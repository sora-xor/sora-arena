#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFieldcraftTestWorld.h"
#include "HUD/SoraHUDPanels.h"

using namespace SoraFieldcraftAutomation;
namespace
{
bool OpenSavedWorld(FBeatWorld& W)
{
    if(W.World)
    {
        W.World->DestroyTestWorld(true);
        W.World->ForwardErrorMessages(&W.Test);
    }
    W.World=MakeUnique<FSoraAutomationWorld>();
    // Two menu presses resume; a third would skip the cinematic or advance
    // the completed result which this fixture deliberately needs to inspect.
    return W.World->Start(W.Slot)&&W.Tick(1)&&W.World->EnableKeyInput()&&
        W.Press(EKeys::Enter)&&W.Press(EKeys::Enter);
}
int32 RegistryNotices(const FBeatWorld& W)
{
    return W.Campaign()->StoryNotices().FilterByPredicate([](const FSoraStoryNotice& N)
        { return N.Kind==FSoraStoryNotice::EKind::Registry; }).Num();
}
bool FinishFoodDelivery(FBeatWorld& W)
{
    for(int32 Action=0;W.Campaign()->ActiveBeat()==10&&Action<8;++Action)
    {
        FVector Anchor;
        if(!W.Test.TestTrue(TEXT("Food has its next pickup or delivery"),W.Campaign()->ObjectiveAnchor(Anchor)&&
            W.Campaign()->AnchorTakesInteract())) return false;
        W.Stand(Anchor);
        if(!W.Press(EKeys::E)) return false;
    }
    return W.Test.TestEqual(TEXT("Three real deliveries finish the food task"),W.Campaign()->ActiveBeat(),11);
}
// A disk fixture for a completed chapter, built through the same pure rules
// that validate saved progress. This tests result recovery, not full playthrough.
bool SaveFinishedChapter(FBeatWorld& W)
{
    auto* Save=NewObject<USoraSaveGame>();
    if(!USoraCampaignDirector::SeedCheckpoint(*Save,W.Chapter,0)) return false;
    const FSoraChapter& Chapter=FSoraCatalog::Get().Chapter(W.Chapter);
    SoraBeatRules::FProgress State{0u,0u,static_cast<unsigned>(Save->ChapterEntryWeapons),
        static_cast<unsigned>(Save->ChapterEntryMechanics),static_cast<unsigned>(Save->ChapterEntryFlags),false};
    for(int32 Index=0;Index<Chapter.Rules.Num();++Index)
        if(!Chapter.Rules[Index].Optional&&!SoraBeatRules::CompleteBeat(State,Chapter.Rules.GetData(),Chapter.Rules.Num(),Index)) return false;
    if(!SoraBeatRules::FinishChapter(State,Chapter.Rules.GetData(),Chapter.Rules.Num())||
        !SoraBeatRules::ProgressValid(State,Chapter.Rules.GetData(),Chapter.Rules.Num(),Save->ChapterEntryWeapons,
            Save->ChapterEntryMechanics,Save->ChapterEntryFlags)) return false;
    Save->HighestChapter=W.Chapter+1;
    Save->CheckpointBeat=INDEX_NONE; Save->CheckpointPhase=0; Save->CheckpointComplete=true;
    Save->CheckpointBeatsMask=static_cast<int32>(State.CompletedMask); Save->CheckpointSitesMask=static_cast<int32>(State.SitesMask);
    Save->CheckpointWeapons=static_cast<int32>(State.WeaponsMask); Save->CheckpointMechanics=static_cast<int32>(State.MechanicsMask);
    Save->CheckpointFlags=static_cast<int32>(State.FlagsMask);
    return UGameplayStatics::SaveGameToSlot(Save,W.Slot,0);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRegistryProductionTest,"SoraArena.Campaign.Registry.ProductionAndRetry",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRegistryProductionTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    FBeatWorld W(*this,TEXT("RegistryProduction"),1,10);
    if(!W.Start()) return false;
    W.Harden();
    TestEqual(TEXT("Seed rice is already complete, food is not"),W.Campaign()->RegistryRows().Num(),1);
    TestEqual(TEXT("Loading progress does not replay toasts"),RegistryNotices(W),0);
    if(!FinishFoodDelivery(W)) return false;
    TestEqual(TEXT("Food is entered once on completion"),W.Campaign()->RegistryRows().Num(),2);
    TestEqual(TEXT("Completion shows one goods toast"),RegistryNotices(W),1);
    const auto Rows=W.Campaign()->RegistryRows();
    TestEqual(TEXT("Exact food goods and quantity"),Rows.Last().Entry.Japanese(),FString(TEXT("食糧 36食")));
    if(!W.Press(EKeys::E)) return false;
    TestEqual(TEXT("Another interaction never duplicates the goods"),W.Campaign()->RegistryRows().Num(),2);
    W.Campaign()->PlayerKilled();
    TestFalse(TEXT("Defeat does not show the successful registry page"),SoraHUDPanels::ShowsRegistry(*W.Mode()));
    if(!W.Press(EKeys::Enter)) return false;
    TestEqual(TEXT("Death before the next checkpoint restores the food task"),W.Campaign()->ActiveBeat(),10);
    TestEqual(TEXT("Uncheckpointed work rolls back instead of accumulating"),W.Campaign()->RegistryRows().Num(),1);
    TestEqual(TEXT("Retry clears stale notices"),RegistryNotices(W),0);
    if(!FinishFoodDelivery(W)) return false;
    FVector Anchor;
    if(!TestTrue(TEXT("Kohagi's following conversation has its volume"),W.Campaign()->ObjectiveAnchor(Anchor))) return false;
    W.Stand(Anchor);
    for(int32 Frame=0;W.Campaign()->ActiveBeat()==11&&Frame<400;++Frame)
        if(!W.Tick(1,.1f)) return false;
    if(!TestTrue(TEXT("The actual conversation reaches the next checkpoint"),W.Campaign()->ActiveBeat()>11)) return false;
    const USoraSaveGame* Saved=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(W.Slot,0));
    if(!TestNotNull(TEXT("Progress has a disk checkpoint"),Saved)) return false;
    TestTrue(TEXT("The checkpoint contains the completed food delivery"),
        (static_cast<unsigned>(Saved->CheckpointBeatsMask)&SoraBeatRules::BeatBit(10))!=0u);
    const int32 SavedBeat=Saved->CheckpointBeat;
    if(!OpenSavedWorld(W)) return false;
    TestEqual(TEXT("An incomplete save resumes the same checkpoint"),W.Campaign()->ActiveBeat(),SavedBeat);
    TestEqual(TEXT("Disk reload reconstructs both goods once"),W.Campaign()->RegistryRows().Num(),2);
    TestFalse(TEXT("Incomplete progress has no completion page"),SoraHUDPanels::ShowsRegistry(*W.Mode()));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRegistryInspectionTest,"SoraArena.Campaign.Registry.FirstInspection",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRegistryInspectionTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    for(const bool Skip:{false,true})
    {
        FBeatWorld W(*this,Skip?TEXT("RegistryInspectionSkip"):TEXT("RegistryInspectionPlayed"),4,11);
        auto* Save=NewObject<USoraSaveGame>();
        if(!TestTrue(TEXT("The ceremony's real checkpoint is seeded"),USoraCampaignDirector::SeedCheckpoint(*Save,4,11))||
            !UGameplayStatics::SaveGameToSlot(Save,W.Slot,0)||!OpenSavedWorld(W)) return false;
        if(!TestEqual(TEXT("The inspection cinematic is active"),W.Campaign()->ActiveBeat(),11)) return false;
        TestEqual(TEXT("Three goods precede inspection"),W.Campaign()->RegistryRows().Num(),3);
        for(const FSoraRegistryRow& Row:W.Campaign()->RegistryRows()) TestFalse(TEXT("No tally before the ceremony ends"),Row.HasSplitTally());
        if(Skip) { if(!W.Press(EKeys::Enter)) return false; }
        else for(int32 Frame=0;W.Campaign()->ActiveBeat()==11&&Frame<302;++Frame) if(!W.Tick(1,.5f)) return false;
        if(!TestTrue(TEXT("The ceremony finishes through its authored path"),W.Campaign()->ActiveBeat()>11)) return false;
        const auto Rows=W.Campaign()->RegistryRows();
        TestEqual(TEXT("The ceremony adds no fourth goods entry"),Rows.Num(),3);
        for(const FSoraRegistryRow& Row:Rows) TestTrue(TEXT("All three entries now have inspected split tallies"),Row.HasSplitTally());
        TestEqual(TEXT("The first inspection reports the three changed entries"),RegistryNotices(W),3);
        if(!W.Tick(20,.5f)) return false;
        TestEqual(TEXT("Registry feedback waits through the following cinematic"),RegistryNotices(W),3);
        if(!W.Campaign()->LoadSave()) return false;
        W.Mode()->ResetRound();
        for(const FSoraRegistryRow& Row:W.Campaign()->RegistryRows()) TestTrue(TEXT("Checkpoint reload retains inspection"),Row.HasSplitTally());
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraRegistryResultTest,"SoraArena.Campaign.Registry.ResultRecovery",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraRegistryResultTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if(!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    for(const int32 Chapter:{4,6})
    {
        FBeatWorld W(*this,TEXT("RegistryResultRecovery"),Chapter,0);
        if(!TestTrue(TEXT("A valid completed checkpoint is saved"),SaveFinishedChapter(W))||!OpenSavedWorld(W)) return false;
        TestEqual(TEXT("Continue does not skip the saved chapter's page"),W.Campaign()->ChapterId,Chapter);
        TestTrue(TEXT("A completed chapter shows the production page"),SoraHUDPanels::ShowsRegistry(*W.Mode()));
        const auto Rows=W.Campaign()->RegistryRows();
        TestEqual(TEXT("The result reconstructs the authored entries"),Rows.Num(),Chapter==4?3:1);
        if(Chapter==6&&Rows.Num()==1)
        {
            TestFalse(TEXT("Returned goods have no split-tally icon"),Rows[0].HasSplitTally());
            const auto Note=SoraRegistry::Status(Rows[0].State);
            TestEqual(TEXT("Exact return-only Japanese note"),Note.Japanese,FString(TEXT("返還のみ記帳・札は切らず")));
            TestEqual(TEXT("Exact return-only English note"),Note.English,FString(TEXT("Recorded as returned. No tally cut.")));
        }
        const bool English=W.Mode()->bEnglishSubtitles;
        if(!W.Press(EKeys::F10)) return false;
        TestTrue(TEXT("The result keeps the subtitle toggle"),W.Mode()->bEnglishSubtitles!=English);
        W.Mode()->bDefeated=true;
        TestFalse(TEXT("Defeat keeps its existing result presentation"),SoraHUDPanels::ShowsRegistry(*W.Mode()));
        W.Mode()->bDefeated=false; W.Mode()->bCampaign=false;
        TestFalse(TEXT("Practice never shows a campaign registry"),SoraHUDPanels::ShowsRegistry(*W.Mode()));
        TestEqual(TEXT("Practice exposes no story goods"),W.Campaign()->RegistryRows().Num(),0);
        W.Mode()->bCampaign=true;
        // Restart the world and load the disk again, not only in-memory state.
        if(!OpenSavedWorld(W)) return false;
        TestTrue(TEXT("The page survives another actual disk reload"),SoraHUDPanels::ShowsRegistry(*W.Mode()));
        TestEqual(TEXT("Reload never duplicates rows"),W.Campaign()->RegistryRows().Num(),Rows.Num());
        if(!W.Press(EKeys::Enter)) return false;
        TestEqual(TEXT("Enter on the result still advances"),W.Campaign()->ChapterId,Chapter+1);
        TestFalse(TEXT("Advancing leaves the result"),SoraHUDPanels::ShowsRegistry(*W.Mode()));
        TestEqual(TEXT("The next chapter starts with no completed goods"),W.Campaign()->RegistryRows().Num(),0);
        W.Mode()->SetMenuOpen(true);
        if(!TestTrue(TEXT("The completed chapter can be replayed"),W.Mode()->StartChapter(Chapter))) return false;
        TestEqual(TEXT("Replay starts its current-chapter registry afresh"),W.Campaign()->RegistryRows().Num(),0);
        W.Mode()->SetMenuOpen(true); W.Mode()->StartNewCampaign();
        TestEqual(TEXT("New Campaign starts at the dojo"),W.Campaign()->ChapterId,0);
        TestEqual(TEXT("New Campaign clears current goods"),W.Campaign()->RegistryRows().Num(),0);
        TestEqual(TEXT("New Campaign clears chapter reach"),W.Campaign()->HighestChapter(),0);
    }
    return true;
}
#endif
