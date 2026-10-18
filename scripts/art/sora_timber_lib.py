"""Unique Nanite timbers: every member is cut from its own 3D log.

A member (column, beam, rail or board) is a dense surface mesh whose geometry
carries the macro detail: plane strokes or chona adze scallops, worn round-over
arrises, drying checks that follow the spiral grain, knots with their own swell,
dents and a slight bow. Rows of vertices run along the member. Each row samples
the section at a base spacing on visible faces (coarse on faces hidden in the
wall) and refines across checks, knots and the arrises; neighbouring rows are
stitched with a ladder triangulation, so detail costs triangles only where it
is.

The fine ring figure is not geometry. Each vertex stores where it lies in its
log: UV2 is the offset from the pith in the cross-section (warped by the ring
wobble and the swirl around knots, and replaced inside a knot by the knot's own
frame), UV3 is the height along the pith and a per-log seed. A material turns
these into growth rings, so faces, arrises, check walls and end grain agree.
Vertex colour carries masks: R cavity, G wear, B soot, A knot.

The fields are numpy only; mesh creation and export need Blender 5.2. Units are
metres. Member frame: Z along the length from 0, X across the width, Y across
the depth, the section centred on the Z axis. Faces run counter-clockwise seen
from +Z: 0 is +X, 1 is +Y, 2 is -X, 3 is -Y; corner c joins face c to face c+1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

TAU = 2.0 * math.pi
FACE_N = np.array([(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)])
FACE_T = np.array([(0.0, 1.0), (-1.0, 0.0), (0.0, -1.0), (1.0, 0.0)])
CORNER_SIGN = np.array([(1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0), (1.0, -1.0)])


# ---------------------------------------------------------------------------
# Deterministic hashing (no global random state; every value is positional)
# ---------------------------------------------------------------------------

_GOLD = np.uint64(0x9E3779B97F4A7C15)
_M1 = np.uint64(0xBF58476D1CE4E5B9)
_M2 = np.uint64(0x94D049BB133111EB)


def _mix(x):
    x = (x ^ (x >> np.uint64(30))) * _M1
    x = (x ^ (x >> np.uint64(27))) * _M2
    return x ^ (x >> np.uint64(31))


def hash01(seed: int, *keys) -> np.ndarray:
    """Uniform [0, 1) from integer keys (broadcast), stable across platforms."""
    shape = np.broadcast(*[np.asarray(k) for k in keys]).shape if keys else ()
    with np.errstate(over="ignore"):
        h = np.full(shape, np.uint64(seed & 0xFFFFFFFF) * _GOLD + _GOLD, dtype=np.uint64)
        for k in keys:
            h = _mix(h ^ (np.asarray(k).astype(np.int64).astype(np.uint64) * _GOLD + _GOLD))
    return (h >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


class Waves:
    """A smooth band-limited field: a sum of random plane waves in (u, v)."""

    def __init__(self, rng: np.random.Generator, terms: int, wavelengths, amplitude, periodic_u=None):
        lo, hi = wavelengths
        lam = np.exp(rng.uniform(math.log(lo), math.log(hi), terms))
        ang = rng.uniform(0, TAU, terms)
        self.ku = np.cos(ang) * TAU / lam
        self.kv = np.sin(ang) * TAU / lam
        if periodic_u:
            # Integer harmonics around a closed loop of length periodic_u.
            self.ku = np.round(self.ku * periodic_u / TAU) * TAU / periodic_u
        self.ph = rng.uniform(0, TAU, terms)
        # Larger waves carry more amplitude (a red spectrum), normalised to rms.
        w = lam / lam.max()
        self.a = amplitude * w / math.sqrt(max(1e-12, float(np.sum(w * w)) / 2.0))

    def __call__(self, u, v):
        u = np.asarray(u, np.float64)[..., None]
        v = np.asarray(v, np.float64)[..., None]
        return np.sum(self.a * np.cos(self.ku * u + self.kv * v + self.ph), axis=-1)


# ---------------------------------------------------------------------------
# The log a member is cut from
# ---------------------------------------------------------------------------

@dataclass
class Knot:
    z: float            # height where the branch leaves the pith
    azimuth: float      # direction of the branch in the section (radians)
    rise: float         # branch angle above horizontal (radians)
    r0: float           # knot radius at the pith
    flare: float        # radius gained per metre of branch
    dead: bool          # dead (black, loose-edged) or intergrown (red)
    bulge: float        # proud (+) or sunken (-) at the surface, metres


@dataclass
class Check:
    face: int
    u0: float           # position across the face at z0
    drift: float        # du/dz from the spiral grain
    z0: float
    z1: float
    width: float        # opening at the surface
    depth: float        # depth into the wood


@dataclass
class Log:
    seed: int
    pith: tuple[float, float]      # pith (x, y) at z = 0, member frame
    lean: tuple[float, float]      # pith dx/dz, dy/dz
    ring_width: float              # mean ring width
    knots: list[Knot] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    sweep: Waves | None = None     # pith wander (x and y share the field, phase-shifted)
    wobble: Waves | None = None    # ring-radius wobble over (theta*r0, z)
    swirl: float = 0.55            # ring bulge around knots, in knot radii

    def pith_at(self, z):
        z = np.asarray(z, np.float64)
        px = self.pith[0] + self.lean[0] * z
        py = self.pith[1] + self.lean[1] * z
        if self.sweep is not None:
            px = px + self.sweep(z, 0.0)
            py = py + self.sweep(z + 17.3, 0.0)
        return px, py


# ---------------------------------------------------------------------------
# Member description
# ---------------------------------------------------------------------------

@dataclass
class Member:
    name: str
    length: float
    width: float
    depth: float
    log: Log
    finish: tuple[str, str, str, str] = ("planed",) * 4   # per face: planed | adze | hidden
    visible: tuple = (None, None, None, None)  # per face: (u_min, u_max) detailed range, None = all
    arris_r: tuple = (0.0025,) * 4             # per corner nominal radius
    arris_p: float = 1.25                      # superellipse exponent: 1 flat chamfer, 2 round
    arris_wear: tuple = (0.0,) * 4             # per corner extra radius where handled
    handling: tuple = (1.2, 0.45)              # handling height centre and spread (m)
    spacing: float = 0.004                     # base vertex spacing on detailed faces
    hidden_spacing: float = 0.025              # spacing on hidden faces / ranges
    corner_samples: int = 10
    dents: int = 24
    dent_zone: tuple = (0.3, 2.0)
    bow: float = 0.0012                        # mid-length bow (m)
    soot_from: float = 2.0                     # soot increases above this height
    seed: int = 0
    end_caps: bool = True
    offset: tuple = (0.0, 0.0, 0.0)            # export translation (kit pivot)
    fallback: bool = False                     # coarse SM5 fallback: macro shape only, detail baked
    fallback_spacing: float = 0.02


def fallback_of(m: Member) -> Member:
    """The same member as the SM5 fallback: the same log, seeds, arrises and
    bow, sampled coarsely. Its checks stay geometry (a 2K bake can't resolve a
    millimetre-wide crack); knots, dents and plane strokes go to the bake."""
    import dataclasses
    return dataclasses.replace(m, name=m.name + "_Fallback", fallback=True, spacing=m.fallback_spacing,
                               hidden_spacing=max(m.hidden_spacing, 2 * m.fallback_spacing), corner_samples=4)


# ---------------------------------------------------------------------------
# Section geometry
# ---------------------------------------------------------------------------

def _corner_points(c, t, R, p, half_w, half_d):
    """Superellipse corner c at parameter t in [0, pi/2): position and normal."""
    sx, sy = CORNER_SIGN[c]
    # Local angle runs from the face c end (t=0) to the face c+1 start (pi/2).
    base = c * (math.pi / 2)
    a = base + t
    ca, sa = np.cos(a), np.sin(a)
    e = 2.0 / p
    lx = np.sign(ca) * np.abs(ca) ** e
    ly = np.sign(sa) * np.abs(sa) ** e
    cx = sx * (half_w - R)
    cy = sy * (half_d - R)
    x = cx + R * lx
    y = cy + R * ly
    nx = np.sign(lx) * np.abs(lx) ** (p - 1)
    ny = np.sign(ly) * np.abs(ly) ** (p - 1)
    nn = np.hypot(nx, ny) + 1e-12
    return x, y, nx / nn, ny / nn


def _face_span(f, half_w, half_d, R):
    """Face f's u range between its two corners' tangent points."""
    half = half_d if f % 2 == 0 else half_w
    return -half + R[(f - 1) % 4], half - R[f]


def _face_xy(f, u, half_w, half_d):
    n = FACE_N[f]
    t = FACE_T[f]
    h = half_w if f % 2 == 0 else half_d
    return n[0] * h + t[0] * u, n[1] * h + t[1] * u


# ---------------------------------------------------------------------------
# Log construction
# ---------------------------------------------------------------------------

def make_log(seed, length, *, cut="boxed_heart", width=0.24, depth=0.24, ring_width=0.0019,
             knot_count=(3, 7), knot_size=(0.003, 0.007), check_count=(2, 5), check_faces=(3, 0, 2),
             check_u=None, check_width=(0.0004, 0.0016), check_depth=(0.004, 0.028), check_length=(0.12, 1.3),
             check_cover=None):
    """A log for a member. ``cut``: boxed_heart (pith inside), flat (pith below
    the -Y face: flat-sawn figure on +Y), quarter (pith beside the -X face).
    ``check_u`` optionally maps a face to the (u_min, u_max) its checks start in,
    so checks land on the visible part of a face. ``check_cover`` (z0, z1) makes
    the first check, on ``check_faces[0]``, span that height range."""
    rng = np.random.default_rng(seed)
    if cut == "boxed_heart":
        pith = (rng.normal(0, 0.012), rng.normal(0, 0.012))
    elif cut == "flat":
        pith = (rng.normal(0, 0.02), -depth / 2 - rng.uniform(0.05, 0.22))
    else:  # quarter
        pith = (-width / 2 - rng.uniform(0.06, 0.20), rng.normal(0, 0.01))
    lean = (rng.normal(0, 0.0025), rng.normal(0, 0.0025))
    sweep = Waves(rng, 5, (1.5, 9.0), 0.004)
    wobble = Waves(rng, 18, (0.012, 0.9), 0.0011)
    log = Log(seed=seed, pith=pith, lean=lean, ring_width=ring_width, sweep=sweep, wobble=wobble)
    # Knots: whorls of 2-4 branches at a few heights (conifers branch in whorls).
    n_knots = int(rng.integers(*knot_count))
    z_whorls = np.sort(rng.uniform(0.05 * length, 0.95 * length, max(1, n_knots // 2)))
    for _ in range(n_knots):
        zw = float(rng.choice(z_whorls)) + rng.normal(0, 0.03)
        log.knots.append(Knot(z=zw, azimuth=float(rng.uniform(0, TAU)), rise=math.radians(rng.uniform(8, 35)),
                              r0=float(rng.uniform(0.0012, 0.0022)),
                              flare=float(rng.uniform(*knot_size)) / 0.12,
                              dead=bool(rng.random() < 0.35), bulge=float(rng.normal(0.0, 0.00018))))
    # Drying checks: boxed-heart timber checks mid-face, along the spiral grain.
    n_checks = int(rng.integers(*check_count))
    for i in range(n_checks):
        f = int(check_faces[0]) if (i == 0 and check_cover) else int(rng.choice(check_faces))
        half = (depth if f % 2 == 0 else width) / 2
        ln = float(rng.uniform(*check_length))
        z0 = float(rng.uniform(0.0, max(0.01, length - ln)))
        if i == 0 and check_cover:
            c0, c1 = check_cover
            ln = max(ln, (c1 - c0) * 1.15)
            z0 = float(np.clip(rng.uniform(c1 - ln, c0), 0.0, max(0.0, length - ln)))
        if check_u and f in check_u:
            u0 = float(rng.uniform(*check_u[f]))
        else:
            u0 = float(rng.normal(0, 0.25 * half))
        log.checks.append(Check(face=f, u0=u0, drift=float(rng.normal(0, 0.012)),
                                z0=z0, z1=z0 + ln, width=float(rng.uniform(*check_width)),
                                depth=float(rng.uniform(*check_depth))))
    return log


# ---------------------------------------------------------------------------
# Sampling: rows along Z, samples around the section
# ---------------------------------------------------------------------------

@dataclass
class Samples:
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    nx: np.ndarray
    ny: np.ndarray
    seg: np.ndarray      # 0..7: face0, corner0, face1, ...
    u: np.ndarray        # face coordinate (faces) or corner parameter t (corners)
    tau: np.ndarray      # perimeter order key in [0, 8)
    detail: np.ndarray   # 1 on detailed (visible) ranges, 0 on hidden ones
    row_start: np.ndarray
    row_count: np.ndarray


def _knot_footprints(m: Member):
    """Approximate each knot's surface footprint per face: (face, u_c, z_c, a_u, a_z)."""
    half_w, half_d = m.width / 2, m.depth / 2
    out = []
    for k in m.log.knots:
        px, py = m.log.pith_at(k.z)
        d = np.array([math.cos(k.azimuth) * math.cos(k.rise), math.sin(k.azimuth) * math.cos(k.rise), math.sin(k.rise)])
        for f in range(4):
            n = FACE_N[f]
            h = half_w if f % 2 == 0 else half_d
            denom = n[0] * d[0] + n[1] * d[1]
            if denom <= 0.15:
                continue
            t = (h - (n[0] * px + n[1] * py)) / denom
            if t <= 0:
                continue
            hit = np.array([px, py, k.z]) + t * d
            u = FACE_T[f][0] * hit[0] + FACE_T[f][1] * hit[1]
            span = _face_span(f, half_w, half_d, (0, 0, 0, 0))
            r = k.r0 + k.flare * t
            if not (span[0] - r < u < span[1] + r) or not (0 < hit[2] < m.length):
                continue
            stretch = 1.0 / max(0.25, denom)
            out.append((f, float(u), float(hit[2]), r * 1.25, r * 1.25 * stretch))
    return out


