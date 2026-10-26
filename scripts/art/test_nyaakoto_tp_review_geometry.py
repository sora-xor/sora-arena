"""Host tests: the third-person paw review's shots and camera geometry (nyaakoto_tp_review_geometry), and the planner's
visibility (plan_nyaakoto_tp_review).

Run: python3.11 -m unittest scripts/art/test_nyaakoto_tp_review_geometry.py
"""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nyaakoto_tp_review_geometry as G  # noqa: E402
import plan_nyaakoto_tp_review as PL  # noqa: E402
import third_person_rig as TP  # noqa: E402

RECORD = json.loads((HERE.parents[1] / "Content/SourceArt/Characters/Hero/runtime_skin_manifest.json").read_text())


class Shots(unittest.TestCase):
    shots = G.shots()

    def test_every_name_is_unique_and_states_its_lod(self):
        names = [s["name"] for s in self.shots]
        self.assertEqual(len(names), len(set(names)))
        for s in self.shots:
            self.assertTrue(s["name"].endswith(f"_LOD{s['lod']}"), s["name"])
            self.assertIn(s["lod"], G.LODS)

    def test_both_paws_both_views_both_states_share_one_camera_a_pair(self):
        paws = [s for s in self.shots if s["kind"] == "paw"]
        self.assertEqual(len(paws), 16)
        for pose, solo in (("guard", ""), ("rest", "_solo")):
            for side in ("R", "L"):
                for view in ("pads", "back"):
                    pair = [s for s in paws if s["pose"] == pose and s["side"] == side and s["view"] == view]
                    self.assertEqual(sorted(s["state"] for s in pair), ["empty", "holding"])
                    self.assertEqual({s["camera"] for s in pair}, {f"paw_{side}_{view}{solo}"})
                    self.assertEqual({s["lod"] for s in pair}, {0})
        self.assertTrue(all("_rest_" in s["name"] for s in paws if s["pose"] == "rest"))
        self.assertTrue(all("_rest_" not in s["name"] for s in paws if s["pose"] == "guard"))

    def test_the_rest_pose_holds_the_records_bind_sockets(self):
        tp = RECORD["third_person"]
        self.assertEqual(G.pose_stance("rest", tp), (None, 0.0))
        bind = G.bind_targets(tp)
        self.assertEqual(set(bind), set(G.SOCKETS.values()))
        for name, (pos, x, z) in bind.items():
            self.assertEqual(list(pos), tp["sockets"][name]["component_cm"])
            self.assertEqual(list(x), tp["sockets"][name]["x_axis"])

    def test_cuffs_and_the_full_guard_and_strike_with_every_lod_of_the_guard(self):
        cuffs = {(s["side"], s["view"]) for s in self.shots if s["kind"] == "cuff"}
        self.assertEqual(cuffs, {("R", "outside"), ("R", "below"), ("L", "outside"), ("L", "below")})
        body = {(s["camera"], s["lod"]) for s in self.shots if s["kind"] == "body"}
        self.assertTrue({("guard_front", 0), ("guard_front", 1), ("guard_front", 2), ("guard_side", 0)} <= body)
        self.assertEqual({s["pose"] for s in self.shots if s["kind"] == "body"}, {"guard", "raise", "hit"})


class Frames(unittest.TestCase):
    def test_axes_are_unreals_make_from_xz(self):
        x, y, z = G.axes_from_xz((0.6, 0.0, 0.8), (-0.8, 0.0, 0.6))
        for a in (x, y, z):
            self.assertAlmostEqual(G.norm(a), 1.0, places=12)
        self.assertAlmostEqual(G.dot(x, y), 0.0, places=12)
        np.testing.assert_allclose(y, G.cross(z, x), atol=1e-12)
        np.testing.assert_allclose(z, G.cross(x, y), atol=1e-12)

    def test_local_and_world_round_trip(self):
        axes = G.axes_from_xz((0.3, -0.9, 0.1), (0.1, 0.2, 0.97))
        origin, p = (10.0, -4.0, 100.0), (14.0, 3.0, 97.5)
        np.testing.assert_allclose(G.to_world(origin, axes, G.to_local(origin, axes, p)), p, atol=1e-9)
        d = G.unit((0.2, 0.5, -0.3))
        np.testing.assert_allclose(G.dir_to_world(axes, G.dir_to_local(axes, d)), d, atol=1e-12)

    def test_the_grip_offset_and_two_paw_targets_are_the_rigs(self):
        self.assertEqual(G.W00_GRIP_L_X, TP.W00["grip_l"][0])
        stance = RECORD["third_person"]["guard"]["stance"]
        mine = G.two_paw_targets(stance)
        theirs = TP.socket_targets(stance)
        for side, sock in G.SOCKETS.items():
            pos_m, rot = theirs[side]
            np.testing.assert_allclose(mine[sock][0], TP.blender_to_ue_point(pos_m), atol=1e-9)
            np.testing.assert_allclose(mine[sock][1], TP.flip_y(rot[:, 0]), atol=1e-12)
            np.testing.assert_allclose(mine[sock][2], TP.flip_y(rot[:, 2]), atol=1e-12)

    def test_the_strikes_keyed_stances_are_the_rigs(self):
        tp = RECORD["third_person"]
        stance, strike = tp["guard"]["stance"], tp["strike"]
        keys = [stance] + [strike["keys"][k] for k in ("raise", "hit", "follow")] + [stance]
        for pose in ("raise", "hit"):
            mine, u = G.pose_stance(pose, tp)
            self.assertAlmostEqual(u, (strike[f"{pose}_frame"] - 1) / strike["frames"])
            theirs = TP.keyed_stance(keys, strike["times"], u)
            np.testing.assert_allclose(mine["grip_l"], theirs["grip_l"], atol=1e-12)
            self.assertAlmostEqual(mine["elevation_deg"], theirs["elevation_deg"], places=12)
        self.assertEqual(G.pose_stance("guard", tp), (stance, 0.0))


