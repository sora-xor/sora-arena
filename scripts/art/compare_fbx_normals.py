"""How far the normals Unreal builds are from the ones we author, corner by corner, from two FBX files.

Root (21:3x UTC 2026-10-26) asked for an authored-normal candidate with the imported normals verified. Unreal's FBX
export of an imported skeletal mesh writes the normals its build made (what the renderer shades with). This compares
them with our FBX's authored ones:
- **Our FBX** (Blender's export): per-corner normals (LayerElementNormal, ByPolygonVertex). The skin keeps Blender's
  own normals; each fur strand's three corners carry its root's skin normal (nyaakoto_runtime_parts.set_strand_normals).
- **Unreal's export:** one mesh per LOD. Only the LOD named on the command line is compared (LOD0 by default).
- **The frames:** both are brought to Blender's world metres by the axis map that puts the paws' strand vertices on
  each other (our files: a half turn about Z; Unreal's: identity, inspect_fbx_paw_coat's finding).
- **Matching:** each of our corners is matched to Unreal's corners at the same position, within 0.02 mm. Unreal splits
  a vertex wherever its normal, tangent or UV differs, so one position can hold several corners. The angle reported is
  to the nearest normal among them, so a skin corner may be matched optimistically. A strand vertex has a single
  corner in both files, so its match is exact.
- **Groups,** by the bone weighting a corner's vertex most and whether its polygon is isolated (no vertex shared with
  another polygon): the paws' strands and skin (hand_R, hand_L), the head's cards and skin (head, neck), and the rest
  of the body's isolated polygons and skin. For every group it also reports the angle between the authored normal and
  the polygon's own face normal, which is what a build that recomputes them gives an isolated polygon.

It reports per group the percentiles of the angle, how many corners found no match, and the axis map.

Run (host, numpy): python3.11 scripts/art/compare_fbx_normals.py <our .fbx> <Unreal's export .fbx> <out.json> [LOD]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fbx_unreal_sockets as FUS  # noqa: E402

MATCH_M = 0.0002 / 1.0          # 0.2 mm in Blender metres: the position tolerance's cell (then 0.02 mm exact check)
TOL_M = 0.00002                 # 0.02 mm
AXIS_MAPS = {"identity": np.eye(3) / 100.0, "half_turn_z": np.diag([-1.0, -1.0, 1.0]) / 100.0}
PERCENTILES = (50, 90, 99, 100)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_meshes(path):
    """{model name: {"positions" (corner, 3) world, "normals" (corner, 3) world unit, "vertex" (corner,), "uses"
    (vertex,), "poly" (corner,)}} in the file's own world units."""
    root, _ = FUS.parser().parse(str(path))
    objects = {o.props[0]: o for o in FUS._child(root, b"Objects").elems}
    links = [(c.props[0], c.props[1], c.props[2]) for c in FUS._child(root, b"Connections").elems]
    globals_ = FUS.model_globals(root)
    name = lambda o: o.props[1].split(b"\x00\x01")[0].decode()  # noqa: E731
    out = {}
    for gid, geo in objects.items():
        if geo.id != b"Geometry" or geo.props[2] != b"Mesh":
            continue
        model_uid = next(d for k, s, d in links if k == b"OO" and s == gid and objects.get(d) is not None
                         and objects[d].id == b"Model")
        model = name(objects[model_uid])
        g = globals_[model_uid]                                 # by UID: Unreal may give the mesh its root's name
        v = np.array(FUS._child(geo, b"Vertices").props[0], float).reshape(-1, 3)
        pvi = np.array(FUS._child(geo, b"PolygonVertexIndex").props[0], np.int64)
        corner_vertex = np.where(pvi < 0, ~pvi, pvi)
        layer = FUS._child(geo, b"LayerElementNormal")
        mapping = FUS._child(layer, b"MappingInformationType").props[0].decode()
        reference = FUS._child(layer, b"ReferenceInformationType").props[0].decode()
        normals = np.array(FUS._child(layer, b"Normals").props[0], float).reshape(-1, 3)
        if reference == "IndexToDirect":
            normals = normals[np.array(FUS._child(layer, b"NormalsIndex").props[0], np.int64)]
        if mapping in ("ByVertice", "ByVertex"):
            normals = normals[corner_vertex]
        elif mapping != "ByPolygonVertex":
            raise SystemExit(f"{path}: {model}'s normals are {mapping}, which is not modelled")
        lin = g[:3, :3]
        world_n = normals @ np.linalg.inv(lin)                 # normals transform by the inverse transpose
        world_n /= np.maximum(np.linalg.norm(world_n, axis=1, keepdims=True), 1e-12)
        best_w, best_bone = np.zeros(len(v)), np.full(len(v), "", dtype=object)
        skins = {s for k, s, d in links if d == gid and objects.get(s) is not None and objects[s].id == b"Deformer"
                 and objects[s].props[2] == b"Skin"}
        for k, s, d in links:
            if d in skins and objects.get(s) is not None and objects[s].id == b"Deformer" and objects[s].props[2] == b"Cluster":
                bone = next((name(objects[b]) for kk, b, dd in links if dd == s and objects.get(b) is not None
                             and objects[b].id == b"Model"), None)
                ix, w = FUS._child(objects[s], b"Indexes"), FUS._child(objects[s], b"Weights")
                if bone is None or ix is None:
                    continue
                ix, w = np.array(ix.props[0], np.int64), np.array(w.props[0], float)
                better = w > best_w[ix]
                best_w[ix[better]], best_bone[ix[better]] = w[better], bone
        out[model] = {"positions": (v @ lin.T + g[:3, 3])[corner_vertex], "normals": world_n,
                      "vertex": corner_vertex, "uses": np.bincount(corner_vertex, minlength=len(v)),
                      "poly": np.concatenate([[0], np.cumsum(pvi < 0)[:-1]]), "mapping": mapping,
                      "bone": best_bone[corner_vertex]}
    return out


