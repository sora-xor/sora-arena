"""Tests for yumi_fp_raster: the whole-bow screen pixels, and the clear-reticle candidate they support.

Run: python3 -m unittest scripts/art/test_yumi_fp_raster.py

- The raster's camera, disc and near-plane clip, on synthetic triangles.
- The CPU rig poses the committed review's full-draw nock.
- On tracked data only (the rig's check geometry, the review's sockets and
  the hold study):
  - right_cheek's stave covers the reticle disc, as capture v3 showed
    (4,956 px captured, about 5,000 rasterised);
  - the study's right_cheek_clear keeps the bow, the arrow and the paw out of
    it by at least MARGIN_PX.
  A capture's ID pass must still confirm it.
"""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import yumi_draw as Y  # noqa: E402
import yumi_fp_holds as H  # noqa: E402
import yumi_fp_raster as R  # noqa: E402

STUDY = ROOT / "docs/art-direction/data/yumi_fp_hold_study.json"
ARROW = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi/Rig/Review/W18_rig_review_arrow.json"
W, HGT = 1920, 1080
MARGIN_PX = 5                         # the raster's whole-pixel edges against a capture's resolved ones, with room


class Camera(unittest.TestCase):
    def test_the_disc_is_the_analysis_disc(self):
        # analyse_yumi_fp_review measured 13,200 disc pixels at 1920 x 1080 and radius 0.12 (capture v3).
        self.assertEqual(int(R.disc(W, HGT, 0.12).sum()), 13200)

    def test_a_triangle_on_the_view_axis_covers_the_centre(self):
        tri = np.array([[[100.0, -5.0, -5.0], [100.0, 5.0, -5.0], [100.0, 0.0, 5.0]]])
        m = R.raster(tri, 70.0, 16 / 9, W, HGT)
        self.assertTrue(m[HGT // 2, W // 2])
        self.assertAlmostEqual(R.clearance(m, W, HGT), 0.0, delta=2.0 / HGT)

    def test_a_triangle_behind_the_near_plane_draws_nothing_and_one_across_it_is_clipped(self):
        behind = np.array([[[5.0, -1.0, -1.0], [5.0, 1.0, -1.0], [5.0, 0.0, 1.0]]])
        self.assertEqual(int(R.raster(behind, 70.0, 16 / 9, W, HGT).sum()), 0)
        across = np.array([[[5.0, 2.0, -1.0], [50.0, 2.0, -1.0], [50.0, 2.0, 1.0]]])
        self.assertGreater(int(R.raster(across, 70.0, 16 / 9, W, HGT).sum()), 0)

    def test_nothing_covered_has_infinite_clearance(self):
        self.assertEqual(R.clearance(np.zeros((HGT, W), bool), W, HGT), float("inf"))


class Rig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig = Y.load_rig()
        cls.study = json.loads(STUDY.read_text(encoding="utf-8"))
        full = json.loads(ARROW.read_text(encoding="utf-8"))["states"]["Full"]
        cls.full = full
        cls.grip_r = tuple(100.0 * np.array(full["nock_m"]) * np.array([1.0, -1.0, 1.0]))
        cls.muzzle = tuple(100.0 * np.array(full["muzzle_m"]) * np.array([1.0, -1.0, 1.0]))
        c = cls.study["root_control"]
        cls.cam, cls.scale = c["camera"], c["mesh_scale"]
        cls.rc = H.right_cheek(tuple(c["anchor_cm"]), tuple(c["rotation_deg"]), cls.scale, cls.grip_r, cls.muzzle)

    def test_the_cpu_rig_poses_the_reviews_full_draw_nock(self):
        grip_r, muzzle = R.posed_sockets_m(self.rig, 1.0)
        self.assertLess(float(np.abs(grip_r - np.array(self.full["nock_m"])).max()), 1e-6)
        self.assertLess(float(np.abs(muzzle - np.array(self.full["muzzle_m"])).max()), 1e-6)

    def test_right_cheeks_stave_covers_the_reticle_disc(self):
        res = R.hold_pixels(self.rig, self.rc["anchor"], self.rc["rot"], self.scale, self.cam, W, HGT, 1.0)
        self.assertGreater(res["bow"]["in_disc"], 4000)
        self.assertLess(res["bow"]["clearance"], self.cam["reticle_clear_radius"])

    def test_the_clear_candidate_keeps_every_part_out_of_the_disc(self):
        c = self.study["right_cheek_clear"]
        h = H.cheek_hold(tuple(c["nock_target_cm"]), c["cant_right_deg"], self.scale, self.grip_r, self.muzzle,
                         tuple(c["aim_cm"]))
        res = R.hold_pixels(self.rig, h["anchor"], h["rot"], self.scale, self.cam, W, HGT, 1.0)
        need = self.cam["reticle_clear_radius"] + MARGIN_PX / (HGT / 2)
        for part in ("bow", "arrow", "paw"):
            self.assertEqual(res[part]["in_disc"], 0, part)
            self.assertGreaterEqual(res[part]["clearance"], need, part)
        self.assertLess(max(abs(m) for m in h["aim_miss_cm"]), 1e-9)
        self.assertEqual(res["bow"]["in_disc"], c["cpu_raster"]["in_disc"]["bow"])       # as the study records


if __name__ == "__main__":
    unittest.main()
