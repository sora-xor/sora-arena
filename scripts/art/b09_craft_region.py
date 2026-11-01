"""The b09 working region: where the hero may stand and face to craft each station, and the gates every admitted stand
and facing must pass (Coordinations 259, 268, 269, 271).

**The region** (REGION, root's prototype target in Coordination 269), in the station frame (+X away from the hero, +Y
the hero's right, Z up):
- **the natural stop** (natural_stop): the capsule's axis where walking along +X on the station's centre line stops
  against the station's proxies. The capsule is 34 cm in radius and 176 cm tall (SoraPlayerCharacter.cpp).
- **depth:** from the natural stop back (-X) by depth_cm;
- **lateral:** |y| <= lateral_cm;
- **facing:** within +-yaw_deg of the bearing from the capsule's axis to the station's fixed look point (the LookPoint
  socket). Root approved this reference in Coordination 271: a hero standing to the side faces the work, not +X. It
  never turns the hero or moves the look point.

**Walkable:** only stands the capsule can occupy count: each station's proxy is a plain box, and its front face is
the near boundary (near_limit). A notch of two cheek posts was tried and withdrawn: its floor posts came within
1.42 cm of the feet (the body gate). Unreal's swept capsule and mapped keyboard/controller walk-up, turning,
release/retry and backing out are root's evidence (Coordination 271).

**Admission** (admitted): the formula root's runtime and this gate share.

**The gates**, at sampled stands and facings (stands, facings):
- **pose** (pose_gate): every action's every sample, both paws, from b09_craft_poses.check: reach, elbow, wrist, torso
  and continuity. The paws' fingers and palms follow the actual shoulders at each stand.
- **view** (view_gate): every working sample's active contacts in frame at 16:9 and 21:9 and hidden by no prop. The
  camera is yawed to the facing and pitched toward the look point. A brush's contacts include its swept bristles.
- **body** (body_gate): the hero's production mesh 2.5 cm clear of every prop in every state.
- **clearance** (clearance_gate): the triangle-exact sleeve, palm and arm gates of b09_craft_poses.check.

**Records kept:** REGION_EXPLORATORY (22/15/15) and its measured conflict; the 15/10/10 feasibility searches
(Saved/Qualification/2026-10-27/b09-craft-region/).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b09_workshop_craft as B  # noqa: E402
import b09_craft_poses as P  # noqa: E402

REGION = {"depth_cm": 15.0, "lateral_cm": 10.0, "yaw_deg": 10.0}            # Coordination 269, a prototype target
REGION_EXPLORATORY = {"depth_cm": 22.0, "lateral_cm": 15.0, "yaw_deg": 15.0,
                      "measured": "infeasible: with today's layouts 59-96 of 441 grid stands pass per station; one ideal "
                                  "contact point, (24, 27, 114) cm from the natural stop, is reachable from every corner "
                                  "(06:11 UTC)"}
# The paste's own region: no supported posture of its frame passes 15/10/10. The free-left-hold search found none (0 of
# 15,552), and the visible-hold search (paste_vis2, Saved/Qualification/2026-10-27/b09-craft-region) finds frames only
# at 10/10/10 (21 of 27,648; at 12/10/10 and 15/10/10 the brush's reach to the seam's far end is 98.9 and 102.6 % at
# best). Proposed for root's decision; root reviews the physical proposal before runtime admission (Coordination 277).
REGION_BY_STATION = {1: {"depth_cm": 10.0, "lateral_cm": 10.0, "yaw_deg": 10.0}}
BODY_CLEAR_CM = 2.5                                                         # the body from every prop (Coordination 269)


def region_of(i):
    return REGION_BY_STATION.get(i, REGION)


def proxies(i):
    return B.station_parts(i)[2]


# The helpers below take the station's proxies (`boxes`) or look point (`lp`) when the caller has them, so that one
# station build serves a whole bisection or sampling (B.station_parts builds every mesh); the results are the same.
def _hits(i, x, y, boxes=None):
    boxes = proxies(i) if boxes is None else boxes
    return any(B.circle_hits_box2d(np.array([x, y]), B.CAPSULE_R, lo, hi) for lo, hi in boxes
               if lo[2] < 2 * B.CAPSULE_HALF and hi[2] > 0.0)


def natural_stop(i, boxes=None):
    """The capsule's axis (station frame, on the floor) where walking along +X on the centre line stops."""
    boxes = proxies(i) if boxes is None else boxes
    lo, hi = -400.0, 0.0
    assert not _hits(i, lo, 0.0, boxes)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if not _hits(i, mid, 0.0, boxes) else (lo, mid)
    return np.array([lo, 0.0, 0.0])


def near_limit(i, y, boxes=None):
    """The walkable limit along +X at lateral y (station frame x), at most the natural stop's."""
    boxes = proxies(i) if boxes is None else boxes
    x0 = float(natural_stop(i, boxes)[0])
    lo, hi = x0 - 3 * region_of(i)["depth_cm"], x0
    if not _hits(i, hi, y, boxes):
        return hi
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if not _hits(i, mid, y, boxes) else (lo, mid)
    return lo


