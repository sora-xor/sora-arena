//! First-release-7 arena data (docs/combat-rules.md §7): the kernel tables
//! match the specification's `arena-data` blocks record for record, satisfy
//! every §7.2 invariant, and match the checked-in presentation export.
use arena_core::{
    RULES_VERSION, arena_export,
    maps::{ARENAS, Arena, GLOBAL_BOUNDS, HazardKind, MAX_WALLS, MIN_WALL_HEIGHT, Spawn},
    math::{Aabb, Vec3},
    simulation::{
        Config, EYE_HEIGHT, HEIGHT, Input, JUMP, Mode, PAYLOAD_PUSH_RADIUS, Participant, RADIUS,
        World,
    },
};
use serde_json::Value;
use std::collections::{BTreeSet, VecDeque};

const SPEC: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../../docs/combat-rules.md");
const EXPORT: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/data/arena-map-v1.json");

fn aabb(v: &[i32]) -> Aabb {
    Aabb {
        min: Vec3::new(v[0], v[1], v[2]),
        max: Vec3::new(v[3], v[4], v[5]),
    }
}

fn numbers(fields: &[&str]) -> Vec<i32> {
    fields
        .iter()
        .map(|field| field.parse().expect("integer field"))
        .collect()
}

fn point(text: &str) -> (i32, i32) {
    let (x, y) = text.split_once(',').expect("x,y lane point");
    (x.parse().unwrap(), y.parse().unwrap())
}

/// One parsed `arena-data` block, labels taken from the `#` comments.
#[derive(Default)]
struct Block {
    id: Option<u8>,
    slug: String,
    bounds: Vec<i32>,
    walls: Vec<(Aabb, String)>,
    spawns: [Vec<Spawn>; 3],
    control: Vec<i32>,
    route: Vec<(i32, i32)>,
    checkpoints: Vec<i32>,
    route_length_comment: Option<i32>,
    hazards: Vec<(HazardKind, Aabb, i32, u16, String)>,
    lanes: Vec<(String, Vec<(i32, i32)>)>,
}

fn spec_blocks() -> Vec<Block> {
    let spec = std::fs::read_to_string(SPEC).expect("read docs/combat-rules.md");
    let mut blocks = Vec::new();
    let mut current: Option<Block> = None;
    for line in spec.lines() {
        if line == "```arena-data" {
            current = Some(Block::default());
            continue;
        }
        let Some(block) = current.as_mut() else {
            continue;
        };
        if line == "```" {
            blocks.push(current.take().unwrap());
            continue;
        }
        let (body, comment) = line.split_once('#').unwrap_or((line, ""));
        let comment = comment.trim().to_string();
        let fields = body.split_whitespace().collect::<Vec<_>>();
        match fields.as_slice() {
            [] => {}
            ["arena", id, slug] => {
                block.id = Some(id.parse().unwrap());
                block.slug = slug.to_string();
            }
            ["bounds", rest @ ..] => block.bounds = numbers(rest),
            ["wall", rest @ ..] => block.walls.push((aabb(&numbers(rest)), comment)),
            ["spawn", set, x, y, yaw] => {
                let index = match *set {
                    "team0" => 0,
                    "team1" => 1,
                    "ffa" => 2,
                    other => panic!("unknown spawn set {other}"),
                };
                block.spawns[index].push(Spawn {
                    x: x.parse().unwrap(),
                    y: y.parse().unwrap(),
                    yaw: yaw.parse().unwrap(),
                });
            }
            ["control", rest @ ..] => block.control = numbers(rest),
            ["route", x, y] => block.route.push((x.parse().unwrap(), y.parse().unwrap())),
            ["checkpoints", rest @ ..] => {
                block.checkpoints = numbers(rest);
                block.route_length_comment = comment
                    .strip_prefix("route length ")
                    .map(|length| length.parse().unwrap());
            }
            ["hazard", kind, rest @ ..] => {
                let kind = match *kind {
                    "fire" => HazardKind::Fire,
                    "slag" => HazardKind::Slag,
                    "shredder" => HazardKind::Shredder,
                    other => panic!("unknown hazard kind {other}"),
                };
                let values = numbers(rest);
                block.hazards.push((
                    kind,
                    aabb(&values[..6]),
                    values[6],
                    u16::try_from(values[7]).unwrap(),
                    comment,
                ));
            }
            ["lane", name, points @ ..] => block
                .lanes
                .push((name.to_string(), points.iter().map(|p| point(p)).collect())),
            other => panic!("unknown arena-data record {other:?}"),
        }
    }
    assert!(current.is_none(), "unterminated arena-data block");
    blocks
}

