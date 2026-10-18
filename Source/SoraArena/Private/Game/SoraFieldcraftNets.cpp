#include "SoraFieldcraft.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Combat/SoraDamage.h"
#include "SoraBeatRules.h"
#include "SoraCampaignDirector.h"
#include "SoraCompanion.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraHorse.h"
#include "SoraPlayerCharacter.h"
#include "SoraSettings.h"
#include "SoraWorldBuilder.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"

// Seizure nets (SoraFieldcraftRules FNet): the drones of a beat's net waves
// (as many of each wave as it nets with) fly to what the hero guards (a
// convoy's pack horses, an escort's ox cart, the planters of a defence), lock
// a quarry under a cyan ring and net it. A netted pack horse halts the whole
// tied string and a netted ox the cart, until the hero cuts the net (Interact
// held beside it, or the ride's blade from the saddle on its side) or brings
// the tether drone down; left too long a load or a planter is hauled away. A
// load freed is let be while a cut net's drone reloads (NetRearmMs). A scout
// wave's drones, and a net wave's drones beyond its netters, hang off the
// road and never net; on ch02.b08 one of G4's crosses to the string's right
// at its mark. Opponents standing at a pack horse or the cart wear it down.
// What happens reaches the beat as its scripts name it (ai:net_windup,
// pattern:net_lock, ai:convoy_netted, npc_downed:planter_*,
// convoy_member_seized, convoy_member_hp0, ai:drone_crossed_right).

namespace Craft = SoraFieldcraftRules;
namespace Layout = SoraFieldcraftLayout;

namespace SoraFieldcraftLayout
{
// A scout keeps to the left of the road the hero rides, a little ahead of
// him (ch02.b08 G1: left, 35 m out), at most this far inside the road's walls
// (the derived road is narrower than the valley the script describes).
constexpr float ScoutSideCm = 3500.f;
constexpr float ScoutWallCm = 200.f;
constexpr float ScoutAheadCm = 800.f;
// A lock breaks if its drone strays this far from the quarry.
constexpr float LockLeashCm = Craft::NetReachCm * 2.5f;
// The drone sent across the road hangs this far to the right of the load it
// nets (within its net's reach), and has crossed once this far right of the
// road's middle (ch02.b08 G4): short of its goal by an errand's reach, it is
// still past the mark, and still close enough to lock the load.
constexpr float CrossHoverCm = 300.f;
constexpr float CrossedCm = 150.f;
static_assert(CrossHoverCm <= Craft::NetReachCm && CrossHoverCm - ASoraEnemyController::ErrandReachCm > CrossedCm,
    "the crossing drone crosses and still nets from the right");
}

void USoraFieldcraft::StageNets()
{
    if (!Staged->bNets) return;
    for (const FSoraNetQuarry& Row : Staged->Nets.Quarry)
    {
        FQuarryState& State = QuarryStates.AddDefaulted_GetRef();
        State.Hp = Row.Hp;
        UStaticMeshComponent* Net = Piece(TEXT("SeizureNet_") + Row.Id, Layout::Sphere, FVector::ZeroVector, FVector(1.9f, 1.9f, .9f),
            FLinearColor(.08f, .75f, .82f));
        Net->SetVisibility(false);
        State.NetMesh = Net;
    }
    NettersJoined.Init(0, Staged->Nets.NetWaves.Num());
    // A blade from the saddle cuts a net on its side (ch02.b08: the katana to the right).
    if (Staged->Nets.SaddleWeapon != INDEX_NONE)
        if (USoraGameEvents* Events = USoraGameEvents::Get(this))
            MeleeHandle = Events->OnMeleeCommitted.AddUObject(this, &USoraFieldcraft::SaddleCut);
}

