use super::*;
use arena_core::simulation::EntityKind;
use std::mem::{offset_of, size_of};

fn config(mode: u32, map_id: u32, max_ticks: u32, player_count: u32) -> ArenaConfig {
    ArenaConfig {
        abi_version: ABI_VERSION,
        mode,
        map_id,
        max_ticks,
        base_bond: 0,
        player_count,
        offline: 1,
    }
}
fn person(slot: u32, team: u32, class_id: u32, weapon_id: u32) -> ArenaParticipant {
    ArenaParticipant {
        slot,
        team,
        class_id,
        weapon_id,
        bond: 0,
        special_entitled: 0,
        reserved: 0,
    }
}
fn idle(count: usize) -> Vec<ArenaInput> {
    (0..count)
        .map(|slot| ArenaInput {
            slot: slot as u32,
            buttons: 0,
            move_x: 0,
            move_y: 0,
            yaw: 0,
            pitch: 0,
        })
        .collect()
}
/// The kernel world behind a live test handle.
unsafe fn kernel<'a>(handle: *mut ArenaHandle) -> &'a mut World {
    unsafe { &mut (*handle).world }
}
/// Every exported event of the last step, checked against `event_count`.
unsafe fn events(handle: *const ArenaHandle) -> Vec<ArenaEvent> {
    let mut snapshot = ArenaSnapshot::default();
    assert_eq!(unsafe { arena_snapshot(handle, &mut snapshot) }, 0);
    let events = (0..snapshot.event_count)
        .map(|index| {
            let mut event = ArenaEvent::default();
            assert_eq!(unsafe { arena_event(handle, index, &mut event) }, 0);
            event
        })
        .collect::<Vec<_>>();
    let mut past = ArenaEvent::default();
    assert_eq!(
        unsafe { arena_event(handle, snapshot.event_count, &mut past) },
        1
    );
    events
}
unsafe fn objective(handle: *const ArenaHandle) -> ArenaObjectiveSnapshot {
    let mut o = ArenaObjectiveSnapshot::default();
    assert_eq!(unsafe { arena_objective(handle, &mut o) }, 0);
    o
}
unsafe fn presentation(handle: *const ArenaHandle, slot: u32) -> ArenaPlayerPresentation {
    let mut p = ArenaPlayerPresentation::default();
    assert_eq!(
        unsafe { arena_player_presentation(handle, slot, &mut p) },
        0
    );
    p
}
fn event(tick: u32, kind: u32, actor: u32, target: u32, weapon: u32, at: Vec3) -> ArenaEvent {
    ArenaEvent {
        tick,
        kind,
        actor_slot: actor,
        target_slot: target,
        weapon_id: weapon,
        x: at.x,
        y: at.y,
        z: at.z,
        ..ArenaEvent::default()
    }
}

#[test]
fn abi_layout_matches_header() {
    assert_eq!(size_of::<ArenaConfig>(), 32);
    assert_eq!(size_of::<ArenaParticipant>(), 32);
    assert_eq!(size_of::<ArenaInput>(), 16);
    assert_eq!(size_of::<ArenaPlayerSnapshot>(), 80);
    assert_eq!(size_of::<ArenaSnapshot>(), 48);
    assert_eq!(size_of::<ArenaMapInfo>(), 76);
    assert_eq!(offset_of!(ArenaMapInfo, control_x), 36);
    assert_eq!(offset_of!(ArenaMapInfo, hazard_count), 72);
    assert_eq!(size_of::<ArenaMapWall>(), 24);
    assert_eq!(size_of::<ArenaMapPoint>(), 8);
    assert_eq!(size_of::<ArenaMapHazard>(), 36);
    assert_eq!(size_of::<ArenaPlayerPresentation>(), 72);
    assert_eq!(
        offset_of!(ArenaPlayerPresentation, charge_ticks_current),
        36
    );
    assert_eq!(
        offset_of!(ArenaPlayerPresentation, charge_ticks_required),
        40
    );
    assert_eq!(offset_of!(ArenaPlayerPresentation, guard_ticks), 44);
    assert_eq!(offset_of!(ArenaPlayerPresentation, admitted_special), 68);
    assert_eq!(size_of::<ArenaWeaponSpec>(), 48);
    assert_eq!(size_of::<ArenaEvent>(), 48);
    assert_eq!(offset_of!(ArenaEvent, entity_id), 36);
    assert_eq!(offset_of!(ArenaEvent, detail), 44);
    assert_eq!(size_of::<ArenaProjectileSnapshot>(), 24);
    assert_eq!(size_of::<ArenaEntitySnapshot>(), 60);
    assert_eq!(size_of::<ArenaObjectiveSnapshot>(), 96);
    assert_eq!(offset_of!(ArenaObjectiveSnapshot, payload_progress), 48);
    assert_eq!(offset_of!(ArenaObjectiveSnapshot, winner_value), 92);
}

