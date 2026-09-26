#include "SoraBoss.h"
#include "SoraSettings.h"
#include "Combat/SoraBossCatalog.h"
#include "Combat/SoraBossHazard.h"
#include "Combat/SoraDamage.h"
#include "SoraEquipmentComponent.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

namespace BossRules = SoraBossRules;
namespace Rules = SoraCombatRules;

namespace SoraBossBody
{
// Attacks leave from this height above the capsule's centre, scaled with the
// body, and strike the hero at his chest.
constexpr float EyeHeight = 50.f;
constexpr float ChestHeight = 35.f;
// Telegraph visuals are refreshed this often while a windup runs.
constexpr int32 VisualMs = 130;
// A gunslinger's sidestep before her burst.
constexpr int32 DashMs = 250;
// The first attack of a fight waits this long after the boss arrives.
constexpr int32 OpeningMs = 800;
// A shield advance shoves the hero aside at most this often.
constexpr int32 PushEveryMs = 800;
// A blow's reach is measured to the hero's capsule, a lane's width to his side.
constexpr float HeroRadius = 34.f;
// A hit near a weak point counts as on it; a blast within this of one.
constexpr float PointSlackCm = 30.f;
constexpr float BlastSlackCm = 250.f;
// The arena lock: this many wall segments, this tall.
constexpr int32 LockSegments = 24;
constexpr float LockHeight = 600.f;
// Barrier, ward and arena-lock parts; telegraphs take the player's palette.
const FLinearColor Cyan(.04f, .85f, .95f);
const FLinearColor Steel(.75f, .82f, .87f);
const FLinearColor Dark(.10f, .11f, .12f);

// A telegraph in the settings' palette (SoraAccessibility): cyan marks a
// locked aim or beam, amber a blow or an area. The strike itself flashes a
// lighter shade of the same colour.
FLinearColor TelegraphColor(const UObject* WorldContext, ESoraBossTelegraph Telegraph)
{
    return SoraAccessibility::TelegraphColor(WorldContext,
        Telegraph == ESoraBossTelegraph::Cyan ? SoraAccessibility::ETelegraph::Lock : SoraAccessibility::ETelegraph::Cleave);
}
FLinearColor StrikeColor(const UObject* WorldContext, ESoraBossTelegraph Telegraph)
{
    return SoraAccessibility::StrikeColor(WorldContext,
        Telegraph == ESoraBossTelegraph::Cyan ? SoraAccessibility::ETelegraph::Lock : SoraAccessibility::ETelegraph::Cleave);
}

FName DefeatName(ESoraBossDefeat Defeat)
{
    switch (Defeat)
    {
    case ESoraBossDefeat::Kill: return TEXT("kill");
    case ESoraBossDefeat::Disarm: return TEXT("disarm");
    case ESoraBossDefeat::Capture: return TEXT("capture");
    case ESoraBossDefeat::DestroyWeakPoints: return TEXT("destroy_weakpoints");
    case ESoraBossDefeat::Points: return TEXT("points");
    }
    return TEXT("kill");
}

int32 CosineMilli(const FVector& A, const FVector& B)
{
    return FMath::RoundToInt32(FVector::DotProduct(A.GetSafeNormal2D(), B.GetSafeNormal2D()) * 1000.f);
}
}

ASoraBoss::ASoraBoss(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
}

ASoraBoss* ASoraBoss::SpawnBoss(UWorld& World, FName Id, int32 Slot, const FVector& Location, const FRotator& Rotation,
    const FSoraBossSetup& InSetup)
{
    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    ASoraBoss* Boss = World.SpawnActor<ASoraBoss>(Location, Rotation, Params);
    if (Boss && !Boss->InitBoss(Id, Slot, InSetup))
    {
        Boss->Destroy();
        return nullptr;
    }
    return Boss;
}

bool ASoraBoss::InitBoss(FName Id, int32 Slot, const FSoraBossSetup& InSetup)
{
    FSoraBossCatalog& Catalog = FSoraBossCatalog::Get();
    const FSoraBossData* Found = Catalog.Load() ? Catalog.Find(Id) : nullptr;
    if (!Found)
    {
        UE_LOG(LogTemp, Error, TEXT("No boss %s: %s"), *Id.ToString(),
            Catalog.IsReady() ? TEXT("not in Content/Data/bosses.json") : *Catalog.Error);
        return false;
    }
    Info = Found;
    Setup = InSetup;
    Setup.Phase = FMath::Clamp(Setup.Phase, 0, Info->Phases.Num() - 1);
    InitScripted(Slot);
    SetActorScale3D(FVector(Info->ScalePermille / 1000.f));
    WeaponId = Info->HeldWeapon;
    RebuildWeapon();
    MaxHealth = Info->HealthFor(Setup.Difficulty);
    Health = BossRules::PhaseHealth(FMath::RoundToInt32(MaxHealth), Info->Phases[Setup.Phase].FromPermille);
    Run = FRun();
    Step = 0; StepDone = 0; NextStartMs = 0; LastStartMs = 0; Picked = INDEX_NONE; Forced = INDEX_NONE; Lead = 0; HabitStep = 0;
    for (BossRules::FWeighted& Habit : Habits)
        Habit = BossRules::Fresh();
    ReadyAtMs.Init(0, Info->Attacks.Num());
    Sides.Reset();
    Exposures.Reset();
    bShieldBroken = false; ShieldHits = 0; FrontBlocked = 0;
    BarrierNowMilli = Info->bBarrier ? Info->Barrier.Health * 1000 : 0;
    BarrierAtHitMilli = BarrierNowMilli; BarrierHitMs = 0;
    MantleDownUntilMs = 0; StunUntilMs = 0; StunTakenPermille = 1000; StrikeImmuneUntilMs = 0;
    PointHealth.Reset();
    PointOpenUntilMs.Reset();
    for (const FSoraBossWeakPoint& Point : Info->WeakPoints)
    {
        PointHealth.Add(Point.Health > 0 ? Point.Health : -1);
        PointOpenUntilMs.Add(0);
    }
    RotateNext = 0; SealCount = 0;
    AddGroups.Reset();
    GroupRespawnAtMs.Init(0, Info->Adds.Num());
    BarkReadyMs.Reset();
    BarkedOnce.Reset();
    KnownAt = GetActorLocation();
    KnownAtMs = MIN_int32 / 2;
    bDefeated = false; bTakenByMuto = false; Defeated = NAME_None;
    Center = Setup.bHasArenaCenter ? Setup.ArenaCenter : GetActorLocation();
    ArenaRadiusCm = Setup.ArenaRadiusCm > 0 ? Setup.ArenaRadiusCm : Info->ArenaRadiusCm;
    // Weak points are parts of the body: they glow when exposed and take hits.
    for (UStaticMeshComponent* Part : PointParts)
        if (Part)
            Part->DestroyComponent();
    PointParts.Reset();
    const float Scale = GetActorScale3D().X;
    for (const FSoraBossWeakPoint& Point : Info->WeakPoints)
    {
        UStaticMeshComponent* Part = ASoraWorldBuilder::Shape(this, GetRootComponent(), TEXT("WeakPoint_") + Point.Id.ToString(),
            TEXT("/Engine/BasicShapes/Sphere.Sphere"), Point.Offset / Scale, FVector(Point.RadiusCm / 50.f / Scale),
            SoraBossBody::Dark, true);
        Part->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        Part->SetCollisionObjectType(ECC_WorldDynamic);
        Part->SetCollisionResponseToAllChannels(ECR_Block);
        Part->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
        Part->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
        Part->SetCanEverAffectNavigation(false);
        PointParts.Add(Part);
    }
    bPhaseEntered = false;
    PhaseNow = Setup.Phase;
    EnterPhase(Setup.Phase);
    LockArena(Setup.bLockArena);
    Broadcast(ESoraBossPhase::Arrived, Info->Id);
    return true;
}

int32 ASoraBoss::NowMs() const { return FMath::FloorToInt32(GetWorld()->GetTimeSeconds() * 1000.0); }
FName ASoraBoss::BossId() const { return Info ? Info->Id : NAME_None; }
const FSoraBossAttack& ASoraBoss::AttackAt(int32 Index) const { return Info->Attacks[Index]; }
const FSoraBossPhase* ASoraBoss::CurrentPhase() const { return Info && Info->Phases.IsValidIndex(PhaseNow) ? &Info->Phases[PhaseNow] : nullptr; }
const FSoraBossAttack* ASoraBoss::BossAttack() const
{
    return Info && Info->Attacks.IsValidIndex(Run.Attack) ? &Info->Attacks[Run.Attack] : nullptr;
}
int32 ASoraBoss::HealthPermille() const
{
    return BossRules::HealthPermille(FMath::RoundToInt32(Health), FMath::RoundToInt32(MaxHealth));
}
bool ASoraBoss::IsSparring() const { return Info && !Info->bLethal; }
bool ASoraBoss::UsesAlienBody() const { return !Info || Info->Body != ESoraBossBody::Local; }
bool ASoraBoss::WieldsDojoBokken() const { return Info && Info->bSparringWeapon; }

int32 ASoraBoss::Tuned(int32 Index, ETuned Which, int32 Base) const
{
    const FSoraBossPhase* Current = CurrentPhase();
    if (!Current)
        return Base;
    int32 Value = Base;
    const auto Apply = [&](const TArray<FSoraBossOverride>& Rows)
    {
        for (const FSoraBossOverride& Row : Rows)
        {
            if (Row.Attack != Index)
                continue;
            const int32 Changed = Which == ETuned::Windup ? Row.WindupMs : Which == ETuned::Active ? Row.ActiveMs :
                Which == ETuned::Recovery ? Row.RecoveryMs : Which == ETuned::Cooldown ? Row.CooldownMs :
                Which == ETuned::Reach ? Row.MaxRangeCm : Row.RootMs;
            if (Changed >= 0)
                Value = Changed;
        }
    };
    Apply(Current->Overrides);
    if (Current->LateBelowPermille > 0 && HealthPermille() <= Current->LateBelowPermille)
        Apply(Current->Late);
    return Value;
}
int32 ASoraBoss::WindupFor(int32 Index) const
{
    const FSoraBossCatalog& Catalog = FSoraBossCatalog::Get();
    return BossRules::ForDifficulty(Tuned(Index, ETuned::Windup, AttackAt(Index).WindupMs), Setup.Difficulty,
        Catalog.EasyWindupPermille, Catalog.HardWindupPermille);
}
int32 ASoraBoss::RecoveryFor(int32 Index) const { return Tuned(Index, ETuned::Recovery, AttackAt(Index).RecoveryMs); }
int32 ASoraBoss::ActiveFor(int32 Index) const { return Tuned(Index, ETuned::Active, AttackAt(Index).ActiveMs); }
int32 ASoraBoss::CooldownFor(int32 Index) const { return Tuned(Index, ETuned::Cooldown, AttackAt(Index).CooldownMs); }
int32 ASoraBoss::ReachFor(int32 Index) const { return Tuned(Index, ETuned::Reach, AttackAt(Index).MaxRangeCm); }
int32 ASoraBoss::RootFor(int32 Index) const { return Tuned(Index, ETuned::Root, AttackAt(Index).RootMs); }
int32 ASoraBoss::MutoWindowMs() const
{
    const FSoraBossCatalog& Catalog = FSoraBossCatalog::Get();
    return BossRules::ForDifficulty(Rules::MutoWindowMs, Setup.Difficulty, Catalog.EasyWindupPermille, Catalog.HardWindupPermille);
}
int32 ASoraBoss::MarobashiWindowMs() const
{
    const FSoraBossAttack* Attack = BossAttack();
    if (!Attack || Attack->MarobashiMs <= 0 || Run.Stage != EStage::Windup)
        return 0;
    const FSoraBossCatalog& Catalog = FSoraBossCatalog::Get();
    return BossRules::ForDifficulty(Attack->MarobashiMs, Setup.Difficulty, Catalog.EasyWindupPermille, Catalog.HardWindupPermille);
}
int32 ASoraBoss::MarobashiUntilLandsMs() const
{
    return Run.Stage == EStage::Windup && GetWorld() ? FMath::Max(0, Run.StageEndsMs - NowMs()) : -1;
}
int32 ASoraBoss::FloorPermille() const
{
    const FSoraBossPhase* Current = CurrentPhase();
    return FMath::Max(Info ? Info->FloorPermille : 0, Current ? Current->FloorPermille : 0);
}

