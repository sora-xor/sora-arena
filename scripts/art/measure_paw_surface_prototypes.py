"""Measure the paw-surface prototypes (nyaakoto_tp_paw_surface) against the baseline, on the CPU.

Root asked (2026-10-26) for a continuous paw UV mapping and pads cut along a smooth contour of a per-vertex field. The
pads keep their geometric separation and the PBR material's semantics. Both are to be measured against the baseline,
with alternatives compared if a single mapping stretches too much. No rebuild, import or render in Unreal.

**Each paw is rebuilt as built** (plan_nyaakoto_tp_review.rebuild: the record's skin counts). The baseline is
mesh_paw's own UVs and pad faces.

**The UV mappings** (baseline, round, torus_arc, torus_tiles) are measured on the baseline mesh:
- **Stretch.** The singular values of each face's Jacobian (surface metres to UV), over UV_PER_M, so an isometric
  face reads 1. Reported as area-weighted percentiles of the larger and smaller value, the anisotropy (their ratio) and
  the area scale (their product), overall and by region:
  - the back: coat 0 and facing within 60 deg of the palm's side;
  - the sides: |n . Y| > 0.75;
  - the inner wall: within 8 mm of the channel;
  - the toes: digit weight above one half.
- **Flips.** Faces whose UV winding opposes the majority.
- **Seams.** Edges whose two faces give a vertex different UVs. Reported as their length and the jump in centimetres
  of texture. A jump that is a whole number of the mapping's tile periods joins texture to itself; its residual is
  reported apart.

**The pad cut** (pad_field, cut_by_field):
- **Contour error.** The distance from the true zero contour (|f| / |grad f|, sampled along every cut segment),
  against the same for the baseline's staircase (along its pad/fur edges).
- **Pad area.** The cut's and the baseline's, against the true area by dense sampling.
- **Triangle quality.** Every face's smallest angle and area, against the baseline's.
- **Topology.** Every edge shared by exactly two faces in opposite directions; V - E + F unchanged.
- **Morph.** empty_points at the new vertices; faces the empty fist turns over (the record's check); how far a new
  vertex's rule position is from the line between its edge's ends' rule positions.
- **Attributes.** The coat rule at the new vertices against interpolating it. Every paw vertex is weighted 1.0 to
  its hand (LOD0's FBX), so the new ones are too.

**Renders** (CPU, from s132's own cameras: the rest-pose pads, and the guard's back with the paw empty): a
checkerboard of 2.08 cm texture squares (20 a tile), with pads in rose, for the baseline and each mapping. The cut's
pads are drawn beside the baseline's.

Run (host: /usr/bin/python3 has numpy, scipy, PIL): /usr/bin/python3 scripts/art/measure_paw_surface_prototypes.py <out dir>
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import diagnose_nyaakoto_paw_boundaries as D  # noqa: E402
import nyaakoto_tp_paw_surface as S  # noqa: E402
import nyaakoto_tp_paws as TPP  # noqa: E402
import plan_nyaakoto_tp_review as PL  # noqa: E402

REVIEW = ROOT / "Saved/NyaakotoThirdPerson/Review/s132"
VIEWS = ("paw_R_pads_holding_rest_LOD0", "paw_R_back_empty_LOD0")
CHECKS_PER_TILE = 20
PCT = (1, 10, 50, 90, 99)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def face_frames(verts, tris):
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    e1, e2 = b - a, c - a
    n = np.cross(e1, e2)
    area = 0.5 * np.linalg.norm(n, axis=1)
    x = e1 / np.maximum(np.linalg.norm(e1, axis=1, keepdims=True), 1e-15)
    nn = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-15)
    y = np.cross(nn, x)
    E = np.stack([np.stack([(e1 * x).sum(1), (e2 * x).sum(1)], 1),
                  np.stack([(e1 * y).sum(1), (e2 * y).sum(1)], 1)], 1)     # (F, 2, 2): local coords of e1, e2 as columns
    return E, area, nn


def jacobian_stats(verts, tris, uvs):
    """Per face: the singular values of the surface-to-UV Jacobian over UV_PER_M, and its determinant's sign."""
    E, area, _ = face_frames(verts, tris)
    Fm = np.stack([uvs[:, 1] - uvs[:, 0], uvs[:, 2] - uvs[:, 0]], 2)      # (F, 2 [u,v], 2 [edge])
    ok = area > 1e-14
    J = np.zeros((len(tris), 2, 2))
    J[ok] = Fm[ok] @ np.linalg.inv(E[ok])
    sv = np.linalg.svd(J, compute_uv=False) / TPP.UV_PER_M
    return sv[:, 0], sv[:, 1], np.sign(np.linalg.det(J)), area


