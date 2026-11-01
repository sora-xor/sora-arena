"""Craft poses for the b09 stations, from one supported stand (Coordination 241).

Root's correction to the first reach study (b09_craft_reach.py, retired; in 3c6b3f70): it let every contact choose its own stand and sometimes its paw, so
it proved only that each contact could be reached alone. Here, both paws of a pose, and every sample of a
continuous action, work from the SAME stand, with fixed shoulders and assigned roles.

**The stand** is b09_workshop_craft.craft_stand(i), the capsule 1 cm clear of the station's proposed proxy, facing
+X. The shoulders are fixed there: (-4, +-27.7, -24.5) cm from the standing eye, in the hero's facing frame.

**The actions** (actions(i)) are records of phases. Each phase gives:
- each paw's targets, one per sample (SAMPLES along a path);
- whether it is the action's work ("phase") or a move between ("transition");
- the props' state it shows (state);
- the parts the paws work in it (works).
Each paw works its own side.

**The paw is the production paw's** (nyaakoto_fp_paws.py):
- the carpus (the wrist) is WRIST_BACK = 4.1 cm behind the knuckle line;
- the palm is 1.05 cm in half-thickness;
- the metacarpal pad sits under the knuckles.
A target is the knuckle line's centre C, the fingers' direction F and the palm's normal N, so the wrist is 4.1 cm
behind C. The targets follow the part:
- **press:** the pads flat on a surface;
- **grip:** round a strip, a rim's edge or a paper's edge;
- **claw:** a small part taken from above, the palm clear of its top (a shell's fuse stub or tied neck), the digits
  reaching down round it;
- **brush:** held as a pencil is.

**Each sample**, per paw, is solved and gated:
- **reach:** two-bone IK (third_person_rig.two_bone) with the production arm (upper arm 29.05, forearm 25.00 cm) and
  its 98 % reach. The elbow bends toward its pole, down and out.
- **the elbow:** flexion at most ELBOW_MAX, and outside the torso (TORSO).
- **the wrist:** the bend from the forearm to the fingers at most WRIST_MAX.
- **clearance,** triangle-exact (mesh_clearance.exact_separation):
  - the sleeves' stand-ins clear every prop by CLEAR_CM. They are the upper arm (a tube) and the forearm (a cone from
    the elbow to the cuff, 2 cm short of the wrist).
  - the palm's stand-in (PALM_HALF, from the carpus to just past the knuckles) clears the parts it does not work by
    CLEAR_CM, and does not pass into those it works (THROUGH_CM).
  - the two arms clear each other by CLEAR_CM.
- **continuity:** the elbow moves at most ELBOW_STEP_CM from one sample to the next. Each phase keeps one swivel
  (pole), chosen under every gate. A transition turns it from the phase before to the phase after; where that would
  fail a gate, the elbow swings out of the way and back smoothly (_transition_poles).

**The props** are the station's, in the state each phase shows (props(i, state)):
- **the rib form,** turned for the hoops wound, with the next hoop at the flex stage root shows at the sample's HeldMs
  (flex_stage), and the needle at that HeldMs. A strip in the paw is not a prop; a hooked strip is.
- **the paste bench,** with its sheets, rims and brush as the step leaves them.
- **the shell bench,** with its cores, seated shells and the shell on the paper as each phase of the clip has them.
- **weapon 7** as its real mesh (b09_prop_clash.weapon7), its rope, fibre cards and cord included.

**These are pose targets and gates, not authored poses.** The paw meshes, rig and keys come after root's
acceptance. The stand-ins are sized from the production kote (sleeve 3.0-3.8 cm) and paw. The digits are not in
them; the final meshes will be gated triangle-exactly again.

**The envelope** (envelope(i)) is the stands round craft_stand, and the facing yaws, from which every action passes
reach, elbow, wrist and torso. Clearance is checked at craft_stand itself. It is for root's interaction and presenter.

**Crouch** is reported apart (crouched(i)), from the crouched eye (CrouchedEyeZ 40 over CrouchedHalfHeight 44), with
the same shoulder offset. The standing proof does not qualify it.

**The press clips' longest durations** (CLIP_MAX_MS) are for the presenter, from root's FView.LastAction age.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b09_prop_clash as PC  # noqa: E402
import b09_workshop_craft as B  # noqa: E402
import mesh_clearance as MC  # noqa: E402
import third_person_rig as TPR  # noqa: E402

UPPER_ARM_CM, FOREARM_CM = 29.05, 25.00
REACH = TPR.REACH_MAX * (UPPER_ARM_CM + FOREARM_CM)
SHOULDER_FROM_EYE = np.array([-4.0, 27.7, -24.5])        # the right shoulder; +Y is the hero's right
STANDING_EYE_Z = B.CAPSULE_HALF + B.EYE[2]               # 152
CROUCHED_EYE_Z = 44.0 + 40.0                             # CrouchedHalfHeight + CrouchedEyeZ (SoraPlayerCharacter.cpp)
# The elbow's swivel about the shoulder-wrist line is the arm's free degree of freedom. Each phase keeps one pole (so
# the elbow moves continuously through it), the one of these, down and out, that serves the phase best.
POLES_R = [np.array(v, float) for v in ((-0.3, 0.6, -0.75), (0.0, 0.6, -0.8), (0.3, 0.6, -0.75), (0.0, 1.0, -0.25),
                                        (0.0, 0.3, -1.0), (0.45, 0.45, -0.75))]
POLES = {"R": POLES_R, "L": [v * [1.0, -1.0, 1.0] for v in POLES_R]}
# Reaching over a row of standing parts (the seated shells' fuse cords) the elbow rises, out and up, so the forearm
# passes over the parts the paw has passed: under the down-and-out poles it trailed down through them to the elbow.
POLES_OVER_R = [np.array(v, float) for v in ((0.0, 0.7, 0.7), (-0.3, 0.7, 0.6), (0.3, 0.7, 0.6), (0.0, 0.95, 0.3),
                                             (0.0, 0.5, 0.85))]
POLES_OVER = {"R": POLES_OVER_R, "L": [v * [1.0, -1.0, 1.0] for v in POLES_OVER_R]}
# Holding a small part up in front of the chest from its side toward the hero, the elbow may also lift level with the
# work: under the down-and-out poles alone the shell's holding forearm ran down over the rack and the board.
POLES_RAISED_R = [np.array(v, float) for v in ((0.0, 1.0, 0.0), (-0.3, 0.9, 0.25), (0.0, 0.85, 0.5))]
POLES_RAISED = {"R": POLES_RAISED_R, "L": [v * [1.0, -1.0, 1.0] for v in POLES_RAISED_R]}
ELBOW_MAX = 145.0                                        # elbow flexion, deg
WRIST_MAX = 75.0                                         # the paw's finger direction from the forearm, deg
ELBOW_STEP_CM = 5.0                                      # the elbow's largest move between samples
TORSO = {"back": -15.0, "front": 12.0, "half": 17.0}    # cm from the stand: no elbow inside this, at chest height
SLEEVE_R = {"upper": 4.5, "fore": 3.8, "cuff": 3.0}     # the forearm's cone: 3.8 at the elbow, 3.0 at the cuff
WRIST_BACK = 4.1                                         # the carpus behind the knuckle line (nyaakoto_fp_paws)
PAD_OFF = 1.2                                            # the knuckle line's centre over a surface its pads press
PALM_HALF = np.array([2.6, 3.6, 1.15])                   # the palm's ellipsoid: along the fingers, across, thick
PALM_MID = 2.05                                          # its centre, behind the knuckle line: carpus to knuckles
BRUSH_PINCH_CM = 6.0                                     # where the digits pinch a brush, up from the bristles' tip
BRUSH_REACH_CM = 4.5                                     # the pinch ahead of the knuckle line, the digits curled
BRUSH_GRIP_DEG = 35.0                                    # a pencil grip: the handle this far from the fingers
CLAW_CLEAR_CM = 0.2                                      # a claw's palm over the part's top (its stub or neck)
CLEAR_CM = 0.5                                           # sleeves and palm from the props, and the arms apart
THROUGH_CM = 0.005                                       # a palm nearer a part it works than this has passed into it
SAMPLES = 17
CLIP_MAX_MS = {"rims": 1200, "shell": 1200, "inspect": 900}   # FView.LastAction ages out at 1200 ms (root's contract)
UP, FWD = np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0])


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


# --- The paw targets: the knuckle line's centre C, the fingers' direction F and the palm's normal N -----------------
# A hand lines up with its forearm: each target's fingers point along the reach from its shoulder (at the craft
# stand), blended with the task's own direction.
def _fingers(c, shoulder, task, w=0.6):
    return unit(unit(np.asarray(c, float) - shoulder) + w * unit(task))


def press(point, surface_normal, shoulder, task):
    """The pads flat on a surface: the knuckle line PAD_OFF off it, the palm facing it, the fingers along it."""
    n = unit(surface_normal)
    c = np.asarray(point, float) + n * PAD_OFF
    f = _fingers(c, shoulder, task)
    return {"C": c, "F": unit(f - (f @ n) * n), "N": -n, "P": np.asarray(point, float), "plane": n}


STEADY_LIFT_CM = 1.5                                     # a steadying paw's palm arched this far over its pads' plane
STEADY_TIP_CM = 3.5                                      # its fingertips' contact ahead of the knuckle line


def steady(point, surface_normal, shoulder, task):
    """A paw steadying a round workpiece by its fingertips, as a hand steadies a hanging lantern: the fingertips on the
    surface at point, the palm arched STEADY_LIFT_CM over it, the knuckle line STEADY_TIP_CM back from the tips along
    the fingers. A flat palm on the lantern's curve kept the wrist 1.8 cm off the paper, so the sleeve's cuff met it
    from every stand that folds the arm (b09_craft_region)."""
    n = unit(surface_normal)
    c0 = np.asarray(point, float) + n * (PAD_OFF + STEADY_LIFT_CM)
    f = _fingers(c0, shoulder, task)
    f = unit(f - (f @ n) * n)
    return {"C": c0 - f * STEADY_TIP_CM, "F": f, "N": -n, "P": np.asarray(point, float), "plane": n, "pivot": c0,
            "pivot_back": STEADY_TIP_CM}


def grip(point, normal, shoulder, task, off=2.5, axis=None):
    """A grasp about a point (a strip, a rim's edge, a paper's edge): the knuckle line off cm from it along -normal,
    the digits curled round it. The palm faces it as nearly as the fingers' direction allows."""
    nn = unit(normal)
    c = np.asarray(point, float) - nn * off
    f = _fingers(c, shoulder, task)
    side = nn - (nn @ f) * f
    if np.linalg.norm(side) < 0.2:                                   # facing along the fingers: palm down instead
        side = -UP - (-UP @ f) * f
    # The fingers may turn about the palm's normal (the palm still faces the part), toward the actual forearm.
    t = {"C": c, "F": f, "N": unit(side), "P": np.asarray(point, float), "plane": unit(side)}
    if axis is not None:                                             # round a strip: the fingers square to its axis
        t["plane"] = unit(axis)
    return t


