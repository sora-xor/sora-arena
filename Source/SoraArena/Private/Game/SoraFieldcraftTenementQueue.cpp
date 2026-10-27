#include "SoraFieldcraft.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraCompanion.h"
#include "SoraGameMode.h"
#include "SoraTenementQueueRules.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"

void USoraFieldcraft::StageKitchenQueue(const FSoraBeat& Beat)
{
    if(!Beat.Space.bTenementDefense)return;
    namespace R=SoraTenementQueueRules;
    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    for(int I=0;I<R::Count;++I)
    {
        const auto P=R::Queue(I);
        auto* Resident=GetWorld()->SpawnActor<ASoraCompanion>(FVector(P.X,P.Y,90.15),FRotator(0,90,0),Params);
        KitchenQueue.Add(Resident); KitchenQueueLeg.Add(0);
        if(!Resident)continue;
        FSoraCompanionSpec Spec;
        Spec.Id=FString::Printf(TEXT("kitchen_resident_%d"),I+1);
        Spec.Role=TEXT("bystander"); Spec.bDetectable=false;
        Spec.Rules={100,false,3000,0,0,false,0};
        Resident->Init(Spec,I);
        // Non-targetable residents cannot intercept bullets or the hero's
        // interaction trace. World collision remains for their real walk.
        Resident->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
    }
}

void USoraFieldcraft::TickKitchenQueue()
{
    if(KitchenQueue.IsEmpty())return;
    const auto* Mode=Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode());
    if(!Mode||!Mode->Campaign())return;
    bKitchenScattered|=Mode->Campaign()->TenementKitchenContested();
    if(!bKitchenScattered)return;
    namespace R=SoraTenementQueueRules;
    for(int I=0;I<KitchenQueue.Num();++I)
    {
        auto* Resident=KitchenQueue[I].Get();
        if(!IsValid(Resident))continue;
        auto& Leg=KitchenQueueLeg[I];
        // Align in the alley before crossing the front; a diagonal shortcut
        // would run through the paper. Once indoors, shelter for this attack.
        const auto Approach=R::DoorApproach(I),Home=R::Home(I);
        const FVector At=Resident->GetActorLocation();
        if(Leg==0&&FVector::Dist2D(At,FVector(Approach.X,Approach.Y,At.Z))<=R::Arrival)Leg=1;
        const auto Goal=Leg==0?Approach:Home;
        Resident->SetGoal(FVector(Goal.X,Goal.Y,At.Z),I%2==0?180.f:0.f,R::Pace);
        // Bystanders use CharacterMovement sweeps, including the 15 cm
        // threshold. They stay visible and collidable inside the room.
    }
}
