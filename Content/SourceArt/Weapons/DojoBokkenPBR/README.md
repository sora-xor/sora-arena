# Dojo bokken oak material study

This is an editable material and UV study of the nonlethal chapter-one bokken.
It keeps the original 16 parts, 8,208 source triangles, dimensions, and combat
geometry. The first FBX UV channel is `UV0` on every part; the oak and oiled
grip both have independently checked two-dimensional coverage. The material
uses a project-generated white-oak albedo source and deterministic authored
normal/roughness maps. [texture_manifest.json](texture_manifest.json) pins the
exact generation prompt, output ID, source hash, derived hashes, tool versions,
and rights basis. The 1,254 px generated source is resampled to 2K; upsampling
does not add real scan detail. Its roughness and normal are estimated from
color, not measured wood topography.

The same-camera [original close render](../../../../docs/visual-reviews/dojo-bokken/Bokken_Baseline_Close_Blender.png)
and [PBR close render](../../../../docs/visual-reviews/dojo-bokken/Bokken_PBRStudy_Close_Blender.png)
show a quieter, finer grain in the study. The bokken remains a simple-shaped
prop, and the source comparison does **not** pass the photoreal AAA gate.
The FBX is an ArtReview candidate. The original playable bokken is unchanged
until an unedited packaged Unreal close-up and first-person performance review
justify admission.

From the repository root, regenerate and validate with Blender 5.2.2 LTS:

```sh
python3 scripts/art/create_dojo_bokken_pbr_textures.py
blender -b --factory-startup --python scripts/art/create_dojo_bokken_pbr_study.py
blender -b --factory-startup --python scripts/art/validate_dojo_bokken_pbr_study.py
blender -b --factory-startup --python scripts/art/audit_fbx_primary_uv.py -- \
  Content/SourceArt/Weapons/DojoBokkenPBR/SM_Nyaagyu_DojoBokken_PBRStudy.fbx
blender -b --factory-startup --python scripts/art/render_dojo_bokken_pbr_comparison.py
```
