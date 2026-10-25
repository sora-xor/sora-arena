"""Regression tests for scripts/art/timber_density_study.py.

Run: python3 -m unittest scripts/art/test_timber_density_study.py

These lock the study's three load-bearing claims against the committed kit:

* the copied column and rail recipes rebuild exactly the manifests' triangle
  counts, so the study measures the real logs;
* today's sampling changes the number of samples across a check from row to
  row, which is the fallback's stair-step;
* keeping the check's zone clear makes that count constant, at the same
  sample cost.

Pure numpy, no Blender; about ten seconds.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sora_timber_lib as T  # noqa: E402
import timber_density_study as D  # noqa: E402


class Study(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.columns = json.loads((D.KIT / "manifest.json").read_text())["placements"]
        cls.rails = json.loads((D.KIT / "Rails/manifest.json").read_text())["placements"]
        cls.wall = next(p for p in cls.columns if p["kind"] == "wall")
        cls.m = D.column_member(cls.wall["seed"], "wall", cls.wall["asset"])

    def test_recipes_rebuild_the_committed_counts(self):
        opn = next(p for p in self.columns if p["kind"] == "open")
        for rec, m in ((self.wall, self.m), (opn, D.column_member(opn["seed"], "open", opn["asset"]))):
            self.assertEqual(2 * T.sample_member(m).x.size, rec["triangles"], rec["asset"])
        for kind in D.R["RAILS"]:
            rec = next(p for p in self.rails if p["kind"] == kind)
            m = D.rail_member(rec["seed"], kind, rec["asset"], rec["length_m"])
            self.assertEqual(2 * T.sample_member(m).x.size, rec["triangles"], rec["asset"])

    def test_todays_fallback_changes_topology_across_checks(self):
        mf = T.fallback_of(self.m)
        today = D.check_topology(mf, T.sample_member(mf))
        self.assertTrue(today and any(c["row_to_row_changes"] > 0 for c in today))

    def test_a_clear_check_zone_keeps_the_count_constant(self):
        topo = D.fallback_topology(self.m)
        self.assertTrue(topo["zone_clear"])
        for c in topo["zone_clear"]:
            self.assertEqual(c["row_to_row_changes"], 0, c)
            self.assertEqual(c["count_min"], c["count_max"])
        self.assertLess(abs(topo["samples_zone_clear"] - topo["samples_today"]) / topo["samples_today"], 0.05)

    def test_budgets_cut_the_committed_triangles(self):
        for name in ("F", "C", "G"):
            self.assertLess(D.budget(self.m, name), 0.5 * self.wall["triangles"], name)


if __name__ == "__main__":
    unittest.main()
