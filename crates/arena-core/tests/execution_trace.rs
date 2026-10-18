//! Adversarial checks for the local full-state execution trace, not a chain proof.

use std::io::{self, Cursor, Read, Write};

use arena_core::{
    execution_trace::{TraceSummary, verify_trace, write_trace},
    protocol::{CommitmentSet, Context, DeadlineResolution, Phase, Reveal, sign_commitment_set},
    rollback::RollbackSession,
    simulation::{ABILITY, BLOCK, Config, FIRE, Input, JUMP, Mode, Participant, World},
};
use ed25519_dalek::SigningKey;
use sha2::{Digest, Sha256};

struct Fixture {
    config: Config,
    participants: Vec<Participant>,
    keys: Vec<SigningKey>,
    session: RollbackSession,
}

impl Fixture {
    fn new(mode: Mode, max_ticks: u32, players: usize) -> Self {
        let config = Config {
            mode,
            map: 0,
            max_ticks,
            base_bond: 1000,
            offline: false,
        };
        let participants = (0..players)
            .map(|slot| Participant {
                team: (slot % 2) as u8,
                class: 0,
                weapon: if mode == Mode::Melee { 0 } else { 1 },
                bond: 1000,
                special_entitled: false,
            })
            .collect::<Vec<_>>();
        let keys = (0..players)
            .map(|slot| SigningKey::from_bytes(&[31 + slot as u8; 32]))
            .collect::<Vec<_>>();
        let context = Context {
            network: [1; 32],
            session: [2; 32],
            manifest: [3; 32],
            roster: keys
                .iter()
                .map(|key| key.verifying_key().to_bytes())
                .collect(),
        };
        let session = RollbackSession::new(context, config.clone(), &participants).unwrap();
        Self {
            config,
            participants,
            keys,
            session,
        }
    }

    fn certify(&mut self, frames: &[Vec<Input>], salt_tag: u8) -> Vec<Reveal> {
        assert_eq!(frames.len(), 2);
        assert!(frames.iter().all(|frame| frame.len() == self.keys.len()));
        let log = self.session.evidence();
        let reveals = (0..self.keys.len())
            .map(|slot| Reveal {
                start_tick: log.certified_tick,
                slot,
                salt: [salt_tag.wrapping_add(slot as u8); 32],
                inputs: frames.iter().map(|frame| frame[slot]).collect(),
            })
            .collect::<Vec<_>>();
        let set = CommitmentSet {
            epoch: log.epoch,
            start_tick: log.certified_tick,
            parent: log.commitment_head,
            commitments: reveals
                .iter()
                .map(|reveal| reveal.commitment(&log.context, log.epoch).unwrap())
                .collect(),
        };
        let signatures = self
            .keys
            .iter()
            .enumerate()
            .map(|(slot, key)| sign_commitment_set(&log.context, &set, slot, key).unwrap())
            .collect();
        self.session.certify(set, signatures).unwrap();
        reveals
    }

    fn advance(&mut self, frames: &[Vec<Input>], salt_tag: u8) {
        let reveals = self.certify(frames, salt_tag);
        self.session.open(reveals).unwrap();
        self.session.advance().unwrap();
    }

    fn trace(&self) -> (Vec<u8>, TraceSummary) {
        let mut bytes = Vec::new();
        let summary = write_trace(
            self.config.clone(),
            &self.participants,
            &self.session,
            &mut bytes,
        )
        .unwrap();
        (bytes, summary)
    }

    fn verify(
        &self,
        bytes: &[u8],
    ) -> Result<TraceSummary, arena_core::execution_trace::TraceError> {
        verify_trace(
            self.config.clone(),
            &self.participants,
            &self.session,
            bytes,
        )
    }
}

fn idle(players: usize) -> Vec<Vec<Input>> {
    vec![vec![Input::default(); players]; 2]
}

