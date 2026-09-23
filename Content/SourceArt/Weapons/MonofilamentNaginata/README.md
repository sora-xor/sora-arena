# Samurai special naginata source art

`SM_Nyaagyu_MonofilamentNaginata` is original editable source art for catalog
weapon ID 12. The 2.311 m polearm combines a smoked-oak and indigo-lacquer
shaft, woven silk grips, bronze fittings, a forged curved blade and a small
ceramic/copper induction module. A narrow edge inlay provides the restrained
sci-fi cue. The visual design makes no claim about weapon reach, damage, bond,
NFT access or runtime readiness.

- Editable source: `Nyaagyu_MonofilamentNaginata.blend` (30 separate mesh parts)
- Exchange mesh: `SM_Nyaagyu_MonofilamentNaginata.fbx` (one UV-bearing static mesh)
- Review images: `Nyaagyu_MonofilamentNaginata_Blender.png` and
  `Nyaagyu_MonofilamentNaginata_Detail_Blender.png`
- Exact hashes, bounds, grip points, blade-tip direction, material provenance
  and license: `manifest.json`

Geometry and Principled BSDF metallic/roughness shaders are original
project-owned work. They use procedural micro-roughness and bump; no external
textures or paid assets are linked. The FBX retains material slots and UVs,
but Unreal material translation requires an in-engine art review. The declared
destination is **only** `/Game/ArtReview/Weapons`. Combat code does not load
this mesh, and the Blender renders are not Unreal gameplay captures.

Regenerate and validate from the project root:

```sh
blender -b --factory-startup --python scripts/art/create_monofilament_naginata.py
blender -b Content/SourceArt/Weapons/MonofilamentNaginata/Nyaagyu_MonofilamentNaginata.blend --python scripts/art/validate_monofilament_naginata.py
python3 scripts/unreal/validate_content.py
```
