#include "SoraCompanion.h"
#include "Combat/SoraDamage.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraFieldcraft.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraHistoricalArms.h"
#include "SoraViewmodelComponent.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

namespace SoraCompanionTuning
{
// A fighter keeps within this of its post and takes on opponents this near it.
constexpr float LeashCm = 1600.f;
constexpr float FighterSightCm = 2200.f;
constexpr float ShooterSightCm = 3600.f;
// Allies land a share of the arm's catalog damage, on a slower cadence than
// the hero's: they hold a line, they do not win the fight for him.
constexpr float FighterDamageShare = .35f;
constexpr float ShooterDamageShare = .3f;
constexpr float FighterExtraWindup = .25f;
constexpr float FighterCadence = 1.6f;
constexpr float ShooterCadence = 2.4f;
constexpr float RunPace = 420.f;
constexpr float GuideNearCm = 260.f;
constexpr float GuideFarCm = 420.f;
constexpr float EyeHeight = 50.f;
// The front rank stands a step before its post.
constexpr float RankStepCm = 120.f;
}

ASoraCompanion::ASoraCompanion(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    // Companions neither block the hero nor his opponents in a crowded lane;
    // blows and rounds still find them along the visibility channel.
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
    bUseControllerRotationYaw = false;
    GetCharacterMovement()->bOrientRotationToMovement = false;
    GetCharacterMovement()->MaxWalkSpeed = SoraCompanionTuning::RunPace;
}

float ASoraCompanion::Now() const
{
    return GetWorld() ? GetWorld()->GetTimeSeconds() : 0.f;
}

void ASoraCompanion::Init(const FSoraCompanionSpec& Spec, int32 Slot)
{
    Id = Spec.Id;
    CompanionSlot = Slot;
    Kind = Spec.Role == TEXT("escort") ? ERole::Escort : Spec.Role == TEXT("fighter") ? ERole::Fighter :
        Spec.Role == TEXT("shooter") ? ERole::Shooter : Spec.Role == TEXT("rank") ? ERole::Rank :
        Spec.Role == TEXT("guide") ? ERole::Guide : ERole::Bystander;
    RankIndex = Spec.Rank;
    RulesData = Spec.Rules;
    StateData = SoraFieldcraftRules::Fresh(RulesData);
    MaxHealth = static_cast<float>(RulesData.Health);
    Health = MaxHealth;
    bDetectable = Spec.bDetectable;
    PostAt = GetActorLocation();
    PostYaw = GetActorRotation().Yaw;
    // The villagers' own cloth, not Nyaakoto's.
    if (GetMesh()->GetSkinnedAsset()) GetMesh()->EmptyOverrideMaterials();
    if (Spec.WeaponId != INDEX_NONE && FSoraCatalog::Get().IsReady())
    {
        WeaponId = Spec.WeaponId;
        RebuildWeapon();
        GetViewmodel()->SetVisibility(true, true);
    }
    else GetViewmodel()->SetVisibility(false, true);
    bJoined = Spec.Joins.IsEmpty();
    if (!bJoined)
    {
        SetActorHiddenInGame(true);
        SetActorEnableCollision(false);
        GetCharacterMovement()->DisableMovement();
    }
    Shown = StateData.State;
    Present();
}

void ASoraCompanion::Join()
{
    if (bJoined) return;
    bJoined = true;
    SetActorHiddenInGame(false);
    SetActorEnableCollision(true);
    GetCharacterMovement()->SetMovementMode(MOVE_Walking);
}

bool ASoraCompanion::IsExposed(int32 DistanceCm) const
{
    if (!bJoined || !bDetectable || !SoraFieldcraftRules::IsStanding(StateData)) return false;
    return !IsHiddenAway() || DistanceCm <= SoraFieldcraftRules::HiddenSightCm;
}

