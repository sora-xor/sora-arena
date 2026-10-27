#include "SoraCatalogWardGate.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraWardGateRules.h"
#include <initializer_list>

namespace
{
bool Numbers(const FJsonObject& O,const TCHAR* Key,std::initializer_list<int> Want)
{
    const auto* A=SoraCatalogJson::Rows(O,Key);if(!A||A->Num()!=int(Want.size()))return false;
    int I=0;for(int E:Want){double V=0;if(!(*A)[I]||(*A)[I]->Type!=EJson::Number||!(*A)[I++]->TryGetNumber(V)||V!=E)return false;}
    return true;
}
bool Number(const FJsonObject& O,const TCHAR* Key,int Want)
{ int32 V=0;return SoraCatalogJson::Int(O,Key,V)&&V==Want; }
}
bool SoraCatalogWardGate::Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraSpace& Space)
{
    namespace R=SoraWardGateRules;
    const auto Value=O.TryGetField(TEXT("ward_gate"));
    if(Beat.Id!=TEXT("ch03.b03"))return !Value.IsValid();
    auto& B=Beat.Space;
    if(!Value||Value->Type!=EJson::Object||!Space.Zones.IsValidIndex(B.Zone))return false;
    const auto H=Value->AsObject();const auto& Z=Space.Zones[B.Zone];
    if(H->Values.Num()!=11||!Numbers(*H,TEXT("plaza_cm"),{-8000,-700,-6200,700})||
       !Numbers(*H,TEXT("shared_landing_cm"),{-8000,-1000,-7600,-660})||
       !Numbers(*H,TEXT("tenement_street_cm"),{R::StreetStartX,-R::StreetHalfWidth,R::StreetEndX,R::StreetHalfWidth})||
       !Number(*H,TEXT("fence_x_cm"),R::FenceX)||!Number(*H,TEXT("fence_height_cm"),R::FenceHeight)||
       !Number(*H,TEXT("gate_width_cm"),R::GateWidth)||
       !Numbers(*H,TEXT("wicket_cm"),{R::FenceX,R::WicketY,R::WicketWidth,R::WicketHeight})||
       !Numbers(*H,TEXT("culvert_cm"),{R::CulvertX,R::CulvertY,R::CulvertFloor,R::CulvertLength,R::CulvertWidth,R::CulvertHeight})||
       !Numbers(*H,TEXT("scanner_cm"),{-6220,-45,0,20,270,240})||
       !Numbers(*H,TEXT("periods_ms"),{0,40000,0,0,50000})||
       Beat.Place!=TEXT("pl_kido")||Z.Place!=Beat.Place||Z.Id!=Beat.Place||
       Z.Rect.Min!=FVector2D(R::MinX,R::MinY)||Z.Rect.Max!=FVector2D(R::MaxX,R::MaxY)||
       Z.Entry!=FVector2D(R::Entry.X,R::Entry.Y)||B.Entry!=Z.Entry||B.HeightCm!=0||
       Z.WallHeight!=420||!Z.Route.IsEmpty()||!Z.Props.IsEmpty()||!Z.Cover.IsEmpty()||Z.Walls.Num()!=7||
       B.Patrols.Num()!=5||B.Spawns.Num()!=5||Beat.Guards.Num()!=5||
       B.Exit.Center!=FVector2D(R::Exit.X,R::Exit.Y)||B.Exit.Size!=FVector2D(300,720))return false;
    const int32 ArrivalZone=Space.ZoneAt(FVector(B.Exit.Center,0));
    if(!Space.Zones.IsValidIndex(ArrivalZone)||Space.Zones[ArrivalZone].Id!=TEXT("pl_ura_nagaya")||
       !Space.Zones[ArrivalZone].Rect.IsInside(B.Exit.Center-B.Exit.Size*.5f)||
       !Space.Zones[ArrivalZone].Rect.IsInside(B.Exit.Center+B.Exit.Size*.5f))return false;
    const auto* Ids=SoraCatalogJson::Rows(*H,TEXT("guard_ids"));
    const TCHAR* Names[]={TEXT("kidoban"),TEXT("g_b03_c2"),TEXT("g_b03_c3"),TEXT("g_b03_e1"),TEXT("g_b03_e2")};
    if(!Ids||Ids->Num()!=5)return false;
    for(int G=0;G<5;++G)
    {
        if(!(*Ids)[G]||(*Ids)[G]->Type!=EJson::String||(*Ids)[G]->AsString()!=Names[G]||
           B.Patrols[G].Num()!=R::Count(G)||B.Spawns[G]!=FVector2D(R::Posts[G].X,R::Posts[G].Y))return false;
        for(int I=0;I<R::Count(G);++I)
        { const auto P=R::Point(G,I);if(B.Patrols[G][I]!=FVector2D(P.X,P.Y))return false; }
        const auto& Guard=Beat.Guards[G];
        if(Guard.Type!=(G<3?TEXT("bound_conscript"):TEXT("enforcer_rifle"))||
           Guard.bPost!=(G==0||G==2||G==3)||Guard.TurnMs!=(G==0?12000:0)||
           Guard.SuspicionPermille!=(G<3?700:0))return false;
    }
    const FVector2D WallAt[]={{-8030,50},{-5570,-710},{-6600,-1030},{-6800,1130},{-5570,760},{-5120,-390},{-5120,390}};
    const FVector2D WallSize[]={{60,2220},{60,700},{2000,60},{2400,60},{60,800},{840,60},{840,60}};
    for(int I=0;I<7;++I)if(Z.Walls[I].Center!=WallAt[I]||Z.Walls[I].Size!=WallSize[I]||Z.Walls[I].Height!=420)return false;
    if(B.Fieldcraft.Lamps.Num()!=3||B.Fieldcraft.Floors.Num()!=4||B.Fieldcraft.Ladders.Num()!=1||B.Volumes.Num()!=2)return false;
    const FVector2D LampAt[]={{-6840,-430},{-6600,-380},{-6220,-70}};
    const TCHAR* LampIds[]={TEXT("andon_b03_bansho"),TEXT("brazier_b03"),TEXT("scan_arch_b03")};
    const TCHAR* Kinds[]={TEXT("andon"),TEXT("brazier"),TEXT("arch")};const int Radii[]={650,400,450};
    for(int I=0;I<3;++I)
    {
        const auto& L=B.Fieldcraft.Lamps[I];
        if(L.Id!=LampIds[I]||L.Kind!=Kinds[I]||L.At!=LampAt[I]||L.RadiusCm!=Radii[I]||L.RelightMs!=0||
           L.Snuff!=(I==0?FSoraLamp::ESnuff::Hold:FSoraLamp::ESnuff::None)||L.HoldMs!=(I==0?1000:0))return false;
    }
    const FVector2D WetAt[]={{-7520,-300},{-7150,300},{-7100,-500},{-6200,-650}};
    for(int I=0;I<4;++I)
    {
        const auto& P=B.Fieldcraft.Floors[I];
        if(P.Area.Center!=WetAt[I]||P.Area.Size!=(I==3?FVector2D(300,100):FVector2D(180,120))||
           P.Kind!=(I==3?TEXT("running_water"):TEXT("puddle"))||P.HeightCm!=(I==3?-90:0)||
           P.StepPermille!=(I==3?500:2000)||P.CrouchPermille!=P.StepPermille)return false;
    }
    const auto& L=B.Fieldcraft.Ladders[0];
    if(L.Id!=TEXT("ladder_b03_shop")||L.Foot!=FVector2D(-6400,650)||L.Yaw!=90||L.HeightCm!=320||
       L.Roof.Center!=FVector2D(-6550,930)||L.Roof.Size!=FVector2D(1100,320)||L.DropNoiseCm!=900||
       !L.bStraw||L.Straw.Center!=FVector2D(-6000,500)||L.Straw.Size!=FVector2D(260,260)||!L.Guards.IsEmpty())return false;
    const TCHAR* Events[]={TEXT("volume_enter:vol_b03_first_conscript"),TEXT("volume_enter:vol_b03_bansho_rear")};
    const FVector2D Centers[]={{-7300,0},{-6850,-565}},Sizes[]={{600,1400},{300,300}};
    for(int I=0;I<2;++I)if(B.Volumes[I].Event!=Events[I]||B.Volumes[I].Center!=Centers[I]||B.Volumes[I].Size!=Sizes[I])return false;
    B.bWardGate=true;return true;
}
