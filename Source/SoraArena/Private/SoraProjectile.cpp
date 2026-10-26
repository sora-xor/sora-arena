#include "SoraProjectile.h"
#include "SoraCollision.h"
#include "Combat/SoraDamage.h"
#include "SoraCombatRules.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraCampaignDirector.h"
#include "SoraWorldBuilder.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/Pawn.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

ASoraProjectile::ASoraProjectile()
{
    PrimaryActorTick.bCanEverTick=true;
    Collision=CreateDefaultSubobject<USphereComponent>(TEXT("ProjectileCollision")); RootComponent=Collision;
    Collision->InitSphereRadius(9); Collision->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Collision->SetCollisionResponseToAllChannels(ECR_Block); Collision->SetCollisionObjectType(SoraCollision::Projectile);
    // A shell or arrow in flight is not terrain: it must never dirty the
    // opponents' navigation mesh.
    Collision->SetCanEverAffectNavigation(false);
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
    Super::Tick(Dt);
    if(bDetonated) return;
    if(bHorseShell&&!HorseShellCurrent()) { Destroy(); return; }
    const auto* Mode=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
    if(Mode&&Mode->InputState()==SoraInput::Dialogue) return;
    if((ArcheryShotId||WoodShotId||bHorseShell)&&Mode&&!Mode->IsPlaying()) return;
    if(Mode&&Mode->Campaign()) Velocity+=Mode->Campaign()->ProjectileWind(GetActorLocation(),bArrow,WeaponId)*Dt;
    Age+=Dt; Velocity.Z-=(bArrow?980.f:Gravity)*Dt;
    if(bArrow) SetActorRotation(Velocity.Rotation());
    const FVector Before=GetActorLocation();
    FHitResult Hit; AddActorWorldOffset(Velocity*Dt,true,&Hit);
    Traveled+=FVector::Dist(Before,GetActorLocation());
    if(bArrow)
    {
        if(Hit.bBlockingHit)
        {
            if((ArcheryShotId||WoodShotId)&&Mode) Mode->Campaign()->ResolveArcheryArrow(*this,&Hit);
            if(Hit.GetActor()&&Hit.GetActor()!=GetOwner())
                SoraDamage::Strike(Hit.GetActor(),Damage,FSoraHit::Ranged(Before,WeaponId),Velocity.GetSafeNormal(),Hit,
                    GetInstigatorController(),this);
            Destroy();
        }
        else if(Age>2.f)
        {
            if((ArcheryShotId||WoodShotId)&&Mode) Mode->Campaign()->ResolveArcheryArrow(*this,nullptr);
            Destroy();
        }
    }
    else if(Hit.bBlockingHit||Age>4.f) Detonate();
}
void ASoraProjectile::EndPlay(const EEndPlayReason::Type Reason)
{
    const auto Warning=HorseShellWarning; HorseShellWarning.Reset();
    if(Warning.IsValid()) Warning->Destroy();
    const auto Arc=ArcWarning;ArcWarning.Reset();
    if(Arc.IsValid())Arc->Destroy();
    // Unexpected projectile removal is a miss, not an eternally pending
    // sixth arrow. Session teardown invalidates its identities first.
    if((ArcheryShotId||WoodShotId)&&Reason==EEndPlayReason::Destroyed)
        if(auto* Mode=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this)))
            Mode->Campaign()->ResolveArcheryArrow(*this,nullptr);
    Super::EndPlay(Reason);
}
void ASoraProjectile::BindHorseShell(USoraCampaignDirector& Director,uint64 Generation,AActor* Warning)
{
    bHorseShell=true; HorseShellDirector=&Director; HorseShellGeneration=Generation; HorseShellWarning=Warning;
}
bool ASoraProjectile::HorseShellCurrent() const
{
    return bHorseShell&&!IsActorBeingDestroyed()&&HorseShellDirector.IsValid()&&
        HorseShellDirector->HorseShellSession(HorseShellGeneration);
}
void ASoraProjectile::Detonate()
{
    if(bDetonated) return;
    bDetonated=true;
    if(bHorseShell&&!HorseShellCurrent()) { Destroy(); return; }
    const TWeakObjectPtr<ASoraProjectile> Weak=this;
    const auto Current=[Weak] { return Weak.IsValid()&&!Weak->IsActorBeingDestroyed()&&
        (!Weak->bHorseShell||Weak->HorseShellCurrent()); };
    const FVector At=GetActorLocation();
    // Stopped short of its arming distance: a dud. It neither bursts nor hurts.
    if(!SoraCombatRules::Armed(FMath::FloorToInt32(Traveled),ArmingCm))
    {
        auto* Puff=GetWorld()->SpawnActor<AActor>(At,FRotator::ZeroRotator);
        auto* Sphere=ASoraWorldBuilder::Shape(Puff,nullptr,TEXT("Dud"),TEXT("/Engine/BasicShapes/Sphere.Sphere"),FVector::ZeroVector,FVector(.3f),FLinearColor(.18f,.17f,.16f));
        Puff->SetRootComponent(Sphere); Puff->SetActorLocation(At); Puff->SetLifeSpan(.2f);
        Destroy();
        return;
    }
    if(auto* Events=USoraGameEvents::Get(this))
    {
        FSoraDetonatedEvent Detonated;
        Detonated.Instigator=GetInstigator(); Detonated.Location=At; Detonated.Radius=Radius; Detonated.Damage=Damage;
        Events->OnDetonated.Broadcast(Detonated);
    }
    if(!Current()) { if(!IsActorBeingDestroyed()) Destroy(); return; }
    auto Hit=FSoraHit::Blast(At,WeaponId);
    if(bHorseShell) { Hit.SourceEnemy=true; Hit.AttackId=TEXT("arcing_shell"); }
    SoraDamage::Blast(*GetWorld(),Damage,Radius,Hit,GetInstigatorController(),this,Current);
    if(!Current()) { if(!IsActorBeingDestroyed()) Destroy(); return; }
    if(bHorseShell) HorseShellDirector->ResolveHorseShell(*this,HorseShellGeneration);
    if(!Current()) { if(!IsActorBeingDestroyed()) Destroy(); return; }
    auto* Effect=GetWorld()->SpawnActor<AActor>(At,FRotator::ZeroRotator);
    auto* Sphere=ASoraWorldBuilder::Shape(Effect,nullptr,TEXT("Blast"),TEXT("/Engine/BasicShapes/Sphere.Sphere"),FVector::ZeroVector,FVector(Radius/110.f),FLinearColor(1,.22,.025));
    Effect->SetRootComponent(Sphere); Effect->SetActorLocation(At); Effect->SetLifeSpan(.12f);
    Destroy();
}
