//! Versioned authenticated encryption for an existing signed `WireFrame`.
//!
//! This is a single pairwise, unidirectional channel. The caller supplies a
//! fresh secret key for this sender/receiver/channel and retains the accepted
//! sequence floor across reconnects. Key agreement, peer authentication at
//! admission, NAT traversal, and the datagram transport are separate work.

use chacha20poly1305::{
    ChaCha20Poly1305, Key, Nonce,
    aead::{Aead, KeyInit, Payload},
};
use ed25519_dalek::SigningKey;
use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};
use zeroize::Zeroizing;

use std::collections::VecDeque;

use crate::{
    Error,
    fragmented_wire::{FragmentAssembler, FragmentResult, authenticated_sequence, fragment_packet},
    protocol::{CertifiedFrontiers, Context},
    wire::{MAX_WIRE_PACKET_BYTES, WireFrame, WireReceiver},
};

const MAGIC: &[u8] = b"SORA-ARENA-AEAD";
pub const ENCRYPTED_WIRE_VERSION: u16 = 1;
const NONCE_BYTES: usize = 12;
const TAG_BYTES: usize = 16;
const HEADER_BYTES: usize = MAGIC.len() + 2 + 1 + 8 + NONCE_BYTES + 32 + 2;
pub const MAX_ENCRYPTED_PACKET_BYTES: usize = HEADER_BYTES + MAX_WIRE_PACKET_BYTES + TAG_BYTES;
const MIN_ENCRYPTED_PACKET_BYTES: usize = HEADER_BYTES + TAG_BYTES;

/// One secret for one direction of one authenticated peer channel. Reusing a
/// key across directions or channels is prohibited even if their context
/// digests differ: AEAD associated data does not make nonce reuse safe.
pub struct ChannelKey(Zeroizing<[u8; 32]>);

impl ChannelKey {
    pub fn new(bytes: [u8; 32]) -> Result<Self, Error> {
        if bytes == [0; 32] {
            return Err(Error::InvalidConfig("empty encrypted wire key"));
        }
        Ok(Self(Zeroizing::new(bytes)))
    }

    fn cipher(&self) -> ChaCha20Poly1305 {
        ChaCha20Poly1305::new(Key::from_slice(self.0.as_ref()))
    }

    fn fragment_mac_key(&self) -> [u8; 32] {
        let mut derive =
            <Hmac<Sha256> as Mac>::new_from_slice(self.0.as_ref()).expect("fixed-size HMAC key");
        derive.update(b"sora-arena:fragment-authentication-key:v1");
        derive.finalize().into_bytes().into()
    }

    pub(crate) fn fragment_tag(&self, bytes: &[u8]) -> [u8; 32] {
        let derived = self.fragment_mac_key();
        let mut mac = <Hmac<Sha256> as Mac>::new_from_slice(&derived).expect("fixed-size HMAC key");
        mac.update(bytes);
        mac.finalize().into_bytes().into()
    }

    pub(crate) fn verify_fragment_tag(&self, bytes: &[u8], tag: &[u8]) -> Result<(), Error> {
        let derived = self.fragment_mac_key();
        let mut mac = <Hmac<Sha256> as Mac>::new_from_slice(&derived).expect("fixed-size HMAC key");
        mac.update(bytes);
        mac.verify_slice(tag)
            .map_err(|_| Error::InvalidEvidence("fragment authentication failed"))
    }

    fn ack_mac_key(&self) -> [u8; 32] {
        let mut derive =
            <Hmac<Sha256> as Mac>::new_from_slice(self.0.as_ref()).expect("fixed-size HMAC key");
        derive.update(b"sora-arena:durable-evidence-ack-key:v1");
        derive.finalize().into_bytes().into()
    }

    fn ack_tag(&self, bytes: &[u8]) -> [u8; 32] {
        let derived = self.ack_mac_key();
        let mut mac = <Hmac<Sha256> as Mac>::new_from_slice(&derived).expect("fixed-size HMAC key");
        mac.update(bytes);
        mac.finalize().into_bytes().into()
    }

