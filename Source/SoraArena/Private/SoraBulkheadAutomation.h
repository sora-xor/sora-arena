#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraLiftAutomation.h"
#include "World/SoraNavigation.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"

namespace SoraBulkheadAutomation
{
inline void FaceLever(FSoraAutomationWorld& W)
{
    auto* Hero=W.Player();
    const FRotator View=(W.Mode()->Arena()->BulkheadPoint()-Hero->GetCamera()->GetComponentLocation()).Rotation();
    Hero->GetController()->SetControlRotation(View); Hero->FaceRotation(FRotator(0,View.Yaw,0),0.f);
    Hero->GetCamera()->SetWorldRotation(View); // Headless world has no camera-manager update.
}
inline bool ApproachLever(FSoraAutomationWorld& W)
{
    auto* Nav=USoraNavigation::Get(W.GetTestWorld());
    auto* Hero=W.Player();
    const FVector Goal=W.Mode()->Arena()->BulkheadApproach();
    TArray<FVector> Path;
    if(!Nav||!Nav->Settle()||!Nav->FindPath(Hero->GetActorLocation(),Goal+FVector(0,0,90),*Hero,Path)||
        Path.IsEmpty()||FVector::Dist2D(Path.Last(),Goal)>60||FMath::Abs(Path.Last().Z-Goal.Z)>30)
    {
        UE_LOG(LogTemp,Error,TEXT("Bulkhead approach has no complete route: hero=%s goal=%s endpoint=%s"),
            *Hero->GetActorLocation().ToString(),*Goal.ToString(),Path.IsEmpty()?TEXT("none"):*Path.Last().ToString());
        return false;
    }
    for(const auto& Node:Path) if(!SoraLiftAutomation::Walk(W,Node)) return false;
    if(!SoraLiftAutomation::Walk(W,Goal)) return false;
    FaceLever(W);
    const bool Reached=FMath::Abs(Hero->GetActorLocation().Z-Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-Goal.Z)<15&&
        W.Mode()->Arena()->CanReachBulkhead(*Hero);
    if(!Reached) UE_LOG(LogTemp,Error,TEXT("Bulkhead is unreachable after normal approach: hero=%s goal=%s"),
        *Hero->GetActorLocation().ToString(),*Goal.ToString());
    return Reached;
}
inline bool SealVault(FSoraAutomationWorld& W,const FKey& Interact=EKeys::E)
{
    if(!ApproachLever(W)||!W.InjectKey(Interact,IE_Pressed)) return false;
    for(int32 Frame=0;Frame<150&&W.Mode()->Campaign()->AwaitingCapture();++Frame)
        if(!W.Tick(1)) return false;
    const bool Released=W.InjectKey(Interact,IE_Released);
    const bool Complete=!W.Mode()->Campaign()->AwaitingCapture();
    if(!Complete) UE_LOG(LogTemp,Error,TEXT("Bulkhead hold did not complete: hero=%s input=%d progress=%.3f"),
        *W.Player()->GetActorLocation().ToString(),int32(W.Mode()->InputState()),W.Mode()->Campaign()->HeldWorkProgress());
    return Released&&Complete;
}
}
#endif
