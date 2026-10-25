"""The yumi's draw: the full-draw shape, the string and arrow, and what the
first-person camera sees of them. Standard library only, no Blender.

create_runtime_weapon_yumi.py builds the braced bow (SM_Weapon_18) from a
curvature profile, solved so both tips sit on the brace line. This module
reproduces that model exactly; its tests rebuild the committed sockets. It
adds what admission needs (viewmodels.json, W18 package): the string and draw
representation, and a check of the bow's volume, not just its sockets.

* **drawn(draw_m):** the stave at full draw. Both limbs' brace curvatures
  scale by one factor until the unstretched string, tip groove to nock to tip
  groove, reaches the nock drawn ``draw_m`` behind the grip at the nocking
  height. The arrow then runs nock to rest (Muzzle), and its point stands
  ``ARROW_M - draw_m`` past the grip.
* **string_segments(...):** two straight segments at any draw; one line when
  braced.
* **footprint(pose):** the drawn bow's stave, string, arrow and bow paw
  (PAW_L) in the A4 pose, through check_viewmodel_framing's own placement and
  projection.

  Codex's BowAim originals showed why it is needed: socket checks did not
  represent the proxy volumes, and those covered the target. Every part's
  nearest approach to the reticle is reported in half-heights against the
  contract's reticle_clear_radius.
* **The continuous draw rig (SK_Weapon_18).** Production is a skeletal yumi,
  not a mesh swap.
  - **Bones:** RIG_BONES along the limbs, fitted to the solved shape at each
    draw (bone_joints), with skinning_error measuring the skinned stave
    against it; Tip_U, Tip_L and String_Nock for the string.
  - **Over time:** draw_fraction is the draw and the release.
* **timeline(...) and summary(...):** every volume, the draw paw (PAW_R)
  included, frame by frame through draw, hold, release and return, in rest
  and both bobs. The presentation rest blends at the contract's blend_per_s,
  optionally following the draw (motion.bow_draw_presentation).
"""
from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_viewmodel_framing as F  # noqa: E402

GENERATOR = HERE / "create_runtime_weapon_yumi.py"


def _constants():
    """The bow's constants, read from the generator so the two cannot drift."""
    tree = ast.parse(GENERATOR.read_text())
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("LENGTH", "BRACE", "GRIP_HALF", "POWER"):
                out[name] = ast.literal_eval(node.value)
    return out


_C = _constants()
LENGTH = _C["LENGTH"]
L_LOW = LENGTH / 3.0
L_UP = LENGTH - L_LOW
BRACE = _C["BRACE"]
GRIP_HALF = _C["GRIP_HALF"]
NOCK_Z = 0.07                      # the nocking point, as the generator places it
ARROW_M = 0.98                     # the ya (SM_Weapon_18_Ya): Nock to Tip
# Full draw in the bow's own (mesh) metres: the A4 bow.drawn pose holds the grip
# 60 cm before the eye at mesh scale 0.75, and the nock sits at the cheek, so
# about 0.88 m. The arrow's point then stands 10 cm past the grip, as in kyudo.
DRAW_M = 0.88
# The bow paw round the nigiri, in bow metres (Blender axes: +X forward, +Y the
# wielder's left, +Z up). A grey-and-white tabby paw, its toes round the
# leather. A capsule from below the grip to the thumb under the arrow, and its
# forearm back toward the archer's left shoulder.
PAW_L = {"radius": 0.036, "from": (-0.004, 0.0, -0.055), "to": (-0.004, 0.0, 0.062),
         "forearm_to": (-0.34, 0.16, -0.10), "forearm_radius": 0.034}


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def thickness(sig):
    """(width Y, depth X) of the stave at arc position sig, as the generator has it."""
    lim = L_UP if sig >= 0 else L_LOW
    u = min(abs(sig) / lim, 1.0)
    w = 0.0285 - 0.0120 * u ** 0.9
    d = 0.0215 - 0.0095 * u ** 0.85
    if abs(sig) < GRIP_HALF + 0.03:
        g = 1.0 - smooth01((abs(sig) - GRIP_HALF) / 0.03)
        d += 0.004 * g
    return w, d


