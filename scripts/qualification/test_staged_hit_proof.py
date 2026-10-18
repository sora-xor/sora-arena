#!/usr/bin/env python3
"""Filesystem/input guard tests, never synthetic cryptographic proof success.

Run with --iroha-root pointing to the checkout that supplies the native guards.
Small fake rlibs and harness files below are guard inputs, never executed code.
"""

import argparse
from contextlib import redirect_stderr, redirect_stdout
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("staged_hit_runner", Path(__file__).with_name("staged_hit_proof.py"))
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
GUARD = None
NATIVE_ROOT = None


def fixture():
    return {"schema": "sora-arena-staged-hit-reference", "scope": "test guard fixture only", "rules": "sora-arena-first-release-7", "simulation_sha256": "1" * 64, "tick_sha256": "4" * 64, "math_sha256": "2" * 64, "abilities_sha256": "3" * 64, "cases": [{"name": "guard_case", "attacker": 0, "controls": [0, 0, 0, 45000, 0, 0], "players": [[0, 0, 0, 0, 1, 0], [2000, 0, 0, 1, 1, 0]], "walls": [], "entities": [], "expected": [3, 1, 38447], "ray": [[0, 0, 1400], [45000, 0, 1400]]}]}


class RunnerGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name).resolve()
        self.root = self.directory / "native"
        self.root.mkdir()
        self.target = self.root / "target"
        self.deps = self.target / "debug/deps"
        self.deps.mkdir(parents=True)
        self.fixture = self.directory / "fixture.json"
        self.fixture.write_text(json.dumps(fixture()))
        self.manifest = self.directory / "dependencies.json"
        pins = {}
        for name in GUARD.REQUIRED_LIBRARIES:
            path = self.deps / f"lib{name}-a123.rlib"
            path.write_bytes(("guard input, not an rlib: " + name).encode())
            pins[name] = {"path": str(path), "sha256": GUARD.file_hash(path)}
        self.manifest.write_text(json.dumps({"schema": "iroha.arena.research_dependencies.v1", "dependencies": pins}))
        (self.root / "scripts").mkdir()
        (self.root / "scripts/check_arena_geometry_stark.py").write_text("# synthetic guard input, never imported\n")
        self.args = argparse.Namespace(iroha_root=self.root, target_dir=self.target, dependency_manifest=self.manifest, fixture=self.fixture, case="guard_case", output_dir=self.directory / "output", threads=2, prove=False)
        self.seal = {"source": {"sourceTreeSha256": "original"}, "dependencies": pins, "toolchain": {"sysroot": str(self.directory / "toolchain")}}

    def tearDown(self):
        self.temp.cleanup()

    def read(self, value):
        self.fixture.write_text(json.dumps(value))
        return RUNNER.read_fixture(self.fixture, "guard_case")

    def test_current_complete_native_fixture_is_accepted(self):
        data, case = RUNNER.read_fixture(NATIVE_ROOT / "crates/iroha_core/tests/fixtures/arena_staged_hit_reference.json", "bounded_random_9")
        self.assertEqual(len(case["players"]), 12)
        self.assertEqual(len(case["walls"]), 64)
        self.assertEqual(len(case["entities"]), 48)
        self.assertGreater(len(data["cases"]), 1)

    def test_executable_strings_nonintegers_and_boolean_coercion_are_rejected(self):
        for bad in ('0}; panic!("injected"); //', "1", True, 1.0, None, {}, []):
            data = fixture()
            data["cases"][0]["controls"][0] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.read(data)
        data = fixture()
        data["cases"][0]["players"][0][0] = '0]; std::process::Command::new("bad");'
        with self.assertRaises(ValueError):
            RUNNER.write_harness(self.root, self.directory, data["cases"][0])
        self.assertFalse((self.directory / "harness.rs").exists())

    def test_counts_coordinate_domains_and_retained_order_are_checked(self):
        mutations = [
            lambda c: c["controls"].pop(),
            lambda c: c["controls"].__setitem__(3, 70001),
            lambda c: c["controls"].__setitem__(4, -1),
            lambda c: c["controls"].__setitem__(5, 16385),
            lambda c: c["players"][0].__setitem__(0, (1 << 20) + 1),
            lambda c: c["players"][0].__setitem__(4, 0),
            lambda c: c["players"].extend([[0, 0, 0, 0, 1, 0]] * 11),
            lambda c: c.__setitem__("walls", [[1, 0, 0, 0, 1, 1]]),
            lambda c: c.__setitem__("walls", [[0] * 6] * 65),
            lambda c: c.__setitem__("entities", [[1, 2, 0, 0, 0, 0, 0, 1, 1]] * 2),
            lambda c: c.__setitem__("entities", [[1, 2, 2, 0, 0, 0, 0, 1, 1]]),
            lambda c: c.__setitem__("expected", [0, 1, 0]),
            lambda c: c.__setitem__("expected", [0, 0, 1]),
            lambda c: c.__setitem__("expected", [2, 90, 100]),
            lambda c: c.__setitem__("expected", [3, 1, (1 << 20) + 1]),
            lambda c: c.__setitem__("attacker", 2),
        ]
        for index, mutate in enumerate(mutations):
            data = fixture()
            mutate(data["cases"][0])
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.read(data)

    def test_duplicate_unknown_and_nonfinite_fixture_inputs_fail(self):
        for text in ('{"schema":1,"schema":2}', '{"value":NaN}'):
            self.fixture.write_text(text)
            with self.assertRaises(ValueError):
                RUNNER.read_fixture(self.fixture, "guard_case")
        data = fixture()
        data["cases"].append(copy.deepcopy(data["cases"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate case"):
            self.read(data)
        self.read(fixture())
        with self.assertRaisesRegex(ValueError, "not found"):
            RUNNER.read_fixture(self.fixture, "absent")
        data = fixture()
        data["cases"][0]["hidden"] = 1
        with self.assertRaises(ValueError):
            self.read(data)

    def test_exact_pins_win_over_other_cache_versions_and_stale_pins_fail(self):
        for name in GUARD.REQUIRED_LIBRARIES:
            (self.deps / f"lib{name}-b456.rlib").write_bytes(b"another guard input")
        selected = GUARD.select_dependencies(self.deps, self.manifest)
        self.assertTrue(all(Path(entry["path"]).name.endswith("-a123.rlib") for entry in selected.values()))
        Path(selected["rand"]["path"]).write_bytes(b"stale")
        with self.assertRaisesRegex(ValueError, "hash differs"):
            GUARD.select_dependencies(self.deps, self.manifest)

    def test_all_input_and_native_seal_components_are_enforced(self):
        paths = {"fixture": self.fixture, "manifest": self.manifest}
        before = RUNNER.input_seal(GUARD, paths)
        self.fixture.write_text(self.fixture.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "input seal changed"):
            RUNNER.require_same_inputs(before, RUNNER.input_seal(GUARD, paths))
        for key in ("source", "dependencies", "toolchain"):
            changed = copy.deepcopy(self.seal)
            changed[key] = {"changed": True}
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "seal changed"):
                GUARD.require_same_seal(self.seal, changed)

    def test_output_is_exclusive_and_rejects_dangling_symlinks_and_native_tree(self):
        output = RUNNER.fresh_output(self.args.output_dir, self.root)
        retained = output / "previous.txt"
        retained.write_text("retain")
        with self.assertRaises(FileExistsError):
            RUNNER.fresh_output(output, self.root)
        dangling = self.directory / "dangling"
        dangling.symlink_to(self.directory / "missing")
        with self.assertRaises(FileExistsError):
            RUNNER.fresh_output(dangling, self.root)
        with self.assertRaises(ValueError):
            RUNNER.fresh_output(self.root / "new-evidence", self.root)
        self.assertEqual(retained.read_text(), "retain")
        self.assertFalse((self.directory / "missing").exists())

    def fake_harness(self, root, output, case):
        path = output / "harness.rs"
        path.write_text("// guard-test input; never compiled\n")
        (output / "native_field.rs").write_text("// guard-test input; never compiled\n")
        return path, []

    def failed_run(self, compile_effect):
        with patch.object(RUNNER, "load_guard", return_value=GUARD), patch.object(GUARD, "capture_seal", side_effect=lambda *args: copy.deepcopy(self.seal)), patch.object(RUNNER, "write_harness", side_effect=self.fake_harness), patch.object(RUNNER.subprocess, "run", side_effect=compile_effect), patch.object(RUNNER.subprocess, "Popen") as process, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(RUNNER.run(self.args), 1)
            process.assert_not_called()
        status = json.loads((self.args.output_dir / "run-status.json").read_text())
        self.assertEqual(status["status"], "invalid")
        self.assertFalse(status["proof_verified"])
        self.assertTrue((self.args.output_dir / "seal-after.json").exists())
        return status

    def test_compile_failure_writes_invalid_status_and_final_seal(self):
        status = self.failed_run(subprocess.CalledProcessError(1, ["rustc", "guard-test"]))
        self.assertIn("non-zero exit status", status["error"])

    def test_native_seals_and_compiler_use_iroha_toolchain_from_foreign_cwd(self):
        original = Path.cwd()
        self.assertNotEqual(original, self.root)
        captured = []
        def capture(*args):
            captured.append(Path.cwd())
            self.assertEqual(Path.cwd(), self.root)
            return copy.deepcopy(self.seal)
        def compile_command(command, **kwargs):
            self.assertEqual(command[0], str(Path(self.seal["toolchain"]["sysroot"]) / "bin/rustc"))
            self.assertEqual(kwargs["cwd"], self.root)
            self.assertEqual(Path.cwd(), self.root)
            raise subprocess.CalledProcessError(1, command)
        with patch.object(RUNNER, "load_guard", return_value=GUARD), patch.object(GUARD, "capture_seal", side_effect=capture), patch.object(RUNNER, "write_harness", side_effect=self.fake_harness), patch.object(RUNNER.subprocess, "run", side_effect=compile_command), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(RUNNER.run(self.args), 1)
        self.assertEqual(captured, [self.root, self.root])
        self.assertEqual(Path.cwd(), original)
        status = json.loads((self.args.output_dir / "run-status.json").read_text())
        self.assertFalse(status["proof_verified"])

    def test_source_drift_stops_before_running_any_binary(self):
        def drift(*args, **kwargs):
            self.seal["source"]["sourceTreeSha256"] = "changed"
        status = self.failed_run(drift)
        self.assertIn("seal changed", status["error"])

    def test_fixture_manifest_and_generated_source_drift_are_invalid(self):
        for name in ("fixture", "manifest", "harness"):
            self.args.output_dir = self.directory / ("changed-" + name)
            def drift(*args, **kwargs):
                path = {"fixture": self.fixture, "manifest": self.manifest, "harness": self.args.output_dir / "harness.rs"}[name]
                path.write_text(path.read_text() + "\n")
            with self.subTest(name=name):
                status = self.failed_run(drift)
                self.assertIn("input seal changed", status["error"])

    def test_missing_manifest_cli_is_not_allowed(self):
        argv = ["runner", "--iroha-root", str(self.root), "--target-dir", str(self.target), "--fixture", str(self.fixture), "--case", "guard_case", "--output-dir", str(self.args.output_dir)]
        with patch.object(sys, "argv", argv), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            RUNNER.main()
        self.assertEqual(raised.exception.code, 2)
        self.assertFalse(self.args.output_dir.exists())

    def test_layout_never_claims_proof_and_partial_proof_evidence_is_rejected(self):
        output = RUNNER.fresh_output(self.args.output_dir, self.root)
        result = output / "result"
        result.mkdir()
        (result / "layout.txt").write_text("guard-test layout metadata")
        (result / "public-statement.txt").write_text("guard-test statement metadata")
        RUNNER.check_artifacts(output, False, fixture()["cases"][0], GUARD)
        status = RUNNER.write_status(output, False, None, GUARD)
        self.assertEqual(status["status"], "layout_complete")
        self.assertFalse(status["proof_verified"])
        (result / "measurements.txt").write_text("incomplete guard-test data, not a proof")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            RUNNER.check_artifacts(output, True, fixture()["cases"][0], GUARD)
        with self.assertRaisesRegex(ValueError, "unexpectedly"):
            RUNNER.check_artifacts(output, False, fixture()["cases"][0], GUARD)

    def test_unknown_platform_does_not_claim_rss_and_path_literals_are_escaped(self):
        with patch.object(RUNNER.platform, "system", return_value="Other"):
            command, metadata = RUNNER.timed_command(["binary", "args"])
        self.assertEqual(command, ["binary", "args"])
        self.assertEqual(metadata["rss"], "not collected")
        self.assertEqual(RUNNER.rust_string('猫/quote"/back\\/\n'), '"猫/quote\\"/back\\\\/\\n"')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--iroha-root", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    NATIVE_ROOT = args.iroha_root.resolve(strict=True)
    GUARD = RUNNER.load_guard(NATIVE_ROOT)
    unittest.main(argv=[sys.argv[0], *remaining])
