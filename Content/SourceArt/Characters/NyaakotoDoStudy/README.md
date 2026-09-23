# Nyaakoto formed-dō material and geometry study — source only

This editable comparison responds to the block-shaped glossy red chest armor in
the current [packaged character capture](../../../../docs/visual-reviews/UE583_Nyaakoto_CoatBlend_Face_Diagnostic.png).
It keeps the existing hero body as a fit mannequin and replaces only the twelve
boxed front plates in the *study* with seven curved, torso-fitted lacquer bands,
modeled silk odoshi crosses/eyelets, and five three-row kusazuri panels. The
chest kamon is a duplicate of the existing exact user-supplied SORA SVG mesh,
with the SVG hash pinned in `manifest.json`. The source `.blend` retains the
original plates in a hidden collection so the change is reviewable.

The project-owned 2K lacquer albedo, DirectX normal, and ORM maps are built by
`scripts/art/build_nyaakoto_do_textures.py`; no third-party bitmap was copied
into these maps. The lacquer has separate broad color variation, fine abrasion,
hem wear and roughness response. Geometry supplies the camber and plate edges.
`Nyaakoto_Do_Before.png` and the front/three-quarter after frames use a fixed
900×900 torso review studio; these are **Blender renders, not packaged game
screenshots**. Source generation and Blender→FBX round-trip pass with 146 mesh
parts and 60 editable braid curves. All linked images in the `.blend` are
portable relative paths.

The visual gate remains **failed**. The bands are a better torso silhouette
than the glossy boxes but still too regular and smooth for AAA photoreal art;
the original crossed carry pieces intersect the new shell, the surrounding
cloth and sode remain stylized, and the lower-panel fit needs an animated cat
rig. The textures require hand-painted edge wear and a high-resolution surface
pass. Historical references describe the materials and construction vocabulary,
not an exact reconstruction of one surviving armor: the [British Museum
Edo-period suit](https://www.britishmuseum.org/collection/object/A_2017-3024-1-1-14)
and the [Met Japanese armor gallery](https://www.metmuseum.org/exhibitions/listings/2009/art-of-the-samurai/photo-gallery).
The study was **not** imported into Unreal or put in gameplay. In-engine fit,
skin weighting, mobility, contact with katana/yumi, lighting and performance
remain open.

Rebuild and validate from the repository root:

```sh
python3 scripts/art/build_nyaakoto_do_textures.py
blender -b Content/SourceArt/Characters/Hero/Nyaakoto_RuntimeSkin.blend --python scripts/art/create_nyaakoto_do_study.py
blender -b Content/SourceArt/Characters/NyaakotoDoStudy/Nyaakoto_Do_Study.blend --python scripts/art/validate_nyaakoto_do_study.py
```
