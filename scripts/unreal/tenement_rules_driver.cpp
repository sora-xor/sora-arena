#include "SoraTenementRules.h"
#include "SoraTerminalChargeRules.h"
#include "SoraNoticeSquareRules.h"
#include "SoraLanternWorkshopRules.h"
#include "SoraTenementDefenseRules.h"
#include "SoraTenementFindRules.h"
#include "SoraTenementQueueRules.h"
#include <cassert>
#include <iomanip>
#include <iostream>
#include <limits>

int main()
{
    namespace F=SoraTenementFindRules;
    for(int I=0;I<F::Count;++I)
    {
        const auto P=F::Points[I];
        assert(F::WithinReach(I,true,-2800,P.Y,2.15));
        assert(F::WithinReach(I,true,P.X+F::ReachCm,P.Y,0));
        assert(!F::WithinReach(I,true,P.X+F::ReachCm+.01,P.Y,0));
        assert(!F::WithinReach(I,false,-2800,P.Y,2.15));
        for(double Z:{-700.,-8.01,8.01,300.})assert(!F::WithinReach(I,true,-2800,P.Y,Z));
        assert(!F::WithinReach(I,true,std::numeric_limits<double>::quiet_NaN(),P.Y,0));
    }
    assert(!F::WithinReach(-1,true,0,0,0)&&!F::WithinReach(2,true,0,0,0));
    namespace D=SoraTenementDefenseRules;
    for(double Z:{2.15,24.65,47.15})assert(D::SupplyReach(true,-2365,3660,Z));
    assert(!D::SupplyReach(false,-2365,3660,24.65));
    assert(!D::SupplyReach(true,-2250,3660,2.15));
    assert(!D::SupplyReach(true,-2365,3499.99,2.15));
    assert(!D::SupplyReach(true,-2365,3660,-700));
    assert(!D::SupplyReach(true,-2365,3660,50.01));
    assert(!D::SupplyReach(true,std::numeric_limits<double>::quiet_NaN(),3660,2.15));
    // Court, alley, rounded capsule corners, street, upper air and shaft.
    assert(D::InKitchen(-2300,3500,90.15,34,88));
    assert(D::InKitchen(-2800,2250,90.15,34,88));
    assert(!D::InKitchen(-2800,2100,90.15,34,88));
    assert(!D::InKitchen(-2800,450,90.15,34,88));
    assert(D::InKitchen(-2800,3050,600,38,38));
    assert(D::InKitchen(-2800,3050,638,38,38));
    assert(!D::InKitchen(-2800,3050,638.01,38,38));
    assert(D::InKitchen(-2166,3000,90.15,34,88));
    assert(!D::InKitchen(-2166,3634,90.15,34,88));
    assert(!D::InKitchen(-3100,3200,-609.85,34,88));
    D::FPoint Invalid;
    for(int W:{-1,3})assert(!D::Spawn(W,0,0,Invalid));
    assert(!D::Spawn(0,2,0,Invalid)&&!D::Spawn(1,0,2,Invalid)&&!D::Spawn(2,0,-1,Invalid));
    std::cout<<std::setprecision(15)<<"{\"solids\":[";
    bool Comma=false;
    for(const auto& B:SoraTenementRules::Solids())
    {
        if(Comma)std::cout<<',';
        Comma=true;
        std::cout<<'['<<B.X<<','<<B.Y<<','<<B.Z<<','<<B.SX<<','<<B.SY<<','<<B.SZ<<','<<B.Yaw<<','<<int(B.Surface)<<']';
    }
    std::cout<<"],\"defense_spawns\":[";Comma=false;
    for(int W=0;W<3;++W)for(int G=0;G<D::Groups(W);++G)for(int M=0;M<D::Count(W,G);++M)
    {
        D::FPoint P;assert(D::Spawn(W,G,M,P));
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<'['<<W<<','<<G<<','<<M<<','<<P.X<<','<<P.Y<<','<<P.Z<<']';
    }
    std::cout<<"],\"defense_flight\":[";Comma=false;
    for(int M=0;M<2;++M)for(int L=0;L<D::FlightLegs;++L)
    {
        const auto P=D::FlightPoint(M,L);
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<'['<<M<<','<<L<<','<<P.X<<','<<P.Y<<','<<P.Z<<']';
    }
    std::cout<<"],\"finds\":[";
    for(int I=0;I<F::Count;++I)
    {
        const auto P=F::Points[I];if(I)std::cout<<',';
        std::cout<<'['<<P.X<<','<<P.Y<<','<<P.Z<<']';
    }
    const auto P=D::SupplyAt,S=D::SupplySize;
    std::cout<<"],\"supply\":["<<P.X<<','<<P.Y<<','<<P.Z<<','<<S.X<<','<<S.Y<<','<<S.Z<<"],\"queue_routes\":[";
    namespace Q=SoraTenementQueueRules;
    for(int I=0;I<Q::Count;++I)
    {
        const auto A=Q::Queue(I),B=Q::DoorApproach(I),C=Q::Home(I);
        if(I)std::cout<<',';
        std::cout<<"[["<<A.X<<','<<A.Y<<"],["<<B.X<<','<<B.Y<<"],["<<C.X<<','<<C.Y<<"]]";
    }
    std::cout<<"],\"notice_solids\":[";Comma=false;
    for(const auto B:SoraTerminalChargeRules::Solids)
    {
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<'['<<B.X<<','<<B.Y<<','<<B.Z<<','<<B.SX<<','<<B.SY<<','<<B.SZ<<",0,1]";
    }
    std::cout<<"],\"workshop_solids\":[";Comma=false;
    for(const auto B:SoraLanternWorkshopRules::Solids())
    {
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<'['<<B.X<<','<<B.Y<<','<<B.Z<<','<<B.SX<<','<<B.SY<<','<<B.SZ<<",0,1]";
    }
    std::cout<<"],\"street_floors\":[";Comma=false;
    for(const auto B:SoraNoticeSquareRules::StreetFloors)
    {
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<'['<<B.X<<','<<B.Y<<','<<B.Z<<','<<B.SX<<','<<B.SY<<','<<B.SZ<<",0,0]";
    }
    std::cout<<"],\"street_walls\":[";Comma=false;
    for(const auto B:SoraNoticeSquareRules::StreetWalls)
    {
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<'['<<B.X<<','<<B.Y<<','<<B.Z<<','<<B.SX<<','<<B.SY<<','<<B.SZ<<",0,1]";
    }
    std::cout<<"],\"north_walls\":[";Comma=false;
    for(const auto B:SoraNoticeSquareRules::NorthWalls)
    {
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<'['<<B.X<<','<<B.Y<<','<<B.Z<<','<<B.SX<<','<<B.SY<<','<<B.SZ<<",0,1]";
    }
    std::cout<<"],\"kept_houses\":[";Comma=false;
    for(int I=0;I<5;++I)if(SoraNoticeSquareRules::KeepLegacyHouse(I))
    {if(Comma)std::cout<<',';Comma=true;std::cout<<I;}
    std::cout<<"],\"kept_cover\":[";Comma=false;
    for(int I=0;I<12;++I)
    {
        const int X=-2300+(I%6)*900,Y=(I<6?-1:1)*(680+(I%2)*200);
        if(SoraNoticeSquareRules::KeepLegacyCover(X,Y))
        {if(Comma)std::cout<<',';Comma=true;std::cout<<'['<<X<<','<<Y<<"]";}
    }
    std::cout<<"]}\n";
}
