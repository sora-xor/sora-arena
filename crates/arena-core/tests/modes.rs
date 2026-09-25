//! Free-for-all and Melee (docs/combat-rules.md §1, §8.3, §8.4, §11):
//! melee-only admission, a staked melee duel to exhaustion on every arena,
//! and a bonded eight-player free-for-all that conserves value through
//! trades, simultaneous kills and exhaustion.
use arena_core::{
    catalog::{self, AttackKind},
    economy,
    maps::ARENAS,
    math::Vec3,
    simulation::{Config, Event, FIRE, Input, Mode, Participant, Winner, World},
};

fn config(mode: Mode, map: u8, base_bond: u64) -> Config {
    Config {
        mode,
        map,
        max_ticks: 36_000,
        base_bond,
        offline: base_bond == 0,
    }
}

fn participant(class: u8, weapon: u8, bond: u64, special_entitled: bool) -> Participant {
    Participant {
        team: 0,
        class,
        weapon,
        bond,
        special_entitled,
    }
}

#[test]
fn melee_mode_admits_only_melee_weapons_and_at_most_eight_players() {
    for class in 0..6u8 {
        for weapon in [class * 2, class * 2 + 1, 12 + class] {
            let special = weapon >= 12;
            let bond = if special { 2000 } else { 1000 };
            let admitted = World::new(
                config(Mode::Melee, 0, 1000),
                &[participant(class, weapon, bond, false)],
            );
            let melee = catalog::WEAPONS[usize::from(weapon)].kind == AttackKind::Melee;
            assert_eq!(admitted.is_ok(), melee, "class {class} weapon {weapon}");
            // The same loadout is admitted in free-for-all.
            assert!(
                World::new(
                    config(Mode::FreeForAll, 0, 1000),
                    &[participant(class, weapon, bond, false)]
                )
                .is_ok()
            );
        }
    }
    // The monofilament naginata is the only melee special.
    assert!(
        World::new(
            config(Mode::Melee, 1, 1000),
            &[participant(0, 12, 1000, true)]
        )
        .is_ok()
    );
    for mode in [Mode::Melee, Mode::FreeForAll] {
        let eight = vec![participant(0, 0, 0, false); 8];
        assert!(World::new(config(mode, 2, 0), &eight).is_ok());
        let nine = vec![participant(0, 0, 0, false); 9];
        assert!(World::new(config(mode, 2, 0), &nine).is_err());
    }
}

/// Slot 0 duels slot 1 with katanas at the arena's clear Control centre until
/// slot 1's reserve is exhausted.
#[test]
fn a_staked_melee_duel_ends_when_one_reserve_is_exhausted_on_every_arena() {
    for (map, arena) in ARENAS.iter().enumerate() {
        let mut w = World::new(
            config(Mode::Melee, map as u8, 1000),
            &[
                participant(0, 0, 1000, false),
                participant(0, 0, 1000, false),
            ],
        )
        .unwrap();
        let spawns = w.players.iter().map(|p| p.position).collect::<Vec<_>>();
        assert_eq!(
            spawns,
            [
                arena.ffa_spawns[0].position(),
                arena.ffa_spawns[1].position()
            ]
        );
        let strike = [
            Input {
                buttons: FIRE,
                ..Input::default()
            },
            Input::default(),
        ];
        let mut respawns = Vec::new();
        while !w.terminal {
            for (slot, x) in [(0, 0), (1, 1500)] {
                if w.players[slot].alive {
                    w.players[slot].position = Vec3::new(x, 0, 0);
                }
            }
            w.step(&strike).unwrap();
            for event in &w.events {
                match event {
                    Event::Shot { weapon, .. } => assert_eq!(*weapon, 0),
                    Event::Respawn { slot } => respawns.push(w.players[*slot].position),
                    _ => {}
                }
            }
            assert!(economy::conserved(&w.accounts));
            assert!(w.tick < 36_000, "{} duel did not finish", arena.slug);
        }
        assert_eq!(w.winner, Some(Winner::Slot(0)), "{}", arena.slug);
        assert!(w.exhausted(1) && !w.exhausted(0));
        assert_eq!((w.accounts[0].kills, w.accounts[0].earnings), (10, 1000));
        assert_eq!(
            (
                w.accounts[1].deaths,
                w.accounts[1].paid_deaths,
                w.accounts[1].remaining
            ),
            (10, 10, 0)
        );
        // Each respawn used the FFA spawn farthest from the living attacker.
        assert_eq!(respawns.len(), 9);
        for p in respawns {
            let farthest = arena
                .ffa_spawns
                .iter()
                .max_by_key(|s| {
                    (
                        s.position().horizontal_distance_squared(Vec3::default()),
                        std::cmp::Reverse(arena.ffa_spawns.iter().position(|o| o == *s)),
                    )
                })
                .unwrap();
            assert_eq!(p, farthest.position(), "{}", arena.slug);
        }
        assert!(matches!(
            w.events.as_slice(),
            [
                ..,
                Event::MatchWinner {
                    winner: Winner::Slot(0)
                },
                Event::Terminal
            ]
        ));
    }
}

