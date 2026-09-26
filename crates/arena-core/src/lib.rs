//! Deterministic first-release SORA Arena reference simulation and evidence.
//!
//! This crate is not a qualified execution prover or a ledger authority. It is
//! the reference implementation whose complete transitions must be constrained
//! by the native Iroha FPS relation before value-bearing admission is enabled.
#![forbid(unsafe_code)]

pub mod arena_export;
pub mod catalog;
pub mod economy;
pub mod encrypted_wire;
mod fragmented_wire;
pub mod handshake;
pub mod localhost_transport;
pub mod maps;
pub mod math;
pub mod mesh_transport;
pub mod protocol;
pub mod recovery;
pub mod rollback;
pub mod simulation;
pub mod wire;

pub const ABI_VERSION: u32 = 3;
pub const TICK_RATE: u32 = 60;
pub const MAX_PLAYERS: usize = 12;
pub const MAX_TICKS: u32 = 36_000;
pub const ASSIST_TICKS: u32 = 5 * TICK_RATE;
pub const RULES_VERSION: &str = "sora-arena-first-release-7";

/// Qualification is an actual release gate, never a user-configurable toggle.
pub const fn proof_qualified() -> bool {
    false
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    InvalidConfig(&'static str),
    InvalidInput(&'static str),
    InvalidEvidence(&'static str),
    Arithmetic,
    Terminal,
}

impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidConfig(s) | Self::InvalidInput(s) | Self::InvalidEvidence(s) => {
                f.write_str(s)
            }
            Self::Arithmetic => f.write_str("checked arithmetic failed"),
            Self::Terminal => f.write_str("match already terminal"),
        }
    }
}
impl std::error::Error for Error {}
