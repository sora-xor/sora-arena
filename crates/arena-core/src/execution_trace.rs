//! Full tick-boundary witness export from locally certified input history.
//!
//! This is a prover input, not a proof, a native ledger codec, or an admission
//! authority. The caller must authenticate the original admission separately.
//! Every boundary is recomputed from genesis; no supplied state is restored.
//! Unverified deadline attestations are refused until a native consensus adapter
//! exists. Pending frontiers remain explicitly unexecuted in the export.
use std::io::{self, Read, Write};

use sha2::{Digest, Sha256};

use crate::{
    Error, RULES_VERSION,
    protocol::{
        BATCH_TICKS, CommitmentSet, EvidenceLog, Hash, MAX_BATCHES, Phase, Reveal, SlotSignature,
    },
    rollback::RollbackSession,
    simulation::{Config, Participant, World},
};

/// The only supported local witness-stream format. It is not Norito.
pub const MAGIC: &[u8] = b"SORA-ARENA-EXECUTION-TRACE\x01";

/// Source identity of the reference witness path, not a native proof profile.
/// A change to any outcome, certificate or witness-encoding implementation
/// invalidates this identity even when RULES_VERSION has not changed.
pub fn source_digest() -> Hash {
    macro_rules! sources {
        ($($name:literal),+ $(,)?) => {
            &[$(($name, include_bytes!($name).as_slice())),+]
        };
    }
    let files: &[(&str, &[u8])] = sources![
        "../../../Cargo.toml",
        "../../../Cargo.lock",
        "../../../rust-toolchain.toml",
        "../Cargo.toml",
        "lib.rs",
        "simulation.rs",
        "simulation/abilities.rs",
        "simulation/hazards.rs",
        "simulation/objectives.rs",
        "simulation/respawn.rs",
        "simulation/state.rs",
        "catalog.rs",
        "economy.rs",
        "maps.rs",
        "math.rs",
        "protocol.rs",
        "rollback.rs",
        "execution_trace.rs",
    ];
    let mut hash = Sha256::new();
    hash.update(b"sora-arena:execution-trace-source:v1\0");
    for (name, contents) in files {
        hash.update((name.len() as u64).to_le_bytes());
        hash.update(name.as_bytes());
        // Normalize line endings consistently across Git Windows checkouts.
        let normalized = String::from_utf8_lossy(contents).replace("\r\n", "\n");
        hash.update((normalized.len() as u64).to_le_bytes());
        hash.update(normalized.as_bytes());
    }
    hash.finalize().into()
}

#[derive(Debug)]
pub enum TraceError {
    Evidence(Error),
    Io(io::Error),
}
impl std::fmt::Display for TraceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Evidence(error) => error.fmt(f),
            Self::Io(error) => error.fmt(f),
        }
    }
}
impl std::error::Error for TraceError {}
impl From<Error> for TraceError {
    fn from(error: Error) -> Self {
        Self::Evidence(error)
    }
}
impl From<io::Error> for TraceError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

/// Local replay measurements. None of these fields establishes ledger finality.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TraceSummary {
    pub tick: u32,
    pub evidence_tick: u32,
    pub certified_tick: u32,
    pub pending_frontiers: usize,
    pub completed: bool,
    pub phase: Phase,
    pub state_hash: Hash,
    pub history_root: Hash,
    pub encoded_bytes: u64,
    /// SHA-256 of the complete stream before its final 32-byte seal.
    pub trace_digest: Hash,
}

fn invalid(reason: &'static str) -> TraceError {
    Error::InvalidEvidence(reason).into()
}

