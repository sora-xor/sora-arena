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
}
void USoraFieldcraft::StageLedger(const FSoraBeat& Beat)
{
    if(Beat.Id!=TEXT("ch06.b06")||!Beat.Space.LedgerHall.bEnabled) return;
    LedgerSpace=&Beat.Space;
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
void USoraFieldcraft::TickLedger()
{
    if(!LedgerSpace) return;
    for(int I=0;I<4;++I)
    {
        const auto* Guard=LedgerAuditors[I].Get();
        const bool Lit=Guard&&Guard->IsAlive()&&!Guard->IsFreed()&&!Guard->IsSeized();
        if(auto* Light=LedgerLights[I].Get()) Light->PointLightComponent->SetVisibility(Lit);
        if(auto* Lens=LedgerLenses[I].Get()) Lens->SetVisibility(Lit);
    }
}
