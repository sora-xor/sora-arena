# Nyaagyu Estate Lumen diagnostic: entrance coverage gap

**The entrance Surface Cache check fails.** The unedited Surface Cache frame
shows visible magenta along both upper eaves/roof-edge regions and several
high foliage/prop patches. In Epic's [Lumen coverage definition](https://dev.epicgames.com/documentation/unreal-engine/lumen-technical-details-in-unreal-engine),
pink marks missing Surface Cache coverage; the associated surfaces cannot
contribute normal cached bounce lighting. This view identifies places to
inspect in the mesh-card setup. It does not establish every unseen surface's
coverage, and it is not a quantitative lighting or photorealism score.

These **seven original 1280×720 PNGs** were captured from the same fixed
Estate entrance view: camera `(-2696, 0, 154.15)` cm, pitch/yaw/roll `0°`,
94° FOV. Each view used a fresh offscreen Development package launch with an
Unreal `-ExecCmds` visualization value; its existing `-SoraArtReview` hook
used an in-memory first-chapter save and requested the entrance screenshot.
The screenshot bytes were copied without image edits immediately after each
launch. The package's temporary Bokken study branch was **not** selected.
No source, gameplay rule, asset, light, scalability setting, or `.ini` value
was changed for this diagnostic.

| Evidence | What it shows |
| --- | --- |
| [Lit](Estate_Entrance_Lit.png) | Gameplay scene at the entrance |
| [Lumen Overview](Estate_Entrance_LumenOverview.png) | Overview tiles explicitly include Reflection View `SWRT` and a Surface Cache tile |
| [Lumen Scene](Estate_Entrance_LumenScene.png) | Software-Lumen scene representation; the first-person weapon is absent/black here |
| [Surface Cache](Estate_Entrance_LumenSurfaceCache.png) | Magenta uncovered patches at upper eaves/roof edges and high foliage/props; yellow foreground weapon is culled from this representation |
| [Card Placement](Estate_Entrance_LumenCardPlacement.png) | Actual mesh-card bounds/capture positions, including large gate-region cards and many modules |
| [Mesh Distance Fields](Estate_Entrance_MeshDistanceFields.png) | Per-mesh distance-field representation used by the software path |
| [Global Distance Field](Estate_Entrance_GlobalDistanceField.png) | Merged distance-field representation of the entrance |

The complete [command-to-file transcript](commands.txt), [manifest](manifest.json),
and seven unfiltered [packaged run logs](logs/) are archived. Every runtime
log reports the same camera coordinates and `METAL_SM5`. The Lumen Overview
tile labels its reflection view `SWRT`; the two distance-field modes rendered
distinct representations, so this run demonstrates the Mac software-Lumen
diagnostic path rather than merely finding a project setting. We requested
`r.DistanceFields.LogAtlasStats 1` in the two distance-field launches, but
no atlas-stat line appeared in their captured stdout; no atlas-memory claim
follows from this run. [SHA-256 checksums](SHA256SUMS) verify the copied PNGs,
logs, manifest, and this assessment.

The package binary hash is
`1f5e5675cb8a32087ffa39f6f283faddd8bf4ed8ca239510a794e1e216d29861`
from the Bokken staged Mac diagnostic. The host is a Mac Studio with Apple
M1 Ultra, macOS 27.0 (26A428), and 128 GiB memory. `Build.version` records
**UE 5.8.3 CL 58210709**; this is an interim diagnostic, while the project
release pin remains **5.8.2**, without a verified source-commit pin. The
package chose Metal SM5 at runtime after logging an SM6 fallback. The
diagnostic checkout had other agents' uncommitted content, recorded as dirty
in the manifest; the results apply to this exact staged binary/content,
not to a clean release build.

The read-only staged hook exposed the entrance camera but not the protocol's
fixed **ToriiFoot close camera**. The [manifest](manifest.json) therefore
marks the three missing close views and `capture_complete: false`. A close
card/Surface Cache inspection remains necessary before claiming local gate
coverage. The local Mac config has `r.Nanite=0` with fallback rendering and
`r.RayTracing=False`; Epic lists Nanite on Apple Silicon M2+ as beta, while
this host is M1 Ultra. This run cannot establish Windows Nanite Mask,
triangles, cluster/overdraw statistics, `NaniteStats`, RTX 4070-class
performance, the 1440p/60 fps target, or full UE 5.8.2 release behavior.
Those require the separately specified Windows hardware/engine run; see the
[capture protocol](../estate-lumen-nanite.md) and Epic's
[Nanite](https://dev.epicgames.com/documentation/unreal-engine/nanite-technical-details)
and [macOS feature table](https://dev.epicgames.com/documentation/unreal-engine/macos-development-requirements-for-unreal-engine).

The [toolchain doctor output](toolchain-doctor.json) was captured after the
frames. It reports 44.3 GiB free, below the existing 100 GiB planning item,
so `all_checks_pass=false`; `build_ready` and `cook_ready` remain true. No
threshold was changed, and this capture reused the already staged package
without a new build, cook, or stage.