/// Eight bonded hitscan players fight in pairs on four clear parallel lanes
/// through Nyaagyu Estate's courtyard. Whenever a reserve runs out the
/// survivors pair up again, until fewer than two hold a reserve.
#[test]
fn a_bonded_eight_player_free_for_all_conserves_every_unit() {
    let roster = [
        participant(0, 1, 1000, false),
        participant(1, 3, 1000, false),
        participant(2, 5, 1000, false),
        participant(4, 9, 1000, false),
        participant(5, 11, 1000, false),
        participant(1, 13, 2000, false),
        participant(2, 14, 1000, true),
        participant(5, 17, 2000, false),
    ];
    let mut w = World::new(config(Mode::FreeForAll, 0, 1000), &roster).unwrap();
    let deposited = roster.iter().map(|p| p.bond).sum::<u64>();
    assert_eq!(deposited, 10_000);
    let lanes = [1500, 500, -500, -1500];
    let mut simultaneous = 0;
    let mut deaths = 0;
    while !w.terminal {
        let holding = (0..8)
            .filter(|&slot| !w.exhausted(slot))
            .collect::<Vec<_>>();
        let mut inputs = [Input::default(); 8];
        for (index, &slot) in holding.iter().enumerate() {
            let (lane, side) = (lanes[index / 2], index % 2);
            if side == 0 && index + 1 == holding.len() {
                // An odd player out waits clear of every lane.
                if w.players[slot].alive {
                    w.players[slot].position = Vec3::new(0, -14_500, 0);
                }
                continue;
            }
            if w.players[slot].alive {
                w.players[slot].position = Vec3::new(if side == 0 { -3000 } else { 3000 }, lane, 0);
            }
            inputs[slot] = Input {
                buttons: FIRE,
                yaw: if side == 0 { 0 } else { 32768 },
                ..Input::default()
            };
        }
        w.step(&inputs).unwrap();
        let died = w
            .events
            .iter()
            .filter(|e| matches!(e, Event::Death { .. }))
            .count();
        deaths += died;
        simultaneous += usize::from(died > 1);
        assert!(economy::conserved(&w.accounts));
        let total = w
            .accounts
            .iter()
            .map(|a| a.remaining + a.earnings)
            .sum::<u64>();
        assert_eq!(total, deposited);
        assert!(w.tick < 36_000, "free-for-all did not finish");
    }
    let holding = (0..8).filter(|&slot| !w.exhausted(slot)).count();
    assert!(holding < 2);
    assert!(simultaneous > 0, "no simultaneous kills were exercised");
    // Every paid death moved exactly a tenth of its victim's deposit.
    let paid = w
        .accounts
        .iter()
        .map(|a| u64::from(a.paid_deaths) * a.initial / 10)
        .sum::<u64>();
    assert_eq!(paid, w.accounts.iter().map(|a| a.earnings).sum::<u64>());
    assert_eq!(
        deaths as u32,
        w.accounts.iter().map(|a| a.deaths).sum::<u32>()
    );
    let kills = w.accounts.iter().map(|a| a.kills).collect::<Vec<_>>();
    let best = *kills.iter().max().unwrap();
    let leaders = (0..8)
        .filter(|&slot| kills[slot] == best)
        .collect::<Vec<_>>();
    let fewest = leaders.iter().map(|&s| w.accounts[s].deaths).min().unwrap();
    let winners = leaders
        .into_iter()
        .filter(|&s| w.accounts[s].deaths == fewest)
        .collect::<Vec<_>>();
    let expected = match winners.as_slice() {
        [slot] => Winner::Slot(*slot),
        _ => Winner::Draw,
    };
    assert_eq!(w.winner, Some(expected));
    eprintln!(
        "ticks={} deaths={deaths} simultaneous={simultaneous} kills={kills:?} winner={:?}",
        w.tick, w.winner
    );
}

#[test]
fn the_free_for_all_winner_breaks_kill_ties_by_fewest_deaths() {
    for (mode, kills, deaths, winner) in [
        (Mode::FreeForAll, [2, 2, 1], [3, 1, 0], Winner::Slot(1)),
        (Mode::Melee, [0, 4, 1], [9, 9, 0], Winner::Slot(1)),
        (Mode::FreeForAll, [2, 2, 0], [1, 1, 0], Winner::Draw),
        (Mode::Melee, [0, 0, 0], [0, 0, 0], Winner::Draw),
    ] {
        let mut w = World::new(
            Config {
                max_ticks: 10,
                ..config(mode, 3, 0)
            },
            &[0, 1, 2].map(|_| participant(0, 0, 0, false)),
        )
        .unwrap();
        for slot in 0..3 {
            w.accounts[slot].kills = kills[slot];
            w.accounts[slot].deaths = deaths[slot];
        }
        while !w.terminal {
            w.step(&[Input::default(); 3]).unwrap();
        }
        assert_eq!((w.tick, w.winner), (10, Some(winner)));
    }
}
