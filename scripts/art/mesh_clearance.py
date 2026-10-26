"""Visible-mesh clearance between two triangle sets, for the third-person grip contract
(docs/art-direction/THIRD_PERSON_GRIP_CONTRACT.md).

It replaces two weaker tests:
- a movement capsule, which is not what anyone sees (hip gear lies inside it by design);
- vertex-to-vertex distances, which can miss a crossing: two triangles can intersect while every pair of their
  vertices is centimetres apart.

**What each measure establishes, for one pose:**
- **Crossings:** the pairs of triangles whose surfaces intersect.
  - The rig build uses Blender's BVHTree.overlap, which runs an exact triangle-triangle test (isect_tri_tri) on each
    candidate pair. The CPU backend tests every pair.
  - Neither backend is trusted with coplanar triangles. So every pair within CONTACT_EPS that the backend did not
    report is tested here for a coplanar overlap of positive area, which counts as a crossing. Pairs that only touch
    (an edge or a vertex) are counted as touching.
- **Allowed and hidden crossings:** a saya is thrust through the obi, so its crossings with the obi's own parts are
  the intended tuck, counted as allowed. A crossing counts as hidden only if all of its intersection segment lies
  inside one closed "hide" island (that obi): both ends inside by ray parity, and no triangle of the island crossing
  the segment. That holds for a non-convex volume too. A midpoint, or the ends alone, would not do. Otherwise, and
  for every coplanar overlap, the crossing counts as visible. In the same way, an island sealed inside an allowed
  part (the saya's mouth fittings inside the obi) is counted as allowed containment, not as containment.
- **Containment:** with no crossings between them, a connected island lies wholly inside or wholly outside each closed
  island of the other set. One vertex per island decides it, by ray parity along two directions against each closed
  island whose bounds hold it; directions that disagree count as ambiguous. Open islands (an edge used once, or more
  than twice) bound no inside, so they are counted, not tested.
- **Separation:** the exact least distance between the two surfaces, up to a limit. Every pair of triangles whose
  bounds come within the limit is measured: the least of its 6 vertex-face and 9 edge-edge closest-point distances,
  or 0 when the two cross. For triangles that do not cross, that is their exact distance, since the closest pair
  of two disjoint triangles is a vertex and a face or two edges. No pair within the limit certifies "at least the
  limit". The least vertex-to-surface distance alone would be only an upper bound, since two edges can pass closer
  than any vertex comes to a face. So it certifies no minimum and is not used.

`calibrate` runs a backend on known geometry, each case with its expected value:
- a crossing pair;
- a tetrahedron inside a cube;
- two cubes 2 cm apart;
- two bars whose edges pass 5 mm apart, their nearest vertices 27 cm apart;
- a rod crossing a box inside a hide volume;
- a 1.6 m crossing whose midpoint alone lies in a 10 cm hide cube (root's probe, 2026-10-26), which must stay visible;
- two coplanar triangles overlapping with positive area (root's probe), which must count as a crossing.
"""
from __future__ import annotations

import math

import numpy as np

RAYS = (np.array([0.6211, 0.4729, 0.6249]) / np.linalg.norm([0.6211, 0.4729, 0.6249]),
        np.array([-0.3127, 0.8846, -0.3459]) / np.linalg.norm([-0.3127, 0.8846, -0.3459]))
EPS = 1e-12
CONTACT_EPS = 1e-7                                   # m: a pair this close touches


# --- Topology --------------------------------------------------------------------------------------------------------
def islands(tris):
    """Each triangle's island, 0..k-1: triangles sharing a vertex are one island."""
    tris = np.asarray(tris, np.int64)
    if not len(tris):
        return np.zeros(0, np.int64)
    parent = list(range(int(tris.max()) + 1))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b, c in tris.tolist():
        ra = find(a)
        for v in (b, c):
            rv = find(v)
            if rv != ra:
                parent[rv] = ra
    roots = np.array([find(t[0]) for t in tris.tolist()])
    return np.unique(roots, return_inverse=True)[1].astype(np.int64)


def closed_islands(tris, island):
    """Per island: True when each of its edges is used by exactly two of its triangles."""
    tris = np.asarray(tris, np.int64)
    k = int(island.max()) + 1 if len(island) else 0
    ok = np.ones(k, bool)
    if not k:
        return ok
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    e.sort(axis=1)
    keys = np.stack([np.concatenate([island] * 3), e[:, 0], e[:, 1]], 1)
    uniq, counts = np.unique(keys, axis=0, return_counts=True)
    ok[uniq[counts != 2, 0]] = False
    return ok


