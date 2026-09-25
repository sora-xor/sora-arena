#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SoraBeatRules.h"
#include "SoraDojoRules.h"
#include "SoraCampaignDirector.generated.h"
class ACameraActor;
class ASoraBoss;
class ASoraEnemy;
class ASoraGameMode;
class ASoraHorse;
class ASoraPlayerCharacter;
class USoraSaveGame;
struct FSoraBeat;
struct FSoraBeatSpace;
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

// A story notice the HUD shows apart from system notices: a weapon or
// mechanic unlocked, a collectible found, a production site restored.
struct FSoraStoryNotice
{
    enum class EKind : uint8 { Weapon, Mechanic, Collectible, Site };
    EKind Kind = EKind::Weapon;
    FString Japanese;
    FString English;
    // A collectible's codex entry, or the site's restored line.
    FString Detail;
    FString DetailEnglish;
    float Remaining = 0.f;
};

// Offline rounds on ASoraGameMode: the eight campaign chapters and the
// training arena. A chapter plays its schema-4 beats (Content/Data/campaign)
// in the order SoraBeatRules.h allows, and each beat's task through the same
// rules, in the chapter's space (FSoraSpace, built by ASoraWorldBuilder):
// cinematics through a camera that dollies over their place behind the
// letterboxed card; dialogue lines; waves released by their triggers and put
// on the field at the beat's spawns; duels and bosses with their phases;
// stealth zones whose guards stand on patrol routes; the production tasks
// (hold, crank, escort, carry, manufacture, defend) at their points with their
// kits; rides on Kurimaru and the other horses (SoraMountRules.h); explore
// caches and loose collectibles. A beat in another place than the hero cuts
// to its entry (travel); the hero entering a trigger volume raises its event.
// Failures follow the beat's rules: a checkpoint, a match retried in place, or
// the story moving on. Completing a beat restores its production site and
// unlocks its weapons, mechanics and story flags; the save (schema 6) keeps
// the checkpoint beat and phase, the beats done, the unlock and flag masks and
// the collectibles, and is refused unless SoraBeatRules accepts it. Lines are
// keyed by events (FireDialogueTrigger). Chapter-one forms use SoraDojoRules.h.
// World-facing play (travel, volumes, points, spawns, horses, carry, siege,
// escort, pickups, the cinematic camera) lives in
// Private/Game/SoraCampaignDirectorWorld.cpp. The director ticks itself; the
// paused menu stops it.
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
    // Destroys opponents, horses and live shells so kernel practice can take the arena.
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
    // E: works the active beat at its point (an objective, a crank turn, a
    // pickup or delivery, a manufacturing stroke, a repair, a dialogue's
    // interact trigger); tacks up, mounts (from her right) or dismounts the
    // horse; picks up a loose collectible; or opens an explore cache.
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
    // Unlocks, finds and restored sites for the HUD, oldest first.
    const TArray<FSoraStoryNotice>& StoryNotices() const { return Notices; }

    // Beat state for the HUD and automation.
    const FSoraChapter* ActiveChapter() const;
    const FSoraBeat* ActiveBeatData() const;
    const FSoraBeatSpace* ActiveSpace() const;
    int32 ActiveBeat() const { return BeatIndex; }
    int32 ActivePhase() const { return BeatPhase; }
    const SoraBeatRules::FProgress& Progress() const { return BeatState; }
    const SoraBeatRules::FTask& ActiveTask() const { return Task; }
    const SoraBeatRules::FTaskState& TaskProgress() const { return TaskState; }
    bool IsWeaponUnlocked(int32 WeaponId) const;
    bool IsStoryFlagSet(FName Flag) const;
    unsigned long long CollectedMask() const;
    // Where the active beat's objective stands, and whether E works it there.
    bool ObjectiveAnchor(FVector& Location) const;
    bool AnchorTakesInteract() const;
    // Explore beats whose cache can be opened now, and where.
    TArray<int32> AvailableCaches() const;
    FVector CacheLocation(int32 Beat) const;
    // The chapter's collectibles still lying loose (its space's pickups), and where.
    TArray<int32> LoosePickups() const;
    FVector PickupLocation(int32 Pickup) const;
    // Where the escorted party walks, and the zone the hero stands in
    // (INDEX_NONE for the hub, -2 for none).
    FVector PartyLocation() const;
    int32 HeroZone() const;
    // A guard's patrol route, for the AI lane's patrol behaviour.
    const TArray<FVector2D>* GuardPatrol(const ASoraEnemy* Guard) const;
    // Seconds of the running cinematic, whether it opens a fresh chapter (the
    // title card shows first), and the camera it plays through.
    float CinematicElapsed() const;
    bool IsChapterOpening() const { return bChapterOpening; }
    ACameraActor* CinematicCamera() const { return ShotCamera; }
    int32 LinesQueued() const { return Queue.Num(); }
    bool LinesStarted() const { return bLinesStarted; }
    // The active beat's riding horse (ridden or waiting), its pack horses, how
    // much of her tack is on, and whether the hero rides her.
    ASoraHorse* Steed() const { return Horse; }
    TArray<ASoraHorse*> PackHorses() const;
    int32 TackDone() const { return TackSteps; }
    bool IsMounted() const;
    // A weapon acts from the saddle only in its mounted arc, and under a
    // carried load only if the carry's loadout keeps it; a refusal raises a notice.
    bool ArmsReady(int32 WeaponId, float AimYaw, bool bNotify);
    // Whether the hero may hold a weapon at all in the saddle or under a load.
    bool CanHold(int32 WeaponId, bool bNotify);
    // The carried load's pace (1 when nothing is carried).
    float CarryPace() const;
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
    UPROPERTY() TObjectPtr<ASoraHorse> Horse;
    UPROPERTY() TArray<TObjectPtr<ASoraHorse>> Pack;
    UPROPERTY() TObjectPtr<ACameraActor> ShotCamera;
    // The wave each spawned opponent belongs to; guards, duellists and bosses have none.
    TMap<const ASoraEnemy*, int32> EnemyWaves;
    // A stealth guard's patrol route (an index into the beat's patrols).
    TMap<const ASoraEnemy*, int32> GuardPatrols;
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
    int32 Spawned = 0;
    int32 IdleMs = 0;
    bool bLinesStarted = false;
    bool bChapterOpening = false;
    bool bCrankSlack = false;
    bool bHeroSeen = false;
    bool bDetected = false;
    float CinematicSeconds = 0.f;
    unsigned DojoLessonMask = 0u;
    // Trigger volumes the hero has entered in the active beat; the horse's
    // tack-up and its refusals; opponents already inside her fear radius.
    TSet<int32> VolumesEntered;
    int32 TackSteps = 0;
    int32 TackRefused = 0;
    TSet<const ASoraEnemy*> Frightening;
    // The escorted party's progress last shown, so the kit knows they walk.
    int32 LastEscortProgress = 0;
    // Dialogue: lines waiting, the head's remaining time, lines heard this
    // round, triggers already fired in it and when repeatable ones last played.
    TArray<int32> Queue;
    float LineRemaining = 0.f;
    TSet<int32> Heard;
    TSet<int32> FiredTriggers;
    TMap<int32, double> TriggerTimes;
    int32 PromptIndex = INDEX_NONE;
    float PromptRemaining = 0.f;
    TArray<FSoraStoryNotice> Notices;
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
    // Releases the volume and event waves an event names.
    void ReleaseEventWaves(const FString& Event);
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
    void Tell(FSoraStoryNotice::EKind Kind, const FString& Japanese, const FString& English,
        const FString& Detail = FString(), const FString& DetailEnglish = FString());
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

    // World-facing play (SoraCampaignDirectorWorld.cpp).
    // Where the active objective stands and whether E works it there.
    bool ObjectivePoint(FVector& Location, bool& bInteract) const;
    // Where an opponent of this slot enters the field: the beat's spawns, or
    // on a road the next ones ahead of the hero.
    FVector SpawnLocation(int32 Slot) const;
    // The beat's place as it starts: a travel cut to its entry, its kit, its
    // horse and its camera; and what it leaves behind when it ends.
    void EnterBeatSpace(bool bResumed);
    void LeaveBeatSpace();
    void TickSpace(int32 DeltaMs);
    void TickVolumes();
    void TickHorses();
    void TickSiege(int32 DeltaMs);
    // E on a loose collectible within reach, or on the horse (tack-up, mount, dismount); true when used.
    bool PickUp();
    bool InteractSpace(ASoraPlayerCharacter& Player);
    void Dismount();
    void ClearHorses();
    void ShowKit();
    void ShowPickups();
    // A carried load changed: the load in the hero's arms and the weapon he may hold.
    void CarryChanged();
    void StartCinematicCamera();
    void UpdateCinematicCamera();
    void EndCinematicCamera(float BlendSeconds);
    // How far along its road the hero has come, permille of the way.
    int32 RoadPermille() const;
};
