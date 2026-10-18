//! Opt-in CPU serialization probe: 12 players, 18,000 signed two-tick batches.
//!
//! Run with `cargo run --release --locked -p arena-core --example trace_capacity -- NEW_FILE`.
//! The output must not exist. Public deterministic seeds are research fixtures,
//! never wallet keys. This measures local signed-history replay and full-state
//! trace I/O, not STARK generation, ledger settlement, network play or 60 Hz.

use std::{
    error::Error,
    fs::{File, OpenOptions},
    io::{self, BufReader, BufWriter, Read},
    path::PathBuf,
    time::Instant,
};

use arena_core::{
    MAX_PLAYERS, MAX_TICKS,
    execution_trace::{verify_trace, write_trace},
    protocol::{BATCH_TICKS, CommitmentSet, Context, MAX_BATCHES, Reveal, sign_commitment_set},
    rollback::RollbackSession,
    simulation::{ABILITY, Config, FIRE, Input, JUMP, Mode, Participant, RELOAD},
};
use ed25519_dalek::SigningKey;
use sha2::{Digest, Sha256};

const PLAYERS: usize = 12;
const TICKS: u32 = 36_000;
const BATCHES: usize = 18_000;

#[derive(Clone, Copy)]
enum Scene {
    SpawnActivity,
    Idle,
}
impl Scene {
    fn label(self) -> &'static str {
        match self {
            Self::SpawnActivity => {
                "outward fire, jump, reload and abilities at team spawns; no movement axes"
            }
            Self::Idle => "idle controls at team spawns; no attacks, jumps, abilities or movement",
        }
    }
    fn input(self, tick: u32, slot: usize) -> Input {
        if matches!(self, Self::Idle) {
            return Input::default();
        }
        let buttons = (u32::from(tick % 60 < 20) * FIRE)
            | (u32::from(tick.is_multiple_of(90)) * JUMP)
            | (u32::from(tick.is_multiple_of(180)) * ABILITY)
            | (u32::from(tick % 120 == 90) * RELOAD);
        Input {
            buttons,
            // Face away from the objective; the Shinobi's dash also points outwards.
            yaw: if slot < 6 { 32_768 } else { 0 },
            ..Input::default()
        }
    }
}

struct Prepared {
    session: RollbackSession,
    max_projectiles: usize,
    max_entities: usize,
}

fn admission() -> (Config, Vec<Participant>, Vec<SigningKey>, Context) {
    let config = Config {
        mode: Mode::Control,
        map: 0,
        max_ticks: TICKS,
        base_bond: 0,
        offline: true,
    };
    let participants = (0..PLAYERS)
        .map(|slot| Participant {
            team: (slot / 6) as u8,
            class: (slot % 6) as u8,
            // Each side fields every class; together they carry all 12 standard arms.
            weapon: (slot % 6 * 2 + slot / 6) as u8,
            bond: 0,
            special_entitled: false,
        })
        .collect::<Vec<_>>();
    let keys = (0..PLAYERS)
        .map(|slot| SigningKey::from_bytes(&[160 + slot as u8; 32]))
        .collect::<Vec<_>>();
    let context = Context {
        network: Sha256::digest(b"arena trace capacity public research network").into(),
        session: Sha256::digest(b"arena trace capacity public research session").into(),
        manifest: Sha256::digest(b"arena trace capacity 12 slots 36000 ticks zero bond").into(),
        roster: keys
            .iter()
            .map(|key| key.verifying_key().to_bytes())
            .collect(),
    };
    (config, participants, keys, context)
}

