# Fern 02: Nyaagyu Estate northern shoulder study

This is a **source-art candidate**, not a placed game asset or proof of AAA visual quality. It adapts the four scanned fern clumps from [Poly Haven Fern 02](https://polyhaven.com/a/fern_02), by Rob Tuytel (scanning) and Rico Cilliers (modeling). Poly Haven publishes the asset under [CC0](https://polyhaven.com/license), including commercial use and redistribution. `manifest.json` pins the exact official CDN URLs, bytes, MD5 values reported by the API at download, and SHA-256 values of the downloaded glTF, geometry, and textures. All upstream files came from `dl.polyhaven.org`; no paid asset or other source was used for the fern.

The original four-card-clump geometry has 6,232 triangles total. The eight FBXs contain four full geometry variants with independent origins and UV0, plus four conventional Mac distance LODs totaling 3,301 triangles. Each has one material slot. The editable `.blend` retains scanned albedo, ARM, OpenGL normal, and the **separate alpha mask**; the upstream glTF's JPEG base color does not carry that alpha. DirectX normal maps are pinned for Unreal. Full textures are 4K, with official 2K maps for the Mac fallback. Fern cards are two-sided and need a masked foliage material in Unreal. The source geometry may be a Nanite candidate on supported Windows settings, but masked foliage/Nanite rendering, shadows, overdraw, wind, and Mac LOD quality still require Unreal qualification.

`Preview_Fern02_EyeHeight_SourceOnly.png` and `Preview_Fern02_MAC_Fallback_SourceOnly.png` are unedited Blender Cycles renders from a 1.63 m camera. They place eight varied instances on a northern/right leaf-silt shoulder without a repeated row. The ground uses the project's separately pinned CC0 Forest Leaves 02 scan. This is a composition study around approximately X −650 cm, Y +1450 cm, separate from the southern WaterCourt study. Its exact in-world terrain height and route clearance are **unverified**. No campaign or multiplayer collision, cover, pathfinding, or `SoraWorldBuilder` code changes are included.

The 4K scan gives much more credible frond cutouts than a flat green proxy. The preview still exposes repetitive card structure in larger clumps and a flat ground substrate, and it lacks actual Estate lighting and material behavior. **The photoreal/AAA in-game art gate remains failed.** Import into an isolated diagnostic build only if a packaged first-person A/B comparison is run; reject placement if frond edges shimmer, foliage overdraw hurts frame time, the ground intersection floats, or the off-path placement changes readability. An unnamed scan is not evidence of a historically appropriate fern species.

Regenerate and validate with Blender 5.2 LTS. Blender needs `--python-exit-code 1` because its default process exit status can otherwise be zero after a Python exception:

```sh
blender -b --factory-startup --python-exit-code 1 --python scripts/art/create_nyaagyu_fern_shoulder.py
blender -b --factory-startup --python-exit-code 1 --python scripts/art/validate_nyaagyu_fern_shoulder.py
```

`scripts/unreal/import_nyaagyu_fern_art_review.py` is pinned to **UE 5.8.2** and imports the scanned PBR/alpha maps and both mesh tiers only under `/Game/Generated/ArtReview/Fern02`. It does not place any actor or modify the Estate or game rules. The Mac LOD1 assets are independent conventional meshes with the 2K material, while Windows HI meshes request Nanite and a complete conventional fallback. Use a separate diagnostic checkout for any UE 5.8.3 experiment; do not change the release pin.
