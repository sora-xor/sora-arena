"""Check a b09 candidate build's FBX files against b09_workshop_craft on the host, before Unreal imports them.

For each of b09_workshop_craft.candidates(), the build's manifest.json must list it, and its file must:
- be the manifest's (SHA-256);
- declare UE 5.8's FBX import axes in centimetres (fbx_socket_export's convention), so no importer converts it;
- as Interchange imports it (fbx_unreal_sockets.interchange):
  - have the module's vertices, in order, within TOL_CM;
  - have the module's sockets, each at its point within TOL_CM, on its axes within TOL_AXIS, at scale 1;
- hold the module's triangles, in order, with each winding reversed, as Blender holds them (the Y flip mirrors);
- carry two UV layers, UV0 and Reveal, equal at every triangle corner to box_uv and reveal_uv within TOL_UV;
- give every triangle its slot's material;
- face outward: each closed part (its vertices welded by position, every edge shared by two triangles running
  opposite ways) has positive signed volume in the file's own right-handed frame. Open parts (paper, strips) are
  counted, not judged.

Prints B09_FBX_CHECK <json>; exits 1 on any problem.

Run (host): /usr/bin/python3 scripts/art/check_b09_candidates_fbx.py Saved/B09Workshop/Candidates/<run> [record.json]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import b09_workshop_craft as B  # noqa: E402
import fbx_unreal_sockets as F  # noqa: E402

TOL_CM = 1e-3
TOL_AXIS = 1e-6
TOL_UV = 1e-6


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unit(v, default):
    v = np.asarray(default if v is None else v, float)
    return v / np.linalg.norm(v)


def layers(path):
    """Each mesh Model's material names (in their connection order, which the per-polygon indices count) and its UV
    layers [(name, per-corner uv)], by the Model's name."""
    root, _version = F.parser().parse(str(path))
    objects = {o.props[0]: o for o in F._child(root, b"Objects").elems}
    name = lambda o: o.props[1].split(b"\x00\x01")[0].decode()  # noqa: E731
    mats, geo_of = {}, {}
    for c in F._child(root, b"Connections").elems:
        if c.props[0] != b"OO":
            continue
        src, dst = objects.get(c.props[1]), objects.get(c.props[2])
        if src is None or dst is None or dst.id != b"Model":
            continue
        if src.id == b"Material":
            mats.setdefault(name(dst), []).append(name(src))
        elif src.id == b"Geometry":
            geo_of[name(dst)] = src
    out = {}
    for model, geo in geo_of.items():
        uvs, per_poly = [], None
        for e in geo.elems:
            if e.id == b"LayerElementUV":
                sub = {s.id: s for s in e.elems}
                uv = np.array(sub[b"UV"].props[0], float).reshape(-1, 2)
                idx = np.array(sub[b"UVIndex"].props[0], int) if b"UVIndex" in sub else np.arange(len(uv))
                uvs.append((sub[b"Name"].props[0].decode() if b"Name" in sub else "", uv[idx],
                            sub[b"MappingInformationType"].props[0].decode()))
            elif e.id == b"LayerElementMaterial":
                sub = {s.id: s for s in e.elems}
                per_poly = (np.array(sub[b"Materials"].props[0], int), sub[b"MappingInformationType"].props[0].decode())
        out[model] = {"materials": mats.get(model, []), "uvs": uvs, "per_polygon": per_poly}
    return out


def closed_parts(verts, tris):
    """The mesh's connected parts after welding vertices by position: [(closed, signed volume)] in its frame."""
    key = np.round(verts / 1e-4).astype(np.int64)
    _, weld = np.unique(key, axis=0, return_inverse=True)
    t = weld.reshape(-1)[tris]
    parent = np.arange(t.max() + 1)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for a, b, c in t:
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra
        parent[find(rc)] = ra
    comp = np.array([find(a) for a in t[:, 0]])
    out = []
    for c in np.unique(comp):
        tt = t[comp == c]
        directed = np.concatenate([tt[:, [0, 1]], tt[:, [1, 2]], tt[:, [2, 0]]])
        fwd = {tuple(e) for e in directed.tolist()}
        closed = len(fwd) == len(directed) and all((b, a) in fwd for a, b in fwd)
        w = verts[tris[comp == c]]
        vol = float(np.einsum("ij,ij->i", w[:, 0], np.cross(w[:, 1], w[:, 2])).sum() / 6.0)
        out.append((closed, vol))
    return out


