# Detached diagnostic checkpoint

Recorded 2026-10-18 from the unchanged `ue583-diagnostic/sora-arena` worktree.
Base HEAD: `6dadd1078424628cd8722ffd6ab26edd98c44d85`.
Master used for byte deduplication: `6609c178c332f76e0e38bb9203474dd8d17fe5d2`.

This preserves older September diagnostic work without replacing newer game
sources. It is recovery evidence, not accepted art, a build or a release.

- 287 changed/untracked source files have exact Git blobs or LFS pointers
  reachable from the recorded master commit. The inventory records each object.
- 26 unmatched files are copied byte-for-byte beneath `snapshot/`.
- `Config/DefaultEngine.ini` has a sanitized snapshot: its editor-generated
  AndroidFileServer SecurityToken value is removed. The exact original and all
  unmatched files are retained in the private external directory recorded in
  `inventory.json`; that directory is not for publication.
- 565 generated Unreal packages under `Content/Generated` and `Content/ArtReview`
  are inventoried as excluded. Ignored files/caches/restricted downloads were
  never enumerated or copied. The original worktree is intact.

The four Stone Pathway 02 texture files are by Amal Kumar, under
[Poly Haven CC0](https://polyhaven.com/license). The
[asset page](https://polyhaven.com/a/stone_pathway_02) and official files API were
checked on 2026-10-18. All four local MD5 hashes and sizes match the published
API; `polyhaven-verified-files.json` retains the exact URLs and checks. Repository
Git LFS attributes apply to the snapshot PNG/JPG files.

## Restore

Use a separate empty recovery directory or a new checkout of the recorded base;
never overlay the current master worktree. For each `master-history-preserved`
entry, obtain `git cat-file blob <reachable_oid>` from this repository. A normal
blob is the exact source bytes. If it is an LFS pointer, obtain its SHA-256 object
from the repository LFS store (fetch it if missing), and verify the inventory's
size/SHA-256 before placing it at `path` in the recovery directory.

For each repository snapshot entry, copy `snapshot_path` to its original `path`.
Verify against `snapshot_sha256`. This reconstructs all inventoried source with
the documented credential omission. An exact private restoration can use
`private_original_location/Config/DefaultEngine.ini` and verify the original
`sha256`; do not publish that file. `source.patch` is an additional text-only
patch against the recorded base, including new scripts, with the same credential
omission. Binary snapshots must be copied separately.

The clean ai/vfx, campaign/env, gameplay and practice/audio worktrees had no
commits outside master at audit time. No worktree, index or branch was changed
by this checkpoint operation.
