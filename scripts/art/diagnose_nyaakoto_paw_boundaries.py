"""Diagnose the paws' sawtooth boundaries in a review original (root, 2026-10-26: "broad sawtooth coat/pad boundaries").

Two per-face choices in nyaakoto_tp_paws.mesh_paw draw a boundary along triangle edges, so on the 3 mm LOD0 grid
the boundary is a staircase:
- **The pads:** pad_faces gives whole faces M_Hero_RoseNose.
- **The UVs:** corner_uvs maps a face planar in the channel's cross-section when it looks along the channel
  (|n . Y| > SIDE_FACING), and otherwise round the channel by arc length. The two mappings are unrelated, so the fur
  texture jumps where they meet.
The coat (CoatBlend) is per vertex, so it should change smoothly. This tests that rather than assuming it.

It rebuilds the paw exactly (the planner's rebuild, to the record's skin counts) and poses it as the shot was posed:
the guard by its grip socket, or the reference pose. It then renders the paw on the CPU from the shot's own camera,
read from the review manifest, colouring each face by its UV mapping and marking the pads. That render is set beside
the original's same frame.

It measures:
- faces and boundary edges per class, with their lengths;
- the UV jump across each planar/round edge, in UV units and in centimetres of texture;
- the coat's change across edges, against its change across the UV and pad boundaries.

Run (host, numpy and PIL: /usr/bin/python3):
    /usr/bin/python3 scripts/art/diagnose_nyaakoto_paw_boundaries.py <review dir> <shot> <side> <out prefix>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nyaakoto_tp_paws as TPP  # noqa: E402
import nyaakoto_tp_review_geometry as G  # noqa: E402
import plan_nyaakoto_tp_review as PL  # noqa: E402

SUB = 14                     # barycentric subdivisions per face: about 0.2 mm apart, under a pixel at 960x540
COLOURS = {"round": (70, 150, 90), "planar": (200, 80, 60), "pad": (235, 150, 170)}


def camera_basis(rotation_deg):
    """Unreal's camera axes from its rotator (pitch, yaw, roll; roll is 0 for find_look_at_rotation)."""
    p, y = math.radians(rotation_deg[0]), math.radians(rotation_deg[1])
    f = np.array([math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)])
    r = np.array([-math.sin(y), math.cos(y), 0.0])
    u = np.array([-math.sin(p) * math.cos(y), -math.sin(p) * math.sin(y), math.cos(p)])
    return f, r, u


def posed_ue(m, side, record, pose):
    """The paw's skin in Unreal component cm as the shot posed it."""
    v = PL.blender_to_ue(m["verts"])
    if pose == "rest":
        return v
    tp = record["third_person"]
    sock = tp["sockets"][G.SOCKETS[side]]
    bind_o, bind_ax = np.array(sock["component_cm"], float), PL.axes_rows(sock["x_axis"], sock["z_axis"])
    stance, _ = G.pose_stance(pose, tp)
    o, x, z = G.two_paw_targets(stance)[G.SOCKETS[side]]
    return np.array(o) + ((v - bind_o) @ bind_ax.T) @ PL.axes_rows(x, z)


def render(points_ue, tris, face_rgb, cam, width, height):
    f, r, u = camera_basis(cam["rotation_deg"])
    c = np.array(cam["location_cm"], float)
    tan_h = math.tan(math.radians(cam["field_of_view_deg"]) / 2.0)
    tan_v = tan_h / (width / height)
    bary = [(i / SUB, j / SUB) for i in range(SUB + 1) for j in range(SUB + 1 - i)]
    a, b, cc = points_ue[tris[:, 0]], points_ue[tris[:, 1]], points_ue[tris[:, 2]]
    pts = np.concatenate([a + wb * (b - a) + wc * (cc - a) for wb, wc in bary])
    face = np.tile(np.arange(len(tris)), len(bary))
    d = pts - c
    depth = d @ f
    ok = depth > 1.0
    x = (d @ r)[ok] / depth[ok] / tan_h
    y = (d @ u)[ok] / depth[ok] / tan_v
    col = np.floor((x + 1.0) * 0.5 * width).astype(np.int64)
    row = np.floor((1.0 - y) * 0.5 * height).astype(np.int64)
    inside = (col >= 0) & (col < width) & (row >= 0) & (row < height)
    idx, z, fc = row[inside] * width + col[inside], depth[ok][inside], face[ok][inside]
    zbuf = np.full(width * height, np.inf)
    np.minimum.at(zbuf, idx, z)
    front = z <= zbuf[idx] + 1e-6
    img = np.full((width * height, 3), 255, np.uint8)
    img[idx[front]] = face_rgb[fc[front]]
    return img.reshape(height, width, 3), (zbuf < np.inf).reshape(height, width)


def edges_between(tris, cls_a, cls_b):
    """Edges shared by a face of class a and one of class b (each once), as vertex pairs with the two faces."""
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    f = np.tile(np.arange(len(tris)), 3)
    key = np.sort(e, 1)
    order = np.lexsort((key[:, 1], key[:, 0]))
    key, f, e = key[order], f[order], e[order]
    same = (key[1:] == key[:-1]).all(1)
    i = np.flatnonzero(same)
    fa, fb = f[i], f[i + 1]
    hit = (cls_a[fa] & cls_b[fb]) | (cls_b[fa] & cls_a[fb])
    return key[i][hit], fa[hit], fb[hit]


