#pragma once

// Chapter 6 L7: eight presses, three master presses. Integer simulation
// time, independent of rendering. Impulses sample the emission time;
// continuous footsteps integrate the masking window over their interval.
namespace SoraPressRules
{
constexpr int Count=8, PeriodMs=1600, WindowMs=500, RadiusCm=800;
constexpr int NoisePermille=200, InspectionMs=20000, JamMs=4000;
constexpr int LampSuspicionMs=5000;
constexpr bool LampNoticeDue(long long Now,long long Extinguished)
{ return Extinguished>=0&&Now>=Extinguished&&Now-Extinguished>=LampSuspicionMs; }
struct FPoint { int X,Y; };
constexpr int CatwalkHeightCm=400, CatwalkWidthCm=120, CatwalkGuard=4;
constexpr FPoint LadderFoot={300,2140}, LadderTop={300,2340};
constexpr FPoint CatwalkRoute[4]={{4140,2340},{4140,60},{60,60},{60,2340}};
constexpr FPoint Centers[Count]={{800,500},{1800,500},{2800,500},
    {800,1200},{1800,1200},{2800,1200},{1200,1900},{2400,1900}};
constexpr int Master[3]={1,4,6};
constexpr int AuditorOrder[8]={0,1,2,5,7,6,3,4};
constexpr FPoint FloorA[4]={{500,800},{3200,800},{3200,980},{500,980}};
constexpr FPoint FloorB[4]={{500,1480},{3200,1480},{3200,1660},{500,1660}};
constexpr FPoint DroneRoute[4]={{500,500},{3200,500},{3200,1900},{500,1900}};
constexpr int PatrolCount(int Guard) { return Guard>=0&&Guard<6?(Guard<2?8:4):0; }
constexpr int PatrolPeriod(int Guard) { return Guard<2?45000:Guard==5?30000:0; }
constexpr int PatrolDwell(int Guard) { return Guard<2?700:Guard==5?0:1500; }
constexpr int PatrolFloor(int Guard) { return Guard==4?CatwalkHeightCm:Guard==5?450:0; }
constexpr FPoint PatrolPoint(int Guard,int Index)
{
    if(Index<0||Index>=PatrolCount(Guard)) return {0,0};
    if(Guard<2)
    {
        const auto P=Centers[AuditorOrder[(Index+(Guard==1?4:0))%8]];
        return {P.X,P.Y-240};
    }
    return Guard==2?FloorA[Index]:Guard==3?FloorB[Index]:Guard==4?CatwalkRoute[Index]:DroneRoute[Index];
}
constexpr int Objective(int Press)
{
    for(int I=0;I<3;++I) if(Master[I]==Press) return I;
    return -1;
}
constexpr bool Running(unsigned Jammed,int Press)
{ return Press>=0&&Press<Count&&(Jammed&(1u<<Press))==0; }
constexpr bool Jam(unsigned& Jammed,int ObjectiveIndex)
{
    if(ObjectiveIndex<0||ObjectiveIndex>=3) return false;
    const unsigned Bit=1u<<Master[ObjectiveIndex];
    if(Jammed&Bit) return false;
    Jammed|=Bit; return true;
}
constexpr int Phase(long long Ms)
{ return Ms<0?0:int(Ms%PeriodMs); }
constexpr bool Masking(long long Ms) { return Ms>=0&&Phase(Ms)<WindowMs; }
// Milliseconds covered by stamp windows in [0,Ms). No loop over elapsed cycles.
constexpr long long MaskedBefore(long long Ms)
{ return Ms<=0?0:(Ms/PeriodMs)*WindowMs+(Ms%PeriodMs<WindowMs?Ms%PeriodMs:WindowMs); }
constexpr long long MaskedBetween(long long Begin,long long End)
{ return End<=Begin?0:MaskedBefore(End)-MaskedBefore(Begin); }
constexpr int Scale(int Loudness,int Mask)
{ return Loudness<=0?0:int((static_cast<long long>(Loudness)*Mask)/1000); }
}
