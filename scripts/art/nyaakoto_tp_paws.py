"""Nyaakoto's third-person paws: a furred paw closed round the grip channel, and its empty fist, in numpy.

Root's 05:15 review of the two-paw study: the curled tube fingers read as white tubes, not furred paws. One shape
per side replaces both the narrowed source palm (Paw_hand_) and those tubes:
- in the runtime body (rig_nyaakoto_runtime.py, LOD0);
- in every LOD (generate_nyaakoto_lods.py).
A single morph rule serves every LOD. Everything here runs without bpy, so it is tested (test_nyaakoto_tp_paws.py).

**Frames and units.** Blender metres, world axes at bind: +X forward, +Z up, +Y the character's left. The grip
channel's frame comes from nyaakoto_runtime_parts.arm_joints:
- c, its centre;
- z, the socket's Z_s, toward the palm (the back of the paw);
- w = +Y x z, forward-up;
- the channel's axis, which is world Y at bind.
The channel is an oval: a (CHANNEL_CM deep) along z and b (CHANNEL_CM across) along w. A point's channel
coordinates are:
- s, along the axis;
- t, the parameter angle of its nearest point on the oval (0 on the palm's side, 90 deg forward-up);
- e, its distance outside the oval along the oval's normal.

**The shape** is a signed distance field from nyaakoto_fp_paws' primitives:
- **the palm:** the source palm's ellipsoid, narrowed along Y to the paw's breadth and to PALM_SCALE of its depth and
  height. It shrinks about its point nearest the channel, so it still meets the grip there. s97's palm read as an egg,
  and r2's, scaled about its centre to 0.92, still did (root's 12:53 UTC review of e8d5b587: "the thumb/hand mass
  remains bulky");
- **four digits:** chains of tapered capsules on the old curled tubes' paths round the channel. Each thins from the
  knuckle and swells to a toe bulb before its rounded tip. The two middle toes lead; the outer two are smaller and end
  sooner (DIGIT_SCALE, DIGIT_END), so the tips make a cat's arc, not s97's mitten-like row;
- **the dewclaw-thumb,** wrapping the other way, slimmer than s97's, whose base read as a bulb under the empty fist,
  and again than r2's.
The digits and thumb meet each other by a smooth minimum whose reach (DIGIT_BLEND) runs from long over the knuckles to
short at the toes. Fur fills between the toes, so the back of the paw reads as one furred mass with toes parted
toward their tips, not four tubes (s96's first preview), and the mesher never meets a pinch. They blend into the palm
by a longer one.
Then two cuts:
- the channel, grown by CARVE_MARGIN, is carved out, so nothing reaches the tsuka;
- a slab keeps the paw, fuzz included, within PAW_HALF either side of the channel's centre (the rig's breadth gate).
  The palm and the outer digits are sized to stay inside it, so the slab only trims a blend's bulge.

**The mesh** is surface nets with a vertex per patch (manifold_surface_nets), smoothed and projected back onto
the field. A fur fuzz then pushes it outward along
its normals. The fuzz is two octaves of value noise, a function of position. It fades to nothing near the channel,
so the grip side never moves toward the tsuka.

**The coat:** one material, M_Hero_GreyTabbyFur, the only slot whose CoatBlend (vertex colour R) blends to the white
coat in Unreal (import_nyaakoto_pbr.py) and in the source render. CoatBlend is the digit weight times a ramp round the
channel (COAT_TURN): the back of the paw and the toes' first joints are tabby, the toes white from there to their tips,
the white fading over a few centimetres. The source's white fingers on a tabby paw are its reference. s96's first
preview, white from the knuckles, read as a white glove. The UVs are at the body's density:
- round the channel and along it, so the texture's fibres run along the toes;
- planar where a face looks along the channel (the paw's sides).

**The empty fist** (empty_points) is a remap in channel coordinates. A digit vertex keeps s, t and e; only the oval
it is measured from closes up:
- each oval point moves toward the palm-side edge, E'(t) = E(0) + k(t) (E(t) - E(0));
- k(t) is 1 up to the knuckles (|t| <= CURL_RAMP[0]) and eases to EMPTY_CHANNEL by CURL_RAMP[1] in log scale,
  k = EMPTY_CHANNEL ** smoothstep, which spends the fold budget (|k'| / k) evenly along the curl;
- the displacement is (k(t) - 1)(E(t) - E(0)), weighted by the digit weight, so the palm stays where it is;
- **the toes' arc:** the closure's end, k at CURL_RAMP[1], is EMPTY_CHANNEL + ARC_OPEN over the middle toes,
  easing back to EMPTY_CHANNEL by ARC_S[1] along the channel (closure_end). The middle toes close a little less,
  so their curl stands some 5 mm proud of the outer toes'.
  - Root's 12:53 UTC review of e8d5b587's IdlePaw_Front: "the idle digit row is nearly straight".
  - DIGIT_END's stagger alone nearly vanishes in the fist: every tip past CURL_RAMP[1] closes to the same share of
    its oval chord.
  - k depends on s as well as t, but the displacement never moves a point along the channel, so the closed fist's
    fold margin is still the oval's, slice by slice (fold_margin takes the least over s). The thumb, inboard at
    one pitch, is almost untouched.
The old fist (the curled tubes rebuilt round a shrunk channel) shrank the whole oval to EMPTY_CHANNEL. That slid every knuckle
about 1 cm along the channel: harmless for separate tubes, a fold for one surface. Here the knuckles do not move,
and the tips close almost as far as the old fist's (k 0.30 at the outer toes' tips, 0.44 at the middle toes' and the
thumb's). The ramp is
slow enough that the closed oval never turns back on itself (fold_margin). A linear ramp to 0.30 over 40-160 deg
did (a margin of -0.04 on this oval). The rule is a function of position, so it gives every LOD's morph.
"""
from __future__ import annotations

