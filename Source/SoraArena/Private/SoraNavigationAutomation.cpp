#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraCatalog.h"
#include "SoraEnemyTestArena.h"
#include "SoraWorldBuilder.h"
#include "World/SoraNavigation.h"
#include "AI/Navigation/NavigationElement.h"
#include "AI/Navigation/NavigationRelevantData.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "NavigationOctree.h"
#include "NavigationSystem.h"

// Visual-only meshes never shape the offline opponents' navigation mesh. The
// arena, boss hazards, telegraphs, bodies and dressing are all built at
// runtime. A mesh set on a new component while it still had the default
// blocking collision entered the navigation octree at the origin, and a cooked
// game kept that entry after the collision was turned off: the next rebuild
// cut holes wherever the visual shape then stood, so in the package Tarifa
// walked around her own painted steam zone and an automaton ended up in her
// tether's line. The editor, whose meshes are still compiling when first set,
// never showed it, so this test matters most in the packaged run.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraVisualMeshesOffNavigationTest,
    "SoraArena.AI.VisualMeshesOffNavigation",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraVisualMeshesOffNavigationTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    SoraEnemyTest::FArena Arena(*this, TEXT("VisualMeshesOffNavigation"));
    if (!Arena.Start())
        return false;
    // A painted zone on the open road, built as a boss hazard builds one: a
    // 2.5-metre disc and its sixteen-segment rim, none of it colliding.
    const FVector Center(900.f, 0.f, 0.f);
    constexpr float Radius = 250.f;
    AActor* Zone = Arena.Get()->SpawnActor<AActor>();
    USceneComponent* Root = NewObject<USceneComponent>(Zone, TEXT("ZoneRoot"));
    Zone->SetRootComponent(Root);
    Root->RegisterComponent();
    Zone->SetActorLocation(Center);
    const TCHAR* Cylinder = TEXT("/Engine/BasicShapes/Cylinder.Cylinder");
    ASoraWorldBuilder::Shape(Zone, Root, TEXT("ZoneFill"), Cylinder, FVector(0.f, 0.f, 1.f), FVector(Radius / 50.f, Radius / 50.f, .04f),
        FLinearColor(1.f, .68f, .16f));
    for (int32 Segment = 0; Segment < 16; ++Segment)
    {
        const FVector A = FVector(Radius, 0.f, 2.f).RotateAngleAxis(22.5f * Segment, FVector::UpVector);
        const FVector B = FVector(Radius, 0.f, 2.f).RotateAngleAxis(22.5f * (Segment + 1), FVector::UpVector);
        UStaticMeshComponent* Edge = ASoraWorldBuilder::Shape(Zone, Root, FString::Printf(TEXT("ZoneRim%d"), Segment), Cylinder,
            (A + B) * .5f, FVector(.05f, .05f, FVector::Distance(A, B) / 100.f), FLinearColor(1.f, .68f, .16f));
        Edge->SetRelativeRotation(FRotationMatrix::MakeFromZ(B - A).Rotator());
    }
    if (!Arena.Tick(2))
        return false;
    UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(Arena.Get());
    USoraNavigation* Nav = USoraNavigation::Get(Arena.Get());
    if (!TestTrue(TEXT("The runtime navigation mesh is ready"), NavSys && NavSys->GetNavOctree() && Nav && Nav->Settle()))
        return false;
    // Everything the octree holds can shape the mesh: the estate's terrain,
    // trees and props, the bodies and the painted zone are not in it.
    int32 Entries = 0;
    TArray<FString> Visual;
    NavSys->GetNavOctree()->FindElementsWithBoundsTest(FBoxCenterAndExtent(Nav->CoveredBounds().ExpandBy(1000.f)),
        [&Entries, &Visual](const FNavigationOctreeElement& Element)
        {
            ++Entries;
            const auto* Piece = Cast<UPrimitiveComponent>(Element.Data->SourceElement->GetWeakUObject().Get());
            if (Piece && !Piece->IsNavigationRelevant())
                Visual.Add(Piece->GetPathName());
        });
    for (int32 Index = 0; Index < FMath::Min(Visual.Num(), 8); ++Index)
        AddError(FString::Printf(TEXT("A visual-only mesh is in the navigation octree: %s"), *Visual[Index]));
    TestTrue(TEXT("The navigation octree holds the arena's collision"), Entries > 0);
    TestEqual(TEXT("No visual-only mesh is in the navigation octree"), Visual.Num(), 0);
    // A full rebuild from the world as it stands leaves the road under and
    // around the zone whole.
    NavSys->Build();
    int32 Probes = 0, OffMesh = 0;
    for (float Y = -Radius - 100.f; Y <= Radius + 100.f; Y += 50.f)
        for (float X = Center.X - Radius - 100.f; X <= Center.X + Radius + 100.f; X += 50.f)
        {
            FVector OnMesh;
            ++Probes;
            OffMesh += Nav->Project(FVector(X, Y, 50.f), OnMesh) && FVector::Dist2D(OnMesh, FVector(X, Y, 0.f)) < 5.f ? 0 : 1;
        }
    AddInfo(FString::Printf(TEXT("%d octree entries; %d of %d road points around the zone are off the mesh"), Entries, OffMesh, Probes));
    TestEqual(TEXT("The painted zone cuts no hole in the navigation mesh"), OffMesh, 0);
    TArray<FVector> Path;
    const bool bPath = Nav->FindPath(Center + FVector(Radius + 150.f, 0.f, 0.f), Center - FVector(Radius + 150.f, 0.f, 0.f), *Arena.Hero(), Path);
    float Widest = 0.f;
    for (const FVector& Point : Path)
        Widest = FMath::Max(Widest, FMath::Abs(Point.Y - Center.Y));
    TestTrue(*FString::Printf(TEXT("A path across the zone runs straight (%d points, widest %.0f cm off the line)"), Path.Num(), Widest),
        bPath && Widest < 5.f);
    return true;
}
#endif
