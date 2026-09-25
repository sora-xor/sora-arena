#include "SoraWorldBuilder.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"

namespace
{
// The central road between the torii, clear of lantern posts (y 470), cover
// (y 590 and beyond), the Lantern Ward terminal and every production site.
const FVector RoadAnchors[] = {
    FVector(-1650,220,0), FVector(-1250,-220,0), FVector(-850,220,0), FVector(-400,-220,0), FVector(0,220,0),
    FVector(400,-220,0), FVector(850,220,0), FVector(1250,-220,0), FVector(1650,220,0), FVector(2050,-220,0)};
// Gaps between the building rows of every map, away from sites and cover.
const FVector CacheAnchors[] = {
    FVector(-1500,1100,0), FVector(500,-1100,0), FVector(1500,1100,0), FVector(-500,-1100,0)};
}

FVector ASoraWorldBuilder::BeatAnchor(int32 Beat,int32 Site) const
{
    if(NodePositions.IsValidIndex(Site)) return NodePositions[Site];
    // Three steps per beat: consecutive objectives sit about 12 m apart.
    return RoadAnchors[(FMath::Max(Beat,0)*3)%UE_ARRAY_COUNT(RoadAnchors)];
}
FVector ASoraWorldBuilder::CacheAnchor(int32 Beat) const
{
    return CacheAnchors[FMath::Max(Beat,0)%UE_ARRAY_COUNT(CacheAnchors)];
}
void ASoraWorldBuilder::ShowObjective(const FVector* Location)
{
    if(!Location)
    {
        if(ObjectiveMarker) ObjectiveMarker->SetVisibility(false);
        return;
    }
    if(!ObjectiveMarker)
    {
        // A slim gold beacon: visible across the arena, never collision.
        ObjectiveMarker=Shape(this,RootComponent,TEXT("ObjectiveMarker"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
            FVector::ZeroVector,FVector(.22f,.22f,3.2f),FLinearColor(.94f,.65f,.21f));
        ObjectiveMarker->SetCastShadow(false);
    }
    ObjectiveMarker->SetRelativeLocation(*Location+FVector(0,0,160));
    ObjectiveMarker->SetVisibility(true);
}
void ASoraWorldBuilder::ShowCaches(const TArray<FVector>& Locations)
{
    for(const auto& Marker:CacheMarkers) if(Marker) Marker->DestroyComponent();
    for(const auto& Light:CacheLights) if(Light) Light->Destroy();
    CacheMarkers.Reset(); CacheLights.Reset();
    for(int32 I=0;I<Locations.Num();++I)
    {
        // No map marker (bible §12.2): a small chest and a warm lantern glow.
        auto* Chest=Shape(this,RootComponent,FString::Printf(TEXT("ExploreCache%d"),I),TEXT("/Engine/BasicShapes/Cube.Cube"),
            Locations[I]+FVector(0,0,22),FVector(.6f,.42f,.44f),FLinearColor(.36f,.21f,.09f));
        Surface(Chest,TEXT("Timber"),FLinearColor(.72f,.58f,.42f));
        CacheMarkers.Add(Chest);
        if(UWorld* World=GetWorld())
            if(auto* Light=World->SpawnActor<APointLight>(Locations[I]+FVector(0,0,120),FRotator::ZeroRotator))
            {
                auto* Glow=Light->PointLightComponent.Get();
                Glow->SetIntensityUnits(ELightUnits::Lumens);
                Glow->SetIntensity(260.f);
                Glow->SetAttenuationRadius(420.f);
                Glow->SetUseTemperature(true);
                Glow->SetTemperature(2300.f);
                Glow->SetCastShadows(false);
                CacheLights.Add(Light);
            }
    }
}
void ASoraWorldBuilder::ActivateSite(int32 Index)
{
    if(!Nodes.IsValidIndex(Index)||!IsValid(Nodes[Index])) return;
    Activated.Add(Index); Tint(Nodes[Index],FLinearColor(.05f,.75f,.5f));
    if(SiteEffects.IsValidIndex(Index)&&IsValid(SiteEffects[Index])) Tint(SiteEffects[Index],SiteRestoredColors[Index]);
}
