#include "SoraWorldBuilder.h"
#include "SoraCatalog.h"
#include "SoraFoundryFurnace.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
ASoraFoundryFurnace* ASoraWorldBuilder::FoundryTarget() const { return FoundryActor.Get(); }
void ASoraWorldBuilder::BuildFoundryDefense(const FSoraBeatSpace& Space)
{
    if(!Space.FoundryDefense.bEnabled) return;
    FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Furnace=GetWorld()->SpawnActor<ASoraFoundryFurnace>(FVector(Space.Targets[0],110),FRotator::ZeroRotator,Params);
    FoundryActor=Furnace;
    if(Furnace) { KitActors.Add(Furnace); Tint(Furnace->Shell(),FLinearColor(.25,.22,.2)); }
    for(const FVector2D& Crew:Space.FoundryDefense.Crew)
    {
        // A fixed base collides; the working tread is a movable visual, so
        // bellows motion does not rebuild navigation every frame.
        KitShape(TEXT("BellowsBase"),TEXT("/Engine/BasicShapes/Cube.Cube"),FVector(Crew+FVector2D(0,120),6),
            FVector(.7,1,.12),FLinearColor(.35,.20,.09),TEXT("Timber"),true);
        auto* Tread=KitShape(TEXT("WorkingBellows"),TEXT("/Engine/BasicShapes/Cube.Cube"),FVector(Crew+FVector2D(0,120),18),
            FVector(.7,1,.16),FLinearColor(.35,.20,.09),TEXT("Timber"));
        Tread->SetMobility(EComponentMobility::Movable); FoundryBellows.Add(Tread);
    }
    for(const FVector2D& Tub:Space.FoundryDefense.Tubs)
    {
        FoundryTubs.Add(KitShape(TEXT("FiniteClayTub"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),FVector(Tub,25),
            FVector(.7,.7,.5),FLinearColor(.47,.28,.12),TEXT("Timber"),true));
        KitShape(TEXT("ClayTubRim"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),FVector(Tub,52),
            FVector(.75,.75,.06),FLinearColor(.25,.16,.08));
    }
}
void ASoraWorldBuilder::ShowFoundrySupplies(unsigned Used,unsigned Netted)
{
    for(int32 I=0;I<FoundryBellows.Num();++I) if(auto* Bellows=FoundryBellows[I].Get())
    {
        FVector At=Bellows->GetRelativeLocation();
        At.Z=(Netted&(1u<<I))?18.f:18.f+5.f*FMath::Sin(GetWorld()->GetTimeSeconds()*3.f+I*PI);
        Bellows->SetRelativeLocation(At);
    }
    if(Used==FoundryUsedShown) return;
    FoundryUsedShown=Used;
    for(int32 I=0;I<FoundryTubs.Num();++I) if(auto* Tub=FoundryTubs[I].Get())
        Tint(Tub,(Used&(1u<<I))?FLinearColor(.16,.12,.08):FLinearColor(.47,.28,.12));
}