#[test]
fn every_mode_replays_complete_certified_history_and_exports_exact_roots() {
    for mode in [Mode::FreeForAll, Mode::Control, Mode::Payload, Mode::Melee] {
        let mut fixture = Fixture::new(mode, 6, 2);
        let mut reference = World::new(fixture.config.clone(), &fixture.participants).unwrap();
        let mut boundaries = vec![reference.state_bytes()];
        for batch in 0..3 {
            let frames = vec![
                vec![
                    Input {
                        buttons: JUMP | ABILITY,
                        move_x: 127,
                        yaw: 16384,
                        ..Input::default()
                    },
                    Input {
                        buttons: BLOCK,
                        move_y: -63,
                        ..Input::default()
                    },
                ],
                vec![
                    Input {
                        buttons: FIRE,
                        move_y: 43,
                        ..Input::default()
                    },
                    Input {
                        move_x: -127,
                        yaw: 32768,
                        ..Input::default()
                    },
                ],
            ];
            for frame in &frames {
                reference.step(frame).unwrap();
                boundaries.push(reference.state_bytes());
            }
            fixture.advance(&frames, 50 + batch);
        }
        fixture.session.finish_local().unwrap();
        let (bytes, summary) = fixture.trace();
        let verified = fixture.verify(&bytes).unwrap();
        assert_eq!(summary.tick, 6);
        assert_eq!(summary.evidence_tick, 6);
        assert_eq!(summary.certified_tick, 6);
        assert_eq!(summary.pending_frontiers, 0);
        assert!(summary.completed);
        assert_eq!(summary.phase, Phase::Terminal);
        assert_eq!(summary.state_hash, fixture.session.confirmed().state_hash());
        assert_eq!(summary.history_root, fixture.session.evidence().root);
        assert_eq!(summary.encoded_bytes as usize, bytes.len());
        assert_eq!(verified.trace_digest, summary.trace_digest);
        assert_eq!(verified.state_hash, summary.state_hash);
        assert_eq!(reference.state_hash(), summary.state_hash);
        for (tick, boundary) in boundaries.iter().enumerate() {
            assert_eq!(
                bytes
                    .windows(boundary.len())
                    .filter(|window| *window == boundary)
                    .count(),
                1,
                "full independently replayed boundary {tick} missing or duplicated in {mode:?}"
            );
        }
        assert_eq!(
            fixture.trace().0,
            bytes,
            "trace encoding must be reproducible"
        );
    }
}

#[test]
fn pending_frontiers_are_retained_without_execution_after_dropout() {
    let mut fixture = Fixture::new(Mode::FreeForAll, 20, 2);
    let first = fixture.certify(&idle(2), 71);
    fixture.session.open(vec![first[0].clone()]).unwrap();
    let second = fixture.certify(&idle(2), 73);
    fixture.session.open(second).unwrap();
    fixture.session.advance().unwrap();
    fixture.session.interrupt();
    let (bytes, summary) = fixture.trace();
    assert_eq!(summary.tick, 0);
    assert_eq!(summary.evidence_tick, 0);
    assert_eq!(summary.certified_tick, 4);
    assert_eq!(summary.pending_frontiers, 2);
    assert!(!summary.completed);
    assert_eq!(summary.phase, Phase::Resolving);
    fixture.verify(&bytes).unwrap();

    // Both retained openings and still-missing openings matter, even though
    // they have not changed the confirmed World or closed-history root.
    fixture.session.open(vec![first[1].clone()]).unwrap();
    assert_eq!(fixture.session.confirmed().tick, 0);
    assert_eq!(fixture.session.evidence().root, summary.history_root);
    assert!(fixture.verify(&bytes).is_err());
}

#[test]
fn odd_terminal_batch_binds_the_unexecuted_second_control() {
    let mut original = Fixture::new(Mode::FreeForAll, 3, 2);
    let mut altered = Fixture::new(Mode::FreeForAll, 3, 2);
    original.advance(&idle(2), 80);
    altered.advance(&idle(2), 80);
    original.advance(&idle(2), 82);
    let mut final_frames = idle(2);
    final_frames[1][0].buttons = FIRE | JUMP;
    final_frames[1][0].move_x = 127;
    altered.advance(&final_frames, 82);
    original.session.finish_local().unwrap();
    altered.session.finish_local().unwrap();
    assert_eq!(
        original.session.confirmed().state_hash(),
        altered.session.confirmed().state_hash()
    );
    let (bytes, summary) = original.trace();
    assert_eq!(summary.tick, 3);
    assert_eq!(summary.evidence_tick, 4);
    assert_eq!(summary.certified_tick, 4);
    assert!(summary.completed);
    assert_ne!(summary.history_root, altered.session.evidence().root);
    assert!(altered.verify(&bytes).is_err());
    assert_ne!(bytes, altered.trace().0);
}

