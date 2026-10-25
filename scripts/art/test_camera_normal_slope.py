"""Tests for camera_normal_slope: the camera-space sign convention of the patch study's normal renders.

Run: python3 -m unittest scripts/art/test_camera_normal_slope.py
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camera_normal_slope as C  # noqa: E402


def tilted(theta_x=0.0, theta_y=0.0, shape=(4, 5), toward=-1.0):
    """Unit normals tilted by theta_x about the image y axis and theta_y about x; toward=-1 faces the camera."""
    n = np.array([math.sin(theta_x), math.sin(theta_y), toward * math.cos(theta_x) * math.cos(theta_y)])
    n /= np.linalg.norm(n)
    return np.broadcast_to(n, shape + (3,)).copy()


class Slope(unittest.TestCase):
    def test_a_face_toward_the_camera_has_no_slope(self):
        slope, stats = C.across_slope(tilted(), "x")
        self.assertTrue(np.allclose(slope, 0.0))
        self.assertAlmostEqual(stats["median_facing"], 1.0)
        self.assertEqual(stats["pixels_below_floor"], 0)

    def test_the_slope_is_the_tangent_of_the_tilt_across_the_grain(self):
        for across, kw in (("x", {"theta_x": 0.05}), ("y", {"theta_y": -0.03})):
            with self.subTest(across=across):
                slope, _ = C.across_slope(tilted(**kw), across)
                theta = kw.get("theta_x", kw.get("theta_y"))
                self.assertTrue(np.allclose(slope, math.tan(theta), rtol=1e-9))

    def test_attempt_0s_reading_is_refused(self):
        # Attempt 0 took +z as facing: the same normals with z flipped are not facing the camera.
        with self.assertRaises(C.NormalRenderError):
            C.across_slope(tilted(theta_x=0.004, toward=+1.0), "x")

    def test_the_old_clamp_made_a_slope_1000_times_its_value(self):
        n = tilted(theta_x=0.004)
        old = n[..., 0] / np.maximum(n[..., 2], 1e-3)
        new, _ = C.across_slope(n, "x")
        self.assertTrue(np.allclose(old / new, 1000.0, rtol=1e-4))

    def test_the_encoding_round_trips(self):
        n = tilted(theta_x=0.1, theta_y=0.2)
        self.assertTrue(np.allclose(C.decode(n * 0.5 + 0.5), n))

    def test_non_unit_values_are_refused(self):
        with self.assertRaises(C.NormalRenderError):
            C.across_slope(tilted() * 0.5, "x")
        with self.assertRaises(C.NormalRenderError):
            C.across_slope(C.decode(np.zeros((3, 3, 3))), "x")   # a black render: (-1, -1, -1), length 1.73

    def test_an_unknown_axis_is_refused(self):
        with self.assertRaises(ValueError):
            C.across_slope(tilted(), "z")


if __name__ == "__main__":
    unittest.main()
