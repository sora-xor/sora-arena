#pragma once
#include "CoreMinimal.h"
#include "SoraBossRules.h"
#include "SoraEnemy.h"
#include "SoraGameEvents.h"
#include "SoraBoss.generated.h"
class ASoraBossHazard;
class UStaticMeshComponent;
struct FSoraBossAttack;
struct FSoraBossData;
struct FSoraBossPhase;

// How a beat sets a boss or duel up.
struct FSoraBossSetup
{
    SoraBossRules::EDifficulty Difficulty = SoraBossRules::EDifficulty::Normal;
    // The arena: its centre (the spawn point when unset) and radius
    // (bosses.json's when zero). The boss never leaves it; a locked arena
    // also keeps the hero in until the fight ends.
    bool bHasArenaCenter = false;
    FVector ArenaCenter = FVector::ZeroVector;
    int32 ArenaRadiusCm = 0;
    bool bLockArena = false;
    // A phase checkpoint: the boss returns at that phase's start.
    int32 Phase = 0;
};

// Where the boss wants to go and look this frame; its controller walks it.
struct FSoraBossIntent
{
    bool bMove = false;
    FVector Goal = FVector::ZeroVector;
    float AcceptanceCm = 50.f;
    bool bFace = false;
    FVector Facing = FVector::ForwardVector;
    float TurnDegreesPerSecond = 180.f;
};