#[test]
fn spec_arena_data_blocks_match_the_kernel_tables_record_for_record() {
    let blocks = spec_blocks();
    assert_eq!(blocks.len(), ARENAS.len());
    for (block, arena) in blocks.iter().zip(&ARENAS) {
        assert_eq!(block.id, Some(arena.id));
        assert_eq!(block.slug, arena.slug);
        let b = arena.bounds;
        assert_eq!(block.bounds, [b.min_x, b.min_y, b.max_x, b.max_y]);
        let walls = arena
            .walls
            .iter()
            .map(|w| (w.aabb, w.label.to_string()))
            .collect::<Vec<_>>();
        assert_eq!(block.walls, walls, "{} walls", arena.slug);
        assert_eq!(block.spawns[0], arena.team_spawns[0]);
        assert_eq!(block.spawns[1], arena.team_spawns[1]);
        assert_eq!(block.spawns[2], arena.ffa_spawns);
        let c = arena.control;
        assert_eq!(block.control, [c.x, c.y, c.radius]);
        assert_eq!(block.route, arena.route);
        assert_eq!(block.checkpoints, arena.checkpoints);
        assert_eq!(block.route_length_comment, Some(arena.route_length()));
        let hazards = arena
            .hazards
            .iter()
            .map(|h| (h.kind, h.volume, h.damage, h.period, h.label.to_string()))
            .collect::<Vec<_>>();
        assert_eq!(block.hazards, hazards, "{} hazards", arena.slug);
        let lanes = arena
            .lanes
            .iter()
            .map(|lane| (lane.name.to_string(), lane.points.to_vec()))
            .collect::<Vec<_>>();
        assert_eq!(block.lanes, lanes, "{} lanes", arena.slug);
    }
}

fn mirror(b: Aabb) -> Aabb {
    Aabb {
        min: Vec3::new(-b.max.x, -b.max.y, b.min.z),
        max: Vec3::new(-b.min.x, -b.min.y, b.max.z),
    }
}

fn key(b: Aabb) -> [i32; 6] {
    [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z]
}

fn body(x: i32, y: i32, extra: i32) -> Aabb {
    Aabb {
        min: Vec3::new(x - RADIUS - extra, y - RADIUS - extra, 0),
        max: Vec3::new(x + RADIUS + extra, y + RADIUS + extra, HEIGHT),
    }
}

/// The closed box a segment sweeps with `half` clearance on each side.
fn corridor((x0, y0): (i32, i32), (x1, y1): (i32, i32), half: i32) -> Aabb {
    Aabb {
        min: Vec3::new(x0.min(x1) - half, y0.min(y1) - half, 0),
        max: Vec3::new(x0.max(x1) + half, y0.max(y1) + half, HEIGHT),
    }
}

fn axis_aligned(points: &[(i32, i32)]) -> bool {
    points
        .windows(2)
        .all(|p| (p[0].0 == p[1].0) != (p[0].1 == p[1].1))
}

