"""Tests for check_scoped_validation: the targeted W18 validation's narrow expected-baseline exception.

Run: python3 -m unittest scripts/art/test_check_scoped_validation.py

Each test builds a before report shaped like metric_report.json (21 rows,
03/11/13/16 failing, serialised as the validator writes it), applies one
change, and checks the gate passes only the run root authorised.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_scoped_validation as G  # noqa: E402

BLOCKOUT = [3, 11, 13, 16]


def row(wid, ok=True, n=3):
    if wid in (11, 13, 16):
        return {"id": wid, "key": f"W{wid:02d}_X", "checks": [], "errors": ["missing build_record.json"], "pass": False}
    checks = [{"name": f"c{i}", "measured": 0.1 * i, "expected": 0.1 * i, "tol": 0.01, "pass": True} for i in range(n)]
    errors = [] if ok else ["SM_Weapon_03.fbx: sha256 differs from build_record"]
    return {"id": wid, "key": f"W{wid:02d}_X", "checks": checks, "errors": errors, "pass": ok}


def before_doc():
    weapons = {str(w): row(w, ok=w not in BLOCKOUT) for w in range(21)}
    weapons["18"]["key"] = "W18_Yumi"
    return {"weapons": weapons, "summary": {"weapons": 21, "passed": 17,
                                            "validator": "scripts/art/create_runtime_weapon_validation.py",
                                            "blender": "5.2.2 LTS", "seconds": 28.0}}


def rebuilt(doc):
    """The authorised run: a new W18 row (passing), a new time in the summary, nothing else."""
    out = copy.deepcopy(doc)
    out["weapons"]["18"]["checks"].append({"name": "SM_Weapon_18_lod_triangles", "measured": [37600, 15000, 5600],
                                           "pass": True})
    out["summary"]["seconds"] = 9.4
    return out


LOG = "[validate] W18_Yumi: PASS\n[validate] 17/21 weapons pass\nBlender quit\n"


class Gate(unittest.TestCase):
    def run_gate(self, after, log=LOG, exit_=1, before=None):
        before = before or before_doc()
        b = before if isinstance(before, bytes) else G.serialise(before)
        a = after if isinstance(after, bytes) else G.serialise(after)
        return G.compare(b, a, 18, BLOCKOUT, log, exit_)

    def refused(self, after, why, **kw):
        with self.assertRaises(G.ScopeError) as cm:
            self.run_gate(after, **kw)
        self.assertIn(why, str(cm.exception))

    def test_the_authorised_run_passes_beside_its_real_exit_1(self):
        res = self.run_gate(rebuilt(before_doc()))
        self.assertEqual(res["validator_exit"], 1)                  # kept, not replaced by the scoped result
        self.assertEqual(res["failing_rows"], BLOCKOUT)
        self.assertNotEqual(res["row_before"], res["row_after"])

    def test_a_failing_w18_check_stops(self):
        after = rebuilt(before_doc())
        after["weapons"]["18"]["checks"][0]["pass"] = False
        after["weapons"]["18"]["pass"] = False
        self.refused(after, "does not pass every check")

    def test_a_w18_error_stops(self):
        after = rebuilt(before_doc())
        after["weapons"]["18"]["errors"] = ["T_Weapon_18_ORM.png: missing"]
        self.refused(after, "does not pass every check")

    def test_an_unwritten_w18_row_stops(self):
        after = before_doc()
        after["summary"]["seconds"] = 3.0
        self.refused(after, "the run did not write it")

    def test_a_new_failure_stops(self):
        after = rebuilt(before_doc())
        after["weapons"]["7"]["pass"] = False
        self.refused(after, "not the expected [3, 11, 13, 16]")

    def test_a_blockout_row_that_stops_failing_stops(self):
        after = rebuilt(before_doc())
        after["weapons"]["3"] = row(3, ok=True)
        self.refused(after, "not the expected [3, 11, 13, 16]")

    def test_an_unexpected_pre_run_failure_set_stops(self):
        before = before_doc()
        before["weapons"]["5"]["pass"] = False
        self.refused(rebuilt(before), "failing rows before the run", before=before)

    def test_another_row_changed_by_one_value_stops(self):
        after = rebuilt(before_doc())
        after["weapons"]["4"]["checks"][1]["measured"] = 0.1000001
        self.refused(after, "rows ['4']")

    def test_a_reformatted_report_stops(self):
        after = rebuilt(before_doc())
        self.refused(json.dumps(after, indent=2).encode("utf-8") + b"\n", "its bytes")

    def test_a_before_report_the_validator_did_not_write_stops(self):
        before = json.dumps(before_doc(), indent=2).encode("utf-8")
        self.refused(rebuilt(before_doc()), "does not reproduce its own bytes", before=before)

    def test_reordered_rows_stop(self):
        after = rebuilt(before_doc())
        after["weapons"] = dict(reversed(list(after["weapons"].items())))
        self.refused(after, "order changed")

    def test_a_changed_summary_count_stops(self):
        after = rebuilt(before_doc())
        after["summary"]["weapons"] = 22
        self.refused(after, "summary's weapons changed")

    def test_another_weapon_in_the_log_stops(self):
        log = "[validate] W04_X: PASS\n" + LOG
        self.refused(rebuilt(before_doc()), "not W18_Yumi alone", log=log)

    def test_a_traceback_in_the_log_stops(self):
        self.refused(rebuilt(before_doc()), "traceback", log=LOG + "Traceback (most recent call last):\n")

    def test_a_log_without_the_summary_line_stops(self):
        self.refused(rebuilt(before_doc()), "summary's count", log="[validate] W18_Yumi: PASS\n")

    def test_an_exit_the_summary_does_not_imply_stops(self):
        for code in (0, 134, 137):
            with self.subTest(code=code):
                self.refused(rebuilt(before_doc()), f"exited {code}", exit_=code)

    def test_an_unreadable_report_stops(self):
        self.refused(b"{", "unreadable")


class Command(unittest.TestCase):
    def test_the_command_writes_its_result_and_keeps_the_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "before.json").write_bytes(G.serialise(before_doc()))
            (t / "after.json").write_bytes(G.serialise(rebuilt(before_doc())))
            (t / "validate.log").write_text(LOG)
            args = [sys.executable, str(HERE / "check_scoped_validation.py"), "--weapon", "18",
                    "--expected-failures", "3,11,13,16", "--before", str(t / "before.json"),
                    "--after", str(t / "after.json"), "--log", str(t / "validate.log"), "--validator-exit", "1",
                    "--out", str(t / "result.json")]
            proc = subprocess.run(args, capture_output=True, text=True, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("SCOPED_VALIDATION_OK", proc.stdout)
            self.assertEqual(json.loads((t / "result.json").read_text())["validator_exit"], 1)
            again = subprocess.run(args, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(again.returncode, 0)                   # --out is created exclusively

    def test_a_refusal_exits_1_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "before.json").write_bytes(G.serialise(before_doc()))
            (t / "after.json").write_bytes(G.serialise(before_doc()))
            (t / "validate.log").write_text(LOG)
            proc = subprocess.run([sys.executable, str(HERE / "check_scoped_validation.py"), "--weapon", "18",
                                   "--expected-failures", "3,11,13,16", "--before", str(t / "before.json"),
                                   "--after", str(t / "after.json"), "--log", str(t / "validate.log"),
                                   "--validator-exit", "1", "--out", str(t / "result.json")],
                                  capture_output=True, text=True, timeout=60)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("SCOPED_VALIDATION_FAILED", proc.stderr)
            self.assertFalse((t / "result.json").exists())


if __name__ == "__main__":
    unittest.main()
