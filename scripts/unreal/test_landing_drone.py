"""Run the production landing-drone state machine; physical cases run in UE."""
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
assert compiler, "A C++ compiler is required for the landing drone rules"
with tempfile.TemporaryDirectory(prefix="sora-landing-drone-") as directory:
    binary = Path(directory) / "landing-drone"
    subprocess.run([compiler, "-std=c++20", "-UNDEBUG", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=undefined", "-fsanitize-trap=undefined", *sdk_flags,
                    "-I", str(ROOT / "Source/SoraArena/Public"),
                    str(ROOT / "scripts/unreal/landing_drone_rules_driver.cpp"), "-o", str(binary)],
                   check=True, env=env)
    subprocess.run([str(binary)], check=True, env=env)
print("Landing drone rules pass: active warning, physical-arrival gate, one release, low recovery, "
      "interruption, difficulty durations and scoped wakizashi vulnerability. UE collision remains separate.")
