# Production dojo Nanite draw diagnostic

This is an uncooked, developer-only renderer diagnostic using the production
chapter-one dojo. It does not admit the existing art, establish unique-beam
fidelity, measure performance, or qualify a platform release. No Nanite draw
has been established merely by adding this fixture. Root must execute and
review the original images.

Run only in a disposable standalone game process at the initial paused
Title/Main menu, never in an active game. After the source-bound build:

```sh
scripts/toolchain/capture-editor-game.sh SoraCapture.NaniteDraw.DojoSM6 1280 720 sm6
scripts/toolchain/capture-editor-game.sh SoraCapture.NaniteDraw.DojoSM5 1280 720 sm5
```

1920×1080 is also supported. Do not run both shader-model filters in one
process: shader platform is chosen at launch. The SM6 test requires actual
SM6 and Nanite eligibility; the SM5 test requires actual SM5 and conventional
eligibility. An M2 running SM5 is **not M1 hardware evidence**. Neither path
qualifies Windows. The wrapper records the exact checkout commit/status,
engine/runtime log, automation devices and original frame hashes.

The SM6 run saves six originals, in order: `entry-Lit`, `entry-Mask`,
`entry-Triangles`, `ceiling-Lit`, `ceiling-Mask`, `ceiling-Triangles`.
SM5 saves the two Lit frames only and explicitly makes no Nanite draw claim.
The fixed camera locations in centimetres are `(8420,0,154)` and
`(9500,-200,154)`, with pitch/yaw/roll `(4,0,0)` and `(52,20,0)`, horizontal
FOV 94°. Gameplay is paused. Each mode settles for at least three seconds
of wall time. The fixture checks the actual camera-manager transform/FOV;
it does not move the hero, paint overlays, alter materials, add substitute
geometry, enable Nanite, or select a different asset tier.

`SoraNaniteDrawCapture.cpp` uses an isolated chapter-one beat-two save and
restores the original menu checkpoint, screen, view target, HUD visibility,
pause state, show flags, view mode and visualization cvars. Original campaign,
controls and settings slot bytes **and existence** are preserved after the
original checkpoint is reconstructed, because `LoadSave/ResetRound` can
create an absent default save. Restoration also runs after failure/timeouts.
This deliberately isolates the diagnostic from `SoraArtReviewCapture.cpp`'s
older cleanup; that older capture path is not changed or claimed repaired.
The test submits no keyboard/mouse actions and does not alter input mappings.
It does not promise to reconstruct unsaved active gameplay, which is why that
starting state is rejected.

Originals and the source `capture.json` are under
`Saved/Screenshots/SoraNaniteDraw/<resolution>/<run-id>/`. The source report
records actual RHI, adapter, shader platform, all relevant cvar readbacks,
actual request/processed frame numbers, engine visualization readbacks, and
registered production DojoKit component/mesh/material identities, instance
counts, bounds, Nanite resource availability and component disable flags.
Bounds are queried through the component's `CalcBounds` at its current transform;
the separate raw cached bounds are also retained because freshly populated
instanced components can still have a zero cache before the first frame.
Authoring enablement is recorded when editor data exists. These are context,
**not draw counters**. Loose mesh `.uasset`/`.uexp`/`.ubulk` bytes are hashed
by the running fixture; the archiver checks that they have not changed and
records SHA256 identities as well. A packaged/IoStore asset run needs separate
package-byte binding and is not supported by this uncooked fixture.

The archive collector requires the exact original `LogTemp: Display:
SORA_NANITE_DRAW_FRAME` acknowledgements, complete ordered sequence, matching
SM6/SM5 test/device metadata, fresh matching source JSON, original PNG
integrity/dimensions, fixed camera and renderer settings, and successful
cleanup. Original PNG/JSON bytes are copied unchanged. When the draw gate
fails, these originals and `pixel-review.json` remain in the archive even
though the wrapper exits nonzero. Do not delete or relabel that failure.

