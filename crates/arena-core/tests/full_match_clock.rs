//! Full-duration headless clock and conservation check for every mode: an idle
//! staked lobby of the largest size each mode admits ends exactly at the
//! ten-minute limit with the §8.4 clock result.
use arena_core::{
    economy,
    simulation::{Config, Event, Input, Mode, Participant, Winner, World},
};

fn idle_ten_minute_match(mode: Mode, map: u8) -> World {
    let players = if mode.team() { 12 } else { 8 };
    let participants = (0..players)
        .map(|slot| Participant {
            team: (slot % 2) as u8,
            class: (slot % 6) as u8,
            weapon: if mode == Mode::Melee {
                (slot % 6 * 2) as u8
            } else {
                (slot % 6 * 2 + 1) as u8
            },
            bond: 1_000,
            special_entitled: false,
        })
        .collect::<Vec<_>>();
    let mut world = World::new(
        Config {
            mode,
            map,
            max_ticks: 36_000,
            base_bond: 1_000,
            offline: false,
        },
        &participants,
    )
    .unwrap();
    let idle = vec![Input::default(); players];
    for tick in 0..36_000 {
        assert!(!world.terminal, "{mode:?} ended early at tick {tick}");
        world.step(&idle).unwrap();
    }
    assert_eq!(world.tick, 36_000);
    assert!(world.terminal);
    assert_eq!(
        world.events,
        vec![
            Event::MatchWinner {
                winner: world.winner.unwrap()
            },
            Event::Terminal
        ]
    );
    assert!(economy::conserved(&world.accounts));
    assert_eq!(world.accounts.iter().map(|a| a.earnings).sum::<u64>(), 0);
    assert_eq!(
        world.accounts.iter().map(|a| a.remaining).sum::<u64>(),
        1_000 * players as u64
    );
    assert!(world.step(&idle).is_err());
    world
}

#[test]
fn every_mode_reaches_the_ten_minute_limit_with_its_clock_result() {
    // Nobody fights or captures: Control is a 0-0 draw, the Payload defenders
    // hold (idle attackers near the route start nudge the payload and it rolls
    // back), and FFA and Melee tie on zero kills.
    for (mode, map, winner) in [
        (Mode::FreeForAll, 0, Winner::Draw),
        (Mode::Melee, 1, Winner::Draw),
        (Mode::Control, 2, Winner::Draw),
        (Mode::Payload, 3, Winner::Team(1)),
    ] {
        let world = idle_ten_minute_match(mode, map);
        assert_eq!(world.winner, Some(winner), "{mode:?}");
        assert_eq!(world.score, [0, 0]);
        assert_eq!(world.control_owner, None);
        assert!(world.payload_progress < 3000);
    }
}

#[test]
fn a_full_ten_minute_match_is_deterministic() {
    let first = idle_ten_minute_match(Mode::Control, 0);
    let second = idle_ten_minute_match(Mode::Control, 0);
    assert_eq!(first.state_hash(), second.state_hash());
}