// A campaign boss or rival duellist built from Content/Data/bosses.json
// (story bible §8). The pawn runs its pattern tables: each phase's attacks in
// a fixed sequence (on a fencer's metronome, a gunslinger's cadence or fixed
// gaps), by priority of reach and cooldown, or by a duellist's weighted
// habits turned into a fixed rotation; attacks on their own clocks (a sonar
// pulse, a channel gate); adds at health thresholds. Every attack is
// telegraphed (a coloured windup, a caption and a voice line) for at least
// its windup, scaled by difficulty, before it can hurt, and every strike is
// announced with its attack's serial. Health phases change at their
// thresholds, which no single blow can pass, with an invulnerable
// transition. It carries its fight's defenses: a frontal tower shield that
// grenades break, a regenerating barrier that a reload drops, a coolant
// mantle, wards that intercept ranged fire, an idle fencer's deflection,
// weak points that its own acts expose, a floor that only mutō-dori passes
// and invulnerability while its adds live. A parry staggers it (or answers
// with a measure reset or a snapped cable); a stagger drops its windup. A
// blind boss acts on what it hears. It locks its arena until it falls, and
// is killed, disarmed, captured or broken as its fight says. It never
// enters the multiplayer kernel, and nothing it does is random.
UCLASS()
class SORAARENA_API ASoraBoss : public ASoraEnemy
{
    GENERATED_BODY()
public:
    ASoraBoss(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    // Spawns and builds the boss or duel BossId, or returns null (with an
    // error) when bosses.json or the id is unknown.
    static ASoraBoss* SpawnBoss(UWorld& World, FName BossId, int32 Slot, const FVector& Location, const FRotator& Rotation,
        const FSoraBossSetup& Setup = FSoraBossSetup());
    bool InitBoss(FName BossId, int32 Slot, const FSoraBossSetup& Setup = FSoraBossSetup());
    // An arena anchor of Kind (heat_slot, wet_slot, channel, cover, slide,
    // beam_fall) from the level; zone attacks that need anchors wait for them.
    void AddAnchor(FName Kind, const FVector& Location);
    // A points duel's score: the hero's lead picks the rival's habits.
    void SetDuelScore(int32 HeroPoints, int32 RivalPoints);
    // The arena strikes the boss (a crane's cargo net): stunned for
    // Milliseconds and taking TakenPermille of every hit meanwhile.
    void Stun(int32 Milliseconds, int32 TakenPermille);
    // Commits AttackId as the next attack whatever the pattern would choose
    // (scripted beats and tests). False when unknown, defeated or busy.
    bool ForceAttack(FName AttackId);
    // No pattern attack starts for Milliseconds (a cinematic's hold).
    void Hold(int32 Milliseconds);

    const FSoraBossData* Data() const { return Info; }
    FName BossId() const;
    SoraBossRules::EDifficulty Difficulty() const { return Setup.Difficulty; }
    int32 PhaseIndex() const { return PhaseNow; }
    const FSoraBossPhase* CurrentPhase() const;
    int32 HealthPermille() const;
    // The attack under way and its serial (INDEX_NONE and zero when idle).
    const FSoraBossAttack* BossAttack() const;
    int32 BossAttackIndex() const { return Run.Attack; }
    int32 AttackSerial() const { return Run.Attack == INDEX_NONE ? 0 : Run.Serial; }
    bool IsBossTelegraphing() const;
    float BossWarningSeconds() const;
    float BossWarningProgress() const;
    bool IsRecovering() const;
    // An attack's timing and reach as this phase and difficulty give them.
    int32 WindupFor(int32 Index) const;
    int32 RecoveryFor(int32 Index) const;
    int32 ActiveFor(int32 Index) const;
    int32 CooldownFor(int32 Index) const;
    int32 ReachFor(int32 Index) const;
    int32 RootFor(int32 Index) const;
    int32 MutoWindowMs() const;
    bool IsInvulnerable() const;
    bool IsStunned() const;
    bool IsShieldUp() const;
    bool IsMantleUp() const;
    bool HasBarrier() const;
    bool IsBarrierOffline() const;
    int32 BarrierPoints() const;
    bool IsWeakPointOpen(int32 Index) const;
    int32 WeakPointHealth(int32 Index) const;
    FVector WeakPointLocation(int32 Index) const;
    UPrimitiveComponent* WeakPointPart(int32 Index) const;
    int32 Seals() const { return SealCount; }
    int32 LiveAdds(int32 Group = INDEX_NONE) const;
    int32 LiveWards() const;
    const TArray<TObjectPtr<ASoraBossHazard>>& Wards() const { return WardActors; }
    int32 LiveZones(int32 Index = INDEX_NONE) const;
    FVector ArenaCenter() const { return Center; }
    float ArenaRadius() const { return ArenaRadiusCm; }
    bool IsArenaLocked() const { return LockWalls.Num() > 0; }
    // A blind boss: where it believes the hero is and whether that is fresh.
    bool KnowsHero() const;
    FVector BelievedHeroLocation() const { return KnownAt; }
    bool IsDefeated() const { return bDefeated; }
    FName DefeatDetail() const { return Defeated; }

    // ASoraEnemyController: this frame's movement and, when free, the next attack.
    FSoraBossIntent Drive(ASoraCharacterBase& Target, float DeltaSeconds);
    // What its controller heard since the last tick; Evidence is where it says the hero is.
    void Hear(const FVector& Evidence);
    // Hazards and wards report back.
    void AnnounceStrike(int32 Index, int32 Serial);
    void BreakMantle();
    void WardBroken(ASoraBossHazard& Ward);
    void AddDefeated(ASoraEnemy& Add);

    virtual void Stagger(int32 Milliseconds) override;
    virtual void Parried(int32 StaggerMs) override;
    virtual bool Disarm(AActor* By) override;
    virtual bool AdmitDamage(float& Damage, FSoraHit& Hit, AActor* Causer) override;
    virtual void OnDefeated(AActor* Causer) override;
    virtual bool IsSparring() const override;
protected:
    virtual void TickPlay(float DeltaSeconds) override;
    virtual void HaltActions() override;
    virtual bool UsesAlienBody() const override;
    virtual bool WieldsDojoBokken() const override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
    enum class EStage : uint8 { Idle, Dash, Windup, Hold, Active, Gap, Recovery };
    // One attack from windup to recovery.
    struct FRun
    {
        int32 Attack = INDEX_NONE;
        int32 Serial = 0;
        EStage Stage = EStage::Idle;
        int32 StageStartMs = 0;
        int32 StageEndsMs = 0;
        int32 WindupMs = 0;
        int32 HitsDone = 0;
        int32 RepeatsLeft = 0;
        bool bFromPattern = false;
        bool bParried = false;
        bool bLanded = false;
        FVector LockedDirection = FVector::ForwardVector;
        FVector LockedPoint = FVector::ZeroVector;
        FVector From = FVector::ZeroVector;
        FVector To = FVector::ZeroVector;
        int32 NextVisualMs = 0;
    };
    // An attack on its own clock, beside the pattern.
    struct FSide
    {
        int32 Attack = INDEX_NONE;
        int32 Serial = 0;
        int32 StartMs = 0;
        int32 WindupMs = 0;
        bool bReleased = false;
        bool bTested = false;
        int32 EndsMs = 0;
    };
    // An open window on weak points or the barrier.
    struct FExposure
    {
        int32 Attack = INDEX_NONE;
        int32 Serial = 0;
        int32 UntilMs = 0;
        int32 Damage = 0;
        TArray<int32> Points;
    };
    enum class ETuned : uint8 { Windup, Active, Recovery, Cooldown, Reach, Root };
    int32 NowMs() const;
    const FSoraBossAttack& AttackAt(int32 Index) const;
    int32 Tuned(int32 Index, ETuned Which, int32 Base) const;
    int32 FloorPermille() const;
    void EnterPhase(int32 Next);
    void SyncPhase();
    void RunTimers();
    ASoraCharacterBase* Hero() const;
    FVector TargetPoint(const ASoraCharacterBase& Target) const;
    bool InReach(int32 Index, const ASoraCharacterBase& Target) const;
    bool FacesTarget(int32 Index, const FVector& Point) const;
    bool Eligible(int32 Index, const ASoraCharacterBase& Target) const;
    // The next attack, and whether it is the pattern's own (not a reaction or a finishing blow).
    int32 Choose(const ASoraCharacterBase& Target, bool& bPattern);
    void Commit(int32 Index, ASoraCharacterBase& Target, bool bFromPattern, int32 RepeatsLeft);
    void Advance();
    void Release(ASoraCharacterBase& Target);
    void AfterActive();
    void StrikeBlow(ASoraCharacterBase& Target);
    void StrikeArea(ASoraCharacterBase& Target);
    void StrikeBeam(ASoraCharacterBase& Target, const FVector& Direction);
    void StrikeRound(ASoraCharacterBase& Target);
    void MoveAlong(float Alpha);
    void Land(ASoraCharacterBase& Target);
    void Recover(int32 Milliseconds);
    void Finish();
    void Telegraph(const FSoraBossAttack& Attack, float Life);
    void StartSide(int32 Index);
    void AdvanceSides();
    void PlaceZones(int32 Index, int32 Serial, int32 WindupMs);
    bool ZonePoints(int32 Index, int32 Serial, TArray<FVector>& Points) const;
    void Summon(int32 Group);
    void Expose(int32 Index, int32 Serial);
    void CloseExposure(int32 Index, bool bInterrupted);
    void SpawnWards(int32 Ward);
    void ClearWards();
    void LockArena(bool bLock);
    void BreakShield();
    void Broadcast(ESoraBossPhase What, FName Detail, FName Line = NAME_None, int32 Serial = 0, int32 WindupMs = 0) const;
    FName BarkLine(const FSoraBossAttack& Attack);
    FName EventBark(FName Event);
    int32 WeakPointHit(const FSoraHit& Hit) const;
    bool Intercepted(const FSoraHit& Hit, int32 Damage);
    float StrikeHero(ASoraCharacterBase& Target, int32 Damage, const FSoraHit& Hit, const FVector& Direction);
    void IgnoreOwn(struct FCollisionQueryParams& Query) const;
    void FinishFight(FName Detail);
    FVector Ground(const FVector& Point) const;
    FVector ClampToArena(const FVector& Point) const;

    const FSoraBossData* Info = nullptr;
    FSoraBossSetup Setup;
    int32 PhaseNow = 0;
    bool bPhaseEntered = false;
    int32 PhaseStartedMs = 0;
    // A metronome counts its beats from the phase's first attack.
    int32 BeatOriginMs = -1;
    int32 InvulnerableUntilMs = 0;
    int32 HoldUntilMs = 0;
    int32 NextSerial = 1;
    FRun Run;
    // Pattern.
    int32 Step = 0;
    // The sequence step the last pattern attack came from (a feint's blow shares it).
    int32 StepDone = 0;
    int32 NextStartMs = 0;
    int32 LastStartMs = 0;
    int32 Picked = INDEX_NONE;
    int32 Forced = INDEX_NONE;
    int32 Lead = 0;
    int32 HabitStep = 0;
    SoraBossRules::FWeighted Habits[3] = {};
    TArray<int32> ReadyAtMs;
    TArray<int32> TimedDueMs;
    TArray<bool> SummonDone;
    TArray<bool> OnceDone;
    int32 NextFloorAttackMs = 0;
    TArray<FSide> Sides;
    TArray<FExposure> Exposures;
    // Defenses.
    bool bShieldBroken = false;
    int32 ShieldHits = 0;
    int32 FrontBlocked = 0;
    int32 BarrierNowMilli = 0;
    int32 BarrierAtHitMilli = 0;
    int32 BarrierHitMs = 0;
    int32 MantleDownUntilMs = 0;
    int32 StunUntilMs = 0;
    int32 StunTakenPermille = 1000;
    int32 StrikeImmuneUntilMs = 0;
    int32 NextPushMs = 0;
    TArray<int32> PointHealth;
    TArray<int32> PointOpenUntilMs;
    int32 RotateNext = 0;
    int32 SealCount = 0;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> PointParts;
    UPROPERTY() TArray<TObjectPtr<ASoraBossHazard>> WardActors;
    int32 WardIndex = INDEX_NONE;
    int32 WardRespawnAtMs = 0;
    UPROPERTY() TArray<TObjectPtr<ASoraBossHazard>> Zones;
    UPROPERTY() TArray<TObjectPtr<ASoraEnemy>> Adds;
    TArray<int32> AddGroups;
    TArray<int32> GroupRespawnAtMs;
    TArray<TPair<FName, FVector>> Anchors;
    TMap<FName, int32> BarkReadyMs;
    TSet<FName> BarkedOnce;
    // A blind hunter's belief.
    FVector KnownAt = FVector::ZeroVector;
    int32 KnownAtMs = MIN_int32 / 2;
    // The arena.
    FVector Center = FVector::ZeroVector;
    float ArenaRadiusCm = 0.f;
    UPROPERTY() TArray<TObjectPtr<AActor>> LockWalls;
    bool bDefeated = false;
    bool bTakenByMuto = false;
    FName Defeated;
};
