#pragma once
#include "SoraFieldcraftRules.h"
#include <cmath>

namespace SoraClimbRules
{
constexpr int Height=1600, PeriodMs=20000, WatchMs=4000, StepMs=1800;
constexpr int CrawlFloor=1650, CrawlHeight=60, CrawlRadius=28, CrawlHalfHeight=28;
constexpr int CrawlEntry=1100, CrawlExit=1400, CrawlHalfWidth=60;
constexpr float CrawlSpeed=90.f;
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
constexpr SoraFieldcraftRules::FClimbRules GripRules(bool Extrusion)
{
    return {Extrusion?8:14,Height,6,25,Extrusion?0u:(1u<<5)|(1u<<9),400,30,800};
}
}
