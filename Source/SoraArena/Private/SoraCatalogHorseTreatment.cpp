#include "SoraCatalogHorseTreatment.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
namespace SoraCatalogHorseTreatment
{
bool Read(const FJsonObject& O,FSoraBeat& Beat)
{
    using namespace SoraCatalogJson;
    const auto V=O.TryGetField(TEXT("horse_treatment"));
    if(Beat.Id!=TEXT("ch02.b06")) return !V.IsValid();
    if(!V||V->Type!=EJson::Object) return false;
    const auto T=V->AsObject();
    const auto Exact=[&](const TCHAR* Key,int Want)
    { const auto N=T->TryGetField(Key); double Value=0; return N&&N->Type==EJson::Number&&N->TryGetNumber(Value)&&Value==Want; };
    FString Scope; const auto Targets=Rows(*T,TEXT("targets"));
    if(T->Values.Num()!=5||!Exact(TEXT("hold_ms"),2000)||!Exact(TEXT("heal_hp"),60)||!Exact(TEXT("cooldown_ms"),20000)||
        !Str(*T,TEXT("cooldown_scope"),Scope)||Scope!=TEXT("per_horse")||!Targets||Targets->Num()!=2||
        Beat.Task.Goal!=SoraBeatRules::EGoal::Survive||Beat.Task.DurationMs!=150000||Beat.Task.TargetCount!=2||
        Beat.Space.Targets.Num()!=2||Beat.Space.TargetKinds.Num()!=2||Beat.Targets.Num()!=2) return false;
    for(int Index=0;Index<2;++Index)
    {
        const FString Id=Index==0?TEXT("pack_horse_a"):TEXT("pack_horse_b"); FString Actual;
        if(!(*Targets)[Index]||(*Targets)[Index]->Type!=EJson::String||!(*Targets)[Index]->TryGetString(Actual)||Actual!=Id||
            Beat.Targets[Index]!=Id||Beat.Task.TargetHp[Index]!=400||Beat.Space.TargetKinds[Index]!=TEXT("horse")) return false;
    }
    Beat.Space.bHorseTreatment=true; return true;
}
}
