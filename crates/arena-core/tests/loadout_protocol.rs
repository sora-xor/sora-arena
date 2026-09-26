//! Respawn loadout requests (docs/combat-rules.md §2.2, §10) across every
//! protocol boundary: the canonical eight-byte input, input commitments, the
//! certified reveal transcript, signed wire frames, rollback prediction and
//! the durable journal. The kernel rules themselves are in respawn_loadout.rs.
use arena_core::{
    Error,
    protocol::{
        BATCH_TICKS, CommitmentSet, Context, Hash, Reveal, SlotSignature, input_commitment,
        sign_commitment_set,
    },
    recovery::DurableSession,
    rollback::RollbackSession,
    simulation::{Config, Event, FIRE, Input, LOADOUT, Mode, Participant, RESPAWN_TICKS, World},
    wire::{WireFrame, WireMessage, WireReceiver},
};
use ed25519_dalek::SigningKey;
use std::sync::atomic::{AtomicU64, Ordering};

fn request(class: i16, index: i16) -> Input {
    Input {
        buttons: LOADOUT,
        move_x: class,
        move_y: index,
        ..Input::default()
    }
}

fn keys() -> Vec<SigningKey> {
    (0..2)
        .map(|slot| SigningKey::from_bytes(&[slot as u8 + 71; 32]))
        .collect()
}

fn context(keys: &[SigningKey]) -> Context {
    Context {
        network: [61; 32],
        session: [62; 32],
        manifest: [63; 32],
        roster: keys.iter().map(|k| k.verifying_key().to_bytes()).collect(),
    }
}

fn config() -> Config {
    Config {
        mode: Mode::Control,
        map: 0,
        max_ticks: 36_000,
        base_bond: 0,
        offline: true,
    }
}

/// Slot 0: a team 0 Samurai with the Arc carbine. Slot 1: a team 1 Shinobi
/// admitted with its special, the Phantom SMG (13).
fn roster() -> [Participant; 2] {
    [(0, 0, 1), (1, 1, 13)].map(|(team, class, weapon)| Participant {
        team,
        class,
        weapon,
        bond: 0,
        special_entitled: false,
    })
}

// Ticks on which the dead Shinobi sends each request, two ticks (one batch)
// apiece: the Samurai special, which it was not admitted with; its own
// admitted special; then the Hanabi grenade launcher, which replaces that.
const WRONG_SPECIAL: u32 = 120;
const OWN_SPECIAL: u32 = 122;
const HANABI: u32 = 124;
const LAST_TICK: u32 = 600;

/// A fixed script on Nyaagyu Estate. Both players strafe from their first
/// team spawn onto the mid lane (the Samurai ends 40 mm short of y = 0), the
/// Samurai fires along it until the Shinobi dies, and the dead Shinobi sends
/// its three loadout requests.
fn controls(tick: u32) -> [Input; 2] {
    let strafe = |ticks: u32| if tick < ticks { 127 } else { 0 };
    let samurai = Input {
        buttons: if (62..WRONG_SPECIAL).contains(&tick) {
            FIRE
        } else {
            0
        },
        move_y: strafe(62),
        yaw: 0,
        ..Input::default()
    };
    let shinobi = match tick {
        t if (WRONG_SPECIAL..OWN_SPECIAL).contains(&t) => request(0, 2),
        t if (OWN_SPECIAL..HANABI).contains(&t) => request(1, 2),
        t if (HANABI..HANABI + 2).contains(&t) => request(3, 0),
        _ => Input {
            move_y: strafe(50),
            yaw: 32768,
            ..Input::default()
        },
    };
    [samurai, shinobi]
}

fn salt(slot: usize, tick: u32) -> Hash {
    let mut salt = [slot as u8; 32];
    salt[..4].copy_from_slice(&tick.to_le_bytes());
    salt
}

