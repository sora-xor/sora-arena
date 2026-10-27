"""Regression tests for the cloth craft prop slot checks.

Run: python3 -m unittest scripts/unreal/test_sora_cloth_admission.py

No Unreal: sora_cloth_admission.py is the pure part of import_sora_craft.py's
cloth path.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sora_cloth_admission as C  # noqa: E402

ROLES = ("M_Maku_Hemp", "M_Maku_Pole", "M_Maku_Gilt", "M_Maku_Cord")
DECLARED = ["M_Maku_Cord", "M_Maku_Gilt", "M_Maku_Hemp", "M_Maku_Pole"]   # as create_sora_maku.py writes it
HEMP = "M_Maku_Hemp"


class Declared(unittest.TestCase):
    def test_the_maku_record_passes(self):
        self.assertEqual(C.check_declared(DECLARED, ROLES, HEMP), DECLARED)

    def test_rejections(self):
        for declared, reason in (([], "non-empty list"), (None, "non-empty list"), ("M_Maku_Hemp", "non-empty list"),
                                 (["M_Maku_Hemp", "M_Maku_Hemp"], "more than once"),
                                 (DECLARED + ["M_Maku_Silk"], "no material for"),
                                 (["M_Maku_Pole", "M_Maku_Gilt"], "cloth slot")):
            with self.subTest(declared=declared), self.assertRaisesRegex(C.AdmissionError, reason):
                C.check_declared(declared, ROLES, HEMP)


class Imported(unittest.TestCase):
    def test_exact_slots_in_any_order_pass(self):
        mesh = ["M_Maku_Hemp", "M_Maku_Pole", "M_Maku_Gilt", "M_Maku_Cord"]
        self.assertEqual(C.check_imported(DECLARED, mesh), mesh)

    def test_empty_mesh_rejects(self):
        with self.assertRaisesRegex(C.AdmissionError, "no material slots"):
            C.check_imported(DECLARED, [])

    def test_single_hemp_slot_rejects(self):
        with self.assertRaisesRegex(C.AdmissionError, "missing"):
            C.check_imported(DECLARED, ["M_Maku_Hemp"])

    def test_known_but_undeclared_slot_rejects(self):
        declared = C.check_declared(["M_Maku_Hemp", "M_Maku_Pole", "M_Maku_Cord"], ROLES, HEMP)
        with self.assertRaisesRegex(C.AdmissionError, "undeclared \\['M_Maku_Gilt'\\]"):
            C.check_imported(declared, ["M_Maku_Hemp", "M_Maku_Pole", "M_Maku_Cord", "M_Maku_Gilt"])

    def test_repeated_slot_rejects(self):
        with self.assertRaisesRegex(C.AdmissionError, "repeats"):
            C.check_imported(DECLARED, DECLARED + ["M_Maku_Hemp"])


if __name__ == "__main__":
    unittest.main()
