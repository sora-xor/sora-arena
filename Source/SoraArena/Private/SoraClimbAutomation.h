#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraLiftAutomation.h"
#include "SoraFieldcraft.h"
#include "Components/CapsuleComponent.h"
#include "Misc/AutomationTest.h"
namespace SoraClimbAutomation
{
inline FKey Key(ASoraPlayerCharacter& Hero,const TCHAR* Action,bool Pad=false)
{
    for(const FKey& K:Hero.GetActionKeys(Action)) if(K.IsGamepadKey()==Pad) return K;
    return FKey();
}
inline bool Begin(FSoraAutomationWorld& W,int32 Route=0,bool Pad=false)
{
    auto* D=W.Mode()->Campaign();const auto& C=D->ActiveBeatData()->Space.Climb;
    if(!C.bEnabled) return false;
    const FVector O(C.Origin,0),Foot=(Route==0?C.Corner:C.Extrusion).Points[0];
    // Walk around the wall's foot to choose a route; no stand/teleport helper.
    if(!SoraLiftAutomation::Walk(W,O+FVector(-300,Foot.Y,0))||!SoraLiftAutomation::Walk(W,O+Foot-FVector(40,0,0))) return false;
    W.Player()->GetController()->SetControlRotation(FRotator::ZeroRotator);W.Player()->FaceRotation(FRotator::ZeroRotator,0);
    return W.PressKey(Key(*W.Player(),TEXT("Jump"),Pad))&&USoraFieldcraft::Get(W.GetTestWorld())->IsClimbing();
}
inline bool ToHold(FSoraAutomationWorld& W,int32 Hold)
{
    auto* C=USoraFieldcraft::Get(W.GetTestWorld());
    for(int32 F=0;F<3600&&C->IsClimbing()&&C->ClimbHoldIndex()<Hold;++F)
        if(!W.InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return false;
    return W.InjectKey(EKeys::W,IE_Released)&&W.Tick(1)&&C->IsClimbing()&&C->ClimbHoldIndex()==Hold;
}
inline bool DownToHold(FSoraAutomationWorld& W,int32 Hold)
{
    auto* C=USoraFieldcraft::Get(W.GetTestWorld());
    for(int32 F=0;F<3600&&C->IsClimbing()&&C->ClimbHoldIndex()>Hold;++F)
        if(!W.InjectKey(EKeys::S,IE_Pressed)||!W.Tick(1)) return false;
    return W.InjectKey(EKeys::S,IE_Released)&&W.Tick(1)&&C->IsClimbing()&&C->ClimbHoldIndex()==Hold;
}
inline bool Top(FSoraAutomationWorld& W)
{
    auto* C=USoraFieldcraft::Get(W.GetTestWorld());
    for(int32 F=0;F<3600&&C->IsClimbing();++F)
        if(!W.InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return false;
    return W.InjectKey(EKeys::W,IE_Released)&&W.Tick(4)&&!C->IsClimbing()&&
        W.Player()->GetCharacterMovement()->IsMovingOnGround()&&FMath::Abs(W.Player()->GetActorLocation().Z-1690)<10;
}
inline bool Approach(FSoraAutomationWorld& W)
{
    const FVector O(W.Mode()->Campaign()->ActiveBeatData()->Space.Climb.Origin,0);
    return SoraLiftAutomation::Walk(W,O+FVector(700,0,1600))&&SoraLiftAutomation::Walk(W,O+FVector(1040,0,1640));
}
inline bool Exit(FSoraAutomationWorld& W,bool Pad=false)
{
    auto* D=W.Mode()->Campaign();const int32 Chapter=D->ChapterId,Beat=D->ActiveBeat();
    if(!W.PressKey(Key(*W.Player(),TEXT("Crouch"),Pad))||!W.Tick(3)) return false;
    auto* C=USoraFieldcraft::Get(W.GetTestWorld());
    if(!C->IsClimbCrawling()||!W.Player()->IsCrouched()||W.Player()->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()!=28) return false;
    W.Player()->GetController()->SetControlRotation(FRotator::ZeroRotator);W.Player()->FaceRotation(FRotator::ZeroRotator,0);
    for(int32 F=0;F<1000&&D->ActiveBeat()==Beat&&!W.Mode()->bDefeated;++F)
        if(!W.InjectKey(EKeys::W,IE_Pressed)||!W.Tick(1)) return false;
    if(!W.InjectKey(EKeys::W,IE_Released)||!W.Tick(3)) return false;
    return D->ChapterId==Chapter&&D->ActiveBeat()==Beat+1&&!W.Mode()->bDefeated&&
        (D->Progress().CompletedMask&SoraBeatRules::BeatBit(Beat))!=0u&&
        W.Player()->GetCapsuleComponent()->GetUnscaledCapsuleRadius()==34&&W.Player()->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight()==88;
}
inline bool Traverse(FSoraAutomationWorld& W,int32 Route=0,bool Pad=false)
{ return Begin(W,Route,Pad)&&Top(W)&&Approach(W)&&Exit(W,Pad); }
}
#endif
