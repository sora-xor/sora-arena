"""Tests for the W18 nigiri wrap (yumi_nigiri) and the ya's shaft (yumi_ya), and their contracts.

Run: python3 -m unittest scripts/art/test_yumi_nigiri_ya.py

Pure math, the same the generator (create_runtime_weapon_yumi.py) builds
with. Root's review of the first lit first-person originals found the grip
wraps reading as stepped plates and the arrow plastic. These pin what fixes
them:

- the wrap's seam steps only its skived edge, and each turn lies flat;
- the outer leather stays inside the first-person envelope
  (yumi_draw.ENVELOPE_GRIP_M) and at the girth the bow paw is carved to
  (nyaakoto_fp_paws.GRIP_WRAP), within the paw's own carve gap;
- the strip covers the paw's digits at every angle round the grip;
- the arrow's nodes are each their own, inside its envelope
  (yumi_draw.ARROW_SHAFT_R), each ridge sampled finely enough to be shaped;
- the generator builds from these modules, not copies of them.

The emitted, rebuilt rig is checked by Grip in test_nyaakoto_fp_paws.py.
"""
from __future__ import annotations

import ast
import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nyaakoto_fp_paws as P  # noqa: E402
import yumi_draw as YD  # noqa: E402
import yumi_nigiri as NG  # noqa: E402
import yumi_ya as YA  # noqa: E402

GENERATOR = HERE / "create_runtime_weapon_yumi.py"


class Nigiri(unittest.TestCase):
    def test_the_section_spans_one_pitch_and_closes(self):
        sec = NG.section()
        along = [b for _a, b in sec]
        self.assertAlmostEqual(min(along), -NG.pitch() / 2, places=12)
        self.assertAlmostEqual(max(along), NG.pitch() / 2, places=12)
        self.assertEqual(sec[-1], (-NG.BURY_M, -NG.pitch() / 2))               # the floor closes at the cut edge
        self.assertTrue(all(a >= NG.THICK_M for a, _b in sec[:-2]))           # the top never dips below the strip

    def test_the_seam_steps_only_the_skived_edge(self):
        # One turn starts (v = 0) where the turn before ends (v = 1): the step between them.
        step = NG.height(0.0) - NG.height(1.0)
        self.assertAlmostEqual(step, NG.EDGE_M, places=12)
        self.assertLess(step, 0.0003)               # a fraction of a millimetre, not v1's 3.8 mm plates

    def test_each_turn_lies_flat_beyond_its_lap(self):
        vs = [v for v in NG.section_vs() if v >= NG.lapped()]
        self.assertTrue(vs)
        self.assertTrue(all(abs(NG.height(v) - NG.THICK_M) < 1e-12 for v in vs))
        # No turn is tilted: its top's slope along the stave is gentle everywhere past the cut edge.
        top = [(b, a) for a, b in NG.section()[:-2]]
        slopes = [abs(a1 - a0) / (b1 - b0) for (b0, a0), (b1, a1) in zip(top, top[1:]) if b1 > b0]
        self.assertLess(max(slopes), 0.3)

    def test_the_outer_leather_stays_inside_the_first_person_envelope(self):
        self.assertLessEqual(NG.max_elevation(), YD.ENVELOPE_GRIP_M)

    def test_the_bow_paw_is_carved_to_this_girth(self):
        # The paw's skin stops CARVE_GAP off GRIP_WRAP. The real leather must
        # lie within that gap of it: never through the skin, never more than
        # twice the gap off it.
        w, d = YD.thickness(0.0)
        self.assertLessEqual(abs(d / 2 + NG.max_elevation() - P.GRIP_WRAP["a"]), P.CARVE_GAP)
        self.assertLessEqual(abs(w / 2 + NG.max_elevation() - P.GRIP_WRAP["b"]), P.CARVE_GAP)
        self.assertEqual(P.GRIP_WRAP["power"], YD._C["POWER"])

    def test_the_strip_covers_the_paws_digits_at_every_angle(self):
        lo, hi = NG.covered_span(YD.GRIP_HALF)
        for name, dig in P.DIGITS.items():
            r = max(dig["r"])
            self.assertGreaterEqual(dig["z"] - r, lo, name)
            self.assertLessEqual(dig["z"] + r, hi, name)

    def test_the_strip_reaches_no_further_than_its_underlay(self):
        lo, hi = NG.reach(YD.GRIP_HALF)
        self.assertGreater(lo, -YD.GRIP_HALF)
        self.assertLess(hi, YD.GRIP_HALF)


