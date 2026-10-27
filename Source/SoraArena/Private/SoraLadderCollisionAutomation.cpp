#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"

namespace SoraLadderTest
{
using SoraFieldcraftAutomation::FBeatWorld;
AActor* Block(FBeatWorld& W, const FVector& At, const FVector& Half)
{
    auto* Actor = W.World->GetTestWorld()->SpawnActor<AActor>();
    if (!Actor) return nullptr;
    auto* Box = NewObject<UBoxComponent>(Actor);
    Actor->SetRootComponent(Box); Actor->AddInstanceComponent(Box);
    Box->SetBoxExtent(Half); Box->SetCollisionProfileName(TEXT("BlockAll"));
    Box->RegisterComponent(); Actor->SetActorLocation(At);
    return Actor;
}
bool Controls(FBeatWorld& W)
{
    for (int I = 0; I < 3000 && !W.Mode()->IsPlaying(); ++I) if (!W.Tick(1)) return false;
    return W.Test.TestTrue(TEXT("The authored dialogue releases controls"), W.Mode()->IsPlaying());
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraLadderCollisionTest, "SoraArena.Fieldcraft.LadderCollision",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)
bool FSoraLadderCollisionTest::RunTest(const FString&)
{
    using namespace SoraLadderTest;
    if (!FSoraCatalog::Get().Load()) return false;
    for (int Beat : {2, 9})
    {
        FBeatWorld W(*this, TEXT("LadderCollision"), 2, Beat);
        if (!W.Start() || !Controls(W)) return false;
        for (TActorIterator<ASoraEnemy> It(W.World->GetTestWorld()); It; ++It) It->Destroy();
        auto* Player = W.Hero(); auto* Craft = W.Fieldcraft();
        const auto& Ladder = W.Craft().Ladders[0];
        const float Half = Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        const FVector Facing = FRotator(0, Ladder.Yaw, 0).Vector();
        const FVector Foot(Ladder.Foot, 0);
        const FVector Top = Foot + Facing * 150.f + FVector(0, 0, Ladder.HeightCm);
        const auto Feet = [&]() { return Player->GetActorLocation() - FVector(0, 0, Half); };
        const auto Finish = [&]()
        {
            float Largest = 0;
            for (int I = 0; I < 600 && Craft->IsOnLadder(); ++I)
            {
                const FVector Before = Player->GetActorLocation();
                if (!W.Tick(1)) return false;
                Largest = FMath::Max(Largest, float(FVector::Dist(Before, Player->GetActorLocation())));
            }
            AddInfo(FString::Printf(TEXT("%s maximum physical step %.6f cm"), *Ladder.Id, Largest));
            return TestTrue(TEXT("Approach, rungs and roof step all stay inside 150 cm/s"), Largest <= 2.6f);
        };
        // Only this initial fixture is placed. Both ends and every later
        // traversal use the real capsule, normal gravity and mapped keys.
        W.Stand(Foot - Facing * 100.f, Ladder.Yaw);
        if (!W.Tick(10) || !W.Press(EKeys::Escape) ||
            !TestTrue(TEXT("Jump can be rebound"), Player->RemapCombatAction(TEXT("Jump"), EKeys::J)) ||
            !W.Press(EKeys::Escape)) return false;
        W.Look(FRotator(0, Ladder.Yaw + 180.f, 0));
        TestFalse(TEXT("Facing away does not advertise a usable ladder"), Craft->Readout(*Player).bAtLadder);
        W.Look(FRotator(0, Ladder.Yaw, 0));
        TestTrue(TEXT("The grounded approach advertises the ladder"), Craft->Readout(*Player).bAtLadder);
        AActor* Barrier = Block(W, Foot + FVector(0, 0, 280), FVector(70, 70, 10));
        if (!TestNotNull(TEXT("An obstruction spans the ascent"), Barrier) || !W.Press(EKeys::J) ||
            !TestTrue(TEXT("Mapped Jump starts the climb with arms stowed"), Craft->IsOnLadder() && Craft->ArmsStowed()) || !Finish()) return false;
        TestTrue(TEXT("The ascent stays below the solid obstruction without awarding arrival"), Craft->IsOnLadder() &&
            Player->GetActorLocation().Z + Half <= 270.1f && !W.Raised(TEXT("roof_reached:") + Ladder.Id));
        const FVector Blocked = Player->GetActorLocation();
        if (!W.Press(EKeys::C) || !W.Tick(2)) return false;
        TestFalse(TEXT("Crouch cannot shrink the capsule through a ladder obstruction"), Player->IsCrouched());
        if (!W.Tick(120)) return false;
        TestTrue(TEXT("Waiting cannot tunnel through the obstruction"), Player->GetActorLocation().Equals(Blocked, .1f));
        if (!W.Press(EKeys::Escape)) return false;
        const FVector Paused = Player->GetActorLocation();
        if (!W.Tick(120)) return false;
        TestTrue(TEXT("The menu freezes ladder movement"), Player->GetActorLocation().Equals(Paused, .1f));
        if (!W.Press(EKeys::Escape)) return false;
        Barrier->Destroy();
        // A second blocker lies on the final horizontal step. The old
        // endpoint teleport would pass straight into this box.
        AActor* ExitBarrier = Block(W, Top + FVector(0, 0, Half), FVector(12, 12, Half));
        if (!TestNotNull(TEXT("The roof exit is obstructed"), ExitBarrier) || !Finish()) return false;
        TestTrue(TEXT("The final step also stops before a real obstacle"), Craft->IsOnLadder() &&
            FVector::Dist2D(Feet(), Top) >= Player->GetCapsuleComponent()->GetScaledCapsuleRadius() + 10.f &&
            !W.Raised(TEXT("roof_reached:") + Ladder.Id));
        ExitBarrier->Destroy();
        UStaticMeshComponent* Roof = nullptr;
        for (TActorIterator<AActor> It(W.World->GetTestWorld()); It; ++It)
        {
            TArray<UStaticMeshComponent*> Parts; It->GetComponents(Parts);
            for (auto* Part : Parts)
                if (Part->GetName().StartsWith(TEXT("Roof_") + Ladder.Id)) Roof = Part;
        }
        if (!TestNotNull(TEXT("The staged ladder has its actual roof slab"), Roof)) return false;
        const auto RoofCollision = Roof->GetCollisionEnabled();
        Roof->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        if (!Finish()) return false;
        TestTrue(TEXT("An unsupported endpoint cannot report a successful climb"), Craft->IsOnLadder() &&
            !W.Raised(TEXT("roof_reached:") + Ladder.Id));
        Roof->SetCollisionEnabled(RoofCollision);
        if (!Finish() || !W.Tick(5)) return false;
        TestTrue(TEXT("A clear ascent ends on the supported roof"), !Craft->IsOnLadder() &&
            Player->GetCharacterMovement()->IsMovingOnGround() && FVector::Dist(Feet(), Top) < 5.f &&
            W.Count(*(TEXT("roof_reached:") + Ladder.Id)) == 1);
        W.Look(FRotator(0, Ladder.Yaw + 180.f, 0));
        Barrier = Block(W, Foot + FVector(0, 0, 280), FVector(70, 70, 10));
        if (!TestNotNull(TEXT("An obstruction spans the descent"), Barrier) || !W.Press(EKeys::J) || !Finish()) return false;
        TestTrue(TEXT("The descending capsule remains above the obstruction"), Craft->IsOnLadder() && Feet().Z >= 289.9f &&
            !W.Raised(TEXT("ladder_foot:") + Ladder.Id));
        if (!W.Press(EKeys::J)) return false;
        TestTrue(TEXT("Jump releases an obstructed ladder at the actual position"), !Craft->IsOnLadder() &&
            Player->GetCharacterMovement()->MovementMode != MOVE_Flying && W.Raised(TEXT("ladder_release:") + Ladder.Id));
        Barrier->Destroy();
        if (!W.Tick(150)) return false;
        TestTrue(TEXT("The released hero lands under gravity"), Player->GetCharacterMovement()->IsMovingOnGround() &&
            FVector::Dist(Feet(), Foot) < 5.f);
        W.Look(FRotator(0, Ladder.Yaw, 0));
        if (!W.Press(EKeys::J) || !W.Tick(30)) return false;
        FBeatWorld::Hurt(*Player, 1.f);
        if (!W.Tick(2)) return false;
        TestTrue(TEXT("An injury interrupts the grip without awarding a roof"), !Craft->IsOnLadder() &&
            Player->GetCharacterMovement()->MovementMode != MOVE_Flying && W.Count(*(TEXT("roof_reached:") + Ladder.Id)) == 1);
        if (!W.Tick(150)) return false;
        W.Look(FRotator(0, Ladder.Yaw, 0));
        if (!W.Press(EKeys::J) || !Finish() || !W.Tick(5)) return false;
        W.Look(FRotator(0, Ladder.Yaw + 180.f, 0));
        if (!W.Press(EKeys::J) || !Finish() || !W.Tick(5)) return false;
        TestTrue(TEXT("The clear reverse route returns to the ground endpoint"), !Craft->IsOnLadder() &&
            Player->GetCharacterMovement()->IsMovingOnGround() && FVector::Dist(Feet(), Foot) < 5.f &&
            W.Count(*(TEXT("ladder_foot:") + Ladder.Id)) == 1);
        W.Look(FRotator(0, Ladder.Yaw, 0));
        if (!W.Press(EKeys::J) || !W.Tick(30)) return false;
        FBeatWorld::Hurt(*Player, Player->Health + 1000.f);
        if (!W.Tick(2) || !TestTrue(TEXT("Death on the ladder offers checkpoint retry"), W.Mode()->bDefeated) ||
            !W.Press(EKeys::Enter) || !Controls(W) || !W.Tick(10)) return false;
        TestTrue(TEXT("Retry discards the old ladder grip"), !Craft->IsOnLadder() && !Craft->HoldsHero() &&
            W.Hero()->GetCharacterMovement()->MovementMode != MOVE_Flying);
    }
    AddInfo(TEXT("Directed ladder collision and interruption evidence. Roof architecture, ordinary route play and visual acceptance remain separate."));
    return !HasAnyErrors();
}
#endif
