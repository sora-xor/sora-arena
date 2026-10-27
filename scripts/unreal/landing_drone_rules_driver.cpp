#include "SoraLandingDroneRules.h"
#include "SoraMillisecondClock.h"
#include <cassert>
#include <initializer_list>
namespace R=SoraLandingDroneRules;
int main()
{
    static_assert(R::MarkMs==900&&R::LowHeightCm==250&&R::RootMs==1500&&R::Damage==5);
    R::FState S;
    assert(!R::ArriveLow(S,true)&&!R::ArriveHome(S,true));
    R::Begin(S,R::MarkMs);
    assert(R::AdvanceTimer(S,899)==0&&S.Stage==R::EStage::Mark&&S.RemainingMs==1);
    assert(!R::ArriveLow(S,true));
    assert(R::AdvanceTimer(S,0)==0&&R::AdvanceTimer(S,-1)==0&&S.RemainingMs==1);
    assert(R::AdvanceTimer(S,1)==0&&S.Stage==R::EStage::Descending&&S.Releases==0);
    // Time is not contact. A blocked descent never releases, however late.
    assert(R::AdvanceTimer(S,100000)==100000&&!R::ArriveLow(S,false)&&S.Releases==0);
    assert(R::ArriveLow(S,true)&&S.Releases==1&&!R::ArriveLow(S,true));
    assert(R::AdvanceTimer(S,R::LowMs-1)==0&&S.Stage==R::EStage::Low);
    assert(R::AdvanceTimer(S,2)==1&&S.Stage==R::EStage::Ascending);
    assert(!R::ArriveHome(S,false)&&S.Stage==R::EStage::Ascending);
    assert(R::ArriveHome(S,true)&&S.Stage==R::EStage::Idle&&S.Releases==1);
    assert(!R::ArriveLow(S,true)&&R::AdvanceTimer(S,100000)==0);
    // Easy/normal/hard durations are supplied by the existing difficulty
    // policy. They cannot accidentally inherit the generic 800 ms lock.
    for(int Windup:{765,900,1170})
    {
        R::Begin(S,Windup);
        assert(R::AdvanceTimer(S,Windup-1)==0&&S.Stage==R::EStage::Mark);
        assert(R::AdvanceTimer(S,51)==50&&S.Stage==R::EStage::Descending);
        assert(!R::ArriveLow(S,false)&&S.Releases==0);
    }
    // Interruption in every stage discards the remaining old attack.
    for(auto Stage:{R::EStage::Mark,R::EStage::Descending,R::EStage::Low,R::EStage::Ascending})
    {
        S.Stage=Stage; S.RemainingMs=100;
        R::Cancel(S);
        assert(S.Stage==R::EStage::Idle&&!R::ArriveLow(S,true));
        R::Begin(S,900);
        assert(S.Releases==0&&R::AdvanceTimer(S,899)==0&&S.Stage==R::EStage::Mark);
    }
    assert(R::WakizashiFinishes(true,true,4,39));
    assert(!R::WakizashiFinishes(false,true,4,39));
    assert(!R::WakizashiFinishes(true,false,4,39));
    assert(!R::WakizashiFinishes(true,true,0,39));
    assert(!R::WakizashiFinishes(true,true,4,0));
    assert(!R::WakizashiFinishes(true,true,4,-1));
    // Fractional frame remainders survive; pausing contributes no time.
    FSoraMillisecondClock Clock;
    int Total=0;
    for(int I=0;I<90;++I) { Total+=Clock.Advance(.0075); Total+=Clock.Advance(.0025); }
    assert(Total==900);
    assert(Clock.Advance(0)==0&&Clock.Advance(-1)==0);
}