bool ASoraBoss::IsBossTelegraphing() const
{
    return IsAlive() && (Run.Stage == EStage::Windup || Run.Stage == EStage::Dash || Run.Stage == EStage::Hold);
}
float ASoraBoss::BossWarningSeconds() const
{
    return Run.Stage == EStage::Windup ? FMath::Max(0, Run.StageEndsMs - NowMs()) / 1000.f : 0.f;
}
float ASoraBoss::BossWarningProgress() const
{
    if (Run.Stage != EStage::Windup || Run.WindupMs <= 0)
        return 0.f;
    return FMath::Clamp(1.f - (Run.StageEndsMs - NowMs()) / static_cast<float>(Run.WindupMs), 0.f, 1.f);
}
bool ASoraBoss::IsRecovering() const { return Run.Stage == EStage::Recovery; }
bool ASoraBoss::IsStunned() const { return GetWorld() && NowMs() < StunUntilMs; }
bool ASoraBoss::IsShieldUp() const
{
    const FSoraBossPhase* Current = CurrentPhase();
    return Info && Info->bShield && Current && Current->bShield && !bShieldBroken;
}
bool ASoraBoss::IsMantleUp() const
{
    const FSoraBossPhase* Current = CurrentPhase();
    return Info && Info->bMantle && Current && Current->bMantle && NowMs() >= MantleDownUntilMs;
}
bool ASoraBoss::HasBarrier() const
{
    const FSoraBossPhase* Current = CurrentPhase();
    return Info && Info->bBarrier && Current && Current->bBarrier;
}
bool ASoraBoss::IsBarrierOffline() const
{
    for (const FExposure& Window : Exposures)
        if (AttackAt(Window.Attack).bBarrierOffline)
            return true;
    return false;
}
int32 ASoraBoss::BarrierPoints() const { return HasBarrier() ? BarrierNowMilli / 1000 : 0; }
bool ASoraBoss::IsInvulnerable() const
{
    if (!Info || !GetWorld())
        return false;
    if (NowMs() < InvulnerableUntilMs)
        return true;
    const FSoraBossPhase* Current = CurrentPhase();
    return Current && Current->ShieldWhileAdds != INDEX_NONE && LiveAdds(Current->ShieldWhileAdds) > 0;
}
bool ASoraBoss::IsWeakPointOpen(int32 Index) const
{
    if (!Info || !Info->WeakPoints.IsValidIndex(Index) || PointHealth[Index] == 0)
        return false;
    return Info->WeakPoints[Index].bAlwaysOpen || NowMs() < PointOpenUntilMs[Index];
}
int32 ASoraBoss::WeakPointHealth(int32 Index) const { return PointHealth.IsValidIndex(Index) ? PointHealth[Index] : 0; }
UPrimitiveComponent* ASoraBoss::WeakPointPart(int32 Index) const { return PointParts.IsValidIndex(Index) ? PointParts[Index].Get() : nullptr; }
FVector ASoraBoss::WeakPointLocation(int32 Index) const
{
    if (const UPrimitiveComponent* Part = WeakPointPart(Index))
        return Part->GetComponentLocation();
    return GetActorLocation() + GetActorRotation().RotateVector(Info->WeakPoints[Index].Offset);
}
int32 ASoraBoss::LiveAdds(int32 Group) const
{
    int32 Count = 0;
    for (int32 Index = 0; Index < Adds.Num(); ++Index)
        if (IsValid(Adds[Index]) && Adds[Index]->IsAlive() && (Group == INDEX_NONE || AddGroups[Index] == Group))
            ++Count;
    return Count;
}
int32 ASoraBoss::LiveWards() const
{
    int32 Count = 0;
    for (const ASoraBossHazard* Guard : WardActors)
        Count += IsValid(Guard) && Guard->WardHealth() > 0 ? 1 : 0;
    return Count;
}
int32 ASoraBoss::LiveZones(int32 Index) const
{
    int32 Count = 0;
    for (const ASoraBossHazard* Zone : Zones)
        Count += IsValid(Zone) && !Zone->IsSpent() && (Index == INDEX_NONE || Zone->AttackOf() == Index) ? 1 : 0;
    return Count;
}
bool ASoraBoss::KnowsHero() const
{
    return Info && (!Info->bBlind || NowMs() - KnownAtMs <= Info->Hearing.FreshMs);
}
ASoraCharacterBase* ASoraBoss::Hero() const
{
    return Cast<ASoraCharacterBase>(UGameplayStatics::GetPlayerPawn(this, 0));
}
FVector ASoraBoss::Ground(const FVector& Point) const
{
    FHitResult Floor;
    FCollisionObjectQueryParams Solid;
    Solid.AddObjectTypesToQuery(ECC_WorldStatic);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraBossGround), false, this);
    if (GetWorld()->LineTraceSingleByObjectType(Floor, Point + FVector(0.f, 0.f, 150.f), Point - FVector(0.f, 0.f, 1500.f), Solid, Query))
        return Floor.ImpactPoint + FVector(0.f, 0.f, 3.f);
    return Point;
}
FVector ASoraBoss::ClampToArena(const FVector& Point) const
{
    const float Limit = FMath::Max(100.f, ArenaRadiusCm - 150.f);
    FVector Flat(Point.X - Center.X, Point.Y - Center.Y, 0.f);
    if (Flat.Size() <= Limit)
        return Point;
    Flat = Flat.GetSafeNormal() * Limit;
    return FVector(Center.X + Flat.X, Center.Y + Flat.Y, Point.Z);
}
FVector ASoraBoss::TargetPoint(const ASoraCharacterBase& Target) const
{
    return Info && Info->bBlind ? KnownAt : Target.GetActorLocation();
}

void ASoraBoss::Broadcast(ESoraBossPhase What, FName Detail, FName Line, int32 Serial, int32 WindupMs) const
{
    USoraGameEvents* Events = USoraGameEvents::Get(this);
    if (!Events)
        return;
    FSoraBossPhaseEvent Event;
    Event.Boss = const_cast<ASoraBoss*>(this);
    Event.Phase = What;
    const FSoraBossAttack* Attack = BossAttack();
    Event.bBeam = Attack && Attack->Kind == ESoraBossAttackKind::Beam;
    Event.HealthFraction = MaxHealth > 0.f ? FMath::Clamp(Health / MaxHealth, 0.f, 1.f) : 0.f;
    Event.BossId = BossId();
    Event.PhaseIndex = PhaseNow;
    Event.Detail = Detail;
    Event.Line = Line;
    Event.Serial = Serial;
    Event.WindupMs = WindupMs;
    Events->OnBossPhase.Broadcast(Event);
}
FName ASoraBoss::BarkLine(const FSoraBossAttack& Attack)
{
    if (Attack.Bark.IsNone() || (Attack.bBarkOnce && BarkedOnce.Contains(Attack.Id)))
        return NAME_None;
    const int32 Now = NowMs();
    if (const int32* Ready = BarkReadyMs.Find(Attack.Id); Ready && Now < *Ready)
        return NAME_None;
    BarkedOnce.Add(Attack.Id);
    BarkReadyMs.Add(Attack.Id, Now + Attack.BarkCooldownMs);
    return Attack.Bark;
}
FName ASoraBoss::EventBark(FName Event)
{
    const FSoraBossBark* Bark = Info ? Info->BarkFor(Event) : nullptr;
    if (!Bark)
        return NAME_None;
    const int32 Now = NowMs();
    const FName Key(*(TEXT("event:") + Event.ToString()));
    if (const int32* Ready = BarkReadyMs.Find(Key); Ready && Now < *Ready)
        return NAME_None;
    BarkReadyMs.Add(Key, Now + Bark->CooldownMs);
    return Bark->Line;
}
void ASoraBoss::AnnounceStrike(int32 Index, int32 Serial)
{
    if (Info && Info->Attacks.IsValidIndex(Index))
        Broadcast(ESoraBossPhase::Strike, AttackAt(Index).Id, NAME_None, Serial, WindupFor(Index));
}

void ASoraBoss::AddAnchor(FName AnchorKind, const FVector& Location)
{
    Anchors.Add({AnchorKind, Location});
}
void ASoraBoss::SetDuelScore(int32 HeroPoints, int32 RivalPoints)
{
    const int32 Next = FMath::Clamp(HeroPoints - RivalPoints, 0, 2);
    if (Next != Lead)
        Picked = INDEX_NONE;
    Lead = Next;
}
void ASoraBoss::Stun(int32 Milliseconds, int32 TakenPermille)
{
    if (Milliseconds <= 0 || !IsAlive())
        return;
    StunUntilMs = FMath::Max(StunUntilMs, NowMs() + Milliseconds);
    StunTakenPermille = TakenPermille;
    Stagger(Milliseconds);
}
bool ASoraBoss::ForceAttack(FName AttackId)
{
    const int32 Index = Info ? Info->AttackIndex(AttackId) : INDEX_NONE;
    if (Index == INDEX_NONE || bDefeated || Run.Attack != INDEX_NONE)
        return false;
    Forced = Index;
    return true;
}
void ASoraBoss::Hold(int32 Milliseconds)
{
    HoldUntilMs = NowMs() + Milliseconds;
}

void ASoraBoss::EnterPhase(int32 Next)
{
    const bool bOpening = !bPhaseEntered;
    bPhaseEntered = true;
    PhaseNow = Next;
    const FSoraBossPhase& Entered = Info->Phases[Next];
    const int32 Now = NowMs();
    PhaseStartedMs = Now;
    BeatOriginMs = -1;
    // A phase change cuts off the attack under way and its open windows.
    Run = FRun();
    Sides.Reset();
    Exposures.Reset();
    Step = 0; StepDone = 0; Picked = INDEX_NONE; HabitStep = 0;
    GetCharacterMovement()->MaxWalkSpeed = Entered.SpeedCmPerSecond;
    GetCharacterMovement()->MaxFlySpeed = Entered.SpeedCmPerSecond;
    const int32 Settle = bOpening ? SoraBossBody::OpeningMs : Info->TransitionMs;
    NextStartMs = Now + Settle;
    if (!bOpening && Info->TransitionMs > 0)
    {
        // The phase's roar: it cannot be hurt and does nothing meanwhile.
        InvulnerableUntilMs = Now + Info->TransitionMs;
        ASoraEnemy::Stagger(Info->TransitionMs);
    }
    TimedDueMs.Reset();
    for (const FSoraBossTimed& Timed : Entered.Concurrent)
        TimedDueMs.Add(Now + Settle + Timed.FirstMs);
    SummonDone.Init(false, Entered.Summons.Num());
    OnceDone.Init(false, Entered.OnceBelow.Num());
    NextFloorAttackMs = 0;
    if (Info->bShield && !Entered.bShield && !bShieldBroken)
        BreakShield();
    if (Info->bBarrier && !Entered.bBarrier && BarrierNowMilli > 0)
    {
        BarrierNowMilli = 0;
        BarrierAtHitMilli = 0;
        Broadcast(ESoraBossPhase::Event, TEXT("barrier_burnout"));
    }
    ClearWards();
    WardIndex = Entered.Ward;
    if (WardIndex != INDEX_NONE)
        SpawnWards(WardIndex);
    Broadcast(ESoraBossPhase::PhaseChanged, Entered.Table, Entered.Bark);
    for (const int32 Attack : Entered.OnEnter)
        StartSide(Attack);
}
void ASoraBoss::SyncPhase()
{
    int32 Starts[BossRules::MaxPhases] = {};
    const int32 Count = FMath::Min(Info->Phases.Num(), BossRules::MaxPhases);
    for (int32 Index = 0; Index < Count; ++Index)
        Starts[Index] = Info->Phases[Index].FromPermille;
    const int32 Reached = BossRules::PhaseFor(Starts, Count, HealthPermille());
    if (Reached > PhaseNow)
        EnterPhase(Reached);
}
void ASoraBoss::RunTimers()
{
    const FSoraBossPhase& Current = Info->Phases[PhaseNow];
    const int32 Now = NowMs();
    const bool bFree = !IsStaggered() && Now >= InvulnerableUntilMs;
    for (int32 Index = 0; Index < Current.Concurrent.Num(); ++Index)
        if (bFree && Now >= TimedDueMs[Index])
        {
            TimedDueMs[Index] = Now + Current.Concurrent[Index].EveryMs;
            StartSide(Current.Concurrent[Index].Attack);
        }
    const int32 Permille = HealthPermille();
    for (int32 Index = 0; Index < Current.Summons.Num(); ++Index)
        if (!SummonDone[Index] && Permille <= Current.Summons[Index].AtPermille)
        {
            SummonDone[Index] = true;
            StartSide(Current.Summons[Index].Attack);
        }
    for (int32 Index = 0; Index < Current.OnceBelow.Num(); ++Index)
        if (!OnceDone[Index] && Permille <= Current.OnceBelow[Index].AtPermille)
        {
            OnceDone[Index] = true;
            StartSide(Current.OnceBelow[Index].Attack);
        }
    for (int32 Group = 0; Group < GroupRespawnAtMs.Num(); ++Group)
        if (GroupRespawnAtMs[Group] > 0 && Now >= GroupRespawnAtMs[Group])
        {
            GroupRespawnAtMs[Group] = 0;
            Summon(Group);
        }
    if (WardIndex != INDEX_NONE && WardRespawnAtMs > 0 && Now >= WardRespawnAtMs)
    {
        WardRespawnAtMs = 0;
        SpawnWards(WardIndex);
    }
    for (int32 Index = Exposures.Num() - 1; Index >= 0; --Index)
        if (Now >= Exposures[Index].UntilMs)
            CloseExposure(Index, false);
    if (HasBarrier())
    {
        const Rules::FBarrier Regenerated = Rules::RegeneratedBarrier({BarrierAtHitMilli, Info->Barrier.Health * 1000}, Now - BarrierHitMs,
            Info->Barrier.RegenDelayMs, Info->Barrier.RegenPerSecond);
        BarrierNowMilli = Regenerated.HealthMilli;
    }
    Zones.RemoveAll([](const TObjectPtr<ASoraBossHazard>& Zone) { return !IsValid(Zone) || Zone->IsSpent(); });
    WardActors.RemoveAll([](const TObjectPtr<ASoraBossHazard>& Guard) { return !IsValid(Guard); });
    // The weak points glow while open.
    for (int32 Index = 0; Index < PointParts.Num(); ++Index)
        if (UStaticMeshComponent* Part = PointParts[Index])
        {
            const bool bOpen = IsWeakPointOpen(Index);
            const bool bShown = Part->ComponentTags.Contains(TEXT("Open"));
            if (bOpen != bShown)
            {
                ASoraWorldBuilder::Tint(Part, bOpen ? SoraBossBody::Cyan : SoraBossBody::Dark);
                if (bOpen)
                    Part->ComponentTags.Add(TEXT("Open"));
                else
                    Part->ComponentTags.Remove(TEXT("Open"));
            }
            Part->SetVisibility(PointHealth[Index] != 0);
        }
}

