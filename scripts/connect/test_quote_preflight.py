"""Compile and exercise read-only Join/Buy comparison rules with the pinned Mac SDK."""

import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
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
        env=environment, text=True
    ).strip()
    environment["SDKROOT"] = sdk
    sdk_args = ["-isysroot", sdk]
if not compiler:
    raise SystemExit("C++17 compiler required")

with tempfile.TemporaryDirectory(prefix="sora-quote-preflight-") as directory:
    binary = Path(directory) / "quote-preflight"
    subprocess.run(
        [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
         "-pedantic", *sdk_args, "-I", str(ROOT / "Source/SoraArena/Public"),
         str(ROOT / "scripts/connect/quote_preflight_driver.cpp"), "-o", str(binary)],
        check=True, env=environment,
    )
    subprocess.run([str(binary)], check=True)
