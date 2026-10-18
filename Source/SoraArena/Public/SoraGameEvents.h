#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "SoraGameEvents.generated.h"

struct FSoraPracticeEvent;

// How a weapon discharge travels. Arrows and shells are projectiles; a
// collector's debt beam is a hitscan line from a boss rather than a weapon.
UENUM()
enum class ESoraShotKind : uint8
{
    Hitscan,
    Shell,
    Arrow,
    Beam,
};

// A boss's or rival duellist's moments (ASoraBoss, Content/Data/bosses.json).
// Windup, Strike and Recovery name the attack in Detail and share its Serial;
// a Windup carries the attack's voice telegraph in Line. PhaseChanged names
// the new pattern table, Staggered, Countered (a parry's special answer) and
// Event name what happened (shield_broken, barrier_broken, mantle_down,
// weakpoint_destroyed, mill_seal, deflected, missed, reload, marobashi, ...), and
// Defeated names the defeat (kill, disarm, capture, destroy_weakpoints, muto_dori).
UENUM()
enum class ESoraBossPhase : uint8
{
    Arrived,
    Windup,
    Strike,
    Recovery,
    Defeated,
    PhaseChanged,
    Staggered,
    Countered,
    Event,
};

// WeaponId is a catalog weapon, or INDEX_NONE for an opponent's fixed attack.
USTRUCT()
struct FSoraWeaponFiredEvent
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Shooter = nullptr;
    UPROPERTY() int32 WeaponId = INDEX_NONE;
    UPROPERTY() ESoraShotKind Kind = ESoraShotKind::Hitscan;
    UPROPERTY() FVector Origin = FVector::ZeroVector;
    UPROPERTY() FVector Direction = FVector::ForwardVector;
    // Hitscan impact or range end; a projectile's launch point.
    UPROPERTY() FVector End = FVector::ZeroVector;
};

USTRUCT()
struct FSoraMeleeCommittedEvent
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Attacker = nullptr;
    UPROPERTY() int32 WeaponId = INDEX_NONE;
    UPROPERTY() FVector Direction = FVector::ForwardVector;
    // Zero for a swing that resolves in the same frame.
    UPROPERTY() float WindupSeconds = 0.f;
};

USTRUCT()
struct FSoraStrikeResolvedEvent
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Attacker = nullptr;
    UPROPERTY() TObjectPtr<AActor> Target = nullptr;
    UPROPERTY() int32 WeaponId = INDEX_NONE;
    UPROPERTY() float Damage = 0.f;
    UPROPERTY() bool bHit = false;
};

// Shared by Guarded and Parried. Damage is what still reached the defender.
USTRUCT()
struct FSoraDefenseEvent
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Defender = nullptr;
    UPROPERTY() TObjectPtr<AActor> Attacker = nullptr;
    UPROPERTY() int32 HeldMs = 0;
    UPROPERTY() float Damage = 0.f;
    // A chapter-one sparring block rather than a live blade.
    UPROPERTY() bool bDojo = false;
};

// 転 (marobashi): the hero rolled to an opponent's flank, after an awase on
// it or out of a boss blow's line in its last stretch.
USTRUCT()
struct FSoraMarobashiEvent
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Hero = nullptr;
    UPROPERTY() TObjectPtr<AActor> Opponent = nullptr;
    UPROPERTY() bool bAfterAwase = false;
};
USTRUCT()
struct FSoraDamagedEvent
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Victim = nullptr;
    UPROPERTY() TObjectPtr<AActor> Causer = nullptr;
    UPROPERTY() float Amount = 0.f;
    UPROPERTY() float HealthAfter = 0.f;
};

USTRUCT()
struct FSoraDiedEvent
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Victim = nullptr;
    UPROPERTY() TObjectPtr<AActor> Killer = nullptr;
    // A sparring pupil yielding or the hero losing a dojo bout; nobody dies.
    UPROPERTY() bool bSparring = false;
};

USTRUCT()
struct FSoraDetonatedEvent
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Instigator = nullptr;
    UPROPERTY() FVector Location = FVector::ZeroVector;
    UPROPERTY() float Radius = 0.f;
    UPROPERTY() float Damage = 0.f;
};

// What an opponent does that presentation answers: barks, captions,
// telegraph sounds and music. Detail is the attack's cue from
// Content/Data/enemies.json for AttackWindup, and the new state for
// AlertState (unaware, suspicious, alert, search, combat, retreat).
UENUM()
enum class ESoraEnemyCue : uint8
{
    AlertState,
    AttackWindup,
    Staggered,
    ShieldTurned,
    BarrierBroken,
    Alarm,
    // A debt-bound conscript knocked down, freed by a cut collar, or back on its feet.
    Subdued,
    Freed,
    Risen,
    // A rear takedown's hilt strike (当て身) put the opponent out.
    KnockedOut,
    // A guard found a body; Detail is unconscious, subdued or dead.
    BodyFound,
};

USTRUCT()
struct FSoraEnemyCueEvent
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Enemy = nullptr;
    UPROPERTY() FName Archetype;
    UPROPERTY() ESoraEnemyCue Cue = ESoraEnemyCue::AlertState;
    UPROPERTY() FName Detail;
};

