//! Deterministic bounded 60 Hz combat reference. Inputs, not reported hits, drive damage.
use crate::{
    ASSIST_TICKS, Error, MAX_PLAYERS, MAX_TICKS,
    catalog::{self, AttackKind},
    economy::{self, Account, Allocation},
    math::{self, Aabb, Vec3},
};
use sha2::{Digest, Sha256};

pub const FIRE: u32 = 1;
pub const MELEE: u32 = 2;
pub const BLOCK: u32 = 4;
pub const JUMP: u32 = 8;
pub const ABILITY: u32 = 16;
pub const RELOAD: u32 = 32;
pub const RESPAWN_TICKS: u32 = 8 * 60;
pub const RADIUS: i32 = 350;
pub const HEIGHT: i32 = 1700;
pub const BOUNDS: i32 = 24000;
pub const EYE_HEIGHT: i32 = 1400;
const MAX_PROJECTILES: usize = 128;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    FreeForAll,
    Control,
    Payload,
    Melee,
}
impl Mode {
    pub fn team(self) -> bool {
        matches!(self, Self::Control | Self::Payload)
    }
}

#[derive(Debug, Clone)]
pub struct Config {
    pub mode: Mode,
    pub map: u8,
    pub max_ticks: u32,
    pub base_bond: u64,
    pub offline: bool,
}
#[derive(Debug, Clone)]
pub struct Participant {
    pub team: u8,
    pub class: u8,
    pub weapon: u8,
    pub bond: u64,
    pub special_entitled: bool,
}
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct Input {
    pub buttons: u32,
    pub move_x: i16,
    pub move_y: i16,
    pub yaw: u16,
    pub pitch: i16,
}
impl Input {
    pub fn validate(self) -> Result<(), Error> {
        if self.buttons & !63 != 0
            || !(-127..=127).contains(&self.move_x)
            || !(-127..=127).contains(&self.move_y)
            || !(-16384..=16384).contains(&self.pitch)
        {
            return Err(Error::InvalidInput(
                "input outside canonical control bounds",
            ));
        }
        Ok(())
    }
    /// Eight-byte input; slot and tick are defined by the containing batch.
    pub fn encode(self) -> [u8; 8] {
        let b = (self.buttons as u16).to_le_bytes();
        let y = self.yaw.to_le_bytes();
        let p = self.pitch.to_le_bytes();
        [
            b[0],
            b[1],
            self.move_x as i8 as u8,
            self.move_y as i8 as u8,
            y[0],
            y[1],
            p[0],
            p[1],
        ]
    }
    pub fn decode(bytes: [u8; 8]) -> Result<Self, Error> {
        let i = Self {
            buttons: u16::from_le_bytes([bytes[0], bytes[1]]) as u32,
            move_x: bytes[2] as i8 as i16,
            move_y: bytes[3] as i8 as i16,
            yaw: u16::from_le_bytes([bytes[4], bytes[5]]),
            pitch: i16::from_le_bytes([bytes[6], bytes[7]]),
        };
        i.validate()?;
        Ok(i)
    }
}

