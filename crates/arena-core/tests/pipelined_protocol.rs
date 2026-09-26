//! Pipelined commitment frontiers and the peer-dropout policy
//! (docs/p2p-pipeline.md). Fixture keys, in-process message queues and
//! temporary journals only: no wallet, reserve movement, proof or ledger.
use std::{
    collections::VecDeque,
    fs,
    path::PathBuf,
    sync::atomic::{AtomicU64, Ordering},
};

use arena_core::{
    protocol::{
        BATCH_TICKS, CommitmentSet, Context, DeadlineResolution, FrontierAssembler, Hash,
        MAX_ASSEMBLY_FRONTIERS, MAX_OUTSTANDING_FRONTIERS, Phase, Reveal, SlotSignature,
        commitment_due, scheduled_tick, sign_commitment_set,
    },
    recovery::{DurableSession, Receipt},
    rollback::{MAX_PREDICTION_TICKS, RollbackSession, TerminalOutcome},
    simulation::{Config, FIRE, Input, Mode, Participant, World},
};
use ed25519_dalek::SigningKey;

const BATCH: u32 = BATCH_TICKS as u32;

fn keys(count: usize, seed: u8) -> Vec<SigningKey> {
    (0..count)
        .map(|slot| SigningKey::from_bytes(&[seed + slot as u8; 32]))
        .collect()
}

fn context(keys: &[SigningKey]) -> Context {
    Context {
        network: [0x51; 32],
        session: [0x52; 32],
        manifest: [0x53; 32],
        roster: keys.iter().map(|k| k.verifying_key().to_bytes()).collect(),
    }
}

type Script = fn(u32, usize) -> Input;

/// Turning, strafing and bursts of fire. The lead-in ticks that no sampled
/// control reaches are idle.
fn skirmish(tick: u32, slot: usize) -> Input {
    if tick < scheduled_tick(0) {
        return Input::default();
    }
    let phase = tick / 20 + slot as u32 * 3;
    Input {
        buttons: if phase.is_multiple_of(4) { FIRE } else { 0 },
        move_x: [127, 0, -127, 60][(phase % 4) as usize],
        move_y: if slot.is_multiple_of(2) { 90 } else { -90 },
        yaw: (tick.wrapping_mul(311) + slot as u32 * 16_384) as u16,
        pitch: 0,
    }
}

/// Nyaagyu Estate, Control: a Samurai strafes onto the mid lane and fires
/// along it from tick 62; the Shinobi opposite dies on tick 110.
fn duel(tick: u32, slot: usize) -> Input {
    let strafe = |ticks: u32| if tick < ticks { 127 } else { 0 };
    if slot == 0 {
        Input {
            buttons: if (62..160).contains(&tick) { FIRE } else { 0 },
            move_y: strafe(62),
            ..Input::default()
        }
    } else {
        Input {
            move_y: strafe(50),
            yaw: 32768,
            ..Input::default()
        }
    }
}
const DEATH_TICK: u32 = 110;

fn opening(script: Script, slot: usize, start_tick: u32) -> Reveal {
    let mut salt = [slot as u8 ^ 0x5a; 32];
    salt[..4].copy_from_slice(&start_tick.to_le_bytes());
    Reveal {
        start_tick,
        slot,
        inputs: (start_tick..start_tick + BATCH)
            .map(|tick| script(tick, slot))
            .collect(),
        salt,
    }
}

fn team_roster(players: usize, bond: u64) -> Vec<Participant> {
    (0..players)
        .map(|slot| Participant {
            team: (slot % 2) as u8,
            class: 0,
            weapon: 1,
            bond,
            special_entitled: false,
        })
        .collect()
}

fn reference(config: &Config, roster: &[Participant], script: Script, ticks: u32) -> World {
    let mut world = World::new(config.clone(), roster).unwrap();
    for tick in 0..ticks {
        let inputs = (0..roster.len())
            .map(|slot| script(tick, slot))
            .collect::<Vec<_>>();
        world.step(&inputs).unwrap();
    }
    world
}

// ---------------------------------------------------------------------------
// Latency simulation: every peer presents one tick per 60 Hz wall tick,
// commits each batch once its last control is sampled, and exchanges
// commitments, endorsements and openings with a fixed one-way delay.
// ---------------------------------------------------------------------------

enum Message {
    Commitment {
        slot: usize,
        start_tick: u32,
        commitment: Hash,
    },
    Endorsement {
        set: CommitmentSet,
        signature: SlotSignature,
    },
    Opening(Reveal),
}

struct SimPeer {
    key: SigningKey,
    session: RollbackSession,
    assembler: FrontierAssembler,
    /// Openings that arrived before this peer certified their frontier.
    early: Vec<Reveal>,
    committed_to: u32,
    presented: u32,
    stalls: u32,
    deepest_prediction: u32,
    deepest_pipeline: usize,
}

