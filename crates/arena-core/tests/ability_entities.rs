//! Rules 7 entity framework (docs/combat-rules.md §5) and ability phase
//! (§2): stable ids and order, the per-owner bound, owner cleanup, and
//! state-hash coverage of every entity, stance and mark field.
use arena_core::{
    catalog::CLASSES,
    economy,
    math::{self, Vec3},
    simulation::{
        ABILITY, Config, Entity, EntityKind, Event, FIRE, Input, MAX_ENTITIES, Mode, Participant,
        RemovalCause, World,
    },
};

fn participant(team: u8, class: u8, weapon: u8) -> Participant {
    Participant {
        team,
        class,
        weapon,
        bond: 0,
        special_entitled: false,
    }
}

fn practice(mode: Mode, roster: &[Participant]) -> World {
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

fn press(buttons: u32, yaw: u16) -> Input {
    Input {
        buttons,
        yaw,
        ..Input::default()
    }
}

fn class_entity(class: u8) -> Option<EntityKind> {
    match class {
        1 => Some(EntityKind::Decoy),
        3 => Some(EntityKind::FireZone),
        4 => Some(EntityKind::Barricade),
        5 => Some(EntityKind::Ward),
        _ => None,
    }
}

/// Twelve players of all six classes start in a ring around the Control
/// point, hold the ability button, and sweep their fire across it while
/// wandering, for 3000 ticks. Returns every tick's state hash.
fn ability_spam() -> Vec<[u8; 32]> {
    let roster = (0..12)
        .map(|slot| participant((slot % 2) as u8, (slot % 6) as u8, (slot % 6 * 2 + 1) as u8))
        .collect::<Vec<_>>();
    let mut w = practice(Mode::Control, &roster);
    for (slot, player) in w.players.iter_mut().enumerate() {
        let angle = slot as u16 * 5461;
        player.position = math::scale_q15(math::direction(angle, 0), 3500);
    }
    let mut hashes = Vec::new();
    let mut spawned = 0;
    let mut removed = [0usize; 5];
    for tick in 0..3000u32 {
        let inputs = std::array::from_fn::<_, 12, _>(|slot| {
            // Aim back across the ring, sweeping +-45 degrees.
            let sweep = (tick * 97 + slot as u32 * 1301) % 16384;
            Input {
                buttons: ABILITY
                    | if !(tick / 40 + slot as u32).is_multiple_of(4) {
                        FIRE
                    } else {
                        0
                    },
                move_x: [40, -40, 20, 0][(tick as usize / 60 + slot) % 4],
                move_y: [0, 60, -60, 30][(tick as usize / 75 + slot) % 4],
                yaw: (slot as u32 * 5461 + 32768 - 8192 + sweep) as u16,
                pitch: -(((tick * 37 + slot as u32 * 911) % 3000) as i16),
            }
        });
        w.step(&inputs).unwrap();
        for event in &w.events {
            match event {
                Event::EntitySpawned { .. } => spawned += 1,
                Event::EntityDestroyed { cause, .. } => {
                    removed[match cause {
                        RemovalCause::Expired => 0,
                        RemovalCause::Destroyed { .. } => 1,
                        RemovalCause::Replaced => 2,
                        RemovalCause::OwnerDied => 3,
                        RemovalCause::OwnerExhausted => 4,
                    }] += 1
                }
                _ => {}
            }
        }
        assert!(w.entities.len() <= MAX_ENTITIES);
        assert!(w.entities.windows(2).all(|pair| pair[0].id < pair[1].id));
        assert!(w.entities.iter().all(|e| e.id < w.next_entity_id));
        for (index, e) in w.entities.iter().enumerate() {
            assert_eq!(Some(e.kind), class_entity(w.players[e.owner].class));
            assert!(
                w.entities[..index]
                    .iter()
                    .all(|other| (other.owner, other.kind) != (e.owner, e.kind)),
                "one live entity per owner and kind"
            );
            assert_eq!(e.position.z, 0);
            assert!(e.age < e.kind.lifetime());
        }
        hashes.push(w.state_hash());
    }
    // The script spawns entities and expires, destroys and replaces them.
    assert!(spawned > 20, "only {spawned} entities spawned");
    assert!(removed[..3].iter().all(|&n| n > 0), "{removed:?}");
    assert_eq!(
        spawned,
        w.entities.len() + removed.iter().sum::<usize>(),
        "every spawned entity is live or was removed exactly once"
    );
    assert!(economy::conserved(&w.accounts));
    hashes
}

#[test]
fn entity_ids_order_and_bound_hold_under_ability_spam_and_replay_exactly() {
    let first = ability_spam();
    let second = ability_spam();
    assert_eq!(first, second);
}

#[test]
fn abilities_resolve_before_any_attack_whatever_the_slot_order() {
    // Slot 0 fires at the Karakuri in slot 1 in the very tick the barricade
    // goes up: the ray still stops on the barricade.
    let mut w = practice(
        Mode::FreeForAll,
        &[participant(0, 0, 1), participant(1, 4, 9)],
    );
    w.players[0].position = Vec3::new(4000, 0, 0);
    w.players[1].position = Vec3::new(0, 0, 0);
    w.step(&[press(FIRE, 32768), press(ABILITY, 0)]).unwrap();
    assert_eq!(
        w.events,
        vec![
            Event::AbilityUsed { slot: 1, class: 4 },
            Event::EntitySpawned {
                id: 1,
                kind: EntityKind::Barricade,
                owner: 1
            },
            Event::Shot { slot: 0, weapon: 1 },
            Event::EntityDamaged {
                id: 1,
                attacker: 0,
                amount: 22
            },
        ]
    );
    // Within the ability phase a lower slot's barricade already blocks a
    // higher slot's Shinobi dash.
    let mut w = practice(
        Mode::FreeForAll,
        &[participant(0, 4, 9), participant(1, 1, 3)],
    );
    w.players[0].position = Vec3::new(0, 0, 0);
    w.players[1].position = Vec3::new(3000, 0, 0);
    w.step(&[press(ABILITY, 0), press(ABILITY, 32768)]).unwrap();
    assert_eq!(w.players[1].position, Vec3::new(3000, 0, 0));
    assert_eq!(
        w.entities
            .iter()
            .map(|e| (e.id, e.kind))
            .collect::<Vec<_>>(),
        vec![(1, EntityKind::Barricade), (2, EntityKind::Decoy)]
    );
}

fn staked_world(roster: &[Participant]) -> World {
    let roster = roster
        .iter()
        .map(|p| Participant {
            bond: 1000,
            ..p.clone()
        })
        .collect::<Vec<_>>();
    World::new(
        Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 3600,
            base_bond: 1000,
            offline: false,
        },
        &roster,
    )
    .unwrap()
}

