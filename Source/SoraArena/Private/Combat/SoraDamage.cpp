#include "Combat/SoraDamage.h"
#include "SoraCharacterBase.h"
#include "SoraGameEvents.h"
#include "SoraWorldBuilder.h"
#include "Engine/World.h"
#include "GameFramework/DamageType.h"
#include "Kismet/GameplayStatics.h"

float SoraDamage::Deal(AActor* Target,float Damage,const FVector& Direction,const FHitResult& Hit,AController* Instigator,AActor* Causer)
{
    return UGameplayStatics::ApplyPointDamage(Target,Damage,Direction,Hit,Instigator,Causer,UDamageType::StaticClass());
}
float SoraDamage::Resolve(ASoraCharacterBase& Victim,float Damage,AActor* Causer)
{
    // Kernel practice owns its own health; Unreal damage cannot change it.
    if(Victim.IsKernelDriven()) return 0;
    if(!Victim.CanPlay()||Damage<=0) return 0;
    // Opponents never damage one another.
    if(const auto* Other=Cast<ASoraCharacterBase>(Causer)) if(Other->IsEnemy()&&Victim.IsEnemy()) return 0;
    // Sparring gates, guards and parries may absorb or reduce the blow.
    if(!Victim.AdmitDamage(Damage,Causer)) return 0;
    const float Applied=FMath::Min(Victim.Health,Damage); Victim.Health-=Applied; Victim.DamageFlash=.3f;
    USoraGameEvents* Events=USoraGameEvents::Get(&Victim);
    if(Events)
    {
        FSoraDamagedEvent Damaged;
        Damaged.Victim=&Victim; Damaged.Causer=Causer; Damaged.Amount=Applied; Damaged.HealthAfter=Victim.Health;
        Events->OnDamaged.Broadcast(Damaged);
    }
    if(Victim.Health<=0)
    {
        if(Events)
        {
            FSoraDiedEvent Died;
            Died.Victim=&Victim; Died.Killer=Causer; Died.bSparring=Victim.IsSparring();
            Events->OnDied.Broadcast(Died);
        }
        Victim.OnDefeated(Causer);
    }
    return Applied;
}
void SoraDamage::Beam(UWorld* World,FVector A,FVector B,FLinearColor Color,float Radius,float Life)
{
    auto* Effect=World->SpawnActor<AActor>();
    auto* Mesh=ASoraWorldBuilder::Shape(Effect,nullptr,TEXT("Tracer"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),FVector::ZeroVector,FVector(Radius/50,Radius/50,FVector::Distance(A,B)/100),Color);
    Effect->SetRootComponent(Mesh); Effect->SetActorLocation((A+B)*.5f); Effect->SetActorRotation(FRotationMatrix::MakeFromZ(B-A).Rotator()); Effect->SetLifeSpan(Life);
}
