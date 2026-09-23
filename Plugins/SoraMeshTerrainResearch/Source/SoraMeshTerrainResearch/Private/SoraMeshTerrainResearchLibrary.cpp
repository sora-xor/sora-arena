#include "SoraMeshTerrainResearchLibrary.h"

#include "Editor.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "MeshDescriptionToDynamicMesh.h"
#include "MeshPartition.h"
#include "MeshPartitionCompiledSection.h"
#include "MeshPartitionDefinition.h"
#include "MeshPartitionEditorComponent.h"
#include "MeshPartitionStaticMeshComponent.h"
#include "WorldPartition/WorldPartition.h"
#include "WorldPartition/WorldPartitionHandle.h"

DEFINE_LOG_CATEGORY_STATIC(LogSoraMeshTerrainResearch, Log, All);

namespace
{
    constexpr int32 TileCountPerAxis = 4;
    constexpr int32 TrianglesPerTile = 26624;
    const FString ResearchMap = TEXT("/Game/Research/NyaagyuMeshTerrain_Source_WP");
    const FString TileFolder = TEXT("/Game/Generated/Environment/Terrain/");

    struct FPreparedTile
    {
        AStaticMeshActor* Actor = nullptr;
        FDynamicMesh3 Mesh;
        TArray<UMaterialInterface*> Materials;
        FBox WorldBounds;
    };

    bool Fail(const FString& Reason)
    {
        UE_LOG(LogSoraMeshTerrainResearch, Error, TEXT("SORA_MESH_RESEARCH_REJECTED: %s"), *Reason);
        return false;
    }
}

bool USoraMeshTerrainResearchLibrary::ConvertPlacedHiTiles()
{
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World || !World->GetWorldPartition() || World->GetOutermost()->GetName() != ResearchMap)
    {
        return Fail(TEXT("Expected the separate World Partition research map"));
    }
    TArray<FWorldPartitionReference> LoadedActorReferences;
    World->GetWorldPartition()->LoadAllActors(LoadedActorReferences);

    for (TActorIterator<UE::MeshPartition::AMeshPartition> It(World); It; ++It)
    {
        return Fail(TEXT("Map already contains a Mesh Partition; refusing a duplicate conversion"));
    }

    auto* Definition = Cast<UE::MeshPartition::UMeshPartitionDefinition>(StaticLoadObject(
        UE::MeshPartition::UMeshPartitionDefinition::StaticClass(), nullptr,
        TEXT("/MeshPartition/DataAssets/MPD_Default.MPD_Default")));
    if (!Definition || Definition->GetCompiledSectionBuildVariants().IsEmpty())
    {
        return Fail(TEXT("Epic MPD_Default definition or build variants are unavailable"));
    }
    for (const auto& Variant : Definition->GetCompiledSectionBuildVariants())
    {
        if (!Variant.TransformerPipeline)
        {
            return Fail(TEXT("Default definition has a build variant without a transformer pipeline"));
        }
    }

    TArray<FPreparedTile> Prepared;
    Prepared.Reserve(TileCountPerAxis * TileCountPerAxis);
    for (int32 Y = 0; Y < TileCountPerAxis; ++Y)
    {
        for (int32 X = 0; X < TileCountPerAxis; ++X)
        {
            const FString Name = FString::Printf(TEXT("SM_NyaagyuTerrain_HI_X%d_Y%d"), X, Y);
            const FString ActorLabel = FString::Printf(TEXT("ResearchTerrain_%s"), *Name);
            const FString AssetPath = TileFolder + Name + TEXT(".") + Name;
            AStaticMeshActor* TileActor = nullptr;
            for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
            {
                if (It->GetActorLabel() == ActorLabel)
                {
                    if (TileActor)
                    {
                        return Fail(TEXT("Duplicate tile actor: ") + ActorLabel);
                    }
                    TileActor = *It;
                }
            }
            if (!TileActor)
            {
                return Fail(TEXT("Missing loaded HI tile actor: ") + ActorLabel);
            }
            UStaticMeshComponent* Component = TileActor->GetStaticMeshComponent();
            UStaticMesh* StaticMesh = Component ? Component->GetStaticMesh() : nullptr;
            if (!StaticMesh || StaticMesh->GetPathName() != AssetPath)
            {
                return Fail(TEXT("Incorrect imported mesh for: ") + ActorLabel);
            }
            const FVector Expected(-2400.0 + 1600.0 * X, -1950.0 + 1300.0 * Y, 0.0);
            if (!TileActor->GetActorLocation().Equals(Expected, 0.01)
                || !TileActor->GetActorRotation().IsNearlyZero(0.01)
                || !TileActor->GetActorScale3D().Equals(FVector::OneVector, 0.0001))
            {
                return Fail(TEXT("Tile transform drifted: ") + ActorLabel);
            }
            const FMeshDescription* Description = StaticMesh->GetMeshDescription(0);
            if (!Description || Description->Triangles().Num() != TrianglesPerTile || Component->GetNumMaterials() != 2)
            {
                return Fail(TEXT("Tile geometry or material slots changed: ") + ActorLabel);
            }
            FPreparedTile& Tile = Prepared.AddDefaulted_GetRef();
            Tile.Actor = TileActor;
            FMeshDescriptionToDynamicMesh Converter;
            Converter.bUseCompactedPolygonGroupIDValues = true;
            Converter.Convert(Description, Tile.Mesh);
            if (Tile.Mesh.TriangleCount() != TrianglesPerTile)
            {
                return Fail(TEXT("MeshDescription conversion changed triangle count: ") + ActorLabel);
            }
            for (int32 MaterialIndex = 0; MaterialIndex < 2; ++MaterialIndex)
            {
                UMaterialInterface* Material = Component->GetMaterial(MaterialIndex);
                if (!Material)
                {
                    return Fail(TEXT("Missing terrain material: ") + ActorLabel);
                }
                Tile.Materials.Add(Material);
            }
            Tile.WorldBounds = FBox(Tile.Mesh.GetBounds()).TransformBy(TileActor->GetActorTransform());
        }
    }

    FActorSpawnParameters Params;
    Params.bCreateActorPackage = true;
    auto* Partition = World->SpawnActor<UE::MeshPartition::AMeshPartition>(
        UE::MeshPartition::AMeshPartition::StaticClass(), FTransform::Identity, Params);
    if (!Partition)
    {
        return Fail(TEXT("Could not spawn AMeshPartition"));
    }
    Partition->SetActorLabel(TEXT("MP_NyaagyuEstate_Research"));
    auto* EditorComponent = NewObject<UE::MeshPartition::UMeshPartitionEditorComponent>(
        Partition, UE::MeshPartition::UMeshPartitionEditorComponent::StaticClass(),
        TEXT("MeshPartitionEditorComponent"), RF_Transactional);
    Partition->SetMeshPartitionComponent(EditorComponent);
    Partition->SetMeshPartitionDefinition(Definition);

    TArray<FBox> Bounds;
    for (FPreparedTile& Tile : Prepared)
    {
        if (!EditorComponent->SpawnBaseModifier(MoveTemp(Tile.Mesh), Tile.Materials,
                                                 Tile.Actor->GetActorTransform()))
        {
            // Keep source actors intact so a partial build can be inspected and discarded.
            return Fail(TEXT("Failed to spawn a base modifier; discard this research map"));
        }
        Bounds.Add(Tile.WorldBounds);
    }
    EditorComponent->OnBoundsChanged(Bounds, UE::MeshPartition::EChangeType::StateChange);
    for (const FPreparedTile& Tile : Prepared)
    {
        World->DestroyActor(Tile.Actor);
    }
    World->GetOutermost()->MarkPackageDirty();
    UE_LOG(LogSoraMeshTerrainResearch, Display,
           TEXT("SORA_MESH_RESEARCH_CONVERT_COMPLETE: 16 HI base modifiers in one AMeshPartition"));
    return true;
}

