# Complete first-release plan

Development resumed on 2026-10-18 at the user's explicit request to finish the
complete game and collaborate with Claude's **Photoreal art WIP checkpoint**.
The release is incomplete. This plan tracks remaining work; historical test
results in [implementation status](implementation-status.md) retain their
original source, machine and scope.

Codex owns integration and release acceptance. Claude owns art direction and
production. Work runs in isolated worktrees, with a single coordinated Unreal
and GPU rendering lane. The shared checkout is not a build or render workspace.
The local coordination mailboxes record current ownership, commits and lane use.

## October 23 cargo unloading and timer qualification

At `d21013d`, chapter-four cargo requires the authored uninterrupted three-second
unload hold before delivery credit or the Naka ambush. Release, departure and
retry cancel partial work; pause freezes it. A fresh hold owns its fractional
clock, so time before the press cannot complete unloading early. Ordinary
carrying and the authored option to continue on foot remain available.

All five selected Mac editor tests pass: CargoUnload, Mount,
CarrySealAndSetDown, CarryDifficulty and the full campaign Playthrough. The
source-bound build passes in 47.33 seconds and the runtime exits zero at EOF
with unchanged source. Mount retains one HTTP connectivity timeout warning;
the other four tests have no selected warnings or errors. All 43 gameplay
source gates pass at the same clean source. The directed cargo fixture freezes
threats and does not qualify ordinary encounter pacing or carrier presentation.

`4db3ce3` carries fractional milliseconds through stealth and gallery clocks
instead of rounding every frame. Ten actual editor regressions pass with zero
selected warnings/errors; four guard searches each take 20.000001 active world
seconds over 1,200 frames. At `fea8842`, the gallery hint appears once after
60.000003 active seconds at both 60 and 120 Hz; a 65-second menu pause advances
no world time, and retry resets the timer. The first gallery fixture's retained
failure came from an extra capstan input after arrival resetting idle time;
the correction stops that input without relaxing the timing bound.

Signed native `01d4e46` also completes actual privacy-crate compilation, exact
test listing and 31 CPU tests, with two proof tests explicitly ignored. All
five phases terminate at EOF with zero exits in 1,180.368 seconds overall.
The maximum measured wire bound across 48 canonical cases is 3,149,632 bytes;
this is a bound, not a proof size. Source and executable hashes are independently
authenticated. One separate native proof/adversarial cohort is running against
that exact executable; no successful proof is yet claimed. This research does
not change the production bridge or establish full World or settlement parity.

CI `39983299505` passes 79 gates in five jobs at `3b00f40`, with identical
source/tested-merge trees and verified artifact digests. It predates these cargo
and timer changes. New source remains uncooked; the latest package is still
`c655b6b`. Art, ordinary-control play, platform/performance and the remaining
native/network/settlement criteria remain open.

Exact archives under `Saved/Qualification/2026-10-23/` are
`campaign-cargo-d21013d/`, `gameplay-clock-4db3ce3/`,
`gameplay-gallery-180e093/`, `gameplay-gallery-fea8842/`, `ci-3b00f40/` and
`native-carbine-adapter-01d4e46/`. Earlier evidence below retains its source
scope; the historical timer quantization and pending native compile are
superseded by this checkpoint.

## October 23 campaign traversal and lighting investigation

The ridge/wind, helm and flood implementations are now integrated and have
actual Mac editor evidence. The release remains incomplete; these directed
fixtures isolate combat or assist health where documented, and do not establish
ordinary play balance, final art or a newly packaged build.

- At `9107ea7`, all three helm and six ridge/wind tests pass, along with held
  crank, input gating, pause and legacy water checks. The original unity-build
  failure and subsequent flood failures remain archived.
- Flood replay exposed an 89.4 cm floor gap before the descent and two companion
  collision stalls. `60ab8ee` joins the actual ramp support; `575de7e` resolves
  vertical and horizontal companion sweeps separately without disabling
  collision. At `9ebcf87`, all five flood fixtures plus legacy Water pass,
  with zero selected errors/warnings. Both early and fully risen water routes
  cross the submerged legs and gate, recover breath in real air, reach solid
  bank support with Iota attached to Toranosuke, incur no drowning damage and
  advance through the actual exit. Retry, fresh load and senses pass too.
- The first broader run retained two failures: the ridge traversal helper
  waited for an old exit center after the game had already advanced, and the
  space audit assumed flat floors and found obstructed hangar markers.
  `78d3ca0` recognizes only verified completion of the explicitly requested
  final exit leg and adds a real-wave/real-exit regression. Its Playthrough,
  RidgeExit and RidgeTraversal tests all pass.
- `6d038f4` checks actual support at authored ridge/flood heights and moves
  hangar markers into clear aisles. It retains every floor/capsule probe and
  additionally rejects traces starting inside geometry. Spaces, both hangar
  tests, RidgeExit and Playthrough all pass, with zero selected errors/warnings.
  The complete scripted traversal records eight chapters, 133 beats, 120
  checkpoint reads, 61 fresh checkpoint reloads and 13 phase reloads. This is
  assisted functional traversal, not a normal-control difficulty review.
- All 56 gameplay/tooling source gates pass at clean `9ebcf87`. CI
  `39908298194` separately authenticates 73 gates in five jobs at `d1790c5`;
  it predates this mechanics integration. Startup engine self-test diagnostics
  remain in the logs. The earlier `60ab8ee` run also retains one HTTP timeout
  warning. Post-exit TraceServer output is preserved with authenticated
  original log prefixes; no prior receipt has been rewritten.
- Same-source SM5 controls reproduce the darker entry with the rebuilt meshes
  and restore the brighter entry using the original twelve meshes with the
  candidate materials/textures. A separate controlled pair with Lumen diffuse
  indirect lighting disabled removes the large visible difference. Normal-GI
  observer captures at `9ebcf87` show changed distance-field payloads and card
  geometry in 11/12 meshes, despite equal fallback source descriptions,
  material assignments and section flags. The column matches. All four floor
  fields grow from 70 to 88 finest-mip bricks and gain expanded Z bounds.
  This narrows the investigation; it does not identify a production repair.
  All four new originals were reviewed and all 48 candidate files restored.

At `75708f3`, opening a menu cancels partial helm correction immediately and
restores the player's hands and weapon visibility. Deadline, grace and hold
progress remain frozen during pause. Both release/repress and Unreal's actual
held-key flush/repeat reconciliation must earn a fresh two-second correction;
the policy does not require a new physical key release. All eight directed
editor tests pass with zero selected errors/warnings: the four helm fixtures,
held crank, dialogue gift hold, input gating and world pause. The source-bound
editor build and independent receipt authentication pass too.

