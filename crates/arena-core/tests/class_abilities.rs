//! Rules 7 class abilities (docs/combat-rules.md §6) through real inputs:
//! one or more behavioural checks per class, plus parry stagger (§3.2).
use arena_core::{
    catalog::CLASSES,
    math::Vec3,
    simulation::{
        ABILITY, BLOCK, Config, Entity, EntityKind, Event, FIRE, Input, JUMP, MELEE, Mode,
        Participant, Projectile, RELOAD, RemovalCause, World,
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
            max_ticks: 3600,
            base_bond: 0,
            offline: true,
        },
        roster,
    )
    .unwrap()
}

fn place(w: &mut World, slot: usize, x: i32, y: i32) {
    w.players[slot].position = Vec3::new(x, y, 0);
}

fn press(buttons: u32, yaw: u16) -> Input {
    Input {
        buttons,
        yaw,
        ..Input::default()
    }
}

/// An armed grenade on its final range-limited step: it detonates at
/// `start + velocity` unless a body or solid lies on that step.
fn expiring_grenade(owner: usize, start: Vec3, velocity: Vec3) -> Projectile {
    Projectile {
        id: 9,
        owner,
        position: start,
        velocity,
        weapon: 7,
        traveled: 40_000 - 350,
        age: 1,
    }
}

fn count(w: &World, predicate: impl Fn(&Event) -> bool) -> usize {
    w.events.iter().filter(|event| predicate(event)).count()
}

// ---------------------------------------------------------------- Samurai

#[test]
fn samurai_stance_negates_every_frontal_ray_of_the_batch_and_ripostes_once() {
    let mut w = world(
        Mode::FreeForAll,
        &[
            participant(0, 0, 0),
            participant(0, 0, 1),
            participant(0, 0, 1),
        ],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, 2500, 0);
    place(&mut w, 2, 2000, 2000);
    let attack = [press(0, 0), press(FIRE, 32768), press(FIRE, 40960)];
    w.step(&[press(ABILITY, 0), attack[1], attack[2]]).unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::AbilityUsed { slot: 0, class: 0 },
            Event::Shot { slot: 1, weapon: 1 },
            Event::Shot { slot: 2, weapon: 1 },
            Event::Guarded {
                attacker: 1,
                victim: 0,
                weapon: 1,
                parried: true,
                prevented: 22
            },
            Event::Riposte { slot: 0, target: 1 },
            Event::Guarded {
                attacker: 2,
                victim: 0,
                weapon: 1,
                parried: true,
                prevented: 22
            },
            Event::Damage {
                attacker: 0,
                victim: 1,
                amount: 90
            },
        ]
    );
    assert_eq!(w.players[0].health, CLASSES[0].health);
    assert_eq!(w.players[1].health, CLASSES[0].health - 90);
    assert_eq!(w.players[0].ability_cooldown, 480);
    // The negating batch ended the stance: the next volley lands in full and
    // no second riposte or whiff recovery follows.
    assert_eq!(w.players[0].stance_ticks, 0);
    let mut landed = 0;
    for _ in 0..12 {
        w.step(&attack).unwrap();
        assert_eq!(
            count(&w, |e| matches!(
                e,
                Event::Riposte { .. } | Event::Guarded { .. }
            )),
            0
        );
        landed += count(&w, |e| matches!(e, Event::Damage { victim: 0, .. }));
    }
    assert_eq!(landed, 2);
    assert_eq!(w.players[0].health, CLASSES[0].health - 44);
    assert_eq!(w.players[0].attack_cooldown, 0);
}

#[test]
fn samurai_stance_lets_hits_from_behind_land_in_full() {
    // The Samurai faces +X. A carbine fires into its back from 5000 mm and a
    // katana strikes from behind its left shoulder. Neither origin is
    // frontal, so both land in full, nothing is guarded or riposted, and the
    // stance stays up.
    let mut w = world(
        Mode::FreeForAll,
        &[
            participant(0, 0, 0),
            participant(0, 0, 1),
            participant(0, 0, 0),
        ],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, -5000, 0);
    place(&mut w, 2, -1500, 1500);
    w.step(&[press(ABILITY, 0), press(FIRE, 0), press(MELEE, 57344)])
        .unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::AbilityUsed { slot: 0, class: 0 },
            Event::Shot { slot: 1, weapon: 1 },
            Event::Shot { slot: 2, weapon: 0 },
            Event::Damage {
                attacker: 1,
                victim: 0,
                amount: 22
            },
            Event::Damage {
                attacker: 2,
                victim: 0,
                amount: 60
            },
        ]
    );
    assert_eq!(w.players[0].health, CLASSES[0].health - 22 - 60);
    assert_eq!(w.players[0].stance_ticks, 24);
    // The rear hits left the stance up: moved in front, the same carbine is
    // negated. At 5000 mm the shooter is out of riposte range.
    place(&mut w, 1, 5000, 0);
    let mut events = Vec::new();
    for _ in 0..12 {
        w.step(&[press(0, 0), press(FIRE, 32768), press(0, 57344)])
            .unwrap();
        events.extend(w.events.iter().cloned());
    }
    assert_eq!(
        events,
        vec![
            Event::Shot { slot: 1, weapon: 1 },
            Event::Guarded {
                attacker: 1,
                victim: 0,
                weapon: 1,
                parried: true,
                prevented: 22
            },
        ]
    );
    assert_eq!(w.players[0].health, CLASSES[0].health - 22 - 60);
    assert_eq!(w.players[0].stance_ticks, 0);
}

