"""Check the empty-fist morph targets that Unreal holds, on every LOD, from its own FBX export of the imported mesh.

UE 5.8's Python exposes a skeletal mesh's morph target names, but not their deltas. import_nyaakoto_third_person.py
therefore has Unreal export SK_NyaagyuSamurai to FBX, every LOD with its morph deltas (FbxSkeletalMeshExport.cpp
CreateMesh writes GetMorphTargetDeltas(LODIndex) per LOD node). This reads that file in a clean Blender session.

**For each LOD** (each mesh Unreal wrote), the checks are:
- **The keys:** shape keys PawEmpty_R and PawEmpty_L exist.
- **The rule:** each moves the vertices skinned to its hand bone to where nyaakoto_tp_paws.empty_points puts them
  from that LOD's own bind positions. The paw's frame and palm come from runtime_skin_manifest.json at full
  precision, so this is the build's own rule applied to what Unreal holds.
- **Nothing else moves:** no vertex outside the paws.

Unreal drops morph deltas under its own threshold, so a vertex at the edge of the knuckle blend may be left in place.
The tolerance (RULE_TOL_M) is set above that.

Run (Blender 5.2, read-only):
    Blender -b --factory-startup --python-exit-code 1 --python scripts/art/check_nyaakoto_ue_morph_export.py --
        <Unreal's export .fbx> <out.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nyaakoto_tp_paws as TPP  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
EXPORT, OUT = Path(ARGS[0]), Path(ARGS[1])
ROOT = Path(__file__).resolve().parents[2]
RECORD = json.loads((ROOT / "Content/SourceArt/Characters/Hero/runtime_skin_manifest.json").read_text())
RULE_TOL_M = 5e-5                     # 0.05 mm: float storage and Unreal's dropped tiny deltas, well under any visible
KEYS = ("PawEmpty_R", "PawEmpty_L")

paws = RECORD["third_person"]["paws"]["by_side"]
skels = {side: TPP.skeleton({k: (np.array(v) if isinstance(v, list) else v) for k, v in paws[side]["frame"].items()},
                            paws[side]["palm_radii_m"]) for side in ("R", "L")}
bpy.ops.import_scene.fbx(filepath=str(EXPORT))
meshes = sorted((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: o.name)
rows, failed = {}, []
for obj in meshes:
    mw = np.array([list(r) for r in obj.matrix_world])
    keys = obj.data.shape_keys
    names = [kb.name for kb in keys.key_blocks] if keys else []
    row = {"vertices": len(obj.data.vertices), "shape_keys": names}

    def world(block):
        co = np.empty(len(block.data) * 3, np.float32)
        block.data.foreach_get("co", co)
        return co.reshape(-1, 3).astype(np.float64) @ mw[:3, :3].T + mw[:3, 3]

    if not keys or not all(k in names for k in KEYS):
        row["failed"] = "missing morph targets"
        failed.append(obj.name)
        rows[obj.name] = row
        continue
    basis = world(keys.reference_key)
    group = np.array([obj.vertex_groups[max(v.groups, key=lambda g: g.weight).group].name if v.groups else ""
                      for v in obj.data.vertices])
    for key, side in zip(KEYS, ("R", "L")):
        got = world(keys.key_blocks[key])
        hand = group == f"hand_{side}"
        expect = TPP.empty_points(basis[hand], skels[side])
        err = np.linalg.norm(got[hand] - expect, axis=1)
        others = float(np.abs(got[~hand] - basis[~hand]).max()) if (~hand).any() else 0.0
        move = np.linalg.norm(got[hand] - basis[hand], axis=1)
        r = {"paw_vertices": int(hand.sum()), "moved_vertices": int((move > 1e-6).sum()),
             "max_move_cm": round(float(move.max()) * 100.0, 3) if hand.any() else 0.0,
             "rule_error_max_mm": round(float(err.max()) * 1000.0, 5) if hand.any() else None,
             "rule_error_p99_mm": round(float(np.percentile(err, 99)) * 1000.0, 5) if hand.any() else None,
             "others_max_move_mm": round(others * 1000.0, 5)}
        r["passes"] = bool(hand.sum() > 500 and err.max() < RULE_TOL_M and others == 0.0 and move.max() > 0.02)
        row[key] = r
        if not r["passes"]:
            failed.append(f"{obj.name}:{key}")
    rows[obj.name] = row
summary = {"export": str(EXPORT), "meshes": len(meshes), "rule_tolerance_mm": RULE_TOL_M * 1000.0, "lods": rows,
           "failed": failed}
OUT.write_text(json.dumps(summary, indent=2) + "\n")
print("NYAAKOTO_UE_MORPH_EXPORT " + json.dumps({"meshes": len(meshes), "failed": failed}), flush=True)
if failed or len(meshes) != 3:
    raise SystemExit(f"NYAAKOTO_UE_MORPH_EXPORT_FAILED {failed} meshes={len(meshes)}")
