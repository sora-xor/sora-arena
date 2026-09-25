//! Environmental hazards and the environmental kill credit
//! (docs/combat-rules.md §3.4, §9, §11) on Nyaagyu Estate's burning storehouse
//! embers: hazard 0 at x 3000..5000, y 13500..15500 and its mirror, hazard 1
//! at x -5000..-3000, y -15500..-13500. Both are fire: 10 damage every 15
//! ticks up to 600 mm above the floor.
use arena_core::{
    economy::{self, Allocation},
    math::Vec3,
    simulation::{ABILITY, BLOCK, Config, Event, FIRE, Input, Mode, Participant, World},
};

fn world(mode: Mode, offline: bool, roster: &[(u8, u8, u8)]) -> World {
    let bond = if offline { 0 } else { 1000 };
    let roster = roster
        .iter()
        .map(|&(team, class, weapon)| Participant {
            team,
            class,
            weapon,
            bond,
            special_entitled: false,
        })
        .collect::<Vec<_>>();
    World::new(
        Config {
            mode,
            map: 0,
            max_ticks: 3600,
            base_bond: bond,
            offline,
        },
        &roster,
    )
    .unwrap()
}

fn place(w: &mut World, slot: usize, x: i32, y: i32) {
    w.players[slot].position = Vec3::new(x, y, 0);
}

fn idle(count: usize) -> Vec<Input> {
    vec![Input::default(); count]
}

fn environmental(w: &World) -> Vec<(usize, u8, i32)> {
    w.events
        .iter()
        .filter_map(|event| match *event {
            Event::EnvironmentalDamage {
                victim,
                hazard,
                amount,
            } => Some((victim, hazard, amount)),
            _ => None,
        })
        .collect()
}

#[test]
fn hazards_pulse_on_period_ticks_inside_their_closed_volume_only() {
    let mut w = world(Mode::FreeForAll, true, &[(0, 0, 1); 5]);
    place(&mut w, 0, 4000, 14_500); // inside hazard 0
    place(&mut w, 1, 5000, 15_500); // on its closed corner
    place(&mut w, 2, 5001, 14_500); // 1 mm outside
    place(&mut w, 3, -3000, -13_500); // on hazard 1's corner
    place(&mut w, 4, 4000, 14_500); // inside, but protected
    w.players[4].spawn_protection = 20;
    let mut hits = Vec::new();
    for tick in 0..46 {
        w.step(&idle(5)).unwrap();
        hits.extend(environmental(&w).into_iter().map(|hit| (tick, hit)));
        assert!(!w.events.iter().any(|e| matches!(e, Event::Damage { .. })));
    }
    let mut expected = Vec::new();
    for tick in [0, 15, 30, 45] {
        expected.extend([(tick, (0, 0, 10)), (tick, (1, 0, 10)), (tick, (3, 1, 10))]);
        if tick >= 30 {
            // Spawn protection ran out after tick 19.
            expected.push((tick, (4, 0, 10)));
        }
    }
    expected.sort_by_key(|&(tick, (slot, _, _))| (tick, slot));
    assert_eq!(hits, expected);
    assert_eq!(w.players[2].health, 125);
    assert_eq!(w.players[4].health, 105);
    // Above the 600 mm top the fire does not reach.
    let mut w = world(Mode::FreeForAll, true, &[(0, 0, 1)]);
    place(&mut w, 0, 4000, 14_500);
    w.players[0].position.z = 1000;
    w.step(&idle(1)).unwrap();
    assert_eq!(w.players[0].position.z, 992);
    assert!(environmental(&w).is_empty());
}

#[test]
fn hazard_damage_is_warded_but_never_guarded_or_marked() {
    // Slot 0 guards, slot 1 is marked, slot 2 stands in its Kusushi ally's
    // ward. Only the ward changes the fire's 10 damage.
    let mut w = world(
        Mode::Control,
        true,
        &[(0, 0, 1), (0, 0, 1), (1, 0, 1), (1, 5, 11)],
    );
    place(&mut w, 0, 3500, 14_000);
    place(&mut w, 1, 4500, 14_000);
    place(&mut w, 2, -4000, -14_500);
    place(&mut w, 3, -2000, -14_500);
    w.players[1].marked_ticks = 100;
    w.tick = 14;
    let mut inputs = idle(4);
    inputs[0].buttons = BLOCK;
    inputs[3].buttons = ABILITY;
    w.step(&inputs).unwrap();
    assert!(w.players[0].guarding);
    assert!(w.entities.iter().any(|e| e.owner == 3));
    inputs[3].buttons = 0;
    w.step(&inputs).unwrap();
    assert_eq!(environmental(&w), vec![(0, 0, 10), (1, 0, 10), (2, 1, 7)]);
    assert!(!w.events.iter().any(|e| matches!(e, Event::Guarded { .. })));
    assert_eq!(w.players[0].stamina, 98);
}

