#pragma once
#include "SoraCaptionLayoutRules.h"
#include "SoraArcheryRules.h"
#include <algorithm>
#include <initializer_list>

// Screen-space allocation only. Font measurement stays in the live Canvas
// caller; the same planner is exercised with independent host font metrics.
namespace SoraAimHUDLayout
{
using SoraCaptionLayoutRules::FRect;
constexpr int MaxObstacles=32;
// Centered target/reticle clearance: 256 x 173 px at the minimum 720p
// viewport, including the normal bow sway. This is reserved in production.
inline FRect Aim(float W,float H) { return {W*.4f,H*.38f,W*.2f,H*.24f}; }
inline int LowerRegions(float W,float H,float Scale,float ObjectiveBottom,float WeaponLeft,FRect* Out)
{
    const auto A=Aim(W,H);
    const float Gap=6*Scale,Left=20*Scale,Bottom=H-110*Scale-Gap;
    const float HealthRight=365*Scale+Gap;
    // Prefer the wide space below the target. Larger subtitles can use the
    // left column, while the center-bottom region extends beside health.
    Out[0]={Left,A.Y+A.H+Gap,WeaponLeft-Left-Gap,Bottom-A.Y-A.H-Gap};
    Out[1]={Left,ObjectiveBottom+Gap,A.X-Left-Gap,Bottom-ObjectiveBottom-Gap};
    Out[2]={HealthRight,A.Y+A.H+Gap,WeaponLeft-HealthRight-Gap,H-30*Scale-A.Y-A.H-Gap};
    return 3;
}
inline bool Contains(const FRect& A,const FRect& B)
{
    return B.X>=A.X-.01f&&B.Y>=A.Y-.01f&&B.X+B.W<=A.X+A.W+.01f&&B.Y+B.H<=A.Y+A.H+.01f;
}
struct FRegions { FRect Bounds[SoraCaptionLayoutRules::MaxRegions]{}; int Count=0; };
inline FRegions FreeRegions(FRect View,const FRect* Obstacles,int Count,float Gap)
{
    FRegions Result;
    if(Count<0||Count>MaxObstacles||View.W<=0||View.H<=0) return Result;
    FRect Blocks[MaxObstacles]{};
    float Edges[2*MaxObstacles+2]={View.X,View.X+View.W}; int EdgesCount=2;
    for(int I=0;I<Count;++I)
    {
        const auto& O=Obstacles[I]; Blocks[I]={O.X-Gap,O.Y-Gap,O.W+2*Gap,O.H+2*Gap};
        for(float X:{Blocks[I].X,Blocks[I].X+Blocks[I].W})
            if(X>View.X&&X<View.X+View.W) Edges[EdgesCount++]=X;
    }
    std::sort(Edges,Edges+EdgesCount);
    FRect Candidates[128]{}; int CandidateCount=0;
    const auto Add=[&](FRect R)
    {
        if(R.W<150||R.H<20) return;
        for(int I=0;I<CandidateCount;++I) if(Contains(Candidates[I],R)) return;
        for(int I=CandidateCount-1;I>=0;--I)
            if(Contains(R,Candidates[I])) Candidates[I]=Candidates[--CandidateCount];
        if(CandidateCount<128) Candidates[CandidateCount++]=R;
    };
    for(int L=0;L<EdgesCount;++L) for(int R=L+1;R<EdgesCount;++R)
    {
        const float X=Edges[L],Width=Edges[R]-X;
        if(Width<150) continue;
        float Y=View.Y;
        while(Y<View.Y+View.H)
        {
            float End=View.Y+View.H,After=Y;
            for(int I=0;I<Count;++I)
            {
                const auto& B=Blocks[I];
                if(B.X>=X+Width-.01f||B.X+B.W<=X+.01f||B.Y+B.H<=Y+.01f||B.Y>=View.Y+View.H) continue;
                if(B.Y<=Y+.01f) After=std::max(After,B.Y+B.H);
                else End=std::min(End,B.Y);
            }
            if(After>Y+.01f) { Y=After; continue; }
            Add({X,Y,Width,End-Y});
            if(End>=View.Y+View.H) break;
            Y=End;
        }
    }
    std::sort(Candidates,Candidates+CandidateCount,[](const FRect& A,const FRect& B)
    { const float AA=A.W*A.H,BA=B.W*B.H; return AA!=BA?AA>BA:A.Y!=B.Y?A.Y<B.Y:A.X<B.X; });
    Result.Count=std::min(CandidateCount,SoraCaptionLayoutRules::MaxRegions);
    for(int I=0;I<Result.Count;++I) Result.Bounds[I]=Candidates[I];
    return Result;
}
struct FArcheryProgress { bool Near=true; int Resolved=0,Hits=0,Goal=0,FetchSeconds=0; };
inline FArcheryProgress ArcheryProgress(const SoraArcheryRules::FState& S)
{
    int Hits=0; for(unsigned B=1;B<=4;B<<=1) Hits+=(S.HangingHits&B)!=0;
    return {S.Stage==SoraArcheryRules::EStage::Near,S.Resolved,
        S.Stage==SoraArcheryRules::EStage::Near?S.Hits:Hits,
        S.Stage==SoraArcheryRules::EStage::Near?SoraArcheryRules::RequiredHits:3,(S.FetchRemainingMs+999)/1000};
}
}
