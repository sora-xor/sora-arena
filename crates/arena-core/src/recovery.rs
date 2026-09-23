//! Durable local evidence, with cryptographic replay and explicit admission binding.
//!
//! This first-release file format is not a native ledger codec or an execution
//! proof. A single process owns an advisory lock; each accepted operation is
//! flushed before returning. Torn records fail closed without changing the file.
//! A trusted receipt from a peer/ledger is needed to detect deletion of complete
//! suffix records. Local bytes alone cannot establish the latest agreed frontier.
use std::{
    collections::BTreeSet,
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
    protocol::{CommitmentSet, Context, Hash, Phase, Reveal, SlotSignature, input_commitment},
    rollback::{Checkpoint, RollbackSession},
    simulation::{Config, Input, Mode, Participant, World},
};

const MAGIC: &[u8] = b"SORA-ARENA-EVIDENCE\x02";
const MAX_RECORD: usize = 4096;
const MAX_FILE: u64 = 64 * 1024 * 1024;

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

fn empty_accepted_offers(count: usize) -> AcceptedOffers {
    (0..count).map(|_| Arc::new(BTreeSet::new())).collect()
}

/// Keep this receipt outside the journal before relying on its latest frontier.
/// It authenticates byte retention, not a monetary outcome or chain finality.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Receipt {
    pub records: u32,
    pub digest: Hash,
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
    session: RollbackSession,
    partial: Vec<Option<Reveal>>,
    accepted_offers: AcceptedOffers,
    resolution_fault: Option<Error>,
    receipt: Receipt,
    prefix_bytes: u64,
    file_bytes: u64,
    failure: Option<PrefixFailure>,
}

