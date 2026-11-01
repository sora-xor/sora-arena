"""Plan the third-person paw review's close cameras (render_nyaakoto_tp_review.py) from the paws as built.

Root (20:31 UTC 2026-10-26) asked for the actual Unreal materials, both paws empty and holding, from their pads and
from their backs. Where a pad can be seen from depends on the paw: holding, the pads face the grip channel inside the
curl; empty, the toes open. So the views are measured, not guessed:
- **The paws, rebuilt.** Each is meshed again with nyaakoto_tp_paws (the module that built the assets: the runtime
  manifest's module_sha256), from the record's own frame, palm radii and LOD0 step. Its skin must have the record's
  vertex and triangle counts, or the planner refuses.
- **Posed in the guard.** Each paw moves with its grip socket. Its points are expressed in the socket's bind frame (the
  record's hand_*_grip), then placed in the guard's targets (import_nyaakoto_third_person.two_paw_targets: the readback
  finds the clip's grips within 0.00005 cm of them).
- **Both states.** Holding is the bind shape; empty is nyaakoto_tp_paws.empty_points, as the PawEmpty morph targets
  are.
- **The regions.** The pads are the faces mesh_paw gives M_Hero_RoseNose. The back is the dorsal tabby: faces whose
  CoatBlend is 0 at every corner and whose normal is within 60 deg of the socket's +Z (from the channel toward the
  palm), less any pad.
- **The score.** Along each of 2,000 directions (a Fibonacci sphere, less the 20 deg about the vertical), both paws
  are splatted into a depth buffer of 2 mm cells, seen along that direction. A region face counts as seen if it faces
  the camera within 75 deg and nothing in its cell is nearer than its own depth less a tolerance (1 mm, plus the
  cell's depth spread at the face's slope). A direction's score in one state is its seen projected area over the best
  direction's. A holding/empty pair shares one camera, so the directions are ranked by the lower of the two states'
  scores.
- **Alone.** Each camera is also ranked with only its own paw's skin in the way ("_solo"): for the reference pose,
  where the paws hang apart (render_nyaakoto_tp_review's "rest" shots).
- **The output** per camera: the target (the paw's bounding-sphere centre over both states) and directions in the
  posed socket's frame, so Unreal places them from the posed socket itself. Also the framing distance, and the ranked
  directions (up to 400, at least 6 deg apart, down to a joint score of 0.15) with their scores. The best few often
  look from where the body is (in the guard the paws' backs face up toward the face), so Unreal needs the list's
  reach.
- **The body** (for Unreal's sight-line test, not this planner's scores): LOD0's skin at bind, sampled at most 2 cm
  apart and binned into 4 cm voxels. Each voxel moves with the bone that most of its samples' dominant weights name.
  The paws (hand_R, hand_L) are left out, since this planner sees them itself. A bone's bind position is its skin
  cluster's TransformLink, in the vertices' own frame and centimetres; hand_R's must land on the record's wrist.
  Attempt 1 measured capsules from the LimbNodes' local chain, which is in metres, and got radii of about 180 cm.
  Attempt 2's capsules came out at the right scale, but the bow, quiver, arrows and saya gave the torso an 89.5 cm
  radius.

The planner measures directions only. Whether a view is clear of the body is decided in Unreal, on the posed bones.

Run (host, numpy): python3.11 scripts/art/plan_nyaakoto_tp_review.py <out.json>
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import fbx_unreal_sockets as FUS  # noqa: E402
import nyaakoto_tp_paws as TPP  # noqa: E402
import nyaakoto_tp_review_geometry as G  # noqa: E402

MANIFEST = ROOT / "Content/SourceArt/Characters/Hero/runtime_skin_manifest.json"
LOD0_FBX = ROOT / "Content/SourceArt/SK_NyaagyuSamurai.fbx"
DIRECTIONS = 2000
MAX_UP = math.cos(math.radians(20.0))      # |d . Z| at most this: no view within 20 deg of the vertical
CELL_CM = 0.2
TOL_CM = 0.1
FACING = math.cos(math.radians(75.0))
BACK_NORMAL = math.cos(math.radians(60.0))
# Up to this many ranked directions per camera, at least 6 deg apart, down to MIN_JOINT. The best few often look at
# the paw from where the body is (a guard's paw backs face up toward the face), so Unreal needs the list's reach.
CANDIDATES = 400
MIN_JOINT = 0.15
SEPARATION = math.cos(math.radians(6.0))
VOXEL_SAMPLE_CM = 2.0          # LOD0's triangles are sampled at most this far apart before voxelising
VOXEL_EXCLUDE = ("hand_R", "hand_L")   # the paws: the planner's own visibility has them


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def blender_to_ue(points_m):
    p = np.asarray(points_m, np.float64)
    return np.stack([p[..., 0], -p[..., 1], p[..., 2]], -1) * 100.0


def axes_rows(x, z):
    """Rows X, Y, Z of a socket frame, as nyaakoto_tp_review_geometry.axes_from_xz (Unreal's MakeFromXZ)."""
    return np.array(G.axes_from_xz(tuple(map(float, x)), tuple(map(float, z))))


def fibonacci_directions(n):
    k = np.arange(n) + 0.5
    z = 1.0 - 2.0 * k / n
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    phi = k * math.pi * (3.0 - math.sqrt(5.0))
    d = np.stack([r * np.cos(phi), r * np.sin(phi), z], 1)
    return d[np.abs(d[:, 2]) <= MAX_UP]


def face_geometry(verts, tris):
    """Centroids, unit normals and areas. For points mirrored into Unreal's axes (blender_to_ue), pass the triangles
    rewound (ue_tris): a mirror turns the winding's normal inward."""
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    cr = np.cross(b - a, c - a)
    area2 = np.linalg.norm(cr, axis=1)
    return (a + b + c) / 3.0, cr / np.maximum(area2, 1e-12)[:, None], 0.5 * area2


def ue_tris(tris):
    """Triangles rewound for points mirrored into Unreal's axes, so their normals stay outward."""
    return np.asarray(tris)[:, [0, 2, 1]]


def splat_points(verts, tris):
    """Occluder samples: the vertices, each face's centroid, and three points nearer its corners."""
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    pts = [verts, (a + b + c) / 3.0]
    for wa, wb, wc in ((4 / 6, 1 / 6, 1 / 6), (1 / 6, 4 / 6, 1 / 6), (1 / 6, 1 / 6, 4 / 6)):
        pts.append(wa * a + wb * b + wc * c)
    return np.concatenate(pts)


def basis(d):
    ref = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(d, ref)
    u /= np.linalg.norm(u)
    return u, np.cross(d, u)


def depth_buffer(occluders, d, cell=CELL_CM):
    """The occluder points splatted along d: per cell of the plane square to d, the nearest depth (larger is nearer a
    camera far along +d)."""
    u, v = basis(d)
    po = np.stack([occluders @ u, occluders @ v], 1)
    lo = po.min(0) - cell
    ij = np.floor((po - lo) / cell).astype(np.int64)
    shape = ij.max(0) + 2
    buf = np.full(int(shape[0] * shape[1]), -np.inf)
    np.maximum.at(buf, ij[:, 0] * shape[1] + ij[:, 1], occluders @ d)
    return {"d": d, "u": u, "v": v, "lo": lo, "shape": shape, "buf": buf, "cell": cell}


def seen(buffer, centroids, normals, tol=TOL_CM):
    """Which faces (centroids, normals) a depth buffer sees: facing within 75 deg, and nothing in their cell nearer
    than their own depth less tol plus the cell's depth spread at their slope."""
    d, u, v, lo, shape, buf, cell = (buffer[k] for k in ("d", "u", "v", "lo", "shape", "buf", "cell"))
    pc = np.stack([centroids @ u, centroids @ v], 1)
    cij = np.floor((pc - lo) / cell).astype(np.int64)
    inside = (cij >= 0).all(1) & (cij < shape).all(1)
    cos = normals @ d
    slope = np.sqrt(np.maximum(0.0, 1.0 - cos * cos)) / np.maximum(cos, 1e-6)
    allowed = tol + cell * np.minimum(slope, 4.0)
    top = np.full(len(centroids), np.inf)
    top[inside] = buf[cij[inside, 0] * shape[1] + cij[inside, 1]]
    return (cos > FACING) & inside & (centroids @ d >= top - allowed)


def rebuild(side, by_side):
    """The paw as built, from the record's frame (nyaakoto_tp_paws.frame_of reads only the channel, the socket's Z,
    the sign and the palm)."""
    fr = by_side[side]["frame"]
    z = np.array(fr["z"], float)
    arm = {"channel": np.array(fr["c"], float), "socket_rot": np.column_stack([np.cross(TPP.Y, z), TPP.Y, z]),
           "sign": int(fr["sign"]), "palm": np.array(fr["palm"], float)}
    m = TPP.mesh_paw(arm, by_side[side]["palm_radii_m"], step=by_side[side]["step_m"])
    want = (by_side[side]["skin"]["vertices"], by_side[side]["skin"]["triangles"])
    if (len(m["verts"]), len(m["tris"])) != want:
        raise SystemExit(f"plan: the rebuilt {side} paw has {len(m['verts'])} vertices and {len(m['tris'])} triangles; "
                         f"the record's has {want}")
    return m


def body_voxels(fbx, record):
    """LOD0's skin at bind as voxels (see the module's notes): {"voxel_cm", "radius_cm", "voxels": [[bone, x, y, z]],
    ...}, in Unreal component cm."""
    data = FUS.read_fbx(fbx)
    nodes, unit = data["nodes"], data.get("unit", 1.0)
    root, _ = FUS.parser().parse(str(fbx))
    objects = {o.props[0]: o for o in FUS._child(root, b"Objects").elems}
    links = [(c.props[0], c.props[1], c.props[2]) for c in FUS._child(root, b"Connections").elems]
    name = lambda o: o.props[1].split(b"\x00\x01")[0].decode()  # noqa: E731
    kind = lambda uid, k, sub: (objects.get(uid) is not None and objects[uid].id == k  # noqa: E731
                                and (sub is None or objects[uid].props[2] == sub))
    heads, samples, sample_bones = {}, [], []
    unweighted = 0
    for gid, geo in objects.items():
        if not kind(gid, b"Geometry", b"Mesh"):
            continue
        model = next(d for k, s_, d in links if k == b"OO" and s_ == gid and kind(d, b"Model", None))
        gm = FUS.global_matrix(nodes, name(objects[model]))
        v = np.array(FUS._child(geo, b"Vertices").props[0], float).reshape(-1, 3)
        w_ = v @ gm[:3, :3].T + gm[:3, 3]
        best_w, best_bone = np.zeros(len(v)), np.full(len(v), "", dtype=object)
        skins = {s_ for k, s_, d in links if d == gid and kind(s_, b"Deformer", b"Skin")}
        for k, s_, d in links:
            if d in skins and kind(s_, b"Deformer", b"Cluster"):
                bone = next((name(objects[b]) for kk, b, dd in links if dd == s_ and kind(b, b"Model", None)), None)
                ix, wt = FUS._child(objects[s_], b"Indexes"), FUS._child(objects[s_], b"Weights")
                if bone is None or ix is None:
                    continue
                # Blender writes TransformLink as the bone's bind matrix, row-major with the translation last.
                link = np.array(FUS._child(objects[s_], b"TransformLink").props[0], float).reshape(4, 4)[3, :3]
                if bone in heads and not np.allclose(heads[bone], link, atol=1e-6):
                    raise SystemExit(f"plan: {bone}'s clusters disagree on its bind position")
                heads[bone] = link
                ix, wt = np.array(ix.props[0], np.int64), np.array(wt.props[0], float)
                better = wt > best_w[ix]
                best_w[ix[better]], best_bone[ix[better]] = wt[better], bone
        unweighted += int((best_bone == "").sum())
        pvi = np.array(FUS._child(geo, b"PolygonVertexIndex").props[0], np.int64)
        corner = np.where(pvi < 0, ~pvi, pvi)
        ends = np.flatnonzero(pvi < 0)
        starts = np.concatenate([[0], ends[:-1] + 1])
        tris = np.concatenate([np.stack([corner[starts[k]].repeat(ends[k] - starts[k] - 1),
                                         corner[starts[k] + 1:ends[k]], corner[starts[k] + 2:ends[k] + 1]], 1)
                               for k in range(len(starts))])
        a, b, c = w_[tris[:, 0]], w_[tris[:, 1]], w_[tris[:, 2]]
        longest = np.maximum.reduce([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1),
                                     np.linalg.norm(a - c, axis=1)]) * unit
        steps = np.maximum(1, np.ceil(longest / (VOXEL_SAMPLE_CM))).astype(np.int64)
        for n in np.unique(steps):
            sel = steps == n
            grid = [(i / n, j / n) for i in range(n + 1) for j in range(n + 1 - i)]
            for wb, wc in grid:
                samples.append(a[sel] + wb * (b[sel] - a[sel]) + wc * (c[sel] - a[sel]))
                sample_bones.append(best_bone[tris[sel, 0]])
    ue = lambda q: np.stack([-q[..., 0], q[..., 1], q[..., 2]], -1) * unit  # noqa: E731  FBX world -> Unreal cm
    wrist = blender_to_ue(np.array(record["third_person"]["arm_joints_blender_m"]["R"]["wrist"]))
    if np.linalg.norm(ue(heads["hand_R"]) - wrist) > 0.01:
        raise SystemExit(f"plan: hand_R binds at {ue(heads['hand_R'])} cm, not the record's wrist {wrist}")
    P, B = ue(np.concatenate(samples)), np.concatenate(sample_bones)
    keep = ~np.isin(B, VOXEL_EXCLUDE) & (B != "")
    P, B = P[keep], B[keep]
    key = np.floor(P / G.VOXEL_CM).astype(np.int64)
    _, inverse = np.unique(key, axis=0, return_inverse=True)
    inverse = inverse.ravel()
    voxels = []
    for k in range(inverse.max() + 1):
        members = inverse == k
        bones, counts = np.unique(B[members], return_counts=True)
        centre = P[members].mean(0)
        voxels.append([str(bones[np.argmax(counts)])] + [round(float(x), 2) for x in centre])
    return {"voxel_cm": G.VOXEL_CM, "radius_cm": G.VOXEL_RADIUS_CM, "sample_cm": VOXEL_SAMPLE_CM,
            "excluded_bones": list(VOXEL_EXCLUDE), "unweighted_vertices": unweighted,
            "bind_heads_cm": {b: [round(float(x), 4) for x in ue(h)] for b, h in sorted(heads.items())},
            "voxels": voxels}


