#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "GameFramework/DamageType.h"

namespace SoraDialogueAutomation
{
// A dialogue marked checkpoint:false must be reached from a real checkpoint.
// Exercise the preceding world's damage, delivery and defense paths; never
// relax SeedCheckpoint, edit progress, or call CompleteActiveBeat directly.
inline bool StartAuthored(SoraFieldcraftAutomation::FBeatWorld& W,int64 Collectibles=0)
{
    const FSoraChapter& Chapter=FSoraCatalog::Get().Chapter(W.Chapter);
    int32 Seed=W.Beat;
    while(Seed>=0&&!Chapter.Rules[Seed].Checkpoint) --Seed;
    if(!W.Test.TestTrue(TEXT("The scene has an earlier authored checkpoint"),Seed>=0)||!W.Start(Collectibles,Seed)) return false;
    if(Seed==W.Beat) return true;
    W.Harden();
    for(int32 Frame=0;W.Campaign()->ActiveBeat()<W.Beat&&Frame<1600;++Frame)
    {
        if(W.Mode()->bDefeated) return W.Test.TestTrue(TEXT("The prerequisite task does not fail"),false);
        if(W.Campaign()->IsDialogueBlocking())
        {
            if(!W.Test.TestNotNull(TEXT("Prelude blocking dialogue keeps its cue"),W.Campaign()->CurrentDialogueCue())||!W.Tick(1,.1f)) return false;
            continue;
        }
        const int32 Before=W.Campaign()->ActiveBeat();
        const FSoraBeat& Beat=*W.Campaign()->ActiveBeatData();
        const auto Goal=Beat.Task.Goal;
        if(Goal!=SoraBeatRules::EGoal::WavesCleared&&Goal!=SoraBeatRules::EGoal::Survive&&Goal!=SoraBeatRules::EGoal::Deliveries)
            return W.Test.TestTrue(TEXT("The prelude has an explicitly driven task"),false);
        TArray<TWeakObjectPtr<ASoraEnemy>> Enemies;
        for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
            if(It->IsEnemy()&&It->IsAlive()) Enemies.Add(*It);
        for(const auto& Enemy:Enemies)
        {
            if(W.Campaign()->ActiveBeat()!=Before) break;
            if(!Enemy.IsValid()||!Enemy->IsAlive()) continue;
            UGameplayStatics::ApplyDamage(Enemy.Get(),Enemy->Health,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
            if(!W.Test.TestFalse(TEXT("A prerequisite opponent is defeated through ordinary damage"),Enemy.IsValid()&&Enemy->IsAlive())) return false;
        }
        if(W.Campaign()->ActiveBeat()!=Before) break;
        if(Goal==SoraBeatRules::EGoal::Deliveries)
        {
            FVector Anchor;
            if(!W.Test.TestTrue(TEXT("The prerequisite delivery has a work spot"),W.Campaign()->ObjectiveAnchor(Anchor)&&W.Campaign()->AnchorTakesInteract())) return false;
            W.Stand(Anchor);
            if(!W.Press(EKeys::E)) return false;
        }
        if(W.Campaign()->ActiveBeat()!=Before) break;
        // Timed defense advances on its actual task clock, with every
        // arriving wave fought before it can destroy the defended objects.
        if(!W.Tick(1,.5f)) return false;
    }
    if(!W.Test.TestEqual(TEXT("Real prerequisite play reaches the requested dialogue"),W.Campaign()->ActiveBeat(),W.Beat)) return false;
    // A walk-and-talk test begins before its trigger volume, not at the
    // previous task's final delivery point in the same place.
    if(W.Mode()->IsPlaying()) W.Stand(FVector(W.Campaign()->ActiveSpace()->Entry,0.f));
    return true;
}
}
#endif
