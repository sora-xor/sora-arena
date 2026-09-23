# First-release implementation record

The active goal is the complete approved SORA Arena release. This is a progress
record, not a claim that the release is complete. Backward compatibility,
legacy formats, aliases, and fallback decoders are prohibited.

Japanese is the primary language for all dialogue and player-facing interfaces.
English subtitles are on by default. Localization is part of campaign production,
including subtitle timing, speaker identification, readable Japanese fonts and
controller-readable menus. The offline catalog now contains 25 timed bilingual
dialogue cues across eight chapters, shown during active gameplay; no voice acting
is recorded, and timing/readability still need Unreal play verification.
The HUD gives Japanese and English campaign subtitles, speaker names and notices
a minimum text size at 720p and above; content and font-width checks pass, but
the UE 5.8.2 visual and controller readability pass is still open.
Local control preferences now save inverted look, stick dead zones, look
sensitivity and whitelisted combat-action remaps separately from campaign
checkpoints. Wallet and menu bindings remain fixed. The control UI and actual
Windows/macOS controller verification are still open.

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
has not run that fixture. A pinned Windows GNU cross-build now produces a PE
x86-64 kernel DLL with all fifteen header exports and matching sizes/alignments
for eleven C ABI structs; it cannot establish Windows runtime parity. Actual
UE compilation and runtime testing are still
required before claiming the Unreal integration works. A separate headless test
runs a twelve-player idle Control lobby for the full 36,000-tick ten-minute clock,
checks deterministic terminal state and XOR conservation; it does not measure
networking, combat load, rendering, or proving.
A separate release-mode 12-player Control bot-input diagnostic reached its
score terminal at tick 19,565 with the same state hash on two runs
(`0dda20c238c44564fc4e9d2e34db311e10c751c416821a254454126df0d20345`);
12,000 initial atomic units remained conserved as 8,900 reserve plus 3,100
earned credits. This is a headless reference workload, not a network,
proof, rendering or human balance benchmark.
The offline campaign now has 24 authored Japanese production-site tasks with
English subtitle text. Each task has a combat threshold and earlier-site
requirements; prototype props vary by task type and change appearance on
activation. The first dojo encounter uses nonlethal wooden-sword sparring
rather than pre-invasion alien enemies. It persists defeated opponents,
restored sites, and exit completion to a local SaveGame checkpoint, rejecting
inconsistent site progress on load. Round resets now destroy live explosive
shells before restoring an encounter, so a previous attempt cannot damage new
opponents or advance their saved kill count. This still needs an editor build and an
in-game save/reload test; the shared encounter layouts do not meet the
six-to-eight-hour campaign target.
The final chapter now reserves its eighteenth opponent for a distinct alien
collector boss with locked-aim cyan beam and amber cleave warnings, recovery,
bilingual HUD/dialogue and a local checkpoint that respawns the boss at full
health after seventeen guards. The prototype save schema advances to 4 so a
pre-boss checkpoint cannot skip the encounter; no compatibility decoder is
included. Content validation passes 25 timed bilingual cues, but UE compilation,
readability, combat balance and save recovery still require an in-engine run.
The campaign presentation and playable protagonist remain the Nyaagyu Samurai;
the six-class selector is available in offline arena practice. This source
behavior still needs an Unreal menu and save/reload check.
Six original Edo/alien environment props now have editable Blender source,
FBX exports, metric collision/bounds checks, and campaign placement source.
The Lantern Ward debt terminal has a retained flat blockout and a licensed CC0
PBR material comparison; its geometry still reads as a prototype. Blender
review renders and import manifests do not establish in-engine appearance; the
UE 5.8.2 import and visual pass remain open.
An original irrigation sluice now adds a hand-cranked timber/stone gate and
alien meter to the agricultural liberation chapter's Estate sites. Its editable
Blender source, FBX, collision-box round trip, material provenance and hashes
pass local checks; it is decorative campaign geometry pending the same UE pass.
An original 319 × 195 × 226 cm Silk Foundry loom with 268 editable source parts,
indigo textile and an alien levy meter is placed beside the foundry station.
Its FBX has one 18,376-triangle render mesh and four UCX boxes; Blender
round-trip, hashes, license checks, and static import validation pass. Existing
combat collision remains unchanged. Unreal import, material translation, visual
quality, and frame rate have not been measured.
The standard Arc carbine (weapon ID 1) now selects an original Edo/sci-fi
hero mesh in the first-person presentation path. Its 84-part editable Blender
source and 12,532-triangle UV-mapped FBX pass material/license, hash, metric
bounds and Blender round-trip checks; the muzzle faces local +X from a
receiver-centered origin. The current 0.75 weapon-root scale is an initial
placement only. Unreal import, paw grip, materials, visual quality and combat
frame time still need an engine run.
The Nyaagyu hero now has an editable 1.849 m Blender static-character
blockout with 293 parts, 51,463 source triangles and an exact SVG-derived
SORA chest mark. Its FBX round-trip and import-source checks pass, but the
render remains stylized; it has no rig, animation, groom or runtime character
wiring. Its editor import targets `/Game/ArtReview/Characters`, outside the
always-cooked runtime asset folder. A separate generated photoreal concept
image provides an art-direction target for fur, cloth, armor and lighting.
It is a 2D reference, not a game mesh or evidence of in-engine visual quality.

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
advanced the identity to `sora-arena-first-release-4`. A subsequent attribution
correction makes self-inflicted explosive deaths reward no opponent even after
recent qualifying enemy damage; this advances the rules identity to
`sora-arena-first-release-5`. A wall-surface blast correction now lets a
grenade hitting a closed collision face damage a target on the impact side,
while preserving far-side occlusion; its fired-projectile regression checks an
exact 100-unit XOR transfer. This advances the provisional identity to
`sora-arena-first-release-6`. Native presentation ABI
3 exposes charge progress to a Japanese HUD bar and world-pawn weapon pose;
opponent readability has not been playtested. The deliberately re-recorded
ABI 3 macOS fixture retains identical controls, participant loadouts, map
geometry and input encoding. Its state/presentation expectations change in all
73 cases, while event streams change only for four Kanabo loadout cases. The
rebuilt library passes 73 cases / 44,100 ticks, eleven negative guards, and
72 native practice scenarios / 86,400 replayed ticks. The full locked offline
Rust suite, format checking, and strict all-targets Clippy pass.
The version-6 fixture refresh changes state hashes and streams for the rules
identity; its event and presentation streams are unchanged from version 5.
These deterministic checks are not a human balance playtest. The separate
campaign prototype catalog still differs from the Rust multiplayer catalog;
full gameplay balance, presentation and proof coverage remain open.
The headless `arena-cli balance` diagnostic now measures all 18 weapons against
one stationary 125-HP target through the real kernel; the six standard ranged
weapons span 1.017–1.217 seconds in a clear lane. It does not model opposing
movement, defense, cover, latency, or visual readability.