class Distances(unittest.TestCase):
    @staticmethod
    def line(bone, a, b, step=G.VOXEL_CM):
        n = max(1, int(round(G.norm(G.sub(b, a)) / step)))
        return [(bone, G.lerp(a, b, k / n)) for k in range(n + 1)]

    def test_choose_skips_a_blocked_view_and_the_floor_and_reports_a_fallback(self):
        target = (0.0, 0.0, 100.0)
        pole = self.line("pole", (30.0, 0.0, 0.0), (30.0, 0.0, 300.0))
        cands = [{"direction": (1.0, 0.0, 0.0)}, {"direction": (0.0, 0.0, -1.0)}, {"direction": (0.0, 1.0, 0.0)}]
        row = G.choose(cands, target, 120.0, pole)
        self.assertEqual((row["rank"], row["clear"]), (2, True))         # +X through the pole, -Z under the floor
        np.testing.assert_allclose(row["camera"], (0.0, 120.0, 100.0))
        fallback = G.choose(cands[:2], target, 120.0, pole)
        self.assertEqual((fallback["rank"], fallback["clear"]), (0, False))   # one pole voxel ties the floor: rank wins
        self.assertEqual(fallback["blocked"], {"pole": 1})
        self.assertEqual(G.choose(cands[1:2], target, 120.0, pole)["blocked"], {"floor": 1})
        self.assertEqual(sorted(G.choose(cands[:1], target, 120.0, pole)["blocked"]), ["pole"])
        self.assertEqual(G.choose(cands[:1], target, 120.0, pole, skip_bones=("pole",))["clear"], True)

    def test_the_near_stretch_of_a_sight_line_is_not_tested(self):
        arm = self.line("forearm_R", (-30.0, 0.0, 100.0), (-5.0, 0.0, 100.0))
        self.assertEqual(G.blocking((0.0, 60.0, 100.0), (0.0, 0.0, 100.0), arm), {})
        self.assertIn("forearm_R", G.blocking((-60.0, 1.0, 100.0), (0.0, 0.0, 100.0), arm))

    def test_point_segment_distance(self):
        self.assertAlmostEqual(G.point_segment_distance((5.0, 3.0, 0.0), (0.0, 0.0, 0.0), (10.0, 0.0, 0.0)), 3.0)
        self.assertAlmostEqual(G.point_segment_distance((-4.0, 3.0, 0.0), (0.0, 0.0, 0.0), (10.0, 0.0, 0.0)), 5.0)
        self.assertAlmostEqual(G.point_segment_distance((1.0, 1.0, 1.0), (2.0, 2.0, 2.0), (2.0, 2.0, 2.0)), math.sqrt(3))

    def test_framing_fits_the_sphere_to_the_frames_height(self):
        aspect = 16.0 / 9.0
        r, d = 7.0, G.fit_distance(7.0, 30.0, aspect)
        self.assertAlmostEqual(r * G.FRAME_MARGIN, d * math.sin(G.vertical_half_fov(30.0, aspect)), places=9)
        cam, tgt, dist = G.body_camera("guard_side", aspect)
        self.assertAlmostEqual(G.norm(G.sub(cam, tgt)), dist, places=9)
        self.assertGreater(cam[1], 0.0)                                   # the character's right

    def test_cuff_candidates_ring_the_forearm(self):
        wrist, elbow = (34.0, 20.0, 110.0), (10.0, 35.0, 120.0)
        axis = G.unit(G.sub(wrist, elbow))
        rows = G.cuff_candidates(wrist, elbow, "R", "outside")
        self.assertEqual(len(rows), 24)
        for r in rows:
            self.assertAlmostEqual(G.norm(r["direction"]), 1.0, places=12)
            self.assertAlmostEqual(G.dot(r["direction"], axis), math.sin(math.radians(15.0)), places=9)
        self.assertGreater(rows[0]["direction"][1], 0.0)
        self.assertLess(G.cuff_candidates(wrist, elbow, "R", "below")[0]["direction"][2], 0.0)


