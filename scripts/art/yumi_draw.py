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
# First-person footprint: a sampled design envelope
# ---------------------------------------------------------------------------

# What these checks are, stated in every report. Codex's review of fa6aa2b /
# 384819b found that the first version passed geometry behind the camera,
# sampled open cylinders and four stave extrema, and stretched the string in
# its release model.
SCOPE = ("sampled design envelope, not the emitted or skinned asset: closed capsules and spheres for the arrow and "
         "paws, the generator's rounded-rectangle stave section (POWER 4.6, 28 points, tip taper) inflated for the "
         "nigiri, rattan and hazu; point samples with a local spacing margin, visibility of the mandatory parts, and "
         "near-plane crossings inside the frame. The timeline is sampled at its fps in rest and the nominal bob "
         "extremes, not a continuous-time bound or the native camera path.")
STAVE_SECTION_POINTS = 28
ENVELOPE_GRIP_M = 0.004            # the deerskin nigiri wound over the stave
ENVELOPE_RATTAN_M = 0.0015         # rattan bands and lacquer
ENVELOPE_HAZU = 1.10               # horn hazu, up to 6% wider than the stave (cap_rings) plus margin
# Parts that must be visible (in front of the near plane and in the frame) in a pose.
MANDATORY = {"bow.drawn": ("stave", "arrow", "paw_L"), "bow": ("stave", "paw_L")}


def _lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _stave_envelope(shape, every=3):
    """Rings of the stave's envelope along the centreline: the generator's
    section, its tip taper, inflated for the nigiri, rattan and hazu."""
    samples = list(reversed(shape["low"]))[:-1] + shape["up"]
    frames = _frames(shape["low"], shape["up"])
    ex = 2.0 / _C["POWER"]
    rings = []
    for i in list(range(0, len(samples), every)) + [len(samples) - 1]:
        sig, p, _t, n = frames[i]
        w, d = thickness(sig)
        rem = min(sig + L_LOW, L_UP - sig)
        if rem < 0.035:
            f = rem / 0.035
            w *= 0.62 + 0.38 * f
            d *= 0.62 + 0.38 * f
        if rem < 0.045:
            w, d = w * ENVELOPE_HAZU, d * ENVELOPE_HAZU
        pad = ENVELOPE_GRIP_M if abs(sig) <= GRIP_HALF + 0.01 else ENVELOPE_RATTAN_M
        w, d = w + 2 * pad, d + 2 * pad
        ring = []
        for k in range(STAVE_SECTION_POINTS):
            a = math.tau * k / STAVE_SECTION_POINTS
            ca, sa = math.cos(a), math.sin(a)
            yy = w / 2 * math.copysign(abs(ca) ** ex, ca)
            xx = d / 2 * math.copysign(abs(sa) ** ex, sa)
            ring.append((p[0] + n[0] * xx, p[1] + yy, p[2] + n[2] * xx))
        rings.append(ring)
    return rings


def _basis(t):
    ref = (0.0, 0.0, 1.0) if abs(t[2]) < 0.9 else (1.0, 0.0, 0.0)
    u = (t[1] * ref[2] - t[2] * ref[1], t[2] * ref[0] - t[0] * ref[2], t[0] * ref[1] - t[1] * ref[0])
    un = math.sqrt(sum(c * c for c in u))
    u = tuple(c / un for c in u)
    v = (t[1] * u[2] - t[2] * u[1], t[2] * u[0] - t[0] * u[2], t[0] * u[1] - t[1] * u[0])
    return u, v


