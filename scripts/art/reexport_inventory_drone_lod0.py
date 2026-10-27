"""Re-export the Inventory drone's LOD0 FBX alone, from the reviewed kit blend, in the UE 5.8 socket convention.

Run: blender -b --factory-startup --python-exit-code 1 --python scripts/art/reexport_inventory_drone_lod0.py
         -- --original <the archived fc0858a9 LOD0 FBX>

**Why.** Root's import of fc0858a9 (0eb8c5e) read both sockets at scale 100 with +X reversed, positions right.
- fbx_unreal_sockets.py has the cause, from the UE 5.8 source.
- create_inventory_drone.export_lod0 has the fix.

**Scope.** Only LOD0's FBX is written. The body, the two sockets and the three UCX hulls are the reviewed blend's own
objects, unchanged.
- The blend, LOD1, LOD2 and the maps are not written. Their hashes are checked against the record before and after.
- Nothing is rebaked, and the blend is not saved.

**Checks, before the record changes:**
- The new file, through Interchange's rule (fbx_unreal_sockets.interchange):
  - its axes are Unreal's import axes, in centimetres;
  - each socket is at scale 1 within 1e-6, on the blend's axes within 1e-6, at the record's position within 1e-3 cm.
- Against the original, mesh by mesh (the body and the three hulls):
  - the vertices are 100 x the original's, within 1e-6 cm;
  - every other geometry array (indices, edges, normals, tangents, binormals, UVs, materials) is equal within 1e-6;
  - Interchange's baked vertices are the same within 1e-4 cm.

**The record** gets LOD0's new hash, the socket axes and the export convention ("lod0_fbx").
"""

import hashlib
import json
import os
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
import create_inventory_drone as D  # noqa: E402
import fbx_unreal_sockets as F  # noqa: E402

ROOT = D.ROOT
KIT = ROOT / "Content/SourceArt/Characters/Enemies/InventoryDrone"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ORIGINAL = Path(argv[argv.index("--original") + 1]).resolve()
RECORD = KIT / "build_record.json"
record = json.loads(RECORD.read_text(encoding="utf-8"))
asset = record["assets"][D.SPEC["asset"]]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
lod0_path = ROOT / asset["lods"][0]["file"]
assert sha(ORIGINAL) == asset["lods"][0]["sha256"], "the original is not the record's LOD0"
untouched = {e["file"]: e["sha256"] for e in asset["lods"][1:] + list(record["textures"].values()) + [record["blend"]]}
for f, h in untouched.items():
    assert sha(ROOT / f) == h, f"changed before the re-export: {f}"

bpy.ops.wm.open_mainfile(filepath=str(ROOT / record["blend"]["file"]), load_ui=False)
lod0 = bpy.data.objects[D.SPEC["asset"]]
empties = sorted((o for o in bpy.data.objects if o.name.startswith("SOCKET_")), key=lambda o: o.name)
hulls = [bpy.data.objects[f"UCX_{D.SPEC['asset']}_{i}"] for i in D.HIT_GROUPS]
assert lod0.matrix_world == D.Matrix.Identity(4), "LOD0 is not at the origin"
assert len(lod0.data.polygons) == asset["lods"][0]["triangles"], "LOD0's triangles changed"
assert {o.name[len("SOCKET_"):] for o in empties} == D.SOCKETS and all(o.parent == lod0 for o in empties)
for o in empties:
    want = asset["sockets"][o.name[len("SOCKET_"):]]
    assert (o.matrix_basis.translation - D.Vector(want)).length < 1e-5, (o.name, tuple(o.matrix_basis.translation))
for h in hulls:
    assert len(h.data.vertices) == record["hit_hulls"]["hulls"][h.name]["vertices"], h.name
axes = D.socket_axes(empties)

D.export_lod0(lod0_path, lod0, empties, hulls)
for f, h in untouched.items():
    assert sha(ROOT / f) == h, f"changed by the re-export: {f}"

# The new file, as Interchange will import it.
scene = F.read_fbx(lod0_path)
assert scene["axes"] == F.UNREAL_IMPORT_AXES and scene["unit"] == 1.0, scene["axes"]
result = F.interchange(scene)
assert np.allclose(result["conversion"], np.eye(3)), result["conversion"]
sockets = {}
for name, s in result["sockets"].items():
    rows = {"position_cm": s["position_cm"].round(5).tolist(), "scale": s["scale"].round(7).tolist(),
            "forward": s["x"].round(7).tolist(), "z": s["z"].round(7).tolist()}
    sockets[name] = rows
    assert np.abs(s["scale"] - 1.0).max() < 1e-6, (name, rows)
    assert np.abs(s["x"] - F.to_unreal_axis(axes[name]["x"])).max() < 1e-6, (name, rows)
    assert np.abs(s["z"] - F.to_unreal_axis(axes[name]["z"])).max() < 1e-6, (name, rows)
    assert np.abs(s["position_cm"] - F.to_unreal(asset["sockets"][name])).max() < 1e-3, (name, rows)
assert set(sockets) == D.SOCKETS, sorted(sockets)

# The same body and hulls as the original, array by array.
old, new = F.geometry_arrays(ORIGINAL), F.geometry_arrays(lod0_path)
assert set(old) == set(new) == {lod0.name, *(h.name for h in hulls)}, (sorted(old), sorted(new))
same = {}
for mesh in sorted(old):
    assert set(old[mesh]) == set(new[mesh]), (mesh, sorted(set(old[mesh]) ^ set(new[mesh])))
    worst = {}
    for key in sorted(old[mesh]):
        a, b = old[mesh][key], new[mesh][key]
        assert a.shape == b.shape, (mesh, key, a.shape, b.shape)
        if key == "Vertices":
            a = a * 100.0
        worst[key] = float(np.abs(a.astype(float) - b.astype(float)).max()) if a.size else 0.0
        assert worst[key] <= 1e-6, (mesh, key, worst[key])
    baked_old = F.interchange(F.read_fbx(ORIGINAL))["vertices"][mesh]
    worst["interchange_vertices_cm"] = float(np.abs(baked_old - result["vertices"][mesh]).max())
    assert worst["interchange_vertices_cm"] <= 1e-4, (mesh, worst["interchange_vertices_cm"])
    same[mesh] = {"arrays": len(old[mesh]), "worst": {k: float(f"{v:.3g}") for k, v in worst.items()}}

replaced = asset["lods"][0]["sha256"]
asset["lods"][0]["sha256"] = sha(lod0_path)
record["lod0_fbx"] = {**D.lod0_fbx_record(), "replaces_sha256": replaced,
                      "replaced_because": "root's 0eb8c5e import of fc0858a9 read both sockets at scale 100 with +X "
                                          "reversed (Saved/Qualification/2026-10-26/drone-0eb8c5e-import-attempt1)",
                      "rewritten_by": "scripts/art/reexport_inventory_drone_lod0.py, from the reviewed blend"}
record["socket_axes"] = axes
RECORD.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("INVENTORY_DRONE_LOD0_REEXPORTED " + json.dumps({"lod0_sha256": asset["lods"][0]["sha256"], "replaced": replaced,
                                                         "sockets_in_unreal": sockets, "same_geometry": same}))
passed = True
