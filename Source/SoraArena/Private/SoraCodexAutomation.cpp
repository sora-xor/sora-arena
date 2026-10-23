#include "SoraFrontEnd.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "UI/SoraFrontEndTesting.h"
#include "UI/SSoraFrontEnd.h"
#include "UI/SoraUIFont.h"
#include "SoraFieldcraftTestWorld.h"
#include "SoraWoodAutomation.h"
#include "SoraSettings.h"
#include "SoraCatalogCollectibles.h"
#include "Engine/Font.h"
#include "Framework/Application/SlateApplication.h"
#include "Input/Events.h"
#include "UObject/StrongObjectPtr.h"

namespace SoraCodexAutomation
{
using SoraUI::EAction;
using SoraUI::EScreen;
bool Choose(FSoraAutomationWorld& W, EAction Action, int32 Param = INDEX_NONE)
{
    auto* Menu = W.Mode()->FrontEnd();
    for (int32 Step = 0; Step <= Menu->Rows().Num(); ++Step)
    {
        const int32 At = Menu->Focus();
        if (Menu->Rows().IsValidIndex(At) && Menu->Rows()[At].Action == Action &&
            (Param == INDEX_NONE || Menu->Rows()[At].Param == Param)) return W.PressKey(EKeys::Enter);
        if (!W.PressKey(EKeys::Down)) return false;
    }
    return false;
}
bool Read(FAutomationTestBase& Test, USoraFrontEnd& Menu, int32 Key)
{
    const auto* Entry = Menu.SelectedCodexEntry();
    if (!Test.TestTrue(TEXT("The selected saved entry is the actual reader"), Menu.Screen() == EScreen::CodexEntry && Entry && Entry->Key == Key)) return false;
    TStrongObjectPtr<UFont> Font(SoraUI::CreateUIFont(GetTransientPackage()));
    TSharedRef<SSoraFrontEnd> Widget = SNew(SSoraFrontEnd).FrontEnd(&Menu).Font(Font.Get());
    Test.TestTrue(TEXT("The widget draws the complete authored Japanese body"), Widget->LinesDrawn().Contains(Entry->Body.Japanese));
    Test.TestTrue(TEXT("The widget draws the complete authored English body"), Widget->LinesDrawn().Contains(Entry->Body.English));
    return true;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCodexEarnedTest,"SoraArena.UI.CodexEarned",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCodexEarnedTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCodexAutomation;
    if (!TestTrue(TEXT("Catalog loads"), FSoraCatalog::Get().Load())) return false;
    SoraFieldcraftAutomation::FBeatWorld W(*this,TEXT("CodexEarned"),0,7);
    if (!W.Start() || !W.Tick(30) || !W.Press(EKeys::E)) return false;
    if (!TestTrue(TEXT("Mapped Interact earns the actual stone collectible"), SoraWoodAutomation::Poi(*W.World,SoraWoodRules::Stone)) ||
        !TestTrue(TEXT("Mapped yumi draw/release earns the actual clapper challenge"), SoraWoodAutomation::Arrow(*this,*W.World,true)) || !W.Tick(480)) return false;
    auto* C = W.Campaign();
    TestEqual(TEXT("The notice has expired before the persistent reader opens"), C->StoryNotices().Num(), 0);
    if (!W.Press(EKeys::Escape) || !Choose(*W.World,EAction::Codex)) return false;
    auto* Menu = W.Mode()->FrontEnd();
    TestEqual(TEXT("Only the earned collectible and independent challenge are listed"), Menu->CodexEntries().Num(),2);
    TestEqual(TEXT("The challenge never increments the collectible count"), Menu->CodexSummary().English,
        FString(TEXT("Collectibles 1 / 48\nSelect a discovered record to read.")));
    TArray<uint8> Before, After;
    if (!TestTrue(TEXT("Read-only comparison loads saved bytes"), UGameplayStatics::LoadDataFromSlot(Before,W.Slot,0))) return false;
    const int64 Found = C->CollectedMask();
    TArray<bool> Weapons;
    for (int32 Id=0;Id<FSoraCatalog::Get().Weapons.Num();++Id) Weapons.Add(C->IsWeaponUnlocked(Id));
    if (!Choose(*W.World,EAction::CodexEntry,0) || !Read(*this,*Menu,0)) return false;
    TestEqual(TEXT("The authored collectible title survives catalog loading"),Menu->SelectedCodexEntry()->Title.Japanese,C->ActiveChapter()->Collectibles[0].Title);
    if (!W.Press(EKeys::Escape)) return false;
    TestEqual(TEXT("Back restores the index's selected record"),Menu->Rows()[Menu->Focus()].Param,0);
    if (!Choose(*W.World,EAction::CodexEntry,48) || !Read(*this,*Menu,48)) return false;
    TestEqual(TEXT("Toshiya reader shows the complete sourced history"),Menu->SelectedCodexEntry()->Body.English,C->ToshiyaCodex(true));
    for (int32 I=0; I<3; ++I)
        if (!W.Press(EKeys::Escape) || !W.Press(EKeys::Enter)) return false;
    TestEqual(TEXT("Repeated reading never changes collectibles"),static_cast<int64>(C->CollectedMask()),Found);
    for (int32 Id=0;Id<Weapons.Num();++Id) TestEqual(TEXT("Reading grants no weapon"),C->IsWeaponUnlocked(Id),Weapons[Id]);
    if (!TestTrue(TEXT("Reading leaves exact campaign bytes unchanged"),UGameplayStatics::LoadDataFromSlot(After,W.Slot,0)&&Before==After)) return false;
    if (!W.Press(EKeys::Escape)||!W.Press(EKeys::Escape)) return false;
    TestTrue(TEXT("Back returns to the paused game context"),Menu->Screen()==EScreen::Pause&&W.World->GetTestWorld()->IsPaused());
    // A real new world reads the same disk slot; no reward is re-seeded.
    W.Fieldcraft()->OnEvent.Remove(W.EventsHandle);
    if (!W.World->DestroyTestWorld(true)) return false;
    W.World->ForwardErrorMessages(this); W.World.Reset();
    W.World=MakeUnique<FSoraAutomationWorld>();
    if (!W.World->Start(W.Slot)||!W.Tick(1)||!W.World->EnableKeyInput()||!W.Press(EKeys::Enter)||!Choose(*W.World,EAction::Codex)) return false;
    Menu=W.Mode()->FrontEnd();
    TestEqual(TEXT("Fresh main-menu load retains both earned records"),Menu->CodexEntries().Num(),2);
    if (!Choose(*W.World,EAction::CodexEntry,48)||!Read(*this,*Menu,48)) return false;
    TestTrue(TEXT("Fresh read remains a title-menu context"),!Menu->IsPauseContext());
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCodexLibraryTest,"SoraArena.UI.CodexLibrary",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCodexLibraryTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraFrontEndTests;
    if (!TestTrue(TEXT("Catalog loads"),FSoraCatalog::Get().Load())) return false;
    FScope Scope(*this,TEXT("CodexLibrary"));
    if (!Scope.Seed(7,7)) return false;
    auto* Save=Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(Scope.Slot,0));
    if (!TestNotNull(TEXT("Prepared UI fixture has a real save"),Save)) return false;
    Save->Collectibles=(int64(1)<<48)-1;
    Save->WoodPoiMask=SoraWoodRules::All;
    if (!UGameplayStatics::SaveGameToSlot(Save,Scope.Slot,0)||!Scope.Start()) return false;
    TArray<uint8> Before,After;
    if (!UGameplayStatics::LoadDataFromSlot(Before,Scope.Slot,0)) return false;
    Scope.Key(Pad.Accept);
    if (!Scope.Choose(Pad,EAction::Codex)) return false;
    auto* Menu=Scope.FrontEnd();
    TestEqual(TEXT("Prepared all-found library has 48 collectibles plus one challenge"),Menu->CodexEntries().Num(),49);
    TestEqual(TEXT("The separate challenge does not produce 49 / 48"),Menu->CodexSummary().English,
        FString(TEXT("Collectibles 48 / 48\nSelect a discovered record to read.")));
    const auto Entries=Menu->CodexEntries();
    for (const auto& Entry:Entries)
    {
        if (!Scope.Choose(Pad,EAction::CodexEntry,Entry.Key)) return false;
        const auto* Selected=Menu->SelectedCodexEntry();
        if (!TestNotNull(TEXT("Pad opens each saved entry"),Selected)) return false;
        TestEqual(TEXT("Reader preserves the complete saved entry"),Selected->Body.English,Entry.Body.English);
        if (Entry.Key<48)
        {
            const auto& Chapter=FSoraCatalog::Get().Chapter(Entry.Key/6);
            const auto* Item=Chapter.Collectibles.FindByPredicate([&](const FSoraCollectible& I){return I.MaskBit==Entry.Key%6;});
            if (!TestNotNull(TEXT("Every entry maps to a real catalog item"),Item)) return false;
            TestEqual(TEXT("Japanese lore is never replaced with a summary"),Selected->Body.Japanese,Item->Codex);
            TestEqual(TEXT("English lore is never replaced with a summary"),Selected->Body.English,Item->CodexEnglish);
            if (!Item->Title.IsEmpty()) TestEqual(TEXT("Authored title is retained verbatim"),Selected->Title.Japanese,Item->Title);
            else TestFalse(TEXT("Untitled entries have a localized neutral label"),Selected->Title.English.IsEmpty());
        }
        Scope.Key(Pad.Back);
        TestTrue(TEXT("Pad Back retains the selected row"),Scope.On(EScreen::Codex)&&Scope.Focused()->Param==Entry.Key);
    }
    if (!Scope.Choose(Keyboard,EAction::CodexEntry,48)) return false;
    TStrongObjectPtr<UFont> Font(SoraUI::CreateUIFont(GetTransientPackage()));
    TSharedRef<SSoraFrontEnd> Widget=SNew(SSoraFrontEnd).FrontEnd(Menu).Font(Font.Get());
    for (int32 Size=0;Size<3;++Size)
        for (bool English:{false,true})
        {
            Scope.Mode()->Settings()->SetSubtitleSize(static_cast<SoraAccessibility::ESubtitleSize>(Size));
            Scope.Mode()->Settings()->SetEnglishSubtitles(English);
            Widget->Refresh();
            const auto* Entry=Menu->SelectedCodexEntry();
            TestTrue(TEXT("Japanese body remains visible at every size"),Widget->LinesDrawn().Contains(Entry->Body.Japanese));
            TestEqual(TEXT("English body follows the subtitle switch"),Widget->LinesDrawn().Contains(Entry->Body.English),English);
            const float Scale=SoraAccessibility::SubtitleScale(static_cast<SoraAccessibility::ESubtitleSize>(Size));
            TestTrue(TEXT("Body uses the selected accessibility text scale"),Widget->FontSizesUsed().Contains(28.f*Scale));
        }
    for (int32 I=0;I<10;++I) Widget->OnKeyDown(FGeometry(),FKeyEvent(EKeys::Gamepad_DPad_Down,FModifierKeysState(),0,false,0,0));
    TestEqual(TEXT("Pad scrolling clamps at the end"),Menu->CodexScrollFraction(),1.f);
    for (int32 I=0;I<10;++I) Widget->OnKeyDown(FGeometry(),FKeyEvent(EKeys::Up,FModifierKeysState(),0,false,0,0));
    TestEqual(TEXT("Keyboard scrolling returns to the start"),Menu->CodexScrollFraction(),0.f);
    TestTrue(TEXT("Reading the full library leaves campaign bytes unchanged"),UGameplayStatics::LoadDataFromSlot(After,Scope.Slot,0)&&Before==After);
    Scope.Key(Keyboard.Back);Scope.Key(Keyboard.Back);
    if (!Scope.Choose(Keyboard,EAction::ChapterSelect)||!Scope.Choose(Keyboard,EAction::Chapter,0)||
        !Scope.Choose(Keyboard,EAction::ConfirmYes)) return false;
    Scope.Mode()->OpenPauseMenu();
    if (!Scope.Choose(Keyboard,EAction::Codex)) return false;
    TestEqual(TEXT("Chapter replay retains all saved lore"),Menu->CodexEntries().Num(),49);
    Scope.Key(Keyboard.Back);
    if (!Scope.Choose(Keyboard,EAction::ReturnToTitle)||!Scope.Choose(Keyboard,EAction::ConfirmYes)) return false;
    if (!TestTrue(TEXT("Returning from replay opens Main without another title key"),Scope.On(EScreen::Main))) return false;
    if (!Scope.Choose(Keyboard,EAction::NewCampaign)||!Scope.Choose(Keyboard,EAction::ConfirmYes)) return false;
    Scope.Mode()->OpenPauseMenu();
    if (!Scope.Choose(Keyboard,EAction::Codex)) return false;
    TestEqual(TEXT("Starting over clears discoveries using existing save semantics"),Menu->CodexEntries().Num(),0);
    TestTrue(TEXT("Empty library focuses Back, never a locked body"),Scope.Focused()&&Scope.Focused()->Action==EAction::Back);
    return !HasAnyErrors();
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCodexTitleDataTest,"SoraArena.UI.CodexTitleData",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCodexTitleDataTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    FJsonObject Row; FSoraCollectible Item;
    TestFalse(TEXT("Missing title fields are rejected"),SoraCatalogCollectibles::ReadTitles(Row,Item));
    Row.SetField(TEXT("title_ja"),MakeShared<FJsonValueNull>());
    Row.SetField(TEXT("title_en"),MakeShared<FJsonValueNull>());
    TestTrue(TEXT("Explicit null pairs retain no invented title"),SoraCatalogCollectibles::ReadTitles(Row,Item)&&Item.Title.IsEmpty()&&Item.TitleEnglish.IsEmpty());
    Row.SetStringField(TEXT("title_ja"),TEXT("authored native title"));
    TestFalse(TEXT("A half-authored title is rejected"),SoraCatalogCollectibles::ReadTitles(Row,Item));
    Row.SetStringField(TEXT("title_en"),TEXT("authored subtitle"));
    TestTrue(TEXT("Both nonempty strings are retained"),SoraCatalogCollectibles::ReadTitles(Row,Item)&&Item.Title==TEXT("authored native title")&&Item.TitleEnglish==TEXT("authored subtitle"));
    Row.SetStringField(TEXT("title_en"),TEXT(""));
    TestFalse(TEXT("An empty subtitle is not an absent title"),SoraCatalogCollectibles::ReadTitles(Row,Item));
    Row.SetStringField(TEXT("title_en"),TEXT("authored subtitle"));
    for (const auto& Bad:TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueBoolean>(true),MakeShared<FJsonValueNumber>(42),
        MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{}),MakeShared<FJsonValueObject>(MakeShared<FJsonObject>())})
    {
        Row.SetField(TEXT("title_ja"),Bad);
        TestFalse(TEXT("Non-string native title is never coerced"),SoraCatalogCollectibles::ReadTitles(Row,Item));
        Row.SetStringField(TEXT("title_ja"),TEXT("authored native title"));
        Row.SetField(TEXT("title_en"),Bad);
        TestFalse(TEXT("Non-string subtitle is never coerced"),SoraCatalogCollectibles::ReadTitles(Row,Item));
        Row.SetStringField(TEXT("title_en"),TEXT("authored subtitle"));
    }
    return !HasAnyErrors();
}
#endif
