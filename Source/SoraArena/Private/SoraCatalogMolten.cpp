#include "SoraCatalogMolten.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraMoltenRules.h"
namespace SoraCatalogMolten
{
bool Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraSpace& Space)
{
    using namespace SoraCatalogJson;
    namespace M=SoraMoltenRules;
    const auto Value=O.TryGetField(TEXT("molten_channels"));
    if(Beat.Id!=TEXT("ch05.b15")) return !Value.IsValid();
    if(!Value||Value->Type!=EJson::Object) return false;
    const auto F=Value->AsObject(); auto& B=Beat.Space;
    const auto Exact=[&](const TCHAR* Key,int Want)
    { const auto V=F->TryGetField(Key); double N=0; return V&&V->Type==EJson::Number&&V->TryGetNumber(N)&&N==Want; };
    FString Interpretation,Destroyed; bool Credit=false,Placement=false;
    if(F->Values.Num()!=13||!Exact(TEXT("cycle_ms"),M::CycleMs)||!Exact(TEXT("warning_ms"),M::WarningMs)||
       !Exact(TEXT("flow_ms"),M::FlowMs)||!Exact(TEXT("player_dps"),M::PlayerDps)||
       !Exact(TEXT("burn_ms"),M::BurnMs)||!Exact(TEXT("burn_dps"),M::PlayerDps)||
       !Exact(TEXT("enemy_dps"),M::EnemyDps)||!Exact(TEXT("floor_z_cm"),0)||
       !Str(*F,TEXT("burn_rate_interpretation"),Interpretation)||Interpretation!=TEXT("same_as_contact_nonstacking_refresh")||
       !Str(*F,TEXT("destroy_enemy"),Destroyed)||Destroyed!=TEXT("loom_automaton")||
       !F->TryGetBoolField(TEXT("environmental_kills_count"),Credit)||!Credit||
       !F->TryGetBoolField(TEXT("provisional_placement"),Placement)||!Placement||B.HeightCm!=0||
       !Space.Zones.IsValidIndex(B.Zone)||!Beat.Has(SoraBeatRules::EGoal::WavesCleared)) return false;
    const auto RowsOf=Rows(*F,TEXT("channels"));
    if(!RowsOf||RowsOf->Num()!=M::Channels) return false;
    const int Y[]={-1000,-350,350,1000};
    for(int I=0;I<M::Channels;++I)
    {
        const auto V=(*RowsOf)[I]; if(!V||V->Type!=EJson::Object) return false;
        const auto R=V->AsObject(); const auto Center=Rows(*R,TEXT("center")),Size=Rows(*R,TEXT("size"));
        if(R->Values.Num()!=2||!Center||!Size||Center->Num()!=2||Size->Num()!=2) return false;
        const int Want[]={68200,Y[I],2500,80};
        for(int J=0;J<4;++J)
        {
            const auto N=J<2?(*Center)[J]:(*Size)[J-2]; double D=0;
            if(!N||N->Type!=EJson::Number||!N->TryGetNumber(D)||D!=Want[J]) return false;
        }
        FSoraVolume Strip; Strip.Center=FVector2D(Want[0],Want[1]); Strip.Size=FVector2D(Want[2],Want[3]);
        const auto& Zone=Space.Zones[B.Zone];
        if(!Zone.Rect.IsInside(Strip.Center+Strip.Size*.5)||!Zone.Rect.IsInside(Strip.Center-Strip.Size*.5)) return false;
        for(const auto& Cover:Zone.Cover)
            if(FMath::Abs(Strip.Center.X-Cover.Center.X)<(Strip.Size.X+Cover.Size.X)*.5&&
               FMath::Abs(Strip.Center.Y-Cover.Center.Y)<(Strip.Size.Y+Cover.Size.Y)*.5) return false;
        B.Molten.Channels.Add(Strip);
    }
    B.Molten.bEnabled=true; return true;
}
}
