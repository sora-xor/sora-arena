//! Headless bot-vs-bot matches on the real kernel. Every mode on every map
//! plays to a terminal state with a winner; bonded runs conserve every bond
//! exactly on every tick; no bot step is ever clipped by a wall, barricade or
//! the arena edge; and each match replays to its checked-in golden. The
//! targeted tests cover team roles at respawn, difficulty tiers, melee
//! defense and the once-per-tick plan.
use arena_bots::{
    Bots,
    Difficulty::{self, Master, Novice, Standard, Veteran},
};
use arena_core::{
    catalog, economy, math,
    simulation::{
        BLOCK, Config, EntityKind, Event, Input, LOADOUT, Mode, Participant, Player, Winner, World,
    },
};
use sha2::{Digest, Sha256};
use std::fmt::Write as _;

const GOLDEN: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/data/bot_matches.txt");
const MAPS: [&str; 4] = ["estate", "lantern", "foundry", "citadel"];

#[derive(Debug, Clone, Copy)]
struct Seat {
    team: u8,
    class: u8,
    weapon: u8,
    entitled: bool,
    difficulty: Difficulty,
}
const fn seat(team: u8, class: u8, weapon: u8, entitled: bool, difficulty: Difficulty) -> Seat {
    Seat {
        team,
        class,
        weapon,
        entitled,
        difficulty,
    }
}

#[derive(Debug, Clone)]
struct Case {
    name: String,
    mode: Mode,
    map: u8,
    seats: Vec<Seat>,
    /// 0 for a zero-stake match; otherwise B, with 2B for an unentitled
    /// special weapon.
    base_bond: u64,
    max_ticks: u32,
}

#[derive(Debug, Default)]
struct Outcome {
    ticks: u32,
    winner: Option<Winner>,
    final_hash: [u8; 32],
    /// SHA-256 over every tick's canonical inputs and resulting state hash.
    stream: [u8; 32],
    /// Events by ABI 4 kind (1-19).
    kinds: [u32; 20],
    abilities: [u32; 6],
    parries: u32,
    lance_heals: u32,
    spawned: [u32; 5],
    /// (slot, class before, class after) at each respawn that changed class.
    class_changes: Vec<(usize, u8, u8)>,
    loadout_requests: u32,
    kills: Vec<u32>,
    /// Bot steps the kernel did not apply in full.
    clipped: u32,
}

/// The ABI 4 export kind of a kernel event (docs/combat-rules.md §4.1).
fn kind(e: &Event) -> usize {
    match e {
        Event::Shot { .. } => 1,
        Event::Damage { .. } => 2,
        Event::Death { .. } => 3,
        Event::Respawn { .. } => 4,
        Event::Terminal => 5,
        Event::Guarded { .. } => 6,
        Event::Healed { .. } => 7,
        Event::AbilityUsed { .. } => 8,
        Event::Marked { .. } => 9,
        Event::Riposte { .. } => 10,
        Event::EntitySpawned { .. } => 11,
        Event::EntityDamaged { .. } => 12,
        Event::EntityRepaired { .. } => 13,
        Event::EntityDestroyed { .. } => 14,
        Event::EnvironmentalDamage { .. } => 15,
        Event::ObjectiveCaptured { .. } => 16,
        Event::OvertimeStarted => 17,
        Event::CheckpointReached { .. } => 18,
        Event::MatchWinner { .. } => 19,
    }
}

/// The horizontal step the kernel applies for `input` when nothing is in the
/// way, written out independently of the bots' own mirror: class speed,
/// halved while guarding, none in a Samurai stance, L1-normalized axes.
fn free_step(before: &Player, input: &Input) -> (i32, i32) {
    if before.stance_ticks > 1 {
        return (0, 0);
    }
    let guarding = input.buttons & BLOCK != 0 && before.stamina > 0;
    let speed =
        catalog::CLASSES[usize::from(before.class)].move_mm_tick / if guarding { 2 } else { 1 };
    let forward = math::direction(input.yaw, 0);
    let right = math::direction(input.yaw.wrapping_add(16384), 0);
    let norm = (i32::from(input.move_x).abs() + i32::from(input.move_y).abs()).max(127);
    let axis = |f: i32, r: i32| {
        ((i64::from(f) * i64::from(input.move_x) + i64::from(r) * i64::from(input.move_y))
            * i64::from(speed)
            / (32767 * i64::from(norm))) as i32
    };
    (axis(forward.x, right.x), axis(forward.y, right.y))
}

