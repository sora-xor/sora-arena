#pragma once
#include <algorithm>

// ch03.b02's landing encounter only. Descent and ascent are swept by the
// pawn; a timer cannot certify that the body reached either flight plane.
namespace SoraLandingDroneRules
{
constexpr int MarkMs=900, LowHeightCm=250, RootMs=1500, Damage=5;
// The chapter does not set a low dwell or vertical speed. Keep the catalog's
// five-second net recovery and 500 cm/s movement for this exposure window.
constexpr int LowMs=5000, SpeedCmPerSecond=500;
enum class EStage { Idle, Mark, Descending, Low, Ascending };
struct FState
{
    EStage Stage=EStage::Idle;
    int RemainingMs=0, WindupMs=0;
    int Releases=0;
};
inline void Begin(FState& S,int WindupMs)
{ S={EStage::Mark,std::max(0,WindupMs),std::max(0,WindupMs),0}; }
inline void Cancel(FState& S) { S.Stage=EStage::Idle; S.RemainingMs=0; }
// Return the part of this frame left for physical motion. A late frame may
// finish a warning, but still cannot release a net without ArriveLow.
inline int AdvanceTimer(FState& S,int DeltaMs)
{
    if(DeltaMs<=0||S.Stage==EStage::Idle) return 0;
    if(S.Stage!=EStage::Mark&&S.Stage!=EStage::Low) return DeltaMs;
    const int Used=std::min(DeltaMs,S.RemainingMs);
    S.RemainingMs-=Used;
    if(S.RemainingMs>0) return 0;
    S.Stage=S.Stage==EStage::Mark?EStage::Descending:EStage::Ascending;
    return DeltaMs-Used;
}
inline bool ArriveLow(FState& S,bool PhysicallyReached)
{
    if(S.Stage!=EStage::Descending||!PhysicallyReached) return false;
    S.Stage=EStage::Low; S.RemainingMs=LowMs; ++S.Releases;
    return true;
}
inline bool ArriveHome(FState& S,bool PhysicallyReached)
{
    if(S.Stage!=EStage::Ascending||!PhysicallyReached) return false;
    Cancel(S); return true;
}
inline bool WakizashiFinishes(bool Low,bool Melee,int WeaponId,float DamageAmount)
{ return Low&&Melee&&WeaponId==4&&DamageAmount>0; }
}
