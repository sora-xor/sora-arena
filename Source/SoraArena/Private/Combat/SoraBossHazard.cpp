#include "Combat/SoraBossHazard.h"
#include "SoraSettings.h"
#include "Combat/SoraBossCatalog.h"
#include "Combat/SoraCombatEffects.h"
#include "Combat/SoraDamage.h"
#include "SoraBoss.h"
#include "SoraBossRules.h"
#include "SoraEquipmentComponent.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

namespace SoraHazardLook
{
constexpr int32 RimSegments = 16;
// A zone reaches the hero's side, not only his centre.
constexpr float HeroRadius = 34.f;
// A fragile seal stands this tall to arrows and blades, however flat it looks.
constexpr float FragileHeight = 170.f;
constexpr float FragileRadius = 30.f;
constexpr float WardRadius = 30.f;
constexpr float WardHeight = 40.f;
const FLinearColor Amber(1.f, .68f, .16f);
const FLinearColor Cyan(.04f, .85f, .95f);
const FLinearColor Spent(.20f, .20f, .22f);
}

ASoraBossHazard::ASoraBossHazard()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("HazardRoot"));
}

int32 ASoraBossHazard::NowMs() const { return FMath::FloorToInt32(GetWorld()->GetTimeSeconds() * 1000.0); }

static void BlockShotsNotBodies(UStaticMeshComponent* Mesh)
{
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Mesh->SetCollisionObjectType(ECC_WorldDynamic);
    Mesh->SetCollisionResponseToAllChannels(ECR_Block);
    Mesh->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
    Mesh->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
    Mesh->SetCanEverAffectNavigation(false);
}

void ASoraBossHazard::BeginZone(ASoraBoss& From, int32 Attack, int32 AttackSerial, int32 Windup, int32 Root)
{
    Keeper = &From;
    AttackIndex = Attack;
    Serial = AttackSerial;
    WindupMs = Windup;
    RootMs = Root;
    const FSoraBossAttack& Spec = From.Data()->Attacks[Attack];
    RadiusCm = Spec.RadiusCm;
    StartedMs = NowMs();
    BuildZone(Spec.Telegraph == ESoraBossTelegraph::Cyan);
    if (Spec.bFragile)
    {
        Body = ASoraWorldBuilder::Shape(this, RootComponent, TEXT("SealPost"), TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
            FVector(0.f, 0.f, SoraHazardLook::FragileHeight * .5f),
            FVector(SoraHazardLook::FragileRadius / 50.f, SoraHazardLook::FragileRadius / 50.f, SoraHazardLook::FragileHeight / 100.f),
            SoraHazardLook::Amber, true);
        BlockShotsNotBodies(Body);
        Body->SetVisibility(false);
    }
    Paint(0.f);
}

void ASoraBossHazard::BeginWard(ASoraBoss& From, int32 Ward, int32 Place)
{
    Keeper = &From;
    WardIndex = Ward;
    Slot = Place;
    Health = From.Data()->Wards[Ward].Health;
    StartedMs = NowMs();
    BuildWard();
}

void ASoraBossHazard::BuildZone(bool bCyan)
{
    // A zone is a telegraph: the settings' palette (SoraAccessibility).
    const FLinearColor Colour = SoraAccessibility::TelegraphColor(this, bCyan ? SoraAccessibility::ETelegraph::Lock : SoraAccessibility::ETelegraph::Cleave);
    Fill = ASoraWorldBuilder::Shape(this, RootComponent, TEXT("ZoneFill"), TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
        FVector(0.f, 0.f, 1.f), FVector(RadiusCm / 50.f, RadiusCm / 50.f, .02f), Colour);
    for (int32 Segment = 0; Segment < SoraHazardLook::RimSegments; ++Segment)
    {
        const FVector A = FVector(RadiusCm, 0.f, 2.f).RotateAngleAxis(360.f * Segment / SoraHazardLook::RimSegments, FVector::UpVector);
        const FVector B = FVector(RadiusCm, 0.f, 2.f).RotateAngleAxis(360.f * (Segment + 1) / SoraHazardLook::RimSegments, FVector::UpVector);
        UStaticMeshComponent* Edge = ASoraWorldBuilder::Shape(this, RootComponent, FString::Printf(TEXT("ZoneRim%d"), Segment),
            TEXT("/Engine/BasicShapes/Cylinder.Cylinder"), (A + B) * .5f, FVector(.05f, .05f, FVector::Distance(A, B) / 100.f), Colour);
        Edge->SetRelativeRotation(FRotationMatrix::MakeFromZ(B - A).Rotator());
        Rim.Add(Edge);
    }
}