struct Sink<W> {
    output: W,
    hash: Sha256,
    bytes: u64,
}
impl<W: Write> Sink<W> {
    fn put(&mut self, bytes: &[u8]) -> Result<(), TraceError> {
        self.output.write_all(bytes)?;
        self.hash.update(bytes);
        self.bytes = self
            .bytes
            .checked_add(bytes.len() as u64)
            .ok_or(Error::Arithmetic)?;
        Ok(())
    }
    fn count(&mut self, count: usize) -> Result<(), TraceError> {
        let count = u32::try_from(count).map_err(|_| Error::Arithmetic)?;
        self.put(&count.to_le_bytes())
    }
    fn blob(&mut self, bytes: &[u8]) -> Result<(), TraceError> {
        self.count(bytes.len())?;
        self.put(bytes)
    }
    fn boundary(&mut self, world: &World) -> Result<(), TraceError> {
        self.blob(&world.state_bytes())
    }
    fn frontier(
        &mut self,
        set: &CommitmentSet,
        signatures: &[SlotSignature],
        openings: &[Option<Reveal>],
    ) -> Result<(), TraceError> {
        self.put(&set.epoch.to_le_bytes())?;
        self.put(&set.start_tick.to_le_bytes())?;
        self.put(&set.parent)?;
        self.count(set.commitments.len())?;
        for commitment in &set.commitments {
            self.put(commitment)?;
        }
        self.count(signatures.len())?;
        for signature in signatures {
            self.count(signature.slot)?;
            self.put(&signature.signature)?;
        }
        self.count(openings.len())?;
        for opening in openings {
            self.put(&[u8::from(opening.is_some())])?;
            if let Some(opening) = opening {
                self.count(opening.slot)?;
                self.put(&opening.start_tick.to_le_bytes())?;
                self.count(opening.inputs.len())?;
                for input in &opening.inputs {
                    self.put(&input.encode())?;
                }
                self.put(&opening.salt)?;
            }
        }
        Ok(())
    }
}

fn admit_frontier(
    evidence: &mut EvidenceLog,
    set: &CommitmentSet,
    signatures: &[SlotSignature],
    openings: &[Option<Reveal>],
    max_ticks: u32,
) -> Result<(), TraceError> {
    if set.start_tick >= max_ticks || openings.len() != evidence.context.roster.len() {
        return Err(invalid("trace frontier exceeds match or opening roster"));
    }
    evidence.certify(set.clone(), signatures.to_vec())?;
    for (slot, opening) in openings.iter().enumerate() {
        if let Some(opening) = opening {
            if opening.slot != slot {
                return Err(invalid("trace openings are not in permanent slot order"));
            }
            evidence.open(opening.clone())?;
        }
    }
    Ok(())
}

