#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <vector>

namespace SoraMarginRules
{
constexpr int Consoles=15,HitsToDestroy=2,MaxDestroyed=6,Targets=3;
constexpr int ConsoleLengthCm=300,ConsoleHeightCm=110,ConsoleDepthCm=80;
constexpr int EveryMs=7000,WarningMs=1500,LingerMs=6000,RadiusCm=250,Damage=60;
struct FState
{
    std::array<int,Consoles> Hits{};
    std::array<int,Consoles> LastSerial=[] { std::array<int,Consoles> A{}; A.fill(-1); return A; }();
    int Destroyed=0,Lingering=-1,HeldMs=0,Pinned=-1;
    bool Live(int Id) const { return Id>=0&&Id<Consoles&&Hits[Id]<HitsToDestroy; }
    bool Reinforced() const { return Destroyed>=MaxDestroyed; }
    bool Strike(int Id,int Serial)
    {
        if(!Live(Id)||Reinforced()||Serial<0||LastSerial[Id]==Serial) return false;
        LastSerial[Id]=Serial;
        if(++Hits[Id]<HitsToDestroy) return false;
        ++Destroyed; return true;
    }
    void LeavePhase() { Lingering=-1; HeldMs=0; Pinned=-1; }
    bool Observe(int Id,int DtMs)
    {
        if(!Live(Id)) { Lingering=-1; HeldMs=0; return false; }
        if(Lingering!=Id) { Lingering=Id; HeldMs=0; }
        const int Before=HeldMs;
        HeldMs=std::min(LingerMs,HeldMs+std::clamp(DtMs,0,LingerMs));
        if(Before<LingerMs&&HeldMs>=LingerMs) { Pinned=Id; return true; }
        return false;
    }
    void ConsumePin() { if(Pinned>=0) { Pinned=-1; HeldMs=0; } }
    // Distances are actual positions on the listed deck. Stable IDs settle ties.
    std::vector<int> Select(const std::array<double,Consoles>& Distances) const
    {
        std::vector<int> Order;
        for(int Id=0;Id<Consoles;++Id) if(Live(Id)&&std::isfinite(Distances[Id])) Order.push_back(Id);
        std::sort(Order.begin(),Order.end(),[&](int A,int B)
        { if(A==B) return false; if(A==Pinned||B==Pinned) return A==Pinned; return Distances[A]!=Distances[B]?Distances[A]<Distances[B]:A<B; });
        if(Order.size()>Targets) Order.resize(Targets);
        return Order;
    }
};
// Crossing the boundary must release once even when a frame skips over its
// exact millisecond. This is deliberately separate from generic ZoneAt.
inline bool Release(double BeforeMs,double AfterMs,int ActualWarningMs,bool Released)
{ return !Released&&BeforeMs<ActualWarningMs&&AfterMs>=ActualWarningMs; }
}
