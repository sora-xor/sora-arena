#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "InputCoreTypes.h"
#include "UObject/Package.h"
#include "SoraControlSaveGame.generated.h"

// One rebound control: an action, or one half of a movement axis
// (SoraInput::Remappable), and the key it now uses in that key's slot
// (keyboard or mouse, or pad).
USTRUCT()
struct FSoraControlBinding
{
    GENERATED_BODY()

    UPROPERTY(SaveGame) FName ActionName;
    // +1 or -1 for a movement axis half; 0 for an action.
    UPROPERTY(SaveGame) int32 Axis = 0;
    UPROPERTY(SaveGame) FKey Key;
};

// Local input preferences have no authority over combat or wallet transactions.
// Another schema is discarded and the defaults apply.
UCLASS()
class SORAARENA_API USoraControlSaveGame : public USaveGame
{
    GENERATED_BODY()
public:
    static constexpr int32 Schema = 2;
    // A new profile stamped with Schema. Unreal writes only the properties
    // that differ from the class default, so SaveSchema defaults to 0: a
    // stamped schema is always on disk, and a file without one reads as 0.
    static USoraControlSaveGame* New()
    {
        USoraControlSaveGame* Profile = NewObject<USoraControlSaveGame>(GetTransientPackage());
        Profile->SaveSchema = Schema;
        return Profile;
    }
    UPROPERTY(SaveGame) int32 SaveSchema = 0;
    UPROPERTY(SaveGame) float MoveDeadZone = .18f;
    UPROPERTY(SaveGame) float LookDeadZone = .12f;
    // The right stick's turn rate multiplier.
    UPROPERTY(SaveGame) float LookSensitivity = 1.f;
    UPROPERTY(SaveGame) float MouseSensitivity = 1.f;
    UPROPERTY(SaveGame) bool InvertedLook = false;
    UPROPERTY(SaveGame) TArray<FSoraControlBinding> Bindings;
};
