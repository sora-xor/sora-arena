#include "SoraEnemyController.h"
#include "SoraFoundryFurnace.h"
#include "Combat/SoraEnemyCatalog.h"
#include "Combat/SoraStealth.h"
#include "SoraBoss.h"
#include "SoraCampaignDirector.h"
#include "SoraGameMode.h"
#include "SoraCatalog.h"
#include "SoraCompanion.h"
#include "SoraEnemy.h"
#include "SoraFieldcraft.h"
#include "SoraFieldcraftRules.h"
#include "SoraPressRules.h"
#include "SoraGameEvents.h"
#include "SoraHistoricalArms.h"
#include "SoraPlayerCharacter.h"
#include "World/SoraNavigation.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

namespace Stealth = SoraStealthRules;

namespace SoraEnemyBrain
{
// The eye sits where the opponents' attacks trace from. The hero is looked for
// at his head, chest and hips, placed on his capsule so a crouch lowers them.
constexpr float EyeHeight = 50.f;
constexpr float BodySamples[] = {.75f, .2f, -.4f};
// Movement input scales: a patrol walk, a careful approach, a hunter's pace,
// combat repositioning (the first invaders' pace) and a retreat.
constexpr float PatrolSpeed = .35f;
constexpr float InvestigateSpeed = Stealth::InvestigatePacePermille / 1000.f;
constexpr float HuntSpeed = .6f;
constexpr float CombatSpeed = .55f;
constexpr float RetreatSpeed = .75f;
constexpr int32 RepathMs = 500;
constexpr int32 SearchPauseMs = 800;
// Blade footwork takes over from pathing within this distance of a seen hero.
constexpr float FootworkRangeCm = 400.f;
// Without cover, a ranged opponent closes to this range and sidesteps there.
constexpr float OpenFireRangeCm = 650.f;
// A melee opponent holds its ground once the hero is this far inside its reach.
constexpr float HoldReachShare = .8f;
// An auditor on the run shouts again this often.
constexpr int32 AlarmRepeatMs = 2000;
// A body is looked at a little above the floor it lies on.
constexpr float BodySightHeight = 20.f;
// In a fight an opponent turns on a companion this near, and clearly nearer than the hero.
constexpr float QuarryCm = 1500.f;
constexpr float QuarryShare = .7f;

const TCHAR* StateName(SoraStealthRules::EState State)
{
    switch (State)
    {
    case SoraStealthRules::EState::Unaware: return TEXT("unaware");
    case SoraStealthRules::EState::Suspicious: return TEXT("suspicious");
    case SoraStealthRules::EState::Alert: return TEXT("alert");
    case SoraStealthRules::EState::Search: return TEXT("search");
    case SoraStealthRules::EState::Combat: return TEXT("combat");
    case SoraStealthRules::EState::Retreat: return TEXT("retreat");
    }
    return TEXT("unaware");
}

bool IsShooter(const FSoraEnemyArchetype* Kind)
{
    return Kind && (Kind->Behavior == ESoraEnemyBehavior::Rifle || Kind->Behavior == ESoraEnemyBehavior::Marksman ||
        Kind->Behavior == ESoraEnemyBehavior::Grenadier);
}
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
    ThinkClock.Reset();
    Listen(true);
}

void ASoraEnemyController::OnUnPossess()
{
    ThinkClock.Reset();
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
    HearNoise(Kind, Event.Origin, Shooter->IsEnemy() ? Event.End : Event.Origin, Shooter);
}

void ASoraEnemyController::OnDetonated(const FSoraDetonatedEvent& Event)
{
    HearNoise(Stealth::ENoise::Explosion, Event.Location, Event.Location, Event.Instigator);
}

void ASoraEnemyController::OnMeleeCommitted(const FSoraMeleeCommittedEvent& Event)
{
    // Only the hero's blade; an ally's swing is already its own fight.
    const auto* Attacker = Cast<ASoraCharacterBase>(Event.Attacker);
    if (!Attacker || Attacker->IsEnemy())
        return;
    HearNoise(Stealth::ENoise::Melee, Attacker->GetActorLocation(), Attacker->GetActorLocation(), Attacker);
}

void ASoraEnemyController::HearCallout(const FVector& Caller, const FVector& Where, bool bAlarm)
{
    Heard.Add({Stealth::ENoise::Callout, Caller, Where, nullptr, bAlarm});
}

void ASoraEnemyController::Rouse(const FVector& Where)
{
    const Stealth::EState Previous = Mind.State;
    Mind = Stealth::Enter(Mind, Stealth::EState::Alert, Stealth::AwarenessMax);
    LastKnown = Where;
    if (ASoraEnemy* Enemy = GetPawn<ASoraEnemy>())
        Enter(*Enemy, Previous, WorldMs());
}

void ASoraEnemyController::HearNoise(Stealth::ENoise Kind, const FVector& Origin, const FVector& Evidence, const AActor* Source,
    int32 LoudnessPermille)
{
    // Queue the emitted loudness, never the later listener's stamp phase.
    if(Cast<ASoraPlayerCharacter>(Source)||(Source&&Cast<ASoraPlayerCharacter>(Source->GetInstigator())))
        if(const auto* Craft=USoraFieldcraft::Get(this))
            LoudnessPermille=SoraPressRules::Scale(LoudnessPermille,Craft->PressNoisePermille(Origin));
    Heard.Add({Kind, Origin, Evidence, Source, false, LoudnessPermille});
}

void ASoraEnemyController::HearAlarm(const FVector& Where)
{
    const Stealth::EState Previous = Mind.State;
    Mind = Stealth::Alarmed(Mind);
    if (Mind.State == Previous)
        return;
    LastKnown = Where;
    if (ASoraEnemy* Enemy = GetPawn<ASoraEnemy>())
        Enter(*Enemy, Previous, WorldMs());
}

void ASoraEnemyController::LearnOfBody(const FVector& Where, bool bFinder)
{
    ASoraEnemy* Enemy = GetPawn<ASoraEnemy>();
    const Stealth::EState Previous = Mind.State;
    Mind = Stealth::BodyFound(Mind);
    // The finder searches around the body even if it was already searching.
    if (bFinder && Mind.State == Stealth::EState::Search)
        Mind = Stealth::Enter(Mind, Stealth::EState::Search, 0);
    else if (Mind.State == Previous)
        return;
    LastKnown = bFinder || !Enemy ? Where : Enemy->GetActorLocation();
    if (Enemy)
        Enter(*Enemy, Previous, WorldMs());
}

void ASoraEnemyController::EnterZone(bool bCarriedOver)
{
    ASoraEnemy* Enemy = GetPawn<ASoraEnemy>();
    if (bHunting || !Enemy || !Enemy->Archetype() || Mind.State != Stealth::EState::Unaware)
        return;
    const Stealth::EState Previous = Mind.State;
    Mind = Stealth::Posted(bCarriedOver);
    if (Mind.State != Previous)
        Enter(*Enemy, Previous, WorldMs());
}

void ASoraEnemyController::NoticeTampering(const FVector& Where)
{
    auto* Enemy=GetPawn<ASoraEnemy>();
    if(!Enemy||!Enemy->IsAlive()||bHunting||
        (Mind.State!=Stealth::EState::Unaware&&Mind.State!=Stealth::EState::Suspicious)) return;
    const auto Previous=Mind.State;
    Mind=Stealth::Disturbed(Mind,Vigilance()); LastKnown=Where; ClearErrand();
    Enter(*Enemy,Previous,WorldMs());
}

