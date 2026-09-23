//! Clean-lane body-shot timings through the canonical 60 Hz simulation.
use arena_core::{
    catalog::CLASSES,
    math::Vec3,
    simulation::{Config, Event, FIRE, Input, Mode, Participant, World},
};

fn duel(attacker_class: u8, weapon: u8, target_class: u8) -> World {
    let mut world = World::new(
        Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 600,
            base_bond: 0,
            offline: true,
        },
        &[
            Participant {
                team: 0,
                class: attacker_class,
                weapon,
                bond: 0,
                special_entitled: false,
            },
            Participant {
                team: 1,
                class: target_class,
                weapon: target_class * 2,
                bond: 0,
                special_entitled: false,
            },
        ],
    )
    .unwrap();
    // Fresh admissions have no respawn protection. The clear 5 m lane is
    // inside both guns' range and outside every Estate obstacle.
    assert_eq!(world.players[1].spawn_protection, 0);
    world.players[0].position = Vec3::new(0, 0, 0);
    world.players[1].position = Vec3::new(5000, 0, 0);
    world
}

#[test]
fn standard_hitscan_body_shots_meet_the_open_lane_timing_band() {
    // Death tick is zero-based from the first held-trigger input. One additional
    // tick gives elapsed simulation duration; for example, tick 48 is 49/60 s.
    for (class, weapon, target_class, target_hp, death_tick, expected_hits) in [
        (0, 1, 1, 100, 48, 5), // Arc -> 100 HP
        (0, 1, 0, 125, 60, 6), // Arc -> 125 HP
        (0, 1, 3, 150, 72, 7), // Arc -> 150 HP
        (4, 9, 1, 100, 48, 5), // Clockwork -> 100 HP
        (4, 9, 0, 125, 72, 7), // Clockwork -> 125 HP
        (4, 9, 3, 150, 84, 8), // Clockwork -> 150 HP
    ] {
        let mut world = duel(class, weapon, target_class);
        assert_eq!(CLASSES[target_class as usize].health, target_hp);
        let mut hit_count = 0;
        let mut shot_count = 0;
        let mut observed_death = None;
        for tick in 0..=death_tick {
            world
                .step(&[
                    Input {
                        buttons: FIRE,
                        ..Input::default()
                    },
                    Input::default(),
                ])
                .unwrap();
            for event in &world.events {
                match event {
                    Event::Shot {
                        slot: 0,
                        weapon: fired,
                    } if *fired == weapon => {
                        shot_count += 1;
                    }
                    Event::Damage {
                        attacker: 0,
                        victim: 1,
                        ..
                    } => hit_count += 1,
                    Event::Death { victim: 1, .. } => observed_death = Some(tick),
                    _ => {}
                }
            }
            if tick < death_tick {
                assert!(world.players[1].alive, "weapon {weapon} killed early");
            }
        }
        assert_eq!(world.players[1].health, 0);
        assert_eq!(observed_death, Some(death_tick), "weapon {weapon}");
        assert_eq!(shot_count, expected_hits, "weapon {weapon}");
        assert_eq!(hit_count, expected_hits, "weapon {weapon}");
    }
}
