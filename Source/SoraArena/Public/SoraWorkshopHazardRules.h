#pragma once
#include "SoraCombatRules.h"
#include <algorithm>
#include <cmath>

namespace SoraWorkshopHazardRules
{
constexpr int BurnMs=6000,DamagePerSecond=12,FireRadiusCm=180;
// Functional geometry and cover health are provisional. The text's x=2300
// oil marker falls inside the x=2320 wall: put the jars on its yard face.
constexpr int OilX=2360,OilY=-1200,OilRadiusCm=24,OilHalfHeightCm=55;
struct FCover { int X,Y,SX,SY,Height,Health; };
constexpr FCover Covers[]={{2770,-950,200,40,120,40},{3200,-950,200,40,120,40},
                           {2780,-1510,160,24,110,30}};
constexpr bool FloorContact(double X,double Y,double Feet)
{
    const double DX=X-OilX,DY=Y-OilY;
    return Feet>=-4&&Feet<=8&&DX*DX+DY*DY<=FireRadiusCm*FireRadiusCm;
}
inline bool BlastReaches(double Distance,double Radius,double Damage,bool Clear)
{
    return Clear&&std::isfinite(Distance)&&std::isfinite(Radius)&&std::isfinite(Damage)&&
        Damage>0&&Radius>0&&Distance>=0&&Distance<=Radius;
}
struct FFire
{
    bool Spent=false;
    int LeftMs=0;
    bool Ignite()
    {
        if(Spent)return false;
        Spent=true;LeftMs=BurnMs;return true;
    }
    int Advance(int DtMs)
    {
        const int Active=std::clamp(DtMs,0,LeftMs);
        LeftMs-=Active;return Active;
    }
};
// Accumulate sub-point exposure per body. Integer damage admission cannot
// round each rendered frame into a different effective damage rate.
inline int Burn(int& MilliDamage,int ActiveMs)
{
    const int Total=MilliDamage+std::clamp(ActiveMs,0,BurnMs)*DamagePerSecond;
    MilliDamage=Total%1000;return Total/1000;
}
inline int BreakCover(int& Health,SoraCombatRules::EHit Kind,float Amount,bool Playing)
{
    using H=SoraCombatRules::EHit;
    if(!Playing||Health<=0||!std::isfinite(Amount)||Amount<=0||
       (Kind!=H::Melee&&Kind!=H::Ranged&&Kind!=H::Blast))return 0;
    const int Applied=Amount>=Health?Health:int(Amount);
    Health-=Applied;return Applied;
}
}
