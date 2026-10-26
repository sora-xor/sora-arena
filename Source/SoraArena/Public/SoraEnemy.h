#pragma once
#include "CoreMinimal.h"
#include "SoraCharacterBase.h"
#include "SoraCombatRules.h"
#include "SoraDojoRules.h"
#include "SoraFieldcraftRules.h"
#include "SoraStealthRules.h"
#include "SoraHorseShellRules.h"
#include "SoraLandingDroneRules.h"
#include "SoraMillisecondClock.h"
#include "SoraEnemy.generated.h"
enum class ESoraEnemyCue : uint8;
class ASoraBoss;
class ASoraProjectile;
class USpotLightComponent;
class USoraCampaignDirector;
struct FSoraEnemyArchetype;
struct FSoraEnemyAttack;
struct FSoraEnemyVariant;
struct FSoraPatrolRoute;

// What a chapter's beat may change about one spawned opponent.
struct FSoraEnemyTuning
{
    // One of the archetype's variants (Content/Data/enemies.json), or none.
    FName Variant;
    // Zero keeps the archetype's (or variant's) value.
    int32 Health = 0;
    // Zero keeps the archetype's hold; chapter 07's ridge specifies 1.2 s.
    int32 NetRootMs = 0;
    // Chapter 03's landing: mark, descend, net and a low wakizashi opening.
    bool bLandingDrone = false;
    bool bLandingCanalSearchlight = false;
    int32 SightCm = 0;
    int32 ViewDegrees = 0;
    // Negative keeps the archetype's value; a zero hearing is deaf.
    int32 DarkSightCm = -1;
    int32 HearingCm = -1;
    // How readily it grows suspicious, x1000 of the reference; zero keeps the archetype's.
    int32 SuspicionPermille = 0;
    // At a post: the arc it sweeps and the ms a sweep takes (0: the brain's
    // own look about), or how often it turns about (0: never).
    int32 ScanDegrees = 0;
    int32 ScanMs = 0;
    int32 TurnMs = 0;
    // A scripted opponent that takes no damage (ch08's sweep-only walkers).
    bool bInvulnerable = false;
};

