#include "SoraFieldcraft.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Combat/SoraDamage.h"
#include "SoraCampaignDirector.h"
#include "SoraEnemy.h"
#include "SoraGameMode.h"
#include "SoraHorse.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"

// The League's charge on the Nekoyama causeway (ch08.b02, FSoraCharge): the
// riders run the road in a column of twos around the hero with Toranosuke on
// Arashi at his right, easing off when he falls behind his place but never
// waiting; each seal stake bars the road until the hero breaks it (a yari
// thrust at a canter or faster, or two arrows) or, left standing, the riders
// break it once the pack has waited at it StakeBreakMs; and every rider
// strikes the opponents it passes on the causeway.

namespace Craft = SoraFieldcraftRules;
namespace Layout = SoraFieldcraftLayout;

namespace SoraFieldcraftLayout
{
// The column: two riders abreast this far either side of the road's middle,
// ranks this far apart, and the hero's place this far behind its head. His
// rank is his and Toranosuke's alone: the League's riders leave it empty.
constexpr float LaneCm = 220.f;
constexpr float RankCm = 450.f;
constexpr int32 HeroRank = 3;
constexpr float HeroPlaceCm = HeroRank * RankCm;
// The rival keeps this far off the hero's right.
constexpr float RivalSideCm = 260.f;
// The pack halts this short of a standing stake; the hero is at it this near.
constexpr float StakeHaltCm = 450.f;
constexpr float StakeReachedCm = 650.f;
constexpr float BarrierHeightCm = 300.f;
const TCHAR* const Coats[] = {TEXT("bay"), TEXT("chestnut"), TEXT("black_bay")};
}

// ---------------------------------------------------------------------------
// ASoraSealStake
// ---------------------------------------------------------------------------
ASoraSealStake::ASoraSealStake()
{
    USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("StakeRoot"));
    RootComponent = Root;
}

void ASoraSealStake::Build(int32 InIndex, float WidthCm)
{
    Index = InIndex;
    USceneComponent* Root = GetRootComponent();
    // The black stake with its cyan seal, and the barrier it throws across the road.
    Stake = ASoraWorldBuilder::Shape(this, Root, TEXT("SealStake"), Layout::Cylinder, FVector(0.f, 0.f, 130.f), FVector(.4f, .4f, 2.6f),
        FLinearColor(.06f, .07f, .08f), true);
    ASoraWorldBuilder::Shape(this, Root, TEXT("SealStakeSeal"), Layout::Cylinder, FVector(0.f, 0.f, 220.f), FVector(.44f, .44f, .12f),
        FLinearColor(.15f, .85f, .95f));
    Barrier = ASoraWorldBuilder::Shape(this, Root, TEXT("SealBarrier"), Layout::Cube, FVector(0.f, 0.f, Layout::BarrierHeightCm * .5f),
        FVector(.04f, WidthCm / 100.f, Layout::BarrierHeightCm / 100.f), FLinearColor(.1f, .8f, .9f), true);
    for (UStaticMeshComponent* Part : {Stake.Get(), Barrier.Get()})
    {
        Part->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        Part->SetCollisionResponseToAllChannels(ECR_Block);
        Part->SetCanEverAffectNavigation(false);
    }
}

float ASoraSealStake::TakeDamage(float Damage, const FDamageEvent& Event, AController* Instigator, AActor* Causer)
{
    // A yari's thrust, or an arrow, on the stake or its barrier.
    if (!bStanding || !Event.IsOfType(FSoraDamageEvent::ClassID)) return 0.f;
    const FSoraHit& Hit = static_cast<const FSoraDamageEvent&>(Event).Hit;
    const bool bYari = Hit.WeaponId == 19 && Hit.Kind == SoraCombatRules::EHit::Melee;
    const bool bArrow = Hit.WeaponId == 18 && Hit.Kind == SoraCombatRules::EHit::Ranged;
    if (USoraFieldcraft* Fieldcraft = USoraFieldcraft::Get(this); Fieldcraft && (bYari || bArrow)) Fieldcraft->StakeHit(Index, bYari, bArrow);
    return 0.f;
}

void ASoraSealStake::Break()
{
    if (!bStanding) return;
    bStanding = false;
    for (UStaticMeshComponent* Part : {Stake.Get(), Barrier.Get()})
        if (Part)
        {
            Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Part->SetVisibility(false);
        }
}

