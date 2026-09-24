# Estate Lumen card-budget probe — stopped at asset-equivalence gate

This was a diagnostic on the isolated UE **5.8.3** Mac worktree, not a release change. The release engine remains pinned to **5.8.2**. The aim was to compare the original 12-card Dojo/Kura assets with 32-card ArtReview duplicates in one packaged build. **No build, cook, package, or image capture was run** because the first duplicate failed the geometry-equivalence gate.

The editor command was:

```text
/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd /Users/takemiyamakoto/.codex/worktrees/ue583-diagnostic/sora-arena/SoraArena.uproject -ExecutePythonScript=/Users/takemiyamakoto/soramitsudev/sora-arena/scripts/unreal/diagnostics/import_lumen_cards32_art_review.py -unattended -nop4 -nosplash -NullRHI -stdout -FullStdOutLogOutput
```

The script duplicated `SM_Nyaagyu_EstateDojo`, set the duplicate LOD0 `MaxLumenMeshCards` from 12 to 32 with `StaticMeshEditorSubsystem.set_lod_build_settings`, and saved it. A second editor run read both assets independently:

| Property | Original Dojo | Rebuilt ArtReview Dojo |
|---|---:|---:|
| LOD0 Max Lumen Mesh Cards | 12 | 32 |
| `get_num_triangles(0)` | 14,966 | 14,884 |
| Nanite enabled | true | true |
| Material slots | 11 | identical names, order, and asset paths |

The 82-triangle change makes original-versus-candidate imagery an uncontrolled comparison. The duplicate's build log also reports degenerate tangent bases and near-zero binormals; it does not prove whether those warnings caused the triangle change. The importer raised `RuntimeError: ArtReview duplicated mesh changed beyond card budget`, before attempting Kura. UnrealEditor-Cmd nonetheless returned process exit code 0, so the required `SORA_LUMEN_CARDS32_ART_REVIEW_READY` markers and Python error scan are essential; exit code alone would falsely indicate success.

The original Dojo and Kura `.uasset` SHA-256 values after the probe were `42ab357403e73628a800533c309812af8860e5a856d5556684fab88a2c49ea3b` and `7b7df8876b5488e9923ec775003886e819d59c890f6c2f60a721e8bba874d04a`. The diagnostic C++ files remained at their handoff SHA-256 values `81e89c34f0040ebd285b8ea7c7ae70c0eb2e5cc94029458824662a1276fa4e86` (`SoraGameMode.cpp`) and `37cfae6afa1f1e4bdefe94ec89fe80288b53efa6f92c80dcba91dfbfed2c0421` (`SoraWorldBuilder.cpp`). The failed duplicate package was removed after its hash and readback were recorded; no runtime selector patch was applied. Available disk space fell from 26 to 18 GiB during the investigation and other concurrent work, below the 20 GiB stop floor, so no further Unreal activity was attempted.

Unedited editor logs are in [import.log.gz](logs/import.log.gz) (SHA-256 `ee9b63dddd15e61a6c38cdec226ebe93aadb0e93ce83aeaec91e4991f1913c20`) and [readback.log.gz](logs/readback.log.gz) (SHA-256 `9e72a845a2efd454db08325640aec0b18e0ba7aa16e77dfa6a6781d98197e599`). The removed Dojo duplicate `.uasset` hash was `406c6b8059ce613c55379115a20dd9dd2a5e2da9b92aed6d6d07e80c11d7bffe`.

A later controlled probe could rebuild *both* ArtReview duplicates from the same source, with 12 and 32 cards, and require equal resulting triangles, materials, and Nanite settings before capture. That separate experiment has not been run. The existing raw roof Surface Cache diagnosis in [estate-ue583-m1-20260924](../estate-ue583-m1-20260924/) remains the visual baseline. This probe provides no evidence of better Lumen coverage or frame time.
