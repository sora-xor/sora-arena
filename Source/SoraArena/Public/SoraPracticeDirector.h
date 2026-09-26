#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "ArenaKernelSubsystem.h"
#include "SoraPracticeClock.h"
#include "SoraPracticeDirector.generated.h"
class ACameraActor;
class ASoraCharacterBase;
class ASoraGameMode;
class ASoraPracticeControlPoint;
class ASoraPracticeEntityActor;
class ASoraPracticePayload;
class USceneComponent;

// One line of the practice feed: a death, or an objective moment.
struct FSoraPracticeFeedEntry
{
    enum EKind : uint8 { Kill, Hazard, Fall, Captured, Overtime, Checkpoint, Winner };
    EKind Kind = Kill;
    uint32 Tick = 0;
    // Killer and victim slots (INDEX_NONE when absent); for a kill, the
    // weapon the killer held on that tick. Detail is the team for Captured,
    // the checkpoint index for Checkpoint and the winner kind for Winner
    // (with its team or slot in Actor).
    int32 Actor = INDEX_NONE, Target = INDEX_NONE, WeaponId = INDEX_NONE, Detail = 0;
};

// The final table, copied from the kernel on the terminal tick.
struct FSoraPracticeResults
{
    bool bValid = false;
    uint32 Tick = 0;
    int32 Mode = 0;
    int32 WinnerKind = SoraPractice::WinnerNone, WinnerValue = 0;
    int32 Score[2] = {0, 0};
    int32 ScoreTarget = 0, Checkpoints = 0;
    float PayloadProgress = 0.f, PayloadLength = 0.f;
    TArray<FSoraPracticePlayer> Players;
    uint64 Deposited = 0, Remaining = 0, Earnings = 0;
    // Deposited == Remaining + Earnings, and every participant's bond,
    // reserve and earnings are zero: no XOR moved.
    bool bConserved = false;
};