void ASoraBoss::TickPlay(float DeltaSeconds)
{
    Super::TickPlay(DeltaSeconds);
    if (!Info || bDefeated)
        return;
    SyncPhase();
    RunTimers();
    ASoraCharacterBase* Target = Hero();
    const int32 Now = NowMs();
    // A blind hunter hears the hero's feet.
    if (Info->bBlind && Target)
    {
        const auto* Player = Cast<ASoraPlayerCharacter>(Target);
        const int32 Distance = FMath::RoundToInt32(FVector::Dist2D(Target->GetActorLocation(), GetActorLocation()));
        const FSoraBossHearing& Ears = Info->Hearing;
        if (BossRules::HearsSteps(Distance, FMath::RoundToInt32(Target->GetVelocity().Size2D()), Target->IsCrouched(),
                Player && Player->IsSprinting(), Ears.WalkCm, Ears.CrouchCm, Ears.SprintCm, Ears.StillCmPerSecond,
                Info->Phases[PhaseNow].HearingPermille))
        {
            KnownAt = Target->GetActorLocation();
            KnownAtMs = Now;
        }
    }
    AdvanceSides();
    Advance();
    // A shield advance shoves the hero aside; it never hurts.
    if (Target && IsShieldUp() && Run.Attack == INDEX_NONE && GetVelocity().Size2D() > 20.f && Now >= NextPushMs)
    {
        const FVector Delta = Target->GetActorLocation() - GetActorLocation();
        const float Reach = GetCapsuleComponent()->GetScaledCapsuleRadius() + SoraBossBody::HeroRadius + 40.f;
        if (Delta.Size2D() <= Reach && SoraDamage::FacingMilli(*this, Target->GetActorLocation()) >= Rules::FrontMilli)
        {
            Target->LaunchCharacter(Delta.GetSafeNormal2D() * 600.f + FVector(0.f, 0.f, 120.f), true, true);
            NextPushMs = Now + SoraBossBody::PushEveryMs;
        }
    }
}
void ASoraBoss::HaltActions()
{
    Super::HaltActions();
    if (Run.Attack != INDEX_NONE && GetWorld())
    {
        Run = FRun();
        NextStartMs = NowMs() + SoraBossBody::OpeningMs;
    }
}

FSoraBossIntent ASoraBoss::Drive(ASoraCharacterBase& Target, float)
{
    FSoraBossIntent Intent;
    if (!Info || bDefeated || !bPhaseEntered)
        return Intent;
    const FSoraBossPhase& Current = Info->Phases[PhaseNow];
    // Outflanked by a 転 step, it neither starts an attack nor turns until it can turn again.
    if (Run.Attack == INDEX_NONE && !IsStaggered() && !IsTurnLocked() && NowMs() >= InvulnerableUntilMs)
    {
        bool bPattern = false;
        int32 Next = INDEX_NONE;
        if (Forced != INDEX_NONE)
        {
            Next = Forced;
            Forced = INDEX_NONE;
        }
        else
            Next = Choose(Target, bPattern);
        if (Next != INDEX_NONE)
        {
            if (bPattern)
                StepDone = Step;
            if (bPattern && BeatOriginMs < 0)
                BeatOriginMs = NowMs();
            if (bPattern && Current.Pattern == ESoraBossPattern::Sequence)
                Step = Step + 1 < Current.Order.Num() ? Step + 1 : Current.LoopFrom;
            if (bPattern && Current.Pattern == ESoraBossPattern::Weighted)
                Picked = INDEX_NONE;
            LastStartMs = NowMs();
            Commit(Next, Target, bPattern, AttackAt(Next).Repeat - 1);
        }
    }
    if (Run.Attack != INDEX_NONE || IsStaggered())
        return Intent;
    const FVector Here = GetActorLocation();
    const bool bKnows = KnowsHero();
    const FVector Point = Info->bBlind ? KnownAt : Target.GetActorLocation();
    FVector Delta = Point - Here;
    Delta.Z = 0.f;
    const float Distance = Delta.Size2D();
    Intent.TurnDegreesPerSecond = Current.TurnDegreesPerSecond;
    Intent.bFace = bKnows && !Delta.IsNearlyZero() && !IsTurnLocked();
    Intent.Facing = Delta;
    switch (Current.Move)
    {
    case ESoraBossMove::Close:
        if (Distance > Current.NearCm)
        {
            Intent.bMove = true;
            Intent.Goal = ClampToArena(Point);
            Intent.AcceptanceCm = Current.NearCm;
        }
        break;
    case ESoraBossMove::Keep:
        if (Distance < Current.NearCm)
        {
            Intent.bMove = true;
            Intent.Goal = ClampToArena(Here - Delta.GetSafeNormal2D() * (Current.NearCm - Distance + 150.f));
            Intent.AcceptanceCm = 60.f;
        }
        else if (Distance > Current.FarCm)
        {
            Intent.bMove = true;
            Intent.Goal = ClampToArena(Point);
            Intent.AcceptanceCm = Current.FarCm;
        }
        break;
    case ESoraBossMove::Hunt:
        if (bKnows && Distance > Current.NearCm)
        {
            Intent.bMove = true;
            Intent.Goal = ClampToArena(Point);
            Intent.AcceptanceCm = Current.NearCm;
        }
        break;
    case ESoraBossMove::Hold:
        break;
    }
    return Intent;
}

bool ASoraBoss::InReach(int32 Index, const ASoraCharacterBase& Target) const
{
    const FSoraBossAttack& Attack = AttackAt(Index);
    const float Distance = FVector::Dist2D(TargetPoint(Target), GetActorLocation());
    switch (Attack.Kind)
    {
    case ESoraBossAttackKind::Zone:
    {
        TArray<FVector> Points;
        const float Away = FVector::Dist2D(Target.GetActorLocation(), GetActorLocation());
        return ZonePoints(Index, 0, Points) && (Attack.MaxActive == 0 || LiveZones(Index) < Attack.MaxActive) &&
            Away >= Attack.MinRangeCm && Away <= ReachFor(Index);
    }
    case ESoraBossAttackKind::Summon:
        return LiveAdds(Attack.Group) < Info->Adds[Attack.Group].MaxAlive;
    case ESoraBossAttackKind::Expose:
    case ESoraBossAttackKind::Pulse:
        return true;
    default:
        break;
    }
    if (Info->bBlind && !KnowsHero())
        return false;
    return Distance >= Attack.MinRangeCm && Distance <= ReachFor(Index);
}
bool ASoraBoss::FacesTarget(int32 Index, const FVector& Point) const
{
    const FSoraBossAttack& Attack = AttackAt(Index);
    const int32 Facing = SoraBossBody::CosineMilli(GetActorForwardVector(), Point - GetActorLocation());
    switch (Attack.Kind)
    {
    case ESoraBossAttackKind::Cut:
        return Attack.ArcMilli <= 0 || Facing >= FMath::Min(Attack.ArcMilli, 866);
    case ESoraBossAttackKind::Thrust:
    case ESoraBossAttackKind::Feint:
    case ESoraBossAttackKind::Beam:
    case ESoraBossAttackKind::Volley:
        return Facing >= 866;
    case ESoraBossAttackKind::Area:
        return Attack.ArcMilli <= -1000 || Facing >= FMath::Max(Attack.ArcMilli, 0);
    default:
        return true;
    }
}
bool ASoraBoss::Eligible(int32 Index, const ASoraCharacterBase& Target) const
{
    const FSoraBossAttack& Attack = AttackAt(Index);
    if (NowMs() < ReadyAtMs[Index] || !InReach(Index, Target) || !FacesTarget(Index, TargetPoint(Target)))
        return false;
    if (Attack.IfGuardHeldMs > 0)
    {
        const auto* Player = Cast<ASoraPlayerCharacter>(&Target);
        const USoraEquipmentComponent* Kit = Player ? Player->GetEquipment() : nullptr;
        return Kit && Kit->IsGuardHeld() && (GetWorld()->GetTimeSeconds() - Kit->GuardPressedAt()) * 1000.f >= Attack.IfGuardHeldMs;
    }
    return true;
}
int32 ASoraBoss::Choose(const ASoraCharacterBase& Target, bool& bPattern)
{
    bPattern = false;
    const FSoraBossPhase& Current = Info->Phases[PhaseNow];
    const int32 Now = NowMs();
    if (Now < NextStartMs || Now < HoldUntilMs)
        return INDEX_NONE;
    // At a fight's floor only the finishing blow comes, on its own beat.
    const int32 Floor = FloorPermille();
    if (Current.AtFloorAttack != INDEX_NONE && Floor > 0 &&
        FMath::RoundToInt32(Health) <= BossRules::PhaseHealth(FMath::RoundToInt32(MaxHealth), Floor))
    {
        if (Now < NextFloorAttackMs)
            return INDEX_NONE;
        NextFloorAttackMs = Now + Current.AtFloorEveryMs;
        return Current.AtFloorAttack;
    }
    if (FVector::Dist2D(TargetPoint(Target), GetActorLocation()) > Current.EngageCm)
        return INDEX_NONE;
    for (const int32 Reaction : Current.Reactions)
        if (Eligible(Reaction, Target))
            return Reaction;
    bPattern = true;
    switch (Current.Pattern)
    {
    case ESoraBossPattern::Sequence:
    {
        const int32 Next = Current.Order[Step];
        if (Eligible(Next, Target))
            return Next;
        return Current.Fallback != INDEX_NONE && Eligible(Current.Fallback, Target) ? Current.Fallback : INDEX_NONE;
    }
    case ESoraBossPattern::Priority:
        for (const int32 Next : Current.Order)
            if (Eligible(Next, Target))
                return Next;
        return INDEX_NONE;
    case ESoraBossPattern::Weighted:
    {
        if (Picked == INDEX_NONE)
        {
            const int32 Habit = FMath::Min(Lead, Current.Habits.Num() - 1);
            const FSoraBossHabit& Habitual = Current.Habits[Habit];
            int32 Weights[BossRules::MaxWeighted] = {};
            for (int32 Index = 0; Index < Habitual.Attacks.Num(); ++Index)
            {
                const bool bHalved = Setup.Difficulty == BossRules::EDifficulty::Easy && Current.EasyHalved.Contains(Habitual.Attacks[Index]);
                Weights[Index] = bHalved ? FMath::Max(1, Habitual.Weights[Index] / 2) : Habitual.Weights[Index];
            }
            const int32 Chosen = BossRules::PickWeighted(Habits[Habit], Weights, Habitual.Attacks.Num());
            Picked = Chosen >= 0 ? Habitual.Attacks[Chosen] : INDEX_NONE;
        }
        return Picked != INDEX_NONE && Eligible(Picked, Target) ? Picked : INDEX_NONE;
    }
    }
    return INDEX_NONE;
}

