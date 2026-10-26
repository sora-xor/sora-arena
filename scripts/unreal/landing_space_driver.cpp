#include "SoraLandingSpaceRules.h"
#include "SoraPatrolRules.h"
#include <cassert>
#include <cmath>
#include <iostream>

int main()
{
    namespace R=SoraLandingSpaceRules;
    namespace P=SoraPatrolRules;
    // A blocked station cannot be skipped at its deadline, even after a
    // whole nominal circuit. The real arrival completes it late instead.
    for(int G=0;G<2;++G)
    {
        const int Count=R::Count(G),Period=R::Period(G);
        assert(P::Valid(Count,Period,0));
        P::FLoop Blocked;
        P::Step(Blocked,Count,Period,Period*2,false);
        assert(Blocked.Legs==0&&Blocked.Cycles==0&&Blocked.Visited==0&&Blocked.Overdue);
        P::Step(Blocked,Count,Period,1,true);
        assert(Blocked.Legs==1&&Blocked.Cycles==0&&Blocked.Overdue);
        P::FLoop Clear;
        for(int I=0;I<Count;++I)
        {
            assert(P::Target(Clear,Count)==(I+1)%Count);
            // Arrival one millisecond early waits for the release time.
            P::Step(Clear,Count,Period,Period/Count-1,true);
            assert(Clear.Legs==I);
            P::Step(Clear,Count,Period,1,true);
        }
        assert(Clear.Cycles==1&&Clear.LastCycleMs==Period&&!Clear.Overdue);
        assert(Clear.Visited==((1u<<Count)-1));
        for(int I=0;I<Count;++I)
        {
            const auto A=R::Point(G,I),B=R::Point(G,(I+1)%Count);
            // Each scheduled leg is physically possible at the catalog's
            // 500 cm/s drone speed; this does not prove UE collision/motion.
            assert(std::hypot(double(B.X-A.X),double(B.Y-A.Y))<500.*Period/Count/1000.);
        }
    }
    std::cout<<"{\"routes\":[";
    for(int G=0;G<2;++G)
    {
        if(G)std::cout<<',';
        std::cout<<"{\"period\":"<<R::Period(G)<<",\"height\":"<<R::Height(G)<<",\"points\":[";
        for(int I=0;I<R::Count(G);++I)
        {const auto Pnt=R::Point(G,I);if(I)std::cout<<',';std::cout<<'['<<Pnt.X<<','<<Pnt.Y<<']';}
        std::cout<<"]}";
    }
    std::cout<<"],\"walls\":[";
    for(int I=0;I<R::WallCount;++I)
    {const auto& W=R::Walls[I];if(I)std::cout<<',';std::cout<<'['<<W.X<<','<<W.Y<<','<<W.Width<<','<<W.Depth<<','<<W.Height<<']';}
    std::cout<<"],\"puddles\":[";
    for(int I=0;I<6;++I)
    {const auto& Q=R::Puddles[I];if(I)std::cout<<',';std::cout<<'['<<Q.X<<','<<Q.Y<<']';}
    std::cout<<"],\"canal_cm\":["<<R::ZoneMinX<<','<<R::CanalMinY<<','<<R::MaxX<<','<<R::MinY
        <<"],\"water_z_cm\":"<<R::WaterZ<<",\"bed_z_cm\":"<<R::BedZ
        <<",\"bridge_cm\":["<<R::BridgeX<<','<<R::BridgeClearance<<"]}\n";
}