/// Stream full state at genesis and after every executed tick, with the exact
/// certificates, salted openings and roots which selected the local controls.
/// Original admission terms are written separately from mutable loadouts. A
/// successful replay checks them against the retained final simulation state;
/// it cannot authenticate the caller's opaque network/manifest or NFT claims.
///
/// A failure may leave a prefix in `output`. Discard it: only success and the
/// final seal represent a complete trace. Memory does not grow with the number
/// of emitted boundaries. Source evidence remains borrowed and unchanged.
pub fn write_trace<W: Write>(
    config: Config,
    participants: &[Participant],
    session: &RollbackSession,
    output: W,
) -> Result<TraceSummary, TraceError> {
    let source = session.evidence();
    if source.context.roster.len() != participants.len() || source.batches.len() > MAX_BATCHES {
        return Err(invalid("trace admission or history bound differs"));
    }
    // Deadline hashes in the local protocol are an external trust boundary.
    // Do not turn their mere nonzero presence into authority for a proof witness.
    if source.batches.iter().any(|b| b.deadline.is_some())
        || source.pending.iter().any(|b| b.deadline.is_some())
    {
        return Err(invalid(
            "trace requires authenticated consensus deadline adapter",
        ));
    }
    let mut evidence = EvidenceLog::new(source.context.clone())?;
    let mut world = World::new(config, participants)?;
    let mut sink = Sink {
        output,
        hash: Sha256::new(),
        bytes: 0,
    };
    sink.put(MAGIC)?;
    sink.blob(RULES_VERSION.as_bytes())?;
    sink.put(&source_digest())?;
    sink.blob(&source.context.domain(b"full-execution-trace"))?;
    // The initial World encodes every Config field and map identity. Admission
    // is additional: current class/equipment may change during a respawn.
    sink.count(participants.len())?;
    for participant in participants {
        let Participant {
            team,
            class,
            weapon,
            bond,
            special_entitled,
        } = participant;
        sink.put(&[*team, *class, *weapon, u8::from(*special_entitled)])?;
        sink.put(&bond.to_le_bytes())?;
    }
    sink.boundary(&world)?;
    sink.count(source.batches.len())?;
    for batch in source.batches.iter() {
        if world.terminal || batch.set.start_tick != world.tick {
            return Err(invalid(
                "trace contains a closed batch outside combat timeline",
            ));
        }
        let previous_root = evidence.root;
        admit_frontier(
            &mut evidence,
            &batch.set,
            &batch.signatures,
            &batch.openings,
            world.config.max_ticks,
        )?;
        let controls = evidence
            .close_next()?
            .ok_or_else(|| invalid("trace closed batch has an unresolved opening"))?;
        let mut boundaries = Vec::with_capacity(BATCH_TICKS);
        for inputs in &controls {
            if world.terminal {
                break;
            }
            world.step(inputs)?;
            boundaries.push(world.state_bytes());
        }
        sink.frontier(&batch.set, &batch.signatures, &batch.openings)?;
        sink.put(&previous_root)?;
        sink.put(&evidence.root)?;
        sink.count(boundaries.len())?;
        for (offset, boundary) in boundaries.iter().enumerate() {
            sink.put(&(batch.set.start_tick + offset as u32).to_le_bytes())?;
            // These controls are also in the signed openings above. Writing
            // their tick-major order makes the proof-stage schedule explicit.
            for input in &controls[offset] {
                sink.put(&input.encode())?;
            }
            sink.blob(boundary)?;
        }
    }
    if world.tick != session.confirmed().tick
        || world.state_bytes() != session.confirmed().state_bytes()
    {
        return Err(invalid(
            "trace replay differs from retained confirmed state",
        ));
    }
    sink.count(source.pending.len())?;
    for frontier in &source.pending {
        if frontier.digest != frontier.set.digest(&source.context)? {
            return Err(invalid("trace pending commitment digest differs"));
        }
        admit_frontier(
            &mut evidence,
            &frontier.set,
            &frontier.signatures,
            &frontier.openings,
            world.config.max_ticks,
        )?;
        sink.frontier(&frontier.set, &frontier.signatures, &frontier.openings)?;
    }
    match source.phase {
        Phase::Live => {}
        Phase::Resolving => evidence.interrupt(),
        Phase::Terminal => evidence.finish(world.terminal)?,
    }
    if evidence.epoch != source.epoch
        || evidence.next_tick != source.next_tick
        || evidence.certified_tick != source.certified_tick
        || evidence.root != source.root
        || evidence.commitment_head != source.commitment_head
        || evidence.phase != source.phase
    {
        return Err(invalid(
            "trace replay differs from retained evidence boundary",
        ));
    }
    sink.put(b"TRACE-END\0")?;
    let phase = match source.phase {
        Phase::Live => 0,
        Phase::Resolving => 1,
        Phase::Terminal => 2,
    };
    sink.put(&[phase, u8::from(world.terminal)])?;
    for tick in [world.tick, evidence.next_tick, evidence.certified_tick] {
        sink.put(&tick.to_le_bytes())?;
    }
    let state_hash = world.state_hash();
    sink.put(&state_hash)?;
    sink.put(&evidence.root)?;
    sink.put(&evidence.commitment_head)?;
    let trace_digest: Hash = sink.hash.finalize().into();
    sink.output.write_all(&trace_digest)?;
    sink.output.flush()?;
    Ok(TraceSummary {
        tick: world.tick,
        evidence_tick: evidence.next_tick,
        certified_tick: evidence.certified_tick,
        pending_frontiers: evidence.pending.len(),
        completed: world.terminal,
        phase: source.phase,
        state_hash,
        history_root: evidence.root,
        encoded_bytes: sink.bytes + 32,
        trace_digest,
    })
}

/// Validate a witness stream by replaying the independently supplied original
/// admission and retained signed evidence, comparing every byte and requiring
/// EOF. Claimed state, hashes or a file's own seal cannot stand in for replay.
/// This is a host reference check, not an independent execution implementation
/// or a native cryptographic verifier.
pub fn verify_trace<R: Read>(
    config: Config,
    participants: &[Participant],
    session: &RollbackSession,
    input: R,
) -> Result<TraceSummary, TraceError> {
    let mut comparison = Compare { input };
    let summary = write_trace(config, participants, session, &mut comparison)?;
    let mut extra = [0];
    loop {
        match comparison.input.read(&mut extra) {
            Ok(0) => return Ok(summary),
            Ok(_) => return Err(invalid("trace has trailing bytes")),
            Err(error) if error.kind() == io::ErrorKind::Interrupted => continue,
            Err(error) => return Err(error.into()),
        }
    }
}

struct Compare<R> {
    input: R,
}
impl<R: Read> Write for Compare<R> {
    fn write(&mut self, expected: &[u8]) -> io::Result<usize> {
        let mut buffer = [0; 8192];
        for chunk in expected.chunks(buffer.len()) {
            self.input.read_exact(&mut buffer[..chunk.len()])?;
            if &buffer[..chunk.len()] != chunk {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidData,
                    "trace differs from replay",
                ));
            }
        }
        Ok(expected.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
