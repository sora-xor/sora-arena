# Nyaakoto head and coat V3 — source-only visual study

This is an editable Blender 5.2.2 LTS study of the supplied Nyaakoto
grey-tabby/white-muzzle design, built from the project's V2 connected shell.
The user's small screenshot guides identity and color only; it is not embedded,
projected, or used as a texture. The source input SHA-256 is pinned in
`manifest.json`.

The V3 sculpt pass shortens and flattens the spherical rear cranium, narrows
the throat, softens the cheek and whisker-pad shelf, broadens the orbital
recess, and seats the eyes deeper. It replaces the triangular V2 ear blades
with curved front/back meshes, a vertex-blended ear-skin region, and fine aural
fur. A separate Blender curve groom contains 30,282 short directional guard
hairs; the static FBX intentionally omits this source groom. The shell keeps
unique UV0. New 2048 px albedo, OpenGL and DirectX normal, and ORM maps are
provided. The normal/roughness detail is **artist-derived from the
project-owned V2 albedo**, not measured surface data or a photographic scan.
ORM red is white because no reliable sculpt-to-retopo AO bake exists, green
is roughness, and blue is zero metallic. The nose and ear materials have
separate micro-bump and nonmetallic response.

Review the unedited fixed-eye-height [front](Nyaakoto_CoatV3_Front.png),
[three-quarter](Nyaakoto_CoatV3_ThreeQuarter.png), and
[profile](Nyaakoto_CoatV3_Profile.png) Cycles renders. **This visual gate
still fails.** Even after the explicit geometry and material work, the skull
and neck read as rounded manufactured forms, the brow and eyes look
mechanical, the muzzle still has a hard profile seam, and the ears look
planar from the side. The fur is more continuous at silhouette than V2 but
does not fix the underlying anatomy. The current rendered face is not
AAA photoreal, is not a rigged production character, and has not been
imported into Unreal. No in-game quality or performance claim follows.

A credible production revision needs a manually sculpted feline skull, jaw,
orbital and muzzle transition built against multiple real-cat views, then
an animation-ready retopology with deforming eyelids/jaw, painted coat
region masks and proper high-to-low bakes, groom/card LODs, and eye-height
packaged-game comparisons on both target platforms. This V3 study is
preserved as a reproducible rejected candidate rather than silently replacing
the runtime Nyaakoto.

Rebuild and validate from the repository root:

```sh
python3 Content/SourceArt/Characters/NyaakotoCoatV3/create_coat_maps.py
blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoCoatV3/create_coat_v3.py
python3 Content/SourceArt/Characters/NyaakotoCoatV3/validate_coat_maps.py
blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoCoatV3/validate_coat_v3.py
```

The .blend is the editable material, UV, mesh, and curve source. The FBX is
a static geometry interchange for review only. `manifest.json` pins all
generated deliverables and the V2 source input.
