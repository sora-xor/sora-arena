#if WITH_DEV_AUTOMATION_TESTS
#include "SoraDialogueTestWorld.h"
#include "SoraCampaignRules.h"
#include "SoraWorldBuilder.h"

using namespace SoraFieldcraftAutomation;
namespace
{
bool WaitForLines(FBeatWorld& W,int32 Frames=600)
{
    for(int32 Frame=0;W.Campaign()->LinesQueued()>0&&Frame<Frames;++Frame)
        if(!W.Tick(1,.1f)) return false;
    return W.Test.TestEqual(TEXT("The authored dialogue finishes without skipping"),W.Campaign()->LinesQueued(),0);
}
int64 SwordMask()
{
    const FSoraChapter& Chapter=FSoraCatalog::Get().Chapters[7];
    for(const FSoraCollectible& Item:Chapter.Collectibles)
        if(Item.Id==TEXT("ch08.c03")) return static_cast<int64>(SoraCampaignRules::CollectibleBit(7,Item.MaskBit));
    return 0;
}
bool PlayEpilogue(FAutomationTestBase& Test,bool bSword)
{
    FBeatWorld W(Test,bSword?TEXT("EpilogueWithSword"):TEXT("EpilogueWithoutSword"),7,16);
    const int64 Found=bSword?SwordMask():0;
    if(!SoraDialogueAutomation::StartAuthored(W,Found)||!WaitForLines(W)) return false;
    ASoraWorldBuilder* Builder=W.Mode()->Arena();
    if(!Test.TestNotNull(TEXT("The epilogue world is staged"),Builder)) return false;
    const unsigned Weapons=W.Campaign()->Progress().WeaponsMask;
    Test.TestEqual(TEXT("The found heirloom matches the saved collectible"),W.Campaign()->HasWashioSword(),bSword);
    // Waiting and interacting from the start never manufacture world events.
    if(!W.Press(EKeys::E)||!W.Tick(80,.1f)) return false;
    Test.TestTrue(TEXT("The final conversation still waits for the walk"),W.Campaign()->ActiveBeat()==16&&
        !W.Campaign()->HasReturnedWashioSword()&&!W.Campaign()->HasRehungPlaques());
    Test.TestEqual(TEXT("The board starts before the promotion"),Builder->RehungPlaques(),0);
    FVector Anchor;
    if(!Test.TestTrue(TEXT("The first objective is the torii arrival"),W.Campaign()->ObjectiveAnchor(Anchor)&&!W.Campaign()->AnchorTakesInteract())) return false;
    W.Stand(Anchor);
    if(!W.Tick(1)||!WaitForLines(W)) return false;
    if(bSword)
    {
        // Trying the name board first cannot bypass the found heirloom.
        W.Stand(ASoraWorldBuilder::Floor(W.BeatData().Space.Closing));
        if(!W.Press(EKeys::E)) return false;
        Test.TestFalse(TEXT("The plaque scene cannot start at the wrong stage"),W.Campaign()->IsDialogueBlocking());
        if(!Test.TestTrue(TEXT("The sword has a normal Interact objective"),W.Campaign()->ObjectiveAnchor(Anchor)&&W.Campaign()->AnchorTakesInteract())) return false;
        W.Stand(Anchor);
        if(!W.Press(EKeys::E)) return false;
        Test.TestTrue(TEXT("Returning the sword keeps movement available"),W.Campaign()->HasReturnedWashioSword()&&W.Mode()->IsPlaying());
        Test.TestTrue(TEXT("The heirloom is now displayed on Toranosuke"),Builder->WashioSwordReturned());
        const auto Lines=W.Campaign()->QueuedSubtitles();
        Test.TestEqual(TEXT("Exactly three optional return lines"),Lines.Num(),3);
        if(!Lines.IsEmpty()) Test.TestEqual(TEXT("The return begins with the found sword"),Lines[0].LineId,FString(TEXT("ch08.b17.nyaakoto.003")));
        if(!W.Press(EKeys::E)) return false;
        Test.TestEqual(TEXT("Repeated interaction cannot duplicate the return"),W.Campaign()->LinesQueued(),3);
        if(!WaitForLines(W)) return false;
    }
    else
    {
        Test.TestFalse(TEXT("A sword that was not found is not returned"),W.Campaign()->HasReturnedWashioSword());
        Test.TestFalse(TEXT("No heirloom is fabricated on Toranosuke"),Builder->WashioSwordReturned());
    }
    if(!Test.TestTrue(TEXT("The plaque stand is an ordinary Interact objective"),W.Campaign()->ObjectiveAnchor(Anchor)&&W.Campaign()->AnchorTakesInteract())) return false;
    W.Stand(Anchor);
    if(!W.Press(EKeys::E)) return false;
    Test.TestTrue(TEXT("The plaque scene holds gameplay"),W.Campaign()->IsDialogueBlocking());
    Test.TestEqual(TEXT("Exactly four plaque lines start"),W.Campaign()->LinesQueued(),4);
    int32 HeldFrames=0;
    while(W.Campaign()->IsDialogueBlocking()&&HeldFrames<202)
    { if(!W.Tick(1,.1f)) return false; ++HeldFrames; }
    Test.TestTrue(TEXT("The plaque exchange releases inside twenty seconds"),HeldFrames<=201&&!W.Campaign()->IsDialogueBlocking());
    Test.TestTrue(TEXT("The final spoken line raises the completion event"),W.Campaign()->HasRehungPlaques());
    Test.TestEqual(TEXT("Both plaques were rehung on their spoken cues"),Builder->RehungPlaques(),2);
    Test.TestEqual(TEXT("Returning an heirloom never changes weapon entitlement"),W.Campaign()->Progress().WeaponsMask,Weapons);
    if(!W.Tick(1)) return false;
    Test.TestEqual(TEXT("Both collectible routes reach One sheaf"),W.Campaign()->ActiveBeat(),17);
    Test.TestEqual(TEXT("The final cinematic preserves the rehung board"),Builder->RehungPlaques(),2);
    if(!W.Press(EKeys::Enter)||!W.Tick(1)) return false;
    Test.TestTrue(TEXT("The authored ending completes the campaign"),W.Mode()->bChapterComplete);
    const USoraSaveGame* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    if(!Test.TestNotNull(TEXT("Completion is saved"),Saved)) return false;
    Test.TestTrue(TEXT("The completed checkpoint contains the epilogue beat"),Saved->CampaignComplete&&Saved->CheckpointComplete&&
        (static_cast<unsigned>(Saved->CheckpointBeatsMask)&SoraBeatRules::BeatBit(16))!=0);
    Test.TestEqual(TEXT("The codex collectible is retained after the return"),Saved->Collectibles,Found);
    W.Mode()->ResetRound();
    Test.TestTrue(TEXT("Reloading completion returns to the result"),W.Mode()->bChapterComplete&&!W.Campaign()->IsDialogueBlocking());
    return true;
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraEpilogueWithSwordTest,"SoraArena.Campaign.Epilogue.WithSword",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraEpilogueWithSwordTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    return TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())&&TestTrue(TEXT("The sword has a collectible bit"),SwordMask()!=0)&&PlayEpilogue(*this,true);
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraEpilogueWithoutSwordTest,"SoraArena.Campaign.Epilogue.WithoutSword",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraEpilogueWithoutSwordTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    return TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())&&PlayEpilogue(*this,false);
}
#endif
