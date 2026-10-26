"""Independently round-trip the Inventory drone kit's FBXs (create_inventory_drone.py).

Run: blender -b --factory-startup --python-exit-code 1 --python scripts/art/validate_inventory_drone.py

From the exported files themselves, in a clean Blender session:
- every file's hash matches build_record.json;
- LOD0 holds one visual mesh, the three UCX hit hulls and the Eye and NetMuzzle sockets. Each socket is within 0.1
  mm of the record, and its X and Z axes within 0.05 deg of the record's socket_axes, signed;
- every vertex of every LOD lies within 0.365 m of the centre, so inside the 0.38 m movement sphere;
- each UCX hull is convex, and every LOD0 vertex lies inside their union. Convex means two things:
  - no vertex lies more than 0.05 mm outside any face plane bigger than 1 mm2. Smaller faces tilt with float32
    noise, and their worst violation is reported, not trusted;
  - the hull's volume is within 0.1 % of the volume of its own convex hull, so a real concavity would show;
- triangle counts fall with each LOD.

**As Unreal will import them.** Blender's import is not Unreal's. fc0858a9 passed here while UE 5.8 read both
sockets at scale 100 with +X reversed. So the FBX bytes are also read through fbx_unreal_sockets.py, UE 5.8
Interchange's rule, calibrated on root's import of fc0858a9:
- LOD0 declares Unreal's import axes in centimetres, and none of its nodes carries a scale, or a rotation other than
  a socket's own;
- each socket:
  - is at scale 1 within 1e-6;
  - is on the record's axes within 1e-5;
  - is within 1e-3 cm of the record's position;
  - meets root's gate: Eye forward +X, NetMuzzle forward (0.7071, 0, -0.7071);
- every LOD's vertices lie within 36.5 cm of the centre, at the record's bounds within 0.02 cm;
- each hull keeps its record's vertex count and bounds within 0.02 cm.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fbx_unreal_sockets as F  # noqa: E402

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
assert set(asset["sockets"]) == set(record["socket_axes"]) == {"Eye", "NetMuzzle"}
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
            mx = sockets[name].matrix_world.to_3x3().normalized()
            for col, key in ((0, "x"), (2, "z")):
                axis, ref = np.array(mx.col[col]), np.array(record["socket_axes"][name][key])
                off = math.degrees(math.acos(max(-1.0, min(1.0, float(axis @ ref / np.linalg.norm(ref))))))
                assert off < 0.05, (name, key, axis.round(6).tolist(), ref.tolist(), off)
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


# As Unreal will import them: Interchange's rule, from the FBX bytes.
ROOT_FORWARD = {"Eye": (1.0, 0.0, 0.0), "NetMuzzle": (math.sqrt(0.5), 0.0, -math.sqrt(0.5))}   # root's 0eb8c5e gate


def unreal_bounds(row):
    """A record's Blender bounds (metres) as Unreal's (centimetres): y is negated, so its ends swap."""
    lo, hi = F.to_unreal(row["bounds_min_m"]), F.to_unreal(row["bounds_max_m"])
    return np.minimum(lo, hi), np.maximum(lo, hi)


unreal_rows = {}
for lod, entry in enumerate(asset["lods"]):
    scene = F.read_fbx(ROOT / entry["file"])
    result = F.interchange(scene)
    visual = [n for n in result["vertices"] if not n.startswith("UCX_")]
    assert len(visual) == 1, visual
    pts = result["vertices"][visual[0]]
    want_lo, want_hi = unreal_bounds(record["envelope"]["lods"][lod])
    radius = float(np.linalg.norm(pts, axis=1).max())
    assert radius <= 100.0 * ENVELOPE, (lod, radius)
    assert np.abs(pts.min(0) - want_lo).max() < 0.02 and np.abs(pts.max(0) - want_hi).max() < 0.02, \
        (lod, pts.min(0).tolist(), pts.max(0).tolist(), want_lo.tolist(), want_hi.tolist())
    row = {"axes": {k: list(v) for k, v in scene["axes"].items()}, "radius_cm": round(radius, 4)}
    if lod == 0:
        assert scene["axes"] == F.UNREAL_IMPORT_AXES and scene["unit"] == 1.0, (scene["axes"], scene["unit"])
        for name, node in scene["nodes"].items():
            assert name.startswith("SOCKET_") or np.abs(np.array(node["R"])).max() < 1e-6, (name, node["R"])
            assert np.abs(np.array(node["S"]) - 1.0).max() < 1e-6, (name, node["S"])
        assert set(result["sockets"]) == {"Eye", "NetMuzzle"}, sorted(result["sockets"])
        for name, s in result["sockets"].items():
            ax = record["socket_axes"][name]
            assert np.abs(s["scale"] - 1.0).max() < 1e-6, (name, s["scale"].tolist())
            assert np.abs(s["x"] - F.to_unreal_axis(ax["x"])).max() < 1e-5, (name, s["x"].tolist())
            assert np.abs(s["z"] - F.to_unreal_axis(ax["z"])).max() < 1e-5, (name, s["z"].tolist())
            assert np.abs(s["x"] - ROOT_FORWARD[name]).max() < 1e-5, (name, s["x"].tolist())
            assert np.abs(s["position_cm"] - F.to_unreal(asset["sockets"][name])).max() < 1e-3, \
                (name, s["position_cm"].tolist())
            assert s["det"] > 0.0, (name, s["det"])
        row["sockets"] = {n: {"position_cm": s["position_cm"].round(4).tolist(), "scale": s["scale"].round(7).tolist(),
                              "forward": s["x"].round(7).tolist()} for n, s in result["sockets"].items()}
        for name, h in record["hit_hulls"]["hulls"].items():
            hv = result["vertices"][name]
            h_lo, h_hi = unreal_bounds(h)
            assert len(hv) == h["vertices"], (name, len(hv))
            assert np.abs(hv.min(0) - h_lo).max() < 0.02 and np.abs(hv.max(0) - h_hi).max() < 0.02, \
                (name, hv.min(0).tolist(), hv.max(0).tolist(), h_lo.tolist(), h_hi.tolist())
        row["hulls"] = sorted(record["hit_hulls"]["hulls"])
    unreal_rows[lod] = row
print("INVENTORY_DRONE_UNREAL", json.dumps(unreal_rows))
print("INVENTORY_DRONE_PASS", json.dumps({"lod_triangles": tri_counts, "max_from_centre_m": round(worst, 5),
                                          "hulls": 3, "sockets": sorted(asset["sockets"])}))
passed = True
