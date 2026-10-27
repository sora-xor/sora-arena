# October 27 Mac package — failed qualification

The fresh Development package at signed `541c61aea1cc5a76579c2185cad64eff653940bf`
builds, cooks and stages on the M2 Ultra with UE 5.8.3 and the pinned Xcode
26.1.1. Startup smoke and the separate untouched rendered startup pass.
The full client suite completes **267/271** cases successfully; five of those
successes carry warnings. This is a failed qualification, not a release.

| Failed case | Original finding |
| --- | --- |
| `SoraArena.Campaign.MoatHands` | Expected the bow to equip on the b02 bank; it remains the katana. The authored infiltration loadout keeps the bow unstrung until b03. |
| `SoraArena.Campaign.Spaces` | 23 support assertions fail in the revised Lantern Ward: sites, aerial patrol points, bench centres, tenement elevations and two collectibles require investigation against actual geometry. |
| `SoraArena.Fieldcraft.Stones` | The auditor does not reach the expected suspicious state after the stone lands. |
| `SoraArena.Integration.GuardedWork` | The fixture assumes the entry is more than 15 m from the desks; that precondition fails in the authored registry layout. |

There are 26 test errors and 607 warnings: 600 missing alternate-location dojo
timber packages, three movement timestep warnings, three named candle-component
overwrite warnings, and one repeated console-lookup warning. The assisted
eight-chapter campaign and rendered front-end tour pass. They do not establish
ordinary gameplay, performance or final art acceptance.

The editor build passes directly. The Game build first fails the known generated
Xcode pre-action, then succeeds through the existing wrapper's exact-scheme
recovery. Its original failure is preserved. Cook reports 1,354 cooked packages,
seven platform skips and zero cook warnings/errors. Staging and strict code
signature verification pass. Metal reports SM6 on Apple M2 Ultra; this does not
qualify M1/SM5, Windows or Nanite visual quality. The general toolchain doctor
retains host Git LFS 3.8.1 versus the repository's 3.8.0 pin.

All phases end naturally; the sequence finishes at `2026-10-27T04:16:57Z`.
The packaged automation process returns 3, with Unreal's test-complete marker
reporting -1 for the failures. The wrapper returns 1. The outer guard only
observes, while the unchanged packaged-launch wrapper retains its 3,600-second
SIGALRM limit. All three launches finish before that limit.

Independent review verifies 93 original files, all five EOF receipts, unchanged
input snapshots, 2,685 tracked inputs including 1,417 LFS payloads, exact discovery
and results for all 271 cases, the ABI30 native bridge, and the complete signed
bundle. Source tree is `96f47d13acb8947b5d9360ed2bbe6d821e1cd604`; native bridge
source remains `10ad7daddf73212e81496620aba628ebf214ab72`.

All 20 untouched 1280×720 screenshots are inspected. Titles, controls, prompts
and selected rows are readable. Credits expose internal generator instructions
and provenance-summary fields that need a player-facing presentation. The pause
image still shows rough repeated dojo surfaces and placeholder shapes. The title
background explicitly identifies itself as a generated key visual, not gameplay.
No image is edited or upscaled for this review.

Local evidence lives under the integration worktree's
`Saved/Qualification/2026-10-27/package-541c61ae-attempt1`; the preserved app is
`Local/Packages/mac-541c61ae/SoraArena.app`. The earlier `c655b6b` package remains.

| Record | SHA-256 |
| --- | --- |
| Original status | `28875be4876670014d764083d979194bd64a0beec12410154a8731019c6cf479` |
| Independent failed-package review | `46aa8321a67c19598aa186aedc570e0da1a4d917ffaf17904afa46dab81d32af` |
| Original-image review | `5783bca96ca861ebe929ccda8a53ca9e0a844e4c2a356f702cd7c5c4570a3b3d` |
| Package candidate | `1bf91b8efce1fc2b05a3675da6902b0e060b1db27ea653ed6cd3f03677e80133` |

The same source separately passes all 125 source CI gates in authenticated run
`40446055600`; tested merge `59fa8d82576eca35d17399ab0503ba1c025c4ffe` has the
identical tree. Source CI does not override these runtime failures. Its strict
review is `538dfb1a767bcd77d0e9102b12b669e5558ad536cdeb099106b72d7adf659e05`.

The following source repair corrects the moat fixture to use the mission katana
and explicitly checks that entering water cancels its held guard, fresh guard and
weapon-wheel inputs are refused, and those inputs work again on the bank. The
player's guard and central arm-selection paths now respect stowed hands. Five
moat and seven infiltration host tests pass; this repair has **not** yet run in
Unreal or a package.

The next isolated CPU checkpoint also revises `Spaces` to probe the actual
working side of permanent benches, local tenement floor elevations, the dry
well bottom and the manager's chest approach. Landing drones get swept checks
at their authored flight altitudes. Ladder guards get checks on the active
beat's staged roof, rather than the ground beneath it. These remain collision
checks; no test is disabled or converted to an expected failure.

`GuardedWork` now holds the mapped interaction at a real desk before, during
and after an explicit guard alarm, then checks release. Guards are frozen to
isolate that contract, and the desk's auditor is placed at its authored far
patrol corner. `Stones` uses a live auditor posted inside its actual corridor
and checks that the physical projectile lands within 4 m; the previous fixture
could place the thrower behind the corridor's end wall or overshoot hearing
range. Neither fixture establishes ordinary encounter difficulty.

Optional timber variants now use the mounted package-store existence query
before loading; the own-log/pool/box coverage report and fallback remain.
Restaged candles receive distinct UObject names so an earlier component can
finish destruction before collection. These are candidate fixes for the
reported warnings, not evidence that the warnings are gone. Movement timestep
and repeated console-lookup warnings remain open.

Six affected host suites pass: fieldcraft rules, stealth rules, 20 tenement
tests, 22 workshop tests, eight landing tests and nine timber-binding tests.
They do not compile or execute the changed Unreal code. All four failed
runtime cases require a new native run and fresh package; the original
`541c61ae` qualification remains failed and its evidence is preserved.
