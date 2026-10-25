#pragma once
// ch02.b06 only. Time is active play, not wall time or the actor's lifespan.
namespace SoraHorseShellRules
{
constexpr int Wave=1, Damage=35, RadiusCm=300, WarningMs=1400, IntervalMs=6000;
constexpr int FlightMs=1400, ArmingCm=200, MinRangeCm=600, MaxRangeCm=2500;
struct FState
{
    long long ClockMs=0, NextReleaseMs=0, WarningStartedMs=0, ReleaseAtMs=0;
    bool Winding=false;
    int Releases=0;
};
inline void Advance(FState& S,int DeltaMs) { if(DeltaMs>0) S.ClockMs+=DeltaMs; }
inline bool CanBegin(const FState& S)
{ return !S.Winding&&S.ClockMs+WarningMs>=S.NextReleaseMs; }
inline bool Begin(FState& S)
{
    if(!CanBegin(S)) return false;
    S.Winding=true; S.WarningStartedMs=S.ClockMs; S.ReleaseAtMs=S.ClockMs+WarningMs;
    return true;
}
inline void Cancel(FState& S) { S.Winding=false; }
inline bool Ready(const FState& S) { return S.Winding&&S.ClockMs>=S.ReleaseAtMs; }
inline bool Release(FState& S)
{
    if(!Ready(S)) return false;
    S.Winding=false; ++S.Releases;
    // A late frame fires once and starts a new interval; it never catches up.
    S.NextReleaseMs=S.ClockMs+IntervalMs;
    return true;
}
}