#[test]
fn header_constants_match_the_kernel() {
    let header = include_str!("../include/arena.h");
    let define = |name: &str| -> u32 {
        let line = header
            .lines()
            .find(|line| line.split_whitespace().nth(1) == Some(name))
            .unwrap_or_else(|| panic!("{name} missing from arena.h"));
        let value = line
            .split_whitespace()
            .nth(2)
            .unwrap()
            .trim_end_matches('u');
        match value.strip_prefix("0x") {
            Some(hex) => u32::from_str_radix(hex, 16).unwrap(),
            None => value.parse().unwrap(),
        }
    };
    assert_eq!(define("ARENA_ABI_VERSION"), ABI_VERSION);
    assert_eq!(define("ARENA_NONE"), NONE);
    for (name, value) in [
        ("ARENA_BUTTON_FIRE", simulation::FIRE),
        ("ARENA_BUTTON_MELEE", simulation::MELEE),
        ("ARENA_BUTTON_BLOCK", simulation::BLOCK),
        ("ARENA_BUTTON_JUMP", simulation::JUMP),
        ("ARENA_BUTTON_ABILITY", simulation::ABILITY),
        ("ARENA_BUTTON_RELOAD", simulation::RELOAD),
        ("ARENA_BUTTON_LOADOUT", simulation::LOADOUT),
        ("ARENA_EVENT_SHOT", EVENT_SHOT),
        ("ARENA_EVENT_DAMAGE", EVENT_DAMAGE),
        ("ARENA_EVENT_DEATH", EVENT_DEATH),
        ("ARENA_EVENT_RESPAWN", EVENT_RESPAWN),
        ("ARENA_EVENT_TERMINAL", EVENT_TERMINAL),
        ("ARENA_EVENT_GUARDED", EVENT_GUARDED),
        ("ARENA_EVENT_HEALED", EVENT_HEALED),
        ("ARENA_EVENT_ABILITY", EVENT_ABILITY),
        ("ARENA_EVENT_MARKED", EVENT_MARKED),
        ("ARENA_EVENT_RIPOSTE", EVENT_RIPOSTE),
        ("ARENA_EVENT_ENTITY_SPAWNED", EVENT_ENTITY_SPAWNED),
        ("ARENA_EVENT_ENTITY_DAMAGED", EVENT_ENTITY_DAMAGED),
        ("ARENA_EVENT_ENTITY_REPAIRED", EVENT_ENTITY_REPAIRED),
        ("ARENA_EVENT_ENTITY_DESTROYED", EVENT_ENTITY_DESTROYED),
        ("ARENA_EVENT_HAZARD_DAMAGE", EVENT_HAZARD_DAMAGE),
        ("ARENA_EVENT_OBJECTIVE_CAPTURED", EVENT_OBJECTIVE_CAPTURED),
        ("ARENA_EVENT_OVERTIME", EVENT_OVERTIME),
        ("ARENA_EVENT_CHECKPOINT", EVENT_CHECKPOINT),
        ("ARENA_EVENT_MATCH_WINNER", EVENT_MATCH_WINNER),
        ("ARENA_ENTITY_DECOY", EntityKind::Decoy as u32),
        ("ARENA_ENTITY_BARRICADE", EntityKind::Barricade as u32),
        ("ARENA_ENTITY_FIRE_ZONE", EntityKind::FireZone as u32),
        ("ARENA_ENTITY_WARD", EntityKind::Ward as u32),
        (
            "ARENA_REMOVAL_EXPIRED",
            removal_code(RemovalCause::Expired).0,
        ),
        (
            "ARENA_REMOVAL_DESTROYED",
            removal_code(RemovalCause::Destroyed { by: 0 }).0,
        ),
        (
            "ARENA_REMOVAL_REPLACED",
            removal_code(RemovalCause::Replaced).0,
        ),
        (
            "ARENA_REMOVAL_OWNER_DIED",
            removal_code(RemovalCause::OwnerDied).0,
        ),
        (
            "ARENA_REMOVAL_OWNER_EXHAUSTED",
            removal_code(RemovalCause::OwnerExhausted).0,
        ),
        ("ARENA_WINNER_NONE", winner_code(None).0),
        ("ARENA_WINNER_TEAM", winner_code(Some(Winner::Team(1))).0),
        ("ARENA_WINNER_SLOT", winner_code(Some(Winner::Slot(3))).0),
        ("ARENA_WINNER_DRAW", winner_code(Some(Winner::Draw)).0),
        (
            "ARENA_HAZARD_FIRE",
            arena_core::maps::HazardKind::Fire as u32,
        ),
        (
            "ARENA_HAZARD_SLAG",
            arena_core::maps::HazardKind::Slag as u32,
        ),
        (
            "ARENA_HAZARD_SHREDDER",
            arena_core::maps::HazardKind::Shredder as u32,
        ),
    ] {
        assert_eq!(define(name), value, "{name}");
    }
    // The header declares exactly the functions this crate exports.
    let declared = header
        .lines()
        .filter(|line| line.ends_with(");") && !line.starts_with(['/', ' ']))
        .filter_map(|line| line.split_once('(').map(|(head, _)| head))
        .filter_map(|head| head.split_whitespace().last())
        .filter(|name| name.starts_with("arena_"))
        .collect::<Vec<_>>();
    let exported: [(&str, *const ()); 20] = [
        ("arena_abi_version", arena_abi_version as *const ()),
        ("arena_create", arena_create as *const ()),
        ("arena_destroy", arena_destroy as *const ()),
        ("arena_step", arena_step as *const ()),
        ("arena_snapshot", arena_snapshot as *const ()),
        ("arena_player", arena_player as *const ()),
        ("arena_state_hash", arena_state_hash as *const ()),
        ("arena_map_info", arena_map_info as *const ()),
        ("arena_map_wall", arena_map_wall as *const ()),
        ("arena_map_route_point", arena_map_route_point as *const ()),
        ("arena_map_hazard", arena_map_hazard as *const ()),
        (
            "arena_player_presentation",
            arena_player_presentation as *const (),
        ),
        ("arena_weapon_spec", arena_weapon_spec as *const ()),
        ("arena_event", arena_event as *const ()),
        (
            "arena_projectile_count",
            arena_projectile_count as *const (),
        ),
        ("arena_projectile", arena_projectile as *const ()),
        ("arena_entity_count", arena_entity_count as *const ()),
        ("arena_entity", arena_entity as *const ()),
        ("arena_objective", arena_objective as *const ()),
        ("arena_proof_qualified", arena_proof_qualified as *const ()),
    ];
    assert_eq!(declared, exported.map(|(name, _)| name));
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
        assert_eq!(
            (map.control_x, map.control_y, map.control_radius),
            (0, 0, 4000)
        );
        assert_eq!(
            (
                map.route_point_count,
                map.route_length,
                map.checkpoint_0,
                map.checkpoint_1,
                map.checkpoint_2,
                map.push_radius,
                map.hazard_count
            ),
            (6, 48_000, 16_000, 32_000, 40_000, 3000, 2)
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
        let handle = arena_create(&config(0, 0, 600, 1), &person(0, 0, 3, 7), 1);
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
        let feet = kernel(handle).players[0].position;
        assert_eq!(
            events(handle),
            [event(
                0,
                EVENT_SHOT,
                0,
                NONE,
                7,
                feet.offset(Vec3::new(0, 0, 1400))
            )]
        );
        let mut count = 0;
        assert_eq!(arena_projectile_count(handle, &mut count), 0);
        assert_eq!(count, 1);
        let mut projectile = ArenaProjectileSnapshot::default();
        assert_eq!(arena_projectile(handle, 0, &mut projectile), 0);
        let id = projectile.id;
        let x = projectile.x;
        input.buttons = 0;
        assert_eq!(arena_step(handle, &input, 1), 0);
        assert_eq!(events(handle), []);
        assert_eq!(arena_projectile(handle, 0, &mut projectile), 0);
        assert_eq!(projectile.id, id);
        assert_eq!(projectile.x, x + 350);
        let visual = presentation(handle, 0);
        assert_eq!(visual.cooldown_ticks, 47);
        assert_eq!(
            (visual.charge_ticks_current, visual.charge_ticks_required),
            (0, 0)
        );
        assert_eq!(
            (visual.ammo, visual.magazine, visual.reload_ticks),
            (4, 5, 0)
        );
        assert_eq!(
            (
                visual.guard_ticks,
                visual.ability_cooldown_total,
                visual.stance_ticks,
                visual.marked_ticks,
                visual.pending_class,
                visual.pending_weapon,
                visual.admitted_special
            ),
            (0, 720, 0, 0, NONE, NONE, NONE)
        );
        input.buttons = simulation::RELOAD;
        assert_eq!(arena_step(handle, &input, 1), 0);
        let visual = presentation(handle, 0);
        assert_eq!((visual.ammo, visual.reload_ticks), (4, 144));
        let mut other = ArenaPlayerPresentation::default();
        assert_eq!(arena_player_presentation(handle, 1, &mut other), 1);
        // Free-for-all has no objective: only the unlock tick and no owner.
        assert_eq!(
            objective(handle),
            ArenaObjectiveSnapshot {
                unlock_tick: 600,
                control_owner: NONE,
                ..ArenaObjectiveSnapshot::default()
            }
        );
        arena_destroy(handle);
    }
}

