"""Host data/rules checks. Sweeps, sentry sight and the crawl need UE fixtures."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from campaign_climb import climb_valid

ROOT = Path(__file__).resolve().parents[2]


class ClimbTests(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT / "Content/Data/campaign/chapter_06.json").read_text())

    def rejected(self, mutate):
        chapter = copy.deepcopy(self.chapter)
        mutate(chapter)
        self.assertFalse(climb_valid(chapter))

    def test_authored_routes_ledges_crawl_and_sentry(self):
        self.assertTrue(climb_valid(self.chapter))
        route = self.chapter["space"]["beats"][2]["climb_routes"]
        corner, extrusion = route["corner"], route["extrusion"]
        self.assertEqual(len(corner["points_cm"]) - 1, 14)
        self.assertEqual(len(extrusion["points_cm"]) - 1, 8)
        self.assertEqual([corner["points_cm"][i][2] for i in corner["rest_holds"]], [550, 1100])
        for approach, rest in ((4, 5), (8, 9)):
            # Shelf lip extends 130 cm; capsule radius34 plus a clear margin
            # must fit before raising outside the shelf, then moving inward.
            self.assertEqual(corner["points_cm"][rest][0] - corner["points_cm"][approach][0], 210)
            self.assertGreater(210 - 130, 34)
        self.assertEqual(extrusion["rest_holds"], [])
        self.assertTrue(extrusion["exposed"])
        self.assertFalse(corner["exposed"])
        self.assertEqual(route["lookdown"], {"period_ms": 20000, "hold_ms": 4000, "guard_index": 0})
        self.assertEqual(route["crawl"]["height_cm"], 60)
        self.assertEqual(route["crawl"]["floor_cm"], 1650)
        self.assertLess(8 * extrusion["step_ms"], 14 * corner["step_ms"])
        for path in (corner, extrusion):
            self.assertEqual(path["points_cm"][0][2], 0)
            self.assertEqual(path["points_cm"][-1][2], 1600)
            self.assertTrue(all(a[2] < b[2] for a, b in zip(path["points_cm"], path["points_cm"][1:])))

    def test_absent_duplicate_misplaced_or_mistyped_contract_rejected(self):
        self.rejected(lambda c: c["space"]["beats"][2].pop("climb_routes"))
        self.rejected(lambda c: c["space"]["beats"][1].update(climb_routes=c["space"]["beats"][2]["climb_routes"]))
        self.rejected(lambda c: c["space"]["beats"].pop())
        self.rejected(lambda c: c["space"]["beats"][2].update(zone=-1))
        for value in (None, True, False, [], "1600", 1600.0):
            with self.subTest(value=value):
                self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"].update(height_cm=value))
        self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"].update(extra=True))
        self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"].update(provisional_geometry=1))
        self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"]["origin"].__setitem__(1, False))
        self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"]["origin"].__setitem__(0, 2**40))

    def test_route_shortcuts_and_ledge_moves_rejected(self):
        for name in ("corner", "extrusion"):
            self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"][name]["points_cm"].pop(1))
            self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"][name]["points_cm"][1].__setitem__(2, 1600))
            self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"][name]["points_cm"][0].__setitem__(0, True))
            self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"][name].update(step_ms=1))
        self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"]["corner"].update(rest_holds=[4, 9]))
        self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"]["corner"]["points_cm"][5].__setitem__(2, 549))
        self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"]["corner"]["points_cm"][4].__setitem__(0, 184))
        self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"]["corner"]["points_cm"][8].__setitem__(0, 340))
        self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"]["extrusion"].update(rest_holds=[3]))
        self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"]["extrusion"].update(exposed=False))

    def test_sentry_crawl_exit_and_companion_changes_rejected(self):
        for key, value in (("period_ms", 24000), ("hold_ms", 0), ("guard_index", 1)):
            self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"]["lookdown"].update({key: value}))
        for key in ("floor_cm", "height_cm", "half_width_cm", "entry_x_cm", "exit_x_cm"):
            self.rejected(lambda c: c["space"]["beats"][2]["climb_routes"]["crawl"].update({key: 0}))
        self.rejected(lambda c: c["space"]["beats"][2]["exit"].update(floor_cm=0))
        self.rejected(lambda c: c["space"]["beats"][2]["spawns"][0].__setitem__(1, 0))
        self.rejected(lambda c: c["space"]["beats"][2]["fieldcraft"]["allies"][0].update(detectable=True))
        self.rejected(lambda c: c["space"]["beats"][2]["fieldcraft"]["lamps"][0].update(snuff="hold"))
        self.rejected(lambda c: c["beats"][2]["params"]["guards"][0]["lookdown"].update(every_s=10))
        self.rejected(lambda c: c["beats"][2]["task"]["guards"][0].update(sight_cm=0))
        self.rejected(lambda c: c["beats"][2]["ext"]["traversal"].update(alt_holds=14))

    def test_generated_chapter_matches_and_retains_flood(self):
        from build_campaign_data import build_chapter, encode, load_places
        from campaign_flood import flood_valid
        self.assertEqual(encode(build_chapter(6, load_places())),
                         (ROOT / "Content/Data/campaign/chapter_06.json").read_bytes())
        self.assertTrue(flood_valid(self.chapter))

    def test_actual_cpp_grip_falls_and_sentry_boundaries(self):
        source = r'''
#include "SoraClimbRules.h"
#include <cassert>
#include <cmath>
#include <initializer_list>
using namespace SoraClimbRules;
using namespace SoraFieldcraftRules;
int main() {
    static_assert(Height==1600 && CornerZ[5]==550 && CornerZ[9]==1100);
    static_assert(sizeof(CornerZ)/sizeof(*CornerZ)==15 && sizeof(ExtrusionZ)/sizeof(*ExtrusionZ)==9);
    static_assert(CrawlHeight==60 && 2*CrawlHalfHeight==56 && 2*CrawlRadius==56);
    static_assert(CrawlEntry<CrawlExit && CrawlFloor==1650);
    static_assert(!Watching(-1) && !Watching(0) && !Watching(19999));
    static_assert(Watching(20000) && Watching(23999) && !Watching(24000));
    static_assert(!Watching(39999) && Watching(40000) && Watching(43999) && !Watching(44000));
    assert(std::abs(WallX(600)-600/std::sqrt(3.0))<1e-8);
    // The real patrol follows connected deck segments, reaches the authored
    // far end, and returns to the bay at each exact look-down boundary.
    for(int t=0;t<60000;++t) {
        const auto p=PatrolAt(t), next=PatrolAt(t+1);
        assert(p.X>=360 && p.X<=650 && p.Y>=-3800 && p.Y<=-300);
        assert(std::abs(p.Y+300)<1e-8 || std::abs(p.X-650)<1e-8);
        assert(std::hypot(next.X-p.X,next.Y-p.Y)<=.4741);
        if(Watching(t)) assert(p.X==360 && p.Y==-300);
    }
    assert(PatrolAt(10000).Y==-3800 && PatrolAt(32000).Y==-3800);
    for(bool extrusion:{false,true}) {
        const auto rules=GripRules(extrusion);
        assert(ClimbValid(rules));
        assert(rules.Holds==(extrusion?8:14));
        auto climb=StartClimb();
        for(int hold=1;hold<=rules.Holds;++hold) {
            const auto result=Reach(climb,rules,1);
            assert(result==(hold==rules.Holds?EReach::Top:EReach::Moved));
        }
        assert(climb.GripMilli==100000-rules.Holds*6000);
        assert(FallDamage(rules,400)==0 && FallDamage(rules,401)==30);
        assert(FallDamage(rules,800)==30 && FallDamage(rules,801)==-1);
    }
    for(int dt:{1,8,16,17,33,50}) {
        FClimb rest{5,50000};int elapsed=0;
        while(elapsed<1000) { const int n=dt<1000-elapsed?dt:1000-elapsed;Rest(rest,GripRules(false),n);elapsed+=n; }
        assert(rest.GripMilli==75000);
        FClimb ordinary{4,50000};Rest(ordinary,GripRules(false),1000);assert(ordinary.GripMilli==50000);
        FClimb exposed{5,50000};Rest(exposed,GripRules(true),1000);assert(exposed.GripMilli==50000);
    }
}
'''
        compiler = os.environ.get("CXX") or shutil.which("clang++") or shutil.which("c++")
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory(prefix="sora-climb-rules-") as directory:
            cpp, binary = Path(directory) / "climb.cpp", Path(directory) / "climb"
            cpp.write_text(source)
            subprocess.run([compiler, "-std=c++17", "-UNDEBUG", "-O2", "-Wall", "-Wextra", "-Werror",
                            "-fsanitize=undefined", "-fsanitize-trap=undefined", "-I", str(ROOT / "Source/SoraArena/Public"),
                            str(cpp), "-o", str(binary)], check=True, capture_output=True, text=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
