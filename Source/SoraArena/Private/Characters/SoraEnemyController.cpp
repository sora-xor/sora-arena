#include "SoraEnemyController.h"
#include "SoraBoss.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraGameEvents.h"
#include "SoraHistoricalArms.h"
#include "SoraPlayerCharacter.h"
#include "World/SoraNavigation.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/Light.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

namespace Stealth = SoraStealthRules;

namespace SoraEnemyBrain
{
// The eye sits where the opponents' attacks trace from; the hero is seen at
// his head or chest.
constexpr float EyeHeight = 50.f;
constexpr float HeadHeight = 60.f;
constexpr float ChestHeight = 10.f;
// Movement input scales: a patrol walk, a careful approach, a hunter's pace,
// combat repositioning (the first invaders' pace) and a retreat.
constexpr float PatrolSpeed = .35f;
constexpr float InvestigateSpeed = .42f;
constexpr float HuntSpeed = .6f;
constexpr float CombatSpeed = .55f;
constexpr float RetreatSpeed = .75f;
constexpr int32 RepathMs = 500;
constexpr int32 StuckMs = 2000;
constexpr int32 SearchPauseMs = 800;
// Blade footwork takes over from pathing within this distance of a seen hero.
constexpr float FootworkRangeCm = 400.f;
// Without cover, a ranged opponent closes to this range and sidesteps there.
constexpr float OpenFireRangeCm = 650.f;
}

ASoraEnemyController::ASoraEnemyController()
{
    PrimaryActorTick.bCanEverTick = true;
    bWantsPlayerState = false;
}

int32 ASoraEnemyController::WorldMs() const
{
    return FMath::FloorToInt32(GetWorld()->GetTimeSeconds() * 1000.0);
}

void ASoraEnemyController::OnPossess(APawn* InPawn)
{
    Super::OnPossess(InPawn);
    Listen(true);
}

void ASoraEnemyController::OnUnPossess()
{
    Listen(false);
    Super::OnUnPossess();
}

void ASoraEnemyController::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    Listen(false);
    Super::EndPlay(EndPlayReason);
}

void ASoraEnemyController::Listen(bool bEnable)
{
    if (USoraGameEvents* Bus = Events.Get())
    {
        Bus->OnWeaponFired.Remove(FiredHandle);
        Bus->OnDetonated.Remove(DetonatedHandle);
        Bus->OnMeleeCommitted.Remove(MeleeHandle);
    }
    Events.Reset();
    FiredHandle.Reset();
    DetonatedHandle.Reset();
    MeleeHandle.Reset();
    if (!bEnable)
        return;
    // Hearing only records what was heard; the next tick decides what to do.
    if (USoraGameEvents* Bus = USoraGameEvents::Get(this))
    {
        Events = Bus;
        FiredHandle = Bus->OnWeaponFired.AddUObject(this, &ASoraEnemyController::OnWeaponFired);
        DetonatedHandle = Bus->OnDetonated.AddUObject(this, &ASoraEnemyController::OnDetonated);
        MeleeHandle = Bus->OnMeleeCommitted.AddUObject(this, &ASoraEnemyController::OnMeleeCommitted);
    }
}

void ASoraEnemyController::OnWeaponFired(const FSoraWeaponFiredEvent& Event)
{
    const auto* Shooter = Cast<ASoraCharacterBase>(Event.Shooter);
    if (!Shooter || Shooter == GetPawn())
        return;
    // A bowstring is no louder than a blade. The hero's shot gives him away;
    // an ally's shot shows where it was aimed.
    const Stealth::ENoise Kind = Event.Kind == ESoraShotKind::Arrow ? Stealth::ENoise::Melee : Stealth::ENoise::Shot;
    Heard.Add({Kind, Event.Origin, Shooter->IsEnemy() ? Event.End : Event.Origin, Shooter});
}

void ASoraEnemyController::OnDetonated(const FSoraDetonatedEvent& Event)
{
    Heard.Add({Stealth::ENoise::Explosion, Event.Location, Event.Location, nullptr});
}

void ASoraEnemyController::OnMeleeCommitted(const FSoraMeleeCommittedEvent& Event)
{
    // Only the hero's blade; an ally's swing is already its own fight.
    const auto* Attacker = Cast<ASoraCharacterBase>(Event.Attacker);
    if (!Attacker || Attacker->IsEnemy())
        return;
    Heard.Add({Stealth::ENoise::Melee, Attacker->GetActorLocation(), Attacker->GetActorLocation(), Attacker});
}

