# Nyaakoto head V4 — source-only anatomy study

This is an original, editable Blender study for **Nyaakoto / ニャーコト**, based on the user's small grey-tabby, blue-eyed samurai-cat reference. It is **not** the packaged game character, a rig, a production facial asset, or evidence of AAA photorealism. No game/runtime file or UE actor is changed.

## Reproduce

Requires Blender 5.2.2 LTS (the installed build used here) and Python 3 with Pillow and NumPy. From the repository root:

```sh
python3 Content/SourceArt/Characters/NyaakotoHeadV4/create_head_v4_maps.py
blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoHeadV4/create_head_v4.py
blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoHeadV4/validate_head_v4.py
```

The generator SHA-pins the project-owned V3 `.blend`; the manifest SHA-pins the output. The `.blend` retains editable meshes, vertex masks, packed PBR images, source fur curves, portrait cameras, and lighting. The FBX exports static geometry with UV0. It deliberately omits the Blender curve groom; no UE skin/groom binding, card LOD, or animation is implied. Geometry uses meters, +X muzzle forward, +Z up.

## Anatomical and surface changes from V3

- Smooth local sculpt fields on V3's **single connected head shell** reduce the lateral cheek lobes and forward bulb of the whisker-pad shelf, soften the forehead dome, and broaden the jaw-to-neck attachment. These preserve the unique UV topology rather than adding disconnected cheek or brow balls.
- The existing eye components are seated farther into the face and shortened vertically; exposed silver-looking tarsal rims now use matte fur/skin values.
- Auricles are new closed, UV-mapped front/back cartilage shells with a concave interior, tapering tip, and genuine front/back relief; their color attribute limits the warm inner skin to the bowl.
- Ten curved vibrissae arise from ten small pigment follicle papillae. The source groom has approximately 18,000 shorter, finer directional hairs, compared with V3's approximately 30,000 longer strands.
- A new 2048-square albedo retains the V3 project-owned unique-UV fibers but shifts gray islands darker relative to ivory. The new GL/DX normal and ORM are deterministic, artist-derived variations; **AO is unbaked**, roughness varies subtly, and metallic is zero. A small M-shaped forehead tabby marking is in the mesh's `CoatMix` vertex attribute, not painted as a free-floating decal.

The raw `Front`, `Profile`, and `ThreeQuarter` PNGs use V3's same 1152-square orthographic cameras, AgX view transform, exposure, and 48-sample Cycles portrait setup. Compare directly with `../NyaakotoCoatV3/Nyaakoto_CoatV3_*.png`. The older packaged facial screenshot in `docs/visual-reviews/UE583_Nyaakoto_CoatBlend_Face_Diagnostic.png` is **not** a packaged V3 or V4 A/B, so it is not used to claim a runtime improvement.

The validator found one 82,566-vertex connected facial shell after FBX round trip. In the same cheek coordinate window (`.04 < x < .15`, `1.5882 < z < 1.65`, `|y| > .07`), its maximum lateral extent changed from **119.37 mm** in V3 to **112.04 mm** in V4; the forward muzzle-window maximum changed from **206.58 mm** to **192.61 mm**. These are geometric deltas, not perceptual quality scores.

## Visual gate and known limitations

**Source iteration only; AAA photoreal gate fails.** The connected shell, restrained fur, and better seated nose/eyes offer a more coherent study than V3, but the skull is still oversized and round, eye sockets are mechanically symmetric and slightly sleepy, whisker pads and lateral cheeks retain a toy-like swelling/seam, and the lower neck remains an unfinished bust. The ear roots still show a dark mechanical join in profile even though the tip/thickness is improved. Proper ocular wetness, fur anisotropy, groom/card LOD, animation deformation, and physically calibrated skin/fur materials need an artist-led anatomy sculpt, retopology, and in-engine lighting review. The 2K artist-derived normal is not a substitute for high-resolution scanned or hand-sculpted pore/fiber relief. No inference about final performance or Mac/Windows rendering follows from Cycles renders.

V4 may be used as a **reference/editable source**, never promoted into runtime without a fixed-camera UE 5.8.2 comparison, topology/rig review, LODs, and an art-direction approval.

## Provenance and license

Original project work, revised from the repository's own pinned V3 head and coat. The user's supplied character image serves only as visual identity reference (SHA-256 in `manifest.json`); it is not embedded or traced into a texture. The albedo, roughness, and normals derive from the project-owned V3 unique-UV atlas. No third-party scans, paid assets, or restricted license content are included.
