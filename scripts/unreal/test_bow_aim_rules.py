"""Visible yumi sway: authored onset, bounded provisional tuning, no frame RNG."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BowAimRulesTests(unittest.TestCase):
    def test_authored_draw_and_full_hold_threshold(self):
        chapter = json.loads((ROOT / "Content/Data/campaign/chapter_01.json").read_text())
        shaho = chapter["beats"][6]["ext"]["shaho"]
        self.assertEqual(shaho["draw_ms"], 650)
        self.assertEqual(shaho["hold_sway_after_s"], 4.0)
        self.assertTrue(shaho["no_fire_while_sprinting"])

    def test_absolute_clock_onset_envelope_and_replay(self):
        source = r'''
#include "SoraBowRules.h"
#include <cassert>
#include <initializer_list>
#include <limits>
using namespace SoraBowRules;
bool zero(FAimOffset x) { return x.Pitch==0 && x.Yaw==0; }
int main() {
    static_assert(DrawMs==650 && FullDrawSwayAfterMs==4000);
    static_assert(SwayRampMs==1000);
    for(double t:{-1.,0.,.649,.650,4.,4.649999,4.650}) assert(zero(AimSway(t)));
    assert(zero(AimSway(std::numeric_limits<double>::quiet_NaN())));
    assert(zero(AimSway(std::numeric_limits<double>::infinity())));
    const auto onset=AimSway(4.650001);
    assert(onset.Pitch>0 && onset.Yaw>0 && onset.Pitch<1e-12 && onset.Yaw<1e-12);
    // Independent golden samples detect swapped axes, timing and ramp shape.
    const auto half=AimSway(5.15), full=AimSway(5.65);
    assert(std::abs(half.Pitch-.0841514618416873)<1e-12);
    assert(std::abs(half.Yaw-.1117224118192335)<1e-12);
    assert(std::abs(full.Pitch-.1193620784833431)<1e-12);
    assert(std::abs(full.Yaw-.2693111800883893)<1e-12);
    double pitchMax=0,yawMax=0,pitchMin=0,yawMin=0;
    for(int ms=4651;ms<300000;++ms) {
        const auto a=AimSway(ms/1000.0);
        assert(std::isfinite(a.Pitch)&&std::isfinite(a.Yaw));
        assert(std::abs(a.Pitch)<=PitchAmplitudeDegrees&&std::abs(a.Yaw)<=YawAmplitudeDegrees);
        pitchMax=std::fmax(pitchMax,a.Pitch); yawMax=std::fmax(yawMax,a.Yaw);
        pitchMin=std::fmin(pitchMin,a.Pitch); yawMin=std::fmin(yawMin,a.Yaw);
    }
    assert(pitchMax>.1799&&pitchMin<-.1799&&yawMax>.2799&&yawMin<-.2799);
    // The one-second join is continuous in value and slope; no pop at full amplitude.
    constexpr double eps=1e-5;
    const auto lo=AimSway(5.65-eps),hi=AimSway(5.65+eps);
    assert(std::abs((full.Pitch-lo.Pitch)/eps-(hi.Pitch-full.Pitch)/eps)<.0001);
    assert(std::abs((full.Yaw-lo.Yaw)/eps-(hi.Yaw-full.Yaw)/eps)<.0001);
    // Different frame partitions and arbitrary intervening reads cannot change
    // the sampled ray; a new draw starts at zero rather than world-time phase.
    for(int frame:{1,8,16,17,33,100,500}) {
        for(int ms=0;ms<5650;ms+=frame) (void)AimSway(ms/1000.0);
        const auto replay=AimSway(5.65);
        assert(replay.Pitch==full.Pitch&&replay.Yaw==full.Yaw);
        assert(zero(AimSway(0.0)));
    }
}
'''
        compiler = os.environ.get("CXX") or shutil.which("clang++") or shutil.which("c++")
        self.assertIsNotNone(compiler, "Host C++ compiler is required")
        with tempfile.TemporaryDirectory() as tmp:
            cpp, binary = Path(tmp) / "bow_aim.cpp", Path(tmp) / "bow_aim"
            cpp.write_text(source)
            subprocess.run([compiler, "-std=c++17", "-I", str(ROOT / "Source/SoraArena/Public"),
                            str(cpp), "-o", str(binary)], check=True, capture_output=True, text=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
