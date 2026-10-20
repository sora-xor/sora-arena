"""Supply restocking preserves catalog caps, entitlement and held inventory."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SupplyRulesTests(unittest.TestCase):
    def test_authored_named_cache_and_existing_supply_forms_remain(self):
        chapters = [json.loads(p.read_text()) for p in sorted(
            (ROOT / "Content/Data/campaign").glob("chapter_*.json"))]
        early = chapters[2]["beats"][13]["ext"]["supply_point"]
        self.assertEqual(early["id"], "vol_b14_supply")
        self.assertEqual(early["refill"], ["arrows", "shells"])
        self.assertEqual(early["slots"], {"side": [4], "polearm": [19], "firearm": [7]})
        late = chapters[7]["beats"][9]
        self.assertEqual(late["ext"]["supply_point"], "sp_spire_base")
        self.assertEqual(late["unlocks"]["weapons"], [])
        self.assertEqual(late["unlocks"]["grants"], [])
        self.assertTrue(late["checkpoint"])
        self.assertEqual(chapters[7]["space"]["beats"][9]["spire"]["ramp"][0][2], 0)

    def test_native_inventory_caps_locked_weapons_and_stale_held_copy(self):
        data = json.loads((ROOT / "Content/Data/catalog.json").read_text())
        weapons = data["weapons"] + data["campaign_weapons"]
        self.assertEqual([w["id"] for w in weapons], list(range(21)))
        self.assertEqual(weapons[18]["magazine"], 12)
        caps = [w["magazine"] if w["kind"] != "melee" else 0 for w in weapons]
        source = r'''
#include "SoraSupplyRules.h"
#include "SoraHistoricalArms.h"
#include <algorithm>
#include <array>
#include <cassert>
#include <vector>
int main() {
    constexpr int Count=21;
    constexpr int Caps[]={CAPS};
    constexpr unsigned All=(1u<<Count)-1;
    for(int n=0;n<Count;++n)
        assert((Caps[n]==0)==SoraHistoricalArms::IsMelee(n));
    std::vector<unsigned> Masks{0,All,0x155555,0x0aaaaa};
    for(int n=0;n<Count;++n) { Masks.push_back(1u<<n); Masks.push_back(All^(1u<<n)); }
    for(unsigned mask:Masks) for(int held=0;held<Count;++held) for(int state=0;state<3;++state) {
        std::array<int,Count> stored;
        // Locked and melee slots carry distinct sentinels. An implementation
        // that resets the whole loadout would destroy them.
        for(int n=0;n<Count;++n) stored[n]=Caps[n]>0?(state==0?0:state==1?Caps[n]-1:Caps[n]):70+n;
        const auto before=stored;
        int ammo=Caps[held]>0?(state==2?0:Caps[held]):113;
        const int activeBefore=ammo;
        int expected=0;
        for(int n=0;n<Count;++n)
            if((mask&(1u<<n))&&Caps[n]>0&&(n==held?ammo:stored[n])<Caps[n]) ++expected;
        assert(SoraSupplyRules::Restock(stored.data(),Caps,Count,mask,held,ammo)==expected);
        for(int n=0;n<Count;++n)
            assert(stored[n]==((mask&(1u<<n))&&Caps[n]>0?Caps[n]:before[n]));
        assert(ammo==((mask&(1u<<held))&&Caps[held]>0?Caps[held]:activeBefore));
        const auto full=stored; const int fullAmmo=ammo;
        for(int use=0;use<10;++use) {
            assert(SoraSupplyRules::Restock(stored.data(),Caps,Count,mask,held,ammo)==0);
            assert(stored==full&&ammo==fullAmmo);
        }
        // Actual held spending does not synchronize the stored copy yet.
        // A later visit must still see the spent arrow/round and refill once.
        if((mask&(1u<<held))&&Caps[held]>0) {
            --ammo;
            assert(stored[held]==Caps[held]);
            assert(SoraSupplyRules::Restock(stored.data(),Caps,Count,mask,held,ammo)==1);
            assert(ammo==Caps[held]&&stored[held]==Caps[held]);
        }
    }
}
'''.replace("CAPS", ",".join(map(str, caps)))
        compiler = os.environ.get("CXX") or shutil.which("clang++") or shutil.which("c++")
        self.assertIsNotNone(compiler, "Host C++ compiler is required")
        with tempfile.TemporaryDirectory() as tmp:
            cpp, binary = Path(tmp) / "supply.cpp", Path(tmp) / "supply"
            cpp.write_text(source)
            subprocess.run([compiler, "-std=c++17", "-I", str(ROOT / "Source/SoraArena/Public"),
                            str(cpp), "-o", str(binary)], check=True, capture_output=True, text=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