#[test]
fn presentation_exposes_only_weapon_bound_windup_progress() {
    unsafe {
        let config = config(0, 0, 120, 1);
        let mut participant = person(0, 0, 3, 6);
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
        let charge = |handle: *const ArenaHandle| {
            let p = presentation(handle, 0);
            (p.charge_ticks_current, p.charge_ticks_required)
        };
        assert_eq!(charge(handle), (0, 18));
        for _ in 0..9 {
            assert_eq!(arena_step(handle, &input, 1), 0);
        }
        assert_eq!(charge(handle), (9, 18));
        input.buttons = 0;
        assert_eq!(arena_step(handle, &input, 1), 0);
        assert_eq!(charge(handle), (0, 18));
        arena_destroy(handle);

        participant.weapon_id = 7;
        let handle = arena_create(&config, &participant, 1);
        assert!(!handle.is_null());
        assert_eq!(charge(handle), (0, 0));
        input.buttons = simulation::MELEE;
        assert_eq!(arena_step(handle, &input, 1), 0);
        assert_eq!(charge(handle), (1, 18));
        input.buttons = 0;
        assert_eq!(arena_step(handle, &input, 1), 0);
        assert_eq!(charge(handle), (0, 0));
        arena_destroy(handle);

        participant.weapon_id = 15;
        participant.special_entitled = 1;
        let handle = arena_create(&config, &participant, 1);
        assert!(!handle.is_null());
        assert_eq!(presentation(handle, 0).admitted_special, 15);
        input.buttons = simulation::MELEE;
        for _ in 0..18 {
            assert_eq!(arena_step(handle, &input, 1), 0);
        }
        assert_eq!(charge(handle), (18, 18));
        input.buttons = simulation::FIRE;
        assert_eq!(arena_step(handle, &input, 1), 0);
        assert_eq!(charge(handle), (1, 15));
        assert_eq!(events(handle), []);
        arena_destroy(handle);
    }
}

