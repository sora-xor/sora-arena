#pragma once
#include "CoreMinimal.h"
#include "AIController.h"
#include "SoraStealthRules.h"
#include "SoraMillisecondClock.h"
#include "SoraPatrolRules.h"
#include "SoraEnemyController.generated.h"
class ASoraBoss;
class ASoraCharacterBase;
class ASoraEnemy;
class ASoraCampaignLift;
class USoraGameEvents;
struct FSoraDetonatedEvent;
struct FSoraMeleeCommittedEvent;
struct FSoraWeaponFiredEvent;

// A route for an opponent that starts unaware: points walked in order with a
// look-around pause at each, looping or walking back the way it came. A single
// point is a guard post.
USTRUCT()
struct FSoraPatrolRoute
{
    GENERATED_BODY()
    UPROPERTY() TArray<FVector> Points;
    // A second circuit with the same start, used on alternate completed laps.
    // Switching never skips an obstructed station or teleports the guard.
    UPROPERTY() TArray<FVector> AlternatePoints;
    UPROPERTY() bool bPingPong = false;
    UPROPERTY() int32 PauseMs = 1500;
    // Optional ordinary-patrol dwell per waypoint, in active patrol time.
    // A zero entry walks through that corner without a timed desk stop.
    UPROPERTY() TArray<int32> PointPauseMs;
    // Optional scheduled circuit, in active patrol time. Distractions and
    // combat take priority; a blocked station never counts as visited.
    UPROPERTY() int32 PeriodMs = 0;
    UPROPERTY() bool bThreeDimensional = false;
    // Authored flat catwalk segments: validate capsule clearance and floor
    // support locally when the rasterized navmesh disconnects a narrow strip.
    UPROPERTY() bool bSupportedSegments = false;
    // Authored stair legs use the walking capsule's step-up and floor support.
    UPROPERTY() bool bSupportedSteps = false;
    // A verified flight corridor follows each segment with ordinary swept
    // movement, without the free-roaming drone's long sidestep look-ahead.
    UPROPERTY() bool bDirectFlightSegments = false;
    // Short circular flight legs need tighter arrivals than long corridors.
    UPROPERTY() float FlightArrivalCm = 20.f;
    UPROPERTY() FVector PauseFacing=FVector::ZeroVector;
};

