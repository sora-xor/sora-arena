"""Prototypes for the paws' surface: a continuous UV mapping, and pads cut along a smooth contour (CPU only).

Root's review of s132 and s134 (2026-10-26) rejects the paws' jagged light boundaries.
diagnose_nyaakoto_paw_boundaries.py traced them to two per-face choices in nyaakoto_tp_paws.mesh_paw:
- corner_uvs switches each face between two unrelated projections;
- pad_faces makes whole faces pads.
On the 3 mm grid both draw triangle staircases. This module offers replacements, measured by
measure_paw_surface_prototypes.py against the baseline. It changes nothing in nyaakoto_tp_paws, whose SHA-256 pins the
built assets.

**The surface.** It is a torus around the grip channel: V - F/2 = 0, as a fist closed round the tsuka is. Any
continuous mapping of a torus has two seam loops. Here:
- **u runs round the channel** (the major loop). Its seam is where the thumb's tip meets the toes' tips
  (nyaakoto_tp_paws.UV_SEAM_DEG), as the baseline's wrap already is.
- **v runs round the paw's cross-section** (the minor loop: the inner wall, over a side, across the back, over the
  other side). Its seam is on the inner wall, which faces the tsuka.
The cross-section is measured from the paw itself. On a grid of turn and minor angle round each turn's cross-section
centre, the outer envelope's radius gives the loop's arc length.

**The mappings** (each per corner; a face that spans a seam is unwrapped):
- **round:** the baseline's round mapping on every face, with no planar switch. It is the reference.
- **torus_arc:** u is the turn times the envelope's radius at the vertex's minor angle; v is the arc length round the
  cross-section. It is isometric along each loop where the envelope is the surface, and it shears on the sides in
  proportion to the turn from the paw's back.
- **torus_tiles:** u is one texture tile round the channel; v is a whole number of tiles round each cross-section, by
  arc-length fraction. The fur maps tile exactly (create_nyaakoto_pbr_textures.exact_wrap), so both seams join
  texture to itself. The cost is scale: u runs at the envelope's radius over 6.63 cm (one tile, 41.7 cm, per turn), and
  v by each loop's length over its whole number of tiles.

**The pads.** pad_field gives each point a margin in metres, positive inside a pad. It is built from pad_faces' own
criteria with their own constants, each as a margin:
- within PAD_REACH of the channel;
- past PAD_TOE_TURN or PAD_THUMB_TURN round it, as arc length;
- PAD_CLEFT nearer its own toe than any other mass, half the distance difference;
- the palm pad's digit weight under one half.
Each pad is the smooth minimum of its margins, and the pads are joined by a smooth maximum. The smoothing radius is
PAD_ROUND, so a pad's corners are rounded.

cut_by_field splits each face the zero contour crosses. A crossing is put on its edge by linear interpolation of the
field at the edge's ends, and an edge shared by two faces gets one vertex, so the surface stays a closed manifold. A
crossing within SNAP of an edge's end moves to that vertex, so no sliver is made.

New vertices take their attributes by the rules the baseline uses:
- **position:** on the edge;
- **coat:** the coat rule at the new position;
- **UV:** the mapping at it;
- **empty fist:** empty_points at it;
- **weight:** hand, 1.0, as every paw vertex is (LOD0's FBX).
"""
from __future__ import annotations

import math

import numpy as np

import nyaakoto_tp_paws as TPP

PAD_ROUND = 0.0008            # m: the smooth minimum's and maximum's reach, rounding a pad's corners
SNAP = 0.15                   # a crossing nearer an edge's end than this share of the edge moves to that end
TURN_BINS, PHI_BINS = 72, 96  # the cross-section grid: 5 deg of turn by 3.75 deg of minor angle
ENVELOPE_PCT = 90.0           # the envelope radius in a cell: this percentile of its points' radii
INNER_WALL = 0.003            # m: the paw's surface this near the channel is its inner wall
COT_FLOOR = 0.05              # ARAP's cotangent weights, clamped from below (negative ones fold the solve)
U_TILE_RADIUS = 1.0 / (2.0 * math.pi * TPP.UV_PER_M)   # m: the radius at which one tile round the channel is isometric


# --- The channel's coordinates ------------------------------------------------------------------------------------------
def coords(points, fr):
    """Per point: s (along the channel), tau (the turn, from the back of the paw: 0 opposite the major seam, +-pi at it),
    rho (distance from the channel's axis), all in metres and radians."""
    d = np.atleast_2d(points) - fr["c"]
    s = d @ TPP.Y
    zc, wc = d @ fr["z"], d @ fr["w"]
    t = np.arctan2(fr["a"] * wc, fr["b"] * zc)                 # nyaakoto_tp_paws.turn_of's scaled polar angle
    seam = math.radians(TPP.UV_SEAM_DEG)
    tau = np.angle(np.exp(1j * (t - seam - math.pi)))           # +-pi at the seam, 0 opposite it
    return s, tau, np.hypot(zc, wc)


