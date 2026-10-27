#include "SoraMarginRules.h"
#include <cassert>
#include <iostream>
#include <limits>
namespace R=SoraMarginRules;
int main()
{
    R::FState S;
    std::array<double,R::Consoles> D;
    for(int N=0;N<R::Consoles;++N) D[N]=N*N;
    assert((S.Select(D)==std::vector<int>{0,1,2}));
    D.fill(10); assert((S.Select(D)==std::vector<int>{0,1,2}));
    S.Pinned=14; assert((S.Select(D)==std::vector<int>{14,0,1}));
    S.ConsumePin(); assert(S.Pinned==-1);
    // Damage belongs to a unique selected console and serial. A duplicate
    // callback cannot become a second hit, including at the sixth loss.
    for(int Id=0;Id<7;++Id)
    {
        assert(!S.Strike(Id,100+Id)); assert(!S.Strike(Id,100+Id));
        const bool Destroyed=S.Strike(Id,200+Id);
        assert(Destroyed==(Id<6)); assert(!S.Strike(Id,200+Id));
    }
    assert(S.Destroyed==6&&S.Reinforced());
    int Live=0; for(int Id=0;Id<R::Consoles;++Id) if(S.Live(Id)) ++Live;
    assert(Live==9);
    for(int Serial=300;Serial<320;++Serial) for(int Id=0;Id<R::Consoles;++Id) assert(!S.Strike(Id,Serial));
    assert(S.Destroyed==6&&S.Hits[6]==0);
    S={}; assert(!S.Strike(-1,1)&&!S.Strike(15,1)&&!S.Strike(0,-1));
    assert(!S.Observe(2,5999)&&S.HeldMs==5999&&S.Pinned==-1);
    assert(S.Observe(2,1)&&S.Pinned==2&&!S.Observe(2,1000));
    S.Observe(-1,50); assert(S.HeldMs==0&&S.Pinned==2); // Leaving does not undo the announced next target.
    S.ConsumePin(); assert(S.Pinned==-1);
    S.Observe(3,5000); S.Observe(4,1000); assert(S.HeldMs==1000&&S.Pinned==-1);
    S.LeavePhase(); assert(S.HeldMs==0&&S.Pinned==-1&&S.Lingering==-1);
    for(int Step:{1,7,16,33,250,6000})
    {
        S={}; int Raised=0;
        for(int Time=0;Time<12000;Time+=Step) if(S.Observe(8,Step)) ++Raised;
        assert(Raised==1&&S.Pinned==8);
    }
    D.fill(std::numeric_limits<double>::infinity()); assert(S.Select(D).empty());
    D[7]=0; D[5]=1; assert((S.Select(D)==std::vector<int>{7,5}));
    for(int Warning:{1260,1500,1800})
    {
        assert(!R::Release(0,Warning-1,Warning,false));
        assert(R::Release(Warning-1,Warning,Warning,false));
        assert(R::Release(Warning-1,Warning+60000,Warning,false));
        assert(!R::Release(Warning-1,Warning+60000,Warning,true));
    }
    std::cout<<"margin rules: stable unique targets, lingering, serial idempotence, six losses/nine survivors and deadline crossings passed\n";
}
