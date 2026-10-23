#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraArcheryAutomation.h"
#include "SoraFieldcraftTestWorld.h"
#include "SoraFrontEnd.h"
#include "SoraSettings.h"
#include "SoraViewmodelComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/InputSettings.h"
#include "Misc/ScopeExit.h"

namespace
{
bool Fetch(SoraFieldcraftAutomation::FBeatWorld& W)
{
    for(int32 Frame=0;Frame<510&&W.Campaign()->ArcheryProgress().FetchRemainingMs>0;++Frame)
        if(!W.Tick(1)) return false;
    return W.Campaign()->ArcheryProgress().FetchRemainingMs==0;
}
bool ReloadWorld(SoraFieldcraftAutomation::FBeatWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    if(!W.World->DestroyTestWorld(true)) return false;
    W.World->ForwardErrorMessages(&W.Test); W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    return W.World->Start(W.Slot)&&W.Tick(1)&&W.World->EnableKeyInput()&&
        W.Press(EKeys::Enter)&&W.Press(EKeys::Enter)&&W.Press(EKeys::Enter)&&W.Tick(30);
}
bool MenuAction(SoraFieldcraftAutomation::FBeatWorld& W,SoraUI::EAction Action)
{
    auto* Menu=W.Mode()->FrontEnd();
    for(int32 Press=0;Press<12;++Press)
    {
        const auto& Rows=Menu->Rows();
        if(Rows.IsValidIndex(Menu->Focus())&&Rows[Menu->Focus()].Action==Action) return W.Press(EKeys::Enter);
        if(!W.Press(EKeys::Down)) return false;
    }
    return false;
}
bool Smithy(SoraFieldcraftAutomation::FBeatWorld& W)
{
    for(int32 Action=0;Action<32&&W.Campaign()->ActiveBeat()==8;++Action)
    {
        auto* C=W.Campaign();
        const int32 Step=C->TaskProgress().Step;
        const auto* Space=C->ActiveSpace();
        const FVector2D Station=Space->Stations[Space->StepStations[Step]];
        if(!SoraLiftAutomation::Walk(*W.World,FVector(Station.X-145,Station.Y,Space->HeightCm))) return false;
        const auto& State=C->TaskProgress(); const auto& Rules=C->ActiveTask();
        if(State.LastActionMs>=0&&Rules.Steps[Step].BeatMs>0)
        {
            const int32 Wait=Rules.Steps[Step].BeatMs-(State.ElapsedMs-State.LastActionMs);
            if(Wait>0&&!W.Tick(FMath::CeilToInt(Wait*60.f/1000.f))) return false;
        }
        if(!W.Press(EKeys::E)) return false;
    }
    return W.Campaign()->ActiveBeat()==9;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraArcheryLessonTest,"SoraArena.Campaign.ArcheryLesson",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraArcheryLessonTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraArcheryRules;
    if(!TestTrue(TEXT("Catalog loads the authored range contract"),FSoraCatalog::Get().Load())) return false;
    const auto OriginalActions=GetDefault<UInputSettings>()->GetActionMappings();
    FString Controls;
    ON_SCOPE_EXIT
    {
        TestTrue(TEXT("Archery restores global input mappings"),OriginalActions==GetDefault<UInputSettings>()->GetActionMappings());
        if(!Controls.IsEmpty()) TestFalse(TEXT("Archery deletes the rebound control profile"),UGameplayStatics::DoesSaveGameExist(Controls,0));
    };
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("Archery"),0,6);
    Controls=FSoraAutomationWorld::ControlSlot(W.Slot);
    if(!W.Start()||!W.Tick(30)) return false;
    auto* C=W.Campaign(); auto* Kit=W.Hero()->GetEquipment();
    TestTrue(TEXT("The active beat is a range, not generic pupil kills"),C->IsArcheryLesson());
    TestEqual(TEXT("B07 begins with the own twelve-arrow quiver"),Kit->AmmoByWeapon[18],12);
    for(TActorIterator<ASoraEnemy> It(W.World->GetTestWorld());It;++It)
        TestFalse(TEXT("No generic pupil stands in for a mato"),It->IsAlive());
    for(int32 I=0;I<4;++I) if(!TestNotNull(TEXT("Each authored target has a physical actor"),C->ArcheryTarget(I))) return false;
    for(int32 I=0;I<4;++I)
    {
        const int32 Phase=I?FMath::RoundToInt32(float(4-I)*PeriodMs/3.f):0;
        // A complete cycle minus the target's phase gives the rest center.
        const FVector Rest=C->ArcheryTarget(I)->CenterAt(Phase);
        TestTrue(TEXT("Target rest distances match the authored range"),FMath::IsNearlyEqual(
            FVector::Dist2D(Rest,C->ArcheryLine()),double(I?HangingCm[I-1]:NearCm),1.0));
    }
    const auto Difficulty=int32(SoraAccessibility::CampaignDifficulty(W.Mode()));
    TestEqual(TEXT("Near collider honors current difficulty"),C->ArcheryTarget(0)->ScoringRadius(),float(HitRadius[Difficulty]));
    if(!TestTrue(TEXT("Normal movement reaches the line and key 3 equips the unlocked bow"),SoraArcheryAutomation::EnterLine(*W.World))) return false;
    TArray<USceneComponent*> HeldParts;
    W.Hero()->GetViewmodel()->GetChildrenComponents(true,HeldParts);
    TestTrue(TEXT("Normal bow equip builds the actual yumi proxy, not the authored bokken mesh"),
        HeldParts.ContainsByPredicate([](const USceneComponent* Part) { return Part->GetName().StartsWith(TEXT("YumiUpper")); })&&
        !HeldParts.ContainsByPredicate([](const USceneComponent* Part) { return Part->GetName().StartsWith(TEXT("OriginalWeaponMesh")); }));
    TestEqual(TEXT("The held arm retains the catalog's yumi label"),FSoraCatalog::Get().Weapon(W.Hero()->WeaponId).NameEnglish,
        FString(TEXT("Yumi")));
    UGameplayStatics::ApplyDamage(C->ArcheryTarget(0),10000,nullptr,W.Hero(),UDamageType::StaticClass());
    TestEqual(TEXT("Generic damage cannot score an arrow"),C->ArcheryProgress().Hits,0);
    if(!W.Hold(EKeys::LeftMouseButton,10)) return false;
    TestEqual(TEXT("An incomplete draw spends no arrow"),Kit->Ammo,12);
    TestEqual(TEXT("An incomplete draw issues no shot"),C->ArcheryProgress().Issued,0);
    if(!W.World->InjectKey(EKeys::LeftShift,IE_Pressed)||!W.Hold(EKeys::LeftMouseButton,45)||
        !W.World->InjectKey(EKeys::LeftShift,IE_Released)) return false;
    TestEqual(TEXT("Sprinting cannot draw or loose"),Kit->Ammo,12);
    if(!SoraLiftAutomation::Walk(*W.World,C->ArcheryLine()+FVector(0,-350,0))||
        !TestFalse(TEXT("The wrong lane position is not the shooting line"),C->AtArcheryLine())||
        !SoraArcheryAutomation::Loose(*this,*W.World,0)) return false;
    if(!TestEqual(TEXT("The off-line arrow really impacted the scoring circle"),C->ArcheryProgress().LastTarget,0)) return false;
    TestEqual(TEXT("Even a real target impact outside the line scores a miss"),C->ArcheryProgress().Hits,0);
    if(!SoraLiftAutomation::Walk(*W.World,C->ArcheryLine())) return false;
    for(int32 Shot=0;Shot<3;++Shot)
        if(!SoraArcheryAutomation::Loose(*this,*W.World,0)||
            !TestEqual(TEXT("Real near-target impacts count exactly once"),C->ArcheryProgress().Hits,Shot+1)) return false;
    for(int32 Shot=0;Shot<2;++Shot) if(!SoraArcheryAutomation::Loose(*this,*W.World,-1)) return false;
    if(!TestTrue(TEXT("Three hits in six resolved arrows fails the set"),C->ArcheryProgress().Stage==EStage::Near&&C->ArcheryProgress().FetchRemainingMs>0)) return false;
    TestEqual(TEXT("The failed set spent exactly six arrows"),Kit->Ammo,6);
    TestTrue(TEXT("Failed set raises the exact keeper line"),C->QueuedSubtitles().ContainsByPredicate(
        [](const FSoraSubtitle& L) { return L.LineId==TEXT("ch01.b07.baio.007"); }));
    const int32 Remaining=C->ArcheryProgress().FetchRemainingMs;
    if(!W.Press(EKeys::Escape)||!W.Tick(120)) return false;
    TestEqual(TEXT("Menu time cannot advance retrieval"),C->ArcheryProgress().FetchRemainingMs,Remaining);
    if(!W.Hero()->RemapCombatAction(TEXT("WeaponThree"),EKeys::G)) return false;
    W.Mode()->ResumePlay();
    if(!W.Tick(1)||!W.Press(EKeys::R)) return false;
    TestEqual(TEXT("Reload cannot bypass keeper time"),Kit->Ammo,6);
    const int32 BeforeWait=C->ArcheryProgress().FetchRemainingMs;
    if(!W.Tick(FMath::Max(0,FMath::FloorToInt(BeforeWait*60.f/1000.f)-2))) return false;
    TestTrue(TEXT("Fewer than eight gameplay seconds never refill"),C->ArcheryProgress().FetchRemainingMs>0&&Kit->Ammo==6);
    if(!TestTrue(TEXT("Eight seconds retrieves the own arrows"),Fetch(W))) return false;
    TestEqual(TEXT("Retrieved quiver is twelve, not an unlimited reload"),Kit->Ammo,12);
    if(!W.Press(EKeys::One)||!W.Press(EKeys::Three)) return false;
    TestEqual(TEXT("Former bow binding does not equip after remap"),W.Hero()->WeaponId,0);
    if(!W.Press(EKeys::G)||!TestEqual(TEXT("Mapped bow action equips the yumi"),W.Hero()->WeaponId,18)) return false;
    for(int32 Shot=0;Shot<6;++Shot)
    {
        if(!SoraArcheryAutomation::Loose(*this,*W.World,Shot<4?0:-1)) return false;
        if(Shot<5) TestTrue(TEXT("Four hits alone cannot skip the six-shot set"),C->ArcheryProgress().Stage==EStage::Near);
    }
    if(!TestTrue(TEXT("Four hits among six resolved shots unlock all hanging targets"),C->ArcheryProgress().Stage==EStage::Hanging)) return false;
    TestEqual(TEXT("The successful near set leaves six real arrows"),Kit->Ammo,6);
    const FVector Moving=C->ArcheryTarget(1)->GetActorLocation();
    if(!W.Tick(60)) return false;
    TestTrue(TEXT("Hanging target collision moves with its visible swing"),FVector::Dist(Moving,C->ArcheryTarget(1)->GetActorLocation())>10);
    if(!SoraArcheryAutomation::Loose(*this,*W.World,1)||
        !TestEqual(TEXT("A led moving-target arrow earns only that target"),C->ArcheryProgress().HangingHits,1u)) return false;
    if(!SoraArcheryAutomation::Loose(*this,*W.World,1)) return false;
    TestEqual(TEXT("A repeated shot at the completed target earns nothing"),C->ArcheryProgress().HangingHits,1u);
    while(Kit->Ammo>0) if(!SoraArcheryAutomation::Loose(*this,*W.World,-1)) return false;
    if(!W.Tick(2)||!TestTrue(TEXT("Exhausted hanging arrows start an explicit timed recovery"),C->ArcheryProgress().FetchRemainingMs>0)) return false;
    TestEqual(TEXT("Recovery retains the one earned hanging hit"),C->ArcheryProgress().HangingHits,1u);
    if(!W.Press(EKeys::R)) return false;
    TestEqual(TEXT("Empty-quiver Reload grants no arrows"),Kit->Ammo,0);
    if(!TestTrue(TEXT("Exhaustion recovery prevents a hanging-stage softlock"),Fetch(W))) return false;
    TestEqual(TEXT("Recovery grants no target progress"),C->ArcheryProgress().HangingHits,1u);
    for(int32 Target=2;Target<=3;++Target) if(!SoraArcheryAutomation::Loose(*this,*W.World,Target)) return false;
    if(!TestTrue(TEXT("Three independently earned hanging hits open the physical route choice"),C->IsWoodTransit())) return false;
    if(!ReloadWorld(W)) return false;
    C=W.Campaign(); Kit=W.Hero()->GetEquipment();
    if(!TestTrue(TEXT("Fresh-world reload retains completed b07 and the physical choice"),C->IsWoodTransit()&&
        (C->Progress().CompletedMask&SoraBeatRules::BeatBit(6))!=0)) return false;
    if(!TestTrue(TEXT("Actual terrace walking reaches the smithy without completing wood"),SoraWoodAutomation::Terrace(*W.World))) return false;
    TestEqual(TEXT("The terrace preserves optional b08"),C->Progress().CompletedMask&SoraBeatRules::BeatBit(7),0u);
    TestEqual(TEXT("The authored stone-damaged batch has six usable arrows"),W.Hero()->GetEquipment()->AmmoByWeapon[18],6);
    TestEqual(TEXT("Six bent arrows motivate manufacture"),C->BentArrows(),6);
    auto* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    if(!TestNotNull(TEXT("The completed range saves the smithy checkpoint"),Saved)) return false;
    TestEqual(TEXT("The checkpoint is b09, not partial target progress"),Saved->CheckpointBeat,8);
    if(!ReloadWorld(W)||!W.Press(EKeys::G)||!W.Tick(30)) return false;
    C=W.Campaign(); Kit=W.Hero()->GetEquipment();
    TestEqual(TEXT("A fresh b09 checkpoint restores six usable arrows"),Kit->Ammo,6);
    TestEqual(TEXT("A fresh b09 checkpoint restores six bent arrows"),C->BentArrows(),6);
    if(!W.Press(EKeys::R)) return false;
    TestEqual(TEXT("Reload cannot replace the manufacture work"),Kit->Ammo,6);
    if(!TestTrue(TEXT("Actual station movement and Interact finish the repair recipe"),Smithy(W))) return false;
    TestEqual(TEXT("Only completed manufacture restores twelve usable arrows"),Kit->Ammo,12);
    TestEqual(TEXT("Manufacture consumes all six bent arrows"),C->BentArrows(),0);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraArcheryReloadTest,"SoraArena.Campaign.ArcheryReload",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraArcheryReloadTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    // Range access must not unlock the bow early or replace the later
    // fukuro-shinai match's specified weapon.
    for(int32 Beat:{2,10})
    {
        SoraFieldcraftAutomation::FBeatWorld Bound(*this,TEXT("ArcheryLoadout"),0,Beat);
        if(!Bound.Start()||!Bound.Tick(30)||!Bound.Press(EKeys::Three)) return false;
        TestEqual(TEXT("Sword lessons and the later sparring duel keep their practice sword"),Bound.Hero()->WeaponId,0);
        if(Beat==2) TestFalse(TEXT("The early sword lesson has not unlocked the yumi"),Bound.Campaign()->IsWeaponUnlocked(18));
        else
        {
            TestTrue(TEXT("The later duel keeps the earned yumi unlock"),Bound.Campaign()->IsWeaponUnlocked(18));
            TestFalse(TEXT("Its authored sparring restriction forbids holding the bow"),Bound.Campaign()->CanHold(18,false));
            TestEqual(TEXT("A checkpoint after the smithy has twelve repaired arrows"),Bound.Hero()->GetEquipment()->AmmoByWeapon[18],12);
            TestEqual(TEXT("A later checkpoint has no remaining bent arrows"),Bound.Campaign()->BentArrows(),0);
        }
    }
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("ArcheryReload"),0,6);
    if(!W.Start()||!SoraArcheryAutomation::EnterLine(*W.World)) return false;
    for(int32 Shot=0;Shot<2;++Shot) if(!SoraArcheryAutomation::Loose(*this,*W.World,0)) return false;
    if(!TestEqual(TEXT("Two actual hits precede the checkpoint retry"),W.Campaign()->ArcheryProgress().Hits,2)) return false;
    W.Campaign()->SaveProgress();
    if(!W.Press(EKeys::Escape)||!MenuAction(W,SoraUI::EAction::Restart)||
        !MenuAction(W,SoraUI::EAction::ConfirmYes)||!W.Tick(30)) return false;
    TestEqual(TEXT("Ordinary menu retry returns to the range checkpoint"),W.Campaign()->ActiveBeat(),6);
    TestEqual(TEXT("Retry cannot preserve partial set hits"),W.Campaign()->ArcheryProgress().Hits,0);
    TestEqual(TEXT("Retry begins with the authored own quiver"),W.Hero()->GetEquipment()->AmmoByWeapon[18],12);
    if(!SoraArcheryAutomation::EnterLine(*W.World)||!SoraArcheryAutomation::Loose(*this,*W.World,0)) return false;
    W.Campaign()->SaveProgress();
    if(!ReloadWorld(W)) return false;
    TestEqual(TEXT("Fresh-world reload has no partial set"),W.Campaign()->ArcheryProgress().Resolved,0);
    TestEqual(TEXT("Fresh-world reload has no stale in-flight identity"),SoraArcheryRules::Pending(W.Campaign()->ArcheryProgress()),0);
    TestEqual(TEXT("Fresh-world reload restores twelve usable arrows"),W.Hero()->GetEquipment()->AmmoByWeapon[18],12);
    TestEqual(TEXT("No bent arrows are granted before completing b07"),W.Campaign()->BentArrows(),0);
    return !HasAnyErrors();
}
#endif
