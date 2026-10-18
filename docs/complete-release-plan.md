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
| G1 | Complete authored offline campaign mechanics | Codex gameplay lane | All 57 campaign/fieldcraft/Connect tests pass at clean `13ec0cd`, zero errors/warnings. The three carry tiers, inspection checkpoint boundary and lifecycle cleanup are verified. At `16b7762`, seal pry/manual set-down, carry difficulty and full 133-beat/8-chapter traversal pass again with zero errors/warnings. Named capacities and co-operative crank/ratchet rules remain. Full normal-control pacing/play verification remains separate from accelerated fixtures. |
| G2 | Complete playable campaign spaces and encounters | Codex + Claude | Use authored layouts, patrols and encounters; verify traversal, collision, navigation, interaction reach, stealth and boss behavior. Verify all eight chapters and 133 beats with normal controls; headless shortcuts do not establish pacing or difficulty. |
| A1 | Unique timber kit and golden-hour Estate/dojo slice | Claude | Nanite policy integrated. Explicit material permutations and reimport resolve prior coarse sampling in same-source `2bb3e36` SM5/SM6 dojo frames; all twelve viewed. Repetitive box geometry, clipped light and placeholder props still fail photoreal acceptance. Unique per-placement timber, dressing, provenance/fallbacks and visible Nanite draw evidence remain open. M2 SM5 does not qualify M1. |
| A2 | Complete character and first-person presentation | Claude | Nyaakoto, paws, sword/saya, clothing, fur and motion must pass [photoreal acceptance](art-direction/photoreal-acceptance.md) in actual gameplay and cinematics. Generated references and Blender images are source evidence only. |
| A3 | Complete campaign/arena art, animation, audio and effects | Claude + Codex integration | Extend approved visual direction across every environment, character and encounter; complete dialogue presentation, cinematics, sound, music and effects. Review every asset's rights and ledger records. Missing original references remain explicit, rather than being claimed as matched. |
| Q1 | Repeatable source validation and CI | Codex validation lane | Common runner/CI integrated. Gameplay/tooling passes 30/30 on clean `16b7762`, unchanged source. Clean Rust passes 279 tests with five long research runs explicitly ignored. Capture archive regression tests pass 20/20. Ledger still fails on 228 recovered weapon records. Source checks do not imply engine, package, performance or live-network qualification. |
| N1 | Matching native kernel and Connect integration | Codex | Kernel ABI4 stages and passes 94 parity cases/99,043 ticks. Signed clean native `75e4ca15` ABI30 bridge passes frozen consumer smoke and actual UE NativeLoader at `13ec0cd`. The original artifact manifest is preserved; later consumer qualification is separate. Native directed tests pass29/29 on clean `10ad7daddf`; fresh release build from that source is in progress. Package/Windows loading remains unverified. |
| N2 | Complete native execution proof and real settlement | Codex | Full authenticated state, legal attacks, damage/death, conserved awards, disconnect handling and composition remain open. Require actual four-validator test-XOR admission/dispute/settlement and market evidence, Connect exact-action signing/finality recovery, and full-size proof qualification. Component hit proofs do not satisfy this milestone. |
| R1 | Windows and Mac release candidates | Codex | Fresh Mac cook at clean `16b7762`: 1,314 packages,385 materials,zero errors/warnings. Game build/staging and packaged qualification remain pending. Require clean-machine install/start, campaign completion, saves, controller/accessibility, Japanese UI/default English subtitles, multiplayer recovery and performance. Windows, actual M1 fallback and M2 Nanite results remain separate. |
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