bool ASoraCompanion::AdmitDamage(float& Damage, FSoraHit& Hit, AActor* Causer)
{
    // Health follows the rules: a downable companion falls at zero and is
    // raised later; one that is not downable cannot be hurt.
    const int32 Before = StateData.Health;
    const SoraFieldcraftRules::EChange Change =
        SoraFieldcraftRules::Hit(StateData, RulesData, FMath::Max(1, FMath::RoundToInt32(Damage)));
    Health = static_cast<float>(StateData.Health);
    if (StateData.Health < Before) DamageFlash = .3f;
    if (USoraGameEvents* Events = USoraGameEvents::Get(this); Events && StateData.Health < Before)
    {
        FSoraDamagedEvent Damaged;
        Damaged.Victim = this; Damaged.Causer = Causer; Damaged.Amount = static_cast<float>(Before - StateData.Health);
        Damaged.HealthAfter = Health;
        Events->OnDamaged.Broadcast(Damaged);
    }
    if (Change != SoraFieldcraftRules::EChange::None)
    {
        Present();
        if (USoraFieldcraft* Craft = USoraFieldcraft::Get(this)) Craft->CompanionChanged(*this, Change);
    }
    // The rules already took the blow.
    Damage = 0.f;
    return false;
}

SoraFieldcraftRules::EChange ASoraCompanion::Step(int32 DtMs, bool bHeld)
{
    const SoraFieldcraftRules::EChange Change = SoraFieldcraftRules::Tick(StateData, RulesData, DtMs, bHeld);
    Health = static_cast<float>(StateData.Health);
    if (Change != SoraFieldcraftRules::EChange::None) Present();
    return Change;
}

bool ASoraCompanion::Lance()
{
    return SoraFieldcraftRules::Lance(StateData, RulesData);
}

void ASoraCompanion::Present(SoraFieldcraftRules::EState NewState)
{
    StateData.State = NewState;
    Present();
    // Netted where it knelt: crouched under the net; taken, gone from the field.
    if (NewState == SoraFieldcraftRules::EState::Bound) Crouch();
    else if (NewState == SoraFieldcraftRules::EState::Up) UnCrouch();
    if (NewState == SoraFieldcraftRules::EState::Dead) SetActorHiddenInGame(true);
}

bool ASoraCompanion::Signal(bool bHide)
{
    if (!SoraFieldcraftRules::Signal(StateData, bHide)) return false;
    Present();
    return true;
}

void ASoraCompanion::SetGoal(const FVector& Goal, float Yaw, float PaceCmS)
{
    GoalAt = Goal; GoalYaw = Yaw; GoalPace = PaceCmS; bHasGoal = true;
}

void ASoraCompanion::Present()
{
    using SoraFieldcraftRules::EState;
    const EState Now = StateData.State;
    if (Now == Shown) return;
    UCapsuleComponent* Capsule = GetCapsuleComponent();
    const bool bWasLying = Shown == EState::Down || Shown == EState::Dead;
    const bool bLying = Now == EState::Down || Now == EState::Dead;
    if (bLying && !bWasLying)
    {
        // Down where it fell, low on the floor. A healing lance's round can
        // still find the downed; the dead are passed over.
        GetCharacterMovement()->StopMovementImmediately();
        GetCharacterMovement()->DisableMovement();
        SetActorRotation(FRotator(0.f, GetActorRotation().Yaw, 85.f));
        AddActorWorldOffset(FVector(0.f, 0.f, Capsule->GetScaledCapsuleRadius() - Capsule->GetScaledCapsuleHalfHeight()));
        bWindup = false;
    }
    else if (!bLying && bWasLying)
    {
        SetActorRotation(FRotator(0.f, GetActorRotation().Yaw, 0.f));
        AddActorWorldOffset(FVector(0.f, 0.f, Capsule->GetScaledCapsuleHalfHeight() - Capsule->GetScaledCapsuleRadius()));
        GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    }
    if (Now == EState::Dead) Capsule->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
    // Hidden: crouched still. Standing again when sent on.
    if (Now == EState::Hidden) Crouch();
    else if (Shown == EState::Hidden) UnCrouch();
    Shown = Now;
}

