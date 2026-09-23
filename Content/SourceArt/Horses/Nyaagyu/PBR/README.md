# Nyaagyu horse and tack PBR study

This is a separate material/UV variant of the [original editable horse](../README.md).
It keeps the original 135 mesh parts, 69,392 triangles, 17 material slots,
six named tack/rider anchors, and eight exact SORA kamon SVG relief objects.
Its static proportions and animation limitations remain unchanged.

The coat, tazuna/abumi leather, and blackened abumi/bit iron use three
project-generated material swatches. Each source image, generation prompt,
output identifier, rights basis, source hash, and each derived map hash is
recorded in [manifest.json](manifest.json). These are generated swatches, not
CC0 photos or measured material scans. Normal and roughness maps are
conservative authored estimates. The [OpenAI Terms of Use](https://openai.com/policies/row-terms-of-use/)
are the content-ownership basis stated in the manifest.

Regenerate and check the material study:

```sh
python3 scripts/art/create_nyaagyu_horse_pbr.py
blender -b --factory-startup --python scripts/art/create_nyaagyu_horse_pbr_variant.py
python3 scripts/art/validate_nyaagyu_horse_pbr.py
blender -b --factory-startup --python scripts/art/validate_nyaagyu_horse_pbr_variant.py
```

The Unreal importer is separate from the original-art pipeline and targets
the exact pinned engine, UE 5.8.2:

```sh
UnrealEditor-Cmd SoraArena.uproject -ExecutePythonScript=scripts/unreal/import_nyaagyu_horse_pbr.py
```

It imports `/Game/ArtReview/Horses/NyaagyuPBR/SM_Nyaagyu_HorseAndTack_PBR`,
creates one PBR master and four instances, then binds only the four authored
PBR slots by exact material-slot identity. The remaining 13 slots retain
their source material appearance. This variant is an art-review asset, not
a game-ready horse; it needs measured anatomy, a rig and gait, closer tack
construction, rider interaction, and actual engine/performance qualification.

Comparison: [before](../Nyaagyu_HorseAndTack_Blender.png) / [after](Nyaagyu_HorseAndTack_PBR_Review.png).
