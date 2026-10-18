//! Live kernel geometry reference vectors for the native staged ray-selection AIR.
//! This fixture covers target selection, not attack admission, full execution or settlement.

use arena_core::{
    RULES_VERSION,
    maps::ARENAS,
    math::{Aabb, Vec3, direction, scale_q15},
    simulation::{Config, Entity, EntityKind, Event, FIRE, Input, Mode, Participant, World},
};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

const FIXTURE: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/tests/data/staged_hit_reference.json"
);

#[derive(Clone)]
struct Case {
    name: String,
    attacker: usize,
    // Team mode, melee, allies, range, yaw, pitch.
    controls: [i64; 6],
    // Position xyz, team, alive, protection, in original slot order.
    players: Vec<[i64; 6]>,
    // Minimum xyz, maximum xyz.
    walls: Vec<[i64; 6]>,
    // Id, kind, owner, team, position xyz, half extents xy; increasing id order.
    entities: Vec<[i64; 9]>,
}

fn vec3(v: &[i64]) -> Vec3 {
    Vec3::new(
        v[0].try_into().unwrap(),
        v[1].try_into().unwrap(),
        v[2].try_into().unwrap(),
    )
}

impl Case {
    fn base(name: &str) -> Self {
        Self {
            name: name.into(),
            attacker: 0,
            controls: [0, 0, 0, 45000, 0, 0],
            players: vec![
                [0, 0, 0, 0, 1, 0],
                [2000, 0, 0, 1, 1, 0],
                [4000, 0, 0, 1, 1, 0],
            ],
            walls: vec![],
            entities: vec![],
        }
    }
    fn ray(&self) -> (Vec3, Vec3) {
        let from = vec3(&self.players[self.attacker]).offset(Vec3::new(0, 0, 1400));
        let to = from.offset(scale_q15(
            direction(self.controls[4] as u16, self.controls[5] as i16),
            self.controls[3] as i32,
        ));
        (from, to)
    }
    fn expected(&self) -> [i64; 3] {
        let (from, to) = self.ray();
        // The arithmetic is the actual kernel's Aabb::intersect, not the AIR's
        // clipped-plane or polynomial implementation. This fold mirrors ray_stop.
        let mut nearest = (1 << 20) + 1;
        let mut result = [0, 0, 0];
        let mut consider = |body: Aabb, kind, id| {
            if let Some(t) = body.intersect(from, to)
                && t < nearest
            {
                nearest = t;
                result = [kind, id, t];
            }
        };
        for b in &self.walls {
            consider(
                Aabb {
                    min: vec3(b),
                    max: vec3(&b[3..]),
                },
                1,
                0,
            );
        }
        let team = self.players[self.attacker][3];
        let expansion = self.controls[1] * 180;
        for e in &self.entities {
            let enemy = if self.controls[0] != 0 {
                e[3] != team
            } else {
                e[2] != self.attacker as i64
            };
            if e[1] != 2 && !(e[1] == 1 && enemy) {
                continue;
            }
            let height = if e[1] == 1 { 1700 } else { 2000 };
            let body = Aabb {
                min: Vec3::new((e[4] - e[7]) as i32, (e[5] - e[8]) as i32, e[6] as i32),
                max: Vec3::new(
                    (e[4] + e[7]) as i32,
                    (e[5] + e[8]) as i32,
                    (e[6] + height) as i32,
                ),
            }
            .expanded(if e[1] == 1 { expansion as i32 } else { 0 }, 0);
            consider(body, 2, e[0]);
        }
        for (slot, p) in self.players.iter().enumerate() {
            let enemy = slot != self.attacker && (self.controls[0] == 0 || p[3] != team);
            if slot == self.attacker
                || (!enemy && self.controls[2] == 0)
                || p[4] == 0
                || (enemy && p[5] > 0)
            {
                continue;
            }
            let radius = 350 + expansion;
            consider(
                Aabb {
                    min: Vec3::new((p[0] - radius) as i32, (p[1] - radius) as i32, p[2] as i32),
                    max: Vec3::new(
                        (p[0] + radius) as i32,
                        (p[1] + radius) as i32,
                        (p[2] + 1700) as i32,
                    ),
                },
                3,
                slot as i64,
            );
        }
        result
    }
    fn json(&self) -> Value {
        let (a, b) = self.ray();
        json!({"name":self.name,"attacker":self.attacker,"controls":self.controls,
            "players":self.players,"walls":self.walls,"entities":self.entities,
            "ray":[[a.x,a.y,a.z],[b.x,b.y,b.z]],"expected":self.expected()})
    }
}

