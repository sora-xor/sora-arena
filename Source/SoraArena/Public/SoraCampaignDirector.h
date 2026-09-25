#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SoraBeatRules.h"
#include "SoraDojoRules.h"
#include "SoraCampaignDirector.generated.h"
class ASoraBoss;
class ASoraEnemy;
class ASoraGameMode;
class ASoraPlayerCharacter;
class USoraSaveGame;
struct FSoraBeat;
struct FSoraChapter;
struct FSoraDialogueCue;
struct FSoraPrompt;

// Offline rounds on ASoraGameMode: the eight campaign chapters and the
// training arena. A chapter plays its schema-4 beats (Content/Data/campaign)
// in the order SoraBeatRules.h allows: cinematics on the letterboxed card,
// dialogue lines, opponents and bosses, dojo lessons, and interactions,
// holds or journeys at each beat's anchor (SoraWorldBuilderLayout.cpp).
// Completing a beat restores its production site and unlocks its weapons and
// mechanics; the save (schema 6) keeps the checkpoint beat, the beats done,
// the unlock masks and the collectibles, and is refused unless SoraBeatRules
// accepts it. Chapter-one forms use SoraDojoRules.h. The director ticks
// itself; the paused menu stops it.
UCLASS(ClassGroup=(Sora))
class SORAARENA_API USoraCampaignDirector : public UActorComponent
{
    GENERATED_BODY()
public:
    USoraCampaignDirector();
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    // Reads the campaign save into the director and the mode; false when no
    // save object can be created. A save of another schema, or one whose
    // chapter, unlocks or collectibles no route can reach, starts anew.
    bool LoadSave();
    bool HasSave() const { return Save != nullptr; }
    // Builds the chapter or arena, restores a valid checkpoint and starts its beat.
    void ResetRound();
    // Destroys opponents and live shells so kernel practice can take the arena.
    void ClearEncounter();
    // After a completed chapter: the next chapter is saved, or the campaign is
    // liberated and the menu reopens (returns false).
    bool AdvanceChapter();
    // New Campaign, confirmed: back to the dojo with no checkpoint or unlocks.
    void StartOver();
    // Return to the saved chapter from practice or the arena.
    void ResumeSavedChapter();
    // The front end's chapter select and New Campaign confirmation: the
    // highest chapter reached, a fresh start of any chapter up to it (with
    // every unlock the earlier chapters offer), and whether the save holds
    // anything New Campaign would erase.
    int32 HighestChapter() const;
    bool SelectChapter(int32 Chapter);
    bool HasProgress() const;
    // Chapter one only: pupils drop their windups; the hero drops the guard
    // and recovery lesson when the menu opens.
    void SuspendDojo(bool bIncludeHero);
    // E: works the active beat's anchor (a crank turn, a delivery, a step, an
    // objective, a dialogue's interact trigger) or opens an explore cache.
    void Interact(ASoraPlayerCharacter& Player);
    // Enter on a cinematic: skips it and starts the next beat now.
    void SkipCinematic();
    void OpponentDefeated(ASoraEnemy* Opponent);
    void PlayerKilled();
    bool RecordDojoLesson(SoraDojoRules::EAction Action, int32 DurationMs,
        bool bFacingAttacker = true, int32 RecoveryMs = 0);
    bool CanScoreDojoBout() const;
    int32 DojoLessonStage() const;
    void SaveProgress();
    // The line on screen: a cinematic subtitle on the card, else the head of
    // the dialogue queue.
    const FSoraDialogueCue* CurrentDialogueCue() const;
    // The active beat's HUD prompt while it shows.
    const FSoraPrompt* CurrentPrompt() const;
    const ASoraBoss* CampaignBoss() const;
    FString ObjectiveText() const;
    FString ObjectiveTextEnglish() const;
    FString DojoLessonText(bool bEnglish) const;