void ASoraEnemyController::HearCallout(const FVector& Caller, const FVector& Where)
{
    Heard.Add({Stealth::ENoise::Callout, Caller, Where, nullptr});
}

void ASoraEnemyController::Prepare(bool bHunt)
{
    const ASoraEnemy* Enemy = GetPawn<ASoraEnemy>();
    bHunting = bHunt;
    Mind = bHunt ? Stealth::Hunting() : Stealth::Calm();
    Slot = Enemy ? Enemy->EnemySlot() : 0;
    Role = Stealth::Role(Slot, Enemy && Enemy->IsBladeRetainer());
    Post = Enemy ? Enemy->GetActorLocation() : FVector::ZeroVector;
    PostYaw = Enemy ? Enemy->GetActorRotation().Yaw : 0.f;
    LastKnown = Post;
    Route = FSoraPatrolRoute();
    RouteIndex = 0;
    RouteStep = 1;
    bPaused = false;
    SearchPoints.Reset();
    Heard.Reset();
    bGoalDone = false;
    bHasPosition = false;
    bCanPeek = false;
    ClearPath();
    NextIntelMs = WorldMs() + Stealth::IntelMs;
    CombatSinceMs = WorldMs();
}

void ASoraEnemyController::BeginHunt()
{
    Prepare(true);
    // The wave is sent where the hero stands now.
    if (const APawn* Hero = UGameplayStatics::GetPlayerPawn(this, 0))
        LastKnown = Hero->GetActorLocation();
}

void ASoraEnemyController::BeginPatrol(const FSoraPatrolRoute& InRoute)
{
    Prepare(false);
    Route = InRoute;
    if (Route.Points.Num() == 1)
        Post = Route.Points[0];
}

void ASoraEnemyController::Tick(float Dt)
{
    Super::Tick(Dt);
    ASoraEnemy* Enemy = GetPawn<ASoraEnemy>();
    if (!Enemy || Enemy->IsKernelDriven() || !FSoraCatalog::Get().IsReady())
        return;
    // A held round (menu, title card or result), a defeated opponent or one
    // whose pawn is held still with its tick off does nothing, and noises made
    // meanwhile are forgotten.
    auto* Target = Cast<ASoraCharacterBase>(UGameplayStatics::GetPlayerPawn(this, 0));
    if (!Enemy->IsActorTickEnabled() || !Enemy->CanPlay() || !Target || !Target->IsAlive())
    {
        Heard.Reset();
        return;
    }
    if (auto* Boss = Cast<ASoraBoss>(Enemy))
    {
        DriveCollector(*Boss, *Target, Dt);
        return;
    }
    if (Enemy->IsDojoPupil())
    {
        DrivePupil(*Enemy, *Target, Dt);
        return;
    }
    Think(*Enemy, *Target, Dt);
}