void ASoraCompanion::HaltActions()
{
    bWindup = false;
    UpdateLocomotion(false, 1.f);
}

ASoraEnemy* ASoraCompanion::Quarry() const
{
    const bool bShooter = Kind == ERole::Shooter;
    const float Sight = bShooter ? SoraCompanionTuning::ShooterSightCm : SoraCompanionTuning::FighterSightCm;
    ASoraEnemy* Best = nullptr;
    float BestDistance = Sight;
    for (TActorIterator<ASoraEnemy> It(GetWorld()); It; ++It)
    {
        ASoraEnemy* Enemy = *It;
        if (!Enemy->IsEnemy() || !Enemy->IsAlive() || Enemy->IsSubdued() || Enemy->IsSeized() || Enemy->IsHidden() ||
            Enemy->IsDojoPupil() || (!bShooter && Enemy->IsFlying()))
            continue;
        const float Distance = FVector::Dist2D(Enemy->GetActorLocation(), GetActorLocation());
        if (Distance >= BestDistance ||
            (!bShooter && FVector::Dist2D(Enemy->GetActorLocation(), PostAt) > SoraCompanionTuning::LeashCm))
            continue;
        Best = Enemy;
        BestDistance = Distance;
    }
    return Best;
}

void ASoraCompanion::MoveToward(const FVector& Where, float Pace, float Acceptance)
{
    FVector Delta = Where - GetActorLocation();
    Delta.Z = 0.f;
    const float Distance = Delta.Size();
    const bool bMoving = Distance > Acceptance;
    if (bMoving)
    {
        GetCharacterMovement()->MaxWalkSpeed = Pace;
        AddMovementInput(Delta / Distance, 1.f);
        SetActorRotation(FRotator(0.f, Delta.Rotation().Yaw, 0.f));
    }
    UpdateLocomotion(bMoving, FMath::Clamp(Pace / 180.f, .65f, 2.5f));
}

void ASoraCompanion::WalkToGoal(float Dt)
{
    // An escorted member is carried along the road by the fieldcraft's
    // placement: it walks there at its pace without ever leaving the road.
    FVector Delta = GoalAt - GetActorLocation();
    Delta.Z = 0.f;
    const float Distance = Delta.Size();
    const float Reach = FMath::Max(GoalPace, 60.f) * 1.6f * Dt;
    const bool bMoving = Distance > 4.f;
    if (bMoving)
    {
        const FVector Step = Distance <= Reach ? Delta : Delta / Distance * Reach;
        SetActorLocation(GetActorLocation() + Step, false, nullptr, ETeleportType::TeleportPhysics);
        if (Distance > 25.f) SetActorRotation(FRotator(0.f, Delta.Rotation().Yaw, 0.f));
    }
    else SetActorRotation(FMath::RInterpTo(GetActorRotation(), FRotator(0.f, GoalYaw, 0.f), Dt, 4.f));
    UpdateLocomotion(bMoving && Distance > 20.f, FMath::Clamp(GoalPace / 160.f, .65f, 2.f));
}