/// Commit, sign and open one batch of the script at `start`, chained to the
/// previous certified set `parent`.
fn batch(
    context: &Context,
    keys: &[SigningKey],
    epoch: u64,
    start: u32,
    parent: Hash,
) -> (CommitmentSet, Vec<SlotSignature>, Vec<Reveal>) {
    let reveals = (0..keys.len())
        .map(|slot| Reveal {
            start_tick: start,
            slot,
            inputs: (start..start + BATCH_TICKS as u32)
                .map(|tick| controls(tick)[slot])
                .collect(),
            salt: salt(slot, start),
        })
        .collect::<Vec<_>>();
    let set = CommitmentSet {
        epoch,
        start_tick: start,
        parent,
        commitments: reveals
            .iter()
            .map(|r| input_commitment(context, epoch, start, r.slot, &r.inputs, r.salt))
            .collect::<Result<_, _>>()
            .unwrap(),
    };
    let signatures = keys
        .iter()
        .enumerate()
        .map(|(slot, key)| sign_commitment_set(context, &set, slot, key).unwrap())
        .collect();
    (set, signatures, reveals)
}

#[test]
fn a_loadout_request_has_one_canonical_eight_byte_encoding() {
    let input = Input {
        yaw: 0x1234,
        pitch: -2,
        ..request(5, 2)
    };
    let bytes = input.encode();
    assert_eq!(bytes, [64, 0, 5, 2, 0x34, 0x12, 0xfe, 0xff]);
    assert_eq!(Input::decode(bytes).unwrap(), input);
    // Every other button may ride along with the request.
    let all = Input {
        buttons: 127,
        ..input
    };
    assert_eq!(Input::decode(all.encode()).unwrap(), all);
    // A decoder rejects a class, an index or a button outside the domain.
    for (offset, byte) in [(2, 6), (2, 0xff), (3, 3), (3, 0xff), (0, 128), (1, 1)] {
        let mut tampered = bytes;
        tampered[offset] = byte;
        assert!(
            matches!(Input::decode(tampered), Err(Error::InvalidInput(_))),
            "byte {offset} = {byte}"
        );
    }
    // Without the bit the same bytes are ordinary movement, in any range.
    let mut steering = bytes;
    steering[0] = 0;
    steering[2] = 0x81;
    assert_eq!(Input::decode(steering).unwrap().move_x, -127);
}

#[test]
fn input_commitments_bind_the_requested_class_and_loadout() {
    let keys = keys();
    let context = context(&keys);
    let commit = |inputs: [Input; 2]| input_commitment(&context, 0, 0, 1, &inputs, [4; 32]);
    let idle = Input::default();
    let base = commit([request(3, 0), idle]).unwrap();
    // Class, index, the bit itself and the tick it is sent on all bind.
    for other in [
        [request(4, 0), idle],
        [request(3, 1), idle],
        [
            Input {
                buttons: 0,
                ..request(3, 0)
            },
            idle,
        ],
        [idle, request(3, 0)],
    ] {
        assert_ne!(commit(other).unwrap(), base);
    }
    // An out-of-range request cannot be committed at all.
    for invalid in [request(6, 0), request(0, 3), request(-1, 0)] {
        assert!(matches!(
            commit([invalid, idle]),
            Err(Error::InvalidInput(_))
        ));
    }
}

