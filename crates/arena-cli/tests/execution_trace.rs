//! CLI witness export from real signed, durable research evidence. No sockets,
//! wallet or chain operations are involved.
#[path = "../src/script.rs"]
mod script;

use arena_core::{
    execution_trace::write_trace,
    protocol::{BATCH_TICKS, CommitmentSet, Reveal, sign_commitment_set},
    recovery::{DurableSession, Receipt},
};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
    process::{Command, Output},
    sync::atomic::{AtomicU64, Ordering},
};

const PLAYERS: usize = 4;
const TICKS: u32 = 6;
const SESSION: u64 = 20_261_018;
static NEXT_ROOT: AtomicU64 = AtomicU64::new(0);

struct Fixture {
    root: PathBuf,
    journal: PathBuf,
    receipt: Receipt,
    expected: Vec<u8>,
    original_journal: Vec<u8>,
}

impl Fixture {
    fn new() -> Self {
        let root = std::env::temp_dir().join(format!(
            "sora-arena-trace-cli-{}-{}",
            std::process::id(),
            NEXT_ROOT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        let journal = root.join("peer.journal");
        let keys = script::keys(SESSION, PLAYERS);
        let context = script::context(SESSION, &keys, TICKS);
        let config = script::config(TICKS);
        let participants = script::participants(PLAYERS);
        let mut evidence =
            DurableSession::create(&journal, context.clone(), config.clone(), &participants)
                .unwrap();
        for start_tick in (0..TICKS).step_by(BATCH_TICKS) {
            let log = evidence.session().evidence();
            let openings = (0..PLAYERS)
                .map(|slot| Reveal {
                    start_tick,
                    slot,
                    inputs: (start_tick..start_tick + BATCH_TICKS as u32)
                        .map(|tick| script::control(tick, slot))
                        .collect(),
                    salt: [slot as u8 + start_tick as u8; 32],
                })
                .collect::<Vec<_>>();
            let set = CommitmentSet {
                epoch: log.epoch,
                start_tick,
                parent: log.commitment_head,
                commitments: openings
                    .iter()
                    .map(|opening| opening.commitment(&context, log.epoch).unwrap())
                    .collect(),
            };
            let signatures = keys
                .iter()
                .enumerate()
                .map(|(slot, key)| sign_commitment_set(&context, &set, slot, key).unwrap())
                .collect();
            evidence.certify(set, signatures).unwrap();
            evidence.reveal_many(openings).unwrap();
        }
        let receipt = evidence.finish().unwrap();
        let mut expected = Vec::new();
        let summary =
            write_trace(config, &participants, evidence.session(), &mut expected).unwrap();
        assert_eq!(summary.tick, TICKS);
        assert!(summary.completed);
        drop(evidence);
        let original_journal = fs::read(&journal).unwrap();
        Self {
            root,
            journal,
            receipt,
            expected,
            original_journal,
        }
    }

    fn command_with(&self, receipt: Receipt, players: usize, ticks: u32, session: u64) -> Command {
        let mut command = Command::new(env!("CARGO_BIN_EXE_arena-cli"));
        command
            .arg("trace")
            .arg("--journal")
            .arg(&self.journal)
            .args(["--receipt-records", &receipt.records.to_string()])
            .args(["--receipt-hash", &hex(&receipt.digest)])
            .args(["--players", &players.to_string()])
            .args(["--ticks", &ticks.to_string()])
            .args(["--session", &session.to_string()]);
        command
    }

    fn command(&self) -> Command {
        self.command_with(self.receipt, PLAYERS, TICKS, SESSION)
    }

    fn export(&self, path: &Path) -> Output {
        self.command().arg("--output").arg(path).output().unwrap()
    }

    fn verify(&self, path: &Path) -> Output {
        self.command().arg("--verify").arg(path).output().unwrap()
    }

    fn journal_unchanged(&self) {
        assert_eq!(fs::read(&self.journal).unwrap(), self.original_journal);
    }
}

impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn success(output: Output) -> String {
    assert!(
        output.status.success(),
        "stdout={} stderr={}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8(output.stdout).unwrap()
}

fn rejected(output: Output) {
    assert!(
        !output.status.success(),
        "unexpected success: {}",
        String::from_utf8_lossy(&output.stdout)
    );
    assert!(!output.stderr.is_empty(), "rejection needs a diagnostic");
}

#[test]
fn exports_and_verifies_exact_evidence_derived_bytes() {
    let f = Fixture::new();
    let path = f.root.join("match.trace");
    let output = success(f.export(&path));
    assert!(output.contains(
        "trace ticks=6 evidence_tick=6 certified_tick=6 pending=0 completed=true phase=Terminal"
    ));
    assert!(output.contains("scope=scripted_research_journal execution_proof=false ledger_selected=false ledger_transactions=0"));
    assert_eq!(fs::read(&path).unwrap(), f.expected);
    let verified = success(f.verify(&path));
    assert_eq!(verified, output);
    assert_eq!(fs::read(&path).unwrap(), f.expected);
    f.journal_unchanged();
}

#[test]
fn altered_resealed_truncated_and_extended_traces_are_rejected() {
    let f = Fixture::new();
    let path = f.root.join("modified.trace");
    let mut altered = f.expected.clone();
    let middle = altered.len() / 2;
    altered[middle] ^= 1;
    // A valid checksum is not sufficient: verification must replay and
    // compare the actual state/evidence bytes against the retained journal.
    let seal = altered.len() - 32;
    let digest = Sha256::digest(&altered[..seal]);
    altered[seal..].copy_from_slice(&digest);
    let mut extended = f.expected.clone();
    extended.push(0);
    for bytes in [
        altered,
        Vec::new(),
        f.expected[..1].to_vec(),
        f.expected[..middle].to_vec(),
        f.expected[..f.expected.len() - 1].to_vec(),
        extended,
    ] {
        fs::write(&path, &bytes).unwrap();
        rejected(f.verify(&path));
        assert_eq!(
            fs::read(&path).unwrap(),
            bytes,
            "verification must not repair input"
        );
    }
    f.journal_unchanged();
}

#[test]
fn wrong_receipts_and_original_admission_never_create_output() {
    let f = Fixture::new();
    let path = f.root.join("refused.trace");
    let mut wrong_digest = f.receipt;
    wrong_digest.digest[0] ^= 1;
    let mut future = f.receipt;
    future.records += 1;
    for (receipt, players, ticks, session) in [
        (wrong_digest, PLAYERS, TICKS, SESSION),
        (future, PLAYERS, TICKS, SESSION),
        (f.receipt, PLAYERS - 1, TICKS, SESSION),
        (f.receipt, PLAYERS, TICKS + 2, SESSION),
        (f.receipt, PLAYERS, TICKS, SESSION + 1),
    ] {
        rejected(
            f.command_with(receipt, players, ticks, session)
                .arg("--output")
                .arg(&path)
                .output()
                .unwrap(),
        );
        assert!(!path.exists());
    }
    f.journal_unchanged();
}

#[test]
fn existing_files_and_the_evidence_journal_are_never_overwritten() {
    let f = Fixture::new();
    let path = f.root.join("existing.trace");
    let sentinel = b"existing output belongs to the user";
    fs::write(&path, sentinel).unwrap();
    rejected(f.export(&path));
    assert_eq!(fs::read(&path).unwrap(), sentinel);
    rejected(f.export(&f.journal));
    f.journal_unchanged();
    let directory = f.root.join("existing-directory");
    fs::create_dir(&directory).unwrap();
    rejected(f.export(&directory));
    assert!(directory.is_dir());
}

#[cfg(unix)]
#[test]
fn existing_and_dangling_output_symlinks_are_never_followed() {
    use std::os::unix::fs::symlink;
    let f = Fixture::new();
    let link = f.root.join("journal-link.trace");
    symlink(&f.journal, &link).unwrap();
    rejected(f.export(&link));
    assert_eq!(fs::read_link(&link).unwrap(), f.journal);
    f.journal_unchanged();

    let missing = f.root.join("must-not-be-created.trace");
    let dangling = f.root.join("dangling.trace");
    symlink(&missing, &dangling).unwrap();
    rejected(f.export(&dangling));
    assert_eq!(fs::read_link(&dangling).unwrap(), missing);
    assert!(!missing.exists());
}

#[test]
fn a_partial_corrupt_journal_never_exports_its_valid_prefix() {
    let f = Fixture::new();
    // All originally anchored records remain valid; the suffix is a torn
    // next record. The CLI must reject the prefix reader's partial result.
    OpenOptions::new()
        .append(true)
        .open(&f.journal)
        .unwrap()
        .write_all(&[0xff, 0x01, 0x02])
        .unwrap();
    let corrupt = fs::read(&f.journal).unwrap();
    let output = f.root.join("partial.trace");
    rejected(f.export(&output));
    assert!(!output.exists());
    assert_eq!(fs::read(&f.journal).unwrap(), corrupt);
}
