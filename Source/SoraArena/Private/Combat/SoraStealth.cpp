#include "Combat/SoraStealth.h"
#include "Combat/SoraDamage.h"
#include "Combat/SoraEnemyCatalog.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraPlayerCharacter.h"
#include "SoraFieldcraft.h"
#include "Components/CapsuleComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/Light.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace StealthRules = SoraStealthRules;

namespace SoraStealthZone
{
// A takedown or a drag needs the hero and the body on one floor.
constexpr float ReachHeightCm = 120.f;
// A dragged body trails this far from the hero.
constexpr float DragTrailCm = 95.f;

bool IsBrain(const ASoraEnemyController* Brain, const ASoraEnemy*& Enemy)
{
    Enemy = Brain ? Cast<ASoraEnemy>(Brain->GetPawn()) : nullptr;
    return Enemy && Enemy->Archetype() && Brain->IsGuard();
}
}

USoraStealth* USoraStealth::Get(const UObject* WorldContext)
{
    const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
    return World ? World->GetSubsystem<USoraStealth>() : nullptr;
}

bool USoraStealth::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
    return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId USoraStealth::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(USoraStealth, STATGROUP_Tickables);
}

double USoraStealth::Now() const
{
    return GetWorld()->GetTimeSeconds();
}

void USoraStealth::BeginZone(const FSoraStealthZone& Zone)
{
    AbortTakedown(false);
    EndDrag();
    ZoneRules = Zone;
    bZoneActive = true;
    Floors.Reset();
    Lecterns.Reset();
    Bodies.Reset();
    CarriedLight = 1000;
    bDetected = false;
    bAlarm = false;
    // Guards posted before the zone opened take its start now; later ones at their spawn.
    for (TActorIterator<ASoraEnemyController> It(GetWorld()); It; ++It)
        It->EnterZone(Zone.bCarriedOver);
}

void USoraStealth::EndZone()
{
    AbortTakedown(false);
    EndDrag();
    bZoneActive = false;
    ZoneRules = FSoraStealthZone();
    Floors.Reset();
    Lecterns.Reset();
    Bodies.Reset();
    CarriedLight = 1000;
    bDetected = false;
    bAlarm = false;
}

StealthRules::FVigilance USoraStealth::Vigilance() const
{
    return bZoneActive ? StealthRules::OnDifficulty(ZoneRules.Vigilance, ZoneRules.Difficulty) : StealthRules::Watchful();
}

void USoraStealth::AddSurface(const FBox& Volume, StealthRules::FSurface Surface)
{
    if (bZoneActive && Volume.IsValid)
        Floors.Add({Volume, Surface});
}

StealthRules::FSurface USoraStealth::SurfaceAt(const FVector& Feet) const
{
    if(const auto* Craft=USoraFieldcraft::Get(this))
    {
        const int32 MoatSteps=Craft->MoatFootstepPermille(Feet);
        if(MoatSteps>=0)return {MoatSteps,MoatSteps};
        const int32 FloodSteps=Craft->FloodFootstepPermille(Feet);
        if(FloodSteps>=0) return {FloodSteps,FloodSteps};
    }
    // The last floor added wins, so a nightingale floor's silent edge strip
    // is added after the corridor it runs along.
    for (int32 Index = Floors.Num() - 1; Index >= 0; --Index)
        if (Floors[Index].Volume.IsInsideOrOn(Feet))
            return Floors[Index].Surface;
    return StealthRules::Plain();
}

void USoraStealth::AddAlarmPoint(const FVector& Location)
{
    if (bZoneActive)
        Lecterns.Add(Location);
}

int32 USoraStealth::LightAt(const FVector& Location) const
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
            Lamps += StealthRules::LampPermille(FMath::RoundToInt32(FVector::Dist(Location, Lamp->GetComponentLocation())),
                FMath::RoundToInt32(Lamp->AttenuationRadius));
        else if (Light->IsA<UDirectionalLightComponent>())
            KeyDeciLux = FMath::Max(KeyDeciLux, FMath::RoundToInt32(Light->Intensity * 10.f));
    }
    return StealthRules::LightPermille(StealthRules::AmbientPermille(KeyDeciLux), Lamps);
}

