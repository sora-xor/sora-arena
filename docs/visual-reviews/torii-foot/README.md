# Torii stone feet: packaged Estate visual review

The four linked PNGs are **unedited 1280×720 frames** from one isolated Mac
UE **5.8.3** packaged diagnostic, not UE 5.8.2 release qualification. The
release project and [strict importer](../../../scripts/unreal/import_nyaagyu_torii_foot_art_review.py)
remain pinned to UE 5.8.2; only the diagnostic worktree accepted 5.8.3. The
Mac package retained `org.sora.soraarena`, used Xcode 26.1.1 and M1 Ultra,
and ran offscreen with `-SoraArtReview`. The temporary hook spawned the mesh
at both Estate gates, X = −2250 and +2300 cm, yaw +90°, with collision and
overlap disabled. The hook and main WorldBuilder were restored afterward;
this asset has **no main-runtime placement**.

| Fixed view | Baseline | Candidate |
| --- | --- | --- |
| Entrance, camera (−2696, 0, 154.15) cm, level yaw 0°, 94° FOV | [Original blocks](UE583_ToriiFoot_Entrance_Baseline.png) | [Fitted stone feet](UE583_ToriiFoot_Entrance_Candidate.png) |
| Right post close, player (−2500, +235, 90.15) cm, camera pitched −28°, yaw 0°, 65° FOV | [Original block](UE583_ToriiFoot_Close_Baseline.png) | [Fitted stone foot](UE583_ToriiFoot_Close_Candidate.png) |

The source study has 26 editable pieces and 9,688 triangles, with two fitted
post sockets, broken stone chips, scan-sampled displacement contours, and
portable 2K diffuse/DirectX normal/ARM/displacement maps from the
[Poly Haven Mossy Rock CC0 scan](https://polyhaven.com/a/mossy_rock). Its
reopened Blender source and FBX roundtrip validator pass. The strict ArtReview
import verified all source hashes, exact material slot and PBR bindings,
Nanite source data, and a full conventional Mac fallback. Mac game compile,
1,002-package cook, stage, and package passed; the material compiled for
METAL_SM5 and METAL_SM6. The packaged Mac runtime reported SM6 unavailable
and used SM5. The FBX importer issued one missing smoothing-group warning;
there were no material shader-map failures or actor mesh-assignment warnings.
The diagnostic toolchain separately reported under 100 GiB free after other
disk activity; its `build_ready`/`cook_ready` checks passed, and no gate was
changed.

The same-package A/B confirms the mesh rendered at the actual gate. For
visibility only, the fraction of pixels with a maximum RGB-channel change
above 16 was **33.57%** in the 190×140 left-foot rectangle, **28.86%** in the
right-foot rectangle, and **59.62%** in the 340×245 close-foot rectangle.
An upper center entrance control rectangle changed **0.55%**, and a close
ground control rectangle changed **0%**. Enemy movement and temporal effects
can affect the small control difference; these fractions are not an art score.

**Visual verdict: retain the source and importer for iteration, but do not
place this candidate in gameplay.** It replaces the plain rectangular base
with a legible irregular stone socket. At the close camera, the scan's
high-contrast green striations and rough stacked silhouette read as a
separate applied boulder against the regular paving and flat, sharply bounded
ground. The entrance view changes only the two small bases; the Estate still
falls well short of the requested photoreal AAA+ quality. A revised material
scale/color and ground contact needs a new packaged comparison before
admission. No Windows Nanite or UE 5.8.2 visual/performance test was made.

[SHA-256 checksums](SHA256SUMS) cover the four original screenshot bytes and
five [compressed raw import/build/cook/stage/run logs](logs/). The package
archive itself is reproducible diagnostic output and may be cleared for disk
space once this evidence is retained.
