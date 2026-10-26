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

## October 26 archive reveal validation

The archive's procedural rack-impact reveal now runs on a twenty-second active
clock: a 4.6-second visual prologue followed by the existing 15.4 seconds of
family dialogue. It owns the real camera, blocks actions, pauses with the
game and defers the mid-duel checkpoint until the exchange finishes.

Exact signed `956a43ef` builds and passes thirteen of fourteen directed runtime
fixtures, including reset, exit and the assisted complete campaign. One
combined final rack/rival rotation assertion fails in both queue cases; the
remaining scene timing, camera, input and save assertions pass. The failed
evidence is preserved and independently authenticated as
`fbcd26a7e41dd5a47ede646f894dd32d5c3488aeb473a952fe2917119ccefbeb`.
The corrected `714f490e` passes both ArchiveFamilyPage and ArchiveRevealReset.
The final rival pitch is -0.000053120 degrees in both queue cases and the rack
is zero, confirming that the original assertion was below the engine setters'
precision. Runtime review:
`5684df256a536cba71e63e6c20ed9ffba960cacd6a412efdc88846232d33beb7`.

Its six-frame 1920×1080 SM6 capture passes the functional camera/clock checks,
but all six originals were reviewed and the presentation is rejected. The
opening is nearly black, the lit slate clips to white without readable text,
the rival and equipment obscure it, and combat HUD covers the scene. Review:
`116878f4f6db7c487beff1dd9cd86ba876bd15655d2b3af60d5df0d9d07aabf7`.
The `4f3fe61f` source candidate adds the authored Japanese household record to the
physical slate, cyan rack lights and a high-window rim, moves the rival aside
before the close-up, and retains only subtitles/captions during the scene.
It also removes the capture's artificial million-health readout. It builds
and passes ArchiveFamilyPage, ArchiveRevealReset and the assisted 133-beat
campaign; review
`10b61453c182b01d1158c6e794058cf1754e11b11905adad144e6f81edcb2203`.

Its six new SM6 originals show the room and characters, clear the rival from
the page close-ups and retain only dialogue. Presentation still fails: the
font's actual line metrics overflow the plate, cutting off purchase price 30
and the unit row; text is too dim, and subtitles overlap the bottom. The
lights are too broad/bright and the art remains visibly provisional. Review:
`be39e888ec88eee9d82bd9c1171d89735fc10b43c5e4a7f0df1772c75061b076`.
The follow-up source reduces type and spacing, increases text contrast and
pulls the camera back. A runtime regression measures the real Slate desired
size against the world widget's render target. Signed `602b862f` builds and
passes both archive fixtures, including the measured layout assertion; review
`108448e535fa69172976348b83d2620621f8a4eeaa894a7941e7baa83d461f41`.
All six new 1920×1080 SM6 originals were inspected. The entire record is
readable, including purchase price 30 and units, with subtitle clearance in
both close-ups. Natural exits, all 34 evidence files and unchanged inputs
verify; review
`f328ecbd467e666b499b22c4f6ce01a0f13b64067aef7a5e16f3518b35741952`.
The broad lighting, flat racks, character materials and floating weapon remain
visually rejected. Final character animation, sound, art, ordinary duel play
and package qualification remain unfinished.

Source CI at `602b862f` passes all 110 checks in run `40243327875`, with the
same tested/source tree, five authenticated artifacts and raw logs; review
`74f106652c47ed243b86034f0d84a25b11ffc16bbae7c694336c75179d9d4f5a`.
The previous `4f3fe61f` also passes all 110 in run `40242427537`; review
`aae45319016365ab86d2c8011a3dee96b0c635ebb94149c9ea17083d0e53dd41`.

Source CI at `714f490e` passes all 110 checks in run `40240662670`; its tested
merge tree matches the candidate. Independent review:
`e2ed80ad8431c62a37f9dd0ea6d936e9dc0915de3e9031e369a961a67205127b`.

Source CI at `956a43ef` passes all 110 checks, independently authenticated in
run `40239701072` (review
`b765735022eff671e9f1172ac4776effdbdf2a096470e2d7d58db28c4c08323d`).
The previous `26ae342` source CI also passes all 110, review
`6098c0560b72d57c18a3a03d9d7475770d6eeab576d5a98b8b2a98c5844b30c2`.
Claude again owns the engine/Blender lane for further art production and
archive direction. Its CPU diagnosis finds v7's grey bands mostly follow the tabby-to-white
colour field, with a smaller coat-height contribution; the earlier shell-edge
interpretation below was an unconfirmed visual hypothesis.

The rebuilt `b9ef0365` v8 source has 31 independently verified source/ledger
files and four inspected Blender views. The actual SM6 capture has 22 verified
evidence files, 33 imported assets matching both freezes, unchanged rig assets
and no material-slot changes; all 22 asset differences are within the paw
namespace. Both original 1080p views were inspected. Contour bands are gone,
but the eye view remains glove-like and the close-up clumps look feathered or
scaled; cloth and cords still look synthetic. No photoreal acceptance. Capture
review: `c2633bee0e4a9a1b3975a25165047424553ea022afc688280c1a17410ba8dd06`.

The separate GPU measurement uses a 969×545 editor viewport and 120 numeric
samples per state. Translucency medians are 2.108/2.527 ms for eye/close-up,
versus 0.085/0.049 ms with the clear control. That control changes opacity,
lighting and shader together, so it does not isolate overdraw. Whole-frame
GPUTime differs by only 0.35/0.34 ms with overlapping spreads. Fifteen original
files and 882 median/quartile statistics independently verify; review
`338595e2fd281277f097cdc51e0443b3d2f704b2dfd1d3d07486c9b98b9d7861`.
The original JSON counts a repeated header as frame 121; valid samples are 120.
This is neither a 1080p timing nor platform/package performance acceptance.

## October 26 archive exit and shell-fur checkpoint

The archive now has a physical north doorway, ten 20 cm descending treads,
and a guarded connector to the press hall's four-metre catwalk. Pledge lines
alone do not advance the beat: the player must arrive on the press landing.
The transition preserves the moving capsule and then saves the press checkpoint.
The connector crosses the current gap between blockout zones; its architecture
and screens are provisional, and the south entry still uses the existing cut.

Exact `dc32d81` passes 13 of 15 selected NullRHI fixtures. ArchiveExit covers
mapped walking, a paused stair position, a real temporary obstruction, jump
attempts against both connector screens, and the actual saved arrival. Its
maximum per-frame movement is 13.289 cm. The two retained failures came from
fixtures expecting or placing the hero at ground level. After those fixture
corrections, exact `fa9f5a6` passes ArchiveExit, all-eight-chapter Spaces and the
assisted 133-beat Playthrough with no errors or warnings. Editor/wrapper exits
are naturally 0/0; twenty evidence files and unchanged inputs verify. Review:
`73e8cf05f9fe49f0d447d017f613f456467e02bf2ad0d441cbe4d2d8509619ab`.
The earlier failed-run review is
`4102c4fc3205a2e77af7aef02e497666a043a75e9c461951062e8509dedfc5e8`.

Source CI at `17fe866` retains 108 passes and two failures: the campaign's
updated timber-binding hash and a lift test's ground-floor assumption. Both
are corrected at `dc32d81` and pass locally. Its full source CI passes all 110,
independently authenticated in run `40238069513`, review
`fa4250f2fbc539bf799c08e024a449d8a68412a11f0c625b2239f5b651292989`.
The prior `a5388b5` source CI is independently authenticated at 110 passes.
These results do not establish ordinary encounter difficulty or release quality.

Claude's `4bcc819` v7 replaces the visible fur flakes with a continuous shell
coat. Both original SM6 images were reviewed: macro pile and silhouette improve,
but gameplay scale still reads as a white glove with broad grey layer contours.
The 25 archived evidence files verify, and all 32 manifest asset hashes match
the before/after freezes and current imported namespaces. Natural exits are
0/0 and the reticle disc remains clear. Review:
`248f412b9b93194bda76a4c447084ed0687fd2b4d491e955c5b329dc001b699b`.
The 1,781-instruction translucent shell material still needs measured cost.
The comparator's explicitly permitted cards-to-shells slot change passes 28
host tests at `3edabfb`; this is measurement tooling, not art acceptance.
Claude has the engine/Blender lane for the next bounded iteration. The authored
archive cinematic, ordinary duel play, final art, platform and performance
qualification remain unfinished.

## October 26 relay aftermath, archive collision and fur review

The archive family-page light and reveal/save ordering pass six NullRHI
fixtures at signed `6eb0df6`, including ArchiveFamilyPage, ArchivePosts,
Spaces, ToranosukeSteel, CombatAndPlaque and the assisted 133-beat campaign.
The two reveal cases cover an empty dialogue queue and a preceding combat
bark. The actual save remains in phase one until the final family line ends,
then restores phase two and the lit slate in a fresh world. Editor/wrapper
exit naturally at zero; twenty evidence files and unchanged inputs verify.
Review: `5b64a75daf3a80b63aa88cc75f2d192791dabac77b82b57cb1b4cde4359a320d`.
The prior `f3de9c2` build failed before tests because a copying test helper
lacked its direct catalog include; its failed log is retained. Source CI at
`f3de9c2` passes all 110 checks, independently authenticated in run
`40235477188`. This remains directed gameplay validation, not the unfinished
twenty-second cinematic, north stair, ordinary duel play or final art.