// Zero-stake deterministic practice on ASoraGameMode. Starts and stops the
// Rust kernel session, steps it on the shared 60 Hz clock with the hero's
// packed input, and presents the kernel's state: every participant (placed
// between the last two 60 Hz states each frame, dressed by side with a
// sashimono), each ability entity, the Control point or the payload, and the
// projectiles. It keeps the kill feed and the results, carries the respawn
// loadout the player chooses while down, runs the spectator camera while the
// player is down or the match is over, and announces each kernel event
// through USoraGameEvents.
UCLASS(ClassGroup=(Sora))
class SORAARENA_API USoraPracticeDirector : public UActorComponent
{
    GENERATED_BODY()
public:
    USoraPracticeDirector();
    virtual void TickComponent(float DeltaSeconds, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    // Checks Config with the kernel and starts a fresh match with it: the
    // game mode switches to practice with Config's class and arena. On
    // failure nothing changes and the reason is in the game mode's notice.
    bool StartPractice(const FSoraPracticeConfig& NewConfig);
    // Restarts Config. Its class and arena follow the game mode's
    // SelectedClass and MapId, so the menu's quick practice keeps working.
    // On failure the menu reopens with the kernel's reason.
    bool Reset();
    // Stops the session and returns the hero to CharacterMovement.
    void Clear();
    // Advances the kernel for one rendered frame of live play.
    void Step(float DeltaSeconds);
    void ResetClock() { Clock.Reset(); }
    FString ObjectiveText() const;
    FString ObjectiveTextEnglish() const;
    // The choice the current or next match is built from.
    FSoraPracticeConfig Config;
    // A long frame slowed practice time instead of skipping input ticks.
    bool bSlowed = false;

    // Respawn loadout: class 0-5 and the kernel loadout index (0 ranged,
    // 1 melee, 2 the admitted special). Chosen at any time and shown while
    // the player is down; the choice rides on the player's input with the
    // LOADOUT bit while down until the kernel reports it pending. False when
    // the kernel would ignore it (a special not admitted, ranged in Melee).
    bool SelectRespawnLoadout(int32 ClassId, int32 LoadoutIndex);
    bool CanSelectLoadout(int32 ClassId, int32 LoadoutIndex) const;
    int32 DesiredClass() const { return RespawnClass; }
    int32 DesiredLoadout() const { return RespawnLoadout; }
    // The weapon a loadout index gives a class, and back; INDEX_NONE if none.
    static int32 LoadoutWeapon(int32 ClassId, int32 LoadoutIndex);
    static int32 LoadoutIndexOf(int32 ClassId, int32 WeaponId);

    // While the player is down the spectator camera follows a living
    // participant (first the one who struck the player down); once the match
    // is over it circles the arena. The player's Fire and Block keys cycle it.
    bool IsSpectating() const { return bSpectating; }
    int32 SpectatedSlot() const { return SpectatorTarget; }
    void CycleSpectator(int32 Direction);
    ACameraActor* SpectatorCamera() const { return Spectator; }

    // Recent deaths and objective moments, oldest first.
    const TArray<FSoraPracticeFeedEntry>& Feed() const { return FeedEntries; }
    const FSoraPracticeResults& Results() const { return FinalResults; }
    // Where a participant is drawn this frame: between the last two kernel
    // states by the practice clock's fraction of a tick.
    FVector PresentedFeet(int32 Slot) const;
    float InterpolationAlpha() const;
    // Team colour in Control and Payload; each slot's own in free-for-all
    // and Melee. The player's side carries the SORA mon.
    FLinearColor ParticipantColor(int32 Slot) const;
    // A shot's tracer: its shooter's colour.
    FLinearColor TracerColor(int32 Slot) const;
    // The player holds Scoreboard during a live match.
    bool ShowsScoreboard() const;
    bool IsSoraSide(int32 Slot) const;
    bool UsesAlienBody(int32 Slot) const;
    // The practice actors, for the HUD and automation.
    const TMap<uint32, TObjectPtr<ASoraPracticeEntityActor>>& EntityActors() const { return Entities; }
    ASoraPracticeControlPoint* ControlPoint() const { return ControlActor; }
    ASoraPracticePayload* Payload() const { return PayloadActor; }
    AActor* ModeDressing() const { return Dressing; }
    ASoraCharacterBase* Participant(int32 Slot) const;
    int32 ParticipantCount() const { return Pawns.Num(); }
private:
    ASoraGameMode& Mode() const;
    void BuildModeDressing();
    void UpdatePresentation();
    void UpdateEntities();
    void UpdateObjective();
    void PresentEvents();
    void PresentFrame();
    void UpdateSpectator(float DeltaSeconds);
    void PollRespawnInput();
    void CaptureResults();
    void AddFeed(const FSoraPracticeFeedEntry& Entry);
    FSoraPracticeInput PlayerInput();
    FSoraPracticeClock Clock;
    UPROPERTY() TArray<TObjectPtr<ASoraCharacterBase>> Pawns;
    UPROPERTY() TMap<uint32, TObjectPtr<AActor>> ProjectileActors;
    UPROPERTY() TMap<uint32, TObjectPtr<ASoraPracticeEntityActor>> Entities;
    UPROPERTY() TObjectPtr<ASoraPracticeControlPoint> ControlActor;
    UPROPERTY() TObjectPtr<ASoraPracticePayload> PayloadActor;
    UPROPERTY() TObjectPtr<AActor> Dressing;
    UPROPERTY() TObjectPtr<ACameraActor> Spectator;
    // Every component of the hero's own sashimono, which only others see.
    UPROPERTY() TArray<TObjectPtr<USceneComponent>> HeroBanner;
    // The last two kernel states of every participant, projectile and payload.
    TArray<FSoraPracticePlayer> Previous, Current;
    TMap<uint32, FVector> ProjectilePrevious, ProjectileCurrent;
    FVector PayloadPrevious = FVector::ZeroVector, PayloadCurrent = FVector::ZeroVector;
    TArray<FSoraPracticeFeedEntry> FeedEntries;
    FSoraPracticeResults FinalResults;
    int32 RespawnClass = 0, RespawnLoadout = 0;
    // The respawn-choice actions held at the last poll, one bit each.
    uint32 HeldActions = 0;
    bool bRespawnChoiceMade = false;
    bool bSpectating = false;
    int32 SpectatorTarget = INDEX_NONE;
    float SpectatorOrbit = 0.f;
    int32 LastKiller = INDEX_NONE;
};