PALM_BALL_BACK_DEG = 20.0                                # a palm on a ball touches it at least this far round toward the hero
PALM_BALL_LAT_DEG = 35.0                                 # and this far up from its equator (pressing down and in, the digits
                                                         # under it): level, the holding forearm ran low over the rack


def _clamp_back(n, back_deg):
    """A level inward normal n turned, if need be, so the ball's surface it touches faces the hero (-X) by back_deg."""
    b = math.atan2(n[1], n[0])
    lim = math.radians(90.0 - back_deg)
    b = max(-lim, min(lim, b))
    return np.array([math.cos(b), math.sin(b), 0.0])


def palm_on_ball(centre, radius, inward, shoulder, task, lift=0.0, back_deg=None, lat_deg=None):
    """A palm against a ball from one side (a shell held or turned between two paws): the palm's normal level, turned from
    inward (toward the ball) as the fingers' line turns it, and the knuckle line PAD_OFF off the ball where the ball faces
    that normal, lift above its centre, so the palm lies on the ball's tangent plane there and cannot cut into it. A
    flat palm square to inward bent the far paw's wrist to 80 deg reaching across, and a grip's palm turned toward the
    fingers' line cut the ball with its edge at the facing band's ends. The palm stays on the ball's side toward the
    hero (back_deg): turned freely, it pressed the ball's front, and the ball hid the pads from the hero's eye. The
    fingers may turn about the palm's normal."""
    centre = np.asarray(centre, float)
    back_deg = PALM_BALL_BACK_DEG if back_deg is None else back_deg
    lat = math.radians(PALM_BALL_LAT_DEG if lat_deg is None else lat_deg)
    nn = unit(inward)
    n = nn
    for _ in range(3):
        c = centre - n * (radius + PAD_OFF) + UP * lift
        f = _fingers(c, shoulder, task)
        side = nn - (nn @ f) * f
        side = unit([side[0], side[1], 0.0])
        n = unit(_clamp_back(side, back_deg) * math.cos(lat) - UP * math.sin(lat))
    c = centre - n * (radius + PAD_OFF) + UP * lift
    f = _fingers(c, shoulder, task)
    # The point worked: the ball under the knuckle line, where the pads press (the palm's flat touches it lower, at the
    # tangent point on the ball's limb as the eye sees it).
    return {"C": c, "F": unit(f - (f @ n) * n), "N": n, "P": centre + unit(c - centre) * radius, "plane": n}


def claw(top, shoulder, task=FWD):
    """A small part taken from above: the palm flat and level over its top (a fuse stub or a tied neck included) by
    CLAW_CLEAR_CM, the fingers along the reach, the digits reaching down round it."""
    c = np.asarray(top, float) + UP * (PAD_OFF + CLAW_CLEAR_CM)
    f = _fingers(c, shoulder, task)
    return {"C": c, "F": unit(f - (f @ UP) * UP), "N": -UP, "P": np.asarray(top, float), "plane": UP}


def brush(tip, surface_normal, shoulder, tilt=0.25, width=None, across=None, square=1.0):
    """A brush's bristle tip at tip, its handle back toward the hand: along the line to the shoulder, tipped toward the
    surface's normal so the bristles meet it at a working angle.

    It is held as a pencil is, not as a dagger: the digits pinch it BRUSH_PINCH_CM up the handle, BRUSH_REACH_CM
    ahead of the knuckle line, the handle BRUSH_GRIP_DEG from the fingers in the palm's plane, the tip on the palm's
    side. (Writing, a pencil lies about 50 deg from the forearm with the wrist straight.) The fingers lean from the
    brush toward the reach.

    With width (the flat bristles' width, cm), the target also carries the bristles' contact: "foot", the tip edge's
    two corners, its flat face against the surface; and "brush_x", the brush's width axis (its mesh's local X; local
    Y runs from the tip up the handle, along a). With across (a direction in the surface) and square 1, the bristle
    edge lies along it, square across the stroke, as it must against an edge such as a rim line, and the handle leans
    as near the hand as that allows; square 0 leaves the handle toward the hand, and between them it turns smoothly."""
    tip = np.asarray(tip, float)
    n = unit(surface_normal)
    a = unit(unit(shoulder - tip) + tilt * n)                         # from the tip toward the hand
    if across is not None and square > 0.0:
        across = unit(np.asarray(across, float) - (np.asarray(across, float) @ n) * n)
        a = unit((1.0 - square) * a + square * unit(a - (a @ across) * across))
    pinch = tip + a * BRUSH_PINCH_CM
    reach = unit(pinch - shoulder)
    m = unit(reach - (reach @ a) * a)
    th = math.radians(BRUSH_GRIP_DEG)
    f = -math.cos(th) * a + math.sin(th) * m
    t = {"C": pinch - f * BRUSH_REACH_CM, "F": f, "N": -math.sin(th) * a - math.cos(th) * m, "P": tip, "brush_y": a}
    if width:
        wx = unit(np.cross(a, unit(n - (n @ a) * a)))
        t.update(brush_x=wx, foot=[tip - wx * width / 2, tip + wx * width / 2], width=width)
    return t


def wrist_of(t):
    return t["C"] - t["F"] * WRIST_BACK


# --- The actions --------------------------------------------------------------------------------------------------
def _line(a, b, n=SAMPLES):
    return [a + (b - a) * u for u in np.linspace(0.0, 1.0, n)]


def _arc(a, b, lift=8.0, n=SAMPLES):
    """A transition from a to b, lifted at its middle (a paw carries things over, not through)."""
    return [a + (b - a) * u + np.array([0.0, 0.0, lift * math.sin(math.pi * u)]) for u in np.linspace(0.0, 1.0, n)]


def _hold(t, n=SAMPLES):
    return [t] * n


PATH_SAMPLE_CM = 1.5                                     # a curved carry's samples at most this far apart along its path, as
                                                         # the 17-sample carries are (the elbow continuity gate is per sample)


def _bezier(a, ctrl, b, n=SAMPLES, ctrl2=None):
    """A path from a to b bowed toward ctrl (a quadratic Bezier), or leaving toward ctrl and arriving from ctrl2 (a cubic
    one): a carry that lifts its part out and goes round another, not through it."""
    def at(us):
        if ctrl2 is None:
            return [(1 - u) ** 2 * a + 2 * u * (1 - u) * ctrl + u ** 2 * b for u in us]
        return [(1 - u) ** 3 * a + 3 * (1 - u) ** 2 * u * ctrl + 3 * (1 - u) * u ** 2 * ctrl2 + u ** 3 * b for u in us]
    fine = np.array(at(np.linspace(0.0, 1.0, 200)))
    length = float(np.sum(np.linalg.norm(np.diff(fine, axis=0), axis=1)))
    n = max(n, int(math.ceil(length / PATH_SAMPLE_CM)) + 1)              # a long carry is sampled as finely as a short one
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(fine, axis=0), axis=1))])
    us = np.interp(np.linspace(0.0, s[-1], n), s, np.linspace(0.0, 1.0, 200))   # evenly along the path, not the parameter
    return at(us)


