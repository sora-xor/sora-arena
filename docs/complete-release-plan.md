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

## October 20 qualification update

These results supersede the running-state descriptions in the retained milestone
history below. The release remains incomplete.

- Mac candidate `298ed9e`, native `10ad7daddf`, passes Game build, full cook
  (1,316 packages, zero cook errors/warnings), staging, strict signatures and
  before/after artifact identity. Startup smoke and the untouched rendered title
  pass. The full Metal suite completes 148 tests: **147 pass, one fails, zero
  test warnings**. `Campaign.Spaces` fails four chapter-eight spawn-floor checks.
  `ScriptedFight`, `FrontEndScreens`, `GalleryPois` and `NativeLoader` pass.
  This package fails qualification. Its 19 front-end frames were viewed; the
  scrolled Credits Back button loses Japanese `戻る`, although English `Back`
  remains. Title tracing shows the tour's injected Enter; it does not establish
  the historical full-suite initial-state cause.
- All five CI source groups pass for `298ed9e` in run `39416677000`. The tested
  merge `3e45733` has the same tree as that head, and all downloaded reports
  record unchanged source. The later gallery-cache candidate `a8dfcf7` passes
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
- Chapter-one source audit finds a release blocker missed by accelerated
  traversal: b07 dispatches its archery targets as sparring pupils, and dojo
  controls cannot equip the bow. Six-shot scoring, swinging targets, finite
  arrows/retrieval and the six-usable/six-bent smithy handoff require
  implementation. Normal b01–b06 controls are source-feasible but have not
  been qualified by a continuous ordinary-input run. Also open: the real
  awase event does not start the missed-marobashi hint timer, dojo play skips
  passive zanshin, and pupil windups lack the authored variation. Directly
  recorded forms, synthetic marobashi and lethal test damage establish none
  of those authored interactions.
- Frozen native research has completed three actual component proofs:
  parry (3,027,008 bytes), marked ward (3,014,624), and simultaneous contact
  (3,012,512). Each has separate verification and rejected statement/proof
  mutations; root checked the proof and six source hashes. Stance, plasma
  and seven actual prover-negative checks remain pending. This is unregistered
  research, not the staged bridge, a complete accepted-control/World proof,
  settlement or reference-M1 qualification.
- Saved-source W09 diagnostics reproduce the original two out-of-range UV
  corners on the barrel, then obtain 4,654 faces and zero out-of-range corners
  in three in-memory weighted-collapse variants. Protecting all barrel chart
  boundaries retains all 270 exact boundary geometry/UV signatures. Uniform
  weights alone also change the result, so the experiment does not establish
  that pinning is the unique cause or qualify a repair. Shape/distortion,
  reproducibility and the existing normal metric failure remain open; no art
  bytes, textures or acceptance thresholds changed.

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
