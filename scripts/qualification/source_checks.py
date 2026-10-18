#!/usr/bin/env python3
"""Run the checked-in source gates without Unreal, a native bridge, or a network."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
SELF = "scripts/qualification/source_checks.py"
GROUPS = ("rust", "gameplay", "tooling", "assets", "audio")
OUTSIDE_SCOPE = (
    "Unreal editor/game builds, imports, automation, cooking and packaged play",
    "Native kernel C ABI execution/parity and native-dependent parity rejection tests; native Connect bridge ABI",
    "Windows builds, signing/distribution, controller and accessibility playtests",
    "Rendered art, shader compilation, audio listening, campaign pacing and performance",
    "Private raw-asset/download-cache verification and complete environment import plans",
    "Ignored long Rust research runs, public-network P2P, live wallet and four-validator trials",
    "Final-source native execution proofs, composition, economic settlement and release qualification",
)
# These six tests require untracked raw downloads. The source suite deliberately
# excludes them even when a developer happens to have that cache. Every other
# test in these files must run; a new skip is a failure, never an implicit pass.
RAW_TESTS = {
    "scripts/unreal/test_cc0_environment_library.py": (
        "SourceTest.test_power_of_two_mode_comes_from_the_source",
        "MeasuredRankTest.test_instances_bind_their_measured_knots",
        "LedgerTest.test_used_by_lists_every_package_built_from_a_record",
        "PlanTest.test_full_plan",
        "PlanTest.test_master_graph_digest_tracks_graph_inputs",
    ),
    "scripts/unreal/test_environment_presets.py": (
        "ScatterTest.test_moss_cushions_are_covered_by_sprigs",
    ),
}
SOURCE_CLASSES = {
    # The other class loads and executes a staged kernel in subprocesses.
    "scripts/unreal/test_parity_guards.py": ("SourceIdentityCoverageTests",),
}


@dataclass(frozen=True)
class Check:
    name: str
    group: str
    command: tuple[str, ...]


def checks(python: str = sys.executable) -> list[Check]:
    """Explicit command inventory: no broad discovery can accidentally launch UE."""
    result = [
        Check("rust-pin", "rust", (python, SELF, "--rust-pin")),
        Check("rust-format", "rust", ("cargo", "fmt", "--all", "--check")),
        Check("rust-clippy", "rust", ("cargo", "clippy", "--workspace", "--all-targets", "--locked", "--", "-D", "warnings")),
        Check("rust-tests", "rust", ("cargo", "test", "--workspace", "--locked", "--no-fail-fast")),
    ]

    def script(group: str, name: str, path: str, *args: str) -> None:
        result.append(Check(name, group, (python, path, *args)))

    def unit(group: str, name: str, path: str) -> None:
        script(group, name, SELF, "--unit-tests", path)

    script("gameplay", "campaign-generated-data", "scripts/unreal/build_campaign_data.py", "--check")
    script("gameplay", "campaign-data", "scripts/unreal/validate_campaign.py")
    script("gameplay", "enemy-data", "scripts/unreal/validate_enemies.py")
    script("gameplay", "localization", "scripts/unreal/native_japanese_localization.py", "--check")
    script("gameplay", "input-bindings", "scripts/unreal/check_input_conflicts.py")
    script("gameplay", "catalog-kernel-parity", "scripts/unreal/check_catalog_kernel_parity.py")
    for name in ("campaign_progression", "combat_rules", "boss_rules", "stealth_rules", "fieldcraft_rules", "historical_arms"):
        script("gameplay", name.replace("_", "-"), f"scripts/unreal/test_{name}.py")
    unit("gameplay", "maai-data", "scripts/unreal/test_maai_data.py")
    unit("gameplay", "equipment-recovery-data", "scripts/unreal/test_recovery_data.py")
    unit("gameplay", "carry-difficulty-data", "scripts/unreal/test_carry_difficulty_data.py")
    unit("gameplay", "carry-work-data", "scripts/unreal/test_carry_work_data.py")
    unit("gameplay", "crank-data", "scripts/unreal/test_crank_data.py")
    unit("gameplay", "lift-data", "scripts/unreal/test_lift_data.py")
    unit("gameplay", "spire-data", "scripts/unreal/test_spire_data.py")
    unit("gameplay", "epilogue-data", "scripts/unreal/test_epilogue_data.py")
    unit("gameplay", "registry-data", "scripts/unreal/test_registry_data.py")
    for name, path in (
        ("connect-cancellation", "scripts/connect/verify-cancellation.py"),
        ("connect-recovery", "scripts/connect/verify-recovery.py"),
        ("quote-preflight", "scripts/connect/test_quote_preflight.py"),
    ):
        script("gameplay", name, path)
    for name, path in (
        ("runner-guards", "scripts/qualification/test_source_checks.py"),
        ("engine-pin-guards", "scripts/toolchain/test_doctor_pin.py"),
        ("rust-pin-guards", "scripts/toolchain/test_doctor_rust.py"),
        ("import-vfx-guards", "scripts/toolchain/test_import_vfx_gate.py"),
        ("capture-report-guards", "scripts/toolchain/test_capture_report.py"),
        ("mac-candidate-guards", "scripts/toolchain/test_mac_candidate.py"),
        ("automation-report-guards", "scripts/toolchain/test_packaged_report.py"),
        ("parity-source-identity", "scripts/unreal/test_parity_guards.py"),
        ("vfx-preview-guards", "scripts/unreal/test_vfx_preview_shots.py"),
        ("environment-library-source", "scripts/unreal/test_cc0_environment_library.py"),
        ("environment-presets-source", "scripts/unreal/test_environment_presets.py"),
    ):
        unit("tooling", name, path)
    script("assets", "lfs-materialized", SELF, "--lfs-materialized")
    script("assets", "source-content", "scripts/unreal/validate_content.py")
    script("assets", "asset-ledger", "scripts/assets/validate_asset_ledger.py", "--json")
    script("assets", "asset-notices", "scripts/assets/generate_asset_notices.py", "--check")
    for name in ("asset_ledger", "fetch_cc0", "fetch_cat_base_v6_sources", "lane_records"):
        unit("assets", name.replace("_", "-") + "-tests", f"scripts/assets/tests/test_{name}.py")
    script("audio", "audio-data", "scripts/audio/validate_audio_data.py")
    unit("audio", "audio-import-spec", "scripts/unreal/test_audio_spec.py")
    unit("audio", "audio-dsp", "scripts/audio/test_build_cc0_audio.py")
    script("audio", "audio-waveforms", "scripts/audio/qa_audio.py", "Content/SourceArt/Audio")
    return result


def flatten(suite: unittest.TestSuite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def select_tests(suite: unittest.TestSuite, excluded: tuple[str, ...]) -> unittest.TestSuite:
    """Reject stale exclusions, and never infer exclusions from missing files."""
    selected = []
    found = set()
    for test in flatten(suite):
        name = ".".join(test.id().split(".")[-2:])
        if name in excluded:
            found.add(name)
        else:
            selected.append(test)
    missing = set(excluded) - found
    if missing:
        raise ValueError(f"Source-scope exclusion no longer matches a test: {sorted(missing)}")
    if not selected:
        raise ValueError("No source tests selected")
    return unittest.TestSuite(selected)


def unit_tests(relative: str) -> int:
    path = ROOT / relative
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("sora_source_test", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    excluded = RAW_TESTS.get(relative, ())
    for name in excluded:
        print(f"OUTSIDE SOURCE SCOPE (private raw downloads): {name}", flush=True)
    classes = SOURCE_CLASSES.get(relative)
    if classes:
        print(f"SOURCE TEST CLASSES: {', '.join(classes)}; native-dependent classes are outside scope", flush=True)
        loaded = unittest.defaultTestLoader.loadTestsFromNames(classes, module)
    else:
        loaded = unittest.defaultTestLoader.loadTestsFromModule(module)
    suite = select_tests(loaded, excluded)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        print("FAIL: unexpected skipped tests are not source-check passes", file=sys.stderr)
    return 0 if result.wasSuccessful() and not result.skipped else 1


def lfs_materialized() -> int:
    inventory = json.loads(subprocess.check_output(["git", "lfs", "ls-files", "--json"], cwd=ROOT))
    paths = [row["name"] for row in inventory["files"]]
    if not paths:
        raise ValueError("No current-tree LFS files were discovered")
    missing = []
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            missing.append(str(path.relative_to(ROOT)))
            continue
        with path.open("rb") as stream:
            if stream.read(128).startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                missing.append(str(path.relative_to(ROOT)))
    if missing:
        print("Unmaterialized LFS assets; run git lfs pull before validating asset bytes:")
        print("\n".join(missing))
        return 1
    print(f"All {len(paths)} current-tree LFS files are materialized")
    return 0


def rust_pin() -> int:
    spec = importlib.util.spec_from_file_location("sora_source_doctor", ROOT / "scripts/toolchain/doctor.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.rust_checks(ROOT)
    print(json.dumps(result, indent=2))
    return 0 if all(row["ok"] for row in result) else 1


def source_identity(root: Path) -> dict:
    """Capture source identity without putting source diffs in public artifacts."""
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", *args], cwd=root)
    return {
        "commit": git("rev-parse", "HEAD").decode().strip(),
        "status": git("status", "--porcelain=v1", "--untracked-files=all").decode().splitlines(),
        "tracked_diff_sha256": hashlib.sha256(git("diff", "--binary", "HEAD")).hexdigest(),
        "untracked_sha256": {
            os.fsdecode(path): hashlib.sha256((root / os.fsdecode(path)).read_bytes()).hexdigest()
            for path in filter(None, git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0"))
        },
    }


def run_check(check: Check, root: Path, output: Path, env: dict) -> dict:
    log = output / f"{check.name}.log"
    started = time.monotonic()
    error = None
    print(f"RUN  [{check.group}] {check.name}", flush=True)
    with log.open("w", encoding="utf-8") as stream:
        try:
            completed = subprocess.run(check.command, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT)
            code = completed.returncode
            status = "passed" if code == 0 else "failed"
        except OSError as exc:
            error = str(exc)
            stream.write(error + "\n")
            code, status = None, "blocked"
    print(f"{status.upper():7} {check.name} ({time.monotonic() - started:.1f}s): {log}", flush=True)
    return {"name": check.name, "group": check.group, "command": list(check.command),
            "status": status, "exit_code": code, "error": error,
            "seconds": round(time.monotonic() - started, 3), "log": log.name}


def write_report(path: Path, report: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run(selected: list[Check], groups: list[str], output: Path, jobs: int) -> int:
    # Never append to or overwrite an earlier run's evidence.
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, RUSTUP_AUTO_INSTALL="0", CARGO_BUILD_JOBS=str(jobs), PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONOPTIMIZE", None)  # Several existing gates intentionally use assert.
    env["CARGO_TARGET_DIR"] = str(ROOT / "target/source-checks")
    report = {
        "schema": "sora-arena.source-checks.v1", "status": "running", "release_qualified": False,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "source_before": source_identity(ROOT), "platform": platform.platform(),
        "python": sys.version, "python_executable": sys.executable,
        "python_packages": {distribution.metadata["Name"]: distribution.version
                            for distribution in importlib.metadata.distributions()},
        "groups": groups, "groups_not_run": [group for group in GROUPS if group not in groups],
        "outside_scope": list(OUTSIDE_SCOPE), "raw_tests_outside_scope": RAW_TESTS,
        "source_only_test_classes": SOURCE_CLASSES,
        "cargo_build_jobs": jobs, "cargo_target_dir": env["CARGO_TARGET_DIR"], "checks": [],
    }
    report_path = output / "report.json"
    write_report(report_path, report)
    for check in selected:
        report["checks"].append(run_check(check, ROOT, output, env))
        write_report(report_path, report)
    report["source_after"] = source_identity(ROOT)
    stable = report["source_before"] == report["source_after"]
    report["source_unchanged"] = stable
    passed = stable and all(row["status"] == "passed" for row in report["checks"])
    report["status"] = "passed" if passed else "failed"
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    write_report(report_path, report)
    counts = {state: sum(row["status"] == state for row in report["checks"]) for state in ("passed", "failed", "blocked")}
    print(f"Source checks: {counts}; source unchanged: {stable}; report: {report_path}")
    print("Release qualification: NOT ESTABLISHED. See report outside_scope and groups_not_run.")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", action="append", choices=GROUPS, help="repeat to select groups; default: all")
    parser.add_argument("--output", type=Path, help="fresh log/report directory (default: Saved/SourceChecks/<UTC timestamp>)")
    parser.add_argument("--jobs", type=int, default=2, help="Cargo build parallelism (default: 2); checks run sequentially")
    parser.add_argument("--list", action="store_true", help="print selected commands without running them")
    internal = parser.add_mutually_exclusive_group()
    internal.add_argument("--unit-tests", help=argparse.SUPPRESS)
    internal.add_argument("--lfs-materialized", action="store_true", help=argparse.SUPPRESS)
    internal.add_argument("--rust-pin", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.unit_tests:
        return unit_tests(args.unit_tests)
    if args.lfs_materialized:
        return lfs_materialized()
    if args.rust_pin:
        return rust_pin()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    groups = list(dict.fromkeys(args.group or GROUPS))
    selected = [check for check in checks() if check.group in groups]
    if args.list:
        print(json.dumps([{"name": check.name, "group": check.group, "command": check.command} for check in selected], indent=2))
        return 0
    output = args.output or ROOT / "Saved/SourceChecks" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    try:
        return run(selected, groups, output.resolve(), args.jobs)
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"Source checks could not complete: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