class TriSet:
    """A set's topology, fixed across poses: its triangles (indices into a full point array), one part name per
    triangle, and its islands. Positions come with each measurement."""

    def __init__(self, tris, names):
        tris = np.asarray(tris, np.int64).reshape(-1, 3)
        self.used = np.unique(tris)
        remap = np.full(int(tris.max()) + 1 if len(tris) else 1, -1, np.int64)
        remap[self.used] = np.arange(len(self.used))
        self.tris = remap[tris]
        self.names = np.asarray(names).reshape(-1)
        assert len(self.names) == len(self.tris)
        self.island = islands(self.tris)
        self.closed = closed_islands(self.tris, self.island)
        self.first_vertex = np.zeros(len(self.closed), np.int64)
        seen = np.zeros(len(self.closed), bool)
        for t, isl in zip(self.tris[:, 0].tolist(), self.island.tolist()):
            if not seen[isl]:
                seen[isl], self.first_vertex[isl] = True, t

    def __len__(self):
        return len(self.tris)

    def positions(self, pts_full):
        return np.asarray(pts_full, np.float64)[self.used]


# --- Geometry (numpy): exact for non-coplanar triangles ---------------------------------------------------------------
def segment_triangle(p0, p1, a, b, c):
    """Where segment p0-p1 crosses triangle abc (Moller-Trumbore, the segment's t in [0, 1]), or None."""
    d = p1 - p0
    e1, e2 = b - a, c - a
    h = np.cross(d, e2)
    det = float(e1 @ h)
    if abs(det) < EPS:
        return None
    f = 1.0 / det
    s = p0 - a
    u = f * float(s @ h)
    if u < 0.0 or u > 1.0:
        return None
    q = np.cross(s, e1)
    v = f * float(d @ q)
    if v < 0.0 or u + v > 1.0:
        return None
    t = f * float(e2 @ q)
    if t < 0.0 or t > 1.0:
        return None
    return p0 + t * d


def tri_tri_points(t1, t2):
    """The points where an edge of one triangle crosses the other: empty when they do not cross. For non-coplanar
    triangles these are the ends of their intersection segment."""
    out = []
    for p, q in ((t1, t2), (t2, t1)):
        for i in range(3):
            x = segment_triangle(p[i], p[(i + 1) % 3], *q)
            if x is not None:
                out.append(x)
    return out


def coplanar_overlap(t1, t2, plane_tol=1e-7, area_tol=1e-14):
    """Whether two coplanar triangles overlap with positive area in their common plane: an edge of one properly
    crossing an edge of the other, a vertex strictly inside the other, or (congruent) each centroid inside the other.
    Triangles not within plane_tol (m) of one plane return False."""
    n = np.cross(t1[1] - t1[0], t1[2] - t1[0])
    nn = float(np.linalg.norm(n))
    if nn < 1e-15:
        return False
    n = n / nn
    if float(np.max(np.abs((t2 - t1[0]) @ n))) > plane_tol:
        return False
    axes = [i for i in range(3) if i != int(np.argmax(np.abs(n)))]
    a2, b2 = t1[:, axes], t2[:, axes]

    def orient(p, q, r):
        return float((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]))

    def inside(p, tri):
        s = [orient(tri[i], tri[(i + 1) % 3], p) for i in range(3)]
        return all(x > area_tol for x in s) or all(x < -area_tol for x in s)

    def proper(p1, p2, q1, q2):
        d1, d2, d3, d4 = orient(q1, q2, p1), orient(q1, q2, p2), orient(p1, p2, q1), orient(p1, p2, q2)
        return (d1 * d2 < -area_tol ** 2 and min(abs(d1), abs(d2)) > area_tol
                and d3 * d4 < -area_tol ** 2 and min(abs(d3), abs(d4)) > area_tol)

    if any(proper(a2[i], a2[(i + 1) % 3], b2[j], b2[(j + 1) % 3]) for i in range(3) for j in range(3)):
        return True
    if any(inside(q, b2) for q in a2) or any(inside(q, a2) for q in b2):
        return True
    return inside(a2.mean(0), b2) and inside(b2.mean(0), a2)


def crossing_segment(t1, t2):
    """The intersection segment of two crossing triangles: its two farthest edge-crossing points, or None when the
    edge tests find none (a coplanar pair)."""
    pts = tri_tri_points(t1, t2)
    if not pts:
        return None
    q = np.array(pts)
    d = np.linalg.norm(q[:, None] - q[None], axis=2)
    i, j = np.unravel_index(int(np.argmax(d)), d.shape)
    return q[i], q[j]


