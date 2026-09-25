#pragma once
#include "CoreMinimal.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Tests/AutomationCommon.h"

class ASoraPlayerCharacter;
class ASoraGameMode;
class FAutomationTestBase;
class UInputComponent;
struct FKey;

// A disposable standalone game world started in the engine's local-game order:
// ASoraGameMode from the world settings, actor initialization and BeginPlay,
// then one player controller possessing the default ASoraPlayerCharacter. Tests use a
// unique save slot, and its control slot, so they never read or overwrite the
// player's campaign or local control preferences.
struct FSoraAutomationWorld : FTestWorldWrapper
{
    bool Start(const FString& SaveSlot);
    // Fixed steps keep kernel practice at exactly one 60 Hz step per frame.
    bool Tick(int32 Frames, float DeltaSeconds = 1.f / 60.f);
    ASoraGameMode* Mode() const;
    ASoraPlayerCharacter* Player() const;
    // UE 5.8 treats a controller without a NetDriver as local only when it has
    // a ULocalPlayer, which needs a viewport this world lacks. Bind the pawn's
    // own input handlers exactly as APawn::PawnClientRestart does for a local player.
    UInputComponent* BindPlayerInput() const;
    // Gives the controller a UPlayerInput so keys resolve through the project's
    // DefaultInput.ini mappings and the engine's paused-input rules, as the
    // viewport does for a local player, and marks it local so the hero's
    // CharacterMovement runs its own moves (jumping included).
    bool EnableKeyInput() const;
    // Presses and releases one key, each followed by a world frame.
    bool PressKey(const FKey& Key);
    // Sends one key event through UPlayerInput without advancing the world, so
    // a scripted frame can hold or release several keys before it ticks. The
    // controller's own tick then evaluates held keys each frame.
    bool InjectKey(const FKey& Key, EInputEvent Event) const;

    // A checkout that has not run scripts/toolchain/import-mac.sh has no
    // /Game/Generated art; the world builder then logs its documented
    // primitive-fallback errors. The terrain and LOD tests and the editor asset
    // validator fail on missing imports, so gameplay tests ignore only these
    // exact messages.
    static void IgnoreMissingGeneratedArt(FAutomationTestBase& Test);
    // BeginPlay reads a slot that does not exist yet, and binding the hero's
    // input reads its control slot; the engine warns once per read.
    static void IgnoreAbsentSaveSlot(FAutomationTestBase& Test, const FString& SaveSlot);
    static FString UniqueSaveSlot(const TCHAR* Purpose);
    // The control-preference slot Start gives the world with SaveSlot.
    static FString ControlSlot(const FString& SaveSlot);
    // Deletes the save slot and its control slot.
    static void DeleteSaveSlot(const FString& SaveSlot);
};
#endif
