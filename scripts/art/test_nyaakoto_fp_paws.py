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

    def test_the_rigs_nigiri_is_the_envelope_the_skin_is_carved_to(self):
        """The rebuilt rig's wrap is the envelope the paw is carved to. This
        was an expected failure until the W18 rebuild (runbook step 3,
        2026-10-25): the first wrap's tilted turns stood up to about 4.6 mm
        off the stave, overhanging its underlay.

        - Over the strip's reach (yumi_nigiri.reach), where grip_ab adds the
          strip to the envelope, no rig vertex lies more than CARVE_GAP
          outside it, so the carved skin never enters the leather.
        - In every 4 mm across the strip's covered span, the strip's crest
          reaches the envelope within CARVE_GAP, so the paw never floats on
          it.

        The domain was |z| < 0.11 m until the rebuild's step 5 (root's review
        of s5_envelope_diag.txt, 2026-10-25). That window was chosen, not
        derived, and reached what the envelope does not model: the nearest
        rattan band below the grip (0.867 mm, unchanged since before the
        rebuild), and the underlay's end rings at +/-GRIP_HALF with one
        hand-wobbled strip vertex past the reach (up to 0.338 mm), all 3.6 mm
        or more from the skin. test_no_bow_vertex_lies_inside_the_carved_paw
        covers the bow's whole nearby extent directly."""
        import yumi_draw as YD
        import yumi_nigiri as NG
        V = self._rig()
        lo, hi = NG.reach(YD.GRIP_HALF)
        V = V[(V[:, 2] >= lo) & (V[:, 2] <= hi)]
        self.assertGreater(len(V), 0)
        d = P.grip_sdf(V)
        self.assertTrue(np.isfinite(d).all())
        self.assertLessEqual(float(d.max()), P.CARVE_GAP)
        lo, hi = NG.covered_span(YD.GRIP_HALF)
        for z0 in np.arange(lo, hi - 0.004, 0.004):
            sl = (V[:, 2] >= z0) & (V[:, 2] < z0 + 0.004)
            self.assertGreater(int(sl.sum()), 0, f"z {z0:.3f}")
            self.assertGreaterEqual(float(d[sl].max()), -P.CARVE_GAP, f"z {z0:.3f}")

    def test_no_bow_vertex_lies_inside_the_carved_paw(self):
        """Vertex-sampled non-penetration over the bow's nearby extent
        (GRIP_Z): the carved paw's own SDF is positive at every rig vertex of
        the bow there (the string and the arrow lie outside _rig's box).

        This samples the rig's vertices. It is not proof that no triangle's
        surface crosses the skin between them: the renders and the engine
        capture remain the visual check."""
        V = self._rig()
        V = V[(V[:, 2] >= P.GRIP_Z[0]) & (V[:, 2] <= P.GRIP_Z[1])]
        self.assertGreater(len(V), 0)
        s = P.paw_sdf(V, self.skel)[0]
        self.assertTrue(np.isfinite(s).all())
        self.assertGreater(float(s.min()), 0.0)

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

    def test_every_card_faces_out_from_the_skin(self):
        # v4: the front, by winding, is the side a viewer sees. Cut strands leave degenerate quads, skipped.
        V, T, K = self.fur["verts"], self.fur["tris"], P.FUR["segments"]
        face = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
        area = np.linalg.norm(face, axis=1)
        live = area > 1e-14
        card = (np.arange(len(T)) % (self.fur["cards"] * K)) // K      # tris: each quad's first halves, then seconds
        cos = np.einsum("ij,ij->i", face[live] / area[live, None], self.fur["root_normals"][card[live]])
        self.assertGreater(int(live.sum()), 0.99 * len(T))
        self.assertGreater(float(cos.min()), 0.0)

    def test_shading_normals_lean_to_the_skin(self):
        # Bent 0.75 of the way from the card's own normal: unit, and close to the skin's at the card's root.
        nrm, K = self.fur["normals"], P.FUR["segments"]
        self.assertEqual(nrm.shape, self.fur["verts"].shape)
        self.assertTrue(np.allclose(np.linalg.norm(nrm, axis=1), 1.0, atol=1e-9))
        skin = np.repeat(self.fur["root_normals"], 2 * (K + 1), axis=0)
        cos = np.einsum("ij,ij->i", nrm, skin)
        self.assertGreater(float(cos.min()), math.cos(math.radians(20.0)))

    def test_cards_narrow_to_their_tips(self):
        # v5: a clump ends in a point. Cards whose edges slid back off the bow are narrower still.
        K = P.FUR["segments"]
        V = self.fur["verts"].reshape(self.fur["cards"], K + 1, 2, 3)
        ratio = np.linalg.norm(V[:, -1, 1] - V[:, -1, 0], axis=1) / np.linalg.norm(V[:, 0, 1] - V[:, 0, 0], axis=1)
        self.assertAlmostEqual(float(np.median(ratio)), P.FUR["tip_width"], delta=0.005)
        # Wider than tip_width only where a root's edge slid back toward its strand, off the bow (within 1 mm of it).
        wide = ratio > P.FUR["tip_width"] + 0.005
        self.assertLess(float(wide.mean()), 0.001)
        if wide.any():
            near = P.grip_sdf(V[wide, 0].reshape(-1, 3)).reshape(-1, 2).min(1)
            self.assertLess(float(near.max()), 0.001)

    def test_form_occlusion_darkens_where_the_paw_closes(self):
        # Against the leather the paw is closed; well away from the grip it is open. Every card's colour is its
        # tabby colour times the occlusion's shade, between the floor and 1.
        sk = self.m["skeleton"]
        both = lambda p: np.minimum(P.paw_sdf(p, sk)[0], P.grip_sdf(p))
        V = self.m["verts"]
        ao = P.form_occlusion(V, P.vertex_normals(V, self.m["tris"]), both)
        self.assertTrue(((ao >= 0) & (ao <= 1)).all())
        g = P.grip_sdf(V)
        self.assertLess(float(ao[g < 0.002].mean()), 0.5)
        self.assertGreater(float(ao[g > 0.015].mean()), 0.9)
        occ = self.fur["occlusion"]
        self.assertEqual(occ.shape, (self.fur["cards"], P.FUR["segments"] + 1))
        self.assertTrue(((occ >= 0) & (occ <= 1)).all())

    def test_the_skin_sits_below_the_coat(self):
        # The skin is the coat's bottom: under each card's root it is darker than that root, where both see the same
        # form (TABBY undercoat).
        sk = self.m["skeleton"]
        both = lambda p: np.minimum(P.paw_sdf(p, sk)[0], P.grip_sdf(p))
        V = self.m["verts"]
        skin = P.skin_colour(self.m, both)[:, 1] / np.maximum(P.tabby_colour(V, sk)[:, 1], 1e-9)
        K = P.FUR["segments"]
        root_col = self.fur["colour"].reshape(self.fur["cards"], K + 1, 2, 3)[:, 0, 0, 1]
        roots = self.fur["roots"]
        card = root_col / np.maximum(P.tabby_colour(roots, sk)[:, 1], 1e-9)
        pick = np.random.default_rng(0).choice(len(roots), 400, replace=False)
        near = np.argmin(np.linalg.norm(roots[pick, None, :] - V[None, :, :], axis=2), axis=1)
        below = skin[near] <= card[pick] * (P.TABBY["undercoat"] + 0.05)
        self.assertGreater(float(below.mean()), 0.95)
        self.assertLessEqual(float(skin.max()), P.TABBY["undercoat"] + 1e-9)

    def test_odd_atlas_rows_run_root_at_the_top(self):
        # create_nyaakoto_fp_fur_textures v4 flips its odd rows, so every card's tip meets the atlas's middle.
        K = P.FUR["segments"]
        uv = self.fur["uv"].reshape(self.fur["cards"], K + 1, 2, 2)
        self.assertEqual(sorted(set(np.round(uv[:, 0, :, 1].ravel(), 9))), [0.0, 1.0])
        self.assertTrue(np.allclose(uv[:, -1, :, 1], 0.5))


