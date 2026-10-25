"""Tests for the first-person review holds (yumi_fp_holds) and their study data.

Run: python3 -m unittest scripts/art/test_yumi_fp_holds.py

Socket math only, as yumi_fp_holds says. These pin:
- its conventions to check_viewmodel_framing's;
- its right_cheek solve to Codex's candidate, from the committed full-draw
  sockets (W18_rig_review_arrow.json, signed 15d67ad);
- the arrow line through the aim point;
- that root's left-side screen boxes do not admit right_cheek's grip. That is
  recorded, not relaxed (the candidate's own limitations).
"""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import check_viewmodel_framing as F  # noqa: E402
import yumi_fp_holds as H  # noqa: E402

STUDY = ROOT / "docs/art-direction/data/yumi_fp_hold_study.json"
ARROW = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi/Rig/Review/W18_rig_review_arrow.json"


def cm(m):
    return (100.0 * m[0], -100.0 * m[1], 100.0 * m[2])


class Holds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study = json.loads(STUDY.read_text(encoding="utf-8"))
        full = json.loads(ARROW.read_text(encoding="utf-8"))["states"]["Full"]
        cls.grip_r, cls.muzzle = cm(full["nock_m"]), cm(full["muzzle_m"])
        c = cls.study["root_control"]
        cls.control = (tuple(c["anchor_cm"]), tuple(c["rotation_deg"]), c["mesh_scale"])
        cls.rc = H.right_cheek(*cls.control, cls.grip_r, cls.muzzle)

    def test_the_conventions_are_the_framing_checkers(self):
        for rot in ((0.25, 0.1, 0.0), (0.17, -1.36, 0.0), (12.0, -30.0, 7.5)):
            self.assertEqual(H.rotation(*rot), F.rotation(*rot))
            v = (1.5, -2.0, 0.25)
            self.assertEqual(H.apply(H.rotation(*rot), v), F.apply(F.rotation(*rot), v))
        self.assertEqual(F.to_ue_cm((0.1, 0.2, 0.3)), cm((0.1, 0.2, 0.3)))

    def test_the_solve_reproduces_the_candidate_for_these_sockets(self):
        # Codex's candidate was solved from the signed 15d67ad sockets. If a rebuild changes
        # the sockets file, the study must carry a candidate recomputed for its hash
        # (right_cheek.recomputed), and the solve must reproduce that: never a stale one.
        import hashlib
        digest = hashlib.sha256(ARROW.read_bytes()).hexdigest()
        rc = self.study["right_cheek"]
        cands = [rc["codex_candidate"]] + rc.get("recomputed", [])
        match = [c for c in cands if c["sockets_source_sha256"] == digest]
        self.assertEqual(len(match), 1, f"no right_cheek candidate for sockets {digest[:12]}: recompute it")
        for got, want in zip(self.rc["anchor"], match[0]["anchor_cm"]):
            self.assertAlmostEqual(got, want, places=9)
        for got, want in zip(self.rc["rot"], match[0]["rotation_deg"]):
            self.assertAlmostEqual(got, want, places=9)

    def test_the_target_mirrors_the_controls_nock(self):
        n, t = self.rc["control_nock"], self.rc["target_nock"]
        self.assertEqual((t[0], t[2]), (n[0], n[2]))
        self.assertEqual(t[1], -n[1])
        self.assertGreater(t[1], 0.0)                                   # right of the eye
        for got, want in zip(self.rc["posed"]["Grip_R"], t):
            self.assertAlmostEqual(got, want, places=9)

    def test_the_arrow_line_passes_through_the_aim_point(self):
        dy, dz = self.rc["aim_miss_cm"]
        self.assertLess(math.hypot(dy, dz), 1e-9)
        self.assertEqual(self.rc["rot"][2], 0.0)

    def test_roots_left_side_box_does_not_admit_the_right_cheek_grip(self):
        c = self.study["root_control"]
        cam = c["camera"]
        aspect = cam["aspect"][0] / cam["aspect"][1]
        uv = H.screen_uv(self.rc["posed"]["Grip_L"], cam["first_person_fov_deg"], aspect)
        self.assertGreater(uv[0], 0.0)
        self.assertFalse(H.in_box(uv, c["screen"]["Grip_L"]))
        control_uv = H.screen_uv(tuple(c["anchor_cm"]), cam["first_person_fov_deg"], aspect)
        self.assertTrue(H.in_box(control_uv, c["screen"]["Grip_L"]))      # the control's own grip is admitted

    def test_the_drawn_nock_is_behind_the_near_plane_in_both(self):
        # Socket math: the full-draw nock is 5.8 cm behind the eye in the control, and so in
        # right_cheek, so the arrow's rear crosses the 10 cm near plane. Originals show how much.
        near = self.study["root_control"]["camera"]["near_plane_cm"]
        for posed in (H.place(*self.control, self.grip_r), self.rc["posed"]["Grip_R"]):
            self.assertLess(posed[0], 0.0)
        f = H.segment_behind(self.rc["posed"]["Grip_R"], self.rc["posed"]["Muzzle"], near)
        self.assertTrue(0.0 < f < 1.0)

    def test_segment_behind(self):
        self.assertEqual(H.segment_behind((20, 0, 0), (30, 0, 0), 10.0), 0.0)
        self.assertEqual(H.segment_behind((0, 0, 0), (5, 0, 0), 10.0), 1.0)
        self.assertAlmostEqual(H.segment_behind((0, 0, 0), (20, 0, 0), 10.0), 0.5)
        self.assertAlmostEqual(H.segment_behind((20, 0, 0), (0, 0, 0), 10.0), 0.5)


if __name__ == "__main__":
    unittest.main()
