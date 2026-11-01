"""Tests for the shells' CPU fragment count (fp_fur_overdraw).

Run: python3 -m unittest scripts/art/test_fp_fur_overdraw.py

On a synthetic hold: three shell layers of a square, facing the eye, over an
opaque square behind them.
- Each layer is counted wherever it covers the opaque square: its fragments
  are that square's pixels.
- Layers facing away are not counted (one-sided material).
- An opaque square in front of the layers hides them all.
- The camera frame matches the capture's eye: a rotator of zero looks down +X.
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fp_fur_overdraw as O  # noqa: E402

W, H = 320, 180
CAM = {"location_cm": [0.0, 0.0, 0.0], "rotation_deg": [0.0, 0.0, 0.0], "field_of_view_deg": 70.0}
HOLD = {"anchor": [50.0, 0.0, 0.0], "rot": [0.0, 0.0, 0.0], "draw": 1.0}


def square(x_m, half_m=0.05):
    """Two triangles of a square in bow metres at x = x_m (toward the eye is -x), in y and z."""
    a, b = -half_m, half_m
    v = np.array([[x_m, a, a], [x_m, b, a], [x_m, b, b], [x_m, a, b]])
    return v, np.array([[0, 1, 2], [0, 2, 3]])


def manifest():
    return {"resolution": [W, H], "mesh_scale": 1.0, "holds": {"h": HOLD}, "cameras": {"h": CAM}}


def shells(normal_x=-1.0):
    verts, tris = [], []
    for i, x in enumerate((-0.001, -0.002, -0.003)):
        v, t = square(x)
        verts.append(v)
        tris.append(t + 4 * i)
    V = np.concatenate(verts)
    return {"verts": V, "tris": np.concatenate(tris), "normals": np.tile([normal_x, 0.0, 0.0], (len(V), 1)),
            "layers": 3}


def opaque(x_m):
    v, t = square(x_m, 0.06)
    return v[t]


class Camera(unittest.TestCase):
    def test_a_zero_rotator_looks_down_x(self):
        loc, M = O.camera_frame(CAM)
        self.assertTrue(np.allclose(M, np.eye(3)))
        _loc, M = O.camera_frame({"location_cm": [0, 0, 0], "rotation_deg": [-30.0, 20.0, 0.0]})
        f = M[0]
        self.assertAlmostEqual(math.degrees(math.asin(f[2])), -30.0, places=9)
        self.assertAlmostEqual(math.degrees(math.atan2(f[1], f[0])), 20.0, places=9)
        self.assertTrue(np.allclose(M @ M.T, np.eye(3)))


class Fragments(unittest.TestCase):
    def test_each_layer_counts_where_it_covers_the_opaque_square(self):
        out = O.hold_overdraw(manifest(), "h", shells(), opaque(0.0), np.zeros((0, 3, 3)))
        per = out["per_layer"]
        self.assertTrue(all(p > 1000 for p in per), per)
        self.assertEqual(out["fragments"], sum(per))
        self.assertEqual(out["max_layers"], 3)
        self.assertAlmostEqual(out["mean_layers"], 3.0, delta=0.05)
        # Each layer is about the same size on screen, no smaller the nearer it is (at this size they may tie).
        self.assertLessEqual(per[0], per[2])
        self.assertLess((per[2] - per[0]) / per[0], 0.05)

    def test_layers_facing_away_are_not_counted(self):
        out = O.hold_overdraw(manifest(), "h", shells(normal_x=1.0), opaque(0.0), np.zeros((0, 3, 3)))
        self.assertEqual(out["fragments"], 0)

    def test_an_opaque_square_in_front_hides_them(self):
        out = O.hold_overdraw(manifest(), "h", shells(), opaque(-0.01), np.zeros((0, 3, 3)))
        self.assertEqual(out["fragments"], 0)


if __name__ == "__main__":
    unittest.main()
