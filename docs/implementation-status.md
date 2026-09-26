# First-release implementation record

The active goal is the complete approved SORA Arena release. This is a progress
record, not a claim that the release is complete. Backward compatibility,
legacy formats, aliases, and fallback decoders are prohibited.

Japanese is the primary language for all dialogue and player-facing interfaces.
English subtitles are on by default. Localization is part of campaign production,
including subtitle timing, speaker identification, readable Japanese fonts and
controller-readable menus. The offline catalog now contains 25 timed bilingual
dialogue cues across eight chapters, shown during active gameplay; no voice acting
is recorded, and timing/readability still need Unreal play verification. A native
Japanese Game localization resource passed `SoraArena.Localization.NativeJapanese`
in a UE 5.8.3 `-game` run: Unreal loaded its metadata/resource, selected `ja`
without the previous English fallback, resolved the Japanese menu title, and
found the separately authored English subtitle. A separately staged 5.8.3 Mac
app contains those resources, passes a headless startup smoke, and passes the
same Japanese automation inside the package with
`native=ja active=ja title=猫柳生 english_subtitle=present`. A release run on the
pinned UE 5.8.3 build and a packaged Japanese UI/subtitle visual readability
check are still required.
The HUD gives Japanese and English campaign subtitles, speaker names and notices
a minimum text size at 720p and above; content and font-width checks pass, but
the UE 5.8.3 visual and controller readability pass is still open.
Local control preferences now save inverted look, stick dead zones, look
sensitivity and whitelisted combat-action remaps separately from campaign
checkpoints. Wallet and menu bindings remain fixed. The control UI and actual
Windows/macOS controller verification are still open.

## Milestones and current evidence

