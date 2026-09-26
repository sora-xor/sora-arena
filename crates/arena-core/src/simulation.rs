//! Deterministic bounded 60 Hz combat reference. Inputs, not reported hits, drive damage.
use crate::{
    ASSIST_TICKS, Error, MAX_PLAYERS, MAX_TICKS,
    catalog::{self, AttackKind},
    economy::{self, Account, Allocation},
    maps::{ARENAS, Arena},
    math::{self, Aabb, Vec3},
};
use sha2::{Digest, Sha256};

mod abilities;
mod hazards;
mod objectives;
mod respawn;
use abilities::EntityHit;
pub use abilities::{ABILITY_COOLDOWNS, Entity, EntityKind, MAX_ENTITIES, RemovalCause};
pub use objectives::{
    CONTROL_CAPTURE, CONTROL_TARGET, OBJECTIVE_UNLOCK_TICK, PAYLOAD_PUSH_RADIUS,
    PAYLOAD_ROLLBACK_DELAY, Winner,
};

pub const FIRE: u32 = 1;
pub const MELEE: u32 = 2;
pub const BLOCK: u32 = 4;
pub const JUMP: u32 = 8;
pub const ABILITY: u32 = 16;
pub const RELOAD: u32 = 32;
/// §10: with this bit a dead player requests class `move_x` (0-5) and
/// loadout index `move_y` (0-2) for the next respawn.
pub const LOADOUT: u32 = 64;
pub const RESPAWN_TICKS: u32 = 8 * 60;
pub const RADIUS: i32 = 350;
pub const HEIGHT: i32 = 1700;
pub const EYE_HEIGHT: i32 = 1400;
const MAX_PROJECTILES: usize = 128;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    FreeForAll,
    Control,
    Payload,
    Melee,
}
impl Mode {
    pub fn team(self) -> bool {
        matches!(self, Self::Control | Self::Payload)
    }
}

#[derive(Debug, Clone)]
pub struct Config {
    pub mode: Mode,
    pub map: u8,
    pub max_ticks: u32,
    pub base_bond: u64,
    pub offline: bool,
}
#[derive(Debug, Clone)]
pub struct Participant {
    pub team: u8,
    pub class: u8,
    pub weapon: u8,
    pub bond: u64,
    pub special_entitled: bool,
}
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct Input {
    pub buttons: u32,
    pub move_x: i16,
    pub move_y: i16,
    pub yaw: u16,
    pub pitch: i16,
}
impl Input {
    pub fn validate(self) -> Result<(), Error> {
        if self.buttons & !127 != 0
            || !(-127..=127).contains(&self.move_x)
            || !(-127..=127).contains(&self.move_y)
            || !(-16384..=16384).contains(&self.pitch)
            || (self.buttons & LOADOUT != 0
                && (!(0..=5).contains(&self.move_x) || !(0..=2).contains(&self.move_y)))
        {
            return Err(Error::InvalidInput(
                "input outside canonical control bounds",
            ));
        }
        Ok(())
    }
    /// Eight-byte input; slot and tick are defined by the containing batch.
    pub fn encode(self) -> [u8; 8] {
        let b = (self.buttons as u16).to_le_bytes();
        let y = self.yaw.to_le_bytes();
        let p = self.pitch.to_le_bytes();
        [
            b[0],
            b[1],
            self.move_x as i8 as u8,
            self.move_y as i8 as u8,
            y[0],
            y[1],
            p[0],
            p[1],
        ]
    }
    pub fn decode(bytes: [u8; 8]) -> Result<Self, Error> {
        let i = Self {
            buttons: u16::from_le_bytes([bytes[0], bytes[1]]) as u32,
            move_x: bytes[2] as i8 as i16,
            move_y: bytes[3] as i8 as i16,
            yaw: u16::from_le_bytes([bytes[4], bytes[5]]),
            pitch: i16::from_le_bytes([bytes[6], bytes[7]]),
        };
        i.validate()?;
        Ok(i)
    }
}

