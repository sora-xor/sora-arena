# Native practice parity fixture

This repository fixture was recorded by executing the real Rust kernel on **macOS arm64**. Windows has **not** been run or certified. A passing report applies only to the host named in that report. It does not verify Unreal compilation, rendering, input integration, networking, on-chain proofs or settlement.

The fixture contains 73 cases: every combination of four maps, six classes and three admitted loadouts, plus a targeted death/respawn scenario. A complete verification executes 44,100 canonical ticks.

## Run on macOS

From the repository root, with native Rust and Python 3 available:

```sh
cargo build --release -p arena-ffi
python3 scripts/unreal/stage_kernel.py --platform Mac
python3 scripts/unreal/verify_parity.py
python3 scripts/unreal/test_parity_guards.py
```

## Run on Windows

From the same source revision on 64-bit Windows, with a native Rust MSVC toolchain and Python 3 available:

```powershell
cargo build --release -p arena-ffi
py -3 scripts/unreal/stage_kernel.py --platform Win64
py -3 scripts/unreal/verify_parity.py
py -3 scripts/unreal/test_parity_guards.py
```

The runner itself uses only Python's standard library and the real target-platform shared library. It does not require Unreal, a network service or a Python package installation. `--library PATH` selects another explicit native library. Verification must use the repository fixture unchanged; do not regenerate expectations on Windows to make a mismatch disappear.

Reports go to `Saved/Diagnostics/parity-<system>-<machine>.json`. Collect a successful Windows report and a successful macOS report against the **same manifest SHA-256** before making a cross-platform parity claim. Each report identifies its native library hash; different platform binaries are expected to have different binary hashes.

## Identity and comparison rules

`manifest.json` records:

- Exact canonical control file lengths and SHA-256 hashes.
- The eight-byte input encoding from `arena_core::simulation::Input::encode`: little-endian `<HbbHh>` (buttons `u16`, forward/right `i8`, yaw `u16`, pitch `i16`). Frames are tick-major; permanent slots ascend within each frame. Slot and tick are implicit. `.gitattributes` prevents text conversion of these binary files.
- Every C ABI structure's expected size, alignment, scalar field type and byte offset.
- SHA-256 identities for the simulation, math, combat catalog, economy, C ABI/header and dependency manifests, plus the exact Python binding/runner sources. Source text normalizes CRLF to LF, allowing ordinary Windows checkouts. Unrelated transport/proof implementation files are outside this fixture's explicit semantic-source scope.
- Actual native map geometry, weapon data and per-case initial/final state hashes.
- Cumulative state, event and presentation digests at every 60-tick checkpoint. State streams include every completed tick and its native hash. Event streams include every tick, count and event field. Presentation streams include snapshot fields, every player and presentation field, and every stable-ID projectile. Each scalar is encoded little-endian by name/order, with C padding excluded.

The runner also verifies zero financial movement, rejected-input atomicity and terminal immutability. The dedicated elimination case exercises both death and respawn. The transcript's aim values are stored bytes; verification does not recalculate them with host floating-point math.

Any mismatch exits nonzero without writing a success report or changing the fixture. Starting verification invalidates the previous report; failure writes `status: fail`, so an obsolete pass cannot be mistaken for the current run. `test_parity_guards.py` verifies rejection of altered controls, noncanonical input, ABI layout, source/runner identities, state hashes and event digests, plus invalidation of an old success report.

## Deliberate baseline changes

When the first-release rules or relevant code intentionally change, review the reason and then explicitly run:

```sh
python3 scripts/unreal/verify_parity.py --record-reference
```

This replaces the reference controls/expectations by executing the loaded native kernel. It is a maintenance operation, never the solution to an unexplained platform mismatch. Review the resulting source identities, control hashes, geometry/weapon identities and expected digest changes together. Recording a new macOS reference does not establish Windows parity.

### 2026-09-22 projectile correction

The reference was deliberately re-recorded after three regression tests exposed
and checked projectile arming and range behavior. Arming now uses the distance
actually traveled to an impact; range expiry clamps the final movement step to
the remaining range. Previously, a collision could arm an explosive using the
unused part of its movement step, and a projectile could overshoot its range.

The update changed expected results in 37 of 73 cases. The control bytes, ABI
layout, runner identities, and map/weapon data identities did not change. The
new real macOS library passed all 73 cases / 44,100 ticks, and all eleven negative
fixture-guard tests passed. This remains a macOS reference, not Windows evidence.

