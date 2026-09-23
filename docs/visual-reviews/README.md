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

`UE583_Nyaakoto_UV0_Diagnostic.png` is an unedited packaged Mac frame of the
same close-up and 25-lux diagnostic setup after correcting the character FBX's
primary UV channel. The previous iris sampled one dark corner of its painted
atlas because its authored coordinates exported on channel 2; parts of the fur
and muzzle had the same channel mismatch. The blue irises and fine fur texture
now render in gameplay. This fixes a material integration defect, while the
separate white muzzle and cheek forms, cylindrical neck, simple ears, dark eye
sockets, and rigid armor still read as stylized. SHA-256:
`8a85ad9f2d12cb1f3afd79652470e12f1831a6e973df2e9529e393d142179f7c`.

`UE583_Estate_RoadCargo_Diagnostic.png` is an unedited packaged Mac frame
after correcting the terrain FBX export orientation and replacing twelve
visible cover cubes with an original cargo-stack mesh. The photographed stone
route now runs between the torii, while the established simple collision is
unchanged. The regular paving and empty broad terrain remain plainly visible.
SHA-256:
`e73dd5e06e7f3a5484c26b123957dea1fa09e387bf8093ed14ed47f3ff5f4bdf`.

`UE583_Estate_Wall_Diagnostic.png` is the next unedited packaged Mac frame
at the same entrance camera and diagnostic 25-lux key. Fifty-eight original
four-metre wall modules replace the four visible perimeter boxes, using
licensed CC0 scanned stone, plaster, timber, and tile maps. The original
perimeter collision stays in place. The modules and materials load without
runtime asset errors, but repeated wall sections, sparse scene dressing, and
the character's stylized anatomy still miss the photoreal target. SHA-256:
`9ae91b59d78046e1bb7fc12e40d6eb688d64457158741ec5532f2d2a65a67375`.

These newer captures are diagnostic UE 5.8.3/M1 Ultra evidence, not a
5.8.2 release qualification, a Windows Nanite result, or a 60-fps claim.

`UE583_Estate_GreyStonePath_Fixed_Diagnostic.png`,
`UE583_Nyaakoto_ConnectedHead_Diagnostic.png`, and
`UE583_Estate_GreyStonePath_Close_Diagnostic.png` are unedited frames from a
new packaged Mac diagnostic after importing the irregular Grey Stone Path
scan and a connected-head Nyaakoto source pass. The first is the HUD-free
entrance, the second a deliberate close character inspection, and the third a
downward view of the pathway. The material graph initially failed Metal shader
compilation because a component mask requested alpha from a float3 output;
the first package showed checkerboard terrain and black torii. The corrected
graph uses the vertex-color alpha output directly. The repaired cook/stage and
game launch passed, and the cook/runtime logs contain no failed material
compilation or invalid shader-map messages. Image SHA-256 values, in the same
order: `d7773c2ed5de904082ffd8e0e7944f706570f832d3b5d5f1b5d8f9614d76650e`,
`96ccc07a508eeb1d464da395f3220fa335f7ffa3578ec5382cfe85bb298bf119`,
and `3d88eba27ae366ba49eb2de359164454a94a88834257ffc9bd764d835854dbdd`.
The path now has convincing local photographed detail, but its repeated tile
layout remains obvious at a distance. Nyaakoto's head is topologically
connected and textured, yet the eyes, ears, neck, mouth, and armor still read
as stylized. The sparse courtyard and regular wall sections also miss the
photoreal target. These frames are art diagnostics, not acceptance evidence
for the stated AAA, performance, Nanite, or exact UE 5.8.2 release gates.

`UE583_Estate_PathQuilt_Entrance_FailedGate.png` and
`UE583_Estate_PathQuilt_Close_FailedGate.png` are unedited 1280×720 frames
from a packaged UE **5.8.3** Mac diagnostic with a 4K co-registered 7.2 m
path quilt derived from the same pinned CC0 stone scan. The first is the
level entrance with HUD hidden; the second looks down at the path from
player eye height. The offscreen `-SoraArtReview` capture used a transient
chapter-one review save and did not write the campaign slot. The combined
Mac cook/stage completed with zero cook warnings or errors, and runtime
requested both named PNGs. SHA-256 values respectively:
`cf99c4b974ec89c14338b24aad47666bf8e447217f7edb3a09d15f435355d58f`
and `4fe170ab24e002d18ad0b0839a9ce10c591225aa651257a388a671050a848f28`.
Compared with the earlier 1.8 m close frame, the entrance's exact tiling is
less obvious, but the close frame still repeats distinctive stone forms
across its width and is softer. The broad route still looks regular. The
visual gate **failed**, so this atlas is source-only and the main project
retains the original terrain material/mesh. Neither frame qualifies the
photoreal target or the exact UE 5.8.2 release build.

`UE583_Estate_RoadsideDressing_Diagnostic.png` is an unedited packaged Mac
frame after seven collision-free placements from the original ground-dressing
mesh were added beside the route. The limited patch is visible on the right
side of the approach. It adds close-scale stone and silt variation but does
not materially change the broad, sparse composition; the repeated path,
regular walls, simple characters, and flat terrain still fail the AAA
photoreal art gate. The package used UE 5.8.3 only for a diagnostic on M1
Ultra. SHA-256:
`dfb0b9d2439b5e2f3288a631bb8fa3b19e92bb0e956bc48871d930128b504a37`.

The [bamboo/rill Estate comparison](bamboo-rill/README.md) archives unedited
fixed-camera before/after and close-route frames from an isolated packaged UE
5.8.3 Mac diagnostic. The collision-free southern-shoulder candidate was
mostly hidden behind the foreground torii/building; its rill was invisible
from the route. Its first-person visual gate failed, so the placement was
removed and the water-court art remains source-only.

`UE583_Nyaakoto_CoatBlend_Body_Diagnostic.png` and
`UE583_Nyaakoto_CoatBlend_Face_Diagnostic.png` are unedited frames from an
offscreen packaged UE 5.8.3/METAL_SM5 Mac game. A diagnostic-only command-line
capture entered the first campaign chapter, hid the HUD, and moved the camera
for fixed body and face reviews without touching a player's save. The
six-texture grey/white fur master compiled and the imported skeletal mesh
retained vertex colors and all three authored LODs; the package cooked 898
packages with zero errors and warnings. These frames nevertheless **fail the
photoreal character art gate**: the head is still round and toy-like, the
ears and eyes are flat, the white throat meets a hard seam, the armor is rigid,
and the fur lacks a convincing silhouette. Shader validity is not visual
quality. The photos also do not establish the exact UE 5.8.2 or Windows gates.
SHA-256 values, in filename order:
`8088a847bd4c23ef59d225041eb3b256c899edf01372065141c7c1d59b234b1d`,
`95f34a2f3bf678b84c8c2406d0207331462f6e705076ecc11fef779178c222ed`.
