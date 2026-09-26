//! Durable local evidence, with cryptographic replay and explicit admission binding.
//!
//! This first-release file format is not a native ledger codec or an execution
//! proof. A single process owns an advisory lock; each accepted operation is
//! flushed before returning, unless the owner switched to group commit, where
//! one write and one sync cover every record accepted since the last one.
//! Torn records fail closed without changing the file. A trusted receipt from a
//! peer/ledger is needed to detect deletion of complete suffix records. Local
//! bytes alone cannot establish the latest agreed frontier.
use std::{
    collections::{BTreeMap, BTreeSet},
    fs::{File, OpenOptions},
    io::{Read, Seek, SeekFrom, Write},
    path::Path,
    sync::Arc,
};

use ed25519_dalek::SigningKey;
use sha2::{Digest, Sha256};

use crate::{
    Error, MAX_PLAYERS, RULES_VERSION,
    handshake::{
        self, MAX_ACCEPTED_OFFERS_PER_MATCH, OFFER_PACKET_BYTES, PairwiseKeys,
        RESPONSE_PACKET_BYTES,
    },
    protocol::{
        BATCH_TICKS, CommitmentSet, Context, DeadlineResolution, Hash, MAX_ASSEMBLY_FRONTIERS,
        Phase, Reveal, SlotSignature, sign_commitment_set, validate_start,
    },
    rollback::{Checkpoint, RollbackSession},
    simulation::{Config, Input, Mode, Participant, World},
};

const MAGIC: &[u8] = b"SORA-ARENA-EVIDENCE\x03";
const MAX_RECORD: usize = 4096;
const MAX_FILE: u64 = 64 * 1024 * 1024;
/// Openings one grouped record may carry, across any pending frontiers.
pub const MAX_REVEAL_GROUP: usize = 64;
/// Ticks ahead of the certified frontier a peer may seal or endorse.
const ASSEMBLY_TICKS: u32 = (MAX_ASSEMBLY_FRONTIERS * BATCH_TICKS) as u32;

#[derive(Debug)]
pub enum RecoveryError {
    Io(std::io::Error),
    Evidence(Error),
    Corrupt(&'static str),
    Poisoned,
}
impl std::fmt::Display for RecoveryError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(e) => e.fmt(f),
            Self::Evidence(e) => e.fmt(f),
            Self::Corrupt(s) => f.write_str(s),
            Self::Poisoned => {
                f.write_str("journal write failed; reopen and reconcile before continuing")
            }
        }
    }
}
impl std::error::Error for RecoveryError {}
impl From<std::io::Error> for RecoveryError {
    fn from(e: std::io::Error) -> Self {
        Self::Io(e)
    }
}
impl From<Error> for RecoveryError {
    fn from(e: Error) -> Self {
        Self::Evidence(e)
    }
}
type Result<T> = std::result::Result<T, RecoveryError>;
type AcceptedOffers = Vec<Arc<BTreeSet<Hash>>>;

/// Keep this receipt outside the journal before relying on its latest frontier.
/// It authenticates byte retention, not a monetary outcome or chain finality.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Receipt {
    pub records: u32,
    pub digest: Hash,
}

/// Everything replay derives from the admission header and the records.
#[derive(Clone)]
struct JournalState {
    session: RollbackSession,
    accepted_offers: AcceptedOffers,
    resolution_fault: Option<Error>,
    /// This peer's own openings, journaled before their commitments left.
    sealed: BTreeMap<(u32, usize), Reveal>,
    /// The set digest this peer signed for each tick not yet certified.
    endorsed: BTreeMap<u32, Hash>,
}

impl JournalState {
    fn new(context: Context, config: Config, participants: &[Participant]) -> Result<Self> {
        Ok(Self {
            session: RollbackSession::new(context, config, participants)?,
            accepted_offers: (0..participants.len())
                .map(|_| Arc::new(BTreeSet::new()))
                .collect(),
            resolution_fault: None,
            sealed: BTreeMap::new(),
            endorsed: BTreeMap::new(),
        })
    }

    fn apply(&mut self, record: &Record) -> Result<()> {
        match record {
            Record::Certify(set, signatures) => {
                self.session.certify(set.clone(), signatures.clone())?
            }
            Record::Reveals(reveals) => {
                self.session.open(reveals.clone())?;
                self.advance();
            }
            Record::Deadline(resolution) => {
                self.session.attach_deadline(resolution)?;
                self.advance();
            }
            Record::Checkpoint(checkpoint, signatures) => self
                .session
                .retain_checkpoint(checkpoint.clone(), signatures.clone())?,
            Record::Interrupt => self.session.interrupt(),
            Record::Finish => self.session.finish_local()?,
            Record::HandshakeOffer {
                initiator,
                responder,
                offer,
            } => {
                // Accepted in every phase: a peer that restarts after this
                // one finished may still need its final checkpoint signature.
                let accepted = self
                    .accepted_offers
                    .get_mut(*responder)
                    .ok_or(Error::InvalidEvidence("handshake responder outside roster"))?;
                let digest = handshake::verified_offer_digest(
                    &self.session.evidence().context,
                    *initiator,
                    *responder,
                    offer,
                )?;
                if accepted.contains(&digest) {
                    return Err(Error::InvalidEvidence("handshake offer replay").into());
                }
                if accepted.len() == MAX_ACCEPTED_OFFERS_PER_MATCH {
                    return Err(Error::InvalidEvidence("handshake replay guard is full").into());
                }
                Arc::make_mut(accepted).insert(digest);
            }
            Record::Seal(opening) => self.seal(opening)?,
            Record::Endorse { start_tick, digest } => self.endorse(*start_tick, *digest)?,
        }
        let evidence = self.session.evidence();
        let (closed, certified) = (evidence.next_tick, evidence.certified_tick);
        self.sealed.retain(|(start, _), _| *start >= closed);
        self.endorsed.retain(|start, _| *start >= certified);
        Ok(())
    }

    fn advance(&mut self) {
        match self.session.advance() {
            Ok(()) => self.resolution_fault = None,
            Err(error) => {
                // Valid openings remain useful evidence even if the reference
                // cannot execute them. Native dispute resolution must decide
                // this; no local timeout may.
                self.session.interrupt();
                self.resolution_fault = Some(error);
            }
        }
    }

    fn seal(&mut self, opening: &Reveal) -> Result<()> {
        let evidence = self.session.evidence();
        if evidence.phase != Phase::Live {
            return Err(Error::InvalidEvidence("combat stopped; nothing new is committed").into());
        }
        let commitment = opening.commitment(&evidence.context, evidence.epoch)?;
        if opening.start_tick < evidence.next_tick
            || opening.start_tick >= evidence.certified_tick + ASSEMBLY_TICKS
        {
            return Err(Error::InvalidEvidence("sealed opening outside the pipeline").into());
        }
        if evidence
            .frontier(opening.start_tick)
            .is_some_and(|frontier| frontier.set.commitments[opening.slot] != commitment)
        {
            return Err(
                Error::InvalidEvidence("sealed opening differs from certified commitment").into(),
            );
        }
        if self
            .sealed
            .insert((opening.start_tick, opening.slot), opening.clone())
            .is_some()
        {
            return Err(Error::InvalidEvidence("slot already sealed for this tick").into());
        }
        Ok(())
    }

    fn endorse(&mut self, start_tick: u32, digest: Hash) -> Result<()> {
        let evidence = self.session.evidence();
        if evidence.phase != Phase::Live {
            return Err(Error::InvalidEvidence("combat stopped; nothing new is endorsed").into());
        }
        validate_start(start_tick)?;
        if start_tick < evidence.certified_tick
            || start_tick >= evidence.certified_tick + ASSEMBLY_TICKS
        {
            return Err(Error::InvalidEvidence("endorsement outside the assembly window").into());
        }
        if self.endorsed.insert(start_tick, digest).is_some() {
            return Err(Error::InvalidEvidence("tick already endorsed").into());
        }
        Ok(())
    }
}

