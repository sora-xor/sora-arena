#include "SoraCatalogFlood.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraFloodRules.h"

namespace SoraCatalogFlood
{
bool Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraSpace& Space)
{
    using namespace SoraCatalogJson;
    const auto V=O.TryGetField(TEXT("flood"));
    if(Beat.Id!=TEXT("ch06.b14")) return !V.IsValid();
    if(!V||V->Type!=EJson::Object) return false;
    const auto F=V->AsObject(); auto& B=Beat.Space; auto& W=B.Fieldcraft.Water;
    const auto Exact=[&](const TCHAR* Key,int32 Want)
    { const auto N=F->TryGetField(Key); double D=0; return N&&N->Type==EJson::Number&&N->TryGetNumber(D)&&D==Want; };
    const auto Point=[&](const TCHAR* Key,FVector2D& Out)
    {
        const auto* A=Rows(*F,Key); if(!A||A->Num()!=2) return false; int32 C[2]={};
        for(int32 I=0;I<2;++I) { double D=0; if(!(*A)[I]||(*A)[I]->Type!=EJson::Number||!(*A)[I]->TryGetNumber(D)||!Whole(D,C[I])) return false; }
        Out=FVector2D(C[0],C[1]); return true;
    };
    FVector2D Shaft; bool Provisional=false;
    if(!Point(TEXT("origin"),B.Flood.Origin)||!Point(TEXT("air_shaft_cm"),Shaft)||Shaft!=FVector2D(8150,8350)||
        !F->TryGetBoolField(TEXT("provisional_air_shaft"),Provisional)||!Provisional||
        !Exact(TEXT("length_cm"),9000)||!Exact(TEXT("width_cm"),240)||!Exact(TEXT("height_cm"),220)||
        !Exact(TEXT("deep_start_cm"),7500)||!Exact(TEXT("deep_floor_cm"),-200)||!Exact(TEXT("deep_roof_cm"),20)||
        !Exact(TEXT("from_cm"),40)||!Exact(TEXT("to_cm"),160)||!Exact(TEXT("rise_ms"),150000)||
        !Space.Zones.IsValidIndex(B.Zone)||Space.Zones[B.Zone].Id!=TEXT("ch06_flood_exfil")||
        B.Entry!=B.Flood.Origin+FVector2D(200,0)||B.EntryYaw!=0||B.HeightCm!=0||
        B.Exit.Center!=B.Flood.Origin+FVector2D(9500,-4300)||!B.Exit.bHeight||B.Exit.FloorCm!=200||
        !B.Fieldcraft.bWater||W.Rules.SurfaceCmS!=180||W.Rules.DiveCmS!=140||W.Rules.BreathMs!=8000||
        W.Rules.RecoverMs!=3000||W.Rules.DrownHpPerSecond!=10||B.Spawns.Num()!=6||
        !Beat.Has(SoraBeatRules::EGoal::Exit)) return false;
    const FVector2D Origin=B.Flood.Origin;
    if(Origin.Y!=0||B.Exit.Size!=FVector2D(400,300)||!B.Fieldcraft.Floors.IsEmpty()||
        W.Area.Center!=Origin+FVector2D(-100,-2000)||W.Area.Size!=FVector2D(22000,4800)||
        W.SurfaceStepPermille!=2000||B.Fieldcraft.Searchlights.Num()!=3||B.Fieldcraft.Allies.Num()!=3||
        B.Volumes.Num()!=4) return false;
    const FVector2D Posts[]={{2000,0},{4500,0},{7000,0},{9500,-700},{4000,-2100},{4150,-2100}};
    for(int32 I=0;I<6;++I) if(B.Spawns[I]!=Origin+Posts[I]) return false;
    const TCHAR* Names[]={TEXT("volume_enter:vol_ankyo_start"),TEXT("volume_enter:vol_ankyo_grate_1"),
        TEXT("volume_enter:vol_ankyo_deep"),TEXT("volume_enter:vol_water_gate_exit")};
    const FVector2D Centers[]={{300,0},{2000,0},{7500,0},{9500,-400}};
    const FVector2D Sizes[]={{600,240},{300,240},{150,240},{400,150}};
    for(int32 I=0;I<4;++I)
        if(B.Volumes[I].Event!=Names[I]||B.Volumes[I].Center!=Origin+Centers[I]||B.Volumes[I].Size!=Sizes[I]) return false;
    for(int32 I=0;I<3;++I)
    {
        const auto& Light=B.Fieldcraft.Searchlights[I];
        if(Light.At!=Origin+Posts[I]||Light.HeightCm!=210||Light.Rules.SpotCm!=180) return false;
        const auto& Ally=B.Fieldcraft.Allies[I];
        if(Ally.bDetectable||Ally.Rules.Downable) return false;
    }
    B.Flood.bEnabled=true; return true;
}
}