CI `39962705267` passes 76 gates in five jobs at `50ef7d6`, with
the tested merge tree identical to the source tree. This includes 279 Rust
passes and five explicitly ignored research tests; private raw assets and
native parity remain outside its scope. Root authenticated all 99 referenced
local evidence files. This run includes the two helm pause commits.

The single-floor and four-floor GI-source controls at `75708f3` both completed.
Each used an identical-settings rebuild baseline before changing only the
floor meshes' distance-field replacement source. Recorded geometry, materials,
Nanite controls and public/component culling bounds match within each pair;
only the targeted floors' SDF/card observations change. The entry floor becomes
brighter, but neither experiment repairs the broad room appearance. All new
originals were inspected and all 48 candidate files restored and independently
rehashed. No production asset or lighting change is accepted from these controls.

The ceiling-only control at `50ef7d6` also completed all six phases with EOF
receipts. Its identical-settings rebuild and replacement captures preserve
recorded geometry, materials, Nanite settings and culling bounds; only the
ceiling's SDF/card observations change. Root inspected all six originals:
the broad room appearance remains dark. All 48 candidate files were restored
and independently rehashed. This is another negative control, not a repair.

Native candidate `a984a5c` composes the bounded two-player/two-tick preparation,
carbine selection, wall/protection checks and nonlethal state updates. Its 49
standalone Rust tests, nine Python provenance tests and 52-case independent
canonical replay pass. The first actual privacy-crate compile stopped at the
owned 30 GiB disk reserve; its EOF receipt is retained. A later single-job retry
completes compilation, actual test listing and 23 CPU tests, with one proof
experiment explicitly ignored. All three phases exit zero at EOF, taking
833.839 seconds overall; the CPU tests take 24.83 seconds with 194,936,832-byte
peak RSS. Independent authentication verifies the signed source, 30 source
files, logs and exact 132,161,600-byte executable. An existing dead-code warning
remains recorded. No new proof follows from these tests. The earlier `c99ee46e`
preparation proof and current game bridge retain their own source scope; this
new relation is not registered or used for settlement.

Chapter-six b03's two climb routes, resting shelves, timed downward sentry and
physical crawl exit are integrated from reviewed `855972c`. Kohagi's physical
climb-first/roof-wait path and a shelf-approach clearance correction are now
integrated at `c5f5799`. Each frozen source candidate passed all 57
gameplay/tooling checks; those checks did not establish Unreal traversal.

The first actual build at `5c8b775` failed on a local variable shadowing a
Director member; `f8f42ab` corrects that name only. At `c5f5799`, the actual
source-bound editor build passes, but only four of thirteen selected tests
pass. All eight climb fixtures except Loader, legacy Climb and the aggregate
Playthrough fail; Loader, Spaces, input gating and pause pass. Original
failures, build receipts and terminal logs are preserved.

Diagnostic-only `623b683` builds and reproduces four focused failures. Actual
sweeps show the player and Kohagi catching at the lower rest shelf's lip, and
the extrusion route catching at the parapet lip. Their paths coincide with
the support surface height. Sentry timing reaches the first look-down at
20,000 ms for 240 frames, but that test subsequently fails while climbing to
its observation position. This is evidence for a swept-path correction,
not traversal acceptance. Collision remains enabled; no failed test is waived.

The subsequent `c26b0e1` correction adds a six-centimetre swept clearance path
across supporting lips while keeping the authored endpoints, duration and
collision. Kohagi's final downward sweep requires an actual upward support
face. Corner, Extrusion, Guide and Sentry pass in the actual editor. Seven more
regressions pass, including Playthrough, Spaces, hand control and pause/retry.
The two retained fall failures exposed a safe shelf release ending the initial
fall without arming a later walk-off. At `b94e5d7`, actual feet/support sampling
starts each new fall, and both corrected fixtures pass: a 550 cm fall applies
30 HP once, while an 1,100 cm fall is lethal and freezes correctly during pause.
At `7409833`, all eight climb fixtures and four shared climb/space/input/pause
regressions pass together. That run's only failure is the newly integrated
moat step in Playthrough, subsequently corrected below. Authored thresholds,
geometry and collision remain unchanged; ordinary play balance is unqualified.

The foundry encounter is integrated at `4019fe6`: a 1,500 HP furnace, 180-second
defense, three once-only 150 HP clay repairs, Kozo's four-second rescue and
25-second deadline, real grenadier furnace targeting and netted bellows pressure.
All 58 gameplay/tooling source gates pass at its initial integrated `5026836`.
The first actual run passes 11/12 selected tests and exposes foundry hand
reservation being overwritten by shared crank/helm handling, plus a fixture
walking directly into a clay tub. The corrected source includes foundry work
in shared hand/weapon reservation and walks clear aisles with ordinary input.
At `4019fe6`, all five foundry mechanic tests and four shared crank/helm hand
regressions pass across two source-bound editor runs. Independent terminal
authentication verifies both reports, exact source/artifacts, zero exits and
EOF. There are zero selected-test errors/warnings; startup engine diagnostics
and appended TraceServer output are retained separately. These are directed
mechanic tests, not ordinary encounter balance, final art or a new package.

CI `39975724835` passes all 78 source gates in five jobs at `c3ba8ef`, with
identical source/tested-merge trees and 99 root-authenticated evidence files.
It predates the newer climb-fall and moat integration; private raw assets and
native parity remain excluded.

Chapter-six b02's physical moat is integrated at `9f963f0`. Twelve of fourteen
initial editor tests pass, including depth, float, submerged gate/retry, guide,
hands, loader, patrols, pause/reload and traversal. Senses and Playthrough fail;
all original reports remain archived. The aggregate pickup sweep had moved the
hero to unrelated chapter zones before swimming. At `4ec2430`, the fixture
starts at the real entry, swims to the moat mark, saves its mapped pickup and
crosses the submerged gate before collecting other finds later. Playthrough
and standalone traversal both pass, covering eight chapters, 133 beats,
28 loose pickups, 120 checkpoint checks, 61 reloads and 13 phase reloads.