bool USoraMeshTerrainResearchLibrary::VerifyCompiledSections()
{
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World || !World->GetWorldPartition() || World->GetOutermost()->GetName() != ResearchMap)
    {
        return Fail(TEXT("Compiled-section verification requires the research World Partition map"));
    }
    TArray<FWorldPartitionReference> LoadedActorReferences;
    World->GetWorldPartition()->LoadAllActors(LoadedActorReferences);

    int32 PartitionCount = 0;
    for (TActorIterator<UE::MeshPartition::AMeshPartition> It(World); It; ++It)
    {
        ++PartitionCount;
    }
    if (PartitionCount != 1)
    {
        return Fail(FString::Printf(TEXT("Expected one AMeshPartition, found %d"), PartitionCount));
    }

    int32 SectionCount = 0;
    TSet<FString> BaseModifierPaths;
    for (TActorIterator<UE::MeshPartition::ACompiledSection> It(World); It; ++It)
    {
        const UE::MeshPartition::ACompiledSection* Section = *It;
        const auto& Info = Section->GetBuildInfo();
        if (!Info.BuildKey.IsValid() || Info.BaseModifierPaths.IsEmpty())
        {
            return Fail(TEXT("Compiled section lacks a build key or base modifier provenance"));
        }
        TArray<UE::MeshPartition::UMeshPartitionStaticMeshComponent*> MeshComponents;
        Section->GetComponents(MeshComponents);
        bool bHasRuntimeMesh = false;
        for (const auto* Component : MeshComponents)
        {
            bHasRuntimeMesh |= Component && Component->GetStaticMesh() != nullptr;
        }
        if (!bHasRuntimeMesh)
        {
            return Fail(TEXT("Compiled section has no runtime static mesh"));
        }
        for (const FSoftObjectPath& Path : Info.BaseModifierPaths)
        {
            BaseModifierPaths.Add(Path.ToString());
        }
        ++SectionCount;
    }
    if (SectionCount == 0 || BaseModifierPaths.Num() != 16)
    {
        return Fail(FString::Printf(TEXT("Compiled sections=%d, covered base modifiers=%d; expected nonzero and 16"),
                                    SectionCount, BaseModifierPaths.Num()));
    }
    UE_LOG(LogSoraMeshTerrainResearch, Display,
           TEXT("SORA_MESH_RESEARCH_VERIFIED: %d compiled sections, 16 base modifiers, 1 partition"),
           SectionCount);
    return true;
}