def curvature(sig, amp, reflex):
    lim = L_UP if sig >= 0 else L_LOW
    u = abs(sig) / lim
    bend = amp * math.sin(math.pi * min(u, 1.0) * 0.92) ** 1.3 * smooth01((u - 0.04) / 0.12)
    tip = reflex * smooth01((u - 0.84) / 0.12)
    return bend - tip


def integrate(amp_u, amp_l, reflex=5.0, step=0.004):
    """Centreline (sigma, x, z) from the grip along each limb, as the generator integrates it."""
    def limb(amp, sign, lim):
        pts = [(0.0, 0.0, 0.0)]
        th = x = z = s = 0.0
        while s < lim - 1e-9:
            ds = min(step, lim - s)
            k = curvature(sign * (s + ds / 2), amp, reflex)
            th += k * ds
            x += -math.sin(th) * ds
            z += math.cos(th) * ds * sign
            s += ds
            pts.append((s * sign, x, z))
        return pts
    return limb(amp_l, -1.0, L_LOW), limb(amp_u, 1.0, L_UP)


def brace_amplitudes():
    """The generator's solve_shape amplitudes: each limb's tip on the brace line."""
    target = -(BRACE + thickness(0.0)[1] / 2)
    res = {}
    for key in ("up", "low"):
        def tip_x(amp):
            low, up = integrate(amp, amp)
            return (up if key == "up" else low)[-1][1]
        amp, step = 0.0, 0.02
        while tip_x(amp + step) > target:
            amp += step
        lo, hi = amp, amp + step
        for _ in range(40):
            mid = (lo + hi) / 2
            if tip_x(mid) > target:
                lo = mid
            else:
                hi = mid
        res[key] = (lo + hi) / 2
    return res["up"], res["low"]


def _frames(low, up):
    samples = list(reversed(low))[:-1] + up
    out = []
    for i, (sig, x, z) in enumerate(samples):
        a = samples[max(i - 1, 0)]
        c = samples[min(i + 1, len(samples) - 1)]
        tx, tz = c[1] - a[1], c[2] - a[2]
        n = math.hypot(tx, tz)
        tx, tz = tx / n, tz / n
        # n = Y x t: toward +X (the back of the bow)
        out.append((sig, (x, 0.0, z), (tx, 0.0, tz), (tz, 0.0, -tx)))
    return out


def grooves(low, up):
    """The string's tie points in the horn hazu: (lower, upper), as the generator finds them."""
    frames = _frames(low, up)

    def at(sig):
        return min(frames, key=lambda f: abs(f[0] - sig))
    _s, lo_p, _t, lo_n = at(-L_LOW + 0.0145)
    _s, up_p, _t, up_n = at(L_UP - 0.0145)
    dl = thickness(-L_LOW + 0.0145)[1] * 0.3
    du = thickness(L_UP - 0.0145)[1] * 0.3
    a = tuple(lo_p[i] - lo_n[i] * dl for i in range(3))
    b = tuple(up_p[i] - up_n[i] * du for i in range(3))
    return a, b


def _dist(a, b):
    return math.dist(a, b)


def braced():
    """The braced bow: centreline, string ends, and the generator's sockets."""
    amp_u, amp_l = brace_amplitudes()
    low, up = integrate(amp_u, amp_l)
    a, b = grooves(low, up)
    tz = (NOCK_Z - a[2]) / (b[2] - a[2])
    nock = tuple(a[i] + (b[i] - a[i]) * tz for i in range(3))
    w0, d0 = thickness(0.0)
    arrow_y = -(w0 / 2 + 0.0055)
    sockets = {"Grip_L": (0.0, 0.0, 0.0), "Grip_R": nock, "Muzzle": (d0 / 2 + 0.002, arrow_y, NOCK_Z),
               "String_Lower": a, "String_Upper": b}
    return {"amplitudes": (amp_u, amp_l), "low": low, "up": up, "string_m": _dist(a, b), "sockets": sockets}


