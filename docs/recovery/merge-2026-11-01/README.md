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