void ASoraEnemyController::SensorEvidence(const FVector& Where,int32 SuspicionPermille)
{
    auto* Enemy=GetPawn<ASoraEnemy>();
    if(!Enemy||!Enemy->IsAlive()||bHunting||SuspicionPermille<=0) return;
    const auto Previous=Mind.State;
    Stealth::FSenses Senses{};
    Senses.NoiseImpulse=FMath::Clamp(SuspicionPermille,0,1000);
    Mind=Stealth::Step(Mind,Senses,0,Vigilance());
    LastKnown=Where;ClearErrand();
    if(Mind.State!=Previous) Enter(*Enemy,Previous,WorldMs());
}

Stealth::FVigilance ASoraEnemyController::Vigilance() const
{
    // A hunting wave never obeys a zone.
    const USoraStealth* Zone = bHunting ? nullptr : USoraStealth::Get(this);
    return Zone ? Zone->Vigilance() : Stealth::Watchful();
}

int32 ASoraEnemyController::MeterPermille() const
{
    return Stealth::Meter(Mind, Vigilance());
}

void ASoraEnemyController::Prepare(bool bHunt)
{
    ThinkClock.Reset();
    PatrolClock.Reset(); PatrolLoop={};
    const ASoraEnemy* Enemy = GetPawn<ASoraEnemy>();
    bHunting = bHunt;
    Mind = bHunt ? Stealth::Hunting() : Stealth::Calm();
    Slot = Enemy ? Enemy->EnemySlot() : 0;
    // Rifles cover or flank by slot; the other shooters always take cover.
    const FSoraEnemyArchetype* Kind = Enemy ? Enemy->Archetype() : nullptr;
    Role = !Kind || Kind->IsMelee() ? Stealth::ERole::Blade :
        Kind->Behavior == ESoraEnemyBehavior::Rifle ? Stealth::Role(Slot, false) : Stealth::ERole::CoverShooter;
    Post = Enemy ? Enemy->GetActorLocation() : FVector::ZeroVector;
    PostYaw = Enemy ? Enemy->GetActorRotation().Yaw : 0.f;
    LastKnown = Post;
    Route = FSoraPatrolRoute();
    RouteIndex = 0;
    RouteStep = 1;
    bPaused = false;
    PointPauseRemainingMs = 0;
    SearchPoints.Reset();
    Heard.Reset();
    bGoalDone = false;
    bHasPosition = false;
    bCanPeek = false;
    bAvoidSpot = false;
    NextAlarmMs = 0;
    Lectern = INDEX_NONE;
    bLecternUnreachable = false;
    bAlarmRaised = false;
    bSeesHero = false;
    BodyEvidence = 0;
    BodyInView.Reset();
    bErrand = false;
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
    // A guard posted into an open zone takes the zone's start.
    if (const USoraStealth* Zone = USoraStealth::Get(this); Zone && Zone->IsZoneActive())
        Mind = Stealth::Posted(Zone->Zone().bCarriedOver);
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
    if (!Enemy->IsActorTickEnabled() || !Enemy->CanPlay() || Enemy->IsSeized() || !Target || !Target->IsAlive())
    {
        Heard.Reset();
        bSeesHero = false;
        return;
    }
    if(Enemy->IsFreed())
    {
        Heard.Reset();bSeesHero=false;
        FVector Goal;
        if(auto* Craft=USoraFieldcraft::Get(this);Craft&&Craft->WardKidobanDeparture(*Enemy,Goal))
        {
            // The gatekeeper walks clear of the narrow wicket after opening
            // it, retaining normal body collision and ordinary movement.
            if(auto* Nav=USoraNavigation::Get(this))Nav->Settle();
            if(WalkTo(*Enemy,Goal,SoraEnemyBrain::PatrolSpeed,20.f,WorldMs())==EMove::Moving)
                Face(*Enemy,Goal-Enemy->GetActorLocation(),Dt,5.f);
        }
        return;
    }
    if (auto* Boss = Cast<ASoraBoss>(Enemy))
    {
        DriveBoss(*Boss, *Target, Dt);
        return;
    }
    if (Enemy->IsDojoPupil())
    {
        DrivePupil(*Enemy, *Target, Dt);
        return;
    }
    if (DriveWorkshopDefense(*Enemy,*Target,Dt)||DriveTenementDefense(*Enemy,*Target,Dt)||DriveLift(*Enemy,*Target,Dt)||DriveSpireFlight(*Enemy,*Target,Dt)) return;
    if (Enemy->Archetype())
        Think(*Enemy, *Target, Dt);
}

