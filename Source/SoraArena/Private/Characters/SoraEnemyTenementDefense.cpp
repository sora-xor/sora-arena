#include "SoraEnemyController.h"
#include "SoraEnemy.h"
#include "SoraTenementDefenseRules.h"

void ASoraEnemyController::AssignTenementDefense(int32 Member)
{
    check(Member>=0&&Member<2);
    TenementDrone=Member;TenementLeg=0;
}
bool ASoraEnemyController::DriveTenementDefense(ASoraEnemy& Enemy,ASoraCharacterBase& Target,float Dt)
{
    if(TenementDrone==INDEX_NONE||!Enemy.IsFlying())return false;
    if(Enemy.IsStaggered())return true;
    namespace R=SoraTenementDefenseRules;
    const auto P=R::FlightPoint(TenementDrone,TenementLeg);
    const FVector Goal(P.X,P.Y,P.Z);
    const FVector Delta=Target.GetActorLocation()-Enemy.GetActorLocation();
    // RunErrand uses real movement input and collision sweeps. A blocked leg
    // cannot advance on a timer, and the normal ground-hover rule never
    // pulls this six-metre approach down onto a roof or into the queue.
    SetErrand(Goal,Delta,1.f,0,false,true,35.f);
    RunErrand(Enemy,Dt,WorldMs());
    if(bErrandReached&&TenementLeg+1<R::FlightLegs)++TenementLeg;
    if(TenementLeg==R::FlightLegs-1)
    {
        Face(Enemy,Delta,Dt,5.f);
        if(CanSee(Target))Enemy.TryAttack(Target,Delta.Size());
    }
    return true;
}