import math

import numpy as np

import nyaakoto_fp_paws as FP
import third_person_rig as TP

CHANNEL_HALF = (TP.CHANNEL_CM[0] / 200.0, TP.CHANNEL_CM[1] / 200.0)   # m: across (along w), deep (along z)
PAW_HALF = TP.PAW_BREADTH_MAX_CM / 200.0                                # m: the paw's half breadth along the channel
DIGIT_PITCH = 0.026            # m between the four digits' planes (the curled tubes' FINGER_PITCH)
DIGIT_SWEEP = (50.0, 200.0)    # deg round the channel, from the palm's top over the front (the tubes' FINGER_SWEEP)
THUMB_SWEEP = (-40.0, -130.0)  # deg, the other way round: from the palm's back under the channel
# m: each digit's radius at its sweep's samples, base to tip. It thins from the knuckle, then swells to the toe bulb.
DIGIT_RADII = (0.0140, 0.0134, 0.0122, 0.0116, 0.0120, 0.0100)
# The toes' arc (root's 07:12 review of s97: "a regular mitten-like row"): a cat's two middle toes lead, the outer two
# are a little smaller and end sooner, so the tips make an arc. Per digit, outer to outer: the radii's scale and the
# sweep's end (deg).
DIGIT_SCALE = (0.90, 1.0, 1.0, 0.90)
DIGIT_END = (186.0, 200.0, 200.0, 186.0)
# s97's 19 mm base read as a bulb under the empty fist; r2's 16.5 mm still read bulky (root, 12:53 UTC)
THUMB_RADII = (0.0150, 0.0139, 0.0126, 0.0114, 0.0100)
PALM_SCALE = (0.82, 0.80)      # the palm's x and z radii against the source's, about its point nearest the channel
SKIN = 0.0004                  # m: a digit's inner surface outside the channel, before the carve
CARVE_MARGIN = 0.0010          # m: the carve's reach outside the oval; nothing of the paw comes nearer
PALM_BLEND = 0.008             # m: the digits' smooth-minimum reach into the palm
# m: the digits' and thumb's smooth-minimum reach into each other: over the knuckles, then at the toes. It eases
# between the two over BLEND_TURN (deg of |t|). A constant 4 mm left slit grooves the mesher folded; a constant 6 mm
# left four tubes (s96). 12 to 5 mm over 95-150 deg pinched notches where the grooves deepen (s97's empty fist).
DIGIT_BLEND = (0.011, 0.007)
BLEND_TURN = (85.0, 175.0)
EMPTY_CHANNEL = 0.30           # the empty fist's closure (the tubes' fist used it throughout), reached at CURL_RAMP[1]
CURL_RAMP = (40.0, 180.0)      # deg of |t|: the fist closes from the knuckles to the tips
ARC_OPEN = 0.12                # the toes' arc: how much less the middle toes close (closure_end)
ARC_S = (0.5 * DIGIT_PITCH, 0.0300)   # m of |s|: the full opening over the middle toes, none from here outward
DIGIT_RAMP = 0.006             # m: the knuckle band where the digit weight eases from palm (0) to digit (1)
COAT_RAMP = 0.009              # m: the same band for the white coat, softer
COAT_TURN = (100.0, 140.0)     # deg of |t|: the white coat eases in along the toes
# The fuzz: a slight breakup of the silhouette, not fur. s96's first preview at 0.9 + 0.6 mm on 4.5 and 9 mm scales
# read as lumps. The fur is the material's.
FUZZ = {"amp": 0.0004, "scale": 0.0060, "broad_amp": 0.0004, "broad_scale": 0.0140, "clear": 0.004}
FUZZ_MAX = FUZZ["amp"] + FUZZ["broad_amp"]           # m: the most the fuzz can push a point out
PALM_HALF_Y = PAW_HALF - FUZZ_MAX - 0.0005          # m: the palm's half breadth along the channel
SLAB = PAW_HALF - FUZZ_MAX - 0.0003                 # m: the field's half breadth limit, before the fuzz
UV_PER_M = 2.4                 # the body's density (rig_nyaakoto_runtime's generated UVs)
UV_SEAM_DEG = -145.0           # the wrap's seam: between the thumb's tip and the digits' tips
SIDE_FACING = 0.75             # |normal . Y| above which a face takes the planar UVs
LOD_STEPS = (0.0030, 0.0045, 0.0070)   # m: the grid step of LOD0, LOD1 and LOD2's paws
Y = np.array([0.0, 1.0, 0.0])


