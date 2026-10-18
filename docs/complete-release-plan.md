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
| G1 | Complete authored offline campaign mechanics | Codex gameplay lane | Maai, equipment recovery, event-driven dialogue, guarded hoist and both chapter-eight ending routes pass directed UE tests. The registry data, production/retry/result lifecycle and elapsed/skipped ceremony completion pass; checkpoint semantics and visual review are being checked. The full 133-beat/8-chapter traversal passes at `e22203b` after fixing a recovery handler that blocked optional caches, with a directed regression. Its 187 teardown warnings remain recorded; the lifecycle fix awaits verification. Difficulty-specific carrying and co-operative crank behavior remain. Each needs directed regression checks, checkpoint/reload checks and normal-input UE play verification. |
| G2 | Complete playable campaign spaces and encounters | Codex + Claude | Use authored layouts, patrols and encounters; verify traversal, collision, navigation, interaction reach, stealth and boss behavior. Verify all eight chapters and 133 beats with normal controls; headless shortcuts do not establish pacing or difficulty. |
| A1 | Unique timber kit and golden-hour Estate/dojo slice | Claude | Unique per-log geometry, physically coherent materials, dressing and SORA craft; preserve gameplay envelopes. Require source provenance, fallback assets, unedited in-game close views, and separate SM5, SM6 and Nanite evidence. Mac Nanite policy commit `cfcea32` is integrated; paired real SM5/SM6 capability and dojo captures each pass 3/3 at clean source `640529d`, with six archived original frames each. Visual inspection fails the old kit on conspicuous blocky materials, clipping light and placeholder props on both renderers. SM6 reports Nanite eligibility; actual Nanite geometry and unique timber admission remain open. |
| A2 | Complete character and first-person presentation | Claude | Nyaakoto, paws, sword/saya, clothing, fur and motion must pass [photoreal acceptance](art-direction/photoreal-acceptance.md) in actual gameplay and cinematics. Generated references and Blender images are source evidence only. |
| A3 | Complete campaign/arena art, animation, audio and effects | Claude + Codex integration | Extend approved visual direction across every environment, character and encounter; complete dialogue presentation, cinematics, sound, music and effects. Review every asset's rights and ledger records. Missing original references remain explicit, rather than being claimed as matched. |
| Q1 | Repeatable source validation and CI | Codex validation lane | Common runner and CI are integrated, with logs and machine-readable results. Gameplay/tooling passes 28/28 on clean `44a03ce`, with unchanged source. A clean Rust rerun passes 279 tests after a deterministic expired-offer regression corrected the handshake-count assertions; five long research runs remain explicitly ignored. The ledger still fails on 228 recovered weapon records. Source checks do not imply engine, package, performance or live-network qualification. |
| N1 | Matching native kernel and Connect integration | Codex | Kernel ABI 4 stages and passes 94 parity cases / 99,043 ticks. Signed, clean native `75e4ca15` builds the ABI 30 bridge; consumer smoke passes 26 symbols, seven builders/eight canonical cases and 282 malformed requests, with non-authorizing Join inspection. The sealed source-bound bridge and matching consumer are integrated; a fresh native smoke on the copied artifact passes. Actual UE loading and packaging remain unverified. Native Rust test closure needs its separate P2P compile prerequisite. Shared Iroha remains untouched. |
| N2 | Complete native execution proof and real settlement | Codex | Full authenticated state, legal attacks, damage/death, conserved awards, disconnect handling and composition remain open. Require actual four-validator test-XOR admission/dispute/settlement and market evidence, Connect exact-action signing/finality recovery, and full-size proof qualification. Component hit proofs do not satisfy this milestone. |
| R1 | Windows and Mac release candidates | Codex | Reproducible cooks/packages on pinned UE 5.8.3; clean-machine install/start, campaign completion, saves, controller/accessibility, Japanese UI and default English subtitles, multiplayer recovery and performance evidence. Windows, M1 fallback and M2 Nanite results must be reported separately. |
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
