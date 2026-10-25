#include "SoraCatalogPress.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraPressRules.h"

namespace SoraPressCatalogDetail
{
bool Number(const FJsonObject& O,const TCHAR* Key,int Expected)
{
    const auto V=O.TryGetField(Key); double N=0;
    return V&&V->Type==EJson::Number&&V->TryGetNumber(N)&&N==Expected;
}
bool Point(const FJsonObject& O,const TCHAR* Key,const FVector2D& Expected)
{
    const auto Rows=SoraCatalogJson::Rows(O,Key);
    if(!Rows||Rows->Num()!=2) return false;
    for(int I=0;I<2;++I)
    {
        double N=0; const auto V=(*Rows)[I];
        if(!V||V->Type!=EJson::Number||!V->TryGetNumber(N)||N!=Expected[I]) return false;
    }
    return true;
}
}
bool SoraCatalogPress::Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraSpace& Space)
{
    using namespace SoraCatalogJson;
    using namespace SoraPressCatalogDetail;
    namespace Press=SoraPressRules;
    const auto V=O.TryGetField(TEXT("press_hall"));
    if(Beat.Id!=TEXT("ch06.b11")) return !V.IsValid();
    auto& B=Beat.Space;
    if(!V||V->Type!=EJson::Object||!Space.Zones.IsValidIndex(B.Zone)||B.HeightCm!=0||
        !Beat.Is(SoraBeatRules::EType::StealthZone)||Beat.Place!=TEXT("pl_press_hall")||
        B.Objectives.Num()!=4||Beat.Objectives.Num()!=4||Beat.ObjectiveHoldMs.Num()!=4||Beat.ObjectiveHoldMs[3]!=0) return false;
    const auto H=V->AsObject(); const auto& Zone=Space.Zones[B.Zone]; const FVector2D Origin=Zone.Rect.Min;
    if(H->Values.Num()!=7||Zone.Rect.GetSize()!=FVector2D(4200,2400)||!Zone.Cover.IsEmpty()||
        !Point(*H,TEXT("origin_cm"),Origin)||!Number(*H,TEXT("period_ms"),Press::PeriodMs)||
        !Number(*H,TEXT("window_ms"),Press::WindowMs)||!Number(*H,TEXT("radius_cm"),Press::RadiusCm)||
        !Number(*H,TEXT("noise_permille"),Press::NoisePermille)||!Number(*H,TEXT("inspection_ms"),Press::InspectionMs)) return false;
    const auto Items=Rows(*H,TEXT("presses")); if(!Items||Items->Num()!=Press::Count) return false;
    static const TCHAR* Names[]={TEXT("press_a1"),TEXT("press_a2"),TEXT("press_a3"),TEXT("press_b1"),
        TEXT("press_b2"),TEXT("press_b3"),TEXT("press_c1"),TEXT("press_c2")};
    for(int I=0;I<Press::Count;++I)
    {
        const auto Row=(*Items)[I]; if(!Row||Row->Type!=EJson::Object) return false;
        const auto P=Row->AsObject(); FString Id;
        const FVector2D Center=Origin+FVector2D(Press::Centers[I].X,Press::Centers[I].Y);
        const int Objective=Press::Objective(I);
        if(P->Values.Num()!=4||!Str(*P,TEXT("id"),Id)||Id!=Names[I]||
            !Point(*P,TEXT("center_cm"),Center)||!Point(*P,TEXT("work_cm"),Center-FVector2D(0,240))||
            !Number(*P,TEXT("objective"),Objective)) return false;
        if(Objective>=0&&(!Beat.ObjectiveHoldMs.IsValidIndex(Objective)||Beat.ObjectiveHoldMs[Objective]!=Press::JamMs||
            Beat.Objectives[Objective]!=Id||B.Objectives[Objective]!=Center-FVector2D(0,240))) return false;
    }
    if(Beat.Objectives[3]!=TEXT("exit")||B.Objectives[3]!=Origin+FVector2D(4000,200)) return false;
    B.PressHall.bEnabled=true; B.PressHall.Origin=Origin;
    return true;
}
