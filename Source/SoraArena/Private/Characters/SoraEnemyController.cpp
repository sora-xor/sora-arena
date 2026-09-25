#include "SoraEnemyController.h"
#include "SoraBoss.h"
#include "SoraEnemy.h"
#include "SoraHistoricalArms.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

void ASoraEnemyController::Think(float Dt)
{
    ASoraEnemy* Enemy=GetPawn<ASoraEnemy>(); if(!Enemy) return;
    auto* Target=Cast<ASoraCharacterBase>(UGameplayStatics::GetPlayerPawn(this,0)); if(!Target||!Target->IsAlive()) return;
    if(auto* Boss=Cast<ASoraBoss>(Enemy)) { DriveCollector(*Boss,*Target,Dt); return; }
    DriveOpponent(*Enemy,*Target,Dt);
}
void ASoraEnemyController::DriveOpponent(ASoraEnemy& Enemy,ASoraCharacterBase& Target,float Dt)
{
    FVector Delta=Target.GetActorLocation()-Enemy.GetActorLocation(); const float Dist=Delta.Size2D(); Delta.Z=0;
    if(!Enemy.IsDuelWindup()) Enemy.SetActorRotation(FMath::RInterpTo(Enemy.GetActorRotation(),Delta.Rotation(),Dt,4.f));
    FVector Move=Delta.GetSafeNormal();
    FHitResult Ahead; FCollisionQueryParams P(SCENE_QUERY_STAT(BotNavigation),false,&Enemy);
    if(GetWorld()->LineTraceSingleByChannel(Ahead,Enemy.GetActorLocation(),Enemy.GetActorLocation()+Move*180,ECC_Visibility,P)&&Ahead.GetActor()!=&Target)
        Move=FVector(-Move.Y,Move.X,0)*(Enemy.EnemySlot()%2?1:-1);
    if((!Enemy.IsDojoPupil()||!Enemy.IsPupilWindup())&&(!Enemy.IsBladeRetainer()||!Enemy.IsDuelWindup()))
    {
        if(Enemy.IsBladeRetainer())
        {
            switch(SoraHistoricalArms::RetainerFootwork(Dist))
            {
            case SoraHistoricalArms::EFootwork::Close: Enemy.AddMovementInput(Move,.55f); break;
            case SoraHistoricalArms::EFootwork::Withdraw: Enemy.AddMovementInput(-Move,.55f); break;
            case SoraHistoricalArms::EFootwork::Hold:
                Enemy.AddMovementInput(Enemy.GetActorRightVector(),FMath::Sin(Enemy.GetLifeTime()+Enemy.EnemySlot())*.2f); break;
            }
        }
        else if(Dist>(Enemy.IsDojoPupil()?160.f:650.f)) Enemy.AddMovementInput(Move,.55f);
        else Enemy.AddMovementInput(Enemy.GetActorRightVector(),FMath::Sin(Enemy.GetLifeTime()+Enemy.EnemySlot())*.2f);
    }
    if(Enemy.IsDojoPupil()) { Enemy.PupilAttack(Target,Dist); return; }
    if(Enemy.IsBladeRetainer()) { Enemy.DuelAttack(Target,Dist); return; }
    Enemy.RangedAttack(Target,Dist);
}
void ASoraEnemyController::DriveCollector(ASoraBoss& Boss,ASoraCharacterBase& Target,float Dt)
{
    // Fixed attack order, locked aim, explicit warning, and recovery make the
    // offline encounter readable. No random damage or hidden hit timestamp.
    if(Boss.UpdateAttack(Dt,Target)) return;
    FVector Delta=Target.GetActorLocation()-Boss.GetActorLocation(); Delta.Z=0.f;
    const float Distance=Delta.Size2D();
    if(Distance>740.f)
    {
        const FVector Move=Delta.GetSafeNormal2D();
        Boss.SetActorRotation(FMath::RInterpTo(Boss.GetActorRotation(),Move.Rotation(),Dt,3.f));
        Boss.AddMovementInput(Move,.72f);
        return;
    }
    Boss.BeginAttack(Distance,Delta);
}