MOVE_RELAX = "slerp"                                     # how a carried paw's fingers turn in the air (_moving)


def _slerp(a, b, u):
    a, b = unit(a), unit(b)
    w = math.acos(max(-1.0, min(1.0, float(a @ b))))
    if w < 1e-6:
        return a
    return unit((math.sin((1 - u) * w) * a + math.sin(u * w) * b) / math.sin(w))


def _moving(targets_from, targets_to, path, shoulder):
    """A paw carried along path (its knuckle line), from targets_from's fingers and palm to targets_to's. In the air
    between, the wrist relaxes: the fingers bend toward the reach from the shoulder (a quadratic Bezier in direction),
    and only the two ends are set poses."""
    _fit_inplace(targets_from, shoulder)
    _fit_inplace(targets_to, shoulder)
    out = []
    ends = (targets_from, targets_to) if (targets_from.get("refit") or targets_to.get("refit")) else None
    for u, c in zip(np.linspace(0.0, 1.0, len(path)), path):
        relaxed = unit(c - shoulder)
        if MOVE_RELAX == "slerp":                                       # straight from the one pose's fingers to the other's
            f = _slerp(targets_from["F"], targets_to["F"], u)
        else:
            f = unit((1 - u) ** 2 * targets_from["F"] + 2 * u * (1 - u) * relaxed + u ** 2 * targets_to["F"])
        n = unit((1 - u) * targets_from["N"] + u * targets_to["N"])
        row = {"C": c, "F": f, "N": unit(n - (n @ f) * f), "relax": RELAX_AIR * math.sin(math.pi * u)}
        if ends is not None:
            row.update(ends=ends, u=float(u))
        out.append(row)
    return out


RELAX_AIR = 0.85                                         # how far a carried paw's wrist relaxes toward its forearm, mid-air


def _hero_rz(sh):
    """The hero's facing frame (columns: ahead, right, up) from its two shoulders."""
    right = np.asarray(sh["R"], float) - np.asarray(sh["L"], float)
    right = unit([right[0], right[1], 0.0])
    return np.stack([np.array([right[1], -right[0], 0.0]), right, UP], 1)


def _fit(t, shoulder, rz, side, poles=None):
    """A contact's fingers settled within its freedom (the plane square to its palm's normal: a palm or fingertips on
    a surface, a grip about its part, a claw from above), toward the forearm the two-bone solve gives under the pole
    of POLES that bends the wrist least. The contact point stays; a fingertip steady's knuckles swing about its tips.
    Done when an action is built, so a carry runs between the settled poses."""
    plane = t.get("plane")
    if plane is None:
        return t
    best, best_bend = None, None
    for pole in (poles or POLES[side]):
        tt = dict(t)
        for _ in range(4):
            w = tt["C"] - tt["F"] * WRIST_BACK
            try:
                e = TPR.two_bone(shoulder, w, UPPER_ARM_CM, FOREARM_CM, rz @ unit(pole))
            except ValueError:
                break
            fa = unit(w - e)
            fp = fa - (fa @ plane) * plane
            if np.linalg.norm(fp) < 1e-6:
                break
            f = unit(fp)
            n = t["N"] - (t["N"] @ f) * f
            tt.update(F=f, N=unit(n) if np.linalg.norm(n) > 1e-9 else t["N"])
            if "pivot" in t:
                tt["C"] = t["pivot"] - f * t["pivot_back"]
        w = tt["C"] - tt["F"] * WRIST_BACK
        try:
            e = TPR.two_bone(shoulder, w, UPPER_ARM_CM, FOREARM_CM, rz @ unit(pole))
        except ValueError:
            continue
        bend = math.degrees(math.acos(max(-1.0, min(1.0, float(unit(w - e) @ tt["F"])))))
        # Within the wrist's limit, prefer an elbow not far below the knuckles: working at chest height the elbow
        # rises, and a low elbow's forearm climbs through the bench under the work.
        cost = bend + FIT_LOW_ELBOW * max(0.0, (tt["C"][2] - FIT_ELBOW_DROP_CM) - e[2]) + (1000.0 if bend > WRIST_MAX else 0.0)
        if best_bend is None or cost < best_bend:
            best, best_bend = tt, cost
    out = dict(best if best is not None else t)
    out.pop("plane", None)
    return out


_CTX = {}                                                # the hero's shoulders and facing while actions() builds
FIT_LOW_ELBOW = 1.0                                      # deg of wrist bend traded per cm of elbow below FIT_ELBOW_DROP_CM
FIT_ELBOW_DROP_CM = 12.0


def _fit_with(t, shoulder, poles):
    """Settle a contact in place under a phase's own pole set (poles: {"L": [...], "R": [...]})."""
    if "plane" not in t or not _CTX:
        return
    side = "L" if np.allclose(shoulder, _CTX["sh"]["L"]) else "R"
    fitted = _fit(t, np.asarray(shoulder, float), _CTX["rz"], side, poles=poles[side])
    t.clear()
    t.update(fitted)


def _fit_inplace(t, shoulder):
    """Settle a contact target where it stands (every phase and carry holding it sees the same settled pose). A "refit"
    contact keeps its freedom: settled here for a default, it is settled again under each pole a gate tries (_arm)."""
    if "plane" not in t or not _CTX:
        return
    if t.get("refit"):
        if not t.get("_settled"):
            side = "L" if np.allclose(shoulder, _CTX["sh"]["L"]) else "R"
            fitted = _fit(t, np.asarray(shoulder, float), _CTX["rz"], side)
            t.update(F=fitted["F"], N=fitted["N"], C=fitted["C"], _settled=True)
        return
    side = "L" if np.allclose(shoulder, _CTX["sh"]["L"]) else "R"
    fitted = _fit(t, np.asarray(shoulder, float), _CTX["rz"], side)
    t.clear()
    t.update(fitted)


def _fit_seq(targets, shoulder, poles=None):
    """Settle a continuous path of contacts (a guide running along a strip, say) under ONE pole of POLES, the one whose
    worst wrist bend over the path is least, so the fingers turn smoothly along it (one pole per sample made the
    elbow jump between samples)."""
    if not targets or "plane" not in targets[0] or not _CTX:
        return
    side = "L" if np.allclose(shoulder, _CTX["sh"]["L"]) else "R"
    best, best_worst = None, None
    for pole in (poles or POLES)[side]:
        fitted = [_fit(tg, np.asarray(shoulder, float), _CTX["rz"], side, poles=[pole]) for tg in targets]
        worst = 0.0
        for tg in fitted:
            w = tg["C"] - tg["F"] * WRIST_BACK
            try:
                e = TPR.two_bone(shoulder, w, UPPER_ARM_CM, FOREARM_CM, _CTX["rz"] @ unit(pole))
            except ValueError:
                worst = 999.0
                break
            worst = max(worst, math.degrees(math.acos(max(-1.0, min(1.0, float(unit(w - e) @ tg["F"]))))))
        if best_worst is None or worst < best_worst:
            best, best_worst = fitted, worst
    for tg, f in zip(targets, best):
        tg.clear()
        tg.update(f)


def _relax(shoulder, t, rz, pole):
    """A carried paw's target with its wrist relaxed: its fingers turned toward its actual forearm (from the two-bone
    solve under pole) by its "relax" weight, the knuckle line where the path puts it. A contact sets its own fingers
    (relax 0); in the air the wrist follows the forearm, as a hand does, instead of an imposed blend."""
    r = float(t.get("relax", 0.0))
    plane = None                                                # contacts are fitted when built (_fit)
    if r <= 0.0:
        return t
    tt = dict(t)
    for _ in range(3):
        w = tt["C"] - tt["F"] * WRIST_BACK
        try:
            e = TPR.two_bone(shoulder, w, UPPER_ARM_CM, FOREARM_CM, rz @ unit(pole))
        except ValueError:
            return tt
        fa = unit(w - e)
        if plane is not None:                                   # a contact: the fingers turn within its freedom
            fp = fa - (fa @ plane) * plane
            if np.linalg.norm(fp) < 1e-6:
                return tt
            f = unit(fp)
        else:
            f = _slerp(t["F"], fa, r)
        n = t["N"] - (t["N"] @ f) * f
        tt.update(F=f, N=unit(n) if np.linalg.norm(n) > 1e-9 else t["N"])
        if "pivot" in t:                                        # fingertips stay put: the knuckles swing about them
            tt["C"] = t["pivot"] - f * t["pivot_back"]
    return tt


def _move(a, b, shoulder, lift=6.0):
    return _moving(a, b, _arc(a["C"], b["C"], lift), shoulder)


