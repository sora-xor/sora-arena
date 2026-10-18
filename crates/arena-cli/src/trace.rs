//! Stream or compare a complete witness for an explicitly named research journal.
use std::{
    collections::BTreeMap,
    fs::{self, File, OpenOptions},
    io::{BufReader, BufWriter},
    path::PathBuf,
};

use arena_core::{
    MAX_PLAYERS, MAX_TICKS,
    execution_trace::{verify_trace, write_trace},
    recovery::{Receipt, inspect_prefix},
};

use crate::script;

pub const USAGE: &str = "trace --journal PATH --receipt-records N --receipt-hash HEX --players N --ticks N --session N (--output PATH | --verify PATH) (research witness only)";

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

pub fn run(args: impl Iterator<Item = String>) -> Result<(), Box<dyn std::error::Error>> {
    let mut options = BTreeMap::new();
    let mut args = args;
    while let Some(key) = args.next() {
        if ![
            "--journal",
            "--receipt-records",
            "--receipt-hash",
            "--players",
            "--ticks",
            "--session",
            "--output",
            "--verify",
        ]
        .contains(&key.as_str())
        {
            return Err(format!("unknown trace option: {key}").into());
        }
        let value = args.next().ok_or_else(|| format!("{key} needs a value"))?;
        if options.insert(key.clone(), value).is_some() {
            return Err(format!("duplicate trace option: {key}").into());
        }
    }
    let required = |key: &str| -> Result<&str, String> {
        options
            .get(key)
            .map(String::as_str)
            .ok_or_else(|| format!("{key} is required"))
    };
    let players: usize = required("--players")?.parse()?;
    let ticks: u32 = required("--ticks")?.parse()?;
    let session_number: u64 = required("--session")?.parse()?;
    if !(2..=MAX_PLAYERS).contains(&players) || ticks == 0 || ticks > MAX_TICKS {
        return Err("trace players or ticks outside research match bounds".into());
    }
    let hash = required("--receipt-hash")?;
    if hash.len() != 64
        || !hash
            .bytes()
            .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
    {
        return Err("--receipt-hash must be exactly 64 lowercase hexadecimal characters".into());
    }
    let mut digest = [0; 32];
    for (byte, text) in digest.iter_mut().zip(hash.as_bytes().chunks_exact(2)) {
        *byte = u8::from_str_radix(std::str::from_utf8(text)?, 16)?;
    }
    let minimum = Receipt {
        records: required("--receipt-records")?.parse()?,
        digest,
    };
    let output = options.get("--output").map(PathBuf::from);
    let verify = options.get("--verify").map(PathBuf::from);
    if output.is_some() == verify.is_some() {
        return Err("choose exactly one of --output and --verify".into());
    }
    let keys = script::keys(session_number, players);
    let config = script::config(ticks);
    let participants = script::participants(players);
    let prefix = inspect_prefix(
        &PathBuf::from(required("--journal")?),
        script::context(session_number, &keys, ticks),
        config.clone(),
        &participants,
        minimum,
    )?;
    if prefix.failure().is_some() || prefix.resolution_fault().is_some() {
        return Err("journal is incomplete, corrupt or cannot execute; no trace exported".into());
    }
    let summary = if let Some(path) = verify {
        verify_trace(
            config,
            &participants,
            prefix.session(),
            BufReader::new(File::open(path)?),
        )?
    } else {
        let path = output.expect("exactly one mode checked");
        // create_new never replaces user output, a journal or a symlink. Remove
        // only this newly created incomplete artifact if streaming fails.
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)?;
        let result = write_trace(
            config,
            &participants,
            prefix.session(),
            BufWriter::new(&mut file),
        )
        .and_then(|summary| {
            file.sync_all()?;
            Ok(summary)
        });
        match result {
            Ok(summary) => summary,
            Err(error) => {
                drop(file);
                fs::remove_file(&path)?;
                return Err(error.into());
            }
        }
    };
    println!(
        "trace ticks={} evidence_tick={} certified_tick={} pending={} completed={} phase={:?} bytes={} digest={} state={} history={}",
        summary.tick,
        summary.evidence_tick,
        summary.certified_tick,
        summary.pending_frontiers,
        summary.completed,
        summary.phase,
        summary.encoded_bytes,
        hex(&summary.trace_digest),
        hex(&summary.state_hash),
        hex(&summary.history_root),
    );
    println!(
        "scope=scripted_research_journal execution_proof=false ledger_selected=false ledger_transactions=0"
    );
    Ok(())
}
