"""Tests for the first-person ID-pixel analysis (analyse_yumi_fp_review), on synthetic images and runs.

Run: python3 -m unittest scripts/art/test_analyse_yumi_fp_review.py

Run fixtures are throwaway capture directories (a manifest and PNGs), so no
original is touched. Codex's review of ad18895: the analysis must fail
clearly, never print an empty analysis, when:
- a requested eye-view ID file is missing or empty;
- dimensions are inconsistent;
- bytes disagree with the manifest's hashes.
It must read the capture's own recorded settings, and keep custom hold
subsets.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse_yumi_fp_review as A  # noqa: E402

H, W = 90, 160                                   # 16:9


def image():
    img = np.zeros((H, W, 3))
    img[60:90, 0:30] = (0.8, 0.0, 0.0)           # the bow, low left, touching the left and bottom edges
    img[40:50, 70:90] = (0.0, 0.8, 0.05)         # the arrow, over the centre
    img[70:80, 30:40] = (0.05, 0.0, 0.8)         # the paw
    img[0:5, 100:160] = (0.9, 0.9, 0.9)          # a bright unsaturated sky: background
    img[10:12, 10:12] = (0.6, 0.4, 0.0)          # a mixed edge pixel: not twice the next channel
    return img


class Analyse(unittest.TestCase):
    def test_parts_are_classified_by_a_dominant_channel(self):
        cls = A.classify(image())
        self.assertEqual(int((cls == 1).sum()), 30 * 30)
        self.assertEqual(int((cls == 2).sum()), 10 * 20)
        self.assertEqual(int((cls == 3).sum()), 10 * 10)
        self.assertEqual(int(cls[0:5, 100:160].max()), 0)       # sky
        self.assertEqual(int(cls[10:12, 10:12].max()), 0)       # mixed

    def test_extents_edges_and_the_reticle(self):
        res = A.analyse(image(), 0.12)
        bow, arrow = res["parts"]["bow"], res["parts"]["arrow"]
        self.assertTrue(bow["touches"]["left"] and bow["touches"]["bottom"])
        self.assertFalse(bow["touches"]["right"] or bow["touches"]["top"])
        self.assertLess(bow["extent_uv"]["u"][1], 0.0)          # left half
        self.assertLess(bow["extent_uv"]["v"][1], 0.0)          # lower half
        self.assertEqual(bow["in_reticle_disc"], 0)
        self.assertGreater(arrow["in_reticle_disc"], 0)
        self.assertTrue(res["reticle_occluded"])
        self.assertAlmostEqual(res["viewmodel_share"], (900 + 200 + 100) / (H * W))

    def test_an_empty_centre_leaves_the_reticle_clear(self):
        img = image()
        img[40:50, 70:90] = 0.0
        res = A.analyse(img, 0.12)
        self.assertFalse(res["reticle_occluded"])
        self.assertEqual(res["parts"]["arrow"]["pixels"], 0)
        self.assertNotIn("extent_uv", res["parts"]["arrow"])

    def test_the_reticle_disc_is_round_in_screen_space(self):
        # 0.12 half-heights at 1080p is 64.8 px, so about pi x 64.8^2 pixels.
        res = A.analyse(np.zeros((1080, 1920, 3)), 0.12)
        self.assertAlmostEqual(res["reticle_disc_pixels"] / (np.pi * 64.8 ** 2), 1.0, delta=0.01)


def write_run(root: Path, holds=("rest", "root", "right_cheek", "paw"), eye=("rest", "root", "right_cheek"),
              ids_enabled=True, size=(W, H)):
    """A capture directory as render_yumi_fp_review.py writes one: lit shots, ID shots and the manifest."""
    w, h = size
    files, id_files, cameras = {}, {}, {}
    for hold in holds:
        lit = root / f"{hold}.png"
        Image.fromarray(np.full((h, w, 3), 90, np.uint8)).save(lit)
        files[lit.name] = hashlib.sha256(lit.read_bytes()).hexdigest()
        cameras[hold] = {"field_of_view_deg": 70.0 if hold in eye else 32.0, "aspect_ratio": w / h,
                         "constrain_aspect_ratio": True, "location_cm": [0.0, 0.0, 0.0],
                         "rotation_deg": [0.0, 0.0, 0.0], "resolution": [w, h]}
        if hold in eye and ids_enabled:
            idf = root / f"{hold}_ids.png"
            img = np.zeros((h, w, 3), np.uint8)
            img[h * 2 // 3:, : w // 5] = (204, 0, 0)          # the bow, low left
            img[h // 2 - 2: h // 2 + 2, w // 2 - 6: w // 2 + 6] = (0, 204, 0)   # the arrow at the centre
            Image.fromarray(img).save(idf)
            files[idf.name] = hashlib.sha256(idf.read_bytes()).hexdigest()
            id_files[hold] = idf.name
    manifest = {"requested_holds": list(holds), "eye_view_holds": list(eye), "ids_enabled": ids_enabled,
                "resolution": [w, h], "cameras": cameras, "files": files, "id_files": id_files,
                "assessment_camera": {"first_person_fov_deg": 70.0, "aspect": [16, 9], "near_plane_cm": 10.0,
                                      "reticle_clear_radius": 0.12},
                "study": {"path": "docs/art-direction/data/yumi_fp_hold_study.json", "sha256": "0" * 64},
                "id_colours": {"bow": [1, 0, 0], "arrow": [0, 1, 0], "paw": [0, 0, 1]}}
    (root / "manifest.json").write_text(json.dumps(manifest))
    return manifest


def snapshot(root: Path):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir())}


class RunFixture(unittest.TestCase):
    """A throwaway capture directory per test, and the failure check every malformed run must meet. No tests here."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def edit(self, **changes):
        m = json.loads((self.root / "manifest.json").read_text())
        m.update(changes)
        (self.root / "manifest.json").write_text(json.dumps(m))
        return m

    def fails(self, *phrases):
        before = snapshot(self.root)
        with self.assertRaises(A.AnalysisError) as ctx:
            A.analyse_run(self.root)
        for phrase in phrases:
            self.assertIn(phrase, str(ctx.exception))
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(A.main(["analyse", str(self.root)]), 1)
        self.assertIn("YUMI_FP_ANALYSIS_FAILED", err.getvalue())
        self.assertFalse((self.root / "analysis.json").exists())             # never an empty analysis
        self.assertEqual(snapshot(self.root), before)                        # the originals are untouched