/// Why inspection stopped after the last fully authenticated record.
#[derive(Debug)]
pub enum PrefixFailureKind {
    /// The first missing byte is `PrefixFailure::offset`.
    Truncated {
        expected_end: u64,
    },
    Framing(&'static str),
    /// Identifies the digest field, not the unknowable original changed byte.
    DigestMismatch,
    /// Decode or evidence verification failed in the indicated payload.
    InvalidRecord(RecoveryError),
}

/// All offsets are absolute, zero-based file byte offsets. A semantic failure
/// identifies the payload start; a digest mismatch identifies its digest field.
/// These locations must not be represented as the original tampered byte.
#[derive(Debug)]
pub struct PrefixFailure {
    pub record_offset: u64,
    pub offset: u64,
    pub kind: PrefixFailureKind,
}

/// Read-only dispute material. This object owns no file or writer capability.
/// A complete prefix is still local evidence, not a settlement or finality proof.
pub struct AuthenticatedPrefix {
    state: JournalState,
    receipt: Receipt,
    prefix_bytes: u64,
    file_bytes: u64,
    failure: Option<PrefixFailure>,
}

impl AuthenticatedPrefix {
    /// Pending frontiers and their retained openings are in the session's
    /// evidence log.
    pub fn session(&self) -> &RollbackSession {
        &self.state.session
    }
    pub fn sealed_openings(&self) -> impl Iterator<Item = &Reveal> {
        self.state.sealed.values()
    }
    pub fn endorsed_digest(&self, start_tick: u32) -> Option<Hash> {
        self.state.endorsed.get(&start_tick).copied()
    }
    /// Signed handshake offers durably accepted by one original responder slot.
    pub fn accepted_offer_digests(&self, responder: usize) -> Option<Vec<Hash>> {
        self.state
            .accepted_offers
            .get(responder)
            .map(|offers| offers.iter().copied().collect())
    }
    pub fn resolution_fault(&self) -> Option<&Error> {
        self.state.resolution_fault.as_ref()
    }
    pub fn receipt(&self) -> Receipt {
        self.receipt
    }
    /// Exclusive end of the last verified record (or exact admission header).
    pub fn prefix_bytes(&self) -> u64 {
        self.prefix_bytes
    }
    pub fn file_bytes(&self) -> u64 {
        self.file_bytes
    }
    pub fn failure(&self) -> Option<&PrefixFailure> {
        self.failure.as_ref()
    }
}

/// Inspect an authenticated prefix without repairing, truncating, or opening a
/// writer. The caller must supply independently authenticated admission and an
/// externally retained receipt. If that receipt is not in the verified prefix,
/// no prefix is returned. A cooperative writer's lock prevents concurrent reads.
///
/// A corruption after the minimum receipt is returned as explicit diagnostic
/// data. Its verified prefix may contain later valid records, but inspection
/// cannot establish that the file retains the latest agreed frontier.
pub fn inspect_prefix(
    path: &Path,
    context: Context,
    config: Config,
    participants: &[Participant],
    minimum: Receipt,
) -> Result<AuthenticatedPrefix> {
    let header = admission(&context, &config, participants)?;
    let mut file = File::open(path)?;
    file.try_lock_shared()
        .map_err(|e| RecoveryError::Io(e.into()))?;
    if file.metadata()?.len() > MAX_FILE {
        return Err(RecoveryError::Corrupt("journal exceeds bound"));
    }
    let mut bytes = Vec::new();
    Read::by_ref(&mut file)
        .take(MAX_FILE + 1)
        .read_to_end(&mut bytes)?;
    if bytes.len() as u64 > MAX_FILE || !bytes.starts_with(&header) {
        return Err(RecoveryError::Corrupt(
            "journal admission or format differs",
        ));
    }
    let mut result = AuthenticatedPrefix {
        state: JournalState::new(context, config, participants)?,
        receipt: Receipt {
            records: 0,
            digest: Sha256::digest(&header).into(),
        },
        prefix_bytes: header.len() as u64,
        file_bytes: bytes.len() as u64,
        failure: None,
    };
    let mut anchor_seen = result.receipt == minimum;
    while result.prefix_bytes < result.file_bytes {
        let start = result.prefix_bytes as usize;
        let (record, receipt, end) =
            match inspect_record(&bytes, start, result.receipt, participants.len()) {
                Ok(parsed) => parsed,
                Err(failure) => {
                    result.failure = Some(failure);
                    break;
                }
            };
        let mut state = result.state.clone();
        if let Err(error) = state.apply(&record) {
            result.failure = Some(PrefixFailure {
                record_offset: start as u64,
                offset: (start + 8) as u64,
                kind: PrefixFailureKind::InvalidRecord(error),
            });
            break;
        }
        result.state = state;
        result.receipt = receipt;
        result.prefix_bytes = end as u64;
        anchor_seen |= result.receipt == minimum;
    }
    if !anchor_seen {
        return Err(RecoveryError::Corrupt(
            "verified prefix does not retain trusted receipt",
        ));
    }
    Ok(result)
}

/// Framing diagnostics use the same canonical Record decoder as full restore.
fn inspect_record(
    bytes: &[u8],
    start: usize,
    previous: Receipt,
    count: usize,
) -> std::result::Result<(Record, Receipt, usize), PrefixFailure> {
    let failure = |offset: usize, kind| PrefixFailure {
        record_offset: start as u64,
        offset: offset as u64,
        kind,
    };
    let require = |end: usize| {
        if end > bytes.len() {
            Err(failure(
                bytes.len(),
                PrefixFailureKind::Truncated {
                    expected_end: end as u64,
                },
            ))
        } else {
            Ok(())
        }
    };
    require(start + 4)?;
    let sequence = u32::from_le_bytes(
        bytes[start..start + 4]
            .try_into()
            .expect("checked four bytes"),
    );
    if previous.records.checked_add(1) != Some(sequence) {
        return Err(failure(
            start,
            PrefixFailureKind::Framing("invalid record sequence"),
        ));
    }
    require(start + 8)?;
    let size = u32::from_le_bytes(
        bytes[start + 4..start + 8]
            .try_into()
            .expect("checked four bytes"),
    ) as usize;
    if size == 0 || size > MAX_RECORD {
        return Err(failure(
            start + 4,
            PrefixFailureKind::Framing("invalid record size"),
        ));
    }
    let digest_start = start + 8 + size;
    require(digest_start)?;
    let end = digest_start + 32;
    require(end)?;
    let payload = &bytes[start + 8..digest_start];
    let digest: Hash = bytes[digest_start..end]
        .try_into()
        .expect("checked digest bytes");
    if digest != record_hash(previous.digest, sequence, payload) {
        return Err(failure(digest_start, PrefixFailureKind::DigestMismatch));
    }
    let record = Record::decode(payload, count)
        .map_err(|e| failure(start + 8, PrefixFailureKind::InvalidRecord(e)))?;
    Ok((
        record,
        Receipt {
            records: sequence,
            digest,
        },
        end,
    ))
}

enum Record {
    Certify(CommitmentSet, Vec<SlotSignature>),
    Reveals(Vec<Reveal>),
    Checkpoint(Checkpoint, Vec<SlotSignature>),
    Interrupt,
    Finish,
    HandshakeOffer {
        initiator: usize,
        responder: usize,
        offer: [u8; OFFER_PACKET_BYTES],
    },
    Deadline(DeadlineResolution),
    Seal(Reveal),
    Endorse {
        start_tick: u32,
        digest: Hash,
    },
}

pub struct DurableSession {
    file: File,
    state: JournalState,
    receipt: Receipt,
    bytes: u64,
    poisoned: bool,
    /// Under group commit, the complete framed records accepted since the
    /// last hand-off to the writer.
    staged: Option<Vec<u8>>,
    /// The newest receipt whose record is written and synced.
    durable: Receipt,
}

/// Framed records accepted under group commit, oldest first, and the receipt
/// of the newest one. Write them in hand-off order.
#[derive(Debug)]
pub struct StagedRecords {
    bytes: Vec<u8>,
    receipt: Receipt,
}
impl StagedRecords {
    pub fn receipt(&self) -> Receipt {
        self.receipt
    }
    pub fn len(&self) -> usize {
        self.bytes.len()
    }
    pub fn is_empty(&self) -> bool {
        self.bytes.is_empty()
    }
}

/// The single writer of a journal under group commit. It may run on another
/// thread; it appends each hand-off with one write and one sync.
#[derive(Debug)]
pub struct GroupWriter {
    file: File,
}
impl GroupWriter {
    /// A failure may leave some of the bytes behind: the journal handle must
    /// be poisoned and the process restored from the file before continuing.
    pub fn write(&mut self, staged: &StagedRecords) -> Result<Receipt> {
        self.file.write_all(&staged.bytes)?;
        self.file.sync_all()?;
        Ok(staged.receipt)
    }
}

impl DurableSession {
    /// Creates a new file only. Admission must come from the independently
    /// authenticated lobby/chain adapter, including manifest and roster order.
    pub fn create(
        path: &Path,
        context: Context,
        config: Config,
        participants: &[Participant],
    ) -> Result<Self> {
        let header = admission(&context, &config, participants)?;
        let state = JournalState::new(context, config, participants)?;
        let mut file = OpenOptions::new()
            .read(true)
            .write(true)
            .create_new(true)
            .open(path)?;
        file.try_lock().map_err(|e| RecoveryError::Io(e.into()))?;
        file.write_all(&header)?;
        file.sync_all()?;
        // Unix directory fsync makes the newly created name durable as well.
        // Windows file sync is implemented by std; directory durability still
        // needs qualification on the shipping Windows filesystem/toolchain.
        #[cfg(unix)]
        File::open(
            path.parent()
                .filter(|p| !p.as_os_str().is_empty())
                .unwrap_or(Path::new(".")),
        )?
        .sync_all()?;
        let receipt = Receipt {
            records: 0,
            digest: Sha256::digest(&header).into(),
        };
        Ok(Self {
            file,
            state,
            receipt,
            bytes: header.len() as u64,
            poisoned: false,
            staged: None,
            durable: receipt,
        })
    }

    /// Replays every retained operation against the caller's exact admission.
    /// `minimum` is a previously trusted receipt, not a value read from this file.
    /// The file is never silently shortened or repaired on failure.
    pub fn restore(
        path: &Path,
        context: Context,
        config: Config,
        participants: &[Participant],
        minimum: Receipt,
    ) -> Result<Self> {
        let header = admission(&context, &config, participants)?;
        let mut file = OpenOptions::new().read(true).write(true).open(path)?;
        file.try_lock().map_err(|e| RecoveryError::Io(e.into()))?;
        if file.metadata()?.len() > MAX_FILE {
            return Err(RecoveryError::Corrupt("journal exceeds bound"));
        }
        let mut bytes = Vec::new();
        Read::by_ref(&mut file)
            .take(MAX_FILE + 1)
            .read_to_end(&mut bytes)?;
        if bytes.len() as u64 > MAX_FILE || !bytes.starts_with(&header) {
            return Err(RecoveryError::Corrupt(
                "journal admission or format differs",
            ));
        }
        let genesis = Receipt {
            records: 0,
            digest: Sha256::digest(&header).into(),
        };
        let mut result = Self {
            file,
            state: JournalState::new(context, config, participants)?,
            receipt: genesis,
            bytes: bytes.len() as u64,
            poisoned: false,
            staged: None,
            durable: genesis,
        };
        let mut anchor_seen = result.receipt == minimum;
        let mut r = Reader {
            bytes: &bytes[header.len()..],
        };
        while !r.bytes.is_empty() {
            let sequence = r.u32()?;
            let size = r.u32()? as usize;
            if sequence != result.receipt.records + 1 || size == 0 || size > MAX_RECORD {
                return Err(RecoveryError::Corrupt("invalid record sequence or size"));
            }
            let payload = r.take(size)?;
            let digest = r.array()?;
            if digest != record_hash(result.receipt.digest, sequence, payload) {
                return Err(RecoveryError::Corrupt("journal record digest mismatch"));
            }
            let record = Record::decode(payload, participants.len())?;
            result.state.apply(&record)?;
            result.receipt = Receipt {
                records: sequence,
                digest,
            };
            anchor_seen |= result.receipt == minimum;
        }
        if !anchor_seen {
            return Err(RecoveryError::Corrupt(
                "journal does not retain trusted receipt",
            ));
        }
        result.file.seek(SeekFrom::End(0))?;
        result.durable = result.receipt;
        Ok(result)
    }

