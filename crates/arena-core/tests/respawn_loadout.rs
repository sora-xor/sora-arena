//! Spawn points and respawn loadout selection (docs/combat-rules.md §10).
use arena_core::{
    catalog::CLASSES,
    maps::ARENAS,
    math::Vec3,
    simulation::{
        ABILITY, Config, EntityKind, Event, FIRE, Input, LOADOUT, Mode, Participant, World,
    },
};

fn world(mode: Mode, map: u8, roster: &[(u8, u8, u8)]) -> World {
    let roster = roster
        .iter()
        .map(|&(team, class, weapon)| Participant {
            team,
            class,
            weapon,
            bond: 0,
            special_entitled: weapon >= 12,
        })
        .collect::<Vec<_>>();
    World::new(
        Config {
            mode,
            map,
            max_ticks: 36_000,
            base_bond: 0,
            offline: true,
        },
        &roster,
    )
    .unwrap()
}

fn kill(w: &mut World, slot: usize, respawn_ticks: u32) {
    let p = &mut w.players[slot];
    p.alive = false;
    p.health = 0;
    p.respawn_ticks = respawn_ticks;
}

fn request(class: i16, index: i16) -> Input {
    Input {
        buttons: LOADOUT,
        move_x: class,
        move_y: index,
        ..Input::default()
    }
}

#[test]
fn team_spawns_follow_each_players_rank_within_its_team() {
    let teams = [0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0];
    let roster = teams.map(|team| (team, 0, 1));
    for (map, arena) in ARENAS.iter().enumerate() {
        let mut w = world(Mode::Payload, map as u8, &roster);
        let mut rank = [0; 2];
        for (slot, &team) in teams.iter().enumerate() {
            let spawn = arena.team_spawns[usize::from(team)][rank[usize::from(team)]];
            rank[usize::from(team)] += 1;
            assert_eq!(w.players[slot].position, spawn.position());
            assert_eq!(w.players[slot].yaw, spawn.yaw);
        }
        // Every respawn returns to the rank's spawn and faces its yaw, level.
        for slot in 0..12 {
            let p = &mut w.players[slot];
            p.position = Vec3::new(0, 0, 0);
            p.yaw = 12_345;
            p.pitch = 3000;
            kill(&mut w, slot, 1);
        }
        w.step(&[Input::default(); 12]).unwrap();
        let mut rank = [0; 2];
        for (slot, &team) in teams.iter().enumerate() {
            let spawn = arena.team_spawns[usize::from(team)][rank[usize::from(team)]];
            rank[usize::from(team)] += 1;
            let p = &w.players[slot];
            assert!(p.alive);
            assert_eq!(
                (p.position, p.yaw, p.pitch),
                (spawn.position(), spawn.yaw, 0)
            );
        }
    }
}

#[test]
fn ffa_respawn_takes_the_spawn_farthest_from_every_living_player() {
    let arena = &ARENAS[1];
    let mut w = world(Mode::FreeForAll, 1, &[(0, 0, 1), (0, 0, 1), (0, 0, 1)]);
    // Nobody else alive: the slot's own FFA spawn.
    kill(&mut w, 0, 1);
    kill(&mut w, 1, 5);
    kill(&mut w, 2, 5);
    w.step(&[Input::default(); 3]).unwrap();
    assert_eq!(w.players[0].position, arena.ffa_spawns[0].position());
    // Otherwise the largest minimum horizontal distance, ties to the lowest
    // index: with players near spawns 0 and 1 the choice is exact.
    let (a, b) = (
        arena.ffa_spawns[0].position(),
        arena.ffa_spawns[1].position(),
    );
    let mut w = world(Mode::FreeForAll, 1, &[(0, 0, 1), (0, 0, 1), (0, 0, 1)]);
    w.players[0].position = a;
    w.players[1].position = b.offset(Vec3::new(0, 0, 900));
    kill(&mut w, 2, 1);
    w.step(&[Input::default(); 3]).unwrap();
    let nearest = |s: Vec3| {
        s.horizontal_distance_squared(a)
            .min(s.horizontal_distance_squared(b))
    };
    let best = arena
        .ffa_spawns
        .iter()
        .map(|s| nearest(s.position()))
        .max()
        .unwrap();
    let index = arena
        .ffa_spawns
        .iter()
        .position(|s| nearest(s.position()) == best)
        .unwrap();
    assert_eq!(w.players[2].position, arena.ffa_spawns[index].position());
    assert_eq!(w.players[2].yaw, arena.ffa_spawns[index].yaw);
}

