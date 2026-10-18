#include "SoraCompanion.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraGameMode.h"
#include "World/SoraNavigation.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

bool ASoraCompanion::UsesSpireRoute() const
{
    if(Kind!=ERole::Fighter&&Kind!=ERole::Guide) return false;
    const auto* Mode=GetWorld()?GetWorld()->GetAuthGameMode<ASoraGameMode>():nullptr;
    const auto* Beat=Mode&&Mode->Campaign()?Mode->Campaign()->ActiveBeatData():nullptr;
    return Beat&&Beat->Space.Spire.Enabled();
}

void ASoraCompanion::MoveOnSpire(const FVector& Goal,float Pace,float Acceptance)
{
    const FVector Here=GetActorLocation();
    if(FVector::Dist2D(Here,Goal)<=Acceptance&&FMath::Abs(Here.Z-Goal.Z)<100.f)
    {
        SpirePath.Reset();
        UpdateLocomotion(false,1.f);
        return;
    }
    if(Now()>=SpireRepathAt||FVector::Dist(Goal,SpirePathGoal)>100.f)
    {
        SpireRepathAt=Now()+.5f;
        SpirePathGoal=Goal;
        SpirePathIndex=1;
        auto* Nav=USoraNavigation::Get(this);
        SpirePath.Reset();
        if(Nav&&Nav->Settle()) Nav->FindPath(Here,Goal,*this,SpirePath);
    }
    if(SpirePath.Num()<2)
    {
        // A failed/partial route is not permission to steer through the void.
        UpdateLocomotion(false,1.f);
        return;
    }
    const float Feet=Here.Z-GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    while(SpirePathIndex<SpirePath.Num()-1&&FVector::Dist2D(Here,SpirePath[SpirePathIndex])<=40.f&&
        FMath::Abs(Feet-SpirePath[SpirePathIndex].Z)<90.f) ++SpirePathIndex;
    const FVector Next=SpirePath[SpirePathIndex];
    if(SpirePathIndex==SpirePath.Num()-1&&FVector::Dist2D(Here,Next)<=40.f&&FMath::Abs(Feet-Next.Z)<90.f)
    {
        UpdateLocomotion(false,1.f);
        return;
    }
    const FVector Direction=(Next-Here).GetSafeNormal2D();
    GetCharacterMovement()->MaxWalkSpeed=Pace;
    AddMovementInput(Direction,1.f);
    SetActorRotation(FRotator(0.f,Direction.Rotation().Yaw,0.f));
    UpdateLocomotion(true,FMath::Clamp(Pace/180.f,.65f,2.5f));
}

bool ASoraCompanion::SpireContact(const ASoraEnemy& Enemy,float Reach) const
{
    const FVector From=GetActorLocation(),To=Enemy.GetActorLocation(),Delta=To-From;
    if(FMath::Abs(Delta.Z)>120.f||Delta.Size()>Reach) return false;
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraSpireCompanionContact),false,this);
    // The committed hit must reach the body through the actual ramp/rail
    // geometry. Similar XY on another winding cannot count as blade contact.
    return GetWorld()->LineTraceSingleByChannel(Hit,From,To,ECC_Visibility,Query)&&Hit.GetActor()==&Enemy;
}
