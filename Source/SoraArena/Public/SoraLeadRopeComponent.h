#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SoraLeadRopeComponent.generated.h"
class USceneComponent;
class UStaticMeshComponent;

// A WIP visible connection, separate from the horse's gameplay tick. Its
// endpoints are named tack/halter components and follow their animation.
UCLASS()
class SORAARENA_API USoraLeadRopeComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    USoraLeadRopeComponent();
    void AttachLead(USceneComponent* Halter,USceneComponent* Tie,float NominalLengthCm);
    void ClearLead();
    virtual void TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* ThisTickFunction) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    bool Anchors(FVector& Halter,FVector& Tie) const;
    bool RenderedEndpoints(FVector& Halter,FVector& Tie) const;
    int32 VisibleSegments() const;
    bool HasCollision() const;
private:
    TWeakObjectPtr<USceneComponent> HalterAnchor,TieAnchor;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Segments;
    float LengthCm=0;
    void UpdateLead();
};