def isolated(m):
    """Per corner: on a polygon none of whose vertices any other polygon uses (a strand or a card)."""
    shared = np.bincount(m["poly"], weights=(m["uses"][m["vertex"]] > 1).astype(float))
    return shared[m["poly"]] == 0


def angle_deg(a, b):
    return np.degrees(np.arccos(np.clip((a * b).sum(-1), -1.0, 1.0)))


def face_normals(m):
    """Each corner's polygon normal (Newell's method), unit."""
    p, poly = m["positions"], m["poly"]
    nxt = np.empty(len(p), np.int64)
    starts = np.concatenate([[0], np.flatnonzero(np.diff(poly)) + 1])
    ends = np.concatenate([starts[1:], [len(p)]])
    for s, e in zip(starts, ends):
        nxt[s:e] = np.roll(np.arange(s, e), -1)
    a, b = p, p[nxt]
    n = np.zeros((poly.max() + 1, 3))
    np.add.at(n, poly, np.stack([(a[:, 1] - b[:, 1]) * (a[:, 2] + b[:, 2]), (a[:, 2] - b[:, 2]) * (a[:, 0] + b[:, 0]),
                                 (a[:, 0] - b[:, 0]) * (a[:, 1] + b[:, 1])], 1))
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    return n[poly]


def match(ours_p, ours_n, theirs_p, theirs_n):
    """For each of our corners, the least angle to one of their corners within TOL_M (nan where none)."""
    key = lambda p: np.floor(p / MATCH_M).astype(np.int64)  # noqa: E731
    order = {}
    for i, k in enumerate(map(tuple, key(theirs_p))):
        order.setdefault(k, []).append(i)
    best = np.full(len(ours_p), np.nan)
    offsets = [(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)]
    for i, k in enumerate(map(tuple, key(ours_p))):
        cand = [j for o in offsets for j in order.get((k[0] + o[0], k[1] + o[1], k[2] + o[2]), ())]
        if not cand:
            continue
        cand = np.array(cand)
        close = cand[np.linalg.norm(theirs_p[cand] - ours_p[i], axis=1) <= TOL_M]
        if len(close):
            best[i] = angle_deg(theirs_n[close], ours_n[i]).min()
    return best