def ray_triangle_t(origin, direction, a, b, c):
    """The ray's parameter where it meets triangle abc (t > 1e-9), or None."""
    e1, e2 = b - a, c - a
    h = np.cross(direction, e2)
    det = float(e1 @ h)
    if abs(det) < EPS:
        return None
    f = 1.0 / det
    s = origin - a
    u = f * float(s @ h)
    if u < 0.0 or u > 1.0:
        return None
    q = np.cross(s, e1)
    v = f * float(direction @ q)
    if v < 0.0 or u + v > 1.0:
        return None
    t = f * float(e2 @ q)
    return t if t > 1e-9 else None


def point_triangle(p, a, b, c):
    """The closest point of triangle abc to p (Ericson, Real-Time Collision Detection 5.1.5)."""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = ab @ ap, ac @ ap
    if d1 <= 0 and d2 <= 0:
        return a
    bp = p - b
    d3, d4 = ab @ bp, ac @ bp
    if d3 >= 0 and d4 <= d3:
        return b
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        return a + ab * (d1 / (d1 - d3))
    cp = p - c
    d5, d6 = ab @ cp, ac @ cp
    if d6 >= 0 and d5 <= d6:
        return c
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        return a + ac * (d2 / (d2 - d6))
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        return b + (c - b) * ((d4 - d3) / ((d4 - d3) + (d5 - d6)))
    denom = 1.0 / (va + vb + vc)
    return a + ab * (vb * denom) + ac * (vc * denom)


# --- Exact triangle-pair distance (numpy, vectorised over pairs) ----------------------------------------------------
def _dot(u, v):
    return np.einsum("ij,ij->i", u, v)


def _safe(x):
    return np.where(np.abs(x) > 1e-300, x, 1.0)


def closest_point_triangle_v(p, a, b, c):
    """point_triangle for n points and n triangles at once ((n, 3) each). Ericson's regions are tried in his order
    (A, B, AB, C, AC, BC, inside): the later np.where calls below take precedence."""
    ab, ac = b - a, c - a
    d1, d2 = _dot(ab, p - a), _dot(ac, p - a)
    d3, d4 = _dot(ab, p - b), _dot(ac, p - b)
    d5, d6 = _dot(ab, p - c), _dot(ac, p - c)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    den = _safe(va + vb + vc)
    out = a + ab * (vb / den)[:, None] + ac * (vc / den)[:, None]
    m = (va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0)
    out = np.where(m[:, None], b + (c - b) * ((d4 - d3) / _safe((d4 - d3) + (d5 - d6)))[:, None], out)
    m = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    out = np.where(m[:, None], a + ac * (d2 / _safe(d2 - d6))[:, None], out)
    out = np.where(((d6 >= 0) & (d5 <= d6))[:, None], c, out)
    m = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    out = np.where(m[:, None], a + ab * (d1 / _safe(d1 - d3))[:, None], out)
    out = np.where(((d3 >= 0) & (d4 <= d3))[:, None], b, out)
    return np.where(((d1 <= 0) & (d2 <= 0))[:, None], a, out)


def closest_segments_v(p1, q1, p2, q2):
    """The closest points of n segment pairs (Ericson 5.1.9, with his degenerate cases)."""
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e, f = _dot(d1, d1), _dot(d2, d2), _dot(d2, r)
    c, b = _dot(d1, r), _dot(d1, d2)
    tiny = 1e-24
    den = a * e - b * b
    s = np.where(den > tiny, np.clip((b * f - c * e) / _safe(den), 0.0, 1.0), 0.0)
    t = (b * s + f) / _safe(np.where(e > tiny, e, 1.0))
    s = np.where(t < 0.0, np.clip(-c / _safe(np.where(a > tiny, a, 1.0)), 0.0, 1.0),
                 np.where(t > 1.0, np.clip((b - c) / _safe(np.where(a > tiny, a, 1.0)), 0.0, 1.0), s))
    t = np.clip(t, 0.0, 1.0)
    first_point = a <= tiny                                  # the first segment is a point
    second_point = e <= tiny
    s = np.where(first_point, 0.0, np.where(second_point, np.clip(-c / _safe(a), 0.0, 1.0), s))
    t = np.where(first_point & ~second_point, np.clip(f / _safe(e), 0.0, 1.0), np.where(second_point, 0.0, t))
    return p1 + d1 * s[:, None], p2 + d2 * t[:, None]


