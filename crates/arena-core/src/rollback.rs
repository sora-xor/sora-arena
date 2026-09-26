//! Bounded local prediction over one certified input timeline.
//!
//! Predicted events never enter the certified world. A checkpoint is evidence
//! signed by gameplay keys, not a ledger authorization or an execution proof.
//! Pipelined frontiers close in tick order, so the confirmed world is the same
//! however many were in flight. On dropout combat stops; the confirmed world
//! then advances only through frontiers already certified, closed by complete
//! openings or by native consensus's deadline decision.
use std::collections::VecDeque;

use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use sha2::{Digest, Sha256};

use crate::{
    Error,
    protocol::{
        BATCH_TICKS, CommitmentSet, Context, DeadlineResolution, EvidenceLog, Hash,
        INPUT_DELAY_TICKS, MAX_ASSEMBLY_FRONTIERS, MAX_OUTSTANDING_FRONTIERS, PendingFrontier,
        Phase, Reveal, SlotSignature,
    },
    simulation::{Config, Input, Participant, World},
};

pub const MAX_PREDICTION_TICKS: usize = 120;
/// Recent closed-batch boundaries a checkpoint may name. Pipelined peers
/// confirm at slightly different times, so a checkpoint for a boundary this
/// peer has already passed is still checked against the exact state there.
pub const CHECKPOINT_WINDOW: usize = 2 * MAX_OUTSTANDING_FRONTIERS + 1;
// A peer can keep presenting across a full assembly window, a full
// certified pipeline and the input delay without exhausting prediction.
const _: () = assert!(
    (MAX_ASSEMBLY_FRONTIERS + MAX_OUTSTANDING_FRONTIERS) * BATCH_TICKS + INPUT_DELAY_TICKS as usize
        <= MAX_PREDICTION_TICKS
);

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Checkpoint {
    pub epoch: u64,
    pub tick: u32,
    pub history_root: Hash,
    pub state_hash: Hash,
}

impl Checkpoint {
    fn digest(&self, context: &Context) -> Result<Hash, Error> {
        context.validate()?;
        let mut bytes = context.domain(b"certified-simulation-checkpoint");
        bytes.extend(self.epoch.to_le_bytes());
        bytes.extend(self.tick.to_le_bytes());
        bytes.extend(self.history_root);
        bytes.extend(self.state_hash);
        Ok(Sha256::digest(bytes).into())
    }

    pub fn sign(
        &self,
        context: &Context,
        slot: usize,
        key: &SigningKey,
    ) -> Result<SlotSignature, Error> {
        if context.roster.get(slot) != Some(&key.verifying_key().to_bytes()) {
            return Err(Error::InvalidEvidence("checkpoint key does not own slot"));
        }
        Ok(SlotSignature {
            slot,
            signature: key.sign(&self.digest(context)?).to_bytes(),
        })
    }

    pub(crate) fn verify(
        &self,
        context: &Context,
        signatures: &[SlotSignature],
    ) -> Result<(), Error> {
        let digest = self.digest(context)?;
        if signatures.len() != context.roster.len() {
            return Err(Error::InvalidEvidence(
                "checkpoint requires complete roster",
            ));
        }
        for (slot, signature) in signatures.iter().enumerate() {
            if signature.slot != slot {
                return Err(Error::InvalidEvidence("checkpoint signatures out of order"));
            }
            verify_digest(context, &digest, signature)?;
        }
        Ok(())
    }

    /// One roster key's signature over this checkpoint, as peers gather
    /// them before a complete set can be retained.
    pub(crate) fn verify_signature(
        &self,
        context: &Context,
        signature: &SlotSignature,
    ) -> Result<(), Error> {
        if signature.slot >= context.roster.len() {
            return Err(Error::InvalidEvidence("checkpoint slot outside roster"));
        }
        verify_digest(context, &self.digest(context)?, signature)
    }
}

fn verify_digest(context: &Context, digest: &Hash, signature: &SlotSignature) -> Result<(), Error> {
    VerifyingKey::from_bytes(&context.roster[signature.slot])
        .map_err(|_| Error::InvalidEvidence("invalid checkpoint key"))?
        .verify_strict(digest, &Signature::from_bytes(&signature.signature))
        .map_err(|_| Error::InvalidEvidence("invalid checkpoint signature"))
}

