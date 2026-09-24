# Nyaagyu kawara bay: isolated Unreal import gate

This is a **source-only material/form study**, not a shipping roof or an AAA+
photoreal pass. The candidate is 55 modeled honbuki-inspired tile solids in
one FBX, plus separate support and SORA eave-cap parts. The current art review
finds the tile courses too regular, the fired-clay response unmeasured, and the
SORA cap too badge-like. Its dimensions are art choices informed by a modern
manufacturer, not a verified Edo roof reconstruction. See the [source
review](../../../Content/SourceArt/Environment/NyaagyuKawaraBay/README.md).

`preflight_kawara_bay_art_review.py` verifies the FBX, the original 4×4
albedo/DirectX normal/ORM atlas, the user's exact SORA raster, the generated
color reference, and the Mac conventional fallback setting. If
`ibushi_texture_manifest.json` is present, it verifies its complete three-map
4×4 set too. A missing or changed hash fails closed. Plain preflight does not
launch Unreal or alter assets:

```sh
python3 scripts/unreal/preflight_kawara_bay_art_review.py
```

To stage the assets after the project has a compiled Editor target, use the
pinned **UE 5.8.2** engine and at least **30 GiB free**. Check that no other
heavy editor/cook/Cargo jobs are competing for disk space. The wrapper records
the editor log and requires its success marker, since `UnrealEditor-Cmd` can
exit zero despite a Python error:

```sh
python3 scripts/unreal/preflight_kawara_bay_art_review.py \
  --engine-root '/path/to/UE_5.8.2' --run
```

The locally installed UE 5.8.3 may be used **only for a diagnostic run** in a
separate linked Git worktree, with its own compiled Editor target and DDC:

```sh
python3 scripts/unreal/preflight_kawara_bay_art_review.py \
  --project-root '/path/to/diagnostic-worktree' \
  --engine-root '/Users/Shared/Epic Games/UE_5.8' \
  --allow-diagnostic-5.8.3 --run
```

The importer writes only `/Game/Generated/ArtReview/KawaraBay` and creates no
level actors. It imports the FBX as a combined StaticMesh without generated
collision, requires all five material slots, enables Windows Nanite data, and
preserves a full conventional-triangle fallback for the Mac configuration.
The two base review variants share exactly the same mesh and material-slot
layout:

| Mesh suffix | Ceramic surface | Interpretation |
| --- | --- | --- |
| `SourcePBR` | Original procedural albedo, DirectX normal, ORM | Coherent source atlas; artistic estimates |
| `ImageGenColorOnly` | Generated color with original normal/ORM | Deliberately mismatched color-only A/B; **not** the Blender correlated-bump candidate |
| `IbushiCoherentPBR` (optional) | Separate ibushi albedo, DirectX normal, ORM | Coherent three-map source candidate; still unmeasured |

Support, clay edge, and brass use their source-estimated flat PBR constants.
The SORA cap plane uses the byte-verified user logo with masked alpha. This
retains the supplied symbol but does not solve the existing flat-badge art
criticism. No lighting comparison has been run by this import script.

For a future Lit review, place each variant in a separate temporary, unsaved
review level at the same origin and camera. The Blender source review uses
camera `(1.85, -2.28, 1.96)` m aimed at `(.72, .55, .58)` m, orthographic
scale `2.05`, resolution `1360×900`, a neutral overcast world, and two soft
area lights. Record the **actual UE camera transform, lens, exposure, engine
build, renderer/scalability settings, and level hash** before comparing UE
captures. Blender-to-UE coordinate conversion and light equivalence still
need direct inspection; the Blender render is not an Unreal Lit/Lumen result.
Inspect Nanite visualization, conventional Mac fallback, UV mips, Lumen
Surface Cache/card coverage, and frame time before any runtime promotion.

At the time this path was authored, the available engine was **5.8.3**, only
**27 GiB** was free, and unrelated Cargo/rustc jobs were active. Therefore
only static preflight was run. There is no UE import, Lit screenshot, Lumen
probe/card result, or performance measurement for this candidate yet.
