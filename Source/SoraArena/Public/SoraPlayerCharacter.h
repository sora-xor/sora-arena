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

// Why RemapControl did or did not rebind a key.
enum class ESoraRemapResult : uint8
{
    Done,
    // Remaps happen only while a menu holds the game.
    NotInMenu,
    NoControl,
    // A pad button for a keyboard slot, or the reverse; movement takes keys only.
    WrongDevice,
    // Not a button: a stick direction, an analog axis, or a key Unreal cannot bind.
    Unbindable,
    // Another control can use the key in the same game state.
    Taken,
    // A pad button another rebindable control held: the two traded buttons
    // (every pad button has a default job, so a pad rebind swaps).
    Swapped,
};

// Nyaakoto, the possessed first-person hero. Owns input (gated by
// SoraInputStates.h), movement (standing or crouch-walking), dojo training,
// the campaign loadout and local control preferences. In a stealth zone
// (USoraStealth) Melee behind an unsuspecting guard is a rear takedown and
// Interact held at a body drags it. The beat's fieldcraft (USoraFieldcraft)
// takes Ability (a signal to the escorted, a thrown stone), Interact held at
// its points (a lamp, the downed, a collar, a cell door), Crouch in the water
// (a dive), Jump at a wall or low cover (a climb or a vault) and Guard with
// the candle lit (cupping it). In the campaign the six weapon keys take up a
// group of arms, and the arms wheel (SoraArmsRules.h) steps through, or shows
// in a ring, every arm he can hold. Weapons live in USoraEquipmentComponent
// and the held weapon's model in USoraViewmodelComponent. In deterministic
// practice the same pawn packs its input for the Rust kernel instead of
// acting locally.
UCLASS()
class SORAARENA_API ASoraPlayerCharacter : public ASoraCharacterBase
{
    GENERATED_BODY()
public:
    ASoraPlayerCharacter(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    virtual void SetKernelDriven(bool Enabled, const FSoraPracticeMap* Map = nullptr) override;
    virtual bool AdmitDamage(float& Damage, FSoraHit& Hit, AActor* Causer) override;
    virtual void OnDefeated(AActor* Causer) override;
    void ProtectAfterSummitFall();
    virtual bool IsSparring() const override { return bDojoTraining; }
    // Crouching keeps the feet on the floor and lowers the eye smoothly.
    virtual void OnStartCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust) override;
    virtual void OnEndCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust) override;
    // Chapter one: the bokken, the four forms and nonlethal bouts.
    void SetDojoTraining(bool Enabled);
    // Later chapters: Nyaakoto's katana, yumi, quiver and saya.
    void SetCampaignHeroLoadout(bool Enabled);
    void SetCampaignGearVisible(bool Visible);
    // Drop held controls and motion at either edge of a dialogue hold.
    void ResetDialogueInput();
    void SuspendDojoAction();
    FSoraPracticeInput ConsumeKernelInput();
    bool IsDojoTraining() const { return bDojoTraining; }
    bool IsCampaignHero() const { return bCampaignHero; }
    bool IsSprinting() const { return bSprint; }
    // Scoreboard is held: practice shows every seat's kills and deaths.
    bool IsScoreboardHeld() const { return bScoreboardHeld; }
    void StopSprint() { bSprint = false; }
    // A bokken swing; during the recovery lesson it starts the recovery timer.
    void NoteDojoSwing(float StartedAt, float RecoveredAt, float CooldownSeconds);
    UCameraComponent* GetCamera() const { return Camera; }
    USoraEquipmentComponent* GetEquipment() const { return Equipment; }
    // Local controls, saved to the game mode's control slot. Only the
    // SoraInput::Remappable controls can be rebound, and only while a menu is
    // open: each has one keyboard-or-mouse key and one pad button (movement
    // halves a keyboard key only). A key that another control can use in the
    // same game state is refused, except that a pad button held by another
    // rebindable control trades places with this control's own. Wallet, menu
    // and campaign commands are never rebindable.
    UFUNCTION(BlueprintCallable, Category="SORA|Controls") bool RemapCombatAction(FName ActionName, FKey NewKey);
    // Rebinds Remappable[Index] in NewKey's slot. On Taken, TakenBy and
    // TakenAxis name the control that holds the key; on Swapped, the control
    // that took this one's old pad button.
    ESoraRemapResult RemapControl(int32 Index, const FKey& NewKey, FName* TakenBy = nullptr, int32* TakenAxis = nullptr);
    // Remappable[Index]'s key in one slot, or EKeys::Invalid.
    FKey ControlKey(int32 Index, bool bPad) const;
    // Every rebound key returns to Config/DefaultInput.ini; sensitivity,
    // dead zones and inversion stay.
    void ResetControls();
    UFUNCTION(BlueprintPure, Category="SORA|Controls") TArray<FKey> GetActionKeys(FName ActionName) const;
    UFUNCTION(BlueprintCallable, Category="SORA|Controls") void SetGamepadDeadZones(float MoveDeadZone, float LookDeadZone);
    float GetMoveDeadZone() const { return GamepadMoveDeadZone; }
    float GetLookDeadZone() const { return GamepadLookDeadZone; }
    UFUNCTION(BlueprintCallable, Category="SORA|Controls") void SetGamepadLookSensitivity(float Sensitivity);
    UFUNCTION(BlueprintPure, Category="SORA|Controls") float GetGamepadLookSensitivity() const { return GamepadLookSensitivity; }
    void SetMouseSensitivity(float Sensitivity);
    float GetMouseSensitivity() const { return MouseSensitivity; }
    UFUNCTION(BlueprintCallable, Category="SORA|Controls") void SetInvertedLook(bool Enabled);
    UFUNCTION(BlueprintPure, Category="SORA|Controls") bool GetInvertedLook() const { return bInvertedLook; }
    // Held guard for the dojo and campaign blades, or the kernel's block bit.
    bool IsGuarding() const;
    // Whether one of Action's keys is held down now (a hold the fieldcraft counts).
    bool IsActionHeld(FName ActionName) const;
    // The campaign hero's arms (SoraArmsRules.h). The arms he can take up
    // now, as a mask of catalog IDs: unlocked, or handed over by the beat in
    // play, and allowed in the saddle or under a load; every arm in the
    // training arena. Empty for another class, in the dojo and in practice.
    unsigned HoldableArms() const;
    // A group key: the group's arm last held, or its next; false (with a
    // notice when the group has none) when nothing changed hands.
    bool SelectArmsGroup(int32 Group);
    // The next (Step +1) or previous (-1) arm he can hold, in ring order.
    bool StepArms(int32 Step);
    // The arms wheel, open while its key is held past a tap: the ring of arms
    // he can hold, the one under the cursor (an index into Arms), and the
    // cursor, a unit-radius offset from the wheel's centre.
    struct FArmsWheel
    {
        bool bOpen = false;
        TArray<int32> Arms;
        int32 Choice = INDEX_NONE;
        FVector2D Cursor = FVector2D::ZeroVector;
    };
    const FArmsWheel& ArmsWheel() const { return Wheel; }
    // World time an arm was last taken up by a key, the wheel or a step.
    float ArmsTakenAt() const { return ArmsTakenTime; }
    // A vault over low cover is carrying the hero (SoraFieldcraftRules).
    bool IsVaulting() const { return bVaulting; }
