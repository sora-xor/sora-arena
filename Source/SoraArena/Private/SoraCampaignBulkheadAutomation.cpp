#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraBulkheadAutomation.h"
#include "SoraBoss.h"
#include "SoraEquipmentComponent.h"
#include "Components/BoxComponent.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/InputSettings.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCampaignBulkheadTest,"SoraArena.Campaign.BulkheadCapture",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCampaignBulkheadTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    const auto Actions=GetDefault<UInputSettings>()->GetActionMappings();
    const auto Axes=GetDefault<UInputSettings>()->GetAxisMappings();
    FString ControlSlot;
    ON_SCOPE_EXIT
    {
        TestTrue(TEXT("Bulkhead preserves global action mappings"),GetDefault<UInputSettings>()->GetActionMappings()==Actions);
        TestTrue(TEXT("Bulkhead preserves global axes"),GetDefault<UInputSettings>()->GetAxisMappings()==Axes);
        if(!ControlSlot.IsEmpty()) TestFalse(TEXT("Bulkhead deletes its isolated controls"),UGameplayStatics::DoesSaveGameExist(ControlSlot,0));
    };
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("BulkheadCapture"),5,12);
    ControlSlot=FSoraAutomationWorld::ControlSlot(W.Slot);
    if(!W.Start(0,INDEX_NONE,2)||!W.Tick(30)) return false;
    W.Harden(); SoraLiftAutomation::HoldThreats(*W.World);
    auto* Arena=W.Mode()->Arena();
    auto* Boss=const_cast<ASoraBoss*>(W.Campaign()->CampaignBoss());
    if(!TestNotNull(TEXT("The final Eskro phase has a living boss"),Boss)) return false;
    const auto Defeat=[&]()
    {
        auto* Target=Boss;
        if(!TestNotNull(TEXT("Eskro exists"),Target)) return false;
        // Setup only: boss combat is covered separately. This fixture owns
        // post-defeat traversal/input; threats are frozen, not auto-killed.
        SoraLiftAutomation::HoldThreats(*W.World);
        UGameplayStatics::ApplyDamage(Target,Target->Health,W.Hero()->GetController(),W.Hero(),UDamageType::StaticClass());
        return W.Tick(2)&&TestTrue(TEXT("Zero HP leaves a persistent yielded captive"),
            W.Campaign()->AwaitingCapture()&&W.Campaign()->IsCaptive(*Target)&&Target->GetLifeSpan()==0);
    };
    if(!SoraBulkheadAutomation::ApproachLever(*W.World)||!W.Hold(EKeys::E,130)) return false;
    TestTrue(TEXT("The lever cannot bind a living boss"),Boss->IsAlive()&&!W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()<0);
    if(!W.Press(EKeys::Escape)||!W.Hero()->RemapCombatAction(TEXT("Interact"),EKeys::G)) return false;
    W.Mode()->ResumePlay();
    if(!W.Tick(3)||!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.Tick(20)||!Defeat()||!W.Tick(130)) return false;
    TestTrue(TEXT("A press held before defeat cannot begin the capture"),W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()<0);
    if(!W.World->InjectKey(EKeys::G,IE_Released)||!W.Tick(1)) return false;
    FVector Objective;
    TestTrue(TEXT("Objective points to the entry lever, not Eskro"),W.Campaign()->ObjectiveAnchor(Objective)&&
        W.Campaign()->AnchorTakesInteract()&&Objective.Equals(Arena->BulkheadPoint(),1)&&
        FVector::Dist2D(Objective,Boss->GetActorLocation())>260);
    TestTrue(TEXT("Persistent objective explains the rebound two-second lever hold"),
        W.Campaign()->ObjectiveTextEnglish().Contains(TEXT("Hold G for 2 seconds")));
    W.Stand(Boss->GetActorLocation()+FVector(160,0,0));
    if(!W.Tick(3)||!W.Hold(EKeys::G,130)) return false;
    TestTrue(TEXT("Mapped held input at the captive cannot use the old shortcut"),W.Campaign()->AwaitingCapture());
    const FVector Goal=Arena->BulkheadApproach();
    // Wrong-floor placement is negative setup only; accepted approach below
    // uses navigation and swept character movement from the real floor.
    W.Hero()->GetCharacterMovement()->StopMovementImmediately();
    W.Hero()->SetActorLocation(Goal+FVector(0,0,-210),false,nullptr,ETeleportType::TeleportPhysics);
    W.Hero()->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    SoraBulkheadAutomation::FaceLever(*W.World);
    TestFalse(TEXT("Matching XY on another floor cannot reach the lever"),Arena->CanReachBulkhead(*W.Hero()));
    W.Hero()->SetActorLocation(Goal+FVector(600,0,90),false,nullptr,ETeleportType::TeleportPhysics);
    if(!W.Tick(4)||!SoraBulkheadAutomation::ApproachLever(*W.World)||!W.Hold(EKeys::E,130)) return false;
    TestTrue(TEXT("The old binding cannot start a remapped hold"),W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()<0);
    W.Mode()->Interact(W.Hero());
    if(!W.Tick(130)) return false;
    TestTrue(TEXT("A synthetic unheld interaction cannot seal the vault"),W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()<0);
    if(!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.Tick(30)) return false;
    const float Partial=W.Campaign()->HeldWorkProgress();
    if(!TestTrue(TEXT("Mapped hold starts visible progress"),Partial>0&&Partial<.3f)) return false;
    if(!W.World->InjectKey(EKeys::G,IE_Released)||!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.Tick(30)) return false;
    TestTrue(TEXT("Release and re-press between ticks discards elapsed work"),
        W.Campaign()->HeldWorkProgress()>0&&W.Campaign()->HeldWorkProgress()<=Partial+.02f);
    if(!W.Press(EKeys::Escape)) return false;
    TestTrue(TEXT("Pause immediately cancels the partial hold"),W.Mode()->bMenu&&W.Campaign()->HeldWorkProgress()<0);
    if(!W.World->InjectKeyPastFrontEnd(EKeys::G,IE_Released)||!W.World->InjectKeyPastFrontEnd(EKeys::G,IE_Pressed)||!W.Tick(150)) return false;
    W.Mode()->ResumePlay();
    if(!W.Tick(150)) return false;
    TestTrue(TEXT("Pause cannot bank work or restart a held press"),W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()<0);
    const auto Begin=[&]()
    {
        return W.World->InjectKey(EKeys::G,IE_Released)&&W.Tick(1)&&W.World->InjectKey(EKeys::G,IE_Pressed)&&W.Tick(30)&&
            TestTrue(TEXT("A fresh mapped press begins a new hold"),W.Campaign()->HeldWorkProgress()>0);
    };
    if(!Begin()) return false;
    W.Hero()->ResetDialogueInput();
    TestTrue(TEXT("Dialogue boundary clears held work immediately"),W.Campaign()->HeldWorkProgress()<0);
    if(!W.Tick(150)||!Begin()) return false;
    W.Look(FRotator(0,0,0));
    if(!W.Tick(1)) return false;
    SoraBulkheadAutomation::FaceLever(*W.World);
    if(!W.Tick(150)) return false;
    TestTrue(TEXT("Looking away cancels and returning while held cannot restart"),W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()<0);
    if(!Begin()) return false;
    W.Stand(Goal+FVector(600,0,0));
    if(!W.Tick(2)||!SoraBulkheadAutomation::ApproachLever(*W.World)||!W.Tick(150)) return false;
    TestTrue(TEXT("Leaving and returning requires a new press"),W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()<0);
    if(!Begin()) return false;
    SoraFieldcraftAutomation::FBeatWorld::Hurt(*W.Hero(),10);
    if(!W.Tick(150)) return false;
    TestTrue(TEXT("Damage discards the partial hold"),W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()<0);
    if(!W.World->InjectKey(EKeys::G,IE_Released)||!W.Tick(90)) return false;
    auto* Wall=W.World->GetTestWorld()->SpawnActor<AActor>();
    auto* Box=NewObject<UBoxComponent>(Wall); Wall->SetRootComponent(Box); Box->SetBoxExtent(FVector(10,100,100));
    Box->SetCollisionProfileName(TEXT("BlockAll")); Box->RegisterComponent(); Wall->AddInstanceComponent(Box);
    Wall->SetActorLocation(Arena->BulkheadPoint()+FVector(59,0,30));
    TestFalse(TEXT("A real wall occludes the lever"),Arena->CanReachBulkhead(*W.Hero()));
    if(!W.Hold(EKeys::G,130)) return false;
    TestTrue(TEXT("Held input cannot seal through the wall"),W.Campaign()->AwaitingCapture());
    Wall->Destroy();
    if(!W.Tick(2)||!Begin()) return false;
    auto* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    TestTrue(TEXT("Partial work leaves the authored phase checkpoint unchanged"),Saved&&Saved->CheckpointBeat==12&&Saved->CheckpointPhase==2);
    UGameplayStatics::ApplyDamage(W.Hero(),W.Hero()->Health+1000.f,nullptr,nullptr,UDamageType::StaticClass());
    if(!W.Tick(2)||!TestTrue(TEXT("Death cancels the partial hold before retry"),W.Mode()->bDefeated&&W.Campaign()->HeldWorkProgress()<0)||
        !W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    W.Harden(); Arena=W.Mode()->Arena(); Boss=const_cast<ASoraBoss*>(W.Campaign()->CampaignBoss());
    SoraLiftAutomation::HoldThreats(*W.World);
    TestTrue(TEXT("Retry restores a living P3 boss without partial capture"),Boss&&Boss->IsAlive()&&Boss->PhaseIndex()==2&&
        !W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()<0);
    if(!W.World->InjectKey(EKeys::G,IE_Released)||!Defeat()||!SoraBulkheadAutomation::ApproachLever(*W.World)||!Begin()) return false;
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    if(!W.World->DestroyTestWorld(true)) return false;
    W.World->ForwardErrorMessages(this); W.World.Reset(); W.EventsHandle.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if(!W.World->Start(W.Slot)||!W.Tick(1)||!W.World->EnableKeyInput()||
        !W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Press(EKeys::Enter)||!W.Tick(30)) return false;
    W.Harden(); Arena=W.Mode()->Arena(); Boss=const_cast<ASoraBoss*>(W.Campaign()->CampaignBoss());
    SoraLiftAutomation::HoldThreats(*W.World);
    TestTrue(TEXT("Fresh-process-style world reload restores a living P3 boss and no hold"),Boss&&Boss->IsAlive()&&Boss->PhaseIndex()==2&&
        !W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()<0);
    if(!Defeat()||!SoraBulkheadAutomation::ApproachLever(*W.World)||!W.World->InjectKey(EKeys::G,IE_Pressed)||!W.Tick(119)) return false;
    TestTrue(TEXT("119 frames at 60 Hz are shorter than the authored two seconds"),W.Campaign()->AwaitingCapture()&&W.Campaign()->HeldWorkProgress()>0);
    if(!W.Tick(3)||!W.World->InjectKey(EKeys::G,IE_Released)) return false;
    TestEqual(TEXT("A complete hold advances to the escape beat"),W.Campaign()->ActiveBeat(),13);
    TestFalse(TEXT("The vault is no longer awaiting capture"),W.Campaign()->AwaitingCapture());
    const auto CountLine=[&]()
    {
        int32 Count=0;
        for(const auto& Line:W.Campaign()->QueuedSubtitles()) if(Line.LineId==TEXT("ch06.b13.nyaakoto.003")) ++Count;
        return Count;
    };
    TestEqual(TEXT("The bulkhead line queues once"),CountLine(),1);
    if(!W.Press(EKeys::G)) return false;
    TestEqual(TEXT("Repeated input does not queue a second capture"),CountLine(),1);
    Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    TestTrue(TEXT("Only completion advances the saved checkpoint"),Saved&&Saved->CheckpointBeat==13&&Saved->CheckpointPhase==0);
    return !HasAnyErrors();
}
#endif
