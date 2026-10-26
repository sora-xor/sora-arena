"""Tests for Nyaakoto's third-person paws (nyaakoto_tp_paws).

Run: python3 -m unittest scripts/art/test_nyaakoto_tp_paws.py

The arms are the hero source's own, unvaried: the palm's centre and radii from create_nyaagyu_hero_character.py, the
channel placed as nyaakoto_runtime_parts.arm_joints places it. Each paw is meshed at the three LOD steps.

- **Channel coordinates:** they round-trip; Newton finds the nearest point of the oval.
- **The closure:** it is 1 at the knuckles and closure_end at the end of its ramp: EMPTY_CHANNEL + ARC_OPEN over the
  middle toes, EMPTY_CHANNEL from ARC_S[1] outward. Its slope is its derivative. The closed oval never turns back on
  itself, and fold_margin catches a ramp too steep.
- **The mesher:** manifold_surface_nets closes a face whose corners alternate, with its centre in or out (a pipe).
  Naive surface nets does not. On a ball it gives naive surface nets' own mesh.
- **self_crossings:** it finds a crossing pair and a cap pushed through a ball, and passes a closed ball.
- **Every paw, both states:** each is a closed, outward 2-manifold without self-crossings. No facet comes within
  half a millimetre of the channel, and the breadth stays within the contract.
- **The empty fist:** the palm and the knuckles stay put. Each digit vertex moves exactly by its oval point's shift,
  no face turns over, and every LOD closes to the same fist. The middle toes stand proud of the outer toes (the arc).
- **The coat, UVs and fuzz** are in range: white on the toes, tabby on the back of the paw, the body's density,
  and no seam across a face.
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nyaakoto_fp_paws as FP  # noqa: E402
import nyaakoto_tp_paws as P  # noqa: E402
import third_person_rig as TP  # noqa: E402

PALM_CENTRE = (0.091, 0.474, 0.84)          # create_nyaagyu_hero_character.py: Paw_hand_{sign}
PALM_RADII = (0.069, 0.078, 0.090)
CHANNEL_DIR = np.array([0.589, 0.0, -0.808]) / np.linalg.norm([0.589, 0.0, -0.808])
CHANNEL_EMBED = -0.0005                      # nyaakoto_runtime_parts.CHANNEL_EMBED


def hero_arm(sign, offset=(0.0, 0.0, 0.0)):
    """nyaakoto_runtime_parts.arm_joints' palm, channel and socket rotation for one side, in numpy."""
    c = np.array([PALM_CENTRE[0], sign * PALM_CENTRE[1], PALM_CENTRE[2]]) + np.asarray(offset)
    surface = 1.0 / math.sqrt((CHANNEL_DIR[0] / PALM_RADII[0]) ** 2 + (CHANNEL_DIR[2] / PALM_RADII[2]) ** 2)
    channel = c + CHANNEL_DIR * (surface + P.CHANNEL_HALF[1] - CHANNEL_EMBED)
    rot = TP.frame(np.array([0.0, -float(sign), 0.0]), (c - channel) / np.linalg.norm(c - channel))
    return {"sign": sign, "palm": c, "channel": channel, "socket_rot": rot}


def nearest_distances(points, cloud, chunk=2000):
    out = np.empty(len(points))
    for k in range(0, len(points), chunk):
        d = np.linalg.norm(points[k:k + chunk, None] - cloud[None], axis=2)
        out[k:k + chunk] = d.min(1)
    return out


def signed_volume(V, T):
    return float(np.einsum("ij,ij->i", V[T[:, 0]], np.cross(V[T[:, 1]], V[T[:, 2]])).sum() / 6.0)


MESHES = {}


def paw(sign, lod):
    if (sign, lod) not in MESHES:
        m = P.mesh_paw(hero_arm(sign), PALM_RADII, step=P.LOD_STEPS[lod])
        m["empty"] = P.empty_points(m["verts"], m["skeleton"])
        MESHES[sign, lod] = m
    return MESHES[sign, lod]


