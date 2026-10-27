#include "SoraCatalogPods.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraPodRules.h"
namespace SoraCatalogPods
{
bool Read(const FJsonObject& O,FSoraBeat& Beat)
{
    using namespace SoraCatalogJson;
    namespace P=SoraPodRules;
    const auto V=O.TryGetField(TEXT("pod_arrivals"));
    if(Beat.Id!=TEXT("ch02.b06")) return !V.IsValid();
    if(!V||V->Type!=EJson::Object) return false;
    const auto R=V->AsObject(); auto& B=Beat.Space;
    const auto Number=[](const TSharedPtr<FJsonValue>& N,int Want)
    { double Value=0; return N&&N->Type==EJson::Number&&N->TryGetNumber(Value)&&Value==Want; };
    bool Allies=false; FString Contact;
    const auto Band=Rows(*R,TEXT("floor_band_cm")),Offsets=Rows(*R,TEXT("spawn_offsets_cm")),Arrivals=Rows(*R,TEXT("arrivals"));
    if(R->Values.Num()!=8||!Number(R->TryGetField(TEXT("windup_ms")),P::WindupMs)||
       !Number(R->TryGetField(TEXT("radius_cm")),P::RadiusCm)||!Number(R->TryGetField(TEXT("damage")),P::Damage)||
       !R->TryGetBoolField(TEXT("hits_allies"),Allies)||!Allies||!Str(*R,TEXT("contact"),Contact)||Contact!=TEXT("foot_center_cylinder")||
       !Band||Band->Num()!=2||!Number((*Band)[0],-P::FloorBelowCm)||!Number((*Band)[1],P::FloorAboveCm)||
       !Offsets||Offsets->Num()!=P::Members||!Arrivals||Arrivals->Num()!=P::Count||
       !B.bHorseTreatment||B.Zone!=INDEX_NONE||B.HeightCm!=0||Beat.Task.MaxAlive!=6||Beat.Task.WaveCount!=3||Beat.Waves.Num()!=3||
       B.Targets.Num()!=2||B.Targets[0]!=FVector2D(800,-1050)||B.Targets[1]!=FVector2D(1200,-1050)) return false;
    const int Positions[][2]={{-200,200},{-600,1100},{-1900,-300}},Times[]={0,45000,95000};
    const TCHAR* Names[]={TEXT("sp_pod_a_road"),TEXT("sp_pod_b_north"),TEXT("sp_pod_c_west")};
    for(int I=0;I<P::Count;++I)
    {
        const auto Offset=(*Offsets)[I];
        if(!Offset||Offset->Type!=EJson::Array||Offset->AsArray().Num()!=2||
           !Number(Offset->AsArray()[0],P::Offsets[I][0])||!Number(Offset->AsArray()[1],P::Offsets[I][1])) return false;
        const auto Row=(*Arrivals)[I]; if(!Row||Row->Type!=EJson::Object) return false;
        const auto A=Row->AsObject(); const auto At=Rows(*A,TEXT("floor_cm")); FString Id;
        if(A->Values.Num()!=4||!Str(*A,TEXT("id"),Id)||Id!=Names[I]||!Number(A->TryGetField(TEXT("wave")),I)||
           !Number(A->TryGetField(TEXT("release_ms")),Times[I])||!At||At->Num()!=3||
           !Number((*At)[0],Positions[I][0])||!Number((*At)[1],Positions[I][1])||!Number((*At)[2],0)) return false;
        const auto& Wave=Beat.Task.Waves[I];
        if(Wave.Trigger!=(I==0?SoraBeatRules::EWaveTrigger::Start:SoraBeatRules::EWaveTrigger::AfterMs)||Wave.Value!=Times[I]) return false;
        const auto& Groups=Beat.Waves[I].Groups;
        if(Groups.Num()!=(I==0?1:2)) return false;
        for(int G=0;G<Groups.Num();++G)
        {
            const FName Type=I==2&&G==0?TEXT("blade_retainer"):I==1&&G==1?TEXT("grenadier"):TEXT("enforcer_rifle");
            const int Count=I==0?3:(I==1?(G==0?2:1):(G==0?1:2));
            if(Groups[G].Type!=Type||Groups[G].Count!=Count||!Groups[G].bLethal||Groups[G].bInvulnerable) return false;
        }
        B.PodArrivals.Add({FName(Id),FVector(Positions[I][0],Positions[I][1],0)});
    }
    return true;
}
}