#[test]
fn guard_and_heal_events_are_exported_in_kernel_order() {
    unsafe {
        let people = [person(0, 0, 0, 1), person(1, 1, 0, 1)];
        let handle = arena_create(&config(0, 0, 600, 2), people.as_ptr(), 2);
        assert!(!handle.is_null());
        let world = &mut (*handle).world;
        world.players[0].position = Vec3::new(0, 0, 0);
        world.players[1].position = Vec3::new(5000, 0, 0);
        let mut frame = idle(2);
        frame[1].buttons = simulation::BLOCK;
        frame[1].yaw = 32768;
        // Nine held guard ticks close the parry window; the tenth halves.
        for _ in 0..9 {
            assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
        }
        assert_eq!(presentation(handle, 1).guard_ticks, 9);
        frame[0].buttons = simulation::FIRE;
        assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
        let victim = Vec3::new(5000, 0, 0);
        assert_eq!(
            events(handle),
            [
                event(9, EVENT_SHOT, 0, NONE, 1, Vec3::new(0, 0, 1400)),
                ArenaEvent {
                    value: 11,
                    ..event(9, EVENT_GUARDED, 0, 1, 1, victim)
                },
                ArenaEvent {
                    value: 11,
                    ..event(9, EVENT_DAMAGE, 0, 1, NONE, victim)
                },
            ]
        );
        arena_destroy(handle);

        // A fresh guard parries: the whole hit is prevented (detail 1).
        let handle = arena_create(&config(0, 0, 600, 2), people.as_ptr(), 2);
        assert!(!handle.is_null());
        let world = &mut (*handle).world;
        world.players[0].position = Vec3::new(0, 0, 0);
        world.players[1].position = Vec3::new(5000, 0, 0);
        frame[0].buttons = simulation::FIRE;
        assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
        assert_eq!(
            events(handle)[1],
            ArenaEvent {
                value: 22,
                detail: 1,
                ..event(0, EVENT_GUARDED, 0, 1, 1, victim)
            }
        );
        arena_destroy(handle);

        let mut people = [person(0, 0, 5, 17), person(1, 0, 0, 1)];
        people[0].special_entitled = 1;
        let handle = arena_create(&config(1, 0, 600, 2), people.as_ptr(), 2);
        assert!(!handle.is_null());
        let world = &mut (*handle).world;
        world.players[0].position = Vec3::new(0, 0, 0);
        world.players[1].position = Vec3::new(3000, 0, 0);
        world.players[1].health = 80;
        let mut frame = idle(2);
        frame[0].buttons = simulation::FIRE;
        assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
        assert_eq!(
            events(handle),
            [
                event(0, EVENT_SHOT, 0, NONE, 17, Vec3::new(0, 0, 1400)),
                ArenaEvent {
                    value: 15,
                    ..event(0, EVENT_HEALED, 0, 1, 17, Vec3::new(3000, 0, 0))
                },
            ]
        );
        arena_destroy(handle);
    }
}

#[test]
fn ability_entity_events_and_queries_describe_the_barricade() {
    unsafe {
        let people = [person(0, 0, 4, 9), person(1, 0, 0, 1)];
        let handle = arena_create(&config(0, 0, 600, 2), people.as_ptr(), 2);
        assert!(!handle.is_null());
        let world = &mut (*handle).world;
        world.players[0].position = Vec3::new(0, 0, 0);
        world.players[1].position = Vec3::new(4000, 0, 0);
        let mut frame = idle(2);
        frame[0].buttons = simulation::ABILITY;
        frame[1].buttons = simulation::FIRE;
        frame[1].yaw = 32768;
        assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
        // The barricade goes up in the ability phase and absorbs the shot.
        let centre = Vec3::new(1500, 0, 0);
        assert_eq!(
            events(handle),
            [
                ArenaEvent {
                    detail: 4,
                    ..event(0, EVENT_ABILITY, 0, NONE, NONE, Vec3::default())
                },
                ArenaEvent {
                    entity_id: 1,
                    entity_kind: 2,
                    ..event(0, EVENT_ENTITY_SPAWNED, 0, 0, NONE, centre)
                },
                event(0, EVENT_SHOT, 1, NONE, 1, Vec3::new(4000, 0, 1400)),
                ArenaEvent {
                    entity_id: 1,
                    entity_kind: 2,
                    value: 22,
                    ..event(0, EVENT_ENTITY_DAMAGED, 1, 0, NONE, centre)
                },
            ]
        );
        let mut count = 0;
        assert_eq!(arena_entity_count(handle, &mut count), 0);
        assert_eq!(count, 1);
        let mut barricade = ArenaEntitySnapshot::default();
        assert_eq!(arena_entity(handle, 0, &mut barricade), 0);
        assert_eq!(
            barricade,
            ArenaEntitySnapshot {
                id: 1,
                kind: 2,
                owner_slot: 0,
                team: 0,
                x: 1500,
                y: 0,
                z: 0,
                yaw: 0,
                health: 228,
                max_health: 250,
                age: 1,
                lifetime: 1800,
                half_x: 200,
                half_y: 1200,
                height: 2000,
            }
        );
        assert_eq!(arena_entity(handle, 1, &mut barricade), 1);
        let visual = presentation(handle, 0);
        assert_eq!(
            (visual.ability_cooldown_ticks, visual.ability_cooldown_total),
            (720, 720)
        );
        arena_destroy(handle);
    }
}