class CrossSection:
    """The paw's cross-section round each turn: its centre, and the arc length of its outer envelope by minor angle."""

    def __init__(self, verts, fr):
        s, tau, rho = coords(verts, fr)
        self.fr = fr
        tb = np.clip(((tau + math.pi) / (2.0 * math.pi) * TURN_BINS).astype(int), 0, TURN_BINS - 1)
        centre = np.zeros((TURN_BINS, 2))
        for k in range(TURN_BINS):
            m = tb == k
            centre[k] = (np.median(rho[m]), np.median(s[m])) if m.any() else (np.nan, np.nan)
        centre = _fill_periodic(centre)
        self.centre = _smooth_periodic(centre, 2)
        phi = self.phi(s, tau, rho)
        r = np.hypot(rho - self._centre_at(tau)[:, 0], s - self._centre_at(tau)[:, 1])
        pb = np.clip(((phi + math.pi) / (2.0 * math.pi) * PHI_BINS).astype(int), 0, PHI_BINS - 1)
        env = np.full((TURN_BINS, PHI_BINS), np.nan)
        for k in range(TURN_BINS):
            for j in range(PHI_BINS):
                m = (tb == k) & (pb == j)
                if m.sum() >= 2:
                    env[k, j] = np.percentile(r[m], ENVELOPE_PCT)
        env = _fill_grid_periodic(env)
        self.env = _smooth_grid_periodic(env, 1)
        # Arc length along each turn's loop: integral of sqrt(r^2 + (dr/dphi)^2) dphi, from phi = -pi (the inner wall).
        dphi = 2.0 * math.pi / PHI_BINS
        dr = (np.roll(self.env, -1, 1) - np.roll(self.env, 1, 1)) / (2.0 * dphi)
        ds = np.sqrt(self.env ** 2 + dr ** 2) * dphi
        self.arc = np.concatenate([np.zeros((TURN_BINS, 1)), np.cumsum(ds, 1)], 1)    # (TURN_BINS, PHI_BINS + 1)
        self.length = self.arc[:, -1]
        # The inner wall's midline along the channel at each turn: the middle of the wall's extent in s (the paw's
        # surface within INNER_WALL of the channel). The wall exists at every turn, but sits off-centre where only the
        # thumb is (s 17-35 mm on r3's right paw), so the cross-section's own centre does not stay on it.
        wall = TPP.channel_sdf(verts, fr) < INNER_WALL
        mid = np.full((TURN_BINS, 1), np.nan)
        for k in range(TURN_BINS):
            m = wall & (tb == k)
            if m.any():
                mid[k] = 0.5 * (s[m].min() + s[m].max())
        self.inner_mid = _smooth_periodic(_fill_periodic(mid), 2)[:, 0]

    def inner_mid_at(self, tau):
        x = (tau + math.pi) / (2.0 * math.pi) * TURN_BINS - 0.5
        k0 = np.floor(x).astype(int)
        f = x - k0
        return self.inner_mid[k0 % TURN_BINS] * (1 - f) + self.inner_mid[(k0 + 1) % TURN_BINS] * f

    def _centre_at(self, tau):
        x = (tau + math.pi) / (2.0 * math.pi) * TURN_BINS - 0.5
        k0 = np.floor(x).astype(int)
        f = x - k0
        a, b = self.centre[k0 % TURN_BINS], self.centre[(k0 + 1) % TURN_BINS]
        return a * (1.0 - f)[:, None] + b * f[:, None]

    def phi(self, s, tau, rho):
        """The minor angle round the turn's cross-section centre: 0 toward the back (away from the channel), +-pi at
        the inner wall."""
        c = self._centre_at(tau)
        return np.arctan2(s - c[:, 1], rho - c[:, 0])

    def _grid(self, table, tau, phi, periodic_phi=True):
        x = (tau + math.pi) / (2.0 * math.pi) * TURN_BINS - 0.5
        y = (phi + math.pi) / (2.0 * math.pi) * (table.shape[1] - (0 if periodic_phi else 1))
        k0, j0 = np.floor(x).astype(int), np.floor(y).astype(int)
        fx, fy = x - k0, y - j0
        cols = table.shape[1]
        jj0 = j0 % cols if periodic_phi else np.clip(j0, 0, cols - 1)
        jj1 = (j0 + 1) % cols if periodic_phi else np.clip(j0 + 1, 0, cols - 1)
        t00, t01 = table[k0 % TURN_BINS, jj0], table[k0 % TURN_BINS, jj1]
        t10, t11 = table[(k0 + 1) % TURN_BINS, jj0], table[(k0 + 1) % TURN_BINS, jj1]
        return (t00 * (1 - fx) * (1 - fy) + t01 * (1 - fx) * fy + t10 * fx * (1 - fy) + t11 * fx * fy)

    def envelope(self, tau, phi):
        return self._grid(self.env, tau, phi) + 0.0

    def arc_at(self, tau, phi):
        """Arc length from the inner wall (phi = -pi) to phi, at this turn (m)."""
        return self._grid(self.arc, tau, phi, periodic_phi=False)

    def length_at(self, tau):
        x = (tau + math.pi) / (2.0 * math.pi) * TURN_BINS - 0.5
        k0 = np.floor(x).astype(int)
        f = x - k0
        return self.length[k0 % TURN_BINS] * (1 - f) + self.length[(k0 + 1) % TURN_BINS] * f


def _fill_periodic(a):
    """Fill nan rows of a (n, d) periodic table by linear interpolation round the period."""
    out = a.copy()
    n = len(a)
    ok = ~np.isnan(a[:, 0])
    idx = np.flatnonzero(ok)
    for k in np.flatnonzero(~ok):
        prev = idx[idx < k][-1] if (idx < k).any() else idx[-1] - n
        nxt = idx[idx > k][0] if (idx > k).any() else idx[0] + n
        f = (k - prev) / (nxt - prev)
        out[k] = a[prev % n] * (1 - f) + a[nxt % n] * f
    return out


def _smooth_periodic(a, passes):
    for _ in range(passes):
        a = 0.25 * np.roll(a, 1, 0) + 0.5 * a + 0.25 * np.roll(a, -1, 0)
    return a


def _fill_grid_periodic(g):
    """Fill nan cells of a doubly periodic grid by repeated averaging of filled neighbours."""
    g = g.copy()
    for _ in range(max(g.shape)):
        bad = np.isnan(g)
        if not bad.any():
            break
        nb = np.stack([np.roll(g, 1, 0), np.roll(g, -1, 0), np.roll(g, 1, 1), np.roll(g, -1, 1)])
        cnt = (~np.isnan(nb)).sum(0)
        avg = np.where(cnt > 0, np.nansum(nb, 0) / np.maximum(cnt, 1), np.nan)
        g[bad] = avg[bad]
    return g


def _smooth_grid_periodic(g, passes):
    for _ in range(passes):
        g = (4 * g + np.roll(g, 1, 0) + np.roll(g, -1, 0) + np.roll(g, 1, 1) + np.roll(g, -1, 1)) / 8.0
    return g


# --- The mappings -------------------------------------------------------------------------------------------------------
def _unwrap_faces(values, tris, period):
    """Per corner, a periodic per-vertex coordinate unwrapped within each face (a face spanning the seam keeps its
    corners on one side)."""
    c = values[tris]
    span = c.max(1) - c.min(1)
    wrap = span > 0.5 * period
    return np.where(wrap[:, None] & (c < c.mean(1, keepdims=True)), c + period, c)


def uv_round(verts, tris, fr):
    """The baseline's round mapping on every face (corner_uvs without its planar switch)."""
    s, t, e = TPP.channel_coords(verts, fr)
    seam = math.radians(TPP.UV_SEAM_DEG)
    turn = np.mod(t - seam, 2.0 * math.pi)
    radius = e + 0.5 * (fr["a"] + fr["b"])
    ct = turn[tris]
    wrap = (ct.max(1) - ct.min(1)) > math.pi
    ct = np.where(wrap[:, None] & (ct < math.pi), ct + 2.0 * math.pi, ct)
    return np.stack([ct * radius[tris], s[tris]], -1) * TPP.UV_PER_M


def uv_torus(verts, tris, fr, section, tiles=False):
    """The toroidal mappings (module notes): torus_arc (tiles False) or torus_tiles."""
    s, tau, rho = coords(verts, fr)
    phi = section.phi(s, tau, rho)
    if tiles:
        u = (tau + math.pi) / (2.0 * math.pi)                                   # one tile round the channel
        n_v = max(1, int(round(float(np.mean(section.length)) * TPP.UV_PER_M)))
        v = section.arc_at(tau, phi) / section.length_at(tau) * n_v            # whole tiles round each loop
        cu = _unwrap_faces(u, tris, 1.0)
        cv = _unwrap_faces(v, tris, float(n_v))
        return np.stack([cu, cv], -1), {"u_period_uv": 1.0, "v_period_uv": float(n_v)}
    # torus_arc: u = turn x envelope radius, v = arc length (both in UV units)
    c = section._centre_at(tau)
    r_env = section.envelope(tau, phi)
    rho_env = c[:, 0] + r_env * np.cos(phi)                    # the envelope point's distance from the channel's axis
    u = (tau + math.pi) * np.maximum(rho_env, 1e-4) * TPP.UV_PER_M
    v = section.arc_at(tau, phi) * TPP.UV_PER_M
    # Per face: a face spanning the u seam (tau near +-pi) or the v seam (phi near +-pi) keeps its corners together.
    ct = (tau + math.pi)[tris]
    wrap_u = (ct.max(1) - ct.min(1)) > math.pi
    cu = np.where(wrap_u[:, None] & (ct < math.pi), (ct + 2 * math.pi) * np.maximum(rho_env, 1e-4)[tris] * TPP.UV_PER_M, u[tris])
    cp = phi[tris]
    wrap_v = (cp.max(1) - cp.min(1)) > math.pi
    lengths = (section.length_at(tau) * TPP.UV_PER_M)[tris]
    cv = np.where(wrap_v[:, None] & (cp < 0), v[tris] + lengths, v[tris])
    return np.stack([cu, cv], -1), {"u_period_uv": None, "v_period_uv": None}


