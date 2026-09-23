//! Local durability/load diagnostic with public fixture keys and no networking.
//! No proof is generated, no wallet is accessed, and no XOR can move.
use arena_core::{
    protocol::{CommitmentSet, Context, Reveal, input_commitment, sign_commitment_set},
    recovery::DurableSession,
    simulation::{Config, Input, Mode, Participant},
};
use ed25519_dalek::SigningKey;
use std::{path::PathBuf, time::Instant};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let path = PathBuf::from(args.next().ok_or("provide a NEW output journal path")?);
    let ticks: u32 = args
        .next()
        .ok_or("provide ticks (even, 2..36000)")?
        .parse()?;
    let players: usize = args.next().ok_or("provide player count (2..12)")?.parse()?;
    if !(2..=36_000).contains(&ticks)
        || !ticks.is_multiple_of(2)
        || !(2..=12).contains(&players)
        || args.next().is_some()
    {
        return Err("invalid diagnostic bounds".into());
    }
    let keys = (0..players)
        .map(|slot| SigningKey::from_bytes(&[slot as u8 + 1; 32]))
        .collect::<Vec<_>>();
    let context = Context {
        network: [0xa1; 32],
        session: [0xa2; 32],
        manifest: [0xa3; 32],
        roster: keys
            .iter()
            .map(|key| key.verifying_key().to_bytes())
            .collect(),
    };
    let config = Config {
        mode: Mode::Control,
        map: 0,
        max_ticks: ticks,
        base_bond: 1000,
        offline: false,
    };
    let roster = (0..players)
        .map(|slot| Participant {
            team: (slot % 2) as u8,
            class: (slot % 6) as u8,
            weapon: ((slot % 6) * 2 + 1) as u8,
            bond: 1000,
            special_entitled: false,
        })
        .collect::<Vec<_>>();
    let mut journal = DurableSession::create(&path, context.clone(), config.clone(), &roster)?;
    let start = Instant::now();
    for _ in 0..ticks / 2 {
        let log = journal.session().evidence();
        let reveals = (0..players)
            .map(|slot| Reveal {
                slot,
                inputs: vec![Input::default(); 2],
                salt: [slot as u8 + 42; 32],
            })
            .collect::<Vec<_>>();
        let set = CommitmentSet {
            epoch: log.epoch,
            start_tick: log.next_tick,
            parent: log.root,
            commitments: reveals
                .iter()
                .map(|r| {
                    input_commitment(
                        &context,
                        log.epoch,
                        log.next_tick,
                        log.root,
                        r.slot,
                        &r.inputs,
                        r.salt,
                    )
                })
                .collect::<Result<_, _>>()?,
        };
        let signatures = keys
            .iter()
            .enumerate()
            .map(|(slot, key)| sign_commitment_set(&context, &set, slot, key))
            .collect::<Result<_, _>>()?;
        journal.certify(set, signatures)?;
        journal.reveal_many(reveals)?;
    }
    let checkpoint = journal.session().checkpoint();
    let signatures = keys
        .iter()
        .enumerate()
        .map(|(slot, key)| checkpoint.sign(&context, slot, key))
        .collect::<Result<_, _>>()?;
    journal.checkpoint(checkpoint, signatures)?;
    let receipt = journal.finish()?;
    let live_ms = start.elapsed().as_millis();
    let expected = journal.session().confirmed().state_hash();
    drop(journal);
    let replay_start = Instant::now();
    let recovered = DurableSession::restore(&path, context, config, &roster, receipt)?;
    if recovered.session().confirmed().state_hash() != expected {
        return Err("recovery diverged".into());
    }
    println!(
        "players={players} ticks={ticks} records={} bytes={} append_ms={live_ms} restore_ms={} replay_identical=true",
        receipt.records,
        std::fs::metadata(&path)?.len(),
        replay_start.elapsed().as_millis()
    );
    println!(
        "controls=idle fixture_keys=public execution_proof=none chain_transactions=0 qualification=false"
    );
    Ok(())
}
