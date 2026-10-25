"""Tests for run-editor-script.sh's pass rule, on the real wrapper with a fake engine.

Run: python3 -m unittest scripts/toolchain/test_run_editor_script.py

No Unreal and no compiler. Each test builds a throwaway project:
- byte-for-byte copies of the real run-editor-script.sh and
  editor-config-guard.sh;
- a fake doctor.py, whose engine root is the fixture's;
- fake UnrealEditor-Cmd and UnrealEditor binaries that print chosen log
  lines and exit with a chosen status.

Codex's review of the exit evidence (0d1ac7b): the status-1 exception
applied in every mode, so a commandlet's exit 1 with the marker passed. Only
a full editor (--editor) that quits itself may exit 1. These pin that, the
other failures, and the evidence (EDITOR_EXIT and <log>.editor-exit, the
editor's real status beside the wrapper's).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
WRAPPER = HERE / "run-editor-script.sh"
GUARD = HERE / "editor-config-guard.sh"
FAKE_DOCTOR = '''from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def inspect():
    return {"engine_root": str(ROOT / "FakeEngine"), "build_ready": True, "developer_dir": "/tmp",
            "sdk_root": "/tmp"}
'''
FAKE_EDITOR = '''#!/bin/sh
# The fixture's editor: FAKE_LINES as its output, then FAKE_EXIT as its status.
printf '%s\\n' "$FAKE_LINES"
exit "${FAKE_EXIT:-0}"
'''
MARKER = "FIXTURE_DONE"
DONE = f"[2026.10.25-17.00.00:000][  0]LogPython: {MARKER}: 3 captures"
PY_ERROR = "[2026.10.25-17.00.00:000][  0]LogPython: Error: RuntimeError: boom"
TRACEBACK = "Traceback (most recent call last):"


class Wrapper(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        tc = root / "scripts/toolchain"
        tc.mkdir(parents=True)
        shutil.copy2(WRAPPER, tc / WRAPPER.name)
        shutil.copy2(GUARD, tc / GUARD.name)
        (tc / "doctor.py").write_text(FAKE_DOCTOR)
        mac = root / "FakeEngine/Engine/Binaries/Mac"
        for rel in ("UnrealEditor-Cmd", "UnrealEditor.app/Contents/MacOS/UnrealEditor"):
            p = mac / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(FAKE_EDITOR)
            p.chmod(0o755)
        (root / "Fixture.uproject").write_text("{}")
        (root / "Config").mkdir()
        (root / "Config/DefaultEngine.ini").write_text("[Fixture]\n")
        (root / "scripts/unreal").mkdir(parents=True)
        (root / "scripts/unreal/fixture.py").write_text("")
        self.root = root

    def tearDown(self):
        self._tmp.cleanup()

    def test_the_copies_are_the_real_scripts(self):
        for real in (WRAPPER, GUARD):
            self.assertEqual((self.root / "scripts/toolchain" / real.name).read_bytes(), real.read_bytes())

    def run_wrapper(self, mode, status, lines):
        log = self.root / "Saved/fixture.log"
        args = ["bash", str(self.root / "scripts/toolchain/run-editor-script.sh")] + ([mode] if mode else [])
        args += [str(self.root / "scripts/unreal/fixture.py"), MARKER, str(log)]
        env = dict(os.environ, FAKE_EXIT=str(status), FAKE_LINES="\n".join(lines))
        proc = subprocess.run(args, cwd=self.root, env=env, capture_output=True, text=True, timeout=120)
        self.assertIn(f"EDITOR_EXIT={status}", proc.stderr)                 # the editor's own status, always
        self.assertEqual((self.root / "Saved/fixture.log.editor-exit").read_text().strip(), str(status))
        return proc

    def passes(self, mode, status, lines):
        proc = self.run_wrapper(mode, status, lines)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip().splitlines()[-1], DONE.split("LogPython: ", 1)[1])

    def fails(self, mode, status, lines, why):
        proc = self.run_wrapper(mode, status, lines)
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn(why, proc.stderr)

    def test_a_commandlet_exit_1_with_the_marker_fails(self):
        self.fails(None, 1, [DONE], "editor exited 1")

    def test_a_rendering_commandlet_exit_1_with_the_marker_fails(self):
        self.fails("--rhi", 1, [DONE], "editor exited 1")

    def test_a_full_editor_exit_1_with_the_marker_passes_and_keeps_its_status(self):
        self.passes("--editor", 1, [DONE])                                  # editor 1, wrapper 0

    def test_a_full_editor_exit_1_with_a_python_error_fails(self):
        self.fails("--editor", 1, [PY_ERROR, DONE], "1 Python error lines")

    def test_a_full_editor_exit_1_without_the_marker_fails(self):
        self.fails("--editor", 1, ["[x] LogExit: Exiting."], "no completion marker")

    def test_a_full_editor_exit_2_fails(self):
        self.fails("--editor", 2, [DONE], "editor exited 2")

    def test_a_commandlet_exit_0_with_the_marker_passes(self):
        self.passes(None, 0, [DONE])
        self.passes("--rhi", 0, [DONE])

    def test_exit_0_without_the_marker_fails(self):
        for mode in (None, "--rhi", "--editor"):
            with self.subTest(mode=mode):
                self.fails(mode, 0, ["[x] LogExit: Exiting."], "no completion marker")

    def test_exit_0_with_a_traceback_fails(self):
        for mode in (None, "--editor"):
            with self.subTest(mode=mode):
                self.fails(mode, 0, [TRACEBACK, DONE], "1 Python error lines")

    def test_a_killed_editor_fails(self):
        self.fails("--editor", 137, [DONE], "editor exited 137")
        self.fails(None, 137, [DONE], "editor exited 137")


if __name__ == "__main__":
    unittest.main()
