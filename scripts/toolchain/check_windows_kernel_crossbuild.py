"""Build and statically inspect the Windows GNU Arena kernel from macOS.

This cannot execute the DLL, test Unreal loading, or establish Windows parity.
The pinned Rust target and free MinGW compiler must already be installed.
"""

import ctypes
import hashlib
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
TOOLCHAIN = "1.93.1"
TARGET = "x86_64-pc-windows-gnu"
TARGET_DIR = ROOT / "target/windows-gnu-1.93.1"
DLL = TARGET_DIR / TARGET / "release/arena_ffi.dll"
HEADER = ROOT / "crates/arena-ffi/include/arena.h"


def run(*argv, env=None):
    return subprocess.run(argv, cwd=ROOT, env=env, text=True, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def source_digest():
    paths = [ROOT / "Cargo.toml", ROOT / "Cargo.lock", HEADER]
    for directory in (ROOT / "crates/arena-core/src", ROOT / "crates/arena-ffi/src"):
        paths.extend(sorted(directory.rglob("*.rs")))
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def main():
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit("This cross-check is scoped to the available Apple Silicon Mac.")
    installed = run("rustup", "target", "list", "--installed", "--toolchain", TOOLCHAIN).stdout.splitlines()
    if TARGET not in installed:
        raise SystemExit(f"Install the pinned target: rustup target add {TARGET} --toolchain {TOOLCHAIN}")
    rustc = run("rustc", f"+{TOOLCHAIN}", "--version").stdout.strip()
    if not rustc.startswith(f"rustc {TOOLCHAIN} "):
        raise SystemExit(f"Unexpected Rust compiler: {rustc}")
    mingw = run("x86_64-w64-mingw32-gcc", "--version").stdout.splitlines()[0]
    before = source_digest()
    env = os.environ.copy()
    env["CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER"] = "x86_64-w64-mingw32-gcc"
    env["CARGO_TARGET_DIR"] = str(TARGET_DIR)
    build = run("cargo", f"+{TOOLCHAIN}", "build", "--locked", "--offline", "--release",
                "-j2", "--target", TARGET, "-p", "arena-ffi", env=env)
    if not DLL.is_file() or before != source_digest():
        raise SystemExit("Windows DLL missing or Arena sources changed during build.")
    file_type = run("file", str(DLL)).stdout
    if "PE32+ executable (DLL)" not in file_type or "x86-64" not in file_type:
        raise SystemExit(f"Cross-build did not produce an x86-64 Windows DLL: {file_type}")

    sys.path.insert(0, str(ROOT / "scripts/unreal"))
    from kernel_abi import (Config, Participant, Input, Snapshot, Player, MapInfo,
                            MapWall, Presentation, Weapon, Event, Projectile)
    layouts = {
        "ArenaConfig": Config, "ArenaParticipant": Participant, "ArenaInput": Input,
        "ArenaSnapshot": Snapshot, "ArenaPlayerSnapshot": Player,
        "ArenaMapInfo": MapInfo, "ArenaMapWall": MapWall,
        "ArenaPlayerPresentation": Presentation, "ArenaWeaponSpec": Weapon,
        "ArenaEvent": Event, "ArenaProjectileSnapshot": Projectile,
    }
    assertions = ["#include \"arena.h\""]
    for name, host_type in layouts.items():
        assertions.append(f'_Static_assert(sizeof({name}) == {ctypes.sizeof(host_type)}, "{name} size");')
        assertions.append(f'_Static_assert(_Alignof({name}) == {ctypes.alignment(host_type)}, "{name} alignment");')
    with tempfile.TemporaryDirectory(prefix="sora-windows-abi-") as directory:
        source = Path(directory) / "abi.c"
        source.write_text("\n".join(assertions) + "\n", encoding="utf-8")
        run("x86_64-w64-mingw32-gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-c",
            "-I", str(HEADER.parent), str(source), "-o", str(Path(directory) / "abi.o"))

    header_exports = set(re.findall(
        r"^\s*(?:uint32_t|int32_t|void|ArenaHandle\*)\s+(arena_[a-z0-9_]+)\(",
        HEADER.read_text(), re.MULTILINE))
    exports = set(re.findall(
        r"^\s*\[\s*\d+\]\s+\+base\[\s*\d+\]\s+[0-9a-f]+\s+(arena_[a-z0-9_]+)\s*$",
        run("x86_64-w64-mingw32-objdump", "-p", str(DLL)).stdout, re.MULTILINE))
    if not header_exports or exports != header_exports:
        raise SystemExit(f"Header/DLL exports differ: missing={sorted(header_exports - exports)} extra={sorted(exports - header_exports)}")
    print(f"Windows GNU cross-build passed: {rustc}; {mingw}")
    print(f"PE x86-64 DLL: {DLL}")
    print(f"SHA-256: {hashlib.sha256(DLL.read_bytes()).hexdigest()}")
    print(f"Arena source SHA-256: {before}")
    print(f"ABI layout: {len(layouts)} C structs; exports: {len(exports)} exact names")
    print("Scope: static cross-build only; no Windows execution, Unreal import, or proof qualification.")
    if build.stderr.strip():
        print(build.stderr.strip(), file=sys.stderr)


if __name__ == "__main__":
    main()