#[derive(Debug, Clone)]
pub struct Player {
    pub team: u8,
    pub class: u8,
    pub weapon: u8,
    pub position: Vec3,
    pub velocity_z: i32,
    pub yaw: u16,
    pub pitch: i16,
    pub health: i32,
    pub stamina: i32,
    pub alive: bool,
    pub respawn_ticks: u32,
    pub attack_cooldown: u16,
    pub ability_cooldown: u16,
    pub charge: u16,
    pub ammo: u16,
    pub reload_ticks: u16,
    pub guarding: bool,
    pub guard_ticks: u16,
    pub spawn_protection: u16,
    pub admitted_special: bool,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DamageRecord {
    pub tick: u32,
    pub attacker: usize,
    pub victim: usize,
    pub damage: u32,
}
#[derive(Debug, Clone)]
pub struct Projectile {
    pub id: u32,
    pub owner: usize,
    pub position: Vec3,
    pub velocity: Vec3,
    pub weapon: u8,
    pub traveled: i32,
    pub age: u16,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Event {
    Shot {
        slot: usize,
        weapon: u8,
    },
    Damage {
        attacker: usize,
        victim: usize,
        amount: i32,
    },
    Death {
        victim: usize,
        killer: Option<usize>,
        awards: Vec<Allocation>,
    },
    Respawn {
        slot: usize,
    },
    Terminal,
}
#[derive(Debug, Clone)]
pub struct World {
    pub config: Config,
    pub tick: u32,
    pub players: Vec<Player>,
    pub accounts: Vec<Account>,
    pub projectiles: Vec<Projectile>,
    pub damage_history: Vec<DamageRecord>,
    pub events: Vec<Event>,
    pub terminal: bool,
    pub score: [u32; 2],
    pub control_owner: Option<u8>,
    pub control_progress: i32,
    pub payload_progress: i32,
    pub walls: Vec<Aabb>,
}

pub fn map_walls(map: u8) -> Vec<Aabb> {
    type WallBounds = (i32, i32, i32, i32, i32);
    let sets: [&[WallBounds]; 4] = [
        &[
            (-8000, -9000, -6500, 6000, 3800),
            (6500, -6000, 8000, 9000, 3800),
            (-4000, 7000, 3500, 8000, 2300),
        ],
        &[
            (-12000, -7000, -8000, 7000, 6000),
            (8000, -7000, 12000, 7000, 6000),
            (-3000, -14000, 3000, -10000, 4000),
            (-3000, 10000, 3000, 14000, 4000),
        ],
        &[
            (-11000, -12000, -9000, 10000, 5000),
            (9000, -10000, 11000, 12000, 5000),
            (-3000, -5000, 3000, -3500, 2300),
            (-3000, 3500, 3000, 5000, 2300),
        ],
        &[
            (-10000, -10000, -7000, 5000, 7500),
            (7000, -5000, 10000, 10000, 7500),
            (-3000, -16000, 3000, -12000, 5500),
            (-3000, 12000, 3000, 16000, 5500),
        ],
    ];
    sets.get(map as usize)
        .into_iter()
        .flat_map(|s| s.iter())
        .map(|&(x1, y1, x2, y2, h)| Aabb {
            min: Vec3::new(x1, y1, 0),
            max: Vec3::new(x2, y2, h),
        })
        .collect()
}

fn spawn(slot: usize, team: u8, team_mode: bool) -> Vec3 {
    if team_mode {
        Vec3::new(
            if team == 0 { -19000 } else { 19000 },
            (slot as i32 / 2) * 2000 - 5000,
            0,
        )
    } else {
        let angles = [
            0u16, 32768, 16384, 49152, 8192, 40960, 24576, 57344, 4096, 36864, 20480, 53248,
        ];
        math::scale_q15(math::direction(angles[slot], 0), 18000)
    }
}

impl World {
    pub fn new(config: Config, participants: &[Participant]) -> Result<Self, Error> {
        if participants.is_empty()
            || participants.len() > MAX_PLAYERS
            || config.map >= 4
            || config.max_ticks == 0
            || config.max_ticks > MAX_TICKS
            || (!config.mode.team() && participants.len() > 8)
        {
            return Err(Error::InvalidConfig("invalid match bounds"));
        }
        if (config.offline && (config.base_bond != 0 || participants.iter().any(|p| p.bond != 0)))
            || (!config.offline && (config.base_bond == 0 || !config.base_bond.is_multiple_of(10)))
        {
            return Err(Error::InvalidConfig("invalid base bond or offline funds"));
        }
        let mut players = Vec::new();
        let mut accounts = Vec::new();
        let mut total = 0u64;
        for (slot, p) in participants.iter().enumerate() {
            if p.class >= 6
                || p.team >= 2
                || !catalog::weapon_allowed(p.class, p.weapon, p.weapon >= 12)
            {
                return Err(Error::InvalidConfig("class, team or weapon mismatch"));
            }
            if config.mode == Mode::Melee
                && catalog::WEAPONS[p.weapon as usize].kind != AttackKind::Melee
            {
                return Err(Error::InvalidConfig("ranged weapon in melee-only mode"));
            }
            let needed = if p.weapon >= 12 && !p.special_entitled {
                config.base_bond.checked_mul(2).ok_or(Error::Arithmetic)?
            } else {
                config.base_bond
            };
            if p.bond != needed || !p.bond.is_multiple_of(10) {
                return Err(Error::InvalidConfig("deposit does not authorize equipment"));
            }
            total = total.checked_add(p.bond).ok_or(Error::Arithmetic)?;
            players.push(Player {
                team: p.team,
                class: p.class,
                weapon: p.weapon,
                position: spawn(slot, p.team, config.mode.team()),
                velocity_z: 0,
                yaw: if config.mode.team() {
                    if p.team == 0 { 0 } else { 32768 }
                } else {
                    0
                },
                pitch: 0,
                health: catalog::CLASSES[p.class as usize].health,
                stamina: 100,
                alive: true,
                respawn_ticks: 0,
                attack_cooldown: 0,
                ability_cooldown: 0,
                charge: 0,
                ammo: catalog::WEAPONS[p.weapon as usize].magazine,
                reload_ticks: 0,
                guarding: false,
                guard_ticks: 0,
                spawn_protection: 0,
                admitted_special: p.weapon >= 12,
            });
            accounts.push(Account::new(p.bond));
        }
        if config.mode.team()
            && (players.iter().filter(|p| p.team == 0).count() > 6
                || players.iter().filter(|p| p.team == 1).count() > 6)
        {
            return Err(Error::InvalidConfig("team exceeds six participants"));
        }
        let walls = map_walls(config.map);
        Ok(Self {
            config,
            tick: 0,
            players,
            accounts,
            projectiles: Vec::new(),
            damage_history: Vec::new(),
            events: Vec::new(),
            terminal: false,
            score: [0, 0],
            control_owner: None,
            control_progress: 0,
            payload_progress: 0,
            walls,
        })
    }

