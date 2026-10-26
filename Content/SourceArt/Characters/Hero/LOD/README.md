# Nyaakoto skeletal distance LODs

`SK_NyaagyuSamurai.fbx` remains LOD0. Regenerate LOD1 and LOD2 with
`blender -b --factory-startup --python scripts/art/generate_nyaakoto_lods.py`,
then run `scripts/art/validate_nyaakoto_lods.py` in a clean Blender session.

| LOD | Source vertices | Source triangles | Fur treatment |
| --- | ---: | ---: | --- |
| 0 | 201,632 | 182,836 | Full mesh/card fur and tabby fibers; furred paws at a 3 mm step, 5.3k fur strands a paw |
| 1 | 84,988 | 110,228 | One in five source fur cards; curved volumes reduced; paws at 4.5 mm, 1.8k strands a paw |
| 2 | 31,391 | 55,374 | No fiber cards; PBR normal/albedo maps provide distant fur; paws at 7 mm, no strands |

The counts are r3's (2026-10-26, s124/s125), read from the FBXs; e8d5b587's (s103/s104) were 176,069/184,493,
76,848/112,106 and 32,489/57,578. At LOD0 each paw's skin is about 24.4k triangles (24,396 and 24,384; e8d5b587's
30.5k, before the slimmer thumb and palm), and its strands 5,277 and 5,278 (one triangle and three vertices each).
(The runtime manifest's `source_triangles`, 128,729, is the hero source's, copied from its record by
`rig_nyaakoto_runtime.py`; its `source_vertices` is the runtime mesh's. Neither manifest field is LOD0's triangle
count.)

**The paws and their empty fists (2026-10-26).** Every LOD meshes the furred
third-person paws again at its own grid step (`nyaakoto_tp_paws.LOD_STEPS`: 3.0,
4.5 and 7.0 mm), and carries the morph targets `PawEmpty_R` and `PawEmpty_L` at 0.
Each LOD's morph is the same rule as LOD0's (`empty_points`, a rule of position)
on its own vertices, so a paw is empty or holding at every distance. The validator
re-derives every morphed vertex from the exported bind and the record's paw frame;
Unreal's own FBX export of the imported mesh is checked the same way
(`scripts/art/check_nyaakoto_ue_morph_export.py`, modelling Unreal's
MorphThresholdPosition).

**Fur strands (r3).** LOD0's paws carry opaque tapered fur strands
(`nyaakoto_tp_fur`) at their full density, LOD1's 35 % of it, LOD2's none. They
are vertices of the paw part, so the empty-fist morph moves them with the skin.
Each paw's pads are `M_Hero_RoseNose` faces on the grip side of the skin.

**Unreal (r3, 2026-10-26).** s128 imported these LODs under `--rhi`; Unreal's export
of the imported mesh keeps every strand (5,277/5,278 on LOD0, 1,801/1,829 on LOD1).
s129 checked every LOD's morph deltas against that LOD's MorphThresholdPosition
as saved (0.015 cm on each); `check_nyaakoto_lod_materials.py` checked what Unreal
renders per material on each LOD; `inspect_fbx_paw_coat.py` read the same coat in
our FBXs and in Unreal's export. The ledger is
`docs/art-direction/data/character_revision_runs.json`.

**Materials per LOD in Unreal.** This LOD2 FBX lists its 23 materials in another
order than LOD0's. Unreal maps an imported LOD's sections to the base slots by
imported slot name (`LODMaterialMap`). Its FBX export does not: it writes the raw
section indices. `scripts/unreal/readback_nyaakoto_lod_materials.py` and
`scripts/art/check_nyaakoto_lod_materials.py` check what Unreal renders on each LOD.

The FBXs preserve the same 20-bone hierarchy, all 23 PBR material identities,
the supplied SORA crest paths, and the full character bounds. `import_nyaakoto_lods.py`
loads them as actual LOD1 and LOD2 in the Unreal skeletal mesh. The source maps
are shared across all LODs; Unreal's texture mip streaming handles distant
texture resolution. There is no separate opaque fur shell or shader-only fake
silhouette. LOD1's triangle reduction is modest because armor, yumi, quiver,
katana and crest detail remain; LOD2 removes ornament, but keeps the same
equipment silhouette. Mac multiplayer needs measured on-screen LOD switching,
skin cost and 6v6 frame time before this counts as a performance qualification.
