"""The r4 candidate's paws, on the CPU: each paw's skin cut along the pads' smooth contour, with the seamless periodic
UV map, coat by rule, pads by the cut, and new UVs for the built fur strands at their roots.

Root's 21:53 UTC entry (2026-10-26) allows a separate candidate once the prototype's topology, morph/weight, foldover
and stretch checks justify it. The prototype is nyaakoto_tp_paw_surface, measured by
measure_paw_surface_prototypes.py (the v6 report). This script writes what assemble_nyaakoto_r4_paws.py (Blender)
needs to swap only the paw skins in an in-memory copy of the runtime blend.

**Each paw is rebuilt as built** (plan_nyaakoto_tp_review.rebuild, checked against the record's counts):
- **The cut:** cut_exact(move=False) along pad_field.
  - Every baseline vertex stays where it is.
  - New vertices sit on baseline edges at the field's roots.
  - Each cut face records the baseline face it lies in.
- **UVs:** uv_periodic_arap at 2x1 whole tiles (60 iterations), then untangle. They are shifted by whole periods to sit
  near the origin. The fur maps tile exactly, so a whole-period shift changes nothing drawn.
- **Coat:** the coat rule (digit weight times the turn's ease) at every vertex. At baseline vertices it must equal
  mesh_paw's own.
- **Pads:** the cut's inside faces are M_Hero_RoseNose; the rest are M_Hero_GreyTabbyFur.
- **The empty fist:** empty_points at every vertex. Blender uses it at the new ones; the baseline's keys stay as built.
- **The strands** (nyaakoto_tp_fur.grow at LOD0's density, as built):
  - Their draws are replayed to recover each strand's root face and barycentric position. The replay is checked equal
    to strands()'s own vertices, and the old UVs to grow's.
  - Each root is located in its face's cut piece, and its UV is interpolated there.
  - Their coat and normals stay as built.

**Checks recorded** (record.json), each beside the baseline's where it has one:
- the cut's topology, faces, slivers, pad area against the field's true area, and contour error;
- the faces whose pad flag disagrees with the field at their centroid;
- UV flips after untangling, stretch, and seams;
- the coat at baseline vertices, and the rule against interpolation at the new ones;
- the faces the empty fist turns over;
- the strands' replay and location, and their roots on pads.

**The contour error** is reported two ways:
- |f|, the field's margin (in metres, like a distance);
- |f| / |grad f|, the first-order distance. It breaks down where the gradient nearly vanishes, so the gradient's
  smallest value along the cut is reported with it.

Writes <out>/paw_R.npz, paw_L.npz and record.json, in a new folder.

Run (host: /usr/bin/python3 has numpy and scipy):
  /usr/bin/python3 scripts/art/prepare_nyaakoto_r4_paws.py Saved/NyaakotoThirdPerson/Candidates/r4/<new folder>
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
import measure_paw_surface_prototypes as MS  # noqa: E402
import nyaakoto_tp_fur as TPF  # noqa: E402
import nyaakoto_tp_paw_surface as S  # noqa: E402
import nyaakoto_tp_paws as TPP  # noqa: E402
import plan_nyaakoto_tp_review as PL  # noqa: E402

PERIODS = (2.0, 1.0)
ITERATIONS = 60
LOCATE_TOL = 1e-9          # a root's smallest barycentric coordinate in its cut piece may be this far below zero
FUR_SLOT, PAD_SLOT = "M_Hero_GreyTabbyFur", "M_Hero_RoseNose"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def face_parents(tris, f):
    """Per cut face, the baseline face it lies in. cut_by_field emits each baseline face's pieces in order: one if the
    contour misses the face, two if it runs through one of its vertices, three otherwise."""
    sg = np.sign(f)[tris]
    whole = (sg >= 0).all(1) | (sg <= 0).all(1)
    through = (sg == 0).sum(1) == 1
    return np.repeat(np.arange(len(tris)), np.where(whole, 1, np.where(through, 2, 3)))


def replay_strands(m, cfg, seed, density_share=1.0):
    """nyaakoto_tp_fur.strands, draw for draw, keeping each kept strand's face and barycentric root:
    (strand vertices (3 per strand), faces, barycentric coordinates (S, 3))."""
    verts, tris, skel = m["verts"], np.asarray(m["tris"]), m["skeleton"]
    rng = np.random.default_rng(seed)
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    cross = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(cross, axis=1)
    count = int(round(area.sum() * 1e4 * cfg["density_per_cm2"] * density_share))
    pick = rng.choice(len(tris), size=count, p=area / area.sum())
    u, v = rng.random(count), rng.random(count)
    flip = u + v > 1.0
    u, v = np.where(flip, 1.0 - u, u), np.where(flip, 1.0 - v, v)
    n = TPF._unit(cross[pick])
    root = a[pick] + (b[pick] - a[pick]) * u[:, None] + (c[pick] - a[pick]) * v[:, None] + cfg["root_lift_m"] * n
    d = TPF.flow(root, n, skel)
    lift = np.radians(rng.uniform(*cfg["lift_deg"], count))
    growth = TPF._unit(np.cos(lift)[:, None] * d + np.sin(lift)[:, None] * n)
    length = rng.uniform(*cfg["length_m"], count)
    half = 0.5 * rng.uniform(*cfg["root_width_m"], count)
    side = TPF._unit(np.cross(n, growth))
    tip = root + length[:, None] * growth
    fr = skel["frame"]
    keep = ((TPP.channel_sdf(root, fr) > cfg["clear_m"]) & (TPP.channel_sdf(tip, fr) > cfg["tip_clear_m"])
            & (TPP.paw_sdf(tip, skel) > TPP.FUZZ_MAX + TPF.TIP_ABOVE_FUZZ_M)
            & (np.abs((tip - fr["c"]) @ TPP.Y) < TPP.PAW_HALF - 0.0003))
    root, tip, side, half = root[keep], tip[keep], side[keep], half[keep]
    sv = np.stack([root + half[:, None] * side, root - half[:, None] * side, tip], 1).reshape(-1, 3)
    bary = np.stack([1.0 - u - v, u, v], 1)[keep]
    return sv, pick[keep], bary


def strand_roots(m):
    """The built strands (grow at LOD0's density) with their baseline faces and barycentric roots, and grow's own UVs
    and coat for them. Raises if the replay is not grow's."""
    coats = (TPF.STRANDS, TPF.GUARD)
    replays = [replay_strands(m, cfg, 11 + k, TPF.LOD_DENSITY[0]) for k, cfg in enumerate(coats)]
    for k, cfg in enumerate(coats):
        own = TPF.strands(m["verts"], m["tris"], m["uvs"], m["coat"], m["skeleton"], TPF.LOD_DENSITY[0], 11 + k, cfg)[0]
        if not np.array_equal(own, replays[k][0]):
            raise SystemExit(f"the strand replay ({['STRANDS', 'GUARD'][k]}) is not nyaakoto_tp_fur.strands")
    pre_v = np.concatenate([r[0] for r in replays]).reshape(-1, 9)
    pre_face = np.concatenate([r[1] for r in replays])
    pre_bary = np.concatenate([r[2] for r in replays])
    grown = dict(m)
    sv, st, suv, scoat, pruned = TPF.grow(grown, TPF.LOD_DENSITY[0])
    index = {row.tobytes(): k for k, row in enumerate(pre_v)}
    keep = np.array([index[row.tobytes()] for row in sv.reshape(-1, 9)], np.int64)
    if len(keep) and (np.diff(keep) <= 0).any():
        raise SystemExit("grow's strands are not an ordered subset of the replay")
    if len(keep) != len(pre_v) - pruned:
        raise SystemExit(f"grow pruned {pruned}, the replay accounts for {len(pre_v) - len(keep)}")
    face, bary = pre_face[keep], pre_bary[keep]
    old_uv = (m["uvs"][face] * bary[:, :, None]).sum(1)
    if not np.allclose(old_uv, suv[:, 0], rtol=0.0, atol=1e-12):
        raise SystemExit("the replayed roots do not give grow's UVs")
    return {"verts": sv, "face": face, "bary": bary, "uv_built": suv[:, 0], "coat_built": scoat[:, 0],
            "pruned": int(pruned), "normals": grown["strand_normals"]}


def barycentric(p, tri):
    """Barycentric coordinates of points p (k, 3) in triangles tri (k, 3, 3), in each triangle's plane."""
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
    d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    return np.stack([1.0 - v - w, v, w], 1)


def locate(roots, face, verts, tris, cut_verts, cut_tris, parent):
    """Each root (in baseline face `face`) in the cut piece of that face that holds it: (cut faces, barycentric
    coordinates there, the smallest coordinate)."""
    order = np.argsort(parent, kind="stable")
    first = np.searchsorted(parent[order], np.arange(len(tris)))
    count = np.bincount(parent, minlength=len(tris))
    best_f = np.full(len(roots), -1, np.int64)
    best_b = np.zeros((len(roots), 3))
    best_min = np.full(len(roots), -np.inf)
    for k in range(3):
        has = count[face] > k
        cand = np.where(has, order[np.minimum(first[face] + k, len(order) - 1)], 0)
        b = barycentric(roots, cut_verts[cut_tris[cand]])
        mn = np.where(has, b.min(1), -np.inf)
        better = mn > best_min
        best_f[better], best_b[better], best_min[better] = cand[better], b[better], mn[better]
    return best_f, best_b, best_min


def contour_report(v2, t2, f2, n, skel, h=1e-4):
    """|f| and the first-order distance along the cut's segments (mm), and the gradient's smallest norm there."""
    on = np.zeros(len(v2), bool)
    on[n:] = True
    on[np.flatnonzero(f2 == 0.0)] = True
    e = np.concatenate([t2[:, [0, 1]], t2[:, [1, 2]], t2[:, [2, 0]]])
    seg = np.unique(np.sort(e[on[e[:, 0]] & on[e[:, 1]]], 1), axis=0)
    pts = MS.segment_samples(v2[seg[:, 0]], v2[seg[:, 1]])
    f = S.pad_field(pts, skel)
    g = np.stack([(S.pad_field(pts + h * np.eye(3)[i], skel) - S.pad_field(pts - h * np.eye(3)[i], skel)) / (2 * h)
                  for i in range(3)], 1)
    gn = np.linalg.norm(g, axis=1)
    pct = lambda x: {f"p{q}": round(float(np.percentile(x, q)), 4) for q in (50, 90, 99, 100)}  # noqa: E731
    return {"segments": int(len(seg)), "outline_mm": round(float(np.linalg.norm(v2[seg[:, 0]] - v2[seg[:, 1]], axis=1).sum() * 1000), 1),
            "margin_mm": pct(np.abs(f) * 1000.0), "first_order_mm": pct(np.abs(f) / np.maximum(gn, 1e-9) * 1000.0),
            "gradient_norm": {"min": round(float(gn.min()), 5), "p1": round(float(np.percentile(gn, 1)), 5),
                              "p50": round(float(np.median(gn)), 5)}}


def paw(side, record):
    m = PL.rebuild(side, record["third_person"]["paws"]["by_side"])
    verts, tris = m["verts"], np.asarray(m["tris"])
    n = len(verts)
    fr, skel = m["skeleton"]["frame"], m["skeleton"]
    field = lambda q: S.pad_field(q, skel)  # noqa: E731
    v2, t2, inside, parents, ts, f2, moved = S.cut_exact(verts, tris, field, move=False)
    if not np.array_equal(v2[:n], verts):
        raise SystemExit("the cut moved a baseline vertex")
    parent = face_parents(tris, f2)
    if len(parent) != len(t2):
        raise SystemExit(f"{len(parent)} parent faces for {len(t2)} cut faces")
    new_at = verts[parents[:, 0]] + (verts[parents[:, 1]] - verts[parents[:, 0]]) * ts[:, None]
    if not np.array_equal(new_at, v2[n:]):
        raise SystemExit("a new vertex is not at its edge's parameter")
    # Every cut face lies in its parent: its corners are the parent's vertices or new vertices on the parent's edges.
    pv = [set(map(int, t)) for t in tris[parent]]
    for f, tri in enumerate(t2):
        for x in map(int, tri):
            if x < n and x not in pv[f]:
                raise SystemExit(f"cut face {f} has vertex {x}, not one of its parent's")
            if x >= n and not {int(parents[x - n, 0]), int(parents[x - n, 1])} <= pv[f]:
                raise SystemExit(f"cut face {f}'s new vertex {x} is not on its parent's edge")
    # UVs on the cut skin: the periodic ARAP map, untangled, shifted by whole periods toward the origin.
    section = S.CrossSection(verts, fr)
    uv, info = S.uv_periodic_arap(v2, t2, fr, section, PERIODS, ITERATIONS)
    uv, untangled = S.untangle(v2, t2, uv)
    if untangled["folded_after"] or untangled["skipped"]:
        raise SystemExit(f"{side}: untangle left {len(untangled['folded_after'])} folded faces, skipped {untangled['skipped']}")
    shift = -np.round(uv.reshape(-1, 2).mean(0) / np.array(PERIODS)) * np.array(PERIODS)
    uv = uv + shift
    # Coat by rule at every vertex; at baseline vertices, mesh_paw's own.
    coat = TPP.digit_weight(v2, skel, TPP.COAT_RAMP) * TPP.ease(*TPP.COAT_TURN, TPP.turn_of(v2, fr))
    coat_base = np.asarray(m["coat"])
    coat_err = float(np.abs(coat[tris] - coat_base).max())
    coat_lerp = coat[parents[:, 0]] * (1.0 - ts) + coat[parents[:, 1]] * ts
    # The empty fist at every vertex; the faces it turns over.
    empty = TPP.empty_points(v2, skel)
    nb = np.cross(v2[t2[:, 1]] - v2[t2[:, 0]], v2[t2[:, 2]] - v2[t2[:, 0]])
    ne = np.cross(empty[t2[:, 1]] - empty[t2[:, 0]], empty[t2[:, 2]] - empty[t2[:, 0]])
    lerp_e = empty[parents[:, 0]] * (1.0 - ts)[:, None] + empty[parents[:, 1]] * ts[:, None]
    # Pad flags against the field at each face's centroid.
    fc = field(v2[t2].mean(1))
    disagree = (fc > 0) != inside
    # Strands: the built ones, located in the cut.
    sr = strand_roots(m)
    roots = (verts[tris[sr["face"]]] * sr["bary"][:, :, None]).sum(1)
    sf, sb, smin_b = locate(roots, sr["face"], verts, tris, v2, t2, parent)
    if (smin_b < -LOCATE_TOL).any():
        raise SystemExit(f"{side}: {int((smin_b < -LOCATE_TOL).sum())} strand roots lie in no cut piece of their face")
    strand_uv = (uv[sf] * sb[:, :, None]).sum(1)
    strand_coat_new = (coat[t2[sf]] * sb).sum(1)
    # Quality and topology, beside the baseline's.
    q0, a0 = MS.tri_quality(verts, tris)
    q2, a2 = MS.tri_quality(v2, t2)
    untouched = np.bincount(parent, minlength=len(tris))[parent] == 1
    regs = MS.regions(dict(m, coat=coat[t2]), v2, t2)
    area0 = 0.5 * np.linalg.norm(np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]]), axis=1)
    bary7 = [(i / 6, j / 6) for i in range(7) for j in range(7 - i)]
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    true_area = float((np.mean([field(a + wb * (b - a) + wc * (c - a)) > 0 for wb, wc in bary7], 0) * area0).sum())
    row = {
        "baseline": {"vertices": n, "triangles": int(len(tris)), "pad_faces": int(np.asarray(m["pad"]).sum()),
                     "pad_area_cm2": round(float(area0[np.asarray(m["pad"], bool)].sum() * 1e4), 3)},
        "cut": {"vertices": int(len(v2)), "triangles": int(len(t2)), "new_vertices": int(len(v2) - n),
                "through_vertices": int((f2[:n] == 0.0).sum()), "vertices_moved": 0,
                "through_vertex_off_root_mm_max": round(max(moved.values()) * 1000, 4) if moved else 0.0,
                "pad_faces": int(inside.sum()),
                "pad_area_cm2": round(float(a2[inside].sum() * 1e4), 3), "true_pad_area_cm2": round(true_area * 1e4, 3),
                "topology": MS.topology(t2, len(v2)), "baseline_topology": MS.topology(tris, n),
                "contour": contour_report(v2, t2, f2, n, skel),
                "pad_flag_vs_centroid": {"faces": int(disagree.sum()),
                                         "max_margin_mm": round(float(np.abs(fc[disagree]).max() * 1000), 4) if disagree.any() else 0.0}},
        "slivers": {"min_angle_deg": round(float(q2.min()), 3),
                    "under_5": int((q2 < 5).sum()), "under_5_untouched_baseline_faces": int(((q2 < 5) & untouched).sum()),
                    "from_5_to_10": int(((q2 >= 5) & (q2 < 10)).sum()),
                    "baseline_under_5": int((q0 < 5).sum()), "baseline_from_5_to_10": int(((q0 >= 5) & (q0 < 10)).sum()),
                    "min_area_mm2": round(float(a2.min() * 1e6), 5), "baseline_min_area_mm2": round(float(a0.min() * 1e6), 5)},
        "uv": {"periods": list(PERIODS), "info": info, "untangle": {"folded_before": len(untangled["folded_before"]),
                                                                    "rings": untangled["rings"], "skipped": untangled["skipped"],
                                                                    "folded_after": len(untangled["folded_after"])},
               "shift_uv": shift.tolist(), "range_uv": {"min": uv.reshape(-1, 2).min(0).round(4).tolist(),
                                                        "max": uv.reshape(-1, 2).max(0).round(4).tolist()},
               "stretch": MS.stretch_report(v2, t2, uv, regs), "seams": MS.seam_report(v2, t2, uv, PERIODS),
               "baseline_stretch": MS.stretch_report(verts, tris, np.asarray(m["uvs"]), MS.regions(m, verts, tris)),
               "baseline_seams": MS.seam_report(verts, tris, np.asarray(m["uvs"]), (None, None))},
        "coat": {"rule_vs_built_at_baseline_vertices_max": coat_err,
                 "rule_vs_interpolation_at_new_vertices_max": round(float(np.abs(coat[n:] - coat_lerp).max()), 5)},
        "empty_fist": {"faces_turned_over": int(((nb * ne).sum(1) < 0).sum()),
                       "rule_off_edge_mm_max": round(float(np.linalg.norm(empty[n:] - lerp_e, axis=1).max() * 1000), 4)},
        "weights": "every paw vertex is weighted 1.0 to its hand alone (LOD0's runtime blend, s135); the new ones are too",
        "strands": {"count": int(len(sr["face"])), "pruned_by_grow": sr["pruned"], "replay": "equal to strands() and grow()",
                    "located_min_barycentric": float(smin_b.min()), "roots_on_pads": int(inside[sf].sum()),
                    "coat_built_vs_new_skin_max": round(float(np.abs(sr["coat_built"] - strand_coat_new).max()), 5)},
        "slots": {"fur": FUR_SLOT, "pad": PAD_SLOT},
    }
    if coat_err > 1e-12:
        raise SystemExit(f"{side}: the coat rule is {coat_err} from mesh_paw's at baseline vertices")
    if row["empty_fist"]["faces_turned_over"]:
        raise SystemExit(f"{side}: the empty fist turns {row['empty_fist']['faces_turned_over']} faces over")
    if row["cut"]["topology"]["edges_not_shared_by_two"] or not row["cut"]["topology"]["every_edge_has_its_opposite"] \
            or row["cut"]["topology"]["euler"] != row["cut"]["baseline_topology"]["euler"]:
        raise SystemExit(f"{side}: the cut's topology {row['cut']['topology']}")
    if row["uv"]["stretch"]["flipped_faces"]:
        raise SystemExit(f"{side}: {row['uv']['stretch']['flipped_faces']} UV faces flipped")
    if row["uv"]["seams"]["visible_seam_edges"]:
        raise SystemExit(f"{side}: {row['uv']['seams']['visible_seam_edges']} visible seam edges")
    arrays = {"skin_verts": verts, "skin_tris": tris.astype(np.int64), "cut_verts": v2, "cut_tris": t2.astype(np.int64),
              "cut_parent": parent.astype(np.int64), "new_parents": parents.astype(np.int64), "new_t": ts,
              "pad": inside.astype(bool), "uv": uv, "coat": coat, "empty": empty,
              "strand_verts": sr["verts"], "strand_uv": strand_uv, "strand_uv_built": sr["uv_built"],
              "strand_coat_built": sr["coat_built"]}
    return row, arrays


