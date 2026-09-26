#pragma once
#include "CoreMinimal.h"
#include "SoraCharacterBase.h"
#include "SoraPracticePawn.generated.h"
class UStaticMeshComponent;

// A deterministic-practice participant other than the local player, or a
// Shinobi decoy standing as its owner. It has no controller and no Unreal
// combat: USoraPracticeDirector applies the Rust kernel's snapshot for its
// slot every tick and places it between states every frame, and it is hidden
// while that slot is down. Its side reads at a glance: resistance cats and
// banker invaders, and a sashimono in the team's colour with its kamon.
// The local player stays ASoraPlayerCharacter, kernel-driven for the session.
UCLASS()
class SORAARENA_API ASoraPracticePawn : public ASoraCharacterBase
{
    GENERATED_BODY()
public:
    ASoraPracticePawn(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    // Slot's body and banner. bSora carries the SORA kamon (the player's
    // side); bAlienBody dresses the cat as a banker invader.
    // Both leave the pawn kernel-driven at the map's body size.
    void InitParticipant(int32 Slot, const FSoraPracticeMap& Map, FLinearColor Color, bool bSora, bool bAlienBody);
    // A decoy: Owner's body, class and weapon, still, at Owner.Feet.
    void InitDecoy(const FSoraPracticePlayer& Owner, const FSoraPracticeMap& Map, FLinearColor Color, bool bSora, bool bAlienBody);
    int32 ParticipantSlot() const { return Slot; }
    bool IsDecoy() const { return bDecoy; }
    // A Teppo mark floats above a marked player's head.
    bool IsShowingMark() const;
    const TArray<TObjectPtr<UStaticMeshComponent>>& Banner() const { return BannerParts; }
    virtual bool IsEnemy() const override { return true; }
protected:
    virtual bool UsesAlienBody() const override { return bAlien; }
    virtual void OnKernelSnapshot(const FSoraPracticePlayer& State) override;
private:
    void BuildBanner(FLinearColor Color, bool bSora);
    int32 Slot = 0;
    bool bAlien = true;
    bool bDecoy = false;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> BannerParts;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> MarkParts;
};