#[test]
fn only_the_first_negated_hit_may_riposte_and_it_needs_range_and_a_clear_line() {
    // Slot 1 fires from 5000 mm, beyond the 3000 mm riposte range, and is
    // gathered first. The katana strike from 2000 mm is negated too, but it
    // is not the stance's first negated hit, so nothing ripostes.
    let mut w = world(
        Mode::FreeForAll,
        &[
            participant(0, 0, 0),
            participant(0, 0, 1),
            participant(0, 0, 0),
        ],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, 5000, 0);
    place(&mut w, 2, 0, 2000);
    w.players[0].yaw = 8192;
    w.step(&[
        press(ABILITY, 8192),
        press(FIRE, 32768),
        press(MELEE, 49152),
    ])
    .unwrap();
    assert_eq!(
        count(&w, |e| matches!(
            e,
            Event::Guarded {
                victim: 0,
                parried: true,
                ..
            }
        )),
        2
    );
    assert_eq!(count(&w, |e| matches!(e, Event::Riposte { .. })), 0);
    assert_eq!(count(&w, |e| matches!(e, Event::Damage { .. })), 0);
    assert_eq!(w.players[0].stance_ticks, 0);

    // The Samurai stands north of Nyaagyu Estate's north veranda screen east
    // (x 3000..5000, y 7000..7600, 2000 mm high), facing it. The attacker,
    // 2950 mm south and so within riposte range, fires down over the screen
    // at the apex of a jump. The shot is negated, but the eye-to-eye line
    // crosses the screen, so the stance does not riposte.
    let mut w = world(
        Mode::FreeForAll,
        &[participant(0, 0, 0), participant(1, 0, 1)],
    );
    place(&mut w, 0, 4000, 8050);
    place(&mut w, 1, 4000, 5100);
    w.step(&[press(0, 49152), press(JUMP, 16384)]).unwrap();
    for _ in 1..21 {
        w.step(&[press(0, 49152), press(0, 16384)]).unwrap();
    }
    // 4 mm short of the 1936 mm apex, which the 22nd tick of a jump reaches.
    assert_eq!(w.players[1].position.z, 1932);
    w.step(&[
        press(ABILITY, 49152),
        Input {
            buttons: FIRE,
            yaw: 16384,
            pitch: -5000,
            ..Input::default()
        },
    ])
    .unwrap();
    assert_eq!(w.players[1].position.z, 1936);
    assert_eq!(
        w.events,
        vec![
            Event::AbilityUsed { slot: 0, class: 0 },
            Event::Shot { slot: 1, weapon: 1 },
            Event::Guarded {
                attacker: 1,
                victim: 0,
                weapon: 1,
                parried: true,
                prevented: 22
            },
        ]
    );
    assert_eq!(w.players[1].health, CLASSES[0].health);
    assert_eq!(w.players[0].stance_ticks, 0);
}

#[test]
fn samurai_stance_ignores_blasts_freezes_actions_and_whiffs_into_recovery() {
    let mut w = world(
        Mode::FreeForAll,
        &[participant(0, 3, 7), participant(1, 0, 1)],
    );
    place(&mut w, 0, 5000, 0);
    place(&mut w, 1, 1000, 0);
    // A frontal blast in the activation tick is not a ray: it hits in full.
    w.projectiles.push(expiring_grenade(
        0,
        Vec3::new(-1000, 0, 1400),
        Vec3::new(-350, 0, 0),
    ));
    w.step(&[press(0, 0), press(ABILITY, 32768)]).unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::AbilityUsed { slot: 1, class: 0 },
            Event::Damage {
                attacker: 0,
                victim: 1,
                amount: 65
            }
        ]
    );
    assert_eq!(w.players[1].stance_ticks, 24);
    // In stance: no horizontal movement, jump, guard, attack or reload.
    let busy = Input {
        buttons: FIRE | JUMP | BLOCK | RELOAD,
        move_x: 127,
        move_y: 40,
        yaw: 32768,
        pitch: 0,
    };
    for remaining in (1..24).rev() {
        w.step(&[press(0, 0), busy]).unwrap();
        assert_eq!(w.players[1].stance_ticks, remaining);
        assert_eq!(w.players[1].position, Vec3::new(1000, 0, 0));
        assert!(!w.players[1].guarding);
        assert_eq!(w.players[1].reload_ticks, 0);
        assert!(w.events.is_empty(), "{:?}", w.events);
    }
    // The stance expires without negating anything: a 30-tick recovery.
    let advance = Input {
        buttons: FIRE,
        move_x: 127,
        yaw: 32768,
        ..Input::default()
    };
    w.step(&[press(0, 0), advance]).unwrap();
    assert_eq!(w.players[1].stance_ticks, 0);
    assert_eq!(w.players[1].attack_cooldown, 30);
    assert_eq!(w.players[1].position, Vec3::new(920, 0, 0));
    let mut first_shot = None;
    while first_shot.is_none() {
        let tick = w.tick;
        w.step(&[press(0, 0), advance]).unwrap();
        if count(&w, |e| matches!(e, Event::Shot { slot: 1, .. })) > 0 {
            first_shot = Some(tick);
        }
    }
    assert_eq!(first_shot, Some(54));
}