def sample_member(m: Member) -> Samples:
    half_w, half_d = m.width / 2, m.depth / 2
    rng = np.random.default_rng(m.seed + 7001)
    sp = m.spacing
    # Rows: the base grid plus fine rows across knots' footprints.
    zs = [np.arange(0.0, m.length + 1e-9, sp)]
    if zs[0][-1] < m.length - 1e-6:
        zs.append(np.array([m.length]))
    feet = [] if m.fallback else _knot_footprints(m)
    for f, u, zc, au, az in feet:
        if m.finish[f] == "hidden" or not _visible(m, f, u):
            continue
        zs.append(np.arange(max(0.0, zc - az * 1.3), min(m.length, zc + az * 1.3), sp / 4.0))
    z_rows = np.unique(np.round(np.concatenate(zs), 7))
    z_rows = z_rows[(z_rows >= 0) & (z_rows <= m.length)]
    # Corner radius along Z: nominal + wear at handling height + slow variation.
    hz, hs = m.handling
    corner_var = [Waves(rng, 6, (0.15, 2.5), 1.0) for _ in range(4)]
    xs, ys, zz, nxs, nys, segs, us, taus, dets, starts, counts = ([] for _ in range(11))
    total = 0
    tc = np.linspace(0.0, math.pi / 2, m.corner_samples, endpoint=False)
    for z in z_rows:
        handled = math.exp(-((z - hz) / hs) ** 2)
        R = []
        P = []
        for c in range(4):
            var = float(corner_var[c](z, 0.0))
            r = m.arris_r[c] * (1.0 + 0.18 * var) + m.arris_wear[c] * handled * (0.75 + 0.25 * var)
            r = max(0.0006, r)
            R.append(r)
            wear_frac = min(1.0, m.arris_wear[c] * handled / max(1e-6, m.arris_r[c] + m.arris_wear[c]))
            P.append(m.arris_p + (2.0 - m.arris_p) * wear_frac)
        row_x, row_y, row_nx, row_ny, row_seg, row_u, row_tau, row_det = ([] for _ in range(8))
        for f in range(4):
            u0, u1 = _face_span(f, half_w, half_d, R)
            vis = m.visible[f]
            hidden = m.finish[f] == "hidden"
            pts = [np.array([u0])]
            if hidden:
                g = np.arange(math.ceil(u0 / m.hidden_spacing), math.floor(u1 / m.hidden_spacing) + 1) * m.hidden_spacing
                pts.append(g)
            else:
                g = np.arange(math.ceil(u0 / sp), math.floor(u1 / sp) + 1) * sp
                if vis is not None:
                    keep = (g >= vis[0] - sp) & (g <= vis[1] + sp)
                    coarse = np.arange(math.ceil(u0 / m.hidden_spacing), math.floor(u1 / m.hidden_spacing) + 1) * m.hidden_spacing
                    coarse = coarse[(coarse < vis[0] - 3 * sp) | (coarse > vis[1] + 3 * sp)]
                    g = np.concatenate([g[keep], coarse])
                pts.append(g)
                # Graded samples into each arris so the round-over meets the face smoothly.
                grade = np.array([0.0025]) if m.fallback else np.array([0.0006, 0.0014, 0.0025])
                pts.append(u0 + grade)
                pts.append(u1 - grade)
                # Checks stay geometry even on the fallback: a 2K bake cannot
                # resolve a millimetre-wide crack, and a few rows cost little.
                for ck in m.log.checks:
                    if ck.face != f or not (ck.z0 <= z <= ck.z1):
                        continue
                    uc, wz, _ = _check_at(ck, z)
                    hw = max(wz / 2, 0.00012)
                    pts.append(uc + hw * np.array([-1.6, -1.0, -0.66, -0.33, 0.0, 0.33, 0.66, 1.0, 1.6]))
                    # Graded beyond the lips, so the face meets the check over
                    # the same short distance wherever the base grid falls.
                    beyond = hw * 1.6 + np.array([0.0003, 0.0008, 0.0016, 0.0028])
                    pts.append(uc - beyond)
                    pts.append(uc + beyond)
                for kf, ku, kz, au, az in feet:
                    if kf != f or abs(z - kz) > az * 1.3:
                        continue
                    pts.append(np.arange(ku - au * 1.3, ku + au * 1.3, sp / 4.0))
            u = np.unique(np.concatenate(pts))
            u = u[(u >= u0) & (u < u1 - 1e-7)]
            # Drop samples crowding the span ends (slivers), keeping the start.
            if u.size > 1:
                keep = np.ones(u.size, bool)
                keep[1:] = np.diff(u) > 0.00005
                u = u[keep]
            x, y = _face_xy(f, u, half_w, half_d)
            row_x.append(x)
            row_y.append(y)
            row_nx.append(np.full(u.size, FACE_N[f][0]))
            row_ny.append(np.full(u.size, FACE_N[f][1]))
            row_seg.append(np.full(u.size, 2 * f, np.int8))
            row_u.append(u)
            row_tau.append(2 * f + (u - u0) / max(1e-9, u1 - u0))
            if hidden:
                row_det.append(np.zeros(u.size, np.float32))
            elif vis is None:
                row_det.append(np.ones(u.size, np.float32))
            else:
                row_det.append(((u >= vis[0] - sp) & (u <= vis[1] + sp)).astype(np.float32))
            # Corner c = f joins face f to f+1.
            c = f
            cx, cy, cnx, cny = _corner_points(c, tc, R[c], P[c], half_w, half_d)
            row_x.append(cx)
            row_y.append(cy)
            row_nx.append(cnx)
            row_ny.append(cny)
            row_seg.append(np.full(tc.size, 2 * c + 1, np.int8))
            row_u.append(tc)
            row_tau.append(2 * c + 1 + tc / (math.pi / 2))
            nxt = (f + 1) % 4
            corner_hidden = m.finish[f] == "hidden" and m.finish[nxt] == "hidden"
            row_det.append(np.full(tc.size, 0.0 if corner_hidden else 1.0, np.float32))
        n = sum(a.size for a in row_x)
        starts.append(total)
        counts.append(n)
        total += n
        xs += row_x
        ys += row_y
        nxs += row_nx
        nys += row_ny
        segs += row_seg
        us += row_u
        taus += row_tau
        dets += row_det
        zz.append(np.full(n, z))
    cat = np.concatenate
    return Samples(x=cat(xs), y=cat(ys), z=cat(zz), nx=cat(nxs), ny=cat(nys), seg=cat(segs), u=cat(us),
                   tau=cat(taus), detail=cat(dets), row_start=np.array(starts), row_count=np.array(counts))


