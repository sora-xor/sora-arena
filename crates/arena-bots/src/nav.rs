//! Static navigation for one arena: a visibility graph over the corners of its
//! walls and hazards, grown by a walking player's clearance and built once per
//! arena. Live barricades are left to local steering, which tests every step
//! against the kernel's own collision before taking it.
use crate::geometry;
use arena_core::{
    maps::{ARENAS, Arena},
    math::{Aabb, Vec3},
    simulation::RADIUS,
};
use std::{cmp::Reverse, collections::BinaryHeap, sync::OnceLock};

/// A floor point in millimetres.
pub type Point = (i32, i32);

/// Paths keep a body 120 mm clear of wall faces.
const WALL_CLEARANCE: i32 = RADIUS + 120;
/// Graph corners stand farther out, so a path along a face keeps its margin.
const CORNER_CLEARANCE: i32 = RADIUS + 260;
/// Paths keep the feet 150 mm outside hazard volumes; corners stand 300 mm out.
const HAZARD_CLEARANCE: i32 = 150;
const HAZARD_CORNER: i32 = 300;

/// One arena's planning obstacles and corner graph.
pub struct Nav {
    /// Flat boxes (z -1..=1): walls grown by `WALL_CLEARANCE`, hazards by
    /// `HAZARD_CLEARANCE`.
    obstacles: Vec<Aabb>,
    /// The rectangle a planned body centre stays inside.
    min: Point,
    max: Point,
    nodes: Vec<Point>,
    /// Straight, clear connections between nodes with their lengths.
    edges: Vec<Vec<(usize, u32)>>,
}

fn flat(b: Aabb, grow: i32) -> Aabb {
    Aabb {
        min: Vec3::new(b.min.x - grow, b.min.y - grow, -1),
        max: Vec3::new(b.max.x + grow, b.max.y + grow, 1),
    }
}

fn floor(p: Point) -> Vec3 {
    Vec3::new(p.0, p.1, 0)
}

/// Floor distance between two points, rounded down.
pub fn length(a: Point, b: Point) -> u32 {
    geometry::distance(floor(a), floor(b)) as u32
}

impl Nav {
    fn build(arena: &Arena) -> Self {
        let b = arena.bounds;
        let mut nav = Self {
            obstacles: arena
                .walls
                .iter()
                .map(|w| flat(w.aabb, WALL_CLEARANCE))
                .chain(
                    arena
                        .hazards
                        .iter()
                        .map(|h| flat(h.volume, HAZARD_CLEARANCE)),
                )
                .collect(),
            min: (b.min_x + WALL_CLEARANCE, b.min_y + WALL_CLEARANCE),
            max: (b.max_x - WALL_CLEARANCE, b.max_y - WALL_CLEARANCE),
            nodes: Vec::new(),
            edges: Vec::new(),
        };
        let corners = arena
            .walls
            .iter()
            .map(|w| (w.aabb, CORNER_CLEARANCE))
            .chain(arena.hazards.iter().map(|h| (h.volume, HAZARD_CORNER)));
        for (b, grow) in corners {
            for p in [
                (b.min.x - grow, b.min.y - grow),
                (b.max.x + grow, b.min.y - grow),
                (b.min.x - grow, b.max.y + grow),
                (b.max.x + grow, b.max.y + grow),
            ] {
                if nav.standable(p) && !nav.nodes.contains(&p) {
                    nav.nodes.push(p);
                }
            }
        }
        let count = nav.nodes.len();
        nav.edges = vec![Vec::new(); count];
        for i in 0..count {
            for j in i + 1..count {
                let (a, b) = (nav.nodes[i], nav.nodes[j]);
                if nav.clear(a, b) {
                    let d = length(a, b);
                    nav.edges[i].push((j, d));
                    nav.edges[j].push((i, d));
                }
            }
        }
        nav
    }

    /// The graph's corner points, in build order.
    pub fn nodes(&self) -> &[Point] {
        &self.nodes
    }

    /// Whether a body centred at `p` stands clear of every planning obstacle.
    pub fn standable(&self, p: Point) -> bool {
        (self.min.0..=self.max.0).contains(&p.0)
            && (self.min.1..=self.max.1).contains(&p.1)
            && !self.obstacles.iter().any(|o| o.contains(floor(p)))
    }

    /// Whether a body can walk straight from `a` to `b` with its margin.
    pub fn clear(&self, a: Point, b: Point) -> bool {
        let (a, b) = (floor(a), floor(b));
        self.obstacles.iter().all(|o| !geometry::hits(*o, a, b))
    }

    /// `p` when a body can stand there, else the first standable point on rings
    /// 250 mm apart around it, 16 directions per ring in a fixed order.
    pub fn standable_near(&self, p: Point) -> Point {
        if self.standable(p) {
            return p;
        }
        for ring in 1..=40 {
            for k in 0..16u16 {
                let (dx, dy) = geometry::ahead(k * 4096, ring * 250);
                let q = (p.0 + dx, p.1 + dy);
                if self.standable(q) {
                    return q;
                }
            }
        }
        p
    }

    /// Waypoints from `from` toward `to`: the shortest graph route, ending at
    /// `to` when some reached corner sees it, otherwise at the reached corner
    /// nearest to it. Empty when `from` sees no corner at all; local steering
    /// then works the body free first.
    pub fn path(&self, from: Point, to: Point) -> Vec<Point> {
        if self.clear(from, to) {
            return vec![to];
        }
        let count = self.nodes.len();
        let mut dist = vec![u32::MAX; count];
        let mut previous = vec![usize::MAX; count];
        let mut heap = BinaryHeap::new();
        for (i, &node) in self.nodes.iter().enumerate() {
            if self.clear(from, node) {
                dist[i] = length(from, node);
                heap.push(Reverse((dist[i], i)));
            }
        }
        while let Some(Reverse((d, i))) = heap.pop() {
            if d > dist[i] {
                continue;
            }
            for &(j, w) in &self.edges[i] {
                if d + w < dist[j] {
                    dist[j] = d + w;
                    previous[j] = i;
                    heap.push(Reverse((d + w, j)));
                }
            }
        }
        // Ties go to the lower node index, so the route is canonical.
        let mut exit: Option<(u32, usize)> = None;
        let mut near: Option<(u32, usize)> = None;
        for (i, &node) in self.nodes.iter().enumerate() {
            if dist[i] == u32::MAX {
                continue;
            }
            let rest = length(node, to);
            if near.is_none_or(|(best, _)| rest < best) {
                near = Some((rest, i));
            }
            if exit.is_none_or(|(best, _)| dist[i] + rest < best) && self.clear(node, to) {
                exit = Some((dist[i] + rest, i));
            }
        }
        let (mut path, mut i) = match (exit, near) {
            (Some((_, i)), _) => (vec![to], i),
            (None, Some((_, i))) => (Vec::new(), i),
            (None, None) => return Vec::new(),
        };
        loop {
            path.push(self.nodes[i]);
            if previous[i] == usize::MAX {
                break;
            }
            i = previous[i];
        }
        path.reverse();
        path
    }
}

/// The navigation graph of arena `map` (0-3), built on first use.
pub fn get(map: u8) -> &'static Nav {
    static NAVS: [OnceLock<Nav>; 4] = [const { OnceLock::new() }; 4];
    NAVS[usize::from(map)].get_or_init(|| Nav::build(&ARENAS[usize::from(map)]))
}
