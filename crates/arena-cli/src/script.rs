//! The eight-peer research lane's scripted controls and fixture admission,
//! shared by `arena peer` and its multi-process harness. Research only: the
//! match is offline with zero bond, and every key derives from a public
//! session number, so anyone can sign for any slot.
use arena_core::{
    RULES_VERSION,
    protocol::Context,
    simulation::{Config, FIRE, Input, Mode, Participant},
};
use ed25519_dalek::SigningKey;
use sha2::{Digest, Sha256};

/// Slot `slot`'s control for combat tick `tick`. Keep this identical to the
/// lane in arena-core's eight_player_two_minute_research.rs and
/// eight_peer_two_minute_udp_research.rs, whose final hash it reproduces.
pub fn control(tick: u32, slot: usize) -> Input {
    let phase = tick % 900;
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
}

/// Control on the Nyaagyu Estate, offline and without bond.
pub fn config(ticks: u32) -> Config {
    Config {
        mode: Mode::Control,
        map: 0,
        max_ticks: ticks,
        base_bond: 0,
        offline: true,
    }
}

/// Alternating teams of Samurai with the Arc carbine.
pub fn participants(players: usize) -> Vec<Participant> {
    (0..players)
        .map(|slot| Participant {
            team: (slot % 2) as u8,
            class: 0,
            weapon: 1,
            bond: 0,
            special_entitled: false,
        })
        .collect()
}

fn digest(parts: &[&[u8]]) -> [u8; 32] {
    let mut hash = Sha256::new();
    for part in parts {
        hash.update((part.len() as u32).to_le_bytes());
        hash.update(part);
    }
    hash.finalize().into()
}

/// Every slot's research key for `session`.
pub fn keys(session: u64, players: usize) -> Vec<SigningKey> {
    (0..players)
        .map(|slot| {
            SigningKey::from_bytes(&digest(&[
                b"sora-arena:research-mesh-key:v1",
                &session.to_le_bytes(),
                &(slot as u32).to_le_bytes(),
            ]))
        })
        .collect()
}

/// The research admission context: fixed network, the session number and a
/// manifest naming the rules and match length.
pub fn context(session: u64, keys: &[SigningKey], ticks: u32) -> Context {
    Context {
        network: digest(&[b"sora-arena:research-mesh-network:v1"]),
        session: digest(&[
            b"sora-arena:research-mesh-session:v1",
            &session.to_le_bytes(),
        ]),
        manifest: digest(&[
            b"sora-arena:research-mesh-manifest:v1",
            RULES_VERSION.as_bytes(),
            &ticks.to_le_bytes(),
        ]),
        roster: keys
            .iter()
            .map(|key| key.verifying_key().to_bytes())
            .collect(),
    }
}
