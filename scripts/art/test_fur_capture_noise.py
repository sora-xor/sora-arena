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


SETUP = {"fov": 70.0, "mesh_scale": 0.75, "holds": {"rest": {"anchor": [45, -15, -12]}, "paw": {"camera": {}}},
         "sockets_cm": {}, "poses_component_cm": {}, "materials": {"bow": "MI"}, "materials_after_id_pass": {},
         "solved": {}, "id_colours": {}, "control": {"source_sha256": "c"}, "study": {"sha256": "s"},
         "requested_holds": ["rest", "paw"], "ids_enabled": True, "eye_view_holds": ["rest"],
         "resolution": [80, 60], "cameras": {}, "assessment_camera": {"reticle_clear_radius": 0.12},
         "set_materials": {}, "sun": {"lux": 20000.0}, "ev100": 12.97, "exposure_bias": -11.97}


def write_run(root, name="run", runup=4, speckled=True, tamper=False, **override):
    """A capture directory like render_yumi_fp_review's: rest (eye view, with its ID image) and paw (camera)."""
    from PIL import Image

    run = Path(root) / name
    run.mkdir()
    img, ids = frame()
    lit = speckle(img, np.random.default_rng(1)) if speckled else img
    files = {}
    for fname, a in (("rest.png", lit), ("rest_ids.png", ids), ("paw.png", lit)):
        Image.fromarray((np.clip(a, 0, 1) * 255).round().astype(np.uint8)).save(run / fname)
        files[fname] = hashlib.sha256((run / fname).read_bytes()).hexdigest()
    if tamper:
        files["paw.png"] = "0" * 64
    manifest = dict(SETUP, files=files, id_files={"rest": "rest_ids.png"},
                    highres_runup={"r.HighResScreenshotDelay": runup}, level=f"/Game/L_{name}")
    manifest.update(override)
    (run / "manifest.json").write_text(json.dumps(manifest))
    return run


class Run(unittest.TestCase):
    def test_a_run_is_measured_per_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = F.run_noise(write_run(tmp))
            self.assertEqual(sorted(r["holds"]), ["paw", "rest"])
            self.assertIn("fur_over_bow", r["holds"]["rest"])
            self.assertEqual(r["highres_runup"], {"r.HighResScreenshotDelay": 4})

    def test_a_file_unlike_its_manifest_hash_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(F.NoiseError):
                F.run_noise(write_run(tmp, tamper=True))

    def test_empty_or_invalid_requested_holds_fail_rather_than_measure_nothing(self):
        for bad in ([], None, "rest", ["rest", "rest"], ["rest", 3], [""]):
            with self.subTest(requested_holds=bad), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(F.NoiseError) as cm:
                    F.run_noise(write_run(tmp, requested_holds=bad))
                self.assertIn("requested_holds", str(cm.exception))

    def test_eye_view_holds_must_be_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(F.NoiseError):
                F.run_noise(write_run(tmp, eye_view_holds=["rest", "root"]))

    def test_an_eye_view_hold_without_its_id_image_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(F.NoiseError) as cm:
                F.run_noise(write_run(tmp, id_files={}))
            self.assertIn("rest: an eye-view hold with no ID image", str(cm.exception))

    def test_eye_view_holds_need_the_id_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(F.NoiseError) as cm:
                F.run_noise(write_run(tmp, ids_enabled=False))
            self.assertIn("ids_enabled", str(cm.exception))

    def test_the_command_never_overwrites_its_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = write_run(tmp)
            out = Path(tmp) / "noise.json"
            self.assertEqual(F.main([str(run), "--out", str(out)]), 0)
            self.assertEqual(F.main([str(run), "--out", str(out)]), 1)

    def test_the_command_takes_one_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = write_run(tmp)
            out = Path(tmp) / "noise.json"
            self.assertEqual(F.main(["--out", str(out)]), 1)
            self.assertEqual(F.main([str(run), "--compare", str(run), str(run), "--out", str(out)]), 1)