Claude's later `c928d90` v6 capture also exits naturally on METAL_SM6.
Thirty archived files, 33 protected inputs and reticle clearance verify.
Sleeve folds are more visible; the paw still has bright angular flakes and
weak coherent volume. Shared-region residual rises 18.9005% in the eye view
and 9.8516% in the close-up against v5 with identical recorded setup/poses.
Review: `69d00d5523ce513adb51e733ad3d27adda183d5753a312f666d0fc1c0dd8f690`.
Neither the number nor this single changed-asset capture is art acceptance.
The comparator's four missing-metadata cases now reject at `a036f59`, with
24 host tests and the unchanged positive control passing independently.
Material paths alone still cannot establish identical asset bytes. Claude
owns the engine/Blender lane for content binding and a different fur approach;
root continues source work on archive traversal.

The complete release remains unfinished. Exact `4ba5ab7` passes fifteen
NullRHI fixtures, including the assisted 133-beat campaign, online drone
radio marks, actual completed-relay save reload, later flood lighting, five
flood fixtures, searchlights, relay controls/scan/notices and acoustic/stealth
regressions. Online marks reach an ally outside twenty metres even with
hearing disabled; offline marks reach the twenty-metre boundary but not
20.0025 metres. The flood escape now contains the two original moat towers
as well as its three handlamps. Its saved relay flag freezes the towers'
horizontal headings and blocks later searchlight retargeting, while the
handlamps still detect. All fifteen pass with natural editor/wrapper exits
zero, unchanged inputs, and twenty independently rehashed evidence files.
Review: `41acc2a73eb7931a6e54477776adb1029739e8c578bed19f7542d570a96f719c`.
Source CI `40232668064` independently passes all 109 checks at that source.
The prior real stair, inspector and 50/40/30-second patrol results remain in
the [relay record](qualification/relay-room.md).

The archive is now a 26 by 18 metre collision blockout with a six-metre
ceiling, four solid posts in its duel ring, wall racks and relocated duel
anchors. Its first engine run retained two fixture failures: selecting the
needle gun instead of the katana, and expecting the relay's removed generic
pedestal. The assisted campaign passed on that exact `1248987` production
source, whose separate source CI passes 110 checks. After fixture corrections,
`e638cd6` passes ArchivePosts, all-eight-chapter Spaces and ToranosukeSteel.
Mapped katana input commits a swing blocked by a real post and a clear-line
swing that damages the target beside it. The boss regression includes the
sheathed mutō-dori finish. Natural exits are zero; all twenty evidence files
and unchanged inputs verify. Review:
`7469d1d4798f839b47cc4f527f6eb4683837f020e0417b79c9b1901bfbe4caa8`.
The [archive record](qualification/archive-room.md) retains failures and
limits. The north stair connection, ordinary duel play and final art remain
unfinished.

Claude's `d6021af` v5 fur capture exits naturally on METAL_SM6. Root verifies
thirty archived files, all nine material slots, 33 unchanged protected inputs
and the three ID classes' zero pixels in the fixed reticle disc. On shared
fur regions, v5 residual is 39.7% lower in the eye view and 46.8% lower in the
close-up than v4. Camera/exposure agree; tiny solved-pose differences and two
study-text edits are retained. This is a descriptive comparison of single
captures and changed assets, not causal or photoreal acceptance. Original
images still show broad angular strips, pale gaps and flat bright white fur;
cloth and craft finish remain WIP. Review:
`659ade7b10c90336291b219cd9f7c96c384c4ba1e5ead1597ca23e330e064a1e`.
Claude has the Unreal/Blender lane for the next bounded fur/kote iteration.

The latest completed Mac package remains `c655b6b` and the production native
bridge remains `10ad7dad`. Current-source packages, M1 and Windows behavior,
ordinary-input gameplay, performance and full native/network settlement
acceptance remain open.

## October 25 completed bounded proof and desk regression

Signed native `cd9263628d` completes its retained-binary final-tick-death proof
cohort: one 3,666,144-byte proof verifies separately; all 90 public-input,
two corrupt/truncated and eleven actual-prover cases reject as required.
Both phases exit zero with natural stream EOF, no guard breaches and unchanged
source. All 116 archived files independently verify. This remains an
unregistered two-player/two-tick relation; full World/Core execution,
network settlement and performance are open. The production bridge stays
`10ad7dad`. See the [native proof record](qualification/native-final-death.md).

Exact game `56bdcfe` builds in 20.56 seconds and passes CopyDesks, Candle and
the assisted 133-beat Playthrough, including the new visibility obstruction
case. All three selected reports have zero errors/warnings, natural
editor/wrapper exits zero, unchanged inputs and 20 authenticated files.
The pre-initialization diagnostic lines are preserved separately in the
[desk record](qualification/copy-desks.md). These results precede the press
candidate. Signed `2b911ea` now passes all 108 source CI checks; its ten Unreal
fixtures remain pending, as described in the [press record](qualification/press-hall.md).

Claude has the engine/Blender slot for its accepted timber, bow and paw rebuild
sequence. Its scoped bow-ledger correction passes eighteen independently
reproduced host tests and three retained regression probes; all sixteen raw
inputs verify. Its wrapper now restricts the exit-one exception to the full
editor, with eleven independently reproduced fake-engine fixtures. These host
results do not admit generated geometry, materials or final art. The release
remains incomplete.

## October 25 press-hall source candidate

A separate source candidate adds the eight authored press positions, separate
master jams, stamp-clock masking at player-noise emission, interval integration
for footsteps, and living auditors' actual inspection movement with a visible
missed-deadline state. Remote CI passes at `43e8d89`, including the C++ press
rules and unchanged climb/flood layout baselines. A subsequent source addition
gives the three hanging die lamps arrow-only impacts and a five-second delay
before the nearest guard becomes suspicious. The source now adds the four-metre
catwalk, an elevated enforcer route and a swept, interruptible ladder from its
north-west entry. Exit credit requires all three jams and the actual lift
floor, and floor dialogue volumes exclude the catwalk. The auditors and drone
now have scheduled 45/30-second circuits that require actual arrival and retain
missed deadlines. Ten host contract tests and four unchanged moat/layout
checks pass. Ten Unreal fixtures are prepared; their compilation and
execution remain pending. The [press-hall record](qualification/press-hall.md)
separates this blockout from unfinished runtime validation, the archive stair
connection, actual patrol cadence, sound, art and ordinary encounter checks.

## October 25 separate desk copies and actual crate CPU evidence

The chapter-six copying candidate preserves the three authored desk names
and 30 seconds of work per desk. Each desk requires a mapped held Interact;
time cannot spill into another copy. Releasing or leaving frees the hands and
preserves partial work, guards pause the active copy, cupping the candle halves
its rate, and checkpoint retry resets all copies. The objective selects the
nearest unfinished desk, and each proxy ledger indicates its own progress.
Host progression passes all 133 tasks and both eight-chapter routes; content
validation rejects 65 malformed variants. Exact `4fa637f` builds in 21.87
seconds and passes CopyDesks, Candle and the full assisted campaign together,
with zero selected errors/warnings and natural editor/wrapper EOF zero. All
20 archived files rehash; source/native/Config/Generated remain unchanged.
The three earlier fixture failures are retained and explained in the
[desk qualification record](qualification/copy-desks.md). Proxy desks do not
establish the authored hall's real layout, ordinary stealth difficulty or final
visuals. CI `025cb32` separately fails a stale chapter-six timber-binding hash;
that hash alone is refreshed with passing binder tests. CI `40205927830` at exact `4fa637f` now independently passes all 107 gates
in five jobs, including 279 Rust tests and five ignores. All five artifact
digests, raw logs and matching tested/source trees are verified; the ledger has
zero errors or warnings. Ten raw warning lines repeat one Node20 deprecation.
The review digest is `64801dd64a8f2ce4928b19093f72f465958381e4186193407c09545cf6e1aa7e`.
A later source correction checks actual visibility to the ledger before and
during copying; its obstruction fixture is added but has not run in Unreal.

Fresh signed native `cd9263628d` completes its actual privacy-crate build and
CPU tests: 45 relation tests pass with four ignored proofs, and the packed
adapter test passes all 254 canonical layouts. Maximum encoded witness size
is 3,803,712 bytes, below 4 MiB. All five phases reach natural EOF with exit
zero and no guard breaches; the compiler retains one unused-field warning.
The independently reviewed retained binary has SHA-256
`b75f671cff284d16ff098f38d838fd1f42b2178d6d3de5d4081acafb273c2624`;
the independent CPU review is
`c3df357cc5631130a4712bb639708f41f3b4cae071fc12cd75460ff8e2c8dd4a`.
The separate final-tick-death proof cohort has launched from this retained
binary with sealed CPU prerequisites and unchanged resource guards. No proof
result is claimed yet. These are functional CPU results under recorded background
load, not performance, full World/Core execution, settlement or a new bridge.

CI run `40201884816` at `d3f19bf` independently passes all 107 gates in five
jobs, including 279 Rust tests with five ignores. Tested merge/source trees
match; five artifact digests and raw logs are verified. The unchanged Fern02
source buffer is now stored through LFS, giving zero ledger errors or warnings.
Ten raw warning lines repeat one Node20 workflow deprecation. The independent
review digest is `126467bc02d37328f880797ba2525e7b7020a61e3feca6bf8d574dec33bc9d69`.
This CI does not qualify the later copying candidate.

Claude has corrected the bow evidence's scope: eight canonical raw samples
fail the original rotation bound; the separate reference-snap model passes.
The previously cited engine branch is inapplicable, the actual snap cause is
unlocated, and all four codec settings are inferred from static defaults.
The four revised paw originals improve digit readability, but macro fur card
edges, glossy cloth/arrow and stepped bow wrapping remain open. Lit first-person
Unreal v2 evidence now comprises four independently reviewed originals from
a failed run: image output finishes, then static Slate/text teardown crashes,
and the stuck crash handler requires recorded SIGTERM/SIGKILL of its own editor.
Exposure and attachment are inspectable, but coarse white fur cards, the grey
bow and glossy arrow remain rejected. No signed art integration, final art,
new package or release acceptance follows from these results.

