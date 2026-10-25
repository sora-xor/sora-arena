"""Tests for yumi_draw: the bow model, the full draw, the rig and the first-person volumes.

Run: python3 -m unittest scripts/art/test_yumi_draw.py

Standard library only; about 20 seconds. It proves:
* the model reproduces the committed SM_Weapon_18 sockets and string;
* the full draw keeps the string's length and puts the arrow's point 10 cm
  past the grip;
* the continuous rig (RIG_BONES) holds the stave within 2 mm of the solved
  shape through the draw;
* in the A4 bow poses, every volume (stave, string, arrow, both paws) stays
  outside the reticle clear radius in rest and both bobs, through draw, hold
  and release. That holds with the authored anchor y = -5 cm and the pose
  following the draw. Today's -3 cm fails in the hold (the stave), and a
  pose that blends ahead of the draw fails in the draw (the arrow).
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yumi_draw as Y  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi/build_record.json"


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
        self.assertAlmostEqual(sum((tip[i] - nock[i]) ** 2 for i in range(3)) ** 0.5, Y.ARROW_M, places=9)
        self.assertTrue(0.09 <= tip[0] <= 0.11, tip)           # the point 10 cm past the grip
        self.assertGreater(dr["k"], 1.0)
        # The tips come in and back: the drawn string ends lie behind the braced ones.
        br = Y.braced()["sockets"]
        self.assertLess(dr["sockets"]["String_Upper"][0], br["String_Upper"][0])
        self.assertLess(dr["sockets"]["String_Lower"][0], br["String_Lower"][0])

    def test_the_rig_holds_the_stave_through_the_draw(self):
        for d in (0.25, 0.5, 0.75, 1.0):
            e = Y.skinning_error(d)
            self.assertLess(e["upper"], 0.002, d)
            self.assertLess(e["lower"], 0.002, d)


class FirstPerson(unittest.TestCase):
    def test_authored_anchor_and_draw_led_pose_keep_every_volume_clear(self):
        sm = Y.summary(Y.timeline(anchor_y=-5.0, pose_follows_draw=True))
        for part, phases in sm.items():
            for phase, v in phases.items():
                self.assertGreaterEqual(v["nearest"], 0.12, (part, phase, v))
                self.assertEqual(v["inside_s"], 0.0, (part, phase))
        self.assertEqual(set(sm), {"stave", "string", "arrow", "paw_L", "paw_R"})
        self.assertNotIn("hold", sm["paw_R"])                 # the draw paw is at the cheek at full draw

    def test_todays_anchor_puts_the_stave_in_the_clear_zone(self):
        sm = Y.summary(Y.timeline(anchor_y=-3.0, pose_follows_draw=True))
        self.assertLess(sm["stave"]["hold"]["nearest"], 0.12)

    def test_a_pose_ahead_of_the_draw_brings_the_arrow_into_it(self):
        sm = Y.summary(Y.timeline(anchor_y=-5.0, pose_follows_draw=False))
        self.assertLess(sm["arrow"]["draw"]["nearest"], 0.12)
        self.assertGreaterEqual(sm["arrow"]["hold"]["nearest"], 0.12)

    def test_volumes_not_sockets(self):
        # The grip socket alone clears the radius at -3 cm; only the stave's volume shows the intrusion.
        fp = Y.footprint("bow.drawn")
        self.assertFalse(fp["clear"])
        self.assertLess(fp["stave"]["nearest_half_heights"], fp["clear_radius"])


if __name__ == "__main__":
    unittest.main()
