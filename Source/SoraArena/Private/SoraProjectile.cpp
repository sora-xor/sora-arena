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
    if(bArrow) Collision->SetSphereRadius(2.f);
    if(bArrow)
    {
        ASoraWorldBuilder::Shape(this,RootComponent,TEXT("ArrowShaft"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
            FVector(-21,0,0),FVector(.012f,.012f,.52f),FLinearColor(.45f,.23f,.07f))->SetRelativeRotation(FRotator(90,0,0));
        ASoraWorldBuilder::Shape(this,RootComponent,TEXT("ArrowHead"),TEXT("/Engine/BasicShapes/Cone.Cone"),
            FVector(10,0,0),FVector(.055f,.055f,.11f),FLinearColor(.66f,.70f,.74f))->SetRelativeRotation(FRotator(90,0,0));
    }
    else
        ASoraWorldBuilder::Shape(this,RootComponent,TEXT("Shell"),TEXT("/Engine/BasicShapes/Sphere.Sphere"),FVector::ZeroVector,FVector(.18),FLinearColor(1,.32,.04));
}
void ASoraProjectile::Tick(float Dt)
{
    Super::Tick(Dt); Age+=Dt; Velocity.Z-=(bArrow?980.f:420.f)*Dt;
    if(bArrow) SetActorRotation(Velocity.Rotation());
    FHitResult Hit; AddActorWorldOffset(Velocity*Dt,true,&Hit);
    if(bArrow)
    {
        if(Hit.bBlockingHit)
        {
            if(Hit.GetActor()&&Hit.GetActor()!=GetOwner())
                UGameplayStatics::ApplyPointDamage(Hit.GetActor(),Damage,Velocity.GetSafeNormal(),Hit,
                    GetInstigatorController(),this,UDamageType::StaticClass());
            Destroy();
        }
        else if(Age>2.f) Destroy();
    }
    else if(Hit.bBlockingHit||Age>4.f) Detonate();
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
