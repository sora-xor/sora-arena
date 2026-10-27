#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEnemy.h"
#include "SoraBoss.h"
#include "Engine/RectLight.h"
#include "Components/RectLightComponent.h"
#include "GameFramework/DamageType.h"
#include "SoraEnemyController.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraWorldBuilder.h"
#include "SoraArchiveRules.h"
#include "Camera/CameraActor.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/WidgetComponent.h"
#include "Widgets/SWidget.h"

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
    const FVector Post(Zone.Rect.Min+FVector2D(900,600),W.BeatData().Space.HeightCm);
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
ARectLight* FamilyPageLight(SoraFieldcraftAutomation::FBeatWorld& W)
{
    ARectLight* Found=nullptr;int32 Count=0;
    for(TActorIterator<ARectLight> It(W.World->GetTestWorld());It;++It)
        if(It->ActorHasTag(TEXT("ArchiveFamilyPageLight"))) { Found=*It;++Count; }
    return W.Test.TestEqual(TEXT("Exactly one physical family-page light exists"),Count,1)?Found:nullptr;
}
bool PageIsLit(SoraFieldcraftAutomation::FBeatWorld& W,bool Expected)
{
    auto* Page=FamilyPageLight(W);if(!Page) return false;
    auto* Light=Page->RectLightComponent.Get();
    TArray<UWidgetComponent*> Widgets;W.Mode()->Arena()->GetComponents(Widgets);
    UWidgetComponent* Record=nullptr;int32 Count=0;
    for(auto* Widget:Widgets) if(Widget->ComponentHasTag(TEXT("ArchiveFamilyRecord"))) { Record=Widget;++Count; }
    bool Good=W.Test.TestEqual(TEXT("Exactly one world-space household record exists"),Count,1);
    if(Record)
    {
        Good&=W.Test.TestEqual(TEXT("The actual record visibility follows discovery"),Record->IsVisible(),Expected);
        Good&=W.Test.TestTrue(TEXT("The record is world-space and cannot obstruct the duel"),
            Record->GetWidgetSpace()==EWidgetSpace::World&&Record->GetCollisionEnabled()==ECollisionEnabled::NoCollision);
        const auto& Slate=Record->GetSlateWidget();
        Good&=W.Test.TestTrue(TEXT("The actual household record has its Slate content"),Slate.IsValid());
        if(Slate.IsValid())
        {
            // Measure the shipped font's real line metrics. The first render
            // clipped the purchase-price and unit rows despite fitting the
            // nominal point sizes into the texture.
            Slate->SlatePrepass(1.f);
            const FVector2D Desired=Slate->GetDesiredSize(),Draw=Record->GetDrawSize();
            Good&=W.Test.TestTrue(FString::Printf(TEXT("The complete household record fits its texture: desired %.1fx%.1f, draw %.1fx%.1f"),
                Desired.X,Desired.Y,Draw.X,Draw.Y),Desired.X>0&&Desired.Y>0&&Desired.X<=Draw.X&&Desired.Y<=Draw.Y);
        }
    }
    Good&=W.Test.TestEqual(TEXT("The actual light visibility follows discovery"),Light->IsVisible(),Expected);
    Good&=W.Test.TestTrue(TEXT("The page supplies light only after discovery"),Expected?Light->Intensity>0.f:Light->Intensity==0.f);
    return Good;
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraArchiveFamilyPageTest,"SoraArena.Campaign.ArchiveFamilyPage",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraArchiveFamilyPageTest::RunTest(const FString&)
{
    using SoraFieldcraftAutomation::FBeatWorld;
    if(!FSoraCatalog::Get().Load()) return false;
    for(const bool WithBark:{false,true})
    {
        FBeatWorld W(*this,WithBark?TEXT("ArchiveFamilyPageQueued"):TEXT("ArchiveFamilyPage"),5,8);
        if(!W.Start()||!PageIsLit(W,false)) return false;
        W.Harden();
        ASoraBoss* Rival=nullptr;
        for(TActorIterator<ASoraBoss> It(W.World->GetTestWorld());It;++It) Rival=*It;
        if(!TestNotNull(TEXT("The actual archive duellist exists"),Rival)) return false;
        Rival->Hold(600000);
        for(int I=0;I<1800&&W.Campaign()->LinesQueued()>0;++I) if(!W.Tick(1)) return false;
        if(!TestTrue(TEXT("The opening lines finish before the phase fixture"),W.Campaign()->LinesQueued()==0)) return false;
        if(WithBark) W.Campaign()->RaiseBeatEvent(TEXT("pattern:kesa_combo"));
        // Directed phase setup using the same generic story-damage path as
        // Boss.ToranosukeSteel. This is not a player combat/difficulty claim.
        UGameplayStatics::ApplyDamage(Rival,Rival->MaxHealth*.5f,nullptr,W.Hero(),UDamageType::StaticClass());
        if(!W.Tick(2)||!TestEqual(TEXT("Actual opponent health enters the family-page phase"),W.Campaign()->ActivePhase(),1)||
            !PageIsLit(W,false)) return false;
        const auto* BeforeReveal=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
        if(!TestTrue(TEXT("Quitting before or during the reveal still resumes before the exchange"),
            BeforeReveal&&BeforeReveal->CheckpointChapter==5&&BeforeReveal->CheckpointBeat==8&&BeforeReveal->CheckpointPhase==0)) return false;
        if(WithBark) TestFalse(TEXT("A prior combat bark has not yet started the blocking exchange"),W.Campaign()->IsDialogueBlocking());
        for(int I=0;I<600&&!W.Campaign()->IsArchiveRevealActive();++I) if(!W.Tick(1)) return false;
        if(!TestTrue(TEXT("The family-page cinematic holds combat"),W.Campaign()->IsArchiveRevealActive()&&
            W.Campaign()->IsDialogueBlocking()&&!W.Hero()->CanPlay())) return false;
        auto* PC=Cast<APlayerController>(W.Hero()->GetController());
        auto* Shot=W.Campaign()->CinematicCamera();
        if(!TestTrue(TEXT("The actual local view belongs to the reveal camera"),PC&&Shot&&PC->GetViewTarget()==Shot)||
            !TestNull(TEXT("The rack-impact prologue has no premature speech cue"),W.Campaign()->CurrentDialogueCue())) return false;
        const double Initial=W.Campaign()->ArchiveRevealTime();int ActiveFrames=0;
        const auto Step=[&]() { ++ActiveFrames;return W.Tick(1); };
        const auto AdvanceTo=[&](double Seconds)
        {
            for(int I=0;I<1300&&W.Campaign()->IsArchiveRevealActive()&&W.Campaign()->ArchiveRevealTime()<Seconds;++I)
                if(!Step()) return false;
            return TestTrue(TEXT("The cinematic reaches its timed mark"),W.Campaign()->IsArchiveRevealActive()&&W.Campaign()->ArchiveRevealTime()>=Seconds);
        };
        if(!AdvanceTo(SoraArchiveRules::ImpactSeconds+.05)) return false;
        if(!PageIsLit(W,true)) return false;
        const auto& Zone=W.Campaign()->ActiveChapter()->Space.Zones[W.BeatData().Space.Zone];
        TestTrue(TEXT("The real duellist has reached the east rack"),FMath::Abs(Rival->GetActorLocation().X-Zone.Rect.Min.X-2444)<2);
        UStaticMeshComponent* Rack=nullptr;TArray<UStaticMeshComponent*> Parts;W.Mode()->Arena()->GetComponents(Parts);
        for(auto* Part:Parts) if(Part->ComponentHasTag(TEXT("ArchiveEastRack"))) Rack=Part;
        TestTrue(TEXT("The physical rack reacts to the impact"),Rack&&!Rack->GetRelativeRotation().IsNearlyZero(.01f));
        const auto HeroAt=W.Hero()->GetActorLocation();
        if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!W.World->InjectKey(EKeys::LeftMouseButton,IE_Pressed)||!Step()||!Step()) return false;
        TestTrue(TEXT("Held movement and fire cannot move the cinematic hero"),HeroAt.Equals(W.Hero()->GetActorLocation(),.1f)&&!W.Hero()->GetEquipment()->IsTriggerHeld());
        W.World->InjectKey(EKeys::W,IE_Released);W.World->InjectKey(EKeys::LeftMouseButton,IE_Released);
        W.Mode()->SetMenuOpen(true);
        const double Paused=W.Campaign()->ArchiveRevealTime();const FTransform CameraAt=Shot->GetActorTransform(),RivalAt=Rival->GetActorTransform();
        if(!W.Tick(120)) return false;
        TestTrue(TEXT("Pause freezes the scene clock, camera and physical duellist"),
            W.Campaign()->ArchiveRevealTime()==Paused&&CameraAt.Equals(Shot->GetActorTransform(),.001f)&&RivalAt.Equals(Rival->GetActorTransform(),.001f));
        W.Mode()->ResumePlay();
        if(!AdvanceTo(SoraArchiveRules::SpeechStartSeconds+.05)) return false;
        const auto* Reveal=W.Campaign()->CurrentDialogueCue();
        TestTrue(TEXT("The family-page exchange follows impact and precedes the remembered lesson"),Reveal&&Reveal->Id==TEXT("ch06.b09.toranosuke.005"));
        TestTrue(TEXT("The rival has cleared the household record before its numbers are spoken"),
            Rival->GetActorLocation().Y-Zone.Rect.Min.Y>1050&&PageIsLit(W,true));
        if(!AdvanceTo(19.5)) return false;
        const auto* LateSave=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
        TestTrue(TEXT("The nearly complete cinematic still retains the phase-one checkpoint"),LateSave&&LateSave->CheckpointPhase==0);
        for(int I=0;I<120&&W.Campaign()->IsArchiveRevealActive();++I) if(!Step()) return false;
        TestTrue(TEXT("The reveal releases at twenty active seconds, excluding pause"),
            !W.Campaign()->IsArchiveRevealActive()&&FMath::Abs(Initial+ActiveFrames/60.-SoraArchiveRules::RevealSeconds)<.04);
        TestTrue(TEXT("The completed scene restores the player view"),PC->GetViewTarget()==W.Hero()||
            (PC->PlayerCameraManager&&PC->PlayerCameraManager->PendingViewTarget.Target==W.Hero()));
        // Scene components elide changes below their 1e-4 degree rotator or
        // 1e-8 quaternion tolerance. A scalar double's default 1e-8 degree
        // comparison is stricter than the transform setter's contract.
        const FRotator RackRotation=Rack?Rack->GetRelativeRotation():FRotator(90,90,90);
        const FRotator RivalRotation=Rival->GetActorRotation();
        AddInfo(FString::Printf(TEXT("SORA_ARCHIVE_SETTLED bark=%d rack=(%.9f,%.9f,%.9f) rival=(%.9f,%.9f,%.9f) degrees"),
            WithBark,RackRotation.Pitch,RackRotation.Yaw,RackRotation.Roll,RivalRotation.Pitch,RivalRotation.Yaw,RivalRotation.Roll));
        TestTrue(TEXT("The rack settles within one thousandth of a degree"),Rack&&RackRotation.IsNearlyZero(.001));
        TestTrue(TEXT("The duellist stands upright within one thousandth of a degree"),
            FMath::Abs(RivalRotation.Pitch)<.001&&FMath::Abs(RivalRotation.Roll)<.001);
        TestTrue(TEXT("Both characters return inside the duel ring before control resumes"),
            FMath::Abs(W.Hero()->GetActorLocation().X-Zone.Rect.Min.X-1400)<2&&
            FMath::Abs(Rival->GetActorLocation().X-Zone.Rect.Min.X-1800)<2&&
            FMath::Abs(W.Hero()->GetActorLocation().Y-Zone.Rect.Min.Y-900)<2&&
            FMath::Abs(Rival->GetActorLocation().Y-Zone.Rect.Min.Y-900)<2);
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
            !PageIsLit(W,true)||!TestFalse(TEXT("Restoring phase two never replays the finished cinematic"),W.Campaign()->IsArchiveRevealActive())) return false;
    }
    FBeatWorld Pledge(*this,TEXT("ArchivePledgePage"),5,9);
    if(!Pledge.Start()||!PageIsLit(Pledge,true)) return false;
    AddInfo(TEXT("Actual twenty-second scene, rack impact, camera ownership, pause/input hold, phase/light state and save reload; directed story damage and procedural character staging. Authored character animation, readable slate art, rendered framing and sound remain unqualified."));
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraArchiveRevealResetTest,"SoraArena.Campaign.ArchiveRevealReset",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraArchiveRevealResetTest::RunTest(const FString&)
{
    using SoraFieldcraftAutomation::FBeatWorld;
    FBeatWorld W(*this,TEXT("ArchiveRevealReset"),5,8);if(!W.Start()) return false;
    W.Harden();ASoraBoss* Rival=nullptr;
    for(TActorIterator<ASoraBoss> It(W.World->GetTestWorld());It;++It) Rival=*It;
    if(!TestNotNull(TEXT("The real archive rival exists"),Rival)) return false;
    Rival->Hold(600000);
    for(int I=0;I<1800&&W.Campaign()->LinesQueued()>0;++I) if(!W.Tick(1)) return false;
    UGameplayStatics::ApplyDamage(Rival,Rival->MaxHealth*.5f,nullptr,W.Hero(),UDamageType::StaticClass());
    if(!W.Tick(180)||!TestTrue(TEXT("The reset occurs during the actual reveal"),W.Campaign()->IsArchiveRevealActive())) return false;
    W.Mode()->ResetRound();if(!W.Tick(1)) return false;
    auto* PC=Cast<APlayerController>(W.Hero()->GetController());
    TestTrue(TEXT("Checkpoint reset cancels camera ownership and restores phase one"),
        !W.Campaign()->IsArchiveRevealActive()&&W.Campaign()->ActivePhase()==0&&PC&&PC->GetViewTarget()==W.Hero());
    return PageIsLit(W,false)&&!HasAnyErrors();
}
#endif
