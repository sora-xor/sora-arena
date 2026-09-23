//! Full-duration headless clock and conservation check for a twelve-player lobby.
use arena_core::{
    economy,
    simulation::{Config, Input, Mode, Participant, World},
};

fn idle_ten_minute_match() -> World {
    let participants = (0..12)
        .map(|slot| Participant {
            team: (slot % 2) as u8,
            class: (slot % 6) as u8,
            weapon: (slot % 6 * 2 + 1) as u8,
            bond: 1_000,
            special_entitled: false,
        })
        .collect::<Vec<_>>();
    let mut world = World::new(
        Config {
            mode: Mode::Control,
            map: 0,
            max_ticks: 36_000,
            base_bond: 1_000,
            offline: false,
        },
        &participants,
    )
    .unwrap();
    let idle = [Input::default(); 12];
    for tick in 0..36_000 {
        assert!(!world.terminal, "match ended early at tick {tick}");
        world.step(&idle).unwrap();
    }
    assert_eq!(world.tick, 36_000);
    assert!(world.terminal);
    assert!(economy::conserved(&world.accounts));
    assert_eq!(world.accounts.iter().map(|a| a.earnings).sum::<u64>(), 0);
    assert_eq!(
        world.accounts.iter().map(|a| a.remaining).sum::<u64>(),
        12_000
    );
    assert_eq!(world.players.len(), 12);
    world
}

#[test]
fn full_ten_minute_clock_is_deterministic_and_terminal() {
    let first = idle_ten_minute_match();
    let second = idle_ten_minute_match();
    assert_eq!(first.state_hash(), second.state_hash());
    let mut ended = first;
    assert!(ended.step(&[Input::default(); 12]).is_err());
}
