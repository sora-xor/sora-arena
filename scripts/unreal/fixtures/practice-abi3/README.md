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
