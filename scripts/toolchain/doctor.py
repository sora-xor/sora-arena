#!/usr/bin/env python3
"""Inspect pinned release and explicitly opted-in interim Mac build prerequisites."""
import argparse
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
RELEASE_UE_VERSION = PINS["unreal"]["version"]
INTERIM_UE_VERSION = PINS["unreal"]["interim_compile_diagnostic_version"]


def command(args, env=None):
    try:
        result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=30, env=env)
        return result.returncode, result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def version_match(text):
    match = re.search(r"\b(\d+\.\d+\.\d+)\b", text)
    return match.group(1) if match else None


def inspect():
    checks = []

    def add(name, actual, expected, ok, detail=None):
        entry = {"name": name, "actual": actual, "expected": expected, "ok": bool(ok)}
        if detail:
            entry["detail"] = detail
        checks.append(entry)

    mac = platform.system() == "Darwin"
    add("host", platform.platform(), "macOS for these build scripts", mac)
    interim_request = os.environ.get("SORA_INTERIM_UE_VERSION")
    interim_mode = interim_request == INTERIM_UE_VERSION
    selection_ok = interim_request is None or interim_mode
    mode = ("interim_compile_diagnostic" if interim_mode else
            "release" if selection_ok else "invalid")
    selected_version = INTERIM_UE_VERSION if interim_mode else RELEASE_UE_VERSION
    add("engine_selection", interim_request if interim_request is not None else "unset",
        f"unset (release) or exactly {INTERIM_UE_VERSION} (compile diagnostic)", selection_ok)
    engine = Path(os.environ.get("UE_ROOT", PINS["unreal"]["default_macos_root"])).expanduser()
    engine_version = None
    version_path = engine / "Engine/Build/Build.version"
    if version_path.is_file():
        try:
            data = json.loads(version_path.read_text())
            engine_version = ".".join(str(data[k]) for k in ("MajorVersion", "MinorVersion", "PatchVersion"))
        except (OSError, ValueError, KeyError) as exc:
            add("engine_manifest", str(exc), "valid Build.version", False)
    build_sh = engine / "Engine/Build/BatchFiles/Mac/Build.sh"
    add("unreal", engine_version, selected_version,
        engine_version == selected_version and build_sh.is_file(), str(engine))
    source_commit = PINS["unreal"]["source_commit"]
    commit_ok = True
    if source_commit and (not interim_mode or engine_version == RELEASE_UE_VERSION):
        code, actual_commit = command(["git", "-C", str(engine), "rev-parse", "HEAD"])
        commit_ok = code == 0 and actual_commit == source_commit
        add("unreal_source_commit", actual_commit if code == 0 else None, source_commit, commit_ok)

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
    common_ready = mac and xcode_ok and sdk_ok and setup_ok and len(projects) == 1
    release_ready = (common_ready and engine_version == RELEASE_UE_VERSION and
                     build_sh.is_file() and commit_ok)
    interim_ready = (common_ready and interim_mode and selection_ok and
                     engine_version == INTERIM_UE_VERSION and build_sh.is_file() and editor_ok)
    build_ready = (release_ready if mode == "release" else
                   interim_ready if mode == "interim_compile_diagnostic" else False)
    note = ("Interim UE 5.8.3 compile/editor diagnostics only; the 5.8.2 release pin and "
            "source-revision/packaging/runtime acceptance remain unmet."
            if interim_mode else
            "Presence/version checks only; successful Unreal compilation, cooking and runtime testing are separate acceptance checks.")
    return {"build_ready": build_ready, "release_prerequisites_ready": release_ready,
            "interim_compile_prerequisites_ready": interim_ready,
            "engine_mode": mode, "selected_engine_version": selected_version,
            "release_engine_version": RELEASE_UE_VERSION,
            "all_checks_pass": all(c["ok"] for c in checks),
            "engine_root": str(engine), "developer_dir": developer_dir, "checks": checks,
            "sdk_root": sdk_path,
            "note": note}


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
        print("\nUE 5.8.2 release prerequisites: " +
              ("READY" if report["release_prerequisites_ready"] else "NOT READY"))
        print("UE 5.8.3 interim compile prerequisites: " +
              ("READY" if report["interim_compile_prerequisites_ready"] else "NOT READY"))
        print("Selected Mac build mode: " + report["engine_mode"] + " (" +
              ("READY" if report["build_ready"] else "NOT READY") + ")")
        print(report["note"])
    return 0 if report["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
