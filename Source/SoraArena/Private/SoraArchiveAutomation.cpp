#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraWorldBuilder.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraArchivePostsTest,"SoraArena.Campaign.ArchivePosts",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraArchivePostsTest::RunTest(const FString&)
{
    using SoraFieldcraftAutomation::FBeatWorld;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("ArchivePosts"),5,8);if(!W.Start()) return false;
    W.Harden();
    for(TActorIterator<ASoraCharacterBase> It(W.World->GetTestWorld());It;++It)
        if(*It!=W.Hero())
        {
            It->SetActorTickEnabled(false);It->GetCharacterMovement()->DisableMovement();
            if(It->GetController()) It->GetController()->SetActorTickEnabled(false);
        }
    for(int I=0;I<1800&&W.Campaign()->IsDialogueBlocking();++I) if(!W.Tick(1)) return false;
    if(!TestTrue(TEXT("The archive's actual duel can accept input"),W.Hero()->CanPlay())) return false;
    const auto& Zone=W.Campaign()->ActiveChapter()->Space.Zones[W.BeatData().Space.Zone];
    TestEqual(TEXT("The archive retains its 26 by 18 metre footprint"),Zone.Rect.GetSize(),FVector2D(2600,1800));
    int32 PostCount=0;
    TArray<UStaticMeshComponent*> Parts;W.Mode()->Arena()->GetComponents(Parts);
    for(auto* Part:Parts) if(Part->ComponentHasTag(TEXT("ArchiveDuelPost"))) ++PostCount;
    if(!TestEqual(TEXT("All four physical duel posts are present"),PostCount,4)) return false;
    const FVector Post(Zone.Rect.Min+FVector2D(900,600),0);
    FSoraPatrolRoute Route;FSoraEnemyTuning Tune;Tune.SightCm=1;Tune.HearingCm=0;
    auto* Target=ASoraEnemy::SpawnArchetype(*W.World->GetTestWorld(),TEXT("enforcer_rifle"),100,Post+FVector(85,0,100),FRotator(0,180,0),&Route,&Tune);
    if(!TestNotNull(TEXT("The isolated sword target spawns"),Target)) return false;
    Target->Health=Target->MaxHealth=1000;
    Target->SetActorTickEnabled(false);Target->GetCharacterMovement()->SetComponentTickEnabled(false);
    if(Target->GetController()) Target->GetController()->SetActorTickEnabled(false);
    const float Half=Target->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    Target->SetActorLocation(Post+FVector(85,0,Half+2));
    if(!TestTrue(TEXT("The unlocked katana equips"),W.Hero()->GetEquipment()->EquipCampaignWeapon(3))) return false;
    W.Stand(Post+FVector(-85,0,0));W.LookAt(Target->GetActorLocation());
    int32 Swings=0;auto* Bus=USoraGameEvents::Get(W.Hero());
    if(!TestNotNull(TEXT("Production combat events are available"),Bus)) return false;
    const auto Handle=Bus->OnMeleeCommitted.AddLambda([&](const FSoraMeleeCommittedEvent& E) { if(E.Attacker==W.Hero()) ++Swings; });
    const float Before=Target->Health;
    bool Good=W.Press(EKeys::LeftMouseButton)&&W.Tick(120);
    Good&=TestEqual(TEXT("The mapped attack actually commits a swing"),Swings,1);
    Good&=TestEqual(TEXT("The real archive post blocks sword damage through it"),Target->Health,Before);
    Target->SetActorLocation(Post+FVector(85,150,Half+2));
    W.Stand(Post+FVector(-85,150,0));W.LookAt(Target->GetActorLocation());
    Good&=W.Press(EKeys::LeftMouseButton)&&W.Tick(120);
    Good&=TestEqual(TEXT("The clear-line control commits a second swing"),Swings,2);
    Good&=TestTrue(TEXT("The same sword reaches the target beside the post"),Target->Health<Before);
    Bus->OnMeleeCommitted.Remove(Handle);Target->Destroy();
    AddInfo(TEXT("Isolated collision and mapped sword input; opponent AI is frozen. This is not ordinary duel balance or final archive art acceptance."));
    return Good&&!HasAnyErrors();
}
#endif
