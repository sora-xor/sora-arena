//! Control and Payload objectives and the match result
//! (docs/combat-rules.md §8), driven through `World::step`.
use arena_core::{
    maps::ARENAS,
    math::Vec3,
    simulation::{
        CONTROL_CAPTURE, CONTROL_TARGET, Config, Event, Input, MELEE, Mode, OBJECTIVE_UNLOCK_TICK,
        PAYLOAD_PUSH_RADIUS, PAYLOAD_ROLLBACK_DELAY, Participant, Winner, World,
    },
};

/// Six players per team; slots alternate teams (even slots are team 0).
fn world(mode: Mode, map: u8, max_ticks: u32) -> World {
    let roster = (0..12)
        .map(|slot| Participant {
            team: (slot % 2) as u8,
            class: 0,
            weapon: 0,
            bond: 0,
            special_entitled: false,
        })
        .collect::<Vec<_>>();
    World::new(
        Config {
            mode,
            map,
            max_ticks,
            base_bond: 0,
            offline: true,
        },
        &roster,
    )
    .unwrap()
}

const IDLE: [Input; 12] = [Input {
    buttons: 0,
    move_x: 0,
    move_y: 0,
    yaw: 0,
    pitch: 0,
}; 12];

/// Put `count` players of `team` at `at` (others stay at their spawns).
fn place(w: &mut World, team: u8, count: usize, at: Vec3) {
    let slots = (0..12).filter(|slot| slot % 2 == usize::from(team));
    for slot in slots.clone().take(count) {
        w.players[slot].position = at;
    }
}

fn step(w: &mut World) -> Vec<Event> {
    w.step(&IDLE).unwrap();
    w.events.clone()
}

#[test]
fn control_is_locked_before_tick_600_then_captures_at_up_to_three_units() {
    for (cappers, ticks) in [(1, 480), (2, 240), (3, 160), (6, 160)] {
        let mut w = world(Mode::Control, 0, 36_000);
        place(&mut w, 1, cappers, Vec3::new(1000, -1000, 0));
        for _ in 0..OBJECTIVE_UNLOCK_TICK {
            assert!(step(&mut w).is_empty());
        }
        assert_eq!((w.control_progress, w.score), (0, [0, 0]));
        for tick in 1..=ticks {
            let events = step(&mut w);
            if tick < ticks {
                assert!(events.is_empty());
                assert_eq!(w.control_owner, None);
            } else {
                assert_eq!(events, vec![Event::ObjectiveCaptured { team: 1 }]);
            }
        }
        assert_eq!(
            (w.control_progress, w.control_owner),
            (CONTROL_CAPTURE, Some(1))
        );
        // The capturing tick already scores.
        assert_eq!(w.score, [0, 1]);
    }
}

#[test]
fn contest_holds_progress_and_an_empty_point_decays_toward_its_owner() {
    let mut w = world(Mode::Control, 1, 36_000);
    w.tick = OBJECTIVE_UNLOCK_TICK;
    place(&mut w, 0, 2, Vec3::new(0, 3000, 0));
    for _ in 0..100 {
        step(&mut w);
    }
    assert_eq!(w.control_progress, -200);
    // One defender on the edge of the 3500 mm radius contests.
    place(&mut w, 1, 1, Vec3::new(3500, 0, 0));
    for _ in 0..50 {
        step(&mut w);
    }
    assert_eq!(w.control_progress, -200);
    // 1 mm outside the radius does not count.
    place(&mut w, 1, 1, Vec3::new(3501, 0, 0));
    step(&mut w);
    assert_eq!(w.control_progress, -202);
    // An unowned empty point decays toward zero.
    place(&mut w, 0, 2, Vec3::new(-19_000, 0, 0));
    for _ in 0..10 {
        step(&mut w);
    }
    assert_eq!((w.control_progress, w.control_owner), (-192, None));
    // An owned empty point returns to its owner's full value, even after
    // the other team moved it.
    w.control_owner = Some(1);
    w.control_progress = -10;
    for _ in 0..(10 + CONTROL_CAPTURE) {
        step(&mut w);
    }
    assert_eq!(w.control_progress, CONTROL_CAPTURE);
    assert_eq!(w.control_owner, Some(1));
}