#[derive(Debug, Clone)]
pub struct Player {
    pub team: u8,
    pub class: u8,
    pub weapon: u8,
    pub position: Vec3,
    pub velocity_z: i32,
    pub yaw: u16,
    pub pitch: i16,
    pub health: i32,
    pub stamina: i32,
    pub alive: bool,
    pub respawn_ticks: u32,
    pub attack_cooldown: u16,
    pub ability_cooldown: u16,
    pub charge: u16,
    pub charge_weapon: u8,
    pub ammo: u16,
    pub reload_ticks: u16,
    pub guarding: bool,
    pub guard_ticks: u16,
    pub spawn_protection: u16,
    /// The special weapon (id 12-17) frozen at admission, if any (§10).
    pub admitted_special: Option<u8>,
    /// A dead player's requested `(class, weapon)`, applied at respawn (§10).
    pub pending_loadout: Option<(u8, u8)>,
    /// Samurai counter-stance ticks remaining (§6.1).
    pub stance_ticks: u16,
    /// Teppō mark ticks remaining (§6.3).
    pub marked_ticks: u16,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DamageRecord {
    pub tick: u32,
    pub attacker: usize,
    pub victim: usize,
    pub damage: u32,
}
/// §3.1 damage kinds. Only rays can be negated by the Samurai stance.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum DamageKind {
    Ray,
    Blast,
    Zone,
    Hazard,
    Riposte,
}
/// §3.1: who dealt a pending hit, a player slot or an arena hazard index.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Source {
    Player(usize),
    Hazard(u8),
}
#[derive(Debug, Clone, Copy)]
struct PendingDamage {
    source: Source,
    victim: usize,
    amount: i32,
    weapon: u8,
    /// Directional-defense source: the attacker's eye for rays and ripostes,
    /// the detonation point for blasts, none for fire zones and hazards.
    /// Never the attacker's current position.
    origin: Option<Vec3>,
    kind: DamageKind,
    /// A charged Plasma matchlock direct hit ignores directional defense.
    penetrating: bool,
}
/// §5.3: where a ray stops.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum RayStop {
    Wall,
    Entity(u32),
    Player(usize),
}
#[derive(Debug, Clone)]
pub struct Projectile {
    pub id: u32,
    pub owner: usize,
    pub position: Vec3,
    pub velocity: Vec3,
    pub weapon: u8,
    pub traveled: i32,
    pub age: u16,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Event {
    Shot {
        slot: usize,
        weapon: u8,
    },
    Damage {
        attacker: usize,
        victim: usize,
        amount: i32,
    },
    Death {
        victim: usize,
        killer: Option<usize>,
        awards: Vec<Allocation>,
    },
    Respawn {
        slot: usize,
    },
    Terminal,
    /// A frontal stance negation, parry or guard applied, emitted before any
    /// `Damage` for the same hit. A halved one-point hit prevents nothing but
    /// still spent guard stamina.
    Guarded {
        attacker: usize,
        victim: usize,
        weapon: u8,
        parried: bool,
        prevented: i32,
    },
    /// Health actually restored (`amount > 0`): Healing lance shots carry the
    /// lance id, class abilities `None`.
    Healed {
        healer: usize,
        target: usize,
        amount: i32,
        weapon: Option<u8>,
    },
    /// An ability activated and started its cooldown. Its own events follow.
    AbilityUsed {
        slot: usize,
        class: u8,
    },
    /// A Teppō mark landed (§6.3).
    Marked {
        marker: usize,
        target: usize,
    },
    /// A Samurai stance queued its riposte (§6.1).
    Riposte {
        slot: usize,
        target: usize,
    },
    EntitySpawned {
        id: u32,
        kind: EntityKind,
        owner: usize,
    },
    /// A decoy or barricade lost `amount > 0` health.
    EntityDamaged {
        id: u32,
        attacker: usize,
        amount: i32,
    },
    /// A forge-hammer strike restored `amount > 0` barricade health.
    EntityRepaired {
        id: u32,
        repairer: usize,
        amount: i32,
    },
    EntityDestroyed {
        id: u32,
        kind: EntityKind,
        owner: usize,
        cause: RemovalCause,
    },
    /// An arena hazard (index into the arena's hazard list) damaged a player
    /// (§9).
    EnvironmentalDamage {
        victim: usize,
        hazard: u8,
        amount: i32,
    },
    /// Control ownership changed (§8.1).
    ObjectiveCaptured {
        team: u8,
    },
    /// Control overtime began (§8.1). Emitted once per match.
    OvertimeStarted,
    /// The payload passed checkpoint `index` (0, 1 or 2) for the first time
    /// (§8.2).
    CheckpointReached {
        index: u8,
    },
    /// The result, immediately before `Terminal` (§8.4).
    MatchWinner {
        winner: Winner,
    },
}
#[derive(Debug, Clone)]
pub struct World {
    pub config: Config,
    pub tick: u32,
    pub players: Vec<Player>,
    pub accounts: Vec<Account>,
    pub projectiles: Vec<Projectile>,
    /// Live ability entities in ascending id order (§5.1).
    pub entities: Vec<Entity>,
    /// Entities removed during the last step, in `EntityDestroyed` order.
    /// Presentation only, like `events`: replaced every step and not part of
    /// the state hash.
    pub removed_entities: Vec<Entity>,
    /// The next entity id. Ids start at 1 and are never reused.
    pub next_entity_id: u32,
    pub damage_history: Vec<DamageRecord>,
    pub events: Vec<Event>,
    pub terminal: bool,
    /// Control owned ticks per team (§8.1).
    pub score: [u32; 2],
    pub control_owner: Option<u8>,
    /// In `[-CONTROL_CAPTURE, CONTROL_CAPTURE]`; negative favours team 0.
    pub control_progress: i32,
    pub overtime: bool,
    /// Distance along the arena's payload route (§8.2).
    pub payload_progress: i32,
    /// Checkpoints passed; the last one is the rollback floor.
    pub payload_checkpoints: u8,
    /// Consecutive unlocked ticks with no attacker near the payload.
    pub payload_idle: u16,
    /// Fixed once, on the terminal tick (§8.4).
    pub winner: Option<Winner>,
}

/// A player-sized body standing at `position`.
fn body_at(position: Vec3) -> Aabb {
    Aabb {
        min: Vec3::new(position.x - RADIUS, position.y - RADIUS, position.z),
        max: Vec3::new(
            position.x + RADIUS,
            position.y + RADIUS,
            position.z + HEIGHT,
        ),
    }
}

impl World {
    pub fn new(config: Config, participants: &[Participant]) -> Result<Self, Error> {
        let Some(arena) = Arena::get(config.map) else {
            return Err(Error::InvalidConfig("invalid match bounds"));
        };
        if participants.is_empty()
            || participants.len() > MAX_PLAYERS
            || config.max_ticks == 0
            || config.max_ticks > MAX_TICKS
            || (!config.mode.team() && participants.len() > 8)
        {
            return Err(Error::InvalidConfig("invalid match bounds"));
        }
        if (config.offline && (config.base_bond != 0 || participants.iter().any(|p| p.bond != 0)))
            || (!config.offline && (config.base_bond == 0 || !config.base_bond.is_multiple_of(10)))
        {
            return Err(Error::InvalidConfig("invalid base bond or offline funds"));
        }
        let mut players = Vec::new();
        let mut accounts = Vec::new();
        let mut total = 0u64;
        for (slot, p) in participants.iter().enumerate() {
            if p.class >= 6
                || p.team >= 2
                || !catalog::weapon_allowed(p.class, p.weapon, p.weapon >= 12)
            {
                return Err(Error::InvalidConfig("class, team or weapon mismatch"));
            }
            if config.mode == Mode::Melee
                && catalog::WEAPONS[p.weapon as usize].kind != AttackKind::Melee
            {
                return Err(Error::InvalidConfig("ranged weapon in melee-only mode"));
            }
            let needed = if p.weapon >= 12 && !p.special_entitled {
                config.base_bond.checked_mul(2).ok_or(Error::Arithmetic)?
            } else {
                config.base_bond
            };
            if p.bond != needed || !p.bond.is_multiple_of(10) {
                return Err(Error::InvalidConfig("deposit does not authorize equipment"));
            }
            total = total.checked_add(p.bond).ok_or(Error::Arithmetic)?;
            // §10: team modes spawn by rank within the team, FFA and Melee at
            // the slot's FFA spawn.
            let spawn = if config.mode.team() {
                let rank = participants[..slot]
                    .iter()
                    .filter(|other| other.team == p.team)
                    .count();
                arena.team_spawns[usize::from(p.team)][rank % 6]
            } else {
                arena.ffa_spawns[slot]
            };
            players.push(Player {
                team: p.team,
                class: p.class,
                weapon: p.weapon,
                position: spawn.position(),
                velocity_z: 0,
                yaw: spawn.yaw,
                pitch: 0,
                health: catalog::CLASSES[p.class as usize].health,
                stamina: 100,
                alive: true,
                respawn_ticks: 0,
                attack_cooldown: 0,
                ability_cooldown: 0,
                charge: 0,
                charge_weapon: u8::MAX,
                ammo: catalog::WEAPONS[p.weapon as usize].magazine,
                reload_ticks: 0,
                guarding: false,
                guard_ticks: 0,
                spawn_protection: 0,
                admitted_special: (p.weapon >= 12).then_some(p.weapon),
                pending_loadout: None,
                stance_ticks: 0,
                marked_ticks: 0,
            });
            accounts.push(Account::new(p.bond));
        }
        if config.mode.team()
            && (players.iter().filter(|p| p.team == 0).count() > 6
                || players.iter().filter(|p| p.team == 1).count() > 6)
        {
            return Err(Error::InvalidConfig("team exceeds six participants"));
        }
        Ok(Self {
            config,
            tick: 0,
            players,
            accounts,
            projectiles: Vec::new(),
            entities: Vec::new(),
            removed_entities: Vec::new(),
            next_entity_id: 1,
            damage_history: Vec::new(),
            events: Vec::new(),
            terminal: false,
            score: [0, 0],
            control_owner: None,
            control_progress: 0,
            overtime: false,
            payload_progress: 0,
            payload_checkpoints: 0,
            payload_idle: 0,
            winner: None,
        })
    }