    fn verify_ack_tag(&self, bytes: &[u8], tag: &[u8]) -> Result<(), Error> {
        let derived = self.ack_mac_key();
        let mut mac = <Hmac<Sha256> as Mac>::new_from_slice(&derived).expect("fixed-size HMAC key");
        mac.update(bytes);
        mac.verify_slice(tag)
            .map_err(|_| Error::InvalidEvidence("evidence ACK authentication failed"))
    }
}

impl std::fmt::Debug for ChannelKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("ChannelKey([REDACTED])")
    }
}

/// The sender's floor must be stored durably before relying on it after a
/// restart. A newly negotiated key can start with `None`.
pub struct EncryptedSender {
    context: Context,
    sender: usize,
    channel_binding: [u8; 32],
    key: ChannelKey,
    sequence_floor: Option<u64>,
}

impl EncryptedSender {
    pub fn new(
        context: Context,
        sender: usize,
        channel_binding: [u8; 32],
        key: ChannelKey,
        sequence_floor: Option<u64>,
    ) -> Result<Self, Error> {
        context.validate()?;
        if sender >= context.roster.len() {
            return Err(Error::InvalidConfig("encrypted sender outside roster"));
        }
        Ok(Self {
            context,
            sender,
            channel_binding,
            key,
            sequence_floor,
        })
    }

    pub const fn sequence_floor(&self) -> Option<u64> {
        self.sequence_floor
    }

    pub(crate) fn verify_ack_tag(&self, bytes: &[u8], tag: &[u8]) -> Result<(), Error> {
        self.key.verify_ack_tag(bytes, tag)
    }

    pub fn seal(&mut self, frame: &WireFrame, signing_key: &SigningKey) -> Result<Vec<u8>, Error> {
        if frame.sender != self.sender {
            return Err(Error::InvalidEvidence(
                "encrypted sender differs from frame",
            ));
        }
        if self
            .sequence_floor
            .is_some_and(|floor| frame.sequence <= floor)
        {
            return Err(Error::InvalidEvidence("encrypted sender sequence replay"));
        }
        let plaintext = frame.encode(&self.context, signing_key)?;
        let ciphertext_len = plaintext
            .len()
            .checked_add(TAG_BYTES)
            .ok_or(Error::Arithmetic)?;
        if ciphertext_len > MAX_WIRE_PACKET_BYTES + TAG_BYTES {
            return Err(Error::InvalidEvidence("encrypted packet exceeds bound"));
        }
        let mut nonce = [0; NONCE_BYTES];
        getrandom::getrandom(&mut nonce)
            .map_err(|_| Error::InvalidConfig("operating system random source unavailable"))?;
        let mut packet = Vec::with_capacity(HEADER_BYTES + ciphertext_len);
        packet.extend(MAGIC);
        packet.extend(ENCRYPTED_WIRE_VERSION.to_le_bytes());
        packet.push(self.sender as u8);
        packet.extend(frame.sequence.to_le_bytes());
        packet.extend(nonce);
        packet.extend(channel_context_hash(&self.context, &self.channel_binding));
        packet.extend((ciphertext_len as u16).to_le_bytes());
        let ciphertext = self
            .key
            .cipher()
            .encrypt(
                Nonce::from_slice(&nonce),
                Payload {
                    msg: &plaintext,
                    aad: &packet,
                },
            )
            .map_err(|_| Error::InvalidEvidence("encrypted packet seal failed"))?;
        packet.extend(ciphertext);
        self.sequence_floor = Some(frame.sequence);
        Ok(packet)
    }

    /// Authenticate and split one sealed packet into datagrams of at most
    /// 1,200 bytes. The sequence floor advances once for the complete packet.
    pub fn seal_fragments(
        &mut self,
        frame: &WireFrame,
        signing_key: &SigningKey,
    ) -> Result<Vec<Vec<u8>>, Error> {
        let packet = self.seal(frame, signing_key)?;
        fragment_packet(&packet, self.sender, frame.sequence, &self.key)
    }
}

