"""Check the empty-fist morph targets that Unreal holds, on every LOD, from its own FBX export of the imported mesh.

UE 5.8's Python exposes a skeletal mesh's morph target names, but not their deltas. import_nyaakoto_third_person.py
therefore has Unreal export SK_NyaagyuSamurai to FBX, every LOD with its morph deltas (FbxSkeletalMeshExport.cpp
CreateMesh writes GetMorphTargetDeltas(LODIndex) per LOD node). This reads that file in a clean Blender session.

**For each LOD** (each mesh the import made; --factory-startup's own cube is not one), the checks are:
- **The keys:** shape keys PawEmpty_R and PawEmpty_L exist.
- **The rule:** each moves the vertices skinned to its hand bone to where nyaakoto_tp_paws.empty_points puts them
  from that LOD's own bind positions. The paw's frame and palm come from runtime_skin_manifest.json at full
  precision, so this is the build's own rule applied to what Unreal holds. The paw module must be the one that built
  the assets (the manifest's module_sha256).
- **Unreal's threshold, modelled:** Unreal keeps a vertex's delta only if it moves more than the LOD's
  MorphThresholdPosition, or, when normals are computed, if its normal turns enough (LODUtilities.cpp:3132). So:
  - a vertex whose rule move is above the threshold must be at the rule;
  - one at or below it (UE_BAND_M either side, for float storage) must be either at the rule or unmoved.
  Both are measured to RULE_TOL_M. s111 compared every vertex with the rule alone and failed on every LOD at
  0.14-0.15 mm, the dropped deltas.
- **Each LOD's own threshold**, read back from the saved asset (--thresholds):
  - either the import's readback, `morph_targets.lod_build`;
  - or a LOD-material readback, `lods[].morph_threshold_position_cm` (s114's).
  The engine's default is 0.015 cm (EngineTypes.h:3181). Root asked (13:19 UTC, 2026-10-26) that the check use the
  saved value rather than assume the default. s112 and s113 used the default; s114 then read 0.0149999997 cm on
  every LOD.
- **Nothing else moves:** no vertex outside the paws.

Run (Blender 5.2, read-only):
    Blender -b --factory-startup --python-exit-code 1 --python scripts/art/check_nyaakoto_ue_morph_export.py --
        <Unreal's export .fbx> <out.json> --thresholds <the import's or s114-style readback .json>
"""
from __future__ import annotations

import hashlib
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
MODULE_SHA = hashlib.sha256(Path(TPP.__file__).read_bytes()).hexdigest()
if MODULE_SHA != RECORD["third_person"]["paws"]["module_sha256"]:
    raise SystemExit(f"NYAAKOTO_UE_MORPH_EXPORT_FAILED: {TPP.__file__} ({MODULE_SHA[:12]}) is not the paw module that "
                     f"built the assets ({RECORD['third_person']['paws']['module_sha256'][:12]})")
RULE_TOL_M = 5e-5                     # 0.05 mm: float storage, well under any visible
UE_BAND_M = 1e-6                      # 0.001 mm either side of it: Unreal measured its delta in its own floats
KEYS = ("PawEmpty_R", "PawEmpty_L")
if "--thresholds" not in ARGS:
    raise SystemExit("NYAAKOTO_UE_MORPH_EXPORT_FAILED: --thresholds <readback .json> is required: each LOD's saved "
                     "MorphThresholdPosition, not the engine's default")
THRESHOLDS_FROM = Path(ARGS[ARGS.index("--thresholds") + 1])
_tr = json.loads(THRESHOLDS_FROM.read_text())
_rows = (_tr["morph_targets"]["lod_build"] if "morph_targets" in _tr and "lod_build" in _tr["morph_targets"]
         else _tr.get("lods", []))
THRESHOLD_M = {int(r["lod"]): float(r["morph_threshold_position_cm"]) / 100.0 for r in _rows
               if "morph_threshold_position_cm" in r}
if not THRESHOLD_M:
    raise SystemExit(f"NYAAKOTO_UE_MORPH_EXPORT_FAILED: no LOD's MorphThresholdPosition in {THRESHOLDS_FROM}")