def _visible(m: Member, f, u):
    vis = m.visible[f]
    return vis is None or (vis[0] <= u <= vis[1])


def _check_at(ck: Check, z):
    """A check's centre across its face, opening and depth at height z."""
    span = max(1e-6, ck.z1 - ck.z0)
    t = np.clip((np.asarray(z) - ck.z0) / span, 0.0, 1.0)
    taper = np.sin(math.pi * t) ** 0.55
    wiggle = 0.0009 * np.sin(TAU * (np.asarray(z) - ck.z0) / 0.37 + ck.u0 * 300.0)
    uc = ck.u0 + ck.drift * (np.asarray(z) - ck.z0) + wiggle
    return uc, ck.width * taper, ck.depth * np.sqrt(taper)


# ---------------------------------------------------------------------------
# Surface fields
# ---------------------------------------------------------------------------

def _plane_strokes(m: Member, S: Samples, f, sel):
    """Kanna strokes: lanes ~6 cm wide, each a series of passes 0.5-1.6 m long,
    slightly hollow across the blade and offset a few hundredths of a mm."""
    rng = np.random.default_rng(m.seed * 31 + f)
    half = (m.depth if f % 2 == 0 else m.width) / 2
    lane_w = rng.uniform(0.050, 0.064)
    edges = np.arange(-half - rng.uniform(0, lane_w), half + lane_w, lane_w * rng.uniform(0.86, 0.95))
    n_l = edges.size - 1
    ns = int(math.ceil(m.length / 0.45)) + 2
    lens = rng.uniform(0.5, 1.6, (n_l, ns))
    breaks = np.concatenate([np.full((n_l, 1), -rng.uniform(0, 0.8)), np.cumsum(lens, 1) - rng.uniform(0, 0.8, (n_l, 1))], 1)
    heights = rng.normal(0, 1.2e-5, (n_l, ns))
    u = S.u[sel]
    z = S.z[sel]
    lane = np.clip(np.searchsorted(edges, u) - 1, 0, n_l - 1)
    k = np.clip((z[:, None] >= breaks[lane]).sum(1) - 1, 0, ns - 1)
    across = (u - edges[lane]) / (edges[lane + 1] - edges[lane]) * 2 - 1
    return heights[lane, k] - 1.6e-5 * (1 - across ** 2)