#[test]
fn an_entity_removed_in_its_spawn_step_keeps_its_exact_position() {
    unsafe {
        // The Shinobi's decoy stays where the dash starts and takes the
        // katana cut meant for its owner in the same step.
        let people = [person(0, 0, 1, 3), person(1, 1, 0, 1)];
        let handle = arena_create(&config(0, 0, 600, 2), people.as_ptr(), 2);
        assert!(!handle.is_null());
        let world = &mut (*handle).world;
        world.players[0].position = Vec3::new(0, 0, 0);
        world.players[1].position = Vec3::new(-1500, 0, 0);
        let mut frame = idle(2);
        frame[0].buttons = simulation::ABILITY;
        frame[1].buttons = simulation::MELEE;
        assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
        let decoy = Vec3::default();
        let exported = events(handle);
        assert_eq!(
            exported[1],
            ArenaEvent {
                entity_id: 1,
                entity_kind: 1,
                ..event(0, EVENT_ENTITY_SPAWNED, 0, 0, NONE, decoy)
            }
        );
        assert_eq!(
            exported[3..],
            [
                ArenaEvent {
                    entity_id: 1,
                    entity_kind: 1,
                    value: 60,
                    ..event(0, EVENT_ENTITY_DAMAGED, 1, 0, NONE, decoy)
                },
                ArenaEvent {
                    entity_id: 1,
                    entity_kind: 1,
                    detail: 1,
                    ..event(0, EVENT_ENTITY_DESTROYED, 1, 0, NONE, decoy)
                },
            ]
        );
        assert_ne!(kernel(handle).players[0].position, decoy);
        let mut count = 1;
        assert_eq!(arena_entity_count(handle, &mut count), 0);
        assert_eq!(count, 0);
        // The removal record lasts one step, like the events.
        assert_eq!(arena_step(handle, idle(2).as_ptr(), 2), 0);
        assert!(kernel(handle).removed_entities.is_empty());
        arena_destroy(handle);
    }
}

#[test]
fn map_queries_serve_every_arena_table_exactly() {
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
            assert_eq!(
                (info.control_x, info.control_y, info.control_radius),
                (arena.control.x, arena.control.y, arena.control.radius)
            );
            assert_eq!(
                [info.checkpoint_0, info.checkpoint_1, info.checkpoint_2],
                arena.checkpoints
            );
            assert_eq!(info.route_length, arena.route_length());
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
            assert_eq!(info.route_point_count as usize, arena.route.len());
            for (index, &(x, y)) in arena.route.iter().enumerate() {
                let mut point = ArenaMapPoint::default();
                assert_eq!(arena_map_route_point(map_id, index as u32, &mut point), 0);
                assert_eq!((point.x, point.y), (x, y));
            }
            assert_eq!(info.hazard_count as usize, arena.hazards.len());
            for (index, expected) in arena.hazards.iter().enumerate() {
                let mut hazard = ArenaMapHazard::default();
                assert_eq!(arena_map_hazard(map_id, index as u32, &mut hazard), 0);
                let v = expected.volume;
                assert_eq!(
                    (hazard.kind, hazard.damage, hazard.period),
                    (
                        expected.kind as u32,
                        expected.damage,
                        u32::from(expected.period)
                    )
                );
                assert_eq!(
                    [
                        hazard.min_x,
                        hazard.min_y,
                        hazard.min_z,
                        hazard.max_x,
                        hazard.max_y,
                        hazard.max_z
                    ],
                    [v.min.x, v.min.y, v.min.z, v.max.x, v.max.y, v.max.z]
                );
            }
            let (walls, route, hazards) =
                (info.wall_count, info.route_point_count, info.hazard_count);
            assert_eq!(
                arena_map_wall(map_id, walls, &mut ArenaMapWall::default()),
                1
            );
            assert_eq!(
                arena_map_route_point(map_id, route, &mut ArenaMapPoint::default()),
                1
            );
            assert_eq!(
                arena_map_hazard(map_id, hazards, &mut ArenaMapHazard::default()),
                1
            );
            assert_eq!(arena_map_wall(map_id, 0, std::ptr::null_mut()), 1);
            assert_eq!(arena_map_route_point(map_id, 0, std::ptr::null_mut()), 1);
            assert_eq!(arena_map_hazard(map_id, 0, std::ptr::null_mut()), 1);
            assert_eq!(arena_map_info(map_id, std::ptr::null_mut()), 1);
        }
        let mut info = ArenaMapInfo::default();
        for map_id in [4, 256, u32::MAX] {
            assert_eq!(arena_map_info(map_id, &mut info), 1);
            assert_eq!(arena_map_wall(map_id, 0, &mut ArenaMapWall::default()), 1);
            assert_eq!(
                arena_map_route_point(map_id, 0, &mut ArenaMapPoint::default()),
                1
            );
            assert_eq!(
                arena_map_hazard(map_id, 0, &mut ArenaMapHazard::default()),
                1
            );
        }
    }
}

