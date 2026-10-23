"""Chapter 08 collateral core contracts; ordinary loom data remains independent."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ConstructRulesTests(unittest.TestCase):
    def test_authored_slam_and_ordinary_loom_are_distinct(self):
        spec = (ROOT / "docs/campaign/chapter-08.md").read_text()
        self.assertIn("slam: {color: amber, windup_ms: 900, radius_cm: 250, damage: 25, recovery_ms: 1400}", spec)
        header = (ROOT / "Source/SoraArena/Public/SoraConstructRules.h").read_text()
        constants = {k: int(v) for k, v in re.findall(r"constexpr int (\w+) = (\d+);", header)}
        for key, value in dict(Health=260, WindupMs=900, RadiusCm=250, Damage=25, RecoveryMs=1400, SealCutMs=1000, HeavyHits=2).items():
            self.assertEqual(constants[key], value, key)
        data = json.loads((ROOT / "Content/Data/enemies.json").read_text())
        # Catalog layout is deliberately not extended for this one story add.
        loom = next(row for row in data["archetypes"] if row["id"] == "loom_automaton")
        self.assertEqual(loom["health"], 420)
        self.assertEqual([(a["id"], a["damage"], a["windup_ms"]) for a in loom["attacks"]],
                         [("beater_slam", 45, 1100), ("shuttle_thrust", 35, 800)])

    def test_native_core_admission_and_gentle_settle(self):
        source = r'''
#include "SoraConstructRules.h"
#include <cassert>
#include <cmath>
#include <initializer_list>
using namespace SoraConstructRules;
using SoraCombatRules::EHit;
int main() {
    assert(SealCutMs<RecoveryMs);
    assert(!Open(true,true,true,0)&&Open(true,true,true,1));
    assert(!Open(false,true,true,1400)&&!Open(true,false,true,1400)&&!Open(true,true,false,1400));
    for(int weapon=-1;weapon<24;++weapon) {
        const int stagger=SoraHistoricalArms::Profile(SoraHistoricalArms::FormFor(weapon)).StaggerMs;
        const bool heavy=weapon==6||weapon==8;
        assert(Heavy(EHit::Melee,weapon,stagger)==heavy);
        for(EHit kind:{EHit::Melee,EHit::Ranged,EHit::Blast,EHit::Beam,EHit::Scripted,EHit::Hazard}) {
            const int hit=CoreDamage(true,true,kind,weapon,stagger);
            assert(hit==(heavy&&kind==EHit::Melee?130:0));
            assert(CoreDamage(false,true,kind,weapon,stagger)==0);
            assert(CoreDamage(true,false,kind,weapon,stagger)==0);
        }
    }
    assert(!Heavy(EHit::Melee,8,799));
    // No rear/stagger amplification can turn one admitted contact into defeat.
    int health=Health;
    health-=CoreDamage(true,true,EHit::Melee,8,800); assert(health==130);
    health-=CoreDamage(false,true,EHit::Melee,8,800); assert(health==130);
    health-=CoreDamage(true,true,EHit::Melee,6,900); assert(health==0);
    for(int step:{1,7,16,33,100,500}) {
        float previous=0;
        for(int elapsed=0;elapsed<=SettleMs+step;elapsed+=step) {
            const float p=Settle(elapsed);
            assert(p>=previous&&p<=1); previous=p;
        }
    }
    assert(Settle(-1)==0&&Settle(0)==0&&Settle(SettleMs)==1&&Settle(9000)==1);
    assert(Settle(1)<.00001f&&1-Settle(SettleMs-1)<.00001f); // zero-speed endpoints
}
'''
        compiler = os.environ.get("CXX") or shutil.which("clang++") or shutil.which("c++")
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "construct.cpp").write_text(source)
            result = subprocess.run([compiler, "-std=c++17", "-I", str(ROOT / "Source/SoraArena/Public"),
                                     str(path / "construct.cpp"), "-o", str(path / "construct")],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(path / "construct")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
