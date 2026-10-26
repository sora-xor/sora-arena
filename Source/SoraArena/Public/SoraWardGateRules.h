#pragma once

// Authored physical gate contract in centimetres. Ordinary play and finished
// art are separate from the geometry/detection rules checked here.
namespace SoraWardGateRules
{
struct FPoint { int X,Y; };
inline constexpr FPoint Entry{-7820,-550};
inline constexpr int FenceX=-6200,FenceHeight=240,GateWidth=360;
inline constexpr int CulvertX=-6200,CulvertY=-650,CulvertFloor=-90,CulvertLength=300,CulvertWidth=100,CulvertHeight=90;
inline constexpr int WicketY=135,WicketWidth=90,WicketHeight=120;
inline constexpr int MinX=-8000,MinY=-1000,MaxX=-4700,MaxY=1100;
inline constexpr int StreetStartX=-5600,StreetEndX=-4700,StreetHalfWidth=360;
inline constexpr FPoint Exit{-4450,0};
inline constexpr int Periods[]={0,40000,0,0,50000};
inline constexpr FPoint Posts[]={{-6300,150},{-7900,-650},{-6660,-290},{-6300,0},{-7900,-500}};
inline constexpr FPoint Ditch[]={{-7900,-650},{-7000,-650},{-7000,-800},{-6450,-800},{-7000,-800},{-7000,-650}};
inline constexpr FPoint Perimeter[]={{-7900,-500},{-7900,600},{-6400,600},{-6400,-190},{-7000,-190},{-7000,-500}};
inline constexpr int Count(int Guard) { return Guard==1||Guard==4?6:1; }
inline constexpr FPoint Point(int Guard,int Index) { return Guard==1?Ditch[Index]:Guard==4?Perimeter[Index]:Posts[Guard]; }
struct FSlab { const char* Name; int X0,Y0,X1,Y1,Top; };
// The landing owns X -8000..-7600, Y -1000..-660. Do not lay a second
// floor over it. The bent western descent also stays outside the hut.
inline constexpr FSlab Ground[]={
    {"WardTenementStreet",StreetStartX,-StreetHalfWidth,StreetEndX,StreetHalfWidth,0},
    {"WardApproach",-8000,-660,-7600,1100,0},
    {"WardGroundNorth",-7600,-600,-5600,1100,0},
    {"WardGroundSouthWest",-7600,-870,-6440,-700,0},
    {"WardGroundSouthEast",-6340,-870,-5600,-700,0},
    {"WardCulvertSouthLip",-6440,-870,-6340,-850,0},
    {"WardGroundSouthOuter",-7600,-1000,-5600,-930,0},
    {"WardDitchEastEnd",-6820,-930,-5600,-870,0},
    {"WardGroundWest",-7600,-700,-6440,-600,0},
    {"WardGroundEast",-5870,-700,-5600,-600,0},
    {"WardCulvertBed",-6440,-700,-6050,-600,-90},
    {"WardCulvertWestStep1",-6440,-850,-6340,-800,-30},
    {"WardCulvertWestStep2",-6440,-800,-6340,-750,-60},
    {"WardCulvertWestStep3",-6440,-750,-6340,-700,-90},
    // A full capsule must clear the roof before the first upward step.
    {"WardCulvertEastStep1",-6050,-700,-5970,-600,-90},
    {"WardCulvertEastStep2",-5970,-700,-5920,-600,-60},
    {"WardCulvertEastStep3",-5920,-700,-5870,-600,-30},
    {"WardDitchBed",-7600,-930,-6820,-870,-40},
};
enum class ESurface { Wood,Stone,Plaster };
struct FSolid { const char* Name; int X,Y,Z,Width,Depth,Height; ESurface Surface; };
inline constexpr FSolid Solids[]={
    {"WardCulvertRoof",-6200,-650,10,300,140,20,ESurface::Stone},
    {"WardCulvertWallSouth",-6200,-710,-45,300,20,90,ESurface::Stone},
    {"WardCulvertWallNorth",-6200,-590,-45,300,20,90,ESurface::Stone},
    {"WardBoardFenceSouth",-6200,-590,120,20,820,240,ESurface::Wood},
    {"WardBoardFenceNorth",-6200,640,120,20,920,240,ESurface::Wood},
    {"WardGateLeafSouth",-6200,-90,120,16,180,240,ESurface::Wood},
    {"WardGateLeafNorthSolid",-6200,45,120,16,90,240,ESurface::Wood},
    {"WardWicketLintel",-6200,135,180,16,90,120,ESurface::Wood},
    {"WardGatePostSouth",-6200,-196,130,32,32,260,ESurface::Wood},
    {"WardGatePostNorth",-6200,196,130,32,32,260,ESurface::Wood},
    {"WardHut",-6620,-565,135,360,270,270,ESurface::Plaster},
    {"WardHutRoof",-6620,-565,278,390,300,16,ESurface::Wood},
    {"WardNorthShop",-6550,930,150,1100,320,300,ESurface::Plaster},
    {"WardUdatsu",-6200,930,340,30,320,40,ESurface::Plaster},
    {"WardRoofFirewallStepWest",-6245,930,330,60,160,20,ESurface::Stone},
    {"WardRoofFirewallStepEast",-6155,930,330,60,160,20,ESurface::Stone},
};
// Swept capsule bounds catch contact before the closed gate stops the
// player's centre. Segment clipping also catches a whole crossing in a tick.
inline bool CrossesScanner(double AX,double AY,double AZ,double BX,double BY,double BZ,double Radius=0,double HalfHeight=0)
{
    const double A[]={AX,AY,AZ},B[]={BX,BY,BZ};
    const double Low[]={-6230-Radius,-180-Radius,-HalfHeight},High[]={-6210+Radius,90+Radius,240+HalfHeight};
    double Enter=0,Leave=1;
    for(int I=0;I<3;++I)
    {
        const double D=B[I]-A[I];
        if(D==0) { if(A[I]<Low[I]||A[I]>High[I])return false;continue; }
        double P=(Low[I]-A[I])/D,Q=(High[I]-A[I])/D;
        if(P>Q){const double T=P;P=Q;Q=T;}
        if(P>Enter)Enter=P;if(Q<Leave)Leave=Q;
        if(Enter>Leave)return false;
    }
    return true;
}
}