#[test]
fn out_of_order_reveals_still_export_the_canonical_tick_order() {
    let mut fixture = Fixture::new(Mode::FreeForAll, 3, 2);
    // A ready second frontier remains pending until advance consumes the
    // first; the final clock then ends halfway through the second batch.
    let first = fixture.certify(&idle(2), 90);
    let second = fixture.certify(&idle(2), 92);
    fixture.session.open(second).unwrap();
    fixture.session.open(first).unwrap();
    fixture.session.advance().unwrap();
    fixture.session.finish_local().unwrap();
    let (bytes, summary) = fixture.trace();
    assert_eq!(summary.tick, 3);
    assert_eq!(summary.evidence_tick, 4);
    assert_eq!(summary.pending_frontiers, 0);
    fixture.verify(&bytes).unwrap();
}

#[test]
fn every_byte_of_a_one_tick_trace_is_authenticated() {
    let mut fixture = Fixture::new(Mode::FreeForAll, 1, 1);
    fixture.advance(&idle(1), 100);
    fixture.session.finish_local().unwrap();
    let (bytes, _) = fixture.trace();
    fixture.verify(&bytes).unwrap();
    for offset in 0..bytes.len() {
        let mut altered = bytes.clone();
        altered[offset] ^= 1;
        assert!(
            fixture.verify(&altered).is_err(),
            "accepted altered byte {offset}"
        );
    }
}

#[test]
fn truncated_duplicated_reordered_and_trailing_trace_bytes_are_rejected() {
    let mut fixture = Fixture::new(Mode::FreeForAll, 4, 2);
    fixture.advance(&idle(2), 110);
    fixture.advance(&idle(2), 112);
    let (bytes, _) = fixture.trace();
    for end in [0, 1, bytes.len() / 3, bytes.len() / 2, bytes.len() - 1] {
        assert!(
            fixture.verify(&bytes[..end]).is_err(),
            "accepted truncation at {end}"
        );
    }
    let middle = bytes.len() / 2;
    let mut duplicate = bytes.clone();
    duplicate.splice(middle..middle, bytes[middle..middle + 16].iter().copied());
    assert!(fixture.verify(&duplicate).is_err());
    let mut omitted = bytes.clone();
    omitted.drain(middle..middle + 16);
    assert!(fixture.verify(&omitted).is_err());
    let mut reordered = bytes.clone();
    reordered.rotate_left(middle);
    assert!(fixture.verify(&reordered).is_err());
    let mut trailing = bytes.clone();
    trailing.push(0);
    assert!(fixture.verify(&trailing).is_err());
    let mut appended = bytes.clone();
    appended.extend_from_slice(&bytes);
    assert!(fixture.verify(&appended).is_err());
    // A self-consistent file seal cannot authenticate a false state or input.
    let mut resealed = bytes.clone();
    resealed[middle] ^= 1;
    let seal = resealed.len() - 32;
    let digest: [u8; 32] = Sha256::digest(&resealed[..seal]).into();
    resealed[seal..].copy_from_slice(&digest);
    assert!(fixture.verify(&resealed).is_err());
}

#[test]
fn original_config_and_participant_terms_cannot_be_substituted() {
    let mut fixture = Fixture::new(Mode::FreeForAll, 4, 2);
    fixture.advance(&idle(2), 120);
    let (bytes, _) = fixture.trace();
    let mut config = fixture.config.clone();
    config.map = 1;
    assert!(
        write_trace(
            config.clone(),
            &fixture.participants,
            &fixture.session,
            Vec::new()
        )
        .is_err()
    );
    assert!(
        verify_trace(
            config,
            &fixture.participants,
            &fixture.session,
            bytes.as_slice()
        )
        .is_err()
    );
    let mut config = fixture.config.clone();
    config.max_ticks += 2;
    assert!(write_trace(config, &fixture.participants, &fixture.session, Vec::new()).is_err());
    let mut participants = fixture.participants.clone();
    participants[0].team ^= 1;
    assert!(
        write_trace(
            fixture.config.clone(),
            &participants,
            &fixture.session,
            Vec::new()
        )
        .is_err()
    );
    assert!(
        verify_trace(
            fixture.config.clone(),
            &participants,
            &fixture.session,
            bytes.as_slice()
        )
        .is_err()
    );
    participants = fixture.participants.clone();
    participants[0].bond += 10;
    assert!(
        write_trace(
            fixture.config.clone(),
            &participants,
            &fixture.session,
            Vec::new()
        )
        .is_err()
    );
    participants = fixture.participants.clone();
    participants.swap(0, 1);
    assert!(
        verify_trace(
            fixture.config.clone(),
            &participants,
            &fixture.session,
            bytes.as_slice()
        )
        .is_err()
    );
    // For an ordinary weapon this flag does not change the World, but the
    // trace must still bind the caller's exact original admission bytes.
    participants = fixture.participants.clone();
    participants[0].special_entitled = true;
    assert!(
        verify_trace(
            fixture.config.clone(),
            &participants,
            &fixture.session,
            bytes.as_slice()
        )
        .is_err()
    );
    assert!(
        write_trace(
            fixture.config.clone(),
            &participants[..1],
            &fixture.session,
            Vec::new()
        )
        .is_err()
    );
}