void ASoraBoss::Commit(int32 Index, ASoraCharacterBase& Target, bool bFromPattern, int32 RepeatsLeft)
{
    const FSoraBossAttack& Attack = AttackAt(Index);
    const int32 Now = NowMs();
    Run = FRun();
    Run.Attack = Index;
    Run.Serial = NextSerial++;
    Run.bFromPattern = bFromPattern;
    Run.RepeatsLeft = FMath::Max(0, RepeatsLeft);
    Run.WindupMs = WindupFor(Index);
    const FVector Point = TargetPoint(Target);
    FVector Direction = Point - GetActorLocation();
    Direction.Z = 0.f;
    Run.LockedDirection = Direction.IsNearlyZero() ? GetActorForwardVector().GetSafeNormal2D() : Direction.GetSafeNormal();
    Run.LockedPoint = Attack.Kind == ESoraBossAttackKind::Volley ? Target.GetActorLocation() + FVector(0.f, 0.f, SoraBossBody::ChestHeight) :
        Ground(Point);
    ReadyAtMs[Index] = Now + CooldownFor(Index);
    const bool bTurns = Attack.IsBlow() || Attack.Kind == ESoraBossAttackKind::Feint || Attack.Kind == ESoraBossAttackKind::Beam ||
        Attack.Kind == ESoraBossAttackKind::Volley || Attack.Kind == ESoraBossAttackKind::Charge ||
        (Attack.Kind == ESoraBossAttackKind::Area && Attack.ArcMilli > -1000);
    if (bTurns)
        SetActorRotation(Run.LockedDirection.Rotation());
    GetCharacterMovement()->StopMovementImmediately();
    if (Attack.Kind == ESoraBossAttackKind::Volley && Attack.DashCm > 0)
    {
        // A sidestep first; the lock and its telegraph come after it.
        const FVector Side = FVector(-Run.LockedDirection.Y, Run.LockedDirection.X, 0.f) * (Run.Serial % 2 ? 1.f : -1.f);
        Run.Stage = EStage::Dash;
        Run.StageStartMs = Now;
        Run.StageEndsMs = Now + SoraBossBody::DashMs;
        Run.From = GetActorLocation();
        Run.To = ClampToArena(Run.From + Side * Attack.DashCm);
        return;
    }
    Run.Stage = EStage::Windup;
    Run.StageStartMs = Now;
    Run.StageEndsMs = Now + Run.WindupMs;
    Broadcast(ESoraBossPhase::Windup, Attack.Id, BarkLine(Attack), Run.Serial, Run.WindupMs);
    if (Attack.IsBlow() || Attack.Kind == ESoraBossAttackKind::Feint)
        if (USoraGameEvents* Events = USoraGameEvents::Get(this))
        {
            FSoraMeleeCommittedEvent Committed;
            Committed.Attacker = this; Committed.WeaponId = WeaponId; Committed.Direction = Run.LockedDirection;
            Committed.WindupSeconds = Run.WindupMs / 1000.f;
            Events->OnMeleeCommitted.Broadcast(Committed);
        }
    if (Attack.Kind == ESoraBossAttackKind::Zone)
        PlaceZones(Index, Run.Serial, Run.WindupMs);
    Telegraph(Attack, SoraBossBody::VisualMs / 1000.f + .02f);
    Run.NextVisualMs = Now + SoraBossBody::VisualMs;
}

void ASoraBoss::Telegraph(const FSoraBossAttack& Attack, float Life)
{
    if (Attack.Telegraph == ESoraBossTelegraph::None)
        return;
    UWorld* World = GetWorld();
    const FLinearColor Shade = SoraBossBody::TelegraphColor(this, Attack.Telegraph);
    const float Scale = GetActorScale3D().Z;
    const FVector EyePoint = GetActorLocation() + FVector(0.f, 0.f, SoraBossBody::EyeHeight * Scale);
    const FVector Feet = GetActorLocation() - FVector(0.f, 0.f, GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - 3.f);
    const FVector& Direction = Run.LockedDirection;
    const int32 Index = Run.Attack;
    switch (Attack.Kind)
    {
    case ESoraBossAttackKind::Cut:
    case ESoraBossAttackKind::Feint:
    {
        // A feint's tell is its tilted blade: a narrow wedge, never a full arc.
        const float Half = Attack.Kind == ESoraBossAttackKind::Feint ? 15.f :
            FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(Attack.ArcMilli / 1000.f, -1.f, 1.f)));
        const float Reach = Attack.Kind == ESoraBossAttackKind::Feint ? 220.f : ReachFor(Index);
        if (Attack.ArcMilli <= -1000)
            SoraDamage::Ring(World, Feet, Reach, Shade, Life);
        else
            for (const float Side : {-1.f, 1.f})
                SoraDamage::Beam(World, EyePoint, EyePoint + Direction.RotateAngleAxis(Side * Half, FVector::UpVector) * Reach, Shade, 3.f, Life);
        return;
    }
    case ESoraBossAttackKind::Thrust:
        SoraDamage::Beam(World, Feet, Feet + Direction * ReachFor(Index), Shade, Attack.WidthCm * .05f, Life);
        return;
    case ESoraBossAttackKind::Area:
        SoraDamage::Ring(World, Feet, Attack.RadiusCm, Shade, Life);
        if (Attack.InnerRadiusCm > 0 && Attack.InnerRadiusCm < Attack.RadiusCm)
            SoraDamage::Ring(World, Feet, Attack.InnerRadiusCm, Shade, Life);
        return;
    case ESoraBossAttackKind::Beam:
        if (Attack.SweepDegrees > 0)
            for (const float Side : {-.5f, .5f})
                SoraDamage::Beam(World, Feet, Feet + Direction.RotateAngleAxis(Side * Attack.SweepDegrees, FVector::UpVector) * ReachFor(Index),
                    Shade, 3.f, Life);
        else
            SoraDamage::Beam(World, Feet, Feet + Direction * ReachFor(Index), Shade, 3.f, Life);
        return;
    case ESoraBossAttackKind::Volley:
        SoraDamage::Beam(World, EyePoint, Run.LockedPoint, Shade, .8f, Life);
        return;
    case ESoraBossAttackKind::Charge:
        SoraDamage::Ring(World, Run.LockedPoint, Attack.RadiusCm, Shade, Life);
        if (Attack.WidthCm > 0)
            SoraDamage::Beam(World, Feet, Run.LockedPoint, Shade, Attack.WidthCm * .05f, Life);
        return;
    default:
        return;
    }
}

