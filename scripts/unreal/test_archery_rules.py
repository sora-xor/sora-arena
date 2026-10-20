"""The dojo range counts real resolved arrows, with finite/recoverable sets."""
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ArcheryRulesTests(unittest.TestCase):
    def test_authored_contract_and_clear_range(self):
        chapter = json.loads((ROOT / "Content/Data/campaign/chapter_01.json").read_text())
        beat = chapter["beats"][6]
        self.assertEqual(beat["params"]["target_kind"], "mato")
        self.assertEqual(beat["ext"]["mato_rules"], {
            "distance_m": 28, "target_cm": 36, "shots_per_set": 6, "hits_required": 4,
            "hit_collider_radius_cm": {"easy": 25, "normal": 21, "hard": 18},
            "between_sets": "yatori_arrow_fetch_8s", "ammo": "own_quiver_12"})
        self.assertEqual(beat["ext"]["tsuri"], {
            "distances_m": [40, 50, 60], "hits_each": 1, "swing_amplitude_cm": 150,
            "period_s": 3.2, "target_cm": 45})
        self.assertEqual(beat["ext"]["quiver_after"]["usable"], 6)
        self.assertEqual(beat["ext"]["quiver_after"]["bent"], 6)
        self.assertEqual(chapter["beats"][8]["ext"]["quiver_after"], {"usable": 12})
        self.assertTrue(beat["checkpoint"])
        self.assertEqual(beat["unlocks"]["weapons"], [18])
        self.assertEqual(beat["ext"]["unlock_at"], "beat_start")
        space = chapter["space"]["beats"][6]
        zone = chapter["space"]["zones"][space["zone"]]
        x, y = space["entry"][:2]
        line = x + 420, y
        # Whole circles, swings and the standing capsule fit the existing
        # zone; no aim corridor intersects the old side crates or NPCs.
        for distance, offset in [(2800, 0), (4000, -600), (5000, 0), (6000, 600)]:
            downrange = math.sqrt(distance**2 - offset**2)
            target = line[0] + downrange, line[1] + offset
            self.assertAlmostEqual(math.hypot(downrange, offset), distance)
            self.assertLess(target[0] + 25, zone["rect"][2])
            self.assertGreater(target[1] - 175, zone["rect"][1])
            self.assertLess(target[1] + 175, zone["rect"][3])
            for cx, cy, sx, sy, _ in zone["cover"]:
                if line[0] <= cx <= target[0]:
                    t = (cx - line[0]) / downrange
                    ray_y = line[1] + offset * t
                    self.assertGreater(abs(cy - ray_y), sy / 2 + 150 + 25)
        for npc in space["fieldcraft"]["allies"]:
            self.assertLess(npc["at"][0] + 45, line[0] - 34)
        catalog = json.loads((ROOT / "Content/Data/catalog.json").read_text())
        bow = (catalog["weapons"] + catalog["campaign_weapons"])[18]
        self.assertEqual(bow["magazine"], 12)
        self.assertEqual(bow["projectile_speed"], 6500)

    def test_resolved_sets_all_orders_and_recovery_boundaries(self):
        source = r'''
#include "SoraArcheryRules.h"
#include <algorithm>
#include <array>
#include <cassert>
#include <climits>
using namespace SoraArcheryRules;
int main() {
    // Every six-shot hit pattern and every resolution order has the same
    // outcome. A first fourth hit never skips unresolved fifth/sixth arrows.
    for(unsigned mask=0;mask<64;++mask) {
        std::array<int,6> order{0,1,2,3,4,5};
        do {
            FState s; int hits=0;
            for(int n=0;n<6;++n) { assert(Issue(s,n+1,true)); hits+=(mask>>n)&1; }
            assert(!Issue(s,7,true)&&!CanLoose(s));
            for(int n=0;n<6;++n) {
                int shot=order[n]; auto result=Resolve(s,shot+1,(mask&(1u<<shot))?0:-1);
                assert(result!=EResult::Ignored);
                assert(s.LastHit==bool(mask&(1u<<shot)));
                const auto copy=s;
                assert(Resolve(s,shot+1,0)==EResult::Ignored);
                assert(s.Hits==copy.Hits&&s.Resolved==copy.Resolved&&s.Stage==copy.Stage);
                if(n<5) assert(s.Stage==EStage::Near&&s.FetchRemainingMs==0);
            }
            assert(Pending(s)==0);
            assert(hits>=4?(s.Stage==EStage::Hanging&&s.FetchRemainingMs==0):
                (s.Stage==EStage::Near&&s.FetchRemainingMs==8000));
        } while(std::next_permutation(order.begin(),order.end()));
    }
    for(int frame:{1,16,17,33,100,500}) {
        FState s;
        for(int n=1;n<=6;++n) { assert(Issue(s,n,false)); Resolve(s,n,0); }
        assert(s.Hits==0&&s.FetchRemainingMs==8000); // Outside-line hits are misses.
        assert(!Issue(s,7,true)&&!TickFetch(s,0)&&!TickFetch(s,-1));
        int elapsed=0;
        while(elapsed+frame<8000) { assert(!TickFetch(s,frame)); elapsed+=frame; }
        assert(TickFetch(s,8000-elapsed)&&s.Resolved==0&&s.Hits==0&&CanLoose(s));
        assert(!TickFetch(s,INT_MAX));
        assert(Resolve(s,1,0)==EResult::Ignored); // Previous set remains invalid.
        for(int n=7;n<=12;++n) { assert(Issue(s,n,true)); Resolve(s,n,n<=10?0:-1); }
        assert(s.Stage==EStage::Hanging);
        assert(Issue(s,13,true)&&Resolve(s,13,1)==EResult::Hit&&s.HangingHits==1);
        assert(Issue(s,14,true)&&Resolve(s,14,1)==EResult::Miss&&s.HangingHits==1);
        assert(!FetchExhausted(s,1));
        assert(Issue(s,15,true)&&!FetchExhausted(s,0)); // Await flying last arrow.
        assert(Resolve(s,15,-1)==EResult::Miss&&FetchExhausted(s,0));
        assert(!FetchExhausted(s,0)&&s.HangingHits==1&&!CanLoose(s));
        assert(TickFetch(s,8000)&&s.HangingHits==1&&CanLoose(s));
        assert(Issue(s,16,true)&&Resolve(s,16,2)==EResult::Hit);
        assert(Issue(s,17,true)&&Resolve(s,17,3)==EResult::Complete);
        assert(s.HangingHits==7&&!CanLoose(s)&&!FetchExhausted(s,0));
    }
    FState empty;
    assert(!Issue(empty,0,true)&&Resolve(empty,0,0)==EResult::Ignored);
    assert(Issue(empty,1,true)&&!Issue(empty,1,true));
    assert(Resolve(empty,2,0)==EResult::Ignored&&Pending(empty)==1);
    assert(Bent(0)==0&&Usable(0)==12);
    assert(Bent(1u<<6)==6&&Usable(1u<<6)==6);
    assert(Bent((1u<<6)|(1u<<8))==0&&Usable((1u<<6)|(1u<<8))==12);
}
'''
        compiler = os.environ.get("CXX") or shutil.which("clang++") or shutil.which("c++")
        self.assertIsNotNone(compiler, "Host C++ compiler is required")
        with tempfile.TemporaryDirectory() as tmp:
            cpp, binary = Path(tmp) / "archery.cpp", Path(tmp) / "archery"
            cpp.write_text(source)
            subprocess.run([compiler, "-std=c++17", "-I", str(ROOT / "Source/SoraArena/Public"),
                            str(cpp), "-o", str(binary)], check=True, capture_output=True, text=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