#[test]
fn melee_parry_staggers_the_striker_and_refunds_a_samurai_cooldown() {
    let mut w = world(
        Mode::FreeForAll,
        &[participant(0, 0, 0), participant(1, 0, 1)],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, 2000, 0);
    w.players[1].ability_cooldown = 400;
    w.step(&[press(MELEE, 0), press(BLOCK, 32768)]).unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::Shot { slot: 0, weapon: 0 },
            Event::Guarded {
                attacker: 0,
                victim: 1,
                weapon: 0,
                parried: true,
                prevented: 60
            }
        ]
    );
    assert_eq!(w.players[0].attack_cooldown, 36 + 30);
    assert_eq!(w.players[1].ability_cooldown, 400 - 1 - 120);

    // A parried ranged shot refunds the Samurai but does not stagger.
    let mut w = world(
        Mode::FreeForAll,
        &[participant(0, 0, 1), participant(1, 0, 1)],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, 5000, 0);
    w.players[1].ability_cooldown = 100;
    w.step(&[press(FIRE, 0), press(BLOCK, 32768)]).unwrap();
    assert!(w.events.contains(&Event::Guarded {
        attacker: 0,
        victim: 1,
        weapon: 1,
        parried: true,
        prevented: 22
    }));
    assert_eq!(w.players[0].attack_cooldown, 12);
    assert_eq!(w.players[1].ability_cooldown, 0);
}

// ---------------------------------------------------------------- Shinobi

#[test]
fn shinobi_decoy_stays_behind_the_dash_and_soaks_enemy_rays_until_destroyed() {
    let mut w = world(
        Mode::FreeForAll,
        &[participant(0, 1, 3), participant(1, 0, 1)],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, -3000, 0);
    w.step(&[press(ABILITY, 0), press(FIRE, 0)]).unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::AbilityUsed { slot: 0, class: 1 },
            Event::EntitySpawned {
                id: 1,
                kind: EntityKind::Decoy,
                owner: 0
            },
            Event::Shot { slot: 1, weapon: 1 },
            Event::EntityDamaged {
                id: 1,
                attacker: 1,
                amount: 22
            },
        ]
    );
    assert_eq!(w.players[0].position, Vec3::new(2000, 0, 0));
    assert_eq!(w.players[0].ability_cooldown, 600);
    assert_eq!(
        w.entities,
        vec![Entity {
            id: 1,
            kind: EntityKind::Decoy,
            owner: 0,
            team: 0,
            position: Vec3::new(0, 0, 0),
            yaw: 0,
            health: 38,
            age: 1,
            half_x: 350,
            half_y: 350,
        }]
    );
    // Two more carbine hits empty it; the next shot reaches the Shinobi.
    for _ in 0..24 {
        w.step(&[press(0, 0), press(FIRE, 0)]).unwrap();
    }
    assert_eq!(
        w.events,
        vec![
            Event::Shot { slot: 1, weapon: 1 },
            Event::EntityDamaged {
                id: 1,
                attacker: 1,
                amount: 16
            },
            Event::EntityDestroyed {
                id: 1,
                kind: EntityKind::Decoy,
                owner: 0,
                cause: RemovalCause::Destroyed { by: 1 }
            },
        ]
    );
    assert!(w.entities.is_empty());
    assert_eq!(w.players[0].health, CLASSES[1].health);
    for _ in 0..12 {
        w.step(&[press(0, 0), press(FIRE, 0)]).unwrap();
    }
    assert!(w.events.contains(&Event::Damage {
        attacker: 1,
        victim: 0,
        amount: 22
    }));
}

#[test]
fn allied_rays_pass_through_a_decoy() {
    let mut w = world(
        Mode::Control,
        &[
            participant(0, 1, 3),
            participant(0, 0, 1),
            participant(1, 0, 1),
        ],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, -3000, 0);
    place(&mut w, 2, 4000, 0);
    // The Shinobi dashes across the lane, leaving the decoy in the line.
    w.step(&[press(ABILITY, 16384), press(FIRE, 0), press(0, 0)])
        .unwrap();
    assert_eq!(w.players[0].position, Vec3::new(0, 2000, 0));
    assert!(w.events.contains(&Event::Damage {
        attacker: 1,
        victim: 2,
        amount: 22
    }));
    assert_eq!(w.entities[0].health, 60);
}