#[test]
fn every_arena_satisfies_the_section_7_2_invariants() {
    for arena in &ARENAS {
        let name = arena.slug;
        let b = arena.bounds;
        let walls = arena.walls.iter().map(|w| w.aabb).collect::<Vec<_>>();
        // 1. Bounds, wall extents and heights.
        assert!(
            -GLOBAL_BOUNDS < b.min_x && b.max_x < GLOBAL_BOUNDS,
            "{name}"
        );
        assert!(
            -GLOBAL_BOUNDS < b.min_y && b.max_y < GLOBAL_BOUNDS,
            "{name}"
        );
        assert_eq!((b.min_x, b.min_y), (-b.max_x, -b.max_y), "{name}");
        for w in &walls {
            assert!(w.min.x < w.max.x && w.min.y < w.max.y && w.min.z < w.max.z);
            assert_eq!(w.min.z, 0, "{name} {w:?}");
            assert!(w.max.z >= MIN_WALL_HEIGHT, "{name} {w:?} is jumpable");
        }
        for w in &walls[4..] {
            assert!(b.contains(w.min.x, w.min.y) && b.contains(w.max.x, w.max.y));
        }
        // The perimeter: 1000 mm thick, just outside each edge.
        let (x1, y1, x2, y2) = (b.min_x, b.min_y, b.max_x, b.max_y);
        let h = walls[0].max.z;
        assert_eq!(
            walls[..4].iter().map(|w| key(*w)).collect::<Vec<_>>(),
            [
                [x1 - 1000, y1 - 1000, 0, x2 + 1000, y1, h],
                [x1 - 1000, y2, 0, x2 + 1000, y2 + 1000, h],
                [x1 - 1000, y1, 0, x1, y2, h],
                [x2, y1, 0, x2 + 1000, y2, h],
            ],
            "{name} perimeter"
        );
        // 2. Point symmetry of walls, hazards and spawns.
        let interior = walls[4..].iter().map(|w| key(*w)).collect::<BTreeSet<_>>();
        for w in &walls[4..] {
            assert!(
                interior.contains(&key(mirror(*w))),
                "{name} {w:?} unmirrored"
            );
        }
        for pair in walls[4..].chunks(2) {
            assert_eq!(pair[1], mirror(pair[0]), "{name} mirror pair order");
        }
        let hazards = arena.hazards.iter().map(|h| h.volume).collect::<Vec<_>>();
        for pair in arena.hazards.chunks(2) {
            assert_eq!(pair[1].volume, mirror(pair[0].volume));
            assert_eq!(
                (pair[1].kind, pair[1].damage, pair[1].period),
                (pair[0].kind, pair[0].damage, pair[0].period)
            );
        }
        let turned = |s: Spawn| Spawn {
            x: -s.x,
            y: -s.y,
            yaw: s.yaw.wrapping_add(32768),
        };
        for (t0, t1) in arena.team_spawns[0].iter().zip(&arena.team_spawns[1]) {
            assert_eq!(*t1, turned(*t0), "{name} team spawns");
        }
        for pair in arena.ffa_spawns.chunks(2) {
            assert_eq!(pair[1], turned(pair[0]), "{name} FFA pairs");
        }
        // 3. Wall counts.
        assert!(walls.len() - 4 >= 24 && walls.len() <= MAX_WALLS, "{name}");
        // 4. Spawns clear of walls, away from hazards, FFA spread out.
        for s in arena.spawns() {
            assert!(
                b.contains(s.x - RADIUS - 150, s.y - RADIUS - 150)
                    && b.contains(s.x + RADIUS + 150, s.y + RADIUS + 150)
            );
            let spawn = body(s.x, s.y, 150);
            assert!(!walls.iter().any(|w| w.overlaps(spawn)), "{name} {s:?}");
            for h in &hazards {
                let grown = h.expanded(3000, 0);
                assert!(
                    s.x <= grown.min.x
                        || s.x >= grown.max.x
                        || s.y <= grown.min.y
                        || s.y >= grown.max.y,
                    "{name} {s:?} near a hazard"
                );
            }
        }
        for (i, p) in arena.ffa_spawns.iter().enumerate() {
            for q in &arena.ffa_spawns[i + 1..] {
                assert!(p.position().horizontal_distance_squared(q.position()) >= 6000 * 6000);
            }
        }
        // 5. Control point.
        let c = arena.control;
        assert_eq!((c.x, c.y), (0, 0), "{name}");
        assert!(!walls.iter().any(|w| w.overlaps(body(c.x, c.y, 1000))));
        let disc = body(c.x, c.y, c.radius - RADIUS);
        assert!(!hazards.iter().any(|h| h.overlaps(disc)), "{name}");
        for s in arena.team_spawns.iter().flatten() {
            let d = i64::from(c.radius + 8000);
            assert!(s.position().horizontal_distance_squared(Vec3::default()) >= d * d);
        }
        // 6. Payload route.
        let route = arena.route;
        assert!(axis_aligned(route), "{name} route");
        for p in route.windows(3) {
            let collinear =
                (p[0].0 == p[1].0 && p[1].0 == p[2].0) || (p[0].1 == p[1].1 && p[1].1 == p[2].1);
            assert!(!collinear, "{name} collinear waypoint {:?}", p[1]);
        }
        for p in route.windows(2) {
            let lane = corridor(p[0], p[1], 600);
            assert!(
                !walls.iter().any(|w| w.overlaps(lane)),
                "{name} route {p:?}"
            );
            assert!(b.contains(lane.min.x, lane.min.y) && b.contains(lane.max.x, lane.max.y));
        }
        let (start, end) = (route[0], route[route.len() - 1]);
        let (t0, t1) = (arena.team_spawns[0][0], arena.team_spawns[1][0]);
        assert!(
            (t0.x..=t0.x + 3000).contains(&start.0),
            "{name} route start"
        );
        assert!((t1.x - 3000..=t1.x).contains(&end.0), "{name} route end");
        let [c1, c2, c3] = arena.checkpoints;
        assert!(0 < c1 && c1 < c2 && c2 < c3 && c3 < arena.route_length());
        // 7. Hazards.
        for h in arena.hazards {
            let v = h.volume;
            assert!(v.min.z == 0 && v.max.z <= 1000 && v.min.x < v.max.x && v.min.y < v.max.y);
            assert!((1..=40).contains(&h.damage) && (6..=60).contains(&h.period));
            assert!(b.contains(v.min.x, v.min.y) && b.contains(v.max.x, v.max.y));
            assert!(!walls.iter().any(|w| w.overlaps(v)), "{name} {}", h.label);
        }
        // 8. Lanes.
        let names = arena.lanes.iter().map(|l| l.name).collect::<Vec<_>>();
        assert_eq!(names, ["north", "south", "mid"]);
        for lane in arena.lanes {
            assert!(axis_aligned(lane.points), "{name} lane {}", lane.name);
            for p in lane.points.windows(2) {
                let path = corridor(p[0], p[1], 450);
                assert!(!walls.iter().any(|w| w.overlaps(path)), "{name} {p:?}");
                assert!(!hazards.iter().any(|h| h.overlaps(path)), "{name} {p:?}");
            }
            let (first, last) = (lane.points[0], lane.points[lane.points.len() - 1]);
            assert!(first.0 <= t0.x + 3000 && last.0 >= t1.x - 3000);
        }
        let north = arena.lanes[0].points;
        let south = north
            .iter()
            .rev()
            .map(|&(x, y)| (-x, -y))
            .collect::<Vec<_>>();
        assert_eq!(arena.lanes[1].points, south, "{name} south mirrors north");
    }
}

