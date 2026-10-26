#include "SoraCatalogTenements.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraTenementRules.h"
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
bool SoraCatalogTenements::Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraSpace& Space)
{
    const bool Expected=Beat.Id==TEXT("ch03.b04")||Beat.Id==TEXT("ch03.b05")||Beat.Id==TEXT("ch03.b06")||
        Beat.Id==TEXT("ch03.b13")||Beat.Id==TEXT("ch03.b14");
    const auto Value=O.TryGetField(TEXT("tenements"));
    if(!Expected)return !Value.IsValid();
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
        if(!B.Fieldcraft.bFires||B.Fieldcraft.Fires.Points.Num()!=3)return false;
        const int Ys[]={2950,3250,3500};
        for(int I=0;I<3;++I)if(B.Fieldcraft.Fires.Points[I]!=FVector2D(-3320,Ys[I]))return false;
    }
    B.bTenements=true;
    return true;
}
