#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "SoraEquipmentComponent.h"
#include "SoraProjectile.h"

using namespace SoraFieldcraftAutomation;

namespace
{
FString LineId(const FBeatWorld& W)
{
    const FSoraDialogueCue* Cue=W.Campaign()->CurrentDialogueCue();
    return Cue?Cue->Id:FString();
}
bool Until(FBeatWorld& W,TFunctionRef<bool()> Done,int32 Frames=600)
{
    for(int32 Frame=0;Frame<Frames&&!Done();++Frame)
        if(!W.Tick(1,.1f)) return false;
    return W.Test.TestTrue(TEXT("The authored dialogue transition occurs"),Done());
}
bool StartAtAnchor(FBeatWorld& W)
{
    FVector Anchor;
    if(!W.Test.TestTrue(TEXT("The required trigger has an anchor"),W.Campaign()->ObjectiveAnchor(Anchor))) return false;
    W.Stand(Anchor);
    return W.Tick(1)&&(!W.Campaign()->AnchorTakesInteract()||W.Press(EKeys::E));
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraDialogueGiftHoldTest,"SoraArena.Campaign.Dialogue.GiftInputHold",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraDialogueGiftHoldTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    FBeatWorld W(*this,TEXT("DialogueGiftHold"),0,11);
    if(!W.Start()||!W.Tick(60,.5f)) return false;
    TestTrue(TEXT("Waiting never completes the gift before Interact"),W.Campaign()->ActiveBeat()==11&&
        !W.Campaign()->LinesStarted()&&W.Mode()->IsPlaying());
    FVector Anchor;
    if(!TestTrue(TEXT("Gift has its stand"),W.Campaign()->ObjectiveAnchor(Anchor))) return false;
    W.Stand(Anchor);
    W.Hero()->GetCharacterMovement()->Velocity=FVector(200,0,0);
    if(!W.World->InjectKey(EKeys::LeftControl,IE_Pressed)||!W.World->InjectKey(EKeys::LeftShift,IE_Pressed)||
        !W.Press(EKeys::E)||!W.Tick(1)) return false;
    TestEqual(TEXT("The gift's actual scene holds control"),W.Mode()->InputState(),SoraInput::Dialogue);
    TestEqual(TEXT("Only the triggered segment is queued"),W.Campaign()->LinesQueued(),4);
    TestEqual(TEXT("The first gift line remains visible"),LineId(W),FString(TEXT("ch01.b12.sekireisai.003")));
    TestFalse(TEXT("Guard is released"),W.Hero()->IsGuarding());
    TestFalse(TEXT("Sprint is released"),W.Hero()->IsSprinting());
    const FVector At=W.Hero()->GetActorLocation();
    if(!W.World->InjectKey(EKeys::W,IE_Pressed)||!W.World->InjectKey(EKeys::LeftMouseButton,IE_Pressed)||
        !W.World->InjectKey(EKeys::SpaceBar,IE_Pressed)||!W.Tick(6,.1f)) return false;
    TestTrue(TEXT("Held movement and jump cannot drift the hero"),W.Hero()->GetActorLocation().Equals(At,.1f));
    TestFalse(TEXT("Fire cannot remain held"),W.Hero()->GetEquipment()->IsTriggerHeld());
    TestFalse(TEXT("Dialogue is not a global pause"),W.World->GetTestWorld()->IsPaused());
    const bool bEnglish=W.Mode()->bEnglishSubtitles;
    if(!W.Press(EKeys::F10)) return false;
    TestTrue(TEXT("Subtitles can change during the hold"),W.Mode()->bEnglishSubtitles!=bEnglish);
    const FString BeforePause=LineId(W);
    if(!W.Press(EKeys::Escape)||!W.Tick(30,.1f)) return false;
    TestTrue(TEXT("The ordinary pause menu remains available"),W.Mode()->bMenu);
    W.Mode()->ResumePlay();
    TestEqual(TEXT("Pause consumes none of the queued line"),LineId(W),BeforePause);
    if(!Until(W,[&] { return !W.Campaign()->IsDialogueBlocking(); },200)) return false;
    TestTrue(TEXT("blocking_end releases control and its prompt"),W.Mode()->IsPlaying()&&W.PromptOn(TEXT("blocking_end")));
    TestEqual(TEXT("The closing line inherits its ambient event"),LineId(W),FString(TEXT("ch01.b12.sekireisai.007")));
    const FVector Released=W.Hero()->GetActorLocation();
    if(!W.Tick(3,.1f)) return false;
    TestTrue(TEXT("Old held movement does not leak out of the scene"),FVector::Dist2D(Released,W.Hero()->GetActorLocation())<.1f);
    TestFalse(TEXT("Old fire does not restart"),W.Hero()->GetEquipment()->IsTriggerHeld());
    W.Mode()->ResetRound();
    TestFalse(TEXT("Reloading the checkpoint clears the hold"),W.Campaign()->IsDialogueBlocking());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraDialogueModesTest,"SoraArena.Campaign.Dialogue.AuthoredModes",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraDialogueModesTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    for(const int32 Beat:{3,11})
    {
        FBeatWorld W(*this,TEXT("DialogueVolume"),1,Beat);
        if(!W.Start()||!W.Tick(100,.1f)) return false;
        TestTrue(TEXT("Volume dialogue keeps control until its trigger"),W.Mode()->IsPlaying()&&!W.Campaign()->LinesStarted());
        if(!StartAtAnchor(W)||!Until(W,[&] { return W.Campaign()->IsDialogueBlocking(); },150)) return false;
        TestNotNull(TEXT("The blocking line still supplies its cue"),W.Campaign()->CurrentDialogueCue());
        int32 HeldFrames=0;
        while(W.Campaign()->IsDialogueBlocking()&&HeldFrames<202)
        { if(!W.Tick(1,.1f)) return false; ++HeldFrames; }
        TestTrue(TEXT("The authored scene releases within twenty seconds"),HeldFrames<=201&&!W.Campaign()->IsDialogueBlocking());
    }
    FBeatWorld W(*this,TEXT("DialogueLineOverrides"),3,12);
    if(!W.Start()) return false;
    TestTrue(TEXT("The blockade appeal starts with a blocking line"),W.Campaign()->IsDialogueBlocking());
    if(!Until(W,[&] { return LineId(W)==TEXT("ch04.b13.taemon.004"); })) return false;
    TestTrue(TEXT("Explicit ambient line overrides the event's blocking mode"),W.Mode()->IsPlaying());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraDialogueReentrantTest,"SoraArena.Campaign.Dialogue.ReentrantSegments",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraDialogueReentrantTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    {
        FBeatWorld W(*this,TEXT("DialogueCrate"),5,4);
        if(!W.Start()||!StartAtAnchor(W)) return false;
        TestTrue(TEXT("Opening Iota's crate starts its blocking segment"),W.Campaign()->IsDialogueBlocking());
        TestEqual(TEXT("The later conversation is not prequeued"),W.Campaign()->LinesQueued(),4);
        if(!Until(W,[&] { return LineId(W)==TEXT("ch06.b05.nyaakoto.003"); })) return false;
        TestTrue(TEXT("lines_done queues the next segment with control restored"),W.Mode()->IsPlaying());
        TestEqual(TEXT("All eight later lines were enqueued once"),W.Campaign()->LinesQueued(),8);
        if(!W.Tick(10,.1f)) return false;
        TestEqual(TEXT("A reentrant head receives its full authored duration"),LineId(W),FString(TEXT("ch06.b05.nyaakoto.003")));
    }
    FBeatWorld W(*this,TEXT("DialogueToranosuke"),5,9);
    if(!W.Start()) return false;
    TestTrue(TEXT("The reconciliation begins ambient"),W.Mode()->IsPlaying());
    if(!Until(W,[&] { return LineId(W)==TEXT("ch06.b10.toranosuke.004"); })) return false;
    TestTrue(TEXT("Its middle lines_done segment holds control"),W.Campaign()->IsDialogueBlocking());
    if(!Until(W,[&] { return LineId(W)==TEXT("ch06.b10.toranosuke.005"); })) return false;
    TestTrue(TEXT("Its final lines_done segment restores control"),W.Mode()->IsPlaying());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraDialogueCombatAndPlaqueTest,"SoraArena.Campaign.Dialogue.CombatAndPlaque",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraDialogueCombatAndPlaqueTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    {
        FBeatWorld W(*this,TEXT("DialogueDuel"),5,8);
        if(!W.Start()) return false;
        W.Harden();
        if(!Until(W,[&] { return W.Campaign()->LinesQueued()==0; })) return false;
        W.Campaign()->RaiseBeatEvent(TEXT("duel_event:family_page"));
        if(!W.Tick(1)) return false;
        TestTrue(TEXT("A duel's authored family-page event holds combat"),W.Campaign()->IsDialogueBlocking()&&!W.Hero()->CanPlay());
        ASoraProjectile* Arrow=W.World->GetTestWorld()->SpawnActor<ASoraProjectile>(W.Hero()->GetActorLocation()+FVector(0,0,300),FRotator::ZeroRotator);
        if(!TestNotNull(TEXT("An in-flight projectile exists"),Arrow)) return false;
        Arrow->Velocity=FVector(100,0,0);
        const FVector At=Arrow->GetActorLocation();
        if(!W.Tick(10,.1f)) return false;
        TestTrue(TEXT("The in-flight projectile stays held with combat"),Arrow->GetActorLocation().Equals(At,.1f));
        W.Campaign()->PlayerKilled();
        TestFalse(TEXT("Defeat clears the dialogue hold"),W.Campaign()->IsDialogueBlocking());
        TestEqual(TEXT("Defeat has the recorded Result state"),W.Mode()->InputState(),SoraInput::Result);
    }
    FBeatWorld W(*this,TEXT("DialoguePlaque"),7,16);
    if(!W.Start()||!W.Tick(80,.1f)) return false;
    TestTrue(TEXT("The final scene waits for its later authored events"),W.Campaign()->ActiveBeat()==16&&!W.Campaign()->TaskProgress().LinesDone);
    // This is a directed event test. Normal world interactions that produce
    // these events are qualified separately by the complete campaign route.
    W.Campaign()->RaiseBeatEvent(TEXT("event:plaque_rehang"));
    if(!W.Tick(1)) return false;
    TestTrue(TEXT("Rehanging the plaque starts its authored hold"),W.Campaign()->IsDialogueBlocking());
    TestEqual(TEXT("The plaque's four lines are queued"),W.Campaign()->LinesQueued(),4);
    if(!Until(W,[&] { return !W.Campaign()->IsDialogueBlocking(); },201)) return false;
    TestFalse(TEXT("Missing sword-return lines cannot be silently completed"),W.Campaign()->TaskProgress().LinesDone);
    return true;
}
#endif
