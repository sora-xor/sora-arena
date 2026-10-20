#pragma once
// Four live captions, measured at each available column width. Search only
// panel positions; glyph wrapping/metrics come from the caller's real font.
namespace SoraCaptionLayoutRules
{
constexpr int MaxCaptions=4,MaxRegions=8;
struct FRect { float X=0,Y=0,W=0,H=0; };
inline bool Overlaps(const FRect& A,const FRect& B,float Gap=0)
{
    // Adjacent columns are calculated through different float expressions.
    // A hundredth of a pixel is rounding tolerance, not usable text space.
    constexpr float Epsilon=.01f;
    return A.X<B.X+B.W+Gap-Epsilon&&A.X+A.W+Gap>B.X+Epsilon&&
        A.Y<B.Y+B.H+Gap-Epsilon&&A.Y+A.H+Gap>B.Y+Epsilon;
}
struct FLabelPlacement { bool Fits=false; FRect Bounds; };
inline FLabelPlacement PlaceLabel(const FRect& Label,const FRect& View,const FRect* Obstacles,int Count,float Gap)
{
    FLabelPlacement Best{false,Label}; float Distance=0.f;
    // Candidate edges are measured panel boundaries, never magic screen
    // offsets. The nearest clear position retains the full label dimensions.
    for(int XI=0;XI<=2*Count+2;++XI) for(int YI=0;YI<=2*Count+2;++YI)
    {
        FRect At=Label;
        if(XI==1) At.X=View.X;
        else if(XI==2) At.X=View.X+View.W-Label.W;
        else if(XI>2) { const auto& O=Obstacles[(XI-3)/2]; At.X=XI%2?O.X-Label.W-Gap:O.X+O.W+Gap; }
        if(YI==1) At.Y=View.Y;
        else if(YI==2) At.Y=View.Y+View.H-Label.H;
        else if(YI>2) { const auto& O=Obstacles[(YI-3)/2]; At.Y=YI%2?O.Y-Label.H-Gap:O.Y+O.H+Gap; }
        if(At.X<View.X||At.Y<View.Y||At.X+At.W>View.X+View.W||At.Y+At.H>View.Y+View.H) continue;
        bool Clear=true;
        for(int I=0;I<Count&&Clear;++I) Clear=!Overlaps(At,Obstacles[I],Gap);
        if(!Clear) continue;
        const float DX=At.X-Label.X,DY=At.Y-Label.Y,D=DX*DX+DY*DY;
        if(!Best.Fits||D<Distance) { Best={true,At}; Distance=D; if(D==0.f) return Best; }
    }
    return Best;
}
struct FPlan { bool Fits=false; int Region[MaxCaptions]={}; FRect Bounds[MaxCaptions]={}; };
inline bool Search(int Index,int Count,const FRect* Regions,int RegionCount,
    const float (&Heights)[MaxCaptions][MaxRegions],float Gap,FPlan& Plan)
{
    if(Index==Count) return true;
    for(int R=0;R<RegionCount;++R)
    {
        const auto& Region=Regions[R];
        FRect At{Region.X,Region.Y,Region.W,Heights[Index][R]};
        if(At.W<=0||At.H<=0) continue;
        // A wider region may share space with the two narrower columns.
        // Advance past earlier panels until this candidate is truly clear.
        for(int Pass=0;Pass<Index+1;++Pass)
            for(int Prior=0;Prior<Index;++Prior)
                if(Overlaps(At,Plan.Bounds[Prior],Gap)) At.Y=Plan.Bounds[Prior].Y+Plan.Bounds[Prior].H+Gap;
        if(At.Y+At.H>Region.Y+Region.H+.01f) continue;
        Plan.Region[Index]=R; Plan.Bounds[Index]=At;
        if(Search(Index+1,Count,Regions,RegionCount,Heights,Gap,Plan)) return true;
    }
    return false;
}
inline FPlan Arrange(int Count,const FRect* Regions,int RegionCount,
    const float (&Heights)[MaxCaptions][MaxRegions],float Gap)
{
    FPlan Plan;
    if(Count<0||Count>MaxCaptions||RegionCount<0||RegionCount>MaxRegions) return Plan;
    Plan.Fits=Search(0,Count,Regions,RegionCount,Heights,Gap,Plan);
    return Plan;
}
}