#[test]
fn decoys_stop_enemy_projectiles_take_blasts_and_die_with_their_owner() {
    let mut w = world(
        Mode::FreeForAll,
        &[participant(0, 1, 3), participant(1, 4, 16)],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, -3000, 0);
    // A shock round flies 600 mm per tick at the decoy and bursts on its face
    // at x = -350. The Shinobi dashed 2000 mm sideways, out of the 1100 mm
    // blast.
    w.step(&[press(ABILITY, 16384), press(FIRE, 0)]).unwrap();
    let mut decoy_hit = Vec::new();
    for _ in 0..6 {
        w.step(&[press(0, 16384), press(0, 0)]).unwrap();
        decoy_hit.extend(
            w.events
                .iter()
                .filter(|e| matches!(e, Event::EntityDamaged { .. }))
                .cloned(),
        );
    }
    assert!(w.projectiles.is_empty());
    assert_eq!(
        decoy_hit,
        vec![Event::EntityDamaged {
            id: 1,
            attacker: 1,
            amount: 28
        }]
    );
    assert_eq!(w.entities[0].health, 32);
    assert_eq!(w.players[0].health, CLASSES[1].health);

    // An armed grenade bursting beside the decoy empties it. Its thrower
    // and the Shinobi stand outside the 2500 mm blast.
    place(&mut w, 1, -6000, 3000);
    w.projectiles.push(expiring_grenade(
        1,
        Vec3::new(-1500, -1500, 1400),
        Vec3::new(350, 0, 0),
    ));
    w.step(&[press(0, 16384), press(0, 0)]).unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::EntityDamaged {
                id: 1,
                attacker: 1,
                amount: 32
            },
            Event::EntityDestroyed {
                id: 1,
                kind: EntityKind::Decoy,
                owner: 0,
                cause: RemovalCause::Destroyed { by: 1 }
            }
        ]
    );

    // A fresh decoy is removed right after its owner's death.
    w.players[0].ability_cooldown = 0;
    w.step(&[press(ABILITY, 16384), press(0, 0)]).unwrap();
    assert_eq!(w.entities.len(), 1);
    assert_eq!(w.entities[0].id, 2);
    assert_eq!(w.players[0].position, Vec3::new(0, 4000, 0));
    w.players[0].health = 1;
    place(&mut w, 1, -3000, 4000);
    w.players[1].weapon = 9;
    w.players[1].ammo = 36;
    w.players[1].attack_cooldown = 0;
    w.step(&[press(0, 16384), press(FIRE, 0)]).unwrap();
    let death = w
        .events
        .iter()
        .position(|e| matches!(e, Event::Death { victim: 0, .. }))
        .unwrap();
    assert_eq!(
        w.events[death + 1],
        Event::EntityDestroyed {
            id: 2,
            kind: EntityKind::Decoy,
            owner: 0,
            cause: RemovalCause::OwnerDied
        }
    );
    assert!(w.entities.is_empty());
}

// ---------------------------------------------------------------- Teppō

#[test]
fn teppo_mark_amplifies_enemy_damage_for_300_ticks() {
    let mut w = world(
        Mode::FreeForAll,
        &[
            participant(0, 2, 5),
            participant(0, 0, 0),
            participant(0, 0, 1),
        ],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, 5000, 0);
    place(&mut w, 2, 5000, -3000);
    let shoot = [press(0, 0), press(0, 0), press(FIRE, 16384)];
    w.step(&[press(ABILITY, 0), press(0, 0), press(FIRE, 16384)])
        .unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::AbilityUsed { slot: 0, class: 2 },
            Event::Marked {
                marker: 0,
                target: 1
            },
            Event::Shot { slot: 2, weapon: 1 },
            Event::Damage {
                attacker: 2,
                victim: 1,
                amount: 27
            },
        ]
    );
    assert_eq!(w.players[1].marked_ticks, 300);
    assert_eq!(w.players[0].ability_cooldown, 720);
    // Still marked in the batch of tick 299, gone from tick 300.
    let mut hits = Vec::new();
    while w.tick < 312 + 1 {
        let tick = w.tick;
        w.step(&shoot).unwrap();
        for event in &w.events {
            if let Event::Damage { amount, .. } = event {
                hits.push((tick, *amount));
            }
        }
        w.players[1].health = CLASSES[0].health;
        w.players[2].ammo = 24;
    }
    assert_eq!(hits.len(), 26);
    assert!(
        hits.iter()
            .all(|&(tick, amount)| amount == if tick < 300 { 27 } else { 22 })
    );
    assert_eq!(hits[23], (288, 27));
    assert_eq!(hits[24], (300, 22));
    assert_eq!(w.players[1].marked_ticks, 0);
}

#[test]
fn teppo_mark_on_a_wall_is_spent_without_a_mark() {
    let mut w = world(
        Mode::FreeForAll,
        &[participant(0, 2, 5), participant(0, 0, 1)],
    );
    // The enemy stands behind Nyaagyu Estate's east kura (x = 9500..12500).
    place(&mut w, 0, 5000, 4750);
    place(&mut w, 1, 13_500, 4750);
    w.players[0].spawn_protection = 50;
    w.step(&[press(ABILITY, 0), press(0, 0)]).unwrap();
    assert_eq!(w.events, vec![Event::AbilityUsed { slot: 0, class: 2 }]);
    assert_eq!(w.players[0].ability_cooldown, 720);
    assert_eq!(w.players[0].spawn_protection, 0);
    assert_eq!(w.players[1].marked_ticks, 0);
}

#[test]
fn teppo_mark_passes_allies_and_spawn_protected_enemies() {
    // Up the +Y line from the Teppō: a spawn-protected enemy, an ally, then
    // the enemy the mark lands on. Neither of the first two stops the ray.
    let mut w = world(
        Mode::Control,
        &[
            participant(0, 2, 5),
            participant(1, 0, 1),
            participant(0, 0, 1),
            participant(1, 0, 1),
        ],
    );
    place(&mut w, 0, 0, -6000);
    place(&mut w, 1, 0, 0);
    place(&mut w, 2, 0, -3000);
    place(&mut w, 3, 0, -4500);
    w.players[3].spawn_protection = 50;
    w.step(&[press(ABILITY, 16384), press(0, 0), press(0, 0), press(0, 0)])
        .unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::AbilityUsed { slot: 0, class: 2 },
            Event::Marked {
                marker: 0,
                target: 1
            },
        ]
    );
    assert_eq!(
        w.players.iter().map(|p| p.marked_ticks).collect::<Vec<_>>(),
        [0, 300, 0, 0]
    );
}