### 2026-09-22 ammunition and presentation ABI 2

The fixture was replaced after adding authoritative magazine/reload state and
charge interruption rules. At that historical reference update, callers required
exactly ABI 2 before accessing
the larger presentation and weapon-spec buffers. No ABI 1 fallback is retained.
The canonical input encoding is unchanged; bit 32 now starts a kernel reload.
All state hashes include ammunition and reload timing, so every case's expected
state digest changes intentionally. Magazine/reload fields are also compared
in the native weapon data and every player presentation snapshot.

After this update, all 73 cases / 44,100 ticks and eleven negative guard tests
passed on macOS arm64. Review confirmed that canonical control bytes are
unchanged. Windows has not executed the new ABI 2 fixture.

### 2026-09-23 P2P dependency refresh

Adding the signed and encrypted P2P frame modules changed `Cargo.lock`, the
`arena-core` dependency manifest, and its module list. The release library was
rebuilt and staged from that source before the macOS reference was deliberately
re-recorded. A structural comparison against the prior reference confirmed
that all 73 case expectations, canonical control hashes, ABI layout, native
map/weapon data identities, runner hashes, input encoding, and digest encoding
are unchanged; only those three source-file identities, the native library
identity, and recording metadata changed. Verification again passed all 73
cases / 44,100 ticks and eleven negative guards on macOS arm64. This does not
establish Windows parity or certify the P2P network and proof path.

Authenticated 1,200-byte packet fragmentation then added `hmac` and the
`fragmented_wire` module. The macOS release library was rebuilt and staged
again. A structural comparison against the immediately prior fixture found no
changes in all 73 case expectations, control bytes/hashes, ABI, map/weapon
identities, runner, or encodings. Only `Cargo.lock`, the `arena-core` dependency
manifest and module list, native library hash, and recording metadata changed.
The current macOS library passed all 73 cases / 44,100 ticks and eleven negative
guards. The fragmentation tests are separate from this offline parity fixture.

### 2026-09-23 provisional hitscan balance, rules version 2

Clean-lane `World::step` measurements showed that the Arc carbine and
Clockwork repeater each killed a 100 HP target in five hits at tick 40, or
0.68 seconds from the first trigger input. Both are hitscan weapons. Their
attack cooldowns changed from 10 to 12 ticks, making the same kill occur at
tick 48 (0.82 seconds); the rules identity advanced to
`sora-arena-first-release-2`. This is a provisional correction, not evidence
that live multiplayer is balanced.

The macOS arm64 reference was deliberately re-recorded from the rebuilt native
library. Structural comparison against the immediately prior fixture found
changed expectations in **all 73 cases**. Control bytes and hashes, input and
digest encodings, ABI layout, runner identities, and map geometry identity are
unchanged. The native weapon-specification SHA-256 changed from
`fe2191c0742f70e8dce7834341d4b3d45996d0ac0fdb8c08139c15536c805258`
to `293394ddcd072747e9224e3458bea8ce8dce71f03388ec878e8f4e9382a83146`.
The source identities for `lib.rs`, `catalog.rs`, and `simulation.rs` changed;
the last includes an adjusted cooldown-sensitive test bound. The current
library again passed all 73 cases / 44,100 ticks and eleven negative fixture
guards on macOS arm64. The full locked offline Rust workspace suite passed 66
tests. Windows parity and Unreal gameplay remain unverified.

### 2026-09-23 team-mode Healing lance, rules version 3

The Healing lance now selects the nearest ray-intersected living player in a
team match: a teammate receives 15 health up to class maximum, or an enemy
receives 15 damage. Dead teammates cannot be revived. FFA remains damage-only.
Simultaneous queued healing resolves before damage. Five kernel behavior tests
exercise targeting order, healing cap, dead targets, FFA, and same-tick survival.
The rules identity advanced to `sora-arena-first-release-3`.

The macOS reference was deliberately re-recorded from the rebuilt ABI 2
library. Compared with the rules-version-2 fixture, all 73 cases have changed
state hashes and checkpoints. Their event and presentation streams are
unchanged: this offline fixture contains no team-mode Healing lance shot.
Control bytes/hashes, ABI layout, runner, input/digest encoding, map and weapon
data identities also remain unchanged. Source identities changed only for
`lib.rs` and `simulation.rs`. The new library passed 73 cases / 44,100 ticks,
all eleven negative fixture guards, and the 71-test locked offline Rust suite
on macOS arm64. Windows parity and Unreal gameplay are still unverified.

