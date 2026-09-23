# Nyaagyu Estate roadside dressing

`SM_Nyaagyu_RoadsideLeafSilt_4m` is original, visual-only ground dressing for the Estate: five uneven compacted-silt lenses, 17 small moss hummocks with modeled sprigs, 22 individually shaped stones, 126 curled leaf meshes, and 22 fallen twigs. The mesh is 4.03 m along local X, 2.15 m across local Y, and reaches 7.7 cm above its origin. Its outer soil/moss rings dip below zero and carry `EdgeBlend` vertex alpha. The original campaign terrain collision remains authoritative; disable collision on every placed visual component.

The materials use pinned 2K Poly Haven CC0 scans: project-existing `brown_mud_leaves_01` (silt), project-existing `rock_01` (stones), and `ScanForestLeaves02/` (moss and leaves). `manifest.json` records exact source URLs, authors, license, hashes, material tints, bounds, and export identity. The source blend packs all nine images. No paid or restricted asset is required.

Regenerate and verify with:

```sh
blender -b --factory-startup --python scripts/art/create_nyaagyu_ground_dressing.py
blender -b Content/SourceArt/Environment/NyaagyuGroundDressing/Nyaagyu_RoadsideLeafSilt.blend --python scripts/art/validate_nyaagyu_ground_dressing.py
```

Use `scripts/unreal/import_nyaagyu_ground_dressing.py` under the pinned UE 5.8.2 Editor to create the static mesh, two PBR masters, six instances, and nine imported scan textures (18 packages). It requests Nanite source data and a full conventional triangle fallback for macOS. The feathered material is masked and reads FBX vertex alpha; this needs an actual packaged Mac/Windows visual review before scene integration, especially at the edge of the thin silt lenses.

The two Blender reviews are [single-module](Nyaagyu_RoadsideLeafSilt_Blender.png) and [three transforms](Nyaagyu_RoadsideLeafSilt_ThreePlacements_Blender.png). They are source-art inspection images, not Unreal screenshots. The three shown transforms rotate the same asymmetric mesh 14°, 171°, and −22° and scale it 0.92, 1.04, and 0.87. Suggested sparse peripheral placement centers in Unreal centimeters are `(-2700,-1700)`, `(-2700,1700)`, `(2700,-1700)`, and `(2700,1700)`. Sample the real terrain height for Z, keep the road and combat lane clear, and inspect overlap with the pine/tree and dojo meshes in the packaged game. Avoid regularly tiled repetition.

This is a focused ground-dressing source asset, not a claim that the Estate or game has reached AAA photoreal quality. Terrain color matching, masked edge quality, lighting, texture scale, and frame cost are unqualified until the integrated render is measured.
