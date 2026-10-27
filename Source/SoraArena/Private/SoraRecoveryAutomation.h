#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "World/SoraNavigation.h"
#include "GameFramework/Controller.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace SoraRecoveryAutomation
{
// Navigate the ordinary floor via real W input. Navigation chooses the
// route; it never moves the pawn or edits a task state.
inline bool WalkTo(FSoraAutomationWorld& World,const FVector& Destination)
{
    auto* Hero=World.Player();
    auto* Nav=USoraNavigation::Get(Hero);
    TArray<FVector> Path;
    if(!Nav||!Nav->Settle()||!Nav->FindPath(Hero->GetActorLocation(),Destination,*Hero,Path)||Path.IsEmpty())
    {
        UE_LOG(LogTemp,Error,TEXT("Recovery walk has no path: hero=%s destination=%s"),
            *Hero->GetActorLocation().ToString(),*Destination.ToString());
        return false;
    }
    Path.Add(Destination);
    for(const FVector& Point:Path)
    {
        for(int32 Frame=0;Frame<1200&&FVector::Dist2D(Hero->GetActorLocation(),Point)>30.f;++Frame)
        {
            const FRotator Facing=(Point-Hero->GetActorLocation()).GetSafeNormal2D().Rotation();
            Hero->GetController()->SetControlRotation(Facing); Hero->FaceRotation(Facing,0.f);
            if(!World.InjectKey(EKeys::W,IE_Pressed)||!World.Tick(1)) return false;
        }
        if(FVector::Dist2D(Hero->GetActorLocation(),Point)>40.f)
        {
            FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(RecoveryWalkBlocked),false,Hero);
            World.GetTestWorld()->LineTraceSingleByChannel(Hit,Hero->GetActorLocation(),
                FVector(Point.X,Point.Y,Hero->GetActorLocation().Z),ECC_Visibility,Query);
            UE_LOG(LogTemp,Error,TEXT("Recovery walk blocked: hero=%s waypoint=%s destination=%s movement=%d input=%d hit=%s component=%s"),
                *Hero->GetActorLocation().ToString(),*Point.ToString(),*Destination.ToString(),
                int(Hero->GetCharacterMovement()->MovementMode),int(World.Mode()->InputState()),*GetNameSafe(Hit.GetActor()),*GetNameSafe(Hit.GetComponent()));
            World.InjectKey(EKeys::W,IE_Released);return false;
        }
    }
    return World.InjectKey(EKeys::W,IE_Released)&&World.Tick(4);
}
inline bool Rope(FSoraAutomationWorld& World)
{
    auto* Campaign=World.Mode()->Campaign();
    if(!World.InjectKey(EKeys::E,IE_Pressed)||!World.Tick(1)||!Campaign->IsClimbingRecoveryWell())
    {
        UE_LOG(LogTemp,Error,TEXT("Recovery rope did not start: position=%s approach=%s bottom=%s held=%d input=%d"),
            *World.Player()->GetActorLocation().ToString(),*Campaign->RecoveryApproach().ToString(),
            *Campaign->RecoveryBottom().ToString(),World.Player()->IsActionHeld(TEXT("Interact")),static_cast<int32>(World.Mode()->InputState()));
        return false;
    }
    for(int32 Frame=0;Frame<900&&Campaign->IsClimbingRecoveryWell();++Frame)
    {
        const FVector Before=World.Player()->GetActorLocation();
        if(!World.Tick(1)) return false;
        const FVector After=World.Player()->GetActorLocation();
        if(FVector::Distance(Before,After)>3.f)
        {
            UE_LOG(LogTemp,Error,TEXT("Recovery rope exceeded swept step: before=%s after=%s delta=%.3f climbing=%d movement=%d bottom=%s"),
                *Before.ToString(),*After.ToString(),FVector::Distance(Before,After),Campaign->IsClimbingRecoveryWell(),
                static_cast<int32>(World.Player()->GetCharacterMovement()->MovementMode),*Campaign->RecoveryBottom().ToString());
            return false;
        }
    }
    if(Campaign->IsClimbingRecoveryWell())
        UE_LOG(LogTemp,Error,TEXT("Recovery rope timed out: position=%s bottom=%s approach=%s held=%d movement=%d input=%d"),
            *World.Player()->GetActorLocation().ToString(),*Campaign->RecoveryBottom().ToString(),*Campaign->RecoveryApproach().ToString(),
            World.Player()->IsActionHeld(TEXT("Interact")),static_cast<int32>(World.Player()->GetCharacterMovement()->MovementMode),
            static_cast<int32>(World.Mode()->InputState()));
    return World.InjectKey(EKeys::E,IE_Released)&&World.Tick(2)&&!Campaign->IsClimbingRecoveryWell();
}
inline bool Recover(FSoraAutomationWorld& World)
{
    auto* Campaign=World.Mode()->Campaign();
    if(!Campaign->NeedsEquipmentRecovery()) return true;
    if(!WalkTo(World,Campaign->RecoveryApproach())||!Rope(World)||
        FVector::Dist(World.Player()->GetActorLocation(),Campaign->RecoveryBottom())>20.f) return false;
    if(!World.InjectKey(EKeys::E,IE_Pressed)||!World.Tick(185)||!World.InjectKey(EKeys::E,IE_Released)||!World.Tick(2)||
        Campaign->NeedsEquipmentRecovery()) return false;
    return Rope(World)&&World.Player()->GetActorLocation().Z>0.f;
}
}
#endif