def _capsule(a, b, r, n_along=24, n_round=16, n_cap=6):
    """Rings of a closed capsule: the cylinder from a to b and a hemisphere
    at each end, so its axial extent is [a - r, b + r]."""
    ax = tuple(b[i] - a[i] for i in range(3))
    L = math.sqrt(sum(c * c for c in ax))
    if L < 1e-9:
        return _sphere(a, r, n_lat=2 * n_cap, n_lon=n_round)
    t = tuple(c / L for c in ax)
    u, v = _basis(t)

    def ring(c, rad):
        return [tuple(c[k] + rad * (math.cos(math.tau * j / n_round) * u[k] + math.sin(math.tau * j / n_round) * v[k])
                      for k in range(3)) for j in range(n_round)]
    rings = []
    for i in range(n_cap, 0, -1):                               # the cap behind a
        phi = math.pi / 2 * i / n_cap
        c = tuple(a[k] - t[k] * r * math.sin(phi) for k in range(3))
        rings.append(ring(c, r * math.cos(phi)) if i < n_cap else [c] * n_round)
    for i in range(n_along + 1):
        rings.append(ring(_lerp(a, b, i / n_along), r))
    for i in range(1, n_cap + 1):                               # the cap beyond b
        phi = math.pi / 2 * i / n_cap
        c = tuple(b[k] + t[k] * r * math.sin(phi) for k in range(3))
        rings.append(ring(c, r * math.cos(phi)) if i < n_cap else [c] * n_round)
    return rings


def _sphere(c, r, n_lat=12, n_lon=16):
    rings = []
    for i in range(n_lat + 1):
        th = math.pi * i / n_lat
        z, rad = r * math.cos(th), r * math.sin(th)
        rings.append([(c[0] + rad * math.cos(math.tau * j / n_lon), c[1] + rad * math.sin(math.tau * j / n_lon), c[2] + z)
                      for j in range(n_lon)])
    return rings


def parts(shape):
    """Each part's envelope as a list of closed groups (each a list of rings
    of points, in bow metres, Blender axes). Groups are assessed apart, so no
    segment joins one group's end to the next one's start."""
    s = shape["sockets"]
    nock, tip = shape.get("arrow", (s["Grip_R"], s["Muzzle"]))
    out = {"stave": [_stave_envelope(shape)]}
    out["string"] = [_capsule(a, b, 0.0031, n_along=60, n_round=8, n_cap=2) for a, b in string_segments(s)]
    out["arrow"] = [_capsule(nock, tip, 0.0042, n_along=80, n_round=8, n_cap=3)]
    out["paw_L"] = [_capsule(PAW_L["from"], PAW_L["to"], PAW_L["radius"]),
                    _capsule(PAW_L["from"], PAW_L["forearm_to"], PAW_L["forearm_radius"])]
    return out


def place_many(rest, points_m, scale, state=None):
    """check_viewmodel_framing.place for many points at once (numpy), about the
    Grip_L anchor at the bow origin: eye-space centimetres."""
    import numpy as np
    state = state or {}
    q = F.rotation(*rest["rotation_deg"])
    if state.get("pitch") or state.get("roll"):
        q = F.compose(F.rotation(state.get("pitch", 0.0), 0.0, state.get("roll", 0.0)), q)
    by, bz = state.get("bob", (0.0, 0.0))
    a = rest["anchor_cm"]
    origin = np.array([a[0], a[1] + by, a[2] + bz + state.get("lift", 0.0)])
    P = np.asarray(points_m, np.float64)
    ue = np.stack([100.0 * P[..., 0], -100.0 * P[..., 1], 100.0 * P[..., 2]], -1) * scale
    return origin + ue @ np.asarray(q, np.float64)


def assess(groups, rest, state, contract):
    """One part's projection, over its groups: visibility, nearest approach
    (with a local spacing margin), near-plane crossings inside the frame."""
    out = {"in_front": 0.0, "visible": False, "near_clip_in_frame": 0, "clip_points": []}
    n = 0
    for rings in groups:
        r = _assess_group(rings, rest, state, contract)
        k = len(rings) * len(rings[0])
        out["in_front"] += r["in_front"] * k
        n += k
        out["visible"] |= r["visible"]
        out["near_clip_in_frame"] += r["near_clip_in_frame"]
        out["clip_points"] += r["clip_points"]
        if "nearest_conservative" in r and r["nearest_conservative"] < out.get("nearest_conservative", 9.0):
            for key in ("nearest_half_heights", "margin", "nearest_conservative"):
                out[key] = r[key]
    out["in_front"] = round(out["in_front"] / max(n, 1), 4)
    out["clip_points"] = out["clip_points"][:4]
    return out


