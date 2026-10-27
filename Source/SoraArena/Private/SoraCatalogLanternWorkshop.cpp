#include "SoraCatalogLanternWorkshop.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraWorkshopEncounterRules.h"
#include "SoraWorkshopCraftRules.h"
#include <initializer_list>

namespace
{
bool Numbers(const FJsonObject& O,const TCHAR* Key,std::initializer_list<int> Want)
{
    const auto* A=SoraCatalogJson::Rows(O,Key);if(!A||A->Num()!=int(Want.size()))return false;
    int I=0;for(int E:Want)
    { double V=0;if(!(*A)[I]||(*A)[I]->Type!=EJson::Number||!(*A)[I++]->TryGetNumber(V)||V!=E)return false; }
    return true;
}
}
bool SoraCatalogLanternWorkshop::Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraSpace& Space)
{
    const bool Combat=Beat.Id==TEXT("ch03.b08"),Craft=Beat.Id==TEXT("ch03.b09");
    const auto V=O.TryGetField(TEXT("lantern_workshop"));
    const auto Controls=O.TryGetField(TEXT("workshop_craft"));
    if(Controls.IsValid()!=Craft)return false;
    if(!Combat&&!Craft)return !V.IsValid();
    const auto H=V.IsValid()&&V->Type==EJson::Object?V->AsObject():nullptr;
    auto& B=Beat.Space;
    if(!H||!Space.Zones.IsValidIndex(B.Zone))return false;
    const auto& Z=Space.Zones[B.Zone];namespace R=SoraLanternWorkshopRules;
    if(Z.Id!=TEXT("pl_chochin_kobo")||Z.Rect.Min!=FVector2D(R::MinX,R::MinY)||Z.Rect.Max!=FVector2D(R::MaxX,R::MaxY)||
       Z.Entry!=FVector2D(2000,-2300)||Z.EntryYaw!=90.f||Z.WallHeight!=430.f||
       !Z.Walls.IsEmpty()||!Z.Cover.IsEmpty()||!Z.Props.IsEmpty()||!Z.Route.IsEmpty()||
       !Numbers(*H,TEXT("building_cm"),{1600,-1500,2320,-400})||
       !Numbers(*H,TEXT("plank_cm"),{1780,-1500,2320,-400,45})||
       !Numbers(*H,TEXT("earth_passage_cm"),{1600,-1500,1780,-400})||
       !Numbers(*H,TEXT("back_door_cm"),{1900,-1500,140})||
       !Numbers(*H,TEXT("yard_cm"),{1600,-2200,3400,-900})||
       !Numbers(*H,TEXT("well_cm"),{2600,-1400})||
       !Numbers(*H,TEXT("storehouse_cm"),{2900,-2200,3400,-1600,650})||
       !Numbers(*H,TEXT("back_gate_cm"),{2000,-2200,180}))return false;
    if(B.Entry!=FVector2D(2000,-2300)||B.EntryYaw!=90.f||B.HeightCm!=0||
       B.Anchor!=(Craft?FVector2D(2050,-950):FVector2D(1900,-1660))||
       B.Exit.Center!=FVector2D(3480,-250)||B.Exit.Size!=FVector2D(300,300)||
       B.Spawns.Num()!=(Combat?8:6)||!B.Patrols.IsEmpty())return false;
    const FVector2D Spawns[]={{3280,-1050},{3100,-1050},{2920,-1050},{2000,-2320},{2000,-2420},{2750,-1700}};
    for(int I=0;I<B.Spawns.Num();++I)
    {
        const auto P=SoraWorkshopEncounterRules::Spawns[I].Floor;
        if(B.Spawns[I]!=(Combat?FVector2D(P.X,P.Y):Spawns[I]))return false;
    }
    if(Craft)
    {
        const auto C=Controls->Type==EJson::Object?Controls->AsObject():nullptr;
        namespace Timing=SoraWorkshopCraftRules;
        if(!C||!Numbers(*C,TEXT("bend_release_ms"),{Timing::BendMs,Timing::BendToleranceMs})||
           !Numbers(*C,TEXT("paste_hold_ms"),{Timing::PasteMs}))return false;
        if(Beat.Task.Goal!=SoraBeatRules::EGoal::Steps||Beat.Task.StepCount!=6||Beat.StepKinds.Num()!=6)return false;
        const int Counts[]={6,4,1,1,3,1};
        const TCHAR* Kinds[]={TEXT("bend"),TEXT("paste"),TEXT("assemble"),TEXT("paste"),TEXT("assemble"),TEXT("inspect")};
        for(int I=0;I<6;++I)
        {
            const auto& Step=Beat.Task.Steps[I];
            if(Beat.StepKinds[I]!=Kinds[I]||Step.Count!=Counts[I]||Step.PhraseStrikes!=0||Step.PhrasePass!=0||
               Step.BeatMs!=(I==0?Timing::BendMs:0)||Step.ToleranceMs!=(I==0?Timing::BendToleranceMs:0))return false;
        }
        if(B.Stations.Num()!=4||B.StepStations.Num()!=6||Space.Sites.Num()!=3||Space.Sites[1]!=B.Anchor)return false;
        for(int I=0;I<4;++I)if(B.Stations[I]!=FVector2D(R::Stations[I].X,R::Stations[I].Y))return false;
        for(int I=0;I<6;++I)if(B.StepStations[I]!=R::StepStations[I])return false;
    }
    else if(!B.Stations.IsEmpty()||!B.StepStations.IsEmpty())return false;
    B.bLanternWorkshop=true;
    return true;
}
