# Real-cat scan acquisition feasibility — 2026-09-24

This is an acquisition and anatomy-reference check for Nyaakoto. It does not approve any scan as the character, a rig, a groom, or a photoreal game asset. No third-party GLB or preview image is checked into this repository.

## Usable no-purchase download path

The strongest **directly accessible** original-animal scan found was [Cat (Take 2) by Neo_minigan](https://sketchfab.com/3d-models/cat-take-2-2996f59c517245aa91cf513a5624935e), a photogrammetry capture of the creator's real tabby cat. [Sketchfab's current public model API record](https://api.sketchfab.com/v3/models/2996f59c517245aa91cf513a5624935e) reports `isDownloadable: true` and `license.slug: by`, with the requirement “Author must be credited. Commercial use is allowed.” [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) permits commercial adaptation with creator credit, source/license links, and an indication of changes. The [Objaverse 1.0 dataset](https://objaverse.allenai.org/docs/objaverse-1.0/) provides a public, standardized GLB mirror:

```text
https://huggingface.co/datasets/allenai/objaverse/resolve/main/glbs/000-065/2996f59c517245aa91cf513a5624935e.glb
```

Downloaded outside the repo to `/tmp/sora-cat-scan-eval/neominigan-cat-take-2.glb` and verified SHA-256 `b2c2cad76dbad62d3eb41c99a20292de31f5b55163eb6d7ca84c11b7dccb444c` (49,087,696 bytes). Blender 5.2.2 imported the actual archive: 18 mesh objects, 1,000,000 triangles, UVs on all 18, two 1024² color images, no armature, no actions. The scan includes the sleeping cat and pillow/background material. The original listing preview **does beat V4 on visible real-cat anatomy**: its cranium-to-muzzle ratio, brow-to-cheek transition, ear placement, and tabby coat are naturally continuous where V4 remains bulbous and symmetric. This is a preview-based form judgement, not a measured close-up of the imported mesh. Its closed-eye facial pose, surface noise and enormous/unreliable imported coordinates require normalization, crop, retopology, and new eye/groom work. It is valuable as **real feline head, cheek, ear and coat reference**, not as an upright hero source mesh to rig directly.

An independently accessible lower-resolution comparison is [Sleeping Cat On The Bed 1 — 3D scan by Alben Tan](https://sketchfab.com/3d-models/sleeping-cat-on-the-bed-1-3d-scan-ae07a741be6944e8ba5e2657069d3aaf). The [public record](https://api.sketchfab.com/v3/models/ae07a741be6944e8ba5e2657069d3aaf) names a LiDAR scan of the creator's cat Margaery, states CC BY and downloadability, and the public mirror is:

```text
https://huggingface.co/datasets/allenai/objaverse/resolve/main/glbs/000-076/ae07a741be6944e8ba5e2657069d3aaf.glb
```

The tested GLB is 1,170,828 bytes, SHA-256 `204796aa2082038c4ef9bf0afec74c191e520461e385b91eefbe3f523fd1296e`. Blender found one UV mesh, 31,139 triangles, one 1024×256 image, no armature/actions. The face is low-resolution and eyes are shut, so it is less suitable for a close facial sculpt than Neo_minigan's scan.

For any derivative that actually incorporates either scan, retain creator name, exact source URL, [CC BY 4.0 license URL](https://creativecommons.org/licenses/by/4.0/), and a clear modification statement in game credits and asset provenance. Keep the raw download in a private asset workspace; do not copy it into the public source tree or distribute it as a stand-alone game package asset. Prefer a fresh original sculpt informed by real-animal measurements to avoid retaining scan defects.

## Stronger face-specific candidate; authenticated download unresolved

[Photogrammetry Experiment: Cat's Face by snacksthecat](https://sketchfab.com/3d-models/photogrammetry-experiment-cats-face-dc453003896b4f53846630900c35e7dc) is the most relevant *visible* reference for Nyaakoto's actual open-eye facial anatomy. Its [live API record](https://api.sketchfab.com/v3/models/dc453003896b4f53846630900c35e7dc) says 279,154 triangles, 142,181 vertices, 455 source photographs, `isDownloadable: true`, and CC BY with commercial use allowed. The creator's preview visibly shows integrated orbit/brow, nasal bridge, muzzle transition, ears and short tabby coat. It is a raw scan with partial body, irregular trim and no evidenced deforming topology, rig, groom or PBR map set.

The official [Sketchfab Download API](https://sketchfab.com/developers/download-api/downloading-models) requires a user OAuth bearer token for `GET https://api.sketchfab.com/v3/models/dc453003896b4f53846630900c35e7dc/download`. The public request returned HTTP **401** `Authentication credentials were not provided.` The same UID was absent from the Objaverse 1.0 object-path mapping tested on this date. The Mac's browser session was unavailable because the machine was locked, so an existing Sketchfab account could not be checked. No bypass of authentication or viewer-asset extraction was attempted. When an authorized Sketchfab session is available, use the listing's **Download 3D Model** action (or the documented OAuth endpoint), inspect the original archive and license file in a private workspace, and record the SHA-256 before any sculpt use.

## Decision

A legally attributed, no-purchase **real-cat reference is available now** through the Neo_minigan/Objaverse GLB above. It is not an acceptable Nyaakoto hero head: both tested scans are sleeping, unrigged, and physically incomplete for a speaking, fighting biped. The face-specific snacksthecat scan has the strongest visible anatomy, but its archive was not acquired, so no topology, texture, or provenance claim beyond the public listing is made. The next character-art step is a manual anatomical sculpt and clean deformation topology using these references, followed by fixed-camera Unreal review; neither a scan nor the V4 procedural study should be promoted directly to runtime.
