#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraLiftAutomation.h"
#include "World/SoraNavigation.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"

namespace SoraSummitAutomation
{
inline void FaceSpine(FSoraAutomationWorld& W)
{
    auto* Hero=W.Player();
    const FRotator View=(W.Mode()->Arena()->SummitSpinePoint()-Hero->GetCamera()->GetComponentLocation()).Rotation();
    Hero->GetController()->SetControlRotation(View); Hero->FaceRotation(FRotator(0,View.Yaw,0),0.f);
    // Headless automation has no local camera-manager update.
    Hero->GetCamera()->SetWorldRotation(View);
}
inline bool ApproachSpine(FSoraAutomationWorld& W)
{
    auto* Nav=USoraNavigation::Get(W.GetTestWorld());
    auto* Hero=W.Player();
    const FVector Goal=W.Mode()->Arena()->SummitSpineApproach();
    TArray<FVector> Path;
    if(!Nav||!Nav->Settle()||!Nav->FindPath(Hero->GetActorLocation(),Goal+FVector(0,0,90),*Hero,Path)) return false;
    for(const auto& Point:Path) if(!SoraLiftAutomation::Walk(W,Point)) return false;
    if(!SoraLiftAutomation::Walk(W,Goal)) return false;
    FaceSpine(W);
    return FMath::Abs(Hero->GetActorLocation().Z-Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-Goal.Z)<15;
}
inline bool CutSpine(FSoraAutomationWorld& W)
{
    if(!ApproachSpine(W)||!W.Tick(95)||!W.InjectKey(EKeys::E,IE_Pressed)) return false;
    for(int32 Frame=0;Frame<120&&W.Mode()->Campaign()->AwaitingCapture();++Frame)
        if(!W.Tick(1)) return false;
    return W.InjectKey(EKeys::E,IE_Released)&&!W.Mode()->Campaign()->AwaitingCapture();
}
}
#endif
