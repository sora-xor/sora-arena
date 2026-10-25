"""Nyaakoto's first-person paws: anatomy, grip poses and meshing, in numpy.

The Blender driver (create_nyaakoto_fp_paws.py) only turns these arrays into
assets. Everything here runs without bpy, so it can be tested.

Frames and units:
- **Units:** metres in the bow's own frame, Blender axes: +X forward (the
  line of action), +Y the wielder's left, +Z up the grip.
- **The bow paw** (SM_NyaakotoFP_PawL_Yumi) is built in the Grip_L socket
  frame, whose origin is the grip's centre.

Construction:
- **The shape:** a signed distance field (SDF) of anatomical masses.
  - Bones are tapered capsules: forearm, carpus, four metacarpals, three
    phalanges on each of digits II-V, and the dewclaw (digit I) opposed as a
    thumb.
  - Pads (digital, metacarpal, carpal) are ellipsoids on the palmar side.
  - Each digit blends into the palm, never into its neighbours, so fur, not
    webbing, fills the gaps.
- **The pose wraps the measured grip.** Each digit's joints are placed along
  the grip's outline, offset by the digit's radius less a squeeze. The grip is
  then carved out of the paw. Contact flattens the pads and digits as soft
  tissue does, and nothing passes into the bow.
- **The mesh** is naive surface nets on a regular grid, then smoothed and
  projected back onto the zero set. That gives a closed quad surface with no
  holes.
- **Regions** label each vertex fur, pad or claw-bed, from the field's nearest
  masses. They drive materials and where fur grows.
"""
from __future__ import annotations

import math

import numpy as np

import yumi_draw as YD
import yumi_nigiri as NG

# ---------------------------------------------------------------------------
# The grip, from the W18 generator's own section, so the paw follows the bow
# it holds. v1-v3 hardcoded two prisms measured from the first rig (nigiri
# 16.6 x 18.2 mm, stave 11.8 x 13.9 mm). Codex (2026-10-25): the rebuilt,
# thinner wrap would leave the paw floating, and the stave tapers about 1 mm
# over the dewclaw's height, which a prism cannot follow.
# - The stave: yumi_draw.thickness(z), the generator's rounded rectangle
#   (POWER 4.6), straight along Z this near the grip (its centre sits at
#   x = 0.000 mm on the rig).
# - The nigiri over it: yumi_nigiri. The underlay at its shoulder height, plus
#   the strip's full height (THICK_M + LAP_M, the crest, as an envelope)
#   wherever the strip reaches.
# - Not modelled: the rattan bands, from +-0.12 m, which the paw never reaches.
# test_nyaakoto_fp_paws.Skin checks this envelope against the rig's emitted
# vertices.
# ---------------------------------------------------------------------------
GRIP_POWER = YD._C["POWER"]
GRIP_Z = (-0.14, 0.14)


def _grip_ab_scalar(z):
    w, d = YD.thickness(z)
    lo, hi = NG.reach(YD.GRIP_HALF)
    e = NG.UNDERLAY_M * NG.shoulder(z, YD.GRIP_HALF) if abs(z) <= YD.GRIP_HALF else 0.0
    if lo <= z <= hi:
        e += NG.THICK_M + NG.LAP_M
    return d / 2 + e, w / 2 + e


_GRIP_TABLE_Z = np.linspace(GRIP_Z[0] - 0.01, GRIP_Z[1] + 0.01, 1281)       # every 0.25 mm
_GRIP_TABLE_AB = np.array([_grip_ab_scalar(float(z)) for z in _GRIP_TABLE_Z])


def grip_ab(z):
    """(half-depth X, half-width Y) of the grip's outer envelope at height z, in metres."""
    return np.interp(z, _GRIP_TABLE_Z, _GRIP_TABLE_AB[:, 0]), np.interp(z, _GRIP_TABLE_Z, _GRIP_TABLE_AB[:, 1])


# The nigiri at the grip's centre, for the digits that wrap it (outline).
GRIP_WRAP = {"a": float(grip_ab(0.0)[0]), "b": float(grip_ab(0.0)[1]), "power": GRIP_POWER,
             "z": NG.reach(YD.GRIP_HALF)}
ARROW_PASS = (0.01475, -0.01975, 0.07)          # Muzzle: the arrow rests on the dewclaw under it
ARROW_SHAFT_R = 0.0026                          # 5.05 mm at the silk, halved, plus margin

SQUEEZE = 0.0012          # how far a resting digit's axis sits inside contact: the carve flattens this much
CARVE_GAP = 0.00015       # skin stops this far off the leather
FOREARM_DIR = np.array((-0.34, 0.16, -0.10)) / np.linalg.norm((-0.34, 0.16, -0.10))   # yumi_draw.PAW_L

# Digits II (index) to V (little): height on the grip, phalanx lengths
# (proximal, middle, distal) and radii at MCP, PIP, DIP and the tip. Feline
# proportions on an anthropomorphic paw: III and IV longest, short distal
# phalanges that carry retractile claws.
DIGITS = {
    "II": {"z": 0.031, "len": (0.033, 0.021, 0.015), "r": (0.0088, 0.0080, 0.0073, 0.0058)},
    "III": {"z": 0.0105, "len": (0.035, 0.022, 0.015), "r": (0.0092, 0.0084, 0.0076, 0.0060)},
    "IV": {"z": -0.0100, "len": (0.034, 0.021, 0.015), "r": (0.0090, 0.0082, 0.0074, 0.0059)},
    "V": {"z": -0.0300, "len": (0.028, 0.018, 0.013), "r": (0.0080, 0.0073, 0.0066, 0.0053)},
}
KNUCKLE_THETA = math.radians(128.0)     # MCP joints on the grip's left side, toward the back (theta from +X to +Y)
WRAP_SIGN = -1.0                        # digits run clockwise seen from above: left, front, right
DEWCLAW = {"z": 0.058, "len": (0.030, 0.024, 0.018), "r": (0.0098, 0.0090, 0.0080, 0.0062),
           "theta0": math.radians(185.0)}         # wraps the other way: the back face, then the right side
WRIST_BACK = 0.041                      # carpus centre behind the knuckle line, along the forearm
PALM_THICK = 0.0105                     # metacarpal radius at the knuckles (the palm's half-thickness)