#[test]
fn flipping_takes_twice_the_threshold_and_the_owner_scores_while_contested() {
    let mut w = world(Mode::Control, 2, 36_000);
    w.tick = OBJECTIVE_UNLOCK_TICK;
    w.control_owner = Some(1);
    w.control_progress = CONTROL_CAPTURE;
    place(&mut w, 0, 3, Vec3::default());
    let mut captured = None;
    for tick in 1..=2 * CONTROL_CAPTURE / 3 {
        if step(&mut w).contains(&Event::ObjectiveCaptured { team: 0 }) {
            captured = Some(tick);
        }
    }
    assert_eq!(captured, Some(2 * CONTROL_CAPTURE / 3));
    assert_eq!(
        (w.control_owner, w.control_progress),
        (Some(0), -CONTROL_CAPTURE)
    );
    // Team 1 owned the point for every tick but the last.
    assert_eq!(w.score, [1, 2 * CONTROL_CAPTURE as u32 / 3 - 1]);
    place(&mut w, 1, 1, Vec3::default());
    for _ in 0..30 {
        step(&mut w);
    }
    assert_eq!(w.control_progress, -CONTROL_CAPTURE);
    assert_eq!(w.score[0], 31);
}

#[test]
fn a_secured_point_at_the_target_wins_and_a_contested_one_goes_to_overtime() {
    // Uncontested at the target: the owner wins that tick.
    let mut w = world(Mode::Control, 3, 36_000);
    w.tick = 20_000;
    w.control_owner = Some(0);
    w.control_progress = -CONTROL_CAPTURE;
    w.score = [CONTROL_TARGET - 1, 5];
    let events = step(&mut w);
    assert_eq!(
        events,
        vec![
            Event::MatchWinner {
                winner: Winner::Team(0)
            },
            Event::Terminal
        ]
    );
    assert_eq!(
        (w.winner, w.overtime, w.score[0]),
        (Some(Winner::Team(0)), false, CONTROL_TARGET)
    );
    assert!(w.step(&IDLE).is_err());

    // Contested at the target: overtime, announced once, until secured.
    let mut w = world(Mode::Control, 3, 36_000);
    w.tick = 20_000;
    w.control_owner = Some(0);
    w.control_progress = -CONTROL_CAPTURE;
    w.score = [CONTROL_TARGET - 1, 5];
    place(&mut w, 0, 1, Vec3::default());
    place(&mut w, 1, 1, Vec3::new(1000, 0, 0));
    assert_eq!(step(&mut w), vec![Event::OvertimeStarted]);
    for _ in 0..100 {
        assert!(step(&mut w).is_empty());
    }
    assert!(w.overtime && !w.terminal);
    assert_eq!(w.score[0], CONTROL_TARGET);
    // Team 1 alone flips the point during overtime and keeps scoring.
    place(&mut w, 0, 1, Vec3::new(-19_000, 0, 0));
    place(&mut w, 1, 3, Vec3::default());
    let mut flipped = false;
    for _ in 0..2 * CONTROL_CAPTURE / 3 {
        let events = step(&mut w);
        flipped |= events.contains(&Event::ObjectiveCaptured { team: 1 });
        assert!(!events.contains(&Event::OvertimeStarted));
    }
    assert!(flipped && !w.terminal);
    assert_eq!(w.control_owner, Some(1));
    let before = w.score[1];
    step(&mut w);
    assert_eq!(w.score, [CONTROL_TARGET, before + 1]);
    // Team 0 retakes it; the first uncontested full-value tick wins.
    place(&mut w, 1, 6, Vec3::new(19_000, 0, 0));
    place(&mut w, 0, 3, Vec3::default());
    let mut ticks = 0;
    while !w.terminal {
        step(&mut w);
        ticks += 1;
    }
    assert_eq!(ticks, 2 * CONTROL_CAPTURE / 3);
    assert_eq!(w.winner, Some(Winner::Team(0)));
    assert_eq!(w.control_progress, -CONTROL_CAPTURE);
}

