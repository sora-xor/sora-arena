#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SoraEquipmentComponent.generated.h"
class ASoraPlayerCharacter;

// Nyaakoto's weapons in the offline campaign and training arena: ammunition
// per weapon, reloads, cooldowns, gunfire and shells, the yumi draw, committed
// strikes with every melee arm (the dojo bokken's swing is swept), and the
// blade guard. The held weapon's ID lives on the character so its visual and
// the HUD can read it. Kernel practice does not use this component; its
// counters come from kernel snapshots.
UCLASS(ClassGroup=(Sora))
class SORAARENA_API USoraEquipmentComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    USoraEquipmentComponent();
    // Full magazines for the class's held weapon and every other weapon; every
    // action and the guard reserve reset.
    void ResetForClass();
    // Holds WeaponId with a full magazine.
    void Hold(int32 WeaponId);
    // Drops the guard, a yumi draw, a committed strike and its recovery.
    void DropStance();
    // The round is held: drop held and drawn actions.
    void Halt();
    // Presses from the player's input handlers.
    void TriggerDown();
    void TriggerUp();
    void Melee();
    void Reload();
    void GuardDown(bool bDojo, bool bCampaignHero);
    void GuardUp() { bGuardHeld = false; }
    void ReleaseTrigger() { bFireHeld = false; }
    bool EquipClassSlot(int32 Slot);
    bool EquipCampaignWeapon(int32 WeaponId);
    // Guard reserve drains while held and recovers otherwise (not in the dojo).
    void TickGuard(float DeltaSeconds);
    // Strike resolution, recovery, reload completion and held fire.
    void TickWeapon();
    // Walking speed scale for committed, recovering, drawing, guarding or sprinting.
    float MoveScale(bool bSprinting) const;
    bool IsBowDrawing() const { return bBowDrawing; }
    float BowDrawProgress() const;
    bool IsCommittedStrike() const { return bCommittedStrike; }
    float StrikeWindupProgress() const;
    bool IsTriggerHeld() const { return bFireHeld; }
    bool IsGuardHeld() const { return bGuardHeld; }
    float GuardPressedAt() const { return GuardPressedTime; }
    float GuardReserve() const { return GuardStamina; }
    // The stamina a guard or parry costs (SoraCombatRules::Defend).
    void SpendGuard(float Amount) { GuardStamina = FMath::Max(0.f, GuardStamina - Amount); }
    // A broken guard or a heavy blow: the guard, a draw and a committed strike
    // drop, and nothing can be raised, drawn or swung for Seconds.
    void Stagger(float Seconds);
    bool IsStaggered() const;
    int32 Ammo = 0;
    bool bReloading = false;
    TArray<int32> AmmoByWeapon;
private:
    ASoraPlayerCharacter* Hero() const;
    void Fire();
    void ReleaseBow();
    void ResolveCommittedStrike();
    bool bFireHeld = false;
    bool bBowDrawing = false;
    float BowDrawStartedAt = 0.f;
    bool bCommittedStrike = false;
    bool bHistoricalRecovery = false;
    int32 CommittedWeaponId = INDEX_NONE;
    float CommittedStrikeAt = 0.f;
    FVector CommittedDirection = FVector::ForwardVector;
    float NextShot = 0.f;
    float ReloadEnd = 0.f;
    bool bGuardHeld = false;
    float GuardStamina = 100.f;
    float GuardPressedTime = 0.f;
    float StaggeredUntil = -1.f;
};