void ASoraBoss::Advance()
{
    if (Run.Attack == INDEX_NONE)
        return;
    ASoraCharacterBase* Target = Hero();
    if ((!Target || !Target->IsAlive()) && Run.Stage != EStage::Recovery)
        Recover(RecoveryFor(Run.Attack));
    const FSoraBossAttack& Attack = AttackAt(Run.Attack);
    const int32 Now = NowMs();
    switch (Run.Stage)
    {
    case EStage::Dash:
    {
        const float Alpha = FMath::Clamp((Now - Run.StageStartMs) / static_cast<float>(SoraBossBody::DashMs), 0.f, 1.f);
        SetActorLocation(FMath::Lerp(Run.From, Run.To, Alpha), true);
        if (Now >= Run.StageEndsMs && Target)
        {
            const FVector Chest = Target->GetActorLocation() + FVector(0.f, 0.f, SoraBossBody::ChestHeight);
            Run.LockedDirection = (Chest - GetActorLocation()).GetSafeNormal2D();
            Run.LockedPoint = Chest;
            SetActorRotation(Run.LockedDirection.Rotation());
            Run.Stage = EStage::Windup;
            Run.StageStartMs = Now;
            Run.StageEndsMs = Now + Run.WindupMs;
            Broadcast(ESoraBossPhase::Windup, Attack.Id, BarkLine(Attack), Run.Serial, Run.WindupMs);
        }
        return;
    }
    case EStage::Windup:
        if (Attack.Kind == ESoraBossAttackKind::Beam && Target && Now - Run.StageStartMs < Attack.TrackMs && !IsTurnLocked())
        {
            // The beam tracks, then locks for the rest of its windup.
            const FVector Direction = (Target->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
            if (!Direction.IsNearlyZero())
            {
                Run.LockedDirection = Direction;
                SetActorRotation(Direction.Rotation());
            }
        }
        if (Now >= Run.NextVisualMs)
        {
            Telegraph(Attack, SoraBossBody::VisualMs / 1000.f + .02f);
            Run.NextVisualMs = Now + SoraBossBody::VisualMs;
        }
        if (Now >= Run.StageEndsMs && Target)
            Release(*Target);
        return;
    case EStage::Hold:
        if (Now >= Run.StageEndsMs && Target && !IsTurnLocked())
        {
            const int32 Then = Attack.Then;
            Commit(Then, *Target, Run.bFromPattern, AttackAt(Then).Repeat - 1);
        }
        return;
    case EStage::Active:
        if (!Target)
            return;
        switch (Attack.Kind)
        {
        case ESoraBossAttackKind::Cut:
        case ESoraBossAttackKind::Thrust:
            while (Run.Stage == EStage::Active && Run.HitsDone < Attack.Hits && Now >= Run.StageStartMs + Run.HitsDone * Attack.GapMs)
            {
                StrikeBlow(*Target);
                if (bDefeated)
                    return;
            }
            return;
        case ESoraBossAttackKind::Area:
            while (Run.Stage == EStage::Active && Run.HitsDone < Attack.Hits && Now >= Run.StageStartMs + Run.HitsDone * Attack.GapMs)
                StrikeArea(*Target);
            break;
        case ESoraBossAttackKind::Beam:
            if (Attack.SweepDegrees > 0 && !Run.bLanded)
            {
                const float Alpha = FMath::Clamp((Now - Run.StageStartMs) / static_cast<float>(FMath::Max(1, ActiveFor(Run.Attack))), 0.f, 1.f);
                StrikeBeam(*Target, Run.LockedDirection.RotateAngleAxis((Alpha - .5f) * Attack.SweepDegrees, FVector::UpVector));
            }
            break;
        case ESoraBossAttackKind::Volley:
            while (Run.Stage == EStage::Active && Run.HitsDone < Attack.Rounds && Now >= Run.StageStartMs + Run.HitsDone * Attack.IntervalMs)
                StrikeRound(*Target);
            return;
        case ESoraBossAttackKind::Charge:
        case ESoraBossAttackKind::Step:
        {
            const float Alpha = FMath::Clamp((Now - Run.StageStartMs) / static_cast<float>(FMath::Max(1, ActiveFor(Run.Attack))), 0.f, 1.f);
            MoveAlong(Alpha);
            if (Alpha >= 1.f)
            {
                if (Attack.Kind == ESoraBossAttackKind::Charge)
                    Land(*Target);
                else
                    AfterActive();
            }
            return;
        }
        default:
            break;
        }
        if (Run.Stage == EStage::Active && Now >= Run.StageStartMs + ActiveFor(Run.Attack))
            AfterActive();
        return;
    case EStage::Gap:
        // The next repeat aims anew, once the boss can turn to it.
        if (Now >= Run.StageEndsMs && Target && !IsTurnLocked())
            Commit(Run.Attack, *Target, Run.bFromPattern, Run.RepeatsLeft - 1);
        return;
    case EStage::Recovery:
        if (Now >= Run.StageEndsMs && !IsStaggered())
            Finish();
        return;
    case EStage::Idle:
        return;
    }
}

void ASoraBoss::Release(ASoraCharacterBase& Target)
{
    const FSoraBossAttack& Attack = AttackAt(Run.Attack);
    const int32 Now = NowMs();
    Run.StageStartMs = Now;
    Run.HitsDone = 0;
    switch (Attack.Kind)
    {
    case ESoraBossAttackKind::Feint:
        Run.Stage = EStage::Hold;
        Run.StageEndsMs = Now + Attack.HoldMs;
        return;
    case ESoraBossAttackKind::Cut:
    case ESoraBossAttackKind::Thrust:
        if (Attack.LungeCm > 0)
        {
            // The lunge closes the committed line, stopping short of the hero.
            const float Along = FVector::DotProduct(Target.GetActorLocation() - GetActorLocation(), Run.LockedDirection);
            const float Travel = FMath::Clamp(Along - 90.f * GetActorScale3D().X, 0.f, static_cast<float>(Attack.LungeCm));
            SetActorLocation(ClampToArena(GetActorLocation() + Run.LockedDirection * Travel), true);
        }
        Run.Stage = EStage::Active;
        return;
    case ESoraBossAttackKind::Area:
    case ESoraBossAttackKind::Volley:
        Run.Stage = EStage::Active;
        return;
    case ESoraBossAttackKind::Beam:
        Run.Stage = EStage::Active;
        if (USoraGameEvents* Events = USoraGameEvents::Get(this))
        {
            FSoraWeaponFiredEvent Fired;
            Fired.Shooter = this; Fired.Kind = ESoraShotKind::Beam; Fired.Direction = Run.LockedDirection;
            Fired.Origin = GetActorLocation(); Fired.End = GetActorLocation() + Run.LockedDirection * ReachFor(Run.Attack);
            Events->OnWeaponFired.Broadcast(Fired);
        }
        if (Attack.SweepDegrees == 0)
            StrikeBeam(Target, Run.LockedDirection);
        return;
    case ESoraBossAttackKind::Charge:
    {
        Run.From = GetActorLocation();
        FVector Landing = Run.LockedPoint;
        Landing.Z = Run.From.Z;
        const FVector Travel = Landing - Run.From;
        Run.To = ClampToArena(Run.From + Travel.GetClampedToMaxSize2D(ReachFor(Run.Attack)));
        Run.Stage = EStage::Active;
        return;
    }
    case ESoraBossAttackKind::Step:
    {
        Run.From = GetActorLocation();
        const float Along = FVector::Dist2D(Target.GetActorLocation(), Run.From);
        Run.To = ClampToArena(Run.From + Run.LockedDirection * FMath::Clamp(Along - 150.f, 0.f, static_cast<float>(Attack.LungeCm)));
        Run.Stage = EStage::Active;
        return;
    }
    case ESoraBossAttackKind::Summon:
        Summon(Attack.Group);
        AfterActive();
        return;
    case ESoraBossAttackKind::Expose:
        Expose(Run.Attack, Run.Serial);
        Run.Stage = EStage::Active;
        return;
    case ESoraBossAttackKind::Zone:
    case ESoraBossAttackKind::Pulse:
        // The zones keep their own time; a pulse runs beside the pattern.
        AfterActive();
        return;
    }
}

void ASoraBoss::AfterActive()
{
    if (Run.RepeatsLeft > 0)
    {
        Run.Stage = EStage::Gap;
        Run.StageStartMs = NowMs();
        Run.StageEndsMs = Run.StageStartMs + AttackAt(Run.Attack).RepeatGapMs;
        return;
    }
    Recover(RecoveryFor(Run.Attack));
}

void ASoraBoss::Recover(int32 Milliseconds)
{
    const FSoraBossPhase& Current = Info->Phases[PhaseNow];
    int32 Bonus = 0;
    if (Current.Pattern == ESoraBossPattern::Weighted && Run.bFromPattern)
        Bonus = Current.Habits[FMath::Min(Lead, Current.Habits.Num() - 1)].RecoveryBonusMs;
    Run.Stage = EStage::Recovery;
    Run.StageStartMs = NowMs();
    Run.StageEndsMs = Run.StageStartMs + Milliseconds + Bonus;
    Broadcast(ESoraBossPhase::Recovery, AttackAt(Run.Attack).Id, NAME_None, Run.Serial);
}

void ASoraBoss::Finish()
{
    const FSoraBossPhase& Current = Info->Phases[PhaseNow];
    const FSoraBossAttack& Attack = AttackAt(Run.Attack);
    const bool bPattern = Run.bFromPattern;
    const bool bMeasureReset = Run.bParried && Attack.OnParry == ESoraBossParry::MeasureReset;
    const int32 Now = NowMs();
    Run = FRun();
    NextStartMs = FMath::Max(NextStartMs, Now);
    if (!bPattern)
        return;
    switch (Current.Pattern)
    {
    case ESoraBossPattern::Sequence:
        if (Current.BeatMs > 0)
        {
            // A parried cut restarts its measure after the pause; a finished
            // measure pauses; the next cut falls on the metronome's beat.
            int32 Free = Now;
            if (bMeasureReset)
            {
                Step = StepDone / Current.Measure * Current.Measure;
                Free += Current.PauseMs;
            }
            else if (StepDone % Current.Measure == Current.Measure - 1)
                Free += Current.PauseMs;
            NextStartMs = BossRules::NextBeat(Free, BeatOriginMs < 0 ? PhaseStartedMs : BeatOriginMs, Current.BeatMs);
        }
        else if (!Current.CadenceMs.IsEmpty())
            NextStartMs = FMath::Max(Now, LastStartMs + Current.CadenceMs[StepDone % Current.CadenceMs.Num()]);
        else if (!Current.GapMs.IsEmpty())
            NextStartMs = Now + Current.GapMs[StepDone % Current.GapMs.Num()];
        return;
    case ESoraBossPattern::Priority:
        NextStartMs = Now + (Current.GapMs.IsEmpty() ? 0 : Current.GapMs[0]);
        return;
    case ESoraBossPattern::Weighted:
    {
        const FSoraBossHabit& Habitual = Current.Habits[FMath::Min(Lead, Current.Habits.Num() - 1)];
        NextStartMs = Now + BossRules::IntervalMs(Habitual.MinIntervalMs, Habitual.MaxIntervalMs, HabitStep++);
        return;
    }
    }
}

void ASoraBoss::IgnoreOwn(FCollisionQueryParams& Query) const
{
    // Its own wards and zones never stand between it and the hero.
    for (AActor* Guard : WardActors)
        Query.AddIgnoredActor(Guard);
    for (AActor* Zone : Zones)
        Query.AddIgnoredActor(Zone);
}

float ASoraBoss::StrikeHero(ASoraCharacterBase& Target, int32 Damage, const FSoraHit& Hit, const FVector& Direction)
{
    FHitResult Trace;
    Trace.ImpactPoint = Target.GetActorLocation();
    Trace.Location = Trace.ImpactPoint;
    return SoraDamage::Strike(&Target, Damage, Hit, Direction, Trace, GetController(), this);
}

void ASoraBoss::StrikeBlow(ASoraCharacterBase& Target)
{
    const FSoraBossAttack& Attack = AttackAt(Run.Attack);
    const int32 Index = Run.Attack;
    const int32 Serial = Run.Serial;
    const int32 HitNumber = ++Run.HitsDone;
    // The blow is out: its recovery starts before it resolves, so a parry's
    // stagger lands on that recovery instead of cancelling a spent windup.
    if (HitNumber >= Attack.Hits)
        AfterActive();
    const float Scale = GetActorScale3D().Z;
    const FVector EyePoint = GetActorLocation() + FVector(0.f, 0.f, SoraBossBody::EyeHeight * Scale);
    const FVector Delta = Target.GetActorLocation() - GetActorLocation();
    const float Distance = Delta.Size2D();
    const float Reach = ReachFor(Index) + SoraBossBody::HeroRadius;
    bool bReach = false;
    if (Attack.Kind == ESoraBossAttackKind::Thrust)
    {
        const float Along = FVector::DotProduct(Delta, Run.LockedDirection);
        const float Across = FVector::Dist2D(Target.GetActorLocation(), GetActorLocation() + Run.LockedDirection * Along);
        bReach = Along >= 0.f && Along <= Reach && Across <= Attack.WidthCm * .5f + SoraBossBody::HeroRadius;
    }
    else
        bReach = Distance >= Attack.MinRangeCm && Distance <= Reach &&
            (Attack.ArcMilli <= -1000 || SoraBossBody::CosineMilli(Run.LockedDirection, Delta) >= Attack.ArcMilli);
    FHitResult Line;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraBossBlow), false, this);
    IgnoreOwn(Query);
    GetWorld()->LineTraceSingleByChannel(Line, EyePoint, Target.GetActorLocation() + FVector(0.f, 0.f, SoraBossBody::ChestHeight),
        ECC_Visibility, Query);
    bReach &= Line.GetActor() == &Target;
    // The hero rolled off this blow's line (転).
    bReach &= EvadedSerial != Serial;
    AnnounceStrike(Index, Serial);
    SoraDamage::Beam(GetWorld(), EyePoint, EyePoint + Run.LockedDirection * ReachFor(Index), SoraBossBody::Steel, 2.f, .13f);
    FSoraStrikeResolvedEvent Resolved;
    Resolved.Attacker = this;
    if (bReach)
    {
        FSoraHit Hit = FSoraHit::Melee(EyePoint, INDEX_NONE);
        Hit.AttackId = Attack.Id;
        Hit.bParryable = Attack.Guard.bParry && (Attack.Guard.ParryHit == 0 || Attack.Guard.ParryHit == HitNumber);
        Hit.GuardChip = Attack.Guard.bGuardable ? Attack.Guard.Chip : Attack.Damage;
        Hit.GuardStamina = Attack.Guard.Stamina;
        Hit.ParryStaggerMs = Attack.Guard.ParryStaggerMs;
        Hit.bBreaksGuard = Attack.Guard.bBreaks;
        Hit.bUnguardable = !Attack.Guard.bGuardable;
        Hit.KnockbackCm = Attack.KnockbackCm;
        Hit.HeroStaggerMs = Attack.HeroStaggerMs;
        Hit.MutoWindowMs = Attack.bMuto && Info->bMutoFinisher ? MutoWindowMs() : 0;
        const auto* Player = Cast<ASoraPlayerCharacter>(&Target);
        const bool bGuarding = Player && Player->GetEquipment()->IsGuardHeld() && !Player->GetEquipment()->IsSheathed();
        Resolved.Target = &Target;
        Resolved.Damage = StrikeHero(Target, Attack.Damage, Hit, Run.LockedDirection);
        Resolved.bHit = Resolved.Damage > 0;
        if (bDefeated)
            return;
        // A tether that was not cut drags the hero toward the heat (or its
        // wielder); a guard halves the pull. The parry's stagger may already
        // have ended the run (a repeated lash between its blows), so the cut
        // is known by the blow's own serial.
        if (Attack.PullCm > 0 && ParriedSerial != Serial)
        {
            FVector Toward = GetActorLocation();
            float Best = MAX_flt;
            for (const TPair<FName, FVector>& Anchor : Anchors)
                if (Anchor.Key == TEXT("heat_slot") && FVector::Dist2D(Anchor.Value, Target.GetActorLocation()) < Best)
                {
                    Best = FVector::Dist2D(Anchor.Value, Target.GetActorLocation());
                    Toward = Anchor.Value;
                }
            const float Pull = bGuarding ? Attack.PullCm * .5f : Attack.PullCm;
            Target.LaunchCharacter((Toward - Target.GetActorLocation()).GetSafeNormal2D() * Pull * 3.f + FVector(0.f, 0.f, 150.f), true, true);
        }
    }
    if (USoraGameEvents* Events = USoraGameEvents::Get(this))
        Events->OnStrikeResolved.Broadcast(Resolved);
}

void ASoraBoss::StrikeArea(ASoraCharacterBase& Target)
{
    const FSoraBossAttack& Attack = AttackAt(Run.Attack);
    const int32 HitNumber = ++Run.HitsDone;
    const FVector Delta = Target.GetActorLocation() - GetActorLocation();
    const float Distance = Delta.Size2D();
    const bool bInside = Distance <= Attack.RadiusCm + SoraBossBody::HeroRadius &&
        (Attack.ArcMilli <= -1000 || SoraBossBody::CosineMilli(Run.LockedDirection, Delta) >= Attack.ArcMilli);
    const int32 Damage = Distance <= Attack.InnerRadiusCm + SoraBossBody::HeroRadius ? Attack.Damage : Attack.EdgeDamage;
    const FVector Feet = GetActorLocation() - FVector(0.f, 0.f, GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - 3.f);
    AnnounceStrike(Run.Attack, Run.Serial);
    SoraDamage::Ring(GetWorld(), Feet, Attack.RadiusCm, SoraBossBody::StrikeColor(this, ESoraBossTelegraph::Amber), .2f);
    if (bInside && Damage > 0)
    {
        FSoraHit Hit = FSoraHit::Melee(GetActorLocation(), INDEX_NONE);
        Hit.AttackId = Attack.Id;
        Hit.GuardChip = Attack.Guard.bGuardable ? Attack.Guard.Chip : Damage;
        Hit.GuardStamina = Attack.Guard.Stamina;
        Hit.bBreaksGuard = Attack.Guard.bBreaks;
        Hit.bUnguardable = !Attack.Guard.bGuardable;
        Hit.ParryStaggerMs = 0;
        Hit.KnockbackCm = Attack.KnockbackCm;
        Hit.HeroStaggerMs = Attack.HeroStaggerMs;
        StrikeHero(Target, Damage, Hit, Delta.GetSafeNormal2D());
    }
    // After its last blow the area leaves its body open.
    if (HitNumber >= Attack.Hits && !Attack.Opens.IsEmpty())
    {
        const int32 Until = NowMs() + Attack.OpensMs;
        for (const int32 Point : Attack.Opens)
            PointOpenUntilMs[Point] = FMath::Max(PointOpenUntilMs[Point], Until);
        Broadcast(ESoraBossPhase::Event, TEXT("opened"), NAME_None, Run.Serial);
    }
}

