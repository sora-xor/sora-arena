# Nyaagyu Estate path quilt — visual candidate

The existing 64 m Estate approach repeats one 1.8 m photograph. This source
study creates a 7.2 × 7.2 m, 4K periodic atlas from the already pinned
[Poly Haven Grey Stone Path](https://polyhaven.com/a/grey_stone_path) scan
(Amal Kumar, **CC0-1.0**). It uses no purchased asset and adds no new
historical or branding claim.

`scripts/art/build_nyaagyu_path_quilt.py` selects 64 overlapping photographed
patches and chooses low-error joining seams. The same source crop and seam
mask is applied to albedo, DirectX tangent-space normal, packed ARM and
16-bit displacement. There are no rotations or mirrors that would turn
tangent-space normals away from the stone relief. Source files are
content-hash pinned in the existing terrain manifest and repeated in the
quilt manifest; generated maps and script version are pinned there too.
`scripts/art/validate_nyaagyu_path_quilt.py` checks this chain, normal
lengths, packed channels, periodic edges and cross-cell repetition. The
maximum correlation among its sixteen 1.8 m subcells is 0.300, versus 1.000
for sixteen exact repeats of the original photograph. The source scan's
stone identities still recur; texture statistics are not proof of visual
quality.

`Nyaagyu_PathQuilt_Review.jpg` is a top-down texture contact sheet, **not an
Unreal gameplay screenshot**. A diagnostic-only import into UE 5.8.3/M1
Ultra bound the three visual maps at 720 cm; the combined packaged Mac
cook/stage completed with zero cook warnings or errors. An offscreen,
packaged-game review then captured the Estate entrance and downward road view
at the established camera. The [unedited frames](../../../../../docs/visual-reviews/README.md)
show a **failed visual gate**: the old exact 1.8 m grid is reduced at distance,
but distinctive oval and square stones repeat across the close view, and the
larger atlas softens the photographed detail. The broad route remains too
regular. This atlas stays source-only. The main game continues to bind the
original 1.8 m scan; the source FBX UV/height and collision were not changed
for this candidate. It is neither photoreal AAA terrain nor a qualified
UE 5.8.2 release asset.

Regenerate and validate:

```sh
python3 scripts/art/build_nyaagyu_path_quilt.py
python3 scripts/art/validate_nyaagyu_path_quilt.py
```