def _surface_path(lc, az_deg, z_from, z_to, off, n=33):
    """A stroke along the paper at azimuth az_deg, from z_from to z_to (lantern frame), off cm out from the paper all
    the way: sampled from the paper's own profile (paper_r). Chords between the nine seam sockets cut inside the curved
    shoulders by up to 0.6 cm, so the brush went through the washi there (found as an occluded contact)."""
    a = math.radians(az_deg)
    zs = np.linspace(z_from, z_to, n)
    return [np.asarray(lc, float) + [(float(B.paper_r(z)) + off) * math.cos(a), (float(B.paper_r(z)) + off) * math.sin(a), z]
            for z in zs]


def _phase(name, kind, left, right, state, works, poles=None, tiers=None):
    """A phase (contacts) or a transition (carries) of an action; poles, if given, replace POLES for its elbows. With
    tiers (pole sets in order of preference), a paw takes the first set under which it passes every gate, and only if
    none does the best of all: a raised elbow serves where the natural ones fail, not wherever its margin is wider."""
    ph = {"phase": name, "kind": kind, "L": left, "R": right, "state": state, "works": frozenset(works)}
    if poles is not None:
        ph["poles"] = poles
    if tiers is not None:
        ph["pole_tiers"] = tiers
    return ph


RIB_TIERS = [POLES, POLES_RAISED]
RIB_WORKS = {"SM_B09_Form", "SM_B09_StripStock", "SM_B09_StripQuiver"} | {f"SM_B09_Hoop{k}" for k in range(1, 7)}
LANTERN_WORKS = {"SM_B09_Form"} | {f"SM_B09_Hoop{k}" for k in range(1, 7)} | {f"SM_B09_Washi{k}" for k in range(1, 5)}


def _front_strip(sk):
    """The strip a paw takes next: the nearest end of the rack's top layer (StripStock), the strips lying along +X with
    their ends toward the hero (b09_workshop_craft.station_parts)."""
    return np.asarray(sk["StripStock"][0], float)


