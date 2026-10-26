#include "SoraCatalogTenements.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraTenementRules.h"
#include "SoraTenementDefenseRules.h"
#include "SoraTenementFindRules.h"
#include <initializer_list>

namespace
{
bool TenementNumbers(const FJsonObject& O,const TCHAR* Key,std::initializer_list<int> Want)
{
    const auto* A=SoraCatalogJson::Rows(O,Key);if(!A||A->Num()!=int(Want.size()))return false;
    int I=0;for(int E:Want){double V=0;if(!(*A)[I]||(*A)[I]->Type!=EJson::Number||!(*A)[I++]->TryGetNumber(V)||V!=E)return false;}
    return true;
}
}
bool SoraCatalogTenements::Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraChapter& Chapter)
{
    const auto& Space=Chapter.Space;
    const bool Expected=Beat.Id==TEXT("ch03.b04")||Beat.Id==TEXT("ch03.b05")||Beat.Id==TEXT("ch03.b06")||
        Beat.Id==TEXT("ch03.b13")||Beat.Id==TEXT("ch03.b14");
    const auto Value=O.TryGetField(TEXT("tenements"));
    if(!Expected)
    {
        if(Beat.Id==TEXT("ch03.b16")||Beat.Id==TEXT("ch03.b18"))
        {
            const auto& B=Beat.Space;
            if(B.Zone!=INDEX_NONE||B.Entry!=FVector2D(-350,0)||B.EntryYaw!=0.f||
               Space.ZoneAt(FVector(B.Entry,0))!=INDEX_NONE||
               Space.ZoneAt(FVector(B.Anchor,0))!=INDEX_NONE)return false;
        }
        return !Value.IsValid()&&!O.HasField(TEXT("tenement_defense"))&&!O.HasField(TEXT("tenement_finds"));
    }
    const auto H=Value.IsValid()&&Value->Type==EJson::Object?Value->AsObject():nullptr;
    auto& B=Beat.Space;
    if(!H||!Space.Zones.IsValidIndex(B.Zone))return false;
    const auto& Z=Space.Zones[B.Zone];
    namespace R=SoraTenementRules;
    const bool Explore=Beat.Id==TEXT("ch03.b04"),Recovery=Beat.Id==TEXT("ch03.b05"),
        Hideout=Beat.Id==TEXT("ch03.b06"),Oath=Beat.Id==TEXT("ch03.b13"),Fires=Beat.Id==TEXT("ch03.b14");
    int32 Units=0,Period=0;
    if(Z.Id!=TEXT("pl_ura_nagaya")||Z.Rect.Min!=FVector2D(R::MinX,R::MinY)||Z.Rect.Max!=FVector2D(R::MaxX,R::MaxY)||
       Z.Entry!=FVector2D(-2800,450)||Z.EntryYaw!=90.f||Z.WallHeight!=240.f||
       !Z.Walls.IsEmpty()||!Z.Cover.IsEmpty()||!Z.Props.IsEmpty()||!Z.Route.IsEmpty()||
       !TenementNumbers(*H,TEXT("alley_cm"),{-2890,1200,-2710,2820})||
       !TenementNumbers(*H,TEXT("unit_cm"),{270,360})||!SoraCatalogJson::Int(*H,TEXT("units_per_row"),Units)||Units!=6||
       !TenementNumbers(*H,TEXT("court_cm"),{-3400,2820,-2200,3600})||
       !TenementNumbers(*H,TEXT("dry_well_cm"),{R::WellX,R::WellY,R::Bore,R::Depth,R::Curb})||
       !TenementNumbers(*H,TEXT("hoist_cm"),{-2600,3100})||
       !TenementNumbers(*H,TEXT("hideout_cm"),{-2710,900,-2440,1200})||
       !TenementNumbers(*H,TEXT("dropoff_cm"),{-2550,1050})||
       !TenementNumbers(*H,TEXT("manager_cm"),{-3200,3600,-2400,4200})||
       !SoraCatalogJson::Int(*H,TEXT("patrol_ms"),Period)||Period!=45000)return false;
    const FVector2D Entry=Hideout?FVector2D(-2580,1050):Oath?FVector2D(-2800,3850):Fires?FVector2D(-2800,3000):FVector2D(-2800,450);
    const FVector2D Anchor=Explore?FVector2D(-2440,3330):Recovery?FVector2D(-2900,2900):
        Hideout?FVector2D(-2510,1110):Oath?FVector2D(-2800,3970):FVector2D(-3220,3250);
    if(B.Entry!=Entry||B.EntryYaw!=(Hideout?0.f:Fires?180.f:90.f)||B.HeightCm!=(Oath?45:0)||B.Anchor!=Anchor||
       B.Exit.Center!=FVector2D(-2800,650)||B.Exit.Size!=FVector2D(180,300)||
       (Explore&&(!B.bCache||B.Cache!=FVector2D(-2800,1800))))return false;
    if(Oath&&(!B.bCamera||B.CameraFrom!=FVector(-2900,3730,220)||
       B.CameraTo!=FVector(-2670,3750,210)||B.CameraLook!=FVector(-2800,3970,155)))return false;
    if(Recovery&&(B.Recovery!=FVector2D(R::WellX,R::WellY)||
       B.Pickups.Num()!=1||B.Pickups[0]!=FVector2D(-2600,3100)||B.Dropoffs.Num()!=1||B.Dropoffs[0]!=FVector2D(-2550,1050)))return false;
    if(B.Spawns.Num()!=(Recovery?2:6)||B.Patrols.Num()!=(Recovery?2:0))return false;
    if(Recovery)
    {
        for(int I=0;I<2;++I)
            if(B.Spawns[I]!=FVector2D(-4500,I*100)||B.Patrols[I].Num()!=2||
               B.Patrols[I][0]!=B.Spawns[I]||B.Patrols[I][1]!=FVector2D(-1000,I*100))return false;
    }
    else if(Fires)
    {
        for(int I=0;I<6;++I)
        {
            SoraTenementDefenseRules::FPoint P;
            if(!SoraTenementDefenseRules::Spawn(I<4?0:1,I<4?I/2:0,I%2,P)||B.Spawns[I]!=FVector2D(P.X,P.Y))return false;
        }
    }
    else
    {
        const FVector2D Spawns[]={{-2800,500},{-2800,650},{-2800,800},{-2800,950},{-3500,3600},{-3600,3400}};
        for(int I=0;I<6;++I)if(B.Spawns[I]!=Spawns[I])return false;
    }
    if(B.Fieldcraft.Floors.Num()!=1)return false;
    const auto& Floor=B.Fieldcraft.Floors[0];
    if(Floor.Kind!=FName(TEXT("dobuita"))||Floor.Area.Center!=FVector2D(-2800,2010)||Floor.Area.Size!=FVector2D(80,1620)||
       Floor.HeightCm!=0||Floor.StepPermille!=1500||Floor.CrouchPermille!=1500)return false;
    if(Fires)
    {
        if(!B.Fieldcraft.bFires||B.Fieldcraft.Fires.Points.Num()!=3||B.Volumes.Num()!=1||
           B.Volumes[0].Event!=TEXT("volume_enter:vol_b14_supply")||B.Volumes[0].Center!=FVector2D(-2400,3600)||
           B.Volumes[0].Size!=FVector2D(200,200))return false;
        const int Ys[]={2950,3250,3500};
        for(int I=0;I<3;++I)if(B.Fieldcraft.Fires.Points[I]!=FVector2D(-3320,Ys[I]))return false;
    }
    if(O.HasField(TEXT("tenement_defense"))!=Fires)return false;
    if(O.HasField(TEXT("tenement_finds"))!=Explore)return false;
    if(Explore)
    {
        const auto Finds=SoraCatalogJson::Rows(O,TEXT("tenement_finds"));
        const int32 BeatIndex=Chapter.BeatIndex(Beat.Id);
        if(!Finds||Finds->Num()!=2||!Beat.Has(SoraBeatRules::EGoal::Cache)||Beat.Rewards.Num()!=2||
           !Chapter.Rules.IsValidIndex(BeatIndex)||!Chapter.Rules[BeatIndex].Optional||
           Beat.Pois.FilterByPredicate([](const FSoraExplorePoi& P){return P.Collectible!=INDEX_NONE;}).Num()!=2)return false;
        const TCHAR* Ids[]={TEXT("poi_chalk"),TEXT("poi_balance_door")};
        const TCHAR* Items[]={TEXT("ch03.c01"),TEXT("ch03.c02")};
        for(int I=0;I<2;++I)
        {
            const auto& ValueRow=(*Finds)[I];
            const auto Row=ValueRow.IsValid()&&ValueRow->Type==EJson::Object?ValueRow->AsObject():nullptr;
            FString Id,Item;const auto P=SoraTenementFindRules::Points[I];
            const auto* Poi=Beat.Pois.FindByPredicate([&](const FSoraExplorePoi& V){return V.Id==Ids[I];});
            if(!Row||!SoraCatalogJson::Str(*Row,TEXT("id"),Id)||Id!=Ids[I]||
               !SoraCatalogJson::Str(*Row,TEXT("collectible"),Item)||Item!=Items[I]||
               !TenementNumbers(*Row,TEXT("at_cm"),{int(P.X),int(P.Y),int(P.Z)})||
               !Poi||!Chapter.Collectibles.IsValidIndex(Poi->Collectible)||Beat.Rewards[I]!=Poi->Collectible||
               Chapter.Collectibles[Poi->Collectible].Id!=Items[I]||Chapter.Collectibles[Poi->Collectible].MaskBit!=I)return false;
        }
    }
    if(Fires)
    {
        const auto D=SoraCatalogJson::Child(O,TEXT("tenement_defense"));int32 StreetSpacing=0,AirSpacing=0;
        if(!D||!TenementNumbers(*D,TEXT("hold_cm"),{-3400,2220,0,-2200,3600,600})||
           !TenementNumbers(*D,TEXT("street_cm"),{-2800,450,0})||!TenementNumbers(*D,TEXT("air_cm"),{-3500,3600,600})||
           !SoraCatalogJson::Int(*D,TEXT("street_spacing_cm"),StreetSpacing)||StreetSpacing!=120||
           !SoraCatalogJson::Int(*D,TEXT("air_spacing_cm"),AirSpacing)||AirSpacing!=200)return false;
        const auto Routes=SoraCatalogJson::Rows(*D,TEXT("flight_cm"));if(!Routes||Routes->Num()!=2)return false;
        for(int I=0;I<2;++I)
        {
            const TArray<TSharedPtr<FJsonValue>>* Legs=nullptr;
            if(!(*Routes)[I]||!(*Routes)[I]->TryGetArray(Legs)||!Legs||Legs->Num()!=2)return false;
            for(int J=0;J<2;++J)
            {
                const TArray<TSharedPtr<FJsonValue>>* Point=nullptr;
                if(!(*Legs)[J]||!(*Legs)[J]->TryGetArray(Point)||!Point||Point->Num()!=3)return false;
                const auto P=SoraTenementDefenseRules::FlightPoint(I,J);const double Want[]={P.X,P.Y,P.Z};
                for(int K=0;K<3;++K)
                { double N=0;if(!(*Point)[K]||(*Point)[K]->Type!=EJson::Number||!(*Point)[K]->TryGetNumber(N)||N!=Want[K])return false; }
            }
        }
    }
    B.bTenements=true;
    B.bTenementDefense=Fires;
    return true;
}

