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


class Refused(unittest.TestCase):
    """Root's probe of fe74f78 and its neighbours: refused outright, never a non-finite or clamped slope."""

    def test_roots_probe_one_infinite_x_amid_valid_normals(self):
        n = np.zeros((16, 16, 3))
        n[..., 2] = -1.0
        n[0, 0, 0] = float("inf")                       # fe74f78 passed the medians and returned an infinite slope
        with self.assertRaises(C.NormalRenderError) as cm:
            C.across_slope(n, "x")
        self.assertIn("non-finite", str(cm.exception))

    def test_a_nan_anywhere(self):
        for k in range(3):
            with self.subTest(component=k):
                n = tilted(shape=(8, 8))
                n[3, 5, k] = float("nan")
                with self.assertRaises(C.NormalRenderError):
                    C.across_slope(n, "y")

    def test_a_non_finite_encoded_value(self):
        enc = np.full((4, 4, 4), 0.5)
        enc[..., 2] = 0.0
        enc[1, 1, 3] = float("-inf")                    # even in the alpha channel decode drops
        with self.assertRaises(C.NormalRenderError):
            C.decode(enc)

    def test_shapes_that_are_not_a_normal_image(self):
        for shape in ((16, 3), (16, 16, 2), (16, 16, 4), (0, 16, 3), (16, 0, 3), (2, 2, 2, 3)):
            with self.subTest(shape=shape):
                n = np.zeros(shape)
                if shape[-1] >= 3:
                    n[..., 2] = -1.0
                with self.assertRaises(C.NormalRenderError):
                    C.across_slope(n, "x")
        with self.assertRaises(C.NormalRenderError):
            C.decode(np.full((4, 4, 2), 0.5))

    def test_one_pixel_below_the_facing_floor_is_refused_not_clamped(self):
        for z in (0.0, 0.5e-3, 0.2):                    # grazing, below the floor, back-facing
            with self.subTest(z=z):
                n = tilted(shape=(8, 8))
                n[2, 2] = (math.sqrt(1.0 - z * z), 0.0, z if z > 0.1 else -z)
                with self.assertRaises(C.NormalRenderError) as cm:
                    C.across_slope(n, "x")
                self.assertIn("less than", str(cm.exception))

    def test_a_steep_pixel_amid_facing_normals_gives_a_finite_slope(self):
        n = tilted(shape=(6, 7))
        n[1, 4] = (math.sin(1.2), 0.0, -math.cos(1.2))  # a check's wall: steep, still facing
        slope, stats = C.across_slope(n, "x")
        self.assertTrue(np.isfinite(slope).all())
        self.assertAlmostEqual(slope[1, 4], math.tan(1.2))
        self.assertAlmostEqual(stats["min_facing"], math.cos(1.2))


if __name__ == "__main__":
    unittest.main()
