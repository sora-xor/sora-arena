# Dojo shoji-paper source ArtReview

**Verdict: source-only study; photoreal/runtime gate failed.** The procedural
paper introduces visible relief and backlighting absent from the flat original,
but its vertical fibers repeat conspicuously at both 1 m and 3 m. The strong
backlit response is an art estimate, not measured paper transmission. No Unreal
material, runtime mesh, Dojo source module, or WorldBuilder placement changed.

## Publisher, license, and exact source

The paper-only [TextureCan Paper 0017](https://www.texturecan.com/details/281/)
is a seamless procedural shoji-paper material, not a photographed or historically
certified washi sample. The publisher's [terms](https://www.texturecan.com/terms/)
place its PBR textures under CC0 1.0 and expressly permit commercial use and
redistribution with a project or 3D asset. Four original 2K maps are retained
unaltered in `Textures/`: color, 16-bit height, 16-bit DirectX normal, and
roughness. The directly downloaded [2K archive](https://www.texturecan.com/downloads/paper_0017/paper_0017_2k_tZ5978.zip)
has SHA-256 `7e2a6fa92d0deaf187e00446108aed57af36f89535727097470d39418dc65dc9`.
Per-map hashes and the original Dojo `.blend` hash are in `manifest.json`.

The publisher did **not** supply opacity, transmission, or a real-world tile
size. The source color map is solid white; the roughness varies very little.
`paper_0017_translucency_ART_ESTIMATE_2k.png` is a separate, clearly named 2K
derivative of the height map, mapping normalized height 0.490–0.510 into a
0.22–0.52 translucent shader fraction. It is neither physical transmission
data nor evidence of historic washi construction. The candidate also assumes
a 0.64 m source tile and a warm color multiplier. These are review controls,
not sourced material properties.

[TextureCan Wood 0033](https://www.texturecan.com/details/280/) was rejected
because its shoji grid is baked into the texture, which would duplicate the
Dojo's modeled kumiko. [ambientCG Paper001](https://ambientcg.com/view?id=Paper001)
was rejected as generic paper without a characteristic fiber or translucency
model. Those alternatives were not imported.

## Study and measured comparison

`Nyaagyu_ShojiPaper0017_OneBayArtReview.blend` contains one original Dojo bay
and its candidate duplicate, 16 meshes in each collection. The paper's vertices
and every lattice, jamb, and pull geometry are unchanged. Only the candidate
paper UV0 and material differ. The source Dojo paper remains a 22 mm-thick box,
which is itself physically implausible for a paper sheet; this material study
does not correct that geometry.

Eight **unedited** 1600×900 Cycles renders use fixed 26 mm cameras 1 m and 3 m
from the bay and identical light rig within each baseline/candidate pair.
`Sun` uses a front directional source; `Backlit` uses a rear area source. The
paper-only ROI display-luma measurements in `metrics.json` are comparison
diagnostics, not radiometric tests:

| View | Baseline luma mean / std | Candidate luma mean / std | Visible result |
| --- | ---: | ---: | --- |
| 1 m, Sun | 122.7 / 0.4 | about 105 / about 2 | Narrow, repeated vertical streaks; more texture, still artificial |
| 3 m, Sun | 122.5 / 0.4 | about 105 / about 2 | Streak repetition still visible; weak facade-scale benefit |
| 1 m, Backlit | 49.4 / 0.9 | about 179 / about 3 | Strong glow, but transmission has no measured basis |
| 3 m, Backlit | 50.0 / 0.5 | about 173 / about 3 | Bright facade sheet; lacks physical calibration |

The unchanged lattice also has its own regular surface pattern. A credible
production pass needs historically appropriate paper reference photography,
fiber/formation variation at real scale, measured or art-directed transmission
against the *actual* interior and exterior lighting, and paper-thickness and
frame-construction corrections. It must then pass an unedited packaged Unreal
first-person A/B before any runtime promotion. This Blender result does not
establish Unreal appearance or the requested AAA photoreal standard.

## Reproduce and validate

From the repository root, with Python 3 plus Pillow/NumPy and Blender 5.2.2:

```sh
python3 scripts/art/derive_shoji_paper0017_translucency.py
blender -b --factory-startup --python scripts/art/create_shoji_paper0017_art_review.py
blender -b --factory-startup --python scripts/art/validate_shoji_paper0017_art_review.py
python3 scripts/art/assess_shoji_paper0017_renders.py
```

The validator checks source and render hashes, original-versus-candidate mesh
fingerprints, shared unmodified lattice meshes, material/UV0, 2K node textures,
fixed cameras, and render sizes. Blender's command-line process may exit zero
after a Python exception, so require its `SHOJI_PAPER0017_SOURCE_VALID` marker.