void ASoraEnemyController::Think(ASoraEnemy& Enemy, ASoraCharacterBase& Target, float Dt)
{
    // Every query this frame sees the same, complete navigation mesh.
    if (USoraNavigation* Nav = USoraNavigation::Get(this))
        Nav->Settle();
    const int32 NowMs = WorldMs();
    const int32 DtMs = FMath::Max(1, FMath::RoundToInt32(Dt * 1000.f));
    const FVector Here = Enemy.GetActorLocation();
    const FVector Ear = Here + FVector(0.f, 0.f, SoraEnemyBrain::EyeHeight);
    const FVector There = Target.GetActorLocation();

    Stealth::FSenses Senses{};
    const Stealth::FSight Sight = Look(Enemy, Target);
    const bool bSees = Stealth::InView(Sight);
    Senses.SightGain = Stealth::SightGainPerSecond(Sight);
    bool bEvidence = bSees;
    FVector Evidence = There;

    // The hero's footsteps are heard for as long as they last.
    const UCharacterMovementComponent* Walk = Target.GetCharacterMovement();
    if (Target.GetVelocity().Size2D() > 150.f && Walk && Walk->IsMovingOnGround())
    {
        const auto* Hero = Cast<ASoraPlayerCharacter>(&Target);
        const Stealth::ENoise Steps = Hero && Hero->IsSprinting() ? Stealth::ENoise::Sprint : Stealth::ENoise::Footstep;
        const int32 Distance = FMath::RoundToInt32(FVector::Dist(There, Ear));
        if (Distance <= Stealth::NoiseRadiusCm(Steps))
            Senses.NoisePerSecond = Stealth::HeardPermille(Steps, Distance, Occluded(There, Ear, &Target));
        bEvidence |= Senses.NoisePerSecond > 0;
    }
    // The loudest single noise since the last tick.
    for (const FNoise& Noise : Heard)
    {
        const int32 Distance = FMath::RoundToInt32(FVector::Dist(Noise.Origin, Ear));
        if (Distance > Stealth::NoiseRadiusCm(Noise.Kind))
            continue;
        const int32 Level = Stealth::HeardPermille(Noise.Kind, Distance, Occluded(Noise.Origin, Ear, Noise.Source.Get()));
        if (Level > Senses.NoiseImpulse)
        {
            Senses.NoiseImpulse = Level;
            if (!bSees)
                Evidence = Noise.Evidence;
        }
    }
    Heard.Reset();
    bEvidence |= Senses.NoiseImpulse > 0;
    // The invaders' relay tells a hunting opponent that cannot see the hero where he is.
    const bool bSearching = Mind.State != Stealth::EState::Combat && Mind.State != Stealth::EState::Retreat;
    if (bHunting && !bSees && bSearching && NowMs >= NextIntelMs)
    {
        NextIntelMs = NowMs + Stealth::IntelMs;
        Senses.NoiseImpulse = Stealth::AwarenessMax / Stealth::AwarenessScale;
        Evidence = There;
        bEvidence = true;
    }
    if (bEvidence)
        LastKnown = Evidence;

    Senses.HealthPermille = Enemy.MaxHealth > 0.f ? FMath::RoundToInt32(Enemy.Health * 1000.f / Enemy.MaxHealth) : 0;
    Senses.Reached = bGoalDone;
    Senses.CanRetreat = Stealth::CanRetreat(Role);
    const Stealth::EState Previous = Mind.State;
    Mind = Stealth::Step(Mind, Senses, DtMs);
    if (Mind.State != Previous)
        Enter(Enemy, Previous, NowMs);
    Act(Enemy, Target, bSees, Dt, NowMs);
}

void ASoraEnemyController::Enter(ASoraEnemy& Enemy, Stealth::EState Previous, int32 NowMs)
{
    bGoalDone = false;
    bPaused = false;
    ClearPath();
    switch (Mind.State)
    {
    case Stealth::EState::Search:
    {
        // The last known place, then four points around it, turned by slot so
        // a group spreads out.
        SearchPoints.Reset();
        SearchPoints.Add(LastKnown);
        const USoraNavigation* Nav = USoraNavigation::Get(this);
        for (int32 Index = 0; Index < 4; ++Index)
        {
            const FVector Offset = FVector(350.f, 0.f, 0.f).RotateAngleAxis(90.f * (Index + Slot), FVector::UpVector);
            FVector OnMesh;
            if (Nav && Nav->Project(LastKnown + Offset, OnMesh))
                SearchPoints.Add(OnMesh);
        }
        SearchIndex = 0;
        break;
    }
    case Stealth::EState::Combat:
        CombatSinceMs = NowMs;
        bHasPosition = false;
        break;
    case Stealth::EState::Retreat:
        ChoosePosition(Enemy, LastKnown, true);
        break;
    default:
        break;
    }
    // An opponent that has just found the hero shouts to the allies near it.
    const bool bWasCalm = Previous == Stealth::EState::Unaware || Previous == Stealth::EState::Suspicious ||
        Previous == Stealth::EState::Search;
    if (bWasCalm && (Mind.State == Stealth::EState::Alert || Mind.State == Stealth::EState::Combat))
        CallOut(Enemy);
}

void ASoraEnemyController::CallOut(const ASoraEnemy& Enemy) const
{
    const float Radius = Stealth::NoiseRadiusCm(Stealth::ENoise::Callout);
    for (TActorIterator<ASoraEnemyController> It(GetWorld()); It; ++It)
    {
        const APawn* Ally = It->GetPawn();
        if (*It != this && Ally && FVector::Dist(Ally->GetActorLocation(), Enemy.GetActorLocation()) <= Radius)
            It->HearCallout(Enemy.GetActorLocation(), LastKnown);
    }
}

