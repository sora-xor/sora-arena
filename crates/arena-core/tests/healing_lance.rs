//! Healing Lance behavior through canonical 60 Hz inputs and team targeting.
use arena_core::{
    catalog::CLASSES,
    math::Vec3,
    simulation::{Config, Event, FIRE, Input, Mode, Participant, RESPAWN_TICKS, World},
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

fn team_world() -> World {
    let mut world = World::new(
        Config {
            mode: Mode::Control,
            map: 0,
            max_ticks: 600,
            base_bond: 0,
            offline: true,
        },
        &[
            participant(0, 5, 17),
            participant(0, 0, 1),
            participant(1, 0, 1),
        ],
    )
    .unwrap();
    world.players[0].position = Vec3::new(0, 0, 0);
    world.players[1].position = Vec3::new(3000, 0, 0);
    world.players[2].position = Vec3::new(6000, 0, 0);
    world
}

fn fire(world: &mut World, enemy_buttons: u32) {
    world
        .step(&[
            Input {
                buttons: FIRE,
                ..Input::default()
            },
            Input::default(),
            Input {
                buttons: enemy_buttons,
                yaw: 32768,
                ..Input::default()
            },
        ])
        .unwrap();
}

#[test]
fn nearer_ally_is_healed_and_blocks_a_lance_shot_from_reaching_an_enemy() {
    let mut world = team_world();
    world.players[1].health = 80;
    fire(&mut world, 0);
    assert_eq!(world.players[1].health, 95);
    assert_eq!(world.players[2].health, CLASSES[0].health);
    assert_eq!(world.players[0].health, CLASSES[5].health);
    assert_eq!(world.players[0].ammo, 15);
    assert!(world.events.iter().any(|event| matches!(
        event,
        Event::Shot {
            slot: 0,
            weapon: 17
        }
    )));
    assert!(
        !world
            .events
            .iter()
            .any(|event| matches!(event, Event::Damage { .. }))
    );
    assert!(world.damage_history.is_empty());
}

#[test]
fn nearer_enemy_takes_damage_and_is_never_healed() {
    let mut world = team_world();
    world.players[1].position = Vec3::new(6000, 0, 0);
    world.players[2].position = Vec3::new(3000, 0, 0);
    world.players[1].health = 80;
    world.players[2].health = 50;
    fire(&mut world, 0);
    assert_eq!(world.players[1].health, 80);
    assert_eq!(world.players[2].health, 35);
    assert!(world.events.iter().any(|event| matches!(
        event,
        Event::Damage {
            attacker: 0,
            victim: 2,
            amount: 15
        }
    )));
    assert_eq!(world.damage_history.len(), 1);
}

#[test]
fn healing_caps_at_class_maximum_and_never_revives_a_dead_ally() {
    let mut world = team_world();
    world.players[1].health = CLASSES[0].health - 5;
    fire(&mut world, 0);
    assert_eq!(world.players[1].health, CLASSES[0].health);
    for _ in 0..10 {
        fire(&mut world, 0);
    }
    assert_eq!(world.players[1].health, CLASSES[0].health);

    let mut world = team_world();
    world.players[1].alive = false;
    world.players[1].health = 0;
    world.players[1].respawn_ticks = RESPAWN_TICKS;
    fire(&mut world, 0);
    assert!(!world.players[1].alive);
    assert_eq!(world.players[1].health, 0);
    assert_eq!(world.players[2].health, CLASSES[0].health - 15);
}

#[test]
fn ffa_lance_damages_even_when_team_numbers_happen_to_match() {
    let mut world = World::new(
        Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 600,
            base_bond: 0,
            offline: true,
        },
        &[participant(0, 5, 17), participant(0, 0, 1)],
    )
    .unwrap();
    world.players[0].position = Vec3::new(0, 0, 0);
    world.players[1].position = Vec3::new(3000, 0, 0);
    world.players[1].health = 50;
    world
        .step(&[
            Input {
                buttons: FIRE,
                ..Input::default()
            },
            Input::default(),
        ])
        .unwrap();
    assert_eq!(world.players[1].health, 35);
    assert!(world.events.iter().any(|event| matches!(
        event,
        Event::Damage {
            attacker: 0,
            victim: 1,
            amount: 15
        }
    )));
}

#[test]
fn same_tick_healing_precedes_damage_and_replays_identically() {
    let mut a = team_world();
    a.players[1].health = 10;
    let mut b = a.clone();
    fire(&mut a, FIRE);
    fire(&mut b, FIRE);
    assert_eq!(a.players[1].health, 3);
    assert!(a.players[1].alive);
    assert_eq!(a.state_hash(), b.state_hash());
    assert!(a.events.iter().any(|event| matches!(
        event,
        Event::Damage {
            attacker: 2,
            victim: 1,
            amount: 22
        }
    )));
    assert!(
        !a.events
            .iter()
            .any(|event| matches!(event, Event::Death { victim: 1, .. }))
    );
}