fn prepare(
    config: &Config,
    participants: &[Participant],
    keys: &[SigningKey],
    context: &Context,
    scene: Scene,
) -> Result<Option<Prepared>, Box<dyn Error>> {
    let mut session = RollbackSession::new(context.clone(), config.clone(), participants)?;
    let mut max_projectiles = 0;
    let mut max_entities = 0;
    for batch in 0..BATCHES {
        let log = session.evidence();
        let start_tick = log.certified_tick;
        let reveals = (0..PLAYERS)
            .map(|slot| {
                let mut salt = Sha256::new();
                salt.update(b"arena trace capacity public research salt");
                salt.update(start_tick.to_le_bytes());
                salt.update((slot as u32).to_le_bytes());
                Reveal {
                    start_tick,
                    slot,
                    salt: salt.finalize().into(),
                    inputs: (0..BATCH_TICKS)
                        .map(|offset| scene.input(start_tick + offset as u32, slot))
                        .collect(),
                }
            })
            .collect::<Vec<_>>();
        let set = CommitmentSet {
            epoch: log.epoch,
            start_tick,
            parent: log.commitment_head,
            commitments: reveals
                .iter()
                .map(|reveal| reveal.commitment(context, log.epoch))
                .collect::<Result<Vec<_>, _>>()?,
        };
        let signatures = keys
            .iter()
            .enumerate()
            .map(|(slot, key)| sign_commitment_set(context, &set, slot, key))
            .collect::<Result<Vec<_>, _>>()?;
        session.certify(set, signatures)?;
        session.open(reveals)?;
        session.advance()?;
        max_projectiles = max_projectiles.max(session.confirmed().projectiles.len());
        max_entities = max_entities.max(session.confirmed().entities.len());
        if session.confirmed().terminal && session.confirmed().tick != TICKS {
            eprintln!(
                "scene ended early at tick {}; full-size probe not satisfied",
                session.confirmed().tick
            );
            return Ok(None);
        }
        if (batch + 1).is_multiple_of(1800) {
            eprintln!("prepared {} / {BATCHES} signed batches", batch + 1);
        }
    }
    if session.confirmed().tick != TICKS
        || !session.confirmed().terminal
        || session.evidence().batches.len() != BATCHES
        || session.evidence().next_tick != TICKS
        || session.evidence().certified_tick != TICKS
        || !session.evidence().pending.is_empty()
    {
        return Err(io::Error::other("full 12-player/36000-tick target was not completed").into());
    }
    session.finish_local()?;
    Ok(Some(Prepared {
        session,
        max_projectiles,
        max_entities,
    }))
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn main() -> Result<(), Box<dyn Error>> {
    let mut args = std::env::args_os().skip(1);
    let path = args
        .next()
        .ok_or("usage: trace_capacity NEW_TRACE_FILE (opt-in research only)")?;
    if path == "--help" || path == "-h" {
        println!(
            "usage: trace_capacity NEW_TRACE_FILE\nSequential CPU probe: 12 players, 36000 ticks, 18000 signed batches.\nPublic fixture keys, offline zero bonds. Refuses overwrite. No STARK, network, settlement or 60 Hz claim."
        );
        return Ok(());
    }
    if args.next().is_some() {
        return Err("exactly one new output path is required".into());
    }
    if MAX_PLAYERS != PLAYERS || MAX_TICKS != TICKS || MAX_BATCHES != BATCHES || BATCH_TICKS != 2 {
        return Err(
            "compiled protocol bounds differ from the fixed full-size research target".into(),
        );
    }
    let path = PathBuf::from(path);
    // Claim a fresh path before doing expensive work. Failures may leave an
    // incomplete file; no consumer may treat it as a verified trace.
    let output = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&path)?;
    let total_started = Instant::now();
    let (config, participants, keys, context) = admission();
    let preparation_started = Instant::now();
    let mut scene = Scene::SpawnActivity;
    eprintln!("research scene: {}", scene.label());
    let prepared = match prepare(&config, &participants, &keys, &context, scene)? {
        Some(prepared) => prepared,
        None => {
            scene = Scene::Idle;
            eprintln!(
                "retrying the unchanged full target with explicit idle load: {}",
                scene.label()
            );
            prepare(&config, &participants, &keys, &context, scene)?
                .ok_or("idle scene also ended early; full-size gate failed")?
        }
    };
    let preparation_ms = preparation_started.elapsed().as_millis();
    let write_started = Instant::now();
    eprintln!("streaming full-state trace with fresh certificate and replay verification");
    let summary = write_trace(
        config.clone(),
        &participants,
        &prepared.session,
        BufWriter::with_capacity(1024 * 1024, output),
    )?;
    let write_ms = write_started.elapsed().as_millis();
    let verify_started = Instant::now();
    eprintln!("replaying and comparing every trace byte, including EOF");
    let verified = verify_trace(
        config,
        &participants,
        &prepared.session,
        BufReader::with_capacity(1024 * 1024, File::open(&path)?),
    )?;
    let verify_ms = verify_started.elapsed().as_millis();
    if verified != summary
        || summary.tick != TICKS
        || summary.evidence_tick != TICKS
        || summary.certified_tick != TICKS
        || summary.pending_frontiers != 0
        || !summary.completed
        || std::fs::metadata(&path)?.len() != summary.encoded_bytes
    {
        return Err("full-size trace verification or file size differs".into());
    }
    let mut file = BufReader::with_capacity(1024 * 1024, File::open(&path)?);
    let mut digest = Sha256::new();
    let mut buffer = [0; 64 * 1024];
    loop {
        let count = file.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        digest.update(&buffer[..count]);
    }
    let file_hash = digest.finalize();
    println!(
        "scope=local signed-history full-state serialization research; not STARK, ledger settlement, network or 60-Hz qualification"
    );
    println!("scene={}", scene.label());
    println!(
        "players={PLAYERS} teams=6v6 classes=6 standard_weapons=12 ticks={} batches={BATCHES} offline=true total_bond=0",
        summary.tick
    );
    println!(
        "prepare_ms={preparation_ms} write_replay_ms={write_ms} verify_replay_ms={verify_ms} total_ms={}",
        total_started.elapsed().as_millis()
    );
    println!(
        "max_projectiles_at_batch_boundaries={} max_entities_at_batch_boundaries={} deaths={}",
        prepared.max_projectiles,
        prepared.max_entities,
        prepared
            .session
            .confirmed()
            .accounts
            .iter()
            .map(|account| u64::from(account.deaths))
            .sum::<u64>()
    );
    println!(
        "encoded_bytes={} trace_digest={} artifact_sha256={}",
        summary.encoded_bytes,
        hex(&summary.trace_digest),
        hex(&file_hash)
    );
    println!(
        "state_hash={} history_root={}",
        hex(&summary.state_hash),
        hex(&summary.history_root)
    );
    println!("artifact={}", path.display());
    Ok(())
}