/// Invariant 9: reachability on a 100 mm walk grid of body centres clear of
/// every wall grown by the body radius, strictly inside the shrunk bounds.
#[test]
fn every_spawn_objective_and_lane_point_is_reachable_on_foot() {
    const GRID: i32 = 100;
    for arena in &ARENAS {
        let b = arena.bounds;
        let grown = arena
            .walls
            .iter()
            .map(|w| w.aabb.expanded(RADIUS, 0))
            .collect::<Vec<_>>();
        let (gx0, gx1) = ((b.min_x + RADIUS) / GRID + 1, (b.max_x - RADIUS) / GRID - 1);
        let (gy0, gy1) = ((b.min_y + RADIUS) / GRID + 1, (b.max_y - RADIUS) / GRID - 1);
        let width = (gx1 - gx0 + 1) as usize;
        let cells = width * (gy1 - gy0 + 1) as usize;
        let index = |gx: i32, gy: i32| (gy - gy0) as usize * width + (gx - gx0) as usize;
        let walkable = (0..cells)
            .map(|i| {
                let (gx, gy) = (gx0 + (i % width) as i32, gy0 + (i / width) as i32);
                let p = Vec3::new(gx * GRID, gy * GRID, 0);
                !grown.iter().any(|w| w.contains(p))
            })
            .collect::<Vec<_>>();
        let snap = |(x, y): (i32, i32)| {
            let round = |v: i32| (v + v.signum() * GRID / 2) / GRID;
            (round(x), round(y))
        };
        let start = snap((arena.team_spawns[0][0].x, arena.team_spawns[0][0].y));
        let mut seen = vec![false; cells];
        let mut queue = VecDeque::from([start]);
        seen[index(start.0, start.1)] = true;
        while let Some((gx, gy)) = queue.pop_front() {
            for (nx, ny) in [(gx + 1, gy), (gx - 1, gy), (gx, gy + 1), (gx, gy - 1)] {
                if (gx0..=gx1).contains(&nx)
                    && (gy0..=gy1).contains(&ny)
                    && walkable[index(nx, ny)]
                    && !seen[index(nx, ny)]
                {
                    seen[index(nx, ny)] = true;
                    queue.push_back((nx, ny));
                }
            }
        }
        let mut probes = arena
            .spawns()
            .map(|s| ("spawn", (s.x, s.y)))
            .collect::<Vec<_>>();
        probes.push(("control", (arena.control.x, arena.control.y)));
        probes.extend(arena.route.iter().map(|&p| ("route", p)));
        for lane in arena.lanes {
            probes.extend(lane.points.iter().map(|&p| ("lane", p)));
        }
        for (what, p) in probes {
            let (gx, gy) = snap(p);
            assert!(
                seen[index(gx, gy)],
                "{} {what} {p:?} is not reachable from team 0's first spawn",
                arena.slug
            );
        }
    }
}

