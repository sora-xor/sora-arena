#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SoraPracticeClock.h"
#include "SoraPracticeDirector.generated.h"
class ASoraCharacterBase;
class ASoraGameMode;

// Zero-stake deterministic practice on ASoraGameMode. Starts and stops the
// Rust kernel session, steps it on the shared 60 Hz clock with the hero's
// packed input, presents every participant and projectile from kernel
// snapshots, and announces each kernel event through USoraGameEvents.
UCLASS(ClassGroup=(Sora))
class SORAARENA_API USoraPracticeDirector : public UActorComponent
{
    GENERATED_BODY()
public:
    USoraPracticeDirector();
    // Starts a fresh session for the selected class, loadout slot and map.
    // On failure the menu reopens with the kernel's reason.
    bool Reset();
    // Stops the session and returns the hero to CharacterMovement.
    void Clear();
    // Advances the kernel for one rendered frame of live play.
    void Step(float DeltaSeconds);
    void ResetClock() { Clock.Reset(); }
    FString ObjectiveText() const;
    FString ObjectiveTextEnglish() const;
    // Loadout slot chosen in the menu with 1, 2 or 3.
    int32 WeaponSlot = 1;
    // A long frame slowed practice time instead of skipping input ticks.
    bool bSlowed = false;
private:
    ASoraGameMode& Mode() const;
    void UpdatePresentation();
    void PresentEvents();
    FSoraPracticeClock Clock;
    UPROPERTY() TArray<TObjectPtr<ASoraCharacterBase>> Pawns;
    UPROPERTY() TMap<uint32, TObjectPtr<AActor>> ProjectileActors;
};
