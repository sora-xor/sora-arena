//! Signed local P2P evidence. This is not a substitute for Iroha's native
//! consensus-selected history or a mathematical execution proof.
use crate::{Error, MAX_PLAYERS, simulation::Input};
use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use sha2::{Digest, Sha256};
use std::sync::Arc;

pub type Hash = [u8; 32];
pub const BATCH_TICKS: usize = 2;
pub const MAX_BATCHES: usize = 18_000;

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
        let mut out = b"sora-arena:p2p-evidence:v1\0".to_vec();
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

pub fn verify_certificate(
    context: &Context,
    set: &CommitmentSet,
    signatures: &[SlotSignature],
) -> Result<(), Error> {
    let digest = set.digest(context)?;
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
        let key = VerifyingKey::from_bytes(&context.roster[slot])
            .map_err(|_| Error::InvalidEvidence("invalid input key"))?;
        key.verify_strict(&digest, &Signature::from_bytes(&sig.signature))
            .map_err(|_| Error::InvalidEvidence("invalid commitment signature"))?;
    }
    Ok(())
}

pub fn input_commitment(
    context: &Context,
    epoch: u64,
    start_tick: u32,
    parent: Hash,
    slot: usize,
    inputs: &[Input],
    salt: Hash,
) -> Result<Hash, Error> {
    context.validate()?;
    if slot >= context.roster.len() || inputs.len() != BATCH_TICKS {
        return Err(Error::InvalidEvidence("invalid input commitment bounds"));
    }
    let mut b = context.domain(b"inputs");
    b.extend(epoch.to_le_bytes());
    b.extend(start_tick.to_le_bytes());
    b.extend(parent);
    b.extend((slot as u32).to_le_bytes());
    b.extend((inputs.len() as u32).to_le_bytes());
    for &input in inputs {
        input.validate()?;
        b.extend(input.encode());
    }
    b.extend(salt);
    Ok(Sha256::digest(b).into())
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Reveal {
    pub slot: usize,
    pub inputs: Vec<Input>,
    pub salt: Hash,
}
#[derive(Debug, Clone)]
pub struct CertifiedBatch {
    pub set: CommitmentSet,
    pub signatures: Vec<SlotSignature>,
    pub reveals: Vec<Reveal>,
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
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Phase {
    Live,
    Resolving,
    Terminal,
}

/// Retains certified frontiers before revealing controls. Only native consensus
/// can decide removals; a peer clock cannot slash or erase pending evidence.
#[derive(Debug, Clone)]
pub struct EvidenceLog {
    pub context: Context,
    pub epoch: u64,
    pub next_tick: u32,
    pub root: Hash,
    pub phase: Phase,
    pub pending: Option<(CommitmentSet, Vec<SlotSignature>)>,
    pub batches: BatchHistory,
}
impl EvidenceLog {
    pub fn new(context: Context) -> Result<Self, Error> {
        context.validate()?;
        let root = Sha256::digest(context.domain(b"genesis")).into();
        Ok(Self {
            context,
            epoch: 0,
            next_tick: 0,
            root,
            phase: Phase::Live,
            pending: None,
            batches: BatchHistory::default(),
        })
    }
    pub fn certify(
        &mut self,
        set: CommitmentSet,
        signatures: Vec<SlotSignature>,
    ) -> Result<(), Error> {
        if self.phase != Phase::Live || self.pending.is_some() {
            return Err(Error::InvalidEvidence("not accepting another frontier"));
        }
        if self.batches.len() >= MAX_BATCHES
            || set.epoch != self.epoch
            || set.start_tick != self.next_tick
            || set.parent != self.root
        {
            return Err(Error::InvalidEvidence(
                "stale or unrelated commitment frontier",
            ));
        }
        verify_certificate(&self.context, &set, &signatures)?;
        self.pending = Some((set, signatures));
        Ok(())
    }
    pub fn reveal(&mut self, reveals: Vec<Reveal>) -> Result<Vec<Vec<Input>>, Error> {
        if self.phase == Phase::Terminal {
            return Err(Error::Terminal);
        }
        let (set, signatures) = self
            .pending
            .as_ref()
            .ok_or(Error::InvalidEvidence("reveal without certified frontier"))?;
        if reveals.len() != self.context.roster.len() {
            return Err(Error::InvalidEvidence("incomplete reveals"));
        }
        let ticks = reveals[0].inputs.len();
        for (slot, r) in reveals.iter().enumerate() {
            if r.slot != slot || r.inputs.len() != ticks {
                return Err(Error::InvalidEvidence("reveal roster or tick mismatch"));
            }
            if input_commitment(
                &self.context,
                set.epoch,
                set.start_tick,
                set.parent,
                slot,
                &r.inputs,
                r.salt,
            )? != set.commitments[slot]
            {
                return Err(Error::InvalidEvidence(
                    "reveal does not match certified commitment",
                ));
            }
        }
        let new_tick = self
            .next_tick
            .checked_add(ticks as u32)
            .ok_or(Error::Arithmetic)?;
        if new_tick > crate::MAX_TICKS {
            return Err(Error::InvalidEvidence("tick limit exceeded"));
        }
        let mut bytes = self.context.domain(b"transcript-batch");
        bytes.extend(self.root);
        bytes.extend(set.digest(&self.context)?);
        for r in &reveals {
            for i in &r.inputs {
                bytes.extend(i.encode());
            }
        }
        let ordered = (0..ticks)
            .map(|tick| reveals.iter().map(|r| r.inputs[tick]).collect())
            .collect();
        let batch = CertifiedBatch {
            set: set.clone(),
            signatures: signatures.clone(),
            reveals,
        };
        self.batches.push(batch);
        self.pending = None;
        self.root = Sha256::digest(bytes).into();
        self.next_tick = new_tick;
        Ok(ordered)
    }
    pub fn interrupt(&mut self) {
        if self.phase == Phase::Live {
            self.phase = Phase::Resolving;
        }
    }
    /// Local evidence can be marked terminal only when no committed frontier is
    /// being silently discarded. Native dispute outcomes need their own verifier.
    pub fn finish(&mut self) -> Result<(), Error> {
        if self.pending.is_some() {
            return Err(Error::InvalidEvidence(
                "pending committed inputs must be resolved",
            ));
        }
        self.phase = Phase::Terminal;
        Ok(())
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
        let reveals = (0..2)
            .map(|slot| Reveal {
                slot,
                inputs: vec![Input::default(); 2],
                salt: [slot as u8; 32],
            })
            .collect::<Vec<_>>();
        let set = CommitmentSet {
            epoch: 0,
            start_tick: 0,
            parent: log.root,
            commitments: reveals
                .iter()
                .map(|r| {
                    input_commitment(&log.context, 0, 0, log.root, r.slot, &r.inputs, r.salt)
                        .unwrap()
                })
                .collect(),
        };
        (keys, log, set, reveals)
    }
    fn sigs(keys: &[SigningKey], log: &EvidenceLog, set: &CommitmentSet) -> Vec<SlotSignature> {
        keys.iter()
            .enumerate()
            .map(|(s, k)| sign_commitment_set(&log.context, set, s, k).unwrap())
            .collect()
    }
    #[test]
    fn reveal_requires_every_signature_then_replays_inputs() {
        let (k, mut l, s, r) = fixture();
        let signatures = sigs(&k, &l, &s);
        assert!(l.certify(s.clone(), signatures[..1].to_vec()).is_err());
        assert!(l.reveal(r.clone()).is_err());
        l.certify(s, signatures).unwrap();
        assert_eq!(l.reveal(r).unwrap(), vec![vec![Input::default(); 2]; 2]);
        assert_eq!(l.next_tick, 2);
    }
    #[test]
    fn cross_network_and_modified_reveals_reject() {
        let (k, mut l, s, mut r) = fixture();
        let mut other = l.context.clone();
        other.network = [9; 32];
        assert!(verify_certificate(&other, &s, &sigs(&k, &l, &s)).is_err());
        l.certify(s.clone(), sigs(&k, &l, &s)).unwrap();
        r[0].inputs[0].buttons = 1;
        assert!(l.reveal(r).is_err());
        assert!(l.pending.is_some());
        assert_eq!(l.next_tick, 0);
    }
    #[test]
    fn disconnect_cannot_erase_a_committed_death() {
        let (k, mut l, s, r) = fixture();
        l.certify(s.clone(), sigs(&k, &l, &s)).unwrap();
        l.interrupt();
        assert!(l.finish().is_err());
        l.reveal(r).unwrap();
        l.finish().unwrap();
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
        l.reveal(r).unwrap();
        assert!(l.certify(s, sig).is_err());
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
                reveals: reveals.clone(),
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
                    log.root,
                    0,
                    &vec![Input::default(); ticks],
                    [0; 32]
                )
                .is_err()
            );
        }
        assert!(
            input_commitment(
                &log.context,
                0,
                0,
                log.root,
                0,
                &[Input::default(); BATCH_TICKS],
                [0; 32]
            )
            .is_ok()
        );
    }
}
