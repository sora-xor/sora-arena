"""Tests for b09_craft_poses: both paws, every sample of every craft action, from one supported stand.

Run: python3 -m unittest scripts/art/test_b09_craft_poses.py
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
import b09_workshop_craft as B  # noqa: E402
import nyaakoto_fp_paws as FP  # noqa: E402


class Hero(unittest.TestCase):
    def test_the_arm_and_the_production_paw(self):
        self.assertAlmostEqual(P.REACH, 0.98 * 54.05, places=9)
        self.assertAlmostEqual(P.WRIST_BACK, FP.WRIST_BACK * 100.0, places=9)        # carpus to knuckle line
        self.assertAlmostEqual(P.PALM_HALF[2], FP.PALM_THICK * 100.0 + 0.1, places=9)  # the palm, its pad proud
        self.assertAlmostEqual(P.PALM_MID + P.PALM_HALF[0], P.WRIST_BACK + 0.55, places=9)

    def test_shoulders_are_fixed_at_the_craft_stand(self):
        for i in range(4):
            sh, _ = P.shoulders(B.craft_stand(i))
            eye = B.craft_stand(i) + [B.EYE[0], B.EYE[1], B.CAPSULE_HALF + B.EYE[2]]
            np.testing.assert_allclose(sh["R"], eye + P.SHOULDER_FROM_EYE)
            np.testing.assert_allclose(sh["L"], eye + P.SHOULDER_FROM_EYE * [1, -1, 1])


class Actions(unittest.TestCase):
    def test_both_paws_have_a_role_in_every_phase(self):
        for i in range(4):
            for name, steps in P.actions(i):
                self.assertEqual(steps[0]["kind"], "phase", name)
                self.assertEqual(steps[-1]["kind"], "phase", name)
                for ph in steps:
                    self.assertTrue(ph["L"] and ph["R"], (name, ph["phase"]))
                    if ph["kind"] == "transition":
                        self.assertEqual(max(len(ph["L"]), len(ph["R"])), P.SAMPLES, (name, ph["phase"]))

    def test_press_clips_end_by_the_action_age_cap(self):
        self.assertEqual(B.ACTION_PRESENTATION_MS, 1200)
        self.assertTrue(all(ms <= B.ACTION_PRESENTATION_MS for ms in P.CLIP_MAX_MS.values()))

    def test_targets_are_orthonormal_frames(self):
        for i in range(4):
            for _, steps in P.actions(i):
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


class Gates(unittest.TestCase):
    """The whole gate: every sample of every action, both paws, the props in each phase's state, triangle-exact."""

    @classmethod
    def setUpClass(cls):
        cls.report = {B.STATIONS[i][0]: P.check(i, clearance=True, every=1) for i in range(4)}

    def test_every_action_passes_from_the_craft_stand(self):
        for sid, actions in self.report.items():
            for name, r in actions.items():
                self.assertTrue(r["ok"], (sid, name, r["fail"]))
                self.assertLessEqual(r["worst"]["reach_pct"], 98.0)
                self.assertLessEqual(r["worst"]["wrist_deg"], P.WRIST_MAX)
                self.assertLessEqual(r["worst"]["elbow_flex_deg"], P.ELBOW_MAX)
                self.assertGreaterEqual(r["worst"]["clear_cm"], P.CLEAR_CM)
                self.assertLessEqual(r["worst"]["elbow_step_cm"], P.ELBOW_STEP_CM)

    def test_crouch_is_reported_not_qualified(self):
        for i in range(4):
            rows = P.crouched(i)
            self.assertTrue(rows)
            self.assertFalse(any(r["ok"] for r in rows.values()), B.STATIONS[i][0])   # the crouched eye is 68 cm lower

    def test_the_envelope_holds_the_craft_stand(self):
        for i in (0, 3):
            env = P.envelope(i)
            self.assertIn((float(B.craft_stand(i)[0]), 0.0, 0.0), env, B.STATIONS[i][0])