#[derive(Debug, Clone)]
pub struct CertifiedCheckpoint {
    pub checkpoint: Checkpoint,
    pub signatures: Vec<SlotSignature>,
}

/// The end of a match as it follows from retained evidence alone: certified
/// frontiers, their openings and consensus deadlines. No final signature is
/// part of it, so a peer that refuses to sign cannot erase a death that its
/// certified inputs already produced. It is dispute material for native
/// settlement; nothing here releases a reserve or an award.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TerminalOutcome {
    pub epoch: u64,
    /// The last executed combat tick.
    pub tick: u32,
    /// First tick after the last closed frontier.
    pub evidence_tick: u32,
    pub history_root: Hash,
    pub state_hash: Hash,
    /// The kernel's own clock or objective ended combat. Otherwise a dropout
    /// stopped it and the state is the last one the evidence reached.
    pub completed: bool,
    /// Closed frontiers in which consensus forfeited at least one opening.
    pub deadline_frontiers: u32,
}

#[derive(Debug, Clone)]
pub struct RollbackSession {
    evidence: EvidenceLog,
    confirmed: World,
    predicted: World,
    prediction: VecDeque<(u32, Vec<Input>)>,
    boundaries: VecDeque<Checkpoint>,
    last_checkpoint: Option<CertifiedCheckpoint>,
}

impl RollbackSession {
    /// The admission adapter must authenticate the context and roster ordering.
    /// This constructor has no access to a chain and cannot verify NFT ownership.
    pub fn new(
        context: Context,
        config: Config,
        participants: &[Participant],
    ) -> Result<Self, Error> {
        if context.roster.len() != participants.len() {
            return Err(Error::InvalidConfig("evidence and combat rosters differ"));
        }
        let evidence = EvidenceLog::new(context)?;
        let confirmed = World::new(config, participants)?;
        let mut session = Self {
            predicted: confirmed.clone(),
            confirmed,
            evidence,
            prediction: VecDeque::new(),
            boundaries: VecDeque::new(),
            last_checkpoint: None,
        };
        session.boundaries.push_back(session.checkpoint());
        Ok(session)
    }

    pub fn evidence(&self) -> &EvidenceLog {
        &self.evidence
    }
    pub fn confirmed(&self) -> &World {
        &self.confirmed
    }
    pub fn predicted(&self) -> &World {
        &self.predicted
    }
    pub fn last_checkpoint(&self) -> Option<&CertifiedCheckpoint> {
        self.last_checkpoint.as_ref()
    }
    /// The checkpoint of a recent closed-batch boundary at `tick`, within
    /// `CHECKPOINT_WINDOW`, so a peer that confirmed several frontiers at
    /// once can still sign each boundary it passed.
    pub fn boundary(&self, tick: u32) -> Option<&Checkpoint> {
        self.boundaries
            .iter()
            .find(|checkpoint| checkpoint.tick == tick)
    }

    /// Run speculative presentation using canonical controls, never a reported hit.
    pub fn predict(&mut self, inputs: Vec<Input>) -> Result<(), Error> {
        if self.evidence.phase != Phase::Live {
            return Err(Error::InvalidEvidence("prediction stopped for resolution"));
        }
        if self.prediction.len() >= MAX_PREDICTION_TICKS {
            return Err(Error::InvalidEvidence("prediction horizon exhausted"));
        }
        let tick = self.predicted.tick;
        let mut next = self.predicted.clone();
        next.step(&inputs)?;
        self.predicted = next;
        self.prediction.push_back((tick, inputs));
        Ok(())
    }

    /// A frontier beyond the match clock, or after combat ended, could never
    /// execute and is refused.
    pub fn certify(
        &mut self,
        set: CommitmentSet,
        signatures: Vec<SlotSignature>,
    ) -> Result<(), Error> {
        if self.confirmed.terminal {
            return Err(Error::Terminal);
        }
        if set.start_tick >= self.confirmed.config.max_ticks {
            return Err(Error::InvalidEvidence("frontier after the match clock"));
        }
        self.evidence.certify(set, signatures)
    }

