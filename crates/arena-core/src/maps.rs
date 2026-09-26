//! Versioned first-release arena data, `arena-map-v1` (docs/combat-rules.md
//! §7). Every value is an exact integer in millimetres, 16-bit turns or ticks.
//! The map digest binds everything that can change a match outcome; the lane
//! polylines guide bots and presentation only and have a separate digest.
use crate::math::{Aabb, Vec3};
use sha2::{Digest, Sha256};

/// Arena bounds lie inside ±24,000 mm (§7.2).
pub const GLOBAL_BOUNDS: i32 = 24_000;
/// Every wall is at least this high: above the 1936 mm apex of a jump, so no
/// player can jump over a wall or land inside one (§7.2).
pub const MIN_WALL_HEIGHT: i32 = 2000;
/// Native ABI consumers accept at most 64 walls per arena.
pub const MAX_WALLS: usize = 64;
const MAP_DOMAIN: &[u8] = b"sora-arena:arena-map:v1\0";
const LANES_DOMAIN: &[u8] = b"sora-arena:arena-lanes:v1\0";

/// The playable rectangle. Player centres stay inside it shrunk by the body
/// radius; projectiles that leave it expire.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Bounds {
    pub min_x: i32,
    pub min_y: i32,
    pub max_x: i32,
    pub max_y: i32,
}
impl Bounds {
    /// Closed containment in the floor plane.
    pub fn contains(self, x: i32, y: i32) -> bool {
        (self.min_x..=self.max_x).contains(&x) && (self.min_y..=self.max_y).contains(&y)
    }
}

/// A static wall. The label names the piece for presentation only.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Wall {
    pub aabb: Aabb,
    pub label: &'static str,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Spawn {
    pub x: i32,
    pub y: i32,
    pub yaw: u16,
}
impl Spawn {
    /// Floor-level spawn position.
    pub const fn position(self) -> Vec3 {
        Vec3::new(self.x, self.y, 0)
    }
}

/// The Control point: a floor circle (§8.1).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ControlPoint {
    pub x: i32,
    pub y: i32,
    pub radius: i32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HazardKind {
    Fire = 1,
    Slag = 2,
    Shredder = 3,
}
impl HazardKind {
    pub const fn name(self) -> &'static str {
        match self {
            Self::Fire => "fire",
            Self::Slag => "slag",
            Self::Shredder => "shredder",
        }
    }
}

/// An environmental floor volume that pulses `damage` every `period` ticks
/// (§9). Hazards never block movement, rays, projectiles or line of sight.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Hazard {
    pub kind: HazardKind,
    pub volume: Aabb,
    pub damage: i32,
    pub period: u16,
    pub label: &'static str,
}

/// A bot and presentation guidance polyline. Not rules data.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Lane {
    pub name: &'static str,
    pub points: &'static [(i32, i32)],
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Arena {
    pub id: u8,
    pub slug: &'static str,
    pub name: &'static str,
    pub bounds: Bounds,
    /// Canonical order: the four perimeter walls, then interior pieces in
    /// point-mirror pairs. It is the native `arena_map_wall` index order.
    pub walls: &'static [Wall],
    /// Six spawns per team, used by team rank (§10).
    pub team_spawns: [[Spawn; 6]; 2],
    /// Twelve FFA and Melee spawns in mirrored pairs.
    pub ffa_spawns: [Spawn; 12],
    pub control: ControlPoint,
    /// Axis-aligned payload waypoints from team 0's base to team 1's.
    pub route: &'static [(i32, i32)],
    /// Distances along the route; each becomes the rollback floor once passed.
    pub checkpoints: [i32; 3],
    pub hazards: &'static [Hazard],
    /// `north`, `south` and `mid`, in that order.
    pub lanes: [Lane; 3],
}

