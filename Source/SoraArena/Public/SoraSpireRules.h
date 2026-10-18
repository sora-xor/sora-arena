#pragma once
#include <cmath>

// Four authored landings are connected at approximately 1:12. The opening
// and walk width determine the hexagon, then the grade determines its turns.
namespace SoraSpireRules
{
constexpr int WidthCm=400,VoidDiameterCm=1400,HeightCm=2700;
constexpr double LandingHalfCm=300,MarksmanHalfCm=200,GantryWidthCm=200;
constexpr double RailOverlapCm=35,RouteRadiusCm=34;
constexpr double Sqrt3=1.7320508075688772935;
constexpr double CenterApothem=(VoidDiameterCm+WidthCm)*.5;
constexpr double SideCm=2*CenterApothem/Sqrt3;
constexpr int Sides=static_cast<int>(HeightCm*12.0/SideCm+.5);
constexpr int Subdivisions=3,NodeCount=Sides*Subdivisions+1;
constexpr int Landing(int Level) { return Level*Sides; }
constexpr bool IsLanding(int Node) { return Node%Sides==0; }
struct FPoint { double X,Y,Z; };
// The gantry rails must begin beyond a landing, including their end-cap
// overlap and the pawn's radius. Clear the entire axis-aligned pad on the
// dominant travel axis; the rail's side offset contributes on that axis too.
inline double GantryRailInset(double DX,double DY,double PadHalfCm)
{
    if(PadHalfCm<=0) return 0;
    const double Length=std::hypot(DX,DY),X=std::abs(DX)/Length,Y=std::abs(DY)/Length;
    const double Major=X>Y?X:Y,Minor=X>Y?Y:X;
    return (PadHalfCm+RouteRadiusCm+Minor*GantryWidthCm*.5)/Major+RailOverlapCm*.5;
}
constexpr FPoint Vertex(int Index,double Apothem=CenterApothem)
{
    const double R=2*Apothem/Sqrt3;
    switch(Index%6)
    {
    case 0: return {-R,0,0}; case 1: return {-R*.5,-Apothem,0};
    case 2: return {R*.5,-Apothem,0}; case 3: return {R,0,0};
    case 4: return {R*.5,Apothem,0}; default: return {-R*.5,Apothem,0};
    }
}
constexpr int Round(double Value) { return static_cast<int>(Value+(Value<0?-.5:.5)); }
constexpr FPoint Point(int Node)
{
    // End at the west L4 gantry after the derived number of hexagon sides.
    const int Start=(6-Sides%6)%6,Edge=Start+Node/Subdivisions;
    const auto A=Vertex(Edge),B=Vertex(Edge+1);
    const double F=double(Node%Subdivisions)/Subdivisions;
    return {double(Round(A.X+(B.X-A.X)*F)),double(Round(A.Y+(B.Y-A.Y)*F)),
        double(Round(double(Node)*HeightCm/(NodeCount-1)))};
}
}
