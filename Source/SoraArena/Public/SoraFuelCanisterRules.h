#pragma once
#include "SoraCombatRules.h"
#include <cmath>

namespace SoraFuelCanisterRules
{
constexpr int Count=3,Damage=80,BlastRadiusCm=360;
struct FPoint { int X,Y; };
constexpr FPoint LocalFeetCm[]={{2800,1200},{5200,1200},{4000,3800}};
// Functional proxy dimensions, not an authored final-art specification.
constexpr int BodyRadiusCm=30,BodyHalfHeightCm=70;
struct FState
{
    bool Burst=false;
    bool Shot(SoraCombatRules::EHit Kind,float Amount,bool Playing)
    {
        if(Burst||!Playing||Kind!=SoraCombatRules::EHit::Ranged||!std::isfinite(Amount)||Amount<=0) return false;
        Burst=true; // Latch before any damage/event callbacks can re-enter.
        return true;
    }
};
}