// ---------------------------------------------------------------- Hanabi

#[test]
fn hanabi_fire_zone_lands_where_the_pot_meets_a_wall_or_the_floor() {
    for (x, y, yaw, pitch, centre) in [
        // Level throw at the east kura face x = 9500, 6500 mm away: pulled
        // back about 400 mm.
        (3000, 4750, 0, 0, Vec3::new(9099, 4750, 0)),
        // 45 degrees down: the floor comes first.
        (0, 0, 0, -8192, Vec3::new(1399, 0, 0)),
    ] {
        let mut w = world(Mode::FreeForAll, &[participant(0, 3, 7)]);
        place(&mut w, 0, x, y);
        w.step(&[Input {
            buttons: ABILITY,
            yaw,
            pitch,
            ..Input::default()
        }])
        .unwrap();
        assert_eq!(
            w.events,
            vec![
                Event::AbilityUsed { slot: 0, class: 3 },
                Event::EntitySpawned {
                    id: 1,
                    kind: EntityKind::FireZone,
                    owner: 0
                }
            ]
        );
        assert_eq!(w.entities[0].position, centre);
        assert_eq!((w.entities[0].half_x, w.entities[0].health), (2500, 0));
        assert_eq!(w.players[0].ability_cooldown, 720);
    }
}

#[test]
fn hanabi_fire_zone_pulses_fourteen_times_on_enemies_only_then_expires() {
    let mut w = world(
        Mode::Control,
        &[
            participant(0, 3, 7),
            participant(0, 0, 1),
            participant(1, 0, 1),
            participant(1, 0, 1),
        ],
    );
    place(&mut w, 0, 0, 0);
    // The pot lands at (1399, 0): the owner and an ally stand inside, one
    // enemy exactly on the 2500 mm edge, another 1 mm beyond it.
    place(&mut w, 1, 1399, 1000);
    place(&mut w, 2, 1399, -2500);
    place(&mut w, 3, 1399 + 2501, 0);
    let idle = [Input::default(); 4];
    w.step(&[
        Input {
            buttons: ABILITY,
            pitch: -8192,
            ..Input::default()
        },
        idle[1],
        idle[2],
        idle[3],
    ])
    .unwrap();
    assert_eq!(w.entities[0].position, Vec3::new(1399, 0, 0));
    let mut pulses = Vec::new();
    let mut destroyed = Vec::new();
    for _ in 1..400 {
        let tick = w.tick;
        w.step(&idle).unwrap();
        for event in &w.events {
            match event {
                Event::Damage {
                    attacker,
                    victim,
                    amount,
                } => pulses.push((tick, *attacker, *victim, *amount)),
                Event::EntityDestroyed { .. } => destroyed.push((tick, event.clone())),
                _ => {}
            }
        }
    }
    let expected = (0..14).map(|k| (29 + 20 * k, 0, 2, 8)).collect::<Vec<_>>();
    assert_eq!(pulses, expected);
    assert_eq!(w.players[2].health, CLASSES[0].health - 14 * 8);
    for slot in [0, 1, 3] {
        assert_eq!(
            w.players[slot].health,
            CLASSES[w.players[slot].class as usize].health
        );
    }
    assert_eq!(
        destroyed,
        vec![(
            299,
            Event::EntityDestroyed {
                id: 1,
                kind: EntityKind::FireZone,
                owner: 0,
                cause: RemovalCause::Expired
            }
        )]
    );
    assert!(w.entities.is_empty());
}

#[test]
fn hanabi_fire_zone_spares_enemies_behind_a_wall_or_high_in_a_jump() {
    let mut w = world(
        Mode::FreeForAll,
        &[
            participant(0, 3, 7),
            participant(1, 0, 1),
            participant(1, 0, 1),
        ],
    );
    // A level throw meets Nyaagyu Estate's north veranda screen east
    // (x 3000..5000, y 7000..7600, 2000 mm high) and lands just south of it.
    // Slot 1 stands inside the radius but north of the screen; slot 2 stands
    // in the open and jumps on tick 12.
    place(&mut w, 0, 4000, 3500);
    place(&mut w, 1, 4000, 8050);
    place(&mut w, 2, 2500, 5000);
    w.step(&[press(ABILITY, 16384), press(0, 0), press(0, 0)])
        .unwrap();
    let centre = w.entities[0].position;
    assert_eq!(centre, Vec3::new(4000, 6599, 0));
    for slot in [1, 2] {
        assert!(w.players[slot].position.horizontal_distance_squared(centre) <= 2500 * 2500);
    }
    let mut pulses = Vec::new();
    while !w.entities.is_empty() {
        let tick = w.tick;
        let jump = if tick == 12 { JUMP } else { 0 };
        w.step(&[press(0, 0), press(0, 0), press(jump, 0)]).unwrap();
        let z = w.players[2].position.z;
        match tick {
            // Airborne above 1000 mm at the first pulse, airborne but low at
            // the second.
            29 => assert_eq!(z, 1872),
            49 => assert_eq!(z, 912),
            _ => {}
        }
        for event in &w.events {
            if let Event::Damage { victim, .. } = event {
                pulses.push((tick, *victim));
            }
        }
    }
    let expected = (1..14).map(|k| (29 + 20 * k, 2)).collect::<Vec<_>>();
    assert_eq!(pulses, expected);
    assert_eq!(w.players[1].health, CLASSES[0].health);
    assert_eq!(w.players[2].health, CLASSES[0].health - 13 * 8);
}