#[test]
fn barricades_outlive_their_owner_but_exhaustion_removes_every_entity() {
    let roster = [
        participant(0, 4, 9),
        participant(0, 0, 1),
        participant(0, 0, 1),
    ];
    for exhausting in [false, true] {
        let mut w = staked_world(&roster);
        w.players[0].position = Vec3::new(0, 0, 0);
        w.players[1].position = Vec3::new(0, -3000, 0);
        w.players[2].position = Vec3::new(-5000, -5000, 0);
        w.step(&[press(ABILITY, 0), press(0, 0), press(0, 0)])
            .unwrap();
        // A second entity kind for the same owner, as a class change at
        // respawn will allow once loadout selection lands (§10).
        let id = w.next_entity_id;
        w.next_entity_id += 1;
        w.entities.push(Entity {
            id,
            kind: EntityKind::Ward,
            owner: 0,
            team: 0,
            position: Vec3::new(-2000, 0, 0),
            yaw: 0,
            health: 0,
            age: 0,
            half_x: 4000,
            half_y: 4000,
        });
        if exhausting {
            // Nine earlier paid deaths, whose 900 units slot 2 earned.
            w.accounts[0].remaining = 100;
            w.accounts[0].paid_deaths = 9;
            w.accounts[2].earnings = 900;
        }
        w.players[0].health = 1;
        w.step(&[press(0, 0), press(FIRE, 16384), press(0, 0)])
            .unwrap();
        let death = w
            .events
            .iter()
            .position(|e| matches!(e, Event::Death { victim: 0, .. }))
            .expect("the Karakuri dies");
        assert_eq!(w.exhausted(0), exhausting);
        if exhausting {
            assert_eq!(
                w.events[death + 1..],
                [
                    Event::EntityDestroyed {
                        id: 1,
                        kind: EntityKind::Barricade,
                        owner: 0,
                        cause: RemovalCause::OwnerExhausted
                    },
                    Event::EntityDestroyed {
                        id: 2,
                        kind: EntityKind::Ward,
                        owner: 0,
                        cause: RemovalCause::OwnerExhausted
                    }
                ]
            );
            assert!(w.entities.is_empty());
        } else {
            assert_eq!(w.events.len(), death + 1);
            assert_eq!(w.entities.len(), 2);
        }
        assert!(economy::conserved(&w.accounts));
    }
}

