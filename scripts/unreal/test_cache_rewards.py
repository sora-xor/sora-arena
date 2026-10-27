"""Finite arrow cache admission, authored quantities and durable claim rules.

The native harness executes the production header rules, without Unreal.
The mapped-input integration fixture is SoraArena.Campaign.CacheArrows.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "ch02.b14": ("arrows_refill_12", 12, True),
    "ch04.b09": ("arrows:6", 6, False),
    "ch05.b13": ("arrows:12", 12, False),
    "ch06.b07": ("arrows:6", 6, False),
    "ch07.b05": ("arrows_12", 12, False),
}


def chapters():
    return [json.loads(p.read_text()) for p in sorted(
        (ROOT / "Content/Data/campaign").glob("chapter_*.json"))]


class CacheRewardsTests(unittest.TestCase):
    def run_native(self, source):
        compiler = os.environ.get("CXX") or shutil.which("clang++") or shutil.which("c++")
        self.assertIsNotNone(compiler, "Host C++ compiler is required")
        with tempfile.TemporaryDirectory() as tmp:
            cpp, binary = Path(tmp) / "cache.cpp", Path(tmp) / "cache"
            cpp.write_text(source)
            compiled = subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                                       "-I", str(ROOT / "Source/SoraArena/Public"), str(cpp), "-o", str(binary)],
                                      capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_authored_rewards_have_exclusive_finds_and_follow_yumi_unlock(self):
        weapons = set()
        found = set()
        for chapter in chapters():
            for beat in chapter["beats"]:
                if beat["id"] in EXPECTED:
                    found.add(beat["id"])
                    token, _, _ = EXPECTED[beat["id"]]
                    rewards = beat["params"]["rewards"]
                    self.assertEqual([r for r in rewards if r.startswith("arrow")], [token])
                    self.assertTrue(beat["optional"])
                    self.assertEqual(beat["task"]["goal"], "cache")
                    self.assertIn(18, weapons, "This cache may not invent yumi entitlement")
                    finds = {r for r in rewards if r.startswith("ch")}
                    self.assertTrue(finds)
                    for item in finds:
                        holders = [b["id"] for b in chapter["beats"]
                                   if item in b["params"].get("rewards", [])]
                        self.assertEqual(holders, [beat["id"]])
                        loose = chapter["space"]["pickups"]
                        self.assertFalse(any(p["collectible"] == item for p in loose))
                if not beat["optional"]:
                    weapons.update(beat["unlocks"]["weapons"])
        self.assertEqual(found, set(EXPECTED))
        # Other ammunition contracts remain present and are not replaced by
        # an unlimited resupply or silently mapped into the arrow magazine.
        all_beats = {b["id"]: b for c in chapters() for b in c["beats"]}
        self.assertIn("hayago:10", all_beats["ch04.b09"]["params"]["rewards"])
        self.assertIn("arc_carbine_rounds:48", all_beats["ch05.b13"]["params"]["rewards"])
        self.assertEqual(all_beats["ch08.b12"]["params"]["rewards"][-1], "arrows_12")

    def test_native_reader_admits_original_tokens_and_rejects_mutations(self):
        rows = []
        all_beats = {b["id"]: b for c in chapters() for b in c["beats"]}
        for beat, (token, amount, refill) in EXPECTED.items():
            tokens = all_beats[beat]["params"]["rewards"]
            rows.append("""{
                const char* tokens[]={TOKENS}; FArrows reward;
                assert(Read(BEAT,tokens,COUNT,reward));
                assert(reward.Amount==AMOUNT&&reward.Refill==REFILL);
                assert(!Read(BEAT,static_cast<const char* const*>(nullptr),0,reward)&&!reward.Enabled());
                for(const char* bad:{"arrows:0","arrows:-6","arrows:06","arrows:6.0","arrows:13","arrows","ARROWS:6"}) {
                    const char* changed[]={bad};
                    assert(!Read(BEAT,changed,1,reward)&&!reward.Enabled());
                }
                const char* duplicate[]={TOKEN,TOKEN};
                assert(!Read(BEAT,duplicate,2,reward)&&!reward.Enabled());
                const char* extra[]={TOKEN,"arrows:4"};
                assert(!Read(BEAT,extra,2,reward)&&!reward.Enabled());
                const char* respelled[]={TOKEN,"ARROWS:6"};
                assert(!Read(BEAT,respelled,2,reward)&&!reward.Enabled());
                const char16_t* wide[]={uTOKEN};
                assert(Read(uBEAT,wide,1,reward)&&reward.Amount==AMOUNT&&reward.Refill==REFILL);
            }""".replace("TOKENS", ",".join(map(json.dumps, tokens)))
                        .replace("COUNT", str(len(tokens))).replace("AMOUNT", str(amount))
                        .replace("REFILL", str(refill).lower()).replace("BEAT", json.dumps(beat))
                        .replace("TOKEN", json.dumps(token)))
        self.run_native("""
