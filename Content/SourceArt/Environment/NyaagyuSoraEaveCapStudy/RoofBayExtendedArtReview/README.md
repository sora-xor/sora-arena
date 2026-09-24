# Rear-only longer socket and iron-oxide crest — source-only comparison

This separate derivative starts from the [failed exact-source fit](../RoofBayArtReview/README.md)
and changes only the copied cap shank's rear mesh rows and review materials.
The shank extends **80 mm in its original local Y axis**, eased in from row 4
of 14. The first four rows, the cap disc, both collars, and the two molded SVG
paths retain their exact positions and topology. All cap parts remain closed,
positive-volume meshes. This derivative does **not** stretch the entire cap or
alter its original editable/FBX source. The first cover and every other roof
mesh remain untouched.

The material comparison darkens the cap body toward smoked ibushi and colors
the **real raised SORA path geometry** with an iron-oxide-like fired-clay
treatment. There is no flat badge/decal. It is a fictional resistance kamon
choice, not a claim about Edo roof ornament or historically authenticated
pigments. All color, roughness, and normal maps remain authored estimates.

![Extended socket and molded SORA material at the fixed roof camera](Nyaagyu_SORA_Extended_FixedReview.png)

The rear now tucks **9.223 mm under** the next course. Across 392 sampled
surface points, its clearance spans −2.225 to +3.779 mm and has 1.324 mm RMS
error around the intended 1.5 mm raised socket. Both **source-geometry fit
gates pass**. At the fixed review distance the red-brown SORA mark reads more
clearly and the abrupt shank termination is hidden. The front collar still
shows a material transition; kiln wear and ceramic response remain too even,
and the underlying roof/support study is not a finished environment.
**Photoreal AAA+ approval is still pending.** This has not been imported into
the game, checked under Unreal Lumen/Nanite, measured on Windows/macOS, or
reviewed for historical construction accuracy.

Rebuild and independently validate from the repository root:

```sh
blender -b --factory-startup --python scripts/art/create_nyaagyu_sora_eave_extended_review.py
blender -b --factory-startup --python scripts/art/validate_nyaagyu_sora_eave_extended_review.py
```

The validator pins the failed baseline blend by SHA-256, compares every roof
mesh and the fixed camera/lights, checks that only the rear shank rows move by
the recorded smoothstep extension, verifies the SVG-path meshes and first
four shank rows stay exact, checks closed positive volume, and recomputes the
overlap and clearance statistics. The `.blend` and image are review artifacts,
not runtime assets.
