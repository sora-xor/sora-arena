"""Host-only doctor tests; create fake engine files and never invoke Build.sh."""

import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("sora_toolchain_doctor", Path(__file__).with_name("doctor.py"))
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)


class InterimEngineSelection(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sora-doctor-interim-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.engine = self.root / "UE_5.8"
        self.version_path = self.engine / "Engine/Build/Build.version"
        self.version_path.parent.mkdir(parents=True)
        build_sh = self.engine / "Engine/Build/BatchFiles/Mac/Build.sh"
        build_sh.parent.mkdir(parents=True)
        build_sh.write_text("#!/bin/sh\nexit 99\n")
        self.editor = self.engine / "Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
        self.editor.parent.mkdir(parents=True)
        self.editor.write_text("#!/bin/sh\nexit 99\n")
        self.editor.chmod(0o755)
        self.sdk = self.root / "MacOSX.sdk"
        self.sdk.mkdir()
        self.developer = self.root / "Xcode.app/Contents/Developer"
        self.developer.mkdir(parents=True)

    def set_version(self, patch_version):
        self.version_path.write_text(json.dumps({
            "MajorVersion": 5, "MinorVersion": 8, "PatchVersion": patch_version
        }))

    def inspect(self, interim=None):
        environment = {
            "UE_ROOT": str(self.engine),
            "SORA_DEVELOPER_DIR": str(self.developer),
        }
        if interim is not None:
            environment["SORA_INTERIM_UE_VERSION"] = interim

        def fake_command(args, env=None):
            if args[:2] == ["xcodebuild", "-version"]:
                return 0, "Xcode 26.1.1\nBuild version 17B100"
            if args[:2] == ["xcodebuild", "-checkFirstLaunchStatus"]:
                return 0, ""
            if args[:4] == ["xcrun", "--sdk", "macosx", "--show-sdk-path"]:
                return 0, str(self.sdk)
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
             patch.object(doctor.shutil, "disk_usage",
                          return_value=SimpleNamespace(free=200 * 1024 ** 3)):
            return doctor.inspect()

    def test_release_pin_is_default(self):
        self.set_version(2)
        report = self.inspect()
        self.assertEqual(report["engine_mode"], "release")
        self.assertTrue(report["release_prerequisites_ready"])
        self.assertFalse(report["interim_compile_prerequisites_ready"])
        self.assertTrue(report["build_ready"])
        self.assertTrue(report["all_checks_pass"])

    def test_583_requires_exact_opt_in(self):
        self.set_version(3)
        default = self.inspect()
        self.assertFalse(default["build_ready"])
        self.assertFalse(default["release_prerequisites_ready"])
        self.assertEqual(default["selected_engine_version"], "5.8.2")
        interim = self.inspect("5.8.3")
        self.assertEqual(interim["engine_mode"], "interim_compile_diagnostic")
        self.assertTrue(interim["interim_compile_prerequisites_ready"])
        self.assertFalse(interim["release_prerequisites_ready"])
        self.assertTrue(interim["build_ready"])
        self.assertTrue(interim["all_checks_pass"])

    def test_unknown_override_fails_closed(self):
        self.set_version(3)
        for value in ("", "5.8.2", "5.8.3 ", "5.8.4"):
            with self.subTest(value=value):
                report = self.inspect(value)
                self.assertEqual(report["engine_mode"], "invalid")
                self.assertFalse(report["build_ready"])
                self.assertFalse(report["all_checks_pass"])

    def test_interim_requires_installed_editor_binary(self):
        self.set_version(3)
        self.editor.unlink()
        report = self.inspect("5.8.3")
        self.assertFalse(report["interim_compile_prerequisites_ready"])
        self.assertFalse(report["build_ready"])

    def test_opt_in_never_relabels_582_as_interim(self):
        self.set_version(2)
        report = self.inspect("5.8.3")
        self.assertTrue(report["release_prerequisites_ready"])
        self.assertFalse(report["interim_compile_prerequisites_ready"])
        self.assertFalse(report["build_ready"])


if __name__ == "__main__":
    unittest.main()
