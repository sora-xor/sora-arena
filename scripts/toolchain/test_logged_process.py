"""CPU process regressions for inherited output after the launched process exits."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
HELPER = HERE / "run_logged_process.py"


class LoggedProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sora-log-pipe-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / "editor.log"
        self.receipt = self.root / "completion.json"

    def command(self, source, timeout=2):
        return [sys.executable, str(HELPER), "--log", str(self.log),
                "--receipt", str(self.receipt), "--drain-timeout", str(timeout),
                "--", sys.executable, "-c", source, str(self.root)]

    def check_receipt(self):
        data = self.log.read_bytes()
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual(receipt["log_bytes"], len(data))
        self.assertEqual(receipt["log_sha256"], hashlib.sha256(data).hexdigest())
        return receipt

    def wait_file(self, name):
        deadline = time.monotonic() + 5
        while not (self.root / name).is_file():
            if time.monotonic() >= deadline:
                self.fail(f"fixture never created {name}")
            time.sleep(0.01)

    def child_source(self, write_late=True):
        # The child waits for actual parent exit, announces that fact, then
        # blocks until the test releases it. This reproduces inherited-pipe
        # ownership without relying on an assumed parent/child sleep ordering.
        return f"""
import os, sys, time
from pathlib import Path
root = Path(sys.argv[1])
parent = os.getpid()
os.write(1, b'editor\\n')
if os.fork():
    os._exit(0)
deadline = time.monotonic() + 5
while os.getppid() == parent and time.monotonic() < deadline:
    time.sleep(.01)
if os.getppid() == parent:
    os._exit(2)
(root/'parent-exited').touch()
while not (root/'release').exists() and time.monotonic() < deadline:
    time.sleep(.01)
try:
    if {write_late!r}:
        os.write(2, b'child\\x00\\xff\\r\\n')
except BrokenPipeError:
    pass
os.close(1)
os.close(2)
(root/'child-closed').touch()
os._exit(0)
"""

    def test_normal_exit_preserves_raw_stdout_and_stderr(self):
        result = subprocess.run(self.command(
            "import os; os.write(1,b'out\\x00\\xff\\r\\n'); os.write(2,b'err\\n')"), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log.read_bytes(), b"out\x00\xff\r\nerr\n")
        receipt = self.check_receipt()
        self.assertEqual(receipt["process_returncode"], 0)
        self.assertIs(receipt["stream_eof"], True)
        self.assertIsNone(receipt["failure"])

    def test_parent_exit_does_not_finish_collection_before_child_write_and_eof(self):
        process = subprocess.Popen(self.command(self.child_source()), stderr=subprocess.PIPE)
        try:
            self.wait_file("parent-exited")
            self.assertIsNone(process.poll(), "collector returned before inherited stream closed")
            self.assertFalse(self.receipt.exists())
            (self.root / "release").touch()
            _, errors = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, errors)
            self.assertEqual(self.log.read_bytes(), b"editor\nchild\x00\xff\r\n")
            self.assertIs(self.check_receipt()["stream_eof"], True)
        finally:
            (self.root / "release").touch()
            process.communicate(timeout=5)
            self.wait_file("child-closed")

    def test_nonzero_process_exit_is_preserved(self):
        result = subprocess.run(self.command("print('failed'); raise SystemExit(7)"), capture_output=True)
        self.assertEqual(result.returncode, 7)
        receipt = self.check_receipt()
        self.assertEqual(receipt["process_returncode"], 7)
        self.assertEqual(receipt["runner_status"], 7)
        self.assertIs(receipt["stream_eof"], True)

    def test_signalled_process_retains_signal_and_shell_status(self):
        result = subprocess.run(self.command(
            "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"), capture_output=True)
        self.assertEqual(result.returncode, 128 + signal.SIGTERM)
        self.assertEqual(self.check_receipt()["process_returncode"], -signal.SIGTERM)

    def test_eof_before_exit_still_waits_for_actual_exit_status(self):
        result = subprocess.run(self.command(
            "import os,time; os.close(1); os.close(2); time.sleep(.2); raise SystemExit(9)"),
            capture_output=True)
        self.assertEqual(result.returncode, 9)
        self.assertEqual(self.check_receipt()["process_returncode"], 9)

    def test_deadline_fails_with_actual_exit_retained_and_log_no_longer_mutable(self):
        process = subprocess.Popen(self.command(self.child_source(), timeout=.1), stderr=subprocess.PIPE)
        try:
            self.wait_file("parent-exited")
            _, errors = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 125, errors)
            self.assertIn(b"did not reach EOF", errors)
            receipt = self.check_receipt()
            self.assertEqual(receipt["process_returncode"], 0)
            self.assertIs(receipt["stream_eof"], False)
            self.assertIn("incomplete", receipt["failure"])
            prefix = self.log.read_bytes()
            (self.root / "release").touch()
            self.wait_file("child-closed")
            self.assertEqual(self.log.read_bytes(), prefix)
        finally:
            (self.root / "release").touch()
            process.communicate(timeout=5)
            self.wait_file("child-closed")

    def test_launch_failure_is_explicit_without_a_fabricated_process_exit(self):
        command = self.command("unused")
        command = command[:command.index("--") + 1] + [str(self.root / "missing-executable")]
        result = subprocess.run(command, capture_output=True)
        self.assertEqual(result.returncode, 125)
        receipt = self.check_receipt()
        self.assertIsNone(receipt["process_returncode"])
        self.assertIs(receipt["stream_eof"], False)
        self.assertIn("could not launch", receipt["failure"])

    def test_continuous_descendant_output_cannot_extend_the_deadline(self):
        source = """
import os, sys, time
from pathlib import Path
root = Path(sys.argv[1])
if os.fork():
    os._exit(0)
deadline = time.monotonic() + 3
try:
    while time.monotonic() < deadline:
        os.write(1, b'x' * 4096)
except BrokenPipeError:
    pass
os.close(1)
os.close(2)
(root/'child-closed').touch()
os._exit(0)
"""
        result = subprocess.run(self.command(source, timeout=.1), capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 125, result.stderr)
        receipt = self.check_receipt()
        self.assertIs(receipt["stream_eof"], False)
        self.assertGreater(receipt["log_bytes"], 0)
        self.wait_file("child-closed")

    def test_invalid_deadlines_fail_without_starting_process(self):
        for timeout in (0, -1, "nan", "inf"):
            result = subprocess.run(self.command("raise SystemExit('must not launch')", timeout),
                                    capture_output=True)
            self.assertEqual(result.returncode, 125)
            self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
