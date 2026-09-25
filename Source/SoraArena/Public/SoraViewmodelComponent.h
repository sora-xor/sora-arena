#pragma once
#include "CoreMinimal.h"
#include "Components/SceneComponent.h"
#include "SoraViewmodelComponent.generated.h"
class UStaticMeshComponent;

// The weapon held at a character's eye. For the possessed hero it is the
// first-person viewmodel: owner-only FirstPerson primitives with UE 5.8's
// viewmodel projection. Opponents and practice participants hold the same
// meshes as ordinary world-visible geometry. Presentation only.
UCLASS(ClassGroup=(Sora))
class SORAARENA_API USoraViewmodelComponent : public USceneComponent
{
    GENERATED_BODY()
public:
    // Rest offset from the eye.
    static FVector RestLocation() { return FVector(40,18,-18); }
    void Build(int32 WeaponId, bool bDojoBokken, bool bFirstPerson);
    // The hero's walking bob and action tilt.
    void Sway(float LifeTime, float Moving, float Pitch, float Roll);
    // A kernel snapshot's charge lift, or the reload tilt.
    void KernelPose(float Windup, bool bReloading);
private:
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Parts;
};
