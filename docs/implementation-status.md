# First-release implementation record

The active goal is the complete approved SORA Arena release. This is a progress
record, not a claim that the release is complete. Backward compatibility,
legacy formats, aliases, and fallback decoders are prohibited.

Japanese is the primary language for all dialogue and player-facing interfaces.
English subtitles are on by default. Localization is part of campaign production,
including subtitle timing, speaker identification, readable Japanese fonts and
controller-readable menus. The offline catalog now contains 24 timed bilingual
dialogue cues across eight chapters, shown during active gameplay; no voice acting
is recorded, and timing/readability still need Unreal play verification.

## Milestones and current evidence

| Milestone | Current state | Completion evidence still required |
| --- | --- | --- |
| Foundation | Active: deterministic Rust kernel and C ABI; locked workspace tests and strict Clippy pass; native generic admission, catalog and Connect changes in isolated Iroha worktree | UE 5.8.2 build, real wallet pairing, complete two-player proof-to-settlement path |
| Research match | Pending | 4v4 two-minute match, then 6v6 ten-minute match with complete proof coverage and measured resources |
| Vertical slice | Source and original prototype assets in progress | One finished mission/arena, representative classes and complete buy/equip/bond/play/settle flow |
| Full production | Chapter/class/weapon/arena data and offline prototype source present | Eight authored chapters, finished art/animation/audio/cinematics, accessibility and measured balance |
| Qualification | Unqualified; funding/trading disabled | Independent review, four validators, Windows/macOS parity, adversarial integration and performance tests |
| Release | Pending | Packaged Windows/macOS builds, recovery tools, release manifest and operational documentation |

The Rust simulation includes integer movement/collision, melee and ranged attacks,
projectiles, deterministic ammunition/reloads, objectives, fixed initial-reserve
losses and conservation. [Weapon handling](combat-rules.md) records exact timing. Its current
geometry and class abilities are a foundation implementation. The Unreal campaign
prototype currently has its own gameplay implementation. Kernel-driven offline
practice source and its native presentation queries are implemented. A real
macOS library passes 73 checked-in replay cases / 44,100 canonical ticks; Windows
has not run that fixture. Actual UE compilation and runtime testing are still
required before claiming the Unreal integration works. A separate headless test
runs a twelve-player idle Control lobby for the full 36,000-tick ten-minute clock,
checks deterministic terminal state and XOR conservation; it does not measure
networking, combat load, rendering, or proving.
The offline campaign now persists chapter objectives (defeated invaders,
restored production sites, and exit completion) to a local SaveGame checkpoint
and restores them on retry/restart; this still needs an editor build and an
in-game save/reload test.
The campaign presentation and playable protagonist remain the Nyaagyu Samurai;
the six-class selector is available in offline arena practice. This source
behavior still needs an Unreal menu and save/reload check.
Three original Edo/alien environment props now have editable Blender source,
FBX exports, metric collision/bounds checks, and campaign placement source.
Blender review renders and the import manifest do not establish in-engine
appearance; the UE 5.8.2 import and visual pass remain open.

The provisional first-release balance correction changed Arc carbine and
Clockwork repeater attack cooldowns from 10 to 12 simulation ticks. A clean-lane
`World::step` test checks body-shot death ticks against 100/125/150 HP targets
for both guns. The team-mode Healing lance heals the nearest living ally
intersected by its ray, capped at that class's maximum health; an enemy struck
first still takes damage. In FFA it damages opponents. Queued heals resolve
before same-tick damage, and five behavior tests cover targeting, cap, dead
allies, FFA, and simultaneous order. Plasma matchlock now penetrates guard only
with its charged direct hit. Kanabo has an eighteen-tick windup, and charge is
bound to its selected weapon, preventing cross-weapon precharge. Those rules
advance the identity to `sora-arena-first-release-4`. Native presentation ABI
3 exposes charge progress to a Japanese HUD bar and world-pawn weapon pose;
opponent readability has not been playtested. The deliberately re-recorded
ABI 3 macOS fixture retains identical controls, participant loadouts, map
geometry and input encoding. Its state/presentation expectations change in all
73 cases, while event streams change only for four Kanabo loadout cases. The
rebuilt library passes 73 cases / 44,100 ticks, eleven negative guards, and
72 native practice scenarios / 86,400 replayed ticks. The full locked offline
Rust suite, format checking, and strict all-targets Clippy pass.
These deterministic checks are not a human balance playtest. The separate
campaign prototype catalog still differs from the Rust multiplayer catalog;
full gameplay balance, presentation and proof coverage remain open.

