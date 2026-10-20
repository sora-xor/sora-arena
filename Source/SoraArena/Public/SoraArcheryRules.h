#pragma once

// Chapter-one range only. A shot has an identity until impact or expiry;
// duplicate/late resolutions cannot score another arrow or another set.
// No Unreal dependency: the same rules are exercised by host tests.
namespace SoraArcheryRules
{
constexpr int Quiver=12,SetSize=6,RequiredHits=4,FetchMs=8000;
constexpr int NearCm=2800,HangingCm[3]={4000,5000,6000};
constexpr int HangingLaneCm[3]={-600,0,600};
constexpr int HitRadius[3]={25,21,18};
constexpr int SwingCm=150,PeriodMs=3200,DrawMs=650;
constexpr int UsableAfter=6,BentAfter=6;
enum class EStage : unsigned char { Near,Hanging,Done };
enum class EResult : unsigned char { Ignored,Miss,Hit,FailedSet,NearComplete,Complete };
struct FShot { unsigned long long Id=0; bool Eligible=false; };
struct FState
{
    EStage Stage=EStage::Near;
    int Issued=0,Resolved=0,Hits=0,FetchRemainingMs=0;
    unsigned HangingHits=0;
    bool LastHit=false;
    FShot Shots[Quiver]{};
};
inline int Pending(const FState& S)
{
    int Count=0;
    for(const auto& Shot:S.Shots) Count+=Shot.Id!=0;
    return Count;
}
inline bool CanLoose(const FState& S)
{
    return S.Stage!=EStage::Done&&S.FetchRemainingMs==0&&
        (S.Stage!=EStage::Near||S.Issued<SetSize)&&Pending(S)<Quiver;
}
inline bool Issue(FState& S,unsigned long long Id,bool Eligible)
{
    if(!Id||!CanLoose(S)) return false;
    for(const auto& Shot:S.Shots) if(Shot.Id==Id) return false;
    for(auto& Shot:S.Shots) if(!Shot.Id)
    {
        Shot={Id,Eligible}; ++S.Issued; return true;
    }
    return false;
}
inline EResult Resolve(FState& S,unsigned long long Id,int Target)
{
    FShot* Found=nullptr;
    if(!Id||S.Stage==EStage::Done||S.FetchRemainingMs>0) return EResult::Ignored;
    for(auto& Shot:S.Shots) if(Shot.Id==Id) { Found=&Shot; break; }
    if(!Found) return EResult::Ignored;
    const bool Eligible=Found->Eligible;
    *Found={}; ++S.Resolved;
    const bool Hit=Eligible&&(S.Stage==EStage::Near?Target==0:
        Target>=1&&Target<=3&&(S.HangingHits&(1u<<(Target-1)))==0);
    S.LastHit=Hit;
    if(Hit)
    {
        ++S.Hits;
        if(S.Stage==EStage::Hanging) S.HangingHits|=1u<<(Target-1);
    }
    if(S.Stage==EStage::Near&&S.Resolved==SetSize)
    {
        if(S.Hits<RequiredHits) { S.FetchRemainingMs=FetchMs; return EResult::FailedSet; }
        S.Stage=EStage::Hanging; S.Issued=S.Resolved=S.Hits=0;
        return EResult::NearComplete;
    }
    if(S.Stage==EStage::Hanging&&S.HangingHits==7u)
    {
        S.Stage=EStage::Done; return EResult::Complete;
    }
    return Hit?EResult::Hit:EResult::Miss;
}
// The text specifies fetching between failed near sets. For the unbounded
// hanging stage, an exhausted quiver also fetches after all arrows resolve.
// This explicit recovery retains earned hits and prevents a miss softlock.
inline bool FetchExhausted(FState& S,int Ammo)
{
    if(S.Stage!=EStage::Hanging||S.FetchRemainingMs||Ammo!=0||Pending(S)) return false;
    S.FetchRemainingMs=FetchMs; return true;
}
inline bool TickFetch(FState& S,int DeltaMs)
{
    if(S.FetchRemainingMs<=0||DeltaMs<=0) return false;
    S.FetchRemainingMs=DeltaMs>=S.FetchRemainingMs?0:S.FetchRemainingMs-DeltaMs;
    if(S.FetchRemainingMs) return false;
    S.Issued=S.Resolved=S.Hits=0;
    return true;
}
// Checkpoint restarts reconstruct the authored chapter inventory, not a
// partial target attempt. Completed b09 has repaired every bent arrow.
constexpr int Bent(unsigned Completed) { return (Completed&(1u<<6))&&!(Completed&(1u<<8))?BentAfter:0; }
constexpr int Usable(unsigned Completed) { return Bent(Completed)?UsableAfter:Quiver; }
}