class Compare(unittest.TestCase):
    def test_both_runs_are_measured_on_their_common_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write_run(tmp, "runup4", runup=4, speckled=True)
            smooth = write_run(tmp, "auto", runup=32, speckled=False)
            r = F.compare_runs(raw, smooth)
            self.assertFalse(r["same_runup"])
            h = r["holds"]["rest"]
            self.assertGreater(h["common_pixels"], 0)
            self.assertEqual(h["a_on_common"]["pixels"], h["b_on_common"]["pixels"])        # one region for both
            self.assertGreater(h["a_on_common"]["residual_mean"], h["b_on_common"]["residual_mean"])
            for side in ("a", "b"):                                    # and each run's own selection, reported apart
                self.assertIn("pixels", h[side]["fur"])

    def test_runs_set_up_differently_are_refused(self):
        for key, value in (("ev100", 12.0), ("cameras", {"rest": {"fov": 60}}), ("holds", {"rest": {}})):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                a = write_run(tmp, "a", runup=4)
                b = write_run(tmp, "b", runup=32, **{key: value})
                with self.assertRaises(F.NoiseError) as cm:
                    F.compare_runs(a, b)
                self.assertIn(key, str(cm.exception))

    def test_the_command_compares(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = write_run(tmp, "a", runup=4), write_run(tmp, "b", runup=32, speckled=False)
            out = Path(tmp) / "compare.json"
            self.assertEqual(F.main(["--compare", str(a), str(b), "--out", str(out)]), 0)
            self.assertTrue(json.loads(out.read_text())["compare"])


class Assets(unittest.TestCase):
    def test_two_assets_are_measured_on_their_common_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, after = write_run(tmp, "before"), write_run(tmp, "after", speckled=False)
            r = F.compare_assets(before, after)
            self.assertEqual(sorted(r["holds"]), ["paw", "rest"])
            h = r["holds"]["rest"]
            self.assertEqual(h["a_on_common"]["pixels"], h["b_on_common"]["pixels"])
            self.assertGreater(h["a_on_common"]["residual_mean"], h["b_on_common"]["residual_mean"])
            self.assertTrue(r["study_same"])

    def test_a_hold_solved_in_another_order_is_the_same_hold(self):
        # v5 solved right_cheek_clear first and v4 fourth: its values differ by about 1e-12 cm.
        with tempfile.TemporaryDirectory() as tmp:
            a = write_run(tmp, "a")
            b = write_run(tmp, "b", holds={"rest": {"anchor": [45 + 2e-12, -15, -12]}, "paw": {"camera": {}}},
                          study={"sha256": "t"})
            r = F.compare_assets(a, b)
            self.assertFalse(r["study_same"])

    def test_a_different_setup_is_refused(self):
        for key, value in (("ev100", 12.0), ("highres_runup", {"r.HighResScreenshotDelay": 32}),
                           ("cameras", {"rest": {"fov": 60}}),
                           ("holds", {"rest": {"anchor": [45.001, -15, -12]}, "paw": {"camera": {}}})):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                a, b = write_run(tmp, "a"), write_run(tmp, "b", **{key: value})
                with self.assertRaises(F.NoiseError) as cm:
                    F.compare_assets(a, b)
                self.assertIn(key, str(cm.exception))

    def test_only_the_holds_both_ran_are_compared(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = write_run(tmp, "a")
            b = write_run(tmp, "b", requested_holds=["rest"])
            self.assertEqual(sorted(F.compare_assets(a, b)["holds"]), ["rest"])
            c = write_run(tmp, "c", requested_holds=["paw"], eye_view_holds=[])
            d = write_run(tmp, "d", requested_holds=["rest"])
            with self.assertRaises(F.NoiseError):
                F.compare_assets(c, d)

    def test_the_command_compares_assets_and_takes_one_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = write_run(tmp, "a"), write_run(tmp, "b", speckled=False)
            out = Path(tmp) / "assets.json"
            self.assertEqual(F.main(["--assets", str(a), str(b), "--out", str(out)]), 0)
            self.assertTrue(json.loads(out.read_text())["compare_assets"])
            self.assertEqual(F.main(["--assets", str(a), str(b), "--compare", str(a), str(b), "--out",
                                     str(Path(tmp) / "x.json")]), 1)


if __name__ == "__main__":
    unittest.main()