// ---------------------------------------------------------------------------
// USoraFieldcraft: the charge
// ---------------------------------------------------------------------------
void USoraFieldcraft::StageCharge()
{
    if (!Staged->bCharge) return;
    const auto* Mode = Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    const USoraCampaignDirector* Campaign = Mode ? Mode->Campaign() : nullptr;
    const FSoraChapter* Chapter = Campaign ? Campaign->ActiveChapter() : nullptr;
    const FSoraBeatSpace* Space = Campaign ? Campaign->ActiveSpace() : nullptr;
    const ASoraPlayerCharacter* Player = Hero();
    if (!Chapter || !Space || !Space->bRoute || !Player) return;
    const FSoraCharge& Charge = Staged->Charge;
    const FSoraZone& Road = Chapter->Space.Zones[Space->Zone];
    const float Start = Road.ChainageOf(FVector2D(Space->Mount.At));
    PackChainage = Start + Layout::HeroPlaceCm;
    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    // Toranosuke on Arashi first, then the twenty in a column of twos.
    for (int32 Index = 0; Index <= Charge.Riders; ++Index)
    {
        ASoraHorse* Rider = GetWorld()->SpawnActor<ASoraHorse>(FVector(Road.PointAlong(Start), 0.f), FRotator::ZeroRotator, Params);
        if (!Rider) continue;
        const bool bRival = Index == 0;
        Rider->Build(FName(bRival ? TEXT("black_bay") : Layout::Coats[Index % UE_ARRAY_COUNT(Layout::Coats)]), ASoraHorse::ETack::Riding);
        Rider->SeatRider(bRival);
        Rider->PackId = bRival ? Charge.Rival : FString::Printf(TEXT("league_rider_%02d"), Index);
        Rider->FollowRoad(&Road, Start, Charge.PaceCmS);
        Riders.Add(Rider);
    }
    // The seal stakes across the road.
    for (int32 Index = 0; Index < Charge.Stakes.Num(); ++Index)
    {
        const float At = Road.ChainageOf(Charge.Stakes[Index]);
        ASoraSealStake* Stake = GetWorld()->SpawnActor<ASoraSealStake>(FVector(Road.PointAlong(At), 0.f),
            FRotator(0.f, Road.HeadingAt(At), 0.f), Params);
        if (Stake) Stake->Build(Index, Road.Rect.Max.Y - Road.Rect.Min.Y);
        Stakes.Add(Stake);
        StakeArrows.Add(0);
        StakeHeldMs.Add(0);
        StakeChainage.Add(At);
    }
}

bool USoraFieldcraft::IsStakeStanding(int32 Stake) const
{
    return Stakes.IsValidIndex(Stake) && IsValid(Stakes[Stake]) && Stakes[Stake]->IsStanding();
}

FVector USoraFieldcraft::StakeLocation(int32 Stake) const
{
    return Stakes.IsValidIndex(Stake) && IsValid(Stakes[Stake]) ? Stakes[Stake]->GetActorLocation() : FVector::ZeroVector;
}

void USoraFieldcraft::StakeHit(int32 Stake, bool bYari, bool bArrow)
{
    if (!Staged || !Staged->bCharge || !IsStakeStanding(Stake)) return;
    const auto* Mode = Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    const USoraCampaignDirector* Campaign = Mode ? Mode->Campaign() : nullptr;
    // A thrust breaks it only from a horse at a canter or faster.
    const ASoraHorse* Steed = Campaign && Campaign->IsMounted() ? Campaign->Steed() : nullptr;
    const bool bFast = Steed && SoraMountRules::Index(Steed->Gait()) >= SoraMountRules::Index(SoraMountRules::EGait::Canter);
    if (!Craft::StakeStruck(StakeArrows[Stake], bYari ? Craft::EStakeHit::Yari : bArrow ? Craft::EStakeHit::Arrow : Craft::EStakeHit::None, bFast))
        return;
    Stakes[Stake]->Break();
    Raise(TEXT("stake_broken:") + Staged->Charge.StakeIds[Stake]);
}

