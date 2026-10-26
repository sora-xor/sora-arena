#include "SoraCatalogPalace.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"

namespace SoraPalaceCatalogDetail
{
bool Point(const TSharedPtr<FJsonValue>& Value,FVector Expected,int Count)
{
    if(!Value||Value->Type!=EJson::Array||Value->AsArray().Num()!=Count) return false;
    const auto& A=Value->AsArray();
    for(int I=0;I<Count;++I)
    {
        double N=0;
        if(!A[I]||A[I]->Type!=EJson::Number||!A[I]->TryGetNumber(N)||N!=Expected[I]) return false;
    }
    return true;
}
}

bool SoraCatalogPalace::Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraSpace& Space)
{
    using namespace SoraPalaceCatalogDetail;
    namespace R=SoraRegistryRules;
    const auto V=O.TryGetField(TEXT("registry_hall"));
    const bool Registry=Beat.Id==TEXT("ch06.b08");
    if(!Registry&&Beat.Id!=TEXT("ch06.b07")) return !V.IsValid();
    auto& B=Beat.Space;
    if(!V||V->Type!=EJson::Object||!Space.Zones.IsValidIndex(B.Zone)||B.HeightCm!=0||
        Beat.Place!=TEXT("pl_uguisu_hall")) return false;
    const auto H=V->AsObject();const auto& Z=Space.Zones[B.Zone];
    const FVector Origin(Z.Rect.Min+FVector2D(600,270),0);
    int32 Width=0;
    if(H->Values.Num()!=3||Z.Rect.GetSize()!=FVector2D(5000,3670)||Z.WallHeight!=500||!Z.Cover.IsEmpty()||!Z.Props.IsEmpty()||
        !Point(H->TryGetField(TEXT("origin_cm")),Origin,2)||
        !SoraCatalogJson::Int(*H,TEXT("perimeter_width_cm"),Width)||Width!=R::PerimeterWidthCm) return false;
    const auto Desks=SoraCatalogJson::Rows(*H,TEXT("desks_cm"));
    if(!Desks||Desks->Num()!=3) return false;
    static const TCHAR* Names[]={TEXT("desk_tagata"),TEXT("desk_machikata"),TEXT("desk_shokukata")};
    if(Registry&&(B.Objectives.Num()!=3||Beat.Objectives.Num()!=3||Beat.ObjectiveHoldMs.Num()!=3||
        Beat.Task.HoldPointCount!=3)) return false;
    for(int I=0;I<3;++I)
    {
        if(!Point((*Desks)[I],Origin+FVector(R::DeskX[I],R::DeskY,R::DeskFloor[I]),3)) return false;
        if(Registry&&(B.Objectives[I]!=FVector2D(Origin)+FVector2D(R::DeskX[I],R::DeskY-110)||
            Beat.Objectives[I]!=Names[I]||Beat.ObjectiveHoldMs[I]!=30000)) return false;
    }
    B.RegistryHall.bEnabled=true;B.RegistryHall.Origin=FVector2D(Origin);
    return true;
}
