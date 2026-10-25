#include "SoraCatalogHorseShell.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraHorseShellRules.h"
#include "Combat/SoraEnemyCatalog.h"
namespace SoraCatalogHorseShell
{
bool Read(const FJsonObject& O,FSoraBeat& Beat)
{
    using namespace SoraCatalogJson;
    namespace R=SoraHorseShellRules;
    const auto V=O.TryGetField(TEXT("horse_shell"));
    if(Beat.Id!=TEXT("ch02.b06")) return !V.IsValid();
    if(!V||V->Type!=EJson::Object) return false;
    const auto S=V->AsObject();
    const auto Number=[](const TSharedPtr<FJsonValue>& N,int Want)
    { double Actual=0; return N&&N->Type==EJson::Number&&N->TryGetNumber(Actual)&&Actual==Want; };
    const auto Exact=[&](const TCHAR* Key,int Want) { return Number(S->TryGetField(Key),Want); };
    const auto Text=[&](const TCHAR* Key,const TCHAR* Want)
    { FString Actual; return Str(*S,Key,Actual)&&Actual==Want; };
    const auto Targets=Rows(*S,TEXT("targets")),Range=Rows(*S,TEXT("range_cm"));
    if(S->Values.Num()!=12||!Exact(TEXT("wave"),R::Wave)||!Exact(TEXT("warning_ms"),R::WarningMs)||
       !Exact(TEXT("release_interval_ms"),R::IntervalMs)||!Exact(TEXT("flight_ms"),R::FlightMs)||
       !Exact(TEXT("arming_cm"),R::ArmingCm)||!Exact(TEXT("damage"),R::Damage)||!Exact(TEXT("radius_cm"),R::RadiusCm)||
       !Text(TEXT("archetype"),TEXT("grenadier"))||!Text(TEXT("attack"),TEXT("arcing_shell"))||
       !Text(TEXT("contact"),TEXT("armed_sphere_with_cover"))||!Targets||Targets->Num()!=2||
       !Range||Range->Num()!=2||!Number((*Range)[0],R::MinRangeCm)||!Number((*Range)[1],R::MaxRangeCm)||
       !Beat.Space.bHorseTreatment||Beat.Space.PodArrivals.Num()!=3) return false;
    for(int I=0;I<2;++I)
    {
        FString Id;
        if(!(*Targets)[I]||(*Targets)[I]->Type!=EJson::String||!(*Targets)[I]->TryGetString(Id)||Id!=Beat.Targets[I]) return false;
    }
    auto& Enemies=FSoraEnemyCatalog::Get();
    if(!Enemies.IsReady()&&!Enemies.Load()) return false;
    const auto* Kind=Enemies.Find(TEXT("grenadier"));
    if(!Kind||Kind->Behavior!=ESoraEnemyBehavior::Grenadier||Kind->Attacks.Num()!=1) return false;
    const auto& A=Kind->Attacks[0];
    if(A.Id!=TEXT("arcing_shell")||A.Kind!=ESoraEnemyAttackKind::Lob||A.Damage!=R::Damage||A.RadiusCm!=R::RadiusCm||
       A.FlightMs!=R::FlightMs||A.ArmingCm!=R::ArmingCm||A.MinRangeCm!=R::MinRangeCm||A.MaxRangeCm!=R::MaxRangeCm) return false;
    Beat.Space.bHorseShell=true; return true;
}
}
