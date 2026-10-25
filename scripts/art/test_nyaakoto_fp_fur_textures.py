"""Tests for the first-person fur-card atlas (create_nyaakoto_fp_fur_textures, v4) and its dither measure.

Run: python3 -m unittest scripts/art/test_nyaakoto_fp_fur_textures.py

- fur_atlas_coverage: the engine's dithered coverage, against a direct
  sampling of its rule, and the footprint's box mean, against a direct sum,
  with and without wrap.
- The committed atlas:
  - its manifest's hashes and dither measure are its own files';
  - at both first-person footprints its speckle variance is at most half
    v3's (V3_SPECKLE, measured on the v3 atlas before it was replaced);
  - its odd rows run root at the top, so the atlas's middle holds only tips.
- The generator's tile: the clump's lower half is covered.
"""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import create_nyaakoto_fp_fur_textures as G  # noqa: E402
import fur_atlas_coverage as C  # noqa: E402

ATLAS = G.OUT
# fur_atlas_coverage on the v3 atlas (3bb60d85...; Saved/NyaakotoFPPaws/Archive/v3_furcards), the speckle the v4
# atlas replaces: each footprint's mean Bernoulli variance of the engine's dithered coverage.
V3_SPECKLE = {"eye_view/digit": 0.170, "eye_view/dorsal": 0.166, "paw_close_up/digit": 0.133,
              "paw_close_up/dorsal": 0.132}


def _alpha():
    from PIL import Image

    with Image.open(ATLAS / "T_NyaakotoFP_FurCards_Albedo.png") as im:
        return np.asarray(im, np.float64)[..., 3] / 255.0


class Measure(unittest.TestCase):
    def test_draw_probability_is_the_engines_rule(self):
        # BlueNoiseCommon.ush: drawn when a - clip + 0.83 x noise - 0.5 > 0, noise uniform in [0, 1).
        noise = (np.arange(200000) + 0.5) / 200000
        for a in (0.0, 0.1, 0.33, 0.415, 0.6, 0.83, 0.95, 1.0):
            direct = float(((a - 0.33 + 0.83 * noise - 0.5) > 0).mean())
            self.assertAlmostEqual(float(C.draw_probability(a, 0.33)), direct, places=4)
        self.assertEqual(float(C.draw_probability(0.0, 0.33)), 0.0)        # an empty texel stays empty
        self.assertEqual(float(C.draw_probability(0.83, 0.33)), 1.0)       # solid from clip + 0.5

    def test_the_box_mean_is_a_direct_sum(self):
        rng = np.random.default_rng(3)
        a = rng.random((12, 10))
        for along, across in ((3, 5), (4, 4), (1, 1)):
            want_wrap = np.zeros_like(a)
            want_zero = np.zeros_like(a)
            for y in range(12):
                for x in range(10):
                    ys = np.arange(y - along // 2, y - along // 2 + along)
                    xs = np.arange(x - across // 2, x - across // 2 + across)
                    want_wrap[y, x] = a[np.ix_(ys % 12, xs % 10)].mean()
                    inside = a[np.ix_(ys[(ys >= 0) & (ys < 12)], xs[(xs >= 0) & (xs < 10)])]
                    want_zero[y, x] = inside.sum() / (along * across)
            self.assertTrue(np.allclose(C.box_mean(a, along, across), want_wrap))
            self.assertTrue(np.allclose(C.box_mean(a, along, across, wrap=False), want_zero))


class CommittedAtlas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ATLAS / "manifest.json").read_text(encoding="utf-8"))
        cls.alpha = _alpha()

    def test_its_manifest_is_its_files(self):
        self.assertEqual(self.manifest["schema_version"], 4)
        for m in self.manifest["maps"].values():
            self.assertEqual(hashlib.sha256((ATLAS / m["file"]).read_bytes()).hexdigest(), m["sha256"], m["file"])
        again = C.measure(self.alpha, G.COLS, G.ROWS, G.CLIP)
        for key, r in self.manifest["dither_measure"]["at"].items():
            for stat in ("dithered_share", "solid_share", "speckle_variance"):
                self.assertAlmostEqual(again["at"][key][stat], r[stat], places=12, msg=f"{key} {stat}")

    def test_at_most_half_v3s_speckle_at_both_views(self):
        at = self.manifest["dither_measure"]["at"]
        self.assertEqual(sorted(at), sorted(V3_SPECKLE))
        for key, v3 in V3_SPECKLE.items():
            self.assertLessEqual(at[key]["speckle_variance"], 0.5 * v3, key)
            self.assertGreater(at[key]["solid_share"], 0.5, key)

    def test_odd_rows_run_root_at_the_top(self):
        rows = self.alpha.mean(1)
        n = int(0.05 * G.TH)
        self.assertGreater(float(rows[:n].mean()), 0.95)                   # row 1's roots, the image's top
        self.assertGreater(float(rows[-n:].mean()), 0.95)                  # row 0's roots, its bottom
        self.assertLess(float(rows[G.TH - n:G.TH + n].mean()), 0.3)        # both rows' tips meet in the middle


class Tile(unittest.TestCase):
    def test_the_clumps_lower_half_is_covered(self):
        alpha, _c, _n, _m = G.tile(np.random.default_rng(G.SEED), 0)
        lower = alpha[G.TH // 2:]                                           # root at the tile's bottom
        self.assertGreater(float((lower >= 0.99).mean()), 0.97)


if __name__ == "__main__":
    unittest.main()