The conservative pixel check inspects the middle 60% of each frame, excluding
engine labels and most exterior windows. It requires at least 24 new
strongly green Mask pixels relative to the same-camera Lit frame and at
least 24 corresponding changed, chromatic Triangles pixels across at least
four coarse color bins. It reports red conventional candidates separately.
These small thresholds reject blank/copy/isolated-pixel accidents; they are
not an exact coverage percentage, GPU statistic, triangle count or quality
target. It also requires at least one recorded, non-disabled dojo component
with actual Nanite data. Eligibility and authored flags alone cannot pass.
A human must inspect the original full frames and attribute green/triangle
coverage to the recorded dojo geometry, especially around windows or nearby
props; a parser pass is not artistic acceptance. A green material in the Lit
frame alone is explicitly rejected by the paired difference test.

## Engine source basis (installed UE 5.8.3)

Paths below are relative to the pinned engine's `Engine/` directory.

- `Source/Runtime/Engine/Private/NaniteVisualizationData.cpp:30–32` registers
  Mask and Triangles; `:227–274` reads `r.Nanite.Visualize`, resolves the mode
  and requests the engine show flag. The fixture never calls the renderer's
  `Update` to fake a successful readback.
- `Source/Runtime/Renderer/Private/DeferredShadingRenderer.cpp:2045–2071`
  updates Nanite visualization only in the actual enabled Nanite renderer.
- `Source/Runtime/Renderer/Private/Nanite/NaniteVisualize.cpp:28–50` defines
  composition/edge/debug shading controls; `:655–690` requires an active
  engine mode and actual raster results. The fixture temporarily sets
  composition to 1 (respect full scene depth), edges to 0 and debug shading
  to 0 for interpretable pixels, restoring each original value and priority.
- `Shaders/Private/Nanite/NaniteVisualize.usf:282–309` unpacks `VisBuffer64`
  and checks `ShadingMask.bIsNanitePixel`; `:404–416` colors actual triangle
  indices; `:589–593` emits green at opacity .5 for Nanite Mask pixels;
  `:793–805` emits red at opacity .5 for conventional depth-written pixels.
- `Source/Runtime/Engine/Private/StaticMesh.cpp:3035–3038` defines valid
  Nanite resource data as nonempty page-streaming states. It does not prove
  any particular component submitted visible raster work.

## Baseline production blocker and enablement plan

This plan is **not implemented by the diagnostic commit `81eb31a`**. At that
baseline, `scripts/unreal/import_nyaagyu_dojo_kit.py:20` says Nanite stays off,
and `:342` sets `build_nanite=False`. `SoraWorldBuilderDojoHall.cpp:28–38,56–70`
loads those same DojoKit meshes on both platforms; it does not choose the
estate HI/MAC assets. Therefore the baseline source predicts no Nanite dojo
resource data, even when the M2 selects METAL_SM6. The renderer diagnostic
must retain an honest failed gate if that is what its original pixels show.

The narrow enablement option is to keep the same source geometry and names,
then explicitly configure and verify Nanite plus a full conventional fallback
on each imported module. Use the existing repository importer pattern:
`StaticMeshEditorSubsystem.get_nanite_settings/set_nanite_settings`,
`enabled=True`, `generate_fallback=NaniteGenerateFallback.ENABLED`,
`fallback_target=NaniteFallbackTarget.PERCENT_TRIANGLES`,
`fallback_percent_triangles=1.0`, `keep_percent_triangles=1.0` and
`trim_relative_error=0.0`. Read those settings
back after applying and verify actual resource data after the mesh build.
Explicit full fallback avoids the engine's Auto/relative-error default silently
simplifying the present conventional representation. UE's
`EngineTypes.h:3213–3229,3335–3359` defines those controls; the existing
`import_nyaagyu_kawara_bay_art_review.py:230–243` demonstrates them on the
pinned engine. Do not merely change the import checkbox and assume existing
assets/reimports gained correct fallback data.

