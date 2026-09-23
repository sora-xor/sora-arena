//! Authenticated ephemeral pairwise keys for the encrypted evidence wire.
//!
//! Both peers already know the signed admission Context and its ordered
//! Ed25519 roster. This two-message exchange binds fresh X25519 public keys
//! to those identities, the exact Context, and the initiator/responder slots.
//! The replay guard is caller-owned and must be retained across reconnects.
//! This module does not discover peers or provide a network transport.

use std::collections::BTreeSet;

use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use hkdf::Hkdf;
use sha2::{Digest, Sha256};
use x25519_dalek::{EphemeralSecret, PublicKey, SharedSecret};
use zeroize::Zeroizing;

use crate::{Error, encrypted_wire::ChannelKey, protocol::Context};

const MAGIC: &[u8] = b"SORA-ARENA-KEX";
const VERSION: u16 = 1;
const OFFER_KIND: u8 = 0;
const RESPONSE_KIND: u8 = 1;
const SIGNATURE_BYTES: usize = 64;
const HEADER_BYTES: usize = MAGIC.len() + 2 + 1 + 1 + 1;
/// Exact byte length of a signed initiator offer.
pub const OFFER_PACKET_BYTES: usize = HEADER_BYTES + 32 + SIGNATURE_BYTES;
/// Exact byte length of a signed responder answer.
pub const RESPONSE_PACKET_BYTES: usize = HEADER_BYTES + 32 + 32 + SIGNATURE_BYTES;
/// Maximum accepted offers retained by one responder for one match.
pub const MAX_ACCEPTED_OFFERS_PER_MATCH: usize = 1024;

/// Retained hashes of offers already accepted by this responder.
///
/// Persist the returned hashes with the match evidence and restore them before
/// accepting packets after a restart. Clearing this guard permits a previously
/// signed offer to consume a new responder secret, though the old initiator
/// cannot complete the resulting exchange without its original secret.
#[derive(Default)]
pub struct OfferReplayGuard {
    accepted: BTreeSet<[u8; 32]>,
}

impl OfferReplayGuard {
    /// Restore trusted accepted-offer hashes retained for this match.
    pub fn restore(hashes: impl IntoIterator<Item = [u8; 32]>) -> Result<Self, Error> {
        let mut accepted = BTreeSet::new();
        for hash in hashes {
            if !accepted.contains(&hash) && accepted.len() == MAX_ACCEPTED_OFFERS_PER_MATCH {
                return Err(Error::InvalidEvidence("handshake replay guard is full"));
            }
            accepted.insert(hash);
        }
        Ok(Self { accepted })
    }

    /// Stable snapshot suitable for the caller's durable evidence record.
    pub fn accepted_digests(&self) -> Vec<[u8; 32]> {
        self.accepted.iter().copied().collect()
    }
}

/// Local sending and receiving secrets for one ordered pair of roster slots.
///
/// Use send_key for the local EncryptedSender and receive_key for the local
/// EncryptedReceiver. Both peers obtain the same channel_binding and opposite
/// directions get independent keys.
pub struct PairwiseKeys {
    pub send_key: ChannelKey,
    pub receive_key: ChannelKey,
    pub channel_binding: [u8; 32],
}

/// A one-use initiator secret and the exact signed offer it created.
pub struct Initiator {
    context: Context,
    initiator_slot: usize,
    responder_slot: usize,
    secret: EphemeralSecret,
    offer: [u8; OFFER_PACKET_BYTES],
}

impl Initiator {
    /// Sign a new ephemeral offer with the admitted initiator's gameplay key.
    pub fn start(
        context: Context,
        initiator_slot: usize,
        responder_slot: usize,
        identity: &SigningKey,
    ) -> Result<(Self, [u8; OFFER_PACKET_BYTES]), Error> {
        validate_local_identity(&context, initiator_slot, responder_slot, identity)?;
        let secret = EphemeralSecret::random();
        let public = PublicKey::from(&secret);
        let mut offer = [0; OFFER_PACKET_BYTES];
        write_header(&mut offer, OFFER_KIND, initiator_slot, responder_slot);
        offer[HEADER_BYTES..HEADER_BYTES + 32].copy_from_slice(public.as_bytes());
        let digest = identity_digest(
            &context,
            b"handshake-offer-signature",
            &offer[..OFFER_PACKET_BYTES - SIGNATURE_BYTES],
        );
        offer[OFFER_PACKET_BYTES - SIGNATURE_BYTES..]
            .copy_from_slice(&identity.sign(&digest).to_bytes());
        let local = Self {
            context,
            initiator_slot,
            responder_slot,
            secret,
            offer,
        };
        Ok((local, offer))
    }

