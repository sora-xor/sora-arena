#!/usr/bin/env python3
"""Run the production cancellation guard without loading Unreal or a wallet."""

import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    environment = os.environ.copy()
    compiler = shutil.which("clang++") or shutil.which("c++")
    sdk_args = []
    if platform.system() == "Darwin":
        versions = json.loads((ROOT / "scripts/toolchain/versions.json").read_text())
        environment["DEVELOPER_DIR"] = (
            environment.get("SORA_DEVELOPER_DIR")
            or str(Path(versions["default_macos_xcode"]).expanduser())
        )
        compiler = subprocess.check_output(
            ["xcrun", "--find", "clang++"], env=environment, text=True
        ).strip()
        sdk = subprocess.check_output(
            ["xcrun", "--sdk", "macosx", "--show-sdk-path"],
            env=environment, text=True,
        ).strip()
        environment["SDKROOT"] = sdk
        sdk_args = ["-isysroot", sdk]
    if not compiler:
        raise SystemExit("C++17 compiler required")
    with tempfile.TemporaryDirectory(prefix="sora-cancelled-signature-") as directory:
        binary = Path(directory) / "cancelled-signature-test"
        subprocess.run(
            [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic",
             *sdk_args, "-I", str(ROOT / "Source/SoraArena/Private"),
             str(ROOT / "scripts/connect/cancelled-signature-test.cpp"), "-o", str(binary)],
            check=True, env=environment,
        )
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