void USoraFieldcraft::OpponentJoined(ASoraEnemy& Enemy, int32 Wave)
{
    if (!Staged || !Staged->bNets || Enemy.ArchetypeId() != TEXT("drone")) return;
    const FSoraNets& Nets = Staged->Nets;
    // A net wave's first drones, as many as it nets with, take quarry; the
    // rest of it hangs off the road with the scouts (ch02.b08 G2: two of three).
    const int32 Slot = Nets.NetWaves.IndexOfByKey(Wave);
    if (Slot != INDEX_NONE && NettersJoined.IsValidIndex(Slot) && NettersJoined[Slot] < Nets.NetsPerWave[Slot])
    {
        ++NettersJoined[Slot];
        Netters.Add(&Enemy);
        if (Wave == Nets.CrossWave) Crossers.Add(&Enemy);
    }
    else if (Slot != INDEX_NONE || Nets.ScoutWaves.Contains(Wave)) Scouts.Add(&Enemy);
}

bool USoraFieldcraft::IsRearming(const ASoraEnemy& Drone) const
{
    for (const auto& Pair : NetRearm)
        if (Pair.Key.Get() == &Drone) return Pair.Value > 0;
    return false;
}

int32 USoraFieldcraft::NettingDrones() const
{
    int32 Count = 0;
    for (const TWeakObjectPtr<ASoraEnemy>& Drone : Netters) Count += Drone.IsValid() && Drone->IsAlive();
    return Count;
}

bool USoraFieldcraft::IsOnErrand(const ASoraEnemy& Enemy) const
{
    const auto Is = [&](const TWeakObjectPtr<ASoraEnemy>& Drone) { return Drone.Get() == &Enemy; };
    return Netters.ContainsByPredicate(Is) || Scouts.ContainsByPredicate(Is);
}

Craft::ENet USoraFieldcraft::NetOf(int32 Quarry) const
{
    return QuarryStates.IsValidIndex(Quarry) ? QuarryStates[Quarry].Net.State : Craft::ENet::Free;
}

int32 USoraFieldcraft::QuarryHealth(int32 Quarry) const
{
    return QuarryStates.IsValidIndex(Quarry) ? QuarryStates[Quarry].Hp : 0;
}

ASoraEnemy* USoraFieldcraft::TetherOf(int32 Quarry) const
{
    return QuarryStates.IsValidIndex(Quarry) ? QuarryStates[Quarry].Drone.Get() : nullptr;
}

FVector USoraFieldcraft::QuarryLocation(int32 Quarry) const
{
    if (!Staged || !Staged->bNets || !Staged->Nets.Quarry.IsValidIndex(Quarry)) return FVector::ZeroVector;
    const FSoraNetQuarry& Row = Staged->Nets.Quarry[Quarry];
    const auto* Mode = GetWorld() ? Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode()) : nullptr;
    const USoraCampaignDirector* Campaign = Mode ? Mode->Campaign() : nullptr;
    switch (Staged->Nets.Kind)
    {
    case FSoraNets::EKind::PackHorse:
        if (Campaign)
            for (const ASoraHorse* Beast : Campaign->PackHorses())
                if (Beast->PackId == Row.Id) return Beast->GetActorLocation();
        return FVector::ZeroVector;
    case FSoraNets::EKind::Cart:
        // The ox walks at the head of the escorted party.
        return Campaign ? Campaign->PartyLocation() + FVector(0.f, 0.f, 90.f) : FVector::ZeroVector;
    case FSoraNets::EKind::Person:
        return People.IsValidIndex(Row.Index) && IsValid(People[Row.Index]) ? People[Row.Index]->GetActorLocation() : FVector::ZeroVector;
    }
    return FVector::ZeroVector;
}

bool USoraFieldcraft::QuarryHalted() const
{
    if (!Staged || !Staged->bNets || !Staged->Nets.bHalts) return false;
    // A tied string or a cart halts while any of it is netted, or while the
    // string shies from a searchlight.
    for (const FQuarryState& State : QuarryStates)
        if (State.Net.State == Craft::ENet::Netted) return true;
    return StringShyMs > 0;
}

