#include "SoraCatalogMoat.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraMoatRules.h"
namespace SoraCatalogMoat
{
namespace
{
bool Whole(const TSharedPtr<FJsonValue>& Value,int32& Out)
{ double N=0;return Value&&Value->Type==EJson::Number&&Value->TryGetNumber(N)&&SoraCatalogJson::Whole(N,Out); }
bool Pair(const TSharedPtr<FJsonValue>& Value,int32 A,int32 B)
{
    const SoraCatalogJson::FJsonRows* Rows=nullptr;int32 X=0,Y=0;
    return Value&&Value->TryGetArray(Rows)&&Rows&&Rows->Num()==2&&Whole((*Rows)[0],X)&&Whole((*Rows)[1],Y)&&X==A&&Y==B;
}
}
bool Read(const FJsonObject& Object,FSoraBeat& Beat,const FSoraSpace& Space)
{
    using namespace SoraCatalogJson;
    const auto Value=Object.TryGetField(TEXT("moat"));
    if(Beat.Id!=TEXT("ch06.b02"))return !Value.IsValid();
    if(!Value||Value->Type!=EJson::Object)return false;
    const auto D=Value->AsObject();const FJsonRows* Origin=Rows(*D,TEXT("origin"));int32 X=0,Y=0;
    if(!Origin||Origin->Num()!=2||!Whole((*Origin)[0],X)||!Whole((*Origin)[1],Y)||Y!=0||X>MAX_int32-23000||X<MIN_int32+1000||D->Values.Num()!=20)return false;
    const struct {const TCHAR* Key;int32 Value;} Fields[]={
        {TEXT("length_cm"),22000},{TEXT("width_cm"),3600},{TEXT("surface_cm"),0},{TEXT("bed_cm"),-240},
        {TEXT("gate_bed_cm"),-300},{TEXT("parapet_walk_cm"),1750},{TEXT("parapet_y_cm"),4860},{TEXT("gate_bottom_cm"),-180},{TEXT("gate_top_cm"),-120},
        {TEXT("float_clear_depth_cm"),80},{TEXT("hitscan_clear_depth_cm"),100},{TEXT("swim_radius_cm"),28},
        {TEXT("swim_half_height_cm"),28},{TEXT("head_offset_cm"),18},{TEXT("surface_center_cm"),-6},{TEXT("dive_center_cm"),-150}};
    for(const auto& F:Fields){int32 N=0;if(!Whole(D->TryGetField(F.Key),N)||N!=F.Value)return false;}
    bool Provisional=false;
    if(!D->TryGetBoolField(TEXT("provisional_posture"),Provisional)||!Provisional||
        !Pair(D->TryGetField(TEXT("gate_x_cm")),20600,21000)||!Pair(D->TryGetField(TEXT("gate_y_cm")),3560,3640))return false;
    auto& B=Beat.Space;const FVector2D O(X,Y);
    if(!Space.Zones.IsValidIndex(B.Zone)||!Beat.Has(SoraBeatRules::EGoal::Exit)||
        B.Entry!=O+FVector2D(1000,-100)||B.EntryYaw!=0||B.HeightCm!=0||B.Anchor!=O+FVector2D(20800,3400)||
        B.Exit.Center!=O+FVector2D(20900,4100)||B.Exit.Size!=FVector2D(1000,800)||B.Exit.bHeight||
        B.Spawns.Num()!=2||B.Spawns[0]!=O+FVector2D(19500,4860)||B.Spawns[1]!=O+FVector2D(20500,4860)||
        B.Patrols.Num()!=3||!B.Fieldcraft.bWater||Beat.Guards.Num()!=3)return false;
    const TArray<TArray<FVector2D>> Routes={{{3000,4860},{10000,4860}},{{11000,4860},{19000,4860}},
        {{4000,1800},{7500,2800},{11000,1800},{14500,800},{18000,1800},{14500,2800},{11000,1800},{7500,800}}};
    for(int32 I=0;I<3;++I)
    {
        if(B.Patrols[I].Num()!=Routes[I].Num())return false;
        for(int32 J=0;J<Routes[I].Num();++J)if(B.Patrols[I][J]!=O+Routes[I][J])return false;
        const auto& G=Beat.Guards[I];
        if(G.Type!=(I==2?TEXT("drone"):TEXT("enforcer_rifle"))||G.bPost||G.ScanDegrees||G.ScanMs||G.TurnMs||G.SuspicionPermille||
            G.SightCm!=(I==2?1200:3500)||G.DarkSightCm!=(I==2?1000:1200)||G.ViewDegrees!=(I==2?50:90)||G.HearingCm!=(I==2?600:1200))return false;
    }
    const FVector2D VC[]={{9200,1800},{13200,1800},{11500,3300},{5500,900}},VS[]={{800,2800},{400,3600},{17000,600},{3000,1000}};
    const TCHAR* Events[]={TEXT("volume_enter:vol_moat_pilings"),TEXT("volume_enter:vol_moat_boom"),TEXT("volume_enter:vol_moat_wallbase"),TEXT("volume_enter:vol_moat_lotus_1")};
    if(B.Volumes.Num()!=4)return false;
    for(int32 I=0;I<4;++I)if(B.Volumes[I].Center!=O+VC[I]||B.Volumes[I].Size!=VS[I]||B.Volumes[I].Event!=Events[I]||B.Volumes[I].bHeight)return false;
    if(Beat.Stealth.RatePermille!=800||Beat.Stealth.SearchMs!=20000||Beat.Stealth.SuspiciousAtPermille!=350)return false;
    const auto& Z=Space.Zones[B.Zone];
    if(Z.Id!=TEXT("ch06_physical_moat")||Z.Place!=TEXT("pl_citadel_moat")||Z.Entry!=B.Entry||
        Z.Rect.Min!=O+FVector2D(-1000,-1000)||Z.Rect.Max!=O+FVector2D(23000,5500)||
        !Z.Cover.IsEmpty()||!Z.Props.IsEmpty()||!Z.Route.IsEmpty())return false;
    const auto& W=B.Fieldcraft.Water;const auto& R=W.Rules;
    if(W.Area.Center!=O+FVector2D(11000,2050)||W.Area.Size!=FVector2D(22000,4900)||
        R.SurfaceCmS!=180||R.DiveCmS!=140||R.BreathMs!=8000||R.RecoverMs!=3000||R.DrownHpPerSecond!=10||
        W.SurfaceStepPermille!=1111||W.Lines.Num()!=1||W.LineNoiseCm.Num()!=1||W.LineNoiseCm[0]!=1400||
        W.Lines[0].Center!=O+FVector2D(13200,1800)||W.Lines[0].Size!=FVector2D(400,3600)||W.Cover.Num()!=4)return false;
    const FVector2D CoverCenter[]={{1000,-100},{5500,900},{11250,2600},{17500,1100}};
    const FVector2D CoverSize[]={{2000,600},{3000,1000},{2500,1200},{2000,1000}};
    for(int32 I=0;I<4;++I)if(W.Cover[I].Center!=O+CoverCenter[I]||W.Cover[I].Size!=CoverSize[I])return false;
    if(B.Fieldcraft.Allies.Num()!=1||B.Fieldcraft.Allies[0].Id!=TEXT("npc_kohagi")||
        B.Fieldcraft.Allies[0].bDetectable||B.Fieldcraft.Allies[0].At!=O+FVector2D(1200,-50)||B.Fieldcraft.Searchlights.Num()!=2)return false;
    for(int32 I=0;I<2;++I)
    {
        const auto& L=B.Fieldcraft.Searchlights[I];
        if(L.At!=O+FVector2D(I?15000:6000,4800)||L.HeightCm!=1750||L.Yaw!=-90||L.ReachCm!=3000||
            L.Rules.SweepDeg!=70||L.Rules.PeriodMs!=10000||L.Rules.SpotCm!=800||
            L.Rules.SuspiciousMs!=500||L.Rules.AlertMs!=1500||L.Rules.LockMs!=6000)return false;
    }
    B.Moat.bEnabled=true;B.Moat.Origin=O;B.Moat.FloatClearDepthCm=80;B.Moat.HitscanClearDepthCm=100;
    return true;
}
}
