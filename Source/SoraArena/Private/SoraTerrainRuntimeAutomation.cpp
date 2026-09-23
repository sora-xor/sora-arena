#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "ArenaKernelSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "Misc/AutomationTest.h"
#include "Tests/AutomationCommon.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraNyaagyuTerrainRuntimeTest,
    "SoraArena.Campaign.NyaagyuTerrainRuntime",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraNyaagyuTerrainRuntimeTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Offline catalog loads before campaign world construction"),
        FSoraCatalog::Get().Load()))
        return false;
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
    bool bBlockoutRoadPresent = false;
    int32 CargoVisualCount = 0;
    int32 HiddenCoverColliders = 0;
    int32 WallVisualCount = 0;
    int32 HiddenBoundaryColliders = 0;
    for (UStaticMeshComponent* Component : CampaignMeshes)
    {
        if (!Component) continue;
        bBlockoutRoadPresent |= Component->GetName().StartsWith(TEXT("CentralRoad"));
        if (Component->GetName().StartsWith(TEXT("SM_Nyaagyu_CargoStack")))
        {
            ++CargoVisualCount;
            TestTrue(TEXT("Cargo art cannot change combat collision"),
                Component->GetCollisionEnabled() == ECollisionEnabled::NoCollision);
        }
        if (Component->GetName().StartsWith(TEXT("SM_Nyaagyu_EstateWall_4m")))
        {
            ++WallVisualCount;
            TestTrue(TEXT("Estate wall art cannot change combat collision"),
                Component->GetCollisionEnabled() == ECollisionEnabled::NoCollision);
            TestTrue(TEXT("Estate wall art participates in distance-field lighting"),
                Component->bAffectDistanceFieldLighting);
            TestTrue(TEXT("Estate wall art participates in dynamic indirect lighting"),
                Component->bAffectDynamicIndirectLighting);
        }
        if (Component->GetName().StartsWith(TEXT("WallX")) ||
            Component->GetName().StartsWith(TEXT("WallY")))
        {
            ++HiddenBoundaryColliders;
            TestFalse(TEXT("Primitive perimeter render is hidden behind authored modules"),
                Component->IsVisible());
            TestTrue(TEXT("Original perimeter wall still blocks campaign combat"),
                Component->GetCollisionEnabled() == ECollisionEnabled::QueryAndPhysics);
        }
        if (Component->GetName().StartsWith(TEXT("Cover")))
        {
            ++HiddenCoverColliders;
            TestFalse(TEXT("Primitive cover render is hidden behind authored cargo"), Component->IsVisible());
            TestTrue(TEXT("Original cover volume still blocks campaign combat"),
                Component->GetCollisionEnabled() == ECollisionEnabled::QueryAndPhysics);
        }
        if (Component->GetName().StartsWith(TEXT("Ground")) &&
            Component->GetCollisionEnabled() == ECollisionEnabled::QueryAndPhysics)
            bCollisionGroundPresent = true;
        if (!Component->GetName().StartsWith(TEXT("SM_NyaagyuTerrain_"))) continue;

        ++TerrainCount;
        const UStaticMesh* Mesh = Component->GetStaticMesh();
        if (!TestNotNull(*FString::Printf(TEXT("Terrain component %s has an asset"),
            *Component->GetName()), Mesh)) continue;
        // NewObject may append a unique suffix to a component name when it
        // collides with an asset object. The imported asset has the stable ID.
        const FString Name = Mesh->GetName();
        TestTrue(*FString::Printf(TEXT("Terrain component %s names its asset"),
            *Component->GetName()), Component->GetName().StartsWith(Name));
        TestFalse(*FString::Printf(TEXT("Terrain tile %s appears only once"), *Name), SeenTiles.Contains(Name));
        SeenTiles.Add(Name);
        TileLocations.Add(Name, Component->GetRelativeLocation());
        TestEqual(*FString::Printf(TEXT("Terrain asset %s"), *Name), Mesh->GetPathName(),
            FString::Printf(TEXT("/Game/Generated/Environment/Terrain/%s.%s"), *Name, *Name));
        for (int32 SlotIndex = 0; SlotIndex < Mesh->GetStaticMaterials().Num(); ++SlotIndex)
        {
            const FString Slot = Mesh->GetStaticMaterials()[SlotIndex].MaterialSlotName.ToString();
            const FString Role = Slot.Contains(TEXT("M_Terrain_Soil")) ? TEXT("Soil") : TEXT("Stone");
            const FString MaterialName = TEXT("MI_Nyaagyu_Terrain") + Role;
            const UMaterialInterface* Bound = Component->GetMaterial(SlotIndex);
            TestNotNull(*FString::Printf(TEXT("Terrain %s material %d is bound"), *Name, SlotIndex), Bound);
            if (Bound)
                TestEqual(*FString::Printf(TEXT("Terrain %s material %d uses macro-tint instance"), *Name, SlotIndex),
                    Bound->GetPathName(), FString::Printf(TEXT("/Game/Generated/Environment/%s.%s"), *MaterialName, *MaterialName));
        }
#if WITH_EDITORONLY_DATA
#if PLATFORM_MAC
        TestFalse(*FString::Printf(TEXT("Mac tile %s uses conventional geometry"), *Name),
            Mesh->GetNaniteSettings().bEnabled);
#else
        TestTrue(*FString::Printf(TEXT("High-detail tile %s enables Nanite"), *Name),
            Mesh->GetNaniteSettings().bEnabled);
#endif
#endif // Nanite authoring settings are stripped from packaged game targets.
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
    TestEqual(TEXT("Campaign has twelve authored cargo visuals"), CargoVisualCount, 12);
    TestEqual(TEXT("Campaign retains twelve hidden cover colliders"), HiddenCoverColliders, 12);
    TestEqual(TEXT("Campaign has fifty-eight authored perimeter modules"), WallVisualCount, 58);
    TestEqual(TEXT("Campaign retains four hidden perimeter colliders"), HiddenBoundaryColliders, 4);
    TestTrue(TEXT("Separate flat gameplay ground still supplies collision"), bCollisionGroundPresent);
    TestFalse(TEXT("Raised blockout road must not hide photographed terrain path"), bBlockoutRoadPresent);

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
    int32 PracticeCargoCount = 0;
    int32 PracticeWallVisualCount = 0;
    bool bKernelGroundPresent = false;
    bool bKernelWallPresent = false;
    for (UStaticMeshComponent* Component : PracticeMeshes)
    {
        if (!Component) continue;
        PracticeTerrainCount += Component->GetName().StartsWith(TEXT("SM_NyaagyuTerrain_")) ? 1 : 0;
        PracticeCargoCount += Component->GetName().StartsWith(TEXT("SM_Nyaagyu_CargoStack")) ? 1 : 0;
        PracticeWallVisualCount += Component->GetName().StartsWith(TEXT("SM_Nyaagyu_EstateWall_4m")) ? 1 : 0;
        bKernelGroundPresent |= Component->GetName().StartsWith(TEXT("KernelGround")) &&
            Component->GetCollisionEnabled() == ECollisionEnabled::QueryAndPhysics;
        bKernelWallPresent |= Component->GetName().StartsWith(TEXT("KernelWall0")) &&
            Component->GetCollisionEnabled() == ECollisionEnabled::QueryAndPhysics;
    }
    TestEqual(TEXT("Practice mode has no authored terrain components"), PracticeTerrainCount, 0);
    TestEqual(TEXT("Practice mode has no authored cargo components"), PracticeCargoCount, 0);
    TestEqual(TEXT("Practice mode has no authored perimeter components"), PracticeWallVisualCount, 0);
    TestTrue(TEXT("Practice mode has kernel-defined colliding ground"), bKernelGroundPresent);
    TestTrue(TEXT("Practice mode has kernel-defined colliding wall"), bKernelWallPresent);

    TestWorld.ForwardErrorMessages(this);
    UE_LOG(LogTemp, Display, TEXT("SORA_NYAAGYU_TERRAIN_RUNTIME_OK: campaign_tiles=%d practice_tiles=%d tier=%s"),
        TerrainCount, PracticeTerrainCount, Tier);
    return !HasAnyErrors();
}
#endif