def actions(i, sh=None):
    """[(action, [phase records])]: each paw's targets per sample. The contacts are the work's; each paw's fingers and
    palm follow the reach from its shoulder (sh, from shoulders(); the craft stand's by default), as a paw does from
    wherever the hero stands in the working region."""
    _, sk, _, _ = B.station_parts(i)
    sock = lambda n: np.asarray(sk[n][0], float)  # noqa: E731
    if sh is None:
        sh, _ = shoulders(B.craft_stand(i))
    L, R = sh["L"], sh["R"]
    _CTX.clear()
    _CTX.update(sh=sh, rz=_hero_rz(sh))
    out = []
    if i == 0:
        lc = B.lantern_centre(0)
        strip = _front_strip(sk)
        for k, (z, r) in enumerate(zip(B.hoop_z(), B.hoop_r()), 1):
            # The two paws work the hooked end in turn (side by side they met: at press 185 and hook 180 the palms came
            # within 0.00-0.50 cm, and spreading the points to 190/168 pushed the lowest hoop out of 21:9). The left paw
            # steadies the form at its front-left (WindSteady) while the right paw hooks the strip's end at the front;
            # then the left comes in to press the hooked strip (WindPress) as the right slides out along the free strip
            # to the guide (WindGuide), and holds it there while the form turns and the strip draws through its grip.
            def on_form(socket):
                n_ = np.asarray(sk[socket][1], float)
                # The palm lies along the form's surface, tilted with its profile; the strip's face is upright, so the
                # palm stands off its edge by half the strip's width times the tilt.
                tilt = abs(float(n_[2])) / max(1e-9, float(np.linalg.norm(n_[:2])))
                t_ = press(sock(socket) + n_ * (B.HOOP_W / 2) * tilt, n_, L, unit(np.cross(n_, UP)))
                t_["refit"] = True                                     # settled under each pole the gates try
                _fit_inplace(t_, L)
                return t_
            presst = on_form(f"WindPress{k}")
            # While the right paw hooks the strip the left waits off the form at its front-left (WindSteady), its hand
            # as it will press (a flat palm on the form there bent the wrist past 75 deg from the far right stands).
            n_w = np.asarray(sk[f"WindSteady{k}"][1], float)
            c_w = sock(f"WindSteady{k}") + n_w * (PAD_OFF + B.RIB["wait_off_cm"])
            steadyt = {"C": c_w, "F": presst["F"], "N": presst["N"], "P": c_w}       # it works nothing while it waits
            # The front strip pinched from above at its end (a grip's palm, facing the ends, cut 0.4 cm into the stock).
            take = claw(strip, R)
            la = math.radians(B.RIB["leave_az_deg"])
            leave = lc + [r * math.cos(la), r * math.sin(la), z]             # where the strip leaves the form
            tang = np.array([math.sin(la), -math.cos(la), 0.0])             # its heading off the form, to the right
            onto = -np.array([math.cos(la), math.sin(la), 0.0])             # from the hero's side onto the form
            # The paw works the strip's outer face (hoop_r is its centre line: seen obliquely, the strip's own half
            # thickness hid a centre-line point from the eye).
            leave = leave - onto * (B.HOOP_T / 2)
            hook = grip(leave, onto, R, FWD, off=B.RIB["grip_off_cm"])        # the knuckles off the strip, toward the hero
            guide = grip(leave + tang * B.RIB["guide_cm"], onto, R, FWD, off=B.RIB["grip_off_cm"])   # held while the strip draws through
            hook["refit"] = guide["refit"] = True
            # The left paw's move from steadying to pressing follows the form round, PAD_OFF off it (a chord cut it).
            a0 = math.radians(B.RIB["steady_az_deg"])
            a1 = math.radians(B.RIB["press_az_deg"])
            # Its knuckles keep their offset off the form's profile at every height between (the form is wider toward
            # its middle), lifting 0.4 cm at the middle of the move.
            off0 = float(np.linalg.norm((steadyt["C"] - lc)[:2])) - float(B.profile_r(steadyt["C"][2] - lc[2]))
            off1 = float(np.linalg.norm((presst["C"] - lc)[:2])) - float(B.profile_r(presst["C"][2] - lc[2]))
            round_path = []
            for u in np.linspace(0.0, 1.0, SAMPLES):
                zz = steadyt["C"][2] + (presst["C"][2] - steadyt["C"][2]) * u - lc[2]
                rr = float(B.profile_r(zz)) + off0 + (off1 - off0) * u + 0.4 * math.sin(math.pi * u)
                aa = a0 + (a1 - a0) * u
                round_path.append(lc + [rr * math.cos(aa), rr * math.sin(aa), zz])
            # The carry lifts the strip up and out of the stock, then comes round the form's right to the notch from
            # the hero's side (straight, the palm passed down through the stock and met the form's face).
            _fit_inplace(take, R)
            out_of = take["C"] + np.array([0.0, -B.RIB["carry_out_cm"], B.RIB["carry_lift_cm"]])   # up and toward the form:
            # pulled toward the hero, the right arm folded past 145 deg at the near right stands turned left
            into = hook["C"] + np.array([-B.RIB["carry_bow_cm"], 0.6 * B.RIB["carry_bow_cm"], 1.0])
            carry = _moving(take, hook, _bezier(take["C"], out_of, hook["C"], ctrl2=into), R)
            held, hooked, bend = {"hoop": k, "strip": "held"}, {"hoop": k, "strip": 0.0}, {"hoop": k, "strip": "bend"}
            out.append((f"wind hoop {k}", [
                _phase("take a strip", "phase", [steadyt], [take], held, RIB_WORKS, tiers=RIB_TIERS),
                _phase("carry it to the notch", "transition", _hold(steadyt), carry, held, RIB_WORKS),
                _phase("hook its end", "phase", [steadyt], [hook], held, RIB_WORKS, tiers=RIB_TIERS),
                _phase("press the hooked strip; slide to the guide", "transition",
                       _moving(steadyt, presst, round_path, L),
                       _moving(hook, guide, _line(hook["C"], guide["C"]), R), hooked, RIB_WORKS),
                _phase("wind (HeldMs 0-800)", "phase", _hold(presst), _hold(guide), bend, RIB_WORKS, tiers=RIB_TIERS),
            ]))
    elif i == 1:
        # The paste (Coordination 268), on the tilting cradle: the left paw lays the next complete sheet against the
        # frame and holds it by its fingertips; the right brush pastes the seam, rim line to rim line, its bristle edge
        # square along each rim line. The frame stands with the worked seam toward the hero for every panel.
        A = B.paste_axes()
        zs = np.linspace(-B.LANTERN_H / 2, B.LANTERN_H / 2, 33)
        if not B.PASTE["stroke_up"]:
            zs = zs[::-1]
        path = B.paste_frame(np.stack([-(B.paper_r(zs) + 0.6), np.zeros_like(zs), zs], 1))
        slope = np.gradient(B.paper_r(zs), zs)
        normals = [unit(A @ np.array([-1.0, 0.0, -float(g)])) for g in slope]
        across = A @ np.array([0.0, 1.0, 0.0])                   # round the frame at the seam
        h = B.LANTERN_H / 2
        sc = B.PASTE["square_cm"]
        sq = B.PASTE["square"] * np.maximum(np.clip(1.0 - (zs + h) / sc, 0.0, 1.0), np.clip(1.0 - (h - zs) / sc, 0.0, 1.0))
        strokes = [brush(qp, nq, R, tilt=B.PASTE["stroke_tilt"], width=B.PASTE_BRUSH_W, across=across, square=float(w))
                   for qp, nq, w in zip(path, normals, sq)]
        hold = steady(sock("SheetHold"), np.asarray(sk["SheetHold"][1], float), L, A @ np.array([0.0, 0.0, 1.0]))
        sheet = grip(sock("SheetTake"), FWD, L, FWD + UP)          # by the next sheet's near end, on the rack
        dip = brush(sock("PasteDip"), UP, R, tilt=0.4, width=B.PASTE_BRUSH_W)
        works = LANTERN_WORKS | {f"SM_B09_WashiSheet{j}" for j in range(1, 5)} | {"SM_B09_PastePot"}
        ready = {"panel": 1, "sheet": "rack", "rims": "rest", "brush": "paw"}
        laid = {"panel": 1, "sheet": "laid", "rims": "rest", "brush": "paw"}
        out.append(("paste a panel", [
            _phase("take the next sheet; dip the brush", "phase", [sheet], [dip], ready, works),
            _phase("lay the sheet on the frame; to the seam's lower end", "transition", _move(sheet, hold, L, 4.0),
                   _move(dip, strokes[0], R, 3.0), {**laid, "sheet": "paw"}, works),
            _phase("paste the seam, rim line to rim line (HeldMs 0-1500)", "phase", _hold(hold, len(strokes)), strokes, laid, works),
        ]))
        # The rims step: the bottom rim is on the frame from the start (its rest is its seat). The left paw takes the
        # top rim from its peg and seats it on the upper mouth, pads on its face; the right paw steadies the frame.
        rc = sock("RimTopRest")
        take_t = press(rc + np.array([-(B.LANTERN_RIM_R - 0.4), 0.0, B.RIM_H / 2]), UP, L, FWD)   # pads on its near rim
        seat_c = sock("RimTopSeat")
        sd = A @ np.array([math.cos(math.radians(200.0)), math.sin(math.radians(200.0)), 0.0])
        seat_t = press(seat_c + sd * B.LANTERN_RIM_R + A[:, 2] * (B.RIM_H / 2), A[:, 2], L, FWD)
        s_az, s_s = B.PASTE["rim_steady"]
        st_p = B.paste_frame([[float(B.paper_r(s_s)) * math.cos(math.radians(s_az)), float(B.paper_r(s_s)) * math.sin(math.radians(s_az)), s_s]])[0]
        st_n = unit(A @ np.array([math.cos(math.radians(s_az)), math.sin(math.radians(s_az)), 0.0]))
        frame_steady = steady(st_p + st_n * 0.1, st_n, R, A[:, 2])
        works_r = LANTERN_WORKS | {"SM_B09_RimTop", "SM_B09_RimBottom"}
        done = {"panel": 5, "sheet": "none", "rims": "rest", "brush": "pot"}
        out.append((f"seat the rims (a press clip, at most {CLIP_MAX_MS['rims']} ms)", [
            _phase("take the top rim; steady the frame", "phase", [take_t], [frame_steady], done, works_r),
            _phase("to the upper mouth", "transition", _move(take_t, seat_t, L, 6.0), _hold(frame_steady), {**done, "rims": "paws"}, works_r),
            _phase("seat it", "phase", [seat_t], [frame_steady], {**done, "rims": "paws"}, works_r),
        ]))
    elif i == 2:
        # The oil: a representative finishing stroke on a prepared batch lantern, already coated but for one remaining
        # swath (Coordination 268). The brush dips in the dish by the lantern's lower right, comes to the top rim line,
        # and finishes the swath down to the belly; the left paw steadies the hanging lantern on its upper left.
        lc = B.lantern_centre(2)
        sw = B.OIL_SWATH
        path = _surface_path(lc, sw["az_deg"], sw["s_cm"][0], sw["s_cm"][1], sw["offset_cm"])
        a = math.radians(sw["az_deg"])
        zs = np.linspace(sw["s_cm"][0], sw["s_cm"][1], len(path))
        slope = np.gradient(B.paper_r(zs), zs)
        normals = [unit([math.cos(a), math.sin(a), -float(g)]) for g in slope]
        # The left palm lies on the lantern's upper left, its fingers turned OIL["steady_fingers_deg"] in the surface from
        # straight up toward the hero's right (the forearm must stay clear of the lantern's bulge below the palm).
        n_st = np.asarray(sk["LanternSteady"][1], float)
        al, th = math.radians(B.OIL["steady_az_deg"]), math.radians(B.OIL["steady_fingers_deg"])
        up_t = unit(UP - (UP @ n_st) * n_st)
        side_t = unit(np.cross(n_st, up_t))
        steady_t = globals()[B.OIL.get("steady_kind", "steady")](sock("LanternSteady"), n_st, L, math.cos(th) * up_t + math.sin(th) * side_t)
        dip = brush(sock("OilDip"), UP, R, tilt=B.OIL_DIP_TILT, width=B.OIL_BRUSH_W)
        # Against the top rim line the bristle edge lies square along it, round the lantern; it relaxes toward the hand
        # over the next OIL_SWATH["square_cm"].
        across = np.array([-math.sin(a), math.cos(a), 0.0])
        sq = sw["square"] * np.clip(1.0 - (sw["s_cm"][0] - zs) / sw["square_cm"], 0.0, 1.0)
        strokes = [brush(q, nq, R, tilt=sw["tilt"], width=B.OIL_BRUSH_W, across=across, square=float(w))
                   for q, nq, w in zip(path, normals, sq)]
        works = (LANTERN_WORKS - {"SM_B09_Form"}) | {"SM_B09_RimTop", "SM_B09_RimBottom", "SM_B09_OilDish"}
        state = {"brush": "paw"}
        out.append(("finish the remaining swath", [
            _phase("dip the brush; steady the lantern", "phase", [steady_t], [dip], state, works),
            _phase("to the swath's top, at the top rim line", "transition", _hold(steady_t),
                   _move(dip, strokes[0], R, B.OIL["carry_lift_cm"]), state, works),
            _phase("finish the swath (HeldMs 0-1500)", "phase", _hold(steady_t, len(strokes)), strokes, state, works),
        ]))
    else:
        wrap = sock("WrapSpot")
        core_top = float(B.shell("core").verts[:, 2].max())         # the fuse stub's top, over the core's centre
        neck_top = float(B.shell("wrapped").verts[:, 2].max())      # the tied neck's top, over the shell's centre
        # The left paw holds the shell on the paper from its left, the right paw twists its neck from its right: both
        # palms upright against the ball (palm_on_ball), their lower edges over the paper.
        lift = PALM_HALF[1] - B.SHELL["wrapped_cm"] / 2 + 0.3
        half = B.SHELL["wrapped_cm"] / 2
        hold = palm_on_ball(wrap, half, [0.0, 1.0, 0.0], L, FWD, lift)
        twist = palm_on_ball(wrap, half, [0.0, -1.0, 0.0], R, FWD, lift)
        hold_poles = {"L": POLES["L"] + POLES_RAISED["L"], "R": POLES["R"]}
        if _CTX:                                                   # the hold settles under the poles its phases use
            fitted = _fit(hold, L, _CTX["rz"], "L", poles=hold_poles["L"])
            hold.clear()
            hold.update(fitted)
        for k in (1, 2, 3):
            core = claw(sock(f"ShellCore{k}") + UP * core_top, R)
            seat = claw(sock(f"ShellSeat{k}") + UP * neck_top, L)  # by its neck, into the cup
            works = {f"SM_B09_ShellCore{k}", f"SM_B09_ShellWrapped{k}", "SM_B09_ShellWrapping", "SM_B09_ShellTray",
                     "SM_B09_WrapPaper", "SM_B09_ShellRack"}
            # What the bench shows as the clip runs: cores k..3 in the tray until the right paw takes core k; shells
            # 1..k-1 seated; shell k on the paper while it is wrapped, then in its seat.
            later, before = tuple(range(k + 1, 4)), tuple(range(1, k))
            tray = {"cores": tuple(range(k, 4)), "seated": before, "wrapping": False}
            carried = {"cores": later, "seated": before, "wrapping": False}
            wrapping = {"cores": later, "seated": before, "wrapping": True}
            seated = {"cores": later, "seated": before + (k,), "wrapping": False}
            out.append((f"wrap and seat shell {k} (a press clip, at most {CLIP_MAX_MS['shell']} ms)", [
                _phase("take a core", "phase", [hold], [core], tray, works, poles=hold_poles),
                _phase("to the paper", "transition", _hold(hold), _move(core, twist, R, 5.0), carried, works),
                _phase("wrap and twist", "phase", [hold], [twist], wrapping, works, poles=hold_poles),
                _phase("to the rack (the right paw lets go)", "transition", _move(hold, seat, L, 5.0), _hold(twist), carried, works),
                _phase("seat it", "phase", [seat], [twist], seated, works),
            ]))
        # The inspection starts where shell 3's clip ends: the left paw over the third shell's neck (its last work), the
        # right paw at the paper. The left paw's pads pass along the seated shells' fuse cords from shell 3 to shell 1
        # (the cups' row is straight), feeling each tip; the right paw waits. (Weapon 7's own touch-hole fuse could not
        # stand in reach of the far corners with the tube clear of the arms: weapon_rest.)
        tips = [sock(f"ShellSeat{k}") + UP * neck_top for k in (3, 1)]
        along = [claw(p, L) for p in _line(tips[0], tips[1])]
        _fit_seq(along, L, POLES_OVER)
        works = {"SM_B09_ShellWrapped1", "SM_B09_ShellWrapped2", "SM_B09_ShellWrapped3", "SM_B09_ShellRack"}
        done = {"cores": (), "seated": (1, 2, 3), "wrapping": False}
        out.append((f"check the fuses (a press clip, at most {CLIP_MAX_MS['inspect']} ms)", [
            _phase("along the fuse cords, shell 3 to shell 1", "phase", along, _hold(twist, len(along)), done, works,
                   poles={"L": POLES_OVER["L"], "R": POLES["R"]}),
        ]))
    for _, steps in out:                                      # settle any contact no carry has settled
        for ph in steps:
            for side in ("L", "R"):
                for tg in ph[side]:
                    _fit_inplace(tg, sh[side])
    _CTX.clear()
    return out


