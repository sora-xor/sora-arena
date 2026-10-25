#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraBoss.h"
#include "Engine/PointLight.h"
#include "Components/PointLightComponent.h"
#include "GameFramework/DamageType.h"
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
    if(!TestTrue(TEXT("The unlocked katana equips"),W.Hero()->GetEquipment()->EquipCampaignWeapon(0))) return false;
    if(!TestEqual(TEXT("Weapon zero is the equipped katana"),W.Hero()->WeaponId,0)||!W.Tick(20)) return false;
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

namespace
{
APointLight* FamilyPageLight(SoraFieldcraftAutomation::FBeatWorld& W)
{
    APointLight* Found=nullptr;int32 Count=0;
    for(TActorIterator<APointLight> It(W.World->GetTestWorld());It;++It)
        if(It->ActorHasTag(TEXT("ArchiveFamilyPageLight"))) { Found=*It;++Count; }
    return W.Test.TestEqual(TEXT("Exactly one physical family-page light exists"),Count,1)?Found:nullptr;
}
bool PageIsLit(SoraFieldcraftAutomation::FBeatWorld& W,bool Expected)
{
    auto* Page=FamilyPageLight(W);if(!Page) return false;
    auto* Light=Page->PointLightComponent.Get();
    return W.Test.TestEqual(TEXT("The actual light visibility follows discovery"),Light->IsVisible(),Expected)&&
        W.Test.TestEqual(TEXT("The actual light power follows discovery"),Light->Intensity,Expected?450.f:0.f);
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraArchiveFamilyPageTest,"SoraArena.Campaign.ArchiveFamilyPage",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraArchiveFamilyPageTest::RunTest(const FString&)
{
    using SoraFieldcraftAutomation::FBeatWorld;
    if(!FSoraCatalog::Get().Load()) return false;
    {
        FBeatWorld W(*this,TEXT("ArchiveFamilyPage"),5,8);
        if(!W.Start()||!PageIsLit(W,false)) return false;
        W.Harden();
        ASoraBoss* Rival=nullptr;
        for(TActorIterator<ASoraBoss> It(W.World->GetTestWorld());It;++It) Rival=*It;
        if(!TestNotNull(TEXT("The actual archive duellist exists"),Rival)) return false;
        Rival->Hold(600000);
        for(int I=0;I<1800&&W.Campaign()->LinesQueued()>0;++I) if(!W.Tick(1)) return false;
        if(!TestTrue(TEXT("The opening lines finish before the phase fixture"),W.Campaign()->LinesQueued()==0)) return false;
        // Directed phase setup using the same generic story-damage path as
        // Boss.ToranosukeSteel. This is not a player combat/difficulty claim.
        UGameplayStatics::ApplyDamage(Rival,Rival->MaxHealth*.5f,nullptr,W.Hero(),UDamageType::StaticClass());
        if(!W.Tick(2)||!TestEqual(TEXT("Actual opponent health enters the family-page phase"),W.Campaign()->ActivePhase(),1)||
            !PageIsLit(W,true)) return false;
        TestTrue(TEXT("The family-page dialogue holds combat"),W.Campaign()->IsDialogueBlocking()&&!W.Hero()->CanPlay());
        const auto* Reveal=W.Campaign()->CurrentDialogueCue();
        TestTrue(TEXT("The family-page exchange precedes the remembered lesson"),Reveal&&Reveal->Id==TEXT("ch06.b09.toranosuke.005"));
        const auto* BeforeReveal=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
        if(!TestTrue(TEXT("Quitting during the reveal still resumes before the exchange"),
            BeforeReveal&&BeforeReveal->CheckpointChapter==5&&BeforeReveal->CheckpointBeat==8&&BeforeReveal->CheckpointPhase==0)) return false;
        for(int I=0;I<1800&&W.Campaign()->IsDialogueBlocking();++I) if(!W.Tick(1)) return false;
        if(!TestFalse(TEXT("The authored reveal releases control"),W.Campaign()->IsDialogueBlocking())||!W.Tick(2)) return false;
        const auto* Memory=W.Campaign()->CurrentDialogueCue();
        TestTrue(TEXT("The remembered lesson follows the blocking exchange"),Memory&&Memory->Id==TEXT("ch06.b09.sekireisai.001"));
        const auto* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
        if(!TestTrue(TEXT("Only the completed reveal saves the actual mid-duel checkpoint"),Saved&&Saved->CheckpointChapter==5&&Saved->CheckpointBeat==8&&Saved->CheckpointPhase==1)) return false;
        W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
        W.World->DestroyTestWorld(true);W.World->ForwardErrorMessages(this);W.World.Reset();
        W.World=MakeUnique<FSoraAutomationWorld>();
        if(!W.World->Start(W.Slot)||!W.World->Tick(1)||!W.World->EnableKeyInput()||
            !W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)) return false;
        W.Events.Reset();W.EventsHandle=W.Fieldcraft()->OnEvent.AddLambda([&W](FName Event){W.Events.Add(Event.ToString());});
        if(!TestTrue(TEXT("The saved duel resumes in phase two"),W.Campaign()->ActiveBeat()==8&&W.Campaign()->ActivePhase()==1)||
            !PageIsLit(W,true)) return false;
    }
    FBeatWorld Pledge(*this,TEXT("ArchivePledgePage"),5,9);
    if(!Pledge.Start()||!PageIsLit(Pledge,true)) return false;
    AddInfo(TEXT("Actual phase/light state and actual save reload; directed story damage. Slate text, character staging, cinematic animation and rendered lighting remain unqualified."));
    return !HasAnyErrors();
}
#endif
