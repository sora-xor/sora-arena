//! One bot's decision for one tick: what it notices, how it defends, which
//! class ability it uses, how it attacks or supports, and where it walks.
//! Every step it takes has been checked against the kernel's own collision, so
//! a bot never walks into a wall, barricade or the arena edge.
use crate::{
    Tier,
    geometry::{
        self, ahead, distance, in_hazard, motion_clear, move_axes, pitch_toward, sight_clear, slew,
        turn, walk_step, yaw_toward,
    },
    nav::{self, Nav, Point},
    plan,
};
use arena_core::{
    catalog::{AttackKind, CLASSES, WEAPONS, Weapon},
    math::{self, Vec3},
    simulation::{
        ABILITY, BLOCK, EYE_HEIGHT, Entity, EntityKind, Event, FIRE, Input, JUMP, LOADOUT, MELEE,
        Mode, Player, RADIUS, RELOAD, World,
    },
};

/// Aim error pattern in 1/256ths of the tier's current amplitude. The index
/// moves with each acquisition and every 20 ticks of tracking.
const AIM_PATTERN: [i32; 8] = [256, -192, 128, -256, 64, -160, 224, -96];
/// Bodies are aimed at 1000 mm above the feet; blasts at 900 mm.
const CHEST: i32 = 1000;
const CENTRE: i32 = 900;
/// How far the view may still be turning when an attack goes out.
const ATTACK_TOLERANCE: i32 = 500;
/// How closely the view must face for a mark or a thrown pot.
const ABILITY_TOLERANCE: i32 = 300;
/// Ticks a target stays engaged after it drops out of sight.
const MEMORY: u32 = 20;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Target {
    Player(usize),
    Decoy(u32),
}

/// The enemy this bot is dealing with, as it stands after the last step.
#[derive(Debug, Clone, Copy)]
struct Sighting {
    target: Target,
    feet: Vec3,
    /// Millimetres moved over the last tick.
    velocity: Vec3,
    distance: i32,
    visible: bool,
    /// In sight now or within `MEMORY` ticks: the fight goes on through a
    /// brief occlusion.
    recent: bool,
    protected: bool,
}

/// An enemy about to hit this bot with a ray it can guard or negate.
#[derive(Debug, Clone, Copy)]
struct Threat {
    attacker: usize,
    distance: i32,
    melee: bool,
    /// A blow already in reach, or fire aimed at this bot: worth a stance.
    imminent: bool,
    /// A heavy blow whose charge completes within three ticks.
    charging: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Motion {
    Hold,
    /// Walk the navigation graph to a point.
    Goal(Point),
    /// Walk straight at a point in the open.
    Direct(Point),
    Away(Vec3),
    /// Circle a point, switching sides on the tier's cadence.
    Strafe(Vec3),
}

/// This tick's intentions before the view turns and the feet are placed.
#[derive(Debug, Default)]
struct Act {
    /// Wanted view; `None` looks along the walking heading.
    aim: Option<(u16, i16)>,
    buttons: u32,
    /// Buttons that wait until the view is within `ABILITY_TOLERANCE` of
    /// `aim`, and those that wait until it faces `aim` exactly: a dash or a
    /// barricade was checked for clearance along that very yaw.
    aimed: u32,
    exact: u32,
    motion: Option<Motion>,
}

/// What a bot remembers between ticks. None of it is kernel state.
#[derive(Debug, Clone, Default)]
pub(crate) struct Memory {
    /// The input planned for a tick, returned again on a repeated call.
    planned: Option<(u32, Input)>,
    target: Option<Target>,
    /// Ticks the target has been in sight, kept through a brief occlusion:
    /// the reaction delay.
    seen: u16,
    /// When the target was last in sight.
    seen_tick: u32,
    /// Ticks spent aiming at the same target in sight: the aim settles.
    tracked: u16,
    acquisitions: u32,
    /// The last enemy that damaged this bot, and when.
    attacker: Option<(usize, u32)>,
    /// Melee threat episodes so far, whether one is active, and whether this
    /// bot answers the active one.
    threats: u32,
    threatened: bool,
    answering: bool,
    path: Vec<Point>,
    path_goal: Option<Point>,
    replanned: u32,
    /// Best distance to the current waypoint, and when it was reached.
    best: i32,
    best_tick: u32,
    /// Detour, strafe and flank side, and when strafing last switched it.
    side: bool,
    side_tick: u32,
    /// Every player's feet on the given tick, for velocities.
    previous: Option<(u32, Vec<Vec3>)>,
    /// Cover from the current threat, and when it was chosen.
    cover: Option<(Point, u32)>,
}

/// The input for `slot` on the next step.
pub(crate) fn think(memory: &mut Memory, world: &World, slot: usize, tier: &Tier) -> Input {
    if let Some((tick, input)) = memory.planned
        && tick == world.tick
    {
        return input;
    }
    let input = if world.players[slot].alive {
        Brain {
            world,
            slot,
            tier,
            memory: &mut *memory,
            nav: nav::get(world.config.map),
        }
        .decide()
    } else {
        forget(memory);
        respawn(world, slot, tier)
    };
    memory.previous = Some((
        world.tick,
        world.players.iter().map(|p| p.position).collect(),
    ));
    memory.planned = Some((world.tick, input));
    input
}

/// Death ends every engagement and route.
fn forget(memory: &mut Memory) {
    memory.target = None;
    memory.seen = 0;
    memory.tracked = 0;
    memory.threatened = false;
    memory.path.clear();
    memory.path_goal = None;
    memory.cover = None;
}

/// A dead bot asks for its next loadout once it wants a change; an exhausted
/// one only spectates.
fn respawn(world: &World, slot: usize, tier: &Tier) -> Input {
    if world.exhausted(slot) {
        return Input::default();
    }
    plan::loadout(world, slot, tier.adapts).map_or_else(Input::default, |(class, index)| Input {
        buttons: LOADOUT,
        move_x: i16::from(class),
        move_y: i16::from(index),
        ..Input::default()
    })
}

fn enemy(world: &World, a: usize, b: usize) -> bool {
    a != b && (!world.config.mode.team() || world.players[a].team != world.players[b].team)
}

/// The kernel's entity side test (`World::entity_enemy`).
fn entity_enemy(world: &World, slot: usize, e: &Entity) -> bool {
    if world.config.mode.team() {
        world.players[slot].team != e.team
    } else {
        slot != e.owner
    }
}

/// Whether a player at `from` facing `yaw` looks at `to` within the cone
/// whose half-angle tangent is `tan_tenths / 10`.
fn looks_at(yaw: u16, from: Vec3, to: Vec3, tan_tenths: i64) -> bool {
    let d = math::direction(yaw, 0);
    let (vx, vy) = (i64::from(to.x - from.x), i64::from(to.y - from.y));
    let dot = i64::from(d.x) * vx + i64::from(d.y) * vy;
    let cross = (i64::from(d.x) * vy - i64::from(d.y) * vx).abs();
    dot > 0 && cross * 10 <= dot * tan_tenths
}

/// Within about 35°: close enough for a melee swing or to notice a flanker.
fn facing(yaw: u16, from: Vec3, to: Vec3) -> bool {
    looks_at(yaw, from, to, 7)
}

/// The melee blow a player would strike with: its equipped melee weapon, else
/// its class melee weapon on the melee button.
fn strike_of(p: &Player) -> Weapon {
    let equipped = WEAPONS[usize::from(p.weapon)];
    if equipped.kind == AttackKind::Melee {
        equipped
    } else {
        WEAPONS[usize::from(p.class * 2)]
    }
}

/// Centre-to-centre horizontal distance at which a melee ray reliably meets a
/// body: its range plus the body radius and the 180 mm melee widening, less a
/// 150 mm margin for aim and motion (§5.3).
fn strike_reach(weapon: Weapon) -> i32 {
    weapon.range_mm + RADIUS + 180 - 150
}

/// The distance band a ranged weapon fights from.
fn band(weapon: u8) -> (i32, i32) {
    match weapon {
        1 => (4000, 20_000),
        3 => (3000, 12_000),
        5 => (10_000, 34_000),
        7 => (4500, 16_000),
        9 => (5000, 18_000),
        11 | 17 => (6000, 18_000),
        13 => (2500, 10_000),
        14 => (9000, 30_000),
        15 => (6500, 22_000),
        16 => (2500, 10_000),
        _ => (0, 2000),
    }
}

struct Brain<'a> {
    world: &'a World,
    slot: usize,
    tier: &'a Tier,
    memory: &'a mut Memory,
    nav: &'static Nav,
}