USTRUCT()
struct FSoraSiteRestoredEvent
{
    GENERATED_BODY()
    UPROPERTY() int32 ChapterId = 0;
    UPROPERTY() int32 SiteIndex = 0;
    UPROPERTY() FString Kind;
    UPROPERTY() bool bCampaign = true;
};

USTRUCT()
struct FSoraChapterEvent
{
    GENERATED_BODY()
    UPROPERTY() int32 ChapterId = 0;
    // Started from a saved checkpoint rather than the chapter opening.
    UPROPERTY() bool bResumed = false;
    UPROPERTY() bool bLiberated = false;
};

// What the front end just did, for its sound: focus moved, a row pressed or a
// commitment confirmed, back, a refused press, an option or slider stepped,
// and the pause menu opened or closed over play.
UENUM()
enum class ESoraUISound : uint8
{
    Hover,
    Click,
    Confirm,
    Back,
    Error,
    Option,
    Slider,
    MenuOpen,
    MenuClose,
};

// A campaign beat of catalog schema 4 (Content/Data/campaign/chapter_0N.json).
USTRUCT()
struct FSoraBeatEvent
{
    GENERATED_BODY()
    UPROPERTY() int32 ChapterId = 0;
    UPROPERTY() int32 BeatIndex = 0;
    UPROPERTY() FString BeatId;
    // Started from a saved checkpoint, and at which boss or duel phase.
    UPROPERTY() bool bResumed = false;
    UPROPERTY() int32 Phase = 0;
    UPROPERTY() bool bOptional = false;
};

USTRUCT()
struct FSoraBossPhaseEvent
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Boss = nullptr;
    UPROPERTY() ESoraBossPhase Phase = ESoraBossPhase::Arrived;
    UPROPERTY() bool bBeam = false;
    UPROPERTY() float HealthFraction = 1.f;
    // The boss's id in bosses.json, and its pattern phase (0-based).
    UPROPERTY() FName BossId;
    UPROPERTY() int32 PhaseIndex = 0;
    // The attack, pattern table, event or defeat (see ESoraBossPhase).
    UPROPERTY() FName Detail;
    // A chapter script's line id: the captioned voice telegraph or bark.
    UPROPERTY() FName Line;
    // One attack's windup, strikes and recovery share a serial.
    UPROPERTY() int32 Serial = 0;
    // The windup this attack was given, after difficulty.
    UPROPERTY() int32 WindupMs = 0;
};

DECLARE_MULTICAST_DELEGATE_OneParam(FSoraWeaponFiredSignature, const FSoraWeaponFiredEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraMeleeCommittedSignature, const FSoraMeleeCommittedEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraStrikeResolvedSignature, const FSoraStrikeResolvedEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraDefenseSignature, const FSoraDefenseEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraMarobashiSignature, const FSoraMarobashiEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraDamagedSignature, const FSoraDamagedEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraDiedSignature, const FSoraDiedEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraDetonatedSignature, const FSoraDetonatedEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraEnemyCueSignature, const FSoraEnemyCueEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraSiteRestoredSignature, const FSoraSiteRestoredEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraChapterSignature, const FSoraChapterEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraBossPhaseSignature, const FSoraBossPhaseEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraBeatSignature, const FSoraBeatEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraUISoundSignature, ESoraUISound);
// One deterministic-practice event from the Rust kernel and the tick it ended.
DECLARE_MULTICAST_DELEGATE_TwoParams(FSoraKernelEventSignature, const FSoraPracticeEvent&, uint32);

/**
 * Gameplay announcements for presentation systems. Audio, effects, telemetry
 * and dialogue subscribe here instead of editing gameplay code. Listeners run
 * synchronously inside the gameplay call and must not change combat state.
 */
UCLASS()
class SORAARENA_API USoraGameEvents : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    static USoraGameEvents* Get(const UObject* WorldContext);

    FSoraWeaponFiredSignature OnWeaponFired;
    FSoraMeleeCommittedSignature OnMeleeCommitted;
    FSoraStrikeResolvedSignature OnStrikeResolved;
    FSoraDefenseSignature OnGuarded;
    FSoraDefenseSignature OnParried;
    FSoraMarobashiSignature OnMarobashi;
    FSoraDamagedSignature OnDamaged;
    FSoraDiedSignature OnDied;
    FSoraDetonatedSignature OnDetonated;
    FSoraEnemyCueSignature OnEnemyCue;
    FSoraSiteRestoredSignature OnSiteRestored;
    FSoraChapterSignature OnChapterStarted;
    FSoraChapterSignature OnChapterCompleted;
    FSoraBossPhaseSignature OnBossPhase;
    // Beat started (fresh, resumed, or a later boss or duel phase saved),
    // completed, or failed when the hero fell during it.
    FSoraBeatSignature OnBeatStarted;
    FSoraBeatSignature OnBeatCompleted;
    FSoraBeatSignature OnBeatFailed;
    FSoraKernelEventSignature OnKernelEvent;
    // USoraFrontEnd's screens, keys and clicks.
    FSoraUISoundSignature OnUISound;

protected:
    virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
};
