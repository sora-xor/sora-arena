#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "InputCoreTypes.h"
#include "SoraCharacter.generated.h"
class UCameraComponent;
class UStaticMeshComponent;
struct FSoraPracticeInput;
struct FSoraPracticePlayer;
struct FSoraPracticeMap;
UCLASS()
class SORAARENA_API ASoraCharacter : public ACharacter
{
    GENERATED_BODY()
public:
    ASoraCharacter();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* InstigatorController, AActor* Causer) override;
    void ApplyClass(int32 Id);
    void MakeEnemy(int32 Id);
    void SetKernelDriven(bool Enabled, const FSoraPracticeMap* Map = nullptr);
    void ApplyKernelPlayer(const FSoraPracticePlayer& State);
    FSoraPracticeInput ConsumeKernelInput();
    bool IsEnemy() const { return bEnemy; }
    bool IsAlive() const { return Health > 0; }
    float Health = 120.f;
    float MaxHealth = 120.f;
    int32 ClassId = 0;
    int32 WeaponId = 1;
    int32 Ammo = 0;
    bool bReloading = false;
    float HitMarkerTime = 0.f;
    float DamageFlash = 0.f;
    UCameraComponent* GetCamera() const { return Camera; }
    void Heal(float Amount);
    static void Beam(UWorld* World, FVector A, FVector B, FLinearColor Color, float Radius = 1.5f, float Life = .08f);
    // Session-scoped controls for a future options screen. Wallet actions are deliberately excluded.
    UFUNCTION(BlueprintCallable, Category="SORA|Controls") bool RemapCombatAction(FName ActionName, FKey NewKey);
    UFUNCTION(BlueprintPure, Category="SORA|Controls") TArray<FKey> GetActionKeys(FName ActionName) const;
    UFUNCTION(BlueprintCallable, Category="SORA|Controls") void SetGamepadDeadZones(float MoveDeadZone, float LookDeadZone);
    UFUNCTION(BlueprintCallable, Category="SORA|Controls") void SetGamepadLookSensitivity(float Sensitivity);
    UFUNCTION(BlueprintPure, Category="SORA|Controls") float GetGamepadLookSensitivity() const { return GamepadLookSensitivity; }
private:
    UPROPERTY() TObjectPtr<UCameraComponent> Camera;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> BodyParts;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> WeaponParts;
    UPROPERTY() TObjectPtr<USceneComponent> WeaponRoot;
    UPROPERTY() TObjectPtr<class UAnimationAsset> IdleAnimation;
    UPROPERTY() TObjectPtr<class UAnimationAsset> WalkAnimation;
    bool bSkeletalVisual = false;
    bool bWalkingVisual = false;
    bool bEnemy = false;
    bool bKernelDriven = false;
    FVector KernelPreviousFeet = FVector::ZeroVector;
    float InputForward = 0.f, InputRight = 0.f;
    float GamepadMoveDeadZone = .18f, GamepadLookDeadZone = .12f;
    float GamepadLookSensitivity = 1.f;
    uint32 KernelHeldButtons = 0, KernelQueuedButtons = 0;
    bool bFireHeld = false;
    bool bSprint = false;
    float NextShot = 0.f;
    float ReloadEnd = 0.f;
    float NextEnemyShot = 0.f;
    float LifeTime = 0.f;
    int32 EnemyIndex = 0;
    void BuildCat();
    void BuildWeapon();
    void BotTick(float Dt);
    bool CanPlay() const;
    void Forward(float Value); void Strafe(float Value); void Yaw(float Value); void Pitch(float Value);
    void GamepadYaw(float Value); void GamepadPitch(float Value);
    void FireDown(); void FireUp(); void Fire(); void Melee(); void Reload(); void Interact();
    void SprintDown(); void SprintUp(); void JumpDown(); void JumpUp();
    void Menu(); void Enter(); void NextMap(); void NewCampaign(); void ReturnCampaign();
    void Practice(); void BlockDown(); void BlockUp(); void Ability(); void MeleeUp();
    void Subtitles();
    void PairWallet(); void OpenWallet(); void DisconnectWallet();
    TArray<int32> AmmoByWeapon;
    void WeaponOne(); void WeaponTwo(); void WeaponThree(); void Equip(int32 Slot);
    void ClassOne(); void ClassTwo(); void ClassThree(); void ClassFour(); void ClassFive(); void ClassSix();
    void ClassPrevious(); void ClassNext();
    void ChooseClass(int32 Id);
};
