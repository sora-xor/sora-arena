# Chapter seven fuel canister behavior

The authored contract is in `chapter-07.md:198–208,579–596,1004`: three glowing canisters in the hangar, bursting when shot, with a 360 cm blast radius and 80 base damage including the player. Their floor coordinates are measured from the aft-starboard hangar corner:

| ID | Local metres | Current world floor centimetres |
|---|---|---|
| fc_01 | 28, 12 | 40800, -1050, 0 |
| fc_02 | 52, 12 | 43200, -1050, 0 |
| fc_03 | 40, 38 | 42000, 1550, 0 |

`campaign_canisters.py` translates these positions using the existing hangar origin and validates the original `ext.hazards`. The catalog requires the exact typed contract on ch07.b08 only. Wind, mouth ledge protection, shuttle cover, gallery collision and projectile drift keep their existing behavior.

Each staged canister has a blocking and shootable capsule. A positive, finite ranged `FSoraDamageEvent` through `TakeDamage` bursts it once while the game is in play. Existing player hitscan weapons, including the Plasma Matchlock, and actual released arrows deliver this event. Melee, generic/scripted damage, blast events and paused input do not consume it. Explosive-shell impact, chain reactions and enemy-fire delivery to props remain unresolved; this slice does not change shared projectile or enemy firing behavior.

The canister latches as spent and disables collision before emitting its explosion event or dealing damage. It remains spent until encounter teardown; retry creates new intact actors. Its components and short flash are owned by that actor and are removed with it.

The blast uses `SoraDamage::Blast` with the canister as causer and the firing pawn as instigator. It therefore retains the existing line-of-sight cover, full self-blast damage, ally exclusions, ordinary defenses, enemy vulnerability modifiers, nonlethal handling and registered-wave defeat credit. **80 is the base damage**, not a bypass of those rules. The blast center is the proxy body's center, 70 cm above the authored floor point.

The 60 cm wide, 140 cm high cylinder, colored band, point light and brief sphere flash are provisional functional presentation. These dimensions and shapes are implementation choices, not quoted authored art specifications or final-quality assets.

Host tests check the typed source contract, transforms and the actual C++ one-shot trigger policy. Prepared runtime tests are `SoraArena.Campaign.HangarCanisterShots` and `SoraArena.Campaign.HangarCanisterBlast`. They use real mapped weapons, collision, world clocks and damage events, with explicit checkpoint/health setup, frozen enemy AI and, in the blast fixture, relocated registered opponents and temporary cover. Their existence is not evidence that they have compiled or passed in Unreal; full encounter difficulty, visuals and platform qualification remain separate.