class Run(RunFixture):
    def test_a_complete_run_analyses_exactly_its_eye_view_holds(self):
        write_run(self.root)
        rec = A.analyse_run(self.root)
        self.assertEqual(list(rec["holds"]), ["rest", "root", "right_cheek"])
        self.assertEqual(rec["reticle_clear_radius"], 0.12)
        self.assertTrue(rec["holds"]["root"]["reticle_occluded"])
        self.assertEqual(rec["holds"]["root"]["camera"]["field_of_view_deg"], 70.0)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(A.main(["analyse", str(self.root)]), 0)
        self.assertTrue((self.root / "analysis.json").is_file())

    def test_a_custom_subset_is_analysed_as_requested(self):
        write_run(self.root, holds=("root", "paw"), eye=("root",))
        self.assertEqual(list(A.analyse_run(self.root)["holds"]), ["root"])

    def test_a_requested_id_file_absent_from_the_manifest_fails(self):
        m = write_run(self.root)
        del m["id_files"]["right_cheek"]
        self.edit(id_files=m["id_files"])
        self.fails("right_cheek: no ID file recorded")

    def test_no_id_files_at_all_fails(self):
        write_run(self.root)
        self.edit(id_files={})
        self.fails("rest: no ID file recorded", "root: no ID file recorded")

    def test_a_missing_id_file_fails(self):
        write_run(self.root)
        (self.root / "root_ids.png").unlink()
        self.fails("root: root_ids.png is missing")

    def test_an_empty_id_file_fails(self):
        write_run(self.root)
        (self.root / "rest_ids.png").write_bytes(b"")
        self.fails("rest: rest_ids.png is empty")

    def test_bytes_that_disagree_with_the_manifest_fail(self):
        write_run(self.root)
        Image.fromarray(np.zeros((H, W, 3), np.uint8)).save(self.root / "root_ids.png")
        self.fails("root: root_ids.png is", "the manifest records")

    def test_an_id_file_without_a_hash_fails(self):
        m = write_run(self.root)
        del m["files"]["rest_ids.png"]
        self.edit(files=m["files"])
        self.fails("rest: rest_ids.png has no hash")

    def test_dimensions_that_are_not_the_capture_resolution_fail(self):
        write_run(self.root)
        self.edit(resolution=[W * 2, H * 2])
        self.fails("the capture's resolution")

    def test_a_camera_aspect_off_the_resolution_fails(self):
        m = write_run(self.root)
        m["cameras"]["root"]["aspect_ratio"] = 4 / 3
        self.edit(cameras=m["cameras"])
        self.fails("root: camera aspect")

    def test_an_id_file_for_a_hold_not_in_view_fails(self):
        m = write_run(self.root)
        m["id_files"]["paw"] = "root_ids.png"
        self.edit(id_files=m["id_files"])
        self.fails("not eye-view holds: ['paw']")

    def test_the_id_pass_off_fails_as_nothing_to_analyse(self):
        write_run(self.root, ids_enabled=False)
        self.fails("the ID pass was off")

    def test_no_eye_view_hold_fails_as_nothing_to_analyse(self):
        write_run(self.root, holds=("paw",), eye=())
        self.fails("no eye-view hold was requested")

    def test_a_manifest_from_before_the_contract_fails(self):
        write_run(self.root)
        m = json.loads((self.root / "manifest.json").read_text())
        for key in ("requested_holds", "eye_view_holds", "ids_enabled", "assessment_camera", "study"):
            del m[key]
        (self.root / "manifest.json").write_text(json.dumps(m))
        self.fails("predates the ID analysis contract")

    def test_a_bad_reticle_radius_fails(self):
        write_run(self.root)
        self.edit(assessment_camera={"reticle_clear_radius": None})
        self.fails("reticle_clear_radius None is not a positive finite number")

    def test_no_manifest_fails(self):
        self.fails("no manifest.json")


