//! Independent arena-core replay for the unregistered Iroha 26-tick kill-history research scene.
//! The JSON projection is a regression fixture, not a proof or admission authority.

use arena_core::math::Vec3;
use arena_core::simulation::{Config, Event, FIRE, Input, Mode, Participant, Winner, World};
use arena_core::{ABI_VERSION, RULES_VERSION};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::Path;

const FIXTURE_PATH: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/tests/data/arena_kill_history_v2_kernel.json"
);

macro_rules! kernel_sources {
    ($($name:literal),+ $(,)?) => {
        &[$(($name, include_bytes!(concat!("../src/", $name)).as_slice())),+]
    };
}

/// Every `src/` file that can change the replayed World or its canonical
/// batches, in `kernel_revision` hashing order.
const KERNEL_SOURCES: &[(&str, &[u8])] = kernel_sources![
    "lib.rs",
    "simulation.rs",
    "simulation/abilities.rs",
    "simulation/hazards.rs",
    "simulation/objectives.rs",
    "simulation/respawn.rs",
    "maps.rs",
    "catalog.rs",
    "math.rs",
    "economy.rs",
    "protocol.rs",
];

/// `src/` files outside the kernel's dependency closure: the arena JSON
/// export, transport, handshake, rollback and recovery layers that consume the
/// kernel, and a `#[cfg(test)]` economy oracle. The classification test
/// rejects any other file.
const NON_SIMULATION_SOURCES: &[&str] = &[
    "arena_export.rs",
    "economy_reference_qualification.rs",
    "encrypted_wire.rs",
    "fragmented_wire.rs",
    "handshake.rs",
    "localhost_transport.rs",
    "recovery.rs",
    "rollback.rs",
    "wire.rs",
];

fn hex(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for &byte in bytes {
        out.push(DIGITS[(byte >> 4) as usize] as char);
        out.push(DIGITS[(byte & 15) as usize] as char);
    }
    out
}

fn kernel_revision() -> String {
    let mut digest = Sha256::new();
    for (name, source) in KERNEL_SOURCES {
        digest.update((name.len() as u64).to_le_bytes());
        digest.update(name.as_bytes());
        digest.update((source.len() as u64).to_le_bytes());
        digest.update(source);
    }
    hex(&digest.finalize())
}

/// Scene positions on Nyaagyu Estate: slot 2 stands on the Control centre and
/// slots 0 and 1 aim at it along clear axis-aligned lines 6000 mm long.
const SCENE: [(i32, i32); 3] = [(0, -6000), (-6000, 0), (0, 0)];

fn input(slot: usize, tick: usize) -> Input {
    Input {
        buttons: u32::from(slot < 2 && matches!(tick, 0 | 12 | 24)) * FIRE,
        yaw: match slot {
            0 => 16_384,
            _ => 0,
        },
        ..Input::default()
    }
}

fn projected_state(world: &World) -> Value {
    let players = &world.players;
    let accounts = &world.accounts;
    assert_eq!(players.len(), 3);
    assert_eq!(accounts.len(), 3);
    json!({
        "tick": world.tick,
        "positions": players.iter().map(|p| [p.position.x, p.position.y, p.position.z]).collect::<Vec<_>>(),
        "health": players.iter().map(|p| p.health).collect::<Vec<_>>(),
        "stamina": players.iter().map(|p| p.stamina).collect::<Vec<_>>(),
        "ammo": players.iter().map(|p| p.ammo).collect::<Vec<_>>(),
        "cooldown": players.iter().map(|p| p.attack_cooldown).collect::<Vec<_>>(),
        "yaw": players.iter().map(|p| p.yaw).collect::<Vec<_>>(),
        "alive": players.iter().map(|p| p.alive).collect::<Vec<_>>(),
        "terminal": world.terminal,
        "respawn_ticks": players.iter().map(|p| p.respawn_ticks).collect::<Vec<_>>(),
        "reserve": accounts.iter().map(|a| a.remaining).collect::<Vec<_>>(),
        "earnings": accounts.iter().map(|a| a.earnings).collect::<Vec<_>>(),
        "paid_deaths": accounts.iter().map(|a| a.paid_deaths).collect::<Vec<_>>(),
        "deaths": accounts.iter().map(|a| a.deaths).collect::<Vec<_>>(),
        "kills": accounts.iter().map(|a| a.kills).collect::<Vec<_>>(),
    })
}