impl Arena {
    /// The arena for a configured map id, if it exists.
    pub fn get(map: u8) -> Option<&'static Self> {
        ARENAS.get(usize::from(map))
    }
    /// Every spawn a player can use: both teams' spawns, then the FFA spawns.
    pub fn spawns(&self) -> impl Iterator<Item = Spawn> + '_ {
        self.team_spawns
            .iter()
            .flatten()
            .chain(self.ffa_spawns.iter())
            .copied()
    }
    /// Exact payload route length. Segments are axis-aligned.
    pub fn route_length(&self) -> i32 {
        self.route
            .windows(2)
            .map(|pair| (pair[1].0 - pair[0].0).abs() + (pair[1].1 - pair[0].1).abs())
            .sum()
    }
    /// The floor point `distance` millimetres along the payload route,
    /// clamped to its ends.
    pub fn route_point(&self, distance: i32) -> Vec3 {
        let mut left = distance.max(0);
        for pair in self.route.windows(2) {
            let ((x0, y0), (x1, y1)) = (pair[0], pair[1]);
            let length = (x1 - x0).abs() + (y1 - y0).abs();
            if left <= length {
                return Vec3::new(
                    x0 + (x1 - x0).signum() * left,
                    y0 + (y1 - y0).signum() * left,
                    0,
                );
            }
            left -= length;
        }
        let (x, y) = self.route[self.route.len() - 1];
        Vec3::new(x, y, 0)
    }
    /// SHA-256 of the canonical little-endian encoding in §7.1. It binds every
    /// rules value of the arena, and replaces the wall list in the state hash.
    pub fn map_digest(&self) -> [u8; 32] {
        let mut h = Sha256::new();
        h.update(MAP_DOMAIN);
        h.update([self.id]);
        let b = self.bounds;
        for n in [b.min_x, b.min_y, b.max_x, b.max_y] {
            h.update(n.to_le_bytes());
        }
        h.update((self.walls.len() as u32).to_le_bytes());
        for wall in self.walls {
            update_box(&mut h, wall.aabb);
        }
        let spawn = |h: &mut Sha256, s: Spawn| {
            h.update(s.x.to_le_bytes());
            h.update(s.y.to_le_bytes());
            h.update(s.yaw.to_le_bytes());
        };
        for s in self.team_spawns.iter().flatten() {
            spawn(&mut h, *s);
        }
        h.update((self.ffa_spawns.len() as u32).to_le_bytes());
        for s in self.ffa_spawns {
            spawn(&mut h, s);
        }
        let c = self.control;
        for n in [c.x, c.y, c.radius] {
            h.update(n.to_le_bytes());
        }
        h.update((self.route.len() as u32).to_le_bytes());
        for &(x, y) in self.route {
            h.update(x.to_le_bytes());
            h.update(y.to_le_bytes());
        }
        for c in self.checkpoints {
            h.update((c as u32).to_le_bytes());
        }
        h.update((self.hazards.len() as u32).to_le_bytes());
        for hazard in self.hazards {
            h.update([hazard.kind as u8]);
            update_box(&mut h, hazard.volume);
            h.update(hazard.damage.to_le_bytes());
            h.update(hazard.period.to_le_bytes());
        }
        h.finalize().into()
    }
    /// SHA-256 of the lane polylines (§7.1). It is not part of the state hash,
    /// so editing bot guidance cannot change a match outcome.
    pub fn lanes_digest(&self) -> [u8; 32] {
        let mut h = Sha256::new();
        h.update(LANES_DOMAIN);
        h.update([self.id]);
        h.update((self.lanes.len() as u32).to_le_bytes());
        for lane in self.lanes {
            h.update((lane.name.len() as u32).to_le_bytes());
            h.update(lane.name.as_bytes());
            h.update((lane.points.len() as u32).to_le_bytes());
            for &(x, y) in lane.points {
                h.update(x.to_le_bytes());
                h.update(y.to_le_bytes());
            }
        }
        h.finalize().into()
    }
}

fn update_box(h: &mut Sha256, b: Aabb) {
    for n in [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z] {
        h.update(n.to_le_bytes());
    }
}

const fn aabb(x1: i32, y1: i32, z1: i32, x2: i32, y2: i32, z2: i32) -> Aabb {
    Aabb {
        min: Vec3::new(x1, y1, z1),
        max: Vec3::new(x2, y2, z2),
    }
}
const fn wall(x1: i32, y1: i32, z1: i32, x2: i32, y2: i32, z2: i32, label: &'static str) -> Wall {
    Wall {
        aabb: aabb(x1, y1, z1, x2, y2, z2),
        label,
    }
}
#[expect(
    clippy::too_many_arguments,
    reason = "One hazard record of the arena-data table, field for field"
)]
const fn hazard(
    kind: HazardKind,
    x1: i32,
    y1: i32,
    z1: i32,
    x2: i32,
    y2: i32,
    z2: i32,
    damage: i32,
    period: u16,
    label: &'static str,
) -> Hazard {
    Hazard {
        kind,
        volume: aabb(x1, y1, z1, x2, y2, z2),
        damage,
        period,
        label,
    }
}
const fn spawn(x: i32, y: i32, yaw: u16) -> Spawn {
    Spawn { x, y, yaw }
}

// The tables below transcribe the `arena-data` blocks of docs/combat-rules.md
// §7.3-§7.6 record for record, one record per line. tests/arena_maps.rs parses
// those blocks and rejects any difference.