def frame_of(arm):
    """The grip channel's frame from an arm_joints() row (mathutils Vectors or arrays; socket_rot as numpy columns)."""
    c = np.array([float(v) for v in arm["channel"]])
    z = np.asarray(arm["socket_rot"], float)[:, 2]
    w = np.cross(Y, z)
    w /= np.linalg.norm(w)
    return {"c": c, "z": z, "w": w, "a": CHANNEL_HALF[1], "b": CHANNEL_HALF[0], "sign": int(arm["sign"]),
            "palm": np.array([float(v) for v in arm["palm"]])}


def ellipse_param(u, v, a, b, iterations=24):
    """The parameter angle of the point (a cos t, b sin t) nearest (u, v), for points outside the oval: Newton's method
    on the normal condition, from the scaled polar angle, each step clamped to a quarter turn."""
    t = np.arctan2(a * v, b * u)
    k = a * a - b * b
    for _ in range(iterations):
        ct, st = np.cos(t), np.sin(t)
        f = k * ct * st - u * a * st + v * b * ct
        fp = k * (ct * ct - st * st) - u * a * ct - v * b * st
        fp = np.where(np.abs(fp) > 1e-18, fp, -1e-18)
        t = t - np.clip(f / fp, -0.4, 0.4)
    return np.arctan2(np.sin(t), np.cos(t))


def oval(t, fr):
    """The oval's point at t, as (along z, along w) from the channel's centre."""
    return fr["a"] * np.cos(t), fr["b"] * np.sin(t)


def normal(t, fr):
    """The oval's outward unit normal at t, as (along z, along w)."""
    nu, nv = np.cos(t) / fr["a"], np.sin(t) / fr["b"]
    n = np.hypot(nu, nv)
    return nu / n, nv / n


def channel_coords(points, fr):
    """(s, t, e) per point (see the module's notes)."""
    d = np.atleast_2d(points) - fr["c"]
    s, u, v = d @ Y, d @ fr["z"], d @ fr["w"]
    t = ellipse_param(u, v, fr["a"], fr["b"])
    ou, ov = oval(t, fr)
    nu, nv = normal(t, fr)
    e = (u - ou) * nu + (v - ov) * nv
    return s, t, e


def from_channel(s, t, e, fr):
    """The point at channel coordinates (s, t, e)."""
    s, t, e = (np.asarray(x, float) for x in (s, t, e))
    ou, ov = oval(t, fr)
    nu, nv = normal(t, fr)
    return (fr["c"] + s[..., None] * Y + (ou + e * nu)[..., None] * fr["z"] + (ov + e * nv)[..., None] * fr["w"])


def _curl_x(t):
    return np.clip((np.degrees(np.abs(t)) - CURL_RAMP[0]) / (CURL_RAMP[1] - CURL_RAMP[0]), 0.0, 1.0)