def main():
    out = (ROOT / sys.argv[1]).resolve() if not Path(sys.argv[1]).is_absolute() else Path(sys.argv[1])
    if out.exists():
        raise SystemExit(f"{out} exists")
    record = json.loads(PL.MANIFEST.read_text())
    if sha256(TPP.__file__) != record["third_person"]["paws"]["module_sha256"]:
        raise SystemExit("the paw module is not the one that built the assets")
    out.mkdir(parents=True)
    report = {"inputs": {"runtime_skin_manifest": sha256(PL.MANIFEST),
                         "runtime_blend_sha256": record["runtime_blend_sha256"],
                         "skeletal_fbx_sha256": record["skeletal_fbx_sha256"],
                         "scripts/art/nyaakoto_tp_paws.py": sha256(TPP.__file__),
                         "scripts/art/nyaakoto_tp_fur.py": sha256(TPF.__file__),
                         "scripts/art/nyaakoto_tp_paw_surface.py": sha256(S.__file__),
                         "scripts/art/measure_paw_surface_prototypes.py": sha256(MS.__file__),
                         "scripts/art/prepare_nyaakoto_r4_paws.py": sha256(__file__)},
              "periods": list(PERIODS), "iterations": ITERATIONS, "paws": {}, "files": {}}
    for side in ("R", "L"):
        row, arrays = paw(side, record)
        path = out / f"paw_{side}.npz"
        np.savez(path, **arrays)
        report["paws"][side] = row
        report["files"][path.name] = sha256(path)
    (out / "record.json").write_text(json.dumps(report, indent=1) + "\n")
    print("NYAAKOTO_R4_PAWS_PREPARED " + json.dumps({side: {"faces": r["cut"]["triangles"], "new": r["cut"]["new_vertices"],
                                                           "pads": r["cut"]["pad_faces"], "slivers_5_10": r["slivers"]["from_5_to_10"],
                                                           "under_5": r["slivers"]["under_5"], "strands": r["strands"]["count"],
                                                           "folded": r["uv"]["untangle"]["folded_after"],
                                                           "margin_p100_mm": r["cut"]["contour"]["margin_mm"]["p100"]}
                                                    for side, r in report["paws"].items()}))


if __name__ == "__main__":
    main()
