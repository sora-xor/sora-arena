#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SoraEquipmentComponent.generated.h"
class ASoraEnemy;
class ASoraPlayerCharacter;

// Nyaakoto's weapons in the offline campaign and training arena: ammunition
// per weapon, reloads, cooldowns, gunfire and shells, the yumi draw, committed
// strikes with every melee arm (the dojo bokken's swing is swept), the
// kusarigama's weighted chain cast at an opponent beyond the sickle's reach
// (SoraFieldcraftRules::Snare), the healing lance raising a downed companion,
// the blade guard, and the sword school's sheathed hand, 転 step, 残心 and
// 水月 read (SoraCombatRules). The held weapon's ID lives on the character so its
// visual and the HUD can read it. In the campaign, a weapon the save has not
// unlocked is refused with a notice; from the saddle a weapon acts only in its
// mounted arc (SoraMountRules.h), and a carried load slows the hero and leaves
// at most the katana in hand. Kernel practice does not use this component; its
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
    // 納刀: a held blade goes back into its scabbard over
    // SoraCombatRules::SheatheMs, or is drawn again. Sheathed, nothing is cut
    // or fired (an attack press draws instead), and a guard press is a
    // mutō-dori attempt (SoraDefense).
    void Sheathe(bool bSheathe);
    bool IsSheathing() const { return bSheathed; }
    bool IsSheathed() const;
    void ReleaseTrigger() { bFireHeld = false; }
    bool EquipClassSlot(int32 Slot);
    bool EquipCampaignWeapon(int32 WeaponId);
    // Guard reserve drains while held and recovers otherwise (not in the dojo);
    // a 残心 hold after a defeat restores it instead.
    void TickGuard(float DeltaSeconds);
    // The 転 step, strike resolution, recovery, reload completion and held fire.
    void TickWeapon();
    // 合わせ met Opponent's blow (SoraDefense): the 転 window after it opens.
    void NoteAwase(ASoraEnemy* Opponent);
    // The opponent last met with awase and how long ago, or null.
    ASoraEnemy* AwaseOpponent(int32& SinceMs) const;
    // 転 (SoraDefense::Marobashi): rounds Center by ArcDegrees from Center +
    // Radius over SoraCombatRules::MarobashiStepMs, the view turning with it.
    void BeginStep(const FVector& Center, const FVector& Radius, float ArcDegrees);
    bool IsStepping() const { return bStepping; }
    // The hero felled an opponent (SoraDamage::Resolve): a 残心 hold is due.
    void NoteDefeat();
    float LastZanshinAt() const { return ZanshinAt; }
    // 水月: a melee arm is drawn and the opponent it points at stands in its
    // maai (SoraCombatRules::InMaai).
    bool InMaai() const;
    // Walking speed scale for committed, recovering, drawing, guarding or sprinting.
    float MoveScale(bool bSprinting) const;
    bool IsBowDrawing() const { return bBowDrawing; }
    float BowDrawProgress() const;
    bool IsCommittedStrike() const { return bCommittedStrike; }
    // The committed action is the kusarigama's chain, not a cut.
    bool IsChainCast() const { return bCommittedStrike && bChainCast; }
    // Weights cast and opponents the chain caught (automation reads them).
    int32 ChainsCast() const { return ChainCasts; }
    int32 ChainsLanded() const { return ChainHits; }
    float StrikeWindupProgress() const;
    bool IsTriggerHeld() const { return bFireHeld; }
    bool IsGuardHeld() const { return bGuardHeld; }
    float GuardPressedAt() const { return GuardPressedTime; }
    float GuardReserve() const { return GuardStamina; }
    // The shared stamina a guard, parry or authored player crank costs.
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
    void TickStep();
    void ResolveCommittedStrike();
    void ResolveChain();
    // The opponent the kusarigama's weight would fly at now, or null.
    ASoraEnemy* ChainQuarry() const;
    // An event for the campaign's active beat (equip:N, fired:N, draw_complete ...).
    void RaiseBeatEvent(const FString& Event) const;
    bool bFireHeld = false;
    bool bBowDrawing = false;
    float BowDrawStartedAt = 0.f;
    bool bCommittedStrike = false;
    bool bChainCast = false;
    TWeakObjectPtr<ASoraEnemy> ChainTarget;
    int32 ChainCasts = 0;
    int32 ChainHits = 0;
    bool bDrawCompleteRaised = false;
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
    bool bSheathed = false;
    float SheathedAt = 0.f;
    TWeakObjectPtr<ASoraEnemy> Awased;
    float AwaseAt = -1000.f;
    bool bStepping = false;
    float StepStartedAt = 0.f;
    FVector StepCenter = FVector::ZeroVector;
    FVector StepRadius = FVector::ZeroVector;
    float StepArc = 0.f;
    float StepTurned = 0.f;
    bool bZanshinDue = false;
    float DefeatAt = -1000.f;
    float ZanshinAt = -1000.f;
};
