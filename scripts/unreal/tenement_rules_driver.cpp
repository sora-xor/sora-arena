#include "SoraTenementRules.h"
#include <iomanip>
#include <iostream>

int main()
{
    std::cout<<std::setprecision(15)<<"[";
    bool Comma=false;
    for(const auto& B:SoraTenementRules::Solids())
    {
        if(Comma)std::cout<<',';
        Comma=true;
        std::cout<<'['<<B.X<<','<<B.Y<<','<<B.Z<<','<<B.SX<<','<<B.SY<<','<<B.SZ<<','<<B.Yaw<<','<<int(B.Surface)<<']';
    }
    std::cout<<"]\n";
}