def drawn(draw_m=DRAW_M):
    """Full draw: the limb scale k at which the unstretched string reaches the
    nock at (-draw_m, 0, NOCK_Z); centreline, string ends, sockets and arrow."""
    br = braced()
    amp_u, amp_l = br["amplitudes"]
    length = br["string_m"]
    nock = (-draw_m, 0.0, NOCK_Z)

    def path(k):
        low, up = integrate(amp_u * k, amp_l * k)
        a, b = grooves(low, up)
        return _dist(a, nock) + _dist(nock, b), low, up, a, b
    lo, hi = 1.0, 1.0
    while path(hi)[0] > length:
        hi *= 1.25
        if hi > 20:
            raise RuntimeError("yumi: no limb bend reaches the drawn nock")
    for _ in range(50):
        mid = (lo + hi) / 2
        if path(mid)[0] > length:
            lo = mid
        else:
            hi = mid
    k = (lo + hi) / 2
    _p, low, up, a, b = path(k)
    rest = br["sockets"]["Muzzle"]
    d = tuple(rest[i] - nock[i] for i in range(3))
    n = math.sqrt(sum(c * c for c in d))
    tip = tuple(nock[i] + d[i] / n * ARROW_M for i in range(3))
    sockets = {"Grip_L": (0.0, 0.0, 0.0), "Grip_R": nock, "Muzzle": rest, "String_Lower": a, "String_Upper": b}
    return {"k": k, "low": low, "up": up, "string_m": _dist(a, nock) + _dist(nock, b), "sockets": sockets,
            "arrow": (nock, tip), "draw_m": draw_m}


def string_segments(sockets):
    """The string at any draw: tip groove to nock to tip groove (two straight segments)."""
    return [(sockets["String_Upper"], sockets["Grip_R"]), (sockets["Grip_R"], sockets["String_Lower"])]


# ---------------------------------------------------------------------------
# First-person footprint
# ---------------------------------------------------------------------------

def _lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _stave_edges(shape, every=1):
    """Points on the stave's left and right edges (+-Y) and its back and belly, along the centreline."""
    samples = list(reversed(shape["low"]))[:-1] + shape["up"]
    frames = _frames(shape["low"], shape["up"])
    pts = []
    for i in range(0, len(samples), every):
        sig, p, _t, n = frames[i]
        w, d = thickness(sig)
        for sy in (-1.0, 1.0):
            pts.append((p[0], p[1] + sy * w / 2, p[2]))
        for sx in (-1.0, 1.0):
            pts.append((p[0] + n[0] * sx * d / 2, p[1], p[2] + n[2] * sx * d / 2))
    return pts


def _capsule(a, b, r, n_along=24, n_round=16):
    pts = []
    ax = tuple(b[i] - a[i] for i in range(3))
    L = math.sqrt(sum(c * c for c in ax)) or 1e-9
    t = tuple(c / L for c in ax)
    # Any two directions perpendicular to t.
    ref = (0.0, 0.0, 1.0) if abs(t[2]) < 0.9 else (1.0, 0.0, 0.0)
    u = (t[1] * ref[2] - t[2] * ref[1], t[2] * ref[0] - t[0] * ref[2], t[0] * ref[1] - t[1] * ref[0])
    un = math.sqrt(sum(c * c for c in u))
    u = tuple(c / un for c in u)
    v = (t[1] * u[2] - t[2] * u[1], t[2] * u[0] - t[0] * u[2], t[0] * u[1] - t[1] * u[0])
    for i in range(n_along + 1):
        c = _lerp(a, b, i / n_along)
        for j in range(n_round):
            ang = math.tau * j / n_round
            pts.append(tuple(c[k] + r * (math.cos(ang) * u[k] + math.sin(ang) * v[k]) for k in range(3)))
    return pts


def parts(shape):
    """Sample points of each visible part, in bow metres (Blender axes)."""
    s = shape["sockets"]
    nock, tip = shape.get("arrow", (s["Grip_R"], s["Muzzle"]))
    out = {"stave": _stave_edges(shape)}
    out["string"] = [_lerp(a, b, i / 60) for a, b in string_segments(s) for i in range(61)]
    out["arrow"] = _capsule(nock, tip, 0.0042, n_along=80, n_round=8)
    out["paw_L"] = (_capsule(PAW_L["from"], PAW_L["to"], PAW_L["radius"])
                    + _capsule(PAW_L["from"], PAW_L["forearm_to"], PAW_L["forearm_radius"]))
    return out


