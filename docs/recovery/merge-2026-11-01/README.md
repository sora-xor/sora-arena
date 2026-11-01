# Merge recovery snapshot — 2026-11-01

This snapshot accompanies the integration of the existing local branches into
`master`. `inventory.json` records the starting commits, branch audit and exact
hashes of the seven untracked art files.

The gameplay baseline is `e322bb33`; the art baseline is `733604b0`.
Older branches already incorporated by cherry-pick are recorded as merge
parents after comparing their patches. Later integrated fixes are retained.
The missing flood-carrier bank diagnostic is merged normally. The bow capture
profile-preservation change was already present through `8ea8dcd3`.

Art conflicts combine the newer W18 rebuild and research tools with the
integrated socket corrections, timber importer fixes, runtime presentation,
lighting and campaign bindings. Both scoped weapon update records are retained;
the metric report combines the existing weapon records with W18's newer record.
Historical timings and receipts remain evidence of their original runs.

`spire-supply-stash.patch` preserves the tracked and untracked portions of the
old supply stash. Its implementation is superseded by the current supply code.
The original stash remains available.

`untracked-art/` preserves the original SoraMaku prototype outputs at their
original relative paths. The FBX and texture hashes match their build record;
the generator has changed since that record. These are recovery artifacts,
not newly admitted production assets. The originals remain in the art worktree.

Existing WIP status, failed visual gates and release limitations remain in force.
This merge does not claim Unreal runtime or visual qualification.

## Validation

The full inventory ran 125 source gates (Rust, gameplay, tooling, assets and
audio). 123 passed initially. The weapon-review manifest pin and chapter-three
timber binding were stale; both pass after the focused metadata corrections.
The refreshed weapon review still reproduces the same 20 meshes / 60 LOD
geometry envelopes. Asset ledger, notices and timber admission checks also pass.

Of 37 additional art test modules, 36 pass after correcting the workshop
checker's FBX unit handling. The remaining module passes 29 of 30 tests; its
frozen-v1 timber input hash assertion also fails on the original art branch,
with identical test, library and manifest bytes. That pre-existing provenance
failure is retained rather than replacing the historical input hash.

`validation.json` records the checks and log/report locations. Earlier failed,
interrupted and timed-out runs remain under `Saved/SourceChecks/`. No Unreal
runtime or rendered qualification was performed as part of this merge.
