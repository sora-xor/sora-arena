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
// sites where their beats restore them. Authored buildings may also have
// raised floors; each beat's FloorAt resolves its interaction heights.
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
    const bool bTenements=Chapter.Beats.ContainsByPredicate([](const FSoraBeat& B){return B.Space.bTenements;});
    const bool bLanternWorkshop=Chapter.Beats.ContainsByPredicate([](const FSoraBeat& B){return B.Space.bLanternWorkshop;});
    if(Space.Hub!=INDEX_NONE) BuildArena(Space.Hub,false,bTenements,bLanternWorkshop);
    else Lighting(Chapter.Map);
    for(int32 Index=0;Index<Space.Zones.Num();++Index)
    {
        if(bTenements&&Space.Zones[Index].Id==TEXT("pl_ura_nagaya"))
        { BuildTenements();continue; }
        // This crossing already belongs to the hub; do not build a second walled yard.
        if(Chapter.Id==TEXT("ch03_lantern_ward")&&Space.Zones[Index].Id==TEXT("pl_kosatsuba"))continue;
        if(bLanternWorkshop&&Space.Zones[Index].Id==TEXT("pl_chochin_kobo"))
        { BuildLanternWorkshop();continue; }
        if(Chapter.Beats.ContainsByPredicate([Index](const FSoraBeat& B){return B.Space.Zone==Index&&B.Space.bLanding;}))
        { BuildLanding(Space.Zones[Index]);continue; }
        if(Chapter.Beats.ContainsByPredicate([Index](const FSoraBeat& B){return B.Space.Zone==Index&&B.Space.bWardGate;}))
        { BuildWardGate(Space.Zones[Index]);continue; }
        const FSoraBeat* Recovery=Chapter.Beats.FindByPredicate([Index](const FSoraBeat& B)
            { return B.Space.Zone==Index&&B.Task.RecoveryWeapons!=0u; });
        const FSoraBeat* Spire=Chapter.Beats.FindByPredicate([Index](const FSoraBeat& B)
            { return B.Space.Zone==Index&&B.Space.Spire.Enabled(); });
        const FSoraBeat* Summit=Chapter.Beats.FindByPredicate([Index](const FSoraBeat& B)
            { return B.Space.Zone==Index&&B.Space.Summit.Enabled(); });
        const FSoraBeat* Wind=Chapter.Beats.FindByPredicate([Index](const FSoraBeat& B)
            { return B.Space.Zone==Index&&B.Space.Wind.Enabled(); });
        const FSoraBeat* Flood=Chapter.Beats.FindByPredicate([Index](const FSoraBeat& B)
            { return B.Space.Zone==Index&&B.Space.Flood.bEnabled; });
        const FSoraBeat* Climb=Chapter.Beats.FindByPredicate([Index](const FSoraBeat& B)
            { return B.Space.Zone==Index&&B.Space.Climb.bEnabled; });
        const FSoraBeat* Moat=Chapter.Beats.FindByPredicate([Index](const FSoraBeat& B)
            { return B.Space.Zone==Index&&B.Space.Moat.bEnabled; });
        const FSoraBeat* Bridge=Chapter.Beats.FindByPredicate([Index](const FSoraBeat& B)
            { return B.Space.Zone==Index&&B.Space.Bridge.bEnabled; });
        const FSoraBeat* Relay=Chapter.Beats.FindByPredicate([Index](const FSoraBeat& B)
            { return B.Space.Zone==Index&&B.Space.RelayRoom.bEnabled; });
        const bool Archive=Chapter.Beats.ContainsByPredicate([Index](const FSoraBeat& B)
            { return B.Space.Zone==Index&&B.Id==TEXT("ch06.b09"); });
        const auto* PressZone=Archive?Space.Zones.FindByPredicate([](const FSoraZone& Z){return Z.Id==TEXT("pl_press_hall");}):nullptr;
        if(Space.Zones[Index].Id==TEXT("pl_ledger_corridors")) BuildLedger(Space.Zones[Index]);
        else if(Space.Zones[Index].Id==TEXT("pl_uguisu_hall")) BuildPalace(Space.Zones[Index]); else if(Archive&&PressZone) BuildArchive(Space.Zones[Index],*PressZone); else if(Relay) BuildRelayRoom(*Relay); else if(Bridge) BuildBridge(Space.Zones[Index],Index,*Bridge); else if(Moat) BuildMoat(*Moat); else if(Climb) BuildClimb(*Climb); else if(Wind) BuildWindSpace(*Wind); else if(Flood) BuildFlood(*Flood); else if(Spire) BuildSpire(*Spire); else if(Summit) BuildSummit(*Summit); else BuildZone(Space.Zones[Index],Index,Recovery);
    }
    BuildChapterWood(Chapter);
    NodePositions.Reset(); Nodes.Reset(); SiteEffects.Reset(); SiteRestoredColors.Reset();
    const FLinearColor Accent=FSoraCatalog::Get().Map(Chapter.Map).Accent;
    for(int32 Site=0;Site<Space.Sites.Num();++Site)
    {
        const auto* Workshop=Chapter.Beats.FindByPredicate([Site,&Space](const FSoraBeat& B)
            { return B.Space.bLanternWorkshop&&B.Space.Anchor==Space.Sites[Site]; });
        const FVector P=Floor(Space.Sites[Site],Workshop?Workshop->Space.FloorAt(Space.Sites[Site]):0.f);
        const int32 Zone=Space.ZoneAt(P);
        NodePositions.Add(P);
        if(Chapter.Beats.ContainsByPredicate([Zone](const FSoraBeat& B)
            { return B.Space.Zone==Zone&&(B.Space.RelayRoom.bEnabled||B.Space.RegistryHall.bEnabled||B.Space.bTenements||B.Space.bLanternWorkshop); }))
        {
            // The relay controls or registry desks own this site's physical work.
            // A second generic production pedestal would obstruct the exit.
            Nodes.SetNum(Site+1);SiteEffects.SetNum(Site+1);SiteRestoredColors.SetNum(Site+1);
            Nodes[Site]=Box(TEXT("AuthoredSiteMarker"),P+FVector(0,0,1),FVector(40,40,2),FLinearColor(.1f,.2f,.2f),false);
            SiteEffects[Site]=nullptr;SiteRestoredColors[Site]=FLinearColor(.07f,.62f,.53f);
            continue;
        }
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
