"""Tests for the shell fur's strand textures (create_nyaakoto_fp_shell_texture, v2: clumped strands and a tint).

Run: python3 -m unittest scripts/art/test_nyaakoto_fp_shell_texture.py

- The committed maps are their manifest's, and tile: opposite edges meet as
  any two neighbouring columns do.
- Coverage falls with height, channel by channel, and every channel has
  some: every shell draws tips, so none costs overdraw for nothing.
- Strands and clumps number about (TILE_MM / spacing)^2.
- Clumps: at mid height the strands sit near their clump's centre, and
  partings open between clumps.
- The tint stays in its designed spread.
- The manifest's far field, white gain and composite measure are what
  nyaakoto_fp_paws and composite_measure compute from the committed maps.
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
import create_nyaakoto_fp_shell_texture as S  # noqa: E402
import nyaakoto_fp_paws as P  # noqa: E402


class Committed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PIL import Image

        cls.manifest = json.loads((S.OUT / "manifest.json").read_text(encoding="utf-8"))
        cls.bytes = (S.OUT / S.NAME).read_bytes()
        cls.tint_bytes = (S.OUT / S.TINT_NAME).read_bytes()
        with Image.open(S.OUT / S.NAME) as im:
            cls.mode = im.mode
            cls.tex = np.asarray(im, np.float64) / 255.0
        with Image.open(S.OUT / S.TINT_NAME) as im:
            cls.tint_mode = im.mode
            cls.tint = np.asarray(im, np.float64) / 255.0

    def test_they_are_their_manifests(self):
        self.assertEqual(self.manifest["version"], S.VERSION)
        self.assertEqual(hashlib.sha256(self.bytes).hexdigest(), self.manifest["texture"]["sha256"])
        self.assertEqual(hashlib.sha256(self.tint_bytes).hexdigest(), self.manifest["tint"]["sha256"])
        self.assertEqual((self.mode, self.tex.shape), ("RGBA", (S.SIZE, S.SIZE, 4)))
        self.assertEqual((self.tint_mode, self.tint.shape), ("L", (S.TINT_SIZE, S.TINT_SIZE)))
        self.assertAlmostEqual(self.manifest["tint"]["mean"], float(self.tint.mean()), places=4)

    def test_they_tile(self):
        for name, t in [("RGBA"[c], self.tex[..., c]) for c in range(4)] + [("tint", self.tint)]:
            seam = (np.abs(t[:, 0] - t[:, -1]).mean() + np.abs(t[0] - t[-1]).mean()) / 2
            inner = (np.abs(np.diff(t, axis=1)).mean() + np.abs(np.diff(t, axis=0)).mean()) / 2
            self.assertLess(seam, 1.5 * inner + 1e-3, name)

    def test_coverage_falls_with_height_and_every_shell_has_some(self):
        means = self.tex.reshape(-1, 4).mean(0)
        self.assertTrue(all(b < a for a, b in zip(means, means[1:])), means)
        self.assertGreater(means[0], 0.5)                      # the undercoat is dense
        self.assertGreater(means[3], 0.01)                     # tips reach the top channel
        self.assertGreater(min(P.shell_alphas(list(means))), 0.01)

    def test_strand_and_clump_counts(self):
        for key, mm in (("strand", S.STRAND_MM), ("clump", S.CLUMP_MM)):
            want = (S.TILE_MM / mm) ** 2
            self.assertLess(abs(self.manifest[key]["count"] - want) / want, 0.15, key)

    def test_strands_gather_into_clumps(self):
        lay = S.layout(np.random.default_rng(S.SEED))
        self.assertEqual(len(lay["clumps"]), self.manifest["clump"]["count"])
        g = (np.arange(S.SIZE) + 0.5) / S.SIZE
        yy, xx = np.meshgrid(g, g, indexing="ij")
        d = np.full((S.SIZE, S.SIZE), np.inf)
        for cx, cy in lay["clumps"]:
            dx, dy = xx - cx, yy - cy
            dx -= np.round(dx)
            dy -= np.round(dy)
            d = np.minimum(d, np.hypot(dx, dy) * S.TILE_MM / S.CLUMP_MM)   # in clump spacings
        mid = self.tex[..., 1]                                 # G: 0.40 of the coat's height
        self.assertGreater(float(mid[d < 0.2].mean()), 2.0 * float(mid[d > 0.45].mean()))

    def test_the_tint_stays_in_its_spread(self):
        lo = 1.0 - sum(S.TINT.values())
        self.assertGreaterEqual(float(self.tint.min()), lo - 1.5 / 255)
        self.assertLessEqual(float(self.tint.max()), 1.0)
        self.assertTrue(0.85 < float(self.tint.mean()) < 0.97)

    def test_the_far_field_and_the_measure_are_recomputed(self):
        means = [float(self.tex[..., c].mean()) for c in range(4)]
        t_mean = float(self.tint.mean())
        gain = P.shell_white_gain(means, t_mean)
        self.assertAlmostEqual(self.manifest["far_field"]["white_gain"], gain, places=4)
        self.assertAlmostEqual(self.manifest["far_field"]["composite"], P.shell_far_field(means, t_mean), places=4)
        k = S.SIZE // S.TINT_SIZE
        up = np.repeat(np.repeat(self.tint, k, 0), k, 1)
        self.assertEqual(S.composite_measure(self.tex, up, gain=gain), self.manifest["composite_measure"])


if __name__ == "__main__":
    unittest.main()
