//! Behavioral timing tests through the actual canonical input entry point.
use arena_core::{
    catalog::WEAPONS,
    math::Vec3,
    simulation::{BLOCK, Config, Event, FIRE, Input, MELEE, Mode, Participant, RELOAD, World},
};

fn practice(class: u8, weapon: u8) -> World {
    World::new(
        Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 3600,
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
fn step(world: &mut World, buttons: u32) -> usize {
    world
        .step(&[Input {
            buttons,
            ..Input::default()
        }])
        .unwrap();
    world
        .events
        .iter()
        .filter(|e| matches!(e, Event::Shot { .. }))
        .count()
}

#[test]
fn empty_magazine_cannot_fire_until_exact_reload_boundary() {
    let mut world = practice(0, 1);
    let mut shots = Vec::new();
    for tick in 0..=336 {
        if step(&mut world, FIRE) > 0 {
            shots.push(tick);
        }
        assert!(world.players[0].ammo <= 24);
        if tick == 230 {
            assert_eq!(world.players[0].ammo, 0);
        }
        if tick == 240 {
            assert_eq!(world.players[0].reload_ticks, 96);
        }
        if tick == 335 {
            assert_eq!(world.players[0].reload_ticks, 1);
        }
    }
    let expected: Vec<_> = (0..24).map(|n| n * 10).chain([336]).collect();
    assert_eq!(shots, expected);
    assert_eq!(world.players[0].ammo, 23);
}

#[test]
fn partial_reload_blocks_fire_and_finishes_only_after_committed_ticks() {
    let mut world = practice(0, 1);
    assert_eq!(step(&mut world, FIRE), 1);
    assert_eq!(step(&mut world, FIRE | RELOAD), 0);
    assert_eq!(world.players[0].reload_ticks, 96);
    for _ in 0..95 {
        assert_eq!(step(&mut world, FIRE), 0);
    }
    assert_eq!(world.players[0].ammo, 23);
    assert_eq!(step(&mut world, FIRE), 1);
    assert_eq!(world.players[0].reload_ticks, 0);
    assert_eq!(world.players[0].ammo, 23);
}

#[test]
fn block_or_melee_cancels_reload_without_refill_or_saved_progress() {
    for interrupt in [BLOCK, MELEE] {
        let mut world = practice(0, 1);
        step(&mut world, FIRE);
        step(&mut world, RELOAD);
        for _ in 0..95 {
            step(&mut world, 0);
        }
        assert_eq!(world.players[0].reload_ticks, 1);
        step(&mut world, interrupt);
        assert_eq!(world.players[0].reload_ticks, 0);
        assert_eq!(world.players[0].ammo, 23);
        step(&mut world, RELOAD);
        assert_eq!(world.players[0].reload_ticks, 96);
    }
}

#[test]
fn charge_does_not_survive_guarding_or_spend_ammo_before_a_shot() {
    let mut world = practice(2, 5);
    for _ in 0..6 {
        assert_eq!(step(&mut world, FIRE), 0);
    }
    assert_eq!(world.players[0].charge, 6);
    assert_eq!(world.players[0].ammo, 5);
    assert_eq!(step(&mut world, FIRE | BLOCK), 0);
    assert_eq!(world.players[0].charge, 0);
    for _ in 0..12 {
        assert_eq!(step(&mut world, FIRE), 0);
    }
    assert_eq!(world.players[0].ammo, 5);
    assert_eq!(step(&mut world, FIRE), 1);
    assert_eq!(world.players[0].ammo, 4);
    step(&mut world, RELOAD);
    assert_eq!(world.players[0].charge, 0);
    assert_eq!(world.players[0].reload_ticks, 138);
}

#[test]
fn melee_never_uses_magazines_and_weapon_state_changes_are_hashed() {
    let mut world = practice(0, 0);
    for _ in 0..120 {
        step(&mut world, FIRE | RELOAD);
    }
    assert_eq!(
        (world.players[0].ammo, world.players[0].reload_ticks),
        (0, 0)
    );
    let mut gun = practice(0, 1);
    let original = gun.state_hash();
    gun.players[0].ammo -= 1;
    assert_ne!(gun.state_hash(), original);
    let partial = gun.state_hash();
    gun.players[0].reload_ticks = 96;
    assert_ne!(gun.state_hash(), partial);
    for spec in WEAPONS {
        assert_eq!(spec.magazine == 0, spec.reload_ticks == 0);
    }
}

#[test]
fn lethal_damage_cancels_reload_and_respawn_restores_the_admitted_magazine() {
    let mut world = World::new(
        Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 3600,
            base_bond: 0,
            offline: true,
        },
        &[
            Participant {
                team: 0,
                class: 0,
                weapon: 1,
                bond: 0,
                special_entitled: false,
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
    world.players[1].position = Vec3::new(4000, 0, 0);
    let idle = Input::default();
    // A real shot uses ammunition; then the attacker kills a reloading victim.
    world
        .step(&[
            Input {
                buttons: FIRE,
                yaw: 32768,
                ..idle
            },
            idle,
        ])
        .unwrap();
    assert_eq!(world.players[0].ammo, 23);
    let attack = Input {
        buttons: FIRE,
        yaw: 32768,
        ..idle
    };
    world
        .step(&[
            Input {
                buttons: RELOAD,
                ..idle
            },
            attack,
        ])
        .unwrap();
    while world.players[0].alive {
        world.step(&[idle, attack]).unwrap();
    }
    assert_eq!(world.players[0].reload_ticks, 0);
    assert_eq!(world.players[0].ammo, 23);
    assert!(
        world
            .events
            .iter()
            .any(|e| matches!(e, Event::Death { victim: 0, .. }))
    );
    for _ in 0..arena_core::simulation::RESPAWN_TICKS {
        world.step(&[idle, idle]).unwrap();
    }
    assert!(world.players[0].alive);
    assert_eq!(
        (
            world.players[0].ammo,
            world.players[0].reload_ticks,
            world.players[0].charge
        ),
        (24, 0, 0)
    );
    assert!(
        world
            .events
            .iter()
            .any(|e| matches!(e, Event::Respawn { slot: 0 }))
    );
}
