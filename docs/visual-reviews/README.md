# In-engine visual reviews

`UE583_Estate_25lux_Diagnostic.png` is an unedited 1280×720 screenshot from a
packaged macOS **UE 5.8.3 diagnostic** build, captured on 2026-09-24 JST with
the camera held level at the Nyaagyu Estate campaign entrance. The review
build used a diagnostic-only 25-lux Estate sun override, hid the HUD for this
frame, and retained the imported prototype scene assets. It is **gameplay rendering**, not
the separate generated menu key art or a Blender source preview. The package
log reported `METAL_SM5` on the available M1 Ultra; the release pin remains
UE 5.8.2. Image SHA-256:
`9727552e80c75dd3ec91911e77ae65993452c9898811e1456f6bd167edd278fd`.

This frame confirms visible imported geometry and PBR materials, and exposes
remaining problems: repeated path/soil patterns, simple distant buildings and
characters, and underdeveloped first-person animation. It does not qualify
photoreal AAA art, Lumen probe coverage, Nanite on Windows, frame rate,
cross-platform parity, gameplay balance, or release packaging. Capture a
comparable gameplay frame after each material/geometry revision and measure
the configured target presets on the specified hardware.