def closure_end(s=None):
    """k at CURL_RAMP[1] for points at s along the channel: EMPTY_CHANNEL + ARC_OPEN over the middle toes
    (|s| <= ARC_S[0]), easing to EMPTY_CHANNEL by ARC_S[1]. s None is EMPTY_CHANNEL, the outer toes'."""
    if s is None:
        return EMPTY_CHANNEL
    return EMPTY_CHANNEL + ARC_OPEN * (1.0 - ease(ARC_S[0], ARC_S[1], np.abs(np.asarray(s, float))))


def closure(t, s=None):
    """k(t, s): 1 up to the knuckles, easing to closure_end(s) by CURL_RAMP[1] in log scale (both sides of the
    channel)."""
    x = _curl_x(t)
    return closure_end(s) ** (x * x * (3.0 - 2.0 * x))


def closure_slope(t, s=None):
    """dk/dt, per radian, at fixed s."""
    x = _curl_x(t)
    span = math.radians(CURL_RAMP[1] - CURL_RAMP[0])
    return np.sign(t) * closure(t, s) * np.log(closure_end(s)) * 6.0 * x * (1.0 - x) / span


def closed_shift(t, fr, s=None):
    """The empty fist's displacement at (t, s), (k(t, s) - 1)(E(t) - E(0)), as (along z, along w)."""
    ou, ov = oval(t, fr)
    k = closure(t, s)
    return (k - 1.0) * (ou - fr["a"]), (k - 1.0) * ov


def fold_margin(fr, samples=4001, s_samples=13):
    """The smallest forward speed of the closed oval E'(t) along the original tangent, over |E_t|, the least over the
    paw's breadth along the channel: positive means the closed oval runs the same way as the original everywhere, so
    no offset surface (e >= 0) folds. 1 is no closure. The displacement never moves a point along the channel, so each
    slice of fixed s is the oval's own case."""
    t = np.linspace(-math.pi, math.pi, samples)
    a, b = fr["a"], fr["b"]
    eu, ev = -a * np.sin(t), b * np.cos(t)                         # E_t
    speed = np.hypot(eu, ev)
    worst = math.inf
    for s in np.linspace(0.0, PAW_HALF, s_samples):
        k, dk = closure(t, s), closure_slope(t, s)
        du, dv = dk * (a * np.cos(t) - a) + k * eu, dk * (b * np.sin(t)) + k * ev
        worst = min(worst, float(np.min((du * eu + dv * ev) / (speed * speed))))
    return worst


def skeleton(fr, palm_radii):
    """The paw's masses: the palm ellipsoid, and each digit's and the thumb's capsule chain (points and radii)."""
    sign = fr["sign"]
    source = np.array([palm_radii[0], PALM_HALF_Y, palm_radii[2]])
    r = source * np.array([PALM_SCALE[0], 1.0, PALM_SCALE[1]])
    toward = (fr["c"] - fr["palm"]) / np.linalg.norm(fr["c"] - fr["palm"])

    def reach(radii):                                              # the ellipsoid's extent along toward
        return 1.0 / math.sqrt(float(((toward / radii) ** 2).sum()))

    # Shrunk about its point nearest the channel, which arm_joints set on the oval: the palm still meets the grip.
    palm = {"c": fr["palm"] + (reach(source) - reach(r)) * toward, "axes": np.eye(3), "r": r}
    digits = []
    for d in range(4):
        s = (d - 1.5) * DIGIT_PITCH
        th = np.radians(np.linspace(DIGIT_SWEEP[0], DIGIT_END[d], len(DIGIT_RADII)))
        r = np.array(DIGIT_RADII) * DIGIT_SCALE[d]
        digits.append({"pts": from_channel(np.full(len(th), s), th, r + SKIN, fr), "r": r, "s": s})
    s_t = (-1.0 if sign > 0 else 1.0) * DIGIT_PITCH                # over the index digit, inboard
    th = np.radians(np.linspace(THUMB_SWEEP[0], THUMB_SWEEP[1], len(THUMB_RADII)))
    r = np.array(THUMB_RADII)
    thumb = {"pts": from_channel(np.full(len(th), s_t), th, r + SKIN, fr), "r": r, "s": s_t}
    return {"palm": palm, "digits": digits, "thumb": thumb, "frame": fr}


def _chain(p, chain):
    out = None
    for i in range(len(chain["r"]) - 1):
        d = FP.round_cone(p, chain["pts"][i], chain["pts"][i + 1], chain["r"][i], chain["r"][i + 1])
        out = d if out is None else np.minimum(out, d)
    return out


