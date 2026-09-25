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
struct FSoraDamagedEvent;
struct FSoraDialogueCue;
struct FSoraPrompt;

// A queued line as the HUD and voice playback need it: the speaker's names,
// the Japanese line with its English subtitle, and how long it holds.
struct FSoraSubtitle
{
    FString LineId;
    FString Speaker;
    FString SpeakerEnglish;
    FString Japanese;
    FString English;
    float Seconds = 0.f;
};

// Offline rounds on ASoraGameMode: the eight campaign chapters and the
// training arena. A chapter plays its schema-4 beats (Content/Data/campaign)
// in the order SoraBeatRules.h allows, and each beat's task through the same
// rules: cinematics on the letterboxed card, dialogue lines, waves released by
// their triggers, duels and bosses with their phases, stealth zones, the
// production tasks (hold, crank, escort, carry, manufacture, defend), rides
// and explore caches, at the beat's anchors (SoraWorldBuilderLayout.cpp).
// Failures follow the beat's rules: a checkpoint, a match retried in place, or
// the story moving on. Completing a beat restores its production site and
// unlocks its weapons, mechanics and story flags; the save (schema 6) keeps
// the checkpoint beat and phase, the beats done, the unlock and flag masks and
// the collectibles, and is refused unless SoraBeatRules accepts it. Lines are
// keyed by events (FireDialogueTrigger). Chapter-one forms use SoraDojoRules.h.
// The director ticks itself; the paused menu stops it.
UCLASS(ClassGroup=(Sora))
class SORAARENA_API USoraCampaignDirector : public UActorComponent
{
    GENERATED_BODY()
public:
    USoraCampaignDirector();
    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    // Reads the campaign save into the director and the mode; false when no
    // save object can be created. A save of another schema, or one whose
    // chapter, unlocks, flags or collectibles no route can reach, starts anew.
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
    // E: works the active beat at its anchor (an objective, a crank turn, a
    // pickup or delivery, a manufacturing stroke, a repair, a dialogue's
    // interact trigger) or opens an explore cache.
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

    // Events. FireDialogueTrigger plays the lines and HUD prompt an event
    // keys in the active beat and the chapter's bark pools ("beat_start",
    // "site_restored:1", "boss_phase:2", "player_died", "exit_reached",
    // "collectible:ch02.c03"). RaiseBeatEvent is how the world reports to the
    // beat (the AI lane's alert states and deaths, scripted events): it plays
    // the event's lines, releases the waves it names and applies the failure
    // it raises ("alert_state:alert", "npc_died:tokichi", "horse_down").
    void FireDialogueTrigger(FName Event);
    void RaiseBeatEvent(FName Event);
    // A defended target (a pack horse, the furnace) takes damage; true when it
    // is destroyed, which fails a beat that must keep it.
    bool DamageDefendedTarget(int32 Target, int32 Hp);

    // The line on screen: a cinematic subtitle on the card, else the head of
    // the dialogue queue.
    const FSoraDialogueCue* CurrentDialogueCue() const;
    // The dialogue queue, head first.
    TArray<FSoraSubtitle> QueuedSubtitles() const;
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
    // The active beat's task (an escort's route laid out by the world) and its progress.
    const SoraBeatRules::FTask& ActiveTask() const { return Task; }
    const SoraBeatRules::FTaskState& TaskProgress() const { return TaskState; }
    bool IsWeaponUnlocked(int32 WeaponId) const;
    bool IsStoryFlagSet(FName Flag) const;
    unsigned long long CollectedMask() const;
    // Where the active beat's objective stands, when it has one in the world,
    // and whether E works it there.
    bool ObjectiveAnchor(FVector& Location) const;
    bool AnchorTakesInteract() const;
    // Explore beats whose cache can be opened now, and where.
    TArray<int32> AvailableCaches() const;
    FVector CacheLocation(int32 Beat) const;
    // Seconds of the running cinematic, and whether it opens a fresh chapter
    // (the title card shows first).
    float CinematicElapsed() const;
    bool IsChapterOpening() const { return bChapterOpening; }
    int32 LinesQueued() const { return Queue.Num(); }
    bool LinesStarted() const { return bLinesStarted; }
    // Automation: a valid schema-6 checkpoint at the start of Beat (or a later
    // Phase) of Chapter, reached through every earlier required beat with the
    // unlocks chapter select grants.
    static bool SeedCheckpoint(USoraSaveGame& Target, int32 Chapter, int32 Beat, int32 Phase = 0);