/// One instance receives from exactly one roster slot. All rejected packets
/// leave its replay floor unchanged; a successfully opened packet is also
/// verified by the original Ed25519 wire decoder.
pub struct EncryptedReceiver {
    context: Context,
    expected_sender: usize,
    channel_binding: [u8; 32],
    key: ChannelKey,
    wire: WireReceiver,
    fragments: FragmentAssembler,
    accepted: VecDeque<(u64, [u8; 32])>,
}

/// Replay is authenticated but must not be delivered or journaled again.
pub(crate) enum FragmentDelivery {
    Pending,
    Frame(WireFrame),
    AcceptedReplay(u64),
    AtCapacity,
}

const MAX_RECENT_ACCEPTED: usize = 4;

impl EncryptedReceiver {
    pub fn new(
        context: Context,
        expected_sender: usize,
        channel_binding: [u8; 32],
        key: ChannelKey,
        sequence_floor: Option<u64>,
    ) -> Result<Self, Error> {
        context.validate()?;
        if expected_sender >= context.roster.len() {
            return Err(Error::InvalidConfig(
                "encrypted receiver sender outside roster",
            ));
        }
        let mut floors = vec![None; context.roster.len()];
        floors[expected_sender] = sequence_floor;
        let wire = WireReceiver::with_sequence_floor(context.clone(), floors)?;
        Ok(Self {
            context,
            expected_sender,
            channel_binding,
            key,
            wire,
            fragments: FragmentAssembler::default(),
            accepted: VecDeque::new(),
        })
    }

    pub(crate) fn ack_tag(&self, bytes: &[u8]) -> [u8; 32] {
        self.key.ack_tag(bytes)
    }

    pub fn sequence_floor(&self) -> Option<u64> {
        self.wire.sequence_floor()[self.expected_sender]
    }

    pub(crate) fn expected_sender(&self) -> usize {
        self.expected_sender
    }

    /// The sequence of one authenticated fragment from the expected sender,
    /// without reassembling or opening it.
    pub(crate) fn fragment_sequence(&self, fragment: &[u8]) -> Result<u64, Error> {
        authenticated_sequence(fragment, self.expected_sender, &self.key)
    }

    /// `frontiers` must be the receiver's own certified evidence.
    pub fn open<F: CertifiedFrontiers + ?Sized>(
        &mut self,
        packet: &[u8],
        frontiers: &F,
    ) -> Result<WireFrame, Error> {
        if !(MIN_ENCRYPTED_PACKET_BYTES..=MAX_ENCRYPTED_PACKET_BYTES).contains(&packet.len()) {
            return Err(Error::InvalidEvidence(
                "encrypted packet length outside bound",
            ));
        }
        let mut cursor = 0;
        let magic = take(packet, &mut cursor, MAGIC.len())?;
        if magic != MAGIC {
            return Err(Error::InvalidEvidence("invalid encrypted packet magic"));
        }
        let version = u16::from_le_bytes(take_array(packet, &mut cursor)?);
        if version != ENCRYPTED_WIRE_VERSION {
            return Err(Error::InvalidEvidence("unsupported encrypted wire version"));
        }
        let sender = take(packet, &mut cursor, 1)?[0] as usize;
        if sender != self.expected_sender {
            return Err(Error::InvalidEvidence("encrypted packet sender differs"));
        }
        let sequence = u64::from_le_bytes(take_array(packet, &mut cursor)?);
        if self.sequence_floor().is_some_and(|floor| sequence <= floor) {
            return Err(Error::InvalidEvidence(
                "encrypted packet replay or reordering",
            ));
        }
        let nonce: [u8; NONCE_BYTES] = take_array(packet, &mut cursor)?;
        let context_hash: [u8; 32] = take_array(packet, &mut cursor)?;
        if context_hash != channel_context_hash(&self.context, &self.channel_binding) {
            return Err(Error::InvalidEvidence("encrypted packet context differs"));
        }
        let ciphertext_len = u16::from_le_bytes(take_array(packet, &mut cursor)?) as usize;
        if !(TAG_BYTES..=MAX_WIRE_PACKET_BYTES + TAG_BYTES).contains(&ciphertext_len)
            || cursor + ciphertext_len != packet.len()
        {
            return Err(Error::InvalidEvidence(
                "encrypted packet length is not exact",
            ));
        }
        let plaintext = self
            .key
            .cipher()
            .decrypt(
                Nonce::from_slice(&nonce),
                Payload {
                    msg: &packet[cursor..],
                    aad: &packet[..cursor],
                },
            )
            .map_err(|_| Error::InvalidEvidence("encrypted packet authentication failed"))?;
        // The signed inner sequence must match the AEAD-authenticated outer
        // sequence. Decode on a clone so a mismatch cannot advance the floor.
        let mut candidate = self.wire.clone();
        let frame = candidate.decode(&plaintext, frontiers)?;
        if frame.sender != sender || frame.sequence != sequence {
            return Err(Error::InvalidEvidence(
                "encrypted packet inner header differs",
            ));
        }
        self.wire = candidate;
        self.fragments.forget_through(sequence);
        self.accepted
            .push_back((sequence, Sha256::digest(packet).into()));
        if self.accepted.len() > MAX_RECENT_ACCEPTED {
            self.accepted.pop_front();
        }
        Ok(frame)
    }

