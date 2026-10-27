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
    return {"C": c, "F": unit(f - (f @ n) * n), "N": -n, "P": np.asarray(point, float)}


def grip(point, normal, shoulder, task, off=2.5):
    """A grasp about a point (a strip, a rim's edge, a paper's edge): the knuckle line off cm from it along -normal,
    the digits curled round it. The palm faces it as nearly as the fingers' direction allows."""
    nn = unit(normal)
    c = np.asarray(point, float) - nn * off
    f = _fingers(c, shoulder, task)
    side = nn - (nn @ f) * f
    if np.linalg.norm(side) < 0.2:                                   # facing along the fingers: palm down instead
        side = -UP - (-UP @ f) * f
    return {"C": c, "F": f, "N": unit(side), "P": np.asarray(point, float)}


def claw(top, shoulder, task=FWD):
    """A small part taken from above: the palm flat and level over its top (a fuse stub or a tied neck included) by
    CLAW_CLEAR_CM, the fingers along the reach, the digits reaching down round it."""
    c = np.asarray(top, float) + UP * (PAD_OFF + CLAW_CLEAR_CM)
    f = _fingers(c, shoulder, task)
    return {"C": c, "F": unit(f - (f @ UP) * UP), "N": -UP, "P": np.asarray(top, float)}


def brush(tip, surface_normal, shoulder, tilt=0.25):
    """A brush's bristle tip at tip, its handle back toward the hand: along the line to the shoulder, tipped toward the
    surface's normal so the bristles meet it at a working angle.

    It is held as a pencil is, not as a dagger: the digits pinch it BRUSH_PINCH_CM up the handle, BRUSH_REACH_CM
    ahead of the knuckle line, the handle BRUSH_GRIP_DEG from the fingers in the palm's plane, the tip on the palm's
    side. (Writing, a pencil lies about 50 deg from the forearm with the wrist straight.) The fingers lean from the
    brush toward the reach."""
    tip = np.asarray(tip, float)
    a = unit(unit(shoulder - tip) + tilt * unit(surface_normal))      # from the tip toward the hand
    pinch = tip + a * BRUSH_PINCH_CM
    reach = unit(pinch - shoulder)
    m = unit(reach - (reach @ a) * a)
    th = math.radians(BRUSH_GRIP_DEG)
    f = -math.cos(th) * a + math.sin(th) * m
    return {"C": pinch - f * BRUSH_REACH_CM, "F": f, "N": -math.sin(th) * a - math.cos(th) * m, "P": tip}


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


def _moving(targets_from, targets_to, path, shoulder):
    """A paw carried along path (its knuckle line), from targets_from's fingers and palm to targets_to's. In the air
    between, the wrist relaxes: the fingers bend toward the reach from the shoulder (a quadratic Bezier in direction),
    and only the two ends are set poses."""
    out = []
    for u, c in zip(np.linspace(0.0, 1.0, len(path)), path):
        relaxed = unit(c - shoulder)
        f = unit((1 - u) ** 2 * targets_from["F"] + 2 * u * (1 - u) * relaxed + u ** 2 * targets_to["F"])
        n = unit((1 - u) * targets_from["N"] + u * targets_to["N"])
        out.append({"C": c, "F": f, "N": unit(n - (n @ f) * f)})
    return out


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


def _phase(name, kind, left, right, state, works):
    return {"phase": name, "kind": kind, "L": left, "R": right, "state": state, "works": frozenset(works)}


RIB_WORKS = {"SM_B09_Form", "SM_B09_StripStock", "SM_B09_StripQuiver"} | {f"SM_B09_Hoop{k}" for k in range(1, 7)}
LANTERN_WORKS = {"SM_B09_Form"} | {f"SM_B09_Hoop{k}" for k in range(1, 7)} | {f"SM_B09_Washi{k}" for k in range(1, 5)}


def _front_strip(sk, shoulder, z):
    """The stock strip nearest the shoulder, at height z: the strips stand round the quiver's axis, splaying outward
    (b09_workshop_craft.station_parts), so a paw takes the front one, not the bundle's middle."""
    q = np.asarray(sk["StripStock"][0], float)
    top = B.station_parts(0)[0][0].verts[:, 2].max()                 # the bench's top
    rad = 1.6 + 0.8 * (z - (top + 2.2)) / 98.0
    pts = [q[:2] + rad * np.array([math.cos(2.4 * j), math.sin(2.4 * j)]) for j in range(12)]
    best = min(pts, key=lambda p: float(np.linalg.norm(p - shoulder[:2])))
    return np.array([best[0], best[1], z])