def smin(a, b, k):
    """Polynomial smooth minimum (k in metres: the blend's reach)."""
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def round_cone(p, a, b, ra, rb):
    """Exact SDF of a capsule from a (radius ra) to b (radius rb)."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    ba = b - a
    l2 = float(ba @ ba)
    rr = ra - rb
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    pa = p - a
    y = pa @ ba
    z = y - l2
    xv = pa * l2 - y[..., None] * ba
    x2 = np.einsum("...i,...i->...", xv, xv)
    y2 = y * y * l2
    z2 = z * z * l2
    k = math.copysign(1.0, rr) * rr * rr * x2
    out = (np.sqrt(x2 * a2 * il2) + y * rr) * il2 - ra
    cap_b = np.sign(z) * a2 * z2 > k
    cap_a = np.sign(y) * a2 * y2 < k
    out = np.where(cap_b, np.sqrt(x2 + z2) * il2 - rb, out)
    out = np.where(cap_a, np.sqrt(x2 + y2) * il2 - ra, out)
    return out


def ellipsoid(p, c, axes, radii):
    """Approximate SDF of an ellipsoid at c with orthonormal axes (3x3, rows) and radii (Quilez's bound)."""
    q = (p - np.asarray(c)) @ np.asarray(axes).T
    r = np.asarray(radii)
    k0 = np.linalg.norm(q / r, axis=-1)
    k1 = np.linalg.norm(q / (r * r), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-12)


def superellipse_prism(p, a, b, power, z):
    """SDF (gradient-normalised near the surface) of |x/a|^n + |y/b|^n <= 1 between z[0] and z[1]."""
    x, y = np.abs(p[..., 0]) / a, np.abs(p[..., 1]) / b
    s = np.maximum(x ** power + y ** power, 1e-30)
    f = s ** (1.0 / power) - 1.0
    g = s ** (1.0 / power - 1.0)
    gx = g * np.maximum(x, 1e-30) ** (power - 1.0) / a
    gy = g * np.maximum(y, 1e-30) ** (power - 1.0) / b
    d2 = f / np.maximum(np.hypot(gx, gy), 1e-9)
    zc, h = 0.5 * (z[0] + z[1]), 0.5 * (z[1] - z[0])
    dz = np.abs(p[..., 2] - zc) - h
    outside = np.hypot(np.maximum(d2, 0.0), np.maximum(dz, 0.0))
    return np.minimum(np.maximum(d2, dz), 0.0) + outside


def grip_sdf(p):
    """SDF of the grip (stave and nigiri), its section following z."""
    a, b = grip_ab(p[..., 2])
    return superellipse_prism(p, a, b, GRIP_POWER, GRIP_Z)


def outline(theta, offset, grip=GRIP_WRAP):
    """A point on the grip's section outline at parameter angle theta, pushed
    out along its normal by offset (the offset curve of the rounded rectangle)."""
    a, b, n = grip["a"], grip["b"], grip["power"]
    c, s = math.cos(theta), math.sin(theta)
    x = a * math.copysign(abs(c) ** (2.0 / n), c)
    y = b * math.copysign(abs(s) ** (2.0 / n), s)
    gx = math.copysign(abs(x / a) ** (n - 1.0), x) / a
    gy = math.copysign(abs(y / b) ** (n - 1.0), y) / b
    g = math.hypot(gx, gy)
    return np.array((x + offset * gx / g, y + offset * gy / g))


def wrap_points(theta0, lengths, offsets, z, sign=WRAP_SIGN, steps=4000):
    """Joint positions along the offset outline, from theta0, at cumulative arc
    lengths. Each joint's offset is its own radius less the squeeze, so the
    digit's axis follows the leather around the grip."""
    thetas = theta0 + sign * np.linspace(0.0, 2.0 * math.pi, steps)
    out, total, target = [], 0.0, 0.0
    marks = np.concatenate([[0.0], np.cumsum(lengths)])
    j = 0
    prev = np.append(outline(thetas[0], offsets[0]), z)
    out.append(prev)
    for t in thetas[1:]:
        j_off = offsets[min(j + 1, len(offsets) - 1)]
        cur = np.append(outline(t, j_off), z)
        total += float(np.linalg.norm(cur - prev))
        prev = cur
        while j + 1 < len(marks) and total >= marks[j + 1]:
            out.append(cur)
            j += 1
        if j + 1 >= len(marks):
            break
    return np.array(out)


def bow_paw_skeleton():
    """Joint positions of the bow paw round the W18 grip (Grip_L frame).
    Returns {name: (points, radii)} chains and the pad ellipsoids."""
    chains = {}
    knuckles = []
    for name, d in DIGITS.items():
        offs = [r - SQUEEZE for r in d["r"]]
        pts = wrap_points(KNUCKLE_THETA, d["len"], offs, d["z"])
        chains[name] = (pts, d["r"])
        knuckles.append(pts[0])
    knuckles = np.array(knuckles)
    # The carpus sits behind the knuckle line toward the forearm; each
    # metacarpal runs from it to its MCP joint, splayed along the grip.
    k_mid = knuckles.mean(0)
    wrist = k_mid + FOREARM_DIR * WRIST_BACK + np.array((0.0, 0.006, -0.004))
    for i, (name, d) in enumerate(DIGITS.items()):
        base = wrist + np.array((0.0, 0.0, (d["z"] - k_mid[2]) * 0.55))
        chains["MC_" + name] = (np.array([base, knuckles[i]]), (0.0105, PALM_THICK * (d["r"][0] / 0.0092)))
    # The dewclaw: from the carpus's upper (radial) side, round the grip's back
    # face at the top, its distal phalanx forward along the right side under
    # the arrow pass.
    dc = DEWCLAW
    root = wrist + np.array((0.012, -0.008, 0.030))           # the CMC joint, inside the carpus's radial side
    offs = [r - SQUEEZE * 0.7 for r in dc["r"][1:]]
    wrapped = wrap_points(dc["theta0"], dc["len"][1:], offs, dc["z"], sign=-WRAP_SIGN)
    chains["I"] = (np.vstack([root, wrapped]), dc["r"])
    chains["forearm"] = (np.array([wrist + FOREARM_DIR * 0.075, wrist]), (0.0255, 0.0215))
    pads = metacarpal_and_digital_pads(chains, wrist)
    return {"chains": chains, "wrist": wrist, "pads": pads}


def _frame(t, up_hint):
    t = t / np.linalg.norm(t)
    n = up_hint - t * (up_hint @ t)
    n = n / np.linalg.norm(n)
    return np.stack([t, n, np.cross(t, n)])


def metacarpal_and_digital_pads(chains, wrist):
    """Toe beans under each digit's middle phalanx, the metacarpal pad under the
    knuckles, and the carpal pad high on the palmar wrist. Each is an
    ellipsoid on the side facing the grip (toward the grip's axis)."""
    pads = []
    for name in DIGITS:
        pts, r = chains[name]
        mid = 0.5 * (pts[2] + pts[3])                       # under the DIP joint and distal phalanx
        inward = -np.append(mid[:2], 0.0)
        inward /= np.linalg.norm(inward)
        c = mid + inward * (r[2] * 0.62)
        axes = _frame(pts[3] - pts[2], inward)
        pads.append(("pad_" + name, c, axes, (0.0072, 0.0046, 0.0052)))
    kn = np.array([chains[n][0][0] for n in DIGITS])
    mid = kn.mean(0)
    inward = -np.append(mid[:2], 0.0)
    inward /= np.linalg.norm(inward)
    axes = _frame(np.array((0.0, 0.0, 1.0)), inward)
    # v3: the metacarpal pad was 52 mm along the grip and bulged past the
    # digits' flank, a bald pink strip in every first-person view (Saved/YumiFP/v2).
    # A cat's metacarpal pad is about as wide as the four toe beans together;
    # here it spans the knuckles at 36 mm and sits tucked toward the grip.
    pads.append(("pad_metacarpal", mid + inward * 0.0045, axes, (0.018, 0.0060, 0.0090)))
    pads.append(("pad_carpal", wrist + np.array((0.004, -0.012, -0.006)),
                 _frame(np.array((0.0, 0.0, 1.0)), np.array((0.4, -0.9, 0.0))), (0.006, 0.0045, 0.0048)))
    return pads


def paw_sdf(p, skel, carve=True):
    """The bow paw's field at points p (..., 3), and the index of the nearest mass for regions."""
    chains, pads = skel["chains"], skel["pads"]
    labels = []
    fields = []
    palm = None
    for name, d in DIGITS.items():
        mc_pts, mc_r = chains["MC_" + name]
        m = round_cone(p, mc_pts[0], mc_pts[1], mc_r[0], mc_r[1])
        palm = m if palm is None else smin(palm, m, 0.010)
    fa_pts, fa_r = chains["forearm"]
    palm = smin(palm, round_cone(p, fa_pts[0], fa_pts[1], fa_r[0], fa_r[1]), 0.012)
    fields.append(palm)
    labels.append("palm")
    body = palm
    for name in list(DIGITS) + ["I"]:
        pts, r = chains[name]
        digit = None
        for j in range(len(pts) - 1):
            seg = round_cone(p, pts[j], pts[j + 1], r[j], r[j + 1])
            digit = seg if digit is None else smin(digit, seg, 0.0018)
        if name == "I":
            # The dewclaw's metacarpal joins the carpus: its first segment blends wide.
            blended = smin(palm, digit, 0.009)
        else:
            blended = smin(palm, digit, 0.0045)
        body = np.minimum(body, blended)
        fields.append(digit)
        labels.append("digit_" + name)
    for name, c, axes, radii in pads:
        pad = ellipsoid(p, c, axes, radii)
        body = smin(body, pad, 0.0022)
        fields.append(pad)
        labels.append(name)
    if carve:
        body = np.maximum(body, -(grip_sdf(p) - CARVE_GAP))
    return body, fields, labels


# ---------------------------------------------------------------------------
# Meshing: naive surface nets, smoothing and projection
# ---------------------------------------------------------------------------

def sample_grid(field, lo, hi, step, chunk=12):
    """Evaluate field(points) on a regular grid, z-chunked; returns the grid and its axes."""
    xs = np.arange(lo[0], hi[0] + step * 0.5, step)
    ys = np.arange(lo[1], hi[1] + step * 0.5, step)
    zs = np.arange(lo[2], hi[2] + step * 0.5, step)
    grid = np.empty((len(xs), len(ys), len(zs)), np.float32)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    for k0 in range(0, len(zs), chunk):
        zz = zs[k0:k0 + chunk]
        P = np.stack(np.broadcast_arrays(X[..., None], Y[..., None], zz[None, None, :]), -1)
        grid[:, :, k0:k0 + chunk] = field(P)
    return grid, (xs, ys, zs)


def sample_grid_banded(field, lo, hi, step, coarse=4):
    """sample_grid, evaluated finely only within reach of the surface.

    A grid at coarse x step marks every point within two coarse steps of
    the zero set; only those are evaluated at step. Every other point keeps
    the coarse field's sign and size, so the surface's crossings, the only
    values surface nets reads, are exact and the rest are signed correctly."""
    c_grid, (cx, cy, cz) = sample_grid(field, lo, hi + coarse * step, step * coarse)
    xs = np.arange(lo[0], hi[0] + step * 0.5, step)
    ys = np.arange(lo[1], hi[1] + step * 0.5, step)
    zs = np.arange(lo[2], hi[2] + step * 0.5, step)
    ix = np.minimum(np.rint((xs - cx[0]) / (step * coarse)).astype(int), len(cx) - 1)
    iy = np.minimum(np.rint((ys - cy[0]) / (step * coarse)).astype(int), len(cy) - 1)
    iz = np.minimum(np.rint((zs - cz[0]) / (step * coarse)).astype(int), len(cz) - 1)
    grid = c_grid[np.ix_(ix, iy, iz)].astype(np.float32)
    band = np.abs(grid) < 2.0 * step * coarse        # sqrt(3)/2 reach, doubled for the field's approximations
    pts = np.argwhere(band)
    for k in range(0, len(pts), 400000):
        q = pts[k:k + 400000]
        P = np.stack([xs[q[:, 0]], ys[q[:, 1]], zs[q[:, 2]]], 1)
        grid[q[:, 0], q[:, 1], q[:, 2]] = field(P)
    return grid, (xs, ys, zs)


_CUBE = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1], [1, 1, 1]])
_EDGES = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]


