//! Class abilities (docs/combat-rules.md §6) and the entities they leave in
//! the world (§5). Every number is an exact integer from the rules document.
use super::{
    DamageKind, EYE_HEIGHT, Event, HEIGHT, PendingDamage, RADIUS, RayStop, Source, World, body_at,
};
use crate::{
    MAX_PLAYERS, catalog,
    math::{self, Aabb, Vec3},
};

/// Each owner keeps at most one live entity of each of the four kinds.
pub const MAX_ENTITIES: usize = 4 * MAX_PLAYERS;
/// Ability cooldown ticks by class id (§6).
pub const ABILITY_COOLDOWNS: [u16; 6] = [480, 600, 720, 720, 720, 900];
const FORGE_HAMMER: u8 = 8;
const DECOY_HEALTH: i32 = 60;
const BARRICADE_HEALTH: i32 = 250;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EntityKind {
    Decoy = 1,
    Barricade = 2,
    FireZone = 3,
    Ward = 4,
}
impl EntityKind {
    /// Entity-phase ticks from spawn to expiry (§5.2).
    pub const fn lifetime(self) -> u16 {
        match self {
            Self::Barricade => 1800,
            Self::Decoy | Self::FireZone | Self::Ward => 300,
        }
    }
    /// Spawn health, which repair never exceeds; 0 for kinds that cannot be
    /// damaged.
    pub const fn max_health(self) -> i32 {
        match self {
            Self::Decoy => DECOY_HEALTH,
            Self::Barricade => BARRICADE_HEALTH,
            Self::FireZone | Self::Ward => 0,
        }
    }
    /// Barricades stand 2000 mm, above the 1936 mm apex of a jump, so no
    /// player can jump over one or land inside one.
    const fn height(self) -> i32 {
        match self {
            Self::Decoy => HEIGHT,
            Self::Barricade => 2000,
            Self::FireZone | Self::Ward => 0,
        }
    }
}

/// Why an entity left the world (§5.2).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RemovalCause {
    Expired,
    /// Its health reached zero; `by` dealt the emptying hit.
    Destroyed {
        by: usize,
    },
    Replaced,
    OwnerDied,
    OwnerExhausted,
}

/// One live ability entity (§5.1). Positions are floor-level (z = 0).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Entity {
    pub id: u32,
    pub kind: EntityKind,
    pub owner: usize,
    pub team: u8,
    pub position: Vec3,
    pub yaw: u16,
    /// Decoy and barricade health; 0 for kinds that cannot be damaged.
    pub health: i32,
    pub age: u16,
    /// Barricade half-extents; the radius for fire zones and wards; the
    /// player radius for decoys.
    pub half_x: i32,
    pub half_y: i32,
}
impl Entity {
    /// Collision box: a player-sized body for decoys, the full barricade box
    /// for barricades, and a flat footprint for zones and wards.
    pub fn bounds(&self) -> Aabb {
        Aabb {
            min: Vec3::new(
                self.position.x - self.half_x,
                self.position.y - self.half_y,
                self.position.z,
            ),
            max: Vec3::new(
                self.position.x + self.half_x,
                self.position.y + self.half_y,
                self.position.z + self.kind.height(),
            ),
        }
    }
}

/// One entry of the entity damage and repair batch (§2 phase 11).
#[derive(Debug, Clone, Copy)]
pub(super) enum EntityHit {
    Damage {
        id: u32,
        attacker: usize,
        amount: i32,
    },
    Repair {
        id: u32,
        repairer: usize,
    },
}

