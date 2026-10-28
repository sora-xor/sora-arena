#pragma once

// Chapter-three crossing and its street stubs. These choices apply only to
// the authored campaign hub; kernel/practice geometry remains unchanged.
namespace SoraNoticeSquareRules
{
constexpr int WestTurnaround=-4000,EastTurnaround=4000;
constexpr int NorthStub=3800,SouthStub=-2000;
constexpr bool KeepLegacyHouse(int Index,int Side){return Index!=2&&!(Side==1&&Index==3);}
constexpr bool KeepLegacyLantern(int Index){return Index%5!=2&&Index!=8;}
constexpr bool KeepLegacyCover(double X,double Y)
{return (X<-900||X>900||Y<-700||Y>700)&&!(Y>0&&(X==400||X==1300));}
// The hub stops at x=3200, while the workshop already extends to x=3700
// through y=200. Tile around that floor and leave its side passage open.
// The tenement floor already covers the western turnaround.
constexpr int EastFloorMinX=3200,EastFloorMaxX=4100,StreetHalfWidth=400;
struct FBox { double X,Y,Z,SX,SY,SZ; };
constexpr int PentHeight=320,RidgeY=800,RidgeHeight=750;
constexpr double RoofSlope=.475,RoofThickness=20;
constexpr double RoofHeight(double Y){return RidgeHeight-RoofSlope*(Y<RidgeY?RidgeY-Y:Y-RidgeY);}
constexpr FBox MoneyChangerGround={960,850,256.25,720,900,512.5};
constexpr FBox Pent={525,1200,310,150,600,20};
constexpr FBox StreetFloors[]={{3450,300,-25,500,200,50},{3900,0,-25,400,800,50},
    {0,3250,-25,800,1300,50}};
// Closed street stubs keep the new floor edges inside the playable ward.
// Inner wall faces meet the floor edges; turnarounds retain 100 cm clearance.
constexpr FBox StreetWalls[]={{-425,3250,220,50,1300,540},{425,3250,220,50,1300,540},
    {0,3925,220,900,50,540},{3900,-425,220,400,50,540},
    {3650,425,220,900,50,540},{4125,0,220,50,900,540}};
// Preserve the north wall around the alley and both sides of the new street.
constexpr FBox NorthWalls[]={{-670,2550,220,540,100,540},{1800,2550,220,2800,100,540}};

struct FPoint { int X,Y; };
// The original 12 m circle cut through the money-changer roof. This explicit
// 5.4 m circuit stays over the crossing, at the same 6 m / 36 s rhythm.
// Thirty-two rounded waypoints bound chord error below 3 cm; visits still
// require actual swept arrivals. This does not qualify the unfinished roof.
constexpr int DroneRadius=540,DroneHeight=600,DronePeriodMs=36000,DroneCount=32;
constexpr FPoint DroneCircuit[]={
    {540,0},{530,105},{499,207},{449,300},{382,382},{300,449},{207,499},{105,530},
    {0,540},{-105,530},{-207,499},{-300,449},{-382,382},{-449,300},{-499,207},{-530,105},
    {-540,0},{-530,-105},{-499,-207},{-449,-300},{-382,-382},{-300,-449},{-207,-499},{-105,-530},
    {0,-540},{105,-530},{207,-499},{300,-449},{382,-382},{449,-300},{499,-207},{530,-105}};
// Fifteen actual waypoints make a single-leg phase offset four seconds for
// P1 and three seconds for P2. The second guard starts one leg behind; no
// clock-driven position updates or skipped arrivals are needed.
constexpr FPoint P1[]={{-1020,-700},{-510,-700},{0,-700},{510,-700},{1020,-700},
    {1020,-350},{1020,0},{1020,300},{440,300},{440,700},{0,700},{-510,700},
    {-1020,700},{-1020,233},{-1020,-233}};
// Separate sides of the street let the conscripts pass each other on their
// return legs without their collision capsules occupying the same line.
constexpr FPoint P2[]={{-60,-2000},{-60,-1033},{-60,-67},{-60,900},{-60,1867},{-60,2833},{-60,3800},
    {60,3800},{60,2971},{60,2143},{60,1314},{60,486},{60,-343},{60,-1171},{60,-2000}};
constexpr bool GroundGuard(int Guard){return Guard>=2&&Guard<=6;}
constexpr int PatrolCount(int Guard){return Guard>=2&&Guard<=5?15:Guard==6?2:0;}
constexpr int PatrolPeriod(int Guard){return Guard==2||Guard==3?60000:Guard==4||Guard==5?45000:Guard==6?70000:0;}
constexpr FPoint PatrolPoint(int Guard,int Index)
{
    if(Guard==2||Guard==3)return P1[(Index+(Guard==3?14:0))%15];
    if(Guard==4||Guard==5)return P2[(Index+(Guard==5?14:0))%15];
    return Guard==6?FPoint{Index%2==0?WestTurnaround:EastTurnaround,0}:FPoint{0,0};
}
}
