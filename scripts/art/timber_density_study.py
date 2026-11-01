#!/usr/bin/env python3
"""Measure the dojo timber logs' triangles, relief and check topology, without Blender.

  python3 scripts/art/timber_density_study.py [--json OUT] [--quick]

Read-only research for docs/art-direction/DOJO_TIMBER_RELIEF_PROPOSAL.md.
It rebuilds members with scripts/art/sora_timber_lib.py (numpy only). It
writes nothing in the kit and changes no generator input, so the frozen
slice stays as built.

1. **Reproduce.** The column and rail recipes are copied from their
   generators, with constants read from the generator sources. They are
   rebuilt, and their triangle counts checked against the committed
   manifests: each side triangle pair is one sample, so triangles = 2 x
   samples.
2. **Relief.** On a built mesh's room face it measures how far each
   triangle tilts from the face, separately for plain planed surface,
   checks, knots and dents. It converts the tilt to the shading change it
   makes under raking light, dI/I ~ tilt x cot(grazing angle).
3. **Check topology.** For each check, the number of samples across it, row
   by row. Wherever that count changes, the ladder stitch skews triangles
   across the check, which shows as the fallback's stair-step.
4. **Budget.** A feature-adaptive sampling counts its samples for the same
   members:
   - sparse rows and columns on plain faces;
   - fine rows and columns only around checks, knots, dents and arrises;
   - the base grid kept out of every check's zone, so the count across a
     check stays constant.
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import sora_timber_lib as T  # noqa: E402

KIT = ROOT / "Content/SourceArt/Environment/NyaagyuDojoTimbers"


def constants(path: Path, names):
    """Literal module constants of a generator, read from its source (it needs Blender to import)."""
    tree = ast.parse(path.read_text())
    env = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            try:
                env[name] = eval(compile(ast.Expression(node.value), str(path), "eval"), {}, dict(env))  # noqa: S307
            except Exception:  # noqa: BLE001 - constants that need Blender modules are skipped
                pass
    missing = [n for n in names if n not in env]
    if missing:
        raise SystemExit(f"{path.name}: constants {missing} not found")
    return {n: env[n] for n in names}


C = constants(HERE / "create_nyaagyu_dojo_timbers.py", ("COL", "WALL_H", "COL_CENTRE_Y", "SIDE_VISIBLE", "SPACING"))
R = constants(HERE / "create_nyaagyu_dojo_rails.py", ("SLAB0", "SPACING", "RAILS"))


def column_member(seed: int, kind: str, name: str) -> T.Member:
    """create_nyaagyu_dojo_timbers.column_member, copied (checked by the triangle counts)."""
    COL, WALL_H, SIDE_VISIBLE = C["COL"], C["WALL_H"], C["SIDE_VISIBLE"]
    rng = np.random.default_rng(seed)
    front_u = (-0.07, 0.07)
    if kind == "wall":
        check_faces = (3,)
        check_u = {3: front_u}
        finish = ("planed", "hidden", "planed", "planed")
        vis = ((-COL / 2, -COL / 2 + SIDE_VISIBLE), None, (COL / 2 - SIDE_VISIBLE, COL / 2), None)
        wear = (0.0, 0.0, rng.uniform(0.003, 0.007), rng.uniform(0.003, 0.007))
    else:
        check_faces = (3, 0, 2, 1)
        check_u = {f: front_u for f in range(4)}
        finish = ("planed",) * 4
        vis = (None,) * 4
        wear = tuple(rng.uniform(0.002, 0.007) for _ in range(4))
    log = T.make_log(seed, WALL_H, cut="boxed_heart", width=COL, depth=COL, ring_width=rng.uniform(0.0015, 0.0024),
                     knot_count=(3, 8), check_count=(2, 5), check_faces=check_faces, check_u=check_u,
                     check_length=(0.4, 2.4), check_cover=(0.9, 1.9))
    return T.Member(name=name, length=WALL_H, width=COL, depth=COL, log=log, finish=finish, visible=vis,
                    arris_r=(0.0025,) * 4, arris_wear=wear, handling=(rng.uniform(1.05, 1.3), 0.5),
                    dents=int(rng.integers(16, 34)), dent_zone=(0.35, 2.0), bow=rng.uniform(0.0006, 0.0018),
                    spacing=C["SPACING"], seed=seed, offset=(0.0, C["COL_CENTRE_Y"], 0.0))


def rail_member(seed: int, kind: str, name: str, length: float) -> T.Member:
    """create_nyaagyu_dojo_rails.rail_member, copied (checked by the triangle counts)."""
    z0, z1, face_y, full, cut, knots, checks, wear = R["RAILS"][kind]
    height, depth = z1 - z0, R["SLAB0"] - face_y
    rng = np.random.default_rng(seed)
    log = T.make_log(seed, length, cut=cut, width=height, depth=depth, ring_width=rng.uniform(0.0014, 0.0022),
                     knot_count=knots, knot_size=(0.002, 0.005), check_count=checks, check_faces=(3,),
                     check_u={3: (-height * 0.3, height * 0.3)}, check_width=(0.0003, 0.0009),
                     check_depth=(0.002, 0.010), check_length=(0.08, 0.5))
    return T.Member(name=name, length=length, width=height, depth=depth, log=log,
                    finish=("planed", "hidden", "planed", "planed"), arris_r=(0.0018,) * 4,
                    arris_wear=(0.0, 0.0, wear, 0.0), handling=(length / 2, length * 2), dents=int(rng.integers(2, 8)),
                    dent_zone=(0.1, max(0.11, length - 0.1)), bow=rng.uniform(0.0003, 0.0010), soot_from=0.0,
                    spacing=R["SPACING"], seed=seed)


# ---------------------------------------------------------------------------
# 2. Relief: triangle tilt on the room face, by feature
# ---------------------------------------------------------------------------

def relief(m: T.Member, grazing_deg=(10.0, 30.0)):
    B = T.build_member(m)
    S, P, tris = B["samples"], B["verts"], B["tris"]
    face = 3                                    # -Y, the room face
    on = (S.seg == 2 * face) & (S.detail > 0)
    sel = on[tris].all(1)
    t = tris[sel]
    n = np.cross(P[t[:, 1]] - P[t[:, 0]], P[t[:, 2]] - P[t[:, 0]])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-30
    tilt = np.degrees(np.arccos(np.clip(np.abs(n @ np.array([0.0, -1.0, 0.0])), 0.0, 1.0)))
    colors = B["colors"]
    face_detail = (S.seg % 2 == 0) & (S.detail > 0)
    dents = np.abs(T._dents(m, S, face_detail)) > 2e-6
    cls_v = np.where(colors[:, 0] > 0.01, "check", np.where(colors[:, 3] > 0.01, "knot", np.where(dents, "dent", "plain")))
    # A triangle takes its most specific vertex class.
    rank = {"plain": 0, "dent": 1, "knot": 2, "check": 3}
    names = np.array(["plain", "dent", "knot", "check"])
    r = np.vectorize(rank.get)(cls_v)[t].max(1)
    out = {}
    for k, name in enumerate(names):
        a = tilt[r == k]
        if a.size == 0:
            continue
        row = {"triangles": int(a.size)}
        for p in (50, 95, 99):
            row[f"tilt_p{p}_deg"] = round(float(np.percentile(a, p)), 4)
        row["tilt_max_deg"] = round(float(a.max()), 3)
        for g in grazing_deg:
            # Lambert: I ~ sin(g + tilt) -> dI/I ~ tilt * cot(g) for small tilt.
            row[f"shading_p95_at_{int(g)}deg_pct"] = round(100.0 * math.radians(row["tilt_p95_deg"]) / math.tan(math.radians(g)), 2)
        out[str(name)] = row
    return out, B


# ---------------------------------------------------------------------------
# 3. Check topology: samples across a check, row by row
# ---------------------------------------------------------------------------

def check_topology(m: T.Member, S: T.Samples):
    out = []
    for i, ck in enumerate(m.log.checks):
        f = ck.face
        if m.finish[f] == "hidden":
            continue
        counts = []
        for st, ct in zip(S.row_start, S.row_count):
            z = S.z[st]
            if not (ck.z0 <= z <= ck.z1):
                continue
            seg = S.seg[st:st + ct]
            u = S.u[st:st + ct][seg == 2 * f]
            uc, wz, _ = T._check_at(ck, z, straight=m.fallback)
            zone = max(wz / 2, 0.00012) * 1.6 + 0.0028 + m.spacing
            counts.append(int(np.sum(np.abs(u - uc) < zone)))
        if len(counts) < 2:
            continue
        c = np.array(counts)
        changes = int(np.sum(np.diff(c) != 0))
        out.append({"check": i, "face": f, "rows": int(c.size), "count_min": int(c.min()), "count_max": int(c.max()),
                    "row_to_row_changes": changes, "change_rate": round(changes / max(1, c.size - 1), 3)})
    return out


# ---------------------------------------------------------------------------
# 4. Budget: a feature-adaptive sampling (counts only)
# ---------------------------------------------------------------------------

def dent_sites(m: T.Member):
    """Dents placed in (face, u, z) independently of the sampling: bokken strikes
    crush a short line across the grain, so they are long across u and short
    along z."""
    rng = np.random.default_rng(m.seed * 977 + 3)
    half_w, half_d = m.width / 2, m.depth / 2
    faces = []
    for f in range(4):
        if m.finish[f] == "hidden":
            continue
        half = half_d if f % 2 == 0 else half_w
        lo, hi = m.visible[f] if m.visible[f] is not None else (-half, half)
        faces.append((f, lo, hi, hi - lo))
    w = np.array([x[3] for x in faces])
    sites = []
    for _ in range(m.dents):
        f, lo, hi, _ = faces[int(rng.choice(len(faces), p=w / w.sum()))]
        u = float(rng.uniform(lo, hi))
        z = float(np.clip(rng.normal((m.dent_zone[0] + m.dent_zone[1]) / 2, (m.dent_zone[1] - m.dent_zone[0]) / 3),
                          0.02, m.length - 0.02))
        a_u = float(rng.uniform(0.006, 0.022))       # across the grain (half-length)
        a_z = float(a_u * rng.uniform(0.12, 0.35))   # along it
        sites.append((f, u, z, a_u, a_z))
    return sites


def adaptive_counts(m: T.Member, row_sp=0.025, across_sp=0.015, check_row_sp=0.008, check_end_sp=0.002,
                    fine=0.00125, dent_sp=0.0012, local_rows=True, margin=0.03, collect=None, refine=True,
                    grades=(0.0006, 0.0014, 0.0025), hw_floor=0.00016, check_rows=True):
    """Samples of a feature-adaptive sampling of ``m``; returns (rows, samples).

    Base rows every ``row_sp`` sample the whole section. Feature rows (around
    checks, knots and dents) are local when ``local_rows``. On a face with a
    feature in that row they hold the base grid within ``margin`` of the
    feature, plus the feature's own samples. Every other face gets only its
    arris grades. Corners keep all their samples in every row, so arris
    highlights never facet.

    ``collect`` (a list) receives (face, z, u) for every row. ``refine=False``
    drops knot and dent refinement, as for the SM5 fallback, which bakes them.
    ``hw_floor`` keeps a check's half-width large enough that its own samples
    never fall below the sliver distance at the tapered ends, so the count across
    a check stays constant. ``check_rows=False`` adds no rows along checks."""
    half_w, half_d = m.width / 2, m.depth / 2
    base_rows = set(np.round(np.concatenate([np.arange(0.0, m.length + 1e-9, row_sp), [m.length]]), 7))
    feet = [ft for ft in T._knot_footprints(m)
            if m.finish[ft[0]] != "hidden" and T._visible(m, ft[0], ft[1])] if refine else []
    dents = dent_sites(m) if refine else []
    rows = [np.array(sorted(base_rows))]
    for f, u, zc, au, az in feet:
        rows.append(np.arange(max(0.0, zc - az * 1.3), min(m.length, zc + az * 1.3), fine))
    for ck in m.log.checks:
        if m.finish[ck.face] == "hidden" or not check_rows:
            continue
        rows.append(np.arange(ck.z0, ck.z1, check_row_sp))
        for zc in (ck.z0, ck.z1):
            rows.append(np.arange(max(0.0, zc - 0.05), min(m.length, zc + 0.05), check_end_sp))
    for f, u, z, a_u, a_z in dents:
        rows.append(np.arange(max(0.0, z - 2 * a_z), min(m.length, z + 2 * a_z), dent_sp))
    z_rows = np.unique(np.round(np.concatenate(rows), 7))
    z_rows = z_rows[(z_rows >= 0) & (z_rows <= m.length)]
    total = 0
    for z in z_rows:
        full = (not local_rows) or (z in base_rows)
        n = 4 * m.corner_samples
        for f in range(4):
            half = half_d if f % 2 == 0 else half_w
            u0, u1 = -half + m.arris_r[(f - 1) % 4], half - m.arris_r[f]
            if m.finish[f] == "hidden":
                n += (int((u1 - u0) / m.hidden_spacing) + 1) if full else 1
                continue
            vis = m.visible[f]
            g = np.arange(math.ceil(u0 / across_sp), math.floor(u1 / across_sp) + 1) * across_sp
            if vis is not None:
                coarse = np.arange(math.ceil(u0 / m.hidden_spacing), math.floor(u1 / m.hidden_spacing) + 1) * m.hidden_spacing
                g = np.concatenate([g[(g >= vis[0]) & (g <= vis[1])], coarse[(coarse < vis[0]) | (coarse > vis[1])]])
            pts = [np.array([u0]), u0 + np.array(grades), u1 - np.array(grades)]
            keep = np.ones(g.size, bool) if full else np.zeros(g.size, bool)
            spans = []
            for ck in m.log.checks:
                if ck.face != f or not (ck.z0 <= z <= ck.z1):
                    continue
                uc, wz, _ = T._check_at(ck, z, straight=m.fallback)
                hw = max(wz / 2, hw_floor)
                zone = hw * 1.6 + 0.0028
                spans.append((uc - zone, uc + zone))
                pts.append(uc + hw * np.array([-1.6, -1.0, -0.66, -0.33, 0.0, 0.33, 0.66, 1.0, 1.6]))
                beyond = hw * 1.6 + np.array([0.0003, 0.0008, 0.0016, 0.0028])
                pts += [uc - beyond, uc + beyond]
            for kf, ku, kz, au, az in feet:
                if kf == f and abs(z - kz) <= az * 1.3:
                    spans.append((ku - au * 1.3, ku + au * 1.3))
                    pts.append(np.arange(ku - au * 1.3, ku + au * 1.3, fine))
            for df, du, dz, a_u, a_z in dents:
                if df == f and abs(z - dz) <= 2 * a_z:
                    spans.append((du - 2 * a_u, du + 2 * a_u))
                    pts.append(np.arange(du - 2 * a_u, du + 2 * a_u, dent_sp))
            if not full:
                for lo, hi in spans:
                    keep |= (g >= lo - margin) & (g <= hi + margin)
            for ck in m.log.checks:
                if ck.face == f and ck.z0 <= z <= ck.z1:
                    uc, wz, _ = T._check_at(ck, z, straight=m.fallback)
                    keep &= np.abs(g - uc) > max(wz / 2, hw_floor) * 1.6 + 0.0028 + across_sp / 2
            pts.append(g[keep])
            u = np.unique(np.concatenate(pts))
            u = u[(u >= u0) & (u < u1 - 1e-7)]
            if u.size > 1:
                u = u[np.concatenate([[True], np.diff(u) > 0.00005])]
            if collect is not None:
                collect.append((f, float(z), u))
            n += u.size
        total += n
    return int(z_rows.size), int(total)


def adaptive_check_topology(m: T.Member, **kw):
    """check_topology for the adaptive sampling: samples across each check, row by row."""
    rows = []
    adaptive_counts(m, collect=rows, **kw)
    across = kw.get("across_sp", 0.015)
    out = []
    for i, ck in enumerate(m.log.checks):
        if m.finish[ck.face] == "hidden":
            continue
        counts = []
        for f, z, u in rows:
            if f != ck.face or not (ck.z0 <= z <= ck.z1):
                continue
            uc, wz, _ = T._check_at(ck, z, straight=m.fallback)
            zone = max(wz / 2, kw.get("hw_floor", 0.00016)) * 1.6 + 0.0028 + across / 2
            counts.append(int(np.sum(np.abs(u - uc) < zone)))
        if len(counts) < 2:
            continue
        c = np.array(counts)
        changes = int(np.sum(np.diff(c) != 0))
        out.append({"check": i, "face": ck.face, "rows": int(c.size), "count_min": int(c.min()),
                    "count_max": int(c.max()), "row_to_row_changes": changes,
                    "change_rate": round(changes / max(1, c.size - 1), 3)})
    return out


# The budgets compared in the proposal: F is the recommendation, C the coarser
# option, and G is F with 6 arris samples instead of 10.
BUDGETS = {
    "F": dict(row_sp=0.04, across_sp=0.02, check_row_sp=0.008, check_end_sp=0.002, fine=0.0015, dent_sp=0.0015),
    "C": dict(row_sp=0.04, across_sp=0.02, check_row_sp=0.015, check_end_sp=0.003, fine=0.0015, dent_sp=0.0015),
}


def budget(m: T.Member, name: str):
    if name == "G":
        return 2 * adaptive_counts(replace(m, corner_samples=6), **BUDGETS["F"])[1]
    return 2 * adaptive_counts(m, **BUDGETS[name])[1]


def fallback_topology(m: T.Member):
    """Today's fallback, and the same fallback with the check zone kept clear."""
    mf = T.fallback_of(m)
    fixed = dict(row_sp=mf.spacing, across_sp=mf.spacing, refine=False, local_rows=False, grades=(0.0025,),
                 check_rows=False)
    return {"today": check_topology(mf, T.sample_member(mf)), "zone_clear": adaptive_check_topology(mf, **fixed),
            "samples_today": int(T.sample_member(mf).x.size), "samples_zone_clear": adaptive_counts(mf, **fixed)[1]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", type=Path)
    ap.add_argument("--quick", action="store_true", help="sample members only, no whole-hall totals")
    a = ap.parse_args(argv)
    t0 = time.time()
    columns = json.loads((KIT / "manifest.json").read_text())
    rails = json.loads((KIT / "Rails/manifest.json").read_text())
    report = {"budgets": BUDGETS, "members": []}
    for kind in ("wall", "open"):
        rec = next(p for p in columns["placements"] if p["kind"] == kind)
        m = column_member(rec["seed"], kind, rec["asset"])
        rel, B = relief(m)
        report["members"].append({
            "asset": rec["asset"], "kind": kind, "manifest_triangles": rec["triangles"],
            "rebuilt_triangles": 2 * (B["verts"].shape[0]), "relief_room_face_today": rel,
            "check_topology_dense": {"today": check_topology(m, B["samples"]),
                                     "zone_clear_F": adaptive_check_topology(m, **BUDGETS["F"])},
            "check_topology_fallback": fallback_topology(m),
            "budget_triangles": {k: budget(m, k) for k in ("F", "C", "G")},
        })
    for kind in R["RAILS"]:
        rec = next(p for p in rails["placements"] if p["kind"] == kind)
        m = rail_member(rec["seed"], kind, rec["asset"], rec["length_m"])
        report["members"].append({"asset": rec["asset"], "kind": kind, "manifest_triangles": rec["triangles"],
                                  "rebuilt_triangles": 2 * T.sample_member(m).x.size,
                                  "budget_triangles": {k: budget(m, k) for k in ("F", "C", "G")}})
    for row in report["members"]:
        print(f"{row['kind']:8s} manifest {row['manifest_triangles']:>8,} rebuilt {row['rebuilt_triangles']:>8,} "
              + " ".join(f"{k} {v:>8,}" for k, v in row["budget_triangles"].items()), flush=True)
    if not a.quick:
        cm = [column_member(p["seed"], p["kind"], p["asset"]) for p in columns["placements"]]
        rm = [rail_member(p["seed"], p["kind"], p["asset"], p["length_m"]) for p in rails["placements"]]
        hall = {"committed": {"columns": sum(p["triangles"] for p in columns["placements"]),
                              "rails": sum(p["triangles"] for p in rails["placements"])}}
        for k in ("F", "C", "G"):
            hall[k] = {"columns": sum(budget(m, k) for m in cm), "rails": sum(budget(m, k) for m in rm)}
        for k, v in hall.items():
            v["hall"] = v["columns"] + v["rails"]
            print(f"hall {k}: columns {v['columns']:,} rails {v['rails']:,} total {v['hall']:,}", flush=True)
        report["hall"] = hall
    report["seconds"] = round(time.time() - t0, 1)
    text = json.dumps(report, indent=1)
    if a.json:
        a.json.write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
