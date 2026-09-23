# Nyaagyu Estate pine saplings

These three scanned pine sapling forms come from [Poly Haven's Pine Sapling
Small](https://polyhaven.com/a/pine_sapling_small), credited to Rico Cilliers
and Rob Tuytel under [CC0](https://polyhaven.com/license). The project stores
the original 1K glTF/geometry and linked textures with hashes in `manifest.json`.
The distinct 2K bark and needle PBR maps are pinned separately. The needle
material uses the white-on-black `twig_mask` as its opacity cutout; the supplied
`twig_alpha` map is retained for provenance, but has the opposite background.

Run `blender -b --factory-startup --python scripts/art/create_nyaagyu_pine_saplings.py`
to regenerate the six FBXs and editable `.blend`, then run
`scripts/art/validate_nyaagyu_pine_saplings.py` for independent FBX validation.
The HI meshes use Nanite on supported Windows configurations. The MAC meshes
are conventional static geometry with the same two PBR zones and needle mask.

| Form | HI triangles | MAC triangles |
| --- | ---: | ---: |
| A | 88,558 | 26,945 |
| B | 75,970 | 23,131 |
| C | 82,910 | 25,242 |

Nine instances are placed between the Estate buildings. They have no collision
or overlap events and are absent from P2P practice maps. Their exact botanical
species is not asserted beyond pine; art reference and Edo vegetation review
remain necessary. Source scans and previews alone do not establish an in-game
photoreal or frame-rate qualification.