class Ya(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nodes = YA.ya_nodes()

    def test_the_nodes_are_each_their_own(self):
        self.assertEqual(len(self.nodes), 4)
        offsets = [xn - x for (xn, _a, _s), x in zip(self.nodes, YA.YA_NODES_M)]
        self.assertTrue(all(abs(o) <= YA.NODE_PLACE_M for o in offsets))
        self.assertGreater(max(offsets) - min(offsets), 0.004)                # not one shift for all
        for (xn, amp, sig) in self.nodes:
            self.assertTrue(YA.NODE_BULGE_M[0] <= amp <= YA.NODE_BULGE_M[1])
            self.assertTrue(YA.NODE_WIDTH_M[0] <= sig <= YA.NODE_WIDTH_M[1])
        self.assertGreater(len({round(a, 6) for _x, a, _s in self.nodes}), 2)
        gaps = [b[0] - a[0] for a, b in zip(self.nodes, self.nodes[1:])]
        self.assertGreater(max(gaps) - min(gaps), 0.004)                      # internodes differ in length

    def test_the_shaft_stays_inside_the_first_person_envelope(self):
        xs = YA.stations(self.nodes)
        r = max(YA.r_shaft(x) + YA.node_bulge(x, self.nodes) for x in xs)
        self.assertLessEqual(r, YD.ARROW_SHAFT_R)

    def test_each_ridge_is_sampled_finely_enough_to_shape(self):
        xs = YA.stations(self.nodes)
        for xn, _amp, sig in self.nodes:
            near = [x for x in xs if abs(x - xn) <= 2 * sig]
            self.assertGreaterEqual(len(near), 5, xn)                         # both flanks and the crest
            self.assertLessEqual(max(b - a for a, b in zip(near, near[1:])), 0.0016)

    def test_the_hash_is_the_generators(self):
        def body(tree, name):
            fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
            stmts = fn.body
            if stmts and isinstance(stmts[0], ast.Expr) and isinstance(getattr(stmts[0], "value", None), ast.Constant):
                stmts = stmts[1:]                                   # a docstring is not the hash
            return ast.dump(ast.Module(body=stmts, type_ignores=[]))
        gen = ast.parse(GENERATOR.read_text(encoding="utf-8"))
        mine = ast.parse((HERE / "yumi_ya.py").read_text(encoding="utf-8"))
        for name in ("hash01", "jit"):
            self.assertEqual(body(gen, name), body(mine, name), name)


class Rebuild(unittest.TestCase):
    """The committed rig against the sources its bow comes from."""

    RIG_RECORD = HERE.parents[1] / "Content/SourceArt/Weapons/Runtime/W18_Yumi/Rig/rig_record.json"
    SOURCES = ("scripts/art/create_runtime_weapon_yumi.py", "scripts/art/yumi_nigiri.py", "scripts/art/yumi_ya.py",
               "scripts/art/create_runtime_weapon_lib.py", "scripts/art/yumi_draw.py")

    def test_the_rig_was_built_from_the_current_w18_sources(self):
        """The rig record pins every source the bow comes from, at the bytes
        on disk. It was an expected failure until the W18 rebuild (runbook
        step 3, 2026-10-25) rebuilt the static bow and the rig from them."""
        import hashlib
        import json
        rec = json.loads(self.RIG_RECORD.read_text(encoding="utf-8"))
        for src in self.SOURCES:
            self.assertIn(src, rec["inputs"], src)
            self.assertEqual(rec["inputs"][src], hashlib.sha256((HERE.parents[1] / src).read_bytes()).hexdigest(), src)


class Generator(unittest.TestCase):
    """The generator builds the grip and the shaft from these modules."""

    @classmethod
    def setUpClass(cls):
        cls.src = GENERATOR.read_text(encoding="utf-8")

    def test_the_nigiri_is_wound_from_its_section(self):
        self.assertIn("import yumi_nigiri as NG", self.src)
        self.assertIn("prof = NG.section()", self.src)
        self.assertIn("NG.wrap_span(GRIP_HALF)", self.src)
        self.assertNotIn('wound_strip("Nigiri', self.src)
        # The grip check finds the grip by its part name (create_runtime_weapon_specs: grip="Nigiri").
        self.assertIn('L.loft("Nigiri", grip_rings', self.src)

    def test_the_shaft_is_built_from_its_nodes(self):
        self.assertIn("import yumi_ya as YA", self.src)
        self.assertIn("nodes = YA.ya_nodes()", self.src)
        self.assertIn("YA.stations(nodes)", self.src)
        self.assertIn("nodes=tuple(x0 + xn for xn, _a, _s in nodes)", self.src)
        self.assertIn("lacquer=0.0", self.src)


if __name__ == "__main__":
    unittest.main()
