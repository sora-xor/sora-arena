#include "SoraCatalogLedger.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraLedgerRules.h"

namespace SoraLedgerCatalogDetail
{
bool Point(const FJsonObject& O,const TCHAR* Key,const FVector2D& Expected)
{
    const auto A=SoraCatalogJson::Rows(O,Key);
    if(!A||A->Num()!=2) return false;
    for(int I=0;I<2;++I)
    { double N=0;if(!(*A)[I]||(*A)[I]->Type!=EJson::Number||!(*A)[I]->TryGetNumber(N)||N!=Expected[I]) return false; }
    return true;
}
bool Area(const FSoraVolume& V,const FVector2D& Center,const FVector2D& Size)
{ return V.Center==Center&&V.Size==Size&&!V.bHeight; }
bool Fieldcraft(const FSoraBeatSpace& B,const FVector2D& O,const FVector2D& P)
{
    const auto& F=B.Fieldcraft;
    if(F.Floors.Num()!=10||!F.bStones||F.Stones.Piles.Num()!=3||F.Alarms.Num()!=2||B.Volumes.Num()!=4) return false;
    const TCHAR* Kinds[]={TEXT("nightingale_floor"),TEXT("nightingale_floor"),TEXT("gravel"),TEXT("tatami"),TEXT("tatami"),
        TEXT("puddle"),TEXT("puddle"),TEXT("puddle"),TEXT("edge_strip"),TEXT("edge_strip")};
    const FVector2D Centers[]={P+FVector2D(900,-135),P+FVector2D(2535,965),P+FVector2D(1200,800),
        P+FVector2D(600,-670),P+FVector2D(1800,-670),O+FVector2D(280,500),O+FVector2D(1160,6200),
        O+FVector2D(2040,600),P+FVector2D(900,-260),P+FVector2D(2660,1100)};
    const FVector2D Sizes[]={FVector2D(3000,270),FVector2D(270,2470),FVector2D(2400,1600),
        FVector2D(1200,800),FVector2D(1200,800),FVector2D(200,200),FVector2D(200,200),FVector2D(200,200),
        FVector2D(3000,20),FVector2D(20,2200)};
    const int Step[]={4000,4000,1500,500,500,1500,1500,1500,4000,4000};
    const int Crouch[]={5000,5000,1500,500,500,1500,1500,1500,0,0};
    for(int I=0;I<10;++I)
        if(F.Floors[I].Kind!=Kinds[I]||F.Floors[I].HeightCm!=0||!Area(F.Floors[I].Area,Centers[I],Sizes[I])||
            F.Floors[I].StepPermille!=Step[I]||F.Floors[I].CrouchPermille!=Crouch[I]) return false;
    const FVector2D Piles[]={FVector2D(1160,1200),FVector2D(720,4400),FVector2D(1600,6000)};
    for(int I=0;I<3;++I) if(F.Stones.Piles[I]!=O+Piles[I]) return false;
    if(F.Alarms[0].At!=O+FVector2D(280,2800)||F.Alarms[1].At!=O+FVector2D(2040,4400)) return false;
    const TCHAR* Events[]={TEXT("volume_enter:vol_rubble_c1"),TEXT("volume_enter:vol_aisle_c2"),
        TEXT("volume_enter:vol_uguisu_entry"),TEXT("volume_enter:vol_sugido")};
    const FVector2D VolCenters[]={O+FVector2D(1160,1200),O+FVector2D(1160,2800),P+FVector2D(-300,-135),P+FVector2D(2540,2500)};
    const FVector2D VolSizes[]={FVector2D(320,320),FVector2D(2400,320),FVector2D(400,270),FVector2D(500,400)};
    for(int I=0;I<4;++I)
        if(B.Volumes[I].Event!=Events[I]||!Area(B.Volumes[I],VolCenters[I],VolSizes[I])) return false;
    return true;
}
}
bool SoraCatalogLedger::ReadLockdown(const FJsonObject& Params,FSoraBeat& Beat)
{
    if(Beat.Id!=TEXT("ch06.b06")) return true;
    using namespace SoraCatalogJson;
    const auto Waves=Rows(Params,TEXT("waves"));
    FString Policy,Id,Trigger;TArray<FString> Effects;
    if(!Waves||Waves->Num()!=1||Beat.Waves.Num()!=1||
        !Str(Params,TEXT("on_detected"),Policy)||Policy!=TEXT("reinforce:w_lockdown")) return false;
    const auto W=(*Waves)[0]&&(*Waves)[0]->Type==EJson::Object?(*Waves)[0]->AsObject():nullptr;
    const auto Groups=W?Rows(*W,TEXT("enemies")):nullptr;
    if(!W||!Groups||Groups->Num()!=2||!Str(*W,TEXT("id"),Id)||Id!=TEXT("w_lockdown")||
        !Str(*W,TEXT("trigger"),Trigger)||Trigger!=TEXT("ai_event:alarm_raised")||
        !Strings(Rows(*W,TEXT("effects")),Effects)||Effects.Num()!=1||Effects[0]!=TEXT("shutter_c3_closed_30s")) return false;
    auto& Wave=Beat.Waves[0];
    if(Wave.Id!=Id||Wave.Event!=Trigger||Wave.Groups.Num()!=2||Beat.Task.ReinforceWave!=0||
        Beat.Task.OnDetected!=SoraBeatRules::EDetected::Reinforce||Beat.Task.ReinforceOnDetection) return false;
    for(int I=0;I<2;++I)
    {
        const auto G=(*Groups)[I]&&(*Groups)[I]->Type==EJson::Object?(*Groups)[I]->AsObject():nullptr;
        FString Type,Spawn;int32 Count=0;
        const FString Expected=I==0?TEXT("sp_aisle_north_door"):TEXT("sp_aisle_south_door");
        auto& Group=Wave.Groups[I];
        if(!G||!Str(*G,TEXT("type"),Type)||Type!=TEXT("enforcer_rifle")||
            !Int(*G,TEXT("count"),Count)||Count!=2||!Str(*G,TEXT("spawn"),Spawn)||Spawn!=Expected||
            Group.Type!=FName(*Type)||Group.Count!=Count||!Group.bLethal||Group.bInvulnerable) return false;
        Group.Spawn=FName(*Spawn);
    }
    return true;
}
bool SoraCatalogLedger::Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraSpace& Space)
{
    using namespace SoraLedgerCatalogDetail;
    namespace R=SoraLedgerRules;
    const auto V=O.TryGetField(TEXT("ledger_hall"));
    const bool Stealth=Beat.Id==TEXT("ch06.b06");
    if(!Stealth&&Beat.Id!=TEXT("ch06.b05")) return !V.IsValid();
    auto& B=Beat.Space;
    if(!V||V->Type!=EJson::Object||!Space.Zones.IsValidIndex(B.Zone)||B.HeightCm!=0) return false;
    const auto H=V->AsObject();const auto& Z=Space.Zones[B.Zone];int32 PalaceZone=INDEX_NONE;
    if(H->Values.Num()!=3||!SoraCatalogJson::Int(*H,TEXT("palace_zone"),PalaceZone)||!Space.Zones.IsValidIndex(PalaceZone)) return false;
    const auto& P=Space.Zones[PalaceZone];
    const FVector2D Palace(P.Rect.Min.X+600,P.Rect.Max.Y-3400),Origin=Palace-FVector2D(3000,6670);
    if(Z.Place!=TEXT("pl_ledger_corridors")||P.Place!=TEXT("pl_uguisu_hall")||
        Z.Rect.Min!=Origin-FVector2D(1000,0)||Z.Rect.Max!=Origin+FVector2D(2400,6670)||
        P.Rect.GetSize()!=FVector2D(5000,4470)||Z.WallHeight!=600||!Z.Walls.IsEmpty()||!Z.Cover.IsEmpty()||!Z.Props.IsEmpty()||
        Z.Entry!=Origin+FVector2D(-700,400)||Z.EntryYaw!=0||
        !Point(*H,TEXT("origin_cm"),Origin)||!Point(*H,TEXT("palace_origin_cm"),Palace)) return false;
    if(Stealth)
    {
        if(Beat.Guards.Num()!=R::GuardCount||B.Spawns.Num()!=R::GuardCount||B.Patrols.Num()!=R::GuardCount||
            B.Entry!=Origin+FVector2D(280,400)||B.EntryYaw!=90||B.Anchor!=Origin+FVector2D(1160,1200)||
            !Area(B.Exit,Palace+FVector2D(2540,2500),FVector2D(500,400))||!Fieldcraft(B,Origin,Palace)) return false;
        for(int I=0;I<R::GuardCount;++I)
        {
            const auto& G=Beat.Guards[I];const auto& Loop=B.Patrols[I];
            const FName Kind=I<4||I==8||I==9?TEXT("auditor"):I==6||I==7?TEXT("drone"):TEXT("enforcer_rifle");
            if(G.Type!=Kind||G.bPost!=R::IsPost(I)||Loop.Num()!=R::PointCount(I)||B.Spawns[I]!=Loop[0]) return false;
            if((I==4||I==5)&&(G.ScanDegrees!=90||G.ScanMs!=8000)) return false;
            for(int J=0;J<Loop.Num();++J)
            {
                const auto At=R::Points[I][J];
                if(Loop[J]!=(I<8?Origin:Palace)+FVector2D(At.X,At.Y)) return false;
            }
        }
    }
    else
    {
        if(B.Entry!=Origin+FVector2D(-700,400)||B.EntryYaw!=0||B.Anchor!=Origin+FVector2D(-350,400)||
            B.Spawns.Num()!=6||B.Patrols.Num()!=1||B.Patrols[0].Num()!=2||
            B.Patrols[0][0]!=Origin+FVector2D(280,600)||B.Patrols[0][1]!=Origin+FVector2D(280,1000)||
            !Area(B.Exit,Origin+FVector2D(280,400),FVector2D(300,300))) return false;
        for(const auto& At:B.Spawns) if(At!=Origin+FVector2D(280,600)) return false;
    }
    B.LedgerHall.bEnabled=true;B.LedgerHall.Origin=Origin;B.LedgerHall.PalaceOrigin=Palace;
    B.LedgerHall.PalaceZone=PalaceZone;
    return true;
}