def _assess_group(rings, rest, state, contract):
    import numpy as np
    screen = F.Screen(contract["camera"])
    R = np.array(rings, np.float64)                             # (rings, points, 3)
    E = place_many(rest, R, contract["mesh_scale"], state)
    x = E[..., 0]
    near_x = screen.near / screen.scale
    front = x > near_x
    with np.errstate(divide="ignore", invalid="ignore"):
        u = E[..., 1] / x / screen.tan_h
        v = E[..., 2] / x / screen.tan_v
    on_frame = front & (np.abs(u) <= 1.0) & (np.abs(v) <= 1.0)
    dist = np.where(front, np.hypot(u * screen.aspect, v), np.inf)
    out = {"in_front": round(float(front.mean()), 4), "visible": bool(on_frame.any())}
    if front.any():
        i, j = np.unravel_index(np.argmin(dist), dist.shape)
        # Local margin: half the longest screen gap from the nearest sample to
        # its ring and axial neighbours that are also in front.
        gaps = []
        for di, dj in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            ii, jj = i + di, (j + dj) % R.shape[1]
            if 0 <= ii < R.shape[0] and front[ii, jj]:
                gaps.append(math.hypot((u[ii, jj] - u[i, j]) * screen.aspect, v[ii, jj] - v[i, j]))
        margin = max(gaps) / 2 if gaps else 0.0
        out.update({"nearest_half_heights": round(float(dist[i, j]), 4), "margin": round(margin, 4),
                    "nearest_conservative": round(float(dist[i, j]) - margin, 4)})
    clipped, where = near_cuts(E, near_x, screen)
    out["near_clip_in_frame"] = clipped
    out["clip_points"] = where[:4]
    return out


def near_cuts(E, near_x, screen):
    """Near-plane crossings that fall inside the frame, for eye-space rings
    E (rings, points, 3): every edge round each closed ring (the last point
    back to the first) and between consecutive rings. Returns (count, (u, v))."""
    import numpy as np
    clipped, where = 0, []
    for A, B in ((E, np.roll(E, -1, axis=1)), (E[:-1], E[1:])):
        fa, fb = A[..., 0] > near_x, B[..., 0] > near_x
        cross = fa != fb
        if cross.any():
            a_, b_ = A[cross], B[cross]
            t = (near_x - a_[:, 0]) / (b_[:, 0] - a_[:, 0])
            c = a_ + (b_ - a_) * t[:, None]
            cu = c[:, 1] / near_x / screen.tan_h
            cv = c[:, 2] / near_x / screen.tan_v
            inside = (np.abs(cu) <= 1.0) & (np.abs(cv) <= 1.0)
            clipped += int(np.sum(inside))
            where += [(round(float(a), 3), round(float(b), 3)) for a, b in zip(cu[inside], cv[inside])]
    return clipped, where


def footprint(pose_name="bow.drawn", shape=None, contract=None):
    """Each part's envelope in the A4 pose at rest: visibility, nearest
    approach to the reticle (half-heights, conservative), near-plane cuts in
    the frame. ``clear`` needs every mandatory part visible, every visible
    part outside the clear radius and no cut in the frame (SCOPE)."""
    contract = contract or F.json.loads(F.CONTRACT.read_text())
    pose = contract["poses"][pose_name]
    shape = shape or (drawn() if pose_name == "bow.drawn" else braced())
    clear_r = contract["camera"]["reticle_clear_radius"]
    report = {"scope": SCOPE, "clear_radius": clear_r, "parts": {}}
    for name, groups in parts(shape).items():
        report["parts"][name] = assess(groups, pose["rest"], None, contract)
    report["missing"] = [n for n in MANDATORY.get(pose_name, ()) if not report["parts"][n]["visible"]]
    report["clear"] = (not report["missing"]
                       and all(p.get("nearest_conservative", 9.0) >= clear_r for p in report["parts"].values() if p["visible"])
                       and all(p["near_clip_in_frame"] == 0 for p in report["parts"].values()))
    return report