def surface_nets(grid, axes):
    """Naive surface nets: one vertex per cell the surface crosses (the mean of
    its edges' zero crossings), one quad per crossed grid edge. The field must
    be positive on the grid's boundary, so the surface is closed."""
    xs, ys, zs = axes
    step = np.array((xs[1] - xs[0], ys[1] - ys[0], zs[1] - zs[0]))
    origin = np.array((xs[0], ys[0], zs[0]))
    if (grid[0] <= 0).any() or (grid[-1] <= 0).any() or (grid[:, 0] <= 0).any() or (grid[:, -1] <= 0).any() \
            or (grid[:, :, 0] <= 0).any() or (grid[:, :, -1] <= 0).any():
        raise ValueError("surface_nets: the surface reaches the grid's boundary")
    inside = grid <= 0
    nx, ny, nz = grid.shape
    corners = [inside[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k] for i, j, k in _CUBE]
    any_in = np.zeros((nx - 1, ny - 1, nz - 1), bool)
    all_in = np.ones_like(any_in)
    for c in corners:
        any_in |= c
        all_in &= c
    active = any_in & ~all_in
    cell = np.argwhere(active)
    index = -np.ones(active.shape, np.int64)
    index[tuple(cell.T)] = np.arange(len(cell))
    vals = [grid[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k][active].astype(np.float64) for i, j, k in _CUBE]
    acc = np.zeros((len(cell), 3))
    cnt = np.zeros(len(cell))
    for a, b in _EDGES:
        va, vb = vals[a], vals[b]
        cross = (va <= 0) != (vb <= 0)
        t = np.where(cross, va / np.where(cross, va - vb, 1.0), 0.0)
        pa, pb = _CUBE[a], _CUBE[b]
        pos = pa[None, :] + (pb - pa)[None, :] * t[:, None]
        acc += np.where(cross[:, None], pos, 0.0)
        cnt += cross
    verts = origin + (cell + acc / cnt[:, None]) * step
    quads = []
    # Each grid edge with a sign change is shared by four cells: a quad.
    for axis in range(3):
        a0 = inside
        sl_a = [slice(None)] * 3
        sl_b = [slice(None)] * 3
        sl_a[axis] = slice(0, -1)
        sl_b[axis] = slice(1, None)
        change = a0[tuple(sl_a)] != a0[tuple(sl_b)]
        e = np.argwhere(change)
        flip = a0[tuple(sl_a)][change]             # inside at the edge's start: orient outward
        o1, o2 = [ax for ax in range(3) if ax != axis]
        ok = (e[:, o1] > 0) & (e[:, o2] > 0) & (e[:, o1] < [nx, ny, nz][o1] - 1) & (e[:, o2] < [nx, ny, nz][o2] - 1)
        e, flip = e[ok], flip[ok]
        c = []
        for d1, d2 in ((0, 0), (1, 0), (1, 1), (0, 1)):
            q = e.copy()
            q[:, o1] -= d1
            q[:, o2] -= d2
            c.append(index[tuple(q.T)])
        c = np.stack(c, 1)
        # The cells run counterclockwise in (o1, o2): the quad faces o1 x o2,
        # which is +axis for a right-handed (axis, o1, o2). Outward is +axis
        # when the edge starts inside; reverse wherever the two disagree.
        right = (o1 - axis) % 3 == 1
        reverse = ~flip if right else flip
        c[reverse] = c[reverse][:, ::-1]
        quads.append(c)
    quads = np.concatenate(quads)
    if (quads < 0).any():
        raise ValueError("surface_nets: a crossed edge lacks one of its four cells")
    return verts, quads


