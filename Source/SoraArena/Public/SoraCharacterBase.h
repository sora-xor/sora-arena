#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "SoraCharacterBase.generated.h"
class UAnimationAsset;
class UStaticMeshComponent;
class USoraViewmodelComponent;
struct FSoraPracticeMap;
struct FSoraPracticePlayer;

// The body every SORA character shares: capsule and movement tuning, health,
// the cat model, the weapon held at the eye, the hooks SoraDamage::Resolve
// calls, and presentation of a deterministic-practice kernel snapshot.
UCLASS(Abstract)
class SORAARENA_API ASoraCharacterBase : public ACharacter
{
    GENERATED_BODY()
public:
    ASoraCharacterBase(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    // The weapon hangs from this eye point; ASoraPlayerCharacter makes it its camera.
    static const FName EyeComponentName;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* InstigatorController, AActor* Causer) override;
    // A class's health, speed and primary weapon.
    void ApplyClass(int32 Id);
    // Deterministic practice stops CharacterMovement; kernel snapshots place the body.
    virtual void SetKernelDriven(bool Enabled, const FSoraPracticeMap* Map = nullptr);
    void ApplyKernelPlayer(const FSoraPracticePlayer& State);
    bool IsKernelDriven() const { return bKernelDriven; }
    bool IsAlive() const { return Health > 0; }
    // Alive, and the round is in live play.
    bool CanPlay() const;
    void Heal(float Amount);
    virtual bool IsEnemy() const { return false; }
    // A dojo bout: the loser yields instead of dying.
    virtual bool IsSparring() const { return false; }
    // Called by SoraDamage::Resolve. AdmitDamage may absorb or scale a blow and
    // returns false when nothing reaches the body; OnDefeated follows health zero.
    virtual bool AdmitDamage(float& Damage, AActor* Causer) { return true; }
    virtual void OnDefeated(AActor* Causer) {}
    USceneComponent* GetEye() const { return Eye; }
    USoraViewmodelComponent* GetViewmodel() const { return Viewmodel; }
    float GetLifeTime() const { return LifeTime; }
    // Rebuilds the held weapon for WeaponId.
    void RebuildWeapon();
    float Health = 120.f;
    float MaxHealth = 120.f;
    int32 ClassId = 0;
    int32 WeaponId = 1;
    float HitMarkerTime = 0.f;
    float DamageFlash = 0.f;
protected:
    // This frame's live-play work, after the shared timers.
    virtual void TickPlay(float DeltaSeconds) {}
    // The round is held (menu, title card, result) or this character is down.
    virtual void HaltActions() {}
    // After ApplyClass sets the class stats and before the weapon is rebuilt.
    virtual void ResetLoadout() {}
    // At the end of every kernel snapshot this character presents.
    virtual void OnKernelSnapshot(const FSoraPracticePlayer& State) {}
    virtual bool UsesAlienBody() const { return false; }
    // The possessed hero hides its own body and holds a first-person weapon.
    virtual bool IsFirstPersonHero() const { return false; }
    virtual bool WieldsDojoBokken() const { return false; }
    // The body model was rebuilt and every earlier body part destroyed.
    virtual void OnBodyRebuilt() {}
    void BuildCat();
    void UpdateLocomotion(bool bMoving, float RateScale);
    UPROPERTY() TObjectPtr<USceneComponent> Eye;
    UPROPERTY() TObjectPtr<USoraViewmodelComponent> Viewmodel;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> BodyParts;
    UPROPERTY() TObjectPtr<UAnimationAsset> IdleAnimation;
    UPROPERTY() TObjectPtr<UAnimationAsset> WalkAnimation;
    bool bSkeletalVisual = false;
    bool bWalkingVisual = false;
    bool bKernelDriven = false;
    FVector KernelPreviousFeet = FVector::ZeroVector;
    float LifeTime = 0.f;
};
