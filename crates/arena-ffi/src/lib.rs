//! Native C ABI for Unreal. Foreign callers own pointer validity and serialize
//! per-handle access. No function signs a wallet transaction or qualifies proofs.
use arena_core::{
    ABI_VERSION, catalog,
    maps::Arena,
    math::Vec3,
    simulation::{self, Config, Event, Input, Mode, Participant, World},
};
use std::panic::{AssertUnwindSafe, catch_unwind};

pub struct ArenaHandle {
    world: World,
}
/// FIRE, MELEE, BLOCK, JUMP, ABILITY and RELOAD: the ABI 3 button domain.
const ABI3_BUTTONS: u32 = simulation::FIRE
    | simulation::MELEE
    | simulation::BLOCK
    | simulation::JUMP
    | simulation::ABILITY
    | simulation::RELOAD;
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
#[derive(Default)]
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

/// # Safety
/// Output must be aligned, writable storage for one ArenaMapInfo.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_map_info(map_id: u32, out: *mut ArenaMapInfo) -> i32 {
    let Some(arena) = u8::try_from(map_id).ok().and_then(Arena::get) else {
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
        })
    };
    0
}
/// # Safety
/// Output must be aligned, writable storage for one ArenaMapWall.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn arena_map_wall(map_id: u32, index: u32, out: *mut ArenaMapWall) -> i32 {
    let Some(arena) = u8::try_from(map_id).ok().and_then(Arena::get) else {
        return 1;
    };
    let Some(w) = arena.walls.get(index as usize).map(|wall| wall.aabb) else {
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
        })
    };
    0
}
/// ABI 3 projection of one kernel event. ABI 3 exports exactly the
/// first-release-6 presentation kinds 1-5; events added by first-release-7
/// (guard/parry, heal, abilities, entities, hazards, objectives and the
/// match winner) return `None` and stay internal
/// until ABI 4 assigns them kinds, so the ABI 3 stream and its indices are
/// unchanged. Deliberately exhaustive: a new kernel event must choose an
/// export here.
fn abi3_event(w: &World, event: &Event) -> Option<ArenaEvent> {
    let mut result = ArenaEvent {
        tick: w.tick.saturating_sub(1),
        actor_slot: u32::MAX,
        target_slot: u32::MAX,
        weapon_id: u32::MAX,
        ..ArenaEvent::default()
    };
    let position = match event {
        Event::Shot { slot, weapon } => {
            result.kind = 1;
            result.actor_slot = *slot as u32;
            result.weapon_id = *weapon as u32;
            w.players[*slot]
                .position
                .offset(Vec3::new(0, 0, simulation::EYE_HEIGHT))
        }
        Event::Damage {
            attacker,
            victim,
            amount,
        } => {
            result.kind = 2;
            result.actor_slot = *attacker as u32;
            result.target_slot = *victim as u32;
            result.value = *amount;
            w.players[*victim].position
        }
        Event::Death { victim, killer, .. } => {
            result.kind = 3;
            result.target_slot = *victim as u32;
            result.actor_slot = killer.map_or(u32::MAX, |slot| slot as u32);
            w.players[*victim].position
        }
        Event::Respawn { slot } => {
            result.kind = 4;
            result.target_slot = *slot as u32;
            w.players[*slot].position
        }
        Event::Terminal => {
            result.kind = 5;
            Vec3::default()
        }
        Event::Guarded { .. }
        | Event::Healed { .. }
        | Event::AbilityUsed { .. }
        | Event::Marked { .. }
        | Event::Riposte { .. }
        | Event::EntitySpawned { .. }
        | Event::EntityDamaged { .. }
        | Event::EntityRepaired { .. }
        | Event::EntityDestroyed { .. }
        | Event::EnvironmentalDamage { .. }
        | Event::ObjectiveCaptured { .. }
        | Event::OvertimeStarted
        | Event::CheckpointReached { .. }
        | Event::MatchWinner { .. } => return None,
    };
    result.x = position.x;
    result.y = position.y;
    result.z = position.z;
    Some(result)
}
fn abi3_events(w: &World) -> impl Iterator<Item = ArenaEvent> + '_ {
    w.events.iter().filter_map(|event| abi3_event(w, event))
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
    let Some(result) = abi3_events(w).nth(index as usize) else {
        return 1;
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
            Ok(world) => Box::into_raw(Box::new(ArenaHandle { world })),
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
        // ABI 3 keeps the first-release-6 input domain: bits above RELOAD,
        // including the rules-7 LOADOUT request, are invalid input (status 2)
        // and change nothing, exactly as before. ABI 4 will admit LOADOUT.
        if controls.iter().any(|c| c.buttons & !ABI3_BUTTONS != 0) {
            return 2;
        }
        match h.world.step(&controls) {
            Ok(()) => 0,
            Err(_) => 2,
        }
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
        event_count: abi3_events(w).count() as u32,
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
mod tests {
    use super::*;
    #[test]
    fn abi_layout_matches_header() {
        assert_eq!(std::mem::size_of::<ArenaConfig>(), 32);
        assert_eq!(std::mem::size_of::<ArenaParticipant>(), 32);
        assert_eq!(std::mem::size_of::<ArenaInput>(), 16);
        assert_eq!(std::mem::size_of::<ArenaPlayerSnapshot>(), 80);
        assert_eq!(std::mem::size_of::<ArenaSnapshot>(), 48);
        assert_eq!(std::mem::size_of::<ArenaMapInfo>(), 36);
        assert_eq!(std::mem::size_of::<ArenaMapWall>(), 24);
        assert_eq!(std::mem::size_of::<ArenaPlayerPresentation>(), 44);
        assert_eq!(
            std::mem::offset_of!(ArenaPlayerPresentation, charge_ticks_current),
            36
        );
        assert_eq!(
            std::mem::offset_of!(ArenaPlayerPresentation, charge_ticks_required),
            40
        );
        assert_eq!(std::mem::size_of::<ArenaWeaponSpec>(), 48);
        assert_eq!(std::mem::size_of::<ArenaEvent>(), 36);
        assert_eq!(std::mem::size_of::<ArenaProjectileSnapshot>(), 24);
    }
    #[test]
    fn presentation_queries_use_reference_geometry_and_tick_events() {
        unsafe {
            let mut map = ArenaMapInfo::default();
            assert_eq!(arena_map_info(0, &mut map), 0);
            assert_eq!(
                (map.player_radius, map.player_height, map.eye_height),
                (350, 1700, 1400)
            );
            assert_eq!(
                (map.min_x, map.min_y, map.max_x, map.max_y),
                (-22_000, -16_000, 22_000, 16_000)
            );
            let mut wall = ArenaMapWall::default();
            assert_eq!(arena_map_wall(0, 0, &mut wall), 0);
            assert_eq!(
                (wall.min_x, wall.min_y, wall.max_x, wall.max_y),
                (-23_000, -17_000, 23_000, -16_000)
            );
            assert_eq!(arena_map_wall(0, map.wall_count, &mut wall), 1);
            assert_eq!(arena_map_info(4, &mut map), 1);
            let mut weapon = ArenaWeaponSpec::default();
            assert_eq!(arena_weapon_spec(7, &mut weapon), 0);
            assert_eq!(
                (weapon.kind, weapon.damage, weapon.projectile_mm_tick),
                (2, 65, 350)
            );
            assert_eq!(arena_weapon_spec(18, &mut weapon), 1);
            let config = ArenaConfig {
                abi_version: ABI_VERSION,
                mode: 0,
                map_id: 0,
                max_ticks: 600,
                base_bond: 0,
                player_count: 1,
                offline: 1,
            };
            let participant = ArenaParticipant {
                slot: 0,
                team: 0,
                class_id: 3,
                weapon_id: 7,
                bond: 0,
                special_entitled: 0,
                reserved: 0,
            };
            let handle = arena_create(&config, &participant, 1);
            assert!(!handle.is_null());
            let mut input = ArenaInput {
                slot: 0,
                buttons: simulation::FIRE,
                move_x: 0,
                move_y: 0,
                yaw: 0,
                pitch: 0,
            };
            assert_eq!(arena_step(handle, &input, 1), 0);
            let mut event = ArenaEvent::default();
            assert_eq!(arena_event(handle, 0, &mut event), 0);
            assert_eq!((event.kind, event.tick, event.weapon_id), (1, 0, 7));
            assert_eq!(event.z, 1400);
            let mut count = 0;
            assert_eq!(arena_projectile_count(handle, &mut count), 0);
            assert_eq!(count, 1);
            let mut projectile = ArenaProjectileSnapshot::default();
            assert_eq!(arena_projectile(handle, 0, &mut projectile), 0);
            let id = projectile.id;
            let x = projectile.x;
            input.buttons = 0;
            assert_eq!(arena_step(handle, &input, 1), 0);
            assert_eq!(arena_event(handle, 0, &mut event), 1);
            assert_eq!(arena_projectile(handle, 0, &mut projectile), 0);
            assert_eq!(projectile.id, id);
            assert_eq!(projectile.x, x + 350);
            let mut presentation = ArenaPlayerPresentation::default();
            assert_eq!(arena_player_presentation(handle, 0, &mut presentation), 0);
            assert_eq!(presentation.cooldown_ticks, 47);
            assert_eq!(
                (
                    presentation.charge_ticks_current,
                    presentation.charge_ticks_required
                ),
                (0, 0)
            );
            assert_eq!(
                (
                    presentation.ammo,
                    presentation.magazine,
                    presentation.reload_ticks
                ),
                (4, 5, 0)
            );
            input.buttons = simulation::RELOAD;
            assert_eq!(arena_step(handle, &input, 1), 0);
            assert_eq!(arena_player_presentation(handle, 0, &mut presentation), 0);
            assert_eq!((presentation.ammo, presentation.reload_ticks), (4, 144));
            assert_eq!(arena_player_presentation(handle, 1, &mut presentation), 1);
            arena_destroy(handle);
        }
    }
    #[test]
    fn presentation_exposes_only_weapon_bound_windup_progress() {
        unsafe {
            let config = ArenaConfig {
                abi_version: ABI_VERSION,
                mode: 0,
                map_id: 0,
                max_ticks: 120,
                base_bond: 0,
                player_count: 1,
                offline: 1,
            };
            let mut participant = ArenaParticipant {
                slot: 0,
                team: 0,
                class_id: 3,
                weapon_id: 6,
                bond: 0,
                special_entitled: 0,
                reserved: 0,
            };
            let handle = arena_create(&config, &participant, 1);
            assert!(!handle.is_null());
            let mut input = ArenaInput {
                slot: 0,
                buttons: simulation::FIRE,
                move_x: 0,
                move_y: 0,
                yaw: 0,
                pitch: 0,
            };
            let mut presentation = ArenaPlayerPresentation::default();
            assert_eq!(arena_player_presentation(handle, 0, &mut presentation), 0);
            assert_eq!(
                (
                    presentation.charge_ticks_current,
                    presentation.charge_ticks_required
                ),
                (0, 18)
            );
            for _ in 0..9 {
                assert_eq!(arena_step(handle, &input, 1), 0);
            }
            assert_eq!(arena_player_presentation(handle, 0, &mut presentation), 0);
            assert_eq!(
                (
                    presentation.charge_ticks_current,
                    presentation.charge_ticks_required
                ),
                (9, 18)
            );
            input.buttons = 0;
            assert_eq!(arena_step(handle, &input, 1), 0);
            assert_eq!(arena_player_presentation(handle, 0, &mut presentation), 0);
            assert_eq!(
                (
                    presentation.charge_ticks_current,
                    presentation.charge_ticks_required
                ),
                (0, 18)
            );
            arena_destroy(handle);

            participant.weapon_id = 7;
            let handle = arena_create(&config, &participant, 1);
            assert!(!handle.is_null());
            assert_eq!(arena_player_presentation(handle, 0, &mut presentation), 0);
            assert_eq!(
                (
                    presentation.charge_ticks_current,
                    presentation.charge_ticks_required
                ),
                (0, 0)
            );
            input.buttons = simulation::MELEE;
            assert_eq!(arena_step(handle, &input, 1), 0);
            assert_eq!(arena_player_presentation(handle, 0, &mut presentation), 0);
            assert_eq!(
                (
                    presentation.charge_ticks_current,
                    presentation.charge_ticks_required
                ),
                (1, 18)
            );
            input.buttons = 0;
            assert_eq!(arena_step(handle, &input, 1), 0);
            assert_eq!(arena_player_presentation(handle, 0, &mut presentation), 0);
            assert_eq!(
                (
                    presentation.charge_ticks_current,
                    presentation.charge_ticks_required
                ),
                (0, 0)
            );
            arena_destroy(handle);

            participant.weapon_id = 15;
            participant.special_entitled = 1;
            let handle = arena_create(&config, &participant, 1);
            assert!(!handle.is_null());
            input.buttons = simulation::MELEE;
            for _ in 0..18 {
                assert_eq!(arena_step(handle, &input, 1), 0);
            }
            assert_eq!(arena_player_presentation(handle, 0, &mut presentation), 0);
            assert_eq!(
                (
                    presentation.charge_ticks_current,
                    presentation.charge_ticks_required
                ),
                (18, 18)
            );
            input.buttons = simulation::FIRE;
            assert_eq!(arena_step(handle, &input, 1), 0);
            assert_eq!(arena_player_presentation(handle, 0, &mut presentation), 0);
            assert_eq!(
                (
                    presentation.charge_ticks_current,
                    presentation.charge_ticks_required
                ),
                (1, 15)
            );
            let mut snapshot = ArenaSnapshot::default();
            assert_eq!(arena_snapshot(handle, &mut snapshot), 0);
            assert_eq!(snapshot.event_count, 0);
            arena_destroy(handle);
        }
    }
    #[test]
    fn abi3_skips_internal_guard_and_heal_events_without_shifting_indices() {
        fn inputs(buttons: [u32; 2]) -> [ArenaInput; 2] {
            std::array::from_fn(|slot| ArenaInput {
                slot: slot as u32,
                buttons: buttons[slot],
                move_x: 0,
                move_y: 0,
                yaw: 0,
                pitch: 0,
            })
        }
        unsafe {
            let config = ArenaConfig {
                abi_version: ABI_VERSION,
                mode: 0,
                map_id: 0,
                max_ticks: 600,
                base_bond: 0,
                player_count: 2,
                offline: 1,
            };
            let people = [0, 1].map(|slot| ArenaParticipant {
                slot,
                team: slot,
                class_id: 0,
                weapon_id: 1,
                bond: 0,
                special_entitled: 0,
                reserved: 0,
            });
            let handle = arena_create(&config, people.as_ptr(), 2);
            assert!(!handle.is_null());
            let world = &mut (*handle).world;
            world.players[0].position = Vec3::new(0, 0, 0);
            world.players[1].position = Vec3::new(5000, 0, 0);
            let mut frame = inputs([0, simulation::BLOCK]);
            frame[1].yaw = 32768;
            // Nine held guard ticks close the parry window; the tenth halves.
            for _ in 0..9 {
                assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
            }
            frame[0].buttons = simulation::FIRE;
            assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
            let world = &(*handle).world;
            assert!(matches!(
                world.events.as_slice(),
                [
                    Event::Shot { slot: 0, .. },
                    Event::Guarded {
                        parried: false,
                        prevented: 11,
                        ..
                    },
                    Event::Damage { amount: 11, .. }
                ]
            ));
            let mut snapshot = ArenaSnapshot::default();
            assert_eq!(arena_snapshot(handle, &mut snapshot), 0);
            assert_eq!(snapshot.event_count, 2);
            let mut event = ArenaEvent::default();
            assert_eq!(arena_event(handle, 0, &mut event), 0);
            assert_eq!((event.kind, event.actor_slot, event.weapon_id), (1, 0, 1));
            assert_eq!(arena_event(handle, 1, &mut event), 0);
            assert_eq!(
                (event.kind, event.actor_slot, event.target_slot, event.value),
                (2, 0, 1, 11)
            );
            assert_eq!(arena_event(handle, 2, &mut event), 1);
            arena_destroy(handle);

            let config = ArenaConfig { mode: 1, ..config };
            let mut people = people;
            people[0].class_id = 5;
            people[0].weapon_id = 17;
            people[1].team = 0;
            let handle = arena_create(&config, people.as_ptr(), 2);
            assert!(!handle.is_null());
            let world = &mut (*handle).world;
            world.players[0].position = Vec3::new(0, 0, 0);
            world.players[1].position = Vec3::new(3000, 0, 0);
            world.players[1].health = 80;
            let frame = inputs([simulation::FIRE, 0]);
            assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
            let world = &(*handle).world;
            assert!(matches!(
                world.events.as_slice(),
                [
                    Event::Shot {
                        slot: 0,
                        weapon: 17
                    },
                    Event::Healed {
                        healer: 0,
                        target: 1,
                        amount: 15,
                        weapon: Some(17)
                    }
                ]
            ));
            assert_eq!(arena_snapshot(handle, &mut snapshot), 0);
            assert_eq!(snapshot.event_count, 1);
            assert_eq!(arena_event(handle, 0, &mut event), 0);
            assert_eq!((event.kind, event.weapon_id), (1, 17));
            assert_eq!(arena_event(handle, 1, &mut event), 1);
            arena_destroy(handle);
        }
    }
    #[test]
    fn abi3_skips_ability_and_entity_events_without_shifting_indices() {
        unsafe {
            let config = ArenaConfig {
                abi_version: ABI_VERSION,
                mode: 0,
                map_id: 0,
                max_ticks: 600,
                base_bond: 0,
                player_count: 2,
                offline: 1,
            };
            let people =
                [(0, 4, 9), (1, 0, 1)].map(|(slot, class_id, weapon_id)| ArenaParticipant {
                    slot,
                    team: 0,
                    class_id,
                    weapon_id,
                    bond: 0,
                    special_entitled: 0,
                    reserved: 0,
                });
            let handle = arena_create(&config, people.as_ptr(), 2);
            assert!(!handle.is_null());
            let world = &mut (*handle).world;
            world.players[0].position = Vec3::new(0, 0, 0);
            world.players[1].position = Vec3::new(4000, 0, 0);
            let frame = [
                ArenaInput {
                    slot: 0,
                    buttons: simulation::ABILITY,
                    move_x: 0,
                    move_y: 0,
                    yaw: 0,
                    pitch: 0,
                },
                ArenaInput {
                    slot: 1,
                    buttons: simulation::FIRE,
                    move_x: 0,
                    move_y: 0,
                    yaw: 32768,
                    pitch: 0,
                },
            ];
            assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
            // The barricade goes up in the ability phase and absorbs the shot.
            let world = &(*handle).world;
            assert!(matches!(
                world.events.as_slice(),
                [
                    Event::AbilityUsed { slot: 0, class: 4 },
                    Event::EntitySpawned { id: 1, .. },
                    Event::Shot { slot: 1, weapon: 1 },
                    Event::EntityDamaged {
                        id: 1,
                        attacker: 1,
                        amount: 22
                    },
                ]
            ));
            let mut snapshot = ArenaSnapshot::default();
            assert_eq!(arena_snapshot(handle, &mut snapshot), 0);
            assert_eq!(snapshot.event_count, 1);
            let mut event = ArenaEvent::default();
            assert_eq!(arena_event(handle, 0, &mut event), 0);
            assert_eq!((event.kind, event.actor_slot, event.weapon_id), (1, 1, 1));
            assert_eq!(arena_event(handle, 1, &mut event), 1);
            let mut presentation = ArenaPlayerPresentation::default();
            assert_eq!(arena_player_presentation(handle, 0, &mut presentation), 0);
            assert_eq!(presentation.ability_cooldown_ticks, 720);
            arena_destroy(handle);
        }
    }
    #[test]
    fn abi3_map_queries_serve_every_arena_table_exactly() {
        unsafe {
            for (map_id, arena) in arena_core::maps::ARENAS.iter().enumerate() {
                let map_id = map_id as u32;
                let mut info = ArenaMapInfo::default();
                assert_eq!(arena_map_info(map_id, &mut info), 0);
                let b = arena.bounds;
                assert_eq!(
                    (info.min_x, info.min_y, info.max_x, info.max_y, info.floor_z),
                    (b.min_x, b.min_y, b.max_x, b.max_y, 0)
                );
                assert_eq!(info.wall_count as usize, arena.walls.len());
                assert!(info.wall_count <= 64);
                for (index, expected) in arena.walls.iter().enumerate() {
                    let mut wall = ArenaMapWall::default();
                    assert_eq!(arena_map_wall(map_id, index as u32, &mut wall), 0);
                    let a = expected.aabb;
                    assert_eq!(
                        [
                            wall.min_x, wall.min_y, wall.min_z, wall.max_x, wall.max_y, wall.max_z
                        ],
                        [a.min.x, a.min.y, a.min.z, a.max.x, a.max.y, a.max.z]
                    );
                }
                let mut wall = ArenaMapWall::default();
                assert_eq!(arena_map_wall(map_id, info.wall_count, &mut wall), 1);
                assert_eq!(arena_map_wall(map_id, 0, std::ptr::null_mut()), 1);
                assert_eq!(arena_map_info(map_id, std::ptr::null_mut()), 1);
            }
            let mut info = ArenaMapInfo::default();
            for map_id in [4, 256, u32::MAX] {
                assert_eq!(arena_map_info(map_id, &mut info), 1);
                assert_eq!(arena_map_wall(map_id, 0, &mut ArenaMapWall::default()), 1);
            }
        }
    }
    #[test]
    fn abi3_rejects_the_rules_7_loadout_bit_like_any_unknown_button() {
        unsafe {
            let config = ArenaConfig {
                abi_version: ABI_VERSION,
                mode: 0,
                map_id: 1,
                max_ticks: 600,
                base_bond: 0,
                player_count: 1,
                offline: 1,
            };
            let participant = ArenaParticipant {
                slot: 0,
                team: 0,
                class_id: 0,
                weapon_id: 1,
                bond: 0,
                special_entitled: 0,
                reserved: 0,
            };
            let handle = arena_create(&config, &participant, 1);
            assert!(!handle.is_null());
            let world = &mut (*handle).world;
            world.players[0].alive = false;
            world.players[0].respawn_ticks = 5;
            let mut before = [0u8; 32];
            assert_eq!(arena_state_hash(handle, before.as_mut_ptr(), 32), 0);
            for buttons in [
                simulation::LOADOUT,
                simulation::LOADOUT | simulation::FIRE,
                128,
            ] {
                let input = ArenaInput {
                    slot: 0,
                    buttons,
                    move_x: 1,
                    move_y: 0,
                    yaw: 0,
                    pitch: 0,
                };
                assert_eq!(arena_step(handle, &input, 1), 2);
                let mut after = [0u8; 32];
                assert_eq!(arena_state_hash(handle, after.as_mut_ptr(), 32), 0);
                assert_eq!(before, after);
            }
            let world = &(*handle).world;
            assert_eq!((world.tick, world.players[0].pending_loadout), (0, None));
            // The kernel itself accepts the request (ABI 4 will expose it).
            let mut kernel = world.clone();
            kernel
                .step(&[Input {
                    buttons: simulation::LOADOUT,
                    move_x: 1,
                    ..Input::default()
                }])
                .unwrap();
            assert_eq!(kernel.players[0].pending_loadout, Some((1, 3)));
            arena_destroy(handle);
        }
    }
    #[test]
    fn abi3_skips_hazard_objective_and_winner_events() {
        let idle = |count: usize| {
            (0..count)
                .map(|slot| ArenaInput {
                    slot: slot as u32,
                    buttons: 0,
                    move_x: 0,
                    move_y: 0,
                    yaw: 0,
                    pitch: 0,
                })
                .collect::<Vec<_>>()
        };
        unsafe {
            let config = ArenaConfig {
                abi_version: ABI_VERSION,
                mode: 1,
                map_id: 0,
                max_ticks: 602,
                base_bond: 0,
                player_count: 2,
                offline: 1,
            };
            let people = [0, 1].map(|slot| ArenaParticipant {
                slot,
                team: slot,
                class_id: 0,
                weapon_id: 1,
                bond: 0,
                special_entitled: 0,
                reserved: 0,
            });
            let handle = arena_create(&config, people.as_ptr(), 2);
            assert!(!handle.is_null());
            let world = &mut (*handle).world;
            // Tick 600 unlocks the point and is a multiple of every fire
            // hazard period: slot 0 captures, slot 1 burns in the embers.
            world.tick = 600;
            world.control_progress = -479;
            world.players[0].position = Vec3::new(0, 0, 0);
            world.players[1].position = Vec3::new(4000, 14_500, 0);
            let frame = idle(2);
            assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
            let world = &(*handle).world;
            assert_eq!(
                world.events,
                vec![
                    Event::EnvironmentalDamage {
                        victim: 1,
                        hazard: 0,
                        amount: 10
                    },
                    Event::ObjectiveCaptured { team: 0 },
                ]
            );
            let mut snapshot = ArenaSnapshot::default();
            assert_eq!(arena_snapshot(handle, &mut snapshot), 0);
            assert_eq!(snapshot.event_count, 0);
            let mut event = ArenaEvent::default();
            assert_eq!(arena_event(handle, 0, &mut event), 1);
            // The last tick fixes the winner; ABI 3 still sees only Terminal.
            assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
            let world = &(*handle).world;
            assert_eq!(
                world.events,
                vec![
                    Event::MatchWinner {
                        winner: simulation::Winner::Team(0)
                    },
                    Event::Terminal
                ]
            );
            assert_eq!(arena_snapshot(handle, &mut snapshot), 0);
            assert_eq!((snapshot.event_count, snapshot.terminal), (1, 1));
            assert_eq!(arena_event(handle, 0, &mut event), 0);
            assert_eq!((event.kind, event.tick), (5, 601));
            arena_destroy(handle);
        }
    }
    #[test]
    fn handle_lifecycle_and_null_rejection() {
        unsafe {
            assert_eq!(arena_step(std::ptr::null_mut(), std::ptr::null(), 0), 1);
            let c = ArenaConfig {
                abi_version: ABI_VERSION,
                mode: 0,
                map_id: 0,
                max_ticks: 60,
                base_bond: 0,
                player_count: 1,
                offline: 1,
            };
            let p = ArenaParticipant {
                slot: 0,
                team: 0,
                class_id: 0,
                weapon_id: 1,
                bond: 0,
                special_entitled: 0,
                reserved: 0,
            };
            let h = arena_create(&c, &p, 1);
            assert!(!h.is_null());
            let old_layout = ArenaConfig {
                abi_version: 2,
                ..c
            };
            assert!(arena_create(&old_layout, &p, 1).is_null());
            let i = ArenaInput {
                slot: 0,
                buttons: 0,
                move_x: 127,
                move_y: 0,
                yaw: 0,
                pitch: 0,
            };
            assert_eq!(arena_step(h, &i, 1), 0);
            let mut s = ArenaSnapshot::default();
            assert_eq!(arena_snapshot(h, &mut s), 0);
            assert_eq!(s.tick, 1);
            assert_eq!(s.proof_qualified, 0);
            assert_eq!(s.deposited, 0);
            arena_destroy(h);
        }
    }
}
