#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Combat/SoraCombatEffects.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraFieldcraftTestWorld.h"
#include "SoraRecoveryAutomation.h"
#include "SoraGameEvents.h"
#include "SoraHorse.h"
#include "SoraMountRules.h"
#include "SoraSettings.h"
#include "SoraStealthRules.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/DamageType.h"
#include "Misc/ScopeExit.h"

// What the chapters script beyond the hero's own fieldcraft, in real game
// worlds: each stealth zone's authored detection and each guard's authored
// senses, and a detection carried to the next zone; seizure nets on a
// convoy's pack horses (cut from the saddle, by hand, freed by a downed
// tether, or hauled off to fail the ride), on the ox cart and on the planters
// of a defence that fails at its third loss, a load cut free let be while
// its drone reloads, the ravine wave's two netters and the drone that crosses
// the road; the rider thrown when a net catches him and the whistle that
// brings his horse back; the moat's searchlights, the lotus that hides a head
// from them, and a ship's light that frightens horses; the one-shot bell; the
// cook-fires a hold waits for; ladders onto the board roofs, a drop heard as
// far as its roof's script says, and a retry from the ladder; the guarded
// hoist; the volley's smoke bank that hides the lane but stops no round, and
// Easy's auto-order; and the League's charge beside the hero, its riders
// clear of his rank.
namespace SoraFieldcraftSetsAutomation
{
using namespace SoraFieldcraftAutomation;

// Opponents held still where they stand: no brain, no movement.
void HoldStill(ASoraEnemy* Enemy)
{
    if (!Enemy) return;
    Enemy->SetActorTickEnabled(false);
    Enemy->GetCharacterMovement()->SetComponentTickEnabled(false);
    if (AController* Brain = Enemy->GetController()) Brain->SetActorTickEnabled(false);
}

TArray<ASoraEnemy*> Guards(const FBeatWorld& W)
{
    TArray<ASoraEnemy*> Found;
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It)
        if (const auto* Brain = Cast<ASoraEnemyController>(It->GetController()); Brain && Brain->IsGuard() && It->IsAlive())
            Found.Add(*It);
    Found.Sort([](const ASoraEnemy& A, const ASoraEnemy& B) { return A.EnemySlot() < B.EnemySlot(); });
    return Found;
}

void KillAll(const FBeatWorld& W)
{
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It)
        if (It->IsAlive()) UGameplayStatics::ApplyDamage(*It, It->Health + 1000.f, nullptr, nullptr, UDamageType::StaticClass());
}

const FSoraZone& Road(const FBeatWorld& W)
{
    return W.Campaign()->ActiveChapter()->Space.Zones[W.BeatData().Space.Zone];
}
} // namespace SoraFieldcraftSetsAutomation