# --- The pads -----------------------------------------------------------------------------------------------------------
def smin(a, b, k=PAD_ROUND):
    return -k * np.logaddexp(-a / k, -b / k)


def smax(a, b, k=PAD_ROUND):
    return k * np.logaddexp(a / k, b / k)


def pad_field(points, skel):
    """The pads' margin (m), positive inside a pad (module notes)."""
    fr = skel["frame"]
    p = np.atleast_2d(points)
    near = TPP.PAD_REACH - TPP.channel_sdf(p, fr)
    d = p - fr["c"]
    rho = np.hypot(d @ fr["z"], d @ fr["w"])
    turn = np.radians(TPP.turn_of(p, fr))
    chains = np.stack([TPP._chain(p, c) for c in skel["digits"]] + [TPP._chain(p, skel["thumb"])], 1)
    pl = skel["palm"]
    palm = TPP.FP.ellipsoid(p, pl["c"], pl["axes"], pl["r"])
    order = np.argsort(chains, 1)
    own = np.take_along_axis(chains, order[:, :1], 1)[:, 0]
    second = np.minimum(np.take_along_axis(chains, order[:, 1:2], 1)[:, 0], palm)
    cleft = 0.5 * ((second - own) - TPP.PAD_CLEFT)
    toe = order[:, 0] < 4
    turn_need = np.where(toe, math.radians(TPP.PAD_TOE_TURN), math.radians(TPP.PAD_THUMB_TURN))
    past = (turn - turn_need) * rho
    digit_pad = smin(smin(near, past), cleft)
    palm_pad = smin(near, (0.5 - TPP.digit_weight(p, skel)) * 0.008)
    return smax(digit_pad, palm_pad)


# --- The cut ------------------------------------------------------------------------------------------------------------
def _min_angle(p):
    """The smallest angle (deg) of the triangle with corners p (3, 3)."""
    out = 180.0
    for k in range(3):
        u, v = p[(k + 1) % 3] - p[k], p[(k + 2) % 3] - p[k]
        c = float(np.dot(u, v) / max(np.linalg.norm(u) * np.linalg.norm(v), 1e-15))
        out = min(out, math.degrees(math.acos(max(-1.0, min(1.0, c)))))
    return out


def cut_by_field(verts, tris, f, snap=SNAP):
    """Split each face the zero contour of the per-vertex field f crosses (module notes).

    Returns (verts, tris, inside per face, parents (n_new, 2) vertex pairs with their parameter t, and the field with its
    snapped vertices at 0)."""
    f = np.asarray(f, float).copy()
    tris = np.asarray(tris)
    # Snap: a crossing near an edge's end moves to that end (its field becomes 0), so no sliver is made.
    for _ in range(3):
        e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
        fa, fb = f[e[:, 0]], f[e[:, 1]]
        cross = (fa * fb) < 0
        t = np.where(cross, fa / np.where(cross, fa - fb, 1.0), 0.5)
        near_a = cross & (t < snap)
        near_b = cross & (t > 1.0 - snap)
        if not (near_a.any() or near_b.any()):
            break
        f[e[near_a, 0]] = 0.0
        f[e[near_b, 1]] = 0.0
    sign = np.sign(f)
    new_index = {}
    parents = []
    out_v = [verts]
    count = len(verts)

    def crossing(a, b):
        nonlocal count
        key = (a, b) if a < b else (b, a)
        if key not in new_index:
            t = f[key[0]] / (f[key[0]] - f[key[1]])
            new_index[key] = count
            parents.append((key[0], key[1], t))
            out_v.append((verts[key[0]] * (1.0 - t) + verts[key[1]] * t)[None])
            count += 1
        return new_index[key]

    out_t, inside = [], []
    for tri in tris:
        sg = sign[tri]
        if (sg >= 0).all() or (sg <= 0).all():
            out_t.append(tri)
            inside.append(bool((sg > 0).any() or (sg == 0).all()))
            continue
        zeros = np.flatnonzero(sg == 0)
        if len(zeros) == 1:
            # The contour runs from the zero vertex to the opposite edge: two faces.
            k = zeros[0]
            a, b, c = tri[k], tri[(k + 1) % 3], tri[(k + 2) % 3]
            m = crossing(b, c)
            out_t += [np.array([a, b, m]), np.array([a, m, c])]
            inside += [bool(sign[b] > 0), bool(sign[c] > 0)]
            continue
        # One vertex alone on its side: its face, and the quad beyond (two faces).
        for k in range(3):
            if sg[k] != sg[(k + 1) % 3] and sg[k] != sg[(k + 2) % 3]:
                break
        a, b, c = tri[k], tri[(k + 1) % 3], tri[(k + 2) % 3]
        mab, mac = crossing(a, b), crossing(a, c)
        lone = bool(sign[a] > 0)
        # The quad mab-b-c-mac splits along whichever diagonal gives the larger smallest angle (fewer slivers).
        pos = np.concatenate(out_v)
        quads = ((np.array([mab, b, c]), np.array([mab, c, mac])), (np.array([mab, b, mac]), np.array([b, c, mac])))
        best = max(quads, key=lambda q: min(_min_angle(pos[q[0]]), _min_angle(pos[q[1]])))
        out_t += [np.array([a, mab, mac]), best[0], best[1]]
        inside += [lone, not lone, not lone]
    verts_out = np.concatenate(out_v)
    par = np.array([(a, b) for a, b, _ in parents], np.int64).reshape(-1, 2)
    ts = np.array([t for _, _, t in parents])
    return verts_out, np.array(out_t, np.int64), np.array(inside), par, ts, f


# --- The periodic harmonic map ------------------------------------------------------------------------------------------
# The torus mappings above fold where the toes make the cross-section concave. A harmonic map into the flat torus
# R^2 / (Pu Z x Pv Z), solved with positive weights, does not: Gortler, Gotsman and Thurston (2006) show that such a
# periodic Tutte embedding of a torus mesh, in the homotopy class of a closed one-form, has no folded face. The class
# is given by where an edge crosses the two seam loops:
# - the major seam (the turn's wrap at UV_SEAM_DEG), as torus_tiles has it;
# - the minor seam: an inner-wall edge (both ends nearer the channel's axis than the cross-section's centre) crossing
#   the channel's mid-plane, s = the centre's s.
# Each loop gets a whole number of texture tiles (the fur maps tile exactly), so neither seam shows.

