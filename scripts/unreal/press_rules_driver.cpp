#include "SoraPressRules.h"
#include "SoraStealthRules.h"
#include "SoraPatrolRules.h"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <initializer_list>
#include <limits>

namespace P=SoraPressRules;
int main()
{
    unsigned Jammed=0;
    for(int I=0;I<8;++I) assert(P::Running(Jammed,I));
    assert(!P::Running(Jammed,-1)&&!P::Running(Jammed,8));
    assert(!P::Jam(Jammed,-1)&&!P::Jam(Jammed,3)&&Jammed==0);
    assert(P::Jam(Jammed,1)&&!P::Jam(Jammed,1));
    for(int I=0;I<8;++I) assert(P::Running(Jammed,I)==(I!=4));
    assert(P::Jam(Jammed,0)&&P::Jam(Jammed,2));
    assert(Jammed==((1u<<1)|(1u<<4)|(1u<<6)));
    for(int I:{0,2,3,5,7}) assert(P::Running(Jammed,I));
    assert(P::Masking(0)&&P::Masking(499)&&!P::Masking(500));
    assert(!P::Masking(1599)&&P::Masking(1600)&&!P::Masking(-1));
    assert(P::MaskedBetween(0,1600)==500&&P::MaskedBetween(499,501)==1);
    assert(P::MaskedBetween(1599,1601)==1&&P::MaskedBetween(1600,1600)==0);
    assert(P::MaskedBetween(-400,400)==400&&P::MaskedBetween(500,400)==0);
    // Independent per-ms oracle, including long frames that cross several
    // stamps. This catches off-by-one windows and skipped cycles.
    for(int Start=0;Start<3200;Start+=13) for(int Span:{1,7,16,33,500,1600,4703})
    {
        int Expected=0;
        for(int T=Start;T<Start+Span;++T) Expected+=(T%1600)<500;
        assert(P::MaskedBetween(Start,Start+Span)==Expected);
    }
    // Every partition covers exactly the same masked duration: no sample-
    // at-frame-end shortcut, including 30/60/144 Hz and one huge tick.
    for(int Frames:{1,30,60,144,1000})
    {
        long long Total=0,Previous=0;
        for(int F=1;F<=Frames;++F)
        {
            const long long End=4800LL*F/Frames;
            Total+=P::MaskedBetween(Previous,End); Previous=End;
        }
        assert(Total==1500);
    }
    constexpr long long Long=static_cast<long long>(std::numeric_limits<int>::max())+1600;
    assert(P::MaskedBetween(Long,Long+1600)==500);
    assert(P::Scale(1500,200)==300&&P::Scale(1000,200)==200&&P::Scale(0,200)==0);
    assert(P::Scale(std::numeric_limits<int>::max(),1000)==std::numeric_limits<int>::max());
    assert(!P::LampNoticeDue(5000,-1)&&!P::LampNoticeDue(4999,0)&&P::LampNoticeDue(5000,0));
    assert(!P::LampNoticeDue(Long+4999,Long)&&P::LampNoticeDue(Long+5000,Long));
    namespace S=SoraStealthRules;
    const auto Vigil=S::Detection(1000,350,25000);
    auto Mind=S::Disturbed(S::Calm(),Vigil);
    assert(Mind.State==S::EState::Suspicious&&Mind.Awareness==350*S::AwarenessScale);
    S::FSenses None{}; None.HealthPermille=1000; None.Alarmist=true;
    Mind=S::Step(Mind,None,16,Vigil);
    assert(Mind.State==S::EState::Suspicious); // Auditors do not raise the alarm for a broken lamp.
    for(auto State:{S::EState::Search,S::EState::Alert,S::EState::Combat,S::EState::Retreat})
    {
        auto Prior=S::Enter(S::Calm(),State,700*S::AwarenessScale); Prior.StateMs=1234;
        const auto After=S::Disturbed(Prior,Vigil);
        assert(After.State==Prior.State&&After.Awareness==Prior.Awareness&&After.StateMs==Prior.StateMs);
    }
    namespace T=SoraPatrolRules;
    assert(T::Valid(8,45000,700)&&T::Valid(4,30000,0));
    assert(!T::Valid(0,45000,700)&&!T::Valid(33,45000,0)&&!T::Valid(8,45000,5625)&&!T::Valid(8,0,0));
    // Physical non-arrival for longer than a full circuit never visits a
    // station or advances a leg. Removing the obstruction still requires
    // each separate arrival; it cannot catch up by skipping stations.
    T::FLoop Blocked;
    T::Step(Blocked,8,45000,100000,false);
    assert(Blocked.Cycles==0&&Blocked.Legs==0&&Blocked.Visited==0&&Blocked.Overdue);
    for(int Leg=1;Leg<=8;++Leg)
    {
        T::Step(Blocked,8,45000,16,true);
        assert(Blocked.Cycles==(Leg==8?1:0));
        assert(Blocked.Legs==Leg%8);
    }
    assert(Blocked.LastCycleMs==100128&&Blocked.Visited==255&&Blocked.Overdue);
    // Independent arrival schedule: reaching each station 700 ms before
    // its deadline gives one circuit at 30/60/144 Hz, within one frame.
    for(int Hz:{30,60,144}) for(int Count:{4,8})
    {
        const int Period=Count==8?45000:30000;
        T::FLoop Loop; int Previous=0;
        for(int Frame=1;Loop.Cycles==0&&Frame<Hz*100;++Frame)
        {
            const int Now=1000*Frame/Hz,Dt=Now-Previous; Previous=Now;
            const long long Arrival=(static_cast<long long>(Loop.Legs)+1)*Period/Count-700;
            T::Step(Loop,Count,Period,Dt,Now>=Arrival);
        }
        assert(Loop.Cycles==1&&Loop.Visited==((1u<<Count)-1)&&!Loop.Overdue);
        assert(Loop.LastCycleMs>=Period&&Loop.LastCycleMs<=Period+1000/Hz+1);
    }
    T::FLoop Early;
    T::Step(Early,8,45000,5000,true); assert(Early.Legs==0&&Early.Visited==2);
    T::Step(Early,8,45000,0,true); assert(Early.ElapsedMs==5000&&Early.Legs==0);
    T::Step(Early,8,45000,625,true); assert(Early.Legs==1&&!Early.Overdue);
    std::cout<<"Press rules: stamp boundaries, interval partitions, jams, lamp suspicion and arrival-gated 30/45-second patrol schedules passed\n";
}