def footprint(pose_name="bow.drawn", shape=None, contract=None):
    """Each part's nearest approach to the reticle (half-heights), its screen
    extent, and how much of it lies in front of the near plane, in the A4 pose."""
    contract = contract or F.json.loads(F.CONTRACT.read_text())
    pose = contract["poses"][pose_name]
    screen = F.Screen(contract["camera"])
    shape = shape or (drawn() if pose_name == "bow.drawn" else braced())
    scale = contract["mesh_scale"]
    report = {}
    for name, pts in parts(shape).items():
        sockets = {"Grip_L": (0.0, 0.0, 0.0)}
        sockets.update({f"p{i}": p for i, p in enumerate(pts)})
        eye, _q = F.place(pose["rest"], sockets, pose["anchor"], scale)
        # The checker's near plane: first-person depth (x * first_person_scale) beyond near_plane_cm.
        front = [eye[f"p{i}"] for i in range(len(pts)) if eye[f"p{i}"][0] * screen.scale > screen.near]
        if not front:
            report[name] = {"in_front": 0}
            continue
        d = [screen.reticle_distance(p) for p in front]
        uv = [screen.uv(p) for p in front]
        report[name] = {"in_front": round(len(front) / len(pts), 3), "nearest_half_heights": round(min(d), 4),
                        "u": [round(min(a for a, _ in uv), 3), round(max(a for a, _ in uv), 3)],
                        "v": [round(min(b for _, b in uv), 3), round(max(b for _, b in uv), 3)]}
    report["clear_radius"] = screen.clear
    report["clear"] = all(v.get("nearest_half_heights", 9.0) >= screen.clear for k, v in report.items()
                          if isinstance(v, dict))
    return report


if __name__ == "__main__":
    import json
    br, dr = braced(), drawn()
    print(json.dumps({"braced_sockets": br["sockets"], "string_m": br["string_m"], "drawn_k": dr["k"],
                      "drawn_sockets": dr["sockets"], "arrow": dr["arrow"],
                      "footprint_drawn": footprint("bow.drawn", dr), "footprint_rest": footprint("bow", br)}, indent=1))


# ---------------------------------------------------------------------------
# The continuous draw rig (SK_Weapon_18) and its first-person timeline
# ---------------------------------------------------------------------------

# Bones along each limb, from the grip, at equal arc fractions; their bind
# pose is the braced bow. The string is three bones: Tip_U and Tip_L in the
# horn hazu, and String_Nock. Each string segment is skinned linearly
# between its two bones, so it stays straight at any draw.
RIG_BONES = {"upper": 12, "lower": 8}
DRAW_S = 0.65                       # the HUD's hold to full draw
RELEASE_S = 0.03                    # the string's return to brace
RELEASE_OVERSHOOT = 0.06            # past brace (in draw fraction), damped out
RELEASE_DAMP_S = 0.12
# The draw paw in the yugake, its thumb hooked on the string under the nock.
# Bow metres from the nock: centre, radius, and the forearm toward the right elbow.
PAW_R = {"centre": (-0.02, -0.03, -0.015), "radius": 0.045, "forearm_to": (-0.26, -0.16, -0.10),
         "forearm_radius": 0.036}


def brace_nock_x():
    return braced()["sockets"]["Grip_R"][0]


_SHAPES = {}


def shape_at(d):
    """The bow at draw fraction d (0 braced, 1 full draw; below 0 is the
    release's overshoot past brace, mirrored as a small reverse bend)."""
    key = round(d, 4)
    if key not in _SHAPES:
        if abs(key) < 1e-9:
            _SHAPES[key] = braced()
        else:
            x0 = brace_nock_x()
            nock_x = x0 + key * (-DRAW_M - x0)
            if key > 0:
                _SHAPES[key] = drawn(-nock_x)
            else:
                # Past brace the string leads the limbs forward: model it as the
                # brace shape with the nock moved ahead and the tips eased forward.
                br = braced()
                sh = dict(br)
                sk = dict(br["sockets"])
                sk["Grip_R"] = (nock_x, 0.0, NOCK_Z)
                sh["sockets"] = sk
                _SHAPES[key] = sh
    return _SHAPES[key]


def _limb_points(shape):
    """(arc, x, z) along each limb from the grip: {'upper': [...], 'lower': [...]}."""
    return {"upper": [(abs(sig), x, z) for sig, x, z in shape["up"]],
            "lower": [(abs(sig), x, z) for sig, x, z in shape["low"]]}


