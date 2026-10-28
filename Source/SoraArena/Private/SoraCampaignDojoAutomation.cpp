#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraDojoAutomation.h"
#include "SoraFieldcraftTestWorld.h"
#include "SoraFrontEnd.h"
#include "SoraSettings.h"
#include "SoraHUD.h"
#include "HUD/SoraHUDPanels.h"

namespace SoraDojoTests
{
using SoraFieldcraftAutomation::FBeatWorld;
using namespace SoraDojoAutomation;
bool Menu(FBeatWorld& W,SoraUI::EAction Action)
{
    for(int32 Press=0;Press<12;++Press)
    {
        auto* Menu=W.Mode()->FrontEnd();
        if(Menu->Rows().IsValidIndex(Menu->Focus())&&Menu->Rows()[Menu->Focus()].Action==Action) return W.Press(EKeys::Enter);
        if(!W.Press(EKeys::Down)) return false;
    }
    return W.Test.TestTrue(TEXT("The ordinary menu action is reachable"),false);
}
bool Reload(FBeatWorld& W)
{
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    if(!W.World->DestroyTestWorld(true)) return false;
    W.World->ForwardErrorMessages(&W.Test); W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    return W.World->Start(W.Slot)&&W.Tick(1)&&W.World->EnableKeyInput()&&
        W.Press(EKeys::Enter)&&W.Press(EKeys::Enter)&&W.Press(EKeys::Enter)&&W.Tick(30);
}
bool LearnRecovery(FBeatWorld& W)
{
    FMeeting Met;
    if(!Meet(W.Test,*W.World,false,Met)||!W.Test.TestEqual(TEXT("A real front guard opens awase"),W.Campaign()->DojoLessonStage(),2)) return false;
    for(int32 Repetition=0;Repetition<2;++Repetition)
        if(!Meet(W.Test,*W.World,true,Met)) return false;
    if(!W.Test.TestEqual(TEXT("Two actual awase contacts open recovery"),W.Campaign()->DojoLessonStage(),3)) return false;
    // Swing toward empty sky, release, then let the real catalog recovery end.
    W.Look(FRotator(75,W.Hero()->GetActorRotation().Yaw,0));
    if(!W.Press(EKeys::LeftMouseButton)) return false;
    for(int32 Frame=0;Frame<90&&W.Campaign()->DojoLessonStage()<4;++Frame)
        if(!W.Tick(1)) return false;
    return W.Test.TestEqual(TEXT("A real released cut teaches the recovery form"),W.Campaign()->DojoLessonStage(),4);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraOpeningTextWrapTest,"SoraArena.UI.OpeningTextWrap",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraOpeningTextWrapTest::RunTest(const FString& Parameters)
{
    using namespace SoraDojoTests;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("OpeningTextWrap"),0,2);
    if(!W.Start()) return false;
    auto* HUD=W.World->GetTestWorld()->SpawnActor<ASoraHUD>();
    if(!TestNotNull(TEXT("The production HUD spawns"),HUD)) return false;
    const FString Sentence=TEXT("Keep a distance from the pupil.");
    const float Width=HUD->LabelWidth(TEXT("Keep a distan"),.6f);
    const auto English=HUD->WrappedLines(Sentence,.6f,Width);
    TestTrue(TEXT("A constrained English line wraps"),English.Num()>1);
    TestEqual(TEXT("Wrapping keeps every English word intact and in order"),FString::Join(English,TEXT(" ")),Sentence);
    for(const auto& Line:English) TestTrue(TEXT("Each wrapped English line fits"),HUD->LabelWidth(Line,.6f)<=Width+1.f);
    const FString Japanese=TEXT("相手に向き、防御を保って一撃を受ける。");
    const auto Wrapped=HUD->WrappedLines(Japanese,.65f,180.f);
    TestTrue(TEXT("Japanese without spaces wraps"),Wrapped.Num()>1);
    TestEqual(TEXT("Wrapping retains the complete Japanese text"),FString::Join(Wrapped,TEXT("")),Japanese);
    const auto Explicit=HUD->WrappedLines(TEXT("First line\nSecond line"),.6f,800.f);
    TestEqual(TEXT("An explicit line break is retained"),FString::Join(Explicit,TEXT("\n")),FString(TEXT("First line\nSecond line")));
    TestTrue(TEXT("An empty label draws no rows"),HUD->WrappedLines(TEXT(""),.6f,800.f).IsEmpty());
    // Exercise actual authored opening copy, not a synthetic replacement.
    for(const FVector2D Size:{FVector2D(1280,720),FVector2D(1920,1080),FVector2D(2560,1080)})
    {
        const FSoraHUDFrame Frame(*HUD,*W.Mode(),Size.X,Size.Y);
        const auto& Chapter=FSoraCatalog::Get().Chapter(0);
        const auto Rows=HUD->WrappedLines(Chapter.NarrativeEnglish,Frame.EnglishSubtitleScale,Size.X-240*Frame.S);
        TestTrue(TEXT("The opening narrative fits the chapter card's four rows"),Rows.Num()<=4);
        TestEqual(TEXT("The actual opening keeps its complete words"),FString::Join(Rows,TEXT(" ")),Chapter.NarrativeEnglish);
    }
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraDojoPromptLayoutTest,"SoraArena.UI.DojoPromptLayout",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraDojoPromptLayoutTest::RunTest(const FString& Parameters)
{
    using namespace SoraDojoTests;
    if(!FSoraCatalog::Get().Load()) return false;
    FBeatWorld W(*this,TEXT("DojoPromptLayout"),0,2);
    if(!W.Start()||!W.Tick(30)) return false;
    auto* HUD=W.World->GetTestWorld()->SpawnActor<ASoraHUD>();
    if(!TestNotNull(TEXT("The production HUD spawns"),HUD)) return false;
    if(!W.Press(EKeys::Escape)||!TestTrue(TEXT("Guard can be rebound in the ordinary menu"),W.Hero()->RemapCombatAction(TEXT("Guard"),EKeys::J))||
        !Menu(W,SoraUI::EAction::Resume)) return false;
    const auto Check=[&](const TCHAR* Action)
    {
        for(const auto Device:{SoraUI::EDevice::KeyboardMouse,SoraUI::EDevice::Gamepad})
        {
            W.Mode()->FrontEnd()->NoteDevice(Device);
            const auto Key=SoraUI::ActionKey(HUD,Action);
            TestTrue(TEXT("The Japanese lesson names the current bound control"),W.Campaign()->DojoLessonText(false).Contains(Key.Japanese));
            TestTrue(TEXT("The English lesson names the current bound control"),W.Campaign()->DojoLessonText(true).Contains(Key.English));
            for(bool English:{false,true})
            {
                W.Mode()->Settings()->SetEnglishSubtitles(English);
                for(const FVector2D Size:{FVector2D(1280,720),FVector2D(1920,1080),FVector2D(2560,1080)})
                {
                    FString Why;
                    const FSoraHUDFrame Frame(*HUD,*W.Mode(),Size.X,Size.Y);
                    const bool Fits=SoraHUDPanels::DojoLayoutFits(Frame,Why);
                    TestTrue(*FString::Printf(TEXT("Lesson %d fits %.0fx%.0f: %s"),W.Campaign()->DojoLessonStage(),Size.X,Size.Y,*Why),Fits);
                }
            }
        }
        W.Mode()->FrontEnd()->NoteDevice(SoraUI::EDevice::KeyboardMouse);
    };
    TestEqual(TEXT("The guard hint uses the rebound key"),SoraUI::ActionKey(HUD,TEXT("Guard")).English,FString(TEXT("J")));
    Check(TEXT("Guard"));
    FMeeting Met;
    if(!Meet(*this,*W.World,false,Met,EKeys::J)) return false;
    TestEqual(TEXT("Real front guard opens parry coaching"),W.Campaign()->DojoLessonStage(),2);
    Check(TEXT("Guard"));
    if(!Meet(*this,*W.World,true,Met,EKeys::J)||!Meet(*this,*W.World,true,Met,EKeys::J)) return false;
    TestEqual(TEXT("Real parries open recovery coaching"),W.Campaign()->DojoLessonStage(),3);
    Check(TEXT("Fire"));
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraDojoGuardLessonsTest,"SoraArena.Campaign.DojoGuardLessons",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraDojoGuardLessonsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraDojoTests;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    for(const auto Difficulty:{SoraAccessibility::EDifficulty::Easy,SoraAccessibility::EDifficulty::Normal,SoraAccessibility::EDifficulty::Hard})
    {
        FBeatWorld W(*this,TEXT("DojoGuardLessons"),0,2);
        if(!W.Start()) return false;
        W.Mode()->Settings()->SetCampaignDifficulty(Difficulty);
        if(!W.Tick(30)||!LearnRecovery(W)) return false;
        TestTrue(TEXT("The real front-guard gate retains enough stamina at this difficulty"),
            W.Hero()->GetEquipment()->GuardReserve()>=SoraCombatRules::MinimumGuardStamina);
        TestEqual(TEXT("Learning the forms alone never awards a bout"),W.Campaign()->TaskProgress().Done,0);
        TestTrue(TEXT("No point means no passive reward"),W.Hero()->GetEquipment()->LastZanshinAt()<0.f);
    }
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraDojoAwaseHintTest,"SoraArena.Campaign.DojoAwaseHint",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraDojoAwaseHintTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraDojoTests;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    {
        FBeatWorld W(*this,TEXT("DojoAwaseMiss"),0,3);
        if(!W.Start()||!W.Tick(30)) return false;
        FMeeting Met;
        if(!Meet(*this,*W.World,false,Met)||!W.Tick(35)) return false;
        TestEqual(TEXT("An ordinary early guard cannot arm the missed-awase hint"),HintCount(*W.Campaign()),0);
        if(!Meet(*this,*W.World,true,Met)) return false;
        auto* C=W.Campaign();
        for(int32 Frame=0;Frame<90&&C->TaskProgress().ElapsedMs-Met.BeatMs<280;++Frame) if(!W.Tick(1)) return false;
        if(!TestTrue(TEXT("Ordinary gameplay advances the awase timer"),C->TaskProgress().ElapsedMs-Met.BeatMs>=280)) return false;
        TestEqual(TEXT("The hint waits for the complete 400 ms opportunity"),HintCount(*C),0);
        if(!W.Press(EKeys::Escape)) return false;
        const int32 PausedAt=C->TaskProgress().ElapsedMs;
        if(!W.Tick(120)) return false;
        TestEqual(TEXT("Paused time cannot expire the gameplay hint timer"),C->TaskProgress().ElapsedMs,PausedAt);
        TestEqual(TEXT("A paused awase has not yet missed its step"),HintCount(*C),0);
        if(!Menu(W,SoraUI::EAction::Resume)) return false;
        for(int32 Frame=0;Frame<90&&C->TaskProgress().ElapsedMs-Met.BeatMs<=SoraCombatRules::MarobashiWindowMs;++Frame)
            if(!W.Tick(1)) return false;
        TestEqual(TEXT("The real missed awase queues Sekireisai's exact authored line once"),HintCount(*C),1);
        if(!W.Tick(45)) return false;
        TestEqual(TEXT("An expired awase does not repeatedly queue the hint"),HintCount(*C),1);
    }
    {
        FBeatWorld W(*this,TEXT("DojoAwaseStep"),0,3);
        if(!W.Start()||!W.Tick(30)) return false;
        FMeeting Met;
        if(!Meet(*this,*W.World,true,Met)||!Step(*this,*W.World)||!W.Tick(20)) return false;
        TestEqual(TEXT("Actual Step cancels the missed-step timer"),HintCount(*W.Campaign()),0);
        TestEqual(TEXT("A flank alone cannot score the bout"),W.Campaign()->TaskProgress().Done,0);
    }
    {
        FBeatWorld W(*this,TEXT("DojoAwaseRetry"),0,3);
        // Reach b04 from b03 with input, so Retry proves that the real
        // newly-written b04 checkpoint preserves forms but clears its attempt.
        if(!W.Start(0,2)||!W.Tick(30)||!LearnRecovery(W)||
            !StrikePupil(*this,*W.World)||!StrikePupil(*this,*W.World)||
            !TestEqual(TEXT("Two real lesson points open b04"),W.Campaign()->ActiveBeat(),3)) return false;
        FMeeting Met;
        if(!Meet(*this,*W.World,true,Met)||!W.Press(EKeys::Escape)||
            !Menu(W,SoraUI::EAction::Restart)||!Menu(W,SoraUI::EAction::ConfirmYes)||!W.Tick(40)) return false;
        TestEqual(TEXT("Checkpoint retry restores the authored b04 checkpoint"),W.Campaign()->ActiveBeat(),3);
        TestEqual(TEXT("The completed b03 forms survive retry"),W.Campaign()->DojoLessonStage(),4);
        TestEqual(TEXT("A pre-retry awase cannot leak its hint into the restored lesson"),HintCount(*W.Campaign()),0);
    }
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraDojoZanshinTest,"SoraArena.Campaign.DojoZanshin",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraDojoZanshinTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraDojoTests;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    {
        FBeatWorld W(*this,TEXT("DojoZanshin"),0,2);
        if(!W.Start()||!W.Tick(30)) return false;
        auto* Kit=W.Hero()->GetEquipment();
        TestEqual(TEXT("The guard lesson begins before passive recovery is learned"),W.Campaign()->DojoLessonStage(),1);
        if(!LearnRecovery(W)) return false;
        // Resource is spent through the normal held guard, not a fixture write.
        if(!W.World->InjectKey(EKeys::LeftControl,IE_Pressed)) return false;
        for(int32 Frame=0;Frame<90&&Kit->GuardReserve()>88.f;++Frame) if(!W.Tick(1)) return false;
        TestTrue(TEXT("Learned dojo guard now has the existing stamina cost"),Kit->GuardReserve()<90.f);
        if(!StrikePupil(*this,*W.World)) return false;
        if(!TestEqual(TEXT("Real cuts score the first accepted lesson point"),W.Campaign()->TaskProgress().Done,1)) return false;
        if(!TestTrue(TEXT("The point leaves an active guard with room for the authored reward"),
            Kit->IsGuardHeld()&&Kit->GuardReserve()>=SoraCombatRules::MinimumGuardStamina&&Kit->GuardReserve()<85.f)) return false;
        const float Before=Kit->GuardReserve();
        const float PointAt=W.World->GetTestWorld()->GetTimeSeconds();
        if(!W.Tick(12)) return false;
        TestTrue(TEXT("A short post-point hold grants no reward"),Kit->LastZanshinAt()<0.f&&FMath::IsNearlyEqual(Kit->GuardReserve(),Before,.01f));
        if(!W.World->InjectKey(EKeys::LeftControl,IE_Released)||!W.Tick(1)||
            !W.World->InjectKey(EKeys::LeftControl,IE_Pressed)) return false;
        const float HeldAt=W.World->GetTestWorld()->GetTimeSeconds();
        const float Reserve=Kit->GuardReserve();
        for(int32 Frame=0;Frame<90&&(W.World->GetTestWorld()->GetTimeSeconds()-HeldAt)*1000.f<450.f;++Frame) if(!W.Tick(1)) return false;
        TestTrue(TEXT("Release resets the required continuous half-second"),Kit->LastZanshinAt()<0.f);
        for(int32 Frame=0;Frame<15&&Kit->LastZanshinAt()<0.f;++Frame) if(!W.Tick(1)) return false;
        TestTrue(TEXT("Holding guard for the complete half-second earns zanshin"),
            Kit->LastZanshinAt()>=HeldAt+.5f&&Kit->LastZanshinAt()-PointAt<2.5f);
        TestTrue(TEXT("A scored point restores exactly fifteen stamina"),FMath::IsNearlyEqual(Kit->GuardReserve(),Reserve+15.f,.02f));
        const float AwardedAt=Kit->LastZanshinAt();
        if(!W.Tick(15)) return false;
        TestEqual(TEXT("Continuing the same hold cannot award twice"),Kit->LastZanshinAt(),AwardedAt);
        TestTrue(TEXT("Ordinary stamina drain resumes after the passive"),Kit->GuardReserve()<Reserve+15.f);
        // The winning point arms a fresh opportunity. Reload before its
        // half-second can complete, so this also tests pending-state cleanup.
        if(!StrikePupil(*this,*W.World)||
            !TestEqual(TEXT("The winning actual point opens the yard"),W.Campaign()->ActiveBeat(),3)) return false;
        TestEqual(TEXT("The new point has not already awarded a second recovery"),Kit->LastZanshinAt(),AwardedAt);
        W.Campaign()->SaveProgress();
        const auto* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
        if(!TestNotNull(TEXT("The real checkpoint save exists"),Saved)||
            !TestEqual(TEXT("The yard transition saves the authored b04 checkpoint"),Saved->CheckpointBeat,3)) return false;
        if(!Reload(W)) return false;
        Kit=W.Hero()->GetEquipment();
        TestEqual(TEXT("Reload retains the real checkpoint's completed recovery form"),W.Campaign()->DojoLessonStage(),4);
        TestEqual(TEXT("Reload restores b04 with no partial points"),W.Campaign()->TaskProgress().Done,0);
        TestTrue(TEXT("Fresh-world load has no previous reward or pending point"),Kit->LastZanshinAt()<0.f);
        if(!W.Hold(EKeys::LeftControl,36)) return false;
        TestTrue(TEXT("A checkpoint's old point cannot be replayed for stamina"),Kit->LastZanshinAt()<0.f);
    }
    {
        FBeatWorld W(*this,TEXT("DojoRefusedZanshin"),0,3);
        if(!W.Start()||!W.Tick(30)||!W.World->InjectKey(EKeys::LeftControl,IE_Pressed)||
            !StrikePupil(*this,*W.World)) return false;
        auto* Kit=W.Hero()->GetEquipment();
        TestEqual(TEXT("Defeating a pupil without the required flank scores nothing"),W.Campaign()->TaskProgress().Done,0);
        if(!W.World->InjectKey(EKeys::LeftControl,IE_Released)||!W.Tick(90)||
            !W.Hold(EKeys::LeftControl,36)) return false;
        TestTrue(TEXT("A refused bout never arms passive stamina recovery"),Kit->LastZanshinAt()<0.f);
    }
    return !HasAnyErrors();
}
#endif