void ASoraEnemyController::Think(ASoraEnemy& Enemy, ASoraCharacterBase& Target, float Dt)
{
    // Every query this frame sees the same, complete navigation mesh.
    if (USoraNavigation* Nav = USoraNavigation::Get(this))
        Nav->Settle();
    const int32 NowMs = WorldMs();
    const int32 DtMs = ThinkClock.Advance(Dt);
    const FVector Here = Enemy.GetActorLocation();
    const FVector Ear = Enemy.SenseOrigin();
    const FVector There = Target.GetActorLocation();
    const Stealth::FPerception& Perception = Enemy.Perception();
    USoraStealth* Zone = bHunting ? nullptr : USoraStealth::Get(this);
    const Stealth::FVigilance Vigil = Vigilance();

    Stealth::FSenses Senses{};
    const Stealth::FSight Sight = Look(Enemy, Target);
    const bool bSees = Stealth::InView(Sight, Perception);
    bSeesHero = bSees;
    Senses.SightGain = Stealth::SightGainPerSecond(Sight, Perception);
    bool bEvidence = bSees;
    FVector Evidence = There;

    // The hero's footsteps are heard for as long as they last: softer when he
    // crouch-walks, louder or silent on the zone's floors.
    const UCharacterMovementComponent* Walk = Target.GetCharacterMovement();
    const auto* WaterCraft=USoraFieldcraft::Get(&Target);
    const FVector StepFeet=There-FVector(0.f,0.f,Target.GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    const bool bMoatStroke=WaterCraft&&WaterCraft->MoatFootstepPermille(StepFeet)>=0;
    const bool bFloodStroke=WaterCraft&&(WaterCraft->FloodFootstepPermille(StepFeet)>=0||bMoatStroke);
    if (Target.GetVelocity().Size2D() > 150.f && Walk && (Walk->IsMovingOnGround()||bFloodStroke))
    {
        const auto* Hero = Cast<ASoraPlayerCharacter>(&Target);
        const Stealth::ENoise Steps = Stealth::Steps(Hero && Hero->IsSprinting(),
            Target.IsCrouched()&&!bMoatStroke ? Stealth::EStance::Crouched : Stealth::EStance::Standing);
        const FVector Feet = There - FVector(0.f, 0.f, Target.GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
        const int32 Loudness = Zone && Zone->IsZoneActive() ? Stealth::StepLoudnessPermille(Steps, Zone->SurfaceAt(Feet)) : 1000;
        const int32 Distance = FMath::RoundToInt32(FVector::Dist(There, Ear));
        if (Distance <= Stealth::HeardRadiusCm(Steps, Perception, Loudness))
        {
            const bool Blocked=Occluded(There,Ear,&Target);
            const int32 Open=Stealth::HeardPermille(Steps,Distance,Blocked,Perception,Loudness);
            const int32 MaskedMs=Hero&&WaterCraft?WaterCraft->PressMaskedMs(Feet,DtMs):0;
            const int32 Quiet=Stealth::HeardPermille(Steps,Distance,Blocked,Perception,
                SoraPressRules::Scale(Loudness,SoraPressRules::NoisePermille));
            // Integrate the two audible states, not an average radius: a
            // short stamp cannot extend quiet footsteps to a farther guard.
            Senses.NoisePerSecond=DtMs>0?int32((int64(Open)*(DtMs-MaskedMs)+int64(Quiet)*MaskedMs)/DtMs):Open;
        }
        bEvidence |= Senses.NoisePerSecond > 0;
    }
    // The loudest single noise since the last tick.
    bool bLure = false;
    for (const FNoise& Noise : Heard)
    {
        // The alarm's sender chose who it reaches; it arrives at full urgency.
        const int32 Distance = FMath::RoundToInt32(FVector::Dist(Noise.Origin, Ear));
        if (!Noise.bAlarm && Distance > Stealth::HeardRadiusCm(Noise.Kind, Perception, Noise.LoudnessPermille))
            continue;
        int32 Level = Noise.bAlarm ? Stealth::NoisePeakPermille(Stealth::ENoise::Callout) :
            Stealth::HeardPermille(Noise.Kind, Distance, Occluded(Noise.Origin, Ear, Noise.Source.Get()), Perception, Noise.LoudnessPermille);
        // A lure (a thrown stone, a float line) sends a calm guard to look but
        // never tells it the hero is there; one already hunting pays it no mind.
        if (Noise.Kind == Stealth::ENoise::Lure)
            Level = Mind.State == Stealth::EState::Unaware || Mind.State == Stealth::EState::Suspicious
                ? SoraFieldcraftRules::LureImpulsePermille(Level, Mind.Awareness / Stealth::AwarenessScale)
                : Mind.State == Stealth::EState::Search
                ? FMath::Clamp(Level, 0, FMath::Max(0, (Vigil.SuspicionThreshold - Mind.Awareness) / Stealth::AwarenessScale - 1))
                : 0;
        if (Level > Senses.NoiseImpulse)
        {
            Senses.NoiseImpulse = Level;
            bLure = Noise.Kind == Stealth::ENoise::Lure;
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
    Senses.CanRetreat = Stealth::CanRetreat(Role) && SoraEnemyBrain::IsShooter(Enemy.Archetype());
    // Even an alarmist only goes to look at where a stone fell.
    Senses.Alarmist = Perception.Alarmist && !(bLure && !bSees);
    const Stealth::EState Previous = Mind.State;
    Mind = Stealth::Step(Mind, Senses, DtMs, Vigil);
    if (Mind.State != Previous)
        Enter(Enemy, Previous, NowMs);
    // A calm guard in a zone may come upon a body.
    if (Zone && Zone->IsZoneActive() && Stealth::IsCalm(Mind.State))
        LookForBodies(Enemy, DtMs);
    else
        BodyEvidence = 0;
    // A staggered opponent still notices, but neither moves nor strikes.
    if (Enemy.IsStaggered())
        return;
    // Perception still updates, but this committed attack owns its swept
    // descent, low recovery and return to the original flight plane.
    if (Enemy.OwnsLandingDroneMotion())
        return;
    if(auto* Craft=USoraFieldcraft::Get(this);Craft&&Craft->DriveClimbSentry(Enemy,Dt)) return;
    if(auto* Craft=USoraFieldcraft::Get(this);Craft&&Craft->DriveMoatGuard(Enemy,Dt,bGoalDone)) return;
    // A scripted errand takes it where the beat sends it instead.
    if (RunErrand(Enemy, Dt, NowMs))
        return;
    if (DriveSpireAlarm(Enemy,Dt,NowMs))
        return;
    // Only this authored defense gives grenadiers a structural quarry.
    // Normal perception/telegraph/range/cover/projectile code remains in Fight.
    if(Enemy.ArchetypeId()==TEXT("grenadier"))
        if(const auto* M=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode()); M&&M->Campaign())
            if(auto* Furnace=M->Campaign()->FoundryFurnace(); Furnace&&Furnace->IsAlive())
            {
                Fight(Enemy,*Furnace,CanSee(*Furnace),Dt,NowMs);
                return;
            }
    if(DriveHorseShell(Enemy,Dt,NowMs)) return;
    // In a fight it may turn on someone beside the hero: the nearest companion
    // it can see that stands clearly nearer than he does.
    if (Mind.State == Stealth::EState::Combat)
    {
        const float HeroDistance = FVector::Dist2D(Here, There);
        ASoraCompanion* Quarry = nullptr;
        float Best = FMath::Min(SoraEnemyBrain::QuarryCm, HeroDistance * SoraEnemyBrain::QuarryShare);
        for (TActorIterator<ASoraCompanion> It(GetWorld()); It; ++It)
        {
            const float Distance = FVector::Dist2D(Here, It->GetActorLocation());
            if (Distance < Best && It->IsAlive() && It->IsExposed(FMath::RoundToInt32(Distance)) && CanSee(**It))
            {
                Best = Distance;
                Quarry = *It;
            }
        }
        if (Quarry)
        {
            Act(Enemy, *Quarry, true, Dt, NowMs);
            return;
        }
    }
    Act(Enemy, Target, bSees, Dt, NowMs);
}

void ASoraEnemyController::SetErrand(const FVector& Goal, const FVector& Facing, float Pace, int32 DurationMs, bool bWhileCalm,
    bool bThreeDimensional,float AcceptanceCm,bool bSupportedSteps)
{
    bErrand = true;
    bErrandWhileCalm = bWhileCalm;
    bErrandReached = false;
    bErrand3D = bThreeDimensional;
    bErrandSupportedSteps = bSupportedSteps;
    ErrandAcceptanceCm = FMath::Max(1.f,AcceptanceCm);
    ErrandGoal = Goal;
    ErrandFacing = Facing.IsNearlyZero() ? FVector::ForwardVector : Facing.GetSafeNormal2D();
    ErrandPace = FMath::Clamp(Pace, .1f, 1.f);
    ErrandUntilMs = DurationMs > 0 ? WorldMs() + DurationMs : 0;
}

bool ASoraEnemyController::RunErrand(ASoraEnemy& Enemy, float Dt, int32 NowMs)
{
    if (!bErrand)
        return false;
    // A calm errand (a guard drawn to a bell) ends once it knows of the hero, or at its time.
    if ((bErrandWhileCalm && !Stealth::IsCalm(Mind.State)) || (ErrandUntilMs > 0 && NowMs >= ErrandUntilMs))
    {
        bErrand = false;
        return false;
    }
    const EMove Move=bErrandSupportedSteps
        ?WalkSupportedSegment(Enemy,ErrandGoal,ErrandPace,ErrandAcceptanceCm,true)
        :WalkTo(Enemy,ErrandGoal,ErrandPace,ErrandAcceptanceCm,NowMs);
    bErrandReached=bErrand3D?Move==EMove::Arrived:Move!=EMove::Moving;
    // Once a flying worker is over its station, keep its tool aimed there
    // while following the station's changing Z. Vertical travel has no yaw.
    const bool bAtStation=bErrand3D&&FVector::Dist2D(Enemy.GetActorLocation(),ErrandGoal)<=ErrandAcceptanceCm;
    Face(Enemy, bErrandReached||bAtStation ? ErrandFacing : Heading, Dt, 5.f);
    if (bErrandReached && bErrandWhileCalm)
        LookAround(Enemy, ErrandFacing.Rotation().Yaw, 40.f, Dt, NowMs);
    return true;
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
    AnnounceState(Enemy);
    if (USoraStealth* Zone = bHunting ? nullptr : USoraStealth::Get(this))
        Zone->NoteState(Enemy, Previous, Mind.State);
    // An opponent that has just found the hero shouts to the allies near it.
    const bool bWasCalm = Previous == Stealth::EState::Unaware || Previous == Stealth::EState::Suspicious ||
        Previous == Stealth::EState::Search;
    if (bWasCalm && (Mind.State == Stealth::EState::Alert || Mind.State == Stealth::EState::Combat))
        CallOut(Enemy);
}

void ASoraEnemyController::AnnounceState(const ASoraEnemy& Enemy) const
{
    if (USoraGameEvents* Bus = USoraGameEvents::Get(this))
    {
        FSoraEnemyCueEvent Event;
        Event.Enemy = const_cast<ASoraEnemy*>(&Enemy); Event.Archetype = Enemy.ArchetypeId();
        Event.Cue = ESoraEnemyCue::AlertState; Event.Detail = SoraEnemyBrain::StateName(Mind.State);
        Bus->OnEnemyCue.Broadcast(Event);
    }
}

void ASoraEnemyController::CallOut(const ASoraEnemy& Enemy) const
{
    // An auditor's alarm carries farther than a trooper's shout, and through
    // walls; a shout carries half as far through them. Where the zone has
    // alarm lecterns, the auditor only shouts: the alarm is raised at a lectern.
    const USoraStealth* Zone = bHunting ? nullptr : USoraStealth::Get(this);
    const bool bLecterns = Zone && Zone->IsZoneActive() && !Zone->AlarmPoints().IsEmpty();
    const int32 Alarm = Enemy.Archetype() && !bLecterns ? Enemy.Archetype()->AlarmRadiusCm : 0;
    const auto* Mode=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    const bool bRelayDrone = Enemy.ArchetypeId() == TEXT("drone") && Mode && Mode->bCampaign &&
        Mode->Campaign() && Mode->Campaign()->ChapterId == 5;
    const bool bLocalDrone = bRelayDrone && Mode->Campaign()->RelayOffline();
    for (TActorIterator<ASoraEnemyController> It(GetWorld()); It; ++It)
    {
        const APawn* Ally = It->GetPawn();
        if (*It == this || !Ally)
            continue;
        if (bRelayDrone)
        {
            // The chapter relay carries a radio mark, independent of hearing
            // and walls. Once disabled, only allies within twenty metres can
            // receive the drone's last observation directly.
            if (!bLocalDrone || FVector::DistSquared(Ally->GetActorLocation(), Enemy.GetActorLocation()) <= FMath::Square(2000.f))
                It->HearCallout(Enemy.GetActorLocation(), LastKnown, true);
            continue;
        }
        const int32 Distance = FMath::RoundToInt32(FVector::Dist(Ally->GetActorLocation(), Enemy.GetActorLocation()));
        if (Distance > FMath::Max(Alarm, Stealth::NoiseRadiusCm(Stealth::ENoise::Callout)))
            continue;
        const bool bMuffled = Alarm <= 0 && Occluded(Enemy.GetActorLocation(), Ally->GetActorLocation(), Ally);
        if (Stealth::CalloutReaches(Distance, bMuffled, Alarm))
            It->HearCallout(Enemy.GetActorLocation(), LastKnown, Alarm > 0);
    }
}

void ASoraEnemyController::Act(ASoraEnemy& Enemy, ASoraCharacterBase& Target, bool bSees, float Dt, int32 NowMs)
{
    // Weak in a fight, an auditor that knows of the hero runs and raises the alarm.
    if (Enemy.Archetype()->Behavior == ESoraEnemyBehavior::Auditor &&
        (Mind.State == Stealth::EState::Alert || Mind.State == Stealth::EState::Combat))
    {
        AlarmRun(Enemy, Target, Dt, NowMs);
        return;
    }
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
    if(SoraPatrolRules::Valid(Route.Points.Num(),Route.PeriodMs,Route.PauseMs))
    { ScheduledPatrol(Enemy,Dt,NowMs); return; }
    if (Route.Points.Num() <= 1)
    {
        // A guard post: return to it, then watch its arc: the sweep the
        // chapter authors for it, turning about as often as it says, or the
        // brain's own look about.
        if (WalkTo(Enemy, Post, SoraEnemyBrain::PatrolSpeed, 60.f, NowMs,Route.bThreeDimensional) == EMove::Moving)
            Face(Enemy, Heading, Dt, 5.f);
        else if (Enemy.PostTurnMs() > 0)
            Face(Enemy, FRotator(0.f, PostYaw + (NowMs / Enemy.PostTurnMs() % 2) * 180.f, 0.f).Vector(), Dt, 3.f);
        else if (Enemy.PostScanMs() > 0)
            LookAround(Enemy, PostYaw, Enemy.PostScanDegrees() * .5f, Dt, NowMs, Enemy.PostScanMs());
        else
            LookAround(Enemy, PostYaw, 25.f, Dt, NowMs);
        return;
    }
    if (bPaused)
    {
        const bool AuthoredDwell=Route.PointPauseMs.IsValidIndex(RouteIndex);
        if(AuthoredDwell&&!Route.PauseFacing.IsNearlyZero()) Face(Enemy,Route.PauseFacing,Dt,5.f);
        else LookAround(Enemy, PauseYaw, 35.f, Dt, NowMs);
        if(AuthoredDwell) PointPauseRemainingMs=FMath::Max(0.0,PointPauseRemainingMs-double(Dt)*1000.0);
        if (AuthoredDwell?PointPauseRemainingMs>0:NowMs<PauseUntilMs)
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
    const EMove Move=Route.bSupportedSegments
        ?WalkSupportedSegment(Enemy,Route.Points[RouteIndex],SoraEnemyBrain::PatrolSpeed,20.f,Route.bSupportedSteps)
        :WalkTo(Enemy,Route.Points[RouteIndex],SoraEnemyBrain::PatrolSpeed,70.f,NowMs,Route.bThreeDimensional);
    if(Move==EMove::Blocked&&(Route.bSupportedSegments||!Route.PointPauseMs.IsEmpty())) return;
    if (Move != EMove::Moving)
    {
        bPaused = true;
        PauseUntilMs = NowMs + Route.PauseMs;
        PointPauseRemainingMs=Route.PointPauseMs.IsValidIndex(RouteIndex)?FMath::Max(0,Route.PointPauseMs[RouteIndex]):0;
        PauseYaw = Enemy.GetActorRotation().Yaw;
        return;
    }
    Face(Enemy, Heading, Dt, 5.f);
}

ASoraEnemyController::EMove ASoraEnemyController::WalkSupportedSegment(ASoraEnemy& Enemy,const FVector& Goal,float Speed,float Acceptance,bool bSteps)
{
    auto* Move=Enemy.GetCharacterMovement();
    const FVector Here=Enemy.GetActorLocation();
    const auto* Capsule=Enemy.GetCapsuleComponent();
    const float Half=Capsule->GetScaledCapsuleHalfHeight();
    const auto Stop=[&](EMove Result) { Move->StopMovementImmediately();return Result; };
    // A short descent can become airborne. Let gravity finish it; resetting
    // velocity here would repeatedly cancel the fall instead of landing.
    if(!Move->IsMovingOnGround()) return bSteps?EMove::Moving:Stop(EMove::Blocked);
    if(!bSteps&&FMath::Abs(Here.Z-Goal.Z)>15.f) return Stop(EMove::Blocked);
    // A 70 cm arrival radius cuts the inside of a 120 cm corner. Twenty
    // centimetres keeps the ordinary 34 cm capsule inside either strip.
    // A capsule straddling a riser can sit above the tread beneath its
    // centre. Accept at most one ordinary step vertically, while keeping
    // the tight horizontal corner tolerance and requiring grounded feet.
    if(FVector::Dist2D(Here,Goal)<=Acceptance&&(!bSteps||FMath::Abs(Here.Z-Goal.Z)<=Move->MaxStepHeight+2.f))
        return Stop(EMove::Arrived);
    const FVector Direction=(Goal-Here).GetSafeNormal2D();
    const FVector Next=Here+Direction*FMath::Min(bSteps?12.f:60.f,float(FVector::Dist2D(Here,Goal)));
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SupportedPatrol),false,&Enemy);
    FHitResult Hit;
    // Flat segments can preflight a level capsule sweep. On stairs the real
    // CharacterMovement sweep and StepUp must resolve each riser; a level
    // preflight would reject every step before the capsule could climb it.
    if(!bSteps&&GetWorld()->SweepSingleByChannel(Hit,Here,Next,FQuat::Identity,ECC_Pawn,
        FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),Half),Query)) return Stop(EMove::Blocked);
    const FVector Foot=Next-FVector(0,0,Half);
    const float StepLimit=bSteps?Move->MaxStepHeight+2.f:30.f;
    if(!GetWorld()->LineTraceSingleByChannel(Hit,Foot+FVector(0,0,StepLimit),Foot-FVector(0,0,StepLimit),ECC_Visibility,Query)||
        Hit.ImpactNormal.Z<Move->GetWalkableFloorZ()||
        (bSteps?FMath::Abs(Hit.ImpactPoint.Z-Foot.Z)>StepLimit:FMath::Abs(Hit.ImpactPoint.Z-(Goal.Z-Half-2.f))>5.f))
    {
        if(!bSteps) return Stop(EMove::Blocked);
        // At the foot of a stair the rounded capsule can still rest on a
        // tread behind its centre. A point ray ahead then sees only the
        // lower floor beyond step height, even though the actual capsule
        // has walkable support. Use CharacterMovement's bounded capsule
        // floor query before rejecting that descent; never invent support.
        FFindFloorResult Floor;
        Move->ComputeFloorDist(Next,StepLimit,StepLimit,Floor,Capsule->GetScaledCapsuleRadius());
        if(!Floor.IsWalkableFloor()) return Stop(EMove::Blocked);
    }
    Heading=Direction;
    Enemy.AddMovementInput(Direction,Speed);
    return EMove::Moving;
}

