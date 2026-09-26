//! Canonical, bounded packets for authenticated P2P evidence exchange.
//!
//! The sender signs the packet header, sequence, and body. This authenticates
//! packet order but does not encrypt traffic, make input human, or prove combat
//! execution. Callers must supply their own certified frontiers when decoding a
//! reveal, and must retain sequence floors across reconnects.
//!
//! Commitments and set signatures are the pre-certification traffic that lets
//! every peer assemble the same pipelined certificates itself; see
//! `protocol::FrontierAssembler`. Checkpoint signatures likewise let peers
//! gather a complete checkpoint certificate without a coordinator.

use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use sha2::{Digest, Sha256};

use crate::{
    Error, MAX_TICKS,
    protocol::{
        BATCH_TICKS, CertifiedFrontiers, CommitmentSet, Context, Hash, Reveal, SlotSignature,
        validate_start, verify_certificate, verify_set_signature,
    },
    rollback::Checkpoint,
    simulation::Input,
};

const MAGIC: &[u8] = b"SORA-ARENA-P2P";
pub const WIRE_VERSION: u16 = 2;
/// This comfortably contains the largest twelve-player certificate. No
/// allocation or cryptographic work is attempted on an oversized packet.
pub const MAX_WIRE_PACKET_BYTES: usize = 1536;
const SIGNATURE_BYTES: usize = 64;
const HEADER_BYTES: usize = MAGIC.len() + 2 + 1 + 1 + 8 + 32 + 2;
const MIN_PACKET_BYTES: usize = HEADER_BYTES + SIGNATURE_BYTES;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WireMessage {
    CommitmentCertificate {
        set: CommitmentSet,
        signatures: Vec<SlotSignature>,
    },
    /// The set is never copied onto the wire. The receiver looks it up among
    /// its own certified frontiers by start tick and checks the opening.
    Reveal { set: CommitmentSet, reveal: Reveal },
    Checkpoint {
        checkpoint: Checkpoint,
        signatures: Vec<SlotSignature>,
    },
    /// The sender's own input commitment for one batch, sent before any set
    /// containing it exists. The signed envelope authenticates it.
    Commitment {
        epoch: u64,
        start_tick: u32,
        commitment: Hash,
    },
    /// The sender's signature over one complete set. The set travels with it
    /// so the receiver can check the signature before it assembles the set.
    SetSignature {
        set: CommitmentSet,
        signature: SlotSignature,
    },
    /// The sender's own signature over the checkpoint of a boundary it
    /// confirmed. A receiver retains the checkpoint only once every roster
    /// key signed exactly the boundary it confirmed itself.
    CheckpointSignature {
        checkpoint: Checkpoint,
        signature: SlotSignature,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WireFrame {
    pub sender: usize,
    pub sequence: u64,
    pub message: WireMessage,
}

impl WireFrame {
    pub fn encode(&self, context: &Context, key: &SigningKey) -> Result<Vec<u8>, Error> {
        context.validate()?;
        if self.sender >= context.roster.len()
            || context.roster[self.sender] != key.verifying_key().to_bytes()
        {
            return Err(Error::InvalidEvidence("wire sender key does not own slot"));
        }
        let (kind, payload) = encode_message(context, self.sender, &self.message)?;
        let payload_len = u16::try_from(payload.len())
            .map_err(|_| Error::InvalidEvidence("wire body exceeds bound"))?;
        let total = HEADER_BYTES + payload.len() + SIGNATURE_BYTES;
        if total > MAX_WIRE_PACKET_BYTES {
            return Err(Error::InvalidEvidence("wire packet exceeds bound"));
        }
        let mut bytes = Vec::with_capacity(total);
        bytes.extend(MAGIC);
        bytes.extend(WIRE_VERSION.to_le_bytes());
        bytes.push(kind);
        bytes.push(self.sender as u8);
        bytes.extend(self.sequence.to_le_bytes());
        bytes.extend(context_hash(context));
        bytes.extend(payload_len.to_le_bytes());
        bytes.extend(payload);
        bytes.extend(key.sign(&envelope_digest(&bytes)).to_bytes());
        Ok(bytes)
    }
}

/// Packet replay state is per roster slot. A restored peer must initialize
/// this from a trusted, persisted floor; `new` is for a fresh transport session.
#[derive(Debug, Clone)]
pub struct WireReceiver {
    context: Context,
    sequence_floor: Vec<Option<u64>>,
}

impl WireReceiver {
    pub fn new(context: Context) -> Result<Self, Error> {
        context.validate()?;
        let sequence_floor = vec![None; context.roster.len()];
        Ok(Self {
            context,
            sequence_floor,
        })
    }

    pub fn with_sequence_floor(
        context: Context,
        sequence_floor: Vec<Option<u64>>,
    ) -> Result<Self, Error> {
        context.validate()?;
        if sequence_floor.len() != context.roster.len() {
            return Err(Error::InvalidEvidence(
                "wire sequence floor roster mismatch",
            ));
        }
        Ok(Self {
            context,
            sequence_floor,
        })
    }

    pub fn sequence_floor(&self) -> &[Option<u64>] {
        &self.sequence_floor
    }

    /// `frontiers` must be the caller's own certified evidence, never sets
    /// received alongside this reveal. Failed decoding never advances a
    /// sequence floor. This check does not apply the result to `EvidenceLog`.
    pub fn decode<F: CertifiedFrontiers + ?Sized>(
        &mut self,
        packet: &[u8],
        frontiers: &F,
    ) -> Result<WireFrame, Error> {
        if !(MIN_PACKET_BYTES..=MAX_WIRE_PACKET_BYTES).contains(&packet.len()) {
            return Err(Error::InvalidEvidence("wire packet length outside bound"));
        }
        let mut reader = Reader::new(packet);
        if reader.take(MAGIC.len())? != MAGIC {
            return Err(Error::InvalidEvidence("invalid wire magic"));
        }
        if reader.u16()? != WIRE_VERSION {
            return Err(Error::InvalidEvidence("unsupported wire version"));
        }
        let kind = reader.u8()?;
        let sender = reader.u8()? as usize;
        if sender >= self.context.roster.len() {
            return Err(Error::InvalidEvidence("wire sender outside roster"));
        }
        let sequence = reader.u64()?;
        if self.sequence_floor[sender].is_some_and(|floor| sequence <= floor) {
            return Err(Error::InvalidEvidence("wire packet replay or reordering"));
        }
        if reader.array::<32>()? != context_hash(&self.context) {
            return Err(Error::InvalidEvidence("wire context differs"));
        }
        let body_len = reader.u16()? as usize;
        if HEADER_BYTES + body_len + SIGNATURE_BYTES != packet.len() {
            return Err(Error::InvalidEvidence("wire length is not exact"));
        }
        let body = reader.take(body_len)?;
        let signature = reader.array::<64>()?;
        if !reader.is_empty() {
            return Err(Error::InvalidEvidence("trailing wire bytes"));
        }
        VerifyingKey::from_bytes(&self.context.roster[sender])
            .map_err(|_| Error::InvalidEvidence("invalid wire sender key"))?
            .verify_strict(
                &envelope_digest(&packet[..packet.len() - SIGNATURE_BYTES]),
                &Signature::from_bytes(&signature),
            )
            .map_err(|_| Error::InvalidEvidence("invalid wire envelope signature"))?;
        let message = decode_message(&self.context, kind, sender, body, frontiers)?;
        self.sequence_floor[sender] = Some(sequence);
        Ok(WireFrame {
            sender,
            sequence,
            message,
        })
    }
}

fn context_hash(context: &Context) -> Hash {
    Sha256::digest(context.domain(b"wire-context")).into()
}

fn envelope_digest(bytes: &[u8]) -> Hash {
    let mut hash = Sha256::new();
    hash.update(b"sora-arena:wire-envelope:v2\0");
    hash.update(bytes);
    hash.finalize().into()
}

fn encode_set(out: &mut Vec<u8>, set: &CommitmentSet) {
    out.extend(set.epoch.to_le_bytes());
    out.extend(set.start_tick.to_le_bytes());
    out.extend(set.parent);
    for commitment in &set.commitments {
        out.extend(commitment);
    }
}

fn encode_message(
    context: &Context,
    sender: usize,
    message: &WireMessage,
) -> Result<(u8, Vec<u8>), Error> {
    let mut out = Vec::new();
    let kind = match message {
        WireMessage::CommitmentCertificate { set, signatures } => {
            validate_start(set.start_tick)?;
            verify_certificate(context, set, signatures)?;
            encode_set(&mut out, set);
            encode_signatures(&mut out, signatures);
            0
        }
        WireMessage::Reveal { set, reveal } => {
            validate_opening(context, sender, set, reveal)?;
            out.extend(set.start_tick.to_le_bytes());
            out.extend(set.digest(context)?);
            out.extend(reveal.salt);
            for &input in &reveal.inputs {
                out.extend(input.encode());
            }
            1
        }
        WireMessage::Checkpoint {
            checkpoint,
            signatures,
        } => {
            validate_checkpoint(context, checkpoint, signatures)?;
            encode_checkpoint(&mut out, checkpoint);
            encode_signatures(&mut out, signatures);
            2
        }
        WireMessage::Commitment {
            epoch,
            start_tick,
            commitment,
        } => {
            validate_start(*start_tick)?;
            out.extend(epoch.to_le_bytes());
            out.extend(start_tick.to_le_bytes());
            out.extend(commitment);
            3
        }
        WireMessage::SetSignature { set, signature } => {
            validate_set_signature(context, sender, set, signature)?;
            encode_set(&mut out, set);
            out.extend(signature.signature);
            4
        }
        WireMessage::CheckpointSignature {
            checkpoint,
            signature,
        } => {
            validate_checkpoint_signature(context, sender, checkpoint, signature)?;
            encode_checkpoint(&mut out, checkpoint);
            out.extend(signature.signature);
            5
        }
    };
    Ok((kind, out))
}

fn decode_message<F: CertifiedFrontiers + ?Sized>(
    context: &Context,
    kind: u8,
    sender: usize,
    body: &[u8],
    frontiers: &F,
) -> Result<WireMessage, Error> {
    let mut reader = Reader::new(body);
    let message = match kind {
        0 => {
            let set = reader.set(context.roster.len())?;
            validate_start(set.start_tick)?;
            let signatures = reader.signatures(context.roster.len())?;
            verify_certificate(context, &set, &signatures)?;
            WireMessage::CommitmentCertificate { set, signatures }
        }
        1 => {
            let start_tick = reader.u32()?;
            let set = frontiers
                .certified_frontier(start_tick)
                .ok_or(Error::InvalidEvidence(
                    "wire reveal without certified frontier",
                ))?;
            if reader.array::<32>()? != set.digest(context)? {
                return Err(Error::InvalidEvidence("wire reveal frontier differs"));
            }
            let salt = reader.array()?;
            let inputs = (0..BATCH_TICKS)
                .map(|_| Input::decode(reader.array()?))
                .collect::<Result<Vec<_>, _>>()?;
            let reveal = Reveal {
                start_tick,
                slot: sender,
                inputs,
                salt,
            };
            validate_opening(context, sender, set, &reveal)?;
            WireMessage::Reveal {
                set: set.clone(),
                reveal,
            }
        }
        2 => {
            let checkpoint = reader.checkpoint()?;
            let signatures = reader.signatures(context.roster.len())?;
            validate_checkpoint(context, &checkpoint, &signatures)?;
            WireMessage::Checkpoint {
                checkpoint,
                signatures,
            }
        }
        3 => {
            let epoch = reader.u64()?;
            let start_tick = reader.u32()?;
            validate_start(start_tick)?;
            WireMessage::Commitment {
                epoch,
                start_tick,
                commitment: reader.array()?,
            }
        }
        4 => {
            let set = reader.set(context.roster.len())?;
            let signature = SlotSignature {
                slot: sender,
                signature: reader.array()?,
            };
            validate_set_signature(context, sender, &set, &signature)?;
            WireMessage::SetSignature { set, signature }
        }
        5 => {
            let checkpoint = reader.checkpoint()?;
            let signature = SlotSignature {
                slot: sender,
                signature: reader.array()?,
            };
            validate_checkpoint_signature(context, sender, &checkpoint, &signature)?;
            WireMessage::CheckpointSignature {
                checkpoint,
                signature,
            }
        }
        _ => return Err(Error::InvalidEvidence("unknown wire message type")),
    };
    if !reader.is_empty() {
        return Err(Error::InvalidEvidence("trailing wire body bytes"));
    }
    Ok(message)
}

fn validate_opening(
    context: &Context,
    sender: usize,
    set: &CommitmentSet,
    reveal: &Reveal,
) -> Result<(), Error> {
    validate_start(set.start_tick)?;
    if reveal.slot != sender {
        return Err(Error::InvalidEvidence("wire reveal bounds differ"));
    }
    reveal
        .verify(context, set)
        .map_err(|_| Error::InvalidEvidence("wire reveal opening differs"))
}

fn validate_set_signature(
    context: &Context,
    sender: usize,
    set: &CommitmentSet,
    signature: &SlotSignature,
) -> Result<(), Error> {
    validate_start(set.start_tick)?;
    if signature.slot != sender {
        return Err(Error::InvalidEvidence("set signature from another slot"));
    }
    verify_set_signature(context, set, signature)
}

fn validate_checkpoint(
    context: &Context,
    checkpoint: &Checkpoint,
    signatures: &[SlotSignature],
) -> Result<(), Error> {
    if checkpoint.tick > MAX_TICKS {
        return Err(Error::InvalidEvidence("wire checkpoint tick outside match"));
    }
    checkpoint.verify(context, signatures)
}

fn validate_checkpoint_signature(
    context: &Context,
    sender: usize,
    checkpoint: &Checkpoint,
    signature: &SlotSignature,
) -> Result<(), Error> {
    if checkpoint.tick > MAX_TICKS {
        return Err(Error::InvalidEvidence("wire checkpoint tick outside match"));
    }
    if signature.slot != sender {
        return Err(Error::InvalidEvidence(
            "checkpoint signature from another slot",
        ));
    }
    checkpoint.verify_signature(context, signature)
}

fn encode_checkpoint(out: &mut Vec<u8>, checkpoint: &Checkpoint) {
    out.extend(checkpoint.epoch.to_le_bytes());
    out.extend(checkpoint.tick.to_le_bytes());
    out.extend(checkpoint.history_root);
    out.extend(checkpoint.state_hash);
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
    const fn new(bytes: &'a [u8]) -> Self {
        Self { bytes }
    }
    fn take(&mut self, count: usize) -> Result<&'a [u8], Error> {
        if self.bytes.len() < count {
            return Err(Error::InvalidEvidence("truncated wire packet"));
        }
        let (head, rest) = self.bytes.split_at(count);
        self.bytes = rest;
        Ok(head)
    }
    fn array<const N: usize>(&mut self) -> Result<[u8; N], Error> {
        Ok(self.take(N)?.try_into().expect("checked fixed length"))
    }
    fn u8(&mut self) -> Result<u8, Error> {
        Ok(self.array::<1>()?[0])
    }
    fn u16(&mut self) -> Result<u16, Error> {
        Ok(u16::from_le_bytes(self.array()?))
    }
    fn u32(&mut self) -> Result<u32, Error> {
        Ok(u32::from_le_bytes(self.array()?))
    }
    fn u64(&mut self) -> Result<u64, Error> {
        Ok(u64::from_le_bytes(self.array()?))
    }
    fn set(&mut self, count: usize) -> Result<CommitmentSet, Error> {
        Ok(CommitmentSet {
            epoch: self.u64()?,
            start_tick: self.u32()?,
            parent: self.array()?,
            commitments: (0..count).map(|_| self.array()).collect::<Result<_, _>>()?,
        })
    }
    fn checkpoint(&mut self) -> Result<Checkpoint, Error> {
        Ok(Checkpoint {
            epoch: self.u64()?,
            tick: self.u32()?,
            history_root: self.array()?,
            state_hash: self.array()?,
        })
    }
    fn signatures(&mut self, count: usize) -> Result<Vec<SlotSignature>, Error> {
        (0..count)
            .map(|_| {
                Ok(SlotSignature {
                    slot: self.u8()? as usize,
                    signature: self.array()?,
                })
            })
            .collect()
    }
    const fn is_empty(&self) -> bool {
        self.bytes.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::MAX_PLAYERS;
    use crate::protocol::{NO_FRONTIERS, sign_commitment_set};

    fn fixture() -> (
        Context,
        Vec<SigningKey>,
        CommitmentSet,
        Vec<Reveal>,
        Checkpoint,
    ) {
        let keys = (1..=3)
            .map(|n| SigningKey::from_bytes(&[n; 32]))
            .collect::<Vec<_>>();
        let context = Context {
            network: [21; 32],
            session: [22; 32],
            manifest: [23; 32],
            roster: keys
                .iter()
                .map(|key| key.verifying_key().to_bytes())
                .collect(),
        };
        let reveals = (0..keys.len())
            .map(|slot| Reveal {
                start_tick: 14,
                slot,
                inputs: vec![Input::default(); BATCH_TICKS],
                salt: [slot as u8; 32],
            })
            .collect::<Vec<_>>();
        let set = CommitmentSet {
            epoch: 7,
            start_tick: 14,
            parent: [24; 32],
            commitments: reveals
                .iter()
                .map(|reveal| reveal.commitment(&context, 7).unwrap())
                .collect(),
        };
        let checkpoint = Checkpoint {
            epoch: 7,
            tick: 16,
            history_root: [25; 32],
            state_hash: [26; 32],
        };
        (context, keys, set, reveals, checkpoint)
    }

    fn certificate(context: &Context, keys: &[SigningKey], set: &CommitmentSet) -> WireMessage {
        WireMessage::CommitmentCertificate {
            set: set.clone(),
            signatures: keys
                .iter()
                .enumerate()
                .map(|(slot, key)| sign_commitment_set(context, set, slot, key).unwrap())
                .collect(),
        }
    }

    #[test]
    fn six_packet_types_roundtrip_and_sequence_floors_restore() {
        let (context, keys, set, reveals, checkpoint) = fixture();
        let messages = [
            certificate(&context, &keys, &set),
            WireMessage::Reveal {
                set: set.clone(),
                reveal: reveals[1].clone(),
            },
            WireMessage::Checkpoint {
                checkpoint: checkpoint.clone(),
                signatures: keys
                    .iter()
                    .enumerate()
                    .map(|(slot, key)| checkpoint.sign(&context, slot, key).unwrap())
                    .collect(),
            },
            WireMessage::Commitment {
                epoch: 7,
                start_tick: 16,
                commitment: [27; 32],
            },
            WireMessage::SetSignature {
                set: set.clone(),
                signature: sign_commitment_set(&context, &set, 2, &keys[2]).unwrap(),
            },
            WireMessage::CheckpointSignature {
                checkpoint: checkpoint.clone(),
                signature: checkpoint.sign(&context, 2, &keys[2]).unwrap(),
            },
        ];
        let mut receiver = WireReceiver::new(context.clone()).unwrap();
        for (index, message) in messages.into_iter().enumerate() {
            let sender = [0, 1, 0, 1, 2, 2][index];
            let frame = WireFrame {
                sender,
                sequence: index as u64,
                message,
            };
            let bytes = frame.encode(&context, &keys[sender]).unwrap();
            assert_eq!(
                receiver.decode(&bytes, std::slice::from_ref(&set)).unwrap(),
                frame
            );
        }
        assert_eq!(receiver.sequence_floor(), &[Some(2), Some(3), Some(5)]);
        let mut restored =
            WireReceiver::with_sequence_floor(context, receiver.sequence_floor().to_vec()).unwrap();
        let old = WireFrame {
            sender: 1,
            sequence: 1,
            message: WireMessage::Reveal {
                set: set.clone(),
                reveal: reveals[1].clone(),
            },
        }
        .encode(&restored.context, &keys[1])
        .unwrap();
        assert!(restored.decode(&old, std::slice::from_ref(&set)).is_err());
    }

    #[test]
    fn exact_length_version_context_and_signature_mutations_reject_without_advancing() {
        let (context, keys, set, _, _) = fixture();
        let frame = WireFrame {
            sender: 0,
            sequence: 9,
            message: certificate(&context, &keys, &set),
        };
        let bytes = frame.encode(&context, &keys[0]).unwrap();
        let mut receiver = WireReceiver::new(context.clone()).unwrap();
        let mut variants = Vec::new();
        variants.push(bytes[..bytes.len() - 1].to_vec());
        let mut trailing = bytes.clone();
        trailing.push(0);
        variants.push(trailing);
        let mut bad_version = bytes.clone();
        bad_version[MAGIC.len()] ^= 1;
        variants.push(bad_version);
        let mut bad_size = bytes.clone();
        bad_size[HEADER_BYTES - 2] ^= 1;
        variants.push(bad_size);
        let mut bad_context = bytes.clone();
        bad_context[MAGIC.len() + 2 + 1 + 1 + 8] ^= 1;
        variants.push(bad_context);
        let mut bad_signature = bytes.clone();
        *bad_signature.last_mut().unwrap() ^= 1;
        variants.push(bad_signature);
        let mut bad_sequence = bytes.clone();
        bad_sequence[MAGIC.len() + 2 + 1 + 1] ^= 1;
        variants.push(bad_sequence);
        for variant in variants {
            assert!(receiver.decode(&variant, NO_FRONTIERS).is_err());
            assert_eq!(receiver.sequence_floor(), &[None, None, None]);
        }
        let mut wrong_network = context.clone();
        wrong_network.network[0] ^= 1;
        assert!(
            WireReceiver::new(wrong_network)
                .unwrap()
                .decode(&bytes, NO_FRONTIERS)
                .is_err()
        );
        assert_eq!(receiver.decode(&bytes, NO_FRONTIERS).unwrap(), frame);
        assert!(receiver.decode(&bytes, NO_FRONTIERS).is_err());
    }

    #[test]
    fn reveal_requires_matching_certified_frontier_and_valid_opening() {
        let (context, keys, set, mut reveals, _) = fixture();
        let frame = WireFrame {
            sender: 1,
            sequence: 0,
            message: WireMessage::Reveal {
                set: set.clone(),
                reveal: reveals[1].clone(),
            },
        };
        let bytes = frame.encode(&context, &keys[1]).unwrap();
        let mut receiver = WireReceiver::new(context.clone()).unwrap();
        assert!(receiver.decode(&bytes, NO_FRONTIERS).is_err());
        let mut wrong_set = set.clone();
        wrong_set.parent[0] ^= 1;
        assert!(receiver.decode(&bytes, &[wrong_set][..]).is_err());
        let mut other_tick = set.clone();
        other_tick.start_tick += BATCH_TICKS as u32;
        assert!(receiver.decode(&bytes, &[other_tick.clone()][..]).is_err());
        assert_eq!(receiver.sequence_floor(), &[None, None, None]);
        // Several pipelined frontiers: the reveal names its own.
        assert_eq!(
            receiver
                .decode(&bytes, &[other_tick, set.clone()][..])
                .unwrap(),
            frame
        );
        let mut forged_opening = bytes.clone();
        // Keep the sender envelope authentic while changing a canonical input.
        let first_input = HEADER_BYTES + 4 + 32 + 32;
        forged_opening[first_input] = 1;
        resign(&mut forged_opening, &keys[1]);
        let mut fresh = WireReceiver::new(context.clone()).unwrap();
        assert!(
            fresh
                .decode(&forged_opening, std::slice::from_ref(&set))
                .is_err()
        );
        assert_eq!(fresh.sequence_floor(), &[None, None, None]);
        reveals[1].inputs[0].buttons = 1;
        assert!(
            WireFrame {
                sender: 1,
                sequence: 1,
                message: WireMessage::Reveal {
                    set,
                    reveal: reveals[1].clone(),
                },
            }
            .encode(&context, &keys[1])
            .is_err()
        );
    }

    #[test]
    fn bound_and_sender_validation_precede_allocations() {
        let (context, keys, set, _, _) = fixture();
        let mut receiver = WireReceiver::new(context.clone()).unwrap();
        assert!(
            receiver
                .decode(&vec![0; MAX_WIRE_PACKET_BYTES + 1], NO_FRONTIERS)
                .is_err()
        );
        assert!(
            receiver
                .decode(&[0; MIN_PACKET_BYTES - 1], NO_FRONTIERS)
                .is_err()
        );
        let frame = WireFrame {
            sender: 0,
            sequence: 0,
            message: certificate(&context, &keys, &set),
        };
        assert!(frame.encode(&context, &keys[1]).is_err());
        let mut bytes = frame.encode(&context, &keys[0]).unwrap();
        bytes[MAGIC.len() + 2 + 1] = MAX_PLAYERS as u8;
        assert!(receiver.decode(&bytes, NO_FRONTIERS).is_err());
        assert_eq!(receiver.sequence_floor(), &[None, None, None]);
        assert!(WireReceiver::with_sequence_floor(context, vec![None; 2]).is_err());
    }

    #[test]
    fn authentic_envelope_cannot_hide_invalid_inner_signatures_or_unknown_tags() {
        let (context, keys, set, _, checkpoint) = fixture();
        let frame = WireFrame {
            sender: 0,
            sequence: 0,
            message: certificate(&context, &keys, &set),
        };
        let bytes = frame.encode(&context, &keys[0]).unwrap();
        let mut receiver = WireReceiver::new(context.clone()).unwrap();
        let mut altered = bytes.clone();
        // Re-sign after damaging the first roster signature. The transport
        // sender is valid, but the complete certificate is still invalid.
        let sig_offset = HEADER_BYTES + 8 + 4 + 32 + context.roster.len() * 32 + 1;
        altered[sig_offset] ^= 1;
        resign(&mut altered, &keys[0]);
        assert!(receiver.decode(&altered, NO_FRONTIERS).is_err());
        let mut unknown = bytes.clone();
        unknown[MAGIC.len() + 2] = 99;
        resign(&mut unknown, &keys[0]);
        assert!(receiver.decode(&unknown, NO_FRONTIERS).is_err());
        assert_eq!(receiver.sequence_floor(), &[None, None, None]);

        let mut checkpoint_signatures = keys
            .iter()
            .enumerate()
            .map(|(slot, key)| checkpoint.sign(&context, slot, key).unwrap())
            .collect::<Vec<_>>();
        checkpoint_signatures[2].signature[0] ^= 1;
        assert!(
            WireFrame {
                sender: 0,
                sequence: 1,
                message: WireMessage::Checkpoint {
                    checkpoint,
                    signatures: checkpoint_signatures,
                },
            }
            .encode(&context, &keys[0])
            .is_err()
        );
    }

    #[test]
    fn pre_certification_messages_bind_their_sender_and_batch_boundary() {
        let (context, keys, set, _, _) = fixture();
        let mut receiver = WireReceiver::new(context.clone()).unwrap();
        // Another slot's signature cannot be relayed as the sender's own.
        let relayed = WireFrame {
            sender: 0,
            sequence: 0,
            message: WireMessage::SetSignature {
                set: set.clone(),
                signature: sign_commitment_set(&context, &set, 1, &keys[1]).unwrap(),
            },
        };
        assert!(relayed.encode(&context, &keys[0]).is_err());
        let own = WireFrame {
            sender: 1,
            sequence: 0,
            message: WireMessage::SetSignature {
                set: set.clone(),
                signature: sign_commitment_set(&context, &set, 1, &keys[1]).unwrap(),
            },
        };
        let bytes = own.encode(&context, &keys[1]).unwrap();
        // A signature over a different set, re-enveloped by its sender.
        let mut altered = bytes.clone();
        let first_commitment = HEADER_BYTES + 8 + 4 + 32;
        altered[first_commitment] ^= 1;
        resign(&mut altered, &keys[1]);
        assert!(receiver.decode(&altered, NO_FRONTIERS).is_err());
        assert_eq!(receiver.decode(&bytes, NO_FRONTIERS).unwrap(), own);
        for start_tick in [15, MAX_TICKS] {
            let unaligned = WireFrame {
                sender: 2,
                sequence: 0,
                message: WireMessage::Commitment {
                    epoch: 0,
                    start_tick,
                    commitment: [1; 32],
                },
            };
            assert!(unaligned.encode(&context, &keys[2]).is_err());
        }
        let commitment = WireFrame {
            sender: 2,
            sequence: 0,
            message: WireMessage::Commitment {
                epoch: 0,
                start_tick: 16,
                commitment: [1; 32],
            },
        };
        let mut bytes = commitment.encode(&context, &keys[2]).unwrap();
        bytes[HEADER_BYTES + 8] = 17;
        resign(&mut bytes, &keys[2]);
        assert!(receiver.decode(&bytes, NO_FRONTIERS).is_err());
        assert_eq!(receiver.sequence_floor(), &[None, Some(0), None]);
    }

    #[test]
    fn checkpoint_signatures_bind_their_signer_and_the_exact_checkpoint() {
        let (context, keys, _, _, checkpoint) = fixture();
        let relayed = WireFrame {
            sender: 0,
            sequence: 0,
            message: WireMessage::CheckpointSignature {
                checkpoint: checkpoint.clone(),
                signature: checkpoint.sign(&context, 1, &keys[1]).unwrap(),
            },
        };
        assert!(relayed.encode(&context, &keys[0]).is_err());
        let own = WireFrame {
            sender: 1,
            sequence: 0,
            message: WireMessage::CheckpointSignature {
                checkpoint: checkpoint.clone(),
                signature: checkpoint.sign(&context, 1, &keys[1]).unwrap(),
            },
        };
        let bytes = own.encode(&context, &keys[1]).unwrap();
        let mut receiver = WireReceiver::new(context.clone()).unwrap();
        // The same signature re-enveloped over another state hash.
        let mut altered = bytes.clone();
        altered[HEADER_BYTES + 8 + 4 + 32] ^= 1;
        resign(&mut altered, &keys[1]);
        assert!(receiver.decode(&altered, NO_FRONTIERS).is_err());
        assert_eq!(receiver.sequence_floor(), &[None, None, None]);
        assert_eq!(receiver.decode(&bytes, NO_FRONTIERS).unwrap(), own);
        let mut late = checkpoint;
        late.tick = MAX_TICKS + 1;
        assert!(
            WireFrame {
                sender: 2,
                sequence: 0,
                message: WireMessage::CheckpointSignature {
                    signature: late.sign(&context, 2, &keys[2]).unwrap(),
                    checkpoint: late,
                },
            }
            .encode(&context, &keys[2])
            .is_err()
        );
    }

    #[test]
    fn twelve_player_certificate_fits_bound_and_packet_reordering_is_rejected_per_sender() {
        let keys = (1..=MAX_PLAYERS)
            .map(|n| SigningKey::from_bytes(&[n as u8; 32]))
            .collect::<Vec<_>>();
        let context = Context {
            network: [31; 32],
            session: [32; 32],
            manifest: [33; 32],
            roster: keys
                .iter()
                .map(|key| key.verifying_key().to_bytes())
                .collect(),
        };
        let set = CommitmentSet {
            epoch: 0,
            start_tick: MAX_TICKS - BATCH_TICKS as u32,
            parent: [34; 32],
            commitments: vec![[35; 32]; MAX_PLAYERS],
        };
        let frame = WireFrame {
            sender: 0,
            sequence: 5,
            message: certificate(&context, &keys, &set),
        };
        let first = frame.encode(&context, &keys[0]).unwrap();
        assert!(first.len() <= MAX_WIRE_PACKET_BYTES);
        let mut receiver = WireReceiver::new(context.clone()).unwrap();
        assert_eq!(receiver.decode(&first, NO_FRONTIERS).unwrap(), frame);
        let old = WireFrame {
            sender: 0,
            sequence: 4,
            message: certificate(&context, &keys, &set),
        }
        .encode(&context, &keys[0])
        .unwrap();
        assert!(receiver.decode(&old, NO_FRONTIERS).is_err());
        // Other participants' sequence spaces are independent.
        let other = WireFrame {
            sender: 1,
            sequence: 0,
            message: certificate(&context, &keys, &set),
        };
        assert_eq!(
            receiver
                .decode(&other.encode(&context, &keys[1]).unwrap(), NO_FRONTIERS)
                .unwrap(),
            other
        );
        assert_eq!(receiver.sequence_floor()[0], Some(5));
        assert_eq!(receiver.sequence_floor()[1], Some(0));
    }

    fn resign(packet: &mut [u8], key: &SigningKey) {
        let signed_len = packet.len() - SIGNATURE_BYTES;
        let signature = key.sign(&envelope_digest(&packet[..signed_len])).to_bytes();
        packet[signed_len..].copy_from_slice(&signature);
    }
}