def check_asset(name, mesh, socks, lantern_frame, path, entry):
    problems, row = [], {"fbx": path.name}
    if sha256(path) != entry["sha256"]:
        problems.append("not the manifest's file")
    scene = F.read_fbx(path)
    if scene["axes"] != F.UNREAL_IMPORT_AXES or abs(scene["unit"] - 1.0) > 1e-12:
        problems.append(f"axes {scene['axes']} unit {scene['unit']}: not UE 5.8's import axes in centimetres")
        return problems, row
    ue = F.interchange(scene)
    meshes = [n for n, node in scene["nodes"].items() if node["vertices"] is not None]
    if meshes != [name]:
        problems.append(f"mesh nodes {meshes}")
        return problems, row
    v = ue["vertices"][name]
    if v.shape != mesh.verts.shape:
        problems.append(f"{len(v)} vertices, the module has {len(mesh.verts)}")
        return problems, row
    row["vertex_err_cm"] = float(np.abs(v - mesh.verts).max())
    if row["vertex_err_cm"] > TOL_CM:
        problems.append(f"vertices differ by {row['vertex_err_cm']:.6f} cm")
    arrays = F.geometry_arrays(path)[name]
    idx = arrays["PolygonVertexIndex"].astype(int)
    ends = idx < 0
    if not (len(idx) % 3 == 0 and ends[2::3].all() and not ends[0::3].any() and not ends[1::3].any()):
        problems.append("the polygons are not all triangles")
        return problems, row
    tris = np.where(ends, ~idx, idx).reshape(-1, 3)
    row["winding"] = "the module's, reversed (Blender's)" if np.array_equal(tris, mesh.tris[:, [0, 2, 1]]) else \
        "the module's, NOT reversed" if np.array_equal(tris, mesh.tris) else "other"
    if row["winding"] != "the module's, reversed (Blender's)":
        problems.append(f"triangles: {row['winding']}")
        return problems, row
    parts = closed_parts(scene["nodes"][name]["vertices"], tris)
    row["parts"] = {"closed": sum(1 for c, _ in parts if c), "open": sum(1 for c, _ in parts if not c),
                    "closed_inward": sum(1 for c, vol in parts if c and vol <= 0.0)}
    if row["parts"]["closed_inward"]:
        problems.append(f"{row['parts']['closed_inward']} closed parts face inward")
    lay = layers(path)[name]
    names = [u[0] for u in lay["uvs"]]
    row["uv_layers"] = names
    if names != ["UV0", "Reveal"] or any(u[2] != "ByPolygonVertex" for u in lay["uvs"]):
        problems.append(f"uv layers {[(u[0], u[2]) for u in lay['uvs']]}")
    else:
        want0 = B.box_uv(mesh)[:, [0, 2, 1]].reshape(-1, 2)
        want1 = B.reveal_uv(mesh, lantern_frame)[tris.ravel()]
        row["uv_err"] = [float(np.abs(lay["uvs"][0][1] - want0).max()), float(np.abs(lay["uvs"][1][1] - want1).max())]
        if max(row["uv_err"]) > TOL_UV:
            problems.append(f"uvs differ by {row['uv_err']}")
    per_poly, mapping = lay["per_polygon"] if lay["per_polygon"] is not None else (None, None)
    slots = mesh.slots().tolist()
    row["materials"] = lay["materials"]
    if per_poly is None:
        problems.append("no material layer")
    elif mapping == "AllSame":
        if len(set(slots)) != 1 or lay["materials"][int(per_poly[0])] != slots[0]:
            problems.append(f"one material {lay['materials']} for slots {sorted(set(slots))}")
    elif mapping != "ByPolygon" or len(per_poly) != len(slots) or \
            [lay["materials"][k] for k in per_poly.tolist()] != slots:
        problems.append(f"per-triangle materials are not the slots ({mapping}, {len(per_poly)} entries)")
    got_socks = ue["sockets"]
    if sorted(got_socks) != sorted(socks):
        problems.append(f"sockets {sorted(got_socks)}, the module has {sorted(socks)}")
    errs = {"position_cm": 0.0, "axis": 0.0, "scale": 0.0}
    for s, (p, xa, za) in socks.items():
        g = got_socks.get(s)
        if g is None:
            continue
        errs["position_cm"] = max(errs["position_cm"], float(np.abs(g["position_cm"] - p).max()))
        errs["axis"] = max(errs["axis"], float(np.abs(g["x"] - unit(xa, (1.0, 0.0, 0.0))).max()),
                           float(np.abs(g["z"] - unit(za, (0.0, 0.0, 1.0))).max()))
        errs["scale"] = max(errs["scale"], float(np.abs(g["scale"] - 1.0).max()), abs(g["det"] - 1.0))
        if s not in entry["sockets"] or float(np.abs(np.array(entry["sockets"][s]) - p).max()) > TOL_CM:
            problems.append(f"socket {s}: the manifest has {entry['sockets'].get(s)}")
    row["socket_err"] = errs
    if errs["position_cm"] > TOL_CM or errs["axis"] > TOL_AXIS or errs["scale"] > 1e-9:
        problems.append(f"socket errors {errs}")
    lo, hi = v.min(0), v.max(0)
    row["bounds_err_cm"] = float(max(np.abs(lo - entry["bounds_cm"][0]).max(), np.abs(hi - entry["bounds_cm"][1]).max()))
    if row["bounds_err_cm"] > 2e-3 or entry["triangles"] != len(tris) or entry["slots"] != list(dict.fromkeys(slots)):
        problems.append(f"the manifest's bounds, triangles or slots ({row['bounds_err_cm']:.6f} cm, {entry['triangles']})")
    return problems, row