fn play(case: &Case) -> Outcome {
    play_with(case, |bots, world, slot, difficulty| {
        bots.input(world, slot, difficulty)
    })
}

/// Play `case` to its terminal tick, asking `ask` for every slot's input, and
/// check the invariants on every tick.
fn play_with(
    case: &Case,
    mut ask: impl FnMut(&mut Bots, &World, usize, Difficulty) -> Input,
) -> Outcome {
    let participants = case
        .seats
        .iter()
        .map(|s| Participant {
            team: s.team,
            class: s.class,
            weapon: s.weapon,
            bond: match case.base_bond {
                0 => 0,
                b if s.weapon >= 12 && !s.entitled => 2 * b,
                b => b,
            },
            special_entitled: s.entitled,
        })
        .collect::<Vec<_>>();
    let mut world = World::new(
        Config {
            mode: case.mode,
            map: case.map,
            max_ticks: case.max_ticks,
            base_bond: case.base_bond,
            offline: case.base_bond == 0,
        },
        &participants,
    )
    .unwrap_or_else(|e| panic!("{}: admission refused: {e}", case.name));
    let deposited: u64 = participants.iter().map(|p| p.bond).sum();
    let mut bots = Bots::new(&world);
    let mut stream = Sha256::new();
    let mut out = Outcome::default();
    while !world.terminal {
        let inputs = case
            .seats
            .iter()
            .enumerate()
            .map(|(slot, s)| ask(&mut bots, &world, slot, s.difficulty))
            .collect::<Vec<_>>();
        let before = world.players.clone();
        world
            .step(&inputs)
            .unwrap_or_else(|e| panic!("{}: tick {} rejected: {e}", case.name, world.tick));
        // Exact conservation of every bond on every tick.
        assert!(
            economy::conserved(&world.accounts),
            "{}: tick {}",
            case.name,
            world.tick
        );
        let held: u64 = world
            .accounts
            .iter()
            .map(|a| a.remaining + a.earnings)
            .sum();
        assert_eq!(held, deposited, "{}: tick {}", case.name, world.tick);
        for (slot, input) in inputs.iter().enumerate() {
            if !before[slot].alive {
                if input.buttons & LOADOUT != 0 {
                    out.loadout_requests += 1;
                }
                continue;
            }
            let (mut dx, mut dy) = free_step(&before[slot], input);
            // A Shinobi's dash follows the step (§6.2).
            if world
                .events
                .iter()
                .any(|e| matches!(*e, Event::AbilityUsed { slot: s, class: 1 } if s == slot))
            {
                let dash = math::scale_q15(math::direction(input.yaw, 0), 2000);
                dx += dash.x;
                dy += dash.y;
            }
            let (from, to) = (before[slot].position, world.players[slot].position);
            if (to.x - from.x, to.y - from.y) != (dx, dy) {
                out.clipped += 1;
            }
        }
        for e in &world.events {
            out.kinds[kind(e)] += 1;
            match *e {
                Event::AbilityUsed { class, .. } => out.abilities[usize::from(class)] += 1,
                Event::Guarded { parried: true, .. } => out.parries += 1,
                Event::Healed {
                    weapon: Some(17), ..
                } => out.lance_heals += 1,
                Event::EntitySpawned { kind: entity, .. } => out.spawned[entity as usize] += 1,
                Event::Respawn { slot } if world.players[slot].class != before[slot].class => {
                    out.class_changes
                        .push((slot, before[slot].class, world.players[slot].class));
                }
                _ => {}
            }
        }
        for input in &inputs {
            stream.update(input.encode());
        }
        stream.update(world.state_hash());
    }
    out.ticks = world.tick;
    out.winner = world.winner;
    out.final_hash = world.state_hash();
    out.stream = stream.finalize().into();
    out.kills = world.accounts.iter().map(|a| a.kills).collect();
    out
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().fold(String::new(), |mut s, b| {
        let _ = write!(s, "{b:02x}");
        s
    })
}