impl World {
    pub fn entity(&self, id: u32) -> Option<&Entity> {
        let index = self.entities.binary_search_by_key(&id, |e| e.id).ok()?;
        Some(&self.entities[index])
    }
    /// An entity is an enemy of `slot` when it belongs to the other team, or
    /// in FFA and Melee to another player. Entities never change team.
    pub(super) fn entity_enemy(&self, slot: usize, entity: &Entity) -> bool {
        if self.config.mode.team() {
            self.players[slot].team != entity.team
        } else {
            slot != entity.owner
        }
    }
    /// A ray from `slot` stopped on entity `id`: enemy rays damage decoys and
    /// barricades; an allied forge-hammer strike repairs a barricade; any
    /// other allied ray stops harmlessly.
    pub(super) fn ray_entity_hit(
        &self,
        slot: usize,
        id: u32,
        weapon: u8,
        amount: i32,
    ) -> Option<EntityHit> {
        let entity = self.entity(id)?;
        if self.entity_enemy(slot, entity) {
            Some(EntityHit::Damage {
                id,
                attacker: slot,
                amount,
            })
        } else if weapon == FORGE_HAMMER && entity.kind == EntityKind::Barricade {
            Some(EntityHit::Repair { id, repairer: slot })
        } else {
            None
        }
    }
    /// §5.3: an armed blast damages enemy decoys (centre 900 mm up) and enemy
    /// barricades (centre 1000 mm up) within its radius, in id order, unless a
    /// wall or another barricade blocks the path. Decoys never occlude.
    pub(super) fn blast_entity_hits(
        &self,
        owner: usize,
        at: Vec3,
        radius: i32,
        amount: i32,
    ) -> Vec<EntityHit> {
        self.entities
            .iter()
            .filter_map(|e| {
                let centre = match e.kind {
                    EntityKind::Decoy => e.position.offset(Vec3::new(0, 0, 900)),
                    EntityKind::Barricade => e.position.offset(Vec3::new(0, 0, 1000)),
                    EntityKind::FireZone | EntityKind::Ward => return None,
                };
                (self.entity_enemy(owner, e)
                    && centre.distance_squared(at) <= i64::from(radius) * i64::from(radius)
                    && !self.blocked_except(at, centre, Some(e.id)))
                .then_some(EntityHit::Damage {
                    id: e.id,
                    attacker: owner,
                    amount,
                })
            })
            .collect()
    }
    /// §6.6: a live ward protects its owner's team (team modes) or its owner
    /// (FFA and Melee) within its radius. Wards do not stack.
    pub(super) fn warded(&self, victim: usize) -> bool {
        let player = &self.players[victim];
        self.entities.iter().any(|e| {
            e.kind == EntityKind::Ward
                && if self.config.mode.team() {
                    e.team == player.team
                } else {
                    e.owner == victim
                }
                && e.position.horizontal_distance_squared(player.position)
                    <= i64::from(e.half_x) * i64::from(e.half_x)
        })
    }

    /// §6: activate `slot`'s class ability. A failed precondition changes
    /// nothing; otherwise `AbilityUsed` precedes the ability's own events.
    pub(super) fn ability(&mut self, slot: usize) {
        let class = self.players[slot].class;
        let barricade = if class == 4 {
            match self.barricade_placement(slot) {
                Some(placement) => Some(placement),
                None => return,
            }
        } else {
            None
        };
        let player = &mut self.players[slot];
        player.ability_cooldown = ABILITY_COOLDOWNS[class as usize];
        player.spawn_protection = 0;
        let (position, yaw, pitch) = (player.position, player.yaw, player.pitch);
        self.events.push(Event::AbilityUsed { slot, class });
        let eye = position.offset(Vec3::new(0, 0, EYE_HEIGHT));
        match class {
            0 => {
                // Kage-no-kamae: the stance replaces guard, attack and reload.
                player.stance_ticks = 24;
                player.guarding = false;
                player.guard_ticks = 0;
                player.charge = 0;
                player.charge_weapon = u8::MAX;
                player.reload_ticks = 0;
            }
            1 => {
                // Utsusemi: the decoy stays where the dash starts.
                self.spawn_entity(
                    slot,
                    EntityKind::Decoy,
                    position,
                    DECOY_HEALTH,
                    RADIUS,
                    RADIUS,
                );
                let to = position.offset(math::scale_q15(math::direction(yaw, 0), 2000));
                self.players[slot].position = self.safe_motion(position, to);
            }
            2 => {
                // Mato-ire: a 45 m hitscan-rule ray; only a player stop marks.
                let to = eye.offset(math::scale_q15(math::direction(yaw, pitch), 45_000));
                if let Some(RayStop::Player(target)) = self.ray_stop(slot, eye, to, false, false) {
                    self.players[target].marked_ticks = 300;
                    self.events.push(Event::Marked {
                        marker: slot,
                        target,
                    });
                }
            }
            3 => {
                let centre = self.fire_pot_centre(eye, yaw, pitch);
                self.spawn_entity(slot, EntityKind::FireZone, centre, 0, 2500, 2500);
            }
            4 => {
                if let Some((centre, half_x, half_y)) = barricade {
                    self.spawn_entity(
                        slot,
                        EntityKind::Barricade,
                        centre,
                        BARRICADE_HEALTH,
                        half_x,
                        half_y,
                    );
                }
            }
            _ => {
                // Yakuen: the first-release-6 area heal, then a ward.
                let team = self.players[slot].team;
                let mut healed = Vec::new();
                for (other, p) in self.players.iter_mut().enumerate() {
                    if p.alive
                        && (other == slot || (self.config.mode.team() && p.team == team))
                        && p.position.distance_squared(position) <= 6000_i64 * 6000
                    {
                        let before = p.health;
                        p.health = (p.health + 35).min(catalog::CLASSES[p.class as usize].health);
                        if p.health > before {
                            healed.push((other, p.health - before));
                        }
                    }
                }
                self.events
                    .extend(healed.into_iter().map(|(target, amount)| Event::Healed {
                        healer: slot,
                        target,
                        amount,
                        weapon: None,
                    }));
                self.spawn_entity(slot, EntityKind::Ward, position, 0, 4000, 4000);
            }
        }
    }