def channel_sdf(p, fr):
    """The channel's oval cylinder, negative inside: f / |grad f| of the oval's implicit, exact on the oval and
    within a fraction of a millimetre of the distance over the carve's reach."""
    d = p - fr["c"]
    u, v = d @ fr["z"], d @ fr["w"]
    a, b = fr["a"], fr["b"]
    f = (u / a) ** 2 + (v / b) ** 2 - 1.0
    g = 2.0 * np.hypot(u / (a * a), v / (b * b))
    return f / np.maximum(g, 1e-9)


def masses(p, skel):
    """The palm's distance and the nearest digit's (or the thumb's) at p."""
    pl = skel["palm"]
    palm = FP.ellipsoid(p, pl["c"], pl["axes"], pl["r"])
    dig = np.minimum.reduce([_chain(p, c) for c in skel["digits"] + [skel["thumb"]]])
    return palm, dig


def smin_var(a, b, k):
    """FP.smin with a reach per point (k > 0 everywhere)."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def turn_of(p, fr):
    """|t| in degrees, by the oval's scaled polar angle: the reach schedule needs no nearest point."""
    d = p - fr["c"]
    return np.degrees(np.abs(np.arctan2(fr["a"] * (d @ fr["w"]), fr["b"] * (d @ fr["z"]))))


def ease(lo, hi, x):
    x = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def digit_blend(p, fr):
    return DIGIT_BLEND[0] + (DIGIT_BLEND[1] - DIGIT_BLEND[0]) * ease(*BLEND_TURN, turn_of(p, fr))


def paw_sdf(p, skel, carve=True):
    pl = skel["palm"]
    palm = FP.ellipsoid(p, pl["c"], pl["axes"], pl["r"])
    k = digit_blend(p, skel["frame"])
    digits = None
    for c in skel["digits"] + [skel["thumb"]]:
        d = _chain(p, c)
        digits = d if digits is None else smin_var(digits, d, k)
    out = FP.smin(palm, digits, PALM_BLEND)
    if carve:
        fr = skel["frame"]
        out = np.maximum(out, -(channel_sdf(p, fr) - CARVE_MARGIN))
        out = np.maximum(out, np.abs((p - fr["c"]) @ Y) - SLAB)
    return out


def digit_weight(points, skel, ramp=DIGIT_RAMP):
    """1 on the digits and thumb, 0 on the palm, easing across the knuckles."""
    palm, dig = masses(np.atleast_2d(points), skel)
    x = np.clip((palm - dig + ramp) / (2.0 * ramp), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def empty_points(points, skel):
    """The empty fist: each digit vertex moved with its oval point as the oval closes; the palm stays (module notes)."""
    p = np.atleast_2d(points).astype(float)
    fr = skel["frame"]
    s, t, _ = channel_coords(p, fr)
    du, dv = closed_shift(t, fr, s)
    w = digit_weight(p, skel)
    return p + (w * du)[:, None] * fr["z"] + (w * dv)[:, None] * fr["w"]


def _value_noise(p, scale, seed):
    """Smooth value noise in [0, 1] on a lattice of the given scale (metres), hashed by seed."""
    g = np.asarray(p, float) / scale
    i0 = np.floor(g).astype(np.int64)
    f = g - i0
    f = f * f * (3.0 - 2.0 * f)
    out = np.zeros(len(g))
    mask = np.int64(0x7FFFFFFF)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                h = ((i0[:, 0] + dx) * 73856093) ^ ((i0[:, 1] + dy) * 19349663) ^ ((i0[:, 2] + dz) * 83492791) ^ (seed * 2654435761)
                h = h & mask
                h = ((h ^ (h >> 13)) * 1274126177) & mask
                val = ((h ^ (h >> 16)) & 0xFFFF) / 65535.0
                wx = f[:, 0] if dx else 1.0 - f[:, 0]
                wy = f[:, 1] if dy else 1.0 - f[:, 1]
                wz = f[:, 2] if dz else 1.0 - f[:, 2]
                out += wx * wy * wz * val
    return out


def fuzz_amount(verts, skel, seed=7, cfg=FUZZ):
    """How far the fur's breakup pushes each point outward: two octaves of noise, nothing within CARVE_MARGIN of the
    channel, the full amount from cfg["clear"] beyond it."""
    amount = cfg["amp"] * _value_noise(verts, cfg["scale"], seed) + cfg["broad_amp"] * _value_noise(verts, cfg["broad_scale"], seed + 1)
    away = np.clip((channel_sdf(verts, skel["frame"]) - CARVE_MARGIN) / cfg["clear"], 0.0, 1.0)
    return amount * away * away * (3.0 - 2.0 * away)


def corner_uvs(verts, tris, fr):
    """Per corner (u, v), at UV_PER_M: round the channel by its arc at each vertex's own radius and along the channel
    where a face looks across it; planar in the channel's cross-section where a face looks along it."""
    s, t, e = channel_coords(verts, fr)
    seam = math.radians(UV_SEAM_DEG)
    turn = np.mod(t - seam, 2.0 * math.pi)
    radius = e + 0.5 * (fr["a"] + fr["b"])
    ct = turn[tris]
    wrap = (ct.max(1) - ct.min(1)) > math.pi
    ct = np.where(wrap[:, None] & (ct < math.pi), ct + 2.0 * math.pi, ct)
    round_uv = np.stack([ct * radius[tris], s[tris]], -1) * UV_PER_M
    d = verts - fr["c"]
    flat_uv = np.stack([d @ fr["z"], d @ fr["w"]], -1)[tris] * UV_PER_M
    n = np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]])
    side = np.abs(n @ Y) > SIDE_FACING * np.linalg.norm(n, axis=1)
    return np.where(side[:, None, None], flat_uv, round_uv)


