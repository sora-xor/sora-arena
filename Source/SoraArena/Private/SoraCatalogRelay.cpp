#include "SoraCatalogRelay.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"
#include "SoraRelayRules.h"

namespace SoraRelayCatalogDetail
{
bool Number(const FJsonObject& O,const TCHAR* Key,int Expected)
{
    const auto V=O.TryGetField(Key); double N=0;
    return V&&V->Type==EJson::Number&&V->TryGetNumber(N)&&N==Expected;
}
bool Point(const TSharedPtr<FJsonValue>& V,const FVector& Expected,int Count)
{
    if(!V||V->Type!=EJson::Array) return false;
    const auto& A=V->AsArray(); if(A.Num()!=Count) return false;
    for(int I=0;I<Count;++I)
    {
        double N=0;
        if(!A[I]||A[I]->Type!=EJson::Number||!A[I]->TryGetNumber(N)||N!=Expected[I]) return false;
    }
    return true;
}
}

bool SoraCatalogRelay::Read(const FJsonObject& O,FSoraBeat& Beat,const FSoraSpace& Space)
{
    using namespace SoraRelayCatalogDetail;
    namespace R=SoraRelayRules;
    const auto V=O.TryGetField(TEXT("relay_room"));
    if(Beat.Id!=TEXT("ch06.b04")) return !V.IsValid();
    auto& B=Beat.Space;
    if(!V||V->Type!=EJson::Object||!Space.Zones.IsValidIndex(B.Zone)||B.HeightCm!=0||
        Beat.Place!=TEXT("pl_relay_room")||!Beat.Is(SoraBeatRules::EType::StealthZone)||
        B.Objectives.Num()!=4||Beat.Objectives.Num()!=4||Beat.ObjectiveHoldMs.Num()!=4||Beat.Guards.Num()!=4) return false;
    const auto H=V->AsObject(); const auto& Zone=Space.Zones[B.Zone]; const FVector Origin(Zone.Rect.Min,0);
    if(H->Values.Num()!=15||Zone.Rect.GetSize()!=FVector2D(2000,1000)||!Zone.Cover.IsEmpty()||
        !Point(H->TryGetField(TEXT("origin_cm")),Origin,2)||
        !Number(*H,TEXT("period_ms"),R::PeriodMs)||!Number(*H,TEXT("exposed_ms"),R::ExposedMs)||
        !Number(*H,TEXT("gap_ms"),R::GapMs)||!Number(*H,TEXT("pull_ms"),R::PullMs)||
        !Number(*H,TEXT("caught_suspicion_permille"),R::CaughtSuspicionPermille)||
        !Number(*H,TEXT("fan_lock_ms"),R::FanLockMs)||!Number(*H,TEXT("nodes_lock_ms"),R::NodesLockMs)||
        !Number(*H,TEXT("reinforcement_delay_ms"),R::ReinforcementDelayMs)||
        !Number(*H,TEXT("reinforcement_count"),R::ReinforcementCount)||!Number(*H,TEXT("lamp_notice_ms"),R::LampNoticeMs)||
        !Number(*H,TEXT("gallery_height_cm"),R::GalleryHeightCm)||!Number(*H,TEXT("gallery_width_cm"),R::GalleryWidthCm)) return false;
    const auto Nodes=SoraCatalogJson::Rows(*H,TEXT("nodes_cm")),Work=SoraCatalogJson::Rows(*H,TEXT("work_cm"));
    if(!Nodes||!Work||Nodes->Num()!=3||Work->Num()!=3) return false;
    static const TCHAR* Names[]={TEXT("node_w"),TEXT("node_e"),TEXT("node_n")};
    for(int I=0;I<3;++I)
    {
        const auto N=R::Nodes[I],W=R::Work[I];
        if(!Point((*Nodes)[I],Origin+FVector(N.X,N.Y,N.Z),3)||!Point((*Work)[I],Origin+FVector(W.X,W.Y,W.Z),3)||
            B.Objectives[I]!=Zone.Rect.Min+FVector2D(W.X,W.Y)||Beat.Objectives[I]!=Names[I]||
            Beat.ObjectiveHoldMs[I]!=R::PullMs) return false;
    }
    if(B.Entry!=Zone.Rect.Min+FVector2D(180,500)||B.EntryYaw!=0||
        Beat.Objectives[3]!=TEXT("exit")||Beat.ObjectiveHoldMs[3]!=0||
        B.Objectives[3]!=Zone.Rect.Min+FVector2D(1850,500)||B.Exit.Center!=B.Objectives[3]||
        B.Exit.Size!=FVector2D(300,300)||!B.Exit.bHeight||B.Exit.FloorCm!=0) return false;
    for(int I=0;I<4;++I)
        if(Beat.Guards[I].Type!=(I<2?TEXT("enforcer_rifle"):I==2?TEXT("auditor"):TEXT("drone"))||
            Beat.Guards[I].bPost!=(I==2)) return false;
    if(B.Volumes.Num()!=1||B.Fieldcraft.Lamps.Num()!=2) return false;
    const auto& Entry=B.Volumes[0];
    if(Entry.Event!=TEXT("volume_enter:vol_relay_entry")||!Entry.bHeight||Entry.FloorCm!=0||
        Entry.Center!=Zone.Rect.Min+FVector2D(180,500)||Entry.Size!=FVector2D(300,300)) return false;
    for(int I=0;I<2;++I)
    {
        const auto& L=B.Fieldcraft.Lamps[I];
        if(L.Id!=(I==0?TEXT("l_worklamp_se"):TEXT("l_worklamp_nw"))||L.Kind!=TEXT("lamp")||
            L.At!=Zone.Rect.Min+(I==0?FVector2D(1900,100):FVector2D(100,900))||
            L.RadiusCm!=700||L.Snuff!=FSoraLamp::ESnuff::Hold||L.HoldMs!=1000||L.RelightMs!=0) return false;
    }
    B.RelayRoom.bEnabled=true;B.RelayRoom.Origin=Zone.Rect.Min;
    return true;
}
