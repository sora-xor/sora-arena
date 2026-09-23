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
