//! Signed local P2P evidence. This is not a substitute for Iroha's native
//! consensus-selected history or a mathematical execution proof.
//!
//! Commitment and opening use two separate hash chains, so several batches
//! can be in flight while earlier ones are still being opened:
//!
//! - the *commitment chain*: every certified [`CommitmentSet`] names the
//!   digest of the set certified before it. An input commitment binds only
//!   its own slot, tick and controls, never another peer's reveal, so a peer
//!   commits its next batch without waiting for a round trip. At most
//!   [`MAX_OUTSTANDING_FRONTIERS`] certified sets may await their openings;
//! - the *reveal transcript*: frontiers close strictly in tick order, and each
//!   closure folds the set digest, how it closed and every slot's executed
//!   controls into `root`, which checkpoints sign.
//!
//! A peer dropout stops combat but never discards a certified frontier. Only
//! complete openings or native consensus's deadline decision can close one.
use crate::{Error, MAX_PLAYERS, MAX_TICKS, simulation::Input};
use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use sha2::{Digest, Sha256};
use std::{collections::VecDeque, sync::Arc};

pub type Hash = [u8; 32];
pub const BATCH_TICKS: usize = 2;
pub const MAX_BATCHES: usize = 18_000;
/// Certified frontiers that may await complete openings at once: 32 ticks,
/// 533 ms of committed controls at 60 Hz. A frontier opens about one one-way
/// delay after certification, so this bounds that delay plus jitter; the
/// batch rate itself no longer depends on the round trip.
pub const MAX_OUTSTANDING_FRONTIERS: usize = 16;
/// Batches a peer may commit beyond the last certified frontier: 64 ticks.
/// A commitment becomes a certificate about two one-way delays later, so this
/// and `MAX_OUTSTANDING_FRONTIERS` together bound the tolerated delay.
pub const MAX_ASSEMBLY_FRONTIERS: usize = 2 * MAX_OUTSTANDING_FRONTIERS;
/// Controls sampled on presentation tick `p` execute on tick
/// `p + INPUT_DELAY_TICKS` (67 ms). A batch is committed once its last control
/// is sampled, ahead of its first tick, which gives remote commitments and
/// openings that much longer to arrive before prediction must cover them.
pub const INPUT_DELAY_TICKS: u32 = 4;
const BATCH: u32 = BATCH_TICKS as u32;
const _: () = assert!(INPUT_DELAY_TICKS as usize <= MAX_OUTSTANDING_FRONTIERS * BATCH_TICKS);

/// The combat tick that executes a control sampled on presentation tick `p`.
pub const fn scheduled_tick(presentation_tick: u32) -> u32 {
    presentation_tick.saturating_add(INPUT_DELAY_TICKS)
}

/// The presentation tick on which the batch starting at `start_tick` holds
/// its last sampled control, so its commitment is due. `None` for the lead-in
/// batches that no sampled control reaches: peers commit the canonical idle
/// control for them at admission.
pub const fn commitment_due(start_tick: u32) -> Option<u32> {
    start_tick
        .saturating_add(BATCH - 1)
        .checked_sub(INPUT_DELAY_TICKS)
}