// ---------------------------------------------------------------- Karakuri

/// A Karakuri at the origin facing +X deploys its barricade at (1500, 0):
/// x 1300..1700, y -1200..1200, z 0..2000.
fn barricade_world(enemy_class: u8, enemy_weapon: u8, enemy_x: i32) -> World {
    let mut w = world(
        Mode::FreeForAll,
        &[
            participant(0, 4, 9),
            participant(1, enemy_class, enemy_weapon),
        ],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, enemy_x, 0);
    w.step(&[press(ABILITY, 0), press(0, 32768)]).unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::AbilityUsed { slot: 0, class: 4 },
            Event::EntitySpawned {
                id: 1,
                kind: EntityKind::Barricade,
                owner: 0
            }
        ]
    );
    assert_eq!(
        w.entities,
        vec![Entity {
            id: 1,
            kind: EntityKind::Barricade,
            owner: 0,
            team: 0,
            position: Vec3::new(1500, 0, 0),
            yaw: 0,
            health: 250,
            age: 1,
            half_x: 200,
            half_y: 1200,
        }]
    );
    w
}

#[test]
fn karakuri_barricade_blocks_enemy_movement_and_rays() {
    let mut w = barricade_world(0, 1, 4000);
    let charge = Input {
        buttons: FIRE,
        move_x: 127,
        yaw: 32768,
        ..Input::default()
    };
    let mut soaked = 0;
    for _ in 0..60 {
        w.step(&[press(0, 0), charge]).unwrap();
        for event in &w.events {
            if let Event::EntityDamaged { amount, .. } = event {
                soaked += amount;
            }
        }
        assert_eq!(count(&w, |e| matches!(e, Event::Damage { .. })), 0);
    }
    // The walker stops where its 350 mm body meets the x = 1700 face.
    assert_eq!(w.players[1].position, Vec3::new(2080, 0, 0));
    assert_eq!(soaked, 5 * 22);
    assert_eq!(w.entities[0].health, 250 - 5 * 22);
    assert_eq!(w.players[0].health, CLASSES[4].health);
}

#[test]
fn a_jump_never_clears_a_barricade() {
    let mut w = barricade_world(1, 3, 3000);
    let leap = Input {
        buttons: JUMP,
        move_x: 127,
        yaw: 32768,
        ..Input::default()
    };
    let mut apex = 0;
    for _ in 0..240 {
        w.step(&[press(0, 0), leap]).unwrap();
        apex = apex.max(w.players[1].position.z);
        assert!(w.players[1].position.x > 1700 + 350);
    }
    assert_eq!(apex, 1936);
}

#[test]
fn karakuri_barricade_stops_projectiles_and_shields_blasts() {
    let mut w = barricade_world(3, 7, 5000);
    w.step(&[press(0, 0), press(FIRE, 32768)]).unwrap();
    let mut events = Vec::new();
    for _ in 0..12 {
        w.step(&[press(0, 0), press(0, 32768)]).unwrap();
        events.extend(w.events.iter().cloned());
    }
    assert!(w.projectiles.is_empty());
    // The grenade bursts on the barricade face: the barricade takes the
    // blast, the Karakuri behind it takes nothing.
    assert_eq!(
        events,
        vec![Event::EntityDamaged {
            id: 1,
            attacker: 1,
            amount: 65
        }]
    );
    assert_eq!(w.players[0].health, CLASSES[4].health);

    // The owner's own projectiles stop on it without damaging it.
    let mut w = world(Mode::FreeForAll, &[participant(0, 4, 16)]);
    place(&mut w, 0, 0, 0);
    w.step(&[press(ABILITY, 0)]).unwrap();
    for tick in 0..6 {
        w.step(&[press(if tick == 0 { FIRE } else { 0 }, 0)])
            .unwrap();
        assert_eq!(count(&w, |e| matches!(e, Event::EntityDamaged { .. })), 0);
    }
    assert!(w.projectiles.is_empty());
    assert_eq!(w.entities[0].health, 250);
}

#[test]
fn forge_hammer_repairs_an_own_barricade_up_to_full_health() {
    let mut w = barricade_world(0, 1, 4000);
    w.entities[0].health = 170;
    let mut repaired = Vec::new();
    for _ in 0..90 {
        w.step(&[press(MELEE, 0), press(0, 32768)]).unwrap();
        for event in &w.events {
            if let Event::EntityRepaired {
                id,
                repairer,
                amount,
            } = event
            {
                repaired.push((*id, *repairer, *amount));
            }
        }
    }
    // Strikes land every 30 ticks: +45, +35, then nothing left to repair.
    assert_eq!(repaired, vec![(1, 0, 45), (1, 0, 35)]);
    assert_eq!(w.entities[0].health, 250);
    assert_eq!(
        count(&w, |e| matches!(e, Event::EntityDamaged { .. })),
        0,
        "a friendly hammer never damages"
    );
}