# ---------------------------------------------------------------------------
# The continuous draw rig (SK_Weapon_18) and its first-person timeline
# ---------------------------------------------------------------------------

# Bones along each limb, from the grip, at equal arc fractions; their bind
# pose is the braced bow. The string is three bones: Tip_U and Tip_L in the
# horn hazu, and String_Nock. Each string segment is skinned linearly
# between its two bones, so it stays straight at any draw.
RIG_BONES = {"upper": 12, "lower": 8}
DRAW_S = 0.65                       # the HUD's hold to full draw
# The release returns the string exactly to brace in RELEASE_S and holds it
# there. An unstretched string can't pass brace: its real few-millimetre
# elastic vibration about brace is not modelled (an earlier overshoot moved
# the nock 4 cm past brace with the tips fixed and stretched the string by
# 1.87 mm; Codex's review of fa6aa2b).
RELEASE_S = 0.03
# The draw paw in the yugake, its thumb hooked on the string under the nock.
# Bow metres from the nock: centre, radius, and the forearm toward the right elbow.
PAW_R = {"centre": (-0.02, -0.03, -0.015), "radius": 0.045, "forearm_to": (-0.26, -0.16, -0.10),
         "forearm_radius": 0.036}


def brace_nock_x():
    return braced()["sockets"]["Grip_R"][0]


_SHAPES = {}


