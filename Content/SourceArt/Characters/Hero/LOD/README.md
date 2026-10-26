# Nyaakoto skeletal distance LODs

`SK_NyaagyuSamurai.fbx` remains LOD0. Regenerate LOD1 and LOD2 with
`blender -b --factory-startup --python scripts/art/generate_nyaakoto_lods.py`,
then run `scripts/art/validate_nyaakoto_lods.py` in a clean Blender session.

| LOD | Source vertices | Source triangles | Fur treatment |
| --- | ---: | ---: | --- |
| 0 | 176,069 | 184,493 | Full mesh/card fur and tabby fibers; furred paws at a 3 mm step |
| 1 | 76,848 | 112,106 | One in five source fur cards; curved volumes reduced; paws at 4.5 mm |
| 2 | 32,489 | 57,578 | No fiber cards; PBR normal/albedo maps provide distant fur; paws at 7 mm |

The counts are the production revision's (2026-10-26, s103/s104), read from the FBXs. The furred paws added
about 61k triangles at LOD0 (30.5k a paw, against a few thousand for the curled tubes before them).

**The paws and their empty fists (2026-10-26).** Every LOD meshes the furred
third-person paws again at its own grid step (`nyaakoto_tp_paws.LOD_STEPS`: 3.0,
4.5 and 7.0 mm), and carries the morph targets `PawEmpty_R` and `PawEmpty_L` at 0.
Each LOD's morph is the same rule as LOD0's (`empty_points`, a rule of position)
on its own vertices, so a paw is empty or holding at every distance. The validator
re-derives every morphed vertex from the exported bind and the record's paw frame;
Unreal's own FBX export of the imported mesh is checked the same way
(`scripts/art/check_nyaakoto_ue_morph_export.py`).

The FBXs preserve the same 20-bone hierarchy, all 23 PBR material identities,
the supplied SORA crest paths, and the full character bounds. `import_nyaakoto_lods.py`
loads them as actual LOD1 and LOD2 in the Unreal skeletal mesh. The source maps
are shared across all LODs; Unreal's texture mip streaming handles distant
texture resolution. There is no separate opaque fur shell or shader-only fake
silhouette. LOD1's triangle reduction is modest because armor, yumi, quiver,
katana and crest detail remain; LOD2 removes ornament, but keeps the same
equipment silhouette. Mac multiplayer needs measured on-screen LOD switching,
skin cost and 6v6 frame time before this counts as a performance qualification.