## October 25 withdrawal detail and fresh native CPU evidence

Exact `5d02f3b` builds in 30.49 seconds and passes the prepared live withdrawal
capture on M2 Ultra, Metal SM6, 1280×720 in 162.00 seconds. All four originals
were reviewed: movement, bilingual dialogue, the corrected defended tracker
and six individually distinguishable survivors in the arrival detail pass
this targeted review. Only the additional detail hides the HUD. All four
requests match their processed frames; the real defense timer, full gate-clear
call and cleanup pass with zero selected errors/warnings and editor/wrapper
EOF zero. All 34 archive files and five original/archive pairs rehash; source,
native, Config and Generated stay unchanged. The preceding `2f85881` failure
is preserved: its detail failed frame identity and its overhead view hit the
gate lintel. The correction uses the viewport draw callback and an oblique
camera. These prepared stills do not accept ordinary combat, final art or
animation. See the [capture record](qualification/horse-withdrawal-capture.md).

CI `40177204154` independently passes all 107 source gates in five jobs at
exact `5d02f3b`, including 279 Rust passes and five explicit ignores. The tested
merge tree equals source; all artifact digests and raw logs are verified.
The existing Fern02 ledger warning and five workflow warning lines remain.

Fresh signed native source `cd9263628d` now passes 18 provenance tests and all
70 standalone constraint tests. A separate canonical observer regenerates four
final-death fixture files byte-identically, covering 133 supported cases and
seven domain refusals. The initial dependency-selection failure and subsequent
observer library-search-path failure are preserved. The corrected observer
uses the identical SHA-2 library from its dependency directory; native source,
lockfile and fixture expectations are unchanged. All 62 retained files and
the dependency closure were rehashed. This is standalone CPU evidence; the
actual crate's CPU build/tests are now running with one Cargo job, recorded
background load and RAM/disk guards. No ignored native proof has run.

Claude delivered signed `bfaded4`, whose isolated bow import now succeeds at
unit bone scale. Review remains open: canonical-rig error exceeds the original
raw rotation bound, while a reference-pose-snap model fits the observations.
The engine branch's applicability is not yet established. Codec runtime
properties are unreadable; package/class defaults are static evidence only.
Claude owns the engine/Blender slot for lit bow/paws and the focused timber
study. The latest package and production native bridge remain `c655b6b` and
`10ad7dad`; complete game and release acceptance remain unfinished.

## October 25 visible withdrawal source candidate

Chapter-two defense source now stages surviving registered enemies retreating
through the real courtyard toward `ps_gate_yard_start`. That point is inside
the existing collision wall; no exterior-gate passage is claimed. At the
existing 150-second task boundary, pending pod members and horse shells retire
and survivors receive normal navigation errands at 75% movement input.
Completion waits for grounded feet within 220 cm of the approach and the
authored retreat bark, then plays Kohagi's full back-gate-clear line before
starting the following cinematic. No timeout,
partial-path stop, teleport or manufactured kill credit can finish it. Six
separate stations inside that approach prevent a shared stopping circle from
forming a queue; each has 30 cm navigation acceptance. With
no survivors, only Kohagi's call plays before the transition. Menus hold movement;
ordinary damage/retry and held horse treatment remain available.

The current-only authoring/normalizer/runtime contract and generated chapter
are updated, including the chapter-bound timber manifest. Ten selected host
groups pass on the initial candidate, with a later cleanup ordering review
detaching old pod/shot state before destruction callbacks and preserving held
treatment during the outro. Six affected groups pass after those changes.
At exact `ac54ab8`, the editor builds in 48.76 seconds. Ten of twelve directed
tests pass, with two selected errors and zero warnings. Actual obstruction,
movement, pause and arrival pass. The following cinematic masks Kohagi's
completion line, and the retry fixture mistakes a dead noncolliding body
within its normal two-second lifetime for a surviving enemy. Both failures
remain preserved, with natural editor/wrapper exits 3/1 and unchanged inputs.
The correction holds the cinematic until the full gate-clear call finishes,
including when no enemies survive, and verifies both immediate body
deactivation and eventual removal. Exact `0adc081` builds in 44.77 seconds and
passes all thirteen directed tests: three withdrawal cases, three horse-shell
cases, three pod cases, two treatment cases, the assisted 133-beat Playthrough
and shared arming. There are zero selected errors and one external HTTP
connectivity-check timeout warning in HorseWithdrawalCleared. Actual editor
and wrapper exits are zero with stream EOF. All twenty archived files rehash;
source, native inputs, Config and Generated stay unchanged. These NullRHI
results establish the tested mechanics and subtitle state, not rendered
readability or ordinary unassisted defense pacing.
CI `40170994760` at exact `0adc081` passes all 106 source gates in five jobs,
including 279 Rust tests and five explicit ignores. The tested merge and
source trees match; all five artifact digests and raw job logs are verified.
The existing Fern02 plain-Git-blob ledger warning and ten Node20 workflow
warning lines remain recorded.

The subsequent prepared withdrawal capture at exact `c63af6f` builds in
21.60 seconds and passes its 158.90-second Metal SM6 1280×720 test, with zero
selected errors/warnings and natural editor/wrapper exit zero. Its actual
150-second defense, six living arrivals, complete gate-clear call and cleanup
pass; all 32 archive files rehash and source/native/Config/Generated are
unchanged. All three originals were reviewed: movement and bilingual dialogue
are readable, but the arrival group overlaps the torii posts and itself.
The stale zero-second countdown receives a subsequent source-only correction
to “Pack horses defended.” Better arrival framing and final visuals remain
open. The [capture record](qualification/horse-withdrawal-capture.md) states
the assisted setup and recorded background CPU load; this is not performance
or ordinary combat acceptance. Exact `c63af6f` CI `40172328160` independently
passes all 107 source gates in five jobs, with 279 Rust passes and five ignores.

The engine lane returned to Claude after the capture's natural EOF. All 15
timber originals still fail photoreal review. Signed bow rig `6f3875b` fixes
the gross tip web and detached serving in all 30 independently reviewed gray
geometry images; its signed 32-test host suite passes independently. Unreal
import attempts 0–6 fail and are retained. Root traced the remaining root-bone
scale issue through the installed engine source and actual FBX properties;
Claude is correcting the export units before new Blender/Unreal playback
verification. Final materials, arrow attachment, paws and runtime integration
remain open. The fresh native minimal-CPU plan passes read-only preflight but
has not executed. No new package or release acceptance is claimed.

## October 25 pod arrivals and horse-defense shells

The authored chapter-two pods now warn for 2.5 active seconds, apply one
physical impact, and admit their registered enemies under the six-enemy cap.
The pod-B grenadier uses real targeting, movement, windup and swept shared
projectiles. It targets living horses, can be baited by a nearer visible hero,
locks its landing point, and preserves cover, arming and faction rules after
the shooter dies. Its minimum warning is 1.4 active seconds before release,
followed by the catalog's 1.4-second flight; it is not an exact 1.4-second
warning-to-impact claim. Failure/retry/leave cancels the encounter session.
The [shell contract](qualification/horse-defense-shells.md) records details.

Exact `bf58810` builds in 39.28 seconds. Fifteen of sixteen selected uncooked
NullRHI tests pass, including all three pod cases, horse-shell cadence/bait,
held horse treatment, canister shots and blast, MarginLinger, Foundry, wind,
shared arming and the full assisted 133-beat Playthrough. The one failing
HorseShellCoverAndDud case produces two selected errors and no warnings.
Its first armed-cover assertions pass; its second fixed wall does not ensure
an early collision after the shooter moves. This cause was inferred from
source; the original run did not record those positions. Actual editor and
wrapper exits are 3 and 1, and that failure remains preserved.

Fixture-only `2a69fb5` puts the wall ahead of the actual shooter and verifies
the physical pre-arming sweep. The build passes in 46.76 seconds; that case
and ExplosiveSelfDamageAndArming both pass with zero selected errors/warnings
and actual editor/wrapper exit zero. The first contact is measured at
95.810 cm; observed projectile travel is 26.414 cm. Production behavior is
unchanged. The previous fifteen cases were not rerun at this revision.
The initial `03e8bf4` build failure on four declaration/helper errors is also
preserved. Both final-run archives have all twenty files independently
rehashed and unchanged source/native/Config/Generated guards.

Authenticated CI `40167446121` passes 105 gates in five jobs at `bf58810`: 53
gameplay, 26 tooling, 17 assets, five audio and four Rust gates. The tested
merge tree equals the source tree; all five artifact digests, archive files
and raw job logs are verified. Rust reports 279 passes and five explicit
ignores. The existing Fern02 plain-Git-blob ledger warning and workflow
Node20 migration warnings are retained. Later source does not inherit this CI.

Evidence under `Saved/Qualification/2026-10-25/`: `horse-shell-source-host`,
`horse-shell-03e8bf4-runtime-attempt1`, `horse-shell-bf58810-runtime-attempt1`,
`horse-dud-2a69fb5-runtime-attempt1`, their adjacent root-review receipts, and
`ci-bf58810/independent-review.json`. These tests stage encounters and assist
the campaign; they do not establish ordinary controls, pacing or a full
unassisted 150-second defense. The visible withdrawal remains unfinished.

The engine/Blender lane returned to Claude after natural EOF. The signed
`d58edaf` clipping correction passes independent reproductions and seven
directed cases, but the new rig schema, exported playback, isolated import,
first-person paws and v2.2 timber still await delivery/review. The prior 54
SM6/SM5 timber frames remain accepted only for baseline capture readiness;
the v2.1 art remains visually rejected. Photoshop, Illustrator and Topaz
Gigapixel Wonder 3.5 High are available with preserved sources/provenance.
Latest package remains `c655b6b`; the production native bridge is `10ad7dad`.
Fresh native qualification from surviving signed source has not run. Final
art, ordinary play, current packages, other platforms and release acceptance
remain open.

