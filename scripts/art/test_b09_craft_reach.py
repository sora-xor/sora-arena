"""Tests for b09_craft_reach: the hero's reach against the b09 craft contacts, as root's inputs and the module stand.

Run: python3 -m unittest scripts/art/test_b09_craft_reach.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b09_craft_reach as R  # noqa: E402
import b09_workshop_craft as B  # noqa: E402


class Hero(unittest.TestCase):
    def test_the_arm_and_its_reach(self):
        self.assertAlmostEqual(R.REACH_CM, 0.98 * 54.05, places=9)          # 98 % of shoulder to wrist
        sh = R.shoulders(-80.0, 0.0)
        np.testing.assert_allclose(sh["R"], [-80.0 + 4.0 - 4.0, 27.7, 88.0 + 64.0 - 24.5])
        np.testing.assert_allclose(sh["L"] * [1, -1, 1], sh["R"])           # mirrored about the stand

    def test_the_nearest_stands_touch_the_proxies(self):
        self.assertEqual([R.nearest_stand_x(i) for i in range(4)], [-66.0, -71.0, -72.0, -71.0])
        for i in range(4):                                                  # all nearer than the framing stand
            self.assertGreater(R.nearest_stand_x(i), B.WORK_STAND[0])


class Findings(unittest.TestCase):
    """The study's findings, pinned: if the layout or the hero changes, these change, and the doc with them."""

    def test_no_station_is_within_reach_as_laid_out(self):
        for i in range(4):
            short = [s for _, _, s, req in R.reach_table(i) if req]
            self.assertGreater(max(short), 0.0, B.STATIONS[i][0])

    def test_the_two_ended_bend_passes_behind_the_form(self):
        ends = [(l, s) for l, _, s, req in R.reach_table(0) if l.startswith("two-ended")]
        self.assertTrue(ends and all(s > 30.0 for _, s in ends))            # no shift in front of the bench helps

    def test_the_smallest_shifts_toward_the_hero(self):
        self.assertEqual([R.layout_shift(i) for i in range(4)], [(15.0, 0.0), (28.0, 0.0), (19.0, 0.0), (40.0, 11.0)])
        for i in range(4):
            dx, dz = R.layout_shift(i)
            worst = max(d for _, d, _, req in R.reach_table(i, (dx, dz)) if req)
            self.assertLessEqual(worst, R.REACH_CM - R.REACH_MARGIN_CM + 1e-9)


if __name__ == "__main__":
    unittest.main()