#[test]
fn a_dead_player_requests_its_respawn_loadout() {
    unsafe {
        let handle = arena_create(&config(0, 1, 600, 1), &person(0, 0, 0, 1), 1);
        assert!(!handle.is_null());
        let world = &mut (*handle).world;
        world.players[0].alive = false;
        world.players[0].respawn_ticks = 3;
        let mut before = [0u8; 32];
        assert_eq!(arena_state_hash(handle, before.as_mut_ptr(), 32), 0);
        // Out-of-domain requests and unknown bits reject the whole step.
        for (buttons, move_x, move_y) in [
            (simulation::LOADOUT, 6, 0),
            (simulation::LOADOUT, 2, 3),
            (simulation::LOADOUT, -1, 0),
            (128, 0, 0),
            (256, 0, 0),
        ] {
            let input = ArenaInput {
                slot: 0,
                buttons,
                move_x,
                move_y,
                yaw: 0,
                pitch: 0,
            };
            assert_eq!(arena_step(handle, &input, 1), 2);
            let mut after = [0u8; 32];
            assert_eq!(arena_state_hash(handle, after.as_mut_ptr(), 32), 0);
            assert_eq!(before, after);
        }
        // Class 2 (Teppō), index 0: the Coil matchlock.
        let mut request = ArenaInput {
            slot: 0,
            buttons: simulation::LOADOUT,
            move_x: 2,
            move_y: 0,
            yaw: 0,
            pitch: 0,
        };
        assert_eq!(arena_step(handle, &request, 1), 0);
        let visual = presentation(handle, 0);
        assert_eq!((visual.pending_class, visual.pending_weapon), (2, 5));
        // Index 2 needs an admitted special of that class: ignored.
        request.move_y = 2;
        assert_eq!(arena_step(handle, &request, 1), 0);
        assert_eq!(presentation(handle, 0).pending_class, 2);
        assert_eq!(events(handle), []);
        request.buttons = 0;
        assert_eq!(arena_step(handle, &request, 1), 0);
        let spawn = kernel(handle).players[0].position;
        assert_eq!(
            events(handle),
            [ArenaEvent {
                detail: 2,
                ..event(2, EVENT_RESPAWN, NONE, 0, 5, spawn)
            }]
        );
        let visual = presentation(handle, 0);
        assert_eq!(
            (
                visual.pending_class,
                visual.pending_weapon,
                visual.ability_cooldown_total,
                visual.magazine
            ),
            (NONE, NONE, 720, 5)
        );
        arena_destroy(handle);
    }
}

#[test]
fn hazard_objective_and_winner_events_and_the_control_snapshot() {
    unsafe {
        let people = [person(0, 0, 0, 1), person(1, 1, 0, 1)];
        let handle = arena_create(&config(1, 0, 602, 2), people.as_ptr(), 2);
        assert!(!handle.is_null());
        let world = &mut (*handle).world;
        // Tick 600 unlocks the point and is a multiple of every fire hazard
        // period: slot 0 captures, slot 1 burns in the embers.
        world.tick = 600;
        world.control_progress = -479;
        world.players[0].position = Vec3::new(0, 0, 0);
        world.players[1].position = Vec3::new(4000, 14_500, 0);
        let frame = idle(2);
        assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
        assert_eq!(
            events(handle),
            [
                ArenaEvent {
                    value: 10,
                    ..event(
                        600,
                        EVENT_HAZARD_DAMAGE,
                        NONE,
                        1,
                        NONE,
                        Vec3::new(4000, 14_500, 0)
                    )
                },
                event(
                    600,
                    EVENT_OBJECTIVE_CAPTURED,
                    NONE,
                    NONE,
                    NONE,
                    Vec3::default()
                ),
            ]
        );
        assert_eq!(
            objective(handle),
            ArenaObjectiveSnapshot {
                mode: 1,
                unlock_tick: 600,
                score_0: 1,
                score_target: 10_800,
                control_owner: 0,
                control_progress: -480,
                control_capture: 480,
                control_team_0: 1,
                ..ArenaObjectiveSnapshot::default()
            }
        );
        // The last tick fixes the winner, just before Terminal.
        assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
        assert_eq!(
            events(handle),
            [
                ArenaEvent {
                    detail: 1,
                    ..event(601, EVENT_MATCH_WINNER, NONE, NONE, NONE, Vec3::default())
                },
                event(601, EVENT_TERMINAL, NONE, NONE, NONE, Vec3::default()),
            ]
        );
        let o = objective(handle);
        assert_eq!((o.winner_kind, o.winner_value, o.score_0), (1, 0, 2));
        assert_eq!(arena_step(handle, frame.as_ptr(), 2), 2);
        arena_destroy(handle);
    }
}