Retain the authored LOD imports and screen sizes (`import_module:357–370`).
Nanite uses its own hierarchy; the ordinary SM5/fallback path must still be
verified to select appropriate conventional LODs. Inspect resulting LOD0 and
LOD1/2 section counts, bounds, UVs, normals, material slots and screen sizes,
and compare the SM5 baseline/candidate originals before admitting any change.
`Config/Mac/MacEngine.ini` already retains `r.Nanite.ProxyRenderMode=0` for
conventional rendering on SM5. Verify cooked fallback availability as well as
uncooked SM5; editor fallback presence alone is not packaged proof.

Collision stays independent: import has `auto_generate_collision=False`,
and both instanced and single hall components disable collision/navigation
before setting meshes (`SoraWorldBuilderDojoHall.cpp:79–105`). Existing hall
collision boxes must remain untouched and pass the normal campaign traversal
suite. Do not repurpose the Nanite fallback as new gameplay collision.

Materials require actual validation. The kit binds the existing instanced
static-mesh material permutations, opaque scan/craft materials and two-sided
foliage shading for shoji paper (`arch_master`, `build_instances`,
`import_module`). Preserve slot order, position-derived UV variation, texture
sampling and subsurface behavior. Inspect the actual Nanite material audit and
Lit/Mask/Triangles captures; if a section is incompatible, keep it conventional
and report the red coverage instead of replacing it or suppressing a warning.
Do not assume a Nanite flag validates every material section.

Finally run the SM6 draw gate, same-camera SM5 fallback comparisons, packaged
SM5/SM6 and eventual **real M1** checks separately. None of this converts the
present repeated modules/boxes into the requested individually sculpted beams
with adze marks, checks, raised grain, knots, end grain and worn chamfers.
That art, its provenance, admission and performance remain separate work.

## Importer preservation audit and isolated engine probes

The follow-up importer uses `dojo_nanite.py` after binding the same LODs and
materials. It intentionally retains a conventional initial FBX import, then
sets all seven explicit Nanite/full-fallback controls and reads each back.
`prepare_conventional` also resets an existing asset before reimport: UE
`FbxStaticMeshImport.cpp:1789` otherwise replaces the import option with the
existing mesh's Nanite flag. This makes repeat imports start from a real
conventional source baseline instead of a previously reduced fallback.

The first real import exposed two distinct effects of a Nanite build. For
`SM_DojoBay_Panel`, the render LOD screen threshold changed from `[2.0]` to
`[0.0]`, and the overall mesh bounds expanded to include the Nanite hierarchy.
The failed audit remains a failure. Matching counts alone would not establish
that the conventional fallback retained the original geometry.

The revised helper reads every conventional render LOD/section with
`ProceduralMeshLibrary.get_section_from_static_mesh`. It compares exact
oriented triangles containing position, normal, UV0, tangent X and tangent
handedness. Triangle order, vertex/index numbering and cyclic corner order
may change; winding, connectivity, attributes and duplicate multiplicity must
remain identical. Equality compares the complete canonical content directly;
per-section SHA256 values are compact report aids. No coordinate rounding or
geometry tolerance is applied. Signed zero is normalized to numeric zero.
The API exposes UV0 only: this does **not** establish UV1+ value equality,
vertex-color equality or raw buffer byte identity. UV-channel counts remain
checked independently. The editor may warn that CPU access is needed for a
cooked conversion; the audit records that limitation and preserves the actual
`allow_cpu_access` flag instead of changing it to suppress the warning.

Before/after triangle and vertex counts, UV-channel counts, section-to-material
mapping, section collision and shadow flags, ordered material names/bindings,
simple collision count and collision complexity must still match. Exact
geometry-derived bounds must also match. Overall composite culling bounds are
reported separately: they may expand, but must be finite, nonnegative in
extent and contain all conventional geometry. The importer never shrinks or
overrides the engine's Nanite bounds. A changed composite center can affect
`ObjectPositionWS` material variation despite identical fallback vertices;
same-camera SM5 original-image comparison remains necessary.

