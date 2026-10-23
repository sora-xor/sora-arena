#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraLiftAutomation.h"
#include "SoraFieldcraft.h"
#include "Components/CapsuleComponent.h"
namespace SoraMoatAutomation
{
inline FKey Key(ASoraPlayerCharacter& Hero,const TCHAR* Action,bool Pad=false)
{ for(const FKey& K:Hero.GetActionKeys(Action))if(K.IsGamepadKey()==Pad)return K;return FKey(); }
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
    return W.InjectKey(EKeys::W,IE_Released)&&W.Tick(2)&&Arrived;
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
    return false;
}
inline bool Recover(FSoraAutomationWorld& W)
{
    auto* C=USoraFieldcraft::Get(W.GetTestWorld());
    for(int32 F=0;F<240&&C->Readout(*W.Player()).Breath<1;++F)if(!W.Tick(1))return false;
    return C->Readout(*W.Player()).Breath>=1;
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
inline bool Exit(FSoraAutomationWorld& W,bool Pad=false)
{
    auto* D=W.Mode()->Campaign();const int32 B=D->ActiveBeat();
    const FVector O(D->ActiveBeatData()->Space.Moat.Origin,0);
    if(!ToGate(W,Pad)||!Recover(W)||!Posture(W,true,Pad)||!Swim(W,O+FVector(20800,3800,-150),true))return false;
    return D->ActiveBeat()==B+1&&(D->Progress().CompletedMask&SoraBeatRules::BeatBit(B))!=0u&&
        W.Player()->GetCapsuleComponent()->GetUnscaledCapsuleRadius()==34&&
        W.Player()->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()==88;
}
}
#endif
