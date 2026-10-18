#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraCatalog.h"
#include "SoraEnemyTestArena.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraEquipmentComponent.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "World/SoraNavigation.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Templates/UniquePtr.h"

// The offline opponents' brain in real game worlds: the runtime navigation mesh
// takes a hunter around a wall placed during play, the view cone and line of
// sight decide what a sentry sees, a shot is heard where the cone cannot see,
// and a walker held fast gives up on its waypoint and walks on once free.
namespace SoraEnemyAI
{
using EState = SoraStealthRules::EState;

using SoraEnemyTest::FArena;

const TCHAR* Name(EState State)
{
    switch (State)
    {
    case EState::Unaware: return TEXT("Unaware");
    case EState::Suspicious: return TEXT("Suspicious");
    case EState::Alert: return TEXT("Alert");
    case EState::Search: return TEXT("Search");
    case EState::Combat: return TEXT("Combat");
    case EState::Retreat: return TEXT("Retreat");
    }
    return TEXT("Unknown");
}
} // namespace SoraEnemyAI

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraEnemyPathAroundWallTest,
    "SoraArena.AI.PathAroundWall",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraEnemyPathAroundWallTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraEnemyAI;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("PathAroundWall"));
    if (!Arena.Start())
        return false;
    // A ten-metre wall raised mid-road between a blade retainer and the hero.
    const FVector HeroAt(1000.f, 0.f, 0.f);
    const float WallX = 560.f, WallHalfLength = 500.f;
    Arena.PlaceHero(HeroAt, 180.f);
    Arena.Wall(FVector(WallX, 0.f, 200.f), FVector(60.f, WallHalfLength * 2.f, 400.f));
    ASoraEnemy* Retainer = Arena.Spawn(0, FVector(100.f, 0.f, 0.f), 0.f);
    ASoraEnemyController* Brain = FArena::Brain(Retainer);
    if (!TestNotNull(TEXT("A blade retainer spawns with its brain"), Brain) || !Arena.Tick(2))
        return false;
    TestTrue(TEXT("A combat-wave retainer hunts"), Brain->IsHunting() && Retainer->IsBladeRetainer());

    USoraNavigation* Nav = USoraNavigation::Get(Arena.Get());
    if (!TestTrue(TEXT("The runtime navigation mesh is ready"), Nav && Nav->IsReady()))
        return false;
    TestTrue(TEXT("The navigation bounds cover the built arena"), Nav->CoveredBounds().IsInsideXY(HeroAt) &&
        Nav->CoveredBounds().IsInsideXY(Retainer->GetActorLocation()));
    FHitResult Direct;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(AutomationWallCheck), false, Retainer);
    Arena.Get()->LineTraceSingleByChannel(Direct, Retainer->GetActorLocation(), Arena.Hero()->GetActorLocation(), ECC_Visibility, Query);
    TestTrue(TEXT("The wall blocks the straight line to the hero"),
        Direct.GetActor() && Direct.GetActor() != Arena.Hero() && !Direct.GetActor()->IsA<ASoraWorldBuilder>());
    TestFalse(TEXT("The retainer cannot see the hero through the wall"), Brain->CanSee(*Arena.Hero()));
    TArray<FVector> Path;
    const bool bPath = Nav->FindPath(Retainer->GetActorLocation(), Arena.Hero()->GetActorLocation(), *Retainer, Path);
    float PathWidest = 0.f;
    for (const FVector& Point : Path)
        PathWidest = FMath::Max(PathWidest, FMath::Abs(Point.Y));
    AddInfo(FString::Printf(TEXT("Mesh path from (%.0f, %.0f, %.0f): %d points, widest |y| %.0f"),
        Retainer->GetActorLocation().X, Retainer->GetActorLocation().Y, Retainer->GetActorLocation().Z, Path.Num(), PathWidest));
    TestTrue(TEXT("The mesh path bends around the wall's end"), bPath && Path.Num() >= 3 && PathWidest >= WallHalfLength);
    const int32 RebuildsBefore = Nav->Rebuilds();

    float Widest = 0.f;
    int32 Frames = 0;
    for (; Frames < 900 && FVector::Dist2D(Retainer->GetActorLocation(), Arena.Hero()->GetActorLocation()) > 260.f; ++Frames)
    {
        if (!Arena.Tick(1))
            return false;
        Widest = FMath::Max(Widest, FMath::Abs(Retainer->GetActorLocation().Y));
    }
    const FVector End = Retainer->GetActorLocation();
    AddInfo(FString::Printf(TEXT("Retainer reached (%.0f, %.0f) after %d frames; widest |y| %.0f; state %s"),
        End.X, End.Y, Frames, Widest, Name(Brain->State())));
    TestTrue(TEXT("The retainer reaches the hero"), FVector::Dist2D(End, Arena.Hero()->GetActorLocation()) <= 260.f);
    TestTrue(TEXT("The retainer ends on the hero's side of the wall"), End.X > WallX);
    TestTrue(TEXT("The retainer walked around the wall's end"), Widest >= WallHalfLength - 20.f);
    TestEqual(TEXT("A settled arena is not rebuilt while the retainer walks"), Nav->Rebuilds(), RebuildsBefore);
    TestEqual(TEXT("The retainer fights once it sees the hero"), static_cast<int32>(Brain->State()), static_cast<int32>(EState::Combat));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraEnemySightConeTest,
    "SoraArena.AI.SightCone",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraEnemySightConeTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraEnemyAI;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("SightCone"));
    if (!Arena.Start())
        return false;
    // A sentry at its post looking east along the road.
    Arena.PlaceHero(FVector(-600.f, 0.f, 0.f), 0.f);
    ASoraEnemy* Sentry = Arena.Sentry(2, FVector::ZeroVector, 0.f);
    ASoraEnemyController* Brain = FArena::Brain(Sentry);
    if (!TestNotNull(TEXT("A sentry spawns with its brain"), Brain) || !Arena.Tick(2))
        return false;
    ASoraPlayerCharacter* Hero = Arena.Hero();
    TestFalse(TEXT("A sentry is not a hunter"), Brain->IsHunting());

    // Behind the sentry, six metres away in daylight: outside the cone.
    TestFalse(TEXT("The hero behind the sentry is not seen"), Brain->CanSee(*Hero));
    if (!Arena.Tick(120))
        return false;
    TestEqual(TEXT("Two seconds behind the sentry leave it unaware"), static_cast<int32>(Brain->State()), static_cast<int32>(EState::Unaware));
    TestEqual(TEXT("Nothing behind the sentry raises its awareness"), Brain->AwarenessPermille(), 0);

    // Beyond sight range straight ahead.
    Arena.PlaceHero(FVector(2950.f, 0.f, 0.f), 180.f);
    TestFalse(TEXT("The hero beyond sight range is not seen"), Brain->CanSee(*Hero));

    // In the cone but behind a wall raised between them.
    const FVector InFront(1000.f, 300.f, 0.f);
    AActor* Screen = Arena.Wall(FVector(500.f, 150.f, 200.f), FVector(60.f, 800.f, 400.f));
    Arena.PlaceHero(InFront, 180.f);
    if (!Arena.Tick(1))
        return false;
    TestFalse(TEXT("The hero behind a wall in the cone is not seen"), Brain->CanSee(*Hero));
    if (!Arena.Tick(120))
        return false;
    TestEqual(TEXT("Two seconds behind the wall leave the sentry unaware"), static_cast<int32>(Brain->State()), static_cast<int32>(EState::Unaware));

    // The wall comes down: in the cone and unobstructed.
    Screen->Destroy();
    if (!Arena.Tick(1))
        return false;
    TestTrue(TEXT("The hero in the cone with a clear line is seen"), Brain->CanSee(*Hero));
    int32 Frames = 0;
    while (Frames < 90 && Brain->State() != EState::Combat)
    {
        if (!Arena.Tick(1))
            return false;
        ++Frames;
    }
    AddInfo(FString::Printf(TEXT("The sentry reached %s after %d frames in view"), Name(Brain->State()), Frames));
    TestEqual(TEXT("A clear view in daylight brings the sentry into combat"), static_cast<int32>(Brain->State()), static_cast<int32>(EState::Combat));
    TestTrue(TEXT("Detection builds over several frames, not at once"), Frames > 3);
    TestTrue(TEXT("The sentry knows where the hero stands"), FVector::Dist2D(Brain->LastKnownLocation(), Hero->GetActorLocation()) < 50.f);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraEnemyHearsShotTest,
    "SoraArena.AI.HearsShot",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraEnemyHearsShotTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraEnemyAI;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("HearsShot"));
    if (!Arena.Start())
        return false;
    // Both sentries face east, away from the hero west of them: one fifteen
    // metres off, one beyond a gunshot's forty-metre reach.
    const FVector HeroAt(-1500.f, 0.f, 0.f);
    Arena.PlaceHero(HeroAt, 180.f);
    ASoraEnemy* Near = Arena.Sentry(2, FVector::ZeroVector, 0.f);
    ASoraEnemy* Far = Arena.Sentry(3, FVector(2600.f, 300.f, 0.f), 0.f);
    ASoraEnemyController* NearBrain = FArena::Brain(Near);
    ASoraEnemyController* FarBrain = FArena::Brain(Far);
    if (!TestTrue(TEXT("Both sentries spawn with brains"), NearBrain && FarBrain) || !Arena.Tick(60))
        return false;
    TestFalse(TEXT("The near sentry cannot see the hero behind it"), NearBrain->CanSee(*Arena.Hero()));
    TestEqual(TEXT("A silent hero leaves the near sentry unaware"), static_cast<int32>(NearBrain->State()), static_cast<int32>(EState::Unaware));

    // The carbine, taken up on the firearms key, then one shot fired west, away from both sentries.
    if (!Arena.World->TakeUpArm(1) || !Arena.Tick(30))
        return TestTrue(TEXT("The hero draws the carbine"), false);
    TestEqual(TEXT("The sentries ignore a hero changing weapons at rest"), static_cast<int32>(NearBrain->State()), static_cast<int32>(EState::Unaware));
    const int32 AmmoBefore = Arena.Hero()->GetEquipment()->Ammo;
    if (!Arena.World->InjectKey(EKeys::LeftMouseButton, IE_Pressed) || !Arena.Tick(1) ||
        !Arena.World->InjectKey(EKeys::LeftMouseButton, IE_Released) || !Arena.Tick(1))
        return TestTrue(TEXT("The hero fires"), false);
    TestEqual(TEXT("The hero holds the carbine"), Arena.Hero()->WeaponId, 1);
    TestTrue(TEXT("A round leaves the carbine"), Arena.Hero()->GetEquipment()->Ammo < AmmoBefore);
    const EState Heard = NearBrain->State();
    AddInfo(FString::Printf(TEXT("After the shot the near sentry is %s, the far one %s"), Name(Heard), Name(FarBrain->State())));
    TestTrue(TEXT("The near sentry hears the shot and is alerted"), Heard == EState::Alert || Heard == EState::Combat);
    TestTrue(TEXT("The shot tells the near sentry where the hero is"),
        FVector::Dist2D(NearBrain->LastKnownLocation(), Arena.Hero()->GetActorLocation()) < 200.f);
    TestEqual(TEXT("The far sentry, beyond a shot's reach, stays unaware"), static_cast<int32>(FarBrain->State()), static_cast<int32>(EState::Unaware));

    // Alerted, the near sentry turns to the place it heard and finds the hero.
    int32 Frames = 0;
    while (Frames < 180 && NearBrain->State() != EState::Combat)
    {
        if (!Arena.Tick(1))
            return false;
        ++Frames;
    }
    AddInfo(FString::Printf(TEXT("The near sentry reached %s %d frames after the shot"), Name(NearBrain->State()), Frames));
    TestEqual(TEXT("The alerted sentry turns and fights the hero"), static_cast<int32>(NearBrain->State()), static_cast<int32>(EState::Combat));
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraEnemyCoverAndFlankTest,
    "SoraArena.AI.CoverAndFlank",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraEnemyCoverAndFlankTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraEnemyAI;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("CoverAndFlank"));
    if (!Arena.Start())
        return false;
    // Two hunters meet the hero on the open road between the estate's cover boxes.
    const FVector HeroAt(-1000.f, 0.f, 0.f);
    Arena.PlaceHero(HeroAt, 0.f);
    ASoraEnemy* Shooter = Arena.Spawn(2, FVector(300.f, -250.f, 0.f), 180.f);
    ASoraEnemy* Flanker = Arena.Spawn(1, FVector(300.f, 250.f, 0.f), 180.f);
    ASoraEnemyController* ShooterBrain = FArena::Brain(Shooter);
    ASoraEnemyController* FlankerBrain = FArena::Brain(Flanker);
    if (!TestTrue(TEXT("Both hunters spawn with brains"), ShooterBrain && FlankerBrain))
        return false;
    TestEqual(TEXT("Slot 2 takes cover"), static_cast<int32>(ShooterBrain->CombatRole()), static_cast<int32>(SoraStealthRules::ERole::CoverShooter));
    TestEqual(TEXT("Slot 1 flanks"), static_cast<int32>(FlankerBrain->CombatRole()), static_cast<int32>(SoraStealthRules::ERole::Flanker));

    float ClosestToCover = TNumericLimits<float>::Max();
    int32 Frames = 0;
    for (; Frames < 420; ++Frames)
    {
        if (!Arena.Tick(1))
            return false;
        if (ShooterBrain->HoldsPosition())
            ClosestToCover = FMath::Min(ClosestToCover, FVector::Dist2D(Shooter->GetActorLocation(), ShooterBrain->HeldPosition()));
        if (ClosestToCover <= 60.f && FlankerBrain->HoldsPosition() && Frames >= 240)
            break;
    }
    const FVector Cover = ShooterBrain->HeldPosition();
    const FVector Flank = FlankerBrain->HeldPosition();
    AddInfo(FString::Printf(TEXT("After %d frames the shooter holds (%.0f, %.0f), closest %.0f; the flanker holds (%.0f, %.0f)"),
        Frames, Cover.X, Cover.Y, ClosestToCover, Flank.X, Flank.Y));
    if (!TestTrue(TEXT("The cover shooter chooses a position"), ShooterBrain->HoldsPosition()))
        return false;
    TestTrue(TEXT("The cover shooter reaches its cover"), ClosestToCover <= 60.f);
    // A box of the arena stands between the hero's chest and a body at the spot.
    FHitResult Screen;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(AutomationCoverCheck), false, Arena.Hero());
    Query.AddIgnoredActor(Shooter);
    Query.AddIgnoredActor(Flanker);
    const FVector Chest(0.f, 0.f, 10.f);
    Arena.Get()->LineTraceSingleByChannel(Screen, Arena.Hero()->GetActorLocation() + Chest,
        FVector(Cover.X, Cover.Y, Shooter->GetActorLocation().Z) + Chest, ECC_Visibility, Query);
    TestTrue(TEXT("The cover shields the shooter's body from the hero"), Screen.bBlockingHit && Screen.GetActor() && Screen.GetActor()->IsA<ASoraWorldBuilder>());
    if (!TestTrue(TEXT("The flanker chooses a position"), FlankerBrain->HoldsPosition()))
        return false;
    // Seen from the hero, the flank opens a second direction of fire.
    const FVector FromHeroToFlank = (Flank - Arena.Hero()->GetActorLocation()).GetSafeNormal2D();
    const FVector FromHeroToShooter = (Shooter->GetActorLocation() - Arena.Hero()->GetActorLocation()).GetSafeNormal2D();
    const float Spread = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(FromHeroToFlank, FromHeroToShooter), -1.f, 1.f)));
    AddInfo(FString::Printf(TEXT("The flank opens %.0f degrees from the shooter around the hero"), Spread));
    TestTrue(TEXT("The flanker circles to the hero's side"), Spread >= 45.f);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraEnemyPatrolTest,
    "SoraArena.AI.Patrol",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraEnemyPatrolTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraEnemyAI;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("Patrol"));
    if (!Arena.Start())
        return false;
    // The hero rests far out of sight; the guard walks a three-point loop.
    Arena.PlaceHero(FVector(-2900.f, 1000.f, 0.f), 0.f);
    FSoraPatrolRoute Route;
    Route.Points = {FVector(0.f, 0.f, 90.f), FVector(600.f, 0.f, 90.f), FVector(600.f, 300.f, 90.f)};
    Route.PauseMs = 500;
    ASoraEnemy* Guard = Arena.Spawn(3, FVector::ZeroVector, 0.f, &Route);
    ASoraEnemyController* Brain = FArena::Brain(Guard);
    if (!TestNotNull(TEXT("A patrolling guard spawns with its brain"), Brain))
        return false;
    TArray<int32> Visits;
    for (int32 Frame = 0; Frame < 900 && Visits.Num() < 4; ++Frame)
    {
        if (!Arena.Tick(1))
            return false;
        for (int32 Point = 0; Point < Route.Points.Num(); ++Point)
            if (FVector::Dist2D(Guard->GetActorLocation(), Route.Points[Point]) <= 80.f && (Visits.IsEmpty() || Visits.Last() != Point))
                Visits.Add(Point);
    }
    FString Order;
    for (const int32 Point : Visits)
        Order += FString::Printf(TEXT("%d "), Point);
    AddInfo(FString::Printf(TEXT("Waypoints visited: %s"), *Order));
    TestTrue(TEXT("The guard walks its route in order and loops back"), Visits == TArray<int32>({0, 1, 2, 0}));
    TestEqual(TEXT("A guard that never sees or hears the hero stays unaware"), static_cast<int32>(Brain->State()), static_cast<int32>(EState::Unaware));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraEnemyBlockedWalksOnTest,
    "SoraArena.AI.BlockedWalksOn",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraEnemyBlockedWalksOnTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraEnemyAI;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FArena Arena(*this, TEXT("BlockedWalksOn"));
    if (!Arena.Start())
        return false;
    // A walking guard and a patrol drone, each held where it stands for longer
    // than the stuck clock (a body in a corridor, a net): each gives up on its
    // waypoint, and once free walks or flies on to the next one instead of
    // standing blocked for good. The walker starts on the world's origin,
    // where a stale clock once blocked a first walk outright.
    Arena.PlaceHero(FVector(-2900.f, 1000.f, 0.f), 90.f);
    FSoraPatrolRoute Walk;
    Walk.Points = {FVector(0.f, 0.f, 90.f), FVector(1500.f, 0.f, 90.f)};
    Walk.PauseMs = 500;
    // The drone flies the same road, above and beside the walker.
    FSoraPatrolRoute Flight;
    Flight.Points = {FVector(0.f, 300.f, 90.f), FVector(1500.f, 300.f, 90.f)};
    Flight.PauseMs = 500;
    ASoraEnemy* Guard = Arena.Spawn(3, FVector::ZeroVector, 0.f, &Walk);
    ASoraEnemy* Drone = Arena.SpawnKind(TEXT("drone"), 4, FVector(0.f, 300.f, 0.f), 0.f, &Flight);
    if (!TestNotNull(TEXT("A patrolling guard spawns with its brain"), FArena::Brain(Guard)) ||
        !TestNotNull(TEXT("A patrolling drone spawns with its brain"), FArena::Brain(Drone)))
        return false;
    // Three seconds in, both are on their way along their routes.
    const TArray<ASoraEnemy*> Walkers{Guard, Drone};
    for (int32 Frame = 0; Frame < 180; ++Frame)
    {
        if (!Arena.Tick(1))
            return false;
        if (Frame % 30 == 29)
            for (ASoraEnemy* Walker : Walkers)
                AddInfo(FString::Printf(TEXT("%.1f s: %s at (%.0f, %.0f, %.0f), moving %.0f cm/s"), (Frame + 1) / 60.f,
                    *Walker->ArchetypeId().ToString(), Walker->GetActorLocation().X, Walker->GetActorLocation().Y,
                    Walker->GetActorLocation().Z, Walker->GetVelocity().Size2D()));
    }
    for (ASoraEnemy* Walker : Walkers)
        TestTrue(*FString::Printf(TEXT("The %s is on its way along its route"), *Walker->ArchetypeId().ToString()),
            Walker->GetVelocity().Size2D() > 50.f && Walker->GetActorLocation().X > 100.f);
    // Held fast for three seconds: longer than the stuck clock, so each
    // gives up on its waypoint and pauses.
    TArray<TEnumAsByte<EMovementMode>> Modes;
    TArray<FVector> Held;
    for (ASoraEnemy* Walker : Walkers)
    {
        Modes.Add(Walker->GetCharacterMovement()->MovementMode);
        Walker->GetCharacterMovement()->StopMovementImmediately();
        Walker->GetCharacterMovement()->DisableMovement();
        Held.Add(Walker->GetActorLocation());
    }
    if (!Arena.Tick(180))
        return false;
    for (int32 Index = 0; Index < Walkers.Num(); ++Index)
    {
        TestTrue(TEXT("Held, it stays put"), FVector::Dist2D(Walkers[Index]->GetActorLocation(), Held[Index]) < 5.f);
        Walkers[Index]->GetCharacterMovement()->SetMovementMode(Modes[Index]);
    }
    // Free again: after its pause it walks on to its next waypoint.
    TArray<float> Farthest;
    Farthest.Init(0.f, Walkers.Num());
    for (int32 Frame = 0; Frame < 240; ++Frame)
    {
        if (!Arena.Tick(1))
            return false;
        for (int32 Index = 0; Index < Walkers.Num(); ++Index)
            Farthest[Index] = FMath::Max(Farthest[Index], static_cast<float>(FVector::Dist2D(Walkers[Index]->GetActorLocation(), Held[Index])));
    }
    for (int32 Index = 0; Index < Walkers.Num(); ++Index)
    {
        const FString What = Walkers[Index]->ArchetypeId().ToString();
        AddInfo(FString::Printf(TEXT("In the four seconds after it was freed, the %s went as far as %.0f cm from where it was held"),
            *What, Farthest[Index]));
        TestTrue(*FString::Printf(TEXT("The freed %s walks on"), *What), Farthest[Index] > 200.f);
        TestEqual(TEXT("It never noticed the hero"), static_cast<int32>(FArena::Brain(Walkers[Index])->State()),
            static_cast<int32>(EState::Unaware));
    }
    return true;
}
#endif
