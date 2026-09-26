#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SoraDojoRules.h"
#include "SoraCampaignDirector.generated.h"
class ASoraBoss;
class ASoraEnemy;
class ASoraGameMode;
class ASoraPlayerCharacter;
class USoraSaveGame;
struct FSoraDialogueCue;

// Offline rounds on ASoraGameMode: the eight campaign chapters and the
// training arena. Owns the campaign save and checkpoints, the chapter's
// opponents and final collector, production sites and the exit, the dojo
// forms, chapter dialogue and the objective text. Rules come from
// SoraCampaignRules.h and SoraDojoRules.h, which the host tests also compile.
UCLASS(ClassGroup=(Sora))
class SORAARENA_API USoraCampaignDirector : public UActorComponent
{
    GENERATED_BODY()
public:
    USoraCampaignDirector();
    // Reads the campaign save into the director and the mode; false when no
    // save object can be created.
    bool LoadSave();
    bool HasSave() const { return Save != nullptr; }
    // Builds the chapter or arena, restores a valid checkpoint and spawns opponents.
    void ResetRound();
    // Destroys opponents and live shells so kernel practice can take the arena.
    void ClearEncounter();
    // After a completed chapter: the next chapter is saved, or the campaign is
    // liberated and the menu reopens (returns false).
    bool AdvanceChapter();
    // New Campaign, confirmed: back to the dojo with no checkpoint.
    void StartOver();
    // Return to the saved chapter from practice or the arena.
    void ResumeSavedChapter();
    // The front end's chapter select and New Campaign confirmation: the
    // highest chapter reached, a fresh start of any chapter up to it (the
    // saved chapter moves there, its checkpoint is cleared, the reach is
    // kept), and whether the save holds anything New Campaign would erase.
    int32 HighestChapter() const;
    bool SelectChapter(int32 Chapter);
    bool HasProgress() const;
    // Chapter one only: pupils drop their windups; the hero drops the guard
    // and recovery lesson when the menu opens.
    void SuspendDojo(bool bIncludeHero);
    void Interact(ASoraPlayerCharacter& Player);
    void OpponentDefeated(ASoraEnemy* Opponent);
    void PlayerKilled();
    bool RecordDojoLesson(SoraDojoRules::EAction Action, int32 DurationMs,
        bool bFacingAttacker = true, int32 RecoveryMs = 0);
    bool CanScoreDojoBout() const;
    int32 DojoLessonStage() const;
    void SaveProgress();
    const FSoraDialogueCue* CurrentDialogueCue() const;
    const ASoraBoss* CampaignBoss() const;
    FString ObjectiveText() const;
    FString ObjectiveTextEnglish() const;
    FString DojoLessonText(bool bEnglish) const;
    int32 ChapterId = 0;
    int32 Kills = 0;
    int32 KillsNeeded = 6;
    bool bCampaignComplete = false;
private:
    ASoraGameMode& Mode() const;
    UPROPERTY() TObjectPtr<USoraSaveGame> Save;
    UPROPERTY() TArray<TObjectPtr<ASoraEnemy>> Enemies;
    UPROPERTY() TObjectPtr<ASoraBoss> BossActor;
    int32 Spawned = 0;
    unsigned DojoLessonMask = 0u;
    bool bPlayChapterDialogue = false;
    void SpawnEnemy();
    void SaveCheckpoint();
    void ClearCheckpoint();
    void ClearOfflineProjectiles();
};
