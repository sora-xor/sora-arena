"""Physical lift contract, generated heights and frame-independent work/motion."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from build_campaign_data import BuildError, fail
from campaign_lift import place_lift

ROOT = Path(__file__).resolve().parents[2]


class LiftDataTests(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT / "Content/Data/campaign/chapter_08.json").read_text())

    def test_landing_gantry_gallery_contract(self):
        lift, gallery = self.chapter["space"]["beats"][10:12]
        x, y = lift["anchor"]
        self.assertEqual(lift["height_cm"], 2700)
        self.assertEqual(lift["entry"], [x - 650, y, 0])
        self.assertEqual(lift["lift"], {
            "size_cm": [600, 600], "bottom_cm": 2700, "top_cm": 14200,
            "gantry_cm": [5575, 8450, 11325],
            "gallery_rect": [x + 300, y - 2000, x + 1300, y + 2000],
            "gallery_exit": [x + 800, y + 1800]})
        self.assertEqual(lift["spawns"], [[x + 650, y + offset] for offset in (-150, 0, 150)])
        self.assertEqual(gallery["height_cm"], 14200)
        self.assertEqual(gallery["cache"], [x + 800, y - 1400])
        self.assertEqual(gallery["exit"]["center"], lift["lift"]["gallery_exit"])
        self.assertEqual(self.chapter["beats"][11]["requires"], ["ch08.b11"])
        for person in lift["fieldcraft"]["people"]:
            self.assertLess(abs(person["at"][0] - x) + 34, 284)
            self.assertLess(abs(person["at"][1] - y) + 34, 284)

    def test_generated_contract_is_deterministic_and_scoped(self):
        for path in sorted((ROOT / "Content/Data/campaign").glob("chapter_*.json")):
            chapter = json.loads(path.read_text())
            records = deepcopy(chapter["space"]["beats"])
            place_lift(chapter["beats"], records, fail)
            self.assertEqual(records, chapter["space"]["beats"])
            for record in records:
                if record["beat"] not in ("ch08.b11", "ch08.b12"):
                    self.assertEqual(record["height_cm"], 0)
                    self.assertIsNone(record["lift"])

    def test_changed_platform_or_unreachable_wave_contract_fails_closed(self):
        for key, value in (("travel_cm", 10000), ("size_cm", [600, 500]), ("from", "L3"), ("to", "ground")):
            beats = deepcopy(self.chapter["beats"])
            beats[10]["params"]["crank"]["moving_platform"][key] = value
            with self.subTest(key=key), self.assertRaises(BuildError):
                place_lift(beats, deepcopy(self.chapter["space"]["beats"]), fail)
        for key, value in (("spawn", "sp_lift_gantry_100m"), ("behavior", "teleport"), ("count", 4)):
            beats = deepcopy(self.chapter["beats"])
            beats[10]["params"]["waves"][2]["enemies"][0][key] = value
            with self.subTest(key=key), self.assertRaises(BuildError):
                place_lift(beats, deepcopy(self.chapter["space"]["beats"]), fail)

    def test_cpp_motion_and_live_contact_decay(self):
        compiler = os.environ.get("CXX") or shutil.which("clang++") or shutil.which("g++")
        self.assertIsNotNone(compiler, "a host C++ compiler is required")
        code = r'''
#include "SoraLiftRules.h"
#include "SoraBeatRules.h"
#include <cassert>
#include <cmath>
int main() {
    using namespace SoraLiftRules;
    static_assert(Height(0,48000)==2700 && Height(48000,48000)==14200);
    static_assert(Height(-10,48000)==2700 && Height(49000,48000)==14200);
    static_assert(Gantry(1)==5575 && Gantry(2)==8450 && Gantry(3)==11325);
    static_assert(Speed(0,1000)==0 && Speed(48,0)==0);
    for (double dt : {1./120,1./60,1./30,.1,.5}) {
        double z=BottomCm;
        for(int frame=0;frame<10000&&!At(z,TopCm);++frame) {
            double before=z; z=Advance(z,TopCm,Speed(48,1000),dt);
            assert(z>=before && z<=TopCm && z-before<=Speed(48,1000)*dt+.0001);
        }
        assert(At(z,TopCm));
        z=Advance(z,TopCm-10,Speed(48,1000),1.);
        assert(At(z,TopCm-10));
        assert(Advance(z,BottomCm,Speed(48,1000),-1)==z);
    }
    using namespace SoraBeatRules;
    FTask t; t.Type=EType::ProductionTask; t.Task=ETask::Crank; t.Goal=EGoal::Turns;
    t.Count=48; t.MinTurnMs=1000; t.MaxTurnMs=2500; t.DecayPermille=10;
    t.CoopCount=3; t.CoopMilliTurnsS=150; t.CoopProgressPermille=1000;
    for(int frameMs : {1,16,17,33,100,500}) for(int helpers=0;helpers<=3;++helpers) {
        FTaskState normal=StartTask(t,0),contact=normal;
        normal.Progress=contact.Progress=24000;
        normal.LastActionMs=contact.LastActionMs=0;
        normal.ElapsedMs=contact.ElapsedMs=10000;
        for(int elapsed=0;elapsed<10000;) {
            int dt=frameMs<10000-elapsed?frameMs:10000-elapsed;
            FTick step; step.DeltaMs=dt; step.CrankHelpers=helpers;
            Tick(normal,t,step); step.CrankDecayMultiplier=3; Tick(contact,t,step); elapsed+=dt;
        }
        assert(normal.Progress==24000+10*(helpers*150-480));
        assert(contact.Progress==24000+10*(helpers*150-1440));
        FTick clear; clear.DeltaMs=1000; clear.CrankHelpers=helpers;
        int before=contact.Progress; Tick(contact,t,clear);
        assert(contact.Progress==before+helpers*150-480);
    }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            source, binary = Path(folder) / "lift.cpp", Path(folder) / "lift"
            source.write_text(code)
            subprocess.run([compiler, "-std=c++17", "-include", "initializer_list", "-I", str(ROOT / "Source/SoraArena/Public"), str(source), "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    unittest.main()
