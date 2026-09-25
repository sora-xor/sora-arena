#pragma once
#include "CoreMinimal.h"
#include "AIController.h"
#include "SoraStealthRules.h"
#include "SoraEnemyController.generated.h"
class ASoraBoss;
class ASoraCharacterBase;
class ASoraEnemy;
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
    UPROPERTY() bool bPingPong = false;
    UPROPERTY() int32 PauseMs = 1500;
};

// The campaign opponents' brain, run from its own tick before its pawn moves.
// Sparring pupils and the final collector keep their fixed drills. Every other
// opponent runs SoraStealthRules' state machine (unaware, suspicious, alert,
// search, combat, retreat) on what it perceives: a view cone with line of
// sight, distance and a light proxy, and the noise of footsteps, sprinting,
// blades, shots, explosions and allies' call-outs. It walks the runtime
// navigation mesh (USoraNavigation) around walls, patrols its route, takes
// cover behind the arena's low boxes and peeks out to fire, or flanks by slot.
// Every choice follows world time, slots and fixed patterns; nothing is random.
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
    // An ally at Caller shouts that the hero is at Where.
    void HearCallout(const FVector& Caller, const FVector& Where);
    // The hero is in the view cone, within sight range and unobstructed.
    bool CanSee(const ASoraCharacterBase& Target) const;
    SoraStealthRules::EState State() const { return Mind.State; }
    int32 AwarenessPermille() const { return Mind.Awareness / SoraStealthRules::AwarenessScale; }
    bool IsHunting() const { return bHunting; }
    SoraStealthRules::ERole CombatRole() const { return Role; }
    // Where the hero was last seen or heard.
    FVector LastKnownLocation() const { return LastKnown; }
    // The cover spot or flank point held in combat or retreat.
    bool HoldsPosition() const { return bHasPosition; }
    FVector HeldPosition() const { return Position; }
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
    };
    void Prepare(bool bHunt);
    void Think(ASoraEnemy& Enemy, ASoraCharacterBase& Target, float DeltaSeconds);
    void DrivePupil(ASoraEnemy& Enemy, ASoraCharacterBase& Target, float DeltaSeconds);
    void DriveCollector(ASoraBoss& Boss, ASoraCharacterBase& Target, float DeltaSeconds);
    SoraStealthRules::FSight Look(const ASoraEnemy& Enemy, const ASoraCharacterBase& Target) const;
    int32 LightAt(const FVector& Location) const;
    bool Occluded(const FVector& From, const FVector& To, const AActor* Source) const;
    void Enter(ASoraEnemy& Enemy, SoraStealthRules::EState Previous, int32 NowMs);
    void CallOut(const ASoraEnemy& Enemy) const;
    void Act(ASoraEnemy& Enemy, ASoraCharacterBase& Target, bool bSees, float DeltaSeconds, int32 NowMs);
    void Fight(ASoraEnemy& Enemy, ASoraCharacterBase& Target, bool bSees, float DeltaSeconds, int32 NowMs);
    void Patrol(ASoraEnemy& Enemy, float DeltaSeconds, int32 NowMs);
    void Search(ASoraEnemy& Enemy, float DeltaSeconds, int32 NowMs);
    bool ChoosePosition(const ASoraEnemy& Enemy, const FVector& Threat, bool bRetreat);
    bool Claimed(const FVector& Spot) const;
    EMove WalkTo(ASoraEnemy& Enemy, const FVector& Goal, float Speed, float Acceptance, int32 NowMs);
    void ClearPath();
    void Face(ASoraEnemy& Enemy, const FVector& Direction, float DeltaSeconds, float Rate) const;
    void LookAround(ASoraEnemy& Enemy, float BaseYaw, float Amplitude, float DeltaSeconds, int32 NowMs) const;
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
    FVector StuckFrom = FVector::ZeroVector;
    int32 StuckSinceMs = 0;
    int32 LastMovingMs = MIN_int32;
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
    TWeakObjectPtr<USoraGameEvents> Events;
    FDelegateHandle FiredHandle, DetonatedHandle, MeleeHandle;
};
