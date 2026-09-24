# SORA Arena photoreal visual acceptance

The user's target is a finished, photoreal AAA+ game. A mesh import, a Nanite
flag, a material graph, and a Blender render do not establish that outcome.
This record names the current **in-game visual failures** and the captures
needed before art is admitted to the playable release. The separate
[render protocol](../render-qualification/estate-lumen-nanite.md) covers Lumen
and Nanite diagnostics. The release engine is UE 5.8.2; UE 5.8.3 evidence is
interim only.

| Subject | Current checked evidence | Admission gate |
| --- | --- | --- |
| Nyaakoto's face, fur and samurai kit | [Packaged close face](../visual-reviews/UE583_Nyaakoto_CoatBlend_Face_Diagnostic.png) reads as a round toy-like cat; both [V4](../../Content/SourceArt/Characters/NyaakotoHeadV4/README.md) and [V5](../../Content/SourceArt/Characters/NyaakotoHeadV5/README.md) source heads fail fixed-light front/profile review. | Same-camera 1 m and 3 m unedited UE views from front, profile and three-quarter in neutral and Estate light. Brow, lids, muzzle, ear roots, coat breakup, groom silhouette, deformation and armor must hold up without toy-like seams; record Mac and Windows frame cost. Compare against the user's Nyaakoto image and the [art target](NYAAKOTO_PHOTOREAL_TARGET.md). |
| First-person sword and paws | [Packaged bokutō A/B](../visual-reviews/dojo-bokuto-form/README.md) improves the side silhouette, but normal pose hides grip/guard and has zero visible paw components. A [new source rig](../../Content/SourceArt/Characters/NyaakotoBokutoViewmodel/README.md) is entirely offscreen at the unchanged idle pose and still reads as a glove close up. | In actual gameplay FOV and attack/parry animations, both paws contact the tsuka without floating, clipping, glove-like digits or obscuring combat. Scanned wood must retain detail under real scene light. Capture a fixed neutral pose and representative motion on both platforms. |
| Estate architecture and roof lighting | [Mac Lumen Surface Cache](../render-qualification/estate-ue583-m1-20260924/README.md) has pink upper roof/eave and foliage gaps. A [packaged frontage check](../visual-reviews/dojo-frontage-yaw/README.md) confirms that the current road-facing Dojo shows its modeled shōji grid and steps; the broad plain panels in an earlier close frame were its rear side. Roof repetition, dark flat facade surfaces and sparse midground detail remain. | Modular, physically plausible roof/eave geometry with photographed or authored calibrated materials; no prominent visible pink gaps in entrance and close-foot Surface Cache views, and matching Lumen Scene/DF representation. Windows Nanite mask/cluster/stats and Mac fallback captures must be inspected separately. |
| Ground and foliage | [Road variation A/B](../visual-reviews/road-variation-study/README.md) reduces scan repetition, while [fern contact A/B](../visual-reviews/fern02-ground-transition/README.md) fails on raised bright soil and card-like clumps. | 1 m, 3 m and entrance views show coherent wet stone, soil, moss, leaf contact and no obvious tile/card repeats; inspect Lumen contribution, shadowing, LOD transition and material physical scale. |
| Complete frame and performance | Current [Estate Lit frame](../render-qualification/estate-ue583-m1-20260924/Estate_Entrance_Lit.png) is a prototype, not a photoreal approval. | Representative combat and traversal on the pinned 5.8.2 builds: 1440p/60 fps RTX 4070-class Windows quality target, 1080p/60 fps M1 Ultra Mac preset target, with recorded CPU/GPU frame times and memory. Capture cinematic shots independently of gameplay and verify offline save/play flow. |

Each visual candidate stays in ArtReview or source-only status until a fixed
camera A/B in the packaged game shows an improvement in normal play, the
license is recorded, and the target-platform performance is measured. Failed
studies remain visible so a later pass cannot be mistaken for a previous
approval. Historical weapon, tack and architectural claims require review by
qualified Japanese-material-culture and practice experts; the current modern
jōdō proportions for the bokutō are a design benchmark, not Edo-period proof.

The [paired Lumen card study](../render-qualification/estate-lumen-cards32-ue583-m1-20260924/PAIRED-REBUILD.md)
stopped before rendering because changing the card setting also changed saved
Dojo triangles and bounds. Its 12/32 images cannot be treated as a controlled
lighting comparison, and the visible Surface Cache gaps remain unresolved.

The [real-cat scan acquisition note](../art-research/nyaakoto-real-cat-scan-acquisition.md)
provides an attributed animal-anatomy reference. Its raw unrigged scan is not a
playable Nyaakoto mesh. Figma may support later interface layout, but this
3D/material gate is judged in Blender source and unedited Unreal frames.
