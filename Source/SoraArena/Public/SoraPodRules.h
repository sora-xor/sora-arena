#pragma once
// Discrete arrival transactions, independent of the pending enemy cap.
namespace SoraPodRules
{
constexpr int Count=3, Members=3, WindupMs=2500, RadiusCm=350, Damage=60;
constexpr int FloorBelowCm=20, FloorAboveCm=80;
constexpr int Offsets[Members][2]={{-110,-60},{110,-60},{0,120}};
struct FArrival
{
    bool Active=false, Impacted=false;
    int ElapsedMs=0, Impacts=0, Contacts=0;
    float AppliedDamage=0;
};
inline bool Begin(FArrival& S)
{
    if(S.Active||S.Impacted) return false;
    S.Active=true; return true;
}
inline bool Tick(FArrival& S,int DeltaMs)
{
    if(!S.Active||S.Impacted||DeltaMs<=0) return false;
    S.ElapsedMs+=DeltaMs>WindupMs-S.ElapsedMs?WindupMs-S.ElapsedMs:DeltaMs;
    if(S.ElapsedMs<WindupMs) return false;
    S.Active=false; S.Impacted=true; ++S.Impacts; // Commit before any world callback.
    return true;
}
inline bool Contains(double X,double Y,double FeetZ)
{ return X*X+Y*Y<=RadiusCm*RadiusCm&&FeetZ>=-FloorBelowCm&&FeetZ<=FloorAboveCm; }
}
