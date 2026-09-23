# SORA kamon in runtime source art

The user-supplied `Content/SourceArt/UI/sora_logo_NOtext2.svg` is the clan
kamon. Its SHA-256 is
`d66413a71b70e25dcb8b2f118dcfe846a6446ed1db3de53ce88fc70c16ac0910`.
The procedural art generators refuse a changed SVG or manifest. They import
its **two original filled paths** through Blender's SVG importer, transform
them uniformly, and never redraw or simplify the symbol.

The older runtime `SM_NyaagyuSamurai` / `SK_NyaagyuSamurai` prototype now has
the exact mark on its headband and a backed chest roundel. The ID 1 Arc carbine
has the same mark on both receiver cheeks. The earlier generic `Clan_mon`
sphere and `Crest_Whisker` / `Crest_Nose` pieces were removed. This is in
addition to the separate Nyaakoto hero artwork, gate and UI use of the SVG.

To regenerate the editable character source, static FBX, skeletal FBX, keyed
walk FBX and Blender review image with Blender 5.2.2 LTS:

```sh
blender -b --factory-startup --python scripts/art/create_original_assets.py -- --render
blender -b --factory-startup --python scripts/art/rig_original_cats.py
blender -b Content/SourceArt/SoraArena_OriginalAssets.blend --python scripts/art/validate_original_sora_kamon.py
```

For the carbine:

```sh
blender -b --factory-startup --python scripts/art/create_arc_carbine.py
blender -b Content/SourceArt/Weapons/Original/Nyaagyu_ArcCarbine.blend --python scripts/art/validate_arc_carbine.py
```

The validators reimport the pinned SVG independently. They compare every
tessellated path vertex with the Blender source mesh and ensure it survives both
static and skinned FBX round trips; they also check placement metadata and asset hashes. The
checked previews are **Blender art-review renders**. The regenerated meshes
still require Unreal reimport, Mac/Windows cook and in-game lighting,
distance-readability and performance review before they count as updated
cooked runtime content. The old samurai mesh remains a prototype rather than
the finished photoreal Nyaakoto character. User reference screenshots stay
outside Git.
