#include "SoraEnemyController.h"
#include "SoraEnemy.h"
#include "SoraWorkshopEncounterRules.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

void ASoraEnemyController::AssignWorkshopDefense(int32 Index)
{
    check(Index>=0&&Index<int(UE_ARRAY_COUNT(SoraWorkshopEncounterRules::Spawns)));
    WorkshopEntry=Index;WorkshopLeg=0;bWorkshopVaultLaunched=false;ClearPath();
    if(auto* Enemy=GetPawn<ASoraEnemy>())Enemy->SetWorkshopArrival(SoraWorkshopEncounterRules::Spawns[Index].Entry!=SoraWorkshopEncounterRules::EEntry::Roof);
}
bool ASoraEnemyController::DriveWorkshopDefense(ASoraEnemy& Enemy,ASoraCharacterBase& Target,float Dt)
{
    namespace R=SoraWorkshopEncounterRules;
    if(WorkshopEntry==INDEX_NONE)return false;
    if(Enemy.IsStaggered())return true;
    const auto Entry=R::Spawns[WorkshopEntry].Entry;const int Member=R::Spawns[WorkshopEntry].Member;
    auto* Movement=Enemy.GetCharacterMovement();const FVector At=Enemy.GetActorLocation();
    const float Half=Enemy.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(Entry==R::EEntry::Roof)
    {
        // Stay on the real roof, preserving normal windup, recovery, range,
        // sight and shell damage. No nav projection can send this post down.
        Enemy.ConsumeMovementInputVector();
        if(Movement->IsMovingOnGround())Movement->StopMovementImmediately();
        const FVector Delta=Target.GetActorLocation()-At;Face(Enemy,Delta,Dt,4.f);
        if(Movement->IsMovingOnGround()&&CanSee(Target))Enemy.TryAttack(Target,Delta.Size());
        return true;
    }
    const auto Finish=[&]
    {
        Enemy.SetWorkshopArrival(false);WorkshopEntry=INDEX_NONE;ClearPath();
        Enemy.ConsumeMovementInputVector();Movement->StopMovementImmediately();
    };
    if(Entry==R::EEntry::Vault)
    {
        Face(Enemy,FVector(-1,0,0),Dt,6.f);
        if(R::VaultLanded(At.X,At.Z-Half,Movement->IsMovingOnGround())){Finish();return true;}
        if(Movement->IsMovingOnGround())
        {
            // LaunchCharacter preserves gravity and swept capsule collision.
            // If interrupted or blocked and landed outside, retry the jump;
            // neither elapsed time nor a launch request counts as entry.
            Enemy.LaunchCharacter(FVector(R::VaultXSpeed,0,R::VaultZSpeed),true,true);
            bWorkshopVaultLaunched=true;
        }
        return true;
    }
    const auto P=R::WalkPoint(Entry,Member,WorkshopLeg);const FVector Goal(P.X,P.Y,P.Z+Half+2.15);
    const EMove Result=WalkSupportedSegment(Enemy,Goal,.7f,12.f);
    Face(Enemy,Goal-At,Dt,5.f);
    if(Result==EMove::Arrived&&++WorkshopLeg>=R::WalkLegs)Finish();
    return true;
}