def _adze(m: Member, S: Samples, f, sel):
    """Chona-hatsuri: staggered lanes of overlapping scoops. Each scoop enters
    gradually and leaves with a short lip; the surface is the deepest cut."""
    seed = m.seed * 131 + f * 17
    rng = np.random.default_rng(seed)
    a = rng.uniform(0.034, 0.042)       # lane width across the face
    b = rng.uniform(0.050, 0.064)       # scoop pitch along the member
    u = S.u[sel]
    z = S.z[sel]
    j0 = np.floor(u / a).astype(np.int64)
    best = np.zeros(u.size)
    for dj in (-1, 0, 1):
        j = j0 + dj
        zoff = (j % 2) * b * 0.5 + (hash01(seed, j, 7) - 0.5) * b * 0.4
        k0 = np.floor((z - zoff) / b).astype(np.int64)
        for dk in (-1, 0, 1):
            k = k0 + dk
            uc = (j + 0.5 + (hash01(seed, j, k, 1) - 0.5) * 0.3) * a
            zc = zoff + (k + 0.5 + (hash01(seed, j, k, 2) - 0.5) * 0.35) * b
            dep = 0.0009 + 0.0014 * hash01(seed, j, k, 3)
            ru = a * (0.70 + 0.12 * hash01(seed, j, k, 4))
            dz = z - zc
            rz = np.where(dz > 0, 0.95 * b, 0.55 * b)
            q = (((u - uc) / ru) ** 2 + (dz / rz) ** 2)
            h = -dep * np.clip(1.0 - q, 0.0, None) ** 0.8
            best = np.minimum(best, h)
    return best + _adze_undulation(m, f, u, z) - 0.001