void ASoraBoss::StrikeBeam(ASoraCharacterBase& Target, const FVector& Direction)
{
    const FSoraBossAttack& Attack = AttackAt(Run.Attack);
    const float Scale = GetActorScale3D().Z;
    const FVector Base = GetActorLocation() - FVector(0.f, 0.f, GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    const FVector From = Attack.HeightCm > 0 ? Base + FVector(0.f, 0.f, Attack.HeightCm) :
        GetActorLocation() + FVector(0.f, 0.f, SoraBossBody::EyeHeight * Scale);
    const FVector Flat = Direction.GetSafeNormal2D();
    const float Reach = ReachFor(Run.Attack);
    const FVector There = Target.GetActorLocation();
    const float Along = FVector::DotProduct(There - From, Flat);
    const float Across = FVector::Dist2D(There, From + Flat * Along);
    // Walls and stone stop the beam; bodies do not.
    FCollisionObjectQueryParams Solid;
    Solid.AddObjectTypesToQuery(ECC_WorldStatic);
    Solid.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraBossBeam), false, this);
    Query.AddIgnoredActor(&Target);
    IgnoreOwn(Query);
    const bool bClear = !GetWorld()->LineTraceTestByObjectType(From, FVector(There.X, There.Y, From.Z), Solid, Query);
    const bool bHit = Along >= 0.f && Along <= Reach && Across <= Attack.WidthCm * .5f + SoraBossBody::HeroRadius && bClear;
    if (Attack.SweepDegrees == 0 || bHit)
        AnnounceStrike(Run.Attack, Run.Serial);
    SoraDamage::Beam(GetWorld(), From, From + Flat * Reach, SoraBossBody::StrikeColor(this, ESoraBossTelegraph::Cyan), 8.f, .1f);
    if (!bHit)
        return;
    Run.bLanded = true;
    FSoraHit Hit = FSoraHit::Beam(From);
    Hit.AttackId = Attack.Id;
    StrikeHero(Target, Attack.Damage, Hit, Flat);
}

void ASoraBoss::StrikeRound(ASoraCharacterBase& Target)
{
    const FSoraBossAttack& Attack = AttackAt(Run.Attack);
    const int32 Round = ++Run.HitsDone;
    const float Scale = GetActorScale3D().Z;
    const FVector EyePoint = GetActorLocation() + FVector(0.f, 0.f, SoraBossBody::EyeHeight * Scale);
    const FVector Chest = Target.GetActorLocation() + FVector(0.f, 0.f, SoraBossBody::ChestHeight);
    FHitResult Line;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraBossRound), false, this);
    IgnoreOwn(Query);
    GetWorld()->LineTraceSingleByChannel(Line, EyePoint, Chest, ECC_Visibility, Query);
    const bool bHolds = BossRules::LockHolds(FMath::RoundToInt32(FVector::Dist(Chest, Run.LockedPoint)), Attack.LockCm);
    AnnounceStrike(Run.Attack, Run.Serial);
    SoraDamage::Beam(GetWorld(), EyePoint, Run.LockedPoint, FLinearColor(1.f, .12f, .3f), 1.7f);
    if (USoraGameEvents* Events = USoraGameEvents::Get(this))
    {
        FSoraWeaponFiredEvent Fired;
        Fired.Shooter = this; Fired.Origin = EyePoint; Fired.Direction = (Run.LockedPoint - EyePoint).GetSafeNormal(); Fired.End = Run.LockedPoint;
        Events->OnWeaponFired.Broadcast(Fired);
    }
    if (bHolds && Line.GetActor() == &Target)
    {
        FSoraHit Hit = FSoraHit::Ranged(EyePoint, INDEX_NONE);
        Hit.AttackId = Attack.Id;
        StrikeHero(Target, Attack.Damage, Hit, (Chest - EyePoint).GetSafeNormal());
    }
    if (Round >= Attack.Rounds && Run.Stage == EStage::Active)
        AfterActive();
}

void ASoraBoss::MoveAlong(float Alpha)
{
    const FSoraBossAttack& Attack = AttackAt(Run.Attack);
    const FVector Before = GetActorLocation();
    FVector Next = FMath::Lerp(Run.From, Run.To, Alpha);
    Next.Z = Before.Z;
    SetActorLocation(Next, true);
    // A charge's lane strikes whoever it passes, once.
    ASoraCharacterBase* Target = Hero();
    if (Attack.Kind != ESoraBossAttackKind::Charge || Attack.WidthCm <= 0 || Run.bLanded || !Target)
        return;
    const FVector After = GetActorLocation();
    const FVector Closest = FMath::ClosestPointOnSegment(Target->GetActorLocation(), Before, After);
    if (FVector::Dist2D(Closest, Target->GetActorLocation()) > Attack.WidthCm * .5f + SoraBossBody::HeroRadius)
        return;
    Run.bLanded = true;
    AnnounceStrike(Run.Attack, Run.Serial);
    FSoraHit Hit = FSoraHit::Melee(Before, INDEX_NONE);
    Hit.AttackId = Attack.Id;
    Hit.GuardChip = Attack.Guard.bGuardable ? Attack.Guard.Chip : Attack.Damage;
    Hit.GuardStamina = Attack.Guard.Stamina;
    Hit.bUnguardable = !Attack.Guard.bGuardable;
    Hit.KnockbackCm = Attack.KnockbackCm;
    StrikeHero(*Target, Attack.Damage, Hit, (After - Before).GetSafeNormal2D());
}

void ASoraBoss::Land(ASoraCharacterBase& Target)
{
    const FSoraBossAttack& Attack = AttackAt(Run.Attack);
    const int32 Distance = FMath::RoundToInt32(FVector::Dist2D(Target.GetActorLocation(), GetActorLocation()));
    const FVector Feet = GetActorLocation() - FVector(0.f, 0.f, GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - 3.f);
    AnnounceStrike(Run.Attack, Run.Serial);
    SoraDamage::Ring(GetWorld(), Feet, Attack.RadiusCm, SoraBossBody::StrikeColor(this, ESoraBossTelegraph::Amber), .2f);
    if (!Run.bLanded && BossRules::Lands(Distance, Attack.RadiusCm + FMath::RoundToInt32(SoraBossBody::HeroRadius)))
    {
        Run.bLanded = true;
        FSoraHit Hit = FSoraHit::Melee(Feet + FVector(0.f, 0.f, 100.f), INDEX_NONE);
        Hit.AttackId = Attack.Id;
        Hit.GuardChip = Attack.Guard.bGuardable ? Attack.Guard.Chip : Attack.Damage;
        Hit.GuardStamina = Attack.Guard.Stamina;
        Hit.bUnguardable = !Attack.Guard.bGuardable;
        Hit.KnockbackCm = Attack.KnockbackCm;
        StrikeHero(Target, Attack.Damage, Hit, (Target.GetActorLocation() - GetActorLocation()).GetSafeNormal2D());
    }
    // What it pounced on is spent; it must hear again.
    if (Info->bBlind)
        KnownAtMs = MIN_int32 / 2;
    if (!Run.bLanded)
        Broadcast(ESoraBossPhase::Event, TEXT("missed"), EventBark(TEXT("missed")), Run.Serial);
    if (Run.RepeatsLeft > 0)
    {
        AfterActive();
        return;
    }
    Recover(BossRules::ChargeRecoveryMs(Run.bLanded, RecoveryFor(Run.Attack), Attack.MissRecoveryMs));
}

void ASoraBoss::StartSide(int32 Index)
{
    const FSoraBossAttack& Attack = AttackAt(Index);
    const int32 Now = NowMs();
    if (Attack.Kind == ESoraBossAttackKind::Zone)
    {
        TArray<FVector> Points;
        if (!ZonePoints(Index, NextSerial, Points))
            return;
        const int32 Serial = NextSerial++;
        const int32 Windup = WindupFor(Index);
        Broadcast(ESoraBossPhase::Windup, Attack.Id, BarkLine(Attack), Serial, Windup);
        PlaceZones(Index, Serial, Windup);
        return;
    }
    if (Attack.Kind == ESoraBossAttackKind::Summon && LiveAdds(Attack.Group) >= Info->Adds[Attack.Group].MaxAlive)
        return;
    FSide Side;
    Side.Attack = Index;
    Side.Serial = NextSerial++;
    Side.StartMs = Now;
    Side.WindupMs = WindupFor(Index);
    Sides.Add(Side);
    Broadcast(ESoraBossPhase::Windup, Attack.Id, BarkLine(Attack), Side.Serial, Side.WindupMs);
}

void ASoraBoss::AdvanceSides()
{
    const int32 Now = NowMs();
    ASoraCharacterBase* Target = Hero();
    for (int32 Index = Sides.Num() - 1; Index >= 0; --Index)
    {
        FSide& Side = Sides[Index];
        const FSoraBossAttack& Attack = AttackAt(Side.Attack);
        if (!Side.bReleased)
        {
            if (Now < Side.StartMs + Side.WindupMs)
                continue;
            Side.bReleased = true;
            Side.EndsMs = Now + Attack.ExpandMs;
            AnnounceStrike(Side.Attack, Side.Serial);
            if (Attack.Kind == ESoraBossAttackKind::Summon)
            {
                Summon(Attack.Group);
                Sides.RemoveAt(Index);
                continue;
            }
            if (Attack.Kind == ESoraBossAttackKind::Expose)
            {
                Expose(Side.Attack, Side.Serial);
                Sides.RemoveAt(Index);
                continue;
            }
        }
        if (Attack.Kind != ESoraBossAttackKind::Pulse)
        {
            Sides.RemoveAt(Index);
            continue;
        }
        // The sonar ring expands; as its front passes a moving hero, he is found.
        const int32 Front = BossRules::PulseFrontCm(Now - (Side.EndsMs - Attack.ExpandMs), Attack.ExpandMs, Attack.RadiusCm);
        const FVector Feet = GetActorLocation() - FVector(0.f, 0.f, GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - 5.f);
        SoraDamage::Ring(GetWorld(), Feet, FMath::Max(50, Front), SoraBossBody::TelegraphColor(this, ESoraBossTelegraph::Cyan), .05f);
        if (Target && !Side.bTested && Front >= FMath::RoundToInt32(FVector::Dist2D(Target->GetActorLocation(), GetActorLocation())))
        {
            Side.bTested = true;
            if (BossRules::PulseReveals(FMath::RoundToInt32(Target->GetVelocity().Size2D()), Attack.RevealCmPerSecond, false))
            {
                KnownAt = Target->GetActorLocation();
                KnownAtMs = Now;
                Broadcast(ESoraBossPhase::Event, TEXT("revealed"), NAME_None, Side.Serial);
            }
        }
        if (Now >= Side.EndsMs)
            Sides.RemoveAt(Index);
    }
}

bool ASoraBoss::ZonePoints(int32 Index, int32 Serial, TArray<FVector>& Points) const
{
    const FSoraBossAttack& Attack = AttackAt(Index);
    const ASoraCharacterBase* Target = Hero();
    if (!Target)
        return false;
    const FVector Feet = Target->GetActorLocation() - FVector(0.f, 0.f, Target->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    const auto Around = [&](int32 Count, float Spread)
    {
        for (int32 Point = 0; Point < Count; ++Point)
        {
            const float Angle = FMath::DegreesToRadians(Serial * 37.f + Point * 360.f / FMath::Max(1, Count));
            Points.Add(Feet + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.f) * Spread);
        }
    };
    switch (Attack.At)
    {
    case ESoraZoneAt::Target:
        Points.Add(Feet);
        break;
    case ESoraZoneAt::AroundTarget:
        Points.Add(Feet);
        Around(Attack.Count - 1, Attack.SpreadCm);
        break;
    case ESoraZoneAt::Anchor:
    case ESoraZoneAt::AnchorOrTarget:
    {
        TArray<FVector> Found;
        for (const TPair<FName, FVector>& Anchor : Anchors)
            if (Anchor.Key == Attack.Anchor && (Attack.At == ESoraZoneAt::Anchor || FVector::Dist2D(Anchor.Value, Feet) <= 1500.f))
                Found.Add(Anchor.Value);
        Found.Sort([&Feet](const FVector& A, const FVector& B) { return FVector::DistSquared2D(A, Feet) < FVector::DistSquared2D(B, Feet); });
        const int32 Wanted = Attack.Count == 0 ? Found.Num() : Attack.Count;
        for (int32 Point = 0; Point < Found.Num() && Point < Wanted; ++Point)
            Points.Add(Found[Point]);
        if (Attack.At == ESoraZoneAt::AnchorOrTarget && Points.Num() < Wanted)
        {
            const int32 Missing = Wanted - Points.Num();
            Points.Add(Feet);
            Around(Missing - 1, FMath::Max(Attack.RadiusCm * 2.f, 300.f));
        }
        break;
    }
    }
    return !Points.IsEmpty();
}

