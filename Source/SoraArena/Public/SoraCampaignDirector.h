#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SoraBeatRules.h"
#include "SoraCrankInputRules.h"
#include "SoraDojoRules.h"
#include "SoraRegistry.h"
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
struct FSoraDefenseEvent;
struct FSoraDialogueCue;
struct FSoraGuard;
struct FSoraEnemyCueEvent;
struct FSoraMarobashiEvent;
struct FSoraStealthDetection;
struct FSoraPrompt;
namespace SoraText { struct FLine; }

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
    enum class EKind : uint8 { Weapon, Mechanic, Collectible, Site, Registry };
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
// stealth zones, and production tasks under guard, whose guards stand on
// patrol routes; the production tasks (hold, crank, escort, carry,
// manufacture, defend) at their points with their kits; rides on Kurimaru and
// the other horses (SoraMountRules.h); explore caches and loose collectibles.
// A beat in another place than the hero cuts to its entry (travel); the hero
// entering a trigger volume raises its event. Failures follow the beat's
// rules: a checkpoint, a match retried in place, or the story moving on. A
// beat teaches its weapons and mechanics while it is in play; completing it
// restores its production site and keeps its weapons, mechanics and story
// flags; the save (schema 6) keeps the checkpoint beat and phase, the beats
// done, the unlock and flag masks and the collectibles, and is refused unless
// SoraBeatRules accepts it. Lines are keyed by events (FireDialogueTrigger).
// Chapter-one forms use SoraDojoRules.h. World-facing play (travel, volumes,
// points, spawns, horses, carry, siege, escort, pickups, the cinematic camera)
// lives in Private/Game/SoraCampaignDirectorWorld.cpp. Each beat's fieldcraft
// (lamps, noisy floors, water, a climbing face, stones, the candle, the
// escorted party and allies) is staged in USoraFieldcraft as the beat starts,
// and what happens there reaches the beat as events. An event a script keys
// "<event>+Ns" plays N seconds after <event>. The director ticks itself; the
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
    // A boss or duellist the active fight spares (disarmed, captured, a duel
    // not to the death) yields where it stands at zero health instead of
    // falling; a captive stays there until the hero binds it with E.
    bool SparesOpponent(const ASoraEnemy& Opponent) const;
    bool IsCaptive(const ASoraEnemy& Opponent) const;
    bool AwaitingCapture() const;
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
    bool IsDialogueBlocking() const { return bDialogueHeld; }
    bool IsToriiEpilogue() const;
    bool HasWashioSword() const;
    bool HasReturnedWashioSword() const;
    bool HasRehungPlaques() const;
    // The dialogue queue, head first.
    TArray<FSoraSubtitle> QueuedSubtitles() const;
    // The active beat's HUD prompt while it shows.
    const FSoraPrompt* CurrentPrompt() const;
    const ASoraBoss* CampaignBoss() const;
    FString ObjectiveText() const;
    FString ObjectiveTextEnglish() const;
    FString DojoLessonText(bool bEnglish) const;
    bool IsMaaiLesson() const;
    bool MaaiReady() const;
    bool MaaiInBand() const;
    bool MaaiNeedsHelp() const;
    float MaaiDistance() const;
    ASoraEnemy* MaaiMentor() const;
    // Unlocks, finds and restored sites for the HUD, oldest first.
    const TArray<FSoraStoryNotice>& StoryNotices() const { return Notices; }
    // Goods completed in this chapter, reconstructed from checkpoint progress.
    TArray<FSoraRegistryRow> RegistryRows() const;

    // Beat state for the HUD and automation.
    const FSoraChapter* ActiveChapter() const;
    const FSoraBeat* ActiveBeatData() const;
    const FSoraBeatSpace* ActiveSpace() const;
    int32 ActiveBeat() const { return BeatIndex; }
    int32 ActivePhase() const { return BeatPhase; }
    const SoraBeatRules::FProgress& Progress() const { return BeatState; }
    const SoraBeatRules::FTask& ActiveTask() const { return Task; }
    const SoraBeatRules::FTaskState& TaskProgress() const { return TaskState; }
    // What the hero may use now: what the campaign has unlocked and what the
    // beat in play teaches (SoraBeatRules::InPlayWeapons, InPlayMechanics).
    bool IsWeaponUnlocked(int32 WeaponId) const;
    bool IsMechanicInPlay(FName Mechanic) const;
    bool IsStoryFlagSet(FName Flag) const;
    // 活人剣: the debt-bound conscript whose seal the hero is cutting (Interact
    // held beside a knocked-down conscript once seal_cut is in play), and how
    // far the cut has come (0-1).
    const ASoraEnemy* SealBeingCut() const { return SealTarget.Get(); }
    float SealCutProgress() const;
    // Work held at a point (0-1), or -1 when none is: a load hoisted at its
    // pickup (ch03.b05's 釣瓶, waiting while a guard watches) or an objective
    // worked with Interact held (a charge planted, a relay node pulled).
    float HeldWorkProgress() const;
    bool IsHoisting() const { return HeldWork == EHeldWork::Hoist; }
    bool IsPryingCarryGate() const { return bPryingCarryGate; }
    bool InLiftGallery() const { return bLiftGallery; }
    bool LiftExitPoint(FVector& Point) const;
    int32 WorkingCrankHelpers() const { return ActiveCrankHelpers; }
    bool CrankHelperRetreating() const { return bCrankHelperRetreating; }
    bool IsWorkingCrank() const;
    bool CrankOccupiesHands() const { return Task.CrankTwoHanded && IsWorkingCrank(); }
    void StopPlayerCrank(bool bWaitForRelease=true);
    bool NeedsCarryGate() const { return !SoraBeatRules::CarryGateReady(TaskState,Task); }
    FVector LooseLoadLocation(int32 Slot) const;
    bool IsRecoveringEquipment() const { return bStringingBow; }
    bool IsClimbingRecoveryWell() const { return RecoveryClimb != ERecoveryClimb::None; }
    bool NeedsEquipmentRecovery() const { return !SoraBeatRules::EquipmentReady(TaskState,Task); }
    FVector RecoveryApproach() const;
    FVector RecoveryBottom() const;
    bool IsHeldWorkWatched() const { return bHeldWatched; }
    unsigned long long CollectedMask() const;
    // Where the active beat's objective stands, and whether E works it there.
    bool ObjectiveAnchor(FVector& Location) const;
    bool AnchorTakesInteract() const;
    // Explore beats whose cache can be opened now, and where. Opening one
    // saves a checkpoint when the active beat can be restored from where play
    // stands (its start, or a boss or duel phase it saves at).
    TArray<int32> AvailableCaches() const;
    FVector CacheLocation(int32 Beat) const;
    // The chapter's collectibles still lying loose (its space's pickups), and where.
    TArray<int32> LoosePickups() const;
    FVector PickupLocation(int32 Pickup) const;
    // Where the escorted party walks, and the zone the hero stands in
    // (INDEX_NONE for the hub, -2 for none).
    FVector PartyLocation() const;
    int32 HeroZone() const;
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
        bool bInvulnerable = false;
    };
    ASoraGameMode& Mode() const;
    UPROPERTY() TObjectPtr<USoraSaveGame> Save;
    UPROPERTY() TArray<TObjectPtr<ASoraEnemy>> Enemies;
    UPROPERTY() TObjectPtr<ASoraBoss> BossActor;
    UPROPERTY() TObjectPtr<ASoraHorse> Horse;
    UPROPERTY() TArray<TObjectPtr<ASoraHorse>> Pack;
    UPROPERTY() TObjectPtr<ACameraActor> ShotCamera;
    // The wave each spawned opponent belongs to (guards, duellists and bosses
    // have none). Weak keys: a fallen opponent's entry leaves with it, and an
    // opponent built later at a freed address never inherits it.
    TMap<TWeakObjectPtr<const ASoraEnemy>, int32> EnemyWaves;
    // A captured boss yielded here, waiting for the hero's hand.
    UPROPERTY() TObjectPtr<ASoraEnemy> Captive;
    TWeakObjectPtr<ASoraEnemy> SealTarget;
    float SealStartedAt = 0.f;
    bool BeginSealCut(ASoraPlayerCharacter& Player);
    void TickSealCut();
    FVector2D CaptiveAt = FVector2D::ZeroVector;
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
    int32 ActiveCrankHelpers = 0;
    bool bCrankHelperRetreating = false;
    int32 CrankHelpers();
    SoraCrankInputRules::FState CrankInput;
    bool PlayerCrankEligible() const;
    bool TurnPlayerCrank(bool bBegin);
    void TickPlayerCrank(int32 DeltaMs);
    bool bLiftGallery=false;
    bool LiftReadyToComplete() const;
    bool BeginLiftGallery();
    bool TickLiftGallery(float DeltaSeconds);
    FVector WorkAnchor() const;
    bool NearFloor(const FVector& Location,float Radius) const;
    bool AtWorkAnchor(float Radius) const;
    ASoraEnemy* SpawnLiftOpponent(FName Type,int32 Wave,int32 Slot);
    int32 LiftDecayMultiplier() const;
    bool bDetected = false;
    float CinematicSeconds = 0.f;
    unsigned DojoLessonMask = 0u;
    // Trigger volumes the hero has entered in the active beat; the horse's
    // tack-up and its refusals; opponents already inside her fear radius.
    TSet<int32> VolumesEntered;
    int32 TackSteps = 0;
    int32 TackRefused = 0;
    TSet<TWeakObjectPtr<const ASoraEnemy>> Frightening;
    // Events raised in the active beat, so an event's ":first" rows play once,
    // and how many times each was raised (its "@N" rows).
    TSet<FString> BeatEvents;
    TMap<FString,int32> EventRaises;
    // "<event>+Ns" rows waiting on the beat clock (world seconds, event).
    TArray<TPair<double, FString>> Scheduled;
    // When a whistle brings the horse back (or -1).
    double WhistleAt=-1.0;
    // Work held at a point: what it is, the pickup or objective, the ms held
    // and whether a guard watches.
    enum class EHeldWork : uint8 { None, Hoist, Objective };
    EHeldWork HeldWork=EHeldWork::None;
    int32 HeldPoint=INDEX_NONE;
    int32 HeldMs=0;
    bool bHeldWatched=false;
    bool TakeLoad(int32 Pickup);
    bool bPryingCarryGate=false;
    bool bCarryGateHit=false;
    FVector LooseLoadAt[SoraBeatRules::MaxPoints] = {};
    void ResetCarryWork();
    bool InteractCarryGate(ASoraPlayerCharacter& Hero);
    void TickCarryWork(int32 DeltaMs);
    bool SetDownLoad(ASoraPlayerCharacter& Hero);
    bool TakeLooseLoad(ASoraPlayerCharacter& Hero);
    bool WorkObjectiveAt(int32 Objective);
    void TickHeldWork(int32 DeltaMs);
    enum class ERecoveryClimb : uint8 { None, Enter, Down, Up, Exit };
    ERecoveryClimb RecoveryClimb=ERecoveryClimb::None;
    bool bStringingBow=false;
    void ResetEquipmentRecovery();
    bool InteractRecovery(ASoraPlayerCharacter& Player);
    void TickEquipmentRecovery(int32 DeltaMs);
    void EndRecoveryClimb();
    bool AtRecoveryBottom() const;
    // Later zones an earlier zone's detection has warned (x_on_detected_carryover).
    TSet<FString> DetectionCarried;
    // Work under guard was seen last step; each guard's last reported state.
    bool bWorkWasSeen = false;
    TMap<TWeakObjectPtr<const AActor>, FName> GuardStates;
    // Chapter one: bouts the chapter's earlier lesson duels scored (bouts are
    // numbered across the dojo), the beat clock at an awase that 転 must
    // follow, and when a pupil's cut landed on a hero still to meet it.
    int32 BoutOffset = 0;
    int32 AwaseAtMs = INDEX_NONE;
    double LateHitAt = -1.0;
    // The escorted party's progress last shown, so the kit knows they walk.
    int32 LastEscortProgress = 0;
    // Dialogue: lines waiting, the head's remaining time, lines heard this
    // round, triggers already fired in it and when repeatable ones last played.
    struct FQueuedLine { int32 Line; int32 Beat; bool bBlocking; };
    TArray<FQueuedLine> Queue;
    float LineRemaining = 0.f;
    float BlockingSeconds = 0.f;
    bool bDialogueHeld = false;
    bool bBlockingLimitReached = false;
    TSet<int32> FinishedLines;
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
    // A hit on the hero knocks a carried item loose where the carry says so,
    // and in the dojo marks an awase pressed too late.
    void HeroDamaged(const FSoraDamagedEvent& Event);
    // A dojo awase (the chapter-one guard met within the parry window), which
    // a 転 lesson's flank must follow; and the hero's 転 itself.
    void HeroGuarded(const FSoraDefenseEvent& Event);
    // USoraStealth: a stealth beat (or guarded work) opens the zone on the
    // settings' difficulty, and the zone's detection, alarm and found bodies
    // reach the beat as alert_state:alert, ai_event:alarm_raised and
    // ai_event:body_found.
    void OpenStealthZone();
    void CloseStealthZone();
    void StealthDetected(const FSoraStealthDetection& Detection);
    void StealthAlarm(ASoraEnemy* By);
    void StealthBodyFound(ASoraEnemy* Body, ASoraEnemy* Finder);
    // The fieldcraft's events (npc_downed:<id>, signal:hide, look_at:<id> ...)
    // reach the beat as the world's do.
    void FieldcraftEvent(FName Event);
    // Opponents' cues the scripts key: alert_state:<state> barks, a retreat,
    // an alarm run, a takedown, a conscript knocked down or freed.
    void EnemyCue(const FSoraEnemyCueEvent& Event);
    void TickScheduled();
    void HeroRolled(const FSoraMarobashiEvent& Event);
    // The next bout of a lesson duel opens, numbered across the chapter.
    void OpenBout();
    void BeginBeat(int32 Index, int32 Phase, bool bResumed);
    void RetryBeatInPlace();
    void CompleteActiveBeat();
    void TellRegistry(int32 CompletedBeat);
    void FinishChapter();
    void CompleteOptional(int32 Index);
    void Collect(int32 Beat);
    void UpdateObjective();
    void TickBeat(float DeltaSeconds);
    void TickMaai(int32 DeltaMs);
    void ResetMaai();
    FVector MaaiTarget = FVector::ZeroVector;
    FVector MaaiForward = FVector::ForwardVector;
    bool bMaaiMoving = false;
    bool bMaaiObstructionReported = false;
    bool bMaaiTooClose = false;
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
    bool EpilogueObjective(FVector& Location, bool& bInteract) const;
    FString EpilogueObjectiveText(bool bEnglish) const;
    bool InteractEpilogue(ASoraPlayerCharacter& Player);
    void EpilogueLineFinished(const FString& Id);
    void ShowEpilogue();
    // Plays the triggers and shows the HUD prompt an event raises in Beat
    // (the active beat by default) and the chapter's bark pools.
    void Fire(const FString& Event, int32 Beat = INDEX_NONE);
    bool TriggerAllowed(int32 Index) const;
    void Enqueue(const TArray<int32>& Lines, bool bForce, const FString& TriggerMode);
    void RefreshDialogueHold();
    void ClearDialogue();
    bool DialogueLinesDone() const;
    void ShowPrompt(const FString& Event, int32 Beat);
    void Notify(const FString& Japanese, const FString& English, float Seconds);
    // A notice from an NSLOCTEXT line (SoraText::Line or Format).
    void Notify(const SoraText::FLine& Line, float Seconds);
    void Tell(FSoraStoryNotice::EKind Kind, const FString& Japanese, const FString& English,
        const FString& Detail = FString(), const FString& DetailEnglish = FString());
    // Who a beat puts on the field. The AI lane's archetypes
    // (Content/Data/enemies.json) and data-driven bosses (bosses.json) replace
    // these bodies at merge; until then every opponent is the prototype
    // invader, a sparring pupil or the collector.
    ASoraEnemy* SpawnWaveOpponent(FName Type, bool bSparring, int32 Slot, bool bInvulnerable = false);
    ASoraEnemy* SpawnStealthGuard(const FSoraGuard& Guard, int32 GuardIndex, int32 Slot);
    ASoraEnemy* SpawnDuelOpponent(FName Opponent, bool bSparring, int32 Slot);
    ASoraBoss* SpawnBoss(FName Boss, int32 Slot);
    void SpawnCast(bool bKeepPupil);
    void SpawnPending();
    void AddOpponent(ASoraEnemy* Enemy, int32 Wave);
    void SpawnArenaInvader();
    void ClearOpponents();
    int32 LiveWaveOpponents() const;
    void CheckPhase();
    // Plays every phase an opponent has passed since phase Before, in order,
    // and saves at the last when bSave and its beat saves there.
    void EnterPhases(int32 Before, bool bSave);
    // Whether a checkpoint written now restores (the active beat's start, or a
    // phase it saves at).
    bool CanCheckpointHere() const;
    bool HeroAtTask() const;
    bool Contested() const;
    bool Near(const FVector& Location, float Radius) const;
    void ApplyLoadout();
    void BroadcastBeat(bool bStarted, bool bResumed);
    // A telemetry row for the active beat, or for Beat (an optional beat completed beside it).
    void Telemetry(const TCHAR* Event, int32 Beat = INDEX_NONE) const;
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
