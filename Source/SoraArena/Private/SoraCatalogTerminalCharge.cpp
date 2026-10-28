#include "SoraCatalogTerminalCharge.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraTerminalChargeRules.h"
#include "SoraNoticeSquareRules.h"
#include <initializer_list>
namespace SoraCatalogTerminalCharge
{
static bool Numbers(const FJsonObject& O,const TCHAR* Key,std::initializer_list<int> Want)
{
    const auto* A=SoraCatalogJson::Rows(O,Key);if(!A||A->Num()!=int(Want.size()))return false;
    int I=0;for(int E:Want)
    {double V=0;if(!(*A)[I]||(*A)[I]->Type!=EJson::Number||!(*A)[I++]->TryGetNumber(V)||V!=E)return false;}
    return true;
}
bool IsSquare(const FSoraZone& Z)
{
    return Z.Id==TEXT("pl_kosatsuba")&&Z.Place==TEXT("pl_kosatsuba")&&
        Z.Rect.Min==FVector2D(-2200,-1000)&&Z.Rect.Max==FVector2D(3200,3200)&&
        Z.Entry==FVector2D(-1000,2800)&&Z.EntryYaw==-90&&Z.Walls.IsEmpty()&&Z.Cover.IsEmpty()&&
        Z.Props.IsEmpty()&&Z.Route.IsEmpty();
}
bool Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraSpace& Space)
{
    const bool Charge=Beat.Id==TEXT("ch03.b10");
    const bool Square=Charge||Beat.Id==TEXT("ch03.b11")||Beat.Id==TEXT("ch03.b12");
    const auto V=O.TryGetField(TEXT("terminal_charge"));if(V.IsValid()!=Charge)return false;
    if(!Square)return true;
    const auto& B=Beat.Space;if(!Space.Zones.IsValidIndex(B.Zone))return false;
    const auto& Z=Space.Zones[B.Zone];
    if(!IsSquare(Z)||B.Entry!=Z.Entry||B.EntryYaw!=-90||B.Anchor!=FVector2D(-730,560)||B.HeightCm!=0)return false;
    if(!Charge)return true;
    const auto C=V->Type==EJson::Object?V->AsObject():nullptr;namespace R=SoraTerminalChargeRules;namespace N=SoraNoticeSquareRules;
    if(!C||!Numbers(*C,TEXT("terminal_cm"),{R::TerminalX,R::TerminalY,0})||
       !Numbers(*C,TEXT("panel_cm"),{R::PanelX,R::PanelY,110})||
       !Numbers(*C,TEXT("holds_ms"),{R::PlantMs,R::LightMs})||!Numbers(*C,TEXT("fuse_ms"),{R::FuseMs})||
       !Numbers(*C,TEXT("blast_cm_hp"),{R::BlastRadius,R::Damage})||
       !Numbers(*C,TEXT("safe_cm"),{-2200,2900,0,-1000,3100,400,R::SafeDistance})||
       !Numbers(*C,TEXT("ground_patrol_periods_ms"),{N::PatrolPeriod(2),N::PatrolPeriod(3),N::PatrolPeriod(4),N::PatrolPeriod(5),N::PatrolPeriod(6)})||
       !Numbers(*C,TEXT("ground_patrol_pair_spacing_ms"),{4000,3000})||
       !Numbers(*C,TEXT("drone_circuit_cm_ms"),{0,0,N::DroneRadius,N::DroneHeight,N::DronePeriodMs,N::DroneCount})||
       !Numbers(*C,TEXT("roof_cm_permille"),{600,400,1320,1300,570,340,1350,1360,N::RidgeY,N::RidgeHeight,475}))return false;
    if(B.Patrols.Num()!=7||Beat.Guards.Num()!=7||B.Patrols[0]!=TArray<FVector2D>{FVector2D(900,800)}||
       B.Patrols[1].Num()!=N::DroneCount)return false;
    for(int I=0;I<N::DroneCount;++I)
        if(B.Patrols[1][I]!=FVector2D(N::DroneCircuit[I].X,N::DroneCircuit[I].Y))return false;
    if(B.Fieldcraft.Ladders.Num()!=2)return false;
    for(int I=0;I<2;++I)
    {
        const auto& L=B.Fieldcraft.Ladders[I];
        if(L.Id!=(I?TEXT("ladder_b10_kawara"):TEXT("ladder_b10_pent"))||L.Foot!=FVector2D(500,I?1250:1600)||
           L.Yaw!=(I?0:-90)||L.BaseHeightCm!=(I?320:0)||L.HeightCm!=(I?540:320)||L.DropNoiseCm!=900||L.bStraw||
           L.Roof.Center!=FVector2D(I?960:525,I?850:1200)||L.Roof.Size!=FVector2D(I?780:150,I?1020:600)||
           L.RoofGeometry!=(I?FSoraLadder::ERoof::NoticeKawara:FSoraLadder::ERoof::NoticePent)||
           L.Guards!=(I?TArray<int32>{0}:TArray<int32>{}))return false;
    }
    int BoardPatches=0;
    for(const auto& Floor:B.Fieldcraft.Floors)if(Floor.Kind==TEXT("board_roof"))
    {
        ++BoardPatches;
        if(Floor.Area.Center!=FVector2D(525,1200)||Floor.Area.Size!=FVector2D(150,600)||Floor.HeightCm!=320||
           Floor.StepPermille!=1500||Floor.CrouchPermille!=1500)return false;
    }
    if(BoardPatches!=1)return false;
    if(Beat.Guards[0].Type!=TEXT("marksman")||!Beat.Guards[0].bPost||Beat.Guards[1].Type!=TEXT("drone")||Beat.Guards[1].bPost)return false;
    const FName Types[]={TEXT("enforcer_rifle"),TEXT("enforcer_rifle"),TEXT("bound_conscript"),TEXT("bound_conscript"),TEXT("blade_retainer")};
    for(int G=2;G<7;++G)
    {
        if(Beat.Guards[G].Type!=Types[G-2]||Beat.Guards[G].bPost||B.Patrols[G].Num()!=N::PatrolCount(G))return false;
        for(int I=0;I<N::PatrolCount(G);++I)
        {const auto P=N::PatrolPoint(G,I);if(B.Patrols[G][I]!=FVector2D(P.X,P.Y))return false;}
    }
    if(B.Objectives.Num()!=3||B.Objectives[0]!=FVector2D(R::PanelX,R::PanelY)||B.Objectives[1]!=B.Objectives[0]||
       B.Objectives[2]!=FVector2D(-1600,3000)||Beat.Objectives.Num()!=3||Beat.ObjectiveHoldMs!=TArray<int32>{4000,1000,0}||
       Beat.Objectives[0]!=TEXT("obj_plant_charge")||Beat.Objectives[1]!=TEXT("obj_light_fuse")||
       Beat.Objectives[2]!=TEXT("obj_reach_safe")||Beat.Task.Goal!=SoraBeatRules::EGoal::Objectives||Beat.Task.Count!=3)return false;
    const auto* Lamp=B.Fieldcraft.Lamps.FindByPredicate([](const FSoraLamp& L){return L.Id==TEXT("terminal_glow_b10");});
    return Lamp&&Lamp->At==FVector2D(R::TerminalX,R::TerminalY);
}
}