void ASoraBoss::PlaceZones(int32 Index, int32 Serial, int32 WindupMs)
{
    const FSoraBossAttack& Attack = AttackAt(Index);
    TArray<FVector> Points;
    if (!ZonePoints(Index, Serial, Points))
        return;
    int32 Room = Attack.MaxActive > 0 ? Attack.MaxActive - LiveZones(Index) : Points.Num();
    for (const FVector& Point : Points)
    {
        if (Room-- <= 0)
            break;
        FActorSpawnParameters Params;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        ASoraBossHazard* Zone = GetWorld()->SpawnActor<ASoraBossHazard>(Ground(Point), FRotator::ZeroRotator, Params);
        if (!Zone)
            continue;
        Zone->BeginZone(*this, Index, Serial, WindupMs, RootFor(Index));
        Zones.Add(Zone);
    }
}

void ASoraBoss::Summon(int32 Group)
{
    const FSoraBossAddGroup& Spec = Info->Adds[Group];
    const int32 Count = FMath::Min(Spec.Count, Spec.MaxAlive - LiveAdds(Group));
    const ASoraCharacterBase* Target = Hero();
    for (int32 Index = 0; Index < Count; ++Index)
    {
        const float Angle = FMath::DegreesToRadians(Index * 360.f / FMath::Max(1, Count) + NextSerial * 29.f);
        const FVector At = ClampToArena(GetActorLocation() + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.f) * 350.f);
        const FRotator Facing = Target ? (Target->GetActorLocation() - At).GetSafeNormal2D().Rotation() : GetActorRotation();
        FSoraEnemyTuning Tuning;
        Tuning.Variant = Spec.Variant;
        ASoraEnemy* Add = ASoraEnemy::SpawnArchetype(*GetWorld(), Spec.Archetype, EnemySlot() * 16 + Adds.Num() % 16, At, Facing, nullptr,
            Spec.Variant.IsNone() ? nullptr : &Tuning);
        if (!Add)
            continue;
        Add->SetSummoner(this);
        Adds.Add(Add);
        AddGroups.Add(Group);
    }
    ++NextSerial;
    Broadcast(ESoraBossPhase::Event, Spec.Id);
}

void ASoraBoss::AddDefeated(ASoraEnemy& Add)
{
    const int32 Index = Adds.IndexOfByKey(&Add);
    if (Index == INDEX_NONE)
        return;
    const int32 Group = AddGroups[Index];
    Adds.RemoveAt(Index);
    AddGroups.RemoveAt(Index);
    if (LiveAdds(Group) > 0 || bDefeated)
        return;
    if (Info->Adds[Group].RespawnMs > 0)
        GroupRespawnAtMs[Group] = NowMs() + Info->Adds[Group].RespawnMs;
    const FSoraBossPhase* Current = CurrentPhase();
    if (Current && Current->ShieldWhileAdds == Group)
        Broadcast(ESoraBossPhase::Event, TEXT("shield_down"));
}

void ASoraBoss::Expose(int32 Index, int32 Serial)
{
    const FSoraBossAttack& Attack = AttackAt(Index);
    FExposure Window;
    Window.Attack = Index;
    Window.Serial = Serial;
    Window.UntilMs = NowMs() + ActiveFor(Index);
    if (Attack.bRotate)
    {
        // One leg plants at a time, round the body; a broken point stays shut.
        for (int32 Tried = 0; Tried < Attack.Opens.Num(); ++Tried)
        {
            const int32 Point = Attack.Opens[RotateNext++ % Attack.Opens.Num()];
            if (PointHealth[Point] != 0)
            {
                Window.Points.Add(Point);
                break;
            }
        }
    }
    else
        for (const int32 Point : Attack.Opens)
            if (PointHealth[Point] != 0)
                Window.Points.Add(Point);
    for (const int32 Point : Window.Points)
        PointOpenUntilMs[Point] = FMath::Max(PointOpenUntilMs[Point], Window.UntilMs);
    Exposures.Add(Window);
    Broadcast(ESoraBossPhase::Event, TEXT("opened"), NAME_None, Serial);
}

void ASoraBoss::CloseExposure(int32 Index, bool bInterrupted)
{
    const FExposure Window = Exposures[Index];
    Exposures.RemoveAt(Index);
    const FSoraBossAttack& Attack = AttackAt(Window.Attack);
    const int32 Now = NowMs();
    for (const int32 Point : Window.Points)
    {
        bool bStillOpen = false;
        for (const FExposure& Other : Exposures)
            bStillOpen |= Other.Points.Contains(Point);
        // An interrupted kneel stays open through its stagger: the best window.
        if (!bStillOpen)
            PointOpenUntilMs[Point] = bInterrupted ? Now + Attack.InterruptStaggerMs : FMath::Min(PointOpenUntilMs[Point], Now);
    }
    if (bInterrupted)
    {
        Broadcast(ESoraBossPhase::Countered, Attack.Id, NAME_None, Window.Serial);
        Stagger(Attack.InterruptStaggerMs);
        return;
    }
    if (Attack.Event.IsNone())
        return;
    ++SealCount;
    Broadcast(ESoraBossPhase::Event, Attack.Event, EventBark(TEXT("seal")), Window.Serial);
    if (BossRules::SealsFail(SealCount, Attack.EventLimit))
        Broadcast(ESoraBossPhase::Event, FName(*FString::Printf(TEXT("%s_%d"), *Attack.Event.ToString(), Attack.EventLimit)),
            NAME_None, Window.Serial);
}

void ASoraBoss::SpawnWards(int32 Ward)
{
    const FSoraBossWard& Spec = Info->Wards[Ward];
    for (int32 Place = 0; Place < Spec.Count; ++Place)
    {
        FActorSpawnParameters Params;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        ASoraBossHazard* Guard = GetWorld()->SpawnActor<ASoraBossHazard>(GetActorLocation(), FRotator::ZeroRotator, Params);
        if (!Guard)
            continue;
        Guard->BeginWard(*this, Ward, Place);
        WardActors.Add(Guard);
    }
    Broadcast(ESoraBossPhase::Event, Spec.Id, Spec.Bark);
}

void ASoraBoss::ClearWards()
{
    for (ASoraBossHazard* Guard : WardActors)
        if (IsValid(Guard))
            Guard->Destroy();
    WardActors.Reset();
    WardRespawnAtMs = 0;
}

void ASoraBoss::WardBroken(ASoraBossHazard& Ward)
{
    WardActors.Remove(&Ward);
    if (bDefeated || !Info->Wards.IsValidIndex(Ward.WardOf()))
        return;
    Broadcast(ESoraBossPhase::Event, TEXT("ward_broken"));
    if (LiveWards() > 0)
        return;
    const FSoraBossWard& Spec = Info->Wards[Ward.WardOf()];
    Broadcast(ESoraBossPhase::Event, TEXT("wards_broken"));
    if (Spec.BrokenStunMs > 0)
        Stun(Spec.BrokenStunMs, Spec.BrokenTakenPermille);
    if (Spec.RespawnMs > 0)
        WardRespawnAtMs = NowMs() + Spec.RespawnMs;
}

bool ASoraBoss::Intercepted(const FSoraHit& Hit, int32 Damage)
{
    if (WardActors.IsEmpty() || !Hit.bHasOrigin || !Info->Wards.IsValidIndex(WardIndex))
        return false;
    const FVector EyePoint = GetActorLocation() + FVector(0.f, 0.f, SoraBossBody::EyeHeight * GetActorScale3D().Z);
    const FVector Point = EyePoint + (Hit.Origin - EyePoint).GetSafeNormal() * Info->Wards[WardIndex].OrbitCm;
    ASoraBossHazard* Nearest = nullptr;
    float Best = MAX_flt;
    for (ASoraBossHazard* Guard : WardActors)
        if (IsValid(Guard) && Guard->WardHealth() > 0 && !Guard->IsOpen() && FVector::Dist(Guard->GetActorLocation(), Point) < Best)
        {
            Best = FVector::Dist(Guard->GetActorLocation(), Point);
            Nearest = Guard;
        }
    // A ward steps into the line and takes the hit (or shrugs it off while closed).
    if (!Nearest || !Nearest->Intercept(Point, Damage))
        return false;
    Broadcast(ESoraBossPhase::Event, TEXT("ward_blocked"));
    return true;
}

void ASoraBoss::LockArena(bool bLock)
{
    for (AActor* Wall : LockWalls)
        if (IsValid(Wall))
            Wall->Destroy();
    LockWalls.Reset();
    if (!bLock || ArenaRadiusCm <= 0.f || !GetWorld())
        return;
    // A ring of walls that stops bodies, never shots, until the fight ends;
    // a seal line on the floor shows where it runs.
    AActor* Ring = GetWorld()->SpawnActor<AActor>(Center, FRotator::ZeroRotator);
    if (!Ring)
        return;
    USceneComponent* Root = NewObject<USceneComponent>(Ring, TEXT("ArenaLockRoot"));
    Ring->SetRootComponent(Root);
    Root->RegisterComponent();
    Ring->SetActorLocation(Ground(Center));
    const float Chord = 2.f * ArenaRadiusCm * FMath::Sin(PI / SoraBossBody::LockSegments) + 40.f;
    for (int32 Segment = 0; Segment < SoraBossBody::LockSegments; ++Segment)
    {
        const float Angle = 2.f * PI * (Segment + .5f) / SoraBossBody::LockSegments;
        const FVector Offset(FMath::Cos(Angle) * ArenaRadiusCm, FMath::Sin(Angle) * ArenaRadiusCm, 0.f);
        UStaticMeshComponent* Wall = ASoraWorldBuilder::Shape(Ring, Root, FString::Printf(TEXT("ArenaLock%d"), Segment),
            TEXT("/Engine/BasicShapes/Cube.Cube"), Offset + FVector(0.f, 0.f, SoraBossBody::LockHeight * .5f),
            FVector(.3f, Chord / 100.f, SoraBossBody::LockHeight / 100.f), SoraBossBody::Cyan, true);
        Wall->SetRelativeRotation(FRotator(0.f, FMath::RadiansToDegrees(Angle), 0.f));
        Wall->SetCollisionResponseToAllChannels(ECR_Ignore);
        Wall->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
        Wall->SetCanEverAffectNavigation(false);
        Wall->SetVisibility(false);
        UStaticMeshComponent* Seal = ASoraWorldBuilder::Shape(Ring, Root, FString::Printf(TEXT("ArenaSeal%d"), Segment),
            TEXT("/Engine/BasicShapes/Cube.Cube"), Offset + FVector(0.f, 0.f, 2.f), FVector(.06f, Chord / 100.f, .02f),
            SoraBossBody::Cyan, false);
        Seal->SetRelativeRotation(FRotator(0.f, FMath::RadiansToDegrees(Angle), 0.f));
    }
    LockWalls.Add(Ring);
}

void ASoraBoss::BreakShield()
{
    if (bShieldBroken)
        return;
    bShieldBroken = true;
    Broadcast(ESoraBossPhase::Event, TEXT("shield_broken"), EventBark(TEXT("shield_broken")));
}

void ASoraBoss::BreakMantle()
{
    if (!Info || !Info->bMantle)
        return;
    MantleDownUntilMs = FMath::Max(MantleDownUntilMs, NowMs() + Info->MantleDownMs);
    Broadcast(ESoraBossPhase::Event, TEXT("mantle_down"), EventBark(TEXT("mantle_down")));
}

void ASoraBoss::Hear(const FVector& Evidence)
{
    if (!Info || !Info->bBlind || bDefeated)
        return;
    const int32 Reach = BossRules::Share(Info->Hearing.NoiseCm, Info->Phases[PhaseNow].HearingPermille);
    if (FVector::Dist2D(Evidence, GetActorLocation()) > Reach)
        return;
    KnownAt = Evidence;
    KnownAtMs = NowMs();
}

