#include "SoraWorldBuilder.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "ArenaKernelSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Misc/AutomationTest.h"
#include "Tests/AutomationCommon.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraNyaagyuTerrainRuntimeTest,
    "SoraArena.Campaign.NyaagyuTerrainRuntime",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraNyaagyuTerrainRuntimeTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    FTestWorldWrapper TestWorld;
    if (!TestTrue(TEXT("A disposable game world can be created"), TestWorld.CreateTestWorld(EWorldType::Game)))
        return false;
    UWorld* World = TestWorld.GetTestWorld();
    if (!TestNotNull(TEXT("Test world exists"), World))
        return false;
    ASoraWorldBuilder* Builder = World->SpawnActor<ASoraWorldBuilder>();
    if (!TestNotNull(TEXT("Campaign builder spawns"), Builder))
        return false;

    // Inspect the spawned components, not the manifest or source text. Missing
    // imports, wrong platform selection, or changed component setup must fail.
    Builder->Build(0);
#if PLATFORM_MAC
    const TCHAR* Tier = TEXT("MAC");
#else
    const TCHAR* Tier = TEXT("HI");
#endif
    TInlineComponentArray<UStaticMeshComponent*> CampaignMeshes;
    Builder->GetComponents(CampaignMeshes);
    int32 TerrainCount = 0;
    TSet<FString> SeenTiles;
    TMap<FString, FVector> TileLocations;
    bool bCollisionGroundPresent = false;
    for (UStaticMeshComponent* Component : CampaignMeshes)
    {
        if (!Component) continue;
        if (Component->GetName().StartsWith(TEXT("Ground")) &&
            Component->GetCollisionEnabled() == ECollisionEnabled::QueryAndPhysics)
            bCollisionGroundPresent = true;
        if (!Component->GetName().StartsWith(TEXT("SM_NyaagyuTerrain_"))) continue;

        ++TerrainCount;
        const FString Name = Component->GetName();
        TestFalse(*FString::Printf(TEXT("Terrain tile %s appears only once"), *Name), SeenTiles.Contains(Name));
        SeenTiles.Add(Name);
        TileLocations.Add(Name, Component->GetRelativeLocation());
        const UStaticMesh* Mesh = Component->GetStaticMesh();
        if (!TestNotNull(*FString::Printf(TEXT("Terrain tile %s loaded"), *Name), Mesh)) continue;
        TestEqual(*FString::Printf(TEXT("Terrain asset %s"), *Name), Mesh->GetPathName(),
            FString::Printf(TEXT("/Game/Generated/Environment/Terrain/%s.%s"), *Name, *Name));
#if PLATFORM_MAC
        TestFalse(*FString::Printf(TEXT("Mac tile %s uses conventional geometry"), *Name),
            Mesh->GetNaniteSettings().bEnabled);
#else
        TestTrue(*FString::Printf(TEXT("High-detail tile %s enables Nanite"), *Name),
            Mesh->GetNaniteSettings().bEnabled);
#endif
        TestTrue(*FString::Printf(TEXT("Terrain tile %s does not change collision"), *Name),
            Component->GetCollisionEnabled() == ECollisionEnabled::NoCollision);
        TestTrue(*FString::Printf(TEXT("Terrain tile %s contributes to distance-field lighting"), *Name),
            Component->bAffectDistanceFieldLighting != 0);
        TestTrue(*FString::Printf(TEXT("Terrain tile %s contributes to dynamic indirect lighting"), *Name),
            Component->bAffectDynamicIndirectLighting != 0);
        TestTrue(*FString::Printf(TEXT("Terrain tile %s casts shadows"), *Name), Component->CastShadow != 0);
        TestTrue(*FString::Printf(TEXT("Terrain tile %s is visible to hardware ray tracing"), *Name),
            Component->bVisibleInRayTracing != 0);
        TestTrue(*FString::Printf(TEXT("Terrain tile %s is registered"), *Name), Component->IsRegistered());
    }
    TestEqual(TEXT("Campaign has exactly sixteen authored terrain tiles"), TerrainCount, 16);
    TestTrue(TEXT("Separate flat gameplay ground still supplies collision"), bCollisionGroundPresent);

    for (int32 Y = 0; Y < 4; ++Y)
    for (int32 X = 0; X < 4; ++X)
    {
        const FString Name = FString::Printf(TEXT("SM_NyaagyuTerrain_%s_X%d_Y%d"), Tier, X, Y);
        TestTrue(*FString::Printf(TEXT("Platform tile %s is present"), *Name), SeenTiles.Contains(Name));
        if (const FVector* Position = TileLocations.Find(Name))
        {
            const FVector Expected(-2400 + X * 1600, -1950 + Y * 1300, 0);
            TestTrue(*FString::Printf(TEXT("Platform tile %s is at its authored grid location"), *Name),
                Position->Equals(Expected, 0.01));
        }
    }

    // Reuse the actor so ClearArena is covered too: no visual campaign tile
    // may remain in a deterministic practice map, even as collisionless art.
    FSoraPracticeMap PracticeMap;
    PracticeMap.Minimum = FVector(-3200, -2600, 0);
    PracticeMap.Maximum = FVector(3200, 2600, 500);
    PracticeMap.Walls.Add({FVector(-200, -100, 0), FVector(200, 100, 300)});
    Builder->BuildPractice(0, PracticeMap);
    TInlineComponentArray<UStaticMeshComponent*> PracticeMeshes;
    Builder->GetComponents(PracticeMeshes);
    int32 PracticeTerrainCount = 0;
    bool bKernelGroundPresent = false;
    bool bKernelWallPresent = false;
    for (UStaticMeshComponent* Component : PracticeMeshes)
    {
        if (!Component) continue;
        PracticeTerrainCount += Component->GetName().StartsWith(TEXT("SM_NyaagyuTerrain_")) ? 1 : 0;
        bKernelGroundPresent |= Component->GetName().StartsWith(TEXT("KernelGround")) &&
            Component->GetCollisionEnabled() == ECollisionEnabled::QueryAndPhysics;
        bKernelWallPresent |= Component->GetName().StartsWith(TEXT("KernelWall0")) &&
            Component->GetCollisionEnabled() == ECollisionEnabled::QueryAndPhysics;
    }
    TestEqual(TEXT("Practice mode has no authored terrain components"), PracticeTerrainCount, 0);
    TestTrue(TEXT("Practice mode has kernel-defined colliding ground"), bKernelGroundPresent);
    TestTrue(TEXT("Practice mode has kernel-defined colliding wall"), bKernelWallPresent);

    TestWorld.ForwardErrorMessages(this);
    UE_LOG(LogTemp, Display, TEXT("SORA_NYAAGYU_TERRAIN_RUNTIME_OK: campaign_tiles=%d practice_tiles=%d tier=%s"),
        TerrainCount, PracticeTerrainCount, Tier);
    return !HasAnyErrors();
}
#endif