#[test]
fn an_enemy_forge_hammer_damages_a_barricade_instead_of_repairing_it() {
    let mut w = barricade_world(4, 9, 3500);
    w.entities[0].health = 200;
    w.step(&[press(0, 0), press(MELEE, 32768)]).unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::Shot { slot: 1, weapon: 8 },
            Event::EntityDamaged {
                id: 1,
                attacker: 1,
                amount: 45
            }
        ]
    );
    assert_eq!(w.entities[0].health, 155);
}

#[test]
fn allied_rays_stop_on_a_barricade_harmlessly() {
    let mut w = world(
        Mode::Control,
        &[
            participant(0, 4, 9),
            participant(0, 0, 1),
            participant(1, 0, 1),
        ],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, 0, 3000);
    place(&mut w, 2, 4000, 500);
    w.step(&[press(ABILITY, 0), press(0, 0), press(0, 0)])
        .unwrap();
    // The ally fires along y = 500, past the Karakuri, at the enemy behind
    // the barricade.
    place(&mut w, 1, -2000, 500);
    w.players[1].yaw = 0;
    w.step(&[press(0, 0), press(FIRE, 0), press(0, 0)]).unwrap();
    assert_eq!(count(&w, |e| matches!(e, Event::Shot { slot: 1, .. })), 1);
    assert_eq!(
        count(&w, |e| matches!(
            e,
            Event::Damage { .. } | Event::EntityDamaged { .. } | Event::EntityRepaired { .. }
        )),
        0
    );
    assert_eq!(w.players[2].health, CLASSES[0].health);
    assert_eq!(w.entities[0].health, 250);
}

#[test]
fn karakuri_barricade_placement_rejects_walls_and_bodies_without_spending() {
    // Into Nyaagyu Estate's east kura at x = 9500..12500.
    let mut w = world(
        Mode::FreeForAll,
        &[participant(0, 4, 9), participant(1, 0, 1)],
    );
    place(&mut w, 0, 8000, 4750);
    place(&mut w, 1, 0, -5000);
    w.players[0].spawn_protection = 50;
    w.step(&[press(ABILITY, 0), press(0, 0)]).unwrap();
    assert!(w.events.is_empty());
    assert!(w.entities.is_empty());
    assert_eq!(w.players[0].ability_cooldown, 0);
    assert_eq!(w.players[0].spawn_protection, 49);
    assert_eq!(w.next_entity_id, 1);
    // Onto a standing player.
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, 1500, 900);
    w.step(&[press(ABILITY, 0), press(0, 0)]).unwrap();
    assert!(w.events.is_empty());
    assert!(w.entities.is_empty());
    // Once the body moves clear, the same placement succeeds.
    place(&mut w, 1, 1500, 1600);
    w.step(&[press(ABILITY, 0), press(0, 0)]).unwrap();
    assert_eq!(w.entities.len(), 1);
    // Near a spawn: Nyaagyu Estate's team 0 spawn at (-19500, -3000).
    let mut w = world(Mode::Control, &[participant(0, 4, 9), participant(1, 0, 1)]);
    place(&mut w, 0, -19500, -1800);
    w.step(&[press(ABILITY, 49152), press(0, 0)]).unwrap();
    assert!(w.entities.is_empty());
    // Through a wall: the box at (4000, 8100) fits between Nyaagyu Estate's
    // north veranda screen east (x 3000..5000, y 7000..7600) and the dojo
    // hall, but the Karakuri stands south of the screen.
    let mut w = world(
        Mode::FreeForAll,
        &[participant(0, 4, 9), participant(1, 0, 1)],
    );
    place(&mut w, 0, 4000, 6600);
    place(&mut w, 1, 0, -5000);
    w.step(&[press(ABILITY, 16384), press(0, 0)]).unwrap();
    assert!(w.events.is_empty());
    assert!(w.entities.is_empty());
    assert_eq!(w.players[0].ability_cooldown, 0);
    // Past the screen's east end the path is clear and the box fits.
    place(&mut w, 0, 5400, 6600);
    w.step(&[press(ABILITY, 16384), press(0, 0)]).unwrap();
    assert_eq!(w.entities.len(), 1);
    assert_eq!(w.entities[0].position, Vec3::new(5400, 8100, 0));
    assert_eq!((w.entities[0].half_x, w.entities[0].half_y), (1200, 200));
}