## October 25 horse treatment and canister runtime

Exact `6750fa6` builds successfully in 27.92 seconds and runs all fourteen
selected campaign tests to natural editor exit 3. Eleven pass; three fail,
with five selected errors and zero warnings. Both horse-treatment tests pass,
including held input, interruption, per-horse cooldowns and checkpoint retry.
Canister blast damage, physical cover/radius exclusion and registered enemy
credit pass, along with Foundry repair/deadline, hangar falls/spawn clearance,
wind projectiles, both casting-channel tests and MarginCover.

HangarCanisterShots fails during mapped walking. Its first waypoint is inside
the gallery staircase; `9b54b44` routes around the foot and records actual
positions. MarginLinger's new diagnostics show a real crouched blocker, console
6, in front of the expected console 2. `af23810` approaches console 6 directly,
retaining physical trace, damage, six-second pin and destruction assertions.
Playthrough still assumes instant quarter-HP repairs at the generic anchor.
`5550ddb` replaces that expectation with mapped two-second treatment beside
the real horse, a cooldown rejection, and a fresh sixty-HP treatment. Seeded
injuries, assisted enemy defeats and checkpoint failure remain explicit. All
three corrections need an engine rerun; none is reported as passed.

The initial `cdb425c` attempt failed before editor launch with two C++ errors:
a local name shadowed the director's Horse field, and UE 5.8's TObjectPtr pawn
return made a conditional expression ambiguous. `6750fa6` fixes these and a
deprecated diagnostic call without changing gameplay. Independent source
review agrees. Both failed-run archives remain intact. The root rehashed all
twenty terminal-run files; source, native inputs, Config and Generated remained
unchanged. Evidence: `horse-canister-cdb425c-runtime-attempt1`,
`horse-canister-6750fa6-runtime-attempt1`,
`horse-canister-6750fa6-root-review.json` and
`compile-correction-6750fa6-independent` under the October 25 qualification
folder. These are directed uncooked results, not ordinary full-game acceptance.

Separate independent review authenticated the earlier ten-pass/one-fail run
and all 36 SM6 plus 18 SM5 timber frames at `0c7961d`, rehashed the archives and
viewed twelve originals. The capture readiness defect is closed for that
source and saved asset set; timber remains visually unfinished. The optional
editor dylib copy was unavailable during later rebuilding, so its archived
exact-source receipt is retained without claiming preserved binary bytes.

Claude now owns the engine/Blender slot for revised timber, skeletal yumi and
hands. The first three reproduced yumi checker omissions are corrected in
`ec5df08`; a separate degenerate-triangle distance error remains reported. New
rig interpolation/socket/provenance source is still under review. Pod-arrival
source and the horse-targeted grenadier remain in progress. Latest completed
package is still `c655b6b`, production native bridge `10ad7dad`, and latest
fully authenticated CI is still `dfbf1b9`. The release remains incomplete.

## October 25 shader readiness and encounter mechanics

At exact `0c7961d`, the editor builds successfully and ten of eleven directed
encounter tests pass. Casting-channel traversal and enemy credit, zero-life
seizure nets, moving deck, the corrected BridgeProps warning boundary,
destructible Margin Call cover, Collatera, both helm tests and Playthrough pass.
MarginLinger fails its combined crouch/physical pistol-block assertion. The
original editor exit 3 and failure are preserved. `4a38d90` moves only that
fixture's approach to the console's middle and adds exact stance/trace data;
its rerun remains pending. Production collision and the blocking requirement
are unchanged. The inferred edge-tolerance cause is not yet proven.

The same source passes all 36 SM6 and 18 SM5 timber captures on Apple M2 Ultra,
with actual editor and wrapper exit zero, no selected errors or warnings, and
unchanged source, Config and Generated bytes. Schema 3 waits for two ready
proxy observations on distinct frames and records observations before the
screenshot request and after the saved screenshot. The first dense and first
conventional views each reject four initial fallback observations in SM6 and
two in SM5. Every admitted view resolves its proper master at both endpoints.
Five SM6 and four SM5 original images were individually reviewed; the previous
SM5 first-view fallback bands are absent, and the SM6 column's mask/triangle
views visibly show Nanite diagnostics. These CPU observations are not GPU
shader identities or draw counts. The unchanged saved assets still originate
at `97c08a0`; this is neither a new import nor photoreal art acceptance. SM5 on
M2 Ultra does not qualify M1 hardware, Windows or packaged performance.

Horse treatment source `75ddda8` requires a two-second held interaction at an
injured horse, heals sixty HP capped at four hundred, and uses independent
twenty-second cooldowns. Its seven integration host-check groups pass at
`202e23c`, including the current campaign binding. Engine tests remain pending.
The chapter-two pod-arrival and horse-targeted grenadier mechanics are still
missing; generic proximity siege damage is provisional.

Authenticated CI `40161978056` passes all 100 source gates in five jobs at
`dfbf1b9`, including 279 Rust tests and five explicit ignores. Later commits do
not inherit that result. Claude's immutable v2.1 pilot contains six members and
fifteen originals; all were viewed and all 46 archived files rehashed. Its crack
geometry improves, but smooth grain bands, blister-like dents, glossy ridges
and repeated rounded adze marks still fail photoreal review. The skeletal yumi
and its checker are separate unintegrated candidates; reproduced clipping
omissions prevent accepting the checker's clearance claims.

Evidence is under `Saved/Qualification/2026-10-25/` in
`casting-margin-0c7961d-runtime-attempt1`,
`timber-ready-metal-sm6-0c7961d-attempt1`,
`timber-ready-metal-sm5-0c7961d-attempt1`, `horse-margin-integrated-host`,
`ci-dfbf1b9` and `timber-v21-root-review`. The original failed runs remain
preserved. The production native bridge and latest package remain `10ad7dad`
and `c655b6b`; the complete release remains unfinished.

## October 25 verified campaign and pending encounter changes

Exact `97c08a0` passes all 15 combined campaign/presentation tests and six
additional defense regressions, with zero selected errors or warnings and
actual editor EOF. This includes all twenty cache cases, nine Collector
sheathing/input cases and the directed 133-beat playthrough. Authenticated CI
`40158853811` passes all 98 source gates in five jobs, including 279 Rust tests
and five explicit ignores. The tests remain assisted uncooked evidence.

Both SM6 BowAim captures pass at 1280×720 and 1920×1080. All eight untouched
originals were individually reviewed: the target stays clear and the temporary
grip/stave remain left of the reticle, without visible near-plane clipping.
The cube paw, proxy bow, broad bilingual panels and world still fail finished
art quality. This closes the specific framing defect, not overall visual
acceptance, authored bow admission or normal campaign play.

The corrected nine-mesh timber import and fresh-process reopen pass at the
same source: all 31 packages are saved and unchanged on readback, and all
1,151 production Generated files retain their hashes. The old 31 packages are
preserved in both the immutable archive and a retained namespace outside
Content. The subsequent SM6 draw fails before its first screenshot: the capture
mistakes an unregistered test console variable for an active override. Its
original observation report records Disabled dynamic resolution and restores
the original 75 percent control. Schema 2 now represents registration explicitly
and checks the actual view's primary override as well as its static fractions.
All 24 host tests pass; a corrected Metal draw is still required. SM5 was not
run against the same faulty precondition. The saved material origin remains
`97c08a0`; a newer capture source must not be described as a reimport.

At `0994b44`, all eight directed encounter tests pass with zero selected errors
or warnings and actual editor EOF: BridgeDeck, BridgeProps, CollectorCaneThrust,
CollectorSheathing, Collatera, HelmHandsAndFloor, HelmTrim and Playthrough.
The real ten-degree moving deck, directional pace, swept props and nine cane
cases are now exercised in Unreal. Source, native inputs, Config and Generated
remain unchanged. BridgeProps' initial single-tick wait is clamped by Unreal,
so its pre-warning assertion is weaker than its label; a correction will check
the actual deadline. The later contacts and assertions passed. These assisted
NullRHI tests do not establish ordinary encounter difficulty or final art.

The same capture source produces all 36 SM6 and 18 SM5 timber images at full
resolution, using the saved `97c08a0` assets. Both editors exit zero, but both
wrappers correctly reject two first-use material readbacks. The other 34 SM6
and 16 SM5 observations resolve the proper masters. Eight selected originals
were individually viewed: the two flagged SM6 views visibly show wood, while
SM5's first dense-asset view has pale fallback bands. The pre-request material
observation can precede the actual screenshot draw; readiness and capture-time
checks need correction. The SM6 column mask and triangle views visibly show
active Nanite diagnostics. Neither run establishes material or art acceptance.
Both retain one repeated absent-CVar lookup warning. All packages remain
unchanged. The earlier zero-frame and compile failures are preserved.

New source `042fa45` implements the casting floor's four timed channels,
grounded contact, residual player burn and ordinary enemy defeat credit.
`e15c71a` makes zero-life boss hazards release once when a frame crosses their
deadline; `aaeeaef` corrects its fixture to observe game and real clocks in
bounded steps. Seven focused host checks pass at `e15c71a`, including generated
campaign data and the binding with both chapter-five and chapter-seven hashes.
The casting and zero-life changes still require an Unreal build and runtime
tests. `d0a4856` separately corrects the BridgeProps warning-clock fixture; its
new boundary assertions also remain unrun. The bridge's authored amphitheatre, final prop art, scrape audio and
margin-call cover behavior remain open.

Authenticated CI `40160784400` passes all 99 source gates in five jobs at
`9cf8be1`, including 279 Rust tests and five explicit ignores. Its tested merge
tree equals the source tree. All five API artifact digests and original job logs
are verified. Newer source does not inherit this CI result.

