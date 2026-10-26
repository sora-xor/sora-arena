# Runtime weapon sockets: the scoped export correction (measured)

**Status (2026-10-26):** the CPU tools, the plan and the CPU results are signed. Section 8 records the staging
re-exports and the real UE probes. Nothing in a kit folder has changed yet. Root owns the eventual runtime adoption.

## 1. The defect

**The cause.** Every runtime weapon kit was exported by the shared library (`create_runtime_weapon_lib.py`
split_and_export): axis_forward -Y with FBX_SCALE_NONE. The drone's fc0858a9 LOD0 used the same export, and root's
real UE 5.8 import of it read its sockets at scale 100, turned.

**The cause, in UE 5.8's source** (`fbx_unreal_sockets.py`):
- Interchange converts a file whose axes are not its import axes, by a rotation C.
- It applies its AxisConversionInverseTransform A⁻¹ to every socket.
- A baked socket keeps its parent node's ×100.

**A⁻¹ is not C⁻¹.** Measured from the real rotators of root's drone imports (runs s79 and s80):
- for the library's axes, A⁻¹ is a 180° turn about Y;
- C is a 180° turn about Z;
- so a socket's **forward and up are reversed and its right is kept**.

**The screen** (`screen_fbx_sockets.py`, data in `data/weapon_socket_screen.json`) predicts this for all **83
sockets in the 26 socketed weapon FBXs**: scale 100, forward and up reversed, right kept. The drone's 2 sockets pass.
It is a prediction until real imports read the files back (section 8).

**Superseded.** My first model (45a2af0a) used C⁻¹ and predicted the up axis kept, a turn about Z. That matched the
drone's forward vectors, positions and scales, which were all it compared. Its weapon predictions are kept in
`data/weapon_socket_screen_superseded.json`.

## 2. Who reads weapon sockets

The C++ is in root's tree, at `95ef38ca`.

