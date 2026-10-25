"""Tests for check_scoped_validation: the targeted W18 validation's narrow expected-baseline exception.

Run: python3 -m unittest scripts/art/test_check_scoped_validation.py

The fixtures follow the real authored rules: W18's spec
(create_runtime_weapon_specs.py) and the validator's own source
(create_runtime_weapon_validation.py, read, never run). The report has 21
rows, 03/11/13/16 failing, serialised as the validator writes it. W18's
reviewed row has the 11 checks of the report before the rebuild. Its new row
is what validate() appends from a build record like the rebuild's: the same
11, and the normal tilt the current validator adds.

Each test applies one change, and checks the gate passes only the run root
authorised. Probes marks root's four adversarial probes of fe74f78, each of
which that version accepted.
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
import create_runtime_weapon_specs as S  # noqa: E402

BLOCKOUT = [3, 11, 13, 16]
SPEC = S.WEAPONS[18]
VALIDATOR_TEXT = G.VALIDATOR.read_text(encoding="utf-8")
REC = {
    "assets": {"SM_Weapon_18": {"lods": [{"triangles": 68716}, {"triangles": 28860}, {"triangles": 10994}]},
               "SM_Weapon_18_Ya": {"lods": [{"triangles": 5502}, {"triangles": 2310}, {"triangles": 880}]}},
    "textures": {"BaseColor": {"file": "b"}, "ORM": {"file": "o"}, "Mask": {"file": "m"}, "Normal": {"file": "n"}},
    "texel_density_px_per_m": {"mean": 2983.0, "p05": 2943.782620251531},
}
SPEC_MEASURED = {"bow_length": 2.21231, "grip_from_lower_tip": 0.3341, "brace_height": 0.1529, "arrow_length": 0.9815}


def spec_checks(measured):
    return [{"name": c["name"], "method": c["method"], "measured": measured[c["name"]], "expected": c["expected"],
             "tol": c["tol"], "basis": c["basis"], "source": c["source"], "pass": True} for c in SPEC["checks"]]


def asset_checks(asset, lods, coverage):
    return [{"name": f"{asset}_uv0_overlap", "measured": 0.0, "expected": 0.0, "tol": 0.004, "pass": True,
             "coverage": coverage},
            {"name": f"{asset}_fbx_bounds_parity_m", "measured": 1.7e-08, "expected": 0.0, "tol": 0.0001, "pass": True},
            {"name": f"{asset}_lod_triangles", "measured": lods, "budget_lod0": 80000, "pass": True}]


def reviewed_w18():
    """W18's row in the report before the rebuild: 11 checks, from the older build."""
    checks = (asset_checks("SM_Weapon_18", [30600, 12852, 4896], 0.5715)
              + asset_checks("SM_Weapon_18_Ya", [3902, 1638, 624], 0.0985)
              + [{"name": "texel_density_p05_px_per_m", "measured": 3138.1, "expected_min": 1024.0, "pass": True}]
              + spec_checks({"bow_length": 2.21209, "grip_from_lower_tip": 0.3333, "brace_height": 0.1535,
                             "arrow_length": 0.982}))
    return {"id": 18, "key": "W18_Yumi", "checks": checks, "errors": [], "pass": True}


def rebuilt_w18():
    """What validate() appends from REC: the 11, and the normal tilt the current validator adds."""
    checks = (asset_checks("SM_Weapon_18", [68716, 28860, 10994], 0.5802)
              + asset_checks("SM_Weapon_18_Ya", [5502, 2310, 880], 0.0991)
              + [{"name": "normal_tilt_mean", "measured": 0.0424, "expected_min": 0.04, "pass": True,
                  "covered_texels_mean": 0.0515},
                 {"name": "texel_density_p05_px_per_m", "measured": 2943.8, "expected_min": 1024.0, "pass": True}]
              + spec_checks(SPEC_MEASURED))
    return {"id": 18, "key": "W18_Yumi", "checks": checks, "errors": [], "pass": True}


