use arena_core::{
    math::Vec3,
    simulation::{
        Config, DamageRecord, Entity, EntityKind, Event, FIRE, Input, Mode, Participant,
        Projectile, Winner, World,
    },
};
use sha2::{Digest, Sha256};

fn world() -> World {
    World::new(
        Config {
            mode: Mode::Control,
            map: 0,
            max_ticks: 36_000,
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
                class: 3,
                weapon: 7,
                bond: 0,
                special_entitled: false,
            },
        ],
    )
    .unwrap()
}

fn assert_bound(world: &World, name: &str, mutate: impl FnOnce(&mut World)) {
    let before = world.state_bytes();
    let before_hash = world.state_hash();
    let mut changed = world.clone();
    mutate(&mut changed);
    let after = changed.state_bytes();
    assert_ne!(after, before, "unbound canonical field: {name}");
    assert_ne!(
        changed.state_hash(),
        before_hash,
        "unbound digest field: {name}"
    );
    assert_eq!(
        <[u8; 32]>::from(Sha256::digest(&after)),
        changed.state_hash(),
        "stream mismatch: {name}"
    );
}

#[test]
fn every_outcome_field_affects_the_canonical_stream() {
    let mut w = world();
    // Deliberately exercise the stored state directly: this tests encoding
    // coverage, not a claim that these synthetic boundaries are reachable.
    w.players[0].admitted_special = Some(12);
    w.players[0].pending_loadout = Some((0, 1));
    w.projectiles.push(Projectile {
        id: 1,
        owner: 1,
        position: Vec3::new(100, 200, 1400),
        velocity: Vec3::new(350, 0, 0),
        weapon: 7,
        traveled: 350,
        age: 1,
    });
    w.entities.push(Entity {
        id: 1,
        kind: EntityKind::Decoy,
        owner: 0,
        team: 0,
        position: Vec3::new(500, 600, 0),
        yaw: 0,
        health: 60,
        age: 1,
        half_x: 350,
        half_y: 350,
    });
    w.next_entity_id = 2;
    w.damage_history.push(DamageRecord {
        tick: 0,
        attacker: 0,
        victim: 1,
        damage: 22,
    });
    w.control_owner = Some(0);
    w.winner = Some(Winner::Team(0));

    macro_rules! bound {
        ($name:literal, $change:expr) => {
            assert_bound(&w, $name, $change);
        };
    }
    bound!("config.mode", |w| w.config.mode = Mode::Payload);
    bound!("config.map", |w| w.config.map = 1);
    bound!("config.max_ticks", |w| w.config.max_ticks -= 1);
    bound!("config.base_bond", |w| w.config.base_bond = 10);
    bound!("config.offline", |w| w.config.offline = false);
    bound!("tick", |w| w.tick = 1);
    bound!("terminal", |w| w.terminal = true);
    bound!("player/account count", |w| {
        w.players.pop();
        w.accounts.pop();
    });
    bound!("player/account order", |w| {
        w.players.swap(0, 1);
        w.accounts.swap(0, 1);
    });
    bound!("player.team", |w| w.players[0].team = 1);
    bound!("player.class", |w| w.players[0].class = 1);
    bound!("player.weapon", |w| w.players[0].weapon = 0);
    bound!("player.position.x", |w| w.players[0].position.x += 1);
    bound!("player.position.y", |w| w.players[0].position.y += 1);
    bound!("player.position.z", |w| w.players[0].position.z += 1);
    bound!("player.velocity_z", |w| w.players[0].velocity_z = -1);
    bound!("player.yaw", |w| w.players[0].yaw ^= 1);
    bound!("player.pitch", |w| w.players[0].pitch = -1);
    bound!("player.health", |w| w.players[0].health -= 1);
    bound!("player.stamina", |w| w.players[0].stamina -= 1);
    bound!("player.alive", |w| w.players[0].alive = false);
    bound!("player.respawn_ticks", |w| w.players[0].respawn_ticks = 1);
    bound!("player.attack_cooldown", |w| w.players[0].attack_cooldown =
        1);
    bound!("player.ability_cooldown", |w| w.players[0]
        .ability_cooldown = 1);
    bound!("player.charge", |w| w.players[0].charge = 1);
    bound!("player.charge_weapon", |w| w.players[0].charge_weapon = 0);
    bound!("player.ammo", |w| w.players[0].ammo -= 1);
    bound!("player.reload_ticks", |w| w.players[0].reload_ticks = 1);
    bound!("player.guarding", |w| w.players[0].guarding = true);
    bound!("player.guard_ticks", |w| w.players[0].guard_ticks = 1);
    bound!("player.spawn_protection", |w| w.players[0]
        .spawn_protection = 1);
    bound!("player.admitted_special value", |w| w.players[0]
        .admitted_special =
        Some(13));
    bound!("player.admitted_special none", |w| w.players[0]
        .admitted_special =
        None);
    bound!("player.pending_loadout class", |w| w.players[0]
        .pending_loadout =
        Some((1, 1)));
    bound!("player.pending_loadout weapon", |w| w.players[0]
        .pending_loadout =
        Some((0, 0)));
    bound!("player.pending_loadout none", |w| w.players[0]
        .pending_loadout =
        None);
    bound!("player.stance_ticks", |w| w.players[0].stance_ticks = 1);
    bound!("player.marked_ticks", |w| w.players[0].marked_ticks = 1);
    bound!("account.initial", |w| w.accounts[0].initial = 10);
    bound!("account.remaining", |w| w.accounts[0].remaining = 10);
    bound!("account.earnings", |w| w.accounts[0].earnings = 10);
    bound!("account.kills", |w| w.accounts[0].kills = 1);
    bound!("account.deaths", |w| w.accounts[0].deaths = 1);
    bound!("account.paid_deaths", |w| w.accounts[0].paid_deaths = 1);
    bound!("projectile count", |w| w.projectiles.clear());
    bound!("projectile.id", |w| w.projectiles[0].id += 1);
    bound!("projectile.owner", |w| w.projectiles[0].owner = 0);
    bound!("projectile.position.x", |w| w.projectiles[0].position.x +=
        1);
    bound!("projectile.position.y", |w| w.projectiles[0].position.y +=
        1);
    bound!("projectile.position.z", |w| w.projectiles[0].position.z +=
        1);
    bound!("projectile.velocity.x", |w| w.projectiles[0].velocity.x +=
        1);
    bound!("projectile.velocity.y", |w| w.projectiles[0].velocity.y +=
        1);
    bound!("projectile.velocity.z", |w| w.projectiles[0].velocity.z +=
        1);
    bound!("projectile.weapon", |w| w.projectiles[0].weapon = 13);
    bound!("projectile.traveled", |w| w.projectiles[0].traveled += 1);
    bound!("projectile.age", |w| w.projectiles[0].age += 1);
    bound!("entity count", |w| w.entities.clear());
    bound!("entity.id", |w| w.entities[0].id += 1);
    bound!("entity.kind", |w| w.entities[0].kind =
        EntityKind::Barricade);
    bound!("entity.owner", |w| w.entities[0].owner = 1);
    bound!("entity.team", |w| w.entities[0].team = 1);
    bound!("entity.position.x", |w| w.entities[0].position.x += 1);
    bound!("entity.position.y", |w| w.entities[0].position.y += 1);
    bound!("entity.position.z", |w| w.entities[0].position.z += 1);
    bound!("entity.yaw", |w| w.entities[0].yaw = 1);
    bound!("entity.health", |w| w.entities[0].health -= 1);
    bound!("entity.age", |w| w.entities[0].age += 1);
    bound!("entity.half_x", |w| w.entities[0].half_x += 1);
    bound!("entity.half_y", |w| w.entities[0].half_y += 1);
    bound!("next_entity_id", |w| w.next_entity_id += 1);
    bound!("damage count", |w| w.damage_history.clear());
    bound!("damage.tick", |w| w.damage_history[0].tick += 1);
    bound!("damage.attacker", |w| w.damage_history[0].attacker = 1);
    bound!("damage.victim", |w| w.damage_history[0].victim = 0);
    bound!("damage.damage", |w| w.damage_history[0].damage += 1);
    bound!("score[0]", |w| w.score[0] = 1);
    bound!("score[1]", |w| w.score[1] = 1);
    bound!("control_owner value", |w| w.control_owner = Some(1));
    bound!("control_owner none", |w| w.control_owner = None);
    bound!("control_progress", |w| w.control_progress = -1);
    bound!("overtime", |w| w.overtime = true);
    bound!("payload_progress", |w| w.payload_progress = 1);
    bound!("payload_checkpoints", |w| w.payload_checkpoints = 1);
    bound!("payload_idle", |w| w.payload_idle = 1);
    bound!("winner team value", |w| w.winner = Some(Winner::Team(1)));
    bound!("winner slot tag", |w| w.winner = Some(Winner::Slot(0)));
    bound!("winner slot value", |w| w.winner = Some(Winner::Slot(1)));
    bound!("winner draw", |w| w.winner = Some(Winner::Draw));
    bound!("winner none", |w| w.winner = None);
}

