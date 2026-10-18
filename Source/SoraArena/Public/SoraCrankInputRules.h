#pragma once
// Transient input, deliberately outside checkpoint/task progress. A physical
// press starts work; merely arriving while holding Interact never starts it.
namespace SoraCrankInputRules
{
struct FState { bool Active=false; bool NeedsRelease=false; int Credit=0; };
constexpr void Stop(FState& State) { State.Active=false; State.NeedsRelease=true; State.Credit=0; }
constexpr bool Begin(FState& State, bool Eligible)
{
    if (!Eligible || State.NeedsRelease) return false;
    State.Active=true; State.Credit=0; return true;
}
constexpr bool Tick(FState& State,int DeltaMs,bool Held,bool Eligible,int MilliTurnsS)
{
    if (!Held) { State={}; return false; }
    if (!Eligible) { Stop(State); return false; }
    if (!State.Active || MilliTurnsS<=0) { State.Credit=0; return false; }
    // Integer phase retains 0.6 exactly across ordinary frame sizes. A long
    // stall may issue at most one attempt: no backlog can bypass Turn's band.
    const int Delta=DeltaMs<0?0:DeltaMs>10000?10000:DeltaMs;
    State.Credit+=Delta*MilliTurnsS;
    if (State.Credit<1000000) return false;
    State.Credit%=1000000;
    return true;
}
// One L+R cycle, with a neutral return between edges. Hysteresis prevents
// analog stick noise or a held key from generating repeated treads.
struct FTreads { bool RightNext=false; int LatchedSide=0; };
constexpr int Side(int Axis) { return Axis<=-500?-1:Axis>=500?1:0; }
constexpr void BeginTreads(FTreads& State,int Axis) { State={false,Side(Axis)}; }
constexpr bool Tread(FTreads& State,int Axis)
{
    if(Axis>=-200&&Axis<=200) { State.LatchedSide=0; return false; }
    const int Press=Side(Axis);
    if(!Press||State.LatchedSide) return false;
    State.LatchedSide=Press;
    if(Press<0) { State.RightNext=true; return false; }
    const bool Cycle=State.RightNext;
    State.RightNext=false;
    return Cycle;
}
}
