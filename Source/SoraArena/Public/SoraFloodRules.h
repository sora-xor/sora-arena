#pragma once
#include "SoraFieldcraftRules.h"

// ch06.b14. The two-metre inspection shaft is an explicit provisional layout
// addition, not an authored historical claim. All distances are centimetres.
namespace SoraFloodRules
{
constexpr int Length=9000, Width=240, Height=220;
constexpr int DeepStart=7500, PocketStart=8150, PocketEnd=8350;
constexpr int DeepFloor=-200, DeepRoof=20, RiseMs=150000;
constexpr int FromCm=40, ToCm=160, SwimDepth=140;
constexpr int DiveSpeed=140, SurfaceSpeed=180, BreathMs=8000, RecoverMs=3000, DrownHpS=10;
constexpr int Clamp(int V,int Lo,int Hi) { return V<Lo?Lo:V>Hi?Hi:V; }
constexpr int Surface(int ClockMs) { return FromCm+(ToCm-FromCm)*static_cast<long long>(Clamp(ClockMs,0,RiseMs))/RiseMs; }
constexpr bool Pocket(int X) { return X>=PocketStart&&X<=PocketEnd; }
constexpr bool RoofedDeep(int X) { return X>=DeepStart&&X<=Length&&!Pocket(X); }
constexpr int Floor(int X)
{
    return X<7300?0:X<7500?-(X-7300):DeepFloor;
}
constexpr bool Immersed(int EyeZ,int WaterZ) { return EyeZ<WaterZ-5; }
struct FRoute { int Stage=0; bool Gate=false; };
// Cross both submerged legs continuously. A teleport/large displacement is
// never evidence of traversal, even if it lands inside the exit volume.
inline void Travel(FRoute& State,float BeforeX,float X,float Y,bool Underwater,float Distance,int DtMs)
{
    if(DtMs<=0) return;
    if(Distance>SurfaceSpeed*DtMs/1000.f+25.f) { State={}; return; }
    if(State.Stage>=4) return;
    if(Y<-120.f||Y>120.f) { State={}; return; }
    if((State.Stage==1||State.Stage==3)&&!Underwater) { State={}; return; }
    if(State.Stage==0&&BeforeX<=DeepStart&&X>DeepStart&&Underwater) State.Stage=1;
    if(State.Stage==1&&X<DeepStart) State.Stage=0;
    if(State.Stage==1&&BeforeX<PocketStart&&X>=PocketStart&&Underwater) State.Stage=2;
    if(State.Stage==2&&BeforeX<=PocketEnd&&X>PocketEnd&&Underwater) State.Stage=3;
    if(State.Stage==3&&X<PocketEnd) State.Stage=2;
    if(State.Stage==3&&BeforeX<Length&&X>=Length&&Underwater) State.Stage=4;
}
constexpr bool Ready(const FRoute& State) { return State.Stage==4&&State.Gate; }
}