#[test]
fn ordered_combat_records_are_never_sorted_by_the_encoder() {
    let mut w = world();
    w.projectiles = (0..2)
        .map(|owner| Projectile {
            id: owner as u32,
            owner,
            position: Vec3::new(0, 0, 1400),
            velocity: Vec3::new(350, 0, 0),
            weapon: 7,
            traveled: 350,
            age: 1,
        })
        .collect();
    w.entities = (0..2)
        .map(|owner| Entity {
            id: owner as u32 + 1,
            kind: EntityKind::Decoy,
            owner,
            team: owner as u8,
            position: Vec3::default(),
            yaw: 0,
            health: 60,
            age: 1,
            half_x: 350,
            half_y: 350,
        })
        .collect();
    // Equal-tick damage still has meaningful insertion order: environmental
    // kill attribution scans it backwards for the last qualifying attacker.
    w.damage_history = (0..2)
        .map(|attacker| DamageRecord {
            tick: 0,
            attacker,
            victim: 1 - attacker,
            damage: 22,
        })
        .collect();
    assert_bound(&w, "projectile order", |w| w.projectiles.swap(0, 1));
    assert_bound(&w, "entity order", |w| w.entities.swap(0, 1));
    assert_bound(&w, "damage order", |w| w.damage_history.swap(0, 1));
}