    /// Accept one authenticated datagram. A complete reassembled packet still
    /// goes through AEAD and the original signed-frame verification.
    pub fn open_fragment<F: CertifiedFrontiers + ?Sized>(
        &mut self,
        fragment: &[u8],
        frontiers: &F,
    ) -> Result<Option<WireFrame>, Error> {
        match self.open_fragment_or_replay(fragment, frontiers)? {
            FragmentDelivery::Pending => Ok(None),
            FragmentDelivery::Frame(frame) => Ok(Some(frame)),
            FragmentDelivery::AcceptedReplay(_) => {
                Err(Error::InvalidEvidence("fragment replay or reordering"))
            }
            FragmentDelivery::AtCapacity => unreachable!("unbounded fragment receive"),
        }
    }

    pub(crate) fn open_fragment_or_replay<F: CertifiedFrontiers + ?Sized>(
        &mut self,
        fragment: &[u8],
        frontiers: &F,
    ) -> Result<FragmentDelivery, Error> {
        self.open_fragment_or_replay_with_capacity(fragment, frontiers, true)
    }

    pub(crate) fn open_fragment_or_replay_with_capacity<F: CertifiedFrontiers + ?Sized>(
        &mut self,
        fragment: &[u8],
        frontiers: &F,
        accept_new: bool,
    ) -> Result<FragmentDelivery, Error> {
        match self.fragments.push(
            fragment,
            self.expected_sender,
            self.sequence_floor(),
            &self.key,
            self.accepted.make_contiguous(),
            accept_new,
        )? {
            FragmentResult::Pending => Ok(FragmentDelivery::Pending),
            FragmentResult::AcceptedReplay(sequence) => {
                Ok(FragmentDelivery::AcceptedReplay(sequence))
            }
            FragmentResult::AtCapacity => Ok(FragmentDelivery::AtCapacity),
            FragmentResult::Complete(packet) => {
                self.open(&packet, frontiers).map(FragmentDelivery::Frame)
            }
        }
    }
}

fn channel_context_hash(context: &Context, channel_binding: &[u8; 32]) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update(b"sora-arena:encrypted-wire-context:v1\0");
    hash.update(context.domain(b"encrypted-wire"));
    hash.update(channel_binding);
    hash.finalize().into()
}

fn take<'a>(packet: &'a [u8], cursor: &mut usize, count: usize) -> Result<&'a [u8], Error> {
    let end = cursor.checked_add(count).ok_or(Error::Arithmetic)?;
    let bytes = packet
        .get(*cursor..end)
        .ok_or(Error::InvalidEvidence("truncated encrypted packet"))?;
    *cursor = end;
    Ok(bytes)
}

