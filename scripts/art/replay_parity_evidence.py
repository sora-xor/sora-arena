"""Replay a rig run's parity disagreements in float64, independently of Blender (root's 18:28 UTC request, 2026-10-26).

rig_nyaakoto_runtime.py --parity-evidence <dir> saves each containment test whose two rays disagreed. Each event is
one .npz holding the point and the target island's vertices and triangles as Blender evaluated them, the rays, and
each ray's hits; index.jsonl lists it with its SHA-256. For every event this:
- checks the file's SHA-256 against the index;
- recomputes from the stored data alone, numerically in float64:
  - each ray's crossings, by its own ray-triangle test: counted with merging only within 1e-9 m, and again with the
    Blender backend's rule of casting again 1e-5 m past each hit;
  - the target's topology (mesh_clearance.oriented_manifold), finiteness, least triangle area and signed volume;
  - the point's distance to the target and the target's winding number about it;
- compares them with what the run recorded, and with the verdict mesh_clearance._inside's rule gives on them.

Run (host Python with numpy): python3 scripts/art/replay_parity_evidence.py <evidence dir> <out.json>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mesh_clearance as MC  # noqa: E402

STEP = 1e-5                                            # BlenderBackend.ray_hits: the next cast starts this far past a hit


def ray_distances(o, d, tri, eps=1e-12):
    """Every distance t > 0 at which the ray o + t d meets a triangle (edges included within eps), float64."""
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    e1, e2 = b - a, c - a
    p = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-300
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    s = o - a
    u = np.einsum("ij,ij->i", s, p) * inv
    q = np.cross(s, e1)
    v = (q @ d) * inv
    t = np.einsum("ij,ij->i", e2, q) * inv
    hit = ok & (u >= -eps) & (v >= -eps) & (u + v <= 1.0 + eps) & (t > 0.0)
    return np.sort(t[hit])


def counts(ts):
    merged = int(np.sum(np.diff(np.concatenate([[-1.0], ts])) > 1e-9)) if len(ts) else 0
    stepped, cur = 0, 0.0
    for x in ts:
        if x > cur:
            stepped += 1
            cur = x + STEP
    return merged, stepped


def replay(EVIDENCE):
    """Every event in an evidence directory, replayed (see the module's notes): the summary, each event's row."""
    index = [json.loads(line) for line in (EVIDENCE / "index.jsonl").read_text().splitlines() if line.strip()]
    rows = []
    for row in index:
        path = EVIDENCE / row["file"]
        sha_ok = hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
        z = np.load(path)
        p, verts, tris, rays = z["point"], z["vertices"], z["triangles"].astype(np.int64), z["rays"]
        tri = verts[tris]
        finite = bool(np.isfinite(p).all() and np.isfinite(verts).all())
        out = {"file": row["file"], "sha256_ok": sha_ok, "frame": row["frame"], "gate": row["gate"], "test": row["test"],
               "recorded": {k: row.get(k) for k in ("ray_hits", "verdict", "decidable", "winding", "gap_m",
                                                     "signed_volume_m3", "oriented_manifold")}}
        if finite:
            rc = [counts(ray_distances(p, rays[k] / np.linalg.norm(rays[k]), tri)) for k in range(len(rays))]
            area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
            volume = float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0)
            q = np.repeat(p[None], len(tri), 0)
            gap = float(np.linalg.norm(MC.closest_point_triangle_v(q, tri[:, 0], tri[:, 1], tri[:, 2]) - q, axis=1).min())
            w = MC.winding_number(p, tri)
            n = int(round(w))
            sign = 1 if volume > 0 else -1
            oriented = MC.oriented_manifold(tris)
            decidable = (oriented and float(area.min()) >= MC.AREA_MIN and abs(volume) >= MC.VOLUME_MIN
                         and gap >= MC.WINDING_CLEAR and abs(w - n) <= MC.WINDING_TOL and n in (0, sign))
            out["replay"] = {"ray_counts_merged_1e-9": [c[0] for c in rc], "ray_counts_stepped_1e-5": [c[1] for c in rc],
                             "parities_merged_agree": rc[0][0] % 2 == rc[1][0] % 2,
                             "oriented_manifold": oriented, "min_area_m2": float(area.min()), "signed_volume_m3": volume,
                             "gap_m": gap, "winding": w, "off_integer": abs(w - n), "decidable": bool(decidable),
                             "verdict_by_rule": (n == sign) if decidable else None,
                             "inside_by_merged_rays": bool(rc[0][0] % 2) if rc[0][0] % 2 == rc[1][0] % 2 else None}
            rec = row.get("verdict")
            out["agrees_with_record"] = (rec is None or rec == out["replay"]["verdict_by_rule"]) and \
                (not row.get("resolve_parity") or rec == out["replay"]["verdict_by_rule"])
        else:
            out["replay"] = {"finite": False}
            out["agrees_with_record"] = row.get("verdict") is None
        rows.append(out)
    summary = {"evidence": str(EVIDENCE), "events": len(rows), "sha256_ok": all(r["sha256_ok"] for r in rows),
               "agree": all(r["agrees_with_record"] for r in rows), "rows": rows}
    return summary


if __name__ == "__main__":
    summary = replay(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(summary, indent=1) + "\n")
    print("PARITY_REPLAY " + json.dumps({k: summary[k] for k in ("events", "sha256_ok", "agree")}), flush=True)
    if not (summary["sha256_ok"] and summary["agree"]):
        raise SystemExit("PARITY_REPLAY_FAILED")