    /// §6.4: the pot flies 9000 mm from the eye and lands on the first wall
    /// or barricade (pulled back 46603/2^20 of the throw, about 400 mm) or the
    /// floor, whichever comes first, else at the end of the throw.
    fn fire_pot_centre(&self, eye: Vec3, yaw: u16, pitch: i16) -> Vec3 {
        let end = eye.offset(math::scale_q15(math::direction(yaw, pitch), 9000));
        let wall = self
            .solids(None)
            .filter_map(|w| w.intersect(eye, end))
            .min();
        let floor =
            (end.z < 0).then(|| (i64::from(eye.z) << 20) / (i64::from(eye.z) - i64::from(end.z)));
        let t = match (wall, floor) {
            (Some(wall), floor) if floor.is_none_or(|floor| wall <= floor) => (wall - 46603).max(0),
            (_, Some(floor)) => floor,
            _ => 1 << 20,
        };
        let d = end.delta(eye);
        Vec3::new(
            eye.x + (i64::from(d.x) * t / (1 << 20)) as i32,
            eye.y + (i64::from(d.y) * t / (1 << 20)) as i32,
            0,
        )
    }

    /// §6.5: the barricade box 1500 mm ahead, turned across the facing axis,
    /// and whether it may be placed. The owner's current barricade, which a
    /// valid placement replaces, is ignored by the overlap and path tests.
    fn barricade_placement(&self, slot: usize) -> Option<(Vec3, i32, i32)> {
        let player = &self.players[slot];
        let facing = math::direction(player.yaw, 0);
        let reach = math::scale_q15(facing, 1500);
        let centre = Vec3::new(player.position.x + reach.x, player.position.y + reach.y, 0);
        let (half_x, half_y) = if facing.x.abs() >= facing.y.abs() {
            (200, 1200)
        } else {
            (1200, 200)
        };
        let bounds = Aabb {
            min: Vec3::new(centre.x - half_x, centre.y - half_y, 0),
            max: Vec3::new(
                centre.x + half_x,
                centre.y + half_y,
                EntityKind::Barricade.height(),
            ),
        };
        let own = self
            .entities
            .iter()
            .find(|e| e.owner == slot && e.kind == EntityKind::Barricade)
            .map(|e| e.id);
        let arena = self.arena();
        let inside = arena.bounds.contains(bounds.min.x, bounds.min.y)
            && arena.bounds.contains(bounds.max.x, bounds.max.y);
        let clear = !self.solids(own).any(|solid| solid.overlaps(bounds))
            && !(0..self.players.len())
                .any(|other| self.players[other].alive && self.body(other).overlaps(bounds))
            && !arena
                .spawns()
                .any(|spawn| body_at(spawn.position()).expanded(500, 0).overlaps(bounds))
            && !arena
                .hazards
                .iter()
                .any(|hazard| hazard.volume.overlaps(bounds));
        let reachable = !self.blocked_except(
            player.position.offset(Vec3::new(0, 0, 800)),
            centre.offset(Vec3::new(0, 0, 800)),
            own,
        );
        (inside && clear && reachable).then_some((centre, half_x, half_y))
    }

    /// Spawn one entity on the floor, first replacing the owner's live entity
    /// of the same kind. Ids ascend, so the list stays in id order.
    fn spawn_entity(
        &mut self,
        owner: usize,
        kind: EntityKind,
        position: Vec3,
        health: i32,
        half_x: i32,
        half_y: i32,
    ) {
        self.remove_entities(owner, Some(kind), RemovalCause::Replaced);
        let id = self.next_entity_id;
        self.next_entity_id += 1;
        self.entities.push(Entity {
            id,
            kind,
            owner,
            team: self.players[owner].team,
            position: Vec3::new(position.x, position.y, 0),
            yaw: self.players[owner].yaw,
            health,
            age: 0,
            half_x,
            half_y,
        });
        self.events.push(Event::EntitySpawned { id, kind, owner });
    }

    /// Remove `owner`'s entities (of one kind, or all) in id order.
    pub(super) fn remove_entities(
        &mut self,
        owner: usize,
        kind: Option<EntityKind>,
        cause: RemovalCause,
    ) {
        let entities = std::mem::take(&mut self.entities);
        for e in entities {
            if e.owner == owner && kind.is_none_or(|kind| kind == e.kind) {
                self.removed_entities.push(e);
                self.events.push(Event::EntityDestroyed {
                    id: e.id,
                    kind: e.kind,
                    owner,
                    cause,
                });
            } else {
                self.entities.push(e);
            }
        }
    }