Evidence is under `Saved/Qualification/2026-10-25/`: `combined-97c08a0-runtime-attempt1`,
`defense-97c08a0-runtime-attempt1`, `ci-97c08a0`, `bow-sm6-97c08a0`,
`timber-corrected-import-attempt1`, `timber-corrected-reopen-attempt1`,
`timber-corrected-metal-sm6-attempt1` and
`timber-corrected-sm6-resolution-failure-review`, `encounters-0994b44-runtime-attempt1`,
`timber-corrected-metal-sm6-0994b44-attempt1`,
`timber-corrected-metal-sm5-0994b44-attempt1`, `timber-corrected-099-root-review`
and `casting-hazard-e15c71a-host`. Claude now owns the engine/generation lane
for the corrected timber pilot and authored bow/hand assets. The native bridge and latest
package remain `10ad7dad` and `c655b6b`. The full release remains incomplete.

## October 25 campaign, first-person and Metal corrections

At exact `e237b9f`, eight selected editor tests pass, including twenty
cache/inventory cases and three presentation tests, with zero selected errors
and one HTTP warning. The corrected log collector confirms actual editor EOF.
Fresh 720p BowAim captures pass functional checks, but all four originals fail
visual review: the temporary grip and paw obstruct the target. `c25d384` gives
that unchanged proxy its own fixed poses and measures its actual component
bounds. New engine and image results are still required.

The nine-asset timber probe produces 36 SM6 and 18 SM5 originals at `e237b9f`,
but both runs fail admission. Both masters fail Metal compilation and resolve
to WorldGridMaterial. All 54 paired views retain the neutral post process and
excluded production lighting, but use 75 percent internal resolution.
`376e4ad` corrects sampler types, explicit alpha outputs and the parent mask
default; `8ede60c` establishes and records full static resolution. Neither fix
has a new Unreal draw result yet. Diagnostic Nanite triangles do not qualify
the failed materials. All 31 original packages are preserved in a verified
read-only archive; all 1,151 production Generated files remain unchanged.

Chapter-six source `f6b7a5f` builds in 76.68 seconds. Six of eight selected
tests pass: BulkheadCapture, CacheArrows, EquipmentRecovery, GalleryCache,
SpineDrawCut and SpireSupply. InfiltrationLoadout tries to collect during the
existing 0.25-second equip cooldown; Playthrough expects a rifle to equip
despite the mission's carrying restriction. The original six assertion failures
and one HTTP warning are retained. `d338b0e` corrects those fixture assumptions
and preserves explicit busy/forbidden-input rejection. Its engine rerun is
pending. `160897c` separately fixes a real offline combat defect: unfinished
sheathing could receive a drawn-blade guard/parry. Completed sheathing remains
required for mutō-dori. The new mapped keyboard/remap/gamepad Collector test
and the three bilingual HUD states await engine qualification.

Authenticated CI `40156704117` passes 94 of 95 gates at `e237b9f`; its UV test
fails to import before its body runs. The corrected exact invocation passes
locally. At `376e4ad`, 42 of 43 tooling/asset gates pass; only the campaign
binding is stale after chapter-six data changed. Regenerating it changes only
that chapter hash, and its check passes. No acceptance thresholds are relaxed.
Evidence is under `Saved/Qualification/2026-10-25/` in `viewmodel-cache-e237b9f/`,
`timber-baseline-metal-sm6-attempt1/`, `timber-baseline-metal-sm5-attempt1/`,
`timber-baseline-31-readonly-archive/`, `ch06-f6b7a5f-runtime-attempt1/`,
`source-checks-376e4ad-tooling-assets/` and `ci-e237b9f/`.

Native evidence availability was rechecked: both old Iroha target folders are
absent. Of 286 historical referenced file paths, 43 still exist and match their
hashes; 243 are missing. Signed source survives, but the original final-death
runner/log/archive was not found within the searched worktrees, development
folders and temporary folders. No removal cause is inferred. Fresh exact-source
qualification is being prepared. Production bridge `10ad7dad` and latest Mac
package `c655b6b` remain unchanged. Ordinary play, photoreal art, platform and
performance testing, full native execution and settlement remain unfinished.

## October 25 saved timber probe and measured exposure

At exact signed `57ce095`, the bounded timber import passes for nine meshes:
five with built Nanite resource inputs (1,245,236 source triangles) and four
conventional pool meshes (124,868 LOD0 triangles). A fresh Unreal process
reopens all nine meshes, nine material instances, two masters and eleven
textures with no reported differences. All 31 probe packages and all 1,151
production Generated files remain unchanged during readback. Both processes
reach natural EOF without a resource breach. This is saved-asset acceptance,
not actual Nanite draw or visual acceptance. The four earlier failed import
attempts and the 19 startup `Condition failed` diagnostics are retained.
Evidence: `timber-baseline-probe-attempt5/` and
`timber-baseline-reopen-attempt1/` under `Saved/Qualification/2026-10-25/`.

At the same source, ordinary six-view 1280×720 ArtReview captures pass separately
on M2 Ultra Metal SM6 and SM5, with zero selected errors/warnings. All twelve
originals were inspected; each has a valid frame-matched GPU exposure record.
At every screenshot, metered average luminance (0.00787–0.02113) exceeds the
legacy minimum average (0.0054), and target exposure matches the unclamped
formula. Lowering that minimum is not supported as a fix for these views.
All screenshot current/target gaps are below 0.05 stops, but Kamiza fails the
preceding-30-frame criterion and SM5 Ceiling has only 26 observations. Full
exposure/GI/streaming convergence is not established. Production lighting and
generated assets are unchanged. The records are in
`eye-adaptation-sm6-baseline-attempt1/`, `eye-adaptation-sm5-baseline-attempt1/`
and `eye-adaptation-diagnostic/baseline-57ce095-exposure-review.json`.

Visual acceptance still fails: orange surfaces, bright panes/lamp glare, dark
characters, repeated ceiling marks, old boxes and red cylinders remain. The
SM5 West_Back median is 0.60 display stops below SM6 and its right-wall window
appearance differs; other paired medians differ by at most 0.12 stops. These
captures use the existing generated kit, not the isolated timber probe, and
do not qualify M1. Claude's six-member v2 Blender pilot also remains visually
rejected after review of all fifteen originals: stepped cracks, knot kinks,
glossy bands and rounded adze dimples require correction. Its first output is
preserved under `timber-v2-pilot-original-review/`; no bulk v2 import is admitted.

All 38 local asset/tooling gates pass at `57ce095`. Authenticated CI
`40155065706` passes all 90 source gates in five jobs at that exact source,
including 279 Rust tests and five explicit ignores; the tested merge tree
matches the source tree. Newer UV correction `cd10643` restores metric/log UV
data and image sampling after Interchange's V flip, preserving baked UV1 and
the frozen ring model. Its new source gate and 47 focused tests pass; current
saved probe assets have not been regenerated with that correction. Exact CI
artifacts are under `ci-57ce095/`. The latest package remains `c655b6b` and the
production native bridge `10ad7dad`; all other release requirements stay open.

## October 25 HUD corrections and resumed art work

At exact `e37e5ae`, both SM6 1280×720 and 1920×1080 combined captures pass all
twelve selected tests: Cargo.Transfer, four WeaponHUDFixture tests and
Campaign.Chapter2–8. Each run has zero selected errors and warnings, reaches
natural EOF without a resource breach, and archives 34 original images. Every
original was independently inspected. Tarifa's complete readout clears the
reticle, BowDraw has no Canvas warnings, the three stealth/tracker collisions
remain corrected, and the cargo counter, full holds, full cinematic and final
zero/idle-boss layout pass. Builds take 83.79 seconds at 720p and 4.29 seconds
at 1080p. Both runs retain 19 startup `Condition failed` diagnostics and 23
startup warnings, separate from the selected tests.

The corrections are `df3d5d5` (compact row whitespace without shrinking fonts
or removing text/meters) and `2ea1d4a` (fixture geometry checked during the actual
HUD draw). The first `66a23f4` build attempt failed on an incomplete `ASoraEnemy`
definition; `e37e5ae` includes its header directly. That failure and the earlier
`c139192` Tarifa failure/eight BowDraw warnings are preserved. Evidence is under
`Saved/Qualification/2026-10-25/hud-spacing-and-frame-e37e5ae/`, with independent
reviews `hud-e37e5ae-independent/review.json` and
`hud-e37e5ae-1080-independent/review.json`.

**Overall visual acceptance still fails.** Broad panels obscure the world,
Landing and HighCollector subjects are almost black, dojo lamps glare, and
the horses, bow and world remain provisional. The cargo view also exposes
distant floating platforms and a gray void. These prepared uncooked M2 Ultra
captures do not establish ordinary play, photoreal art, M1/Windows performance,
a new package or later boss states. The latest package remains `c655b6b` with
native bridge `10ad7dad`.

Claude's reviewed timber source is integrated at `6e951e5`: eleven art commits
through `1b4221b`, four timber-capture commits, refreshed campaign binding and
notices, and four registered source gates. Cache lookup, exact cloth material
slots and duplicate/altered placement records now fail closed. All 103 changed
LFS assets (130,902,261 bytes) are verified. All 37 asset/tooling gates pass on
the materialized root with unchanged source, including content, images, ledger,
notices and binding. The source candidate's earlier ledger failure for 577
unchanged LFS pointers is retained; its files were not corrupt. Root's stronger
notices and Nanite fallback helpers remain intact.

The new timbers have **no Unreal import or draw acceptance yet**. Unique logs
cover 65/260 columns and 235/940 rails; floors and the other halls remain open.
The first hall has about 57.1 million source triangles with unmeasured runtime
cost. The nine Blender originals remain visually rejected. A small import in
an isolated asset namespace is next, followed by actual exposure telemetry.
Claude is correcting the first-person contract and proposing a separate
six-member timber pilot. A2 lighting was already integrated at `e3b8aa5` and
was not reapplied. Frozen source/cache evidence remains intact.