| Milestone | Current state | Completion evidence still required |
| --- | --- | --- |
| Foundation | Active: deterministic Rust kernel and C ABI; locked workspace tests and strict Clippy pass; native generic admission, catalog and Connect changes in isolated Iroha worktree | Release UE 5.8.3 build, real wallet pairing, complete two-player proof-to-settlement path |
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
for eleven C ABI structs; it cannot establish Windows runtime parity. The Mac
editor target compiled in an isolated UE **5.8.3** diagnostic worktree (installed
changelist **58210709**). That Launcher build became the release engine pin on
2026-09-25 after UE 5.8.2 could no longer be installed ([toolchain](toolchain.md));
these earlier interim runs are not release qualification, and actual Unreal
gameplay integration remains unverified.
The same isolated 5.8.3 checkout loaded `/Engine/Maps/Entry` with
`SoraGameMode` in a headless Mac game startup and exited cleanly. This is a
startup smoke check, not a played campaign or rendered performance test.
With Apple's separate Metal Toolchain installed, a Mac UE 5.8.3 diagnostic
cook exited successfully. The latest post-terrain run reported 671 cooked
packages, and UAT staged and archived the updated game target. The 1.0 GiB
Mac app contains all 32 authored estate terrain tile packages in IoStore,
has a valid local code signature, and passed an exit-0 headless packaged
startup. This is not a release cook, distribution signature, played
session, or frame-rate test.
A separate headless test
runs a twelve-player idle Control lobby for the full 36,000-tick ten-minute clock,
checks deterministic terminal state and XOR conservation; it does not measure
networking, combat load, rendering, or proving.
A separate release-mode 12-player Control bot-input diagnostic reached its
score terminal at tick 19,565 with the same state hash on two runs
(`0dda20c238c44564fc4e9d2e34db311e10c751c416821a254454126df0d20345`);
12,000 initial atomic units remained conserved as 8,900 reserve plus 3,100
earned credits. This is a headless reference workload, not a network,
proof, rendering or human balance benchmark.
An eight-player local kernel fixture now executes 7,200 fixed-input ticks,
with every state hash matching a second run and an encoded-input replay. A
separate opt-in eight-socket signed loopback UDP fixture ran 3,600 two-tick
batches, 60 unanimous checkpoint rounds and 227,220 authenticated packet
deliveries in 90.92 seconds on the M1 Ultra; all eight peers matched the
pinned kernel hashes. This is zero-bond research with fixture-held keys and
lossless local transport, not a production 4v4 P2P match, execution proof or
settlement. See [the loopback research note](proof/eight-peer-loopback-research.md).
The offline campaign now has 24 authored Japanese production-site tasks with
English subtitle text. Each task has a combat threshold and earlier-site
requirements; prototype props vary by task type and change appearance on
activation. The first dojo encounter uses nonlethal wooden-sword sparring
rather than pre-invasion alien enemies. Nyaagyushinkageryuu apprenticeship
now requires a held stance, front-facing guard, fresh timed parry against a
telegraphed pupil swing, and full wooden-sword recovery before sparring damage
can score. Its prefix-complete lesson mask is validated on reload. The campaign
also persists defeated opponents,
restored sites, and exit completion to a local SaveGame checkpoint, rejecting
inconsistent site progress on load. Round resets now destroy live explosive
shells before restoring an encounter, so a previous attempt cannot damage new
opponents or advance their saved kill count. The `SoraArena.Campaign.SaveRoundTrip`
automation passed inside UE 5.8.3, covering `USoraSaveGame` memory serialization
and restoration of all checkpoint fields. `SoraArena.Campaign.DiskSaveRecovery`
also passed four on-disk save/load cases and removed its temporary slot. World
teardown and an in-game checkpoint recovery test remain open; the shared
encounter layouts do not meet the
six-to-eight-hour campaign target.
The [host campaign acceptance driver](campaign/offline-acceptance.md) exercises
the same extracted GameMode progression rules across all eight catalog
chapters, checkpoint values, the final boss gate and final liberation. It
checks all 25 Japanese dialogue cues have English counterparts. It does not
test Unreal save slots, played combat, subtitle rendering or campaign length.
The final chapter now reserves its eighteenth opponent for a distinct alien
collector boss with locked-aim cyan beam and amber cleave warnings, recovery,
bilingual HUD/dialogue and a local checkpoint that respawns the boss at full
health after seventeen guards. The prototype save schema advances to 5 so a
pre-boss checkpoint cannot skip the encounter; no compatibility decoder is
included. Content validation passes 25 timed bilingual cues. The interim
UE 5.8.3 editor compile and SaveGame automation do not verify subtitle
readability, combat balance, played-world recovery or a release build on the
pinned 5.8.3 engine.
The campaign presentation and playable protagonist remain the Nyaagyu Samurai;
the six-class selector is available in offline arena practice. This source
behavior still needs an Unreal menu and save/reload check.
Six original Edo/alien environment props now have editable Blender source,
FBX exports, metric collision/bounds checks, and campaign placement source.
The Lantern Ward debt terminal has a retained flat blockout and a licensed CC0
PBR material comparison; its geometry still reads as a prototype. Blender
review renders and import manifests do not establish in-engine appearance. An
isolated UE 5.8.3 editor diagnostic imported 26 character/weapon/horse meshes,
six environment props, 32 modular estate terrain tiles, the SORA insignia and
the pinned CC0 palette. Its follow-up validator loaded 92 expected packages
with their declared Unreal types, including the high-tier Nanite-enabled and
Mac-tier conventional terrain assets. The
release import on the pinned UE 5.8.3 engine, in-game visual pass, and measured
frame rate remain open.
An original irrigation sluice now adds a hand-cranked timber/stone gate and
alien meter to the agricultural liberation chapter's Estate sites. Its editable
Blender source, FBX, collision-box round trip, material provenance and hashes
pass local checks; it is decorative campaign geometry. Its Unreal import type
passes in the 5.8.3 diagnostic editor; in-world appearance still needs review.
An original 319 × 195 × 226 cm Silk Foundry loom with 268 editable source parts,
indigo textile and an alien levy meter is placed beside the foundry station.
Its FBX has one 18,376-triangle render mesh and four UCX boxes; Blender
round-trip, hashes, license checks, and static import validation pass. Existing
combat collision remains unchanged. Unreal 5.8.3 imported its mesh, but material
translation, visual quality, and frame rate have not been measured.
The standard Arc carbine (weapon ID 1) now selects an original Edo/sci-fi
hero mesh in the first-person presentation path. Its 84-part editable Blender
source and 12,292-triangle UV-mapped FBX pass material/license, hash, metric
bounds and Blender round-trip checks; the muzzle faces local +X from a
receiver-centered origin. The current 0.75 weapon-root scale is an initial
placement only. Unreal 5.8.3 imports it, but paw grip, materials, visual
quality and combat frame time still need an in-game check.
The Nyaakoto art-review hero now has an editable 2.195 m Blender static-character
blockout with 351 parts, 56,091 source triangles, yumi and arrows, katana, and
four exact SVG-derived SORA kamon placements. Its FBX round-trip and Unreal
5.8.3 import checks pass, but the
render remains stylized; it has no rig, animation, groom or runtime character
wiring. Its editor import targets `/Game/ArtReview/Characters`, outside the
always-cooked runtime asset folder. A separate generated photoreal concept
image provides an art-direction target for fur, cloth, armor and lighting.
It is a 2D reference, not a game mesh or evidence of in-engine visual quality.
An original 1.821 m horse and Edo tack study has paired broad iron abumi,
tazuna rein grips, kura saddle and exact SORA kamon. Its 135-part, 69,392-triangle
unrigged source passed Blender FBX round-trip and UE 5.8.3 static import. It is
an art-review model, not a mounted or animated runtime character.
Nyaagyu Estate has 16 high-density tiles and 16 conventional Mac tiles with
seam-matched local geometry, exact placement centers, and pinned CC0 soil/stone
textures. The campaign runtime chooses the Mac tier on M1 and the high tier
otherwise, explicitly enables distance-field lighting/dynamic indirect light
and ray-tracing visibility, and leaves the flat gameplay collision unchanged.
The Windows-tier import builds Nanite data; the Mac tier does not. This is a
regular static-mesh terrain presentation path. Epic's experimental Mesh Terrain
plugin, World Partition conversion, compiled runtime sections and the special
Mesh Partition Lumen-heightfield path have not yet been integrated or qualified.
The 5.8.3 import/cook/stage checks do not prove Lumen card/probe coverage,
photoreal appearance, Windows rendering, or 60 fps. See
[terrain source and integration record](mesh-terrain-nyaagyu.md).
The Estate campaign now replaces its ten pink-sphere tree prototypes with
separately authored 354k-triangle Nanite and 95k-triangle conventional tiers
of a CC0 scanned Poly Haven broadleaf tree, including masked leaves and PBR
maps. It replaces the visual building blockouts with a 74k-triangle Edo-inspired
dojo containing a tiled roof, veranda, shoji, and the exact supplied SORA
kamon; gameplay collision remains on the prior simple proxies. The skinned
Nyaakoto runtime cat has a 20-bone rig, 23 fixed material slots, authored
fur/cloth/lacquer PBR maps, yumi, quiver and katana. The roof has a separate
4K CC0 grey ceramic PBR scan applied to the original curved geometry; its
photographed overlap pattern still needs a period-art review. Source validators
and the 5.8.3 editor import validator pass for all 154 expected packages and
exact character and roof material bindings. Blender reviews still show a
stylized character. Two authored distance LODs reduce Nyaakoto from 136,701
runtime vertices to 53,302 and 18,546 in the 5.8.3 editor. Editor and packaged
Mac automation both load the skeletal asset with three LODs and 23 material
slots. Performance still needs measurement. This asset work is not a photoreal
AAA qualification; an in-game
visual pass and
measured Windows/Mac frame times remain required.
An additional unrigged Nyaagyu bust study has editable Blender source and a
102,071-triangle FBX with 32,155 fur-card triangles. Its Blender round-trip,
source hashes, bounds and material-slot checks pass. Its render is still visibly
stylized and it is neither runtime-imported nor a photoreal shipping character;
rigging, production materials, LODs, and UE 5.8 visual/performance checks remain.

