# Nyaagyu hero bust study

This is a separate, unrigged visual candidate for the Nyaagyu samurai. It does not replace the existing hero character, and it is not imported into the game or included in the runtime cook. The Blender review images are source-art renders, not Unreal captures. The generated image in `../Hero/Reference` is a quality reference only; it is not sampled, projected, baked, or embedded as a material.

The source uses an original continuous 6 mm voxel-remeshed feline head, an authored vertex-color tabby coat, raycast-seated eye surfaces and lids, multi-section ear shells with concave skin, 32,155 opaque tapered fur-card triangles, a layered upper-body silhouette, stitched indigo cloth, worn lacquer plates and bronze/iron fittings. The current FBX has **102,071 triangles**, **160 editable source parts**, **20 material slots**, and bounds X `-0.2700..0.2719 m`, Y `-0.3960..0.3960 m`, Z `0.8780..1.8587 m`. Local +X is face-forward and +Z is up. `manifest.json` pins the exact hashes, material names, source Blender version, license, and geometry counts.

All source geometry, vertex colors, procedural shaders, fur cards, lighting and renders were authored for this project; no purchased or third-party mesh or texture is used. The editable source and FBX round-trip are reproducible with Blender 5.2.2 LTS:

```sh
blender -b --factory-startup --python scripts/art/create_nyaagyu_hero_bust_study.py
blender -b Content/SourceArt/Characters/HeroBustStudy/Nyaagyu_HeroBustStudy.blend --python scripts/art/validate_nyaagyu_hero_bust_study.py
```

The preview setup is Blender Cycles at 1,200 × 1,200 pixels, 32 samples with denoising. No gameplay frame rate or memory figure is claimed. The model is still visibly stylized compared with the project's photoreal reference: its muzzle and ears need artist sculpting, the coat needs a production groom or layered optimized cards, and the cloth and armor need scan-quality detail. Before gameplay use it also needs a rig, animation, LODs, two-sided fur material, Unreal material conversion, UE 5.8 import inspection, and Windows/macOS performance measurement. Treat its 102k triangles and 32k cards as a review-source complexity figure, not a shipping budget.