Local rollback replays only complete signed commitment/reveal batches into the
confirmed world. Speculative state is isolated, capped at 120 ticks, and discarded
on disconnect. A durable local journal preserves certified pending commitments,
individual valid reveals and signed checkpoints across restart, then replays the
kernel against the caller's exact admission. Recovery rejects damaged records,
forged signatures and rollback behind a caller-supplied trusted receipt. Native
consensus deadlines and forced resolution, production transport and complete FPS AIR
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
and rejects a rolled-back file when given an externally retained receipt. An
[offline loopback UDP research transport](p2p-localhost.md) now exchanges real
encrypted packets between two pre-admitted peers. Focused tests cover a
certificate/two-reveal exchange, loss with byte-identical retransmission,
reordered and duplicate twelve-slot fragments, persistence failure, and
rejection of bonded admission.
The loopback transport now also has bounded authenticated ACK/retry: it sends
the same sealed fragments at most four times, ACKs only durably journaled
evidence, re-ACKs authenticated duplicate fragments without redelivery, and
queues incoming evidence during an ACK wait. Drop, reorder, forged ACK, retry
exhaustion and fresh-key restart tests pass. A full local receive queue now
authenticates and re-ACKs only previously journaled replays; new evidence is
refused before state mutation or ACK, then accepted when capacity returns.
An eight-batch, 16-tick two-peer Arc-carbine diagnostic now checks identical
accepted combat hashes/history roots against independent `World` replay and
rejects a tampered or duplicate reveal. Focused regressions and the arena-core
suite pass. It remains a zero-bond localhost
research path without production NAT/relay transport or settlement authority.

