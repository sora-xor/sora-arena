#pragma once
#include "SoraBeatRules.h"

// Chapter seven's helm: beat-local state, restored at the checkpoint start.
// Grace permits ordinary holding; after grace, decay replaces gain until the
// wheel is corrected. Each threshold alarms once, even after progress falls.
namespace SoraHelmRules
{
struct FContract
{
    int Threshold[3]={250,500,750};
    int WorkMs=2000,GraceMs=8000,DecayPermille=20;
    int DeadlineMs[3]={200000,150000,130000};
};
struct FState
{
    unsigned Raised=0,Corrected=0;
    int Pending=-1,GraceMs=0,HeldMs=0,DecayCarry=0,DeadlineMs=0;
    bool Working=false,Failed=false;
};
constexpr bool Valid(const FContract& C)
{
    return C.Threshold[0]>0&&C.Threshold[0]<C.Threshold[1]&&C.Threshold[1]<C.Threshold[2]&&C.Threshold[2]<1000&&
        C.WorkMs>0&&C.WorkMs<=60000&&C.GraceMs>=C.WorkMs&&C.GraceMs<=60000&&C.DecayPermille>0&&C.DecayPermille<=1000&&
        C.DeadlineMs[0]>0&&C.DeadlineMs[0]<=SoraBeatRules::MaxClockMs&&C.DeadlineMs[1]>0&&
        C.DeadlineMs[1]<=SoraBeatRules::MaxClockMs&&C.DeadlineMs[2]>0&&C.DeadlineMs[2]<=SoraBeatRules::MaxClockMs;
}
constexpr void Cancel(FState& S) { S.Working=false; S.HeldMs=0; }
// Millisecond stepping preserves exact threshold, grace, correction and timer
// ordering across frame partitions. At normal rates this is 16–17 iterations.
constexpr void Tick(FState& S,const FContract& C,SoraBeatRules::FTaskState& T,const SoraBeatRules::FTask& Task,
                    SoraBeatRules::FTick Step,bool Held)
{
    if(S.Failed||SoraBeatRules::TaskComplete(T,Task)||Step.DeltaMs<=0) return;
    if(!Held||S.Pending<0) Cancel(S);
    const int Count=Step.DeltaMs>60000?60000:Step.DeltaMs;
    for(int Millisecond=0;Millisecond<Count;++Millisecond)
    {
        ++T.ElapsedMs;
        if(T.ElapsedMs>=S.DeadlineMs) { S.Failed=true; Cancel(S); return; }
        const bool Overdue=S.Pending>=0&&S.GraceMs==0;
        if(S.Pending>=0)
        {
            if(S.Working&&Held&&++S.HeldMs>=C.WorkMs)
            {
                S.Corrected|=1u<<S.Pending; S.Pending=-1; S.GraceMs=0; S.DecayCarry=0; Cancel(S);
            }
            else if(S.GraceMs>0) --S.GraceMs;
        }
        if(S.Pending>=0&&Overdue)
        {
            // Progress is milliseconds; 20 permille of the complete hold / s.
            const long long Loss=S.DecayCarry+static_cast<long long>(C.DecayPermille)*Task.DurationMs;
            const int Drop=static_cast<int>(Loss/1000000);
            S.DecayCarry=static_cast<int>(Loss%1000000);
            T.Progress=T.Progress>Drop?T.Progress-Drop:0;
        }
        else if(Step.AtTask&&!Step.Contested)
        {
            const int Rate=Step.RatePermille<0?0:Step.RatePermille>1000?1000:Step.RatePermille;
            T.RateCarry+=Rate; T.Progress+=T.RateCarry/1000; T.RateCarry%=1000;
        }
        if(S.Pending<0)
            for(int Index=0;Index<3;++Index)
                if(!(S.Raised&(1u<<Index))&&static_cast<long long>(T.Progress)*1000>=static_cast<long long>(Task.DurationMs)*C.Threshold[Index])
                { S.Raised|=1u<<Index; S.Pending=Index; S.GraceMs=C.GraceMs; break; }
        // Correct all three headings before the beacon can complete.
        if(T.Progress>=Task.DurationMs)
        {
            T.Progress=S.Corrected==7u&&S.Pending<0?Task.DurationMs:Task.DurationMs-1;
            if(SoraBeatRules::TaskComplete(T,Task)) return;
        }
    }
}
}