    /// Verify the signed answer and consume this offer's secret exactly once.
    pub fn finish(self, response: &[u8]) -> Result<PairwiseKeys, Error> {
        let responder_public = decode_response(
            &self.context,
            self.initiator_slot,
            self.responder_slot,
            offer_digest(&self.context, &self.offer),
            response,
        )?;
        let shared = self
            .secret
            .diffie_hellman(&PublicKey::from(responder_public));
        derive_keys(&self.context, &self.offer, response, &shared, true)
    }
}

/// Verify one fresh signed offer, sign a response, and derive the responder's
/// directional keys. A duplicate offer is rejected even if the responder
/// would otherwise generate a fresh local X25519 secret.
pub fn accept_offer(
    context: &Context,
    initiator_slot: usize,
    responder_slot: usize,
    identity: &SigningKey,
    offer: &[u8],
    replay: &mut OfferReplayGuard,
) -> Result<(PairwiseKeys, [u8; RESPONSE_PACKET_BYTES]), Error> {
    validate_local_identity(context, responder_slot, initiator_slot, identity)?;
    let initiator_public = decode_offer(context, initiator_slot, responder_slot, offer)?;
    let offer_id = offer_digest(context, offer);
    if replay.accepted.contains(&offer_id) {
        return Err(Error::InvalidEvidence("handshake offer replay"));
    }
    if replay.accepted.len() == MAX_ACCEPTED_OFFERS_PER_MATCH {
        return Err(Error::InvalidEvidence("handshake replay guard is full"));
    }

    let secret = EphemeralSecret::random();
    let public = PublicKey::from(&secret);
    let mut response = [0; RESPONSE_PACKET_BYTES];
    write_header(&mut response, RESPONSE_KIND, initiator_slot, responder_slot);
    response[HEADER_BYTES..HEADER_BYTES + 32].copy_from_slice(&offer_id);
    response[HEADER_BYTES + 32..HEADER_BYTES + 64].copy_from_slice(public.as_bytes());
    let digest = identity_digest(
        context,
        b"handshake-response-signature",
        &response[..RESPONSE_PACKET_BYTES - SIGNATURE_BYTES],
    );
    response[RESPONSE_PACKET_BYTES - SIGNATURE_BYTES..]
        .copy_from_slice(&identity.sign(&digest).to_bytes());
    let shared = secret.diffie_hellman(&PublicKey::from(initiator_public));
    let keys = derive_keys(context, offer, &response, &shared, false)?;
    replay.accepted.insert(offer_id);
    Ok((keys, response))
}

fn validate_local_identity(
    context: &Context,
    local_slot: usize,
    peer_slot: usize,
    identity: &SigningKey,
) -> Result<(), Error> {
    context.validate()?;
    if local_slot == peer_slot
        || local_slot >= context.roster.len()
        || peer_slot >= context.roster.len()
    {
        return Err(Error::InvalidConfig("invalid handshake slot pair"));
    }
    if context.roster[local_slot] != identity.verifying_key().to_bytes() {
        return Err(Error::InvalidEvidence(
            "handshake identity does not own slot",
        ));
    }
    Ok(())
}

fn write_header(packet: &mut [u8], kind: u8, initiator: usize, responder: usize) {
    packet[..MAGIC.len()].copy_from_slice(MAGIC);
    packet[MAGIC.len()..MAGIC.len() + 2].copy_from_slice(&VERSION.to_le_bytes());
    packet[MAGIC.len() + 2] = kind;
    packet[MAGIC.len() + 3] = initiator as u8;
    packet[MAGIC.len() + 4] = responder as u8;
}

fn check_header(
    packet: &[u8],
    expected_len: usize,
    kind: u8,
    initiator: usize,
    responder: usize,
) -> Result<(), Error> {
    if packet.len() != expected_len {
        return Err(Error::InvalidEvidence(
            "handshake packet length is not exact",
        ));
    }
    if &packet[..MAGIC.len()] != MAGIC {
        return Err(Error::InvalidEvidence("invalid handshake magic"));
    }
    if u16::from_le_bytes(
        packet[MAGIC.len()..MAGIC.len() + 2]
            .try_into()
            .expect("fixed handshake version"),
    ) != VERSION
        || packet[MAGIC.len() + 2] != kind
    {
        return Err(Error::InvalidEvidence("unsupported handshake packet"));
    }
    if packet[MAGIC.len() + 3] as usize != initiator
        || packet[MAGIC.len() + 4] as usize != responder
    {
        return Err(Error::InvalidEvidence("handshake slot pair differs"));
    }
    Ok(())
}

