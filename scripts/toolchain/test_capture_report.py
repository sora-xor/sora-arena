"""Reject incomplete, failed or wrong-renderer capture runs even after exit zero."""
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

SPEC = importlib.util.spec_from_file_location(
    "capture_report", Path(__file__).with_name("verify-capture-report.py"))
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class CaptureReportTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "devices": [{"rHI": "Metal", "renderMode": "SM6"}],
            "tests": [{"fullTestPath": "SoraCapture.ArtReview.Dojo", "state": "Success",
                       "errors": 0, "entries": []}],
            "failed": 0, "notRun": 0, "inProcess": 0,
        }
        self.log = "Found 1 automation tests based on 'SoraCapture.ArtReview.Dojo'"

    def check(self, report=None, log=None, status=0, shader="sm6"):
        return VERIFY.problems(self.report if report is None else report,
                               self.log if log is None else log, status, shader)

    def test_finished_run_matches_explicit_shader_model(self):
        self.assertEqual(self.check(), [])
        self.assertTrue(self.check(shader="sm5"))

    def test_exit_zero_with_no_tests_is_not_success(self):
        self.report["tests"] = []
        self.assertTrue(self.check())

    def test_partial_report_and_missing_discovery_are_rejected(self):
        self.assertTrue(self.check(log=self.log.replace("Found 1", "Found 2")))
        self.assertTrue(self.check(log=""))
        self.report["inProcess"] = 1
        self.assertTrue(self.check())

    def test_errors_cannot_hide_behind_success_state(self):
        self.report["tests"][0]["entries"] = [{"event": {"type": "Error", "message": "Screenshot missing"}}]
        self.assertTrue(self.check())
        self.report["tests"][0]["entries"] = []
        self.report["tests"][0]["errors"] = 1
        self.assertTrue(self.check())

    def test_failed_test_and_crash_after_tests_are_rejected(self):
        self.assertTrue(self.check(status=1))
        self.report["tests"][0]["state"] = "Fail"
        self.assertTrue(self.check())

    def test_null_renderer_or_missing_device_cannot_qualify_capture(self):
        for rhi in ("", "Null", "N/A"):
            with self.subTest(rhi=rhi):
                report = copy.deepcopy(self.report)
                report["devices"][0]["rHI"] = rhi
                self.assertTrue(self.check(report=report))
        self.report["devices"] = []
        self.assertTrue(self.check(shader="auto"))


class CaptureArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "project with spaces"
        self.engine_base = self.root / "Engine/Binaries/Mac"
        self.engine_base.mkdir(parents=True)
        self.source = self.project / "Saved/Screenshots/SoraArtReview/2x1/DojoEntry.png"
        self.source.parent.mkdir(parents=True)
        def chunk(kind, payload):
            return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
        self.chunk = chunk
        self.png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 1, 8, 2, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(b"\0\xff\0\0\0\xff\0")) + chunk(b"IEND", b""))
        self.source.write_bytes(self.png)
        self.started = self.source.stat().st_mtime_ns - 1
        self.log = "LogTemp: Display: SORA_ART_REVIEW_FRAME " + os.path.relpath(self.source, self.engine_base)
        self.report = {"tests": [{"fullTestPath": "SoraCapture.ArtReview.Dojo"}]}

    def archive(self, output="run-sm6", log=None):
        return VERIFY.archive_frames(self.log if log is None else log, self.report, self.project,
                                     self.engine_base, self.root / output, self.started, 2, 1)

    def test_original_bytes_survive_later_shader_model_capture(self):
        first = self.archive()
        self.assertEqual(first[0]["sha256"], hashlib.sha256(self.png).hexdigest())
        self.archive("run-sm5")
        self.source.write_bytes(b"a later engine run overwrote this file")
        for run in ("run-sm6", "run-sm5"):
            self.assertEqual((self.root / run / first[0]["path"]).read_bytes(), self.png)

    def test_stale_missing_or_unacknowledged_frames_are_rejected(self):
        os.utime(self.source, ns=(self.started - 1, self.started - 1))
        with self.assertRaisesRegex(ValueError, "stale"):
            self.archive()
        self.source.unlink()
        with self.assertRaises(OSError):
            self.archive()
        with self.assertRaisesRegex(ValueError, "no screenshot"):
            self.archive(log="")

    def test_marker_cannot_archive_files_outside_project_screenshots(self):
        outside = self.root / "private.png"
        outside.write_bytes(self.png)
        with self.assertRaises(ValueError):
            self.archive(log="SORA_ART_REVIEW_FRAME " + str(outside))

    def test_truncated_corrupt_or_wrong_size_png_is_rejected(self):
        missing_pixels = self.png[:33] + self.chunk(b"IDAT", zlib.compress(b"")) + self.chunk(b"IEND", b"")
        for data in (self.png[:-12], self.png[:-1] + b"x", b"not png", missing_pixels):
            with self.subTest(data=data[-12:]):
                self.source.write_bytes(data)
                with self.assertRaises(ValueError):
                    self.archive()
        self.source.write_bytes(self.png)
        with self.assertRaisesRegex(ValueError, "dimensions"):
            VERIFY.archive_frames(self.log, self.report, self.project, self.engine_base,
                                  self.root / "wrong-size", self.started, 1920, 1080)

    def test_duplicate_markers_and_overwriting_an_archive_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.archive(log=self.log + "\n" + self.log)
        with self.assertRaises(FileExistsError):
            self.archive()

    def test_non_capture_render_test_does_not_invent_frames(self):
        frames = VERIFY.archive_frames("", {"tests": [{"fullTestPath": "SoraArena.Rendering.EnvironmentCapability"}]},
                                       self.project, self.engine_base, self.root / "capability", self.started, 2, 1)
        self.assertEqual(frames, [])

    def test_registry_fixture_keeps_original_bytes_and_labels_its_scope(self):
        self.report = {"tests": [{"fullTestPath": "SoraCapture.RegistryFixture.Chapter5"}]}
        frames = self.archive(log="SORA_REGISTRY_FIXTURE_FRAME " + str(self.source))
        self.assertEqual((self.root / "run-sm6" / frames[0]["path"]).read_bytes(), self.png)
        self.assertEqual(frames[0]["sha256"], hashlib.sha256(self.png).hexdigest())
        self.assertEqual(frames[0]["capture_kind"], "completed-save registry UI fixture; not playthrough evidence")

    def test_an_art_frame_cannot_stand_in_for_a_missing_registry_capture(self):
        self.report["tests"].append({"fullTestPath": "SoraCapture.RegistryFixture.Chapter4"})
        with self.assertRaisesRegex(ValueError, "RegistryFixture.*no screenshot"):
            self.archive()

    def test_different_capture_markers_cannot_hide_a_reused_path(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.archive(log=self.log + "\nSORA_REGISTRY_FIXTURE_FRAME " + str(self.source))


if __name__ == "__main__":
    unittest.main()
