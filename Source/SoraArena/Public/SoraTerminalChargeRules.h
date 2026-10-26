#pragma once
#include <algorithm>

// The festival-shell charge is independent of the mounted cavalry charge.
// Work and fuse clocks are advanced separately: the ignition frame cannot
// donate its hold time to the newly lit fuse.
namespace SoraTerminalChargeRules
{
constexpr int PlantMs=4000,LightMs=1000,FuseMs=20000,BlastRadius=800,SafeDistance=1500,Damage=120;
constexpr int TerminalX=-730,TerminalY=460,PanelX=-730,PanelY=560;
enum class EStage { Empty,Planted,Burning,Detonated };
enum class EEvent { None,Planted,Ignited,Detonated };
struct FState
{
    EStage Stage=EStage::Empty;
    bool Working=false,WaitRelease=false;
    int HeldMs=0,FuseAgeMs=0;
};
constexpr int HoldNeed(const FState& S){return S.Stage==EStage::Empty?PlantMs:S.Stage==EStage::Planted?LightMs:0;}
constexpr bool Begin(FState& S)
{
    if(S.Working||S.WaitRelease||!HoldNeed(S))return false;
    S.Working=true;S.HeldMs=0;return true;
}
constexpr void Cancel(FState& S,bool WaitRelease=true)
{S.Working=false;S.HeldMs=0;S.WaitRelease=WaitRelease;}
constexpr EEvent Work(FState& S,int DeltaMs,bool Eligible)
{
    if(!S.Working)return EEvent::None;
    if(!Eligible){Cancel(S);return EEvent::None;}
    const int Need=HoldNeed(S);
    S.HeldMs+=std::clamp(DeltaMs,0,std::max(0,Need-S.HeldMs));
    if(S.HeldMs<Need)return EEvent::None;
    const bool Plant=S.Stage==EStage::Empty;
    S.Stage=Plant?EStage::Planted:EStage::Burning;Cancel(S);
    S.FuseAgeMs=0;return Plant?EEvent::Planted:EEvent::Ignited;
}
constexpr EEvent Fuse(FState& S,int DeltaMs)
{
    if(S.Stage!=EStage::Burning)return EEvent::None;
    S.FuseAgeMs+=std::clamp(DeltaMs,0,FuseMs-S.FuseAgeMs);
    if(S.FuseAgeMs<FuseMs)return EEvent::None;
    S.Stage=EStage::Detonated;return EEvent::Detonated;
}
constexpr bool InSafeVolume(double X,double Y,double Feet)
{return X>=-2200&&X<=-1000&&Y>=2900&&Y<=3100&&Feet>=0&&Feet<=400;}
constexpr bool Safe(double X,double Y,double Feet,bool Grounded,bool Occluded)
{
    const double DX=X-TerminalX,DY=Y-TerminalY;
    return Grounded&&Occluded&&InSafeVolume(X,Y,Feet)&&DX*DX+DY*DY>=SafeDistance*SafeDistance;
}
}