impl AuthenticatedPrefix {
    pub fn session(&self) -> &RollbackSession {
        &self.session
    }
    pub fn partial_reveals(&self) -> &[Option<Reveal>] {
        &self.partial
    }
    /// Signed handshake offers durably accepted by one original responder slot.
    pub fn accepted_offer_digests(&self, responder: usize) -> Option<Vec<Hash>> {
        self.accepted_offers
            .get(responder)
            .map(|offers| offers.iter().copied().collect())
    }
    pub fn resolution_fault(&self) -> Option<&Error> {
        self.resolution_fault.as_ref()
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
        session: RollbackSession::new(context, config, participants)?,
        partial: vec![None; participants.len()],
        accepted_offers: empty_accepted_offers(participants.len()),
        resolution_fault: None,
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
        let mut session = result.session.clone();
        let mut partial = result.partial.clone();
        let mut accepted_offers = result.accepted_offers.clone();
        let mut resolution_fault = result.resolution_fault.clone();
        if let Err(error) = apply(
            &mut session,
            &mut partial,
            &mut accepted_offers,
            &mut resolution_fault,
            &record,
        ) {
            result.failure = Some(PrefixFailure {
                record_offset: start as u64,
                offset: (start + 8) as u64,
                kind: PrefixFailureKind::InvalidRecord(error),
            });
            break;
        }
        result.session = session;
        result.partial = partial;
        result.accepted_offers = accepted_offers;
        result.resolution_fault = resolution_fault;
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
}

pub struct DurableSession {
    file: File,
    session: RollbackSession,
    partial: Vec<Option<Reveal>>,
    accepted_offers: AcceptedOffers,
    resolution_fault: Option<Error>,
    receipt: Receipt,
    bytes: u64,
    poisoned: bool,
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
        let session = RollbackSession::new(context, config, participants)?;
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
        Ok(Self {
            file,
            session,
            partial: vec![None; participants.len()],
            accepted_offers: empty_accepted_offers(participants.len()),
            resolution_fault: None,
            receipt: Receipt {
                records: 0,
                digest: Sha256::digest(&header).into(),
            },
            bytes: header.len() as u64,
            poisoned: false,
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
        let mut result = Self {
            file,
            session: RollbackSession::new(context, config, participants)?,
            partial: vec![None; participants.len()],
            accepted_offers: empty_accepted_offers(participants.len()),
            resolution_fault: None,
            receipt: Receipt {
                records: 0,
                digest: Sha256::digest(&header).into(),
            },
            bytes: bytes.len() as u64,
            poisoned: false,
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
            apply(
                &mut result.session,
                &mut result.partial,
                &mut result.accepted_offers,
                &mut result.resolution_fault,
                &record,
            )?;
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
        Ok(result)
    }

    pub fn receipt(&self) -> Receipt {
        self.receipt
    }
    pub fn session(&self) -> &RollbackSession {
        &self.session
    }
    pub fn partial_reveals(&self) -> &[Option<Reveal>] {
        &self.partial
    }
    pub fn accepted_offer_digests(&self, responder: usize) -> Option<Vec<Hash>> {
        self.accepted_offers
            .get(responder)
            .map(|offers| offers.iter().copied().collect())
    }
    /// Complete openings stay available for dispute if reference execution fails.
    /// A recorded fault freezes gameplay and cannot release escrow or NFTs.
    pub fn resolution_fault(&self) -> Option<&Error> {
        self.resolution_fault.as_ref()
    }

    pub fn certify(
        &mut self,
        set: CommitmentSet,
        signatures: Vec<SlotSignature>,
    ) -> Result<Receipt> {
        self.append(Record::Certify(set, signatures))
    }
    /// Each valid reveal is durable even if another player withholds theirs.
    /// Retrying the exact same pending reveal is idempotent.
    pub fn reveal(&mut self, reveal: Reveal) -> Result<Receipt> {
        self.reveal_many(vec![reveal])
    }
    /// Persist reveals already received together with one sync. Never wait for
    /// a withholding peer to fill a group; a singleton follows the same path.
    pub fn reveal_many(&mut self, reveals: Vec<Reveal>) -> Result<Receipt> {
        if self.poisoned {
            return Err(RecoveryError::Poisoned);
        }
        if reveals.is_empty() || reveals.len() > self.partial.len() {
            return Err(Error::InvalidEvidence("invalid reveal group size").into());
        }
        for (i, reveal) in reveals.iter().enumerate() {
            if reveals[..i].iter().any(|r| r.slot == reveal.slot) {
                return Err(Error::InvalidEvidence("duplicate grouped reveal").into());
            }
        }
        let new = reveals
            .into_iter()
            .filter(|r| self.partial.get(r.slot).and_then(Option::as_ref) != Some(r))
            .collect::<Vec<_>>();
        if new.is_empty() {
            return Ok(self.receipt);
        }
        self.append(Record::Reveals(new))
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
        if self.session.evidence().phase == Phase::Terminal {
            return Err(Error::InvalidEvidence("terminal handshake offer").into());
        }
        let accepted = self
            .accepted_offers
            .get(responder)
            .ok_or(Error::InvalidEvidence("handshake responder outside roster"))?;
        let mut replay = handshake::OfferReplayGuard::restore(accepted.iter().copied())?;
        let (keys, response) = handshake::accept_offer(
            &self.session.evidence().context,
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
        self.session.predict(controls)?;
        Ok(())
    }

    fn append(&mut self, record: Record) -> Result<Receipt> {
        if self.poisoned {
            return Err(RecoveryError::Poisoned);
        }
        let mut session = self.session.clone();
        let mut partial = self.partial.clone();
        let mut accepted_offers = self.accepted_offers.clone();
        let mut resolution_fault = self.resolution_fault.clone();
        apply(
            &mut session,
            &mut partial,
            &mut accepted_offers,
            &mut resolution_fault,
            &record,
        )?;
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
        // A failed write/sync can have retained some or all of the new bytes.
        // Stop this handle; do not retry a financial/evidence operation blindly.
        self.poisoned = true;
        self.file.write_all(&frame)?;
        self.file.sync_all()?;
        self.session = session;
        self.partial = partial;
        self.accepted_offers = accepted_offers;
        self.resolution_fault = resolution_fault;
        self.bytes += frame.len() as u64;
        self.receipt = Receipt {
            records: sequence,
            digest,
        };
        self.poisoned = false;
        Ok(self.receipt)
    }
}

fn apply(
    session: &mut RollbackSession,
    partial: &mut [Option<Reveal>],
    accepted_offers: &mut AcceptedOffers,
    resolution_fault: &mut Option<Error>,
    record: &Record,
) -> Result<()> {
    match record {
        Record::Certify(set, signatures) => {
            session.certify(set.clone(), signatures.clone())?;
            partial.fill(None);
            *resolution_fault = None;
        }
        Record::Reveals(reveals) => {
            let evidence = session.evidence();
            let (set, _) = evidence
                .pending
                .as_ref()
                .ok_or(Error::InvalidEvidence("reveal without pending frontier"))?;
            for reveal in reveals {
                if reveal.slot >= partial.len() || partial[reveal.slot].is_some() {
                    return Err(Error::InvalidEvidence("invalid or duplicate reveal slot").into());
                }
                let digest = input_commitment(
                    &evidence.context,
                    set.epoch,
                    set.start_tick,
                    set.parent,
                    reveal.slot,
                    &reveal.inputs,
                    reveal.salt,
                )?;
                if digest != set.commitments[reveal.slot] {
                    return Err(Error::InvalidEvidence("reveal differs from commitment").into());
                }
                partial[reveal.slot] = Some(reveal.clone());
            }
            if partial.iter().all(Option::is_some) {
                match session.reveal(partial.iter().flatten().cloned().collect()) {
                    Ok(()) => {
                        partial.fill(None);
                        *resolution_fault = None;
                    }
                    Err(error) => {
                        // Valid commitment openings remain useful evidence even
                        // if the reference cannot execute them. Native dispute
                        // resolution must decide this; no local timeout may.
                        session.interrupt();
                        *resolution_fault = Some(error);
                    }
                }
            }
        }
        Record::Checkpoint(checkpoint, signatures) => {
            session.retain_checkpoint(checkpoint.clone(), signatures.clone())?
        }
        Record::Interrupt => session.interrupt(),
        Record::Finish => session.finish_local()?,
        Record::HandshakeOffer {
            initiator,
            responder,
            offer,
        } => {
            if session.evidence().phase == Phase::Terminal {
                return Err(Error::InvalidEvidence("terminal handshake offer").into());
            }
            let accepted = accepted_offers
                .get_mut(*responder)
                .ok_or(Error::InvalidEvidence("handshake responder outside roster"))?;
            let digest = handshake::verified_offer_digest(
                &session.evidence().context,
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
    }
    Ok(())
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
                    out.extend([reveal.slot as u8, reveal.inputs.len() as u8]);
                    out.extend(reveal.salt);
                    for input in &reveal.inputs {
                        out.extend(input.encode());
                    }
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
                if !(1..=count).contains(&group) {
                    return Err(RecoveryError::Corrupt("invalid reveal group size"));
                }
                let mut reveals = Vec::with_capacity(group);
                for _ in 0..group {
                    let slot = r.byte()? as usize;
                    let ticks = r.byte()? as usize;
                    if slot >= count || ticks != crate::protocol::BATCH_TICKS {
                        return Err(RecoveryError::Corrupt("invalid reveal bounds"));
                    }
                    reveals.push(Reveal {
                        slot,
                        salt: r.array()?,
                        inputs: (0..ticks)
                            .map(|_| Ok(Input::decode(r.array()?)?))
                            .collect::<Result<_>>()?,
                    });
                }
                Self::Reveals(reveals)
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
                start_tick: log.next_tick,
                parent: log.root,
                commitments: reveals
                    .iter()
                    .map(|r| {
                        input_commitment(
                            &self.context,
                            log.epoch,
                            log.next_tick,
                            log.root,
                            r.slot,
                            &r.inputs,
                            r.salt,
                        )
                        .unwrap()
                    })
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
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.path);
        }
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
        assert_eq!(recovered.partial_reveals()[1], Some(reveals[1].clone()));
        assert_eq!(recovered.session().evidence().phase, Phase::Resolving);
        assert!(recovered.session().evidence().pending.is_some());
        recovered.reveal(reveals[0].clone()).unwrap();
        assert_eq!(recovered.session().confirmed().tick, 2);
        assert!(recovered.partial_reveals().iter().all(Option::is_none));
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
        assert!(journal.partial_reveals().iter().all(Option::is_none));
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
        assert!(
            recovered
                .accept_handshake_offer(0, 1, &fixture.keys[1], &new_offer)
                .is_err()
        );
        assert_eq!(recovered.receipt(), terminal);
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
                    slot,
                    inputs: vec![Input::default(); crate::protocol::BATCH_TICKS],
                    salt: [slot as u8 + 70; 32],
                })
                .collect::<Vec<_>>();
            let set = CommitmentSet {
                epoch: evidence.epoch,
                start_tick: evidence.next_tick,
                parent: evidence.root,
                commitments: reveals
                    .iter()
                    .map(|r| {
                        input_commitment(
                            &self.context,
                            evidence.epoch,
                            evidence.next_tick,
                            evidence.root,
                            r.slot,
                            &r.inputs,
                            r.salt,
                        )
                        .unwrap()
                    })
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
        assert_eq!(prefix.partial_reveals()[1], Some(reveals[1].clone()));
        assert!(prefix.partial_reveals()[0].is_none());
        assert!(prefix.session().evidence().pending.is_some());
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
            assert_eq!(prefix.partial_reveals()[0], Some(reveals[0].clone()));
            assert!(prefix.partial_reveals()[1].is_none());
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
        assert!(complete.partial_reveals().iter().all(Option::is_none));
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
        assert!(inspected.partial_reveals().iter().all(Option::is_none));
        assert!(inspected.session().evidence().pending.is_some());
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
        assert!(prefix.session().evidence().pending.is_none());
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
