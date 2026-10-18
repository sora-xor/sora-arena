#!/usr/bin/env python3
"""Run the unregistered native ray-stop component with explicit inputs and seals.

Layout is the default; --prove opts into actual proving and verification. Neither
mode authenticates a World, attack, kill, admission, or settlement. Dependencies
must already be built and explicitly pinned; this runner never chooses versions.
Darwin uses /usr/bin/time -l and Linux uses -v when available. Other platforms
retain elapsed wall time only and explicitly report that RSS was not collected.
"""

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time


COORDINATE_LIMIT = 1 << 20
PROOF_CAP = 4 * 1024 * 1024
RELATIONS = (
    "integer_air", "checked_integer_air", "arena_aim_air", "arena_geometry_air",
    "arena_staged_hit_air", "arena_staged_hit_stark_research",
)
FIELD_CONSTANTS = (
    "GOLDILOCKS_MODULUS_V1", "GOLDILOCKS_EPSILON_V1", "GOLDILOCKS_GENERATOR_V1",
    "GOLDILOCKS_FP4_DEGREE_V1", "GOLDILOCKS_FP4_WIRE_BYTES_V1",
    "GOLDILOCKS_FP4_NONRESIDUE_V1",
)


def exact_keys(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f"{label} has an invalid object shape")


def integer(value, low, high, label):
    # bool is an int subclass; accepting it would silently rewrite the fixture.
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} must be an integer in {low}..{high}")
    return value


def vector(value, size, label):
    if type(value) is not list or len(value) != size:
        raise ValueError(f"{label} must contain exactly {size} values")
    return value


def coordinates(value, label, limit=COORDINATE_LIMIT):
    for index, item in enumerate(vector(value, 3, label)):
        integer(item, -limit, limit, f"{label}[{index}]")


def validate_case(case):
    exact_keys(case, ("name", "attacker", "controls", "players", "walls", "entities", "expected", "ray"), "case")
    if type(case["name"]) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", case["name"]):
        raise ValueError("case name must be a bounded identifier")
    controls = vector(case["controls"], 6, "controls")
    for index in range(3):
        integer(controls[index], 0, 1, f"controls[{index}]")
    integer(controls[3], 1, 70000, "range")
    integer(controls[4], 0, 65535, "yaw")
    integer(controls[5], -16384, 16384, "pitch")
    for name, low, high in (("players", 1, 12), ("walls", 0, 64), ("entities", 0, 48)):
        if type(case[name]) is not list or not low <= len(case[name]) <= high:
            raise ValueError(f"{name} count must be {low}..{high}")
    players = case["players"]
    attacker = integer(case["attacker"], 0, len(players) - 1, "attacker")
    for player in players:
        vector(player, 6, "player")
        coordinates(player[:3], "player position")
        integer(player[3], 0, 1, "player team")
        integer(player[4], 0, 1, "player alive")
        integer(player[5], 0, 65535, "player protection")
    if players[attacker][4] != 1:
        raise ValueError("attacker must be alive")
    for wall in case["walls"]:
        vector(wall, 6, "wall")
        coordinates(wall[:3], "wall minimum")
        coordinates(wall[3:], "wall maximum")
        if any(wall[i] > wall[i + 3] for i in range(3)):
            raise ValueError("wall bounds must be ordered")
    prior_id = 0
    for entity in case["entities"]:
        vector(entity, 9, "entity")
        prior_id = integer(entity[0], prior_id + 1, (1 << 32) - 1, "entity ID in retained order")
        integer(entity[1], 1, 4, "entity kind")
        integer(entity[2], 0, len(players) - 1, "entity owner")
        integer(entity[3], 0, 1, "entity team")
        coordinates(entity[4:7], "entity position")
        integer(entity[7], 0, COORDINATE_LIMIT, "entity half width")
        integer(entity[8], 0, COORDINATE_LIMIT, "entity half depth")
    expected = vector(case["expected"], 3, "expected")
    integer(expected[0], 0, 3, "expected kind")
    integer(expected[1], 0, (1 << 32) - 1, "expected identity")
    integer(expected[2], 0, 1 << 20, "expected fraction")
    if expected[0] < 2 and expected[1] != 0:
        raise ValueError("none/wall identity must be zero")
    if expected[0] == 0 and expected[2] != 0:
        raise ValueError("no-stop fraction must be zero")
    if expected[0] == 2 and expected[1] not in {e[0] for e in case["entities"]}:
        raise ValueError("expected entity must be present")
    if expected[0] == 3 and expected[1] >= len(players):
        raise ValueError("expected player must be present")
    # The independent reference ray is retained, not substituted for native aim.
    for point in vector(case["ray"], 2, "reference ray"):
        coordinates(point, "reference ray point", 2 * COORDINATE_LIMIT)
    return case


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def reject_nonfinite(value):
    raise ValueError("nonfinite JSON value: " + value)


