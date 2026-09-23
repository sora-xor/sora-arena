//! Native C ABI for Unreal. Foreign callers own pointer validity and serialize
//! per-handle access. No function signs a wallet transaction or qualifies proofs.
use arena_core::{
    ABI_VERSION, catalog,
    math::Vec3,
    simulation::{self, Config, Event, Input, Mode, Participant, World},
};
use std::panic::{AssertUnwindSafe, catch_unwind};

pub struct ArenaHandle {
    world: World,
}
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
    if map_id >= 4 || out.is_null() {
        return 1;
    }
    unsafe {
        out.write(ArenaMapInfo {
            min_x: -simulation::BOUNDS,
            min_y: -simulation::BOUNDS,
            max_x: simulation::BOUNDS,
            max_y: simulation::BOUNDS,
            floor_z: 0,
            wall_count: simulation::map_walls(map_id as u8).len() as u32,
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
    if map_id >= 4 || out.is_null() {
        return 1;
    }
    let walls = simulation::map_walls(map_id as u8);
    let Some(w) = walls.get(index as usize) else {
        return 1;
    };
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
        })
    };
    0
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
    };
    result.x = position.x;
    result.y = position.y;
    result.z = position.z;
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
        assert_eq!(std::mem::size_of::<ArenaPlayerPresentation>(), 36);
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
            let mut wall = ArenaMapWall::default();
            assert_eq!(arena_map_wall(0, 0, &mut wall), 0);
            assert_eq!((wall.min_x, wall.max_x), (-8000, -6500));
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
                abi_version: 1,
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