def _adze_undulation(m: Member, f, u, z):
    """The hewn face undulates by a millimetre or two over half a metre."""
    und = Waves(np.random.default_rng(m.seed * 131 + f * 17 + 5), 8, (0.25, 1.8), 0.0007)
    return und(u, z)


def _dents(m: Member, S: Samples, sel_detail):
    """Bokken strikes and handling dings: shallow elongated dishes."""
    rng = np.random.default_rng(m.seed * 977 + 3)
    disp = np.zeros(S.x.size)
    idx = np.nonzero(sel_detail)[0]
    if idx.size == 0 or m.dents <= 0:
        return disp
    px, py, pz = S.x[idx], S.y[idx], S.z[idx]
    for _ in range(m.dents):
        k = idx[rng.integers(0, idx.size)]
        cz = float(np.clip(rng.normal((m.dent_zone[0] + m.dent_zone[1]) / 2, (m.dent_zone[1] - m.dent_zone[0]) / 3),
                           0.02, m.length - 0.02))
        # Re-pick a sample near the chosen height on a detailed range.
        near = idx[np.abs(pz - cz) < 0.05]
        if near.size:
            k = near[rng.integers(0, near.size)]
        cx, cy, cz = S.x[k], S.y[k], S.z[k]
        a_z = rng.uniform(0.003, 0.016)
        a_h = a_z * rng.uniform(0.25, 0.8)
        dep = rng.uniform(0.00012, 0.0007)
        box = (np.abs(S.z - cz) < a_z * 3) & (np.abs(S.x - cx) < a_h * 3 + 0.004) & (np.abs(S.y - cy) < a_h * 3 + 0.004)
        if not box.any():
            continue
        dh = np.hypot(S.x[box] - cx, S.y[box] - cy)
        dz = S.z[box] - cz
        disp[box] -= dep * np.exp(-((dh / a_h) ** 2 + (dz / a_z) ** 2))
    return disp


def _knots(m: Member, P: np.ndarray):
    """Per knot: inside mask, distance to its axis, its radius there, and dead flag."""
    n = P.shape[0]
    mask = np.zeros(n)
    kd = np.full(n, np.inf)
    kr = np.ones(n)
    swirl = np.zeros(n)
    dead = np.zeros(n)
    bulge = np.zeros(n)
    for k in m.log.knots:
        px, py = m.log.pith_at(k.z)
        a0 = np.array([px, py, k.z])
        d = np.array([math.cos(k.azimuth) * math.cos(k.rise), math.sin(k.azimuth) * math.cos(k.rise), math.sin(k.rise)])
        v = P - a0
        t = v @ d
        perp = v - t[:, None] * d
        dist = np.linalg.norm(perp, axis=1)
        r = k.r0 + k.flare * np.clip(t, 0, None)
        valid = t > 0
        inside = valid & (dist < r)
        edge = 1.0 - smoothstep(r * 0.82, r * 1.0, dist)
        mask = np.where(valid, np.maximum(mask, edge), mask)
        closer = valid & (dist / r < kd / kr)
        kd = np.where(closer, dist, kd)
        kr = np.where(closer, r, kr)
        dead = np.where(closer & inside, 1.0 if k.dead else 0.0, dead)
        swirl += np.where(valid, m.log.swirl * r * np.exp(-((np.maximum(dist - r, 0)) / (1.6 * r)) ** 2), 0.0)
        bulge += np.where(inside, k.bulge * (1 - (dist / r) ** 2), 0.0)
        if k.dead:
            # A dead knot shrinks from its socket: a fine groove round its edge.
            ring = valid & (np.abs(dist - r) < 0.0005)
            bulge -= np.where(ring, 0.00035 * (1 - np.abs(dist - r) / 0.0005), 0.0)
    return mask, kd, kr, swirl, dead, bulge


