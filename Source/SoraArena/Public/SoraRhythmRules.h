#pragma once
#include "SoraBeatRules.h"
// A cue clock and a single phrase in flight. Completed phrases/picks and
// fractional assisted production live in the task; this input state never
// survives departure, interruption or a checkpoint.
namespace SoraRhythmRules
{
using namespace SoraBeatRules;
struct FState
{
    int Step=-1, StartedMs=0, DueMs=0, LastTickMs=0, Attempts=0, Hits=0;
    bool Answered=false, Hit=false, Assisted=false;
};
constexpr bool Supported(const FTaskState& TaskState,const FTask& Task)
{
    return Task.Goal==EGoal::Steps&&TaskState.Step>=0&&TaskState.Step<MaxSteps&&TaskState.Step<Task.StepCount&&Task.Steps[TaskState.Step].PhraseStrikes>0;
}
constexpr bool Active(const FState& State,const FTaskState& TaskState,const FTask& Task)
{
    return Supported(TaskState,Task)&&State.Step==TaskState.Step;
}
constexpr bool Begin(FState& State,const FTaskState& TaskState,const FTask& Task)
{
    if(!Supported(TaskState,Task)) return false;
    State={}; State.Step=TaskState.Step; State.StartedMs=TaskState.ElapsedMs;
    State.LastTickMs=TaskState.ElapsedMs;
    State.DueMs=TaskState.ElapsedMs+Task.Steps[State.Step].BeatMs;
    return true;
}
constexpr int Cue(const FState& State,const FTaskState& TaskState,const FTask& Task)
{
    return Active(State,TaskState,Task)?(TaskState.ElapsedMs-State.StartedMs)/Task.Steps[State.Step].BeatMs:-1;
}
constexpr bool Strike(FState& State,const FTaskState& TaskState,const FTask& Task,bool Assisted=false)
{
    if(!Active(State,TaskState,Task)||State.Answered) return false;
    const int Off=TaskState.ElapsedMs-State.DueMs;
    const int Tolerance=Task.Steps[State.Step].ToleranceMs;
    State.Answered=true; State.Hit=Off>=-Tolerance&&Off<=Tolerance;
    State.Assisted|=Assisted;
    return State.Hit;
}
// Resolves only a full phrase, after all eight windows (including misses).
// A failed phrase/pick leaves earlier completed units intact. At most one
// assisted response per Tick: a long stall cannot synthesize a backlog.
constexpr EStroke Tick(FState& State,FTaskState& TaskState,const FTask& Task,bool Assist,bool* AutoStruck=nullptr)
{
    if(AutoStruck) *AutoStruck=false;
    if(!Active(State,TaskState,Task)) return EStroke::Refused;
    const FStep& Step=Task.Steps[State.Step];
    if(Assist&&!State.Answered&&State.LastTickMs<State.DueMs&&TaskState.ElapsedMs>=State.DueMs&&TaskState.ElapsedMs-State.LastTickMs<=Step.BeatMs)
    { State.Answered=true; State.Hit=true; State.Assisted=true; if(AutoStruck) *AutoStruck=true; }
    State.LastTickMs=TaskState.ElapsedMs;
    EStroke Result=EStroke::Refused;
    while(TaskState.ElapsedMs>State.DueMs+Step.ToleranceMs)
    {
        ++State.Attempts;
        if(State.Hit) ++State.Hits;
        State.Answered=false; State.Hit=false;
        State.DueMs+=Step.BeatMs;
        if(State.Attempts<Step.PhraseStrikes) continue;
        const bool Passed=State.Hits>=Step.PhrasePass;
        State.Attempts=0; State.Hits=0;
        if(Passed)
        {
            TaskState.RhythmCarry+=State.Assisted?700:1000;
            State.Assisted=false;
            Result=EStroke::Credited;
            if(TaskState.RhythmCarry>=1000)
            {
                Result=EStroke::Counted;
                TaskState.RhythmCarry-=1000;
                ++TaskState.StepDone; ++TaskState.Done;
                if(TaskState.StepDone>=Step.Count)
                {
                    ++TaskState.Step; TaskState.StepDone=0; TaskState.RhythmCarry=0; TaskState.LastActionMs=-1;
                    State={};
                    return TaskState.Step>=Task.StepCount?EStroke::Finished:EStroke::StepDone;
                }
            }
        }
        else { State.Assisted=false; Result=EStroke::Missed; }
    }
    return Result;
}
}