/// Frontiers start on a batch boundary and end inside the match clock.
pub(crate) fn validate_start(start_tick: u32) -> Result<(), Error> {
    if !start_tick.is_multiple_of(BATCH) || start_tick > MAX_TICKS - BATCH {
        return Err(Error::InvalidEvidence("frontier tick outside match"));
    }
    Ok(())
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Context {
    pub network: Hash,
    pub session: Hash,
    pub manifest: Hash,
    pub roster: Vec<[u8; 32]>,
}
impl Context {
    pub fn validate(&self) -> Result<(), Error> {
        if self.roster.is_empty() || self.roster.len() > MAX_PLAYERS {
            return Err(Error::InvalidEvidence("invalid roster bound"));
        }
        for (i, key) in self.roster.iter().enumerate() {
            if self.roster[..i].contains(key) || VerifyingKey::from_bytes(key).is_err() {
                return Err(Error::InvalidEvidence(
                    "duplicate or invalid input authority",
                ));
            }
        }
        Ok(())
    }
    pub(crate) fn domain(&self, tag: &[u8]) -> Vec<u8> {
        let mut out = b"sora-arena:p2p-evidence:v2\0".to_vec();
        out.extend((tag.len() as u32).to_le_bytes());
        out.extend(tag);
        out.extend(self.network);
        out.extend(self.session);
        out.extend(self.manifest);
        out.extend((self.roster.len() as u32).to_le_bytes());
        for key in &self.roster {
            out.extend(key);
        }
        out
    }
}

/// One batch's input commitments in slot order. `parent` is the digest of
/// the set certified before it, or the commitment genesis for the first.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommitmentSet {
    pub epoch: u64,
    pub start_tick: u32,
    pub parent: Hash,
    pub commitments: Vec<Hash>,
}
impl CommitmentSet {
    pub fn digest(&self, context: &Context) -> Result<Hash, Error> {
        context.validate()?;
        if self.commitments.len() != context.roster.len() {
            return Err(Error::InvalidEvidence("commitment roster mismatch"));
        }
        let mut b = context.domain(b"complete-commitment-set");
        b.extend(self.epoch.to_le_bytes());
        b.extend(self.start_tick.to_le_bytes());
        b.extend(self.parent);
        for c in &self.commitments {
            b.extend(c);
        }
        Ok(Sha256::digest(b).into())
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SlotSignature {
    pub slot: usize,
    pub signature: [u8; 64],
}

pub fn sign_commitment_set(
    context: &Context,
    set: &CommitmentSet,
    slot: usize,
    key: &SigningKey,
) -> Result<SlotSignature, Error> {
    if context.roster.get(slot) != Some(&key.verifying_key().to_bytes()) {
        return Err(Error::InvalidEvidence("input key does not own slot"));
    }
    Ok(SlotSignature {
        slot,
        signature: key.sign(&set.digest(context)?).to_bytes(),
    })
}

/// One original roster key's endorsement of exactly this set.
pub fn verify_set_signature(
    context: &Context,
    set: &CommitmentSet,
    signature: &SlotSignature,
) -> Result<(), Error> {
    let digest = set.digest(context)?;
    let key = context
        .roster
        .get(signature.slot)
        .ok_or(Error::InvalidEvidence("signature slot outside roster"))?;
    VerifyingKey::from_bytes(key)
        .map_err(|_| Error::InvalidEvidence("invalid input key"))?
        .verify_strict(&digest, &Signature::from_bytes(&signature.signature))
        .map_err(|_| Error::InvalidEvidence("invalid commitment signature"))
}

pub fn verify_certificate(
    context: &Context,
    set: &CommitmentSet,
    signatures: &[SlotSignature],
) -> Result<(), Error> {
    set.digest(context)?;
    if signatures.len() != context.roster.len() {
        return Err(Error::InvalidEvidence(
            "certificate requires every original key",
        ));
    }
    for (slot, sig) in signatures.iter().enumerate() {
        if slot != sig.slot {
            return Err(Error::InvalidEvidence(
                "signatures must be unique and in roster order",
            ));
        }
        verify_set_signature(context, set, sig)?;
    }
    Ok(())
}

/// A slot's commitment to its controls for one batch. It deliberately binds
/// no other peer's commitment or reveal, so batches can be committed ahead.
pub fn input_commitment(
    context: &Context,
    epoch: u64,
    start_tick: u32,
    slot: usize,
    inputs: &[Input],
    salt: Hash,
) -> Result<Hash, Error> {
    context.validate()?;
    validate_start(start_tick)?;
    if slot >= context.roster.len() || inputs.len() != BATCH_TICKS {
        return Err(Error::InvalidEvidence("invalid input commitment bounds"));
    }
    let mut b = context.domain(b"inputs");
    b.extend(epoch.to_le_bytes());
    b.extend(start_tick.to_le_bytes());
    b.extend((slot as u32).to_le_bytes());
    b.extend((inputs.len() as u32).to_le_bytes());
    for &input in inputs {
        input.validate()?;
        b.extend(input.encode());
    }
    b.extend(salt);
    Ok(Sha256::digest(b).into())
}

/// One slot's opening of its commitment in the frontier starting at `start_tick`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Reveal {
    pub start_tick: u32,
    pub slot: usize,
    pub inputs: Vec<Input>,
    pub salt: Hash,
}
impl Reveal {
    pub fn commitment(&self, context: &Context, epoch: u64) -> Result<Hash, Error> {
        input_commitment(
            context,
            epoch,
            self.start_tick,
            self.slot,
            &self.inputs,
            self.salt,
        )
    }
    /// The opening must name `set` and reproduce its slot's exact commitment.
    pub fn verify(&self, context: &Context, set: &CommitmentSet) -> Result<(), Error> {
        if self.start_tick != set.start_tick
            || set.commitments.len() != context.roster.len()
            || self.slot >= set.commitments.len()
        {
            return Err(Error::InvalidEvidence("reveal roster or tick mismatch"));
        }
        if self.commitment(context, set.epoch)? != set.commitments[self.slot] {
            return Err(Error::InvalidEvidence(
                "reveal does not match certified commitment",
            ));
        }
        Ok(())
    }
}

/// Native consensus's decision that the opening deadline of one certified
/// frontier passed. `openings` is consensus's retained view in slot order:
/// a `None` slot published no opening in time and is forfeited, executing the
/// canonical idle control for the whole batch. Any peer may publish any
/// opening, so honest peers publish every one they hold before the deadline.
///
/// `attestation` identifies the consensus decision. arena-core cannot verify
/// it: the chain adapter must, and the transcript binds it so a native
/// verifier rejects any other substitution. A peer clock never produces one.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeadlineResolution {
    pub start_tick: u32,
    pub frontier: Hash,
    pub attestation: Hash,
    pub openings: Vec<Option<Reveal>>,
}

/// Certified commitment sets a reveal may open, looked up by start tick.
/// Callers pass their own evidence, never a set received with the reveal.
pub trait CertifiedFrontiers {
    fn certified_frontier(&self, start_tick: u32) -> Option<&CommitmentSet>;
}
impl CertifiedFrontiers for [CommitmentSet] {
    fn certified_frontier(&self, start_tick: u32) -> Option<&CommitmentSet> {
        self.iter().find(|set| set.start_tick == start_tick)
    }
}
/// For decoding packets that cannot carry a reveal.
pub const NO_FRONTIERS: &[CommitmentSet] = &[];

/// A certified frontier that has not been closed into the transcript yet.
#[derive(Debug, Clone)]
pub struct PendingFrontier {
    pub set: CommitmentSet,
    pub digest: Hash,
    pub signatures: Vec<SlotSignature>,
    pub openings: Vec<Option<Reveal>>,
    /// Consensus attestation that closed this frontier's opening deadline.
    pub deadline: Option<Hash>,
}
impl PendingFrontier {
    pub fn ready(&self) -> bool {
        self.deadline.is_some() || self.openings.iter().all(Option::is_some)
    }
}

#[derive(Debug, Clone)]
pub struct CertifiedBatch {
    pub set: CommitmentSet,
    pub signatures: Vec<SlotSignature>,
    /// `None` only for a slot forfeited by `deadline`.
    pub openings: Vec<Option<Reveal>>,
    pub deadline: Option<Hash>,
}

const HISTORY_CHUNK_BATCHES: usize = 64;

#[derive(Debug, Clone)]
struct HistoryChunk {
    previous: Option<Arc<HistoryChunk>>,
    batches: Vec<Arc<CertifiedBatch>>,
}