The helper force-saves the conventional baseline before reading it, applies
the Nanite settings without an intermediate rebuild, imports the same
hash-verified LOD0 FBX as a dedicated Nanite source, then builds. It requires
the HiRes import to return true and its source filename to resolve to that
exact file both immediately and after the final save. The source hash is
checked before import and after save. Crucially, the ordinary geometry
snapshot precedes the HiRes import API, so that API's side effects are also
covered by the preservation audit. Repeat imports disable Nanite and clear
any prior named HiRes source before reimporting the ordinary source FBX.
An ineffective removal or an already-enabled baseline fails the audit.

After the Nanite build, the helper explicitly restores the original LOD screen thresholds
with `set_lod_screen_sizes`, requires the setter to succeed, and force-saves
the result before the final audit. Saving alone did not restore the thresholds
in the engine probe. The post-save audit retains the existing screen-size
comparison and all other preservation checks; no success line is emitted
before these checks pass.

It requires actual positive `get_num_nanite_triangles/vertices` after the
build: installed UE `StaticMesh.cpp:5024–5051` returns zero unless Nanite page
and root data exists, and `GetRenderData` waits for its asynchronous property.
Those are built input-resource counts, **not visible triangle counters**.
`MeshBuilder/Private/StaticMeshBuilder.cpp:296–302` identifies full fallback
input reuse when percentage is 1 and relative error is 0; the candidate sets
both explicitly.

Installed UE 5.8.3 source explains the audited behavior:

- `Plugins/Runtime/ProceduralMeshComponent/Source/ProceduralMeshComponent/Private/KismetProceduralMeshLibrary.cpp:402–500`
  copies the conventional position/index buffers, normal, UV channel 0,
  tangent X and handedness into section-local arrays of referenced vertices.
- `Source/Runtime/Engine/Private/StaticMesh.cpp:2493,3085` resolves section
  information and LOD screen thresholds during serialization.
- `Source/Editor/StaticMeshEditor/Private/StaticMeshEditorSubsystem.cpp:1020–1100`
  updates source and render screen sizes without requesting a mesh rebuild.
- `Source/Developer/MeshBuilder/Private/StaticMeshBuilder.cpp:885–897` includes
  the simplified Nanite hierarchy in overall bounds. This is culling data,
  not evidence that the conventional triangle positions changed.

On 2026-10-23 the root execution lane tested the original panel with required
Nanite material usage enabled. All three sections retained exactly the same
oriented geometry/attributes (704 triangles, 770 vertices), CPU access stayed
false, and explicit threshold restoration plus save yielded `[2.0]` with
704 built Nanite input triangles. A fresh editor process reloaded that asset
with `[2.0]`, 704 Nanite input triangles and CPU access false. Original
artifacts are `Saved/Qualification/2026-10-23/probe-dojo-nanite-geometry-verified.json`
and `probe-dojo-nanite-reload-verified.json`, with their corresponding logs,
in the root execution worktree. This is an isolated one-mesh mechanism probe,
not a successful run of the revised importer across all modules or a draw
qualification. Earlier `original-restore` probe artifacts lacked the required
material usage and had zero Nanite resource data; they remain diagnostic
failures and are not evidence of Nanite persistence.

The subsequent full-kit attempt with revision `b00a282` passed the panel but
failed the shoji module's exact geometry gate. A narrow root probe measured
position-only changes in shoji LOD0 sections 0 and 1 (880 and 88 triangles),
while normals, UV0, tangent X and handedness matched. For example, one Z
coordinate changed from `209.79998779296875` to `209.8000030517578`; another
changed from `0.19999998807907104` to `0.20000000298023224`. Nanite had 1256
input triangles. These measured changes are not admitted by a tolerance.

Full fallback reuses newly built Nanite input rather than the previous
conventional buffers (`NaniteBuilder.cpp:791–795`). The two input paths have
different overlap/degenerate rules: `MeshDescriptionHelper.cpp:41,53,68,83–86`
uses `THRESH_POINTS_ARE_SAME` for ordinary meshes when remove-degenerates is
enabled, but zero for Nanite. That overlap list affects vertex deduplication
in `StaticMeshBuilder.cpp:1723–1731`. The differences are consistent with the
measured near-coincident position substitutions; they do not imply Nanite
triangle simplification at 100 percent. Enabling explicit tangents alone
does not change this: full fallback already requires tangents at
`StaticMeshBuilder.cpp:297–302`.

