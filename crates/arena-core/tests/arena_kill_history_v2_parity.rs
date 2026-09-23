//! Independent arena-core replay for the unregistered Iroha 26-tick kill-history research scene.
//! The JSON projection is a regression fixture, not a proof or admission authority.

use arena_core::simulation::{Config, Event, FIRE, Input, Mode, Participant, World};
use arena_core::{ABI_VERSION, RULES_VERSION};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

const FIXTURE_PATH: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/tests/data/arena_kill_history_v2_kernel.json"
);

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
    for (name, source) in [
        ("lib.rs", include_bytes!("../src/lib.rs").as_slice()),
        (
            "simulation.rs",
            include_bytes!("../src/simulation.rs").as_slice(),
        ),
        ("catalog.rs", include_bytes!("../src/catalog.rs").as_slice()),
        ("math.rs", include_bytes!("../src/math.rs").as_slice()),
        ("economy.rs", include_bytes!("../src/economy.rs").as_slice()),
        (
            "protocol.rs",
            include_bytes!("../src/protocol.rs").as_slice(),
        ),
    ] {
        digest.update((name.len() as u64).to_le_bytes());
        digest.update(name.as_bytes());
        digest.update((source.len() as u64).to_le_bytes());
        digest.update(source);
    }
    hex(&digest.finalize())
}

fn input(slot: usize, tick: usize) -> Input {
    Input {
        buttons: u32::from(slot < 2 && matches!(tick, 0 | 12 | 24)) * FIRE,
        yaw: match slot {
            0 => 24_576,
            1 => 8_192,
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
}