fn config(mode: Mode, map: u8, max_ticks: u32) -> Config {
    Config {
        mode,
        map,
        max_ticks,
        base_bond: 0,
        offline: true,
    }
}

fn roster(count: usize, team_mode: bool) -> Vec<Participant> {
    (0..count)
        .map(|slot| Participant {
            team: if team_mode { (slot % 2) as u8 } else { 0 },
            class: (slot % 6) as u8,
            weapon: (slot % 6 * 2) as u8,
            bond: 0,
            special_entitled: false,
        })
        .collect()
}

/// A body at `p` intersects a wall's closed box.
fn inside_wall(arena: &Arena, p: Vec3) -> bool {
    let b = Aabb {
        min: Vec3::new(p.x - RADIUS, p.y - RADIUS, p.z),
        max: Vec3::new(p.x + RADIUS, p.y + RADIUS, p.z + HEIGHT),
    };
    arena.walls.iter().any(|w| w.aabb.overlaps(b))
}

#[test]
fn spawn_points_are_never_inside_walls_or_hazards_at_start_or_respawn() {
    for (map, arena) in ARENAS.iter().enumerate() {
        for (mode, count) in [
            (Mode::FreeForAll, 8),
            (Mode::Melee, 8),
            (Mode::Control, 12),
            (Mode::Payload, 12),
        ] {
            let mut w =
                World::new(config(mode, map as u8, 3600), &roster(count, mode.team())).unwrap();
            assert!(std::ptr::eq(w.arena(), arena));
            let mut spawned = w.players.iter().map(|p| p.position).collect::<Vec<_>>();
            // Kill everyone: each respawn then picks a spawn point again.
            for p in &mut w.players {
                p.alive = false;
                p.health = 0;
                p.respawn_ticks = 1;
            }
            w.step(&vec![Input::default(); count]).unwrap();
            assert!(
                w.players
                    .iter()
                    .all(|p| p.alive && p.spawn_protection == 120)
            );
            spawned.extend(w.players.iter().map(|p| p.position));
            for p in spawned {
                assert!(
                    !inside_wall(arena, p),
                    "{} {mode:?} spawn {p:?}",
                    arena.slug
                );
                assert!(
                    !arena
                        .hazards
                        .iter()
                        .any(|h| body(p.x, p.y, 0).overlaps(h.volume))
                );
                assert!(arena.spawns().any(|s| s.position() == p));
            }
        }
    }
}

#[test]
fn payload_route_is_walkable_and_clear_of_every_wall() {
    for arena in &ARENAS {
        let length = arena.route_length();
        assert_eq!(
            arena.route_point(0),
            Vec3::new(arena.route[0].0, arena.route[0].1, 0)
        );
        let end = arena.route[arena.route.len() - 1];
        assert_eq!(arena.route_point(length), Vec3::new(end.0, end.1, 0));
        assert_eq!(arena.route_point(length + 1000), arena.route_point(length));
        let mut previous = arena.route_point(0);
        for distance in (0..=length).step_by(10) {
            let p = arena.route_point(distance);
            // One exact step along an axis, never through a corner.
            assert_eq!(
                (p.x - previous.x).abs() + (p.y - previous.y).abs(),
                distance.min(10)
            );
            previous = p;
            // A body 250 mm off the line either side stays clear of walls.
            for (dx, dy) in [(0, 0), (250, 0), (-250, 0), (0, 250), (0, -250)] {
                let q = Vec3::new(p.x + dx, p.y + dy, 0);
                assert!(
                    !inside_wall(arena, q),
                    "{} route {distance} {q:?}",
                    arena.slug
                );
            }
        }
        for (k, &checkpoint) in arena.checkpoints.iter().enumerate() {
            let p = arena.route_point(checkpoint);
            assert!(!inside_wall(arena, p), "{} checkpoint {k}", arena.slug);
        }
    }
}