    /// The newest accepted record. Under group commit it may not be durable
    /// yet; see [`Self::durable_receipt`].
    pub fn receipt(&self) -> Receipt {
        self.receipt
    }
    /// The newest record that is written and synced.
    pub fn durable_receipt(&self) -> Receipt {
        self.durable
    }

    /// Switch to group commit. Every later record is validated and applied at
    /// once but only buffered: [`Self::take_staged`] hands all buffered
    /// records to the returned writer, which writes and syncs them together,
    /// and [`Self::mark_durable`] then advances the durable receipt. Nothing
    /// that depends on a record may leave the process before it is durable.
    /// There is exactly one writer: a second call is refused.
    pub fn group_commit(&mut self) -> Result<GroupWriter> {
        if self.poisoned {
            return Err(RecoveryError::Poisoned);
        }
        if self.staged.is_some() {
            return Err(Error::InvalidConfig("journal already has a group writer").into());
        }
        let file = self.file.try_clone()?;
        self.staged = Some(Vec::new());
        Ok(GroupWriter { file })
    }
    /// Every record accepted since the last hand-off, or `None`. Hand off
    /// again only after the writer finished the previous one.
    pub fn take_staged(&mut self) -> Option<StagedRecords> {
        let staged = self.staged.as_mut().filter(|bytes| !bytes.is_empty())?;
        Some(StagedRecords {
            bytes: std::mem::take(staged),
            receipt: self.receipt,
        })
    }
    /// The writer synced every record through `receipt`.
    pub fn mark_durable(&mut self, receipt: Receipt) -> Result<()> {
        if self.poisoned {
            return Err(RecoveryError::Poisoned);
        }
        if receipt.records <= self.durable.records || receipt.records > self.receipt.records {
            return Err(RecoveryError::Corrupt("durable receipt out of order"));
        }
        self.durable = receipt;
        Ok(())
    }
    /// A group write failed: stop this handle. Restore from the file.
    pub fn poison(&mut self) {
        self.poisoned = true;
    }
    /// Pending frontiers and their retained openings are in the session's
    /// evidence log.
    pub fn session(&self) -> &RollbackSession {
        &self.state.session
    }
    /// This peer's own openings not yet closed into the transcript. After a
    /// restart, resend their commitments and open the certified ones.
    pub fn sealed_openings(&self) -> impl Iterator<Item = &Reveal> {
        self.state.sealed.values()
    }
    pub fn endorsed_digest(&self, start_tick: u32) -> Option<Hash> {
        self.state.endorsed.get(&start_tick).copied()
    }
    pub fn accepted_offer_digests(&self, responder: usize) -> Option<Vec<Hash>> {
        self.state
            .accepted_offers
            .get(responder)
            .map(|offers| offers.iter().copied().collect())
    }
    /// Complete openings stay available for dispute if reference execution fails.
    /// A recorded fault freezes gameplay and cannot release escrow or NFTs.
    pub fn resolution_fault(&self) -> Option<&Error> {
        self.state.resolution_fault.as_ref()
    }

    pub fn certify(
        &mut self,
        set: CommitmentSet,
        signatures: Vec<SlotSignature>,
    ) -> Result<Receipt> {
        self.append(Record::Certify(set, signatures))
    }
    /// Each valid reveal is durable even if another player withholds theirs.
    /// Retrying an opening the evidence already retains is idempotent.
    pub fn reveal(&mut self, reveal: Reveal) -> Result<Receipt> {
        self.reveal_many(vec![reveal])
    }
    /// Persist openings already received, for any pending frontiers, with one
    /// sync. Never wait for a withholding peer to fill a group; a singleton
    /// follows the same path.
    pub fn reveal_many(&mut self, reveals: Vec<Reveal>) -> Result<Receipt> {
        if self.poisoned {
            return Err(RecoveryError::Poisoned);
        }
        if reveals.is_empty() || reveals.len() > MAX_REVEAL_GROUP {
            return Err(Error::InvalidEvidence("invalid reveal group size").into());
        }
        for (i, reveal) in reveals.iter().enumerate() {
            if reveals[..i]
                .iter()
                .any(|r| (r.start_tick, r.slot) == (reveal.start_tick, reveal.slot))
            {
                return Err(Error::InvalidEvidence("duplicate grouped reveal").into());
            }
        }
        let evidence = self.state.session.evidence();
        let new = reveals
            .into_iter()
            .filter(|r| !evidence.retains(r))
            .collect::<Vec<_>>();
        if new.is_empty() {
            return Ok(self.receipt);
        }
        self.append(Record::Reveals(new))
    }
    /// Journal native consensus's deadline decision for one certified
    /// frontier. The caller's chain adapter must already have authenticated
    /// it; a local timeout can only `interrupt`.
    pub fn resolve_deadline(&mut self, resolution: DeadlineResolution) -> Result<Receipt> {
        self.append(Record::Deadline(resolution))
    }
    /// Journal this peer's own opening before its commitment leaves the
    /// process, so a restart can still open it, and return that commitment.
    /// Resealing the identical opening is idempotent; any other opening of
    /// the same slot and tick is refused, so a restart never equivocates.
    pub fn seal(&mut self, opening: Reveal) -> Result<(Hash, Receipt)> {
        if self.poisoned {
            return Err(RecoveryError::Poisoned);
        }
        let evidence = self.state.session.evidence();
        let commitment = opening.commitment(&evidence.context, evidence.epoch)?;
        if self.state.sealed.get(&(opening.start_tick, opening.slot)) == Some(&opening) {
            return Ok((commitment, self.receipt));
        }
        Ok((commitment, self.append(Record::Seal(opening))?))
    }
    /// Journal this peer's endorsement of `set` before returning its
    /// signature, so a restarted peer never signs a second set for one tick.
    /// Refused once combat has stopped, and for a set whose commitment for
    /// this slot differs from the sealed one.
    pub fn endorse(
        &mut self,
        set: &CommitmentSet,
        slot: usize,
        key: &SigningKey,
    ) -> Result<(SlotSignature, Receipt)> {
        if self.poisoned {
            return Err(RecoveryError::Poisoned);
        }
        let evidence = self.state.session.evidence();
        let signature = sign_commitment_set(&evidence.context, set, slot, key)?;
        let digest = set.digest(&evidence.context)?;
        if set.epoch != evidence.epoch
            || (set.start_tick == evidence.certified_tick && set.parent != evidence.commitment_head)
        {
            return Err(Error::InvalidEvidence("endorsed set leaves the commitment chain").into());
        }
        if let Some(sealed) = self.state.sealed.get(&(set.start_tick, slot))
            && sealed.commitment(&evidence.context, evidence.epoch)? != set.commitments[slot]
        {
            return Err(
                Error::InvalidEvidence("endorsed set differs from sealed commitment").into(),
            );
        }
        if self.state.endorsed.get(&set.start_tick) == Some(&digest) {
            return Ok((signature, self.receipt));
        }
        let receipt = self.append(Record::Endorse {
            start_tick: set.start_tick,
            digest,
        })?;
        Ok((signature, receipt))
    }
    pub fn checkpoint(
        &mut self,
        checkpoint: Checkpoint,
        signatures: Vec<SlotSignature>,
    ) -> Result<Receipt> {
        self.append(Record::Checkpoint(checkpoint, signatures))
    }
    pub fn interrupt(&mut self) -> Result<Receipt> {
        self.append(Record::Interrupt)
    }
    pub fn finish(&mut self) -> Result<Receipt> {
        self.append(Record::Finish)
    }
    /// Authenticates an admitted peer's ephemeral offer, then syncs the exact
    /// signed public bytes into this journal before returning keys or a
    /// response. Retain the returned receipt independently before transmitting
    /// that response so whole-suffix deletion is detectable on restart.
    /// A finished journal still accepts fresh offers, under the same replay
    /// guard and bound: a peer that restarted near the end of the match may
    /// still need this peer's final checkpoint signature.
    pub fn accept_handshake_offer(
        &mut self,
        initiator: usize,
        responder: usize,
        identity: &SigningKey,
        offer: &[u8],
    ) -> Result<(PairwiseKeys, [u8; RESPONSE_PACKET_BYTES], Receipt)> {
        if self.poisoned {
            return Err(RecoveryError::Poisoned);
        }
        let accepted = self
            .state
            .accepted_offers
            .get(responder)
            .ok_or(Error::InvalidEvidence("handshake responder outside roster"))?;
        let mut replay = handshake::OfferReplayGuard::restore(accepted.iter().copied())?;
        let (keys, response) = handshake::accept_offer(
            &self.state.session.evidence().context,
            initiator,
            responder,
            identity,
            offer,
            &mut replay,
        )?;
        let offer: [u8; OFFER_PACKET_BYTES] = offer
            .try_into()
            .map_err(|_| Error::InvalidEvidence("handshake offer length differs"))?;
        let receipt = self.append(Record::HandshakeOffer {
            initiator,
            responder,
            offer,
        })?;
        Ok((keys, response, receipt))
    }
    pub fn predict(&mut self, controls: Vec<Input>) -> Result<()> {
        if self.poisoned {
            return Err(RecoveryError::Poisoned);
        }
        self.state.session.predict(controls)?;
        Ok(())
    }

