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

`UE583_Estate_ToriiTerrain_Diagnostic.png` is the next unedited packaged Mac
frame at the same camera and diagnostic 25-lux key. The imported original
vermilion-lacquer albedo, DirectX normal, and ORM maps now read on the torii
posts. The authored stone route still appears as soil in the middle of the
approach, despite corrected source FBX face assignments; placement/material
diagnosis is open. SHA-256:
`32c95ba7fc5b10fd2486b500628d932e526eb1f3d0dc01ec457ea5fa341f2903`.

`UE583_Nyaakoto_RuntimePBR_Diagnostic.png` is an unedited close-up from a
subsequent packaged Mac diagnostic after the Nyaakoto master material was
explicitly marked for skeletal-mesh use. The runtime log no longer reports
default-material substitution. The camera was temporarily positioned in front
of a dojo pupil using the 23-slot Nyaakoto runtime mesh; that diagnostic
position and hidden HUD are not campaign framing. Fur, blue eyes, arrows,
armor, and SORA insignia are visible, but the separated muzzle pads, ears,
eye contour, neck, and limited animation remain stylized and fall well short
of the photoreal target. SHA-256:
`9cb58fbe3610183f6e0d3431e8d367194fe83d864b96f8cd93ce2532f9adfb72`.

These two newer captures are diagnostic UE 5.8.3/M1 Ultra evidence, not a
5.8.2 release qualification, a Windows Nanite result, or a 60-fps claim.