#[test]
fn a_jump_never_clears_or_lands_inside_any_wall() {
    // The apex of a standing jump.
    let mut w = World::new(config(Mode::FreeForAll, 0, 600), &roster(1, false)).unwrap();
    w.players[0].position = Vec3::default();
    let mut apex = 0;
    w.step(&[Input {
        buttons: JUMP,
        ..Input::default()
    }])
    .unwrap();
    for _ in 0..60 {
        apex = apex.max(w.players[0].position.z);
        w.step(&[Input::default()]).unwrap();
    }
    assert_eq!(apex, 1936);
    assert!(apex < MIN_WALL_HEIGHT);
    // Running and jumping at each of the lowest walls, from far enough away
    // to meet the face near the apex and from close by, never gets a body
    // into the wall.
    for (map, arena) in ARENAS.iter().enumerate() {
        let lowest = arena
            .walls
            .iter()
            .filter(|wall| wall.aabb.max.z == MIN_WALL_HEIGHT)
            .collect::<Vec<_>>();
        assert!(!lowest.is_empty(), "{} has low cover", arena.slug);
        let mut runs = 0;
        for wall in lowest {
            let a = wall.aabb;
            let (cx, cy) = ((a.min.x + a.max.x) / 2, (a.min.y + a.max.y) / 2);
            for gap in [1760, 200] {
                let approaches = [
                    (Vec3::new(a.min.x - RADIUS - gap, cy, 0), 0),
                    (Vec3::new(a.max.x + RADIUS + gap, cy, 0), 32768),
                    (Vec3::new(cx, a.min.y - RADIUS - gap, 0), 16384),
                    (Vec3::new(cx, a.max.y + RADIUS + gap, 0), 49152),
                ];
                for (start, yaw) in approaches {
                    let b = arena.bounds;
                    if inside_wall(arena, start)
                        || !b.contains(start.x - RADIUS, start.y - RADIUS)
                        || !b.contains(start.x + RADIUS, start.y + RADIUS)
                    {
                        continue;
                    }
                    let mut w =
                        World::new(config(Mode::FreeForAll, map as u8, 600), &roster(1, false))
                            .unwrap();
                    w.players[0].position = start;
                    let run = Input {
                        buttons: JUMP,
                        move_x: 127,
                        yaw,
                        ..Input::default()
                    };
                    for _ in 0..90 {
                        w.step(&[run]).unwrap();
                        let p = w.players[0].position;
                        let feet_to_head = Aabb {
                            min: Vec3::new(p.x - RADIUS, p.y - RADIUS, p.z),
                            max: Vec3::new(p.x + RADIUS, p.y + RADIUS, p.z + HEIGHT),
                        };
                        assert!(
                            !a.overlaps(feet_to_head),
                            "{} {}: {p:?}",
                            arena.slug,
                            wall.label
                        );
                    }
                    runs += 1;
                }
            }
        }
        assert!(runs >= 8, "{} exercised {runs} approaches", arena.slug);
    }
}

#[test]
fn map_digests_bind_every_rules_field_but_not_lanes() {
    let digests = ARENAS
        .iter()
        .map(Arena::map_digest)
        .collect::<BTreeSet<_>>();
    assert_eq!(digests.len(), ARENAS.len());
    let base = &ARENAS[0];
    let leak_walls = |walls: Vec<arena_core::maps::Wall>| &*Box::leak(walls.into_boxed_slice());
    let mut variants: Vec<Arena> = Vec::new();
    let mut bounds = *base;
    bounds.bounds.max_x -= 1;
    variants.push(bounds);
    let mut walls = base.walls.to_vec();
    walls[7].aabb.max.z += 1;
    variants.push(Arena {
        walls: leak_walls(walls),
        ..*base
    });
    let mut label = base.walls.to_vec();
    label[7].label = "renamed";
    let relabelled = Arena {
        walls: leak_walls(label),
        ..*base
    };
    let mut spawn = *base;
    spawn.team_spawns[1][5].yaw ^= 1;
    variants.push(spawn);
    let mut ffa = *base;
    ffa.ffa_spawns[11].x += 1;
    variants.push(ffa);
    let mut control = *base;
    control.control.radius += 1;
    variants.push(control);
    let mut route = base.route.to_vec();
    route[1].0 += 1;
    variants.push(Arena {
        route: Box::leak(route.into_boxed_slice()),
        ..*base
    });
    let mut checkpoints = *base;
    checkpoints.checkpoints[2] += 1;
    variants.push(checkpoints);
    let mut hazards = base.hazards.to_vec();
    hazards[1].period += 1;
    variants.push(Arena {
        hazards: Box::leak(hazards.into_boxed_slice()),
        ..*base
    });
    for variant in &variants {
        assert_ne!(variant.map_digest(), base.map_digest());
        assert_eq!(variant.lanes_digest(), base.lanes_digest());
    }
    // Labels and lanes are presentation data outside the map digest.
    assert_eq!(relabelled.map_digest(), base.map_digest());
    let mut lanes = *base;
    lanes.lanes[2].points = &[(0, 0), (1, 0)];
    assert_eq!(lanes.map_digest(), base.map_digest());
    assert_ne!(lanes.lanes_digest(), base.lanes_digest());
    // The configured arena is part of the canonical state hash.
    let a = World::new(config(Mode::FreeForAll, 0, 60), &roster(1, false)).unwrap();
    let mut b = a.clone();
    b.config.map = 1;
    assert_ne!(a.state_hash(), b.state_hash());
}