def look_point(i):
    return np.asarray(B.station_parts(i)[1]["LookPoint"][0], float)


def bearing_deg(i, stand, lp=None):
    lp = look_point(i) if lp is None else lp
    return math.degrees(math.atan2(lp[1] - stand[1], lp[0] - stand[0]))


def admitted(i, stand, yaw_deg, region=None):
    """The admission rule (root's runtime and this gate): the capsule's axis within depth behind the natural stop and
    within the lateral bound, and the facing within the band about the bearing to the look point. Station frame."""
    r = region or region_of(i)
    _, sk, boxes, _ = B.station_parts(i)
    x0 = float(natural_stop(i, boxes)[0])
    dyaw = (yaw_deg - bearing_deg(i, stand, np.asarray(sk["LookPoint"][0], float)) + 180.0) % 360.0 - 180.0
    return (x0 - r["depth_cm"] - 1e-6 <= stand[0] <= x0 + 1e-6 and abs(stand[1]) <= r["lateral_cm"] + 1e-6
            and abs(dyaw) <= r["yaw_deg"] + 1e-6 and not _hits(i, stand[0], stand[1], boxes))


def stands(i, region=None, n_lat=5, n_depth=4):
    """Walkable stands of the region: its near boundary (the walkable limit), far edge, lateral edges and interior.
    [(name, stand)]; station frame."""
    r = region or region_of(i)
    D, W = r["depth_cm"], r["lateral_cm"]
    boxes = proxies(i)
    x0 = float(natural_stop(i, boxes)[0])
    out = []
    for y in np.linspace(-W, W, 2 * n_lat - 1):
        xn = near_limit(i, y, boxes)
        if xn >= x0 - D:
            out.append((f"near y{y:+.1f}", np.array([xn, y, 0.0])))
        out.append((f"far y{y:+.1f}", np.array([x0 - D, y, 0.0])))
    for y in (-W, W):
        xn = near_limit(i, y, boxes)
        for x in np.linspace(x0 - D, xn, n_depth + 1)[1:-1]:
            out.append((f"side y{y:+.1f} x{x - x0:+.1f}", np.array([x, y, 0.0])))
    for x in np.linspace(x0 - D, x0, n_depth + 1)[1:-1]:
        for y in np.linspace(-W, W, n_lat)[1:-1]:
            if not _hits(i, x, y, boxes):
                out.append((f"inner y{y:+.1f} x{x - x0:+.1f}", np.array([x, y, 0.0])))
    return out


def facings(i, stand, region=None, n=3, lp=None):
    r = region or region_of(i)
    b = bearing_deg(i, stand, lp)
    return [b + d for d in np.linspace(-r["yaw_deg"], r["yaw_deg"], n)]


def dense(i, region=None):
    """A denser sampling of the region for the final gate: 9 lateral stations and 6 depths, 5 facings."""
    lp = look_point(i)
    return [(name, st, yaw) for name, st in stands(i, region, n_lat=9, n_depth=6)
            for yaw in facings(i, st, region, n=5, lp=lp)]


def samples(i, region=None, **kw):
    """[(stand name, stand, yaw)] over the region's stands and its facing band's ends and middle."""
    lp = look_point(i)
    return [(name, st, yaw) for name, st in stands(i, region, **kw) for yaw in facings(i, st, region, lp=lp)]


def pose_gate(i, region=None, **kw):
    """Every action at every sampled stand and facing (reach, elbow, wrist, torso, continuity; no clearance):
    {"samples", "passed", "fail": [(stand, yaw, action, first failure)], "worst" {gate: value}}."""
    rows, worst = [], {}
    smp = samples(i, region, **kw)
    for name, st, yaw in smp:
        for action, rep in P.check(i, st, yaw, clearance=False).items():
            for k, v in rep["worst"].items():
                worst[k] = max(worst.get(k, v), v) if k != "clear_cm" else min(worst.get(k, v), v)
            if not rep["ok"]:
                rows.append((name, round(float(yaw), 2), action, rep["fail"][0]))
    bad = {(r[0], r[1]) for r in rows}
    return {"samples": len(smp), "passed": len(smp) - len(bad), "fail": rows, "worst": worst}


def view_gate(i, region=None, **kw):
    """The active contacts of every working sample in frame and unoccluded at each sampled stand and facing:
    {aspect: {"samples", "passed", "fail": [(stand, yaw, action, seen, of)]}}."""
    out = {a: {"samples": 0, "passed": 0, "fail": []} for a in B.ASPECTS}
    for name, st, yaw in samples(i, region, **kw):
        for action, rows in P.view_at(i, st, yaw).items():
            for aspect, r in rows.items():
                o = out[aspect]
                o["samples"] += 1
                if r["in_frame"] == r["samples"]:
                    o["passed"] += 1
                else:
                    o["fail"].append((name, round(float(yaw), 2), action, r["in_frame"], r["samples"]))
    return out


