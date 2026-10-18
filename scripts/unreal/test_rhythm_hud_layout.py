"""Compile and exercise the live rhythm/prompt pixel-bound helper, without UE."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]

env = os.environ.copy()
compiler = shutil.which("clang++") or shutil.which("c++")
sdk_flags = []
if platform.system() == "Darwin":
    pins = json.loads((ROOT / "scripts/toolchain/versions.json").read_text())
    env["DEVELOPER_DIR"] = env.get("SORA_DEVELOPER_DIR") or str(Path(pins["default_macos_xcode"]).expanduser())
    compiler = subprocess.check_output(["xcrun", "--find", "clang++"], env=env, text=True).strip()
    sdk = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"], env=env, text=True).strip()
    sdk_flags = ["-isysroot", sdk]
assert compiler, "A C++ compiler is required to test the rhythm-hud-layout rules"
with tempfile.TemporaryDirectory(prefix="sora-rhythm-hud-layout-rules-") as temp:
    binary = Path(temp) / "rhythm-hud-layout-rules"
    # Asserts must stay live: the driver is nothing but asserts. It is built
    # optimized as the editor builds the rules, with undefined behaviour
    # trapping instead of silently miscomparing.
    subprocess.run([compiler, "-std=c++20", "-UNDEBUG", "-O2", "-fsanitize=undefined", "-fsanitize-trap=undefined",
                    "-Wall", "-Werror", *sdk_flags,
                    "-I", str(ROOT / "Source/SoraArena/Public"),
                    str(ROOT / "scripts/unreal/rhythm_hud_layout_driver.cpp"), "-o", str(binary)],
                   check=True, env=env)
    subprocess.run([str(binary)], check=True, env=env)
