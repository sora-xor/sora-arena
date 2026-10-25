"""Tests for the shell fur's strand texture (create_nyaakoto_fp_shell_texture).

Run: python3 -m unittest scripts/art/test_nyaakoto_fp_shell_texture.py

- The committed texture is its manifest's, and tiles: its opposite edges
  meet as any two neighbouring columns do.
- Its coverage falls with height, channel by channel.
- Its strands number about (TILE_MM / SPACING_MM)^2.
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


class Committed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PIL import Image

        cls.manifest = json.loads((S.OUT / "manifest.json").read_text(encoding="utf-8"))
        path = S.OUT / S.NAME
        cls.bytes = path.read_bytes()
        with Image.open(path) as im:
            cls.mode = im.mode
            cls.tex = np.asarray(im, np.float64) / 255.0

    def test_it_is_its_manifests(self):
        self.assertEqual(hashlib.sha256(self.bytes).hexdigest(), self.manifest["texture"]["sha256"])
        self.assertEqual(self.mode, "RGBA")
        self.assertEqual(self.tex.shape, (S.SIZE, S.SIZE, 4))

    def test_it_tiles(self):
        for c in range(4):
            t = self.tex[..., c]
            seam = (np.abs(t[:, 0] - t[:, -1]).mean() + np.abs(t[0] - t[-1]).mean()) / 2
            inner = (np.abs(np.diff(t, axis=1)).mean() + np.abs(np.diff(t, axis=0)).mean()) / 2
            self.assertLess(seam, 1.5 * inner + 1e-3, "RGBA"[c])

    def test_coverage_falls_with_height(self):
        means = self.tex.reshape(-1, 4).mean(0)
        self.assertTrue(all(b < a for a, b in zip(means, means[1:])), means)
        self.assertGreater(means[0], 0.5)                      # the undercoat is dense

    def test_strand_count(self):
        want = (S.TILE_MM / S.SPACING_MM) ** 2
        self.assertLess(abs(self.manifest["strands"] - want) / want, 0.15)


if __name__ == "__main__":
    unittest.main()