// A campaign or training-arena opponent built from an archetype in
// Content/Data/enemies.json (story bible §7), or a chapter-one sparring pupil.
// The pawn owns its attacks (commit, telegraph, windup, strike and recovery),
// its defenses (a tower shield, a personal barrier, a weak rear) and its
// stagger; ASoraEnemyController decides from its own tick where it moves and
// when an attack may start. A debt-bound conscript is never killed: a lethal
// blow knocks it down, and cutting its collar frees it (SoraCombatRules). In a
// stealth zone (USoraStealth) a guard can be taken down from behind, and a
// guard knocked out or killed stays down as a body for the others to find.
UCLASS()
class SORAARENA_API ASoraEnemy : public ASoraCharacterBase
{
    GENERATED_BODY()
public:
    ASoraEnemy(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    // The inventory drone's integrated net outlet, in actual world space.
    FVector NetMuzzle() const;
    FVector SenseOrigin() const { return Eye(); }
    // Makes this pawn an opponent of Archetype. Slot is its place in the spawn
    // order; fixed patterns (misses, peeks, flank sides) are offset by it so a
    // group never acts in unison. Without a patrol it belongs to a combat wave
    // and hunts the hero; with one it starts unaware on that route. Returns false
    // when catalog data or required body assets cannot be admitted; callers must
    // discard the failed pawn (SpawnArchetype handles that cleanup).
    bool InitArchetype(FName Archetype, int32 Slot, const FSoraPatrolRoute* Patrol = nullptr, const FSoraEnemyTuning* Tuning = nullptr);
    // Spawns and initializes an opponent, or returns null when it cannot.
    static ASoraEnemy* SpawnArchetype(UWorld& World, FName Archetype, int32 Slot, const FVector& Location, const FRotator& Rotation,
        const FSoraPatrolRoute* Patrol = nullptr, const FSoraEnemyTuning* Tuning = nullptr);
    // The combat wave's mix by slot: blade retainers on slots 0, 6, 12 and 18,
    // rifle enforcers on every other slot.
    static FName WaveArchetype(int32 Slot);
    // InitArchetype(WaveArchetype(Slot)); an opponent that cannot be built is destroyed.
    void InitInvader(int32 Slot, const FSoraPatrolRoute* Patrol = nullptr);
    static ASoraEnemy* SpawnInvader(UWorld& World, int32 Slot, const FVector& Location, const FRotator& Rotation,
        const FSoraPatrolRoute* Patrol = nullptr);
    // Nonlethal sparring with the bokken; a defeated pupil yields.
    void InitDojoPupil(int32 Slot, const SoraDojoRules::FPupilTiming& Timing = {});
    void SuspendDojoAction();
    virtual bool IsEnemy() const override { return !IsFreed(); }
    virtual bool IsSparring() const override { return bDojoPupil; }
    virtual bool AdmitDamage(float& Damage, FSoraHit& Hit, AActor* Causer) override;
    virtual void OnDefeated(AActor* Causer) override;
    // Null for sparring pupils and the collector, which keep their own drills.
    const FSoraEnemyArchetype* Archetype() const { return Kind; }
    FName ArchetypeId() const;
    FName VariantId() const { return Variant; }
    const SoraStealthRules::FPerception& Perception() const { return Senses; }
    // How it watches from a post (FSoraEnemyTuning's scan and turn).
    int32 PostScanDegrees() const { return ScanDegrees; }
    int32 PostScanMs() const { return ScanMs; }
    int32 PostTurnMs() const { return TurnMs; }
    bool IsBladeRetainer() const;
    bool IsDojoPupil() const { return bDojoPupil; }
    bool IsFlying() const;
    int32 EnemySlot() const { return EnemyIndex; }
    // Aimed rounds miss on a fixed pattern (SoraCombatRules::RoundMisses).
    static bool RangedShotMisses(int32 Slot, int32 Shot);
    int32 RangedShotsFired() const { return RangedShots; }
    // The damage of the archetype's attack at Index, or zero.
    int32 AttackDamage(int32 Index) const;
    bool IsPupilWindup() const { return bPupilWindup; }
    // The chapter-one drill ASoraEnemyController runs for a sparring pupil.
    void PupilAttack(ASoraCharacterBase& Target, float Distance);

    // Attacks. TryAttack commits the first of the archetype's attacks whose
    // range holds Distance and whose cooldown has passed, when none is under
    // way; the pawn's own tick then winds it up, strikes and recovers.
    void DisruptWindAim(int32 Milliseconds);
    bool TryAttack(ASoraCharacterBase& Target, float Distance);
    void SetCampaignWithdrawal(bool Active);
    bool IsCampaignWithdrawing() const { return bCampaignWithdrawing; }
    // Only the registered pod-B grenadier receives this encounter binding.
    void BindHorseShell(USoraCampaignDirector& Director,uint64 Generation);
    bool HasHorseShellAssignment() const { return bHorseShellBound; }
    bool TryHorseShell(AActor& Target,const FVector& Landing);
    void CancelHorseShell() { CancelAttack(); }
    const SoraHorseShellRules::FState& HorseShellState() const { return HorseShellClock; }
    AActor* HorseShellWarning() const { return ShellWarning.Get(); }
    bool HasLandingDroneAssignment() const { return bLandingDrone; }
    int32 LandingSearchlightAt(const FVector& Location) const;
    bool OwnsLandingDroneMotion() const { return bLandingDrone&&LandingDroneClock.Stage!=SoraLandingDroneRules::EStage::Idle; }
    bool IsLandingDroneLow() const;
    const SoraLandingDroneRules::FState& LandingDroneState() const { return LandingDroneClock; }
    AActor* LandingDroneWarning() const { return LandingWarning.Get(); }
    bool IsAttacking() const { return Phase != EPhase::Idle; }
    bool IsWindingUp() const { return Phase == EPhase::Windup; }
    // Winding up or firing; collateral also holds still during its exposed
    // recovery, so the hero can maintain contact with the core.
    bool IsCommitted() const { return Phase == EPhase::Windup || Phase == EPhase::Firing ||
        ((bCollateralConstruct || bLandingDrone) && Phase == EPhase::Recovery); }
    const FSoraEnemyAttack* CurrentAttack() const;
    float WindupProgress() const;
    // The farthest reach of its melee attacks, for footwork.
    float MeleeReachCm() const;
    // Shots since the last change of position (a marksman relocates).
    int32 ShotsSinceMove() const { return ShotsSinceRelocation; }
    void Relocated() { ShotsSinceRelocation = 0; }

    // Stagger: the windup drops and the opponent cannot act; hits deal more.
    bool IsStaggered() const;
    virtual void Stagger(int32 Milliseconds);
    // A parry met its blow (SoraDefense): staggered for StaggerMs.
    virtual void Parried(int32 StaggerMs) { Stagger(StaggerMs); }
    // 転 (SoraDefense::Marobashi): the hero rolled to its flank. For
    // Milliseconds it cannot turn after him or start an attack.
    virtual void Outflanked(int32 Milliseconds);
    bool IsTurnLocked() const;
    // 無刀取り took this opponent's blade (SoraDefense). True when its fight
    // allows it; only a boss or rival duellist with that finisher does.
    virtual bool Disarm(AActor* By) { return false; }
    // An add a boss called in: its defeat is the boss's business, never a
    // beat's defeat count.
    void SetSummoner(ASoraBoss* Boss);
    ASoraBoss* Summoner() const;
    // Chapter 08 summit adds only. No mutation of the shared loom archetype.
    void EnableCollateralConstruct();
    void EnableClimbSentry() { bClimbSentry=true; }
    bool IsCollateralConstruct() const { return bCollateralConstruct; }
    bool IsConstructCoreOpen() const;
    FVector ConstructCorePoint() const;
    bool CanReachConstructCore(const ASoraCharacterBase& By) const;
    bool HasReleasedGoods() const { return bGoodsReleased; }
    bool IsShieldOpen() const;
    // A tower shield on its arm (enemies.json shield).
    bool HasShield() const;
    int32 BarrierHealth() const { return BarrierMilli / 1000; }
    // The kusarigama's weighted chain caught it (SoraFieldcraftRules::Snare):
    // a blade bound, a shield's rim pulled aside, a drone dragged down.
    void Snared(SoraFieldcraftRules::ESnare Kind, AActor* By);

    // 活人剣. A knocked-down conscript's collar can be cut within its window;
    // SoraDamage::Resolve calls Subdue for a blow that would kill it.
    bool IsNonlethal() const;
    bool IsSubdued() const { return Conscript == SoraCombatRules::EConscript::Down; }
    bool IsFreed() const { return Conscript == SoraCombatRules::EConscript::Freed; }
    void Subdue(AActor* Causer);
    bool CanCutSeal() const;
    // Frees a knocked-down conscript; it never fights again. False outside the window.
    bool CutSeal(AActor* By);
    // How long Interact is held to cut a collar, from the archetype.
    int32 SealCutHoldMs() const;

    // Stealth (USoraStealth). A body is an opponent down on the floor:
    // knocked out, knocked down or dead, and left where it fell for the other
    // guards to find. A combat wave's dead clear away instead.
    bool IsBody() const;
    bool IsUnconscious() const { return bUnconscious; }
    // 当て身: a rear takedown's hilt strike. Out for the rest of the beat; it
    // counts as defeated and leaves a body.
    void KnockOut(AActor* By);
    // A rear takedown may start on it: its archetype allows one and it can still fight.
    bool CanBeTakenDown() const;
    // Held by a takedown: it neither thinks, moves nor strikes.
    void Seize(bool bHeld);
    bool IsSeized() const { return bSeized; }
protected:
    virtual void TickPlay(float DeltaSeconds) override;
    virtual void HaltActions() override;
    virtual bool UsesAlienBody() const override;
    virtual bool UsesHeldWeapon() const override { return !IsFlying(); }
    virtual bool BuildSpecialBody() override;
    virtual bool WieldsDojoBokken() const override { return bDojoPupil; }
    // An opponent outside the archetype catalog (the collector) with its own drill.
    void InitScripted(int32 Slot);
    float Now() const;
    bool bDojoPupil = false;
    int32 EnemyIndex = 0;
private:
    UPROPERTY() TObjectPtr<UStaticMeshComponent> DroneBody;
    UPROPERTY() TObjectPtr<USpotLightComponent> LandingSearchlight;
    bool bLandingCanalSearchlight=false;
    void DisableLandingSearchlight();
    void ConfigureBodyCollision();
    const TArray<FSoraEnemyAttack>& AttackSet() const;
    void ResetConstruct();
    bool AdmitConstructDamage(float& Damage, FSoraHit& Hit);
    void ReleaseConstructGoods();
    void TickConstruct(float DeltaSeconds);
    void ConstructSlam(const FSoraEnemyAttack& Attack);
    bool bCollateralConstruct = false;
    bool bClimbSentry=false;
    bool bConstructSlamReleased = false;
    bool bGoodsReleased = false;
    bool bCoreWasOpen = false;
    float GoodsReleaseSeconds = 0.f;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> ConstructCore;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> ConstructGoods;
    TArray<FVector> GoodsAssembled;
    TArray<FVector> GoodsReleaseFrom;
    TArray<FVector> GoodsReleaseTo;
    enum class EPhase : uint8 { Idle, Windup, Firing, Recovery };
    void Commit(int32 Index, ASoraCharacterBase& Target);
    void AdvanceAttack();
    void Release(const FSoraEnemyAttack& Attack, ASoraCharacterBase& Target);
    void Recover(const FSoraEnemyAttack& Attack);
    void CancelAttack();
    void StrikeMelee(const FSoraEnemyAttack& Attack, ASoraCharacterBase& Target);
    void FireRound(const FSoraEnemyAttack& Attack, ASoraCharacterBase& Target, bool bPattern);
    void Lob(const FSoraEnemyAttack& Attack, ASoraCharacterBase& Target);
    ASoraProjectile* LaunchShell(const FSoraEnemyAttack& Attack,const FVector& Landing,
        USoraCampaignDirector* Director=nullptr,uint64 Generation=0,AActor* Warning=nullptr);
    void TickHorseShell();
    bool BeginLandingDrone(int32 WindupMs);
    void TickLandingDrone();
    void ClearLandingWarning();
    bool bLandingDrone=false, bLandingFloorKnown=false;
    SoraLandingDroneRules::FState LandingDroneClock;
    FSoraMillisecondClock LandingDroneMilliseconds;
    double LandingDroneLastWorldSeconds=0;
    FVector LandingHome=FVector::ZeroVector, LandingLow=FVector::ZeroVector;
    TWeakObjectPtr<AActor> LandingWarning;
    void AdvanceHorseShellClock();
    bool bHorseShellBound=false;
    bool bCampaignWithdrawing=false;
    TWeakObjectPtr<USoraCampaignDirector> HorseShellDirector;
    uint64 HorseShellGeneration=0;
    SoraHorseShellRules::FState HorseShellClock;
    FSoraMillisecondClock HorseShellMilliseconds;
    double HorseShellLastWorldSeconds=0;
    TWeakObjectPtr<AActor> HorseShellTarget;
    TWeakObjectPtr<AActor> ShellWarning;
    void FireBeam(const FSoraEnemyAttack& Attack, ASoraCharacterBase& Target);
    void CastNet(const FSoraEnemyAttack& Attack, ASoraCharacterBase& Target);
    void Telegraph(const FSoraEnemyAttack& Attack, float Life);
    void Announce(ESoraEnemyCue Cue, FName Detail) const;
    void Rise();
    // Down where it fell and passed over. A body that stays down settles onto
    // the floor, stops blocking sight and is left for the guards to find.
    void LieDown(bool bBody);
    FVector Eye() const;
    FVector Feet(const ASoraCharacterBase& Body) const;
    const FSoraEnemyArchetype* Kind = nullptr;
    FName Variant;
    const FSoraEnemyVariant* VariantData = nullptr;
    SoraStealthRules::FPerception Senses = SoraStealthRules::Standard();
    int32 ScanDegrees = 0;
    int32 ScanMs = 0;
    int32 TurnMs = 0;
    bool bInvulnerable = false;
    TWeakObjectPtr<ASoraBoss> SummonedBy;
    // The attack under way.
    EPhase Phase = EPhase::Idle;
    int32 AttackIndex = INDEX_NONE;
    TWeakObjectPtr<ASoraCharacterBase> AttackTarget;
    float PhaseStartedAt = 0.f;
    float PhaseEndsAt = 0.f;
    int32 RoundsLeft = 0;
    float NextRoundAt = 0.f;
    float NextLaserAt = 0.f;
    FVector LockedDirection = FVector::ForwardVector;
    FVector LockedPoint = FVector::ZeroVector;
    float NextAttackAt = 0.f;
    int32 NetRootOverrideMs = 0;
    TArray<float> AttackReadyAt;
    int32 RangedShots = 0;
    int32 ShotsSinceRelocation = 0;
    // Defenses.
    float StaggerUntil = -1.f;
    float TurnLockedUntil = -1.f;
    float StrikeStaggerImmuneUntil = -1.f;
    float ShieldOpenUntil = -1.f;
    int32 BarrierMilli = 0;
    int32 BarrierMaxMilli = 0;
    // The barrier as the last hit left it; it regenerates from there.
    int32 BarrierAtLastHitMilli = 0;
    float LastHitAt = -1000.f;
    // Nonlethal state.
    SoraCombatRules::EConscript Conscript = SoraCombatRules::EConscript::Standing;
    float DownAt = 0.f;
    bool bUnconscious = false;
    bool bSeized = false;
    // The sparring pupil's drill.
    SoraDojoRules::FPupilTiming PupilTiming;
    bool bPupilWindup = false;
    float PupilWindupEndsAt = 0.f;
    FVector PupilLockedDirection = FVector::ForwardVector;
    float NextPupilStrike = 0.f;
};
