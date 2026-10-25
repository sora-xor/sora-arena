"""Regression tests for the first-person viewmodel contract's source checker.

Run: python3 -m unittest scripts/art/test_viewmodel_framing.py

Source-only. The committed contract (Content/Data/viewmodels.json) must pass,
and every gap root's review of 3d01352 reproduced must now fail:

* empty, short or duplicated weapon tables;
* a wrong mesh or a missing socket;
* a stale rotated-socket provenance;
* a heavy grip below the frame;
* the legacy -15 degree drawing tilt stacked on the drawn bow;
* a bow reload that clips the stave.

So must the original framing failures: today's (40, 18, -18) root, and a
blade through the reticle. The aim tests check that applying the same angle on
both cameras misses the HUD ray, while the presentation correction meets it.
Pure Python.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_viewmodel_framing as F  # noqa: E402


class Framing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(F.CONTRACT.read_text())

    def run_contract(self, contract):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "viewmodels.json"
            path.write_text(json.dumps(contract))
            out, err = StringIO(), StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = F.main(["--contract", str(path)])
            return code, err.getvalue()

    def fails(self, contract, text):
        code, err = self.run_contract(contract)
        self.assertEqual(code, 1, f"expected a failure containing {text!r}")
        self.assertIn(text, err)

    def mutated(self):
        return copy.deepcopy(self.contract)

    def weapon(self, contract, key):
        return next(w for w in contract["weapons"] if w["key"] == key)

    def test_committed_contract_passes(self):
        self.assertEqual(self.run_contract(self.contract)[0], 0)

    def test_empty_short_and_duplicated_tables_fail(self):
        c = self.mutated()
        c["weapons"] = []
        self.fails(c, "weapon table is empty")
        c = self.mutated()
        c["weapons"] = [w for w in c["weapons"] if w["id"] != 20]
        self.fails(c, "missing [20]")
        c = self.mutated()
        c["weapons"].append(copy.deepcopy(c["weapons"][2]))
        self.fails(c, "duplicate weapon ids")
        c = self.mutated()
        self.weapon(c, "W05_CoilMatchlock")["key"] = "W09_Repeater"
        self.fails(c, "duplicate weapon keys")

    def test_wrong_mesh_or_missing_socket_fails(self):
        c = self.mutated()
        self.weapon(c, "W02_Kusarigama")["first_person_mesh"] = "/Game/Generated/Meshes/SM_Weapon_02_Missing"
        self.fails(c, "record has no SM_Weapon_02_Missing sockets")
        c = self.mutated()
        c["poses"]["polearm"]["clear_line"] = ["Grip_L", "Spearhead"]
        self.fails(c, "no sockets ['Spearhead']")

    def test_stale_rotated_socket_provenance_fails(self):
        c = self.mutated()
        self.weapon(c, "W15_MicroMortar")["socket_axes"]["Grip_R"]["call"] = 'b.socket("Grip_R", (0.0, 0.0, 0.0), x=(0, 1, 0), z=(-1, 0, 0))'
        self.fails(c, "no longer in")

    def test_heavy_grip_below_the_frame_fails(self):
        c = self.mutated()
        c["poses"]["heavy"]["rest"] = {"anchor_cm": [36.0, 13.0, -15.0], "rotation_deg": [26.0, 4.0, 0.0]}
        c["poses"]["heavy"]["screen"]["Grip_R"] = {"u": [0.35, 0.75], "v": [-1.2, -0.8]}
        self.fails(c, "visible Grip_R at u +0.52, v -1.06 is off the frame")

    def test_todays_weapon_root_puts_the_grip_offscreen(self):
        c = self.mutated()
        c["poses"]["sword"]["rest"] = {"anchor_cm": [40.0, 18.0, -18.0], "rotation_deg": [0.0, 0.0, 0.0]}
        self.fails(c, "W00_Katana sword [rest]: Grip_R at u +0.64, v -1.14")

    def test_blade_through_the_reticle_fails(self):
        c = self.mutated()
        c["poses"]["sword"]["rest"]["rotation_deg"] = [6.0, -9.0, 0.0]
        self.fails(c, "from the reticle")

    def test_drawn_bow_replaces_the_legacy_tilt(self):
        c = self.mutated()
        c["motion"]["pitch_deg"]["bow_drawing"] = -15.0
        self.fails(c, "replace, not add")
        rep, _ = F.run(self.contract, F.ROOT)
        stacked = next(u for label, name, u, v in rep.rows if name == "stacked legacy -15 miss")
        self.assertAlmostEqual(stacked, 0.654, places=2)
        c = self.mutated()
        c["poses"]["bow.drawn"]["rest"]["rotation_deg"] = [2.0, 1.0, 0.0]
        self.fails(c, "misses the reticle")

    def test_bow_reload_must_not_clip_the_stave(self):
        c = self.mutated()
        del c["poses"]["bow"]["motion_overrides"]
        self.fails(c, "W18_Yumi bow [reload]: String_Lower behind the near plane")

    def test_same_angle_aim_misses_and_the_correction_meets_the_hud_ray(self):
        rep, _ = F.run(self.contract, F.ROOT)
        rows = {name: u for label, name, u, v in rep.rows if label.startswith("W18_Yumi bow.drawn")}
        tol = self.contract["aim_presentation"]["tolerance"]
        self.assertGreater(rows["aim offset (+6,+4) same-angle error"], tol)
        for yaw, pitch in self.contract["aim_presentation"]["check_offsets_deg"]:
            self.assertLessEqual(rows[f"aim offset ({yaw:+.0f},{pitch:+.0f}) corrected error"], tol)

    def test_socket_axes_follow_the_fbx_flip(self):
        pts, _ = F.place({"anchor_cm": [40.0, 0.0, 0.0], "rotation_deg": [0.0, 0.0, 0.0]},
                         {"Grip_R": [0.0, 0.0, 0.0], "Grip_L": [0.0, 0.10, 0.0]}, "Grip_R", 1.0)
        self.assertAlmostEqual(pts["Grip_L"][1], -10.0)


if __name__ == "__main__":
    unittest.main()
