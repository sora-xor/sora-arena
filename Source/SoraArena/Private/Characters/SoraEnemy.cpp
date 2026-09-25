#include "SoraEnemy.h"
#include "Combat/SoraDamage.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemyController.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraHistoricalArms.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

ASoraEnemy::ASoraEnemy(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    // Each opponent spawns with its own AI controller, which drives it.
    AIControllerClass=ASoraEnemyController::StaticClass();
    AutoPossessAI=EAutoPossessAI::PlacedInWorldOrSpawned;
    bUseControllerRotationYaw=false;
    GetCharacterMovement()->bOrientRotationToMovement=false;
}
void ASoraEnemy::InitInvader(int32 Id)
{
    bDojoPupil=false;
    bBladeRetainer=Id%6==0; bDuelWindup=false; EnemyIndex=Id; RangedShots=0;
    ApplyClass(Id%6);
    if(bBladeRetainer) { WeaponId=0; RebuildWeapon(); }
    BuildCat();
}
void ASoraEnemy::InitDojoPupil(int32 Id)
{
    bDojoPupil=true; bBladeRetainer=false; bDuelWindup=false;
    EnemyIndex=Id;
    bPupilWindup=false; NextEnemyShot=GetWorld()->GetTimeSeconds()+1.4f+Id*.35f;
    ApplyClass(0);
    WeaponId=FSoraCatalog::Get().Class(0).Weapons[0]; RebuildWeapon();
    BuildCat();
}
void ASoraEnemy::SuspendDojoAction()
{
    if(bDojoPupil)
    {
        bPupilWindup=false;
        NextEnemyShot=GetWorld()->GetTimeSeconds()+.8f;
    }
}
void ASoraEnemy::TickPlay(float Dt)
{
    const bool Moving=GetVelocity().Size2D()>5.f;
    UpdateLocomotion(Moving,Moving?FMath::Clamp(GetVelocity().Size2D()/180.f,.65f,2.5f):1.f);
    // The controller decides; asking it here keeps its decisions ahead of the
    // hero's tick and consumed by movement on the next frame, as before.
    if(auto* Brain=Cast<ASoraEnemyController>(GetController())) Brain->Think(Dt);
}
bool ASoraEnemy::AdmitDamage(float& Damage,AActor* Causer)
{
    // A pupil cannot be scored until the four dojo forms are complete.
    if(bDojoPupil)
    {
        const auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
        if(!G||!G->Campaign()->CanScoreDojoBout()) return false;
    }
    return true;
}
void ASoraEnemy::OnDefeated(AActor* Causer)
{
    // Zero here means the sparring pupil has yielded, not died; the
    // actor stands for a moment and cannot be scored a second time. So does
    // a boss or duellist the story spares (disarmed, captured, a duel not to
    // the death); a captive stays until the campaign takes it away.
    auto* G=Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(this));
    const bool bSpared=G&&G->Campaign()->SparesOpponent(*this);
    if(G) G->Campaign()->OpponentDefeated(this);
    SetActorEnableCollision(false);
    if(bDojoPupil||bSpared) SetActorTickEnabled(false);
    else SetActorRotation(FRotator(0,GetActorRotation().Yaw,85));
    if(!G||!G->Campaign()->IsCaptive(*this)) SetLifeSpan(2.f);
}
void ASoraEnemy::PupilAttack(ASoraCharacterBase& Target,float Dist)
{
    const float Now=GetWorld()->GetTimeSeconds();
    const FVector From=GetActorLocation()+FVector(0,0,50);
    USoraGameEvents* Events=USoraGameEvents::Get(this);
    if(bPupilWindup)
    {
        if(Now<PupilWindupEndsAt) return;
        bPupilWindup=false;
        FHitResult Hit; FCollisionQueryParams PupilTrace(SCENE_QUERY_STAT(DojoSpar),false,this);
        const FVector To=From+PupilLockedDirection*200.f;
        GetWorld()->LineTraceSingleByChannel(Hit,From,To,ECC_Visibility,PupilTrace);
        SoraDamage::Beam(GetWorld(),From,Hit.bBlockingHit?Hit.ImpactPoint:To,FLinearColor(.83f,.92f,1.f),2.5f,.14f);
        FSoraStrikeResolvedEvent Resolved;
        Resolved.Attacker=this; Resolved.WeaponId=WeaponId;
        if(Hit.GetActor()==&Target)
        {
            Resolved.Target=&Target;
            Resolved.Damage=SoraDamage::Deal(&Target,4.f,PupilLockedDirection,Hit,GetController(),this);
            Resolved.bHit=Resolved.Damage>0;
        }
        if(Events) Events->OnStrikeResolved.Broadcast(Resolved);
        return;
    }
    if(Now<NextEnemyShot||Dist>190.f) return;
    bPupilWindup=true; PupilWindupEndsAt=Now+.55f; NextEnemyShot=PupilWindupEndsAt+1.45f;
    PupilLockedDirection=(Target.GetActorLocation()+FVector(0,0,50)-From).GetSafeNormal();
    SoraDamage::Beam(GetWorld(),From,From+PupilLockedDirection*200.f,FLinearColor(1.f,.68f,.16f),2.f,.55f);
    if(Events)
    {
        FSoraMeleeCommittedEvent Committed;
        Committed.Attacker=this; Committed.WeaponId=WeaponId; Committed.Direction=PupilLockedDirection; Committed.WindupSeconds=.55f;
        Events->OnMeleeCommitted.Broadcast(Committed);
    }
}
void ASoraEnemy::DuelAttack(ASoraCharacterBase& Target,float Dist)
{
    const float Now=GetWorld()->GetTimeSeconds();
    const FVector From=GetActorLocation()+FVector(0,0,52);
    const auto Profile=SoraHistoricalArms::Profile(SoraHistoricalArms::EForm::Katana);
    USoraGameEvents* Events=USoraGameEvents::Get(this);
    if(bDuelWindup)
    {
        if(Now<DuelStrikeAt) return;
        bDuelWindup=false;
        const FVector To=From+DuelLockedDirection*Profile.MaximumDistanceCm;
        FHitResult Hit; FCollisionQueryParams DuelTrace(SCENE_QUERY_STAT(BladeRetainer),false,this);
        GetWorld()->LineTraceSingleByChannel(Hit,From,To,ECC_Visibility,DuelTrace);
        SoraDamage::Beam(GetWorld(),From,Hit.bBlockingHit?Hit.ImpactPoint:To,FLinearColor(.75f,.82f,.87f),2.f,.13f);
        const FVector ToHero=Target.GetActorLocation()-GetActorLocation();
        const float Facing=FVector::DotProduct(DuelLockedDirection.GetSafeNormal2D(),ToHero.GetSafeNormal2D());
        FSoraStrikeResolvedEvent Resolved;
        Resolved.Attacker=this; Resolved.WeaponId=WeaponId;
        if(Hit.GetActor()==&Target&&
            SoraHistoricalArms::CanStrike(SoraHistoricalArms::EForm::Katana,ToHero.Size2D(),Facing))
        {
            Resolved.Target=&Target;
            Resolved.Damage=SoraDamage::Deal(&Target,18.f,DuelLockedDirection,Hit,GetController(),this);
            Resolved.bHit=Resolved.Damage>0;
        }
        if(Events) Events->OnStrikeResolved.Broadcast(Resolved);
        return;
    }
    if(Now<NextEnemyShot||Dist>Profile.MaximumDistanceCm||Dist<Profile.MinimumDistanceCm) return;
    bDuelWindup=true;
    DuelStrikeAt=Now+SoraHistoricalArms::RetainerWindupSeconds;
    NextEnemyShot=DuelStrikeAt+SoraHistoricalArms::RetainerRecoverySeconds;
    DuelLockedDirection=(Target.GetActorLocation()+FVector(0,0,52)-From).GetSafeNormal();
    SoraDamage::Beam(GetWorld(),From,From+DuelLockedDirection*Profile.MaximumDistanceCm,
        FLinearColor(1.f,.68f,.16f),2.f,SoraHistoricalArms::RetainerWindupSeconds);
    if(Events)
    {
        FSoraMeleeCommittedEvent Committed;
        Committed.Attacker=this; Committed.WeaponId=WeaponId; Committed.Direction=DuelLockedDirection;
        Committed.WindupSeconds=SoraHistoricalArms::RetainerWindupSeconds;
        Events->OnMeleeCommitted.Broadcast(Committed);
    }
}
void ASoraEnemy::RangedAttack(ASoraCharacterBase& Target,float Dist)
{
    if(GetWorld()->GetTimeSeconds()<NextEnemyShot||Dist>2100) return;
    NextEnemyShot=GetWorld()->GetTimeSeconds()+1.3f+EnemyIndex%3*.2f;
    FVector From=GetActorLocation()+FVector(0,0,50); FVector To=Target.GetActorLocation()+FVector(0,0,35);
    FHitResult Hit; FCollisionQueryParams P(SCENE_QUERY_STAT(BotNavigation),false,this);
    GetWorld()->LineTraceSingleByChannel(Hit,From,To,ECC_Visibility,P);
    if(Hit.GetActor()==&Target)
    {
        const bool bMiss=RangedShotMisses(EnemyIndex,RangedShots++);
        const FVector End=To+(bMiss?FVector(0,80,60):FVector::ZeroVector);
        SoraDamage::Beam(GetWorld(),From,End,FLinearColor(1,.12,.3),1.7);
        if(auto* Events=USoraGameEvents::Get(this))
        {
            FSoraWeaponFiredEvent Fired;
            Fired.Shooter=this; Fired.WeaponId=WeaponId; Fired.Origin=From; Fired.Direction=(To-From).GetSafeNormal(); Fired.End=End;
            Events->OnWeaponFired.Broadcast(Fired);
        }
        if(!bMiss) SoraDamage::Deal(&Target,7.f,(To-From).GetSafeNormal(),Hit,GetController(),this);
    }
}