// The campaign opponents' brain, run from its own tick before its pawn moves.
// Sparring pupils keep their fixed drill; a boss or rival duellist
// (ASoraBoss) chooses its own attacks from its pattern tables and is walked
// here, hearing through this brain when it is blind. Every other
// opponent runs SoraStealthRules' state machine (unaware, suspicious, alert,
// search, combat, retreat) on what its archetype perceives (Content/Data/
// enemies.json): a view cone with line of sight to the hero's head, chest and
// hips, distance, his stance and a light proxy, and the noise of footsteps
// (walking, sprinting or crouch-walking, on the zone's floors), blades, shots,
// explosions, takedowns and allies' call-outs. A guard (an opponent on a
// patrol or post) obeys the stealth zone (USoraStealth): its vigilance, the
// bodies it may find, the alarm lecterns an auditor runs to and the alarm
// that reaches every guard. It walks the runtime navigation mesh (USoraNavigation) around
// walls and patrols its route. In a fight each archetype keeps its own
// manner: blades, shields, conscripts and automata close to their reach;
// rifles take cover behind the arena's low boxes and peek out to fire, or
// flank by slot; a marksman moves on after its shots; a grenadier keeps its
// distance; a drone holds station in the air; a walker stands and turns; an
// auditor runs and raises the alarm. A staggered opponent does nothing. Every
// choice follows world time, slots and fixed patterns; nothing is random.
UCLASS()
class SORAARENA_API ASoraEnemyController : public AAIController
{
    GENERATED_BODY()
public:
    ASoraEnemyController();
    virtual void Tick(float DeltaSeconds) override;
    // A combat wave: the opponent starts alert, and the invaders' relay keeps
    // telling it where the hero is whenever it cannot see him.
    void BeginHunt();
    // The opponent starts unaware on Route; an empty route guards where it stands.
    void BeginPatrol(const FSoraPatrolRoute& Route);
    // An ally at Caller shouts that the hero is at Where. An auditor's alarm
    // reaches everyone within its alarm radius at full urgency.
    void HearCallout(const FVector& Caller, const FVector& Where, bool bAlarm = false);
    // Straight to alert: a conscript whose collar drags it back up knows where the hero is.
    void Rouse(const FVector& Where);
    // A noise the stealth zone makes heard everywhere at once (a takedown's
    // scuffle), at Loudness (x1000 of the kind's own).
    void HearNoise(SoraStealthRules::ENoise Kind, const FVector& Origin, const FVector& Evidence, const AActor* Source,
        int32 LoudnessPermille = 1000);
    // The zone's alarm: to where it says the hero is, and wary from now on.
    void HearAlarm(const FVector& Where);
    // A body found in the zone: the finder searches around it, the others where they stand.
    void LearnOfBody(const FVector& Where, bool bFinder);
    // A changed object makes a calm guard investigate its position, without
    // exposing the player's position or turning an auditor's alarm on.
    void NoticeTampering(const FVector& Where);
    // A relay sensor's exact evidence impulse. Its first suspicious report
    // does not turn an auditor's ordinary object inspection into an alarm.
    void SensorEvidence(const FVector& Where,int32 SuspicionPermille);
    // A guard's start in a zone that has just opened (SoraStealthRules::Posted).
    void EnterZone(bool bCarriedOver);
    // On a patrol or post rather than in a hunting wave: the stealth zone's guard.
    bool IsGuard() const { return !bHunting; }
    // The hero was in view at the last tick.
    bool SeesHero() const { return bSeesHero; }
    // Wary for the rest of the beat (SoraStealthRules::WaryPermille).
    bool IsWary() const { return Mind.Wary; }
    // The detection meter the HUD shows over it (SoraStealthRules::Meter).
    int32 MeterPermille() const;
    // The hero is in the view cone, within sight range and unobstructed.
    bool CanSee(const ASoraCharacterBase& Target) const;
    SoraStealthRules::EState State() const { return Mind.State; }
    int32 StateElapsedMs() const { return Mind.StateMs; }
    int32 AwarenessPermille() const { return Mind.Awareness / SoraStealthRules::AwarenessScale; }
    bool IsHunting() const { return bHunting; }
    SoraStealthRules::ERole CombatRole() const { return Role; }
    // Where the hero was last seen or heard.
    FVector LastKnownLocation() const { return LastKnown; }
    // The cover spot or flank point held in combat or retreat.
    bool HoldsPosition() const { return bHasPosition; }
    FVector HeldPosition() const { return Position; }
    // A scripted errand the beat gives it (USoraFieldcraft): a seizure drone
    // to its quarry, a scout pacing the road, a guard drawn to a rung bell.
    // It goes to Goal at Pace (x its full speed) and holds there facing
    // Facing, and neither patrols nor fights while the errand lasts. It still
    // notices the hero; one that only runs while calm (bWhileCalm) ends the
    // moment it is alerted. DurationMs 0 lasts until cleared.
    void SetErrand(const FVector& Goal, const FVector& Facing, float Pace, int32 DurationMs, bool bWhileCalm,
        bool bThreeDimensional = false, float AcceptanceCm = ErrandReachCm, bool bSupportedSteps = false);
    void AssignLift(ASoraCampaignLift& Lift,int32 Wave);
    void AssignSpireFlight() { bSpireFlight=true; }
    void AssignTenementDefense(int32 Member);
    bool HasTenementDefenseFlight() const { return TenementDrone!=INDEX_NONE; }
    void AssignWorkshopDefense(int32 Index);
    int32 WorkshopEntryIndex() const { return WorkshopEntry; }
    bool WorkshopVaultLaunched() const { return bWorkshopVaultLaunched; }
    // An errand's goal is reached within this (2D).
    static constexpr float ErrandReachCm = 120.f;
    void ClearErrand() { bErrand = false; }
    bool HasErrand() const { return bErrand; }
    // Within its acceptance of the errand's goal (2D).
    bool ErrandReached() const { return bErrand && bErrandReached; }
    const SoraPatrolRules::FLoop& PatrolTiming() const { return PatrolLoop; }
    // An ordinary patrol's physical waypoint stop, excluding search/errands.
    bool IsPatrolPausedAt(int32 Point) const
    { return !bHunting&&!bErrand&&Mind.State==SoraStealthRules::EState::Unaware&&bPaused&&RouteIndex==Point; }
protected:
    virtual void OnPossess(APawn* InPawn) override;
    virtual void OnUnPossess() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
    enum class EMove : uint8 { Moving, Arrived, Blocked };
    // A noise heard since the last tick. Evidence is where it says the hero is.
    struct FNoise
    {
        SoraStealthRules::ENoise Kind;
        FVector Origin;
        FVector Evidence;
        TWeakObjectPtr<const AActor> Source;
        bool bAlarm = false;
        int32 LoudnessPermille = 1000;
    };
    void Prepare(bool bHunt);
    FSoraMillisecondClock ThinkClock;
    void Think(ASoraEnemy& Enemy, ASoraCharacterBase& Target, float DeltaSeconds);
    void DrivePupil(ASoraEnemy& Enemy, ASoraCharacterBase& Target, float DeltaSeconds);
    void DriveBoss(ASoraBoss& Boss, ASoraCharacterBase& Target, float DeltaSeconds);
    SoraStealthRules::FSight Look(const ASoraEnemy& Enemy, const ASoraCharacterBase& Target) const;
    bool Occluded(const FVector& From, const FVector& To, const AActor* Source) const;
    void Enter(ASoraEnemy& Enemy, SoraStealthRules::EState Previous, int32 NowMs);
    SoraStealthRules::FVigilance Vigilance() const;
    void LookForBodies(ASoraEnemy& Enemy, int32 DtMs);
    void CallOut(const ASoraEnemy& Enemy) const;
    void AlarmRun(ASoraEnemy& Enemy, const ASoraCharacterBase& Target, float DeltaSeconds, int32 NowMs);
    bool DriveSpireAlarm(ASoraEnemy& Enemy,float DeltaSeconds,int32 NowMs);
    void AnnounceState(const ASoraEnemy& Enemy) const;
    void Act(ASoraEnemy& Enemy, ASoraCharacterBase& Target, bool bSees, float DeltaSeconds, int32 NowMs);
    void Fight(ASoraEnemy& Enemy, ASoraCharacterBase& Target, bool bSees, float DeltaSeconds, int32 NowMs);
    bool DriveHorseShell(ASoraEnemy& Enemy,float DeltaSeconds,int32 NowMs);
    void Patrol(ASoraEnemy& Enemy, float DeltaSeconds, int32 NowMs);
    void ScheduledPatrol(ASoraEnemy& Enemy,float DeltaSeconds,int32 NowMs);
    FSoraMillisecondClock PatrolClock;
    SoraPatrolRules::FLoop PatrolLoop;
    void Search(ASoraEnemy& Enemy, float DeltaSeconds, int32 NowMs);
    bool ChoosePosition(const ASoraEnemy& Enemy, const FVector& Threat, bool bRetreat);
    bool Claimed(const FVector& Spot) const;
    EMove WalkTo(ASoraEnemy& Enemy, const FVector& Goal, float Speed, float Acceptance, int32 NowMs,bool bStrict3D=false);
    EMove WalkSupportedSegment(ASoraEnemy& Enemy,const FVector& Goal,float Speed,float Acceptance=20.f,bool bSteps=false);
    EMove FlyTo(ASoraEnemy& Enemy, const FVector& Goal, float Speed, float Acceptance, int32 NowMs,bool bVolume=false);
    // One move request at Here: true once the walk has made no progress for
    // SoraStealthRules::StuckMs; the next request starts a fresh clock.
    bool Stuck(const FVector& Here, int32 NowMs,bool bThreeDimensional=false);
    void ClearPath();
    void Face(ASoraEnemy& Enemy, const FVector& Direction, float DeltaSeconds, float Rate) const;
    void LookAround(ASoraEnemy& Enemy, float BaseYaw, float Amplitude, float DeltaSeconds, int32 NowMs, int32 PeriodMs = 6000) const;
    void Footwork(ASoraEnemy& Enemy, const ASoraCharacterBase& Target, const FVector& Delta, float Distance);
    void OnWeaponFired(const FSoraWeaponFiredEvent& Event);
    void OnDetonated(const FSoraDetonatedEvent& Event);
    void OnMeleeCommitted(const FSoraMeleeCommittedEvent& Event);
    void Listen(bool bEnable);
    int32 WorldMs() const;

