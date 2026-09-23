//! Bounded local prediction over one certified input timeline.
//!
//! Predicted events never enter the certified world. A checkpoint is evidence
//! signed by gameplay keys, not a ledger authorization or an execution proof.
//! Native consensus deadlines and forced reveals are a separate integration gate.
use std::collections::VecDeque;

use ed25519_dalek::{Signature, Signer, SigningKey, VerifyingKey};
use sha2::{Digest, Sha256};

use crate::{
    Error,
    protocol::{CommitmentSet, Context, EvidenceLog, Hash, Phase, Reveal, SlotSignature},
    simulation::{Config, Input, Participant, World},
};

pub const MAX_PREDICTION_TICKS: usize = 120;

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
            VerifyingKey::from_bytes(&context.roster[slot])
                .map_err(|_| Error::InvalidEvidence("invalid checkpoint key"))?
                .verify_strict(&digest, &Signature::from_bytes(&signature.signature))
                .map_err(|_| Error::InvalidEvidence("invalid checkpoint signature"))?;
        }
        Ok(())
    }
}

#[derive(Debug, Clone)]
pub struct CertifiedCheckpoint {
    pub checkpoint: Checkpoint,
    pub signatures: Vec<SlotSignature>,
}

#[derive(Debug, Clone)]
pub struct RollbackSession {
    evidence: EvidenceLog,
    confirmed: World,
    predicted: World,
    prediction: VecDeque<(u32, Vec<Input>)>,
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
        Ok(Self {
            predicted: confirmed.clone(),
            confirmed,
            evidence,
            prediction: VecDeque::new(),
            last_checkpoint: None,
        })
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

    pub fn certify(
        &mut self,
        set: CommitmentSet,
        signatures: Vec<SlotSignature>,
    ) -> Result<(), Error> {
        if self.confirmed.terminal {
            return Err(Error::Terminal);
        }
        self.evidence.certify(set, signatures)
    }

    /// Validate and commit a complete batch atomically, then replay remaining predictions.
    /// Invalid or stale data cannot modify either the evidence frontier or combat state.
    pub fn reveal(&mut self, reveals: Vec<Reveal>) -> Result<(), Error> {
        let mut next_evidence = self.evidence.clone();
        let inputs = next_evidence.reveal(reveals)?;
        let mut next_world = self.confirmed.clone();
        for frame in inputs {
            // A previously certified batch may extend beyond an objective or
            // clock ending the match. Retain every committed/revealed byte,
            // but execute no controls after the first terminal transition.
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
        let mut remaining = self.prediction.clone();
        while remaining
            .front()
            .is_some_and(|(tick, _)| *tick < next_world.tick)
        {
            remaining.pop_front();
        }
        let mut presentation = next_world.clone();
        if next_evidence.phase != Phase::Live || presentation.terminal {
            remaining.clear();
        } else {
            let mut kept = 0;
            for (tick, frame) in &remaining {
                if presentation.terminal {
                    break;
                }
                if *tick != presentation.tick {
                    return Err(Error::InvalidEvidence("prediction gap"));
                }
                presentation.step(frame)?;
                kept += 1;
            }
            remaining.truncate(kept);
        }
        self.evidence = next_evidence;
        self.confirmed = next_world;
        self.predicted = presentation;
        self.prediction = remaining;
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

    pub fn retain_checkpoint(
        &mut self,
        checkpoint: Checkpoint,
        signatures: Vec<SlotSignature>,
    ) -> Result<(), Error> {
        if checkpoint != self.checkpoint() {
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

    /// Freeze immediately on dropout. Already certified pending inputs remain available.
    pub fn interrupt(&mut self) {
        self.evidence.interrupt();
        self.prediction.clear();
        self.predicted = self.confirmed.clone();
    }

    /// Close only resolved local evidence; this cannot submit or release any funds.
    pub fn finish_local(&mut self) -> Result<(), Error> {
        if self.evidence.phase == Phase::Live && !self.confirmed.terminal {
            return Err(Error::InvalidEvidence("live combat has not ended"));
        }
        self.evidence.finish()?;
        self.prediction.clear();
        self.predicted = self.confirmed.clone();
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        protocol::{input_commitment, sign_commitment_set},
        simulation::Mode,
    };

    fn fixture() -> (RollbackSession, Vec<SigningKey>) {
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
                max_ticks: 600,
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
        let reveals = (0..keys.len())
            .map(|slot| Reveal {
                slot,
                salt: [slot as u8 + 30; 32],
                inputs: frames.iter().map(|frame| frame[slot]).collect(),
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
                        &log.context,
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
        let signatures = keys
            .iter()
            .enumerate()
            .map(|(slot, key)| sign_commitment_set(&log.context, &set, slot, key).unwrap())
            .collect();
        session.certify(set, signatures).unwrap();
        reveals
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
        forged[0].inputs[0].buttons = 1;
        assert!(session.reveal(forged).is_err());
        assert_eq!(session.confirmed().state_hash(), before);
        assert_eq!(session.evidence().root, root);
        session.interrupt();
        assert!(session.predict(vec![Input::default(); 2]).is_err());
        assert!(session.finish_local().is_err());
        assert!(session.evidence().pending.is_some());
        session.reveal(r).unwrap();
        assert_eq!(session.confirmed().tick, 2);
        session.finish_local().unwrap();
        assert_eq!(session.evidence().phase, Phase::Terminal);
    }

    #[test]
    fn checkpoint_requires_current_state_and_every_exact_signature() {
        let (mut session, keys) = fixture();
        let checkpoint = session.checkpoint();
        let signatures = keys
            .iter()
            .enumerate()
            .map(|(slot, key)| {
                checkpoint
                    .sign(&session.evidence.context, slot, key)
                    .unwrap()
            })
            .collect::<Vec<_>>();
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
        let r = certify(&mut session, &keys, vec![vec![Input::default(); 2]; 2]);
        session.reveal(r).unwrap();
        assert!(session.retain_checkpoint(checkpoint, signatures).is_err());
        assert_eq!(session.last_checkpoint().unwrap().checkpoint.tick, 0);
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
        let (session, keys) = fixture();
        let context = session.evidence.context.clone();
        let roster = (0..2)
            .map(|team| Participant {
                team,
                class: 0,
                weapon: 1,
                bond: 1000,
                special_entitled: false,
            })
            .collect::<Vec<_>>();
        let mut session = RollbackSession::new(
            context,
            Config {
                mode: Mode::FreeForAll,
                map: 0,
                max_ticks: 1,
                base_bond: 1000,
                offline: false,
            },
            &roster,
        )
        .unwrap();
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
        assert!(session.evidence().pending.is_none());
        session.finish_local().unwrap();
    }
}
