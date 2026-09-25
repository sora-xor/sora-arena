#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "SoraNavigation.generated.h"
class ANavMeshBoundsVolume;
class APawn;
class UNavigationSystemV1;

// A place beside one of the arena's low boxes where an opponent's body is
// hidden from anyone on the box's far side.
struct FSoraCoverSpot
{
    // On the navigation mesh, a body's width out from the face.
    FVector Location = FVector::ZeroVector;
    // Out of the face, and along it.
    FVector Normal = FVector::ForwardVector;
    FVector Tangent = FVector::RightVector;
    float HalfWidth = 0.f;
    // The box's footprint.
    FBox2D Box = FBox2D(ForceInit);
};

/**
 * The offline opponents' navigation. The arena is built from actors at
 * runtime, so there is no saved navigation mesh: this subsystem spawns a
 * NavMeshBoundsVolume sized to the built arena, registers it with the world's
 * navigation system (dynamic generation, Config/DefaultEngine.ini) and waits
 * for the mesh. Settle runs before an opponent's queries: queued geometry
 * changes, a rebuilt arena or a wall placed at runtime, are always complete
 * when a path is asked for, so paths never depend on worker-thread timing.
 * The arena's low boxes become cover spots.
 */
UCLASS()
class USoraNavigation : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    static USoraNavigation* Get(const UObject* WorldContext);
    // Brings the mesh up to date with the world; true when it is ready.
    bool Settle();
    bool IsReady() const;
    // A path along the mesh for Agent, including both ends; partial when To is
    // unreachable. False without a mesh or a path.
    bool FindPath(const FVector& From, const FVector& To, const APawn& Agent, TArray<FVector>& Points) const;
    bool Project(const FVector& Point, FVector& OnMesh) const;
    const TArray<FSoraCoverSpot>& CoverSpots() const { return Cover; }
    // The spot's box lies between the spot and Threat, on the side it faces.
    static bool Shields(const FSoraCoverSpot& Spot, const FVector& Threat);
    // The line from From to To crosses Box, seen from above.
    static bool Crosses(const FVector& From, const FVector& To, const FBox2D& Box);
    FBox CoveredBounds() const { return Covered; }
    // Complete rebuilds since the world began, for automation.
    int32 Rebuilds() const { return RebuildCount; }
protected:
    virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
private:
    UNavigationSystemV1* NavigationSystem();
    // The built arena: the extent of its colliding pieces and its low boxes.
    bool ScanArena(FBox& Bounds, TArray<FBox>& LowBoxes) const;
    void CoverArena(const FBox& Bounds);
    void GatherCover();
    UPROPERTY() TObjectPtr<ANavMeshBoundsVolume> Volume;
    FBox Covered = FBox(ForceInit);
    TArray<FBox> CoverBoxes;
    TArray<FSoraCoverSpot> Cover;
    uint64 ScannedFrame = MAX_uint64;
    int32 RebuildCount = 0;
    bool bReportedMissing = false;
};
