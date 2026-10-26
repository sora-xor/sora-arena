#include "SoraCatalogLanding.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraLandingSpaceRules.h"
#include <initializer_list>

namespace
{
bool LandingNumbers(const FJsonObject& O,const TCHAR* Key,std::initializer_list<int> Values)
{
    const auto* A=SoraCatalogJson::Rows(O,Key);
    if(!A||A->Num()!=int(Values.size()))return false;
    int I=0;
    for(int Expected:Values)
    { double Number=0;if(!(*A)[I]||(*A)[I]->Type!=EJson::Number||!(*A)[I++]->TryGetNumber(Number)||Number!=Expected)return false; }
    return true;
}
}

bool SoraCatalogLanding::Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraSpace& Space)
{
    namespace R=SoraLandingSpaceRules;
    const auto Value=O.TryGetField(TEXT("landing"));
    if(Beat.Id!=TEXT("ch03.b01")&&Beat.Id!=TEXT("ch03.b02"))return !Value.IsValid();
    auto& B=Beat.Space;
    if(!Value||Value->Type!=EJson::Object||!Space.Zones.IsValidIndex(B.Zone)||B.HeightCm!=0)return false;
    const auto H=Value->AsObject();const auto& Z=Space.Zones[B.Zone];bool Eight=false,PingPong=false;
    if(H->Values.Num()!=5||!LandingNumbers(*H,TEXT("yard_cm"),{R::MinX,R::MinY,R::MaxX,R::MaxY})||
       !LandingNumbers(*H,TEXT("altitudes_cm"),{R::Height(0),R::Height(1)})||
       !LandingNumbers(*H,TEXT("periods_ms"),{R::Period(0),R::Period(1)})||
       !H->TryGetBoolField(TEXT("figure_eight"),Eight)||!Eight||!H->TryGetBoolField(TEXT("canal_ping_pong"),PingPong)||!PingPong||
       Beat.Place!=TEXT("pl_horiwari")||Z.Id!=TEXT("pl_horiwari")||Z.Place!=Beat.Place||
       Z.Rect.Min!=FVector2D(R::MinX,R::ZoneMinY)||Z.Rect.Max!=FVector2D(R::MaxX,R::ZoneMaxY)||
       Z.Entry!=FVector2D(R::Entry.X,R::Entry.Y)||B.Entry!=Z.Entry||Z.EntryYaw!=0||B.EntryYaw!=0||
       Z.WallHeight!=360||Z.Walls.Num()!=4||!Z.Route.IsEmpty()||
       Z.Cover.Num()!=5||!Z.Props.IsEmpty()||B.Patrols.Num()!=2||
       B.Exit.Center!=FVector2D(-7820,-850)||B.Exit.Size!=FVector2D(360,300))return false;
    for(int I=0;I<4;++I)
    {
        const auto& W=Z.Walls[I];const auto& E=R::Walls[I];
        if(W.Center!=FVector2D(E.X,E.Y)||W.Size!=FVector2D(E.Width,E.Depth)||W.Height!=E.Height)return false;
    }
    for(int I=0;I<5;++I)
        if(Z.Cover[I].Center!=FVector2D(R::Cargo[I].X,R::Cargo[I].Y)||Z.Cover[I].Size!=FVector2D(230,180)||Z.Cover[I].Height!=140)return false;
    for(int G=0;G<2;++G)
    {
        if(B.Patrols[G].Num()!=R::Count(G))return false;
        for(int I=0;I<R::Count(G);++I)
        { const auto P=R::Point(G,I);if(B.Patrols[G][I]!=FVector2D(P.X,P.Y))return false; }
    }
    if(Beat.Id==TEXT("ch03.b02"))
    {
        if(B.Fieldcraft.Lamps.Num()!=3||B.Fieldcraft.Floors.Num()!=6)return false;
        const TCHAR* LampIds[]={TEXT("andon_b02_w1"),TEXT("andon_b02_w3"),TEXT("andon_b02_shed")};
        for(int I=0;I<3;++I)
        {
            const auto& L=B.Fieldcraft.Lamps[I];
            if(L.At!=FVector2D(R::Lamps[I].X,R::Lamps[I].Y)||L.Id!=LampIds[I]||L.Kind!=TEXT("andon")||
               L.RadiusCm!=650||L.Snuff!=FSoraLamp::ESnuff::Hold||L.HoldMs!=1000||L.RelightMs!=0)return false;
        }
        for(int I=0;I<6;++I)
        {
            const auto& P=B.Fieldcraft.Floors[I];
            if(P.Area.Center!=FVector2D(R::Puddles[I].X,R::Puddles[I].Y)||P.Area.Size!=FVector2D(280,140)||
               P.Kind!=TEXT("puddle")||P.HeightCm!=0||P.StepPermille!=2000||P.CrouchPermille!=2000)return false;
        }
        if(B.Volumes.Num()!=3)return false;
        const TCHAR* Events[]={TEXT("volume_enter:vol_b02_drones"),TEXT("volume_enter:vol_b02_puddles"),TEXT("volume_enter:vol_b02_andon")};
        const FVector2D Centers[]={{-11300,-2400},{-10400,-2100},{-11300,-1450}},Sizes[]={{1000,800},{800,600},{1000,500}};
        for(int I=0;I<3;++I)
            if(B.Volumes[I].Event!=Events[I]||B.Volumes[I].Center!=Centers[I]||B.Volumes[I].Size!=Sizes[I])return false;
    }
    B.bLanding=true;return true;
}
