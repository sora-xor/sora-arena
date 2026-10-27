#pragma once
#include <algorithm>
#include <cmath>

// Chapter 7's authored mechanics; geometry/tuning below is a gameplay proxy
// in the current bridge hall, not the unbuilt tiered amphitheatre.
namespace SoraBridgeRules
{
constexpr int ListDegrees=10, UphillPermille=850, DownhillPermille=1100;
constexpr int PeriodMs=6000, WarningMs=700, Damage=30, StaggerMs=600;
constexpr int Chairs=6, Pods=4;
constexpr double TiltSeconds=1.0;
constexpr double GravityCm=980.0, MaxSlideCmPerSecond=500.0;
inline double Pace(double DownhillDot,bool Grounded,bool Listed)
{
    if(!Grounded||!Listed) return 1.0;
    return DownhillDot>0.01?DownhillPermille/1000.0:DownhillDot<-.01?UphillPermille/1000.0:1.0;
}
inline double ListAt(double Degrees,double Dt,bool Listed)
{
    const double Target=Listed?ListDegrees:0;
    const double Step=std::max(0.0,Dt)*ListDegrees/TiltSeconds;
    return Degrees<Target?std::min(Target,Degrees+Step):std::max(Target,Degrees-Step);
}
inline double SlideStep(double& Speed,double Dt,double Degrees)
{
    if(Dt<=0||Degrees<=0) return 0;
    const double A=GravityCm*std::sin(Degrees*3.14159265358979323846/180);
    const double UntilCap=std::max(0.0,(MaxSlideCmPerSecond-Speed)/A);
    const double Accelerating=std::min(Dt,UntilCap);
    const double Distance=Speed*Accelerating+.5*A*Accelerating*Accelerating+
        MaxSlideCmPerSecond*(Dt-Accelerating);
    Speed=std::min(MaxSlideCmPerSecond,Speed+A*Dt);
    return Distance;
}
// Integrate only the interval after the warning and before the next cue.
// This also prevents a frame crossing 700 ms from moving a full frame early.
inline double MovingSeconds(double BeforeMs,double AfterMs,int Warning=WarningMs)
{
    return std::max(0.0,std::min(AfterMs,double(PeriodMs))-std::max(BeforeMs,double(Warning)))/1000;
}
}