The corrected searchlight fixture exposes the real head through a sweep
reversal. Subsequent actual diagnostics identify a drone spending its movement
budget on distant horizontal pursuit, two reinforcement capsules blocking one
another because their patrol assignments reverse their spawn order, and an
unconfirmed suspicious guard never receiving an investigation-arrival signal.
At `54008a8`, physical spawn order assigns the posts, altitude gets priority
within the existing swept 300 cm/s flight budget, and suspicious guards retain
their usual look delay and careful approach before actual arrival permits
decay. Senses, Patrols, Traversal and full Playthrough all pass with zero
selected errors/warnings. The drone reaches 300 cm within 90 frames and moves
at most 5 cm per frame; all five guards return to Unaware with zero awareness.
Four observed searches each take 1,177 frames: the existing brain rounds each
60 Hz step to 17 ms, so its configured 20,000 ms timer is 19.616668 world seconds.
This records the existing quantization, not exact wall-clock pacing acceptance.
All 59 gameplay/tooling source gates also pass at clean `54008a8`. Runtime and
source receipts are independently authenticated through terminal EOF.

Signed native `01d4e46` adds a separate bounded carbine research adapter with
all four ray schedules and verifier-owned fixed selectors. Its 55 standalone
CPU tests, nine provenance tests and 48 canonical cases pass; independent
source review finds no actionable defect. The managed-note totals are 908 base
columns and 2,670 constraints, within unchanged limits. Earlier over-limit
and fixture failures remain recorded. Actual crate compilation is in progress;
backend wire bounds and new proofs are not yet qualified. The prior native
binaries, preparation proof and production bridge retain their original scope.

Photoreal art, ordinary-control campaign acceptance,
new packages, actual M1/Windows performance and the remaining native/network/
settlement criteria remain open. Claude's art ownership and queued requests
are unchanged during the confirmed weekly limit through October 24, 22:00 JST.