def edge_graph(quads, n):
    e = np.concatenate([quads[:, [0, 1]], quads[:, [1, 2]], quads[:, [2, 3]], quads[:, [3, 0]]])
    e = np.sort(e, 1)
    e = np.unique(e, axis=0)
    return e


def smooth_project(verts, quads, field, iterations=6, lam=0.55, project=True):
    """Laplacian smoothing, each step projected back onto the field's zero set
    along its finite-difference gradient (the voxel terraces go, the shape stays)."""
    v = verts.copy()
    e = edge_graph(quads, len(v))
    deg = np.bincount(e.ravel(), minlength=len(v)).astype(np.float64)
    for _ in range(iterations):
        acc = np.zeros_like(v)
        np.add.at(acc, e[:, 0], v[e[:, 1]])
        np.add.at(acc, e[:, 1], v[e[:, 0]])
        v = v + lam * (acc / deg[:, None] - v)
        if project:
            v = project_to_zero(v, field)
    return v


def project_to_zero(v, field, h=1e-4, steps=2):
    for _ in range(steps):
        d = field(v)
        g = np.stack([(field(v + h * np.eye(3)[i]) - field(v - h * np.eye(3)[i])) / (2 * h) for i in range(3)], 1)
        gn = np.maximum(np.linalg.norm(g, axis=1), 1e-9)
        v = v - (d / gn ** 2)[:, None] * g
    return v


def triangulate(quads, verts):
    """Split each quad along its shorter diagonal."""
    d02 = np.linalg.norm(verts[quads[:, 0]] - verts[quads[:, 2]], axis=1)
    d13 = np.linalg.norm(verts[quads[:, 1]] - verts[quads[:, 3]], axis=1)
    a = quads[d02 <= d13]
    b = quads[d02 > d13]
    return np.concatenate([a[:, [0, 1, 2]], a[:, [0, 2, 3]], b[:, [0, 1, 3]], b[:, [1, 2, 3]]])


def is_closed_manifold(tris):
    """Every edge used by exactly two triangles, once in each direction."""
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    key = e[:, 0].astype(np.int64) * (int(tris.max()) + 1) + e[:, 1]
    rev = e[:, 1].astype(np.int64) * (int(tris.max()) + 1) + e[:, 0]
    u, c = np.unique(key, return_counts=True)
    return bool((c == 1).all() and np.isin(rev, key).all())


def mesh_bow_paw(step=0.0006, smooth=6):
    """The bow paw as a closed triangle mesh, with per-vertex regions."""
    skel = bow_paw_skeleton()

    def field(p):
        return paw_sdf(p, skel)[0]
    pts = np.vstack([c[0] for c in skel["chains"].values()])
    pad = 0.03
    lo, hi = pts.min(0) - pad, pts.max(0) + pad
    grid, axes = sample_grid_banded(field, lo, hi, step)
    verts, quads = surface_nets(grid, axes)
    verts = smooth_project(verts, quads, field, iterations=smooth)
    tris = triangulate(quads, verts)
    _, fields, labels = paw_sdf(verts, skel)
    nearest = np.argmin(np.stack(fields), 0)
    region = np.array(labels, dtype=object)[nearest]
    return {"verts": verts, "tris": tris, "quads": quads, "region": region, "skeleton": skel, "step": step,
            "bounds": (lo, hi)}


