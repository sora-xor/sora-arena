#pragma once

// Chapter 6 L3 / b04. One owner advances this clock in active gameplay time.
// Input, reach, line of sight, suspicion and spawning belong to the runtime;
// this reducer returns their events without depending on Unreal's tick order.
namespace SoraRelayRules
{
constexpr int NodeCount=3, PeriodMs=12000, ExposedMs=8000, GapMs=4000;
constexpr int PullMs=3000, CaughtSuspicionPermille=600, FanLockMs=2000;
constexpr int NodesLockMs=30000, ReinforcementDelayMs=8000, ReinforcementCount=2;
constexpr int LampNoticeMs=5000, GalleryHeightCm=400, GalleryWidthCm=180;
struct FPoint { int X,Y,Z; };
constexpr FPoint Nodes[NodeCount]={{920,500,120},{1080,500,120},{1000,580,520}};
constexpr FPoint Work[NodeCount]={{800,500,0},{1200,500,0},{1000,690,400}};
// Positive rotation starts at east. Each node has the same eight-second
// exposure and four-second gap, offset by its angle around the column.
constexpr int NodePhaseMs[NodeCount]={6000,0,3000};
constexpr bool ValidNode(int Node) { return Node>=0&&Node<NodeCount; }
constexpr int PhaseAt(int Phase,int Node)
{ return ValidNode(Node)?(Phase-NodePhaseMs[Node]+PeriodMs)%PeriodMs:0; }

enum class EBegin { Unavailable, Locked, Started, Caught };
struct FStep
{
    int Completed=-1;
    int Caught=-1;
    int EventAtMs=0;
    bool ReinforcementsDue=false;
};

struct FState
{
    int PhaseMs=0;
    int FanLockedMs=0;
    int NodesLockedMs=0;
    int ReinforcementsInMs=-1; // Not detected yet.
    unsigned Disabled=0;
    int HeldNode=-1;
    int HeldMs=0;
    bool Detected=false;

    bool IsDisabled(int Node) const
    { return ValidNode(Node)&&(Disabled&(1u<<Node))!=0; }
    bool AllDisabled() const { return Disabled==7u; }
    bool Exposed(int Node) const
    { return ValidNode(Node)&&PhaseAt(PhaseMs,Node)<ExposedMs; }
    int SafeRemainingMs(int Node) const
    { return !ValidNode(Node)||Exposed(Node)?0:FanLockedMs+PeriodMs-PhaseAt(PhaseMs,Node); }
    bool ReinforcementsReady() const { return Detected&&ReinforcementsInMs==0; }
    void Cancel() { HeldNode=-1; HeldMs=0; }

    EBegin Begin(int Node)
    {
        if(!ValidNode(Node)||IsDisabled(Node)||HeldNode!=-1) return EBegin::Unavailable;
        if(NodesLockedMs>0) return EBegin::Locked;
        if(Exposed(Node))
        {
            // Keep the actual heading. Locking does not jump to a different
            // scan phase, and a held input never restarts a caught pull.
            FanLockedMs=FanLockMs;
            return EBegin::Caught;
        }
        HeldNode=Node; HeldMs=0;
        return EBegin::Started;
    }

    bool Detect(int AgeMs=0)
    {
        if(Detected) return false;
        const int Age=AgeMs<0?0:AgeMs;
        Detected=true; NodesLockedMs=Age>=NodesLockMs?0:NodesLockMs-Age;
        ReinforcementsInMs=Age>=ReinforcementDelayMs?0:ReinforcementDelayMs-Age;
        Cancel();
        return true;
    }

    FStep Advance(int DeltaMs,bool HoldValid)
    {
        FStep Out;
        if(DeltaMs<=0) return Out;
        const bool WasReady=ReinforcementsReady();
        if(!HoldValid||NodesLockedMs>0) Cancel();
        int Remaining=DeltaMs;
        if(HeldNode!=-1)
        {
            const int Need=PullMs-HeldMs;
            const int Safe=SafeRemainingMs(HeldNode);
            // The interval worked is half-open: finishing exactly as the
            // fan returns completes the pull. An incomplete hold is caught
            // at that boundary, including at the end of a frame.
            if(Need<=Safe&&Need<=Remaining)
            {
                AdvanceClock(Need); Remaining-=Need;
                Out.EventAtMs=Need;
                Out.Completed=HeldNode; Disabled|=1u<<HeldNode;
                Cancel();
            }
            else if(Safe<=Remaining)
            {
                AdvanceClock(Safe); Remaining-=Safe;
                Out.EventAtMs=Safe;
                Out.Caught=HeldNode; Cancel(); FanLockedMs=FanLockMs;
            }
            else
            {
                HeldMs+=Remaining;
            }
        }
        AdvanceClock(Remaining);
        Out.ReinforcementsDue=!WasReady&&ReinforcementsReady();
        return Out;
    }

private:
    void AdvanceClock(int Ms)
    {
        const int Frozen=Ms<FanLockedMs?Ms:FanLockedMs;
        FanLockedMs-=Frozen;
        // Modulo before adding also supports a very long frame without int
        // overflow; the lock timers use subtraction only when it is safe.
        PhaseMs=(PhaseMs+(Ms-Frozen)%PeriodMs)%PeriodMs;
        NodesLockedMs=Ms>=NodesLockedMs?0:NodesLockedMs-Ms;
        if(ReinforcementsInMs>=0)
            ReinforcementsInMs=Ms>=ReinforcementsInMs?0:ReinforcementsInMs-Ms;
    }
};
}