fn projected_event(tick: usize, event: &Event) -> Value {
    match event {
        Event::Shot { slot, weapon } => {
            json!({"tick": tick, "kind": "shot", "slot": slot, "weapon": weapon})
        }
        Event::Damage {
            attacker,
            victim,
            amount,
        } => json!({
            "tick": tick, "kind": "damage", "attacker": attacker,
            "victim": victim, "amount": amount,
        }),
        Event::Death {
            victim,
            killer,
            awards,
        } => json!({
            "tick": tick, "kind": "death", "victim": victim, "killer": killer,
            "awards": awards.iter().map(|a| json!({"slot": a.slot, "amount": a.amount})).collect::<Vec<_>>(),
        }),
        Event::Respawn { slot } => json!({"tick": tick, "kind": "respawn", "slot": slot}),
        Event::Terminal => json!({"tick": tick, "kind": "terminal"}),
        Event::Guarded {
            attacker,
            victim,
            weapon,
            parried,
            prevented,
        } => json!({
            "tick": tick, "kind": "guarded", "attacker": attacker, "victim": victim,
            "weapon": weapon, "parried": parried, "prevented": prevented,
        }),
        Event::Healed {
            healer,
            target,
            amount,
            weapon,
        } => json!({
            "tick": tick, "kind": "healed", "healer": healer, "target": target,
            "amount": amount, "weapon": weapon,
        }),
        Event::AbilityUsed { slot, class } => {
            json!({"tick": tick, "kind": "ability", "slot": slot, "class": class})
        }
        Event::Marked { marker, target } => {
            json!({"tick": tick, "kind": "marked", "marker": marker, "target": target})
        }
        Event::Riposte { slot, target } => {
            json!({"tick": tick, "kind": "riposte", "slot": slot, "target": target})
        }
        Event::EntitySpawned { id, kind, owner } => json!({
            "tick": tick, "kind": "entity_spawned", "id": id,
            "entity_kind": *kind as u8, "owner": owner,
        }),
        Event::EntityDamaged {
            id,
            attacker,
            amount,
        } => json!({
            "tick": tick, "kind": "entity_damaged", "id": id,
            "attacker": attacker, "amount": amount,
        }),
        Event::EntityRepaired {
            id,
            repairer,
            amount,
        } => json!({
            "tick": tick, "kind": "entity_repaired", "id": id,
            "repairer": repairer, "amount": amount,
        }),
        Event::EntityDestroyed {
            id,
            kind,
            owner,
            cause,
        } => json!({
            "tick": tick, "kind": "entity_destroyed", "id": id,
            "entity_kind": *kind as u8, "owner": owner, "cause": format!("{cause:?}"),
        }),
        Event::EnvironmentalDamage {
            victim,
            hazard,
            amount,
        } => json!({
            "tick": tick, "kind": "environmental_damage", "victim": victim,
            "hazard": hazard, "amount": amount,
        }),
        Event::ObjectiveCaptured { team } => {
            json!({"tick": tick, "kind": "objective_captured", "team": team})
        }
        Event::OvertimeStarted => json!({"tick": tick, "kind": "overtime_started"}),
        Event::CheckpointReached { index } => {
            json!({"tick": tick, "kind": "checkpoint_reached", "index": index})
        }
        Event::MatchWinner { winner } => json!({
            "tick": tick, "kind": "match_winner",
            "winner": match winner {
                Winner::Team(team) => json!({"team": team}),
                Winner::Slot(slot) => json!({"slot": slot}),
                Winner::Draw => json!("draw"),
            },
        }),
    }
}

