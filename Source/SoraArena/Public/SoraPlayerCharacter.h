#pragma once
#include "CoreMinimal.h"
#include "SoraCharacterBase.h"
#include "InputCoreTypes.h"
#include "SoraPlayerCharacter.generated.h"
class UCameraComponent;
class UInputComponent;
class USoraControlSaveGame;
class USoraEquipmentComponent;
struct FSoraPracticeInput;

// Nyaakoto, the possessed first-person hero. Owns input (gated by
// SoraInputStates.h), movement, dojo training, the campaign loadout and local
// control preferences. Weapons live in USoraEquipmentComponent and the held
// weapon's model in USoraViewmodelComponent. In deterministic practice the
// same pawn packs its input for the Rust kernel instead of acting locally.
UCLASS()
class SORAARENA_API ASoraPlayerCharacter : public ASoraCharacterBase
{
    GENERATED_BODY()
public:
    ASoraPlayerCharacter(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    virtual void SetKernelDriven(bool Enabled, const FSoraPracticeMap* Map = nullptr) override;
    virtual bool AdmitDamage(float& Damage, AActor* Causer) override;
    virtual void OnDefeated(AActor* Causer) override;
    virtual bool IsSparring() const override { return bDojoTraining; }
    // Chapter one: the bokken, the four forms and nonlethal bouts.
    void SetDojoTraining(bool Enabled);
    // Later chapters: Nyaakoto's katana, yumi, quiver and saya.
    void SetCampaignHeroLoadout(bool Enabled);
    void SuspendDojoAction();
    FSoraPracticeInput ConsumeKernelInput();
    bool IsDojoTraining() const { return bDojoTraining; }
    bool IsCampaignHero() const { return bCampaignHero; }
    bool IsSprinting() const { return bSprint; }
    void StopSprint() { bSprint = false; }
    // A bokken swing; during the recovery lesson it starts the recovery timer.
    void NoteDojoSwing(float StartedAt, float RecoveredAt, float CooldownSeconds);
    UCameraComponent* GetCamera() const { return Camera; }
    USoraEquipmentComponent* GetEquipment() const { return Equipment; }
    // Local controls. Combat action remaps cannot target wallet or menu commands.
    UFUNCTION(BlueprintCallable, Category="SORA|Controls") bool RemapCombatAction(FName ActionName, FKey NewKey);
    UFUNCTION(BlueprintPure, Category="SORA|Controls") TArray<FKey> GetActionKeys(FName ActionName) const;
    UFUNCTION(BlueprintCallable, Category="SORA|Controls") void SetGamepadDeadZones(float MoveDeadZone, float LookDeadZone);
    UFUNCTION(BlueprintCallable, Category="SORA|Controls") void SetGamepadLookSensitivity(float Sensitivity);
    UFUNCTION(BlueprintPure, Category="SORA|Controls") float GetGamepadLookSensitivity() const { return GamepadLookSensitivity; }
    UFUNCTION(BlueprintCallable, Category="SORA|Controls") void SetInvertedLook(bool Enabled);
    UFUNCTION(BlueprintPure, Category="SORA|Controls") bool GetInvertedLook() const { return bInvertedLook; }
protected:
    virtual void TickPlay(float DeltaSeconds) override;
    virtual void HaltActions() override;
    virtual void ResetLoadout() override;
    virtual void OnKernelSnapshot(const FSoraPracticePlayer& State) override;
    virtual bool IsFirstPersonHero() const override { return true; }
    virtual bool WieldsDojoBokken() const override { return bDojoTraining; }
    virtual void OnBodyRebuilt() override;
private:
    UPROPERTY() TObjectPtr<UCameraComponent> Camera;
    UPROPERTY() TObjectPtr<USoraEquipmentComponent> Equipment;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> QuiverParts;
    UPROPERTY() TObjectPtr<USoraControlSaveGame> ControlProfile;
    // The game mode's control slot when the profile was loaded; saves go back to it.
    FString ControlSlot;
    bool bDojoTraining = false;
    bool bCampaignHero = false;
    bool bDojoRecoveryPending = false;
    float DojoRecoveryStartedAt = 0.f;
    float DojoRecoveryEndsAt = 0.f;
    int32 DojoRecoveryRequiredMs = 0;
    float InputForward = 0.f, InputRight = 0.f;
    float GamepadMoveDeadZone = .18f, GamepadLookDeadZone = .12f;
    float GamepadLookSensitivity = 1.f;
    bool bInvertedLook = false;
    bool bRestoringControlProfile = false;
    uint32 KernelHeldButtons = 0, KernelQueuedButtons = 0;
    bool bSprint = false;
    uint64 InputFrame = MAX_uint64;
    uint8 InputFrameState = 0;
    bool AcceptsInput(uint8 States);
    void BindPress(UInputComponent* Input, const TCHAR* Action, void (ASoraPlayerCharacter::*Handler)());
    void BindRelease(UInputComponent* Input, const TCHAR* Action, void (ASoraPlayerCharacter::*Handler)());
    void BuildHeroQuiver();
    void BuildHeroSaya();
    void TickDojoLessons();
    void Forward(float Value); void Strafe(float Value); void Yaw(float Value); void Pitch(float Value);
    void GamepadYaw(float Value); void GamepadPitch(float Value);
    void FireDown(); void FireUp(); void Melee(); void Reload(); void Interact();
    void SprintDown(); void SprintUp(); void JumpDown(); void JumpUp();
    void Menu(); void Enter(); void NextMap(); void NewCampaign(); void ReturnCampaign();
    void Practice(); void BlockDown(); void BlockUp(); void Ability(); void MeleeUp();
    void Subtitles();
    void PairWallet(); void OpenWallet(); void DisconnectWallet();
    void WeaponOne(); void WeaponTwo(); void WeaponThree(); void Equip(int32 Slot);
    void WeaponFour(); void WeaponFive(); void WeaponSix(); void CampaignWeaponNext();
    void EquipCampaignWeapon(int32 WeaponId);
    void ClassOne(); void ClassTwo(); void ClassThree(); void ClassFour(); void ClassFive(); void ClassSix();
    void ClassPrevious(); void ClassNext();
    void ChooseClass(int32 Id);
    bool ApplyCombatActionMapping(FName ActionName, FKey NewKey, bool bRequireMenu);
    void LoadControlProfile();
    void SaveControlProfile();
};