# ---------------------------------------------------------------------------
# Fur cards: clumps of hair as tapered ribbons on the skin
# ---------------------------------------------------------------------------
# Each card is one clump drawn from the fur atlas (create_nyaakoto_fp_fur_textures.py):
# a ribbon along a groomed strand, root on the skin, tip lying back toward it.
# v2 (root's review of the first originals: "stiff overlapping white flakes"):
# a cat's paw coat is short and lies flat, 2.5-4 mm on the toes and 5-7.5 mm
# over the metacarpus, longer only at the wrist. Its direction flows: it turns
# gradually over a few millimetres (flow), with little per-clump scatter
# (swirl), and its clumps lie face out (twist). v1's cards were twice as long,
# lifted up to 30 degrees, scattered 13 degrees each and rolled 38.
# v3 (the first lit Unreal originals, Saved/YumiFP/v2, and root's review of
# them: "flecked/flat white fur clumps and dewclaw tuft"): the coat still
# stood up in stiff spikes with a spiky outline, and the dewclaw's tuft read
# as a cotton ball. Lift 7-18 -> 3-9 degrees, with more droop, so the strands
# lie along the skin. Narrower cards, denser (60 -> 80 per cm2, 1.0-1.7 ->
# 0.8-1.3 mm), clumped less (0.45 -> 0.25) and rolled less (14 -> 10
# degrees). The dewclaw's hair is shorter (3.0-4.5 -> 2.2-3.2 mm).
# v4 (capture v4, Saved/YumiFP/v4_*, and root's review: "coarse, blade-like,
# noisy"). The layout is unchanged; how a card shades and faces changes:
# - **Shading normals:** each card vertex's normal is bent skin_normal (0.75)
#   of the way to the skin's normal at its root. v3 exported each card's own
#   face normal, so overlapping cards at slightly different angles lit as
#   separate flat facets, the "blades". A short coat lit by its skin's form
#   reads as one surface.
# - **Front faces outward:** v3's winding faced the skin, so the side a viewer
#   sees was a back face that a two-sided material shades with its normal
#   flipped. Now the visible side is the front, with the bent normal as it is.
# - **Odd atlas rows run root at the top** (create_nyaakoto_fp_fur_textures.py
#   v4), so their v is reversed here: tips abut tips in the atlas, and a mip
#   never pulls a neighbour's opaque root into a tip.
# v5 (capture v5, Saved/YumiFP/v5_fur, and root's review: "flat bright white",
# "angular overlapping strips and pale gaps", "brush-like wrist"). The coat is
# a thin sheet (its strands lie 0.2-1.2 mm off the skin), so its volume has to
# come from shading the paw's form and from each clump's shape. Lift, density,
# lengths and the seeds' layout are v4's.
# - **The hero's white:** TABBY white is the hero fur texture's mean over the
#   atlas's, so the cards' mean colour is the hero's body fur, not a brighter,
#   cooler one.
# - **Form occlusion** (form_occlusion): a distance-field ambient occlusion over
#   the paw with the grip, baked into every card's and the skin's vertex
#   colour. The gaps between the digits and the paw's edge against the leather
#   darken; the knuckles' tops stay open.
# - **The undercoat:** the skin is the coat's bottom, so it sits darker than
#   any card above it (TABBY undercoat), rather than reading as pale gaps.
# - **Clump taper:** a card narrows to tip_width of its root's width, so each
#   clump ends in a point rather than a strip.
# - **Curl:** each strand turns a little in the skin's plane toward its tip,
#   more in the wrist's ruff (curl_deg), so the ruff stops reading as a brush.
#   It is drawn from its own seeded stream, so no v4 card moves for it.
FUR = {
    "seed": 20261025,
    "per_cm2": 80,                       # clumps per square centimetre of furred skin
    "length_m": {"ruff": (0.010, 0.014), "dorsal": (0.0050, 0.0075), "digit": (0.0026, 0.0040),
                 "dewclaw": (0.0022, 0.0032)},
    "width_m": (0.0008, 0.0013),
    "lift_deg": (3.0, 9.0),              # off the skin at the root
    "droop": 0.7,                        # how far the strand bends back toward the skin by its tip
    "flow_deg": 16.0,                    # the coat's slow turn about the normal...
    "flow_wavelength_m": (0.006, 0.014),  # ...over these distances
    "swirl_deg": 4.0,                    # each clump's own scatter on top of the flow
    "twist_deg": 10.0,                   # the card's roll about its strand
    "clump": 0.25,                       # tips pulled toward their clump's direction
    "segments": 4,
    "contact_clear_m": 0.0007,           # no roots where the skin rests on the leather
    "ruff_m": (0.000, 0.022),            # the wrist ruff: from the carpus back toward the forearm
    "sleeve_from_m": -0.026,             # roots stop this far behind the carpus, under the kote's cuff
    "tiles": (8, 2),                     # atlas columns, rows
    "skin_normal": 0.75,                 # how far each card vertex's shading normal is bent to the skin's (v4)
    "tip_width": 0.20,                   # a card's width at its tip, as a share of its root's (v5; v4 0.55)
    "taper_power": 1.3,                  # how that width closes along the strand
    "curl_deg": {"ruff": 16.0, "other": 5.0},   # one standard deviation of a strand's turn by its tip (v5)
    "occlusion": {"steps_m": (0.003, 0.006, 0.012, 0.024), "falloff": 0.6, "floor": 0.45},   # form_occlusion (v5)
}
# white (v5): the hero's fur white, T_Nyaakoto_fur_white_Albedo's mean (0.692, 0.646, 0.574) linear, over the
# fur atlas's coverage-weighted mean hair value (0.933), so a card's mean is the hero's. v4: (0.86, 0.85, 0.82).
# undercoat (v5): the skin under the cards as a share of the coat's colour, the coat's bottom; the skin materials'
# own 0.82 multiplies it again (about 0.59 in all).
TABBY = {"white": (0.742, 0.693, 0.617), "grey": (0.50, 0.50, 0.50), "stripe": (0.20, 0.20, 0.21),
         "period_m": 0.015, "white_from_knuckles_m": -0.010, "undercoat": 0.72}
# ---------------------------------------------------------------------------
# Shell fur (v6): the coat as translucent offset layers of the skin, not cards.
# Root's reviews of captures v5 and v6: the masked cards read as "bright
# angular white flakes over dark gaps". Their two failure modes come from one
# construction, masked cards on a thin sheet: thin alpha dithered into speckle
# (v3), and opaque cores tiled into a patchwork (v4, v5). Shells stack layers
# of the skin, each drawing only the cross-sections of the strands that reach
# its height (create_nyaakoto_fp_shell_texture.py). Every gap is deeper coat;
# a translucent material has no dither; nothing has a card's outline.
# - **The layers:** `layers` shells on the paw's own coarser skin (step_m), at
#   h_i = H x ((i + 0.5) / layers)^spacing_power. H is the coat's height by
#   region, clamped clear of the bow.
# - **The comb:** each shell slides along the coat's flow (coat_flow, as the
#   cards) by h x tan(lean_deg), so the strands lean as the coat lies.
# - **The colour:** the tabby colour, the form's occlusion, and a self-shadow
#   from deep_shade at the skin to 1 at the top. Alpha is the shell's height
#   share, which the material uses to pick the strand texture's channels.
# - **The UVs:** a box projection of the base skin, one texture tile per
#   uv_tile_m, shared by every shell, so a strand stays one column.
# Fins for silhouettes are not built: shells' layered edges are the known
# limit of the method, to judge in the capture.
FUR_MODE = "shells"                      # v6: the coat as shells; "cards" builds v5's fur cards instead
SHELLS = {
    "layers": 10,
    "step_m": 0.0016,                    # the shells' own skin (surface nets), coarser than the skin's 0.9 mm
    "height_m": {"ruff": 0.0030, "dorsal": 0.0018, "digit": 0.0012, "dewclaw": 0.0010},
    "first_m": 0.00015,                  # the lowest shell's least height above the skin
    "spacing_power": 1.15,               # shells closer together near the skin
    "lean_deg": 50.0,                    # the comb along the coat's flow
    "clear_m": 0.0004,                   # shells stop this far off the bow
    "uv_tile_m": 0.004,                  # create_nyaakoto_fp_shell_texture.TILE_MM
    "deep_shade": 0.55,                  # the lowest shell's colour, as a share of the top's
}