bool SoraCatalogTenements::ReadDefense(const FJsonObject& Params,FSoraBeat& Beat)
{
    if(Beat.Id!=TEXT("ch03.b14"))return true;
    namespace R=SoraTenementDefenseRules;
    using namespace SoraCatalogJson;
    const auto Waves=Rows(Params,TEXT("waves"));
    if(!Waves||Waves->Num()!=3||Beat.Waves.Num()!=3||Beat.Task.WaveCount!=3||
       Beat.Task.Goal!=SoraBeatRules::EGoal::Hold||Beat.Task.DurationMs!=120000||
       Beat.Task.Contest!=SoraBeatRules::EContest::Pause)return false;
    const int Marks[]={300,600,800};const TCHAR* Triggers[]={TEXT("progress_at:0.3"),TEXT("progress_at:0.6"),TEXT("progress_at:0.8")};
    for(int W=0;W<3;++W)
    {
        const auto Wave=(*Waves)[W]&&(*Waves)[W]->Type==EJson::Object?(*Waves)[W]->AsObject():nullptr;
        const auto Groups=Wave?Rows(*Wave,TEXT("enemies")):nullptr;FString Trigger;
        if(!Wave||!Groups||Groups->Num()!=R::Groups(W)||Beat.Waves[W].Groups.Num()!=R::Groups(W)||
           !Str(*Wave,TEXT("trigger"),Trigger)||Trigger!=Triggers[W]||
           Beat.Task.Waves[W].Trigger!=SoraBeatRules::EWaveTrigger::ProgressAt||Beat.Task.Waves[W].Value!=Marks[W])return false;
        const FName Entry=W==1?FName(TEXT("sp_b14_backfence_air")):FName(TEXT("sp_b14_alley_mouth"));
        for(int G=0;G<R::Groups(W);++G)
        {
            const auto Raw=(*Groups)[G]&&(*Groups)[G]->Type==EJson::Object?(*Groups)[G]->AsObject():nullptr;
            FString Kind,Spawn;int32 Count=0;auto& Group=Beat.Waves[W].Groups[G];
            const FName Expected(UTF8_TO_TCHAR(R::Kind(W,G)));
            if(!Raw||!Str(*Raw,TEXT("type"),Kind)||FName(*Kind)!=Expected||!Int(*Raw,TEXT("count"),Count)||Count!=R::Count(W,G)||
               !Str(*Raw,TEXT("spawn"),Spawn)||FName(*Spawn)!=Entry||Group.Type!=Expected||Group.Count!=Count||
               Group.bInvulnerable||Group.bLethal==(Expected==TEXT("bound_conscript")))return false;
            Group.Spawn=Entry;
        }
    }
    return true;
}
