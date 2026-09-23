# Nyaakoto hero character source

`Nyaagyu_HeroCharacter.blend` is editable original source art for **Nyaakoto / ニャーコト**,
the player's feline Edo samurai. The single static `SM_Nyaagyu_HeroCharacter.fbx`
contains the visual mesh in meters, facing local +X with +Z up and its feet at
the origin. The model now follows the supplied character image's grey tabby and
white face/paws, blue eyes, black-and-red layered armor, red sash, sheathed
katana, bamboo yumi, and red-fletched arrows in an open ebira quiver. The image
itself is an ephemeral user design reference (SHA-256 recorded in the manifest),
not a texture or distributable asset. Its captured HUD labels and cyan floor
are not character-design elements.

Chest, waist and both shoulder kamon use the **exact two SVG paths** of the
user-supplied `Content/SourceArt/UI/sora_logo_NOtext2.svg`; the original SVG is
left unchanged. The earlier invented ray motif on the waist was removed.
`manifest.json` pins every output and the insignia source by SHA-256.

The bow is about 2.19 m along its centerline, with the grip about one-third of
the way up from the lower tip. The open ebira, bamboo arrow shafts and
feathered ends follow the [British Museum samurai exhibit](https://www.britishmuseum.org/exhibitions/samurai/samurai-large-print-guide).
The [All Japan Kyudo Federation's equipment guidance](https://www.kyudo.jp/pdf/schedule/taikai/20240607_tebiki.pdf)
provides the present-day 221 cm size reference; historical examples vary. This
is a review pose, not a validated archery draw or carry animation.

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
under `/Game/ArtReview/Characters/SM_Nyaagyu_HeroCharacter`; it is not yet the
runtime player character or a photoreal final design. This review folder is
outside the project's always-cooked `/Game/Generated` runtime content.
Unreal 5.8.2 import, visual quality, animation,
and performance require editor and gameplay review.