void ASoraBossHazard::BuildWard()
{
    const FSoraBossWard& Spec = Keeper->Data()->Wards[WardIndex];
    Body = ASoraWorldBuilder::Shape(this, RootComponent, TEXT("Ward"), TEXT("/Engine/BasicShapes/Sphere.Sphere"), FVector::ZeroVector,
        FVector(SoraHazardLook::WardRadius / 50.f), Spec.bClosedInvulnerable ? SoraHazardLook::Amber : SoraHazardLook::Cyan, true);
    BlockShotsNotBodies(Body);
}

void ASoraBossHazard::Paint(float Progress)
{
    // The mark fills while its windup runs; armed, it lies full.
    if (Fill)
        Fill->SetRelativeScale3D(FVector(RadiusCm / 50.f * FMath::Clamp(Progress, .05f, 1.f), RadiusCm / 50.f * FMath::Clamp(Progress, .05f, 1.f),
            Progress >= 1.f ? .04f : .02f));
}

bool ASoraBossHazard::IsArmed() const
{
    const ASoraBoss* Boss = Keeper.Get();
    if (IsWard() || !Boss || !GetWorld())
        return false;
    const FSoraBossAttack& Spec = Boss->Data()->Attacks[AttackIndex];
    return SoraBossRules::ObservedZoneAt(NowMs() - StartedMs, WindupMs, Spec.ArmMs, Spec.LifeMs, PreviousArmedMs) == SoraBossRules::EZone::Armed;
}

bool ASoraBossHazard::IsOpen() const
{
    const ASoraBoss* Boss = Keeper.Get();
    if (!IsWard() || !Boss || !GetWorld())
        return false;
    const FSoraBossWard& Spec = Boss->Data()->Wards[WardIndex];
    return SoraBossRules::WardOpen(NowMs() - StartedMs, Spec.OpenEveryMs, Spec.OpenMs, NowMs() - LastBlockMs, Spec.bOpenAfterBlock);
}

void ASoraBossHazard::Expire()
{
    const ASoraBoss* Boss = Keeper.Get();
    if (IsWard() || !Boss)
        return;
    StartedMs = NowMs() - WindupMs - Boss->Data()->Attacks[AttackIndex].ArmMs;
}

void ASoraBossHazard::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    ASoraBoss* Boss = Keeper.Get();
    if (!Boss || Boss->IsDefeated() || !Boss->Data())
    {
        Destroy();
        return;
    }
    const int32 Now = NowMs();
    if (IsWard())
    {
        // Wards circle their boss at its eye; an open one dims while it re-indexes.
        const FSoraBossWard& Spec = Boss->Data()->Wards[WardIndex];
        const float Turn = 2.f * PI * ((Now - StartedMs) % Spec.PeriodMs) / Spec.PeriodMs + 2.f * PI * Slot / FMath::Max(1, Spec.Count);
        const FVector Around = Boss->GetActorLocation() + FVector(0.f, 0.f, SoraHazardLook::WardHeight * Boss->GetActorScale3D().Z);
        if (Now - LastBlockMs > 150)
            SetActorLocation(Around + FVector(FMath::Cos(Turn), FMath::Sin(Turn), 0.f) * Spec.OrbitCm);
        const bool bOpen = IsOpen();
        if (Body && Body->ComponentTags.Contains(TEXT("Open")) != bOpen)
        {
            ASoraWorldBuilder::Tint(Body, bOpen ? SoraHazardLook::Spent : Spec.bClosedInvulnerable ? SoraHazardLook::Amber : SoraHazardLook::Cyan);
            if (bOpen)
                Body->ComponentTags.Add(TEXT("Open"));
            else
                Body->ComponentTags.Remove(TEXT("Open"));
        }
        return;
    }
    const FSoraBossAttack& Spec = Boss->Data()->Attacks[AttackIndex];
    const int32 Elapsed = Now - StartedMs;
    switch (SoraBossRules::ObservedZoneAt(Elapsed, WindupMs, Spec.ArmMs, Spec.LifeMs, PreviousArmedMs))
    {
    case SoraBossRules::EZone::Marked:
        Paint(static_cast<float>(Elapsed) / FMath::Max(1, WindupMs + Spec.ArmMs));
        return;
    case SoraBossRules::EZone::Armed:
    {
        Paint(1.f);
        const int32 ArmedMs = Elapsed - WindupMs - Spec.ArmMs;
        const ACharacter* Hero = UGameplayStatics::GetPlayerCharacter(this, 0);
        const bool bInside = Hero && FVector::Dist2D(Hero->GetActorLocation(), GetActorLocation()) <= RadiusCm + SoraHazardLook::HeroRadius;
        const bool bFirst = PreviousArmedMs < 0;
        if (bFirst && Spec.bBreaksMantle &&
            FVector::Dist2D(Boss->GetActorLocation(), GetActorLocation()) <= RadiusCm + Boss->GetCapsuleComponent()->GetScaledCapsuleRadius())
            Boss->BreakMantle();
        // It strikes when it arms and on every tick; a root or a void also
        // catches whoever steps in.
        const bool bCatches = (RootMs > 0 || Spec.bVoid) && bInside && !bHeroInside && !bFirst;
        if (SoraBossRules::ZoneTick(ArmedMs, PreviousArmedMs, Spec.TickMs) || bCatches)
            StrikeHero();
        PreviousArmedMs = ArmedMs;
        bHeroInside = bInside;
        return;
    }
    case SoraBossRules::EZone::Spent:
        bSpent = true;
        Destroy();
        return;
    }
}