The current Estate art pass adds a distinct provision storehouse with individually
modeled roof tiles, measured CC0 plaster/wood/stone surfaces, and three CC0 pine
sapling variants with high-density Windows and conventional Mac tiers. The
first-person katana now has authored UVs and six 2K PBR map sets; its saya is a
separate body-mounted mesh. Independent source validators pass. In the isolated
5.8.3 worktree, after both original-asset and palette import passes, the editor
validator loads **207** expected packages and verifies the new material bindings.
The latest Mac diagnostic cook processed **795** packages; its packaged
Nyaakoto LOD automation test passed. The earlier 154-package/735-package
figures above document the preceding art revision. Source previews remain below
the user's AAA photoreal target. The runtime scene, close-up character shading,
animation, lighting and measured frame time need direct in-game review.

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
integration are still required; no peer timeout can settle funds. Up to 16
certified frontiers can now await openings at once, and the protocol-level
dropout policy forfeits a withheld opening only through a consensus deadline
resolution ([pipelined evidence](p2p-pipeline.md)). See
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
pass. The version-3 evidence journal now syncs each verified signed handshake
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
An N-peer research mesh (`mesh_transport`, `arena peer`) now runs a
two-minute 4v4 match as eight OS processes on loopback. It passes cleanly,
with one peer killed and restarted from its journal, and under injected
datagram damage; every process reaches the pinned final state
([measurements](p2p-localhost.md#n-peer-mesh-transport)). A two-minute 6v6
match as twelve processes also agrees on the final state, but on one machine
it does not hold 60 Hz presentation: 1.9–5.3% of ticks were late in two runs.
When a peer drops out, the survivors stop combat with a journaled interrupt,
share their certificates and last checkpoint, and finish once the openings
are available. A frontier only the dropped peer can open stays pending for a
consensus deadline, which is not implemented. The mesh has the same
zero-bond, no-NAT, no-settlement limits.

The Unreal wallet source can prepare allowlisted native transactions, verify a
wallet signature through the native Connect bridge, submit a signed Norito
transaction to an explicitly configured isolated loopback Torii, and reconcile
its exact hash against ledger-state status. HTTP acceptance is not treated as
finality, and ambiguous submissions are never retried. An identity-only
recovery record is synced before POST; after restart it permits only exact-hash
reconciliation under the same loopback network configuration. The portable
C++17 codec passes 23 checks. The Mac Unreal editor target compiled in the
interim UE 5.8.3 worktree and `SoraArena.Connect.LaunchBindings` passed there.
Crash/restart, live pairing, submission and recovery runs remain outstanding. Shipping builds keep
both signing and submission of allowlisted game/NFT transactions disabled.
Research signing requires an explicit isolated loopback Torii and exact network
match before any wallet request, since signed bytes could be submitted elsewhere.
The menu presents the existing Japanese transaction state with an English
status explanation. A bounded read-only Join scaffold preview displays
requested deposit/asset, up to one NFT reservation including its metadata
hash, role hash and return policy, and two fee caps, marked unverified and
partial in Japanese with an English explanation. Missing authenticated
death-loss and maximum-loss terms are explicitly unavailable; no menu action
creates a Join scaffold yet. Exact typed
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
An additional portable C++17 Join/Buy preflight now compares exact supplied
session, bond, equipment, offer, custody and expiry terms, with Japanese-first
status text and English subtitles. Its Mac host driver and Windows compiler
syntax check pass. It enforces B for ordinary equipment, 2B for a cataloged
special without its NFT, or B with one exact owned and reservable cataloged
NFT, plus exact ten-way death losses. This is deliberately non-authorizing:
no authenticated ledger snapshot or final fee quote is wired to it, and the
Join/Buy wallet signing block remains in place.

The Windows GNU Connect bridge also passed a source-sealed static cross-build:
its PE x86-64 DLL has 175 exports exactly matching the native C header and
the game's 26 Windows C ABI declarations compile. The staged DLL and source
fingerprints are recorded in [the Connect build note](connect.md). Windows
loading, wallet pairing, transactions and MSVC packaging remain untested.
The Iroha JavaScript native addon now builds and publishes with the project-specific
Xcode 26.1.1 linker; 29 focused allocation, equipment, resource and racing SDK
tests pass. This does not exercise Unreal or a live validator network.
The focused native equipment integration suite also passes all five tests,
including rejection of a snapshot missing authoritative custody maps. A broad
`iroha_core --lib` test build still has 257 compiler errors after bounded
Kagemusha fixture repairs, predominantly stale test-fixture API usage; the
focused result does not qualify the node. A data-model `--lib` test build also
stops on 60 unrelated stale Kagemusha and staking fixture errors.
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
An independent host-side audit now reconstructs the same 25 controls from
thirteen signed two-tick P2P-shaped batches plus one exact idle pad frame. Its
two focused tests pass transcript chaining, input/kill-row agreement and
adversarial mutations. The saved STARK does not bind that transcript, and
Iroha has not selected it as canonical session history.
An independent `arena-core` regression now replays the exact 26-tick extension
of that kill scene through `World::step`, pinning 27 state boundaries, 78 encoded
controls across 13 two-tick batches, events, final allocations and a source
fingerprint. Its focused test passes. This catches game-kernel drift in the
fixed research scene; the fingerprint is not a cryptographic binding in the
Iroha proof or a general live-match execution relation. See the
[kernel parity fixture](proof/arena-kill-history-v2-kernel-parity.md).
The corresponding unregistered Iroha 26-tick research relation now binds all
13 signed two-tick batches in one public statement and proves the fixed
projected death, 100-unit loss, 20/80 credits and final idle-tick transition.
Its 2,772,064-byte STARK passed fresh-process verification and four saved-proof
tamper checks; the conservative complete envelope bound is 2,946,649 bytes,
below 4 MiB. Proving took 169.685 seconds and 768,720,896 bytes peak RSS on
the M1 Ultra. This manually fixed scene is not a registered `ArenaV1` profile,
ledger-selected history, general live-kernel relation, or settlement authority.
The next selected-history gate is blocked at native routing: Iroha's closed
registry currently admits only the racing relation, so its Open, Start and
Reveal instructions cannot create a genuine ledger-retained session for this
unregistered Arena proof. The research fixture also fixes all batch epochs at
zero while native forced batches advance epochs. A synthetic test-only session
would not meet the consensus-evidence requirement; source-derived `ArenaV1`,
canonical epoch mapping and restoration validation remain required.
The existing RaceV1 profile ID hashes the entire native
`execution_proofs.rs` source file. A proposed enum addition would change that
historical proof identity, so it was reverted. Staged negative registry,
instruction and verifier-dispatch tests keep the exact Arena research ID
unregistered and unfunded while a separate, reviewed profile-identity strategy
is developed; those tests have not executed because the broad data-model test
target still fails to compile on unrelated fixtures.

An unfunded, unregistered translation test now verifies all thirteen signed
two-tick peer batches and maps them to native forced-batch epochs 0–12,
deriving separate P2P, input-transcript, and conditional dispute roots. It
rejects altered epochs, order, frames, slots, and hash-domain substitution.
Its checkpoint is supplied by the caller, not selected by consensus, so this
does not relax the native routing or settlement gate.

An unregistered Iroha research preflight separately measured an 18,000-batch,
twelve-slot history as 6,030,008 canonical Norito bytes, exceeding the current
4 MiB proof envelope before the rest of a complete combat witness. Repeated
whole-history cloning and hashing under fixed gas quotes is another unresolved
capacity gate. The native 4,096-batch cap and unfunded Arena status remain in
place; the research validator does not authenticate control inputs or kills.

## 2026-09-24 visual-art gate

The earlier asset counts above describe historical source passes, not the
current quality level. The current estate source includes a 58-module perimeter
wall, a 425,984-triangle high-density terrain tier and a 26,624-triangle Mac
tier with a pinned CC0 Grey Stone Path scan, a connected-head Nyaakoto
iteration, and an isolated 28-bone horse walk study. The latter is not yet a
runtime riding system. The Mac diagnostic on UE 5.8.3 loaded 258 generated
packages and passed build, cook and stage; a material graph error initially
produced checkerboard terrain and black torii. A corrected graph and fail-closed
Mac shader-compile gate then passed another cook/stage, and the packaged game
captured [unedited estate, character and path views](visual-reviews/README.md)
with no material shader-map errors in the logs. These views still show repeated
road motifs, sparse scene dressing and visibly stylized cat anatomy. Neither
the current asset count nor the engine feature flags constitute AAA
photorealism. The release UE 5.8.3 build, Windows/Nanite, Lumen coverage, 60 fps, and
full-content release gates remain open.

The next Mac diagnostic loaded 276 expected generated packages, cooked 898
packages without reported warnings or errors, and staged an
`org.sora.soraarena` Development app. The Nyaakoto skeletal reimport retained
the authored vertex colors and three distance LODs; the repaired six-map
grey/white fur shader compiled on METAL_SM5. Its [packaged body and face
frames](visual-reviews/README.md) still fail the character art gate: the eyes,
ears, throat seam, armor and fur silhouette remain stylized. A separate
anatomical head variant also failed the profile review and was not integrated.
The gate's round tapered posts improved the entrance silhouette, while the
larger 4K path atlas reduced distant tiling but failed the close gameplay
view because distinct stones still repeat and detail softened. The atlas is
source-only; the main path binding and collision remain unchanged. The horse
anatomy and measured-tack study has editable source and texture maps but is
also source-only and still visibly stylized. No frame in this pass qualifies
AAA photorealism or the UE 5.8.3 release path.

The subsequent facial-anatomy V2 source study moved Nyaakoto's eyes, ear cups,
muzzle volumes and neck transition. Its Blender/FBX validator passes, but its
front/profile renders still have a toy-like dome, separate muzzle and flat ears;
it is explicitly excluded from runtime. A measured Edo horse-tack comparison
used a CC0 older horse model as visual reference only and improved the mane and
eye of the isolated source horse; hocks, fetlocks, hooves, groom and rider fit
remain below the historical and photoreal gates. No reference animal geometry
or textures were copied into the game.

A new [2.20 m yumi and ya source study](../Content/SourceArt/Weapons/NyaagyuYumi/README.md)
replaces the block-shape *authoring*
approach with an editable asymmetric laminated stave, horn nocks, modeled
leather and cord grip, arrow/fletching, and the exact user-supplied SORA crest.
It uses hash-pinned CC0 photographed bamboo and leather 2K albedo, normal and
ARM scans. Its Blender/FBX round trip passes for 60 mesh parts and preserves
the stave/grip UVs. The first-person runtime still uses the earlier prototype:
the study needs period-art review, a driven draw/string/arrow rig, correct paw
contact and a packaged UE 5.8.3 release visual pass. The source renders do not yet pass
the AAA photoreal gate.

A full water-court and bamboo/rill subset were modeled with editable geometry,
PBR source maps and conventional Mac/Nanite candidate exports. The isolated
5.8.3 package imported and cooked the subset, but the [fixed entrance and path
captures](visual-reviews/bamboo-rill/README.md) show that the proposed
placement is hidden by existing buildings and cover. It was removed from the
diagnostic world; no main-world placement occurred. Source geometry validation
passes, but the gameplay visual gate fails.

The later [Nyaakoto coat/head V3](../Content/SourceArt/Characters/NyaakotoCoatV3/README.md)
has an editable sculpt, unique-UV 2K PBR maps and authored directional fur.
Its fixed-view renders still have a rounded cranium, exposed mechanical-looking
eyes, flat ear presentation and a hard muzzle silhouette; it is source-only.
The [formed-dō armor study](../Content/SourceArt/Characters/NyaakotoDoStudy/README.md)
replaces rectangular chest plates with fitted curved bands, modeled odoshi and
kusazuri, plus project-owned lacquer albedo/normal/ORM maps. Its controlled
Blender comparison and FBX validation pass, but the plate wear and lacing are
too regular, carried weapon pieces intersect the shell, and the surrounding
body remains stylized. It is also source-only. Neither study is a photoreal
character upgrade or evidence of a shippable animated rig.

The [first-person paw/grip source study](../Content/SourceArt/Characters/NyaakotoFirstPersonPaws/README.md)
adds anatomically separate digits/pads, modeled kote plates, authored pad PBR
maps, and katana/yumi contact poses. Grip radii, UVs, source hashes and FBX
round trips pass. Its fixed first-person renders still read as smooth gloves
and simplified sleeves, without driven draw or sword animation, so runtime
hands and weapon bindings were not changed. A [free realistic-cat base survey](art-research/nyaakoto-realistic-cat-base-survey.md)
found no no-account model that met the photoreal hero and open-source licensing
gate; the strongest realistic quadruped candidate has account/restricted raw
asset terms and cannot simply replace the biped hero rig.

The [packaged Fern 02 A/B](visual-reviews/fern02/README.md) verified that the
licensed scan's masked fronds render through the full conventional Mac fallback
in UE 5.8.3. Its fixed entrance comparison shows only small patches around the
torii posts, and the close view exposes card-like clumps above flat ground.
The isolated importer and editable source are retained, but the tested eight
plants were not placed in the main WorldBuilder. They do not qualify the
Estate's scene composition or photorealism.

The [follow-up fern ground-transition package](visual-reviews/fern02-ground-transition/README.md)
also passed import, Mac cook and fixed-camera capture, but failed the visual
gate: the entrance camera barely sees it around the torii, while a close view
shows a bright hard-edged soil strip and crowded path. Its modeled roots,
stones, scanned ground and fern contacts remain source-only. Separate source
studies now test a full [integrated gravel-and-stone road](../Content/SourceArt/Environment/NyaagyuIntegratedRoji/README.md),
a [weathered kura frontage](../Content/SourceArt/Environment/NyaagyuKuraFront/README.md),
and [scan-backed gate footings](../Content/SourceArt/Environment/NyaagyuToriiFootStudy/README.md).
Their Blender and FBX validations establish editable geometry and texture
provenance, not in-game quality. The [packaged Kura facade review](visual-reviews/kura-front/README.md)
exposed a misplaced UV channel, which was fixed in the study; its corrected
wood grain is visible at close range, but the repetitive frontage still fails
the entrance composition gate. The [torii foot review](visual-reviews/torii-foot/README.md)
shows a more irregular stone outline with conspicuous green striping, so both
studies remain source-only. The existing Kura and Dojo facades were reoriented
toward the road in the main Estate without changing gameplay collision.

The original stone scan also repeated visibly across the road. An isolated
[UE 5.8.3 packaged A/B](visual-reviews/road-variation-study/README.md) at fixed
entrance and close cameras found that height-guided UV variation reduces that
repeat while retaining photographed color and terrain dampness. The material
was admitted as an incremental Estate-only visual improvement; the original
map mesh/collision remain intact. Eleven seconds of 1080p frame-counter
observation is not a combat benchmark, and the Estate still fails the AAA+
composition and hero-character art target. A separate editable
[bokuto form study](../Content/SourceArt/Weapons/DojoBokutoForm/README.md) now
tests a curved, faceted, blunt white-oak training sword with modern AJKF jodo
proportions and a leather guard. Blender/FBX orientation, UV, dimensions,
texture provenance and render checks pass. The later
[packaged UE 5.8.3 bokuto A/B](visual-reviews/dojo-bokuto-form/README.md)
confirms a better curve, blunt tip, guard and photographed grain from a
test-only side-on view. In the actual first-person pose, only a narrow pale
blade strip remains visible, with grip and guard offscreen. The current authored
weapon path also renders **no first-person paw**; its component count is zero.
The candidate remains source-only pending a fitted hand viewmodel, usable pose,
material calibration, animation and historical review.
The subsequent [two-paw bokutō viewmodel study](../Content/SourceArt/Characters/NyaakotoBokutoViewmodel/README.md)
has an editable 15-bone source rig, four separately posed digits per paw, UV0
and PBR bindings, and an exact SORA-kamon kote detail. Its paired normal-idle
Blender renders differ by **zero visible pixels** because both paws remain
outside the current first-person frustum. The detail camera shows a grasp but
the forms still look glove-like. It is not bound to the runtime. A measured
pose change and packaged Unreal A/B must come before any admission.
A [source-only pose probe](../Content/SourceArt/Characters/NyaakotoBokutoViewmodel/PoseProbe/README.md)
moving WeaponRoot from `(40,18,−18)` to `(40,8,−7)` cm makes 28,448 grip
pixels and 94,592 paw pixels visible in the fixed 70° Blender camera while
the tested 80-pixel reticle disc stays clear. The oversized glove-like forms,
different Unreal first-person projection and untested motion still block use.

An earlier [first-person bokken PBR A/B](visual-reviews/dojo-bokken/README.md)
used the same UE 5.8.3 Mac package and fixed camera. Its wood grain improved
some close detail, but the straight, bright blade still read as a baton; the
candidate failed the visual gate and the playable asset was left unchanged.
The new curved bokuto study is a separate geometry-and-scan experiment, not a
retroactive pass for that earlier material test.

The [raw Estate renderer diagnostic](render-qualification/estate-ue583-m1-20260924/README.md)
captured seven unedited 1280×720 entrance frames and original logs on the M1
Ultra software-Lumen path. Its Surface Cache view shows pink missing coverage
at visible upper roof/eave edges and high foliage/props. The Scene, card and
distance-field modes rendered, but the fixed close-foot view was unavailable,
so the evidence archive is explicitly incomplete. The two imported building
meshes each combine hundreds of parts and thin tile sheets; a diagnostic-only
card-count A/B was attempted before any source change to their modular
geometry. Both the initial duplicate and a [paired 12/32-card rebuild](render-qualification/estate-lumen-cards32-ue583-m1-20260924/PAIRED-REBUILD.md)
failed the geometry-equality gate: the persisted Dojo clones have 14,966
versus 14,884 LOD0 triangles and different bounds. No visual comparison or
runtime card-count change was made. A different isolation method or modular
roof/body geometry is needed before attributing the pink gaps to card count.
The independent [packaged Dojo frontage A/B](visual-reviews/dojo-frontage-yaw/README.md)
compared the current main visual yaw against a 180° flip at the same near
camera on both Estate rows. Current yaw shows the modeled shōji lattice and
steps; the flip exposes the plain rear plaster. Existing placement is correct,
so no production rotation change was made. Both views still expose repetitive
roof detailing and stylized materials.
The next source-art pass [split the Dojo into four FBX modules](../Content/SourceArt/Environment/NyaagyuDojo/LumenModules/README.md)
with exact pre-export triangle/material parity and a sub-2 µm FBX reimport
bound. This provides a candidate for a controlled roof/eaves Surface Cache
study; it has not been imported or evaluated in Unreal. A
[CC0 shōji-paper A/B](../Content/SourceArt/Environment/ShojiPaperArtReview/README.md)
failed at 1 m and 3 m because the fibers repeat conspicuously. A separate
[modeled concave/convex roof-bay study](../Content/SourceArt/Environment/NyaagyuKawaraBay/README.md)
adds individually overlapping ceramic forms and four fixed-camera material
renders. The latest variation raises the convex covers and authors a coherent
polished ibushi-inspired color/normal/ORM set, but its estimated reflectance and
regular course wear remain below the AAA+ art threshold. A separate
[modeled SORA relief cap](../Content/SourceArt/Environment/NyaagyuSoraEaveCapStudy/README.md)
passes source/FBX checks but does not yet fit the bay. A hash-verified
[isolated UE ArtReview import path](visual-reviews/kawara-bay/README.md)
passes static preflight; Unreal Lit/Lumen import was held when free disk fell
below the 30 GiB heavy-run gate. These source candidates do not change the playable Estate.
The current Estate does not pass a Lumen coverage gate, Windows Nanite coverage
is unmeasured, and these captures establish no AAA+ or frame-rate result.

A separate [Nyaakoto V4 head study](../Content/SourceArt/Characters/NyaakotoHeadV4/README.md)
adds an editable connected shell, eyelid and ear geometry, groom curves and
unique PBR maps. Its same-camera Blender front/profile/three-quarter views
still read as an oversized round skull with puffy muzzle, obvious ear-root
joins and an unfinished neck. It failed the photoreal face gate and was not
imported or bound to the playable character.
A [V5 anatomy correction](../Content/SourceArt/Characters/NyaakotoHeadV5/README.md)
passed editable-mesh/FBX checks but still fails the same-light front and
profile visual gate: cheek and brow volumes, bridge plane and ear-root seams
remain toy-like. It is also source-only. A newer
[photoreal four-view reference](../Content/SourceArt/Characters/Hero/Reference/Nyaakoto_PhotorealTurnaround_v2.png)
helps define coat and costume direction; it is a generated picture, not a
shippable mesh, historically verified weapon reference, or Unreal screenshot.

## Workstreams

- Deterministic Rust combat/economics, replay, P2P evidence and Unreal C ABI.
- UE 5.8.3 offline playable game, original assets and campaign production.
- Generic native Iroha admission, proof-authenticated allocations, equipment and Connect.
- Installed toolchains, packaged builds, measured performance and qualification.

Iroha changes are isolated in `../iroha-arena`, branch
`codex/arena-native-games`; the existing Iroha checkout is not modified.

## Release gates

1. Reproducible Windows and macOS builds on the pinned UE 5.8.3 Launcher build
   (changelist 58210709).
2. Deterministic simulation parity, source-reviewed complete FPS execution AIR,
   and actual proof generation/verification for all financially relevant rules.
3. Real four-validator test-XOR admission/dispute/settlement and NFT market runs.
4. Native Connect exact-action signing, verified results and finality recovery.
5. Full content, asset licensing, playtesting, accessibility and frame-time checks.
6. Full-size proof <=30 minutes and <=96 GiB on the M1 Ultra reference host.

Live funding and trading remain disabled until their actual qualification gates
pass. A replay hash, a signed checkpoint, a unit test or a kill event is not a
cryptographic execution proof. No production network or asset is guessed.