def seam_crossings(verts, tris, fr, section):
    """Per directed half-edge (face, corner k -> k+1): its crossings (ku, kv) of the major and minor seams (+-1 or 0),
    and the faces whose crossings do not sum to zero (must be none).

    The major seam is where the turn wraps. The minor seam is one curve of the level set s = the inner wall's midline
    at each turn (CrossSection.inner_mid): the curve that winds round the channel nearest its axis. Taking one whole
    level curve keeps the class closed, since every face it crosses has exactly two crossing edges.
    - A first version took every crossing edge with both ends inside the centre's radius, and left 8 faces open where
      the mid-plane meets the surface near that radius.
    - A second used the cross-sections' median s, which jumps where only the thumb is, and no curve went round."""
    s, tau, rho = coords(verts, fr)
    a, b = tris, np.roll(tris, -1, 1)
    dt = tau[b] - tau[a]
    ku = np.where(dt < -math.pi, 1, np.where(dt > math.pi, -1, 0))
    g = s - section.inner_mid_at(tau)
    # Only within the inner wall's band (every corner within INNER_WALL of the channel). There the midline is one
    # closed curve round the channel, a longitude. A whole-surface level curve (v2) joined the inner and outer
    # crossings into one null-homologous curve, and v came out constant.
    band = (TPP.channel_sdf(verts, fr) < INNER_WALL)[tris].all(1)
    up = band[:, None] & (g[a] < 0) & (g[b] >= 0)
    down = band[:, None] & (g[b] < 0) & (g[a] >= 0)
    kv = np.where(up, -1, np.where(down, 1, 0))
    # A closed one-form: zero round every face, and opposite on the two half-edges of every edge.
    bad = list(np.flatnonzero((ku.sum(1) != 0) | (kv.sum(1) != 0)))
    half = {}
    for f, k in zip(*np.nonzero(kv)):
        key = (int(min(a[f, k], b[f, k])), int(max(a[f, k], b[f, k])))
        half.setdefault(key, []).append((int(f), int(kv[f, k]) * (1 if a[f, k] < b[f, k] else -1)))
    for key, rows in half.items():
        if len(rows) != 2 or rows[0][1] != rows[1][1]:
            bad += [f for f, _ in rows]
    return ku, kv, np.unique(np.array(bad, np.int64))