void ASoraEnemyController::ScheduledPatrol(ASoraEnemy& Enemy,float Dt,int32 NowMs)
{
    const int32 Count=Route.Points.Num();
    const FVector Goal=Route.Points[SoraPatrolRules::Target(PatrolLoop,Count)];
    const FVector Here=Enemy.GetActorLocation();
    float Distance=FVector::Dist(Here,Goal);
    // Follow the remaining navigation path, not a straight-line estimate
    // through machinery. A newly selected goal gets its path in WalkTo.
    if(!Enemy.IsFlying()&&!Route.bSupportedSegments&&bPathValid&&PathGoal.Equals(Goal,1.f)&&Path.IsValidIndex(PathIndex))
    {
        Distance=FVector::Dist(Here,Path[PathIndex]);
        for(int I=PathIndex+1;I<Path.Num();++I) Distance+=FVector::Dist(Path[I-1],Path[I]);
    }
    const long long Until=SoraPatrolRules::Deadline(PatrolLoop,Count,Route.PeriodMs)-PatrolLoop.ElapsedMs-Route.PauseMs;
    const float Seconds=FMath::Max(.1f,float(Until)/1000.f);
    const float FullSpeed=FMath::Max(1.f,float(Enemy.Archetype()->SpeedCmPerSecond));
    const float Pace=FMath::Clamp(Distance/(Seconds*FullSpeed),.1f,1.f);
    EMove Move;
    if(Route.bDirectFlightSegments&&Enemy.IsFlying())
    {
        // The authored corridor already avoids the room's structure. Native
        // character movement still sweeps the body, so an added obstruction
        // holds the patrol here instead of advancing a visit on the clock.
        if(Distance<=20.f)
        { Enemy.GetCharacterMovement()->StopMovementImmediately();Move=EMove::Arrived; }
        else
        { Heading=(Goal-Here).GetSafeNormal();Enemy.AddMovementInput(Heading,Pace);Move=EMove::Moving; }
    }
    else if(Route.bSupportedSegments)
        Move=WalkSupportedSegment(Enemy,Goal,Pace,20.f,Route.bSupportedSteps);
    else Move=WalkTo(Enemy,Goal,Pace,70.f,NowMs,Route.bThreeDimensional);
    if(Move==EMove::Arrived&&!PatrolLoop.Arrived)
        PauseYaw=Route.PauseFacing.IsNearlyZero()?Enemy.GetActorRotation().Yaw:Route.PauseFacing.Rotation().Yaw;
    // Actual arrival is required at the scheduled release. Blocked does not
    // advance; the late flag survives even if the obstruction clears later.
    const int32 PreviousCycles=PatrolLoop.Cycles;
    SoraPatrolRules::Step(PatrolLoop,Count,Route.PeriodMs,PatrolClock.Advance(Dt),Move==EMove::Arrived);
    if(PatrolLoop.Cycles!=PreviousCycles&&!Route.AlternatePoints.IsEmpty()&&
        SoraPatrolRules::Valid(Route.AlternatePoints.Num(),Route.PeriodMs,Route.PauseMs)&&
        Route.Points[0].Equals(Route.AlternatePoints[0],1.f))
    {
        Swap(Route.Points,Route.AlternatePoints);
        PatrolLoop.Visited=1u;
        ClearPath();
    }
    if(Move==EMove::Arrived) LookAround(Enemy,PauseYaw,20.f,Dt,NowMs);
    else Face(Enemy,Heading,Dt,5.f);
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

bool ASoraEnemyController::DriveHorseShell(ASoraEnemy& Enemy,float Dt,int32 NowMs)
{
    if(!Enemy.HasHorseShellAssignment()) return false;
    const auto* M=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    FVector Landing;
    auto* Target=M&&M->Campaign()?M->Campaign()->HorseShellQuarry(Enemy,Landing):nullptr;
    if(!Target||Enemy.IsWindingUp()||Enemy.IsTurnLocked())
    { ClearPath(); Enemy.GetCharacterMovement()->StopMovementImmediately(); return true; }
    const FVector Here=Enemy.GetActorLocation();
    auto* Hero=M->Hero();
    // The existing companion-quarry thresholds also make this shell baitable.
    if(Hero&&Hero->IsAlive()&&CanSee(*Hero)&&FVector::Dist2D(Here,Hero->GetActorLocation())<
       FMath::Min(SoraEnemyBrain::QuarryCm,FVector::Dist2D(Here,Landing)*SoraEnemyBrain::QuarryShare))
    {
        Target=Hero;
        Landing=Hero->GetActorLocation()-FVector(0,0,Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    }
    const FVector Delta=(Landing-Here)*FVector(1,1,0);
    const float Distance=Delta.Size();
    Face(Enemy,Delta,Dt,4.f);
    const float Standoff=Enemy.Archetype()->KeepDistanceCm;
    const bool Clear=!Occluded(Here+FVector(0,0,SoraEnemyBrain::EyeHeight-30),Target->GetActorLocation(),Target);
    if(Distance>=Standoff&&Clear&&Enemy.TryHorseShell(*Target,Landing))
    { ClearPath(); Enemy.GetCharacterMovement()->StopMovementImmediately(); return true; }
    if(Distance<Standoff||Distance>SoraHorseShellRules::MaxRangeCm||!Clear)
        WalkTo(Enemy,Landing-Delta.GetSafeNormal()*Standoff,SoraEnemyBrain::CombatSpeed,60.f,NowMs);
    else
    { ClearPath(); Enemy.GetCharacterMovement()->StopMovementImmediately(); }
    return true;
}

void ASoraEnemyController::Fight(ASoraEnemy& Enemy, ASoraCharacterBase& Target, bool bSees, float Dt, int32 NowMs)
{
    const FSoraEnemyArchetype& Kind = *Enemy.Archetype();
    FVector Delta = Target.GetActorLocation() - Enemy.GetActorLocation();
    Delta.Z = 0.f;
    const float Distance = Delta.Size();
    switch (Kind.Behavior)
    {
    case ESoraEnemyBehavior::Walker:
        // A walker stands where it is placed and turns its beam on the hero.
        Face(Enemy, Delta, Dt, 4.f);
        if (bSees)
            Enemy.TryAttack(Target, Distance);
        return;
    case ESoraEnemyBehavior::Drone:
        // A drone holds station in the air off the hero, and nets him from there.
        if (!Enemy.IsCommitted())
        {
            Face(Enemy, Delta, Dt, 4.f);
            WalkTo(Enemy, Target.GetActorLocation() - Delta.GetSafeNormal() * Kind.KeepDistanceCm,
                SoraEnemyBrain::CombatSpeed, 120.f, NowMs);
        }
        if (bSees)
            Enemy.TryAttack(Target, Distance);
        return;
    case ESoraEnemyBehavior::Blade:
    case ESoraEnemyBehavior::Shield:
    case ESoraEnemyBehavior::Conscript:
    case ESoraEnemyBehavior::Automaton:
        // A committed blow keeps its locked line. Otherwise the opponent squares
        // up to the hero and paths in until it holds him inside its reach; a
        // blade retainer's footwork takes over at close range.
        if (!Enemy.IsCommitted())
        {
            Face(Enemy, Delta, Dt, 4.f);
            if (bSees && Kind.Behavior == ESoraEnemyBehavior::Blade && Distance <= SoraEnemyBrain::FootworkRangeCm)
                Footwork(Enemy, Target, Delta, Distance);
            else if (bSees && Distance <= Enemy.MeleeReachCm() * SoraEnemyBrain::HoldReachShare)
                Enemy.AddMovementInput(Enemy.GetActorRightVector(), FMath::Sin(Enemy.GetLifeTime() + Slot) * .2f);
            else
                WalkTo(Enemy, Target.GetActorLocation(), SoraEnemyBrain::CombatSpeed, 150.f, NowMs);
        }
        if (bSees)
            Enemy.TryAttack(Target, Distance);
        return;
    default:
        break;
    }
    // Shooters: rifles, marksmen and grenadiers.
    Face(Enemy, Delta, Dt, 4.f);
    if (bSees)
        Enemy.TryAttack(Target, Distance);
    // On first contact a shooter holds its ground and fires; nobody walks off
    // in the middle of a raise or a burst.
    if (NowMs - CombatSinceMs < Stealth::ReactionMs(Slot) || Enemy.IsCommitted())
        return;
    const FVector Threat = Target.GetActorLocation();
    // A marksman moves on after its shots and does not take the same spot again.
    if (Kind.RelocateAfterShots > 0 && Enemy.ShotsSinceMove() >= Kind.RelocateAfterShots)
    {
        bAvoidSpot = bHasPosition;
        AvoidSpot = Position;
        bHasPosition = false;
        Enemy.Relocated();
    }
    // A grenadier keeps its distance: its shells burst around the hero.
    if (Kind.KeepDistanceCm > 0 && Distance < Kind.KeepDistanceCm)
    {
        FVector Away;
        const USoraNavigation* Nav = USoraNavigation::Get(this);
        if (Nav && Nav->Project(Enemy.GetActorLocation() - Delta.GetSafeNormal() * 400.f, Away))
            WalkTo(Enemy, Away, SoraEnemyBrain::CombatSpeed, 60.f, NowMs);
        return;
    }
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
    const float Standoff = FMath::Max(SoraEnemyBrain::OpenFireRangeCm, Kind.KeepDistanceCm + 100.f);
    if (Distance > Standoff)
        WalkTo(Enemy, Threat, SoraEnemyBrain::CombatSpeed, Standoff, NowMs);
    else
        Enemy.AddMovementInput(Enemy.GetActorRightVector(), FMath::Sin(Enemy.GetLifeTime() + Slot) * .2f);
}

void ASoraEnemyController::AlarmRun(ASoraEnemy& Enemy, const ASoraCharacterBase& Target, float Dt, int32 NowMs)
{
    // In a zone with alarm lecterns (ch06 alarm_points) the auditor runs to
    // the nearest one and raises the zone's alarm there. Stopped on the way,
    // it raises none; a lectern it cannot reach leaves it shouting as it flees.
    USoraStealth* Zone = bHunting ? nullptr : USoraStealth::Get(this);
    if (Zone && Zone->IsZoneActive() && !Zone->AlarmPoints().IsEmpty() && !bLecternUnreachable)
    {
        if (bAlarmRaised)
        {
            bGoalDone = true;
            LookAround(Enemy, Enemy.GetActorRotation().Yaw, 60.f, Dt, NowMs);
            return;
        }
        const TArray<FVector>& Lecterns = Zone->AlarmPoints();
        if (!Lecterns.IsValidIndex(Lectern))
        {
            Lectern = 0;
            for (int32 Index = 1; Index < Lecterns.Num(); ++Index)
                if (FVector::Dist2D(Enemy.GetActorLocation(), Lecterns[Index]) < FVector::Dist2D(Enemy.GetActorLocation(), Lecterns[Lectern]))
                    Lectern = Index;
        }
        const EMove Move = WalkTo(Enemy, Lecterns[Lectern], SoraEnemyBrain::RetreatSpeed, 90.f, NowMs);
        Face(Enemy, Heading, Dt, 5.f);
        if (Move == EMove::Arrived)
        {
            bAlarmRaised = true;
            if (USoraGameEvents* Bus = USoraGameEvents::Get(this))
            {
                FSoraEnemyCueEvent Event;
                Event.Enemy = &Enemy; Event.Archetype = Enemy.ArchetypeId(); Event.Cue = ESoraEnemyCue::Alarm;
                Event.Detail = TEXT("lectern");
                Bus->OnEnemyCue.Broadcast(Event);
            }
            Zone->RaiseAlarm(Enemy, LastKnown);
        }
        else if (Move == EMove::Blocked)
            bLecternUnreachable = true;
        return;
    }
    if (NowMs >= NextAlarmMs)
    {
        NextAlarmMs = NowMs + SoraEnemyBrain::AlarmRepeatMs;
        CallOut(Enemy);
        if (USoraGameEvents* Bus = USoraGameEvents::Get(this))
        {
            FSoraEnemyCueEvent Event;
            Event.Enemy = &Enemy; Event.Archetype = Enemy.ArchetypeId(); Event.Cue = ESoraEnemyCue::Alarm;
            Bus->OnEnemyCue.Broadcast(Event);
        }
    }
    const FVector Here = Enemy.GetActorLocation();
    FVector Away = Here + (Here - Target.GetActorLocation()).GetSafeNormal2D() * 600.f;
    FVector OnMesh;
    if (const USoraNavigation* Nav = USoraNavigation::Get(this); Nav && Nav->Project(Away, OnMesh))
        Away = OnMesh;
    bGoalDone = WalkTo(Enemy, Away, SoraEnemyBrain::RetreatSpeed, 60.f, NowMs) != EMove::Moving;
    Face(Enemy, Heading, Dt, 5.f);
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
        if (!USoraNavigation::Shields(Spot, Threat) || Claimed(Spot.Location) ||
            (bAvoidSpot && FVector::Dist2D(Spot.Location, AvoidSpot) < 300.f))
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

ASoraEnemyController::EMove ASoraEnemyController::WalkTo(ASoraEnemy& Enemy, const FVector& Goal, float Speed, float Acceptance, int32 NowMs,bool bStrict3D)
{
    const FVector Here = Enemy.GetActorLocation();
    const bool bVolume=bStrict3D||(bErrand&&bErrand3D);
    if ((bVolume?FVector::Dist(Here,Goal):FVector::Dist2D(Here,Goal)) <= Acceptance &&
        (Enemy.IsFlying()||FMath::Abs(Here.Z-Goal.Z)<180.f))
    {
        ClearPath();
        return EMove::Arrived;
    }
    // A walker never leaves its place; a drone flies over the mesh.
    if (Enemy.Archetype() && Enemy.Archetype()->bStatic)
        return EMove::Blocked;
    if (Enemy.IsFlying())
        return FlyTo(Enemy, Goal, Speed, Acceptance, NowMs,bVolume);
    if (!bPathValid || FVector::Dist2D(Goal, PathGoal) > 100.f || FMath::Abs(Goal.Z-PathGoal.Z)>100.f || NowMs >= RepathAtMs)
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
        while (PathIndex < Path.Num() - 1 && FVector::Dist2D(Here, Path[PathIndex]) <= 40.f && FMath::Abs(Here.Z-Path[PathIndex].Z)<180.f)
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
    if (Stuck(Here, NowMs,bVolume))
    {
        ClearPath();
        return EMove::Blocked;
    }
    Heading = Direction;
    Enemy.AddMovementInput(Direction, Speed);
    return EMove::Moving;
}

ASoraEnemyController::EMove ASoraEnemyController::FlyTo(ASoraEnemy& Enemy, const FVector& Goal, float Speed, float Acceptance, int32 NowMs,bool bVolume)
{
    // Straight at the goal at its hover height over the ground below, stepping
    // aside from what is ahead; no path is needed in the air.
    const FVector Here = Enemy.GetActorLocation();
    FVector Direction = bVolume?(Goal-Here).GetSafeNormal():(Goal - Here).GetSafeNormal2D();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BotNavigation), false, &Enemy);
    FCollisionObjectQueryParams Solid;
    Solid.AddObjectTypesToQuery(ECC_WorldStatic);
    Solid.AddObjectTypesToQuery(ECC_WorldDynamic);
    FHitResult Ahead;
    if (GetWorld()->LineTraceSingleByObjectType(Ahead, Here, Here + Direction * 180.f, Solid, Query))
        Direction = FVector(-Direction.Y, Direction.X, 0.f) * (Slot % 2 ? 1.f : -1.f);
    FHitResult Ground;
    float Climb = 0.f;
    if (!bVolume&&GetWorld()->LineTraceSingleByObjectType(Ground, Here, Here - FVector(0.f, 0.f, 5000.f), Solid, Query))
    {
        const float Height = Enemy.Archetype()->HoverCm + Enemy.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        Climb = FMath::Clamp((Ground.ImpactPoint.Z + Height - Here.Z) / 100.f, -1.f, 1.f);
    }
    // No progress for two seconds of flying means the goal cannot be reached.
    if (Stuck(Here, NowMs,bVolume))
        return EMove::Blocked;
    Heading = Direction;
    Enemy.AddMovementInput((Direction + FVector(0.f, 0.f, Climb)).GetClampedToMaxSize(1.f), Speed);
    return EMove::Moving;
}

bool ASoraEnemyController::Stuck(const FVector& Here, int32 NowMs,bool bThreeDimensional)
{
    const int32 Moved = FMath::RoundToInt32(bThreeDimensional?FVector::Dist(Here,StuckFrom):FVector::Dist2D(Here, StuckFrom));
    switch (Stealth::Progress(Walked, NowMs, Moved))
    {
    case Stealth::EProgress::Restarted:
        StuckFrom = Here;
        return false;
    case Stealth::EProgress::Walking:
        return false;
    case Stealth::EProgress::Stuck:
        return true;
    }
    return false;
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
    // A body the hero has just rolled past (転) cannot turn after him yet.
    if (Flat.IsNearlyZero() || Enemy.IsTurnLocked())
        return;
    // Heavy bodies turn at their own fixed rate, so a flank can outpace them.
    const FSoraEnemyArchetype* Kind = Enemy.Archetype();
    if (Kind && Kind->TurnDegreesPerSecond < 360)
        Enemy.SetActorRotation(FMath::RInterpConstantTo(Enemy.GetActorRotation(), Flat.Rotation(), Dt, Kind->TurnDegreesPerSecond));
    else
        Enemy.SetActorRotation(FMath::RInterpTo(Enemy.GetActorRotation(), Flat.Rotation(), Dt, Rate));
}

void ASoraEnemyController::LookAround(ASoraEnemy& Enemy, float BaseYaw, float Amplitude, float Dt, int32 NowMs, int32 PeriodMs) const
{
    // A slow sweep on its cycle (six seconds unless authored), offset by slot.
    const int32 Period = FMath::Max(1000, PeriodMs);
    const float Phase = 2.f * PI * static_cast<float>((NowMs + Slot * 977) % Period) / Period;
    Enemy.SetActorRotation(FMath::RInterpTo(Enemy.GetActorRotation(), FRotator(0.f, BaseYaw + Amplitude * FMath::Sin(Phase), 0.f), Dt, 3.f));
}

bool ASoraEnemyController::CanSee(const ASoraCharacterBase& Target) const
{
    const ASoraEnemy* Enemy = GetPawn<ASoraEnemy>();
    return Enemy && Stealth::InView(Look(*Enemy, Target), Enemy->Perception());
}

Stealth::FSight ASoraEnemyController::Look(const ASoraEnemy& Enemy, const ASoraCharacterBase& Target) const
{
    const FVector Eye = Enemy.SenseOrigin();
    const FVector There = Target.GetActorLocation();
    const FVector Flat(There.X - Eye.X, There.Y - Eye.Y, 0.f);
    const Stealth::FPerception& Perception = Enemy.Perception();
    const USoraStealth* Zone = USoraStealth::Get(this);
    Stealth::FSight Sight{};
    Sight.DistanceCm = FMath::RoundToInt32(Flat.Size());
    Sight.FacingMilli = FMath::RoundToInt32(FVector::DotProduct(Enemy.GetActorForwardVector().GetSafeNormal2D(), Flat.GetSafeNormal()) * 1000.f);
    if(const auto* Craft=USoraFieldcraft::Get(this);Craft&&Craft->IsClimbSentry(Enemy))
    {
        const bool Combat=Mind.State==Stealth::EState::Combat||Mind.State==Stealth::EState::Alert;
        if(!Craft->ClimbSentryWatching()&&!Combat&&There.Z<Eye.Z-250) return Sight;
        const FVector Aim=Combat?LastKnown:Craft->ClimbSentryWatching()?Craft->ClimbSentryAim():Eye+Enemy.GetActorForwardVector()*1000;
        const FVector Delta=There-Eye;
        Sight.DistanceCm=FMath::RoundToInt32(Delta.Size());
        Sight.FacingMilli=FMath::RoundToInt32(FVector::DotProduct((Aim-Eye).GetSafeNormal(),Delta.GetSafeNormal())*1000.f);
    }
    if(const auto* Craft=USoraFieldcraft::Get(this);Craft&&Craft->IsMoatGuard(Enemy))
    {
        const FVector Delta=There-Eye;
        Sight.DistanceCm=FMath::RoundToInt32(Delta.Size());
        Sight.FacingMilli=FMath::RoundToInt32(FVector::DotProduct((Craft->MoatGuardAim(Enemy)-Eye).GetSafeNormal(),Delta.GetSafeNormal())*1000.f);
    }
    Sight.TargetMoving = Target.GetVelocity().Size2D() > 30.f;
    Sight.Crouched = Target.IsCrouched();
    Sight.VisibilityPermille = Zone && Cast<ASoraPlayerCharacter>(&Target) ? Zone->HeroVisibility() : 1000;
    if (Sight.DistanceCm > Perception.SightRangeCm || Sight.FacingMilli < Perception.ViewConeMilli)
        return Sight;
    // How much of the hero a line from the eye reaches: low cover hides a
    // crouch but not a standing head, and a volley's smoke bank all of him.
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraSight), false, &Enemy);
    const float HalfHeight = Target.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const USoraFieldcraft* Fieldcraft = USoraFieldcraft::Get(this);
    int32 Visible = 0;
    for (const float Share : SoraEnemyBrain::BodySamples)
    {
        FHitResult Hit;
        const FVector Sample = There + FVector(0.f, 0.f, Share * HalfHeight);
        GetWorld()->LineTraceSingleByChannel(Hit, Eye, Sample, ECC_Visibility, Query);
        Visible += Hit.GetActor() == &Target && !(Fieldcraft && Fieldcraft->SmokeBetween(Eye, Sample)) ? 1 : 0;
    }
    Sight.ExposurePermille = Stealth::ExposurePermille(Visible, static_cast<int32>(UE_ARRAY_COUNT(SoraEnemyBrain::BodySamples)));
    // Under the water nothing of the hero shows; at its surface only a head.
    if (Fieldcraft && Cast<ASoraPlayerCharacter>(&Target))
        Sight.ExposurePermille = Fieldcraft->HeroExposure(Sight.ExposurePermille);
    if (Sight.ExposurePermille > 0)
    {
        Sight.LightPermille = Zone ? Zone->LightAt(There) : 1000;
        // These lamps are components, so the general ALight scan cannot see
        // them. Use the real head/cover/lamp-LOS sample; guard LOS still applies.
        if (Fieldcraft && Fieldcraft->IsMoatGuard(Enemy) && Cast<ASoraPlayerCharacter>(&Target) && Fieldcraft->MoatHeadLit())
            Sight.LightPermille = 1000;
    }
    return Sight;
}