def _states(i):
    """The distinct prop states station i's actions show: [(label, meshes)]."""
    seen, out = set(), []
    for name, steps in P.actions(i):
        for ph in steps:
            n = max(len(ph["L"]), len(ph["R"]))
            for k in sorted({0, n - 1}):
                key = (tuple(sorted(ph["state"].items())), round(P._bend_ms(ph["state"], P._u(ph, k)), 3))
                if key not in seen:
                    seen.add(key)
                    out.append((f"{name}: {ph['phase']} [{k}]", P.props(i, ph["state"], P._u(ph, k))))
    return out


def body_gate(i, region=None, where=("near", "side")):
    """The hero's production mesh (b09_prop_clash.hero_body: the torso, legs, head and worn gear) BODY_CLEAR_CM clear
    of every prop in every state the station's actions show, at the region's stands nearest the work (its near
    boundary and lateral edges, the body's closest) and the facing band's ends and middle:
    {"samples", "passed", "least_cm", "fail": [(stand, yaw, state, cm, near point)]}."""
    import b09_prop_clash as C
    import mesh_clearance as MC
    states = [(label, B.merge("props", ms)) for label, ms in _states(i)]
    smp = [(n, st, yaw) for n, st, yaw in samples(i, region) if n.split()[0] in where]
    least, fails = None, []
    for name, st, yaw in smp:
        body = C.body_at(st, yaw)
        rel = (body.verts - [st[0], st[1], 0.0]) @ P.shoulders(st, yaw)[1]      # the body's own frame
        keep = np.all(rel[body.tris][:, :, 0] > 5.0, axis=1)                    # its front: what can meet the work
        front = B.Mesh("body", body.verts, body.tris[keep], "M_Hero")
        for label, scene in states:
            tris = P.near_tris(front, scene, BODY_CLEAR_CM + 1.0)
            r = (MC.exact_separation(front.verts, front.tris, scene.verts, tris, limit=BODY_CLEAR_CM + 1.0) if len(tris)
                 else {"separation_m": None, "at": None})
            cm = BODY_CLEAR_CM + 1.0 if r["separation_m"] is None else float(r["separation_m"])
            least = cm if least is None else min(least, cm)
            if cm < BODY_CLEAR_CM:
                fails.append((name, round(float(yaw), 2), label, round(cm, 3), None if r["at"] is None else np.round(r["at"][1], 1).tolist()))
    bad = {(f[0], f[1]) for f in fails}
    return {"samples": len(smp), "passed": len(smp) - len(bad), "least_cm": None if least is None else round(least, 3), "fail": fails}


def region_spec(i):
    """The station's working region for the signed spec (station frame: +X away from the hero, +Y its right; cm and
    degrees): the bounds, the natural stop, the fixed look point, the admission rule root's runtime and these gates
    share, the walkable near boundary, and the sampling the gates use."""
    r = region_of(i)
    boxes = proxies(i)
    x0 = float(natural_stop(i, boxes)[0])
    W = r["lateral_cm"]
    return {
        "region": dict(r),
        "natural_stop_cm": [round(x0, 3), 0.0, 0.0],
        "look_point_cm": np.round(look_point(i), 3).tolist(),
        "admission": ("admitted(stand, yaw) = x0 - depth_cm <= stand.x <= x0 and |stand.y| <= lateral_cm and "
                      "|wrap180(yaw - atan2(LookPoint.y - stand.y, LookPoint.x - stand.x))| <= yaw_deg and the capsule "
                      "(radius 34 cm, half-height 88 cm) clear of every collision proxy; stand = the capsule's axis on "
                      "the floor; x0 = natural_stop_cm.x (b09_craft_region.admitted)"),
        "near_boundary_cm": [[round(near_limit(i, float(y), boxes), 3), round(float(y), 3)] for y in np.linspace(-W, W, 9)],
        "sampling": {"stands": f"{len(stands(i))} stands (near boundary, far edge, lateral edges, interior) x 3 facings "
                               "(the band's ends and middle)",
                     "dense_pose": f"{len(dense(i))} samples (9 lateral x 6 depths x 5 facings)"},
        "not_covered": "Unreal's swept capsule, mapped keyboard/controller walk-up, turning, release/retry and backing "
                       "out are root's evidence (Coordination 271)",
    }


def clearance_gate(i, region=None, where=("near", "far", "side")):
    """The triangle-exact sleeve, palm and arm gates (b09_craft_poses.check with clearance, every sample) at the
    region's boundary stands and the facing band's ends: {"samples", "passed", "fail", "worst"}."""
    smp = [(n, st, yaw) for n, st, yaw in samples(i, region) if n.split()[0] in where]
    rows, worst = [], {}
    for name, st, yaw in smp:
        for action, rep in P.check(i, st, yaw, clearance=True, every=1).items():
            for k, v in rep["worst"].items():
                worst[k] = max(worst.get(k, v), v) if k != "clear_cm" else min(worst.get(k, v), v)
            if not rep["ok"]:
                rows.append((name, round(float(yaw), 2), action, rep["fail"][0]))
    bad = {(r[0], r[1]) for r in rows}
    return {"samples": len(smp), "passed": len(smp) - len(bad), "fail": rows, "worst": worst}
