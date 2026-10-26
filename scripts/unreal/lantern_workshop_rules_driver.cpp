#include "SoraLanternWorkshopRules.h"
#include "SoraFieldcraftRules.h"
#include <cassert>
#include <iomanip>
#include <iostream>

int main()
{
    namespace R=SoraLanternWorkshopRules;
    std::cout<<std::setprecision(15)<<"{\"solids\":[";
    bool Comma=false;
    for(const auto& B:R::Solids())
    {
        if(Comma)std::cout<<',';
        Comma=true;
        std::cout<<'['<<B.X<<','<<B.Y<<','<<B.Z<<','<<B.SX<<','<<B.SY<<','<<B.SZ<<",0,"<<int(B.Surface)<<']';
    }
    std::cout<<"],\"stations\":[";Comma=false;
    for(const auto& P:R::Stations)
    {
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<'['<<P.X<<','<<P.Y<<','<<R::FloorAt(P.X,P.Y)<<']';
    }
    std::cout<<"],\"floor_samples\":[";Comma=false;
    for(const auto& P:{R::FPoint{1655,-950},{1745,-950},{1900,-1535},{1900,-1490},{3150,-1900},{3150,-2000}})
    {
        if(Comma)std::cout<<',';Comma=true;
        std::cout<<'['<<P.X<<','<<P.Y<<','<<R::FloorAt(P.X,P.Y)<<']';
    }
    std::cout<<"],\"craft_routes\":[";Comma=false;
    for(int I=0;I<R::CraftspersonCount;++I)
    {
        if(Comma)std::cout<<',';Comma=true;
        const auto A=R::CraftStart(I),B=R::CraftShelter(I);
        std::cout<<"[["<<A.X<<','<<A.Y<<",47.15],["<<B.X<<','<<B.Y<<",47.15]]";
    }
    std::cout<<"],\"seal_reach\":[";
    std::cout<<R::CanCutSeal(1900,-1660,0,true)<<','<<R::CanCutSeal(1900,-1540,22.5,true)<<','
        <<R::CanCutSeal(1900,-1450,45,true)<<','<<R::CanCutSeal(1900,-1660,450,true)<<','
        <<R::CanCutSeal(1900,-1700,0,true)<<','<<R::CanCutSeal(2120,-1550,0,true)<<','
        <<R::CanCutSeal(1900,-1660,0,false);
    int Hold=0;
    assert(!SoraFieldcraftRules::Hold(Hold,true,1999,R::SealHoldMs));
    assert(Hold==1999);
    assert(!SoraFieldcraftRules::Hold(Hold,false,1,R::SealHoldMs));
    assert(Hold==0);
    assert(!SoraFieldcraftRules::Hold(Hold,true,1999,R::SealHoldMs));
    assert(SoraFieldcraftRules::Hold(Hold,true,1,R::SealHoldMs));
    std::cout<<"],\"hold_ms\":"<<Hold<<"}\n";
}
