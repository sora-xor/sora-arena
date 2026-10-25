#pragma once
#include <algorithm>
#include <cstdint>

// ch05.b15: integral world-time exposure, independent of frame rate. The
// residual burn uses the sole authored player rate (an explicit implementation
// interpretation); it refreshes without stacking or double-charging contact.
namespace SoraMoltenRules
{
constexpr int CycleMs=12000, WarningMs=2000, FlowMs=5000, BurnMs=2000;
constexpr int PlayerDps=35, EnemyDps=60, Channels=4;
enum class EPhase { Warning, Flow, Cooling };
enum class EBody { Player, Enemy, Automaton };
struct FSpan { int Begin=0,End=0; };
struct FBody { int BurnLeftMs=0,Remainder=0; };
struct FResult { int Damage=0; bool Destroy=false; int ContactMs=0; };
inline EPhase Phase(int Clock)
{
    const int T=Clock%CycleMs;
    return T<WarningMs?EPhase::Warning:T<WarningMs+FlowMs?EPhase::Flow:EPhase::Cooling;
}
// Foot-point segment against a strip; airborne/raised bodies supply no spans.
inline bool Cross(double X0,double Y0,double X1,double Y1,double MinX,double MinY,
                  double MaxX,double MaxY,int Dt,FSpan& Out)
{
    double A=0,B=1;
    const auto Axis=[&](double P,double D,double Lo,double Hi)
    {
        if(D==0) return P>=Lo&&P<=Hi;
        double U=(Lo-P)/D,V=(Hi-P)/D;
        if(U>V) std::swap(U,V);
        A=std::max(A,U); B=std::min(B,V); return A<B;
    };
    if(Dt<=0||!Axis(X0,X1-X0,MinX,MaxX)||!Axis(Y0,Y1-Y0,MinY,MaxY)) return false;
    Out={int(A*Dt+.5),int(B*Dt+.5)}; return Out.End>Out.Begin;
}
inline FResult Tick(FBody& Body,EBody Kind,int Clock,int Dt,const FSpan* Spans,int Count)
{
    FResult Out;
    if(Dt<=0) return Out;
    int At=0;
    std::int64_t MilliDamage=Body.Remainder;
    while(At<Dt)
    {
        const int T=int((std::int64_t(Clock)+At)%CycleMs);
        const int Boundary=T<WarningMs?WarningMs:T<WarningMs+FlowMs?WarningMs+FlowMs:CycleMs;
        int End=At+std::min(Dt-At,Boundary-T);
        bool Contact=false;
        for(int I=0;I<Count;++I)
        {
            Contact|=At>=Spans[I].Begin&&At<Spans[I].End;
            if(Spans[I].Begin>At) End=std::min(End,Spans[I].Begin);
            if(Spans[I].End>At) End=std::min(End,Spans[I].End);
        }
        const int Step=End-At;
        const bool Flow=Contact&&T>=WarningMs&&T<WarningMs+FlowMs;
        if(Flow)
        {
            Out.ContactMs+=Step;
            if(Kind==EBody::Automaton) Out.Destroy=true;
            else MilliDamage+=std::int64_t(Step)*(Kind==EBody::Player?PlayerDps:EnemyDps);
            if(Kind==EBody::Player) Body.BurnLeftMs=BurnMs;
        }
        else if(Kind==EBody::Player)
        {
            const int Burn=std::min(Step,Body.BurnLeftMs);
            MilliDamage+=std::int64_t(Burn)*PlayerDps;
            Body.BurnLeftMs-=Burn;
        }
        At=End;
    }
    Out.Damage=int(MilliDamage/1000); Body.Remainder=int(MilliDamage%1000);
    return Out;
}
}