#[test]
fn a_dead_player_selects_a_new_class_and_loadout_for_its_respawn() {
    let mut w = world(Mode::Control, 0, &[(0, 0, 1), (1, 0, 1)]);
    w.players[0].ability_cooldown = 300;
    kill(&mut w, 0, 3);
    let idle = Input::default();
    w.step(&[request(5, 0), idle]).unwrap();
    assert_eq!(w.players[0].pending_loadout, Some((5, 11)));
    // A later valid request replaces it; an invalid one leaves it.
    w.step(&[request(3, 1), idle]).unwrap();
    w.step(&[request(3, 2), idle]).unwrap();
    assert!(w.players[0].alive);
    let p = &w.players[0];
    assert_eq!((p.class, p.weapon, p.pending_loadout), (3, 6, None));
    assert_eq!((p.health, p.ammo, p.stamina), (CLASSES[3].health, 0, 100));
    assert_eq!((p.ability_cooldown, p.spawn_protection), (297, 120));
    assert_eq!(p.admitted_special, None);
    // The new weapon is live at once: the Kanabō starts its windup.
    w.step(&[
        Input {
            buttons: FIRE,
            ..Input::default()
        },
        idle,
    ])
    .unwrap();
    assert_eq!((w.players[0].charge_weapon, w.players[0].charge), (6, 1));
    // Living players ignore even a request a dead player could make; its
    // fields still steer them.
    let before = w.players[0].position;
    w.step(&[request(5, 1), idle]).unwrap();
    assert_eq!(w.players[0].pending_loadout, None);
    assert_eq!(w.players[0].position, before.offset(Vec3::new(2, 0, 0)));
}

#[test]
fn only_the_admitted_special_of_the_chosen_class_can_be_selected() {
    let mut w = world(Mode::FreeForAll, 2, &[(0, 1, 13), (0, 4, 9)]);
    assert_eq!(
        (w.players[0].admitted_special, w.players[1].admitted_special),
        (Some(13), None)
    );
    kill(&mut w, 0, 50);
    kill(&mut w, 1, 50);
    // Samurai's special is 12, not the admitted 13; slot 1 has none.
    w.step(&[request(0, 2), request(4, 2)]).unwrap();
    assert_eq!(
        (w.players[0].pending_loadout, w.players[1].pending_loadout),
        (None, None)
    );
    w.step(&[request(1, 2), request(4, 0)]).unwrap();
    assert_eq!(
        (w.players[0].pending_loadout, w.players[1].pending_loadout),
        (Some((1, 13)), Some((4, 9)))
    );
    // Standard equipment of any class stays available to a special holder.
    w.step(&[request(2, 0), Input::default()]).unwrap();
    assert_eq!(w.players[0].pending_loadout, Some((2, 5)));
}

#[test]
fn melee_mode_ignores_ranged_loadout_requests() {
    let mut w = world(Mode::Melee, 3, &[(0, 0, 12), (0, 2, 4)]);
    kill(&mut w, 0, 50);
    kill(&mut w, 1, 50);
    w.step(&[request(0, 0), request(2, 0)]).unwrap();
    assert_eq!(
        (w.players[0].pending_loadout, w.players[1].pending_loadout),
        (None, None)
    );
    w.step(&[request(0, 2), request(3, 1)]).unwrap();
    assert_eq!(
        (w.players[0].pending_loadout, w.players[1].pending_loadout),
        (Some((0, 12)), Some((3, 6)))
    );
}