def vertex_normals(V, T):
    n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, T[:, k], n)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)


def _segments(skel):
    """Every bone of the skeleton as (a, b, chain name, last of a digit),
    proximal to distal. The forearm chain runs elbow to wrist, so distal is
    toward the paw there too."""
    out = []
    for name, (pts, _r) in skel["chains"].items():
        for j in range(len(pts) - 1):
            tip = j == len(pts) - 2 and (name in DIGITS or name == "I")
            out.append((pts[j], pts[j + 1], name, tip))
    return out


def _nearest_segment(p, segs):
    A = np.array([s[0] for s in segs])
    B = np.array([s[1] for s in segs])
    ab = B - A
    t = np.clip(np.einsum("nsi,si->ns", p[:, None, :] - A[None], ab) / np.einsum("si,si->s", ab, ab), 0.0, 1.0)
    q = A[None] + t[..., None] * ab[None]
    d = np.linalg.norm(p[:, None, :] - q, axis=2)
    k = np.argmin(d, 1)
    return k, ab[k] / np.linalg.norm(ab[k], axis=1, keepdims=True), t[np.arange(len(p)), k]


def fur_region(region):
    """The fur class of each skin vertex label, or None for bare skin."""
    out = []
    for r in region:
        r = str(r)
        if r.startswith("pad"):
            out.append(None)
        elif r == "digit_I":
            out.append("dewclaw")
        elif r.startswith("digit"):
            out.append("digit")
        else:
            out.append("dorsal")
    return np.array(out, dtype=object)


def tabby_colour(p, skel):
    """Grey tabby proximally with dark stripes round the arm; white toes."""
    wrist = skel["wrist"]
    axis = -FOREARM_DIR                                      # toward the paw
    s = (p - wrist) @ axis                                   # metres distal of the carpus
    knuckles = np.array([skel["chains"][n][0][0] for n in DIGITS]).mean(0)
    s_k = float((knuckles - wrist) @ axis)
    rng = np.random.default_rng(FUR["seed"] + 7)
    phase = rng.random() * 2 * math.pi
    wobble = 0.004 * np.sin(p[:, 2] * 260.0 + phase) + 0.003 * np.sin(p[:, 1] * 330.0)
    stripe = 0.5 + 0.5 * np.cos(2 * math.pi * (s + wobble) / TABBY["period_m"])
    stripe = np.clip((stripe - 0.62) / 0.25, 0.0, 1.0)
    grey = np.array(TABBY["grey"])[None] * (1 - stripe[:, None]) + np.array(TABBY["stripe"])[None] * stripe[:, None]
    w = np.clip((s - (s_k + TABBY["white_from_knuckles_m"])) / 0.012 + 0.5 + wobble / 0.012, 0.0, 1.0)
    w = w * w * (3 - 2 * w)
    return grey * (1 - w[:, None]) + np.array(TABBY["white"])[None] * w[:, None]


def form_occlusion(points, normals, occluder, cfg=FUR["occlusion"]):
    """How open each point is above itself, 1 open to 0 closed: Quilez's distance-field ambient occlusion.

    At each step h along the normal, the occluder's distance falls short of h wherever the form closes in. The
    shortfalls, weighted by falloff^i, are summed and normalised. With the paw and the grip as the occluder, the gaps
    between the digits and the paw's edge against the leather darken, and the knuckles' tops stay open."""
    occ = np.zeros(len(points))
    total, w = 0.0, 1.0
    for h in cfg["steps_m"]:
        d = occluder(points + normals * h)
        occ += w * np.clip(h - d, 0.0, None) / h
        total += w
        w *= cfg["falloff"]
    return np.clip(1.0 - occ / total, 0.0, 1.0)


def occlusion_shade(ao, cfg=FUR["occlusion"]):
    """The colour factor for an occlusion: floor where closed, 1 where open."""
    return cfg["floor"] + (1.0 - cfg["floor"]) * ao


def skin_colour(mesh, occluder, cfg=FUR):
    """The skin's vertex colour, the coat's bottom: the tabby colour at TABBY undercoat, darkened by the form's
    occlusion (the pads' material does not read it)."""
    V, T = mesh["verts"], mesh["tris"]
    ao = form_occlusion(V, vertex_normals(V, T), occluder, cfg["occlusion"])
    return tabby_colour(V, mesh["skeleton"]) * (TABBY["undercoat"] * occlusion_shade(ao, cfg["occlusion"]))[:, None]


