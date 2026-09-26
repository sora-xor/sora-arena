//! Deterministic practice bots for the SORA Arena kernel.
//!
//! A bot reads the kernel's public [`World`] after a step and returns the
//! canonical [`Input`] for its slot on the next one, as a person at a
//! controller would. It never changes the world. Bots are not rules: they are
//! outside the state hash, the kernel's parity fingerprint and any future
//! proof, and the kernel validates their inputs like anyone else's.
//!
//! Every decision is integer arithmetic on the world state and the bot's own
//! memory. Difficulty comes from fixed reaction delays, aim-error patterns and
//! answer cadences, never from randomness, so a match replays identically on
//! every platform.
#![forbid(unsafe_code)]

mod brain;
pub mod geometry;
pub mod nav;
mod plan;

use arena_core::simulation::{Input, World};

/// Practice difficulty, weakest first: `ARENA_BOT_NOVICE`,
/// `ARENA_BOT_STANDARD`, `ARENA_BOT_VETERAN` and `ARENA_BOT_MASTER` in the C
/// ABI, the four tiers the practice lobby offers.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Difficulty {
    Novice = 0,
    Standard = 1,
    Veteran = 2,
    Master = 3,
}
impl Difficulty {
    pub const ALL: [Self; 4] = [Self::Novice, Self::Standard, Self::Veteran, Self::Master];
    /// The tier for a C ABI code, if it is one.
    pub fn from_code(code: u32) -> Option<Self> {
        Self::ALL.get(code as usize).copied()
    }
}

/// One difficulty tier. Every number is a fixed tick count or an angle in
/// 16-bit turns (65536 per revolution, about 182 per degree).
#[derive(Debug)]
pub(crate) struct Tier {
    /// Ticks a newly sighted enemy must stay in view before the bot attacks.
    reaction: u16,
    /// Aim error amplitude on acquiring a target, the floor it settles to, and
    /// the ticks of tracking that settling takes.
    aim_error: i32,
    aim_floor: i32,
    settle: u16,
    /// Largest view turn per tick.
    turn: i32,
    /// The bot answers one in `answer` melee threat episodes with a timed guard
    /// or counter stance.
    answer: u32,
    /// Reads a charging heavy blow and guards even when it could strike.
    reads_charge: bool,
    /// Uncharged fire cadence: fire for `burst` ticks of sight, then hold for
    /// `pause`.
    burst: u16,
    pause: u16,
    /// Ticks between strafe direction changes; 0 never strafes.
    strafe: u32,
    /// Leads moving targets with projectiles.
    lead: bool,
    /// Treats enemy decoys as players.
    fooled: bool,
    /// Changes class or weapon at respawn for the team or the scoreboard.
    adapts: bool,
}

const TIERS: [Tier; 4] = [
    Tier {
        reaction: 30,
        aim_error: 1500,
        aim_floor: 560,
        settle: 90,
        turn: 1400,
        answer: 4,
        reads_charge: false,
        burst: 30,
        pause: 36,
        strafe: 0,
        lead: false,
        fooled: true,
        adapts: false,
    },
    Tier {
        reaction: 16,
        aim_error: 900,
        aim_floor: 240,
        settle: 60,
        turn: 2600,
        answer: 2,
        reads_charge: false,
        burst: 60,
        pause: 18,
        strafe: 75,
        lead: true,
        fooled: true,
        adapts: true,
    },
    Tier {
        reaction: 8,
        aim_error: 420,
        aim_floor: 70,
        settle: 40,
        turn: 4600,
        answer: 1,
        reads_charge: true,
        burst: 1,
        pause: 0,
        strafe: 48,
        lead: true,
        fooled: false,
        adapts: true,
    },
    // Master punishes every opening: half the Veteran's reaction, a tighter
    // aim that settles sooner, a faster turn and a quicker strafe.
    Tier {
        reaction: 4,
        aim_error: 260,
        aim_floor: 30,
        settle: 24,
        turn: 6400,
        answer: 1,
        reads_charge: true,
        burst: 1,
        pause: 0,
        strafe: 36,
        lead: true,
        fooled: false,
        adapts: true,
    },
];

/// Bots for every slot of one match. Each slot keeps its own memory, so a
/// slot can be driven by a bot on some ticks and by a person on others.
#[derive(Debug, Clone)]
pub struct Bots {
    memories: Vec<brain::Memory>,
}
impl Bots {
    pub fn new(world: &World) -> Self {
        Self {
            memories: vec![brain::Memory::default(); world.players.len()],
        }
    }
    /// The input for `slot` on the world's next step. A bot plans once per
    /// tick: a repeated call before the world steps returns the same input.
    ///
    /// # Panics
    /// If `slot` is not a participant of the world these bots were made for.
    pub fn input(&mut self, world: &World, slot: usize, difficulty: Difficulty) -> Input {
        brain::think(
            &mut self.memories[slot],
            world,
            slot,
            &TIERS[difficulty as usize],
        )
    }
}
