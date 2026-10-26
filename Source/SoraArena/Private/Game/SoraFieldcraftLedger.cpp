#include "SoraFieldcraft.h"
#include "SoraEnemy.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"

void USoraFieldcraft::ClearLedger()
{
    for(int I=0;I<4;++I)
    {
        if(auto* Light=LedgerLights[I].Get()) Light->Destroy();
        LedgerLights[I].Reset();LedgerLenses[I].Reset();LedgerAuditors[I].Reset();
    }
    LedgerSpace=nullptr;
    LedgerShutter.Reset();LedgerSouthDoor.Reset();LedgerLockdown={};bLedgerShutterBlocked=false;
}
void USoraFieldcraft::StageLedger(const FSoraBeat& Beat)
{
    if(!Beat.Space.LedgerHall.bEnabled) return;
    LedgerSpace=&Beat.Space;
    namespace R=SoraLedgerRules;
    const FVector O(LedgerSpace->LedgerHall.Origin,0);
    // Construction roll-up leaves: their top edges stay fixed. Retraction
    // changes the hanging length, so the leaves never slide through a solid
    // ceiling. A fitted slatted shutter and motor/audio still need art.
    auto* Shutter=Piece(TEXT("LedgerC3Shutter"),SoraFieldcraftLayout::Cube,
        O+FVector(R::HallWidth*.5f,R::ShutterY,R::ShutterTop-R::ShutterRetractedHeight*.5f),
        FVector(R::HallWidth,R::ShutterThickness,R::ShutterRetractedHeight)/100.f,FLinearColor(.035f,.065f,.08f),true);
    Shutter->SetMobility(EComponentMobility::Movable);Shutter->ComponentTags.Add(TEXT("LedgerC3Shutter"));
    LedgerShutter=Shutter;
    auto* Door=Piece(TEXT("LedgerSouthDoor"),SoraFieldcraftLayout::Cube,O+FVector(1160,-10,125),
        FVector(R::SouthDoorRight-R::SouthDoorLeft,8,250)/100.f,FLinearColor(.035f,.065f,.08f),true);
    Door->SetMobility(EComponentMobility::Movable);Door->ComponentTags.Add(TEXT("LedgerSouthDoor"));
    LedgerSouthDoor=Door;
    if(Beat.Id!=TEXT("ch06.b06")) return;
    const FLinearColor Cold(.45f,.8f,1.f);
    for(int I=0;I<4;++I)
    {
        const FVector At(LedgerSpace->Spawns[I],110);
        auto* Lens=Piece(TEXT("LedgerCarriedLens"),SoraFieldcraftLayout::Sphere,At,FVector(.12f),Cold,false);
        Lens->SetMobility(EComponentMobility::Movable);Lens->SetVisibility(false);
        Lens->ComponentTags.Add(TEXT("LedgerCarriedLens"));LedgerLenses[I]=Lens;
        FActorSpawnParameters Params;Params.Owner=Props;
        Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Light=GetWorld()->SpawnActor<APointLight>(At,FRotator::ZeroRotator,Params);
        if(Light)
        {
            Light->Tags.Add(TEXT("LedgerCarriedLamp"));Light->SetMobility(EComponentMobility::Movable);
            auto* Component=Light->PointLightComponent.Get();
            Component->SetLightColor(Cold);Component->SetIntensity(1200.f);
            Component->SetAttenuationRadius(450.f);Component->SetCastShadows(true);Component->SetVisibility(false);
            LedgerLights[I]=Light;
        }
    }
    // A small lens marks the functional source light. A fitted handheld
    // housing and hand animation still require the authored auditor asset.
}
void USoraFieldcraft::AssignLedgerAuditor(ASoraEnemy& Guard,int32 Index)
{
    if(LedgerSpace&&Index>=0&&Index<4)
    {
        LedgerAuditors[Index]=&Guard;
        const FVector Offset(20,-30,20);
        if(auto* Light=LedgerLights[Index].Get())
        {
            Light->AttachToComponent(Guard.GetRootComponent(),FAttachmentTransformRules::KeepWorldTransform);
            Light->SetActorRelativeLocation(Offset);
        }
        if(auto* Lens=LedgerLenses[Index].Get())
        {
            Lens->AttachToComponent(Guard.GetRootComponent(),FAttachmentTransformRules::KeepWorldTransform);
            Lens->SetRelativeLocation(Offset);
        }
        TickLedger();
    }
}
bool USoraFieldcraft::LedgerLampLit(int32 Index) const
{
    const auto* Light=LedgerSpace&&Index>=0&&Index<4?LedgerLights[Index].Get():nullptr;
    return Light&&Light->PointLightComponent->IsVisible();
}
void USoraFieldcraft::TickLedger(int32 DeltaMs)
{
    if(!LedgerSpace) return;
    for(int I=0;I<4;++I)
    {
        const auto* Guard=LedgerAuditors[I].Get();
        const bool Lit=Guard&&Guard->IsAlive()&&!Guard->IsFreed()&&!Guard->IsSeized();
        if(auto* Light=LedgerLights[I].Get()) Light->PointLightComponent->SetVisibility(Lit);
        if(auto* Lens=LedgerLenses[I].Get()) Lens->SetVisibility(Lit);
    }
    if(DeltaMs<=0) return;
    namespace R=SoraLedgerRules;
    if(LedgerLockdown.Phase==R::ELockdown::Dormant||LedgerLockdown.Phase==R::ELockdown::Finished) return;
    auto* Shutter=LedgerShutter.Get();auto* Door=LedgerSouthDoor.Get();
    if(!Shutter||!Door) return;
    const FVector O(LedgerSpace->LedgerHall.Origin,0);
    R::FLockdown Next=LedgerLockdown;
    R::TickLockdown(Next,DeltaMs,false);
    const float Height=R::ShutterRetractedHeight+(R::ShutterTop-R::ShutterRetractedHeight)*
        (static_cast<float>(Next.TravelMs)/R::ShutterTravelMs);
    const FVector At=O+FVector(R::HallWidth*.5f,R::ShutterY,R::ShutterTop-Height*.5f);
    bLedgerShutterBlocked=false;
    if(Next.TravelMs>LedgerLockdown.TravelMs)
    {
        // The target box contains the entire swept volume of a descending
        // roll-up leaf. Stop before touching any live or downed pawn.
        FCollisionObjectQueryParams Objects(ECC_Pawn);
        FCollisionQueryParams Query(SCENE_QUERY_STAT(LedgerShutterOccupancy),false,Props);
        bLedgerShutterBlocked=GetWorld()->OverlapAnyTestByObjectType(At,FQuat::Identity,Objects,
            FCollisionShape::MakeBox(FVector(R::HallWidth,R::ShutterThickness,Height)*.5f+FVector(.5f)),Query);
    }
    const auto Previous=LedgerLockdown.Phase;
    if(bLedgerShutterBlocked) R::TickLockdown(LedgerLockdown,DeltaMs,true);
    else
    {
        LedgerLockdown=Next;
        Shutter->SetWorldScale3D(FVector(R::HallWidth,R::ShutterThickness,Height)/100.f);
        Shutter->SetWorldLocation(At);
    }
    const float DoorHeight=250.f-246.f*LedgerLockdown.EntranceMs/R::EntranceOpenMs;
    Door->SetWorldScale3D(FVector(R::SouthDoorRight-R::SouthDoorLeft,8,DoorHeight)/100.f);
    Door->SetWorldLocation(O+FVector(1160,-10,250-DoorHeight*.5f));
    if(Previous!=LedgerLockdown.Phase)
    {
        if(LedgerLockdown.Phase==R::ELockdown::Holding) Raise(TEXT("ledger_shutter:closed"));
        else if(LedgerLockdown.Phase==R::ELockdown::Finished) Raise(TEXT("ledger_shutter:opened"));
    }
}
