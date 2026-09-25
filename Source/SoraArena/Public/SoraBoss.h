#pragma once
#include "CoreMinimal.h"
#include "SoraEnemy.h"
#include "SoraGameEvents.h"
#include "SoraBoss.generated.h"

// The final chapter's alien collector. It reuses the banker cat prototype and
// stays entirely local; it never enters the multiplayer combat kernel. Two
// telegraphed attacks alternate: a long debt beam and a close cleave.
UCLASS()
class SORAARENA_API ASoraBoss : public ASoraEnemy
{
    GENERATED_BODY()
public:
    void InitCollector(int32 Slot);
    virtual void OnDefeated(AActor* Causer) override;
    bool IsBossTelegraphing() const { return bBossWindup && IsAlive(); }
    bool IsBossBeamWindup() const { return bBossBeam; }
    float BossWarningSeconds() const { return BossPhaseTimer; }
    float BossWarningProgress() const { return BossWindupDuration > 0.f ? FMath::Clamp(1.f-BossPhaseTimer/BossWindupDuration,0.f,1.f) : 0.f; }
    // Advances a windup or recovery; true while an attack is in progress.
    bool UpdateAttack(float DeltaSeconds, ASoraCharacterBase& Target);
    // Locks the next attack toward Delta: a beam from range or on even
    // attacks, otherwise a cleave.
    void BeginAttack(float Distance, const FVector& Delta);
private:
    void Telegraph();
    void Strike(ASoraCharacterBase& Target);
    void AnnouncePhase(ESoraBossPhase Phase);
    bool bBossWindup = false;
    bool bBossRecovery = false;
    bool bBossBeam = true;
    int32 BossAttackNumber = 0;
    float BossPhaseTimer = 0.f;
    float BossWindupDuration = 0.f;
    float BossVisualTimer = 0.f;
    FVector BossLockedDirection = FVector::ForwardVector;
};