paws = RECORD["third_person"]["paws"]["by_side"]
skels = {side: TPP.skeleton({k: (np.array(v) if isinstance(v, list) else v) for k, v in paws[side]["frame"].items()},
                            paws[side]["palm_radii_m"]) for side in ("R", "L")}
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(EXPORT))
meshes = sorted((o for o in bpy.data.objects if o.type == "MESH" and o not in before), key=lambda o: o.name)
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
    lod = int(obj.name.rsplit("_LOD", 1)[1]) if "_LOD" in obj.name else None
    if lod not in THRESHOLD_M:
        row["failed"] = f"no saved MorphThresholdPosition for LOD {lod} in {THRESHOLDS_FROM.name}"
        failed.append(obj.name)
        rows[obj.name] = row
        continue
    threshold_m = THRESHOLD_M[lod]
    row["unreal_morph_threshold_mm"] = threshold_m * 1000.0
    basis = world(keys.reference_key)
    group = np.array([obj.vertex_groups[max(v.groups, key=lambda g: g.weight).group].name if v.groups else ""
                      for v in obj.data.vertices])
    for key, side in zip(KEYS, ("R", "L")):
        got = world(keys.key_blocks[key])
        hand = group == f"hand_{side}"
        bind = basis[hand]
        expect = TPP.empty_points(bind, skels[side])
        rule_move = np.linalg.norm(expect - bind, axis=1)
        to_rule = np.linalg.norm(got[hand] - expect, axis=1)
        to_bind = np.linalg.norm(got[hand] - bind, axis=1)
        must_keep = rule_move > threshold_m + UE_BAND_M
        may_drop = ~must_keep
        err = np.where(must_keep, to_rule, np.minimum(to_rule, to_bind))
        static = rule_move < 1e-9                          # the palm: the rule does not move it
        dropped = may_drop & ~static & (to_bind < to_rule)
        kept = may_drop & ~static & ~dropped
        others = float(np.abs(got[~hand] - basis[~hand]).max()) if (~hand).any() else 0.0
        move = to_bind

        def mm(x):
            return round(float(x.max()) * 1000.0, 5) if x.size else None

        r = {"paw_vertices": int(hand.sum()), "moved_vertices": int((move > 1e-6).sum()),
             "max_move_cm": round(float(move.max()) * 100.0, 3) if hand.any() else 0.0,
             "rule_moves_above_threshold": int(must_keep.sum()),
             "rule_error_above_threshold_max_mm": mm(to_rule[must_keep]),
             "rule_error_above_threshold_p99_mm": (round(float(np.percentile(to_rule[must_keep], 99)) * 1000.0, 5)
                                                   if must_keep.any() else None),
             "rule_moves_at_or_below_threshold": int(may_drop.sum()), "of_which_rule_static": int(static.sum()),
             "of_which_unreal_dropped": int(dropped.sum()), "of_which_unreal_kept": int(kept.sum()),
             "below_threshold_error_max_mm": mm(err[may_drop]),
             "largest_dropped_rule_move_mm": mm(rule_move[dropped]),
             "rule_only_error_max_mm": mm(to_rule),
             "others_max_move_mm": round(others * 1000.0, 5)}
        r["passes"] = bool(hand.sum() > 500 and err.max() < RULE_TOL_M and others == 0.0 and move.max() > 0.02)
        row[key] = r
        if not r["passes"]:
            failed.append(f"{obj.name}:{key}")
    rows[obj.name] = row
summary = {"export": str(EXPORT), "meshes": len(meshes), "paw_module": {"file": TPP.__file__, "sha256": MODULE_SHA},
           "rule_tolerance_mm": RULE_TOL_M * 1000.0,
           "unreal_morph_threshold_mm_by_lod": {lod: t * 1000.0 for lod, t in sorted(THRESHOLD_M.items())},
           "thresholds_from": {"file": str(THRESHOLDS_FROM),
                               "sha256": hashlib.sha256(THRESHOLDS_FROM.read_bytes()).hexdigest()},
           "unreal_band_mm": UE_BAND_M * 1000.0, "lods": rows, "failed": failed}
OUT.write_text(json.dumps(summary, indent=2) + "\n")
print("NYAAKOTO_UE_MORPH_EXPORT " + json.dumps({"meshes": len(meshes), "failed": failed}), flush=True)
if failed or len(meshes) != 3:
    raise SystemExit(f"NYAAKOTO_UE_MORPH_EXPORT_FAILED {failed} meshes={len(meshes)}")
