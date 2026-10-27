#pragma once
#include <cmath>

// Ordinary yumi aiming, independent of the deterministic practice kernel.
namespace SoraBowRules
{
// Authored ch01.b07 x_shaho: 650 ms to full draw, then four steady seconds.
constexpr int DrawMs=650,FullDrawSwayAfterMs=4000;
// Provisional play-review defaults, NOT numbers supplied by the chapter:
// one smooth ramp, fixed pitch/yaw waves, identical on every difficulty.
constexpr int SwayRampMs=1000;
constexpr double PitchAmplitudeDegrees=.18,YawAmplitudeDegrees=.28;
constexpr double PitchPeriodSeconds=2.6,YawPeriodSeconds=3.4;
struct FAimOffset { double Pitch=0,Yaw=0; };
inline FAimOffset AimSway(double DrawElapsedSeconds)
{
    const double Since=DrawElapsedSeconds-(DrawMs+FullDrawSwayAfterMs)/1000.0;
    if(!std::isfinite(Since)||Since<=0) return {};
    const double Ramp=Since>=SwayRampMs/1000.0?1.0:Since*1000.0/SwayRampMs;
    const double Weight=Ramp*Ramp*(3.0-2.0*Ramp);
    constexpr double Tau=6.2831853071795864769;
    // Evaluate from this draw's absolute age; never accumulate frame steps or
    // sample randomness at release. The player can see and counter this ray.
    return {PitchAmplitudeDegrees*Weight*std::sin(Tau*Since/PitchPeriodSeconds),
        YawAmplitudeDegrees*Weight*std::sin(Tau*Since/YawPeriodSeconds)};
}
}
