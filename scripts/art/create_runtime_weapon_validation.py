"""Metric validation of the runtime weapon meshes (writes metric_report.json).

Run:  blender -b --factory-startup --python scripts/art/create_runtime_weapon_validation.py [-- --only 0,4]

For every weapon in create_runtime_weapon_specs.WEAPONS this script works
independently of the builders' own bookkeeping:

1. opens the saved source .blend and re-measures the named source parts
   (nagasa and sori from the blade's machi ring and mune line, tsuka and
   tsuba extents, yumi arc length, grip ratio and brace height, bore from the
   vertices at the muzzle socket, chain length from the link centres, head
   mass from the closed mesh volume) against the spec with its tolerance;
2. imports every exported FBX (LOD0-2 of each asset) into that session and
   checks the mesh name, one material slot, two UV layers (UV0 inside 0..1
   with no overlapping texels at 1024^2, UVMetric), decreasing triangle
   counts within the LOD0 budget, the SOCKET_ empties (Grip_R, Grip_L,
   Muzzle on the main mesh) and their positions, and FBX-to-source vertex
   bounds parity;
3. checks the four 2048^2 texture maps exist and match the recorded SHA-256;
4. measures the microsurface: the mean tangent tilt sqrt(x^2 + y^2) of the
   baked NormalDX over all texels (the review metric) and over the texels
   the UV0 islands cover, against MIN_NORMAL_TILT.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_runtime_weapon_specs as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "Content/SourceArt/Weapons/Runtime"
# Review floor for the baked microsurface (mean tangent tilt over all texels):
# below it grain, weave, file and casting relief read as flat.
MIN_NORMAL_TILT = 0.04


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def world_verts(obj):
    me = obj.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    m = np.array(obj.matrix_world)
    return co @ m[:3, :3].T + m[:3, 3]


def attr(obj, name, domain_len):
    a = obj.data.attributes.get(name)
    if a is None:
        return None
    vals = np.empty(domain_len)
    a.data.foreach_get("value", vals)
    return vals


def parts(names):
    out = []
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None:
            raise KeyError(f"source part {n} not found")
        out.append(o)
    return out


def prefix_parts(prefix):
    return sorted([o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(prefix)
                   and o.users_collection and o.users_collection[0].name == "RW_Source"], key=lambda o: o.name)


# ---------------------------------------------------------------------------
# measurement methods
# ---------------------------------------------------------------------------

def blade_points(obj):
    v = world_verts(obj)
    s = attr(obj, "hamon_s", len(v))
    return v, s


def m_blade_nagasa(check, ctx):
    v, s = blade_points(parts([check["args"]["part"]])[0])
    base = s <= 1e-7
    xs = v[base, 0]
    machi_ring = base & (v[:, 0] >= xs.max() - 1e-5)
    munemachi = v[machi_ring][np.argmax(v[machi_ring][:, 2])]
    tip = v[np.argmax(s)]
    return float(np.linalg.norm(tip - munemachi))


def m_blade_sori(check, ctx):
    v, s = blade_points(parts([check["args"]["part"]])[0])
    base = s <= 1e-7
    xs = v[base, 0]
    machi_ring = base & (v[:, 0] >= xs.max() - 1e-5)
    a = v[machi_ring][np.argmax(v[machi_ring][:, 2])]
    tip = v[np.argmax(s)]
    chord = tip - a
    chord_n = chord / np.linalg.norm(chord)
    up = np.array([-chord_n[2], 0.0, chord_n[0]])
    best = 0.0
    for sv in np.unique(np.round(s, 6)):
        ring = v[np.abs(s - sv) < 1e-7]
        if len(ring) < 3:
            continue
        peak = ring[np.argmax(ring @ up)]
        rel = peak - a
        d = rel - chord_n * rel.dot(chord_n)
        best = max(best, float(np.linalg.norm(d)) * (1 if d.dot(up) < 0 else 1))
    return best


def _extent(check, axis):
    args = check["args"]
    if "asset" in args:
        obj = ctx_state["imported"][args["asset"]][0]
        v = world_verts(obj)
    else:
        v = world_verts(parts([args["part"]])[0])
    return float(v[:, axis].max() - v[:, axis].min())


def m_extent_x(check, ctx):
    return _extent(check, 0)


def m_extent_y(check, ctx):
    return _extent(check, 1)


def m_extent_z(check, ctx):
    return _extent(check, 2)


def m_span_x(check, ctx):
    vs = np.concatenate([world_verts(o) for o in parts(check["args"]["parts"])])
    return float(vs[:, 0].max() - vs[:, 0].min())


def m_extent_y_at_base(check, ctx):
    v, s = blade_points(parts([check["args"]["part"]])[0])
    base = s <= 1e-7
    xs = v[base, 0]
    ring = v[base & (v[:, 0] >= xs.max() - 1e-5)]
    return float(ring[:, 1].max() - ring[:, 1].min())


def m_max_across_flats(check, ctx):
    v = world_verts(parts([check["args"]["part"]])[0])
    return float(2.0 * np.abs(v[:, 1]).max())


def m_chain_length(check, ctx):
    links = prefix_parts(check["args"]["prefix"])
    cs = [world_verts(o).mean(axis=0) for o in links]
    total = sum(float(np.linalg.norm(b - a)) for a, b in zip(cs[:-1], cs[1:]))
    pitch = S.WEAPONS[ctx["id"]]["link_pitch"]
    return total + pitch


def m_mass(check, ctx):
    obj = parts([check["args"]["part"]])[0]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    vol = abs(bm.calc_volume(signed=True))
    bm.free()
    return vol * check["args"]["density"]


def _stave_polyline(obj, ring=28):
    """Centreline of the lofted stave: the centroid of each cross-section
    ring (the loft stores its vertices ring by ring)."""
    v = world_verts(obj)
    n = (len(v) // ring) * ring
    cents = v[:n].reshape(-1, ring, 3).mean(axis=1)
    order = np.argsort(cents[:, 2])
    cents = cents[order]
    seg = np.linalg.norm(np.diff(cents, axis=0), axis=1)
    return cents, np.concatenate([[0.0], np.cumsum(seg)]), v


def m_yumi_length(check, ctx):
    cents, cum, v = _stave_polyline(parts([check["args"]["part"]])[0])
    # add the half-bin end caps (tips lie beyond the first/last centroids)
    return float(cum[-1] + (cents[0][2] - v[:, 2].min()) + (v[:, 2].max() - cents[-1][2]))


def m_yumi_grip_ratio(check, ctx):
    stave = parts([check["args"]["part"]])[0]
    cents, cum, v = _stave_polyline(stave)
    grip = world_verts(parts([check["args"]["grip"]])[0])
    gz = 0.5 * (grip[:, 2].min() + grip[:, 2].max())
    i = int(np.searchsorted(cents[:, 2], gz))
    i = max(1, min(i, len(cents) - 1))
    t = (gz - cents[i - 1][2]) / max(cents[i][2] - cents[i - 1][2], 1e-9)
    s_grip = cum[i - 1] + t * (cum[i] - cum[i - 1]) + (cents[0][2] - v[:, 2].min())
    total = m_yumi_length(check, ctx)
    return float(s_grip / total)


def m_yumi_brace(check, ctx):
    v = world_verts(parts([check["args"]["part"]])[0])
    near = v[np.abs(v[:, 2]) < 0.01]
    belly = near[:, 0].min()
    sv = world_verts(parts([check["args"]["string"]])[0])
    sn = sv[np.abs(sv[:, 2]) < 0.01]
    return float(belly - sn[:, 0].mean())


def m_bore_diameter(check, ctx):
    obj = parts([check["args"]["part"]])[0]
    v = world_verts(obj)
    mz = ctx["sockets"]["Muzzle"]
    near = v[np.abs(v[:, 0] - v[:, 0].max()) < 0.0025]
    r = np.sqrt((near[:, 1] - mz[1]) ** 2 + (near[:, 2] - mz[2]) ** 2)
    return float(2.0 * r.min())


METHODS = {k[2:]: v for k, v in globals().items() if k.startswith("m_")}
ctx_state = {"imported": {}}


# ---------------------------------------------------------------------------
# FBX checks
# ---------------------------------------------------------------------------

def uv_overlap(mesh, layer="UV0", res=1024):
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers[layer].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2) * res
    count = np.zeros((res, res), dtype=np.uint8)
    for poly in mesh.polygons:
        idx = list(poly.loop_indices)
        for k in range(1, len(idx) - 1):
            tri = uv[[idx[0], idx[k], idx[k + 1]]]
            x0, y0 = np.floor(tri.min(axis=0)).astype(int)
            x1, y1 = np.ceil(tri.max(axis=0)).astype(int)
            x0, y0 = max(x0, 0), max(y0, 0)
            x1, y1 = min(x1, res - 1), min(y1, res - 1)
            if x1 < x0 or y1 < y0:
                continue
            xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax, ay), (bx, by), (cx, cy) = tri
            det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(det) < 1e-12:
                continue
            l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / det
            l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / det
            l3 = 1 - l1 - l2
            inside = (l1 > 1e-6) & (l2 > 1e-6) & (l3 > 1e-6)
            sub = count[y0:y1 + 1, x0:x1 + 1]
            sub[inside] = np.minimum(sub[inside].astype(np.int32) + 1, 255).astype(np.uint8)
    covered = int((count >= 1).sum())
    over = int((count >= 2).sum())
    return over / max(covered, 1), covered / (res * res), count >= 1


def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path), use_custom_normals=True, ignore_leaf_bones=True)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        o.hide_render = True
    return new


def validate(wid):
    spec = S.WEAPONS[wid]
    wdir = RUNTIME / spec["key"]
    rec_path = wdir / "build_record.json"
    res = {"id": wid, "key": spec["key"], "checks": [], "errors": []}
    if not rec_path.is_file():
        res["errors"].append("missing build_record.json")
        return res
    rec = json.loads(rec_path.read_text())
    blend = ROOT / rec["blend"]["file"]
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    ctx = {"id": wid, "sockets": {}}
    ctx_state["imported"] = {}
    # Source export objects: map name -> object (for parity).
    src = {o.name: o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SM_Weapon_")}
    coverage = None
    for asset, arec in rec["assets"].items():
        lods = []
        for li, lod in enumerate(arec["lods"]):
            path = ROOT / lod["file"]
            if sha256(path) != lod["sha256"]:
                res["errors"].append(f"{path.name}: sha256 differs from build_record")
            new = import_fbx(path)
            meshes = [o for o in new if o.type == "MESH"]
            empties = [o for o in new if o.type == "EMPTY"]
            if len(meshes) != 1:
                res["errors"].append(f"{path.name}: expected one mesh, got {len(meshes)}")
                continue
            m = meshes[0]
            want = asset if li == 0 else f"{asset}_LOD{li}"
            if not m.name.startswith(want):
                res["errors"].append(f"{path.name}: mesh named {m.name}, expected {want}")
            tris = sum(len(p.vertices) - 2 for p in m.data.polygons)
            if tris != lod["triangles"]:
                res["errors"].append(f"{path.name}: {tris} triangles, record says {lod['triangles']}")
            if len(m.data.materials) != 1:
                res["errors"].append(f"{path.name}: {len(m.data.materials)} material slots (expected 1)")
            uvn = [l.name for l in m.data.uv_layers]
            if len(uvn) != 2:
                res["errors"].append(f"{path.name}: UV layers {uvn} (expected UV0 + UVMetric)")
            uv = np.empty(len(m.data.loops) * 2)
            m.data.uv_layers[0].data.foreach_get("uv", uv)
            if uv.min() < -1e-4 or uv.max() > 1 + 1e-4:
                res["errors"].append(f"{path.name}: UV0 outside 0..1")
            lods.append((m, tris, empties))
            if li == 0:
                over, cov, mask = uv_overlap(m.data)
                coverage = mask if coverage is None else (coverage | mask)
                res["checks"].append({"name": f"{asset}_uv0_overlap", "measured": round(over, 5), "expected": 0.0,
                                      "tol": 0.004, "pass": over <= 0.004, "coverage": round(cov, 4)})
                # Parity with the source export object.
                if asset in src:
                    a = world_verts(src[asset])
                    bb = world_verts(m)
                    d = float(max(np.abs(a.min(0) - bb.min(0)).max(), np.abs(a.max(0) - bb.max(0)).max()))
                    res["checks"].append({"name": f"{asset}_fbx_bounds_parity_m", "measured": d, "expected": 0.0,
                                          "tol": 1e-4, "pass": d <= 1e-4})
        if not lods:
            continue
        ctx_state["imported"][asset] = lods[0]
        t = [x[1] for x in lods]
        budget = spec["lod0_tri_budget"] if asset == spec["asset"] else spec["lod0_tri_budget"]
        ok = t[0] <= budget and all(b_ < a_ for a_, b_ in zip(t[:-1], t[1:])) and len(t) == 3
        res["checks"].append({"name": f"{asset}_lod_triangles", "measured": t, "budget_lod0": budget, "pass": ok})
        # Sockets on LOD0.
        socks = {e.name.split(".")[0][len("SOCKET_"):]: e for e in lods[0][2] if e.name.startswith("SOCKET_")}
        for e in socks.values():
            if e.parent is not lods[0][0]:
                res["errors"].append(f"{asset}: socket {e.name} is not parented to the mesh")
        if asset == spec["asset"]:
            missing = [s for s in S.SOCKETS if s not in socks]
            if missing:
                res["errors"].append(f"{asset}: missing sockets {missing}")
        for name, pos in arec["sockets"].items():
            if name not in socks:
                res["errors"].append(f"{asset}: recorded socket {name} not in FBX")
                continue
            p = socks[name].matrix_world.translation
            d = (p - Vector(pos)).length
            if d > 2e-4:
                res["errors"].append(f"{asset}: socket {name} at {tuple(round(c, 5) for c in p)} differs by {d:.6f} m")
            if asset == spec["asset"]:
                ctx["sockets"][name] = tuple(p)
    # Textures.
    for key, trec in rec.get("textures", {}).items():
        path = ROOT / trec["file"]
        if not path.is_file() or sha256(path) != trec["sha256"]:
            res["errors"].append(f"texture {key}: missing or hash mismatch")
            continue
        img = bpy.data.images.load(str(path), check_existing=False)
        if tuple(img.size) != (rec["texture_res"], rec["texture_res"]):
            res["errors"].append(f"texture {key}: size {tuple(img.size)}")
        bpy.data.images.remove(img)
    if "textures" not in rec:
        res["errors"].append("no baked textures recorded")
    ntex = rec.get("textures", {}).get("Normal")
    if ntex and (ROOT / ntex["file"]).is_file():
        img = bpy.data.images.load(str(ROOT / ntex["file"]), check_existing=False)
        img.colorspace_settings.name = "Non-Color"
        w_, h_ = img.size
        px = np.empty(w_ * h_ * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        bpy.data.images.remove(img)
        n = px.reshape(h_, w_, 4)[..., :2] * 2.0 - 1.0
        tilt = np.sqrt((n ** 2).sum(axis=2))
        t_all = float(tilt.mean())
        chk = {"name": "normal_tilt_mean", "measured": round(t_all, 4), "expected_min": MIN_NORMAL_TILT,
               "pass": t_all >= MIN_NORMAL_TILT}
        if coverage is not None:
            step = max(1, h_ // coverage.shape[0])
            sub = tilt[::step, ::step][:coverage.shape[0], :coverage.shape[1]]
            chk["covered_texels_mean"] = round(float(sub[coverage].mean()), 4)
        res["checks"].append(chk)
    dens = rec.get("texel_density_px_per_m", {})
    if dens:
        res["checks"].append({"name": "texel_density_p05_px_per_m", "measured": round(dens["p05"], 1),
                              "expected_min": S.MIN_TEXEL_DENSITY, "pass": dens["p05"] >= S.MIN_TEXEL_DENSITY})
    # Metric checks from the spec.
    for chk in spec["checks"]:
        try:
            val = METHODS[chk["method"]](chk, ctx)
            ok = abs(val - chk["expected"]) <= chk["tol"]
            res["checks"].append({"name": chk["name"], "method": chk["method"], "measured": round(val, 5),
                                  "expected": chk["expected"], "tol": chk["tol"], "basis": chk["basis"],
                                  "source": chk["source"], "pass": ok})
        except Exception as exc:  # report, do not hide
            res["checks"].append({"name": chk["name"], "method": chk["method"], "pass": False, "error": repr(exc)})
    res["pass"] = not res["errors"] and all(c.get("pass") for c in res["checks"])
    return res


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = None
    if "--only" in argv:
        only = [int(x) for x in argv[argv.index("--only") + 1].split(",")]
    ids = only or [w for w in sorted(S.WEAPONS) if S.WEAPONS[w].get("status") != "blockout"]
    report_path = RUNTIME / "metric_report.json"
    report = json.loads(report_path.read_text()) if report_path.is_file() and only else {"weapons": {}}
    t0 = time.time()
    for wid in ids:
        r = validate(wid)
        report["weapons"][str(wid)] = r
        status = "PASS" if r.get("pass") else "FAIL"
        print(f"[validate] {S.WEAPONS[wid]['key']}: {status}", flush=True)
        for c in r["checks"]:
            if not c.get("pass"):
                print(f"    check {c['name']}: {c.get('measured', c.get('error'))} vs {c.get('expected')}", flush=True)
        for e in r["errors"]:
            print(f"    error {e}", flush=True)
    allw = report["weapons"]
    report["summary"] = {"weapons": len(allw), "passed": sum(1 for r in allw.values() if r.get("pass")),
                         "validator": "scripts/art/create_runtime_weapon_validation.py",
                         "blender": bpy.app.version_string, "seconds": round(time.time() - t0, 1)}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"[validate] {report['summary']['passed']}/{report['summary']['weapons']} weapons pass", flush=True)
    if report["summary"]["passed"] != report["summary"]["weapons"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