def segments_cross_triangles_v(p0, p1, a, b, c):
    """For n segments and n triangles: whether each segment crosses its triangle (segment_triangle, vectorised), and
    where."""
    d, e1, e2 = p1 - p0, b - a, c - a
    h = np.cross(d, e2)
    det = _dot(e1, h)
    ok = np.abs(det) > EPS
    f = 1.0 / _safe(det)
    s = p0 - a
    u = f * _dot(s, h)
    q = np.cross(s, e1)
    v = f * _dot(d, q)
    t = f * _dot(e2, q)
    return ok & (u >= 0) & (u <= 1) & (v >= 0) & (u + v <= 1) & (t >= 0) & (t <= 1), p0 + d * t[:, None]


def triangle_distances_v(t1, t2):
    """Exact distances of n triangle pairs ((n, 3, 3) each): 0 for a crossing pair, else the least vertex-face or
    edge-edge distance. Returns the distances, the closest points on each, and the kind of the closest pair."""
    n = len(t1)
    best = np.full(n, np.inf)
    q1, q2 = np.zeros((n, 3)), np.zeros((n, 3))
    kind = np.zeros(n, np.int8)                              # 0 crossing, 1 vertex-face, 2 edge-edge
    for p_set, tri, swap in ((t1, t2, False), (t2, t1, True)):
        for i in range(3):
            cp = closest_point_triangle_v(p_set[:, i], tri[:, 0], tri[:, 1], tri[:, 2])
            d = np.linalg.norm(p_set[:, i] - cp, axis=1)
            m = d < best
            best = np.where(m, d, best)
            a_pt, b_pt = (cp, p_set[:, i]) if swap else (p_set[:, i], cp)
            q1, q2 = np.where(m[:, None], a_pt, q1), np.where(m[:, None], b_pt, q2)
            kind = np.where(m, 1, kind)
    for i in range(3):
        for j in range(3):
            c1, c2 = closest_segments_v(t1[:, i], t1[:, (i + 1) % 3], t2[:, j], t2[:, (j + 1) % 3])
            d = np.linalg.norm(c1 - c2, axis=1)
            m = d < best
            best = np.where(m, d, best)
            q1, q2 = np.where(m[:, None], c1, q1), np.where(m[:, None], c2, q2)
            kind = np.where(m, 2, kind)
    cross = np.zeros(n, bool)
    for p_set, tri in ((t1, t2), (t2, t1)):
        for i in range(3):
            m, x = segments_cross_triangles_v(p_set[:, i], p_set[:, (i + 1) % 3], tri[:, 0], tri[:, 1], tri[:, 2])
            m &= ~cross                                      # the first crossing point found, on both triangles
            q1, q2 = np.where(m[:, None], x, q1), np.where(m[:, None], x, q2)
            cross |= m
    best = np.where(cross, 0.0, best)
    kind = np.where(cross, 0, kind)
    return best, q1, q2, kind


KINDS = ("crossing", "vertex-face", "edge-edge")


def touching_pairs(pa, tris_a, pb, tris_b, eps=CONTACT_EPS, chunk=128):
    """Every pair of triangles within eps of each other (exact triangle distance), as (index in a, index in b)."""
    A, Bt = np.asarray(pa, np.float64)[tris_a], np.asarray(pb, np.float64)[tris_b]
    out = []
    if not len(A) or not len(Bt):
        return out
    alo, ahi, blo, bhi = A.min(1), A.max(1), Bt.min(1), Bt.max(1)
    ia = np.nonzero(np.all((alo <= bhi.max(0) + eps) & (ahi >= blo.min(0) - eps), 1))[0]
    ib = np.nonzero(np.all((blo <= ahi.max(0) + eps) & (bhi >= alo.min(0) - eps), 1))[0]
    for s in range(0, len(ia), chunk):
        ca = ia[s:s + chunk]
        near = np.all((alo[ca][:, None] - eps <= bhi[ib][None]) & (ahi[ca][:, None] + eps >= blo[ib][None]), 2)
        ii, jj = np.nonzero(near)
        if not len(ii):
            continue
        d = triangle_distances_v(A[ca[ii]], Bt[ib[jj]])[0]
        keep = d <= eps
        out += list(zip(ca[ii][keep].tolist(), ib[jj][keep].tolist()))
    return out