def corner_of(tris, face, vertex):
    """The corner index (0-2) of a vertex in a face."""
    return np.argmax(tris[face] == vertex[:, None], axis=1)


def main():
    review, shot, side, prefix = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
    manifest = json.loads((review / "manifest.json").read_text())
    row = manifest["shots"][shot]
    record = json.loads(PL.MANIFEST.read_text())
    m = PL.rebuild(side, record["third_person"]["paws"]["by_side"])
    verts, tris = m["verts"], np.asarray(m["tris"])
    fr = m["skeleton"]["frame"]
    pose, state = row["shot"]["pose"], row["shot"]["state"]
    shape = TPP.empty_points(verts, m["skeleton"]) if state == "empty" else verts
    n = np.cross(shape[tris[:, 1]] - shape[tris[:, 0]], shape[tris[:, 2]] - shape[tris[:, 0]])
    planar = np.abs(n @ TPP.Y) > TPP.SIDE_FACING * np.linalg.norm(n, axis=1)
    if state == "empty":                             # the UVs are the bind shape's (the morph moves no UV)
        nb = np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]])
        planar = np.abs(nb @ TPP.Y) > TPP.SIDE_FACING * np.linalg.norm(nb, axis=1)
    pad = np.asarray(m["pad"], bool)
    rgb = np.where(pad[:, None], COLOURS["pad"], np.where(planar[:, None], COLOURS["planar"], COLOURS["round"])).astype(np.uint8)
    m2 = dict(m, verts=shape)
    pts = posed_ue(m2, side, record, pose)
    width, height = (x // 4 for x in manifest["resolution"])
    img, mask = render(pts, PL.ue_tris(tris), rgb, row["camera"], width, height)
    with Image.open(review / f"{shot}.png") as im:
        ue = np.asarray(im.convert("RGB").resize((width, height), Image.LANCZOS))
    ys, xs = np.nonzero(mask)
    pad_px = 24
    box = (max(0, xs.min() - pad_px), max(0, ys.min() - pad_px), min(width, xs.max() + pad_px), min(height, ys.max() + pad_px))
    crop = lambda a: a[box[1]:box[3], box[0]:box[2]]  # noqa: E731
    Image.fromarray(np.concatenate([crop(ue), crop(img)], 1)).save(f"{prefix}_{shot}.png")
    uv = m["uvs"]                                    # per corner, UV units (UV_PER_M per metre)
    coat = np.asarray(m["coat"])                     # per corner
    stats = {}
    for label, (ca, cb) in {"planar_round": (planar & ~pad, ~planar & ~pad), "pad_fur": (pad, ~pad)}.items():
        key, fa, fb = edges_between(tris, ca, cb)
        length_mm = np.linalg.norm(verts[key[:, 0]] - verts[key[:, 1]], axis=1) * 1000.0
        jumps, coat_steps = [], []
        for k in (0, 1):
            va = key[:, k]
            ua = uv[fa, corner_of(tris, fa, va)]
            ub = uv[fb, corner_of(tris, fb, va)]
            jumps.append(np.linalg.norm(ua - ub, axis=1))
            coat_steps.append(np.abs(coat[fa, corner_of(tris, fa, va)] - coat[fb, corner_of(tris, fb, va)]))
        jump = np.maximum(*jumps)
        stats[label] = {"edges": int(len(key)), "length_mm": round(float(length_mm.sum()), 1),
                        "edge_mm_median": round(float(np.median(length_mm)), 3) if len(key) else None,
                        "uv_jump_median": round(float(np.median(jump)), 5) if len(key) else None,
                        "uv_jump_p90": round(float(np.percentile(jump, 90)), 5) if len(key) else None,
                        "texture_jump_cm_median": round(float(np.median(jump) / TPP.UV_PER_M * 100.0), 3) if len(key) else None,
                        "coat_step_max": round(float(np.max(coat_steps)), 6) if len(key) else None}
    # The coat across every interior edge: a per-vertex attribute changes by the same amount on both faces.
    key, fa, fb = edges_between(tris, np.ones(len(tris), bool), np.ones(len(tris), bool))
    va = key[:, 0]
    step = np.abs(coat[fa, corner_of(tris, fa, va)] - coat[fb, corner_of(tris, fb, va)])
    result = {"review": str(review), "shot": shot, "side": side, "pose": pose, "state": state,
              "faces": int(len(tris)), "pad_faces": int(pad.sum()), "planar_uv_faces": int((planar & ~pad).sum()),
              "round_uv_faces": int((~planar & ~pad).sum()), "boundaries": stats,
              "coat_discontinuity_across_any_edge_max": round(float(step.max()), 6),
              "render": f"{prefix}_{shot}.png", "render_box_px": [int(b) for b in box],
              "colours": {k: list(v) for k, v in COLOURS.items()}}
    Path(f"{prefix}_{shot}.json").write_text(json.dumps(result, indent=1) + "\n")
    print("PAW_BOUNDARIES " + json.dumps({k: result[k] for k in ("shot", "pad_faces", "planar_uv_faces", "boundaries",
                                                                 "coat_discontinuity_across_any_edge_max")}))


if __name__ == "__main__":
    main()
