#pragma once
#include "CoreMinimal.h"
#include "SoraCharacterBase.h"
#include "SoraPracticePawn.generated.h"

// A deterministic-practice participant other than the local player. It has no
// controller and no Unreal combat: every frame USoraPracticeDirector applies the
// Rust kernel's snapshot for its slot, and it is hidden while that slot is down.
// The local player stays ASoraPlayerCharacter, kernel-driven for the session.
UCLASS()
class SORAARENA_API ASoraPracticePawn : public ASoraCharacterBase
{
    GENERATED_BODY()
public:
    ASoraPracticePawn(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    void InitParticipant(int32 Slot);
    int32 ParticipantSlot() const { return Slot; }
    virtual bool IsEnemy() const override { return true; }
protected:
    virtual bool UsesAlienBody() const override { return true; }
    virtual void OnKernelSnapshot(const FSoraPracticePlayer& State) override;
private:
    int32 Slot = 0;
};
