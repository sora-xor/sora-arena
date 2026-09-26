#pragma once
#include "CoreMinimal.h"
#include "SoraCharacterBase.h"
#include "SoraPracticePawn.generated.h"
class USceneComponent;
class UStaticMeshComponent;

// A deterministic-practice participant other than the local player, or a
// Shinobi decoy standing as its owner. It has no controller and no Unreal
// combat: USoraPracticeDirector applies the Rust kernel's snapshot for its
// slot every tick and places it between states every frame, and it is hidden
// while that slot is down. Its side reads at a glance: Sora League cats and
// Stellar Credit House invaders, each with a sashimono carrying the League's
// SORA mon or the Credit House's ledger sigil.
// The local player stays ASoraPlayerCharacter, kernel-driven for the session.
UCLASS()
class SORAARENA_API ASoraPracticePawn : public ASoraCharacterBase
{
    GENERATED_BODY()
public:
    ASoraPracticePawn(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    // Slot's body and banner. bSora carries the SORA mon (the player's
    // side); bAlienBody gives the body of a Credit House invader.
    // Both leave the pawn kernel-driven at the map's body size.
    void InitParticipant(int32 Slot, const FSoraPracticeMap& Map, FLinearColor Color, bool bSora, bool bAlienBody);
    // A decoy: Owner's body, class and weapon, still, at Owner.Feet.
    void InitDecoy(const FSoraPracticePlayer& Owner, const FSoraPracticeMap& Map, FLinearColor Color, bool bSora, bool bAlienBody);
    int32 ParticipantSlot() const { return Slot; }
    bool IsDecoy() const { return bDecoy; }
    // A Teppo mark floats above a marked player's head.
    bool IsShowingMark() const;
    // Every component of the sashimono, scene roots included.
    const TArray<TObjectPtr<USceneComponent>>& Banner() const { return BannerParts; }
    virtual bool IsEnemy() const override { return true; }
protected:
    virtual bool UsesAlienBody() const override { return bAlien; }
    virtual void OnKernelSnapshot(const FSoraPracticePlayer& State) override;
private:
    void BuildBanner(FLinearColor Color, bool bSora);
    int32 Slot = 0;
    bool bAlien = true;
    bool bDecoy = false;
    UPROPERTY() TArray<TObjectPtr<USceneComponent>> BannerParts;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> MarkParts;
};