def uv_periodic(verts, tris, fr, section, periods=(1.0, 1.0), kind="mvc"):
    """Per corner UVs: the periodic harmonic map (above), each loop `periods` tiles. Returns (uvs, info)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    n = len(verts)
    ku, kv, bad = seam_crossings(verts, tris, fr, section)
    if len(bad):
        raise ValueError(f"{len(bad)} faces have inconsistent seam crossings")
    P = verts[tris]
    rows, cols, vals, bu, bv = [], [], [], np.zeros(n), np.zeros(n)
    for k in range(3):
        i, j, l = tris[:, k], tris[:, (k + 1) % 3], tris[:, (k + 2) % 3]
        if kind == "mvc":
            e_ij, e_il = P[:, (k + 1) % 3] - P[:, k], P[:, (k + 2) % 3] - P[:, k]
            cos_i = (e_ij * e_il).sum(1) / np.maximum(np.linalg.norm(e_ij, axis=1) * np.linalg.norm(e_il, axis=1), 1e-15)
            half = np.tan(np.arccos(np.clip(cos_i, -1, 1)) / 2.0)
            w_ij = half / np.maximum(np.linalg.norm(e_ij, axis=1), 1e-15)
            w_il = half / np.maximum(np.linalg.norm(e_il, axis=1), 1e-15)
            # i -> j crosses (ku, kv)[:, k]; i -> l is the reverse of l -> i, half-edge (k + 2) % 3
            pairs = ((j, w_ij, ku[:, k], kv[:, k]), (l, w_il, -ku[:, (k + 2) % 3], -kv[:, (k + 2) % 3]))
        else:
            e_li, e_lj = P[:, k] - P[:, (k + 2) % 3], P[:, (k + 1) % 3] - P[:, (k + 2) % 3]
            cot = 0.5 * (e_li * e_lj).sum(1) / np.maximum(np.linalg.norm(np.cross(e_li, e_lj), axis=1), 1e-15)
            pairs = ((j, cot, ku[:, k], kv[:, k]),)
            # the symmetric half: j -> i with the same weight
            rows.append(j); cols.append(i); vals.append(cot)
            np.add.at(bu, j, cot * (-ku[:, k]) * periods[0]); np.add.at(bv, j, cot * (-kv[:, k]) * periods[1])
            rows.append(j); cols.append(j); vals.append(-cot)
        for other, w, cu, cv in pairs:
            rows.append(i); cols.append(other); vals.append(w)
            rows.append(i); cols.append(i); vals.append(-w)
            np.add.at(bu, i, w * cu * periods[0])
            np.add.at(bv, i, w * cv * periods[1])
    L = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    # Sum_j w_ij (x_j + k_ij P - x_i) = 0  ->  L x = -b; pin vertex 0 at 0.
    L = L.tolil()
    L[0, :] = 0
    L[0, 0] = 1.0
    L = L.tocsr()
    bu, bv = -bu, -bv
    bu[0] = bv[0] = 0.0
    u, v = spsolve(L, bu), spsolve(L, bv)
    # Per corner: each face from its first corner, lifted along its own half-edges.
    cu = np.stack([u[tris[:, 0]], u[tris[:, 1]] + ku[:, 0] * periods[0],
                   u[tris[:, 2]] - ku[:, 2] * periods[0]], 1)
    cv = np.stack([v[tris[:, 0]], v[tris[:, 1]] + kv[:, 0] * periods[1],
                   v[tris[:, 2]] - kv[:, 2] * periods[1]], 1)
    return np.stack([cu, cv], -1), {"u_period_uv": float(periods[0]), "v_period_uv": float(periods[1]),
                                    "inconsistent_faces": int(len(bad)), "weights": kind}


# --- The cut, with exact roots and snapping by moving the vertex ---------------------------------------------------------
def _roots(va, vb, field_fn, iterations=40):
    """The parameter t in (0, 1) where field_fn crosses zero on each segment va -> vb (bisection; fa, fb of opposite
    sign)."""
    lo, hi = np.zeros(len(va)), np.ones(len(va))
    fa = field_fn(va)
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        fm = field_fn(va + (vb - va) * mid[:, None])
        same = np.sign(fm) == np.sign(fa)
        lo, hi = np.where(same, mid, lo), np.where(same, hi, mid)
    return 0.5 * (lo + hi)


def cut_exact(verts, tris, field_fn, snap=SNAP, move=True):
    """cut_by_field with each crossing at the field's own root on its edge. A crossing within `snap` of an edge's end
    moves that vertex onto it (move=True; the vertex slides along that edge) or puts the contour through the vertex
    as it is (move=False). Returns what cut_by_field does, plus the vertices moved and how far (m)."""
    verts = np.asarray(verts, float).copy()
    tris = np.asarray(tris)
    moved = {}
    for _ in range(4):
        f = field_fn(verts)
        f[list(moved)] = 0.0
        e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
        e = np.unique(np.sort(e, 1), axis=0)
        cross = (f[e[:, 0]] * f[e[:, 1]]) < 0
        if not cross.any():
            break
        ec = e[cross]
        t = _roots(verts[ec[:, 0]], verts[ec[:, 1]], field_fn)
        near_a, near_b = t < snap, t > 1.0 - snap
        changed = False
        for (a, b), tt, na, nb in zip(ec, t, near_a, near_b):
            vtx = a if na else (b if nb else None)
            if vtx is None or vtx in moved:
                continue
            target = verts[a] + (verts[b] - verts[a]) * tt
            moved[vtx] = float(np.linalg.norm(target - verts[vtx]))
            if move:
                verts[vtx] = target
            changed = True
        if not changed:
            break
    f = field_fn(verts)
    for vtx in moved:
        f[vtx] = 0.0
    # The remaining crossings at their exact roots.
    e = np.unique(np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), 1), axis=0)
    cross = (f[e[:, 0]] * f[e[:, 1]]) < 0
    ec = e[cross]
    t = _roots(verts[ec[:, 0]], verts[ec[:, 1]], field_fn) if len(ec) else np.zeros(0)
    exact = {(int(a), int(b)): float(tt) for (a, b), tt in zip(ec, t)}
    f_lin = f.copy()
    # cut_by_field places a crossing at fa / (fa - fb): give it values whose interpolation lands on the root.
    v2, t2, inside, parents, ts, f2 = cut_by_field(verts, tris, f_lin, snap=0.0)
    for idx, (a, b) in enumerate(parents):
        tt = exact[(int(min(a, b)), int(max(a, b)))]
        if a > b:
            tt = 1.0 - tt
        ts[idx] = tt
        v2[len(verts) + idx] = verts[a] + (verts[b] - verts[a]) * tt
    return v2, t2, inside, parents, ts, f2, moved


# --- The minor seam as the shortest loop round the channel ------------------------------------------------------------
# The level-set seams above (v2, v3) left faces open where the inner wall splits into patches at the thumb's and
# toes' tips. This takes the minor seam as an edge loop instead: the shortest closed loop of edges winding once round
# the channel. Being shortest, it runs on the inner wall, which faces the tsuka. Each face then gets, per corner, an
# offset of one period where its corner is a loop vertex and the face lies on the loop's right. A face's offsets lift
# its corners consistently by construction:
# - round a face, the differences of its corner offsets sum to zero;
# - across a shared edge, both faces see the same sides of the loop at that edge's ends.

def longitude_loop(verts, tris, fr):
    """The shortest edge loop winding once round the channel: (ordered vertices, its length m, turn winding rad)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    _, tau, _ = coords(verts, fr)
    e = np.unique(np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), 1), axis=0)
    length = np.linalg.norm(verts[e[:, 0]] - verts[e[:, 1]], axis=1)
    ta, tb = tau[e[:, 0]], tau[e[:, 1]]
    across = ((ta < 0) != (tb < 0)) & (np.abs(ta - tb) < math.pi)          # edges crossing the half-plane tau = 0
    keep = ~across
    n = len(verts)
    G = coo_matrix((np.concatenate([length[keep]] * 2),
                    (np.concatenate([e[keep, 0], e[keep, 1]]), np.concatenate([e[keep, 1], e[keep, 0]]))), shape=(n, n)).tocsr()
    cand = np.flatnonzero(across)
    # From each crossing edge's tau >= 0 end round the long way to its tau < 0 end; the shortest closes the loop.
    starts = np.where(tau[e[cand, 0]] >= 0, e[cand, 0], e[cand, 1])
    ends = np.where(tau[e[cand, 0]] >= 0, e[cand, 1], e[cand, 0])
    uniq, inv = np.unique(starts, return_inverse=True)
    dist, pred = dijkstra(G, indices=uniq, return_predecessors=True)
    total = dist[inv, ends] + length[cand]
    best = int(np.argmin(total))
    row, end = inv[best], ends[best]
    path = [int(end)]
    while path[-1] != uniq[row]:
        path.append(int(pred[row, path[-1]]))
    loop = path[::-1]                                                       # start (tau >= 0) ... end (tau < 0)
    winding = float(np.sum(np.angle(np.exp(1j * (tau[np.roll(loop, -1)] - tau[loop])))))
    return loop, float(total[best]), winding


def right_side_offsets(tris, loop):
    """Per face corner: 1 where the corner's vertex is on the loop and the face lies on the loop's right there, else 0.
    Faces are wound outward, so a face lies left of each of its half-edges."""
    half = {}
    for f, tri in enumerate(tris):
        for k in range(3):
            half[(int(tri[k]), int(tri[(k + 1) % 3]))] = (f, int(tri[(k + 2) % 3]))
    R = np.zeros(tris.shape, np.int8)
    m = len(loop)
    for i, v in enumerate(loop):
        nxt, prv = loop[(i + 1) % m], loop[(i - 1) % m]
        # Faces round v, counterclockwise from the face left of v -> nxt, until the one holding v_prv -> v.
        left = set()
        f, y = half[(v, nxt)]
        for _ in range(64):
            left.add(f)
            if y == prv:
                break
            f, y = half[(v, y)]
        else:
            raise ValueError(f"the fan round loop vertex {v} did not close")
        for f2 in np.flatnonzero((tris == v).any(1)):
            if f2 not in left:
                k = int(np.flatnonzero(tris[f2] == v)[0])
                R[f2, k] = 1
    return R