#[test]
fn contested_overtime_is_exported() {
    unsafe {
        let people = [person(0, 0, 0, 1), person(1, 1, 0, 1)];
        let handle = arena_create(&config(1, 0, 36_000, 2), people.as_ptr(), 2);
        let world = &mut (*handle).world;
        world.tick = 20_000;
        world.control_owner = Some(0);
        world.control_progress = -480;
        world.score[0] = CONTROL_TARGET - 1;
        world.players[0].position = Vec3::new(0, 0, 0);
        world.players[1].position = Vec3::new(1000, 1000, 0);
        assert_eq!(arena_step(handle, idle(2).as_ptr(), 2), 0);
        assert_eq!(
            events(handle),
            [event(
                20_000,
                EVENT_OVERTIME,
                NONE,
                NONE,
                NONE,
                Vec3::default()
            )]
        );
        let o = objective(handle);
        assert_eq!(
            (
                o.overtime,
                o.contested,
                o.control_team_0,
                o.control_team_1,
                o.score_0,
                o.winner_kind
            ),
            (1, 1, 1, 1, CONTROL_TARGET, 0)
        );
        arena_destroy(handle);
    }
}

#[test]
fn payload_checkpoint_event_and_snapshot() {
    unsafe {
        let people = [person(0, 0, 0, 1), person(1, 1, 0, 1)];
        let handle = arena_create(&config(2, 0, 36_000, 2), people.as_ptr(), 2);
        assert!(!handle.is_null());
        let world = &mut (*handle).world;
        // Estate's first checkpoint is 16,000 mm along the route, at the
        // corner (-8000, -5500). One attacker pushes 6 mm per tick.
        world.tick = 600;
        world.payload_progress = 15_995;
        world.players[0].position = Vec3::new(-8000, -5400, 0);
        assert_eq!(arena_step(handle, idle(2).as_ptr(), 2), 0);
        assert_eq!(
            events(handle),
            [ArenaEvent {
                value: 16_000,
                ..event(
                    600,
                    EVENT_CHECKPOINT,
                    NONE,
                    NONE,
                    NONE,
                    Vec3::new(-8000, -5500, 0)
                )
            }]
        );
        assert_eq!(
            objective(handle),
            ArenaObjectiveSnapshot {
                mode: 2,
                unlock_tick: 600,
                control_owner: NONE,
                payload_progress: 16_001,
                payload_length: 48_000,
                payload_checkpoints: 1,
                payload_rollback_delay: 900,
                payload_x: -7999,
                payload_y: -5500,
                payload_attackers: 1,
                ..ArenaObjectiveSnapshot::default()
            }
        );
        // A defender inside the radius contests and stops the push.
        kernel(handle).players[1].position = Vec3::new(-7000, -4000, 0);
        assert_eq!(arena_step(handle, idle(2).as_ptr(), 2), 0);
        let o = objective(handle);
        assert_eq!(
            (
                o.payload_progress,
                o.contested,
                o.payload_attackers,
                o.payload_defenders
            ),
            (16_001, 1, 1, 1)
        );
        arena_destroy(handle);
    }
}

#[test]
fn staked_matches_conserve_value_and_report_exhaustion() {
    unsafe {
        let mut people = [person(0, 0, 0, 1), person(1, 1, 0, 12)];
        people[0].bond = 1000;
        // A special weapon without its NFT needs twice the base bond.
        people[1].bond = 2000;
        let staked = ArenaConfig {
            base_bond: 1000,
            offline: 0,
            ..config(0, 0, 600, 2)
        };
        let handle = arena_create(&staked, people.as_ptr(), 2);
        assert!(!handle.is_null());
        let world = &mut (*handle).world;
        world.players[0].position = Vec3::new(0, 0, 0);
        world.players[1].position = Vec3::new(5000, 0, 0);
        world.players[1].health = 1;
        let mut frame = idle(2);
        frame[0].buttons = simulation::FIRE;
        assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
        let exported = events(handle);
        assert_eq!(
            exported.iter().map(|e| e.kind).collect::<Vec<_>>(),
            [EVENT_SHOT, EVENT_DAMAGE, EVENT_DEATH]
        );
        assert_eq!((exported[2].actor_slot, exported[2].detail), (0, 0));
        let mut snapshot = ArenaSnapshot::default();
        assert_eq!(arena_snapshot(handle, &mut snapshot), 0);
        assert_eq!(
            (snapshot.deposited, snapshot.remaining, snapshot.earnings),
            (3000, 2800, 200)
        );
        arena_destroy(handle);

        // The tenth paid death exhausts the reserve, and a staked FFA with one
        // reserve left ends at once.
        let handle = arena_create(&staked, people.as_ptr(), 2);
        let world = &mut (*handle).world;
        world.players[0].position = Vec3::new(0, 0, 0);
        world.players[1].position = Vec3::new(5000, 0, 0);
        world.players[1].health = 1;
        world.accounts[1].remaining = 200;
        world.accounts[1].paid_deaths = 9;
        world.accounts[0].earnings = 1800;
        assert_eq!(arena_step(handle, frame.as_ptr(), 2), 0);
        let exported = events(handle);
        assert_eq!(
            exported.iter().map(|e| e.kind).collect::<Vec<_>>(),
            [
                EVENT_SHOT,
                EVENT_DAMAGE,
                EVENT_DEATH,
                EVENT_MATCH_WINNER,
                EVENT_TERMINAL
            ]
        );
        assert_eq!(exported[2].detail, 1);
        assert_eq!((exported[3].detail, exported[3].value), (2, 0));
        let mut player = ArenaPlayerSnapshot::default();
        assert_eq!(arena_player(handle, 1, &mut player), 0);
        assert_eq!((player.exhausted, player.remaining_bond), (1, 0));
        assert_eq!(arena_snapshot(handle, &mut snapshot), 0);
        assert_eq!(
            (snapshot.deposited, snapshot.remaining + snapshot.earnings),
            (3000, 3000)
        );
        arena_destroy(handle);
    }
}

