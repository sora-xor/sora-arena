"""Tests for yumi_draw: the bow model, the full draw, the rig and the first-person envelopes.

Run: python3 -m unittest scripts/art/test_yumi_draw.py

Numpy and the standard library; about a minute. It proves:
* the model reproduces the committed SM_Weapon_18 sockets and string;
* the full draw keeps the string's length, and puts the arrow's point 10 cm
  past the grip;
* the string never stretches through draw and release, and a draw past brace
  is refused (Codex's review of fa6aa2b: the old overshoot added 1.87 mm);
* the continuous rig (RIG_BONES) holds the stave within 2 mm of the solved
  shape through the draw;
* the envelopes are closed and conservative: capsules with end caps, the
  stave containing the generator's own section, and the batch placement
  equal to the checker's;
* geometry behind the camera never passes, and a near-plane cut inside the
  frame is reported;
* the authored kai pose (60, -6, -14), with the pose following the draw,
  keeps every envelope outside the reticle radius in rest and both bobs,
  through draw, hold and release. Its residual is reported, not hidden: the
  draw paw's forearm crosses the near plane in the frame's bottom-left
  region (u <= -0.82, v <= -0.74) for 10 sampled frames (0.17 s) early in the
  draw.

Everything here is a sampled design envelope (yumi_draw.SCOPE), not the
emitted or skinned asset, continuous time, or the native camera path.
"""
from __future__ import annotations

import json
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yumi_draw as Y  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi/build_record.json"


def contract():
    return json.loads(Y.F.CONTRACT.read_text())


class Model(unittest.TestCase):
    def test_reproduces_the_committed_sockets(self):
        committed = json.loads(RECORD.read_text())["assets"]["SM_Weapon_18"]["sockets"]
        built = Y.braced()["sockets"]
        for name, want in committed.items():
            for a, b in zip(built[name], want):
                self.assertAlmostEqual(a, b, places=5, msg=name)
        notes = json.loads(RECORD.read_text())["notes"]
        self.assertAlmostEqual(Y.braced()["string_m"], notes["string_chord_m"], places=4)
        self.assertEqual((Y.LENGTH, Y.BRACE), (notes["bow_length_m"], notes["brace_height_m"]))

    def test_full_draw_keeps_the_string_and_the_arrow_length(self):
        dr = Y.drawn()
        self.assertAlmostEqual(dr["string_m"], Y.braced()["string_m"], places=6)
        nock, tip = dr["arrow"]
        self.assertEqual(nock, (-Y.DRAW_M, 0.0, Y.NOCK_Z))
        self.assertAlmostEqual(math.dist(tip, nock), Y.ARROW_M, places=9)
        self.assertTrue(0.09 <= tip[0] <= 0.11, tip)           # the point 10 cm past the grip
        br = Y.braced()["sockets"]
        self.assertLess(dr["sockets"]["String_Upper"][0], br["String_Upper"][0])
        self.assertLess(dr["sockets"]["String_Lower"][0], br["String_Lower"][0])

    def test_the_string_never_stretches_and_never_passes_brace(self):
        length = Y.braced()["string_m"]
        tl = Y.timeline(fps=30.0)
        self.assertLess(max(abs(fr["string_m"] - length) for fr in tl["frames"]), 1e-6)
        self.assertGreaterEqual(min(fr["draw"] for fr in tl["frames"]), 0.0)
        with self.assertRaises(ValueError):
            Y.shape_at(-0.06)
        with self.assertRaises(ValueError):
            Y.shape_at(1.1)

    def test_the_rig_holds_the_stave_through_the_draw(self):
        for d in (0.05, 0.25, 0.5, 0.75, 1.0):
            e = Y.skinning_error(d)
            self.assertLess(e["upper"], 0.002, d)
            self.assertLess(e["lower"], 0.002, d)


