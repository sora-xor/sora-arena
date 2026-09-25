"""Host test for the offline opponents' awareness rules (Source/SoraArena/Public/SoraStealthRules.h)."""
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
assert compiler, "A C++ compiler is required to test the stealth rules"
with tempfile.TemporaryDirectory(prefix="sora-stealth-rules-") as temp:
    binary = Path(temp) / "stealth-rules"
    # Asserts must stay live: the driver is nothing but asserts.
    subprocess.run([compiler, "-std=c++20", "-UNDEBUG", "-Wall", "-Werror", *sdk_flags,
                    "-I", str(ROOT / "Source/SoraArena/Public"),
                    str(ROOT / "scripts/unreal/stealth_rules_driver.cpp"), "-o", str(binary)],
                   check=True, env=env)
    subprocess.run([str(binary)], check=True, env=env)
print("Stealth rules pass: view cone, line of sight, exposure, stance, range and light; hearing by stance "
      "and floor; unaware/suspicious/alert/search/combat/retreat transitions; zone vigilance, difficulty, "
      "search decay and wariness; detection, carryover, alarms and found bodies; work under guard; "
      "rear takedowns; slot roles and cover preference")