void USoraFieldcraft::TickNets(int32 DtMs)
{
    if (!Staged->bNets) return;
    const FSoraNets& Nets = Staged->Nets;
    StringShyMs = FMath::Max(0, StringShyMs - DtMs);
    TickScouts();
    // Drones that fell or left drop their quarry: a lock breaks, a net goes slack.
    Netters.RemoveAll([](const TWeakObjectPtr<ASoraEnemy>& Drone) { return !Drone.IsValid() || !Drone->IsAlive(); });
    for (int32 Quarry = 0; Quarry < QuarryStates.Num(); ++Quarry)
    {
        FQuarryState& State = QuarryStates[Quarry];
        State.GraceMs = Craft::Rearm(State.GraceMs, DtMs);
        if (State.Drone.IsValid() && State.Drone->IsAlive()) continue;
        State.Drone.Reset();
        if (State.Net.State == Craft::ENet::Locking || State.Net.State == Craft::ENet::Netted)
            NetChanged(Quarry, Craft::Loosen(State.Net));
    }
    for (auto It = NetRearm.CreateIterator(); It; ++It)
        if ((It.Value() = Craft::Rearm(It.Value(), DtMs)) == 0 || !It.Key().IsValid()) It.RemoveCurrent();
    // The road, for the drone sent across it.
    const auto* Mode = Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    const USoraCampaignDirector* Campaign = Mode ? Mode->Campaign() : nullptr;
    const FSoraChapter* Chapter = Campaign ? Campaign->ActiveChapter() : nullptr;
    const FSoraBeatSpace* Space = Campaign ? Campaign->ActiveSpace() : nullptr;
    const FSoraZone* Road = Chapter && Space && Space->bRoute ? &Chapter->Space.Zones[Space->Zone] : nullptr;
    // Each drone of a net wave takes the free quarry nearest it that no other
    // drone has and that is not let be after a cut, flies over it and locks
    // it; the drone that netted it holds its tether above it. A drone whose
    // net was cut takes nothing while it reloads. The drone sent across the
    // road keeps to the string's right: over the load it nets, or beside the
    // nearest while it has none.
    const auto Nearest = [&](const ASoraEnemy& Drone, bool bFreeOnly)
    {
        int32 Found = INDEX_NONE;
        float Best = MAX_flt;
        for (int32 Quarry = 0; Quarry < QuarryStates.Num(); ++Quarry)
        {
            const FQuarryState& Row = QuarryStates[Quarry];
            if (Row.bLost || (bFreeOnly && (Row.Net.State != Craft::ENet::Free || Row.Drone.IsValid() || Row.GraceMs > 0))) continue;
            const float Distance = FVector::Dist2D(QuarryLocation(Quarry), Drone.GetActorLocation());
            if (Distance < Best) { Best = Distance; Found = Quarry; }
        }
        return Found;
    };
    for (const TWeakObjectPtr<ASoraEnemy>& Weak : Netters)
    {
        ASoraEnemy* Drone = Weak.Get();
        auto* Brain = Drone ? Cast<ASoraEnemyController>(Drone->GetController()) : nullptr;
        if (!Brain) continue;
        const bool bCrossing = Road && Drone == Crosser.Get();
        int32 Held = QuarryStates.IndexOfByPredicate([&](const FQuarryState& Row) { return Row.Drone.Get() == Drone; });
        if (Held == INDEX_NONE && !IsRearming(*Drone))
        {
            Held = Nearest(*Drone, true);
            if (Held != INDEX_NONE) QuarryStates[Held].Drone = Drone;
        }
        const int32 Over = Held != INDEX_NONE ? Held : bCrossing ? Nearest(*Drone, false) : INDEX_NONE;
        if (Over == INDEX_NONE)
        {
            // A netter waiting for quarry or reloading still belongs to this
            // convoy assignment. Clearing its errand resumes ordinary combat
            // AI, which fires another seizure net at the rider during reload
            // and throws him from the saddle. Hold station until it can take
            // quarry again instead of starting an unrelated attack.
            Brain->SetErrand(Drone->GetActorLocation(), Drone->GetActorForwardVector(), 1.f, 0, false);
            continue;
        }
        const FVector At = QuarryLocation(Over);
        FVector Hover = At;
        if (bCrossing)
            Hover += FRotator(0.f, Road->HeadingAt(Road->ChainageOf(FVector2D(At))) + 90.f, 0.f).Vector() * Layout::CrossHoverCm;
        Brain->SetErrand(Hover, At - Drone->GetActorLocation(), 1.f, 0, false);
        if (Held == INDEX_NONE) continue;
        FQuarryState& State = QuarryStates[Held];
        const float Distance = FVector::Dist2D(At, Drone->GetActorLocation());
        if (State.Net.State == Craft::ENet::Free && Distance <= Craft::NetReachCm && Craft::BeginLock(State.Net))
        {
            // The lock tone under a cyan ring (ch02.b08's ai:net_windup, ch04.b12's pattern:net_lock).
            Raise(TEXT("ai:net_windup"));
            Raise(TEXT("pattern:net_lock"));
        }
        else if (State.Net.State == Craft::ENet::Locking && Distance > Layout::LockLeashCm)
            NetChanged(Held, Craft::Loosen(State.Net));
    }
    // Every quarry's net; the hero's hand on it where he holds Interact beside it.
    for (int32 Quarry = 0; Quarry < QuarryStates.Num(); ++Quarry)
    {
        FQuarryState& State = QuarryStates[Quarry];
        if (State.bLost) continue;
        const FVector At = QuarryLocation(Quarry);
        const bool bHeld = Holding.Kind == EHoldKind::NetCut && Holding.Index == Quarry;
        const Craft::ENetChange Change = Craft::NetTick(State.Net, Nets.Rules, DtMs, bHeld);
        if (Change == Craft::ENetChange::Freed && bHeld) Holding = FHold();
        if (Change != Craft::ENetChange::None) NetChanged(Quarry, Change);
        if (State.Net.State == Craft::ENet::Locking)
            SoraDamage::Ring(GetWorld(), FVector(At.X, At.Y, 3.f), 150.f,
                SoraAccessibility::TelegraphColor(this, SoraAccessibility::ETelegraph::Lock), .05f);
        if (UStaticMeshComponent* Net = State.NetMesh.Get())
        {
            Net->SetVisibility(State.Net.State == Craft::ENet::Netted);
            if (State.Net.State == Craft::ENet::Netted) Net->SetWorldLocation(At + FVector(0.f, 0.f, 40.f));
        }
        // The tether line up to the drone that holds the net.
        if (State.Net.State == Craft::ENet::Netted && State.Drone.IsValid())
            SoraDamage::Beam(GetWorld(), At + FVector(0.f, 0.f, 80.f), State.Drone->GetActorLocation(), FLinearColor(.1f, .8f, .9f), 1.2f, .05f);
    }
    // Opponents standing at a pack horse or the cart wear it down (the
    // defence's siege rule, SoraBeatRules::SiegeHpPerSecond); a drone on an
    // errand nets rather than strikes.
    if (Nets.Kind == FSoraNets::EKind::Person) return;
    for (int32 Quarry = 0; Quarry < QuarryStates.Num(); ++Quarry)
    {
        FQuarryState& State = QuarryStates[Quarry];
        if (State.bLost || State.Hp <= 0) continue;
        const FVector At = QuarryLocation(Quarry);
        int32 Attackers = 0;
        for (TActorIterator<ASoraEnemy> It(GetWorld()); It; ++It)
            if (It->IsEnemy() && It->IsAlive() && !IsOnErrand(**It) &&
                FVector::Dist2D(It->GetActorLocation(), At) < SoraBeatRules::SiegeRadiusCm)
                ++Attackers;
        const long long Total = State.SiegeMs + static_cast<long long>(Attackers) * DtMs;
        const int32 Damage = static_cast<int32>(Total / SoraBeatRules::SiegeMsPerHp);
        State.SiegeMs = Attackers > 0 ? static_cast<int32>(Total - Damage * SoraBeatRules::SiegeMsPerHp) : 0;
        if (Damage > 0) QuarryDamaged(Quarry, Damage);
    }
}

