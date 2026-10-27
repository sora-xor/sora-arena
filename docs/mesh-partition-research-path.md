# UE 5.8 Mesh Partition research path

The playable Nyaagyu Estate still uses the dynamic campaign world and its flat gameplay collision. Its 16 visual terrain tiles are ordinary static mesh components, with the HI tier imported with Nanite and the Mac tier imported without it. This opt-in path creates **a separate research map** to test UE 5.8's actual [experimental Mesh Terrain](https://dev.epicgames.com/documentation/unreal-engine/mesh-terrain-in-unreal-engine). It never changes the campaign map or matchmaking collision.

Epic requires [World Partition and the Mesh Partition plugins](https://dev.epicgames.com/documentation/unreal-engine/accessing-mesh-terrain-in-unreal-engine). Its [crafting guide](https://dev.epicgames.com/documentation/unreal-engine/crafting-mesh-terrain-in-unreal-engine) distinguishes editor preview sections from **compiled sections required for PIE and cooked games**. The installed 5.8 source confirms that `UMeshPartitionStaticMeshComponent` sets `bLumenHeightfield = true`, and its static-mesh transformer defaults to Nanite with a fallback mesh. Those implementation defaults need visual and performance qualification on each target; flags alone are not a photorealism or frame-rate result.

`Plugins/SoraMeshTerrainResearch` is an **Editor-only, disabled-by-default** native bridge. It calls `UMeshPartitionEditorComponent::SpawnBaseModifier`, which Unreal Python cannot call directly. It uses Epic's `/MeshPartition/DataAssets/MPD_Default` definition only for the experiment. A real art pass would require a project-owned definition and material pipeline. It does not use Sensei Terrain or any paid asset.

Run only in a **separate linked Git worktree** with the 16 HI `/Game/Generated/Environment/Terrain` assets and two terrain material instances already imported. The runner refuses the source checkout and existing research maps. It changes `SoraArena.uproject` only in that diagnostic worktree to enable the editor plugin and its four Epic dependencies. From the source checkout, after copying this commit into the diagnostic worktree:

```bash
python3 scripts/unreal/run_mesh_partition_research.py \
  --project-root /absolute/path/to/diagnostic/sora-arena \
  --engine-root '/Users/Shared/Epic Games/UE_5.8' \
  --allow-interim-5.8.3 --dry-run

python3 scripts/unreal/run_mesh_partition_research.py \
  --project-root /absolute/path/to/diagnostic/sora-arena \
  --engine-root '/Users/Shared/Epic Games/UE_5.8' \
  --allow-interim-5.8.3 --prepare-plugin-only

# Build SoraArenaEditor in the diagnostic worktree after enabling the plugin.
# Then run the complete map conversion, compiled-section build, and verifier.
python3 scripts/unreal/run_mesh_partition_research.py \
  --project-root /absolute/path/to/diagnostic/sora-arena \
  --engine-root '/Users/Shared/Epic Games/UE_5.8' \
  --allow-interim-5.8.3
```

The one-shot runner validates source FBX SHA-256s, tile identities and placements, imported assets, material instances, worktree isolation, and engine version. It then creates `/Game/Research/NyaagyuMeshTerrain_Source`, places all 16 HI assets, runs Epic's `WorldPartitionConvertCommandlet` with `-ConversionSuffix` to produce `/Game/Research/NyaagyuMeshTerrain_Source_WP`, converts only those tiles to one `AMeshPartition` with 16 native base modifiers, and runs:

```text
UnrealEditor-Cmd SoraArena.uproject /Game/Research/NyaagyuMeshTerrain_Source_WP \
  -run=WorldPartitionBuilderCommandlet \
  -Builder=WorldPartitionMeshPartitionBuilder \
  -ReuseMode=ForceRebuild -AllowCommandletRendering
```

The gate rejects a zero-section build, any failed section or partition, an absent final build summary, or a level that cannot reload its compiled runtime sections with a static mesh. The native verifier also requires exactly one partition and provenance covering all 16 base modifiers. Logs remain in `Saved/Logs/mesh_research_<phase>.log` in the diagnostic worktree. Stage completion, native conversion, the builder summary, and native post-build verification are separate pieces of evidence; a mere process exit code is insufficient.

This path is **unqualified** until the diagnostic editor module compiles and the full gate runs on 5.8.2. UE 5.8.3 results remain interim. A passing compiled-section gate still does not prove final asset quality, material blends, seam appearance, Lumen probe behavior in scene, Mac fallback, cook/load, streaming cost, gameplay collision, or 60 fps. Those require visual review and measured Windows/macOS runs before any release-map migration. Keep the normal 16-tile rendering path until then.

## Source audit of Lumen and Nanite defaults

Run `python3 scripts/unreal/diagnostics/audit_mesh_terrain_lumen_source.py --engine-root '/Users/Shared/Epic Games/UE_5.8'` before a rendering experiment. It reads installed Epic source and the unchanged project descriptor; it does not open Unreal or alter a map. The pinned [5.8.3 diagnostic result](render-qualification/mesh-terrain-source-audit-ue583-20260924.json) records CL 58210709 and source hashes. The intended 5.8.2 release build remains uninstalled, so its exact source defaults and compiled assets have not been checked.

The 5.8.3 `UMeshPartitionStaticMeshComponent` constructor sets `bLumenHeightfield=true`, and the renderer uses that flag to classify a Lumen primitive group as a heightfield. Its static-mesh transformer defaults `bUseNanite=true` with a generated fallback. These are API capabilities, not evidence that a rendered surface is included in Lumen or uses Nanite on a particular machine. The transformer's first source model and later LODs set `MaxLumenMeshCards=4` and `DistanceFieldResolutionScale=0.0`; the engine's signed mesh distance-field builder only runs for positive resolution scale. The separate Lumen heightfield classification might be an intended alternate representation, but it still needs the actual **Lumen Scene, Surface Cache, card placement, Mesh/Global Distance Field, and Lit** comparison. [Epic's Lumen guide](https://dev.epicgames.com/documentation/unreal-engine/lumen-technical-details-in-unreal-engine) explains why card counts, pink coverage gaps, and thin geometry require visual inspection. The current [Estate entrance capture](render-qualification/estate-ue583-m1-20260924/README.md) covers the conventional static-mesh scene, not a built Mesh Partition.

The research plugin remains disabled in `SoraArena.uproject`, and the M1 path runs `METAL_SM5`, which cannot run Nanite. [Epic's macOS requirements](https://dev.epicgames.com/documentation/unreal-engine/macos-development-requirements-for-unreal-engine) list software Lumen on M1+ but Nanite on M2+ as beta. Qualification needs the isolated World Partition build and its compiled sections, followed by matched camera captures on Mac and supported Windows DX12 hardware. Changing these engine defaults globally or claiming coverage from the heightfield flag would bypass that gate.

The user identified [Unreal Sensei's Sensei Terrain Material](https://www.unrealsensei.com/asset/senseiterrainmaterial.html), whose current publisher page calls it a UE 5.8 Mesh Terrain master material and offers an emailed download link without a website account. It may help an isolated material comparison, especially slope-based layers, but no download, license text, compatible package, or redistribution rights have yet been inspected. The release repository therefore keeps its project-owned material graph and pinned CC0 surface scans. Acquiring a free copy would be a material evaluation, not evidence that Epic's experimental Mesh Terrain builds compiled runtime sections or that the scene is photoreal.
