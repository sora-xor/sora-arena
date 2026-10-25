"""Regression tests for scripts/art/bind_dojo_timbers.py.

Run: python3 -m unittest scripts/art/test_bind_dojo_timbers.py

The tests read the committed column and rail manifests and the project's
chapter files. Then they check that the binder accepts them, and that it
rejects every reproduced mutation: a rail's seed, kind, length, side or bay;
a column's kind or seed; a record repeated; a record without a hall; a moved
hall. Pure Python, no Blender.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_dojo_timbers as B  # noqa: E402
import dojo_hall_placements as HP  # noqa: E402

CH01 = (8000, -1300, 11600, 1300)


class Binder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.columns, cls.rails = (json.loads(p.read_text()) for p in B.MANIFESTS)
        cls.halls = HP.estate_halls(B.ROOT)
        cls.layout = B.rail_layout()

    def check(self, columns=None, rails=None, halls=None):
        return B.layout_check(columns or self.columns, rails or self.rails, halls or self.halls, self.layout)

    def assertStale(self, reason, **kwargs):
        rows, stale = self.check(**kwargs)
        self.assertTrue(any(reason in s for s in stale), f"no stale entry with {reason!r}: {stale[:3]}")

    def rail(self, kind="Nageshi"):
        rails = copy.deepcopy(self.rails)
        return rails, next(r for r in rails["placements"] if r["kind"] == kind)

    def test_committed_kit_binds(self):
        rows, stale = self.check()
        self.assertEqual(stale, [])
        ch01 = next(r for r in rows if tuple(r["rect"]) == CH01)
        self.assertEqual((ch01["columns_with_own_log"], ch01["columns"]), (65, 65))
        self.assertEqual((ch01["rails_with_own_log"], ch01["rails"]), (235, 235))
        self.assertEqual(sum(r["columns"] for r in rows), 260)
        self.assertEqual(sum(r["rails"] for r in rows), 940)

    def test_mutated_rail_seed_rejects(self):
        rails, rec = self.rail()
        rec["seed"] += 1
        self.assertStale("seed", rails=rails)

    def test_mutated_rail_kind_rejects(self):
        rails, rec = self.rail("Nuki")
        rec["kind"] = "Koshi"
        self.assertStale("kind 'Koshi'", rails=rails)

    def test_mutated_rail_length_side_or_bay_rejects(self):
        for field, value in (("length_m", 1.0), ("side", 3), ("bay", 99)):
            with self.subTest(field=field):
                rails, rec = self.rail("Cornice")
                rec[field] = value
                self.assertStale(field, rails=rails)

    def test_mutated_column_kind_or_seed_rejects(self):
        for field in ("kind", "seed"):
            with self.subTest(field=field):
                columns = copy.deepcopy(self.columns)
                rec = columns["placements"][0]
                rec[field] = ("wall" if rec["kind"] == "open" else "open") if field == "kind" else rec["seed"] ^ 1
                self.assertStale(field, columns=columns)

    def test_duplicate_column_record_rejects(self):
        columns = copy.deepcopy(self.columns)
        columns["placements"].append(copy.deepcopy(columns["placements"][5]))
        self.assertStale("column recorded 2 times", columns=columns)

    def test_duplicate_rail_record_rejects(self):
        rails = copy.deepcopy(self.rails)
        rails["placements"].append(copy.deepcopy(rails["placements"][7]))
        self.assertStale("rail recorded 2 times", rails=rails)

    def test_record_without_a_hall_rejects(self):
        columns = copy.deepcopy(self.columns)
        ghost = copy.deepcopy(columns["placements"][0])
        ghost["asset"] = HP.column_name((60000, -1300, 63600, 1300), 0, 0)
        columns["placements"].append(ghost)
        self.assertStale("no current estate hall has this column", columns=columns)

    def test_moved_hall_rejects_every_log(self):
        halls = {((x0 + 200, y0, x1 + 200, y1) if (x0, y0, x1, y1) == CH01 else (x0, y0, x1, y1)): uses
                 for (x0, y0, x1, y1), uses in self.halls.items()}
        rows, stale = self.check(halls=halls)
        self.assertEqual(sum("no current estate hall" in s for s in stale), 65 + 235)
        self.assertEqual(sum(r["columns_with_own_log"] + r["rails_with_own_log"] for r in rows), 0)


if __name__ == "__main__":
    unittest.main()