def actions(i):
    """[(action, [phase records])]: each paw's targets per sample, from the craft stand."""
    _, sk, _, _ = B.station_parts(i)
    sock = lambda n: np.asarray(sk[n][0], float)  # noqa: E731
    sh, _ = shoulders(B.craft_stand(i))
    L, R = sh["L"], sh["R"]
    out = []
    if i == 0:
        lc = B.lantern_centre(0)
        strip = _front_strip(sk, R, sock("StripStock")[2] - 18.0)
        for k, (z, r) in enumerate(zip(B.hoop_z(), B.hoop_r()), 1):
            # The left paw takes its place at the form's front-left from the start, steadying the form: hovering where
            # the strip will lie, then pressing the wound strip there, its fingers along the strip toward where it
            # comes on (the elbow out).
            n_press = np.asarray(sk[f"WindPress{k}"][1], float)
            # The palm lies along the form's surface there, tilted with its profile; the strip's face is upright, so
            # the palm stands off its edge by half the strip's width times the tilt.
            tilt = abs(float(n_press[2])) / max(1e-9, float(np.linalg.norm(n_press[:2])))
            presst = press(sock(f"WindPress{k}") + n_press * (B.HOOP_W / 2) * tilt, n_press, L, unit(np.cross(n_press, UP)))
            hover = {"C": presst["C"] + n_press * 0.5, "F": presst["F"], "N": presst["N"], "P": presst["P"]}
            take = grip(strip, unit(strip - R) * [1, 1, 0], R, FWD + UP)    # the front strip, from the quiver
            hook = grip(lc + [-r, 0.0, z], FWD, R, FWD)
            length = r * math.radians(B.WIND_DEG)
            guides = [grip(lc + [-r, min(9.0, max(length * (1.0 - f) - 1.0, 0.0)), z], FWD, R, FWD)   # it runs in with
                      for f in np.linspace(0.0, 1.0, SAMPLES)]                                         # the strip's end
            held, hooked, bend = {"hoop": k, "strip": "held"}, {"hoop": k, "strip": 0.0}, {"hoop": k, "strip": "bend"}
            out.append((f"wind hoop {k}", [
                _phase("take a strip", "phase", [hover], [take], held, RIB_WORKS),
                _phase("carry it to the notch", "transition", _hold(hover), _move(take, hook, R), held, RIB_WORKS),
                _phase("hook its end", "phase", [hover], [hook], held, RIB_WORKS),
                _phase("press the hooked strip; slide to the guide", "transition",
                       _moving(hover, presst, _line(hover["C"], presst["C"]), L),
                       _moving(hook, guides[0], _line(hook["C"], guides[0]["C"]), R), hooked, RIB_WORKS),
                _phase("wind (HeldMs 0-800)", "phase", _hold(presst), guides, bend, RIB_WORKS),
            ]))
    elif i == 1:
        lc = B.lantern_centre(1)
        st = {m.name: m for m, _, _ in B.state_meshes(1)}
        path = _surface_path(lc, 180.0, -B.LANTERN_H / 2, B.LANTERN_H / 2, 0.6)   # up seam 1 (Seam1_0..8's curve)
        az = math.radians(245.0)                                    # the left hold, on the panel's left
        nrm = np.array([math.cos(az), math.sin(az), 0.0])
        hold = press(lc + nrm * (float(B.paper_r(6.0)) + 0.1) + [0.0, 0.0, 6.0], nrm, L, UP)
        top = sock("WashiSheet4")
        sheet_lo = st["SM_B09_WashiSheet4"].verts.min(0)
        sheet = grip(np.array([top[0] + sheet_lo[0] + 1.0, top[1], top[2] + 0.1]), -UP, L, FWD)   # by the top sheet's near edge
        dip = brush(sock("PasteDip"), UP, R, tilt=1.0)              # the handle rises about 54 deg, clear of the rim
        strokes = [brush(q, -FWD, R) for q in path]
        works = LANTERN_WORKS | {f"SM_B09_WashiSheet{j}" for j in range(1, 5)} | {"SM_B09_PastePot"}
        state = {"sheets": 4, "rims": "rest", "brush": "paw"}
        out.append(("paste a panel", [
            _phase("dip the brush; take a sheet", "phase", [sheet], [dip], state, works),
            _phase("to the frame", "transition", _move(sheet, hold, L), _move(dip, strokes[0], R), state, works),
            _phase("paste up the seam (HeldMs 0-1500)", "phase", _hold(hold, len(strokes)), strokes, state, works),
        ]))
        # The rims step: the bottom rim is on the frame from the start (its rest is its seat). The right paw sets the
        # top rim, pads on its upper face, onto the top mouth; the left paw steadies the frame.
        rest_t, seat_c = sock("RimTopRest"), sock("RimTopSeat")
        near = math.atan2(R[1] - rest_t[1], R[0] - rest_t[0])       # the rim's point toward the right shoulder
        take_t = press(rest_t + [B.LANTERN_RIM_R * math.cos(near), B.LANTERN_RIM_R * math.sin(near), B.RIM_H / 2], UP, R, FWD)
        at = math.radians(150.0)
        seat_t = press(seat_c + [B.LANTERN_RIM_R * math.cos(at), B.LANTERN_RIM_R * math.sin(at), B.RIM_H / 2], UP, R, FWD)
        works = LANTERN_WORKS | {"SM_B09_RimTop", "SM_B09_RimBottom"}
        out.append((f"seat the rims (a press clip, at most {CLIP_MAX_MS['rims']} ms)", [
            _phase("take the top rim; steady the frame", "phase", [hold], [take_t], {"sheets": 0, "rims": "rest", "brush": "pot"}, works),
            _phase("to the lantern", "transition", _hold(hold), _move(take_t, seat_t, R, 10.0),
                   {"sheets": 0, "rims": "paws", "brush": "pot"}, works),
            _phase("seat it", "phase", [hold], [seat_t], {"sheets": 0, "rims": "paws", "brush": "pot"}, works),
        ]))
    elif i == 2:
        lc = B.lantern_centre(2)
        path = _surface_path(lc, 180.0, B.LANTERN_H / 2, -B.LANTERN_H / 2, 0.7)   # down the front (OilStroke0_0..8's curve)
        az = math.radians(245.0)                                    # the left paw steadies the lantern's left
        nrm = np.array([math.cos(az), math.sin(az), 0.0])
        steady = press(lc + nrm * (float(B.paper_r(0.0)) + 0.1), nrm, L, UP)
        dip = brush(sock("OilDip"), UP, R, tilt=1.0)
        strokes = [brush(q, -FWD, R) for q in path]
        works = (LANTERN_WORKS - {"SM_B09_Form"}) | {"SM_B09_RimTop", "SM_B09_RimBottom", "SM_B09_OilDish"}
        state = {"brush": "paw"}
        out.append(("oil the lantern", [
            _phase("dip the brush; steady the lantern", "phase", [steady], [dip], state, works),
            _phase("to the stroke's top", "transition", _hold(steady), _move(dip, strokes[0], R, 5.0), state, works),
            _phase("oil down the front (HeldMs 0-1500)", "phase", _hold(steady, len(strokes)), strokes, state, works),
        ]))
    else:
        wrap = sock("WrapSpot")
        core_top = float(B.shell("core").verts[:, 2].max())         # the fuse stub's top, over the core's centre
        neck_top = float(B.shell("wrapped").verts[:, 2].max())      # the tied neck's top, over the shell's centre
        # The left paw holds the shell on the paper from its left, the right paw twists its neck from its right: both
        # palms upright beside it, their lower edges over the paper.
        lift = PALM_HALF[1] - B.SHELL["wrapped_cm"] / 2 + 0.3
        half = B.SHELL["wrapped_cm"] / 2
        hold = grip(wrap + [0.0, -half, lift], [0.0, 1.0, 0.0], L, FWD, off=PAD_OFF)
        twist = grip(wrap + [0.0, half, lift], [0.0, -1.0, 0.0], R, FWD, off=PAD_OFF)
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
                _phase("take a core", "phase", [hold], [core], tray, works),
                _phase("to the paper", "transition", _hold(hold), _move(core, twist, R, 5.0), carried, works),
                _phase("wrap and twist", "phase", [hold], [twist], wrapping, works),
                _phase("to the rack (the right paw lets go)", "transition", _move(hold, seat, L, 5.0), _hold(twist), carried, works),
                _phase("seat it", "phase", [seat], [twist], seated, works),
            ]))
        # The inspection starts where shell 3's clip ends: the left paw keeps the third shell seated (its last work),
        # and the right paw goes from the paper to the fuse, its index pad on the fuse's wire.
        seat3 = claw(sock("ShellSeat3") + UP * neck_top, L)
        fuse = grip(sock("FuseInspect") + [0.0, 0.0, 1.0], -UP, R, FWD - UP)
        works = {"SM_Weapon_07", "SM_B09_ShellWrapped3", "SM_B09_ShellRack"}
        done = {"cores": (), "seated": (1, 2, 3), "wrapping": False}
        out.append((f"inspect the fuse (a press clip, at most {CLIP_MAX_MS['inspect']} ms)", [
            _phase("ready", "phase", [seat3], [twist], done, works),
            _phase("to the fuse", "transition", _hold(seat3), _move(twist, fuse, R, 6.0), done, works),
            _phase("touch the fuse", "phase", [seat3], [fuse], done, works),
        ]))
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
        lc = B.lantern_centre(1)
        st = {m.name: m for m, _, _ in B.state_meshes(1)}
        meshes += [B.gore(k).moved(lc) for k in range(1, 5)]
        meshes += [st[f"SM_B09_WashiSheet{j}"].moved(sock(f"WashiSheet{j}")) for j in range(1, state["sheets"] + 1)]
        meshes.append(B.rim("Bottom").moved(sock("RimBottomRest")))  # fitted to the frame from the start
        if state["rims"] == "rest":
            meshes.append(B.rim("Top").moved(sock("RimTopRest")))
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