fn winner_text(winner: Option<Winner>) -> String {
    match winner {
        None => "none".into(),
        Some(Winner::Team(team)) => format!("team:{team}"),
        Some(Winner::Slot(slot)) => format!("slot:{slot}"),
        Some(Winner::Draw) => "draw".into(),
    }
}

/// Eight players of every class, with an NFT-entitled naginata and an
/// unentitled rocket (2B when bonded).
const FFA8: [Seat; 8] = [
    seat(0, 0, 1, false, Veteran),
    seat(1, 1, 3, false, Standard),
    seat(0, 2, 5, false, Novice),
    seat(1, 3, 7, false, Standard),
    seat(0, 4, 9, false, Veteran),
    seat(1, 5, 11, false, Novice),
    seat(0, 0, 12, true, Standard),
    seat(1, 3, 15, false, Novice),
];
/// Eight blades: every class's melee weapon and the naginata.
const MELEE8: [Seat; 8] = [
    seat(0, 0, 0, false, Veteran),
    seat(1, 1, 2, false, Standard),
    seat(0, 2, 4, false, Novice),
    seat(1, 3, 6, false, Standard),
    seat(0, 4, 8, false, Veteran),
    seat(1, 5, 10, false, Novice),
    seat(0, 0, 12, true, Standard),
    seat(1, 1, 2, false, Novice),
];
/// 6v6 with mirrored classes and tiers; the specials are spread over both
/// teams, entitled and unentitled.
const TEAM12: [Seat; 12] = [
    seat(0, 0, 0, false, Veteran),
    seat(1, 0, 1, false, Veteran),
    seat(0, 1, 3, false, Standard),
    seat(1, 1, 13, false, Standard),
    seat(0, 2, 5, false, Novice),
    seat(1, 2, 14, true, Novice),
    seat(0, 3, 15, false, Standard),
    seat(1, 3, 7, false, Standard),
    seat(0, 4, 9, false, Veteran),
    seat(1, 4, 16, true, Veteran),
    seat(0, 5, 17, true, Standard),
    seat(1, 5, 11, false, Standard),
];

/// Every mode on every map at the full ten-minute clock. Half of the matches
/// are bonded: each mode is bonded on two maps and each map in two modes.
fn suite() -> Vec<Case> {
    let mut cases = Vec::new();
    for (index, (mode, label, seats)) in [
        (Mode::FreeForAll, "ffa8", &FFA8[..]),
        (Mode::Control, "control12", &TEAM12[..]),
        (Mode::Payload, "payload12", &TEAM12[..]),
        (Mode::Melee, "melee8", &MELEE8[..]),
    ]
    .into_iter()
    .enumerate()
    {
        for map in 0..4u8 {
            let bonded = (index + usize::from(map)) % 2 == 1;
            cases.push(Case {
                name: format!(
                    "{label}-{}-{}",
                    MAPS[usize::from(map)],
                    if bonded { "bonded" } else { "practice" }
                ),
                mode,
                map,
                seats: seats.to_vec(),
                base_bond: if bonded { 1000 } else { 0 },
                max_ticks: 36_000,
            });
        }
    }
    cases
}

