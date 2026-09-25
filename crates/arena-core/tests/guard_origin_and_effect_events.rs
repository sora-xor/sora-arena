//! Rules 7: directional defense uses the damage origin, and guard/heal effects
//! are recorded as internal kernel events.
use arena_core::{
    catalog::CLASSES,
    math::Vec3,
    simulation::{
        ABILITY, BLOCK, Config, EntityKind, Event, FIRE, Input, Mode, Participant, Projectile,
        World,
    },
};

fn participant(team: u8, class: u8, weapon: u8) -> Participant {
    Participant {
        team,
        class,
        weapon,
        bond: 0,
        special_entitled: weapon >= 12,
    }
}

fn world(mode: Mode, roster: &[Participant]) -> World {
    World::new(
        Config {
            mode,
            map: 0,
            max_ticks: 600,
            base_bond: 0,
            offline: true,
        },
        roster,
    )
    .unwrap()
}

/// A grenadier and a guarding Samurai facing -X in open floor on Estate.
fn blast_duel(grenadier_x: i32) -> World {
    let mut w = world(
        Mode::FreeForAll,
        &[participant(0, 3, 7), participant(1, 0, 0)],
    );
    w.players[0].position = Vec3::new(grenadier_x, 0, 0);
    w.players[1].position = Vec3::new(1000, 0, 0);
    w
}

/// An armed grenade on its final range-limited step: it detonates at
/// `start + velocity` whatever it passes, without touching any body.
fn expiring_grenade(start: Vec3, velocity_x: i32) -> Projectile {
    Projectile {
        id: 9,
        owner: 0,
        position: start,
        velocity: Vec3::new(velocity_x, 0, 0),
        weapon: 7,
        traveled: 40_000 - 350,
        age: 1,
    }
}

fn guard_step(w: &mut World) {
    w.step(&[
        Input::default(),
        Input {
            buttons: BLOCK,
            yaw: 32768,
            ..Input::default()
        },
    ])
    .unwrap();
}

#[test]
fn blast_behind_a_guard_hits_in_full_even_when_its_thrower_stands_in_front() {
    // Rules 6 took the direction from the grenadier at x=-3000, in front of
    // the victim, and parried this. The detonation at x=3350 is behind it.
    let mut w = blast_duel(-3000);
    w.projectiles
        .push(expiring_grenade(Vec3::new(3000, 0, 1400), 350));
    guard_step(&mut w);
    assert!(w.projectiles.is_empty());
    assert_eq!(w.players[1].guard_ticks, 1);
    assert_eq!(w.players[1].health, CLASSES[0].health - 65);
    assert_eq!(w.players[1].stamina, 99);
    assert!(
        !w.events
            .iter()
            .any(|event| matches!(event, Event::Guarded { .. }))
    );
    assert!(w.events.contains(&Event::Damage {
        attacker: 0,
        victim: 1,
        amount: 65
    }));
}

#[test]
fn blast_in_front_of_a_guard_is_parried_or_halved_even_when_its_thrower_is_behind() {
    // Rules 6 used the grenadier at x=5000, behind the victim, and let this
    // frontal detonation at x=-1350 through in full.
    for (prior_guard_ticks, parried, prevented, stamina) in [(0, true, 65, 79), (9, false, 32, 80)]
    {
        let mut w = blast_duel(5000);
        for _ in 0..prior_guard_ticks {
            guard_step(&mut w);
        }
        w.projectiles
            .push(expiring_grenade(Vec3::new(-1000, 0, 1400), -350));
        guard_step(&mut w);
        assert!(w.projectiles.is_empty());
        assert_eq!(w.players[1].health, CLASSES[0].health - (65 - prevented));
        assert_eq!(w.players[1].stamina, stamina);
        let guarded = Event::Guarded {
            attacker: 0,
            victim: 1,
            weapon: 7,
            parried,
            prevented,
        };
        assert!(w.events.contains(&guarded));
        let damage = w
            .events
            .iter()
            .position(|event| matches!(event, Event::Damage { .. }));
        if parried {
            assert_eq!(damage, None, "a parry deals no damage");
        } else {
            let guard = w.events.iter().position(|event| event == &guarded);
            assert!(guard < damage, "Guarded precedes the halved Damage");
        }
    }
}

