#include "SoraProjectile.h"
#include "SoraWorldBuilder.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/Pawn.h"
#include "Engine/World.h"

ASoraProjectile::ASoraProjectile()
{
    PrimaryActorTick.bCanEverTick=true;
    Collision=CreateDefaultSubobject<USphereComponent>(TEXT("ProjectileCollision")); RootComponent=Collision;
    Collision->InitSphereRadius(9); Collision->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Collision->SetCollisionResponseToAllChannels(ECR_Block); Collision->SetCollisionObjectType(ECC_WorldDynamic);
}
void ASoraProjectile::BeginPlay()
{
    Super::BeginPlay(); Collision->IgnoreActorWhenMoving(GetOwner(),true);
    ASoraWorldBuilder::Shape(this,RootComponent,TEXT("Shell"),TEXT("/Engine/BasicShapes/Sphere.Sphere"),FVector::ZeroVector,FVector(.18),FLinearColor(1,.32,.04));
}
void ASoraProjectile::Tick(float Dt)
{
    Super::Tick(Dt); Age+=Dt; Velocity.Z-=420.f*Dt;
    FHitResult Hit; AddActorWorldOffset(Velocity*Dt,true,&Hit);
    if(Hit.bBlockingHit||Age>4.f) Detonate();
}
void ASoraProjectile::Detonate()
{
    TArray<AActor*> Ignore;
    UGameplayStatics::ApplyRadialDamage(this,Damage,GetActorLocation(),Radius,UDamageType::StaticClass(),Ignore,this,GetInstigatorController(),false,ECC_Visibility);
    auto* Effect=GetWorld()->SpawnActor<AActor>(GetActorLocation(),FRotator::ZeroRotator);
    auto* Sphere=ASoraWorldBuilder::Shape(Effect,nullptr,TEXT("Blast"),TEXT("/Engine/BasicShapes/Sphere.Sphere"),FVector::ZeroVector,FVector(Radius/110.f),FLinearColor(1,.22,.025));
    Effect->SetRootComponent(Sphere); Effect->SetActorLocation(GetActorLocation()); Effect->SetLifeSpan(.12f);
    Destroy();
}