void ASoraCompanion::Fight(float Dt)
{
    const float Time = Now();
    const auto Profile = SoraHistoricalArms::Profile(SoraHistoricalArms::FormFor(WeaponId));
    if (bWindup)
    {
        ASoraEnemy* Enemy = Target.Get();
        if (Time < StrikeAt) return;
        bWindup = false;
        ReadyAt = Time + Profile.RecoverySeconds * SoraCompanionTuning::FighterCadence;
        if (!Enemy || !Enemy->IsAlive()) return;
        const FVector From = GetActorLocation() + FVector(0.f, 0.f, SoraCompanionTuning::EyeHeight);
        const FVector Delta = Enemy->GetActorLocation() - GetActorLocation();
        // The blow lands only if the opponent is still in its committed reach.
        if (Delta.Size2D() > Profile.MaximumDistanceCm + 40.f ||
            FVector::DotProduct(GetActorForwardVector(), Delta.GetSafeNormal2D()) < Profile.MinimumFacingDot)
            return;
        FHitResult Trace;
        Trace.ImpactPoint = Enemy->GetActorLocation();
        Trace.Location = Trace.ImpactPoint;
        FSoraHit Hit = FSoraHit::Melee(From, WeaponId);
        Hit.StaggerMs = Profile.StaggerMs / 2;
        SoraDamage::Strike(Enemy, FSoraCatalog::Get().Weapon(WeaponId).Damage * SoraCompanionTuning::FighterDamageShare, Hit,
            Delta.GetSafeNormal(), Trace, nullptr, this);
        SoraDamage::Beam(GetWorld(), From, From + GetActorForwardVector() * Profile.MaximumDistanceCm, FLinearColor(.72f, .8f, .84f), 1.4f, .1f);
        ++StrikeCount;
        return;
    }
    ASoraEnemy* Enemy = Quarry();
    Target = Enemy;
    if (!Enemy)
    {
        MoveToward(PostAt, SoraCompanionTuning::RunPace * .7f, 80.f);
        return;
    }
    const FVector Delta = Enemy->GetActorLocation() - GetActorLocation();
    const float Distance = Delta.Size2D();
    if (Distance > Profile.MaximumDistanceCm * .8f)
    {
        MoveToward(Enemy->GetActorLocation(), SoraCompanionTuning::RunPace, Profile.MaximumDistanceCm * .7f);
        return;
    }
    UpdateLocomotion(false, 1.f);
    SetActorRotation(FRotator(0.f, Delta.Rotation().Yaw, 0.f));
    if (Time < ReadyAt) return;
    // A committed windup along a fixed line, then one contact.
    bWindup = true;
    StrikeAt = Time + Profile.WindupSeconds + SoraCompanionTuning::FighterExtraWindup;
}

void ASoraCompanion::Shoot(float Dt)
{
    const float Time = Now();
    ASoraEnemy* Enemy = Quarry();
    if (FVector::Dist2D(GetActorLocation(), PostAt) > 90.f)
        MoveToward(PostAt, SoraCompanionTuning::RunPace * .7f, 80.f);
    else UpdateLocomotion(false, 1.f);
    if (!Enemy) return;
    const FVector From = GetActorLocation() + FVector(0.f, 0.f, SoraCompanionTuning::EyeHeight);
    const FVector To = Enemy->GetActorLocation() + FVector(0.f, 0.f, 20.f);
    SetActorRotation(FRotator(0.f, (To - From).Rotation().Yaw, 0.f));
    if (Time < ReadyAt) return;
    FHitResult Trace;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraCompanionShot), false, this);
    GetWorld()->LineTraceSingleByChannel(Trace, From, To, ECC_Visibility, Query);
    if (Trace.GetActor() != Enemy) return;
    const FSoraWeapon& Arm = FSoraCatalog::Get().Weapon(WeaponId);
    ReadyAt = Time + FMath::Max(1.2f, Arm.Cooldown * SoraCompanionTuning::ShooterCadence);
    // Every third round goes wide, on a pattern offset by slot.
    const bool bMiss = (RoundCount + CompanionSlot) % 3 == 2;
    ++RoundCount;
    const FVector End = bMiss ? To + FVector(0.f, 90.f, 70.f) : To;
    SoraDamage::Beam(GetWorld(), From + (To - From).GetSafeNormal() * 50.f, End, FLinearColor(1.f, .72f, .2f), 1.5f, .08f);
    if (USoraGameEvents* Events = USoraGameEvents::Get(this))
    {
        FSoraWeaponFiredEvent Fired;
        Fired.Shooter = this; Fired.WeaponId = WeaponId; Fired.Kind = ESoraShotKind::Hitscan;
        Fired.Origin = From; Fired.Direction = (End - From).GetSafeNormal(); Fired.End = End;
        Events->OnWeaponFired.Broadcast(Fired);
    }
    if (!bMiss)
        SoraDamage::Strike(Enemy, Arm.Damage * SoraCompanionTuning::ShooterDamageShare, FSoraHit::Ranged(From, WeaponId),
            (To - From).GetSafeNormal(), Trace, nullptr, this);
}

