#pragma once
#include <cmath>
#include <vector>

// Summit collision and seizure timing, shared by runtime and host checks.
namespace SoraSummitRules
{
constexpr int RadiusCm=1800,TileCm=300,GridRadius=RadiusCm/TileCm;
constexpr int MarkMs=1500,VoidMs=5000,RestoreMs=1000,CadenceMs=9000;
constexpr int PhaseTransitionMs(int Phase) { return Phase==1?2000:Phase==2?2500:0; }
constexpr bool PhaseTransitionReady(int Phase,int ElapsedMs,bool OnDais)
{ return ElapsedMs>=PhaseTransitionMs(Phase)&&(Phase!=1||OnDais); }
constexpr double Pi=3.14159265358979323846;
struct FPoint { double X=0,Y=0; };
using FPolygon=std::vector<FPoint>;
enum class EStage { Intact,Marked,Void,Restoring };
inline FPolygon Tile(int X,int Y)
{
    // Clip a 72-sided disc to the tile's 300 cm square. Boundary tiles
    // follow the 36 m disc instead of extending square corners beyond it.
    FPolygon Poly;
    for(int N=0;N<72;++N) Poly.push_back({RadiusCm*std::cos(N*2*Pi/72),RadiusCm*std::sin(N*2*Pi/72)});
    for(int Side=0;Side<4;++Side)
    {
        FPolygon Out;
        const bool Vertical=Side<2;
        const double Bound=(Vertical?X:Y)*TileCm+(Side%2?TileCm:0);
        const auto Distance=[&](FPoint P) { return ((Vertical?P.X:P.Y)-Bound)*(Side%2?-1:1); };
        for(int N=0;N<int(Poly.size());++N)
        {
            const FPoint A=Poly[N],B=Poly[(N+1)%Poly.size()];
            const double DA=Distance(A),DB=Distance(B);
            if(DA>=-1e-7) Out.push_back(A);
            if((DA>=0)!=(DB>=0))
            {
                const double T=DA/(DA-DB);
                Out.push_back({A.X+(B.X-A.X)*T,A.Y+(B.Y-A.Y)*T});
            }
        }
        Poly=Out;
    }
    // Tangencies may produce repeated vertices or zero-area fragments.
    FPolygon Unique;
    for(const auto P:Poly)
        if(Unique.empty()||std::hypot(P.X-Unique.back().X,P.Y-Unique.back().Y)>.01) Unique.push_back(P);
    if(Unique.size()>1&&std::hypot(Unique.front().X-Unique.back().X,Unique.front().Y-Unique.back().Y)<.01) Unique.pop_back();
    double Area=0;
    for(int N=0;N<int(Unique.size());++N) Area+=Unique[N].X*Unique[(N+1)%Unique.size()].Y-Unique[N].Y*Unique[(N+1)%Unique.size()].X;
    return Area>1?Unique:FPolygon{};
}
constexpr bool Selected(int Pattern,int X,int Y,int HeroX,int HeroY)
{
    const double CX=(X+.5)*TileCm,CY=(Y+.5)*TileCm,R2=CX*CX+CY*CY;
    if(Pattern==0) return ((X+Y)%3+3)%3==0;
    if(Pattern==1) return R2>=800*800&&R2<=1200*1200;
    // Three one-tile-wide lines lock to the hero at the mark: row,
    // column and rising diagonal. They never track during the warning.
    return X==HeroX||Y==HeroY||X-Y==HeroX-HeroY;
}
constexpr EStage Stage(int Elapsed,int Warning=MarkMs)
{
    return Elapsed<0?EStage::Intact:Elapsed<Warning?EStage::Marked:
        Elapsed<Warning+VoidMs?EStage::Void:Elapsed<Warning+VoidMs+RestoreMs?EStage::Restoring:EStage::Intact;
}
constexpr bool Solid(EStage State) { return State==EStage::Intact||State==EStage::Marked; }
inline double Offset(int Elapsed,int Warning=MarkMs)
{
    const auto State=Stage(Elapsed,Warning);
    if(State==EStage::Void)
    {
        const double T=(Elapsed-Warning)/1000.0,Drop=490*T*T;
        return -std::fmin(1200,Drop);
    }
    if(State==EStage::Restoring) return -400*(1-double(Elapsed-Warning-VoidMs)/RestoreMs);
    return 0;
}
// The finale hold is transient. Any interruption requires a fresh press;
// neither a released partial cut nor an input held from afar can bank time.
struct FCut { int HeldMs=0; bool Active=false,NeedsRelease=false; };
constexpr void Interrupt(FCut& State) { State={0,false,true}; }
constexpr bool Begin(FCut& State,bool Eligible,bool Held)
{
    if(!Eligible||!Held||State.NeedsRelease||State.Active) return false;
    State={0,true,false}; return true;
}
constexpr bool TickCut(FCut& State,int DeltaMs,bool Eligible,bool Held,int RequiredMs)
{
    if(!Held) { State={}; return false; }
    if(!Eligible) { Interrupt(State); return false; }
    if(!State.Active||RequiredMs<=0||DeltaMs<=0) return false;
    State.HeldMs+=DeltaMs;
    if(State.HeldMs<RequiredMs) return false;
    Interrupt(State); return true;
}

}