def weighted_pct(x, w, qs=PCT):
    order = np.argsort(x)
    x, w = x[order], w[order]
    c = np.cumsum(w) / w.sum()
    return {f"p{q}": round(float(np.interp(q / 100.0, c, x)), 4) for q in qs}


def regions(m, verts, tris):
    fr, skel = m["skeleton"]["frame"], m["skeleton"]
    centres = verts[tris].mean(1)
    _, _, nn = face_frames(verts, tris)
    socket_z = np.asarray(fr["z"])
    tabby = (np.asarray(m["coat"]) < 1e-6).all(1) if len(m["coat"]) == len(tris) else np.zeros(len(tris), bool)
    return {"all": np.ones(len(tris), bool),
            "back": tabby & ((nn @ socket_z) > math.cos(math.radians(60.0))),
            "sides": np.abs(nn @ TPP.Y) > TPP.SIDE_FACING,
            "inner": TPP.channel_sdf(centres, fr) < 0.008,
            "toes": TPP.digit_weight(centres, skel) > 0.5}


def stretch_report(verts, tris, uvs, regs):
    smax, smin, sgn, area = jacobian_stats(verts, tris, uvs)
    major = 1.0 if (area * (sgn > 0)).sum() >= (area * (sgn < 0)).sum() else -1.0
    flips = (sgn == -major) & (area > 1e-14)
    aniso = smax / np.maximum(smin, 1e-9)
    out = {"flipped_faces": int(flips.sum()), "flipped_area_share": round(float(area[flips].sum() / area.sum()), 5)}
    for name, mask in regs.items():
        m = mask & ~flips & (area > 1e-14)
        if not m.any():
            continue
        out[name] = {"area_cm2": round(float(area[m].sum() * 1e4), 2),
                     "larger": weighted_pct(smax[m], area[m]), "smaller": weighted_pct(smin[m], area[m]),
                     "anisotropy": weighted_pct(aniso[m], area[m]), "area_scale": weighted_pct((smax * smin)[m], area[m]),
                     "share_anisotropy_over_1.5": round(float(area[m & (aniso > 1.5)].sum() / area[m].sum()), 4),
                     "share_anisotropy_over_2": round(float(area[m & (aniso > 2.0)].sum() / area[m].sum()), 4)}
    return out


def seam_report(verts, tris, uvs, periods):
    key, fa, fb = D.edges_between(tris, np.ones(len(tris), bool), np.ones(len(tris), bool))
    length = np.linalg.norm(verts[key[:, 0]] - verts[key[:, 1]], axis=1)
    jumps = []
    for k in (0, 1):
        v = key[:, k]
        ua = uvs[fa, D.corner_of(tris, fa, v)]
        ub = uvs[fb, D.corner_of(tris, fb, v)]
        d = ua - ub
        for axis, period in enumerate(periods):
            if period:
                d[:, axis] = d[:, axis] - np.round(d[:, axis] / period) * period
        jumps.append((np.linalg.norm(ua - ub, axis=1), np.linalg.norm(d, axis=1)))
    raw = np.maximum(jumps[0][0], jumps[1][0])
    residual = np.maximum(jumps[0][1], jumps[1][1])
    seam = raw > 1e-6
    visible = residual > 1e-4
    cm = lambda x: x / TPP.UV_PER_M * 100.0  # noqa: E731
    return {"seam_edges": int(seam.sum()), "seam_length_mm": round(float(length[seam].sum() * 1000), 1),
            "visible_seam_edges": int(visible.sum()), "visible_seam_length_mm": round(float(length[visible].sum() * 1000), 1),
            "visible_jump_texture_cm": ({"median": round(float(np.median(cm(residual[visible]))), 3),
                                         "p90": round(float(np.percentile(cm(residual[visible]), 90)), 3),
                                         "max": round(float(cm(residual[visible]).max()), 3)} if visible.any() else None)}


def contour_distance(points, skel, h=1e-4):
    """|f| / |grad f| at points (m): the distance to the field's zero contour, to first order."""
    f = S.pad_field(points, skel)
    g = np.stack([(S.pad_field(points + h * np.eye(3)[i], skel) - S.pad_field(points - h * np.eye(3)[i], skel)) / (2 * h)
                  for i in range(3)], 1)
    return np.abs(f) / np.maximum(np.linalg.norm(g, axis=1), 1e-9)


