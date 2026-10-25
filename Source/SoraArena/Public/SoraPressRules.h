#pragma once

// Chapter 6 L7: eight presses, three master presses. Integer simulation
// time, independent of rendering. Impulses sample the emission time;
// continuous footsteps integrate the masking window over their interval.
namespace SoraPressRules
{
constexpr int Count=8, PeriodMs=1600, WindowMs=500, RadiusCm=800;
constexpr int NoisePermille=200, InspectionMs=20000, JamMs=4000;
struct FPoint { int X,Y; };
constexpr FPoint Centers[Count]={{800,500},{1800,500},{2800,500},
    {800,1200},{1800,1200},{2800,1200},{1200,1900},{2400,1900}};
constexpr int Master[3]={1,4,6};
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