struct Mesh {
    peers: Vec<SimPeer>,
    in_flight: VecDeque<(u32, usize, Message)>,
    delay: u32,
    now: u32,
}

impl Mesh {
    fn new(players: usize, delay: u32, config: &Config) -> Self {
        let keys = keys(players, 40);
        let context = context(&keys);
        let roster = team_roster(players, 0);
        let peers = keys
            .into_iter()
            .map(|key| {
                let session =
                    RollbackSession::new(context.clone(), config.clone(), &roster).unwrap();
                SimPeer {
                    key,
                    assembler: FrontierAssembler::following(session.evidence()),
                    session,
                    early: Vec::new(),
                    committed_to: 0,
                    presented: 0,
                    stalls: 0,
                    deepest_prediction: 0,
                    deepest_pipeline: 0,
                }
            })
            .collect();
        let mut mesh = Self {
            peers,
            in_flight: VecDeque::new(),
            delay,
            now: 0,
        };
        // Lead-in batches carry no sampled control; commit them at admission.
        for slot in 0..players {
            let mut start = 0;
            while commitment_due(start).is_none() {
                mesh.commit(slot, start);
                start += BATCH;
            }
        }
        mesh
    }

    fn broadcast(&mut self, from: usize, message: impl Fn() -> Message) {
        for to in 0..self.peers.len() {
            if to != from {
                self.in_flight
                    .push_back((self.now + self.delay, to, message()));
            }
        }
    }

    fn commit(&mut self, slot: usize, start_tick: u32) {
        let peer = &mut self.peers[slot];
        let evidence = peer.session.evidence();
        let commitment = opening(skirmish, slot, start_tick)
            .commitment(&evidence.context, evidence.epoch)
            .unwrap();
        assert!(
            peer.assembler
                .add_commitment(slot, 0, start_tick, commitment)
                .unwrap()
        );
        peer.committed_to = start_tick + BATCH;
        self.broadcast(slot, || Message::Commitment {
            slot,
            start_tick,
            commitment,
        });
    }

    fn deliver(&mut self, to: usize, message: Message) {
        let peer = &mut self.peers[to];
        match message {
            Message::Commitment {
                slot,
                start_tick,
                commitment,
            } => {
                peer.assembler
                    .add_commitment(slot, 0, start_tick, commitment)
                    .unwrap();
            }
            Message::Endorsement { set, signature } => {
                peer.assembler.add_endorsement(&set, signature).unwrap();
            }
            Message::Opening(reveal) => {
                if peer.session.open(vec![reveal.clone()]).is_err() {
                    assert!(
                        peer.session
                            .evidence()
                            .frontier(reveal.start_tick)
                            .is_none()
                    );
                    peer.early.push(reveal);
                }
                peer.session.advance().unwrap();
            }
        }
    }

    /// `serial` emulates a protocol with one frontier in flight: a batch is
    /// committed only once every earlier frontier has closed.
    fn tick(&mut self, present: bool, serial: bool) {
        while self
            .in_flight
            .front()
            .is_some_and(|(due, _, _)| *due <= self.now)
        {
            let (_, to, message) = self.in_flight.pop_front().unwrap();
            self.deliver(to, message);
        }
        for slot in 0..self.peers.len() {
            if present {
                self.present(slot, serial);
            }
            self.endorse(slot);
            self.certify(slot);
            let peer = &mut self.peers[slot];
            let (predicted, confirmed) =
                (peer.session.predicted().tick, peer.session.confirmed().tick);
            peer.deepest_prediction = peer.deepest_prediction.max(predicted - confirmed);
        }
        self.now += 1;
    }

    /// Present tick `presented`. The presentation clock is wall-driven: when
    /// confirmation has already passed it, nothing needs predicting.
    fn present(&mut self, slot: usize, serial: bool) {
        let peer = &self.peers[slot];
        let tick = peer.presented;
        if tick.saturating_sub(peer.session.confirmed().tick) as usize >= MAX_PREDICTION_TICKS {
            self.peers[slot].stalls += 1;
            return;
        }
        // The control sampled now executes INPUT_DELAY_TICKS later; its batch
        // is committed as soon as that control completes it.
        let target = scheduled_tick(tick);
        if target % BATCH == BATCH - 1 && target + 1 > peer.committed_to {
            let start = target + 1 - BATCH;
            let open = if serial {
                peer.session.evidence().next_tick >= start
            } else {
                start < peer.assembler.next_tick() + (MAX_ASSEMBLY_FRONTIERS * BATCH_TICKS) as u32
            };
            if !open {
                self.peers[slot].stalls += 1;
                return;
            }
            self.commit(slot, start);
        }
        // Remote controls are predicted by repeating each slot's last
        // confirmed control; the local control is known exactly.
        let peer = &mut self.peers[slot];
        peer.presented += 1;
        if peer.session.predicted().tick > tick {
            return;
        }
        let evidence = peer.session.evidence();
        let last = evidence
            .batches
            .len()
            .checked_sub(1)
            .and_then(|index| evidence.batches.get(index));
        let controls = (0..evidence.context.roster.len())
            .map(|other| {
                if other == slot {
                    skirmish(tick, slot)
                } else {
                    last.and_then(|batch| batch.openings[other].as_ref())
                        .map_or(Input::default(), |r| r.inputs[BATCH_TICKS - 1])
                }
            })
            .collect();
        peer.session.predict(controls).unwrap();
    }

