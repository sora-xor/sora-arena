# W18 rebuild, bow paw and first-person capture: the runbook

**Status:**

- Root accepted this order (Codex, 2026-10-25 16:43 UTC). It is **not
  started**. It runs only after root's explicit handback of the UE/Blender
  lane.
- It runs from the art worktree (`claude/photoreal-art`), never the shared
  checkout.
- One job at a time. At the start of each step, post its command, PID and log
  to the mailbox. At its end, post its EOF, exit codes and results.
- **Stop at the first failure**, keep everything it wrote, and post it.
  Nothing here is an admission or a photoreal claim.

**Conventions:**

| Name | Means |
| --- | --- |
| `B` | `/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python-exit-code 1 --python` |
| `PY` | `env OPENBLAS_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 /Users/mtakemiya/.codex/worktrees/complete-game/sora-arena/Local/Python311/bin/python` |
| `UE` | `scripts/toolchain/run-editor-script.sh`. The default is `-nullrhi` in UnrealEditor-Cmd. `--rhi` renders offscreen in UnrealEditor-Cmd; `--editor` uses the full UnrealEditor. It passes with the completion marker and no Python error lines, and exit 0, or exit 1 from a full editor that quit itself |
| PIDs | `pgrep -x Blender`, `pgrep -x UnrealEditor-Cmd` (default and `--rhi`) or `pgrep -x UnrealEditor` (`--editor`). Never `pgrep -f`, which matches the launching shell |
| Archive | `Saved/W18Rebuild/Archive/<step>/`: a copy of everything the step will overwrite, with SHA256SUMS, made read-only before it runs |
| Times | `date -u` at start and end, in `Saved/W18Rebuild/<step>.times` |

**Test counts** are reported as unittest gives them: run, passed, expected
failures and skipped. Never a run total called "passed".

## The steps

1. **Timber patch study** (Blender, CPU).
   - `B scripts/art/render_timber_patch_study.py -- --cpu --raw /Users/mtakemiya/.codex/worktrees/complete-game/sora-arena/Local/ThirdPartyRaw`
   - Marker `PATCH_STUDY_READY`. It writes `Local/ArtCache/NyaagyuDojoTimbersV23Patch/attempt<N>/`, created exclusively, so no archive is needed.
   - **Check:** view both contact sheets and every panel. `study.json` must hold both variants' measurements beside the scans'. The EXR normal-map read must pass its unit-normal check, or the study stops (that is a result, not a retry).
2. **W18 static rebuild** (Blender).
   - **Archive** `Content/SourceArt/Weapons/Runtime/W18_Yumi/{*.fbx,*.blend,T_Weapon_18_*.png,build_record.json}` and `Runtime/Renders/SM_Weapon_18*.png`.
   - `B scripts/art/create_runtime_weapon_yumi.py -- --only 18`, then `B scripts/art/create_runtime_weapon_validation.py -- --only 18`. These are the two Blender jobs `create_runtime_weapon_build_all.py --only 18` runs, without its manifest rewrite (see the open decision).
   - **Check:**
     - LOD0 under the 80,000-triangle budget (it was 61,556; the new strip adds about 7,000);
     - the spec checks pass (length, grip ratio, brace, arrow length), and `Nigiri` still names the grip part;
     - the four maps are present;
     - the three renders, viewed: the grip reads as a skived spiral, and the shaft shows its nodes, browning and satin polish.
3. **Rig rebuild** (Blender).
   - **Archive** `W18_Yumi/Rig/` except `Review/`.
   - `B scripts/art/create_runtime_weapon_yumi_rig.py`
   - **Check:** the build's own gates pass: the FBX read-back (centimetres, 10 fps take), check geometry v3, the stretch gate. `rig_record.json` pins every W18 source, `yumi_nigiri.py` and `yumi_ya.py` included.
4. **Rig grey review** (Blender).
   - **Archive** `W18_Yumi/Rig/Review/`.
   - `B scripts/art/render_yumi_rig_review.py -- --out Saved/YumiRig/Review_w18rebuild`, then copy the 30 originals, the playback npz and `W18_rig_review_arrow.json` into `Rig/Review/`.
   - **If `W18_rig_review_arrow.json`'s SHA-256 changed:** add a `right_cheek.recomputed` entry to `data/yumi_fp_hold_study.json`, solved by `yumi_fp_holds.right_cheek` from the new sockets, with their hash. `test_yumi_fp_holds` requires it. The grip correction should not move Grip_R (the string) or the Muzzle (the stave face).
