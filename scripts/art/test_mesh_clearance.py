"""CPU tests of mesh_clearance with its every-pair numpy backend.

  python3 scripts/art/test_mesh_clearance.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mesh_clearance as MC  # noqa: E402

B = MC.BruteBackend()


def tset(mesh, name):
    v, f = mesh
    return MC.TriSet(f, [name] * len(f)), v


def join(*meshes):
    vs, fs, n = [], [], 0
    for v, f in meshes:
        vs.append(v)
        fs.append(np.asarray(f) + n)
        n += len(v)
    return np.concatenate(vs), np.concatenate(fs)


def vertex_to_surface(pa, fa, pb, fb):
    """The least vertex-to-surface distance, both ways: the measure the exact separation replaces."""
    return min(min(float(np.linalg.norm(p - MC.point_triangle(p, *q[f]))) for f in g) for p, q, g in
               [(p, pb, fb) for p in pa] + [(p, pa, fa) for p in pb])


class Topology(unittest.TestCase):
    def test_islands_and_closed(self):
        v, f = join(MC.cube((0, 0, 0), 0.02), MC.cube((0.1, 0, 0), 0.02),
                    (np.array([[0, 0, 1.0], [0.01, 0, 1.0], [0, 0.01, 1.0]]), np.array([(0, 1, 2)])))
        isl = MC.islands(f)
        self.assertEqual(len(set(isl.tolist())), 3)
        closed = MC.closed_islands(f, isl)
        self.assertEqual(sorted(closed.tolist()), [False, True, True])
        self.assertFalse(closed[isl[-1]])                       # the lone triangle is open

    def test_triset_reindexes(self):
        v, f = MC.cube((0, 0, 0), 0.02)
        t = MC.TriSet(f[:6] + 100, ["x"] * 6)                    # indices into a larger array
        self.assertEqual(int(t.tris.max()), len(t.used) - 1)
        self.assertTrue(np.all(t.used >= 100))


class Geometry(unittest.TestCase):
    def test_point_triangle(self):
        a, b, c = np.array([0.0, 0, 0]), np.array([1.0, 0, 0]), np.array([0.0, 1, 0])
        for p, d in (((0.2, 0.2, 0.5), 0.5), ((-1.0, 0, 0), 1.0), ((1.0, 1.0, 0), 2 ** 0.5 / 2)):
            q = MC.point_triangle(np.array(p), a, b, c)
            self.assertAlmostEqual(float(np.linalg.norm(np.array(p) - q)), d, places=9)

    def test_vectorised_point_triangle_matches_scalar(self):
        rng = np.random.default_rng(3)
        p, a, b, c = (rng.normal(size=(400, 3)) for _ in range(4))
        v = MC.closest_point_triangle_v(p, a, b, c)
        s = np.array([MC.point_triangle(*q) for q in zip(p, a, b, c)])
        np.testing.assert_allclose(v, s, atol=1e-12)

    def test_vectorised_segments(self):
        """Closest points of segment pairs, against a dense search; and the degenerate (point) segments."""
        rng = np.random.default_rng(5)
        p1, q1, p2, q2 = (rng.normal(size=(60, 3)) for _ in range(4))
        c1, c2 = MC.closest_segments_v(p1, q1, p2, q2)
        d = np.linalg.norm(c1 - c2, axis=1)
        u = np.linspace(0.0, 1.0, 401)
        for k in range(60):
            a = p1[k] + np.outer(u, q1[k] - p1[k])
            b = p2[k] + np.outer(u, q2[k] - p2[k])
            dense = np.linalg.norm(a[:, None] - b[None], axis=2).min()
            self.assertLessEqual(d[k], dense + 1e-12)
            self.assertGreater(d[k], dense - 0.02)
        c1, c2 = MC.closest_segments_v(np.zeros((1, 3)), np.zeros((1, 3)), np.array([[1.0, -1, 0]]), np.array([[1.0, 1, 0]]))
        np.testing.assert_allclose(c2, [[1.0, 0.0, 0.0]])

    def test_triangle_distances_against_dense_sampling(self):
        """Exact distance never above a dense sample of both triangles, and close to it."""
        rng = np.random.default_rng(11)
        t1 = rng.normal(size=(40, 3, 3))
        t2 = rng.normal(size=(40, 3, 3)) + np.array([2.0, 0.0, 0.0])
        d, q1, q2, kind = MC.triangle_distances_v(t1, t2)
        g = np.array([(u, v) for u in np.linspace(0, 1, 41) for v in np.linspace(0, 1, 41) if u + v <= 1.0])
        for k in range(40):
            s1 = t1[k, 0] + g[:, :1] * (t1[k, 1] - t1[k, 0]) + g[:, 1:] * (t1[k, 2] - t1[k, 0])
            s2 = t2[k, 0] + g[:, :1] * (t2[k, 1] - t2[k, 0]) + g[:, 1:] * (t2[k, 2] - t2[k, 0])
            dense = np.linalg.norm(s1[:, None] - s2[None], axis=2).min()
            self.assertLessEqual(d[k], dense + 1e-12)
            self.assertGreater(d[k], dense - 0.1)
            self.assertAlmostEqual(float(np.linalg.norm(q1[k] - q2[k])), float(d[k]), places=9)

    def test_crossing_pair_distance_is_zero(self):
        """A small triangle piercing a large one: no vertex on a face and no edge meets an edge, yet distance 0."""
        big = np.array([[[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [0.0, 1.0, 0.0]]])
        small = np.array([[[0.0, -0.1, -0.1], [0.0, 0.1, -0.1], [0.0, 0.0, 0.1]]])
        d, _q1, _q2, kind = MC.triangle_distances_v(big, small)
        self.assertEqual(float(d[0]), 0.0)
        self.assertEqual(MC.KINDS[int(kind[0])], "crossing")

    def test_segment_triangle(self):
        a, b, c = np.array([0.0, 0, 0]), np.array([1.0, 0, 0]), np.array([0.0, 1, 0])
        x = MC.segment_triangle(np.array([0.2, 0.2, -1.0]), np.array([0.2, 0.2, 1.0]), a, b, c)
        np.testing.assert_allclose(x, [0.2, 0.2, 0.0])
        self.assertIsNone(MC.segment_triangle(np.array([0.2, 0.2, 0.5]), np.array([0.2, 0.2, 1.0]), a, b, c))


class Measure(unittest.TestCase):
    def test_calibration(self):
        cal = MC.calibrate(B)
        self.assertTrue(cal["ok"], cal)
        self.assertEqual(cal["crossing_pair"]["crossings"], 1)
        self.assertEqual(cal["tetra_inside_cube"]["contained"], 1)
        self.assertAlmostEqual(cal["cubes_2cm_apart"]["separation_m"], 0.02, places=6)
        self.assertAlmostEqual(cal["edges_5mm_apart"]["separation_m"], 0.005, places=6)
        self.assertEqual(cal["edges_5mm_apart"]["kind"], "edge-edge")
        self.assertGreater(cal["edges_5mm_apart"]["nearest_vertex_pair_m"], 0.19)
        self.assertEqual(cal["partial_hide_probe"]["visible"], 1)
        self.assertFalse(cal["coplanar_overlap_probe"]["passes"])

    def test_crossing_with_every_vertex_far(self):
        """Two thin crossing slabs: no vertex within 2 cm of the other's vertices, yet their faces cross."""
        a = (np.array([[-0.1, -0.1, 0.0], [0.1, -0.1, 0.0], [0.0, 0.1, 0.0]]), np.array([(0, 1, 2)]))
        b = (np.array([[0.0, -0.05, -0.1], [0.0, 0.05, 0.1], [0.0, -0.05, 0.1]]), np.array([(0, 1, 2)]))
        vv = np.linalg.norm(a[0][:, None] - b[0][None], axis=2).min()
        self.assertGreater(vv, 0.02)
        r = MC.measure(B, *tset(a, "a"), *tset(b, "b"))
        self.assertEqual(r["crossing_pairs_visible"], 1)
        self.assertEqual(r["separation_m"], 0.0)
        self.assertEqual(r["separation_kind"], "crossing")
        self.assertFalse(MC.passes(r))

    def test_exact_separation_edge_over_edge(self):
        """Edge over edge, 5 mm apart: the exact separation finds it; the vertex-to-surface measure would report
        over 10 cm, so it could have passed a 3 cm minimum that the bars fail."""
        gap, s = 0.005, 0.01
        a = MC.diamond_bar("x", 0.2, s, 0.0)
        b = MC.diamond_bar("y", 0.2, s, 2 * s + gap)
        r = MC.measure(B, *tset(a, "a"), *tset(b, "b"), limit=0.05)
        self.assertEqual(r["crossing_pairs_visible"], 0)
        self.assertAlmostEqual(r["separation_m"], gap, places=6)
        self.assertEqual(r["separation_kind"], "edge-edge")
        self.assertGreater(vertex_to_surface(*a, *b), 0.10)
        self.assertFalse(MC.passes(r, min_separation_m=0.03))
        self.assertTrue(MC.passes(r, min_separation_m=0.004))

    def test_minimum_above_limit_refused(self):
        r = MC.measure(B, *tset(MC.cube((0, 0, 0), 0.04), "a"), *tset(MC.cube((0.2, 0, 0), 0.04), "b"), limit=0.03)
        self.assertIsNone(r["separation_m"])                    # nothing within 3 cm
        self.assertTrue(MC.passes(r, min_separation_m=0.03))
        with self.assertRaises(ValueError):
            MC.passes(r, min_separation_m=0.05)                  # 5 cm was never measured

    def test_open_island_is_counted_not_tested(self):
        v, f = MC.cube((0, 0, 0), 0.04)
        open_box = (v, f[2:])                                    # one face removed
        r = MC.measure(B, *tset(MC.tetra((0, 0, 0), 0.005), "tetra"), *tset(open_box, "box"))
        self.assertEqual(r["contained"], 0)
        self.assertEqual(r["open_islands"], [0, 1])

    def test_hidden_and_visible_crossings(self):
        """A rod through a box: the crossing at one face lies inside the hide volume, the other's outside it."""
        rod = MC.rod((-0.05, 0.0, 0.0), (0.05, 0.0, 0.0), 0.004)
        box = MC.cube((0.0, 0.0, 0.0), 0.03)                     # faces at x = -0.015 and +0.015
        hide = tset(MC.cube((0.02, 0.0, 0.0), 0.02), "obi")      # holds x 0.01 to 0.03: the +0.015 face only
        r = MC.measure(B, *tset(rod, "saya"), *tset(box, "haori"), hide=hide)
        self.assertGreater(r["crossing_pairs_hidden"], 0)
        self.assertGreater(r["crossing_pairs_visible"], 0)
        self.assertEqual(r["crossing_parts_visible"][0][:2], ["saya", "haori"])
        self.assertLess(r["first_visible_crossing"][0], 0.0)    # the visible one is at the -X face
        self.assertFalse(MC.passes(r))

    def test_allowed_tuck(self):
        """A saya through the obi: its crossings with the obi itself are the intended tuck, not visible clipping."""
        rod = MC.rod((-0.05, 0.0, 0.0), (0.05, 0.0, 0.0), 0.004)
        r = MC.measure(B, *tset(rod, "saya"), *tset(MC.cube((0.0, 0.0, 0.0), 0.03), "Obi_waist"), allowed=("Obi_",))
        self.assertGreater(r["crossing_pairs_allowed"], 0)
        self.assertEqual(r["crossing_pairs_visible"], 0)
        self.assertTrue(MC.passes(r))
        # A fitting sealed inside the obi is the tuck too; the same fitting inside anything else is contained.
        fitting = MC.tetra((0.0, 0.0, 0.0), 0.003)
        r = MC.measure(B, *tset(fitting, "kurikata"), *tset(MC.cube((0.0, 0.0, 0.0), 0.03), "Obi_waist"), allowed=("Obi_",))
        self.assertEqual((r["contained"], r["contained_allowed"]), (0, 1))
        r = MC.measure(B, *tset(fitting, "kurikata"), *tset(MC.cube((0.0, 0.0, 0.0), 0.03), "Do_lamellar"), allowed=("Obi_",))
        self.assertEqual((r["contained"], r["contained_allowed"]), (1, 0))

    def test_root_probe_partial_hide(self):
        """Root's probe (2026-10-26): a 1.6 m crossing with only its midpoint in a 10 cm hide cube is visible."""
        a = (np.array([(-1, -1, 0), (1, -1, 0), (0, 1, 0)], float), np.array([(0, 1, 2)]))
        b = (np.array([(0, -.8, -1), (0, -.8, 1), (0, .8, 0)], float), np.array([(0, 1, 2)]))
        seg = MC.crossing_segment(a[0], b[0])
        self.assertAlmostEqual(float(np.linalg.norm(seg[1] - seg[0])), 1.6, places=9)
        hp, hf = MC.cube((seg[0] + seg[1]) / 2.0, .10)
        r = MC.measure(B, *tset(a, "blade"), *tset(b, "body"), limit=0, hide=(MC.TriSet(hf, ["obi"] * len(hf)), hp))
        self.assertEqual((r["crossing_pairs_visible"], r["crossing_pairs_hidden"]), (1, 0))
        self.assertFalse(MC.passes(r))

    def test_root_probe_coplanar_overlap(self):
        """Root's probe: coplanar triangles overlapping with positive area are a crossing, not a pass."""
        a = (np.array([(-1, -1, 0), (1, -1, 0), (0, 1, 0)], float), np.array([(0, 1, 2)]))
        c = (np.array([(-.3, -.3, 0), (.5, -.3, 0), (.1, .5, 0)], float), np.array([(0, 1, 2)]))
        r = MC.measure(B, *tset(a, "blade"), *tset(c, "body"), limit=.1)
        self.assertEqual(r["crossing_pairs_visible"], 1)
        self.assertEqual(r["separation_m"], 0.0)
        self.assertFalse(MC.passes(r))

    def test_coplanar_detected_without_the_backend(self):
        """A backend blind to coplanar pairs (as isect_tri_tri may be) is caught by measure's own test."""
        class Blind(MC.BruteBackend):
            def crossings(self, ta, tb):
                return [ij for ij in super().crossings(ta, tb)
                        if MC.tri_tri_points(ta[0][ta[1][ij[0]]], tb[0][tb[1][ij[1]]])]
        a = (np.array([(-1, -1, 0), (1, -1, 0), (0, 1, 0)], float), np.array([(0, 1, 2)]))
        c = (np.array([(-.3, -.3, 0), (.5, -.3, 0), (.1, .5, 0)], float), np.array([(0, 1, 2)]))
        r = MC.measure(Blind(), *tset(a, "blade"), *tset(c, "body"), limit=.1)
        self.assertEqual((r["coplanar_overlap_pairs"], r["crossing_pairs_visible"]), (1, 1))
        self.assertFalse(MC.passes(r))

    def test_touching_edge_is_not_a_crossing(self):
        """Two coplanar triangles sharing only an edge touch with zero area: touching, not crossing."""
        a = (np.array([(0, 0, 0), (1, 0, 0), (0, 1, 0)], float), np.array([(0, 1, 2)]))
        b = (np.array([(1, 0, 0), (0, 1, 0), (1, 1, 0)], float), np.array([(0, 1, 2)]))
        r = MC.measure(B, *tset(a, "a"), *tset(b, "b"), limit=.1)
        self.assertEqual((r["crossing_pairs_visible"], r["touching_pairs"]), (0, 1))

    def test_nonconvex_hide_needs_the_whole_segment(self):
        """An L-shaped hide volume holds both ends of a crossing whose middle runs through its notch: visible."""
        s, h = 0.05, 0.01
        poly = [(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)]
        v = np.array([(x * s, y * s, z) for z in (-h, h) for x, y in poly], float)
        f = [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 5)] + [(6, 8, 7), (6, 9, 8), (6, 10, 9), (6, 11, 10)]
        f += [q for k in range(6) for q in ((k, (k + 1) % 6, 6 + (k + 1) % 6), (k, 6 + (k + 1) % 6, 6 + k))]
        hide = MC.TriSet(np.array(f), ["obi"] * len(f))
        self.assertTrue(hide.closed.all())
        P, Q = np.array([1.8 * s, 0.5 * s, 0.0]), np.array([0.5 * s, 1.8 * s, 0.0])
        a = (np.array([(-s, -s, 0), (5 * s, -s, 0), (-s, 5 * s, 0)], float), np.array([(0, 1, 2)]))
        d = Q - P
        b = (np.array([P - 0.25 * d + (0, 0, -h / 2), Q + 0.25 * d + (0, 0, -h / 2), (P + Q) / 2 + (0, 0, h)], float),
             np.array([(0, 1, 2)]))
        seg = MC.crossing_segment(a[0], b[0])
        in_l = lambda q: (0 < q[0] < 2 * s and 0 < q[1] < s) or (0 < q[0] < s and 0 < q[1] < 2 * s)
        self.assertTrue(in_l(seg[0]) and in_l(seg[1]))          # both ends inside the L
        self.assertFalse(in_l((seg[0] + seg[1]) / 2.0))          # its middle in the notch
        r = MC.measure(B, *tset(a, "saya"), *tset(b, "haori"), limit=0, hide=(hide, v))
        self.assertEqual((r["crossing_pairs_visible"], r["crossing_pairs_hidden"]), (1, 0))

    def test_reverse_containment(self):
        """The second set's island inside the first's closed island is found too."""
        r = MC.measure(B, *tset(MC.cube((0, 0, 0), 0.04), "cube"), *tset(MC.tetra((0, 0, 0), 0.005), "tetra"))
        self.assertEqual(r["contained"], 1)
        self.assertEqual(r["contained_parts"][0][:2], ["cube", "tetra"])


