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

UENUM()
enum class ESoraBossPhase : uint8
{
    Arrived,
    Windup,
    Strike,
    Recovery,
    Defeated,
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
};

DECLARE_MULTICAST_DELEGATE_OneParam(FSoraWeaponFiredSignature, const FSoraWeaponFiredEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraMeleeCommittedSignature, const FSoraMeleeCommittedEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraStrikeResolvedSignature, const FSoraStrikeResolvedEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraDefenseSignature, const FSoraDefenseEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraDamagedSignature, const FSoraDamagedEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraDiedSignature, const FSoraDiedEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraDetonatedSignature, const FSoraDetonatedEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraSiteRestoredSignature, const FSoraSiteRestoredEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraChapterSignature, const FSoraChapterEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraBossPhaseSignature, const FSoraBossPhaseEvent&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraBeatSignature, const FSoraBeatEvent&);
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
    FSoraDamagedSignature OnDamaged;
    FSoraDiedSignature OnDied;
    FSoraDetonatedSignature OnDetonated;
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

protected:
    virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
};
