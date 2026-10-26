#include "SoraLanternWorkshopRules.h"
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
    std::cout<<"]}\n";
}
