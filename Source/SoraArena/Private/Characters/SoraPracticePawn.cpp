#include "SoraPracticePawn.h"
#include "ArenaKernelSubsystem.h"
#include "GameFramework/CharacterMovementComponent.h"

ASoraPracticePawn::ASoraPracticePawn(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    AutoPossessAI=EAutoPossessAI::Disabled;
    bUseControllerRotationYaw=false;
    GetCharacterMovement()->bOrientRotationToMovement=false;
}
void ASoraPracticePawn::InitParticipant(int32 InSlot)
{
    Slot=InSlot;
    ApplyClass(InSlot%6);
    BuildCat();
}
void ASoraPracticePawn::OnKernelSnapshot(const FSoraPracticePlayer& State)
{
    SetActorHiddenInGame(!State.Alive);
}