    pub fn exhausted(&self, slot: usize) -> bool {
        self.accounts[slot].initial > 0 && self.accounts[slot].remaining == 0
    }
    fn enemy(&self, a: usize, b: usize) -> bool {
        a != b && (!self.config.mode.team() || self.players[a].team != self.players[b].team)
    }
    fn body(&self, slot: usize) -> Aabb {
        let p = self.players[slot].position;
        Aabb {
            min: Vec3::new(p.x - RADIUS, p.y - RADIUS, p.z),
            max: Vec3::new(p.x + RADIUS, p.y + RADIUS, p.z + HEIGHT),
        }
    }
    fn blocked(&self, from: Vec3, to: Vec3) -> bool {
        self.walls.iter().any(|w| w.intersect(from, to).is_some())
    }
    fn safe_motion(&self, old: Vec3, desired: Vec3) -> Vec3 {
        let mut next = old;
        for axis in 0..2 {
            let mut p = next;
            if axis == 0 {
                p.x = desired.x.clamp(-BOUNDS + RADIUS, BOUNDS - RADIUS);
            } else {
                p.y = desired.y.clamp(-BOUNDS + RADIUS, BOUNDS - RADIUS);
            }
            let feet = Vec3::new(p.x, p.y, p.z + HEIGHT / 2);
            if !self.walls.iter().any(|w| {
                w.expanded(RADIUS, HEIGHT / 2).contains(feet)
                    || w.expanded(RADIUS, HEIGHT / 2)
                        .intersect(Vec3::new(next.x, next.y, next.z + HEIGHT / 2), feet)
                        .is_some()
            }) {
                next = p;
            }
        }
        next.z = desired.z.max(0);
        next
    }

