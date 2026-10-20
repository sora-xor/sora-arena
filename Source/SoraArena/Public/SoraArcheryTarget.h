#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraArcheryTarget.generated.h"
class UBoxComponent;

// Functional paper/straw target proxy. Only the director's registered arrow
// impact can score it; ordinary damage never changes lesson progress.
UCLASS()
class SORAARENA_API ASoraArcheryTarget : public AActor
{
    GENERATED_BODY()
public:
    ASoraArcheryTarget();
    void Configure(int32 Index,const FVector& Center,float Radius,float FaceDiameter);
    void MoveForClock(int32 Milliseconds);
    FVector CenterAt(int32 Milliseconds) const;
    bool ContainsImpact(const FHitResult& Hit) const;
    void SetAvailable(bool bAvailable);
    int32 TargetIndex() const { return Index; }
    float ScoringRadius() const { return Radius; }
private:
    UPROPERTY() TObjectPtr<UBoxComponent> Face;
    FVector Rest=FVector::ZeroVector;
    float Radius=21.f;
    int32 Index=0;
};