# Manifold surface nets. Naive surface nets (nyaakoto_fp_paws.surface_nets) puts one vertex in each crossed cell.
# Where two sheets pass through one cell, at a groove or where the thumb's tip meets the toes, that vertex joins them,
# and a face whose corners alternate in and out gives an edge four quads. The s96 smoke tests found 2 to 12 such edges
# a paw at every step. Here each cell gets one vertex per patch. Within a cell, two crossed edges are on one patch when
# a face joins them:
# - a face with two crossed edges joins those two;
# - a face with four is resolved by its centre (the mean of its corners). If the centre has the sign of corners 0
#   and 2, those corners connect through it and the face's two segments cut off corners 1 and 3; otherwise they cut
#   off 0 and 2.
# Both cells that share a face read the same four values, so they resolve it alike.
# One case is left: a pipe of the surface through such a face, whose two segments are on one patch in both cells.
# The dual edge between those two patches would then carry four quads. That face's resolution is flipped, which cuts
# the pipe there, and the patches are found again (at most MSN_ROUNDS times).
_FACES = ((0, 2, 6, 4), (1, 3, 7, 5), (0, 1, 5, 4), (2, 3, 7, 6), (0, 1, 3, 2), (4, 5, 7, 6))   # x0 x1 y0 y1 z0 z1
_EDGE_INDEX = {frozenset(e): i for i, e in enumerate(FP._EDGES)}
_FACE_EDGES = np.array([[_EDGE_INDEX[frozenset((f[i], f[(i + 1) % 4]))] for i in range(4)] for f in _FACES])
MSN_ROUNDS = 8


def _patches(cross, vals, ins, flip_of_face):
    """Each crossed edge's patch label in its cell (0-11; 12 for an edge not crossed), and each face's segments."""
    m = len(cross)
    rows = np.arange(m)
    links, segments = [], []
    for fi, (f, fe) in enumerate(zip(_FACES, _FACE_EDGES)):
        c = cross[:, fe]
        n = c.sum(1)
        order = np.argsort(~c, axis=1, kind="stable")
        links.append((fe[order[:, 0]], fe[order[:, 1]], n == 2))
        four = n == 4
        join02 = ((vals[:, list(f)].mean(1) <= 0) == ins[:, f[0]]) ^ flip_of_face[fi]
        s1 = (np.where(join02, fe[0], fe[3]), np.where(join02, fe[1], fe[0]))
        s2 = (np.where(join02, fe[2], fe[1]), np.where(join02, fe[3], fe[2]))
        links += [(s1[0], s1[1], four), (s2[0], s2[1], four)]
        segments.append((four, s1[0], s2[0]))
    label = np.where(cross, np.arange(12)[None], 12)
    for _ in range(12):
        before = label.copy()
        for a, b, ok in links:
            r, a, b = rows[ok], a[ok], b[ok]
            low = np.minimum(label[r, a], label[r, b])
            label[r, a] = low
            label[r, b] = low
        if (label == before).all():
            break
    return label, segments


