"""Host test for the offline campaign combat rules (Source/SoraArena/Public/SoraCombatRules.h).

The driver checks guard and parry against every melee attack in
Content/Data/enemies.json, and the shells' arming distances against the
kernel's weapons 7 and 15 in crates/arena-core/src/catalog.rs.
"""
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def kernel_arming_mm():
    """Arming distance of each projectile weapon in the kernel's frozen table."""
    source = (ROOT / "crates/arena-core/src/catalog.rs").read_text()
    table = source[source.index("pub const WEAPONS"):]
    arming = {}
    for call in re.finditer(r"\bw\(\s*(.*?)\)\s*,", table, re.S):
        fields = [field.strip() for field in call.group(1).split(",") if field.strip()]
        if len(fields) == 13:
            arming[int(fields[0])] = int(fields[9])
    assert len(arming) == 18, f"expected 18 kernel weapons, parsed {len(arming)}"
    return arming


def melee_attacks():
    """One C++ initializer per melee attack in enemies.json."""
    data = json.loads((ROOT / "Content/Data/enemies.json").read_text())
    rows = []
    for archetype in data["archetypes"]:
        for attack in archetype["attacks"]:
            if attack["kind"] != "melee":
                continue
            guard = attack["guard"]
            rows.append('    {"%s.%s", {EHit::Melee, %d, %s, %d, %d, %d, %s}},' % (
                archetype["id"], attack["id"], attack["damage"], "true" if guard["parry"] else "false",
                guard["chip"], guard["stamina"], guard["parry_stagger_ms"], "true" if guard["breaks"] else "false"))
    assert rows, "enemies.json has no melee attacks"
    return "constexpr FDataAttack EnemyMeleeAttacks[] = {\n" + "\n".join(rows) + "\n};\n", len(rows)


arming = kernel_arming_mm()
table, count = melee_attacks()
env = os.environ.copy()
compiler = shutil.which("clang++") or shutil.which("c++")
sdk_flags = []
if platform.system() == "Darwin":
    pins = json.loads((ROOT / "scripts/toolchain/versions.json").read_text())
    env["DEVELOPER_DIR"] = env.get("SORA_DEVELOPER_DIR") or str(Path(pins["default_macos_xcode"]).expanduser())
    compiler = subprocess.check_output(["xcrun", "--find", "clang++"], env=env, text=True).strip()
    sdk = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"], env=env, text=True).strip()
    sdk_flags = ["-isysroot", sdk]
assert compiler, "A C++ compiler is required to test the combat rules"
with tempfile.TemporaryDirectory(prefix="sora-combat-rules-") as temp:
    attacks = Path(temp) / "enemy_attacks.inc"
    attacks.write_text(table)
    binary = Path(temp) / "combat-rules"
    # Asserts must stay live: the driver is nothing but asserts.
    subprocess.run([compiler, "-std=c++20", "-UNDEBUG", "-Wall", "-Werror", *sdk_flags,
                    "-I", str(ROOT / "Source/SoraArena/Public"),
                    f'-DSORA_ENEMY_ATTACKS="{attacks}"',
                    f"-DKERNEL_ARMING_7_MM={arming[7]}", f"-DKERNEL_ARMING_15_MM={arming[15]}",
                    str(ROOT / "scripts/unreal/combat_rules_driver.cpp"), "-o", str(binary)],
                   check=True, env=env)
    subprocess.run([str(binary)], check=True, env=env)
print(f"Combat rules pass: guard and parry against all {count} melee attacks in enemies.json and the collector's cleave; "
      "ranged and blast chip; hit-stop; stagger, poise and immunity; shields, rears and barriers; "
      f"arming at the kernel's {arming[7]} and {arming[15]} mm; self-damage; subdue and seal-cut; fixed miss pattern; "
      "mutō-dori, marobashi, zanshin and the maai ring")