    /// §2 phase 7: in id order each entity ages, a fire zone due to pulse
    /// queues its damage after this tick's blasts, and an entity that reached
    /// its lifetime expires.
    pub(super) fn entity_phase(&mut self, damage: &mut Vec<PendingDamage>) {
        let mut index = 0;
        while index < self.entities.len() {
            self.entities[index].age += 1;
            let e = self.entities[index];
            if e.kind == EntityKind::FireZone
                && (30..=290).contains(&e.age)
                && (e.age - 30).is_multiple_of(20)
            {
                damage.extend(self.fire_pulse(&e));
            }
            if e.age >= e.kind.lifetime() {
                self.entities.remove(index);
                self.removed_entities.push(e);
                self.events.push(Event::EntityDestroyed {
                    id: e.id,
                    kind: e.kind,
                    owner: e.owner,
                    cause: RemovalCause::Expired,
                });
            } else {
                index += 1;
            }
        }
    }

    /// §6.4: 8 undirected damage to every living, unprotected enemy standing
    /// low in the zone with a clear line from the zone floor.
    fn fire_pulse(&self, zone: &Entity) -> Vec<PendingDamage> {
        let lift = Vec3::new(0, 0, 300);
        let source = zone.position.offset(lift);
        (0..self.players.len())
            .filter(|&slot| {
                let p = &self.players[slot];
                p.alive
                    && p.spawn_protection == 0
                    && self.entity_enemy(slot, zone)
                    && p.position.horizontal_distance_squared(zone.position)
                        <= i64::from(zone.half_x) * i64::from(zone.half_x)
                    && p.position.z <= 1000
                    && !self.blocked(source, p.position.offset(lift))
            })
            .map(|victim| PendingDamage {
                source: Source::Player(zone.owner),
                victim,
                amount: 8,
                weapon: 255,
                origin: None,
                kind: DamageKind::Zone,
                penetrating: false,
            })
            .collect()
    }

    /// §6.1: the first negated hit of a stance ripostes for 90 when the
    /// attacker still stands within 3000 mm horizontally in line of sight.
    pub(super) fn riposte(&mut self, samurai: usize, target: usize) -> Option<PendingDamage> {
        let lift = Vec3::new(0, 0, EYE_HEIGHT);
        let eye = self.players[samurai].position.offset(lift);
        let target_eye = self.players[target].position.offset(lift);
        if !self.players[target].alive
            || self.players[target].health <= 0
            || eye.horizontal_distance_squared(target_eye) > 3000_i64 * 3000
            || self.blocked(eye, target_eye)
        {
            return None;
        }
        self.events.push(Event::Riposte {
            slot: samurai,
            target,
        });
        Some(PendingDamage {
            source: Source::Player(samurai),
            victim: target,
            amount: 90,
            weapon: 0,
            origin: Some(eye),
            kind: DamageKind::Riposte,
            penetrating: false,
        })
    }

    /// §2 phase 11: entity damage and repair in queue order. Entries for an
    /// entity that is gone or already emptied are skipped. Emptied entities
    /// are removed after the batch, in id order.
    pub(super) fn apply_entity_hits(&mut self, hits: &[EntityHit]) {
        let mut emptied = Vec::new();
        for &hit in hits {
            let id = match hit {
                EntityHit::Damage { id, .. } | EntityHit::Repair { id, .. } => id,
            };
            let Ok(index) = self.entities.binary_search_by_key(&id, |e| e.id) else {
                continue;
            };
            let entity = &mut self.entities[index];
            if entity.health <= 0 {
                continue;
            }
            match hit {
                EntityHit::Damage {
                    attacker, amount, ..
                } => {
                    let dealt = amount.min(entity.health);
                    entity.health -= dealt;
                    if entity.health == 0 {
                        emptied.push((id, attacker));
                    }
                    if dealt > 0 {
                        self.events.push(Event::EntityDamaged {
                            id,
                            attacker,
                            amount: dealt,
                        });
                    }
                }
                EntityHit::Repair { repairer, .. } => {
                    let restored = 45.min(BARRICADE_HEALTH - entity.health);
                    entity.health += restored;
                    if restored > 0 {
                        self.events.push(Event::EntityRepaired {
                            id,
                            repairer,
                            amount: restored,
                        });
                    }
                }
            }
        }
        emptied.sort_unstable();
        for (id, by) in emptied {
            if let Ok(index) = self.entities.binary_search_by_key(&id, |e| e.id) {
                let e = self.entities.remove(index);
                self.removed_entities.push(e);
                self.events.push(Event::EntityDestroyed {
                    id,
                    kind: e.kind,
                    owner: e.owner,
                    cause: RemovalCause::Destroyed { by },
                });
            }
        }
    }
}
