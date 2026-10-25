"""Tests for the first-person bow paw's numpy geometry (nyaakoto_fp_paws, nyaakoto_fp_kote).

Run: python3 -m unittest scripts/art/test_nyaakoto_fp_paws.py

Numpy only; a coarse mesh (2 mm) keeps it to about a minute. It proves:
* the skin is one closed, outward, manifold surface;
* it rests on the W18 grip's leather (contact) and never enters it;
* the dewclaw lies under the arrow's pass, the arrow resting on it;
* the banded sampler gives the full grid's surface exactly;
* the fur cards stand clear of the bow, carry atlas UVs, and grow on fur
  only, never on the pads;
* every kote part is closed and wound outward, the cords bind the sleeve
  instead of floating off it, and nothing of the kote touches the grip.

The renders are the visual review; these pin the geometry the renders show.
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nyaakoto_fp_kote as K  # noqa: E402
import nyaakoto_fp_paws as P  # noqa: E402

STEP = 0.002


def signed_volume(V, T):
    return float(np.einsum("ij,ij->i", V[T[:, 0]], np.cross(V[T[:, 1]], V[T[:, 2]])).sum() / 6.0)


class Skin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = P.mesh_bow_paw(step=STEP, smooth=3)
        cls.skel = cls.m["skeleton"]

    def test_closed_outward_manifold(self):
        self.assertTrue(P.is_closed_manifold(self.m["tris"]))
        self.assertGreater(signed_volume(self.m["verts"], self.m["tris"]), 0.0)

    def test_rests_on_the_leather_without_entering_it(self):
        g = P.grip_sdf(self.m["verts"])
        self.assertGreater(float(g.min()), 0.0)                     # never inside the bow
        self.assertGreater(int((g < 0.0008).sum()), 50)             # but holding it

    @staticmethod
    def _rig():
        import yumi_draw as YD
        V = np.load(YD.RIG_GEOMETRY)["rest"]
        return V[(np.abs(V[:, 0]) < 0.03) & (np.abs(V[:, 1]) < 0.03)]       # the bow: string and arrow lie outside

    def test_the_grip_section_is_the_rigs_bare_stave(self):
        # Above the nigiri and below the first rattan group, nothing else is
        # wound on the stave: there the envelope (from the generator's section)
        # must be the stave the rig emits, within 5 um.
        V = self._rig()
        V = V[(V[:, 2] > 0.056) & (V[:, 2] < 0.11)]
        self.assertGreater(len(V), 40)
        self.assertLess(float(np.abs(P.grip_sdf(V)).max()), 5e-6)

    def test_the_digits_wrap_the_nigiri_at_its_centre(self):
        a, b = P.grip_ab(0.0)
        self.assertEqual((P.GRIP_WRAP["a"], P.GRIP_WRAP["b"]), (float(a), float(b)))

    @unittest.expectedFailure
    def test_the_rigs_nigiri_is_the_envelope_the_skin_is_carved_to(self):
        """STALE until the W18 rebuild, on purpose. The committed rig still has
        the first wrap: tilted turns up to about 4.6 mm off the stave,
        overhanging its underlay. The paw is now carved to the rebuilt wrap's
        envelope. Remove the marker with the rebuild: from then this test must
        pass.

        - No rig vertex lies more than CARVE_GAP outside the envelope, so the
          carved skin never enters the leather.
        - In every 4 mm across the strip's covered span, the strip's crest
          reaches the envelope within CARVE_GAP, so the paw never floats on
          it."""
        import yumi_draw as YD
        import yumi_nigiri as NG
        V = self._rig()
        V = V[np.abs(V[:, 2]) < 0.11]
        d = P.grip_sdf(V)
        self.assertLessEqual(float(d.max()), P.CARVE_GAP)
        lo, hi = NG.covered_span(YD.GRIP_HALF)
        for z0 in np.arange(lo, hi - 0.004, 0.004):
            sl = (V[:, 2] >= z0) & (V[:, 2] < z0 + 0.004)
            self.assertGreaterEqual(float(d[sl].max()), -P.CARVE_GAP, f"z {z0:.3f}")

    def test_the_arrow_rests_on_the_dewclaw(self):
        pts, r = self.skel["chains"]["I"]
        top = max(p[2] + rr for p, rr in zip(pts[1:], r[1:]))
        under = P.ARROW_PASS[2] - P.ARROW_SHAFT_R
        self.assertLess(top, under)
        self.assertGreater(top, under - 0.004)                      # close beneath, not a hand's width away
        tip = pts[-1]
        self.assertLess(tip[1], 0.0)                                # on the right side, where the arrow passes

    def test_digits_wrap_the_grip(self):
        for name in P.DIGITS:
            pts, _r = self.skel["chains"][name]
            th = [math.degrees(math.atan2(p[1], p[0])) for p in pts]
            self.assertGreater(th[0] - th[-1], 100.0, name)         # round the left side and the front

    def test_banded_sampling_matches_the_full_grid(self):
        f = lambda p: P.paw_sdf(p, self.skel)[0]  # noqa: E731
        pts = np.vstack([c[0] for c in self.skel["chains"].values()])
        lo, hi = pts.min(0) - 0.03, pts.max(0) + 0.03
        g1, a1 = P.sample_grid(f, lo, hi, 0.004)
        g2, a2 = P.sample_grid_banded(f, lo, hi, 0.004)
        np.testing.assert_array_equal(g1 <= 0, g2 <= 0)
        v1, q1 = P.surface_nets(g1, a1)
        v2, q2 = P.surface_nets(g2, a2)
        np.testing.assert_array_equal(q1, q2)
        np.testing.assert_allclose(v1, v2, atol=0)


class Fur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = P.mesh_bow_paw(step=STEP, smooth=3)
        sk = cls.m["skeleton"]
        cls.fur = P.fur_cards(cls.m, lambda p: P.paw_sdf(p, sk)[0])

    def test_cards_stand_clear_of_the_bow(self):
        self.assertGreater(self.fur["cards"], 500)
        self.assertGreater(float(P.grip_sdf(self.fur["verts"]).min()), 0.0)

    def test_cards_map_into_the_atlas(self):
        uv = self.fur["uv"]
        self.assertTrue(((uv >= 0.0) & (uv <= 1.0)).all())
        c = self.fur["colour"]
        self.assertTrue(((c >= 0.0) & (c <= 1.0)).all())

    def test_no_fur_grows_on_the_pads(self):
        pads = np.array([str(r).startswith("pad") for r in self.m["region"]])
        if pads.any():
            d = np.linalg.norm(self.fur["roots"][:, None, :] - self.m["verts"][pads][None, ::7, :], axis=2).min(1)
            self.assertGreater(float(np.percentile(d, 1)), 0.0005)


class Kote(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skel = P.bow_paw_skeleton()
        cls.parts, cls.mon = K.bow_kote(cls.skel)

    def test_every_part_is_closed_and_outward(self):
        for p in self.parts:
            self.assertTrue(P.is_closed_manifold(p["tris"]), p["name"])
            self.assertGreater(signed_volume(p["verts"], p["tris"]), 0.0, p["name"])

    def test_cords_bind_the_sleeve(self):
        o, a, u, v = K.forearm_frame(self.skel)
        for p in self.parts:
            if not p["name"].startswith("Kote_Cord"):
                continue
            q = p["verts"] - o
            s = -(q @ a)
            radial = q - np.outer(q @ a, a)
            r = np.linalg.norm(radial, axis=1)
            th = np.arctan2(radial @ v, radial @ u)
            surface = np.maximum(K.sleeve_radius(s, th), np.where(K.splint_arc(th) > 0.5,
                                                                 K.splint_base_r(s, th) + K.KOTE["splints"]["thick"], 0.0))
            gap = r - surface
            self.assertLess(float(gap.max()), 0.0045, p["name"])      # within a cord's width of what it binds

    def test_the_kote_never_touches_the_grip(self):
        for p in self.parts:
            self.assertGreater(float(P.grip_sdf(p["verts"]).min()), 0.002, p["name"])

    def test_the_mon_faces_out_from_the_plate(self):
        self.assertAlmostEqual(float(np.linalg.norm(self.mon["normal"])), 1.0, places=6)
        self.assertAlmostEqual(self.mon["diameter"], K.KOTE["tekko"]["mon_d"])


if __name__ == "__main__":
    unittest.main()
