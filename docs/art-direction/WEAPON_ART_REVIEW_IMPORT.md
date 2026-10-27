# Corrected weapon kit review import

`scripts/unreal/import_runtime_weapon_review.py` imports the 20 socket-corrected
meshes from W00, W01, W02, W04–W10, W12, W14, W15, W17, W19 and W20 into
`/Game/ArtReview/RuntimeWeapons`. It does not replace gameplay assets. W03, W11,
W13 and W16 remain held; the separate W18/Ya rebuild is outside this inventory.

The source gate verifies the exact manifest, records, FBXs and four authored
2048px maps per kit against a pinned geometry envelope. Every mesh receives all
three authored LODs, one baked material and its authored screen thresholds.
Imported normals/tangents and full-precision UVs are retained, with Nanite,
automatic collision, lightmap generation and degenerate removal disabled.

Materials use BaseColor, DirectX normal, ORM and Mask. W07's straw uses masked,
two-sided alpha. Emission uses each record's linear color and strength multiplied
by Mask R; kits with a hamon mask and no authored emission remain non-emissive.
Saved graph connections, channels, sampler types and parameter values are read
back rather than inferred from successful import calls.

Run through the pinned UE 5.8 editor with `-ExecutePythonScript`, in an isolated
worktree and the coordinated engine lane. The script accepts `mode=import` or
`mode=validate`, and `out=Saved/<fresh-directory>` via Python's `sys.argv`.
Validation must run in a separate editor process to check saved packages.
Both modes retain full render arrays, signed socket frames and measured JSON.
The completion marker is `WEAPON_REVIEW_READY`; editor exit alone is insufficient.

After each successful readback, run on CPU:

```sh
python -B scripts/art/verify_weapon_review_geometry.py Saved/<directory>/readback.json --output Saved/<directory>/source-geometry.json
```

This matches every triangle corner to the exact FBX, preserving winding and UV
seams, and compares positions, UV0, normals and tangents with explicit packing
tolerances. It uses Blender's installed parser without launching Blender.
It complements the editor's counts, bounds, LOD, material and socket gates.

The first import exposed existing atlas overshoots in the source LOD2s: one
corner in W05 reaches V=1.00972125, and two corners in W09 reach V=1.00321476.
The envelope records their exact bounds and corner counts; readback must match
them. They remain art defects pending correction, not accepted UV layout. The
first failed import is retained. Winding comparison follows Unreal's clockwise
face convention; it does not accept both orientations to make a match.

These checks establish an import candidate. Original renders, framing, character
grips, runtime integration, platform and performance acceptance remain separate.
