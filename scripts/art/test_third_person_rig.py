"""Tests for the third-person grip contract's math (third_person_rig).

Run: python3 -m unittest scripts/art/test_third_person_rig.py

- Blender metres and Unreal cm convert both ways, Y flipped.
- frame() is a proper rotation with the X it was given.
- The contract's stances derive the Grip_R and kissaki its table records.
- two_bone keeps both lengths, bends toward the pole, and refuses a wrist out of reach (above 98 %) or too close.
- hand_pose puts the socket exactly on its target.
- segment_distance matches a direct computation.
- keyed_stance rests on each key, eases between them, keeps its poles unit, and refuses a time outside [0, 1].
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import third_person_rig as T  # noqa: E402


class Frames(unittest.TestCase):
    def test_conversion_round_trip(self):
        p = np.array([12.5, -47.2, 79.1])
        self.assertTrue(np.allclose(T.blender_to_ue_point(T.ue_to_blender_point(p)), p))
        self.assertTrue(np.allclose(T.ue_to_blender_point(p), [0.125, 0.472, 0.791]))   # Unreal's left is Blender +Y

    def test_frame_is_a_rotation(self):
        r = T.frame([1.0, 0.2, 0.1], [0.0, 0.3, 1.0])
        self.assertTrue(np.allclose(r.T @ r, np.eye(3)))
        self.assertAlmostEqual(float(np.linalg.det(r)), 1.0, places=12)
        self.assertTrue(np.allclose(r[:, 0], T.unit([1.0, 0.2, 0.1])))


class GearSockets(unittest.TestCase):
    def test_frotator_matches_the_viewmodel_checks(self):
        import check_viewmodel_framing as F
        for pyr in ((0.0, 180.0, 0.0), (-14.0, 0.0, 0.0), (0.0, 0.0, 32.0), (12.0, -37.0, 51.0)):
            self.assertTrue(np.allclose(T.frotator_rows(*pyr), np.array(F.rotation(*pyr))), pyr)

    def test_gear_saya_l_in_blender(self):
        """viewmodels.json's planned saya socket: koiguchi forward at the left hip (Blender +Y), the saya's X trailing
        back, its Z up."""
        pos, rot = T.gear_socket_blender({"bind_component_cm": [17.0, -25.0, 95.0], "rotation_deg": [0.0, 180.0, 0.0]})
        self.assertTrue(np.allclose(pos, [0.17, 0.25, 0.95]))
        self.assertTrue(np.allclose(rot[:, 0], [-1.0, 0.0, 0.0]))
        self.assertTrue(np.allclose(rot[:, 2], [0.0, 0.0, 1.0]))
        self.assertAlmostEqual(float(np.linalg.det(rot)), 1.0, places=12)

    def test_socket_targets(self):
        """Two paws: Grip_R lies 14.242 cm up the blade from Grip_L. One paw: the right on its target, the left paw
        upright, and breath lifts both."""
        two = T.socket_targets({"grip_l": (24.0, 0.0, 100.0), "elevation_deg": 30.0})
        d = T.blender_to_ue_point(two["R"][0]) - T.blender_to_ue_point(two["L"][0])
        self.assertAlmostEqual(float(np.linalg.norm(d)), 14.242, places=9)
        self.assertAlmostEqual(math.degrees(math.asin(d[2] / np.linalg.norm(d))), 30.0, places=9)
        one = T.socket_targets({"grip_r": (40.0, 18.0, 110.0), "elevation_deg": 30.0, "yaw_deg": -15.0,
                                "left_paw": (20.0, -34.0, 92.0)}, breath=0.004)
        self.assertTrue(np.allclose(T.blender_to_ue_point(one["R"][0]), [40.0, 18.0, 110.4]))
        self.assertTrue(np.allclose(T.blender_to_ue_point(one["L"][0]), [20.0, -34.0, 92.4]))
        x = T.flip_y(one["R"][1][:, 0])                       # the blade's X back in Unreal axes: turned in
        self.assertAlmostEqual(math.degrees(math.atan2(x[1], x[0])), -15.0, places=9)


class Stances(unittest.TestCase):
    def test_the_contracts_table(self):
        # THIRD_PERSON_GRIP_CONTRACT.md section 4.5.
        want = {"guard": ((36.3, 0, 107.1), (103.5, 0, 154.7)), "raise": ((32.5, 0, 142.0), (39.2, 0, 224.1)),
                "hit": ((36.2, 0, 106.8), (118.5, 0, 107.2))}
        for name, (gr, kissaki) in want.items():
            t = T.stance_targets(name)
            self.assertTrue(np.allclose(t["grip_r"], gr, atol=0.06), (name, t["grip_r"]))
            self.assertTrue(np.allclose(t["kissaki"], kissaki, atol=0.06), (name, t["kissaki"]))
            self.assertAlmostEqual(float(np.linalg.norm(t["grip_r"] - t["grip_l"])), 14.242, places=9)

    def test_scale(self):
        a, b = T.stance_targets("guard"), T.stance_targets("guard", 1.08)
        self.assertTrue(np.allclose(b["grip_r"], 1.08 * a["grip_r"]))


class Solve(unittest.TestCase):
    def test_two_bone_keeps_lengths_and_bends_to_the_pole(self):
        s, w = np.array([0.0, -0.277, 1.275]), np.array([0.25, -0.12, 1.10])
        a, b = 0.21, 0.20
        e = T.two_bone(s, w, a, b, pole=[0.0, -1.0, -1.0])
        self.assertAlmostEqual(float(np.linalg.norm(e - s)), a, places=9)
        self.assertAlmostEqual(float(np.linalg.norm(w - e)), b, places=9)
        mid = (s + w) / 2
        self.assertGreater(float(np.dot(e - mid, [0.0, -1.0, -1.0])), 0.0)

    def test_two_bone_refuses_out_of_reach_and_too_close(self):
        s = np.zeros(3)
        with self.assertRaises(ValueError):
            T.two_bone(s, [0.0, 0.0, 0.99 * 0.41], 0.21, 0.20, [1, 0, 0])
        with self.assertRaises(ValueError):
            T.two_bone(s, [0.0, 0.0, 0.005], 0.21, 0.20, [1, 0, 0])

    def test_hand_pose_lands_the_socket(self):
        rng = np.random.default_rng(1)
        sock, wrist = np.array([0.158, -0.474, 0.748]), np.array([0.092, -0.467, 0.887])
        r0 = T.frame([0, -1, 0], [-0.589, 0, 0.808])
        x, z = T.blade_axes(30.0)
        target_rot = T.frame(x, z)
        target = rng.random(3)
        R, w = T.hand_pose(sock, r0, wrist, target, target_rot)
        self.assertTrue(np.allclose(w + R @ (sock - wrist), target))
        self.assertTrue(np.allclose(R @ r0, target_rot))

    def test_segment_distance(self):
        d = T.segment_distance([0, 0, 0], [1, 0, 0], [[0.5, 0.2, 0], [2.0, 0, 0], [-1.0, 0, 1.0]])
        self.assertTrue(np.allclose(d, [0.2, 1.0, math.sqrt(2.0)]))


class KeyedStance(unittest.TestCase):
    KEYS = [{"grip_l": (34.0, 0.0, 106.0), "elevation_deg": 30.0, "poles": {"R": (1.0, -0.6, -0.5), "L": (1.0, 0.6, -0.5)}},
            {"grip_l": (40.0, 0.0, 130.0), "elevation_deg": 80.0, "poles": {"R": (0.4, -1.0, -0.6), "L": (0.4, 1.0, -0.6)}},
            {"grip_l": (34.0, 0.0, 106.0), "elevation_deg": 30.0, "poles": {"R": (1.0, -0.6, -0.5), "L": (1.0, 0.6, -0.5)}}]
    TIMES = (0.0, 0.4, 1.0)

    def test_rests_on_each_key(self):
        for key, u in zip(self.KEYS, self.TIMES):
            s = T.keyed_stance(self.KEYS, self.TIMES, u)
            self.assertTrue(np.allclose(s["grip_l"], key["grip_l"]))
            self.assertAlmostEqual(s["elevation_deg"], key["elevation_deg"])
            for side in ("R", "L"):
                self.assertTrue(np.allclose(s["poles"][side], T.unit(key["poles"][side])))

    def test_eases_between_keys(self):
        mid = T.keyed_stance(self.KEYS, self.TIMES, 0.2)
        self.assertAlmostEqual(mid["elevation_deg"], 55.0)
        early = T.keyed_stance(self.KEYS, self.TIMES, 0.02)
        self.assertLess(early["elevation_deg"] - 30.0, 0.05 * 50.0)     # slow out of the key
        for side in ("R", "L"):
            self.assertAlmostEqual(float(np.linalg.norm(mid["poles"][side])), 1.0)

    def test_refuses_time_outside(self):
        with self.assertRaises(ValueError):
            T.keyed_stance(self.KEYS, self.TIMES, 1.01)


if __name__ == "__main__":
    unittest.main()