void USoraStealth::NoteState(ASoraEnemy& Guard, StealthRules::EState Previous, StealthRules::EState Next)
{
    if (!bZoneActive || bDetected || !StealthRules::Detects(Previous, Next))
        return;
    bDetected = true;
    FSoraStealthDetection Detection;
    Detection.By = &Guard;
    Detection.Response = StealthRules::Response(ZoneRules.OnDetected, ZoneRules.Difficulty);
    if (const auto* Brain = Cast<ASoraEnemyController>(Guard.GetController()))
        Detection.KnownLocation = Brain->LastKnownLocation();
    OnDetected.Broadcast(Detection);
}

void USoraStealth::RaiseAlarm(ASoraEnemy& By, const FVector& Where)
{
    if (!bZoneActive || bAlarm)
        return;
    bAlarm = true;
    // Whoever raises an alarm has placed the hero.
    if (!bDetected)
    {
        bDetected = true;
        FSoraStealthDetection Detection;
        Detection.By = &By;
        Detection.Response = StealthRules::Response(ZoneRules.OnDetected, ZoneRules.Difficulty);
        Detection.KnownLocation = Where;
        OnDetected.Broadcast(Detection);
    }
    for (TActorIterator<ASoraEnemyController> It(GetWorld()); It; ++It)
    {
        const ASoraEnemy* Guard = nullptr;
        if (SoraStealthZone::IsBrain(*It, Guard) && Guard != &By && Guard->IsAlive())
            It->HearAlarm(Where);
    }
    OnAlarm.Broadcast(&By);
}

void USoraStealth::AddBody(ASoraEnemy& Body)
{
    if (!bZoneActive)
        return;
    for (const FBody& Entry : Bodies)
        if (Entry.Enemy.Get() == &Body)
            return;
    Bodies.Add({&Body, false});
}

TArray<ASoraEnemy*> USoraStealth::UnfoundBodies() const
{
    TArray<ASoraEnemy*> Found;
    if (!bZoneActive || !ZoneRules.bBodiesDiscoverable)
        return Found;
    for (const FBody& Entry : Bodies)
        if (ASoraEnemy* Body = Entry.Enemy.Get(); Body && !Entry.bFound && Body->IsBody())
            Found.Add(Body);
    return Found;
}

void USoraStealth::FindBody(ASoraEnemy& Body, ASoraEnemy& Finder)
{
    FBody* Entry = Bodies.FindByPredicate([&Body](const FBody& Candidate) { return Candidate.Enemy.Get() == &Body; });
    if (!bZoneActive || !Entry || Entry->bFound)
        return;
    Entry->bFound = true;
    // The whole zone searches: the finder around the body, the others where they stand.
    for (TActorIterator<ASoraEnemyController> It(GetWorld()); It; ++It)
    {
        const ASoraEnemy* Guard = nullptr;
        if (SoraStealthZone::IsBrain(*It, Guard) && Guard->IsAlive())
            It->LearnOfBody(Body.GetActorLocation(), Guard == &Finder);
    }
    if (USoraGameEvents* Events = USoraGameEvents::Get(this))
    {
        FSoraEnemyCueEvent Event;
        Event.Enemy = &Finder; Event.Archetype = Finder.ArchetypeId(); Event.Cue = ESoraEnemyCue::BodyFound;
        Event.Detail = Body.IsUnconscious() ? FName(TEXT("unconscious")) : Body.IsSubdued() ? FName(TEXT("subdued")) : FName(TEXT("dead"));
        Events->OnEnemyCue.Broadcast(Event);
    }
    OnBodyFound.Broadcast(&Body, &Finder);
}