void USoraFieldcraft::QuarryDamaged(int32 Quarry, int32 Hp)
{
    FQuarryState& State = QuarryStates[Quarry];
    if (State.bLost || Hp <= 0) return;
    State.Hp = FMath::Max(0, State.Hp - Hp);
    if (State.Hp > 0) return;
    // A pack horse or the cart worn to nothing loses the convoy (convoy_member_hp0).
    State.bLost = true;
    Raise(TEXT("convoy_member_hp0:") + Staged->Nets.Quarry[Quarry].Id);
    Raise(TEXT("convoy_member_hp0"));
}

void USoraFieldcraft::NetChanged(int32 Quarry, Craft::ENetChange Change)
{
    const FSoraNets& Nets = Staged->Nets;
    const FSoraNetQuarry& Row = Nets.Quarry[Quarry];
    FQuarryState& State = QuarryStates[Quarry];
    ASoraCompanion* Person = Nets.Kind == FSoraNets::EKind::Person && People.IsValidIndex(Row.Index) ? People[Row.Index].Get() : nullptr;
    switch (Change)
    {
    case Craft::ENetChange::Netted:
    {
        Raise(TEXT("netted:") + Row.Id);
        if (Nets.Kind == FSoraNets::EKind::PackHorse) Raise(TEXT("ai:convoy_netted"));
        else if (Nets.Kind == FSoraNets::EKind::Cart) Raise(TEXT("ai:cart_netted"));
        else if (Person)
        {
            // A netted planter kneels under the net (npc_downed:planter_*).
            Person->Present(Craft::EState::Bound);
            RaiseDowned(*Person);
        }
        // The net's impact frightens a horse near it.
        const auto* Mode = Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
        USoraCampaignDirector* Campaign = Mode ? Mode->Campaign() : nullptr;
        const FSoraBeat* Beat = Campaign ? Campaign->ActiveBeatData() : nullptr;
        if (ASoraHorse* Steed = Campaign ? Campaign->Steed() : nullptr; Steed && Beat && Beat->Space.bMount &&
            Beat->Space.Mount.FearRadiusCm > 0 && Campaign->IsMounted() &&
            FVector::Dist2D(Steed->GetActorLocation(), QuarryLocation(Quarry)) < Beat->Space.Mount.FearRadiusCm)
        {
            Steed->Spook();
            Raise(TEXT("horse_spooked"));
            Raise(TEXT("ai:horse_spooked:kurimaru"));
        }
        return;
    }
    case Craft::ENetChange::Freed:
        // The net cut, or its tether brought down: the load is let be for
        // NetRearmMs (a cut net's drone reloads meanwhile), then any drone
        // may come for it again.
        if (State.Drone.IsValid() && State.Drone->IsAlive()) NetRearm.Add(State.Drone, Craft::NetRearmMs);
        State.Drone.Reset();
        State.GraceMs = Craft::NetRearmMs;
        Raise(TEXT("net_freed:") + Row.Id);
        if (Person)
        {
            Person->Present(Craft::EState::Up);
            Raise(TEXT("npc_freed:") + Row.Id);
        }
        return;
    case Craft::ENetChange::Taken:
    {
        // Hauled away: a load seized loses the convoy; a planter taken is a
        // target lost (the defence fails at its limit).
        State.bLost = true;
        State.Drone.Reset();
        if (UStaticMeshComponent* Net = State.NetMesh.Get()) Net->SetVisibility(false);
        Raise(TEXT("hauled:") + Row.Id);
        if (!Nets.LostEvent.IsEmpty()) Raise(Nets.LostEvent);
        if (Person)
        {
            Person->Present(Craft::EState::Dead);
            const auto* Mode = Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
            if (USoraCampaignDirector* Campaign = Mode ? Mode->Campaign() : nullptr)
                Campaign->DamageDefendedTarget(Row.Index, Campaign->ActiveTask().TargetHp[Row.Index]);
        }
        return;
    }
    case Craft::ENetChange::None:
        return;
    }
}

