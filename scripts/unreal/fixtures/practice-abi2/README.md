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
charge interruption rules. Callers now require exactly ABI 2 before accessing
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

### Validation interpreter checks

The loader requires exactly ABI 2 with an explicit exception before any layout
query and rejects optimized Python (`-O`, `-OO`, or `PYTHONOPTIMIZE`). This prevents
staging or practice diagnostics from silently skipping assertions containing
native calls. Eleven guard tests now pass, including stale-library rejection,
optimized staging leaving binaries unchanged, and optimized parity runs replacing
old success reports with failure. Re-recording after this runner-only correction
confirmed identical controls and all 73 case expectations.
