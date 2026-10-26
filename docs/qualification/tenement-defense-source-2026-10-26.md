# Tenement kitchen defense: source checkpoint, 26 October 2026

This continues the tenement checkpoint `1e15e8a9`. It is **not compiled or tested
in Unreal**. Claude still owns the engine/Blender lane for the r3 character work.
The published integration branch and packaged game have not changed.

## Behavior changes

Chapter three's communal-kitchen defense now uses the authored court and last six
metres of alley: X -3400..-2200, Y 2220..3600, Z 0..600 cm. A grounded player's
capsule overlapping it can work. A live enemy capsule overlapping it contests the
work. The old 420 cm work circle and 900 cm contest circle around the western
anchor no longer decide this encounter. A drone centred at the six-metre upper
face counts because its body overlaps the volume; an enemy in the street, outside
the west fence, above the volume, or below the court does not.

The loader retains the admitted wave entrance identities. Spawning uses wave,
group and member indices, including the nonlethal conscript path, rather than the
global number of enemies spawned. The first wave's four bodies occupy separate
positions 120 cm apart at the alley mouth. The second wave's two inventory drones
enter at (-3500, 3600, 600) and (-3500, 3400, 600). The third wave reuses the alley
mouth for its retainer and rifle instead of inheriting old drone slots. Conscripts
remain nonlethal; the 30/60/80% release marks and 120-second hold remain unchanged.

Each drone follows two admitted waypoints over the west fence toward the queue,
at an actor-centre height of 600 cm. The controller uses ordinary swept flying
movement with a real 3D goal. Only actual arrival advances the leg; a timer cannot
skip an obstruction. This assignment bypasses the ordinary ground-relative hover
rule, holds its final station and uses the existing visible-target net attack.
It does not alter other drones' behavior or move a pawn directly to a waypoint.

The provisional work marker spans the authored rectangle. The supply trigger is
restored to the specified 200 x 200 cm box centred at the manager's door
(-2400, 3600). The three two-second cookfire relights are reused. Later inspection
found that the generic supply refill existed but its builder staged only the
spire cache: **this checkpoint did not create a kitchen supply crate**. The
follow-up `tenement-supply-source-2026-10-26.md` records that fix and its limits.
The generated layout, raw wave names/types/counts,
compiled wave rules, loader checks and shared native geometry must agree.

## Evidence and remaining validation

Twelve targeted tenement host tests pass, including the existing narrow-well and
carry routes. The compiled native driver checks capsule/volume boundaries, the
far court and alley, the street, rounded corners, the upper air boundary and the
below-ground shaft. It emits the exact runtime spawn and flight tables; tests
check all eight wave members, same-wave body separation and both drone routes
against the tenement solids at six metres. Invalid entry names, wave kinds,
counts, timing, lethality, height and volume data are rejected.

The final campaign validator passed with 133 beats, 1,032 bilingual lines and all
65 invalid variants rejected. Regeneration is unchanged on a second run. The dojo
campaign binding is refreshed for the changed chapter hash only.

All 119 selected host source checks passed at signed, clean and unchanged commit
`cef5e471fc858ab92ef01de5ac7d4b39b658049b`, tree
`64756574cc00eeb0e5b0aea076c773d0da3a2342`: 64 gameplay, 27 tooling, 22 assets and
six audio checks. Rust checks were not rerun. The independent receipt verifies
the expected check inventory, commands, exit codes, log hashes and source state.
It does not compile the Unreal module or establish runtime behavior.

Evidence in the source-validation worktree:

- `Saved/Qualification/2026-10-26/tenement-defense-cef5e471-source/report.json`,
  SHA-256 `8b0e7e0f1d634f01443c7c9e778bc21e3386da3340b2f8fcc46c6c87ae45da30`.
- `Saved/Qualification/2026-10-26/tenement-defense-cef5e471-source/independent-review.json`,
  SHA-256 `06a6b3f6b6d63d476aa5c50a90404f4b7f5dd96f3551b02e186bb38cf6fa5327`.

New Unreal fixtures are source only:

- `SoraArena.Campaign.Tenements.KitchenVolume`: work in the east court and upper
  alley, refusal in the lower alley, and menu pause.
- `SoraArena.Campaign.Tenements.DefenseWaves`: real beat time and all three wave
  entries; held relighting at all three fire interruptions; an east-court enemy
  contests while a nearby enemy outside the west fence does not; live drone
  movement at six metres, arrival, a real net root and aerial contest after the
  root effect expires. The fixture hardens the hero, holds/repositions a probe
  and removes completed groups to isolate the encounter rules. It does not
  establish ordinary combat difficulty or campaign completion.

After lane handback, compile and run these plus the existing tenement, equipment
recovery, cookfire, supply, carry, landing/ward, enemy and assisted-playthrough
regressions. Inspect an ordinary fight and its visual/readability/performance
results. The resident queue and scattering behavior, serving furniture, final
kitchen art and craft remain unfinished. The chapter's other known tenement gaps
(separate early finds, balances, hint lamp, notice-board continuation and connected
ward street) remain open. This source checkpoint is not release acceptance.
