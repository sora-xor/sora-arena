#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "Algo/AllOf.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"

// A chapter's space (FSoraSpace, scripts/unreal/campaign_space.py): the hub
// arena when one of its places is the arena itself, a walled zone for every
// other place and a corridor for every ride and escort
// (SoraWorldBuilderLayoutZones.cpp), and the chapter's three production
// sites where their beats restore them. Every floor is at z 0, so a point of
// the space is a location on the ground.
namespace
{
// The arena map whose dressing a zone's style borrows.
int32 ZoneStyleMap(FName Style)
{
    return Style==TEXT("ward")?1:Style==TEXT("foundry")?2:Style==TEXT("citadel")?3:0;
}
}

void ASoraWorldBuilder::BuildCampaign(const FSoraChapter& Chapter)
{
    const FSoraSpace& Space=Chapter.Space;
    RecoveryHatch=nullptr;
    // The hub arena brings its own light; a chapter without one is lit as its map.
    if(Space.Hub!=INDEX_NONE) BuildArena(Space.Hub,false);
    else Lighting(Chapter.Map);
    for(int32 Index=0;Index<Space.Zones.Num();++Index)
    {
        const FSoraBeat* Recovery=Chapter.Beats.FindByPredicate([Index](const FSoraBeat& B)
            { return B.Space.Zone==Index&&B.Task.RecoveryWeapons!=0u; });
        const FSoraBeat* Spire=Chapter.Beats.FindByPredicate([Index](const FSoraBeat& B)
            { return B.Space.Zone==Index&&B.Space.Spire.Enabled(); });
        const FSoraBeat* Summit=Chapter.Beats.FindByPredicate([Index](const FSoraBeat& B)
            { return B.Space.Zone==Index&&B.Space.Summit.Enabled(); });
        if(Spire) BuildSpire(*Spire); else if(Summit) BuildSummit(*Summit); else BuildZone(Space.Zones[Index],Index,Recovery);
    }
    NodePositions.Reset(); Nodes.Reset(); SiteEffects.Reset(); SiteRestoredColors.Reset();
    const FLinearColor Accent=FSoraCatalog::Get().Map(Chapter.Map).Accent;
    for(int32 Site=0;Site<Space.Sites.Num();++Site)
    {
        const FVector P=Floor(Space.Sites[Site]);
        const int32 Zone=Space.ZoneAt(P);
        NodePositions.Add(P);
        SiteStructure(Site,P,Chapter.Sites[Site].Kind,Space.Zones.IsValidIndex(Zone)?ZoneStyleMap(Space.Zones[Zone].Style):Chapter.Map,Accent);
    }
    // The hero stands a capsule's height above the floor at the first beat's entry.
    bCampaignSpace=true;
    CampaignStart=Floor(Space.Start,120.f);
    CampaignStartYaw=Space.StartYaw;
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
        // A slim gold beacon: visible across the zone, never collision.
        ObjectiveMarker=Shape(this,RootComponent,TEXT("ObjectiveMarker"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
            FVector::ZeroVector,FVector(.22f,.22f,3.2f),FLinearColor(.94f,.65f,.21f));
        ObjectiveMarker->SetCastShadow(false);
    }
    ObjectiveMarker->SetRelativeLocation(*Location+FVector(0,0,160.f));
    ObjectiveMarker->SetVisibility(true);
}
void ASoraWorldBuilder::ShowCaches(const TArray<FVector>& Locations)
{
    // The objective refreshes whenever a task's progress moves (many times a
    // second while a hold fills or an escort walks); caches that already
    // stand where they are asked for stay, so nothing is rebuilt for them.
    const auto Standing=[](const auto& Part) { return IsValid(Part); };
    if(Locations==CacheLocations&&CacheMarkers.Num()==Locations.Num()&&Algo::AllOf(CacheMarkers,Standing)&&
        Algo::AllOf(CacheLights,Standing))
        return;
    for(const auto& Marker:CacheMarkers) if(Marker) Marker->DestroyComponent();
    for(const auto& Light:CacheLights) if(Light) Light->Destroy();
    CacheMarkers.Reset(); CacheLights.Reset();
    CacheLocations=Locations;
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