    /// Invalid inputs do not advance time or partially modify a match.
    pub fn step(&mut self, inputs: &[Input]) -> Result<(), Error> {
        if self.terminal {
            return Err(Error::Terminal);
        }
        if inputs.len() != self.players.len() {
            return Err(Error::InvalidInput("one input required per permanent slot"));
        }
        for i in inputs {
            i.validate()?;
        }
        self.events.clear();
        for (slot, &input) in inputs.iter().enumerate() {
            if !self.players[slot].alive {
                if self.exhausted(slot) {
                    continue;
                }
                if self.players[slot].respawn_ticks > 0 {
                    self.players[slot].respawn_ticks -= 1;
                }
                if self.players[slot].respawn_ticks == 0 {
                    let p = &mut self.players[slot];
                    p.position = spawn(slot, p.team, self.config.mode.team());
                    p.health = catalog::CLASSES[p.class as usize].health;
                    p.alive = true;
                    p.stamina = 100;
                    p.spawn_protection = 120;
                    p.velocity_z = 0;
                    p.charge = 0;
                    p.ammo = catalog::WEAPONS[p.weapon as usize].magazine;
                    p.reload_ticks = 0;
                    p.guarding = false;
                    p.guard_ticks = 0;
                    p.attack_cooldown = 0;
                    self.events.push(Event::Respawn { slot });
                }
                continue;
            }
            let p = &mut self.players[slot];
            p.yaw = input.yaw;
            p.pitch = input.pitch;
            p.attack_cooldown = p.attack_cooldown.saturating_sub(1);
            // Blocking or a melee request interrupts the whole-magazine reload
            // before completion. Partial progress never creates ammunition.
            if input.buttons & (BLOCK | MELEE) != 0 {
                p.reload_ticks = 0;
            } else if p.reload_ticks > 0 {
                p.reload_ticks -= 1;
                if p.reload_ticks == 0 {
                    p.ammo = catalog::WEAPONS[p.weapon as usize].magazine;
                }
            }
            p.ability_cooldown = p.ability_cooldown.saturating_sub(1);
            p.spawn_protection = p.spawn_protection.saturating_sub(1);
            p.guarding = input.buttons & BLOCK != 0 && p.stamina > 0;
            p.guard_ticks = if p.guarding {
                p.guard_ticks.saturating_add(1)
            } else {
                0
            };
            if p.guarding {
                p.stamina = (p.stamina - 1).max(0);
            } else {
                p.stamina = (p.stamina + 1).min(100);
            }
            if input.buttons & JUMP != 0 && p.position.z == 0 {
                p.velocity_z = 180;
            }
            p.velocity_z = (p.velocity_z - 8).max(-500);
            let speed =
                catalog::CLASSES[p.class as usize].move_mm_tick / (if p.guarding { 2 } else { 1 });
            let forward = math::direction(input.yaw, 0);
            let right = math::direction(input.yaw.wrapping_add(16384), 0);
            // L1 normalization prevents diagonal speed gain without square roots.
            let norm = (i32::from(input.move_x).abs() + i32::from(input.move_y).abs()).max(127);
            let dx = ((i64::from(forward.x) * i64::from(input.move_x)
                + i64::from(right.x) * i64::from(input.move_y))
                * i64::from(speed)
                / (32767 * i64::from(norm))) as i32;
            let dy = ((i64::from(forward.y) * i64::from(input.move_x)
                + i64::from(right.y) * i64::from(input.move_y))
                * i64::from(speed)
                / (32767 * i64::from(norm))) as i32;
            let old = p.position;
            let desired = old.offset(Vec3::new(dx, dy, p.velocity_z));
            self.players[slot].position = self.safe_motion(old, desired);
            if self.players[slot].position.z == 0 {
                self.players[slot].velocity_z = 0;
            }
        }
        self.damage_history
            .retain(|h| self.tick.saturating_sub(h.tick) <= ASSIST_TICKS);
        let mut damage = Vec::<(usize, usize, i32)>::new();
        // Gather attacks before applying damage so mutual kills are possible.
        for (slot, input) in inputs.iter().enumerate() {
            if !self.players[slot].alive {
                continue;
            }
            if input.buttons & ABILITY != 0 && self.players[slot].ability_cooldown == 0 {
                self.ability(slot);
            }
            let equipped = catalog::WEAPONS[self.players[slot].weapon as usize];
            if input.buttons & RELOAD != 0
                && input.buttons & (BLOCK | MELEE) == 0
                && equipped.magazine > 0
                && self.players[slot].ammo < equipped.magazine
                && self.players[slot].reload_ticks == 0
            {
                self.players[slot].reload_ticks = equipped.reload_ticks;
            }
            if self.players[slot].reload_ticks > 0 || self.players[slot].guarding {
                self.players[slot].charge = 0;
                continue;
            }
            if input.buttons & (FIRE | MELEE) == 0 {
                self.players[slot].charge = 0;
                continue;
            }
            if self.players[slot].attack_cooldown != 0 {
                continue;
            }
            let weapon = if input.buttons & MELEE != 0 {
                self.players[slot].class * 2
            } else {
                self.players[slot].weapon
            };
            let spec = catalog::WEAPONS[weapon as usize];
            if spec.kind != AttackKind::Melee && self.players[slot].ammo == 0 {
                self.players[slot].reload_ticks = spec.reload_ticks;
                self.players[slot].charge = 0;
                continue;
            }
            if self.players[slot].stamina < spec.stamina {
                continue;
            }
            if self.players[slot].charge < spec.charge_ticks {
                self.players[slot].charge += 1;
                continue;
            }
            self.players[slot].charge = 0;
            self.players[slot].stamina -= spec.stamina;
            if spec.kind != AttackKind::Melee {
                self.players[slot].ammo -= 1;
            }
            self.players[slot].attack_cooldown = spec.cooldown;
            self.players[slot].spawn_protection = 0;
            let from = self.players[slot]
                .position
                .offset(Vec3::new(0, 0, EYE_HEIGHT));
            let direction = math::direction(self.players[slot].yaw, self.players[slot].pitch);
            let to = from.offset(math::scale_q15(direction, spec.range_mm));
            self.events.push(Event::Shot { slot, weapon });
            match spec.kind {
                AttackKind::Melee | AttackKind::Hitscan => {
                    let mut nearest = self
                        .walls
                        .iter()
                        .filter_map(|w| w.intersect(from, to))
                        .min()
                        .unwrap_or((1 << 20) + 1);
                    let mut hit = None;
                    for other in 0..self.players.len() {
                        if !self.enemy(slot, other)
                            || !self.players[other].alive
                            || self.players[other].spawn_protection > 0
                        {
                            continue;
                        }
                        let body = if spec.kind == AttackKind::Melee {
                            self.body(other).expanded(180, 0)
                        } else {
                            self.body(other)
                        };
                        if let Some(t) = body.intersect(from, to)
                            && t < nearest
                        {
                            nearest = t;
                            hit = Some(other);
                        }
                    }
                    if let Some(other) = hit {
                        damage.push((slot, other, spec.damage));
                    }
                }
                AttackKind::Projectile => {
                    if self.projectiles.len() < MAX_PROJECTILES {
                        self.projectiles.push(Projectile {
                            id: self.tick * MAX_PLAYERS as u32 + slot as u32,
                            owner: slot,
                            position: from,
                            velocity: math::scale_q15(direction, spec.projectile_mm_tick),
                            weapon,
                            traveled: 0,
                            age: 0,
                        });
                    }
                }
            }
        }
        let flying = std::mem::take(&mut self.projectiles);
        for mut p in flying {
            let spec = catalog::WEAPONS[p.weapon as usize];
            let old = p.position;
            let previous_travel = p.traveled;
            let step_mm = spec.projectile_mm_tick.min(spec.range_mm - previous_travel);
            // The last range-limited step is shortened before collision tests.
            // Truncate each signed component toward zero, like other movement.
            let displacement = Vec3::new(
                (i64::from(p.velocity.x) * i64::from(step_mm) / i64::from(spec.projectile_mm_tick))
                    as i32,
                (i64::from(p.velocity.y) * i64::from(step_mm) / i64::from(spec.projectile_mm_tick))
                    as i32,
                (i64::from(p.velocity.z) * i64::from(step_mm) / i64::from(spec.projectile_mm_tick))
                    as i32,
            );
            let next = old.offset(displacement);
            p.traveled += step_mm;
            p.age += 1;
            let mut intersection = self
                .walls
                .iter()
                .filter_map(|w| w.intersect(old, next))
                .min();
            for slot in 0..self.players.len() {
                if slot != p.owner
                    && self.players[slot].alive
                    && let Some(t) = self.body(slot).intersect(old, next)
                {
                    intersection = Some(intersection.map_or(t, |v| v.min(t)));
                }
            }
            let expired = p.traveled >= spec.range_mm
                || p.age >= 300
                || next.z <= 0
                || next.x.abs() > BOUNDS
                || next.y.abs() > BOUNDS;
            if intersection.is_some() || expired {
                let frac = intersection.unwrap_or(1 << 20);
                let d = next.delta(old);
                p.position = old.offset(Vec3::new(
                    (i64::from(d.x) * frac / (1 << 20)) as i32,
                    (i64::from(d.y) * frac / (1 << 20)) as i32,
                    (i64::from(d.z) * frac / (1 << 20)) as i32,
                ));
                // Only distance traversed before the Q20 impact can arm a fuse.
                // Floor nonnegative fractional millimetres conservatively.
                p.traveled = previous_travel + (i64::from(step_mm) * frac / (1 << 20)) as i32;
                if p.traveled >= spec.arming_mm {
                    for slot in 0..self.players.len() {
                        let center = self.players[slot].position.offset(Vec3::new(0, 0, 900));
                        if !self.players[slot].alive
                            || self.players[slot].spawn_protection > 0
                            || (!self.enemy(p.owner, slot) && slot != p.owner)
                        {
                            continue;
                        }
                        if center.distance_squared(p.position)
                            <= i64::from(spec.blast_mm) * i64::from(spec.blast_mm)
                            && !self.blocked(p.position, center)
                        {
                            damage.push((p.owner, slot, spec.damage));
                        }
                    }
                }
            } else {
                p.position = next;
                self.projectiles.push(p);
            }
        }
        let mut killers = vec![None; self.players.len()];
        for (attacker, victim, mut amount) in damage {
            if self.players[victim].health <= 0 {
                continue;
            }
            if self.players[victim].guarding && attacker != victim {
                let facing = math::direction(self.players[victim].yaw, 0);
                let incoming = self.players[attacker]
                    .position
                    .delta(self.players[victim].position);
                if i64::from(facing.x) * i64::from(incoming.x)
                    + i64::from(facing.y) * i64::from(incoming.y)
                    > 0
                {
                    if self.players[victim].guard_ticks <= 8 && self.players[victim].stamina >= 20 {
                        amount = 0;
                        self.players[victim].stamina -= 20;
                    } else if self.players[victim].stamina >= 10 {
                        amount = (amount + 1) / 2;
                        self.players[victim].stamina -= 10;
                    }
                }
            }
            let dealt = amount.min(self.players[victim].health);
            self.players[victim].health -= dealt;
            if dealt > 0 {
                self.events.push(Event::Damage {
                    attacker,
                    victim,
                    amount: dealt,
                });
                if attacker != victim {
                    self.damage_history.push(DamageRecord {
                        tick: self.tick,
                        attacker,
                        victim,
                        damage: dealt as u32,
                    });
                }
            }
            if self.players[victim].health <= 0 {
                killers[victim] = if self.enemy(attacker, victim) {
                    Some(attacker)
                } else {
                    self.damage_history
                        .iter()
                        .rev()
                        .find(|h| h.victim == victim && self.enemy(h.attacker, victim))
                        .map(|h| h.attacker)
                };
            }
        }
        // Participation is frozen for the whole simultaneous death batch. A
        // lower-slot victim exhausting now must not lose a teammate award from
        // another death in the same tick merely because we visit it first.
        let participating: Vec<_> = (0..self.players.len())
            .map(|slot| !self.exhausted(slot))
            .collect();
        for (victim, killer) in killers.into_iter().enumerate() {
            if self.players[victim].alive && self.players[victim].health <= 0 {
                let mut assist_damage = vec![0u32; self.players.len()];
                if let Some(k) = killer {
                    for h in &self.damage_history {
                        if h.victim == victim
                            && h.attacker != k
                            && self.enemy(h.attacker, victim)
                            && (!self.config.mode.team()
                                || self.players[h.attacker].team == self.players[k].team)
                        {
                            assist_damage[h.attacker] =
                                assist_damage[h.attacker].saturating_add(h.damage);
                        }
                    }
                }
                let assists: Vec<_> = assist_damage
                    .into_iter()
                    .enumerate()
                    .filter(|(_, d)| *d > 0)
                    .collect();
                let teammates: Vec<_> = if self.config.mode.team() {
                    killer.map_or_else(Vec::new, |k| {
                        (0..self.players.len())
                            .filter(|&s| {
                                s != k
                                    && self.players[s].team == self.players[k].team
                                    && participating[s]
                            })
                            .collect()
                    })
                } else {
                    Vec::new()
                };
                let awards = economy::apply_death(
                    &mut self.accounts,
                    victim,
                    killer,
                    &assists,
                    &teammates,
                    self.config.mode.team(),
                )?;
                self.players[victim].alive = false;
                self.players[victim].respawn_ticks = RESPAWN_TICKS;
                self.players[victim].charge = 0;
                self.players[victim].reload_ticks = 0;
                self.damage_history.retain(|h| h.victim != victim);
                self.events.push(Event::Death {
                    victim,
                    killer,
                    awards,
                });
            }
        }
        self.update_objectives();
        self.tick += 1;
        let active = (0..self.players.len())
            .filter(|&s| !self.exhausted(s))
            .count();
        let team_eliminated = self.config.mode.team()
            && (0..2).any(|t| {
                !(0..self.players.len()).any(|s| self.players[s].team == t && !self.exhausted(s))
            });
        if self.tick >= self.config.max_ticks
            || (!self.config.offline && (active < 2 || team_eliminated))
            || self.score.iter().any(|&s| s >= 18000)
            || self.payload_progress >= 36000
        {
            self.terminal = true;
            self.events.push(Event::Terminal);
        }
        debug_assert!(economy::conserved(&self.accounts));
        Ok(())
    }

