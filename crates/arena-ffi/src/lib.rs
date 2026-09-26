//! Native C ABI 4 for Unreal. Foreign callers own pointer validity and serialize
//! per-handle access. No function signs a wallet transaction or qualifies proofs.
use arena_bots::{Bots, Difficulty};
use arena_core::{
    ABI_VERSION, catalog,
    maps::Arena,
    math::Vec3,
    simulation::{
        self, ABILITY_COOLDOWNS, CONTROL_CAPTURE, CONTROL_TARGET, Config, Entity, Event, Input,
        Mode, OBJECTIVE_UNLOCK_TICK, PAYLOAD_PUSH_RADIUS, PAYLOAD_ROLLBACK_DELAY, Participant,
        RemovalCause, Winner, World,
    },
};
use std::panic::{AssertUnwindSafe, catch_unwind};

pub struct ArenaHandle {
    world: World,
    /// Practice bot memories (crates/arena-bots): not kernel state and never
    /// part of the state hash.
    bots: Bots,
}
/// `ARENA_NONE`: an absent slot, weapon, class or team.
pub const NONE: u32 = u32::MAX;
/// `ARENA_EVENT_*` kinds. 1-5 keep their ABI 3 meaning.
pub const EVENT_SHOT: u32 = 1;
pub const EVENT_DAMAGE: u32 = 2;
pub const EVENT_DEATH: u32 = 3;
pub const EVENT_RESPAWN: u32 = 4;
pub const EVENT_TERMINAL: u32 = 5;
pub const EVENT_GUARDED: u32 = 6;
pub const EVENT_HEALED: u32 = 7;
pub const EVENT_ABILITY: u32 = 8;
pub const EVENT_MARKED: u32 = 9;
pub const EVENT_RIPOSTE: u32 = 10;
pub const EVENT_ENTITY_SPAWNED: u32 = 11;
pub const EVENT_ENTITY_DAMAGED: u32 = 12;
pub const EVENT_ENTITY_REPAIRED: u32 = 13;
pub const EVENT_ENTITY_DESTROYED: u32 = 14;
pub const EVENT_HAZARD_DAMAGE: u32 = 15;
pub const EVENT_OBJECTIVE_CAPTURED: u32 = 16;
pub const EVENT_OVERTIME: u32 = 17;
pub const EVENT_CHECKPOINT: u32 = 18;
pub const EVENT_MATCH_WINNER: u32 = 19;
/// `ARENA_BOT_*` practice difficulties.
pub const BOT_NOVICE: u32 = Difficulty::Novice as u32;
pub const BOT_STANDARD: u32 = Difficulty::Standard as u32;
pub const BOT_VETERAN: u32 = Difficulty::Veteran as u32;
pub const BOT_MASTER: u32 = Difficulty::Master as u32;
#[repr(C)]
pub struct ArenaConfig {
    pub abi_version: u32,
    pub mode: u32,
    pub map_id: u32,
    pub max_ticks: u32,
    pub base_bond: u64,
    pub player_count: u32,
    pub offline: u32,
}
#[repr(C)]
pub struct ArenaParticipant {
    pub slot: u32,
    pub team: u32,
    pub class_id: u32,
    pub weapon_id: u32,
    pub bond: u64,
    pub special_entitled: u32,
    pub reserved: u32,
}
#[repr(C)]
pub struct ArenaInput {
    pub slot: u32,
    pub buttons: u32,
    pub move_x: i16,
    pub move_y: i16,
    pub yaw: u16,
    pub pitch: i16,
}
#[repr(C)]
#[derive(Default)]
pub struct ArenaPlayerSnapshot {
    pub x: i32,
    pub y: i32,
    pub z: i32,
    pub health: i32,
    pub stamina: i32,
    pub slot: u32,
    pub team: u32,
    pub class_id: u32,
    pub weapon_id: u32,
    pub alive: u32,
    pub exhausted: u32,
    pub respawn_ticks: u32,
    pub initial_bond: u64,
    pub remaining_bond: u64,
    pub earnings: u64,
    pub kills: u32,
    pub deaths: u32,
}
#[repr(C)]
#[derive(Default)]
pub struct ArenaSnapshot {
    pub abi_version: u32,
    pub tick: u32,
    pub player_count: u32,
    pub terminal: u32,
    pub proof_qualified: u32,
    pub event_count: u32,
    pub deposited: u64,
    pub remaining: u64,
    pub earnings: u64,
}

