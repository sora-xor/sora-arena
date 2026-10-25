"""Tests for archive_art_run: a complete receipt, never overwritten, run made read-only.

Run: python3 -m unittest scripts/art/test_archive_art_run.py
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive_art_run as A  # noqa: E402


class Archive(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.run = base / "Run"
        (self.run / "Renders").mkdir(parents=True)
        (self.run / "Renders" / "a.png").write_bytes(b"png-a")
        (self.run / "manifest.json").write_text("{}")
        self.log = base / "run.log"
        self.log.write_text("noise\nPILOT_MEMBER x 1 2 3.0\nPILOT_READY 1 members\n")
        self.archive_dir = base / "Archive" / "run1"

    def tearDown(self):
        for p in [self.run, *self.run.rglob("*")]:
            if p.exists() and not p.is_symlink():
                p.chmod(p.stat().st_mode | stat.S_IWUSR)
        self.tmp.cleanup()

    def test_receipt_lists_every_file_with_its_digest(self):
        r = A.archive(self.run, self.archive_dir, "run1", self.log, 0)
        self.assertEqual([f["path"] for f in r["files"]], ["Renders/a.png", "manifest.json"])
        self.assertEqual(r["files"][0]["sha256"], hashlib.sha256(b"png-a").hexdigest())
        self.assertEqual(r["log"]["markers"], ["PILOT_MEMBER x 1 2 3.0", "PILOT_READY 1 members"])
        self.assertEqual(r["exit_code"], 0)
        self.assertEqual(r["totals"]["by_folder"]["Renders"], {"files": 1, "bytes": 5})
        on_disk = json.loads((self.archive_dir / "receipt.json").read_text())
        self.assertEqual(on_disk["files_digest"], A.files_digest(on_disk["files"]))
        self.assertTrue((self.archive_dir / "run.log").exists())

    def test_never_overwrites_an_archive(self):
        A.archive(self.run, self.archive_dir, "run1", self.log, 0)
        for p in [self.run, *self.run.rglob("*")]:
            p.chmod(p.stat().st_mode | stat.S_IWUSR)
        with self.assertRaises(FileExistsError):
            A.archive(self.run, self.archive_dir, "run1", self.log, 0)

    def test_run_is_read_only_afterwards(self):
        A.archive(self.run, self.archive_dir, "run1", self.log, 0)
        if os.geteuid() == 0:
            self.skipTest("root ignores permission bits")
        with self.assertRaises(PermissionError):
            (self.run / "Renders" / "a.png").write_bytes(b"overwritten")
        with self.assertRaises(PermissionError):
            (self.run / "Renders" / "new.png").write_bytes(b"new")

    def test_archive_must_live_outside_the_run(self):
        with self.assertRaises(ValueError):
            A.archive(self.run, self.run / "Archive", "run1", self.log, 0)


if __name__ == "__main__":
    unittest.main()