# --- The scene the arms must clear ----------------------------------------------------------------------------------
_PROPS = {}


def _bend_ms(state, u):
    return u * B.BEND_MS if state.get("strip") == "bend" else 0.0


def props(i, state, u=0.0):
    """The station's meshes in a phase's state (station frame). The rib form's follows the bend: hoops 1..k-1 wound, the
    form turned for them, and hoop k as the state has it: in the paw ("held", not a prop), hooked (0.0), or at the
    flex stage root shows at HeldMs = u * BEND_MS ("bend"), with the needle there."""
    parts, sk, _, _ = B.station_parts(i)
    sock = lambda n: np.asarray(sk[n][0], float)  # noqa: E731
    meshes = list(parts)
    if i == 0:
        k, strip = state["hoop"], state["strip"]
        ms = _bend_ms(state, u)
        flex = B.FLEX_STAGES[B.flex_stage(ms)] if strip == "bend" else 0.0 if strip == "held" else float(strip)
        yaw = B.form_yaw_deg(k - 1, flex)
        rib = [B.form()] + [B.hoop(j) for j in range(1, k)]
        if strip != "held":
            rib.append(B.hoop(k, flex) if flex < 1.0 else B.hoop(k))
        meshes += [B.Mesh(m.name.split("_Flex")[0], B.to_station(m.verts, yaw, B.lantern_centre(0)), m.tris, m.slot) for m in rib]
        meshes.append(B.needle_at(ms))
    elif i == 1:
        st = {m.name: m for m, _, _ in B.state_meshes(1)}
        panel = state["panel"]
        on = list(B.PASTE_ORDER[:panel - 1]) + ([B.PASTE_ORDER[panel - 1]] if state.get("sheet") == "laid" and panel <= 4 else [])
        meshes += [B.Mesh(f"SM_B09_Washi{k}", B.paste_frame(B.gore(k).verts, panel), B.gore(k).tris, "M_B09_Washi") for k in on]
        left = [j for j in range(1, 5) if j >= panel + (0 if state.get("sheet") == "rack" else 1)]
        meshes += [PC.placed(st[f"SM_B09_WashiSheet{j}"], sk[f"WashiSheet{j}"]) for j in left]
        rb = sk["RimBottomSeat"]
        meshes.append(PC.placed(B.rim("Bottom"), rb))              # fitted to the frame from the start
        if state["rims"] == "rest":
            meshes.append(PC.placed(B.rim("Top"), sk["RimTopRest"]))
        if state["brush"] == "pot":
            meshes.append(PC.placed(st["SM_B09_PasteBrush"], sk["BrushRest"]))
    elif i == 2:
        meshes += [m.moved(sock("LanternHang") - B.hang_point()) for m in B.lantern("finished")]
    else:
        meshes.append(PC.weapon7_placed())
        meshes += [B.shell("wrapped").moved(sock(f"ShellSeat{k}"), name=f"SM_B09_ShellWrapped{k}") for k in state["seated"]]
        meshes += [B.shell("core").moved(sock(f"ShellCore{k}"), name=f"SM_B09_ShellCore{k}") for k in state["cores"]]
        if state["wrapping"]:
            meshes.append(B.shell("wrapped").moved(sock("WrapSpot"), name="SM_B09_ShellWrapping"))
    return meshes


def _scene(i, state, u, works):
    """(every prop merged, the props the paws do not work, the worked props), cached by state."""
    key = (i, tuple(sorted(state.items())), round(_bend_ms(state, u), 3), works)
    if key not in _PROPS:
        scene = props(i, state, u)
        hard = [m for m in scene if m.name not in works]
        soft = [m for m in scene if m.name in works]
        _PROPS[key] = tuple(B.merge(n, ms) if ms else None for n, ms in (("all", scene), ("hard", hard), ("worked", soft)))
    return _PROPS[key]


# --- The solve and the gates ---------------------------------------------------------------------------------------
def shoulders(stand, yaw_deg=0.0, eye_z=STANDING_EYE_Z):
    a = math.radians(yaw_deg)
    rz = np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
    eye = np.array([stand[0], stand[1], 0.0]) + rz @ np.array([B.EYE[0], B.EYE[1], 0.0]) + [0.0, 0.0, eye_z]
    return {"R": eye + rz @ SHOULDER_FROM_EYE, "L": eye + rz @ (SHOULDER_FROM_EYE * [1.0, -1.0, 1.0])}, rz


def solve(side, shoulder, target, rz, pole):
    """One paw with the elbow toward pole (the hero's frame): (elbow, wrist, a dict of gate values, failure or None)."""
    w = wrist_of(target)
    d = float(np.linalg.norm(w - shoulder))
    gate = {"reach_pct": round(100.0 * d / (UPPER_ARM_CM + FOREARM_CM), 2)}
    try:
        e = TPR.two_bone(shoulder, w, UPPER_ARM_CM, FOREARM_CM, rz @ unit(pole))
    except ValueError:
        return None, w, gate, f"reach {gate['reach_pct']} % of the arm (at most {100 * TPR.REACH_MAX:g} %)"
    u, f = unit(shoulder - e), unit(w - e)
    gate["elbow_flex_deg"] = round(180.0 - math.degrees(math.atan2(np.linalg.norm(np.cross(u, f)), float(u @ f))), 2)
    gate["wrist_deg"] = round(math.degrees(math.atan2(np.linalg.norm(np.cross(f, target["F"])), float(f @ target["F"]))), 2)
    if gate["elbow_flex_deg"] > ELBOW_MAX:
        return e, w, gate, f"elbow flexion {gate['elbow_flex_deg']}"
    if gate["wrist_deg"] > WRIST_MAX:
        return e, w, gate, f"wrist bend {gate['wrist_deg']}"
    return e, w, gate, None


def _frame_z(d):
    """An orthonormal frame (rows u, v, d) with its third axis along d."""
    d = unit(d)
    u = unit(np.cross(d, [0.0, 0.0, 1.0] if abs(d[2]) < 0.9 else [1.0, 0.0, 0.0]))
    return np.stack([u, np.cross(d, u), d])


def _cone(name, a, b, ra, rb):
    """A closed round cone from a (radius ra) to b (radius rb)."""
    length = float(np.linalg.norm(b - a))
    m = B.revolve(name, [(0.0, 0.0), (0.0, ra), (length, rb), (length, 0.0)], "M_B09_Iron", n_az=12)
    return B.Mesh(name, np.asarray(a, float) + m.verts @ _frame_z(b - a), m.tris, m.slot)


def _palm(t):
    """The palm's stand-in: an ellipsoid PALM_HALF, from the carpus to just past the knuckles, oriented by the target."""
    f, n = t["F"], t["N"]
    m = B.sphere("palm", 1.0, "M_B09_Iron", n=8)
    axes = np.stack([f, np.cross(n, f), n])
    return B.Mesh("palm", (t["C"] - f * PALM_MID) + (m.verts * PALM_HALF) @ axes, m.tris, m.slot)


