#include "SoraCatalogTerminalCharge.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraTerminalChargeRules.h"
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
bool Square(const FSoraZone& Z)
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
    if(!Square(Z)||B.Entry!=Z.Entry||B.EntryYaw!=-90||B.Anchor!=FVector2D(-730,560)||B.HeightCm!=0)return false;
    if(!Charge)return true;
    const auto C=V->Type==EJson::Object?V->AsObject():nullptr;namespace R=SoraTerminalChargeRules;
    if(!C||!Numbers(*C,TEXT("terminal_cm"),{R::TerminalX,R::TerminalY,0})||
       !Numbers(*C,TEXT("panel_cm"),{R::PanelX,R::PanelY,110})||
       !Numbers(*C,TEXT("holds_ms"),{R::PlantMs,R::LightMs})||!Numbers(*C,TEXT("fuse_ms"),{R::FuseMs})||
       !Numbers(*C,TEXT("blast_cm_hp"),{R::BlastRadius,R::Damage})||
       !Numbers(*C,TEXT("safe_cm"),{-2200,2900,0,-1000,3100,400,R::SafeDistance}))return false;
    if(B.Objectives.Num()!=3||B.Objectives[0]!=FVector2D(R::PanelX,R::PanelY)||B.Objectives[1]!=B.Objectives[0]||
       B.Objectives[2]!=FVector2D(-1600,3000)||Beat.Objectives.Num()!=3||Beat.ObjectiveHoldMs!=TArray<int32>{4000,1000,0}||
       Beat.Objectives[0]!=TEXT("obj_plant_charge")||Beat.Objectives[1]!=TEXT("obj_light_fuse")||
       Beat.Objectives[2]!=TEXT("obj_reach_safe")||Beat.Task.Goal!=SoraBeatRules::EGoal::Objectives||Beat.Task.Count!=3)return false;
    const auto* Lamp=B.Fieldcraft.Lamps.FindByPredicate([](const FSoraLamp& L){return L.Id==TEXT("terminal_glow_b10");});
    return Lamp&&Lamp->At==FVector2D(R::TerminalX,R::TerminalY);
}
}