void ASoraBoss::Stagger(int32 Milliseconds)
{
    if (Milliseconds <= 0 || !IsAlive() || !Info)
        return;
    ASoraEnemy::Stagger(Milliseconds);
    const int32 Now = NowMs();
    const int32 Serial = Run.Serial;
    switch (Run.Stage)
    {
    case EStage::Dash:
    case EStage::Windup:
    case EStage::Hold:
    case EStage::Gap:
        // A staggered boss drops its windup; a kneel it was holding ends unsealed.
        Exposures.RemoveAll([Serial](const FExposure& Window) { return Window.Serial == Serial; });
        Run = FRun();
        break;
    case EStage::Active:
        Exposures.RemoveAll([Serial](const FExposure& Window) { return Window.Serial == Serial; });
        Run.RepeatsLeft = 0;
        Recover(RecoveryFor(Run.Attack));
        Run.StageEndsMs = FMath::Max(Run.StageEndsMs, Now + Milliseconds);
        break;
    case EStage::Recovery:
        Run.StageEndsMs = FMath::Max(Run.StageEndsMs, Now + Milliseconds);
        break;
    case EStage::Idle:
        break;
    }
    NextStartMs = FMath::Max(NextStartMs, Now + Milliseconds);
    Broadcast(ESoraBossPhase::Staggered, NAME_None, EventBark(TEXT("stagger")), 0, Milliseconds);
}

void ASoraBoss::Outflanked(int32 Milliseconds)
{
    if (Info && !bDefeated && Rules::MarobashiOpen(-1, MarobashiUntilLandsMs(), MarobashiWindowMs()))
    {
        EvadedSerial = Run.Serial;
        Broadcast(ESoraBossPhase::Event, TEXT("marobashi"), NAME_None, Run.Serial);
    }
    ASoraEnemy::Outflanked(Milliseconds);
}

void ASoraBoss::Parried(int32 StaggerMs)
{
    const FSoraBossAttack* Attack = BossAttack();
    Run.bParried = true;
    ParriedSerial = Run.Serial;
    if (Attack && Attack->OnParry == ESoraBossParry::MeasureReset)
        Broadcast(ESoraBossPhase::Countered, Attack->Id, NAME_None, Run.Serial);
    if (Attack && Attack->OnParry == ESoraBossParry::MantleDown)
    {
        Broadcast(ESoraBossPhase::Countered, Attack->Id, EventBark(TEXT("countered")), Run.Serial);
        BreakMantle();
    }
    if (StaggerMs > 0)
        Stagger(StaggerMs);
    else if (Run.Stage == EStage::Active || Run.Stage == EStage::Gap)
    {
        // A parry ends a multi-hit blow even when it does not stagger.
        Run.RepeatsLeft = 0;
        Recover(RecoveryFor(Run.Attack));
    }
}

bool ASoraBoss::Disarm(AActor* By)
{
    const FSoraBossAttack* Attack = BossAttack();
    if (!Info || !Info->bMutoFinisher || bDefeated || !Attack || !Attack->bMuto)
        return false;
    // 無刀取り: the blade is taken; the fight is over at any health.
    bTakenByMuto = true;
    Health = 0.f;
    if (USoraGameEvents* Events = USoraGameEvents::Get(this))
    {
        FSoraDiedEvent Died;
        Died.Victim = this; Died.Killer = By; Died.bSparring = IsSparring();
        Events->OnDied.Broadcast(Died);
    }
    OnDefeated(By);
    return true;
}

int32 ASoraBoss::WeakPointHit(const FSoraHit& Hit) const
{
    for (int32 Index = 0; Index < PointParts.Num(); ++Index)
        if (Hit.Part.IsValid() && Hit.Part.Get() == PointParts[Index].Get() && PointHealth[Index] != 0)
            return Index;
    const bool bBlast = Hit.Kind == Rules::EHit::Blast;
    if (!Hit.bHasImpact && !bBlast)
        return INDEX_NONE;
    const FVector At = bBlast ? Hit.Origin : Hit.Impact;
    int32 Best = INDEX_NONE;
    float Nearest = MAX_flt;
    for (int32 Index = 0; Index < Info->WeakPoints.Num(); ++Index)
    {
        if (PointHealth[Index] == 0)
            continue;
        const float Distance = FVector::Dist(At, WeakPointLocation(Index));
        const float Limit = Info->WeakPoints[Index].RadiusCm + (bBlast ? SoraBossBody::BlastSlackCm : SoraBossBody::PointSlackCm);
        if (Distance <= Limit && Distance < Nearest)
        {
            Nearest = Distance;
            Best = Index;
        }
    }
    return Best;
}

bool ASoraBoss::AdmitDamage(float& Damage, FSoraHit& Hit, AActor* Causer)
{
    if (!Info || bDefeated)
        return false;
    // A story event or a test: straight to health, past every defense.
    if (Hit.Kind == Rules::EHit::Scripted)
        return Damage > 0.f;
    const int32 Now = NowMs();
    const auto Blocked = [&Hit]() { Hit.Defense = Rules::EDefense::Guard; return false; };
    if (IsInvulnerable())
        return Blocked();
    int32 Amount = FMath::RoundToInt32(Damage);
    const int32 Facing = Hit.bHasOrigin ? SoraDamage::FacingMilli(*this, Hit.Origin) : 1000;
    const bool bRanged = Hit.Kind == Rules::EHit::Ranged || Hit.Kind == Rules::EHit::Blast;
    if (bRanged && Intercepted(Hit, Amount))
        return Blocked();
    if (BossRules::Deflects(Facing, Info->DeflectHalfArcMilli, Run.Attack == INDEX_NONE, bRanged))
    {
        Broadcast(ESoraBossPhase::Event, TEXT("deflected"));
        return Blocked();
    }
    if (IsShieldUp() && Rules::ShieldStops(Hit.Kind, Facing, Info->ShieldHalfArcMilli, false))
    {
        if (Hit.Kind == Rules::EHit::Blast && Hit.WeaponId == Info->ShieldBreakWeapon && ++ShieldHits >= Info->ShieldBreakHits)
            BreakShield();
        if (Info->FrontBlockedHint > 0 && ++FrontBlocked == Info->FrontBlockedHint)
            Broadcast(ESoraBossPhase::Event, TEXT("front_blocked"));
        if (USoraGameEvents* Events = USoraGameEvents::Get(this))
        {
            FSoraDefenseEvent Guarded;
            Guarded.Defender = this; Guarded.Attacker = Causer;
            Events->OnGuarded.Broadcast(Guarded);
        }
        return Blocked();
    }
    const bool bMelee = Hit.Kind == Rules::EHit::Melee;
    const int32 Point = WeakPointHit(Hit);
    if (Point != INDEX_NONE)
    {
        const FSoraBossWeakPoint& Spec = Info->WeakPoints[Point];
        const int32 Permille = IsWeakPointOpen(Point) ? (bMelee ? Spec.MeleePermille : Spec.RangedPermille) : Spec.ClosedPermille;
        if (Permille == 0)
            return Blocked();
        Amount = BossRules::WeakPointDamage(Amount, Permille, PointHealth[Point] > 0 ? PointHealth[Point] : -1);
    }
    else
    {
        Amount = BossRules::Share(Amount, Info->BodyPermille);
        if (Amount <= 0)
            return Blocked();
    }
    // A barrier soaks the hit (a reload leaves it down); the hit that breaks
    // it does not carry through.
    if (HasBarrier() && !IsBarrierOffline() && BarrierNowMilli > 0)
    {
        const FSoraBossBarrier& Spec = Info->Barrier;
        const int32 MaxMilli = Spec.Health * 1000;
        Rules::FBarrierHit Soaked{};
        if (const int32* Strip = Spec.StripPermille.Find(Hit.WeaponId))
            Soaked = Rules::SoakBarrier({BarrierNowMilli, MaxMilli}, BossRules::Share(Spec.Health, *Strip), 1000, false);
        else
        {
            const int32* Weapon = Spec.WeaponPermille.Find(Hit.WeaponId);
            Soaked = Rules::SoakBarrier({BarrierNowMilli, MaxMilli}, Amount, Weapon ? *Weapon : bMelee ? Spec.MeleePermille : 1000, false);
        }
        BarrierNowMilli = Soaked.Barrier.HealthMilli;
        BarrierAtHitMilli = BarrierNowMilli;
        BarrierHitMs = Now;
        if (Soaked.Broke)
            Broadcast(ESoraBossPhase::Event, TEXT("barrier_broken"), EventBark(TEXT("barrier_broken")));
        return Blocked();
    }
    if (HasBarrier())
    {
        BarrierAtHitMilli = BarrierNowMilli;
        BarrierHitMs = Now;
    }
    if (IsMantleUp())
        Amount = BossRules::Taken(Amount, Info->MantleTakenPermille);
    Amount = IsStunned() ? BossRules::Taken(Amount, StunTakenPermille) : Rules::StaggeredDamage(Amount, IsStaggered());
    Amount = BossRules::Taken(Amount, BossRules::DirectionalPermille(Facing, Info->RearPermille, Info->FlankPermille));
    // A cut that outweighs its poise staggers it, but not in a chain.
    if (bMelee)
    {
        const int32 Ms = Rules::StrikeStaggerMs(Hit.StaggerMs, Info->PoiseMs, Now < StrikeImmuneUntilMs);
        if (Ms > 0)
        {
            Stagger(Ms);
            StrikeImmuneUntilMs = Now + Rules::StaggerImmunityMs;
        }
    }
    // No blow passes the next phase's start or the fight's floor.
    int32 Starts[BossRules::MaxPhases] = {};
    const int32 Count = FMath::Min(Info->Phases.Num(), BossRules::MaxPhases);
    for (int32 Index = 0; Index < Count; ++Index)
        Starts[Index] = Info->Phases[Index].FromPermille;
    Amount = BossRules::Admitted(FMath::RoundToInt32(Health), Amount, FMath::RoundToInt32(MaxHealth), Starts, Count, PhaseNow, FloorPermille());
    if (Amount <= 0)
        return false;
    if (Point != INDEX_NONE)
    {
        if (PointHealth[Point] > 0)
            PointHealth[Point] = FMath::Max(0, PointHealth[Point] - Amount);
        for (int32 Window = Exposures.Num() - 1; Window >= 0; --Window)
        {
            FExposure& Open = Exposures[Window];
            if (!Open.Points.Contains(Point))
                continue;
            Open.Damage += Amount;
            if (BossRules::Interrupted(Open.Damage, AttackAt(Open.Attack).InterruptDamage))
            {
                // One interrupt per blow; the stagger it causes may close other windows.
                CloseExposure(Window, true);
                break;
            }
        }
        if (PointHealth[Point] == 0)
        {
            PointOpenUntilMs[Point] = 0;
            Broadcast(ESoraBossPhase::Event, TEXT("weakpoint_destroyed"), EventBark(TEXT("weakpoint_destroyed")));
            Broadcast(ESoraBossPhase::Event, Info->WeakPoints[Point].Id);
        }
    }
    Damage = Amount;
    return true;
}

void ASoraBoss::FinishFight(FName Detail)
{
    if (bDefeated)
        return;
    bDefeated = true;
    Defeated = Detail;
    Run = FRun();
    Sides.Reset();
    Exposures.Reset();
    ClearWards();
    for (ASoraBossHazard* Zone : Zones)
        if (IsValid(Zone))
            Zone->Destroy();
    Zones.Reset();
    // Its adds leave with it.
    for (ASoraEnemy* Add : Adds)
        if (IsValid(Add))
            Add->Destroy();
    Adds.Reset();
    AddGroups.Reset();
    LockArena(false);
    Broadcast(ESoraBossPhase::Defeated, Detail, EventBark(bTakenByMuto ? TEXT("muto_dori") : TEXT("defeated")));
}

void ASoraBoss::OnDefeated(AActor* Causer)
{
    if (Info)
        FinishFight(bTakenByMuto ? FName(TEXT("muto_dori")) : SoraBossBody::DefeatName(Info->Defeat));
    Super::OnDefeated(Causer);
}

void ASoraBoss::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    // A boss removed from the world takes its wards, zones, adds and lock with it.
    ClearWards();
    for (ASoraBossHazard* Zone : Zones)
        if (IsValid(Zone))
            Zone->Destroy();
    Zones.Reset();
    for (ASoraEnemy* Add : Adds)
        if (IsValid(Add))
            Add->Destroy();
    Adds.Reset();
    AddGroups.Reset();
    LockArena(false);
    Super::EndPlay(EndPlayReason);
}
