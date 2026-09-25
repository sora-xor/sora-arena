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
// Pinned under sora-arena-first-release-7 with the final v2 state layout, on
// the authored Nyaagyu Estate with its team spawns and a script rewritten for
// its walls. The first-release-6 script on first-release-6 map data replays
// identically through the new kernel apart from hashes and objectives.
const EXPECTED_FINAL_HASH: &str =
    "5d000cfd7b28526bfa55fe0050c0d47872fa6c9831b189f6ea5c602d0af019ea";
const EXPECTED_TIMELINE_HASH: &str =
    "409dd59b3d6016dd35c026d0d6608e9f55f56512866f22d1cfae1c5d9b1b9c9e";

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
    // Each player strafes from its Nyaagyu Estate team spawn onto the mid lane
    // (y = 0) through the gatehouse's central doorway, then both teams advance
    // along it with held Arc-carbine fire and back off at the end of every
    // 900-tick cycle. This is a fixed script, not a bot policy.
    let phase = tick % 900;
    std::array::from_fn(|slot| {
        let team = slot % 2;
        // Estate team spawns by rank: team 0 at y = -5000 + 2000r facing +x,
        // team 1 at y = 5000 - 2000r facing -x. Each player's right is +y for
        // team 0 and -y for team 1, and strafing moves exactly 80 mm a tick.
        let rank = (slot / 2) as i32;
        let spawn_y = if team == 0 {
            -5000 + 2000 * rank
        } else {
            5000 - 2000 * rank
        };
        let right = if team == 0 { 1 } else { -1 };
        Input {
            buttons: FIRE,
            move_x: if phase < 100 {
                0
            } else if phase < 700 || (phase / 50).is_multiple_of(2) {
                127
            } else {
                -127
            },
            move_y: if phase < spawn_y.unsigned_abs() / 80 {
                (-spawn_y.signum() * right * 127) as i16
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
    guarded: u32,
    healed: u32,
    abilities: u32,
    entities: u32,
    environmental: u32,
    objectives: u32,
    winners: u32,
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
                Event::Guarded { .. } => events.guarded += 1,
                Event::Healed { .. } => events.healed += 1,
                Event::AbilityUsed { .. } | Event::Marked { .. } | Event::Riposte { .. } => {
                    events.abilities += 1
                }
                Event::EntitySpawned { .. }
                | Event::EntityDamaged { .. }
                | Event::EntityRepaired { .. }
                | Event::EntityDestroyed { .. } => events.entities += 1,
                Event::EnvironmentalDamage { .. } => events.environmental += 1,
                Event::ObjectiveCaptured { .. }
                | Event::OvertimeStarted
                | Event::CheckpointReached { .. } => events.objectives += 1,
                Event::MatchWinner { .. } => events.winners += 1,
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