    fn append(&mut self, record: Record) -> Result<Receipt> {
        if self.poisoned {
            return Err(RecoveryError::Poisoned);
        }
        let mut state = self.state.clone();
        state.apply(&record)?;
        let payload = record.encode();
        let sequence = self
            .receipt
            .records
            .checked_add(1)
            .ok_or(RecoveryError::Corrupt("record count overflow"))?;
        let digest = record_hash(self.receipt.digest, sequence, &payload);
        let mut frame = sequence.to_le_bytes().to_vec();
        frame.extend((payload.len() as u32).to_le_bytes());
        frame.extend(payload);
        frame.extend(digest);
        if self.bytes + frame.len() as u64 > MAX_FILE {
            return Err(RecoveryError::Corrupt("journal exceeds bound"));
        }
        let receipt = Receipt {
            records: sequence,
            digest,
        };
        if let Some(staged) = &mut self.staged {
            staged.extend(&frame);
        } else {
            // A failed write/sync can have retained some or all of the new
            // bytes. Stop this handle; do not retry an evidence operation
            // blindly.
            self.poisoned = true;
            self.file.write_all(&frame)?;
            self.file.sync_all()?;
            self.poisoned = false;
            self.durable = receipt;
        }
        self.state = state;
        self.bytes += frame.len() as u64;
        self.receipt = receipt;
        Ok(self.receipt)
    }
}

fn admission(context: &Context, config: &Config, participants: &[Participant]) -> Result<Vec<u8>> {
    context.validate()?;
    let world = World::new(config.clone(), participants)?;
    if participants.len() != context.roster.len() {
        return Err(Error::InvalidConfig("admission roster mismatch").into());
    }
    let mut bytes = MAGIC.to_vec();
    bytes.extend((RULES_VERSION.len() as u16).to_le_bytes());
    bytes.extend(RULES_VERSION.as_bytes());
    bytes.extend(context.network);
    bytes.extend(context.session);
    bytes.extend(context.manifest);
    bytes.push(context.roster.len() as u8);
    for key in &context.roster {
        bytes.extend(key);
    }
    bytes.push(match config.mode {
        Mode::FreeForAll => 0,
        Mode::Control => 1,
        Mode::Payload => 2,
        Mode::Melee => 3,
    });
    bytes.push(config.map);
    bytes.extend(config.max_ticks.to_le_bytes());
    bytes.extend(config.base_bond.to_le_bytes());
    bytes.push(u8::from(config.offline));
    for p in participants {
        bytes.extend([p.team, p.class, p.weapon, u8::from(p.special_entitled)]);
        bytes.extend(p.bond.to_le_bytes());
    }
    bytes.extend(world.state_hash());
    Ok(bytes)
}

fn record_hash(parent: Hash, sequence: u32, payload: &[u8]) -> Hash {
    let mut hash = Sha256::new();
    hash.update(b"sora-arena:durable-record:v1\0");
    hash.update(parent);
    hash.update(sequence.to_le_bytes());
    hash.update((payload.len() as u32).to_le_bytes());
    hash.update(payload);
    hash.finalize().into()
}

impl Record {
    fn encode(&self) -> Vec<u8> {
        let mut out = Vec::new();
        match self {
            Self::Certify(set, signatures) => {
                out.push(0);
                out.extend(set.epoch.to_le_bytes());
                out.extend(set.start_tick.to_le_bytes());
                out.extend(set.parent);
                for commitment in &set.commitments {
                    out.extend(commitment);
                }
                encode_signatures(&mut out, signatures);
            }
            Self::Reveals(reveals) => {
                out.extend([1, reveals.len() as u8]);
                for reveal in reveals {
                    encode_opening(&mut out, reveal);
                }
            }
            Self::Checkpoint(checkpoint, signatures) => {
                out.push(2);
                out.extend(checkpoint.epoch.to_le_bytes());
                out.extend(checkpoint.tick.to_le_bytes());
                out.extend(checkpoint.history_root);
                out.extend(checkpoint.state_hash);
                encode_signatures(&mut out, signatures);
            }
            Self::Interrupt => out.push(3),
            Self::Finish => out.push(4),
            Self::HandshakeOffer {
                initiator,
                responder,
                offer,
            } => {
                out.extend([5, *initiator as u8, *responder as u8]);
                out.extend(offer);
            }
            Self::Deadline(resolution) => {
                out.push(6);
                out.extend(resolution.start_tick.to_le_bytes());
                out.extend(resolution.frontier);
                out.extend(resolution.attestation);
                let opened = resolution
                    .openings
                    .iter()
                    .enumerate()
                    .filter(|(_, opening)| opening.is_some())
                    .fold(0u16, |mask, (slot, _)| mask | 1 << slot);
                out.extend(opened.to_le_bytes());
                for opening in resolution.openings.iter().flatten() {
                    out.extend(opening.salt);
                    for input in &opening.inputs {
                        out.extend(input.encode());
                    }
                }
            }
            Self::Seal(opening) => {
                out.push(7);
                encode_opening(&mut out, opening);
            }
            Self::Endorse { start_tick, digest } => {
                out.push(8);
                out.extend(start_tick.to_le_bytes());
                out.extend(digest);
            }
        }
        out
    }
    fn decode(payload: &[u8], count: usize) -> Result<Self> {
        if !(1..=MAX_PLAYERS).contains(&count) {
            return Err(RecoveryError::Corrupt("invalid roster count"));
        }
        let mut r = Reader { bytes: payload };
        let record = match r.byte()? {
            0 => Self::Certify(
                CommitmentSet {
                    epoch: r.u64()?,
                    start_tick: r.u32()?,
                    parent: r.array()?,
                    commitments: (0..count).map(|_| r.array()).collect::<Result<_>>()?,
                },
                r.signatures(count)?,
            ),
            1 => {
                let group = r.byte()? as usize;
                if !(1..=MAX_REVEAL_GROUP).contains(&group) {
                    return Err(RecoveryError::Corrupt("invalid reveal group size"));
                }
                Self::Reveals(
                    (0..group)
                        .map(|_| r.opening(count))
                        .collect::<Result<_>>()?,
                )
            }
            2 => Self::Checkpoint(
                Checkpoint {
                    epoch: r.u64()?,
                    tick: r.u32()?,
                    history_root: r.array()?,
                    state_hash: r.array()?,
                },
                r.signatures(count)?,
            ),
            3 => Self::Interrupt,
            4 => Self::Finish,
            5 => Self::HandshakeOffer {
                initiator: r.byte()? as usize,
                responder: r.byte()? as usize,
                offer: r.array()?,
            },
            6 => {
                let start_tick = r.u32()?;
                let frontier = r.array()?;
                let attestation = r.array()?;
                let opened = r.u16()?;
                if u32::from(opened) >> count != 0 {
                    return Err(RecoveryError::Corrupt("deadline slot outside roster"));
                }
                let openings = (0..count)
                    .map(|slot| {
                        if opened & 1 << slot == 0 {
                            return Ok(None);
                        }
                        Ok(Some(Reveal {
                            start_tick,
                            slot,
                            salt: r.array()?,
                            inputs: r.inputs()?,
                        }))
                    })
                    .collect::<Result<_>>()?;
                Self::Deadline(DeadlineResolution {
                    start_tick,
                    frontier,
                    attestation,
                    openings,
                })
            }
            7 => Self::Seal(r.opening(count)?),
            8 => Self::Endorse {
                start_tick: r.u32()?,
                digest: r.array()?,
            },
            _ => return Err(RecoveryError::Corrupt("unknown record type")),
        };
        if !r.bytes.is_empty() {
            return Err(RecoveryError::Corrupt("trailing record bytes"));
        }
        Ok(record)
    }
}
fn encode_signatures(out: &mut Vec<u8>, signatures: &[SlotSignature]) {
    for signature in signatures {
        out.push(signature.slot as u8);
        out.extend(signature.signature);
    }
}
fn encode_opening(out: &mut Vec<u8>, opening: &Reveal) {
    out.extend(opening.start_tick.to_le_bytes());
    out.extend([opening.slot as u8, opening.inputs.len() as u8]);
    out.extend(opening.salt);
    for input in &opening.inputs {
        out.extend(input.encode());
    }
}
struct Reader<'a> {
    bytes: &'a [u8],
}
impl<'a> Reader<'a> {
    fn take(&mut self, count: usize) -> Result<&'a [u8]> {
        if self.bytes.len() < count {
            return Err(RecoveryError::Corrupt("truncated journal record"));
        }
        let (head, rest) = self.bytes.split_at(count);
        self.bytes = rest;
        Ok(head)
    }
    fn array<const N: usize>(&mut self) -> Result<[u8; N]> {
        Ok(self.take(N)?.try_into().expect("fixed length"))
    }
    fn byte(&mut self) -> Result<u8> {
        Ok(self.array::<1>()?[0])
    }
    fn u16(&mut self) -> Result<u16> {
        Ok(u16::from_le_bytes(self.array()?))
    }
    fn u32(&mut self) -> Result<u32> {
        Ok(u32::from_le_bytes(self.array()?))
    }
    fn u64(&mut self) -> Result<u64> {
        Ok(u64::from_le_bytes(self.array()?))
    }
    fn signatures(&mut self, count: usize) -> Result<Vec<SlotSignature>> {
        (0..count)
            .map(|_| {
                Ok(SlotSignature {
                    slot: self.byte()? as usize,
                    signature: self.array()?,
                })
            })
            .collect()
    }
    fn inputs(&mut self) -> Result<Vec<Input>> {
        (0..BATCH_TICKS)
            .map(|_| Ok(Input::decode(self.array()?)?))
            .collect()
    }
    fn opening(&mut self, count: usize) -> Result<Reveal> {
        let start_tick = self.u32()?;
        let slot = self.byte()? as usize;
        if slot >= count || self.byte()? as usize != BATCH_TICKS {
            return Err(RecoveryError::Corrupt("invalid reveal bounds"));
        }
        Ok(Reveal {
            start_tick,
            slot,
            salt: self.array()?,
            inputs: self.inputs()?,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{handshake::Initiator, protocol::sign_commitment_set};
    use ed25519_dalek::SigningKey;
    use std::{
        fs,
        path::PathBuf,
        sync::atomic::{AtomicU64, Ordering},
    };

    struct Fixture {
        path: PathBuf,
        context: Context,
        config: Config,
        participants: Vec<Participant>,
        keys: Vec<SigningKey>,
    }
    impl Fixture {
        fn new() -> Self {
            static NEXT: AtomicU64 = AtomicU64::new(0);
            let path = std::env::temp_dir().join(format!(
                "sora-arena-recovery-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
            let keys = vec![
                SigningKey::from_bytes(&[101; 32]),
                SigningKey::from_bytes(&[102; 32]),
            ];
            Self {
                path,
                context: Context {
                    network: [1; 32],
                    session: [2; 32],
                    manifest: [3; 32],
                    roster: keys.iter().map(|k| k.verifying_key().to_bytes()).collect(),
                },
                config: Config {
                    mode: Mode::FreeForAll,
                    map: 0,
                    max_ticks: 600,
                    base_bond: 1000,
                    offline: false,
                },
                participants: (0..2)
                    .map(|team| Participant {
                        team,
                        class: 0,
                        weapon: 1,
                        bond: 1000,
                        special_entitled: false,
                    })
                    .collect(),
                keys,
            }
        }
        fn create(&self) -> DurableSession {
            DurableSession::create(
                &self.path,
                self.context.clone(),
                self.config.clone(),
                &self.participants,
            )
            .unwrap()
        }
        fn restore(&self, minimum: Receipt) -> Result<DurableSession> {
            DurableSession::restore(
                &self.path,
                self.context.clone(),
                self.config.clone(),
                &self.participants,
                minimum,
            )
        }
        fn commit(&self, journal: &mut DurableSession) -> Vec<Reveal> {
            let log = journal.session().evidence();
            let reveals = (0..2)
                .map(|slot| Reveal {
                    start_tick: log.certified_tick,
                    slot,
                    inputs: vec![
                        Input {
                            move_x: 127,
                            ..Input::default()
                        };
                        2
                    ],
                    salt: [slot as u8 + 90; 32],
                })
                .collect::<Vec<_>>();
            let set = CommitmentSet {
                epoch: log.epoch,
                start_tick: log.certified_tick,
                parent: log.commitment_head,
                commitments: reveals
                    .iter()
                    .map(|r| r.commitment(&self.context, log.epoch).unwrap())
                    .collect(),
            };
            let signatures = self
                .keys
                .iter()
                .enumerate()
                .map(|(slot, key)| sign_commitment_set(&self.context, &set, slot, key).unwrap())
                .collect();
            journal.certify(set, signatures).unwrap();
            reveals
        }
        fn openings(&self, start_tick: u32) -> Vec<Reveal> {
            (0..2)
                .map(|slot| Reveal {
                    start_tick,
                    slot,
                    inputs: vec![
                        Input {
                            move_x: 127 - 254 * slot as i16,
                            ..Input::default()
                        };
                        BATCH_TICKS
                    ],
                    salt: [slot as u8 + start_tick as u8 + 50; 32],
                })
                .collect()
        }
        fn set(&self, openings: &[Reveal], parent: Hash) -> CommitmentSet {
            CommitmentSet {
                epoch: 0,
                start_tick: openings[0].start_tick,
                parent,
                commitments: openings
                    .iter()
                    .map(|r| r.commitment(&self.context, 0).unwrap())
                    .collect(),
            }
        }
        fn signatures(&self, set: &CommitmentSet) -> Vec<SlotSignature> {
            self.keys
                .iter()
                .enumerate()
                .map(|(slot, key)| sign_commitment_set(&self.context, set, slot, key).unwrap())
                .collect()
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.path);
        }
    }

    #[test]
    fn pipelined_frontiers_seals_and_endorsements_survive_restart() {
        let fixture = Fixture::new();
        let mut journal = fixture.create();
        let mut parent = journal.session().evidence().commitment_head;
        let mut batches = Vec::new();
        for start in [0, 2, 4] {
            let openings = fixture.openings(start);
            let (commitment, _) = journal.seal(openings[0].clone()).unwrap();
            let set = fixture.set(&openings, parent);
            assert_eq!(commitment, set.commitments[0]);
            let (signature, _) = journal.endorse(&set, 0, &fixture.keys[0]).unwrap();
            assert_eq!(signature, fixture.signatures(&set)[0]);
            parent = set.digest(&fixture.context).unwrap();
            batches.push((set, openings));
        }
        for (set, _) in &batches[..2] {
            journal
                .certify(set.clone(), fixture.signatures(set))
                .unwrap();
        }
        // Openings arrive out of order across both pending frontiers.
        journal
            .reveal_many(vec![batches[1].1[1].clone(), batches[0].1[1].clone()])
            .unwrap();
        assert_eq!(journal.session().confirmed().tick, 0);
        let receipt = journal.receipt();
        drop(journal);

        let mut journal = fixture.restore(receipt).unwrap();
        let evidence = journal.session().evidence();
        assert_eq!(evidence.pending.len(), 2);
        assert_eq!(evidence.certified_tick, 4);
        assert_eq!(
            evidence.pending[1].openings[1],
            Some(batches[1].1[1].clone())
        );
        assert_eq!(
            journal.sealed_openings().cloned().collect::<Vec<_>>(),
            batches
                .iter()
                .map(|(_, o)| o[0].clone())
                .collect::<Vec<_>>()
        );
        // Certification retired the endorsements of ticks 0 and 2.
        assert_eq!(journal.endorsed_digest(0), None);
        let pending_digest = batches[2].0.digest(&fixture.context).unwrap();
        assert_eq!(journal.endorsed_digest(4), Some(pending_digest));
        // A restarted peer never signs or seals a second version of a tick.
        let mut other = batches[2].0.clone();
        other.commitments[1] = [7; 32];
        assert!(journal.endorse(&other, 0, &fixture.keys[0]).is_err());
        let mut resealed = batches[2].1[0].clone();
        resealed.salt[0] ^= 1;
        assert!(journal.seal(resealed).is_err());
        let before = journal.receipt();
        journal.endorse(&batches[2].0, 0, &fixture.keys[0]).unwrap();
        journal.seal(batches[2].1[0].clone()).unwrap();
        assert_eq!(journal.receipt(), before);
        // Its own sealed openings still open the certified frontiers.
        let own = journal
            .sealed_openings()
            .filter(|opening| opening.start_tick < 4)
            .cloned()
            .collect::<Vec<_>>();
        journal.reveal_many(own).unwrap();
        assert_eq!(journal.session().confirmed().tick, 4);
        assert_eq!(journal.sealed_openings().count(), 1);
        let mut reference = World::new(fixture.config.clone(), &fixture.participants).unwrap();
        for (_, openings) in &batches[..2] {
            for tick in 0..BATCH_TICKS {
                reference
                    .step(&[openings[0].inputs[tick], openings[1].inputs[tick]])
                    .unwrap();
            }
        }
        assert_eq!(
            journal.session().confirmed().state_hash(),
            reference.state_hash()
        );
    }

    #[test]
    fn group_commit_applies_at_once_and_syncs_every_staged_record_together() {
        let fixture = Fixture::new();
        let mut journal = fixture.create();
        let genesis = journal.receipt();
        let mut writer = journal.group_commit().unwrap();
        assert!(journal.group_commit().is_err());
        let admitted_bytes = fs::metadata(&fixture.path).unwrap().len();
        let openings = fixture.openings(0);
        journal.seal(openings[0].clone()).unwrap();
        let set = fixture.set(&openings, journal.session().evidence().commitment_head);
        journal.endorse(&set, 0, &fixture.keys[0]).unwrap();
        journal
            .certify(set.clone(), fixture.signatures(&set))
            .unwrap();
        journal.reveal_many(openings.clone()).unwrap();
        // Applied and replay-checked at once, but nothing is written yet.
        assert_eq!(journal.receipt().records, 4);
        assert_eq!(journal.durable_receipt(), genesis);
        assert_eq!(journal.session().confirmed().tick, 2);
        assert_eq!(fs::metadata(&fixture.path).unwrap().len(), admitted_bytes);
        let staged = journal.take_staged().unwrap();
        assert!(journal.take_staged().is_none());
        assert_eq!(staged.receipt(), journal.receipt());
        assert!(journal.mark_durable(genesis).is_err());
        let durable = writer.write(&staged).unwrap();
        journal.mark_durable(durable).unwrap();
        assert_eq!(journal.durable_receipt(), journal.receipt());
        assert!(journal.mark_durable(durable).is_err());
        // A record accepted after the last hand-off is lost with the process,
        // like any unsynced write; nothing may have depended on it.
        let lost = journal.interrupt().unwrap();
        assert_eq!(journal.durable_receipt(), durable);
        let state = journal.session().confirmed().state_hash();
        drop(journal);
        drop(writer);
        assert!(fixture.restore(lost).is_err());
        let restored = fixture.restore(durable).unwrap();
        assert_eq!(restored.receipt(), durable);
        assert_eq!(restored.durable_receipt(), durable);
        assert_eq!(restored.session().confirmed().state_hash(), state);
        assert_eq!(restored.session().evidence().phase, Phase::Live);
    }

    #[test]
    fn consensus_deadline_is_journaled_and_replayed_exactly() {
        let fixture = Fixture::new();
        let mut journal = fixture.create();
        let first = fixture.commit(&mut journal);
        let second = fixture.commit(&mut journal);
        journal.reveal(first[0].clone()).unwrap();
        // The later frontier is complete but waits for the withheld one.
        journal.reveal_many(second).unwrap();
        assert_eq!(journal.session().confirmed().tick, 0);
        // A local timeout only interrupts; it cannot close the frontier.
        journal.interrupt().unwrap();
        assert!(journal.finish().is_err());
        let resolution = DeadlineResolution {
            start_tick: 0,
            frontier: journal.session().evidence().pending[0].digest,
            attestation: [5; 32],
            openings: vec![Some(first[0].clone()), None],
        };
        let before = journal.receipt();
        let mut unattested = resolution.clone();
        unattested.attestation = [0; 32];
        assert!(journal.resolve_deadline(unattested).is_err());
        assert_eq!(journal.receipt(), before);
        journal.resolve_deadline(resolution).unwrap();
        assert_eq!(journal.session().confirmed().tick, 4);
        assert!(journal.reveal(first[1].clone()).is_err());
        let receipt = journal.finish().unwrap();
        let outcome = journal.session().terminal_outcome().unwrap();
        assert_eq!(outcome.deadline_frontiers, 1);
        assert!(!outcome.completed);
        drop(journal);
        let restored = fixture.restore(receipt).unwrap();
        assert_eq!(restored.session().terminal_outcome(), Some(outcome));
        let batch = restored.session().evidence().batches.get(0).unwrap();
        assert_eq!(batch.deadline, Some([5; 32]));
        assert!(batch.openings[1].is_none());
    }

    #[test]
    fn a_stopped_match_seals_and_endorses_nothing_new() {
        let fixture = Fixture::new();
        let mut journal = fixture.create();
        let openings = fixture.openings(0);
        let set = fixture.set(&openings, journal.session().evidence().commitment_head);
        journal.interrupt().unwrap();
        let before = journal.receipt();
        assert!(journal.seal(openings[0].clone()).is_err());
        assert!(journal.endorse(&set, 0, &fixture.keys[0]).is_err());
        assert_eq!(journal.receipt(), before);
        // A certificate completed before the dropout is still evidence.
        journal
            .certify(set.clone(), fixture.signatures(&set))
            .unwrap();
        journal.reveal_many(openings).unwrap();
        assert_eq!(journal.session().confirmed().tick, 2);
        journal.finish().unwrap();
    }

    #[test]
    fn worst_case_full_match_journal_fits_the_file_bound() {
        let keys = (0..MAX_PLAYERS)
            .map(|slot| SigningKey::from_bytes(&[slot as u8 + 1; 32]))
            .collect::<Vec<_>>();
        let context = Context {
            network: [1; 32],
            session: [2; 32],
            manifest: [3; 32],
            roster: keys.iter().map(|k| k.verifying_key().to_bytes()).collect(),
        };
        let config = Config {
            mode: Mode::Control,
            map: 0,
            max_ticks: crate::MAX_TICKS,
            base_bond: 1000,
            offline: false,
        };
        let participants = (0..MAX_PLAYERS)
            .map(|slot| Participant {
                team: (slot % 2) as u8,
                class: 0,
                weapon: 1,
                bond: 1000,
                special_entitled: false,
            })
            .collect::<Vec<_>>();
        let header = admission(&context, &config, &participants).unwrap().len();
        let framed = |record: Record| 8 + record.encode().len() + 32;
        let opening = Reveal {
            start_tick: 0,
            slot: 0,
            inputs: vec![Input::default(); BATCH_TICKS],
            salt: [0; 32],
        };
        let signatures = (0..MAX_PLAYERS)
            .map(|slot| SlotSignature {
                slot,
                signature: [0; 64],
            })
            .collect::<Vec<_>>();
        let set = CommitmentSet {
            epoch: 0,
            start_tick: 0,
            parent: [0; 32],
            commitments: vec![[0; 32]; MAX_PLAYERS],
        };
        let checkpoint = Checkpoint {
            epoch: 0,
            tick: 0,
            history_root: [0; 32],
            state_hash: [0; 32],
        };
        // One certificate, twelve separate openings, a full checkpoint, and
        // this peer's seal and endorsement, for every batch of the match.
        let batch = framed(Record::Certify(set, signatures.clone()))
            + MAX_PLAYERS * framed(Record::Reveals(vec![opening.clone()]))
            + framed(Record::Checkpoint(checkpoint, signatures))
            + framed(Record::Seal(opening.clone()))
            + framed(Record::Endorse {
                start_tick: 0,
                digest: [0; 32],
            });
        assert_eq!(batch, 3_470);
        assert_eq!(
            framed(Record::Reveals(vec![opening.clone(); MAX_PLAYERS])),
            690
        );
        let mut forfeiting = vec![Some(opening); MAX_PLAYERS];
        forfeiting[0] = None;
        let deadlines = crate::protocol::MAX_OUTSTANDING_FRONTIERS
            * framed(Record::Deadline(DeadlineResolution {
                start_tick: 0,
                frontier: [0; 32],
                attestation: [1; 32],
                openings: forfeiting,
            }));
        let offers = MAX_ACCEPTED_OFFERS_PER_MATCH
            * MAX_PLAYERS
            * framed(Record::HandshakeOffer {
                initiator: 0,
                responder: 1,
                offer: [0; OFFER_PACKET_BYTES],
            });
        let total = header
            + crate::protocol::MAX_BATCHES * batch
            + deadlines
            + offers
            + framed(Record::Interrupt)
            + framed(Record::Finish);
        assert!(total as u64 <= MAX_FILE, "{total} bytes");
    }

    #[test]
    fn restart_retains_partial_reveals_and_resolves_without_a_final_signature() {
        let fixture = Fixture::new();
        let mut journal = fixture.create();
        let reveals = fixture.commit(&mut journal);
        journal
            .predict(vec![
                Input {
                    move_x: -127,
                    ..Input::default()
                };
                2
            ])
            .unwrap();
        journal.reveal(reveals[1].clone()).unwrap();
        let before_retry = journal.receipt();
        assert_eq!(journal.reveal(reveals[1].clone()).unwrap(), before_retry);
        let mut forged = reveals[0].clone();
        forged.inputs[0].buttons = 1;
        assert!(journal.reveal(forged).is_err());
        assert_eq!(journal.receipt(), before_retry);
        let minimum = journal.interrupt().unwrap();
        assert!(journal.finish().is_err());
        assert_eq!(journal.session().predicted().tick, 0);
        drop(journal);
        let mut recovered = fixture.restore(minimum).unwrap();
        let pending = &recovered.session().evidence().pending;
        assert_eq!(pending[0].openings[1], Some(reveals[1].clone()));
        assert_eq!(recovered.session().evidence().phase, Phase::Resolving);
        assert_eq!(pending.len(), 1);
        recovered.reveal(reveals[0].clone()).unwrap();
        assert_eq!(recovered.session().confirmed().tick, 2);
        assert!(recovered.session().evidence().pending.is_empty());
        let checkpoint = recovered.session().checkpoint();
        let signatures = fixture
            .keys
            .iter()
            .enumerate()
            .map(|(slot, key)| checkpoint.sign(&fixture.context, slot, key).unwrap())
            .collect();
        recovered
            .checkpoint(checkpoint.clone(), signatures)
            .unwrap();
        let final_receipt = recovered.finish().unwrap();
        let final_hash = recovered.session().confirmed().state_hash();
        drop(recovered);
        let recovered = fixture.restore(final_receipt).unwrap();
        assert_eq!(recovered.session().evidence().phase, Phase::Terminal);
        assert_eq!(recovered.session().confirmed().state_hash(), final_hash);
        assert_eq!(
            recovered.session().last_checkpoint().unwrap().checkpoint,
            checkpoint
        );
    }

    #[test]
    fn corrupt_torn_and_rolled_back_journals_fail_without_rewriting_evidence() {
        let fixture = Fixture::new();
        let mut journal = fixture.create();
        let minimum = journal.receipt();
        let prefix = fs::read(&fixture.path).unwrap();
        let reveals = fixture.commit(&mut journal);
        journal.reveal(reveals[0].clone()).unwrap();
        let latest = journal.receipt();
        drop(journal);
        let pristine = fs::read(&fixture.path).unwrap();
        for removed in [1, 17, 32, 40] {
            let truncated = &pristine[..pristine.len() - removed];
            fs::write(&fixture.path, truncated).unwrap();
            assert!(fixture.restore(minimum).is_err());
            assert_eq!(fs::read(&fixture.path).unwrap(), truncated);
        }
        let mut corrupt = pristine;
        corrupt[prefix.len() + 20] ^= 1;
        fs::write(&fixture.path, &corrupt).unwrap();
        assert!(fixture.restore(minimum).is_err());
        assert_eq!(fs::read(&fixture.path).unwrap(), corrupt);
        fs::write(&fixture.path, prefix).unwrap();
        assert!(fixture.restore(latest).is_err());
        assert!(fixture.restore(minimum).is_ok());
    }

    #[test]
    fn exact_admission_and_single_writer_are_required() {
        let fixture = Fixture::new();
        let journal = fixture.create();
        let receipt = journal.receipt();
        assert!(fixture.restore(receipt).is_err());
        assert!(
            DurableSession::create(
                &fixture.path,
                fixture.context.clone(),
                fixture.config.clone(),
                &fixture.participants
            )
            .is_err()
        );
        drop(journal);
        let mut wrong_context = fixture.context.clone();
        wrong_context.network[0] ^= 1;
        assert!(
            DurableSession::restore(
                &fixture.path,
                wrong_context,
                fixture.config.clone(),
                &fixture.participants,
                receipt
            )
            .is_err()
        );
        let mut wrong_config = fixture.config.clone();
        wrong_config.map = 1;
        assert!(
            DurableSession::restore(
                &fixture.path,
                fixture.context.clone(),
                wrong_config,
                &fixture.participants,
                receipt
            )
            .is_err()
        );
        let mut wrong_equipment = fixture.participants.clone();
        wrong_equipment[0].weapon = 0;
        assert!(
            DurableSession::restore(
                &fixture.path,
                fixture.context.clone(),
                fixture.config.clone(),
                &wrong_equipment,
                receipt
            )
            .is_err()
        );
        assert!(fixture.restore(receipt).is_ok());
    }

    #[test]
    fn recomputed_record_hash_cannot_authenticate_a_forged_signature() {
        let fixture = Fixture::new();
        let mut journal = fixture.create();
        let initial = journal.receipt();
        let prefix = fs::metadata(&fixture.path).unwrap().len() as usize;
        fixture.commit(&mut journal);
        drop(journal);
        let mut bytes = fs::read(&fixture.path).unwrap();
        let size = u32::from_le_bytes(bytes[prefix + 4..prefix + 8].try_into().unwrap()) as usize;
        // Certificate payload: tag + epoch + start tick + parent + 2 commitments + slot.
        bytes[prefix + 8 + 1 + 8 + 4 + 32 + 64 + 1] ^= 1;
        let digest = record_hash(initial.digest, 1, &bytes[prefix + 8..prefix + 8 + size]);
        bytes[prefix + 8 + size..].copy_from_slice(&digest);
        fs::write(&fixture.path, bytes).unwrap();
        assert!(matches!(
            fixture.restore(initial),
            Err(RecoveryError::Evidence(_))
        ));
    }

    #[test]
    fn grouped_reveals_are_atomic_and_may_include_an_exact_retained_retry() {
        let fixture = Fixture::new();
        let mut journal = fixture.create();
        let reveals = fixture.commit(&mut journal);
        let before = journal.receipt();
        let size = fs::metadata(&fixture.path).unwrap().len();
        let mut forged = reveals.clone();
        forged[1].salt[0] ^= 1;
        assert!(journal.reveal_many(forged).is_err());
        assert_eq!(journal.receipt(), before);
        assert_eq!(fs::metadata(&fixture.path).unwrap().len(), size);
        assert!(
            journal.session().evidence().pending[0]
                .openings
                .iter()
                .all(Option::is_none)
        );
        assert!(
            journal
                .reveal_many(vec![reveals[0].clone(), reveals[0].clone()])
                .is_err()
        );
        journal.reveal(reveals[0].clone()).unwrap();
        let receipt = journal.reveal_many(reveals).unwrap();
        let expected = journal.session().confirmed().state_hash();
        assert_eq!(journal.session().confirmed().tick, 2);
        drop(journal);
        assert_eq!(
            fixture
                .restore(receipt)
                .unwrap()
                .session()
                .confirmed()
                .state_hash(),
            expected
        );
    }

    #[test]
    fn accepted_handshake_offer_survives_restart_and_trusted_receipt_detects_rollback() {
        let fixture = Fixture::new();
        let mut journal = fixture.create();
        let initial = journal.receipt();
        let header_only = fs::read(&fixture.path).unwrap();
        let (initiator, offer) =
            Initiator::start(fixture.context.clone(), 0, 1, &fixture.keys[0]).unwrap();
        let (responder_keys, response, accepted) = journal
            .accept_handshake_offer(0, 1, &fixture.keys[1], &offer)
            .unwrap();
        let initiator_keys = initiator.finish(&response).unwrap();
        assert_eq!(
            responder_keys.channel_binding,
            initiator_keys.channel_binding
        );
        assert_eq!(journal.accepted_offer_digests(1).unwrap().len(), 1);
        assert!(
            journal
                .accept_handshake_offer(0, 1, &fixture.keys[1], &offer)
                .is_err()
        );
        assert_eq!(journal.receipt(), accepted);
        drop(journal);

        let saved = fs::read(&fixture.path).unwrap();
        let prefix = inspect_prefix(
            &fixture.path,
            fixture.context.clone(),
            fixture.config.clone(),
            &fixture.participants,
            initial,
        )
        .unwrap();
        assert_eq!(prefix.receipt(), accepted);
        assert_eq!(prefix.accepted_offer_digests(1).unwrap().len(), 1);
        let mut recovered = fixture.restore(accepted).unwrap();
        assert_eq!(recovered.accepted_offer_digests(1).unwrap().len(), 1);
        assert!(
            recovered
                .accept_handshake_offer(0, 1, &fixture.keys[1], &offer)
                .is_err()
        );
        let (fresh, new_offer) =
            Initiator::start(fixture.context.clone(), 0, 1, &fixture.keys[0]).unwrap();
        let (_, answer, later) = recovered
            .accept_handshake_offer(0, 1, &fixture.keys[1], &new_offer)
            .unwrap();
        fresh.finish(&answer).unwrap();
        assert_eq!(recovered.accepted_offer_digests(1).unwrap().len(), 2);
        drop(recovered);
        assert_eq!(
            fixture
                .restore(later)
                .unwrap()
                .accepted_offer_digests(1)
                .unwrap()
                .len(),
            2
        );

        fs::write(&fixture.path, &header_only).unwrap();
        assert!(fixture.restore(accepted).is_err());
        assert!(fixture.restore(initial).is_ok());
        fs::write(&fixture.path, saved).unwrap();
        let mut recovered = fixture.restore(accepted).unwrap();
        assert_eq!(recovered.accepted_offer_digests(1).unwrap().len(), 1);
        recovered.interrupt().unwrap();
        recovered.finish().unwrap();
        let terminal = recovered.receipt();
        // A finished journal still refuses a replay, but answers a fresh
        // offer from a peer that restarted after it finished.
        assert!(
            recovered
                .accept_handshake_offer(0, 1, &fixture.keys[1], &offer)
                .is_err()
        );
        assert_eq!(recovered.receipt(), terminal);
        let (late, late_offer) =
            Initiator::start(fixture.context.clone(), 0, 1, &fixture.keys[0]).unwrap();
        let (responder_keys, answer, after_finish) = recovered
            .accept_handshake_offer(0, 1, &fixture.keys[1], &late_offer)
            .unwrap();
        assert_eq!(
            late.finish(&answer).unwrap().channel_binding,
            responder_keys.channel_binding
        );
        assert_eq!(after_finish.records, terminal.records + 1);
        drop(recovered);
        let restored = fixture.restore(after_finish).unwrap();
        assert_eq!(restored.session().evidence().phase, Phase::Terminal);
        assert_eq!(restored.accepted_offer_digests(1).unwrap().len(), 2);
    }

    #[test]
    fn retained_handshake_signature_is_reverified_after_record_hash_recomputed() {
        let fixture = Fixture::new();
        let mut journal = fixture.create();
        let initial = journal.receipt();
        let start = fs::metadata(&fixture.path).unwrap().len() as usize;
        let (_, offer) = Initiator::start(fixture.context.clone(), 0, 1, &fixture.keys[0]).unwrap();
        let before = journal.receipt();
        let size_before = fs::metadata(&fixture.path).unwrap().len();
        let mut tampered = offer;
        *tampered.last_mut().unwrap() ^= 1;
        assert!(
            journal
                .accept_handshake_offer(0, 1, &fixture.keys[1], &tampered)
                .is_err()
        );
        assert_eq!(journal.receipt(), before);
        assert_eq!(fs::metadata(&fixture.path).unwrap().len(), size_before);
        journal
            .accept_handshake_offer(0, 1, &fixture.keys[1], &offer)
            .unwrap();
        drop(journal);

        let mut bytes = fs::read(&fixture.path).unwrap();
        let size = u32::from_le_bytes(bytes[start + 4..start + 8].try_into().unwrap()) as usize;
        assert_eq!(size, 3 + OFFER_PACKET_BYTES);
        bytes[start + 8 + size - 1] ^= 1;
        let digest = record_hash(initial.digest, 1, &bytes[start + 8..start + 8 + size]);
        bytes[start + 8 + size..].copy_from_slice(&digest);
        fs::write(&fixture.path, &bytes).unwrap();
        assert!(matches!(
            fixture.restore(initial),
            Err(RecoveryError::Evidence(_))
        ));
        assert_eq!(fs::read(&fixture.path).unwrap(), bytes);
    }
}

#[cfg(test)]
mod prefix_inspection_tests {
    use super::*;
    use crate::protocol::sign_commitment_set;
    use ed25519_dalek::SigningKey;
    use std::{
        fs,
        path::PathBuf,
        sync::atomic::{AtomicU64, Ordering},
    };

    struct Fixture {
        path: PathBuf,
        context: Context,
        config: Config,
        participants: Vec<Participant>,
        keys: Vec<SigningKey>,
    }
    impl Fixture {
        fn new() -> Self {
            static NEXT: AtomicU64 = AtomicU64::new(0);
            let keys = vec![
                SigningKey::from_bytes(&[121; 32]),
                SigningKey::from_bytes(&[122; 32]),
            ];
            Self {
                path: std::env::temp_dir().join(format!(
                    "sora-arena-prefix-{}-{}",
                    std::process::id(),
                    NEXT.fetch_add(1, Ordering::Relaxed)
                )),
                context: Context {
                    network: [11; 32],
                    session: [12; 32],
                    manifest: [13; 32],
                    roster: keys.iter().map(|k| k.verifying_key().to_bytes()).collect(),
                },
                config: Config {
                    mode: Mode::FreeForAll,
                    map: 0,
                    max_ticks: 600,
                    base_bond: 1000,
                    offline: false,
                },
                participants: (0..2)
                    .map(|team| Participant {
                        team,
                        class: 0,
                        weapon: 1,
                        bond: 1000,
                        special_entitled: false,
                    })
                    .collect(),
                keys,
            }
        }
        fn create(&self) -> DurableSession {
            DurableSession::create(
                &self.path,
                self.context.clone(),
                self.config.clone(),
                &self.participants,
            )
            .unwrap()
        }
        fn inspect(&self, minimum: Receipt) -> Result<AuthenticatedPrefix> {
            inspect_prefix(
                &self.path,
                self.context.clone(),
                self.config.clone(),
                &self.participants,
                minimum,
            )
        }
        fn batch(
            &self,
            receipt: &DurableSession,
        ) -> (CommitmentSet, Vec<SlotSignature>, Vec<Reveal>) {
            let evidence = receipt.session().evidence();
            let reveals = (0..2)
                .map(|slot| Reveal {
                    start_tick: evidence.certified_tick,
                    slot,
                    inputs: vec![Input::default(); crate::protocol::BATCH_TICKS],
                    salt: [slot as u8 + 70; 32],
                })
                .collect::<Vec<_>>();
            let set = CommitmentSet {
                epoch: evidence.epoch,
                start_tick: evidence.certified_tick,
                parent: evidence.commitment_head,
                commitments: reveals
                    .iter()
                    .map(|r| r.commitment(&self.context, evidence.epoch).unwrap())
                    .collect(),
            };
            let signatures = self
                .keys
                .iter()
                .enumerate()
                .map(|(slot, key)| sign_commitment_set(&self.context, &set, slot, key).unwrap())
                .collect();
            (set, signatures, reveals)
        }
        fn append_payload(&self, previous: Receipt, payload: &[u8]) -> Receipt {
            let sequence = previous.records + 1;
            let digest = record_hash(previous.digest, sequence, payload);
            let mut file = OpenOptions::new().append(true).open(&self.path).unwrap();
            file.write_all(&sequence.to_le_bytes()).unwrap();
            file.write_all(&(payload.len() as u32).to_le_bytes())
                .unwrap();
            file.write_all(payload).unwrap();
            file.write_all(&digest).unwrap();
            Receipt {
                records: sequence,
                digest,
            }
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.path);
        }
    }

    #[test]
    fn complete_inspection_is_read_only_and_retains_pending_openings() {
        let fixture = Fixture::new();
        let mut journal = fixture.create();
        let initial = journal.receipt();
        assert!(matches!(
            fixture.inspect(initial),
            Err(RecoveryError::Io(_))
        ));
        let (set, signatures, reveals) = fixture.batch(&journal);
        journal.certify(set, signatures).unwrap();
        let latest = journal.reveal(reveals[1].clone()).unwrap();
        drop(journal);
        let bytes = fs::read(&fixture.path).unwrap();
        let prefix = fixture.inspect(initial).unwrap();
        assert!(prefix.failure().is_none());
        assert_eq!(prefix.receipt(), latest);
        assert_eq!(prefix.prefix_bytes(), bytes.len() as u64);
        assert_eq!(prefix.file_bytes(), bytes.len() as u64);
        let pending = &prefix.session().evidence().pending;
        assert_eq!(pending[0].openings[1], Some(reveals[1].clone()));
        assert!(pending[0].openings[0].is_none());
        assert_eq!(prefix.session().confirmed().tick, 0);
        assert!(prefix.resolution_fault().is_none());
        assert_eq!(fs::read(&fixture.path).unwrap(), bytes);
        // Inspection retains no lock or writable handle after returning.
        let restored = DurableSession::restore(
            &fixture.path,
            fixture.context.clone(),
            fixture.config.clone(),
            &fixture.participants,
            latest,
        )
        .unwrap();
        assert_eq!(restored.receipt(), latest);
    }

    #[test]
    fn every_torn_final_record_preserves_the_anchored_prefix_and_exact_missing_offset() {
        let fixture = Fixture::new();
        let mut journal = fixture.create();
        let (set, signatures, reveals) = fixture.batch(&journal);
        journal.certify(set, signatures).unwrap();
        let minimum = journal.reveal(reveals[0].clone()).unwrap();
        let start = fs::metadata(&fixture.path).unwrap().len() as usize;
        let latest = journal.reveal(reveals[1].clone()).unwrap();
        let expected = journal.session().confirmed().state_hash();
        drop(journal);
        let pristine = fs::read(&fixture.path).unwrap();
        for end in start..pristine.len() {
            let truncated = &pristine[..end];
            fs::write(&fixture.path, truncated).unwrap();
            let prefix = fixture.inspect(minimum).unwrap();
            assert_eq!(prefix.receipt(), minimum);
            assert_eq!(prefix.prefix_bytes(), start as u64);
            assert_eq!(prefix.file_bytes(), end as u64);
            let openings = &prefix.session().evidence().pending[0].openings;
            assert_eq!(openings[0], Some(reveals[0].clone()));
            assert!(openings[1].is_none());
            assert_eq!(prefix.session().confirmed().tick, 0);
            if end == start {
                assert!(prefix.failure().is_none());
            } else {
                let failure = prefix.failure().unwrap();
                assert_eq!(failure.record_offset, start as u64);
                assert_eq!(failure.offset, end as u64);
                assert!(
                    matches!(failure.kind, PrefixFailureKind::Truncated { expected_end } if expected_end > end as u64)
                );
            }
            assert!(fixture.inspect(latest).is_err());
            assert_eq!(fs::read(&fixture.path).unwrap(), truncated);
        }
        fs::write(&fixture.path, &pristine).unwrap();
        let complete = fixture.inspect(latest).unwrap();
        assert!(complete.failure().is_none());
        assert_eq!(complete.session().confirmed().state_hash(), expected);
        assert!(complete.session().evidence().pending.is_empty());
    }

    #[test]
    fn digest_and_semantic_failures_report_boundaries_without_partial_group_mutation() {
        let fixture = Fixture::new();
        let mut journal = fixture.create();
        let (set, signatures, mut reveals) = fixture.batch(&journal);
        let minimum = journal.certify(set, signatures).unwrap();
        drop(journal);
        let prefix_bytes = fs::read(&fixture.path).unwrap();
        let start = prefix_bytes.len();
        reveals[1].salt[0] ^= 1;
        let payload = Record::Reveals(reveals).encode();
        let forged_receipt = fixture.append_payload(minimum, &payload);
        let forged = fs::read(&fixture.path).unwrap();
        let inspected = fixture.inspect(minimum).unwrap();
        assert_eq!(inspected.prefix_bytes(), start as u64);
        let pending = &inspected.session().evidence().pending;
        assert!(pending[0].openings.iter().all(Option::is_none));
        let failure = inspected.failure().unwrap();
        assert_eq!(failure.record_offset, start as u64);
        assert_eq!(failure.offset, (start + 8) as u64);
        assert!(matches!(
            failure.kind,
            PrefixFailureKind::InvalidRecord(RecoveryError::Evidence(_))
        ));
        assert!(fixture.inspect(forged_receipt).is_err());
        assert_eq!(fs::read(&fixture.path).unwrap(), forged);
        let mut corrupt = forged;
        corrupt[start + 8] ^= 1;
        fs::write(&fixture.path, &corrupt).unwrap();
        let inspected = fixture.inspect(minimum).unwrap();
        let failure = inspected.failure().unwrap();
        assert_eq!(failure.offset, (start + 8 + payload.len()) as u64);
        assert!(matches!(failure.kind, PrefixFailureKind::DigestMismatch));
        assert_eq!(fs::read(&fixture.path).unwrap(), corrupt);
    }

    #[test]
    fn rehashed_forged_certificate_cannot_enter_prefix_or_satisfy_external_anchor() {
        let fixture = Fixture::new();
        let journal = fixture.create();
        let minimum = journal.receipt();
        let (set, mut signatures, _) = fixture.batch(&journal);
        let header_end = fs::metadata(&fixture.path).unwrap().len();
        drop(journal);
        signatures[0].signature[0] ^= 1;
        let forged_receipt =
            fixture.append_payload(minimum, &Record::Certify(set, signatures).encode());
        let pristine = fs::read(&fixture.path).unwrap();
        let prefix = fixture.inspect(minimum).unwrap();
        assert_eq!(prefix.receipt(), minimum);
        assert_eq!(prefix.prefix_bytes(), header_end);
        assert!(prefix.session().evidence().pending.is_empty());
        let failure = prefix.failure().unwrap();
        assert_eq!(failure.record_offset, header_end);
        assert_eq!(failure.offset, header_end + 8);
        assert!(matches!(
            failure.kind,
            PrefixFailureKind::InvalidRecord(RecoveryError::Evidence(_))
        ));
        assert!(fixture.inspect(forged_receipt).is_err());
        let mut wrong_minimum = minimum;
        wrong_minimum.digest[0] ^= 1;
        assert!(fixture.inspect(wrong_minimum).is_err());
        assert_eq!(fs::read(&fixture.path).unwrap(), pristine);
    }

    #[test]
    fn framing_bounds_and_exact_admission_reject_without_repair() {
        let fixture = Fixture::new();
        let journal = fixture.create();
        let minimum = journal.receipt();
        drop(journal);
        let header = fs::read(&fixture.path).unwrap();
        let start = header.len();
        for (sequence, size, expected_offset) in [
            (2u32, 1u32, start),
            (1, 0, start + 4),
            (1, MAX_RECORD as u32 + 1, start + 4),
        ] {
            let mut bytes = header.clone();
            bytes.extend(sequence.to_le_bytes());
            bytes.extend(size.to_le_bytes());
            fs::write(&fixture.path, &bytes).unwrap();
            let prefix = fixture.inspect(minimum).unwrap();
            let failure = prefix.failure().unwrap();
            assert_eq!(failure.record_offset, start as u64);
            assert_eq!(failure.offset, expected_offset as u64);
            assert!(matches!(failure.kind, PrefixFailureKind::Framing(_)));
            assert_eq!(fs::read(&fixture.path).unwrap(), bytes);
        }
        fs::write(&fixture.path, &header).unwrap();
        fixture.append_payload(minimum, &[255]);
        let prefix = fixture.inspect(minimum).unwrap();
        assert!(matches!(
            prefix.failure().unwrap().kind,
            PrefixFailureKind::InvalidRecord(RecoveryError::Corrupt("unknown record type"))
        ));
        let mut wrong_context = fixture.context.clone();
        wrong_context.manifest[0] ^= 1;
        assert!(
            inspect_prefix(
                &fixture.path,
                wrong_context,
                fixture.config.clone(),
                &fixture.participants,
                minimum
            )
            .is_err()
        );
        let mut wrong_config = fixture.config.clone();
        wrong_config.map = 1;
        assert!(
            inspect_prefix(
                &fixture.path,
                fixture.context.clone(),
                wrong_config,
                &fixture.participants,
                minimum
            )
            .is_err()
        );
        fs::write(&fixture.path, &header[..header.len() - 1]).unwrap();
        assert!(fixture.inspect(minimum).is_err());
        let file = OpenOptions::new().write(true).open(&fixture.path).unwrap();
        file.set_len(MAX_FILE + 1).unwrap();
        drop(file);
        assert!(matches!(
            fixture.inspect(minimum),
            Err(RecoveryError::Corrupt("journal exceeds bound"))
        ));
        assert_eq!(fs::metadata(&fixture.path).unwrap().len(), MAX_FILE + 1);
    }
}