The revised candidate therefore uses the same original FBX as a dedicated
Nanite source; "HiRes" is the engine API's name, not a claim of additional
detail. `StaticMeshBuilder.cpp:633–634,895–899` leaves conventional LOD0 on
the ordinary builder when a valid separate source exists. On a target without
Nanite support, the early return at `:179–188` also leaves LOD0 unsimplified.
The importer retains all seven explicit settings and exact geometry checks;
this changes the build path, not the accepted error.

The root lane's `probe-dojo-shoji-hires.json` and corresponding log at source
revision `8d8fac4` subsequently recorded 1256 built Nanite input triangles,
exact pre/post conventional oriented geometry and matching metadata, with
the dedicated source resolving to the original shoji FBX. Its SHA256 was
`52f19ea553af968c5436996bcf9b0ab2584e3ed3ba7421c3058d2b2e84ebbd89`.
This probe inherited `[0.0]` screen sizes from the preceding failed asset:
it proves the one-mesh geometry mechanism, not preservation of the authored
screen threshold. The complete candidate run must restore original generated
assets, freshly reimport ordinary source geometry, and audit that baseline.
At the source-only `d04f246` checkpoint, neither the full-kit candidate nor its
repeated import had passed in-engine. Subsequent root execution is recorded below.

Only the required Nanite usage permutation is added to each existing base
material using the pinned engine's `set_base_material_usage`; material graphs,
slot order, textures, blend/shading behavior and sidedness are retained.
The readback audits actual instance blend/shading/sidedness overrides and
requires surface, opaque/masked, DefaultLit or TwoSidedFoliage plus instanced
and Nanite usage. Unsupported/overridden cases fail rather than changing the
material. This conservative importer audit is not the engine's complete
runtime material audit; the engine log and original render comparisons still
have to establish that every intended section renders correctly.

Each successful module writes a `SORA_DOJO_NANITE_IMPORT` JSON audit into the
original editor log. Existing source FBX/texture hashes remain enforced.
The twenty-two host tests exercise rejected settings, missing built resources,
reimport reset, LOD reduction/loss, UV loss, slot remapping, collision and
material changes, malformed/nonfinite geometry, same-count position/normal/
UV0/tangent/handedness/connectivity changes, reversed winding, duplicate
triangle multiplicity, permitted ordering changes, enclosing culling bounds,
failed threshold restoration, save-time mutations, corrupt/missing/mutated
source files, false API success/source readbacks, repeated source removal,
and HiRes API side effects against the pre-import baseline. They use explicit fake
editor objects; they do not execute the importer, build an asset or prove
runtime behavior.

## Root execution at a8ecee6

On October 23, root restored and SHA256-verified all 48 original generated
files (490,372,208 bytes), then executed the importer in the isolated integration
worktree. All 12 module audits passed, with 21,984 built Nanite input triangles.
A separate editor process loaded the saved assets and matched geometry-report
hashes, metadata, material behavior, settings, source identity and Nanite counts.
A second complete import passed too; its twelve audit objects exactly match
the first run. Source and Config stayed unchanged. The current twelve modules
each have one ordinary LOD with a fresh-import screen threshold of zero; these
results preserve that fresh conventional baseline through HiRes import. They
do not establish preservation across reimport of older saved thresholds. The
earlier one-panel probe has separate evidence for retaining two. Editor CPU-access warnings remain recorded;
the CPU flag was not enabled. Startup automation self-test diagnostics are also
retained, so these are not claimed as logs without warnings or errors.

Actual Metal captures at the same source subsequently passed:

- `Saved/Capture/20261023T054521Z-sm6-60895`: METAL_SM6 on Apple M2 Ultra,
  1280×720. Root inspected all six originals. Walls, floors and ceiling have
  broad green Mask coverage and corresponding colored triangle geometry;
  the hero and other conventional objects remain red/black in those modes.
  The conservative central-region check found 319,293 green candidates at
  entry and 331,776 at ceiling, with 299,177 and 325,846 corresponding changed
  triangle pixels. These are pixel diagnostics, not GPU triangle counters.
  All 24 recorded components across the 12 assets have Nanite and fallback data.
- `Saved/Capture/20261023T054701Z-sm5-62942`: METAL_SM5 on the same M2 Ultra,
  two Lit originals. Runtime, restoration and archive checks pass. Root also
  viewed the old `20261023T013947Z-sm5-44044` originals: the candidate entry
  floor and some props are visibly darker, while the ceiling is comparable.
  Camera, recorded cvars and shader platform match; the cause remains open.
  This is not an appearance-parity pass or M1 hardware evidence.

The root reviews bind original PNGs, reports, runtime logs and imported mesh
bytes. Existing art remains unadmitted. Cooked fallback, performance, real M1
and Windows results, final material appearance and unique detailed beams are
still required. Earlier failed imports and the failed baseline draw remain
available beside the successful receipts.

The diagnostic itself does not modify generated assets. The import and SM6
results above supersede the earlier source-only state; appearance parity,
cooked fallback, performance and actual M1 behavior remain open.

## SM5 diffuse-lighting controls and existing-data observer

At `d1790c5`, repeated same-camera controls show the dark entry follows the
rebuilt mesh files: original twelve meshes restore brighter floor/props while
keeping all 36 candidate material/texture files. Actual saved property reads
find identical conventional oriented geometry, UV0, normals/tangents, nineteen
LOD build settings and five mesh properties. All twelve old saved screen
thresholds are two; fresh candidate thresholds are zero. The candidate also
enables Nanite and adds the separate HiRes source. These observations alone
cannot attribute the lighting change to any one setting.

At `9107ea7`, a separate same-source pair sets only the launch-time
`r.Lumen.DiffuseIndirect.Allow=0`; actual console readbacks confirm it. All four
originals were inspected: the large entry brightness difference disappears.
Entry/ceiling mean absolute eight-bit channel differences are 0.2995/0.1747,
diagnostic measurements without an acceptance threshold. The setting was not
saved to production configuration. A separate Nanite-disabled experiment
failed the DoorOpen bounds audit before rendering and remains a failed control.

The read-only observer integrated at `9ebcf87` records each of twelve meshes
once after compilation: existing CPU SDF validity/bounds/mip descriptors and
exact always-loaded byte MD5; streamable size/residency without loading its
payload; existing card bounds and OBBs; material/section/DF flags and Nanite
voxel masks; raw LOD0/HiRes source group bounds/counts/material correspondence.
Source getters may deserialize/cache descriptions and indexes. They do not
rebuild or save render geometry, SDFs or cards. CPU observations are not GPU
atlas residency or surface-cache coverage. The initial link failure is retained;
direct editor-only MeshDescription/StaticMeshDescription dependencies repair it.

Normal-GI paired captures at that source both pass runtime/restoration checks:
`20261023T065542Z-sm5-50677` (candidate) and
`20261023T065708Z-sm5-52741` (original twelve meshes). All four originals were
viewed; the same entry brightness difference remains. Eleven of twelve SDF
always-loaded payloads and card representations differ; the column matches.
All twelve raw LOD0 descriptions, material properties, section mappings/flags
and voxel masks match; all 37 candidate HiRes group mappings match LOD0.
Floor finest-mip bricks change from 70 to 88, with Z bounds expanding from
[-3,0] cm to approximately [-5.9,2.87] cm. Card counts are unchanged but their
OBBs differ. These measurements do not distinguish SDF versus card causality.

All 48 candidate files are restored and hash-verified after each successful
or failed control. Existing art remains unadmitted. A proposed single-floor
GI-source experiment is still a diagnostic plan, not an implemented repair.
