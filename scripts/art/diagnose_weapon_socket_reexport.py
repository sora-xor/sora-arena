"""Measure, without gating, how a socketed weapon LOD0 re-exported from its reloaded blend differs from the
original FBX. It separates the convention change from what reloading the blend alone changes.

Run (Blender 5.2.2, by the holder of the engine/Blender lane):
  blender -b --factory-startup --python-exit-code 1 --python scripts/art/diagnose_weapon_socket_reexport.py
      -- --out Saved/<dir> [--source-root <tree>] [--only W00_Katana,...]

**Why.** Staging run s81 stopped at SM_Weapon_00: LayerElementBinormal[1].Binormals was 4.7e-6 from the original,
against reexport_runtime_weapon_sockets.py's 1e-6. The convention's normal matrix is the exact identity, so the
re-export should leave the tangent basis alone; reloading the blend may not.

**What it writes.** For every socketed LOD0, two files under <dir>/<kit>/:
- control/<file>: the library's own convention (fbx_socket_export.LIBRARY_CONVENTION), from the reloaded blend;
- corrected/<file>: the socket convention.

**What it measures,** per geometry array (worst absolute difference):
- control against the original: what the reload changes;
- corrected against control, with control's vertices x100: what the convention changes;
- corrected against the original.

Nothing under Content/ is written, no blend is saved, and nothing is gated beyond the inputs' hashes.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np

passed = False


def fail_on_exit():
    if not passed:
        sys.stdout.flush()
        os._exit(1)


__import__("atexit").register(fail_on_exit)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fbx_socket_export as X  # noqa: E402
import fbx_unreal_sockets as F  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


OUT = (ROOT / opt("--out")).resolve()
assert OUT.is_relative_to(ROOT / "Saved"), "the out dir must be under this worktree's Saved/"
SRC = Path(opt("--source-root", str(ROOT))).resolve()
RUNTIME = SRC / "Content/SourceArt/Weapons/Runtime"
ONLY = set(opt("--only", "").split(",")) - {""}


def worst(a_path, b_path, asset, scale_a=1.0):
    a, b = F.geometry_arrays(a_path)[asset], F.geometry_arrays(b_path)[asset]
    out = {"_keys_differ": sorted(set(a) ^ set(b))} if set(a) != set(b) else {}
    for key in sorted(set(a) & set(b)):
        x, y = a[key].astype(float), b[key].astype(float)
        if x.shape != y.shape:
            out[key] = f"shape {x.shape} against {y.shape}"
            continue
        out[key] = float(np.abs((x * scale_a if key == "Vertices" else x) - y).max()) if x.size else 0.0
    return out


rows = []
head = subprocess.run(["git", "-C", str(SRC), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
for rec_path in sorted(RUNTIME.glob("W*/build_record.json")):
    kit = rec_path.parent
    if ONLY and kit.name not in ONLY:
        continue
    record = json.loads(rec_path.read_text(encoding="utf-8"))
    assets = [(a, e) for a, e in record["assets"].items() if e.get("sockets")]
    if not assets:
        continue
    stale = [e["lods"][0]["file"] for _a, e in assets if X.sha256(SRC / e["lods"][0]["file"]) != e["lods"][0]["sha256"]]
    if stale or X.sha256(SRC / record["blend"]["file"]) != record["blend"]["sha256"]:
        rows.append({"kit": kit.name, "skipped": "the record and the files differ in this tree", "files": stale})
        print("WEAPON_REEXPORT_DIAG " + json.dumps(rows[-1]), flush=True)
        continue
    bpy.ops.wm.open_mainfile(filepath=str(SRC / record["blend"]["file"]), load_ui=False)
    for asset, entry in assets:
        original = SRC / entry["lods"][0]["file"]
        mesh = bpy.data.objects[asset]
        empties = sorted((o for o in bpy.data.objects if o.parent == mesh and o.name.startswith("SOCKET_")),
                         key=lambda o: o.name)
        for o in (mesh, *empties):
            o.hide_set(False)
            o.hide_viewport = False
        paths = {}
        for tag, convention in (("control", X.LIBRARY_CONVENTION), ("corrected", X.SOCKET_FBX)):
            paths[tag] = OUT / kit.name / tag / original.name
            paths[tag].parent.mkdir(parents=True, exist_ok=True)
            assert not paths[tag].exists(), paths[tag]
            X.export(paths[tag], mesh, empties, convention)
        row = {"kit": kit.name, "asset": asset, "original_sha256": X.sha256(original),
               "control_sha256": X.sha256(paths["control"]),
               "reload": worst(original, paths["control"], asset),
               "convention": worst(paths["control"], paths["corrected"], asset, scale_a=100.0),
               "corrected_vs_original": worst(original, paths["corrected"], asset, scale_a=100.0)}
        rows.append(row)
        print("WEAPON_REEXPORT_DIAG " + json.dumps(row), flush=True)
    assert X.sha256(SRC / record["blend"]["file"]) == record["blend"]["sha256"], "the blend changed"
(OUT / "diagnosis.json").write_text(json.dumps({"source": {"root": str(SRC), "head": head},
                                                "blender": bpy.app.version_string, "rows": rows}, indent=1) + "\n")
print("WEAPON_REEXPORT_DIAG_DONE " + json.dumps({"files": sum(1 for r in rows if "asset" in r),
                                                 "skipped": [r["kit"] for r in rows if "skipped" in r]}))
passed = True