| consumer | reads |
| --- | --- |
| `SoraViewmodelComponent.cpp:20-30` AdmittedSocketsAndMaterials | Grip_R, Grip_L, Muzzle: present, no NaN, **scale 1 within 1e-4**; the rotation is NaN-checked only. Weapons 0-17 only; 0, 1 and the bokken are approximate. |
| `SoraViewmodelComponent.cpp:73-75` | the pose anchor (Grip_R or Grip_L): RelativeLocation only. "do not undo its rotation" (W15's grip axes turn 90°). |
| `SoraViewmodelComponent.cpp:211-216` PresentationSocketWorld | any socket's **full world transform**. Today's one caller is `SoraViewmodelPresentationAutomation.cpp:145`, which asserts that the proxy bow has none. |
| `viewmodels.json` socket_frame | sockets in Blender metres; `socket_axes` for W02 Grip_L and W15 Grip_R; for other sockets, "read their full transforms from the imported mesh". |
| `SoraViewmodelPresentation.cpp:103-113` | `sockets_from` must be the kit's build_record.json. |
| `check_viewmodel_framing.py` | record positions, and the builder-call provenance of `socket_axes`. It never reads the FBX. |
| drone: `SoraEnemyDrone.cpp:31-33`, `SoraEnemy.cpp:80,85` | the drone's scale gate and socket locations. |

**What Unreal holds today.**
- `/Game/Generated/Meshes/SM_Weapon_00..17` come from `Content/SourceArt/SM_Weapon_XX.fbx`
  (`import_original_assets.py:160-185`). Those files carry **no SOCKET_ nodes at all**, so no weapon from 2 to 17
  can pass admission today.
- The runtime kits are not imported anywhere.
- So the defect is latent until the kits are adopted. Admitting a kit as it stands would fail on scale, as the
  stricter gate should.

## 3. Inventory: 26 files, 83 sockets

**The files:**
- **23 files are byte-identical** in root's tree and in this one.
- **W14 (1 file).**
  - Root's `3b0a662d` "Recover W14 source outputs and reconcile verified weapon provenance" makes W14's record match
    its files, in root's tree only.
  - Here W14 is a stale, interrupted state: its LOD0 and blend do not match its record.
  - So W14 is staged from root's tree, read-only, and labelled so.
- **W18 (2 files).**
  - Here, W18 is my unintegrated rebuild (`b55fe81a`..`de70236e`). Root's W18 is older.
  - So W18 is staged from this tree, labelled as mine. Root's runtime refuses ids 18 and up in any case.

**The manifests.**
- Root's `Weapons/Runtime/manifest.json` (`3b0a662d`) is current for 22 socketed files, and does not list W03, W11,
  W13 or W16 (held back).
- This tree's copy is older, with my W18 scoped update.

## 4. Frozen digests and gates, kept

**The library.** `create_runtime_weapon_lib.py` is not edited.
- Root's copy, `1068e8c0`, is pinned by the dojo timber manifests (`test_sora_timber_v2`).
- My copy, `7312e9f2`, is pinned by the W18 rig record and by my manifest's W18 scoped update.
- The two copies differ only in W18's bamboo-material options.
- `test_weapon_socket_export.py` reads the library's one export call from its source and proves that the new export
  differs only in axis_forward and bake_space_transform.

**Staging writes no kit file.** The kit FBXs, records, blends, maps, LOD1 and LOD2 are not written.
- The tool checks every input hash before, and the other LODs and the blend after.
- A later apply changes only:
  - each socketed LOD0;
  - its record: LOD0's hash, `socket_axes` and a `socket_fbx` block;
  - the manifest: the rewritten files' entries and one scoped update.
- `amend_record` is tested to change nothing else, and apply refuses a record or manifest it would reformat.

**Gates that stay as they are:**
- `create_runtime_weapon_validation.py`, unchanged. It measures sockets and bounds in world space, so the corrected
  files should pass it. It runs in the apply window.
- `viewmodels.json`, `check_viewmodel_framing.py` and AdmittedSocketsAndMaterials.
- No transform is normalized after import.

## 5. The correction

**The convention** is the drone's (`fbx_socket_export.SOCKET_FBX`): Blender's own axes, which are Unreal's import
axes, with the unit baked. No importer converts the file, and no node carries a rotation or a scale. Everything else
is the library's LOD0 call.

**The tool** is `reexport_runtime_weapon_sockets.py`.
- `--stage` writes to Saved/ only. `--source-root` reads another tree, read-only.
- `--apply` (later) writes in place, with an archive.
- Its checks:
  - inputs against the record;
  - the blend's socket positions;
  - the new file through the rule: unit scale, the blend's axes and the record's positions;
  - every geometry array against the original: vertices ×100, the rest equal, the material layer included.

**The UE probe** is `probe_runtime_weapon_sockets.py`. It imports the original and the corrected file with
`import_original_assets.py`'s weapon options, and saves nothing. It reads back:
- every socket's position, scale, and signed forward, right and up;
- LOD0's render arrays, the material slots and the collision counts.

Its gates are in `weapon_socket_gates.py`:
- the corrected file meets admission's unit scale and the authored frame on all three axes;
- its import repeats the original's geometry, slots and collision counts;
- both imports follow the model on every axis.

## 6. Sequence

1. **Done:** the CPU tools, the plan and the CPU results (section 7), signed.
2. **This window:**
   - s81: a Blender staging re-export of this tree's 25 files, W18 included;
   - s82: a Blender staging re-export of root's W14;
   - s83: one UE probe of all 26 pairs.
   - Then the evidence is signed and the lane handed back.
   - All 26 are staged and probed, not a sample: staging writes only Saved/, the probe saves nothing, and the full
     set leaves no file trusted on the model alone.
3. **Root's call: the apply.**
   - Which base? Either a fresh branch from root's head, which cherry-picks cleanly, or this branch after taking
     root's W14 and manifest.
   - W18: with root's adoption of my rebuild, or not.
   - Then `--apply`, the screen with exit 0, `create_runtime_weapon_validation.py`, and a probe of the in-place files.
4. **Root's runtime adoption** of the kits into `/Game/Generated/Meshes`.
5. **A rebuild would regress.** Any kit rebuild with the frozen library writes the old convention again, so it must
   be followed by the socket re-export. That holds until root decides to change the library's export and re-freeze
   its pins.

## 7. CPU results (this tree, before staging)

**Tests.** test_weapon_socket_export, test_fbx_unreal_sockets and test_inventory_drone_record: **31 run: 31 passed,
0 failed, 0 skipped**. Earlier runs failed on two mistakes in my own test code, both fixed:
- 17 run: 16 passed, 1 failed, from a synthetic expectation that missed Unreal's left-handed Y sign;
- 14 run: 13 passed, 1 error, from an AST helper meeting `filepath=str(path)`.

**The screen.** 27 files, 85 sockets; 83 failing sockets in 26 files; 0 unreadable; exit 1. In every failing row
the forward and up are reversed, the right is kept, and the scale is 100.

## 8. Staging and UE results

Logs are in `Saved/W18Rebuild/`; outputs are in `Saved/WeaponSocketFix/`. Every run ended in a natural exit.

**s81, staging from this tree (failed, kept).** Blender pid 36515, 04:21:44-04:21:47Z, exit 1.
- It stopped at its first file, SM_Weapon_00, on the tool's own array gate: `LayerElementBinormal[1].Binormals` was
  4.7e-6 from the original, against 1e-6.
- It wrote no staging report.

**s82, a diagnosis** (`diagnose_weapon_socket_reexport.py`; pid 37447, 04:23:18-04:23:29Z, exit 0).
- **What it did:** each of this tree's 25 socketed LOD0s was exported twice from its reloaded blend, once in the
  library's convention (control) and once in the socket convention (corrected). W14 was skipped as stale here.
- **What it found:** in all three comparisons (control against original, corrected against control, corrected
  against original), every array but the tangent basis matches exactly: vertices ×100, indices, edges, normals,
  UVs, materials and smoothing.
- **The tangents and binormals do not reproduce** from one export to the next, even within one session.
  - The worst is 7.1e-6, in W00.
  - About 70,000 of W00's 195,816 loops differ by one float32 ulp (median 5.96e-8), and 6 by more than 1e-6.
  - Those 6 are in the control export, not the corrected one.
- So the 1e-6 gate was miscalibrated, for these two derived arrays only. The drone's one pair happened to show
  1.8e-7. The tool now gates the tangent basis at 1e-4 and keeps every other array at 1e-6.
- Data: `data/weapon_socket_reexport_diagnosis.json`.

**s83, staging from this tree** (claude/photoreal-art at 77e35643; pid 39086, 04:25:32-04:25:44Z, exit 0).
- 25 files and 79 sockets were staged to `Saved/WeaponSocketFix/s83_stage_art/`, with every gate passed.
- Through the rule, each socket is at scale 0.9999998 to 1, on the blend's axes and at the record's positions.
- Against the originals:
  - every array is exact but the tangent basis, whose worst is 7.1e-6;
  - Interchange's baked vertices are within 2.8e-5 cm.
- W18 is my rebuild (kit last commit `b0eef326`). Content/ is unchanged.

**s84, root's W14, read-only** (`codex/complete-game`, kit at `3b0a662d`; pid 40040, 04:26:42-04:26:44Z, exit 0).
- 1 file and 4 sockets were staged to `Saved/WeaponSocketFix/s84_stage_root_w14/`, with every gate passed.
- Git in root's tree ran with `--no-optional-locks`, and `git status -- Content/` there is still empty.

**s85, the UE 5.8 probe** (wrapper 40367, UnrealEditor-Cmd 40485, 04:26:59-04:27:57Z; editor exit 0, wrapper 1).
- **Sockets:** all 83 corrected sockets pass: the record's position within 0.02 cm, scale 1 within 1e-4, and signed
  forward, right and up on the authored axes. Every original fails as the model predicted: scale 100, forward and
  up reversed, right kept.
- **The model** matches every axis of all 52 imports: position within 7.1e-6 cm, scale 6.8e-8, axes 1.1e-7. The
  screen's predictions for the files not yet probed are therefore backed by this measurement, but they remain
  predictions.
- **Material slots** are equal for all 26 pairs. **Collision** is 0 convex and 0 other in every import.
- **The wrapper's exit 1** came from my own same_import gate, which compared whole render arrays:
  - **24 pairs** have the same render layout, UVs exact, positions within 3.2e-5 cm, and normals and tangents
    within one 8-bit step (1/127 = 0.0079). The exception is one W01 tangent, at 0.0249.
  - **W11 and W13:** the corrected import has one more render vertex (12,156 against 12,155; 6,628 against 6,627),
    with the same triangle counts and bounds within 5e-6 cm.
  - **The likely cause**, not yet measured: the original's node turn is 179.999991°, not 180°. Its import is
    rotated by 8.65e-6°, which flips a few 8-bit roundings and one vertex-welding decision; the corrected file has
    no turn.
- **The gate is reworked** (weapon_socket_gates.same_import), and the next run, s86, tests the cause:
  - it compares corner by corner, in 8-bit steps and degrees;
  - it imports the s82 control as a third file. The control is the library's convention from the same blend, so it
    carries the original's inexact turn.

**s86, the UE 5.8 probe with controls** (wrapper 47437, 04:31:34-04:33:06Z; editor exit 0, wrapper 1; the editor's
pid was not sampled).
- **Sockets:** again, all 83 corrected sockets pass, and the model matches every axis of all imports.
- **The attribution, measured:**
  - **original against control** is bit-identical in UE for all 25 pairs: positions 0.0, normals and tangents 0
    steps, the same render vertex counts. The control's FBX tangents differ by up to 7.1e-6, so Unreal recomputes
    the tangents and ignores the file's.
  - **control against corrected** repeats the original-against-corrected numbers in every row. So the differences
    come from the convention change alone: removing the original's 179.999991° node turn.
- **The 24 pairs with the same layout** pass the corner gate:
  - positions within 3.2e-5 cm;
  - normals within one 8-bit step, at no more than 12 corners;
  - tangents within one step, except W01, where 42 corners differ and the worst by 3 steps.
- **W11 and W13** failed the corner gate. Unreal ordered their triangles differently, together with the one extra
  render vertex, so pairing corners in index order compared unrelated corners. same_import now matches triangles by
  their corners, keeping the winding, when index order does not line up (`corner_pairs`). Next run: s87.

**s87, the probe with triangle matching** (wrapper 50281, 04:35:09-04:35:59Z; editor exit 0, wrapper 0, marker
printed; the editor's pid was not sampled).
- **It passed every gate of that probe version** (dabc60a1):
  - all 83 corrected sockets pass, and the model matches every axis;
  - W11 and W13 pair by matching ("matched"), with positions within 8.5e-6 cm and UVs exact;
  - the worst over all 26 pairs: positions 3.2e-5 cm, normals one step (0.45°), tangents 1.43°;
  - original against control is exact for all 25.
- **That pass is not taken as clean.** W11's tangents differ by up to 125 8-bit steps while their worst angle is
  1.39°, which two unit vectors cannot do.
  - So at least one W11 corner has a degenerate (zero) tangent in one import only, and the angle check read it as
    0°: atan2(0, 0).
  - The gate now counts such corners apart and fails them (`tangent_degenerate_mismatches`), and `detail=` keeps
    the worst corners in full. Next run: s88.
