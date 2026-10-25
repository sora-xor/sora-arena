#include "SoraRelayRules.h"
#include <cassert>
#include <climits>
#include <iostream>
using namespace SoraRelayRules;

static bool Same(const FState& A,const FState& B)
{
    return A.PhaseMs==B.PhaseMs&&A.FanLockedMs==B.FanLockedMs&&
        A.NodesLockedMs==B.NodesLockedMs&&A.ReinforcementsInMs==B.ReinforcementsInMs&&
        A.Disabled==B.Disabled&&A.HeldNode==B.HeldNode&&A.HeldMs==B.HeldMs&&A.Detected==B.Detected;
}

int main()
{
    // Every millisecond of a full rotation: each node's distinct angular
    // position still receives exactly eight seconds exposed and four safe.
    for(int Node=0;Node<NodeCount;++Node)
    {
        int ExposedCount=0,SafeCount=0;
        for(int Phase=0;Phase<PeriodMs;++Phase)
        {
            FState S; S.PhaseMs=Phase;
            if(S.Exposed(Node)) ++ExposedCount; else ++SafeCount;
        }
        assert(ExposedCount==ExposedMs&&SafeCount==GapMs);
    }
    assert(Nodes[2].Z-Nodes[0].Z==GalleryHeightCm);
    assert(NodePhaseMs[0]==6000&&NodePhaseMs[1]==0&&NodePhaseMs[2]==3000);
    for(int Bad:{INT_MIN,-1,3,INT_MAX})
    {
        FState S; const auto Before=S;
        assert(S.Begin(Bad)==EBegin::Unavailable&&Same(S,Before));
        assert(!S.Exposed(Bad)&&!S.IsDisabled(Bad)&&S.SafeRemainingMs(Bad)==0);
    }

    // Compare a large frame with a 1 ms reference for every possible start
    // instant, on every node. Check event multiplicity, not only final state.
    for(int Node=0;Node<NodeCount;++Node) for(int Phase=0;Phase<PeriodMs;++Phase)
    {
        FState Whole; Whole.PhaseMs=Phase;
        const auto Start=Whole.Begin(Node); FState Fine=Whole;
        if(Start==EBegin::Caught)
        {
            assert(Whole.FanLockedMs==2000&&Whole.HeldNode==-1);
            Whole.Advance(1999,true); assert(Whole.PhaseMs==Phase&&Whole.FanLockedMs==1);
            Whole.Advance(2,true); assert(Whole.PhaseMs==(Phase+1)%PeriodMs&&Whole.HeldNode==-1);
            continue;
        }
        assert(Start==EBegin::Started);
        const auto One=Whole.Advance(6500,true);
        int Completed=0,Caught=0;
        for(int Ms=0;Ms<6500;++Ms)
        {
            const auto Part=Fine.Advance(1,true);
            if(Part.Completed!=-1) { assert(Part.Completed==Node); ++Completed; }
            if(Part.Caught!=-1) { assert(Part.Caught==Node); ++Caught; }
        }
        assert(Same(Whole,Fine));
        assert(Completed==(One.Completed!=-1)&&Caught==(One.Caught!=-1));
        const int Safe=PeriodMs-PhaseAt(Phase,Node);
        assert((One.Completed==Node)==(Safe>=PullMs));
        assert((One.Caught==Node)==(Safe<PullMs));
        assert(Completed+Caught==1);
    }

    // Exact safe-window edges, releasing the key, losing physical reach,
    // and repeated input cannot bank a partial pull or credit it twice.
    FState S; S.PhaseMs=9000;
    assert(S.Begin(1)==EBegin::Started);
    assert(S.Begin(1)==EBegin::Unavailable);
    S.Advance(2999,true); assert(S.HeldMs==2999&&!S.IsDisabled(1));
    assert(S.Advance(1,true).Completed==1&&S.IsDisabled(1));
    assert(S.Begin(1)==EBegin::Unavailable);
    assert(S.Advance(INT_MAX,true).Completed==-1);
    for(int CancelAfter:{1,1000,2999})
    {
        S=FState{};S.PhaseMs=8000;S.Begin(1);S.Advance(CancelAfter,true);
        S.Advance(1,false);assert(S.HeldNode==-1&&S.HeldMs==0&&S.Disabled==0);
        S.Advance(30000,true);assert(S.Disabled==0);
    }
    S=FState{};S.PhaseMs=9001;S.Begin(1);
    auto Caught=S.Advance(2999,true);
    assert(Caught.Caught==1&&S.PhaseMs==0&&S.FanLockedMs==2000&&S.Disabled==0);
    S.Advance(2000,true);assert(S.PhaseMs==0&&S.FanLockedMs==0&&S.HeldNode==-1);

    // A different node can be worked while the fan is frozen if that node
    // is genuinely in the gap; the pause extends its remaining safe time.
    S=FState{}; assert(S.Begin(1)==EBegin::Caught);
    assert(S.Begin(2)==EBegin::Started);
    assert(S.Advance(3000,true).Completed==2&&S.PhaseMs==1000);

    // Detection cancels ongoing work, locks all nodes for 30 s, and releases
    // exactly one reinforcement event after 8 s. Repeat reports do not
    // restart deadlines or remove a node already pulled.
    S=FState{};S.Disabled=1;S.Begin(2);S.Advance(300,true);
    assert(S.Detect()&&S.HeldNode==-1&&S.Disabled==1);
    assert(!S.Detect());
    for(int Node=1;Node<3;++Node) assert(S.Begin(Node)==EBegin::Locked);
    assert(!S.Advance(7999,true).ReinforcementsDue&&!S.ReinforcementsReady());
    assert(S.Advance(1,true).ReinforcementsDue&&S.ReinforcementsReady());
    assert(!S.Detect()&&S.NodesLockedMs==22000);
    assert(!S.Advance(21999,true).ReinforcementsDue&&S.NodesLockedMs==1);
    assert(!S.Advance(1,true).ReinforcementsDue&&S.NodesLockedMs==0);
    assert(!S.Advance(INT_MAX,true).ReinforcementsDue);

    // Timers remain independent when the scan pauses, and survive arbitrary
    // frame partitions without a cumulative phase or deadline error.
    for(int Chunk:{1,7,16,33,500,1999,8000,30000,INT_MAX})
    {
        FState Whole;Whole.Begin(1);Whole.Detect();FState Split=Whole;
        const auto One=Whole.Advance(37001,true);int Due=0,Left=37001;
        while(Left>0) { const int Dt=Left<Chunk?Left:Chunk; Due+=Split.Advance(Dt,true).ReinforcementsDue;Left-=Dt; }
        assert(Same(Whole,Split)&&Due==1&&One.ReinforcementsDue);
        const auto Before=Split;Split.Advance(0,false);Split.Advance(-1,true);assert(Same(Split,Before));
    }
    S=FState{};
    for(int Node=0;Node<3;++Node)
    {
        S.PhaseMs=(NodePhaseMs[Node]+ExposedMs)%PeriodMs;
        assert(S.Begin(Node)==EBegin::Started&&S.Advance(PullMs,true).Completed==Node);
    }
    assert(S.AllDisabled());
    S=FState{};assert(S.Disabled==0&&!S.Detected&&S.HeldNode==-1&&!S.ReinforcementsReady());
    std::cout<<"Relay timing: all 36000 start phases, half-open completion, catches, locks, cancellation, "
                 "one reinforcement event, long frames and frame partitions pass.\n";
}