protected:
    virtual void TickPlay(float DeltaSeconds) override;
    virtual void HaltActions() override;
    virtual void ResetLoadout() override;
    virtual void OnKernelSnapshot(const FSoraPracticePlayer& State) override;
    virtual bool IsFirstPersonHero() const override { return true; }
    virtual bool WieldsDojoBokken() const override { return bDojoTraining&&WeaponId==0; }
    virtual void OnBodyRebuilt() override;
private:
    float SummitFallProtectedUntil=0.f;
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
    float GamepadLookSensitivity = 1.f, MouseSensitivity = 1.f;
    bool bInvertedLook = false;
    bool bRestoringControlProfile = false;
    uint32 KernelHeldButtons = 0, KernelQueuedButtons = 0;
    bool bSprint = false;
    bool bScoreboardHeld = false;
    // The arms wheel's key: when it went down, and the wheel it opened.
    bool bArmsKeyHeld = false;
    float ArmsKeyDownAt = 0.f;
    FArmsWheel Wheel;
    FVector2D WheelPad = FVector2D::ZeroVector;
    float ArmsTakenTime = -1000.f;
    // Each group's arm last taken up, or INDEX_NONE.
    int32 GroupMemory[6] = {INDEX_NONE, INDEX_NONE, INDEX_NONE, INDEX_NONE, INDEX_NONE, INDEX_NONE};
    // A vault in progress: from, over and to, and when it began.
    bool bVaulting = false;
    float VaultStartedAt = 0.f;
    FVector VaultFrom = FVector::ZeroVector, VaultOver = FVector::ZeroVector, VaultTo = FVector::ZeroVector;
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
    void FireDown(); void FireUp(); void Melee(); void Reload(); void Interact(); void InteractUp();
    // A toggle between standing and crouch-walking (SoraStealthRules).
    void CrouchPressed();
    // 納刀 and 抜刀 on one key: the blade goes into its scabbard, or out again.
    void SheathePressed();
    void SprintDown(); void SprintUp(); void JumpDown(); void JumpUp();
    void Menu(); void Enter();
    void BlockDown(); void BlockUp(); void Ability(); void MeleeUp();
    // Released keys; with the toggle settings on, the next press ends guard
    // or sprint instead. SprintUp and BlockUp always end them.
    void SprintReleased(); void BlockReleased();
    bool TogglesGuard() const; bool TogglesSprint() const;
    void Subtitles(); void ScoreboardDown(); void ScoreboardUp();
    void WeaponOne(); void WeaponTwo(); void WeaponThree(); void WeaponFour(); void WeaponFive(); void WeaponSix();
    // A weapon key: its group of Nyaakoto's arms (in the campaign and in the
    // training arena with his loadout), else its class slot (INDEX_NONE: none).
    void WeaponKey(int32 Group, int32 Slot);
    bool TakeUpArm(int32 WeaponId);
    // Unlocked (or handed over) arms; bNow keeps only those he can hold now.
    unsigned ArmsMask(bool bNow) const;
    void ArmsWheelDown(); void ArmsWheelUp(); void ArmsNext(); void ArmsPrevious();
    void OpenArmsWheel();
    // Closes the wheel, taking up the arm under its cursor when bTake.
    void CloseArmsWheel(bool bTake);
    void TickArmsWheel();
    // Jump at low cover: a vault over it (true: the press is spent).
    bool TryVault();
    void TickVault();
    ESoraRemapResult ApplyControlMapping(int32 Index, const FKey& NewKey, bool bRequireMenu, FName* TakenBy, int32* TakenAxis);
    void LoadControlProfile();
    void RestoreBindings();
    void SaveControlProfile();
};
