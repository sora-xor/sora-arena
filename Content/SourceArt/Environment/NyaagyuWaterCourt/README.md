# Nyaagyu rainwater court art study

This is editable, original Estate environment geometry. The full `SM_Nyaagyu_WaterCourt_4m` contains a hand-profiled stone catch basin, individually laid rill stones, a two-post timber/tile rain eave, three uneven bamboo groups, and moss. It is **source-only**: the posts and basin would become false cover if placed in the open shoulder without matched campaign collision, while placing the full module inside an existing dojo collider would hide it behind the dojo wall. Its fixed-camera Blender render still reads as a constructed art study, not AAA photoreal production art.

`SM_Nyaagyu_BambooRill_4m` is the foliage and shallow-rill subset. It excludes the canopy and basin and is a candidate for an off-road, collision-free Estate composition test. This is not proof that it works in-game. The [full court eye-height render](Nyaagyu_WaterCourt_EyeHeight_Blender.png), [detail render](Nyaagyu_WaterCourt_Detail_Blender.png), and [subset eye-height render](Nyaagyu_BambooRill_EyeHeight_Blender.png) are Blender source reviews, not Unreal screenshots.

The editable `.blend` retains each leaf, culm, branch, tile, and stone. The full mesh has 59,100 triangles across 2,962 source parts; the one-piece subset export has 53,540 triangles, 32 individually segmented bamboo culms, and 2,334 modeled leaf blades. UV0, material slot names, and FBX roundtrips are validated. The meshes request Nanite where available but retain their full geometry for the macOS conventional fallback. Neither has authored gameplay collision.

Materials use five pinned Poly Haven CC0 photographic PBR sets already in the project: `wood_planks_dirt`, `rock_01`, `grey_roof_tiles`, `forest_leaves_02`, and `brown_mud_leaves_01`. The two 2048² bamboo albedo/normal/ORM sets are deterministic original project maps. `manifest.json` records exact hashes, URLs, authors, material roles, bounds, and export identities. No paid or restricted source asset is required.

The court is a fictional dojo rainwater scene. [Kyoto City documents a stone water basin at Ryōan-ji](https://ja.kyoto.travel/komafuda/show.php?id=2259&lang=en), and [Kyoto's official bamboo artisan article](https://kyoto.travel/fr/travel-inspiration/bamboo-artisan-hiroaki-nakagawa-the-notsoobvious-yet-solid-role-that-bamboo-plays-in-japanese-culture/) describes multiple named bamboo-fence traditions. These are design references, not evidence that this invented arrangement reconstructs a particular Edo estate.

From the repository root, reproduce and validate with:

```sh
python3 scripts/art/create_nyaagyu_water_court_textures.py
blender -b --factory-startup --python scripts/art/create_nyaagyu_water_court.py
blender -b Content/SourceArt/Environment/NyaagyuWaterCourt/Nyaagyu_WaterCourt_Source.blend --python scripts/art/validate_nyaagyu_water_court.py
```

Only after the subset's first-person packaged visual gate passes should `scripts/unreal/import_nyaagyu_bamboo_rill.py` and a campaign-only, noncolliding WorldBuilder placement be retained. A candidate at Estate `(−1000, −1200, 2)` cm with 180° yaw leaves the center route and current cargo-cover boxes clear; it must still be checked against the dojo render, combat readability, material scale, and frame cost. The full court is deliberately excluded from the runtime import.
