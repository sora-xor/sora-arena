//! The bots' integer mirrors of kernel rules, checked against the kernel
//! itself: the inverse of `math::direction`, the walking step, collision-safe
//! motion near every wall and barricade, and barricade placement. Also the
//! navigation graph's reach over every arena.
use arena_bots::{geometry, nav};
use arena_core::{
    maps::ARENAS,
    math::{self, Vec3},
    simulation::{
        ABILITY, BLOCK, Config, EntityKind, Event, Input, Mode, Participant, RADIUS, World,
    },
};

fn solo(map: u8, class: u8, weapon: u8) -> World {
    World::new(
        Config {
            mode: Mode::FreeForAll,
            map,
            max_ticks: 36_000,
            base_bond: 0,
            offline: true,
        },
        &[Participant {
            team: 0,
            class,
            weapon,
            bond: 0,
            special_entitled: false,
        }],
    )
    .unwrap()
}

fn cross(yaw: u16, dx: i32, dy: i32) -> i64 {
    let d = math::direction(yaw, 0);
    i64::from(d.x) * i64::from(dy) - i64::from(d.y) * i64::from(dx)
}

#[test]
fn yaw_and_pitch_invert_the_kernel_direction() {
    assert_eq!(
        [
            geometry::yaw_toward(5, 0),
            geometry::yaw_toward(0, 5),
            geometry::yaw_toward(-5, 0),
            geometry::yaw_toward(0, -5)
        ],
        [0, 16384, 32768, 49152]
    );
    for dx in (-40_000..=40_000).step_by(1733) {
        for dy in (-40_000..=40_000).step_by(1907) {
            if (dx, dy) == (0, 0) {
                continue;
            }
            let yaw = geometry::yaw_toward(dx, dy);
            let d = math::direction(yaw, 0);
            assert!(i64::from(d.x) * i64::from(dx) + i64::from(d.y) * i64::from(dy) > 0);
            // No neighbouring yaw points closer along (dx, dy).
            for other in [yaw.wrapping_sub(1), yaw.wrapping_add(1)] {
                assert!(
                    cross(yaw, dx, dy).abs() <= cross(other, dx, dy).abs(),
                    "{dx},{dy}"
                );
            }
        }
    }
    let pitch_cross = |pitch: i16, h: i32, dz: i32| {
        let d = math::direction(0, pitch);
        i64::from(d.x) * i64::from(dz) - i64::from(d.z) * i64::from(h)
    };
    for h in (100..=40_000).step_by(997) {
        for dz in (-3000..=3000).step_by(137) {
            let pitch = geometry::pitch_toward(h, dz);
            for other in [pitch - 1, pitch + 1] {
                assert!(pitch_cross(pitch, h, dz).abs() <= pitch_cross(other, h, dz).abs());
            }
        }
    }
}

#[test]
fn the_walking_step_matches_the_kernel_in_the_open() {
    for class in 0..6u8 {
        let mut open = solo(0, class, class * 2 + 1);
        // The courtyard centre of Nyaagyu Estate is clear for 2 m around.
        open.players[0].position = Vec3::new(0, 0, 0);
        for yaw in (0..=65535u16).step_by(4099) {
            for heading in (0..=65535u16).step_by(5003) {
                for guard in [false, true] {
                    let (move_x, move_y) = geometry::move_axes(yaw, heading);
                    let input = Input {
                        buttons: if guard { BLOCK } else { 0 },
                        move_x,
                        move_y,
                        yaw,
                        pitch: 0,
                    };
                    let mut w = open.clone();
                    w.step(&[input]).unwrap();
                    let p = w.players[0].position;
                    assert_eq!(
                        (p.x, p.y),
                        geometry::walk_step(class, guard, yaw, move_x, move_y)
                    );
                }
            }
        }
    }
}

/// Probe positions just outside `b` grown by the body radius: on each face
/// and at each corner, 1 to 160 mm away.
fn around(b: arena_core::math::Aabb) -> Vec<Vec3> {
    let (x0, y0, x1, y1) = (
        b.min.x - RADIUS,
        b.min.y - RADIUS,
        b.max.x + RADIUS,
        b.max.y + RADIUS,
    );
    let (cx, cy) = ((x0 + x1) / 2, (y0 + y1) / 2);
    let mut points = Vec::new();
    for gap in [1, 7, 40, 99, 160] {
        for (x, y) in [
            (x0 - gap, cy),
            (x1 + gap, cy),
            (cx, y0 - gap),
            (cx, y1 + gap),
            (x0 - gap, y0 - gap),
            (x1 + gap, y1 + gap),
            (x0 - gap, y1 + gap),
            (x1 + gap, y0 - gap),
        ] {
            points.push(Vec3::new(x, y, 0));
        }
    }
    points
}

