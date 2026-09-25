#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraWorldBuilder.generated.h"
class UStaticMeshComponent;
class UMaterialInterface;
struct FSoraPracticeMap;
struct FSoraChapter;

// Builds the procedural arena at runtime. The shared layout (ground, walls,
// building rows, cover, torii, production sites and lanterns) lives in
// Private/World/SoraWorldBuilder.cpp; each map's dressing lives in its own
// Private/World/SoraMap*.cpp file, lighting in SoraWorldBuilderLighting.cpp,
// campaign beat objectives in SoraWorldBuilderLayout.cpp and the
// kernel-defined practice map in SoraWorldBuilderPractice.cpp. Authored props
// are visual only; the primitive boxes remain the gameplay collision.
UCLASS()
class SORAARENA_API ASoraWorldBuilder : public AActor
{
    GENERATED_BODY()
public:
    ASoraWorldBuilder();
    void Build(int32 MapId, const FSoraChapter* Chapter = nullptr);
    void BuildPractice(int32 MapId, const FSoraPracticeMap& Map);
    bool ActivateNearest(const FVector& Location);
    int32 NearestInactiveNode(const FVector& Location) const;
    int32 ActiveNodes() const { return Activated.Num(); }
    int32 ActivatedMask() const;
    void RestoreActivatedMask(int32 Mask);
    FVector SpawnPoint(int32 Index) const;
    // Campaign beat layout (SoraWorldBuilderLayout.cpp). A beat that restores a
    // production site stands at that site; every other beat's objective stands
    // on the central road, spread so consecutive beats move the hero. A beat
    // with several points (objectives, pickups and drop-offs, a dialogue's
    // closing anchor, the volumes that release waves) finds point N > 0 further
    // along the road. Explore beats hide an unmarked cache off the road, found
    // by its lantern glow.
    FVector BeatAnchor(int32 Beat, int32 Site) const;
    FVector TaskAnchor(int32 Beat, int32 Site, int32 Point) const;
    FVector CacheAnchor(int32 Beat) const;
    // Shows the marker over the active objective; nullptr hides it.
    void ShowObjective(const FVector* Location);
    void ShowCaches(const TArray<FVector>& Locations);
    // A site restored by its beat, wherever the hero stands.
    void ActivateSite(int32 Index);
    FVector ExitPoint() const { return FVector(2250,0,110); }
    // Begin far enough west of the entrance torii to frame the gate and
    // estate in first person instead of spawning with the camera under a beam.
    FVector PlayerStart() const { return FVector(-2700,0,120); }
    static UStaticMeshComponent* Shape(AActor* Owner, USceneComponent* Parent, const FString& Name, const TCHAR* Asset, FVector Location, FVector Scale, FLinearColor Color, bool Collision = false);
    static void Tint(UStaticMeshComponent* Mesh, FLinearColor Color);
    static void Surface(UStaticMeshComponent* Mesh, const FString& Role, FLinearColor Color = FLinearColor::White);
    TArray<FVector> NodePositions;
private:
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Pieces;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Nodes;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> SiteEffects;
    TArray<FLinearColor> SiteRestoredColors;
    UPROPERTY() TArray<TObjectPtr<AActor>> DecorActors;
    TSet<int32> Activated;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> ObjectiveMarker;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> CacheMarkers;
    UPROPERTY() TArray<TObjectPtr<AActor>> CacheLights;
    // Shared layout (SoraWorldBuilder.cpp).
    UStaticMeshComponent* Box(const FString& Name, FVector Location, FVector Size, FLinearColor Color, bool Collision = true, FRotator Rotation = FRotator::ZeroRotator, const FString& SurfaceRole = TEXT(""));
    void Building(FVector Location, FVector Size, FLinearColor Wall, bool HighTech);
    bool ImportedProp(const FString& Name, FVector Location, FRotator Rotation, float Scale = 1.f);
    void Torii(FVector Location, float Yaw);
    void ProductionSites(int32 MapId, const FSoraChapter* Chapter, FLinearColor Accent);
    void Lanterns();
    void ClearArena();
    // Sun, sky, fog and grade per map (SoraWorldBuilderLighting.cpp).
    void Lighting(int32 MapId);
    // Nyaagyu Estate, map 0 (SoraMapNyaagyuEstate.cpp).
    void NyaagyuTerrain();
    void NyaagyuTree(FVector Location, FRotator Rotation, float Scale);
    void NyaagyuPine(FVector Location, FRotator Rotation, float Scale, int32 Variant);
    void EstatePerimeter(int32 S, UStaticMeshComponent* WallX, UStaticMeshComponent* WallY);
    void EstateHall(int32 I, int32 S, FVector P, int32 BuildingStart);
    void EstateGrounds();
    void EstateCargo(int32 I, FVector Location, UStaticMeshComponent* Cover);
    void EstateSluice(FVector P);
    // Lantern Ward, map 1 (SoraMapLanternWard.cpp).
    void LanternWardTerminal();
    // Silk Foundry, map 2 (SoraMapSilkFoundry.cpp).
    void SilkFoundryLoom(FVector P);
    // Debt Citadel, map 3 (SoraMapDebtCitadel.cpp).
    void DebtCitadelKiosk();
};
