#pragma once
#include <cmath>

namespace SoraTenementFindRules
{
constexpr int Count=2;
constexpr double ReachCm=140,FloorToleranceCm=8,ViewDot=.5;
struct FPoint { double X,Y,Z; };
constexpr FPoint Points[Count]={{-2887,1830,65},{-2713,2415,135}};
inline bool WithinReach(int Index,bool Grounded,double X,double Y,double Feet)
{
    if(Index<0||Index>=Count||!Grounded||!std::isfinite(X)||!std::isfinite(Y)||!std::isfinite(Feet)||
       std::abs(Feet)>FloorToleranceCm)return false;
    const auto P=Points[Index];
    return (X-P.X)*(X-P.X)+(Y-P.Y)*(Y-P.Y)<=ReachCm*ReachCm;
}
}
