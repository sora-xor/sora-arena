"""Tests for the third-person paws' fur strands (nyaakoto_tp_fur).

Run: python3 -m unittest scripts/art/test_nyaakoto_tp_fur.py

On the hero's own arms (test_nyaakoto_tp_paws.hero_arm), both sides:
- **Density by LOD:** LOD0 grows the most strands, LOD1 about a third as many, LOD2 none.
- **Where they grow:** no root within clear_m of the grip channel; every tip clear of it, outside the skin (fuzz
  included), and within the rig's 11 cm breadth gate.
- **No skin crossing:** after grow, no strand crosses the skin, in the grip or the empty fist.
- **The flow:** unit, and in the skin's tangent plane.
- **The empty fist:** the morph carries each strand's root with the skin point it grows from.
- **Determinism:** the same seed grows the same strands.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nyaakoto_tp_fur as F  # noqa: E402
import nyaakoto_tp_paws as P  # noqa: E402
from test_nyaakoto_tp_paws import PALM_RADII, hero_arm  # noqa: E402

GROWN = {}


def grown(sign, lod):
    if (sign, lod) not in GROWN:
        m = P.mesh_paw(hero_arm(sign), PALM_RADII, step=P.LOD_STEPS[lod])
        GROWN[sign, lod] = (m, F.grow(m, F.LOD_DENSITY[lod]))
    return GROWN[sign, lod]


class Strands(unittest.TestCase):
    def test_density_by_lod(self):
        for sign in (1, -1):
            n = [len(grown(sign, lod)[1][1]) for lod in range(3)]
            with self.subTest(sign=sign, counts=n):
                self.assertGreater(n[0], 3000)
                self.assertTrue(0.2 * n[0] < n[1] < 0.5 * n[0])
                self.assertEqual(n[2], 0)

    def test_where_they_grow(self):
        for sign in (1, -1):
            for lod in (0, 1):
                m, (sv, st, suv, scoat, _) = grown(sign, lod)
                fr = m["skeleton"]["frame"]
                tri = sv.reshape(-1, 3, 3)
                root, tip = tri[:, :2].mean(1), tri[:, 2]
                with self.subTest(sign=sign, lod=lod):
                    self.assertGreater(float(P.channel_sdf(root, fr).min()), F.STRANDS["clear_m"] - 1e-6)
                    self.assertGreater(float(P.channel_sdf(tip, fr).min()), F.STRANDS["tip_clear_m"] - 1e-9)
                    self.assertGreater(float(P.paw_sdf(tip, m["skeleton"]).min()), P.FUZZ_MAX)
                    self.assertLess(float(np.abs((tip - fr["c"]) @ P.Y).max()), P.PAW_HALF)
                    self.assertTrue(((scoat >= 0.0) & (scoat <= 1.0)).all())
                    self.assertEqual(suv.shape, (len(st), 3, 2))

    def test_no_strand_crosses_the_skin_in_either_state(self):
        for sign in (1, -1):
            for lod in (0, 1):
                m, (sv, st, *_rest) = grown(sign, lod)
                for state in ("grip", "empty"):
                    skin = m["verts"] if state == "grip" else P.empty_points(m["verts"], m["skeleton"])
                    fur = sv if state == "grip" else P.empty_points(sv, m["skeleton"])
                    with self.subTest(sign=sign, lod=lod, state=state):
                        self.assertEqual(len(F.skin_crossing_strands(skin, m["tris"], fur, st)), 0)

    def test_flow_is_a_unit_tangent(self):
        m, _ = grown(1, 1)
        V, T = m["verts"], m["tris"]
        n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
        n /= np.linalg.norm(n, axis=1, keepdims=True)
        c = V[T].mean(1)
        d = F.flow(c, n, m["skeleton"])
        self.assertLess(float(np.abs(np.linalg.norm(d, axis=1) - 1.0).max()), 1e-9)
        self.assertLess(float(np.abs((d * n).sum(1)).max()), 1e-9)

    def test_the_morph_carries_the_roots_with_the_skin(self):
        m, (sv, st, *_rest) = grown(-1, 0)
        root = sv.reshape(-1, 3, 3)[:, :2].mean(1)
        moved = P.empty_points(root, m["skeleton"])
        skin = P.empty_points(m["verts"], m["skeleton"])
        # every moved root lies within a few millimetres of the moved skin's vertices
        far = 0.0
        for k in range(0, len(moved), 2000):
            d = np.linalg.norm(moved[k:k + 2000, None] - skin[None], axis=2).min(1)
            far = max(far, float(d.max()))
        self.assertLess(far, 2.0 * P.LOD_STEPS[0])

    def test_strand_normals_are_their_roots_skin_normal(self):
        """Each strand's three vertices carry one unit normal, its root's skin normal, so it shades as the coat
        beneath it; the strand leans off that surface by the coats' lift (8-24 deg)."""
        for sign in (1, -1):
            m, (sv, st, *_rest) = grown(sign, 1)
            n = m["strand_normals"]
            with self.subTest(sign=sign):
                self.assertEqual(n.shape, sv.shape)
                self.assertLess(float(np.abs(np.linalg.norm(n, axis=1) - 1.0).max()), 1e-9)
                tri_n = n.reshape(-1, 3, 3)
                self.assertLess(float(np.abs(tri_n - tri_n[:, :1]).max()), 1e-12)
                tri = sv.reshape(-1, 3, 3)
                growth = tri[:, 2] - tri[:, :2].mean(1)
                growth /= np.linalg.norm(growth, axis=1, keepdims=True)
                lift = np.degrees(np.arcsin(np.clip((growth * tri_n[:, 0]).sum(1), -1.0, 1.0)))
                self.assertGreater(float(lift.min()), min(F.STRANDS["lift_deg"][0], F.GUARD["lift_deg"][0]) - 1e-6)
                self.assertLess(float(lift.max()), max(F.STRANDS["lift_deg"][1], F.GUARD["lift_deg"][1]) + 1e-6)

    def test_every_strand_faces_outward(self):
        """Each strand's face looks the way its root's normal does: a strand facing into the skin renders as a dark
        backface in Cycles and is culled by a one-sided Unreal material (s115-s120 wound every strand inward)."""
        for sign in (1, -1):
            for lod in (0, 1):
                m, (sv, *_rest) = grown(sign, lod)
                tri = sv.reshape(-1, 3, 3)
                fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
                fn /= np.linalg.norm(fn, axis=1, keepdims=True)
                dots = (fn * m["strand_normals"].reshape(-1, 3, 3)[:, 0]).sum(1)
                with self.subTest(sign=sign, lod=lod, least=float(dots.min())):
                    self.assertGreater(float(dots.min()), 0.5)

    def test_no_strand_grows_on_a_pad(self):
        """The pads (nyaakoto_tp_paws.pad_faces) lie within PAD_REACH of the channel; every strand's root is further."""
        self.assertGreater(min(F.STRANDS["clear_m"], F.GUARD["clear_m"]), P.PAD_REACH)
        for sign in (1, -1):
            m, (sv, *_rest) = grown(sign, 0)
            root = sv.reshape(-1, 3, 3)[:, :2].mean(1)
            with self.subTest(sign=sign):
                self.assertGreater(float(P.channel_sdf(root, m["skeleton"]["frame"]).min()), P.PAD_REACH)

    def test_same_seed_same_strands(self):
        m, (sv, *_rest) = grown(1, 1)
        again = F.grow(m, F.LOD_DENSITY[1])[0]
        self.assertTrue(np.array_equal(sv, again))


if __name__ == "__main__":
    unittest.main()