fn take_array<const N: usize>(packet: &[u8], cursor: &mut usize) -> Result<[u8; N], Error> {
    Ok(take(packet, cursor, N)?
        .try_into()
        .expect("checked fixed-length encrypted field"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        MAX_PLAYERS,
        protocol::{CommitmentSet, NO_FRONTIERS, sign_commitment_set},
        rollback::Checkpoint,
        wire::{MAX_WIRE_PACKET_BYTES, WireMessage},
    };

    fn fixture(players: usize) -> (Context, Vec<SigningKey>, WireFrame) {
        let keys = (1..=players)
            .map(|n| SigningKey::from_bytes(&[n as u8; 32]))
            .collect::<Vec<_>>();
        let context = Context {
            network: [40; 32],
            session: [41; 32],
            manifest: [42; 32],
            roster: keys
                .iter()
                .map(|key| key.verifying_key().to_bytes())
                .collect(),
        };
        let checkpoint = Checkpoint {
            epoch: 3,
            tick: 120,
            history_root: [43; 32],
            state_hash: [44; 32],
        };
        let signatures = keys
            .iter()
            .enumerate()
            .map(|(slot, key)| checkpoint.sign(&context, slot, key).unwrap())
            .collect();
        let frame = WireFrame {
            sender: 0,
            sequence: 9,
            message: WireMessage::Checkpoint {
                checkpoint,
                signatures,
            },
        };
        (context, keys, frame)
    }

    fn sender(context: &Context, floor: Option<u64>) -> EncryptedSender {
        EncryptedSender::new(
            context.clone(),
            0,
            [45; 32],
            ChannelKey::new([46; 32]).unwrap(),
            floor,
        )
        .unwrap()
    }

    fn receiver(context: &Context, floor: Option<u64>) -> EncryptedReceiver {
        EncryptedReceiver::new(
            context.clone(),
            0,
            [45; 32],
            ChannelKey::new([46; 32]).unwrap(),
            floor,
        )
        .unwrap()
    }

    #[test]
    fn roundtrip_replay_reordering_and_restored_floors() {
        let (context, keys, frame) = fixture(3);
        let mut tx = sender(&context, None);
        let packet = tx.seal(&frame, &keys[0]).unwrap();
        assert_eq!(tx.sequence_floor(), Some(9));
        assert!(tx.seal(&frame, &keys[0]).is_err());
        let mut rx = receiver(&context, None);
        assert_eq!(rx.open(&packet, NO_FRONTIERS).unwrap(), frame);
        assert_eq!(rx.sequence_floor(), Some(9));
        assert!(rx.open(&packet, NO_FRONTIERS).is_err());
        assert_eq!(rx.sequence_floor(), Some(9));

        let mut next = frame.clone();
        next.sequence = 10;
        let next_packet = tx.seal(&next, &keys[0]).unwrap();
        assert_eq!(rx.open(&next_packet, NO_FRONTIERS).unwrap(), next);
        assert!(rx.open(&packet, NO_FRONTIERS).is_err());
        assert!(
            receiver(&context, Some(10))
                .open(&next_packet, NO_FRONTIERS)
                .is_err()
        );
        assert!(sender(&context, Some(10)).seal(&frame, &keys[0]).is_err());
    }

    #[test]
    fn tampered_packets_and_wrong_bindings_never_advance_replay_floor() {
        let (context, keys, frame) = fixture(3);
        let packet = sender(&context, None).seal(&frame, &keys[0]).unwrap();
        let mut variants = Vec::new();
        variants.push(packet[..packet.len() - 1].to_vec());
        let mut trailing = packet.clone();
        trailing.push(0);
        variants.push(trailing);
        let mut bad_version = packet.clone();
        bad_version[MAGIC.len()] ^= 1;
        variants.push(bad_version);
        let mut bad_sender = packet.clone();
        bad_sender[MAGIC.len() + 2] = 1;
        variants.push(bad_sender);
        let mut bad_sequence = packet.clone();
        bad_sequence[MAGIC.len() + 2 + 1] ^= 1;
        variants.push(bad_sequence);
        let mut bad_nonce = packet.clone();
        bad_nonce[MAGIC.len() + 2 + 1 + 8] ^= 1;
        variants.push(bad_nonce);
        let mut bad_context = packet.clone();
        bad_context[MAGIC.len() + 2 + 1 + 8 + NONCE_BYTES] ^= 1;
        variants.push(bad_context);
        let mut bad_length = packet.clone();
        bad_length[HEADER_BYTES - 2] ^= 1;
        variants.push(bad_length);
        let mut bad_ciphertext = packet.clone();
        bad_ciphertext[HEADER_BYTES] ^= 1;
        variants.push(bad_ciphertext);
        let mut bad_tag = packet.clone();
        *bad_tag.last_mut().unwrap() ^= 1;
        variants.push(bad_tag);
        variants.push(vec![0; MAX_ENCRYPTED_PACKET_BYTES + 1]);
        variants.push(vec![0; MIN_ENCRYPTED_PACKET_BYTES - 1]);
        let mut rx = receiver(&context, None);
        for variant in variants {
            assert!(rx.open(&variant, NO_FRONTIERS).is_err());
            assert_eq!(rx.sequence_floor(), None);
        }
        let mut wrong_channel = EncryptedReceiver::new(
            context.clone(),
            0,
            [0; 32],
            ChannelKey::new([46; 32]).unwrap(),
            None,
        )
        .unwrap();
        assert!(wrong_channel.open(&packet, NO_FRONTIERS).is_err());
        let mut wrong_key = EncryptedReceiver::new(
            context.clone(),
            0,
            [45; 32],
            ChannelKey::new([47; 32]).unwrap(),
            None,
        )
        .unwrap();
        assert!(wrong_key.open(&packet, NO_FRONTIERS).is_err());
        let mut wrong_network = context.clone();
        wrong_network.network[0] ^= 1;
        assert!(
            receiver(&wrong_network, None)
                .open(&packet, NO_FRONTIERS)
                .is_err()
        );
        assert_eq!(rx.open(&packet, NO_FRONTIERS).unwrap(), frame);
    }

    #[test]
    fn authenticated_outer_header_cannot_override_signed_inner_header() {
        let (context, keys, frame) = fixture(3);
        let packet = sender(&context, None).seal(&frame, &keys[0]).unwrap();
        let mut forged = packet.clone();
        let nonce: [u8; NONCE_BYTES] = packet
            [MAGIC.len() + 2 + 1 + 8..MAGIC.len() + 2 + 1 + 8 + NONCE_BYTES]
            .try_into()
            .unwrap();
        let key = ChannelKey::new([46; 32]).unwrap();
        let plaintext = key
            .cipher()
            .decrypt(
                Nonce::from_slice(&nonce),
                Payload {
                    msg: &packet[HEADER_BYTES..],
                    aad: &packet[..HEADER_BYTES],
                },
            )
            .unwrap();
        forged[MAGIC.len() + 2 + 1..MAGIC.len() + 2 + 1 + 8].copy_from_slice(&10_u64.to_le_bytes());
        let resealed = key
            .cipher()
            .encrypt(
                Nonce::from_slice(&nonce),
                Payload {
                    msg: &plaintext,
                    aad: &forged[..HEADER_BYTES],
                },
            )
            .unwrap();
        forged[HEADER_BYTES..].copy_from_slice(&resealed);
        let mut rx = receiver(&context, None);
        assert!(rx.open(&forged, NO_FRONTIERS).is_err());
        assert_eq!(rx.sequence_floor(), None);

        let mut forged_inner = packet.clone();
        let mut damaged_plaintext = plaintext;
        damaged_plaintext[0] ^= 1;
        let resealed = key
            .cipher()
            .encrypt(
                Nonce::from_slice(&nonce),
                Payload {
                    msg: &damaged_plaintext,
                    aad: &packet[..HEADER_BYTES],
                },
            )
            .unwrap();
        forged_inner[HEADER_BYTES..].copy_from_slice(&resealed);
        assert!(rx.open(&forged_inner, NO_FRONTIERS).is_err());
        assert_eq!(rx.sequence_floor(), None);
        assert_eq!(rx.open(&packet, NO_FRONTIERS).unwrap(), frame);
    }

    #[test]
    fn twelve_player_packet_is_bounded_and_invalid_configuration_rejects() {
        let (context, keys, frame) = fixture(MAX_PLAYERS);
        let mut tx = sender(&context, None);
        let packet = tx.seal(&frame, &keys[0]).unwrap();
        assert!(frame.encode(&context, &keys[0]).unwrap().len() <= MAX_WIRE_PACKET_BYTES);
        assert!(packet.len() <= MAX_ENCRYPTED_PACKET_BYTES);
        assert_eq!(
            receiver(&context, None)
                .open(&packet, NO_FRONTIERS)
                .unwrap(),
            frame
        );
        assert!(ChannelKey::new([0; 32]).is_err());
        assert!(
            EncryptedSender::new(
                context.clone(),
                MAX_PLAYERS,
                [45; 32],
                ChannelKey::new([46; 32]).unwrap(),
                None,
            )
            .is_err()
        );
        assert!(
            EncryptedReceiver::new(
                context,
                MAX_PLAYERS,
                [45; 32],
                ChannelKey::new([46; 32]).unwrap(),
                None,
            )
            .is_err()
        );
    }

    #[test]
    fn twelve_player_certificate_reassembles_out_of_order_with_mtu_bound() {
        let (context, keys, _) = fixture(MAX_PLAYERS);
        let set = CommitmentSet {
            epoch: 0,
            start_tick: 0,
            parent: [55; 32],
            commitments: (0..MAX_PLAYERS).map(|i| [i as u8; 32]).collect(),
        };
        let signatures = keys
            .iter()
            .enumerate()
            .map(|(slot, key)| sign_commitment_set(&context, &set, slot, key).unwrap())
            .collect();
        let frame = WireFrame {
            sender: 0,
            sequence: 1,
            message: WireMessage::CommitmentCertificate { set, signatures },
        };
        let fragments = sender(&context, None)
            .seal_fragments(&frame, &keys[0])
            .unwrap();
        assert_eq!(fragments.len(), 2);
        assert!(fragments.iter().all(|f| f.len() <= 1_200));
        let mut receiver = receiver(&context, None);
        assert_eq!(
            receiver.open_fragment(&fragments[1], NO_FRONTIERS).unwrap(),
            None
        );
        assert_eq!(receiver.sequence_floor(), None);
        assert_eq!(
            receiver.open_fragment(&fragments[1], NO_FRONTIERS).unwrap(),
            None
        );
        assert_eq!(
            receiver.open_fragment(&fragments[0], NO_FRONTIERS).unwrap(),
            Some(frame)
        );
        assert_eq!(receiver.sequence_floor(), Some(1));
        assert!(receiver.open_fragment(&fragments[0], NO_FRONTIERS).is_err());
    }

    #[test]
    fn fragment_tampering_and_wrong_key_cannot_advance_replay_floor() {
        let (context, keys, frame) = fixture(MAX_PLAYERS);
        let fragments = sender(&context, None)
            .seal_fragments(&frame, &keys[0])
            .unwrap();
        let mut receiver = receiver(&context, None);
        let mut bad = fragments[0].clone();
        bad[3] ^= 1;
        assert!(receiver.open_fragment(&bad, NO_FRONTIERS).is_err());
        let mut bad_tag = fragments[0].clone();
        *bad_tag.last_mut().unwrap() ^= 1;
        assert!(receiver.open_fragment(&bad_tag, NO_FRONTIERS).is_err());
        assert!(
            receiver
                .open_fragment(&vec![0; 1_201], NO_FRONTIERS)
                .is_err()
        );
        assert_eq!(receiver.sequence_floor(), None);
        let mut wrong_key = EncryptedReceiver::new(
            context.clone(),
            0,
            [45; 32],
            ChannelKey::new([47; 32]).unwrap(),
            None,
        )
        .unwrap();
        assert!(
            wrong_key
                .open_fragment(&fragments[0], NO_FRONTIERS)
                .is_err()
        );
        let mut complete = None;
        for fragment in &fragments {
            if let Some(decoded) = receiver.open_fragment(fragment, NO_FRONTIERS).unwrap() {
                complete = Some(decoded);
            }
        }
        assert_eq!(complete, Some(frame));
    }
}
