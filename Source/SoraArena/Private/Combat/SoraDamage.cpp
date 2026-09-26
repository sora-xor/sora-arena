#include "Combat/SoraDamage.h"
#include "Combat/SoraCombatEffects.h"
#include "SoraCharacterBase.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraPlayerCharacter.h"
#include "SoraWorldBuilder.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/DamageType.h"

namespace Rules = SoraCombatRules;

FSoraHit FSoraHit::Melee(const FVector& From,int32 WeaponId)
{
    FSoraHit Hit;
    Hit.Kind=Rules::EHit::Melee; Hit.Origin=From; Hit.bHasOrigin=true; Hit.WeaponId=WeaponId;
    return Hit;
}
FSoraHit FSoraHit::Ranged(const FVector& From,int32 WeaponId)
{
    FSoraHit Hit;
    Hit.Kind=Rules::EHit::Ranged; Hit.Origin=From; Hit.bHasOrigin=true; Hit.WeaponId=WeaponId;
    return Hit;
}
FSoraHit FSoraHit::Blast(const FVector& At,int32 WeaponId)
{
    FSoraHit Hit;
    Hit.Kind=Rules::EHit::Blast; Hit.Origin=At; Hit.bHasOrigin=true; Hit.WeaponId=WeaponId;
    return Hit;
}
FSoraHit FSoraHit::Beam(const FVector& From)
{
    FSoraHit Hit;
    Hit.Kind=Rules::EHit::Beam; Hit.Origin=From; Hit.bHasOrigin=true;
    return Hit;
}
FSoraHit FSoraHit::Hazard(const FVector& At)
{
    FSoraHit Hit;
    Hit.Kind=Rules::EHit::Hazard; Hit.Origin=At; Hit.bHasOrigin=true;
    return Hit;
}
Rules::FAttack FSoraHit::Attack(int32 Damage) const
{
    return {Kind,Damage,bParryable,GuardChip,GuardStamina,ParryStaggerMs,bBreaksGuard,bUnguardable};
}
FSoraDamageEvent::FSoraDamageEvent(float InDamage,const FHitResult& InHitInfo,const FVector& InShotDirection,const FSoraHit& InHit)
    : FPointDamageEvent(InDamage,InHitInfo,InShotDirection,UDamageType::StaticClass()),Hit(InHit)
{
}

