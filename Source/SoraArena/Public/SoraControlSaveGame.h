#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "InputCoreTypes.h"
#include "SoraControlSaveGame.generated.h"

USTRUCT()
struct FSoraControlBinding
{
    GENERATED_BODY()

    UPROPERTY(SaveGame) FName ActionName;
    UPROPERTY(SaveGame) FKey Key;
};

// Local input preferences have no authority over combat or wallet transactions.
UCLASS()
class SORAARENA_API USoraControlSaveGame : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY(SaveGame) int32 SaveSchema = 1;
    UPROPERTY(SaveGame) float MoveDeadZone = .18f;
    UPROPERTY(SaveGame) float LookDeadZone = .12f;
    UPROPERTY(SaveGame) float LookSensitivity = 1.f;
    UPROPERTY(SaveGame) bool InvertedLook = false;
    UPROPERTY(SaveGame) TArray<FSoraControlBinding> Bindings;
};
