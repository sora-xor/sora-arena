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
its existing separate behavior.

Ammunition and reload state are included in the canonical state hash and must be
constrained by the complete future FPS execution relation. The current damage
proof experiment does not cover these rules. The native presentation ABI is
exactly 2; callers reject earlier development layouts before accessing buffers.
No compatibility decoder, fallback, or alias is provided.

Behavioral tests cover exact empty-magazine and partial-reload boundaries,
interruption one tick before completion, charge interruption, ammunition
consumption, death during reload followed by respawn, melee independence, and
state-hash binding. The replay fixture
checks the same native state through the C ABI. Balance and rendering still
require actual cross-platform gameplay tests.