fn cases() -> Vec<Case> {
    let mut cases = vec![Case::base("nearest_player")];
    let mut add = |name: &str, change: fn(&mut Case)| {
        let mut c = Case::base(name);
        change(&mut c);
        cases.push(c);
    };
    add("wall_before_player", |c| {
        c.walls.push([1000, -1000, 0, 1200, 1000, 3000])
    });
    add("wall_tie_beats_player", |c| {
        c.walls.push([1650, -350, 0, 2350, 350, 1700])
    });
    add("wall_beyond_segment", |c| {
        c.walls.push([50000, -1000, 0, 51000, 1000, 3000])
    });
    add("lower_slot_wins_tie", |c| c.players[2] = c.players[1]);
    add("dead_target_skipped", |c| c.players[1][4] = 0);
    add("protected_enemy_skipped", |c| c.players[1][5] = 1);
    add("ally_skipped", |c| {
        c.controls[0] = 1;
        c.players[1][3] = 0;
    });
    add("protected_ally_healable", |c| {
        c.controls[0] = 1;
        c.controls[2] = 1;
        c.players[1][3] = 0;
        c.players[1][5] = 65535;
    });
    add("protected_enemy_still_skipped_for_heal", |c| {
        c.controls[0] = 1;
        c.controls[2] = 1;
        c.players[1][5] = 65535;
    });
    add("self_always_excluded", |c| {
        c.controls[2] = 1;
        c.players.truncate(1);
    });
    add("parallel_closed_body_edge", |c| {
        c.players[1][1] = 350;
        c.players[2][1] = 10000;
    });
    add("parallel_outside_body", |c| {
        c.players[1][1] = 351;
        c.players[2][1] = 10000;
    });
    add("melee_widened_body_edge", |c| {
        c.controls[1] = 1;
        c.players[1][1] = 530;
    });
    add("segment_endpoint_closed", |c| {
        c.controls[3] = 1650;
    });
    add("segment_ends_before_body", |c| {
        c.controls[3] = 1649;
    });
    add("start_inside_target", |c| {
        c.players[1][0] = 0;
    });
    add("opposite_direction", |c| {
        c.controls[4] = 32768;
        c.players[1][0] = -2000;
    });
    add("vertical_up", |c| {
        c.controls[5] = 16384;
        c.players[1] = [0, 0, 3000, 1, 1, 0];
    });
    add("vertical_down", |c| {
        c.controls[5] = -16384;
        c.players[1] = [0, 0, -1000, 1, 1, 0];
    });
    add("friendly_barricade_blocks", |c| {
        c.controls[0] = 1;
        c.entities.push([7, 2, 0, 0, 1000, 0, 0, 300, 300]);
    });
    add("enemy_decoy_blocks", |c| {
        c.entities.push([8, 1, 1, 1, 1000, 0, 0, 350, 350])
    });
    add("own_decoy_ignored_ffa", |c| {
        c.entities.push([8, 1, 0, 0, 1000, 0, 0, 350, 350])
    });
    add("team_decoy_ignored", |c| {
        c.controls[0] = 1;
        c.entities.push([8, 1, 1, 0, 1000, 0, 0, 350, 350]);
    });
    add("entity_wins_player_tie", |c| {
        c.entities.push([8, 1, 1, 1, 2000, 0, 0, 350, 350])
    });
    add("lower_entity_id_wins_tie", |c| {
        c.entities.push([8, 1, 1, 1, 1000, 0, 0, 350, 350]);
        c.entities.push([20, 2, 2, 1, 1000, 0, 0, 350, 350]);
    });
    add("wall_wins_entity_tie", |c| {
        c.entities.push([8, 2, 1, 1, 1000, 0, 0, 350, 350]);
        c.walls.push([650, -350, 0, 1350, 350, 2000]);
    });
    add("melee_widens_decoy", |c| {
        c.controls[1] = 1;
        c.entities.push([9, 1, 1, 1, 1000, 530, 0, 350, 350]);
    });
    add("melee_does_not_widen_barricade", |c| {
        c.controls[1] = 1;
        c.entities.push([9, 2, 1, 1, 1000, 351, 0, 350, 350]);
    });
    add("zones_and_wards_do_not_block", |c| {
        c.entities.push([9, 3, 1, 1, 1000, 0, 0, 4000, 4000]);
        c.entities.push([11, 4, 2, 1, 1000, 0, 0, 4000, 4000]);
    });
    add("attacker_one_targets_original_slot_zero", |c| {
        c.attacker = 1;
        c.controls[4] = 32768;
    });
    add("attacker_two_ignores_own_decoy", |c| {
        c.attacker = 2;
        c.controls[4] = 32768;
        c.entities
            .push([u32::MAX as i64, 1, 2, 1, 3000, 0, 0, 350, 350]);
    });
    for (index, arena) in ARENAS.iter().enumerate() {
        for yaw in [0, 8192, 16384, 24576, 32768, 49152, 65535] {
            let mut c = Case::base(&format!("map_{index}_yaw_{yaw}"));
            c.controls[4] = yaw;
            c.walls = arena
                .walls
                .iter()
                .map(|w| {
                    let b = w.aabb;
                    [
                        b.min.x as i64,
                        b.min.y as i64,
                        b.min.z as i64,
                        b.max.x as i64,
                        b.max.y as i64,
                        b.max.z as i64,
                    ]
                })
                .collect();
            cases.push(c);
        }
    }
    let mut seed = 0xc0ffeecafef00d_u64;
    let mut random = |n: i64| {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        (seed % n as u64) as i64
    };
    for index in 0..32 {
        let mut c = Case::base(&format!("bounded_random_{index}"));
        c.controls = [
            random(2),
            random(2),
            random(2),
            1 + random(70000),
            random(65536),
            random(32769) - 16384,
        ];
        c.players = (0..12)
            .map(|slot| {
                [
                    random(40001) - 20000,
                    random(40001) - 20000,
                    random(3000),
                    random(2),
                    i64::from(slot == 0 || random(2) == 1),
                    random(3),
                ]
            })
            .collect();
        c.attacker = index % 12;
        c.players[c.attacker][4] = 1;
        c.walls = (0..64)
            .map(|_| {
                let x = random(40001) - 20000;
                let y = random(40001) - 20000;
                let z = random(5000) - 1000;
                [
                    x,
                    y,
                    z,
                    x + random(1000),
                    y + random(1000),
                    z + random(3000),
                ]
            })
            .collect();
        c.entities = (0..48)
            .map(|i| {
                [
                    1 + i,
                    1 + i % 4,
                    i / 4,
                    c.players[(i / 4) as usize][3],
                    random(40001) - 20000,
                    random(40001) - 20000,
                    0,
                    100 + random(1000),
                    100 + random(1000),
                ]
            })
            .collect();
        cases.push(c);
    }
    cases
}