def fur_shells(skel, field, keep_out=grip_sdf, cfg=SHELLS, fur=FUR, base=None):
    """The coat as shells: verts, tris (outward), uv, colour (RGBA; A the shell's height share), normals, and counts.

    ``base`` is the shells' own skin mesh (mesh_bow_paw at step_m unless given). Only furred skin grows shells: not
    the pads, not where the skin rests on the leather, not under the kote's sleeve, by the cards' rules."""
    if base is None:
        base = mesh_bow_paw(step=cfg["step_m"], smooth=6)
    V, T = base["verts"], base["tris"]
    N = vertex_normals(V, T)
    cls = fur_region(base["region"])
    s = (V - skel["wrist"]) @ (-FOREARM_DIR)
    furred = np.array([c is not None for c in cls]) & (keep_out(V) > fur["contact_clear_m"]) & (s > fur["sleeve_from_m"])
    keep_tri = furred[T].all(1)
    used = np.unique(T[keep_tri])
    remap = -np.ones(len(V), np.int64)
    remap[used] = np.arange(len(used))
    Vb, Nb, Tb, kind, sb = V[used], N[used], remap[T[keep_tri]], cls[used], s[used]
    ruff = (sb > -fur["ruff_m"][1]) & (sb < fur["ruff_m"][0] + 0.012) & (kind == "dorsal")
    H = np.array([cfg["height_m"]["ruff" if r else str(k)] for r, k in zip(ruff, kind)])
    H = np.minimum(H, np.maximum(keep_out(Vb) - cfg["clear_m"], 0.0))
    # The coat's flow, as the cards': the nearest bone's distal direction in the skin's plane, turned by coat_flow.
    _k, distal, _t = _nearest_segment(Vb, _segments(skel))
    tang = distal - Nb * np.einsum("ij,ij->i", distal, Nb)[:, None]
    tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-9)
    side = np.cross(Nb, tang)
    turn = np.radians(coat_flow(Vb, fur))
    tang = tang * np.cos(turn)[:, None] + side * np.sin(turn)[:, None]
    lean = math.tan(math.radians(cfg["lean_deg"]))
    axis = np.argmax(np.abs(Nb), 1)
    uv = np.stack([np.where(axis == 0, Vb[:, 1], Vb[:, 0]), np.where(axis == 2, Vb[:, 1], Vb[:, 2])], 1) / cfg["uv_tile_m"]
    both = lambda p: np.minimum(field(p), keep_out(p))
    colour = tabby_colour(Vb, skel) * occlusion_shade(form_occlusion(Vb, Nb, both, fur["occlusion"]), fur["occlusion"])[:, None]
    L = cfg["layers"]
    verts, cols, tris, share = [], [], [], []
    for i in range(L):
        frac = ((i + 0.5) / L) ** cfg["spacing_power"]
        h = np.maximum(H * frac, np.minimum(cfg["first_m"], H))
        P = Vb + Nb * h[:, None] + tang * (h * lean)[:, None]
        for f in (0.6, 0.3, 0.0):                                # never into the bow: slide back toward the base
            bad = keep_out(P) < cfg["clear_m"]
            if not bad.any():
                break
            P[bad] = Vb[bad] + (P[bad] - Vb[bad]) * f
        shade = cfg["deep_shade"] + (1.0 - cfg["deep_shade"]) * (i + 0.5) / L
        verts.append(P)
        cols.append(np.concatenate([colour * shade, np.full((len(Vb), 1), frac)], 1))
        tris.append(Tb + i * len(Vb))
        share.append(frac)
    return {"verts": np.concatenate(verts), "tris": np.concatenate(tris), "uv": np.tile(uv, (L, 1)),
            "colour": np.concatenate(cols), "normals": np.tile(Nb, (L, 1)), "layers": L, "base_vertices": len(Vb),
            "height_m": H, "shares": share, "base": base}


def coat_flow(points, cfg=FUR):
    """The coat's slow turn about the skin's normal at points, in degrees: a few seeded plane waves over the skin,
    so neighbouring clumps turn together (fur_cards; fur_shells combs along the same field)."""
    waves = np.random.default_rng(cfg["seed"] + 1)
    flow = np.zeros(len(points))
    for _ in range(4):
        k = waves.normal(size=3)
        k *= 2 * np.pi / (np.linalg.norm(k) * waves.uniform(*cfg["flow_wavelength_m"]))
        flow += np.sin(points @ k + waves.uniform(0, 2 * np.pi))
    return flow * (cfg["flow_deg"] / 2.0)                    # four unit waves: about +-1 standard deviation each