class Channel(unittest.TestCase):
    def setUp(self):
        self.fr = P.frame_of(hero_arm(1))
        self.rng = np.random.default_rng(1)

    def test_coordinates_round_trip(self):
        s = self.rng.uniform(-0.05, 0.05, 500)
        t = self.rng.uniform(-math.pi, math.pi, 500)
        e = self.rng.uniform(0.0, 0.06, 500)
        s2, t2, e2 = P.channel_coords(P.from_channel(s, t, e, self.fr), self.fr)
        self.assertLess(np.abs(s2 - s).max(), 1e-12)
        self.assertLess(np.abs(np.angle(np.exp(1j * (t2 - t)))).max(), 1e-9)
        self.assertLess(np.abs(e2 - e).max(), 1e-12)

    def test_newton_finds_the_nearest_point_of_the_oval(self):
        fr = self.fr
        q = self.rng.uniform(-0.08, 0.08, (300, 2))
        q = q[(q[:, 0] / fr["a"]) ** 2 + (q[:, 1] / fr["b"]) ** 2 > 1.0]
        dense = np.linspace(-math.pi, math.pi, 200001)
        ou, ov = P.oval(dense, fr)
        brute = np.sqrt(((q[:, None, 0] - ou[None]) ** 2 + (q[:, None, 1] - ov[None]) ** 2).min(1))
        t = P.ellipse_param(q[:, 0], q[:, 1], fr["a"], fr["b"])
        pu, pv = P.oval(t, fr)
        self.assertLess(np.abs(np.hypot(q[:, 0] - pu, q[:, 1] - pv) - brute).max(), 1e-8)


class Closure(unittest.TestCase):
    def setUp(self):
        self.fr = P.frame_of(hero_arm(-1))

    def test_one_at_the_knuckles_and_the_target_at_the_ramps_end(self):
        for deg in (0.0, 20.0, P.CURL_RAMP[0], -P.CURL_RAMP[0]):
            self.assertEqual(float(P.closure(np.radians(deg))), 1.0)
            self.assertEqual(P.closed_shift(np.radians(deg), self.fr), (0.0, 0.0))
        for deg in (P.CURL_RAMP[1], -P.CURL_RAMP[1]):
            self.assertAlmostEqual(float(P.closure(np.radians(deg))), P.EMPTY_CHANNEL, places=12)
            for s, end in ((0.0, P.EMPTY_CHANNEL + P.ARC_OPEN), (P.ARC_S[0], P.EMPTY_CHANNEL + P.ARC_OPEN),
                           (-P.ARC_S[1], P.EMPTY_CHANNEL), (P.PAW_HALF, P.EMPTY_CHANNEL)):
                self.assertAlmostEqual(float(P.closure(np.radians(deg), s)), end, places=12)

    def test_the_arc_eases_between_the_middle_and_outer_toes(self):
        s = np.linspace(-P.PAW_HALF, P.PAW_HALF, 2001)
        end = P.closure_end(s)
        self.assertTrue(np.allclose(end, end[::-1]))
        half = s >= 0.0
        self.assertTrue((np.diff(end[half]) <= 1e-15).all())                      # never opens outward
        self.assertLess(float(np.abs(np.diff(end)).max()), 2.0 * P.ARC_OPEN * (s[1] - s[0]) / (P.ARC_S[1] - P.ARC_S[0]))

    def test_slope_is_the_derivative(self):
        t = np.radians(np.linspace(-179.0, 179.0, 359))
        h = 1e-6
        for s in (None, 0.0, 0.5 * (P.ARC_S[0] + P.ARC_S[1]), P.PAW_HALF):
            fd = (P.closure(t + h, s) - P.closure(t - h, s)) / (2 * h)
            with self.subTest(s=s):
                self.assertLess(np.abs(fd - P.closure_slope(t, s)).max(), 1e-6)

    def test_the_closed_oval_never_turns_back(self):
        for sign in (1, -1):
            self.assertGreater(P.fold_margin(P.frame_of(hero_arm(sign))), 0.05)

    def test_fold_margin_catches_a_ramp_too_steep(self):
        saved = P.CURL_RAMP
        try:
            P.CURL_RAMP = (40.0, 80.0)
            self.assertLess(P.fold_margin(self.fr), 0.0)
        finally:
            P.CURL_RAMP = saved


