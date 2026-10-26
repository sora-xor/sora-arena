#include "SoraTerminalChargeRules.h"
#include "SoraMillisecondClock.h"
#include <cassert>
#include <climits>
#include <iostream>
using namespace SoraTerminalChargeRules;
int main()
{
    FState S;assert(Fuse(S,INT_MAX)==EEvent::None);assert(Begin(S));
    assert(Work(S,3999,true)==EEvent::None&&S.Stage==EStage::Empty);
    assert(Work(S,1,true)==EEvent::Planted&&S.HeldMs==0&&!S.Working);
    assert(!Begin(S));Cancel(S,false);assert(Begin(S));
    assert(Work(S,999,true)==EEvent::None&&S.Stage==EStage::Planted);
    assert(Work(S,1,true)==EEvent::Ignited&&S.FuseAgeMs==0);
    assert(Fuse(S,19999)==EEvent::None&&S.Stage==EStage::Burning);
    assert(Fuse(S,1)==EEvent::Detonated&&S.Stage==EStage::Detonated);
    assert(Fuse(S,INT_MAX)==EEvent::None&&!Begin(S));
    for(int Part:{1,7,16,17,33,100,1000,19999,20000,INT_MAX})
    {
        S={};assert(Begin(S));Work(S,PlantMs,true);Cancel(S,false);assert(Begin(S));Work(S,LightMs,true);
        int Events=0;for(int I=0;I<20001&&S.Stage==EStage::Burning;++I)Events+=Fuse(S,Part)==EEvent::Detonated;
        assert(Events==1&&S.FuseAgeMs==FuseMs);
    }
    S={};Begin(S);Work(S,3999,true);Work(S,1,false);
    assert(S.Stage==EStage::Empty&&!S.Working&&S.HeldMs==0&&!Begin(S));
    Cancel(S,false);assert(Begin(S));assert(Work(S,-1,true)==EEvent::None&&S.HeldMs==0);
    Work(S,INT_MAX,true);Cancel(S,false);Begin(S);Work(S,999,true);Cancel(S);
    assert(S.Stage==EStage::Planted&&S.HeldMs==0);
    Cancel(S,false);Begin(S);Work(S,INT_MAX,true);Fuse(S,9000);Cancel(S,false);
    assert(S.Stage==EStage::Burning&&S.FuseAgeMs==9000&&!Begin(S));
    assert(Safe(-1600,3000,2,true,true));
    assert(!Safe(-1600,3000,2,false,true)&&!Safe(-1600,3000,2,true,false));
    assert(!Safe(-999,3000,2,true,true)&&!Safe(-1600,2899,2,true,true));
    assert(!Safe(-1600,3000,401,true,true)&&!Safe(-1600,3000,-1,true,true));
    FSoraMillisecondClock Clock;S={};S.Stage=EStage::Burning;
    for(int I=0;I<19999;++I)assert(Fuse(S,Clock.Advance(.001))==EEvent::None);
    assert(Fuse(S,Clock.Advance(.001))==EEvent::Detonated);
    std::cout<<"terminal charge boundaries, interruption, overflow, safety and partitions passed\n";
}