void ASoraBossHazard::StrikeHero()
{
    ASoraBoss* Boss = Keeper.Get();
    ACharacter* Hero = UGameplayStatics::GetPlayerCharacter(this, 0);
    if (!Boss || !Hero || FVector::Dist2D(Hero->GetActorLocation(), GetActorLocation()) > RadiusCm + SoraHazardLook::HeroRadius)
        return;
    const FSoraBossAttack& Spec = Boss->Data()->Attacks[AttackIndex];
    Boss->AnnounceStrike(AttackIndex, Serial);
    const FVector Away = (Hero->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
    if (Spec.Damage > 0)
    {
        FHitResult Trace;
        Trace.ImpactPoint = Hero->GetActorLocation();
        Trace.Location = Trace.ImpactPoint;
        FSoraHit Hit = FSoraHit::Hazard(GetActorLocation());
        Hit.AttackId = Spec.Id;
        SoraDamage::Strike(Hero, Spec.Damage, Hit, Away, Trace, Boss->GetController(), Boss);
    }
    if (RootMs > 0)
        if (USoraCombatEffects* Effects = USoraCombatEffects::Get(this))
            Effects->Root(*Hero, RootMs);
    if (Spec.StaggerMs > 0)
        if (auto* Player = Cast<ASoraPlayerCharacter>(Hero))
            Player->GetEquipment()->Stagger(Spec.StaggerMs / 1000.f);
    // A tile giving way throws the hero back onto firm floor.
    if (Spec.bVoid)
        Hero->LaunchCharacter((Away.IsNearlyZero() ? FVector::ForwardVector : Away) * (RadiusCm + 120.f) * 3.f + FVector(0.f, 0.f, 200.f),
            true, true);
    // A seal that has caught someone is spent.
    if (RootMs > 0 && Spec.bFragile && Spec.LifeMs > 0)
    {
        bSpent = true;
        Destroy();
    }
}

bool ASoraBossHazard::Intercept(const FVector& Point, int32 Damage)
{
    ASoraBoss* Boss = Keeper.Get();
    if (!IsWard() || !Boss || Health <= 0 || IsOpen())
        return false;
    SetActorLocation(Point);
    LastBlockMs = NowMs();
    if (!Boss->Data()->Wards[WardIndex].bClosedInvulnerable)
    {
        Health -= FMath::Max(0, Damage);
        if (Health <= 0)
            Break();
    }
    return true;
}

float ASoraBossHazard::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer)
{
    ASoraBoss* Boss = Keeper.Get();
    if (!Boss || Damage <= 0.f || bSpent)
        return 0.f;
    // Only the hero's side breaks what a boss has set down.
    const ASoraCharacterBase* Attacker = SoraDamage::AttackerOf(Causer);
    if (Attacker && Attacker->IsEnemy())
        return 0.f;
    if (IsWard())
    {
        const FSoraBossWard& Spec = Boss->Data()->Wards[WardIndex];
        if (Health <= 0 || (Spec.bClosedInvulnerable && !IsOpen()))
            return 0.f;
        const int32 Taken = FMath::Min(Health, FMath::RoundToInt32(Damage));
        Health -= Taken;
        if (Health <= 0)
            Break();
        return Taken;
    }
    if (!Boss->Data()->Attacks[AttackIndex].bFragile)
        return 0.f;
    Break();
    return Damage;
}

void ASoraBossHazard::Break()
{
    ASoraBoss* Boss = Keeper.Get();
    bSpent = true;
    Health = 0;
    if (IsWard() && Boss)
        Boss->WardBroken(*this);
    Destroy();
}