fn as_i32(value: &Value) -> i32 {
    i32::try_from(value.as_i64().expect("integer")).unwrap()
}

fn corners(value: &Value) -> Aabb {
    let min = value["min"].as_array().unwrap();
    let max = value["max"].as_array().unwrap();
    Aabb {
        min: Vec3::new(as_i32(&min[0]), as_i32(&min[1]), as_i32(&min[2])),
        max: Vec3::new(as_i32(&max[0]), as_i32(&max[1]), as_i32(&max[2])),
    }
}

fn pairs(value: &Value) -> Vec<(i32, i32)> {
    value
        .as_array()
        .unwrap()
        .iter()
        .map(|p| (as_i32(&p[0]), as_i32(&p[1])))
        .collect()
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

#[test]
fn checked_in_arena_export_matches_the_kernel() {
    let actual = arena_export::json();
    if std::env::var("ARENA_REGENERATE_ARENA_EXPORT").as_deref() == Ok("1") {
        std::fs::write(EXPORT, &actual).expect("write arena export");
    }
    let checked_in = std::fs::read_to_string(EXPORT).expect("read checked-in arena export");
    assert_eq!(
        actual, checked_in,
        "arena tables changed; regenerate with ARENA_REGENERATE_ARENA_EXPORT=1 and review"
    );
    let export: Value = serde_json::from_str(&checked_in).expect("valid JSON");
    assert_eq!(export["schema"], arena_export::SCHEMA);
    assert_eq!(export["rules_version"], RULES_VERSION);
    assert_eq!(
        (
            as_i32(&export["player"]["radius"]),
            as_i32(&export["player"]["height"]),
            as_i32(&export["player"]["eye_height"]),
            as_i32(&export["min_wall_height"]),
        ),
        (RADIUS, HEIGHT, EYE_HEIGHT, MIN_WALL_HEIGHT)
    );
    let arenas = export["arenas"].as_array().unwrap();
    assert_eq!(arenas.len(), ARENAS.len());
    for (map, (json, arena)) in arenas.iter().zip(&ARENAS).enumerate() {
        assert_eq!(json["id"], u64::from(arena.id));
        assert_eq!(json["slug"], arena.slug);
        assert_eq!(json["name"], arena.name);
        assert_eq!(json["map_digest"], hex(&arena.map_digest()));
        assert_eq!(json["lanes_digest"], hex(&arena.lanes_digest()));
        let b = &json["bounds"];
        assert_eq!(
            [&b["min_x"], &b["min_y"], &b["max_x"], &b["max_y"]].map(as_i32),
            [
                arena.bounds.min_x,
                arena.bounds.min_y,
                arena.bounds.max_x,
                arena.bounds.max_y
            ]
        );
        let walls = json["walls"].as_array().unwrap();
        assert_eq!(walls.len(), arena.walls.len());
        for (index, (w, wall)) in walls.iter().zip(arena.walls).enumerate() {
            assert_eq!(w["index"], index as u64);
            assert_eq!(w["label"], wall.label);
            assert_eq!(corners(w), wall.aabb);
        }
        let spawns = |set: &Value| {
            set.as_array()
                .unwrap()
                .iter()
                .map(|s| Spawn {
                    x: as_i32(&s["x"]),
                    y: as_i32(&s["y"]),
                    yaw: u16::try_from(s["yaw"].as_u64().unwrap()).unwrap(),
                })
                .collect::<Vec<_>>()
        };
        assert_eq!(spawns(&json["spawns"]["team0"]), arena.team_spawns[0]);
        assert_eq!(spawns(&json["spawns"]["team1"]), arena.team_spawns[1]);
        assert_eq!(spawns(&json["spawns"]["ffa"]), arena.ffa_spawns);
        let c = &json["control"];
        assert_eq!(
            [&c["x"], &c["y"], &c["radius"]].map(as_i32),
            [arena.control.x, arena.control.y, arena.control.radius]
        );
        let payload = &json["payload"];
        assert_eq!(as_i32(&payload["length"]), arena.route_length());
        assert_eq!(as_i32(&payload["push_radius"]), PAYLOAD_PUSH_RADIUS);
        assert_eq!(
            payload["checkpoints"]
                .as_array()
                .unwrap()
                .iter()
                .map(as_i32)
                .collect::<Vec<_>>(),
            arena.checkpoints
        );
        assert_eq!(pairs(&payload["route"]), arena.route);
        let hazards = json["hazards"].as_array().unwrap();
        assert_eq!(hazards.len(), arena.hazards.len());
        for (index, (h, hazard)) in hazards.iter().zip(arena.hazards).enumerate() {
            assert_eq!(h["index"], index as u64);
            assert_eq!(h["label"], hazard.label);
            assert_eq!(h["kind"], hazard.kind.name());
            assert_eq!(h["kind_id"], hazard.kind as u64);
            assert_eq!(corners(h), hazard.volume);
            assert_eq!(as_i32(&h["damage"]), hazard.damage);
            assert_eq!(h["period"], u64::from(hazard.period));
        }
        let lanes = json["lanes"].as_array().unwrap();
        assert_eq!(lanes.len(), arena.lanes.len());
        for (l, lane) in lanes.iter().zip(arena.lanes) {
            assert_eq!(l["name"], lane.name);
            assert_eq!(pairs(&l["points"]), lane.points);
        }
        // A live World uses exactly the exported data.
        let team = World::new(config(Mode::Control, map as u8, 60), &roster(12, true)).unwrap();
        for (slot, p) in team.players.iter().enumerate() {
            let s = &json["spawns"][format!("team{}", slot % 2)][slot / 2];
            assert_eq!(
                (p.position.x, p.position.y),
                (as_i32(&s["x"]), as_i32(&s["y"]))
            );
            assert_eq!(u64::from(p.yaw), s["yaw"].as_u64().unwrap());
        }
        let ffa = World::new(config(Mode::FreeForAll, map as u8, 60), &roster(8, false)).unwrap();
        for (slot, p) in ffa.players.iter().enumerate() {
            let s = &json["spawns"]["ffa"][slot];
            assert_eq!(
                (p.position.x, p.position.y),
                (as_i32(&s["x"]), as_i32(&s["y"]))
            );
            assert_eq!(u64::from(p.yaw), s["yaw"].as_u64().unwrap());
        }
        assert!(std::ptr::eq(ffa.arena(), arena));
    }
}

#[test]
fn projectiles_expire_where_they_leave_the_arena_bounds() {
    // A steep grenade from beside Nyaagyu Estate's east perimeter (top 6000,
    // bounds max_x 22000) clears the wall and expires at the bounds.
    let mut w = World::new(
        config(Mode::FreeForAll, 0, 600),
        &[Participant {
            team: 0,
            class: 3,
            weapon: 7,
            bond: 0,
            special_entitled: false,
        }],
    )
    .unwrap();
    let bounds = w.arena().bounds;
    w.players[0].position = Vec3::new(bounds.max_x - 1000, 0, 0);
    w.step(&[Input {
        buttons: arena_core::simulation::FIRE,
        pitch: 15_000,
        ..Input::default()
    }])
    .unwrap();
    let mut last = w.projectiles[0].clone();
    while let Some(p) = w.projectiles.first() {
        assert!(bounds.contains(p.position.x, p.position.y));
        last = p.clone();
        w.step(&[Input::default()]).unwrap();
    }
    assert!(last.position.z > 6000, "it flew over the perimeter wall");
    assert!(last.position.x + last.velocity.x > bounds.max_x);
    assert!(last.position.x <= bounds.max_x);
    assert!(w.tick < 100);
}
