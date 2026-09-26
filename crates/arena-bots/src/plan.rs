//! Team plans: where a bot holds for its objective (§8), which lane it travels
//! on a long trip, and what it takes at respawn (§10).
use crate::{
    geometry,
    nav::{self, Nav, Point},
};
use arena_core::{
    catalog::{AttackKind, WEAPONS},
    maps::Arena,
    simulation::{Mode, Player, World},
};

/// A slot's rank among its team in slot order, the kernel's team spawn rank.
pub fn rank(world: &World, slot: usize) -> usize {
    let team = world.players[slot].team;
    world.players[..slot]
        .iter()
        .filter(|p| p.team == team)
        .count()
}

/// Payload formation by team rank: (along the route, across it) from the
/// payload. The escort stays well inside the 3000 mm push radius; the blockers
/// stand ahead of it, still close enough to contest.
const ESCORT: [(i32, i32); 6] = [
    (900, 0),
    (400, 1300),
    (400, -1300),
    (-300, 2000),
    (-300, -2000),
    (-900, 0),
];
const BLOCKERS: [(i32, i32); 6] = [
    (2200, 0),
    (1800, 1000),
    (1800, -1000),
    (1200, 1500),
    (1200, -1500),
    (2600, 300),
];

/// The unit axis of the payload route at `distance` (segments are
/// axis-aligned).
fn route_axis(arena: &Arena, distance: i32) -> (i32, i32) {
    let end = arena.route_length();
    let at = distance.clamp(0, end - 1);
    let (a, b) = (arena.route_point(at), arena.route_point(at + 1));
    ((b.x - a.x).signum(), (b.y - a.y).signum())
}

/// The mode's objective centre and the radius that counts, for target
/// priority: the Control circle, or the payload and its push radius.
pub fn objective(world: &World) -> Option<(Point, i32)> {
    let arena = world.arena();
    match world.config.mode {
        Mode::Control => Some(((arena.control.x, arena.control.y), arena.control.radius)),
        Mode::Payload => {
            let at = arena.route_point(world.payload_progress);
            Some(((at.x, at.y), arena_core::simulation::PAYLOAD_PUSH_RADIUS))
        }
        Mode::FreeForAll | Mode::Melee => None,
    }
}

/// Where a team-mode bot holds for its objective, or `None` in free-for-all
/// and Melee, where bots hunt. Control spreads the team on a ring inside the
/// circle, with Teppō on overwatch at the team's own edge. Payload escorts
/// stand around the payload and blockers just ahead of it.
pub fn post(world: &World, slot: usize, nav: &Nav) -> Option<Point> {
    let me = &world.players[slot];
    let arena = world.arena();
    let rank = rank(world, slot) % 6;
    let point = match world.config.mode {
        Mode::Control => {
            let c = arena.control;
            // Team 0 spawns at negative x, team 1 at positive x.
            let home = if me.team == 0 { -1 } else { 1 };
            if me.class == 2 {
                (
                    c.x + home * (c.radius + 3500),
                    c.y + [-2500, 2500, 0, -1200, 1200, 0][rank],
                )
            } else {
                let facing = if me.team == 0 { 32768u16 } else { 0 };
                let angle = facing.wrapping_add(rank as u16 * 10923);
                let (dx, dy) = geometry::ahead(angle, c.radius * [1, 2, 2, 1, 3, 2][rank] / 4);
                (c.x + dx, c.y + dy)
            }
        }
        Mode::Payload => {
            let (along, across) = if me.team == 0 {
                // A Kusushi escorts from behind.
                if me.class == 5 {
                    (-1200, ESCORT[rank].1)
                } else {
                    ESCORT[rank]
                }
            } else {
                BLOCKERS[rank]
            };
            let at = (world.payload_progress + along).clamp(0, arena.route_length());
            let p = arena.route_point(at);
            let (ax, ay) = route_axis(arena, at);
            (p.x - ay * across, p.y + ax * across)
        }
        Mode::FreeForAll | Mode::Melee => return None,
    };
    Some(nav.standable_near(point))
}

