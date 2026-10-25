#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraFuelCanisterRules.h"
#include "SoraFuelCanister.generated.h"

class UCapsuleComponent;
class UPointLightComponent;
class UStaticMeshComponent;

// Authored b08 hazard with explicitly provisional geometry. Shot damage enters
// through the same typed TakeDamage event as a character; the resulting blast
// retains ordinary cover, defense, instigator and enemy defeat handling.
UCLASS()
class SORAARENA_API ASoraFuelCanister : public AActor
{
    GENERATED_BODY()
public:
    ASoraFuelCanister();
    void Build(FName Id);
    FName CanisterId() const { return Id; }
    bool IsBurst() const { return State.Burst; }
    FVector BlastPoint() const { return GetActorLocation(); }
    virtual float TakeDamage(float Amount,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer) override;
    virtual void Tick(float DeltaSeconds) override;
private:
    FName Id;
    SoraFuelCanisterRules::FState State;
    float FlashLeft=0;
    UPROPERTY() TObjectPtr<UCapsuleComponent> Collision;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Band;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Flash;
    UPROPERTY() TObjectPtr<UPointLightComponent> Light;
};