    /// Retain openings of any pending frontiers without executing them. The
    /// whole group is validated first; an invalid member changes nothing.
    pub fn open(&mut self, reveals: Vec<Reveal>) -> Result<(), Error> {
        let mut next = self.evidence.clone();
        for reveal in reveals {
            next.open(reveal)?;
        }
        self.evidence = next;
        Ok(())
    }

    /// Attach native consensus's deadline decision without executing it.
    /// This stops combat and discards prediction.
    pub fn attach_deadline(&mut self, resolution: &DeadlineResolution) -> Result<(), Error> {
        let mut next = self.evidence.clone();
        next.resolve_deadline(resolution)?;
        self.evidence = next;
        self.stop_prediction();
        Ok(())
    }

    /// Execute every ready frontier in tick order, each atomically. On an
    /// execution failure the frontiers before it stay applied and the failing
    /// one stays pending with its openings for dispute resolution. After
    /// combat is terminal, later frontiers are void and are not executed.
    pub fn advance(&mut self) -> Result<(), Error> {
        let mut outcome = Ok(());
        let mut advanced = false;
        while !self.confirmed.terminal
            && self
                .evidence
                .pending
                .front()
                .is_some_and(PendingFrontier::ready)
        {
            if let Err(error) = self.execute_next() {
                outcome = Err(error);
                break;
            }
            advanced = true;
        }
        if advanced {
            self.rebase_prediction();
        }
        outcome
    }

    fn execute_next(&mut self) -> Result<(), Error> {
        let mut next_evidence = self.evidence.clone();
        let Some(inputs) = next_evidence.close_next()? else {
            return Ok(());
        };
        let mut next_world = self.confirmed.clone();
        for frame in inputs {
            // A certified batch may extend beyond an objective or clock
            // ending the match. Retain every committed/revealed byte, but
            // execute no controls after the first terminal transition.
            if next_world.terminal {
                break;
            }
            next_world.step(&frame)?;
        }
        if next_world.tick > next_evidence.next_tick
            || (!next_world.terminal && next_world.tick != next_evidence.next_tick)
        {
            return Err(Error::InvalidEvidence(
                "combat and transcript clocks differ",
            ));
        }
        self.evidence = next_evidence;
        self.confirmed = next_world;
        self.boundaries.push_back(self.checkpoint());
        if self.boundaries.len() > CHECKPOINT_WINDOW {
            self.boundaries.pop_front();
        }
        Ok(())
    }

    /// Replay retained speculative controls from the new confirmed state.
    /// Presentation is never evidence, so a gap only discards speculation.
    fn rebase_prediction(&mut self) {
        while self
            .prediction
            .front()
            .is_some_and(|(tick, _)| *tick < self.confirmed.tick)
        {
            self.prediction.pop_front();
        }
        let mut presentation = self.confirmed.clone();
        if self.evidence.phase != Phase::Live || presentation.terminal {
            self.prediction.clear();
        } else {
            let mut kept = 0;
            for (tick, frame) in &self.prediction {
                if presentation.terminal
                    || *tick != presentation.tick
                    || presentation.step(frame).is_err()
                {
                    break;
                }
                kept += 1;
            }
            self.prediction.truncate(kept);
        }
        self.predicted = presentation;
    }

    /// Open and execute atomically: on any error nothing changes.
    pub fn reveal(&mut self, reveals: Vec<Reveal>) -> Result<(), Error> {
        let mut next = self.clone();
        next.open(reveals)?;
        next.advance()?;
        *self = next;
        Ok(())
    }

    /// Attach a consensus deadline and execute atomically.
    pub fn resolve_deadline(&mut self, resolution: &DeadlineResolution) -> Result<(), Error> {
        let mut next = self.clone();
        next.attach_deadline(resolution)?;
        next.advance()?;
        *self = next;
        Ok(())
    }

    pub fn checkpoint(&self) -> Checkpoint {
        Checkpoint {
            epoch: self.evidence.epoch,
            tick: self.confirmed.tick,
            history_root: self.evidence.root,
            state_hash: self.confirmed.state_hash(),
        }
    }