#[rustfmt::skip]
const ESTATE_WALLS: [Wall; 38] = [
    wall(-23000, -17000, 0, 23000, -16000, 6000, "perimeter south"),
    wall(-23000, 16000, 0, 23000, 17000, 6000, "perimeter north"),
    wall(-23000, -16000, 0, -22000, 16000, 6000, "perimeter west"),
    wall(22000, -16000, 0, 23000, 16000, 6000, "perimeter east"),
    wall(14500, -16000, 0, 15500, -9500, 4500, "east gatehouse south wing"),
    wall(-15500, 9500, 0, -14500, 16000, 4500, "mirror of east gatehouse south wing"),
    wall(14500, -6000, 0, 15500, -1800, 4500, "east gatehouse inner south"),
    wall(-15500, 1800, 0, -14500, 6000, 4500, "mirror of east gatehouse inner south"),
    wall(14500, 1800, 0, 15500, 6000, 4500, "east gatehouse inner north"),
    wall(-15500, -6000, 0, -14500, -1800, 4500, "mirror of east gatehouse inner north"),
    wall(14500, 9500, 0, 15500, 16000, 4500, "east gatehouse north wing"),
    wall(-15500, -16000, 0, -14500, -9500, 4500, "mirror of east gatehouse north wing"),
    wall(-7000, 8500, 0, 7000, 12500, 5500, "north dojo hall"),
    wall(-7000, -12500, 0, 7000, -8500, 5500, "mirror of north dojo hall"),
    wall(3000, 7000, 0, 5000, 7600, 2000, "north veranda screen east"),
    wall(-5000, -7600, 0, -3000, -7000, 2000, "mirror of north veranda screen east"),
    wall(-5000, 7000, 0, -3000, 7600, 2000, "north veranda screen west"),
    wall(3000, -7600, 0, 5000, -7000, 2000, "mirror of north veranda screen west"),
    wall(2600, 2200, 0, 3200, 2800, 2000, "toro north-east"),
    wall(-3200, -2800, 0, -2600, -2200, 2000, "mirror of toro north-east"),
    wall(2600, -2800, 0, 3200, -2200, 2000, "toro south-east"),
    wall(-3200, 2200, 0, -2600, 2800, 2000, "mirror of toro south-east"),
    wall(9500, 3000, 0, 12500, 6500, 5000, "east kura north"),
    wall(-12500, -6500, 0, -9500, -3000, 5000, "mirror of east kura north"),
    wall(9500, -6500, 0, 12500, -3000, 5000, "east kura south"),
    wall(-12500, 3000, 0, -9500, 6500, 5000, "mirror of east kura south"),
    wall(9000, 1000, 0, 10200, 2200, 2000, "east garden rock"),
    wall(-10200, -2200, 0, -9000, -1000, 2000, "mirror of east garden rock"),
    wall(8000, 9000, 0, 8600, 13500, 2000, "east hedge north"),
    wall(-8600, -13500, 0, -8000, -9000, 2000, "mirror of east hedge north"),
    wall(5000, -4500, 0, 6500, -3900, 2000, "courtyard wall south-east"),
    wall(-6500, 3900, 0, -5000, 4500, 2000, "mirror of courtyard wall south-east"),
    wall(9500, -14500, 0, 11000, -13000, 2400, "well house"),
    wall(-11000, 13000, 0, -9500, 14500, 2400, "mirror of well house"),
    wall(12000, 8500, 0, 13200, 9700, 2000, "pine planter north"),
    wall(-13200, -9700, 0, -12000, -8500, 2000, "mirror of pine planter north"),
    wall(12000, -11500, 0, 13200, -10300, 2000, "pine planter south"),
    wall(-13200, 10300, 0, -12000, 11500, 2000, "mirror of pine planter south"),
];
#[rustfmt::skip]
const ESTATE_ROUTE: [(i32, i32); 6] = [
    (-18500, 0), (-8000, 0), (-8000, -5500), (8000, -5500), (8000, 0), (18500, 0),
];
#[rustfmt::skip]
const ESTATE_HAZARDS: [Hazard; 2] = [
    hazard(HazardKind::Fire, 3000, 13500, 0, 5000, 15500, 600, 10, 15, "burning storehouse embers"),
    hazard(HazardKind::Fire, -5000, -15500, 0, -3000, -13500, 600, 10, 15, "mirror of burning storehouse embers"),
];
#[rustfmt::skip]
const ESTATE_LANE_NORTH: [(i32, i32); 10] = [
    (-18500, 3000), (-16500, 3000), (-16500, 7750), (-7500, 7750), (-7500, 13000),
    (7500, 13000), (7500, 7750), (16500, 7750), (16500, 3000), (18500, 3000),
];
#[rustfmt::skip]
const ESTATE_LANE_SOUTH: [(i32, i32); 10] = [
    (-18500, -3000), (-16500, -3000), (-16500, -7750), (-7500, -7750), (-7500, -13000),
    (7500, -13000), (7500, -7750), (16500, -7750), (16500, -3000), (18500, -3000),
];
#[rustfmt::skip]
const ESTATE_LANE_MID: [(i32, i32); 2] = [
    (-18500, 0), (18500, 0),
];
#[rustfmt::skip]
const LANTERN_WARD_WALLS: [Wall; 40] = [
    wall(-24000, -15000, 0, 24000, -14000, 7000, "perimeter south"),
    wall(-24000, 14000, 0, 24000, 15000, 7000, "perimeter north"),
    wall(-24000, -14000, 0, -23000, 14000, 7000, "perimeter west"),
    wall(23000, -14000, 0, 24000, 14000, 7000, "perimeter east"),
    wall(2000, 2500, 0, 6000, 6500, 5000, "north row machiya A"),
    wall(-6000, -6500, 0, -2000, -2500, 5000, "mirror of north row machiya A"),
    wall(8000, 2500, 0, 12000, 6500, 5500, "north row machiya B"),
    wall(-12000, -6500, 0, -8000, -2500, 5500, "mirror of north row machiya B"),
    wall(14000, 2500, 0, 17500, 6500, 5000, "north row machiya C"),
    wall(-17500, -6500, 0, -14000, -2500, 5000, "mirror of north row machiya C"),
    wall(1000, -6500, 0, 5000, -2500, 5000, "south row machiya A"),
    wall(-5000, 2500, 0, -1000, 6500, 5000, "mirror of south row machiya A"),
    wall(7000, -6500, 0, 11000, -2500, 5500, "south row machiya B"),
    wall(-11000, 2500, 0, -7000, 6500, 5500, "mirror of south row machiya B"),
    wall(13000, -6500, 0, 16500, -2500, 5000, "south row machiya C"),
    wall(-16500, 2500, 0, -13000, 6500, 5000, "mirror of south row machiya C"),
    wall(1000, 10500, 0, 6500, 14000, 6000, "outer north teahouse"),
    wall(-6500, -14000, 0, -1000, -10500, 6000, "mirror of outer north teahouse"),
    wall(9500, 10500, 0, 15000, 14000, 6000, "outer north warehouse"),
    wall(-15000, -14000, 0, -9500, -10500, 6000, "mirror of outer north warehouse"),
    wall(3500, -14000, 0, 8500, -10500, 6000, "outer south bathhouse"),
    wall(-8500, 10500, 0, -3500, 14000, 6000, "mirror of outer south bathhouse"),
    wall(11500, -14000, 0, 17000, -10500, 6000, "outer south merchant house"),
    wall(-17000, 10500, 0, -11500, 14000, 6000, "mirror of outer south merchant house"),
    wall(-400, 6600, 0, 400, 7400, 2200, "north street lantern tower"),
    wall(-400, -7400, 0, 400, -6600, 2200, "mirror of north street lantern tower"),
    wall(4000, 6600, 0, 5200, 7400, 2000, "north street cart"),
    wall(-5200, -7400, 0, -4000, -6600, 2000, "mirror of north street cart"),
    wall(13000, 6600, 0, 14200, 7400, 2000, "north street barrels"),
    wall(-14200, -7400, 0, -13000, -6600, 2000, "mirror of north street barrels"),
    wall(9800, 1500, 0, 10600, 2300, 2200, "main street lantern post"),
    wall(-10600, -2300, 0, -9800, -1500, 2200, "mirror of main street lantern post"),
    wall(2500, 800, 0, 3700, 1600, 2000, "main street stall"),
    wall(-3700, -1600, 0, -2500, -800, 2000, "mirror of main street stall"),
    wall(11500, -1600, 0, 12700, -800, 2000, "main street cart"),
    wall(-12700, 800, 0, -11500, 1600, 2000, "mirror of main street cart"),
    wall(19000, 7000, 0, 20000, 11000, 3500, "east yard fence north"),
    wall(-20000, -11000, 0, -19000, -7000, 3500, "mirror of east yard fence north"),
    wall(19000, -11000, 0, 20000, -7000, 3500, "east yard fence south"),
    wall(-20000, 7000, 0, -19000, 11000, 3500, "mirror of east yard fence south"),
];
#[rustfmt::skip]
const LANTERN_WARD_ROUTE: [(i32, i32); 6] = [
    (-19500, 0), (-6000, 0), (-6000, 8500), (7000, 8500), (7000, 0), (19500, 0),
];
#[rustfmt::skip]
const LANTERN_WARD_HAZARDS: [Hazard; 2] = [
    hazard(HazardKind::Fire, 9500, 9000, 0, 11500, 10400, 600, 10, 15, "spilled lantern oil"),
    hazard(HazardKind::Fire, -11500, -10400, 0, -9500, -9000, 600, 10, 15, "mirror of spilled lantern oil"),
];
#[rustfmt::skip]
const LANTERN_WARD_LANE_NORTH: [(i32, i32); 6] = [
    (-19500, 3000), (-18500, 3000), (-18500, 8000), (18500, 8000), (18500, 3000),
    (19500, 3000),
];
#[rustfmt::skip]
const LANTERN_WARD_LANE_SOUTH: [(i32, i32); 6] = [
    (-19500, -3000), (-18500, -3000), (-18500, -8000), (18500, -8000), (18500, -3000),
    (19500, -3000),
];
#[rustfmt::skip]
const LANTERN_WARD_LANE_MID: [(i32, i32); 2] = [
    (-19500, 0), (19500, 0),
];
#[rustfmt::skip]
const SILK_FOUNDRY_WALLS: [Wall; 38] = [
    wall(-21000, -19000, 0, 21000, -18000, 8000, "perimeter south"),
    wall(-21000, 18000, 0, 21000, 19000, 8000, "perimeter north"),
    wall(-21000, -18000, 0, -20000, 18000, 8000, "perimeter west"),
    wall(20000, -18000, 0, 21000, 18000, 8000, "perimeter east"),
    wall(-2500, 5000, 0, 2500, 8000, 6500, "north furnace"),
    wall(-2500, -8000, 0, 2500, -5000, 6500, "mirror of north furnace"),
    wall(3800, 1500, 0, 4800, 2500, 2000, "casting mould north-east"),
    wall(-4800, -2500, 0, -3800, -1500, 2000, "mirror of casting mould north-east"),
    wall(3800, -2500, 0, 4800, -1500, 2000, "casting mould south-east"),
    wall(-4800, 1500, 0, -3800, 2500, 2000, "mirror of casting mould south-east"),
    wall(5000, 10500, 0, 5800, 15500, 2000, "loom row 1"),
    wall(-5800, -15500, 0, -5000, -10500, 2000, "mirror of loom row 1"),
    wall(8000, 10500, 0, 8800, 15500, 2000, "loom row 2"),
    wall(-8800, -15500, 0, -8000, -10500, 2000, "mirror of loom row 2"),
    wall(11000, 10500, 0, 11800, 15500, 2000, "loom row 3"),
    wall(-11800, -15500, 0, -11000, -10500, 2000, "mirror of loom row 3"),
    wall(5000, -15500, 0, 9000, -14000, 2200, "reeling machine A"),
    wall(-9000, 14000, 0, -5000, 15500, 2200, "mirror of reeling machine A"),
    wall(5000, -11500, 0, 9000, -10000, 2200, "reeling machine B"),
    wall(-9000, 10000, 0, -5000, 11500, 2200, "mirror of reeling machine B"),
    wall(11500, -15500, 0, 12500, -10000, 2600, "drive shaft housing"),
    wall(-12500, 10000, 0, -11500, 15500, 2600, "mirror of drive shaft housing"),
    wall(8500, 4000, 0, 9500, 5000, 7000, "hall pillar north-east"),
    wall(-9500, -5000, 0, -8500, -4000, 7000, "mirror of hall pillar north-east"),
    wall(8500, -5000, 0, 9500, -4000, 7000, "hall pillar south-east"),
    wall(-9500, 4000, 0, -8500, 5000, 7000, "mirror of hall pillar south-east"),
    wall(13500, 4500, 0, 16500, 8000, 5000, "east boiler room"),
    wall(-16500, -8000, 0, -13500, -4500, 5000, "mirror of east boiler room"),
    wall(13500, -8000, 0, 16500, -4500, 5000, "east coal bunker"),
    wall(-16500, 4500, 0, -13500, 8000, 5000, "mirror of east coal bunker"),
    wall(7000, -2400, 0, 8200, -1200, 2000, "crate stack east"),
    wall(-8200, 1200, 0, -7000, 2400, 2000, "mirror of crate stack east"),
    wall(-3500, 14200, 0, -2500, 15200, 2000, "crate stack north"),
    wall(2500, -15200, 0, 3500, -14200, 2000, "mirror of crate stack north"),
    wall(-1000, 10500, 0, 1000, 11300, 2000, "bridge rail north"),
    wall(-1000, -11300, 0, 1000, -10500, 2000, "mirror of bridge rail north"),
    wall(16500, 9500, 0, 18000, 13500, 4000, "east dye vats"),
    wall(-18000, -13500, 0, -16500, -9500, 4000, "mirror of east dye vats"),
];
#[rustfmt::skip]
const SILK_FOUNDRY_ROUTE: [(i32, i32); 8] = [
    (-16500, 0), (-10500, 0), (-10500, 12750), (3500, 12750), (3500, 3200), (12500, 3200), (12500, 0), (16500, 0),
];
#[rustfmt::skip]
const SILK_FOUNDRY_HAZARDS: [Hazard; 2] = [
    hazard(HazardKind::Slag, -6000, 8200, 0, 6000, 9400, 400, 20, 15, "slag channel north"),
    hazard(HazardKind::Slag, -6000, -9400, 0, 6000, -8200, 400, 20, 15, "mirror of slag channel north"),
];
#[rustfmt::skip]
const SILK_FOUNDRY_LANE_NORTH: [(i32, i32); 8] = [
    (-16500, 3000), (-10500, 3000), (-10500, 12750), (3500, 12750), (3500, 16750),
    (12750, 16750), (12750, 3000), (16500, 3000),
];
#[rustfmt::skip]
const SILK_FOUNDRY_LANE_SOUTH: [(i32, i32); 8] = [
    (-16500, -3000), (-12750, -3000), (-12750, -16750), (-3500, -16750), (-3500, -12750),
    (10500, -12750), (10500, -3000), (16500, -3000),
];
#[rustfmt::skip]
const SILK_FOUNDRY_LANE_MID: [(i32, i32); 2] = [
    (-16500, 0), (16500, 0),
];
#[rustfmt::skip]
const DEBT_CITADEL_WALLS: [Wall; 42] = [
    wall(-24000, -17000, 0, 24000, -16000, 9000, "perimeter south"),
    wall(-24000, 16000, 0, 24000, 17000, 9000, "perimeter north"),
    wall(-24000, -16000, 0, -23000, 16000, 9000, "perimeter west"),
    wall(23000, -16000, 0, 24000, 16000, 9000, "perimeter east"),
    wall(16000, -16000, 0, 17000, -11500, 5500, "east security wall south"),
    wall(-17000, 11500, 0, -16000, 16000, 5500, "mirror of east security wall south"),
    wall(16000, -8500, 0, 17000, -2500, 5500, "east security wall inner south"),
    wall(-17000, 2500, 0, -16000, 8500, 5500, "mirror of east security wall inner south"),
    wall(16000, 2500, 0, 17000, 8500, 5500, "east security wall inner north"),
    wall(-17000, -8500, 0, -16000, -2500, 5500, "mirror of east security wall inner north"),
    wall(16000, 11500, 0, 17000, 16000, 5500, "east security wall north"),
    wall(-17000, -16000, 0, -16000, -11500, 5500, "mirror of east security wall north"),
    wall(4500, 3000, 0, 6500, 5000, 8000, "vault column north-east"),
    wall(-6500, -5000, 0, -4500, -3000, 8000, "mirror of vault column north-east"),
    wall(4500, -5000, 0, 6500, -3000, 8000, "vault column south-east"),
    wall(-6500, 3000, 0, -4500, 5000, 8000, "mirror of vault column south-east"),
    wall(-1000, 5000, 0, 1000, 7000, 8000, "vault column north"),
    wall(-1000, -7000, 0, 1000, -5000, 8000, "mirror of vault column north"),
    wall(2500, 1200, 0, 3300, 2400, 2000, "ledger terminal north-east"),
    wall(-3300, -2400, 0, -2500, -1200, 2000, "mirror of ledger terminal north-east"),
    wall(8000, 12000, 0, 13000, 16000, 7500, "vault block north-east"),
    wall(-13000, -16000, 0, -8000, -12000, 7500, "mirror of vault block north-east"),
    wall(8000, -16000, 0, 13000, -12000, 7500, "vault block south-east"),
    wall(-13000, 12000, 0, -8000, 16000, 7500, "mirror of vault block south-east"),
    wall(-2000, 12500, 0, 2000, 16000, 7000, "archive tower north"),
    wall(-2000, -16000, 0, 2000, -12500, 7000, "mirror of archive tower north"),
    wall(9000, 3500, 0, 11000, 5000, 2200, "coin counter north-east"),
    wall(-11000, -5000, 0, -9000, -3500, 2200, "mirror of coin counter north-east"),
    wall(9000, -5000, 0, 11000, -3500, 2200, "coin counter south-east"),
    wall(-11000, 3500, 0, -9000, 5000, 2200, "mirror of coin counter south-east"),
    wall(5000, 11200, 0, 6200, 12000, 2000, "bond press north"),
    wall(-6200, -12000, 0, -5000, -11200, 2000, "mirror of bond press north"),
    wall(-5500, 7800, 0, -4300, 8600, 2000, "bond press north-west"),
    wall(4300, -8600, 0, 5500, -7800, 2000, "mirror of bond press north-west"),
    wall(12500, 5500, 0, 14000, 7000, 2400, "ledger shelf north"),
    wall(-14000, -7000, 0, -12500, -5500, 2400, "mirror of ledger shelf north"),
    wall(12500, -7000, 0, 14000, -5500, 2400, "ledger shelf south"),
    wall(-14000, 5500, 0, -12500, 7000, 2400, "mirror of ledger shelf south"),
    wall(19500, 7000, 0, 21000, 8500, 3000, "conduit housing north"),
    wall(-21000, -8500, 0, -19500, -7000, 3000, "mirror of conduit housing north"),
    wall(19500, -8500, 0, 21000, -7000, 3000, "conduit housing south"),
    wall(-21000, 7000, 0, -19500, 8500, 3000, "mirror of conduit housing south"),
];
#[rustfmt::skip]
const DEBT_CITADEL_ROUTE: [(i32, i32); 6] = [
    (-19000, 0), (-7500, 0), (-7500, 10000), (7500, 10000), (7500, 0), (19000, 0),
];
#[rustfmt::skip]
const DEBT_CITADEL_HAZARDS: [Hazard; 2] = [
    hazard(HazardKind::Shredder, -1500, 7600, 0, 1500, 9000, 600, 25, 12, "ledger shredder grate"),
    hazard(HazardKind::Shredder, -1500, -9000, 0, 1500, -7600, 600, 25, 12, "mirror of ledger shredder grate"),
];
#[rustfmt::skip]
const DEBT_CITADEL_LANE_NORTH: [(i32, i32); 6] = [
    (-19000, 3000), (-18500, 3000), (-18500, 10000), (18500, 10000), (18500, 3000),
    (19000, 3000),
];
#[rustfmt::skip]
const DEBT_CITADEL_LANE_SOUTH: [(i32, i32); 6] = [
    (-19000, -3000), (-18500, -3000), (-18500, -10000), (18500, -10000), (18500, -3000),
    (19000, -3000),
];
#[rustfmt::skip]
const DEBT_CITADEL_LANE_MID: [(i32, i32); 2] = [
    (-19000, 0), (19000, 0),
];

