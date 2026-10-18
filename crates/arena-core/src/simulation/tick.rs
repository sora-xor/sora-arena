//! Ordered internal tick phases for the canonical combat transition.
//!
//! Only `advance` is callable from the parent module. Phase helpers and pending
//! effects stay private, so callers cannot skip or reorder part of a tick.
//! These are the reference transition itself, not a proof or a checkpoint API.
use super::{
    ABILITY, BLOCK, DamageKind, DamageRecord, EYE_HEIGHT, EntityKind, Event, FIRE, Input, JUMP,
    LOADOUT, MAX_ENTITIES, MAX_PROJECTILES, MELEE, PendingDamage, Projectile, RELOAD,
    RESPAWN_TICKS, RayStop, RemovalCause, Source, World, abilities::EntityHit,
};
use crate::{
    ASSIST_TICKS, Error, MAX_PLAYERS,
    catalog::{self, AttackKind},
    economy,
    math::{self, Vec3},
};

/// Effects gathered in canonical order before damage changes living targets.
#[derive(Default)]
struct PendingEffects {
    damage: Vec<PendingDamage>,
    entity_hits: Vec<EntityHit>,
    healing: Vec<PendingHealing>,
}

/// A healing-lance hit resolves before the gathered damage batch.
struct PendingHealing {
    healer: usize,
    target: usize,
    amount: i32,
    weapon: u8,
}

/// Kill credit retained while entity hits resolve before simultaneous deaths.
struct PendingDeaths {
    killers: Vec<Option<usize>>,
}

/// The sole internal entry to the complete ordered transition.
pub(super) fn advance(world: &mut World, inputs: &[Input]) -> Result<(), Error> {
    world.advance_tick(inputs)
}

impl World {
    fn advance_tick(&mut self, inputs: &[Input]) -> Result<(), Error> {
        if self.terminal {
            return Err(Error::Terminal);
        }
        if inputs.len() != self.players.len() {
            return Err(Error::InvalidInput("one input required per permanent slot"));
        }
        for i in inputs {
            i.validate()?;
        }
        self.prepare_players(inputs);
        self.activate_abilities(inputs);
        let mut effects = PendingEffects::default();
        self.gather_attacks(inputs, &mut effects);
        self.advance_projectiles(&mut effects);
        self.entity_phase(&mut effects.damage);
        self.hazard_phase(&mut effects.damage);
        let PendingEffects {
            mut damage,
            entity_hits,
            healing,
        } = effects;
        self.resolve_healing(healing);
        let deaths = self.resolve_damage(&mut damage);
        self.apply_entity_hits(&entity_hits);
        self.resolve_deaths(deaths)?;
        self.complete_tick();
        Ok(())
    }

    fn prepare_players(&mut self, inputs: &[Input]) {
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
    }

    fn activate_abilities(&mut self, inputs: &[Input]) {
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
    }

    fn gather_attacks(&mut self, inputs: &[Input], effects: &mut PendingEffects) {
        let PendingEffects {
            damage,
            entity_hits,
            healing,
        } = effects;
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
                                healing.push(PendingHealing {
                                    healer: slot,
                                    target: other,
                                    amount: spec.damage,
                                    weapon,
                                });
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
    }

    fn advance_projectiles(&mut self, effects: &mut PendingEffects) {
        let PendingEffects {
            damage,
            entity_hits,
            ..
        } = effects;
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
    }

    fn resolve_healing(&mut self, healing: Vec<PendingHealing>) {
        // Simultaneous shots are resolved from one canonical pre-damage target
        // snapshot. Healing lands first, then the ordered damage batch, so a
        // timely lance hit can prevent a lethal hit without reviving the dead.
        for PendingHealing {
            healer,
            target,
            amount,
            weapon,
        } in healing
        {
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
    }

    fn resolve_damage(&mut self, damage: &mut Vec<PendingDamage>) -> PendingDeaths {
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
        PendingDeaths { killers }
    }

    fn resolve_deaths(&mut self, deaths: PendingDeaths) -> Result<(), Error> {
        let PendingDeaths { killers } = deaths;
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
        Ok(())
    }

    fn complete_tick(&mut self) {
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
    }
}