The Unreal wallet source can prepare allowlisted native transactions, verify a
wallet signature through the native Connect bridge, submit a signed Norito
transaction to an explicitly configured isolated loopback Torii, and reconcile
its exact hash against ledger-state status. HTTP acceptance is not treated as
finality, and ambiguous submissions are never retried. An identity-only
recovery record is synced before POST; after restart it permits only exact-hash
reconciliation under the same loopback network configuration. The portable
C++17 codec passes 23 checks. An Unreal editor build, crash/restart, live
pairing, submission and recovery run remain outstanding. Shipping builds keep
both signing and submission of allowlisted game/NFT transactions disabled.
Research signing requires an explicit isolated loopback Torii and exact network
match before any wallet request, since signed bytes could be submitted elsewhere.
The menu now presents the existing Japanese transaction state with an English
status explanation, without displaying raw inspection JSON. Exact typed
join, bond and NFT purchase terms still need a game-facing review flow: the
current native inspection has transaction fields, but the game lacks a
verified session/offer snapshot and a separate pre-sign confirmation. See
[Connect review gap](connect.md#exact-game-facing-review-gap).
Join and NFT purchase signing now fail closed in the game before a wallet
request until that review exists. A non-authorizing typed Join inspector is
implemented in the native bridge and its two focused Rust tests pass. It
is now callable read-only from Unreal for a paired account/network, with the
typed payload hash cross-checked against the general scaffold inspection and
`authorization_ready=false` required. No UI treats that JSON as a qualified
term sheet, and it cannot lift the Join/Buy signing gate. It
remains uncommitted under Iroha's signed-commit rule. A release-profile local
research bridge containing this inspector is staged on macOS and passed native
smoke checks; it cannot substitute for the missing
authenticated session quote. Open and payout-claim scaffolds retain their
existing test-network behavior.
The Iroha JavaScript native addon now builds and publishes with the project-specific
Xcode 26.1.1 linker; 29 focused allocation, equipment, resource and racing SDK
tests pass. This does not exercise Unreal or a live validator network.
The focused native equipment integration suite also passes all five tests,
including rejection of a snapshot missing authoritative custody maps. A broad
`iroha_core --lib` test build remains blocked by unrelated Kagemusha and
consensus test-fixture API errors; the focused result does not qualify the node.
The generic native genesis API now accepts the immutable admission body and
validates it before Race root derivation; one focused integration test passes
and rejects malformed version, skin, duplicate input key, and missing slot.
This Iroha work is uncommitted pending the repository's signed-commit policy.

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
An unregistered, unfunded native Arena movement research relation now proves
four restricted position transitions across two players and two 60 Hz ticks.
It binds an exact zero-bond admission, peer-signed commitment/reveal batch,
map/rules identity and the accepted inputs, with both FFA team/class/weapon
fields zero. It matches the current
`sora-arena-first-release-6` kernel on that slice. Its 81-column, 90-constraint
preflight capped encoded proof size at 1,315,072 bytes. A fresh M1 Ultra proof
was 1,192,288 bytes (SHA-256
`2456130dad1254c76e73665c406a5bff5b58d46b884c3b59e894bb0582b2d0b5`),
generated in 121.994 seconds at 252,723,200 bytes peak RSS;
separate-process verification took 12.260 seconds and rejected altered
position, input, session and proof bytes. The batch is peer-accepted rather
than ledger-selected, and the relation proves no hits, deaths or payouts;
it cannot register or settle an Arena match.
A second unregistered, zero-bond native research proof covers one fixed
genesis-derived Arc carbine hit in a canonical, peer-signed two-tick,
three-player FFA batch. Deterministic host checks fix the exact scene,
accepted controls, target reduction, 22-damage row and projected state;
native AIR proves 30 wall/body slab fractions and the damage arithmetic.
Its 658-column, 1,414-constraint preflight caps wire size at 2,607,552
bytes. The saved proof is 2,471,808 bytes (SHA-256
`f7e626081cf1938d388876129ab591681029835756be7a17041a76523a8a76cd`),
generated in 134.148 seconds at 664,354,816 bytes peak process RSS; a
fresh process verified it in 17.426 seconds and rejected statement/proof
mutations. This is a fixed-scene arithmetic result, not a general
movement/hit-to-state proof, kill proof or XOR settlement relation.
A third unregistered, unfunded native research proof covers one fixed
25-tick, three-player Arc-carbine kill. Its projected combat/account rows
constrain six hits, 125→0 health, a 100-unit fixed loss from a 1,000-unit
victim bond, and 20/80 FFA assist/killer credits; adjacent tick rows and two
selected wall/body rays are also constrained. The saved 2,624,704-byte STARK
(SHA-256 `577d706dc0d0d2396c412b817c490c08bab4bef655b0d3bdc65e2c8b84562e49`)
was proved in 138.033 seconds with 706,609,152 bytes peak RSS and verified
in a fresh process in 17.821 seconds. Focused mutation checks rejected
changed controls, geometry, combat state, awards, row links and proof bytes.
The fixture hardcodes one scene and uses a 25-tick research batch, not the
production two-tick P2P protocol; it cannot authorize any chain payout or
establish full-match proof feasibility. See
[the native research record](iroha-integration.md#measured-native-proof-research).
An unregistered Iroha research preflight separately measured an 18,000-batch,
twelve-slot history as 6,030,008 canonical Norito bytes, exceeding the current
4 MiB proof envelope before the rest of a complete combat witness. Repeated
whole-history cloning and hashing under fixed gas quotes is another unresolved
capacity gate. The native 4,096-batch cap and unfunded Arena status remain in
place; the research validator does not authenticate control inputs or kills.

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
