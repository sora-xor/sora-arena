"""Tests for the first-person ID-pixel analysis (analyse_yumi_fp_review), on synthetic images.

Run: python3 -m unittest scripts/art/test_analyse_yumi_fp_review.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse_yumi_fp_review as A  # noqa: E402

H, W = 90, 160                                   # 16:9


def image():
    img = np.zeros((H, W, 3))
    img[60:90, 0:30] = (0.8, 0.0, 0.0)           # the bow, low left, touching the left and bottom edges
    img[40:50, 70:90] = (0.0, 0.8, 0.05)         # the arrow, over the centre
    img[70:80, 30:40] = (0.05, 0.0, 0.8)         # the paw
    img[0:5, 100:160] = (0.9, 0.9, 0.9)          # a bright unsaturated sky: background
    img[10:12, 10:12] = (0.6, 0.4, 0.0)          # a mixed edge pixel: not twice the next channel
    return img


class Analyse(unittest.TestCase):
    def test_parts_are_classified_by_a_dominant_channel(self):
        cls = A.classify(image())
        self.assertEqual(int((cls == 1).sum()), 30 * 30)
        self.assertEqual(int((cls == 2).sum()), 10 * 20)
        self.assertEqual(int((cls == 3).sum()), 10 * 10)
        self.assertEqual(int(cls[0:5, 100:160].max()), 0)       # sky
        self.assertEqual(int(cls[10:12, 10:12].max()), 0)       # mixed

    def test_extents_edges_and_the_reticle(self):
        res = A.analyse(image(), 0.12)
        bow, arrow = res["parts"]["bow"], res["parts"]["arrow"]
        self.assertTrue(bow["touches"]["left"] and bow["touches"]["bottom"])
        self.assertFalse(bow["touches"]["right"] or bow["touches"]["top"])
        self.assertLess(bow["extent_uv"]["u"][1], 0.0)          # left half
        self.assertLess(bow["extent_uv"]["v"][1], 0.0)          # lower half
        self.assertEqual(bow["in_reticle_disc"], 0)
        self.assertGreater(arrow["in_reticle_disc"], 0)
        self.assertTrue(res["reticle_occluded"])
        self.assertAlmostEqual(res["viewmodel_share"], (900 + 200 + 100) / (H * W))

    def test_an_empty_centre_leaves_the_reticle_clear(self):
        img = image()
        img[40:50, 70:90] = 0.0
        res = A.analyse(img, 0.12)
        self.assertFalse(res["reticle_occluded"])
        self.assertEqual(res["parts"]["arrow"]["pixels"], 0)
        self.assertNotIn("extent_uv", res["parts"]["arrow"])

    def test_the_reticle_disc_is_round_in_screen_space(self):
        # 0.12 half-heights at 1080p is 64.8 px, so about pi x 64.8^2 pixels.
        res = A.analyse(np.zeros((1080, 1920, 3)), 0.12)
        self.assertAlmostEqual(res["reticle_disc_pixels"] / (np.pi * 64.8 ** 2), 1.0, delta=0.01)


if __name__ == "__main__":
    unittest.main()