class Envelopes(unittest.TestCase):
    def test_capsules_are_closed(self):
        rings = Y._capsule((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 0.5)
        xs = [p[0] for ring in rings for p in ring]
        self.assertAlmostEqual(min(xs), -0.5, places=9)
        self.assertAlmostEqual(max(xs), 1.5, places=9)
        sphere = Y._sphere((0.0, 0.0, 0.0), 0.045)
        self.assertAlmostEqual(max(abs(p[2]) for ring in sphere for p in ring), 0.045, places=9)
        # A zero-length capsule is a sphere, not a degenerate cylinder.
        self.assertEqual(Y._capsule((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.1)[0], Y._sphere((0.0, 0.0, 0.0), 0.1, 12, 16)[0])

    def test_the_stave_envelope_contains_the_generators_section(self):
        shape = Y.braced()
        rings = Y._stave_envelope(shape, every=1)
        frames = Y._frames(shape["low"], shape["up"])
        for i in (0, len(frames) // 4, len(frames) // 2, 3 * len(frames) // 4, len(frames) - 1):
            sig, p, _t, n = frames[i]
            w, d = Y.thickness(sig)
            ring = rings[i]
            half_w = max(abs(q[1] - p[1]) for q in ring)
            half_d = max(abs((q[0] - p[0]) * n[0] + (q[2] - p[2]) * n[2]) for q in ring)
            rem = min(sig + Y.L_LOW, Y.L_UP - sig)
            taper = 0.62 + 0.38 * rem / 0.035 if rem < 0.035 else 1.0
            self.assertGreaterEqual(half_w + 1e-12, w * taper / 2, sig)
            self.assertGreaterEqual(half_d + 1e-12, d * taper / 2, sig)
            self.assertEqual(len(ring), Y.STAVE_SECTION_POINTS)

    def test_ring_edges_close_last_to_first(self):
        # Codex's counterexample on 4481327: a ring whose last edge crosses the
        # near plane counted no cut, but did once its first point was repeated.
        import numpy as np
        screen = Y.F.Screen(contract()["camera"])
        near_x = screen.near / screen.scale
        ring = [(30.0, 1.0, 0.0), (30.0, 0.0, 1.0), (30.0, -1.0, 0.0), (5.0, 0.0, -1.0)]
        implicit, _ = Y.near_cuts(np.array([ring]), near_x, screen)
        explicit, _ = Y.near_cuts(np.array([ring + [ring[0]]]), near_x, screen)
        self.assertEqual(implicit, 2)                # into and out of the point behind the plane
        self.assertEqual(explicit, implicit)         # repeating the first point adds only a zero-length edge
        E = np.array([ring])
        unclosed = int(np.sum((E[:, :-1, 0] > near_x) != (E[:, 1:, 0] > near_x)))
        self.assertEqual(unclosed, 1)                # 4481327's traversal saw only one of the two

    def test_batch_placement_equals_the_checker(self):
        c = contract()
        rest = c["poses"]["bow.drawn"]["rest"]
        rng = random.Random(7)
        pts = [(rng.uniform(-1, 1), rng.uniform(-0.2, 0.2), rng.uniform(-0.8, 1.5)) for _ in range(50)]
        for state_name in ("rest", "bob_up_right", "reload"):
            state = c["envelopes"]["states"][state_name]
            batch = Y.place_many(rest, pts, c["mesh_scale"], state)
            sockets = {"Grip_L": (0.0, 0.0, 0.0), **{f"p{i}": p for i, p in enumerate(pts)}}
            ref, _q = Y.F.place(rest, sockets, "Grip_L", c["mesh_scale"], state)
            for i in range(len(pts)):
                for k in range(3):
                    self.assertAlmostEqual(batch[i][k], ref[f"p{i}"][k], places=9)


class FirstPerson(unittest.TestCase):
    def test_geometry_behind_the_camera_never_passes(self):
        c = contract()
        c["poses"]["bow.drawn"]["rest"]["anchor_cm"] = [-200.0, -6.0, -14.0]
        fp = Y.footprint("bow.drawn", contract=c)
        self.assertFalse(fp["clear"])
        self.assertEqual(set(fp["missing"]), {"stave", "arrow", "paw_L"})
        self.assertTrue(all(p["in_front"] == 0.0 for p in fp["parts"].values()))

    def test_the_old_high_hold_cuts_the_arrow_inside_the_frame(self):
        c = contract()
        c["poses"]["bow.drawn"]["rest"]["anchor_cm"] = [60.0, -5.0, -9.5]
        fp = Y.footprint("bow.drawn", contract=c)
        self.assertGreater(fp["parts"]["arrow"]["near_clip_in_frame"], 0)
        self.assertFalse(fp["clear"])

    def test_the_authored_kai_pose_keeps_every_envelope_clear(self):
        c = contract()
        self.assertEqual(c["poses"]["bow.drawn"]["rest"]["anchor_cm"], [60.0, -6.0, -14.0])
        fp = Y.footprint("bow.drawn", contract=c)
        self.assertTrue(fp["clear"], fp)
        tl = Y.timeline(contract=c, pose_follows_draw=True)
        sm = Y.summary(tl)
        self.assertEqual(set(sm), {"stave", "string", "arrow", "paw_L", "paw_R"})
        residual = {("paw_R", "draw"): 10, ("arrow", "draw"): 10}
        for part, phases in sm.items():
            for phase, v in phases.items():
                self.assertGreaterEqual(v["nearest"], 0.12, (part, phase, v))
                self.assertEqual(v["inside_s"], 0.0, (part, phase))
                self.assertEqual(v["hidden_frames"], 0, (part, phase))
                self.assertEqual(v["near_clip_frames"], residual.get((part, phase), 0), (part, phase))
        # The residual cuts, exact in count and bounded over every cut point
        # (not display examples): early in the draw, the draw paw's forearm and
        # the conservative fletching envelope, in the frame's bottom-left region.
        u0, u1, v0, v1 = sm["paw_R"]["draw"]["clip_box"]
        self.assertTrue(u1 <= -0.8 and v1 <= -0.7, sm["paw_R"]["draw"]["clip_box"])
        u0, u1, v0, v1 = sm["arrow"]["draw"]["clip_box"]
        self.assertTrue(u1 <= -0.75 and v1 <= -0.8, sm["arrow"]["draw"]["clip_box"])

    def test_todays_high_hold_puts_the_stave_in_the_clear_zone(self):
        sm = Y.summary(Y.timeline(anchor_y=-3.0, anchor_z=-9.5, pose_follows_draw=True, fps=30.0))
        self.assertLess(sm["stave"]["hold"]["nearest"], 0.12)

    def test_without_the_draw_led_pose_the_string_is_cut_mid_frame(self):
        # Blending to bow.drawn at once (today's runtime) brings the string past
        # the face inside the near plane, mid-frame. Following the draw leaves
        # only the draw paw's forearm at the frame's corner.
        def cuts(tl, part):
            return [pt for fr in tl["frames"] for pt in fr["parts"][part]["clip_points"]]
        ahead = Y.timeline(pose_follows_draw=False)
        follow = Y.timeline(pose_follows_draw=True)
        mid = [pt for pt in cuts(ahead, "string") if abs(pt[0]) < 0.9 and abs(pt[1]) < 0.9]
        self.assertTrue(mid, cuts(ahead, "string"))
        self.assertEqual(cuts(follow, "string"), [])

    def test_summary_counts_every_cut_even_when_a_part_is_not_visible(self):
        # Codex's review of 4481327: cuts were skipped on frames where the part was not visible.
        tl = Y.timeline(pose_follows_draw=True)
        direct = sum(1 for fr in tl["frames"] if fr["parts"]["paw_R"]["near_clip_in_frame"])
        sm = Y.summary(tl)
        self.assertEqual(sum(v["near_clip_frames"] for v in sm["paw_R"].values()), direct)

    def test_every_report_states_its_scope(self):
        self.assertIn("not the emitted or skinned asset", Y.footprint("bow.drawn")["scope"])
        self.assertIn("not a continuous-time bound", Y.timeline(fps=10.0, end=0.2)["scope"])


class MeshChecker(unittest.TestCase):
    """assess_eye on exact eye-space triangles: Codex's three counterexamples
    to f1433a7 (yumi-b55fe81-independent-review/checker-reproductions.json)."""

    @classmethod
    def setUpClass(cls):
        import numpy as np
        cls.np = np
        cls.screen = Y.F.Screen(contract()["camera"])

    def test_a_triangle_covering_the_viewport_with_every_vertex_outside_is_visible(self):
        T = self.np.array([[[100.0, -1000.0, -1000.0], [100.0, 1000.0, -1000.0], [100.0, 0.0, 2000.0]]])
        r = Y.assess_eye(T, self.screen)
        self.assertTrue(r["visible"])
        self.assertEqual(r["nearest_half_heights"], 0.0)

    def test_a_near_cut_across_the_screen_counts_although_its_ends_are_off_screen(self):
        # One vertex in front, two behind: its cut runs u -1.83 to +1.83 at v 0.
        T = self.np.array([[[30.0, 0.0, 0.0], [5.0, -40.0, 0.0], [5.0, 40.0, 0.0]]])
        r = Y.assess_eye(T, self.screen)
        self.assertEqual(r["near_clip_in_frame"], 1)
        u0, u1, v0, v1 = r["clip_box"]
        self.assertAlmostEqual(u0, -1.0, places=9)
        self.assertAlmostEqual(u1, 1.0, places=9)
        self.assertAlmostEqual(v0, 0.0, places=9)

    def test_a_crossing_triangles_remainder_is_kept(self):
        # Two vertices in front on screen, one behind; the remainder covers the reticle at x 27.5 cm.
        T = self.np.array([[[50.0, -10.0, -10.0], [50.0, 10.0, -10.0], [5.0, 0.0, 10.0]]])
        r = Y.assess_eye(T, self.screen)
        self.assertTrue(r["visible"])
        self.assertEqual(r["nearest_half_heights"], 0.0)
        self.assertEqual(r["near_clip_in_frame"], 1)

    def test_summary_counts_time_inside_the_radius_whatever_the_visibility(self):
        tl = {"clear_radius": 0.12, "fps": 30.0, "release_at": 1.0,
              "frames": [{"t": 0.7, "draw": 1.0, "parts": {"arrow": {"visible": False, "nearest_conservative": 0.0,
                                                                     "near_clip_in_frame": 0, "clip_box": None}}}]}
        sm = Y.summary(tl)
        self.assertGreater(sm["arrow"]["hold"]["inside_s"], 0.0)
        self.assertEqual(sm["arrow"]["hold"]["nearest"], 0.0)


class EmittedGeometry(unittest.TestCase):
    """The built rig (b55fe81) and the committed arrow, as triangles."""

    @classmethod
    def setUpClass(cls):
        cls.rig = Y.load_rig()

    def test_the_rig_reproduces_the_static_bow_and_the_drawn_nock(self):
        import numpy as np
        self.assertLess(float(np.abs(Y.skinned(self.rig, 0.0) - self.rig["rest"]).max()), 1e-5)
        i = list(self.rig["bones"]).index("String_Nock")
        M = Y._deform_at(self.rig, 1.0)[i]
        nock = M[:3, :3] @ np.array(Y.braced()["sockets"]["Grip_R"]) + M[:3, 3]
        np.testing.assert_allclose(nock, (-Y.DRAW_M, 0.0, Y.NOCK_Z), atol=1e-5)
        self.assertEqual(self.rig["arrow_verts"].shape[1], 3)
        size = self.rig["arrow_verts"].max(0) - self.rig["arrow_verts"].min(0)
        self.assertGreater(float(size[1]), 0.03)                 # the feathers, not a 4 mm shaft

    def test_local_slerp_reproduces_keys_and_rotations(self):
        # The take's playback between keys (local slerp and lerp), on a synthetic two-bone rig.
        import numpy as np

        def rot_y(a):
            c, s = math.cos(a), math.sin(a)
            return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        bind = np.stack([np.eye(4), np.eye(4)])
        bind[1, :3, 3] = (0.0, 0.0, 1.0)
        pose = np.zeros((2, 2, 4, 4))
        for k, a in enumerate((0.0, 0.4)):
            for b in range(2):
                pose[k, b] = np.eye(4)
                pose[k, b, :3, :3] = rot_y(a * b) @ bind[b, :3, :3]
                pose[k, b, :3, 3] = bind[b, :3, 3] + (0.1 * k * b, 0.0, 0.0)
        rig = {"fractions": np.array([0.0, 1.0]), "bind": bind, "pose": pose,
               "deform": np.einsum("kbij,bjl->kbil", pose, np.linalg.inv(bind))}
        np.testing.assert_allclose(Y._deform_at(rig, 0.0), rig["deform"][0], atol=1e-12)
        np.testing.assert_allclose(Y._deform_at(rig, 1.0 - 1e-12), rig["deform"][1], atol=1e-9)
        mid = Y._deform_at(rig, 0.5) @ bind
        np.testing.assert_allclose(mid[1, :3, :3], rot_y(0.2), atol=1e-12)     # slerped halfway
        np.testing.assert_allclose(mid[1, :3, 3], (0.05, 0.0, 1.0), atol=1e-12)  # translation lerped

    def test_point_to_triangle_distance(self):
        import numpy as np
        P = np.array([[[-1.0, -1.0], [1.0, -1.0], [0.0, 1.0]],      # contains the origin
                      [[1.0, 1.0], [2.0, 1.0], [1.0, 2.0]]])        # nearest corner at (1, 1)
        d = Y._point_tri_dist(P)
        self.assertEqual(float(d[0]), 0.0)
        self.assertAlmostEqual(float(d[1]), 2 ** 0.5, places=12)

    def test_the_kai_pose_clears_the_reticle_with_the_real_bow_and_arrow(self):
        sm = Y.summary(Y.timeline_mesh(rig=self.rig, fps=30.0))
        for part, phases in sm.items():
            for phase, v in phases.items():
                self.assertGreaterEqual(v["nearest"], 0.12, (part, phase, v))
                self.assertEqual(v["hidden_frames"], 0, (part, phase))
        for phase in sm["bow"]:
            self.assertEqual(sm["bow"][phase]["near_clip_frames"], 0, phase)
        self.assertEqual(sm["arrow"]["hold"]["near_clip_frames"], 0)
        # Reported residual: the real feathers cross the near plane at the
        # frame's bottom-left corner briefly in the draw (draw about 0.64-0.69).
        self.assertEqual(sm["arrow"]["draw"]["near_clip_frames"], 2)    # at this test's 30 fps (3 at 60 fps), cut segments clipped to the frame
        u0, u1, v0, v1 = sm["arrow"]["draw"]["clip_box"]
        self.assertTrue(u1 <= -0.9 and v1 <= -0.85, sm["arrow"]["draw"]["clip_box"])


if __name__ == "__main__":
    unittest.main()