    SoraStealthRules::FMind Mind = SoraStealthRules::Calm();
    SoraStealthRules::ERole Role = SoraStealthRules::ERole::CoverShooter;
    bool bHunting = false;
    int32 Slot = 0;
    int32 NextIntelMs = 0;
    int32 CombatSinceMs = 0;
    FVector LastKnown = FVector::ZeroVector;
    TArray<FNoise> Heard;
    // Patrol and post.
    UPROPERTY() FSoraPatrolRoute Route;
    FVector Post = FVector::ZeroVector;
    float PostYaw = 0.f;
    int32 RouteIndex = 0;
    int32 RouteStep = 1;
    int32 PauseUntilMs = 0;
    float PauseYaw = 0.f;
    bool bPaused = false;
    double PointPauseRemainingMs = 0;
    // Search around the last known place.
    TArray<FVector> SearchPoints;
    int32 SearchIndex = 0;
    // The state's move goal is reached or unreachable (SoraStealthRules::FSenses::Reached).
    bool bGoalDone = false;
    // Movement along the navigation mesh.
    TArray<FVector> Path;
    int32 PathIndex = 0;
    FVector PathGoal = FVector::ZeroVector;
    bool bPathValid = false;
    int32 RepathAtMs = 0;
    FVector Heading = FVector::ForwardVector;
    // The stuck clock (SoraStealthRules::Progress) and where it last started.
    SoraStealthRules::FProgress Walked;
    FVector StuckFrom = FVector::ZeroVector;
    // Combat and retreat positions: a cover spot (its box and the face's
    // outward normal) or an open flank or fallback point.
    bool bHasPosition = false;
    FVector Position = FVector::ZeroVector;
    bool bPositionIsCover = false;
    FVector PositionNormal = FVector::ForwardVector;
    FBox2D PositionBox = FBox2D(ForceInit);
    bool bCanPeek = false;
    FVector PeekPosition = FVector::ZeroVector;
    int32 ReviewPositionAtMs = 0;
    // A marksman that has fired enough moves on and does not take this spot again.
    bool bAvoidSpot = false;
    FVector AvoidSpot = FVector::ZeroVector;
    // An auditor's alarm repeats while it runs; in a zone with lecterns it
    // runs to one instead and raises the zone's alarm there.
    int32 NextAlarmMs = 0;
    int32 Lectern = INDEX_NONE;
    bool bLecternUnreachable = false;
    bool bAlarmRaised = false;
    // A scripted errand (SetErrand).
    bool bErrand = false;
    bool bErrandWhileCalm = false;
    bool bErrandReached = false;
    bool bErrand3D = false;
    // Authored stair/gallery waypoints use ordinary swept character movement
    // with support checked ahead, where coarse navmesh cells lose the treads.
    bool bErrandSupportedSteps = false;
    float ErrandAcceptanceCm = ErrandReachCm;
    FVector ErrandGoal = FVector::ZeroVector;
    FVector ErrandFacing = FVector::ForwardVector;
    float ErrandPace = 1.f;
    int32 ErrandUntilMs = 0;
    bool RunErrand(ASoraEnemy& Enemy, float DeltaSeconds, int32 NowMs);
    TWeakObjectPtr<ASoraCampaignLift> AssignedLift;
    int32 LiftWave = INDEX_NONE;
    bool bLiftJumped = false;
    bool bSpireFlight=false;
    int32 TenementDrone=INDEX_NONE,TenementLeg=0;
    bool DriveTenementDefense(ASoraEnemy& Enemy,ASoraCharacterBase& Target,float Dt);
    int32 WorkshopEntry=INDEX_NONE,WorkshopLeg=0;
    bool bWorkshopVaultLaunched=false;
    bool DriveWorkshopDefense(ASoraEnemy& Enemy,ASoraCharacterBase& Target,float Dt);
    bool DriveSpireFlight(ASoraEnemy& Enemy,ASoraCharacterBase& Target,float Dt);
    bool DriveLift(ASoraEnemy& Enemy,ASoraCharacterBase& Target,float Dt);
    // Stealth: the hero in view at the last tick, and evidence of a body.
    bool bSeesHero = false;
    int32 BodyEvidence = 0;
    TWeakObjectPtr<ASoraEnemy> BodyInView;
    TWeakObjectPtr<USoraGameEvents> Events;
    FDelegateHandle FiredHandle, DetonatedHandle, MeleeHandle;
};
