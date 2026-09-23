//! Physical impact location, rather than unused tick distance, governs arming.
use arena_core::{
    catalog::CLASSES,
    math::Vec3,
    simulation::{Config, FIRE, Input, Mode, Participant, World},
};

fn grenade_impact(victim_x: i32) -> World {
    let participants = (0..2)
        .map(|team| Participant {
            team,
            class: 3,
            weapon: 7,
            bond: 0,
            special_entitled: false,
        })
        .collect::<Vec<_>>();
    let mut world = World::new(
        Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 600,
            base_bond: 0,
            offline: true,
        },
        &participants,
    )
    .unwrap();
    world.players[0].position = Vec3::new(0, 0, 0);
    world.players[1].position = Vec3::new(victim_x, 0, 0);
    for tick in 0..7 {
        world
            .step(&[
                Input {
                    buttons: if tick == 0 { FIRE } else { 0 },
                    ..Input::default()
                },
                Input::default(),
            ])
            .unwrap();
    }
    assert!(
        world.projectiles.is_empty(),
        "projectile must have collided with the victim body"
    );
    world
}

#[test]
fn collision_before_arming_distance_cannot_borrow_unused_tick_travel() {
    // Six 350-mm steps would reach 2100 mm, but the body's near face is 1850 mm.
    // The 2000-mm fuse must not arm at this earlier impact.
    let world = grenade_impact(2200);
    assert_eq!(world.players[1].health, CLASSES[3].health);
    assert_eq!(world.players[0].health, CLASSES[3].health);
    assert!(world.damage_history.is_empty());
}

#[test]
fn collision_past_arming_distance_still_detonates() {
    // The body's near face is exactly the end of the 2100-mm sixth step.
    let world = grenade_impact(2450);
    assert_eq!(world.players[1].health, CLASSES[3].health - 65);
    assert_eq!(world.players[0].health, CLASSES[3].health - 65);
    assert_eq!(
        world.damage_history.len(),
        1,
        "self damage does not create an enemy assist"
    );
}

#[test]
fn range_expiry_does_not_add_an_extra_partial_tick_of_blast_reach() {
    let participants = (0..2)
        .map(|team| Participant {
            team,
            class: 4,
            weapon: 16,
            bond: 0,
            special_entitled: false,
        })
        .collect::<Vec<_>>();
    let mut world = World::new(
        Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 600,
            base_bond: 0,
            offline: true,
        },
        &participants,
    )
    .unwrap();
    world.players[0].position = Vec3::new(0, 0, 0);
    world.players[1].position = Vec3::new(0, -23150, 0);
    for tick in 0..37 {
        world
            .step(&[
                Input {
                    buttons: if tick == 0 { FIRE } else { 0 },
                    yaw: 49152,
                    ..Input::default()
                },
                Input::default(),
            ])
            .unwrap();
    }
    assert!(world.projectiles.is_empty());
    assert_eq!(
        world.players[1].health, CLASSES[4].health,
        "22,000-mm range must not become 22,200 mm by rounding up to a 600-mm tick"
    );
}