class Mesher(unittest.TestCase):
    @staticmethod
    def checkerboard(centre_inside):
        """Two grid points inside, diagonal on one face; the face's centre (the mean of its corners) in or out. In, it
        is a pipe of the surface through the face, on one patch in both cells."""
        grid = np.ones((5, 5, 4))
        grid[1, 1, 1] = grid[2, 2, 1] = -1.0 if centre_inside else -0.5
        if centre_inside:
            grid[2, 1, 1] = grid[1, 2, 1] = 0.2
        axes = tuple(np.arange(n) * 0.001 for n in grid.shape)
        return grid, axes

    def test_an_ambiguous_face_closes_either_way(self):
        for centre_inside in (False, True):
            with self.subTest(centre_inside=centre_inside):
                grid, axes = self.checkerboard(centre_inside)
                self.assertAlmostEqual(float(grid[1:3, 1:3, 1].mean() <= 0), float(centre_inside))
                V, Q = P.manifold_surface_nets(grid, axes)
                self.assertTrue(FP.is_closed_manifold(FP.triangulate(Q, V)))
                v0, q0 = FP.surface_nets(grid, axes)
                self.assertFalse(FP.is_closed_manifold(FP.triangulate(q0, v0)))   # the case the patches are for

    def test_a_ball_is_unchanged(self):
        field = lambda p: np.linalg.norm(p, axis=-1) - 0.01       # noqa: E731
        grid, axes = FP.sample_grid(field, np.full(3, -0.0151), np.full(3, 0.0153), 0.0017)
        V, Q = P.manifold_surface_nets(grid, axes)
        v0, q0 = FP.surface_nets(grid, axes)
        self.assertEqual(len(V), len(v0))
        self.assertTrue(np.allclose(np.sort(V, 0), np.sort(v0, 0)))
        self.assertEqual(len(Q), len(q0))


class SelfCrossings(unittest.TestCase):
    def ball(self):
        field = lambda p: np.linalg.norm(p, axis=-1) - 0.01       # noqa: E731
        grid, axes = FP.sample_grid(field, np.full(3, -0.015), np.full(3, 0.015), 0.002)
        V, Q = P.manifold_surface_nets(grid, axes)
        return V, FP.triangulate(Q, V)

    def test_a_closed_ball_has_none(self):
        V, T = self.ball()
        self.assertEqual(len(P.self_crossings(V, T)), 0)

    def test_a_crossing_pair_is_found(self):
        V = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0.2, 0.2, -0.5], [0.2, 0.2, 0.5], [0.9, 0.9, 0.0]], float)
        T = np.array([[0, 1, 2], [3, 4, 5]])
        self.assertEqual(P.self_crossings(V, T).tolist(), [[0, 1]])

    def test_a_cap_pushed_through_the_ball_is_found(self):
        V, T = self.ball()
        W = V.copy()
        top = W[:, 2] > 0.004
        W[top, 2] -= 0.025                                   # through the lower half; a fold alone is test_no_face_turns_over's
        self.assertGreater(len(P.self_crossings(W, T)), 0)