class BroadPhase(unittest.TestCase):
    """The grid broad-phase finds the pairwise bounds test's own pairs, and the separation it bounds is the pairwise
    loop's (s103 found that loop |a| x |b|: minutes a check with the furred paws)."""

    @staticmethod
    def soup(rng, n, centre, size, big=0):
        c = np.asarray(centre) + rng.normal(0, 0.05, (n, 3))
        tri = c[:, None, :] + rng.normal(0, size, (n, 3, 3))
        if big:
            k = rng.choice(n, big, replace=False)
            tri[k] = c[k, None, :] + rng.normal(0, size * 40, (big, 3, 3))
        return tri.reshape(-1, 3), np.arange(3 * n).reshape(-1, 3)

    @staticmethod
    def pairwise(alo, ahi, blo, bhi, grow):
        ok = np.all((alo[:, None] - grow <= bhi[None]) & (ahi[:, None] + grow >= blo[None]), 2)
        return np.argwhere(ok)

    def test_bbox_pairs_is_the_pairwise_set(self):
        rng = np.random.default_rng(7)
        for trial in range(20):
            pa, ta = self.soup(rng, int(rng.integers(1, 400)), (0, 0, 0), 0.004, big=int(rng.integers(0, 3)))
            pb, tb = self.soup(rng, int(rng.integers(1, 400)), (0.02, 0, 0), 0.004, big=int(rng.integers(0, 3)))
            A, Bt = pa[ta], pb[tb]
            for grow in (0.0, 1e-7, 0.003, 0.02):
                want = self.pairwise(A.min(1), A.max(1), Bt.min(1), Bt.max(1), grow)
                got = MC.bbox_pairs(A.min(1), A.max(1), Bt.min(1), Bt.max(1), grow)
                with self.subTest(trial=trial, grow=grow):
                    self.assertTrue(np.array_equal(got, want))

    def test_bbox_pairs_with_a_coarse_and_a_fine_set(self):
        """s117's case: a coarse set with long triangles (the katana) against a fine, dense one (the furred paws), so
        the cell is the fine set's and many triangles are large. A rows subset, and a large triangle reaching more
        cells than the other set has members (the guard), give the pairwise set too."""
        rng = np.random.default_rng(17)
        for trial in range(12):
            pa, ta = self.soup(rng, int(rng.integers(50, 500)), (0, 0, 0), 0.006, big=int(rng.integers(5, 40)))
            pb, tb = self.soup(rng, int(rng.integers(50, 900)), (0.01, 0, 0), 0.0012, big=int(rng.integers(0, 3)))
            if trial % 3 == 0:                                       # one triangle across the whole scene
                pa[:3] = [(-0.4, -0.3, -0.2), (0.4, 0.3, 0.25), (0.3, -0.35, 0.3)]
            A, Bt = pa[ta], pb[tb]
            rows = np.sort(rng.choice(len(A), max(1, len(A) // 2), replace=False))
            for grow in (0.0, 1e-7, 0.002, 0.03):
                want = self.pairwise(A.min(1), A.max(1), Bt.min(1), Bt.max(1), grow)
                for swap in (False, True):
                    if swap:
                        w = self.pairwise(Bt.min(1), Bt.max(1), A.min(1), A.max(1), grow)
                        got = MC.bbox_pairs(Bt.min(1), Bt.max(1), A.min(1), A.max(1), grow)
                    else:
                        w = want
                        got = MC.bbox_pairs(A.min(1), A.max(1), Bt.min(1), Bt.max(1), grow)
                    with self.subTest(trial=trial, grow=grow, swap=swap):
                        self.assertTrue(np.array_equal(got, w))
                sub = MC.bbox_pairs(A.min(1), A.max(1), Bt.min(1), Bt.max(1), grow, rows=rows)
                with self.subTest(trial=trial, grow=grow, rows=True):
                    self.assertTrue(np.array_equal(sub, want[np.isin(want[:, 0], rows)]))

    def test_nearest_vertex_gap_is_the_least_vertex_distance(self):
        rng = np.random.default_rng(8)
        for trial in range(10):
            va, vb = rng.normal(0, 0.05, (300, 3)), rng.normal(0.03, 0.05, (200, 3))
            d = float(np.linalg.norm(va[:, None] - vb[None], axis=2).min())
            for limit in (0.001, 0.01, 0.1):
                with self.subTest(trial=trial, limit=limit):
                    self.assertAlmostEqual(MC.nearest_vertex_gap(va, vb, limit), min(d, limit), places=12)

    def test_separation_is_the_pairwise_loops(self):
        rng = np.random.default_rng(9)
        for trial in range(12):
            pa, ta = self.soup(rng, int(rng.integers(20, 300)), (0, 0, 0), 0.003, big=int(rng.integers(0, 2)))
            pb, tb = self.soup(rng, int(rng.integers(20, 300)), (0.12 * rng.random(), 0, 0), 0.003)
            for limit in (0.005, 0.02, 0.1):
                got = MC.exact_separation(pa, ta, pb, tb, limit)
                # the pairwise reference: every pair whose bounds come within the limit, measured
                A, Bt = pa[ta], pb[tb]
                q = self.pairwise(A.min(1), A.max(1), Bt.min(1), Bt.max(1), limit)
                with self.subTest(trial=trial, limit=limit):
                    if not len(q):
                        self.assertIsNone(got["separation_m"])
                        continue
                    d, q1, q2, kind = MC.triangle_distances_v(A[q[:, 0]], Bt[q[:, 1]])
                    k = int(np.argmin(d))
                    if d[k] < limit:
                        self.assertEqual(got["separation_m"], float(d[k]))
                        self.assertTrue(np.array_equal(got["at"][0], q1[k]) and np.array_equal(got["at"][1], q2[k]))
                        self.assertEqual(got["kind"], MC.KINDS[int(kind[k])])
                    else:
                        self.assertIsNone(got["separation_m"])


class TreeCache(unittest.TestCase):
    def test_a_pose_reuses_its_trees_and_a_new_array_builds_afresh(self):
        class Counting(MC.BruteBackend):
            built = 0

            def tree(self, pts, tris):
                Counting.built += 1
                return super().tree(pts, tris)

        bk = Counting()
        va, fa = MC.cube((0.0, 0.0, 0.0), 0.1)
        vb, fb = MC.cube((0.2, 0.0, 0.0), 0.1)
        pts = np.concatenate([va, vb])
        sa, sb = MC.TriSet(fa, ["a"] * len(fa)), MC.TriSet(fb + len(va), ["b"] * len(fb))
        r1 = MC.measure(bk, sa, pts, sb, pts, limit=0.2)
        n1 = Counting.built
        r2 = MC.measure(bk, sa, pts, sb, pts, limit=0.2)
        self.assertEqual(Counting.built, n1)                 # the same array: no new tree
        self.assertEqual(r1, r2)
        moved = pts.copy()
        moved[len(va):, 0] -= 0.05
        r3 = MC.measure(bk, sa, moved, sb, moved, limit=0.2)
        self.assertGreater(Counting.built, n1)               # a new array: built afresh
        self.assertAlmostEqual(r3["separation_m"], 0.05, places=9)


if __name__ == "__main__":
    unittest.main()