#[test]
fn loadout_requests_are_structurally_bounded_and_spectators_ignore_them() {
    for (move_x, move_y, valid) in [
        (0, 0, true),
        (5, 2, true),
        (6, 0, false),
        (0, 3, false),
        (-1, 0, false),
        (0, -1, false),
    ] {
        let input = request(move_x, move_y);
        assert_eq!(input.validate().is_ok(), valid, "{move_x} {move_y}");
        if valid {
            assert_eq!(Input::decode(input.encode()).unwrap(), input);
        } else {
            assert!(Input::decode(input.encode()).is_err());
        }
    }
    let unknown = Input {
        buttons: 128,
        ..Input::default()
    };
    assert!(unknown.validate().is_err());
    // An invalid request rejects the whole step atomically.
    let mut w = world(Mode::FreeForAll, 0, &[(0, 0, 1), (0, 0, 1)]);
    kill(&mut w, 0, 10);
    let hash = w.state_hash();
    assert!(w.step(&[request(9, 0), Input::default()]).is_err());
    assert_eq!((w.state_hash(), w.tick), (hash, 0));
    // A spectator whose reserve is exhausted never acts on a request.
    let mut w = World::new(
        Config {
            mode: Mode::FreeForAll,
            map: 0,
            max_ticks: 600,
            base_bond: 1000,
            offline: false,
        },
        &[0, 1, 2].map(|_| Participant {
            team: 0,
            class: 0,
            weapon: 1,
            bond: 1000,
            special_entitled: false,
        }),
    )
    .unwrap();
    kill(&mut w, 0, 0);
    w.accounts[0].remaining = 0;
    w.accounts[0].paid_deaths = 10;
    w.accounts[1].earnings = 1000;
    w.step(&[request(1, 0), Input::default(), Input::default()])
        .unwrap();
    assert_eq!(w.players[0].pending_loadout, None);
    assert!(!w.players[0].alive);
}

#[test]
fn a_class_change_keeps_the_entities_of_the_previous_class() {
    let mut w = world(Mode::FreeForAll, 0, &[(0, 4, 9), (0, 0, 1)]);
    w.players[0].position = Vec3::new(0, 0, 0);
    w.players[1].position = Vec3::new(-6000, 0, 0);
    w.step(&[
        Input {
            buttons: ABILITY,
            ..Input::default()
        },
        Input::default(),
    ])
    .unwrap();
    assert_eq!(w.entities.len(), 1);
    kill(&mut w, 0, 2);
    w.step(&[request(1, 1), Input::default()]).unwrap();
    w.step(&[request(1, 1), Input::default()]).unwrap();
    assert_eq!((w.players[0].class, w.players[0].weapon), (1, 2));
    w.players[0].ability_cooldown = 0;
    w.step(&[
        Input {
            buttons: ABILITY,
            ..Input::default()
        },
        Input::default(),
    ])
    .unwrap();
    let kinds = w
        .entities
        .iter()
        .map(|e| (e.owner, e.kind))
        .collect::<Vec<_>>();
    assert_eq!(kinds, [(0, EntityKind::Barricade), (0, EntityKind::Decoy)]);
}

#[test]
fn a_respawned_player_acts_on_its_respawn_tick_from_the_spawn_yaw() {
    let arena = &ARENAS[0];
    let mut w = world(Mode::Control, 0, &[(0, 0, 1), (1, 5, 11)]);
    kill(&mut w, 0, 1);
    kill(&mut w, 1, 1);
    let act = |buttons| Input {
        buttons,
        move_x: 127,
        yaw: 12_345,
        pitch: 900,
        ..Input::default()
    };
    w.step(&[act(FIRE), act(ABILITY)]).unwrap();
    // The player phase respawned both without turning or moving them, and the
    // later phases let them fire and use an ability from the spawn yaw.
    for (slot, team) in [(0, 0), (1, 1)] {
        let (p, spawn) = (&w.players[slot], arena.team_spawns[team][0]);
        assert!(p.alive);
        assert_eq!(
            (p.position, p.yaw, p.pitch, p.spawn_protection),
            (spawn.position(), spawn.yaw, 0, 0)
        );
    }
    assert_eq!(w.players[0].ammo, 23);
    assert!(w.events.contains(&Event::Shot { slot: 0, weapon: 1 }));
    assert!(w.events.contains(&Event::AbilityUsed { slot: 1, class: 5 }));
    let ward = w.entities.iter().find(|e| e.owner == 1).unwrap();
    assert_eq!(
        (ward.kind, ward.position),
        (EntityKind::Ward, arena.team_spawns[1][0].position())
    );
}

#[test]
fn loadout_state_is_part_of_the_state_hash() {
    let base = world(Mode::FreeForAll, 0, &[(0, 1, 13)]);
    let mut pending = base.clone();
    pending.players[0].pending_loadout = Some((1, 2));
    let mut other = base.clone();
    other.players[0].pending_loadout = Some((1, 3));
    let mut special = base.clone();
    special.players[0].admitted_special = None;
    let hashes = [&base, &pending, &other, &special].map(World::state_hash);
    for (i, a) in hashes.iter().enumerate() {
        for b in &hashes[i + 1..] {
            assert_ne!(a, b);
        }
    }
}