class Paws(unittest.TestCase):
    def test_closed_outward_manifolds(self):
        for sign in (1, -1):
            for lod in range(3):
                m = paw(sign, lod)
                for state in ("verts", "empty"):
                    with self.subTest(sign=sign, lod=lod, state=state):
                        self.assertTrue(FP.is_closed_manifold(m["tris"]))
                        self.assertGreater(signed_volume(m[state], m["tris"]), 0.0)

    def test_no_self_crossings(self):
        for sign in (1, -1):
            for lod in range(3):
                m = paw(sign, lod)
                for state in ("verts", "empty"):
                    with self.subTest(sign=sign, lod=lod, state=state):
                        self.assertEqual(len(P.self_crossings(m[state], m["tris"])), 0)

    def test_no_facet_comes_near_the_channel(self):
        bary = np.array([(i / 6, j / 6, 1 - (i + j) / 6) for i in range(7) for j in range(7 - i)])
        for sign in (1, -1):
            fr = P.frame_of(hero_arm(sign))
            for lod in range(3):
                m = paw(sign, lod)
                with self.subTest(sign=sign, lod=lod):
                    _, _, e = P.channel_coords(m["verts"], fr)
                    self.assertGreater(e.min(), P.CARVE_MARGIN - 1e-5)
                    pts = np.einsum("kc,tcx->tkx", bary, m["verts"][m["tris"]]).reshape(-1, 3)
                    self.assertGreater(P.channel_coords(pts, fr)[2].min(), 0.0005)

    def test_the_rigs_channel_gate(self):
        """rig_nyaakoto_runtime's 4.2 check, as it computes it: no hand vertex inside the channel, the breadth along
        it at most PAW_BREADTH_MAX_CM."""
        for sign in (1, -1):
            arm = hero_arm(sign)
            for lod in range(3):
                m = paw(sign, lod)
                loc = (m["verts"] - arm["channel"]) @ arm["socket_rot"]
                inside = (np.abs(loc[:, 0]) <= P.PAW_HALF) & ((loc[:, 1] / P.CHANNEL_HALF[0]) ** 2 + (loc[:, 2] / P.CHANNEL_HALF[1]) ** 2 < 1.0)
                with self.subTest(sign=sign, lod=lod):
                    self.assertEqual(int(inside.sum()), 0)
                    self.assertLessEqual(float(np.ptp(loc[:, 0])) * 100.0, TP.PAW_BREADTH_MAX_CM)

    def test_every_lod_is_the_same_surface(self):
        for sign in (1, -1):
            fine = paw(sign, 0)
            for lod in (1, 2):
                m = paw(sign, lod)
                for state in ("verts", "empty"):
                    with self.subTest(sign=sign, lod=lod, state=state):
                        d = nearest_distances(m[state], fine[state])
                        self.assertLess(np.percentile(d, 99), 0.75 * P.LOD_STEPS[lod])
                        self.assertLess(d.max(), 1.5 * P.LOD_STEPS[lod])


