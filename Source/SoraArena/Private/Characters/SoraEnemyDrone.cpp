#include "SoraEnemy.h"
#include "SoraCollision.h"
#include "SoraDroneRules.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSocket.h"
#include "PhysicsEngine/BodySetup.h"

void ASoraEnemy::ConfigureBodyCollision()
{
    auto* Capsule=GetCapsuleComponent();
    const bool Drone=IsFlying();
    Capsule->SetCapsuleSize(Drone?SoraDroneRules::MovementRadiusCm:34.f,
        Drone?SoraDroneRules::MovementRadiusCm:88.f);
    Capsule->SetCollisionResponseToChannel(ECC_Visibility,Drone?ECR_Ignore:ECR_Block);
    Capsule->SetCollisionResponseToChannel(SoraCollision::Projectile,Drone?ECR_Ignore:ECR_Block);
}

bool ASoraEnemy::BuildSpecialBody()
{
    DroneBody=nullptr;
    if(!IsFlying()) return false;
    const TCHAR* Path=TEXT("/Game/Generated/Characters/Enemies/InventoryDrone/SM_Drone_Inventory.SM_Drone_Inventory");
    auto* Asset=LoadObject<UStaticMesh>(nullptr,Path,nullptr,LOAD_NoWarn);
    const auto* Setup=Asset?Asset->GetBodySetup():nullptr;
    bool Valid=Asset&&Setup&&Setup->AggGeom.ConvexElems.Num()==3&&Setup->AggGeom.GetElementCount()==3&&
        Setup->CollisionTraceFlag!=CTF_UseComplexAsSimple;
    for(const FName Name:{FName(TEXT("Eye")),FName(TEXT("NetMuzzle"))})
    {
        const auto* Socket=Asset?Asset->FindSocket(Name):nullptr;
        Valid=Valid&&Socket&&!Socket->RelativeLocation.ContainsNaN()&&!Socket->RelativeRotation.ContainsNaN()&&
            Socket->RelativeScale.Equals(FVector::OneVector,1e-4);
    }
    if(!Valid)
    {
        UE_LOG(LogTemp,Error,TEXT("Inventory drone requires its imported disc, convex hit hulls and Eye/NetMuzzle sockets: %s"),Path);
        // Do not silently substitute the humanoid or an invisible hit sphere.
        // InitArchetype rejects this spawn when DroneBody remains null.
        return true;
    }
    auto* Mesh=NewObject<UStaticMeshComponent>(this,MakeUniqueObjectName(this,UStaticMeshComponent::StaticClass(),TEXT("InventoryDroneBody")));
    Mesh->SetCanEverAffectNavigation(false);
    Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Mesh->SetCollisionObjectType(ECC_Pawn);
    Mesh->SetCollisionResponseToAllChannels(ECR_Ignore);
    Mesh->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    Mesh->SetCollisionResponseToChannel(SoraCollision::Projectile,ECR_Block);
    Mesh->SetGenerateOverlapEvents(false);
    Mesh->SetStaticMesh(Asset);
    Mesh->SetupAttachment(GetCapsuleComponent());
    Mesh->SetRelativeTransform(FTransform::Identity);
    Mesh->ComponentTags.Add(TEXT("InventoryDroneBody"));
    Mesh->RegisterComponent();AddInstanceComponent(Mesh);BodyParts.Add(Mesh);
    DroneBody=Mesh;
    return true;
}
