#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraProjectile.generated.h"
class USphereComponent;
UCLASS()
class SORAARENA_API ASoraProjectile : public AActor
{
    GENERATED_BODY()
public:
    ASoraProjectile();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    FVector Velocity = FVector::ZeroVector;
    float Damage = 55.f;
    float Radius = 320.f;
private:
    UPROPERTY() TObjectPtr<USphereComponent> Collision;
    float Age = 0.f;
    void Detonate();
};
