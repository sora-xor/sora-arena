#pragma once
#include "CoreMinimal.h"
#include "Components/SceneComponent.h"
#include "SoraViewmodelPresentation.h"
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
    // State/rest smoothing is visual only; the current gameplay ray is never delayed.
    void Sway(float DeltaSeconds,float LifeTime,float Moving,bool bReloading,bool bStrike,
        bool bSprint,bool bBowDrawing,const FMinimalViewInfo& View,const FVector& GameplayRay);
    // A kernel snapshot's charge lift, or the reload tilt.
    void KernelPose(float Windup, bool bReloading);
    bool UsesAuthoredPresentation() const { return bAuthoredPresentation; }
    bool UsesFallbackBowPresentation() const { return bFallbackBowPresentation; }
    bool HasPresentationPose() const { return bPresentationReady; }
    const FString& PresentationPose() const { return ActivePose; }
    // Full imported socket rotation/scale is retained for future authored paws.
    bool PresentationSocketWorld(FName Socket,FTransform& Transform) const;
private:
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Parts;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> PrimaryMesh;
    bool bFirstPersonMode=false,bPresentationReady=false,bAuthoredPresentation=false,bFallbackBowPresentation=false;
    int32 PresentationWeapon=INDEX_NONE;
    FString ActivePose;
    FVector SmoothedAnchor=FVector::ZeroVector;
    FQuat SmoothedRest=FQuat::Identity;
    float SmoothedPitch=0,SmoothedRoll=0,SmoothedLift=0;
    void BeginPresentation(bool bFallbackBow);
    void Present(float DeltaSeconds,float LifeTime,float Moving,float Pitch,float Roll,float Lift,
        bool bDrawn,const FMinimalViewInfo* View,const FVector& GameplayRay);
};
