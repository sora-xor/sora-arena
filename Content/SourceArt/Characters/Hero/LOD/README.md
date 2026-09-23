# Nyaakoto skeletal distance LODs

`SK_NyaagyuSamurai.fbx` remains LOD0. Regenerate LOD1 and LOD2 with
`blender -b --factory-startup --python scripts/art/generate_nyaakoto_lods.py`,
then run `scripts/art/validate_nyaakoto_lods.py` in a clean Blender session.

| LOD | Source vertices | Source triangles | Fur treatment |
| --- | ---: | ---: | --- |
| 0 | 130,071 | 95,007 | Full mesh/card fur and tabby fibers |
| 1 | 48,137 | 60,089 | One in five source fur cards; curved volumes reduced |
| 2 | 15,298 | 29,020 | No fiber cards; PBR normal/albedo maps provide distant fur |

The FBXs preserve the same 20-bone hierarchy, all 23 PBR material identities,
the supplied SORA crest paths, and the full character bounds. `import_nyaakoto_lods.py`
loads them as actual LOD1 and LOD2 in the Unreal skeletal mesh. The source maps
are shared across all LODs; Unreal's texture mip streaming handles distant
texture resolution. There is no separate opaque fur shell or shader-only fake
silhouette. LOD1's triangle reduction is modest because armor, yumi, quiver,
katana and crest detail remain; LOD2 removes ornament, but keeps the same
equipment silhouette. Mac multiplayer needs measured on-screen LOD switching,
skin cost and 6v6 frame time before this counts as a performance qualification.
