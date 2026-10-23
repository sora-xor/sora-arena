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

## Known production blocker and minimal future enablement plan

This plan is **not implemented by the diagnostic**. Current
`scripts/unreal/import_nyaagyu_dojo_kit.py:20` says Nanite stays off, and
`:342` sets `build_nanite=False`. `SoraWorldBuilderDojoHall.cpp:28–38,56–70`
loads those same DojoKit meshes on both platforms; it does not choose the
estate HI/MAC assets. Therefore the current source predicts no Nanite dojo
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
