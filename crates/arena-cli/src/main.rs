//! Headless deterministic simulation/qualification diagnostic. Never moves XOR.
use arena_core::{
    catalog,
    simulation::{Config, FIRE, Input, Mode, Participant, World},
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
                "reference_simulation ticks={} players={} elapsed_ms={} state_hash={}",
                w.tick,
                w.players.len(),
                start.elapsed().as_millis(),
                hash
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
        "qualification" => {
            println!(
                "arena_profile_qualified=false\nexecution_relation=not_implemented\nmainnet_funding=disabled\nmarketplace=disabled\nreference_kernel=development"
            );
        }
        "help" | "--help" | "-h" => println!(
            "SORA Arena headless tools\n  catalog\n  simulate [ticks<=36000] [players<=12]\n  qualification\nSimulation is not a cryptographic proof; no wallet is accessed."
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