5. **Host contracts** (CPU).
   - **Remove the two STALE markers:** `test_yumi_nigiri_ya.Rebuild` and `test_nyaakoto_fp_paws`'s nigiri-envelope test.
   - Run `PY -m unittest` on `test_yumi_draw`, `test_yumi_nigiri_ya`, `test_nyaakoto_fp_paws`, `test_yumi_fp_holds`, `test_fp_material_bindings` and `test_analyse_yumi_fp_review`. Every count must show 0 expected failures.
   - **If the envelope test fails,** the rebuilt wrap is not the design envelope within the carve gap. Investigate before the paw; never widen the gap.
   - **Ledgers:**
     - regenerate `W18_Yumi/Rig/manifest.ledger.json` (`scripts/assets/write_own_ledger.py`, its original arguments, after the rebuilt files are staged);
     - record the W18 static per the open decision;
     - `scripts/assets/validate_asset_ledger.py` must show no new errors and none on W18 paths.
6. **Bow paw v3** (Blender).
   - **Archive** `Content/SourceArt/Characters/NyaakotoFirstPersonPaws/Production/` (the uncommitted v2, about 88 MB).
   - `B scripts/art/create_nyaakoto_fp_paws.py`
   - **Check:** its build record, the paw tests on the built mesh, and the four renders, viewed.
   - Stage Production, then write its OWN ledger (`write_own_ledger.py` reads git-tracked files).
7. **Unreal rig import.**
   - `UE scripts/unreal/import_runtime_weapon_yumi_rig.py YUMI_RIG_UE_READY Saved/W18Rebuild/ue_rig_import.log`
   - **Check:** the readback's sockets, unit bone scale, raw and compressed playback (`test_yumi_draw`'s Unreal tests on the new readback), `bow_materials` = MI_W18_Weapon, and `bow_package_binds` (supporting evidence only).
8. **Unreal paw import.**
   - `UE --rhi scripts/unreal/import_nyaakoto_fp_paws.py FP_PAWS_UE_READY Saved/NyaakotoFPPaws/Unreal/import_v3.log`
   - **Check:** bounds against the build, all seven materials compiled, the dithered fur card material.
9. **Fresh-editor material proof.**
   - `UE scripts/unreal/verify_yumi_rig_materials.py YUMI_RIG_MATERIALS_OK Saved/YumiRig/material_check.log`
   - **Check:** `material_check.json`'s ordered rows. Every component index draws its asset's slot, and no engine default appears.
10. **First-person capture.**
    - `UE --editor scripts/unreal/render_yumi_fp_review.py YUMI_FP_REVIEW_COMPLETE Saved/YumiFP/capture_v3.log -- holds=rest,root,right_cheek,paw res=1920x1080 out=v3`
    - Expect four lit originals and three ID originals (the eye-view holds).
    - **Its gates:** materials (before, and after each ID pass), pose, the right_cheek solve.
    - **If the editor hangs at exit** (as attempt 2 did): sample it, preserve everything, and ask for authorization before any signal. Record it as a failed run.
11. **Pixel analysis** (CPU).
    - `PY scripts/art/analyse_yumi_fp_review.py Saved/YumiFP/v3`
    - It fails closed on any missing, empty, mismatched or malformed input.
    - **Then** view every original, and post the analysis beside the manifest's socket math: root's boxes, the clear line, the 20 m miss, the near plane.

## Open decision for root, before step 5's static ledger

- **The question:** `create_runtime_weapon_build_all.py` records W18 only by rewriting the whole runtime-weapons manifest (`Content/SourceArt/Weapons/Runtime/manifest.json`) from the files on disk.
- **On this branch** that manifest is stale for every weapon since `f4e8a16` (October 18): 228 validator errors before any W18 change.
- **Option A: re-record all.** A full rewrite would clear them by re-recording files nobody has reviewed per weapon.
- **Option B: W18 only.** Record W18 alone, with a narrowly scoped update, leaving the other weapons' errors as they are for their own review.
- **Either way:** the 63 tracked renders of the blockout weapons (03, 11, 13, 16) stay unrecorded, by the manifest's own rule.