def _sleeves(shoulder, e, w):
    f = unit(w - e)
    return B.merge("arm", [_cone("upper", shoulder, e, SLEEVE_R["upper"], SLEEVE_R["upper"]),
                           _cone("fore", e, w - f * 2.0, SLEEVE_R["fore"], SLEEVE_R["cuff"])])


_BOUNDS = {}


def tri_bounds(m):
    """Each triangle's bounds of a (cached, unchanging) scene mesh."""
    hit = _BOUNDS.get(id(m))
    if hit is None or hit[0] is not m:
        T = m.verts[m.tris]
        hit = (m, T.min(1), T.max(1))
        _BOUNDS[id(m)] = hit
    return hit[1], hit[2]


def near_tris(a, b, limit):
    """b's triangles whose bounds come within limit of a's bounds (a moving part against a cached scene)."""
    lo, hi = a.verts.min(0), a.verts.max(0)
    blo, bhi = tri_bounds(b)
    return b.tris[np.all((blo <= hi + limit) & (bhi >= lo - limit), 1)]


SEP_LIMIT_CM = 3.0                                       # clearances are measured to here; beyond, reported as this


def _sep(a, b, limit=SEP_LIMIT_CM):
    if a is None or b is None:
        return limit
    tris = near_tris(a, b, limit)
    if not len(tris):
        return limit
    r = MC.exact_separation(a.verts, a.tris, b.verts, tris, limit=limit)
    return limit if r["separation_m"] is None else float(r["separation_m"])


def _torso_hit(stand, e, shoulder, rz):
    x, y, _ = rz.T @ (np.asarray(e, float) - [stand[0], stand[1], 0.0])     # the elbow in the hero's facing frame
    return TORSO["back"] <= x <= TORSO["front"] and -TORSO["half"] <= y <= TORSO["half"] and e[2] < shoulder[2] + 5.0


def _u(ph, k):
    n = max(len(ph["L"]), len(ph["R"]))
    return k / (n - 1) if n > 1 else 0.0


def _settled_for(t, shoulder, rz, side, pole):
    """A target as it stands under pole: a refit contact's fingers settled within its freedom toward this pole's
    forearm; a carry between refit contacts turning (slerp) between their poses so settled; anything else unchanged."""
    if t.get("refit") and "plane" in t:
        return _fit(t, shoulder, rz, side, poles=[pole])
    if "ends" in t:
        a_, b_ = (_fit(e, shoulder, rz, side, poles=[pole]) if (e.get("refit") and "plane" in e) else e for e in t["ends"])
        f = _slerp(a_["F"], b_["F"], t["u"])
        n = unit((1 - t["u"]) * a_["N"] + t["u"] * b_["N"])
        out = {k_: v for k_, v in t.items() if k_ not in ("ends", "u")}
        out.update(F=f, N=unit(n - (n @ f) * f))
        return out
    return t


def _arm(i, stand, sh, rz, ph, k, side, pole, clearance):
    """One paw at sample k of phase ph under pole: (elbow, wrist, target, gate values, failures, its arm's mesh)."""
    t = _settled_for(ph[side][min(k, len(ph[side]) - 1)], sh[side], rz, side, pole)
    t = _relax(sh[side], t, rz, pole)
    e, w, gate, why = solve(side, sh[side], t, rz, pole)
    if why:
        return None, w, t, gate, [why], None
    fails = ["elbow inside the torso"] if _torso_hit(stand, e, sh[side], rz) else []
    if not clearance:
        return e, w, t, gate, fails, None
    allm, hard, soft = _scene(i, ph["state"], _u(ph, k), ph["works"])
    sleeves, palm = _sleeves(sh[side], e, w), _palm(t)
    s_all, s_hard, s_soft = _sep(sleeves, allm), _sep(palm, hard), _sep(palm, soft)
    gate.update(sleeve_cm=round(s_all, 3), palm_cm=round(s_hard, 3), palm_worked_cm=round(s_soft, 3))
    if s_all < CLEAR_CM:
        fails.append(f"sleeve {s_all:.2f} cm from a prop")
    if s_hard < CLEAR_CM:
        fails.append(f"palm {s_hard:.2f} cm from a part it does not work")
    if s_soft < THROUGH_CM:
        fails.append("palm into a part it works")
    return e, w, t, gate, fails, B.merge("arm", [sleeves, palm])


def _pole_for(i, stand, sh, rz, ph, side, clearance, every, keyed=False):
    """The pole (of POLES) under which a phase's samples pass every gate for this paw, with the most margin."""
    n = max(len(ph["L"]), len(ph["R"]))
    if "pole_tiers" in ph:
        best_any = None
        for tier in ph["pole_tiers"]:
            pick = _pole_for(i, stand, sh, rz, {**{k: v for k, v in ph.items() if k != "pole_tiers"}, "poles": tier}, side,
                             clearance, every, keyed=True)
            if pick[1][0] == 0:
                return pick[0]
            if best_any is None or pick[1] < best_any[1]:
                best_any = pick
        return best_any[0]
    choices = ph.get("poles", POLES)[side]
    best, key = choices[0], None
    for pole in choices:
        fails, margin, prev = 0, math.inf, None
        for k in range(0, n, every):
            e, w, t, gate, why, _ = _arm(i, stand, sh, rz, ph, k, side, pole, clearance)
            fails += len(why)
            if e is None:
                continue
            # A pole nearly along the shoulder-wrist line swings the elbow round between close samples: a jump the
            # continuity gate fails, so it counts here as a failure too.
            if every == 1 and prev is not None and float(np.linalg.norm(e - prev)) > ELBOW_STEP_CM:
                fails += 1
            prev = e
            margin = min(margin, WRIST_MAX - gate["wrist_deg"], ELBOW_MAX - gate["elbow_flex_deg"])
            if "sleeve_cm" in gate:
                margin = min(margin, 20.0 * (min(gate["sleeve_cm"], gate["palm_cm"]) - CLEAR_CM))
        k_ = (fails, -margin)
        if key is None or k_ < key:
            best, key = pole, k_
    return (best, key) if keyed else best


def _swivel(pole, shoulder, wrist, deg):
    """pole turned by deg about the shoulder-wrist line: the elbow's free swivel."""
    a = unit(wrist - shoulder)
    p = np.asarray(pole, float)
    t = math.radians(deg)
    return p * math.cos(t) + np.cross(a, p) * math.sin(t) + a * (a @ p) * (1.0 - math.cos(t))


SWIVEL_BUMPS = (15.0, -15.0, 30.0, -30.0, 45.0, -45.0, 60.0, -60.0)


def _transition_poles(i, stand, sh, rz, ph, side, a, b, clearance, every):
    """A transition's pole at each sample for one paw: turned from the phase before's (a) to the phase after's (b).
    If that fails a gate, the elbow swings out of the way and back: a swivel of bump * sin(pi u) about the shoulder-
    wrist line, zero at both ends, the smallest bump of SWIVEL_BUMPS that clears every sample. Returns (poles, bump)."""
    n = max(len(ph["L"]), len(ph["R"]))
    base = [unit((1 - _u(ph, k)) * unit(a) + _u(ph, k) * unit(b)) for k in range(n)]

    def poles_for(bump):
        return [_swivel(base[k], sh[side], wrist_of(ph[side][min(k, len(ph[side]) - 1)]), bump * math.sin(math.pi * _u(ph, k)))
                for k in range(n)]

    def clean(poles):
        return all(not _arm(i, stand, sh, rz, ph, k, side, poles[k], clearance)[4] for k in range(0, n, every))

    if clean(base):
        return base, 0.0
    for bump in SWIVEL_BUMPS:
        trial = poles_for(bump)
        if clean(trial):
            return trial, bump
    return base, 0.0


