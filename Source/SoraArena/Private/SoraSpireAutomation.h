#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraLiftAutomation.h"
#include "SoraCatalog.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"

namespace SoraSpireAutomation
{
inline bool GantryClearance(FSoraAutomationWorld& W,const FSoraBeatSpace& Space)
{
    const auto* Hero=W.Player();
    const auto Capsule=FCollisionShape::MakeCapsule(Hero->GetCapsuleComponent()->GetScaledCapsuleRadius(),Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    FCollisionObjectQueryParams Objects(ECC_WorldStatic);
    Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(SpireLandingClearance),false,Hero);
    for(int32 Level:{1,3})
    {
        const int32 Landing=SoraSpireRules::Landing(Level);
        for(int32 Next:{Landing-1,Landing+1})
        {
            if(!Space.Spire.Ramp.IsValidIndex(Next)) continue;
            // A raised capsule clears the walkable landing lip but still
            // intersects every 150 cm rail; this checks solid geometry only.
            const FVector A=Space.Spire.Ramp[Landing]+FVector(0,0,150),B=Space.Spire.Ramp[Next]+FVector(0,0,150);
            FHitResult Hit;
            if(W.GetTestWorld()->SweepSingleByObjectType(Hit,A,B,FQuat::Identity,Objects,Capsule,Query))
            {
                UE_LOG(LogTemp,Error,TEXT("Spire gantry clearance failed landing=%d node=%d actor=%s component=%s impact=%s"),
                    Landing,Next,*GetNameSafe(Hit.GetActor()),*GetNameSafe(Hit.GetComponent()),*Hit.ImpactPoint.ToString());
                return false;
            }
        }
    }
    return true;
}
inline bool Climb(FSoraAutomationWorld& W,const FSoraBeatSpace& Space,int32 From,int32 To)
{
    for(int32 N=From;N<=To;++N)
    {
        const bool Walked=SoraLiftAutomation::Walk(W,Space.Spire.Ramp[N]);
        const auto* Hero=W.Player();
        // A point with matching XY on another winding is not arrival.
        if(!Walked||FMath::Abs(Hero->GetActorLocation().Z-Space.Spire.Ramp[N].Z-90.f)>55.f)
        {
            const FVector Here=Hero->GetActorLocation(),Goal=Space.Spire.Ramp[N];
            const auto* Move=Hero->GetCharacterMovement();
            FHitResult Block; FCollisionQueryParams Query(SCENE_QUERY_STAT(SpireRouteFailure),false,Hero);
            W.GetTestWorld()->SweepSingleByChannel(Block,Here,Here+(Goal-Here).GetSafeNormal2D()*100,FQuat::Identity,ECC_Pawn,
                FCollisionShape::MakeCapsule(Hero->GetCapsuleComponent()->GetScaledCapsuleRadius(),Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),Query);
            UE_LOG(LogTemp,Error,TEXT("Spire climb failed node=%d range=%d..%d walked=%d beat=%d hero=%s target=%s feet=%.2f mode=%d base=%s sweep_actor=%s sweep_component=%s impact=%s"),
                N,From,To,Walked,W.Mode()->Campaign()->ActiveBeat(),*Here.ToString(),*Goal.ToString(),
                Here.Z-Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(),int32(Move->MovementMode),
                *GetNameSafe(Hero->GetMovementBaseObject()),*GetNameSafe(Block.GetActor()),*GetNameSafe(Block.GetComponent()),*Block.ImpactPoint.ToString());
            return false;
        }
    }
    return true;
}
}
#endif