/// Persistent evidence storage. Transactional candidate states share immutable
/// history and copy at most 64 batch pointers when appending, instead of copying
/// all prior signatures and controls for every received reveal. At the protocol
/// limit there are at most 282 linked chunks, bounding recursive destruction.
#[derive(Debug, Clone, Default)]
pub struct BatchHistory {
    head: Option<Arc<HistoryChunk>>,
    len: usize,
}
impl BatchHistory {
    pub fn len(&self) -> usize {
        self.len
    }
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }
    pub fn iter(&self) -> impl Iterator<Item = &CertifiedBatch> {
        let mut chunks = Vec::new();
        let mut next = self.head.as_deref();
        while let Some(chunk) = next {
            chunks.push(chunk);
            next = chunk.previous.as_deref();
        }
        chunks
            .into_iter()
            .rev()
            .flat_map(|chunk| chunk.batches.iter().map(Arc::as_ref))
    }
    /// The closed batch at `index`, its start tick over `BATCH_TICKS`.
    pub fn get(&self, index: usize) -> Option<&CertifiedBatch> {
        if index >= self.len {
            return None;
        }
        // Every chunk but the newest is full.
        let mut chunk = self.head.as_deref()?;
        for _ in index / HISTORY_CHUNK_BATCHES..(self.len - 1) / HISTORY_CHUNK_BATCHES {
            chunk = chunk.previous.as_deref()?;
        }
        chunk
            .batches
            .get(index % HISTORY_CHUNK_BATCHES)
            .map(Arc::as_ref)
    }
    fn push(&mut self, batch: CertifiedBatch) {
        if self
            .head
            .as_ref()
            .is_none_or(|head| head.batches.len() == HISTORY_CHUNK_BATCHES)
        {
            self.head = Some(Arc::new(HistoryChunk {
                previous: self.head.clone(),
                batches: Vec::new(),
            }));
        }
        Arc::make_mut(self.head.as_mut().expect("history head created"))
            .batches
            .push(Arc::new(batch));
        self.len += 1;
    }
}

/// `Live` accepts new frontiers and prediction. `Resolving` has stopped
/// combat: it still accepts certificates that were fully signed before the
/// dropout, openings and consensus deadlines, but no local peer signs a new
/// set. `Terminal` accepts nothing.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Phase {
    Live,
    Resolving,
    Terminal,
}

/// Retains certified frontiers until their openings close them. Only native
/// consensus can decide a missing opening; a peer clock cannot slash or erase
/// pending evidence.
#[derive(Debug, Clone)]
pub struct EvidenceLog {
    pub context: Context,
    pub epoch: u64,
    /// First tick after the last closed frontier.
    pub next_tick: u32,
    /// Reveal transcript root over every closed frontier.
    pub root: Hash,
    /// Digest of the newest certified set, the next set's parent.
    pub commitment_head: Hash,
    /// First tick of the next frontier to certify.
    pub certified_tick: u32,
    pub phase: Phase,
    /// Certified, unclosed frontiers from `next_tick`, oldest first.
    pub pending: VecDeque<PendingFrontier>,
    pub batches: BatchHistory,
}
impl EvidenceLog {
    pub fn new(context: Context) -> Result<Self, Error> {
        context.validate()?;
        let root = Sha256::digest(context.domain(b"transcript-genesis")).into();
        let commitment_head = Sha256::digest(context.domain(b"commitment-genesis")).into();
        Ok(Self {
            context,
            epoch: 0,
            next_tick: 0,
            root,
            commitment_head,
            certified_tick: 0,
            phase: Phase::Live,
            pending: VecDeque::new(),
            batches: BatchHistory::default(),
        })
    }

    /// Append the next frontier to the commitment chain. Certificates remain
    /// acceptable while resolving: each needed every original signature, so it
    /// was complete before the dropout and cannot be discarded.
    pub fn certify(
        &mut self,
        set: CommitmentSet,
        signatures: Vec<SlotSignature>,
    ) -> Result<(), Error> {
        if self.phase == Phase::Terminal {
            return Err(Error::Terminal);
        }
        if self.pending.len() >= MAX_OUTSTANDING_FRONTIERS {
            return Err(Error::InvalidEvidence("commitment pipeline is full"));
        }
        if self.certified_tick > MAX_TICKS - BATCH
            || set.epoch != self.epoch
            || set.start_tick != self.certified_tick
            || set.parent != self.commitment_head
        {
            return Err(Error::InvalidEvidence(
                "stale or unrelated commitment frontier",
            ));
        }
        verify_certificate(&self.context, &set, &signatures)?;
        let digest = set.digest(&self.context)?;
        self.pending.push_back(PendingFrontier {
            openings: vec![None; set.commitments.len()],
            set,
            digest,
            signatures,
            deadline: None,
        });
        self.commitment_head = digest;
        self.certified_tick += BATCH;
        Ok(())
    }

    pub fn frontier(&self, start_tick: u32) -> Option<&PendingFrontier> {
        let offset = start_tick.checked_sub(self.next_tick)?;
        if !offset.is_multiple_of(BATCH) {
            return None;
        }
        self.pending.get((offset / BATCH) as usize)
    }
    fn frontier_mut(&mut self, start_tick: u32) -> Option<&mut PendingFrontier> {
        let offset = start_tick.checked_sub(self.next_tick)?;
        if !offset.is_multiple_of(BATCH) {
            return None;
        }
        self.pending.get_mut((offset / BATCH) as usize)
    }
    fn closed(&self, start_tick: u32) -> Option<&CertifiedBatch> {
        if start_tick >= self.next_tick || !start_tick.is_multiple_of(BATCH) {
            return None;
        }
        self.batches.get((start_tick / BATCH) as usize)
    }

    /// True when this exact opening is already part of the evidence.
    pub fn retains(&self, reveal: &Reveal) -> bool {
        let openings = match self.closed(reveal.start_tick) {
            Some(batch) => &batch.openings,
            None => match self.frontier(reveal.start_tick) {
                Some(frontier) => &frontier.openings,
                None => return false,
            },
        };
        openings.get(reveal.slot).and_then(Option::as_ref) == Some(reveal)
    }

