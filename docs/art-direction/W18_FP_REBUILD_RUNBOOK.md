# W18 rebuild, bow paw and first-person capture: the runbook

**Status:**

- Root accepted this order (Codex, 2026-10-25 16:43 UTC). It **started** at
  root's explicit handback of the UE/Blender lane (2026-10-25, step 1 at
  17:59 UTC). Each step's evidence is in the mailbox.
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
| `UE` | `scripts/toolchain/run-editor-script.sh`. The default is `-nullrhi` in UnrealEditor-Cmd. `--rhi` renders offscreen in UnrealEditor-Cmd; `--editor` uses the full UnrealEditor. It passes with the completion marker and no Python error lines, and exit 0. The one exception is exit 1 from a full editor (`--editor`) that quit itself; a commandlet's exit 1 fails (`scripts/toolchain/test_run_editor_script.py`) |
| PIDs | `pgrep -x Blender`, `pgrep -x UnrealEditor-Cmd` (default and `--rhi`) or `pgrep -x UnrealEditor` (`--editor`). Never `pgrep -f`, which matches the launching shell |
| Archive | `Saved/W18Rebuild/Archive/<step>/`: a copy of everything the step will overwrite, with SHA256SUMS, made read-only before it runs |
| Times | `date -u` at start and end, in `Saved/W18Rebuild/<step>.times` |

**Test counts** are reported as unittest gives them: run, passed, expected
failures and skipped. Never a run total called "passed".

**Exit codes** are evidence, reported as they were:
- **An Unreal step:** the editor's own exit, from the wrapper's
  `EDITOR_EXIT=<n>` line and `<log>.editor-exit`, beside the wrapper's own
  exit. A full editor that quits itself exits 1, and the wrapper accepts it;
  it is reported as **editor exit 1, wrapper exit 0**, never as 0/0.
- **A Blender step:** Blender's own exit status.
- **EOF** means the process has exited and its output streams have reached
  end of file: the launching command returned, with that process's status.
  A last log line alone is not EOF, as attempt 2's editor showed: it logged
  `Exiting.` and then hung. A process that never exits is preserved and
  recorded as a failed or incomplete run, never as EOF.

**Provenance is not admission.** An OWN ledger or record states authorship
and the exact bytes of files. Whether the geometry or the look is accepted is
root's review of the originals, never a ledger's.

## The steps

1. **Timber patch study** (Blender, CPU).
   - `B scripts/art/render_timber_patch_study.py -- --cpu --raw /Users/mtakemiya/.codex/worktrees/complete-game/sora-arena/Local/ThirdPartyRaw`
   - Marker `PATCH_STUDY_READY`. It writes `Local/ArtCache/NyaagyuDojoTimbersV23Patch/attempt<N>/`, created exclusively, so no archive is needed.
   - **Check:** view both contact sheets and every panel. `study.json` must hold both variants' measurements beside the scans'. The EXR normal-map read must pass its unit-normal check, or the study stops (that is a result, not a retry).
   - **Done (attempt 0, kept unchanged).** Its render slopes were 1000 times their value: Cycles' camera space looks along +z, and the study divided by +z clamped at 1e-3. `7b38f6e` fixed the decode (`camera_normal_slope.py`, tested); `--reanalyse` recomputed the slopes from attempt 0's retained renders into `attempt0_reanalysis0/`, rendering nothing. No timber production batch follows from an unreviewed metric.
