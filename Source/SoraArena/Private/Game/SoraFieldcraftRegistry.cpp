#include "SoraFieldcraft.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "Game/SoraFieldcraftLayout.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

void USoraFieldcraft::ClearRegistry()
{
    for(int I=0;I<3;++I)
    {
        if(auto* Light=RegistryLights[I].Get()) Light->Destroy();
        RegistryLights[I].Reset();RegistryLenses[I].Reset();RegistryAuditors[I].Reset();
    }
    RegistrySpace=nullptr;
}
void USoraFieldcraft::StageRegistry(const FSoraBeat& Beat)
{
    if(Beat.Id!=TEXT("ch06.b08")||!Beat.Space.RegistryHall.bEnabled) return;
    RegistrySpace=&Beat.Space;
    const FLinearColor Metal(.025f,.045f,.055f),Cold(.45f,.8f,1.f);
    for(int I=0;I<3;++I)
    {
        const FVector Desk(RegistrySpace->Objectives[I]+FVector2D(0,110),
            RegistrySpace->FloorAt(RegistrySpace->Objectives[I]));
        const FVector Lens=Desk+FVector(46,12,128);
        Piece(TEXT("RegistryLampBase"),SoraFieldcraftLayout::Cube,Desk+FVector(46,12,75),FVector(.18f,.16f,.06f),Metal,false);
        Piece(TEXT("RegistryLampStem"),SoraFieldcraftLayout::Cube,Desk+FVector(46,12,100),FVector(.04f,.04f,.5f),Metal,false);
        Piece(TEXT("RegistryLampShade"),SoraFieldcraftLayout::Cube,Lens+FVector(0,0,3),FVector(.24f,.18f,.06f),Metal,false);
        auto* Glow=Piece(TEXT("RegistryLampLens"),SoraFieldcraftLayout::Cube,Lens,FVector(.2f,.14f,.02f),Cold,false);
        Glow->ComponentTags.Add(TEXT("RegistryLampLens"));Glow->SetVisibility(false);RegistryLenses[I]=Glow;
        FActorSpawnParameters Params;Params.Owner=Props;
        Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Light=GetWorld()->SpawnActor<APointLight>(Lens-FVector(0,0,4),FRotator::ZeroRotator,Params);
        if(Light)
        {
            Light->Tags.Add(TEXT("RegistryDeskLamp"));Light->SetMobility(EComponentMobility::Movable);
            auto* Component=Light->PointLightComponent;
            Component->SetLightColor(Cold);Component->SetIntensity(1200.f);
            Component->SetAttenuationRadius(300.f);Component->SetCastShadows(true);Component->SetVisibility(false);
            RegistryLights[I]=Light;
        }
    }
}
void USoraFieldcraft::AssignRegistryAuditor(ASoraEnemy& Guard,int32 Index)
{
    if(RegistrySpace&&Index>=0&&Index<3) RegistryAuditors[Index]=&Guard;
}
ASoraEnemy* USoraFieldcraft::RegistryAuditor(int32 Index) const
{ return RegistrySpace&&Index>=0&&Index<3?RegistryAuditors[Index].Get():nullptr; }
bool USoraFieldcraft::RegistryLampLit(int32 Index) const
{
    const auto* Light=RegistrySpace&&Index>=0&&Index<3?RegistryLights[Index].Get():nullptr;
    return Light&&Light->PointLightComponent->IsVisible();
}
void USoraFieldcraft::TickRegistry()
{
    if(!RegistrySpace) return;
    for(int I=0;I<3;++I)
    {
        const auto* Guard=RegistryAuditors[I].Get();
        const auto* Brain=Guard?Cast<ASoraEnemyController>(Guard->GetController()):nullptr;
        bool Lit=Guard&&Guard->IsAlive()&&!Guard->IsFreed()&&!Guard->IsSeized()&&!Guard->IsStaggered()&&
            Brain&&Brain->IsPatrolPausedAt(0)&&Guard->GetCharacterMovement()->IsMovingOnGround();
        if(Lit)
        {
            const FVector Work(RegistrySpace->Objectives[I],RegistrySpace->FloorAt(RegistrySpace->Objectives[I]));
            const FVector Feet=Guard->GetActorLocation()-FVector(0,0,Guard->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
            Lit=FVector::Dist2D(Feet,Work)<=80.f&&FMath::Abs(Feet.Z-Work.Z)<=5.f;
        }
        if(auto* Light=RegistryLights[I].Get()) Light->PointLightComponent->SetVisibility(Lit);
        if(auto* Lens=RegistryLenses[I].Get()) Lens->SetVisibility(Lit);
    }
}
