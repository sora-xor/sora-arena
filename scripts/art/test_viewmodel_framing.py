"""Regression tests for the first-person viewmodel contract's framing check.

Run: python3 -m unittest scripts/art/test_viewmodel_framing.py

The committed contract (Content/Data/viewmodels.json) must pass, and two known
failures must be caught. Today's WeaponRoot (40, 18, -18) puts the katana's
grip below the frame (the paw studies drew 0 px there). A blade aimed through
the reticle covers the target. Pure Python.
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

    def test_committed_contract_passes(self):
        self.assertEqual(self.run_contract(self.contract)[0], 0)

    def test_todays_weapon_root_puts_the_grip_offscreen(self):
        contract = copy.deepcopy(self.contract)
        contract["poses"]["sword"]["rest"] = {"anchor_cm": [40.0, 18.0, -18.0], "rotation_deg": [0.0, 0.0, 0.0]}
        code, err = self.run_contract(contract)
        self.assertEqual(code, 1)
        self.assertIn("W00_Katana sword: Grip_R at u +0.64, v -1.14", err)

    def test_blade_through_the_reticle_fails(self):
        contract = copy.deepcopy(self.contract)
        contract["poses"]["sword"]["rest"]["rotation_deg"] = [6.0, -9.0, 0.0]
        code, err = self.run_contract(contract)
        self.assertEqual(code, 1)
        self.assertIn("from the reticle", err)

    def test_drawn_bow_must_aim_at_the_reticle(self):
        contract = copy.deepcopy(self.contract)
        contract["poses"]["bow.drawn"]["rest"]["rotation_deg"] = [2.0, 1.0, 0.0]
        code, err = self.run_contract(contract)
        self.assertEqual(code, 1)
        self.assertIn("arrow line misses the reticle", err)

    def test_socket_axes_follow_the_fbx_flip(self):
        # +Y in the weapon's Blender frame is the wielder's left, so a socket
        # there lands left of the anchor in UE eye space.
        pts = F.place({"anchor_cm": [40.0, 0.0, 0.0], "rotation_deg": [0.0, 0.0, 0.0]},
                      {"Grip_R": [0.0, 0.0, 0.0], "Grip_L": [0.0, 0.10, 0.0]}, "Grip_R", 1.0)
        self.assertAlmostEqual(pts["Grip_L"][1], -10.0)


if __name__ == "__main__":
    unittest.main()