#[test]
fn ability_cooldown_keeps_counting_while_dead() {
    let mut w = practice(
        Mode::FreeForAll,
        &[participant(0, 5, 11), participant(1, 0, 1)],
    );
    w.players[0].position = Vec3::new(0, 0, 0);
    w.players[1].position = Vec3::new(0, -3000, 0);
    w.players[0].ability_cooldown = 500;
    w.players[0].health = 1;
    w.step(&[press(0, 0), press(FIRE, 16384)]).unwrap();
    assert!(!w.players[0].alive);
    assert_eq!(w.players[0].ability_cooldown, 499);
    let mut respawned = false;
    while !respawned {
        w.step(&[press(0, 0), press(0, 0)]).unwrap();
        respawned = w.events.contains(&Event::Respawn { slot: 0 });
    }
    assert_eq!(w.players[0].ability_cooldown, 499 - 480);
    assert_eq!(w.players[0].health, CLASSES[5].health);
}

/// One named state change that the hash must notice.
type Mutation = (&'static str, fn(&mut World));

fn hash_after(base: &World, mutate: fn(&mut World)) -> [u8; 32] {
    let mut w = base.clone();
    mutate(&mut w);
    w.state_hash()
}

#[test]
fn state_hash_covers_every_entity_field_and_the_stance_and_mark_timers() {
    let mut base = practice(
        Mode::FreeForAll,
        &[participant(0, 4, 9), participant(1, 1, 3)],
    );
    base.players[0].position = Vec3::new(0, 0, 0);
    base.players[1].position = Vec3::new(-3000, 3000, 0);
    base.step(&[press(ABILITY, 0), press(ABILITY, 0)]).unwrap();
    assert_eq!(base.entities.len(), 2);
    let mutations: [Mutation; 17] = [
        ("id", |w| w.entities[0].id = 7),
        ("kind", |w| w.entities[0].kind = EntityKind::Ward),
        ("owner", |w| w.entities[0].owner = 1),
        ("team", |w| w.entities[0].team = 1),
        ("x", |w| w.entities[0].position.x += 1),
        ("y", |w| w.entities[0].position.y += 1),
        ("z", |w| w.entities[0].position.z += 1),
        ("yaw", |w| w.entities[0].yaw += 1),
        ("health", |w| w.entities[0].health -= 1),
        ("age", |w| w.entities[0].age += 1),
        ("half_x", |w| w.entities[0].half_x += 1),
        ("half_y", |w| w.entities[0].half_y += 1),
        ("order", |w| w.entities.swap(0, 1)),
        ("removed", |w| {
            w.entities.pop();
        }),
        ("next id", |w| w.next_entity_id += 1),
        ("stance", |w| w.players[0].stance_ticks = 1),
        ("mark", |w| w.players[1].marked_ticks = 1),
    ];
    let reference = base.state_hash();
    let mut seen = vec![reference];
    for (field, mutate) in mutations {
        let hash = hash_after(&base, mutate);
        assert!(!seen.contains(&hash), "state hash ignores entity {field}");
        seen.push(hash);
    }
    assert_eq!(base.state_hash(), reference);
}