    fn endorse(&mut self, slot: usize) {
        let peer = &mut self.peers[slot];
        let mut outgoing = Vec::new();
        for set in peer.assembler.unendorsed(slot) {
            let context = &peer.session.evidence().context;
            let signature = sign_commitment_set(context, &set, slot, &peer.key).unwrap();
            peer.assembler
                .add_endorsement(&set, signature.clone())
                .unwrap();
            outgoing.push((set, signature));
        }
        for (set, signature) in outgoing {
            self.broadcast(slot, || Message::Endorsement {
                set: set.clone(),
                signature: signature.clone(),
            });
        }
    }

    fn certify(&mut self, slot: usize) {
        let mut outgoing = Vec::new();
        let peer = &mut self.peers[slot];
        while peer.session.evidence().pending.len() < MAX_OUTSTANDING_FRONTIERS {
            let Some((set, signatures)) = peer.assembler.take_certified() else {
                break;
            };
            let start_tick = set.start_tick;
            peer.session.certify(set, signatures).unwrap();
            // A peer opens its own commitment as soon as it is certified.
            let own = opening(skirmish, slot, start_tick);
            peer.session.open(vec![own.clone()]).unwrap();
            outgoing.push(own);
        }
        peer.deepest_pipeline = peer
            .deepest_pipeline
            .max(peer.session.evidence().pending.len());
        let early = std::mem::take(&mut peer.early);
        for reveal in early {
            if peer.session.open(vec![reveal.clone()]).is_err() {
                peer.early.push(reveal);
            }
        }
        peer.session.advance().unwrap();
        for own in outgoing {
            self.broadcast(slot, || Message::Opening(own.clone()));
        }
    }
}

fn sim_config() -> Config {
    Config {
        mode: Mode::Control,
        map: 0,
        max_ticks: 7_200,
        base_bond: 0,
        offline: true,
    }
}

/// Run `wall` presentation ticks, then let every committed batch close.
fn run_mesh(players: usize, delay: u32, wall: u32, serial: bool) -> Mesh {
    let mut mesh = Mesh::new(players, delay, &sim_config());
    for _ in 0..wall {
        mesh.tick(true, serial);
    }
    for _ in 0..4 * delay + 4 {
        mesh.tick(false, serial);
    }
    mesh
}