class EmptyFist(unittest.TestCase):
    def test_the_palm_and_knuckles_stay(self):
        for sign in (1, -1):
            m = paw(sign, 0)
            fr = m["skeleton"]["frame"]
            _, t, _ = P.channel_coords(m["verts"], fr)
            w = P.digit_weight(m["verts"], m["skeleton"])
            move = np.linalg.norm(m["empty"] - m["verts"], axis=1)
            with self.subTest(sign=sign):
                self.assertEqual(float(move[w == 0.0].max(initial=0.0)), 0.0)
                self.assertGreater(int((w == 0.0).sum()), len(w) // 4)
                self.assertEqual(float(move[np.abs(t) <= math.radians(P.CURL_RAMP[0])].max(initial=0.0)), 0.0)

    def test_each_digit_vertex_moves_by_its_oval_points_shift(self):
        m = paw(1, 1)
        fr = m["skeleton"]["frame"]
        w = P.digit_weight(m["verts"], m["skeleton"])
        on = w == 1.0
        self.assertGreater(int(on.sum()), 1000)
        s, t, _ = P.channel_coords(m["verts"][on], fr)
        du, dv = P.closed_shift(t, fr, s)
        expect = m["verts"][on] + du[:, None] * fr["z"] + dv[:, None] * fr["w"]
        self.assertLess(np.abs(m["empty"][on] - expect).max(), 1e-12)
        self.assertGreater(np.linalg.norm(m["empty"][on] - m["verts"][on], axis=1).max(), 0.02)   # the tips close

    def test_the_middle_toes_stand_proud_of_the_outer_toes(self):
        """The arc: in the empty fist, each middle toe reaches further from the palm's side (along -z) than either
        outer toe, by at least 5 mm. Root's 12:53 UTC review of e8d5b587: "the idle digit row is nearly straight"."""
        for sign in (1, -1):
            m = paw(sign, 1)
            fr = m["skeleton"]["frame"]
            s, t, _ = P.channel_coords(m["verts"], fr)
            w = P.digit_weight(m["verts"], m["skeleton"])
            reach = []
            for d in range(4):
                on = (w > 0.999) & (np.abs(s - (d - 1.5) * P.DIGIT_PITCH) < 0.006) & (np.abs(t) > math.radians(90.0))
                reach.append(float(((m["empty"][on] - fr["c"]) @ -fr["z"]).max()))
            with self.subTest(sign=sign, reach_mm=[round(r * 1000.0, 1) for r in reach]):
                self.assertGreater(min(reach[1], reach[2]) - max(reach[0], reach[3]), 0.005)

    def test_no_face_turns_over(self):
        for sign in (1, -1):
            for lod in range(3):
                m = paw(sign, lod)
                V, E, T = m["verts"], m["empty"], m["tris"]
                n0 = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
                n1 = np.cross(E[T[:, 1]] - E[T[:, 0]], E[T[:, 2]] - E[T[:, 0]])
                with self.subTest(sign=sign, lod=lod):
                    self.assertEqual(int((np.einsum("ij,ij->i", n0, n1) <= 0.0).sum()), 0)

    def test_it_is_a_function_of_position(self):
        m = paw(-1, 2)
        idx = np.random.default_rng(3).permutation(len(m["verts"]))
        self.assertTrue(np.array_equal(P.empty_points(m["verts"][idx], m["skeleton"]), m["empty"][idx]))


class Surface(unittest.TestCase):
    def test_coat_white_on_the_toes_tabby_on_the_back(self):
        m = paw(1, 0)
        coat = m["coat"]
        self.assertGreaterEqual(float(coat.min()), 0.0)
        self.assertLessEqual(float(coat.max()), 1.0)
        V = m["verts"]
        w = P.digit_weight(V, m["skeleton"], P.COAT_RAMP)
        turn = P.turn_of(V, m["skeleton"]["frame"])
        tip = (w == 1.0) & (turn >= P.COAT_TURN[1])
        back = (w == 0.0) | (turn <= P.COAT_TURN[0])
        per_vertex = np.zeros(len(V))
        per_vertex[m["tris"].ravel()] = coat.ravel()
        self.assertGreater(int(tip.sum()), 500)
        self.assertTrue(np.allclose(per_vertex[tip], 1.0))
        self.assertTrue(np.allclose(per_vertex[back], 0.0))
        self.assertTrue(0.1 < float(coat.mean()) < 0.5)

    def test_uvs_at_the_bodys_density_without_a_seam_across_a_face(self):
        for sign in (1, -1):
            m = paw(sign, 0)
            V, T, uv = m["verts"], m["tris"], m["uvs"]
            area3 = 0.5 * np.linalg.norm(np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]), axis=1)
            d1, d2 = uv[:, 1] - uv[:, 0], uv[:, 2] - uv[:, 0]
            area2 = 0.5 * np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0])
            ratio = area2 / np.maximum(area3, 1e-14) / P.UV_PER_M ** 2
            with self.subTest(sign=sign):
                self.assertTrue(0.6 < float(np.median(ratio)) < 1.6, float(np.median(ratio)))
                span = (uv.max(1) - uv.min(1)).max(1)
                self.assertLess(float(span.max()), 4.0 * P.LOD_STEPS[0] * P.UV_PER_M * 3.0)

    def test_fuzz_is_bounded_and_clear_of_the_channel(self):
        skel = paw(1, 0)["skeleton"]
        rng = np.random.default_rng(9)
        s = rng.uniform(-0.05, 0.05, 4000)
        t = rng.uniform(-math.pi, math.pi, 4000)
        e = rng.uniform(0.0, 0.03, 4000)
        pts = P.from_channel(s, t, e, skel["frame"])
        f = P.fuzz_amount(pts, skel)
        self.assertGreaterEqual(float(f.min()), 0.0)
        self.assertLessEqual(float(f.max()), P.FUZZ_MAX)
        near = P.channel_sdf(pts, skel["frame"]) <= P.CARVE_MARGIN
        self.assertTrue(near.any())
        self.assertEqual(float(f[near].max()), 0.0)


if __name__ == "__main__":
    unittest.main()
