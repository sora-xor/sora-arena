# Nyaagyu hero character source

`Nyaagyu_HeroCharacter.blend` is editable original source art for a feline Edo
samurai character concept/blockout. The single static `SM_Nyaagyu_HeroCharacter.fbx`
contains the visual mesh in meters, facing local +X with +Z up and its feet at
the origin. The visible chest insignia uses the **exact two paths** of the
user-supplied `Content/SourceArt/UI/sora_logo_NOtext2.svg`; the original SVG is
left unchanged. `manifest.json` pins each output and the insignia source by
SHA-256 and records authorship and limitations.

Regenerate and validate with Blender 5.2.2 LTS from the repository root:

```sh
blender -b --factory-startup --python scripts/art/create_nyaagyu_hero_character.py
blender -b Content/SourceArt/Characters/Hero/Nyaagyu_HeroCharacter.blend \
  --python scripts/art/validate_nyaagyu_hero_character.py
python3 scripts/unreal/validate_content.py
```

The two PNGs are Blender source-art review renders. The mesh is unrigged and
has no authored combat animations, fur groom, cloth simulation, or Unreal
runtime material pass. It is deliberately imported as a static visual asset
under `/Game/Generated/Meshes/SM_Nyaagyu_HeroCharacter`; it is not yet the
runtime player character or a photoreal final design. Unreal 5.8.2 import, visual quality, animation,
and performance require editor and gameplay review.