def exact_separation(pa, tris_a, pb, tris_b, limit, chunk=128):
    """The exact least distance between two triangle sets, if it is below limit (else None): every pair whose
    bounds, grown by limit, overlap is measured by triangle_distances_v. Returns a dict with the distance, its
    points (as given), its kind, and how many pairs were measured."""
    A, Bt = np.asarray(pa, np.float64)[tris_a], np.asarray(pb, np.float64)[tris_b]
    out = {"separation_m": None, "at": None, "kind": None, "pairs_measured": 0, "limit_m": limit}
    if not len(A) or not len(Bt):
        return out
    alo, ahi, blo, bhi = A.min(1), A.max(1), Bt.min(1), Bt.max(1)
    ia = np.nonzero(np.all((alo <= bhi.max(0) + limit) & (ahi >= blo.min(0) - limit), 1))[0]
    ib = np.nonzero(np.all((blo <= ahi.max(0) + limit) & (bhi >= alo.min(0) - limit), 1))[0]
    best = limit
    for s in range(0, len(ia), chunk):
        ca = ia[s:s + chunk]
        near = np.all((alo[ca][:, None] - best <= bhi[ib][None]) & (ahi[ca][:, None] + best >= blo[ib][None]), 2)
        ii, jj = np.nonzero(near)
        if not len(ii):
            continue
        d, q1, q2, kind = triangle_distances_v(A[ca[ii]], Bt[ib[jj]])
        out["pairs_measured"] += int(len(d))
        k = int(np.argmin(d))
        if d[k] < best:
            best = float(d[k])
            out.update(separation_m=best, at=[q1[k], q2[k]], kind=KINDS[int(kind[k])])
    return out


# --- Backends -------------------------------------------------------------------------------------------------------
class BruteBackend:
    """Every pair, in numpy: for the CPU tests and the calibration's reference values."""
    name = "numpy, every pair"

    def tree(self, pts, tris):
        return np.asarray(pts, np.float64), np.asarray(tris, np.int64)

    def crossings(self, ta, tb):
        (pa, fa), (pb, fb) = ta, tb
        out = []
        for i, f in enumerate(fa):
            a = pa[f]
            lo, hi = a.min(0), a.max(0)
            for j, g in enumerate(fb):
                b = pb[g]
                if (hi < b.min(0)).any() or (b.max(0) < lo).any():
                    continue
                if tri_tri_points(a, b) or coplanar_overlap(a, b):
                    out.append((i, j))
        return out

    def segment_hits(self, tree, p0, p1):
        pa, fa = tree
        return any(segment_triangle(p0, p1, *pa[f]) is not None for f in fa)

    def ray_hits(self, tree, origin, direction):
        pa, fa = tree
        ts = sorted(t for t in (ray_triangle_t(origin, direction, *pa[f]) for f in fa) if t is not None)
        return sum(1 for i, t in enumerate(ts) if i == 0 or t - ts[i - 1] > 1e-9)


class BlenderBackend:
    """mathutils.bvhtree in the rig build: overlap runs isect_tri_tri on each candidate pair."""
    name = "Blender mathutils.bvhtree (overlap: isect_tri_tri per candidate pair)"

    def __init__(self):
        from mathutils import Vector
        from mathutils.bvhtree import BVHTree
        self.vector, self.bvh = Vector, BVHTree

    def tree(self, pts, tris):
        return self.bvh.FromPolygons([tuple(map(float, p)) for p in pts], [tuple(map(int, t)) for t in tris],
                                     all_triangles=True)

    def crossings(self, ta, tb):
        return ta.overlap(tb)

    def segment_hits(self, tree, p0, p1):
        d = self.vector(tuple(map(float, p1))) - self.vector(tuple(map(float, p0)))
        if d.length < 1e-12:
            return False
        return tree.ray_cast(self.vector(tuple(map(float, p0))), d.normalized(), d.length)[0] is not None

    def ray_hits(self, tree, origin, direction, step=1e-5, cap=512):
        o, d = self.vector(tuple(map(float, origin))), self.vector(tuple(map(float, direction))).normalized()
        n = 0
        while n < cap:
            loc = tree.ray_cast(o, d)[0]
            if loc is None:
                break
            n += 1
            o = loc + d * step
        return n


# --- The measurement ------------------------------------------------------------------------------------------------
def _bounds(pts, tset):
    k = len(tset.closed)
    lo, hi = np.full((k, 3), np.inf), np.full((k, 3), -np.inf)
    corners = pts[tset.tris]
    np.minimum.at(lo, tset.island, corners.min(1))
    np.maximum.at(hi, tset.island, corners.max(1))
    return lo, hi


def _inside(backend, cache, key, tset, pts, isl, p):
    """Ray parity of p against closed island isl: True, False, or None (the two directions disagree)."""
    if key not in cache:
        cache[key] = backend.tree(pts, tset.tris[tset.island == isl])
    hits = [backend.ray_hits(cache[key], p, d) for d in RAYS]
    if hits[0] % 2 != hits[1] % 2:
        return None
    return bool(hits[0] % 2)


