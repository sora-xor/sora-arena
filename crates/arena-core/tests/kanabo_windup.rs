//! Kanabo hold-to-strike timing and charge ownership through canonical inputs.
use arena_core::{
    catalog::WEAPONS,
    math::Vec3,
    simulation::{
        BLOCK, Config, Event, FIRE, Input, MELEE, Mode, Participant, RESPAWN_TICKS, World,
    },
};

fn world(equipped: u8) -> World {
    let mut world = World::new(
        Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 1000,
            base_bond: 0,
            offline: true,
        },
        &[
            Participant {
                team: 0,
                class: 3,
                weapon: equipped,
                bond: 0,
                special_entitled: equipped >= 12,
            },
            Participant {
                team: 1,
                class: 0,
                weapon: 1,
                bond: 0,
                special_entitled: false,
            },
        ],
    )
    .unwrap();
    world.players[0].position = Vec3::new(0, 0, 0);
    world.players[1].position = Vec3::new(2000, 0, 0);
    world
}

fn step(world: &mut World, first: u32, second: u32) {
    world
        .step(&[
            Input {
                buttons: first,
                ..Input::default()
            },
            Input {
                buttons: second,
                yaw: 32768,
                ..Input::default()
            },
        ])
        .unwrap();
}

#[test]
fn kanabo_strikes_on_nineteenth_held_tick_after_eighteen_unpaid_windup_ticks() {
    assert_eq!(WEAPONS[6].charge_ticks, 18);
    let mut world = world(6);
    for tick in 1..=18 {
        step(&mut world, FIRE, 0);
        assert_eq!(world.players[0].charge, tick);
        assert_eq!(world.players[0].charge_weapon, 6);
        assert_eq!(world.players[0].stamina, 100);
        assert_eq!(world.players[0].attack_cooldown, 0);
        assert_eq!(world.players[1].health, 125);
        assert!(
            !world
                .events
                .iter()
                .any(|event| matches!(event, Event::Shot { slot: 0, .. }))
        );
    }
    step(&mut world, FIRE, 0);
    assert_eq!(world.players[0].charge, 0);
    assert_eq!(world.players[0].charge_weapon, u8::MAX);
    assert_eq!(world.players[0].stamina, 65);
    assert_eq!(world.players[0].attack_cooldown, 48);
    assert_eq!(world.players[1].health, 45);
    assert!(
        world
            .events
            .iter()
            .any(|event| matches!(event, Event::Shot { slot: 0, weapon: 6 }))
    );
    assert!(world.events.iter().any(|event| matches!(
        event,
        Event::Damage {
            attacker: 0,
            victim: 1,
            amount: 80
        }
    )));

    for _ in 0..47 {
        step(&mut world, FIRE, 0);
        assert_eq!(world.players[0].charge, 0);
        assert!(
            !world
                .events
                .iter()
                .any(|event| matches!(event, Event::Shot { slot: 0, .. }))
        );
    }
    step(&mut world, FIRE, 0);
    assert_eq!(world.players[0].charge, 1);
    assert!(
        !world
            .events
            .iter()
            .any(|event| matches!(event, Event::Shot { slot: 0, .. }))
    );
}

#[test]
fn release_and_block_each_restart_the_full_windup_without_upfront_stamina() {
    let mut world = world(6);
    for _ in 0..9 {
        step(&mut world, FIRE, 0);
    }
    assert_eq!(world.players[0].charge, 9);
    step(&mut world, 0, 0);
    assert_eq!(
        (world.players[0].charge, world.players[0].charge_weapon),
        (0, u8::MAX)
    );
    for _ in 0..9 {
        step(&mut world, MELEE, 0);
    }
    assert_eq!(world.players[0].charge, 9);
    step(&mut world, MELEE | BLOCK, 0);
    assert_eq!(
        (world.players[0].charge, world.players[0].charge_weapon),
        (0, u8::MAX)
    );
    assert_eq!(world.players[0].stamina, 99); // Guard's ordinary one-point drain only.
    for _ in 0..18 {
        step(&mut world, FIRE, 0);
        assert_eq!(world.players[0].stamina, 100);
        assert_eq!(world.players[1].health, 125);
    }
    step(&mut world, FIRE, 0);
    assert_eq!(world.players[1].health, 45);
    assert_eq!(world.players[0].stamina, 65);
}

#[test]
fn kanabo_melee_precharge_cannot_bypass_a_different_equipped_weapon_charge() {
    let mut world = world(15);
    for _ in 0..18 {
        step(&mut world, MELEE, 0);
    }
    assert_eq!(
        (world.players[0].charge, world.players[0].charge_weapon),
        (18, 6)
    );
    assert_eq!(world.players[0].ammo, 3);
    step(&mut world, FIRE, 0);
    assert_eq!(
        (world.players[0].charge, world.players[0].charge_weapon),
        (1, 15)
    );
    assert_eq!(world.players[0].ammo, 3);
    assert!(
        !world
            .events
            .iter()
            .any(|event| matches!(event, Event::Shot { slot: 0, .. }))
    );
    for _ in 0..14 {
        step(&mut world, FIRE, 0);
    }
    assert_eq!(world.players[0].charge, 15);
    assert_eq!(world.players[0].ammo, 3);
    step(&mut world, FIRE, 0);
    assert_eq!(world.players[0].charge, 0);
    assert_eq!(world.players[0].charge_weapon, u8::MAX);
    assert_eq!(world.players[0].ammo, 2);
    assert!(world.events.iter().any(|event| matches!(
        event,
        Event::Shot {
            slot: 0,
            weapon: 15
        }
    )));
}

#[test]
fn death_and_respawn_clear_the_windup_and_its_weapon_tag() {
    let mut world = world(6);
    for _ in 0..9 {
        step(&mut world, FIRE, 0);
    }
    assert_eq!(
        (world.players[0].charge, world.players[0].charge_weapon),
        (9, 6)
    );
    world.players[0].health = 1;
    step(&mut world, FIRE, FIRE);
    assert!(!world.players[0].alive);
    assert_eq!(
        (world.players[0].charge, world.players[0].charge_weapon),
        (0, u8::MAX)
    );
    assert_eq!(world.players[0].respawn_ticks, RESPAWN_TICKS);
    for _ in 0..RESPAWN_TICKS {
        step(&mut world, 0, 0);
    }
    assert!(world.players[0].alive);
    assert_eq!(
        (world.players[0].charge, world.players[0].charge_weapon),
        (0, u8::MAX)
    );
    assert_eq!(world.players[0].health, 150);
}
