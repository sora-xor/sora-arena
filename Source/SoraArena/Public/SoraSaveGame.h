#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "SoraSaveGame.generated.h"

// The offline campaign save, schema 6. It is local campaign state only and
// never holds wallet, bond or NFT data; campaign unlocks never grant
// multiplayer entitlement. USoraCampaignDirector checks every field against
// the chapter beats (SoraBeatRules.h) and refuses any other schema.
UCLASS()
class SORAARENA_API USoraSaveGame : public USaveGame
{
    GENERATED_BODY()
public:
    static constexpr int32 Schema = 6;
    UPROPERTY(SaveGame) int32 SaveSchema = 0;
    UPROPERTY(SaveGame) int32 CurrentChapter = 0;
    UPROPERTY(SaveGame) int32 HighestChapter = 0;
    UPROPERTY(SaveGame) int32 SelectedClass = 0;
    UPROPERTY(SaveGame) bool CampaignComplete = false;
    UPROPERTY(SaveGame) bool EnglishSubtitles = true;
    // Weapon IDs 0-20 and campaign.json mechanic bits held when CurrentChapter began.
    UPROPERTY(SaveGame) int32 ChapterEntryWeapons = 0;
    UPROPERTY(SaveGame) int32 ChapterEntryMechanics = 0;
    // Codex entries found, bit chapter * 6 + mask_bit; they never grant stats.
    UPROPERTY(SaveGame) int64 Collectibles = 0;
    // The checkpoint: the start of CheckpointBeat, or a later boss or duel
    // phase, with the beats completed before it and the sites, weapons and
    // mechanics they earned. CheckpointBeat -1 with CheckpointComplete keeps a
    // finished chapter waiting at its result screen.
    UPROPERTY(SaveGame) int32 CheckpointChapter = -1;
    UPROPERTY(SaveGame) int32 CheckpointBeat = -1;
    UPROPERTY(SaveGame) int32 CheckpointPhase = 0;
    UPROPERTY(SaveGame) int32 CheckpointBeatsMask = 0;
    UPROPERTY(SaveGame) int32 CheckpointSitesMask = 0;
    UPROPERTY(SaveGame) int32 CheckpointWeapons = 0;
    UPROPERTY(SaveGame) int32 CheckpointMechanics = 0;
    UPROPERTY(SaveGame) bool CheckpointComplete = false;
    // Chapter-one stance, guard, parry and recovery form a prefix mask.
    UPROPERTY(SaveGame) int32 CheckpointDojoLessonMask = 0;
};