def _at_arc(pts, s):
    import bisect
    arcs = [p[0] for p in pts]
    i = min(max(bisect.bisect_left(arcs, s), 1), len(pts) - 1)
    a, b = pts[i - 1], pts[i]
    f = (s - a[0]) / max(b[0] - a[0], 1e-12)
    x, z = a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f
    phi = math.atan2(b[2] - a[2], b[1] - a[1])            # the tangent's own angle in (x, z), away from the grip
    return x, z, phi


def bone_joints(shape):
    """Each limb's bone heads: [(arc, x, z, theta)], from the grip outward."""
    out = {}
    lims = {"upper": L_UP, "lower": L_LOW}
    for limb, pts in _limb_points(shape).items():
        n = RIG_BONES[limb]
        joints = []
        for j in range(n + 1):
            s = lims[limb] * j / n
            x, z, th = _at_arc(pts, s)
            joints.append((s, x, z, th))
        out[limb] = joints
    return out


def skinning_error(d, every=5):
    """The rig's worst stave centreline error (m) at draw fraction d, per limb,
    against the solved shape: each centreline point skinned to its two nearest
    bones, weighted linearly by arc, posed by their rotation and head."""
    bind = bone_joints(shape_at(0.0))
    pose = bone_joints(shape_at(d))
    exact = _limb_points(shape_at(d))
    rest = _limb_points(shape_at(0.0))
    worst = {}
    for limb in ("upper", "lower"):
        err = 0.0
        jb, jp = bind[limb], pose[limb]
        for s, x0, z0 in rest[limb][::every]:
            j = min(int(s / (jb[-1][0] / RIG_BONES[limb])), RIG_BONES[limb] - 1)
            a = (s - jb[j][0]) / (jb[j + 1][0] - jb[j][0])
            pos = [0.0, 0.0]
            for k, w in ((j, 1.0 - a), (j + 1, a)):
                _s, bx, bz, bphi = jb[k]
                _s, px, pz, pphi = jp[k]
                # The bone's rotation in the (x, z) plane: bind tangent onto posed tangent, wrapped.
                dphi = math.atan2(math.sin(pphi - bphi), math.cos(pphi - bphi))
                vx, vz = x0 - bx, z0 - bz
                c, sn = math.cos(dphi), math.sin(dphi)
                rx, rz = c * vx - sn * vz, sn * vx + c * vz
                pos[0] += w * (px + rx)
                pos[1] += w * (pz + rz)
            ex, ez, _th = _at_arc(exact[limb], s)
            err = max(err, math.hypot(pos[0] - ex, pos[1] - ez))
        worst[limb] = err
    return worst


def draw_fraction(t, release_at):
    """The draw over time: steady to full in DRAW_S while held (the HUD's
    0.65 s), then the string's snap back past brace and its damped return."""
    if t < release_at:
        return min(max(t / DRAW_S, 0.0), 1.0)
    d0 = min(release_at / DRAW_S, 1.0)
    tr = t - release_at
    if tr < RELEASE_S:
        return d0 * (1.0 - tr / RELEASE_S) - RELEASE_OVERSHOOT * (tr / RELEASE_S)
    return -RELEASE_OVERSHOOT * math.exp(-(tr - RELEASE_S) / RELEASE_DAMP_S) * math.cos(
        math.tau * (tr - RELEASE_S) / (2.2 * RELEASE_DAMP_S))


def _paw_r_points(nock, flown=0.0):
    """The draw paw at the nock; after the release it flies back and out (hanare)."""
    c = tuple(nock[i] + PAW_R["centre"][i] for i in range(3))
    away = (-0.30 * flown, -0.20 * flown, 0.02 * flown)
    c = tuple(c[i] + away[i] for i in range(3))
    pts = _capsule(c, (c[0] + 1e-4, c[1], c[2]), PAW_R["radius"], n_along=2, n_round=16)
    pts += _capsule(c, tuple(c[i] + PAW_R["forearm_to"][i] for i in range(3)), PAW_R["forearm_radius"], n_along=12,
                    n_round=12)
    return pts


