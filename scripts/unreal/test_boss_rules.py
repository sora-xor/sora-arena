"""Host test for the campaign bosses' rules (Source/SoraArena/Public/SoraBossRules.h).

The driver checks difficulty scaling, phases and the blows that stop at their
starts, weak points, the fencer's metronome, the duellist's weighted rotation,
a blind hunter's hearing and sonar, charges, locked volleys, zones and wards,
and mutō-dori. Every fight in Content/Data/bosses.json is walked through its
phases with hits of several sizes.
"""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def fights():
    """One C++ initializer per boss and duel in bosses.json."""
    data = json.loads((ROOT / "Content/Data/bosses.json").read_text())
    rows = []
    for fight in data["bosses"] + data["duels"]:
        health = fight["health"]
        starts = [phase["from_permille"] for phase in fight["phases"]]
        floors = [phase["floor_permille"] for phase in fight["phases"]]
        pad = [0] * (4 - len(starts))
        rows.append('    {"%s", {%d, %d, %d}, %d, %d, {%s}, {%s}},' % (
            fight["id"], health["easy"], health["normal"], health["hard"], fight["floor_permille"], len(starts),
            ", ".join(map(str, starts + pad)), ", ".join(map(str, floors + pad))))
    assert rows, "bosses.json has no fights"
    return "constexpr FDataFight Fights_[] = {\n" + "\n".join(rows) + "\n};\n", len(rows)


table, count = fights()
env = os.environ.copy()
compiler = shutil.which("clang++") or shutil.which("c++")
sdk_flags = []
if platform.system() == "Darwin":
    pins = json.loads((ROOT / "scripts/toolchain/versions.json").read_text())
    env["DEVELOPER_DIR"] = env.get("SORA_DEVELOPER_DIR") or str(Path(pins["default_macos_xcode"]).expanduser())
    compiler = subprocess.check_output(["xcrun", "--find", "clang++"], env=env, text=True).strip()
    sdk = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"], env=env, text=True).strip()
    sdk_flags = ["-isysroot", sdk]
assert compiler, "A C++ compiler is required to test the boss rules"
with tempfile.TemporaryDirectory(prefix="sora-boss-rules-") as temp:
    include = Path(temp) / "boss_fights.inc"
    include.write_text(table)
    binary = Path(temp) / "boss-rules"
    # Asserts must stay live: the driver is nothing but asserts.
    subprocess.run([compiler, "-std=c++20", "-UNDEBUG", "-Wall", "-Werror", *sdk_flags,
                    "-I", str(ROOT / "Source/SoraArena/Public"), f'-DSORA_BOSS_TABLE="{include}"',
                    str(ROOT / "scripts/unreal/boss_rules_driver.cpp"), "-o", str(binary)],
                   check=True, env=env)
    subprocess.run([str(binary)], check=True, env=env)
print(f"Boss rules pass: difficulty, phases and their thresholds, weak points, metronome, weighted rotation, "
      f"hearing and sonar, charges, locked volleys, zones and wards, mutō-dori; all {count} fights in bosses.json "
      "walked through every phase")
