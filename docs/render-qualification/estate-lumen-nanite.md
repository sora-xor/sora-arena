# Nyaagyu Estate renderer evidence protocol

This is a **diagnostic protocol**, not a rendering-quality claim. It changes
only temporary viewport visualization state. Do not edit meshes, materials,
lighting, `.ini` files, or gameplay to improve a capture. Run against the
current Estate content at a fixed 1280×720 viewport. Save original PNG bytes,
the unfiltered runtime log, and a literal command/readback transcript.

The release pin is **UE 5.8.3** (changelist 58210709; see
[toolchain.md](../toolchain.md)). Before opening the project, run:

```sh
python3 scripts/render/estate_render_evidence.py --platform mac preflight
```

The script checks the engine against the pin in `versions.json` through
`scripts/unreal/sora_engine_pin.py` (version, changelist, branch, installed
build and plugin versions), plus the project association and renderer
configuration. It rejects any other engine. The result records the
`Build.version` contents and file hash. Earlier archives in this directory were
captured before the 2026-09-25 re-pin and are labelled as interim diagnostics.

Use the runtime-built **Nyaagyu Estate**, not an empty level-editor map. Lock
the following two camera transforms in the diagnostic package or editor PIE;
do not move them between modes:

| Camera | World location (cm) | Pitch, yaw, roll | Horizontal FOV |
| --- | --- | --- | --- |
| Entrance | `(-2696, 0, 154.15)` | `(0, 0, 0)` degrees | 94° |
| ToriiFoot | `(-2500, 235, 90.15)` | `(-28, 0, 0)` degrees | 65° |

Wait at least two seconds after each visualization switch and allow scene
capture/streaming to settle before requesting the screenshot. Disable HUD for
every mode. Record the actual camera transform, view mode, cvar readbacks,
renderer/RHI/shader platform, screenshot request, and any failure in
`commands.txt`; retain every original UE run log. Where packaged-game
`viewmode` is gated by a CheatManager, use the editor View Modes menu or a
**disposable diagnostic-only** viewport hook that calls
`UGameViewportClient::SetViewMode` and the viewport visualization-mode setters.
Do not add such a hook to the release runtime. A failed or blank mode must be
reported as missing evidence; do not substitute a Lit frame.

For a Development package that already has a fixed Estate screenshot hook,
first try separate, otherwise identical launches using Unreal's deferred
`-ExecCmds`: `r.Lumen.Visualize 1` (Overview), `r.Lumen.Visualize 3` (Lumen
Scene), `r.Lumen.Visualize 5` (Surface Cache), and
`r.Lumen.Visualize.CardPlacement 1` (cards over Lit). The numeric modes are
defined in UE 5.8's `LumenVisualize.cpp` and do not require changing content.
`show VisualizeMeshDistanceFields` and `show VisualizeGlobalDistanceField`
toggle the respective viewport flags. Verify that the runtime log accepted
each command and that the captured pixels actually show the intended mode;
an accepted command alone is not evidence of rendered coverage.

Capture these **Mac software-Lumen/fallback** modes. Use the Level Viewport
View Modes and Show > Visualize menus where available. The equivalent 5.8
console commands are included for a disposable packaged capture hook:

| Raw filename | Viewport/console selection | Camera |
| --- | --- | --- |
| `Estate_Entrance_Lit.png` | `viewmode Lit` | Entrance |
| `Estate_Entrance_LumenOverview.png` | `viewmode VisualizeLumen`, `r.Lumen.Visualize.ViewMode Overview` | Entrance |
| `Estate_Entrance_LumenScene.png` | `viewmode VisualizeLumen`, `r.Lumen.Visualize.ViewMode LumenScene` | Entrance |
| `Estate_Entrance_LumenSurfaceCache.png` | `viewmode VisualizeLumen`, `r.Lumen.Visualize.ViewMode SurfaceCache` | Entrance |
| `Estate_Entrance_LumenCardPlacement.png` | `viewmode Lit`, `r.Lumen.Visualize.CardPlacement 1` | Entrance |
| `Estate_Entrance_MeshDistanceFields.png` | Show > Visualize > Mesh Distance Fields | Entrance |
| `Estate_Entrance_GlobalDistanceField.png` | Show > Visualize > Global Distance Field | Entrance |
| `Estate_ToriiFoot_Lit.png` | `viewmode Lit` | ToriiFoot |
| `Estate_ToriiFoot_LumenSurfaceCache.png` | `viewmode VisualizeLumen`, `r.Lumen.Visualize.ViewMode SurfaceCache` | ToriiFoot |
| `Estate_ToriiFoot_LumenCardPlacement.png` | `viewmode Lit`, `r.Lumen.Visualize.CardPlacement 1` | ToriiFoot |