class Shells(unittest.TestCase):
    """v6: the coat as shells (fur_shells), on its own 1.6 mm skin."""

    @classmethod
    def setUpClass(cls):
        skel = cls.skel = P.bow_paw_skeleton()
        cls.field = staticmethod(lambda p: P.paw_sdf(p, skel)[0])
        cls.sh = P.fur_shells(skel, cls.field)
        cls.L, cls.n = cls.sh["layers"], cls.sh["base_vertices"]
        cls.V = cls.sh["verts"].reshape(cls.L, cls.n, 3)

    def test_shells_stand_clear_of_the_bow(self):
        self.assertGreaterEqual(float(P.grip_sdf(self.sh["verts"]).min()), P.SHELLS["clear_m"] - 1e-6)

    def test_shells_lie_above_the_skin(self):
        # The shells' skin is coarser than the skin's, so where it cuts a curve a few points of the lowest shell dip
        # under the fine skin, which hides them.
        self.assertGreater(float((self.field(self.sh["verts"]) > 0).mean()), 0.999)

    def test_each_shell_is_higher_and_its_alpha_is_its_height_share(self):
        heights = [float(np.median(self.field(self.V[i]))) for i in range(self.L)]
        self.assertTrue(all(b > a for a, b in zip(heights, heights[1:])), heights)
        A = self.sh["colour"][:, 3].reshape(self.L, self.n)
        self.assertTrue(np.allclose(A, np.array(self.sh["shares"])[:, None]))
        self.assertTrue(0 < self.sh["shares"][0] < self.sh["shares"][-1] <= 1.0)
        self.assertLessEqual(float(self.sh["height_m"].max()), max(P.SHELLS["height_m"].values()) + 1e-12)

    def test_shells_face_out_and_deeper_ones_are_darker(self):
        V, T, N = self.sh["verts"], self.sh["tris"], self.sh["normals"]
        face = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
        cos = np.einsum("ij,ij->i", face, N[T[:, 0]])
        self.assertGreater(float((cos > 0).mean()), 0.99)
        rgb = self.sh["colour"][:, :3].reshape(self.L, self.n, 3)
        ratio = float(rgb[0].mean() / rgb[-1].mean())
        want = (P.SHELLS["deep_shade"] + (1 - P.SHELLS["deep_shade"]) * 0.5 / self.L) / \
            (P.SHELLS["deep_shade"] + (1 - P.SHELLS["deep_shade"]) * (self.L - 0.5) / self.L)
        self.assertAlmostEqual(ratio, want, places=6)

    def test_the_comb_leans_each_shell_along_the_skin(self):
        # Where nothing slid a shell back off the bow, its offset's share along the skin is tan(lean) of its height.
        top = self.V[-1] - self.V[0]
        N = self.sh["normals"][: self.n]
        up = np.einsum("ij,ij->i", top, N)
        along = np.linalg.norm(top - up[:, None] * N, axis=1)
        free = P.grip_sdf(self.V[-1]) > P.SHELLS["clear_m"] + 0.002
        ratio = along[free] / np.maximum(up[free], 1e-9)
        self.assertAlmostEqual(float(np.median(ratio)), math.tan(math.radians(P.SHELLS["lean_deg"])), delta=0.05)


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

    def test_the_cloth_puffs_between_cords_and_not_under_the_splints(self):
        # v5: tight at each binding, swelling between, flat under the splints.
        cords = sorted(K.KOTE["cords"]["at_s"], reverse=True)
        off = np.radians(K.KOTE["splints"]["centre_deg"] + 180.0)          # the sleeve's inner side
        on = np.radians(K.KOTE["splints"]["centre_deg"])
        for c in cords:
            self.assertAlmostEqual(float(K.puff(c, off)), 0.0, places=9)
        for c0, c1 in zip(cords[:-1], cords[1:]):
            self.assertGreater(float(K.puff(0.5 * (c0 + c1), off)), 0.8 * K.KOTE["puff"]["depth"])
            self.assertAlmostEqual(float(K.puff(0.5 * (c0 + c1), on)), 0.0, places=9)

    def test_the_kote_never_touches_the_grip(self):
        for p in self.parts:
            self.assertGreater(float(P.grip_sdf(p["verts"]).min()), 0.002, p["name"])

    def test_the_mon_faces_out_from_the_plate(self):
        self.assertAlmostEqual(float(np.linalg.norm(self.mon["normal"])), 1.0, places=6)
        self.assertAlmostEqual(self.mon["diameter"], K.KOTE["tekko"]["mon_d"])


if __name__ == "__main__":
    unittest.main()
