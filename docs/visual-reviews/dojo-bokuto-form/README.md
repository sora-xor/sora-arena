# Nyaagyu bokutō form: packaged visual gate

The revised bokutō is an original four-part mesh with a curved, faceted,
blunt wooden blade and a leather tsuba. Its surface maps use [Poly Haven's
White Oak Veneer](https://polyhaven.com/a/white_oak_veneer) and brown-leather
scans under [CC0](https://polyhaven.com/license). The veneer image supplies
surface detail; it does not imply veneer construction. The source [manifest](../../../Content/SourceArt/Weapons/DojoBokutoForm/manifest.json)
pins the exact files and hashes. The 101.5 cm total, 24.2 cm grip, and 1.5 cm
sori follow the [All Japan Kendo Federation's modern Jodo equipment rules](https://www.kendo.or.jp/wp/wp-content/uploads/2023/07/jodo-shiai_regulations.pdf)
as a proportion benchmark, not a universal Edo or Nyaagyushinkageryuu claim.

## Same-camera packaged review, 24 September 2026

The [strict UE 5.8.2 ArtReview importer](../../../scripts/unreal/import_dojo_bokuto_form_art_review.py)
verified source hashes, CC0 manifests, 2K map dimensions, UV0, material slots,
and the full conventional Nanite fallback. The isolated diagnostic copy changed
only the importer engine guard to the installed UE
`5.8.3-58210709+++UE5+Release-5.8`. Blender 5.2.2 LTS source/FBX roundtrip
and primary UV audit passed: four parts, 5,332 triangles, three material zones,
one noncollapsed UV channel, and zero suspected wrong-primary zones. Unreal
import, Mac game build, cook, stage, and packaged launch passed. This does not
qualify the pinned UE 5.8.2 release or Windows rendering.

The unedited 1,280 × 720 captures use chapter-one dojo, player location
`(-1800, -1050, 90.15)` cm, camera yaw `-105°`, pitch `-2°`, and field of view
`65°`. The default pair retains the real gameplay `WeaponRoot` transform and
0.75 mesh scale. The close pair applies the same **test-only** side-on root
transform to both meshes; it judges silhouette/material, not normal paw fit.
No gameplay asset, collision, animation, or WorldBuilder placement was changed.

| Pose | Playable original | Revised source-only candidate | Finding |
| --- | --- | --- | --- |
| Normal first-person | [original](UE583_DojoBokutoForm_Settled_Default_Original.png) | [candidate](UE583_DojoBokutoForm_Settled_Default_Candidate.png) | Both render, but the candidate is only a narrow pale strip near the lower right. The grip and guard are offscreen. |
| Side-on close inspection | [original](UE583_DojoBokutoForm_Settled_Close_Original.png) | [candidate](UE583_DojoBokutoForm_Settled_Close_Candidate.png) | The candidate has a legible curve, blunt kissaki, guard, and longitudinal oak grain; its wood remains too pale and clean for final art. |

The first [run](UE583_DojoBokutoForm_Default_Candidate.png) and an identical
[repeat](UE583_DojoBokutoForm_Repeat_Default_Candidate.png) captured an empty
default candidate frame. `SetStaticMesh` subsequently returned success, and a
third run with a one-second delay after the swap produced the visible [settled
candidate](UE583_DojoBokutoForm_Settled_Default_Candidate.png). This is
consistent with capture/render-state timing; the first two frames cannot be
used as evidence that the geometry is absent. The diagnostic hook and all run
logs are archived for review.

The packaged log reports `paw_components=0`. In the current
`ASoraCharacter::BuildWeapon`, an authored mesh returns before the fallback
`FurPaw` is created; the owner's body mesh is hidden from the first-person
camera. **There is no visible hand or paw contact to validate.** This blocks
runtime admission independently of the improved source shape.

The Estate uses automatic histogram exposure (12–88% percentile range, bias
`-0.45`) in its post-process volume. A separate unedited diagnostic launch
used `-ExecCmds='r.EyeAdaptationQuality 0'` on the same staged binary. Its
[close candidate](UE583_DojoBokutoForm_NoEyeAdaptation_Close_Candidate.png)
is darker overall than the [normal close candidate](UE583_DojoBokutoForm_Settled_Close_Candidate.png),
but the wood still looks pale. The frame-wide mean changed from approximately
`(112,99,80)` to `(102,88,70)` in 8-bit RGB. This is evidence of a rendering
and exposure interaction, not an image edit or a material calibration. Further
camera, lighting, and albedo work must be assessed in game.

**Gate result: source-only.** The side-on profile is materially better than the
inherited straight bokken, but the normal first-person view does not show its
characteristic shape or a believable grip. The wood is overbright in the Estate
lighting. A final pass needs a visible paw/hand viewmodel, fitted grip, pose and
animation review, calibrated wood response, independent historical review, and
Mac/Windows performance measurements. The 1,280 × 720 diagnostic frames are
insufficient to assert the requested AAA photorealistic quality.

All 16 unedited frames, compressed raw logs, and the temporary diagnostic hook
are recorded in [checksums](logs/SHA256SUMS.txt). The last staged bundle ID was
`org.sora.soraarena`. The build was run below the 100 GiB planning disk check
under a bounded diagnostic allowance; free space remained above the 20 GiB stop
floor. The diagnostic `SoraGameMode.cpp` and `SoraWorldBuilder.cpp` were restored
byte-for-byte to SHA-256
`81e89c34f0040ebd285b8ea7c7ae70c0eb2e5cc94029458824662a1276fa4e86`
and `37cfae6afa1f1e4bdefe94ec89fe80288b53efa6f92c80dcba91dfbfed2c0421`
respectively. The imported candidate remains unreferenced under
`/Game/Generated/ArtReview/DojoBokutoForm` in the isolated checkout.
