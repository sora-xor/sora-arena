#pragma once
#include <cmath>
// Authored ch06.b02 dimensions are centimetres. The compact swimming posture
// is local to this route; its fixed head point is independent of camera sway.
namespace SoraMoatRules
{
constexpr int Length=22000,Width=3600,Surface=0,Bed=-240,GateBed=-300;
constexpr int GateX0=20600,GateX1=21000,GateY0=3560,GateY1=3640;
constexpr int GateBottom=-180,GateTop=-120,FloatClearDepth=80,HitscanClearDepth=100;
constexpr int Radius=28,HalfHeight=28,HeadOffset=18,SurfaceCenter=-6,DiveCenter=-150;
constexpr int ParapetWalk=1750,ParapetY=4860;
constexpr int SurfaceSpeed=180,DiveSpeed=140,BreathMs=8000,RecoverMs=3000,DrownHp=10;
struct FBankRamp { double CenterY,CenterZ,Length,RollDegrees; };
inline FBankRamp BankRamp()
{
    const double L=std::sqrt(400.*400.+340.*340.);
    return {-200.-20.*340./L,-70.-20.*400./L,L,std::atan2(340.,400.)*180./std::acos(-1.)};
}
inline bool Water(double X,double Y)
{ return (X>=0&&X<=Length&&Y>=-400&&Y<=Width)||(X>=20400&&X<=21400&&Y>=Width&&Y<=4500); }
inline double Floor(double X,double Y)
{
    if(Y<=-400)return 100.;
    if(Y<0) return -240.-.85*Y;
    return X>=20000&&X<=21400&&Y>=3000?GateBed:Bed;
}
inline double HeadDepth(double CenterZ) { return Surface-(CenterZ+HeadOffset); }
inline bool Submerged(double CenterZ) { return HeadDepth(CenterZ)>0; }
inline bool ClearsFloat(double CenterZ) { return HeadDepth(CenterZ)>FloatClearDepth; }
inline bool ExcludesHitscan(double CenterZ) { return HeadDepth(CenterZ)>HitscanClearDepth; }
inline bool GateFits(double X,double Z,double R=Radius,double Half=HalfHeight)
{ return X-R>=GateX0&&X+R<=GateX1&&Z-Half>=GateBottom&&Z+Half<=GateTop; }
inline bool GateCrossed(double OldX,double OldY,double OldZ,double X,double Y,double Z,double Distance,double Dt)
{
    return Dt>0&&OldY<=Width&&Y>Width&&GateFits(OldX,OldZ)&&GateFits(X,Z)&&
        Distance<=SurfaceSpeed*Dt+2.;
}
}
