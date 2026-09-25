"""Host-only Rust pin tests; fake the compiler query and never run cargo."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("sora_toolchain_doctor_rust", Path(__file__).with_name("doctor.py"))
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)
PIN = doctor.PINS["rust"]


def compiler(release=PIN["version"], commit=PIN["commit_hash"]):
    return 0, f"rustc {release} ({commit[:9]} 2026-07-14)\nbinary: rustc\ncommit-hash: {commit}\nrelease: {release}"


class RustPin(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sora-doctor-rust-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.calls = []

    def write_channel(self, channel):
        (self.root / "rust-toolchain.toml").write_text(f'[toolchain]\nchannel = "{channel}"\n')

    def checks(self, root, result):
        def fake_command(args, env=None, cwd=None):
            self.calls.append((args, env, cwd))
            if args == ["rustc", "-vV"]:
                return result
            raise AssertionError(f"unexpected doctor command: {args}")

        with patch.object(doctor, "command", side_effect=fake_command):
            return {check["name"]: check for check in doctor.rust_checks(root)}

    def test_repository_toolchain_file_names_the_pinned_compiler(self):
        checks = self.checks(doctor.ROOT, compiler())
        self.assertTrue(checks["rust_toolchain_file"]["ok"], checks["rust_toolchain_file"])
        self.assertEqual(checks["rust_toolchain_file"]["actual"], PIN["version"])
        self.assertTrue(checks["rustc"]["ok"], checks["rustc"])

    def test_compiler_is_queried_in_the_repository_without_auto_install(self):
        self.write_channel(PIN["version"])
        self.checks(self.root, compiler())
        [(args, env, cwd)] = self.calls
        self.assertEqual(args, ["rustc", "-vV"])
        self.assertEqual(cwd, self.root)
        self.assertEqual(env["RUSTUP_AUTO_INSTALL"], "0")

    def test_floating_or_other_channel_fails(self):
        for channel in ("stable", "1.97", "1.97.0", PIN["version"] + "-aarch64-apple-darwin"):
            with self.subTest(channel=channel):
                self.write_channel(channel)
                checks = self.checks(self.root, compiler())
                self.assertEqual(checks["rust_toolchain_file"]["actual"], channel)
                self.assertFalse(checks["rust_toolchain_file"]["ok"])

    def test_missing_toolchain_file_fails(self):
        checks = self.checks(self.root, compiler())
        self.assertIsNone(checks["rust_toolchain_file"]["actual"])
        self.assertFalse(checks["rust_toolchain_file"]["ok"])

    def test_other_release_or_build_fails(self):
        self.write_channel(PIN["version"])
        for result in (compiler(release="1.97.0"), compiler(commit="0" * 40)):
            with self.subTest(result=result[1]):
                checks = self.checks(self.root, result)
                self.assertFalse(checks["rustc"]["ok"])
                self.assertIn("commit-hash", checks["rustc"]["detail"])

    def test_missing_pinned_toolchain_fails_closed(self):
        self.write_channel(PIN["version"])
        checks = self.checks(self.root, (1, f"error: toolchain '{PIN['version']}-aarch64-apple-darwin' is not installed"))
        self.assertIsNone(checks["rustc"]["actual"])
        self.assertFalse(checks["rustc"]["ok"])
        self.assertIn("not installed", checks["rustc"]["detail"])


if __name__ == "__main__":
    unittest.main()