def _top(counter, n=8):
    return [[*k, v] for k, v in sorted(counter.items(), key=lambda kv: -kv[1])[:n]]


def measure(backend, set_a, pts_a, set_b, pts_b, limit=0.10, hide=None, allowed=(), to_report=lambda p: p):
    """Crossings, containment and separation between set_a and set_b at these positions (full point arrays, each
    indexed as its set's triangles are).
    - limit: the exact separation is measured up to it; 0 skips it.
    - hide: (TriSet, full points) of closed volumes whose inside is not seen; a crossing inside one counts as hidden.
    - allowed: part-name prefixes in set_b whose crossings are intended (the obi's tuck), counted as allowed.
    - to_report maps a position to the report's frame."""
    pa, pb = set_a.positions(pts_a), set_b.positions(pts_b)
    ta, tb = backend.tree(pa, set_a.tris), backend.tree(pb, set_b.tris)
    pairs = [tuple(map(int, ij)) for ij in backend.crossings(ta, tb)]
    reported = set(pairs)
    touching, coplanar = 0, set()
    for i, j in touching_pairs(pa, set_a.tris, pb, set_b.tris):
        if (i, j) in reported:
            continue
        if coplanar_overlap(pa[set_a.tris[i]], pb[set_b.tris[j]]):
            coplanar.add((i, j))
        else:
            touching += 1
    hide_cache, visible, hidden, allowed_n, crossing_islands = {}, {}, {}, {}, set()
    first_visible = None
    if hide is not None:
        hset, hpts_full = hide
        hp = hset.positions(hpts_full)
        hlo, hhi = _bounds(hp, hset)

    def segment_hidden(seg):
        """All of seg inside one closed hide island: both ends inside, and no triangle of it crossing seg."""
        if hide is None or seg is None:
            return False
        p0, p1 = seg
        lo, hi = np.minimum(p0, p1), np.maximum(p0, p1)
        for h in np.nonzero(hset.closed & np.all((hlo <= lo) & (hi <= hhi), 1))[0]:
            key_h = ("h", int(h))
            if (_inside(backend, hide_cache, key_h, hset, hp, int(h), p0) is True
                    and _inside(backend, hide_cache, key_h, hset, hp, int(h), p1) is True
                    and not backend.segment_hits(hide_cache[key_h], p0, p1)):
                return True
        return False

    for i, j in pairs + sorted(coplanar):
        crossing_islands.add((int(set_a.island[i]), int(set_b.island[j])))
        key = (str(set_a.names[i]), str(set_b.names[j]))
        if allowed and key[1].startswith(tuple(allowed)):
            allowed_n[key] = allowed_n.get(key, 0) + 1
            continue
        seg = None if (i, j) in coplanar else crossing_segment(pa[set_a.tris[i]], pb[set_b.tris[j]])
        in_hide = segment_hidden(seg)                    # a coplanar overlap, or no segment found, stays visible
        bucket = hidden if in_hide else visible
        bucket[key] = bucket.get(key, 0) + 1
        if not in_hide and first_visible is None:
            first_visible = (np.mean(seg, 0) if seg is not None
                             else (pa[set_a.tris[i]].mean(0) + pb[set_b.tris[j]].mean(0)) / 2.0)
    # Containment, both ways, for island pairs that do not cross.
    contained, contained_allowed, ambiguous, cache = {}, {}, {}, {}
    for src, sp, dst, dp, flip in ((set_a, pa, set_b, pb, False), (set_b, pb, set_a, pa, True)):
        lo, hi = _bounds(dp, dst)
        for isl in range(len(src.closed)):
            p = sp[src.first_vertex[isl]]
            for k in np.nonzero(dst.closed & np.all((lo <= p) & (p <= hi), 1))[0]:
                pair = (int(k), isl) if flip else (isl, int(k))
                if pair in crossing_islands:
                    continue
                inside = _inside(backend, cache, (flip, int(k)), dst, dp, int(k), p)
                if inside is False:
                    continue
                name_src = str(src.names[src.island == isl][0])
                name_dst = str(dst.names[dst.island == k][0])
                key = (name_dst, name_src) if flip else (name_src, name_dst)
                tuck = (not flip) and bool(allowed) and name_dst.startswith(tuple(allowed))
                bucket = (contained_allowed if tuck else contained) if inside else ambiguous
                bucket[key] = bucket.get(key, 0) + 1
    sep = (exact_separation(pa, set_a.tris, pb, set_b.tris, limit) if limit > 0 else
           {"separation_m": None, "at": None, "kind": "not measured", "pairs_measured": 0})
    return {
        "crossing_pairs_visible": int(sum(visible.values())),
        "crossing_pairs_hidden": int(sum(hidden.values())), "crossing_pairs_allowed": int(sum(allowed_n.values())),
        "coplanar_overlap_pairs": len(coplanar), "touching_pairs": int(touching),
        "crossing_parts_visible": _top(visible), "crossing_parts_hidden": _top(hidden),
        "crossing_parts_allowed": _top(allowed_n),
        "first_visible_crossing": None if first_visible is None else [round(float(v), 2) for v in to_report(first_visible)],
        "contained": int(sum(contained.values())), "contained_parts": _top(contained),
        "contained_allowed": int(sum(contained_allowed.values())), "contained_allowed_parts": _top(contained_allowed),
        "ambiguous": int(sum(ambiguous.values())), "ambiguous_parts": _top(ambiguous),
        "islands": [len(set_a.closed), len(set_b.closed)],
        "open_islands": [int((~set_a.closed).sum()), int((~set_b.closed).sum())],
        "separation_m": None if sep["separation_m"] is None else round(sep["separation_m"], 5),
        "separation_kind": sep["kind"], "separation_pairs_measured": sep["pairs_measured"],
        "separation_at": None if sep["at"] is None else [[round(float(v), 2) for v in to_report(q)] for q in sep["at"]],
        "separation_limit_m": limit,
    }


