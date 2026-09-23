# Nyaakoto facial anatomy V2 — source-only, visual gate failed

This editable Blender candidate revises the earlier [head study](../NyaakotoHeadSculpt/README.md) without changing the Unreal character. It keeps the supplied Nyaakoto image's grey tabby, white muzzle, and blue eyes as design cues; the screenshot is not copied into the model or textures. The geometry, UV0 baked 2K albedo, iris, and material setup are original project work. The coat swatches already in `../Hero/PBR` are packed in the `.blend`; their provenance is recorded in that folder. No paid or downloaded model is used.

The revised shell has a smaller adult-cat cranial dome, lower whisker pads, a joined throat, and measured orbital recesses. The ocular geometry moves about 25 mm rearward compared with V1 so it sits closer to the sculpt surface. Separate cupped ears have tapered cartilage and a graded inner-color mask. Directional fur cards are shortened from 4–12 mm to 1.8–4.8 mm, avoiding the most obvious quill silhouette. All forms remain editable, and the FBX round trip preserves UV0 on 118 meshes. This is a neutral head study, not a game-rigged character or groom.

The [front](Nyaakoto_AnatomyV2_Front.png), [profile](Nyaakoto_AnatomyV2_Profile.png), and [three-quarter](Nyaakoto_AnatomyV2_ThreeQuarter.png) renders are unedited Blender Cycles frames at 960 px. **The visual gate still fails.** The dome and cheek construction read as a toy, the muzzle is detached-looking in profile, the ear bowls are too planar and clean, the eye edges remain mechanical, and the neck reads as a vertical column. Short mesh cards and procedural albedo alone cannot reproduce a continuous fur coat. These images cannot establish AAA photorealism or Unreal quality; this study is not approved for runtime integration.

A production revision needs feline anatomy sculpting against multiple photographic views, retopology around lids, muzzle, ears, and jaw, a painted region-specific tabby coat with tangent normal/roughness/AO maps, and a real groom/card LOD system. It must then be registered to the existing 20-bone Nyaakoto rig, tested for eye/jaw deformation and neck seam continuity, and compared in packaged UE at game-camera distances on Windows and macOS. None of that qualification is complete.

Rebuild and validate from the repository root with Blender 5.2.2 LTS:

```sh
blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoAnatomyV2/create_anatomy_v2.py
blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoAnatomyV2/validate_anatomy_v2.py
```

The manifest records SHA-256 hashes for the editable source, FBX, bake, and review frames. Regenerating the study rewrites those hashes.