def other_row(wid):
    if wid in (11, 13, 16):
        return {"id": wid, "key": f"W{wid:02d}_X", "checks": [], "errors": ["missing build_record.json"], "pass": False}
    ok = wid != 3
    checks = [{"name": f"c{i}", "measured": 0.1 * i, "expected": 0.1 * i, "tol": 0.01, "pass": True} for i in range(3)]
    return {"id": wid, "key": f"W{wid:02d}_X", "checks": checks,
            "errors": [] if ok else ["SM_Weapon_03.fbx: sha256 differs from build_record"], "pass": ok}


def before_doc():
    weapons = {str(w): (reviewed_w18() if w == 18 else other_row(w)) for w in range(21)}
    return {"weapons": weapons, "summary": {"weapons": 21, "passed": 17,
                                            "validator": "scripts/art/create_runtime_weapon_validation.py",
                                            "blender": "5.2.2 LTS", "seconds": 28.0}}


def rebuilt(doc=None):
    """The authorised run: the new W18 row and a new time in the summary, nothing else."""
    out = copy.deepcopy(doc or before_doc())
    out["weapons"]["18"] = rebuilt_w18()
    out["summary"]["seconds"] = 9.4
    return out


def check(doc, name):
    return next(c for c in doc["weapons"]["18"]["checks"] if c["name"] == name)


LOG = "[validate] W18_Yumi: PASS\n[validate] 17/21 weapons pass\nBlender quit\n"


