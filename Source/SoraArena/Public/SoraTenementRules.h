#pragma once
#include <cmath>
#include <vector>

// Authored ch03 back tenements in world centimetres. Shared by the builder
// and native geometry checks; these are functional solids, not final art.
namespace SoraTenementRules
{
constexpr int WellX=-3100, WellY=3200, Bore=90, Depth=700, Curb=75;
constexpr int MinX=-4700, MinY=-400, MaxX=-600, MaxY=4300;
enum class ESurface { Soil, Wood, Stone, Paper };
struct FBox { double X,Y,Z,SX,SY,SZ,Yaw=0; ESurface Surface=ESurface::Wood; };
inline const std::vector<FBox>& Solids()
{
    static const std::vector<FBox> Boxes=[]
    {
        std::vector<FBox> B;
        const auto Box=[&](double X,double Y,double Z,double SX,double SY,double SZ,
                          ESurface S=ESurface::Wood,double Yaw=0)
        { B.push_back({X,Y,Z,SX,SY,SZ,Yaw,S}); };
        const auto Floor=[&](double X0,double Y0,double X1,double Y1,double Z=0)
        { Box((X0+X1)/2,(Y0+Y1)/2,Z-25,X1-X0,Y1-Y0,50,ESurface::Soil); };
        // The existing arena owns x>=-3200,y<=2600. Do not put a second
        // coplanar floor on it. North slabs leave the real 90 cm shaft open.
        Floor(MinX,MinY,-3200,MaxY);
        Floor(-3200,2600,WellX-Bore/2,MaxY);
        Floor(WellX+Bore/2,2600,MaxX,MaxY);
        Floor(WellX-Bore/2,2600,WellX+Bore/2,WellY-Bore/2);
        Floor(WellX-Bore/2,WellY+Bore/2,WellX+Bore/2,MaxY);
        Floor(WellX-65,WellY-65,WellX+65,WellY+65,-Depth);
        // Six facing 2.7 m-frontage / 3.6 m-deep homes on each side.
        for(int Side:{-1,1})for(int I=0;I<6;++I)
        {
            const double X=Side<0?-3070:-2530,Y=1335+I*270;
            Box(X,Y,7.5,360,270,15,ESurface::Stone);
            Box(X,Y,300,378,282,24);
            Box(Side<0?-3250:-2350,Y,145,12,270,290);
            Box(X,Y-135,145,360,12,290);
            Box(X,Y+135,145,360,12,290);
            // The inner face, not the centre, lies on the alley boundary.
            const double Front=Side<0?-2895:-2705;
            Box(Front,Y,145,10,270,290,ESurface::Paper);
        }
        // Front shop, its 1.8 m undercroft, and the 2.7 x 3 m hideout.
        Box(-2800,800,310,180,800,30);
        Box(-2900,800,150,20,800,300);
        Box(-2700,640,150,20,480,300);
        Box(-2575,900,150,270,12,300);
        Box(-2575,1200,150,270,12,300);
        Box(-2440,1050,150,12,300,300);
        Box(-2704,945,150,12,90,300);
        Box(-2704,1155,150,12,90,300);
        Box(-2704,1050,270,12,120,60);
        Box(-2575,1050,310,290,320,25);
        // A lower opening leads into the court; laundry poles stay above
        // the full standing capsule and carry crate.
        for(int Y:{1500,2200,2700})Box(-2800,Y,260,180,6,6);
        // Court fence with a real gap toward the canal-side lots.
        Box(-3400,3000,90,10,360,180);
        Box(-3400,3500,90,10,200,180);
        Box(-3320,3200,250,160,780,20);
        for(int Y:{2850,3550})Box(-3380,Y,125,10,10,250);
        // Manager's house. The southeast corner has an L-shaped entry and
        // two 22.5 cm steps up to the room's 45 cm floor.
        Floor(-3200,3600,-2400,4200,45);
        Box(-3200,3900,195,12,600,300);
        Box(-2800,4200,195,800,12,300);
        Box(-2860,3600,195,680,12,300);
        Box(-2400,3960,195,12,480,300);
        Box(-2800,3900,355,830,630,25);
        Box(-2460,3565,11.25,120,70,22.5,ESurface::Stone);
        Box(-2365,3660,11.25,70,120,22.5,ESurface::Stone);
        // A 90 cm clear bore, 7 m below court level, with a 75 cm curb.
        // Twenty-four tangential slabs preserve the specified clear diameter.
        constexpr double Pi=3.14159265358979323846;
        for(int I=0;I<24;++I)
        {
            const double A=I*2*Pi/24;
            Box(WellX+55*std::cos(A),WellY+55*std::sin(A),(Curb-Depth)/2.,
                20,130*std::tan(Pi/24),Depth+Curb,ESurface::Stone,I*15);
        }
        for(int Side:{-1,1})Box(WellX,WellY+Side*90,175,14,14,350);
        Box(WellX,WellY,350,20,210,20);
        // The working well and its hoist are distinct from the dry shaft.
        for(int Side:{-1,1})
        {
            Box(-2600+Side*90,3100,140,14,14,280);
            Box(-2600+Side*55,3100,35,20,130,70,ESurface::Stone);
            Box(-2600,3100+Side*55,35,90,20,70,ESurface::Stone);
        }
        Box(-2600,3100,285,210,20,20);
        Box(-3080,4020,85,100,70,80);
        // North passage: 2 m east-west, then the authored 1.2 m side run.
        Box(-1630,2895,120,1140,10,240);
        Box(-1570,3105,120,1260,10,240);
        Box(-1065,1770,120,10,2260,240);
        Box(-935,1930,120,10,2340,240);
        return B;
    }();
    return Boxes;
}
}
