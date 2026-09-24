# Nyaagyu honbuki-inspired roof bay — source-only art review

This editable roof-bay study replaces a flat whole-roof pattern with **55
separate, solid, overlapping tile meshes**: 30 concave pans and 25 convex
seam covers. The lower lips are raised so the five courses have actual visible
overlap. A single eave cap uses the exact raster of the user's SORA mark,
verified against `Content/SourceArt/UI/sora_logo_manifest.json`. The model is
not in the playable Estate or any shipping build.

The proportions use [Maruei Kawara's current honbuki description and nominal
dimensions](https://eishiro.co.jp/english/products/honbuki/index.html) as a
design reference. The model uses a 0.240 m pan width, 0.303 m tile length,
0.229 m course pitch, an 0.087 m seam cover and a 1.44 m-wide six-pan bay.
The width and length come from different entries in the modern dimension
table; the seam cover and overlap are artistic choices. The page describes a
concave/convex combination and is a **modern product reference**, not proof
that these exact tiles, joinery, support members, or SORA-decorated end cap represent an Edo
samurai household. A Japanese architectural historian/roofer must review the
final design before historical-accuracy claims.

Two fixed-camera, fixed-light source renders compare only the albedo input:

- [Original generated-parameter ceramic atlas](Nyaagyu_KawaraBay_ProceduralReview.png)
  has pronounced, artificial camouflage-like blotches.
- [Image-generated ceramic color swatch](Nyaagyu_KawaraBay_ImageGenReview.png)
  has finer granular detail and reads better at this camera, but still tends
  toward clean concrete/silver paint rather than convincingly aged ibushi clay.

The image-generated swatch is a **generated color reference**, not a photograph
or measured ceramic capture. Its exact prompt is in
`T_NyaagyuKawara_ImageGenAlbedo_v1.prompt.txt` and generation ID in
`manifest.json`; it was made with the built-in image generation tool. The
paired 2K DirectX normal and ORM maps are original algorithmically painted
art estimates, and their relief does not precisely correspond to the
image-generated albedo pores. The A/B deliberately leaves those maps and all
geometry/light settings unchanged. The `.blend` saves the second, selected
source candidate; it does not confer runtime acceptance.

**Art verdict: source candidate, photoreal AAA+ gate not passed.** Roof courses
and grain now read as real geometry rather than a repeated slate photograph,
but the shapes and wear are too regular, the ceramic reflectance is unmeasured,
and the support/eave transition remains a simplified prototype. No same-camera
Unreal Lit/Lumen Surface Cache/Nanite-Mac fallback comparison, historical
review, or target-platform frame-time test has been run. The existing Dojo's
road-facing façade and playable collision are unchanged.

Rebuild from the repository root with the pinned Blender 5.2.2 LTS:

```sh
python3 scripts/art/build_nyaagyu_kawara_pbr.py
blender -b --factory-startup --python scripts/art/create_nyaagyu_kawara_bay.py
blender -b --factory-startup --python scripts/art/validate_nyaagyu_kawara_bay.py
```

The independent validator checks all manifest texture/output hashes, all 55
tile UV islands and 16 atlas cells, concave/convex cross sections, mesh counts,
and all 64 mesh parts after FBX reimport. This is source/FBX verification only;
it does not prove how Unreal will render or light the material.
