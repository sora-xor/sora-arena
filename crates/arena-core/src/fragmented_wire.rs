//! Bounded, authenticated datagram framing for sealed peer packets.
//!
//! Each fragment has an independently verified HMAC under a domain-separated
//! channel key. The complete packet is still checked by AEAD and Ed25519.
//! A receiver retains at most four incomplete packets for one peer.

use sha2::{Digest, Sha256};

use crate::{
    Error,
    encrypted_wire::{ChannelKey, MAX_ENCRYPTED_PACKET_BYTES},
};

const MAGIC: &[u8] = b"SORA-ARENA-FRAG";
const VERSION: u16 = 1;
pub const MAX_DATAGRAM_BYTES: usize = 1_200;
const TAG_BYTES: usize = 32;
const HEADER_BYTES: usize = MAGIC.len() + 2 + 1 + 8 + 2 + 1 + 1 + 32 + 2;
const CHUNK_BYTES: usize = MAX_DATAGRAM_BYTES - HEADER_BYTES - TAG_BYTES;
const MAX_PENDING: usize = 4;

pub(crate) fn fragment_packet(
    packet: &[u8],
    sender: usize,
    sequence: u64,
    key: &ChannelKey,
) -> Result<Vec<Vec<u8>>, Error> {
    if packet.is_empty() || packet.len() > MAX_ENCRYPTED_PACKET_BYTES || sender > u8::MAX as usize {
        return Err(Error::InvalidEvidence("fragment source outside bound"));
    }
    let count = packet.len().div_ceil(CHUNK_BYTES);
    let count = u8::try_from(count).map_err(|_| Error::Arithmetic)?;
    let total = u16::try_from(packet.len()).map_err(|_| Error::Arithmetic)?;
    let digest: [u8; 32] = Sha256::digest(packet).into();
    let mut out = Vec::with_capacity(count as usize);
    for (index, chunk) in packet.chunks(CHUNK_BYTES).enumerate() {
        let mut fragment = Vec::with_capacity(HEADER_BYTES + chunk.len() + TAG_BYTES);
        fragment.extend(MAGIC);
        fragment.extend(VERSION.to_le_bytes());
        fragment.push(sender as u8);
        fragment.extend(sequence.to_le_bytes());
        fragment.extend(total.to_le_bytes());
        fragment.push(count);
        fragment.push(index as u8);
        fragment.extend(digest);
        fragment.extend((chunk.len() as u16).to_le_bytes());
        fragment.extend(chunk);
        let tag = key.fragment_tag(&fragment);
        fragment.extend(tag);
        debug_assert!(fragment.len() <= MAX_DATAGRAM_BYTES);
        out.push(fragment);
    }
    Ok(out)
}

struct PendingPacket {
    sequence: u64,
    total: usize,
    digest: [u8; 32],
    chunks: Vec<Option<Vec<u8>>>,
    received: usize,
}

pub(crate) enum FragmentResult {
    Pending,
    Complete(Vec<u8>),
    /// A fragment from a previously authenticated complete packet. The
    /// caller may re-ACK it, but must not deliver its evidence twice.
    AcceptedReplay(u64),
    /// An authenticated new fragment cannot be accepted while the caller's
    /// delivery queue is full. No pending-fragment state has been changed.
    AtCapacity,
}

#[derive(Default)]
pub(crate) struct FragmentAssembler {
    pending: Vec<PendingPacket>,
}

impl FragmentAssembler {
    pub(crate) fn forget_through(&mut self, sequence: u64) {
        self.pending.retain(|packet| packet.sequence > sequence);
    }