void USoraStealth::MakeNoise(StealthRules::ENoise Kind, const FVector& Origin, const FVector& Evidence, const AActor* Source,
    int32 LoudnessPermille) const
{
    for (TActorIterator<ASoraEnemyController> It(GetWorld()); It; ++It)
        if (It->GetPawn() && It->GetPawn() != Source)
            It->HearNoise(Kind, Origin, Evidence, Source, LoudnessPermille);
}

bool USoraStealth::IsWorkPaused() const
{
    bool bSees = false;
    StealthRules::EState Most = StealthRules::EState::Unaware;
    for (TActorIterator<ASoraEnemyController> It(GetWorld()); It; ++It)
    {
        const ASoraEnemy* Guard = nullptr;
        if (!SoraStealthZone::IsBrain(*It, Guard) || !Guard->IsAlive())
            continue;
        bSees |= It->SeesHero();
        if (StealthRules::Severity(It->State()) > StealthRules::Severity(Most))
            Most = It->State();
    }
    return StealthRules::WorkPaused(bSees, Most);
}

ASoraEnemy* USoraStealth::TakedownTarget(const ASoraPlayerCharacter& Hero) const
{
    if (!bZoneActive || !ZoneRules.bRearTakedowns || bTakedownActive || IsDragging() || !Hero.CanPlay() || Hero.IsKernelDriven())
        return nullptr;
    ASoraEnemy* Best = nullptr;
    int32 BestDistance = MAX_int32;
    const FVector There = Hero.GetActorLocation();
    for (TActorIterator<ASoraEnemy> It(GetWorld()); It; ++It)
    {
        ASoraEnemy* Enemy = *It;
        const auto* Brain = Cast<ASoraEnemyController>(Enemy->GetController());
        if (!Brain || !Enemy->CanBeTakenDown() ||
            FMath::Abs(Enemy->GetActorLocation().Z - There.Z) > SoraStealthZone::ReachHeightCm)
            continue;
        const int32 Distance = FMath::RoundToInt32(FVector::Dist2D(There, Enemy->GetActorLocation()));
        if (Distance >= BestDistance || !StealthRules::CanTakedown(true, true, Brain->State(), Distance,
            SoraDamage::FacingMilli(*Enemy, There), SoraDamage::FacingMilli(Hero, Enemy->GetActorLocation())))
            continue;
        Best = Enemy;
        BestDistance = Distance;
    }
    return Best;
}

bool USoraStealth::BeginTakedown(ASoraPlayerCharacter& Hero)
{
    // A press during a takedown is spent on it.
    if (bTakedownActive)
        return true;
    ASoraEnemy* Target = TakedownTarget(Hero);
    if (!Target)
        return false;
    Victim = Target;
    Taker = &Hero;
    bTakedownActive = true;
    TakedownStartedAt = Now();
    bTakedownHeld = true;
    bTakedownDecided = false;
    Target->Seize(true);
    // The hero commits: guard, draw and strike drop, and he stands where he struck.
    Hero.GetEquipment()->DropStance();
    Hero.GetEquipment()->ReleaseTrigger();
    Hero.StopSprint();
    Hero.GetCharacterMovement()->StopMovementImmediately();
    if (AController* Controller = Hero.GetController())
    {
        Controller->SetIgnoreMoveInput(true);
        bMoveLocked = true;
    }
    return true;
}

void USoraStealth::ReleaseTakedown()
{
    bTakedownHeld = false;
}