def ranked(joint, dirs, stats, socket_axes):
    order = np.argsort(-joint, kind="stable")
    picked = []
    for i in order:
        if len(picked) >= CANDIDATES or joint[i] < MIN_JOINT:
            break
        if any(dirs[i] @ dirs[j] > SEPARATION for j in picked):
            continue
        picked.append(i)
    rows = []
    for i in picked:
        rows.append({"direction": [round(float(x), 6) for x in socket_axes @ dirs[i]],
                     "direction_guard_ue": [round(float(x), 6) for x in dirs[i]],
                     "joint": round(float(joint[i]), 4),
                     **{state: {k: round(float(v[i]), 4) for k, v in stats[state].items()} for state in stats}})
    return rows


def plan():
    record = json.loads(MANIFEST.read_text())
    tp = record["third_person"]
    paws = tp["paws"]
    module_sha = sha256(TPP.__file__)
    if module_sha != paws["module_sha256"]:
        raise SystemExit(f"plan: {TPP.__file__} ({module_sha[:12]}) is not the paw module that built the assets")
    stance, _ = G.pose_stance("guard", tp)
    targets = G.two_paw_targets(stance)
    meshes, posed, regions, frames = {}, {}, {}, {}
    for side in ("R", "L"):
        m = meshes[side] = rebuild(side, paws["by_side"])
        sock = tp["sockets"][G.SOCKETS[side]]
        bind_o, bind_ax = np.array(sock["component_cm"], float), axes_rows(sock["x_axis"], sock["z_axis"])
        o, x, z = targets[G.SOCKETS[side]]
        pose_o, pose_ax = np.array(o, float), axes_rows(x, z)
        frames[side] = (pose_o, pose_ax)
        for state, v in (("holding", m["verts"]), ("empty", TPP.empty_points(m["verts"], m["skeleton"]))):
            local = (blender_to_ue(v) - bind_o) @ bind_ax.T
            posed[side, state] = pose_o + local @ pose_ax
        _, n_bind, _ = face_geometry(blender_to_ue(m["verts"]), ue_tris(m["tris"]))
        dorsal = (n_bind @ bind_ax[2]) > BACK_NORMAL
        tabby = (np.asarray(m["coat"]) < 1e-6).all(1)
        regions[side] = {"pads": np.asarray(m["pad"], bool), "back": tabby & dorsal & ~np.asarray(m["pad"], bool)}
    dirs = fibonacci_directions(DIRECTIONS)

    def score(occluder_sides, region_sides, state, into):
        """Seen projected area and share per (side, view, state) and direction, past the occluder sides' skins."""
        occ = np.concatenate([splat_points(posed[s, state], meshes[s]["tris"]) for s in occluder_sides])
        geo = {s: face_geometry(posed[s, state], ue_tris(meshes[s]["tris"])) for s in region_sides}
        sets = {(side, view): tuple(x[mask] for x in geo[side])
                for side in region_sides for view, mask in regions[side].items()}
        for key in sets:
            into[key + (state,)] = (np.zeros(len(dirs)), np.zeros(len(dirs)))
        for k, d in enumerate(dirs):
            buffer = depth_buffer(occ, d)
            for key, (c, n, a) in sets.items():
                ok = seen(buffer, c, n)
                proj, share = into[key + (state,)]
                proj[k] = float((a[ok] * (n[ok] @ d)).sum())
                share[k] = float(a[ok].sum() / a.sum())

    # In the guard both paws are in each other's way; alone ("solo", for the reference pose, where they hang apart),
    # only a paw's own skin is.
    area, solo = {}, {}
    for state in ("holding", "empty"):
        score(("R", "L"), ("R", "L"), state, area)
        for side in ("R", "L"):
            score((side,), (side,), state, solo)
    aspect = G.RESOLUTION[0] / G.RESOLUTION[1]
    cameras = {}
    for side in ("R", "L"):
        both = np.concatenate([posed[side, "holding"], posed[side, "empty"]])
        lo, hi = both.min(0), both.max(0)
        centre = 0.5 * (lo + hi)
        radius = float(np.linalg.norm(both - centre, axis=1).max())
        pose_o, pose_ax = frames[side]
        for view in ("pads", "back"):
            for suffix, source in (("", area), ("_solo", solo)):
                stats, norm_scores = {}, []
                for state in ("holding", "empty"):
                    proj, share = source[side, view, state]
                    norm_scores.append(proj / max(proj.max(), 1e-12))
                    stats[state] = {"score": norm_scores[-1], "seen_share": share, "seen_projected_cm2": proj}
                joint = np.minimum(*norm_scores)
                cameras[f"paw_{side}_{view}{suffix}"] = {
                    "socket": G.SOCKETS[side], "side": side, "view": view,
                    "occluders": "both paws, as in the guard" if not suffix else "the paw's own skin alone",
                    "target_local_cm": [round(float(x), 4) for x in pose_ax @ (centre - pose_o)],
                    "target_guard_ue_cm": [round(float(x), 4) for x in centre],
                    "radius_cm": round(radius, 4), "fov_deg": G.CLOSE_FOV_DEG,
                    "distance_cm": round(G.fit_distance(radius, G.CLOSE_FOV_DEG, aspect), 3),
                    "region_faces": {"pads": int(regions[side]["pads"].sum()), "back": int(regions[side]["back"].sum())}[view],
                    "candidates": ranked(joint, dirs, stats, pose_ax)}
    inputs = {"runtime_skin_manifest": sha256(MANIFEST), "paw_module": module_sha, "lod0_fbx": sha256(LOD0_FBX),
              "planner": sha256(__file__), "geometry": sha256(G.__file__)}
    return {"schema": 1, "generator": "scripts/art/plan_nyaakoto_tp_review.py", "inputs": inputs,
            "resolution": list(G.RESOLUTION), "pose": "guard", "stance": stance,
            "guard_targets_cm": {k: {"origin": list(v[0]), "x": list(v[1]), "z": list(v[2])} for k, v in targets.items()},
            "directions": int(len(dirs)), "cell_cm": CELL_CM, "tolerance_cm": TOL_CM,
            "skin": {s: {"vertices": int(len(meshes[s]["verts"])), "triangles": int(len(meshes[s]["tris"])),
                         "pad_faces": int(regions[s]["pads"].sum()), "back_faces": int(regions[s]["back"].sum())}
                     for s in ("R", "L")},
            "cameras": cameras, "body": body_voxels(LOD0_FBX, record)}


def main():
    out = Path(sys.argv[1])
    if out.exists():
        raise SystemExit(f"plan: {out} exists; plans are new files")
    result = plan()
    out.write_text(json.dumps(result, indent=1) + "\n")
    summary = {k: {"best": v["candidates"][0]["joint"],
                   "holding_seen": v["candidates"][0]["holding"]["seen_share"],
                   "empty_seen": v["candidates"][0]["empty"]["seen_share"], "distance_cm": v["distance_cm"]}
               for k, v in result["cameras"].items()}
    body = result["body"]
    print("NYAAKOTO_TP_REVIEW_PLAN " + json.dumps({"cameras": summary, "voxels": len(body["voxels"]),
                                                   "unweighted_vertices": body["unweighted_vertices"]}))


if __name__ == "__main__":
    main()
