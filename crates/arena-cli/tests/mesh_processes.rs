//! Multi-process loopback research: every peer of a match runs as its own
//! `arena-cli peer` OS process with its own UDP socket, durable journal and
//! receipt log, and the harness only starts, kills and restarts processes and
//! reads their output. Research only: offline, zero bond, keys derived from a
//! public session number. Not production networking, consensus or a proof.
// The harness keys nothing itself; it only replays the script.
#[allow(dead_code)]
#[path = "../src/script.rs"]
mod script;

use arena_core::{
    mesh_transport::ReceiptLog,
    protocol::{BATCH_TICKS, MAX_ASSEMBLY_FRONTIERS, MAX_OUTSTANDING_FRONTIERS, Phase},
    recovery::DurableSession,
    simulation::World,
};
use std::{
    collections::HashMap,
    fs::{self, File},
    io::{BufRead, BufReader, Write},
    net::UdpSocket,
    path::PathBuf,
    process::{Child, ChildStdin, Command, Stdio},
    sync::{
        atomic::{AtomicU64, Ordering},
        mpsc,
    },
    thread,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

/// The two-minute 4v4 script's final kernel state, pinned in arena-core's
/// eight_peer_two_minute_udp_research.rs and eight_player_two_minute_research.rs.
const PINNED_TWO_MINUTE_HASH: &str =
    "5d000cfd7b28526bfa55fe0050c0d47872fa6c9831b189f6ea5c602d0af019ea";

/// The public session number every harness peer derives its keys from.
const SESSION: u64 = 20_260_925;

/// The dropped peer opens none of its commitments from this tick on, after
/// the checkpoint at 120.
const WITHHELD: u32 = 140;
/// Every peer then certifies one full pipeline of frontiers past it...
const CERTIFIED: u32 = WITHHELD + (MAX_OUTSTANDING_FRONTIERS * BATCH_TICKS) as u32;
/// ...and commits one assembly window past that.
const COMMITTED: u32 = CERTIFIED + (MAX_ASSEMBLY_FRONTIERS * BATCH_TICKS) as u32;

static NEXT_ROOT: AtomicU64 = AtomicU64::new(0);

type Fields = HashMap<String, String>;

struct Kill {
    slot: usize,
    /// Kill once a progress line shows at least this confirmed tick.
    at_confirmed: u32,
    down_for: Duration,
}

struct Scenario {
    name: &'static str,
    players: usize,
    ticks: u32,
    /// 0 presents as fast as the pipeline allows.
    rate_hz: u32,
    /// Drop, duplicate, reorder and corrupt, per mille, on every peer.
    impairment: [u16; 4],
    kill: Option<Kill>,
    progress: u32,
    /// `--stall-seconds` and `--resolve-seconds` of every peer.
    limits: (u64, u64),
    timeout: Duration,
    /// This slot opens none of its commitments from this tick on.
    withhold: Option<(usize, u32)>,
    /// Every peer holds its limits until the harness releases it.
    hold: bool,
}

struct Mesh {
    root: PathBuf,
    peers: String,
    start_unix_ms: u64,
    children: Vec<Option<Child>>,
    stdins: Vec<Option<ChildStdin>>,
    incarnations: Vec<u32>,
    sender: mpsc::Sender<(usize, String)>,
    lines: mpsc::Receiver<(usize, String)>,
    passed: bool,
}

impl Mesh {
    fn new(players: usize) -> Self {
        let root = std::env::temp_dir().join(format!(
            "sora-arena-mesh-processes-{}-{}",
            std::process::id(),
            NEXT_ROOT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        // Reserve distinct loopback ports; each peer process binds its own.
        let sockets = (0..players)
            .map(|_| UdpSocket::bind("127.0.0.1:0").unwrap())
            .collect::<Vec<_>>();
        let peers = sockets
            .iter()
            .map(|socket| socket.local_addr().unwrap().to_string())
            .collect::<Vec<_>>()
            .join(",");
        drop(sockets);
        let start_unix_ms = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_millis() as u64
            + 2_500;
        let (sender, lines) = mpsc::channel();
        Self {
            root,
            peers,
            start_unix_ms,
            children: (0..players).map(|_| None).collect(),
            stdins: (0..players).map(|_| None).collect(),
            incarnations: vec![0; players],
            sender,
            lines,
            passed: false,
        }
    }

    fn spawn(&mut self, scenario: &Scenario, slot: usize, restore: bool) {
        let incarnation = self.incarnations[slot];
        self.incarnations[slot] += 1;
        let [drop, duplicate, reorder, corrupt] = scenario.impairment;
        let mut command = Command::new(env!("CARGO_BIN_EXE_arena-cli"));
        command
            .arg("peer")
            .args(["--slot", &slot.to_string()])
            .args(["--peers", &self.peers])
            .arg("--dir")
            .arg(&self.root)
            .args(["--ticks", &scenario.ticks.to_string()])
            .args(["--rate-hz", &scenario.rate_hz.to_string()])
            .args(["--start-unix-ms", &self.start_unix_ms.to_string()])
            .args(["--session", &SESSION.to_string()])
            .args(["--drop", &drop.to_string()])
            .args(["--duplicate", &duplicate.to_string()])
            .args(["--reorder", &reorder.to_string()])
            .args(["--corrupt", &corrupt.to_string()])
            .args([
                "--impair-seed",
                &(slot as u64 * 1_000 + u64::from(incarnation)).to_string(),
            ])
            .args(["--progress", &scenario.progress.to_string()])
            .args(["--stall-seconds", &scenario.limits.0.to_string()])
            .args(["--resolve-seconds", &scenario.limits.1.to_string()]);
        if restore {
            command.arg("--restore");
        }
        if scenario.hold {
            command.arg("--hold");
        }
        if let Some((withholder, tick)) = scenario.withhold
            && withholder == slot
        {
            command.args(["--withhold-from", &tick.to_string()]);
        }
        let stderr =
            File::create(self.root.join(format!("stderr-{slot}-{incarnation}.txt"))).unwrap();
        let mut child = command
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::from(stderr))
            .spawn()
            .unwrap();
        self.stdins[slot] = child.stdin.take();
        let stdout = child.stdout.take().unwrap();
        let sender = self.sender.clone();
        thread::spawn(move || {
            for line in BufReader::new(stdout).lines() {
                let Ok(line) = line else { break };
                if sender.send((slot, line)).is_err() {
                    break;
                }
            }
        });
        self.children[slot] = Some(child);
    }

    /// Let a held peer's stall and resolve limits count. A peer that already
    /// left shows up in its exit status and stderr.
    fn release(&mut self, slot: usize) {
        if let Some(stdin) = self.stdins[slot].as_mut() {
            let _ = writeln!(stdin, "release");
        }
    }

    /// The journal a peer process left behind, restored as the harness
    /// admitted it.
    fn restore(&self, scenario: &Scenario, slot: usize) -> DurableSession {
        let keys = script::keys(SESSION, scenario.players);
        let latest = ReceiptLog::open(&self.root.join(format!("peer-{slot}.receipts")))
            .unwrap()
            .latest();
        DurableSession::restore(
            &self.root.join(format!("peer-{slot}.journal")),
            script::context(SESSION, &keys, scenario.ticks),
            script::config(scenario.ticks),
            &script::participants(scenario.players),
            latest,
        )
        .unwrap()
    }

    /// The next line from any peer, or a panic with every stderr.
    fn next_line(&self, name: &str, deadline: Instant) -> (usize, String) {
        let remaining = deadline.saturating_duration_since(Instant::now());
        self.lines
            .recv_timeout(remaining)
            .unwrap_or_else(|_| panic!("{name}: timed out waiting for peers\n{}", self.stderr()))
    }

    fn stderr(&self) -> String {
        let mut text = String::new();
        let mut paths = fs::read_dir(&self.root)
            .unwrap()
            .filter_map(|entry| entry.ok().map(|entry| entry.path()))
            .filter(|path| {
                path.file_name()
                    .and_then(|name| name.to_str())
                    .is_some_and(|name| name.starts_with("stderr-"))
            })
            .collect::<Vec<_>>();
        paths.sort();
        for path in paths {
            let contents = fs::read_to_string(&path).unwrap_or_default();
            if !contents.is_empty() {
                text.push_str(&format!("--- {}\n{contents}\n", path.display()));
            }
        }
        text
    }
}

impl Drop for Mesh {
    fn drop(&mut self) {
        for child in self.children.iter_mut().flatten() {
            let _ = child.kill();
            let _ = child.wait();
        }
        if self.passed {
            let _ = fs::remove_dir_all(&self.root);
        } else {
            eprintln!("kept mesh artifacts in {}", self.root.display());
        }
    }
}

fn fields(line: &str) -> Fields {
    line.split_whitespace()
        .skip(1)
        .filter_map(|pair| pair.split_once('='))
        .map(|(key, value)| (key.to_string(), value.to_string()))
        .collect()
}

fn number(fields: &Fields, key: &str) -> u64 {
    fields[key].parse().unwrap()
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn reference_hash(players: usize, ticks: u32) -> String {
    let mut world = World::new(script::config(ticks), &script::participants(players)).unwrap();
    while !world.terminal {
        let tick = world.tick;
        let controls = (0..players)
            .map(|slot| script::control(tick, slot))
            .collect::<Vec<_>>();
        world.step(&controls).unwrap();
    }
    assert_eq!(world.tick, ticks);
    hex(&world.state_hash())
}

/// Run one match to the end and return every final process's result.
fn run(scenario: Scenario) -> Vec<Fields> {
    let expected = reference_hash(scenario.players, scenario.ticks);
    let mut mesh = Mesh::new(scenario.players);
    for slot in 0..scenario.players {
        mesh.spawn(&scenario, slot, false);
    }
    let deadline = Instant::now() + scenario.timeout;
    let mut results: Vec<Option<Fields>> = vec![None; scenario.players];
    let mut killed = false;
    let mut restored = None;
    while results.iter().any(Option::is_none) {
        let remaining = deadline.saturating_duration_since(Instant::now());
        let Ok((slot, line)) = mesh.lines.recv_timeout(remaining) else {
            panic!(
                "{}: timed out waiting for results {:?}\n{}",
                scenario.name,
                results.iter().map(Option::is_some).collect::<Vec<_>>(),
                mesh.stderr()
            );
        };
        if line.starts_with("result ") {
            results[slot] = Some(fields(&line));
        } else if line.starts_with("restored ") {
            restored = Some(fields(&line));
        } else if line.starts_with("progress ")
            && let Some(kill) = &scenario.kill
            && !killed
            && slot == kill.slot
            && number(&fields(&line), "confirmed") >= u64::from(kill.at_confirmed)
        {
            // SIGKILL on Unix: no destructor, flush or goodbye runs.
            let mut child = mesh.children[slot].take().unwrap();
            child.kill().unwrap();
            let status = child.wait().unwrap();
            assert!(!status.success());
            killed = true;
            eprintln!(
                "{}: killed slot {slot} after {line}; restarting in {:?}",
                scenario.name, kill.down_for
            );
            thread::sleep(kill.down_for);
            mesh.spawn(&scenario, slot, true);
        }
    }
    for (slot, child) in mesh.children.iter_mut().enumerate() {
        let status = child.as_mut().unwrap().wait().unwrap();
        assert!(
            status.success(),
            "slot {slot} exited with {status}\n{}",
            mesh.stderr()
        );
    }
    let results = results.into_iter().map(Option::unwrap).collect::<Vec<_>>();
    if scenario.kill.is_some() {
        assert!(
            killed,
            "{}: the victim finished before it was killed",
            scenario.name
        );
        let restored = restored.expect("the restarted peer restored its journal");
        assert!(number(&restored, "confirmed") > 0);
        assert!(number(&restored, "records") > 0);
        eprintln!(
            "{}: restored slot {} in {} ms from {} records at confirmed tick {}",
            scenario.name,
            restored["slot"],
            restored["restore_ms"],
            restored["records"],
            restored["confirmed"]
        );
    }
    for (slot, result) in results.iter().enumerate() {
        assert_eq!(number(result, "slot"), slot as u64);
        assert_eq!(
            result["state_hash"], expected,
            "{}: slot {slot}",
            scenario.name
        );
        assert_eq!(result["history_root"], results[0]["history_root"]);
        assert_eq!(result["checkpoint_state"], expected);
        assert_eq!(result["checkpoint_root"], results[0]["history_root"]);
        assert_eq!(number(result, "tick"), u64::from(scenario.ticks));
        assert_eq!(number(result, "checkpoint_tick"), u64::from(scenario.ticks));
        assert_eq!(result["completed"], "true");
        assert_eq!(number(result, "deadline_frontiers"), 0);
    }
    summarize(&scenario, &results);
    mesh.passed = true;
    results
}

fn summarize(scenario: &Scenario, results: &[Fields]) {
    let total = |key: &str| {
        results
            .iter()
            .map(|result| number(result, key))
            .sum::<u64>()
    };
    let max = |key: &str| {
        results
            .iter()
            .map(|result| number(result, key))
            .max()
            .unwrap()
    };
    eprintln!(
        "{}: peers={} ticks={} rate_hz={} impairment={:?} state_hash={} history_root={}",
        scenario.name,
        scenario.players,
        scenario.ticks,
        scenario.rate_hz,
        scenario.impairment,
        results[0]["state_hash"],
        results[0]["history_root"]
    );
    for result in results {
        let syncs = number(result, "journal_syncs").max(1);
        eprintln!(
            "  slot={} elapsed_ms={} presented={} late_ticks={} max_late_ms={} lag_mean={} lag_p50={} lag_p99={} lag_max={} datagrams_sent={} datagrams_received={} bytes_sent={} frames_sent={} retransmitted={} fast_retransmits={} timeouts={} unacknowledged={} duplicates={} out_of_order={} rejected={} unready={} handshakes={} replaced={} journal_syncs={} journal_sync_mean_ms={:.2} journal_sync_max_ms={:.1} receipt_sync_mean_ms={:.2} receipt_sync_max_ms={:.1} records={} bytes_synced={} checkpoints={}/{} impaired={}/{}/{}/{}",
            result["slot"],
            result["elapsed_ms"],
            result["presented"],
            result["late_ticks"],
            result["max_late_ms"],
            result["lag_mean"],
            result["lag_p50"],
            result["lag_p99"],
            result["lag_max"],
            result["datagrams_sent"],
            result["datagrams_received"],
            result["bytes_sent"],
            result["frames_sent"],
            result["retransmitted"],
            result["fast_retransmits"],
            result["timeouts"],
            result["unacknowledged"],
            result["duplicates"],
            result["out_of_order"],
            result["rejected"],
            result["unready"],
            result["handshakes"],
            result["replaced_channels"],
            result["journal_syncs"],
            number(result, "journal_sync_us") as f64 / syncs as f64 / 1000.0,
            number(result, "journal_sync_max_us") as f64 / 1000.0,
            number(result, "receipt_sync_us") as f64 / syncs as f64 / 1000.0,
            number(result, "receipt_sync_max_us") as f64 / 1000.0,
            result["records"],
            result["bytes_synced"],
            result["checkpoints_retained"],
            result["checkpoints_missed"],
            result["impaired_dropped"],
            result["impaired_duplicated"],
            result["impaired_reordered"],
            result["impaired_corrupted"],
        );
    }
    eprintln!(
        "  total datagrams_sent={} bytes_sent={} retransmitted={} late_ticks={} max lag={} journal_syncs={} batches={}",
        total("datagrams_sent"),
        total("bytes_sent"),
        total("retransmitted"),
        total("late_ticks"),
        max("lag_max"),
        total("journal_syncs"),
        u64::from(scenario.ticks) / 2 * scenario.players as u64
    );
}

#[test]
fn four_processes_agree_after_a_killed_peer_restarts_under_impairment() {
    let results = run(Scenario {
        name: "smoke",
        players: 4,
        ticks: 360,
        rate_hz: 0,
        impairment: [20, 20, 20, 10],
        kill: Some(Kill {
            slot: 2,
            at_confirmed: 120,
            down_for: Duration::from_millis(300),
        }),
        progress: 30,
        limits: (90, 60),
        timeout: Duration::from_secs(240),
        withhold: None,
        hold: false,
    });
    let impaired = results
        .iter()
        .map(|result| {
            number(result, "impaired_dropped")
                + number(result, "impaired_duplicated")
                + number(result, "impaired_reordered")
                + number(result, "impaired_corrupted")
        })
        .sum::<u64>();
    assert!(impaired > 0);
    assert!(number(&results[2], "handshakes") >= 3);
}

#[test]
#[ignore = "two-minute, eight-process 60 Hz loopback run; use --release -- --ignored --nocapture"]
fn eight_processes_play_a_two_minute_match_to_the_pinned_kernel_hash() {
    assert_eq!(reference_hash(8, 7200), PINNED_TWO_MINUTE_HASH);
    run(Scenario {
        name: "baseline",
        players: 8,
        ticks: 7200,
        rate_hz: 60,
        impairment: [0; 4],
        kill: None,
        progress: 600,
        limits: (90, 60),
        timeout: Duration::from_secs(400),
        withhold: None,
        hold: false,
    });
}

#[test]
#[ignore = "two-minute, eight-process 60 Hz loopback run; use --release -- --ignored --nocapture"]
fn eight_processes_recover_a_peer_killed_and_restarted_mid_match() {
    let results = run(Scenario {
        name: "kill-restart",
        players: 8,
        ticks: 7200,
        rate_hz: 60,
        impairment: [0; 4],
        kill: Some(Kill {
            slot: 5,
            at_confirmed: 3600,
            down_for: Duration::from_secs(1),
        }),
        progress: 300,
        limits: (90, 60),
        timeout: Duration::from_secs(400),
        withhold: None,
        hold: false,
    });
    assert_eq!(results[0]["state_hash"], PINNED_TWO_MINUTE_HASH);
    for (slot, result) in results.iter().enumerate() {
        if slot != 5 {
            assert_eq!(number(result, "replaced_channels"), 1, "slot {slot}");
        }
    }
}

#[test]
#[ignore = "two-minute, eight-process 60 Hz loopback run; use --release -- --ignored --nocapture"]
fn eight_processes_agree_despite_loss_reordering_duplication_and_damage() {
    let results = run(Scenario {
        name: "impaired",
        players: 8,
        ticks: 7200,
        rate_hz: 60,
        impairment: [50, 50, 50, 10],
        kill: None,
        progress: 600,
        limits: (90, 60),
        timeout: Duration::from_secs(400),
        withhold: None,
        hold: false,
    });
    assert_eq!(results[0]["state_hash"], PINNED_TWO_MINUTE_HASH);
    for result in &results {
        assert!(number(result, "impaired_dropped") > 0);
        assert!(number(result, "impaired_duplicated") > 0);
        assert!(number(result, "impaired_reordered") > 0);
        assert!(number(result, "impaired_corrupted") > 0);
        assert!(number(result, "retransmitted") > 0);
    }
}

#[test]
#[ignore = "two-minute, twelve-process 6v6 60 Hz loopback run; use --release -- --ignored --nocapture"]
fn twelve_processes_play_a_two_minute_six_versus_six_match() {
    run(Scenario {
        name: "six-versus-six",
        players: 12,
        ticks: 7200,
        rate_hz: 60,
        impairment: [0; 4],
        kill: None,
        progress: 600,
        limits: (90, 60),
        timeout: Duration::from_secs(400),
        withhold: None,
        hold: false,
    });
}

#[test]
fn survivors_stop_combat_and_keep_the_evidence_when_a_peer_never_returns() {
    let scenario = Scenario {
        name: "dropout",
        players: 4,
        ticks: 360,
        rate_hz: 0,
        impairment: [0; 4],
        kill: None,
        progress: 30,
        limits: (2, 2),
        timeout: Duration::from_secs(120),
        // Slot 3 withholds its openings, so the evidence stops at a known
        // frontier however fast each process runs, and no peer's limits
        // count until the harness releases it.
        withhold: Some((3, WITHHELD)),
        hold: true,
    };
    let mut mesh = Mesh::new(scenario.players);
    for slot in 0..scenario.players {
        mesh.spawn(&scenario, slot, false);
    }
    let deadline = Instant::now() + scenario.timeout;
    // A peer reports `quiet` when every frame it sent is acknowledged. Once
    // each reported it at the frontier where slot 3's openings stop, with its
    // checkpoint at 120 synced, every frame that decides the survivors'
    // evidence has arrived: nothing any peer sends later can change it.
    let mut settled = [false; 4];
    while !settled.iter().all(|settled| *settled) {
        let (slot, line) = mesh.next_line(scenario.name, deadline);
        if line.starts_with("quiet ") {
            let quiet = fields(&line);
            settled[slot] |= number(&quiet, "confirmed") == u64::from(WITHHELD)
                && number(&quiet, "certified") == u64::from(CERTIFIED)
                && number(&quiet, "next_commit") == u64::from(COMMITTED)
                && quiet["checkpoint"] == "120"
                && quiet["records"] == quiet["durable"];
        }
    }
    // Slot 3 is SIGKILLed and never returns; only now do the survivors'
    // limits count, so a loaded machine cannot stop combat before the
    // dropout.
    let mut child = mesh.children[3].take().unwrap();
    child.kill().unwrap();
    assert!(!child.wait().unwrap().success());
    eprintln!("{}: killed slot 3 once every peer settled", scenario.name);
    for slot in 0..3 {
        mesh.release(slot);
    }
    let mut ends: Vec<Option<(String, Fields)>> = vec![None; 3];
    while ends.iter().any(Option::is_none) {
        let (slot, line) = mesh.next_line(scenario.name, deadline);
        let kind = line
            .split_whitespace()
            .next()
            .unwrap_or_default()
            .to_string();
        if slot < 3 && (kind == "unresolved" || kind == "result") {
            ends[slot] = Some((kind, fields(&line)));
        }
    }
    for (slot, end) in ends.iter().enumerate() {
        let (kind, end) = end.as_ref().unwrap();
        let status = mesh.children[slot].as_mut().unwrap().wait().unwrap();
        assert_eq!(kind, "unresolved", "slot {slot}\n{}", mesh.stderr());
        assert!(!status.success());
        let journal = mesh.restore(&scenario, slot);
        let session = journal.session();
        let evidence = session.evidence();
        // Combat stopped where slot 3's openings end. The journal keeps the
        // last certified checkpoint, every pending frontier and every
        // opening, and every survivor holds the same certified frontiers.
        assert_eq!(evidence.phase, Phase::Resolving);
        assert!(!session.confirmed().terminal);
        assert_eq!(session.confirmed().tick, WITHHELD);
        assert_eq!(number(end, "confirmed"), u64::from(WITHHELD));
        assert_eq!(
            session
                .last_checkpoint()
                .map(|checkpoint| checkpoint.checkpoint.tick),
            Some(120)
        );
        assert_eq!(evidence.certified_tick, CERTIFIED);
        assert_eq!(evidence.pending.len(), MAX_OUTSTANDING_FRONTIERS);
        assert_eq!(number(end, "pending"), evidence.pending.len() as u64);
        for frontier in &evidence.pending {
            // Only the dropped peer's opening is missing; a consensus
            // deadline must forfeit it.
            let opened = frontier
                .openings
                .iter()
                .map(Option::is_some)
                .collect::<Vec<_>>();
            assert_eq!(opened, [true, true, true, false], "slot {slot}");
        }
        eprintln!(
            "{}: slot {slot} {kind} phase={:?} confirmed={} certified={} pending={} records={}",
            scenario.name,
            evidence.phase,
            session.confirmed().tick,
            evidence.certified_tick,
            evidence.pending.len(),
            journal.receipt().records
        );
    }

    // A survivor restarted from its journal stays stopped: it journals
    // nothing new, so it neither commits nor endorses.
    let records = mesh.restore(&scenario, 0).receipt().records;
    mesh.spawn(&scenario, 0, true);
    mesh.release(0);
    let status = mesh.children[0].as_mut().unwrap().wait().unwrap();
    assert!(!status.success());
    assert_eq!(mesh.restore(&scenario, 0).receipt().records, records);
    mesh.passed = true;
}