void USoraFieldcraft::TickCharge(float DeltaTime, int32 DtMs)
{
    if (!Staged->bCharge || Riders.IsEmpty()) return;
    const auto* Mode = Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    const USoraCampaignDirector* Campaign = Mode ? Mode->Campaign() : nullptr;
    const FSoraChapter* Chapter = Campaign ? Campaign->ActiveChapter() : nullptr;
    const FSoraBeatSpace* Space = Campaign ? Campaign->ActiveSpace() : nullptr;
    const ASoraPlayerCharacter* Player = Hero();
    if (!Chapter || !Space || !Space->bRoute || !Player) return;
    const FSoraCharge& Charge = Staged->Charge;
    const FSoraZone& Road = Chapter->Space.Zones[Space->Zone];
    const AActor* Rides = Campaign->IsMounted() ? static_cast<const AActor*>(Campaign->Steed()) : Player;
    const float Here = Road.ChainageOf(FVector2D(Rides->GetActorLocation()));
    // The pack eases off for a hero fallen behind his place, never waiting,
    // and stands at a stake still barring the road.
    const int32 Lag = FMath::RoundToInt32(PackChainage - Layout::HeroPlaceCm - Here);
    int32 Pace = Craft::PackPaceCmS(Charge.PaceCmS, Charge.CatchUpCmS, Lag);
    float Limit = Road.RouteLength;
    for (int32 Stake = 0; Stake < StakeChainage.Num(); ++Stake)
    {
        if (!IsStakeStanding(Stake)) continue;
        Limit = FMath::Min(Limit, StakeChainage[Stake] - Layout::StakeHaltCm);
        // At a stake the pack or the hero has reached, the riders behind break it in time.
        const bool bAtIt = PackChainage >= StakeChainage[Stake] - Layout::StakeHaltCm - 1.f || Here >= StakeChainage[Stake] - Layout::StakeReachedCm;
        if (!bAtIt) break;
        StakeHeldMs[Stake] += DtMs;
        if (StakeHeldMs[Stake] >= Charge.StakeBreakMs)
        {
            Stakes[Stake]->Break();
            Raise(TEXT("stake_broken_by_riders:") + Charge.StakeIds[Stake]);
        }
        break;
    }
    const float Before = PackChainage;
    PackChainage = FMath::Min(PackChainage + Pace * DeltaTime, FMath::Max(Before, Limit));
    if (PackChainage <= Before) Pace = 0;
    // Toranosuke keeps the hero's right; the column runs two abreast behind its head.
    const FVector Right = FRotator(0.f, Road.HeadingAt(Here) + 90.f, 0.f).Vector();
    const FVector Middle = FVector(Road.PointAlong(Here), 0.f);
    const float HeroLane = FVector::DotProduct(Rides->GetActorLocation() - Middle, Right);
    if (ASoraHorse* Rival = Riders[0])
    {
        const float HalfRoad = (Road.Rect.Max.Y - Road.Rect.Min.Y) * .5f - 200.f;
        const int32 HeroPace = Campaign->IsMounted() ? Campaign->Steed()->SpeedCmS() : FMath::RoundToInt32(Player->GetVelocity().Size2D());
        Rival->SetLane(FMath::Clamp(HeroLane + Layout::RivalSideCm, -HalfRoad, HalfRoad));
        Rival->SetRoadPace(FMath::Max(1, HeroPace));
        Rival->SetRoadChainage(Here);
    }
    for (int32 Index = 1; Index < Riders.Num(); ++Index)
        if (ASoraHorse* Rider = Riders[Index])
        {
            const int32 Rank = (Index - 1) / 2 + ((Index - 1) / 2 >= Layout::HeroRank ? 1 : 0);
            Rider->SetLane((Index % 2 ? -1.f : 1.f) * Layout::LaneCm);
            Rider->SetRoadPace(FMath::Max(1, Pace));
            Rider->SetRoadChainage(PackChainage - Rank * Layout::RankCm);
        }
    RiderStrikes(DtMs);
}

void USoraFieldcraft::RiderStrikes(int32 DtMs)
{
    // Each rider strikes an opponent on the causeway within reach once every
    // RiderStrikeMs, the pack's strokes staggered by rank; drones fly out of reach.
    const int32 Before = RiderClockMs;
    RiderClockMs += DtMs;
    for (int32 Index = 0; Index < Riders.Num(); ++Index)
    {
        ASoraHorse* Rider = Riders[Index];
        if (!IsValid(Rider)) continue;
        const int32 Offset = Index * 97 % Craft::RiderStrikeMs;
        if ((Before + Offset) / Craft::RiderStrikeMs == (RiderClockMs + Offset) / Craft::RiderStrikeMs) continue;
        ASoraEnemy* Target = nullptr;
        float Best = Craft::RiderReachCm;
        for (TActorIterator<ASoraEnemy> It(GetWorld()); It; ++It)
        {
            if (!It->IsEnemy() || !It->IsAlive() || It->IsSubdued() || It->IsFlying()) continue;
            const float Distance = FVector::Dist2D(It->GetActorLocation(), Rider->GetActorLocation());
            if (Distance < Best) { Best = Distance; Target = *It; }
        }
        if (!Target) continue;
        const FVector From = Rider->GetActorLocation() + FVector(0.f, 0.f, 120.f);
        FHitResult Trace; Trace.ImpactPoint = Target->GetActorLocation(); Trace.Location = Trace.ImpactPoint;
        if (SoraDamage::Strike(Target, static_cast<float>(Craft::RiderStrikeDamage), FSoraHit::Melee(From, 19),
            (Target->GetActorLocation() - From).GetSafeNormal(), Trace, nullptr, Rider) > 0.f)
            ++RiderStrikeCount;
    }
}
