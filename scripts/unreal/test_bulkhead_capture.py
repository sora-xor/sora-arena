"""Authored capture admission and the real transient hold/clock rules.

Mapped input, collision, navigation and reload wiring are exercised by the
prepared SoraArena.Campaign.BulkheadCapture Unreal fixture, not this host test.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from build_campaign_data import BuildError, build_chapter, load_places, normalize_task
from validate_campaign import CampaignError, check_capture_hold

ROOT = Path(__file__).resolve().parents[2]


class BulkheadCaptureTests(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT / "Content/Data/campaign/chapter_06.json").read_text())
        self.beat = self.chapter["beats"][12]
        self.space = self.chapter["space"]["beats"][12]

    def test_authored_hold_and_entry_relation(self):
        self.assertEqual(self.beat["ext"]["defeat_interact"], {"id": "bulkhead_lever", "hold_s": 2})
        self.assertEqual(self.beat["task"]["capture_hold_ms"], 2000)
        # The chapter pass applies carried mission arms after normalize_task.
        # Check the complete pipeline so neither the hold nor its equipment
        # restriction can disappear when these independent contracts compose.
        rebuilt = build_chapter(6, load_places())
        self.assertEqual(self.beat["task"], rebuilt["beats"][12]["task"])
        self.assertEqual(self.beat["task"]["equipment_weapons"], [0, 3, 4, 10, 13, 18])
        self.assertEqual(self.space["bulkhead"], [self.space["entry"][0], self.space["entry"][1] + 180])
        self.assertEqual(self.chapter["space"]["zones"][self.space["zone"]]["place"], "pl_vault_core")
        check_capture_hold(self.beat, self.space)
        self.assertTrue(any(t["beat"] == self.beat["id"] and t["on"] == "interact:bulkhead_lever" and
                            t["lines"] == ["ch06.b13.nyaakoto.003"] for t in self.chapter["triggers"]))

    def test_authored_duration_and_binding_mutations_fail(self):
        for value in (None, False, True, 0, -2, 1.5, 1.999, 2.001, "2", [], {}):
            beat = copy.deepcopy(self.beat)
            beat["ext"]["defeat_interact"]["hold_s"] = value
            with self.subTest(value=value), self.assertRaises(BuildError):
                normalize_task(beat)
        changes = ({"id": "ch06.b12"}, {"id": "ch08.b14"},
                   {"params": {**self.beat["params"], "boss": "boss_val_amort"}},
                   {"params": {**self.beat["params"], "defeat": "kill"}},
                   {"ext": {}}, {"ext": {"defeat_interact": {"id": "engine_spine", "hold_s": 2}}},
                   {"ext": {"defeat_interact": {"id": "bulkhead_lever", "hold_s": 2},
                            "post_defeat": {"interact": "engine_spine", "hold_s": 1.5}}})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(BuildError):
                normalize_task({**self.beat, **change})

    def test_normalized_mutations_cannot_bypass_admission(self):
        for key, values in (("capture_hold_ms", (None, False, "2000", 2000.0, 0, 1999, 2001)),
                            ("capture_event", (None, "interact:engine_spine", "interact:unknown")),
                            ("opponent", ("boss_val_amort", None)), ("defeat", ("kill", "spare"))):
            for value in values:
                beat = copy.deepcopy(self.beat)
                beat["task"][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(CampaignError):
                    check_capture_hold(beat, self.space)
        for value in (None, [], [48680, 0], [48680, True], [48680.0, 180], [48680, 180, 0]):
            with self.subTest(point=value), self.assertRaises(CampaignError):
                check_capture_hold(self.beat, {**self.space, "bulkhead": value})
        for key, value in (("height_cm", 300), ("entry", [48680, 0, 90])):
            with self.assertRaises(CampaignError):
                check_capture_hold(self.beat, {**self.space, key: value})
        without = {k: v for k, v in self.space.items() if k != "bulkhead"}
        with self.assertRaises(CampaignError):
            check_capture_hold(self.beat, without)

    def test_only_the_two_authored_endings_capture(self):
        found = {}
        for path in sorted((ROOT / "Content/Data/campaign").glob("chapter_*.json")):
            chapter = json.loads(path.read_text())
            for beat, space in zip(chapter["beats"], chapter["space"]["beats"]):
                check_capture_hold(beat, space)
                if beat["task"]["capture_event"]:
                    found[beat["id"]] = beat["task"]["capture_hold_ms"]
                elif beat["id"] != "ch06.b13":
                    with self.assertRaises(CampaignError):
                        check_capture_hold(beat, {**space, "bulkhead": [0, 180]})
        self.assertEqual(found, {"ch06.b13": 2000, "ch08.b14": 1500})

    def test_native_contract_clock_hold_and_once_only_capture(self):
        source = r'''
#include "SoraCaptureRules.h"
#include "SoraSummitRules.h"
#include "SoraMillisecondClock.h"
#include "SoraBeatRules.h"
#include <cassert>
#include <algorithm>
#include <iostream>
int main() {
    using namespace SoraCaptureRules;
    assert(Valid("ch06.b13","boss_eskro","interact:bulkhead_lever",2000,true,true));
    assert(Valid(u"ch06.b13",u"boss_eskro",u"interact:bulkhead_lever",2000,true,true));
    assert(Valid("ch08.b14","boss_val_amort","interact:engine_spine",1500,true,true));
    assert(Valid("ch06.b12","","",0,false,false));
    for(int ms:{-1,0,1,1500,1999,2001,2147483647})
        assert(!Valid("ch06.b13","boss_eskro","interact:bulkhead_lever",ms,true,true));
    for(const char* beat:{"ch06.b12","ch08.b14","unknown"})
        assert(!Valid(beat,"boss_eskro","interact:bulkhead_lever",2000,true,true));
    assert(!Valid("ch06.b13","boss_eskro","interact:engine_spine",2000,true,true));
    assert(!Valid("ch06.b13","boss_val_amort","interact:bulkhead_lever",2000,true,true));
    assert(!Valid("ch06.b13","boss_eskro","interact:bulkhead_lever",2000,false,true));
    assert(!Valid("ch06.b13","boss_eskro","",0,true,false));
    assert(!Valid("ch06.b12","boss_eskro","interact:bulkhead_lever",2000,true,true));
    using namespace SoraSummitRules;
    for(int step:{1,7,16,33,100,500}) {
        FCut hold;
        assert(!Begin(hold,false,true));
        assert(!TickCut(hold,2000,false,true,2000));
        assert(!Begin(hold,true,true)); // Entering reach with an old press cannot start.
        TickCut(hold,0,true,false,2000);
        assert(Begin(hold,true,true));
        int elapsed=0;
        while(elapsed<1999) {
            const int delta=std::min(step,1999-elapsed);
            assert(!TickCut(hold,delta,true,true,2000)); elapsed+=delta;
        }
        assert(hold.HeldMs==1999&&hold.Active);
        assert(TickCut(hold,1,true,true,2000));
        assert(!TickCut(hold,2000,true,true,2000)&&!Begin(hold,true,true));
        TickCut(hold,0,true,false,2000); assert(Begin(hold,true,true));
        assert(!TickCut(hold,1999,true,true,2000));
        Interrupt(hold); // Damage, lost reach, pause and dialogue discard the same transient work.
        assert(hold.HeldMs==0&&!hold.Active&&hold.NeedsRelease);
        assert(!Begin(hold,true,true)&&!TickCut(hold,2000,true,true,2000));
        TickCut(hold,0,true,false,2000); assert(Begin(hold,true,true));
        assert(!TickCut(hold,1000,true,true,2000));
        TickCut(hold,0,true,false,2000); assert(Begin(hold,true,true));
        assert(!TickCut(hold,1999,true,true,2000)); // Release/re-press banks nothing.
    }
    for(double hz:{30.,60.,144.,240.}) {
        FSoraMillisecondClock clock; FCut hold; assert(Begin(hold,true,true));
        double seconds=0; bool done=false;
        while(!done) {
            seconds+=1./hz;
            done=TickCut(hold,std::min(clock.Advance(1./hz),2000-hold.HeldMs),true,true,2000);
            if(seconds<1.999999) assert(!done);
        }
        assert(seconds>=1.999999&&seconds<2.+1./hz+.000001);
    }
    FSoraMillisecondClock clock;
    assert(clock.Advance(.0009)==0); clock.Reset();
    assert(clock.Advance(.0002)==0); // Cancel cannot transfer a fractional millisecond.
    using namespace SoraBeatRules;
    FTask task; task.Type=EType::Boss; task.Goal=EGoal::OpponentDown; task.Defeat=EDefeat::Capture;
    task.PhaseCount=3; task.PhaseStart[1]=600; task.PhaseStart[2]=250;
    auto state=StartTask(task,2); assert(!AwaitsCapture(state,task)&&!Capture(state,task));
    OpponentHealth(state,task,0); assert(AwaitsCapture(state,task));
    assert(Capture(state,task)&&!Capture(state,task)&&!AwaitsCapture(state,task));
    auto retry=StartTask(task,2); assert(retry.OpponentPermille==250&&!retry.Captured&&!AwaitsCapture(retry,task));
    std::cout<<"strict capture contract, 1999/2000 ms, cancellation, fractional clock, once-only outcome PASS\n";
}
'''
        compiler = os.environ.get("CXX") or shutil.which("clang++") or shutil.which("c++")
        self.assertIsNotNone(compiler, "Host C++ compiler is required")
        with tempfile.TemporaryDirectory() as tmp:
            cpp, binary = Path(tmp) / "capture.cpp", Path(tmp) / "capture"
            cpp.write_text(source)
            built = subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-I",
                                    str(ROOT / "Source/SoraArena/Public"), str(cpp), "-o", str(binary)],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            print(result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