using namespace SoraFieldcraftSetsAutomation;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftAuthoredSensesTest,
    "SoraArena.Fieldcraft.AuthoredSenses",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftAuthoredSensesTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    {
        // ch03.b03: five guards with their own eyes and ears, the zone's detection and lethal takedowns.
        FBeatWorld W(*this, TEXT("FieldcraftSenses"), 2, 2);
        if (!W.Start())
            return false;
        const FSoraBeat& Beat = W.BeatData();
        const TArray<ASoraEnemy*> Posted = Guards(W);
        if (!TestEqual(TEXT("Every authored guard takes its post"), Posted.Num(), Beat.Guards.Num()))
            return false;
        for (int32 Index = 0; Index < Posted.Num(); ++Index)
        {
            const FSoraGuard& Row = Beat.Guards[Index];
            const SoraStealthRules::FPerception& Senses = Posted[Index]->Perception();
            const FString What = FString::Printf(TEXT("Guard %d (%s)"), Index, *Row.Type.ToString());
            TestEqual(*(What + TEXT(" sees as far as the script says")), Senses.SightRangeCm, Row.SightCm);
            TestEqual(*(What + TEXT(" sees as far in the dark")), Senses.DarkSightRangeCm, Row.DarkSightCm);
            TestEqual(*(What + TEXT(" has its authored view cone")), Senses.ViewConeMilli,
                FMath::RoundToInt32(FMath::Cos(FMath::DegreesToRadians(Row.ViewDegrees * .5)) * 1000.0));
            TestEqual(*(What + TEXT(" hears as far")), Senses.HearingCm, Row.HearingCm);
            if (Row.SuspicionPermille > 0)
                TestEqual(*(What + TEXT(" is as reluctant as the script says")), Senses.SuspicionPermille, Row.SuspicionPermille);
        }
        TestEqual(TEXT("The kido-ban conscript notices at 0.7 of an enforcer's rate"), Posted[0]->Perception().SuspicionPermille, 700);
        const SoraStealthRules::FVigilance Vigil = W.Stealth()->Vigilance();
        TestTrue(TEXT("The zone searches 20 s on Normal, as authored"), Vigil.SearchDurationMs == 20000 && Vigil.RatePermille == 1000 &&
            Vigil.SuspicionThreshold == 250 * SoraStealthRules::AwarenessScale);
        TestTrue(TEXT("Its rear takedowns are lethal by default"), W.Stealth()->Zone().bRearTakedowns && W.Stealth()->Zone().bLethalDefault);
        // The kido-ban keeps his post at the wicket and turns about every 12 s.
        ASoraEnemy* Kidoban = Posted[0];
        for (int32 Index = 1; Index < Posted.Num(); ++Index) Posted[Index]->Destroy();
        const FBox2D Yard = W.Campaign()->ActiveChapter()->Space.Zones[Beat.Space.Zone].Rect;
        W.Stand(FVector(Yard.Max.X - 900.f, Beat.Space.Entry.Y, 0.f));
        // His facing two seconds after one turn, and two seconds after the next.
        const auto Turn = [&]() { return FMath::FloorToInt32(W.World->GetTestWorld()->GetTimeSeconds() * 1000.0) / 12000; };
        const auto Settle = [&]()
        {
            const int32 From = Turn();
            for (int32 Frame = 0; Frame < 60 && Turn() == From; ++Frame)
                if (!W.Tick(1, .25f)) return false;
            return W.Tick(8, .25f);
        };
        if (!Settle())
            return false;
        const FVector PostAt = Kidoban->GetActorLocation();
        const float Before = Kidoban->GetActorRotation().Yaw;
        if (!Settle())
            return false;
        const float Turned = FMath::Abs(FRotator::NormalizeAxis(Kidoban->GetActorRotation().Yaw - Before));
        TestTrue(TEXT("The kido-ban keeps his post"), FVector::Dist2D(Kidoban->GetActorLocation(), PostAt) < 120.f);
        TestTrue(TEXT("and turns about every twelve seconds"), Turned > 150.f);
    }
    {
        // ch06.b02: the moat notices at 0.8 of the rate, suspicious at 0.35 of the meter.
        FBeatWorld W(*this, TEXT("FieldcraftSensesMoat"), 5, 1);
        if (!W.Start())
            return false;
        const SoraStealthRules::FVigilance Vigil = W.Stealth()->Vigilance();
        TestTrue(TEXT("The moat's zone takes its authored detection"), Vigil.RatePermille == 800 &&
            Vigil.SuspicionThreshold == 350 * SoraStealthRules::AwarenessScale && Vigil.SearchDurationMs == 20000);
        const TArray<ASoraEnemy*> Posted = Guards(W);
        TestTrue(TEXT("The parapet sees 35 m, 12 m in the dark"), Posted.Num() == 3 && Posted[0]->Perception().SightRangeCm == 3500 &&
            Posted[0]->Perception().DarkSightRangeCm == 1200);
    }
    {
        // ch03.b02 seen: the word goes ahead, and ch03.b03's guards start suspicious and wary.
        FBeatWorld W(*this, TEXT("FieldcraftCarryover"), 2, 1);
        if (!W.Start())
            return false;
        W.Harden();
        const TArray<ASoraEnemy*> Drones = Guards(W);
        if (!TestTrue(TEXT("ch03.b02's drones patrol"), !Drones.IsEmpty()))
            return false;
        FSoraStealthDetection Seen;
        Seen.By = Drones[0];
        W.Stealth()->OnDetected.Broadcast(Seen);
        W.Stand(Floor(W.BeatData().Space.Exit.Center));
        for (int32 Frame = 0; Frame < 30 && W.Campaign()->ActiveBeat() == W.Beat; ++Frame)
            if (!W.Tick(1)) return false;
        if (!TestEqual(TEXT("Reaching the exit moves on to the ward gate"), W.Campaign()->ActiveBeat(), W.Beat + 1) || !W.Tick(2))
            return false;
        const TArray<ASoraEnemy*> Gate = Guards(W);
        bool bWarned = !Gate.IsEmpty();
        for (const ASoraEnemy* Guard : Gate)
        {
            const auto* Brain = Cast<ASoraEnemyController>(Guard->GetController());
            bWarned &= Brain && Brain->IsWary() && Brain->State() != SoraStealthRules::EState::Unaware;
        }
        TestTrue(TEXT("The gate's guards start suspicious and wary"), bWarned && W.Stealth()->Zone().bCarriedOver);
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftConvoyNetsTest,
    "SoraArena.Fieldcraft.ConvoyNets",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftConvoyNetsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch02.b08: the pack string on the kaidō and the drones that net it.
    FBeatWorld W(*this, TEXT("FieldcraftConvoy"), 1, 7);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    USoraCampaignDirector* Campaign = W.Campaign();
    const FSoraZone& Kaido = Road(W);
    TArray<ASoraHorse*> Convoy = Campaign->PackHorses();
    if (!TestTrue(TEXT("The string of three pack horses is the nets' quarry"), Convoy.Num() == 3 && Fieldcraft->QuarryCount() == 3 &&
        Campaign->IsMounted()))
        return false;
    // Past the G2 mark with the string close by: the ravine's drones come for it.
    const float At = Kaido.RouteLength * .34f;
    Campaign->Steed()->Place(Floor(Kaido.PointAlong(At)), Kaido.HeadingAt(At));
    for (int32 Index = 0; Index < Convoy.Num(); ++Index)
        Convoy[Index]->FollowRoad(&Kaido, At + 1500.f + 450.f * Index, 450);
    const auto NettedOne = [&]()
    {
        for (int32 Quarry = 0; Quarry < Fieldcraft->QuarryCount(); ++Quarry)
            if (Fieldcraft->NetOf(Quarry) == SoraFieldcraftRules::ENet::Netted) return Quarry;
        return static_cast<int32>(INDEX_NONE);
    };
    const auto WaitForNet = [&](int32 Quarters)
    {
        for (int32 Frame = 0; Frame < Quarters && NettedOne() == INDEX_NONE; ++Frame)
            if (!W.Tick(1, .25f)) return static_cast<int32>(INDEX_NONE);
        return NettedOne();
    };
    int32 Netted = WaitForNet(160);
    if (!TestTrue(TEXT("A drone of the net wave locks a pack horse and nets it"), Netted != INDEX_NONE))
        return false;
    TestTrue(TEXT("The lock tone and the net are the beat's events"), W.Raised(TEXT("ai:net_windup")) && W.Raised(TEXT("ai:convoy_netted")));
    TestTrue(TEXT("The first net shows its prompt"), W.PromptOn(TEXT("ai:convoy_netted@1")));
    ASoraEnemy* NetDrone = Fieldcraft->TetherOf(Netted);
    TestNotNull(TEXT("Its drone holds the tether"), NetDrone);
    TestEqual(TEXT("Two of the ravine's three drones net; the third scouts"), Fieldcraft->NettingDrones(), 2);
    TestFalse(TEXT("No drone crosses the road before its mark"), W.Raised(TEXT("ai:drone_crossed_right")));
    const float Before = Convoy[0]->RoadChainage();
    if (!W.Tick(4, .25f))
        return false;
    TestTrue(TEXT("A net on any horse halts the whole tied string"), Fieldcraft->QuarryHalted() &&
        FMath::IsNearlyEqual(Convoy[0]->RoadChainage(), Before, 1.f));
    // From the saddle: ride up on its left and cut to the right with the katana.
    const FVector Load = Fieldcraft->QuarryLocation(Netted);
    const float Yaw = Kaido.HeadingAt(Kaido.ChainageOf(FVector2D(Load)));
    const FVector Right = FRotator(0.f, Yaw + 90.f, 0.f).Vector();
    Campaign->Steed()->Place(FVector(Load.X, Load.Y, 0.f) - Right * 250.f, Yaw);
    if (!W.Press(EKeys::One) || !W.Tick(20))
        return false;
    W.Hero()->GetController()->SetControlRotation(FRotator(0.f, Yaw + 90.f, 0.f));
    for(int32 Index=1;Index<Convoy.Num();++Index)
        TestTrue(TEXT("The waiting convoy retains separate 450 cm road positions"),
            FMath::IsNearlyEqual(Convoy[Index]->RoadChainage()-Convoy[Index-1]->RoadChainage(),450.f,1.f));
    if (!W.Press(EKeys::RightMouseButton) || !W.Tick(2))
        return false;
    TestTrue(TEXT("A katana cut from the saddle to the right frees the netted horse"),
        Fieldcraft->NetOf(Netted) != SoraFieldcraftRules::ENet::Netted && W.Raised(TEXT("net_cut:") + Fieldcraft->Active()->Nets.Quarry[Netted].Id));
    // Cut free, the load is let be while its drone reloads (9 s): for eight
    // seconds that drone takes nothing and nothing nets the horse cut free.
    TestTrue(TEXT("The drone whose net was cut reloads"), NetDrone && Fieldcraft->IsRearming(*NetDrone));
    const int32 Freed = Netted;
    bool bLeftBe = true;
    bool bRiderLeftBe = true;
    for (int32 Frame = 0; Frame < 32; ++Frame)
    {
        if (!W.Tick(1, .25f)) return false;
        bLeftBe &= Fieldcraft->NetOf(Freed) == SoraFieldcraftRules::ENet::Free;
        bRiderLeftBe &= Campaign->IsMounted();
        for (int32 Quarry = 0; Quarry < Fieldcraft->QuarryCount(); ++Quarry) bLeftBe &= Fieldcraft->TetherOf(Quarry) != NetDrone;
    }
    TestTrue(TEXT("While it reloads it takes nothing, and the horse cut free is let be"), bLeftBe);
    TestTrue(TEXT("A reloading netter does not fire another net at the rider"), bRiderLeftBe);
    // A drone brought down lets its net fall slack.
    Netted = WaitForNet(160);
    if (!TestTrue(TEXT("The drones net again"), Netted != INDEX_NONE))
        return false;
    ASoraEnemy* Tether = Fieldcraft->TetherOf(Netted);
    if (!TestNotNull(TEXT("The net hangs from its drone"), Tether))
        return false;
    UGameplayStatics::ApplyDamage(Tether, Tether->Health + 10.f, W.Hero()->GetController(), W.Hero(), UDamageType::StaticClass());
    if (!W.Tick(2))
        return false;
    TestTrue(TEXT("Shooting the tether drone frees the load"), Fieldcraft->NetOf(Netted) != SoraFieldcraftRules::ENet::Netted &&
        W.Raised(TEXT("net_freed:") + Fieldcraft->Active()->Nets.Quarry[Netted].Id));
    // On foot: Interact held beside the net for a second cuts it.
    Netted = WaitForNet(200);
    if (!TestTrue(TEXT("A third net falls"), Netted != INDEX_NONE))
        return false;
    if (!TestTrue(TEXT("The convoy remains in live play before the on-foot cut"), W.Mode()->IsPlaying()) ||
        !TestTrue(TEXT("The rider is still in the saddle before pressing dismount"), Campaign->IsMounted()))
        return false;
    if (!W.Press(EKeys::E) || !W.Tick(2) || !TestFalse(TEXT("E in the saddle dismounts him"), Campaign->IsMounted()))
        return false;
    W.Stand(Fieldcraft->QuarryLocation(Netted) + FVector(0.f, 120.f, 0.f));
    if (!W.Tick(1) || !W.Hold(EKeys::E, 80))
        return false;
    TestTrue(TEXT("Interact held a second beside the net cuts it"), Fieldcraft->NetOf(Netted) != SoraFieldcraftRules::ENet::Netted);
    // Left netted fifteen seconds, the load is lifted away and the ride fails.
    Netted = WaitForNet(200);
    if (!TestTrue(TEXT("A net falls once more"), Netted != INDEX_NONE))
        return false;
    for (int32 Frame = 0; Frame < 70 && !W.Mode()->bDefeated; ++Frame)
        if (!W.Tick(1, .25f)) return false;
    TestTrue(TEXT("Fifteen seconds netted, the load is seized and the ride fails to its checkpoint"),
        W.Raised(TEXT("convoy_member_seized")) && W.Mode()->bDefeated);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftDroneCrossingTest,
    "SoraArena.Fieldcraft.DroneCrossing",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftDroneCrossingTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch02.b08 G4: past 1 020 m one of the wave's netting drones crosses the
    // road to the string's right, out of the bow's left arc.
    FBeatWorld W(*this, TEXT("FieldcraftDroneCrossing"), 1, 7);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    USoraCampaignDirector* Campaign = W.Campaign();
    const FSoraZone& Kaido = Road(W);
    const FSoraNets& Nets = Fieldcraft->Active()->Nets;
    if (!TestTrue(TEXT("G4 is the crossing wave, its mark at 1 020 m"), Nets.CrossWave == 3 && Nets.CrossAtCm == 102000 &&
        Nets.NetsPerWave == TArray<int32>({2, 2, 3})))
        return false;
    // Clear G1-G3 through normal damage before reaching G4. Jumping straight
    // past all four triggers leaves seven earlier drones queued against the
    // six-opponent cap, so the crossing wave cannot enter the world.
    const float BeforeG4 = Kaido.RouteLength * .70f;
    Campaign->Steed()->Place(Floor(Kaido.PointAlong(BeforeG4)), Kaido.HeadingAt(BeforeG4));
    for (int32 Frame = 0; Frame < 120; ++Frame)
    {
        if (!W.Tick(1)) return false;
        for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It)
            if (It->IsAlive())
                UGameplayStatics::ApplyDamage(*It, It->Health + 10.f, W.Hero()->GetController(), W.Hero(), UDamageType::StaticClass());
        const auto& State = Campaign->TaskProgress();
        if (State.Down[0] == 2 && State.Down[1] == 3 && State.Down[2] == 2) break;
    }
    const auto& Cleared = Campaign->TaskProgress();
    if (!TestTrue(TEXT("The seven earlier drones are defeated before G4 is released"),
        Cleared.Down[0] == 2 && Cleared.Down[1] == 3 && Cleared.Down[2] == 2) ||
        !TestFalse(TEXT("No crossing is reported before its mark"), W.Raised(TEXT("ai:drone_crossed_right"))))
        return false;
    // Just past the mark, the string walking slowly ahead of the hero.
    const float At = Nets.CrossAtCm + 300.f;
    Campaign->Steed()->Place(Floor(Kaido.PointAlong(At)), Kaido.HeadingAt(At));
    TArray<ASoraHorse*> Convoy = Campaign->PackHorses();
    for (int32 Index = 0; Index < Convoy.Num(); ++Index)
        Convoy[Index]->FollowRoad(&Kaido, At + 600.f + 450.f * Index, 60);
    for (int32 Frame = 0; Frame < 200 && !W.Raised(TEXT("ai:drone_crossed_right")); ++Frame)
        if (!W.Tick(1, .25f)) return false;
    if (!TestTrue(TEXT("Past its mark one of G4's netting drones crosses to the string's right"), W.Raised(TEXT("ai:drone_crossed_right"))))
        return false;
    if (!W.Tick(8, .25f))
        return false;
    int32 Right = 0;
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It)
    {
        if (!It->IsAlive() || It->ArchetypeId() != TEXT("drone")) continue;
        const float Chainage = Kaido.ChainageOf(FVector2D(It->GetActorLocation()));
        const FVector Side = FRotator(0.f, Kaido.HeadingAt(Chainage) + 90.f, 0.f).Vector();
        Right += FVector::DotProduct(It->GetActorLocation() - Floor(Kaido.PointAlong(Chainage)), Side) > 150.f;
    }
    TestTrue(TEXT("and stays there, right of the road"), Right >= 1);
    TestEqual(TEXT("It crosses once"), W.Count(TEXT("ai:drone_crossed_right")), 1);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftHorseDownTest,
    "SoraArena.Fieldcraft.HorseDown",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftHorseDownTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    {
        // ch02.b08 (on_horse_down: dismount_continue): a net's catch throws the rider; a whistle brings her back.
        FBeatWorld W(*this, TEXT("FieldcraftHorseDown"), 1, 7);
        if (!W.Start())
            return false;
        W.Harden();
        USoraCampaignDirector* Campaign = W.Campaign();
        for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
        const float Health = W.Hero()->Health;
        USoraCombatEffects::Get(W.Hero())->Root(*W.Hero(), 1500);
        if (!W.Tick(2))
            return false;
        TestTrue(TEXT("Caught in a net the horse stumbles and throws him"), !Campaign->IsMounted() && W.Hero()->Health < Health);
        TestFalse(TEXT("and the ride goes on with him on foot"), W.Mode()->bDefeated);
        const ASoraHorse* Kurimaru = Campaign->Steed();
        W.Stand(Kurimaru->GetActorLocation() + Kurimaru->GetActorForwardVector() * 1500.f, Kurimaru->GetActorRotation().Yaw);
        if (!W.Tick(40, .25f))
            return false;
        if (!W.Press(EKeys::E) || !W.Tick(16, .25f))
            return false;
        const FVector2D Local = Kurimaru->LocalOf(W.Hero()->GetActorLocation());
        TestTrue(TEXT("A whistle brings her to his side, with him at her right"), Local.Size() < 300.f && Local.Y > 0.f);
        if (!W.Press(EKeys::E) || !W.Tick(2))
            return false;
        TestTrue(TEXT("and he mounts again"), Campaign->IsMounted());
    }
    {
        // ch08.b02 (on_horse_down: checkpoint): the charge goes back to its checkpoint.
        FBeatWorld W(*this, TEXT("FieldcraftHorseDownCharge"), 7, 1);
        if (!W.Start())
            return false;
        W.Harden();
        USoraCombatEffects::Get(W.Hero())->Root(*W.Hero(), 1500);
        if (!W.Tick(2))
            return false;
        TestTrue(TEXT("A horse down in the charge returns to the checkpoint"), W.Mode()->bDefeated);
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftPlantersTest,
    "SoraArena.Fieldcraft.PlantersNets",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftPlantersTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch04.b12: eight planters under drone nets; hauled after 12 s, the third loss fails.
    FBeatWorld W(*this, TEXT("FieldcraftPlanters"), 3, 11);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    USoraCampaignDirector* Campaign = W.Campaign();
    if (!TestTrue(TEXT("The planters are the drones' quarry"), Fieldcraft->QuarryCount() == 8 && Fieldcraft->PeopleInPlay().Num() == 8))
        return false;
    // Otane's chain would pull the drones down: only the nets are measured here.
    for (const TObjectPtr<ASoraCompanion>& Ally : Fieldcraft->AlliesInPlay()) Ally->SetActorTickEnabled(false);
    const auto Count = [&](SoraFieldcraftRules::ENet State)
    {
        int32 Total = 0;
        for (int32 Quarry = 0; Quarry < Fieldcraft->QuarryCount(); ++Quarry) Total += Fieldcraft->NetOf(Quarry) == State;
        return Total;
    };
    for (int32 Frame = 0; Frame < 200 && Count(SoraFieldcraftRules::ENet::Netted) < 3; ++Frame)
        if (!W.Tick(1, .25f)) return false;
    if (!TestEqual(TEXT("The first wave's three drones net three planters"), Count(SoraFieldcraftRules::ENet::Netted), 3))
        return false;
    TestTrue(TEXT("A netted planter is npc_downed:planter_*"), W.Raised(TEXT("npc_downed:planter_*")) && W.Raised(TEXT("npc_downed:any")));
    int32 Cut = INDEX_NONE;
    for (int32 Quarry = 0; Quarry < Fieldcraft->QuarryCount() && Cut == INDEX_NONE; ++Quarry)
        if (Fieldcraft->NetOf(Quarry) == SoraFieldcraftRules::ENet::Netted) Cut = Quarry;
    TestTrue(TEXT("A netting drone does not wear its planter down"), Campaign->TaskProgress().TargetHp[Cut] == Campaign->ActiveTask().TargetHp[Cut]);
    // One cut free by hand (1 s).
    W.Stand(Fieldcraft->QuarryLocation(Cut) + FVector(60.f, 0.f, 0.f));
    if (!W.Tick(1) || !W.Hold(EKeys::E, 80))
        return false;
    const FString CutId = Fieldcraft->Active()->Nets.Quarry[Cut].Id;
    TestTrue(TEXT("Interact held a second cuts the net and frees the planter"),
        Fieldcraft->NetOf(Cut) != SoraFieldcraftRules::ENet::Netted && W.Raised(TEXT("npc_freed:") + CutId));
    bool bLeftBe = true;
    for (int32 Frame = 0; Frame < 32; ++Frame)
    {
        if (!W.Tick(1, .25f)) return false;
        bLeftBe &= Fieldcraft->NetOf(Cut) == SoraFieldcraftRules::ENet::Free;
    }
    TestTrue(TEXT("The planter cut free is let be while the drone reloads"), bLeftBe);
    // The other two are hauled off at 12 s: two lost, and the planting goes on.
    for (int32 Frame = 0; Frame < 80 && SoraBeatRules::TargetsLost(Campaign->TaskProgress(), Campaign->ActiveTask()) < 2; ++Frame)
        if (!W.Tick(1, .25f)) return false;
    TestEqual(TEXT("Two planters left in their nets are hauled away"), SoraBeatRules::TargetsLost(Campaign->TaskProgress(), Campaign->ActiveTask()), 2);
    TestFalse(TEXT("Two losses do not fail the defence"), W.Mode()->bDefeated);
    // The drones take the next; left netted, the third loss fails it.
    for (int32 Frame = 0; Frame < 160 && !W.Mode()->bDefeated; ++Frame)
        if (!W.Tick(1, .25f)) return false;
    TestTrue(TEXT("The third planter hauled away fails the defence to its checkpoint"),
        W.Mode()->bDefeated && SoraBeatRules::TargetsLost(Campaign->TaskProgress(), Campaign->ActiveTask()) == 3);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftCartTest,
    "SoraArena.Fieldcraft.CartNet",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftCartTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch04.b10: the ox cart, netted by a drone of the second wave; 600 health.
    FBeatWorld W(*this, TEXT("FieldcraftCart"), 3, 9);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    USoraCampaignDirector* Campaign = W.Campaign();
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
    if (!TestTrue(TEXT("The ox cart is the nets' quarry, with 600 health"), Fieldcraft->QuarryCount() == 1 && Fieldcraft->QuarryHealth(0) == 600))
        return false;
    const auto Walk = [&](int32 Quarters)
    {
        const int32 Before = Campaign->TaskProgress().Progress;
        for (int32 Frame = 0; Frame < Quarters; ++Frame)
        {
            W.Stand(Campaign->PartyLocation() + FVector(0.f, 200.f, 0.f));
            if (!W.Tick(1, .25f)) return -1;
        }
        return Campaign->TaskProgress().Progress - Before;
    };
    TestTrue(TEXT("The cart and carpenters walk with the hero beside them"), Walk(8) > 0);
    // A drone of the net wave comes for the ox.
    ASoraEnemy* Drone = ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(), TEXT("drone"), 0,
        Campaign->PartyLocation() + FVector(600.f, 600.f, 450.f), FRotator::ZeroRotator);
    if (!TestNotNull(TEXT("A drone comes"), Drone))
        return false;
    Fieldcraft->OpponentJoined(*Drone, Fieldcraft->Active()->Nets.NetWaves[0]);
    for (int32 Frame = 0; Frame < 120 && Fieldcraft->NetOf(0) != SoraFieldcraftRules::ENet::Netted; ++Frame)
    {
        W.Stand(Campaign->PartyLocation() + FVector(0.f, 200.f, 0.f));
        if (!W.Tick(1, .25f)) return false;
    }
    if (!TestTrue(TEXT("It nets the ox"), Fieldcraft->NetOf(0) == SoraFieldcraftRules::ENet::Netted && W.Raised(TEXT("ai:cart_netted"))))
        return false;
    TestEqual(TEXT("A netted ox stops the cart"), Walk(8), 0);
    W.Stand(Fieldcraft->QuarryLocation(0) + FVector(0.f, 150.f, 0.f));
    if (!W.Tick(1) || !W.Hold(EKeys::E, 80))
        return false;
    TestTrue(TEXT("Interact held a second cuts the ox free"), Fieldcraft->NetOf(0) != SoraFieldcraftRules::ENet::Netted);
    // Its drone, still up, reloads, and the cart walks on meanwhile.
    TestTrue(TEXT("The drone whose net was cut reloads"), IsValid(Drone) && Drone->IsAlive() && Fieldcraft->IsRearming(*Drone));
    const int32 Walked = Walk(32);
    TestTrue(TEXT("and for its reload the cart walks on"), Walked > 0 && Fieldcraft->NetOf(0) == SoraFieldcraftRules::ENet::Free);
    // Reloaded, it comes for the ox again; brought down, its net falls slack.
    for (int32 Frame = 0; Frame < 60 && Fieldcraft->NetOf(0) != SoraFieldcraftRules::ENet::Netted; ++Frame)
    {
        W.Stand(Campaign->PartyLocation() + FVector(0.f, 200.f, 0.f));
        if (!W.Tick(1, .25f)) return false;
    }
    TestTrue(TEXT("Reloaded, the drone nets the ox again"), Fieldcraft->NetOf(0) == SoraFieldcraftRules::ENet::Netted);
    UGameplayStatics::ApplyDamage(Drone, Drone->Health + 10.f, W.Hero()->GetController(), W.Hero(), UDamageType::StaticClass());
    TestTrue(TEXT("Shot down, its net falls slack and the cart walks on"), Walk(8) > 0);
    // Opponents standing at the cart wear it down; at nothing it is lost.
    // Step beyond the escort's wait range so the cart stays with these
    // stationary attackers instead of walking out of their siege radius.
    const FSoraZone& EscortRoad = Road(W);
    const float CartChainage = EscortRoad.ChainageOf(FVector2D(Campaign->PartyLocation()));
    W.Stand(Floor(EscortRoad.PointAlong(CartChainage + Campaign->ActiveTask().WaitCm + 500.f)));
    if (!W.Tick(1))
        return false;
    const int32 SiegeProgress = Campaign->TaskProgress().Progress;
    for (int32 Index = 0; Index < 6; ++Index)
        HoldStill(ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(), TEXT("enforcer_rifle"), Index + 1,
            Campaign->PartyLocation() + FVector(-150.f + Index * 60.f, -250.f, 120.f), FRotator::ZeroRotator));
    if (!W.Tick(8, .25f))
        return false;
    TestTrue(TEXT("Opponents at the cart wear it down"), Fieldcraft->QuarryHealth(0) < 600);
    for (int32 Frame = 0; Frame < 100 && !W.Mode()->bDefeated; ++Frame)
        if (!W.Tick(1, .25f)) return false;
    TestEqual(TEXT("With the hero beyond its wait range, the besieged cart stays put"), Campaign->TaskProgress().Progress, SiegeProgress);
    TestTrue(TEXT("The cart worn to nothing fails the escort"), W.Raised(TEXT("convoy_member_hp0")) && W.Mode()->bDefeated);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftSearchlightTest,
    "SoraArena.Fieldcraft.Searchlights",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftSearchlightTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    {
        // ch06.b02: two lights on the keep wall sweeping the moat.
        FBeatWorld W(*this, TEXT("FieldcraftSearchlights"), 5, 1);
        if (!W.Start())
            return false;
        W.Harden();
        USoraFieldcraft* Fieldcraft = W.Fieldcraft();
        // The parapet's own eyes held shut: only the light may find him here.
        for (ASoraEnemy* Guard : Guards(W)) HoldStill(Guard);
        if (!TestTrue(TEXT("The moat's two searchlights shine"), Fieldcraft->LightCount() == 2 && Fieldcraft->IsLightOn(0) && Fieldcraft->IsLightOn(1)))
            return false;
        const FVector First = Fieldcraft->SpotOf(0);
        if (!W.Tick(10, .25f))
            return false;
        TestTrue(TEXT("Its spot sweeps across the water"), FVector::Dist2D(First, Fieldcraft->SpotOf(0)) > 400.f);
        const auto Follow = [&](int32 Frames)
        {
            for (int32 Frame = 0; Frame < Frames; ++Frame)
            {
                W.Stand(Fieldcraft->SpotOf(0));
                if (!W.Tick(1)) return false;
            }
            return true;
        };
        // Under the water the light finds nothing.
        W.Stand(Fieldcraft->SpotOf(0));
        if (!W.Tick(2) || !W.Press(EKeys::C) || !Follow(90))
            return false;
        TestTrue(TEXT("A diver in the spot is not seen"), Fieldcraft->IsDiving() && !W.Raised(TEXT("ai_event:searchlight_suspicious")));
        // Surface, then start observing the detection immediately. Waiting
        // five seconds here can trigger the alarm at the sweep's turnaround
        // before Follow starts, and exhaust its six-second lock before the
        // later assertion.
        if (!W.Press(EKeys::C)) return false;
        // This legacy lamp-isolation test keeps its moving spot target, but
        // waits for actual swept ascent rather than granting air on the wish.
        for(int32 F=0;F<240&&Fieldcraft->IsDiving();++F)if(!Follow(1))return false;
        TestFalse(TEXT("The hero has physically surfaced before measuring light exposure"), Fieldcraft->IsDiving());
        // A head in the spot: half a second makes the guards look, a second and a half raises the alarm.
        if (!Follow(40))
            return false;
        TestTrue(TEXT("Half a second in the light makes the guards look"), W.Raised(TEXT("ai_event:searchlight_suspicious")));
        TestFalse(TEXT("Half a second has not yet raised the searchlight alarm"), W.Raised(TEXT("ai_event:searchlight_alert")));
        for (int32 Frame = 0; Frame < 70 && !W.Stealth()->IsDetected(); ++Frame)
            if (!Follow(1)) return false;
        TestTrue(TEXT("A second and a half raises the alarm"), W.Raised(TEXT("ai_event:searchlight_alert")) && W.Stealth()->IsDetected());
        if (!W.Tick(2))
            return false;
        // The alarm releases fresh riflemen. Keep their eyes shut too so
        // this assertion measures the light's lock rather than a later
        // detection by the reinforcements.
        for (ASoraEnemy* Guard : Guards(W)) HoldStill(Guard);
        const FVector Seen = W.Hero()->GetActorLocation();
        W.Stand(Seen + FVector(0.f, -1500.f, 0.f));
        // A later guard's alarm bark has no new visual evidence. It must not
        // redirect either beam to the unseen hero's current position.
        Fieldcraft->NoteBeatEvent(TEXT("alert_state:alert"));
        if (!W.Tick(8, .25f))
            return false;
        AddInfo(FString::Printf(TEXT("Searchlight lock: seen=%s hero=%s light0=%s light1=%s"),
            *Seen.ToString(), *W.Hero()->GetActorLocation().ToString(), *Fieldcraft->SpotOf(0).ToString(), *Fieldcraft->SpotOf(1).ToString()));
        TestTrue(TEXT("The lights lock on the last place he was seen"), FVector::Dist2D(Fieldcraft->SpotOf(0), Seen) < 250.f &&
            FVector::Dist2D(Fieldcraft->SpotOf(1), Seen) < 250.f);
        // Surfaced under the lotus leaves, a head shows to no light: locked on
        // him there, the spot finds nothing; in the open water beside the
        // leaves it finds him at once.
        const FSoraWater& Moat = W.Craft().Water;
        if (!TestTrue(TEXT("The moat has lotus beds"), !Moat.Cover.IsEmpty()))
            return false;
        const FSoraVolume& Lotus = Moat.Cover[0];
        const auto Lit = [&](const FVector& Where)
        {
            W.Stand(Where);
            if (!W.Tick(2)) return false;
            Fieldcraft->LockSearchlights(Where);
            return W.Tick(20);
        };
        if (!Lit(Floor(Lotus.Center)))
            return false;
        AddInfo(FString::Printf(TEXT("Lotus visibility: hero=%s lotus=%s swimming=%d diving=%d light=%d exposure=%.3f"),
            *W.Hero()->GetActorLocation().ToString(), *Lotus.Center.ToString(), Fieldcraft->IsSwimming(), Fieldcraft->IsDiving(),
            Fieldcraft->Readout(*W.Hero()).bInLight, Fieldcraft->Readout(*W.Hero()).LightExposure));
        TestTrue(TEXT("Under the lotus the searchlight finds no head"), Fieldcraft->IsSwimming() && !Fieldcraft->IsDiving() &&
            !Fieldcraft->Readout(*W.Hero()).bInLight);
        FVector Open = FVector::ZeroVector;
        for (const float Side : FBeatWorld::Sides)
        {
            const FVector Candidate = Floor(Lotus.Center) + FRotator(0.f, Side, 0.f).Vector() * (Lotus.Size.GetMax() * .5f + 250.f);
            if (Moat.Area.Contains(Candidate) && !Moat.Cover.ContainsByPredicate([&](const FSoraVolume& Leaves) { return Leaves.Contains(Candidate); }))
            {
                Open = Candidate;
                break;
            }
        }
        if (!TestFalse(TEXT("Open water lies beside the lotus"), Open.IsZero()) || !Lit(Open))
            return false;
        TestTrue(TEXT("In the open water beside it the light finds him"), Fieldcraft->Readout(*W.Hero()).bInLight);
    }
    {
        // ch02.b08: the ship's light on the road frightens the horses it comes near.
        FBeatWorld W(*this, TEXT("FieldcraftShipLight"), 1, 7);
        if (!W.Start())
            return false;
        W.Harden();
        USoraFieldcraft* Fieldcraft = W.Fieldcraft();
        USoraCampaignDirector* Campaign = W.Campaign();
        const FSoraZone& Kaido = Road(W);
        if (!TestTrue(TEXT("The ship's light waits for its wave"), Fieldcraft->LightCount() == 1 && !Fieldcraft->IsLightOn(0)))
            return false;
        const float At = Kaido.RouteLength * .56f;
        Campaign->Steed()->Place(Floor(Kaido.PointAlong(At)), Kaido.HeadingAt(At));
        for (int32 Frame = 0; Frame < 8 && !Fieldcraft->IsLightOn(0); ++Frame)
            if (!W.Tick(1)) return false;
        if (!TestTrue(TEXT("With the third wave the ship's light comes on"), Fieldcraft->IsLightOn(0)))
            return false;
        for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
        const FVector Spot = Fieldcraft->SpotOf(0);
        const float Chainage = Kaido.ChainageOf(FVector2D(Spot));
        TestTrue(TEXT("It sweeps its stretch of the road"), Chainage >= 64000.f - 50.f && Chainage <= 80000.f + 50.f);
        Campaign->Steed()->Place(FVector(Spot.X, Spot.Y, 0.f), Kaido.HeadingAt(Chainage));
        Campaign->PackHorses()[0]->FollowRoad(&Kaido, Chainage + 300.f, 450);
        if (!W.Tick(2))
            return false;
        TestTrue(TEXT("Kurimaru shies in the light"), Campaign->Steed()->IsSpooked() && W.Raised(TEXT("ai:horse_spooked:kurimaru")));
        TestTrue(TEXT("and the string halts"), W.Raised(TEXT("ai:horse_spooked:convoy")) && Fieldcraft->QuarryHalted());
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftBellTest,
    "SoraArena.Fieldcraft.Bell",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftBellTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch07.b04: the village bell on its gantry hook, one stone, 25 m, 12 s.
    FBeatWorld W(*this, TEXT("FieldcraftBell"), 6, 3);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    const FVector Bell = Fieldcraft->BellLocation();
    // The hero out of every guard's sight, behind the entry.
    W.Stand(Floor(W.BeatData().Space.Entry));
    if (!W.Tick(2))
        return false;
    TArray<ASoraEnemy*> Near;
    for (ASoraEnemy* Guard : Guards(W))
    {
        const auto* Brain = Cast<ASoraEnemyController>(Guard->GetController());
        const bool bCalm = Brain && (Brain->State() == SoraStealthRules::EState::Unaware || Brain->State() == SoraStealthRules::EState::Suspicious);
        if (bCalm && FVector::Dist2D(Guard->GetActorLocation(), Bell) <= W.Craft().Bell.Rules.RadiusCm) Near.Add(Guard);
    }
    if (!TestTrue(TEXT("Guards patrol within the bell's reach"), !Near.IsEmpty() && !Fieldcraft->BellRung()))
        return false;
    TArray<float> Before;
    for (const ASoraEnemy* Guard : Near) Before.Add(FVector::Dist2D(Guard->GetActorLocation(), Bell));
    // A stone that strikes the bell rings it.
    Fieldcraft->StoneLanded(Bell + FVector(40.f, 0.f, 0.f), W.Craft().Stones.NoiseCm);
    TestTrue(TEXT("A stone on the bell rings it once"), Fieldcraft->BellRung() && W.Raised(TEXT("lure_triggered:bell_bonsho")));
    int32 Drawn = 0;
    for (const ASoraEnemy* Guard : Near)
        if (const auto* Brain = Cast<ASoraEnemyController>(Guard->GetController()); Brain && Brain->HasErrand()) ++Drawn;
    TestEqual(TEXT("Every unaware guard in earshot goes to it"), Drawn, Near.Num());
    if (!W.Tick(24, .25f))
        return false;
    int32 Closer = 0;
    for (int32 Index = 0; Index < Near.Num(); ++Index)
        Closer += FVector::Dist2D(Near[Index]->GetActorLocation(), Bell) < FMath::Max(300.f, Before[Index] - 100.f);
    TestTrue(TEXT("and walks over to look it over"), Closer > 0);
    Fieldcraft->StoneLanded(Bell, W.Craft().Stones.NoiseCm);
    TestEqual(TEXT("It rings only once"), W.Count(TEXT("lure_triggered:bell_bonsho")), 1);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftCookFiresTest,
    "SoraArena.Fieldcraft.CookFires",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftCookFiresTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch03.b14: three 竈 in the tenement court; one gutters at 25 %.
    FBeatWorld W(*this, TEXT("FieldcraftCookFires"), 2, 13);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    USoraCampaignDirector* Campaign = W.Campaign();
    const FVector Anchor = Floor(W.BeatData().Space.Anchor);
    if (!TestTrue(TEXT("Three cook-fires burn"), W.Craft().bFires && W.Craft().Fires.Points.Num() == 3 && Fieldcraft->FiresOut() == 0))
        return false;
    for (int32 Frame = 0; Frame < 200 && !W.Raised(TEXT("fire_out")); ++Frame)
    {
        W.Stand(Anchor);
        for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
        if (!W.Tick(1, .25f)) return false;
    }
    if (!TestTrue(TEXT("At a quarter of the hold a cook-fire gutters"), W.Raised(TEXT("fire_out")) && Fieldcraft->FiresOut() == 1))
        return false;
    TestTrue(TEXT("and its prompt shows"), W.PromptOn(TEXT("fire_out:first")));
    const int32 Held = Campaign->TaskProgress().Progress;
    if (!W.Tick(12, .25f))
        return false;
    TestEqual(TEXT("The kitchen waits while the fire is out"), Campaign->TaskProgress().Progress, Held);
    FVector Fire;
    TestTrue(TEXT("The guttered fire is the objective, worked with Interact"), Campaign->ObjectiveAnchor(Fire) && Campaign->AnchorTakesInteract() &&
        FVector::Dist2D(Fire, Fieldcraft->FireLocation(0)) < 1.f);
    W.Stand(Fire + FVector(60.f, 0.f, 0.f));
    if (!W.Tick(1) || !W.Hold(EKeys::E, 140))
        return false;
    TestTrue(TEXT("Interact held two seconds relights it"), Fieldcraft->FiresOut() == 0 && W.Raised(TEXT("fire_lit:") + W.Craft().Fires.Ids[0]));
    W.Stand(Anchor);
    if (!W.Tick(12, .25f))
        return false;
    TestTrue(TEXT("and the kitchen goes on"), Campaign->TaskProgress().Progress > Held);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftLaddersTest,
    "SoraArena.Fieldcraft.Ladders",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftLaddersTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    {
        // ch03.b03: the roofer's ladder, the board roof, and the drop onto the straw.
        FBeatWorld W(*this, TEXT("FieldcraftLadders"), 2, 2);
        if (!W.Start())
            return false;
        W.Harden();
        USoraFieldcraft* Fieldcraft = W.Fieldcraft();
        for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
        if (!TestEqual(TEXT("The shop has its ladder"), W.Craft().Ladders.Num(), 1))
            return false;
        const FSoraLadder& Ladder = W.Craft().Ladders[0];
        W.Stand(Floor(Ladder.Foot), Ladder.Yaw);
        if (!W.Tick(2))
            return false;
        TestTrue(TEXT("At its foot the ladder is offered"), Fieldcraft->Readout(*W.Hero()).bAtLadder);
        if (!W.Press(EKeys::SpaceBar) || !TestTrue(TEXT("Jump at its foot takes the ladder"), Fieldcraft->IsOnLadder()))
            return false;
        for (int32 Frame = 0; Frame < 240 && Fieldcraft->IsOnLadder(); ++Frame)
            if (!W.Tick(1)) return false;
        if (!W.Tick(10))
            return false;
        TestTrue(TEXT("and he steps off onto the roof"), Fieldcraft->IsOnRoof(W.Hero()->GetActorLocation()) && W.Raised(TEXT("roof_reached:") + Ladder.Id));
        // Off the far edge onto the straw: quiet.
        const float Half = W.Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        if (!TestTrue(TEXT("The shop has its straw"), Ladder.bStraw))
            return false;
        // The straw's far half crosses this beat's exit (its centre is only
        // 5 cm inside it). Land on the near half so the real exit transition
        // does not remove this ladder before its landing checks run.
        const FVector2D StrawLanding = Ladder.Straw.Center + (Ladder.Roof.Center - Ladder.Straw.Center).GetSafeNormal() *
            (Ladder.Straw.Size.GetMin() * .25f);
        if (!TestTrue(TEXT("The landing remains on straw"), Ladder.Straw.Contains(Floor(StrawLanding))) ||
            !TestFalse(TEXT("The straw landing stays outside the beat exit"), W.BeatData().Space.Exit.Contains(Floor(StrawLanding))))
            return false;
        W.Hero()->SetActorLocation(FVector(StrawLanding, Ladder.HeightCm + Half + 20.f), false, nullptr, ETeleportType::TeleportPhysics);
        W.Hero()->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
        // A fall starts from the roof: he was up there.
        if (!W.Tick(1))
            return false;
        for (int32 Frame = 0; Frame < 120 && !W.Hero()->GetCharacterMovement()->IsMovingOnGround(); ++Frame)
            if (!W.Tick(1)) return false;
        if (!W.Tick(2))
            return false;
        AddInfo(FString::Printf(TEXT("Landed at %s"), *W.Hero()->GetActorLocation().ToString()));
        if (!TestEqual(TEXT("Landing on the near straw keeps the ladder's beat active"), W.Campaign()->ActiveBeat(), W.Beat))
            return false;
        // Back up, and off where there is no straw, with a guard close by: he hears it.
        W.Stand(Floor(Ladder.Foot), Ladder.Yaw);
        if (!W.Tick(2) || !W.Press(EKeys::SpaceBar))
            return false;
        for (int32 Frame = 0; Frame < 240 && Fieldcraft->IsOnLadder(); ++Frame)
            if (!W.Tick(1)) return false;
        const FVector Edge = FVector(Ladder.Roof.Center + FVector2D(0.f, -Ladder.Roof.Size.Y * .5f - 80.f), 0.f);
        // A guard below, looking away: he can only hear it.
        FSoraPatrolRoute Post;
        Post.Points.Add(Edge + FVector(-500.f, -300.f, 90.f));
        ASoraEnemy* Guard = ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(), TEXT("enforcer_rifle"), 9, Post.Points[0],
            FRotator(0.f, FVector(-500.f, -300.f, 0.f).Rotation().Yaw, 0.f), &Post);
        if (!TestNotNull(TEXT("A guard stands below the roof"), Guard) || !W.Tick(2))
            return false;
        const auto* Brain = Cast<ASoraEnemyController>(Guard->GetController());
        const int32 Calm = Brain ? Brain->AwarenessPermille() : 0;
        const auto Drop = [&]()
        {
            W.Hero()->SetActorLocation(FVector(Edge.X, Edge.Y, Ladder.HeightCm + Half + 20.f), false, nullptr, ETeleportType::TeleportPhysics);
            W.Hero()->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
            if (!W.Tick(1))
                return false;
            for (int32 Frame = 0; Frame < 120 && !W.Hero()->GetCharacterMovement()->IsMovingOnGround(); ++Frame)
                if (!W.Tick(1)) return false;
            return W.Tick(3);
        };
        // A roof whose script says its drop carries only 4.5 m: the guard,
        // about 6 m off, hears nothing. The catalog row is put back after.
        FSoraLadder& Authored = const_cast<FSoraLadder&>(Ladder);
        const int32 Scripted = Authored.DropNoiseCm;
        {
            ON_SCOPE_EXIT { Authored.DropNoiseCm = Scripted; };
            Authored.DropNoiseCm = 450;
            if (!Drop())
                return false;
            TestTrue(TEXT("A drop is heard no farther than its roof's script says"), W.Count(TEXT("roof_drop")) == 1 && Brain &&
                Brain->AwarenessPermille() <= Calm && Brain->State() == SoraStealthRules::EState::Unaware);
        }
        W.Stand(Floor(Ladder.Foot), Ladder.Yaw);
        if (!W.Tick(2) || !W.Press(EKeys::SpaceBar))
            return false;
        for (int32 Frame = 0; Frame < 240 && Fieldcraft->IsOnLadder(); ++Frame)
            if (!W.Tick(1)) return false;
        if (!Drop())
            return false;
        TestTrue(TEXT("The straw takes a drop quietly"), W.Raised(TEXT("roof_drop:straw")));
        AddInfo(FString::Printf(TEXT("Roof landing: drops=%d hero=%s guard=%s awareness=%d calm=%d state=%d"),
            W.Count(TEXT("roof_drop")), *W.Hero()->GetActorLocation().ToString(), *Guard->GetActorLocation().ToString(),
            Brain ? Brain->AwarenessPermille() : -1, Calm, Brain ? static_cast<int32>(Brain->State()) : -1));
        TestTrue(TEXT("A drop off the roof onto the ground, as far as its script says (9 m), is heard"), W.Count(TEXT("roof_drop")) == 2 && Brain &&
            (Brain->AwarenessPermille() > Calm || Brain->State() != SoraStealthRules::EState::Unaware));
        // Struck down half way up the ladder and retried: he comes back
        // standing on the ground, not held in the air by a ladder he left.
        Guard->Destroy();
        W.Stand(Floor(Ladder.Foot), Ladder.Yaw);
        if (!W.Tick(2) || !W.Press(EKeys::SpaceBar) || !W.Tick(30) || !TestTrue(TEXT("He climbs the ladder again"), Fieldcraft->IsOnLadder()))
            return false;
        FBeatWorld::Hurt(*W.Hero(), W.Hero()->Health + 1000.f);
        for (int32 Frame = 0; Frame < 30 && !W.Mode()->bDefeated; ++Frame)
            if (!W.Tick(1)) return false;
        if (!TestTrue(TEXT("Struck down on the ladder, the beat fails to its checkpoint"), W.Mode()->bDefeated))
            return false;
        // Enter on the defeat screen, as the playthrough retries.
        W.Mode()->BeginRound();
        UCharacterMovementComponent* Movement = W.Hero()->GetCharacterMovement();
        for (int32 Frame = 0; Frame < 120 && !Movement->IsMovingOnGround(); ++Frame)
            if (!W.Tick(1)) return false;
        TestTrue(TEXT("Retried, he is off the ladder and on his feet"), !W.Mode()->bDefeated && !Fieldcraft->IsOnLadder() &&
            Movement->MovementMode != MOVE_Flying && Movement->IsMovingOnGround());
    }
    {
        // ch03.b10: the marksman keeps his post on the actual kawara ridge.
        FBeatWorld W(*this, TEXT("FieldcraftRoofMarksman"), 2, 9);
        if (!W.Start())
            return false;
        const TArray<ASoraEnemy*> Posted = Guards(W);
        const FSoraLadder& Ladder = W.Craft().Ladders[1];
        TestTrue(TEXT("The marksman stands on the roof"), !Posted.IsEmpty() && Posted[0]->ArchetypeId() == TEXT("marksman") &&
            Posted[0]->GetActorLocation().Z > Ladder.HeightCm && Ladder.Roof.Contains(Posted[0]->GetActorLocation()));
        // His glint, as the scripts key it, shows the glint prompt.
        FSoraEnemyCueEvent Cue;
        Cue.Enemy = Posted[0]; Cue.Archetype = TEXT("marksman"); Cue.Cue = ESoraEnemyCue::AttackWindup; Cue.Detail = TEXT("marksman_lock");
        USoraGameEvents::Get(W.Hero())->OnEnemyCue.Broadcast(Cue);
        TestTrue(TEXT("A marksman's lock is pattern:marksman_lock"), W.PromptOn(TEXT("pattern:marksman_lock:first")));
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftHoistTest,
    "SoraArena.Fieldcraft.GuardedHoist",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftHoistTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch03.b05: each crate hoisted on the well's 釣瓶 (3 s), waiting while a guard watches.
    FBeatWorld W(*this, TEXT("FieldcraftHoist"), 2, 4);
    if (!W.Start())
        return false;
    W.Harden();
    USoraCampaignDirector* Campaign = W.Campaign();
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
    if(!TestTrue(TEXT("The well's equipment pre-step must precede hoisting"),Campaign->NeedsEquipmentRecovery())||
        !TestTrue(TEXT("Recover equipment through the rope and held input"),SoraRecoveryAutomation::Recover(*W.World))) return false;
    const FVector Well = Floor(W.BeatData().Space.Pickups[0]);
    W.Stand(Well);
    if (!W.Tick(2) || !W.Press(EKeys::E))
        return false;
    TestFalse(TEXT("A press alone lifts nothing"), Campaign->TaskProgress().Carrying);
    if (!W.Hold(EKeys::E, 200))
        return false;
    TestTrue(TEXT("Interact held three seconds hoists a crate"), Campaign->TaskProgress().Carrying);
    // Delivered, and back for the next with a guard looking on.
    W.Stand(Floor(W.BeatData().Space.Dropoffs[0]));
    if (!W.Tick(2) || !W.Press(EKeys::E) || !W.Tick(2))
        return false;
    if (!TestTrue(TEXT("The first crate is delivered"), Campaign->TaskProgress().Done == 1 && !Campaign->TaskProgress().Carrying))
        return false;
    W.Stand(Well, 0.f);
    FSoraPatrolRoute Post;
    Post.Points.Add(Well + FVector(400.f, 0.f, 90.f));
    ASoraEnemy* Guard = ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(), TEXT("enforcer_rifle"), 9, Post.Points[0],
        FRotator(0.f, 180.f, 0.f), &Post);
    if (!TestNotNull(TEXT("A guard watches the well"), Guard) || !W.Tick(2))
        return false;
    if (!W.World->InjectKey(EKeys::E, IE_Pressed) || !W.Tick(80))
        return false;
    const bool bWatched = W.Stealth()->IsWorkPaused();
    TestTrue(TEXT("Seen, the hoist waits and says so"), bWatched && Campaign->IsHeldWorkWatched() && !Campaign->TaskProgress().Carrying &&
        Campaign->HeldWorkProgress() < .05f);
    Guard->Destroy();
    if (!W.Tick(240) || !W.World->InjectKey(EKeys::E, IE_Released) || !W.Tick(1))
        return false;
    TestTrue(TEXT("Unseen, it goes on and the crate comes up"), Campaign->TaskProgress().Carrying);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftVolleySmokeTest,
    "SoraArena.Fieldcraft.VolleySmokeAndAutoOrder",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftVolleySmokeTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch08.b03: each volley leaves a 4 s smoke bank; on Easy the ranks may order themselves.
    FBeatWorld W(*this, TEXT("FieldcraftVolleySmoke"), 7, 2);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    for (const TObjectPtr<ASoraCompanion>& Ally : Fieldcraft->AlliesInPlay())
        if (Ally->VolleyRank() == INDEX_NONE) Ally->SetActorTickEnabled(false);
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
    const FVector Center = Floor(W.BeatData().Space.Spawns[0]);
    ASoraEnemy* Rifleman = ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(), TEXT("enforcer_rifle"), 0, Center + FVector(0.f, 0.f, 120.f),
        FRotator::ZeroRotator);
    HoldStill(Rifleman);
    if (!TestNotNull(TEXT("An opponent stands in the ring"), Rifleman) || !W.ClearView(Center, 900.f) || !W.Hold(EKeys::Q, 8) || !W.Tick(60))
        return false;
    if (!TestTrue(TEXT("The volley fires and leaves its smoke bank"), Fieldcraft->VolleysFired() == 1 && Fieldcraft->SmokeBanks() == 1))
        return false;
    // It hides the lane from sight for both sides, and stops no round, arrow
    // or blade: a line through it reaches the rifleman in it.
    const FVector Across = Center + FVector(0.f, 0.f, 150.f);
    TestTrue(TEXT("The smoke hides the lane from sight"), Fieldcraft->SmokeBetween(Across + FVector(-600.f, 0.f, 0.f), Across + FVector(600.f, 0.f, 0.f)));
    TestFalse(TEXT("but not the sky above it"), Fieldcraft->SmokeBetween(Across + FVector(-600.f, 0.f, 400.f), Across + FVector(600.f, 0.f, 400.f)));
    // A fresh opponent in the bank: the hero, 9 m off, finds a clear shot at
    // it through the smoke (nothing but the bank between them), and it,
    // turned to him, does not see him.
    ASoraEnemy* Inside = ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(), TEXT("enforcer_rifle"), 2, Center + FVector(0.f, 0.f, 120.f),
        FRotator::ZeroRotator);
    HoldStill(Inside);
    if (!TestNotNull(TEXT("An opponent stands in the smoke"), Inside) || !W.Tick(1))
        return false;
    if (!TestTrue(TEXT("A shot into the smoke reaches the opponent in it"), W.ClearShot(*Inside, 900.f)))
        return false;
    Inside->SetActorRotation(FRotator(0.f, (W.Hero()->GetActorLocation() - Inside->GetActorLocation()).Rotation().Yaw, 0.f));
    const auto* Brain = Cast<ASoraEnemyController>(Inside->GetController());
    TestTrue(TEXT("The opponent in the smoke does not see the hero outside it"), Fieldcraft->SmokeBanks() == 1 && Brain &&
        !Brain->CanSee(*W.Hero()));
    if (!W.Tick(18, .25f))
        return false;
    TestEqual(TEXT("and clears after four seconds"), Fieldcraft->SmokeBanks(), 0);
    TestTrue(TEXT("Cleared, it sees him again"), Brain && Brain->CanSee(*W.Hero()));
    Inside->Destroy();
    // On Normal the ranks wait for the hero's order.
    TestFalse(TEXT("On Normal the ranks never order themselves"), Fieldcraft->AutoOrdering());
    const int32 Orders = Fieldcraft->VolleysOrdered();
    ASoraEnemy* Next = ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(), TEXT("enforcer_rifle"), 1, Center + FVector(200.f, 0.f, 120.f),
        FRotator::ZeroRotator);
    HoldStill(Next);
    if (!W.Tick(8, .25f))
        return false;
    TestEqual(TEXT("No order comes without the hero"), Fieldcraft->VolleysOrdered(), Orders);
    // On Easy, with the setting on, the loaded rank fires on the nearest opponent.
    W.Mode()->Settings()->SetCampaignDifficulty(SoraAccessibility::EDifficulty::Easy);
    W.Mode()->Settings()->SetVolleyAutoOrder(true);
    W.Stand(Center + FVector(-1500.f, 0.f, 0.f));
    for (int32 Frame = 0; Frame < 60 && Fieldcraft->VolleysOrdered() == Orders; ++Frame)
        if (!W.Tick(1, .25f)) return false;
    TestTrue(TEXT("On Easy the loaded rank orders itself on the nearest opponent"), Fieldcraft->AutoOrdering() &&
        Fieldcraft->VolleysOrdered() > Orders && W.Raised(TEXT("event:volley_auto_order")));
    W.Mode()->Settings()->SetVolleyAutoOrder(false);
    const int32 Easy = Fieldcraft->VolleysOrdered();
    if (!W.Tick(48, .25f))
        return false;
    TestTrue(TEXT("With the setting off it waits again"), !Fieldcraft->AutoOrdering() && Fieldcraft->VolleysOrdered() == Easy);
    W.Mode()->Settings()->SetCampaignDifficulty(SoraAccessibility::EDifficulty::Normal);
    W.Mode()->Settings()->SetVolleyAutoOrder(true);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFieldcraftChargeTest,
    "SoraArena.Fieldcraft.Charge",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFieldcraftChargeTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // ch08.b02: twenty League riders and Toranosuke on Arashi, and three seal stakes.
    FBeatWorld W(*this, TEXT("FieldcraftCharge"), 7, 1);
    if (!W.Start())
        return false;
    W.Harden();
    USoraFieldcraft* Fieldcraft = W.Fieldcraft();
    USoraCampaignDirector* Campaign = W.Campaign();
    const FSoraZone& Causeway = Road(W);
    for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
    const TArray<TObjectPtr<ASoraHorse>>& Riders = Fieldcraft->ChargeRiders();
    if (!TestEqual(TEXT("Twenty riders and the rival ride out"), Riders.Num(), 21))
        return false;
    TestEqual(TEXT("The rival rides first: Toranosuke on Arashi"), Riders[0]->PackId, FString(TEXT("toranosuke")));
    // Riding on with the pack: the rival keeps his right.
    ASoraHorse* Kurimaru = Campaign->Steed();
    if (!W.World->InjectKey(EKeys::W, IE_Pressed) || !W.World->InjectKey(EKeys::LeftShift, IE_Pressed))
        return false;
    const float LeadBefore = Fieldcraft->PackLead();
    if (!W.Tick(120))
        return false;
    const FVector2D Rival = Kurimaru->LocalOf(Riders[0]->GetActorLocation());
    TestTrue(TEXT("Toranosuke rides at Nyaakoto's right"), Rival.Y > 100.f && Rival.Y < 450.f && FMath::Abs(Rival.X) < 200.f);
    // Their rank is theirs alone: no League rider rides in either horse's body.
    int32 Overlaps = 0;
    for (int32 Index = 1; Index < Riders.Num(); ++Index)
        for (const ASoraHorse* Mount : {static_cast<const ASoraHorse*>(Kurimaru), static_cast<const ASoraHorse*>(Riders[0].Get())})
        {
            const FVector2D Local = Mount->LocalOf(Riders[Index]->GetActorLocation());
            Overlaps += FMath::Abs(Local.X) < 260.f && FMath::Abs(Local.Y) < 90.f;
        }
    TestEqual(TEXT("The League's riders leave the hero's rank to him and Toranosuke"), Overlaps, 0);
    TestTrue(TEXT("The pack runs the causeway"), Fieldcraft->PackLead() - LeadBefore > 800.f);
    if (!W.World->InjectKey(EKeys::W, IE_Released) || !W.World->InjectKey(EKeys::LeftShift, IE_Released))
        return false;
    // Halted, he falls behind his place: the pack eases off but never waits.
    const float Here = Causeway.ChainageOf(FVector2D(Kurimaru->GetActorLocation()));
    Kurimaru->Place(Floor(Causeway.PointAlong(Here)), Causeway.HeadingAt(Here));
    for (int32 Frame = 0; Frame < 120 && Fieldcraft->PackLead() - Here < 1350.f + 2.f * SoraFieldcraftRules::LagCm + 100.f; ++Frame)
    {
        Kurimaru->Place(Floor(Causeway.PointAlong(Here)), Causeway.HeadingAt(Here));
        if (!W.Tick(1, .25f)) return false;
    }
    const float Eased = Fieldcraft->PackLead();
    if (!W.Tick(4, .25f))
        return false;
    const float Moved = Fieldcraft->PackLead() - Eased;
    TestTrue(TEXT("The pack eases off for a hero fallen behind, never waiting"),
        Moved > 0.f && Moved < W.Craft().Charge.PaceCmS - W.Craft().Charge.CatchUpCmS * .5f);
    // The first stake bars the way until struck: a thrust at a walk does nothing.
    const FVector Stake = Fieldcraft->StakeLocation(0);
    const auto Strike = [&](int32 Index, const FSoraHit& Hit)
    {
        ASoraSealStake* Target = nullptr;
        for (TActorIterator<ASoraSealStake> It(W.World->GetTestWorld()); It; ++It)
            if (FVector::Dist2D(It->GetActorLocation(), Fieldcraft->StakeLocation(Index)) < 1.f) Target = *It;
        FHitResult Trace; Trace.ImpactPoint = Fieldcraft->StakeLocation(Index); Trace.Location = Trace.ImpactPoint;
        if (Target) SoraDamage::Strike(Target, 40.f, Hit, FVector::ForwardVector, Trace, W.Hero()->GetController(), W.Hero());
    };
    const float StakeAt = Causeway.ChainageOf(FVector2D(Stake));
    Kurimaru->Place(Floor(Causeway.PointAlong(StakeAt - 3000.f)), Causeway.HeadingAt(StakeAt - 3000.f));
    if (!W.Tick(2))
        return false;
    Strike(0, FSoraHit::Melee(W.Hero()->GetActorLocation(), 19));
    TestTrue(TEXT("A yari thrust at a halt leaves the stake standing"), Fieldcraft->IsStakeStanding(0));
    // Urged to a canter toward it, the thrust breaks it.
    if (!W.World->InjectKey(EKeys::W, IE_Pressed) || !W.World->InjectKey(EKeys::LeftShift, IE_Pressed))
        return false;
    for (int32 Frame = 0; Frame < 300 && SoraMountRules::Index(Kurimaru->Gait()) < SoraMountRules::Index(SoraMountRules::EGait::Canter); ++Frame)
        if (!W.Tick(1)) return false;
    Strike(0, FSoraHit::Melee(W.Hero()->GetActorLocation(), 19));
    W.World->InjectKey(EKeys::W, IE_Released);
    W.World->InjectKey(EKeys::LeftShift, IE_Released);
    TestTrue(TEXT("A yari thrust at a canter breaks the stake"), !Fieldcraft->IsStakeStanding(0) && W.Raised(TEXT("stake_broken:pylon_1")));
    // Two arrows break the second.
    Strike(1, FSoraHit::Ranged(W.Hero()->GetActorLocation(), 18));
    TestTrue(TEXT("One arrow does not break a stake"), Fieldcraft->IsStakeStanding(1));
    Strike(1, FSoraHit::Ranged(W.Hero()->GetActorLocation(), 18));
    TestFalse(TEXT("The second arrow does"), Fieldcraft->IsStakeStanding(1));
    // Left standing, the riders break the third eight seconds after it holds them.
    const float Third = Causeway.ChainageOf(FVector2D(Fieldcraft->StakeLocation(2)));
    Kurimaru->Place(Floor(Causeway.PointAlong(Third - 500.f)), Causeway.HeadingAt(Third - 500.f));
    if (!W.Tick(28, .25f))
        return false;
    TestTrue(TEXT("Not before eight seconds"), Fieldcraft->IsStakeStanding(2));
    if (!W.Tick(8, .25f))
        return false;
    TestTrue(TEXT("The riders behind break a stake left standing"), !Fieldcraft->IsStakeStanding(2) &&
        W.Raised(TEXT("stake_broken_by_riders:pylon_3")));
    // The riders strike what they pass on the causeway: Toranosuke beside the halted hero.
    ASoraEnemy* Barricade = ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(), TEXT("enforcer_rifle"), 0,
        Riders[0]->GetActorLocation() + FVector(0.f, 0.f, 30.f), FRotator::ZeroRotator);
    HoldStill(Barricade);
    const float Full = Barricade ? Barricade->Health : 0.f;
    if (!TestNotNull(TEXT("An enforcer stands among the riders"), Barricade) || !W.Tick(8, .25f))
        return false;
    TestTrue(TEXT("The riders strike opponents on the causeway"), Fieldcraft->RiderStrikes() > 0 && (!IsValid(Barricade) || Barricade->Health < Full));
    return true;
}
#endif
