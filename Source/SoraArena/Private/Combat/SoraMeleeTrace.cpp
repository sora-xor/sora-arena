#include "Combat/SoraMeleeTrace.h"
#include "SoraEnemy.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"

void SoraMeleeTrace::Sweep(UWorld& World,TArray<FHitResult>& Hits,const FVector& Start,
    const FVector& End,float Radius,AActor* Attacker)
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraMelee),false,Attacker);
    const auto Shape=FCollisionShape::MakeSphere(Radius);
    TArray<FHitResult> DroneHits;
    for(TActorIterator<ASoraEnemy> It(&World);It;++It)
    {
        if(*It==Attacker)continue;
        auto* Body=It->InventoryDroneBody();
        if(!Body)continue;
        // Ignoring this component before the world sweep is essential: a
        // rejected sphere hit must not hide a real target farther along it.
        Query.AddIgnoredComponent(It->GetCapsuleComponent());
        FHitResult Hit;
        if(Body->IsQueryCollisionEnabled()&&Body->SweepComponent(Hit,Start,End,FQuat::Identity,Shape,false))
        {
            // SweepComponent queries geometry without a trace-channel policy
            // (UE's BodyInstance path uses an overlap-all filter). This hull
            // is a solid weapon contact, so it participates in the cutoff.
            Hit.bBlockingHit=true;
            DroneHits.Add(Hit);
        }
    }
    World.SweepMultiByChannel(Hits,Start,End,FQuat::Identity,ECC_Pawn,Shape,Query);
    if(DroneHits.IsEmpty())return;
    Hits.Append(DroneHits);
    // Component sweeps do not see intervening world cover. Merge them with
    // the ordinary query, retaining overlaps up to the first blocking hit.
    float BlockingTime=1.f;
    for(const auto& Hit:Hits)if(Hit.bBlockingHit)BlockingTime=FMath::Min(BlockingTime,Hit.Time);
    Hits.RemoveAll([BlockingTime](const FHitResult& Hit){return Hit.Time>BlockingTime;});
    Hits.StableSort([](const FHitResult& A,const FHitResult& B)
    {
        return A.Time<B.Time||(A.Time==B.Time&&!A.bBlockingHit&&B.bBlockingHit);
    });
}