    /// Retain one opening of any pending frontier. Openings may arrive in any
    /// order; frontiers still close in tick order. An exact repeat, including
    /// one of an already closed frontier, is accepted without change.
    pub fn open(&mut self, reveal: Reveal) -> Result<bool, Error> {
        if self.phase == Phase::Terminal {
            return Err(Error::Terminal);
        }
        if self.retains(&reveal) {
            return Ok(false);
        }
        if self.closed(reveal.start_tick).is_some() {
            return Err(Error::InvalidEvidence(
                "opening of a closed frontier differs",
            ));
        }
        let context = &self.context;
        let frontier = self
            .pending
            .iter_mut()
            .find(|frontier| frontier.set.start_tick == reveal.start_tick)
            .ok_or(Error::InvalidEvidence("reveal without certified frontier"))?;
        if frontier.deadline.is_some() {
            return Err(Error::InvalidEvidence(
                "frontier closed by consensus deadline",
            ));
        }
        reveal.verify(context, &frontier.set)?;
        let slot = &mut frontier.openings[reveal.slot];
        if slot.is_some() {
            // Two openings of one SHA-256 commitment would be a collision.
            return Err(Error::InvalidEvidence("conflicting opening"));
        }
        *slot = Some(reveal);
        Ok(true)
    }

    /// Attach native consensus's deadline decision to one pending frontier.
    /// This stops combat. A frontier that consensus holds complete openings
    /// for closes through those openings, never as a deadline, so every peer
    /// that sees them derives the same transcript.
    pub fn resolve_deadline(&mut self, resolution: &DeadlineResolution) -> Result<(), Error> {
        if self.phase == Phase::Terminal {
            return Err(Error::Terminal);
        }
        if resolution.attestation == [0; 32] {
            return Err(Error::InvalidEvidence(
                "deadline without consensus attestation",
            ));
        }
        let context = self.context.clone();
        let frontier = self
            .frontier_mut(resolution.start_tick)
            .ok_or(Error::InvalidEvidence(
                "deadline without certified frontier",
            ))?;
        if frontier.digest != resolution.frontier || frontier.deadline.is_some() {
            return Err(Error::InvalidEvidence("deadline names another frontier"));
        }
        if resolution.openings.len() != context.roster.len()
            || resolution.openings.iter().all(Option::is_some)
        {
            return Err(Error::InvalidEvidence(
                "deadline must forfeit a missing opening",
            ));
        }
        for (slot, opening) in resolution.openings.iter().enumerate() {
            if let Some(opening) = opening {
                if opening.slot != slot {
                    return Err(Error::InvalidEvidence("deadline opening out of slot order"));
                }
                opening.verify(&context, &frontier.set)?;
            }
        }
        // Consensus's view is final: a locally held opening that nobody
        // published before the deadline no longer counts.
        frontier.openings = resolution.openings.clone();
        frontier.deadline = Some(resolution.attestation);
        self.interrupt();
        Ok(())
    }

    /// Close the oldest frontier once it is complete or consensus resolved
    /// it, returning its controls tick-major in slot order. A forfeited slot
    /// executes the canonical idle control; the transcript records that it did.
    pub fn close_next(&mut self) -> Result<Option<Vec<Vec<Input>>>, Error> {
        if self.phase == Phase::Terminal {
            return Err(Error::Terminal);
        }
        let Some(frontier) = self.pending.front().filter(|f| f.ready()) else {
            return Ok(None);
        };
        let new_tick = self.next_tick.checked_add(BATCH).ok_or(Error::Arithmetic)?;
        if new_tick > MAX_TICKS {
            return Err(Error::InvalidEvidence("tick limit exceeded"));
        }
        let mut bytes = self.context.domain(b"transcript-batch");
        bytes.extend(self.root);
        bytes.extend(frontier.digest);
        match frontier.deadline {
            None => bytes.push(0),
            Some(attestation) => {
                bytes.push(1);
                bytes.extend(attestation);
            }
        }
        let idle = [Input::default(); BATCH_TICKS];
        let mut controls = vec![vec![Input::default(); frontier.openings.len()]; BATCH_TICKS];
        for (slot, opening) in frontier.openings.iter().enumerate() {
            bytes.push(u8::from(opening.is_some()));
            let inputs = opening.as_ref().map_or(&idle[..], |r| &r.inputs);
            for (tick, input) in inputs.iter().enumerate() {
                bytes.extend(input.encode());
                controls[tick][slot] = *input;
            }
        }
        let frontier = self.pending.pop_front().expect("checked ready frontier");
        self.batches.push(CertifiedBatch {
            set: frontier.set,
            signatures: frontier.signatures,
            openings: frontier.openings,
            deadline: frontier.deadline,
        });
        self.root = Sha256::digest(bytes).into();
        self.next_tick = new_tick;
        Ok(Some(controls))
    }

    pub fn interrupt(&mut self) {
        if self.phase == Phase::Live {
            self.phase = Phase::Resolving;
        }
    }
    /// Local evidence can be marked terminal only when no committed frontier
    /// is being silently discarded. Once combat itself is terminal, the
    /// remaining frontiers are void: they stay retained, and no control in
    /// them could change the outcome. Native dispute outcomes need their own
    /// verifier.
    pub fn finish(&mut self, combat_terminal: bool) -> Result<(), Error> {
        if !combat_terminal && !self.pending.is_empty() {
            return Err(Error::InvalidEvidence(
                "pending committed inputs must be resolved",
            ));
        }
        self.phase = Phase::Terminal;
        Ok(())
    }
}

impl CertifiedFrontiers for EvidenceLog {
    fn certified_frontier(&self, start_tick: u32) -> Option<&CommitmentSet> {
        self.closed(start_tick)
            .map(|batch| &batch.set)
            .or_else(|| self.frontier(start_tick).map(|frontier| &frontier.set))
    }
}

