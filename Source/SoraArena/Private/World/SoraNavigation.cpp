#include "World/SoraNavigation.h"
#include "SoraGameMode.h"
#include "SoraWorldBuilder.h"
#include "AI/NavigationSystemBase.h"
#include "Components/BrushComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "NavigationData.h"
#include "NavigationSystem.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "PhysicsEngine/BodySetup.h"

namespace
{
// A cover spot stands a body's width off the box: the capsule's 34 cm radius
// and a little air, inside the mesh's own 34 cm margin from the face.
constexpr float StandOffCm = 60.f;
// Low cover stands between chest and head height, a few metres across and
// square to the arena, like the builder's cover boxes and cargo stacks.
bool IsLowBox(const FBox& Box, const FRotator& Rotation)
{
    const FVector Size = Box.GetSize();
    const float Quarter = FMath::Fmod(FMath::Abs(Rotation.Yaw), 90.f);
    return Size.Z >= 110.f && Size.Z <= 220.f && FMath::Max(Size.X, Size.Y) <= 450.f &&
        FMath::IsNearlyZero(Rotation.Pitch, 1.f) && FMath::IsNearlyZero(Rotation.Roll, 1.f) &&
        (Quarter <= 1.f || Quarter >= 89.f);
}
}

USoraNavigation* USoraNavigation::Get(const UObject* WorldContext)
{
    const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
    return World ? World->GetSubsystem<USoraNavigation>() : nullptr;
}

bool USoraNavigation::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
    return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

UNavigationSystemV1* USoraNavigation::NavigationSystem()
{
    UWorld* World = GetWorld();
    UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (World && (!NavSys || !NavSys->IsWorldInitDone()))
    {
        // A world loaded from a map already runs its navigation system. A
        // world created without one, such as an automation world, gets the
        // world settings' system here, initialized for play.
        FNavigationSystem::AddNavigationSystemToWorld(*World, FNavigationSystemRunMode::GameMode);
        NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    }
    if (!NavSys && !bReportedMissing)
    {
        bReportedMissing = true;
        UE_LOG(LogTemp, Error, TEXT("SORA navigation: this world has no navigation system, so opponents cannot find paths."));
    }
    return NavSys;
}

bool USoraNavigation::ScanArena(FBox& Bounds, TArray<FBox>& LowBoxes) const
{
    const ASoraGameMode* Mode = Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    const ASoraWorldBuilder* Arena = Mode ? Mode->Arena() : nullptr;
    if (!Arena)
        return false;
    Bounds = FBox(ForceInit);
    LowBoxes.Reset();
    // Only pieces that stop a body shape the mesh; visual props do not.
    Arena->ForEachComponent<UPrimitiveComponent>(false, [&Bounds, &LowBoxes](const UPrimitiveComponent* Piece)
    {
        if (!Piece->IsRegistered() || !Piece->IsCollisionEnabled() || Piece->GetCollisionResponseToChannel(ECC_Pawn) != ECR_Block)
            return;
        const FBox Box = Piece->Bounds.GetBox();
        Bounds += Box;
        if (IsLowBox(Box, Piece->GetComponentRotation()))
            LowBoxes.Add(Box);
    });
    if (!Bounds.IsValid)
        return false;
    Bounds = Bounds.ExpandBy(FVector(50.f, 50.f, 100.f));
    LowBoxes.Sort([](const FBox& A, const FBox& B)
    {
        return A.Min.X != B.Min.X ? A.Min.X < B.Min.X : A.Min.Y != B.Min.Y ? A.Min.Y < B.Min.Y : A.Min.Z < B.Min.Z;
    });
    return true;
}

