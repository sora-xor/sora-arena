# Deterministic weapon handling

The Rust kernel owns the following first-release rules. Unreal practice collects
inputs and displays snapshots; animation completion and local wall-clock timers
cannot refill a magazine or authorize a shot. The campaign prototype still has
separate gameplay code and is not proof-qualified.

All ranged weapons start and respawn with a full magazine. Replacement magazines
are unlimited in the current Arena rules, but every refill requires the weapon's
complete reload duration. Melee weapons use stamina and have no ammunition.
Magazine sizes and reload times are fixed in the versioned combat catalog; NFT
rarity does not change them.

| Weapon | Magazine | Reload ticks / seconds |
| --- | ---: | ---: |
| Arc carbine | 24 | 96 / 1.60 |
| Needle SMG | 32 | 102 / 1.70 |
| Coil matchlock | 5 | 138 / 2.30 |
| Grenade launcher | 5 | 144 / 2.40 |
| Clockwork repeater | 36 | 120 / 2.00 |
| Pulse carbine | 22 | 93 / 1.55 |
| Phantom SMG | 22 | 132 / 2.20 |
| Plasma matchlock | 3 | 168 / 2.80 |
| Micro-mortar | 3 | 168 / 2.80 |
| Shock emitter | 18 | 114 / 1.90 |
| Healing lance | 16 | 138 / 2.30 |

`RELOAD` requests a whole-magazine refill if the equipped firearm is not full.
A trigger request on an empty gun starts the same reload once attack recovery
ends. Starting a reload sets its full remaining duration; subsequent simulation
ticks decrement it. A reload begun at tick T with duration N completes at T+N,
when a held trigger may fire if other requirements permit. No shot can occur
while the reload has remaining ticks.

A block or melee request interrupts reload before that tick's completion check.
The existing ammunition is retained; partial progress is discarded. Reloading
and guarding clear charge progress. A charged attack consumes a round only when
it produces a shot. Death cancels pending reload/charge; respawn restores the
magazine and clears melee defense and attack recovery. Ability cooldown retains
its existing separate behavior. Charge progress is tagged with the selected
weapon and cannot be transferred by switching from melee to a charged firearm.
The tag is included in the canonical state hash.

Kanabo strikes require eighteen held 60 Hz ticks of windup and land on the
nineteenth held tick. Releasing or guarding restarts that windup. Stamina is
spent only when the strike occurs, followed by its forty-eight-tick recovery.
Plasma matchlock direct hits require a twenty-four-tick charge and penetrate
directional parry and guard; its three-round magazine and long reload remain.
Other hits, including projectiles from a player currently holding Plasma,
retain normal defense rules. These are provisional sidegrade tradeoffs pending
human balance and readability playtests.

`cargo run --release -p arena-cli -- balance` now measures every weapon through
the 60 Hz kernel against a stationary, undefended 125-HP Samurai in a clear
lane. The six standard ranged weapons kill in 1.017–1.217 seconds in that
scenario. Standard melee ranges from 1.017 to 1.617 seconds; charged Plasma
matchlock and Micro-mortar take about 1.78–1.80 seconds. The command reports
the exact death tick, shots and damage events for each weapon. This is a
repeatable mechanical baseline, not evidence of fair duels, readable effects,
map balance, or human playtesting.

In Control and Payload, the Healing lance's ray selects the nearest living
player before the first wall. It heals an ally by 15 health up to that class's
maximum, or damages an enemy by 15. A full-health ally still intercepts the
shot. Dead allies are skipped and cannot be revived. In FFA, it damages other
players. Its ammunition and cooldown apply to every shot. All shots gather
targets from the same pre-damage state; queued healing resolves before ordered
damage, allowing a same-tick rescue but no resurrection. This health
transition is part of the versioned combat rules and still needs a complete
execution proof. The current native event interface reports the shot and
subsequent health snapshot, but has no dedicated heal effect event.

Ammunition, reload, and weapon-bound charge state are included in the canonical state hash and must be
constrained by the complete future FPS execution relation. The current damage
proof experiment does not cover these rules. The native presentation ABI is
exactly 3; callers reject earlier development layouts before accessing buffers.
No compatibility decoder, fallback, or alias is provided.

Behavioral tests cover exact empty-magazine and partial-reload boundaries,
interruption one tick before completion, charge interruption, ammunition
consumption, death during reload followed by respawn, melee independence,
Kanabo/Plasma semantics, and state-hash binding. The replay fixture
checks the same native state through the C ABI. Balance and rendering still
require actual cross-platform gameplay tests.