#[repr(C)]
#[derive(Default)]
pub struct ArenaMapInfo {
    pub min_x: i32,
    pub min_y: i32,
    pub max_x: i32,
    pub max_y: i32,
    pub floor_z: i32,
    pub wall_count: u32,
    pub player_radius: i32,
    pub player_height: i32,
    pub eye_height: i32,
    pub control_x: i32,
    pub control_y: i32,
    pub control_radius: i32,
    pub route_point_count: u32,
    pub route_length: i32,
    pub checkpoint_0: i32,
    pub checkpoint_1: i32,
    pub checkpoint_2: i32,
    pub push_radius: i32,
    pub hazard_count: u32,
}
#[repr(C)]
#[derive(Default)]
pub struct ArenaMapWall {
    pub min_x: i32,
    pub min_y: i32,
    pub min_z: i32,
    pub max_x: i32,
    pub max_y: i32,
    pub max_z: i32,
}
#[repr(C)]
#[derive(Default)]
pub struct ArenaMapPoint {
    pub x: i32,
    pub y: i32,
}
#[repr(C)]
#[derive(Default)]
pub struct ArenaMapHazard {
    pub kind: u32,
    pub damage: i32,
    pub period: u32,
    pub min_x: i32,
    pub min_y: i32,
    pub min_z: i32,
    pub max_x: i32,
    pub max_y: i32,
    pub max_z: i32,
}
#[repr(C)]
#[derive(Default)]
pub struct ArenaPlayerPresentation {
    pub yaw: u16,
    pub pitch: i16,
    pub cooldown_ticks: u32,
    pub max_health: i32,
    pub guarding: u32,
    pub spawn_protection_ticks: u32,
    pub ability_cooldown_ticks: u32,
    pub ammo: u32,
    pub magazine: u32,
    pub reload_ticks: u32,
    pub charge_ticks_current: u32,
    pub charge_ticks_required: u32,
    pub guard_ticks: u32,
    pub ability_cooldown_total: u32,
    pub stance_ticks: u32,
    pub marked_ticks: u32,
    pub pending_class: u32,
    pub pending_weapon: u32,
    pub admitted_special: u32,
}
#[repr(C)]
#[derive(Default)]
pub struct ArenaWeaponSpec {
    pub id: u32,
    pub kind: u32,
    pub damage: i32,
    pub range_mm: i32,
    pub cooldown_ticks: u32,
    pub stamina_cost: i32,
    pub projectile_mm_tick: i32,
    pub blast_mm: i32,
    pub arming_mm: i32,
    pub charge_ticks: u32,
    pub magazine: u32,
    pub reload_ticks: u32,
}
#[repr(C)]
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct ArenaEvent {
    pub tick: u32,
    pub kind: u32,
    pub actor_slot: u32,
    pub target_slot: u32,
    pub weapon_id: u32,
    pub x: i32,
    pub y: i32,
    pub z: i32,
    pub value: i32,
    pub entity_id: u32,
    pub entity_kind: u32,
    pub detail: u32,
}
#[repr(C)]
#[derive(Default)]
pub struct ArenaProjectileSnapshot {
    pub id: u32,
    pub owner_slot: u32,
    pub weapon_id: u32,
    pub x: i32,
    pub y: i32,
    pub z: i32,
}
#[repr(C)]
#[derive(Debug, Default, PartialEq, Eq)]
pub struct ArenaEntitySnapshot {
    pub id: u32,
    pub kind: u32,
    pub owner_slot: u32,
    pub team: u32,
    pub x: i32,
    pub y: i32,
    pub z: i32,
    pub yaw: u32,
    pub health: i32,
    pub max_health: i32,
    pub age: u32,
    pub lifetime: u32,
    pub half_x: i32,
    pub half_y: i32,
    pub height: i32,
}
#[repr(C)]
#[derive(Debug, Default, PartialEq, Eq)]
pub struct ArenaObjectiveSnapshot {
    pub mode: u32,
    pub unlock_tick: u32,
    pub score_0: u32,
    pub score_1: u32,
    pub score_target: u32,
    pub control_owner: u32,
    pub control_progress: i32,
    pub control_capture: i32,
    pub control_team_0: u32,
    pub control_team_1: u32,
    pub contested: u32,
    pub overtime: u32,
    pub payload_progress: i32,
    pub payload_length: i32,
    pub payload_checkpoints: u32,
    pub payload_idle: u32,
    pub payload_rollback_delay: u32,
    pub payload_x: i32,
    pub payload_y: i32,
    pub payload_z: i32,
    pub payload_attackers: u32,
    pub payload_defenders: u32,
    pub winner_kind: u32,
    pub winner_value: u32,
}