def timeline(contract=None, anchor_y=None, release_at=1.2, end=1.8, fps=60.0, states=("rest", "bob_up_right",
                                                                                         "bob_down_left"),
             pose_follows_draw=False):
    """Simulate the presentation from the draw press (t = 0) through the hold,
    the release at ``release_at`` and the return. The rest blends bow ->
    bow.drawn -> bow at blend_per_s, as the runtime does (first-order). The rig
    draws as draw_fraction; the bow paw stays at the grip, the draw paw rides
    the nock and flies back at the release, and the arrow is shown until
    the release. Returns per frame and state each part's nearest approach to
    the reticle (half-heights) and the clear radius."""
    contract = contract or F.json.loads(F.CONTRACT.read_text())
    rest_pose = contract["poses"]["bow"]
    drawn_pose = contract["poses"]["bow.drawn"]
    screen = F.Screen(contract["camera"])
    scale = contract["mesh_scale"]
    k = contract["motion"]["blend_per_s"]
    a_rest = [float(v) for v in rest_pose["rest"]["anchor_cm"]]
    r_rest = [float(v) for v in rest_pose["rest"]["rotation_deg"]]
    a_drawn = [float(v) for v in drawn_pose["rest"]["anchor_cm"]]
    if anchor_y is not None:
        a_drawn[1] = anchor_y
    r_drawn = [float(v) for v in drawn_pose["rest"]["rotation_deg"]]
    anchor, rot = list(a_rest), list(r_rest)
    frames = []
    dt = 1.0 / fps
    t = 0.0
    while t <= end + 1e-9:
        target_a, target_r = (a_drawn, r_drawn) if t < release_at else (a_rest, r_rest)
        if pose_follows_draw and t < release_at:
            # The presentation target moves with the draw: the arrow comes up
            # onto the line as it is drawn, not ahead of it.
            g = draw_fraction(t, release_at)
            target_a = [a_rest[i] + (a_drawn[i] - a_rest[i]) * g for i in range(3)]
            target_r = [r_rest[i] + (r_drawn[i] - r_rest[i]) * g for i in range(3)]
        f = 1.0 - math.exp(-k * dt)
        anchor = [anchor[i] + (target_a[i] - anchor[i]) * f for i in range(3)]
        rot = [rot[i] + (target_r[i] - rot[i]) * f for i in range(3)]
        d = draw_fraction(t, release_at)
        shape = shape_at(d)
        s = shape["sockets"]
        p = parts(shape)
        nock = s["Grip_R"]
        if t >= release_at:
            p.pop("arrow")
        flown = 0.0 if t < release_at else min((t - release_at) / 0.10, 1.0)
        p["paw_R"] = _paw_r_points(nock, flown)
        row = {"t": round(t, 4), "draw": round(d, 4), "anchor": [round(v, 3) for v in anchor], "parts": {}}
        for state_name in states:
            st = contract["envelopes"]["states"][state_name]
            rest = {"anchor_cm": anchor, "rotation_deg": rot}
            for name, pts in p.items():
                sockets = {"Grip_L": (0.0, 0.0, 0.0)}
                sockets.update({f"p{i}": q for i, q in enumerate(pts)})
                eye, _q = F.place(rest, sockets, "Grip_L", scale, st)
                front = [eye[f"p{i}"] for i in range(len(pts)) if eye[f"p{i}"][0] * screen.scale > screen.near]
                dist = min((screen.reticle_distance(e) for e in front), default=None)
                prev = row["parts"].get(name)
                if dist is not None and (prev is None or dist < prev):
                    row["parts"][name] = round(dist, 4)
        frames.append(row)
        t += dt
    return {"clear_radius": screen.clear, "fps": fps, "release_at": release_at, "frames": frames}


def summary(tl):
    """Per part: the nearest approach over the aim hold (full draw, the pose
    settled, before the release) and over the transitions, with how long each
    phase sits inside the clear radius."""
    clear = tl["clear_radius"]
    dt = 1.0 / tl["fps"]
    out = {}
    for fr in tl["frames"]:
        settled = fr["draw"] >= 1.0 and fr["t"] < tl["release_at"] and fr["t"] >= DRAW_S
        phase = "hold" if settled else ("draw" if fr["t"] < tl["release_at"] else "release")
        for name, dist in fr["parts"].items():
            o = out.setdefault(name, {})
            ph = o.setdefault(phase, {"nearest": 9.0, "inside_s": 0.0})
            ph["nearest"] = min(ph["nearest"], dist)
            if dist < clear:
                ph["inside_s"] = round(ph["inside_s"] + dt, 4)
    return out
