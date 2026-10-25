"""Host test for the campaign's arms selection and fieldcraft rules
(Source/SoraArena/Public/SoraArmsRules.h and SoraFieldcraftRules.h)."""
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
assert compiler, "A C++ compiler is required to test the fieldcraft rules"
with tempfile.TemporaryDirectory(prefix="sora-fieldcraft-rules-") as temp:
    for name in ("fieldcraft", "press"):
        binary = Path(temp) / (name + "-rules")
        # Assertions stay live; undefined behavior traps on both rule drivers.
        subprocess.run([compiler, "-std=c++20", "-UNDEBUG", "-O2", "-fsanitize=undefined", "-fsanitize-trap=undefined",
                        "-Wall", "-Werror", *sdk_flags,
                        "-I", str(ROOT / "Source/SoraArena/Public"),
                        str(ROOT / f"scripts/unreal/{name}_rules_driver.cpp"), "-o", str(binary)],
                       check=True, env=env)
        subprocess.run([str(binary)], check=True, env=env)

print("Fieldcraft rules pass: the arms ring, groups, stepping and wheel sectors; companions downed, raised by a "
      "held hand or a healing lance, bleeding out, freed from collars and cells, hidden and sent on by signal, and "
      "the party walking only whole; held work; lamps snuffed and relit; breath and drowning at any frame rate; grip, "
      "ledges and falls; tsubute stones and their capped lure; the candle; vaulting; the kusarigama's chain; "
      "rotating volley ranks, their reload, the volley's split, its smoke and Easy's auto-order; seizure nets locked, "
      "cut by hand or from the saddle, loosened by a downed tether and hauled off, and a cut net's reload; searchlights' sweep and the time a "
      "head in the spot takes to be noticed; the one-shot bell; guttering cook-fires; a roof's drop; the charge's pace "
      "and its seal stakes")