#[test]
fn motion_clear_predicts_exactly_what_the_kernel_applies() {
    let (mut clipped, mut clear) = (0, 0);
    for map in 0..4u8 {
        // A Shinobi, the fastest class, with one barricade raised mid-arena.
        let mut base = solo(map, 4, 9);
        let arena = &ARENAS[usize::from(map)];
        let mut obstacles: Vec<_> = arena.walls.iter().map(|w| w.aabb).collect();
        base.players[0].position = Vec3::new(arena.control.x - 2500, arena.control.y + 400, 0);
        base.step(&[Input {
            buttons: ABILITY,
            ..Input::default()
        }])
        .unwrap();
        let barricade = base
            .entities
            .iter()
            .find(|e| e.kind == EntityKind::Barricade)
            .expect("a barricade in the open");
        obstacles.push(barricade.bounds());
        base.players[0].class = 1;
        for b in obstacles {
            for at in around(b) {
                if !arena.bounds.contains(at.x, at.y) {
                    continue;
                }
                for heading in (0..=65535u16).step_by(4096) {
                    let (move_x, move_y) = geometry::move_axes(0, heading);
                    let (dx, dy) = geometry::walk_step(1, false, 0, move_x, move_y);
                    let mut w = base.clone();
                    w.players[0].position = at;
                    let predicted = geometry::motion_clear(&w, at, dx, dy);
                    w.step(&[Input {
                        move_x,
                        move_y,
                        ..Input::default()
                    }])
                    .unwrap();
                    let p = w.players[0].position;
                    let applied = (p.x - at.x, p.y - at.y) == (dx, dy);
                    assert_eq!(predicted, applied, "map {map} at {at:?} heading {heading}");
                    if applied {
                        clear += 1;
                    } else {
                        clipped += 1;
                    }
                }
            }
        }
    }
    // Both outcomes were exercised in quantity.
    assert!(
        clipped > 1000 && clear > 1000,
        "{clipped} clipped, {clear} clear"
    );
}

#[test]
fn barricade_fits_predicts_the_kernel_placement() {
    let (mut placed, mut refused) = (0, 0);
    for map in 0..4u8 {
        let arena = &ARENAS[usize::from(map)];
        let b = arena.bounds;
        let base = solo(map, 4, 9);
        for x in (b.min_x + 700..b.max_x - 700).step_by(1300) {
            for y in (b.min_y + 700..b.max_y - 700).step_by(1300) {
                let at = Vec3::new(x, y, 0);
                // Only where a body can stand at all.
                if arena
                    .walls
                    .iter()
                    .any(|w| w.aabb.overlaps(geometry::body(at, 0)))
                {
                    continue;
                }
                for yaw in (0..=65535u16).step_by(8192 + 1111) {
                    let mut w = base.clone();
                    w.players[0].position = at;
                    let predicted = geometry::barricade_fits(&w, 0, at, yaw);
                    w.step(&[Input {
                        buttons: ABILITY,
                        yaw,
                        ..Input::default()
                    }])
                    .unwrap();
                    let actual = w
                        .events
                        .iter()
                        .any(|e| matches!(e, Event::AbilityUsed { class: 4, .. }));
                    assert_eq!(predicted, actual, "map {map} at {at:?} yaw {yaw}");
                    if actual {
                        placed += 1;
                    } else {
                        refused += 1;
                    }
                }
            }
        }
    }
    assert!(
        placed > 500 && refused > 500,
        "{placed} placed, {refused} refused"
    );
}

#[test]
fn every_spawn_reaches_every_objective_and_spawn_on_the_graph() {
    for arena in &ARENAS {
        let graph = nav::get(arena.id);
        assert!(graph.nodes().iter().all(|&n| graph.standable(n)));
        let spawns: Vec<_> = arena.spawns().map(|s| (s.x, s.y)).collect();
        let mut goals = spawns.clone();
        goals.push((arena.control.x, arena.control.y));
        goals.extend(arena.route.iter().copied());
        for lane in arena.lanes {
            goals.extend(lane.points.iter().copied());
        }
        for &from in &spawns {
            // A bot inside a wall's planning margin first steps out.
            let start = graph.standable_near(from);
            assert!(nav::length(from, start) <= 500, "{} {from:?}", arena.slug);
            for &goal in &goals {
                let path = graph.path(start, goal);
                assert!(!path.is_empty(), "{} {from:?} -> {goal:?}", arena.slug);
                let mut here = start;
                for &next in &path {
                    assert!(
                        graph.clear(here, next),
                        "{} {here:?} -> {next:?}",
                        arena.slug
                    );
                    here = next;
                }
                // A standable goal is reached exactly; one inside a margin is
                // approached to the nearest corner.
                if graph.standable(goal) {
                    assert_eq!(here, goal, "{} {from:?} -> {goal:?}", arena.slug);
                } else {
                    assert!(nav::length(here, goal) <= 1500, "{} {goal:?}", arena.slug);
                }
            }
        }
    }
}