/// The four first-release arenas, indexed by map id.
#[rustfmt::skip]
pub static ARENAS: [Arena; 4] = [
    Arena {
        id: 0,
        slug: "nyaagyu-estate",
        name: "Nyaagyu Estate",
        bounds: Bounds { min_x: -22000, min_y: -16000, max_x: 22000, max_y: 16000 },
        walls: &ESTATE_WALLS,
        team_spawns: [
            [
                spawn(-19500, -5000, 0), spawn(-19500, -3000, 0), spawn(-19500, -1000, 0),
                spawn(-19500, 1000, 0), spawn(-19500, 3000, 0), spawn(-19500, 5000, 0),
            ],
            [
                spawn(19500, 5000, 32768), spawn(19500, 3000, 32768), spawn(19500, 1000, 32768),
                spawn(19500, -1000, 32768), spawn(19500, -3000, 32768), spawn(19500, -5000, 32768),
            ],
        ],
        ffa_spawns: [
            spawn(-18500, -12500, 8192), spawn(18500, 12500, 40960),
            spawn(-18500, 12500, 57344), spawn(18500, -12500, 24576),
            spawn(0, 14500, 49152), spawn(0, -14500, 16384),
            spawn(-10500, 0, 0), spawn(10500, 0, 32768),
            spawn(-4000, -5500, 8192), spawn(4000, 5500, 40960),
            spawn(-11000, -13500, 8192), spawn(11000, 13500, 40960),
        ],
        control: ControlPoint { x: 0, y: 0, radius: 4000 },
        route: &ESTATE_ROUTE,
        checkpoints: [16000, 32000, 40000],
        hazards: &ESTATE_HAZARDS,
        lanes: [
            Lane { name: "north", points: &ESTATE_LANE_NORTH },
            Lane { name: "south", points: &ESTATE_LANE_SOUTH },
            Lane { name: "mid", points: &ESTATE_LANE_MID },
        ],
    },
    Arena {
        id: 1,
        slug: "lantern-ward",
        name: "Lantern Ward",
        bounds: Bounds { min_x: -23000, min_y: -14000, max_x: 23000, max_y: 14000 },
        walls: &LANTERN_WARD_WALLS,
        team_spawns: [
            [
                spawn(-21000, -5000, 0), spawn(-21000, -3000, 0), spawn(-21000, -1000, 0),
                spawn(-21000, 1000, 0), spawn(-21000, 3000, 0), spawn(-21000, 5000, 0),
            ],
            [
                spawn(21000, 5000, 32768), spawn(21000, 3000, 32768), spawn(21000, 1000, 32768),
                spawn(21000, -1000, 32768), spawn(21000, -3000, 32768), spawn(21000, -5000, 32768),
            ],
        ],
        ffa_spawns: [
            spawn(-21000, -12000, 8192), spawn(21000, 12000, 40960),
            spawn(-21000, 12000, 57344), spawn(21000, -12000, 24576),
            spawn(-9000, 8500, 0), spawn(9000, -8500, 32768),
            spawn(-8500, 0, 0), spawn(8500, 0, 32768),
            spawn(1250, -12500, 16384), spawn(-1250, 12500, 49152),
            spawn(-16000, -8500, 8192), spawn(16000, 8500, 40960),
        ],
        control: ControlPoint { x: 0, y: 0, radius: 3500 },
        route: &LANTERN_WARD_ROUTE,
        checkpoints: [22000, 35000, 43500],
        hazards: &LANTERN_WARD_HAZARDS,
        lanes: [
            Lane { name: "north", points: &LANTERN_WARD_LANE_NORTH },
            Lane { name: "south", points: &LANTERN_WARD_LANE_SOUTH },
            Lane { name: "mid", points: &LANTERN_WARD_LANE_MID },
        ],
    },
    Arena {
        id: 2,
        slug: "silk-foundry",
        name: "Silk Foundry",
        bounds: Bounds { min_x: -20000, min_y: -18000, max_x: 20000, max_y: 18000 },
        walls: &SILK_FOUNDRY_WALLS,
        team_spawns: [
            [
                spawn(-18000, -5000, 0), spawn(-18000, -3000, 0), spawn(-18000, -1000, 0),
                spawn(-18000, 1000, 0), spawn(-18000, 3000, 0), spawn(-18000, 5000, 0),
            ],
            [
                spawn(18000, 5000, 32768), spawn(18000, 3000, 32768), spawn(18000, 1000, 32768),
                spawn(18000, -1000, 32768), spawn(18000, -3000, 32768), spawn(18000, -5000, 32768),
            ],
        ],
        ffa_spawns: [
            spawn(-17500, -15500, 8192), spawn(17500, 15500, 40960),
            spawn(-17500, 15500, 57344), spawn(17500, -15500, 24576),
            spawn(-7000, 13000, 57344), spawn(7000, -13000, 24576),
            spawn(-10000, 0, 0), spawn(10000, 0, 32768),
            spawn(-3000, -13000, 16384), spawn(3000, 13000, 49152),
            spawn(-11000, -9000, 8192), spawn(11000, 9000, 40960),
        ],
        control: ControlPoint { x: 0, y: 0, radius: 3500 },
        route: &SILK_FOUNDRY_ROUTE,
        checkpoints: [18750, 32750, 51300],
        hazards: &SILK_FOUNDRY_HAZARDS,
        lanes: [
            Lane { name: "north", points: &SILK_FOUNDRY_LANE_NORTH },
            Lane { name: "south", points: &SILK_FOUNDRY_LANE_SOUTH },
            Lane { name: "mid", points: &SILK_FOUNDRY_LANE_MID },
        ],
    },
    Arena {
        id: 3,
        slug: "debt-citadel",
        name: "Debt Citadel",
        bounds: Bounds { min_x: -23000, min_y: -16000, max_x: 23000, max_y: 16000 },
        walls: &DEBT_CITADEL_WALLS,
        team_spawns: [
            [
                spawn(-20000, -5000, 0), spawn(-20000, -3000, 0), spawn(-20000, -1000, 0),
                spawn(-20000, 1000, 0), spawn(-20000, 3000, 0), spawn(-20000, 5000, 0),
            ],
            [
                spawn(20000, 5000, 32768), spawn(20000, 3000, 32768), spawn(20000, 1000, 32768),
                spawn(20000, -1000, 32768), spawn(20000, -3000, 32768), spawn(20000, -5000, 32768),
            ],
        ],
        ffa_spawns: [
            spawn(-20000, -12500, 8192), spawn(20000, 12500, 40960),
            spawn(-20000, 12500, 57344), spawn(20000, -12500, 24576),
            spawn(-5500, 13800, 57344), spawn(5500, -13800, 24576),
            spawn(-9500, 0, 0), spawn(9500, 0, 32768),
            spawn(-14000, -9000, 8192), spawn(14000, 9000, 40960),
            spawn(-4000, -13800, 16384), spawn(4000, 13800, 49152),
        ],
        control: ControlPoint { x: 0, y: 0, radius: 4500 },
        route: &DEBT_CITADEL_ROUTE,
        checkpoints: [21500, 36500, 46500],
        hazards: &DEBT_CITADEL_HAZARDS,
        lanes: [
            Lane { name: "north", points: &DEBT_CITADEL_LANE_NORTH },
            Lane { name: "south", points: &DEBT_CITADEL_LANE_SOUTH },
            Lane { name: "mid", points: &DEBT_CITADEL_LANE_MID },
        ],
    },
];