Archives: `campaign-integration-9107ea7/`, `campaign-flood-9ebcf87/`,
`campaign-ridge-78d3ca0/`, `campaign-spaces-6d038f4/`, and
`dojo-sm5-appearance-control/` under `Saved/Qualification/2026-10-23/`.
The exact normal-GI captures are `20261023T065542Z-sm5-50677` and
`20261023T065708Z-sm5-52741`; the GI-off control pair is
`20261023T062604Z-sm5-12647` and `20261023T062706Z-sm5-14737`.
The helm archive is `campaign-helm-75708f3/runtime-targeted/`, CI is
`ci-50ef7d6/`, and the bounded floor controls are under
`dojo-floor0-replacement/`. Their exact captures and limitations are recorded
in [the renderer diagnostic](render-qualification/dojo-nanite-draw.md#bounded-floor-gi-source-controls-at-75708f3).
The ceiling archive is `dojo-ceiling-replacement/` and the native source/test
review and retained resource stop are under `native-carbine-a984a5c/`.
Climb failures and source-bound build receipts are under
`campaign-climb-c5f5799/runtime-targeted/` and
`campaign-climb-623b683/runtime-targeted/`; corrected climb runs are under
`campaign-climb-c26b0e1/`. Foundry failures and corrected passes are under
`campaign-foundry-5026836/` and `campaign-foundry-4019fe6/` respectively.
The native retry is `native-carbine-a984a5c/actual-crate-2/`;
CI is under `ci-5c8b775/`.
The newer CI archive is `ci-c3ba8ef/`. Climb fall/regression receipts are under
`campaign-climb-b94e5d7/` and `campaign-climb-7409833/`. Moat failures and
corrections are under `campaign-moat-9f963f0/`, `campaign-moat-198f616/`,
`campaign-moat-4ec2430/`, `campaign-moat-defebfc/` and `campaign-moat-54008a8/`.
The native adapter archive is `native-carbine-adapter-01d4e46/`, with independent
review under `native-carbine-01d4e46/`.

## October 23 package, Codex and Nanite qualification

This update supersedes the running and pending states in the historical
October 23 sections below. The release remains incomplete.

- The completed Mac Development package is `c655b6b`, with native bridge
  `10ad7dad`. Game build, cooking (1,323 packages, zero cook errors/warnings),
  staging, strict signature validation, startup smoke, all 164 client tests
  and a separate untouched rendered Title test pass. All 62 packaged files
  retain their hashes. The independent review resolves the original cook
  receipt reference against the exact archived receipt; original evidence is
  retained. Four Metal converter include warnings and the successful existing
  Xcode-scheme retry remain recorded. Root inspected all 19 front-end frames
  and the separate fresh Title. This is M2 Ultra development-package evidence,
  not clean-machine, M1, Windows, performance or normal-control acceptance.
- The package exposed a translucent Title backdrop that allowed paused-world
  geometry to show through. `770a618` makes the backdrop opaque. Its fresh
  isolated-profile Title and five directed editor gameplay/UI tests pass;
  root inspected the original fresh Title. The Codex now has sourced Toshiya
  copy and explicit end-of-reader capture. All nine original frames at each
  of 720p and 1080p pass their scoped readability/scroll/footer review. The
  49-entry capture ledger is prepared; earning and reloading have separate
  directed tests. This newer UI source has not been repackaged.
- The bow HUD correction at `92011bb` passes the unchanged pixel gates and
  original-frame review at 720p and 1080p, resolving the historical target
  obstruction below. An initial missing-glyph diagnosis was retracted after
  inspecting intact original pixels; no font repair was made.
- CI run `39905369237` authenticates all 73 source gates across five jobs at
  `783a3eb`; merge `183c9abc` has the exact same source tree. Downloaded artifact
  IDs, sizes, hashes and raw job logs agree. Five explicit Rust research tests
  and six private-asset tests remain outside this source suite. Later importer
  revisions require separate qualification.
- The real production-dojo baseline at `6e0e99c` passes its runtime fixture but
  fails the SM6 Nanite draw gate: all 12 recorded DojoKit assets lack Nanite
  resources, the ceiling has zero qualifying Mask/Triangles coverage, and
  green entry coverage belongs to cargo props. The separate SM5 conventional
  capture passes its limited diagnostic. Root inspected all six SM6 originals
  and both SM5 originals. The earlier compile, cached-bounds and pixel-gate
  failures are retained.
- Importer `a8ecee6` now builds Nanite from the same hash-verified FBX as a
  separate source, keeping ordinary LODs on their original builder. All 12
  modules pass actual import, fresh-process reload and repeat import; the
  repeated audit objects match exactly. They contain 21,984 Nanite input
  triangles. Exact oriented conventional geometry, UV0, normals, tangents,
  materials, collision metadata and fresh-import screen thresholds are
  preserved. UV1+ values and vertex colors are outside this readback. Earlier
  API and shoji geometry failures remain recorded; the geometry check was not
  weakened. All current modules have one LOD with fresh-import threshold zero;
  this does not claim preservation of the previous saved asset's threshold.
- The actual M2 Ultra SM6 draw diagnostic at `a8ecee6` passes. Root inspected
  six originals: broad Mask and Triangles coverage now belongs to the dojo's
  walls, floor and ceiling. All 24 registered components have Nanite data and
  conventional fallback data. The separate SM5 runtime/capture also passes,
  but its entry floor and some props look darker than the previous SM5
  baseline. Root inspected both before/after pairs; the appearance difference
  remains unresolved. Neither this renderer result nor the 22 importer host
  tests establish photoreal art, unique beams, cooked fallback, M1 or performance.
- Signed native `c99ee46e` completed one actual preparation proof, separate
  verification with a rebuilt adapter, 27 public-input mutation rejections,
  two corrupt/truncated-proof rejections and eight actual prover Constraint
  rejections. The proof is 2,717,600 bytes; proving took 762.916 seconds and
  verification 17.239 seconds. The cohort took 3,127.68 seconds with
  1,246,937,088-byte peak RSS. Independent terminal authentication passes;
  the stale running snapshot is superseded by terminal receipts. This is an
  unregistered, caller-bound two-player/two-tick preparation component, not
  Core authority, full World/history, a full match, registry, settlement or M1
  qualification. The staged native bridge is unchanged.
- The W09 correspondence-priority diagnostic's six source renders have now
  been inspected. It still fails the unchanged normal requirement and remains
  unadmitted. The historical statement that these renders were pending is
  superseded; no production geometry was replaced.

At the earlier checkpoint, chapter-seven ridge/wind and helm work and
chapter-six flood work were still under review. Their later integration and
runtime results are recorded in the update above. Ridge follow-up `7d72c94` fixes terminal falls destroying the
pawn before retry and five spawns inside a shuttle proxy. Helm `3a1fef7` fixes
its visible hold boundary and reserves the player's hands during wheel work.
Flood `d8d4a01` fixes the bank ramp and gate opening; its companion ascent stall
has a separate `f58528c` correction using actual capsule support and walking.
These source reviews do not establish engine behavior. Their engine execution, final geometry/art/audio and normal
pacing remain open. Claude's last confirmed weekly limit remains October 24
at 22:00 JST, with the existing art requests queued. Its uncommitted timber and
curtain work is untouched and unadmitted. Final art, remaining authored
mechanics, ordinary-control acceptance, new packages, Windows and actual M1
performance, full native execution and settlement remain required.

Exact local archives include `Saved/Qualification/2026-10-23/package-c655b6b/`,
`ui-770a618-bound/`, `ci-783a3eb/`, `native-c99ee46e-terminal-review/`,
`dojo-nanite-import-a8ecee6/`, `dojo-nanite-import-a8ecee6-repeat/`, and the
source-bound original captures under `Saved/Capture/`. The new renderer archives
are `20261023T054521Z-sm6-60895` and `20261023T054701Z-sm5-62942`.

## October 23 bow, wood and source qualification (historical)

This update supersedes the running states in the historical updates below. The
release remains incomplete, and the latest packaged baseline is still `44ffc35`.

- CI run `39872957667` passes all five source groups for `53d972c`: 67 checks
  across gameplay, assets, tooling, audio and Rust. The tested merge `26d5f7a`
  has the exact same tree as the PR head. Root verified the downloaded reports,
  unchanged source and artifact hashes. This resolves the earlier Arabic font
  checker failure; later commits require their own CI evidence.
- Bow candidate `8ea1446` passes five source-bound editor tests with zero
  selected errors/warnings. Full draw takes 650 ms, followed by four steady
  seconds; the observed 60 Hz onset is 4.666667 seconds. The reticle, held yumi
  and released arrow use the same camera-local aim ray. Sway amplitude, periods
  and ramp are explicitly provisional tuning, not authored numerical values.
  The live Metal SM6 capture at `8ea8dcd` passes its runtime test but fails
  rendered qualification: the real 720p story panels cover the central target
  and reticle, so the four-arm pixel check correctly rejects it. All four
  original frames and metadata are preserved, including the actual release
  ray and finite ammunition change. Production HUD repair is in progress;
  neither capture-only hiding nor weaker image thresholds qualifies a repair.
- Wood candidate `fa9d353` builds and passes all nine source-bound editor tests,
  with zero selected errors/warnings: WoodExplore, WoodExitOnly, WoodLoader,
  ArcheryLesson, ArcheryReload, Playthrough, SaveRoundTrip, ForgedSaves and Spaces.
  The completed range opens a walkable junction with an optional wood route
  and a smithy bypass. Discoveries and collectibles persist independently;
  a real arrow from the 45 m vista unlocks the clapper codex reward, while
  misses, melee and shots from outside the vista do not. Only the authored exit
  completes the optional beat. The imported source passes 60 gameplay/tooling/
  asset checks at `db5aea1`; the subsequent compiler-shadow and actual arrow
  registration corrections are covered by the `fa9d353` engine run. Terrain,
  POI props, clapper sound/craft and ordinary-control pacing remain unfinished.
  Durable codex navigation is being audited separately from the unlock API.
- Signed native research `357c722` passes 28 standalone actual-source field
  checks and five provenance guards for a bounded two-player, two-tick
  preparation slice. Root verified all committed/captured source hashes and
  the signed checkpoint. Actual privacy-crate compilation and all ten exact
  preparation tests pass (4.12 seconds, 72,450,048-byte peak test RSS). The
  original report collector fails on multiline test diagnostics; that failure
  is preserved, and root independently verifies each test block, process exit,
  terminal summary and frozen binary/source hashes. These checks bind accepted
  controls and the incoming state for supported cases;
  they do not establish a native proof, registered profile, full World/history
  execution or settlement. The staged bridge remains `10ad7dad`.
- The bounded W09 oriented reducer reaches the unchanged 4,654-triangle target
  with all 2,177 joint-boundary pins preserved and zero UV0 overlaps or winding
  reversals in either UV field. Maximum same-UV XYZ error is 13.694 mm. Six
  source renders compare LOD0, the actual saved LOD2 and the candidate at close
  and distant views. Root reviewed all six: close brass highlights/faceting
  change, and still images do not establish a satisfactory LOD transition.
  The independent normal metric remains 0.0299 below the unchanged 0.04 floor.
  This is an unadmitted diagnostic; no production asset bytes changed. A new
  correspondence-priority experiment passes 30 CPU checks and reaches the same
  4,654-triangle target with all pins intact, zero UV0 overlaps/reversals and
  unchanged source. Maximum same-UV XYZ error falls to 8.357 mm; UVMetric's
  maximum is unchanged and anisotropy percentiles do not uniformly improve.
  Its rendered comparison is pending. These are diagnostics, not admission.
- Claude's last confirmed weekly limit remains October 24 at 22:00 JST; the
  existing requests are queued. Its uncommitted timber/curtain work has not
  been admitted. Final art, remaining authored mechanics, ordinary-control
  campaign acceptance, Windows/M1 execution and performance, full native proof
  and real settlement remain required.

Exact local evidence is retained under `Saved/Qualification/2026-10-23/`, the
failed `Saved/Capture/20261023T000254Z-sm6-49156/` archive, and the isolated
source-validation worktree's `Saved/Qualification/lod-uv-diagnostic-20261020/`.

## October 23 earlier qualification update (historical)

These results supersede the October 20 running states below. The release remains
incomplete; each result retains its exact source and platform.

- Mac Development candidate `44ffc35`, native `10ad7dad`, passes Game build,
  cook (1,323 packages, zero errors/warnings), staging, strict signature checks,
  startup smoke, untouched rendered Title, and **152 client automation tests
  with zero selected errors/warnings**, including the rendered front-end tour.
  The former tower floor-placement failure is resolved in this package.
  All 60 app files match the same candidate hashes before and after execution.
  Nineteen original menu frames are retained; Title and both Credits views were
  reviewed in this run. The Back glyph masks match before/after scrolling.
  This is local M2 Ultra evidence, not clean-machine, M1, Windows, performance,
  final art or ordinary-control campaign acceptance.
- CI run `39424130199` at `44ffc35` passes gameplay, Rust, tooling and audio;
  assets fail only because the old source checker requires Arabic credit letters
  in the Japanese font. Its tested merge has the exact same tree and unchanged
  source. Repair `efec4a8` bundles the identical 146,548-byte OFL Arabic font,
  records its rights and hash, and makes source checks and runtime use the same
  project file. Coverage now includes staged credits and routes each character
  through the actual composite's Unicode blocks. Independent review and all
  25 asset/tooling CPU gates pass at the equivalent isolated `e31e249` source.
- Integrated `c841a8d` fixes the real `OnParried` missed-step hint and enables
  the learned dojo guard/stamina cycle. Only accepted points arm zanshin;
  a continuous 500 ms guard grants +15 once, while refused flank bouts earn
  none. Actual-input tests cover guard/parry/recovery, hint delay and pause,
  swept Step, retry, pending-reward fresh load, finite archery and traversal.
  The first seven-test editor run passed on October 21 but omitted the optional
  source-bound artifact receipt; it is retained as ordinary development evidence.
  The fresh October 23 run builds with the exact candidate declaration and
  passes eight tests (adding Campaign.Maai), with zero selected errors/warnings.
  Its source, module and artifact receipt are retained together. The same clean
  source passes all 57 gameplay/tooling/asset source gates and a fresh Metal
  SM6 front-end tour with zero selected errors/warnings. Nineteen original
  frames are archived; only the two Credits views were reviewed in this run.
  Exact original-pixel Japanese/English Back masks agree across the scroll.
  The Arabic filename lies outside those two views; its coverage is established
  by the separate shaping test, not visual review of that line.
- Pupil candidate `876f539` loads the actual b03/b04 timing fields and scales
  windups by difficulty. b03 repeats every 1,450 ms from onset; b04 has a
  600 ms base windup and 1,000 ms recovery from actual contact. The visible
  telegraph lifetime matches each scaled windup, with stagger/turn locks still
  delaying the next attack. All 58 gameplay/tooling/assets source checks and
  nine actual source-bound editor tests pass with zero selected errors/warnings,
  including real timing/contact/guard/parry observations on all difficulties.
  Independent review found coercible JSON numeric fields; the strict-type
  correction `24f27f9` passes its fresh source-bound actual loader/timing
  regression with zero selected errors/warnings. Boolean, numeric-string and
  null timing fields and malformed non-lesson pattern fields are rejected.
  Final straight/diagonal presentation and human pacing remain open.
- Signed native research `47db4112437ad34e8a6ca1f47dd67dfddf060b31` completes five
  actual component proofs, separate verification, 44 statement mutations and
  ten corrupt/truncated-proof rejections, seven exact native prover `Constraint`
  rejections, and 16 unit/regression checks. The whole cohort took 8,198.529 s
  with 1,350,336,512-byte peak RSS on this M2 Ultra using two workers. Root
  verified the signed commit, proven source blobs and all 18 artifact hashes.
  The staged bridge remains `10ad7dad`. This supplied-boundary two-player
  component is unregistered; canonical control authority, complete World/history
  composition, full-match proof, settlement and reference-M1 gates remain open.
- W09's all-UV0-boundary collapse reaches 4,654 triangles with zero out-of-range
  corners but introduces 34 orientation reversals and 1,011 positive-area atlas
  overlaps. Protecting both UV fields retains every pinned signature but yields
  4,766 triangles (112 over budget), 37 reversals and 3,516 overlaps. Both are
  rejected as repairs. The source and original control have zero such overlaps.
  No asset bytes or acceptance thresholds changed. The next experiment prevents
  interior orientation reversals before each collapse. Its first bounded run
  retains every protected signature, zero UV0 atlas overlap and zero winding
  reversals in either UV field, with unchanged source bytes. It stops at the
  400,000-operation cap after 6.907 s at 6,028 triangles, 1,374 above target;
  391,397 heap entries were stale. The largest same-atlas XYZ error is
  2.759 mm and UVMetric error 0.000127. This improves the diagnostic but does
  not meet the triangle target or resolve the independent normal-map failure.
  No production asset has changed.
- Claude's branch remains `b17453d` with uncommitted timber/curtain/importer work.
  Its last confirmed weekly limit is October 24 at 22:00 JST. Existing requests
  remain queued, and the coordination mailbox carries the latest integration
  evidence. No new Claude output has been admitted. Pupil attack presentation,
  visible bow sway, optional wood/clapper play, remaining reserve rules, final
  art, normal-control play and all remaining release gates still require work.

## October 20 qualification update (historical)

These results supersede the running-state descriptions in the retained milestone
history below. The release remains incomplete.

- Mac candidate `298ed9e`, native `10ad7daddf`, passes Game build, full cook
  (1,316 packages, zero cook errors/warnings), staging, strict signatures and
  before/after artifact identity. Startup smoke and the untouched rendered title
  pass. The full Metal suite completes 148 tests: **147 pass, one fails, zero
  test warnings**. `Campaign.Spaces` fails four chapter-eight spawn-floor checks.
  `ScriptedFight`, `FrontEndScreens`, `GalleryPois` and `NativeLoader` pass.
  This package fails qualification. Its 19 front-end frames were viewed.
  A prior missing-Credits-label finding was incorrect: comparison of the
  original PNG pixels and an enlarged crop confirms both `戻る` and `Back`
  before and after scrolling. The original reviews are retained with an
  explicit superseding correction; temporary layout probes were reverted.
  A separate editor diagnostic records 21 missing-Arabic-glyph warnings from
  a credited filename. The later shared font composite adds the existing Noto
  Arabic face with an explicit package rule and complete license notice;
  Japanese/English retain their original face. At `44ffc35`, actual mixed-script
  shaping with last-resort fallback disabled and 720p readability both pass.
  The unchanged SM6 menu tour passes with zero selected-test warnings/errors.
  All 19 fresh frames are archived; the two Credits views were reviewed and
  retain readable Back labels and footer controls. The Arabic-title line is
  outside those two views. Actual packaged font/license staging remains pending.
  Title tracing shows
  the tour's injected Enter; it does not establish the historical full-suite
  initial-state cause.
- All five CI source groups pass for `298ed9e` in run `39416677000`. The tested
  merge `3e45733` has the same tree as that head, and all downloaded reports
  record unchanged source. Run `39420723898` also passes all five groups for
  `7990cac`; tested merge `9e063f7` has the same tree and unchanged source.
  The later gallery-cache candidate `a8dfcf7` passes
  45 local gameplay/tooling source checks. At `383d113`, eight of nine directed
  editor tests pass; one passing LiftReload test retains an HTTP connectivity
  warning. The new `GalleryCache` test passes actual equip/shot/Interact,
  bounded arrow reward, exact memory dialogue, repeated-use rejection and
  retry/save/reload checks. `Spaces` remains the sole failure.
- Collision diagnostics at `383d113` establish the four floor mismatches:
  spawns 1/3 hit `SpireRamp32` at 911.490/903.123 cm rather than 900;
  spawn 7 hits `SpireRamp63` at 1808.410 rather than 1800; spawn 8 hits
  `SpireL3Shortcut` at 1814.035 rather than 1800. These are overlapping rising
  surfaces, not absent floors. Candidate `51f1c25` moves the formations onto
  the incoming flat landing approaches, retaining the strict floor and capsule
  checks. All six directed editor tests pass: Spaces, Playthrough, SpireTraversal,
  SpireAuditorShutter, SpireSupply and SpireCompanions. The last retains one HTTP
  connectivity-probe warning; there are no selected-test errors. The generated
  campaign and five host spire checks also pass. A rebuilt package remains
  unqualified.
- The chapter-one archery blocker is repaired in candidate `44ffc35`: physical
  targets replace sparring pupils, mapped key 3 equips the unlocked yumi,
  six resolved near shots require four hits, and three swinging targets require
  distinct arrow impacts. Timed retrieval, finite chapter-one arrows and the
  six-usable/six-bent smithy handoff are implemented. ArcheryLesson, ArcheryReload
  and the aggregate Playthrough pass actual editor execution with zero selected
  warnings/errors, alongside the two font tests above. The integrated source
  at `8fb35cf` passes all 46 gameplay/tooling checks; its original compile
  failure is retained, with explicit wave scopes and a direct catalog include
  fixing both causes at `44ffc35`. This candidate's fresh full Mac package is
  running. Authored aim sway after four seconds, the optional clapper challenge,
  other chapters' reserve contracts and final target/weapon art remain open.
  Normal b01–b06 controls are source-feasible but have not
  been qualified by a continuous ordinary-input run. Also open: the real
  awase event does not start the missed-marobashi hint timer, dojo play skips
  passive zanshin, and pupil windups lack the authored variation. Directly
  recorded forms, synthetic marobashi and lethal test damage establish none
  of those authored interactions.
- Frozen native research has completed five actual component proofs:
  parry (3,027,008 bytes), marked ward (3,014,624), and simultaneous contact
  (3,012,512), stance (3,010,688), and plasma (3,005,120).
  Each has separate verification and rejected
  statement/proof mutations; root checked the proof and six source hashes.
  The seven actual prover-negative checks are still running. This is unregistered
  research, not the staged bridge, a complete accepted-control/World proof,
  settlement or reference-M1 qualification.
- Saved-source W09 diagnostics reproduce the original two out-of-range UV
  corners on the barrel, then obtain 4,654 faces and zero out-of-range corners
  in three in-memory weighted-collapse variants. Protecting all barrel chart
  boundaries retains all 270 exact boundary geometry/UV signatures. Uniform
  weights alone also change the result, so the experiment does not establish
  that pinning is the unique cause or qualify a repair. All six controls repeat
  exactly across reversed order and two fresh Blender processes. Sampled overall
  shape error is at most 0.224 mm, but chart-constrained error reaches 183 mm:
  texture-chart migration remains even with barrel-only pins. Uniform weights
  worsen maximum UV0 anisotropy; the existing normal metric also still fails.
  An experiment protecting all UV0/UVMetric seams and measuring correspondence
  at identical atlas coordinates is prepared but has not run. No art bytes,
  textures or acceptance thresholds changed.

## Milestones and evidence

| ID | Deliverable | Owner | Current state / completion evidence |
| --- | --- | --- | --- |
| T1 | Reproducible Mac development toolchain | Codex toolchain lane | UE 5.8.3 / CL 58210709 installed and identity checked on M2 Ultra. Xcode 26.1.1 / 17B100, SDK 26.1 and Metal 17B54 installed; doctor and editor build pass. Full imports/validators pass for 280 original-art, 345 CC0 and 267 audio packages, 27 VFX systems, the craft prop and 12 dojo-kit modules. Actual SM5 and SM6 captures pass on this M2 Ultra. Xcode 27 and global selection are preserved; that compiler has not been qualified for this project. |
| G1 | Complete authored offline campaign mechanics | Codex gameplay lane | At clean `c45ec6c`, the Editor build and seven directed tests pass, with zero selected-test errors/warnings: collateral constructs, seizure phase ownership, physical seizure tiles, summit phases/reload, generic ValAmort and the full 133-beat/eight-chapter traversal. The construct test confirms both one-second held core release and two actual 130-damage hammer contacts, including closed-core rejection and interruption/expiry. Phase ownership keeps concurrent seizure hazards active, suppresses/cancels shielded beam/cleave attacks, permits the ten-second P2 respawn and rejects stale respawns after P3 transition or saved P3 reload. Its earlier late-cut and second-hammer fixture failures are retained; the corrections synchronize to actual game-time deadlines and commitment/contact events. Telemetry records 61 checkpoint reloads, 13 phase reloads and 76 worlds. Earlier `e871c2d` Playthrough/BellowsTreads pass 2/2 after completing the actual held net rescue; the historical `56b95f3` campaign/fieldcraft/Connect suite passes 62/62. Held spine draw-cut, named carry capacities, cooperative cranks, alternating bellows treads, exact hammer/weaving rhythms, optional rhythm assist and physical lift/spiral/summit traversal are integrated. At `febb516`, five further editor tests pass without selected errors/warnings: CollectorCapture, full traversal, SpineDrawCut, ScriptedFight and generic ValAmort. The actual mapped-input fixture rejects sheathed hammer/kanabō/wakizashi capture attempts, accepts the katana, and verifies the first-foreclosure memory replays once despite earlier dialogue deduplication; later 1%-floor attempts refresh only the prompt. The auditor shortcut candidate at `a8d541d` fails three of five directed editor tests: its new shutter test and the existing spiral navigation/companion-ascent tests. The full traversal and chapter-six alarm lectern pass. The auditor stops above its L3 destination, a corner sweep misses its expected rail, and the continuous navigation route is disconnected; the failed run and exact build receipt are retained. The `62d6fe6` repair passes all five directed editor tests with zero selected errors and one retained HTTP connectivity-probe timeout warning. The landing guards now preserve the complete ramp footprint; the auditor reaches the grounded L3 panel, an occupied doorway defers physical shutter closure, the route grows from 1,596.00 to 1,966.10 cm, and all five companions traverse the continuous ramp. Death/retry restores the shutter. The authored L1 supply cache at `5f7958f` passes EquipmentRecovery, full Playthrough, SpireTraversal and SpireCompanions, but its first supply fixture fails because the attempted jump never establishes airborne movement. The fixture-only correction at `e3e116d` passes SpireSupply with zero selected errors/warnings: mapped Jump raises the actual falling capsule 8.36 cm with positive vertical velocity, supply reach is false, and inventory, obstruction, reload, retry and input/profile cleanup checks pass. Production supply code is unchanged; the original failed run and both exact build receipts are retained. Goods/core visuals remain functional proxies. Accelerated NullRHI traversal does not establish normal-control pacing, renders, package or performance acceptance. |
| G2 | Complete playable campaign spaces and encounters | Codex + Claude | Use authored layouts, patrols and encounters; verify traversal, collision, navigation, interaction reach, stealth and boss behavior. Verify all eight chapters and 133 beats with normal controls; headless shortcuts do not establish pacing or difficulty. |
| U1 | Readable bilingual gameplay and accessible controls | Codex HUD lane | At clean `5f7958f`, the complete Metal SM6 HUD matrix passes all nine prepared scenes at both 1280×720 and 1920×1080, with zero selected-test errors/warnings. All 36 actual images were viewed and their hashes retained. Measured dark backing resolves the gold Examine text over bright bellows and objective labels over bright dojo surfaces, while ordinary Work remains above coaching. No blocking overlap or clipping appears in the matrix. Earlier `febb516` hidden-prompt and `495170d` low-contrast visual failures remain preserved. Both original logs received trace-server shutdown output after their capture manifests were written; reviews retain and bind the exact original prefix, appended suffix and final full log separately. The owned-stream runner at `977c12d` then passes one actual Metal SM6 BellowsGamepad capture at 1280×720: one selected test, zero errors/warnings, two original frames viewed, editor/runner exit zero and inherited-stream EOF true. Its manifest and completion receipt match the entire final raw log, including trace-server shutdown. The earlier wrong-filter invocation remains preserved as a failed launch with correctly retained exit 3. The runner also passes 47 CPU process/report/source tests. U1 remains open for normal-control play, dense bilingual screen coverage, small projected labels, accessibility, motion and packaged/platform qualification. Prepared stress scenes do not establish those gates. |
| A1 | Unique timber kit and golden-hour Estate/dojo slice | Claude | Nanite policy integrated. Explicit material permutations and reimport resolve prior coarse sampling in same-source `2bb3e36` SM5/SM6 dojo frames; all twelve viewed. Repetitive box geometry, clipped light and placeholder props still fail photoreal acceptance. Claude’s chapter-one sun/sky presets are integrated at `e3b8aa5`, retaining existing intensities and default-off Mac volumetric fog; preset checks pass 20 tests with one skip. All three directed stealth tests pass at `aedfba0`. Paired 1920×1080 SM5/SM6 dojo capture tests pass at `184a7b6`, with zero selected errors/warnings; all twelve images were viewed. Warm direct sunlight and resolved texture are visible, while clipped white exterior/windows and lamp highlights, repeated motifs, box beams, crates and red cylinders still fail photoreal acceptance. Unique per-placement timber binaries, dressing, provenance/fallbacks and visible Nanite draw evidence remain open. On October 20, Claude’s weekly limit blocks new art responses until October 24 at 22:00 JST. The existing coordination message remains queued; both background generation jobs report completed. Uncommitted timber outputs total 128,480,373 bytes across 91 files and have not been admitted or runtime-qualified. M2 SM5 does not qualify M1. |
| A2 | Complete character and first-person presentation | Claude | Nyaakoto, paws, sword/saya, clothing, fur and motion must pass [photoreal acceptance](art-direction/photoreal-acceptance.md) in actual gameplay and cinematics. Generated references and Blender images are source evidence only. |
| A3 | Complete campaign/arena art, animation, audio and effects | Claude + Codex integration | Extend approved visual direction across every environment, character and encounter; complete dialogue presentation, cinematics, sound, music and effects. Review every asset's rights and ledger records. Missing original references remain explicit, rather than being claimed as matched. |
| Q1 | Repeatable source validation and CI | Codex validation lane | CI run `39408861085` for `1bbe026` passes Rust, gameplay, tooling and audio; assets fail on that pre-recovery source. Run `39411591370` for PR head `f550122` passes all five source groups: Rust, gameplay, tooling, audio and all ten asset gates. Its clean tested merge `7534d2d` has the exact same tree as `f550122` (`c139e933`), and the downloaded asset report records unchanged source. The isolated W14 recovery `ff53357` rebuilds the truncated source image with the unchanged committed generator, verifies all eight output hashes and seven PNGs, and passes the independent tracked PNG/JPEG scan 766/766. Fresh weapon metrics pass 11/17, retaining six geometry/UV/normal failures and four excluded blockout designs. After verifying the other 143 non-blockout output hashes and all 26 third-party source inputs, the runtime inventory is reconciled. Twelve unchanged blockout previews are recorded separately from their recovery evidence without runtime admission. At integrated `3b0a662`, all ten asset source gates pass with unchanged source. The default ledger has zero errors and one existing plain-Git fern warning; generated notices pass. See [recovery evidence](recovery/claude-2026-10-18/W14_RECOVERY_20261020.md). Earlier 228 ledger errors and the 765/766 image failure remain preserved in prior reports. Image integrity/runner/parser tests pass 46/46; HDR/SVG remain outside that focused gate. Source checks do not establish visual, engine, package, performance or live-network qualification. |
| N1 | Matching native kernel and Connect integration | Codex | Kernel ABI4 stages and passes 94 parity cases/99,043 ticks. Signed clean native `10ad7daddf` passes29/29 directed tests and has a fresh frozen ABI30 release build with its original sidecar. All29 frozen files and six consumer hashes were checked before staging; actual UE NativeLoader passes in the `56b95f3` editor and the `b4a02d1` packaged Metal client, with the exact staged library path. Strict package/artifact hashes verify before and after execution. These tests cover loading, binding, canonical JSON and hashing; signing, submission and finality are not tested. Earlier producer records remain preserved. Windows loading remains unverified. |
| N2 | Complete native execution proof and real settlement | Codex | Signed clean native `64326660bc` adds an unregistered attack-initiation arithmetic component. The actual Core/privacy/codec Cargo cohort compiles, and five privacy-crate attack tests pass, including 5,328 canonical-prefix observations and forged-output rejection. Root verified the signature and qualification record; copied-equation mixed cases and width measurements remain supplementary. Parent `65e4ded205` passes 52 actual Core game/item/resource tests, including unequal deposits and deferred allocation awards with owner-only redirects, plus authenticated ABI30 unit consumers/custody-refusal tests. These are component results: the new attack source has no registered Arena profile, STARK proof or accepted-control/World binding. A subsequent frozen, uncommitted ordered-contact research source has produced its first actual parry proof: 3,027,008 bytes, proving 1,044.546580 seconds and separate verification 24.814912 seconds on this M2 Ultra using two Rayon threads in the debug test binary. All eight rebound statements plus corrupt and truncated proofs are rejected. Root independently verified the proof hash and all six source hashes and retained the completed first-case evidence. Four proof cases and seven actual prover-negative checks remain running; this unregistered supplied-boundary component has no accepted-control/World binding or settlement route, and is not the reference-M1 full-size qualification. Ordered attack/hit/damage proof composition, conserved awards, disconnect handling and complete authenticated state remain open. Require actual four-validator test-XOR admission/dispute/settlement and market evidence, Connect exact-action signing/finality recovery, and full-size proof qualification. |
| R1 | Windows and Mac release candidates | Codex | Fresh declared candidate `b4a02d1` with native `10ad7dad` passes Editor/Game build, full cook (1,314 packages, seven platform skips, zero UE cook errors/warnings), and staging with strict signature and source/artifact verification. The rejected `56b95f3` archive remains preserved; the narrow staging guard fix records newly created Crypto metadata separately. Packaged startup smoke passes with Entry/SoraGameMode, Japanese and exit 0. The real-Metal packaged suite completed all 131 tests: 126 passed without warnings, three passed with four GC/memory timing warnings, and two failed (ScriptedFight epilogue sequence and FrontEndScreens initial menu state). This candidate fails qualification. Full campaign playthrough, native loading, practice matches and stealth subtests pass; original JSON/logs, 19 menu frames, process exit 3 and post-execution identity checks are preserved. The missing HTML report template is recorded and corrected in the next source. The epilogue correction subsequently passes in the editor. The unchanged packaged menu test passes 1/1 alone in a fresh process, with zero errors/warnings and 19 frames; its full-run initial-state cause is unproven. At `be5e365`, the untouched rendered startup gate passes 1/1 with zero selected-test errors/warnings in an uncooked editor-binary Metal launch at 1280x720. Its title frame was visually checked; the verifier confirms title/focus, paused state, catalog, arena, rendered geometry and PNG integrity. This is not a packaged or clean-machine start result. Separately, 19 pre-test engine smoke errors are attributed to two UnifiedError message tests (11) and StructuredLogFormat (8); the first two compare localized Japanese text with hardcoded English. Their errors are preserved outside the selected-test result. An English-only diagnostic at `1729001` passes all three named engine smoke tests with zero automation errors and an unchanged project module; the process required an external termination request after its Quit command, so this is culture-comparison evidence only. No project language default or engine source changed. Require clean-machine install/start, campaign completion, saves, controller/accessibility, Japanese UI/default English subtitles, multiplayer recovery and performance. Windows, actual M1 fallback and M2 Nanite results remain separate. |
| R2 | Complete release acceptance | Codex + user visual review | Close every gate below, review unresolved defects, and deliver identifiable packages and their source/evidence. No milestone is completed by relabeling prototype content or weakening a gate. |

## Release gates

The acceptance sources are [offline campaign acceptance](campaign/offline-acceptance.md),
[photoreal acceptance](art-direction/photoreal-acceptance.md),
[render qualification](render-qualification/estate-lumen-nanite.md), and the
[implementation release gates](implementation-status.md#release-gates).

- Reproducible Windows and macOS builds on UE 5.8.3 / CL 58210709.
- Complete campaign, content rights, playtesting, accessibility and measured
  frame times: 1440p/60 fps on RTX 4070-class Windows hardware and 1080p/60 fps
  on the M1 Ultra Mac preset. M2 testing does not qualify M1.
- Deterministic simulation parity and reviewed complete FPS execution AIR,
  with actual proof generation/verification for financially relevant rules.
- Real four-validator admission, dispute, settlement and NFT market tests;
  exact-action Connect signing and verified finality/recovery.
- Full-size 12-player proof at most 30 minutes and 96 GiB on the reference
  M1 Ultra host.

Live funding and trading remain disabled until their gates pass. No production
network, asset identity or test account is guessed. Tests and evidence must name
the actual source revision, platform, toolchain and limitations.

## Integration order

1. Establish T1 and Q1 while G1 and Claude's A1 source production proceed.
2. Integrate reviewed gameplay and art commits. Build/import in the integration
   worktree, verify runtime SM6/SM5 asset selection, then run directed campaign,
   stealth and capture checks before accepting the first playable slice.
3. Complete G1/G2 and A2/A3 in reviewable chapter/character slices. Re-run affected
   save, combat and navigation checks as presentation changes land.
4. Complete N1/N2 and R1 with separate native, engine and platform evidence.
5. Close R2 only when the actual release gates pass. A blocked external platform,
   reference or credential requirement stays visible and does not stop independent work.