void ASoraEnemyController::LookForBodies(ASoraEnemy& Enemy, int32 DtMs)
{
    // The nearest unfound body in view: a still figure low on the floor, in
    // whatever light falls on it. Evidence gathers while it stays in view.
    USoraStealth* Zone = USoraStealth::Get(this);
    const Stealth::FPerception& Perception = Enemy.Perception();
    const FVector Eye = Enemy.SenseOrigin();
    ASoraEnemy* Seen = nullptr;
    int32 SeenGain = 0;
    int32 SeenDistance = MAX_int32;
    for (ASoraEnemy* Body : Zone->UnfoundBodies())
    {
        if (Body == &Enemy)
            continue;
        const FVector At = Body->GetActorLocation() + FVector(0.f, 0.f, SoraEnemyBrain::BodySightHeight);
        const FVector Flat(At.X - Eye.X, At.Y - Eye.Y, 0.f);
        Stealth::FSight Sight{};
        Sight.DistanceCm = FMath::RoundToInt32(Flat.Size());
        Sight.FacingMilli = FMath::RoundToInt32(FVector::DotProduct(Enemy.GetActorForwardVector().GetSafeNormal2D(), Flat.GetSafeNormal()) * 1000.f);
        Sight.Crouched = true;
        if (Sight.DistanceCm >= SeenDistance || Sight.DistanceCm > Perception.SightRangeCm || Sight.FacingMilli < Perception.ViewConeMilli)
            continue;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraBodySight), false, &Enemy);
        Query.AddIgnoredActor(Body);
        if (GetWorld()->LineTraceTestByChannel(Eye, At, ECC_Visibility, Query))
            continue;
        if (const USoraFieldcraft* Fieldcraft = USoraFieldcraft::Get(this); Fieldcraft && Fieldcraft->SmokeBetween(Eye, At))
            continue;
        Sight.ExposurePermille = 1000;
        Sight.LightPermille = Zone->LightAt(At);
        const int32 Gain = Stealth::SightGainPerSecond(Sight, Perception);
        if (Gain <= 0)
            continue;
        Seen = Body;
        SeenGain = Gain;
        SeenDistance = Sight.DistanceCm;
    }
    if (Seen != BodyInView.Get())
        BodyEvidence = 0;
    BodyInView = Seen;
    BodyEvidence = Stealth::BodyEvidence(BodyEvidence, SeenGain, Stealth::RatePermille(Mind, Vigilance()), DtMs);
    if (Seen && Stealth::FindsBody(BodyEvidence, Vigilance()))
    {
        BodyEvidence = 0;
        BodyInView.Reset();
        Zone->FindBody(*Seen, Enemy);
    }
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
    if(const auto* Mode=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this)); Mode&&Mode->Campaign()->IsMaaiLesson())
    {
        Enemy.SuspendDojoAction();
        Enemy.GetCharacterMovement()->StopMovementImmediately();
        return;
    }
    // The chapter-one drill: face the hero, close to bokken distance around the
    // obstacle ahead, and strike on the pupil's own rhythm.
    // A pupil staggered by a meeting cut, or rolled past (転), stands where it is.
    if (Enemy.IsStaggered() || Enemy.IsTurnLocked())
        return;
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

void ASoraEnemyController::DriveBoss(ASoraBoss& Boss, ASoraCharacterBase& Target, float Dt)
{
    // Every query this frame sees the same, complete navigation mesh.
    if (USoraNavigation* Nav = USoraNavigation::Get(this))
        Nav->Settle();
    // A blind boss acts on what it hears; the others see their whole arena.
    for (const FNoise& Noise : Heard)
        Boss.Hear(Noise.Evidence);
    Heard.Reset();
    const FSoraBossIntent Intent = Boss.Drive(Target, Dt);
    const int32 NowMs = WorldMs();
    if (Intent.bMove)
        WalkTo(Boss, Intent.Goal, 1.f, Intent.AcceptanceCm, NowMs);
    else
        ClearPath();
    const FVector Flat(Intent.Facing.X, Intent.Facing.Y, 0.f);
    // A heavy boss turns at its phase's rate, so a flank can outpace it.
    if (Intent.bFace && !Flat.IsNearlyZero() && !Boss.IsTurnLocked())
        Boss.SetActorRotation(FMath::RInterpConstantTo(Boss.GetActorRotation(), Flat.Rotation(), Dt, Intent.TurnDegreesPerSecond));
}