def segment_samples(a, b, n=7):
    t = np.linspace(0.0, 1.0, n)
    return (a[:, None] * (1 - t)[None, :, None] + b[:, None] * t[None, :, None]).reshape(-1, 3)


def tri_quality(verts, tris):
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    def ang(p, q, r):
        u, v = q - p, r - p
        cosv = (u * v).sum(1) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1), 1e-15)
        return np.degrees(np.arccos(np.clip(cosv, -1, 1)))
    mins = np.minimum.reduce([ang(a, b, c), ang(b, c, a), ang(c, a, b)])
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    return mins, area


def topology(tris, nverts):
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    key = np.sort(e, 1)
    _, inv, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    directed = {tuple(x) for x in map(tuple, e)}
    opposite_ok = all((b, a) in directed for a, b in directed)
    return {"edges_not_shared_by_two": int((counts != 2).sum()), "directed_edges_unique": len(directed) == len(e),
            "every_edge_has_its_opposite": bool(opposite_ok), "euler": int(nverts - len(counts) + len(tris))}


def checker_render(points_ue, tris, uvs, pad, cam, width, height):
    """The paw rendered from a review camera: a checkerboard of the UVs, with pads in rose."""
    f, r, u = D.camera_basis(cam["rotation_deg"])
    c = np.array(cam["location_cm"], float)
    tan_h = math.tan(math.radians(cam["field_of_view_deg"]) / 2.0)
    tan_v = tan_h / (width / height)
    sub = D.SUB
    bary = np.array([(i / sub, j / sub) for i in range(sub + 1) for j in range(sub + 1 - i)])
    T = PL.ue_tris(tris)
    pa, pb, pc = points_ue[T[:, 0]], points_ue[T[:, 1]], points_ue[T[:, 2]]
    ua, ub, uc = uvs[:, 0], uvs[:, 2], uvs[:, 1]                 # the corners in the rewound order
    zbuf = np.full(width * height, np.inf)
    colour = np.full((width * height, 3), 255, np.uint8)
    for wb, wc in bary:
        p = pa + wb * (pb - pa) + wc * (pc - pa)
        uv = ua + wb * (ub - ua) + wc * (uc - ua)
        d = p - c
        depth = d @ f
        x = (d @ r) / np.maximum(depth, 1e-6) / tan_h
        y = (d @ u) / np.maximum(depth, 1e-6) / tan_v
        col = np.floor((x + 1.0) * 0.5 * width).astype(np.int64)
        row = np.floor((1.0 - y) * 0.5 * height).astype(np.int64)
        ok = (depth > 1.0) & (col >= 0) & (col < width) & (row >= 0) & (row < height)
        idx = row[ok] * width + col[ok]
        z = depth[ok]
        check = ((np.floor(uv[ok, 0] * CHECKS_PER_TILE) + np.floor(uv[ok, 1] * CHECKS_PER_TILE)) % 2).astype(int)
        rgb = np.where(check[:, None] == 1, [70, 70, 78], [205, 205, 210])
        rgb = np.where(pad[ok][:, None], [232, 140, 160], rgb)
        order = np.argsort(-z)                                    # nearer samples written last
        idx, z, rgb = idx[order], z[order], rgb[order]
        nearer = z < zbuf[idx]
        zbuf[idx[nearer]] = z[nearer]
        colour[idx[nearer]] = rgb[nearer]
    return colour.reshape(height, width, 3), (zbuf < np.inf).reshape(height, width)