/// Gathers peers' input commitments and set endorsements ahead of
/// certification, one window per batch after the last certified frontier.
/// Certificates come out in commitment-chain order only, and one slot can
/// hold one commitment and one endorsed set per tick. Durable peers journal
/// their own opening and endorsement (`DurableSession::seal` and `endorse`)
/// before the commitment or signature leaves the process.
#[derive(Debug, Clone)]
pub struct FrontierAssembler {
    context: Context,
    epoch: u64,
    next_tick: u32,
    head: Hash,
    windows: VecDeque<Window>,
}

#[derive(Debug, Clone)]
struct Window {
    commitments: Vec<Option<Hash>>,
    /// Each slot's endorsed set digest and its signature over that digest.
    endorsements: Vec<Option<(Hash, [u8; 64])>>,
}

impl FrontierAssembler {
    /// Continue after the log's newest certified frontier.
    pub fn following(log: &EvidenceLog) -> Self {
        Self {
            context: log.context.clone(),
            epoch: log.epoch,
            next_tick: log.certified_tick,
            head: log.commitment_head,
            windows: VecDeque::new(),
        }
    }

    pub fn next_tick(&self) -> u32 {
        self.next_tick
    }

    /// Drop windows the log certified from another source, such as a
    /// relayed certificate or a restored journal.
    pub fn sync(&mut self, log: &EvidenceLog) {
        while self.next_tick < log.certified_tick {
            self.windows.pop_front();
            self.next_tick += BATCH;
        }
        if self.next_tick == log.certified_tick {
            self.head = log.commitment_head;
        }
    }

    fn window(&mut self, epoch: u64, start_tick: u32) -> Result<Option<&mut Window>, Error> {
        validate_start(start_tick)?;
        if epoch != self.epoch {
            return Err(Error::InvalidEvidence("commitment from another epoch"));
        }
        let Some(offset) = start_tick.checked_sub(self.next_tick) else {
            return Ok(None);
        };
        let index = (offset / BATCH) as usize;
        if index >= MAX_ASSEMBLY_FRONTIERS {
            return Err(Error::InvalidEvidence("commitment beyond assembly window"));
        }
        let count = self.context.roster.len();
        while self.windows.len() <= index {
            self.windows.push_back(Window {
                commitments: vec![None; count],
                endorsements: vec![None; count],
            });
        }
        Ok(self.windows.get_mut(index))
    }

    /// Record a slot's own commitment, authenticated by its signed envelope.
    /// A commitment for an already certified tick is ignored.
    pub fn add_commitment(
        &mut self,
        slot: usize,
        epoch: u64,
        start_tick: u32,
        commitment: Hash,
    ) -> Result<bool, Error> {
        if slot >= self.context.roster.len() {
            return Err(Error::InvalidEvidence("commitment slot outside roster"));
        }
        let Some(window) = self.window(epoch, start_tick)? else {
            return Ok(false);
        };
        match window.commitments[slot] {
            None => {
                window.commitments[slot] = Some(commitment);
                Ok(true)
            }
            Some(existing) if existing == commitment => Ok(false),
            Some(_) => Err(Error::InvalidEvidence("conflicting input commitment")),
        }
    }

    /// Record a slot's signature over one set, checked against its key.
    pub fn add_endorsement(
        &mut self,
        set: &CommitmentSet,
        signature: SlotSignature,
    ) -> Result<bool, Error> {
        verify_set_signature(&self.context, set, &signature)?;
        let digest = set.digest(&self.context)?;
        let Some(window) = self.window(set.epoch, set.start_tick)? else {
            return Ok(false);
        };
        match window.endorsements[signature.slot] {
            None => {
                window.endorsements[signature.slot] = Some((digest, signature.signature));
                Ok(true)
            }
            Some((existing, _)) if existing == digest => Ok(false),
            Some(_) => Err(Error::InvalidEvidence("conflicting set endorsement")),
        }
    }

    /// The set for `start_tick` once it and every earlier window hold every
    /// slot's commitment.
    pub fn assembled(&self, start_tick: u32) -> Option<CommitmentSet> {
        self.assembled_sets()
            .into_iter()
            .find(|(set, _)| set.start_tick == start_tick)
            .map(|(set, _)| set)
    }

    fn assembled_sets(&self) -> Vec<(CommitmentSet, Hash)> {
        let mut parent = self.head;
        let mut sets = Vec::new();
        for (index, window) in self.windows.iter().enumerate() {
            let Some(commitments) = window
                .commitments
                .iter()
                .copied()
                .collect::<Option<Vec<_>>>()
            else {
                break;
            };
            let set = CommitmentSet {
                epoch: self.epoch,
                start_tick: self.next_tick + index as u32 * BATCH,
                parent,
                commitments,
            };
            let Ok(digest) = set.digest(&self.context) else {
                break;
            };
            parent = digest;
            sets.push((set, digest));
        }
        sets
    }

    /// Assembled sets `slot` has not endorsed yet, oldest first. A peer that
    /// has stopped combat must not sign any of them.
    pub fn unendorsed(&self, slot: usize) -> Vec<CommitmentSet> {
        self.assembled_sets()
            .into_iter()
            .enumerate()
            .filter(|(index, _)| {
                self.windows[*index]
                    .endorsements
                    .get(slot)
                    .is_some_and(Option::is_none)
            })
            .map(|(_, (set, _))| set)
            .collect()
    }