def check(i, stand=None, yaw_deg=0.0, eye_z=STANDING_EYE_Z, clearance=True, every=1):
    """Every action of station i from one stand: {action: {"ok", "fail" [(phase, sample, paw, why)], "fail_count",
    "worst" {gate: value}}}. every > 1 samples every n-th target (the continuity gate needs every == 1)."""
    stand = B.craft_stand(i) if stand is None else np.asarray(stand, float)
    sh, rz = shoulders(stand, yaw_deg, eye_z)
    report = {}
    for name, steps in actions(i, sh):
        # Poles: each phase its own; each transition turns from the phase before to the phase after.
        pole = [{s: _pole_for(i, stand, sh, rz, ph, s, clearance, every) for s in ("L", "R")} if ph["kind"] == "phase" else None
                for ph in steps]
        swing = {}
        for j, ph in enumerate(steps):
            if pole[j] is None:
                before = next((pole[q] for q in range(j - 1, -1, -1) if pole[q] is not None), None)
                after = next((pole[q] for q in range(j + 1, len(steps)) if pole[q] is not None), None)
                a, b = before or after, after or before
                for side in ("L", "R"):
                    swing[(j, side)] = _transition_poles(i, stand, sh, rz, ph, side, a[side], b[side], clearance, every)
        fails = []
        worst = {"reach_pct": 0.0, "elbow_flex_deg": 0.0, "wrist_deg": 0.0, "clear_cm": SEP_LIMIT_CM, "elbow_step_cm": 0.0}
        for (j, side), (_, bump) in swing.items():
            if bump:
                worst["swivel_deg"] = max(worst.get("swivel_deg", 0.0), abs(bump))
        prev = {}
        for j, ph in enumerate(steps):
            n = max(len(ph["L"]), len(ph["R"]))
            for k in range(0, n, every):
                poles = pole[j] if pole[j] is not None else {side: swing[(j, side)][0][k] for side in ("L", "R")}
                arms = {}
                for side in ("L", "R"):
                    e, w, t, gate, why, mesh = _arm(i, stand, sh, rz, ph, k, side, poles[side], clearance)
                    fails += [(ph["phase"], k, side, x) for x in why]
                    for key in ("reach_pct", "elbow_flex_deg", "wrist_deg"):
                        if key in gate:
                            worst[key] = max(worst[key], gate[key])
                    for key in ("sleeve_cm", "palm_cm"):
                        if key in gate:
                            worst["clear_cm"] = min(worst["clear_cm"], gate[key])
                    if e is not None:
                        if side in prev and every == 1:
                            step = float(np.linalg.norm(e - prev[side]))
                            worst["elbow_step_cm"] = max(worst["elbow_step_cm"], step)
                            if step > ELBOW_STEP_CM:
                                fails.append((ph["phase"], k, side, f"the elbow jumps {step:.1f} cm"))
                        prev[side] = e
                    if mesh is not None:
                        arms[side] = mesh
                if len(arms) == 2:
                    gap = _sep(arms["L"], arms["R"])
                    worst["clear_cm"] = min(worst["clear_cm"], gap)
                    if gap < CLEAR_CM:
                        fails.append((ph["phase"], k, "LR", f"the arms {gap:.2f} cm apart"))
        report[name] = {"ok": not fails, "fail": fails[:12], "fail_count": len(fails),
                        "worst": {k: round(v, 2) for k, v in worst.items()}}
    return report


def action_summary(i):
    """Each action at the natural stop facing its bearing, for the spec: its phases (kind, samples) and, per paw, the
    point worked at the phase's first and last sample (station frame, cm). The paths themselves follow the sockets and
    the contact rules here at every admitted stand."""
    import b09_craft_region as R_
    st = B.craft_stand(i)
    sh, _ = shoulders(st, R_.bearing_deg(i, st))
    out = []
    for name, steps in actions(i, sh):
        rows = []
        for ph in steps:
            row = {"phase": ph["phase"], "kind": ph["kind"], "samples": max(len(ph["L"]), len(ph["R"]))}
            for s in ("L", "R"):
                first, last = ph[s][0], ph[s][-1]
                row[s] = {"from_cm": np.round(first.get("P", first["C"]), 2).tolist(), "to_cm": np.round(last.get("P", last["C"]), 2).tolist()}
            rows.append(row)
        out.append({"action": name, "phases": rows})
    return out


def contact_view(i):
    """What the hero sees of the work while doing it, from the craft stand looking at the station's work point (the
    natural look; the camera is the player's and nothing moves it): {action: {aspect: {"in_frame", "samples",
    "span_deg", "frame_deg"}}}.
    - in_frame: the samples of the action's working phases whose active contacts, both paws' knuckle lines and the
      points they work (a brush's tip, a pressed or gripped point), are all in frame and hidden by no prop (occluded
      counts those a prop hides).
    - span_deg: the height those points span from the eye. A fixed look can frame them all only if it is at most the
      frame's height (frame_deg), so a span over it means the player would have to pitch the camera during the work."""
    stand = B.craft_stand(i)
    eye = stand + [B.EYE[0], B.EYE[1], B.CAPSULE_HALF + B.EYE[2]]
    work = B.station_parts(i)[3]
    out = {}
    for name, steps in actions(i):
        rows = []                                                   # (points, unoccluded) per working sample
        for ph in steps:
            if ph["kind"] != "phase":
                continue
            n = max(len(ph["L"]), len(ph["R"]))
            for k in range(n):
                pts = []
                for side in ("L", "R"):
                    t = ph[side][min(k, len(ph[side]) - 1)]
                    pts += [t["C"], t["P"]]
                scene = props(i, ph["state"], _u(ph, k))
                clear = not any(B._segment_meets_mesh(eye, eye + (p - eye) * 0.995, m) for p in pts for m in scene)
                rows.append((pts, clear))
        every = [p for pts, _ in rows for p in pts]
        out[name] = {}
        for aspect, a in B.ASPECTS.items():
            seen = sum(clear and B.in_view(eye, work, pts, a) for pts, clear in rows)
            out[name][aspect] = {"in_frame": int(seen), "samples": len(rows), "occluded": int(sum(not c for _, c in rows)),
                                 "span_deg": round(B.vertical_span_deg(eye, every), 2), "frame_deg": round(B.frame_height_deg(a), 2)}
    return out


def eye_at(stand, yaw_deg=0.0, eye_z=STANDING_EYE_Z):
    a = math.radians(yaw_deg)
    return np.array([stand[0] + B.EYE[0] * math.cos(a), stand[1] + B.EYE[0] * math.sin(a), eye_z])


def look_target(eye, yaw_deg, look):
    """A point the camera looks through: yawed to the facing, pitched toward the station's look point."""
    a = math.radians(yaw_deg)
    pitch = math.atan2(look[2] - eye[2], math.hypot(look[0] - eye[0], look[1] - eye[1]))
    return eye + np.array([math.cos(pitch) * math.cos(a), math.cos(pitch) * math.sin(a), math.sin(pitch)]) * 100.0


def view_at(i, stand, yaw_deg):
    """What the hero sees of the work while doing it from any stand and facing: the camera yawed to the facing and
    pitched toward the station's look point (the LookPoint socket; nothing moves the camera or the hero).
    {action: {aspect: {"in_frame", "samples", "occluded"}}}. A working sample counts as seen if its active contacts
    (both paws' knuckle lines and the points they work, and a brush's bristle corners) are all in frame and hidden by
    no prop."""
    stand = np.asarray(stand, float)
    sh, _ = shoulders(stand, yaw_deg)
    eye = eye_at(stand, yaw_deg)
    target = look_target(eye, yaw_deg, np.asarray(B.station_parts(i)[1]["LookPoint"][0], float))
    out = {}
    for name, steps in actions(i, sh):
        rows = []
        for ph in steps:
            if ph["kind"] != "phase":
                continue
            n = max(len(ph["L"]), len(ph["R"]))
            for k in range(n):
                pts = []
                for side in ("L", "R"):
                    t = ph[side][min(k, len(ph[side]) - 1)]
                    pts += [t["C"], t["P"]] + list(t.get("foot", []))
                allm = _scene(i, ph["state"], _u(ph, k), ph["works"])[0]
                clear = not any(B._segment_meets_mesh(eye, eye + (p - eye) * 0.995, allm) for p in pts)
                rows.append((pts, clear))
        out[name] = {aspect: {"in_frame": int(sum(c and B.in_view(eye, target, pts, a) for pts, c in rows)),
                              "samples": len(rows), "occluded": int(sum(not c for _, c in rows))}
                     for aspect, a in B.ASPECTS.items()}
    return out


def envelope(i, dx=(-12.0, 0.0, 4.0), dy=(-12.0, 12.0, 4.0), yaws=(-10.0, 0.0, 10.0)):
    """The stands about craft_stand (station frame) and facing yaws from which every action of station i passes
    reach, elbow, wrist and torso (clearance is checked at craft_stand itself), for root's interaction and presenter."""
    base = B.craft_stand(i)
    _, _, proxies, _ = B.station_parts(i)
    ok = []
    for x in np.arange(dx[0], dx[1] + 1e-9, dx[2]):
        for y in np.arange(dy[0], dy[1] + 1e-9, dy[2]):
            for yaw in yaws:
                stand = base + [x, y, 0.0]
                if any(B.circle_hits_box2d(stand[:2], B.CAPSULE_R, lo, hi) for lo, hi in proxies):
                    continue
                if all(r["ok"] for r in check(i, stand, yaw, clearance=False).values()):
                    ok.append((float(stand[0]), float(stand[1]), float(yaw)))
    return ok


def crouched(i):
    """The same actions from the crouched eye (reach, elbow, wrist, torso): reported, never a qualification."""
    return {a: {"ok": r["ok"], "fail_count": r["fail_count"], "worst": r["worst"], "first": r["fail"][:3]}
            for a, r in check(i, eye_z=CROUCHED_EYE_Z, clearance=False).items()}


if __name__ == "__main__":
    import json
    for i in range(4):
        print(B.STATIONS[i][0], json.dumps(check(i), indent=1, default=str)[:3000])