fn replay_fixture() -> Value {
    let mut world = World::new(
        Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 26,
            base_bond: 1000,
            offline: false,
        },
        &[
            Participant {
                team: 0,
                class: 0,
                weapon: 1,
                bond: 1000,
                special_entitled: false,
            },
            Participant {
                team: 0,
                class: 0,
                weapon: 1,
                bond: 1000,
                special_entitled: false,
            },
            Participant {
                team: 0,
                class: 0,
                weapon: 0,
                bond: 1000,
                special_entitled: false,
            },
        ],
    )
    .expect("fixed V2 scene must be admitted by the current kernel");
    for (player, (x, y)) in world.players.iter_mut().zip(SCENE) {
        player.position = Vec3::new(x, y, 0);
    }

    // A batch lists permanent slots in order; each contains its two exact wire frames.
    let batches = (0..13)
        .map(|batch| {
            let controls_hex = (0..3)
                .map(|slot| {
                    (0..2)
                        .map(|offset| hex(&input(slot, batch * 2 + offset).encode()))
                        .collect::<Vec<_>>()
                })
                .collect::<Vec<_>>();
            json!({"start_tick": batch * 2, "controls_hex": controls_hex})
        })
        .collect::<Vec<_>>();

    let mut states = vec![projected_state(&world)];
    let mut state_hashes = vec![hex(&world.state_hash())];
    let mut events = Vec::new();
    for tick in 0..26 {
        // Decode the exact eight-byte canonical frames that the fixture publishes.
        let inputs = (0..3)
            .map(|slot| Input::decode(input(slot, tick).encode()).expect("canonical input"))
            .collect::<Vec<_>>();
        world.step(&inputs).expect("fixed V2 combat step");
        events.extend(
            world
                .events
                .iter()
                .map(|event| projected_event(tick, event)),
        );
        states.push(projected_state(&world));
        state_hashes.push(hex(&world.state_hash()));
    }
    let final_allocations = world
        .accounts
        .iter()
        .map(|account| account.remaining + account.earnings)
        .collect::<Vec<_>>();
    json!({
        "schema": "sora-arena-kill-history-v2-kernel-parity-v1",
        "scope": "unregistered-unfunded-fixed-research-scene",
        "kernel_revision": kernel_revision(),
        "rules_version": RULES_VERSION,
        "abi_version": ABI_VERSION,
        "batches": batches,
        "states": states,
        "state_hashes": state_hashes,
        "events": events,
        "final_allocations": final_allocations,
    })
}

#[test]
fn exact_26_tick_kernel_replay_matches_persisted_v2_projection() {
    let actual = replay_fixture();
    if std::env::var("ARENA_REGENERATE_KILL_V2_FIXTURE").as_deref() == Ok("1") {
        std::fs::write(
            FIXTURE_PATH,
            format!("{}\n", serde_json::to_string_pretty(&actual).unwrap()),
        )
        .expect("write research projection");
    }
    let expected: Value = serde_json::from_str(
        &std::fs::read_to_string(FIXTURE_PATH).expect("read persisted research projection"),
    )
    .expect("valid JSON research projection");
    assert_eq!(
        actual, expected,
        "arena-core changed; update V2 relation and fixture together"
    );
    assert_eq!(actual["states"].as_array().unwrap().len(), 27);
    assert_eq!(actual["batches"].as_array().unwrap().len(), 13);
    assert_eq!(actual["final_allocations"], json!([1020, 1080, 900]));
    assert_eq!(actual["states"][25]["respawn_ticks"][2], 480);
    assert_eq!(actual["states"][26]["respawn_ticks"][2], 479);
    assert_eq!(actual["states"][26]["terminal"], true);
    let death_events = actual["events"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|event| event["kind"] == "death")
        .collect::<Vec<_>>();
    assert_eq!(death_events.len(), 1);
    assert_eq!(death_events[0]["tick"], 24);
    assert_eq!(death_events[0]["victim"], 2);
    assert_eq!(death_events[0]["killer"], 1);
    assert_eq!(
        death_events[0]["awards"],
        json!([{"slot": 0, "amount": 20}, {"slot": 1, "amount": 80}])
    );
    let events = actual["events"].as_array().unwrap();
    assert_eq!(
        events[events.len() - 2..],
        [
            json!({"tick": 25, "kind": "match_winner", "winner": {"slot": 1}}),
            json!({"tick": 25, "kind": "terminal"}),
        ]
    );
}

