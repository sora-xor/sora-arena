#include "SoraBoss.h"
#include "SoraSettings.h"
#include "Combat/SoraDamage.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

void ASoraBoss::InitCollector(int32 Id)
{
    InitInvader(Id);
    bBladeRetainer=false; bDuelWindup=false;
    MaxHealth=300.f; Health=MaxHealth;
    GetCharacterMovement()->MaxWalkSpeed=280.f;
    SetActorScale3D(FVector(1.25f));
    bBossWindup=false; bBossRecovery=false; bBossBeam=true;
    BossAttackNumber=0; BossPhaseTimer=0.f; BossVisualTimer=0.f;
    AnnouncePhase(ESoraBossPhase::Arrived);
}
void ASoraBoss::OnDefeated(AActor* Causer)
{
    AnnouncePhase(ESoraBossPhase::Defeated);
    Super::OnDefeated(Causer);
}
void ASoraBoss::AnnouncePhase(ESoraBossPhase Phase)
{
    if(auto* Events=USoraGameEvents::Get(this))
    {
        FSoraBossPhaseEvent Event;
        Event.Boss=this; Event.Phase=Phase; Event.bBeam=bBossBeam;
        Event.HealthFraction=MaxHealth>0.f?FMath::Clamp(Health/MaxHealth,0.f,1.f):0.f;
        Events->OnBossPhase.Broadcast(Event);
    }
}
bool ASoraBoss::UpdateAttack(float Dt,ASoraCharacterBase& Target)
{
    if(bBossWindup)
    {
        BossPhaseTimer=FMath::Max(0.f,BossPhaseTimer-Dt);
        BossVisualTimer-=Dt;
        if(BossVisualTimer<=0.f) { Telegraph(); BossVisualTimer=.13f; }
        if(BossPhaseTimer<=0.f)
        {
            Strike(Target);
            bBossWindup=false; bBossRecovery=true;
            BossPhaseTimer=Health<=MaxHealth*.5f ? .90f : 1.15f;
            AnnouncePhase(ESoraBossPhase::Recovery);
        }
        return true;
    }
    if(bBossRecovery)
    {
        BossPhaseTimer=FMath::Max(0.f,BossPhaseTimer-Dt);
        if(BossPhaseTimer<=0.f) bBossRecovery=false;
        return true;
    }
    return false;
}
void ASoraBoss::BeginAttack(float Distance,const FVector& Delta)
{
    bBossBeam=Distance>340.f||(BossAttackNumber%2)==0;
    ++BossAttackNumber;
    BossLockedDirection=Delta.GetSafeNormal2D();
    if(BossLockedDirection.IsNearlyZero()) BossLockedDirection=GetActorForwardVector().GetSafeNormal2D();
    SetActorRotation(BossLockedDirection.Rotation());
    GetCharacterMovement()->StopMovementImmediately();
    bBossWindup=true;
    BossWindupDuration=bBossBeam?1.45f:1.2f;
    BossPhaseTimer=BossWindupDuration;
    BossVisualTimer=0.f;
    AnnouncePhase(ESoraBossPhase::Windup);
}
void ASoraBoss::Telegraph()
{
    const FVector From=GetActorLocation()+FVector(0,0,55);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BossWarning),false,this);
    if(bBossBeam)
    {
        const FVector End=From+BossLockedDirection*1500.f;
        FHitResult Hit;
        GetWorld()->LineTraceSingleByChannel(Hit,From,End,ECC_Visibility,Query);
        SoraDamage::Beam(GetWorld(),From,Hit.bBlockingHit?Hit.ImpactPoint:End,
            SoraAccessibility::TelegraphColor(this,SoraAccessibility::ETelegraph::Lock),3.f,.18f);
    }
    else
    {
        for(int32 Side:{-1,1})
            SoraDamage::Beam(GetWorld(),From,From+BossLockedDirection.RotateAngleAxis(Side*28.f,FVector::UpVector)*330.f,
                SoraAccessibility::TelegraphColor(this,SoraAccessibility::ETelegraph::Cleave),3.5f,.18f);
    }
}
void ASoraBoss::Strike(ASoraCharacterBase& Target)
{
    AnnouncePhase(ESoraBossPhase::Strike);
    USoraGameEvents* Events=USoraGameEvents::Get(this);
    const FVector From=GetActorLocation()+FVector(0,0,55);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BossStrike),false,this);
    FHitResult Hit;
    if(bBossBeam)
    {
        const FVector End=From+BossLockedDirection*1500.f;
        GetWorld()->LineTraceSingleByChannel(Hit,From,End,ECC_Visibility,Query);
        SoraDamage::Beam(GetWorld(),From,Hit.bBlockingHit?Hit.ImpactPoint:End,FLinearColor(.12f,1.f,1.f),8.f,.22f);
        if(Events)
        {
            FSoraWeaponFiredEvent Fired;
            Fired.Shooter=this; Fired.Kind=ESoraShotKind::Beam; Fired.Origin=From; Fired.Direction=BossLockedDirection;
            Fired.End=Hit.bBlockingHit?FVector(Hit.ImpactPoint):End;
            Events->OnWeaponFired.Broadcast(Fired);
        }
        if(Hit.GetActor()==&Target)
            SoraDamage::Deal(&Target,22.f,BossLockedDirection,Hit,GetController(),this);
    }
    else
    {
        const FVector To=Target.GetActorLocation()+FVector(0,0,35);
        const FVector Delta=To-From;
        GetWorld()->LineTraceSingleByChannel(Hit,From,To,ECC_Visibility,Query);
        for(int32 Side:{-1,1})
            SoraDamage::Beam(GetWorld(),From,From+BossLockedDirection.RotateAngleAxis(Side*28.f,FVector::UpVector)*330.f,
                FLinearColor(1.f,.80f,.24f),8.f,.22f);
        FSoraStrikeResolvedEvent Resolved;
        Resolved.Attacker=this;
        if(Delta.Size2D()<=330.f && FVector::DotProduct(Delta.GetSafeNormal2D(),BossLockedDirection)>=.88f && Hit.GetActor()==&Target)
        {
            Resolved.Target=&Target;
            Resolved.Damage=SoraDamage::Deal(&Target,30.f,BossLockedDirection,Hit,GetController(),this);
            Resolved.bHit=Resolved.Damage>0;
        }
        if(Events) Events->OnStrikeResolved.Broadcast(Resolved);
    }
}
