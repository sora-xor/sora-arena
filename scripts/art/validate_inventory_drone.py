"""Independently round-trip the Inventory drone kit's FBXs (create_inventory_drone.py).

Run: blender -b --factory-startup --python-exit-code 1 --python scripts/art/validate_inventory_drone.py

From the exported files themselves, in a clean Blender session:
- every file's hash matches build_record.json;
- LOD0 holds one visual mesh, the three UCX hit hulls and the Eye and NetMuzzle sockets, each socket within 0.1 mm
  and 0.5 deg of the record;
- every vertex of every LOD lies within 0.365 m of the centre, so inside the 0.38 m movement sphere;
- each UCX hull is convex, and every LOD0 vertex lies inside their union. Convex means two things:
  - no vertex lies more than 0.05 mm outside any face plane bigger than 1 mm2. Smaller faces tilt with float32
    noise, and their worst violation is reported, not trusted;
  - the hull's volume is within 0.1 % of the volume of its own convex hull, so a real concavity would show;
- triangle counts fall with each LOD.
"""

import atexit
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

passed = False


def fail_on_exit():
    if not passed:
        sys.stdout.flush()
        os._exit(1)


atexit.register(fail_on_exit)
ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "Content/SourceArt/Characters/Enemies/InventoryDrone"
record = json.loads((KIT / "build_record.json").read_text(encoding="utf-8"))
asset = record["assets"]["SM_Drone_Inventory"]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
for entry in asset["lods"]:
    assert sha(ROOT / entry["file"]) == entry["sha256"], entry["file"]
for key, entry in record.get("textures", {}).items():
    assert sha(ROOT / entry["file"]) == entry["sha256"], entry["file"]
assert sha(ROOT / record["blend"]["file"]) == record["blend"]["sha256"]
assert set(asset["sockets"]) == {"Eye", "NetMuzzle"}
ENVELOPE = 0.365
tri_counts, worst = [], 0.0
for lod, entry in enumerate(asset["lods"]):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(ROOT / entry["file"]))
    new = [o for o in bpy.data.objects if o not in before]
    visual = [o for o in new if o.type == "MESH" and not o.name.startswith("UCX_")]
    assert len(visual) == 1, [o.name for o in visual]
    mesh = visual[0]
    pts = np.array([list(mesh.matrix_world @ v.co) for v in mesh.data.vertices])
    far = float(np.linalg.norm(pts, axis=1).max())
    worst = max(worst, far)
    assert far <= ENVELOPE + 1e-4, (lod, far)
    tri_counts.append(sum(len(p.vertices) - 2 for p in mesh.data.polygons))
    if lod == 0:
        sockets = {o.name.split(".")[0][len("SOCKET_"):]: o for o in new if o.name.startswith("SOCKET_")}
        assert set(sockets) == {"Eye", "NetMuzzle"}, sorted(sockets)
        for name, want in asset["sockets"].items():
            got = sockets[name].matrix_world.translation
            assert (got - __import__("mathutils").Vector(want)).length < 1e-4, (name, tuple(got), want)
        mx = sockets["NetMuzzle"].matrix_world.to_3x3().normalized()
        x_axis = np.array(mx.col[0])
        assert math.degrees(math.acos(min(1.0, abs(float(x_axis @ np.array([math.sqrt(0.5), 0.0, -math.sqrt(0.5)])))))) < 0.5
        hulls = [o for o in new if o.type == "MESH" and o.name.startswith("UCX_SM_Drone_Inventory_")]
        assert sorted(o.name.split(".")[0] for o in hulls) == [f"UCX_SM_Drone_Inventory_{i:02d}" for i in range(3)]
        inside_any = np.zeros(len(pts), bool)
        hull_rows = {}
        for h in hulls:
            hv = np.array([list(h.matrix_world @ v.co) for v in h.data.vertices])
            c = hv.mean(0)
            n, d, area = [], [], []
            for poly in h.data.polygons:
                q = hv[list(poly.vertices)]
                cr = np.cross(q[1] - q[0], q[2] - q[0])
                a = float(np.linalg.norm(cr)) / 2.0
                nn = cr / max(2.0 * a, 1e-30)
                if nn @ (q[0] - c) < 0:
                    nn = -nn
                n.append(nn)
                d.append(nn @ q[0])
                area.append(a)
            n, d, area = np.array(n), np.array(d), np.array(area)
            viol = (hv @ n.T - d).max(0)
            big = area >= 1e-6
            vol = sum(abs(np.dot(hv[p.vertices[0]] - c, np.cross(hv[p.vertices[1]] - c, hv[p.vertices[2]] - c))) / 6.0
                      for p in h.data.polygons)
            bm = bmesh.new()
            for q in hv:
                bm.verts.new(q)
            bmesh.ops.convex_hull(bm, input=list(bm.verts), use_existing_faces=False)
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if not f.is_valid] , context="FACES")
            rehull = bm.calc_volume(signed=False)
            bm.free()
            hull_rows[h.name.split(".")[0]] = {"worst_big_face_m": round(float(viol[big].max()), 7),
                                               "worst_small_face_m": round(float(viol[~big].max()), 7) if (~big).any() else 0.0,
                                               "small_faces": int((~big).sum()), "volume_m3": round(vol, 6),
                                               "own_convex_hull_m3": round(rehull, 6)}
            assert viol[big].max() <= 5e-5, (h.name, hull_rows[h.name.split(".")[0]])
            assert abs(vol - rehull) <= 1e-3 * rehull, (h.name, hull_rows[h.name.split(".")[0]])
            inside_any |= (pts @ n[big].T - d[big]).max(1) <= 2e-5
        print("INVENTORY_DRONE_HULLS", json.dumps(hull_rows))
        assert inside_any.all(), f"{int((~inside_any).sum())} LOD0 vertices outside every hit hull"
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
assert all(a > b for a, b in zip(tri_counts, tri_counts[1:])), tri_counts
print("INVENTORY_DRONE_PASS", json.dumps({"lod_triangles": tri_counts, "max_from_centre_m": round(worst, 5),
                                          "hulls": 3, "sockets": sorted(asset["sockets"])}))
passed = True
