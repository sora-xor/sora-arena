#include "SoraTenementRules.h"
#include "SoraTenementDefenseRules.h"
#include <cassert>
#include <iomanip>
#include <iostream>

int main()
{
    namespace D=SoraTenementDefenseRules;
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
    std::cout<<"]}\n";
}