def shape_at(d):
    """The bow at draw fraction d: 0 braced, 1 full draw (DRAW_M). The string
    keeps its unstretched length at every d; d < 0 (past brace) is refused."""
    if d < 0.0 or d > 1.0 + 1e-9:
        raise ValueError(f"yumi: draw fraction {d} outside [0, 1]; the string can't pass brace or full draw")
    key = round(d, 4)
    if key not in _SHAPES:
        if key < 1e-9:
            _SHAPES[key] = braced()
        else:
            x0 = brace_nock_x()
            _SHAPES[key] = drawn(-(x0 + key * (-DRAW_M - x0)))
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
    0.65 s), then straight back to brace in RELEASE_S, and held there."""
    if t < release_at:
        return min(max(t / DRAW_S, 0.0), 1.0)
    d0 = min(release_at / DRAW_S, 1.0)
    return max(d0 * (1.0 - (t - release_at) / RELEASE_S), 0.0)


def _paw_r_rings(nock, flown=0.0):
    """The draw paw's envelope at the nock (a sphere and its forearm); after
    the release it flies back and out (hanare)."""
    c = tuple(nock[i] + PAW_R["centre"][i] for i in range(3))
    away = (-0.30 * flown, -0.20 * flown, 0.02 * flown)
    c = tuple(c[i] + away[i] for i in range(3))
    return [_sphere(c, PAW_R["radius"]), _capsule(c, tuple(c[i] + PAW_R["forearm_to"][i] for i in range(3)),
                                                  PAW_R["forearm_radius"], n_along=12, n_round=12)]


def timeline(contract=None, anchor_y=None, release_at=1.2, end=1.8, fps=60.0, states=("rest", "bob_up_right",
                                                                                         "bob_down_left"),
             pose_follows_draw=False, anchor_z=None):
    """Simulate the presentation from the draw press (t = 0) through the hold,
    the release at ``release_at`` and the return, sampled at ``fps`` in each of
    ``states`` (SCOPE: not continuous time, not the native camera path).

    - **The pose:** the rest blends bow -> bow.drawn -> bow at blend_per_s, as
      the runtime does (first order), optionally following the draw
      (motion.bow_draw_presentation).
    - **The parts:** the rig draws as draw_fraction. The bow paw stays at the
      grip; the draw paw rides the nock and flies back at the release; the
      arrow is shown until the release.

    Returns per frame the string's length and, per part (worst over states),
    its assess() figures."""
    contract = contract or F.json.loads(F.CONTRACT.read_text())
    rest_pose = contract["poses"]["bow"]
    drawn_pose = contract["poses"]["bow.drawn"]
    k = contract["motion"]["blend_per_s"]
    a_rest = [float(v) for v in rest_pose["rest"]["anchor_cm"]]
    r_rest = [float(v) for v in rest_pose["rest"]["rotation_deg"]]
    a_drawn = [float(v) for v in drawn_pose["rest"]["anchor_cm"]]
    if anchor_y is not None:
        a_drawn[1] = anchor_y
    if anchor_z is not None:
        a_drawn[2] = anchor_z
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
        p = parts(shape)
        if t >= release_at:
            p.pop("arrow")
        # The draw paw rides the nock while drawing. At the release the hand
        # lets the string go: it flies back from where it was, not with the string.
        if t < release_at:
            paw_at = shape["sockets"]["Grip_R"]
            held = paw_at
        flown = 0.0 if t < release_at else min((t - release_at) / 0.10, 1.0)
        p["paw_R"] = _paw_r_rings(paw_at if t < release_at else held, flown)
        segs = string_segments(shape["sockets"])
        row = {"t": round(t, 4), "draw": round(d, 4), "anchor": [round(v, 3) for v in anchor],
               "string_m": sum(_dist(a, b) for a, b in segs), "parts": {}}
        rest = {"anchor_cm": anchor, "rotation_deg": rot}
        for name, groups in p.items():
            worst = None
            for state_name in states:
                r = assess(groups, rest, contract["envelopes"]["states"][state_name], contract)
                if worst is None:
                    worst = dict(r)
                else:
                    worst["visible"] = worst["visible"] and r["visible"]
                    worst["near_clip_in_frame"] = max(worst["near_clip_in_frame"], r["near_clip_in_frame"])
                    worst["clip_points"] = (worst["clip_points"] + r["clip_points"])[:8]
                    if r.get("nearest_conservative", 9.0) < worst.get("nearest_conservative", 9.0):
                        for key in ("nearest_half_heights", "margin", "nearest_conservative"):
                            worst[key] = r[key]
            row["parts"][name] = worst
        frames.append(row)
        t += dt
    return {"scope": SCOPE, "clear_radius": contract["camera"]["reticle_clear_radius"], "fps": fps,
            "release_at": release_at, "frames": frames}


def summary(tl):
    """Per part and phase (draw, hold, release): the nearest conservative
    approach to the reticle, how long it sits inside the clear radius,
    frames where a mandatory part is not visible (the hold), and frames with
    a near-plane cut inside the frame."""
    clear = tl["clear_radius"]
    dt = 1.0 / tl["fps"]
    out = {}
    for fr in tl["frames"]:
        settled = fr["draw"] >= 1.0 and fr["t"] < tl["release_at"] and fr["t"] >= DRAW_S
        phase = "hold" if settled else ("draw" if fr["t"] < tl["release_at"] else "release")
        for name, r in fr["parts"].items():
            ph = out.setdefault(name, {}).setdefault(phase, {"nearest": 9.0, "inside_s": 0.0, "hidden_frames": 0,
                                                             "near_clip_frames": 0})
            if not r["visible"]:
                if phase == "hold" and name in MANDATORY["bow.drawn"]:
                    ph["hidden_frames"] += 1
                continue
            ph["nearest"] = min(ph["nearest"], r.get("nearest_conservative", 9.0))
            if r.get("nearest_conservative", 9.0) < clear:
                ph["inside_s"] = round(ph["inside_s"] + dt, 4)
            if r["near_clip_in_frame"]:
                ph["near_clip_frames"] += 1
    return out


if __name__ == "__main__":
    import json
    br, dr = braced(), drawn()
    print(json.dumps({"braced_sockets": br["sockets"], "string_m": br["string_m"], "drawn_k": dr["k"],
                      "drawn_sockets": dr["sockets"], "arrow": dr["arrow"],
                      "footprint_drawn": footprint("bow.drawn", dr), "footprint_rest": footprint("bow", br)}, indent=1))