#[test]
fn control_at_the_clock_limit_goes_to_the_higher_score_or_a_draw() {
    for (score, winner) in [
        ([7, 6], Winner::Team(0)),
        ([6, 7], Winner::Team(1)),
        ([7, 7], Winner::Draw),
    ] {
        let mut w = world(Mode::Control, 0, 700);
        w.tick = 699;
        w.score = score;
        let events = step(&mut w);
        assert_eq!(events, vec![Event::MatchWinner { winner }, Event::Terminal]);
        assert_eq!((w.tick, w.winner), (700, Some(winner)));
    }
    // Overtime never extends the match past max_ticks.
    let mut w = world(Mode::Control, 0, 20_001);
    w.tick = 20_000;
    w.control_owner = Some(1);
    w.control_progress = CONTROL_CAPTURE;
    w.score = [0, CONTROL_TARGET - 1];
    place(&mut w, 0, 1, Vec3::default());
    place(&mut w, 1, 1, Vec3::default());
    assert_eq!(
        step(&mut w),
        vec![
            Event::OvertimeStarted,
            Event::MatchWinner {
                winner: Winner::Team(1)
            },
            Event::Terminal
        ]
    );
}

/// Idle inputs, except one katana strike by `slot` toward `yaw`.
fn strike(slot: usize, yaw: u16) -> [Input; 12] {
    let mut inputs = IDLE;
    inputs[slot] = Input {
        buttons: MELEE,
        yaw,
        ..Input::default()
    };
    inputs
}

#[test]
fn a_body_left_on_the_point_neither_captures_nor_contests() {
    // A dead body keeps its position until it respawns 480 ticks later.
    let mut w = world(Mode::Control, 0, 36_000);
    w.tick = OBJECTIVE_UNLOCK_TICK;
    w.players[1].position = Vec3::new(0, 3000, 0);
    for _ in 0..10 {
        step(&mut w);
    }
    assert_eq!(w.control_progress, 10);
    w.players[0].position = Vec3::new(0, 1000, 0);
    step(&mut w);
    assert_eq!(w.control_progress, 10);
    // Slot 0 kills the team 1 capper where it stands. Team 0 holds the point
    // alone from that same tick.
    w.players[1].health = 1;
    w.step(&strike(0, 16384)).unwrap();
    assert!(!w.players[1].alive);
    assert_eq!(w.players[1].position, Vec3::new(0, 3000, 0));
    assert_eq!(w.control_progress, 9);
    for _ in 0..20 {
        step(&mut w);
    }
    assert_eq!(w.control_progress, -11);
    // Slot 3 strikes from off the point and kills slot 0 on it. With both
    // bodies on the point and no one alive there, progress decays toward 0.
    w.players[0].position = Vec3::new(0, 3500, 0);
    w.players[0].health = 1;
    w.players[3].position = Vec3::new(0, 5700, 0);
    w.step(&strike(3, 49152)).unwrap();
    assert!(!w.players[0].alive);
    assert_eq!(w.players[0].position, Vec3::new(0, 3500, 0));
    assert_eq!(w.control_progress, -10);
    for _ in 0..10 {
        step(&mut w);
    }
    assert_eq!((w.control_progress, w.control_owner), (0, None));
}

#[test]
fn a_body_beside_the_payload_neither_contests_nor_pushes() {
    let start = ARENAS[0].route_point(0);
    let mut w = world(Mode::Payload, 0, 36_000);
    w.tick = OBJECTIVE_UNLOCK_TICK;
    place(&mut w, 0, 6, BENCH);
    place(&mut w, 1, 6, BENCH);
    w.players[0].position = start;
    w.players[1].position = start.offset(Vec3::new(2000, 0, 0));
    step(&mut w);
    assert_eq!((w.payload_progress, w.payload_idle), (0, 0));
    // The attacker kills the contesting defender: it pushes on that tick.
    w.players[1].health = 1;
    w.step(&strike(0, 0)).unwrap();
    assert!(!w.players[1].alive);
    assert_eq!(w.players[1].position, start.offset(Vec3::new(2000, 0, 0)));
    assert_eq!(w.payload_progress, 6);
    // A defender outside the push radius kills the attacker inside it: the
    // payload stops and idles.
    w.players[0].position = start.offset(Vec3::new(0, 2800, 0));
    w.players[0].health = 1;
    w.players[3].position = start.offset(Vec3::new(0, 5000, 0));
    w.step(&strike(3, 49152)).unwrap();
    assert!(!w.players[0].alive);
    assert_eq!((w.payload_progress, w.payload_idle), (6, 1));
    for _ in 0..10 {
        step(&mut w);
    }
    assert_eq!((w.payload_progress, w.payload_idle), (6, 11));
}