def read_fixture(path, case_name):
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("fixture exceeds the 16-MiB input bound")
    data = json.loads(path.read_text(), object_pairs_hook=unique_object,
                      parse_constant=reject_nonfinite)
    exact_keys(data, ("schema", "scope", "rules", "simulation_sha256", "tick_sha256", "math_sha256", "abilities_sha256", "cases"), "fixture")
    if data["schema"] != "sora-arena-staged-hit-reference":
        raise ValueError("unsupported fixture schema")
    for key in ("simulation_sha256", "tick_sha256", "math_sha256", "abilities_sha256"):
        if type(data[key]) is not str or not re.fullmatch(r"[0-9a-f]{64}", data[key]):
            raise ValueError("invalid fixture source hash: " + key)
    for key in ("rules", "scope"):
        if type(data[key]) is not str or not 1 <= len(data[key]) <= 512:
            raise ValueError("invalid fixture metadata: " + key)
    if type(data["cases"]) is not list or not 1 <= len(data["cases"]) <= 4096:
        raise ValueError("fixture must have 1..4096 cases")
    selected = None
    names = set()
    for case in data["cases"]:
        validate_case(case)
        if case["name"] in names:
            raise ValueError("duplicate case name: " + case["name"])
        names.add(case["name"])
        if case["name"] == case_name:
            selected = case
    if selected is None:
        raise ValueError("fixture case was not found: " + case_name)
    return data, selected


def fresh_output(requested, root):
    # Do not resolve the leaf first: a dangling symlink is an existing output.
    requested = requested.absolute()
    if requested.exists() or requested.is_symlink():
        raise FileExistsError("output already exists: " + str(requested))
    if requested.resolve().is_relative_to(root):
        raise ValueError("output must be outside the frozen Iroha checkout")
    requested.parent.mkdir(parents=True, exist_ok=True)
    requested.mkdir(exist_ok=False)
    return requested.resolve()


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def load_guard(root):
    path = root / "scripts/check_arena_geometry_stark.py"
    spec = importlib.util.spec_from_file_location("arena_native_stark_guard", path)
    guard = importlib.util.module_from_spec(spec)
    prior = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(guard)
    finally:
        sys.dont_write_bytecode = prior
    return guard


def input_seal(guard, paths):
    return {name: {"path": str(path), "sha256": guard.file_hash(path)} for name, path in paths.items()}


def require_same_inputs(before, after):
    if not before or before != after:
        raise ValueError("driver, fixture, manifest or guard input seal changed")


def native_field(source):
    start = "/// Canonical Goldilocks field element."
    end = "/// Failure in protocol-neutral transparent-proof machinery."
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError("native field extraction boundaries changed")
    constants = []
    for name in FIELD_CONSTANTS:
        matches = [line for line in source.splitlines() if line.startswith(("const " + name + ":", "pub(crate) const " + name + ":"))]
        if len(matches) != 1 or not matches[0].endswith(";"):
            raise ValueError("native field constant changed: " + name)
        constants.extend(matches)
    return "use zeroize::Zeroize as _;\n" + "\n".join(constants) + "\n" + source[source.index(start):source.index(end)]


def rust_string(value):
    escapes = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}
    return '"' + "".join(escapes.get(c, f"\\u{{{ord(c):x}}}" if ord(c) < 32 else c) for c in value) + '"'


def write_harness(root, output, case):
    validate_case(case)
    source_root = root / "crates/iroha_core/src/execution_proofs"
    field_path = root / "crates/iroha_core/src/privacy_engines/transparent_stark.rs"
    field = native_field(field_path.read_text())
    (output / "native_field.rs").write_text(field)
    paths = [source_root / (name + ".rs") for name in RELATIONS]
    stark = source_root / "stark/mod.rs"
    lines = ['#![allow(dead_code)]', 'mod privacy_engines { pub mod transparent_stark { include!("native_field.rs"); } }', 'mod execution_proofs {']
    lines += ["#[path = " + rust_string(str(path)) + "] mod " + path.stem + ";" for path in paths]
    lines += ["#[path = " + rust_string(str(stark)) + "] mod stark;", "pub fn run(output: &std::path::Path, prove: bool)->Result<(),Box<dyn std::error::Error>> {", "use arena_staged_hit_stark_research::*;"]
    c = case["controls"]
    boolean = lambda value: ("false", "true")[value]
    lines.append(f"let snapshot=ArenaHitSnapshotV1 {{ team_mode:{boolean(c[0])}, melee:{boolean(c[1])}, allies:{boolean(c[2])}, range_mm:{c[3]}, yaw:{c[4]}, pitch:{c[5]}, players:vec![")
    for p in case["players"]:
        lines.append(f"ArenaHitPlayerV1 {{ position:{p[:3]}, team:{p[3]}, alive:{boolean(p[4])}, protection:{p[5]} }},")
    lines.append("], walls:vec![")
    lines += [f"({w[:3]},{w[3:]})," for w in case["walls"]]
    lines.append("], entities:vec![")
    for e in case["entities"]:
        lines.append(f"ArenaHitEntityV1 {{ id:{e[0]}, kind:{e[1]}, owner:{e[2]}, team:{e[3]}, position:{e[4:7]}, half_x:{e[7]}, half_y:{e[8]} }},")
    lines.append("] };")
    e = case["expected"]
    lines.append(f"run_staged_hit_research_v1(&snapshot, {case['attacker']}, ArenaHitOutputV1 {{ kind:{e[0]}, identity:{e[1]}, fraction_q20:{e[2]} }}, output, prove) }} }}")
    lines.append('fn main()->Result<(),Box<dyn std::error::Error>> { let path=std::env::args().nth(1).ok_or("missing output directory")?; let prove=std::env::args().nth(2).as_deref()==Some("prove"); execution_proofs::run(std::path::Path::new(&path), prove) }')
    harness = output / "harness.rs"
    harness.write_text("\n".join(lines) + "\n")
    return harness, paths + [field_path] + sorted(stark.parent.glob("*.rs"))


