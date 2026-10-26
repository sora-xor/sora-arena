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

(Filled in by the evidence commit.)
