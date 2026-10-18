#include "SoraCampaignDirector.h"
#include "Game/SoraCampaignReach.h"
#include "SoraCompanion.h"
#include "SoraEnemy.h"
#include "SoraFieldcraft.h"
#include "SoraWorldBuilder.h"
#include "EngineUtils.h"

int32 USoraCampaignDirector::CrankHelpers()
{
    ActiveCrankHelpers=0;
    bCrankHelperRetreating=false;
    const FSoraBeat* Beat=ActiveBeatData();
    USoraFieldcraft* Craft=USoraFieldcraft::Get(this);
    if(!Beat||!Craft||Beat->CrankNpcs.IsEmpty()||Task.Goal!=SoraBeatRules::EGoal::Turns) return 0;
    for(const FString& Npc:Beat->CrankNpcs)
    {
        const FSoraDefendedPerson* Spec=Beat->Space.Fieldcraft.People.FindByPredicate(
            [&](const FSoraDefendedPerson& Person) { return Person.Id==Npc; });
        if(!Spec) continue;
        ASoraCompanion* Helper=nullptr;
        for(const auto& Person:Craft->PeopleInPlay())
            if(IsValid(Person)&&Person->CompanionId()==Npc) { Helper=Person; break; }
        if(!Helper||Helper->Condition()!=SoraFieldcraftRules::EState::Up||!Helper->IsJoined()) continue;
        const FVector Work=ASoraWorldBuilder::Floor(Spec->At,Helper->GetActorLocation().Z);
        bool bRetreat=false;
        if(Task.CoopRetreatCm>0)
            for(TActorIterator<ASoraEnemy> It(GetWorld());It;++It)
                if(It->IsEnemy()&&It->IsAlive()&&
                    (FVector::Dist2D(It->GetActorLocation(),Helper->GetActorLocation())<=Task.CoopRetreatCm||
                     FVector::Dist2D(It->GetActorLocation(),Work)<=Task.CoopRetreatCm))
                { bRetreat=true; break; }
        bCrankHelperRetreating|=bRetreat;
        // Do not send her back into the same threat at the wheel. This also
        // prevents oscillation as the cover itself puts her beyond five metres.
        const FVector Goal=bRetreat?ASoraWorldBuilder::Floor(Spec->Cover,Work.Z):Work;
        Helper->SetGoal(Goal,(ASoraWorldBuilder::Floor(Beat->Space.Anchor)-Work).Rotation().Yaw,180.f);
        if(!bRetreat&&FVector::Dist2D(Helper->GetActorLocation(),Work)<=40.f&&
            TaskState.LastActionMs>=0&&!Near(ASoraWorldBuilder::Floor(Beat->Space.Anchor),SoraCampaignReach::Interact))
            ++ActiveCrankHelpers;
    }
    return ActiveCrankHelpers;
}