    /// The configured arena's versioned data (§7).
    pub fn arena(&self) -> &'static Arena {
        &ARENAS[usize::from(self.config.map)]
    }
    pub fn exhausted(&self, slot: usize) -> bool {
        self.accounts[slot].initial > 0 && self.accounts[slot].remaining == 0
    }
    fn enemy(&self, a: usize, b: usize) -> bool {
        a != b && (!self.config.mode.team() || self.players[a].team != self.players[b].team)
    }
    fn body(&self, slot: usize) -> Aabb {
        body_at(self.players[slot].position)
    }
    /// Static walls and live barricades, optionally without one barricade:
    /// everything that blocks movement, rays, projectiles and blasts (§5.4).
    fn solids(&self, skip: Option<u32>) -> impl Iterator<Item = Aabb> + '_ {
        self.arena().walls.iter().map(|w| w.aabb).chain(
            self.entities
                .iter()
                .filter(move |e| e.kind == EntityKind::Barricade && Some(e.id) != skip)
                .map(Entity::bounds),
        )
    }
    fn blocked(&self, from: Vec3, to: Vec3) -> bool {
        self.blocked_except(from, to, None)
    }
    /// Line of sight through static walls and live barricades, ignoring the
    /// barricade `skip` (a blast's target, or one about to be replaced).
    fn blocked_except(&self, from: Vec3, to: Vec3, skip: Option<u32>) -> bool {
        self.solids(skip).any(|w| {
            // A projectile can detonate exactly on a wall face. Its same-side
            // blast ray starts on the closed AABB boundary, so a t=0 hit is
            // not occlusion when the ray immediately leaves that wall.
            if w.contains(from) {
                let direction = to.delta(from);
                let outward = from.offset(Vec3::new(
                    direction.x.signum(),
                    direction.y.signum(),
                    direction.z.signum(),
                ));
                if !w.contains(outward) {
                    return false;
                }
            }
            w.intersect(from, to).is_some()
        })
    }
    fn safe_motion(&self, old: Vec3, desired: Vec3) -> Vec3 {
        let bounds = self.arena().bounds;
        let mut next = old;
        for axis in 0..2 {
            let mut p = next;
            if axis == 0 {
                p.x = desired
                    .x
                    .clamp(bounds.min_x + RADIUS, bounds.max_x - RADIUS);
            } else {
                p.y = desired
                    .y
                    .clamp(bounds.min_y + RADIUS, bounds.max_y - RADIUS);
            }
            let feet = Vec3::new(p.x, p.y, p.z + HEIGHT / 2);
            if !self.solids(None).any(|w| {
                w.expanded(RADIUS, HEIGHT / 2).contains(feet)
                    || w.expanded(RADIUS, HEIGHT / 2)
                        .intersect(Vec3::new(next.x, next.y, next.z + HEIGHT / 2), feet)
                        .is_some()
            }) {
                next = p;
            }
        }
        next.z = desired.z.max(0);
        next
    }
    /// §5.3: the nearest stop of a ray from `shooter`. Living enemies without
    /// spawn protection are targets, and living allies too when `allies`.
    /// Melee reach widens player and decoy bodies by 180 mm. Walls win ties,
    /// then lower entity ids, then lower slots.
    fn ray_stop(
        &self,
        shooter: usize,
        from: Vec3,
        to: Vec3,
        melee: bool,
        allies: bool,
    ) -> Option<RayStop> {
        let wall = self
            .arena()
            .walls
            .iter()
            .filter_map(|w| w.aabb.intersect(from, to))
            .min();
        let mut nearest = wall.unwrap_or((1 << 20) + 1);
        let mut stop = wall.map(|_| RayStop::Wall);
        let reach = if melee { 180 } else { 0 };
        for e in &self.entities {
            let body = match e.kind {
                EntityKind::Barricade => e.bounds(),
                EntityKind::Decoy if self.entity_enemy(shooter, e) => e.bounds().expanded(reach, 0),
                _ => continue,
            };
            if let Some(t) = body.intersect(from, to)
                && t < nearest
            {
                nearest = t;
                stop = Some(RayStop::Entity(e.id));
            }
        }
        for other in 0..self.players.len() {
            let enemy = self.enemy(shooter, other);
            if other == shooter
                || (!enemy && !allies)
                || !self.players[other].alive
                || (enemy && self.players[other].spawn_protection > 0)
            {
                continue;
            }
            if let Some(t) = self.body(other).expanded(reach, 0).intersect(from, to)
                && t < nearest
            {
                nearest = t;
                stop = Some(RayStop::Player(other));
            }
        }
        stop
    }
    /// §3.2: the origin lies in front of the victim in the floor plane. The
    /// direction comes from where the damage came from, so a blast behind a
    /// guard is never blocked because its thrower is ahead. A zero horizontal
    /// offset is not frontal.
    fn frontal(&self, victim: usize, origin: Vec3) -> bool {
        let facing = math::direction(self.players[victim].yaw, 0);
        let incoming = origin.delta(self.players[victim].position);
        i64::from(facing.x) * i64::from(incoming.x) + i64::from(facing.y) * i64::from(incoming.y)
            > 0
    }

    /// Invalid inputs do not advance time or partially modify a match.
    pub fn step(&mut self, inputs: &[Input]) -> Result<(), Error> {
        if self.terminal {
            return Err(Error::Terminal);
        }
        if inputs.len() != self.players.len() {
            return Err(Error::InvalidInput("one input required per permanent slot"));
        }
        for i in inputs {
            i.validate()?;
        }
        self.events.clear();
        self.removed_entities.clear();
        for (slot, &input) in inputs.iter().enumerate() {
            if !self.players[slot].alive {
                if self.exhausted(slot) {
                    continue;
                }
                if input.buttons & LOADOUT != 0 {
                    self.request_loadout(slot, input.move_x as u8, input.move_y as u8);
                }
                // Ability cooldowns keep counting through death (§6).
                let p = &mut self.players[slot];
                p.ability_cooldown = p.ability_cooldown.saturating_sub(1);
                if p.respawn_ticks > 0 {
                    p.respawn_ticks -= 1;
                }
                if p.respawn_ticks == 0 {
                    self.respawn(slot);
                    self.events.push(Event::Respawn { slot });
                }
                continue;
            }
            let p = &mut self.players[slot];
            p.yaw = input.yaw;
            p.pitch = input.pitch;
            p.attack_cooldown = p.attack_cooldown.saturating_sub(1);
            // Blocking or a melee request interrupts the whole-magazine reload
            // before completion. Partial progress never creates ammunition.
            if input.buttons & (BLOCK | MELEE) != 0 {
                p.reload_ticks = 0;
            } else if p.reload_ticks > 0 {
                p.reload_ticks -= 1;
                if p.reload_ticks == 0 {
                    p.ammo = catalog::WEAPONS[p.weapon as usize].magazine;
                }
            }
            p.ability_cooldown = p.ability_cooldown.saturating_sub(1);
            p.spawn_protection = p.spawn_protection.saturating_sub(1);
            if p.stance_ticks > 0 {
                p.stance_ticks -= 1;
                if p.stance_ticks == 0 {
                    // A stance that ends by expiry negated nothing: a whiff.
                    p.attack_cooldown = p.attack_cooldown.max(30);
                }
            }
            p.marked_ticks = p.marked_ticks.saturating_sub(1);
            // A Samurai in stance cannot guard, jump or move horizontally.
            let stance = p.stance_ticks > 0;
            p.guarding = !stance && input.buttons & BLOCK != 0 && p.stamina > 0;
            p.guard_ticks = if p.guarding {
                p.guard_ticks.saturating_add(1)
            } else {
                0
            };
            if p.guarding {
                p.stamina = (p.stamina - 1).max(0);
            } else {
                p.stamina = (p.stamina + 1).min(100);
            }
            if !stance && input.buttons & JUMP != 0 && p.position.z == 0 {
                p.velocity_z = 180;
            }
            p.velocity_z = (p.velocity_z - 8).max(-500);
            let (move_x, move_y) = if stance {
                (0, 0)
            } else {
                (input.move_x, input.move_y)
            };
            let speed =
                catalog::CLASSES[p.class as usize].move_mm_tick / (if p.guarding { 2 } else { 1 });
            let forward = math::direction(input.yaw, 0);
            let right = math::direction(input.yaw.wrapping_add(16384), 0);
            // L1 normalization prevents diagonal speed gain without square roots.
            let norm = (i32::from(move_x).abs() + i32::from(move_y).abs()).max(127);
            let dx = ((i64::from(forward.x) * i64::from(move_x)
                + i64::from(right.x) * i64::from(move_y))
                * i64::from(speed)
                / (32767 * i64::from(norm))) as i32;
            let dy = ((i64::from(forward.y) * i64::from(move_x)
                + i64::from(right.y) * i64::from(move_y))
                * i64::from(speed)
                / (32767 * i64::from(norm))) as i32;
            let old = p.position;
            let desired = old.offset(Vec3::new(dx, dy, p.velocity_z));
            self.players[slot].position = self.safe_motion(old, desired);
            if self.players[slot].position.z == 0 {
                self.players[slot].velocity_z = 0;
            }
        }
        self.damage_history
            .retain(|h| self.tick.saturating_sub(h.tick) <= ASSIST_TICKS);
        // Every ability resolves before any attack is gathered, so its
        // movement, stance, mark or entity affects this tick's attacks the
        // same way whatever the slot order.
        for (slot, input) in inputs.iter().enumerate() {
            if input.buttons & ABILITY != 0
                && self.players[slot].alive
                && self.players[slot].ability_cooldown == 0
            {
                self.ability(slot);
            }
        }
        let mut damage = Vec::<PendingDamage>::new();
        let mut entity_hits = Vec::<EntityHit>::new();
        // (healer, target, amount, weapon), resolved before the damage batch.
        let mut healing = Vec::<(usize, usize, i32, u8)>::new();
        // Gather attacks before applying damage so mutual kills are possible.
        for (slot, input) in inputs.iter().enumerate() {
            if !self.players[slot].alive {
                continue;
            }
            if self.players[slot].stance_ticks > 0 {
                // Attack and reload requests are ignored in stance.
                self.players[slot].charge = 0;
                self.players[slot].charge_weapon = u8::MAX;
                continue;
            }
            let equipped = catalog::WEAPONS[self.players[slot].weapon as usize];
            if input.buttons & RELOAD != 0
                && input.buttons & (BLOCK | MELEE) == 0
                && equipped.magazine > 0
                && self.players[slot].ammo < equipped.magazine
                && self.players[slot].reload_ticks == 0
            {
                self.players[slot].reload_ticks = equipped.reload_ticks;
            }
            if self.players[slot].reload_ticks > 0 || self.players[slot].guarding {
                self.players[slot].charge = 0;
                self.players[slot].charge_weapon = u8::MAX;
                continue;
            }
            if input.buttons & (FIRE | MELEE) == 0 {
                self.players[slot].charge = 0;
                self.players[slot].charge_weapon = u8::MAX;
                continue;
            }
            if self.players[slot].attack_cooldown != 0 {
                continue;
            }
            let weapon = if input.buttons & MELEE != 0 {
                self.players[slot].class * 2
            } else {
                self.players[slot].weapon
            };
            if self.players[slot].charge_weapon != weapon {
                self.players[slot].charge = 0;
                self.players[slot].charge_weapon = weapon;
            }
            let spec = catalog::WEAPONS[weapon as usize];
            if spec.kind != AttackKind::Melee && self.players[slot].ammo == 0 {
                self.players[slot].reload_ticks = spec.reload_ticks;
                self.players[slot].charge = 0;
                self.players[slot].charge_weapon = u8::MAX;
                continue;
            }
            if self.players[slot].stamina < spec.stamina {
                continue;
            }
            if self.players[slot].charge < spec.charge_ticks {
                self.players[slot].charge += 1;
                continue;
            }
            self.players[slot].charge = 0;
            self.players[slot].charge_weapon = u8::MAX;
            self.players[slot].stamina -= spec.stamina;
            if spec.kind != AttackKind::Melee {
                self.players[slot].ammo -= 1;
            }
            self.players[slot].attack_cooldown = spec.cooldown;
            self.players[slot].spawn_protection = 0;
            let from = self.players[slot]
                .position
                .offset(Vec3::new(0, 0, EYE_HEIGHT));
            let direction = math::direction(self.players[slot].yaw, self.players[slot].pitch);
            let to = from.offset(math::scale_q15(direction, spec.range_mm));
            self.events.push(Event::Shot { slot, weapon });
            match spec.kind {
                AttackKind::Melee | AttackKind::Hitscan => {
                    let heals_allies = weapon == 17 && self.config.mode.team();
                    let melee = spec.kind == AttackKind::Melee;
                    match self.ray_stop(slot, from, to, melee, heals_allies) {
                        Some(RayStop::Player(other)) => {
                            if heals_allies && !self.enemy(slot, other) {
                                healing.push((slot, other, spec.damage, weapon));
                            } else {
                                damage.push(PendingDamage {
                                    source: Source::Player(slot),
                                    victim: other,
                                    amount: spec.damage,
                                    weapon,
                                    origin: Some(from),
                                    kind: DamageKind::Ray,
                                    penetrating: spec.kind == AttackKind::Hitscan && weapon == 14,
                                });
                            }
                        }
                        Some(RayStop::Entity(id)) => {
                            entity_hits.extend(self.ray_entity_hit(slot, id, weapon, spec.damage));
                        }
                        Some(RayStop::Wall) | None => {}
                    }
                }
                AttackKind::Projectile => {
                    if self.projectiles.len() < MAX_PROJECTILES {
                        self.projectiles.push(Projectile {
                            id: self.tick * MAX_PLAYERS as u32 + slot as u32,
                            owner: slot,
                            position: from,
                            velocity: math::scale_q15(direction, spec.projectile_mm_tick),
                            weapon,
                            traveled: 0,
                            age: 0,
                        });
                    }
                }
            }
        }
        let flying = std::mem::take(&mut self.projectiles);
        for mut p in flying {
            let spec = catalog::WEAPONS[p.weapon as usize];
            let old = p.position;
            let previous_travel = p.traveled;
            let step_mm = spec.projectile_mm_tick.min(spec.range_mm - previous_travel);
            // The last range-limited step is shortened before collision tests.
            // Truncate each signed component toward zero, like other movement.
            let displacement = Vec3::new(
                (i64::from(p.velocity.x) * i64::from(step_mm) / i64::from(spec.projectile_mm_tick))
                    as i32,
                (i64::from(p.velocity.y) * i64::from(step_mm) / i64::from(spec.projectile_mm_tick))
                    as i32,
                (i64::from(p.velocity.z) * i64::from(step_mm) / i64::from(spec.projectile_mm_tick))
                    as i32,
            );
            let next = old.offset(displacement);
            p.traveled += step_mm;
            p.age += 1;
            // Walls, live barricades, the owner's enemies' decoys and every
            // other living player body stop a projectile (§5.3).
            let mut intersection = self
                .solids(None)
                .filter_map(|w| w.intersect(old, next))
                .min();
            for e in &self.entities {
                if e.kind == EntityKind::Decoy
                    && self.entity_enemy(p.owner, e)
                    && let Some(t) = e.bounds().intersect(old, next)
                {
                    intersection = Some(intersection.map_or(t, |v| v.min(t)));
                }
            }
            for slot in 0..self.players.len() {
                if slot != p.owner
                    && self.players[slot].alive
                    && let Some(t) = self.body(slot).intersect(old, next)
                {
                    intersection = Some(intersection.map_or(t, |v| v.min(t)));
                }
            }
            let expired = p.traveled >= spec.range_mm
                || p.age >= 300
                || next.z <= 0
                || !self.arena().bounds.contains(next.x, next.y);
            if intersection.is_some() || expired {
                let frac = intersection.unwrap_or(1 << 20);
                let d = next.delta(old);
                p.position = old.offset(Vec3::new(
                    (i64::from(d.x) * frac / (1 << 20)) as i32,
                    (i64::from(d.y) * frac / (1 << 20)) as i32,
                    (i64::from(d.z) * frac / (1 << 20)) as i32,
                ));
                // Only distance traversed before the Q20 impact can arm a fuse.
                // Floor nonnegative fractional millimetres conservatively.
                p.traveled = previous_travel + (i64::from(step_mm) * frac / (1 << 20)) as i32;
                if p.traveled >= spec.arming_mm {
                    for slot in 0..self.players.len() {
                        let center = self.players[slot].position.offset(Vec3::new(0, 0, 900));
                        if !self.players[slot].alive
                            || self.players[slot].spawn_protection > 0
                            || (!self.enemy(p.owner, slot) && slot != p.owner)
                        {
                            continue;
                        }
                        if center.distance_squared(p.position)
                            <= i64::from(spec.blast_mm) * i64::from(spec.blast_mm)
                            && !self.blocked(p.position, center)
                        {
                            damage.push(PendingDamage {
                                source: Source::Player(p.owner),
                                victim: slot,
                                amount: spec.damage,
                                weapon: p.weapon,
                                origin: Some(p.position),
                                kind: DamageKind::Blast,
                                penetrating: false,
                            });
                        }
                    }
                    entity_hits.extend(self.blast_entity_hits(
                        p.owner,
                        p.position,
                        spec.blast_mm,
                        spec.damage,
                    ));
                }
            } else {
                p.position = next;
                self.projectiles.push(p);
            }
        }
        self.entity_phase(&mut damage);
        self.hazard_phase(&mut damage);
        // Simultaneous shots are resolved from one canonical pre-damage target
        // snapshot. Healing lands first, then the ordered damage batch, so a
        // timely lance hit can prevent a lethal hit without reviving the dead.
        for (healer, target, amount, weapon) in healing {
            let player = &mut self.players[target];
            if player.alive && player.health > 0 {
                let maximum = catalog::CLASSES[player.class as usize].health;
                let before = player.health;
                player.health = player.health.saturating_add(amount).min(maximum);
                let restored = player.health - before;
                if restored > 0 {
                    self.events.push(Event::Healed {
                        healer,
                        target,
                        amount: restored,
                        weapon: Some(weapon),
                    });
                }
            }
        }
        let mut killers = vec![None; self.players.len()];
        // Samurai whose stance negated a hit in this batch (§6.1).
        let mut negated = vec![false; self.players.len()];
        // Ripostes are appended while the batch runs, so walk it by index.
        let mut next = 0;
        while let Some(&hit) = damage.get(next) {
            next += 1;
            let victim = hit.victim;
            let mut amount = hit.amount;
            if self.players[victim].health <= 0 {
                continue;
            }
            let attacker = match hit.source {
                Source::Player(slot) => Some(slot),
                Source::Hazard(_) => None,
            };
            // §3.3 modifier order: mark, directional defense, ward. Hazards
            // are never marked or defended, but wards reduce them.
            if self.players[victim].marked_ticks > 0
                && attacker.is_some_and(|attacker| self.enemy(attacker, victim))
            {
                amount += amount / 4;
            }
            if let (Some(attacker), Some(origin)) = (attacker, hit.origin)
                && attacker != victim
                && !hit.penetrating
                && self.frontal(victim, origin)
            {
                let (remaining, riposte) = self.defend(hit, attacker, amount, &mut negated);
                amount = remaining;
                damage.extend(riposte);
            }
            if attacker != Some(victim) && self.warded(victim) {
                amount -= amount * 35 / 100;
            }
            let dealt = amount.min(self.players[victim].health);
            self.players[victim].health -= dealt;
            if dealt > 0 {
                match hit.source {
                    Source::Player(attacker) => {
                        self.events.push(Event::Damage {
                            attacker,
                            victim,
                            amount: dealt,
                        });
                        if attacker != victim {
                            self.damage_history.push(DamageRecord {
                                tick: self.tick,
                                attacker,
                                victim,
                                damage: dealt as u32,
                            });
                        }
                    }
                    Source::Hazard(hazard) => self.events.push(Event::EnvironmentalDamage {
                        victim,
                        hazard,
                        amount: dealt,
                    }),
                }
            }
            if self.players[victim].health <= 0 {
                // §3.4 kill credit. A self-inflicted blast is a suicide even
                // when an enemy dealt qualifying damage earlier in the assist
                // window. A hazard death credits the most recent enemy damage
                // still inside the window, or no one. Friendly fire never
                // reaches the batch.
                killers[victim] = match hit.source {
                    Source::Player(attacker) => {
                        (attacker != victim && self.enemy(attacker, victim)).then_some(attacker)
                    }
                    Source::Hazard(_) => self
                        .damage_history
                        .iter()
                        .rev()
                        .find(|h| h.victim == victim && self.enemy(h.attacker, victim))
                        .map(|h| h.attacker),
                };
            }
        }
        // A stance that negated a hit ends with the batch that negated it.
        for (slot, negated) in negated.into_iter().enumerate() {
            if negated {
                self.players[slot].stance_ticks = 0;
            }
        }
        self.apply_entity_hits(&entity_hits);
        // Participation is frozen for the whole simultaneous death batch. A
        // lower-slot victim exhausting now must not lose a teammate award from
        // another death in the same tick merely because we visit it first.
        let participating: Vec<_> = (0..self.players.len())
            .map(|slot| !self.exhausted(slot))
            .collect();
        for (victim, killer) in killers.into_iter().enumerate() {
            if self.players[victim].alive && self.players[victim].health <= 0 {
                let mut assist_damage = vec![0u32; self.players.len()];
                if let Some(k) = killer {
                    for h in &self.damage_history {
                        if h.victim == victim
                            && h.attacker != k
                            && self.enemy(h.attacker, victim)
                            && (!self.config.mode.team()
                                || self.players[h.attacker].team == self.players[k].team)
                        {
                            assist_damage[h.attacker] =
                                assist_damage[h.attacker].saturating_add(h.damage);
                        }
                    }
                }
                let assists: Vec<_> = assist_damage
                    .into_iter()
                    .enumerate()
                    .filter(|(_, d)| *d > 0)
                    .collect();
                let teammates: Vec<_> = if self.config.mode.team() {
                    killer.map_or_else(Vec::new, |k| {
                        (0..self.players.len())
                            .filter(|&s| {
                                s != k
                                    && self.players[s].team == self.players[k].team
                                    && participating[s]
                            })
                            .collect()
                    })
                } else {
                    Vec::new()
                };
                let awards = economy::apply_death(
                    &mut self.accounts,
                    victim,
                    killer,
                    &assists,
                    &teammates,
                    self.config.mode.team(),
                )?;
                let p = &mut self.players[victim];
                p.alive = false;
                p.respawn_ticks = RESPAWN_TICKS;
                p.charge = 0;
                p.charge_weapon = u8::MAX;
                p.reload_ticks = 0;
                // Death ends a stance without a whiff and clears a mark.
                p.stance_ticks = 0;
                p.marked_ticks = 0;
                self.damage_history.retain(|h| h.victim != victim);
                self.events.push(Event::Death {
                    victim,
                    killer,
                    awards,
                });
                // §5.2: a death removes the victim's decoy; a death that
                // exhausts the reserve removes every entity the victim owns.
                if self.exhausted(victim) {
                    self.remove_entities(victim, None, RemovalCause::OwnerExhausted);
                } else {
                    self.remove_entities(victim, Some(EntityKind::Decoy), RemovalCause::OwnerDied);
                }
            }
        }
        let secured = self.update_objectives();
        self.tick += 1;
        if let Some(winner) = self.result(secured) {
            self.winner = Some(winner);
            self.terminal = true;
            self.events.push(Event::MatchWinner { winner });
            self.events.push(Event::Terminal);
        }
        debug_assert!(economy::conserved(&self.accounts));
        debug_assert!(self.entities.len() <= MAX_ENTITIES);
        Ok(())
    }

    /// §3.2 directional defense of a frontal hit from another player, in
    /// order: the Samurai stance, parry, guard. Returns the remaining amount
    /// and the riposte to append to the batch, if the stance earned one.
    fn defend(
        &mut self,
        hit: PendingDamage,
        attacker: usize,
        amount: i32,
        negated: &mut [bool],
    ) -> (i32, Option<PendingDamage>) {
        let victim = hit.victim;
        if hit.kind == DamageKind::Ray
            && self.players[victim].stance_ticks > 0
            && self.enemy(attacker, victim)
        {
            self.events.push(Event::Guarded {
                attacker,
                victim,
                weapon: hit.weapon,
                parried: true,
                prevented: amount,
            });
            // Only the first negated hit of a stance ripostes.
            let riposte = if negated[victim] {
                None
            } else {
                negated[victim] = true;
                self.riposte(victim, attacker)
            };
            return (0, riposte);
        }
        let player = &mut self.players[victim];
        if !player.guarding {
            return (amount, None);
        }
        let parried = player.guard_ticks <= 8 && player.stamina >= 20;
        let remaining = if parried {
            player.stamina -= 20;
            0
        } else if player.stamina >= 10 {
            player.stamina -= 10;
            (amount + 1) / 2
        } else {
            // With less than 10 stamina a guard has no effect.
            return (amount, None);
        };
        if parried && player.class == 0 {
            // A Samurai's parry refunds part of the stance cooldown.
            player.ability_cooldown = player.ability_cooldown.saturating_sub(120);
        }
        if parried
            && hit.kind == DamageKind::Ray
            && catalog::WEAPONS[hit.weapon as usize].kind == AttackKind::Melee
        {
            // Parry stagger: a parried melee strike delays the next attack.
            let striker = &mut self.players[attacker];
            striker.attack_cooldown = striker.attack_cooldown.saturating_add(30);
        }
        self.events.push(Event::Guarded {
            attacker,
            victim,
            weapon: hit.weapon,
            parried,
            prevented: amount - remaining,
        });
        (remaining, None)
    }

    /// Frozen offline replay fingerprint. Native envelopes use canonical Norito.
    /// This digest is not an execution proof or authenticated ledger statement.
    /// Layout: docs/combat-rules.md §12.
    pub fn state_hash(&self) -> [u8; 32] {
        let mut h = Sha256::new();
        h.update(b"sora-arena:reference-state:v2\0");
        h.update(crate::RULES_VERSION.as_bytes());
        h.update([
            self.config.mode as u8,
            self.config.map,
            self.config.offline as u8,
        ]);
        h.update(self.config.max_ticks.to_le_bytes());
        h.update(self.config.base_bond.to_le_bytes());
        h.update(self.tick.to_le_bytes());
        h.update([self.terminal as u8]);
        h.update(self.arena().map_digest());
        h.update((self.players.len() as u32).to_le_bytes());
        for (p, a) in self.players.iter().zip(&self.accounts) {
            let (pending_class, pending_weapon) = p.pending_loadout.unwrap_or((255, 255));
            h.update([
                p.team,
                p.class,
                p.weapon,
                p.alive as u8,
                p.guarding as u8,
                p.admitted_special.unwrap_or(255),
                pending_class,
                pending_weapon,
            ]);
            for n in [
                p.position.x,
                p.position.y,
                p.position.z,
                p.velocity_z,
                p.health,
                p.stamina,
            ] {
                h.update(n.to_le_bytes());
            }
            h.update(p.yaw.to_le_bytes());
            h.update(p.pitch.to_le_bytes());
            h.update(p.respawn_ticks.to_le_bytes());
            h.update([p.charge_weapon]);
            for n in [
                p.attack_cooldown,
                p.ability_cooldown,
                p.charge,
                p.ammo,
                p.reload_ticks,
                p.guard_ticks,
                p.spawn_protection,
                p.stance_ticks,
                p.marked_ticks,
            ] {
                h.update(n.to_le_bytes());
            }
            for n in [a.initial, a.remaining, a.earnings] {
                h.update(n.to_le_bytes());
            }
            for n in [a.kills, a.deaths, a.paid_deaths] {
                h.update(n.to_le_bytes());
            }
        }
        h.update((self.projectiles.len() as u32).to_le_bytes());
        for p in &self.projectiles {
            h.update(p.id.to_le_bytes());
            h.update((p.owner as u32).to_le_bytes());
            h.update([p.weapon]);
            for n in [
                p.position.x,
                p.position.y,
                p.position.z,
                p.velocity.x,
                p.velocity.y,
                p.velocity.z,
                p.traveled,
            ] {
                h.update(n.to_le_bytes());
            }
            h.update(p.age.to_le_bytes());
        }
        h.update((self.entities.len() as u32).to_le_bytes());
        for e in &self.entities {
            h.update(e.id.to_le_bytes());
            h.update([e.kind as u8]);
            h.update((e.owner as u32).to_le_bytes());
            h.update([e.team]);
            for n in [e.position.x, e.position.y, e.position.z] {
                h.update(n.to_le_bytes());
            }
            h.update(e.yaw.to_le_bytes());
            h.update(e.health.to_le_bytes());
            h.update(e.age.to_le_bytes());
            for n in [e.half_x, e.half_y] {
                h.update(n.to_le_bytes());
            }
        }
        h.update(self.next_entity_id.to_le_bytes());
        h.update((self.damage_history.len() as u32).to_le_bytes());
        for d in &self.damage_history {
            for n in [d.tick, d.attacker as u32, d.victim as u32, d.damage] {
                h.update(n.to_le_bytes());
            }
        }
        for n in self.score {
            h.update(n.to_le_bytes());
        }
        h.update([self.control_owner.unwrap_or(255)]);
        h.update(self.control_progress.to_le_bytes());
        h.update([self.overtime as u8]);
        h.update(self.payload_progress.to_le_bytes());
        h.update([self.payload_checkpoints]);
        h.update(self.payload_idle.to_le_bytes());
        let (tag, value) = match self.winner {
            None => (0u8, 0u32),
            Some(Winner::Team(team)) => (1, u32::from(team)),
            Some(Winner::Slot(slot)) => (2, slot as u32),
            Some(Winner::Draw) => (3, 0),
        };
        h.update([tag]);
        h.update(value.to_le_bytes());
        h.finalize().into()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn duel() -> World {
        World::new(
            Config {
                mode: Mode::FreeForAll,
                map: 0,
                max_ticks: 36000,
                base_bond: 1000,
                offline: false,
            },
            &[
                Participant {
                    team: 0,
                    class: 0,
                    weapon: 1,
                    bond: 1000,
                    special_entitled: false,
                },
                Participant {
                    team: 1,
                    class: 0,
                    weapon: 1,
                    bond: 1000,
                    special_entitled: false,
                },
            ],
        )
        .unwrap()
    }
    #[test]
    fn simultaneous_exhaustion_preserves_same_tick_team_awards() {
        let roster = (0..4)
            .map(|slot| Participant {
                team: slot / 2,
                class: 0,
                weapon: 1,
                bond: 1000,
                special_entitled: false,
            })
            .collect::<Vec<_>>();
        let mut w = World::new(
            Config {
                mode: Mode::Control,
                map: 0,
                max_ticks: 600,
                base_bond: 1000,
                offline: false,
            },
            &roster,
        )
        .unwrap();
        for (slot, (x, y)) in [(-1000, 0), (-1000, 2000), (0, 0), (0, 2000)]
            .into_iter()
            .enumerate()
        {
            w.players[slot].position = Vec3::new(x, y, 0);
        }
        w.players[0].health = 1;
        w.players[3].health = 1;
        w.accounts[0].remaining = 100;
        w.accounts[0].paid_deaths = 9;
        w.accounts[2].earnings = 900;
        w.step(&[
            Input::default(),
            Input {
                buttons: FIRE,
                ..Input::default()
            },
            Input {
                buttons: FIRE,
                yaw: 32768,
                ..Input::default()
            },
            Input::default(),
        ])
        .unwrap();
        assert!(w.exhausted(0));
        assert_eq!(w.accounts[0].earnings, 40);
        assert_eq!(w.accounts[1].earnings, 60);
        assert_eq!(w.accounts[3].earnings, 40);
        assert!(!w.players[3].alive);
        assert!(economy::conserved(&w.accounts));
    }
    #[test]
    fn legal_shots_derive_death_and_payout() {
        let mut w = duel();
        w.players[0].position = Vec3::new(0, 0, 0);
        w.players[1].position = Vec3::new(5000, 0, 0);
        let i = [
            Input {
                buttons: FIRE,
                ..Input::default()
            },
            Input::default(),
        ];
        for _ in 0..=60 {
            w.step(&i).unwrap();
        }
        assert!(!w.players[1].alive);
        assert_eq!(w.accounts[1].remaining, 900);
        assert_eq!(w.accounts[0].earnings, 100);
    }
    #[test]
    fn suicide_after_enemy_damage_never_transfers_bond() {
        let mut w = World::new(
            Config {
                mode: Mode::FreeForAll,
                map: 0,
                max_ticks: 600,
                base_bond: 1000,
                offline: false,
            },
            &[
                Participant {
                    team: 0,
                    class: 3,
                    weapon: 7,
                    bond: 1000,
                    special_entitled: false,
                },
                Participant {
                    team: 1,
                    class: 0,
                    weapon: 1,
                    bond: 1000,
                    special_entitled: false,
                },
            ],
        )
        .unwrap();
        // A real grenade travels 2100 mm to the enemy's near face, arms, and
        // detonates inside its owner's 2500 mm blast radius.
        w.players[0].position = Vec3::new(0, 0, 0);
        w.players[1].position = Vec3::new(2450, 0, 0);
        w.players[0].health = 50;
        w.damage_history.push(DamageRecord {
            tick: 0,
            attacker: 1,
            victim: 0,
            damage: 30,
        });
        w.step(&[
            Input {
                buttons: FIRE,
                ..Input::default()
            },
            Input::default(),
        ])
        .unwrap();
        for _ in 0..6 {
            w.step(&[Input::default(), Input::default()]).unwrap();
        }
        assert!(!w.players[0].alive);
        assert_eq!(w.accounts[0].deaths, 1);
        assert_eq!(w.accounts[0].paid_deaths, 0);
        assert_eq!(w.accounts[0].remaining, 1000);
        assert_eq!(w.accounts[1].kills, 0);
        assert_eq!(w.accounts[1].earnings, 0);
        assert!(economy::conserved(&w.accounts));
    }
    #[test]
    fn wall_surface_blast_reaches_a_target_on_the_impact_side() {
        let mut w = World::new(
            Config {
                mode: Mode::FreeForAll,
                map: 0,
                max_ticks: 600,
                base_bond: 1000,
                offline: false,
            },
            &[
                Participant {
                    team: 0,
                    class: 3,
                    weapon: 7,
                    bond: 1000,
                    special_entitled: false,
                },
                Participant {
                    team: 1,
                    class: 0,
                    weapon: 1,
                    bond: 1000,
                    special_entitled: false,
                },
            ],
        )
        .unwrap();
        // The grenade travels in exact 350-mm steps and meets the near face
        // of Nyaagyu Estate's east kura at x=9500. The enemy is beside it,
        // clear of the wall itself.
        w.players[0].position = Vec3::new(7050, 4750, 0);
        w.players[1].position = Vec3::new(9000, 6550, 0);
        w.players[1].health = 60;
        let impact = Vec3::new(9500, 4750, EYE_HEIGHT);
        assert!(!w.blocked(impact, Vec3::new(9000, 6550, 900)));
        assert!(w.blocked(impact, Vec3::new(13_000, 4750, 900)));
        w.step(&[
            Input {
                buttons: FIRE,
                ..Input::default()
            },
            Input::default(),
        ])
        .unwrap();
        for _ in 0..6 {
            w.step(&[Input::default(), Input::default()]).unwrap();
        }
        assert!(!w.players[1].alive);
        assert_eq!(w.accounts[1].remaining, 900);
        assert_eq!(w.accounts[0].earnings, 100);
        assert!(economy::conserved(&w.accounts));
    }
    #[test]
    fn walls_stop_damage() {
        // Nyaagyu Estate's east kura (x = 9500..12500) stands between them.
        let mut w = duel();
        w.players[0].position = Vec3::new(4000, 4750, 0);
        w.players[1].position = Vec3::new(14_000, 4750, 0);
        for _ in 0..120 {
            w.step(&[
                Input {
                    buttons: FIRE,
                    ..Input::default()
                },
                Input::default(),
            ])
            .unwrap();
        }
        assert_eq!(w.players[1].health, 125);
    }
    #[test]
    fn invalid_input_is_transactional() {
        let mut w = duel();
        let hash = w.state_hash();
        assert!(
            w.step(&[
                Input {
                    move_x: 128,
                    ..Input::default()
                },
                Input::default()
            ])
            .is_err()
        );
        assert_eq!(hash, w.state_hash());
    }
    #[test]
    fn identical_inputs_produce_identical_replays() {
        let mut a = duel();
        let mut b = a.clone();
        for t in 0..600 {
            let input = [
                Input {
                    buttons: if t % 11 == 0 { FIRE } else { 0 },
                    move_x: 80,
                    yaw: (t * 93) as u16,
                    ..Input::default()
                },
                Input {
                    move_y: -80,
                    yaw: (t * 77) as u16,
                    ..Input::default()
                },
            ];
            a.step(&input).unwrap();
            b.step(&input).unwrap();
            assert_eq!(a.state_hash(), b.state_hash());
        }
    }
    #[test]
    fn nft_or_double_bond_access() {
        let c = Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 10,
            base_bond: 1000,
            offline: false,
        };
        let mut p = Participant {
            team: 0,
            class: 0,
            weapon: 12,
            bond: 1000,
            special_entitled: false,
        };
        assert!(World::new(c.clone(), &[p.clone()]).is_err());
        p.bond = 2000;
        assert!(World::new(c.clone(), &[p.clone()]).is_ok());
        p.bond = 1000;
        p.special_entitled = true;
        assert!(World::new(c, &[p]).is_ok());
    }
    #[test]
    fn friendly_fire_is_disabled() {
        let mut w = duel();
        w.config.mode = Mode::Control;
        w.players[0].team = 0;
        w.players[1].team = 0;
        w.config.offline = true;
        w.players[0].position = Vec3::default();
        w.players[1].position = Vec3::new(3000, 0, 0);
        for _ in 0..60 {
            w.step(&[
                Input {
                    buttons: FIRE,
                    ..Input::default()
                },
                Input::default(),
            ])
            .unwrap();
        }
        assert_eq!(w.players[1].health, 125);
    }
    #[test]
    fn every_control_roundtrips() {
        for b in 0..64 {
            let i = Input {
                buttons: b,
                move_x: -127,
                move_y: 127,
                yaw: 65535,
                pitch: -16384,
            };
            assert_eq!(Input::decode(i.encode()).unwrap(), i);
        }
    }
}