/// The next point of the bot's lane toward `goal` on a long trip, or `None`
/// once it is near or the lane does not lead there. Team modes spread their
/// approach over the arena's `north`, `south` and `mid` lanes by rank; lane
/// corridors are clear of walls and hazards (§7.2).
pub fn lane_waypoint(
    world: &World,
    slot: usize,
    nav: &Nav,
    from: Point,
    goal: Point,
) -> Option<Point> {
    if !world.config.mode.team() || nav::length(from, goal) < 9000 {
        return None;
    }
    let lane = world.arena().lanes[rank(world, slot) % 3].points;
    // Lanes run from team 0's base to team 1's.
    let order: Vec<Point> = if world.players[slot].team == 0 {
        lane.to_vec()
    } else {
        lane.iter().rev().copied().collect()
    };
    let nearest = |p: Point| {
        (0..order.len())
            .min_by_key(|&k| (nav::length(order[k], p), k))
            .unwrap_or(0)
    };
    let (entry, exit) = (nearest(from), nearest(goal));
    // Lane corridors are 450 mm wide each side; paths keep a wider margin.
    (entry < exit).then(|| nav.standable_near(order[entry + 1]))
}

/// Roles a team wants filled for its mode and side, most needed first.
fn roles(mode: Mode, team: u8) -> &'static [u8] {
    match (mode, team) {
        // Kusushi, Karakuri, Samurai, Hanabi.
        (Mode::Control, _) => &[5, 4, 0, 3],
        // Attackers: Kusushi, Hanabi, Samurai, Shinobi.
        (Mode::Payload, 0) => &[5, 3, 0, 1],
        // Defenders: Karakuri, Teppō, Hanabi, Kusushi.
        (Mode::Payload, _) => &[4, 2, 3, 5],
        (Mode::FreeForAll | Mode::Melee, _) => &[],
    }
}

/// The class a player will respawn as: its pending request, else its class.
fn next_class(p: &Player) -> u8 {
    p.pending_loadout.map_or(p.class, |(class, _)| class)
}

/// A dead bot's respawn request `(class, loadout index)` (§10), or `None` when
/// it will already respawn with what it wants.
///
/// Adapting bots fill a missing team role: of the teammates sharing a
/// duplicated class, only the highest slot switches, and never one whose
/// admitted special belongs to its class. In free-for-all an adapting bot that
/// keeps losing tries its class's other standard weapon every third death.
/// Every bot takes its admitted special when its class allows it, and Melee
/// mode keeps to melee weapons.
pub fn loadout(world: &World, slot: usize, adapts: bool) -> Option<(u8, u8)> {
    let me = &world.players[slot];
    // The choice depends only on what this bot fought with and on its
    // teammates' next classes, never on its own pending request, so it is
    // stable over every tick of the respawn wait.
    let mut class = me.class;
    let class_of = |s: usize| {
        if s == slot {
            me.class
        } else {
            next_class(&world.players[s])
        }
    };
    if adapts && world.config.mode.team() && me.admitted_special != Some(12 + me.class) {
        let team: Vec<usize> = (0..world.players.len())
            .filter(|&s| world.players[s].team == me.team && !world.exhausted(s))
            .collect();
        let count = |c: u8| team.iter().filter(|&&s| class_of(s) == c).count();
        let switcher = team.iter().rev().find(|&&s| class_of(s) == me.class) == Some(&slot);
        if count(me.class) >= 2
            && switcher
            && let Some(&missing) = roles(world.config.mode, me.team)
                .iter()
                .find(|&&c| count(c) == 0)
        {
            class = missing;
        }
    }
    let melee_style = WEAPONS[usize::from(me.weapon)].kind == AttackKind::Melee;
    let special = me.admitted_special == Some(12 + class);
    let account = &world.accounts[slot];
    let losing = adapts
        && me.admitted_special.is_none()
        && world.config.mode == Mode::FreeForAll
        && account.deaths >= account.kills + 3
        && account.deaths.is_multiple_of(3);
    let index: u8 = if world.config.mode == Mode::Melee {
        if special && WEAPONS[usize::from(12 + class)].kind == AttackKind::Melee {
            2
        } else {
            1
        }
    } else if special {
        2
    } else if class != me.class {
        // A new role starts with its natural weapon: the katana for a
        // Samurai, otherwise the class's ranged weapon.
        u8::from(class == 0)
    } else {
        u8::from(melee_style != losing)
    };
    let weapon = match index {
        0 => class * 2 + 1,
        1 => class * 2,
        _ => 12 + class,
    };
    let next = me.pending_loadout.unwrap_or((me.class, me.weapon));
    ((class, weapon) != next).then_some((class, index))
}
