# Nyaagyu torii stone-foot study

The first-person Estate entrance keeps the authored red gate but exposes its
simple stone footings close to the camera. This study sculpts two fitted,
chipped stone sockets at the gate's exact local post centers (x = ±2.35 m),
with small detached talus pieces. The source contains 26 editable mesh parts,
explicit UVs, and a single visual-only FBX; it does **not** change the simple
gameplay collision. Both feet cover the existing plain .55 × .53 × .44 m
footing rather than moving the gate or changing its SORA kamon.

The surface uses the [Poly Haven Mossy Rock scan](https://polyhaven.com/a/mossy_rock)
at 2K: diffuse, DirectX normal, ARM, and displacement are pinned in
`manifest.json`. Poly Haven publishes this asset under CC0. The scanned maps
provide microstructure; the irregular stepped profile, chipped rim and rock
debris are modeled geometry. The source `.blend` links to files in `MossyRock`
by relative path. No source asset with an extraction-restricted license is
included.

`ToriiFoot_Before_Blender.png` and `ToriiFoot_After_Blender.png` use a controlled
camera and a proxy post to show the source geometry change. They are **not**
Unreal game frames. The material appears too crisply striated in this source
render and will need a packaged fixed-camera check under Estate lighting.
Keep this candidate source-only until an unedited packaged UE5.8.3 comparison
proves it improves the in-game entrance and close views. The target release
still requires UE5.8.2 and independent Windows/macOS performance qualification.

Generate and validate:

```sh
blender -b --factory-startup --python scripts/art/create_nyaagyu_torii_foot_study.py
blender -b Content/SourceArt/Environment/NyaagyuToriiFootStudy/Nyaagyu_ToriiFoot_Study.blend --python scripts/art/validate_nyaagyu_torii_foot_study.py
```
