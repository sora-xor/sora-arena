"""Tests for the first-person material-binding check (scripts/unreal/fp_material_bindings.py).

Run: python3 -m unittest scripts/art/test_fp_material_bindings.py

The check is plain Python. Codex's review of cf646c2: sorted paths alone hide
a swapped override, so each component index must draw its asset's slot at
that index, with exact slot counts and names. These tests pin that, and pin
the serialized expectations to the importers' own slot names.
"""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/unreal"))
import fp_material_bindings as B  # noqa: E402

RIG = "/Game/Generated/Qualification/W18YumiRig"
PAWS = "/Game/Generated/Qualification/NyaakotoFPPaws"
A, PA = "M_A", "/Game/X/MI_A.MI_A"
C, PC = "M_C", "/Game/X/MI_C.MI_C"
WANT = {"slots": {A: PA, C: PC}}


def constant(script: Path, name: str):
    """A module-level constant's literal value, read without importing the script (it imports unreal)."""
    for node in ast.parse(script.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(f"{name} not in {script}")


class Check(unittest.TestCase):
    def test_matching_rows_pass(self):
        self.assertEqual(B.check("asset", [(0, A, PA), (1, C, PC)], [(0, PA), (1, PC)], WANT), [])

    def test_a_swapped_override_fails_though_sorted_paths_match(self):
        drawn = [(0, PC), (1, PA)]
        self.assertEqual(sorted(p for _, p in drawn), sorted((PA, PC)))
        problems = B.check("asset", [(0, A, PA), (1, C, PC)], drawn, WANT)
        self.assertEqual(len(problems), 2, problems)
        self.assertTrue(all("component index" in p for p in problems))

    def test_a_slot_bound_to_the_wrong_material_fails(self):
        problems = B.check("asset", [(0, A, PC), (1, C, PC)], [(0, PC), (1, PC)], WANT)
        self.assertTrue(any("slot 0 (M_A) binds" in p for p in problems), problems)

    def test_the_engine_default_fails_even_where_the_component_agrees(self):
        grid = "/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial"
        problems = B.check("asset", [(0, A, grid), (1, C, PC)], [(0, grid), (1, PC)], WANT)
        self.assertTrue(any("engine default" in p for p in problems), problems)
        self.assertTrue(any("binds " + grid in p for p in problems), problems)

    def test_slot_count_names_and_duplicates_are_exact(self):
        self.assertTrue(B.check("asset", [(0, A, PA)], [(0, PA)], WANT))                       # one missing
        self.assertTrue(B.check("asset", [(0, A, PA), (1, A, PA)], [(0, PA), (1, PA)], WANT))  # duplicate name
        extra = [(0, A, PA), (1, C, PC), (2, "M_D", PC)]
        self.assertTrue(B.check("asset", extra, [(0, PA), (1, PC), (2, PC)], WANT))            # one too many

    def test_component_and_slot_counts_must_agree(self):
        self.assertTrue(B.check("asset", [(0, A, PA), (1, C, PC)], [(0, PA)], WANT))

    def test_rows_must_be_indexed_in_order(self):
        self.assertTrue(B.check("asset", [(1, A, PA), (0, C, PC)], [(0, PA), (1, PC)], WANT))


class Expectations(unittest.TestCase):
    """The serialized rows name exactly the slots the importers bind."""

    @classmethod
    def setUpClass(cls):
        cls.want = B.load()

    def test_the_three_parts(self):
        self.assertEqual(sorted(self.want), sorted((f"{RIG}/SK_Weapon_18", f"{RIG}/SM_Weapon_18_Ya",
                                                    f"{PAWS}/SM_NyaakotoFP_PawL_Yumi")))

    def test_the_bow_and_arrow_bind_their_w18_instances(self):
        rig = ROOT / "scripts/unreal/import_runtime_weapon_yumi_rig.py"
        self.assertEqual(set(self.want[f"{RIG}/SK_Weapon_18"]["slots"]), constant(rig, "BOW_SLOTS"))
        self.assertEqual(set(self.want[f"{RIG}/SM_Weapon_18_Ya"]["slots"]), constant(rig, "ARROW_SLOTS"))
        # instance_for(): the bow's slot takes MI_W18_Weapon, the arrow's MI_W18_Hane (two-sided).
        self.assertEqual(set(self.want[f"{RIG}/SK_Weapon_18"]["slots"].values()),
                         {f"{RIG}/MI_W18_Weapon.MI_W18_Weapon"})
        self.assertEqual(set(self.want[f"{RIG}/SM_Weapon_18_Ya"]["slots"].values()),
                         {f"{RIG}/MI_W18_Hane.MI_W18_Hane"})

    def test_the_paw_binds_each_slot_to_its_own_material(self):
        slots = constant(ROOT / "scripts/unreal/import_nyaakoto_fp_paws.py", "SLOTS")
        want = self.want[f"{PAWS}/SM_NyaakotoFP_PawL_Yumi"]["slots"]
        self.assertEqual(sorted(want), sorted(slots))
        self.assertEqual(want, {s: f"{PAWS}/{s}.{s}" for s in slots})


if __name__ == "__main__":
    unittest.main()
