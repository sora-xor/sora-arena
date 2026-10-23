#pragma once
#include "SoraCharacterBase.h"
#include "SoraFoundryFurnace.generated.h"
// Actual blast/trace target for ch05.b07. Its health mirrors the defended
// target; unlike the old kit box it participates in ordinary combat damage.
UCLASS()
class SORAARENA_API ASoraFoundryFurnace : public ASoraCharacterBase
{
    GENERATED_BODY()
public:
    ASoraFoundryFurnace();
    virtual void BeginPlay() override;
    virtual bool AdmitDamage(float& Damage,FSoraHit& Hit,AActor* Causer) override;
    UStaticMeshComponent* Shell() const { return FurnaceMesh; }
private:
    UPROPERTY() TObjectPtr<UStaticMeshComponent> FurnaceMesh;
};