def main():
    build = (ROOT / sys.argv[1]).resolve()
    record_path = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    man = json.loads((build / "manifest.json").read_text())
    problems, rows = [], {}
    if man["module_sha256"] != sha256(B.__file__):
        problems.append("the build was made from another b09_workshop_craft.py")
    want = B.candidates()
    if sorted(man["assets"]) != sorted(n for n, *_ in want):
        problems.append(f"assets {sorted(set(man['assets']) ^ {n for n, *_ in want})} differ")
    for name, mesh, socks, frame, lantern_frame in want:
        entry = man["assets"].get(name)
        if entry is None:
            continue
        p, row = check_asset(name, mesh, socks, lantern_frame, build / entry["fbx"], entry)
        rows[name] = row
        problems += [f"{name}: {x}" for x in p]
    out = {"build": str(build.relative_to(ROOT)), "manifest_sha256": sha256(build / "manifest.json"),
           "checker_sha256": sha256(__file__), "module_sha256": sha256(B.__file__), "assets": len(rows),
           "tolerances": {"cm": TOL_CM, "axis": TOL_AXIS, "uv": TOL_UV},
           "worst": {"vertex_err_cm": max((r.get("vertex_err_cm", 0.0) for r in rows.values()), default=None),
                     "socket_position_err_cm": max((r["socket_err"]["position_cm"] for r in rows.values() if "socket_err" in r), default=None),
                     "socket_axis_err": max((r["socket_err"]["axis"] for r in rows.values() if "socket_err" in r), default=None),
                     "uv_err": max((max(r["uv_err"]) for r in rows.values() if "uv_err" in r), default=None)},
           "problems": problems, "rows": rows}
    text = json.dumps(out, indent=1)
    if record_path is not None:
        with open(record_path, "x") as fh:
            fh.write(text + "\n")
    print("B09_FBX_CHECK " + json.dumps({k: out[k] for k in ("build", "assets", "worst", "problems")}, indent=1))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