def manifold_surface_nets(grid, axes):
    """Surface nets with one vertex per patch of each cell (see the notes above): a closed 2-manifold whenever the
    field is positive on the grid's boundary. Returns the vertices and the outward quads."""
    xs, ys, zs = axes
    step = np.array((xs[1] - xs[0], ys[1] - ys[0], zs[1] - zs[0]))
    origin = np.array((xs[0], ys[0], zs[0]))
    if (grid[0] <= 0).any() or (grid[-1] <= 0).any() or (grid[:, 0] <= 0).any() or (grid[:, -1] <= 0).any() \
            or (grid[:, :, 0] <= 0).any() or (grid[:, :, -1] <= 0).any():
        raise ValueError("manifold_surface_nets: the surface reaches the grid's boundary")
    inside = grid <= 0
    nx, ny, nz = grid.shape
    corners = [inside[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k] for i, j, k in FP._CUBE]
    any_in = np.zeros((nx - 1, ny - 1, nz - 1), bool)
    all_in = np.ones_like(any_in)
    for c in corners:
        any_in |= c
        all_in &= c
    active = any_in & ~all_in
    cell = np.argwhere(active)
    m = len(cell)
    rows = np.arange(m)
    index = -np.ones(active.shape, np.int64)
    index[tuple(cell.T)] = rows
    vals = np.stack([grid[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k][active] for i, j, k in FP._CUBE], 1).astype(np.float64)
    ins = vals <= 0
    E = np.array(FP._EDGES)
    va, vb = vals[:, E[:, 0]], vals[:, E[:, 1]]
    cross = (va <= 0) != (vb <= 0)
    tpar = np.where(cross, va / np.where(cross, va - vb, 1.0), 0.0)
    pa, pb = FP._CUBE[E[:, 0]], FP._CUBE[E[:, 1]]
    local = pa[None] + (pb - pa)[None] * tpar[..., None]
    # Global faces: those normal to axis a are indexed by the grid point at their low corner.
    flips = [np.zeros((nx, ny, nz), bool) for _ in range(3)]
    face_at = []
    for fi in range(6):
        axis, off = divmod(fi, 2)
        g = cell.copy()
        g[:, axis] += off
        face_at.append((axis, tuple(g.T)))
    for _ in range(MSN_ROUNDS):
        label, segments = _patches(cross, vals, ins, [flips[a][at] for a, at in face_at])
        key = rows[:, None] * 13 + label
        keys, vid = np.unique(key[cross], return_inverse=True)
        vmap = -np.ones((m, 12), np.int64)
        vmap[cross] = vid
        joined = [np.zeros((nx, ny, nz), np.int8) for _ in range(3)]
        for (axis, at), (four, a, b) in zip(face_at, segments):
            same = four & (vmap[rows, a] == vmap[rows, b])
            np.add.at(joined[axis], tuple(np.array(at)[:, same]), 1)
        pipes = [j == 2 for j in joined]
        if not any(p.any() for p in pipes):
            break
        for a in range(3):
            flips[a] ^= pipes[a]
    else:
        raise ValueError("manifold_surface_nets: a face still joins one patch pair twice")
    acc = np.zeros((len(keys), 3))
    np.add.at(acc, vid, (local + cell[:, None, :])[cross])
    cnt = np.bincount(vid, minlength=len(keys)).astype(np.float64)
    verts = origin + acc / cnt[:, None] * step
    quads = []
    for axis in range(3):
        sl_a = [slice(None)] * 3
        sl_b = [slice(None)] * 3
        sl_a[axis] = slice(0, -1)
        sl_b[axis] = slice(1, None)
        change = inside[tuple(sl_a)] != inside[tuple(sl_b)]
        e = np.argwhere(change)
        flip = inside[tuple(sl_a)][change]
        o1, o2 = [ax for ax in range(3) if ax != axis]
        ok = (e[:, o1] > 0) & (e[:, o2] > 0) & (e[:, o1] < [nx, ny, nz][o1] - 1) & (e[:, o2] < [nx, ny, nz][o2] - 1)
        e, flip = e[ok], flip[ok]
        q = []
        for d1, d2 in ((0, 0), (1, 0), (1, 1), (0, 1)):
            g = e.copy()
            g[:, o1] -= d1
            g[:, o2] -= d2
            ci = index[tuple(g.T)]
            if (ci < 0).any():
                raise ValueError("manifold_surface_nets: a crossed edge lacks one of its four cells")
            q.append(vmap[ci, 4 * axis + d1 + 2 * d2])
        q = np.stack(q, 1)
        right = (o1 - axis) % 3 == 1
        reverse = ~flip if right else flip
        q[reverse] = q[reverse][:, ::-1]
        quads.append(q)
    quads = np.concatenate(quads)
    if (quads < 0).any():
        raise ValueError("manifold_surface_nets: a quad corner has no patch vertex")
    return verts, quads


