"""Tests for dojo_timber_pilot_verify: read-only comparison, a unique receipt outside the run.

Run: python3 -m unittest scripts/art/test_dojo_timber_pilot_verify.py
"""
from __future__ import annotations

import datetime as dt
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
import dojo_timber_pilot_verify as VF  # noqa: E402


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Verify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.run = self.root / "Local/ArtCache/Pilot"
        for sub in ("Dense", "Fallback", "Shared"):
            (self.run / sub).mkdir(parents=True)
        (self.run / "Dense/SM_A.fbx").write_bytes(b"dense-a")
        (self.run / "Fallback/SM_A_Fallback.fbx").write_bytes(b"fallback-a")
        (self.run / "Shared/T_Noise.png").write_bytes(b"noise")
        (self.root / "scripts").mkdir()
        (self.root / "scripts/gen.py").write_text("gen")
        (self.root / "scripts/lib.py").write_text("lib")
        self.manifest = {
            "kit": "Pilot", "generator": "scripts/gen.py", "generator_sha256": sha(b"gen"),
            "inputs": {"scripts/lib.py": sha(b"lib")},
            "shared_textures": {"Noise": {"file": "Local/ArtCache/Pilot/Shared/T_Noise.png", "sha256": sha(b"noise")}},
            "members": [{"asset": "SM_A", "digest": "d1", "fallback_digest": "f1",
                         "cache_fbx": "Local/ArtCache/Pilot/Dense/SM_A.fbx",
                         "fallback_fbx": "Local/ArtCache/Pilot/Fallback/SM_A_Fallback.fbx"}],
        }
        self.evidence = {"fbx": {
            "Local/ArtCache/Pilot/Dense/SM_A.fbx": {"sha256": sha(b"dense-a"), "bytes": 7, "digest": "d1"},
            "Local/ArtCache/Pilot/Fallback/SM_A_Fallback.fbx": {"sha256": sha(b"fallback-a"), "bytes": 10, "digest": "f1"}}}
        self.checks = {"SM_A:dense": {"ok": True, "metrics": {"folded": 0, "p95": 4.25e-05}}}
        for name, data in (("manifest.json", self.manifest), ("evidence.json", self.evidence), ("checks.json", self.checks)):
            (self.run / name).write_text(json.dumps(data, indent=1) + "\n")
        self.rebuilt_dir = self.root / "rebuilt"
        self.rebuilt_dir.mkdir()
        (self.rebuilt_dir / "T_Noise.png").write_bytes(b"noise")

    def tearDown(self):
        for p in [self.run, *self.run.rglob("*")]:
            if p.exists():
                p.chmod(p.stat().st_mode | stat.S_IWUSR)
        self.tmp.cleanup()

    def everything(self, rebuilt=None, checks=None, archive=None, accept_generator=None):
        manifest, evidence, original = VF.load_run(self.run)
        fbx = VF.compare_fbx(self.root, evidence)
        digests = VF.compare_digests(manifest, evidence, rebuilt or {"SM_A": ("d1", "f1")})
        check_cmp = VF.compare_checks(original, checks if checks is not None else json.loads(json.dumps(self.checks)))
        shared = VF.compare_shared(self.root, manifest, self.rebuilt_dir)
        inputs = VF.compare_inputs(self.root, manifest)
        return VF.verdict(fbx, digests, check_cmp, shared, inputs, archive, accept_generator)

    def test_an_unchanged_run_verifies(self):
        self.assertEqual(self.everything(), (VF.PASSED, []))
        self.assertEqual(VF.PASSED, "GEOMETRY_INPUTS_VERIFIED")
        self.assertIn("Not a re-export, re-bake or re-render", VF.SCOPE)

    def test_never_writes_into_the_run(self):
        receipt = A.receipt(self.run, "r", self.run / "checks.json", 0, "x")
        A.make_read_only(self.run)
        if os.geteuid() == 0:
            self.skipTest("root ignores permission bits")
        status, _ = self.everything()          # would raise PermissionError on any write
        self.assertEqual(status, VF.PASSED)
        self.assertEqual(A.files_digest(A.listing(self.run)), receipt["files_digest"])
        path = VF.receipt_path("Pilot", base=self.root / "Verification")
        VF.write_receipt(path, self.run, {"status": status})
        with self.assertRaises(ValueError):
            VF.write_receipt(self.run / "verify.json", self.run, {})

    def test_a_changed_fbx_is_caught_against_the_original_evidence(self):
        (self.run / "Dense/SM_A.fbx").write_bytes(b"dense-b")
        status, problems = self.everything()
        self.assertEqual(status, "MISMATCH")
        self.assertIn("fbx Local/ArtCache/Pilot/Dense/SM_A.fbx", problems)
        (self.run / "Dense/SM_A.fbx").unlink()
        self.assertFalse(VF.compare_fbx(self.root, self.evidence)[0]["ok"])

    def test_a_rebuilt_digest_must_match_manifest_and_evidence(self):
        status, problems = self.everything(rebuilt={"SM_A": ("d2", "f1")})
        self.assertEqual((status, problems), ("MISMATCH", ["digest SM_A:dense"]))
        status, problems = self.everything(rebuilt={"SM_A": ("d1", "f1"), "SM_B": ("x", "y")})
        self.assertIn("digest SM_B:dense", problems)
        ev = json.loads(json.dumps(self.evidence))
        ev["fbx"]["Local/ArtCache/Pilot/Dense/SM_A.fbx"]["digest"] = "other"
        self.assertFalse(VF.compare_digests(self.manifest, ev, {"SM_A": ("d1", "f1")})[0]["ok"])

    def test_rebuilt_checks_must_be_identical(self):
        changed = json.loads(json.dumps(self.checks))
        changed["SM_A:dense"]["metrics"]["p95"] = 4.26e-05
        self.assertEqual(self.everything(checks=changed)[1], ["checks SM_A:dense"])
        self.assertEqual(self.everything(checks={})[1], ["checks SM_A:dense"])

    def test_shared_textures_are_compared_not_rewritten(self):
        (self.rebuilt_dir / "T_Noise.png").write_bytes(b"other")
        self.assertEqual(self.everything()[1], ["shared Noise"])
        self.assertEqual((self.run / "Shared/T_Noise.png").read_bytes(), b"noise")

    def test_a_changed_input_is_reported_as_such(self):
        (self.root / "scripts/lib.py").write_text("lib2")
        status, problems = self.everything()
        self.assertEqual((status, problems), ("INPUTS_CHANGED", ["input scripts/lib.py"]))

    def test_a_changed_generator_is_inputs_changed_unless_exactly_accepted(self):
        # Codex's counterexample on 82869a4: generator-only drift still verified.
        (self.root / "scripts/gen.py").write_text("changed generator")
        status, problems = self.everything()
        self.assertEqual(status, "INPUTS_CHANGED")
        self.assertTrue(any(p.startswith("generator scripts/gen.py") for p in problems), problems)
        now = sha(b"changed generator")
        self.assertEqual(self.everything(accept_generator=now), (VF.PASSED, []))
        self.assertEqual(self.everything(accept_generator=sha(b"some other generator"))[0], "INPUTS_CHANGED")
        drift = VF.generator_drift(VF.compare_inputs(self.root, self.manifest), now)
        self.assertEqual((drift["accepted"], drift["current_sha256"], drift["manifest_sha256"], drift["pinned_sha256"]),
                         (True, now, sha(b"gen"), now))           # the original hash is kept beside the pin
        wrong = VF.generator_drift(VF.compare_inputs(self.root, self.manifest), sha(b"x"))
        self.assertEqual((wrong["accepted"], wrong["pinned_sha256"]), (False, sha(b"x")))
        self.assertIsNone(VF.generator_drift(VF.compare_inputs(self.root, {**self.manifest, "generator_sha256": now})))

    def test_archive_receipt_comparison(self):
        archive_dir = self.root / "Archive/run1"
        log = self.root / "run.log"
        log.write_text("PILOT_READY\n")
        A.archive(self.run, archive_dir, "run1", log, 0)
        cmp = VF.compare_archive(self.run, archive_dir / "receipt.json")
        self.assertTrue(cmp["ok"])
        self.assertEqual(self.everything(archive=cmp), (VF.PASSED, []))
        for p in [self.run, *self.run.rglob("*")]:
            p.chmod(p.stat().st_mode | stat.S_IWUSR)
        (self.run / "Shared/T_Noise.png").write_bytes(b"tampered")
        cmp = VF.compare_archive(self.run, archive_dir / "receipt.json")
        self.assertEqual((cmp["ok"], cmp["changed"]), (False, ["Shared/T_Noise.png"]))

    def test_receipts_are_unique_and_never_overwritten(self):
        now = dt.datetime(2026, 10, 25, 3, 0, 0, 123456, tzinfo=dt.timezone.utc)
        a = VF.receipt_path("Pilot", base=self.root / "V", now=now, pid=11)
        b = VF.receipt_path("Pilot", base=self.root / "V", now=now, pid=12)
        self.assertNotEqual(a, b)
        self.assertEqual(a.name, "verify_20261025T030000123456Z_11.json")
        VF.write_receipt(a, self.run, {"n": 1})
        with self.assertRaises(FileExistsError):
            VF.write_receipt(a, self.run, {"n": 2})
        self.assertEqual(json.loads(a.read_text()), {"n": 1})
        with self.assertRaises(ValueError):
            VF.write_receipt(self.root / "Frozen/v.json", self.run, {}, frozen=(self.root / "Frozen",))


if __name__ == "__main__":
    unittest.main()
