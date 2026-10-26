#pragma once

// Chapter-six L4/L5 coordinates in centimetres. Guard indices follow the
// authored encounter order, with eight ledger guards and four palace guards.
namespace SoraLedgerRules
{
struct FPoint { int X=0,Y=0; };
constexpr int GuardCount=12;
constexpr int PeriodMs[GuardCount]={0,0,0,0,0,0,35000,35000,0,0,40000,0};
constexpr int HeightCm[GuardCount]={0,0,0,0,0,0,550,550,0,0,0,0};
constexpr int Yaw[GuardCount]={90,90,-90,-90,0,180,0,0,90,90,0,-90};
constexpr bool IsPost(int I) { return I==4||I==5||I==8||I==11; }
constexpr int PointCount(int I) { return I==6||I==7?4:2; }
constexpr FPoint Points[GuardCount][4]={
    {{280,600},{280,5600}},{{720,1000},{720,5400}},
    {{1600,5400},{1600,800}},{{2040,5600},{2040,1000}},
    {{1160,2800},{1160,2800}},{{1160,6000},{1160,6000}},
    {{280,1200},{2040,1200},{2040,4400},{280,4400}},
    {{720,2800},{2040,2800},{2040,6000},{720,6000}},
    {{2535,-100},{2535,-100}},{{2535,400},{2535,1900}},
    {{-300,-135},{2200,-135}},{{2540,2140},{2540,2140}}};
constexpr int ShelfX[6]={0,440,880,1320,1760,2200};
constexpr FPoint ShelfY[4]={{400,1040},{1360,2640},{2960,4240},{4560,5840}};
constexpr int NicheY[6]={1800,3400,5000,1800,3400,5000};
constexpr int HallWidth=2400,HallLength=6400,HallHeight=600,ShelfWidth=120,ShelfHeight=450;
constexpr int AisleX[5]={280,720,1160,1600,2040};
constexpr int CrossY[4]={1200,2800,4400,6000};
}