fn decode_offer(
    context: &Context,
    initiator: usize,
    responder: usize,
    offer: &[u8],
) -> Result<[u8; 32], Error> {
    check_header(offer, OFFER_PACKET_BYTES, OFFER_KIND, initiator, responder)?;
    verify_signature(
        context,
        initiator,
        b"handshake-offer-signature",
        &offer[..OFFER_PACKET_BYTES - SIGNATURE_BYTES],
        &offer[OFFER_PACKET_BYTES - SIGNATURE_BYTES..],
    )?;
    Ok(offer[HEADER_BYTES..HEADER_BYTES + 32]
        .try_into()
        .expect("fixed handshake offer public key"))
}

fn decode_response(
    context: &Context,
    initiator: usize,
    responder: usize,
    expected_offer: [u8; 32],
    response: &[u8],
) -> Result<[u8; 32], Error> {
    check_header(
        response,
        RESPONSE_PACKET_BYTES,
        RESPONSE_KIND,
        initiator,
        responder,
    )?;
    if response[HEADER_BYTES..HEADER_BYTES + 32] != expected_offer {
        return Err(Error::InvalidEvidence("handshake response offer differs"));
    }
    verify_signature(
        context,
        responder,
        b"handshake-response-signature",
        &response[..RESPONSE_PACKET_BYTES - SIGNATURE_BYTES],
        &response[RESPONSE_PACKET_BYTES - SIGNATURE_BYTES..],
    )?;
    Ok(response[HEADER_BYTES + 32..HEADER_BYTES + 64]
        .try_into()
        .expect("fixed handshake response public key"))
}

fn verify_signature(
    context: &Context,
    slot: usize,
    tag: &[u8],
    unsigned: &[u8],
    signature: &[u8],
) -> Result<(), Error> {
    let key = VerifyingKey::from_bytes(&context.roster[slot])
        .map_err(|_| Error::InvalidEvidence("invalid handshake roster key"))?;
    key.verify_strict(
        &identity_digest(context, tag, unsigned),
        &Signature::from_bytes(
            &signature
                .try_into()
                .expect("fixed handshake signature field"),
        ),
    )
    .map_err(|_| Error::InvalidEvidence("invalid handshake signature"))
}

fn identity_digest(context: &Context, tag: &[u8], unsigned: &[u8]) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update(context.domain(tag));
    hash.update(unsigned);
    hash.finalize().into()
}

fn offer_digest(context: &Context, offer: &[u8]) -> [u8; 32] {
    identity_digest(context, b"handshake-offer-id", offer)
}

