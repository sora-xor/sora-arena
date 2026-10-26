#pragma once
#include <algorithm>

// ch03.b14: the complete kitchen court/alley volume and named wave entries.
namespace SoraTenementDefenseRules
{
constexpr int MinX=-3400,MinY=2220,MaxX=-2200,MaxY=3600,Top=600;
constexpr int FlightHeight=600,FlightLegs=2;
struct FPoint { double X=0,Y=0,Z=0; };
constexpr int Groups(int Wave) { return Wave==1?1:Wave==0||Wave==2?2:0; }
constexpr int Count(int Wave,int Group)
{ return Group>=0&&Group<Groups(Wave)?(Wave==2?1:2):0; }
constexpr const char* Kind(int Wave,int Group)
{
    return Wave==0?(Group==0?"enforcer_rifle":"bound_conscript"):
        Wave==1?"drone":Group==0?"blade_retainer":"enforcer_rifle";
}
constexpr bool Spawn(int Wave,int Group,int Member,FPoint& Out)
{
    if(Member<0||Member>=Count(Wave,Group))return false;
    if(Wave==1)Out={-3500.,3600.-Member*200.,FlightHeight};
    else Out={-2800.,450.+120.*(Member+(Wave==0?Group*2:Group)),90.15};
    return true;
}
constexpr FPoint FlightPoint(int Member,int Leg)
{
    return Leg==0?FPoint{-3300.,3350.-Member*300.,FlightHeight}:
        FPoint{-2800.,3050.-Member*300.,FlightHeight};
}
// Capsule overlap includes a drone whose centre is on the 6 m upper face.
// A drone above it or a guard still in the street does not contest the work.
inline bool InKitchen(double X,double Y,double Z,double Radius,double HalfHeight)
{
    if(!(Radius>0&&HalfHeight>=Radius))return false;
    const double DX=std::max({MinX-X,0.,X-MaxX});
    const double DY=std::max({MinY-Y,0.,Y-MaxY});
    const double DZ=std::max({-(Z+HalfHeight-Radius),0.,Z-HalfHeight+Radius-Top});
    return DX*DX+DY*DY+DZ*DZ<=Radius*Radius;
}
}
