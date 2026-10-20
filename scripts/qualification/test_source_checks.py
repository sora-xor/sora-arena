"""Regression tests for failure reporting and the source/release scope boundary."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("source_checks_under_test", Path(__file__).with_name("source_checks.py"))
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


class SourceChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sora-source-checks-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def command(self, name, code):
        return RUNNER.Check(name, "tooling", (sys.executable, "-c", code))

    def run_checks(self, checks, identities=None, groups=None):
        output = self.root / "report"
        identity = {"commit": "test-only", "status": [], "tracked_diff_sha256": "test-only"}
        with patch.object(RUNNER, "ROOT", self.root), patch.object(
            RUNNER, "source_identity", side_effect=identities or [identity, identity]
        ), redirect_stdout(io.StringIO()):
            code = RUNNER.run(checks, groups or ["tooling"], output, 2)
        return code, json.loads((output / "report.json").read_text())

    def test_failure_does_not_hide_subsequent_checks_or_become_an_expected_pass(self):
        code, report = self.run_checks([
            self.command("asset-ledger", "print('unrecorded asset'); raise SystemExit(7)"),
            self.command("later", "print('still tested')"),
        ])
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual([row["status"] for row in report["checks"]], ["failed", "passed"])
        self.assertEqual(report["checks"][0]["exit_code"], 7)
        self.assertIn("unrecorded asset", (self.root / "report/asset-ledger.log").read_text())
        self.assertFalse(report["release_qualified"])

    def test_unavailable_executable_is_blocked_and_nonzero(self):
        code, report = self.run_checks([RUNNER.Check("missing", "tooling", (str(self.root / "absent"),))])
        self.assertEqual(code, 1)
        self.assertEqual(report["checks"][0]["status"], "blocked")
        self.assertIsNone(report["checks"][0]["exit_code"])

    def test_missing_python_dependency_is_a_failure(self):
        code, report = self.run_checks([self.command("dependency", "import nonexistent_sora_test_dependency")])
        self.assertEqual(code, 1)
        self.assertEqual(report["checks"][0]["status"], "failed")

    def test_success_only_qualifies_selected_source_groups(self):
        code, report = self.run_checks([self.command("ok", "assert True")])
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["groups"], ["tooling"])
        self.assertIn("rust", report["groups_not_run"])
        self.assertGreater(len(report["outside_scope"]), 0)
        self.assertFalse(report["release_qualified"])

    def test_changed_sources_fail_even_when_every_command_passes(self):
        code, report = self.run_checks([self.command("ok", "pass")], identities=[{"commit": "before"}, {"commit": "after"}])
        self.assertEqual(code, 1)
        self.assertFalse(report["source_unchanged"])

    def test_existing_output_is_refused_without_overwriting_prior_evidence(self):
        output = self.root / "existing"
        output.mkdir()
        (output / "report.json").write_text('{"status":"passed"}')
        with self.assertRaises(FileExistsError):
            RUNNER.run([], ["tooling"], output, 2)
        self.assertEqual((output / "report.json").read_text(), '{"status":"passed"}')

    def test_assertions_remain_enabled_when_parent_environment_disables_them(self):
        with patch.dict(os.environ, {"PYTHONOPTIMIZE": "1"}):
            code, report = self.run_checks([self.command("assertion", "assert False, 'gate must run'")])
        self.assertEqual(code, 1)
        self.assertEqual(report["checks"][0]["status"], "failed")

    def test_raw_exclusions_are_exact_and_stale_names_fail(self):
        class Sample(unittest.TestCase):
            def test_source(self):
                pass

            def test_raw(self):
                pass

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Sample)
        selected = RUNNER.select_tests(suite, ("Sample.test_raw",))
        self.assertEqual([test._testMethodName for test in RUNNER.flatten(selected)], ["test_source"])
        with self.assertRaisesRegex(ValueError, "no longer matches"):
            RUNNER.select_tests(unittest.defaultTestLoader.loadTestsFromTestCase(Sample), ("Sample.test_typo",))

    def test_empty_suite_is_not_a_pass(self):
        with self.assertRaisesRegex(ValueError, "No source tests"):
            RUNNER.select_tests(unittest.TestSuite(), ())

    def test_unexpected_skip_is_not_a_pass(self):
        module = self.root / "test_skipped.py"
        module.write_text("import unittest\nclass Missing(unittest.TestCase):\n @unittest.skip('dependency unavailable')\n def test_required(self): pass\n")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(RUNNER.unit_tests(str(module)), 1)

    def test_lfs_pointer_cannot_count_as_verified_asset_bytes(self):
        (self.root / "asset.fbx").write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:example\n")
        with patch.object(RUNNER, "ROOT", self.root), patch.object(
            RUNNER.subprocess, "check_output", return_value=b'{"files":[{"name":"asset.fbx"}]}'
        ) as command, redirect_stdout(io.StringIO()):
            self.assertEqual(RUNNER.lfs_materialized(), 1)
            command.assert_called_with(["git", "lfs", "ls-files", "--json"], cwd=self.root)
            (self.root / "asset.fbx").write_bytes(b"materialized bytes")
            self.assertEqual(RUNNER.lfs_materialized(), 0)

    def test_empty_lfs_inventory_cannot_claim_materialization(self):
        with patch.object(RUNNER.subprocess, "check_output", return_value=b'{"files":[]}'):
            with self.assertRaisesRegex(ValueError, "No current-tree LFS"):
                RUNNER.lfs_materialized()

    def test_native_parity_class_is_outside_source_scope(self):
        self.assertEqual(RUNNER.SOURCE_CLASSES["scripts/unreal/test_parity_guards.py"], ("SourceIdentityCoverageTests",))

    def test_inventory_is_unique_explicit_and_keeps_ledger_mandatory(self):
        checks = RUNNER.checks()
        self.assertEqual(len({check.name for check in checks}), len(checks))
        self.assertEqual({check.group for check in checks}, set(RUNNER.GROUPS))
        ledger = next(check for check in checks if check.name == "asset-ledger")
        self.assertIn("scripts/assets/validate_asset_ledger.py", ledger.command)
        self.assertNotIn("--require-local", ledger.command)
        images = next(check for check in checks if check.name == "source-images")
        self.assertEqual(images.group, "assets")
        self.assertIn("scripts/unreal/validate_source_images.py", images.command)
        self.assertIn("--json", images.command)
        self.assertTrue(any(check.name == "source-content" for check in checks))
        self.assertFalse(any("UnrealEditor" in token or "build-bridge" in token for check in checks for token in check.command))


if __name__ == "__main__":
    unittest.main()
