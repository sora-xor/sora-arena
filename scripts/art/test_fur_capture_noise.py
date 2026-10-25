"""Tests for fur_capture_noise: the fur speckle measurement for the run-up comparison.

Run: python3 -m unittest scripts/art/test_fur_capture_noise.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fur_capture_noise as F  # noqa: E402


def frame(h=60, w=80, stave_grain=0.02):
    """A dark warm background, a white fur patch (rows 10-40, cols 10-40) and a black stave (cols 50-60) with a
    faint checker grain of ``stave_grain``, as lacquer has some."""
    img = np.zeros((h, w, 3))
    img[...] = (0.35, 0.25, 0.18)
    img[10:40, 10:40] = 0.8
    img[:, 50:60] = (0.03, 0.025, 0.02)
    yy, xx = np.mgrid[0:h, 50:60]
    img[:, 50:60] += (((yy + xx) % 2) * stave_grain)[..., None]
    ids = np.zeros((h, w, 3))
    ids[10:40, 10:40] = (0.0, 0.0, 1.0)
    ids[:, 50:60] = (1.0, 0.0, 0.0)
    return img, ids


def speckle(img, rng, amount=0.12):
    """Dither-like salt noise on the fur patch only."""
    out = img.copy()
    noise = (rng.random((30, 30)) < 0.3) * amount
    out[10:40, 10:40] -= noise[..., None]
    return out


class Measure(unittest.TestCase):
    def test_speckled_fur_reads_noisier_than_smooth_fur(self):
        img, ids = frame()
        smooth = F.hold_noise(img, ids)
        noisy = F.hold_noise(speckle(img, np.random.default_rng(3)), ids)
        self.assertLess(smooth["fur"]["residual_mean"], 1e-9)
        self.assertGreater(noisy["fur"]["residual_mean"], 0.01)
        self.assertGreater(noisy["fur_over_bow"], smooth.get("fur_over_bow", 0.0))

    def test_only_bright_unsaturated_pixels_in_the_paw_class_count(self):
        img, ids = frame()
        r = F.hold_noise(img, ids)
        self.assertEqual(r["fur"]["pixels"], (30 - 2 * F.ERODE_PX) ** 2)    # eroded, the stave and ground excluded
        self.assertEqual(r["bow"]["pixels"], 60 * 8 - 2 * 8)                # eroded by 1, at the image edges too

    def test_a_perfectly_smooth_control_gives_no_ratio(self):
        img, ids = frame(stave_grain=0.0)
        r = F.hold_noise(speckle(img, np.random.default_rng(5)), ids)
        self.assertNotIn("fur_over_bow", r)
        self.assertEqual(r["bow"]["residual_mean"], 0.0)

    def test_a_camera_hold_has_no_control(self):
        img, _ids = frame()
        r = F.hold_noise(img)
        self.assertNotIn("bow", r)
        self.assertGreater(r["fur"]["pixels"], 0)


class Run(unittest.TestCase):
    def write_run(self, tmp, tamper=False):
        from PIL import Image

        run = Path(tmp)
        img, ids = frame()
        files = {}
        for name, a in (("rest.png", speckle(img, np.random.default_rng(1))), ("rest_ids.png", ids),
                        ("paw.png", img)):
            Image.fromarray((np.clip(a, 0, 1) * 255).round().astype(np.uint8)).save(run / name)
            files[name] = hashlib.sha256((run / name).read_bytes()).hexdigest()
        if tamper:
            files["paw.png"] = "0" * 64
        (run / "manifest.json").write_text(json.dumps({"requested_holds": ["rest", "paw"], "files": files,
                                                        "id_files": {"rest": "rest_ids.png"},
                                                        "highres_runup": {"r.HighResScreenshotDelay": 4}}))
        return run

    def test_a_run_is_measured_per_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = F.run_noise(self.write_run(tmp))
            self.assertEqual(sorted(r["holds"]), ["paw", "rest"])
            self.assertIn("fur_over_bow", r["holds"]["rest"])
            self.assertEqual(r["highres_runup"], {"r.HighResScreenshotDelay": 4})

    def test_a_file_unlike_its_manifest_hash_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(F.NoiseError):
                F.run_noise(self.write_run(tmp, tamper=True))

    def test_the_command_never_overwrites_its_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.write_run(tmp)
            out = Path(tmp) / "noise.json"
            self.assertEqual(F.main([str(run), "--out", str(out)]), 0)
            self.assertEqual(F.main([str(run), "--out", str(out)]), 1)


if __name__ == "__main__":
    unittest.main()