#[test]
fn changed_signed_history_is_rejected_even_when_the_final_world_matches() {
    let mut original = Fixture::new(Mode::FreeForAll, 4, 2);
    let mut changed = Fixture::new(Mode::FreeForAll, 4, 2);
    original.advance(&idle(2), 130);
    changed.advance(&idle(2), 131);
    assert_eq!(
        original.session.confirmed().state_hash(),
        changed.session.confirmed().state_hash()
    );
    let (bytes, summary) = original.trace();
    assert_ne!(summary.history_root, changed.session.evidence().root);
    assert!(changed.verify(&bytes).is_err());
}

#[test]
fn pending_and_closed_consensus_deadlines_require_external_verification() {
    for advance in [false, true] {
        let mut fixture = Fixture::new(Mode::FreeForAll, 6, 2);
        let reveals = fixture.certify(&idle(2), 140);
        let frontier = fixture.session.evidence().pending[0].digest;
        fixture
            .session
            .attach_deadline(&DeadlineResolution {
                start_tick: 0,
                frontier,
                attestation: [42; 32],
                openings: vec![Some(reveals[0].clone()), None],
            })
            .unwrap();
        if advance {
            fixture.session.advance().unwrap();
        }
        assert!(
            write_trace(
                fixture.config.clone(),
                &fixture.participants,
                &fixture.session,
                Vec::new()
            )
            .is_err()
        );
    }
}

struct FailWriter {
    remaining: usize,
}
impl Write for FailWriter {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        if self.remaining == 0 {
            return Err(io::Error::other("injected write failure"));
        }
        let written = bytes.len().min(self.remaining);
        self.remaining -= written;
        Ok(written)
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

struct FailReader<'a> {
    input: Cursor<&'a [u8]>,
    fail_at: usize,
}

struct FailFlush;
impl Write for FailFlush {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        Ok(bytes.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Err(io::Error::other("injected flush failure"))
    }
}
impl Read for FailReader<'_> {
    fn read(&mut self, bytes: &mut [u8]) -> io::Result<usize> {
        let position = self.input.position() as usize;
        if position >= self.fail_at {
            return Err(io::Error::other("injected read failure"));
        }
        let count = bytes.len().min(self.fail_at - position);
        self.input.read(&mut bytes[..count])
    }
}

#[test]
fn partial_output_input_and_eof_io_failures_propagate() {
    let mut fixture = Fixture::new(Mode::FreeForAll, 2, 2);
    fixture.advance(&idle(2), 150);
    let (bytes, _) = fixture.trace();
    for remaining in [0, 7, bytes.len() / 2, bytes.len() - 1] {
        assert!(
            write_trace(
                fixture.config.clone(),
                &fixture.participants,
                &fixture.session,
                FailWriter { remaining }
            )
            .is_err()
        );
    }
    assert!(
        write_trace(
            fixture.config.clone(),
            &fixture.participants,
            &fixture.session,
            FailFlush
        )
        .is_err()
    );
    for fail_at in [0, 7, bytes.len() / 2, bytes.len()] {
        assert!(
            verify_trace(
                fixture.config.clone(),
                &fixture.participants,
                &fixture.session,
                FailReader {
                    input: Cursor::new(bytes.as_slice()),
                    fail_at
                }
            )
            .is_err()
        );
    }
}