def build_member(m: Member):
    """Sample, displace and attribute a member. Returns a dict of numpy arrays:
    verts (N,3), tris (T,3), tri_wrap (T,3) bool, uv0/uv2/uv3 per vertex (N,2),
    s (arc length, N), colors (N,4), plus counts."""
    S = sample_member(m)
    N = S.x.size
    disp = np.zeros(N)
    face_detail = (S.seg % 2 == 0) & (S.detail > 0)
    adze_depth = np.zeros(N)
    for f in range(4):
        sel = (S.seg == 2 * f) & (S.detail > 0)
        if not sel.any():
            continue
        if m.fallback:
            if m.finish[f] == "adze":
                # The hewn face's mean surface and its slow undulation only.
                disp[sel] += _adze_undulation(m, f, S.u[sel], S.z[sel]) - 0.001
            continue
        if m.finish[f] == "planed":
            disp[sel] += _plane_strokes(m, S, f, sel)
        elif m.finish[f] == "adze":
            h = _adze(m, S, f, sel)
            disp[sel] += h
            adze_depth[sel] = -h
    # Checks.
    check_depth = np.zeros(N)
    for ck in m.log.checks:
        sel = (S.seg == 2 * ck.face) & (S.z >= ck.z0) & (S.z <= ck.z1) & (S.detail > 0)
        if not sel.any():
            continue
        uc, wz, dz = _check_at(ck, S.z[sel])
        hw = np.maximum(wz / 2, 1e-6)
        rel = np.abs(S.u[sel] - uc) / hw
        cut = dz * np.clip(1.0 - rel, 0.0, None) ** 1.15
        # The lips of a check are eased slightly.
        lip = np.where((rel >= 1.0) & (rel < 1.6), 0.00004 * (1 - (rel - 1.0) / 0.6), 0.0)
        disp[sel] -= cut + lip
        check_depth[sel] = np.maximum(check_depth[sel], cut)
    if not m.fallback:
        disp += _dents(m, S, face_detail)
    # Bow: the member is not quite straight.
    rng = np.random.default_rng(m.seed + 41)
    ang = rng.uniform(0, TAU)
    bow = m.bow * np.sin(math.pi * S.z / m.length)
    P = np.stack([S.x, S.y, S.z], 1)
    mask, kd, kr, swirl, dead, kb = _knots(m, P)
    if not m.fallback:
        disp += np.where(S.detail > 0, kb, 0.0)
    P[:, 0] += S.nx * disp + bow * math.cos(ang)
    P[:, 1] += S.ny * disp + bow * math.sin(ang)
    # Log coordinates: offset from the pith, warped by wobble and knot swirl.
    px, py = m.log.pith_at(P[:, 2])
    qx = P[:, 0] - px
    qy = P[:, 1] - py
    r = np.hypot(qx, qy) + 1e-9
    theta = np.arctan2(qy, qx)
    r_warp = r + m.log.wobble(theta * 0.08, P[:, 2]) * np.clip(r / 0.03, 0, 1) + swirl
    scale = r_warp / r
    q2x, q2y = qx * scale, qy * scale
    # Inside a knot the figure is the branch's own rings, centred on its axis.
    knot_rings = m.log.ring_width / 0.00055
    # A coarse fallback can't resolve a knot's frame: its knots come from the bake.
    inside = (kd < kr) & (not m.fallback)
    q2x = np.where(inside, kd * knot_rings * np.cos(theta), q2x)
    q2y = np.where(inside, kd * knot_rings * np.sin(theta), q2y)
    tris, wrap = ladder(S)
    caps = None
    if m.end_caps:
        caps = end_caps(S, N)
    # Arc length per row (for UV0 / UV1), wrap length per row.
    s = np.zeros(N)
    row_len = np.zeros(S.row_start.size)
    for i, (st, ct) in enumerate(zip(S.row_start, S.row_count)):
        seg = np.hypot(np.diff(P[st:st + ct, 0], append=P[st, 0]), np.diff(P[st:st + ct, 1], append=P[st, 1]))
        s[st:st + ct] = np.concatenate([[0.0], np.cumsum(seg[:-1])])
        row_len[i] = seg.sum()
    row_of = np.repeat(np.arange(S.row_start.size), S.row_count)
    # Masks.
    cavity = np.clip(check_depth / 0.004, 0, 1) * 0.9 + np.clip(adze_depth / 0.0025, 0, 1) * 0.35
    cavity = np.clip(cavity + mask * 0.15, 0, 1)
    hz, hs = m.handling
    handled = np.exp(-((P[:, 2] - hz) / hs) ** 2)
    corner = (S.seg % 2 == 1).astype(np.float64)
    near_corner = np.zeros(N)
    faces = S.seg % 2 == 0
    # Distance into a face from its nearest arris, for wear falloff.
    half = np.where((S.seg // 2) % 2 == 0, m.depth / 2, m.width / 2)
    near_corner[faces] = np.clip(1.0 - (half[faces] - np.abs(S.u[faces])) / 0.012, 0, 1)
    wear_noise = Waves(np.random.default_rng(m.seed + 77), 10, (0.02, 0.6), 0.5)
    wear = np.clip((np.maximum(corner, near_corner) * 0.75 + 0.25) * handled * (0.7 + wear_noise(S.tau * 0.1, P[:, 2]))
                   * (S.detail > 0), 0, 1)
    soot_noise = Waves(np.random.default_rng(m.seed + 78), 10, (0.05, 1.5), 0.25)
    soot = np.clip(smoothstep(m.soot_from, m.length, P[:, 2]) * 0.7 + cavity * 0.4 + soot_noise(S.tau * 0.1, P[:, 2]), 0, 1)
    knot_a = np.clip(mask * (0.55 + 0.45 * dead), 0, 1)
    colors = np.stack([cavity, wear, soot, knot_a], 1).astype(np.float32)
    seed01 = (m.log.seed % 997) / 997.0
    return {
        "verts": P, "tris": tris, "wrap": wrap, "caps": caps,
        "s": s, "row_len": row_len, "row_of": row_of, "z": P[:, 2],
        "uv2": np.stack([q2x, q2y], 1), "uv3": np.stack([P[:, 2] - 0.0, np.full(N, seed01)], 1),
        "colors": colors, "samples": S,
    }


# ---------------------------------------------------------------------------
# Triangulation
# ---------------------------------------------------------------------------

def ladder(S: Samples):
    """Stitch consecutive closed rows. Returns (tris (T,3), wrap (T,3) bool):
    wrap marks corners that refer to a row's first sample after going round."""
    out_t = []
    out_w = []
    for i in range(S.row_start.size - 1):
        a0, na = S.row_start[i], S.row_count[i]
        b0, nb = S.row_start[i + 1], S.row_count[i + 1]
        ta = S.tau[a0:a0 + na]
        tb = S.tau[b0:b0 + nb]
        # Extended sequences: elements 1..n then the first again (+8 round).
        ka = np.concatenate([ta[1:], [ta[0] + 8.0]])
        kb = np.concatenate([tb[1:], [tb[0] + 8.0]])
        keys = np.concatenate([ka, kb])
        is_a = np.concatenate([np.ones(na, bool), np.zeros(nb, bool)])
        order = np.argsort(keys, kind="stable")
        isa = is_a[order]
        ca = np.cumsum(isa)          # A elements consumed including this step
        cb = np.cumsum(~isa)
        cur_a = ca - isa             # index into extended A before this step (0 = first sample)
        cur_b = cb - (~isa)
        new_a = ca
        new_b = cb
        ia = lambda k: a0 + (k % na)
        ib = lambda k: b0 + (k % nb)
        wa = lambda k: k >= na
        wb = lambda k: k >= nb
        t = np.where(isa[:, None],
                     np.stack([ia(cur_a), ia(new_a), ib(cur_b)], 1),
                     np.stack([ia(cur_a), ib(new_b), ib(cur_b)], 1))
        w = np.where(isa[:, None],
                     np.stack([wa(cur_a), wa(new_a), wb(cur_b)], 1),
                     np.stack([wa(cur_a), wb(new_b), wb(cur_b)], 1))
        out_t.append(t)
        out_w.append(w)
    return np.concatenate(out_t).astype(np.int64), np.concatenate(out_w)


def end_caps(S: Samples, n_verts):
    """Fan caps for both ends around a new centre vertex each (indices n, n+1)."""
    caps = []
    for end, centre in ((0, n_verts), (S.row_start.size - 1, n_verts + 1)):
        st, ct = S.row_start[end], S.row_count[end]
        ring = np.arange(st, st + ct)
        nxt = np.roll(ring, -1)
        c = np.full(ct, centre)
        if end == 0:
            caps.append(np.stack([c, nxt, ring], 1))
        else:
            caps.append(np.stack([c, ring, nxt], 1))
    return caps


# ---------------------------------------------------------------------------
# Shared material textures (plain numpy + zlib PNG; no Blender needed)
# ---------------------------------------------------------------------------

def write_png(path, arr):
    """Write uint8 or uint16 grey/RGB/RGBA ``arr`` (H, W[, C]) as a PNG."""
    import struct
    import zlib
    from pathlib import Path

    a = np.asarray(arr)
    if a.ndim == 2:
        a = a[..., None]
    h, w, c = a.shape
    depth = 16 if a.dtype == np.uint16 else 8
    ctype = {1: 0, 3: 2, 4: 6}[c]
    if depth == 16:
        raw = a.astype(">u2").view(np.uint8).reshape(h, w * c * 2)
    else:
        raw = a.astype(np.uint8).reshape(h, w * c)
    data = b"".join(b"\x00" + raw[y].tobytes() for y in range(h))

    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, depth, ctype, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(data, 9)) + chunk(b"IEND", b"")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(png)
    return Path(path)


def _filtered_noise(rng, shape, sigma_u, sigma_v):
    """Periodic Gaussian-filtered white noise (cycles per pixel), mean 0.5, std ~0.17."""
    h, w = shape
    white = rng.standard_normal(shape)
    fu = np.fft.fftfreq(w)[None, :]
    fv = np.fft.fftfreq(h)[:, None]
    filt = np.exp(-(fu / sigma_u) ** 2 - (fv / sigma_v) ** 2)
    n = np.real(np.fft.ifft2(np.fft.fft2(white) * filt))
    n = (n - n.mean()) / (n.std() + 1e-12)
    return np.clip(0.5 + 0.17 * n, 0.0, 1.0)


def shared_textures(out_dir, seed=90210):
    """The timber material's shared lookups. Returns {kind: (path, importer kind)}.

    * RingNoise (1024 x 64, 16-bit grey): each row a periodic 1D fbm; a log's
      seed picks the row, the radius / (6 ring widths) runs along it.
    * RingRandom (256 x 256, 8-bit grey): per-year strength, sampled nearest.
    * Fibre (1024 x 1024, 8-bit RGB) on UV0 / 0.25 m: R fine fibres (long along
      V, the grain), G streaks, B broad drift (sampled at UV0 x 0.11).
    """
    from pathlib import Path

    out = Path(out_dir)
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(64):
        white = rng.standard_normal(1024)
        f = np.fft.rfftfreq(1024)
        spec = np.fft.rfft(white) * np.where(f > 0, (f * 1024) ** -1.1, 0.0) * np.exp(-(f / 0.06) ** 2)
        row = np.fft.irfft(spec, 1024)
        row = (row - row.min()) / (row.max() - row.min() + 1e-12)
        rows.append(row)
    ring_noise = (np.array(rows) * 65535).astype(np.uint16)
    ring_random = (rng.random((256, 256)) * 255).astype(np.uint8)
    fib = _filtered_noise(rng, (1024, 1024), 0.22, 0.012)
    streak = _filtered_noise(rng, (1024, 1024), 0.035, 0.004)
    drift = _filtered_noise(rng, (1024, 1024), 0.004, 0.004)
    fibre = (np.stack([fib, streak, drift], -1) * 255).astype(np.uint8)
    return {
        "RingNoise": (write_png(out / "T_TimberRingNoise.png", ring_noise), "Data"),
        "RingRandom": (write_png(out / "T_TimberRingRandom.png", ring_random), "Random"),
        "Fibre": (write_png(out / "T_TimberFibre.png", fibre), "Masks"),
    }


# ---------------------------------------------------------------------------
# Blender mesh
# ---------------------------------------------------------------------------

def to_blender(name, B, m: Member, atlas_strips=3):
    """Create a Blender mesh object: UV0 metric, UV1 unique atlas, UV2/UV3 log
    frame, colour attribute Masks (linear floats)."""
    import bpy

    P = B["verts"]
    N = P.shape[0]
    tris = B["tris"]
    wrap = B["wrap"]
    caps = B["caps"]
    verts = P
    cap_tris = []
    if caps is not None:
        S = B["samples"]
        c0 = P[S.row_start[0]:S.row_start[0] + S.row_count[0]].mean(0)
        last = S.row_start.size - 1
        c1 = P[S.row_start[last]:S.row_start[last] + S.row_count[last]].mean(0)
        verts = np.concatenate([P, [c0, c1]])
        cap_tris = caps
    all_tris = np.concatenate([tris] + list(cap_tris)) if cap_tris else tris
    nt = all_tris.shape[0]
    off = np.asarray(m.offset)
    me = bpy.data.meshes.new(name)
    me.vertices.add(verts.shape[0])
    me.vertices.foreach_set("co", (verts + off).astype(np.float32).ravel())
    me.loops.add(nt * 3)
    me.loops.foreach_set("vertex_index", all_tris.astype(np.int32).ravel())
    me.polygons.add(nt)
    me.polygons.foreach_set("loop_start", np.arange(0, nt * 3, 3, dtype=np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set("use_smooth", np.ones(nt, bool))
    # Per-loop UVs.
    vi = all_tris.ravel()
    n_side = tris.shape[0] * 3
    side_wrap = wrap.ravel()
    row_len = B["row_len"]
    row_of = np.concatenate([B["row_of"], [0, B["row_of"][-1]]]) if cap_tris else B["row_of"]
    s_all = np.concatenate([B["s"], [0.0, 0.0]]) if cap_tris else B["s"]
    z_all = verts[:, 2]
    s_loop = s_all[vi].copy()
    s_loop[:n_side] += np.where(side_wrap, row_len[row_of[vi[:n_side]]], 0.0)
    uv0 = np.stack([s_loop, z_all[vi]], 1)
    # UV0 caps: planar in X/Y.
    if cap_tris:
        uv0[n_side:, 0] = verts[vi[n_side:], 0]
        uv0[n_side:, 1] = verts[vi[n_side:], 1]
    # UV1: unfold the side into ``atlas_strips`` strips side by side; caps below.
    P_max = float(row_len.max())
    L = m.length
    K = atlas_strips
    side_w = K * P_max
    cap_h = max(m.width, m.depth) * 1.05
    span = max(side_w, L / K + cap_h)
    tri_row = np.minimum(row_of[vi[:n_side]].reshape(-1, 3).min(1), row_of.max())
    tri_z = z_all[vi[:n_side]].reshape(-1, 3).min(1)
    strip = np.clip((tri_z / (L / K)).astype(int), 0, K - 1)
    strip_l = np.repeat(strip, 3)
    zl = z_all[vi[:n_side]] - strip_l * (L / K)
    pad = 0.01 * span
    u1 = (strip_l * P_max + s_loop[:n_side] * (P_max - pad) / P_max + pad * 0.5) / span
    v1 = (cap_h + zl) / span
    uv1 = np.zeros((nt * 3, 2))
    uv1[:n_side, 0] = u1
    uv1[:n_side, 1] = v1
    if cap_tris:
        cv = vi[n_side:]
        half_cap = (nt * 3 - n_side) // 2
        which = np.concatenate([np.zeros(half_cap), np.ones(nt * 3 - n_side - half_cap)])
        uv1[n_side:, 0] = (which * cap_h + verts[cv, 0] + m.width / 2 + 0.01) / span
        uv1[n_side:, 1] = (verts[cv, 1] + m.depth / 2 + 0.01) / span
    uv2 = np.concatenate([B["uv2"], [[0, 0], [0, 0]]])[vi] if cap_tris else B["uv2"][vi]
    uv3 = np.concatenate([B["uv3"], [B["uv3"][0], B["uv3"][-1]]])[vi] if cap_tris else B["uv3"][vi]
    if cap_tris:
        # End grain: compute the log frame for the cap centres as well.
        for k, cvx in enumerate((N, N + 1)):
            px, py = m.log.pith_at(verts[cvx, 2])
            sel = vi == cvx
            uv2[sel] = [verts[cvx, 0] - px, verts[cvx, 1] - py]
            uv3[sel] = [verts[cvx, 2], B["uv3"][0, 1]]
    for layer, arr in (("UV0", uv0), ("UV1", uv1), ("UVLogQ", uv2), ("UVLogZ", uv3)):
        uv = me.uv_layers.new(name=layer)
        uv.data.foreach_set("uv", arr.astype(np.float32).ravel())
    col = me.color_attributes.new("Masks", "FLOAT_COLOR", "POINT")
    cols = B["colors"]
    if cap_tris:
        cols = np.concatenate([cols, [cols[0] * 0 + (0.0, 0.0, 0.6, 0.0)] * 2]).astype(np.float32)
    col.data.foreach_set("color", cols.ravel())
    me.validate(clean_customdata=False)
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj
