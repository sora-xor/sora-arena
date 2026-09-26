//! Lossless loopback-UDP wire research: eight local evidence peers, not production P2P.
//! Each peer assembles every pipelined certificate itself from the others'
//! signed commitments and set signatures, with eight certified frontiers
//! awaiting openings throughout. Test keys and sockets are fixture-owned; no
//! wallet, bond, proof, or ledger exists.
use arena_core::{
    TICK_RATE,
    protocol::{
        CommitmentSet, Context, FrontierAssembler, MAX_OUTSTANDING_FRONTIERS, Reveal,
        sign_commitment_set,
    },
    rollback::RollbackSession,
    simulation::{Config, FIRE, Input, Mode, Participant, World},
    wire::{WireFrame, WireMessage, WireReceiver},
};
use ed25519_dalek::SigningKey;
use sha2::{Digest, Sha256};
use std::{net::UdpSocket, time::Duration};

const PLAYERS: usize = 8;
const TICKS: u32 = 2 * 60 * TICK_RATE;
const BATCHES: u32 = TICKS / 2;
/// Commitments run this many batches ahead of certification.
const COMMIT_LEAD: u32 = 4;
/// Openings trail certification by this many frontiers.
const REVEAL_LAG: u32 = 8;
const _: () = assert!((REVEAL_LAG as usize) < MAX_OUTSTANDING_FRONTIERS);
// Pinned under sora-arena-first-release-7 with the final v2 state layout, on
// the authored Nyaagyu Estate with its team spawns and a script rewritten for
// its walls. The first-release-6 script on first-release-6 map data replays
// identically through the new kernel apart from hashes and objectives.
// Pipelining the evidence protocol left both kernel digests unchanged.
const EXPECTED_FINAL_HASH: &str =
    "5d000cfd7b28526bfa55fe0050c0d47872fa6c9831b189f6ea5c602d0af019ea";
const EXPECTED_TIMELINE_HASH: &str =
    "409dd59b3d6016dd35c026d0d6608e9f55f56512866f22d1cfae1c5d9b1b9c9e";
// The p2p-evidence v2 reveal transcript over all 3,600 frontiers, pinned
// with the pipelined commitment chain.
const EXPECTED_HISTORY_ROOT: &str =
    "7e381209517af7f0ea3486ba6ecfed25d171df11dcecb8ccf506be5c91d1e743";

fn participants() -> [Participant; PLAYERS] {
    std::array::from_fn(|slot| Participant {
        team: (slot % 2) as u8,
        class: 0,
        weapon: 1,
        bond: 0,
        special_entitled: false,
    })
}

fn controls(tick: u32) -> [Input; PLAYERS] {
    // Keep this scripted lane identical to eight_player_two_minute_research.rs.
    let phase = tick % 900;
    std::array::from_fn(|slot| {
        let team = slot % 2;
        // Estate team spawns by rank: team 0 at y = -5000 + 2000r facing +x,
        // team 1 at y = 5000 - 2000r facing -x. Each player's right is +y for
        // team 0 and -y for team 1, and strafing moves exactly 80 mm a tick.
        let rank = (slot / 2) as i32;
        let spawn_y = if team == 0 {
            -5000 + 2000 * rank
        } else {
            5000 - 2000 * rank
        };
        let right = if team == 0 { 1 } else { -1 };
        Input {
            buttons: FIRE,
            move_x: if phase < 100 {
                0
            } else if phase < 700 || (phase / 50).is_multiple_of(2) {
                127
            } else {
                -127
            },
            move_y: if phase < spawn_y.unsigned_abs() / 80 {
                (-spawn_y.signum() * right * 127) as i16
            } else {
                0
            },
            yaw: if team == 0 { 0 } else { 32768 },
            pitch: 0,
        }
    })
}

fn config() -> Config {
    Config {
        mode: Mode::Control,
        map: 0,
        max_ticks: TICKS,
        base_bond: 0,
        offline: true,
    }
}

fn opening(batch: u32, slot: usize) -> Reveal {
    let start_tick = batch * 2;
    let mut salt = [slot as u8; 32];
    salt[..4].copy_from_slice(&batch.to_le_bytes());
    Reveal {
        start_tick,
        slot,
        inputs: (0..2)
            .map(|offset| controls(start_tick + offset)[slot])
            .collect(),
        salt,
    }
}

struct Peer {
    socket: UdpSocket,
    receiver: WireReceiver,
    session: RollbackSession,
    assembler: FrontierAssembler,
    sequence: u64,
}

fn peers(context: &Context) -> Vec<Peer> {
    (0..PLAYERS)
        .map(|_| {
            let socket = UdpSocket::bind("127.0.0.1:0").unwrap();
            socket
                .set_read_timeout(Some(Duration::from_secs(2)))
                .unwrap();
            let session = RollbackSession::new(context.clone(), config(), &participants()).unwrap();
            Peer {
                socket,
                receiver: WireReceiver::new(context.clone()).unwrap(),
                assembler: FrontierAssembler::following(session.evidence()),
                session,
                sequence: 0,
            }
        })
        .collect()
}

