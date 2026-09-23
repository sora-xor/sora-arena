#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "SoraSaveGame.generated.h"
UCLASS()
class SORAARENA_API USoraSaveGame : public USaveGame
{
    GENERATED_BODY()
public:
    // Legacy prototype checkpoints are not interpreted under the first-release
    // chapter rules, where the dojo uses nonlethal sparring.
    UPROPERTY(SaveGame) int32 SaveSchema = 0;
    UPROPERTY(SaveGame) int32 CurrentChapter = 0;
    UPROPERTY(SaveGame) int32 HighestChapter = 0;
    UPROPERTY(SaveGame) int32 SelectedClass = 0;
    UPROPERTY(SaveGame) bool CampaignComplete = false;
    UPROPERTY(SaveGame) bool EnglishSubtitles = true;
    // A chapter checkpoint is local campaign state; it never contains wallet or bond data.
    UPROPERTY(SaveGame) int32 CheckpointChapter = -1;
    UPROPERTY(SaveGame) int32 CheckpointKills = 0;
    UPROPERTY(SaveGame) int32 CheckpointNodesMask = 0;
    UPROPERTY(SaveGame) bool CheckpointComplete = false;
    // Chapter-one stance, guard, parry, and recovery form a prefix mask.
    UPROPERTY(SaveGame) int32 CheckpointDojoLessonMask = 0;
};
