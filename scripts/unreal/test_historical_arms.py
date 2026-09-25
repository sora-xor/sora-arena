"""Host test for the offline Japanese-arm handling profile and catalog boundaries."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
catalog = json.loads((ROOT / "Content/Data/catalog.json").read_text())
arms = catalog["campaign_weapons"]
assert [arm["id"] for arm in arms] == [18, 19, 20]
assert [arm["name_en"] for arm in arms] == ["Yumi", "Yari", "Naginata"]
assert all(arm["class"] == 0 and not arm["special"] for arm in arms)
assert [arm["kind"] for arm in arms] == ["bow", "melee", "melee"]
assert [arm["range"] for arm in arms[1:]] == [285, 260]
assert arms[0]["projectile_speed"] > 0 and arms[0]["magazine"] > 0
assert len(catalog["weapons"]) == 18

env = os.environ.copy()
compiler = shutil.which("clang++") or shutil.which("c++")
sdk_flags = []
if platform.system() == "Darwin":
    pins = json.loads((ROOT / "scripts/toolchain/versions.json").read_text())
    env["DEVELOPER_DIR"] = env.get("SORA_DEVELOPER_DIR") or str(Path(pins["default_macos_xcode"]).expanduser())
    compiler = subprocess.check_output(["xcrun", "--find", "clang++"], env=env, text=True).strip()
    sdk = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"], env=env, text=True).strip()
    sdk_flags = ["-isysroot", sdk]
assert compiler, "A C++ compiler is required to test the historical arms profile"
with tempfile.TemporaryDirectory(prefix="sora-historical-arms-") as temp:
    binary = Path(temp) / "historical-arms"
    subprocess.run([compiler, "-std=c++20", *sdk_flags, "-I", str(ROOT / "Source/SoraArena/Public"),
                    str(ROOT / "scripts/unreal/historical_arms_driver.cpp"), "-o", str(binary)],
                   check=True, env=env)
    subprocess.run([str(binary)], check=True, env=env)
melee = [w for w in catalog["weapons"] + arms if w["kind"] == "melee"]
assert sorted(w["id"] for w in melee) == [0, 2, 4, 6, 8, 10, 12, 19, 20]
print("Historical offline arm profile passes: committed maai, timing and weight for all nine melee arms; "
      "yumi cataloged separately from Arena")