#[test]
fn sixty_hertz_presentation_survives_internet_round_trips_with_pipelined_frontiers() {
    const PLAYERS: usize = 3;
    const WALL: u32 = 240;
    let config = sim_config();
    let roster = team_roster(PLAYERS, 0);
    // One-way delays of 50, 150 and 400 ms (100, 300 and 800 ms round trips).
    for delay in [3, 9, 24] {
        let mesh = run_mesh(PLAYERS, delay, WALL, false);
        let first = &mesh.peers[0].session;
        let closed = first.evidence().next_tick;
        assert_eq!(closed, WALL + scheduled_tick(0));
        let expected = reference(&config, &roster, skirmish, closed);
        for peer in &mesh.peers {
            assert_eq!(peer.stalls, 0, "delay {delay}");
            assert_eq!(peer.presented, WALL);
            assert_eq!(peer.session.evidence().root, first.evidence().root);
            assert_eq!(peer.session.confirmed().state_hash(), expected.state_hash());
            assert!(peer.session.evidence().pending.is_empty());
            // Confirmation trails presentation by about three one-way delays
            // less the input delay; several frontiers are in flight at once.
            assert!(
                peer.deepest_prediction <= 3 * delay + 2 * BATCH,
                "delay {delay}"
            );
            assert!(peer.deepest_pipeline > 1);
            assert!(peer.deepest_pipeline <= MAX_OUTSTANDING_FRONTIERS);
        }
        // Pipelining changes neither the transcript nor the combat state:
        // one frontier at a time over the same openings gives the same root.
        let mut sequential =
            RollbackSession::new(first.evidence().context.clone(), config.clone(), &roster)
                .unwrap();
        let keys = keys(PLAYERS, 40);
        for start in (0..closed).step_by(BATCH_TICKS) {
            let log = sequential.evidence();
            let openings = (0..PLAYERS)
                .map(|slot| opening(skirmish, slot, start))
                .collect::<Vec<_>>();
            let set = CommitmentSet {
                epoch: 0,
                start_tick: start,
                parent: log.commitment_head,
                commitments: openings
                    .iter()
                    .map(|r| r.commitment(&log.context, 0).unwrap())
                    .collect(),
            };
            let signatures = keys
                .iter()
                .enumerate()
                .map(|(slot, key)| sign_commitment_set(&log.context, &set, slot, key).unwrap())
                .collect();
            sequential.certify(set, signatures).unwrap();
            sequential.reveal(openings).unwrap();
        }
        assert_eq!(sequential.evidence().root, first.evidence().root);
        assert_eq!(sequential.checkpoint(), first.checkpoint());
        eprintln!(
            "pipelined one_way_ticks={delay} presented={WALL} stalls=0 closed_ticks={closed} deepest_prediction={:?} deepest_certified_pipeline={:?}",
            mesh.peers
                .iter()
                .map(|p| p.deepest_prediction)
                .collect::<Vec<_>>(),
            mesh.peers
                .iter()
                .map(|p| p.deepest_pipeline)
                .collect::<Vec<_>>(),
        );
    }
    // Past the certified pipeline (533 ms one way) presentation stalls for
    // backpressure; the peers still never diverge.
    let congested = run_mesh(PLAYERS, 32, WALL, false);
    let first = &congested.peers[0].session;
    let closed = first.evidence().next_tick;
    assert!(closed < WALL + scheduled_tick(0));
    let expected = reference(&config, &roster, skirmish, closed);
    for peer in &congested.peers {
        assert!(peer.stalls > 0);
        assert_eq!(peer.deepest_pipeline, MAX_OUTSTANDING_FRONTIERS);
        assert_eq!(peer.session.evidence().root, first.evidence().root);
        assert_eq!(peer.session.confirmed().state_hash(), expected.state_hash());
    }
    eprintln!(
        "congested one_way_ticks=32 wall={WALL} presented={:?} stalls={:?} closed_ticks={closed}",
        congested
            .peers
            .iter()
            .map(|p| p.presented)
            .collect::<Vec<_>>(),
        congested.peers.iter().map(|p| p.stalls).collect::<Vec<_>>(),
    );
    // One frontier in flight at a 300 ms round trip cannot keep up with 60 Hz.
    let serial = run_mesh(PLAYERS, 9, WALL, true);
    for peer in &serial.peers {
        assert!(peer.presented < WALL / 4, "{}", peer.presented);
        assert!(peer.stalls > WALL / 2);
    }
    eprintln!(
        "serial one_way_ticks=9 wall={WALL} presented={:?} stalls={:?}",
        serial.peers.iter().map(|p| p.presented).collect::<Vec<_>>(),
        serial.peers.iter().map(|p| p.stalls).collect::<Vec<_>>(),
    );
}

// ---------------------------------------------------------------------------
// Durable peers and the dropout policy.
// ---------------------------------------------------------------------------

static NEXT_ROOT: AtomicU64 = AtomicU64::new(0);

struct Node {
    journal: DurableSession,
    assembler: FrontierAssembler,
    /// Retained outside the journal, as a trusted anchor for restore.
    receipt: Receipt,
}

struct Journals {
    root: PathBuf,
    context: Context,
    config: Config,
    roster: Vec<Participant>,
    keys: Vec<SigningKey>,
    script: Script,
    nodes: Vec<Option<Node>>,
    sent_commitments: Vec<(usize, u32, Hash)>,
    sent_endorsements: Vec<(CommitmentSet, SlotSignature)>,
}