def _sep(a, b, limit=10.0):
    if a is None or b is None:
        return limit
    r = MC.exact_separation(a.verts, a.tris, b.verts, b.tris, limit=limit)
    return limit if r["separation_m"] is None else float(r["separation_m"])


def _torso_hit(stand, e, shoulder):
    return (stand[0] + TORSO["back"] <= e[0] <= stand[0] + TORSO["front"] and
            stand[1] - TORSO["half"] <= e[1] <= stand[1] + TORSO["half"] and e[2] < shoulder[2] + 5.0)


def _u(ph, k):
    n = max(len(ph["L"]), len(ph["R"]))
    return k / (n - 1) if n > 1 else 0.0


def _arm(i, stand, sh, rz, ph, k, side, pole, clearance):
    """One paw at sample k of phase ph under pole: (elbow, wrist, target, gate values, failures, its arm's mesh)."""
    t = ph[side][min(k, len(ph[side]) - 1)]
    e, w, gate, why = solve(side, sh[side], t, rz, pole)
    if why:
        return None, w, t, gate, [why], None
    fails = ["elbow inside the torso"] if _torso_hit(stand, e, sh[side]) else []
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


def _pole_for(i, stand, sh, rz, ph, side, clearance, every):
    """The pole (of POLES) under which a phase's samples pass every gate for this paw, with the most margin."""
    best, key = POLES[side][0], None
    n = max(len(ph["L"]), len(ph["R"]))
    for pole in POLES[side]:
        fails, margin = 0, math.inf
        for k in range(0, n, every):
            e, w, t, gate, why, _ = _arm(i, stand, sh, rz, ph, k, side, pole, clearance)
            fails += len(why)
            if e is None:
                continue
            margin = min(margin, WRIST_MAX - gate["wrist_deg"], ELBOW_MAX - gate["elbow_flex_deg"])
            if "sleeve_cm" in gate:
                margin = min(margin, 20.0 * (min(gate["sleeve_cm"], gate["palm_cm"]) - CLEAR_CM))
        k_ = (fails, -margin)
        if key is None or k_ < key:
            best, key = pole, k_
    return best


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
    for name, steps in actions(i):
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
        worst = {"reach_pct": 0.0, "elbow_flex_deg": 0.0, "wrist_deg": 0.0, "clear_cm": 10.0, "elbow_step_cm": 0.0}
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
