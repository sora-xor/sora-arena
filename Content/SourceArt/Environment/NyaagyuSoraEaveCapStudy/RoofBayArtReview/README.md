# Exact-source cap against the Nyaagyu roof bay — failed joint review

This derived Blender scene opens the **committed** roof-bay `.blend`, appends
the six exact source meshes from the committed molded SORA cap `.blend`, and
removes only the three older flat-badge objects in the derivative scene. The
parent roof/cap `.blend`, FBX and playable content remain unchanged. The
source Blender and FBX SHA-256 hashes are pinned in `manifest.json`.

The cap's measured shank-front width is 98.092 mm. A single **uniform scale of
0.886925** fits it to the bay's nominal 87 mm first cover; the fit solver sets
an 11.173° pitch and records the full placement transform. The cap is rendered
with the roof bay's existing camera, two area lights, Cycles settings and
1360×900 frame. The SORA paths retain the exact user SVG geometry and the
original molded-clay materials; no decal substitutes for them.

![Failed exact-source joint at the fixed roof camera](Nyaagyu_KawaraBay_SORA_Cap_FixedReview.png)

The **local surface contact passes**: 394 shank/cover samples have −1.448 to
+4.273 mm clearance, with 1.127 mm RMS error around the intended 1.5 mm
raised socket. **The actual joint fails**. The 224 mm source shank stops
**60.386 mm before** the next cover course, leaving a visible butt seam. Its
paler clay finish stands apart from the roof, and the relief has weak contrast
at the full roof-camera distance. This is a failure report, not an integrated
roof asset or a photoreal acceptance.

Rebuild and independently validate from the repository root:

```sh
blender -b --factory-startup --python scripts/art/create_nyaagyu_sora_eave_roof_fit_review.py
blender -b --factory-startup --python scripts/art/validate_nyaagyu_sora_eave_roof_fit_review.py
```

The validator hashes source/output files, checks that all 61 retained roof
meshes plus camera/lights are exact, confirms all six cap meshes are the one
rigid/uniform transform of the source including the SVG paths, and recomputes
the exposed 60 mm gap. The read-only source geometry is not historically
authenticated; no Unreal Lumen/Nanite or target-platform result exists here.
