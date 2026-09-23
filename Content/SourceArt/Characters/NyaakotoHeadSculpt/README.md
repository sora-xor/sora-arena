# Nyaakoto anatomical head study — source-only, rejected for runtime

This is an original, isolated Blender source study for **Nyaakoto / ニャーコト**.
It follows the user's grey-tabby, blue-eyed cat identity and the established
character's meter coordinates (+X face forward, +Z up). The supplied character
screenshot was used only as a design reference and was **not** copied into a
texture, source file, or distributable asset. The original SORA kamon remains
unchanged on the existing character; this head study has no kamon.

The sculpt joins the cranium, facial wedge, nasal bridge, cheek, whisker pads,
mandible, and throat into one remeshed surface. Its 76,848-polygon head has a
unique UV0 albedo bake; separate cupped cartilage ears, layered eye parts,
directional mesh fur cards, follicles, and whiskers are editable in the `.blend`.
The grey, white, charcoal, and iris paint inputs are copies of existing
project-owned image-generation swatches; their provenance is documented in
[`../Hero/PBR/Source/README.md`](../Hero/PBR/Source/README.md). The baked head
albedo is an original derived texture, not a scan. [This CC0 domestic-cat skull
lateral view](https://commons.wikimedia.org/wiki/File:KATZENSCHAEDEL_LATERAL_1280x1024.jpg)
was an anatomy reference only; none of its pixels or geometry were used.

**Visual gate: failed.** Front, profile, and three-quarter Blender renders
still show overly full cheek masses, a round cranium, fin-like exposed ears,
eye assemblies that read as mechanical, and fur cards too sparse and stiff to
make a continuous feline silhouette. At the matched portrait scale these do
not meet the photoreal target or clearly surpass the packaged UE close-up in
[`docs/visual-reviews/UE583_Nyaakoto_ConnectedHead_Diagnostic.png`](../../../../docs/visual-reviews/UE583_Nyaakoto_ConnectedHead_Diagnostic.png).
This FBX is **not** a replacement for the runtime mesh, and the rendered stills
are not evidence of Unreal, animation, or game-camera quality.

To continue toward a shippable head, a character artist should sculpt the
zygomatic-to-muzzle and forehead planes from photographic feline references,
retopologize around eyes, lips, ears, and jaw, then paint a region-specific
tabby/white coat with coherent hair-flow direction. Build a layered groom or
card atlas with a soft silhouette, replace the blocky ears with rolled,
irregular cartilage and deep canal detail, and narrow the visible eye aperture
with natural tarsal margins and restrained blue iris saturation. The cornea
here is separate geometry, but its transparent shader has **not** been tested
on the M1 UE fallback or Windows.

Integration must preserve the existing 20-bone runtime rig and first-person
body scale. The head needs an artist-approved topology with eyelid loops,
mouth/jaw loops, and ear root loops; transfer `head` and `jaw` weights after
registering to the current eye centers and nose tip. Weld the throat below
the jaw into the existing neck or hide a validated seam under the armor
collar. Bake albedo, tangent normal, roughness, and AO to UV0; author card
LODs for M1 and supported Windows paths, then measure LOD pop and frame cost.
Only after rig/deformation review should the project-specific Unreal importer
and material instances be updated and packaged UE 5.8.2 portrait, campaign,
first-person, and arena captures be compared. None of these steps are done.

Regenerate and validate from the repository root:

```sh
blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoHeadSculpt/create_head_study.py
blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoHeadSculpt/validate_head_study.py
```

The generator saves an editable `.blend`, UV0 FBX, 2K baked albedo, three
review angles, and SHA-256 manifest. Blender 5.2.2 LTS was used. There is no
paid software, downloaded model, restricted texture, or marketplace asset in
this study.