void ASoraCompanion::StepUp(bool bFront)
{
    bFrontRank = bFront;
}

void ASoraCompanion::HoldRank(float Dt)
{
    // At the front a step before its post, filed back to load behind it;
    // always facing into the place.
    const FVector Forward = FRotator(0.f, PostYaw, 0.f).Vector();
    const FVector Spot = PostAt + (bFrontRank ? Forward * SoraCompanionTuning::RankStepCm : FVector::ZeroVector);
    if (FVector::Dist2D(Spot, GetActorLocation()) > 20.f)
    {
        MoveToward(Spot, SoraCompanionTuning::RunPace * .4f, 15.f);
        return;
    }
    UpdateLocomotion(false, 1.f);
    SetActorRotation(FMath::RInterpTo(GetActorRotation(), FRotator(0.f, PostYaw, 0.f), Dt, 4.f));
}

void ASoraCompanion::Volley(const FVector& At)
{
    // Each gunner's ball finds the ring at its own fixed place in it.
    const FVector From = GetActorLocation() + FVector(0.f, 0.f, SoraCompanionTuning::EyeHeight);
    const float Angle = CompanionSlot * 2.39996f;
    const FVector End = At + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.f) * (60.f + 35.f * (CompanionSlot % 4)) + FVector(0.f, 0.f, 60.f);
    SetActorRotation(FRotator(0.f, (End - From).Rotation().Yaw, 0.f));
    ++RoundCount;
    SoraDamage::Beam(GetWorld(), From + (End - From).GetSafeNormal() * 50.f, End, FLinearColor(1.f, .72f, .2f), 1.5f, .08f);
    if (USoraGameEvents* Events = USoraGameEvents::Get(this))
    {
        FSoraWeaponFiredEvent Fired;
        Fired.Shooter = this; Fired.WeaponId = WeaponId; Fired.Kind = ESoraShotKind::Hitscan;
        Fired.Origin = From; Fired.Direction = (End - From).GetSafeNormal(); Fired.End = End;
        Events->OnWeaponFired.Broadcast(Fired);
    }
}

void ASoraCompanion::Guide(float Dt)
{
    const APawn* Hero = UGameplayStatics::GetPlayerPawn(this, 0);
    if (!Hero) return;
    const float Distance = FVector::Dist2D(Hero->GetActorLocation(), GetActorLocation());
    if (Distance > SoraCompanionTuning::GuideFarCm)
        MoveToward(Hero->GetActorLocation(), SoraCompanionTuning::RunPace, SoraCompanionTuning::GuideNearCm);
    else UpdateLocomotion(false, 1.f);
}

void ASoraCompanion::TickPlay(float Dt)
{
    if (!bJoined || !SoraFieldcraftRules::IsStanding(StateData) || IsHiddenAway())
    {
        UpdateLocomotion(false, 1.f);
        if (IsHiddenAway() && bHasGoal) WalkToGoal(Dt);
        return;
    }
    switch (Kind)
    {
    case ERole::Escort: if (bHasGoal) WalkToGoal(Dt); return;
    case ERole::Fighter: Fight(Dt); return;
    case ERole::Shooter: Shoot(Dt); return;
    case ERole::Rank: HoldRank(Dt); return;
    case ERole::Guide: Guide(Dt); return;
    case ERole::Bystander: UpdateLocomotion(false, 1.f); return;
    }
}