#[test]
fn every_mode_admits_two_to_twelve_players_on_every_map() {
    unsafe {
        for map_id in 0..4 {
            for (mode, counts) in [(0, 2..=8), (1, 2..=12), (2, 2..=12), (3, 2..=8)] {
                for count in counts {
                    let people = (0..count)
                        .map(|slot| {
                            let class = slot % 6;
                            // Melee admits only the class melee weapon.
                            let weapon = if mode == 3 { class * 2 } else { class * 2 + 1 };
                            person(slot, slot % 2, class, weapon)
                        })
                        .collect::<Vec<_>>();
                    let handle = arena_create(
                        &config(mode, map_id, 60, count),
                        people.as_ptr(),
                        count as usize,
                    );
                    assert!(
                        !handle.is_null(),
                        "mode {mode} map {map_id} players {count}"
                    );
                    assert_eq!(
                        arena_step(handle, idle(count as usize).as_ptr(), count as usize),
                        0
                    );
                    assert_eq!(objective(handle).mode, mode);
                    arena_destroy(handle);
                }
            }
        }
        let crowd = |count: u32, team: fn(u32) -> u32| {
            (0..count)
                .map(|slot| person(slot, team(slot), 0, 1))
                .collect::<Vec<_>>()
        };
        // Nine in free-for-all, seven on one team, and a ranged Melee weapon.
        let nine = crowd(9, |slot| slot % 2);
        assert!(arena_create(&config(0, 0, 60, 9), nine.as_ptr(), 9).is_null());
        let lopsided = crowd(8, |slot| u32::from(slot >= 7));
        assert!(arena_create(&config(1, 0, 60, 8), lopsided.as_ptr(), 8).is_null());
        let ranged = crowd(2, |slot| slot);
        assert!(arena_create(&config(3, 0, 60, 2), ranged.as_ptr(), 2).is_null());
        assert!(arena_create(&config(4, 0, 60, 2), ranged.as_ptr(), 2).is_null());
        // Practice cannot carry funds, and a staked match needs a base bond
        // divisible by ten that every deposit matches.
        let mut funded = crowd(2, |slot| slot);
        funded[0].bond = 1000;
        assert!(arena_create(&config(0, 0, 60, 2), funded.as_ptr(), 2).is_null());
        let staked = |base_bond| ArenaConfig {
            base_bond,
            offline: 0,
            ..config(0, 0, 60, 2)
        };
        assert!(arena_create(&staked(1000), funded.as_ptr(), 2).is_null());
        funded[1].bond = 1000;
        let handle = arena_create(&staked(1000), funded.as_ptr(), 2);
        assert!(!handle.is_null());
        arena_destroy(handle);
        assert!(arena_create(&staked(0), funded.as_ptr(), 2).is_null());
        funded[0].bond = 1005;
        funded[1].bond = 1005;
        assert!(arena_create(&staked(1005), funded.as_ptr(), 2).is_null());
    }
}

#[test]
fn handle_lifecycle_and_null_rejection() {
    unsafe {
        assert_eq!(arena_step(std::ptr::null_mut(), std::ptr::null(), 0), 1);
        let c = config(0, 0, 60, 1);
        let p = person(0, 0, 0, 1);
        let h = arena_create(&c, &p, 1);
        assert!(!h.is_null());
        for old in [2, 3] {
            let old_layout = ArenaConfig {
                abi_version: old,
                ..config(0, 0, 60, 1)
            };
            assert!(arena_create(&old_layout, &p, 1).is_null());
        }
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
        assert_eq!((s.abi_version, s.tick, s.proof_qualified), (4, 1, 0));
        assert_eq!(s.deposited, 0);
        let null = std::ptr::null::<ArenaHandle>();
        let mut count = 0;
        assert_eq!(arena_entity_count(null, &mut count), 1);
        assert_eq!(arena_entity_count(h, std::ptr::null_mut()), 1);
        assert_eq!(
            arena_entity(null, 0, &mut ArenaEntitySnapshot::default()),
            1
        );
        assert_eq!(arena_entity(h, 0, std::ptr::null_mut()), 1);
        assert_eq!(
            arena_objective(null, &mut ArenaObjectiveSnapshot::default()),
            1
        );
        assert_eq!(arena_objective(h, std::ptr::null_mut()), 1);
        assert_eq!(arena_event(null, 0, &mut ArenaEvent::default()), 1);
        assert_eq!(arena_event(h, 0, std::ptr::null_mut()), 1);
        arena_destroy(h);
    }
}