fn arena(map_id: u32) -> Option<&'static Arena> {
    u8::try_from(map_id).ok().and_then(Arena::get)
}
/// `ARENA_WINNER_*` kind and value, the §12 state-hash encoding.
fn winner_code(winner: Option<Winner>) -> (u32, u32) {
    match winner {
        None => (0, 0),
        Some(Winner::Team(team)) => (1, u32::from(team)),
        Some(Winner::Slot(slot)) => (2, slot as u32),
        Some(Winner::Draw) => (3, 0),
    }
}
/// `ARENA_REMOVAL_*` cause and the slot that caused it, if any.
fn removal_code(cause: RemovalCause) -> (u32, u32) {
    match cause {
        RemovalCause::Expired => (0, NONE),
        RemovalCause::Destroyed { by } => (1, by as u32),
        RemovalCause::Replaced => (2, NONE),
        RemovalCause::OwnerDied => (3, NONE),
        RemovalCause::OwnerExhausted => (4, NONE),
    }
}
fn entity_snapshot(e: &Entity) -> ArenaEntitySnapshot {
    let bounds = e.bounds();
    ArenaEntitySnapshot {
        id: e.id,
        kind: e.kind as u32,
        owner_slot: e.owner as u32,
        team: u32::from(e.team),
        x: e.position.x,
        y: e.position.y,
        z: e.position.z,
        yaw: u32::from(e.yaw),
        health: e.health,
        max_health: e.kind.max_health(),
        age: u32::from(e.age),
        lifetime: u32::from(e.kind.lifetime()),
        half_x: e.half_x,
        half_y: e.half_y,
        height: bounds.max.z - bounds.min.z,
    }
}