def uv_periodic_loop(verts, tris, fr, section, periods=(1.0, 1.0)):
    """The periodic harmonic map (mean-value weights) with the major seam where the turn wraps and the minor seam
    the shortest longitude loop (above). Returns (corner uvs, info)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    n = len(verts)
    ku, _, _ = seam_crossings(verts, tris, fr, section)
    if (ku.sum(1) != 0).any():
        raise ValueError("the major seam's crossings are not closed")
    loop, loop_len, winding = longitude_loop(verts, tris, fr)
    if abs(abs(winding) - 2.0 * math.pi) > 1e-6:
        raise ValueError(f"the longitude loop winds {winding:.4f} rad, not once round")
    R = right_side_offsets(tris, loop)
    P = verts[tris]
    rows, cols, vals = [], [], []
    bu, bv = np.zeros(n), np.zeros(n)
    for k in range(3):
        i, j, l = tris[:, k], tris[:, (k + 1) % 3], tris[:, (k + 2) % 3]
        e_ij, e_il = P[:, (k + 1) % 3] - P[:, k], P[:, (k + 2) % 3] - P[:, k]
        cos_i = (e_ij * e_il).sum(1) / np.maximum(np.linalg.norm(e_ij, axis=1) * np.linalg.norm(e_il, axis=1), 1e-15)
        half = np.tan(np.arccos(np.clip(cos_i, -1, 1)) / 2.0)
        w_ij = half / np.maximum(np.linalg.norm(e_ij, axis=1), 1e-15)
        w_il = half / np.maximum(np.linalg.norm(e_il, axis=1), 1e-15)
        for other, w, cu, cv in ((j, w_ij, ku[:, k], R[:, (k + 1) % 3] - R[:, k]),
                                 (l, w_il, -ku[:, (k + 2) % 3], R[:, (k + 2) % 3] - R[:, k])):
            rows += [i, i]
            cols += [other, i]
            vals += [w, -w]
            np.add.at(bu, i, w * cu * periods[0])
            np.add.at(bv, i, w * cv * periods[1])
    L = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tolil()
    L[0, :] = 0
    L[0, 0] = 1.0
    L = L.tocsr()
    bu, bv = -bu, -bv
    bu[0] = bv[0] = 0.0
    u, v = spsolve(L, bu), spsolve(L, bv)
    cu = np.stack([u[tris[:, 0]], u[tris[:, 1]] + ku[:, 0] * periods[0], u[tris[:, 2]] - ku[:, 2] * periods[0]], 1)
    cv = v[tris] + R * periods[1]
    return np.stack([cu, cv], -1), {"u_period_uv": float(periods[0]), "v_period_uv": float(periods[1]),
                                    "longitude_loop_vertices": len(loop), "longitude_loop_mm": round(loop_len * 1000, 1),
                                    "weights": "mvc"}


# --- A free-boundary near-isometric unwrap (ARAP) of the torus cut to a disk ----------------------------------------------
# The seamless periodic maps cannot keep the body's texel density. The paw's surface is about 0.24 of one fur tile's
# area at UV_PER_M, so whole-tile periods make its texture at least about twice as dense on average. The harmonic map
# spreads that unevenly: 0.24 on the back, 2.9 on the inner wall, in linear scale. This unwrap instead:
# - cuts the torus to a disk along the shortest longitude (the inner wall) and the shortest meridian through it
#   nearest the thumb's and toes' junction (UV_SEAM_DEG), both where the paw is least seen;
# - maps it as-rigid-as-possibly (Liu et al. 2008: local rotations, then a global cotangent solve), from a least-squares
#   conformal start (Levy et al. 2002), at UV_PER_M;
# - turns it so that u runs round the channel on the paw's back, as the baseline's round mapping does.
# Its two seams are real UV discontinuities, along edge paths in those hidden places.

def _split_loop_vertex_graph(verts, tris, loop):
    """The vertex graph with each loop vertex split into its left (index v) and right (index n + position in loop)
    copies, as the faces on each side see it; edges along the loop are dropped."""
    n = len(verts)
    R = right_side_offsets(tris, loop)
    pos = {v: k for k, v in enumerate(loop)}
    copy = np.where(R.astype(bool), np.vectorize(lambda v: n + pos.get(int(v), 0))(tris), tris)
    on_loop = np.zeros(n, bool)
    on_loop[loop] = True
    e = []
    for k in range(3):
        a, b = tris[:, k], tris[:, (k + 1) % 3]
        along = on_loop[a] & on_loop[b]
        e.append(np.stack([copy[:, k], copy[:, (k + 1) % 3]], 1)[~along])
    return np.unique(np.sort(np.concatenate(e), 1), axis=0), n + len(loop)


def meridian_loop(verts, tris, fr, loop):
    """The shortest edge loop crossing the longitude once, through the loop vertex nearest the major seam's turn."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    n = len(verts)
    edges, size = _split_loop_vertex_graph(verts, tris, loop)
    pos_all = np.concatenate([verts, verts[loop]])
    length = np.linalg.norm(pos_all[edges[:, 0]] - pos_all[edges[:, 1]], axis=1)
    G = coo_matrix((np.concatenate([length] * 2), (np.concatenate([edges[:, 0], edges[:, 1]]),
                                                    np.concatenate([edges[:, 1], edges[:, 0]]))), shape=(size, size)).tocsr()
    _, tau, _ = coords(verts, fr)
    k = int(np.argmin(np.abs(np.angle(np.exp(1j * (tau[loop] - math.pi))))))   # tau nearest +-pi
    src, dst = loop[k], n + k
    dist, pred = dijkstra(G, indices=[src], return_predecessors=True)
    path = [dst]
    while path[-1] != src:
        path.append(int(pred[0, path[-1]]))
    path = [p if p < n else loop[p - n] for p in path[::-1]]
    return path[:-1], float(dist[0, dst])                   # a closed loop: first == last vertex, dropped once


def cut_to_disk(tris, cut_edges):
    """Per face corner, the index of its vertex's copy: faces round a vertex share a copy unless a cut edge parts them."""
    cut = {(min(a, b), max(a, b)) for a, b in cut_edges}
    nv = int(tris.max()) + 1
    corner_copy = -np.ones(tris.shape, np.int64)
    # Union-find over face corners at the same vertex, joined across shared non-cut edges.
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for f in range(len(tris)):
        for k in range(3):
            parent[(f, k)] = (f, k)
    owner = {}
    for f, tri in enumerate(tris):
        for k in range(3):
            a, b = int(tri[k]), int(tri[(k + 1) % 3])
            key = (min(a, b), max(a, b))
            if key in cut:
                continue
            if key in owner:
                g, kk = owner[key]
                ga = int(np.flatnonzero(tris[g] == a)[0])
                gb = int(np.flatnonzero(tris[g] == b)[0])
                for c1, c2 in (((f, k), (g, ga)), ((f, (k + 1) % 3), (g, gb))):
                    r1, r2 = find(c1), find(c2)
                    if r1 != r2:
                        parent[r1] = r2
            else:
                owner[key] = (f, k)
    roots = {}
    vertex_of = []
    for f, tri in enumerate(tris):
        for k in range(3):
            r = find((f, k))
            if r not in roots:
                roots[r] = len(vertex_of)
                vertex_of.append(int(tri[k]))
            corner_copy[f, k] = roots[r]
    return corner_copy, np.array(vertex_of)


def _cot_laplacian(V, T):
    from scipy.sparse import coo_matrix
    n = len(V)
    rows, cols, vals = [], [], []
    for k in range(3):
        i, j, l = T[:, k], T[:, (k + 1) % 3], T[:, (k + 2) % 3]
        a, b = V[i] - V[l], V[j] - V[l]
        cot = (a * b).sum(1) / np.maximum(np.linalg.norm(np.cross(a, b), axis=1), 1e-15)
        w = 0.5 * np.maximum(cot, COT_FLOOR)      # surface nets' obtuse faces give negative cotangents: clamped
        rows += [i, j, i, j]
        cols += [j, i, i, j]
        vals += [-w, -w, w, w]
    return coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()


