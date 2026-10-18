#pragma once
// Presentation only. Absolute task-clock phase makes the same pose at every
// frame size; no clock, progress, or input is advanced by a rendered frame.
namespace SoraWorkshopRules
{
struct FPose
{
    float CueTap=0.f, Response=0.f, Shuttle=-1.f, Ring=1.f;
    bool Glint=false;
};
constexpr float Pulse(int AgeMs,int DurationMs)
{
    return AgeMs<0||AgeMs>=DurationMs?0.f:1.f-static_cast<float>(AgeMs)/DurationMs;
}
constexpr FPose Pose(bool Active,int ElapsedMs,int PeriodMs,int HitAgeMs)
{
    FPose P;
    if(!Active||ElapsedMs<0||PeriodMs<=0) return P;
    const int Age=ElapsedMs%PeriodMs;
    const int Cycle=ElapsedMs/PeriodMs;
    P.CueTap=Pulse(Age,160);
    P.Response=Pulse(HitAgeMs,220);
    P.Glint=Age<90;
    P.Ring=1.f-static_cast<float>(Age)/PeriodMs;
    const float Travel=Age<180?static_cast<float>(Age)/180.f:1.f;
    P.Shuttle=Cycle%2==0?-1.f+2.f*Travel:1.f-2.f*Travel;
    return P;
}
}
