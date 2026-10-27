"""Tests for b09_prop_clash: no station prop passes through another, and each resting prop rests on its support.

Run: python3 -m unittest scripts/art/test_b09_prop_clash.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b09_prop_clash as C  # noqa: E402
import b09_workshop_craft as B  # noqa: E402


def cube(name, lo, hi):
    return B.box(name, lo, hi, "M")


class Primitives(unittest.TestCase):
    def test_resting_is_not_crossing(self):
        self.assertEqual(C.crossings(cube("a", (0, 0, 0), (2, 2, 2)), cube("b", (0.5, 0.5, 2), (1.5, 1.5, 3)))[0], 0)
        self.assertEqual(C.crossings(cube("a", (0, 0, 0), (2, 2, 2)), cube("b", (2, 0, 0), (3, 2, 2)))[0], 0)

    def test_overlap_crosses_and_a_box_within_is_contained(self):
        self.assertGreater(C.crossings(cube("a", (0, 0, 0), (2, 2, 2)), cube("b", (1, 1, 1), (3, 3, 3)))[0], 0)
        inner = cube("b", (0.5, 0.5, 0.5), (1.5, 1.5, 1.5))
        self.assertEqual(C.crossings(cube("a", (0, 0, 0), (2, 2, 2)), inner)[0], 0)
        self.assertEqual(C.contained(inner, cube("a", (0, 0, 0), (2, 2, 2))), 1)

    def test_the_real_weapon_is_read_whole(self):
        w = C.weapon7()
        self.assertEqual(len(w.tris), 53360)                                 # build_record.json, LOD0
        lo, hi = w.bounds()
        np.testing.assert_allclose([lo[0], hi[0]], B.WEAPON7["x_range_cm"], atol=0.01)
        np.testing.assert_allclose([lo[2], hi[2]], B.WEAPON7["z_range_cm"], atol=0.02)


class Stations(unittest.TestCase):
    def test_no_prop_passes_through_another(self):
        for i in (0, 1, 2, 3, None):
            for label, rows in C.clashes(i).items():
                self.assertEqual(rows, [], (i, label))

    def test_each_resting_prop_rests_on_its_support(self):
        for i in (0, 1, 2, 3, None):
            for label, rows in C.supports(i).items():
                for item, carrier, gap in rows:
                    self.assertIsNotNone(gap, (label, item, carrier))
                    self.assertLessEqual(gap, C.CONTACT_CM, (label, item, carrier))

    def test_weapon_cradles_hold_the_clean_cylinders(self):
        origin, _ = B.weapon_rest()
        for x0, x1, r in (B.WEAPON7["collar_cm"], B.WEAPON7["muzzle_bare_cm"]):
            v = C.weapon7().verts
            band = v[(v[:, 0] > x0 + 0.3) & (v[:, 0] < x1 - 0.3)]
            radius = np.hypot(band[:, 1], band[:, 2])
            self.assertAlmostEqual(float(radius.max()), r, delta=0.011, msg=(x0, x1))


if __name__ == "__main__":
    unittest.main()