#[test]
fn an_unassisted_environmental_death_credits_no_one_and_moves_no_value() {
    for mode in [Mode::FreeForAll, Mode::Control] {
        let mut w = world(mode, false, &[(0, 0, 1), (1, 0, 1)]);
        place(&mut w, 0, -4000, -14_500);
        place(&mut w, 1, 0, 0);
        w.players[0].health = 10;
        w.step(&idle(2)).unwrap();
        assert_eq!(
            w.events,
            vec![
                Event::EnvironmentalDamage {
                    victim: 0,
                    hazard: 1,
                    amount: 10
                },
                Event::Death {
                    victim: 0,
                    killer: None,
                    awards: Vec::new()
                }
            ]
        );
        let (victim, other) = (&w.accounts[0], &w.accounts[1]);
        assert_eq!(
            (victim.deaths, victim.paid_deaths, victim.remaining),
            (1, 0, 1000)
        );
        assert_eq!((other.kills, other.earnings), (0, 0));
        assert!(economy::conserved(&w.accounts));
        assert!(!w.players[0].alive);
    }
}

/// Slots 0 and 2 (team 0) shoot slot 1 (team 1) standing in hazard 1, from
/// 4000 mm either side, on ticks 1 and 2; the fire finishes it on tick 15.
#[test]
fn a_hazard_death_credits_the_last_enemy_to_damage_the_victim() {
    let mut w = world(
        Mode::Control,
        false,
        &[(0, 0, 1), (1, 0, 1), (0, 0, 1), (1, 0, 1)],
    );
    place(&mut w, 0, -8000, -14_500);
    place(&mut w, 1, -4000, -14_500);
    place(&mut w, 2, 0, -14_500);
    w.players[1].health = 64;
    let fire = |slot: usize, yaw: u16| {
        let mut inputs = idle(4);
        inputs[slot] = Input {
            buttons: FIRE,
            yaw,
            ..Input::default()
        };
        inputs
    };
    w.step(&idle(4)).unwrap();
    assert_eq!(environmental(&w), vec![(1, 1, 10)]);
    w.step(&fire(0, 0)).unwrap();
    w.step(&fire(2, 32768)).unwrap();
    assert_eq!(w.players[1].health, 10);
    while w.tick < 15 {
        w.step(&idle(4)).unwrap();
        assert!(environmental(&w).is_empty());
    }
    w.step(&idle(4)).unwrap();
    // 60% to the killer; the assist's 20% and the team's 20% both go to
    // slot 0, the killer's only other teammate.
    assert_eq!(
        w.events,
        vec![
            Event::EnvironmentalDamage {
                victim: 1,
                hazard: 1,
                amount: 10
            },
            Event::Death {
                victim: 1,
                killer: Some(2),
                awards: vec![
                    Allocation {
                        slot: 0,
                        amount: 40
                    },
                    Allocation {
                        slot: 2,
                        amount: 60
                    }
                ]
            }
        ]
    );
    assert_eq!(
        (w.accounts[1].remaining, w.accounts[1].paid_deaths),
        (900, 1)
    );
    assert_eq!((w.accounts[2].kills, w.accounts[0].kills), (1, 0));
    assert!(economy::conserved(&w.accounts));
}

#[test]
fn the_environmental_credit_lapses_with_the_assist_window() {
    // A shot on tick 0, then the victim steps into the fire for the pulse on
    // tick 300 (inside the 300-tick window) or tick 315 (outside it).
    for (pulse, killer) in [(300, Some(1)), (315, None)] {
        let mut w = world(Mode::FreeForAll, false, &[(0, 0, 1), (1, 0, 1)]);
        place(&mut w, 0, -2000, -14_500);
        place(&mut w, 1, 2000, -14_500);
        w.players[0].health = 32;
        w.step(&[
            Input::default(),
            Input {
                buttons: FIRE,
                yaw: 32768,
                ..Input::default()
            },
        ])
        .unwrap();
        assert_eq!(w.players[0].health, 10);
        while w.tick < pulse {
            w.step(&idle(2)).unwrap();
        }
        place(&mut w, 0, -4000, -14_500);
        w.step(&idle(2)).unwrap();
        let death = w
            .events
            .iter()
            .find_map(|event| match event {
                Event::Death {
                    victim,
                    killer,
                    awards,
                } => Some((*victim, *killer, awards.len())),
                _ => None,
            })
            .expect("the fire kills the victim");
        assert_eq!(death, (0, killer, usize::from(killer.is_some())));
        let transferred = if killer.is_some() { 100 } else { 0 };
        assert_eq!(w.accounts[0].remaining, 1000 - transferred);
        assert_eq!(w.accounts[1].earnings, transferred);
        assert!(economy::conserved(&w.accounts));
    }
}

#[test]
fn a_barricade_cannot_be_placed_over_a_hazard() {
    // Facing hazard 0 from its west side: 1500 mm ahead the box reaches the
    // embers at x = 3000; 500 mm further back it stands clear of them.
    for (x, placed) in [(1500, false), (1000, true)] {
        let mut w = world(Mode::FreeForAll, true, &[(0, 4, 9)]);
        place(&mut w, 0, x, 14_500);
        w.step(&[Input {
            buttons: ABILITY,
            ..Input::default()
        }])
        .unwrap();
        assert_eq!(w.entities.len(), usize::from(placed), "x = {x}");
        assert_eq!(w.players[0].ability_cooldown > 0, placed);
    }
}
