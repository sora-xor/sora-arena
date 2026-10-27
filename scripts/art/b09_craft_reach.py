"""Can the hero's paws reach the b09 craft contacts? A CPU reach study, before any craft paw is posed.

Root's integration audit (Saved/Qualification/2026-10-27/b09-integration-review.json) makes the authored craft paws
and believable hand-tool contact Claude's, with the contact drawn at the world's 94 deg projection. This module asks
the question that comes first: from where the hero can stand, do the paws reach the contacts at all?

**The hero** (in Unreal cm):
- the standing eye is at the capsule's centre + (4, 0, 64) (SoraPlayerCharacter.cpp), with capsule radius 34 and
  half-height 88;
- the shoulders are (-4, +-27.7, -24.5) from the eye, with upper arm 29.05 cm and forearm 25.00 cm
  (runtime_skin_manifest.json arm_joints_blender_m, the production body);
- reach is at most 98 % of shoulder to wrist (THIRD_PERSON_GRIP_CONTRACT.md's two-bone limit): 52.97 cm.

**Where it can stand:** the capsule must clear the station's proposed proxy (b09_workshop_craft.station_parts), so
the stand nearest the work is the proxy's front less the capsule's radius. Every stand counted here is one root's
eligibility admits: feet on the station's floor, within 260 cm. The capsule is tested against the proxy alone, and
root's collision is root's.

**What it reports**, per station and contact (b09_workshop_craft's sockets and paths):
- the least shoulder distance over the admissible stands, and the shortfall against reach;
- the smallest translation of the station's whole work group, toward the hero and up, that brings every required
  contact within reach with REACH_MARGIN_CM to spare (layout_shift).

It moves nothing and authors no pose. The layout change and any first-person convention are root's decisions.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b09_workshop_craft as B  # noqa: E402

UPPER_ARM_CM, FOREARM_CM = 29.05, 25.00
REACH_CM = 0.98 * (UPPER_ARM_CM + FOREARM_CM)
SHOULDER_FROM_EYE = np.array([-4.0, 27.7, -24.5])      # right shoulder; +Y is the hero's right in Unreal
REACH_MARGIN_CM = 3.0
STAND_Y = np.arange(-40.0, 40.5, 1.0)                  # lateral stands considered, station frame


def eye_at(x, y):
    """The standing eye over a stand (station frame)."""
    return np.array([x + B.EYE[0], y + B.EYE[1], B.CAPSULE_HALF + B.EYE[2]])


def shoulders(x, y):
    e = eye_at(x, y)
    return {"R": e + SHOULDER_FROM_EYE, "L": e + SHOULDER_FROM_EYE * [1.0, -1.0, 1.0]}


def nearest_stand_x(i):
    """The stand nearest the work along -X: the capsule touching the front of the station's proxy."""
    _, _, proxies, _ = B.station_parts(i)
    return float(min(lo[0] for lo, hi in proxies)) - B.CAPSULE_R


def contacts(i):
    """The contacts a credible craft pose needs, per station: [(label, point, paw, required)].
    paw is "L", "R" or "either". A required contact must be reachable; a reported one is a rest or stock that a
    presentation could stage nearer."""
    _, sockets, _, _ = B.station_parts(i)
    sock = lambda n: np.asarray(sockets[n][0], float)  # noqa: E731
    out = []
    if i == 0:
        lift = np.array([0.0, 0.0, B.LANTERN_Z[0]])
        # The winding the craft pose needs: the strip's end hooked into the form's notch, the form turned on its
        # spindle, the left paw pressing the wound strip to the form at the front, the right paw guiding the free
        # strip in. Both stay at the form's front for every hoop.
        for k, (z, r) in enumerate(zip(B.hoop_z(), B.hoop_r()), 1):
            out.append((f"hoop {k} front, held to the form", lift + [-r - B.HOOP_T, 6.0, z], "L", True))
            out.append((f"hoop {k} front, the free strip guided", lift + [-r - 2.0, -9.0, z], "R", True))
        # Today's presentation bends both ends round at once (hoop_path), so its ends pass behind the form: reported.
        for f in B.FLEX_STAGES[1:]:
            pts, nrm, s, end = B.hoop_path(1, f)
            for paw, j in (("R", 0), ("L", -1)):
                out.append((f"two-ended bend, hoop 1 end at flex {f:g}", pts[j] + lift, paw, False))
        out += [("StripHoldL", sock("StripHoldL"), "L", True), ("StripHoldR", sock("StripHoldR"), "R", True),
                ("StripStock", sock("StripStock"), "either", False)]
    elif i == 1:
        out += [(f"Seam1_{j} (brush)", sock(f"Seam1_{j}"), "R", True) for j in range(9)]
        out += [("BrushRest", sock("BrushRest"), "R", False), ("WashiSheet1", sock("WashiSheet1"), "L", False),
                ("RimTopRest", sock("RimTopRest"), "either", False), ("RimTopSeat", sock("RimTopSeat"), "either", True),
                ("RimBottomSeat", sock("RimBottomSeat"), "either", True)]
    elif i == 2:
        out += [(f"OilStroke0_{j} (brush)", sock(f"OilStroke0_{j}"), "R", True) for j in range(9)]
        out += [("BrushRest", sock("BrushRest"), "R", False), ("OilJar", sock("OilJar"), "R", False)]
    else:
        out += [(f"ShellCore{k}", sock(f"ShellCore{k}"), "either", True) for k in (1, 2, 3)]
        out += [("WrapSpot", sock("WrapSpot"), "either", True)]
        out += [(f"ShellSeat{k}", sock(f"ShellSeat{k}"), "either", True) for k in (1, 2, 3)]
        out += [("FuseInspect", sock("FuseInspect"), "either", True)]
    return out