def stats(x):
    x = x[np.isfinite(x)]
    if not len(x):
        return None
    return {f"p{q}": round(float(np.percentile(x, q)), 4) for q in PERCENTILES} | {"corners": int(len(x))}


def compare(ours_path, theirs_path, lod=0):
    ours = read_meshes(ours_path)
    if len(ours) != 1:
        raise SystemExit(f"{ours_path}: {len(ours)} meshes; one is expected")
    o = next(iter(ours.values()))
    theirs_all = read_meshes(theirs_path)
    name = next((n for n in theirs_all if n.endswith(f"_LOD{lod}")), None) if len(theirs_all) > 1 else next(iter(theirs_all))
    if name is None:
        raise SystemExit(f"{theirs_path}: no mesh named *_LOD{lod} among {sorted(theirs_all)}")
    t = theirs_all[name]
    iso = isolated(o)
    paw = np.isin(o["bone"], ["hand_R", "hand_L"])
    head = np.isin(o["bone"], ["head", "neck"])
    groups = {"paw_strands": paw & iso, "paw_skin": paw & ~iso, "head_cards": head & iso, "head_skin": head & ~iso,
              "other_isolated": ~paw & ~head & iso, "other_skin": ~paw & ~head & ~iso}
    strand = groups["paw_strands"]
    # The frame: the map that puts our strand corners on theirs (the most exact matches over a sample).
    sample = np.flatnonzero(strand)[:: max(1, int(strand.sum()) // 2000)] if strand.any() else np.arange(min(2000, len(o["positions"])))
    fits = {}
    for a_label, a in AXIS_MAPS.items():
        for b_label, b in AXIS_MAPS.items():
            got = match(o["positions"][sample] @ a.T, o["normals"][sample] @ np.sign(a.T * 100.0),
                        t["positions"] @ b.T, t["normals"] @ np.sign(b.T * 100.0))
            fits[(a_label, b_label)] = int(np.isfinite(got).sum())
    (a_label, b_label) = max(fits, key=fits.get)
    a, b = AXIS_MAPS[a_label], AXIS_MAPS[b_label]
    op, on = o["positions"] @ a.T, o["normals"] @ np.sign(a.T * 100.0)
    tp, tn = t["positions"] @ b.T, t["normals"] @ np.sign(b.T * 100.0)
    best = match(op, on, tp, tn)
    own_face = angle_deg(face_normals(o), o["normals"])
    return {"ours": {"file": str(ours_path), "sha256": sha256(ours_path), "normals": o["mapping"]},
            "theirs": {"file": str(theirs_path), "sha256": sha256(theirs_path), "mesh": name, "normals": t["mapping"]},
            "axis_maps": {"ours": a_label, "theirs": b_label, "sample_matches": fits[(a_label, b_label)],
                          "sample": int(len(sample))},
            "corners": {"ours": int(len(op)), "theirs": int(len(tp)), "unmatched": int(np.isnan(best).sum())},
            "angle_to_unreal_deg": {g: stats(best[m]) for g, m in groups.items()},
            "unmatched_by_group": {g: int(np.isnan(best[m]).sum()) for g, m in groups.items()},
            "authored_vs_own_face_deg": {g: stats(own_face[m]) for g, m in groups.items()}}


def main():
    ours, theirs, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    lod = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    if out.exists():
        raise SystemExit(f"{out} exists")
    result = compare(ours, theirs, lod)
    out.write_text(json.dumps(result, indent=1) + "\n")
    print("FBX_NORMALS " + json.dumps({k: result[k] for k in ("axis_maps", "corners", "angle_to_unreal_deg",
                                                              "authored_vs_own_face_deg")}))


if __name__ == "__main__":
    main()
