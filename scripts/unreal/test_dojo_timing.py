"""Keep the two authored pupil cadences distinct at every difficulty."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DojoTimingTests(unittest.TestCase):
    def test_authored_lesson_patterns_and_independent_rival(self):
        chapter = json.loads((ROOT / "Content/Data/campaign/chapter_01.json").read_text())
        self.assertEqual(chapter["beats"][2]["ext"]["opponent_pattern"], {
            "id": "pupil_men", "windup_ms": 550, "repeat_s": 1.45,
            "telegraph": "amber_edge", "stagger_on_awase_s": 1.2})
        self.assertEqual(chapter["beats"][3]["ext"]["opponent_pattern"], {
            "id": "pupil_kesa", "windup_ms": 600, "recovery_ms": 1000,
            "telegraph": "amber_edge_diagonal"})
        self.assertNotIn("opponent_pattern", chapter["beats"][1]["ext"])
        self.assertNotIn("opponent_pattern", chapter["beats"][10]["ext"])
        # The runtime consumes the authored extension rather than hard-coding
        # b04's timing in the AI, and keeps the rival's separate boss dispatch.
        director = (ROOT / "Source/SoraArena/Private/Game/SoraCampaignDirector.cpp").read_text()
        self.assertIn("Beat?Beat->PupilTiming", director)
        self.assertIn("Duel&&Duel->bDuel&&Duel->Opponent==Opponent", director)
        loader = (ROOT / "Source/SoraArena/Private/SoraCatalog.cpp").read_text()
        self.assertIn("SoraCatalogDojo::Read(*O, Beat)", loader)
        enemy = (ROOT / "Source/SoraArena/Private/Characters/SoraEnemy.cpp").read_text()
        self.assertIn("PupilWindupMs(PupilTiming,Difficulty)", enemy)
        self.assertIn("PupilStartIntervalMs(PupilTiming,Difficulty)", enemy)
        self.assertIn("Committed.WindupSeconds=Windup", enemy)

    def test_distinct_cadences_guard_window_and_frame_rounding(self):
        source = r'''
#include "SoraDojoRules.h"
#include <cassert>
#include <initializer_list>
using namespace SoraDojoRules;
int main() {
    constexpr FPupilTiming Men{550,0,1450}, Kesa{600,1000,0};
    constexpr int MenMs[]{715,550,468}, KesaMs[]{780,600,510};
    static_assert(PupilTimingValid(Men)&&PupilTimingValid(Kesa));
    // Conflicting cadence fields, no cadence, impossible repeat and unsafe
    // inputs are refused before they reach the world-facing timers.
    static_assert(!PupilTimingValid({550,1000,1450}));
    static_assert(!PupilTimingValid({550,0,0}));
    static_assert(!PupilTimingValid({550,0,715}));
    static_assert(PupilTimingValid({550,0,716}));
    static_assert(!PupilTimingValid({0,1000,0}));
    static_assert(!PupilTimingValid({10001,1000,0}));
    static_assert(!PupilTimingValid({550,-1,0}));
    static_assert(!PupilTimingValid({550,60001,0}));
    static_assert(!PupilTimingValid({550,0,60001}));
    for(int difficulty=0;difficulty<3;++difficulty) {
        assert(PupilWindupMs(Men,difficulty)==MenMs[difficulty]);
        assert(PupilWindupMs(Kesa,difficulty)==KesaMs[difficulty]);
        assert(PupilStartIntervalMs(Men,difficulty)==1450);
        assert(PupilStartIntervalMs(Kesa,difficulty)==KesaMs[difficulty]+1000);
        // A response on the next ordinary 60/30 Hz frame still gives the
        // b03 guard lesson its full 350 ms on Easy, Normal AND Hard.
        for(int frame:{17,34}) {
            const int held=MenMs[difficulty]-frame;
            assert(held>=GuardHoldMs&&held>ParryWindowMs);
            FProgress progress{1};
            assert(Record(progress,EAction::Guard,held));
            assert(Record(progress,EAction::Parry,160));
        }
        // Recovery is not difficulty-scaled, and a 1200 ms parry stagger
        // must supersede the earlier scheduled next-onset for BOTH drills.
        assert(PupilStartIntervalMs(Kesa,difficulty)-PupilWindupMs(Kesa,difficulty)==1000);
        assert(MenMs[difficulty]+1200>PupilStartIntervalMs(Men,difficulty));
        assert(KesaMs[difficulty]+1200>PupilStartIntervalMs(Kesa,difficulty));
    }
}
'''
        compiler = os.environ.get("CXX") or shutil.which("clang++") or shutil.which("c++")
        self.assertIsNotNone(compiler, "Host C++ compiler is required")
        with tempfile.TemporaryDirectory() as tmp:
            cpp, binary = Path(tmp) / "dojo.cpp", Path(tmp) / "dojo"
            cpp.write_text(source)
            subprocess.run([compiler, "-std=c++17", "-UNDEBUG", "-Wall", "-Werror", "-I",
                            str(ROOT / "Source/SoraArena/Public"), str(cpp), "-o", str(binary)],
                           check=True, capture_output=True, text=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