    /// Pop the next frontier once every slot endorsed exactly its assembled
    /// set. A slot that endorsed another set can never complete it; that
    /// stall is a dropout for the resolution rules.
    pub fn take_certified(&mut self) -> Option<(CommitmentSet, Vec<SlotSignature>)> {
        let (set, digest) = self.assembled_sets().into_iter().next()?;
        let signatures = self.windows[0]
            .endorsements
            .iter()
            .enumerate()
            .map(|(slot, endorsement)| match endorsement {
                Some((endorsed, signature)) if *endorsed == digest => Some(SlotSignature {
                    slot,
                    signature: *signature,
                }),
                _ => None,
            })
            .collect::<Option<Vec<_>>>()?;
        self.windows.pop_front();
        self.head = digest;
        self.next_tick += BATCH;
        Some((set, signatures))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> (Vec<SigningKey>, EvidenceLog, CommitmentSet, Vec<Reveal>) {
        let keys = vec![
            SigningKey::from_bytes(&[1; 32]),
            SigningKey::from_bytes(&[2; 32]),
        ];
        let context = Context {
            network: [3; 32],
            session: [4; 32],
            manifest: [5; 32],
            roster: keys.iter().map(|k| k.verifying_key().to_bytes()).collect(),
        };
        let log = EvidenceLog::new(context).unwrap();
        let (set, reveals) = frontier(&log, 0, log.commitment_head, 0);
        (keys, log, set, reveals)
    }
    fn frontier(
        log: &EvidenceLog,
        start_tick: u32,
        parent: Hash,
        buttons: u32,
    ) -> (CommitmentSet, Vec<Reveal>) {
        let reveals = (0..log.context.roster.len())
            .map(|slot| Reveal {
                start_tick,
                slot,
                inputs: vec![
                    Input {
                        buttons,
                        ..Input::default()
                    };
                    BATCH_TICKS
                ],
                salt: [slot as u8 + start_tick as u8; 32],
            })
            .collect::<Vec<_>>();
        let set = CommitmentSet {
            epoch: 0,
            start_tick,
            parent,
            commitments: reveals
                .iter()
                .map(|r| r.commitment(&log.context, 0).unwrap())
                .collect(),
        };
        (set, reveals)
    }
    fn sigs(keys: &[SigningKey], log: &EvidenceLog, set: &CommitmentSet) -> Vec<SlotSignature> {
        keys.iter()
            .enumerate()
            .map(|(s, k)| sign_commitment_set(&log.context, set, s, k).unwrap())
            .collect()
    }
    fn open_all(log: &mut EvidenceLog, reveals: &[Reveal]) {
        for reveal in reveals {
            assert!(log.open(reveal.clone()).unwrap());
        }
    }

    #[test]
    fn reveal_requires_every_signature_then_replays_inputs() {
        let (k, mut l, s, r) = fixture();
        let signatures = sigs(&k, &l, &s);
        assert!(l.certify(s.clone(), signatures[..1].to_vec()).is_err());
        assert!(l.open(r[0].clone()).is_err());
        l.certify(s, signatures).unwrap();
        open_all(&mut l, &r[..1]);
        assert_eq!(l.close_next().unwrap(), None);
        open_all(&mut l, &r[1..]);
        assert_eq!(
            l.close_next().unwrap(),
            Some(vec![vec![Input::default(); 2]; 2])
        );
        assert_eq!(l.next_tick, 2);
        assert!(l.pending.is_empty());
    }

    #[test]
    fn cross_network_and_modified_reveals_reject() {
        let (k, mut l, s, mut r) = fixture();
        let mut other = l.context.clone();
        other.network = [9; 32];
        assert!(verify_certificate(&other, &s, &sigs(&k, &l, &s)).is_err());
        l.certify(s.clone(), sigs(&k, &l, &s)).unwrap();
        r[0].inputs[0].buttons = 1;
        assert!(l.open(r[0].clone()).is_err());
        let mut shifted = r[1].clone();
        shifted.start_tick = 2;
        assert!(l.open(shifted).is_err());
        assert!(l.pending[0].openings.iter().all(Option::is_none));
        assert_eq!(l.next_tick, 0);
    }

    #[test]
    fn disconnect_cannot_erase_a_committed_death() {
        let (k, mut l, s, r) = fixture();
        l.certify(s.clone(), sigs(&k, &l, &s)).unwrap();
        l.interrupt();
        assert!(l.finish(false).is_err());
        open_all(&mut l, &r);
        l.close_next().unwrap().unwrap();
        l.finish(false).unwrap();
        assert_eq!(l.phase, Phase::Terminal);
    }

    #[test]
    fn stale_frontier_and_duplicate_signature_reject() {
        let (k, mut l, s, r) = fixture();
        let mut dup = sigs(&k, &l, &s);
        dup[1] = dup[0].clone();
        assert!(l.certify(s.clone(), dup).is_err());
        let sig = sigs(&k, &l, &s);
        l.certify(s.clone(), sig.clone()).unwrap();
        open_all(&mut l, &r);
        l.close_next().unwrap().unwrap();
        assert!(l.certify(s, sig).is_err());
    }

    #[test]
    fn pipelined_frontiers_chain_commitments_and_close_in_tick_order() {
        let (k, mut l, _, _) = fixture();
        let mut parent = l.commitment_head;
        let mut frontiers = Vec::new();
        for batch in 0..MAX_OUTSTANDING_FRONTIERS as u32 {
            let (set, reveals) = frontier(&l, batch * BATCH, parent, batch % 2);
            // A set chained to the reveal transcript instead is unrelated.
            let mut wrong = set.clone();
            wrong.parent = l.root;
            if batch > 0 {
                assert!(l.certify(wrong.clone(), sigs(&k, &l, &wrong)).is_err());
            }
            parent = set.digest(&l.context).unwrap();
            l.certify(set.clone(), sigs(&k, &l, &set)).unwrap();
            frontiers.push((set, reveals));
        }
        assert_eq!(l.commitment_head, parent);
        let (extra, _) = frontier(&l, l.certified_tick, parent, 0);
        assert!(matches!(
            l.certify(extra.clone(), sigs(&k, &l, &extra)),
            Err(Error::InvalidEvidence("commitment pipeline is full"))
        ));
        // The second frontier opens first; it waits for the first.
        open_all(&mut l, &frontiers[1].1);
        assert_eq!(l.close_next().unwrap(), None);
        assert!(l.frontier(2).unwrap().ready());
        open_all(&mut l, &frontiers[0].1);
        let root_before = l.root;
        assert!(l.close_next().unwrap().is_some());
        assert!(l.close_next().unwrap().is_some());
        assert_eq!(l.close_next().unwrap(), None);
        assert_ne!(l.root, root_before);
        assert_eq!(l.next_tick, 4);
        // Exact repeats are idempotent, even for closed frontiers.
        assert!(!l.open(frontiers[0].1[1].clone()).unwrap());
        assert!(l.retains(&frontiers[1].1[0]));
        let mut altered = frontiers[0].1[0].clone();
        altered.salt[0] ^= 1;
        assert!(l.open(altered).is_err());
        assert_eq!(l.certified_frontier(0), Some(&frontiers[0].0));
        assert_eq!(l.certified_frontier(6), Some(&frontiers[3].0));
        // With capacity back, the chain continues from the certified head.
        l.certify(extra.clone(), sigs(&k, &l, &extra)).unwrap();
        assert_eq!(l.pending.len(), MAX_OUTSTANDING_FRONTIERS - 1);
    }

    #[test]
    fn transcript_is_independent_of_pipeline_depth() {
        let (k, _, _, _) = fixture();
        let mut sequential = fixture().1;
        let mut pipelined = sequential.clone();
        let mut parent = sequential.commitment_head;
        let mut frontiers = Vec::new();
        for batch in 0..6u32 {
            let (set, reveals) = frontier(&sequential, batch * BATCH, parent, batch % 3);
            parent = set.digest(&sequential.context).unwrap();
            frontiers.push((set, reveals));
        }
        for (set, reveals) in &frontiers {
            sequential
                .certify(set.clone(), sigs(&k, &sequential, set))
                .unwrap();
            open_all(&mut sequential, reveals);
            sequential.close_next().unwrap().unwrap();
        }
        for (set, _) in &frontiers {
            pipelined
                .certify(set.clone(), sigs(&k, &pipelined, set))
                .unwrap();
        }
        for (_, reveals) in frontiers.iter().rev() {
            open_all(&mut pipelined, reveals);
        }
        while pipelined.close_next().unwrap().is_some() {}
        assert_eq!(pipelined.root, sequential.root);
        assert_eq!(pipelined.commitment_head, sequential.commitment_head);
        assert_eq!(pipelined.next_tick, 12);
    }

    #[test]
    fn consensus_deadline_forfeits_only_missing_openings_and_is_bound_into_the_root() {
        let (k, mut l, s, r) = fixture();
        l.certify(s.clone(), sigs(&k, &l, &s)).unwrap();
        l.open(r[0].clone()).unwrap();
        let digest = s.digest(&l.context).unwrap();
        let resolution = DeadlineResolution {
            start_tick: 0,
            frontier: digest,
            attestation: [7; 32],
            openings: vec![Some(r[0].clone()), None],
        };
        let mut unattested = resolution.clone();
        unattested.attestation = [0; 32];
        let mut complete = resolution.clone();
        complete.openings[1] = Some(r[1].clone());
        let mut other = resolution.clone();
        other.frontier[0] ^= 1;
        let mut forged = resolution.clone();
        forged.openings[0].as_mut().unwrap().salt[0] ^= 1;
        for invalid in [unattested, complete, other, forged] {
            assert!(l.resolve_deadline(&invalid).is_err());
        }
        assert_eq!(l.phase, Phase::Live);
        let mut alternative = l.clone();
        l.resolve_deadline(&resolution).unwrap();
        assert_eq!(l.phase, Phase::Resolving);
        // Consensus closed the frontier: a late opening is refused.
        assert!(l.open(r[1].clone()).is_err());
        assert!(l.resolve_deadline(&resolution).is_err());
        let controls = l.close_next().unwrap().unwrap();
        assert_eq!(controls, vec![vec![Input::default(); 2]; 2]);
        // The forfeit is distinguishable from an opening of idle controls.
        alternative.open(r[1].clone()).unwrap();
        assert_eq!(alternative.close_next().unwrap().unwrap(), controls);
        assert_ne!(alternative.root, l.root);
        assert!(l.batches.get(0).unwrap().openings[1].is_none());
        assert_eq!(l.batches.get(0).unwrap().deadline, Some([7; 32]));
        assert!(!l.open(r[0].clone()).unwrap());
        assert!(l.open(r[1].clone()).is_err());
        l.finish(false).unwrap();
    }

    #[test]
    fn certificates_signed_before_a_dropout_are_still_accepted() {
        let (k, mut l, s, r) = fixture();
        l.interrupt();
        l.certify(s.clone(), sigs(&k, &l, &s)).unwrap();
        open_all(&mut l, &r);
        l.close_next().unwrap().unwrap();
        l.finish(false).unwrap();
        let (next, _) = frontier(&l, 2, l.commitment_head, 0);
        assert!(matches!(
            l.certify(next.clone(), sigs(&k, &l, &next)),
            Err(Error::Terminal)
        ));
        assert!(l.open(r[0].clone()).is_err());
    }

    #[test]
    fn assembler_certifies_in_chain_order_and_rejects_equivocation() {
        let (k, l, _, _) = fixture();
        let mut assembler = FrontierAssembler::following(&l);
        let (first, first_reveals) = frontier(&l, 0, l.commitment_head, 0);
        let first_digest = first.digest(&l.context).unwrap();
        let (second, _) = frontier(&l, 2, first_digest, 1);
        // Commitments for the second batch arrive first.
        for (slot, commitment) in second.commitments.iter().enumerate() {
            assert!(assembler.add_commitment(slot, 0, 2, *commitment).unwrap());
        }
        assert_eq!(assembler.assembled(2), None);
        assert!(assembler.unendorsed(0).is_empty());
        for (slot, commitment) in first.commitments.iter().enumerate() {
            assembler.add_commitment(slot, 0, 0, *commitment).unwrap();
        }
        assert!(
            !assembler
                .add_commitment(0, 0, 0, first.commitments[0])
                .unwrap()
        );
        assert!(assembler.add_commitment(0, 0, 0, [1; 32]).is_err());
        assert!(assembler.add_commitment(0, 1, 4, [1; 32]).is_err());
        assert!(
            assembler
                .add_commitment(0, 0, MAX_ASSEMBLY_FRONTIERS as u32 * BATCH, [1; 32])
                .is_err()
        );
        assert_eq!(assembler.assembled(0), Some(first.clone()));
        assert_eq!(assembler.assembled(2), Some(second.clone()));
        assert_eq!(assembler.unendorsed(1), vec![first.clone(), second.clone()]);
        for set in [&second, &first] {
            for (slot, key) in k.iter().enumerate() {
                let signature = sign_commitment_set(&l.context, set, slot, key).unwrap();
                assert!(assembler.add_endorsement(set, signature).unwrap());
            }
        }
        // A forged or second, different endorsement for a tick is refused.
        let mut forged = sign_commitment_set(&l.context, &first, 0, &k[0]).unwrap();
        forged.signature[0] ^= 1;
        assert!(assembler.add_endorsement(&first, forged).is_err());
        let mut other = first.clone();
        other.commitments[1] = [2; 32];
        let equivocation = sign_commitment_set(&l.context, &other, 1, &k[1]).unwrap();
        assert!(assembler.add_endorsement(&other, equivocation).is_err());

        let mut log = l.clone();
        let (set, signatures) = assembler.take_certified().unwrap();
        assert_eq!(set, first);
        log.certify(set, signatures).unwrap();
        let (set, signatures) = assembler.take_certified().unwrap();
        assert_eq!(set, second);
        log.certify(set, signatures).unwrap();
        assert!(assembler.take_certified().is_none());
        assert_eq!(assembler.next_tick(), log.certified_tick);
        // Late commitments for certified ticks are ignored, not errors.
        assert!(!assembler.add_commitment(0, 0, 0, [3; 32]).unwrap());
        for reveal in first_reveals {
            log.open(reveal).unwrap();
        }
        assert!(log.close_next().unwrap().is_some());
    }

    #[test]
    fn assembler_resynchronizes_after_a_relayed_certificate() {
        let (k, mut l, s, _) = fixture();
        let mut assembler = FrontierAssembler::following(&l);
        assembler.add_commitment(0, 0, 0, s.commitments[0]).unwrap();
        l.certify(s.clone(), sigs(&k, &l, &s)).unwrap();
        assembler.sync(&l);
        assert_eq!(assembler.next_tick(), 2);
        let (next, _) = frontier(&l, 2, l.commitment_head, 0);
        for (slot, commitment) in next.commitments.iter().enumerate() {
            assembler.add_commitment(slot, 0, 2, *commitment).unwrap();
        }
        assert_eq!(assembler.assembled(2), Some(next));
    }

    #[test]
    fn input_delay_schedules_commitments_ahead_of_their_first_tick() {
        assert_eq!(scheduled_tick(0), INPUT_DELAY_TICKS);
        for start in (0..64).step_by(BATCH_TICKS) {
            match commitment_due(start) {
                None => assert!(start + BATCH <= INPUT_DELAY_TICKS),
                Some(due) => {
                    assert_eq!(scheduled_tick(due), start + BATCH - 1);
                    assert!(due < start || INPUT_DELAY_TICKS < BATCH);
                }
            }
        }
    }

    #[test]
    fn history_clones_preserve_order_and_do_not_mutate_prior_frontiers() {
        let (_, _, set, reveals) = fixture();
        let batch = |tick| {
            let mut set = set.clone();
            set.start_tick = tick;
            CertifiedBatch {
                set,
                signatures: Vec::new(),
                openings: reveals.iter().cloned().map(Some).collect(),
                deadline: None,
            }
        };
        let mut history = BatchHistory::default();
        for tick in 0..65 {
            history.push(batch(tick));
        }
        let prefix = history.clone();
        let shared = Arc::clone(history.head.as_ref().unwrap());
        assert!(Arc::ptr_eq(prefix.head.as_ref().unwrap(), &shared));
        history.push(batch(65));
        assert_eq!(prefix.len(), 65);
        assert_eq!(history.len(), 66);
        assert_eq!(
            prefix.iter().map(|b| b.set.start_tick).collect::<Vec<_>>(),
            (0..65).collect::<Vec<_>>()
        );
        assert_eq!(
            history.iter().map(|b| b.set.start_tick).collect::<Vec<_>>(),
            (0..66).collect::<Vec<_>>()
        );
        for index in [0, 63, 64, 65] {
            assert_eq!(history.get(index).unwrap().set.start_tick, index as u32);
        }
        assert!(history.get(66).is_none());
        assert!(prefix.get(65).is_none());
        assert!(Arc::ptr_eq(
            prefix.head.as_ref().unwrap().previous.as_ref().unwrap(),
            history.head.as_ref().unwrap().previous.as_ref().unwrap()
        ));
    }

    #[test]
    fn fixed_batch_length_preserves_capacity_for_the_full_match() {
        let (_, log, _, _) = fixture();
        assert_eq!(MAX_BATCHES * BATCH_TICKS, crate::MAX_TICKS as usize);
        for ticks in [0, 1, 3] {
            assert!(
                input_commitment(
                    &log.context,
                    0,
                    0,
                    0,
                    &vec![Input::default(); ticks],
                    [0; 32]
                )
                .is_err()
            );
        }
        for start in [1, MAX_TICKS - 1, MAX_TICKS] {
            assert!(
                input_commitment(
                    &log.context,
                    0,
                    start,
                    0,
                    &[Input::default(); BATCH_TICKS],
                    [0; 32]
                )
                .is_err()
            );
        }
        assert!(
            input_commitment(
                &log.context,
                0,
                MAX_TICKS - BATCH,
                0,
                &[Input::default(); BATCH_TICKS],
                [0; 32]
            )
            .is_ok()
        );
    }
}
