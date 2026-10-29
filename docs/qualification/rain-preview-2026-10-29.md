# Rain preview investigation, 29 October 2026

Rain is still visually rejected and is not integrated into gameplay. The
existing asset's preview did not establish the steady rain authored for
Chapter 3. `578064f7` changes the diagnostic to use a main editor viewport
and adds a matching zero-intensity dry control. Ten host harness tests pass;
the new viewport path has not yet run in Unreal because disk space is below
the existing 30 GiB launch reserve.

## What was observed

Both completed attempts used UE 5.8.3, CL 58210709, on Metal SM6 in isolated
SOURCE. The compiled editor remained `c7f1dfe4`; its artifact and native
inputs were checked before each launch. Only documentation and the preview
scripts differed. Neither attempt imported or changed generated assets.

| Source / archive under `Saved/Qualification/2026-10-28/` | Result |
| --- | --- |
| `7e2d85df`, `rain-preview-7e2d85df-attempt1` | Editor/wrapper completed naturally with code 0. One rain EXR and three light controls were written; the light comparison passed. All four originals were viewed through the same documented fixed display transforms. The rain image showed only the stage, with no visible rain. Visual rejection. |
| `1d8e5d6f`, `rain-preview-1d8e5d6f-attempt1` | Explicit simulation steps separated by scene captures still produced no convincing steady rain: the wall and floor dominate, with at most sparse pale flecks. All four displays were reviewed; the light comparison passed. Native editor exit was 0, but the observing guard returned 125 because free disk briefly reached 32,099,835,904 bytes, below 30 GiB. The guard never signalled the editor. This run failed qualification. |

Each archive contains 17 authenticated original files, including the EXRs,
logs, process receipt, artifact record and before/after input manifests.
Config, generated assets, native inputs and frozen ROOT were unchanged.
Raw engine startup diagnostics remain in the logs; the light-check result is
not an error-free-engine or rain-quality claim.

The sibling review JSONs have SHA-256:

- Baseline: `8052a91bd07558f46056b3678fc6a21b0f95c138db9da1cb5ec44c7d0dbde383`.
- Scene-capture stepping: `9e22325e761a4fdb71a767470be1aa07b16cecab013851b4d994da3b12a50cfa`.

## Cause and diagnostic change

In the installed engine, `Engine/Source/Runtime/Engine/Public/SceneView.h`
defines `AllowGPUParticleUpdate()` to exclude scene captures. Niagara's
`PostRenderOpaque()` in `NiagaraGpuComputeDispatch.cpp` checks that method
before executing its post-opaque stage. The rain streak emitter uses GPU
depth-buffer collision, which requires this stage. Calling `capture_scene()`
between manual simulation steps therefore does not provide the required
main-view simulation. Niagara's fallback tick flushing can use dummy view
and buffer data; its own console-variable description warns about incorrect
depth collisions in that situation.

`31ae8ee1` now aims a level editor viewport at the shot camera, refuses to
proceed without one, and invalidates that viewport between manual 1/60 s
simulation steps. Solo mode and disabled component ticking prevent extra
automatic steps. The final viewport draw gets time to drain before pausing
the effect and exporting through SceneCapture2D. This changes the preview,
not the engine or production effect. The unnecessary post-construction
`set_auto_activate()` call was also removed; it generated a warning.

`578064f7` adds `Rain_DryControl_day_2.50s.exr`, with the same camera, lighting,
placement and prescribed age but `User.Intensity = 0`. The next run should
produce two rain-stage EXRs and three lighting controls. Compare and view
both stage originals before deciding whether the viewport change works.
The ten host tests cover shot identity, the missing-viewport failure, the
step/draw/drain sequence and existing preview cases. They cannot prove that
the GPU ran or that the effect looks correct.

## Disk cleanup and remaining work

The user-authorized cleanup removed unused SORA intermediate/cooked output,
the old staging directory and completed Homebrew download archives older
than one day. Before deletion, all 64 staged application files matched the
preserved `Local/Packages/mac-1b6dfadc/SoraArena.app` byte for byte, and the
selected paths had no open files. That preserved application was rechecked
afterward. Source files, generated assets, validation originals and backups
were retained. The receipt is
`Saved/Qualification/2026-10-29/unused-build-cache-cleanup.json`; free space
increased from 22.42 to 28.87 GiB during cleanup, then continued falling as
other work ran. No other job was stopped and the launch reserve was not lowered.

Next: run the main-view wet/dry diagnostic once disk reserve is available,
then establish visible moving rain under the actual night lighting. Rain
integration must handle roofs/eaves and varying surface height: the current
splash emitter assumes a flat plane at component height. Eave drips, puddle
rings, gutter flow, sky, wet materials and chapter weather transitions remain
unfinished. There is no new SM5, Nanite, actual M1, Windows, packaged-game,
performance or photoreal acceptance. ROOT stays frozen at `b6ba3c11`; the
preserved package is still `1b6dfadc`.