impl Journals {
    fn new(config: Config, roster: Vec<Participant>, script: Script) -> Self {
        let root = std::env::temp_dir().join(format!(
            "sora-arena-pipelined-{}-{}",
            std::process::id(),
            NEXT_ROOT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        let keys = keys(roster.len(), 80);
        let context = context(&keys);
        let nodes = (0..roster.len())
            .map(|slot| {
                let journal = DurableSession::create(
                    &root.join(format!("peer-{slot}.journal")),
                    context.clone(),
                    config.clone(),
                    &roster,
                )
                .unwrap();
                Some(Node {
                    assembler: FrontierAssembler::following(journal.session().evidence()),
                    receipt: journal.receipt(),
                    journal,
                })
            })
            .collect();
        Self {
            root,
            context,
            config,
            roster,
            keys,
            script,
            nodes,
            sent_commitments: Vec::new(),
            sent_endorsements: Vec::new(),
        }
    }

    fn node(&mut self, slot: usize) -> &mut Node {
        self.nodes[slot].as_mut().expect("live peer")
    }

    fn live(&mut self) -> impl Iterator<Item = &mut Node> {
        self.nodes.iter_mut().flatten()
    }

    fn opening(&self, slot: usize, batch: u32) -> Reveal {
        opening(self.script, slot, batch * BATCH)
    }

    fn commit(&mut self, slot: usize, batch: u32) {
        let own = self.opening(slot, batch);
        let node = self.node(slot);
        let (commitment, receipt) = node.journal.seal(own).unwrap();
        node.receipt = receipt;
        self.sent_commitments
            .push((slot, batch * BATCH, commitment));
        for node in self.live() {
            node.assembler
                .add_commitment(slot, 0, batch * BATCH, commitment)
                .unwrap();
        }
    }

    fn endorse(&mut self, slot: usize) {
        let key = self.keys[slot].clone();
        let node = self.node(slot);
        let mut signed = Vec::new();
        for set in node.assembler.unendorsed(slot) {
            let (signature, receipt) = node.journal.endorse(&set, slot, &key).unwrap();
            node.receipt = receipt;
            signed.push((set, signature));
        }
        for (set, signature) in signed {
            self.sent_endorsements
                .push((set.clone(), signature.clone()));
            for node in self.live() {
                node.assembler
                    .add_endorsement(&set, signature.clone())
                    .unwrap();
            }
        }
    }

    fn certify(&mut self) {
        for node in self.live() {
            while let Some((set, signatures)) = node.assembler.take_certified() {
                node.receipt = node.journal.certify(set, signatures).unwrap();
            }
        }
    }

    fn reveal(&mut self, slot: usize, batch: u32, to: &[usize]) {
        let own = self.opening(slot, batch);
        for &peer in to {
            let node = self.node(peer);
            node.receipt = node.journal.reveal(own.clone()).unwrap();
        }
    }

    fn live_slots(&self) -> Vec<usize> {
        (0..self.nodes.len())
            .filter(|slot| self.nodes[*slot].is_some())
            .collect()
    }

    /// Every live peer commits, endorses, certifies and opens the batch.
    fn full_batch(&mut self, batch: u32) {
        let live = self.live_slots();
        for &slot in &live {
            self.commit(slot, batch);
        }
        for &slot in &live {
            self.endorse(slot);
        }
        self.certify();
        for &slot in &live {
            self.reveal(slot, batch, &live);
        }
    }

    fn checkpoint(&mut self) {
        let checkpoint = self.node(0).journal.session().checkpoint();
        let signatures = self
            .keys
            .iter()
            .enumerate()
            .map(|(slot, key)| checkpoint.sign(&self.context, slot, key).unwrap())
            .collect::<Vec<_>>();
        for node in self.live() {
            node.receipt = node
                .journal
                .checkpoint(checkpoint.clone(), signatures.clone())
                .unwrap();
        }
    }

    fn drop_peer(&mut self, slot: usize) {
        self.nodes[slot] = None;
    }

    /// What native consensus retained for one frontier: every opening any
    /// live peer published, and a forfeit for the rest.
    fn deadline(&mut self, batch: u32, attestation: u8) -> DeadlineResolution {
        let start_tick = batch * BATCH;
        let mut openings = vec![None; self.roster.len()];
        let mut frontier = None;
        for node in self.live() {
            let pending = node
                .journal
                .session()
                .evidence()
                .frontier(start_tick)
                .unwrap();
            frontier = Some(pending.digest);
            for (slot, opening) in pending.openings.iter().enumerate() {
                if opening.is_some() {
                    openings[slot] = opening.clone();
                }
            }
        }
        DeadlineResolution {
            start_tick,
            frontier: frontier.unwrap(),
            attestation: [attestation; 32],
            openings,
        }
    }

    fn outcomes(&mut self) -> Vec<TerminalOutcome> {
        self.live()
            .map(|node| node.journal.session().terminal_outcome().unwrap())
            .collect()
    }
}

impl Drop for Journals {
    fn drop(&mut self) {
        self.nodes.clear();
        let _ = fs::remove_dir_all(&self.root);
    }
}

fn skirmish_journals() -> Journals {
    Journals::new(
        Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 600,
            base_bond: 1000,
            offline: false,
        },
        (0..3)
            .map(|slot| Participant {
                team: (slot % 2) as u8,
                class: 0,
                weapon: 1,
                bond: 1000,
                special_entitled: false,
            })
            .collect(),
        skirmish,
    )
}

#[test]
fn disconnect_before_or_after_commitment_ends_at_the_last_certified_frontier() {
    let mut outcomes = Vec::new();
    for commits_before_dropping in [false, true] {
        let mut journals = skirmish_journals();
        for batch in 0..4 {
            journals.full_batch(batch);
        }
        journals.commit(0, 4);
        journals.commit(1, 4);
        if commits_before_dropping {
            journals.commit(2, 4);
        }
        journals.drop_peer(2);
        journals.endorse(0);
        journals.endorse(1);
        journals.certify();
        for slot in [0, 1] {
            let node = journals.node(slot);
            let evidence = node.journal.session().evidence();
            // Without the missing commitment or endorsement nothing past the
            // last certified frontier can be certified by anyone.
            assert_eq!(evidence.certified_tick, 8);
            assert!(evidence.pending.is_empty());
            assert!(node.assembler.take_certified().is_none());
            // A local timeout stops combat; nothing new is committed after it.
            node.journal.interrupt().unwrap();
            assert!(node.journal.session().predicted().tick == 8);
            let late = opening(skirmish, slot, 10);
            assert!(node.journal.seal(late).is_err());
            node.journal.finish().unwrap();
        }
        let terminal = journals.outcomes();
        assert_eq!(terminal[0], terminal[1]);
        assert_eq!(terminal[0].evidence_tick, 8);
        assert_eq!(terminal[0].deadline_frontiers, 0);
        assert!(!terminal[0].completed);
        let expected = reference(&journals.config, &journals.roster, skirmish, 8);
        assert_eq!(terminal[0].state_hash, expected.state_hash());
        outcomes.push(terminal[0].clone());
    }
    // Whether or not the dropped peer's commitment was sent, the evidence
    // ends at the same provable state.
    assert_eq!(outcomes[0], outcomes[1]);
}

#[test]
fn disconnect_after_certification_forfeits_withheld_openings_through_consensus_deadlines() {
    let mut journals = skirmish_journals();
    for batch in 0..4 {
        journals.full_batch(batch);
    }
    journals.checkpoint();
    // Two pipelined frontiers are certified with every signature, then peer
    // 2 drops before opening either of them.
    for batch in 4..6 {
        for slot in 0..3 {
            journals.commit(slot, batch);
        }
    }
    for slot in 0..3 {
        journals.endorse(slot);
    }
    journals.certify();
    journals.drop_peer(2);
    for batch in 4..6 {
        for slot in [0, 1] {
            journals.reveal(slot, batch, &[0, 1]);
        }
    }
    let mut resolutions = Vec::new();
    for batch in 4..6 {
        resolutions.push(journals.deadline(batch, 0x70 + batch as u8));
    }
    for slot in [0, 1] {
        let node = journals.node(slot);
        assert_eq!(node.journal.session().evidence().pending.len(), 2);
        assert_eq!(node.journal.session().confirmed().tick, 8);
        // A peer clock can stop combat but can never close a frontier.
        node.journal.interrupt().unwrap();
        assert!(node.journal.finish().is_err());
        assert_eq!(node.journal.session().evidence().phase, Phase::Resolving);
        let checkpoint = node.journal.session().last_checkpoint().unwrap();
        assert_eq!(checkpoint.checkpoint.tick, 8);
        for resolution in &resolutions {
            node.receipt = node.journal.resolve_deadline(resolution.clone()).unwrap();
        }
        assert_eq!(node.journal.session().confirmed().tick, 12);
        // A late opening from the dropped peer is refused.
        let late = opening(skirmish, 2, 8);
        assert!(node.journal.reveal(late).is_err());
        node.receipt = node.journal.finish().unwrap();
        // The certified checkpoint from before the dropout is preserved.
        assert_eq!(
            node.journal
                .session()
                .last_checkpoint()
                .unwrap()
                .checkpoint
                .tick,
            8
        );
    }
    let terminal = journals.outcomes();
    assert_eq!(terminal[0], terminal[1]);
    assert_eq!(terminal[0].deadline_frontiers, 2);
    assert_eq!(terminal[0].evidence_tick, 12);
    // Slot 2 executed the canonical idle control for both batches.
    let forfeited = |tick: u32, slot: usize| {
        if slot == 2 && tick >= 8 {
            Input::default()
        } else {
            skirmish(tick, slot)
        }
    };
    let expected = reference(&journals.config, &journals.roster, forfeited, 12);
    assert_eq!(terminal[0].state_hash, expected.state_hash());
    // Replay from the externally retained receipt proves the same state.
    let receipt = journals.node(1).receipt;
    journals.nodes[1] = None;
    let restored = DurableSession::restore(
        &journals.root.join("peer-1.journal"),
        journals.context.clone(),
        journals.config.clone(),
        &journals.roster,
        receipt,
    )
    .unwrap();
    assert_eq!(restored.session().terminal_outcome().unwrap(), terminal[0]);
}

#[test]
fn an_opening_revealed_to_one_peer_before_dropout_completes_the_frontier_everywhere() {
    let mut journals = skirmish_journals();
    for batch in 0..2 {
        journals.full_batch(batch);
    }
    for slot in 0..3 {
        journals.commit(slot, 2);
    }
    for slot in 0..3 {
        journals.endorse(slot);
    }
    journals.certify();
    // Peer 2 opens only towards peer 0, then drops.
    journals.reveal(2, 2, &[0]);
    journals.drop_peer(2);
    for slot in [0, 1] {
        journals.reveal(slot, 2, &[0, 1]);
    }
    assert_eq!(journals.node(0).journal.session().confirmed().tick, 6);
    assert_eq!(journals.node(1).journal.session().confirmed().tick, 4);
    // Peer 0 publishes every opening it holds. The opening authenticates
    // itself against the certified commitment, so a forged relay fails.
    let published = journals
        .node(0)
        .journal
        .session()
        .evidence()
        .batches
        .get(2)
        .unwrap()
        .openings[2]
        .clone()
        .unwrap();
    let mut forged = published.clone();
    forged.inputs[0].buttons ^= FIRE;
    let node = journals.node(1);
    let before = node.journal.receipt();
    assert!(node.journal.reveal(forged).is_err());
    assert_eq!(node.journal.receipt(), before);
    node.journal.reveal(published).unwrap();
    for slot in [0, 1] {
        let node = journals.node(slot);
        node.journal.interrupt().unwrap();
        node.journal.finish().unwrap();
    }
    let terminal = journals.outcomes();
    assert_eq!(terminal[0], terminal[1]);
    assert_eq!(terminal[0].deadline_frontiers, 0);
    let expected = reference(&journals.config, &journals.roster, skirmish, 6);
    assert_eq!(terminal[0].state_hash, expected.state_hash());
}

#[test]
fn a_withholding_victim_cannot_erase_its_provable_death() {
    let config = Config {
        mode: Mode::Control,
        map: 0,
        max_ticks: 600,
        base_bond: 1000,
        offline: false,
    };
    let roster = [(0, 0, 1), (1, 1, 3)]
        .map(|(team, class, weapon)| Participant {
            team,
            class,
            weapon,
            bond: 1000,
            special_entitled: false,
        })
        .to_vec();
    let mut journals = Journals::new(config.clone(), roster.clone(), duel);
    let death_batch = DEATH_TICK / BATCH;
    for batch in 0..death_batch {
        journals.full_batch(batch);
        if batch == 49 {
            journals.checkpoint();
        }
    }
    // Both players commit and endorse the batch in which the Shinobi dies.
    for slot in 0..2 {
        journals.commit(slot, death_batch);
    }
    for slot in 0..2 {
        journals.endorse(slot);
    }
    journals.certify();
    // The Shinobi sees the Samurai's opening, withholds its own, refuses to
    // sign any further checkpoint and leaves.
    journals.reveal(0, death_batch, &[0, 1]);
    journals.drop_peer(1);
    let resolution = journals.deadline(death_batch, 0x99);
    assert!(resolution.openings[1].is_none());
    let node = journals.node(0);
    node.journal.interrupt().unwrap();
    assert!(node.journal.finish().is_err());
    node.journal.resolve_deadline(resolution).unwrap();
    node.journal.finish().unwrap();
    let session = node.journal.session();
    let outcome = session.terminal_outcome().unwrap();
    assert!(!outcome.completed);
    assert_eq!(outcome.deadline_frontiers, 1);
    assert_eq!(outcome.tick, DEATH_TICK + BATCH);
    // The last certified checkpoint precedes the death; no final signature
    // exists, yet the death and its award are in the provable state.
    assert_eq!(session.last_checkpoint().unwrap().checkpoint.tick, 100);
    let world = session.confirmed();
    assert!(!world.players[1].alive);
    assert_eq!(world.accounts[1].paid_deaths, 1);
    assert_eq!(world.accounts[1].remaining, 900);
    assert_eq!(world.accounts[0].earnings, 100);
    // Withholding gained the victim nothing: the same death and award
    // follow if it had opened its controls.
    let honest = reference(&config, &roster, duel, DEATH_TICK + BATCH);
    assert!(!honest.players[1].alive);
    assert_eq!(
        honest
            .accounts
            .iter()
            .map(|a| (a.remaining, a.earnings, a.paid_deaths))
            .collect::<Vec<_>>(),
        world
            .accounts
            .iter()
            .map(|a| (a.remaining, a.earnings, a.paid_deaths))
            .collect::<Vec<_>>()
    );
}

#[test]
fn restart_in_the_middle_of_the_pipeline_recovers_the_uninterrupted_outcome() {
    let run = |crash: bool| {
        let mut journals = skirmish_journals();
        for batch in 0..3 {
            journals.full_batch(batch);
        }
        // Frontiers 3..6 are certified; 7 is committed by everyone and
        // endorsed by peers 0 and 1 only.
        for batch in 3..8 {
            for slot in 0..3 {
                journals.commit(slot, batch);
            }
        }
        for slot in 0..2 {
            journals.endorse(slot);
        }
        let (set, signature) = {
            let key = journals.keys[2].clone();
            let node = journals.node(2);
            let sets = node.assembler.unendorsed(2);
            assert_eq!(sets.len(), 5);
            let mut signed = Vec::new();
            for set in &sets[..4] {
                let (signature, receipt) = node.journal.endorse(set, 2, &key).unwrap();
                node.receipt = receipt;
                signed.push((set.clone(), signature));
            }
            for (set, signature) in &signed {
                journals
                    .sent_endorsements
                    .push((set.clone(), signature.clone()));
                for node in journals.live() {
                    node.assembler
                        .add_endorsement(set, signature.clone())
                        .unwrap();
                }
            }
            let key = journals.keys[2].clone();
            let node = journals.node(2);
            let set = node.assembler.unendorsed(2).remove(0);
            (
                set.clone(),
                sign_commitment_set(&journals.context, &set, 2, &key).unwrap(),
            )
        };
        journals.certify();
        // Openings of the pipelined frontiers arrive partially and out of order.
        for batch in [5, 3] {
            for slot in 0..3 {
                journals.reveal(slot, batch, &[0, 1, 2]);
            }
        }
        journals.reveal(2, 4, &[1]);
        for slot in 0..3 {
            let evidence = journals.node(slot).journal.session().evidence();
            assert_eq!(evidence.certified_tick, 14);
            assert_eq!(evidence.next_tick, 8);
        }
        if crash {
            // Peer 1's process dies. It restores from its retained receipt and
            // rebuilds its assembler; peers resend uncertified traffic.
            let receipt = journals.node(1).receipt;
            journals.nodes[1] = None;
            let journal = DurableSession::restore(
                &journals.root.join("peer-1.journal"),
                journals.context.clone(),
                journals.config.clone(),
                &journals.roster,
                receipt,
            )
            .unwrap();
            let evidence = journal.session().evidence();
            assert_eq!(evidence.pending.len(), 3);
            assert_eq!(
                evidence.pending[0].openings[2],
                Some(journals.opening(2, 4))
            );
            assert!(evidence.pending[1].ready());
            assert_eq!(evidence.next_tick, 8);
            // Its own openings of every unclosed batch survived, as did its
            // endorsement of the uncertified one.
            assert_eq!(
                journal
                    .sealed_openings()
                    .map(|opening| opening.start_tick)
                    .collect::<Vec<_>>(),
                vec![8, 10, 12, 14]
            );
            assert!(journal.endorsed_digest(14).is_some());
            let mut assembler = FrontierAssembler::following(evidence);
            for (slot, start, commitment) in &journals.sent_commitments {
                assembler
                    .add_commitment(*slot, 0, *start, *commitment)
                    .unwrap();
            }
            for (set, signature) in &journals.sent_endorsements {
                assembler.add_endorsement(set, signature.clone()).unwrap();
            }
            journals.nodes[1] = Some(Node {
                receipt,
                journal,
                assembler,
            });
            // The restarted peer cannot endorse a different set for tick 14.
            let mut other = set.clone();
            other.commitments[0] = [0xee; 32];
            let key = journals.keys[1].clone();
            assert!(journals.node(1).journal.endorse(&other, 1, &key).is_err());
            // Its sealed opening reopens frontier 8 without the harness's help.
            let own = journals
                .node(1)
                .journal
                .sealed_openings()
                .find(|opening| opening.start_tick == 8)
                .cloned()
                .unwrap();
            assert_eq!(own, journals.opening(1, 4));
        }
        // Peer 2 completes the last endorsement; every peer certifies it.
        journals
            .sent_endorsements
            .push((set.clone(), signature.clone()));
        for node in journals.live() {
            node.assembler
                .add_endorsement(&set, signature.clone())
                .unwrap();
        }
        journals.certify();
        for batch in [4, 6, 7] {
            for slot in 0..3 {
                journals.reveal(slot, batch, &[0, 1, 2]);
            }
        }
        journals.checkpoint();
        for slot in 0..3 {
            let node = journals.node(slot);
            node.journal.interrupt().unwrap();
            node.journal.finish().unwrap();
        }
        let terminal = journals.outcomes();
        assert!(terminal.iter().all(|outcome| *outcome == terminal[0]));
        terminal[0].clone()
    };
    let uninterrupted = run(false);
    let restarted = run(true);
    assert_eq!(restarted, uninterrupted);
    assert_eq!(uninterrupted.evidence_tick, 16);
    let journals = skirmish_journals();
    let expected = reference(&journals.config, &journals.roster, skirmish, 16);
    assert_eq!(uninterrupted.state_hash, expected.state_hash());
}