/// A corner of the arena far from every route, control point and spawn.
const BENCH: Vec3 = Vec3::new(0, -15_000, 0);

#[test]
fn payload_push_speed_contest_rollback_and_checkpoint_floor() {
    let arena = &ARENAS[0];
    let start = arena.route_point(0);
    for (pushers, speed) in [(1, 6), (2, 8), (3, 10), (6, 10)] {
        let mut w = world(Mode::Payload, 0, 36_000);
        place(&mut w, 0, 6, BENCH);
        place(&mut w, 0, pushers, start);
        for _ in 0..OBJECTIVE_UNLOCK_TICK {
            step(&mut w);
        }
        assert_eq!((w.payload_progress, w.payload_idle), (0, 0));
        step(&mut w);
        assert_eq!(w.payload_progress, speed);
    }
    // An attacker exactly on the push radius counts; 1 mm beyond does not.
    for (offset, progress, idle) in [(PAYLOAD_PUSH_RADIUS, 6, 0), (PAYLOAD_PUSH_RADIUS + 1, 0, 1)] {
        let mut w = world(Mode::Payload, 0, 36_000);
        w.tick = OBJECTIVE_UNLOCK_TICK;
        place(&mut w, 0, 6, BENCH);
        place(&mut w, 0, 1, start.offset(Vec3::new(0, offset, 0)));
        step(&mut w);
        assert_eq!((w.payload_progress, w.payload_idle), (progress, idle));
    }
    // Passing a checkpoint is announced once and becomes the rollback floor.
    let mut w = world(Mode::Payload, 0, 36_000);
    w.tick = OBJECTIVE_UNLOCK_TICK;
    w.payload_progress = 15_990;
    place(&mut w, 0, 6, BENCH);
    place(&mut w, 0, 1, arena.route_point(15_990));
    assert_eq!(step(&mut w), vec![]);
    assert_eq!(w.payload_progress, 15_996);
    assert_eq!(step(&mut w), vec![Event::CheckpointReached { index: 0 }]);
    assert_eq!((w.payload_progress, w.payload_checkpoints), (16_002, 1));
    // A defender in range stops the push and resets the idle count.
    place(&mut w, 1, 1, arena.route_point(16_002));
    w.payload_idle = 17;
    assert_eq!(step(&mut w), vec![]);
    assert_eq!((w.payload_progress, w.payload_idle), (16_002, 0));
    // Everyone leaves: 900 idle ticks, then 4 mm a tick back to the floor.
    place(&mut w, 0, 6, BENCH);
    place(&mut w, 1, 6, BENCH);
    for _ in 1..PAYLOAD_ROLLBACK_DELAY {
        step(&mut w);
    }
    assert_eq!(
        (w.payload_progress, w.payload_idle),
        (16_002, PAYLOAD_ROLLBACK_DELAY - 1)
    );
    step(&mut w);
    assert_eq!(w.payload_progress, 16_000);
    for _ in 0..100 {
        assert_eq!(step(&mut w), vec![]);
    }
    assert_eq!((w.payload_progress, w.payload_checkpoints), (16_000, 1));
    assert_eq!(w.payload_idle, PAYLOAD_ROLLBACK_DELAY + 100);
    // Below the first checkpoint the floor is the route start.
    let mut w = world(Mode::Payload, 0, 36_000);
    w.tick = OBJECTIVE_UNLOCK_TICK;
    w.payload_progress = 6;
    w.payload_idle = PAYLOAD_ROLLBACK_DELAY;
    place(&mut w, 0, 6, BENCH);
    step(&mut w);
    assert_eq!(w.payload_progress, 2);
    step(&mut w);
    assert_eq!(w.payload_progress, 0);
    // The idle count saturates.
    w.payload_idle = u16::MAX;
    step(&mut w);
    assert_eq!(w.payload_idle, u16::MAX);
}