class Visibility(unittest.TestCase):
    @staticmethod
    def square(z, size=2.0, offset=(0.0, 0.0), step=0.1):
        """A square at height z facing +z, as a grid of triangles wound counter-clockwise from above, about as fine
        against the planner's 2 mm cells as LOD0's paws (3 mm grid) are."""
        n = int(round(size / step))
        g = np.linspace(-size / 2.0, size / 2.0, n + 1)
        xx, yy = np.meshgrid(g, g, indexing="ij")
        v = np.stack([xx.ravel() + offset[0], yy.ravel() + offset[1], np.full(xx.size, z)], 1)
        idx = np.arange((n + 1) ** 2).reshape(n + 1, n + 1)
        a, b, c, d = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
        return v, np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])

    def test_a_face_is_seen_from_its_front_and_hidden_behind_another(self):
        v, t = self.square(0.0)
        c, n, _ = PL.face_geometry(v, t)
        occ = PL.splat_points(v, t)
        up = PL.depth_buffer(occ, np.array([0.0, 0.0, 1.0]))
        self.assertTrue(PL.seen(up, c, n).all())
        down = PL.depth_buffer(occ, np.array([0.0, 0.0, -1.0]))
        self.assertFalse(PL.seen(down, c, n).any())                      # facing away
        lid_v, lid_t = self.square(1.0, size=3.0)
        both = np.concatenate([occ, PL.splat_points(lid_v, lid_t)])
        self.assertFalse(PL.seen(PL.depth_buffer(both, np.array([0.0, 0.0, 1.0])), c, n).any())
        aside_v, aside_t = self.square(1.0, size=1.0, offset=(5.0, 0.0))
        both = np.concatenate([occ, PL.splat_points(aside_v, aside_t)])
        self.assertTrue(PL.seen(PL.depth_buffer(both, np.array([0.0, 0.0, 1.0])), c, n).all())

    def test_mirrored_points_keep_outward_normals_once_rewound(self):
        v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
        t = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])      # outward in Blender's axes
        c0, n0, _ = PL.face_geometry(v, t)
        self.assertTrue((np.einsum("ij,ij->i", n0, c0 - v.mean(0)) > 0).all())
        u = PL.blender_to_ue(v / 100.0)
        c, n, _ = PL.face_geometry(u, PL.ue_tris(t))
        self.assertTrue((np.einsum("ij,ij->i", n, c - u.mean(0)) > 0).all())
        _, inward, _ = PL.face_geometry(u, t)
        self.assertTrue((np.einsum("ij,ij->i", inward, c - u.mean(0)) < 0).all())

    def test_directions_are_unit_and_never_near_vertical(self):
        d = PL.fibonacci_directions(500)
        np.testing.assert_allclose(np.linalg.norm(d, axis=1), 1.0, atol=1e-12)
        self.assertLessEqual(np.abs(d[:, 2]).max(), PL.MAX_UP + 1e-12)
        self.assertGreater(len(d), 400)

    def test_ranked_directions_are_apart_and_in_order(self):
        d = PL.fibonacci_directions(800)
        joint = d @ G.unit((0.3, 0.4, 0.2))
        stats = {"holding": {"score": joint}, "empty": {"score": joint}}
        rows = PL.ranked(joint, d, stats, np.eye(3))
        self.assertGreater(len(rows), 50)
        self.assertLessEqual(len(rows), PL.CANDIDATES)
        self.assertGreaterEqual(min(r["joint"] for r in rows), round(PL.MIN_JOINT, 4))
        self.assertEqual([r["joint"] for r in rows], sorted((r["joint"] for r in rows), reverse=True))
        dirs = np.array([r["direction"] for r in rows])
        cos = dirs @ dirs.T - 2.0 * np.eye(len(dirs))
        self.assertLessEqual(cos.max(), PL.SEPARATION + 1e-5)


if __name__ == "__main__":
    unittest.main()