void USoraStealth::TickTakedown()
{
    if (!bTakedownActive)
        return;
    ASoraPlayerCharacter* Hero = Taker.Get();
    if (!Hero || !Hero->CanPlay())
    {
        AbortTakedown(true);
        return;
    }
    const int32 ElapsedMs = FMath::FloorToInt32((Now() - TakedownStartedAt) * 1000.0);
    if (!bTakedownDecided && ElapsedMs >= StealthRules::TakedownHoldMs)
    {
        ASoraEnemy* Target = Victim.Get();
        if (!Target || !Target->IsAlive())
        {
            AbortTakedown(true);
            return;
        }
        bTakedownDecided = true;
        TakedownKind = StealthRules::Takedown(Target->IsNonlethal(), ZoneRules.bLethalDefault, bTakedownHeld);
        FinishTakedown(*Target, *Hero);
    }
    if (bTakedownDecided && ElapsedMs >= StealthRules::TakedownMs(TakedownKind))
    {
        UnlockHero();
        bTakedownActive = false;
        Victim.Reset();
        Taker.Reset();
    }
}

void USoraStealth::FinishTakedown(ASoraEnemy& Target, ASoraPlayerCharacter& Hero)
{
    Target.Seize(false);
    if (TakedownKind == StealthRules::ETakedown::Knockout)
        Target.KnockOut(&Hero);
    else
    {
        // The gorget thrust, or on a conscript the back of the blade: whatever
        // its shield, barrier or poise, the blow from behind ends the fight
        // (SoraDamage::Resolve knocks a conscript down instead).
        FSoraHit Hit;
        Hit.WeaponId = Hero.WeaponId;
        FHitResult Trace;
        Trace.ImpactPoint = Target.GetActorLocation();
        Trace.Location = Trace.ImpactPoint;
        SoraDamage::Strike(&Target, Target.MaxHealth * 10.f + 1000.f, Hit, Target.GetActorForwardVector(), Trace, Hero.GetController(), &Hero);
    }
    MakeNoise(StealthRules::ENoise::Takedown, Target.GetActorLocation(), Hero.GetActorLocation(), &Hero);
}

void USoraStealth::AbortTakedown(bool bRouse)
{
    if (!bTakedownActive)
        return;
    // A takedown the round interrupts lets go; the guard felt the grab. One
    // the zone's end or restart interrupts lets go quietly.
    ASoraEnemy* Target = Victim.Get();
    if (Target && !bTakedownDecided)
    {
        Target->Seize(false);
        if (auto* Brain = Cast<ASoraEnemyController>(Target->GetController()); bRouse && Brain && Taker.IsValid())
            Brain->Rouse(Taker->GetActorLocation());
    }
    UnlockHero();
    bTakedownActive = false;
    Victim.Reset();
    Taker.Reset();
}

void USoraStealth::UnlockHero()
{
    if (!bMoveLocked)
        return;
    bMoveLocked = false;
    if (ASoraPlayerCharacter* Hero = Taker.Get())
        if (AController* Controller = Hero->GetController())
            Controller->SetIgnoreMoveInput(false);
}

ASoraEnemy* USoraStealth::DragTarget(const ASoraPlayerCharacter& Hero) const
{
    if (!bZoneActive || !ZoneRules.bDragBodies || bTakedownActive || IsDragging() || !Hero.CanPlay() || Hero.IsKernelDriven())
        return nullptr;
    ASoraEnemy* Best = nullptr;
    float BestDistance = StealthRules::DragReachCm;
    const FVector There = Hero.GetActorLocation();
    for (const FBody& Entry : Bodies)
    {
        ASoraEnemy* Body = Entry.Enemy.Get();
        // A knocked-down conscript's collar is cut, not dragged.
        if (!Body || !Body->IsBody() || Body->IsSubdued() || SoraDamage::FacingMilli(Hero, Body->GetActorLocation()) < 0 ||
            FMath::Abs(Body->GetActorLocation().Z - There.Z) > SoraStealthZone::ReachHeightCm)
            continue;
        const float Distance = FVector::Dist2D(There, Body->GetActorLocation());
        if (Distance <= BestDistance)
        {
            Best = Body;
            BestDistance = Distance;
        }
    }
    return Best;
}

bool USoraStealth::BeginDrag(ASoraPlayerCharacter& Hero)
{
    ASoraEnemy* Body = DragTarget(Hero);
    if (!Body)
        return false;
    Dragged = Body;
    Dragger = &Hero;
    return true;
}