/// Real movement: three attackers walk the route just ahead of the payload,
/// turning only along the axis-aligned route, until it reaches the end.
#[test]
fn attackers_escort_the_payload_to_victory_on_every_arena() {
    for (map, arena) in ARENAS.iter().enumerate() {
        let mut w = world(Mode::Payload, map as u8, 36_000);
        let start = arena.route_point(0);
        let attackers = [0, 2, 4];
        place(&mut w, 0, 6, BENCH);
        place(&mut w, 1, 6, BENCH);
        for slot in attackers {
            w.players[slot].position = start;
        }
        let length = arena.route_length();
        let mut reached = Vec::new();
        let burning = |p: Vec3| {
            arena.hazards.iter().any(|h| {
                (h.volume.min.x..=h.volume.max.x).contains(&p.x)
                    && (h.volume.min.y..=h.volume.max.y).contains(&p.y)
            })
        };
        while !w.terminal {
            // Lead the payload by 800 mm, or wait just past a hazard such as
            // Silk Foundry's slag channel instead of standing in it.
            let lead = (800..=2800)
                .step_by(100)
                .find(|lead| !burning(arena.route_point(w.payload_progress + lead)))
                .unwrap();
            let target = arena.route_point(w.payload_progress + lead);
            let mut inputs = IDLE;
            for slot in attackers {
                let p = w.players[slot].position;
                let (dx, dy) = (target.x - p.x, target.y - p.y);
                // Walk one axis at a time toward a point on the route, at
                // most the remaining distance, so bodies stay on the line.
                let (yaw, distance) = if dx.abs() >= dy.abs() {
                    (if dx >= 0 { 0 } else { 32768 }, dx.abs())
                } else {
                    (if dy >= 0 { 16384 } else { 49152 }, dy.abs())
                };
                inputs[slot] = Input {
                    move_x: (distance.min(80) * 127 / 80) as i16,
                    yaw,
                    ..Input::default()
                };
            }
            w.step(&inputs).unwrap();
            for event in &w.events {
                if let Event::CheckpointReached { index } = event {
                    reached.push((*index, w.payload_progress));
                }
            }
            assert!(w.tick < 36_000, "{} payload stalled", arena.slug);
        }
        assert_eq!(w.winner, Some(Winner::Team(0)), "{}", arena.slug);
        assert_eq!(w.payload_progress, length);
        assert_eq!(
            reached.iter().map(|(index, _)| *index).collect::<Vec<_>>(),
            [0, 1, 2]
        );
        for ((_, progress), checkpoint) in reached.iter().zip(arena.checkpoints) {
            assert!((checkpoint..checkpoint + 10).contains(progress));
        }
        // Three pushers at 10 mm a tick from the unlock.
        assert_eq!(
            w.tick,
            OBJECTIVE_UNLOCK_TICK + (length as u32).div_ceil(10),
            "{}",
            arena.slug
        );
        assert!(matches!(
            w.events.as_slice(),
            [
                ..,
                Event::MatchWinner {
                    winner: Winner::Team(0)
                },
                Event::Terminal
            ]
        ));
    }
}