void ASoraEnemyController::Act(ASoraEnemy& Enemy, ASoraCharacterBase& Target, bool bSees, float Dt, int32 NowMs)
{
    switch (Mind.State)
    {
    case Stealth::EState::Unaware:
        Patrol(Enemy, Dt, NowMs);
        return;
    case Stealth::EState::Suspicious:
        // Turn toward what was noticed, then walk over carefully.
        Face(Enemy, LastKnown - Enemy.GetActorLocation(), Dt, 5.f);
        if (Mind.StateMs >= Stealth::LookMs)
            bGoalDone = WalkTo(Enemy, LastKnown, SoraEnemyBrain::InvestigateSpeed, 150.f, NowMs) != EMove::Moving;
        return;
    case Stealth::EState::Alert:
        // Eyes stay on the place the hero was while the path winds toward it.
        Face(Enemy, LastKnown - Enemy.GetActorLocation(), Dt, 5.f);
        bGoalDone = WalkTo(Enemy, LastKnown, SoraEnemyBrain::HuntSpeed, 150.f, NowMs) != EMove::Moving;
        return;
    case Stealth::EState::Search:
        Search(Enemy, Dt, NowMs);
        return;
    case Stealth::EState::Combat:
        Fight(Enemy, Target, bSees, Dt, NowMs);
        return;
    case Stealth::EState::Retreat:
        Face(Enemy, Target.GetActorLocation() - Enemy.GetActorLocation(), Dt, 4.f);
        bGoalDone = !bHasPosition || WalkTo(Enemy, Position, SoraEnemyBrain::RetreatSpeed, 60.f, NowMs) != EMove::Moving;
        return;
    }
}

void ASoraEnemyController::Patrol(ASoraEnemy& Enemy, float Dt, int32 NowMs)
{
    if (Route.Points.Num() <= 1)
    {
        // A guard post: return to it, then watch its arc.
        if (WalkTo(Enemy, Post, SoraEnemyBrain::PatrolSpeed, 60.f, NowMs) == EMove::Moving)
            Face(Enemy, Heading, Dt, 5.f);
        else
            LookAround(Enemy, PostYaw, 25.f, Dt, NowMs);
        return;
    }
    if (bPaused)
    {
        LookAround(Enemy, PauseYaw, 35.f, Dt, NowMs);
        if (NowMs < PauseUntilMs)
            return;
        bPaused = false;
        if (Route.bPingPong)
        {
            if (!Route.Points.IsValidIndex(RouteIndex + RouteStep))
                RouteStep = -RouteStep;
            RouteIndex = FMath::Clamp(RouteIndex + RouteStep, 0, Route.Points.Num() - 1);
        }
        else
            RouteIndex = (RouteIndex + 1) % Route.Points.Num();
    }
    if (WalkTo(Enemy, Route.Points[RouteIndex], SoraEnemyBrain::PatrolSpeed, 70.f, NowMs) != EMove::Moving)
    {
        bPaused = true;
        PauseUntilMs = NowMs + Route.PauseMs;
        PauseYaw = Enemy.GetActorRotation().Yaw;
        return;
    }
    Face(Enemy, Heading, Dt, 5.f);
}

void ASoraEnemyController::Search(ASoraEnemy& Enemy, float Dt, int32 NowMs)
{
    if (SearchPoints.IsEmpty())
    {
        LookAround(Enemy, Enemy.GetActorRotation().Yaw, 60.f, Dt, NowMs);
        return;
    }
    if (bPaused)
    {
        LookAround(Enemy, PauseYaw, 60.f, Dt, NowMs);
        if (NowMs < PauseUntilMs)
            return;
        bPaused = false;
        SearchIndex = (SearchIndex + 1) % SearchPoints.Num();
    }
    if (WalkTo(Enemy, SearchPoints[SearchIndex], SoraEnemyBrain::InvestigateSpeed, 90.f, NowMs) != EMove::Moving)
    {
        bPaused = true;
        PauseUntilMs = NowMs + SoraEnemyBrain::SearchPauseMs;
        PauseYaw = Enemy.GetActorRotation().Yaw;
        return;
    }
    Face(Enemy, Heading, Dt, 5.f);
}

