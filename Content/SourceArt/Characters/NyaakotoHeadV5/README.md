# Nyaakoto V5 adult-cat form study — source only

This is one editable, non-runtime head study for Nyaakoto. It starts from the SHA-pinned, project-owned V4 `.blend`, not from a third-party scan. It was visually guided by [Neo_minigan's *Cat (Take 2)* photogrammetry of a real domestic cat](https://sketchfab.com/3d-models/cat-take-2-2996f59c517245aa91cf513a5624935e), which is designated [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Reference credit: **Neo_minigan, “Cat (Take 2),” Sketchfab, CC BY 4.0; visually consulted for feline head proportions; no scan vertices or textures copied.** The GLB remains private/outside the repository. See [the acquisition check](../../../../docs/art-research/nyaakoto-real-cat-scan-acquisition.md) for its recorded SHA and archive evaluation.

The public preview of [snacksthecat's *Photogrammetry Experiment: Cat's Face*](https://sketchfab.com/3d-models/photogrammetry-experiment-cats-face-dc453003896b4f53846630900c35e7dc), also listed CC BY 4.0, was a second *visual-only* reference for the open-eye orbit, shallow cheek-to-muzzle transition and ear root. **Credit: snacksthecat, “Photogrammetry Experiment: Cat's Face,” Sketchfab, CC BY 4.0.** Its authenticated archive was unavailable, so no geometry or texture from it was used.

## Rebuild

Blender 5.2.2 LTS and Python 3 with NumPy/Pillow were used. Run from the repository root:

```sh
python3 Content/SourceArt/Characters/NyaakotoHeadV5/create_head_v5_maps.py
blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoHeadV5/create_head_v5.py
blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoHeadV5/validate_head_v5.py
```

The `.blend` contains an editable connected head shell, separate eyes/nose/follicles/ears, V4 short guard-curve groom, packed unique-UV images, portrait rig, and materials. The FBX contains only static UV geometry. Facial rig, game skinning, eye wetness, groom/card export and LODs are absent. Units are meters, +X is muzzle forward, +Z up.

The 2048² `T_Nyaakoto_HeadV5_Albedo.png` is a modest grade of the project-owned V4 coat atlas. V4's artist-derived `NormalGL`, `NormalDX`, and `ORM` remain companion maps in `../NyaakotoHeadV4/`; the Blender source has its required images packed. There is **no measured scan-derived roughness or normal map** in V5. The FBX's texture path mode strips external paths; a future importer must explicitly bind the V5 albedo with those V4 companion maps.

## Fixed-light comparison and measurable form change

`Nyaakoto_HeadV5_Front.png`, `_Profile.png`, and `_ThreeQuarter.png` use the identical V4 1152×1152 orthographic camera positions/target, AgX look, exposure, world value and 48-sample Cycles lighting. Compare directly with `../NyaakotoHeadV4/Nyaakoto_HeadV4_*.png`.

| View | V4 raw frame | V5 raw frame |
|---|---|---|
| Front | [V4](../NyaakotoHeadV4/Nyaakoto_HeadV4_Front.png) | [V5](Nyaakoto_HeadV5_Front.png) |
| Profile | [V4](../NyaakotoHeadV4/Nyaakoto_HeadV4_Profile.png) | [V5](Nyaakoto_HeadV5_Profile.png) |
| Three-quarter | [V4](../NyaakotoHeadV4/Nyaakoto_HeadV4_ThreeQuarter.png) | [V5](Nyaakoto_HeadV5_ThreeQuarter.png) |

The central bridge maximum in `1.65 < z < 1.69, |y| < .025` dropped from approximately 215 mm in V4 to **176 mm** in V5. The lateral cheek maximum in `.04 < x < .15, 1.5882 < z < 1.65, |y| > .07` dropped from **112 mm** to **91 mm**. The head retains one connected **82,566-vertex** shell and UV0. These numbers verify a meaningful sculpt change; they do not certify anatomical fidelity.

## Art verdict: fail

**V5 still fails the same-light adult-cat/AAA photoreal profile gate and must not be promoted to runtime.** The bridge and skull are less inflated than V4, and the nose is smaller relative to the face, but the side view still shows a distinct capsule-like cheek, protruding brow tube, a steep angular nasal plane, and an abrupt jaw/throat seam. The new ear roots still read as separate slabs at the crown, despite being buried more deeply. The eyes look rigid and overly symmetric; the coat is diffuse and soft rather than truly groomed. The face still resembles a sculpted toy more than Neo_minigan's real cat or the user's Nyaakoto image.

Another primitive/parametric derivative of the V4 shell is unlikely to reach the requested adult-cat photoreal target: its characteristic brow, cheek and ear-root topology are built into the starting form. The next viable route is an authorized **licensed open-eye real-cat scan** used as multi-angle anatomical reference, followed by a character artist's original sculpt and clean retopology, open-eye expression/eyelid/cornea detail, grooms/cards, measured material response, rigging, and fixed-camera UE 5.8.2 A/B. Preserve exact creator/license provenance for any actual scan-derived work. This pass is a rejected source experiment that identifies those limits. No inference about packaged game quality or frame rate follows from these offline renders.