#[test]
fn hitscan_guard_events_report_parry_and_halving_in_order() {
    for (prior_guard_ticks, parried, prevented) in [(0, true, 22), (9, false, 11)] {
        let mut w = world(
            Mode::FreeForAll,
            &[participant(0, 0, 1), participant(1, 0, 1)],
        );
        w.players[0].position = Vec3::new(0, 0, 0);
        w.players[1].position = Vec3::new(5000, 0, 0);
        for _ in 0..prior_guard_ticks {
            guard_step(&mut w);
        }
        w.step(&[
            Input {
                buttons: FIRE,
                ..Input::default()
            },
            Input {
                buttons: BLOCK,
                yaw: 32768,
                ..Input::default()
            },
        ])
        .unwrap();
        let mut expected = vec![
            Event::Shot { slot: 0, weapon: 1 },
            Event::Guarded {
                attacker: 0,
                victim: 1,
                weapon: 1,
                parried,
                prevented,
            },
        ];
        if !parried {
            expected.push(Event::Damage {
                attacker: 0,
                victim: 1,
                amount: 22 - prevented,
            });
        }
        assert_eq!(w.events, expected);
        assert_eq!(w.players[1].health, CLASSES[0].health - (22 - prevented));
    }
}

#[test]
fn guard_facing_away_from_the_shooter_records_no_guard_event() {
    let mut w = world(
        Mode::FreeForAll,
        &[participant(0, 0, 1), participant(1, 0, 1)],
    );
    w.players[0].position = Vec3::new(0, 0, 0);
    w.players[1].position = Vec3::new(5000, 0, 0);
    w.step(&[
        Input {
            buttons: FIRE,
            ..Input::default()
        },
        Input {
            buttons: BLOCK,
            ..Input::default()
        },
    ])
    .unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::Shot { slot: 0, weapon: 1 },
            Event::Damage {
                attacker: 0,
                victim: 1,
                amount: 22
            }
        ]
    );
}

#[test]
fn healing_lance_reports_only_health_actually_restored() {
    let mut w = world(
        Mode::Control,
        &[participant(0, 5, 17), participant(0, 0, 1)],
    );
    w.players[0].position = Vec3::new(0, 0, 0);
    w.players[1].position = Vec3::new(3000, 0, 0);
    w.players[1].health = CLASSES[0].health - 5;
    let fire = [
        Input {
            buttons: FIRE,
            ..Input::default()
        },
        Input::default(),
    ];
    w.step(&fire).unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::Shot {
                slot: 0,
                weapon: 17
            },
            Event::Healed {
                healer: 0,
                target: 1,
                amount: 5,
                weapon: Some(17)
            }
        ]
    );
    // A full-health ally still absorbs the next shot, which restores nothing.
    for _ in 0..10 {
        w.step(&fire).unwrap();
    }
    assert_eq!(w.players[1].health, CLASSES[0].health);
    assert!(
        !w.events
            .iter()
            .any(|event| matches!(event, Event::Healed { .. }))
    );
}

#[test]
fn kusushi_area_heal_reports_each_restored_ally_but_never_an_enemy() {
    let mut w = world(
        Mode::Control,
        &[
            participant(0, 5, 11),
            participant(0, 0, 1),
            participant(0, 1, 3),
            participant(1, 0, 1),
        ],
    );
    for (slot, x) in [(0, 0), (1, 2000), (2, -2000), (3, 3000)] {
        w.players[slot].position = Vec3::new(x, 0, 0);
    }
    w.players[0].health = CLASSES[5].health - 10;
    w.players[1].health = 50;
    w.players[3].health = 50;
    w.step(&[
        Input {
            buttons: ABILITY,
            ..Input::default()
        },
        Input::default(),
        Input::default(),
        Input::default(),
    ])
    .unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::AbilityUsed { slot: 0, class: 5 },
            Event::Healed {
                healer: 0,
                target: 0,
                amount: 10,
                weapon: None
            },
            Event::Healed {
                healer: 0,
                target: 1,
                amount: 35,
                weapon: None
            },
            Event::EntitySpawned {
                id: 1,
                kind: EntityKind::Ward,
                owner: 0
            }
        ]
    );
    assert_eq!(w.players[2].health, CLASSES[1].health);
    assert_eq!(w.players[3].health, 50);
}