Turn `r.Lumen.Visualize.CardPlacement` back to `0` before non-card captures.
Record `r.GenerateMeshDistanceFields`, `r.DynamicGlobalIlluminationMethod`,
`r.ReflectionMethod`, `r.RayTracing`, `r.Nanite`,
`r.Nanite.ProxyRenderMode`, and `r.DistanceFields.LogAtlasStats 1` output.
The last command logs distance-field atlas statistics; record any unsupported
or empty result. Close the diagnostic process after capture, which restores
all temporary view state.

On **Windows DX12 with supported Nanite hardware**, capture the eight common
Lit/Lumen frames above plus these five frames at the same two cameras:

| Raw filename | Selection | Camera |
| --- | --- | --- |
| `Estate_Entrance_NaniteMask.png` | View Modes > Nanite Visualization > Mask; or `viewmode VisualizeNanite`, `r.Nanite.Visualize Mask` | Entrance |
| `Estate_Entrance_NaniteTriangles.png` | Nanite Visualization > Triangles; or `r.Nanite.Visualize Triangles` | Entrance |
| `Estate_Entrance_NaniteClusters.png` | Nanite Visualization > Clusters; or `r.Nanite.Visualize Clusters` | Entrance |
| `Estate_Entrance_NaniteStats.png` | Lit view with `NaniteStats Primary` overlay | Entrance |
| `Estate_ToriiFoot_NaniteMask.png` | Nanite Visualization > Mask | ToriiFoot |

Preserve the `NaniteStats List` output in `runtime.log` or `commands.txt`.
Do not enable Nanite for the Mac run; its `Config/Mac/MacEngine.ini` explicitly
sets `r.Nanite=0` and `r.Nanite.ProxyRenderMode=0`. Epic lists Nanite on Apple
Silicon **M2+** as beta, while this machine is an **M1 Ultra**. The Mac run
can inspect Lumen's software path, its distance-field representation, and
the conventional Nanite fallback. It cannot establish Windows Nanite
coverage, clusters, overdraw, culling cost, MegaLights quality, RTX frame
rate, or the 1440p/60 fps production target. A Nanite-enabled source asset
alone is not evidence that Nanite rendered in a particular frame.

Inspect the **Surface Cache** view for pink uncovered regions on the gate,
walls, roofs, terrain edges, and nearby props. Compare **Lumen Scene** with
Lit for missing geometry or material mismatch, then inspect card placement
on any suspect mesh. Check Mesh/Global Distance Fields for thin, absent, or
merged occluders on the Mac path. Pink indicates missing surface-cache
coverage, but a single camera cannot prove all unseen surfaces are covered.
Card placement shows capture directions, not a count of valid radiance probes
or a performance measurement. Record observed defects by object and view;
leave the original screenshots available for independent review.

Archive without resizing, cropping, color correction, or compression:

```sh
python3 scripts/render/estate_render_evidence.py \
  --platform mac \
  --project-root /absolute/path/to/diagnostic/sora-arena \
  archive --capture-dir /absolute/path/to/raw-pngs \
  --runtime-log /absolute/path/to/lit-runtime.log \
  --runtime-log /absolute/path/to/surface-cache-runtime.log \
  --command-log /absolute/path/to/commands.txt \
  --hardware-label 'M1 Ultra, METAL_SM5' \
  --output /absolute/path/to/docs/render-qualification/estate-2026-09-24
```

Use `--platform windows` and the pinned 5.8.3 `--engine-root` for Windows.
The tool refuses missing or incorrectly sized captures and never overwrites
an existing archive. If a visualization fails, archive the available raw
evidence with `--allow-incomplete`; `manifest.json` then records
`capture_complete: false` and every missing filename. `SHA256SUMS` records
the copied PNG/log/manifest bytes. Each `--runtime-log` becomes an unmodified
`logs/run-NN.log`; `commands.txt` must map each run to its launch command and
captures. The archive is an evidence record, not an
automatic coverage score or a photoreal/AAA+ acceptance test.

Command names, coverage semantics, and platform limits follow Epic's
[Lumen Technical Details](https://dev.epicgames.com/documentation/unreal-engine/lumen-technical-details-in-unreal-engine),
[Nanite Technical Details](https://dev.epicgames.com/documentation/unreal-engine/nanite-technical-details),
and [UE 5.8 macOS rendering requirements](https://dev.epicgames.com/documentation/unreal-engine/macos-development-requirements-for-unreal-engine).
