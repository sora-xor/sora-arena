# CC0 Rancher horse comparison, 2026-09-24

The [Realtime Rancher's 3D Model Pack](https://opengameart.org/content/realtime-ranchers-3d-model-pack)
is posted by **lyndon** on OpenGameArt with a **CC0** license. The directly
linked `horse.zip` archive downloads without an account and has SHA-256
`469704f523c97b18627c14d47dcda69271357f2bb2787309f461b310a0043d27`.
It contains `LD_HorseRtime02.obj`, its `.mtl`, and six texture PNGs; no
separate license file is inside the archive. [CC0](https://creativecommons.org/publicdomain/zero/1.0/)
permits commercial reuse, but these files are used here only as external
reference. The project does not import or distribute the horse mesh or its
textures. The two clay renders derived from it are credited to lyndon/CC0.

The comparison script is
[`scripts/art/review_nyaagyu_horse_cc0_reference.py`](../../../../../../scripts/art/review_nyaagyu_horse_cc0_reference.py).
It extracts the source archive to a temporary directory, normalizes both
horses to the ground and to a common full ear height of about 1.83 m, and
renders fixed orthographic [profile](rancher_cc0_profile.png) and
[front](rancher_cc0_front.png) views in clay. That normalization is solely for
silhouette comparison; it is not evidence of the historical size of Japanese
horses. Our [bare profile](nyaagyu_anatomy_bare_profile.png),
[bare front](nyaagyu_anatomy_bare_front.png),
[saddled profile](nyaagyu_study_saddled_profile.png) and
[saddled front](nyaagyu_study_saddled_front.png) use the same cameras. The
eight [turntable frames](nyaagyu_study_turntable_000.png) run at 45° steps;
every frame SHA is pinned in `comparison_manifest.json`.

The Rancher model is a 2012 low-poly game asset with 14,986 source triangles,
not an anatomical measurement study. It provides a useful visual challenge to
our sculpt, but it is not a ground-truth source for breed, motion or Edo tack.
The visual findings are:

| Feature | Fixed-view observation | Decision |
|---|---|---|
| Shoulder/withers | Rancher has a softer slope into the forearm; Nyaagyu still shows a broad straight foreleg and visible proximal transition. | No direct geometry transfer. Re-sculpt against veterinary and horse-photo evidence before release. |
| Chest/front | Rancher's pectoral forms taper around the sternum. Nyaagyu remains too circular and symmetric. | An attempted 19 mm chest dent created a visible false fold and was reverted. |
| Head/eye | Rancher's longer head has a less raised eye. Nyaagyu's previous oval button read as a toy eye. | Reduced Nyaagyu's eye and orbital fold and added a lower lid; nostril/masseter still need sculpt review. |
| Mane/tail | Rancher's mane visibly breaks the crest silhouette. Nyaagyu's fine fibres were buried in its neck surface. | Raised the first-party mane roots to the crest; [before](nyaagyu_before_profile.png) and [after](nyaagyu_anatomy_bare_profile.png) show a clear source-only improvement. A proper groom/card LOD remains needed. |
| Hock/fetlock/hoof | Rancher has more leg joint variation but is itself coarse; Nyaagyu still has tube-like cannons and cap-like hoof joins. | Do not trace the CC0 mesh. Obtain an equine anatomy and biomechanics pass. |

The measured tack check uses the **structural** source bounds from the current
Blender study, excluding saddlecloth/loose straps: the kura is about
**40.0 × 37.9 × 28.5 cm** (length × width × height). The [Met's dated 1658
kura](https://www.metmuseum.org/art/collection/search/26572) is **36.8 ×
38.1 × 27.3 cm**. Our length is roughly 3.2 cm greater, a known rider-fit
assumption, not a historical match. The left modeled abumi toe enclosure,
excluding its suspension and strap, is about **30.0 × 13.4 × 26.4 cm**.
The [Met's late-16th/early-17th-century pair](https://www.metmuseum.org/art/collection/search/35376)
is **29.8 × 12.5 × 26.5 cm**. The family-mon placement on that pair is the
reference for the fictional exact SORA SVG on ours. Their measured similarity
does not prove functional fit or period accuracy; a mounted Nyaakoto pose,
foot clearance, girth/rein tension and tack specialist review are outstanding.

This comparison led to one limited art change: more visible mane and a less
button-like eye. The eight-angle [turntable](nyaagyu_study_turntable_045.png)
still exposes stylized body, cloth, hoof and tack forms. The isolated model
remains **source-only**; there is no Unreal import or release claim.
