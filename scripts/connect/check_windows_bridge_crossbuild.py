#!/usr/bin/env python3
"""Cross-build and statically check the native Windows Connect bridge on macOS.

This cannot load the DLL or establish Windows wallet/runtime interoperability.
Only a source-stable PE with the exact C export set is staged for later testing.
"""

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
IROHA = Path(os.environ.get("IROHA_SOURCE_ROOT", ROOT.parent / "iroha-arena")).resolve()
TOOLCHAIN = "1.93.1"
TARGET = "x86_64-pc-windows-gnu"
TARGET_DIR = IROHA / "target" / f"windows-gnu-{TOOLCHAIN}"
DLL = TARGET_DIR / TARGET / "release" / "connect_norito_bridge.dll"
HEADER = IROHA / "crates/connect_norito_bridge/include/connect_norito_bridge.h"
STAGED = ROOT / "Binaries/Win64/connect_norito_bridge.dll"


def run(*argv, cwd=IROHA, env=None):
    result = subprocess.run(argv, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(f"{' '.join(argv)} failed ({result.returncode}):\n"
                           f"{(result.stdout + result.stderr)[-12000:]}")
    return result


def source_seal():
    revision = run("git", "rev-parse", "HEAD").stdout.strip()
    tracked_diff = run("git", "diff", "HEAD", "--").stdout.encode()
    # Untracked Rust files can be compiled through a module declaration. Include
    # their path and bytes instead of treating a clean tracked diff as sufficient.
    untracked = run("git", "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    extra = hashlib.sha256()
    for name in sorted(untracked):
        path = IROHA / name
        if path.is_file() and (path.suffix == ".rs" or path.name in ("Cargo.toml", "Cargo.lock")):
            extra.update(name.encode())
            extra.update(b"\0")
            extra.update(path.read_bytes())
            extra.update(b"\0")
    return {
        "source_revision": revision,
        "tracked_diff_sha256": hashlib.sha256(tracked_diff).hexdigest(),
        "untracked_build_source_sha256": extra.hexdigest(),
        "header_sha256": hashlib.sha256(HEADER.read_bytes()).hexdigest(),
    }


def exported_symbols():
    output = run("x86_64-w64-mingw32-objdump", "-p", str(DLL)).stdout
    match = re.search(r"\[Ordinal/Name Pointer\] Table\s*(.*?)(?:\n\s*The Function Table|\Z)",
                      output, re.DOTALL)
    if not match:
        raise RuntimeError("PE export name table is absent")
    return set(re.findall(r"^\s*\[\s*\d+\]\s+\+base\[\s*\d+\]\s+[0-9a-fA-F]+\s+(connect_norito_[a-z0-9_]+)\s*$",
                          match.group(1), re.MULTILINE))


def main():
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit("This cross-check is scoped to the available Apple Silicon Mac.")
    if not HEADER.is_file():
        raise SystemExit(f"Matching Iroha header missing: {HEADER}")
    installed = run("rustup", "target", "list", "--installed", "--toolchain", TOOLCHAIN).stdout.splitlines()
    if TARGET not in installed:
        raise SystemExit(f"Install {TARGET} for Rust {TOOLCHAIN} first")
    rustc = run("rustc", f"+{TOOLCHAIN}", "--version").stdout.strip()
    if not rustc.startswith(f"rustc {TOOLCHAIN} "):
        raise SystemExit(f"Unexpected compiler: {rustc}")
    before = source_seal()
    env = os.environ.copy()
    # Rust host build scripts are macOS binaries even for a Windows target.
    # Pin their SDK and linker explicitly: the system Command Line Tools may
    # point at a newer SDK that this project's compiler cannot parse.
    env["DEVELOPER_DIR"] = os.path.expanduser(
        env.get("DEVELOPER_DIR", "~/Applications/SORAToolchain/Xcode_26.1.1.app/Contents/Developer")
    )
    env["SDKROOT"] = run("xcrun", "--sdk", "macosx", "--show-sdk-path", env=env).stdout.strip()
    env["CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER"] = run(
        "xcrun", "--find", "clang", env=env
    ).stdout.strip()
    env["CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER"] = "x86_64-w64-mingw32-gcc"
    env["CC_x86_64_pc_windows_gnu"] = "x86_64-w64-mingw32-gcc"
    env["CXX_x86_64_pc_windows_gnu"] = "x86_64-w64-mingw32-g++"
    env["AR_x86_64_pc_windows_gnu"] = "x86_64-w64-mingw32-ar"
    env["CARGO_TARGET_DIR"] = str(TARGET_DIR)
    build = run("cargo", f"+{TOOLCHAIN}", "build", "--locked", "--release", "-j2",
                "--target", TARGET, "-p", "connect_norito_bridge", "--lib", env=env)
    if not DLL.is_file() or source_seal() != before:
        raise SystemExit("Windows bridge is missing or Iroha sources changed during build")
    file_type = run("file", str(DLL)).stdout
    if "PE32+ executable (DLL)" not in file_type or "x86-64" not in file_type:
        raise SystemExit(f"Unexpected Windows bridge format: {file_type}")
    header_symbols = set(re.findall(
        r"^\s*(?:uint32_t|int32_t|void)\s+(connect_norito_[a-z0-9_]+)\(",
        HEADER.read_text(), re.MULTILINE))
    exports = exported_symbols()
    if not header_symbols or exports != header_symbols:
        raise SystemExit(f"Bridge export mismatch: missing={sorted(header_symbols - exports)} "
                         f"extra={sorted(exports - header_symbols)}")
    run(sys.executable, str(ROOT / "scripts/connect/check-abi.py"),
        "--compiler", "x86_64-w64-mingw32-g++", cwd=ROOT)
    STAGED.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DLL, STAGED)
    manifest = {
        **before,
        "rustc": rustc,
        "target": TARGET,
        "library_sha256": hashlib.sha256(STAGED.read_bytes()).hexdigest(),
        "export_count": len(exports),
        "qualification": "static cross-build only; no Windows execution, Unreal load, wallet pairing or transaction",
    }
    STAGED.with_suffix(".dll.build.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Windows GNU Connect bridge static cross-build passed: {STAGED}")
    print(f"SHA-256: {manifest['library_sha256']}; exact C exports: {len(exports)}")
    print("Windows runtime and wallet qualification remain open.")
    if build.stderr.strip():
        print(build.stderr.strip(), file=sys.stderr)


if __name__ == "__main__":
    main()