def timed_command(command):
    timer = Path("/usr/bin/time")
    flag = {"Darwin": "-l", "Linux": "-v"}.get(platform.system())
    if flag and timer.is_file():
        return [str(timer), flag] + command, {"tool": str(timer), "flag": flag, "rss": "raw platform-specific report in run.log"}
    return command, {"tool": None, "rss": "not collected"}


def check_artifacts(output, prove, case, guard):
    result = output / "result"
    for name in ("layout.txt", "public-statement.txt"):
        if not (result / name).is_file() or not (result / name).stat().st_size:
            raise ValueError("missing native evidence: " + name)
    proof_path = result / "staged-hit.stark"
    measurements = result / "measurements.txt"
    if not prove:
        if proof_path.exists() or measurements.exists():
            raise ValueError("layout-only run unexpectedly produced proof evidence")
        return
    if not proof_path.is_file() or not 0 < proof_path.stat().st_size <= PROOF_CAP or not measurements.is_file():
        raise ValueError("incomplete or oversized native proof evidence")
    entries = {}
    for line in measurements.read_text().splitlines():
        key, separator, value = line.partition("=")
        if not separator or key in entries:
            raise ValueError("invalid measurement record")
        entries[key] = value
    exact_keys(entries, ("research_only", "qualified", "relation", "proof_bytes", "proof_sha256", "prove_ms", "verify_ms", "negative_verifications"), "measurements")
    negatives = 8 + bool(case["walls"]) + bool(case["entities"])
    required = {"research_only": "true", "qualified": "false", "relation": "generic_public_ordered_ray_stop", "proof_bytes": str(proof_path.stat().st_size), "proof_sha256": guard.file_hash(proof_path), "negative_verifications": str(negatives)}
    if any(entries[key] != value for key, value in required.items()):
        raise ValueError("native proof measurements disagree with retained evidence")
    if any(not re.fullmatch(r"[0-9]+", entries[key]) for key in ("prove_ms", "verify_ms")):
        raise ValueError("invalid native timing measurement")


