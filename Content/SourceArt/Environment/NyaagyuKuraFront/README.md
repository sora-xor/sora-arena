# Nyaagyu Kura front: source-only art candidate

The fixed Estate entrance camera at world `(−2696, 0, 154.15)` cm and a 94°
horizontal field of view shows the **provision kura at `(−1000, ±1800)` cm** at
the far left and right edges. The nearest dojos are outside this view. A
geometry-only recreation puts each visible kura within roughly 225 × 200
pixels of a 1280 × 720 frame. The candidate studies the first southern kura's
front loading doors without changing combat collision or the center-road
sightline. The later packaged review revealed that the current actor yaw
points those doors outward, behind the building from the entrance camera.

The [matched baseline](KuraFront_Baseline_EyeHeight_Source.png) and
[frontage candidate](KuraFront_Close_EyeHeight_Source.png) are original,
unedited **Blender** renders from the same 1.58 m-high camera, lights and
exposure. The candidate replaces the parent kura's regular, flat striped
loading-door mesh with fourteen separate boards. Slightly cupped board faces,
actual seams, six forged cross-straps, peened rivets, pull rings and a
rain-board provide depth. Each board has explicit UV0 within a distinct slice
of a 2K cedar PBR atlas. The atlas cuts separate vertical grain sections from
the repository's SHA-pinned [Poly Haven Wood Planks Dirt scan](https://polyhaven.com/a/wood_planks_dirt), then adds restrained per-board tonal and lower-edge rain variation. The forged-iron shader uses the pinned [Rusty Metal 02](https://polyhaven.com/a/rusty_metal_02) scan. Both scans are CC0; exact input and derived output hashes are in [texture_manifest.json](texture_manifest.json). The untouched parent kura's plaster, roof, stone, geometry and SORA sign retain their existing provenance.

This is a **visual-only alternate full kura FBX**. It remains source-only after
the packaged first-person A/B failed the entrance composition gate. The existing
WorldBuilder building boxes remain the sole gameplay collision; the FBX has
no UCX. The candidate is neither an Edo-period measured reconstruction nor a
claim of AAA photoreal quality. The close source comparison improves the door
surface, while the surrounding roof, masonry, lighting and limited entrance
screen occupancy still constrain the whole frame.

The corrected FBX copies the authored board UVs onto export channel 0 for the
cedar polygons; the parent kura's other UVs remain untouched. An initial
package sampled channel 0 before this copy, yielding a flat tan door from one
atlas texel. The independent validator now checks that all 476 cedar polygons
span approximately the full atlas on FBX channel 0. The [packaged review](../../../../docs/visual-reviews/kura-front/README.md)
shows the defect, correction, and a separate visual-only inward-yaw test.

Rebuild and independently validate from the repository root:

```sh
python3 scripts/art/create_nyaagyu_kura_front_textures.py
blender -b --factory-startup --python scripts/art/render_nyaagyu_kura_front_baseline.py
blender -b --factory-startup --python scripts/art/create_nyaagyu_kura_front.py
blender -b --factory-startup --python scripts/art/validate_nyaagyu_kura_front.py
```

The validator checks the CC0 input hashes, generated atlas hashes, 14 board UV
ranges, exported cedar channel-0 coverage, editable mesh and hardware counts,
material-slot identity, full-size
FBX roundtrip triangles and bounds, and that the candidate is absent from
WorldBuilder. [validation.json](validation.json) records the current pass.

The [isolated ArtReview importer](../../../../scripts/unreal/import_nyaagyu_kura_front_art_review.py)
is pinned to UE 5.8.2. It imports the candidate under
`/Game/Generated/ArtReview/KuraFront`, keeps the full conventional Mac fallback,
and changes no runtime placement. Any UE 5.8.3 diagnostic package must use an
isolated copy with its version guard altered only in that worktree.
