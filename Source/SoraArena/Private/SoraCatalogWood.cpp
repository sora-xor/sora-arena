#include "SoraCatalogWood.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraWoodRules.h"

namespace
{
bool Point(const TSharedPtr<FJsonValue>& Value,FVector2D& Out)
{
    const TArray<TSharedPtr<FJsonValue>>* A=nullptr;
    if(!Value||!Value->TryGetArray(A)||A->Num()!=2) return false;
    int32 N[2]={};
    for(int32 I=0;I<2;++I)
    {
        double V=0;
        if(!(*A)[I]||(*A)[I]->Type!=EJson::Number||!(*A)[I]->TryGetNumber(V)||
            !SoraCatalogJson::Whole(V,N[I])) return false;
    }
    Out=FVector2D(N[0],N[1]); return true;
}
bool Integer(const FJsonObject& O,const TCHAR* Key,int32& Out)
{
    const auto V=O.TryGetField(Key); double N=0;
    return V&&V->Type==EJson::Number&&V->TryGetNumber(N)&&SoraCatalogJson::Whole(N,Out);
}
bool Path(const FJsonObject& O,const TCHAR* Key,TArray<FVector2D>& Out,int32 Count)
{
    const auto* Rows=SoraCatalogJson::Rows(O,Key);
    if(!Rows||Rows->Num()!=Count) return false;
    for(const auto& Row:*Rows)
    { FVector2D V; if(!Point(Row,V)) return false; Out.Add(V); }
    return true;
}
}
bool SoraCatalogWood::Read(const FJsonObject& Data,FSoraChapter& C)
{
    using namespace SoraCatalogJson;
    const auto Space=Child(Data,TEXT("space"));
    const int32 Index=C.BeatIndex(TEXT("ch01.b08"));
    if(Index==INDEX_NONE) return Space&&!Space->HasField(TEXT("wood"));
    const auto Wood=Space?Child(*Space,TEXT("wood")):nullptr;
    const auto* Beats=Rows(Data,TEXT("beats"));
    const auto Beat=Beats&&Beats->IsValidIndex(Index)&&(*Beats)[Index]&&(*Beats)[Index]->Type==EJson::Object
        ?(*Beats)[Index]->AsObject():nullptr;
    const auto Ext=Beat?Child(*Beat,TEXT("ext")):nullptr;
    const auto Challenge=Ext?Child(*Ext,TEXT("challenge")):nullptr;
    FString Id,Reward; int32 Distance=0;
    auto& W=C.Wood;
    if(!C.Beats.IsValidIndex(Index+1)||!Wood||!Challenge||
        !Str(*Wood,TEXT("beat"),Id)||Id!=C.Beats[Index].Id||
        !C.Rules[Index].Optional||C.Rules[Index+1].RequiresMask!=SoraBeatRules::BeatBit(Index-1)||
        !C.Beats[Index].Pois.ContainsByPredicate([](const FSoraExplorePoi& P) { return P.Id==TEXT("poi_ch01_naruko")&&P.Collectible==INDEX_NONE; })||
        !Str(*Challenge,TEXT("id"),Id)||Id!=TEXT("poi_ch01_naruko")||
        !Str(*Challenge,TEXT("reward"),Reward)||Reward!=TEXT("codex_toshiya")||
        !Integer(*Challenge,TEXT("distance_m"),Distance)||Distance!=45||
        !Str(*Wood,TEXT("reward"),Reward)||Reward!=TEXT("codex_toshiya")||
        !Integer(*Wood,TEXT("distance_cm"),Distance)||Distance!=SoraWoodRules::DistanceCm||
        !C.Beats[Index].Has(SoraBeatRules::EGoal::Exit)||C.Beats[Index].ExitEvent!=TEXT("volume_enter:vol_ch01_wood_exit")||
        !Point(Wood->TryGetField(TEXT("entry")),W.Entry)||!Point(Wood->TryGetField(TEXT("arrival")),W.Arrival)||
        !Point(Wood->TryGetField(TEXT("face_cm")),W.FaceCm)||W.FaceCm.X<=0||W.FaceCm.Y<=0||
        W.FaceCm.X>100||W.FaceCm.Y>100||
        !Path(*Wood,TEXT("approach"),W.Approach,3)||!Path(*Wood,TEXT("trail"),W.Trail,6)||
        !Path(*Wood,TEXT("terrace"),W.Terrace,5)||!Path(*Wood,TEXT("bridge"),W.Bridge,4)) return false;
    const auto* Pois=Rows(*Wood,TEXT("pois"));
    const TCHAR* Ids[]={TEXT("poi_ch01_issoseki"),TEXT("poi_ch01_vista"),TEXT("poi_ch01_sakaiishi"),TEXT("poi_ch01_hokora")};
    if(!Pois||Pois->Num()!=4) return false;
    const FVector2D Offset=W.Entry-FVector2D(-15200,3000);
    const FVector2D AuthoredPois[]={FVector2D(-10000,8800),FVector2D(-9000,2600),FVector2D(-6000,3400),FVector2D(-11800,10000)};
    for(int32 I=0;I<4;++I)
    {
        const auto P=(*Pois)[I]&&(*Pois)[I]->Type==EJson::Object?(*Pois)[I]->AsObject():nullptr; FVector2D At;
        if(!P||!Str(*P,TEXT("id"),Id)||Id!=Ids[I]||!Point(P->TryGetField(TEXT("at")),At)||
            !C.Beats[Index].Pois.ContainsByPredicate([&](const FSoraExplorePoi& Row) { return Row.Id==Id; })) return false;
        const auto& Poi=*C.Beats[Index].Pois.FindByPredicate([&](const FSoraExplorePoi& Row) { return Row.Id==Id; });
        const int32 Expected=I==SoraWoodRules::Stone?0:I==SoraWoodRules::Boundary?1:INDEX_NONE;
        if(Poi.Collectible!=Expected||At!=AuthoredPois[I]+Offset) return false;
        W.Pois.Add(At);
    }
    const auto* Target=Rows(*Wood,TEXT("naruko"));
    if(!Target||Target->Num()!=3) return false;
    for(int32 I=0;I<3;++I)
    {
        double V=0; int32 N=0;
        if(!(*Target)[I]||(*Target)[I]->Type!=EJson::Number||!(*Target)[I]->TryGetNumber(V)||!Whole(V,N)) return false;
        W.Naruko[I]=N;
    }
    if(!FMath::IsNearlyEqual(FVector::Dist(W.Naruko,FVector(W.Pois[SoraWoodRules::Vista],150)),4500.0,.001)||
        W.Approach.Last()!=W.Entry||W.Trail[0]!=W.Entry||W.Terrace[0]!=W.Approach[1]||
        W.Terrace.Last()!=W.Arrival||W.Bridge[0]!=W.Trail.Last()||W.Bridge.Last()!=W.Arrival||
        W.Trail.Last()!=C.Beats[Index].Space.Exit.Center||W.Arrival!=C.Beats[Index+1].Space.Entry) return false;
    const FVector2D AuthoredTrail[]={FVector2D(-15200,3000),FVector2D(-13000,5500),FVector2D(-10500,8000),
        FVector2D(-8000,7000),FVector2D(-5800,5800),FVector2D(-3600,5450)};
    for(int32 I=0;I<6;++I) if(W.Trail[I]!=AuthoredTrail[I]+Offset) return false;
    if(C.Space.ZoneAt(FVector(W.Entry,0))!=C.Beats[Index].Space.Zone||
        C.Space.ZoneAt(FVector(W.Arrival,0))!=C.Beats[Index+1].Space.Zone) return false;
    W.Beat=Index;
    return true;
}