class Gate(unittest.TestCase):
    def run_gate(self, after, log=LOG, exit_=1, before=None, rec=None, validator=None):
        before = before or before_doc()
        b = before if isinstance(before, bytes) else G.serialise(before)
        a = after if isinstance(after, bytes) else G.serialise(after)
        return G.compare(b, a, 18, BLOCKOUT, log, exit_, SPEC, rec or REC, validator or VALIDATOR_TEXT,
                         S.MIN_TEXEL_DENSITY)

    def refused(self, after, *whys, **kw):
        with self.assertRaises(G.ScopeError) as cm:
            self.run_gate(after, **kw)
        for why in whys:
            self.assertIn(why, str(cm.exception))

    def test_the_authorised_run_passes_beside_its_real_exit_1(self):
        res = self.run_gate(rebuilt())
        self.assertEqual(res["validator_exit"], 1)                  # kept, not replaced by the scoped result
        self.assertEqual(res["failing_rows"], BLOCKOUT)
        self.assertEqual(res["checks_new_since_the_reviewed_row"], ["normal_tilt_mean"])
        self.assertEqual(len(res["checks"]), 12)
        self.assertNotEqual(res["row_before"], res["row_after"])

    def test_the_fixture_follows_the_real_report_before_the_rebuild(self):
        # The archived metric_report.json's W18 row has these 11 checks, in this order, with this metadata.
        names = [c["name"] for c in reviewed_w18()["checks"]]
        self.assertEqual(names, ["SM_Weapon_18_uv0_overlap", "SM_Weapon_18_fbx_bounds_parity_m",
                                 "SM_Weapon_18_lod_triangles", "SM_Weapon_18_Ya_uv0_overlap",
                                 "SM_Weapon_18_Ya_fbx_bounds_parity_m", "SM_Weapon_18_Ya_lod_triangles",
                                 "texel_density_p05_px_per_m", "bow_length", "grip_from_lower_tip", "brace_height",
                                 "arrow_length"])

    # Root's four probes of fe74f78 -----------------------------------------------------------------------------
    def test_probe_1_checks_cut_to_one(self):
        after = rebuilt()
        after["weapons"]["18"]["checks"] = after["weapons"]["18"]["checks"][:1]
        self.refused(after, "are not the validator's inventory")

    def test_probe_2_row_relabelled_w19_with_a_matching_log(self):
        after = rebuilt()
        after["weapons"]["18"]["id"], after["weapons"]["18"]["key"] = 19, "W19_Teppo"
        self.refused(after, "is not W18", "not W18_Yumi alone",
                     log="[validate] W19_Teppo: PASS\n[validate] 17/21 weapons pass\n")

    def test_probe_3_tolerance_widened_with_pass_true(self):
        after = rebuilt()
        c = check(after, "bow_length")
        c["measured"], c["tol"] = 50, 100
        self.refused(after, "bow_length: metadata", "is not the authored")

    def test_probe_4_infinite_measurement_with_pass_true(self):
        after = rebuilt()
        check(after, "bow_length")["measured"] = float("inf")
        self.refused(after, "bow_length: the measurement inf is not a finite number")

    # Identity and inventory ------------------------------------------------------------------------------------
    def test_an_id_that_is_not_the_integer_18(self):
        for bad in ("18", 18.0, True):
            with self.subTest(id=bad):
                after = rebuilt()
                after["weapons"]["18"]["id"] = bad
                self.refused(after, "is not W18")

    def test_a_repeated_check(self):
        after = rebuilt()
        after["weapons"]["18"]["checks"].append(copy.deepcopy(check(after, "brace_height")))
        self.refused(after, "repeats the checks ['brace_height']")

    def test_an_unknown_extra_check(self):
        after = rebuilt()
        after["weapons"]["18"]["checks"].append({"name": "looks_right", "measured": 1.0, "pass": True})
        self.refused(after, "are not the validator's inventory")

    def test_a_reordered_inventory(self):
        after = rebuilt()
        cs = after["weapons"]["18"]["checks"]
        cs[0], cs[1] = cs[1], cs[0]
        self.refused(after, "are not the validator's inventory")

    def test_a_spec_check_that_raised(self):
        after = rebuilt()
        c = check(after, "brace_height")
        c["error"] = "KeyError('Tsuru')"
        self.refused(after, "brace_height: keys")

    def test_build_record_assets_that_are_not_the_specs(self):
        rec = copy.deepcopy(REC)
        rec["assets"]["SM_Weapon_18_Extra"] = {"lods": []}
        self.refused(rebuilt(), "are not the spec's", rec=rec)

    def test_a_row_with_an_extra_key(self):
        after = rebuilt()
        after["weapons"]["18"]["note"] = "ok"
        self.refused(after, "row 18's keys")

    # Fixed metadata --------------------------------------------------------------------------------------------
    def test_changed_spec_metadata(self):
        for field, value in (("basis", "design"), ("source", "trust me"), ("method", "extent_x"),
                             ("expected", 2.0)):
            with self.subTest(field=field):
                after = rebuilt()
                check(after, "bow_length")[field] = value
                self.refused(after, "bow_length: metadata")

    def test_a_raised_lod0_budget(self):
        after = rebuilt()
        check(after, "SM_Weapon_18_lod_triangles")["budget_lod0"] = 200000
        self.refused(after, "SM_Weapon_18_lod_triangles: metadata")

    def test_a_widened_overlap_tolerance(self):
        after = rebuilt()
        check(after, "SM_Weapon_18_uv0_overlap")["tol"] = 0.5
        self.refused(after, "SM_Weapon_18_uv0_overlap: metadata")

    def test_a_lowered_minimum(self):
        after = rebuilt()
        check(after, "normal_tilt_mean")["expected_min"] = 0.0
        self.refused(after, "normal_tilt_mean: metadata")

    def test_metadata_unlike_the_reviewed_rows(self):
        before = before_doc()
        check(before, "arrow_length")["tol"] = 0.02          # the authored tol is 0.01
        self.refused(rebuilt(before), "arrow_length: its metadata differs from the reviewed row's", before=before)

    def test_a_validator_that_no_longer_states_a_rule(self):
        text = VALIDATOR_TEXT.replace('"tol": 0.004, "pass": over <= 0.004', '"tol": 0.04, "pass": over <= 0.04')
        self.assertNotEqual(text, VALIDATOR_TEXT)
        self.refused(rebuilt(), "the validator no longer states 1 rules", validator=text)

    # Measurements, recomputed ----------------------------------------------------------------------------------
    def test_non_finite_or_boolean_measurements(self):
        for bad in (float("nan"), float("-inf"), True, "2.21", None):
            with self.subTest(measured=bad):
                after = rebuilt()
                check(after, "brace_height")["measured"] = bad
                self.refused(after, "is not a finite number")

    def test_a_measurement_outside_its_tolerance_with_pass_true(self):
        after = rebuilt()
        check(after, "arrow_length")["measured"] = 0.9699
        self.refused(after, "arrow_length: 0.9699 is outside 0.98 +/- 0.01")

    def test_the_rounding_slack_and_no_more(self):
        # A measured 0.3033334 passes (0.0299999 off 1/3); the validator records it as 0.30333, 0.0300033 off.
        inside = rebuilt()
        check(inside, "grip_from_lower_tip")["measured"] = 0.30333
        self.run_gate(inside)
        # 0.30332 is 0.0300133 off: more than the rounding, and no passing measurement records as it.
        outside = rebuilt()
        check(outside, "grip_from_lower_tip")["measured"] = 0.30332
        self.refused(outside, "grip_from_lower_tip: 0.30332 is outside")

    def test_a_tilt_below_its_minimum_with_pass_true(self):
        after = rebuilt()
        check(after, "normal_tilt_mean")["measured"] = 0.0399
        self.refused(after, "normal_tilt_mean: 0.0399 is below 0.04")

    def test_a_false_pass_bit_on_a_good_measurement(self):
        after = rebuilt()
        check(after, "brace_height")["pass"] = False
        self.refused(after, "brace_height: its pass bit is False")

    def test_negative_overlap_or_parity(self):
        for name in ("SM_Weapon_18_uv0_overlap", "SM_Weapon_18_Ya_fbx_bounds_parity_m"):
            with self.subTest(check=name):
                after = rebuilt()
                check(after, name)["measured"] = -1e-5
                self.refused(after, f"{name}: the measurement -1e-05 is negative")

    def test_a_coverage_that_is_not_a_share(self):
        for bad in (1.5, -0.1, float("nan")):
            with self.subTest(coverage=bad):
                after = rebuilt()
                check(after, "SM_Weapon_18_Ya_uv0_overlap")["coverage"] = bad
                self.refused(after, "is not a share")

    def test_lod_triangles_unlike_the_build_record(self):
        after = rebuilt()
        check(after, "SM_Weapon_18_lod_triangles")["measured"] = [68000, 28860, 10994]
        self.refused(after, "but the build record says [68716, 28860, 10994]")

    def test_lod_triangles_over_budget_or_not_decreasing(self):
        for lods in ([90000, 28860, 10994], [68716, 68716, 10994]):
            with self.subTest(lods=lods):
                rec = copy.deepcopy(REC)
                rec["assets"]["SM_Weapon_18"]["lods"] = [{"triangles": t} for t in lods]
                after = rebuilt()
                check(after, "SM_Weapon_18_lod_triangles")["measured"] = lods
                self.refused(after, "is not decreasing within the LOD0 budget 80000", rec=rec)

    def test_lod_triangles_that_are_not_three_counts(self):
        for lods in ([68716, 28860], [68716.0, 28860, 10994], [True, 1, 0]):
            with self.subTest(lods=lods):
                after = rebuilt()
                check(after, "SM_Weapon_18_lod_triangles")["measured"] = lods
                self.refused(after, "is not three positive triangle counts")

    def test_a_texel_density_unlike_the_build_record(self):
        after = rebuilt()
        check(after, "texel_density_p05_px_per_m")["measured"] = 3138.1
        self.refused(after, "but the build record's p05 rounds to 2943.8")

    def test_a_w18_error(self):
        after = rebuilt()
        after["weapons"]["18"]["errors"] = ["T_Weapon_18_ORM.png: missing"]
        self.refused(after, "row 18 has errors")

    def test_an_unwritten_w18_row(self):
        after = before_doc()
        after["summary"]["seconds"] = 3.0
        self.refused(after, "the run did not write it")

    # The rest of the report ------------------------------------------------------------------------------------
    def test_a_new_failure(self):
        after = rebuilt()
        after["weapons"]["7"]["pass"] = False
        self.refused(after, "not the expected [3, 11, 13, 16]")

    def test_a_blockout_row_that_stops_failing(self):
        after = rebuilt()
        after["weapons"]["3"] = other_row(4) | {"id": 3, "key": "W03_X"}
        self.refused(after, "not the expected [3, 11, 13, 16]")

    def test_an_unexpected_pre_run_failure_set(self):
        before = before_doc()
        before["weapons"]["5"]["pass"] = False
        before["summary"]["passed"] = 16
        self.refused(rebuilt(before), "failing rows before the run", before=before)

    def test_another_row_changed_by_one_value(self):
        after = rebuilt()
        after["weapons"]["4"]["checks"][1]["measured"] = 0.1000001
        self.refused(after, "rows ['4']")

    def test_a_reformatted_report(self):
        self.refused(json.dumps(rebuilt(), indent=2).encode("utf-8") + b"\n", "its bytes")

    def test_a_before_report_the_validator_did_not_write(self):
        before = json.dumps(before_doc(), indent=2).encode("utf-8")
        self.refused(rebuilt(), "does not reproduce its own bytes", before=before)

    def test_reordered_rows(self):
        after = rebuilt()
        after["weapons"] = dict(reversed(list(after["weapons"].items())))
        self.refused(after, "order changed")

    def test_summary_counts_that_are_not_the_rows(self):
        for name in ("before", "after"):
            with self.subTest(report=name):
                before = before_doc()
                if name == "before":
                    before["summary"]["passed"] = 18
                after = rebuilt(before)
                if name == "after":
                    after["summary"]["passed"] = 18
                self.refused(after, f"the {name} summary counts 18 passed; 17 rows pass", before=before)

    def test_a_changed_summary_count(self):
        after = rebuilt()
        after["summary"]["weapons"] = 22
        self.refused(after, "summary's weapons changed")

    def test_a_malformed_summary_time(self):
        after = rebuilt()
        after["summary"]["seconds"] = float("inf")
        self.refused(after, "time or Blender version is malformed")

    # The log and the exit --------------------------------------------------------------------------------------
    def test_another_weapon_in_the_log(self):
        self.refused(rebuilt(), "not W18_Yumi alone", log="[validate] W04_X: PASS\n" + LOG)

    def test_a_traceback_in_the_log(self):
        self.refused(rebuilt(), "traceback", log=LOG + "Traceback (most recent call last):\n")

    def test_a_log_without_the_summary_line(self):
        self.refused(rebuilt(), "summary's count", log="[validate] W18_Yumi: PASS\n")

    def test_an_exit_the_summary_does_not_imply(self):
        for code in (0, 134, 137):
            with self.subTest(code=code):
                self.refused(rebuilt(), f"exited {code}", exit_=code)

    def test_an_unreadable_report(self):
        self.refused(b"{", "unreadable")