void USoraStealth::EndDrag()
{
    Dragged.Reset();
    Dragger.Reset();
}

float USoraStealth::HeroMoveScale() const
{
    return IsDragging() ? StealthRules::DragSpeedPermille / 1000.f : 1.f;
}

void USoraStealth::TickDrag()
{
    ASoraEnemy* Body = Dragged.Get();
    const ASoraPlayerCharacter* Hero = Dragger.Get();
    if (!Body && !Hero)
        return;
    if (!Body || !Hero || !Hero->CanPlay() || !Body->IsBody() || !bZoneActive)
    {
        EndDrag();
        return;
    }
    // Towed on a short rope: once the hero is farther than the trail, the body
    // follows him on his floor, lying along the line it is pulled.
    const FVector Here = Hero->GetActorLocation();
    FVector Offset = Body->GetActorLocation() - Here;
    Offset.Z = 0.f;
    if (Offset.Size() <= SoraStealthZone::DragTrailCm)
        return;
    const FVector Line = Offset.GetSafeNormal();
    const FVector To = Here + Line * SoraStealthZone::DragTrailCm;
    const float Floor = Here.Z - Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    Body->SetActorLocation(FVector(To.X, To.Y, Floor + Body->GetCapsuleComponent()->GetScaledCapsuleRadius()), false, nullptr,
        ETeleportType::TeleportPhysics);
    Body->SetActorRotation(FRotator(0.f, Line.Rotation().Yaw, 85.f));
}

FSoraStealthReadout USoraStealth::Readout(const ASoraPlayerCharacter& Hero) const
{
    FSoraStealthReadout Readout;
    Readout.bZone = bZoneActive;
    if (!bZoneActive)
        return Readout;
    for (TActorIterator<ASoraEnemyController> It(GetWorld()); It; ++It)
    {
        const ASoraEnemy* Guard = nullptr;
        if (!SoraStealthZone::IsBrain(*It, Guard) || !Guard->IsAlive() || Guard->IsSeized())
            continue;
        FSoraStealthMark Mark;
        Mark.Enemy = const_cast<ASoraEnemy*>(Guard);
        Mark.State = It->State();
        Mark.MeterPermille = It->MeterPermille();
        Mark.Head = Guard->GetActorLocation() + FVector(0.f, 0.f, Guard->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 30.f);
        const int32 Severity = StealthRules::Severity(Mark.State);
        const int32 WorstSeverity = StealthRules::Severity(Readout.Worst);
        if (Severity > WorstSeverity || (Severity == WorstSeverity && Mark.MeterPermille > Readout.MeterPermille))
        {
            Readout.Worst = Mark.State;
            Readout.MeterPermille = Mark.MeterPermille;
        }
        Readout.bSeen |= It->SeesHero();
        if (Mark.State != StealthRules::EState::Unaware || Mark.MeterPermille > 0)
            Readout.Marks.Add(Mark);
    }
    Readout.LightPermille = LightAt(Hero.GetActorLocation());
    Readout.VisibilityPermille = CarriedLight;
    Readout.bCrouched = Hero.IsCrouched();
    Readout.bDetected = bDetected;
    Readout.bAlarm = bAlarm;
    if (const ASoraEnemy* Target = TakedownTarget(Hero))
    {
        Readout.bTakedown = true;
        Readout.bTakedownSubdues = Target->IsNonlethal();
    }
    Readout.bLethalDefault = ZoneRules.bLethalDefault;
    Readout.bDrag = DragTarget(Hero) != nullptr;
    Readout.bDragging = IsDragging();
    return Readout;
}

void USoraStealth::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);
    TickTakedown();
    TickDrag();
}

void USoraStealth::Deinitialize()
{
    // The world is going; nobody is roused or released.
    bTakedownActive = false;
    bMoveLocked = false;
    Victim.Reset();
    Taker.Reset();
    EndDrag();
    Super::Deinitialize();
}