def _face_frames_2d(V, T):
    """Each face's corners in its own isometric 2D frame: (F, 3, 2)."""
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    x = b - a
    lx = np.linalg.norm(x, axis=1, keepdims=True)
    x = x / np.maximum(lx, 1e-15)
    nrm = np.cross(b - a, c - a)
    y = np.cross(nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-15), x)
    p = np.zeros((len(T), 3, 2))
    p[:, 1, 0] = lx[:, 0]
    p[:, 2, 0] = ((c - a) * x).sum(1)
    p[:, 2, 1] = ((c - a) * y).sum(1)
    return p


def lscm(V, T, pins):
    """Least-squares conformal map of a disk mesh, two vertices pinned at (0, 0) and (1, 0)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import lsqr
    n, F = len(V), len(T)
    p = _face_frames_2d(V, T)
    area2 = np.abs(p[:, 1, 0] * p[:, 2, 1] - p[:, 2, 0] * p[:, 1, 1])
    ws = []
    for k in range(3):
        d = p[:, (k + 2) % 3] - p[:, (k + 1) % 3]          # W_k = x_{k+2} - x_{k+1} as a complex number
        ws.append(d[:, 0] + 1j * d[:, 1])
    rows, cols, vals = [], [], []
    for k in range(3):
        w = ws[k] / np.sqrt(np.maximum(area2, 1e-30))
        # Re and Im parts: [Re W  -Im W; Im W  Re W] acting on (u_k, v_k)
        for r_off, (cu, cv) in ((0, (w.real, -w.imag)), (F, (w.imag, w.real))):
            rows += [np.arange(F) + r_off] * 2
            cols += [T[:, k], T[:, k] + n]
            vals += [cu, cv]
    A = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(2 * F, 2 * n)).tocsc()
    fixed = {pins[0]: (0.0, 0.0), pins[1]: (1.0, 0.0)}
    free = np.setdiff1d(np.arange(2 * n), [pins[0], pins[0] + n, pins[1], pins[1] + n])
    x0 = np.zeros(2 * n)
    for v, (uu, vv) in fixed.items():
        x0[v], x0[v + n] = uu, vv
    b = -A @ x0
    sol = lsqr(A[:, free], b, atol=1e-12, btol=1e-12, iter_lim=20000)[0]
    x = x0.copy()
    x[free] = sol
    return np.stack([x[:n], x[n:]], 1)


def arap(V, T, uv0, iterations=40):
    """As-rigid-as-possible refinement (local rotations, global cotangent solve), one vertex pinned (translation)."""
    from scipy.sparse.linalg import factorized
    n = len(V)
    p = _face_frames_2d(V, T)
    L = _cot_laplacian(V, T).tolil()
    L[0, :] = 0
    L[0, 0] = 1.0
    solve = factorized(L.tocsc())
    uv = uv0.copy()
    cots = []
    for k in range(3):
        i, j, l = k, (k + 1) % 3, (k + 2) % 3
        a, b = p[:, i] - p[:, l], p[:, j] - p[:, l]
        cots.append(np.maximum((a * b).sum(1) / np.maximum(np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]), 1e-15),
                               COT_FLOOR))
    for _ in range(iterations):
        # Local: the rotation nearest each face's Jacobian (frame -> uv).
        E = np.stack([p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]], 2)                # (F, 2, 2)
        U = np.stack([uv[T[:, 1]] - uv[T[:, 0]], uv[T[:, 2]] - uv[T[:, 0]]], 2)
        J = U @ np.linalg.inv(E)
        Us, _, Vt = np.linalg.svd(J)
        Rf = Us @ Vt
        flip = np.linalg.det(Rf) < 0
        Us[flip, :, 1] *= -1
        Rf = Us @ Vt
        # Global: L uv = sum over faces of cot-weighted rotated frame edges.
        b = np.zeros((n, 2))
        for k in range(3):
            i, j = k, (k + 1) % 3                               # cots[k] is the angle opposite this edge (at k + 2)
            w = 0.5 * cots[k]
            d = np.einsum("fab,fb->fa", Rf, p[:, i] - p[:, j])
            np.add.at(b, T[:, i], w[:, None] * d)
            np.add.at(b, T[:, j], -w[:, None] * d)
        b[0] = uv[0]
        uv = np.stack([solve(b[:, 0]), solve(b[:, 1])], 1)
    return uv


def uv_arap_disk(verts, tris, fr, iterations=40):
    """The unwrap above: per corner UVs at UV_PER_M, and the seams' edge paths."""
    loop, loop_len, winding = longitude_loop(verts, tris, fr)
    mer, mer_len = meridian_loop(verts, tris, fr, loop)
    cut_edges = [(loop[k], loop[(k + 1) % len(loop)]) for k in range(len(loop))]
    cut_edges += [(mer[k], mer[(k + 1) % len(mer)]) for k in range(len(mer))]
    corner_copy, vertex_of = cut_to_disk(tris, cut_edges)
    V = verts[vertex_of]
    T = corner_copy
    # Pins for LSCM: two far-apart copies.
    d = np.linalg.norm(V - V[0], axis=1)
    pins = (0, int(np.argmax(d)))
    uv = lscm(V, T, pins)
    # Scale the conformal start to the surface's area, then refine.
    a3 = 0.5 * np.linalg.norm(np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]), axis=1).sum()
    a2 = 0.5 * np.abs(np.cross(uv[T[:, 1]] - uv[T[:, 0]], uv[T[:, 2]] - uv[T[:, 0]])).sum()
    uv = uv * math.sqrt(a3 / max(a2, 1e-30))
    uv = arap(V, T, uv, iterations)
    # Orient: u along the turn on the paw's back (the faces whose coat would be 0 and which face away from the channel).
    s, tau, rho = coords(V, fr)
    back = TPP.channel_sdf(V, fr) > 0.02
    E = np.stack([uv[T[:, 1]] - uv[T[:, 0]], uv[T[:, 2]] - uv[T[:, 0]]], 2)
    dt = np.stack([np.angle(np.exp(1j * (tau[T[:, 1]] - tau[T[:, 0]]))), np.angle(np.exp(1j * (tau[T[:, 2]] - tau[T[:, 0]])))], 1)
    sel = back[T].all(1)
    # least-squares direction of increasing turn in uv: g with E^T g ~ dt
    g = np.linalg.lstsq(np.concatenate(list(E[sel].transpose(0, 2, 1))), np.concatenate(list(dt[sel])), rcond=None)[0]
    ang = math.atan2(g[1], g[0])
    rot = np.array([[math.cos(-ang), -math.sin(-ang)], [math.sin(-ang), math.cos(-ang)]])
    uv = uv @ rot.T * TPP.UV_PER_M
    uv = uv - uv.min(0)
    return uv[T], {"longitude_mm": round(loop_len * 1000, 1), "meridian_mm": round(mer_len * 1000, 1),
                   "seam_edges": len(cut_edges), "disk_vertices": int(len(V)), "iterations": iterations}