#[test]
fn every_mode_on_every_map_plays_to_a_winner_and_replays_its_golden() {
    let cases = suite();
    let outcomes = std::thread::scope(|scope| {
        let runs = cases
            .iter()
            .map(|case| scope.spawn(|| play(case)))
            .collect::<Vec<_>>();
        runs.into_iter()
            .map(|run| run.join().expect("match thread"))
            .collect::<Vec<_>>()
    });
    let mut lines = String::from(
        "# arena-bots golden matches: case, terminal tick, winner, final state hash,\n\
         # SHA-256 of every tick's inputs and state hash. Regenerate after a reviewed\n\
         # bot or kernel change with ARENA_REGENERATE_BOT_MATCHES=1.\n",
    );
    let mut total = Outcome::default();
    for (case, out) in cases.iter().zip(&outcomes) {
        let name = &case.name;
        assert!(out.ticks <= case.max_ticks, "{name}");
        match (case.mode.team(), out.winner) {
            (true, Some(Winner::Team(_))) | (false, Some(Winner::Slot(_))) => {}
            (_, winner) => panic!("{name}: no winner ({winner:?})"),
        }
        assert_eq!(out.clipped, 0, "{name}: bot steps clipped by walls");
        assert_eq!(out.kinds[5], 1, "{name}: one terminal event");
        assert!(out.kills.iter().sum::<u32>() > 0, "{name}: nobody fought");
        match case.mode {
            Mode::Control => assert!(out.kinds[16] > 0, "{name}: the point was never taken"),
            Mode::Payload => assert!(out.kinds[18] > 0, "{name}: no checkpoint reached"),
            Mode::FreeForAll | Mode::Melee => {}
        }
        // Bots keep out of hazards; nothing else can push them in.
        assert_eq!(out.kinds[15], 0, "{name}: a bot stood in a hazard");
        for (k, n) in out.kinds.iter().enumerate() {
            total.kinds[k] += n;
        }
        for (c, n) in out.abilities.iter().enumerate() {
            total.abilities[c] += n;
        }
        for (k, n) in out.spawned.iter().enumerate() {
            total.spawned[k] += n;
        }
        total.parries += out.parries;
        total.lance_heals += out.lance_heals;
        let _ = writeln!(
            lines,
            "{name} {} {} {} {}",
            out.ticks,
            winner_text(out.winner),
            hex(&out.final_hash),
            hex(&out.stream)
        );
    }
    // Over the suite every class uses its ability, and every behaviour the
    // bots are built for shows up in the kernel's own events.
    assert!(
        total.abilities.iter().all(|&n| n > 0),
        "{:?}",
        total.abilities
    );
    let spawned = |kind: EntityKind| total.spawned[kind as usize];
    assert!(spawned(EntityKind::Decoy) > 0 && spawned(EntityKind::Barricade) > 0);
    assert!(spawned(EntityKind::FireZone) > 0 && spawned(EntityKind::Ward) > 0);
    assert!(
        total.parries > 0 && total.kinds[10] > 0,
        "no parry or riposte"
    );
    assert!(
        total.kinds[9] > 0 && total.kinds[13] > 0,
        "no mark or repair"
    );
    assert!(total.lance_heals > 0, "no Healing lance heal");
    if std::env::var("ARENA_REGENERATE_BOT_MATCHES").as_deref() == Ok("1") {
        std::fs::write(GOLDEN, &lines).expect("write bot match goldens");
    }
    let golden = std::fs::read_to_string(GOLDEN).expect("read bot match goldens");
    for (expected, actual) in golden.lines().zip(lines.lines()) {
        assert_eq!(actual, expected, "bot match diverged from its golden");
    }
    assert_eq!(golden.lines().count(), lines.lines().count());
}

#[test]
fn a_bot_plans_once_per_tick_whatever_the_calling_order() {
    // The same match, asked slot by slot once, and asked three times per tick
    // in reverse slot order: identical inputs and states throughout.
    let case = Case {
        name: "control12-citadel-short".into(),
        mode: Mode::Control,
        map: 3,
        seats: TEAM12.to_vec(),
        base_bond: 0,
        max_ticks: 2400,
    };
    let once = play(&case);
    let count = case.seats.len();
    let mut asked = vec![None; count];
    let mut tick = u32::MAX;
    let thrice = play_with(&case, |bots, world, slot, difficulty| {
        if world.tick != tick {
            tick = world.tick;
            for other in (0..count).rev() {
                let first = bots.input(world, other, case.seats[other].difficulty);
                let again = bots.input(world, other, case.seats[other].difficulty);
                assert_eq!(first, again);
                asked[other] = Some(first);
            }
        }
        let planned = bots.input(world, slot, difficulty);
        assert_eq!(Some(planned), asked[slot]);
        planned
    });
    assert_eq!((once.ticks, once.stream), (thrice.ticks, thrice.stream));
    assert_eq!(once.clipped + thrice.clipped, 0);
}