void ASoraEnemyController::Fight(ASoraEnemy& Enemy, ASoraCharacterBase& Target, bool bSees, float Dt, int32 NowMs)
{
    FVector Delta = Target.GetActorLocation() - Enemy.GetActorLocation();
    Delta.Z = 0.f;
    const float Distance = Delta.Size();
    if (Role == Stealth::ERole::Blade)
    {
        // A committed cut keeps its locked line. Otherwise the blade squares up
        // to the hero, pathing in until footwork takes over at close range.
        if (!Enemy.IsDuelWindup())
        {
            Face(Enemy, Delta, Dt, 4.f);
            if (bSees && Distance <= SoraEnemyBrain::FootworkRangeCm)
                Footwork(Enemy, Target, Delta, Distance);
            else
                WalkTo(Enemy, Target.GetActorLocation(), SoraEnemyBrain::CombatSpeed, 150.f, NowMs);
        }
        if (bSees || Enemy.IsDuelWindup())
            Enemy.DuelAttack(Target, Distance);
        return;
    }
    Face(Enemy, Delta, Dt, 4.f);
    if (bSees)
        Enemy.RangedAttack(Target, Distance);
    // On first contact a shooter holds its ground and fires.
    if (NowMs - CombatSinceMs < Stealth::ReactionMs(Slot))
        return;
    const FVector Threat = Target.GetActorLocation();
    FSoraCoverSpot Held;
    Held.Location = Position;
    Held.Normal = PositionNormal;
    Held.Box = PositionBox;
    const bool bExposed = bHasPosition && bPositionIsCover && !USoraNavigation::Shields(Held, Threat);
    if (!bHasPosition || bExposed || NowMs >= ReviewPositionAtMs)
        ChoosePosition(Enemy, Threat, false);
    if (bHasPosition)
    {
        const FVector Goal = bCanPeek && Stealth::Peeking(NowMs, Slot) ? PeekPosition : Position;
        if (WalkTo(Enemy, Goal, SoraEnemyBrain::CombatSpeed, 40.f, NowMs) == EMove::Blocked)
        {
            bHasPosition = false;
            ReviewPositionAtMs = NowMs + 1500;
        }
        return;
    }
    // No cover within reach: close to firing range and sidestep there.
    if (Distance > SoraEnemyBrain::OpenFireRangeCm)
        WalkTo(Enemy, Threat, SoraEnemyBrain::CombatSpeed, SoraEnemyBrain::OpenFireRangeCm, NowMs);
    else
        Enemy.AddMovementInput(Enemy.GetActorRightVector(), FMath::Sin(Enemy.GetLifeTime() + Slot) * .2f);
}

void ASoraEnemyController::Footwork(ASoraEnemy& Enemy, const ASoraCharacterBase& Target, const FVector& Delta, float Distance)
{
    // The retainer's maai: close, hold with a slow sidestep, or withdraw.
    FVector Move = Delta.GetSafeNormal();
    FHitResult Ahead;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BotNavigation), false, &Enemy);
    if (GetWorld()->LineTraceSingleByChannel(Ahead, Enemy.GetActorLocation(), Enemy.GetActorLocation() + Move * 180.f, ECC_Visibility, Query) &&
        Ahead.GetActor() != &Target)
        Move = FVector(-Move.Y, Move.X, 0.f) * (Slot % 2 ? 1.f : -1.f);
    switch (SoraHistoricalArms::RetainerFootwork(Distance))
    {
    case SoraHistoricalArms::EFootwork::Close: Enemy.AddMovementInput(Move, SoraEnemyBrain::CombatSpeed); break;
    case SoraHistoricalArms::EFootwork::Withdraw: Enemy.AddMovementInput(-Move, SoraEnemyBrain::CombatSpeed); break;
    case SoraHistoricalArms::EFootwork::Hold:
        Enemy.AddMovementInput(Enemy.GetActorRightVector(), FMath::Sin(Enemy.GetLifeTime() + Slot) * .2f); break;
    }
}