impl<'a> Brain<'a> {
    fn me(&self) -> &'a Player {
        &self.world.players[self.slot]
    }

    fn here(&self) -> Point {
        let p = self.me().position;
        (p.x, p.y)
    }

    fn decide(&mut self) -> Input {
        let sight = self.perceive();
        let threat = self.threat();
        let post = plan::post(self.world, self.slot, self.nav);
        let mut act = Act::default();
        if self.me().stance_ticks > 1 {
            // In stance: stand and keep facing the danger, since only frontal
            // hits are negated (§6.1).
            let face = threat
                .map(|t| self.world.players[t.attacker].position)
                .or(sight.map(|s| s.feet));
            act.aim = face.map(|f| self.aim_exact(f.offset(Vec3::new(0, 0, CHEST))));
            act.motion = Some(Motion::Hold);
        } else if !self.defend(threat, &mut act) {
            let claimed = self.me().ability_cooldown == 0 && self.ability(sight, post, &mut act);
            if !claimed {
                if let Some(s) = sight {
                    self.attack(&s, post, &mut act);
                }
                if act.buttons & (FIRE | MELEE) == 0 {
                    self.support(sight, &mut act);
                }
            }
            self.reload(sight, &mut act);
        }
        let motion = match act.motion {
            Some(motion) => motion,
            None => self.travel(sight, post),
        };
        self.finish(act, motion)
    }

    // ---- Perception ------------------------------------------------------

    /// Choose the enemy to deal with: the nearest in sight, preferring the one
    /// already engaged, the last attacker, the wounded and those on the
    /// objective. Enemies out of sight still guide hunting. Lower tiers also
    /// fall for decoys.
    fn perceive(&mut self) -> Option<Sighting> {
        let (world, slot) = (self.world, self.slot);
        let me = &world.players[slot];
        let eye = me.position.offset(Vec3::new(0, 0, EYE_HEIGHT));
        for e in &world.events {
            if let Event::Damage {
                attacker, victim, ..
            } = *e
                && victim == slot
                && attacker != slot
            {
                self.memory.attacker = Some((attacker, world.tick));
            }
        }
        let attacker = self
            .memory
            .attacker
            .filter(|&(_, at)| world.tick <= at + 180)
            .map(|(a, _)| a);
        let objective = plan::objective(world);
        let previous = self
            .memory
            .previous
            .as_ref()
            .filter(|(at, feet)| at + 1 == world.tick && feet.len() == world.players.len())
            .map(|(_, feet)| feet.clone());
        let current = self.memory.target;
        let mut best: Option<(i64, Sighting)> = None;
        let mut consider = |score: i64, s: Sighting| {
            if best.is_none_or(|(b, _)| score < b) {
                best = Some((score, s));
            }
        };
        for (other, p) in world.players.iter().enumerate() {
            if !p.alive || !enemy(world, slot, other) {
                continue;
            }
            let target = Target::Player(other);
            let d = distance(me.position, p.position);
            let visible = sight_clear(world, eye, p.position.offset(Vec3::new(0, 0, CHEST)));
            let protected = p.spawn_protection > 0;
            let wounded = CLASSES[usize::from(p.class)].health - p.health;
            let mut score = i64::from(d) - i64::from(wounded) * 20;
            if !visible {
                score += 20_000;
            }
            if protected {
                score += 30_000;
            }
            if current == Some(target) {
                score -= 3000;
            }
            if attacker == Some(other) {
                score -= 4000;
            }
            if let Some((centre, radius)) = objective
                && nav::length(centre, (p.position.x, p.position.y)) as i32 <= radius + 1000
            {
                score -= 2500;
            }
            let velocity = previous
                .as_ref()
                .map_or(Vec3::default(), |feet| p.position.delta(feet[other]));
            consider(
                score,
                Sighting {
                    target,
                    feet: p.position,
                    velocity,
                    distance: d,
                    visible,
                    recent: visible,
                    protected,
                },
            );
        }
        if self.tier.fooled {
            for e in &world.entities {
                if e.kind != EntityKind::Decoy || !entity_enemy(world, slot, e) {
                    continue;
                }
                // A decoy only matters while it is in sight.
                if !sight_clear(world, eye, e.position.offset(Vec3::new(0, 0, CHEST))) {
                    continue;
                }
                let target = Target::Decoy(e.id);
                let d = distance(me.position, e.position);
                let score = i64::from(d) - if current == Some(target) { 3000 } else { 0 };
                consider(
                    score,
                    Sighting {
                        target,
                        feet: e.position,
                        velocity: Vec3::default(),
                        distance: d,
                        visible: true,
                        recent: true,
                        protected: false,
                    },
                );
            }
        }
        let m = &mut *self.memory;
        let Some((_, mut s)) = best else {
            m.target = None;
            m.seen = 0;
            m.tracked = 0;
            return None;
        };
        if m.target != Some(s.target) {
            m.target = Some(s.target);
            m.acquisitions += 1;
            m.seen = 0;
            m.tracked = 0;
            m.seen_tick = 0;
        }
        if s.visible {
            m.seen = m.seen.saturating_add(1);
            m.tracked = m.tracked.saturating_add(1);
            m.seen_tick = world.tick;
        } else if m.seen > 0 && world.tick <= m.seen_tick + MEMORY {
            // Briefly occluded, as at a corner: the fight and the reaction
            // it earned carry on.
            s.recent = true;
        } else {
            m.seen = 0;
            m.tracked = 0;
        }
        Some(s)
    }

    /// The nearest enemy in sight that faces this bot and can land a ray on
    /// it now: a melee blow in reach, or hitscan fire within riposte range.
    fn threat(&self) -> Option<Threat> {
        let (world, slot) = (self.world, self.slot);
        let me = self.me();
        let eye = me.position.offset(Vec3::new(0, 0, EYE_HEIGHT));
        let mut best: Option<Threat> = None;
        for (other, p) in world.players.iter().enumerate() {
            if !p.alive || !enemy(world, slot, other) {
                continue;
            }
            let d = distance(me.position, p.position);
            if d > 6000
                || !facing(p.yaw, p.position, me.position)
                || !sight_clear(world, eye, p.position.offset(Vec3::new(0, 0, EYE_HEIGHT)))
            {
                continue;
            }
            let strike = strike_of(p);
            let charge = if p.charge_weapon == strike.id {
                p.charge
            } else {
                0
            };
            let ready = p.attack_cooldown <= 1 && p.stamina >= strike.stamina;
            let charging = strike.charge_ticks > 0 && charge + 3 >= strike.charge_ticks;
            let melee =
                d <= strike_reach(strike) + 350 && ready && (strike.charge_ticks == 0 || charging);
            let in_reach = melee && d <= strike_reach(strike) + 100;
            // Hitscan fire counts only when aimed at this bot, within about 11°.
            let shooting = d <= 2900
                && looks_at(p.yaw, p.position, me.position, 2)
                && world.events.iter().any(|e| {
                    matches!(*e, Event::Shot { slot: s, weapon }
                        if s == other && WEAPONS[usize::from(weapon)].kind == AttackKind::Hitscan)
                });
            if (melee || shooting) && best.is_none_or(|b| d < b.distance) {
                best = Some(Threat {
                    attacker: other,
                    distance: d,
                    melee,
                    imminent: in_reach || shooting,
                    charging,
                });
            }
        }
        best
    }

    // ---- Defense ---------------------------------------------------------

    /// Answer a threat on the tier's cadence: a Samurai counter stance, or a
    /// guard pulsed so it always counts as a parry (§3.2). Returns whether the
    /// tick is spent defending.
    fn defend(&mut self, threat: Option<Threat>, act: &mut Act) -> bool {
        let Some(t) = threat else {
            self.memory.threatened = false;
            return false;
        };
        if !self.memory.threatened {
            self.memory.threats += 1;
            self.memory.answering = self.memory.threats.is_multiple_of(self.tier.answer);
        }
        self.memory.threatened = true;
        if !self.memory.answering {
            return false;
        }
        let me = self.me();
        let foe = &self.world.players[t.attacker];
        let face = self.aim_exact(foe.position.offset(Vec3::new(0, 0, CHEST)));
        // The stance negates only frontal hits: the view must end this tick
        // within 60° of the attacker.
        let frontal = turn(slew(me.yaw, face.0, self.tier.turn), face.0).abs() <= 10_923;
        if me.class == 0 && me.ability_cooldown == 0 && t.imminent && t.distance <= 2900 && frontal
        {
            act.aim = Some(face);
            act.buttons |= ABILITY;
            act.motion = Some(Motion::Hold);
            return true;
        }
        if !t.melee || me.stamina < 20 {
            return false;
        }
        // Striking first beats waiting for a blow, unless a heavy one is
        // about to land and this tier reads it.
        let strike = strike_of(me);
        let ready = me.attack_cooldown <= 1 && me.stamina >= strike.stamina;
        if ready && !(self.tier.reads_charge && t.charging) {
            return false;
        }
        // A guard parries during its first 8 ticks: release for a tick, then
        // guard afresh.
        if !(me.guarding && me.guard_ticks >= 7) {
            act.buttons |= BLOCK;
        }
        act.aim = Some(face);
        act.motion = Some(Motion::Hold);
        true
    }

    // ---- Class abilities (§6) ---------------------------------------------

    /// Use the class ability when it helps. Returns whether it claims the
    /// tick's facing, so no attack goes out.
    fn ability(&mut self, sight: Option<Sighting>, post: Option<Point>, act: &mut Act) -> bool {
        match self.me().class {
            1 => self.decoy(sight, act),
            2 => {
                self.mark(sight, act);
                false
            }
            3 => self.fire_pot(sight, act),
            4 => self.barricade(sight, post, act),
            5 => {
                self.ward(sight, act);
                false
            }
            // The Samurai stance answers threats in `defend`.
            _ => false,
        }
    }

    /// Shinobi Utsusemi (§6.2): leave a decoy and dash 2000 mm, away when
    /// badly hurt, or across the line of an enemy that faces it to flank. The
    /// dash must be clear of walls, barricades and hazards.
    fn decoy(&mut self, sight: Option<Sighting>, act: &mut Act) -> bool {
        let Some(s) = sight else { return false };
        let Target::Player(foe) = s.target else {
            return false;
        };
        let world = self.world;
        let me = self.me();
        let pos = me.position;
        if !s.visible {
            return false;
        }
        let escape =
            me.health * 100 <= CLASSES[usize::from(me.class)].health * 35 && s.distance <= 7000;
        let flank = !escape
            && (4500..=9000).contains(&s.distance)
            && facing(world.players[foe].yaw, s.feet, pos);
        if !(escape || flank) {
            return false;
        }
        // A barricade raised this same tick by a lower slot could still clip
        // the dash, so never dash near a Karakuri whose ability is ready.
        if world.players.iter().enumerate().any(|(other, p)| {
            other != self.slot
                && p.alive
                && p.class == 4
                && p.ability_cooldown == 0
                && distance(p.position, pos) <= 8000
        }) {
            return false;
        }
        let toward = yaw_toward(s.feet.x - pos.x, s.feet.y - pos.y);
        let side: i32 = if self.memory.side { 1 } else { -1 };
        let offsets = if escape {
            [32768, 32768 - side * 6000, 32768 + side * 6000]
        } else {
            [side * 6000, side * 9000, -side * 6000]
        };
        for offset in offsets {
            let yaw = toward.wrapping_add(offset as u16);
            let (dx, dy) = ahead(yaw, 2000);
            let end = Vec3::new(pos.x + dx, pos.y + dy, pos.z);
            if motion_clear(world, pos, dx, dy) && !in_hazard(world, end) {
                act.aim = Some((yaw, 0));
                act.buttons |= ABILITY;
                act.exact |= ABILITY;
                // The dash starts where the step ends: stand still.
                act.motion = Some(Motion::Hold);
                return true;
            }
        }
        false
    }

    /// Teppō Mato-ire (§6.3): mark an unmarked enemy in sight. The mark
    /// resolves before this tick's shot, which still goes out.
    fn mark(&mut self, sight: Option<Sighting>, act: &mut Act) {
        let Some(s) = sight else { return };
        let Target::Player(foe) = s.target else {
            return;
        };
        // The mark is a single ray: wait until the aim has settled.
        if !s.visible
            || s.protected
            || s.distance > 44_000
            || self.memory.seen < self.tier.reaction
            || self.memory.tracked < self.tier.settle
            || self.world.players[foe].marked_ticks > 0
        {
            return;
        }
        act.aim = Some(self.aim_at(s.feet.offset(Vec3::new(0, 0, CHEST))));
        act.buttons |= ABILITY;
        act.aimed |= ABILITY;
    }

    /// Hanabi Kaen-tsubo (§6.4): throw the pot to land at an enemy's feet,
    /// within the 9000 mm throw. It claims the facing for the tick.
    fn fire_pot(&mut self, sight: Option<Sighting>, act: &mut Act) -> bool {
        let Some(s) = sight else { return false };
        if !s.visible
            || s.protected
            || !(2500..=8600).contains(&s.distance)
            || self.memory.seen < self.tier.reaction
        {
            return false;
        }
        // The pot lands at once and burns for five seconds: aim at the feet.
        let eye = self.eye_next();
        let at = s.feet;
        if !sight_clear(self.world, eye, at.offset(Vec3::new(0, 0, 300))) {
            return false;
        }
        let yaw = yaw_toward(at.x - eye.x, at.y - eye.y);
        let pitch = pitch_toward(distance(eye, at), at.z - eye.z);
        act.aim = Some((yaw, pitch));
        act.buttons |= ABILITY;
        act.aimed |= ABILITY;
        true
    }

    /// Karakuri-tate (§6.5): raise cover toward an enemy that is shooting at
    /// this bot, or toward any enemy while holding the objective, when the
    /// placement fits. It claims the facing for the tick.
    fn barricade(&mut self, sight: Option<Sighting>, post: Option<Point>, act: &mut Act) -> bool {
        let Some(s) = sight else { return false };
        let Target::Player(foe) = s.target else {
            return false;
        };
        if !s.visible || !(3000..=25_000).contains(&s.distance) {
            return false;
        }
        let tick = self.world.tick;
        let pressed = self
            .memory
            .attacker
            .is_some_and(|(a, at)| a == foe && tick <= at + 120);
        let holding = post.is_some_and(|p| nav::length(self.here(), p) <= 3000);
        if !(pressed || holding) {
            return false;
        }
        let me = self.me();
        let yaw = yaw_toward(s.feet.x - me.position.x, s.feet.y - me.position.y);
        if !geometry::barricade_fits(self.world, self.slot, me.position, yaw) {
            return false;
        }
        act.aim = Some((yaw, 0));
        act.buttons |= ABILITY;
        act.exact |= ABILITY;
        // Placement tests the body where the step ends: stand still.
        act.motion = Some(Motion::Hold);
        true
    }

    /// Kusushi Yakuen (§6.6): heal and ward when the heal is worth it, or when
    /// the team fights together.
    fn ward(&mut self, sight: Option<Sighting>, act: &mut Act) {
        let world = self.world;
        let me = self.me();
        let team = world.config.mode.team();
        let (mut missing, mut near) = (0, 0);
        for (other, p) in world.players.iter().enumerate() {
            if !p.alive
                || !(other == self.slot || (team && p.team == me.team))
                || p.position.distance_squared(me.position) > 6000_i64 * 6000
            {
                continue;
            }
            near += 1;
            missing += (CLASSES[usize::from(p.class)].health - p.health).min(35);
        }
        let own = CLASSES[usize::from(me.class)].health - me.health;
        let fighting = sight.is_some_and(|s| s.visible && s.distance <= 15_000);
        if own >= 45 || missing >= 60 || (team && fighting && near >= 3) {
            act.buttons |= ABILITY;
        }
    }

    // ---- Attack ------------------------------------------------------------

    /// Fight the sighted enemy: track it, strike when in reach, otherwise fire
    /// the equipped weapon within its range, and choose the fighting motion.
    fn attack(&mut self, s: &Sighting, post: Option<Point>, act: &mut Act) {
        let me = self.me();
        let equipped = WEAPONS[usize::from(me.weapon)];
        if act.motion.is_none() {
            act.motion = self.engage(s, equipped, post);
        }
        // Aim through a brief occlusion too, ready for the target to reappear.
        if !s.recent {
            return;
        }
        let (strike, button) = if equipped.kind == AttackKind::Melee {
            (equipped, FIRE)
        } else {
            (WEAPONS[usize::from(me.class * 2)], MELEE)
        };
        // A blow that is still charging lands later, after closing in.
        let charged = if me.charge_weapon == strike.id {
            me.charge
        } else {
            0
        };
        let closing = CLASSES[usize::from(me.class)].move_mm_tick
            * i32::from(strike.charge_ticks.saturating_sub(charged))
            / 2;
        let in_reach = s.distance <= strike_reach(strike) + closing;
        let weapon = if in_reach { strike } else { equipped };
        let point = if weapon.kind == AttackKind::Projectile {
            self.lead(s, weapon.projectile_mm_tick)
                .offset(Vec3::new(0, 0, CENTRE))
        } else {
            s.feet.offset(Vec3::new(0, 0, CHEST))
        };
        if act.aim.is_none() {
            act.aim = Some(self.aim_at(point));
        }
        if !s.visible || s.protected || self.memory.seen < self.tier.reaction {
            return;
        }
        if in_reach {
            if me.stamina >= strike.stamina {
                act.buttons |= button;
            }
            return;
        }
        if equipped.kind == AttackKind::Melee {
            return;
        }
        let range = if equipped.kind == AttackKind::Projectile {
            (equipped.range_mm - 1000).min(22_000)
        } else {
            equipped.range_mm - 1000
        };
        // Never inside the own blast, nor before the fuse arms.
        let safe = equipped.kind != AttackKind::Projectile
            || s.distance > (equipped.blast_mm + 800).max(equipped.arming_mm + 300);
        let period = self.tier.burst + self.tier.pause;
        let cadence = equipped.charge_ticks > 0 || self.memory.seen % period < self.tier.burst;
        if s.distance <= range && safe && cadence {
            act.buttons |= FIRE;
        }
    }

    /// The motion of a fight in sight: maai for blades, a range band for guns,
    /// cover when hurt or reloading, and in team modes a leash to the post.
    fn engage(&mut self, s: &Sighting, equipped: Weapon, post: Option<Point>) -> Option<Motion> {
        if !s.recent || s.distance > 30_000 {
            return None;
        }
        let me = self.me();
        let target = (s.feet.x, s.feet.y);
        let toward = if s.distance <= 6000 {
            Motion::Direct(target)
        } else {
            Motion::Goal(target)
        };
        let motion = if equipped.kind == AttackKind::Melee {
            // Maai: step in to strike when ready, otherwise stay just outside
            // the enemy's own reach.
            let ready = me.attack_cooldown <= 4 && me.stamina >= equipped.stamina;
            let theirs = match s.target {
                Target::Player(foe) => strike_reach(strike_of(&self.world.players[foe])),
                Target::Decoy(_) => 0,
            };
            if !ready {
                if s.distance < theirs + 400 {
                    Motion::Away(s.feet)
                } else if self.tier.strafe > 0 {
                    Motion::Strafe(s.feet)
                } else {
                    Motion::Hold
                }
            } else if s.distance <= strike_reach(equipped) - 250 {
                Motion::Hold
            } else if let (1, Target::Player(foe)) = (me.class, s.target)
                && s.distance > 5000
                && facing(self.world.players[foe].yaw, s.feet, me.position)
            {
                // A Shinobi comes in from the side of an enemy watching it.
                Motion::Goal(self.flank(s))
            } else {
                toward
            }
        } else {
            let (near, far) = band(equipped.id);
            let hurt = me.health * 100 <= CLASSES[usize::from(me.class)].health * 35;
            let cover = if hurt || me.reload_ticks > 0 {
                self.cover(s.feet.offset(Vec3::new(0, 0, EYE_HEIGHT)))
            } else {
                None
            };
            if let Some(cover) = cover {
                Motion::Goal(cover)
            } else if s.distance > far {
                toward
            } else if s.distance < near {
                // Samurai, Shinobi and Hanabi carry real blades and close in to
                // strike; the others back off to their band.
                let strike = WEAPONS[usize::from(me.class * 2)];
                let brawler = matches!(me.class, 0 | 1 | 3);
                if brawler && me.attack_cooldown <= 4 && me.stamina >= strike.stamina {
                    Motion::Direct(target)
                } else {
                    Motion::Away(s.feet)
                }
            } else if self.tier.strafe > 0 {
                Motion::Strafe(s.feet)
            } else {
                Motion::Hold
            }
        };
        Some(self.leash(motion, post))
    }

    /// Team bots fight near their post: they return when too far from it and
    /// never chase past it.
    fn leash(&self, motion: Motion, post: Option<Point>) -> Motion {
        let Some(post) = post else { return motion };
        let limit = match self.world.config.mode {
            Mode::Control => self.world.arena().control.radius as u32 + 4000,
            _ => 4500,
        };
        if nav::length(self.here(), post) > limit {
            return Motion::Goal(post);
        }
        match motion {
            Motion::Goal(p) | Motion::Direct(p) if nav::length(p, post) > limit => Motion::Hold,
            other => other,
        }
    }

    /// A standable point beside an enemy, off the line it watches.
    fn flank(&self, s: &Sighting) -> Point {
        let me = self.me();
        let from = yaw_toward(me.position.x - s.feet.x, me.position.y - s.feet.y);
        let side: u16 = if self.memory.side { 12_000 } else { 53_536 };
        let (dx, dy) = ahead(from.wrapping_add(side), 3500);
        self.nav.standable_near((s.feet.x + dx, s.feet.y + dy))
    }

    /// The nearest graph corner within 6000 mm hidden from `threat_eye`, kept
    /// for a second so the bot commits to it.
    fn cover(&mut self, threat_eye: Vec3) -> Option<Point> {
        let tick = self.world.tick;
        if let Some((p, at)) = self.memory.cover
            && tick < at + 60
        {
            return Some(p);
        }
        let here = self.here();
        let best = self
            .nav
            .nodes()
            .iter()
            .copied()
            .filter(|&n| nav::length(n, here) <= 6000)
            .filter(|&n| !sight_clear(self.world, threat_eye, Vec3::new(n.0, n.1, CHEST)))
            .min_by_key(|&n| (nav::length(n, here), n));
        self.memory.cover = best.map(|p| (p, tick));
        best
    }

    // ---- Support -----------------------------------------------------------

    /// With no enemy close: a Kusushi mends the most hurt ally in sight with
    /// the Healing lance (team modes), and a Karakuri repairs its own or an
    /// ally's barricade with the forge hammer (§6.5).
    fn support(&mut self, sight: Option<Sighting>, act: &mut Act) {
        let world = self.world;
        let me = self.me();
        if sight.is_some_and(|s| s.visible && s.distance <= 8000) {
            return;
        }
        let eye = me.position.offset(Vec3::new(0, 0, EYE_HEIGHT));
        if world.config.mode.team() && me.weapon == 17 {
            let patient = world
                .players
                .iter()
                .enumerate()
                .filter(|&(other, p)| {
                    other != self.slot
                        && p.alive
                        && p.team == me.team
                        && p.health <= CLASSES[usize::from(p.class)].health - 15
                        && distance(me.position, p.position) <= 30_000
                        && sight_clear(world, eye, p.position.offset(Vec3::new(0, 0, CHEST)))
                })
                .min_by_key(|&(other, p)| (p.health - CLASSES[usize::from(p.class)].health, other));
            if let Some((_, p)) = patient {
                act.aim = Some(self.aim_exact(p.position.offset(Vec3::new(0, 0, CHEST))));
                act.buttons |= FIRE;
                act.motion
                    .get_or_insert(if distance(me.position, p.position) > 12_000 {
                        Motion::Goal((p.position.x, p.position.y))
                    } else {
                        Motion::Hold
                    });
                return;
            }
        }
        if me.class != 4 {
            return;
        }
        let team = world.config.mode.team();
        let damaged = world
            .entities
            .iter()
            .filter(|e| {
                e.kind == EntityKind::Barricade
                    && (e.owner == self.slot || (team && e.team == me.team))
                    && e.health <= e.kind.max_health() - 45
                    && distance(me.position, e.position) <= 9000
            })
            .min_by_key(|e| (distance(me.position, e.position), e.id));
        let Some(b) = damaged else { return };
        // Stand 900 mm off the barricade's thin face, on this bot's side.
        let spot = if b.half_x < b.half_y {
            let side = if me.position.x < b.position.x { -1 } else { 1 };
            (b.position.x + side * (b.half_x + 900), b.position.y)
        } else {
            let side = if me.position.y < b.position.y { -1 } else { 1 };
            (b.position.x, b.position.y + side * (b.half_y + 900))
        };
        if !self.nav.standable(spot) {
            return;
        }
        if nav::length(self.here(), spot) > 200 {
            act.motion.get_or_insert(Motion::Goal(spot));
            return;
        }
        act.aim = Some(self.aim_exact(b.position.offset(Vec3::new(0, 0, CHEST))));
        act.motion = Some(Motion::Hold);
        if me.attack_cooldown == 0 && me.stamina >= WEAPONS[8].stamina {
            act.buttons |= MELEE;
        }
    }

    /// Reload an empty magazine, or top up a low one while nothing is in sight.
    /// Blocking and striking would interrupt it.
    fn reload(&self, sight: Option<Sighting>, act: &mut Act) {
        let me = self.me();
        let spec = WEAPONS[usize::from(me.weapon)];
        if spec.magazine == 0
            || me.reload_ticks > 0
            || me.ammo >= spec.magazine
            || act.buttons & (FIRE | MELEE | BLOCK | ABILITY) != 0
        {
            return;
        }
        let quiet = sight.is_none_or(|s| !s.visible);
        if me.ammo == 0 || (quiet && me.ammo * 3 < spec.magazine * 2) {
            act.buttons |= RELOAD;
        }
    }

    // ---- Movement ----------------------------------------------------------

    /// Where to go with nothing to fight: the objective post, over the lanes
    /// on a long trip, or in free-for-all and Melee toward the chosen enemy.
    fn travel(&self, sight: Option<Sighting>, post: Option<Point>) -> Motion {
        let here = self.here();
        if let Some(post) = post {
            if nav::length(here, post) <= 350 {
                return Motion::Hold;
            }
            let via = plan::lane_waypoint(self.world, self.slot, self.nav, here, post);
            return Motion::Goal(via.unwrap_or(post));
        }
        sight.map_or(Motion::Hold, |s| Motion::Goal((s.feet.x, s.feet.y)))
    }

    /// The world heading to walk this tick, if any.
    fn heading(&mut self, motion: Motion) -> Option<u16> {
        let pos = self.me().position;
        match motion {
            Motion::Hold => None,
            Motion::Goal(p) => self.follow(p),
            Motion::Direct(p) => {
                (nav::length((pos.x, pos.y), p) > 150).then(|| yaw_toward(p.0 - pos.x, p.1 - pos.y))
            }
            Motion::Away(q) => Some(yaw_toward(pos.x - q.x, pos.y - q.y)),
            Motion::Strafe(q) => {
                let tick = self.world.tick;
                if tick >= self.memory.side_tick + self.tier.strafe {
                    self.memory.side = !self.memory.side;
                    self.memory.side_tick = tick;
                }
                let toward = yaw_toward(q.x - pos.x, q.y - pos.y);
                Some(toward.wrapping_add(if self.memory.side { 16384 } else { 49152 }))
            }
        }
    }

    /// Follow a graph route to `goal`, replanning when the goal moves, the
    /// next waypoint drops out of reach, or progress stalls.
    fn follow(&mut self, goal: Point) -> Option<u16> {
        let here = self.here();
        if nav::length(here, goal) <= 200 {
            return None;
        }
        let tick = self.world.tick;
        let nav = self.nav;
        let m = &mut *self.memory;
        let stale = m.path.is_empty()
            || m.path_goal.is_none_or(|g| nav::length(g, goal) > 1500)
            || tick >= m.replanned + 120
            || (tick >= m.replanned + 15 && !nav.clear(here, m.path[0]));
        if stale {
            // From inside the planning margin of a wall or hazard, the route
            // starts by stepping out to the nearest standable point.
            let start = nav.standable_near(here);
            m.path = if start == here {
                nav.path(here, goal)
            } else {
                std::iter::once(start)
                    .chain(nav.path(start, goal))
                    .collect()
            };
            m.path_goal = Some(goal);
            m.replanned = tick;
            m.best = i32::MAX;
            m.best_tick = tick;
        }
        // On a waypoint, or with the next one already in the clear: move on.
        while m.path.len() > 1 && (nav::length(here, m.path[0]) <= 60 || nav.clear(here, m.path[1]))
        {
            m.path.remove(0);
            m.best = i32::MAX;
            m.best_tick = tick;
        }
        let Some(&waypoint) = m.path.first() else {
            return Some(yaw_toward(goal.0 - here.0, goal.1 - here.1));
        };
        let left = nav::length(here, waypoint) as i32;
        if left <= 60 {
            return None;
        }
        if left + 150 < m.best {
            m.best = left;
            m.best_tick = tick;
        } else if tick >= m.best_tick + 60 {
            // Stalled: detour the other way round and plan afresh.
            m.side = !m.side;
            m.path.clear();
            m.best = i32::MAX;
            m.best_tick = tick;
        }
        Some(yaw_toward(waypoint.0 - here.0, waypoint.1 - here.1))
    }

    /// Movement axes for `heading` under view `yaw`: the heading itself, else
    /// the nearest turn of it, up to square, whose step the kernel applies in
    /// full without leaving the walkable floor for a hazard.
    fn steer(&self, heading: u16, yaw: u16, guarding: bool) -> (i16, i16) {
        let world = self.world;
        let me = self.me();
        let pos = me.position;
        let hazard_now = in_hazard(world, pos);
        let side: i32 = if self.memory.side { 1 } else { -1 };
        for offset in [
            0, 2048, -2048, 4096, -4096, 8192, -8192, 12_288, -12_288, 16_384, -16_384,
        ] {
            let h = heading.wrapping_add((offset * side) as u16);
            let (move_x, move_y) = move_axes(yaw, h);
            let (dx, dy) = walk_step(me.class, guarding, yaw, move_x, move_y);
            if (dx, dy) == (0, 0) {
                continue;
            }
            let end = Vec3::new(pos.x + dx, pos.y + dy, pos.z);
            if motion_clear(world, pos, dx, dy) && (hazard_now || !in_hazard(world, end)) {
                return (move_x, move_y);
            }
        }
        (0, 0)
    }

    /// Turn the view, gate what needs it, and place the feet.
    fn finish(&mut self, act: Act, motion: Motion) -> Input {
        let heading = self.heading(motion);
        let me = self.me();
        let (want_yaw, want_pitch) = act.aim.unwrap_or((heading.unwrap_or(me.yaw), 0));
        let turn_rate = self.tier.turn;
        let yaw = slew(me.yaw, want_yaw, turn_rate);
        let pitch = (i32::from(me.pitch)
            + (i32::from(want_pitch) - i32::from(me.pitch)).clamp(-turn_rate, turn_rate))
            as i16;
        let off = turn(yaw, want_yaw)
            .abs()
            .max((i32::from(pitch) - i32::from(want_pitch)).abs());
        let mut buttons = act.buttons;
        if off > 0 {
            buttons &= !act.exact;
        }
        if off > ABILITY_TOLERANCE {
            buttons &= !act.aimed;
        }
        if off > ATTACK_TOLERANCE {
            // A charged weapon may keep charging while the view catches up,
            // as long as the shot cannot leave this tick.
            let spec = WEAPONS[usize::from(me.weapon)];
            let charging = spec.charge_ticks > 0
                && off <= 3000
                && (me.charge_weapon != spec.id || me.charge < spec.charge_ticks);
            buttons &= !MELEE;
            if !charging {
                buttons &= !FIRE;
            }
        }
        // A jump now and then while circling an enemy.
        if matches!(motion, Motion::Strafe(_))
            && me.position.z == 0
            && (self.world.tick + self.slot as u32 * 37).is_multiple_of(97)
        {
            buttons |= JUMP;
        }
        let guarding = buttons & BLOCK != 0 && me.stamina > 0 && me.stance_ticks <= 1;
        let (move_x, move_y) = heading.map_or((0, 0), |h| self.steer(h, yaw, guarding));
        Input {
            buttons,
            move_x,
            move_y,
            yaw,
            pitch,
        }
    }

    // ---- Aim ---------------------------------------------------------------

    /// The eye after this tick's vertical motion, where rays will start.
    fn eye_next(&self) -> Vec3 {
        let me = self.me();
        let z = (me.position.z + (me.velocity_z - 8).max(-500)).max(0);
        Vec3::new(me.position.x, me.position.y, z + EYE_HEIGHT)
    }

    /// The exact view onto `point`.
    fn aim_exact(&self, point: Vec3) -> (u16, i16) {
        let eye = self.eye_next();
        (
            yaw_toward(point.x - eye.x, point.y - eye.y),
            pitch_toward(distance(eye, point), point.z - eye.z),
        )
    }

    /// The view onto `point` with the tier's aim error: large on acquiring a
    /// target, settling to the tier's floor as the bot keeps tracking it.
    fn aim_at(&self, point: Vec3) -> (u16, i16) {
        let (yaw, pitch) = self.aim_exact(point);
        let (t, m) = (self.tier, &*self.memory);
        let settle = i32::from(t.settle);
        let left = (settle - i32::from(m.tracked)).max(0);
        let amplitude = t.aim_floor + (t.aim_error - t.aim_floor) * left / settle;
        let index = (m.acquisitions as usize + self.slot * 3 + usize::from(m.tracked / 20)) % 8;
        let yaw_error = amplitude * AIM_PATTERN[index] / 256;
        let pitch_error = amplitude * AIM_PATTERN[(index + 3) % 8] / 512;
        (
            yaw.wrapping_add(yaw_error as u16),
            (i32::from(pitch) + pitch_error).clamp(-16384, 16384) as i16,
        )
    }

    /// The target's feet, led by its last-tick velocity over the flight time
    /// of a `speed` mm/tick projectile when the tier leads.
    fn lead(&self, s: &Sighting, speed: i32) -> Vec3 {
        if !self.tier.lead || speed <= 0 {
            return s.feet;
        }
        let ticks = (s.distance / speed).min(45);
        Vec3::new(
            s.feet.x + s.velocity.x.clamp(-120, 120) * ticks,
            s.feet.y + s.velocity.y.clamp(-120, 120) * ticks,
            s.feet.z,
        )
    }
}