#include "SoraCacheRewardRules.h"
#include <cassert>
#include <initializer_list>
int main() {
    using namespace SoraCacheRewardRules;
    ROWS
    assert(!Find("ch01.b08")&&!Find("ch08.b12")); // unchanged wood and gallery paths
    assert(!Find("ch06.b07extra")&&!Find(static_cast<const char*>(nullptr)));
}
""".replace("ROWS", "\n".join(rows)))

    def test_native_add_refill_caps_entitlement_and_held_authority(self):
        self.run_native(r'''
#include "SoraCacheRewardRules.h"
#include "SoraSupplyRules.h"
#include <array>
#include <cassert>
#include <climits>
int main() {
    constexpr int Bow=18,Count=21;
    // The wider synthetic cap distinguishes add from refill: 8+6 is 14,
    // whereas refill-to-12 is 12. Production remains a twelve-arrow quiver.
    for(const int cap:{12,20}) for(const int held:{0,Bow}) for(int before=0;before<=cap;++before)
    for(const auto& contract:SoraCacheRewardRules::Contracts) {
        std::array<int,Count> stored,caps{}; stored.fill(37); caps[Bow]=cap;
        stored[Bow]=held==Bow?cap:before; int live=held==Bow?before:9;
        const auto initial=stored; const int oldLive=live;
        const int wanted=contract.Arrows.Refill?(before<contract.Arrows.Amount?contract.Arrows.Amount-before:0):contract.Arrows.Amount;
        const int expected=wanted<cap-before?wanted:cap-before;
        assert(SoraSupplyRules::AddAmmo(stored.data(),caps.data(),Count,1u<<Bow,held,live,Bow,
            contract.Arrows.Amount,contract.Arrows.Refill)==expected);
        for(int n=0;n<Count;++n) assert(stored[n]==(n==Bow?before+expected:initial[n]));
        assert(live==(held==Bow?before+expected:oldLive));
    }
    for(bool refill:{false,true}) for(int amount:{6,12,INT_MAX}) {
        std::array<int,Count> stored{},caps{}; caps[Bow]=12; stored[Bow]=4; int live=7;
        const auto initial=stored;
        assert(SoraSupplyRules::AddAmmo(stored.data(),caps.data(),Count,0,0,live,Bow,amount,refill)==-1);
        assert(stored==initial&&live==7); // no pre-unlock entitlement or consumption
        for(int bad:{-1,13}) {
            live=bad;
            assert(SoraSupplyRules::AddAmmo(stored.data(),caps.data(),Count,1u<<Bow,Bow,live,Bow,amount,refill)==-1);
            assert(stored==initial&&live==bad);
        }
    }
}
''')

    def test_native_claim_uses_existing_saved_find_state(self):
        masks = []
        for chapter_index, chapter in enumerate(chapters()):
            for beat in chapter["beats"]:
                if beat["id"] not in EXPECTED:
                    continue
                mask = sum(1 << (chapter_index * 6 + item["mask_bit"])
                           for item in chapter["collectibles"] if item["id"] in beat["params"]["rewards"])
                masks.append(mask)
        self.run_native(r'''
#include "SoraCacheRewardRules.h"
#include <cassert>
int main() {
    using SoraCacheRewardRules::Unclaimed;
    constexpr unsigned long long masks[]={MASKS};
    for(auto finds:masks) {
        assert(Unclaimed(finds,0));
        // Completion, retry, fresh load and chapter replay all read the same
        // persisted codex bits. Full inventory also exhausts the cache.
        assert(!Unclaimed(finds,finds));
        for(int bit=0;bit<48;++bit) {
            const auto saved=1ull<<bit;
            assert(Unclaimed(finds,saved)==((finds&saved)==0));
        }
        for(auto unrelated:masks) if(unrelated!=finds) assert(Unclaimed(finds,unrelated));
    }
    assert(!Unclaimed(0,0));
}
'''.replace("MASKS", ",".join(f"{mask}ull" for mask in masks)))

    def test_actual_director_claim_refuses_without_consuming_or_granting(self):
        source = (ROOT / "Source/SoraArena/Private/Game/SoraCampaignSupply.cpp").read_text()
        begin = source.index("bool USoraCampaignDirector::ClaimCacheArrows(")
        end = source.index("void USoraCampaignDirector::TickSupplyHint", begin)
        # Execute the actual production claim body with minimal host objects.
        # Save persistence and mapped input remain the editor fixture's work.
        self.run_native(r'''
#include "SoraCacheRewardRules.h"
#include "SoraCampaignRules.h"
#include "SoraSupplyRules.h"
#include <array>
#include <cassert>
#include <vector>
using int32=int;
template<class T> struct Rows:std::vector<T> {
    using std::vector<T>::vector;
    bool IsValidIndex(int n) const {return n>=0&&n<int(this->size());}
};
struct Cache { SoraCacheRewardRules::FArrows CacheArrows; Rows<int> Rewards; };
struct Find {int MaskBit;};
struct Chapter {Rows<Cache> Beats; Rows<Find> Collectibles;};
struct Equipment {
    std::array<int,21> Stored{},Caps{}; int Held=18,Ammo=2; bool Busy=false;
    int GrantArrows(int amount,unsigned weapons,bool refill) {
        return Busy?-1:SoraSupplyRules::AddAmmo(Stored.data(),Caps.data(),21,weapons,Held,Ammo,18,amount,refill);
    }
};
struct Hero {Equipment Kit; Equipment* GetEquipment(){return &Kit;}};
struct ModeState {struct Hero* Player=nullptr; struct Hero* Hero(){return Player;}};
struct USoraCampaignDirector {
    void* Save=this; Chapter Data; bool HaveChapter=true,Unlocked=true;
    int ChapterId=1; unsigned long long Collected=0; ModeState World;
    Chapter* ActiveChapter(){return HaveChapter?&Data:nullptr;}
    unsigned long long CollectedMask(){return Collected;}
    bool IsWeaponUnlocked(int id){assert(id==18); return Unlocked;}
    ModeState& Mode(){return World;}
    bool ClaimCacheArrows(int32 Index);
};
BODY
int main() {
    for(const auto& contract:SoraCacheRewardRules::Contracts) {
        USoraCampaignDirector d; Hero hero; d.World.Player=&hero;
        d.Data.Beats.push_back({contract.Arrows,{0,1}});
        d.Data.Collectibles={{0},{2}};
        auto& kit=hero.Kit; kit.Stored.fill(37); kit.Stored[18]=12; kit.Caps[18]=12;
        const auto inventory=kit.Stored;
        for(int refusal=0;refusal<4;++refusal) {
            d.Save=refusal==0?nullptr:&d;
            d.HaveChapter=refusal!=1; d.Unlocked=refusal!=2; kit.Busy=refusal==3;
            assert(!d.ClaimCacheArrows(0));
            assert(kit.Ammo==2&&kit.Stored==inventory&&d.Collected==0);
        }
        d.Save=&d; d.HaveChapter=true; d.Unlocked=true; kit.Busy=false;
        assert(!d.ClaimCacheArrows(-1)&&!d.ClaimCacheArrows(1));
        assert(d.ClaimCacheArrows(0));
        const int expected=contract.Arrows.Refill?12:2+contract.Arrows.Amount<12?2+contract.Arrows.Amount:12;
        assert(kit.Ammo==expected&&kit.Stored[18]==expected&&d.Collected==0);
        // CompleteOptional collects these exact finds immediately after the
        // successful return. The claim itself never invents a second ledger.
        d.Collected=(1ull<<6)|(1ull<<8); kit.Ammo=1;
        assert(d.ClaimCacheArrows(0)&&kit.Ammo==1);
        kit.Busy=true;
        assert(d.ClaimCacheArrows(0)&&kit.Ammo==1);
        for(int n=0;n<21;++n) if(n!=18) assert(kit.Stored[n]==inventory[n]);
    }
}
'''.replace("BODY", source[begin:end]))


if __name__ == "__main__":
    unittest.main()