def main():
    out = Path(sys.argv[1])
    if out.exists():
        raise SystemExit(f"{out} exists")
    out.mkdir(parents=True)
    record = json.loads(PL.MANIFEST.read_text())
    review = json.loads((REVIEW / "manifest.json").read_text())
    report = {"inputs": {"runtime_skin_manifest": sha256(PL.MANIFEST), "paw_module": sha256(TPP.__file__),
                         "prototype_module": sha256(S.__file__), "measure": sha256(__file__),
                         "s132_manifest": sha256(REVIEW / "manifest.json")}, "paws": {}}
    if report["inputs"]["paw_module"] != record["third_person"]["paws"]["module_sha256"]:
        raise SystemExit("the paw module is not the one that built the assets")
    for side in ("R", "L"):
        m = PL.rebuild(side, record["third_person"]["paws"]["by_side"])
        verts, tris = m["verts"], np.asarray(m["tris"])
        fr, skel = m["skeleton"]["frame"], m["skeleton"]
        regs = regions(m, verts, tris)
        section = S.CrossSection(verts, fr)
        maps = {"baseline": (np.asarray(m["uvs"]), (None, None)), "round": (S.uv_round(verts, tris, fr), (None, None))}
        uv, info = S.uv_torus(verts, tris, fr, section, tiles=False)
        maps["torus_arc"] = (uv, (None, None))
        uv, info = S.uv_torus(verts, tris, fr, section, tiles=True)
        maps["torus_tiles"] = (uv, (info["u_period_uv"], info["v_period_uv"]))
        periodic_info = {}
        uv, info = S.uv_periodic_loop(verts, tris, fr, section, (2.0, 1.0))
        maps["periodic_harmonic_2x1"] = (uv, (2.0, 1.0))
        periodic_info["periodic_harmonic_2x1"] = info
        for name, periods in (("periodic_arap_1x1", (1.0, 1.0)), ("periodic_arap_2x1", (2.0, 1.0))):
            uv, info = S.uv_periodic_arap(verts, tris, fr, section, periods, 60)
            uv, untangled = S.untangle(verts, tris, uv)
            maps[name] = (uv, periods)
            periodic_info[name] = dict(info, untangle=untangled)
        paw = {"cross_section_length_mm": {"min": round(float(section.length.min() * 1000), 1),
                                           "median": round(float(np.median(section.length) * 1000), 1),
                                           "max": round(float(section.length.max() * 1000), 1)},
               "mappings": {}, "periodic_info": periodic_info}
        for name, (uv, periods) in maps.items():
            paw["mappings"][name] = {"stretch": stretch_report(verts, tris, uv, regs),
                                     "seams": seam_report(verts, tris, uv, periods), "periods_uv": list(periods)}
        # The pad cut: the linear-interpolation cut for the record, then the exact cuts.
        f = S.pad_field(verts, skel)
        lin = S.cut_by_field(verts, tris, f)
        field_fn = lambda q: S.pad_field(q, skel)  # noqa: E731
        variants = {"linear": lin + ({},),
                    "exact_through": S.cut_exact(verts, tris, field_fn, move=False),
                    "exact_move": S.cut_exact(verts, tris, field_fn, move=True)}
        paw["pad_cut_variants"] = {}
        for vname, (vv, tt, ins, par, tss, ff, moved) in variants.items():
            nw = np.arange(len(verts), len(vv))
            occ = np.zeros(len(vv), bool)
            occ[nw] = True
            occ[np.flatnonzero(ff == 0.0)] = True
            segs = np.unique(np.array([(min(tri[k], tri[(k + 1) % 3]), max(tri[k], tri[(k + 1) % 3]))
                                       for tri in tt for k in range(3) if occ[tri[k]] and occ[tri[(k + 1) % 3]]],
                                      np.int64).reshape(-1, 2), axis=0)
            err = contour_distance(segment_samples(vv[segs[:, 0]], vv[segs[:, 1]]), skel) * 1000.0
            qmin, qarea = tri_quality(vv, tt)
            ev = TPP.empty_points(vv, skel)
            nb = np.cross(vv[tt[:, 1]] - vv[tt[:, 0]], vv[tt[:, 2]] - vv[tt[:, 0]])
            ne = np.cross(ev[tt[:, 1]] - ev[tt[:, 0]], ev[tt[:, 2]] - ev[tt[:, 0]])
            paw["pad_cut_variants"][vname] = {
                "contour_error_mm": {f"p{q}": round(float(np.percentile(err, q)), 4) for q in (50, 90, 99, 100)},
                "min_angle_deg": {"min": round(float(qmin.min()), 3), "under_10": int((qmin < 10).sum()), "under_5": int((qmin < 5).sum())},
                "min_area_mm2": round(float(qarea.min() * 1e6), 5), "faces": int(len(tt)), "pad_faces": int(ins.sum()),
                "vertices_moved": len(moved), "move_max_mm": round(max(moved.values()) * 1000, 4) if moved else 0.0,
                "faces_turned_by_morph": int(((nb * ne).sum(1) < 0).sum()), "topology": topology(tt, len(vv))}
        # The candidate cut leaves every vertex where it is (the surface stays the same point set, so the rig's
        # clearance holds as it was): crossings at exact roots, the contour through vertices within SNAP.
        v2, t2, inside, parents, ts, f2, _moved = variants["exact_through"]
        new = np.arange(len(verts), len(v2))
        on_contour = np.concatenate([new, np.flatnonzero(f2 == 0.0)])
        # Cut segments: in each new face, the edge joining two contour vertices.
        seg = []
        oc = np.zeros(len(v2), bool)
        oc[on_contour] = True
        for tri in t2:
            for k in range(3):
                a, b = tri[k], tri[(k + 1) % 3]
                if oc[a] and oc[b] and a < b:
                    seg.append((a, b))
        seg = np.unique(np.array(seg, np.int64).reshape(-1, 2), axis=0)
        cut_err = contour_distance(segment_samples(v2[seg[:, 0]], v2[seg[:, 1]]), skel) * 1000.0
        bkey, _, _ = D.edges_between(tris, np.asarray(m["pad"], bool), ~np.asarray(m["pad"], bool))
        base_err = contour_distance(segment_samples(verts[bkey[:, 0]], verts[bkey[:, 1]]), skel) * 1000.0
        # Areas: the cut's inside faces, the baseline's pad faces, and the field's true area by dense sampling.
        area2 = 0.5 * np.linalg.norm(np.cross(v2[t2[:, 1]] - v2[t2[:, 0]], v2[t2[:, 2]] - v2[t2[:, 0]]), axis=1)
        area0 = 0.5 * np.linalg.norm(np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]]), axis=1)
        bary = [(i / 6, j / 6) for i in range(7) for j in range(7 - i)]
        a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
        frac = np.mean([S.pad_field(a + wb * (b - a) + wc * (c - a), skel) > 0 for wb, wc in bary], 0)
        true_area = float((frac * area0).sum())
        q0_min, q0_area = tri_quality(verts, tris)
        q2_min, q2_area = tri_quality(v2, t2)
        # Morph: the rule at every vertex, faces turned over, and the rule's departure from the edge at new vertices.
        e2 = TPP.empty_points(v2, skel)
        n_b = np.cross(v2[t2[:, 1]] - v2[t2[:, 0]], v2[t2[:, 2]] - v2[t2[:, 0]])
        n_e = np.cross(e2[t2[:, 1]] - e2[t2[:, 0]], e2[t2[:, 2]] - e2[t2[:, 0]])
        turned = int(((n_b * n_e).sum(1) < 0).sum())
        lerp_e = e2[parents[:, 0]] * (1 - ts)[:, None] + e2[parents[:, 1]] * ts[:, None]
        coat_rule = TPP.digit_weight(v2[new], skel, TPP.COAT_RAMP) * TPP.ease(*TPP.COAT_TURN, TPP.turn_of(v2[new], fr))
        coat_v = TPP.digit_weight(verts, skel, TPP.COAT_RAMP) * TPP.ease(*TPP.COAT_TURN, TPP.turn_of(verts, fr))
        coat_lerp = coat_v[parents[:, 0]] * (1 - ts) + coat_v[parents[:, 1]] * ts
        paw["pad_cut"] = {
            "faces": {"baseline": int(len(tris)), "cut": int(len(t2)), "new_vertices": int(len(new)),
                      "snapped_vertices": int((f2 == 0.0).sum())},
            "pad_faces": {"baseline": int(np.asarray(m["pad"]).sum()), "cut": int(inside.sum())},
            "pad_area_cm2": {"baseline": round(float(area0[np.asarray(m["pad"], bool)].sum() * 1e4), 3),
                             "cut": round(float(area2[inside].sum() * 1e4), 3), "true": round(true_area * 1e4, 3)},
            "contour_error_mm": {"cut": {f"p{q}": round(float(np.percentile(cut_err, q)), 4) for q in (50, 90, 99, 100)},
                                 "baseline_staircase": {f"p{q}": round(float(np.percentile(base_err, q)), 4) for q in (50, 90, 99, 100)}},
            "outline_mm": {"cut": round(float(np.linalg.norm(v2[seg[:, 0]] - v2[seg[:, 1]], axis=1).sum() * 1000), 1),
                           "baseline": round(float(np.linalg.norm(verts[bkey[:, 0]] - verts[bkey[:, 1]], axis=1).sum() * 1000), 1)},
            "min_angle_deg": {"baseline": {"min": round(float(q0_min.min()), 3), "under_10": int((q0_min < 10).sum()), "under_5": int((q0_min < 5).sum())},
                              "cut": {"min": round(float(q2_min.min()), 3), "under_10": int((q2_min < 10).sum()), "under_5": int((q2_min < 5).sum())}},
            "min_area_mm2": {"baseline": round(float(q0_area.min() * 1e6), 5), "cut": round(float(q2_area.min() * 1e6), 5)},
            "topology": {"baseline": topology(tris, len(verts)), "cut": topology(t2, len(v2))},
            "morph": {"faces_turned_over": turned,
                      "rule_off_edge_mm": {"p50": round(float(np.median(np.linalg.norm(e2[new] - lerp_e, axis=1)) * 1000), 4),
                                           "max": round(float(np.linalg.norm(e2[new] - lerp_e, axis=1).max() * 1000), 4)}},
            "coat_rule_vs_interpolation_max": round(float(np.abs(coat_rule - coat_lerp).max()), 5),
            "weights": "every paw vertex is weighted 1.0 to its hand (LOD0's FBX), so the new ones are too"}
        # The periodic maps on the cut mesh: stretch, flips and seams again (regions by geometry; the cut's coat is
        # not tabulated per face, so its back is left out).
        regs_cut = regions(dict(m, coat=np.zeros((len(t2), 3))), v2, t2)
        uv_cut, info = S.uv_periodic_arap(v2, t2, fr, section, (2.0, 1.0), 60)
        uv_cut, untangled = S.untangle(v2, t2, uv_cut)
        paw["pad_cut"]["periodic_arap_2x1_on_cut"] = {"stretch": stretch_report(v2, t2, uv_cut, regs_cut),
                                                      "seams": seam_report(v2, t2, uv_cut, (2.0, 1.0)),
                                                      "info": dict(info, untangle=untangled)}
        paw["pad_cut"]["chosen_mapping"] = "periodic_arap_2x1"
        report["paws"][side] = paw
        if side == "R":
            for view in VIEWS:
                row = review["shots"][view]
                pose, state = row["shot"]["pose"], row["shot"]["state"]
                width, height = (x // 4 for x in review["resolution"])
                panels = []
                with Image.open(REVIEW / f"{view}.png") as im:
                    original = np.asarray(im.convert("RGB").resize((width, height), Image.LANCZOS))
                box = None
                for name, mesh_v, mesh_t, uv, pad in (("baseline", verts, tris, maps["baseline"][0], np.asarray(m["pad"], bool)),
                                                      ("torus_tiles", verts, tris, maps["torus_tiles"][0], np.asarray(m["pad"], bool)),
                                                      ("chosen periodic map + cut", v2, t2, uv_cut, inside)):
                    shape = TPP.empty_points(mesh_v, skel) if state == "empty" else mesh_v
                    pts = D.posed_ue(dict(m, verts=shape), side, record, pose)
                    img, mask = checker_render(pts, mesh_t, uv, pad, row["camera"], width, height)
                    if box is None:
                        ys, xs = np.nonzero(mask)
                        box = (max(0, xs.min() - 20), max(0, ys.min() - 20), min(width, xs.max() + 20), min(height, ys.max() + 20))
                    panels.append(img[box[1]:box[3], box[0]:box[2]])
                strip = np.concatenate([original[box[1]:box[3], box[0]:box[2]]] + panels, 1)
                Image.fromarray(strip.astype(np.uint8)).save(out / f"{view}_checker.png")
    report["renders"] = {p.name: sha256(p) for p in sorted(out.glob("*.png"))}
    (out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    summary = {side: {"stretch_all_anisotropy_p90": {k: v["stretch"]["all"]["anisotropy"]["p90"] for k, v in p["mappings"].items()},
                      "visible_seam_mm": {k: v["seams"]["visible_seam_length_mm"] for k, v in p["mappings"].items()},
                      "flipped": {k: v["stretch"]["flipped_faces"] for k, v in p["mappings"].items()},
                      "contour_error_p99_mm": {k: v["p99"] for k, v in p["pad_cut"]["contour_error_mm"].items()},
                      "min_angle": p["pad_cut"]["min_angle_deg"], "turned": p["pad_cut"]["morph"]["faces_turned_over"]}
               for side, p in report["paws"].items()}
    print("PAW_SURFACE_PROTOTYPES " + json.dumps(summary))


if __name__ == "__main__":
    main()
