# Nyaakoto bokutō paw viewmodel — source-only study

This is an editable **source-only** grip study fitted to the measured
`DojoBokutoForm` mesh. The current playable Unreal chapter-one bokken and its
`SoraCharacter` viewmodel are untouched. The original four-part bokutō in the
`.blend` is review-only and is excluded from the paw FBX.

Nyaakoto's user-supplied white-paw/red-and-indigo samurai image informed the
palette and exposed-paw design; its SHA-256 is in `manifest.json`. The image is
not redistributed or used as a texture. The two paws each have four **separate**
digit meshes, their own contact pads, an opposing thumb, carpal transition,
layered cloth/plate kote, and a small physically mounted SORA kamon. The kamon
samples the exact project SVG-derived PNG; no substitute mark was drawn. A
15-bone editable armature gives each wrist, digit, and thumb an independent pose
control. The FBX has 91 meshes, 12,520 source triangles, single authored UV0
on every mesh, and one rigid weight per vertex. This is a control study, not a
production skin or combat animation set.

The paired 1600×900 Cycles PNGs are raw, unedited Blender renders. Each pair
uses the same camera, lighting, bokutō, and actual idle WeaponRoot transform:
`(40,18,-18)` cm, authored mesh scale `0.75`, no pose offset. The normal camera
uses a 70° horizontal FOV to approximate Unreal's native first-person setting;
it cannot reproduce UE's `FirstPersonScale=0.6` projection exactly.

- `IdlePose_BokutoOnly.png` / `IdlePose_BokutoAndPaws.png`: no paw is visible.
  An 8/255 per-channel difference threshold finds **0 changed pixels out of
  1,440,000**. This is a real framing failure at the current idle pose.
- `GripDetail_BokutoOnly.png` / `GripDetail_BokutoAndPaws.png`: the fixed detail
  camera shows two distinct grasps, but the white palm/digit masses still read
  too glove-like, the small pads are mostly occluded by wood, and the fabric
  plate shapes remain too simple for a photoreal AAA close-up. The source kamon
  is mounted on the right kote, but is not clearly readable in this frame.

The scan-led white oak/albedo/normal/ARM on the bokutō comes from the existing
Poly Haven `white_oak_veneer` CC0 record. Paw fur, silk, and lacquer reuse the
project-owned image-generation/procedural maps documented in
`../Hero/PBR/manifest.json`; paw pads reuse the project-authored maps from
`../NyaakotoFirstPersonPaws/Textures/manifest.json`. The exact SORA PNG/SVG
hashes are pinned to `../../UI/sora_logo_manifest.json`. FBX materials require
future explicit Unreal PBR binding; the full material-node setup is in the
editable `.blend`. All source images are linked from within this repository.

This study **fails runtime and photoreal admission**. The normal grip is
offscreen; the paw anatomy needs sculpting and finer fur, the kote needs a
construction/historical review, and rigid digit weights need proper skinning
and animation. A first packaged UE fixed-camera A/B is needed after a
viewmodel pose adjustment. A nonruntime starting probe is WeaponRoot Y≈8 cm
and Z≈−7 cm (from Y=18, Z=−18), holding X=40 cm and yaw=0; this must be
measured in Unreal for reticle clearance, collision, motion, and 65–70° native
FOV before any playable placement. No historical authenticity or AAA visual
quality is claimed by these Blender renders.

The reproducible source-only test of that translation is in
[`PoseProbe/README.md`](PoseProbe/README.md). It confirms the grip/paws enter
the fixed Blender frame and the static reticle disc stays clear, while leaving
the runtime and photoreal gate failed.

Rebuild and independently validate from the repository root:

```sh
blender -b --factory-startup --python scripts/art/create_nyaakoto_bokuto_viewmodel.py
blender -b --factory-startup --python scripts/art/validate_nyaakoto_bokuto_viewmodel.py
```