    int32 ChapterId = 0;
    // Defeats in the active beat (or the training arena) and how many its
    // waves hold (the arena's twelve).
    int32 Kills = 0;
    int32 KillsNeeded = 0;
    bool bCampaignComplete = false;
private:
    // One opponent a released wave still has to put on the field.
    struct FPendingSpawn
    {
        int32 Wave = INDEX_NONE;
        FName Type;
    };
    ASoraGameMode& Mode() const;
    UPROPERTY() TObjectPtr<USoraSaveGame> Save;
    UPROPERTY() TArray<TObjectPtr<ASoraEnemy>> Enemies;
    UPROPERTY() TObjectPtr<ASoraBoss> BossActor;
    // The wave each spawned opponent belongs to; guards, duellists and bosses have none.
    TMap<const ASoraEnemy*, int32> EnemyWaves;
    TArray<FPendingSpawn> Pending;
    // Chapter progress and the unlocks and flags held when the chapter began.
    SoraBeatRules::FProgress BeatState{0u, 0u, 0u, 0u, 0u, false};
    unsigned EntryWeapons = 0u;
    unsigned EntryMechanics = 0u;
    unsigned EntryFlags = 0u;
    int32 BeatIndex = INDEX_NONE;
    int32 BeatPhase = 0;
    SoraBeatRules::FTask Task;
    SoraBeatRules::FTaskState TaskState;
    // Sub-millisecond carry of the integer beat clock.
    float ClockCarryMs = 0.f;
    // Where the beat's route (an escort, a ride, a stealth zone) began.
    FVector RouteStart = FVector::ZeroVector;
    int32 Spawned = 0;
    int32 IdleMs = 0;
    bool bLinesStarted = false;
    bool bChapterOpening = false;
    bool bCrankSlack = false;
    bool bHeroSeen = false;
    bool bDetected = false;
    float CinematicSeconds = 0.f;
    unsigned DojoLessonMask = 0u;
    // Dialogue: lines waiting, the head's remaining time, lines heard this
    // round, triggers already fired in it and when repeatable ones last played.
    TArray<int32> Queue;
    float LineRemaining = 0.f;
    TSet<int32> Heard;
    TSet<int32> FiredTriggers;
    TMap<int32, double> TriggerTimes;
    int32 PromptIndex = INDEX_NONE;
    float PromptRemaining = 0.f;
    // Training arena.
    int32 ArenaSitesMask = 0;
    bool bArenaComplete = false;

    bool LoadCheckpoint();
    // A hit on the hero knocks a carried item loose where the carry says so.
    void HeroDamaged(const FSoraDamagedEvent& Event);
    void BeginBeat(int32 Index, int32 Phase, bool bResumed);
    void RetryBeatInPlace();
    void CompleteActiveBeat();
    void FinishChapter();
    void CompleteOptional(int32 Index);
    void Collect(int32 Beat);
    void UpdateObjective();
    void TickBeat(float DeltaSeconds);
    void TickDialogue(float DeltaSeconds);
    // After any change to the task: plays the progress triggers crossed,
    // releases and spawns due waves and completes the beat once its task is done.
    void Progressed(int32 PermilleBefore);
    void QueueWaves(unsigned Waves);
    void HandleFailure(SoraBeatRules::ERetry Outcome, const FString& Event);
    bool FailureOf(const FString& Event, SoraBeatRules::EFail& Failure) const;
    void StartLines();
    // Plays the triggers and shows the HUD prompt an event raises in Beat
    // (the active beat by default) and the chapter's bark pools.
    void Fire(const FString& Event, int32 Beat = INDEX_NONE);
    bool TriggerAllowed(int32 Index) const;
    void Enqueue(const TArray<int32>& Lines, bool bForce);
    void ShowPrompt(const FString& Event, int32 Beat);
    void Notify(const FString& Japanese, const FString& English, float Seconds);
    // Who a beat puts on the field. The AI lane's archetypes
    // (Content/Data/enemies.json) and data-driven bosses (bosses.json) replace
    // these bodies at merge; until then every opponent is the prototype
    // invader, a sparring pupil or the collector.
    ASoraEnemy* SpawnWaveOpponent(FName Type, bool bSparring, int32 Slot);
    ASoraEnemy* SpawnStealthGuard(FName Type, int32 Slot);
    ASoraEnemy* SpawnDuelOpponent(FName Opponent, bool bSparring, int32 Slot);
    ASoraBoss* SpawnBoss(FName Boss, int32 Slot);
    void SpawnCast(bool bKeepPupil);
    void SpawnPending();
    void AddOpponent(ASoraEnemy* Enemy, int32 Wave);
    void SpawnArenaInvader();
    void ClearOpponents();
    int32 LiveWaveOpponents() const;
    void CheckPhase();
    // The point (TaskAnchor) of the active objective, or INDEX_NONE.
    int32 ObjectivePoint() const;
    FVector PointLocation(int32 Point) const;
    FVector PartyLocation() const;
    bool HeroAtTask() const;
    bool Contested() const;
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
