"""Host tests: nyaakoto_tp_paw_surface, the paws' cut and UV prototypes.

Run: /usr/bin/python3 -m unittest scripts/art/test_paw_surface.py   (numpy and scipy)

- **The pads' field:** the smooth minimum and maximum bound the plain ones, and meet them far from a tie.
- **The cut** (cut_by_field, cut_exact):
  - an octahedron stays a closed, oriented manifold with its Euler characteristic;
  - new vertices lie on their edges at the field's roots;
  - each face's inside flag matches the field at its centroid;
  - move=False leaves every old vertex where it was.
- **The unwrap:** LSCM and ARAP are exact, up to a similarity, on a developable surface (a cylinder cut open), which is
  what the module's notes rely on.
- **untangle** unfolds a folded neighbourhood.
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import measure_paw_surface_prototypes as MS  # noqa: E402
import nyaakoto_tp_paw_surface as S  # noqa: E402

OCTA_V = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)
OCTA_T = np.array([[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4], [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]])


def cylinder_strip(radius=0.03, sweep=1.5 * math.pi, height=0.04, nu=24, nv=6):
    """A cylinder cut open along a line (a disk), its rings' quads split into triangles: developable."""
    a = np.linspace(0.0, sweep, nu + 1)
    z = np.linspace(0.0, height, nv + 1)
    V = np.array([[radius * math.cos(t), radius * math.sin(t), h] for h in z for t in a])
    T = []
    for j in range(nv):
        for i in range(nu):
            p, q = j * (nu + 1) + i, (j + 1) * (nu + 1) + i
            T += [[p, p + 1, q + 1], [p, q + 1, q]]
    return V, np.array(T)


def edge_ratio(V, T, uv):
    e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]])
    l3 = np.linalg.norm(V[e[:, 0]] - V[e[:, 1]], axis=1)
    l2 = np.linalg.norm(uv[e[:, 0]] - uv[e[:, 1]], axis=1)
    return l2 / l3


class Field(unittest.TestCase):
    def test_smooth_min_and_max_bound_the_plain_ones(self):
        a, b = np.array([0.0, 0.001, -0.002, 0.01]), np.array([0.0, -0.001, 0.003, -0.01])
        self.assertTrue((S.smin(a, b) <= np.minimum(a, b) + 1e-15).all())
        self.assertTrue((S.smax(a, b) >= np.maximum(a, b) - 1e-15).all())
        self.assertAlmostEqual(float(S.smin(np.array([0.05]), np.array([-0.05]))[0]), -0.05, places=12)
        self.assertAlmostEqual(float(S.smax(np.array([0.05]), np.array([-0.05]))[0]), 0.05, places=12)


class Cut(unittest.TestCase):
    def setUp(self):
        self.f = OCTA_V[:, 2] - 0.3 + 0.2 * OCTA_V[:, 0]

    def test_the_cut_keeps_a_closed_oriented_manifold(self):
        v2, t2, inside, parents, ts, f2 = S.cut_by_field(OCTA_V, OCTA_T, self.f, snap=0.0)
        topo = MS.topology(t2, len(v2))
        self.assertEqual(topo["edges_not_shared_by_two"], 0)
        self.assertTrue(topo["every_edge_has_its_opposite"])
        self.assertEqual(topo["euler"], MS.topology(OCTA_T, len(OCTA_V))["euler"])
        # New vertices at the linear root on their edge; each face's flag is the field's sign at its centroid.
        lin = self.f[parents[:, 0]] * (1 - ts) + self.f[parents[:, 1]] * ts
        np.testing.assert_allclose(lin, 0.0, atol=1e-12)
        fv = np.concatenate([self.f, np.zeros(len(v2) - len(OCTA_V))])
        bary = fv[t2].mean(1)
        self.assertTrue(((bary > 0) == inside).all())

    def test_exact_roots_without_moving_a_vertex(self):
        field = lambda q: q[:, 2] - 0.3 + 0.2 * q[:, 0]  # noqa: E731  (linear: its root is the interpolation's)
        v2, t2, inside, parents, ts, f2, moved = S.cut_exact(OCTA_V, OCTA_T, field, snap=0.0, move=False)
        np.testing.assert_array_equal(v2[:len(OCTA_V)], OCTA_V)
        np.testing.assert_allclose(field(v2[len(OCTA_V):]), 0.0, atol=1e-10)
        self.assertEqual(moved, {})

    def test_a_snapped_crossing_runs_through_the_vertex_and_leaves_it(self):
        field = lambda q: q[:, 2] - 0.95  # noqa: E731  (crosses the edges into the top vertex near their end)
        v2, t2, inside, parents, ts, f2, moved = S.cut_exact(OCTA_V, OCTA_T, field, move=False)
        np.testing.assert_array_equal(v2[:len(OCTA_V)], OCTA_V)
        self.assertIn(4, moved)                         # the top vertex: the contour goes through it
        self.assertEqual(len(v2), len(OCTA_V))          # so no new vertex is needed


class Unwrap(unittest.TestCase):
    def test_lscm_and_arap_are_exact_on_a_cut_cylinder(self):
        V, T = cylinder_strip()
        far = int(np.argmax(np.linalg.norm(V - V[0], axis=1)))
        uv = S.lscm(V, T, (0, far))
        r = edge_ratio(V, T, uv)
        self.assertLess(float(r.max() / r.min() - 1.0), 1e-6)      # conformal and developable: one scale
        uv = S.arap(V, T, uv * float(1.0 / np.median(r)), 10)
        r = edge_ratio(V, T, uv)
        np.testing.assert_allclose(r, 1.0, atol=1e-6)               # rigid

    def test_untangle_unfolds_a_folded_neighbourhood(self):
        n = 6
        g = np.array([[i, j, 0.0] for j in range(n) for i in range(n)], float) * 0.01
        T = np.array([[j * n + i, j * n + i + 1, (j + 1) * n + i + 1] for j in range(n - 1) for i in range(n - 1)]
                     + [[j * n + i, (j + 1) * n + i + 1, (j + 1) * n + i] for j in range(n - 1) for i in range(n - 1)])
        uv = g[:, :2].copy()
        uv[2 * n + 2] += [0.025, 0.018]                             # an interior vertex pushed past its neighbours
        corner = uv[T]
        out, rec = S.untangle(g, T, corner)
        self.assertGreater(len(rec["folded_before"]), 0)
        self.assertEqual(rec["folded_after"], [])
        d = (out[:, 1, 0] - out[:, 0, 0]) * (out[:, 2, 1] - out[:, 0, 1]) - (out[:, 2, 0] - out[:, 0, 0]) * (out[:, 1, 1] - out[:, 0, 1])
        self.assertTrue((d > 0).all())


if __name__ == "__main__":
    unittest.main()
