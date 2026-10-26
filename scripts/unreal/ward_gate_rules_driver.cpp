#include "SoraWardGateRules.h"
#include "SoraLandingSpaceRules.h"
#include "SoraPatrolRules.h"
#include <cassert>
#include <iostream>

int main()
{
    namespace R=SoraWardGateRules;
    namespace P=SoraPatrolRules;
    for(int G:{1,4})
    {
        P::FLoop Loop,Blocked;
        const int Count=R::Count(G),Period=R::Periods[G];
        assert(P::Valid(Count,Period,0));
        for(int I=0;I<Count;++I)
        {
            const int Wait=int(P::Deadline(Loop,Count,Period)-Loop.ElapsedMs);
            P::Step(Loop,Count,Period,Wait-1,true);
            assert(Loop.Legs==I&&Loop.Cycles==0);
            P::Step(Loop,Count,Period,1,true);
        }
        assert(Loop.Cycles==1&&Loop.LastCycleMs==Period&&!Loop.Overdue);
        P::Step(Blocked,Count,Period,2*Period,false);
        assert(Blocked.Cycles==0&&Blocked.Legs==0&&Blocked.Overdue);
    }
    assert(R::CrossesScanner(-6500,0,88,-6000,0,88));
    assert(R::CrossesScanner(-6000,0,88,-6500,0,88));
    assert(R::CrossesScanner(-6220,0,88,-6220,0,88));
    assert(!R::CrossesScanner(-6300,0,88,-6245,0,88));
    // A real 34 cm body reaches the sensor before its centre reaches the
    // closed leaf. The centre-only test above intentionally misses it.
    assert(R::CrossesScanner(-6300,0,90,-6245,0,90,34,88));
    assert(!R::CrossesScanner(-6400,135,46,-6000,135,46,34,44));
    assert(!R::CrossesScanner(-6400,-650,-44,-6000,-650,-44,34,44));
    assert(!R::CrossesScanner(-6400,0,410,-6000,0,410,34,88));
    assert(!R::CrossesScanner(-6300,500,90,-6300,-500,90,34,88));
    assert(!R::CrossesScanner(-6300,90,90,-6265,90,90,34,88));
    assert(R::CrossesScanner(-6300,90,90,-6264,90,90,34,88));
    std::cout<<"{\"routes\":[";
    for(int G=0;G<5;++G)
    {
        if(G)std::cout<<',';
        std::cout<<"{\"period\":"<<R::Periods[G]<<",\"points\":[";
        for(int I=0;I<R::Count(G);++I)
        {const auto Q=R::Point(G,I);if(I)std::cout<<',';std::cout<<'['<<Q.X<<','<<Q.Y<<']';}
        std::cout<<"]}";
    }
    std::cout<<"],\"ground\":[";bool Comma=false;
    for(const auto& S:R::Ground)
    {
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<"[\""<<S.Name<<"\","<<S.X0<<','<<S.Y0<<','<<S.X1<<','<<S.Y1<<','<<S.Top<<']';
    }
    std::cout<<"],\"solids\":[";Comma=false;
    for(const auto& S:R::Solids)
    {
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<"[\""<<S.Name<<"\","<<S.X<<','<<S.Y<<','<<S.Z<<','<<S.Width<<','<<S.Depth<<','<<S.Height<<']';
    }
    std::cout<<"],\"landing_walls\":[";Comma=false;
    for(const auto& W:SoraLandingSpaceRules::Walls)
    {
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<'['<<W.X<<','<<W.Y<<','<<W.Width<<','<<W.Depth<<','<<W.Height<<']';
    }
    std::cout<<"]}\n";
}
