#include "SoraCatalogCanisters.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraFuelCanisterRules.h"

bool SoraCatalogCanisters::Read(const FJsonObject& O,FSoraBeat& Beat)
{
    using namespace SoraCatalogJson;
    namespace Fuel=SoraFuelCanisterRules;
    const auto Value=O.TryGetField(TEXT("fuel_canisters"));
    if(Beat.Id!=TEXT("ch07.b08")) return !Value.IsValid();
    if(!Value||Value->Type!=EJson::Object) return false;
    const auto F=Value->AsObject(); auto& B=Beat.Space;
    const auto Exact=[&](const TCHAR* Key,int Want)
    { const auto V=F->TryGetField(Key); double N=0; return V&&V->Type==EJson::Number&&V->TryGetNumber(N)&&N==Want; };
    bool Player=false; FString Trigger;
    if(F->Values.Num()!=5||!Exact(TEXT("blast_radius_cm"),Fuel::BlastRadiusCm)||!Exact(TEXT("damage"),Fuel::Damage)||
       !F->TryGetBoolField(TEXT("hurts_player"),Player)||!Player||!Str(*F,TEXT("trigger"),Trigger)||Trigger!=TEXT("positive_ranged_hit")||
       B.HeightCm!=0||B.Wind.Kind!=TEXT("hangar")||B.Wind.Origin!=FVector2D(38000,-2250)||!Beat.Has(SoraBeatRules::EGoal::WavesCleared)) return false;
    const auto Items=Rows(*F,TEXT("items")); if(!Items||Items->Num()!=Fuel::Count) return false;
    for(int I=0;I<Fuel::Count;++I)
    {
        const auto V=(*Items)[I]; if(!V||V->Type!=EJson::Object) return false;
        const auto Item=V->AsObject(); const auto Point=Rows(*Item,TEXT("floor_cm")); FString Id;
        const FString Expected=FString::Printf(TEXT("fc_%02d"),I+1);
        if(Item->Values.Num()!=2||!Str(*Item,TEXT("id"),Id)||Id!=Expected||!Point||Point->Num()!=3) return false;
        const FVector Floor=FVector(B.Wind.Origin,0)+FVector(Fuel::LocalFeetCm[I].X,Fuel::LocalFeetCm[I].Y,0);
        for(int J=0;J<3;++J)
        {
            const auto N=(*Point)[J]; double D=0;
            if(!N||N->Type!=EJson::Number||!N->TryGetNumber(D)||D!=Floor[J]) return false;
        }
        B.FuelCanisters.Add({FName(*Id),Floor});
    }
    return true;
}
