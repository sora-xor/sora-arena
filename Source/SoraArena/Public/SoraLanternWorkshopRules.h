#pragma once
#include <vector>

// Chapter-three workshop, in authored world centimetres. These construction
// solids establish play space; their materials and meshes are still WIP art.
namespace SoraLanternWorkshopRules
{
constexpr int MinX=1450,MinY=-2500,MaxX=3700,MaxY=200;
struct FPoint { double X,Y; };
constexpr FPoint Stations[]={{2100,-620},{2100,-950},{2100,-1300},{2790,-2050}};
constexpr int StepStations[]={0,1,1,2,3,3};
constexpr int SealHoldMs=2000,CraftspersonCount=4;
constexpr FPoint SealApproach{1900,-1660};
constexpr FPoint CraftStart(int I) { return {2250.,-1400.+I*200.}; }
constexpr FPoint CraftShelter(int I) { return {2250.,-950.+I*150.}; }
// The seal is on the yard face, above its step. Height and side matter:
// neither the roof nor a matching position inside the room can cut it.
constexpr bool CanCutSeal(double X,double Y,double Feet,bool Grounded)
{
    const double DX=X-1900,DY=Y+1500;
    return Grounded&&Feet>=-4&&Feet<=26&&Y<=-1506&&
        DX*DX+DY*DY<180*180;
}
constexpr double FloorAt(double X,double Y)
{
    if(X>=1780&&X<=2320&&Y>=-1500&&Y<=-400)return 45;
    if((X>=1710&&X<1780&&Y>=-1494&&Y<=-406)||
       (X>=1830&&X<=1970&&Y>=-1570&&Y<-1500))return 22.5;
    return 0;
}
enum class ESurface { Soil,Wood,Stone,Paper };
struct FBox { double X,Y,Z,SX,SY,SZ; ESurface Surface=ESurface::Wood; };
inline const std::vector<FBox>& Solids()
{
    static const std::vector<FBox> Boxes=[]
    {
        std::vector<FBox> B;
        const auto Box=[&](double X,double Y,double Z,double SX,double SY,double SZ,ESurface S=ESurface::Wood)
        { B.push_back({X,Y,Z,SX,SY,SZ,S}); };
        // The arena already owns all ground west of x=3200 here.
        Box(3450,-1150,-25,500,2700,50,ESurface::Soil);
        // A 1.8 m earth passage beside a 5.4 m plank floor. Two half-height
        // steps make the raised floor accessible from the passage and yard.
        Box(2050,-950,22.5,540,1100,45);
        Box(1745,-950,11.25,70,1088,22.5);
        Box(1900,-1535,11.25,140,70,22.5);
        Box(1600,-950,215,12,1100,430);
        Box(2320,-950,215,12,1100,430);
        Box(1960,-400,215,720,12,430); // Barred street frontage.
        Box(1715,-1500,215,230,12,430);
        Box(2145,-1500,215,350,12,430);
        Box(1900,-1500,345,140,12,170); // 215 cm clear above the plank floor.
        Box(1960,-950,440,750,1130,20);
        // The shallow neighbour leaves the authored east side passage open.
        Box(2860,-650,210,1080,500,420);
        // Yard boundaries; the 180 cm canal gate remains physically open.
        Box(1600,-1850,100,12,700,200);
        Box(1755,-2200,100,310,12,200);
        Box(2495,-2200,100,810,12,200);
        Box(3400,-1375,80,12,450,160); // Leave the north-east yard entrance open.
        Box(3700,-1150,100,12,2700,200,ESurface::Stone);
        // Well curb is hard cover, with a clear route on both sides.
        for(int S:{-1,1})
        {
            Box(2600+S*65,-1400,40,30,160,80,ESurface::Stone);
            Box(2600,-1400+S*65,40,100,30,80,ESurface::Stone);
        }
        // Storehouse: a real ground-floor interior, a west doorway and a
        // distinct 6.5 m roof. The shell bench sits under its west eaves.
        Box(3400,-1900,319,16,600,638,ESurface::Stone);
        Box(3150,-1600,319,500,16,638,ESurface::Stone);
        Box(3150,-2200,319,500,16,638,ESurface::Stone);
        Box(2900,-2095,319,16,210,638,ESurface::Stone);
        Box(2900,-1705,319,16,210,638,ESurface::Stone);
        Box(2900,-1900,444,16,180,388,ESurface::Stone);
        Box(3050,-1900,644,700,640,12);
        return B;
    }();
    return Boxes;
}
}