### 2026-09-23 charged combat and presentation ABI 3

Plasma matchlock's charged **direct** hit now penetrates directional guard;
projectile and self-damage retain the normal defense rules. Kanabo now requires
an eighteen-tick held windup and spends stamina only on the strike. Charge
progress is bound to the selected weapon, so holding melee cannot precharge a
Micro-mortar or another firearm. These outcome-affecting changes advance the
rules identity to `sora-arena-first-release-4`.

The current presentation ABI is exactly **3**, with two appended `u32` fields:
`charge_ticks_current` at byte 36 and `charge_ticks_required` at byte 40; the
structure is 44 bytes. Native Unreal code and the Python loader reject every
other ABI. The HUD bar and practice-pawn weapon pose read this authoritative
snapshot, although Unreal has not been compiled or playtested. The fixture
directory and identity moved from `practice-abi2` to `practice-abi3`; there is
no ABI 2 fixture or compatibility loader in this release source.

The macOS arm64 reference was deliberately re-recorded after rebuilding and
staging the ABI 3 library. Compared with the immediately prior ABI 2/rules-3
reference, the 73 control streams, participant loadouts, map geometry, input
encoding and digest encoding are unchanged. Session configurations differ only
in their required ABI number. The native weapon-specification SHA-256 changed
from `293394ddcd072747e9224e3458bea8ce8dce71f03388ec878e8f4e9382a83146`
to `cb0ad920ba09c1effe43ea042c5314d27888c3637dd0f7d9b5c29ae2dac76d7a`.
All 73 cases changed their state and presentation expectations; event streams
changed only in the four Hanabi/Kanabo standard-loadout cases, each with three
fewer shot events in the 600-tick transcript. The new library passes all 73
cases / 44,100 canonical ticks, eleven negative fixture guards, and 72 native
practice scenarios / 86,400 replayed ticks. The locked offline Rust workspace
suite passes 80 tests. Windows parity and Unreal gameplay remain unverified.

### Validation interpreter checks

The loader requires exactly ABI 3 with an explicit exception before any layout
query and rejects optimized Python (`-O`, `-OO`, or `PYTHONOPTIMIZE`). This prevents
staging or practice diagnostics from silently skipping assertions containing
native calls. Eleven guard tests now pass, including stale-library rejection,
optimized staging leaving binaries unchanged, and optimized parity runs replacing
old success reports with failure. Re-recording after this runner-only correction
confirmed identical controls and all 73 case expectations.

### 2026-09-23 suicide attribution, rules version 5

An armed self-inflicted explosive death could previously pay a recent enemy
damager from the five-second assist history. The outcome rule now treats that
death as a suicide with no XOR transfer, regardless of earlier enemy damage.
A focused `World::step` regression test detonates a self-owned projectile after
qualifying enemy damage and verifies that the full initial bond remains in the
victim's reserve. This financially relevant correction advances the rules
identity to `sora-arena-first-release-5`.

The macOS arm64 release library was rebuilt, staged, and deliberately used to
re-record this ABI 3 reference. Structural comparison with the immediately
prior fixture found identical control bytes and hashes, session configurations,
rosters, ABI layout, runner identity, map/weapon identities, event streams,
presentation streams, and event counts. All 73 initial and final state hashes,
state streams, and 735 checkpoint state hashes/streams changed as expected from
the rules identity in the canonical world hash. Source identity changed only
for `lib.rs` and `simulation.rs`. Verification passes 73 cases / 44,100 ticks,
eleven negative guards, 72 practice scenarios / 86,400 ticks, and the locked
offline Rust suite. These fixtures still do not prove payout correctness or
Windows/macOS parity.

### 2026-09-23 wall-surface blast attribution, rules version 6

A grenade that arrived exactly on a wall's closed AABB face could have its
same-side blast ray counted as blocked at the zero-distance intersection. A
nearby enemy then survived a valid lethal blast, preventing the corresponding
XOR death transfer. The occlusion rule now ignores that wall only when the ray
immediately leaves its surface; a ray into or through the wall remains blocked.
The focused kernel regression fires a real grenade at the near face, checks a
same-side kill and exact 100-unit transfer, and checks far-side occlusion.
This outcome-affecting correction advances the rules identity to
`sora-arena-first-release-6`.