# --- The seamless periodic map, refined toward one uniform scale (periodic ARAP) ----------------------------------------
# A free-boundary unwrap cannot keep the paw's back at the body's density. Cut along its inner wall, the paw is a strip
# whose middle (the back) is about three times longer than its edges (the inner wall), so the back is squashed: area
# scale 0.29 on r3's right paw. LSCM and ARAP are both exact on a cut cylinder (test_paw_surface), so this is the
# shape, not the solver. The periodic maps keep the seams invisible at whole tiles. The harmonic one spreads its forced
# density unevenly, so this refines it as-rigid-as-possibly toward one uniform target scale:
#   s = sqrt(Pu * Pv / (surface area x UV_PER_M^2)),
# the scale at which the whole tile lattice covers the paw. The fur is then everywhere about s times the body's
# density: 2.9 for 2x1 tiles on r3's paws.

def periodic_lift(verts, tris, fr, section):
    """The periodic map's seam lifts: per face corner, the u offset (in periods, from the turn's wrap) and the v offset
    (in periods, right of the shortest longitude)."""
    ku, _, _ = seam_crossings(verts, tris, fr, section)
    loop, _, _ = longitude_loop(verts, tris, fr)
    R = right_side_offsets(tris, loop).astype(float)
    ou = np.stack([np.zeros(len(tris)), ku[:, 0].astype(float), -ku[:, 2].astype(float)], 1)
    return ou, R


def uv_periodic_arap(verts, tris, fr, section, periods=(2.0, 1.0), iterations=60):
    """Per corner UVs (above) and info. Starts from the mean-value periodic map (uv_periodic_loop)."""
    from scipy.sparse.linalg import factorized
    uv_c, _ = uv_periodic_loop(verts, tris, fr, section, periods)
    ou, ov = periodic_lift(verts, tris, fr, section)
    O = np.stack([ou * periods[0], ov * periods[1]], -1)          # (F, 3, 2) corner lifts in UV
    n = len(verts)
    uv = np.zeros((n, 2))
    uv[tris] = uv_c - O                                            # per vertex (every corner of a vertex agrees)
    p = _face_frames_2d(verts, tris)
    area = 0.5 * np.abs(p[:, 1, 0] * p[:, 2, 1] - p[:, 2, 0] * p[:, 1, 1])
    s = math.sqrt(periods[0] * periods[1] / (area.sum() * TPP.UV_PER_M ** 2)) * TPP.UV_PER_M
    L = _cot_laplacian(verts, tris).tolil()
    L[0, :] = 0
    L[0, 0] = 1.0
    solve = factorized(L.tocsc())
    cots = []
    for k in range(3):
        i, j, l = k, (k + 1) % 3, (k + 2) % 3
        a, b = p[:, i] - p[:, l], p[:, j] - p[:, l]
        cots.append(np.maximum((a * b).sum(1) / np.maximum(np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]), 1e-15), COT_FLOOR))
    E = np.stack([p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]], 2)
    Einv = np.linalg.inv(E)
    for _ in range(iterations):
        C = uv[tris] + O
        U = np.stack([C[:, 1] - C[:, 0], C[:, 2] - C[:, 0]], 2)
        Us, _, Vt = np.linalg.svd(U @ Einv)
        flip = np.linalg.det(Us @ Vt) < 0
        Us[flip, :, 1] *= -1
        Rf = (Us @ Vt) * s
        b = np.zeros((n, 2))
        for k in range(3):
            a_, b_ = k, (k + 1) % 3
            w = 0.5 * cots[k]
            d = np.einsum("fab,fb->fa", Rf, p[:, a_] - p[:, b_]) - O[:, a_] + O[:, b_]
            np.add.at(b, tris[:, a_], w[:, None] * d)
            np.add.at(b, tris[:, b_], -w[:, None] * d)
        b[0] = uv[0]
        uv = np.stack([solve(b[:, 0]), solve(b[:, 1])], 1)
    return uv[tris] + O, {"periods": list(periods), "target_scale": round(s / TPP.UV_PER_M, 4), "iterations": iterations}


def untangle(verts, tris, uv_corner, max_rings=6):
    """Unfold the faces a map folds (UV winding opposite the majority): their neighbourhood's interior vertices are
    re-solved harmonically with uniform positive weights and the neighbourhood's boundary fixed (Tutte), growing the
    neighbourhood a ring at a time until none is folded. A neighbourhood is solved in one consistent chart, so one
    that holds a seam's lift is skipped and reported. Returns (corner uvs, record)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    uv_corner = uv_corner.copy()
    n = len(verts)

    def folded(uvc):
        d = (uvc[:, 1, 0] - uvc[:, 0, 0]) * (uvc[:, 2, 1] - uvc[:, 0, 1]) - (uvc[:, 2, 0] - uvc[:, 0, 0]) * (uvc[:, 1, 1] - uvc[:, 0, 1])
        major = 1.0 if (d > 0).sum() >= (d < 0).sum() else -1.0
        return np.flatnonzero(d * major < 0)

    record = {"folded_before": [int(f) for f in folded(uv_corner)], "rings": None, "skipped": []}
    adj_faces = [[] for _ in range(n)]
    for f, tri in enumerate(tris):
        for v in tri:
            adj_faces[v].append(f)
    for rings in range(1, max_rings + 1):
        bad = folded(uv_corner)
        if not len(bad):
            record["rings"] = rings - 1
            break
        region_f = set(int(f) for f in bad)
        for _ in range(rings):
            verts_r = {int(v) for f in region_f for v in tris[f]}
            region_f |= {f for v in verts_r for f in adj_faces[v]}
        region_f = np.array(sorted(region_f))
        # One chart: every corner of a vertex in the region must agree (no seam lift inside it).
        vals = {}
        consistent = True
        for f in region_f:
            for k in range(3):
                v = int(tris[f, k])
                if v in vals and np.abs(vals[v] - uv_corner[f, k]).max() > 1e-9:
                    consistent = False
                vals[v] = uv_corner[f, k]
        if not consistent:
            record["skipped"].append(rings)
            continue
        inner_v = {int(v) for f in region_f for v in tris[f]}
        boundary = {v for v in inner_v if any(f not in set(region_f.tolist()) for f in adj_faces[v])}
        free = sorted(inner_v - boundary)
        idx = {v: i for i, v in enumerate(free)}
        rows, cols, vals_m, b = [], [], [], np.zeros((len(free), 2))
        nbrs = {v: set() for v in free}
        for f in region_f:
            t = tris[f]
            for k in range(3):
                a, c = int(t[k]), int(t[(k + 1) % 3])
                if a in nbrs:
                    nbrs[a].add(c)
                if c in nbrs:
                    nbrs[c].add(a)
        for v, ns in nbrs.items():
            i = idx[v]
            rows.append(i); cols.append(i); vals_m.append(float(len(ns)))
            for w in ns:
                if w in idx:
                    rows.append(i); cols.append(idx[w]); vals_m.append(-1.0)
                else:
                    b[i] += vals[w]
        A = coo_matrix((vals_m, (rows, cols)), shape=(len(free), len(free))).tocsr()
        sol = np.stack([spsolve(A, b[:, 0]), spsolve(A, b[:, 1])], 1)
        for f in region_f:
            for k in range(3):
                v = int(tris[f, k])
                if v in idx:
                    uv_corner[f, k] = sol[idx[v]]
    record["folded_after"] = [int(f) for f in folded(uv_corner)]
    return uv_corner, record
