# Nyaagyu SORA molded ceramic eave cap — source-only art study

This replaces the earlier roof-bay study's flat red SORA decal with a separate
**physical ceramic end piece**. The 130 mm disc has a raised rolled rim, an
incised transition, small kiln asymmetry, and a solid vaulted cover section
behind it. Two molded crest pieces are built by importing the **exact
user-supplied** `sora_logo_NOtext2.svg` paths, normalizing their 350.9-unit
mark to 93 mm, then giving the filled paths 3.6 mm thickness and a softened
edge. The mark is visible through its real silhouette, relief and cast shadow;
there is no red paint plane, alpha cutout or logo texture on the cap.

The editable `Nyaagyu_SORA_EaveCap.blend`, six-part
`SM_Nyaagyu_SORA_EaveCap.fbx`, and fixed-camera
`Nyaagyu_SORA_EaveCap_FixedReview.png` are **source candidates only**. The
review board is in a separate collection and is not exported. The FBX needs
new Unreal import, material, Lumen/Nanite, distance, and target-platform
reviews before it can replace the old cap in the playable Estate or the roof
bay. The 98 mm vaulted shank and 130 mm face intentionally exceed the existing
roof bay's 87 mm cover; the junction must be fitted, not simply snapped into
that source scene.

The 1K albedo, OpenGL normal, and ORM images are original, deterministic
**estimated** ibushi-clay maps. They use multiscale painted grain, tiny chips
and a mild smoked edge. They are not photographs, ceramic scans or measured
BRDF data; the normal and roughness are authored estimates. The crest uses
the same ceramic maps with slightly worn high-point finish, not metal. Unreal
DirectX normal import needs the green channel inverted. The render uses fixed
AgX tone mapping, an overcast world, a cool area key and restrained lantern
bounce, and Blender Eevee. It does not demonstrate final in-game lighting.

The cap is a fictional SORA resistance ornament. Its exact dimensions,
construction, wear, and use on a Nyaagyu household are art direction rather
than authenticated Edo-period roof practice. The adjacent bay takes general
concave/convex form inspiration from a [modern Maruei honbuki product
description](https://eishiro.co.jp/english/products/honbuki/index.html), which
does not authenticate this crest or historical installation. Obtain a
Japanese architectural historian/roofer review before asserting historical
accuracy.

Rebuild from the repository root with Blender 5.2.2 LTS and Python/Pillow:

```sh
python3 scripts/art/build_nyaagyu_sora_eave_cap_maps.py
blender -b --factory-startup --python scripts/art/create_nyaagyu_sora_eave_cap_study.py
blender -b --factory-startup --python scripts/art/validate_nyaagyu_sora_eave_cap_study.py
```

The validator hashes the user SVG and outputs, independently imports the two
SVG paths to compare the filled crest areas, checks every exported mesh for
closed positive-volume geometry, and compares source/FBX world vertices,
materials and UV coordinates. The current check passes for all six meshes
(11,100 triangles). The molded front face areas differ from the original
filled SVG paths by 0.36% and 0.15%, and maximum FBX world-vertex round-trip
error is 0.04 µm. This establishes reproducible modeled geometry only.
**Photoreal AAA+ approval is pending:** the clay response is estimated,
aging is still regular, and no Unreal same-camera Lumen/Nanite/Mac fallback or
historical review has passed.
