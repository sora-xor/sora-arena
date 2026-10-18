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
    if(!Nav||!Nav->Settle()||!Nav->FindPath(Hero->GetActorLocation(),Goal+FVector(0,0,90),*Hero,Path)||
        Path.IsEmpty()||FVector::Dist2D(Path.Last(),Goal)>60||FMath::Abs(Path.Last().Z-Goal.Z)>30)
    {
        UE_LOG(LogTemp,Error,TEXT("Spine approach has no complete route: hero=%s goal=%s endpoint=%s"),
            *Hero->GetActorLocation().ToString(),*Goal.ToString(),Path.IsEmpty()?TEXT("none"):*Path.Last().ToString());
        return false;
    }
    for(int32 Node=0;Node<Path.Num();++Node)
        if(!SoraLiftAutomation::Walk(W,Path[Node]))
        {
            UE_LOG(LogTemp,Error,TEXT("Spine approach walk failed: node=%d hero=%s goal=%s base=%s"),
                Node,*Hero->GetActorLocation().ToString(),*Path[Node].ToString(),*GetNameSafe(Hero->GetMovementBaseObject()));
            return false;
        }
    if(!SoraLiftAutomation::Walk(W,Goal)) return false;
    FaceSpine(W);
    const bool Reached=FMath::Abs(Hero->GetActorLocation().Z-Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-Goal.Z)<15&&
        W.Mode()->Arena()->CanReachSummitSpine(*Hero);
    if(!Reached) UE_LOG(LogTemp,Error,TEXT("Spine seam is unreachable after approach: hero=%s goal=%s movement=%d"),
        *Hero->GetActorLocation().ToString(),*Goal.ToString(),int32(Hero->GetCharacterMovement()->MovementMode));
    return Reached;
}
inline bool CutSpine(FSoraAutomationWorld& W)
{
    if(!ApproachSpine(W)||!W.Tick(95)||!W.InjectKey(EKeys::E,IE_Pressed)) return false;
    for(int32 Frame=0;Frame<120&&W.Mode()->Campaign()->AwaitingCapture();++Frame)
        if(!W.Tick(1)) return false;
    const bool Released=W.InjectKey(EKeys::E,IE_Released);
    const bool Complete=!W.Mode()->Campaign()->AwaitingCapture();
    if(!Complete) UE_LOG(LogTemp,Error,TEXT("Spine hold did not complete: hero=%s input=%d progress=%.3f"),
        *W.Player()->GetActorLocation().ToString(),int32(W.Mode()->InputState()),W.Mode()->Campaign()->HeldWorkProgress());
    return Released&&Complete;
}
}
#endif