def self_crossings(verts, tris, chunk=200000):
    """The pairs of triangles that share no vertex and cross (mesh_clearance's exact edge-triangle test, in numpy, so
    it runs in Blender too). A surface the morph folded through itself has some; a clean one has none. Candidates come
    from a grid of cells the size of the largest triangle, so each pair that could meet is in neighbouring cells."""
    import mesh_clearance as MC
    P = np.asarray(verts, float)[tris]
    lo, hi = P.min(1), P.max(1)
    h = float(np.max(hi - lo)) * 1.001 + 1e-12
    cell = np.floor((lo - lo.min(0)) / h).astype(np.int64)
    dims = cell.max(0) + 3
    key = ((cell[:, 0] + 1) * dims[1] + (cell[:, 1] + 1)) * dims[2] + (cell[:, 2] + 1)
    order = np.argsort(key, kind="stable")
    skey = key[order]
    pairs = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if (dx, dy, dz) < (0, 0, 0):
                    continue
                nkey = key + (dx * dims[1] + dy) * dims[2] + dz
                start, stop = np.searchsorted(skey, nkey, "left"), np.searchsorted(skey, nkey, "right")
                count = stop - start
                i = np.repeat(np.arange(len(tris)), count)
                j = order[np.repeat(start, count) + (np.arange(count.sum()) - np.repeat(np.cumsum(count) - count, count))]
                keep = (i < j) if (dx, dy, dz) == (0, 0, 0) else np.ones(len(i), bool)
                pairs.append(np.stack([i[keep], j[keep]], 1))
    pairs = np.concatenate(pairs)
    pairs = pairs[np.all((lo[pairs[:, 0]] <= hi[pairs[:, 1]]) & (lo[pairs[:, 1]] <= hi[pairs[:, 0]]), 1)]
    shared = (tris[pairs[:, 0]][:, :, None] == tris[pairs[:, 1]][:, None, :]).any((1, 2))
    pairs = pairs[~shared]
    found = []
    for k in range(0, len(pairs), chunk):
        q = pairs[k:k + chunk]
        A, B = P[q[:, 0]], P[q[:, 1]]
        hit = np.zeros(len(q), bool)
        for X, Tt in ((A, B), (B, A)):
            for e in range(3):
                m, _ = MC.segments_cross_triangles_v(X[:, e], X[:, (e + 1) % 3], Tt[:, 0], Tt[:, 1], Tt[:, 2])
                hit |= m
        found.append(q[hit])
    return np.concatenate(found) if found else np.zeros((0, 2), np.int64)


def mesh_paw(arm, palm_radii, step=LOD_STEPS[0], smooth=6, seed=7, fuzz=True):
    """The closed paw at one grid step: verts, tris (outward), the per-corner UVs and CoatBlend, and its skeleton (for
    empty_points). The same arm, radii and seed at another step give the same surface, finer or coarser."""
    fr = frame_of(arm)
    skel = skeleton(fr, palm_radii)
    field = lambda q: paw_sdf(q, skel)                                   # noqa: E731
    pl = skel["palm"]
    pts = np.concatenate([pl["c"] - pl["r"], pl["c"] + pl["r"]] + [c["pts"].ravel() for c in skel["digits"] + [skel["thumb"]]]
                         ).reshape(-1, 3)
    lo, hi = pts.min(0) - 0.03, pts.max(0) + 0.03
    grid, axes = FP.sample_grid_banded(field, lo, hi, step)
    verts, quads = manifold_surface_nets(grid, axes)
    verts = FP.smooth_project(verts, quads, field, iterations=smooth)
    tris = FP.triangulate(quads, verts)
    if fuzz:
        n = FP.vertex_normals(verts, tris)
        # Free space ahead: in a groove the normal points at the facing wall, and a full push would cross it.
        probe = 2.0 * FUZZ_MAX
        free = np.clip(field(verts + probe * n) / probe, 0.0, 1.0)
        verts = verts + (fuzz_amount(verts, skel, seed) * free)[:, None] * n
    coat = digit_weight(verts, skel, COAT_RAMP) * ease(*COAT_TURN, turn_of(verts, fr))
    return {"verts": verts, "tris": tris, "uvs": corner_uvs(verts, tris, fr), "coat": coat[tris], "skeleton": skel,
            "step": step}
