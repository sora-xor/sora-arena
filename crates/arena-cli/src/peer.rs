//! `arena peer`: one headless, scripted peer of a research mesh match. Each
//! peer is its own process with one UDP socket, one durable journal and one
//! receipt log. Offline, zero bond and research keys only; see
//! docs/p2p-localhost.md.
use std::{
    fs,
    net::{SocketAddr, UdpSocket},
    ops::ControlFlow,
    path::PathBuf,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

use arena_core::{
    MAX_PLAYERS, MAX_TICKS,
    mesh_transport::{
        HeadlessReport, Impairment, MeshAdmission, MeshError, MeshPeer, NetworkScope, Pace,
        ReceiptLog, run_headless,
    },
    protocol::BATCH_TICKS,
    recovery::DurableSession,
};

use crate::script;

pub const USAGE: &str = "peer --slot N --peers ADDR,ADDR,... --dir PATH [--ticks 7200] [--rate-hz 60] [--start-unix-ms MS] [--session N] [--restore] [--drop N] [--duplicate N] [--reorder N] [--corrupt N] [--impair-seed N] [--research-lan] [--progress TICKS] [--stall-seconds S] [--resolve-seconds S]";

struct Options {
    slot: usize,
    addresses: Vec<SocketAddr>,
    dir: PathBuf,
    ticks: u32,
    rate_hz: u32,
    start_unix_ms: Option<u64>,
    session: u64,
    restore: bool,
    impairment: Impairment,
    research_lan: bool,
    progress: u32,
    stall_seconds: u64,
    resolve_seconds: u64,
}

fn parse(args: impl Iterator<Item = String>) -> Result<Options, String> {
    let mut args = args;
    let mut slot = None;
    let mut addresses = None;
    let mut dir = None;
    let mut options = Options {
        slot: 0,
        addresses: Vec::new(),
        dir: PathBuf::new(),
        ticks: 7200,
        rate_hz: 60,
        start_unix_ms: None,
        session: 1,
        restore: false,
        impairment: Impairment::default(),
        research_lan: false,
        progress: 300,
        stall_seconds: 60,
        resolve_seconds: 60,
    };
    while let Some(flag) = args.next() {
        let mut value = || args.next().ok_or_else(|| format!("{flag} needs a value"));
        let number = |text: String| {
            text.parse::<u64>()
                .map_err(|_| format!("{flag} expects a number, not {text}"))
        };
        let per_mille = |text: String| -> Result<u16, String> {
            let rate = number(text)?;
            u16::try_from(rate)
                .ok()
                .filter(|rate| *rate <= 1000)
                .ok_or_else(|| format!("{flag} is per mille, at most 1000"))
        };
        match flag.as_str() {
            "--slot" => slot = Some(number(value()?)? as usize),
            "--peers" => {
                addresses = Some(
                    value()?
                        .split(',')
                        .map(|address| {
                            address
                                .parse::<SocketAddr>()
                                .map_err(|_| format!("invalid peer address {address}"))
                        })
                        .collect::<Result<Vec<_>, _>>()?,
                )
            }
            "--dir" => dir = Some(PathBuf::from(value()?)),
            "--ticks" => {
                options.ticks = u32::try_from(number(value()?)?)
                    .ok()
                    .filter(|ticks| {
                        *ticks > 0
                            && *ticks <= MAX_TICKS
                            && ticks.is_multiple_of(BATCH_TICKS as u32)
                    })
                    .ok_or("--ticks must be a positive even count up to 36000")?
            }
            "--rate-hz" => {
                options.rate_hz = u32::try_from(number(value()?)?)
                    .map_err(|_| "--rate-hz is too large".to_string())?
            }
            "--start-unix-ms" => options.start_unix_ms = Some(number(value()?)?),
            "--session" => options.session = number(value()?)?,
            "--restore" => options.restore = true,
            "--drop" => options.impairment.drop_per_mille = per_mille(value()?)?,
            "--duplicate" => options.impairment.duplicate_per_mille = per_mille(value()?)?,
            "--reorder" => options.impairment.reorder_per_mille = per_mille(value()?)?,
            "--corrupt" => options.impairment.corrupt_per_mille = per_mille(value()?)?,
            "--impair-seed" => options.impairment.seed = number(value()?)?,
            "--research-lan" => options.research_lan = true,
            "--progress" => {
                options.progress = u32::try_from(number(value()?)?)
                    .ok()
                    .filter(|every| *every > 0)
                    .ok_or("--progress must be positive")?
            }
            "--stall-seconds" => options.stall_seconds = number(value()?)?.max(1),
            "--resolve-seconds" => options.resolve_seconds = number(value()?)?.max(1),
            _ => return Err(format!("unknown peer option {flag}")),
        }
    }
    options.slot = slot.ok_or("--slot is required")?;
    options.addresses = addresses.ok_or("--peers is required")?;
    options.dir = dir.ok_or("--dir is required")?;
    if !(2..=MAX_PLAYERS).contains(&options.addresses.len())
        || options.slot >= options.addresses.len()
    {
        return Err(format!(
            "--peers lists 2 to {MAX_PLAYERS} addresses and --slot indexes one of them"
        ));
    }
    Ok(options)
}

/// The shared presentation start as a local instant.
fn start_instant(start_unix_ms: Option<u64>) -> Instant {
    let now = Instant::now();
    let Some(ms) = start_unix_ms else {
        return now;
    };
    let start = UNIX_EPOCH + Duration::from_millis(ms);
    match start.duration_since(SystemTime::now()) {
        Ok(ahead) => now + ahead,
        Err(behind) => now.checked_sub(behind.duration()).unwrap_or(now),
    }
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

pub fn run(args: impl Iterator<Item = String>) -> Result<(), Box<dyn std::error::Error>> {
    let options = parse(args)?;
    let slot = options.slot;
    let players = options.addresses.len();
    let keys = script::keys(options.session, players);
    let context = script::context(options.session, &keys, options.ticks);
    let config = script::config(options.ticks);
    let participants = script::participants(players);
    fs::create_dir_all(&options.dir)?;
    let journal_path = options.dir.join(format!("peer-{slot}.journal"));
    let receipts_path = options.dir.join(format!("peer-{slot}.receipts"));
    let restoring = Instant::now();
    let (journal, receipts) = if options.restore {
        let receipts = ReceiptLog::open(&receipts_path)?;
        let journal = DurableSession::restore(
            &journal_path,
            context,
            config,
            &participants,
            receipts.latest(),
        )?;
        (journal, receipts)
    } else {
        let journal = DurableSession::create(&journal_path, context, config, &participants)?;
        let receipts = ReceiptLog::create(&receipts_path, journal.receipt())?;
        (journal, receipts)
    };
    let admission = MeshAdmission {
        socket: UdpSocket::bind(options.addresses[slot])?,
        addresses: options.addresses.clone(),
        local_slot: slot,
        identity: keys[slot].clone(),
        journal,
        receipts,
        scope: if options.research_lan {
            NetworkScope::ResearchLan
        } else {
            NetworkScope::Loopback
        },
        impairment: options.impairment,
    };
    let peer = if options.restore {
        let peer = MeshPeer::resume(admission)?;
        let session = peer.session();
        println!(
            "restored slot={slot} restore_ms={} records={} confirmed={} certified={}",
            restoring.elapsed().as_millis(),
            peer.journal().receipt().records,
            session.confirmed().tick,
            session.evidence().certified_tick
        );
        peer
    } else {
        MeshPeer::start(admission)?
    };
    println!("ready slot={slot} address={}", options.addresses[slot]);
    let pace = Pace {
        rate_hz: (options.rate_hz > 0).then_some(options.rate_hz),
        start: start_instant(options.start_unix_ms),
        stall_limit: Duration::from_secs(options.stall_seconds),
        resolve_limit: Duration::from_secs(options.resolve_seconds),
        linger: Duration::from_millis(2_000),
    };
    let every = options.progress;
    let result = run_headless(
        peer,
        pace,
        |tick| script::control(tick, slot),
        |peer, tick| {
            if (tick + 1).is_multiple_of(every) {
                let session = peer.session();
                println!(
                    "progress slot={slot} presented={} confirmed={} certified={}",
                    tick + 1,
                    session.confirmed().tick,
                    session.evidence().certified_tick
                );
            }
            ControlFlow::Continue(())
        },
    );
    if let Err(MeshError::Unresolved {
        confirmed, pending, ..
    }) = &result
    {
        // Combat stopped and the journal keeps the evidence; only a
        // consensus deadline can close what is still pending.
        println!("unresolved slot={slot} confirmed={confirmed} pending={pending}");
    }
    println!("{}", result_line(slot, &result?));
    Ok(())
}

fn result_line(slot: usize, report: &HeadlessReport) -> String {
    let outcome = &report.outcome;
    let checkpoint = report
        .checkpoint
        .as_ref()
        .map(|checkpoint| &checkpoint.checkpoint);
    let none = || String::from("none");
    let presentation = &report.presentation;
    let mesh = &report.mesh;
    let fields = [
        ("state_hash", hex(&outcome.state_hash)),
        ("history_root", hex(&outcome.history_root)),
        ("tick", outcome.tick.to_string()),
        ("evidence_tick", outcome.evidence_tick.to_string()),
        ("completed", outcome.completed.to_string()),
        ("deadline_frontiers", outcome.deadline_frontiers.to_string()),
        (
            "checkpoint_tick",
            checkpoint.map_or_else(none, |checkpoint| checkpoint.tick.to_string()),
        ),
        (
            "checkpoint_state",
            checkpoint.map_or_else(none, |checkpoint| hex(&checkpoint.state_hash)),
        ),
        (
            "checkpoint_root",
            checkpoint.map_or_else(none, |checkpoint| hex(&checkpoint.history_root)),
        ),
        ("records", report.receipt.records.to_string()),
        ("unacknowledged", report.unacknowledged.to_string()),
        ("elapsed_ms", report.elapsed.as_millis().to_string()),
        ("presented", presentation.presented.to_string()),
        ("late_ticks", presentation.late_ticks.to_string()),
        ("max_late_ms", presentation.max_late.as_millis().to_string()),
        ("lag_mean", format!("{:.2}", presentation.lag_mean())),
        ("lag_p50", presentation.lag_quantile(500).to_string()),
        ("lag_p99", presentation.lag_quantile(990).to_string()),
        ("lag_max", presentation.lag_max().to_string()),
        ("datagrams_sent", mesh.datagrams_sent.to_string()),
        ("datagrams_received", mesh.datagrams_received.to_string()),
        ("bytes_sent", mesh.bytes_sent.to_string()),
        ("bytes_received", mesh.bytes_received.to_string()),
        ("send_errors", mesh.send_errors.to_string()),
        ("frames_sent", mesh.frames_sent.to_string()),
        ("frames_received", mesh.frames_received.to_string()),
        ("retransmitted", mesh.retransmitted.to_string()),
        ("timeouts", mesh.timeouts.to_string()),
        ("fast_retransmits", mesh.fast_retransmits.to_string()),
        ("probes", mesh.probes.to_string()),
        ("acks_sent", mesh.acks_sent.to_string()),
        ("acks_received", mesh.acks_received.to_string()),
        ("duplicates", mesh.duplicates.to_string()),
        ("out_of_order", mesh.out_of_order.to_string()),
        ("rejected", mesh.rejected.to_string()),
        ("unready", mesh.unready.to_string()),
        ("backpressured", mesh.backpressured.to_string()),
        ("offers_sent", mesh.offers_sent.to_string()),
        ("handshakes", mesh.handshakes.to_string()),
        ("replaced_channels", mesh.replaced_channels.to_string()),
        ("early_openings", mesh.early_openings.to_string()),
        ("deferred", mesh.deferred.to_string()),
        (
            "relayed_certificates",
            mesh.relayed_certificates.to_string(),
        ),
        (
            "checkpoints_retained",
            mesh.checkpoints_retained.to_string(),
        ),
        ("checkpoints_missed", mesh.checkpoints_missed.to_string()),
        ("journal_syncs", mesh.journal_syncs.to_string()),
        ("journal_sync_us", mesh.journal_sync_micros.to_string()),
        (
            "journal_sync_max_us",
            mesh.journal_sync_max_micros.to_string(),
        ),
        ("receipt_syncs", mesh.receipt_syncs.to_string()),
        ("receipt_sync_us", mesh.receipt_sync_micros.to_string()),
        (
            "receipt_sync_max_us",
            mesh.receipt_sync_max_micros.to_string(),
        ),
        ("records_synced", mesh.records_synced.to_string()),
        ("bytes_synced", mesh.bytes_synced.to_string()),
        ("impaired_dropped", mesh.impaired_dropped.to_string()),
        ("impaired_duplicated", mesh.impaired_duplicated.to_string()),
        ("impaired_reordered", mesh.impaired_reordered.to_string()),
        ("impaired_corrupted", mesh.impaired_corrupted.to_string()),
    ];
    let mut line = format!("result slot={slot}");
    for (name, value) in fields {
        line.push(' ');
        line.push_str(name);
        line.push('=');
        line.push_str(&value);
    }
    line
}
