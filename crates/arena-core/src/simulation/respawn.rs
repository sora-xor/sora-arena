//! Respawn and loadout selection (docs/combat-rules.md §10). Admission froze
//! the bond and the one special weapon a participant may ever select.
use super::{Mode, World};
use crate::{
    catalog::{self, AttackKind},
    maps::Spawn,
};

impl World {
    /// §10: a dead player's loadout request. Index 0 selects the class ranged
    /// weapon, 1 the class melee weapon and 2 the admitted special, only if it
    /// is that class's special. Melee mode admits only melee weapons. An
    /// invalid request is ignored; a valid one replaces any earlier one.
    pub(super) fn request_loadout(&mut self, slot: usize, class: u8, index: u8) {
        let weapon = match index {
            0 => class * 2 + 1,
            1 => class * 2,
            _ => match self.players[slot].admitted_special {
                Some(special) if special == 12 + class => special,
                _ => return,
            },
        };
        if self.config.mode == Mode::Melee
            && catalog::WEAPONS[usize::from(weapon)].kind != AttackKind::Melee
        {
            return;
        }
        self.players[slot].pending_loadout = Some((class, weapon));
    }

    /// §10 spawn point. Team modes use the slot's rank among its team. FFA and
    /// Melee respawn at the FFA spawn farthest (largest minimum horizontal
    /// distance) from every other living player, ties to the lowest index.
    fn respawn_point(&self, slot: usize) -> Spawn {
        let arena = self.arena();
        let player = &self.players[slot];
        if self.config.mode.team() {
            let rank = self.players[..slot]
                .iter()
                .filter(|other| other.team == player.team)
                .count();
            return arena.team_spawns[usize::from(player.team)][rank % 6];
        }
        let others = self
            .players
            .iter()
            .enumerate()
            .filter(|&(other, p)| other != slot && p.alive)
            .map(|(_, p)| p.position)
            .collect::<Vec<_>>();
        if others.is_empty() {
            return arena.ffa_spawns[slot % arena.ffa_spawns.len()];
        }
        let mut best = (-1, arena.ffa_spawns[0]);
        for spawn in arena.ffa_spawns {
            let nearest = others
                .iter()
                .map(|p| p.horizontal_distance_squared(spawn.position()))
                .fold(i64::MAX, i64::min);
            if nearest > best.0 {
                best = (nearest, spawn);
            }
        }
        best.1
    }

    /// Apply a pending loadout, then restore the player at its spawn point.
    /// The bond, the admitted special and the ability cooldown carry over.
    pub(super) fn respawn(&mut self, slot: usize) {
        let spawn = self.respawn_point(slot);
        let p = &mut self.players[slot];
        if let Some((class, weapon)) = p.pending_loadout.take() {
            p.class = class;
            p.weapon = weapon;
        }
        p.position = spawn.position();
        p.yaw = spawn.yaw;
        p.pitch = 0;
        p.health = catalog::CLASSES[usize::from(p.class)].health;
        p.alive = true;
        p.stamina = 100;
        p.spawn_protection = 120;
        p.velocity_z = 0;
        p.charge = 0;
        p.charge_weapon = u8::MAX;
        p.ammo = catalog::WEAPONS[usize::from(p.weapon)].magazine;
        p.reload_ticks = 0;
        p.guarding = false;
        p.guard_ticks = 0;
        p.attack_cooldown = 0;
        p.stance_ticks = 0;
        p.marked_ticks = 0;
    }
}