    /// Retain a checkpoint for a recent boundary this peer confirmed itself,
    /// strictly after the checkpoint already retained.
    pub fn retain_checkpoint(
        &mut self,
        checkpoint: Checkpoint,
        signatures: Vec<SlotSignature>,
    ) -> Result<(), Error> {
        if !self.boundaries.contains(&checkpoint)
            || self
                .last_checkpoint
                .as_ref()
                .is_some_and(|last| checkpoint.tick <= last.checkpoint.tick)
        {
            return Err(Error::InvalidEvidence(
                "checkpoint does not match certified simulation",
            ));
        }
        checkpoint.verify(&self.evidence.context, &signatures)?;
        self.last_checkpoint = Some(CertifiedCheckpoint {
            checkpoint,
            signatures,
        });
        Ok(())
    }

    fn stop_prediction(&mut self) {
        self.prediction.clear();
        self.predicted = self.confirmed.clone();
    }

    /// Stop combat on dropout. Certified frontiers, their openings and the
    /// last certified checkpoint remain; no new prediction runs.
    pub fn interrupt(&mut self) {
        self.evidence.interrupt();
        self.stop_prediction();
    }

    /// Close only resolved local evidence; this cannot submit or release any funds.
    pub fn finish_local(&mut self) -> Result<(), Error> {
        if self.evidence.phase == Phase::Live && !self.confirmed.terminal {
            return Err(Error::InvalidEvidence("live combat has not ended"));
        }
        self.evidence.finish(self.confirmed.terminal)?;
        self.stop_prediction();
        Ok(())
    }