2. **W18 static rebuild** (Blender).
   - **The raw CC0 inputs.** The weapon library reads them only at `Local/ThirdPartyRaw/cc0` (`create_runtime_weapon_lib.cc0`).
     - Nine of W18's sixteen were missing from this worktree. They are **copied** into its ignored `Local/ThirdPartyRaw`, relative paths kept (Codex authorized this, 2026-10-25; a symlink would not make root's cache read-only).
     - All sixteen were verified against the ledger before and after the copy. The receipt is `Saved/W18Rebuild/raw_inputs_copy.json`.
     - The copies stay through step 5's final ledger and check.
   - Before the build, `PY scripts/art/record_runtime_weapon.py --weapon 18 --preflight` must print `RECORD_PREFLIGHT_OK`. It did on 2026-10-25, after the copy.
   - **Archive** `Content/SourceArt/Weapons/Runtime/W18_Yumi/{*.fbx,*.blend,T_Weapon_18_*.png,build_record.json}`, `Runtime/Renders/SM_Weapon_18*.png` and `Runtime/metric_report.json`. Hash the whole `Runtime/` tree too.
   - `B scripts/art/create_runtime_weapon_yumi.py -- --only 18`, then `B scripts/art/create_runtime_weapon_validation.py -- --only 18`. These are the two Blender jobs `create_runtime_weapon_build_all.py --only 18` runs, without its manifest rewrite, which would re-record every weapon (root's decision B, below).
   - **The validation's exit, and the scoped W18 gate** (root's rule, below):
     - The validator rewrites the whole `metric_report.json`. It exits from the summary of every row, and the four blockout rows fail, so it exits 1 whatever W18 does. That exit and the full report are kept and reported as they are.
     - **Separately**, after archiving the rewritten report: `PY scripts/art/check_scoped_validation.py --weapon 18 --expected-failures 3,11,13,16 --before <the archived report> --after Content/SourceArt/Weapons/Runtime/metric_report.json --build-record Content/SourceArt/Weapons/Runtime/W18_Yumi/build_record.json --log Saved/W18Rebuild/s2_validate.log --validator-exit <its real exit> --out Saved/W18Rebuild/s2_scoped_validation.json` must print `SCOPED_VALIDATION_OK`.
       - It recomputes W18's row rather than trusting its pass bits (root's probes of `fe74f78`). It checks the exact identity and the validator's complete, unique check inventory, and the authored expected, tolerance, budget, method, basis and source. Measurements must be finite. Each check must pass by the validator's own rule, which its source must still state, and the triangles and texel density must be the build record's.
       - It also checks that the failing rows are exactly 03/11/13/16 before and after, and that every other row is byte-identical.
       - Both summaries' counts must match their rows. The exit must be what the summary implies (`test_check_scoped_validation`).
     - The `Runtime/` tree after: only W18's static outputs, its three renders, an ignored `*.blend1` and `metric_report.json` may differ.
     - Any new failure, or any unrelated change, stops the sequence.
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
   - **Ledgers** (decision B: W18 only):
     - **The W18 static:** `PY scripts/art/record_runtime_weapon.py --weapon 18 --generator scripts/art/yumi_nigiri.py --generator scripts/art/yumi_ya.py`, then the same with `--check`. It must exit 0, "matches, provenance included".
       - Both runs first validate provenance: every derived input present at its sources_manifest.json hash, and every generator present. They fail otherwise.
       - A check matches only when the latest scoped record names the same generator and input hashes and files.
       - It replaces only W18's scope in the runtime-weapons manifest: its static outputs (not `Rig/`, which keeps its own ledger, nor `*.blend1`) and its renders.
       - Every other weapon's entry is kept exactly, stale or not (`test_record_runtime_weapon`).
       - It records W18's generators and derived inputs by SHA-256, as OWN provenance, not admission.
     - **The metric report's ledger entry** (an explicit W18-scoped exception):
       - The runtime-weapons manifest records `metric_report.json`'s bytes and hash. That one global metadata record changes only because W18's row and the summary did.
       - It is updated only with the scoped gate passing again, on the archived report before step 2 and the file now. The scoped update records the before and after.
       - No other weapon's entry or output is refreshed.
       - At integration, root applies the same reviewed W18 row and summary to root's validated baseline, and updates that one hash.
     - **The rig:** regenerate `W18_Yumi/Rig/manifest.ledger.json` (`scripts/assets/write_own_ledger.py`, its original arguments, after the rebuilt files are staged).
     - **Never** run `create_runtime_weapon_build_all.py` or `--manifests-only`. They re-record every weapon.
     - **Validate:** `scripts/assets/validate_asset_ledger.py` before and after. The only errors that may go are W18's; none may be added.
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

## Root's decision: W18 only (Codex, 2026-10-25)

- **Decision B.** Record the exact new W18 static outputs, their generators
  and their derived inputs, plus the separate rig and paw ledgers. Never
  re-record all weapons, or clear unrelated errors by refreshing their
  hashes.
- **Tool:** `scripts/art/record_runtime_weapon.py`. Its fixtures prove
  every unrelated entry is kept exactly.
- **At integration:** root keeps root56's independently validated ledger
  baseline and merges only the reviewed W18 records and files. This
  branch's 228-error baseline, stale since `f4e8a16` (before this work),
  is not a replacement for it.
- **Either way:** the blockout weapons' tracked renders (03, 11, 13, 16)
  stay unrecorded here, by the manifest's own rule.

## Root's rule for the targeted validation (Codex, 2026-10-25)

- **The real exit stays.** `--only 18` returns 1 from the accumulated
  summary. That exit and the full report are kept, archived before and
  after, and never reported as a pass.
- **The narrow expected-baseline exception** gates the new W18 row
  separately. It holds **only if** W18 passes every check, the four
  blockout failures are exactly the unchanged pre-run failures (03, 11, 13,
  16), and every other weapon record stays byte-identical. Any new failure or
  unrelated record change stops the sequence.
- **The report's metadata** may change only in W18's row and its summary.
  Its ledger hash in the runtime-weapons manifest is the one W18-scoped
  metadata exception, with a before/after comparison. No other weapon output
  is refreshed.
- **At integration** root applies the same reviewed W18 row and summary to
  root's validated baseline, and updates that single metadata hash.