bool ASoraEnemyController::ChoosePosition(const ASoraEnemy& Enemy, const FVector& Threat, bool bRetreat)
{
    bHasPosition = false;
    bCanPeek = false;
    ReviewPositionAtMs = WorldMs() + 3500 + Slot % 4 * 250;
    const USoraNavigation* Nav = USoraNavigation::Get(this);
    if (!Nav || !Nav->IsReady())
        return false;
    const FVector Here = Enemy.GetActorLocation();
    // A flanker aims for the hero's side, square to where its allies press.
    FVector Flank = FVector::ZeroVector;
    bool bFlank = false;
    if (!bRetreat && Role == Stealth::ERole::Flanker)
    {
        FVector Squad = FVector::ZeroVector;
        int32 Allies = 0;
        for (TActorIterator<ASoraEnemyController> It(GetWorld()); It; ++It)
        {
            const auto* Ally = Cast<ASoraCharacterBase>(It->GetPawn());
            if (*It != this && Ally && Ally->IsAlive() && It->State() == Stealth::EState::Combat)
            {
                Squad += Ally->GetActorLocation();
                ++Allies;
            }
        }
        FVector Front = ((Allies > 0 ? Squad / Allies : Here) - Threat).GetSafeNormal2D();
        if (Front.IsNearlyZero())
            Front = (Here - Threat).GetSafeNormal2D();
        const FVector Side = Front.RotateAngleAxis(90.f * Stealth::FlankSide(Slot), FVector::UpVector);
        bFlank = Nav->Project(Threat + Side * Stealth::FlankDistanceCm, Flank);
    }
    const TArray<FSoraCoverSpot>& Spots = Nav->CoverSpots();
    int32 Best = INDEX_NONE;
    int32 BestScore = MAX_int32;
    for (int32 Index = 0; Index < Spots.Num(); ++Index)
    {
        const FSoraCoverSpot& Spot = Spots[Index];
        if (!USoraNavigation::Shields(Spot, Threat) || Claimed(Spot.Location))
            continue;
        const int32 Travel = FMath::RoundToInt32(FVector::Dist2D(Here, Spot.Location));
        const int32 Range = FMath::RoundToInt32(FVector::Dist2D(Spot.Location, Threat));
        int32 Score = bRetreat ? Stealth::RetreatScore(Travel, Range) : Stealth::CoverScore(Travel, Range);
        if (Score < 0 || Travel > 2500)
            continue;
        if (bFlank)
        {
            // Flank cover must be near the flank point.
            Score = FMath::RoundToInt32(FVector::Dist2D(Spot.Location, Flank));
            if (Score > 600)
                continue;
        }
        if (Score < BestScore)
        {
            BestScore = Score;
            Best = Index;
        }
    }
    if (Best != INDEX_NONE)
    {
        const FSoraCoverSpot& Spot = Spots[Best];
        bHasPosition = true;
        bPositionIsCover = true;
        Position = Spot.Location;
        PositionNormal = Spot.Normal;
        PositionBox = Spot.Box;
        // Peek past whichever end of the box leaves a clear line to the hero.
        for (const float Side : {1.f, -1.f})
        {
            const FVector Peek = Spot.Location + Spot.Tangent * Side * (Spot.HalfWidth + 55.f);
            FVector OnMesh;
            if (!bRetreat && Nav->Project(Peek, OnMesh) && FVector::Dist2D(OnMesh, Peek) <= 30.f &&
                !USoraNavigation::Crosses(OnMesh, Threat, Spot.Box))
            {
                bCanPeek = true;
                PeekPosition = OnMesh;
                break;
            }
        }
        return true;
    }
    bPositionIsCover = false;
    if (bFlank)
    {
        bHasPosition = true;
        Position = Flank;
        return true;
    }
    if (bRetreat)
    {
        // No cover far enough away: fall back straight from the hero.
        FVector Away;
        if (Nav->Project(Here + (Here - Threat).GetSafeNormal2D() * 600.f, Away))
        {
            bHasPosition = true;
            Position = Away;
            return true;
        }
    }
    return false;
}

bool ASoraEnemyController::Claimed(const FVector& Spot) const
{
    for (TActorIterator<ASoraEnemyController> It(GetWorld()); It; ++It)
    {
        const auto* Ally = Cast<ASoraCharacterBase>(It->GetPawn());
        if (*It != this && It->bHasPosition && Ally && Ally->IsAlive() && FVector::Dist2D(It->Position, Spot) < 150.f)
            return true;
    }
    return false;
}

