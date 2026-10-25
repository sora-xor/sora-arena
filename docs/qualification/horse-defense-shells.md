# Horse-defense shells

This implements the horse-targeted grenadier in `ch02.b06`. Its Unreal build
and three directed runtime fixtures pass across the exact-source runs below.
This does not qualify campaign pacing, final art, a package, or either platform.

The actual grenadier registered from pod B receives an encounter binding.
It chooses the nearest living indexed horse; a visible hero within 1500 cm
and clearly nearer (less than 70% of horse distance) can bait the shot. Its
controller uses normal turning, collision, navigation, catalog range and
700 cm standoff. The landing point locks when its warning appears.

The chapter's “1.4 s ahead” is implemented conservatively as **at least
1400 active milliseconds before release**, followed by the shared catalog's
1400 ms ballistic flight. The warning therefore normally precedes ground
impact by about 2.8 seconds; early physical contact can shorten flight.
It is not a claim of exactly 1.4 seconds from warning to impact. Release
intervals are 6000 active ms under continuous valid aim, quantized to the
world tick. Interruption earns a fresh full warning; late frames never fire
catch-up volleys. Difficulty does not shorten this encounter's minimum warning.

The visible ring and clock hold through menus and blocking dialogue. Stagger,
turn lock, death, target removal or warning removal cancels an unspent shot.
The real shared projectile retains swept movement, wind, 200 cm arming and
normal character defenses. An armed contact also reaches each canonical
horse target at most once within a 300 cm 3D sphere, if physical cover does
not block the blast. Each reached horse takes 35 HP. The previous proximity
health drain is disabled only for this defense and the existing foundry.

Released shells survive the shooter's death and retain its launch faction.
Failure, retry, load, leaving the beat or world teardown retires the session
before cancelling warnings and projectiles. A detonation or damage callback
that retires it stops remaining contacts. Shared blast victims use weak
references and retain ordinary damage admission and defeat handling.

The normalizer and runtime reader require the exact current contract and
cross-check the actual grenadier projectile catalog. There is no older-schema
decoder or fallback attack. The source gate exercises the production C++
clock and rejects missing, foreign, mistyped and drifted bindings.

Directed Unreal fixtures:

- `SoraArena.Campaign.HorseShellClockAndImpact`: real pod-B spawn, visible
  warning, mapped menu pause, stagger, release cadence, swept impact, indexed
  horse health, shooter removal and retained faction.
- `SoraArena.Campaign.HorseShellBaitAndCancellation`: nearer-hero selection,
  fixed landing point, successful dodge, and cancellation from an actual
  detonation callback before horse damage.
- `SoraArena.Campaign.HorseShellCoverAndDud`: physical armed contact inside
  blast range with cover, and a collision before arming distance.

These fixtures freeze unrelated combat, give the hero extra health, and
stage combat poses in a clear estate aisle. They do not prove an unassisted
150-second defense or navigation all the way from the pod to firing range.
Pod descent art, finished horses, the final warning effect and the authored
withdrawal on completion remain separate unfinished work.

## October 25 runtime evidence

Exact `bf58810` builds in 39.28 seconds and runs sixteen selected tests: fifteen
pass, with two selected errors in HorseShellCoverAndDud and zero warnings.
ClockAndImpact and BaitAndCancellation pass, along with all three pod fixtures,
held treatment/cooldown/retry, the corrected canister and MarginLinger cases,
and the full assisted 133-beat Playthrough. The first armed-cover assertions
pass; the second shot detonates because the fixture's fixed obstruction no
longer guarantees a pre-arming contact after the shooter moves. The original
failure is preserved; that cause was inferred from source, not measured in
the original failed run.

Fixture-only `2a69fb5` places the obstruction ahead of the actual shooter and
asserts a radius-nine sweep along the first 199 cm reaches that obstruction.
Its build passes in 46.76 seconds. HorseShellCoverAndDud and the shared
ExplosiveSelfDamageAndArming regression both pass, with zero selected errors
or warnings and actual editor/wrapper exit zero. The diagnostic measures
first contact at 95.810 cm and projectile travel at 26.414 cm. Production
arming and damage code are unchanged. The earlier fifteen passes were not
rerun at this fixture-only revision.

The root rehashed twenty files from each runtime archive and verified unchanged
source, native inputs, Config and Generated files. Evidence is under
`Saved/Qualification/2026-10-25/horse-shell-bf58810-runtime-attempt1` and
`horse-dud-2a69fb5-runtime-attempt1`, with adjacent root-review JSON receipts.
An earlier `03e8bf4` build failed before editor launch on four declaration/test
helper errors; that failure also remains preserved. Authenticated CI at
`bf58810` passes 105 source gates in five jobs, including 279 Rust tests with
five explicit ignores. It does not cover the later fixture correction.