    // Beat state for the HUD and automation.
    const FSoraChapter* ActiveChapter() const;
    const FSoraBeat* ActiveBeatData() const;
    int32 ActiveBeat() const { return BeatIndex; }
    int32 ActivePhase() const { return BeatPhase; }
    const SoraBeatRules::FProgress& Progress() const { return BeatState; }
    bool IsWeaponUnlocked(int32 WeaponId) const;
    unsigned long long CollectedMask() const;
    // Where the active beat's objective stands, when it has one in the world.
    bool ObjectiveAnchor(FVector& Location) const;
    // Explore beats whose cache can be opened now, and where.
    TArray<int32> AvailableCaches() const;
    FVector CacheLocation(int32 Beat) const;
    // Seconds of the running cinematic, and whether it opens a fresh chapter
    // (the title card shows first).
    float CinematicElapsed() const;
    bool IsChapterOpening() const { return bChapterOpening; }
    // Progress toward the active beat's goal: interactions, held seconds, or
    // for dialogue the lines still to come.
    int32 Interactions() const { return InteractCount; }
    float HeldSeconds() const { return HoldSeconds; }
    int32 LinesQueued() const { return Queue.Num(); }
    bool LinesStarted() const { return bLinesStarted; }
    // Automation: a valid schema-6 checkpoint at the start of Beat (or a later
    // Phase) of Chapter, reached through every earlier required beat with the
    // unlocks chapter select grants.
    static bool SeedCheckpoint(USoraSaveGame& Target, int32 Chapter, int32 Beat, int32 Phase = 0);

    int32 ChapterId = 0;
    // Defeats in the active beat (or the training arena) and how many it needs.
    int32 Kills = 0;
    int32 KillsNeeded = 0;
    bool bCampaignComplete = false;
private:
    ASoraGameMode& Mode() const;
    UPROPERTY() TObjectPtr<USoraSaveGame> Save;
    UPROPERTY() TArray<TObjectPtr<ASoraEnemy>> Enemies;
    UPROPERTY() TObjectPtr<ASoraBoss> BossActor;
    // Chapter progress and the unlocks held when the chapter began.
    SoraBeatRules::FProgress BeatState{0u, 0u, 0u, 0u, false};
    unsigned EntryWeapons = 0u;
    unsigned EntryMechanics = 0u;
    int32 BeatIndex = INDEX_NONE;
    int32 BeatPhase = 0;
    int32 Spawned = 0;
    int32 InteractCount = 0;
    float HoldSeconds = 0.f;
    bool bReached = false;
    bool bLinesStarted = false;
    bool bChapterOpening = false;
    float CinematicSeconds = 0.f;
    unsigned DojoLessonMask = 0u;
    // Dialogue: lines waiting, the head's remaining time, lines heard this
    // round, and triggers already fired in it.
    TArray<int32> Queue;
    float LineRemaining = 0.f;
    TSet<int32> Heard;
    TSet<int32> FiredTriggers;
    int32 PromptIndex = INDEX_NONE;
    float PromptRemaining = 0.f;
    // Training arena.
    int32 ArenaSitesMask = 0;
    bool bArenaComplete = false;

    bool LoadCheckpoint();
    void BeginBeat(int32 Index, int32 Phase, bool bResumed);
    void CompleteActiveBeat();
    void FinishChapter();
    void CompleteOptional(int32 Index);
    void Collect(int32 Beat);
    void UpdateObjective();
    void TickBeat(float DeltaSeconds);
    void TickDialogue(float DeltaSeconds);
    // Plays the triggers and shows the HUD prompt an event raises in Beat
    // (the active beat by default).
    void Fire(const FString& Event, int32 Beat = INDEX_NONE);
    void Enqueue(const TArray<int32>& Lines, bool bForce);
    void ShowPrompt(const FString& Event, int32 Beat);
    void Notify(const FString& Japanese, const FString& English, float Seconds);
    void SpawnOpponents();
    void SpawnOne();
    void ClearOpponents();
    void CheckPhase();
    bool WavesCleared() const;
    bool Near(const FVector& Location, float Radius) const;
    void ApplyLoadout();
    void BroadcastBeat(bool bStarted, bool bResumed);
    void Telemetry(const TCHAR* Event) const;
    void SaveCheckpoint();
    void ClearCheckpoint();
    void ClearOfflineProjectiles();
    // Training arena rounds (not campaign).
    void ArenaInteract(ASoraPlayerCharacter& Player);
};
