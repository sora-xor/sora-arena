#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraWorkshopHazardRules.h"
#include "SoraWorkshopProp.generated.h"

class ASoraCharacterBase;
class UBoxComponent;
class UPointLightComponent;
class UStaticMeshComponent;

// Campaign workshop collision and damage proxies, pending final prop/VFX art.
UCLASS()
class SORAARENA_API ASoraWorkshopProp : public AActor
{
    GENERATED_BODY()
public:
    ASoraWorkshopProp();
    // -1 is the oil stack; other indices address the authored soft cover.
    void Build(int Index);
    bool IsOil() const { return CoverIndex<0; }
    bool IsSpent() const { return IsOil()?Fire.Spent:Health<=0; }
    int FireLeftMs() const { return Fire.LeftMs; }
    int CoverHealth() const { return Health; }
    bool BlastReaches(const FVector& At,float Radius,float Damage) const;
    void Detonate(float Damage);
    void StepFire(int DtMs);
    virtual float TakeDamage(float Amount,const FDamageEvent& Event,AController* Instigator,AActor* Causer) override;
private:
    bool Playing() const;
    bool ClearLine(const FVector& From,const FVector& To) const;
    void Break();
    int CoverIndex=-1,Health=0;
    SoraWorkshopHazardRules::FFire Fire;
    TMap<TWeakObjectPtr<ASoraCharacterBase>,int> Exposure;
    UPROPERTY() TObjectPtr<UBoxComponent> Collision;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Pieces;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Flame;
    UPROPERTY() TObjectPtr<UPointLightComponent> Light;
};
