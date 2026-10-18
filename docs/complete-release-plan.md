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

## Milestones and evidence

| ID | Deliverable | Owner | Current state / completion evidence |
| --- | --- | --- | --- |
| T1 | Reproducible Mac development toolchain | Codex toolchain lane | UE 5.8.3 / CL 58210709 installed and identity checked on M2 Ultra. Xcode 26.1.1 / 17B100, SDK 26.1 and Metal 17B54 installed; doctor and editor build pass. Full imports/validators pass for 280 original-art, 345 CC0 and 267 audio packages, 27 VFX systems, the craft prop and 12 dojo-kit modules. Actual SM5 and SM6 captures pass on this M2 Ultra. Xcode 27 and global selection are preserved; that compiler has not been qualified for this project. |
| G1 | Complete authored offline campaign mechanics | Codex gameplay lane | All 62 campaign/fieldcraft/Connect tests pass at clean `56b95f3`, zero errors/warnings, including the full 133-beat/8-chapter traversal, seal/set-down, carry tiers and cooperative crank/net/ratchet/crew rules. Named capacities, crank stamina/held input, alternating bellows treads, and physical lift/spiral/summit traversal are implemented in an isolated integration branch; their new engine fixtures remain unrun. The combined editor build passes through `3c436a5` after adapting movement bases to UE 5.8. Later summit and bellows additions still require a combined compile. Shared rhythm assist and exact manufacturing phrases remain in development. Full normal-control pacing/play verification remains separate from accelerated fixtures. |
| G2 | Complete playable campaign spaces and encounters | Codex + Claude | Use authored layouts, patrols and encounters; verify traversal, collision, navigation, interaction reach, stealth and boss behavior. Verify all eight chapters and 133 beats with normal controls; headless shortcuts do not establish pacing or difficulty. |
| A1 | Unique timber kit and golden-hour Estate/dojo slice | Claude | Nanite policy integrated. Explicit material permutations and reimport resolve prior coarse sampling in same-source `2bb3e36` SM5/SM6 dojo frames; all twelve viewed. Repetitive box geometry, clipped light and placeholder props still fail photoreal acceptance. Unique per-placement timber, dressing, provenance/fallbacks and visible Nanite draw evidence remain open. M2 SM5 does not qualify M1. |
| A2 | Complete character and first-person presentation | Claude | Nyaakoto, paws, sword/saya, clothing, fur and motion must pass [photoreal acceptance](art-direction/photoreal-acceptance.md) in actual gameplay and cinematics. Generated references and Blender images are source evidence only. |
| A3 | Complete campaign/arena art, animation, audio and effects | Claude + Codex integration | Extend approved visual direction across every environment, character and encounter; complete dialogue presentation, cinematics, sound, music and effects. Review every asset's rights and ledger records. Missing original references remain explicit, rather than being claimed as matched. |
| Q1 | Repeatable source validation and CI | Codex validation lane | Common runner/CI integrated. Gameplay/tooling passes 35/35 on clean integration source `a4e0c8c`, unchanged source. That check precedes the movement-base compatibility, summit and bellows follow-ups. The baseline `b4a02d1` PR CI also passes Rust, gameplay, tooling and audio; asset CI still fails the recovered weapon ledger and stale notices. The notice generator correction is integrated for the next run. Clean Rust passes 279 tests with five long research runs explicitly ignored. Capture archive regression tests pass 20/20. Ledger still fails on 228 recovered weapon records. Source checks do not imply engine, package, performance or live-network qualification. |
| N1 | Matching native kernel and Connect integration | Codex | Kernel ABI4 stages and passes 94 parity cases/99,043 ticks. Signed clean native `10ad7daddf` passes29/29 directed tests and has a fresh frozen ABI30 release build with its original sidecar. All29 frozen files and six consumer hashes were checked before staging; actual UE NativeLoader passes at `56b95f3`. Earlier producer records remain preserved. Package/Windows loading remains unverified. |
| N2 | Complete native execution proof and real settlement | Codex | Full authenticated state, legal attacks, damage/death, conserved awards, disconnect handling and composition remain open. Require actual four-validator test-XOR admission/dispute/settlement and market evidence, Connect exact-action signing/finality recovery, and full-size proof qualification. Component hit proofs do not satisfy this milestone. |
| R1 | Windows and Mac release candidates | Codex | Fresh declared candidate `b4a02d1` with native `10ad7dad` passes Editor/Game build, full cook (1,314 packages, seven platform skips, zero UE cook errors/warnings), and staging with strict signature and source/artifact verification. The rejected `56b95f3` archive remains preserved; the narrow staging guard fix records newly created Crypto metadata separately. Packaged startup smoke passes with Entry/SoraGameMode, Japanese and exit 0. The 131-test real-Metal packaged suite is still running. Its missing HTML report template is recorded and corrected in the next source; final JSON results and packaged native loading remain pending. Require clean-machine install/start, campaign completion, saves, controller/accessibility, Japanese UI/default English subtitles, multiplayer recovery and performance. Windows, actual M1 fallback and M2 Nanite results remain separate. |
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