/// # Safety
/// Output must be aligned, writable storage for one ArenaMapInfo.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_map_info(map_id: u32, out: *mut ArenaMapInfo) -> i32 {
    let Some(arena) = arena(map_id) else {
        return 1;
    };
    if out.is_null() {
        return 1;
    }
    unsafe {
        out.write(ArenaMapInfo {
            min_x: arena.bounds.min_x,
            min_y: arena.bounds.min_y,
            max_x: arena.bounds.max_x,
            max_y: arena.bounds.max_y,
            floor_z: 0,
            wall_count: arena.walls.len() as u32,
            player_radius: simulation::RADIUS,
            player_height: simulation::HEIGHT,
            eye_height: simulation::EYE_HEIGHT,
            control_x: arena.control.x,
            control_y: arena.control.y,
            control_radius: arena.control.radius,
            route_point_count: arena.route.len() as u32,
            route_length: arena.route_length(),
            checkpoint_0: arena.checkpoints[0],
            checkpoint_1: arena.checkpoints[1],
            checkpoint_2: arena.checkpoints[2],
            push_radius: PAYLOAD_PUSH_RADIUS,
            hazard_count: arena.hazards.len() as u32,
        })
    };
    0
}
/// # Safety
/// Output must be aligned, writable storage for one ArenaMapWall.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_map_wall(map_id: u32, index: u32, out: *mut ArenaMapWall) -> i32 {
    let Some(w) =
        arena(map_id).and_then(|arena| arena.walls.get(index as usize).map(|wall| wall.aabb))
    else {
        return 1;
    };
    if out.is_null() {
        return 1;
    }
    unsafe {
        out.write(ArenaMapWall {
            min_x: w.min.x,
            min_y: w.min.y,
            min_z: w.min.z,
            max_x: w.max.x,
            max_y: w.max.y,
            max_z: w.max.z,
        })
    };
    0
}
/// # Safety
/// Output must be aligned, writable storage for one ArenaMapPoint.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_map_route_point(
    map_id: u32,
    index: u32,
    out: *mut ArenaMapPoint,
) -> i32 {
    let Some(&(x, y)) = arena(map_id).and_then(|arena| arena.route.get(index as usize)) else {
        return 1;
    };
    if out.is_null() {
        return 1;
    }
    unsafe { out.write(ArenaMapPoint { x, y }) };
    0
}
/// # Safety
/// Output must be aligned, writable storage for one ArenaMapHazard.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_map_hazard(
    map_id: u32,
    index: u32,
    out: *mut ArenaMapHazard,
) -> i32 {
    let Some(h) = arena(map_id).and_then(|arena| arena.hazards.get(index as usize)) else {
        return 1;
    };
    if out.is_null() {
        return 1;
    }
    let v = h.volume;
    unsafe {
        out.write(ArenaMapHazard {
            kind: h.kind as u32,
            damage: h.damage,
            period: u32::from(h.period),
            min_x: v.min.x,
            min_y: v.min.y,
            min_z: v.min.z,
            max_x: v.max.x,
            max_y: v.max.y,
            max_z: v.max.z,
        })
    };
    0
}
/// # Safety
/// Output must be aligned, writable storage for one ArenaWeaponSpec.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_weapon_spec(weapon_id: u32, out: *mut ArenaWeaponSpec) -> i32 {
    if out.is_null() {
        return 1;
    }
    let Some(w) = catalog::WEAPONS.get(weapon_id as usize) else {
        return 1;
    };
    let kind = match w.kind {
        catalog::AttackKind::Melee => 0,
        catalog::AttackKind::Hitscan => 1,
        catalog::AttackKind::Projectile => 2,
    };
    unsafe {
        out.write(ArenaWeaponSpec {
            id: w.id as u32,
            kind,
            damage: w.damage,
            range_mm: w.range_mm,
            cooldown_ticks: w.cooldown as u32,
            stamina_cost: w.stamina,
            projectile_mm_tick: w.projectile_mm_tick,
            blast_mm: w.blast_mm,
            arming_mm: w.arming_mm,
            charge_ticks: w.charge_ticks as u32,
            magazine: w.magazine as u32,
            reload_ticks: w.reload_ticks as u32,
        })
    };
    0
}
/// # Safety
/// Live handle and aligned writable output; no concurrent handle mutation.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_player_presentation(
    handle: *const ArenaHandle,
    slot: u32,
    out: *mut ArenaPlayerPresentation,
) -> i32 {
    if handle.is_null() || out.is_null() {
        return 1;
    }
    let Some(p) = (unsafe { &*handle }).world.players.get(slot as usize) else {
        return 1;
    };
    let charge_spec = catalog::WEAPONS
        .get(p.charge_weapon as usize)
        .unwrap_or(&catalog::WEAPONS[p.weapon as usize]);
    let charge_ticks_current = if p.alive && p.charge_weapon == charge_spec.id {
        p.charge.min(charge_spec.charge_ticks) as u32
    } else {
        0
    };
    unsafe {
        out.write(ArenaPlayerPresentation {
            yaw: p.yaw,
            pitch: p.pitch,
            cooldown_ticks: p.attack_cooldown as u32,
            max_health: catalog::CLASSES[p.class as usize].health,
            guarding: p.guarding as u32,
            spawn_protection_ticks: p.spawn_protection as u32,
            ability_cooldown_ticks: p.ability_cooldown as u32,
            ammo: p.ammo as u32,
            magazine: catalog::WEAPONS[p.weapon as usize].magazine as u32,
            reload_ticks: p.reload_ticks as u32,
            charge_ticks_current,
            charge_ticks_required: charge_spec.charge_ticks as u32,
            guard_ticks: u32::from(p.guard_ticks),
            ability_cooldown_total: u32::from(ABILITY_COOLDOWNS[p.class as usize]),
            stance_ticks: u32::from(p.stance_ticks),
            marked_ticks: u32::from(p.marked_ticks),
            pending_class: p
                .pending_loadout
                .map_or(NONE, |(class, _)| u32::from(class)),
            pending_weapon: p
                .pending_loadout
                .map_or(NONE, |(_, weapon)| u32::from(weapon)),
            admitted_special: p.admitted_special.map_or(NONE, u32::from),
        })
    };
    0
}
/// ABI 4 projection of one kernel event, read after the step (docs/combat-rules.md
/// §4.3). Every kernel event has an exported kind. Deliberately exhaustive: a
/// new kernel event must choose an export here. `None` means the world lost an
/// entity an event names, which the kernel never does.
fn export_event(w: &World, event: &Event) -> Option<ArenaEvent> {
    let mut result = ArenaEvent {
        tick: w.tick.saturating_sub(1),
        actor_slot: NONE,
        target_slot: NONE,
        weapon_id: NONE,
        ..ArenaEvent::default()
    };
    let feet = |slot: usize| w.players[slot].position;
    let arena = w.arena();
    let control = Vec3::new(arena.control.x, arena.control.y, 0);
    // An entity event reads the entity's live record, or the record of this
    // step's removal: an entity can spawn and leave within one step.
    let entity = |result: &mut ArenaEvent, kind: u32, id: u32, actor: u32| {
        let e = w
            .entity(id)
            .or_else(|| w.removed_entities.iter().find(|e| e.id == id))?;
        result.kind = kind;
        result.actor_slot = actor;
        result.target_slot = e.owner as u32;
        result.entity_id = id;
        result.entity_kind = e.kind as u32;
        Some(e.position)
    };
    let position = match event {
        &Event::Shot { slot, weapon } => {
            result.kind = EVENT_SHOT;
            result.actor_slot = slot as u32;
            result.weapon_id = u32::from(weapon);
            feet(slot).offset(Vec3::new(0, 0, simulation::EYE_HEIGHT))
        }
        &Event::Damage {
            attacker,
            victim,
            amount,
        } => {
            result.kind = EVENT_DAMAGE;
            result.actor_slot = attacker as u32;
            result.target_slot = victim as u32;
            result.value = amount;
            feet(victim)
        }
        &Event::Death { victim, killer, .. } => {
            result.kind = EVENT_DEATH;
            result.target_slot = victim as u32;
            result.actor_slot = killer.map_or(NONE, |slot| slot as u32);
            result.detail = u32::from(w.exhausted(victim));
            feet(victim)
        }
        &Event::Respawn { slot } => {
            result.kind = EVENT_RESPAWN;
            result.target_slot = slot as u32;
            result.weapon_id = u32::from(w.players[slot].weapon);
            result.detail = u32::from(w.players[slot].class);
            feet(slot)
        }
        Event::Terminal => {
            result.kind = EVENT_TERMINAL;
            Vec3::default()
        }
        &Event::Guarded {
            attacker,
            victim,
            weapon,
            parried,
            prevented,
        } => {
            result.kind = EVENT_GUARDED;
            result.actor_slot = attacker as u32;
            result.target_slot = victim as u32;
            result.weapon_id = u32::from(weapon);
            result.value = prevented;
            result.detail = u32::from(parried);
            feet(victim)
        }
        &Event::Healed {
            healer,
            target,
            amount,
            weapon,
        } => {
            result.kind = EVENT_HEALED;
            result.actor_slot = healer as u32;
            result.target_slot = target as u32;
            result.weapon_id = weapon.map_or(NONE, u32::from);
            result.value = amount;
            feet(target)
        }
        &Event::AbilityUsed { slot, class } => {
            result.kind = EVENT_ABILITY;
            result.actor_slot = slot as u32;
            result.detail = u32::from(class);
            feet(slot)
        }
        &Event::Marked { marker, target } => {
            result.kind = EVENT_MARKED;
            result.actor_slot = marker as u32;
            result.target_slot = target as u32;
            feet(target)
        }
        &Event::Riposte { slot, target } => {
            result.kind = EVENT_RIPOSTE;
            result.actor_slot = slot as u32;
            result.target_slot = target as u32;
            feet(target)
        }
        &Event::EntitySpawned { id, owner, .. } => {
            entity(&mut result, EVENT_ENTITY_SPAWNED, id, owner as u32)?
        }
        &Event::EntityDamaged {
            id,
            attacker,
            amount,
        } => {
            result.value = amount;
            entity(&mut result, EVENT_ENTITY_DAMAGED, id, attacker as u32)?
        }
        &Event::EntityRepaired {
            id,
            repairer,
            amount,
        } => {
            result.value = amount;
            entity(&mut result, EVENT_ENTITY_REPAIRED, id, repairer as u32)?
        }
        &Event::EntityDestroyed { id, cause, .. } => {
            let (detail, actor) = removal_code(cause);
            result.detail = detail;
            entity(&mut result, EVENT_ENTITY_DESTROYED, id, actor)?
        }
        &Event::EnvironmentalDamage {
            victim,
            hazard,
            amount,
        } => {
            result.kind = EVENT_HAZARD_DAMAGE;
            result.target_slot = victim as u32;
            result.value = amount;
            result.detail = u32::from(hazard);
            feet(victim)
        }
        &Event::ObjectiveCaptured { team } => {
            result.kind = EVENT_OBJECTIVE_CAPTURED;
            result.detail = u32::from(team);
            control
        }
        Event::OvertimeStarted => {
            result.kind = EVENT_OVERTIME;
            control
        }
        &Event::CheckpointReached { index } => {
            let distance = *arena.checkpoints.get(usize::from(index))?;
            result.kind = EVENT_CHECKPOINT;
            result.value = distance;
            result.detail = u32::from(index);
            arena.route_point(distance)
        }
        &Event::MatchWinner { winner } => {
            let (kind, value) = winner_code(Some(winner));
            result.kind = EVENT_MATCH_WINNER;
            result.detail = kind;
            result.value = value as i32;
            Vec3::default()
        }
    };
    result.x = position.x;
    result.y = position.y;
    result.z = position.z;
    Some(result)
}
/// # Safety
/// Live handle and aligned writable output; no concurrent handle mutation.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_event(
    handle: *const ArenaHandle,
    index: u32,
    out: *mut ArenaEvent,
) -> i32 {
    if handle.is_null() || out.is_null() {
        return 1;
    }
    let w = &(unsafe { &*handle }).world;
    let Some(event) = w.events.get(index as usize) else {
        return 1;
    };
    let Some(result) = export_event(w, event) else {
        return 2;
    };
    unsafe { out.write(result) };
    0
}
/// # Safety
/// Live handle and aligned writable count storage; no concurrent mutation.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_projectile_count(handle: *const ArenaHandle, out: *mut u32) -> i32 {
    if handle.is_null() || out.is_null() {
        return 1;
    }
    unsafe { out.write((&*handle).world.projectiles.len() as u32) };
    0
}
/// # Safety
/// Live handle and aligned writable output; no concurrent mutation.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_projectile(
    handle: *const ArenaHandle,
    index: u32,
    out: *mut ArenaProjectileSnapshot,
) -> i32 {
    if handle.is_null() || out.is_null() {
        return 1;
    }
    let Some(p) = (unsafe { &*handle }).world.projectiles.get(index as usize) else {
        return 1;
    };
    unsafe {
        out.write(ArenaProjectileSnapshot {
            id: p.id,
            owner_slot: p.owner as u32,
            weapon_id: p.weapon as u32,
            x: p.position.x,
            y: p.position.y,
            z: p.position.z,
        })
    };
    0
}
/// # Safety
/// Live handle and aligned writable count storage; no concurrent mutation.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_entity_count(handle: *const ArenaHandle, out: *mut u32) -> i32 {
    if handle.is_null() || out.is_null() {
        return 1;
    }
    unsafe { out.write((&*handle).world.entities.len() as u32) };
    0
}
/// # Safety
/// Live handle and aligned writable output; no concurrent mutation.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_entity(
    handle: *const ArenaHandle,
    index: u32,
    out: *mut ArenaEntitySnapshot,
) -> i32 {
    if handle.is_null() || out.is_null() {
        return 1;
    }
    let Some(e) = (unsafe { &*handle }).world.entities.get(index as usize) else {
        return 1;
    };
    unsafe { out.write(entity_snapshot(e)) };
    0
}
/// # Safety
/// Live handle and aligned writable output; no concurrent mutation.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_objective(
    handle: *const ArenaHandle,
    out: *mut ArenaObjectiveSnapshot,
) -> i32 {
    if handle.is_null() || out.is_null() {
        return 1;
    }
    let w = &unsafe { &*handle }.world;
    let arena = w.arena();
    let (winner_kind, winner_value) = winner_code(w.winner);
    let mut o = ArenaObjectiveSnapshot {
        mode: w.config.mode as u32,
        unlock_tick: OBJECTIVE_UNLOCK_TICK,
        control_owner: NONE,
        winner_kind,
        winner_value,
        ..ArenaObjectiveSnapshot::default()
    };
    // Head counts use the kernel's own objective rule (§8): living players
    // within the horizontal radius, by team.
    match w.config.mode {
        Mode::Control => {
            let c = arena.control;
            let [team_0, team_1] = w.count_near(Vec3::new(c.x, c.y, 0), c.radius);
            o.score_0 = w.score[0];
            o.score_1 = w.score[1];
            o.score_target = CONTROL_TARGET;
            o.control_owner = w.control_owner.map_or(NONE, u32::from);
            o.control_progress = w.control_progress;
            o.control_capture = CONTROL_CAPTURE;
            o.control_team_0 = team_0 as u32;
            o.control_team_1 = team_1 as u32;
            o.contested = u32::from(team_0 > 0 && team_1 > 0);
            o.overtime = u32::from(w.overtime);
        }
        Mode::Payload => {
            let at = arena.route_point(w.payload_progress);
            let [attackers, defenders] = w.count_near(at, PAYLOAD_PUSH_RADIUS);
            o.payload_progress = w.payload_progress;
            o.payload_length = arena.route_length();
            o.payload_checkpoints = u32::from(w.payload_checkpoints);
            o.payload_idle = u32::from(w.payload_idle);
            o.payload_rollback_delay = u32::from(PAYLOAD_ROLLBACK_DELAY);
            o.payload_x = at.x;
            o.payload_y = at.y;
            o.payload_z = at.z;
            o.payload_attackers = attackers as u32;
            o.payload_defenders = defenders as u32;
            o.contested = u32::from(attackers > 0 && defenders > 0);
        }
        Mode::FreeForAll | Mode::Melee => {}
    }
    unsafe { out.write(o) };
    0
}