#[test]
fn defenders_win_payload_at_the_clock_limit() {
    let arena = &ARENAS[2];
    let mut w = world(Mode::Payload, 2, 4000);
    let start = arena.route_point(0);
    place(&mut w, 1, 6, BENCH);
    place(&mut w, 0, 6, start);
    // One defender stands on the payload from the unlock onward.
    place(&mut w, 1, 1, start.offset(Vec3::new(1000, 0, 0)));
    while !w.terminal {
        step(&mut w);
    }
    assert_eq!((w.tick, w.payload_progress), (4000, 0));
    assert_eq!(w.winner, Some(Winner::Team(1)));
    // Pushed most of the way, the attackers still lose at the limit.
    let mut w = world(Mode::Payload, 2, 700);
    w.tick = 699;
    w.payload_progress = arena.route_length() - 11;
    w.payload_checkpoints = 3;
    place(&mut w, 1, 6, BENCH);
    let at = arena.route_point(w.payload_progress);
    place(&mut w, 0, 3, at);
    assert_eq!(
        step(&mut w),
        vec![
            Event::MatchWinner {
                winner: Winner::Team(1)
            },
            Event::Terminal
        ]
    );
    assert_eq!(w.payload_progress, arena.route_length() - 1);
    // One more push at the limit completes the route: rule 1 comes first.
    let mut w = world(Mode::Payload, 2, 700);
    w.tick = 699;
    w.payload_progress = arena.route_length() - 10;
    w.payload_checkpoints = 3;
    place(&mut w, 1, 6, BENCH);
    let at = arena.route_point(w.payload_progress);
    place(&mut w, 0, 3, at);
    step(&mut w);
    assert_eq!(w.winner, Some(Winner::Team(0)));
}

#[test]
fn objective_and_result_state_is_part_of_the_state_hash() {
    let base = world(Mode::Payload, 1, 36_000);
    let hash = base.state_hash();
    let changes: [fn(&mut World); 9] = [
        |w| w.score[1] = 1,
        |w| w.control_owner = Some(0),
        |w| w.control_progress = 1,
        |w| w.overtime = true,
        |w| w.payload_progress = 1,
        |w| w.payload_checkpoints = 1,
        |w| w.payload_idle = 1,
        |w| w.winner = Some(Winner::Draw),
        |w| w.winner = Some(Winner::Slot(0)),
    ];
    let mut seen = vec![hash];
    for change in changes {
        let mut w = base.clone();
        change(&mut w);
        let changed = w.state_hash();
        assert!(!seen.contains(&changed));
        seen.push(changed);
    }
    let mut team = base.clone();
    team.winner = Some(Winner::Team(0));
    let mut slot = base.clone();
    slot.winner = Some(Winner::Slot(0));
    assert_ne!(team.state_hash(), slot.state_hash());
}

/// Slot 0 (team 0) and slot 1 (team 1) each have one paid death left and
/// face each other with Arc carbines at 1 health.
fn last_lives() -> World {
    let roster = [0, 1].map(|team| Participant {
        team,
        class: 0,
        weapon: 1,
        bond: 1000,
        special_entitled: false,
    });
    let mut w = World::new(
        Config {
            mode: Mode::Control,
            map: 1,
            max_ticks: 36_000,
            base_bond: 1000,
            offline: false,
        },
        &roster,
    )
    .unwrap();
    for (slot, x) in [(0, -3000), (1, 3000)] {
        w.players[slot].position = Vec3::new(x, 0, 0);
        w.players[slot].health = 1;
        w.accounts[slot].remaining = 100;
        w.accounts[slot].paid_deaths = 9;
        w.accounts[1 - slot].earnings = 900;
    }
    w
}

#[test]
fn a_staked_team_match_ends_when_a_team_has_no_reserve_left() {
    let fire = |yaw| Input {
        buttons: arena_core::simulation::FIRE,
        yaw,
        ..Input::default()
    };
    // Team 1's last reserve is spent: team 0 wins on that tick.
    let mut w = last_lives();
    w.step(&[fire(0), Input::default()]).unwrap();
    assert!(w.exhausted(1) && !w.exhausted(0));
    assert_eq!(w.winner, Some(Winner::Team(0)));
    assert!(matches!(
        w.events.as_slice(),
        [
            ..,
            Event::MatchWinner {
                winner: Winner::Team(0)
            },
            Event::Terminal
        ]
    ));
    // Both spend their last reserve in one simultaneous exchange: a draw.
    let mut w = last_lives();
    w.step(&[fire(0), fire(32768)]).unwrap();
    assert!(w.exhausted(0) && w.exhausted(1));
    assert_eq!(w.winner, Some(Winner::Draw));
    assert!(arena_core::economy::conserved(&w.accounts));
}
