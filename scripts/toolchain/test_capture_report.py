"""Reject incomplete, failed or wrong-renderer capture runs even after exit zero."""
import copy
import importlib.util
from pathlib import Path
import unittest

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


if __name__ == "__main__":
    unittest.main()
