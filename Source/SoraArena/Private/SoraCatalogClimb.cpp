#include "SoraCatalogClimb.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraClimbRules.h"

namespace SoraCatalogClimb
{
namespace
{
bool Integer(const TSharedPtr<FJsonValue>& Value, int32& Out)
{
    double Number=0;
    return Value && Value->Type==EJson::Number && Value->TryGetNumber(Number) && SoraCatalogJson::Whole(Number,Out);
}
bool Exact(const FJsonObject& Object, const TCHAR* Key, int32 Expected, int32& Out)
{
    return Integer(Object.TryGetField(Key),Out) && Out==Expected;
}
bool Point(const TSharedPtr<FJsonValue>& Value, int32 Count, int32* Out)
{
    const SoraCatalogJson::FJsonRows* Rows=nullptr;
    if(!Value || !Value->TryGetArray(Rows) || !Rows || Rows->Num()!=Count) return false;
    for(int32 I=0;I<Count;++I) if(!Integer((*Rows)[I],Out[I])) return false;
    return true;
}
bool Route(const FJsonObject& Object, bool Extrusion, FSoraClimbRoute& Out)
{
    using namespace SoraCatalogJson;
    FString Id;
    const auto* Points=Rows(Object,TEXT("points_cm"));
    const auto* Rests=Rows(Object,TEXT("rest_holds"));
    const int32 Count=Extrusion?9:15;
    if(Object.Values.Num()!=5 || !Str(Object,TEXT("id"),Id) ||
        Id!=(Extrusion?TEXT("spl_climb_extrusion"):TEXT("spl_climb_corner")) ||
        !Points || Points->Num()!=Count || !Rests || Rests->Num()!=(Extrusion?0:2) ||
        !Exact(Object,TEXT("step_ms"),SoraClimbRules::StepMs,Out.StepMs) ||
        !Object.TryGetBoolField(TEXT("exposed"),Out.bExposed) || Out.bExposed!=Extrusion) return false;
    Out.Id=FName(*Id);
    for(int32 I=0;I<Count;++I)
    {
        int32 XYZ[3]={};
        const int32 Z=Extrusion?SoraClimbRules::ExtrusionZ[I]:SoraClimbRules::CornerZ[I];
        // These two provisional approach holds clear the solid rest-shelf
        // lip before the swept runtime rises and moves inward onto the rest.
        const int32 X=!Extrusion&&(I==4||I==8)
            ? FMath::RoundToInt32(SoraClimbRules::WallX(SoraClimbRules::CornerZ[I+1]))-70-210
            : FMath::RoundToInt32(SoraClimbRules::WallX(Z))-70;
        if(!Point((*Points)[I],3,XYZ) || XYZ[0]!=X ||
            XYZ[1]!=(Extrusion?-1000:70) || XYZ[2]!=Z) return false;
        Out.Points.Add(FVector(XYZ[0],XYZ[1],XYZ[2]));
    }
    for(int32 I=0;I<Rests->Num();++I)
    {
        int32 Hold=0;
        if(!Integer((*Rests)[I],Hold) || Hold!=(I==0?5:9) ||
            Out.Points[Hold].Z!=(I==0?550:1100)) return false;
        Out.RestHolds.Add(Hold);
    }
    return true;
}
}

bool Read(const FJsonObject& Object, FSoraBeat& Beat, const FSoraSpace& Space)
{
    using namespace SoraCatalogJson;
    const auto Value=Object.TryGetField(TEXT("climb_routes"));
    if(Beat.Id!=TEXT("ch06.b03")) return !Value.IsValid();
    if(!Value || Value->Type!=EJson::Object) return false;
    const auto Data=Value->AsObject();
    const auto Corner=Child(*Data,TEXT("corner")), Extrusion=Child(*Data,TEXT("extrusion"));
    const auto Look=Child(*Data,TEXT("lookdown")), Crawl=Child(*Data,TEXT("crawl"));
    auto& B=Beat.Space;
    FSoraClimbSpace Climb;
    int32 XY[2]={}; bool Provisional=false;
    if(Data->Values.Num()!=7 || !Point(Data->TryGetField(TEXT("origin")),2,XY) || XY[1]!=0 ||
        !Exact(*Data,TEXT("height_cm"),SoraClimbRules::Height,Climb.HeightCm) ||
        !Data->TryGetBoolField(TEXT("provisional_geometry"),Provisional) || !Provisional ||
        !Corner || !Extrusion || !Route(*Corner,false,Climb.Corner) || !Route(*Extrusion,true,Climb.Extrusion) ||
        !Look || Look->Values.Num()!=3 || !Exact(*Look,TEXT("period_ms"),SoraClimbRules::PeriodMs,Climb.LookPeriodMs) ||
        !Exact(*Look,TEXT("hold_ms"),SoraClimbRules::WatchMs,Climb.LookHoldMs) ||
        !Exact(*Look,TEXT("guard_index"),0,Climb.GuardIndex) ||
        !Crawl || Crawl->Values.Num()!=5 || !Exact(*Crawl,TEXT("floor_cm"),SoraClimbRules::CrawlFloor,Climb.CrawlFloorCm) ||
        !Exact(*Crawl,TEXT("height_cm"),SoraClimbRules::CrawlHeight,Climb.CrawlHeightCm) ||
        !Exact(*Crawl,TEXT("half_width_cm"),SoraClimbRules::CrawlHalfWidth,Climb.CrawlHalfWidthCm) ||
        !Exact(*Crawl,TEXT("entry_x_cm"),SoraClimbRules::CrawlEntry,Climb.CrawlEntryX) ||
        !Exact(*Crawl,TEXT("exit_x_cm"),SoraClimbRules::CrawlExit,Climb.CrawlExitX)) return false;
    Climb.Origin=FVector2D(XY[0],XY[1]);
    const FVector2D O=Climb.Origin;
    if(!Space.Zones.IsValidIndex(B.Zone) || !Beat.Has(SoraBeatRules::EGoal::Exit) ||
        Space.Zones[B.Zone].Id!=TEXT("ch06_corner_climb") || B.Entry!=O+FVector2D(-400,70) ||
        B.EntryYaw!=0 || B.HeightCm!=0 || B.Anchor!=O+FVector2D(1700,0) ||
        B.Exit.Center!=B.Anchor || B.Exit.Size!=FVector2D(300,300) || !B.Exit.bHeight || B.Exit.FloorCm!=1650 ||
        B.Spawns.Num()!=1 || B.Spawns[0]!=O+FVector2D(650,-3800) || !B.Patrols.IsEmpty() ||
        B.Volumes.Num()!=1 || B.Volumes[0].Event!=TEXT("volume_enter:vol_climb_start") ||
        B.Volumes[0].Center!=O+FVector2D(-250,70) || B.Volumes[0].Size!=FVector2D(400,400) ||
        !B.Fieldcraft.bClimb || Beat.Guards.Num()!=1) return false;
    const auto& Zone=Space.Zones[B.Zone];
    if(Zone.Place!=TEXT("pl_ishigaki") || Zone.Style!=TEXT("citadel") || Zone.Form!=TEXT("yard") ||
        Zone.Entry!=B.Entry || Zone.EntryYaw!=0 || Zone.WallHeight!=360 || Zone.Walls.Num()!=4 ||
        Zone.Rect.Min!=O+FVector2D(-1000,-4400) || Zone.Rect.Max!=O+FVector2D(2200,1000) ||
        !Zone.Cover.IsEmpty() || !Zone.Props.IsEmpty() || !Zone.Route.IsEmpty()) return false;
    const auto& Face=B.Fieldcraft.Climb;
    const auto& R=Face.Rules;
    const auto& G=Beat.Guards[0];
    if(Face.At!=O || Face.Yaw!=180 || Face.WidthCm!=5400 || Face.DepthCm!=650 ||
        R.HeightCm!=1600 || R.Holds!=14 || R.GripPerHold!=6 || R.RegenPerSecond!=25 ||
        R.LedgeMask!=((1u<<5)|(1u<<9)) || R.HurtCm!=400 || R.HurtHp!=30 || R.LethalCm!=800 ||
        Face.LedgeEvents.Num()!=2 || Face.LedgeEvents[0]!=TEXT("volume_enter:vol_rest_ledge_1") ||
        Face.LedgeEvents[1]!=TEXT("volume_enter:vol_rest_ledge_2") || Face.TopEvent!=TEXT("volume_enter:vol_climb_top") ||
        G.Type!=TEXT("enforcer_rifle") || G.SightCm!=1800 || G.DarkSightCm!=900 || G.ViewDegrees!=60 ||
        G.HearingCm!=1000 || G.SuspicionPermille!=0 || G.bPost || G.ScanDegrees!=0 || G.ScanMs!=0 || G.TurnMs!=0)
        return false;
    if(B.Fieldcraft.Allies.Num()!=1 || B.Fieldcraft.Lamps.Num()!=1) return false;
    const auto& Ally=B.Fieldcraft.Allies[0];
    const auto& Lamp=B.Fieldcraft.Lamps[0];
    if(Ally.Id!=TEXT("npc_kohagi") || Ally.bDetectable || Ally.Rules.Downable || Ally.At!=B.Entry ||
        Lamp.Id!=TEXT("l_extrusion_strip") || Lamp.Snuff!=FSoraLamp::ESnuff::None ||
        Lamp.At!=O+FVector2D(350,-1000)) return false;
    Climb.bEnabled=true;
    B.Climb=MoveTemp(Climb);
    return true;
}
}