ASoraEnemyController::EMove ASoraEnemyController::WalkTo(ASoraEnemy& Enemy, const FVector& Goal, float Speed, float Acceptance, int32 NowMs)
{
    const FVector Here = Enemy.GetActorLocation();
    if (FVector::Dist2D(Here, Goal) <= Acceptance)
    {
        ClearPath();
        return EMove::Arrived;
    }
    if (!bPathValid || FVector::Dist2D(Goal, PathGoal) > 100.f || NowMs >= RepathAtMs)
    {
        const USoraNavigation* Nav = USoraNavigation::Get(this);
        PathGoal = Goal;
        RepathAtMs = NowMs + SoraEnemyBrain::RepathMs;
        PathIndex = 1;
        bPathValid = Nav && Nav->FindPath(Here, Goal, Enemy, Path);
    }
    FVector Next = Goal;
    if (bPathValid)
    {
        while (PathIndex < Path.Num() - 1 && FVector::Dist2D(Here, Path[PathIndex]) <= 40.f)
            ++PathIndex;
        Next = Path[PathIndex];
        // A partial path stops short of the goal: it cannot be reached from here.
        if (PathIndex == Path.Num() - 1 && FVector::Dist2D(Here, Next) <= 40.f && FVector::Dist2D(Next, Goal) > Acceptance)
        {
            ClearPath();
            return EMove::Blocked;
        }
    }
    FVector Direction = (Next - Here).GetSafeNormal2D();
    if (!bPathValid)
    {
        // Off the mesh: steer straight and sidestep what is ahead, as the first
        // invaders did.
        FHitResult Ahead;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(BotNavigation), false, &Enemy);
        if (GetWorld()->LineTraceSingleByChannel(Ahead, Here, Here + Direction * 180.f, ECC_Visibility, Query) &&
            !Cast<ASoraCharacterBase>(Ahead.GetActor()))
            Direction = FVector(-Direction.Y, Direction.X, 0.f) * (Slot % 2 ? 1.f : -1.f);
    }
    // No progress for two seconds of moving means the goal cannot be reached.
    if (NowMs - LastMovingMs > 100 || FVector::Dist2D(Here, StuckFrom) > 40.f)
    {
        StuckFrom = Here;
        StuckSinceMs = NowMs;
    }
    else if (NowMs - StuckSinceMs > SoraEnemyBrain::StuckMs)
    {
        ClearPath();
        LastMovingMs = MIN_int32;
        return EMove::Blocked;
    }
    LastMovingMs = NowMs;
    Heading = Direction;
    Enemy.AddMovementInput(Direction, Speed);
    return EMove::Moving;
}

void ASoraEnemyController::ClearPath()
{
    Path.Reset();
    PathIndex = 0;
    bPathValid = false;
    RepathAtMs = 0;
}

void ASoraEnemyController::Face(ASoraEnemy& Enemy, const FVector& Direction, float Dt, float Rate) const
{
    const FVector Flat(Direction.X, Direction.Y, 0.f);
    if (!Flat.IsNearlyZero())
        Enemy.SetActorRotation(FMath::RInterpTo(Enemy.GetActorRotation(), Flat.Rotation(), Dt, Rate));
}

void ASoraEnemyController::LookAround(ASoraEnemy& Enemy, float BaseYaw, float Amplitude, float Dt, int32 NowMs) const
{
    // A slow sweep on a six-second cycle, offset by slot.
    const float Phase = 2.f * PI * static_cast<float>((NowMs + Slot * 977) % 6000) / 6000.f;
    Enemy.SetActorRotation(FMath::RInterpTo(Enemy.GetActorRotation(), FRotator(0.f, BaseYaw + Amplitude * FMath::Sin(Phase), 0.f), Dt, 3.f));
}

bool ASoraEnemyController::CanSee(const ASoraCharacterBase& Target) const
{
    const ASoraEnemy* Enemy = GetPawn<ASoraEnemy>();
    return Enemy && Stealth::InView(Look(*Enemy, Target));
}

Stealth::FSight ASoraEnemyController::Look(const ASoraEnemy& Enemy, const ASoraCharacterBase& Target) const
{
    const FVector Eye = Enemy.GetActorLocation() + FVector(0.f, 0.f, SoraEnemyBrain::EyeHeight);
    const FVector There = Target.GetActorLocation();
    const FVector Flat(There.X - Eye.X, There.Y - Eye.Y, 0.f);
    Stealth::FSight Sight{};
    Sight.DistanceCm = FMath::RoundToInt32(Flat.Size());
    Sight.FacingMilli = FMath::RoundToInt32(FVector::DotProduct(Enemy.GetActorForwardVector().GetSafeNormal2D(), Flat.GetSafeNormal()) * 1000.f);
    Sight.TargetMoving = Target.GetVelocity().Size2D() > 30.f;
    if (Sight.DistanceCm > Stealth::SightRangeCm || Sight.FacingMilli < Stealth::ViewConeMilli)
        return Sight;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraSight), false, &Enemy);
    for (const float Height : {SoraEnemyBrain::HeadHeight, SoraEnemyBrain::ChestHeight})
    {
        FHitResult Hit;
        GetWorld()->LineTraceSingleByChannel(Hit, Eye, There + FVector(0.f, 0.f, Height), ECC_Visibility, Query);
        if (Hit.GetActor() == &Target)
        {
            Sight.Clear = true;
            break;
        }
    }
    if (Sight.Clear)
        Sight.LightPermille = LightAt(There);
    return Sight;
}