def passes(result, min_separation_m=0.0):
    """No visible crossing, nothing contained or ambiguous, and, when a minimum is asked, an exact separation of at
    least it. A separation beyond the limit certifies only the limit, so the minimum may not exceed it."""
    if min_separation_m > result["separation_limit_m"] + 1e-12:
        raise ValueError(f"min {min_separation_m} m above the measured limit {result['separation_limit_m']} m")
    sep = result["separation_m"]
    return (result["crossing_pairs_visible"] == 0 and result["contained"] == 0 and result["ambiguous"] == 0
            and (sep is None or sep >= min_separation_m))


# --- Calibration on known geometry ----------------------------------------------------------------------------------
def cube(centre, side):
    c, h = np.asarray(centre, np.float64), side / 2.0
    v = np.array([[x, y, z] for x in (-h, h) for y in (-h, h) for z in (-h, h)]) + c
    f = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6), (0, 2, 6),
         (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return v, np.array(f)


def tetra(centre, r):
    c = np.asarray(centre, np.float64)
    v = np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], np.float64) * r / math.sqrt(3) + c
    return v, np.array([(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)])


def rod(a, b, r, sides=8):
    """A closed prism of radius r from a to b."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    ax = (b - a) / np.linalg.norm(b - a)
    u = np.cross(ax, [0.0, 0.0, 1.0] if abs(ax[2]) < 0.9 else [1.0, 0.0, 0.0])
    u /= np.linalg.norm(u)
    w = np.cross(ax, u)
    ring = [r * (math.cos(math.tau * k / sides) * u + math.sin(math.tau * k / sides) * w) for k in range(sides)]
    v = np.array([a + q for q in ring] + [b + q for q in ring] + [a, b])
    f = []
    for k in range(sides):
        k1 = (k + 1) % sides
        f += [(k, k1, sides + k1), (k, sides + k1, sides + k), (2 * sides, k1, k), (2 * sides + 1, sides + k, sides + k1)]
    return v, np.array(f)


def diamond_bar(axis, half_length, s, lift):
    """A bar along X or Y, its square section turned 45 deg: an edge on top at z = lift + s, one below at lift - s."""
    sec = [(0.0, s), (s, 0.0), (0.0, -s), (-s, 0.0)]
    v = [(end, a, z + lift) if axis == "x" else (a, end, z + lift) for end in (-half_length, half_length) for a, z in sec]
    f = [q for k in range(4) for q in ((k, (k + 1) % 4, 4 + (k + 1) % 4), (k, 4 + (k + 1) % 4, 4 + k))]
    return np.array(v, np.float64), np.array(f + [(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6)])


def _set(mesh, name):
    v, f = mesh
    return TriSet(f, [name] * len(f)), v


def calibrate(backend):
    """The backend on known geometry, with each case's expected value."""
    out = {}
    tri_a = (np.array([[-0.01, -0.01, 0.0], [0.01, -0.01, 0.0], [0.0, 0.01, 0.0]]), np.array([(0, 1, 2)]))
    tri_b = (np.array([[0.0, 0.0, -0.01], [0.005, 0.0, 0.01], [-0.005, 0.0, 0.01]]), np.array([(0, 1, 2)]))
    r = measure(backend, *_set(tri_a, "a"), *_set(tri_b, "b"))
    out["crossing_pair"] = {"crossings": r["crossing_pairs_visible"], "expect": 1}
    r = measure(backend, *_set(tetra((0.0, 0.0, 0.0), 0.005), "tetra"), *_set(cube((0.0, 0.0, 0.0), 0.04), "cube"))
    out["tetra_inside_cube"] = {"crossings": r["crossing_pairs_visible"], "contained": r["contained"],
                                "expect": {"crossings": 0, "contained": 1}}
    r = measure(backend, *_set(cube((0.0, 0.0, 0.0), 0.04), "a"), *_set(cube((0.06, 0.0, 0.0), 0.04), "b"))
    out["cubes_2cm_apart"] = {"crossings": r["crossing_pairs_visible"], "contained": r["contained"],
                              "separation_m": r["separation_m"], "expect": {"separation_m": 0.02}}
    gap, s = 0.005, 0.01
    r = measure(backend, *_set(diamond_bar("x", 0.2, s, 0.0), "a"), *_set(diamond_bar("y", 0.2, s, 2 * s + gap), "b"),
                limit=0.05)
    va, vb = diamond_bar("x", 0.2, s, 0.0)[0], diamond_bar("y", 0.2, s, 2 * s + gap)[0]
    out["edges_5mm_apart"] = {"separation_m": r["separation_m"], "kind": r["separation_kind"],
                              "nearest_vertex_pair_m": round(float(np.linalg.norm(va[:, None] - vb[None], axis=2).min()), 4),
                              "expect": {"separation_m": gap, "kind": "edge-edge"}}
    hide = _set(cube((0.0, 0.0, 0.0), 0.05), "hide")
    r = measure(backend, *_set(rod((-0.05, 0.0, 0.0), (0.05, 0.0, 0.0), 0.004), "rod"),
                *_set(cube((0.0, 0.0, 0.0), 0.03), "box"), hide=(hide[0], hide[1]))
    out["rod_through_box_inside_hide"] = {"visible": r["crossing_pairs_visible"], "hidden": r["crossing_pairs_hidden"],
                                          "expect": {"visible": 0, "hidden": "> 0"}}
    blade = (np.array([[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [0.0, 1.0, 0.0]]), np.array([(0, 1, 2)]))
    long_body = (np.array([[0.0, -0.8, -1.0], [0.0, -0.8, 1.0], [0.0, 0.8, 0.0]]), np.array([(0, 1, 2)]))
    seg = crossing_segment(blade[0], long_body[0])
    small_hide = _set(cube((seg[0] + seg[1]) / 2.0, 0.10), "obi")
    r = measure(backend, *_set(blade, "blade"), *_set(long_body, "body"), limit=0.0, hide=small_hide)
    out["partial_hide_probe"] = {"visible": r["crossing_pairs_visible"], "hidden": r["crossing_pairs_hidden"],
                                 "passes": passes(r), "expect": {"visible": 1, "passes": False}}
    flat = (np.array([[-0.3, -0.3, 0.0], [0.5, -0.3, 0.0], [0.1, 0.5, 0.0]]), np.array([(0, 1, 2)]))
    r = measure(backend, *_set(blade, "blade"), *_set(flat, "body"), limit=0.1)
    out["coplanar_overlap_probe"] = {"visible": r["crossing_pairs_visible"], "coplanar": r["coplanar_overlap_pairs"],
                                     "backend_reported": r["crossing_pairs_visible"] - r["coplanar_overlap_pairs"],
                                     "passes": passes(r), "expect": {"visible": 1, "passes": False}}
    out["ok"] = (out["partial_hide_probe"]["visible"] == 1 and not out["partial_hide_probe"]["passes"]
                 and out["coplanar_overlap_probe"]["visible"] == 1 and not out["coplanar_overlap_probe"]["passes"]
                 and out["crossing_pair"]["crossings"] == 1
                 and out["tetra_inside_cube"]["crossings"] == 0 and out["tetra_inside_cube"]["contained"] == 1
                 and out["cubes_2cm_apart"]["crossings"] == 0 and out["cubes_2cm_apart"]["contained"] == 0
                 and abs((out["cubes_2cm_apart"]["separation_m"] or 0.0) - 0.02) < 1e-5
                 and abs((out["edges_5mm_apart"]["separation_m"] or 0.0) - gap) < 1e-6
                 and out["edges_5mm_apart"]["kind"] == "edge-edge"
                 and out["rod_through_box_inside_hide"]["visible"] == 0
                 and out["rod_through_box_inside_hide"]["hidden"] > 0)
    out["backend"] = backend.name
    return out