void USoraFieldcraft::SaddleCut(const FSoraMeleeCommittedEvent& Event)
{
    if (!Staged || !Staged->bNets || Event.WeaponId != Staged->Nets.SaddleWeapon) return;
    const auto* Mode = GetWorld() ? Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode()) : nullptr;
    const USoraCampaignDirector* Campaign = Mode ? Mode->Campaign() : nullptr;
    const ASoraHorse* Steed = Campaign && Campaign->IsMounted() ? Campaign->Steed() : nullptr;
    if (!Steed || Event.Attacker != Hero()) return;
    // A netted horse at the rider's flank, on the ride's side for the blade
    // (ch02.b08: ride up on its left and cut to the right).
    for (int32 Quarry = 0; Quarry < QuarryStates.Num(); ++Quarry)
    {
        if (QuarryStates[Quarry].Net.State != Craft::ENet::Netted) continue;
        const FVector2D Local = Steed->LocalOf(QuarryLocation(Quarry));
        if (Local.Y * Staged->Nets.SaddleSide <= 0.f || FMath::Abs(Local.Y) > Craft::SaddleCutCm || FMath::Abs(Local.X) > 300.f)
            continue;
        if (!Craft::CutNet(QuarryStates[Quarry].Net)) continue;
        Raise(TEXT("net_cut:") + Staged->Nets.Quarry[Quarry].Id);
        NetChanged(Quarry, Craft::ENetChange::Freed);
        return;
    }
}