#[test]
fn karakuri_barricade_is_replaced_in_place_destroyed_and_expires() {
    let mut w = barricade_world(0, 1, 4000);
    // Redeploying in place replaces the old barricade.
    w.players[0].ability_cooldown = 0;
    w.step(&[press(ABILITY, 0), press(0, 32768)]).unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::AbilityUsed { slot: 0, class: 4 },
            Event::EntityDestroyed {
                id: 1,
                kind: EntityKind::Barricade,
                owner: 0,
                cause: RemovalCause::Replaced
            },
            Event::EntitySpawned {
                id: 2,
                kind: EntityKind::Barricade,
                owner: 0
            }
        ]
    );
    assert_eq!(w.next_entity_id, 3);
    // Destroyed by the hit that empties it.
    w.entities[0].health = 20;
    w.step(&[press(0, 0), press(FIRE, 32768)]).unwrap();
    assert_eq!(
        w.events[1..],
        [
            Event::EntityDamaged {
                id: 2,
                attacker: 1,
                amount: 20
            },
            Event::EntityDestroyed {
                id: 2,
                kind: EntityKind::Barricade,
                owner: 0,
                cause: RemovalCause::Destroyed { by: 1 }
            }
        ]
    );
    // An untouched barricade lasts 1800 entity-phase ticks.
    let mut w = barricade_world(0, 1, 4000);
    for _ in 1..1799 {
        w.step(&[press(0, 0), press(0, 32768)]).unwrap();
        assert_eq!(w.entities.len(), 1);
    }
    assert_eq!(w.entities[0].age, 1799);
    w.step(&[press(0, 0), press(0, 32768)]).unwrap();
    assert_eq!(
        w.events,
        vec![Event::EntityDestroyed {
            id: 1,
            kind: EntityKind::Barricade,
            owner: 0,
            cause: RemovalCause::Expired
        }]
    );
}

// ---------------------------------------------------------------- Kusushi

#[test]
fn kusushi_ward_reduces_damage_to_protected_players_inside_it() {
    let mut w = world(
        Mode::Control,
        &[
            participant(0, 5, 11),
            participant(0, 0, 1),
            participant(0, 0, 1),
            participant(1, 0, 1),
            participant(1, 0, 1),
        ],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, 4000, 0); // ally on the ward edge
    place(&mut w, 2, -4001, 0); // ally just outside
    place(&mut w, 3, 0, 3000); // enemy inside the ward
    place(&mut w, 4, 4000, -6000);
    w.step(&[
        press(ABILITY, 0),
        press(0, 0),
        press(0, 0),
        press(0, 0),
        press(0, 0),
    ])
    .unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::AbilityUsed { slot: 0, class: 5 },
            Event::EntitySpawned {
                id: 1,
                kind: EntityKind::Ward,
                owner: 0
            }
        ]
    );
    assert_eq!(w.players[0].ability_cooldown, 900);
    // Enemy fire at the edge ally is cut by 35%; the ally outside and the
    // enemy inside take it in full.
    w.step(&[
        press(FIRE, 16384),
        press(0, 0),
        press(0, 0),
        press(0, 0),
        press(FIRE, 16384),
    ])
    .unwrap();
    assert!(w.events.contains(&Event::Damage {
        attacker: 4,
        victim: 1,
        amount: 22 - 22 * 35 / 100
    }));
    assert!(w.events.contains(&Event::Damage {
        attacker: 0,
        victim: 3,
        amount: 18
    }));
    place(&mut w, 4, -4001, -6000);
    for _ in 0..12 {
        w.step(&[
            press(0, 0),
            press(0, 0),
            press(0, 0),
            press(0, 0),
            press(FIRE, 16384),
        ])
        .unwrap();
    }
    assert!(w.events.contains(&Event::Damage {
        attacker: 4,
        victim: 2,
        amount: 22
    }));
    // The ward is removed by the entity phase of its 300th tick.
    while w.tick < 299 {
        w.step(&[Input::default(); 5]).unwrap();
        assert_eq!(w.entities.len(), 1);
    }
    w.step(&[Input::default(); 5]).unwrap();
    assert_eq!(
        w.events,
        vec![Event::EntityDestroyed {
            id: 1,
            kind: EntityKind::Ward,
            owner: 0,
            cause: RemovalCause::Expired
        }]
    );
}

#[test]
fn kusushi_ward_protects_only_its_owner_in_ffa_and_never_self_damage() {
    let mut w = world(
        Mode::FreeForAll,
        &[
            participant(0, 5, 11),
            participant(0, 0, 1),
            participant(0, 3, 7),
        ],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, 1000, 0);
    place(&mut w, 2, 0, -3000);
    w.step(&[press(ABILITY, 0), press(0, 0), press(0, 0)])
        .unwrap();
    // Slot 1 shoots the Kusushi; the Kusushi shoots slot 1 back.
    w.step(&[press(FIRE, 0), press(FIRE, 32768), press(0, 0)])
        .unwrap();
    assert!(w.events.contains(&Event::Damage {
        attacker: 1,
        victim: 0,
        amount: 22 - 7
    }));
    assert!(w.events.contains(&Event::Damage {
        attacker: 0,
        victim: 1,
        amount: 18
    }));

    // In a team match a warded ally's own blast is not reduced.
    let mut w = world(
        Mode::Control,
        &[participant(0, 5, 11), participant(0, 3, 7)],
    );
    place(&mut w, 0, 0, 0);
    place(&mut w, 1, 1000, 0);
    w.step(&[press(ABILITY, 0), press(0, 0)]).unwrap();
    w.projectiles.push(expiring_grenade(
        1,
        Vec3::new(1500, 1500, 1400),
        Vec3::new(0, 350, 0),
    ));
    w.step(&[press(0, 0), press(0, 0)]).unwrap();
    assert!(w.events.contains(&Event::Damage {
        attacker: 1,
        victim: 1,
        amount: 65
    }));
}
