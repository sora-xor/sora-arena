#pragma once
#include "CoreMinimal.h"
#include "SoraCharacterBase.h"
#include "SoraEnemy.generated.h"
struct FSoraPatrolRoute;

// A campaign or training-arena opponent: an alien ranged invader, a blade
// retainer on every sixth slot, or a chapter-one sparring pupil. The pawn
// owns its attacks (telegraph, windup, strike and damage); ASoraEnemyController
// decides from its own tick where it moves and which attack it runs.
UCLASS()
class SORAARENA_API ASoraEnemy : public ASoraCharacterBase
{
    GENERATED_BODY()
public:
    ASoraEnemy(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    // Slot is the spawn order; slots 0, 6, 12 and 18 are blade retainers.
    // Without a patrol the invader belongs to a combat wave and hunts the hero;
    // with one it starts unaware on that route.
    void InitInvader(int32 Slot, const FSoraPatrolRoute* Patrol = nullptr);
    // Spawns and initializes an invader, or returns null when it cannot be placed.
    static ASoraEnemy* SpawnInvader(UWorld& World, int32 Slot, const FVector& Location, const FRotator& Rotation,
        const FSoraPatrolRoute* Patrol = nullptr);
    // Nonlethal sparring with the bokken; a defeated pupil yields.
    void InitDojoPupil(int32 Slot);
    void SuspendDojoAction();
    virtual bool IsEnemy() const override { return true; }
    virtual bool IsSparring() const override { return bDojoPupil; }
    virtual bool AdmitDamage(float& Damage, AActor* Causer) override;
    virtual void OnDefeated(AActor* Causer) override;
    bool IsBladeRetainer() const { return bBladeRetainer; }
    bool IsDojoPupil() const { return bDojoPupil; }
    int32 EnemySlot() const { return EnemyIndex; }
    // Ranged invaders miss on a fixed pattern, never a dice roll: every third
    // shot, offset by slot so a group does not miss in unison.
    static bool RangedShotMisses(int32 Slot, int32 Shot) { return (Shot + Slot) % 3 == 0; }
    int32 RangedShotsFired() const { return RangedShots; }
    bool IsPupilWindup() const { return bPupilWindup; }
    bool IsDuelWindup() const { return bDuelWindup; }
    // The attacks ASoraEnemyController runs; each starts, winds up and
    // resolves on its own timing against Target at Distance (2D, cm).
    void PupilAttack(ASoraCharacterBase& Target, float Distance);
    void DuelAttack(ASoraCharacterBase& Target, float Distance);
    void RangedAttack(ASoraCharacterBase& Target, float Distance);
    // A parried blade delays this opponent's next attack.
    void DelayNextAttack(float Seconds) { NextEnemyShot += Seconds; }
protected:
    virtual void TickPlay(float DeltaSeconds) override;
    virtual void HaltActions() override { bDuelWindup = false; }
    virtual bool UsesAlienBody() const override { return !bDojoPupil; }
    virtual bool WieldsDojoBokken() const override { return bDojoPupil; }
    bool bDojoPupil = false;
    bool bBladeRetainer = false;
    bool bDuelWindup = false;
    float DuelStrikeAt = 0.f;
    FVector DuelLockedDirection = FVector::ForwardVector;
    bool bPupilWindup = false;
    float PupilWindupEndsAt = 0.f;
    FVector PupilLockedDirection = FVector::ForwardVector;
    float NextEnemyShot = 0.f;
    int32 EnemyIndex = 0;
    int32 RangedShots = 0;
};
