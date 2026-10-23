#pragma once
#include <algorithm>
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
// The optional L3 chord skips two hexagon sides. Closing it must leave the
// complete authored spiral intact; these are geometry indices, not progress.
constexpr int ShortcutStart=Landing(2),ShortcutEnd=ShortcutStart+2*Subdivisions;
constexpr bool IsAccessPad(int Node) { return IsLanding(Node)||Node==ShortcutEnd; }
// The shortcut meets its upper pad obliquely; the ordinary 230 cm landing
// opening clips a 34 cm capsule there. Keep the extra clearance local.
constexpr double InnerRailInset(int Node) { return Node==ShortcutEnd?280:IsLanding(Node)?230:0; }
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
constexpr FPoint AlarmApproach(int Panel)
{
    const auto P=Point(ShortcutStart);
    return {P.X+(Panel==0?-140:140),P.Y-100,P.Z};
}

struct FLine { FPoint A,B; };
struct FPadRails { FLine Lines[16]{}; int Count=0; };
// Guard the square pads' exposed edges, omitting only the footprints of the
// adjoining ramp footprint and the shortcut. A 600 cm square pad extends
// beyond the nearest 346 cm node on a diagonal: include the next segment
// too, or its guard cap narrows the continuing ramp below navmesh clearance.
// Trimming long gantry rails alone leaves the pad corners open to the void.
inline FPadRails ShortcutPadRails(int Node)
{
    FPadRails Out;
    const auto P=Point(Node);
    const FLine Corridors[]={{Point(Node-2),Point(Node-1)},{Point(Node-1),P},
        {P,Point(Node+1)},{Point(Node+1),Point(Node+2)},
        {P,Point(Node==ShortcutStart?ShortcutEnd:ShortcutStart)}};
    const double Half=LandingHalfCm-10;
    const FPoint Corners[]={{P.X-Half,P.Y-Half,P.Z},{P.X+Half,P.Y-Half,P.Z},
        {P.X+Half,P.Y+Half,P.Z},{P.X-Half,P.Y+Half,P.Z}};
    for(int Edge=0;Edge<4;++Edge)
    {
        const auto A=Corners[Edge],B=Corners[(Edge+1)%4];
        struct FInterval { double Low,High; } Open[5];
        int Count=0;
        for(int Route=0;Route<5;++Route)
        {
            const auto C=Corridors[Route];
            const double Length=std::hypot(C.B.X-C.A.X,C.B.Y-C.A.Y);
            const double DX=(C.B.X-C.A.X)/Length,DY=(C.B.Y-C.A.Y)/Length;
            double Low=0,High=1;
            const auto Clip=[&](double Start,double Delta,double Min,double Max)
            {
                if(std::abs(Delta)<1.e-9) return Start>=Min&&Start<=Max;
                double T0=(Min-Start)/Delta,T1=(Max-Start)/Delta;
                if(T0>T1) std::swap(T0,T1);
                Low=std::max(Low,T0); High=std::min(High,T1);
                return Low<=High;
            };
            const double Width=(Route==4?GantryWidthCm:WidthCm)*.5;
            if(Clip((A.X-C.A.X)*DX+(A.Y-C.A.Y)*DY,(B.X-A.X)*DX+(B.Y-A.Y)*DY,-15,Length+15)&&
                Clip(-(A.X-C.A.X)*DY+(A.Y-C.A.Y)*DX,-(B.X-A.X)*DY+(B.Y-A.Y)*DX,-Width,Width))
                Open[Count++]={Low,High};
        }
        std::sort(Open,Open+Count,[](const FInterval& X,const FInterval& Y) { return X.Low<Y.Low; });
        const auto Add=[&](double From,double To)
        {
            if((To-From)*2*Half<=1) return;
            Out.Lines[Out.Count++]={{A.X+(B.X-A.X)*From,A.Y+(B.Y-A.Y)*From,P.Z},
                {A.X+(B.X-A.X)*To,A.Y+(B.Y-A.Y)*To,P.Z}};
        };
        double End=0;
        for(int N=0;N<Count;++N) { Add(End,Open[N].Low); End=std::max(End,Open[N].High); }
        Add(End,1);
    }
    return Out;
}
}