_CACHE = {}


def _station(i):
    """(nearest stand x, contacts, stand shoulders {side: (n, 3)}) for station i, computed once."""
    if i not in _CACHE:
        x0 = nearest_stand_x(i)
        sh = {"R": [], "L": []}
        for x in (x0, x0 - 5.0, x0 - 10.0):
            for y in STAND_Y:
                s_ = shoulders(x, y)
                sh["R"].append(s_["R"])
                sh["L"].append(s_["L"])
        _CACHE[i] = (x0, contacts(i), {k: np.array(v) for k, v in sh.items()})
    return _CACHE[i]


def _distances(i, shifts):
    """(len(shifts), n contacts): each contact's least shoulder distance over the admissible stands, with the work
    group moved by each shift (toward the hero dx, up dz)."""
    _, rows, sh = _station(i)
    shifts = np.asarray(shifts, float).reshape(-1, 2)
    move = np.stack([-shifts[:, 0], np.zeros(len(shifts)), shifts[:, 1]], 1)          # (G, 3)
    out = np.empty((len(shifts), len(rows)))
    for c, (label, p, paw, required) in enumerate(rows):
        pts = p[None, :] + move                                                           # (G, 3)
        sides = ("R", "L") if paw == "either" else (paw,)
        d = np.min([np.linalg.norm(pts[:, None, :] - sh[k][None, :, :], axis=2).min(1) for k in sides], axis=0)
        out[:, c] = d
    return out


def best_distance(i, point, paw):
    """The least shoulder-to-point distance over the admissible stands (x from the nearest stand back, y in STAND_Y)."""
    _, _, sh = _station(i)
    sides = ("R", "L") if paw == "either" else (paw,)
    return float(min(np.linalg.norm(sh[k] - point, axis=1).min() for k in sides))


def reach_table(i, shift=(0.0, 0.0)):
    """[(label, distance, shortfall, required)] with the work group moved by shift = (toward the hero, up) cm."""
    _, rows, _ = _station(i)
    d = _distances(i, [shift])[0]
    return [(label, float(dd), max(0.0, float(dd) - REACH_CM), req) for (label, _, _, req), dd in zip(rows, d)]


def layout_shift(i, max_cm=40.0, step=1.0):
    """The smallest move of the work group (toward the hero dx, up dz; least dx + dz) that brings every required
    contact within REACH_CM - REACH_MARGIN_CM, or None within max_cm. The proxies stay as proposed, so the stand does
    not move with the work. Whether the bench can carry the work there is a layout question this does not settle."""
    _, rows, _ = _station(i)
    req = np.array([r[3] for r in rows])
    grid = np.array([(dx, dz) for dx in np.arange(0.0, max_cm + 1e-9, step) for dz in np.arange(0.0, max_cm + 1e-9, step)])
    d = _distances(i, grid)[:, req]
    ok = (d <= REACH_CM - REACH_MARGIN_CM).all(1)
    if not ok.any():
        return None
    cost = grid.sum(1) + np.where(ok, 0.0, np.inf)
    k = int(np.argmin(cost))
    return (float(grid[k, 0]), float(grid[k, 1]))


def study():
    out = {"reach_cm": round(REACH_CM, 2), "margin_cm": REACH_MARGIN_CM, "stations": {}}
    for i, (sid, _) in enumerate(B.STATIONS):
        rows = reach_table(i)
        out["stations"][sid] = {
            "nearest_stand_x_cm": nearest_stand_x(i), "work_stand_x_cm": B.WORK_STAND[0],
            "contacts": [{"contact": l, "shoulder_cm": round(d, 1), "short_cm": round(s, 1), "required": r} for l, d, s, r in rows],
            "required_reachable": all(s == 0.0 for _, _, s, r in rows if r),
            "layout_shift_cm": layout_shift(i)}
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(study(), indent=1))
