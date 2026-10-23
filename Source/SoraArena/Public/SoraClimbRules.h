#pragma once
#include "SoraFieldcraftRules.h"
#include <cmath>

namespace SoraClimbRules
{
constexpr int Height=1600, PeriodMs=20000, WatchMs=4000, StepMs=1800;
constexpr int CrawlFloor=1650, CrawlHeight=60, CrawlRadius=28, CrawlHalfHeight=28;
constexpr int CrawlEntry=1100, CrawlExit=1400, CrawlHalfWidth=60;
constexpr float CrawlSpeed=90.f;
// Provisional companion staging and roof approach; the script specifies
// climbing first and waiting on the 24 m turret roof, not these coordinates.
constexpr float GuideSpeed=140.f;
constexpr int GuideRoofHeight=2400;
struct FGuidePoint { int X,Y,Z; };
constexpr FGuidePoint GuideRoofPath[]={
    {900,500,1600},{1040,500,1600},{1040,500,1800},{1040,500,2000},
    {1040,500,2200},{1040,500,2400},{1500,500,2400}};
// Implementation geometry/timing, not authored hold coordinates: the wall
// uses two slope segments; art may curve the upper profile within this shell.
inline double WallX(double Z)
{
    constexpr double Pi=3.14159265358979323846;
    return Z<=600 ? Z/std::tan(Pi/3) : 600/std::tan(Pi/3)+(Z-600)/std::tan(80*Pi/180);
}
constexpr int CornerZ[]={0,110,220,330,440,550,680,820,960,1100,1200,1300,1400,1500,1600};
constexpr int ExtrusionZ[]={0,200,400,600,800,1000,1200,1400,1600};
constexpr bool Watching(int ClockMs) { return ClockMs>=PeriodMs && ClockMs%PeriodMs<WatchMs; }
constexpr int CircuitMs(int ClockMs) { return (ClockMs+PeriodMs-WatchMs)%PeriodMs; }
struct FPatrolPoint { double X,Y; };
inline FPatrolPoint PatrolAt(int ClockMs)
{
    if(Watching(ClockMs)) return {360,-300};
    const double T=ClockMs<PeriodMs?double(ClockMs)/PeriodMs:double((ClockMs-WatchMs)%PeriodMs)/(PeriodMs-WatchMs);
    const double Out=T<.5?T*2:(1-T)*2;
    const double Distance=Out*3790; // 290 cm bay arm + 500 cm approach + 30 m parapet.
    if(Distance<290) return {360+Distance,-300};
    return {650,-300-(Distance-290)};
}
constexpr SoraFieldcraftRules::FClimbRules GripRules(bool Extrusion)
{
    return {Extrusion?8:14,Height,6,25,Extrusion?0u:(1u<<5)|(1u<<9),400,30,800};
}
}