The macOS arm64 release library was rebuilt and staged before deliberately
re-recording this ABI 3 reference. Against the immediately prior fixture,
control bytes and hashes, session configurations, rosters, ABI layout, runner
identity, native map/weapon identities, event streams, and presentation streams
were unchanged. The 73 initial/final state hashes, checkpoint state hashes,
and state streams changed with the rules identity; source identity changed
only for `lib.rs` and `simulation.rs`. The offline reference scenarios do not
exercise the wall-surface payout regression and cannot establish Windows parity
or execution-proof qualification.

### 2026-09-25 test-only source identity refresh, Rust 1.97.1 pin

Research tests added a `#[cfg(test)]` module declaration to `economy.rs` and a
`serde_json` dev-dependency to `arena-core`, which also changed `Cargo.lock`.
None of these changes is compiled into the release library. Before
re-recording, the rebuilt release library was compared against the unchanged
reference with only the source-identity gate bypassed. All 73 cases / 44,100
ticks matched in every initial and final state hash, state, event and
presentation stream, event count and checkpoint. The runner identity, ABI
layout, native map/weapon identities, both checked-in control files and
freshly regenerated control bytes also matched. A deliberately altered
presentation digest was reported as a mismatch.

The library was then rebuilt with the Rust 1.97.1 toolchain now pinned by
`rust-toolchain.toml`, staged, and used to re-record the fixture. A structural
comparison with the prior manifest found identical cases and control files.
Only these three source identities, the reference library SHA-256 and the
recording time changed. Two clean release builds with the same pinned compiler
produced different library SHA-256 values, so the reference library hash
identifies only the recorded binary; parity is established by the per-case
outputs. Verification passes 73 cases / 44,100 ticks and eleven negative guards
on macOS arm64. Windows parity remains unverified.

### 2026-09-25 guard origin and internal effect events, rules version 7

Directional guard and parry now use where the damage came from: the attacker's
eye for rays and the detonation point for blasts. Before this change a blast
behind a guarding player was blocked when its thrower stood in front, and a
blast in front was not blocked when its thrower stood behind. The kernel also
records `Guarded` and `Healed` events internally. ABI 3 does not export them:
`event_count` and `arena_event` skip them, so ABI 3 callers see exactly event
kinds 1-5 at unchanged indices. Weapon 15 is renamed Bō-hiya rocket, with no
change to its simulation. The rules identity advanced to
`sora-arena-first-release-7`; `docs/combat-rules.md` specifies the full
revision.

Before re-recording, every case was run in separate processes against three
release libraries:

- the previously staged rules-6 library, which reproduced the prior manifest
  exactly;
- a scratch build of the pre-change sources with only `RULES_VERSION` bumped;
- the new library.

The new library matched the version-only build in every field of all 73 cases,
including every state hash. So the guard-origin fix and the event filtering
change no outcome in these scenarios, and the state-hash change comes from the
rules identity alone. Against the prior manifest, the control bytes, session
configurations, rosters, ABI layout, runner identity, native map and weapon
identities, event streams, presentation streams, event counts and per-checkpoint
event and presentation digests were unchanged. All 73 initial and final state
hashes and state streams, and the 735 checkpoint state hashes, changed. Source
identity changed only for `lib.rs`, `simulation.rs` and `catalog.rs` in
`arena-core` and `lib.rs` in `arena-ffi`. The kernel's own regression tests,
not this fixture, cover the guard-origin behaviour.

### 2026-09-25 class abilities and entities, rules version 7

The kernel now implements the six first-release-7 class abilities and the
entities they create (`docs/combat-rules.md` §5 and §6): the Samurai counter
stance, the Shinobi decoy, the Teppō mark, the Hanabi fire zone, the Karakuri
barricade and the Kusushi ward. It also implements the separate ability phase,
the mark, stance and ward modifiers, parry stagger, and ability cooldowns that
keep counting while a player is dead. The state hash uses the interim §12.1
layout, which adds the stance and mark timers, the entity list and
`next_entity_id`. The fixture's exercise controls press the ability button, so
every exercise case changes. The ABI 3 layout and exported event kinds are
unchanged. The new internal events (`AbilityUsed`, `Marked`, `Riposte` and the
four entity events) are skipped like `Guarded` and `Healed`. Entities are not
exported until ABI 4.

Before re-recording, every case was traced tick by tick, in separate
processes, against the previously staged library (`a7ad4c30…`) and the new one.
The comparison covered the per-tick digests of the exported events and of the
snapshot, player, presentation and projectile queries:

