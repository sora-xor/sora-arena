#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraLiftAutomation.h"
#include "SoraFieldcraft.h"
#include "Components/CapsuleComponent.h"
namespace SoraMoatAutomation
{
inline FKey Key(ASoraPlayerCharacter& Hero,const TCHAR* Action,bool Pad=false)
{ for(const FKey& K:Hero.GetActionKeys(Action))if(K.IsGamepadKey()==Pad)return K;return FKey(); }
inline void Sample(FSoraAutomationWorld& W,const TCHAR* Stage,const FVector& Goal=FVector::ZeroVector)
{
    const auto* D=W.Mode()->Campaign();const auto* B=D->ActiveBeatData();
    const auto* C=USoraFieldcraft::Get(W.GetTestWorld());const auto* P=W.Player();
    const FVector O=B&&B->Space.Moat.bEnabled?FVector(B->Space.Moat.Origin,0):FVector::ZeroVector;
    UE_LOG(LogTemp,Display,TEXT("SORA_MOAT_ROUTE: %s chapter=%d beat=%d xyz=%s goal=%s hp=%.1f defeated=%d input=%d swim=%d dive=%d gate=%d depth=%.3f breath=%.5f radius=%.1f half=%.1f"),
        Stage,D->ChapterId,D->ActiveBeat(),*(P->GetActorLocation()-O).ToString(),*(Goal-O).ToString(),P->Health,W.Mode()->bDefeated,
        int32(W.Mode()->InputState()),C->IsSwimming(),C->IsDiving(),C->MoatExitReady(),C->MoatDepth(),C->Readout(*P).Breath,
        P->GetCapsuleComponent()->GetScaledCapsuleRadius(),P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
}
inline bool Swim(FSoraAutomationWorld& W,const FVector& Goal,bool Finish=false)
{
    auto* D=W.Mode()->Campaign();const int32 Chapter=D->ChapterId,Beat=D->ActiveBeat();
    bool Arrived=false;
    for(int32 F=0;F<12000&&!W.Mode()->bDefeated;++F)
    {
        if(Finish&&D->ActiveBeat()!=Beat)
        { Arrived=D->ChapterId==Chapter&&(D->Progress().CompletedMask&SoraBeatRules::BeatBit(Beat))!=0u;break; }
        if(D->ActiveBeat()!=Beat)break;
        const FVector Delta=Goal-W.Player()->GetActorLocation();
        if(Delta.Size2D()<12){Arrived=true;break;}
        const FRotator Yaw(0,Delta.Rotation().Yaw,0);
        W.Player()->GetController()->SetControlRotation(Yaw);W.Player()->FaceRotation(Yaw,0);
        if(!W.InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1))return false;
    }
    const bool OK=W.InjectKey(EKeys::W,IE_Released)&&W.Tick(2)&&Arrived;
    if(!OK)Sample(W,TEXT("swim failed"),Goal);
    return OK;
}
inline bool Posture(FSoraAutomationWorld& W,bool Dive,bool Pad=false)
{
    auto* C=USoraFieldcraft::Get(W.GetTestWorld());
    if(Dive){if(!W.PressKey(Key(*W.Player(),TEXT("Crouch"),Pad)))return false;}
    else if(!W.PressKey(Key(*W.Player(),TEXT("Jump"),Pad)))return false;
    for(int32 F=0;F<240;++F)
    {
        if(!W.Tick(1))return false;
        if(Dive?C->MoatDepth()>131.f:!C->IsDiving()&&C->MoatDepth()<-11.f)return true;
    }
    Sample(W,Dive?TEXT("dive failed"):TEXT("surface failed"));return false;
}
inline bool Recover(FSoraAutomationWorld& W)
{
    auto* C=USoraFieldcraft::Get(W.GetTestWorld());
    for(int32 F=0;F<240&&C->Readout(*W.Player()).Breath<1;++F)if(!W.Tick(1))return false;
    const bool OK=C->Readout(*W.Player()).Breath>=1;
    if(!OK)Sample(W,TEXT("recovery failed"));
    return OK;
}
inline bool ToGate(FSoraAutomationWorld& W,bool Pad=false)
{
    const FVector O(W.Mode()->Campaign()->ActiveBeatData()->Space.Moat.Origin,0);
    // Every segment uses the same mapped movement as play. Stay outside the
    // piling field; dive only at the float line and recover in real open air.
    return Swim(W,O+FVector(3000,200,0))&&Swim(W,O+FVector(12950,200,0))&&Posture(W,true,Pad)&&
        Swim(W,O+FVector(13450,200,-150))&&Posture(W,false,Pad)&&Recover(W)&&
        Swim(W,O+FVector(20800,200,0))&&Swim(W,O+FVector(20800,3400,0));
}
inline bool ThroughGate(FSoraAutomationWorld& W,bool Pad=false)
{
    auto* D=W.Mode()->Campaign();const int32 B=D->ActiveBeat();
    const FVector O(D->ActiveBeatData()->Space.Moat.Origin,0);
    if(!Recover(W)||!Posture(W,true,Pad)||!Swim(W,O+FVector(20800,3800,-150),true))return false;
    return D->ActiveBeat()==B+1&&(D->Progress().CompletedMask&SoraBeatRules::BeatBit(B))!=0u&&
        W.Player()->GetCapsuleComponent()->GetUnscaledCapsuleRadius()==34&&
        W.Player()->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()==88;
}
inline bool Exit(FSoraAutomationWorld& W,bool Pad=false)
{
    Sample(W,TEXT("exit helper entry"));
    return ToGate(W,Pad)&&ThroughGate(W,Pad);
}
}
#endif