CI `40144633078` succeeds at earlier `66a23f4`: five jobs, 85 source gates,
279 Rust tests passed and five explicitly ignored; tested/source trees and
archives are authenticated under `Saved/Qualification/2026-10-25/ci-66a23f4/`.
Later source does not inherit that qualification. Authorized unused-build
cleanup recovered 38.56 GiB of inactive incremental caches; source, active
builds and retained qualification artifacts were preserved. Disk no longer
blocks the capture lane. Full native/network/settlement, ordinary play,
photoreal art and platform/performance requirements remain open.

## October 24 cargo timing and campaign HUD checkpoint

At clean `eeaf2ed`, the Mac editor builds in 19.26 seconds and all five selected
SM6 1280×720 captures pass with zero selected errors/warnings: Cargo.Transfer,
BokkenDialogue, BowDraw, PickupNotices and CaptionPressure. The process reaches
natural EOF without a resource breach. All twelve original PNGs were inspected.
The 30/20/10 stock frames retain readable counters, horse/rope framing and visible
stand transfers. The final zero Registry title is visible, and the complete idle
Assessor readout now sits below the dialogue without covering the tracker.
This closes the specific final-frame collision observed at `235e810`.

The earlier `812d70c` cargo attempt is retained as a failure: world time was
3.000953 seconds but wall time was 2.891395 seconds, below the unchanged 2.9-second
gate. The capture pressed Interact directly from the screenshot-processed
callback after resuming the world. `eeaf2ed` sends that first press through the
same ordinary unpaused settling stage used by later transfers. Its v3 sidecar
binds resume, press and acceptance frames to the original screenshots. The three
holds measure 3.000092/3.000132/3.000090 world seconds and
2.998619/2.999462/2.991158 wall seconds; the complete cinematic measures
90.006284 world / 90.004961 wall seconds. Gameplay clocks, mapped controls,
duration gates and the cinematic remain unchanged; profile/input/save cleanup
passes. Evidence is retained under
`Saved/Qualification/2026-10-24/cargo-resume-8ab751a/`, including root visual
review `617503e1` and independent review `7f4ade39`. This is prepared uncooked M2 Ultra SM6 evidence, not ordinary
play, final art, 1080p or package acceptance.

Separately, clean `812d70c` passes all seven existing Campaign.Chapter2–8 capture
tests and archives all 22 originals against committed shot/catalog identities.
Every original was inspected. Seven primary bosses reach phase-one, full-health
telegraphs: quick_cut, hammer_slam, seizure_net, tether_lash, claw_flurry,
twin_burst and amort_ledger_beam. Their readouts clear the other measured HUD
panels, but **overall visual acceptance fails**: Tarifa's English Marobashi hint
crosses the ordinary center reticle, and LandingStealth, LedgerAisles and CargoHold
place stealth status under the tracker. These functional layout defects are being
corrected. Dark or obstructed subjects and broad HUD coverage also leave combat
presentation and art unqualified. No Muto, later phases, full campaign play or
new package is established. Independent review `35b9ce00` and root review
`5c59e8e8` retain these findings under `cargo-boss-campaign-93a8d8e/`.

CI run `40008222267` succeeds at the earlier pushed `71b9d2d`: five jobs,
82 source gates, 279 Rust tests passed and five explicitly ignored. Its tested
merge tree equals that source tree; original ZIPs/logs and exclusions are
authenticated under `ci-71b9d2d/`. This run does not qualify `812d70c`, `eeaf2ed`
or later changes. The separate native `cd9263628d` actual-crate plan remains
unrun: the unchanged 55 GiB launch reserve and compiler-exclusion conditions
have not been met. The full release goal remains open.

## October 24 rendered cargo and final-death source checkpoint

At clean `235e810`, the Mac editor builds in 21.03 seconds and all five selected
SM6 1280×720 tests pass with zero selected errors/warnings: Cargo.Transfer,
BokkenDialogue, BowDraw, PickupNotices and CaptionPressure. The outer process
and editor both reach natural EOF with no resource breach. All twelve original
PNGs are archived and independently inspected. The three stock frames show
wrapped objective text, horses clear of the tracker, and transferred stand
shares after the real delivery dialogue finishes. The final zero Registry
notice appears after the complete 90.007663-second world / 90.006150-second wall
scene; all three mapped holds and profile/input/temporary-slot cleanup pass.

**Visual acceptance still fails:** the final frame's upper-right tracker covers
part of the boss title and description. The automated layout gate did not detect
that collision. A measured boss layout and a shared overlap check are being
implemented; no 1080p success is claimed. The eight other prepared HUD fixture
images have no additional visible text collision in this set. These are assisted
uncooked M2 Ultra SM6 captures, not ordinary play, photoreal art or a package.
Independent review `a38a6acd` and root visual review `12ff3dd4` retain exact scope
under `Saved/Qualification/2026-10-24/cargo-hud-358af02/`. The earlier `b3a6e65`
compile failure and `c3c6c33` rejected final-notice bounds are preserved, including
the latter's three originals and missing final-zero image.

Separate signed native `cd9263628d` extends `6fd03be8` with final-tick deaths,
checked account transfers, ordered death stages, history retention and canonical
FFA completion in the bounded two-player/two-tick relation. Seventy standalone
CPU tests and eighteen provenance checks pass, covering 254 supported cases and
twelve refusals. The final CPU run takes 205.816 seconds, reaches natural EOF and
has no resource breach. The earlier 69-pass/one-failure mutation-harness attempt
is preserved. Independent review `39425032` checks the equations, public history
binding and original canonical observations; root authenticates 286 referenced
files. This remains separate source research: no actual crate, native proof,
wire-size or full-match/settlement qualification is established. A fresh 46-test
actual-crate CPU plan is prepared only, retaining the 55 GiB launch reserve,
30 GiB observational floor and exclusive compiler lane. The production bridge
stays `10ad7dad`; the older source, executable and failed resource proof remain
preserved. Evidence is indexed under
`Saved/Qualification/2026-10-24/native-final-death-cd9263628d/`.

## October 24 cargo counter and lead rope checkpoint

Signed author `57dcf3d` is integrated at clean `67cc9a0`. The bilingual objective
now shows 30 → 20 → 10 → 0 remaining sheaves, and the final zero is retained in
the existing Registry notice across the following scene. A twelve-segment visual
lead joins Bunta's animated halter to Kurimaru's provisional saddle tie. Its
300 cm slack model has no collision or pulling force; this is functional
presentation, with final materials, attachments and equine animation still open.

At exact `67cc9a0622a149bc1ce12e7fd5acad17157cf2e4`, CargoUnload,
BuntaLeadFear, KurimaruSpookDismount, Mount and Playthrough pass in the Mac editor
with zero selected errors/warnings; all 43 gameplay source gates also pass.
The directed tests inspect counter strings and actual rope-component endpoints
through movement, fear, pause, recall, retry and detach/reattach. Independent
runtime review `49d751a6` and source review `ea6dd5bb` are authenticated by root
against 112 retained file references and 131 Git blob records. Exact evidence is
in `Saved/Qualification/2026-10-24/cargo-counter-rope-57dcf3d/`.
These NullRHI tests do not establish rendered readability. A separate four-frame
capture is being prepared, including the zero notice after the full ordinary
90-second scene; no rendered result is claimed yet. New source remains uncooked.

Separate signed native candidate `6fd03be8` extends the bounded two-player,
two-tick carbine relation with the canonical Katana fallback. Independent review
`19866d1a` and root rehashes of 342 references and 47 Git blobs authenticate
61 standalone CPU tests, 13 provenance checks, 121 supported canonical cases,
five explicit refusals and 144 independently observed phase records. The initial
60-pass/one-failure attempt and the previous native proof's resource failure
remain preserved. Actual privacy-crate compilation, native proof and encoded
wire bounds for this changed source have not run. The prepared 37-test runner
retains the 55 GiB launch reserve and 30 GiB observational floor; no process is
signalled to make room. The production bridge remains `10ad7dad`.

CI `39997885857` succeeds at exact `7f18046`, with five jobs and 80 source gates
(43 gameplay, 17 tooling, 11 assets, five audio and four Rust); 279 Rust tests
pass and five long tests remain explicitly ignored. Independent review
`29b53c98` verifies the source and tested-merge trees, GitHub archive digests,
all gate reports and raw job logs. Root rehashes 101 file references and 56 ZIP
log members under `Saved/Qualification/2026-10-24/ci-7f18046/`. This predates
`67cc9a0` and does not qualify its added source. The previous `56ba142` run is
cancelled, although all 80 reports completed; it is not a successful workflow.
Private raw assets and native execution remain outside CI scope; the existing
plain-Git fern warning and Node action warnings remain recorded.

## October 24 cargo transfer checkpoint

Signed author candidate `d8ae065` is integrated as `ec91382`. The authored
30 sheaves and ten per destination are now strictly admitted in generated and
runtime data. Remaining load derives from accepted delivery credit, and each
stand derives from its unique destination credit; there is no second inventory.
The paired pack bundles and three drying stands are functional basic meshes,
with no new collision, proximity requirement, loss policy or return gate.

At clean `ec91382962d342bdd23d37b2e06689f072275819`, the Mac editor build and all
seven CargoUnload, BuntaLeadFear, KurimaruSpookDismount, Mount,
CarrySealAndSetDown, CarryDifficulty and Playthrough tests pass with zero
selected errors/warnings. All 43 gameplay source gates also pass. The cargo
fixture observes 30 → 20 → 10 → 0, ten at each completed stand, cancellation,
pause, foot unloading with the horses behind, retry after a completed transfer,
final state before teardown, and the ordinary mapped remount after Shimo spook.
Six destination orders have host-rule coverage; UE traversal uses Kami, Naka,
then Shimo. Assisted checkpoint placement and frozen threats remain explicit.

