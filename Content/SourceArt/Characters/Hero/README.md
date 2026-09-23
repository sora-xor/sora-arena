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

The eye study now has a shallow orbital seat, UV-mapped iris discs, narrow
vertical pupils, curved eyelid margins, lower lid shelves, a narrow ivory
scleral crescent and a small modeled catchlight. Its original
1024 px blue-grey radial pigment map is in `EyeStudy/` and packed into the
editable `.blend`. The close-up Blender review is
`EyeStudy/Nyaakoto_Eye_Macro_Blender.png`. This replaces the previous flat blue
eye spheres without adding material slots to the runtime's 23-slot contract.
The iris, muzzle, and generated fur coordinates now occupy primary `UVMap`
channel 0 before the source meshes are joined. Unreal's shared PBR master
samples that channel; an earlier export left the iris on channel 2 and sampled
only the dark atlas corner in gameplay. The FBX round-trip validator checks
channel 0 coverage for the eye and fur surfaces.
`scripts/unreal/import_nyaakoto_pbr.py` verifies the atlas hash and binds it
as `MI_Nyaakoto_BlueEye.AlbedoMap`; the eye slot uses a neutral tint so its
painted pigment survives Unreal's material multiplication. The other 22
material identities and both authored skeletal LODs stay unchanged. The
current face pass adds UV-mapped muzzle pads, a smaller nose with nostrils,
a philtrum, tapered whiskers with follicles, and short muzzle fur cards. The
grey fur tint is neutral to retain the authored albedo; the pale eye trim is
cool ivory. Side and eye close-ups are in `Nyaagyu_HeroFace_Blender.png` and
`EyeStudy/Nyaakoto_Eye_Macro_Blender.png`. The cheek-to-muzzle transition,
ears, fur direction, eye depth, and exposed neck remain visibly stylized.
These review renders do not establish photoreal quality or in-game
appearance; the material and deformation need Unreal and animation review. A
full transparent cornea needs a separate UE material path before it can be
added without obscuring the iris in the current opaque runtime master.

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
blender -b --factory-startup --python scripts/art/rig_nyaakoto_runtime.py
blender -b --factory-startup --python scripts/art/validate_nyaakoto_runtime_skin.py
blender -b --factory-startup --python scripts/art/generate_nyaakoto_lods.py
blender -b --factory-startup --python scripts/art/validate_nyaakoto_lods.py
python3 scripts/art/validate_nyaakoto_pbr.py
python3 scripts/unreal/validate_content.py
```

The original `Nyaagyu_HeroCharacter.blend` stays an unrigged, editable design
source and its static FBX remains in `/Game/ArtReview/Characters`. The separate
`Nyaakoto_RuntimeSkin.blend` binds its 421 authored parts to the established
20-bone samurai skeleton. Its `SK_NyaagyuSamurai.fbx` and
`A_NyaagyuSamurai_Walk.fbx` replace the orange prototype's runtime exports
under `/Game/Generated`; armor, yumi, arrows, sheathed katana and exact kamon
are rigidly weighted to appropriate bones. The campaign's proxy quiver is
shown only when the skeletal import is unavailable, avoiding a duplicate.

All PNGs are Blender art-review renders. This first skin has only idle/walk
cycles and per-part rigid weights; it still lacks production facial and combat
animation, cloth, strand groom, and an Unreal material pass. The result is
visibly closer to the supplied grey-tabby reference, but remains stylized
source art rather than a qualified photoreal shipping character. Unreal 5.8.2
import, gameplay appearance and frame rate still require review.
