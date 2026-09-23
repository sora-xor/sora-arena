//! Bounded eight-player, two-minute local combat-replay research fixture.
//! This exercises the reference kernel only: no peers, proofs, wallets, or ledger.
use arena_core::{
    TICK_RATE, economy,
    simulation::{Config, Event, FIRE, Input, Mode, Participant, World},
};
use sha2::{Digest, Sha256};
use std::time::{Duration, Instant};

const PLAYERS: usize = 8;
const TICKS: u32 = 2 * 60 * TICK_RATE;
const EXPECTED_FINAL_HASH: &str =
    "ae4f7add6174106217c1ba20f1dc18da4b1c28456a7630931739f5ba78ea60be";
const EXPECTED_TIMELINE_HASH: &str =
    "effafb52709a3fc946c82eeb3ad80b3b2616193c0505c22289273e16f754fe56";

fn participants() -> [Participant; PLAYERS] {
    std::array::from_fn(|slot| Participant {
        team: (slot % 2) as u8,
        class: 0,
        weapon: 1,
        bond: 0,
        special_entitled: false,
    })
}

fn controls(tick: u32) -> [Input; PLAYERS] {
    // Both teams route north of Estate walls, approach each other with held
    // Arc-carbine fire, then repeat. This is a fixed script, not a bot policy.
    let phase = tick % 900;
    std::array::from_fn(|slot| {
        let team = slot % 2;
        Input {
            buttons: FIRE,
            move_x: if phase < 250 {
                0
            } else if phase < 700 || (phase / 50).is_multiple_of(2) {
                127
            } else {
                -127
            },
            move_y: if phase < 250 {
                if team == 0 { 127 } else { -127 }
            } else {
                0
            },
            yaw: if team == 0 { 0 } else { 32768 },
            pitch: 0,
        }
    })
}

#[derive(Debug, Default, PartialEq, Eq)]
struct EventCounts {
    shots: u32,
    damage: u32,
    deaths: u32,
    respawns: u32,
    terminal: u32,
}

struct Run {
    final_hash: [u8; 32],
    timeline_hash: [u8; 32],
    tick_hashes: Vec<[u8; 32]>,
    encoded_inputs: Vec<[[u8; 8]; PLAYERS]>,
    events: EventCounts,
    elapsed: Duration,
}

fn run(mut input_for_tick: impl FnMut(u32) -> [Input; PLAYERS]) -> Run {
    let mut world = World::new(
        Config {
            mode: Mode::Control,
            map: 0,
            max_ticks: TICKS,
            base_bond: 0,
            offline: true,
        },
        &participants(),
    )
    .unwrap();
    let mut timeline = Sha256::new();
    timeline.update(b"sora-arena:8-player-2-minute-local-research:v1\0");
    let mut tick_hashes = Vec::with_capacity(TICKS as usize);
    let mut encoded_inputs = Vec::with_capacity(TICKS as usize);
    let mut events = EventCounts::default();
    let start = Instant::now();
    for tick in 0..TICKS {
        assert_eq!(world.tick, tick);
        assert!(
            !world.terminal,
            "local simulation ended before {TICKS} ticks"
        );
        let inputs = input_for_tick(tick);
        let encoded = inputs.map(Input::encode);
        for bytes in encoded {
            timeline.update(bytes);
        }
        world.step(&inputs).unwrap();
        for event in &world.events {
            match event {
                Event::Shot { .. } => events.shots += 1,
                Event::Damage { .. } => events.damage += 1,
                Event::Death { .. } => events.deaths += 1,
                Event::Respawn { .. } => events.respawns += 1,
                Event::Terminal => events.terminal += 1,
            }
        }
        let hash = world.state_hash();
        timeline.update(hash);
        tick_hashes.push(hash);
        encoded_inputs.push(encoded);
    }
    let elapsed = start.elapsed();
    assert_eq!(world.tick, TICKS);
    assert!(world.terminal);
    assert_eq!(events.terminal, 1);
    assert!(economy::conserved(&world.accounts));
    assert!(world.accounts.iter().all(|account| account.initial == 0));
    Run {
        final_hash: world.state_hash(),
        timeline_hash: timeline.finalize().into(),
        tick_hashes,
        encoded_inputs,
        events,
        elapsed,
    }
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[test]
fn eight_player_two_minute_fixed_inputs_repeat_and_replay() {
    let first = run(controls);
    assert_eq!(hex(&first.final_hash), EXPECTED_FINAL_HASH);
    assert_eq!(hex(&first.timeline_hash), EXPECTED_TIMELINE_HASH);
    let repeated = run(controls);
    let replayed =
        run(|tick| first.encoded_inputs[tick as usize].map(|bytes| Input::decode(bytes).unwrap()));
    for other in [&repeated, &replayed] {
        assert_eq!(first.final_hash, other.final_hash);
        assert_eq!(first.timeline_hash, other.timeline_hash);
        assert_eq!(first.tick_hashes, other.tick_hashes);
        assert_eq!(first.events, other.events);
    }
    assert!(first.events.shots > 0, "fixture must exercise attacks");
    assert!(first.events.damage > 0, "fixture must exercise hits");
    assert!(first.events.deaths > 0, "fixture must exercise deaths");
    eprintln!(
        "players={PLAYERS} ticks={TICKS} shots={} damage={} deaths={} respawns={} final_hash={} timeline_hash={} generate_ms={} repeat_ms={} replay_ms={} encoded_input_bytes={} proof=none network=none ledger=none",
        first.events.shots,
        first.events.damage,
        first.events.deaths,
        first.events.respawns,
        hex(&first.final_hash),
        hex(&first.timeline_hash),
        first.elapsed.as_millis(),
        repeated.elapsed.as_millis(),
        replayed.elapsed.as_millis(),
        first.encoded_inputs.len() * PLAYERS * 8,
    );
}
