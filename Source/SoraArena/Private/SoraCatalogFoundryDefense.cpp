#include "SoraCatalogFoundryDefense.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraFoundryDefenseRules.h"
namespace SoraCatalogFoundryDefense
{
bool Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraSpace& Space)
{
    using namespace SoraCatalogJson;
    const auto Value=O.TryGetField(TEXT("foundry_defense"));
    if(Beat.Id!=TEXT("ch05.b07")) return !Value.IsValid();
    if(!Value||Value->Type!=EJson::Object) return false;
    const auto F=Value->AsObject(); auto& B=Beat.Space; auto& D=B.FoundryDefense;
    const auto Exact=[&](const TCHAR* Key,int Want)
    { const auto V=F->TryGetField(Key); double N=0; return V&&V->Type==EJson::Number&&V->TryGetNumber(N)&&N==Want; };
    bool Provisional=false;
    if(F->Values.Num()!=10||!Exact(TEXT("furnace_target"),0)||!Exact(TEXT("kozo_target"),1)||
        !Exact(TEXT("repair_ms"),3000)||!Exact(TEXT("repair_hp"),150)||!Exact(TEXT("revive_ms"),4000)||
        !Exact(TEXT("down_limit_ms"),25000)||!Exact(TEXT("crew_drain_hp_s"),5)||
        !F->TryGetBoolField(TEXT("provisional_placement"),Provisional)||!Provisional||
        !Beat.Has(SoraBeatRules::EGoal::Survive)||Beat.Task.DurationMs!=180000||Beat.Task.TargetCount!=2||
        Beat.Task.TargetHp[0]!=1500||Beat.Task.TargetHp[1]!=300||B.Targets.Num()!=2||B.HeightCm!=0||
        !Space.Zones.IsValidIndex(B.Zone)) return false;
    const TCHAR* Names[]={TEXT("clay_tub_w"),TEXT("clay_tub_e"),TEXT("clay_tub_n"),TEXT("bellows_boy"),TEXT("bellows_worker")};
    const FVector2D Offsets[]={{-380,-380},{380,-380},{0,380},{-160,700},{160,700}};
    const auto Points=[&](const TCHAR* Key,int Count,int Start,TArray<FVector2D>& Out)
    {
        const auto A=Rows(*F,Key); if(!A||A->Num()!=Count) return false;
        for(int I=0;I<Count;++I)
        {
            const auto V=(*A)[I]; if(!V||V->Type!=EJson::Object) return false;
            const auto R=V->AsObject(); FString Id; const auto P=Rows(*R,TEXT("at"));
            if(R->Values.Num()!=2||!Str(*R,TEXT("id"),Id)||Id!=Names[Start+I]||!P||P->Num()!=2) return false;
            int C[2]={};
            for(int J=0;J<2;++J) { double N=0; if(!(*P)[J]||(*P)[J]->Type!=EJson::Number||!(*P)[J]->TryGetNumber(N)||!Whole(N,C[J])) return false; }
            const FVector2D At(C[0],C[1]);
            if(At!=B.Targets[0]+Offsets[Start+I]||!Space.Zones[B.Zone].Rect.IsInside(At+FVector2D(100,100))||
                !Space.Zones[B.Zone].Rect.IsInside(At-FVector2D(100,100))) return false;
            for(const auto& Cover:Space.Zones[B.Zone].Cover)
                if(FMath::Abs(At.X-Cover.Center.X)<=Cover.Size.X*.5+100&&FMath::Abs(At.Y-Cover.Center.Y)<=Cover.Size.Y*.5+100) return false;
            Out.Add(At);
        }
        return true;
    };
    if(!Points(TEXT("tubs"),3,0,D.Tubs)||!Points(TEXT("crew"),2,3,D.Crew)) return false;
    const auto& C=B.Fieldcraft; const auto& N=C.Nets;
    if(C.People.Num()!=3||C.People[0].Id!=TEXT("kozo")||C.People[0].Target!=1||!C.bNets||
        N.Kind!=FSoraNets::EKind::Person||N.Quarry.Num()!=2||N.Rules.WindupMs!=800||N.Rules.HaulMs!=0||
        N.Rules.CutMs!=1000||N.SaddleWeapon!=INDEX_NONE||N.SaddleSide!=0||N.bHalts||
        N.NetWaves!=TArray<int32>{2}||N.NetsPerWave!=TArray<int32>{2}||!N.ScoutWaves.IsEmpty()||
        N.CrossWave!=INDEX_NONE||N.CrossAtCm!=0||!N.LostEvent.IsEmpty()) return false;
    for(int I=0;I<2;++I)
        if(C.People[I+1].Id!=Names[I+3]||C.People[I+1].Target!=INDEX_NONE||C.People[I+1].At!=D.Crew[I]||
            C.People[I+1].Cover!=D.Crew[I]||N.Quarry[I].Index!=I+1||N.Quarry[I].Hp!=0||N.Quarry[I].Id!=Names[I+3]) return false;
    D.bEnabled=true; return true;
}
}
