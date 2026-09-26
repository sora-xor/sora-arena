//! Control and Payload objectives and the match result (docs/combat-rules.md
//! §8). Only living players count; exhausted players never respawn.
use super::{Event, Mode, World};
use crate::math::Vec3;

/// Objectives are inactive on ticks 0-599: no progress, idle count or score.
pub const OBJECTIVE_UNLOCK_TICK: u32 = 600;
/// Control progress units that capture the point (§8.1).
pub const CONTROL_CAPTURE: i32 = 480;
/// Owned ticks that win Control once the point is secured (3 minutes).
pub const CONTROL_TARGET: u32 = 10_800;
/// Attackers and defenders count within this horizontal distance (§8.2).
pub const PAYLOAD_PUSH_RADIUS: i32 = 3000;
/// Idle ticks after which the payload rolls back.
pub const PAYLOAD_ROLLBACK_DELAY: u16 = 900;
/// Push speed in mm per tick for 0, 1, 2 and 3+ uncontested attackers.
const PAYLOAD_PUSH: [i32; 4] = [0, 6, 8, 10];
const PAYLOAD_ROLLBACK: i32 = 4;

/// The fixed result of a terminal match (§8.4).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Winner {
    Team(u8),
    Slot(usize),
    Draw,
}

impl World {
    /// §2 phase 13. Returns true when the Control owner has met the target
    /// and secured the point on this tick.
    pub(super) fn update_objectives(&mut self) -> bool {
        if self.tick < OBJECTIVE_UNLOCK_TICK {
            return false;
        }
        match self.config.mode {
            Mode::Control => self.update_control(),
            Mode::Payload => {
                self.update_payload();
                false
            }
            Mode::FreeForAll | Mode::Melee => false,
        }
    }

    /// Living players of each team within `radius` of `centre`, horizontally.
    pub fn count_near(&self, centre: Vec3, radius: i32) -> [i32; 2] {
        let mut count = [0; 2];
        for p in &self.players {
            if p.alive
                && p.position.horizontal_distance_squared(centre)
                    <= i64::from(radius) * i64::from(radius)
            {
                count[usize::from(p.team)] += 1;
            }
        }
        count
    }

    /// §8.1 king of the hill. Negative progress favours team 0.
    fn update_control(&mut self) -> bool {
        let point = self.arena().control;
        let [n0, n1] = self.count_near(Vec3::new(point.x, point.y, 0), point.radius);
        let contested = n0 > 0 && n1 > 0;
        let full = |team: u8| {
            if team == 0 {
                -CONTROL_CAPTURE
            } else {
                CONTROL_CAPTURE
            }
        };
        match (n0 > 0, n1 > 0) {
            (true, false) => {
                self.control_progress = (self.control_progress - n0.min(3)).max(-CONTROL_CAPTURE);
            }
            (false, true) => {
                self.control_progress = (self.control_progress + n1.min(3)).min(CONTROL_CAPTURE);
            }
            (false, false) => {
                // An empty point decays toward the owner's full value, or 0.
                let rest = self.control_owner.map_or(0, full);
                self.control_progress += (rest - self.control_progress).signum();
            }
            // Contested: progress holds.
            (true, true) => {}
        }
        let owner = match self.control_progress {
            p if p == -CONTROL_CAPTURE => Some(0),
            p if p == CONTROL_CAPTURE => Some(1),
            _ => self.control_owner,
        };
        if owner != self.control_owner
            && let Some(team) = owner
        {
            self.control_owner = owner;
            self.events.push(Event::ObjectiveCaptured { team });
        }
        let Some(owner) = self.control_owner else {
            return false;
        };
        let score = &mut self.score[usize::from(owner)];
        *score = (*score + 1).min(CONTROL_TARGET);
        if *score < CONTROL_TARGET {
            return false;
        }
        if !contested && self.control_progress == full(owner) {
            return true;
        }
        if !self.overtime {
            self.overtime = true;
            self.events.push(Event::OvertimeStarted);
        }
        false
    }

    /// §8.2 escort: team 0 pushes the payload along the arena route.
    fn update_payload(&mut self) {
        let arena = self.arena();
        let at = arena.route_point(self.payload_progress);
        let [attackers, defenders] = self.count_near(at, PAYLOAD_PUSH_RADIUS);
        if attackers > 0 {
            self.payload_idle = 0;
            if defenders == 0 {
                self.payload_progress = (self.payload_progress
                    + PAYLOAD_PUSH[attackers.min(3) as usize])
                    .min(arena.route_length());
            }
        } else {
            self.payload_idle = self.payload_idle.saturating_add(1);
            if self.payload_idle >= PAYLOAD_ROLLBACK_DELAY {
                // Never below the last checkpoint reached.
                let floor = match self.payload_checkpoints {
                    0 => 0,
                    passed => arena.checkpoints[usize::from(passed) - 1],
                };
                self.payload_progress = (self.payload_progress - PAYLOAD_ROLLBACK).max(floor);
            }
        }
        while let Some(&checkpoint) = arena.checkpoints.get(usize::from(self.payload_checkpoints))
            && self.payload_progress >= checkpoint
        {
            self.events.push(Event::CheckpointReached {
                index: self.payload_checkpoints,
            });
            self.payload_checkpoints += 1;
        }
    }

    /// §8.4: after the clock advances, the first matching rule fixes the
    /// result. `secured` is this tick's Control win condition.
    pub(super) fn result(&self, secured: bool) -> Option<Winner> {
        let mode = self.config.mode;
        if mode == Mode::Payload && self.payload_progress >= self.arena().route_length() {
            return Some(Winner::Team(0));
        }
        if secured {
            return self.control_owner.map(Winner::Team);
        }
        let staked = !self.config.offline;
        let holding = |team: Option<u8>| {
            (0..self.players.len())
                .filter(|&slot| team.is_none_or(|team| self.players[slot].team == team))
                .filter(|&slot| !self.exhausted(slot))
                .count()
        };
        if staked && mode.team() {
            match (holding(Some(0)) > 0, holding(Some(1)) > 0) {
                (true, true) => {}
                (true, false) => return Some(Winner::Team(0)),
                (false, true) => return Some(Winner::Team(1)),
                (false, false) => return Some(Winner::Draw),
            }
        }
        if staked && !mode.team() && holding(None) < 2 {
            return Some(self.most_kills());
        }
        if self.tick == self.config.max_ticks {
            return Some(match mode {
                Mode::Control => match self.score[0].cmp(&self.score[1]) {
                    std::cmp::Ordering::Greater => Winner::Team(0),
                    std::cmp::Ordering::Less => Winner::Team(1),
                    std::cmp::Ordering::Equal => Winner::Draw,
                },
                Mode::Payload => Winner::Team(1),
                Mode::FreeForAll | Mode::Melee => self.most_kills(),
            });
        }
        None
    }

    /// §8.3: the unique participant with the most credited kills; ties go to
    /// the fewest deaths, and a remaining tie is a draw.
    fn most_kills(&self) -> Winner {
        let kills = self.accounts.iter().map(|a| a.kills).max().unwrap_or(0);
        let deaths = self
            .accounts
            .iter()
            .filter(|a| a.kills == kills)
            .map(|a| a.deaths)
            .min()
            .unwrap_or(0);
        let mut best = self
            .accounts
            .iter()
            .enumerate()
            .filter(|(_, a)| a.kills == kills && a.deaths == deaths)
            .map(|(slot, _)| slot);
        match (best.next(), best.next()) {
            (Some(slot), None) => Winner::Slot(slot),
            _ => Winner::Draw,
        }
    }
}