void USoraFieldcraft::TickScouts()
{
    Scouts.RemoveAll([](const TWeakObjectPtr<ASoraEnemy>& Drone) { return !Drone.IsValid() || !Drone->IsAlive(); });
    const ASoraPlayerCharacter* Player = Hero();
    const auto* Mode = GetWorld() ? Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode()) : nullptr;
    const USoraCampaignDirector* Campaign = Mode ? Mode->Campaign() : nullptr;
    const FSoraChapter* Chapter = Campaign ? Campaign->ActiveChapter() : nullptr;
    const FSoraBeatSpace* Space = Campaign ? Campaign->ActiveSpace() : nullptr;
    if (!Player || !Chapter || !Space || !Space->bRoute) return;
    const FSoraZone& Road = Chapter->Space.Zones[Space->Zone];
    // A scout hangs off the road on the hero's left, a little ahead of him, and never nets.
    const float Here = Road.ChainageOf(FVector2D(Player->GetActorLocation()));
    const FVector Forward = FRotator(0.f, Road.HeadingAt(Here), 0.f).Vector();
    const FVector Left = -FRotator(0.f, Road.HeadingAt(Here) + 90.f, 0.f).Vector();
    const FVector Middle(Road.PointAlong(Here), Player->GetActorLocation().Z);
    for (int32 Index = 0; Index < Scouts.Num(); ++Index)
        if (auto* Brain = Cast<ASoraEnemyController>(Scouts[Index]->GetController()))
        {
            FVector Goal = Middle + Left * Layout::ScoutSideCm + Forward * (Layout::ScoutAheadCm + Index * 500.f);
            Goal.X = FMath::Clamp(Goal.X, Road.Rect.Min.X + Layout::ScoutWallCm, Road.Rect.Max.X - Layout::ScoutWallCm);
            Goal.Y = FMath::Clamp(Goal.Y, Road.Rect.Min.Y + Layout::ScoutWallCm, Road.Rect.Max.Y - Layout::ScoutWallCm);
            Brain->SetErrand(Goal, Player->GetActorLocation() - Goal, 1.f, 0, false);
        }
    // Past the crossing mark one netting drone of its wave crosses the road
    // to the string's right (ch02.b08 G4, one_crosses_right_at_m), out of the
    // bow's left arc until the hero drops back and crosses behind the string.
    // Brought down before it gets there, the next of its wave goes.
    const FSoraNets& Nets = Staged->Nets;
    if (Nets.CrossWave == INDEX_NONE || bDroneCrossed || Here < Nets.CrossAtCm) return;
    if (!Crosser.IsValid() || !Crosser->IsAlive())
    {
        Crosser.Reset();
        for (const TWeakObjectPtr<ASoraEnemy>& Drone : Crossers)
            if (Drone.IsValid() && Drone->IsAlive())
            {
                Crosser = Drone;
                break;
            }
    }
    const ASoraEnemy* Drone = Crosser.Get();
    if (!Drone) return;
    const float At = Road.ChainageOf(FVector2D(Drone->GetActorLocation()));
    const FVector Right = FRotator(0.f, Road.HeadingAt(At) + 90.f, 0.f).Vector();
    const FVector Offset = Drone->GetActorLocation() - ASoraWorldBuilder::Floor(Road.PointAlong(At), Drone->GetActorLocation().Z);
    if (FVector::DotProduct(Offset, Right) <= Layout::CrossedCm) return;
    bDroneCrossed = true;
    Raise(TEXT("ai:drone_crossed_right"));
}
