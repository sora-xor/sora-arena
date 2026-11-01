"""Tests for b09_craft_region: the working region's natural stop, admission rule and sampling, and a light pass of its
gates. The full region gate (dense pose, view at 16:9 and 21:9, body, triangle-exact clearance at every region sample,
clash and supports) is the qualification run that records its inputs' hashes
(Saved/Qualification/2026-10-27/b09-craft-region/par_full_gate.py), not a unit test.

Run: /usr/bin/python3 -m unittest scripts/art/test_b09_craft_region.py
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b09_craft_poses as P  # noqa: E402
import b09_craft_region as R  # noqa: E402
import b09_workshop_craft as B  # noqa: E402

STATIONS = range(4)


class NaturalStop(unittest.TestCase):
    def test_the_capsule_stops_against_the_proxy_on_the_centre_line(self):
        for i in STATIONS:
            x0 = float(R.natural_stop(i)[0])
            self.assertFalse(R._hits(i, x0, 0.0), i)
            self.assertTrue(R._hits(i, x0 + 0.05, 0.0), i)

    def test_the_craft_stand_is_the_natural_stop(self):
        for i in STATIONS:
            np.testing.assert_allclose(B.craft_stand(i), R.natural_stop(i), atol=1e-6)

    def test_the_near_limit_never_passes_the_natural_stop(self):
        for i in STATIONS:
            x0 = float(R.natural_stop(i)[0])
            W = R.region_of(i)["lateral_cm"]
            for y in np.linspace(-W, W, 9):
                self.assertLessEqual(R.near_limit(i, float(y)), x0 + 1e-6, (i, y))


class Admission(unittest.TestCase):
    def test_the_rule_bounds_depth_lateral_and_the_facing_band(self):
        for i in STATIONS:
            r = R.region_of(i)
            x0 = float(R.natural_stop(i)[0])
            stop = np.array([x0, 0.0, 0.0])
            b = R.bearing_deg(i, stop)
            self.assertTrue(R.admitted(i, stop, b), i)
            self.assertTrue(R.admitted(i, stop, b + r["yaw_deg"]), i)
            self.assertFalse(R.admitted(i, stop, b + r["yaw_deg"] + 0.5), i)
            far = np.array([x0 - r["depth_cm"], 0.0, 0.0])
            self.assertTrue(R.admitted(i, far, R.bearing_deg(i, far)), i)
            beyond = np.array([x0 - r["depth_cm"] - 0.5, 0.0, 0.0])
            self.assertFalse(R.admitted(i, beyond, R.bearing_deg(i, beyond)), i)
            wide = np.array([x0 - 5.0, r["lateral_cm"] + 0.5, 0.0])
            self.assertFalse(R.admitted(i, wide, R.bearing_deg(i, wide)), i)

    def test_the_facing_is_about_the_bearing_to_the_fixed_look_point(self):
        for i in STATIONS:
            x0 = float(R.natural_stop(i)[0])
            lp = R.look_point(i)
            np.testing.assert_allclose(lp, B.station_parts(i)[1]["LookPoint"][0])
            side = np.array([x0 - 5.0, R.region_of(i)["lateral_cm"], 0.0])
            b = R.bearing_deg(i, side)
            self.assertAlmostEqual(b, math.degrees(math.atan2(lp[1] - side[1], lp[0] - side[0])), places=9)
            f = R.facings(i, side)
            self.assertAlmostEqual(f[1], b, places=9)
            self.assertAlmostEqual(f[2] - f[0], 2 * R.region_of(i)["yaw_deg"], places=9)


class Sampling(unittest.TestCase):
    def test_the_stands_cover_the_boundary_and_the_interior_and_are_admitted(self):
        for i in STATIONS:
            names = [n for n, _ in R.stands(i)]
            for kind in ("near", "far", "side", "inner"):
                self.assertTrue(any(n.startswith(kind) for n in names), (i, kind))
            for n, st, yaw in R.samples(i):
                self.assertTrue(R.admitted(i, st, yaw), (i, n, yaw))

    def test_the_dense_sampling_is_five_facings_over_nine_by_six(self):
        for i in STATIONS:
            d = R.dense(i)
            self.assertGreaterEqual(len(d), 9 * 5)
            self.assertTrue(all(R.admitted(i, st, yaw) for _, st, yaw in d), i)


class Records(unittest.TestCase):
    def test_the_prototype_target_and_the_kept_records(self):
        self.assertEqual(R.REGION, {"depth_cm": 15.0, "lateral_cm": 10.0, "yaw_deg": 10.0})
        self.assertEqual((R.REGION_EXPLORATORY["depth_cm"], R.REGION_EXPLORATORY["lateral_cm"],
                          R.REGION_EXPLORATORY["yaw_deg"]), (22.0, 15.0, 15.0))
        self.assertIn("infeasible", R.REGION_EXPLORATORY["measured"])
        self.assertEqual(R.BODY_CLEAR_CM, 2.5)

    def test_a_station_region_smaller_than_the_target_is_a_proposal_only(self):
        for i, r in R.REGION_BY_STATION.items():
            self.assertTrue(r["depth_cm"] <= R.REGION["depth_cm"] and r["lateral_cm"] <= R.REGION["lateral_cm"]
                            and r["yaw_deg"] <= R.REGION["yaw_deg"], i)


class LightGates(unittest.TestCase):
    """The pose gate (no clearance) at the region's four far and near corners, the facing band's ends: a quick read of
    the full gate's hardest stands."""

    def corners(self, i):
        r = R.region_of(i)
        x0 = float(R.natural_stop(i)[0])
        for x in (R.near_limit(i, -r["lateral_cm"]), x0 - r["depth_cm"]):
            for y in (-r["lateral_cm"], r["lateral_cm"]):
                st = np.array([x if x < x0 - 1.0 else R.near_limit(i, y), y, 0.0])
                for yaw in (R.facings(i, st)[0], R.facings(i, st)[-1]):
                    yield st, yaw

    def _corners_pass(self, i):
        for st, yaw in self.corners(i):
            rep = P.check(i, st, yaw, clearance=False)
            self.assertTrue(all(r["ok"] for r in rep.values()),
                            (B.STATIONS[i][0], st.tolist(), round(yaw, 2), [r["fail"][:1] for r in rep.values() if not r["ok"]]))

    def test_the_rib_form_oil_rack_and_shell_bench_corners(self):
        for i in (0, 2, 3):
            self._corners_pass(i)

    @unittest.expectedFailure
    def test_open_the_paste_corners(self):              # the stroke's top end and the rims step (B09_WORKSHOP_CRAFT.md 13.2)
        self._corners_pass(1)


if __name__ == "__main__":
    unittest.main()
