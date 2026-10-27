# Saved dojo packages — permanent import validation

The Mac import pipeline now starts a separate editor process after the DojoKit
import and reopens all 16 required modules, including the four rails. It fails
if a saved package is missing or its reopened contents differ from the completed
import. The validator does not repair or save assets.

The implementation begins at signed `6c92cf59f47cba91a8a09476e2c9ced6d3bb5a33`.
The corrected read-only entry point is signed
`da669a331ec8d7491d5c8cb5fa52b0195a66c774`, tree
`a13e2f98364cf8b542f6091b7165ac05f0c49724`. It is validated in the isolated
source-validation worktree. The integration worktree remains at `1b6dfadc`;
its [passing package](mac-package-1b6-2026-10-27.md) predates this pipeline guard.

The import wrapper supplies the completed `import-dojo-kit.log` through
`SORA_DOJO_IMPORT_LOG`. The validator rejects Python failures, an incomplete
completion marker, missing module records and duplicate module records. It
checks the generator and every source LOD hash, then compares each reopened
mesh with its import audit:

- Conventional LOD counts, oriented per-section geometry hashes, UV0,
  normals, tangents, material assignments, bounds and screen thresholds.
- Dedicated Nanite source identity, full fallback settings, and nonempty
  Nanite triangle/vertex resources with their recorded counts.
- Material domain, blend/shading behavior, sidedness, and required Nanite
  and instanced-mesh usage.

The existing geometry API does not expose UV1+ values, vertex colors or raw
buffer layout. Those remain outside this comparison. Its editor CPU-access
warnings are retained; the validator does not enable CPU access to suppress
them. Saved Nanite settings and resource counts do not prove raster coverage.

All 28 helper tests and all 10 import-pipeline tests pass. New cases reject
missing/wrong assets, stale source links, missing LODs, wrong slots, incomplete
resources, reduced fallback settings, missing materials, changed geometry with
unchanged triangle counts, and incomplete or duplicated import audits. The
pipeline fixture checks that the completed import log reaches the fresh
validation process and that a failed validation prevents later import stages.

The first helper run had one failed test fixture: removing a LOD without its
screen threshold triggered the earlier screen-size check. The corrected fixture
removes both, so it reaches the intended saved-LOD comparison. The original
failure remains under `Saved/Qualification/2026-10-27/` alongside the passing
runs. No production check was relaxed.

A fresh editor process at `da669a33` successfully reopens all 16 saved modules
and exactly matches their completed import audits. Independent review verifies
all 6 original evidence files, natural EOF, source identity and
unchanged source-validation and integration input manifests. The C++ module
remains the previously built `c4b47fbb` code; subsequent changes are Python,
shell and documentation only. No new C++ build, import, asset save or render
was requested. The run starts at 07:46:40 UTC and finishes at
07:47:24 UTC.

The first native attempt at `6c92cf59` passes all module checks but fails the
outer immutability guard because embedded Python rewrites
`dojo_nanite.cpython-311.pyc`. Its status remains failed. The correction sets
`sys.dont_write_bytecode` before importing project helpers; the passing run
then leaves the cache and every other guarded input unchanged. Both runs
retain 41 editor CPU-access warnings and 19 pre-initialization `Condition
failed` diagnostics, with no Python error. These are not hidden or classified
as selected gameplay-test results.

Evidence is under `Saved/Qualification/2026-10-27/` in the source-validation
worktree. The earlier one-off check remains in
[the restoration record](first-launch-dojo-restore-2026-10-27.md).

| Record | SHA-256 |
| --- | --- |
| Passing original status | `d61134a52c6fab59ee5c1fc67d712668ecf6b91fd50c415c65bc2d1acc067efc` |
| Independent readback review | `29f4eed7be9bf59734a77b8c498a519997471b6665adb9860fceb64c0377eac7` |
| Preserved failed-attempt review | `5f9ebdf1d9955a84f0fa3bd12d2c641edd583bfaacec30b8942ccd408f1a8652` |

This change does not deliver unique beam art, final lighting, physical M1
qualification, Windows, ordinary play, performance or release acceptance.
