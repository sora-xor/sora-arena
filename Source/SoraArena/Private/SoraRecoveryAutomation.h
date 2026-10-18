#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraCampaignDirector.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "World/SoraNavigation.h"
#include "GameFramework/Controller.h"

namespace SoraRecoveryAutomation
{
// Navigate the ordinary floor via real W input. Navigation chooses the
// route; it never moves the pawn or edits a task state.
inline bool WalkTo(FSoraAutomationWorld& World,const FVector& Destination)
{
    auto* Hero=World.Player();
    auto* Nav=USoraNavigation::Get(Hero);
    TArray<FVector> Path;
    if(!Nav||!Nav->Settle()||!Nav->FindPath(Hero->GetActorLocation(),Destination,*Hero,Path)||Path.IsEmpty()) return false;
    Path.Add(Destination);
    for(const FVector& Point:Path)
    {
        for(int32 Frame=0;Frame<1200&&FVector::Dist2D(Hero->GetActorLocation(),Point)>30.f;++Frame)
        {
            const FRotator Facing=(Point-Hero->GetActorLocation()).GetSafeNormal2D().Rotation();
            Hero->GetController()->SetControlRotation(Facing); Hero->FaceRotation(Facing,0.f);
            if(!World.InjectKey(EKeys::W,IE_Pressed)||!World.Tick(1)) return false;
        }
        if(FVector::Dist2D(Hero->GetActorLocation(),Point)>40.f) { World.InjectKey(EKeys::W,IE_Released); return false; }
    }
    return World.InjectKey(EKeys::W,IE_Released)&&World.Tick(4);
}
inline bool Rope(FSoraAutomationWorld& World)
{
    auto* Campaign=World.Mode()->Campaign();
    if(!World.InjectKey(EKeys::E,IE_Pressed)||!World.Tick(1)||!Campaign->IsClimbingRecoveryWell()) return false;
    for(int32 Frame=0;Frame<900&&Campaign->IsClimbingRecoveryWell();++Frame)
    {
        const FVector Before=World.Player()->GetActorLocation();
        if(!World.Tick(1)||FVector::Distance(Before,World.Player()->GetActorLocation())>3.f) return false;
    }
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
