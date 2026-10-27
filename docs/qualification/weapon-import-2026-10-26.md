# Corrected weapon ArtReview import — 26 October 2026

Saved-package persistence passes. Full source fidelity and final art acceptance
remain open. No gameplay weapon was replaced.

## Source and editor results

Signed `eba7f54d4dcc68b3b5e5f6232884ca6e6eb636dd`, tree
`11ff66a1b4bc435a12d9372f75e4b98e4156783a`, imports the corrected kit into
`/Game/ArtReview/RuntimeWeapons` using pinned UE 5.8.3 CL58210709 and Xcode
26.1.1. The native bridge remains `10ad7daddf73212e81496620aba628ebf214ab72`.

The inventory is 20 meshes, 60 authored LODs, 926,089 total LOD triangles,
64 sockets, 16 materials and 64 textures: 100 saved packages. The actual editor
readback checks all LOD counts, signed bounds, screen thresholds, two UV channels,
single material slots, no generated collision, Nanite disabled, authored normal
and tangent import settings, full socket frames, and saved material graphs.
Graph checks cover the four maps, color spaces, DirectX normal convention,
W07 masked/two-sided alpha and each kit's authored emission.

Import attempt 2 and a separate `mode=validate` editor process both finish with
natural editor/wrapper exits 0/0. Reopen changes no ArtReview packages, Generated
assets or Config files. All render-array hashes, material graph readbacks and
socket frames match the import run exactly. The first importer attempt at
`97a152b6` remains failed: seven mesh readbacks preceded a W05 LOD2 UV-range
failure; its original log and partial package inventory are retained.

The import log retains 19 pre-initialization `Condition failed` diagnostics,
40 Interchange LOD-name warnings and 60 editor CPU-access warnings. The startup
diagnostics also occur in preceding editor runs; this is not an error-free
engine qualification. Readback is editor-only and does not need cooked CPU
mesh access. Three-LOD readback independently verifies the explicitly imported
LOD files despite the filename warnings. No game automation tests ran here.

## Strict source comparison and remaining defects

The CPU comparator reads the exact FBXs through Blender's parser without running
Blender. It matches oriented triangle corners, preserving UV seams and split
vertices, then checks position, UV0, normal and tangent differences. A corrected
clockwise face model follows Unreal's coordinate convention. Signed `39e348bb`
tightens source-to-render matching to 0.00005 cm so fine adjacent triangles are
not mistaken for one another. The earlier comparison failures remain archived.

**58 of 60 LOD comparisons pass; the complete comparison remains failed.**
All 60 match positions, triangle winding and normal tolerances. Two LOD0s remain
held under the unchanged strict UV/tangent limits:

- **W12 Monofilament Naginata:** four corners, mapped to two render vertices,
  differ in UV0 by at most `0.0000554958935` (about 0.114 texel at 2048px).
  Unreal's builder merges vertices using its UV-equality test. The strict
  source comparison still reports this difference instead of widening its limit.
- **W15 Micro Mortar:** 384 corners / 130 render vertices have zero Unreal
  tangents. Their source tangents point along the source normals, so the basis
  is degenerate; Unreal's orthogonalization removes that component. These are
  unit-length parallel source vectors, not tiny source vectors. The strict
  tangent mismatch remains a failure pending source correction.

Two additional source defects are faithfully preserved and explicitly reported:
W05 LOD2 has one atlas corner reaching V=`1.0097212456`; W09 LOD2 has two reaching
V=`1.0032147579`. The pinned envelope verifies exact source UV bounds and outside
corner counts. It does not approve these UV layouts. Claude has the defect list
for a later kit correction, after the current character revision.

Original rendered review, framing and grip checks, gameplay adoption, cooked
assets, Nanite, Windows/M1 and performance qualification remain outstanding.
The existing gameplay importer still loads the older weapon assets. The new
ArtReview importer is deliberately not in that production import chain yet.

## Retained evidence

Under the complete-game worktree's `Saved/Qualification/2026-10-26/`:

- `weapon-review-97a152b-import-attempt1/` — failed import, source UV diagnosis.
- `weapon-review-eba7f54-import-attempt2/` — successful import, raw logs and inputs.
- `weapon-review-eba7f54-reopen-attempt1/` — fresh saved-package validation.
- `weapon-review-independent-review.json` — authenticates both natural exits,
  every archived file, identical readbacks and 100 package hashes; keeps strict
  source fidelity failed. SHA256:
  `513913fe10174b5afdf9ea3c771ac29d14f17b1c5c1291a651f322aaaf28ad83`.

Full arrays and both source comparisons remain under
`Saved/WeaponReviewImports/20261026T055007.380530Z/`; the matching reopened arrays
are under `20261026T055206.925982Z/`. The source envelope SHA256 is
`0f84ef765a6f3e8cbd7967123dd260c5cbd21467d5634c26c259a63d9cc5886e`.

All 49 local asset/tooling gates pass at `97a152b6` with unchanged clean source;
their independent log review is
`69c423586a13f1f3552dbc4296c8b665face73bcefd502a95e9e668bd1e56a7d`.
The subsequent UV/winding/near-triangle fixes pass 13 targeted admission tests.
The earlier pushed `6a54e3d4` passes all 117 source CI gates in authenticated run
`40273883821`, tested merge `8a0075e4170ca9f9139ead8c4cce980a60214353` with
identical source tree. Review SHA256:
`5497f470f541d98b547947bc20b2677c805c55ccc2802a8007bc4a15207f3f50`.
These source checks do not establish release acceptance.
