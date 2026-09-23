# Nyaagyu hero stone-path study

This is an editable, **source-only visual study** for a roughly 6 × 2.9 m
section of the Estate entrance path. Its stones are separate meshes in the
Blender source and combined into one FBX for a potential Unreal import. The
existing terrain remains the only gameplay collision. **Do not place this
study in the level yet.** The eye-height review failed the visual gate: the
new slabs read as raised repaving over the existing photographed path, with
larger/brighter stones, darker joints, and a recognizable insert boundary.

The geometry creates non-repeating slabs by clipping a seeded point field,
fracturing and chipping each edge, building raised faces and recessed side
walls, and sinking perimeter stones into the existing paving. The grout bed
is a thin vertex-alpha lens shaped around the stones, not a rectangular terrain
replacement. It is still a procedural art pass, not a hand-sculpted or
photogrammetry-grade AAA stone set.

The face atlas derives aligned albedo, DirectX normal, and ARM crops from the
already hash-pinned [Poly Haven Grey Stone Path](https://polyhaven.com/a/grey_stone_path)
CC0 scan. The script selects stone interiors with at most 7.5% dark joint
pixels; each face receives a different crop. Crops are **not** rotated or
mirrored, because doing so without tangent-space vector transforms would make
the normal map physically incorrect. The side walls use the existing
[Poly Haven Rock 01](https://polyhaven.com/a/rock_01) CC0 scan. The dark joint
material uses the existing [Brown Mud Leaves 01](https://polyhaven.com/a/brown_mud_leaves_01)
CC0 scan. No new paid or restricted source art is included.

Rebuild and validate from the repository root:

```sh
python3 scripts/art/build_nyaagyu_hero_path_atlas.py
blender -b --factory-startup --python scripts/art/create_nyaagyu_hero_path.py
blender -b --factory-startup --python scripts/art/validate_nyaagyu_hero_path.py
```

The Blender renders show an oblique, overhead, and approximate eye-height
inspection over a repeated copy of the currently pinned Estate terrain scan.
They are **not** Unreal runtime images. The standalone importer is
`scripts/unreal/import_nyaagyu_hero_path.py`; it pins UE 5.8.2 and prepares
Nanite plus a full conventional mesh fallback for the M1 Mac path. It must
pass an actual 5.8.2 import, cook, and first-person visual review before any
level placement. The scan-derived 4K atlas still softens at extreme close
range, and a 6 m source patch cannot cure repetition across the full 64 m road.

To pass the visual gate, the production path needs an integrated terrain edit:
cut a matching opening in the underlying photographed path; align/sculpt slab
contours to that texture and the road's actual height field; sink the stones
until edges are flush; bake edge dirt and moss to the actual seam geometry;
blend color/roughness across the boundary under the Estate's runtime lighting;
then re-review at first-person height on both rendering presets. Repeating the
current mesh over the existing path would conceal the problem only in an
overhead asset shot, not in play.