    fn ability(&mut self, slot: usize) {
        let class = self.players[slot].class;
        self.players[slot].ability_cooldown = 600;
        if class == 5 {
            let origin = self.players[slot].position;
            let team = self.players[slot].team;
            for (other, p) in self.players.iter_mut().enumerate() {
                if p.alive
                    && (other == slot || (self.config.mode.team() && p.team == team))
                    && p.position.distance_squared(origin) <= 6000_i64 * 6000
                {
                    p.health = (p.health + 35).min(catalog::CLASSES[p.class as usize].health);
                }
            }
        } else if class == 1 {
            let old = self.players[slot].position;
            let to = old.offset(math::scale_q15(
                math::direction(self.players[slot].yaw, 0),
                2000,
            ));
            self.players[slot].position = self.safe_motion(old, to);
        } else {
            self.players[slot].stamina = 100;
        }
    }

    fn update_objectives(&mut self) {
        if !self.config.mode.team() {
            return;
        }
        let center = if self.config.mode == Mode::Payload {
            Vec3::new(-18000 + self.payload_progress, 0, 0)
        } else {
            Vec3::default()
        };
        let mut count = [0u32; 2];
        for p in &self.players {
            if p.alive && p.position.distance_squared(center) <= 3500_i64 * 3500 {
                count[p.team as usize] += 1;
            }
        }
        if self.config.mode == Mode::Control {
            if count[0] > 0 && count[1] == 0 {
                self.control_progress = (self.control_progress - 1).max(-180);
            } else if count[1] > 0 && count[0] == 0 {
                self.control_progress = (self.control_progress + 1).min(180);
            }
            if self.control_progress == -180 {
                self.control_owner = Some(0);
            }
            if self.control_progress == 180 {
                self.control_owner = Some(1);
            }
            if let Some(t) = self.control_owner {
                self.score[t as usize] += 1;
            }
        } else if count[0] > 0 && count[1] == 0 {
            self.payload_progress = (self.payload_progress + 5).min(36000);
        }
    }

