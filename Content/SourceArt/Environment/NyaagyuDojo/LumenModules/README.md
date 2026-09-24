# Nyaagyu Dojo modular Lumen study

These four FBXs split the existing authored Dojo into logical visual modules for
a future Unreal Surface Cache/Card Placement experiment. They are **source
art only**. The released combined StaticMesh, its placement, collision, and
gameplay remain unchanged.

| Module | Editable parts | Triangles | Scope |
| --- | ---: | ---: | --- |
| Roof | 67 | 15,226 | Kawara, ridge caps, gable verge and upper gable infill |
| Eaves | 49 | 5,292 | Ceiling, exposed rafters, fascia and brackets |
| Body | 202 | 18,936 | Frame, walls, foundation and underfloor |
| Shoji | 106 | 34,492 | Front shōji, engawa, steps, signs, lanterns and SORA kamon |

The four source groups partition all 424 editable objects and 73,946 triangles
in [the original Blender file](../Nyaagyu_EstateDojo.blend). Their world-space
oriented triangle multisets, bounds, and material-face counts exactly equal
the original *before FBX serialization*. Each FBX contains the unjoined
authored objects, retaining their transforms and material slots. Temporary
stable FBX object IDs are mapped to authored part names in [manifest.json](manifest.json),
because Blender's FBX exporter truncates object names containing decimal
points. No source geometry is regenerated, filled, or retopologized.

Regenerate with Blender 5.2:

```sh
blender -b Content/SourceArt/Environment/NyaagyuDojo/Nyaagyu_EstateDojo.blend \
  --python scripts/art/create_nyaagyu_dojo_lumen_modules.py
blender -b Content/SourceArt/Environment/NyaagyuDojo/Nyaagyu_EstateDojo.blend \
  --python scripts/art/validate_nyaagyu_dojo_lumen_modules.py
```

The validator checks every imported FBX part against its source part:
polygon/vertex counts, indexed winding, face material, slot order, UV loops
and world-space vertices. The observed maximum position error after FBX
roundtrip is 0.954 µm; the allowed threshold is 2 µm. This tiny serialization
drift is why a bit-exact hash of *reimported* floating-point vertices would
be misleading. The manifest retains the exact pre-export triangle hashes.

A future isolated Unreal test must import each FBX with **Combine Meshes**
enabled and auto collision disabled, attach the four resulting visual meshes
at the current Dojo transform, and compare original/candidate Lit, Lumen
Surface Cache, Card Placement and Lumen Scene at identical warmed cameras.
It must also check triangle and material counts after Unreal import, shadows,
exposure, performance and both roof bands before considering a runtime
change. None of those Unreal checks has been performed for this split.

The Roof group has 9,334 open boundary edges across source parts; Shoji has
4,400. These counts are per-part sums, so adjacent authored pieces may
visually close some gaps. Thin/open kawara remain thin/open here, and software
Lumen distance fields may still leak or omit coverage. More StaticMeshes may
increase draw calls and card count without improving GI. The original
[asset manifest](../manifest.json) records source and license provenance:
project-owned geometry, the supplied SORA crest, CC0 Poly Haven maps and
SIL OFL font.