class ContactView(unittest.TestCase):
    """The hero must see the active contact, both paws and what they work, through every working sample, from the craft
    stand at the natural look (contact_view). Required everywhere; the OPEN ones fail today (Coordination 252) and are
    kept as expected failures until the view repair (B09_CRAFT_PAWS.md) lands."""

    # Open: each stroke's sample at the bottom mouth, under the lantern's lower bulge (33 of 34 seen at both aspects
    # since the view repair). The rim clip, open until the view repair, is required again.
    OPEN = {("st_b09_paste_bench", "paste a panel", "16:9"), ("st_b09_paste_bench", "paste a panel", "21:9"),
            ("st_b09_oil_rack", "oil the lantern", "16:9"), ("st_b09_oil_rack", "oil the lantern", "21:9")}

    @classmethod
    def setUpClass(cls):
        cls.view = {B.STATIONS[i][0]: P.contact_view(i) for i in range(4)}

    def _open(self, sid, name, aspect):
        return any(sid == s and name.startswith(n) and aspect == a for s, n, a in self.OPEN)

    def test_every_other_action_keeps_its_contact_in_frame(self):
        for sid, actions in self.view.items():
            for name, rows in actions.items():
                for aspect, r in rows.items():
                    if not self._open(sid, name, aspect):
                        self.assertEqual(r["in_frame"], r["samples"], (sid, name, aspect, r))

    def _all_seen(self, sid, prefix, aspect):
        r = next(rows[aspect] for name, rows in self.view[sid].items() if name.startswith(prefix))
        self.assertEqual(r["in_frame"], r["samples"], r)

    @unittest.expectedFailure
    def test_open_paste_contact_at_16_9(self):
        self._all_seen("st_b09_paste_bench", "paste a panel", "16:9")

    @unittest.expectedFailure
    def test_open_paste_contact_at_21_9(self):
        self._all_seen("st_b09_paste_bench", "paste a panel", "21:9")

    def test_the_rim_clip_contact_is_seen(self):                       # closed by the view repair (was open)
        self._all_seen("st_b09_paste_bench", "seat the rims", "16:9")
        self._all_seen("st_b09_paste_bench", "seat the rims", "21:9")

    def test_only_the_bottom_mouth_sample_is_hidden(self):
        for sid, prefix in (("st_b09_paste_bench", "paste a panel"), ("st_b09_oil_rack", "oil the lantern")):
            for aspect in B.ASPECTS:
                r = next(rows[aspect] for name, rows in self.view[sid].items() if name.startswith(prefix))
                self.assertEqual((r["samples"] - r["in_frame"], r["occluded"]), (1, 1), (sid, aspect, r))

    @unittest.expectedFailure
    def test_open_oil_contact_at_16_9(self):                     # the lowest strokes behind the lantern's belly
        self._all_seen("st_b09_oil_rack", "oil the lantern", "16:9")

    @unittest.expectedFailure
    def test_open_oil_contact_at_21_9(self):
        self._all_seen("st_b09_oil_rack", "oil the lantern", "21:9")


class WorkingRegion(unittest.TestCase):
    """Root's usability requirement (Coordination 259): the admitted stands must include the natural stop against the
    proxy, with practical depth, lateral room and yaw, from ordinary keyboard and controller walking. Proposed target,
    for root to confirm: 22 cm deep (one 30 Hz frame at 660 cm/s), +-15 cm lateral, +-15 deg yaw, every action passing
    at the region's corners, edges and centre. It is OPEN: today's envelopes are 0-4 cm deep."""

    DEPTHS, LATERALS, YAWS = (0.0, -11.0, -22.0), (-15.0, 0.0, 15.0), (-15.0, 0.0, 15.0)

    def _region_ok(self, i):
        base = B.craft_stand(i)
        return all(all(r["ok"] for r in P.check(i, base + [dx, dy, 0.0], yaw, clearance=False).values())
                   for dx in self.DEPTHS for dy in self.LATERALS for yaw in self.YAWS)

    def test_the_natural_stop_itself_passes(self):
        for i in range(4):
            self.assertTrue(all(r["ok"] for r in P.check(i, B.craft_stand(i), 0.0, clearance=False).values()), i)

    @unittest.expectedFailure
    def test_open_a_practical_region_at_every_station(self):
        self.assertTrue(all(self._region_ok(i) for i in range(4)))


if __name__ == "__main__":
    unittest.main()