Independent runtime review `82fe0a1e` and source review `b4862d67` authenticate
original build receipts, terminal EOF, all logs, exact source/configuration and
kernel/native inputs. Root rehashes 60 file references and 112 Git blob records.
Evidence is under `Saved/Qualification/2026-10-24/cargo-transfer-d8ae065/`.
The editor log's 855-byte TraceServer appendix is retained separately from its
original recorded prefix. Two existing chapter-two host pacing overruns remain.

This establishes functional component visibility, not rendered readability or
photoreal acceptance. The later `67cc9a0` checkpoint above adds the numeric cargo HUD and
connecting lead rope with separate source and editor evidence. New source remains uncooked; ordinary play, current
packages, actual M1/Windows/performance, full native/network/settlement and the
complete first release remain open. Claude retains art ownership.

## October 23 horse behavior and bounded proof checkpoint

Bunta's own proximity fear now starts her authored 2.5-second recovery and a
one-second steering interruption for her mounted leader. The leader can still
move and rein; manual and automatic steering resume after the complete tug.
Remaining beside the same threat does not continually restart either clock.
Kurimaru's separate `on_spook: dismount_continue` policy applies only to
ch04.b14: his actual own-spook onset dismounts without new damage or cargo loss.
The existing simultaneous net branch retains its thrown damage and priority.
The other seven mounts retain their ordinary spook behavior.

At `2ab5d01`, the source-bound Mac editor build and seven of eight selected
tests pass. Bunta's exact pause checks preserve both timers, positions and
full-precision yaw. At 60/120 Hz, steering resumes at 1.016666720/1.008333386
active seconds and fear ends at 2.500000130 seconds. Kurimaru passes both actor
tick orders, same-encounter remount, pause/retry, damage-free spook and net
priority. Whistle recall takes 3.000000156 active seconds in both orders.
Mount, Playthrough, Searchlights, HorseDown and ConvoyNets pass too. All 43
gameplay source gates pass at this exact source.

CargoUnload initially returns false while riding to Shimo. Diagnostic
`d6d51b0` identifies a real spook dismount at frame 561; the old fixture assumed
the horse would remain mounted. `3a3a3d3` uses the rebound Interact key to remount
normally and completes all three deliveries. CargoUnload, BuntaLeadFear and
KurimaruSpookDismount pass together at this source, with zero selected errors
or warnings and a zero terminal exit at EOF. The earlier Bunta pause failure
at `abfa730` is also retained: its fixture narrowed double yaw to float before
exact comparison. The correction preserves native precision and adds separate
exact checks. No production timing, fear, damage or collision rule is waived.
These fixtures freeze opponents and assist setup; ordinary encounter pacing
and cargo presentation remain unqualified. Visible cargo transfer and the
connecting lead are still being completed separately.

The actual native `01d4e46` carbine cohort has finished naturally. Its retained
executable produces one 3,005,248-byte proof, separately verifies it, rejects
45 public mutations plus corrupt and truncated proofs, and receives actual
prover `Constraint` failures for eight invalid witnesses. Proving takes
725.802387 seconds and verification 18.843102 seconds; the native test exits
zero after 3,469.49 seconds. **Overall qualification fails:** the observational
guard records one fall below the unchanged 30 GiB disk reserve and returns
125. The enclosing runner records failure after 3,475.657 seconds. Functional
evidence is retained without waiving that resource failure or rerunning the
proof. This remains an unregistered two-player/two-tick research relation;
Core authority, full World/history, full-match and settlement acceptance remain
open, and the production bridge is unchanged.

The twelve-module SM5 GI-source experiment at `e34edc8` stops before replacement
rendering because Kamiza's public bounds change during rebuild. The equality
gate remains strict. A separate eleven-module experiment at `abfa730` leaves
Kamiza unchanged and completes all six functional phases. Its recorded
geometry/material/Nanite/culling controls match within the replacement pair;
only ten targeted meshes' SDF/card data change, while the column matches.
The floor and nearby cargo brighten, but the broad room remains dark. All six
original frames were inspected. This attempt also fails its 30 GiB resource
reserve. Both experiments restore and verify all 48 candidate files and remove
their unique temporary proxies. Neither admits a production art or lighting
repair; the twelve-module hypothesis remains unresolved.

CI `39988965609` authenticates 80 gates in five jobs at `e34edc8`, with identical
source/tested-merge trees, including 279 Rust passes and five explicitly ignored
research tests. It includes the prior cargo/timer work but predates these horse
changes. Private raw-asset exclusions and source-only native parity remain
explicit. New source is uncooked; `c655b6b` remains the latest packaged baseline.

Evidence under `Saved/Qualification/2026-10-23/` includes
`campaign-bunta-abfa730/`, `campaign-kurimaru-2ab5d01/`,
`campaign-cargo-d6d51b0/`, `campaign-cargo-3a3a3d3/`,
`native-carbine-adapter-01d4e46/native-proof-attempt-1/`,
`dojo-room-gi-replacement/`, `dojo-architecture11-gi-replacement/` and `ci-e34edc8/`.
The following sections retain their historical source and pending states.

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

### 2026-10-26: palace registry runtime and assisted campaign

The chapter-six store and registry use the authored palace frame. Three desks
stand at (16,29), (6,29) and (-2,29) metres from the garden origin on real 0, 15
and 30 cm floors. The builder supplies a level 1.8 m south corridor, vestibule,
store, walls, doorway gaps and coffered ceiling. Desk meshes, interaction rays,
contest checks and objective markers use local floor heights. This construction
geometry has not passed final art review.

Signed `53a4be3a` passed all 58 local gameplay source gates and all 111 CI gates
in run 40249002097 on an identical tested/source tree. Independent CI review
SHA256: `ac5b4c016e5fcf0c8642e150b353ea9c36b01bbc44b6e104bfd5ae088e0abb25`.
Its separate editor build then failed because `auto*` could not unwrap the
light component's `TObjectPtr`. No runtime tests ran in that failed attempt;
the original build log is retained. Signed `adca677d` fixes the pointer access
with `.Get()` and builds successfully.

At exact `adca677d`, six of seven NullRHI tests pass: RegistryPatrols, Patrol,
BlockedWalksOn, CopyDesks, Spaces and Candle. RegistryPatrols uses the actual
authored guards: initial lit desk visits measured 5.917, 7.917 and 9.917 seconds
against the 6/8/10-second targets, then each auditor walked its circuit and
returned. Menu pause held visits and lights; defeating an auditor extinguished
its lamp; retry destroyed old lights and created exactly three replacements.
The grounded rifle circuit completed at 60,000 ms and the drone at 30,000 ms,
with the drone remaining at Z400. These are directed behavior checks with the
hero placed behind the hall wall, not ordinary stealth difficulty or a rendered
lighting review. All 20 evidence files and unchanged source/native, Config and
Generated inputs were independently verified after natural editor/wrapper
exits 3/1. Review SHA256:
`4223e282d66411ea68e2afef270e1c84b1846fd4015bd21fdbc3b5a50777a70d`.

The failed seventh case, assisted Playthrough, correctly grabbed a fallen
auditor when Interact was pressed beside its desk. Signed `a8242f65` changes
only automation: use held mapped Interact and ordinary walking to drag the
body clear, release it, return, and begin the copy with a fresh press. The
CopyDesks regression adds a real defeated auditor and verifies it was moved
and released. Both CopyDesks and the complete assisted 133-beat Playthrough
pass on the exact signed source with zero selected errors/warnings and natural
exits 0/0. All three bodies' positions were recorded in the runtime log from their
desks to the corridor; copy progress remained zero while dragging. All 20
files and unchanged inputs were rechecked. Review SHA256:
`94c7c0d1e87cdbb2905c14543c14924d47251d848d3b82d7416d43533ea19118`.
The earlier failed attempts remain preserved under the dated registry folders
in `Saved/Qualification/2026-10-26`. CI for `adca677d` was superseded and
cancelled; no passing result is claimed for it.

The later `a8242f65` CI run 40250227769 also passes all 111 source gates.
The tested merge `a24704e0` has the identical source tree; all artifact digests
and raw logs were independently authenticated. Review SHA256:
`28c674fd381031f1e65a5630cacf5b0065b4ec07de1db805208764218a327d4b`.

Claude again owns the engine/Blender lane after root's natural completion.
The signed third-person grip direction (`3521e93e`) and archive lighting
addendum (`88539dc1`) remain production direction, not accepted assets. After
refitting the arm positions, the original centred two-paw target is reachable
but intersects the body/armor. The one-paw pose is explicitly interim; original
two-paw closure stays open. Gear clearance uses posed visible meshes, triangle
intersection and containment, with edge-edge as well as vertex-face separation
for minimum-gap thresholds. The movement capsule and nearest vertex distance
cannot certify those gaps. Rig/LOD consistency, closed paws, sockets, W00/saya
and guard renders remain with Claude; the lighting addendum is unimplemented.

Runtime qualification of the connected nightingale/garden/tatami route,
ornamental archive-door connection, authored store dressing, ordinary-control
play and final visual acceptance remain open. The preceding `f51c2236`
ArchiveFamilyPage and ArchiveRevealReset runs pass; six original 1920×1080
Metal SM6 frames show the full readable family record and reduced shelf/wall
glare. Archive final art remains rejected for dark opening/return characters,
unfinished materials, rigid poses and floating weapons. Newer source remains
uncooked; package/platform/performance and full native execution gates are open.

### 2026-10-26: ledger/palace spatial implementation awaiting Unreal

