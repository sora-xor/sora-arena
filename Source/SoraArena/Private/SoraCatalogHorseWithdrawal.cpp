#include "SoraCatalogHorseWithdrawal.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraHorseWithdrawalRules.h"
namespace SoraCatalogHorseWithdrawal
{
bool Read(const FJsonObject& O,FSoraBeat& Beat)
{
    using namespace SoraCatalogJson;
    namespace R=SoraHorseWithdrawalRules;
    const auto V=O.TryGetField(TEXT("horse_withdrawal"));
    if(Beat.Id!=TEXT("ch02.b06")) return !V.IsValid();
    if(!V||V->Type!=EJson::Object) return false;
    const auto S=V->AsObject();
    const auto Number=[](const TSharedPtr<FJsonValue>& N,int Want)
    { double Actual=0; return N&&N->Type==EJson::Number&&N->TryGetNumber(Actual)&&Actual==Want; };
    const auto Exact=[&](const TCHAR* Key,int Want) { return Number(S->TryGetField(Key),Want); };
    const auto Text=[&](const TCHAR* Key,const TCHAR* Want)
    { FString Actual; return Str(*S,Key,Actual)&&Actual==Want; };
    const auto Floor=Rows(*S,TEXT("floor_cm"));
    if(S->Values.Num()!=8||!Exact(TEXT("arrival_cm"),R::ArrivalCm)||
       !Exact(TEXT("pace_permille"),R::PacePermille)||!Exact(TEXT("floor_tolerance_cm"),R::FloorToleranceCm)||
       !Text(TEXT("muster"),TEXT("ps_gate_yard_start"))||
       !Text(TEXT("event"),TEXT("event:horse_defense_withdrawal"))||
       !Text(TEXT("bark"),TEXT("ch02.b02.enforcer.009"))||
       !Text(TEXT("completion"),TEXT("arrived_survivors_and_finished_bark"))||
       !Floor||Floor->Num()!=3||!Number((*Floor)[0],R::GoalX)||!Number((*Floor)[1],R::GoalY)||
       !Number((*Floor)[2],R::GoalZ)||!Beat.Space.bHorseShell||Beat.Space.Zone!=-1||Beat.Space.HeightCm!=0||
       Beat.Task.Goal!=SoraBeatRules::EGoal::Survive||Beat.Task.DurationMs!=150000) return false;
    Beat.Space.bHorseWithdrawal=true; return true;
}
}