def fur_cards(mesh, field, keep_out=grip_sdf, cfg=FUR):
    """Fur cards on a skin mesh: verts, tris (front faces out), uvs, colours, shading normals and the card count.

    Roots are area-sampled on furred triangles away from contact. Each strand
    starts along its nearest bone's distal direction in the skin's tangent
    plane, swirled and lifted, then droops back toward the skin. Tips pull
    toward their clump, and each turns by its own curl. Strand points that would enter the bow (keep_out) end
    the strand; points that dip into the skin are pushed back out of it. Each card narrows to tip_width, and its
    colour is the tabby colour shaded by the form's occlusion at each strand point (form_occlusion, over the skin
    and keep_out together)."""
    rng = np.random.default_rng(cfg["seed"])
    V, T = mesh["verts"], mesh["tris"]
    skel = mesh["skeleton"]
    N = vertex_normals(V, T)
    cls = fur_region(mesh["region"])
    tri_cls = cls[T[:, 0]]
    furred = np.array([c is not None for c in tri_cls])
    tri_c = V[T].mean(1)
    furred &= keep_out(tri_c) > cfg["contact_clear_m"]
    # Under the kote sleeve, behind the ruff, nothing shows: no roots there.
    furred &= (tri_c - skel["wrist"]) @ (-FOREARM_DIR) > cfg["sleeve_from_m"]
    area = 0.5 * np.linalg.norm(np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]), axis=1)
    area = np.where(furred, area, 0.0)
    count = int(round(area.sum() * 1e4 * cfg["per_cm2"]))
    pick = rng.choice(len(T), size=count, p=area / area.sum())
    r1, r2 = rng.random(count), rng.random(count)
    su = np.sqrt(r1)
    bary = np.stack([1 - su, su * (1 - r2), su * r2], 1)
    root = (V[T[pick]] * bary[:, :, None]).sum(1)
    n = (N[T[pick]] * bary[:, :, None]).sum(1)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    kind = tri_cls[pick]
    segs = _segments(skel)
    seg_k, distal, seg_t = _nearest_segment(root, segs)
    # Over a digit's end cap the distal direction projects radially: hair
    # there lies short and flat over the tip instead of bursting from it.
    cap = np.array([segs[k][3] for k in seg_k]) & (seg_t > 0.97)
    tang = distal - n * np.einsum("ij,ij->i", distal, n)[:, None]
    tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-9)
    side = np.cross(n, tang)
    # The coat's direction field (coat_flow), plus each clump's own small scatter.
    flow = coat_flow(root, cfg)
    swirl = np.radians(flow + rng.normal(0.0, cfg["swirl_deg"], count))
    tang = tang * np.cos(swirl)[:, None] + side * np.sin(swirl)[:, None]
    side = np.cross(n, tang)
    # The wrist ruff: longer hair near the carpus.
    s = (root - skel["wrist"]) @ (-FOREARM_DIR)
    ruff = (s > -cfg["ruff_m"][1]) & (s < cfg["ruff_m"][0] + 0.012) & (kind == "dorsal")
    length = np.empty(count)
    for name, (lo_l, hi_l) in cfg["length_m"].items():
        sel = (kind == name) if name != "ruff" else ruff
        if name == "dorsal":
            sel &= ~ruff
        length[sel] = rng.uniform(lo_l, hi_l, int(sel.sum()))
    # Clumps: every root follows the nearest of a sparse set of leaders.
    leaders = rng.choice(count, size=max(1, count // 6), replace=False)
    d2 = ((root[:, None, :] - root[None, leaders, :]) ** 2).sum(2) if count * len(leaders) < 4e7 else None
    if d2 is None:
        lead = np.empty(count, int)
        for k0 in range(0, count, 2000):
            dd = ((root[k0:k0 + 2000, None, :] - root[None, leaders, :]) ** 2).sum(2)
            lead[k0:k0 + 2000] = leaders[np.argmin(dd, 1)]
    else:
        lead = leaders[np.argmin(d2, 1)]
    length[cap] *= 0.42
    lift = np.radians(rng.uniform(*cfg["lift_deg"], count))
    lift[cap] *= 0.35
    K = cfg["segments"]
    pts = np.zeros((count, K + 1, 3))
    pts[:, 0] = root
    dirs0 = tang * np.cos(lift)[:, None] + n * np.sin(lift)[:, None]
    # v5: each strand's curl, from its own stream so the cards drawn below are v4's.
    curl = np.radians(np.random.default_rng(cfg["seed"] + 2).normal(0.0, 1.0, count)
                      * np.where(ruff, cfg["curl_deg"]["ruff"], cfg["curl_deg"]["other"]))
    for k in range(1, K + 1):
        u = k / K
        # droop: the lift fades toward the tip, and the clump pulls the tip; curl turns it in the skin's plane.
        a = lift * (1.0 - cfg["droop"] * u)
        c = curl * u ** 1.5
        turned = tang * np.cos(c)[:, None] + side * np.sin(c)[:, None]
        d = turned * np.cos(a)[:, None] + n * np.sin(a)[:, None]
        d = d * (1 - cfg["clump"] * u) + dirs0[lead] * (cfg["clump"] * u)
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        pts[:, k] = pts[:, k - 1] + d * (length / K)[:, None]
    # Out of the skin, and never into the bow.
    for k in range(1, K + 1):
        dskin = field(pts[:, k])
        under = dskin < 0.0002
        if under.any():
            h = 1e-4
            g = np.stack([(field(pts[under, k] + h * np.eye(3)[i]) - field(pts[under, k] - h * np.eye(3)[i])) / (2 * h)
                          for i in range(3)], 1)
            g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
            pts[under, k] += g * (0.0002 - dskin[under])[:, None]
    alive = np.ones((count, K + 1), bool)
    for k in range(1, K + 1):
        alive[:, k] = alive[:, k - 1] & (keep_out(pts[:, k]) > 0.0003)
    keep = alive[:, 2]                                       # at least half a strand stands
    pts, n, side, alive = pts[keep], n[keep], side[keep], alive[keep]
    for k in range(1, K + 1):                                 # a cut strand ends at its last free point
        pts[~alive[:, k], k] = pts[~alive[:, k], k - 1]
    m = len(pts)
    twist = np.radians(rng.normal(0.0, cfg["twist_deg"], m))
    keep_card = np.ones(m, bool)
    width = rng.uniform(*cfg["width_m"], m)
    cols, rows = cfg["tiles"]
    tile = rng.integers(0, cols * rows, m)
    tu, tv = (tile % cols) / cols, (tile // cols) / rows
    flip = (tile // cols) % 2 == 1                          # odd atlas rows run root at the top
    verts = np.zeros((m, K + 1, 2, 3))
    uvs = np.zeros((m, K + 1, 2, 2))
    normals = np.zeros((m, K + 1, 2, 3))
    for k in range(K + 1):
        t = pts[:, min(k + 1, K)] - pts[:, max(k - 1, 0)]
        t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-12)
        b = np.cross(t, n)
        b /= np.maximum(np.linalg.norm(b, axis=1, keepdims=True), 1e-12)
        nb = np.cross(b, t)                                  # the untwisted card's normal, out from the skin
        b = b * np.cos(twist)[:, None] + nb * np.sin(twist)[:, None]
        face = np.cross(b, t)                                # the twisted card's: its front, outward
        w = width * (1.0 - (1.0 - cfg["tip_width"]) * (k / K) ** cfg["taper_power"]) * 0.5
        verts[:, k, 0] = pts[:, k] - b * w[:, None]
        verts[:, k, 1] = pts[:, k] + b * w[:, None]
        frac = np.where(flip, 1.0 - k / K, k / K)
        uvs[:, k, 0] = np.stack([tu, tv + frac / rows], 1)
        uvs[:, k, 1] = np.stack([tu + 1.0 / cols, tv + frac / rows], 1)
        shade = (1.0 - cfg["skin_normal"]) * face + cfg["skin_normal"] * n
        shade /= np.maximum(np.linalg.norm(shade, axis=1, keepdims=True), 1e-12)
        normals[:, k, 0] = normals[:, k, 1] = shade
    # A card's edges, not only its strand, stay out of the bow: an edge vertex
    # that would enter it slides back toward the strand until it is clear.
    flat = verts.reshape(-1, 3)
    centre = np.repeat(pts[:, :, None, :], 2, axis=2).reshape(-1, 3)
    for frac in (0.6, 0.3, 0.0):
        inside = keep_out(flat) < 0.0002
        if not inside.any():
            break
        flat[inside] = centre[inside] + (flat[inside] - centre[inside]) * frac
    verts = flat.reshape(m, K + 1, 2, 3)
    base = np.arange(m)[:, None] * (2 * (K + 1))
    quads = []
    for k in range(K):
        a, b = 2 * k, 2 * k + 1
        # Left, right, then up the strand: the front faces out (b x t), the side a viewer sees.
        quads.append(np.stack([base[:, 0] + a, base[:, 0] + b, base[:, 0] + b + 2, base[:, 0] + a + 2], 1))
    quads = np.stack(quads, 1).reshape(-1, 4)
    tris = np.concatenate([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])
    colour = tabby_colour(pts[:, 0], skel)
    ao = form_occlusion(pts.reshape(-1, 3), np.repeat(n, K + 1, axis=0),
                        lambda p: np.minimum(field(p), keep_out(p)), cfg["occlusion"]).reshape(m, K + 1)
    shade = occlusion_shade(ao, cfg["occlusion"])
    vcol = np.repeat(colour[:, None, None, :] * shade[:, :, None, None], 2, axis=2).reshape(-1, 3)
    return {"verts": verts.reshape(-1, 3), "tris": tris, "uv": uvs.reshape(-1, 2), "colour": vcol, "cards": m,
            "normals": normals.reshape(-1, 3), "root_normals": n, "roots": pts[:, 0], "tips": pts[:, -1],
            "occlusion": ao, "attempted": count}