fn source_files(directory: &Path, root: &Path, found: &mut Vec<String>) {
    for entry in std::fs::read_dir(directory).expect("read arena-core source directory") {
        let path = entry.expect("arena-core source entry").path();
        let hidden = path
            .file_name()
            .is_some_and(|name| name.to_string_lossy().starts_with('.'));
        if hidden {
            continue;
        }
        if path.is_dir() {
            source_files(&path, root, found);
        } else {
            let relative = path.strip_prefix(root).expect("path below src");
            found.push(relative.to_string_lossy().replace('\\', "/"));
        }
    }
}

/// Lexical guard: true when `source` uses `module` as a path segment.
fn uses_module(source: &str, module: &str) -> bool {
    let boundary = |c: Option<char>| !c.is_some_and(|c| c.is_ascii_alphanumeric() || c == '_');
    source.match_indices(module).any(|(start, _)| {
        let (before, after) = (&source[..start], &source[start + module.len()..]);
        boundary(before.chars().next_back())
            && boundary(after.chars().next())
            && (after.starts_with("::")
                || before.ends_with("crate::")
                || before.ends_with("super::"))
    })
}

#[test]
fn kernel_revision_classifies_every_arena_core_source() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
    let mut found = Vec::new();
    source_files(&root, &root, &mut found);
    found.sort();
    let kernel = KERNEL_SOURCES
        .iter()
        .map(|(name, _)| name.to_string())
        .collect::<Vec<_>>();
    let mut classified = kernel
        .iter()
        .cloned()
        .chain(NON_SIMULATION_SOURCES.iter().map(|name| name.to_string()))
        .collect::<Vec<_>>();
    classified.sort();
    assert_eq!(
        found, classified,
        "classify each arena-core src file exactly once: hash it in KERNEL_SOURCES \
         if it can affect the replay, otherwise list it in NON_SIMULATION_SOURCES"
    );

    for (name, source) in KERNEL_SOURCES {
        let text = std::str::from_utf8(source).expect("UTF-8 kernel source");
        for excluded in NON_SIMULATION_SOURCES {
            let file = Path::new(excluded);
            let module = match file.file_stem().and_then(|stem| stem.to_str()) {
                Some("mod") => file.parent().and_then(|parent| parent.file_name()),
                _ => file.file_stem(),
            }
            .and_then(|module| module.to_str())
            .expect("module name");
            assert!(
                !uses_module(text, module),
                "{name} uses `{module}`; hash {excluded} in KERNEL_SOURCES"
            );
        }
        // A `#[path]` module compiled outside tests is part of the kernel.
        let lines = text.lines().map(str::trim).collect::<Vec<_>>();
        for (index, line) in lines.iter().enumerate() {
            let Some(target) = line
                .strip_prefix("#[path = \"")
                .and_then(|rest| rest.strip_suffix("\"]"))
            else {
                continue;
            };
            let target = Path::new(name)
                .parent()
                .expect("relative source path")
                .join(target)
                .to_string_lossy()
                .replace('\\', "/");
            assert!(
                kernel.contains(&target) || (index > 0 && lines[index - 1] == "#[cfg(test)]"),
                "{name} compiles {target} outside #[cfg(test)]; hash it in KERNEL_SOURCES"
            );
        }
    }
}
