//! Headless deterministic simulation/qualification diagnostic. Never moves XOR.
mod peer;
mod script;
mod trace;

use arena_core::{
    arena_export,
    catalog::{self, AttackKind},
    math::Vec3,
    simulation::{Config, Event, FIRE, Input, Mode, Participant, World},
};
use std::time::Instant;

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let command = args.next().unwrap_or_else(|| "help".into());
    match command.as_str() {
        "catalog" => {
            for c in catalog::CLASSES {
                println!(
                    "{}: {} health={} movement={}mm/tick",
                    c.id, c.name, c.health, c.move_mm_tick
                );
            }
            for w in catalog::WEAPONS {
                println!(
                    "{}: {} {:?} damage={} cooldown={}ticks",
                    w.id, w.name, w.kind, w.damage, w.cooldown
                );
            }
        }
        "simulate" => {
            let ticks = args
                .next()
                .map(|s| s.parse::<u32>())
                .transpose()?
                .unwrap_or(7200);
            let count = args
                .next()
                .map(|s| s.parse::<usize>())
                .transpose()?
                .unwrap_or(8);
            let participants = (0..count)
                .map(|i| Participant {
                    team: (i % 2) as u8,
                    class: (i % 6) as u8,
                    weapon: (i % 6 * 2 + 1) as u8,
                    bond: 1000,
                    special_entitled: false,
                })
                .collect::<Vec<_>>();
            let mut w = World::new(
                Config {
                    mode: Mode::Control,
                    map: 0,
                    max_ticks: ticks,
                    base_bond: 1000,
                    offline: false,
                },
                &participants,
            )?;
            let start = Instant::now();
            while !w.terminal {
                let input = (0..count)
                    .map(|slot| Input {
                        buttons: if w.tick.is_multiple_of(3) { FIRE } else { 0 },
                        move_x: 80,
                        move_y: if (w.tick / 180 + slot as u32).is_multiple_of(2) {
                            60
                        } else {
                            -60
                        },
                        yaw: ((w.tick * 37 + slot as u32 * 5461) % 65536) as u16,
                        pitch: 0,
                    })
                    .collect::<Vec<_>>();
                w.step(&input)?;
            }
            let hash = w
                .state_hash()
                .iter()
                .map(|b| format!("{b:02x}"))
                .collect::<String>();
            println!(
                "reference_simulation ticks={} players={} elapsed_ms={} state_hash={} winner={:?}",
                w.tick,
                w.players.len(),
                start.elapsed().as_millis(),
                hash,
                w.winner
            );
            println!(
                "deposited={} remaining={} pending_earnings={} conserved={}",
                w.accounts.iter().map(|a| a.initial).sum::<u64>(),
                w.accounts.iter().map(|a| a.remaining).sum::<u64>(),
                w.accounts.iter().map(|a| a.earnings).sum::<u64>(),
                arena_core::economy::conserved(&w.accounts)
            );
            println!("execution_proof=NOT_IMPLEMENTED qualified=false ledger_transactions=0");
        }
        "balance" => {
            println!("weapon,class,kind,lane_mm,death_tick,elapsed_seconds,shots,damage_events");
            for weapon in catalog::WEAPONS {
                let attacker_class = if weapon.id < 12 {
                    weapon.id / 2
                } else {
                    weapon.id - 12
                };
                let mut world = World::new(
                    Config {
                        mode: Mode::FreeForAll,
                        map: 0,
                        max_ticks: 600,
                        base_bond: 0,
                        offline: true,
                    },
                    &[
                        Participant {
                            team: 0,
                            class: attacker_class,
                            weapon: weapon.id,
                            bond: 0,
                            special_entitled: false,
                        },
                        Participant {
                            team: 1,
                            class: 0,
                            weapon: 0,
                            bond: 0,
                            special_entitled: false,
                        },
                    ],
                )?;
                // A stationary, undefended 125-HP Samurai in a clear lane.
                // This is a repeatable mechanical diagnostic, not a playtest.
                let distance = if weapon.kind == AttackKind::Melee {
                    1500
                } else {
                    5000_i32.max(weapon.arming_mm + 500)
                };
                world.players[0].position = Vec3::new(0, 0, 0);
                world.players[1].position = Vec3::new(distance, 0, 0);
                let mut death_tick = None;
                let mut shots = 0;
                let mut damage_events = 0;
                for tick in 0..600 {
                    world.step(&[
                        Input {
                            buttons: FIRE,
                            ..Input::default()
                        },
                        Input::default(),
                    ])?;
                    for event in &world.events {
                        match event {
                            Event::Shot { slot: 0, .. } => shots += 1,
                            Event::Damage {
                                attacker: 0,
                                victim: 1,
                                ..
                            } => damage_events += 1,
                            Event::Death { victim: 1, .. } => death_tick = Some(tick),
                            _ => {}
                        }
                    }
                    if death_tick.is_some() || world.terminal {
                        break;
                    }
                }
                let elapsed = death_tick.map_or(String::from("none"), |tick| {
                    format!("{:.3}", f64::from(tick + 1) / 60.0)
                });
                let tick = death_tick.map_or(String::from("none"), |tick| tick.to_string());
                println!(
                    "{},{},{:?},{},{},{},{},{}",
                    weapon.id,
                    attacker_class,
                    weapon.kind,
                    distance,
                    tick,
                    elapsed,
                    shots,
                    damage_events
                );
            }
            println!("scope=offline clear-lane mechanics only; proof_qualified=false");
        }
        "arenas" => print!("{}", arena_export::json()),
        "peer" => peer::run(args)?,
        "trace" => trace::run(args)?,
        "qualification" => {
            println!(
                "arena_profile_qualified=false\nexecution_relation=not_implemented\nmainnet_funding=disabled\nmarketplace=disabled\nreference_kernel=development"
            );
        }
        "help" | "--help" | "-h" => println!(
            "SORA Arena headless tools\n  catalog\n  simulate [ticks<=36000] [players<=12]\n  balance\n  arenas (arena-map-v1 JSON: the exact kernel collision, spawns, objectives and hazards)\n  qualification\n  {} (one scripted, offline, zero-bond research mesh peer)\n  {}\nSimulation is not a cryptographic proof; no wallet is accessed.",
            peer::USAGE,
            trace::USAGE
        ),
        _ => return Err(format!("unknown command: {command}").into()),
    }
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("arena: {e}");
        std::process::exit(1);
    }
}
