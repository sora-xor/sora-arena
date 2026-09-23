//! Plasma direct-hit guard behavior through the canonical charged firing path.
use arena_core::{
    math::Vec3,
    simulation::{BLOCK, Config, Event, FIRE, Input, Mode, Participant, Projectile, RELOAD, World},
};

fn duel(weapon: u8) -> World {
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
                class: 2,
                weapon,
                bond: 0,
                special_entitled: weapon >= 12,
            },
            Participant {
                team: 1,
                class: 0,
                weapon: 0,
                bond: 0,
                special_entitled: false,
            },
        ],
    )
    .unwrap();
    world.players[0].position = Vec3::new(0, 0, 0);
    world.players[1].position = Vec3::new(5000, 0, 0);
    world
}

fn step(world: &mut World, attacker_buttons: u32, victim_buttons: u32) {
    world
        .step(&[
            Input {
                buttons: attacker_buttons,
                ..Input::default()
            },
            Input {
                buttons: victim_buttons,
                yaw: 32768,
                ..Input::default()
            },
        ])
        .unwrap();
}

#[test]
fn ordinary_charged_coil_shot_is_still_parried() {
    let mut world = duel(5);
    for _ in 0..12 {
        step(&mut world, FIRE, 0);
    }
    assert_eq!(world.players[0].charge, 12);
    assert_eq!(world.players[0].ammo, 5);
    step(&mut world, FIRE, BLOCK);
    assert_eq!(world.players[0].ammo, 4);
    assert_eq!(world.players[1].health, 125);
    assert!(
        world
            .events
            .iter()
            .any(|event| matches!(event, Event::Shot { slot: 0, weapon: 5 }))
    );
    assert!(
        !world
            .events
            .iter()
            .any(|event| matches!(event, Event::Damage { .. }))
    );
}

#[test]
fn plasma_direct_hit_pierces_both_parry_and_sustained_guard_after_full_charge() {
    for sustained_guard in [false, true] {
        let mut world = duel(14);
        for _ in 0..24 {
            step(&mut world, FIRE, if sustained_guard { BLOCK } else { 0 });
            assert_eq!(world.players[0].ammo, 3);
            assert_eq!(world.players[1].health, 125);
            assert!(
                !world
                    .events
                    .iter()
                    .any(|event| matches!(event, Event::Shot { slot: 0, .. }))
            );
        }
        assert_eq!(world.players[0].charge, 24);
        step(&mut world, FIRE, BLOCK);
        assert_eq!(world.players[0].charge, 0);
        assert_eq!(world.players[0].ammo, 2);
        assert_eq!(world.players[0].attack_cooldown, 58);
        assert_eq!(world.players[1].health, 40);
        assert!(world.events.iter().any(|event| matches!(
            event,
            Event::Damage {
                attacker: 0,
                victim: 1,
                amount: 85
            }
        )));
        for _ in 0..5 {
            step(&mut world, FIRE, 0);
        }
        assert_eq!(world.players[0].ammo, 2);
        step(&mut world, RELOAD, 0);
        assert_eq!(world.players[0].reload_ticks, 168);
        for _ in 0..167 {
            step(&mut world, 0, 0);
        }
        assert_eq!(world.players[0].ammo, 2);
        assert_eq!(world.players[0].reload_ticks, 1);
        step(&mut world, 0, 0);
        assert_eq!(world.players[0].ammo, 3);
        assert_eq!(world.players[0].reload_ticks, 0);
    }
}

fn armed_grenade(owner: usize, position: Vec3) -> Projectile {
    Projectile {
        id: 7,
        owner,
        position,
        velocity: Vec3::new(350, 0, 0),
        weapon: 7,
        traveled: 2000,
        age: 1,
    }
}

#[test]
fn projectile_from_plasma_equipped_attacker_keeps_normal_parry_and_guard() {
    for (prior_guard_ticks, expected_health) in [(0, 125), (9, 92)] {
        let mut world = duel(14);
        for _ in 0..prior_guard_ticks {
            step(&mut world, 0, BLOCK);
        }
        world
            .projectiles
            .push(armed_grenade(0, Vec3::new(5000, 0, 1400)));
        step(&mut world, 0, BLOCK);
        assert_eq!(world.players[1].health, expected_health);
        assert_eq!(world.players[0].ammo, 3);
    }
}

#[test]
fn self_explosion_retains_existing_full_damage_even_while_guarding() {
    let mut world = World::new(
        Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 600,
            base_bond: 0,
            offline: true,
        },
        &[Participant {
            team: 0,
            class: 3,
            weapon: 7,
            bond: 0,
            special_entitled: false,
        }],
    )
    .unwrap();
    world.players[0].position = Vec3::default();
    let mut grenade = armed_grenade(0, Vec3::new(0, 0, 1400));
    // The owner is excluded from direct projectile collision, so let range
    // expiry detonate this already armed grenade beside its own shooter.
    grenade.traveled = 40000 - 350;
    world.projectiles.push(grenade);
    world
        .step(&[Input {
            buttons: BLOCK,
            ..Input::default()
        }])
        .unwrap();
    assert_eq!(world.players[0].health, 85);
    assert!(world.events.iter().any(|event| matches!(
        event,
        Event::Damage {
            attacker: 0,
            victim: 0,
            amount: 65
        }
    )));
}
