#pragma once
#include <cmath>
// Chapter 07 §2.3/§6.10, centimetres and gameplay milliseconds. Gust schedule
// entries are onset-to-onset intervals; the warning precedes each onset.
namespace SoraRidgeRules
{
constexpr int Length=18000, Fall=200, WarningMs=1000, HoldMs=2500;
constexpr int Schedule[5]={11000,9000,14000,10000,12000};
constexpr int CycleMs=56000, FallCost=25, Recoveries=3;
constexpr int NetRootMs=1200, DroneDisruptionMs=600;
// Chapter 07 specifies drone drift but not its speed. This is provisional.
constexpr int DroneDriftCmS=120;
struct FWind { int Speed=8, Serial=0; bool Warning=false,Gust=false; int GustAgeMs=-1; };
inline FWind At(int Ms)
{
    FWind W; if(Ms<0) return W;
    const int Cycle=Ms/CycleMs, T=Ms%CycleMs;
    // The previous cycle's final gust carries across the cycle boundary.
    if(Cycle>0&&T<HoldMs) { W.Speed=18; W.Gust=true; W.GustAgeMs=T; W.Serial=Cycle*5; }
    int Onset=0;
    for(int I=0;I<5;++I)
    {
        Onset+=Schedule[I];
        if(T>=Onset-WarningMs&&T<Onset) { W.Warning=true; W.Serial=Cycle*5+I+1; }
        if(T>=Onset&&T<Onset+HoldMs) { W.Speed=18; W.Gust=true; W.GustAgeMs=T-Onset; W.Serial=Cycle*5+I+1; }
    }
    return W;
}
inline double CrownHalf(double X) { return X>=6000&&X<=12000?700:300; }
inline double Height(double X,double Y=0)
{
    const double Across=std::fmax(0.,std::abs(Y)-CrownHalf(X));
    return -Fall*X/Length-Across*std::tan(20.*3.141592653589793/180.);
}
inline bool Gap(double X,int Side) { return Side>0&&((X>=4500&&X<=5500)||(X>=9500&&X<=10500)||(X>=13500&&X<=14500)); }
inline bool Deck(double X,double Y,double Margin=0) { return X>=Margin&&X<=Length-Margin&&std::abs(Y)<=CrownHalf(X)+400-Margin; }
inline bool Cable(int Index) { return Index>=0&&Index<62&&!Gap((Index/2)*600,Index%2?1:-1); }
inline double Push(bool Crouched,bool Braced,bool Lee) { return Braced||Lee?0:Crouched?60:120; }
inline double Acceleration(int WindMps) { return 35.*WindMps; }
// Only external wind displacement is clamped. Normal movement/jump is never
// clamped and can cross every lip, including each missing-cable span.
inline double GuardedPush(double X,double Y,double Radius,double Wanted)
{
    if(!Deck(X,Y)) return 0;
    return std::fmax(0.,std::fmin(Wanted,CrownHalf(X)+400-Radius-Y));
}
}