def write_status(output, prove, error, guard=None, elapsed=None, resources=None):
    status = {"schema": "iroha.arena.staged_hit.run.v1", "kind": "prove_verify" if prove else "layout_only", "status": "invalid" if error else ("proof_verified" if prove else "layout_complete"), "proof_verified": prove and error is None, "research_only": True, "registered": False, "qualified": False, "elapsed_seconds": elapsed, "resource_measurement": resources or {"rss": "not collected"}}
    if error:
        status["error"] = error
    status["artifacts_sha256"] = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "run-status.json":
            try:
                status["artifacts_sha256"][str(path.relative_to(output))] = guard.file_hash(path) if guard else hashlib.sha256(path.read_bytes()).hexdigest()
            except (OSError, ValueError) as failure:
                status.update(status="invalid", proof_verified=False)
                status["error"] = status.get("error", "") + "; artifact hashing failed: " + str(failure)
    with (output / "run-status.json").open("x") as stream:
        json.dump(status, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return status


def run(args):
    root = args.iroha_root.resolve(strict=True)
    output = fresh_output(args.output_dir, root)
    print("Exclusive staged-hit research run:", output, flush=True)
    guard = dependencies = before = input_before = generated_before = binary_before = None
    generated_paths = {}
    binary = None
    resources = None
    started = time.monotonic()
    error = None
    try:
        guard = load_guard(root)
        target = args.target_dir.resolve(strict=True)
        deps = (target / "debug/deps").resolve(strict=True)
        paths = {"driver": Path(__file__).resolve(), "fixture": args.fixture.resolve(strict=True), "manifest": args.dependency_manifest.resolve(strict=True), "guard": root / "scripts/check_arena_geometry_stark.py"}
        input_before = input_seal(guard, paths)
        guard.write_json(output / "inputs-before.json", input_before)
        # The guard enforces every exact filename and SHA256; no fallback scan.
        dependencies = guard.select_dependencies(deps, paths["manifest"])
        fixture, case = read_fixture(paths["fixture"], args.case)
        guard.write_json(output / "reference-fixture.json", fixture)
        guard.write_json(output / "reference-case.json", case)
        guard.write_json(output / "dependencies.json", {"schema": "iroha.arena.research_dependencies.v1", "dependencies": dependencies})
        with working_directory(root):
            before = guard.capture_seal(root, dependencies)
            guard.write_json(output / "seal-before.json", before)
            harness, sources = write_harness(root, output, case)
            require_same_inputs(input_before, input_seal(guard, paths))
            compiler = Path(before["toolchain"]["sysroot"]) / "bin/rustc"
            binary = output / "native-staged-hit"
            externs = [item for name, entry in dependencies.items() for item in ("--extern", name + "=" + entry["path"])]
            command = [str(compiler), "--edition=2024", "-C", "opt-level=3", "-C", "debuginfo=0", str(harness), "-L", "dependency=" + str(deps), "-o", str(binary)] + externs
            guard.write_json(output / "source-provenance.json", {"research_only": True, "registered": False, "scope": "conditional public ray-stop relation only", "case": case["name"], "sources": {str(p.relative_to(root)): guard.file_hash(p) for p in sources}, "inputs": input_before, "harness_sha256": guard.file_hash(harness), "field_extraction_sha256": guard.file_hash(output / "native_field.rs"), "dependencies": dependencies, "threads": args.threads, "compile_command": command})
            generated_paths = {name: output / name for name in ("harness.rs", "native_field.rs", "reference-fixture.json", "reference-case.json", "source-provenance.json")}
            generated_before = input_seal(guard, generated_paths)
            guard.write_json(output / "generated-before.json", generated_before)
            with (output / "build.log").open("x") as log:
                subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
            compiled = guard.capture_seal(root, dependencies)
            guard.write_json(output / "seal-after-compile.json", compiled)
            guard.require_same_seal(before, compiled)
            require_same_inputs(input_before, input_seal(guard, paths))
            require_same_inputs(generated_before, input_seal(guard, generated_paths))
            binary_before = input_seal(guard, {"binary": binary})
            guard.write_json(output / "binary-before.json", binary_before)
            command, resources = timed_command([str(binary), str(output / "result"), "prove" if args.prove else "layout"])
            with (output / "run.log").open("x") as log:
                process = subprocess.Popen(command, cwd=root, env=dict(os.environ, RAYON_NUM_THREADS=str(args.threads)), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in process.stdout:
                    print(line, end="", flush=True)
                    log.write(line)
                    log.flush()
                if process.wait():
                    raise RuntimeError("native component failed with exit code " + str(process.returncode))
            check_artifacts(output, args.prove, case, guard)
    except Exception as failure:
        error = str(failure)
    finally:
        for label, initial, retained in (
            ("generated", generated_before, generated_paths),
            ("binary", binary_before, {"binary": binary} if binary_before else {}),
        ):
            if guard is not None and initial is not None:
                try:
                    final = input_seal(guard, retained)
                    guard.write_json(output / (label + "-after.json"), final)
                    require_same_inputs(initial, final)
                except Exception as failure:
                    error = (error + "; " if error else "") + "final " + label + " seal: " + str(failure)
        if guard is not None and input_before is not None:
            try:
                after_inputs = input_seal(guard, paths)
                guard.write_json(output / "inputs-after.json", after_inputs)
                require_same_inputs(input_before, after_inputs)
            except Exception as failure:
                error = (error + "; " if error else "") + "final input seal: " + str(failure)
        if guard is not None and dependencies is not None:
            try:
                with working_directory(root):
                    after = guard.capture_seal(root, dependencies)
                guard.write_json(output / "seal-after.json", after)
                guard.require_same_seal(before, after)
            except Exception as failure:
                error = (error + "; " if error else "") + "final native seal: " + str(failure)
    status = write_status(output, args.prove, error, guard, time.monotonic() - started, resources)
    print("Research status:", status["status"], flush=True)
    if "error" in status:
        print(status["error"], file=sys.stderr)
    return 1 if status["status"] == "invalid" else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("iroha-root", "target-dir", "dependency-manifest", "fixture", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--prove", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.threads <= 4:
        parser.error("--threads must be 1..4")
    try:
        return run(args)
    except (OSError, ValueError) as failure:
        parser.error(str(failure))


if __name__ == "__main__":
    sys.exit(main())