#[test]
fn a_certified_request_respawns_the_dead_player_with_its_selection() {
    let keys = keys();
    let context = context(&keys);
    let mut session = RollbackSession::new(context.clone(), config(), &roster()).unwrap();
    let mut receiver = WireReceiver::new(context.clone()).unwrap();
    let mut reference = World::new(config(), &roster()).unwrap();
    let mut death = None;
    let mut respawn = None;
    for start in (0..LAST_TICK).step_by(BATCH_TICKS) {
        // Each peer predicts its script before the batch is certified.
        for tick in start..start + BATCH_TICKS as u32 {
            session.predict(controls(tick).to_vec()).unwrap();
        }
        let log = session.evidence();
        let (set, signatures, reveals) =
            batch(&context, &keys, log.epoch, start, log.commitment_head);
        session.certify(set.clone(), signatures).unwrap();
        // The requester's opening crosses the wire as a signed frame.
        let frame = WireFrame {
            sender: 1,
            sequence: u64::from(start),
            message: WireMessage::Reveal {
                set: set.clone(),
                reveal: reveals[1].clone(),
            },
        };
        let packet = frame.encode(&context, &keys[1]).unwrap();
        assert_eq!(
            receiver
                .decode(&packet, std::slice::from_ref(&set))
                .unwrap(),
            frame
        );
        if start == HANABI {
            // After the commitment no peer can swap its selection, and a
            // rejected opening changes neither the transcript nor the match.
            let before = (session.confirmed().state_hash(), session.evidence().root);
            for swapped in [request(4, 0), request(3, 1), Input::default()] {
                let mut forged = reveals.clone();
                forged[1].inputs[0] = swapped;
                assert!(session.reveal(forged).is_err());
            }
            assert_eq!(
                (session.confirmed().state_hash(), session.evidence().root),
                before
            );
            assert_eq!(session.evidence().next_tick, HANABI);
        }
        session.reveal(reveals).unwrap();
        // Replaying the revealed controls directly gives the same world.
        for tick in start..start + BATCH_TICKS as u32 {
            reference.step(&controls(tick)).unwrap();
            for event in &reference.events {
                match *event {
                    Event::Death { victim: 1, .. } => death = Some(tick),
                    Event::Respawn { slot: 1 } => respawn = Some(tick),
                    _ => {}
                }
            }
        }
        let confirmed = session.confirmed();
        assert_eq!(confirmed.state_hash(), reference.state_hash());
        assert_eq!(session.predicted().state_hash(), confirmed.state_hash());
        let pending = confirmed.players[1].pending_loadout;
        match start {
            WRONG_SPECIAL => assert_eq!(pending, None),
            OWN_SPECIAL => assert_eq!(pending, Some((1, 13))),
            HANABI => assert_eq!(pending, Some((3, 7))),
            _ => {}
        }
    }
    // The Shinobi died before its first request and respawned as a Hanabi
    // with the grenade launcher; its admitted special is unchanged.
    let death = death.expect("the scripted lane kills the Shinobi");
    assert!(death < WRONG_SPECIAL, "death on tick {death}");
    assert_eq!(respawn, Some(death + RESPAWN_TICKS));
    let p = &session.confirmed().players[1];
    assert!(p.alive);
    assert_eq!(
        (p.class, p.weapon, p.health, p.ammo, p.pending_loadout),
        (3, 7, 150, 5, None)
    );
    assert_eq!(p.admitted_special, Some(13));
    assert_eq!(session.confirmed().tick, LAST_TICK);
}

#[test]
fn the_durable_journal_replays_a_pending_selection_exactly() {
    static NEXT: AtomicU64 = AtomicU64::new(0);
    let path = std::env::temp_dir().join(format!(
        "sora-arena-loadout-journal-{}-{}",
        std::process::id(),
        NEXT.fetch_add(1, Ordering::Relaxed)
    ));
    let keys = keys();
    let context = context(&keys);
    let mut journal = DurableSession::create(&path, context.clone(), config(), &roster()).unwrap();
    for start in (0..HANABI + BATCH_TICKS as u32).step_by(BATCH_TICKS) {
        let log = journal.session().evidence();
        let (set, signatures, reveals) =
            batch(&context, &keys, log.epoch, start, log.commitment_head);
        journal.certify(set, signatures).unwrap();
        journal.reveal_many(reveals).unwrap();
    }
    let confirmed = journal.session().confirmed();
    assert!(!confirmed.players[1].alive);
    assert_eq!(confirmed.players[1].pending_loadout, Some((3, 7)));
    let expected = confirmed.state_hash();
    let receipt = journal.receipt();
    drop(journal);
    let restored = DurableSession::restore(&path, context, config(), &roster(), receipt).unwrap();
    assert_eq!(restored.session().confirmed().state_hash(), expected);
    assert_eq!(
        restored.session().confirmed().players[1].pending_loadout,
        Some((3, 7))
    );
    drop(restored);
    std::fs::remove_file(&path).unwrap();
}
