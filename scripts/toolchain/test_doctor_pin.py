"""Host-only tests of the exact UE pin in doctor.py; fake engine files, never run Unreal."""

import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("sora_toolchain_doctor_pin", Path(__file__).with_name("doctor.py"))
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)
PIN = doctor.PINS["unreal"]
RUST = doctor.PINS["rust"]


class EnginePin(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sora-doctor-pin-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.engine = self.root / "UE_5.8"
        build = self.engine / "Engine/Build"
        (build / "BatchFiles/Mac").mkdir(parents=True)
        (build / "BatchFiles/Mac/Build.sh").write_text("#!/bin/sh\nexit 99\n")
        (build / "InstalledBuild.txt").write_text("fake-installed-build\n")
        self.editor = self.engine / "Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
        self.editor.parent.mkdir(parents=True)
        self.editor.write_text("#!/bin/sh\nexit 99\n")
        self.editor.chmod(0o755)
        for plugin in PIN["plugins"].values():
            self.write_plugin(plugin["descriptor"], plugin["version"], plugin["version_name"])
        self.write_build()
        self.sdk = self.root / "MacOSX.sdk"
        self.sdk.mkdir()
        self.developer = self.root / "Xcode.app/Contents/Developer"
        self.developer.mkdir(parents=True)
        self.rustc = (0, f"release: {RUST['version']}\ncommit-hash: {RUST['commit_hash']}")
        self.calls = []

    def write_build(self, **overrides):
        major, minor, patch_version = (int(part) for part in PIN["version"].split("."))
        data = {"MajorVersion": major, "MinorVersion": minor, "PatchVersion": patch_version,
                "Changelist": PIN["changelist"], "CompatibleChangelist": PIN["compatible_changelist"],
                "IsLicenseeVersion": PIN["is_licensee_version"], "IsPromotedBuild": PIN["is_promoted_build"],
                "BranchName": PIN["branch"]}
        data.update(overrides)
        (self.engine / "Engine/Build/Build.version").write_text(json.dumps(data))

    def write_plugin(self, descriptor, version, version_name):
        path = self.engine / descriptor
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"FileVersion": 3, "Version": version, "VersionName": version_name}))

    def inspect(self, transitional=None, metal_available=True):
        environment = {"UE_ROOT": str(self.engine), "SORA_DEVELOPER_DIR": str(self.developer)}
        if transitional is not None:
            environment["SORA_INTERIM_UE_VERSION"] = transitional

        def fake_command(args, env=None, cwd=None):
            self.calls.append(args)
            if args == ["rustc", "-vV"]:
                return self.rustc
            if args[:2] == ["xcodebuild", "-version"]:
                return 0, "Xcode 26.1.1\nBuild version 17B100"
            if args[:2] == ["xcodebuild", "-checkFirstLaunchStatus"]:
                return 0, ""
            if args[:4] == ["xcrun", "--sdk", "macosx", "--show-sdk-path"]:
                return 0, str(self.sdk)
            if args[:4] == ["xcrun", "--sdk", "macosx", "metal"]:
                return (0, "Apple metal version test") if metal_available else (1, "missing Metal Toolchain")
            if args[:3] == ["git", "lfs", "version"]:
                return 0, "git-lfs/3.8.0"
            if len(args) >= 5 and args[:2] == ["git", "-C"] and args[3:5] == ["config", "--local"]:
                return 0, "git-lfs filter-process"
            if args[-1] == "--version" and "blender" in args[0].lower():
                return 0, "Blender 5.2.2"
            raise AssertionError(f"unexpected doctor command: {args}")

        with patch.dict(os.environ, environment, clear=True), \
             patch.object(doctor, "command", side_effect=fake_command), \
             patch.object(doctor.platform, "system", return_value="Darwin"), \
             patch.object(doctor.platform, "platform", return_value="macOS-test"), \
             patch.object(doctor.shutil, "disk_usage", return_value=SimpleNamespace(free=200 * 1024 ** 3)):
            return doctor.inspect()

    def assert_blocked(self, report, check):
        failed = {entry["name"] for entry in report["checks"] if not entry["ok"]}
        self.assertIn(check, failed)
        self.assertFalse(report["build_ready"])
        self.assertFalse(report["cook_ready"])
        self.assertFalse(report["all_checks_pass"])

    def test_pin_records_the_launcher_build(self):
        self.assertEqual(PIN["version"], "5.8.3")
        self.assertEqual(PIN["changelist"], 58210709)
        self.assertEqual(PIN["compatible_changelist"], 55116800)
        self.assertEqual(PIN["branch"], "++UE5+Release-5.8")
        self.assertEqual((PIN["is_promoted_build"], PIN["is_licensee_version"]), (1, 0))
        self.assertIsNone(PIN["source_commit"])
        self.assertNotIn("interim_compile_diagnostic_version", PIN)
        self.assertEqual(doctor.engine_pin.ENGINE_VERSION, "5.8.3-58210709+++UE5+Release-5.8")

    def test_exact_version_and_changelist_pass(self):
        report = self.inspect()
        self.assertTrue(report["build_ready"])
        self.assertTrue(report["cook_ready"])
        self.assertTrue(report["all_checks_pass"], [c for c in report["checks"] if not c["ok"]])
        self.assertEqual(report["pinned_engine_version"], doctor.engine_pin.ENGINE_VERSION)
        for key in ("engine_root", "developer_dir", "sdk_root"):
            self.assertIn(key, report)
        for removed in ("release_prerequisites_ready", "interim_compile_prerequisites_ready",
                        "selected_engine_version", "release_engine_version", "engine_mode"):
            self.assertNotIn(removed, report)

    def test_wrong_changelist_fails(self):
        self.write_build(Changelist=PIN["changelist"] + 1)
        self.assert_blocked(self.inspect(), "unreal_changelist")

    def test_wrong_compatible_changelist_or_branch_fails(self):
        self.write_build(CompatibleChangelist=0)
        self.assert_blocked(self.inspect(), "unreal_compatible_changelist")
        self.write_build(BranchName="++UE5+Main")
        self.assert_blocked(self.inspect(), "unreal_branch")

    def test_unpromoted_or_licensee_build_fails(self):
        self.write_build(IsPromotedBuild=0)
        self.assert_blocked(self.inspect(), "unreal_promoted_build")
        self.write_build(IsLicenseeVersion=1)
        self.assert_blocked(self.inspect(), "unreal_licensee_version")
        with self.assertRaisesRegex(RuntimeError, "unreal_licensee_version: 1 != 0"):
            doctor.engine_pin.require_engine_root(self.engine)
        build = json.loads((self.engine / "Engine/Build/Build.version").read_text())
        del build["IsPromotedBuild"]
        (self.engine / "Engine/Build/Build.version").write_text(json.dumps(build))
        self.assert_blocked(self.inspect(), "unreal_promoted_build")

    def test_previous_hotfix_fails(self):
        self.write_build(PatchVersion=2)
        self.assert_blocked(self.inspect(), "unreal")
        self.assert_blocked(self.inspect("5.8.2"), "unreal")

    def test_source_build_fails_distribution(self):
        (self.engine / "Engine/Build/InstalledBuild.txt").unlink()
        self.assert_blocked(self.inspect(), "unreal_distribution")

    def test_plugin_version_mismatch_or_absence_fails(self):
        name, plugin = next(iter(PIN["plugins"].items()))
        self.write_plugin(plugin["descriptor"], plugin["version"] + 1, plugin["version_name"])
        self.assert_blocked(self.inspect(), "unreal_plugins")
        (self.engine / plugin["descriptor"]).unlink()
        report = self.inspect()
        self.assert_blocked(report, "unreal_plugins")
        entry = next(c for c in report["checks"] if c["name"] == "unreal_plugins")
        self.assertIsNone(entry["actual"][name])

    def test_missing_build_version_fails(self):
        (self.engine / "Engine/Build/Build.version").unlink()
        self.assert_blocked(self.inspect(), "unreal")

    def test_missing_editor_binary_fails(self):
        self.editor.unlink()
        self.assert_blocked(self.inspect(), "editor_binary")

    # TODO: remove SORA_INTERIM_UE_VERSION handling after Wave A (these two tests too).
    def test_transitional_variable_at_pin_is_a_no_op(self):
        self.assertEqual(self.inspect("5.8.3"), self.inspect())

    def test_transitional_variable_other_values_fail(self):
        for value in ("", "5.8.2", "5.8.3 ", "5.8.4", "5.8"):
            with self.subTest(value=value):
                self.assert_blocked(self.inspect(value), "transitional_engine_variable")

    def test_missing_metal_blocks_cook_but_not_code_build(self):
        report = self.inspect(metal_available=False)
        self.assertTrue(report["build_ready"])
        self.assertFalse(report["cook_ready"])
        self.assertFalse(report["all_checks_pass"])

    def test_rust_checks_are_wired(self):
        report = self.inspect()
        self.assertIn(["rustc", "-vV"], self.calls)
        names = {entry["name"] for entry in report["checks"]}
        self.assertTrue({"rust_toolchain_file", "rustc"} <= names)
        self.assertTrue(report["rust_ready"])
        self.rustc = (0, f"release: 1.97.0\ncommit-hash: {RUST['commit_hash']}")
        report = self.inspect()
        self.assertFalse(report["rust_ready"])
        self.assertFalse(report["all_checks_pass"])

    def test_editor_script_guard_requires_exact_engine_string(self):
        pin = doctor.engine_pin
        self.assertEqual(pin.require_engine_version(pin.ENGINE_VERSION, "test"), pin.ENGINE_VERSION)
        for actual in ("5.8.3", "5.8.3-58210708+++UE5+Release-5.8", "5.8.2-0+++UE5+Release-5.8",
                       pin.ENGINE_VERSION + "-Mac", ""):
            with self.subTest(actual=actual), self.assertRaises(RuntimeError):
                pin.require_engine_version(actual, "test")

    def test_host_preflight_guard_fails_closed(self):
        pin = doctor.engine_pin
        self.assertEqual(pin.require_engine_root(self.engine), PIN["version"])
        with self.assertRaises(RuntimeError):
            pin.require_engine_root(self.engine, ("plugins", "research_plugins"))
        for plugin in PIN["research_plugins"].values():
            self.write_plugin(plugin["descriptor"], plugin["version"], plugin["version_name"])
        pin.require_engine_root(self.engine, ("plugins", "research_plugins"))
        self.write_build(PatchVersion=2)
        with self.assertRaisesRegex(RuntimeError, "unreal: '5.8.2'"):
            pin.require_engine_root(self.engine)


if __name__ == "__main__":
    unittest.main()
