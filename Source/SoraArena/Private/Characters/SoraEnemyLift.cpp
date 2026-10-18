#include "SoraEnemyController.h"
#include "SoraCampaignLift.h"
#include "SoraEnemy.h"
#include "SoraLiftRules.h"
#include "GameFramework/CharacterMovementComponent.h"

void ASoraEnemyController::AssignLift(ASoraCampaignLift& Lift,int32 Wave)
{
    AssignedLift=&Lift; LiftWave=Wave; bLiftJumped=false;
}
bool ASoraEnemyController::DriveLift(ASoraEnemy& Enemy,ASoraCharacterBase& Target,float Dt)
{
    auto* Lift=AssignedLift.Get();
    if(!Lift) return false;
    if(Enemy.IsStaggered()) return true;
    if(LiftWave==0)
    {
        // This errand alone uses its goal's real Z. Ordinary road drones
        // retain their existing ground-relative hover behavior.
        if(!Enemy.IsFlying()) return false;
        const FVector Goal=Lift->CutterGoal(Enemy.EnemySlot()%3);
        SetErrand(Goal,Lift->HawserPoint(Goal.Z)-Goal,1.f,0,false,true,6.f);
        RunErrand(Enemy,Dt,WorldMs());
        return true;
    }
    if(LiftWave==1)
    {
        // Riflemen hold the fixed gantry and fire actual traced attacks.
        const FVector Delta=Target.GetActorLocation()-Enemy.GetActorLocation();
        Face(Enemy,Delta,Dt,4.f);
        if(CanSee(Target)) Enemy.TryAttack(Target,Delta.Size());
        return true;
    }
    if(LiftWave==2)
    {
        if(Lift->Aboard(Enemy)) { AssignedLift.Reset(); return false; }
        if(!bLiftJumped)
        {
            // Wait for physical alignment, rather than jumping when the
            // progress counter leads the moving floor. LaunchCharacter is
            // a normal falling trajectory with capsule sweeps and gravity.
            if(FMath::Abs(Lift->Height()-SoraLiftRules::Gantry(3))>80.f) return true;
            Enemy.LaunchCharacter(FVector(-450.f,0.f,850.f),true,true);
            bLiftJumped=true;
        }
        return true;
    }
    return false;
}

bool ASoraEnemyController::DriveSpireFlight(ASoraEnemy& Enemy,ASoraCharacterBase& Target,float Dt)
{
    if(!bSpireFlight||!Enemy.IsFlying()) return false;
    if(Enemy.IsStaggered()) return true;
    const FVector Offset=FRotator(0,Enemy.EnemySlot()*90,0).Vector()*450.f+FVector(0,0,220);
    const FVector Goal=Target.GetActorLocation()+Offset;
    SetErrand(Goal,-Offset,1.f,0,false,true,60.f);
    RunErrand(Enemy,Dt,WorldMs());
    const FVector Delta=Target.GetActorLocation()-Enemy.GetActorLocation();
    Face(Enemy,Delta,Dt,5.f);
    if(CanSee(Target)) Enemy.TryAttack(Target,Delta.Size());
    return true;
}