The source now places the full 24 × 64 m ledger hall, 10 × 8 m southwest annex,
five 3.2 m aisles, 1.2 m shelf banks, four cross-aisles and six one-metre niches.
A 2.7 m north passage joins the west entrance of the palace's L-shaped
nightingale corridor. Two quiet rooms extend the palace south while preserving
the garden origin, registry desks, archive, press hall and flood coordinates.
The b06 exit now lies in the palace vestibule. The twelve guards have distinct
routes: four aisle auditors, two scanning posts, two 35-second drones at 5.5 m,
two palace auditors and two palace rifles, including the 40-second leg-A walk.
Noise patches, rubble and lecterns use the authored local coordinates. The
loader and host validator reject changed route/guard/floor/door contracts.

All 59 gameplay source gates pass on an unchanged working tree. Its patch,
untracked sources and logs are frozen in
`Saved/Qualification/2026-10-26/ledger-working-source-attempt1`; independent
review SHA256:
`73ab270bd9d68bfa9e017d0a06b7e5a53a1c9adec5ad787a1f7e2a654521684d`.
The seven new contract tests cover continuous floor support across seams,
capsule clearance in aisles/niches, the annex-to-vestibule route through both
quiet rooms, exact guard assignments, noise rectangles, malformed records and
host/C++ route parity. This is source evidence, not an Unreal pass. Prepared
`Campaign.LedgerPatrols` and `Campaign.LedgerRoute` separately observe actual
guards and walk the physical route using mapped input with opponents held.

Unreal build, collision, navigation and clock checks are pending while Claude
owns the engine lane. The current generic drone capsule has a 52.8 cm scaled
half-height, larger than the 50 cm clearance above the authored 5.5 m flight
centre; this is an unresolved body/ceiling fit concern to check explicitly.
The 20 cm silent strip also needs a reachable foot-contact policy beside a
solid wall for the ordinary 34 cm player capsule. Neither dimension is widened
to make a source test pass. Sliding fusuma, carried auditor lamps, the alarm
shutter, reinforcement-door placement, noise calibration, garden/annex dressing
and final slate/shoin art remain open. The timber binding changes only the
chapter-six data hash; no art mesh or texture was regenerated.

## Milestones and evidence

| ID | Deliverable | Owner | Current state / completion evidence |
| --- | --- | --- | --- |
| T1 | Reproducible Mac development toolchain | Codex toolchain lane | UE 5.8.3 / CL 58210709 installed and identity checked on M2 Ultra. Xcode 26.1.1 / 17B100, SDK 26.1 and Metal 17B54 installed; doctor and editor build pass. Full imports/validators pass for 280 original-art, 345 CC0 and 267 audio packages, 27 VFX systems, the craft prop and 12 dojo-kit modules. Actual SM5 and SM6 captures pass on this M2 Ultra. Xcode 27 and global selection are preserved; that compiler has not been qualified for this project. |
| G1 | Complete authored offline campaign mechanics | Codex gameplay lane | Exact `4fa637f` passes CopyDesks, Candle and the complete assisted campaign with zero selected errors/warnings and natural EOF; three separate held copies now replace the generic chapter-six timer. Exact `bf58810` passes 15/16 directed Unreal cases, including all pods, real horse-shell cadence/bait, treatment, corrected canister/MarginLinger and the assisted 133-beat route. Fixture-only `2a69fb5` passes the remaining dud case and shared arming regression. Casting, bridge/props, helm and cane cases have earlier directed passes. Exact `0adc081` separately passes all 13 withdrawal/horse/pod/treatment/assisted campaign cases, with no errors and one external HTTP connectivity timeout. The withdrawal includes real movement and the complete gate-clear call before the cinematic. Prepared rendered withdrawal at `5d02f3b` also passes, including the six-person detail and readable tracker; ordinary controls/pacing, remaining mechanics and current packages remain open. |
| G2 | Complete playable campaign spaces and encounters | Codex + Claude | Exact `adca677d` passes actual registry visits/lamps, rifle/drone periods, tier traversal, Spaces and Candle. Automation-only `a8242f65` passes CopyDesks with real held body drag and the assisted 133-beat route. The full ledger/palace source now passes 59 gameplay gates; Unreal traversal/patrol checks and final art remain open. Use authored layouts, patrols and encounters; verify traversal, collision, navigation, interaction reach, stealth and boss behavior. Verify all eight chapters and 133 beats with normal controls; headless shortcuts do not establish pacing or difficulty. |
| U1 | Readable bilingual gameplay and accessible controls | Codex HUD lane | At clean `5f7958f`, the complete Metal SM6 HUD matrix passes all nine prepared scenes at both 1280×720 and 1920×1080, with zero selected-test errors/warnings. All 36 actual images were viewed and their hashes retained. Measured dark backing resolves the gold Examine text over bright bellows and objective labels over bright dojo surfaces, while ordinary Work remains above coaching. No blocking overlap or clipping appears in the matrix. Earlier `febb516` hidden-prompt and `495170d` low-contrast visual failures remain preserved. Both original logs received trace-server shutdown output after their capture manifests were written; reviews retain and bind the exact original prefix, appended suffix and final full log separately. The owned-stream runner at `977c12d` then passes one actual Metal SM6 BellowsGamepad capture at 1280×720: one selected test, zero errors/warnings, two original frames viewed, editor/runner exit zero and inherited-stream EOF true. Its manifest and completion receipt match the entire final raw log, including trace-server shutdown. The earlier wrong-filter invocation remains preserved as a failed launch with correctly retained exit 3. The runner also passes 47 CPU process/report/source tests. U1 remains open for normal-control play, dense bilingual screen coverage, small projected labels, accessibility, motion and packaged/platform qualification. Prepared stress scenes do not establish those gates. |
| A1 | Unique timber kit and golden-hour Estate/dojo slice | Claude | Nine baseline meshes/31 packages pass import and reopen at `97c08a0`. At `0c7961d`, 36 SM6 and 18 SM5 captures pass readiness checks on M2 Ultra, with original-image review; this closes capture readiness only. The separate six-member v2.1 pilot remains visually rejected for smooth bands, blister dents, glossy ridges and repeated adze marks. The separate v2.2 pilot also fails review of all 15 originals for smooth striped surfaces and repeated adze tiling. Claude owns the engine lane for the corrected bow; a focused timber patch is next. Unique per-placement binaries, dressing, full provenance and photoreal acceptance remain open. M2 SM5 does not qualify M1. |
| A2 | Complete character and first-person presentation | Claude | Nyaakoto, paws, sword/saya, clothing, fur and motion must pass [photoreal acceptance](art-direction/photoreal-acceptance.md) in actual gameplay and cinematics. Generated references and Blender images are source evidence only. |
| A3 | Complete campaign/arena art, animation, audio and effects | Claude + Codex integration | Extend approved visual direction across every environment, character and encounter; complete dialogue presentation, cinematics, sound, music and effects. Review every asset's rights and ledger records. Missing original references remain explicit, rather than being claimed as matched. |
| Q1 | Repeatable source validation and CI | Codex validation lane | Authenticated CI `40250227769` passes all 111 gates in five jobs at exact `a8242f65`. The newer ledger contract adds one gate; its CI is pending. Tested/source trees match; all five artifact digests and raw logs are verified. This closes the selected source checks only; private assets, Unreal behavior, rendered art, packages and full native execution remain separate gates. Historical failures and ignored proof cases retain their original scope. |
| N1 | Matching native kernel and Connect integration | Codex | Kernel ABI4 stages and passes 94 parity cases/99,043 ticks. Signed clean native `10ad7daddf` passes29/29 directed tests and has a fresh frozen ABI30 release build with its original sidecar. All29 frozen files and six consumer hashes were checked before staging; actual UE NativeLoader passes in the `56b95f3` editor and the `b4a02d1` packaged Metal client, with the exact staged library path. Strict package/artifact hashes verify before and after execution. These tests cover loading, binding, canonical JSON and hashing; signing, submission and finality are not tested. Earlier producer records remain preserved. Windows loading remains unverified. |
| N2 | Complete native execution proof and real settlement | Codex | Bounded native `01d4e46` completes actual crate compilation/31 CPU tests and a 3,005,248-byte proof with separate verification and 55 negative cases, but its proof attempt fails the unchanged disk reserve. Signed `6fd03be8` adds Katana fallback, and `cd9263628d` adds final-tick death/account/FFA completion with independently authenticated standalone source evidence. Fresh `cd9263628d` passes 18 provenance tests, 70 standalone constraints, exact regeneration of four final-death fixture files, and 46 actual-crate CPU tests with four ignored proofs. The actual adapter covers 254 layouts, at most 3,803,712 bytes; independent CPU review and the unchanged retained binary are sealed into the completed proof plan. Two earlier runner failures and the successful observer retry remain preserved. Fresh native proof cohort completes: one separately verified 3,666,144-byte proof, 92 verifier rejections and eleven actual-prover Constraint rejections, natural EOF zero and 116 files independently verified. This remains an unregistered two-player/two-tick relation. Historical outputs are partly missing, with no cause inferred. No registered full Arena execution profile, full World/death/ability/terminal composition, full-size proof or settlement acceptance is established. Four-validator admission/dispute/settlement, market recovery and Connect signing/finality remain open; live funding/trading stay disabled. |
| R1 | Windows and Mac release candidates | Codex | Latest completed Mac Development package `c655b6b`, native bridge `10ad7dad`, passes Game build, cook of 1,323 packages with zero cook errors/warnings, staging/signature checks, smoke, all 164 client tests and a fresh rendered Title check. Newer gameplay and art source remains uncooked. Earlier rejected packages and warning/failure records remain preserved in the dated checkpoints. Clean-machine install, normal campaign play, controller/accessibility, multiplayer recovery, Windows and actual M1 performance remain open; M2 results do not qualify M1. |
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