    pub(crate) fn push(
        &mut self,
        fragment: &[u8],
        expected_sender: usize,
        floor: Option<u64>,
        key: &ChannelKey,
        accepted: &[(u64, [u8; 32])],
        accept_new: bool,
    ) -> Result<FragmentResult, Error> {
        if !(HEADER_BYTES + TAG_BYTES..=MAX_DATAGRAM_BYTES).contains(&fragment.len()) {
            return Err(Error::InvalidEvidence("fragment length outside bound"));
        }
        let authenticated_len = fragment.len() - TAG_BYTES;
        key.verify_fragment_tag(
            &fragment[..authenticated_len],
            &fragment[authenticated_len..],
        )?;
        let mut at = 0;
        if take(fragment, &mut at, MAGIC.len())? != MAGIC {
            return Err(Error::InvalidEvidence("fragment magic differs"));
        }
        let version = u16::from_le_bytes(take_array(fragment, &mut at)?);
        if version != VERSION {
            return Err(Error::InvalidEvidence("fragment version differs"));
        }
        let sender = take(fragment, &mut at, 1)?[0] as usize;
        if sender != expected_sender {
            return Err(Error::InvalidEvidence("fragment sender differs"));
        }
        let sequence = u64::from_le_bytes(take_array(fragment, &mut at)?);
        let total = u16::from_le_bytes(take_array(fragment, &mut at)?) as usize;
        let count = take(fragment, &mut at, 1)?[0] as usize;
        let index = take(fragment, &mut at, 1)?[0] as usize;
        let digest: [u8; 32] = take_array(fragment, &mut at)?;
        let chunk_len = u16::from_le_bytes(take_array(fragment, &mut at)?) as usize;
        if total == 0 || total > MAX_ENCRYPTED_PACKET_BYTES {
            return Err(Error::InvalidEvidence("fragment total outside bound"));
        }
        if count != total.div_ceil(CHUNK_BYTES) || index >= count {
            return Err(Error::InvalidEvidence("fragment count or index differs"));
        }
        let offset = index * CHUNK_BYTES;
        let expected_len = (total - offset).min(CHUNK_BYTES);
        if chunk_len != expected_len || at + chunk_len != authenticated_len {
            return Err(Error::InvalidEvidence("fragment chunk length differs"));
        }
        if floor.is_some_and(|floor| sequence <= floor) {
            if accepted.iter().any(|(old_sequence, old_digest)| {
                *old_sequence == sequence && *old_digest == digest
            }) {
                return Ok(FragmentResult::AcceptedReplay(sequence));
            }
            return Err(Error::InvalidEvidence("fragment replay or reordering"));
        }
        if !accept_new {
            return Ok(FragmentResult::AtCapacity);
        }
        let chunk = &fragment[at..authenticated_len];
        let slot = match self.pending.iter().position(|p| p.sequence == sequence) {
            Some(slot) => slot,
            None => {
                if self.pending.len() >= MAX_PENDING {
                    // Lost tails must not permanently fill the bounded window.
                    // A newer authenticated sequence replaces its oldest
                    // incomplete predecessor without advancing the replay floor.
                    let (oldest, packet) = self
                        .pending
                        .iter()
                        .enumerate()
                        .min_by_key(|(_, packet)| packet.sequence)
                        .expect("full pending window has an oldest packet");
                    if sequence <= packet.sequence {
                        return Err(Error::InvalidEvidence("fragment outside pending window"));
                    }
                    self.pending.swap_remove(oldest);
                }
                self.pending.push(PendingPacket {
                    sequence,
                    total,
                    digest,
                    chunks: vec![None; count],
                    received: 0,
                });
                self.pending.len() - 1
            }
        };
        let pending = &mut self.pending[slot];
        if pending.total != total || pending.digest != digest || pending.chunks.len() != count {
            return Err(Error::InvalidEvidence("conflicting fragment identity"));
        }
        if let Some(existing) = &pending.chunks[index] {
            if existing == chunk {
                return Ok(FragmentResult::Pending);
            }
            return Err(Error::InvalidEvidence("conflicting fragment payload"));
        }
        pending.chunks[index] = Some(chunk.to_vec());
        pending.received += 1;
        if pending.received != count {
            return Ok(FragmentResult::Pending);
        }
        let complete = self.pending.swap_remove(slot);
        let mut packet = Vec::with_capacity(total);
        for chunk in complete.chunks {
            packet.extend(chunk.expect("received all authenticated fragments"));
        }
        if packet.len() != total || Sha256::digest(&packet).as_slice() != digest {
            return Err(Error::InvalidEvidence("reassembled packet hash differs"));
        }
        Ok(FragmentResult::Complete(packet))
    }
}

fn take<'a>(bytes: &'a [u8], at: &mut usize, len: usize) -> Result<&'a [u8], Error> {
    let end = at.checked_add(len).ok_or(Error::Arithmetic)?;
    let field = bytes
        .get(*at..end)
        .ok_or(Error::InvalidEvidence("truncated fragment"))?;
    *at = end;
    Ok(field)
}

fn take_array<const N: usize>(bytes: &[u8], at: &mut usize) -> Result<[u8; N], Error> {
    Ok(take(bytes, at, N)?
        .try_into()
        .expect("checked fragment field width"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn missing_tails_cannot_permanently_fill_receive_window() {
        let key = ChannelKey::new([91; 32]).unwrap();
        let mut receiver = FragmentAssembler::default();
        for sequence in 1..=4 {
            let packet = vec![sequence as u8; MAX_ENCRYPTED_PACKET_BYTES];
            let fragments = fragment_packet(&packet, 0, sequence, &key).unwrap();
            assert_eq!(fragments.len(), 2);
            assert!(matches!(
                receiver
                    .push(&fragments[0], 0, None, &key, &[], true)
                    .unwrap(),
                FragmentResult::Pending
            ));
        }
        let stale = fragment_packet(&vec![0; MAX_ENCRYPTED_PACKET_BYTES], 0, 0, &key).unwrap();
        assert!(receiver.push(&stale[0], 0, None, &key, &[], true).is_err());
        let next = vec![55; 100];
        let fragments = fragment_packet(&next, 0, 5, &key).unwrap();
        assert_eq!(fragments.len(), 1);
        assert!(matches!(
            receiver
                .push(&fragments[0], 0, None, &key, &[], true)
                .unwrap(),
            FragmentResult::Complete(bytes) if bytes == next
        ));
    }
}
