"""Tests for b09_craft_poses: both paws, every sample of every craft action, at the natural stop.

The working region's gates (every admitted stand and facing) are b09_craft_region's: test_b09_craft_region.py covers
its rule and sampling, and Saved/Qualification/2026-10-27/b09-craft-region/par_full_gate.py is the qualification run.
Open defects stay failing here as asserted expected failures, never passed by a weaker test.

Run: /usr/bin/python3 -m unittest scripts/art/test_b09_craft_poses.py
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
import nyaakoto_fp_paws as FP  # noqa: E402


class Hero(unittest.TestCase):
    def test_the_arm_and_the_production_paw(self):
        self.assertAlmostEqual(P.REACH, 0.98 * 54.05, places=9)
        self.assertAlmostEqual(P.WRIST_BACK, FP.WRIST_BACK * 100.0, places=9)        # carpus to knuckle line
        self.assertAlmostEqual(P.PALM_HALF[2], FP.PALM_THICK * 100.0 + 0.1, places=9)  # the palm, its pad proud
        self.assertAlmostEqual(P.PALM_MID + P.PALM_HALF[0], P.WRIST_BACK + 0.55, places=9)

    def test_shoulders_follow_the_stand_and_facing(self):
        for i in range(4):
            st = B.craft_stand(i)
            for yaw in (0.0, 15.0):
                sh, rz = P.shoulders(st, yaw)
                eye = P.eye_at(st, yaw)
                np.testing.assert_allclose(sh["R"], eye + rz @ P.SHOULDER_FROM_EYE, atol=1e-9)
                np.testing.assert_allclose(sh["L"], eye + rz @ (P.SHOULDER_FROM_EYE * [1, -1, 1]), atol=1e-9)


class Actions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acts = {i: P.actions(i) for i in range(4)}

    def test_both_paws_have_a_role_in_every_phase(self):
        for i, acts in self.acts.items():
            for name, steps in acts:
                self.assertEqual(steps[0]["kind"], "phase", name)
                self.assertEqual(steps[-1]["kind"], "phase", name)
                for ph in steps:
                    self.assertTrue(ph["L"] and ph["R"], (name, ph["phase"]))
                    if ph["kind"] == "transition":
                        self.assertGreaterEqual(max(len(ph["L"]), len(ph["R"])), P.SAMPLES, (name, ph["phase"]))

    def test_press_clips_end_by_the_action_age_cap(self):
        self.assertEqual(B.ACTION_PRESENTATION_MS, 1200)
        self.assertTrue(all(ms <= B.ACTION_PRESENTATION_MS for ms in P.CLIP_MAX_MS.values()))

    def test_targets_are_orthonormal_frames(self):
        for acts in self.acts.values():
            for _, steps in acts:
                for ph in steps:
                    for t in ph["L"] + ph["R"]:
                        self.assertAlmostEqual(float(np.linalg.norm(t["F"])), 1.0, places=9)
                        self.assertAlmostEqual(float(np.linalg.norm(t["N"])), 1.0, places=9)
                        self.assertLess(abs(float(t["F"] @ t["N"])), 1e-9)

    def test_the_wind_presses_along_the_forms_own_normal(self):
        _, sk, _, _ = B.station_parts(0)
        for k, z in enumerate(B.hoop_z(), 1):
            n = np.asarray(sk[f"WindPress{k}"][1], float)
            slope = float(B.profile_r(z + 0.01) - B.profile_r(z - 0.01)) / 0.02
            self.assertAlmostEqual(float(-n[2] / np.linalg.norm(n[:2])), slope, places=6)

    def test_the_brush_is_held_as_a_pencil(self):
        sh, _ = P.shoulders(B.craft_stand(1))
        tip = np.array([-37.0, 0.0, 130.0])
        t = P.brush(tip, [-1.0, 0.0, 0.0], sh["R"])
        handle = P.unit(t["C"] + t["F"] * P.BRUSH_REACH_CM - tip)
        self.assertAlmostEqual(math.degrees(math.acos(float(-handle @ t["F"]))), P.BRUSH_GRIP_DEG, places=6)

    def test_the_inspection_checks_the_seated_shells_fuse_cords(self):
        """Coordination 277: the single Inspect unit passes over the three seated shells' fuse cords, shell 3 to 1, the
        elbow raised over them; the tube is not a contact."""
        name, steps = self.acts[3][-1]
        self.assertTrue(name.startswith("check the fuses"), name)
        _, sk, _, _ = B.station_parts(3)
        top = float(B.shell("wrapped").verts[:, 2].max())
        path = steps[-1]["L"]
        for k, t in ((3, path[0]), (1, path[-1])):
            np.testing.assert_allclose(t["P"], np.asarray(sk[f"ShellSeat{k}"][0]) + [0.0, 0.0, top], atol=1e-6)
        self.assertIs(steps[-1]["poles"]["L"], P.POLES_OVER["L"])
        for t in steps[-1]["L"] + steps[-1]["R"]:
            self.assertGreater(float(np.linalg.norm(t["P"] - np.asarray(sk["TubeFuse"][0]))), 10.0)

    def test_a_palm_on_a_ball_lies_on_its_tangent_plane_toward_the_hero(self):
        sh, _ = P.shoulders(B.craft_stand(3))
        centre, r = np.array([-42.0, -0.25, 133.9]), B.SHELL["wrapped_cm"] / 2
        for side, inward in (("L", [0.0, 1.0, 0.0]), ("R", [0.0, -1.0, 0.0])):
            t = P.palm_on_ball(centre, r, inward, sh[side], P.FWD)
            self.assertAlmostEqual(float(np.linalg.norm(t["C"] - centre)), r + P.PAD_OFF, places=9)
            self.assertAlmostEqual(float(np.linalg.norm(t["P"] - centre)), r, places=9)
            outward = -t["N"]
            self.assertLessEqual(float(outward[0]), -math.sin(math.radians(P.PALM_BALL_BACK_DEG)) * math.cos(
                math.radians(P.PALM_BALL_LAT_DEG)) + 1e-9)                 # facing the hero by back_deg at least
            self.assertAlmostEqual(math.degrees(math.asin(float(outward[2]))), P.PALM_BALL_LAT_DEG, places=6)


class NaturalStop(unittest.TestCase):
    """Every sample of every action, both paws, the props in each phase's state, triangle-exact, at the natural stop
    facing the bearing to the look point."""

    @classmethod
    def setUpClass(cls):
        cls.report = {}
        for i in range(4):
            st = B.craft_stand(i)
            cls.report[i] = P.check(i, st, R.bearing_deg(i, st), clearance=True, every=1)

    def _passes(self, i, prefix=None):
        for name, r in self.report[i].items():
            if prefix is None or name.startswith(prefix):
                self.assertTrue(r["ok"], (B.STATIONS[i][0], name, r["fail"]))
                self.assertLessEqual(r["worst"]["reach_pct"], 98.0)
                self.assertLessEqual(r["worst"]["wrist_deg"], P.WRIST_MAX)
                self.assertLessEqual(r["worst"]["elbow_flex_deg"], P.ELBOW_MAX)
                self.assertGreaterEqual(r["worst"]["clear_cm"], P.CLEAR_CM)
                self.assertLessEqual(r["worst"]["elbow_step_cm"], P.ELBOW_STEP_CM)

    def test_the_oil_rack(self):
        self._passes(2)

    def test_the_shell_bench(self):
        self._passes(3)

    def test_the_paste_stroke(self):
        self._passes(1, "paste a panel")

    @unittest.expectedFailure
    def test_open_the_rib_form(self):                                  # clearance 38 of 99 region samples (open)
        self._passes(0)

    @unittest.expectedFailure
    def test_open_the_rims_on_the_paste_pose(self):                    # the upper mouth out of reach (open)
        self._passes(1, "seat the rims")

    def test_crouch_is_reported_not_qualified(self):
        for i in range(4):
            rows = P.crouched(i)
            self.assertTrue(rows)
            self.assertFalse(any(r["ok"] for r in rows.values()), B.STATIONS[i][0])   # the crouched eye is 68 cm lower


class ContactView(unittest.TestCase):
    """The hero sees the active contacts, both paws and what they work (a brush's bristle corners too), through every
    working sample, from the natural stop at the natural look, at 16:9 and 21:9."""

    @classmethod
    def setUpClass(cls):
        cls.view = {i: P.view_at(i, B.craft_stand(i), R.bearing_deg(i, B.craft_stand(i))) for i in range(4)}

    def _seen(self, i, prefix=None):
        for name, rows in self.view[i].items():
            if prefix is None or name.startswith(prefix):
                for aspect, r in rows.items():
                    self.assertEqual(r["in_frame"], r["samples"], (B.STATIONS[i][0], name, aspect, r))

    def test_the_rib_form(self):
        self._seen(0)

    def test_the_paste_stroke(self):
        self._seen(1, "paste a panel")

    def test_the_oil_rack(self):
        self._seen(2)

    def test_the_shell_bench(self):
        self._seen(3)

    @unittest.expectedFailure
    def test_open_the_rims_on_the_paste_pose(self):
        self._seen(1, "seat the rims")


if __name__ == "__main__":
    unittest.main()