Local rollback replays only complete signed commitment/reveal batches into the
confirmed world. Speculative state is isolated, capped at 120 ticks, and discarded
on disconnect. A durable local journal preserves certified pending commitments,
individual valid reveals and signed checkpoints across restart, then replays the
kernel against the caller's exact admission. Recovery rejects damaged records,
forged signatures and rollback behind a caller-supplied trusted receipt. Native
consensus deadlines and forced resolution, transport and complete FPS AIR
integration are still required; no peer timeout can settle funds. See
[P2P recovery](p2p-recovery.md) for the remaining durability and integration gates.
The bounded P2P wire codec signs complete commitment certificates, reveal
openings and checkpoints with version, context and sequence binding. It rejects
oversized, malformed, cross-session and replayed packets. The codec does not
prove the combat execution. A pairwise ChaCha20-Poly1305 wrapper now encrypts
those signed frames with session/channel binding and restored replay floors.
Authenticated 1,200-byte fragmentation now carries the largest 12-player
certificate in two datagrams, with bounded out-of-order reassembly. A signed
ephemeral X25519/HKDF handshake derives pairwise directional keys and an
admission-bound channel binding; six focused tests and the full workspace suite
pass. The version-2 evidence journal now syncs each verified signed handshake
offer before returning its channel response, restores bounded replay protection,
and rejects a rolled-back file when given an externally retained receipt. Live
peer transport, independent receipt retention, retransmission and NAT traversal
remain open.

The Unreal wallet source can prepare allowlisted native transactions, verify a
wallet signature through the native Connect bridge, submit a signed Norito
transaction to an explicitly configured isolated loopback Torii, and reconcile
its exact hash against ledger-state status. HTTP acceptance is not treated as
finality, and ambiguous submissions are never retried. Static C ABI checking
passes; an Unreal editor build, live pairing, submission and recovery run remain
outstanding. Shipping builds keep submission disabled.
The Iroha JavaScript native addon now builds and publishes with the project-specific
Xcode 26.1.1 linker; 29 focused allocation, equipment, resource and racing SDK
tests pass. This does not exercise Unreal or a live validator network.
The focused native equipment integration suite also passes all five tests,
including rejection of a snapshot missing authoritative custody maps. A broad
`iroha_core --lib` test build remains blocked by unrelated Kagemusha and
consensus test-fixture API errors; the focused result does not qualify the node.

A research adapter has also produced and independently verified a native STARK
for one fixed public damage/parry transition, rejecting seven tampering cases.
Measured generation was 522,431 ms including self-verification, with
584,663,040 bytes peak process RSS. This is a narrow proof milestone; it does
not establish kill correctness, match settlement, or the full-size resource
target. See [native integration](iroha-integration.md) for exact scope and evidence.
The compiled monolithic hit layout independently fails the current 4 MiB proof
limit before proof generation: canonical trace openings alone require about
43 MB at two players/three walls and 126 MB at twelve players/four walls.
[A narrower one-axis geometry relation](iroha-integration.md#measured-native-proof-research)
has generated a 3,847,520-byte native proof below that cap, and an independent
saved-proof verifier accepted it and rejected eleven changes. The original
combined run remains marked invalid because its negative fixture used an
out-of-range Boolean; a corrected full reprove has not run. This proves neither
a complete 3D hit nor a kill or settlement.
[Proof feasibility](proof/arena-feasibility.md) records the measurements and
the staged-composition requirement. This is a failed gate for that layout, not
a reduction of the agreed player count or proof coverage.

## Workstreams

- Deterministic Rust combat/economics, replay, P2P evidence and Unreal C ABI.
- UE 5.8.2 offline playable game, original assets and campaign production.
- Generic native Iroha admission, proof-authenticated allocations, equipment and Connect.
- Installed toolchains, packaged builds, measured performance and qualification.

Iroha changes are isolated in `../iroha-arena`, branch
`codex/arena-native-games`; the existing Iroha checkout is not modified.

## Release gates

1. Reproducible UE 5.8.2 Windows and macOS builds.
2. Deterministic simulation parity, source-reviewed complete FPS execution AIR,
   and actual proof generation/verification for all financially relevant rules.
3. Real four-validator test-XOR admission/dispute/settlement and NFT market runs.
4. Native Connect exact-action signing, verified results and finality recovery.
5. Full content, asset licensing, playtesting, accessibility and frame-time checks.
6. Full-size proof <=30 minutes and <=96 GiB on the M1 Ultra reference host.

Live funding and trading remain disabled until their actual qualification gates
pass. A replay hash, a signed checkpoint, a unit test or a kill event is not a
cryptographic execution proof. No production network or asset is guessed.