void USoraNavigation::CoverArena(const FBox& Bounds)
{
    if (IsValid(Volume))
        Volume->Destroy();
    Volume = nullptr;
    Covered = FBox(ForceInit);
    const FTransform Center(Bounds.GetCenter());
    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    Params.ObjectFlags |= RF_Transient;
    ANavMeshBoundsVolume* Bounded = GetWorld()->SpawnActor<ANavMeshBoundsVolume>(ANavMeshBoundsVolume::StaticClass(), Center, Params);
    if (!Bounded)
        return;
    // A volume spawned at runtime has no editor brush, so it registered with
    // empty bounds. A box body gives its brush component the arena's extent,
    // and the queued registration is replaced with those bounds.
    UBrushComponent* Brush = Bounded->GetBrushComponent();
    UBodySetup* Body = NewObject<UBodySetup>(Brush, NAME_None, RF_Transient);
    const FVector Size = Bounds.GetSize();
    Body->AggGeom.BoxElems.Add(FKBoxElem(Size.X, Size.Y, Size.Z));
    Brush->BrushBodySetup = Body;
    Brush->UpdateBounds();
    if (UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
        NavSys->OnNavigationBoundsUpdated(Bounded);
    Volume = Bounded;
    Covered = Bounds;
    UE_LOG(LogTemp, Display, TEXT("SORA navigation bounds cover the arena: %s"), *Bounds.ToString());
}

bool USoraNavigation::Settle()
{
    UNavigationSystemV1* NavSys = NavigationSystem();
    if (!NavSys)
        return false;
    // Pieces registered since the last settle enter the octree now, so a
    // rebuilt arena or a wall placed at runtime shows up as dirty areas.
    NavSys->ProcessPendingOctreeUpdates();
    bool bRebuild = NavSys->HasDirtyAreasQueued() || !NavSys->GetDefaultNavDataInstance(FNavigationSystem::DontCreate);
    bool bRegatherCover = false;
    if (bRebuild || ScannedFrame != GFrameCounter || !IsValid(Volume))
    {
        ScannedFrame = GFrameCounter;
        FBox Bounds;
        TArray<FBox> LowBoxes;
        if (!ScanArena(Bounds, LowBoxes))
            return false;
        if (!IsValid(Volume) || !(Bounds == Covered))
        {
            CoverArena(Bounds);
            // The navigation system applies new bounds only in its own tick,
            // where it also creates a missing navmesh for them. Running that
            // tick once now registers the bounds before the mesh exists.
            NavSys->Tick(0.f);
            bRebuild = true;
        }
        if (LowBoxes != CoverBoxes)
        {
            CoverBoxes = MoveTemp(LowBoxes);
            bRegatherCover = true;
        }
    }
    if (bRebuild)
    {
        // Build spawns the missing mesh, registers it, gathers every bounds
        // volume, rebuilds from the current geometry and waits for the result.
        // The queued bounds requests and dirty areas it supersedes are dropped.
        NavSys->Build();
        ++RebuildCount;
        bRegatherCover = true;
    }
    else if (NavSys->IsNavigationBuildInProgress())
    {
        // The navigation system's own tick began rebuilding dirty tiles.
        for (ANavigationData* NavData : NavSys->NavDataSet)
            if (NavData)
                NavData->EnsureBuildCompletion();
    }
    if (bRegatherCover)
        GatherCover();
    return IsReady();
}

bool USoraNavigation::IsReady() const
{
    const UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    return NavSys && IsValid(Volume) && NavSys->GetDefaultNavDataInstance() != nullptr;
}

bool USoraNavigation::FindPath(const FVector& From, const FVector& To, const APawn& Agent, TArray<FVector>& Points) const
{
    Points.Reset();
    const UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    if (!NavSys || !IsValid(Volume))
        return false;
    const FNavAgentProperties& Props = Agent.GetNavAgentPropertiesRef();
    const ANavigationData* NavData = NavSys->GetNavDataForProps(Props, From);
    if (!NavData)
        return false;
    FPathFindingQuery Query(&Agent, *NavData, From, To, NavData->GetDefaultQueryFilter());
    Query.SetAllowPartialPaths(true).SetRequireNavigableEndLocation(false).SetNavAgentProperties(Props);
    const FPathFindingResult Result = const_cast<UNavigationSystemV1*>(NavSys)->FindPathSync(Props, Query);
    if (!Result.IsSuccessful() || !Result.Path.IsValid())
        return false;
    for (const FNavPathPoint& Point : Result.Path->GetPathPoints())
        Points.Add(Point.Location);
    return Points.Num() >= 2;
}

bool USoraNavigation::Project(const FVector& Point, FVector& OnMesh) const
{
    const UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    FNavLocation Location;
    if (!NavSys || !IsValid(Volume) ||
        !NavSys->ProjectPointToNavigation(Point, Location, FVector(60.f, 60.f, 200.f), NavSys->GetDefaultNavDataInstance()))
        return false;
    OnMesh = Location.Location;
    return true;
}

void USoraNavigation::GatherCover()
{
    Cover.Reset();
    static const FVector Normals[] = {FVector(1, 0, 0), FVector(-1, 0, 0), FVector(0, 1, 0), FVector(0, -1, 0)};
    for (const FBox& Box : CoverBoxes)
    {
        const FVector Center = Box.GetCenter();
        const FVector Extent = Box.GetExtent();
        for (const FVector& Normal : Normals)
        {
            const bool bAlongX = Normal.X != 0.f;
            FSoraCoverSpot Spot;
            Spot.Normal = Normal;
            Spot.Tangent = FVector(-Normal.Y, Normal.X, 0.f);
            Spot.HalfWidth = bAlongX ? Extent.Y : Extent.X;
            Spot.Box = FBox2D(FVector2D(Box.Min.X, Box.Min.Y), FVector2D(Box.Max.X, Box.Max.Y));
            const FVector Want = FVector(Center.X, Center.Y, Box.Min.Z + 60.f) + Normal * ((bAlongX ? Extent.X : Extent.Y) + StandOffCm);
            FVector OnMesh;
            // The spot must be walkable ground at the box's foot, not a roof or a gap.
            if (!Project(Want, OnMesh) || FVector::Dist2D(OnMesh, Want) > 25.f || FMath::Abs(OnMesh.Z - Box.Min.Z) > 60.f)
                continue;
            Spot.Location = OnMesh;
            Cover.Add(Spot);
        }
    }
}

bool USoraNavigation::Shields(const FSoraCoverSpot& Spot, const FVector& Threat)
{
    const FVector2D Toward = FVector2D(Threat.X - Spot.Location.X, Threat.Y - Spot.Location.Y).GetSafeNormal();
    return FVector2D::DotProduct(Toward, FVector2D(Spot.Normal.X, Spot.Normal.Y)) <= -.5f &&
        Crosses(Spot.Location, Threat, Spot.Box);
}

bool USoraNavigation::Crosses(const FVector& FromPoint, const FVector& ToPoint, const FBox2D& Box)
{
    // Slab test on the segment's parameter along each axis.
    const FVector2D From(FromPoint.X, FromPoint.Y);
    const FVector2D Delta = FVector2D(ToPoint.X, ToPoint.Y) - From;
    double Enter = 0.0, Exit = 1.0;
    for (int32 Axis = 0; Axis < 2; ++Axis)
    {
        const double Start = Axis ? From.Y : From.X;
        const double Step = Axis ? Delta.Y : Delta.X;
        const double Low = Axis ? Box.Min.Y : Box.Min.X;
        const double High = Axis ? Box.Max.Y : Box.Max.X;
        if (FMath::Abs(Step) < UE_KINDA_SMALL_NUMBER)
        {
            if (Start < Low || Start > High)
                return false;
            continue;
        }
        double A = (Low - Start) / Step, B = (High - Start) / Step;
        if (A > B)
            Swap(A, B);
        Enter = FMath::Max(Enter, A);
        Exit = FMath::Min(Exit, B);
        if (Enter > Exit)
            return false;
    }
    return true;
}
