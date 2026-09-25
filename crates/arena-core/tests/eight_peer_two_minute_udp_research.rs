//! Lossless loopback-UDP wire research: eight local evidence peers, not production P2P.
//! Test keys and sockets are fixture-owned; no wallet, bond, proof, or ledger exists.
use arena_core::{
    TICK_RATE,
    protocol::{CommitmentSet, Context, Reveal, input_commitment, sign_commitment_set},
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
// Pinned under sora-arena-first-release-7 with the final v2 state layout, on
// the authored Nyaagyu Estate with its team spawns and a script rewritten for
// its walls. The first-release-6 script on first-release-6 map data replays
// identically through the new kernel apart from hashes and objectives.
const EXPECTED_FINAL_HASH: &str =
    "5d000cfd7b28526bfa55fe0050c0d47872fa6c9831b189f6ea5c602d0af019ea";
const EXPECTED_TIMELINE_HASH: &str =
    "409dd59b3d6016dd35c026d0d6608e9f55f56512866f22d1cfae1c5d9b1b9c9e";

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

struct Peer {
    socket: UdpSocket,
    receiver: WireReceiver,
    session: RollbackSession,
}

fn peers(context: &Context) -> Vec<Peer> {
    (0..PLAYERS)
        .map(|_| {
            let socket = UdpSocket::bind("127.0.0.1:0").unwrap();
            socket
                .set_read_timeout(Some(Duration::from_secs(2)))
                .unwrap();
            Peer {
                socket,
                receiver: WireReceiver::new(context.clone()).unwrap(),
                session: RollbackSession::new(context.clone(), config(), &participants()).unwrap(),
            }
        })
        .collect()
}

fn fanout(
    peers: &mut [Peer],
    context: &Context,
    frame: &WireFrame,
    key: &SigningKey,
) -> Vec<(usize, WireFrame)> {
    let bytes = frame.encode(context, key).unwrap();
    let source = peers[frame.sender].socket.local_addr().unwrap();
    let mut delivered = Vec::with_capacity(PLAYERS - 1);
    for destination in 0..PLAYERS {
        if destination == frame.sender {
            continue;
        }
        let address = peers[destination].socket.local_addr().unwrap();
        assert_eq!(
            peers[frame.sender].socket.send_to(&bytes, address).unwrap(),
            bytes.len()
        );
        let mut buffer = [0u8; 2048];
        let (size, from) = peers[destination].socket.recv_from(&mut buffer).unwrap();
        assert_eq!(from, source);
        let pending = peers[destination]
            .session
            .evidence()
            .pending
            .as_ref()
            .map(|(set, _)| set);
        let decoded = peers[destination]
            .receiver
            .decode(&buffer[..size], pending)
            .unwrap();
        assert_eq!(decoded, *frame);
        delivered.push((destination, decoded));
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
    let mut sequence = [0u64; PLAYERS];
    let mut reference = World::new(config(), &participants()).unwrap();
    let mut timeline = Sha256::new();
    timeline.update(b"sora-arena:8-player-2-minute-local-research:v1\0");
    let mut delivered_packets = 0usize;
    let mut checkpoint_count = 0u32;

    for batch in 0..BATCHES {
        let first_tick = batch * 2;
        let evidence = peers[0].session.evidence();
        assert_eq!(evidence.next_tick, first_tick);
        let reveals = (0..PLAYERS)
            .map(|slot| Reveal {
                slot,
                inputs: (0..2)
                    .map(|offset| controls(first_tick + offset)[slot])
                    .collect(),
                salt: [(batch as usize + slot) as u8; 32],
            })
            .collect::<Vec<_>>();
        let set = CommitmentSet {
            epoch: evidence.epoch,
            start_tick: evidence.next_tick,
            parent: evidence.root,
            commitments: reveals
                .iter()
                .map(|reveal| {
                    input_commitment(
                        &context,
                        evidence.epoch,
                        evidence.next_tick,
                        evidence.root,
                        reveal.slot,
                        &reveal.inputs,
                        reveal.salt,
                    )
                    .unwrap()
                })
                .collect(),
        };
        let signatures = keys
            .iter()
            .enumerate()
            .map(|(slot, key)| sign_commitment_set(&context, &set, slot, key).unwrap())
            .collect::<Vec<_>>();
        let certificate = WireFrame {
            sender: 0,
            sequence: sequence[0],
            message: WireMessage::CommitmentCertificate {
                set: set.clone(),
                signatures: signatures.clone(),
            },
        };
        sequence[0] += 1;
        peers[0].session.certify(set.clone(), signatures).unwrap();
        for (destination, decoded) in fanout(&mut peers, &context, &certificate, &keys[0]) {
            let WireMessage::CommitmentCertificate { set, signatures } = decoded.message else {
                unreachable!();
            };
            peers[destination].session.certify(set, signatures).unwrap();
            delivered_packets += 1;
        }
        if batch == 0 {
            // One speculative frame must be replaced by the certified batch.
            for peer in &mut peers {
                peer.session.predict(controls(0).to_vec()).unwrap();
            }
        }

        let mut received = vec![vec![None; PLAYERS]; PLAYERS];
        let mut order = (0..PLAYERS).collect::<Vec<_>>();
        order.rotate_left(batch as usize % PLAYERS);
        if batch % 2 == 1 {
            order.reverse();
        }
        for origin in order {
            let reveal = reveals[origin].clone();
            received[origin][origin] = Some(reveal.clone());
            let frame = WireFrame {
                sender: origin,
                sequence: sequence[origin],
                message: WireMessage::Reveal {
                    set: set.clone(),
                    reveal,
                },
            };
            sequence[origin] += 1;
            for (destination, decoded) in fanout(&mut peers, &context, &frame, &keys[origin]) {
                let WireMessage::Reveal { reveal, .. } = decoded.message else {
                    unreachable!();
                };
                assert!(received[destination][origin].replace(reveal).is_none());
                delivered_packets += 1;
            }
        }
        for (peer, slots) in peers.iter_mut().zip(received) {
            peer.session
                .reveal(slots.into_iter().map(Option::unwrap).collect())
                .unwrap();
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
            let frame = WireFrame {
                sender: 0,
                sequence: sequence[0],
                message: WireMessage::Checkpoint {
                    checkpoint: checkpoint.clone(),
                    signatures: signatures.clone(),
                },
            };
            sequence[0] += 1;
            peers[0]
                .session
                .retain_checkpoint(checkpoint, signatures)
                .unwrap();
            for (destination, decoded) in fanout(&mut peers, &context, &frame, &keys[0]) {
                let WireMessage::Checkpoint {
                    checkpoint,
                    signatures,
                } = decoded.message
                else {
                    unreachable!();
                };
                peers[destination]
                    .session
                    .retain_checkpoint(checkpoint, signatures)
                    .unwrap();
                delivered_packets += 1;
            }
            checkpoint_count += 1;
        }
    }
    assert!(reference.terminal);
    assert_eq!(reference.tick, TICKS);
    assert_eq!(hex(&reference.state_hash()), EXPECTED_FINAL_HASH);
    assert_eq!(hex(&timeline.finalize()), EXPECTED_TIMELINE_HASH);
    for peer in &mut peers {
        assert_eq!(
            peer.session.confirmed().state_hash(),
            reference.state_hash()
        );
        assert_eq!(
            peer.session.last_checkpoint().unwrap().checkpoint.tick,
            TICKS
        );
        peer.session.finish_local().unwrap();
    }
    eprintln!(
        "peers={PLAYERS} ticks={TICKS} batches={BATCHES} checkpoint_rounds={checkpoint_count} delivered_udp_packets={delivered_packets} terminal_hash={} xor=0 proof=none settlement=none",
        hex(&reference.state_hash()),
    );
}
