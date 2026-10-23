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
// Provisional foot clearance for crossing a support edge. Exact tangency
// catches the rounded capsule on the side face even without penetration.
constexpr int SupportLiftCm=6;
struct FGuidePoint { int X,Y,Z; };
constexpr FGuidePoint GuideRoofPath[]={
    {900,500,1600+SupportLiftCm},{1040,500,1600+SupportLiftCm},{1040,500,1800},{1040,500,2000},
    {1040,500,2200},{1040,500,GuideRoofHeight+SupportLiftCm},
    {1500,500,GuideRoofHeight+SupportLiftCm},{1500,500,GuideRoofHeight}};
struct FPathPoint { double X,Y,Z; };
enum class EHoldPath { Direct, OntoRest, OffRest, BeforeRest, FromBeforeRest, Mount };
inline FPathPoint Mix(FPathPoint A,FPathPoint B,double T)
{ return {A.X+(B.X-A.X)*T,A.Y+(B.Y-A.Y)*T,A.Z+(B.Z-A.Z)*T}; }
inline FPathPoint HoldPath(FPathPoint A,FPathPoint B,double T,EHoldPath Path)
{
    switch(Path)
    {
    case EHoldPath::OntoRest:
    {
        const FPathPoint Outside{B.X-210,B.Y,B.Z+SupportLiftCm},Above{B.X,B.Y,B.Z+SupportLiftCm};
        return T<.7?Mix(A,Outside,T/.7):T<.9?Mix(Outside,Above,(T-.7)/.2):Mix(Above,B,(T-.9)/.1);
    }
    case EHoldPath::OffRest:
    {
        const FPathPoint Above{A.X,A.Y,A.Z+SupportLiftCm},Outside{A.X-210,A.Y,A.Z+SupportLiftCm};
        return T<.1?Mix(A,Above,T/.1):T<.3?Mix(Above,Outside,(T-.1)/.2):Mix(Outside,B,(T-.3)/.7);
    }
    case EHoldPath::BeforeRest:
    { const FPathPoint Outside{B.X,B.Y,A.Z};return T<.2?Mix(A,Outside,T/.2):Mix(Outside,B,(T-.2)/.8); }
    case EHoldPath::FromBeforeRest:
    { const FPathPoint Below{A.X,A.Y,B.Z};return T<.8?Mix(A,Below,T/.8):Mix(Below,B,(T-.8)/.2); }
    case EHoldPath::Mount:
    {
        const FPathPoint Lifted{A.X,A.Y,A.Z+SupportLiftCm},Above{B.X,B.Y,B.Z+SupportLiftCm};
        return T<.15?Mix(A,Lifted,T/.15):T<.85?Mix(Lifted,Above,(T-.15)/.7):Mix(Above,B,(T-.85)/.15);
    }
    default:return Mix(A,B,T);
    }
}
inline bool AtSupport(bool Penetrating,double NormalZ,double ImpactNormalZ,double LateralError,double AboveTarget)
{ return !Penetrating&&NormalZ>=.99&&ImpactNormalZ>=.99&&LateralError<=.25&&AboveTarget>=0&&AboveTarget<=3; }
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
