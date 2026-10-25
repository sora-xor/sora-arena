#pragma once
#include "CoreMinimal.h"
#include "Camera/CameraTypes.h"
class UCameraComponent;

// Presentation data only. Weapon simulation and world/NPC poses do not read it.
namespace SoraViewmodelPresentation
{
constexpr int32 BokkenId=21;
struct FPose
{
    FString Name;
    FName Anchor;
    FVector Location=FVector::ZeroVector;
    FQuat Rotation=FQuat::Identity;
    float ReloadPitch=-30.f;
};
struct FWeapon
{
    int32 Id=INDEX_NONE;
    FString Key,Name,Mesh,Pose;
    bool bApproximateSockets=false;
};
// Existing cube proxy only: its real grip/paw volumes differ from authored art.
FPose FallbackBowPose(bool bDrawn);
struct FPartBounds
{
    FString Name;
    TArray<FVector> WorldCorners;
    bool bArrow=false;
};
struct FContract
{
    TMap<FString,FPose> Poses;
    TMap<int32,FWeapon> Weapons;
    float MeshScale=.75f,BlendPerSecond=12.f;
    float BobY=.7f,BobZ=.6f,BobYRate=8.f,BobZRate=16.f;
    float ReloadPitch=-30.f,StrikePitch=25.f,SprintRoll=-15.f,WindupLift=8.f,WindupPitch=28.f;
};
// Strict parsing is separately callable by automation with malformed tables.
bool Parse(const FString& Text,FContract& Out,FString& Error);
const FContract* Get();
// Projection-only snapshot. GetCameraView would update the pawn's aim rotation.
FMinimalViewInfo CameraView(const UCameraComponent& Camera);
// Invert the actual camera's native first-person projection for a world ray.
// No fixed FOV pair and no smoothing of the supplied gameplay direction.
FVector CorrectedWorldDirection(const FMinimalViewInfo& View,const FVector& GameplayDirection);
FQuat Compose(const FQuat& Aim,const FQuat& Action,const FQuat& Rest);
float BlendAlpha(float DeltaSeconds,float PerSecond);
}
