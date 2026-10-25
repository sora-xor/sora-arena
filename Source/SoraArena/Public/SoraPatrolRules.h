#pragma once

// A scheduled patrol advances only after a real arrival. A missed deadline
// stays late; elapsed time cannot skip an obstructed station or finish a lap.
namespace SoraPatrolRules
{
struct FLoop
{
    long long ElapsedMs=0,LastCycleMs=0;
    int Legs=0,Cycles=0;
    unsigned Visited=0;
    bool Arrived=false,Overdue=false;
};
constexpr bool Valid(int Count,int PeriodMs,int DwellMs)
{ return Count>=2&&Count<=32&&PeriodMs>=Count&&DwellMs>=0&&DwellMs<PeriodMs/Count; }
constexpr int Target(const FLoop& Loop,int Count)
{ return Count>0?(Loop.Legs+1)%Count:0; }
constexpr long long Deadline(const FLoop& Loop,int Count,int PeriodMs)
{ return Count>0?(static_cast<long long>(Loop.Legs)+1)*PeriodMs/Count:0; }
constexpr void Step(FLoop& Loop,int Count,int PeriodMs,int DeltaMs,bool Reached)
{
    if(!Valid(Count,PeriodMs,0)||DeltaMs<=0) return;
    Loop.ElapsedMs+=DeltaMs;
    const long long Due=Deadline(Loop,Count,PeriodMs);
    if(!Loop.Arrived&&Loop.ElapsedMs>Due) Loop.Overdue=true;
    Loop.Arrived=Reached;
    if(!Reached) return;
    Loop.Visited|=1u<<Target(Loop,Count);
    if(Loop.ElapsedMs<Due) return;
    ++Loop.Legs; Loop.Arrived=false;
    if(Loop.Legs==Count)
    {
        ++Loop.Cycles; Loop.LastCycleMs=Loop.ElapsedMs;
        Loop.ElapsedMs=0; Loop.Legs=0;
    }
}
}