fn fixture() -> Value {
    let digest = |bytes: &[u8]| {
        Sha256::digest(bytes)
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect::<String>()
    };
    json!({"schema":"sora-arena-staged-hit-reference","rules":RULES_VERSION,
        "scope":"ray selection only; no attack legality, full execution, admission or settlement",
        "math_sha256":digest(include_bytes!("../src/math.rs")),
        "simulation_sha256":digest(include_bytes!("../src/simulation.rs")),
        "tick_sha256":digest(include_bytes!("../src/simulation/tick.rs")),
        "abilities_sha256":digest(include_bytes!("../src/simulation/abilities.rs")),
        "cases":cases().iter().map(Case::json).collect::<Vec<_>>()})
}

#[test]
fn reference_vectors_match_live_kernel_geometry() {
    let actual = fixture();
    if std::env::var_os("ARENA_REGENERATE_STAGED_HIT_FIXTURE").is_some() {
        std::fs::write(
            FIXTURE,
            format!("{}\n", serde_json::to_string_pretty(&actual).unwrap()),
        )
        .unwrap();
    }
    let expected: Value = serde_json::from_slice(&std::fs::read(FIXTURE).unwrap()).unwrap();
    assert_eq!(actual, expected);
}

#[test]
fn reference_target_fold_agrees_with_actual_world_fire() {
    // Check the separate reference fold against the private runtime ray_stop
    // through observable shots/damage. No production visibility change is needed.
    let mut exercised = 0;
    for case in cases().into_iter().take(30).filter(|c| {
        c.players.len() == 3 && c.walls.is_empty() && c.players.iter().all(|p| p[2] == 0)
    }) {
        let weapon = if case.controls[2] != 0 {
            17
        } else if case.controls[1] != 0 {
            0
        } else {
            1
        };
        let mut world = World::new(
            Config {
                mode: if case.controls[0] != 0 {
                    Mode::Control
                } else {
                    Mode::FreeForAll
                },
                map: 0,
                max_ticks: 60,
                base_bond: 0,
                offline: true,
            },
            &(0..3)
                .map(|slot| Participant {
                    team: case.players[slot][3] as u8,
                    class: if slot == 0 && weapon == 17 { 5 } else { 0 },
                    weapon: if slot == 0 { weapon } else { 1 },
                    bond: 0,
                    special_entitled: slot == 0 && weapon == 17,
                })
                .collect::<Vec<_>>(),
        )
        .unwrap();
        for (p, values) in world.players.iter_mut().zip(&case.players) {
            p.position = vec3(values);
            p.alive = values[4] != 0;
            p.spawn_protection = if values[5] > 0 { 2 } else { 0 };
            p.respawn_ticks = 100;
            p.health = 50;
        }
        world.entities = case
            .entities
            .iter()
            .map(|e| {
                let kind = match e[1] {
                    1 => EntityKind::Decoy,
                    2 => EntityKind::Barricade,
                    3 => EntityKind::FireZone,
                    4 => EntityKind::Ward,
                    _ => unreachable!(),
                };
                Entity {
                    id: e[0] as u32,
                    kind,
                    owner: e[2] as usize,
                    team: e[3] as u8,
                    position: vec3(&e[4..]),
                    yaw: 0,
                    health: kind.max_health(),
                    age: 0,
                    half_x: e[7] as i32,
                    half_y: e[8] as i32,
                }
            })
            .collect();
        let mut current = case.clone();
        current.controls[3] = i64::from(arena_core::catalog::WEAPONS[weapon as usize].range_mm);
        current.walls = world
            .arena()
            .walls
            .iter()
            .map(|w| {
                let b = w.aabb;
                [
                    b.min.x as i64,
                    b.min.y as i64,
                    b.min.z as i64,
                    b.max.x as i64,
                    b.max.y as i64,
                    b.max.z as i64,
                ]
            })
            .collect();
        let expected = current.expected();
        let mut inputs = vec![Input::default(); 3];
        inputs[0] = Input {
            buttons: FIRE,
            yaw: case.controls[4] as u16,
            pitch: case.controls[5] as i16,
            ..Input::default()
        };
        world.step(&inputs).unwrap();
        assert!(
            world
                .events
                .iter()
                .any(|e| matches!(e, Event::Shot { slot: 0, .. })),
            "{}",
            case.name
        );
        let targets = world
            .events
            .iter()
            .filter_map(|e| match e {
                Event::Damage {
                    attacker: 0,
                    victim,
                    ..
                } => Some((3, *victim as i64)),
                Event::Healed {
                    healer: 0,
                    target,
                    weapon: Some(17),
                    ..
                } => Some((3, *target as i64)),
                Event::EntityDamaged {
                    attacker: 0, id, ..
                } => Some((2, i64::from(*id))),
                _ => None,
            })
            .collect::<Vec<_>>();
        assert_eq!(
            targets,
            if expected[0] == 3 {
                vec![(3, expected[1])]
            } else if expected[0] == 2
                && current.entities.iter().any(|e| e[0] == expected[1]
                    && if current.controls[0] != 0 {
                        e[3] != current.players[0][3]
                    } else {
                        e[2] != 0
                    })
            {
                vec![(2, expected[1])]
            } else {
                vec![]
            },
            "{}",
            case.name
        );
        exercised += 1;
    }
    assert_eq!(
        exercised, 23,
        "directed runtime comparison coverage changed"
    );
}