const ASoraCharacterBase* SoraDamage::AttackerOf(const AActor* Causer)
{
    if(const auto* Character=Cast<ASoraCharacterBase>(Causer)) return Character;
    return Causer?Cast<ASoraCharacterBase>(Causer->GetInstigator()):nullptr;
}
int32 SoraDamage::FacingMilli(const AActor& Body,const FVector& From)
{
    const FVector Flat(From.X-Body.GetActorLocation().X,From.Y-Body.GetActorLocation().Y,0.f);
    // A hit from directly above or inside the body is not frontal.
    if(Flat.IsNearlyZero()) return -1000;
    return FMath::RoundToInt32(FVector::DotProduct(Body.GetActorForwardVector().GetSafeNormal2D(),Flat.GetSafeNormal())*1000.f);
}
float SoraDamage::Strike(AActor* Target,float Damage,const FSoraHit& Hit,const FVector& Direction,const FHitResult& Trace,
    AController* Instigator,AActor* Causer)
{
    if(!Target||Damage<=0.f) return 0.f;
    FSoraDamageEvent Event(Damage,Trace,Direction,Hit);
    return Target->TakeDamage(Damage,Event,Instigator,Causer);
}
float SoraDamage::Resolve(ASoraCharacterBase& Victim,float Damage,const FDamageEvent& Event,AActor* Causer)
{
    // Kernel practice owns its own health; Unreal damage cannot change it.
    if(Victim.IsKernelDriven()) return 0;
    if(!Victim.CanPlay()||Damage<=0) return 0;
    FSoraHit Hit;
    if(Event.IsOfType(FSoraDamageEvent::ClassID))
    {
        const FSoraDamageEvent& Typed=static_cast<const FSoraDamageEvent&>(Event);
        Hit=Typed.Hit;
        Hit.Impact=Typed.HitInfo.ImpactPoint; Hit.bHasImpact=Typed.HitInfo.bBlockingHit||!Hit.Impact.IsNearlyZero();
        Hit.Part=Typed.HitInfo.GetComponent();
    }
    else if(Causer) { Hit.Origin=Causer->GetActorLocation(); Hit.bHasOrigin=true; }
    // Opponents never damage one another, nor the hero and his companions one
    // another (no friendly fire); a shell's owner is hit by its own blast.
    const ASoraCharacterBase* Attacker=AttackerOf(Causer);
    if(Attacker&&Attacker!=&Victim&&Attacker->IsEnemy()==Victim.IsEnemy()) return 0;
    USoraCombatEffects* Effects=USoraCombatEffects::Get(&Victim);
    // Guards, shields, barriers and sparring gates may absorb or reduce the blow.
    const bool bAdmitted=Victim.AdmitDamage(Damage,Hit,Causer);
    const float Applied=bAdmitted?FMath::Min(Victim.Health,FMath::Max(0.f,Damage)):0.f;
    if(Effects) Effects->HitStop(Rules::HitStopMs(Hit.Kind,Hit.Defense,Applied>0.f,Hit.StaggerMs));
    if(Applied<=0.f) return 0;
    Victim.Health-=Applied; Victim.DamageFlash=.3f;
    USoraGameEvents* Events=USoraGameEvents::Get(&Victim);
    if(Events)
    {
        FSoraDamagedEvent Damaged;
        Damaged.Victim=&Victim; Damaged.Causer=Causer; Damaged.Amount=Applied; Damaged.HealthAfter=Victim.Health;
        Events->OnDamaged.Broadcast(Damaged);
    }
    if(Victim.Health<=0)
    {
        // 残心: an opponent the hero fells, or knocks down, starts his lingering guard.
        ASoraPlayerCharacter* Hero=Cast<ASoraPlayerCharacter>(Causer);
        if(!Hero&&Causer) Hero=Cast<ASoraPlayerCharacter>(Causer->GetInstigator());
        if(Hero&&Hero!=&Victim&&Victim.IsEnemy()) Hero->GetEquipment()->NoteDefeat();
        // 活人剣: a debt-bound conscript is knocked down, never killed.
        if(auto* Conscript=Cast<ASoraEnemy>(&Victim); Conscript&&Conscript->IsNonlethal())
        {
            Conscript->Subdue(Causer);
            return Applied;
        }
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
int32 SoraDamage::Blast(UWorld& World,float Damage,float Radius,const FSoraHit& Hit,AController* Instigator,AActor* Causer)
{
    const ASoraCharacterBase* Owner=AttackerOf(Causer);
    // Walls, buildings and cover stop a blast front; bodies do not.
    FCollisionObjectQueryParams Solid;
    Solid.AddObjectTypesToQuery(ECC_WorldStatic);
    Solid.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraBlast),false,Causer);
    TArray<ASoraCharacterBase*> Reached;
    for(TActorIterator<ASoraCharacterBase> It(&World);It;++It)
    {
        ASoraCharacterBase* Body=*It;
        if(!Body->IsAlive()||Body->IsActorBeingDestroyed()) continue;
        const bool bSelf=Body==Owner;
        const bool bOpponent=!Owner||Owner->IsEnemy()!=Body->IsEnemy();
        const int32 Distance=FMath::RoundToInt32(FVector::Dist(Hit.Origin,Body->GetActorLocation()));
        if(Distance>Radius) continue;
        FCollisionQueryParams Line=Query; Line.AddIgnoredActor(Body);
        const bool bClear=!World.LineTraceTestByObjectType(Hit.Origin,Body->GetActorLocation(),Solid,Line);
        if(Rules::BlastReaches(bSelf,bOpponent,Distance,FMath::RoundToInt32(Radius),bClear)) Reached.Add(Body);
    }
    for(ASoraCharacterBase* Body:Reached)
    {
        const FVector Direction=(Body->GetActorLocation()-Hit.Origin).GetSafeNormal();
        FHitResult Trace; Trace.ImpactPoint=Body->GetActorLocation(); Trace.Location=Trace.ImpactPoint;
        Strike(Body,Damage,Hit,Direction,Trace,Instigator,Causer);
    }
    return Reached.Num();
}
void SoraDamage::Beam(UWorld* World,FVector A,FVector B,FLinearColor Color,float Radius,float Life)
{
    auto* Effect=World->SpawnActor<AActor>();
    auto* Mesh=ASoraWorldBuilder::Shape(Effect,nullptr,TEXT("Tracer"),TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),FVector::ZeroVector,FVector(Radius/50,Radius/50,FVector::Distance(A,B)/100),Color);
    Effect->SetRootComponent(Mesh); Effect->SetActorLocation((A+B)*.5f); Effect->SetActorRotation(FRotationMatrix::MakeFromZ(B-A).Rotator()); Effect->SetLifeSpan(Life);
}
void SoraDamage::Ring(UWorld* World,FVector Center,float Radius,FLinearColor Color,float Life)
{
    constexpr int32 Segments=16;
    for(int32 Index=0;Index<Segments;++Index)
    {
        const FVector A=Center+FVector(Radius,0.f,0.f).RotateAngleAxis(360.f*Index/Segments,FVector::UpVector);
        const FVector B=Center+FVector(Radius,0.f,0.f).RotateAngleAxis(360.f*(Index+1)/Segments,FVector::UpVector);
        Beam(World,A,B,Color,2.f,Life);
    }
}