#[test]
fn a_team_fills_its_missing_roles_at_respawn() {
    // Three Samurai against three stronger Teppō in Control. As they die, the
    // highest-slot duplicate of each team takes the first missing role
    // (Kusushi, then Karakuri, then Samurai, then Hanabi), and Novice bots never
    // change at all.
    let mut seats = vec![];
    for rank in 0..3 {
        seats.push(seat(0, 0, 1, false, Standard));
        seats.push(seat(
            1,
            2,
            5,
            false,
            if rank == 0 { Veteran } else { Standard },
        ));
    }
    let case = Case {
        name: "control6-roles".into(),
        mode: Mode::Control,
        map: 0,
        seats,
        base_bond: 0,
        max_ticks: 9000,
    };
    let out = play(&case);
    assert_eq!(out.clipped, 0);
    let changes = |team: usize| {
        out.class_changes
            .iter()
            .filter(|(slot, ..)| slot % 2 == team)
            .map(|&(slot, from, to)| (slot, from, to))
            .collect::<Vec<_>>()
    };
    let samurai = changes(0);
    assert!(!samurai.is_empty(), "the Samurai team never adapted");
    // The first switch is the highest Samurai slot taking the Kusushi role.
    assert_eq!(samurai[0], (4, 0, 5));
    assert!(
        samurai
            .iter()
            .all(|&(_, from, to)| from != to && [5, 4, 0, 3].contains(&to))
    );
    assert!(out.loadout_requests > 0);
    let mut easy = case.clone();
    for s in &mut easy.seats {
        s.difficulty = Novice;
    }
    let out = play(&easy);
    assert!(out.class_changes.is_empty() && out.loadout_requests == 0);
}

#[test]
fn harder_tiers_win_mirror_matches() {
    // Identical classes and weapons; only the tier differs.
    let duel = |a: Difficulty, b: Difficulty| {
        play(&Case {
            name: format!("duel-{a:?}-{b:?}"),
            mode: Mode::FreeForAll,
            map: 0,
            seats: vec![seat(0, 0, 1, false, a), seat(1, 0, 1, false, b)],
            base_bond: 0,
            max_ticks: 10_800,
        })
    };
    let out = duel(Veteran, Novice);
    assert!(out.kills[0] > 2 * out.kills[1], "{:?}", out.kills);
    assert_eq!(out.winner, Some(Winner::Slot(0)));
    let out = duel(Standard, Novice);
    assert!(out.kills[0] > out.kills[1], "{:?}", out.kills);
    let out = duel(Novice, Veteran);
    assert_eq!(out.winner, Some(Winner::Slot(1)));
    // Master, the top tier, beats the Veteran in the same mirror.
    let out = duel(Master, Veteran);
    assert!(out.kills[0] > out.kills[1], "{:?}", out.kills);
    assert_eq!(out.winner, Some(Winner::Slot(0)));
    // A Veteran team beats the same team played Novice.
    let seats = TEAM12
        .iter()
        .map(|s| Seat {
            difficulty: if s.team == 0 { Veteran } else { Novice },
            ..*s
        })
        .collect();
    let out = play(&Case {
        name: "control12-tiers".into(),
        mode: Mode::Control,
        map: 1,
        seats,
        base_bond: 0,
        max_ticks: 36_000,
    });
    assert_eq!(out.winner, Some(Winner::Team(0)));
}

#[test]
fn blades_keep_maai_parry_and_riposte() {
    // A Veteran Samurai with a katana against a Veteran Hanabi with the charged
    // Kanabo: parries of the heavy blow and counter-stance ripostes both land.
    let out = play(&Case {
        name: "melee2-duel".into(),
        mode: Mode::Melee,
        map: 2,
        seats: vec![seat(0, 0, 0, false, Veteran), seat(1, 3, 6, false, Veteran)],
        base_bond: 0,
        max_ticks: 7200,
    });
    assert_eq!(out.clipped, 0);
    assert!(out.parries > 0, "no parry");
    assert!(out.kinds[10] > 0, "no riposte");
    assert!(out.kills.iter().all(|&k| k > 0), "{:?}", out.kills);
}

#[test]
fn stronger_escorts_push_the_payload_home() {
    // Veteran attackers against Novice defenders on Debt Citadel, zero stake: the
    // attackers win by reaching the end of the route, passing every
    // checkpoint, well inside the clock.
    let seats = TEAM12
        .iter()
        .map(|s| Seat {
            difficulty: if s.team == 0 { Veteran } else { Novice },
            ..*s
        })
        .collect();
    let out = play(&Case {
        name: "payload12-escort".into(),
        mode: Mode::Payload,
        map: 3,
        seats,
        base_bond: 0,
        max_ticks: 36_000,
    });
    assert_eq!(out.winner, Some(Winner::Team(0)));
    assert!(out.ticks < 36_000);
    assert_eq!(out.kinds[18], 3);
    assert_eq!(out.clipped, 0);
}