    /// Available once local evidence is terminal.
    pub fn terminal_outcome(&self) -> Option<TerminalOutcome> {
        (self.evidence.phase == Phase::Terminal).then(|| TerminalOutcome {
            epoch: self.evidence.epoch,
            tick: self.confirmed.tick,
            evidence_tick: self.evidence.next_tick,
            history_root: self.evidence.root,
            state_hash: self.confirmed.state_hash(),
            completed: self.confirmed.terminal,
            deadline_frontiers: self
                .evidence
                .batches
                .iter()
                .filter(|batch| batch.deadline.is_some())
                .count() as u32,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{protocol::sign_commitment_set, simulation::Mode};

    fn fixture() -> (RollbackSession, Vec<SigningKey>) {
        fixture_with(600)
    }

    fn fixture_with(max_ticks: u32) -> (RollbackSession, Vec<SigningKey>) {
        let keys = vec![
            SigningKey::from_bytes(&[11; 32]),
            SigningKey::from_bytes(&[12; 32]),
        ];
        let context = Context {
            network: [1; 32],
            session: [2; 32],
            manifest: [3; 32],
            roster: keys.iter().map(|k| k.verifying_key().to_bytes()).collect(),
        };
        let roster = (0..2)
            .map(|team| Participant {
                team,
                class: 0,
                weapon: 1,
                bond: 1000,
                special_entitled: false,
            })
            .collect::<Vec<_>>();
        let session = RollbackSession::new(
            context,
            Config {
                mode: Mode::FreeForAll,
                map: 0,
                max_ticks,
                base_bond: 1000,
                offline: false,
            },
            &roster,
        )
        .unwrap();
        (session, keys)
    }

    fn certify(
        session: &mut RollbackSession,
        keys: &[SigningKey],
        frames: Vec<Vec<Input>>,
    ) -> Vec<Reveal> {
        let log = session.evidence();
        let start_tick = log.certified_tick;
        let reveals = (0..keys.len())
            .map(|slot| Reveal {
                start_tick,
                slot,
                salt: [slot as u8 + 30 + start_tick as u8; 32],
                inputs: frames.iter().map(|frame| frame[slot]).collect(),
            })
            .collect::<Vec<_>>();
        let set = CommitmentSet {
            epoch: log.epoch,
            start_tick,
            parent: log.commitment_head,
            commitments: reveals
                .iter()
                .map(|r| r.commitment(&log.context, log.epoch).unwrap())
                .collect(),
        };
        let signatures = keys
            .iter()
            .enumerate()
            .map(|(slot, key)| sign_commitment_set(&log.context, &set, slot, key).unwrap())
            .collect();
        session.certify(set, signatures).unwrap();
        reveals
    }

    fn sign(session: &RollbackSession, keys: &[SigningKey], cp: &Checkpoint) -> Vec<SlotSignature> {
        keys.iter()
            .enumerate()
            .map(|(slot, key)| cp.sign(&session.evidence.context, slot, key).unwrap())
            .collect()
    }

    #[test]
    fn differing_reveals_rebase_prediction_without_mutating_confirmed_earnings() {
        let (mut session, keys) = fixture();
        let controls = vec![
            Input {
                move_x: 127,
                ..Input::default()
            };
            2
        ];
        for _ in 0..4 {
            session.predict(controls.clone()).unwrap();
        }
        let predicted_hash = session.predicted().state_hash();
        assert_eq!(session.confirmed().tick, 0);
        assert!(session.confirmed().accounts.iter().all(|a| a.earnings == 0));
        let revealed = vec![vec![Input::default(); 2]; 2];
        let r = certify(&mut session, &keys, revealed.clone());
        let mut reference = session.confirmed().clone();
        for frame in revealed {
            reference.step(&frame).unwrap();
        }
        session.reveal(r).unwrap();
        assert_eq!(session.confirmed().state_hash(), reference.state_hash());
        for _ in 0..2 {
            reference.step(&controls).unwrap();
        }
        assert_eq!(session.predicted().state_hash(), reference.state_hash());
        assert_ne!(session.predicted().state_hash(), predicted_hash);
    }

    #[test]
    fn invalid_reveal_is_atomic_and_disconnect_preserves_frontier() {
        let (mut session, keys) = fixture();
        let r = certify(&mut session, &keys, vec![vec![Input::default(); 2]; 2]);
        let before = session.confirmed().state_hash();
        let root = session.evidence().root;
        let mut forged = r.clone();
        forged[1].inputs[0].buttons = 1;
        assert!(session.reveal(forged).is_err());
        assert_eq!(session.confirmed().state_hash(), before);
        assert_eq!(session.evidence().root, root);
        assert!(
            session.evidence().pending[0]
                .openings
                .iter()
                .all(Option::is_none)
        );
        session.interrupt();
        assert!(session.predict(vec![Input::default(); 2]).is_err());
        assert!(session.finish_local().is_err());
        assert_eq!(session.evidence().pending.len(), 1);
        session.reveal(r).unwrap();
        assert_eq!(session.confirmed().tick, 2);
        session.finish_local().unwrap();
        assert_eq!(session.evidence().phase, Phase::Terminal);
        let outcome = session.terminal_outcome().unwrap();
        assert!(!outcome.completed);
        assert_eq!((outcome.tick, outcome.evidence_tick), (2, 2));
        assert_eq!(outcome.state_hash, session.confirmed().state_hash());
    }

    #[test]
    fn checkpoint_requires_a_confirmed_boundary_and_every_exact_signature() {
        let (mut session, keys) = fixture();
        let checkpoint = session.checkpoint();
        let signatures = sign(&session, &keys, &checkpoint);
        let context = session.evidence().context.clone();
        checkpoint
            .verify_signature(&context, &signatures[1])
            .unwrap();
        let mut misattributed = signatures[1].clone();
        misattributed.slot = 0;
        assert!(
            checkpoint
                .verify_signature(&context, &misattributed)
                .is_err()
        );
        assert_eq!(session.boundary(0), Some(&checkpoint));
        assert!(
            session
                .retain_checkpoint(checkpoint.clone(), signatures[..1].to_vec())
                .is_err()
        );
        let mut forged = checkpoint.clone();
        forged.state_hash[0] ^= 1;
        assert!(
            session
                .retain_checkpoint(forged, signatures.clone())
                .is_err()
        );
        session
            .retain_checkpoint(checkpoint.clone(), signatures.clone())
            .unwrap();
        // Two frontiers confirm before the peers' checkpoint for the first
        // arrives: it still matches the boundary this peer passed.
        let first = certify(&mut session, &keys, vec![vec![Input::default(); 2]; 2]);
        let second = certify(&mut session, &keys, vec![vec![Input::default(); 2]; 2]);
        session.reveal(first).unwrap();
        let passed = session.checkpoint();
        session.reveal(second).unwrap();
        assert_ne!(session.checkpoint(), passed);
        assert_eq!(session.boundary(2), Some(&passed));
        assert_eq!(session.boundary(3), None);
        assert!(session.retain_checkpoint(checkpoint, signatures).is_err());
        let passed_signatures = sign(&session, &keys, &passed);
        session
            .retain_checkpoint(passed.clone(), passed_signatures.clone())
            .unwrap();
        assert!(
            session
                .retain_checkpoint(passed, passed_signatures)
                .is_err()
        );
        assert_eq!(session.last_checkpoint().unwrap().checkpoint.tick, 2);
    }

    #[test]
    fn checkpoints_older_than_the_window_are_refused() {
        let (mut session, keys) = fixture();
        let old = session.checkpoint();
        for _ in 0..CHECKPOINT_WINDOW {
            let r = certify(&mut session, &keys, vec![vec![Input::default(); 2]; 2]);
            session.reveal(r).unwrap();
        }
        let signatures = sign(&session, &keys, &old);
        assert!(session.retain_checkpoint(old, signatures).is_err());
    }

    #[test]
    fn bounded_prediction_and_invalid_controls_leave_state_intact() {
        let (mut session, _) = fixture();
        let initial = session.predicted().state_hash();
        assert!(
            session
                .predict(vec![
                    Input {
                        buttons: 128,
                        ..Input::default()
                    };
                    2
                ])
                .is_err()
        );
        assert_eq!(session.predicted().state_hash(), initial);
        for _ in 0..MAX_PREDICTION_TICKS {
            session.predict(vec![Input::default(); 2]).unwrap();
        }
        assert!(session.predict(vec![Input::default(); 2]).is_err());
        assert_eq!(session.confirmed().tick, 0);
        assert_eq!(session.predicted().tick, MAX_PREDICTION_TICKS as u32);
        assert!(session.finish_local().is_err());
        session.interrupt();
        assert_eq!(session.predicted().state_hash(), initial);
    }

    #[test]
    fn terminal_inside_certified_batch_retains_unused_controls_without_executing_them() {
        let (mut session, keys) = fixture_with(1);
        let first = vec![Input::default(); 2];
        let second = vec![
            Input {
                buttons: crate::simulation::FIRE,
                move_x: 127,
                ..Input::default()
            };
            2
        ];
        let mut reference = session.confirmed().clone();
        reference.step(&first).unwrap();
        let reveals = certify(&mut session, &keys, vec![first, second]);
        session.reveal(reveals).unwrap();
        assert!(session.confirmed().terminal);
        assert_eq!(session.confirmed().tick, 1);
        assert_eq!(session.evidence().next_tick, 2);
        assert_eq!(session.confirmed().state_hash(), reference.state_hash());
        assert!(session.evidence().pending.is_empty());
        session.finish_local().unwrap();
        assert!(session.terminal_outcome().unwrap().completed);
    }

    #[test]
    fn frontiers_after_the_match_clock_are_refused_and_the_clock_ends_combat() {
        let (mut session, keys) = fixture_with(4);
        let idle = vec![vec![Input::default(); 2]; 2];
        let reveals = (0..2)
            .map(|_| certify(&mut session, &keys, idle.clone()))
            .collect::<Vec<_>>();
        // The clock ends at tick 4: nothing may be certified at or after it.
        let log = session.evidence();
        let late = CommitmentSet {
            epoch: 0,
            start_tick: 4,
            parent: log.commitment_head,
            commitments: vec![[0; 32]; 2],
        };
        assert!(session.certify(late, Vec::new()).is_err());
        session.reveal(reveals[0].clone()).unwrap();
        session.reveal(reveals[1][..1].to_vec()).unwrap();
        assert_eq!(session.confirmed().tick, 2);
        assert!(session.finish_local().is_err());
        session.reveal(reveals[1][1..].to_vec()).unwrap();
        assert!(session.confirmed().terminal);
        session.finish_local().unwrap();
        assert_eq!(session.terminal_outcome().unwrap().evidence_tick, 4);
    }

    #[test]
    fn pipelined_openings_execute_in_tick_order_and_match_sequential_replay() {
        let (mut sequential, keys) = fixture();
        let mut pipelined = sequential.clone();
        let frames = (0..8u32)
            .map(|batch| {
                (0..2)
                    .map(|offset| {
                        (0..2u32)
                            .map(|slot| Input {
                                buttons: u32::from((batch + offset + slot) % 3 == 0),
                                move_x: 127 - 30 * slot as i16,
                                yaw: (batch * 4096 + slot * 16384) as u16,
                                ..Input::default()
                            })
                            .collect::<Vec<_>>()
                    })
                    .collect::<Vec<_>>()
            })
            .collect::<Vec<_>>();
        for batch in &frames {
            let reveals = certify(&mut sequential, &keys, batch.clone());
            sequential.reveal(reveals).unwrap();
        }
        let reveals = frames
            .iter()
            .map(|batch| certify(&mut pipelined, &keys, batch.clone()))
            .collect::<Vec<_>>();
        assert_eq!(pipelined.evidence().pending.len(), 8);
        for tick in 0..16 {
            let frame = frames[tick / 2][tick % 2].clone();
            pipelined.predict(frame).unwrap();
        }
        // Slot 1's openings arrive newest first, slot 0's oldest first.
        for batch in reveals.iter().rev() {
            pipelined.open(vec![batch[1].clone()]).unwrap();
        }
        pipelined.advance().unwrap();
        assert_eq!(pipelined.confirmed().tick, 0);
        for (index, batch) in reveals.iter().enumerate() {
            pipelined.reveal(vec![batch[0].clone()]).unwrap();
            assert_eq!(pipelined.confirmed().tick, 2 * (index as u32 + 1));
            // Exact predictions survive every rebase.
            assert_eq!(pipelined.predicted().tick, 16);
        }
        assert_eq!(pipelined.evidence().root, sequential.evidence().root);
        assert_eq!(
            pipelined.confirmed().state_hash(),
            sequential.confirmed().state_hash()
        );
        assert_eq!(
            pipelined.predicted().state_hash(),
            sequential.confirmed().state_hash()
        );
    }

    #[test]
    fn deadline_forfeits_a_withheld_opening_and_stops_combat() {
        let (mut session, keys) = fixture();
        let fire = vec![
            Input {
                buttons: crate::simulation::FIRE,
                ..Input::default()
            };
            2
        ];
        let first = certify(&mut session, &keys, vec![fire.clone(), fire.clone()]);
        let second = certify(&mut session, &keys, vec![fire.clone(), fire]);
        session.predict(vec![Input::default(); 2]).unwrap();
        session.reveal(first[..1].to_vec()).unwrap();
        let resolution = DeadlineResolution {
            start_tick: 0,
            frontier: session.evidence().pending[0].digest,
            attestation: [9; 32],
            openings: vec![Some(first[0].clone()), None],
        };
        let mut reference = session.confirmed().clone();
        let forfeited = [first[0].inputs[0], Input::default()];
        reference.step(&forfeited).unwrap();
        reference
            .step(&[first[0].inputs[1], Input::default()])
            .unwrap();
        session.resolve_deadline(&resolution).unwrap();
        assert_eq!(session.evidence().phase, Phase::Resolving);
        assert_eq!(session.confirmed().state_hash(), reference.state_hash());
        assert_eq!(session.predicted().state_hash(), reference.state_hash());
        assert!(session.predict(vec![Input::default(); 2]).is_err());
        // The second frontier was certified before the dropout; its complete
        // openings still execute.
        assert!(session.finish_local().is_err());
        session.reveal(second).unwrap();
        assert_eq!(session.confirmed().tick, 4);
        session.finish_local().unwrap();
        let outcome = session.terminal_outcome().unwrap();
        assert_eq!(outcome.deadline_frontiers, 1);
        assert!(!outcome.completed);
        assert_eq!(outcome.evidence_tick, 4);
    }
}