class Command(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.t = Path(self._tmp.name)
        (self.t / "before.json").write_bytes(G.serialise(before_doc()))
        (self.t / "record.json").write_text(json.dumps(REC))
        (self.t / "validate.log").write_text(LOG)

    def tearDown(self):
        self._tmp.cleanup()

    def run_command(self, after):
        (self.t / "after.json").write_bytes(G.serialise(after))
        args = [sys.executable, str(HERE / "check_scoped_validation.py"), "--weapon", "18",
                "--expected-failures", "3,11,13,16", "--before", str(self.t / "before.json"),
                "--after", str(self.t / "after.json"), "--build-record", str(self.t / "record.json"),
                "--log", str(self.t / "validate.log"), "--validator-exit", "1", "--out", str(self.t / "result.json")]
        return subprocess.run(args, capture_output=True, text=True, timeout=60)

    def test_the_command_writes_its_result_and_keeps_the_exit(self):
        proc = self.run_command(rebuilt())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("SCOPED_VALIDATION_OK", proc.stdout)
        result = json.loads((self.t / "result.json").read_text())
        self.assertEqual(result["validator_exit"], 1)
        self.assertEqual(result["build_record"]["sha256"],
                         __import__("hashlib").sha256((self.t / "record.json").read_bytes()).hexdigest())
        again = self.run_command(rebuilt())
        self.assertEqual(again.returncode, 1)                              # --out is never overwritten
        self.assertIn("never overwritten", again.stderr)

    def test_a_refusal_exits_1_and_writes_nothing(self):
        proc = self.run_command(before_doc())
        self.assertEqual(proc.returncode, 1)
        self.assertIn("SCOPED_VALIDATION_FAILED", proc.stderr)
        self.assertFalse((self.t / "result.json").exists())


if __name__ == "__main__":
    unittest.main()