int32 ASoraEnemyController::LightAt(const FVector& Location) const
{
    // The key light's illuminance and every lamp whose reach covers the spot.
    int32 KeyDeciLux = 0;
    int32 Lamps = 0;
    for (TActorIterator<ALight> It(GetWorld()); It; ++It)
    {
        const ULightComponent* Light = It->GetLightComponent();
        if (!Light || !Light->IsVisible())
            continue;
        if (const auto* Lamp = Cast<UPointLightComponent>(Light))
            Lamps += Stealth::LampPermille(FMath::RoundToInt32(FVector::Dist(Location, Lamp->GetComponentLocation())),
                FMath::RoundToInt32(Lamp->AttenuationRadius));
        else if (Light->IsA<UDirectionalLightComponent>())
            KeyDeciLux = FMath::Max(KeyDeciLux, FMath::RoundToInt32(Light->Intensity * 10.f));
    }
    return Stealth::LightPermille(Stealth::AmbientPermille(KeyDeciLux), Lamps);
}

bool ASoraEnemyController::Occluded(const FVector& From, const FVector& To, const AActor* Source) const
{
    // Walls, buildings and cover muffle a noise; bodies do not.
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraHearing), false, GetPawn());
    if (Source)
        Query.AddIgnoredActor(Source);
    FCollisionObjectQueryParams Solid;
    Solid.AddObjectTypesToQuery(ECC_WorldStatic);
    Solid.AddObjectTypesToQuery(ECC_WorldDynamic);
    return GetWorld()->LineTraceTestByObjectType(From + FVector(0.f, 0.f, 30.f), To, Solid, Query);
}

void ASoraEnemyController::DrivePupil(ASoraEnemy& Enemy, ASoraCharacterBase& Target, float Dt)
{
    // The chapter-one drill: face the hero, close to bokken distance around the
    // obstacle ahead, and strike on the pupil's own rhythm.
    FVector Delta = Target.GetActorLocation() - Enemy.GetActorLocation();
    const float Distance = Delta.Size2D();
    Delta.Z = 0.f;
    Enemy.SetActorRotation(FMath::RInterpTo(Enemy.GetActorRotation(), Delta.Rotation(), Dt, 4.f));
    FVector Move = Delta.GetSafeNormal();
    FHitResult Ahead;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BotNavigation), false, &Enemy);
    if (GetWorld()->LineTraceSingleByChannel(Ahead, Enemy.GetActorLocation(), Enemy.GetActorLocation() + Move * 180.f, ECC_Visibility, Query) &&
        Ahead.GetActor() != &Target)
        Move = FVector(-Move.Y, Move.X, 0.f) * (Enemy.EnemySlot() % 2 ? 1.f : -1.f);
    if (!Enemy.IsPupilWindup())
    {
        if (Distance > 160.f)
            Enemy.AddMovementInput(Move, .55f);
        else
            Enemy.AddMovementInput(Enemy.GetActorRightVector(), FMath::Sin(Enemy.GetLifeTime() + Enemy.EnemySlot()) * .2f);
    }
    Enemy.PupilAttack(Target, Distance);
}

void ASoraEnemyController::DriveCollector(ASoraBoss& Boss, ASoraCharacterBase& Target, float Dt)
{
    // Fixed attack order, locked aim, explicit warning, and recovery make the
    // offline encounter readable. No random damage or hidden hit timestamp.
    if (Boss.UpdateAttack(Dt, Target))
        return;
    FVector Delta = Target.GetActorLocation() - Boss.GetActorLocation();
    Delta.Z = 0.f;
    const float Distance = Delta.Size2D();
    if (Distance > 740.f)
    {
        const FVector Move = Delta.GetSafeNormal2D();
        Boss.SetActorRotation(FMath::RInterpTo(Boss.GetActorRotation(), Move.Rotation(), Dt, 3.f));
        Boss.AddMovementInput(Move, .72f);
        return;
    }
    Boss.BeginAttack(Distance, Delta);
}