/// Sign and send one message from `sender` to every other peer, returning
/// each destination's decoded copy.
fn fanout(
    peers: &mut [Peer],
    context: &Context,
    sender: usize,
    message: WireMessage,
    key: &SigningKey,
    delivered_packets: &mut usize,
) -> Vec<(usize, WireMessage)> {
    let frame = WireFrame {
        sender,
        sequence: peers[sender].sequence,
        message,
    };
    peers[sender].sequence += 1;
    let bytes = frame.encode(context, key).unwrap();
    let source = peers[sender].socket.local_addr().unwrap();
    let mut delivered = Vec::with_capacity(PLAYERS - 1);
    for destination in 0..PLAYERS {
        if destination == sender {
            continue;
        }
        let address = peers[destination].socket.local_addr().unwrap();
        assert_eq!(
            peers[sender].socket.send_to(&bytes, address).unwrap(),
            bytes.len()
        );
        let mut buffer = [0u8; 2048];
        let (size, from) = peers[destination].socket.recv_from(&mut buffer).unwrap();
        assert_eq!(from, source);
        let peer = &mut peers[destination];
        let decoded = peer
            .receiver
            .decode(&buffer[..size], peer.session.evidence())
            .unwrap();
        assert_eq!(decoded, frame);
        delivered.push((destination, decoded.message));
        *delivered_packets += 1;
    }
    delivered
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[test]
#[ignore = "full 7,200-tick signed UDP research load; run explicitly with --release -- --ignored"]
fn eight_local_peers_agree_on_two_minute_signed_history_and_kernel_hash() {
    let keys = (0..PLAYERS)
        .map(|slot| SigningKey::from_bytes(&[slot as u8 + 1; 32]))
        .collect::<Vec<_>>();
    let context = Context {
        network: [0xa1; 32],
        session: [0xa2; 32],
        manifest: [0xa3; 32],
        roster: keys
            .iter()
            .map(|key| key.verifying_key().to_bytes())
            .collect(),
    };
    let mut peers = peers(&context);
    let mut reference = World::new(config(), &participants()).unwrap();
    let mut timeline = Sha256::new();
    timeline.update(b"sora-arena:8-player-2-minute-local-research:v1\0");
    let mut delivered_packets = 0usize;
    let mut checkpoint_count = 0u32;
    let mut deepest_pipeline = 0usize;

    for step in 0..BATCHES + COMMIT_LEAD + REVEAL_LAG {
        // Every peer commits its own controls for the newest batch, and
        // presents it speculatively with the script's exact controls.
        if step < BATCHES {
            for origin in 0..PLAYERS {
                let commitment = opening(step, origin).commitment(&context, 0).unwrap();
                peers[origin]
                    .assembler
                    .add_commitment(origin, 0, step * 2, commitment)
                    .unwrap();
                let message = WireMessage::Commitment {
                    epoch: 0,
                    start_tick: step * 2,
                    commitment,
                };
                for (destination, decoded) in fanout(
                    &mut peers,
                    &context,
                    origin,
                    message,
                    &keys[origin],
                    &mut delivered_packets,
                ) {
                    let WireMessage::Commitment {
                        epoch,
                        start_tick,
                        commitment,
                    } = decoded
                    else {
                        unreachable!();
                    };
                    assert!(
                        peers[destination]
                            .assembler
                            .add_commitment(origin, epoch, start_tick, commitment)
                            .unwrap()
                    );
                }
            }
            for peer in &mut peers {
                for offset in 0..2 {
                    peer.session
                        .predict(controls(step * 2 + offset).to_vec())
                        .unwrap();
                }
            }
        }
        // Every peer endorses the set it assembled itself, then certifies
        // once it holds every endorsement.
        if let Some(batch) = step
            .checked_sub(COMMIT_LEAD)
            .filter(|batch| *batch < BATCHES)
        {
            for origin in 0..PLAYERS {
                let unendorsed = peers[origin].assembler.unendorsed(origin);
                assert_eq!(
                    unendorsed.len() as u32,
                    (BATCHES - batch).min(COMMIT_LEAD + 1)
                );
                let set: CommitmentSet = unendorsed[0].clone();
                assert_eq!(set.start_tick, batch * 2);
                let signature = sign_commitment_set(&context, &set, origin, &keys[origin]).unwrap();
                peers[origin]
                    .assembler
                    .add_endorsement(&set, signature.clone())
                    .unwrap();
                let message = WireMessage::SetSignature { set, signature };
                for (destination, decoded) in fanout(
                    &mut peers,
                    &context,
                    origin,
                    message,
                    &keys[origin],
                    &mut delivered_packets,
                ) {
                    let WireMessage::SetSignature { set, signature } = decoded else {
                        unreachable!();
                    };
                    assert!(
                        peers[destination]
                            .assembler
                            .add_endorsement(&set, signature)
                            .unwrap()
                    );
                }
            }
            let head = peers[0].session.evidence().commitment_head;
            for peer in &mut peers {
                let (set, signatures) = peer.assembler.take_certified().unwrap();
                assert_eq!(set.parent, head);
                peer.session.certify(set, signatures).unwrap();
                deepest_pipeline = deepest_pipeline.max(peer.session.evidence().pending.len());
            }
        }
        // Openings of the oldest pending frontier, in rotating slot orders.
        let Some(batch) = step
            .checked_sub(COMMIT_LEAD + REVEAL_LAG)
            .filter(|batch| *batch < BATCHES)
        else {
            continue;
        };
        let first_tick = batch * 2;
        let mut order = (0..PLAYERS).collect::<Vec<_>>();
        order.rotate_left(batch as usize % PLAYERS);
        if batch % 2 == 1 {
            order.reverse();
        }
        for origin in order {
            let reveal = opening(batch, origin);
            peers[origin].session.open(vec![reveal.clone()]).unwrap();
            let set = peers[origin]
                .session
                .evidence()
                .frontier(first_tick)
                .unwrap()
                .set
                .clone();
            let message = WireMessage::Reveal { set, reveal };
            for (destination, decoded) in fanout(
                &mut peers,
                &context,
                origin,
                message,
                &keys[origin],
                &mut delivered_packets,
            ) {
                let WireMessage::Reveal { reveal, .. } = decoded else {
                    unreachable!();
                };
                peers[destination].session.open(vec![reveal]).unwrap();
            }
        }
        for peer in &mut peers {
            peer.session.advance().unwrap();
        }
        for offset in 0..2 {
            let inputs = controls(first_tick + offset);
            for input in inputs {
                timeline.update(input.encode());
            }
            reference.step(&inputs).unwrap();
            timeline.update(reference.state_hash());
        }
        let expected = reference.state_hash();
        let root = peers[0].session.evidence().root;
        for peer in &peers {
            assert_eq!(peer.session.confirmed().state_hash(), expected);
            assert_eq!(peer.session.evidence().root, root);
            assert_eq!(peer.session.evidence().next_tick, first_tick + 2);
        }
        if (batch + 1) % 60 == 0 || batch + 1 == BATCHES {
            let checkpoint = peers[0].session.checkpoint();
            assert_eq!(checkpoint.state_hash, expected);
            for peer in &peers {
                assert_eq!(peer.session.checkpoint(), checkpoint);
            }
            let signatures = keys
                .iter()
                .enumerate()
                .map(|(slot, key)| checkpoint.sign(&context, slot, key).unwrap())
                .collect::<Vec<_>>();
            peers[0]
                .session
                .retain_checkpoint(checkpoint.clone(), signatures.clone())
                .unwrap();
            let message = WireMessage::Checkpoint {
                checkpoint,
                signatures,
            };
            for (destination, decoded) in fanout(
                &mut peers,
                &context,
                0,
                message,
                &keys[0],
                &mut delivered_packets,
            ) {
                let WireMessage::Checkpoint {
                    checkpoint,
                    signatures,
                } = decoded
                else {
                    unreachable!();
                };
                peers[destination]
                    .session
                    .retain_checkpoint(checkpoint, signatures)
                    .unwrap();
            }
            checkpoint_count += 1;
        }
    }
    assert!(reference.terminal);
    assert_eq!(reference.tick, TICKS);
    assert_eq!(deepest_pipeline, REVEAL_LAG as usize + 1);
    assert_eq!(hex(&reference.state_hash()), EXPECTED_FINAL_HASH);
    assert_eq!(hex(&timeline.finalize()), EXPECTED_TIMELINE_HASH);
    let mut outcomes = Vec::new();
    for peer in &mut peers {
        assert_eq!(
            peer.session.confirmed().state_hash(),
            reference.state_hash()
        );
        assert_eq!(
            peer.session.predicted().state_hash(),
            reference.state_hash()
        );
        assert_eq!(
            peer.session.last_checkpoint().unwrap().checkpoint.tick,
            TICKS
        );
        peer.session.finish_local().unwrap();
        outcomes.push(peer.session.terminal_outcome().unwrap());
    }
    assert!(outcomes.iter().all(|outcome| *outcome == outcomes[0]));
    assert!(outcomes[0].completed);
    assert_eq!(hex(&outcomes[0].history_root), EXPECTED_HISTORY_ROOT);
    eprintln!(
        "peers={PLAYERS} ticks={TICKS} batches={BATCHES} commit_lead={COMMIT_LEAD} reveal_lag={REVEAL_LAG} deepest_certified_pipeline={deepest_pipeline} checkpoint_rounds={checkpoint_count} delivered_udp_packets={delivered_packets} terminal_hash={} history_root={} xor=0 proof=none settlement=none",
        hex(&reference.state_hash()),
        hex(&outcomes[0].history_root),
    );
}
