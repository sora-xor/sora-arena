//! Integer geometry for bot decisions. Where a function mirrors a kernel rule
//! it names that rule, and the crate's tests compare each mirror with the real
//! kernel, so a rules change that moves one fails loudly instead of silently
//! steering bots into walls.
use arena_core::{
    catalog,
    math::{self, Aabb, Vec3},
    simulation::{EntityKind, HEIGHT, RADIUS, World},
};

/// Horizontal distance in millimetres, rounded down.
pub fn distance(a: Vec3, b: Vec3) -> i32 {
    // Arena coordinates lie within ±24,000 mm, so the root fits an i32.
    (a.horizontal_distance_squared(b) as u64).isqrt() as i32
}

/// The yaw whose kernel direction `math::direction(yaw, 0)` points most nearly
/// along `(dx, dy)`. The direction turns monotonically within each quarter
/// turn, so a binary search on the sign of the cross product finds it.
pub fn yaw_toward(dx: i32, dy: i32) -> u16 {
    if dx == 0 && dy == 0 {
        return 0;
    }
    let quarter: u32 = if dx > 0 && dy >= 0 {
        0
    } else if dx <= 0 && dy > 0 {
        1
    } else if dx < 0 && dy <= 0 {
        2
    } else {
        3
    };
    // Positive while the target lies counter-clockwise of the yaw.
    let cross = |yaw: u32| {
        let d = math::direction(yaw as u16, 0);
        i64::from(d.x) * i64::from(dy) - i64::from(d.y) * i64::from(dx)
    };
    let base = quarter * 16384;
    let (mut low, mut high) = (base, base + 16384);
    while low < high {
        let mid = (low + high) / 2;
        if cross(mid) <= 0 {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    let best = if low > base && cross(low - 1).abs() < cross(low).abs() {
        low - 1
    } else {
        low
    };
    // A full turn (65536) is yaw 0.
    best as u16
}

/// The kernel pitch toward a point `dz` above the eye at `horizontal`
/// millimetres, searched the same way against `math::direction(0, pitch)`.
pub fn pitch_toward(horizontal: i32, dz: i32) -> i16 {
    if horizontal <= 0 && dz == 0 {
        return 0;
    }
    // Search the offset pitch + 16384 over 0..=32768, where the cross product
    // falls monotonically.
    let cross = |offset: i32| {
        let d = math::direction(0, (offset - 16384) as i16);
        i64::from(d.x) * i64::from(dz) - i64::from(d.z) * i64::from(horizontal.max(0))
    };
    let (mut low, mut high) = (0, 32768);
    while low < high {
        let mid = (low + high) / 2;
        if cross(mid) <= 0 {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    let best = if low > 0 && cross(low - 1).abs() < cross(low).abs() {
        low - 1
    } else {
        low
    };
    (best - 16384) as i16
}

/// The signed angle from `from` to `to` in 16-bit turns, -32768..32767.
pub fn turn(from: u16, to: u16) -> i32 {
    i32::from(to.wrapping_sub(from) as i16)
}

/// `from` turned toward `to` by at most `max` 16-bit turns.
pub fn slew(from: u16, to: u16, max: i32) -> u16 {
    from.wrapping_add_signed(turn(from, to).clamp(-max, max) as i16)
}

/// `(x, y)` offset of `length` millimetres along `yaw`, as the kernel scales a
/// dash, a barricade reach or a thrown pot.
pub fn ahead(yaw: u16, length: i32) -> (i32, i32) {
    let v = math::scale_q15(math::direction(yaw, 0), length);
    (v.x, v.y)
}

/// Movement axes that walk along world heading `heading` while the view faces
/// `yaw`: the kernel moves along `forward * move_x + right * move_y`.
pub fn move_axes(yaw: u16, heading: u16) -> (i16, i16) {
    let d = math::direction(heading.wrapping_sub(yaw), 0);
    ((d.x * 127 / 32767) as i16, (d.y * 127 / 32767) as i16)
}

/// The kernel player phase's horizontal step (`World::step`): the class speed,
/// halved while guarding, along the input axes with L1 normalization.
pub fn walk_step(class: u8, guarding: bool, yaw: u16, move_x: i16, move_y: i16) -> (i32, i32) {
    let speed = catalog::CLASSES[usize::from(class)].move_mm_tick / if guarding { 2 } else { 1 };
    let forward = math::direction(yaw, 0);
    let right = math::direction(yaw.wrapping_add(16384), 0);
    let norm = (i32::from(move_x).abs() + i32::from(move_y).abs()).max(127);
    let axis = |f: i32, r: i32| {
        ((i64::from(f) * i64::from(move_x) + i64::from(r) * i64::from(move_y)) * i64::from(speed)
            / (32767 * i64::from(norm))) as i32
    };
    (axis(forward.x, right.x), axis(forward.y, right.y))
}

/// Static walls and live barricades: everything that stops movement, rays and
/// line of sight (§5.4).
pub fn solids(world: &World) -> impl Iterator<Item = Aabb> + '_ {
    world.arena().walls.iter().map(|w| w.aabb).chain(
        world
            .entities
            .iter()
            .filter(|e| e.kind == EntityKind::Barricade)
            .map(|e| e.bounds()),
    )
}

/// Whether the segment's bounding box reaches the closed box `b`. A cheap
/// rejection before the exact Q20 intersection.
fn near(b: Aabb, from: Vec3, to: Vec3) -> bool {
    from.x.min(to.x) <= b.max.x
        && from.x.max(to.x) >= b.min.x
        && from.y.min(to.y) <= b.max.y
        && from.y.max(to.y) >= b.min.y
        && from.z.min(to.z) <= b.max.z
        && from.z.max(to.z) >= b.min.z
}

/// Whether the segment meets the closed box, by the kernel's own intersection.
pub fn hits(b: Aabb, from: Vec3, to: Vec3) -> bool {
    near(b, from, to) && b.intersect(from, to).is_some()
}

/// Line of sight through walls and live barricades, as the kernel's `blocked`
/// tests rays, blasts and marks.
pub fn sight_clear(world: &World, from: Vec3, to: Vec3) -> bool {
    solids(world).all(|s| !hits(s, from, to))
}

/// Whether the kernel's collision-safe motion (`World::safe_motion`) moves a
/// player standing at `from` by exactly `(dx, dy)`: no clamp to the arena
/// bounds, and no wall or barricade on either axis-separated leg.
pub fn motion_clear(world: &World, from: Vec3, dx: i32, dy: i32) -> bool {
    let b = world.arena().bounds;
    let (x, y) = (from.x + dx, from.y + dy);
    if x < b.min_x + RADIUS || x > b.max_x - RADIUS || y < b.min_y + RADIUS || y > b.max_y - RADIUS
    {
        return false;
    }
    let lift = HEIGHT / 2;
    let start = Vec3::new(from.x, from.y, from.z + lift);
    let across = Vec3::new(x, from.y, from.z + lift);
    let end = Vec3::new(x, y, from.z + lift);
    // An axis with no motion cannot be clipped: the kernel keeps the same
    // coordinate whether or not it tests it.
    solids(world).all(|s| {
        let s = s.expanded(RADIUS, lift);
        (dx == 0 || (!s.contains(across) && !hits(s, start, across)))
            && (dy == 0 || (!s.contains(end) && !hits(s, across, end)))
    })
}

/// Whether `at` lies over the floor rectangle of one of the arena's hazard
/// volumes (the kernel's closed test, `hazards::inside`, at any height): a
/// player in the air over a hazard lands in it.
pub fn in_hazard(world: &World, at: Vec3) -> bool {
    world.arena().hazards.iter().any(|h| {
        let v = h.volume;
        (v.min.x..=v.max.x).contains(&at.x) && (v.min.y..=v.max.y).contains(&at.y)
    })
}

/// A player-sized body standing at `position`, grown by `extra` horizontally.
pub fn body(position: Vec3, extra: i32) -> Aabb {
    let r = RADIUS + extra;
    Aabb {
        min: Vec3::new(position.x - r, position.y - r, position.z),
        max: Vec3::new(position.x + r, position.y + r, position.z + HEIGHT),
    }
}

/// Whether the Karakuri in `slot`, standing at `position` and facing `yaw`,
/// may place its barricade (§6.5, `World::barricade_placement`). The bot
/// judges before the step, when other players may still move up to 100 mm, so
/// their bodies count 120 mm wider. The kernel has the final word; a refused
/// placement changes nothing.
pub fn barricade_fits(world: &World, slot: usize, position: Vec3, yaw: u16) -> bool {
    let facing = math::direction(yaw, 0);
    let (reach_x, reach_y) = ahead(yaw, 1500);
    let centre = Vec3::new(position.x + reach_x, position.y + reach_y, 0);
    let (half_x, half_y) = if facing.x.abs() >= facing.y.abs() {
        (200, 1200)
    } else {
        (1200, 200)
    };
    let bounds = Aabb {
        min: Vec3::new(centre.x - half_x, centre.y - half_y, 0),
        max: Vec3::new(centre.x + half_x, centre.y + half_y, 2000),
    };
    let own = world
        .entities
        .iter()
        .find(|e| e.owner == slot && e.kind == EntityKind::Barricade)
        .map(|e| e.id);
    let arena = world.arena();
    let inside = arena.bounds.contains(bounds.min.x, bounds.min.y)
        && arena.bounds.contains(bounds.max.x, bounds.max.y);
    let walls_clear = !arena.walls.iter().any(|w| w.aabb.overlaps(bounds))
        && !world.entities.iter().any(|e| {
            e.kind == EntityKind::Barricade && Some(e.id) != own && e.bounds().overlaps(bounds)
        });
    let bodies_clear = !world.players.iter().enumerate().any(|(other, p)| {
        p.alive
            && if other == slot {
                body(position, 0)
            } else {
                body(p.position, 120)
            }
            .overlaps(bounds)
    });
    let spawns_clear = !arena
        .spawns()
        .any(|spawn| body(spawn.position(), 500).overlaps(bounds));
    let hazards_clear = !arena.hazards.iter().any(|h| h.volume.overlaps(bounds));
    let lift = Vec3::new(0, 0, 800);
    let reachable = arena
        .walls
        .iter()
        .map(|w| w.aabb)
        .chain(
            world
                .entities
                .iter()
                .filter(|e| e.kind == EntityKind::Barricade && Some(e.id) != own)
                .map(|e| e.bounds()),
        )
        .all(|s| !hits(s, position.offset(lift), centre.offset(lift)));
    inside && walls_clear && bodies_clear && spawns_clear && hazards_clear && reachable
}