fn derive_keys(
    context: &Context,
    offer: &[u8],
    response: &[u8],
    shared: &SharedSecret,
    local_initiator: bool,
) -> Result<PairwiseKeys, Error> {
    if !shared.was_contributory() {
        return Err(Error::InvalidEvidence("non-contributory handshake key"));
    }
    let mut transcript = Sha256::new();
    transcript.update(context.domain(b"handshake-transcript"));
    transcript.update(offer);
    transcript.update(response);
    let salt: [u8; 32] = transcript.finalize().into();
    let hkdf = Hkdf::<Sha256>::new(Some(&salt), shared.as_bytes());
    let mut forward = Zeroizing::new([0; 32]);
    let mut reverse = Zeroizing::new([0; 32]);
    let mut binding = [0; 32];
    hkdf.expand(b"sora-arena:initiator-to-responder:v1", forward.as_mut())
        .map_err(|_| Error::Arithmetic)?;
    hkdf.expand(b"sora-arena:responder-to-initiator:v1", reverse.as_mut())
        .map_err(|_| Error::Arithmetic)?;
    hkdf.expand(b"sora-arena:channel-binding:v1", &mut binding)
        .map_err(|_| Error::Arithmetic)?;
    let (send_key, receive_key) = if local_initiator {
        (ChannelKey::new(*forward)?, ChannelKey::new(*reverse)?)
    } else {
        (ChannelKey::new(*reverse)?, ChannelKey::new(*forward)?)
    };
    Ok(PairwiseKeys {
        send_key,
        receive_key,
        channel_binding: binding,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        encrypted_wire::{EncryptedReceiver, EncryptedSender},
        rollback::Checkpoint,
        wire::{WireFrame, WireMessage},
    };

    fn fixture() -> (Context, [SigningKey; 3]) {
        let keys = [
            SigningKey::from_bytes(&[1; 32]),
            SigningKey::from_bytes(&[2; 32]),
            SigningKey::from_bytes(&[3; 32]),
        ];
        let context = Context {
            network: [21; 32],
            session: [22; 32],
            manifest: [23; 32],
            roster: keys
                .iter()
                .map(|key| key.verifying_key().to_bytes())
                .collect(),
        };
        (context, keys)
    }

    #[test]
    fn directional_keys_open_only_the_matching_signed_wire_direction() {
        let (context, identities) = fixture();
        let (initiator, offer) = Initiator::start(context.clone(), 0, 1, &identities[0]).unwrap();
        let mut replay = OfferReplayGuard::default();
        let (responder_keys, response) =
            accept_offer(&context, 0, 1, &identities[1], &offer, &mut replay).unwrap();
        let initiator_keys = initiator.finish(&response).unwrap();
        assert_eq!(
            initiator_keys.channel_binding,
            responder_keys.channel_binding
        );
        assert_eq!(
            initiator_keys.send_key.fragment_tag(b"direction-check"),
            responder_keys.receive_key.fragment_tag(b"direction-check")
        );
        assert_eq!(
            initiator_keys.receive_key.fragment_tag(b"direction-check"),
            responder_keys.send_key.fragment_tag(b"direction-check")
        );
        assert_ne!(
            initiator_keys.send_key.fragment_tag(b"direction-check"),
            initiator_keys.receive_key.fragment_tag(b"direction-check")
        );
        assert_eq!(replay.accepted_digests().len(), 1);

        let checkpoint = Checkpoint {
            epoch: 1,
            tick: 120,
            history_root: [24; 32],
            state_hash: [25; 32],
        };
        let signatures = identities
            .iter()
            .enumerate()
            .map(|(slot, key)| checkpoint.sign(&context, slot, key).unwrap())
            .collect();
        let forward = WireFrame {
            sender: 0,
            sequence: 7,
            message: WireMessage::Checkpoint {
                checkpoint,
                signatures,
            },
        };
        let mut sender = EncryptedSender::new(
            context.clone(),
            0,
            initiator_keys.channel_binding,
            initiator_keys.send_key,
            None,
        )
        .unwrap();
        let mut receiver = EncryptedReceiver::new(
            context.clone(),
            0,
            responder_keys.channel_binding,
            responder_keys.receive_key,
            None,
        )
        .unwrap();
        let sealed = sender.seal(&forward, &identities[0]).unwrap();
        assert_eq!(receiver.open(&sealed, None).unwrap(), forward);

        let reverse = WireFrame {
            sender: 1,
            sequence: 4,
            message: forward.message.clone(),
        };
        let mut sender = EncryptedSender::new(
            context.clone(),
            1,
            responder_keys.channel_binding,
            responder_keys.send_key,
            None,
        )
        .unwrap();
        let mut receiver = EncryptedReceiver::new(
            context,
            1,
            initiator_keys.channel_binding,
            initiator_keys.receive_key,
            None,
        )
        .unwrap();
        let sealed = sender.seal(&reverse, &identities[1]).unwrap();
        assert_eq!(receiver.open(&sealed, None).unwrap(), reverse);
    }

    #[test]
    fn offer_codec_rejects_tampering_truncation_and_wrong_context() {
        let (context, identities) = fixture();
        let (_, offer) = Initiator::start(context.clone(), 0, 1, &identities[0]).unwrap();
        let mut variants = Vec::new();
        variants.push(offer[..offer.len() - 1].to_vec());
        let mut extra = offer.to_vec();
        extra.push(0);
        variants.push(extra);
        for position in [
            0,
            MAGIC.len(),
            MAGIC.len() + 2,
            MAGIC.len() + 3,
            MAGIC.len() + 4,
            HEADER_BYTES,
            OFFER_PACKET_BYTES - 1,
        ] {
            let mut tampered = offer.to_vec();
            tampered[position] ^= 1;
            variants.push(tampered);
        }
        let mut replay = OfferReplayGuard::default();
        for variant in variants {
            assert!(accept_offer(&context, 0, 1, &identities[1], &variant, &mut replay).is_err());
            assert!(replay.accepted_digests().is_empty());
        }
        for field in 0..3 {
            let mut wrong = context.clone();
            match field {
                0 => wrong.network[0] ^= 1,
                1 => wrong.session[0] ^= 1,
                _ => wrong.manifest[0] ^= 1,
            }
            assert!(accept_offer(&wrong, 0, 1, &identities[1], &offer, &mut replay).is_err());
        }
        let mut reordered = context.clone();
        reordered.roster.swap(0, 2);
        assert!(accept_offer(&reordered, 0, 1, &identities[1], &offer, &mut replay).is_err());
        assert!(accept_offer(&context, 1, 0, &identities[0], &offer, &mut replay).is_err());
        assert!(Initiator::start(context, 0, 1, &identities[1]).is_err());
    }

    #[test]
    fn response_codec_and_old_offer_with_fresh_local_secret_fail_closed() {
        let (context, identities) = fixture();
        let (old_local, old_offer) =
            Initiator::start(context.clone(), 0, 1, &identities[0]).unwrap();
        let mut replay = OfferReplayGuard::default();
        let (_, response) =
            accept_offer(&context, 0, 1, &identities[1], &old_offer, &mut replay).unwrap();
        let saved = replay.accepted_digests();
        let mut restored = OfferReplayGuard::restore(saved).unwrap();
        assert!(accept_offer(&context, 0, 1, &identities[1], &old_offer, &mut restored).is_err());

        let (fresh_local, fresh_offer) =
            Initiator::start(context.clone(), 0, 1, &identities[0]).unwrap();
        assert_ne!(old_offer, fresh_offer);
        assert!(fresh_local.finish(&response).is_err());
        let mut forged = response;
        forged[RESPONSE_PACKET_BYTES - 1] ^= 1;
        assert!(old_local.finish(&forged).is_err());
    }

    #[test]
    fn response_codec_rejects_exact_length_header_and_signature_mutations() {
        let (context, identities) = fixture();
        for mutation in 0..10 {
            let (local, offer) = Initiator::start(context.clone(), 0, 1, &identities[0]).unwrap();
            let mut replay = OfferReplayGuard::default();
            let (_, response) =
                accept_offer(&context, 0, 1, &identities[1], &offer, &mut replay).unwrap();
            let altered = match mutation {
                0 => response[..response.len() - 1].to_vec(),
                1 => [response.as_slice(), &[0]].concat(),
                _ => {
                    let position = [
                        0,
                        MAGIC.len(),
                        MAGIC.len() + 2,
                        MAGIC.len() + 3,
                        MAGIC.len() + 4,
                        HEADER_BYTES,
                        HEADER_BYTES + 32,
                        RESPONSE_PACKET_BYTES - 1,
                    ][mutation - 2];
                    let mut bytes = response.to_vec();
                    bytes[position] ^= 1;
                    bytes
                }
            };
            assert!(local.finish(&altered).is_err(), "mutation {mutation}");
        }
    }

    #[test]
    fn signed_low_order_public_key_cannot_create_a_channel() {
        let (context, identities) = fixture();
        let (_, mut offer) = Initiator::start(context.clone(), 0, 1, &identities[0]).unwrap();
        offer[HEADER_BYTES..HEADER_BYTES + 32].fill(0);
        let digest = identity_digest(
            &context,
            b"handshake-offer-signature",
            &offer[..OFFER_PACKET_BYTES - SIGNATURE_BYTES],
        );
        offer[OFFER_PACKET_BYTES - SIGNATURE_BYTES..]
            .copy_from_slice(&identities[0].sign(&digest).to_bytes());
        let mut replay = OfferReplayGuard::default();
        assert!(matches!(
            accept_offer(&context, 0, 1, &identities[1], &offer, &mut replay),
            Err(Error::InvalidEvidence("non-contributory handshake key"))
        ));
        assert!(replay.accepted_digests().is_empty());
    }

    #[test]
    fn accepted_offer_limit_rejects_new_channels_without_growing_state() {
        let (context, identities) = fixture();
        let hashes = (0..MAX_ACCEPTED_OFFERS_PER_MATCH)
            .map(|index| {
                let mut hash = [0; 32];
                hash[..8].copy_from_slice(&(index as u64).to_le_bytes());
                hash
            })
            .collect::<Vec<_>>();
        let mut replay = OfferReplayGuard::restore(hashes.clone()).unwrap();
        let (_, offer) = Initiator::start(context.clone(), 0, 1, &identities[0]).unwrap();
        assert!(matches!(
            accept_offer(&context, 0, 1, &identities[1], &offer, &mut replay),
            Err(Error::InvalidEvidence("handshake replay guard is full"))
        ));
        assert_eq!(
            replay.accepted_digests().len(),
            MAX_ACCEPTED_OFFERS_PER_MATCH
        );
        let mut over_limit = hashes;
        over_limit.push([255; 32]);
        assert!(matches!(
            OfferReplayGuard::restore(over_limit),
            Err(Error::InvalidEvidence("handshake replay guard is full"))
        ));
    }
}
