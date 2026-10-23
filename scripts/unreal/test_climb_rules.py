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
#include <algorithm>
using namespace SoraClimbRules;
using namespace SoraFieldcraftRules;
/* ROUTE_POINTS */
double CapsuleRectDistance2(FPathPoint feet,double left,double right,double bottom,double top) {
    const double dx=std::max({left-feet.X,0.0,feet.X-right});
    const double dz=std::max({bottom-(feet.Z+142),0.0,feet.Z+34-top});
    return dx*dx+dz*dz; // radius34; vertical capsule segment centres feet+34..142.
}
double CapsuleShelfDistance2(FPathPoint feet,FPathPoint shelf) {
    return CapsuleRectDistance2(feet,shelf.X-130,shelf.X+130,shelf.Z-20,shelf.Z);
}
double Distance(FPathPoint a,FPathPoint b) {
    return std::sqrt((a.X-b.X)*(a.X-b.X)+(a.Y-b.Y)*(a.Y-b.Y)+(a.Z-b.Z)*(a.Z-b.Z));
}
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
    static_assert(GuideRoofHeight==2400 && GuideSpeed>0 && GuideSpeed<420);
    static_assert(SupportLiftCm>3); // guide may advance at <=3 cm actual proximity.
    for(unsigned i=0;i<sizeof(GuideRoofPath)/sizeof(*GuideRoofPath);++i) {
        const auto p=GuideRoofPath[i];
        assert(p.Z>=1600+SupportLiftCm && p.Z<=GuideRoofHeight+SupportLiftCm);
        // Before the final roof mount, the capsule stays outside the
        // colliding turret front at x1100, including its 34 cm radius.
        if(p.Z<GuideRoofHeight) assert(p.X+34<1100);
        if(i) {
            const auto previous=GuideRoofPath[i-1];
            // Only the last, vertical support-settle leg goes downward.
            if(p.Z<previous.Z) assert(p.X==previous.X && p.Y==previous.Y && p.Z==GuideRoofHeight);
            for(int sample=0;sample<=4096;++sample) {
                const auto at=Mix({double(previous.X),double(previous.Y),double(previous.Z)},
                    {double(p.X),double(p.Y),double(p.Z)},sample/4096.0);
                assert(CapsuleRectDistance2(at,1100,2100,2360,2400)>=34*34-1e-7);
            }
            if(p.X>previous.X && p.Z==GuideRoofHeight+SupportLiftCm)
                assert(CapsuleRectDistance2({1200,500,double(p.Z)},1100,2100,2360,2400)==(34+SupportLiftCm)*(34+SupportLiftCm));
        }
    }
    const auto roof=GuideRoofPath[sizeof(GuideRoofPath)/sizeof(*GuideRoofPath)-1];
    assert(roof.X>1100+34 && roof.X<2100-34 && roof.Y>-800+34 && roof.Y<700-34 && roof.Z==2400);
    // The previous straight approach really intersects the lower shelf.
    const auto old=HoldPath(Route[3],Route[4],6629.0/18989,EHoldPath::Direct);
    assert(CapsuleShelfDistance2(old,Route[5])<34*34);
    for(int from=0;from<15;++from) for(int direction:{-1,1}) {
        const int to=from+direction;if(to<0||to>=15) continue;
        const auto rest=[](int h) { return h==5||h==9; };
        EHoldPath path=EHoldPath::Direct;
        if(direction>0&&rest(to)) path=EHoldPath::OntoRest;
        else if(direction<0&&rest(from)) path=EHoldPath::OffRest;
        else if(direction>0&&rest(to+1)) path=EHoldPath::BeforeRest;
        else if(direction<0&&rest(from+1)) path=EHoldPath::FromBeforeRest;
        // Sample the production interpolation densely, including both
        // directions and all actual generated coordinates, not just endpoints.
        for(int sample=0;sample<=4096;++sample) {
            const auto at=HoldPath(Route[from],Route[to],sample/4096.0,path);
            for(int shelf:{5,9}) assert(CapsuleShelfDistance2(at,Route[shelf])>=34*34-1e-7);
            if(sample) {
                const auto previous=HoldPath(Route[from],Route[to],(sample-1)/4096.0,path);
                assert(Distance(at,previous)<=600*1.8/4096+1e-7);
            }
        }
    }
    for(int rest:{5,9}) {
        // Regression: crossing at the authored support plane is exactly
        // tangent (the real UE capsule stopped on the shelf side at time0).
        const FPathPoint edge{Route[rest].X-130,Route[rest].Y,Route[rest].Z};
        assert(CapsuleShelfDistance2(edge,Route[rest])==34*34);
        for(int sample=0;sample<=4096;++sample) {
            const double t=sample/4096.0;
            const auto onto=HoldPath(Route[rest-1],Route[rest],.7+.2*t,EHoldPath::OntoRest);
            const auto off=HoldPath(Route[rest],Route[rest-1],.1+.2*t,EHoldPath::OffRest);
            assert(CapsuleShelfDistance2(onto,Route[rest])>=(34+SupportLiftCm)*(34+SupportLiftCm)-1e-7);
            assert(CapsuleShelfDistance2(off,Route[rest])>=(34+SupportLiftCm)*(34+SupportLiftCm)-1e-7);
            // Exact reverse motion keeps input reversal on the same safe path.
            const auto reverse=HoldPath(Route[rest],Route[rest-1],1-t,EHoldPath::OffRest);
            const auto forward=HoldPath(Route[rest-1],Route[rest],t,EHoldPath::OntoRest);
            assert(Distance(reverse,forward)<1e-7);
        }
    }
    const FPathPoint mountFrom=Route[14],mountTo{650,mountFrom.Y,1600};
    assert(CapsuleRectDistance2({500,mountFrom.Y,1600},500,1200,1560,1600)==34*34);
    for(int sample=0;sample<=4096;++sample) {
        const double t=sample/4096.0;
        const auto at=HoldPath(mountFrom,mountTo,t,EHoldPath::Mount);
        assert(CapsuleRectDistance2(at,500,1200,1560,1600)>=34*34-1e-7);
        if(t>=.15 && t<=.85)
            assert(CapsuleRectDistance2(at,500,1200,1560,1600)>=(34+SupportLiftCm)*(34+SupportLiftCm)-1e-7);
        if(sample) assert(Distance(at,HoldPath(mountFrom,mountTo,(sample-1)/4096.0,EHoldPath::Mount))<=600*1.8/4096+1e-7);
    }
    assert(Distance(HoldPath(mountFrom,mountTo,0,EHoldPath::Mount),mountFrom)<1e-7);
    assert(Distance(HoldPath(mountFrom,mountTo,1,EHoldPath::Mount),mountTo)<1e-7);
    assert(AtSupport(false,1,1,0,2.2));
    assert(!AtSupport(false,-1,1,0,0) && !AtSupport(false,0,1,.1,1));
    // Actual side contacts had a near-upward capsule normal but a -X face
    // impact normal. Even a tiny residual must not classify those as support.
    assert(!AtSupport(false,1,0,.1,.02));
    assert(!AtSupport(true,1,1,0,0) && !AtSupport(false,1,1,.251,1));
    assert(!AtSupport(false,1,1,0,-.001) && !AtSupport(false,1,1,0,3.001));
    // Release onto the real shelf is harmless. It must not disable a later
    // supported->airborne->landing transition or charge height twice.
    FFall fall=FallAt(550);
    assert(SampleFall(fall,550,false,false,true)==0);
    assert(SampleFall(fall,552.15,false,true,false)==0 && !fall.Airborne);
    assert(SampleFall(fall,552.15,false,true,false)==0);
    assert(SampleFall(fall,549,false,false,true)==0 && fall.Airborne);
    assert(SampleFall(fall,200,false,false,true)==0);
    const int lowerDrop=SampleFall(fall,2.15,false,true,false);
    assert(lowerDrop==550 && FallDamage(GripRules(false),lowerDrop)==30 && !fall.Airborne);
    assert(SampleFall(fall,2.15,false,true,false)==0);
    // A real intermediate shelf ends that fall: two 5.5m falls are not one
    // 11m fall. A clear drop to the terrace is, and must be lethal.
    fall=FallAt(1102.15);
    SampleFall(fall,1090,false,false,true);
    assert(SampleFall(fall,552.15,false,true,false)==550);
    SampleFall(fall,540,false,false,true);
    assert(SampleFall(fall,2.15,false,true,false)==550);
    fall=FallAt(1102.15);
    SampleFall(fall,1090,false,false,true);
    SampleFall(fall,550,false,false,true);
    const int upperDrop=SampleFall(fall,2.15,false,true,false);
    assert(upperDrop==1100 && FallDamage(GripRules(false),upperDrop)<0);
    // Grounded crouch changes body height, not feet height. A genuine jump
    // records its physical apex; acquiring holds/reset discards old peaks.
    fall=FallAt(552.15);
    assert(SampleFall(fall,552.15,false,true,false)==0);
    SampleFall(fall,600,false,false,true);SampleFall(fall,580,false,false,true);
    assert(SampleFall(fall,552.15,false,true,false)==48);
    SampleFall(fall,500,false,false,true);
    assert(SampleFall(fall,440,true,false,false)==0 && !fall.Airborne && fall.PeakZ==440);
    fall={};assert(SampleFall(fall,2.15,false,true,false)==0 && !fall.Airborne);
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
        points = self.chapter["space"]["beats"][2]["climb_routes"]["corner"]["points_cm"]
        source = source.replace("/* ROUTE_POINTS */", "constexpr FPathPoint Route[]={" +
                                ",".join("{" + ",".join(map(str, point)) + "}" for point in points) + "};")
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