NAN, INF = float("nan"), float("inf")


class Malformed(RunFixture):
    """Narrow malformed numbers and types (Codex's review of 841d246, radius-probe.json: a NaN radius
    reported the reticle clear over a covered centre; infinity and true were taken as radii). Each must
    be an AnalysisError naming it: no raw exception, no false success, nothing written, originals intact."""

    def test_nonfinite_boolean_and_nonpositive_radii_fail(self):
        for r in (NAN, INF, -INF, True, False, 0, -0.12, "0.12", None):
            with self.subTest(radius=r):
                write_run(self.root)
                self.edit(assessment_camera={"first_person_fov_deg": 70.0, "aspect": [16, 9], "near_plane_cm": 10.0,
                                             "reticle_clear_radius": r})
                self.fails("reticle_clear_radius", "is not a positive finite number")

    def test_the_probes_nan_no_longer_reports_a_clear_reticle(self):
        # radius-probe.json's case: the arrow covers the centre, and NaN made it "clear".
        write_run(self.root)
        self.edit(assessment_camera={"reticle_clear_radius": NAN})
        with self.assertRaises(A.AnalysisError):
            A.analyse_run(self.root)
        with self.assertRaises(ValueError):
            A.analyse(image(), NAN)

    def test_nonfinite_boolean_and_nonpositive_aspects_fail(self):
        for a in (NAN, INF, 0, -16 / 9, True, "1.78", None):
            with self.subTest(aspect=a):
                m = write_run(self.root)
                m["cameras"]["root"]["aspect_ratio"] = a
                self.edit(cameras=m["cameras"])
                self.fails("root: camera aspect_ratio", "is not a positive finite number")

    def test_a_resolution_must_be_two_positive_integers(self):
        for res in ([0, 90], [-160, 90], [160.0, 90], [True, 90], ["160", "90"], [160], [160, 90, 3], "160x90",
                    None):
            with self.subTest(resolution=res):
                write_run(self.root)
                self.edit(resolution=res)
                self.fails("is not two positive integers")

    def test_ids_enabled_must_be_a_boolean(self):
        for v in ("yes", 1, None):
            with self.subTest(ids_enabled=v):
                write_run(self.root)
                self.edit(ids_enabled=v)
                self.fails("ids_enabled", "is not a boolean")

    def test_holds_must_be_lists_of_names(self):
        write_run(self.root)
        self.edit(requested_holds="rest,root")
        self.fails("requested_holds 'rest,root' is not a list of hold names")
        write_run(self.root)
        self.edit(eye_view_holds=[1, 2])
        self.fails("eye_view_holds [1, 2] is not a list of hold names")

    def test_file_maps_and_records_must_have_their_types(self):
        write_run(self.root)
        self.edit(files=["rest.png"])
        self.fails("files is not a map of names to names")
        write_run(self.root)
        self.edit(id_files={"root": 7})
        self.fails("id_files is not a map of names to names")
        write_run(self.root)
        self.edit(cameras=[])
        self.fails("cameras [] is not a record")

    def test_an_unreadable_or_non_record_manifest_fails(self):
        write_run(self.root)
        (self.root / "manifest.json").write_text("{")
        self.fails("unreadable")
        (self.root / "manifest.json").write_text("[1, 2]")
        self.fails("not a record")


if __name__ == "__main__":
    unittest.main()