    /// Frozen offline replay fingerprint. Native envelopes use canonical Norito.
    /// This digest is not an execution proof or authenticated ledger statement.
    pub fn state_hash(&self) -> [u8; 32] {
        let mut h = Sha256::new();
        h.update(b"sora-arena:reference-state:v1\0");
        h.update(crate::RULES_VERSION.as_bytes());
        h.update([
            self.config.mode as u8,
            self.config.map,
            self.config.offline as u8,
        ]);
        h.update(self.config.max_ticks.to_le_bytes());
        h.update(self.config.base_bond.to_le_bytes());
        h.update(self.tick.to_le_bytes());
        h.update([self.terminal as u8]);
        h.update((self.players.len() as u32).to_le_bytes());
        for (p, a) in self.players.iter().zip(&self.accounts) {
            h.update([
                p.team,
                p.class,
                p.weapon,
                p.alive as u8,
                p.guarding as u8,
                p.admitted_special as u8,
            ]);
            for n in [
                p.position.x,
                p.position.y,
                p.position.z,
                p.velocity_z,
                p.health,
                p.stamina,
            ] {
                h.update(n.to_le_bytes());
            }
            h.update(p.yaw.to_le_bytes());
            h.update(p.pitch.to_le_bytes());
            h.update(p.respawn_ticks.to_le_bytes());
            for n in [
                p.attack_cooldown,
                p.ability_cooldown,
                p.charge,
                p.ammo,
                p.reload_ticks,
                p.guard_ticks,
                p.spawn_protection,
            ] {
                h.update(n.to_le_bytes());
            }
            for n in [a.initial, a.remaining, a.earnings] {
                h.update(n.to_le_bytes());
            }
            for n in [a.kills, a.deaths, a.paid_deaths] {
                h.update(n.to_le_bytes());
            }
        }
        h.update((self.projectiles.len() as u32).to_le_bytes());
        for p in &self.projectiles {
            h.update(p.id.to_le_bytes());
            h.update((p.owner as u32).to_le_bytes());
            h.update([p.weapon]);
            for n in [
                p.position.x,
                p.position.y,
                p.position.z,
                p.velocity.x,
                p.velocity.y,
                p.velocity.z,
                p.traveled,
            ] {
                h.update(n.to_le_bytes());
            }
            h.update(p.age.to_le_bytes());
        }
        h.update((self.damage_history.len() as u32).to_le_bytes());
        for d in &self.damage_history {
            for n in [d.tick, d.attacker as u32, d.victim as u32, d.damage] {
                h.update(n.to_le_bytes());
            }
        }
        for n in self.score {
            h.update(n.to_le_bytes());
        }
        h.update([self.control_owner.unwrap_or(255)]);
        h.update(self.control_progress.to_le_bytes());
        h.update(self.payload_progress.to_le_bytes());
        h.update((self.walls.len() as u32).to_le_bytes());
        for w in &self.walls {
            for n in [w.min.x, w.min.y, w.min.z, w.max.x, w.max.y, w.max.z] {
                h.update(n.to_le_bytes());
            }
        }
        h.finalize().into()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn duel() -> World {
        World::new(
            Config {
                mode: Mode::FreeForAll,
                map: 0,
                max_ticks: 36000,
                base_bond: 1000,
                offline: false,
            },
            &[
                Participant {
                    team: 0,
                    class: 0,
                    weapon: 1,
                    bond: 1000,
                    special_entitled: false,
                },
                Participant {
                    team: 1,
                    class: 0,
                    weapon: 1,
                    bond: 1000,
                    special_entitled: false,
                },
            ],
        )
        .unwrap()
    }
    #[test]
    fn simultaneous_exhaustion_preserves_same_tick_team_awards() {
        let roster = (0..4)
            .map(|slot| Participant {
                team: slot / 2,
                class: 0,
                weapon: 1,
                bond: 1000,
                special_entitled: false,
            })
            .collect::<Vec<_>>();
        let mut w = World::new(
            Config {
                mode: Mode::Control,
                map: 0,
                max_ticks: 600,
                base_bond: 1000,
                offline: false,
            },
            &roster,
        )
        .unwrap();
        for (slot, (x, y)) in [(-1000, 0), (-1000, 2000), (0, 0), (0, 2000)]
            .into_iter()
            .enumerate()
        {
            w.players[slot].position = Vec3::new(x, y, 0);
        }
        w.players[0].health = 1;
        w.players[3].health = 1;
        w.accounts[0].remaining = 100;
        w.accounts[0].paid_deaths = 9;
        w.accounts[2].earnings = 900;
        w.step(&[
            Input::default(),
            Input {
                buttons: FIRE,
                ..Input::default()
            },
            Input {
                buttons: FIRE,
                yaw: 32768,
                ..Input::default()
            },
            Input::default(),
        ])
        .unwrap();
        assert!(w.exhausted(0));
        assert_eq!(w.accounts[0].earnings, 40);
        assert_eq!(w.accounts[1].earnings, 60);
        assert_eq!(w.accounts[3].earnings, 40);
        assert!(!w.players[3].alive);
        assert!(economy::conserved(&w.accounts));
    }
    #[test]
    fn legal_shots_derive_death_and_payout() {
        let mut w = duel();
        w.players[0].position = Vec3::new(0, 0, 0);
        w.players[1].position = Vec3::new(5000, 0, 0);
        let i = [
            Input {
                buttons: FIRE,
                ..Input::default()
            },
            Input::default(),
        ];
        for _ in 0..60 {
            w.step(&i).unwrap();
        }
        assert!(!w.players[1].alive);
        assert_eq!(w.accounts[1].remaining, 900);
        assert_eq!(w.accounts[0].earnings, 100);
    }
    #[test]
    fn walls_stop_damage() {
        let mut w = duel();
        w.players[0].position = Vec3::new(4000, 0, 0);
        w.players[1].position = Vec3::new(10000, 0, 0);
        for _ in 0..120 {
            w.step(&[
                Input {
                    buttons: FIRE,
                    ..Input::default()
                },
                Input::default(),
            ])
            .unwrap();
        }
        assert_eq!(w.players[1].health, 125);
    }
    #[test]
    fn invalid_input_is_transactional() {
        let mut w = duel();
        let hash = w.state_hash();
        assert!(
            w.step(&[
                Input {
                    move_x: 128,
                    ..Input::default()
                },
                Input::default()
            ])
            .is_err()
        );
        assert_eq!(hash, w.state_hash());
    }
    #[test]
    fn identical_inputs_produce_identical_replays() {
        let mut a = duel();
        let mut b = a.clone();
        for t in 0..600 {
            let input = [
                Input {
                    buttons: if t % 11 == 0 { FIRE } else { 0 },
                    move_x: 80,
                    yaw: (t * 93) as u16,
                    ..Input::default()
                },
                Input {
                    move_y: -80,
                    yaw: (t * 77) as u16,
                    ..Input::default()
                },
            ];
            a.step(&input).unwrap();
            b.step(&input).unwrap();
            assert_eq!(a.state_hash(), b.state_hash());
        }
    }
    #[test]
    fn nft_or_double_bond_access() {
        let c = Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 10,
            base_bond: 1000,
            offline: false,
        };
        let mut p = Participant {
            team: 0,
            class: 0,
            weapon: 12,
            bond: 1000,
            special_entitled: false,
        };
        assert!(World::new(c.clone(), &[p.clone()]).is_err());
        p.bond = 2000;
        assert!(World::new(c.clone(), &[p.clone()]).is_ok());
        p.bond = 1000;
        p.special_entitled = true;
        assert!(World::new(c, &[p]).is_ok());
    }
    #[test]
    fn friendly_fire_is_disabled() {
        let mut w = duel();
        w.config.mode = Mode::Control;
        w.players[0].team = 0;
        w.players[1].team = 0;
        w.config.offline = true;
        w.players[0].position = Vec3::default();
        w.players[1].position = Vec3::new(3000, 0, 0);
        for _ in 0..60 {
            w.step(&[
                Input {
                    buttons: FIRE,
                    ..Input::default()
                },
                Input::default(),
            ])
            .unwrap();
        }
        assert_eq!(w.players[1].health, 125);
    }
    #[test]
    fn every_control_roundtrips() {
        for b in 0..64 {
            let i = Input {
                buttons: b,
                move_x: -127,
                move_y: 127,
                yaw: 65535,
                pitch: -16384,
            };
            assert_eq!(Input::decode(i.encode()).unwrap(), i);
        }
    }
}