#[test]
fn presentation_output_is_deliberately_not_state() {
    let mut w = world();
    let bytes = w.state_bytes();
    let hash = w.state_hash();
    w.events.push(Event::Death {
        victim: 0,
        killer: Some(1),
        awards: Vec::new(),
    });
    w.removed_entities.push(Entity {
        id: 1,
        kind: EntityKind::Decoy,
        owner: 0,
        team: 0,
        position: Vec3::default(),
        yaw: 0,
        health: 0,
        age: 300,
        half_x: 350,
        half_y: 350,
    });
    assert_eq!(w.state_bytes(), bytes);
    assert_eq!(w.state_hash(), hash);
}

#[test]
fn mismatched_account_lists_cannot_silently_drop_a_slot() {
    for more in [false, true] {
        let mut w = world();
        if more {
            w.accounts.push(w.accounts[0].clone());
        } else {
            w.accounts.pop();
        }
        assert!(std::panic::catch_unwind(|| w.state_bytes()).is_err());
        assert!(std::panic::catch_unwind(|| w.state_hash()).is_err());
    }
}

#[test]
fn exact_bytes_retain_all_27_recorded_research_hashes() {
    // This existing fixed scene is a regression anchor only, not admissible
    // genesis or proof authority. Its expected hashes predate this encoder.
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("data/arena_kill_history_v2_kernel.json")).unwrap();
    let mut w = World::new(
        Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 26,
            base_bond: 1000,
            offline: false,
        },
        &(0..3)
            .map(|slot| Participant {
                team: 0,
                class: 0,
                weapon: u8::from(slot < 2),
                bond: 1000,
                special_entitled: false,
            })
            .collect::<Vec<_>>(),
    )
    .unwrap();
    for (player, (x, y)) in w.players.iter_mut().zip([(0, -6000), (-6000, 0), (0, 0)]) {
        player.position = Vec3::new(x, y, 0);
    }
    for tick in 0..=26 {
        let bytes = w.state_bytes();
        let hash = w.state_hash();
        assert_eq!(<[u8; 32]>::from(Sha256::digest(&bytes)), hash);
        let hex: String = hash.iter().map(|byte| format!("{byte:02x}")).collect();
        assert_eq!(
            hex,
            fixture["state_hashes"][tick].as_str().unwrap(),
            "boundary {tick}"
        );
        if tick < 26 {
            let inputs = (0..3)
                .map(|slot| Input {
                    buttons: u32::from(slot < 2 && matches!(tick, 0 | 12 | 24)) * FIRE,
                    yaw: if slot == 0 { 16_384 } else { 0 },
                    ..Input::default()
                })
                .collect::<Vec<_>>();
            w.step(&inputs).unwrap();
        }
    }
}
