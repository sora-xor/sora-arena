#include "SoraCampaignDirector.h"
#include "Game/SoraCampaignReach.h"
#include "SoraCatalog.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameMode.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

void USoraCampaignDirector::ResetCarryWork()
{
    bPryingCarryGate=false; bCarryGateHit=false;
    for(FVector& Position:LooseLoadAt) Position=FVector::ZeroVector;
}
FVector USoraCampaignDirector::LooseLoadLocation(int32 Slot) const
{
    return Slot>=0&&Slot<SoraBeatRules::MaxPoints&&(TaskState.LooseLoads&(1u<<Slot))!=0u?LooseLoadAt[Slot]:FVector::ZeroVector;
}
bool USoraCampaignDirector::InteractCarryGate(ASoraPlayerCharacter& Hero)
{
    const auto* Space=ActiveSpace();
    if(!Space||!NeedsCarryGate()||!Near(ASoraWorldBuilder::Floor(Space->CarryGate),SoraCampaignReach::Interact)) return false;
    if(bPryingCarryGate) return true;
    auto* Kit=Hero.GetEquipment();
    if(!Kit->EquipCampaignWeapon(19)) return true;
    Kit->Halt(); Kit->DropStance();
    bPryingCarryGate=true; bCarryGateHit=false;
    Fire(TEXT("interact_start:")+ActiveBeatData()->CarryGatePoint);
    UpdateObjective();
    return true;
}
void USoraCampaignDirector::TickCarryWork(int32 DeltaMs)
{
    if(!bPryingCarryGate) return;
    auto* Hero=Mode().Hero();
    const auto* Space=ActiveSpace();
    if(!Hero||!Space) { bPryingCarryGate=false; return; }
    const bool At=Near(ASoraWorldBuilder::Floor(Space->CarryGate),SoraCampaignReach::Interact);
    const bool Held=Hero->IsActionHeld(TEXT("Interact"));
    // The damage event contests its next work step; combat stagger also
    // pauses work for its existing duration. No new damage cooldown is added.
    const bool Hit=bCarryGateHit||Hero->GetEquipment()->IsStaggered();
    if(DeltaMs>0) bCarryGateHit=false;
    if(SoraBeatRules::PryCarryGate(TaskState,Task,DeltaMs,At,Held,Hit))
    {
        bPryingCarryGate=false;
        Fire(TEXT("interact_complete:")+ActiveBeatData()->CarryGatePoint);
        Notify(TEXT("蔵の封印が外れた。種籾を運び出そう。"),TEXT("The granary seal is open. Carry out the seed rice."),4.f);
        UpdateObjective();
    }
    else if(!At||!Held) bPryingCarryGate=false;
}
bool USoraCampaignDirector::SetDownLoad(ASoraPlayerCharacter& Hero)
{
    auto* Movement=Hero.GetCharacterMovement();
    // Rest the load on the same real floor supporting the player. It adds
    // no collision and cannot be left suspended over the recovery shaft.
    if(IsMounted()||!Movement->IsMovingOnGround()||!Movement->CurrentFloor.IsWalkableFloor()) return false;
    FVector At=Hero.GetActorLocation();
    At.Z=Movement->CurrentFloor.HitResult.ImpactPoint.Z;
    const int32 Slot=SoraBeatRules::SetDownCarried(TaskState,Task);
    if(Slot==INDEX_NONE) return false;
    LooseLoadAt[Slot]=At;
    CarryChanged();
    Fire(TEXT("item_set_down"));
    return true;
}
bool USoraCampaignDirector::TakeLooseLoad(ASoraPlayerCharacter& Hero)
{
    int32 Nearest=INDEX_NONE;
    float Distance=SoraCampaignReach::Interact;
    const float Feet=Hero.GetActorLocation().Z-Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    for(int32 Slot=0;Slot<SoraBeatRules::MaxPoints;++Slot)
        if((TaskState.LooseLoads&(1u<<Slot))!=0u&&FMath::Abs(Feet-LooseLoadAt[Slot].Z)<60.f)
        {
            const float To=FVector::Dist2D(Hero.GetActorLocation(),LooseLoadAt[Slot]);
            if(To<Distance) { Distance=To; Nearest=Slot; }
        }
    if(!SoraBeatRules::PickupLoose(TaskState,Task,Nearest)) return false;
    CarryChanged();
    Fire(TEXT("item_picked:")+ActiveBeatData()->CarryItem);
    return true;
}
