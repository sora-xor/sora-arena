#!/usr/bin/env python3
"""Inspect the pinned Unreal, Xcode, Metal and Rust prerequisites for Mac builds."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PINS = json.loads((HERE / "versions.json").read_text())
_ENGINE_PIN_SPEC = importlib.util.spec_from_file_location(
    "sora_engine_pin", ROOT / "scripts/unreal/sora_engine_pin.py")
engine_pin = importlib.util.module_from_spec(_ENGINE_PIN_SPEC)
_ENGINE_PIN_SPEC.loader.exec_module(engine_pin)
# TODO: remove SORA_INTERIM_UE_VERSION handling after Wave A. Build wrappers
# started before the re-pin still export it; exactly the pinned version is a
# no-op and any other set value fails closed.
TRANSITIONAL_ENGINE_VARIABLE = "SORA_INTERIM_UE_VERSION"


def command(args, env=None, cwd=None):
    try:
        result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=30, env=env, cwd=cwd)
        return result.returncode, result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def version_match(text):
    match = re.search(r"\b(\d+\.\d+\.\d+)\b", text)
    return match.group(1) if match else None


def rust_checks(root=ROOT):
    """Compare rust-toolchain.toml and the compiler cargo selects in the repository with the Rust pin."""
    pin = PINS["rust"]
    expected = f"{pin['version']} ({pin['commit_hash']})"
    toolchain_file = root / "rust-toolchain.toml"
    try:
        match = re.search(r'^channel\s*=\s*"([^"]*)"\s*$', toolchain_file.read_text(), re.MULTILINE)
    except OSError:
        match = None
    channel = match.group(1) if match else None
    checks = [{"name": "rust_toolchain_file", "actual": channel, "expected": pin["version"],
               "ok": channel == pin["version"], "detail": str(toolchain_file)}]
    # rustup resolves rust-toolchain.toml from the working directory. Disable
    # its auto-install so a missing pinned toolchain fails instead of downloading.
    code, output = command(["rustc", "-vV"], env=dict(os.environ, RUSTUP_AUTO_INSTALL="0"), cwd=root)
    fields = dict(line.split(": ", 1) for line in output.splitlines() if ": " in line) if code == 0 else {}
    actual = f"{fields['release']} ({fields['commit-hash']})" if "release" in fields and "commit-hash" in fields else None
    entry = {"name": "rustc", "actual": actual, "expected": expected, "ok": actual == expected}
    if not entry["ok"]:
        entry["detail"] = output
    checks.append(entry)
    return checks


def inspect():
    checks = []

    def add(name, actual, expected, ok, detail=None):
        entry = {"name": name, "actual": actual, "expected": expected, "ok": bool(ok)}
        if detail:
            entry["detail"] = detail
        checks.append(entry)

    mac = platform.system() == "Darwin"
    add("host", platform.platform(), "macOS for these build scripts", mac)
    transitional = os.environ.get(TRANSITIONAL_ENGINE_VARIABLE)
    selection_ok = transitional is None or transitional == engine_pin.PIN["version"]
    if not selection_ok:
        add("transitional_engine_variable", transitional,
            f"unset, or exactly {engine_pin.PIN['version']} (ignored)", False)
    engine = Path(os.environ.get("UE_ROOT", PINS["unreal"]["default_macos_root"])).expanduser()
    identity = engine_pin.identity_checks(engine)
    checks.extend(identity)
    identity_ok = all(check["ok"] for check in identity)
    build_sh = engine / "Engine/Build/BatchFiles/Mac/Build.sh"
    add("unreal_build_script", str(build_sh) if build_sh.is_file() else None,
        "Engine/Build/BatchFiles/Mac/Build.sh", build_sh.is_file())

    candidates = [Path(PINS["default_macos_xcode"]).expanduser(),
                  Path("/Applications/Xcode_26.1.1.app/Contents/Developer"),
                  Path("/Applications/Xcode.app/Contents/Developer")]
    developer_dir = os.environ.get("SORA_DEVELOPER_DIR") or os.environ.get("DEVELOPER_DIR")
    if not developer_dir:
        developer_dir = str(next((path for path in candidates if path.is_dir()), candidates[0]))
    build_env = dict(os.environ, DEVELOPER_DIR=developer_dir)
    code, output = command(["xcodebuild", "-version"], env=build_env)
    match = re.search(r"^Xcode (\S+)", output, re.MULTILINE)
    xcode_version = match.group(1) if match else None
    xcode_ok = code == 0 and xcode_version == PINS["xcode"]
    add("xcode", xcode_version, PINS["xcode"], xcode_ok, developer_dir)
    if code:
        add("xcode_execution", output, "xcodebuild succeeds", False)
    code, output = command(["xcrun", "--sdk", "macosx", "--show-sdk-path"], env=build_env)
    sdk_ok = code == 0 and Path(output).is_dir()
    sdk_path = output if sdk_ok else None
    add("macos_sdk", output if sdk_ok else None, "available through selected Xcode", sdk_ok)
    code, output = command(["xcodebuild", "-checkFirstLaunchStatus"], env=build_env)
    setup_ok = code == 0
    add("xcode_first_launch", "complete" if setup_ok else "incomplete", "setup already complete", setup_ok,
        output if not setup_ok else None)
    code, metal_output = command(["xcrun", "--sdk", "macosx", "metal", "-v"], env=build_env)
    metal_ok = code == 0
    add("metal_toolchain", "available" if metal_ok else "missing",
        "Metal compiler executable through selected Xcode", metal_ok,
        metal_output if not metal_ok else None)

    blender = shutil.which("blender") or "/Applications/Blender.app/Contents/MacOS/Blender"
    code, output = command([blender, "--version"])
    blender_version = version_match(output) if code == 0 else None
    add("blender", blender_version, PINS["blender"], blender_version == PINS["blender"], blender)
    code, output = command(["git", "lfs", "version"])
    lfs_version = version_match(output) if code == 0 else None
    add("git_lfs", lfs_version, PINS["git_lfs"], lfs_version == PINS["git_lfs"])
    code, output = command(["git", "-C", str(ROOT), "config", "--local", "--get", "filter.lfs.process"])
    add("git_lfs_repository", output if code == 0 else None, "git-lfs filter-process", code == 0 and output == "git-lfs filter-process")
    projects = sorted(ROOT.glob("*.uproject"))
    add("project", [p.name for p in projects], "one root .uproject", len(projects) == 1)
    editor = engine / "Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
    editor_ok = editor.is_file() and os.access(editor, os.X_OK)
    add("editor_binary", str(editor) if editor.is_file() else None, "UnrealEditor executable", editor_ok)
    free_gib = round(shutil.disk_usage(ROOT).free / (1024 ** 3), 1)
    add("free_disk_gib", free_gib, "at least 100 GiB before engine installation/build", free_gib >= 100)
    rust = rust_checks()
    checks.extend(rust)
    engine_ok = selection_ok and identity_ok and build_sh.is_file() and editor_ok
    build_ready = mac and xcode_ok and sdk_ok and setup_ok and len(projects) == 1 and engine_ok
    cook_ready = build_ready and metal_ok
    # The Mac wrappers read build_ready (cook_ready for the cook), engine_root,
    # developer_dir and sdk_root; main() reads pinned_engine_version, rust_ready
    # and all_checks_pass.
    return {"build_ready": build_ready, "cook_ready": cook_ready,
            "pinned_engine_version": engine_pin.ENGINE_VERSION,
            "rust_ready": all(c["ok"] for c in rust),
            "all_checks_pass": all(c["ok"] for c in checks),
            "engine_root": str(engine), "developer_dir": developer_dir, "checks": checks,
            "sdk_root": sdk_path,
            "note": "Presence/version checks only; successful Unreal compilation, cooking and "
                    "runtime testing are separate acceptance checks."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable status")
    args = parser.parse_args()
    report = inspect()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for check in report["checks"]:
            mark = "OK" if check["ok"] else "MISSING/MISMATCH"
            print(f"{mark:17} {check['name']}: {check['actual']} (expected {check['expected']})")
            if "detail" in check:
                print(f"                  {check['detail']}")
        print(f"\nPinned UE {report['pinned_engine_version']} Mac build prerequisites: " +
              ("READY" if report["build_ready"] else "NOT READY"))
        print("Mac cook prerequisites (adds Metal compiler): " +
              ("READY" if report["cook_ready"] else "NOT READY"))
        print("Pinned Rust kernel toolchain: " +
              ("READY" if report["rust_ready"] else "NOT READY"))
        print(report["note"])
    return 0 if report["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