#[unsafe(no_mangle)]
pub extern "C" fn arena_abi_version() -> u32 {
    ABI_VERSION
}
#[unsafe(no_mangle)]
pub extern "C" fn arena_proof_qualified() -> u32 {
    u32::from(arena_core::proof_qualified())
}

/// # Safety
/// `config` and `participants` must point to aligned initialized storage valid
/// for this call; participants must contain `count` entries.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_create(
    config: *const ArenaConfig,
    participants: *const ArenaParticipant,
    count: usize,
) -> *mut ArenaHandle {
    if config.is_null() || participants.is_null() || count == 0 || count > arena_core::MAX_PLAYERS {
        return std::ptr::null_mut();
    }
    catch_unwind(AssertUnwindSafe(|| {
        let c = unsafe { &*config };
        let p = unsafe { std::slice::from_raw_parts(participants, count) };
        if c.abi_version != ABI_VERSION
            || c.player_count as usize != count
            || c.offline > 1
            || c.map_id > 3
        {
            return std::ptr::null_mut();
        }
        let mode = match c.mode {
            0 => Mode::FreeForAll,
            1 => Mode::Control,
            2 => Mode::Payload,
            3 => Mode::Melee,
            _ => return std::ptr::null_mut(),
        };
        let mut roster = Vec::with_capacity(count);
        for (slot, p) in p.iter().enumerate() {
            if p.slot as usize != slot
                || p.team > 1
                || p.class_id > 5
                || p.weapon_id > 17
                || p.special_entitled > 1
                || p.reserved != 0
            {
                return std::ptr::null_mut();
            }
            roster.push(Participant {
                team: p.team as u8,
                class: p.class_id as u8,
                weapon: p.weapon_id as u8,
                bond: p.bond,
                special_entitled: p.special_entitled == 1,
            });
        }
        // The kernel enforces the remaining admission rules (§2.1): player
        // limits per mode and team, class weapons, Melee weapons and bonds.
        match World::new(
            Config {
                mode,
                map: c.map_id as u8,
                max_ticks: c.max_ticks,
                base_bond: c.base_bond,
                offline: c.offline == 1,
            },
            &roster,
        ) {
            Ok(world) => {
                let bots = Bots::new(&world);
                Box::into_raw(Box::new(ArenaHandle { world, bots }))
            }
            Err(_) => std::ptr::null_mut(),
        }
    }))
    .unwrap_or(std::ptr::null_mut())
}
/// # Safety
/// Handle must be live and returned by arena_create; destroy exactly once.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_destroy(handle: *mut ArenaHandle) {
    if !handle.is_null() {
        drop(unsafe { Box::from_raw(handle) });
    }
}
/// # Safety
/// Valid exclusively-owned handle and `count` aligned readable input entries.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_step(
    handle: *mut ArenaHandle,
    inputs: *const ArenaInput,
    count: usize,
) -> i32 {
    if handle.is_null() || inputs.is_null() || count > arena_core::MAX_PLAYERS {
        return 1;
    }
    catch_unwind(AssertUnwindSafe(|| {
        let h = unsafe { &mut *handle };
        let input = unsafe { std::slice::from_raw_parts(inputs, count) };
        if input.len() != h.world.players.len() {
            return 1;
        }
        let mut controls = Vec::with_capacity(count);
        for (slot, i) in input.iter().enumerate() {
            if i.slot as usize != slot {
                return 1;
            }
            controls.push(Input {
                buttons: i.buttons,
                move_x: i.move_x,
                move_y: i.move_y,
                yaw: i.yaw,
                pitch: i.pitch,
            });
        }
        // The kernel validates the canonical input domain (§2.2), including
        // the LOADOUT request's class and index, before changing anything.
        match h.world.step(&controls) {
            Ok(()) => 0,
            Err(_) => 2,
        }
    }))
    .unwrap_or(3)
}
/// A practice bot's input for `slot` on the next step (crates/arena-bots). The
/// bot plans from the current state once per tick; repeated calls before the
/// next step return the same input. Zero-stake handles only: bots never play
/// for bonded value.
///
/// # Safety
/// Valid exclusively-owned handle and aligned writable output storage.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_bot_input(
    handle: *mut ArenaHandle,
    slot: u32,
    difficulty: u32,
    out: *mut ArenaInput,
) -> i32 {
    if handle.is_null() || out.is_null() {
        return 1;
    }
    catch_unwind(AssertUnwindSafe(|| {
        let h = unsafe { &mut *handle };
        let Some(difficulty) = Difficulty::from_code(difficulty) else {
            return 1;
        };
        if slot as usize >= h.world.players.len() || !h.world.config.offline {
            return 1;
        }
        if h.world.terminal {
            return 2;
        }
        let input = h.bots.input(&h.world, slot as usize, difficulty);
        unsafe {
            out.write(ArenaInput {
                slot,
                buttons: input.buttons,
                move_x: input.move_x,
                move_y: input.move_y,
                yaw: input.yaw,
                pitch: input.pitch,
            })
        };
        0
    }))
    .unwrap_or(3)
}
/// # Safety
/// Live handle and aligned writable snapshot storage; no concurrent mutation.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_snapshot(
    handle: *const ArenaHandle,
    out: *mut ArenaSnapshot,
) -> i32 {
    if handle.is_null() || out.is_null() {
        return 1;
    }
    let w = &unsafe { &*handle }.world;
    let snapshot = ArenaSnapshot {
        abi_version: ABI_VERSION,
        tick: w.tick,
        player_count: w.players.len() as u32,
        terminal: w.terminal as u32,
        proof_qualified: arena_proof_qualified(),
        event_count: w.events.len() as u32,
        deposited: w.accounts.iter().map(|a| a.initial).sum(),
        remaining: w.accounts.iter().map(|a| a.remaining).sum(),
        earnings: w.accounts.iter().map(|a| a.earnings).sum(),
    };
    unsafe { out.write(snapshot) };
    0
}
/// # Safety
/// Live handle and aligned writable player storage; no concurrent mutation.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_player(
    handle: *const ArenaHandle,
    slot: u32,
    out: *mut ArenaPlayerSnapshot,
) -> i32 {
    if handle.is_null() || out.is_null() {
        return 1;
    }
    let w = &unsafe { &*handle }.world;
    let Some(p) = w.players.get(slot as usize) else {
        return 1;
    };
    let a = &w.accounts[slot as usize];
    let snapshot = ArenaPlayerSnapshot {
        x: p.position.x,
        y: p.position.y,
        z: p.position.z,
        health: p.health,
        stamina: p.stamina,
        slot,
        team: p.team as u32,
        class_id: p.class as u32,
        weapon_id: p.weapon as u32,
        alive: p.alive as u32,
        exhausted: w.exhausted(slot as usize) as u32,
        respawn_ticks: p.respawn_ticks,
        initial_bond: a.initial,
        remaining_bond: a.remaining,
        earnings: a.earnings,
        kills: a.kills,
        deaths: a.deaths,
    };
    unsafe { out.write(snapshot) };
    0
}
/// # Safety
/// Live handle and at least 32 writable bytes at output; no concurrent mutation.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_state_hash(
    handle: *const ArenaHandle,
    output: *mut u8,
    length: usize,
) -> i32 {
    if handle.is_null() || output.is_null() || length != 32 {
        return 1;
    }
    let hash = unsafe { &*handle }.world.state_hash();
    unsafe { std::ptr::copy_nonoverlapping(hash.as_ptr(), output, 32) };
    0
}

#[cfg(test)]
mod tests;