- The 72 exercise cases diverge exactly at the first tick where any slot
  presses the ability button, and never earlier. At that tick the only
  difference is the Teppō's new 720-tick cooldown in place of 600.
- The death-and-respawn case never presses the ability button. Its exported
  events and presentation are identical at every tick. Only its state hashes
  change, because of the new hash layout.

A scratch build of the new kernel with only the pre-step hash layout restored
reproduced the pinned eight-player research hashes. Its kill-history V2
projection differed from the previous fixture only in `kernel_revision`. So
outside ability use, the behavioural changes do not alter these scripted
matches.

Against the prior manifest, these were unchanged: the control bytes, session
configurations, rosters, ABI layout, native map and weapon identities, and the
input encoding. All 73 initial and final state hashes, state streams and
checkpoint lists changed. Event streams changed in 30 cases and presentation
streams in 72. Source identity changed for `simulation.rs` and `math.rs` in
`arena-core` and `lib.rs` in `arena-ffi`, and the new
`simulation/abilities.rs` was added. That file was also added to
`verify_parity.py`'s `SOURCE_FILES`, which changes the runner identity. The
new library passed 73 cases / 44,100 ticks and all eleven negative guards on
macOS arm64. Windows parity remains unverified.

### 2026-09-25 authored arenas, objectives, hazards and respawn, rules version 7

The kernel now implements the rest of first-release-7 (`docs/combat-rules.md`
§7–§10 and the final §12 state hash). The four arenas are authored integer data
with 38–42 walls each, per-arena bounds, spawns, a control point, a payload
route and hazards, and the configured arena's map digest replaces the wall list
in the state hash. Control and Payload objectives, the match result
(`MatchWinner`), environmental hazards with the environmental kill credit,
spawn selection by team rank or farthest FFA spawn, and respawn loadout
requests are new. Projectiles expire at the arena bounds. The ABI 3 layout and
its exported event kinds are unchanged; the new internal events are skipped,
and `arena_step` rejects the rules-7 loadout bit (64) with status 2, as it
rejected every bit above 32 before. `arena_map_info` and `arena_map_wall` now
serve the authored arenas.

The death-and-respawn case had to change. Its attacker, slot 4 made a Teppō,
has no line of sight to slot 0 from the new Estate FFA spawns. The case now
uses slot 2, which the standard roster already makes a Teppō with the Coil
matchlock, aiming from FFA spawn 2 at slot 0 on FFA spawn 0 along
x = -18,500. The roster no longer overrides slot 4, and the recorded aim and
control file changed with it. Its event counts are unchanged: 12 shots,
4 damage, 2 deaths, 1 respawn and 1 terminal.

Before re-recording, the previous fixture was run in separate processes against
the previously staged library (`51462d4b…`, which reproduced it exactly) and a
scratch build of the new kernel with the first-release-6 map data restored: the
old 3–4 wall boxes, ±24,000 mm bounds, the old spawn points, the old respawn at
the slot's own spawn without resetting yaw or pitch, and no hazards. In all 73
cases the two produced identical event streams, presentation streams and event
counts, identical event and presentation digests at all 735 checkpoints, and
identical native map and weapon identities. Only the state hashes differed,
because of the v2 layout. So every behavioural change recorded here comes from
the new arena data and spawn rules, not from the objective, hazard, loadout or
result code, which FFA practice does not reach.

Against the prior manifest, these were unchanged: the exercise control bytes,
session configurations, every roster except the death case's, the ABI layout,
the input encoding and the weapon-spec identity. The map geometry identity
changed, as did the death-and-respawn control bytes and all 73 initial and final
state hashes, state, event and presentation streams. Event counts changed in 36
cases. Across all cases, shots went from 11,976 to 11,401, damage events from
196 to 102, deaths from 2 to 38 and respawns from 1 to 2, because the exercise
lanes now meet on the new maps. Source identity changed for `lib.rs`,
`simulation.rs`, `simulation/abilities.rs` and `catalog.rs` (its duplicate
map-name table was removed; `maps.rs` now names the arenas) in `arena-core` and
`lib.rs` in `arena-ffi`. `maps.rs`, `simulation/hazards.rs`, `simulation/objectives.rs` and
`simulation/respawn.rs` were added to `verify_parity.py`'s `SOURCE_FILES`,
which, with the death-case change, changes the runner identity. The new library
(`c9f6b781…`) passed 73 cases / 44,100 ticks and all eleven negative guards on
macOS arm64. Windows parity remains unverified.
