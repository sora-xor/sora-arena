#include "SoraFrontEnd.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "ArenaKernelSubsystem.h"
#include "SoraAutomationWorld.h"
#include "UI/SoraFrontEndTesting.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraPracticeDirector.h"
#include "SoraPracticeLobby.h"
#include "SoraInputStates.h"
#include "SoraSaveGame.h"
#include "SoraSettings.h"
#include "UI/SSoraFrontEnd.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/GameViewportClient.h"
#include "Engine/UserInterfaceSettings.h"
#include "Engine/World.h"
#include "Fonts/CompositeFont.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "Framework/Application/SlateApplication.h"
#include "Input/Events.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"
#include "Templates/UniquePtr.h"
#include "Tests/AutomationCommon.h"
#include "UnrealClient.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"

// The Slate front end in standalone game worlds: every screen and dialog
// reached with the pad alone and with the keyboard alone, each line of each
// checked for its Japanese and its English subtitle, chapter select, the
// practice lobby's choice reaching practice, and text that stays readable at 720p. A test world
// has no viewport, so keys reach USoraFrontEnd the way SSoraFrontEnd forwards
// them (FSoraAutomationWorld::InjectKey); the readability test builds the real
// widget for every screen and sends it keys directly. The rendered test at the
// end runs only in a game client with a viewport (see its comment).
namespace SoraFrontEndTests
{
bool HasJapanese(const FString& Text)
{
    for (const TCHAR Char : Text)
        if ((Char >= 0x3000 && Char <= 0x9FFF) || (Char >= 0xFF00 && Char <= 0xFFEF))
            return true;
    return false;
}

// Every line on the open screen has its Japanese and its English subtitle:
// the heading or the dialog's two lines, the banner, and each row's label,
// value, hint and key caps. No English line carries Japanese.
void CheckBilingual(FAutomationTestBase& Test, const USoraFrontEnd& FrontEnd, const FString& Label)
{
    const EScreen Screen = FrontEnd.Screen();
    const FString Where = FString::Printf(TEXT("%s, screen %d"), *Label, static_cast<int32>(Screen));
    const auto Pair = [&](const FString& Japanese, const FString& English, const FString& What, bool bRequired)
    {
        if ((bRequired && Japanese.IsEmpty()) || Japanese.IsEmpty() != English.IsEmpty() || HasJapanese(English))
            Test.AddError(FString::Printf(TEXT("%s: %s is not bilingual (\"%s\" / \"%s\")"), *Where, *What, *Japanese, *English));
    };
    if (Screen == EScreen::Confirm || Screen == EScreen::Capture)
    {
        // A question, then its warning, the reason a key was refused, or the way out.
        Pair(FrontEnd.ConfirmJapanese(), FrontEnd.ConfirmEnglish(), TEXT("the dialog"), true);
        if (!FrontEnd.ConfirmJapanese().Contains(TEXT("\n")) || !FrontEnd.ConfirmEnglish().Contains(TEXT("\n")))
            Test.AddError(FString::Printf(TEXT("%s: the dialog lacks its second line"), *Where));
    }
    else
        Pair(FrontEnd.TitleJapanese(), FrontEnd.TitleEnglish(), TEXT("the heading"), true);
    Pair(FrontEnd.BannerJapanese, FrontEnd.BannerEnglish, TEXT("the banner"), false);
    const TArray<SoraUI::FRow>& Rows = FrontEnd.Rows();
    for (int32 Index = 0; Index < Rows.Num(); ++Index)
    {
        const SoraUI::FRow& Row = Rows[Index];
        const FString What = FString::Printf(TEXT("row %d"), Index);
        Pair(Row.Japanese, Row.English, What, true);
        Pair(Row.ValueJapanese, Row.ValueEnglish, What + TEXT("'s value"), Row.bOption);
        Pair(Row.HintJapanese, Row.HintEnglish, What + TEXT("'s hint"), false);
        if (Row.bBinding && (Row.Keys[0].IsEmpty() || Row.Keys[1].IsEmpty()))
            Test.AddError(FString::Printf(TEXT("%s: %s lacks a key cap"), *Where, *What));
        if (Row.bHeading)
            for (int32 Column = 0; Column < 2; ++Column)
                Pair(Row.Keys[Column], Row.KeysEnglish[Column], What + TEXT("'s column"), false);
    }
}

// Title, main menu, the new-campaign dialog, chapter select and its dialog,
// practice lobby, wallet, credits, the quit dialog, the settings hub, all five
// settings screens, a rebind and the reset dialog, then play, the pause menu,
// its settings, restart dialog and return to the title, with one device's keys
// only. Every dialog is withdrawn, so nothing changes. The world stays paused
// on every screen, and after every key the open screen must be bilingual.
bool Tour(FAutomationTestBase& Test, const FKeys& Keys)
{
    FScope Scope(Test, Keys.Name);
    constexpr int32 Chapter = 2;
    if (!Scope.Seed(Chapter, Chapter) || !Scope.Start())
        return false;
    ASoraGameMode* Mode = Scope.Mode();
    USoraFrontEnd* FrontEnd = Scope.FrontEnd();
    const FString Label = Keys.Name;
    const auto Check = [&](const TCHAR* What, bool bHolds) { return Test.TestTrue(*FString::Printf(TEXT("%s: %s"), *Label, What), bHolds); };
    TSet<EScreen> Visited;
    TSet<FString> Dialogs;
    Scope.AfterKey = [&]()
    {
        if (!FrontEnd->IsOpen())
            return;
        Visited.Add(FrontEnd->Screen());
        if (FrontEnd->Screen() == EScreen::Confirm)
            Dialogs.Add(FrontEnd->ConfirmEnglish());
        CheckBilingual(Test, *FrontEnd, Label);
    };
    Scope.AfterKey();
    Check(TEXT("the title screen opens paused"), Scope.On(EScreen::Title) && Scope.Paused());
    Scope.Key(Keys.Accept);
    if (!Check(TEXT("accept leaves the title for the main menu"), Scope.On(EScreen::Main)))
        return false;
    Check(TEXT("prompts follow the device"), FrontEnd->Device() == Keys.Device &&
        SoraUI::PromptKey(SoraUI::ECommand::Accept, FrontEnd->Device()) == Keys.AcceptLabel);
    TArray<EAction> Main;
    for (const SoraUI::FRow& Row : FrontEnd->Rows())
        Main.Add(Row.Action);
    Check(TEXT("the main menu lists every entry in order"), Main == TArray<EAction>({EAction::Continue, EAction::NewCampaign,
        EAction::ChapterSelect, EAction::Practice, EAction::Wallet, EAction::Settings, EAction::Credits, EAction::Quit}));
    Check(TEXT("every main menu row has Japanese and English"), !FrontEnd->Rows().ContainsByPredicate([](const SoraUI::FRow& Row)
    {
        return Row.Japanese.IsEmpty() || Row.English.IsEmpty();
    }));

    Scope.Choose(Keys, EAction::NewCampaign);
    Check(TEXT("a new campaign over saved progress asks first, starting on Cancel"), Scope.On(EScreen::Confirm) &&
        Scope.Focused()->Action == EAction::ConfirmNo);
    Scope.Key(Keys.Back);
    Check(TEXT("back withdraws it and keeps the saved chapter"), Scope.On(EScreen::Main) && Mode->Campaign()->ChapterId == Chapter);

    Scope.Choose(Keys, EAction::ChapterSelect);
    if (Check(TEXT("chapter select opens"), Scope.On(EScreen::ChapterSelect) && Scope.Paused()))
    {
        const TArray<SoraUI::FRow>& Rows = FrontEnd->Rows();
        Check(TEXT("eight chapters and Back"), Rows.Num() == 9 && Rows.Last().Action == EAction::Back);
        for (int32 Index = 0; Index < 8 && Index < Rows.Num(); ++Index)
            Check(*FString::Printf(TEXT("chapter %d is %s"), Index + 1, Index <= Chapter ? TEXT("open") : TEXT("locked")),
                Rows[Index].bEnabled == (Index <= Chapter));
        Check(TEXT("focus starts on the saved chapter"), FrontEnd->Focus() == Chapter);
        Scope.Key(Keys.Down);
        Check(TEXT("down skips the locked chapters to Back"), FrontEnd->Focus() == 8);
        Scope.Key(Keys.Up);
        Check(TEXT("up returns to the last open chapter"), FrontEnd->Focus() == Chapter);
        Scope.Key(Keys.Accept);
        Check(TEXT("a chapter asks before moving the save, starting on Cancel"), Scope.On(EScreen::Confirm) &&
            Scope.Focused()->Action == EAction::ConfirmNo && FrontEnd->ConfirmEnglish().StartsWith(TEXT("Start Chapter 3?")));
        Scope.Key(Keys.Back);
        Check(TEXT("back withdraws it"), Scope.On(EScreen::ChapterSelect));
        Scope.Key(Keys.Back);
    }
    Check(TEXT("back returns to the main menu on the same row"), Scope.On(EScreen::Main) && Scope.Focused()->Action == EAction::ChapterSelect);

    Scope.Choose(Keys, EAction::Practice);
    if (Check(TEXT("the practice lobby opens"), Scope.On(EScreen::Practice) && Scope.Paused()))
    {
        Scope.Key(Keys.Right);
        Check(TEXT("right changes the mode"), FrontEnd->Lobby().Mode == SoraPracticeLobby::Control);
        Scope.Key(Keys.Left);
        Check(TEXT("left changes it back"), FrontEnd->Lobby().Mode == SoraPracticeLobby::FreeForAll);
        Scope.Key(Keys.Back);
    }
    Scope.Choose(Keys, EAction::Wallet);
    if (Check(TEXT("the wallet screen opens"), Scope.On(EScreen::Wallet) && Scope.Paused()))
    {
        Check(TEXT("wallet rows: pair, open, disconnect, back"), FrontEnd->Rows().Num() == 4);
        Scope.Key(Keys.Back);
    }
    Scope.Choose(Keys, EAction::Settings);
    if (Check(TEXT("settings open"), Scope.On(EScreen::Settings) && Scope.Paused()))
    {
        const TPair<EAction, EScreen> Screens[] = {{EAction::OpenGraphics, EScreen::Graphics}, {EAction::OpenAudio, EScreen::Audio},
            {EAction::OpenSubtitles, EScreen::Subtitles}, {EAction::OpenControls, EScreen::Controls}, {EAction::OpenAccessibility, EScreen::Accessibility}};
        for (const TPair<EAction, EScreen>& Screen : Screens)
        {
            Scope.Choose(Keys, Screen.Key);
            const FString Name = FString::Printf(TEXT("settings screen %d"), static_cast<int32>(Screen.Value));
            if (!Check(*(Name + TEXT(" opens over the paused world")), Scope.On(Screen.Value) && Scope.Paused()))
                continue;
            Check(*(Name + TEXT(": every row has Japanese and English")), !FrontEnd->Rows().ContainsByPredicate([](const SoraUI::FRow& Row)
            {
                return Row.Japanese.IsEmpty() || Row.English.IsEmpty();
            }));
            if (Screen.Value == EScreen::Subtitles)
            {
                const bool bEnglish = Mode->bEnglishSubtitles;
                Scope.Key(Keys.Right);
                Check(TEXT("right toggles English subtitles"), Mode->bEnglishSubtitles != bEnglish);
                Scope.Key(Keys.Left);
                Check(TEXT("left toggles them back"), Mode->bEnglishSubtitles == bEnglish);
            }
            if (Screen.Value == EScreen::Controls)
            {
                Scope.FocusOn(Keys, EAction::Binding, SoraInput::FindRemappable(TEXT("Fire"), 0));
                Scope.Key(Keys.Accept);
                Check(TEXT("accept on Fire opens its rebind for this device"), FrontEnd->IsCapturing() && FrontEnd->CaptureDevice() == Keys.Device);
                Scope.Key(Keys.Pause);
                Check(TEXT("Start or Esc cancels the rebind"), Scope.On(EScreen::Controls));
                Scope.FocusOn(Keys, EAction::ResetControls);
                Scope.Key(Keys.Accept);
                Check(TEXT("resetting the keys asks first, starting on Cancel"), Scope.On(EScreen::Confirm) && Scope.Focused()->Action == EAction::ConfirmNo);
                Scope.Key(Keys.Back);
                Check(TEXT("back withdraws it"), Scope.On(EScreen::Controls));
            }
            Scope.Key(Keys.Back);
            Check(*(Name + TEXT(": back returns to the settings hub on the same row")), Scope.On(EScreen::Settings) && Scope.Focused()->Action == Screen.Key);
        }
        Scope.Key(Keys.Back);
    }
    Scope.Choose(Keys, EAction::Credits);
    if (Check(TEXT("credits open"), Scope.On(EScreen::Credits) && Scope.Paused()))
    {
        Check(TEXT("credits read ThirdPartyNotices"), FrontEnd->CreditsError().IsEmpty() &&
            FrontEnd->Credits().ContainsByPredicate([](const SoraUI::FCreditLine& Line) { return Line.Line.Contains(TEXT("QR Code generator")); }));
        Scope.Key(Keys.Down);
        Check(TEXT("down scrolls the credits"), FrontEnd->CreditsScroll > 0);
        Scope.Key(Keys.Back);
    }
    Scope.Choose(Keys, EAction::Quit);
    Check(TEXT("quit asks first, starting on Cancel"), Scope.On(EScreen::Confirm) && Scope.Focused()->Action == EAction::ConfirmNo);
    Scope.Key(Keys.Back);
    Check(TEXT("back withdraws the quit dialog"), Scope.On(EScreen::Main) && Scope.Paused());
    Scope.Key(Keys.Back);
    Check(TEXT("back on the main menu returns to the title"), Scope.On(EScreen::Title));
    Scope.Key(Keys.Accept);
    Scope.Choose(Keys, EAction::Continue);
    if (!Check(TEXT("continue opens the saved chapter's title card"),
        !Mode->bMenu && !Scope.Paused() && Mode->TitleCardChapter() == &FSoraCatalog::Get().Chapter(Chapter)))
        return false;
    Scope.Key(Keys.Pause);
    Check(TEXT("the pause key opens the pause menu over the paused card"), Scope.On(EScreen::Pause) && FrontEnd->IsPauseContext() && Scope.Paused());
    Scope.Choose(Keys, EAction::Settings);
    Check(TEXT("settings open from the pause menu"), Scope.On(EScreen::Settings) && FrontEnd->IsPauseContext() && Scope.Paused());
    Scope.Key(Keys.Back);
    Check(TEXT("back returns to the pause menu"), Scope.On(EScreen::Pause) && Scope.Paused());
    Scope.Choose(Keys, EAction::Restart);
    Check(TEXT("restart asks first, starting on Cancel"), Scope.On(EScreen::Confirm) && Scope.Focused()->Action == EAction::ConfirmNo);
    Scope.Key(Keys.Back);
    Check(TEXT("back withdraws it, still paused"), Scope.On(EScreen::Pause) && Scope.Paused());
    Scope.Choose(Keys, EAction::ReturnToTitle);
    Check(TEXT("return to title asks first"), Scope.On(EScreen::Confirm));
    Scope.Key(Keys.Up);
    Scope.Key(Keys.Accept);
    const bool bReturned = Check(TEXT("confirming returns to the main menu with the chapter kept"), Scope.On(EScreen::Main) &&
        !FrontEnd->IsPauseContext() && Mode->bMenu && Scope.Paused() && Mode->bCampaign && Mode->Campaign()->ChapterId == Chapter);
    Scope.AfterKey = nullptr;
    bool bEverywhere = true;
    for (int32 Screen = 0; Screen <= static_cast<int32>(EScreen::Capture); ++Screen)
        bEverywhere &= Check(*FString::Printf(TEXT("the keys reach screen %d"), Screen), Visited.Contains(static_cast<EScreen>(Screen)));
    // New campaign, chapter, reset keys, quit, restart and return to title.
    bEverywhere &= Check(*FString::Printf(TEXT("the keys reach all six confirmations (%d)"), Dialogs.Num()), Dialogs.Num() == 6);
    return bReturned && bEverywhere;
}
} // namespace SoraFrontEndTests

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFrontEndEveryScreenTest,
    "SoraArena.UI.EveryScreenByPadAndKeyboard",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFrontEndEveryScreenTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraFrontEndTests;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    const bool bPad = Tour(*this, Pad);
    const bool bKeyboard = Tour(*this, Keyboard);
    return bPad && bKeyboard;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFrontEndChapterSelectTest,
    "SoraArena.UI.ChapterSelect",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFrontEndChapterSelectTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraFrontEndTests;
    const FSoraCatalog& Catalog = FSoraCatalog::Get();
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    {
        // Chapter five at a later checkpoint beat; replay chapter two.
        FScope Scope(*this, TEXT("ChapterSelect"));
        constexpr int32 Chapter = 4, Replay = 1;
        int32 Beat = INDEX_NONE;
        for (int32 Index = 1; Beat == INDEX_NONE && Index < Catalog.Chapter(Chapter).Rules.Num(); ++Index)
            if (Catalog.Chapter(Chapter).Rules[Index].Checkpoint && !Catalog.Chapter(Chapter).Rules[Index].Optional)
                Beat = Index;
        if (!TestTrue(TEXT("Chapter five has a later checkpoint beat"), Beat != INDEX_NONE) || !Scope.Seed(Chapter, Chapter, Beat) || !Scope.Start())
            return false;
        ASoraGameMode* Mode = Scope.Mode();
        USoraFrontEnd* FrontEnd = Scope.FrontEnd();
        Scope.Key(Keyboard.Accept);
        Scope.Choose(Keyboard, EAction::ChapterSelect);
        if (!TestTrue(TEXT("Chapter select opens on the saved chapter"), Scope.On(EScreen::ChapterSelect) && FrontEnd->Focus() == Chapter))
            return false;
        FrontEnd->Click(6);
        TestTrue(TEXT("A click on a locked chapter does nothing"), Scope.On(EScreen::ChapterSelect) && FrontEnd->Focus() == Chapter);
        for (int32 Step = Chapter; Step > Replay; --Step)
            Scope.Key(Keyboard.Up);
        Scope.Key(Keyboard.Accept);
        TestTrue(TEXT("Replaying asks first"), Scope.On(EScreen::Confirm));
        Scope.Key(Keyboard.Up);
        Scope.Key(Keyboard.Accept);
        TestTrue(TEXT("The replayed chapter opens on its title card"), !Mode->bMenu && Mode->TitleCardChapter() == &Catalog.Chapter(Replay));
        const USoraSaveGame* Saved = Cast<USoraSaveGame>(UGameplayStatics::LoadGameFromSlot(Scope.Slot, 0));
        // The replayed chapter's opening cinematic is its first checkpoint.
        TestTrue(TEXT("The save moves to the replayed chapter, keeps its reach and drops the old checkpoint"),
            Saved && Saved->CurrentChapter == Replay && Saved->HighestChapter == Chapter && Saved->CheckpointChapter == Replay &&
            Saved->CheckpointBeat == 0 && Saved->CheckpointBeatsMask == 0);
    }
    {
        // A liberated campaign: no Continue, and its final chapter replays as a fight.
        FScope Scope(*this, TEXT("ChapterSelectLiberated"));
        constexpr int32 Final = 7;
        if (!Scope.Seed(Final, Final, INDEX_NONE, true) || !Scope.Start())
            return false;
        ASoraGameMode* Mode = Scope.Mode();
        USoraFrontEnd* FrontEnd = Scope.FrontEnd();
        Scope.Key(Pad.Accept);
        TestTrue(TEXT("A liberated campaign offers no Continue"), Scope.On(EScreen::Main) && FrontEnd->Rows()[0].Action == EAction::NewCampaign);
        Scope.Choose(Pad, EAction::ChapterSelect);
        Scope.Choose(Pad, EAction::Chapter, Final);
        Scope.Key(Pad.Up);
        Scope.Key(Pad.Accept);
        TestTrue(TEXT("The final chapter replays as a fight, not the liberated city"), !Mode->bMenu && !Mode->bChapterComplete &&
            !Mode->Campaign()->bCampaignComplete && Mode->TitleCardChapter() == &Catalog.Chapter(Final));
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFrontEndPracticeLobbyTest,
    "SoraArena.UI.PracticeLobby",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFrontEndPracticeLobbyTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraFrontEndTests;
    namespace Lobby = SoraPracticeLobby;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // The selection's rules, without a world.
    const auto Valid = [](TFunctionRef<void(FSoraPracticeLobbySelection&)> Change)
    {
        FSoraPracticeLobbySelection Selection;
        Change(Selection);
        return Lobby::IsValid(Selection);
    };
    TestTrue(TEXT("The default selection is valid"), Valid([](FSoraPracticeLobbySelection&) {}));
    TestTrue(TEXT("Six against six is valid"), Valid([](FSoraPracticeLobbySelection& S) { S.Mode = Lobby::Control; S.PlayerCount = 12; }));
    TestFalse(TEXT("Uneven teams are rejected"), Valid([](FSoraPracticeLobbySelection& S) { S.Mode = Lobby::Payload; S.PlayerCount = 7; }));
    TestFalse(TEXT("Nine in a free-for-all is rejected"), Valid([](FSoraPracticeLobbySelection& S) { S.PlayerCount = 9; }));
    TestFalse(TEXT("Another class's special is rejected"), Valid([](FSoraPracticeLobbySelection& S) { S.ClassId = 1; S.SpecialWeaponId = 12; }));
    TestFalse(TEXT("A standard weapon is no special"), Valid([](FSoraPracticeLobbySelection& S) { S.SpecialWeaponId = 1; }));
    TestFalse(TEXT("Melee admits no ranged special"), Valid([](FSoraPracticeLobbySelection& S) { S.Mode = Lobby::Melee; S.ClassId = 3; S.SpecialWeaponId = 15; }));
    TestTrue(TEXT("Melee admits the naginata"), Valid([](FSoraPracticeLobbySelection& S) { S.Mode = Lobby::Melee; S.SpecialWeaponId = 12; }));
    TestFalse(TEXT("A fifth arena is rejected"), Valid([](FSoraPracticeLobbySelection& S) { S.MapId = 4; }));
    TestFalse(TEXT("A fifth difficulty is rejected"), Valid([](FSoraPracticeLobbySelection& S) { S.Difficulty = 4; }));
    // Every special weapon states its tradeoff in Japanese, and its English
    // subtitle is the catalog's own tradeoff, word for word.
    for (const FSoraWeapon& Weapon : FSoraCatalog::Get().Weapons)
    {
        const FText Tradeoff = SoraUI::SpecialTradeoff(Weapon.Id);
        if (Weapon.Special)
            TestTrue(*FString::Printf(TEXT("%s's tradeoff is in Japanese with the catalog's English"), *Weapon.NameEnglish),
                !Tradeoff.IsEmpty() && HasJapanese(Tradeoff.ToString()) && SoraText::English(Tradeoff) == Weapon.Tradeoff);
        else
            TestTrue(*FString::Printf(TEXT("%s is no special and has no tradeoff"), *Weapon.NameEnglish), Tradeoff.IsEmpty());
    }

    FScope Scope(*this, TEXT("PracticeLobby"));
    if (!Scope.Start())
        return false;
    ASoraGameMode* Mode = Scope.Mode();
    USoraFrontEnd* FrontEnd = Scope.FrontEnd();
    UArenaKernelSubsystem* Kernel = Mode->Kernel();
    const FSoraPracticeLobbySelection& L = FrontEnd->Lobby();
    Scope.Key(Keyboard.Accept);
    Scope.Choose(Keyboard, EAction::Practice);
    if (!TestTrue(TEXT("The lobby opens"), Scope.On(EScreen::Practice)))
        return false;
    TestTrue(TEXT("The lobby starts from the saved class and map, a full free-for-all"), L.ClassId == Mode->SelectedClass &&
        L.MapId == Mode->MapId && L.Mode == Lobby::FreeForAll && L.PlayerCount == 8 && L.SpecialWeaponId == INDEX_NONE && L.Difficulty == Lobby::Standard);
    Scope.Key(Keyboard.Right);
    TestTrue(TEXT("Control keeps eight players as four against four"), L.Mode == Lobby::Control && L.PlayerCount == 8);
    const auto RowFor = [FrontEnd](EAction Action) { return FrontEnd->Rows().FindByPredicate([Action](const SoraUI::FRow& Row) { return Row.Action == Action; }); };
    TestTrue(TEXT("A team mode's hint leaves the team size to the Players row"), RowFor(EAction::LobbyMode) &&
        !RowFor(EAction::LobbyMode)->HintJapanese.Contains(TEXT("六対六")) && !RowFor(EAction::LobbyMode)->HintEnglish.Contains(TEXT("Six")));
    Scope.FocusOn(Keyboard, EAction::LobbyPlayers);
    for (int32 Press = 0; Press < 3; ++Press)
        Scope.Key(Keyboard.Right);
    TestEqual(TEXT("Team players rise two at a time to six against six"), L.PlayerCount, 12);
    Scope.FocusOn(Keyboard, EAction::LobbyMode);
    Scope.Key(Keyboard.Right);
    Scope.Key(Keyboard.Right);
    TestTrue(TEXT("Melee only clamps the count to eight"), L.Mode == Lobby::Melee && L.PlayerCount == 8);
    TestTrue(TEXT("Melee is named for every melee weapon, not the katana alone"), RowFor(EAction::LobbyMode) &&
        RowFor(EAction::LobbyMode)->ValueJapanese == TEXT("近接のみ") && RowFor(EAction::LobbyMode)->ValueEnglish == TEXT("Melee only"));
    Scope.FocusOn(Keyboard, EAction::LobbyClass);
    for (int32 Press = 0; Press < 3; ++Press)
        Scope.Key(Keyboard.Right);
    const SoraUI::FRow* Special = FrontEnd->Rows().FindByPredicate([](const SoraUI::FRow& Row) { return Row.Action == EAction::LobbySpecial; });
    TestTrue(TEXT("Hanabi has no melee special, so the special row is closed in Melee"), L.ClassId == 3 && Special && !Special->bEnabled);
    Scope.Key(Keyboard.Up);
    Scope.Key(Keyboard.Up);
    Scope.Key(Keyboard.Right);
    TestTrue(TEXT("Mode wraps back to free-for-all"), Scope.Focused()->Action == EAction::LobbyMode && L.Mode == Lobby::FreeForAll);
    Scope.FocusOn(Keyboard, EAction::LobbySpecial);
    Scope.Key(Keyboard.Right);
    TestEqual(TEXT("Hanabi brings the micro-mortar"), L.SpecialWeaponId, 15);
    const SoraUI::FRow* Mortar = RowFor(EAction::LobbySpecial);
    TestTrue(TEXT("The special's hint opens with its tradeoff in both languages"), Mortar &&
        Mortar->HintJapanese.StartsWith(SoraUI::SpecialTradeoff(15).ToString()) && Mortar->HintEnglish.StartsWith(FSoraCatalog::Get().Weapon(15).Tradeoff));
    // Every lobby choice reaches the practice director, so the Start row
    // carries only its zero-stake line.
    const SoraUI::FRow* StartRow = RowFor(EAction::LobbyStart);
    const SoraText::FLine StartHint = SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Lobby.Start.Hint", "資産は預けず、報酬も発生しない。"));
    TestTrue(TEXT("The Start row states only that nothing is bonded"), StartRow &&
        StartRow->HintJapanese == StartHint.Japanese && StartRow->HintEnglish == StartHint.English);
    Scope.Key(Keyboard.Up);
    Scope.Key(Keyboard.Right);
    TestTrue(TEXT("The special follows the class to Karakuri's shock emitter"), L.ClassId == 4 && L.SpecialWeaponId == 16);
    const int32 Map = (L.MapId + 2) % Lobby::MapCount;
    Scope.Key(Keyboard.Up);
    Scope.Key(Keyboard.Right);
    Scope.Key(Keyboard.Right);
    TestEqual(TEXT("The arena steps through the four maps"), L.MapId, Map);
    Scope.FocusOn(Keyboard, EAction::LobbyDifficulty);
    Scope.Key(Keyboard.Right);
    TestEqual(TEXT("Difficulty rises to veteran"), L.Difficulty, static_cast<int32>(Lobby::Veteran));

    // A selection the lobby could not build is refused and the menu stays.
    FSoraPracticeLobbySelection Broken = L;
    Broken.PlayerCount = 1;
    TestFalse(TEXT("An invalid selection is refused"), Mode->StartPracticeFromLobby(Broken));
    TestTrue(TEXT("The refusal keeps the lobby open with a reason"), Scope.On(EScreen::Practice) && !Mode->NoticeEnglish.IsEmpty() && !Mode->bDeterministicPractice);

    if (!TestTrue(TEXT("Staged Rust kernel is available"), Kernel && Kernel->Available))
        return false;
    Scope.Choose(Keyboard, EAction::LobbyStart);
    const FSoraPracticeConfig& Config = Mode->Practice()->Config;
    if (!TestTrue(TEXT("Start begins kernel practice with every lobby choice"), !Mode->bMenu && Mode->bDeterministicPractice &&
        Kernel->PracticeActive() && Mode->SelectedClass == 4 && Mode->MapId == Map && Config.Mode == L.Mode &&
        Config.PlayerCount == L.PlayerCount && Config.MapId == L.MapId && Config.ClassId == L.ClassId &&
        Config.SpecialWeaponId == 16 && Config.Difficulty == L.Difficulty && Kernel->PracticePlayers.Num() == L.PlayerCount))
        return false;
    const SoraText::FLine Reload = SoraUI::ActionKey(Mode, TEXT("Reload"));
    TestTrue(TEXT("The practice notice names the player's own keys in both languages"), !Reload.Japanese.IsEmpty() &&
        Mode->Notice.Contains(Reload.Japanese + TEXT(" 装填")) && Mode->NoticeEnglish.Contains(Reload.English + TEXT(" reload")) &&
        !HasJapanese(Mode->NoticeEnglish));
    Scope.World->Tick(FramesPerSecond);
    TestTrue(TEXT("Practice steps in play"), Kernel->PracticeTick > 0 && Mode->IsPlaying());
    Scope.Key(Keyboard.Pause);
    TestTrue(TEXT("Esc pauses practice"), Scope.On(EScreen::Pause) && Scope.Paused() &&
        FrontEnd->Rows().ContainsByPredicate([](const SoraUI::FRow& Row) { return Row.Action == EAction::Restart && Row.English == TEXT("Restart practice"); }));
    Scope.Choose(Keyboard, EAction::ReturnToTitle);
    Scope.Key(Keyboard.Up);
    Scope.Key(Keyboard.Accept);
    return TestTrue(TEXT("Returning to the title ends practice and restores the campaign round"), Scope.On(EScreen::Main) &&
        !Mode->bDeterministicPractice && Mode->bCampaign && !Kernel->PracticeActive() && Scope.Paused());
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFrontEndReadableTest,
    "SoraArena.UI.SlateReadableAt720p",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFrontEndReadableTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraFrontEndTests;
    // The viewport scales Slate by the project's DPI curve. At 720p the
    // smallest English text must stay at least 18 px tall and Japanese 21 px.
    const float Scale720 = GetDefault<UUserInterfaceSettings>()->GetDPIScaleBasedOnSize(FIntPoint(1280, 720));
    const float PixelsPerPoint = 96.f / 72.f;
    TestTrue(TEXT("720p scales the 1080p layout by about two thirds"), FMath::IsNearlyEqual(Scale720, .666f, .01f));
    TestTrue(TEXT("English text is at least 18 px at 720p"), SoraUI::MinEnglishFontSize * PixelsPerPoint * Scale720 >= 18.f);
    TestTrue(TEXT("Japanese text is at least 21 px at 720p"), SoraUI::MinJapaneseFontSize * PixelsPerPoint * Scale720 >= 21.f);
    if (!TestTrue(TEXT("Slate is running"), FSlateApplication::IsInitialized()) || !TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;

    FScope Scope(*this, TEXT("Readable"));
    if (!Scope.Start())
        return false;
    ASoraGameMode* Mode = Scope.Mode();
    USoraFrontEnd* FrontEnd = Scope.FrontEnd();
    TStrongObjectPtr<UFont> Font(NewObject<UFont>(GetTransientPackage()));
    Font->FontCacheType = EFontCacheType::Runtime;
    Font->GetMutableInternalCompositeFont() = FCompositeFont(FName(TEXT("Regular")),
        FPaths::ProjectContentDir() / TEXT("SourceArt/Fonts/NotoSansCJKjp-Regular.otf"), EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
    TSharedRef<SSoraFrontEnd> Widget = SNew(SSoraFrontEnd).FrontEnd(FrontEnd).Font(Font.Get());
    const auto Screen = [&](const TCHAR* Name)
    {
        Widget->Refresh();
        TestEqual(*FString::Printf(TEXT("%s draws one widget per row"), Name), Widget->RowWidgetCount(), FrontEnd->Rows().Num());
        float Smallest = TNumericLimits<float>::Max();
        for (const float Size : Widget->FontSizesUsed())
            Smallest = FMath::Min(Smallest, Size);
        TestTrue(*FString::Printf(TEXT("%s uses text"), Name), Widget->FontSizesUsed().Num() > 0);
        TestTrue(*FString::Printf(TEXT("%s never goes below the English minimum (%.0f pt)"), Name, Smallest), Smallest >= SoraUI::MinEnglishFontSize);
    };
    const auto Press = [&](const FKey& Key)
    {
        const FKeyEvent Event(Key, FModifierKeysState(), 0, false, 0, 0);
        return Widget->OnKeyDown(FGeometry(), Event).IsEventHandled();
    };
    Screen(TEXT("Title"));
    TestTrue(TEXT("The title shows the 120 pt 猫柳生"), Widget->FontSizesUsed().Contains(120.f));
    TestTrue(TEXT("The widget takes the key that leaves the title"), Press(EKeys::Gamepad_FaceButton_Bottom) && Scope.On(EScreen::Main));
    TestEqual(TEXT("A pad key switches prompts to the pad"), SoraUI::PromptKey(SoraUI::ECommand::Accept, FrontEnd->Device()), FString(TEXT("A")));
    Screen(TEXT("Main menu"));
    // The game's name heads every menu screen with its English subtitle.
    const SoraText::FLine GameName = SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Heading.Game", "SORA 抵抗軍　猫柳生"));
    TestTrue(TEXT("The game's name heads the menu in Japanese and English"), !GameName.English.IsEmpty() &&
        Widget->LinesDrawn().Contains(GameName.Japanese) && Widget->LinesDrawn().Contains(GameName.English));
    Mode->Settings()->SetEnglishSubtitles(false);
    Widget->Refresh();
    TestTrue(TEXT("With English off the name is Japanese alone"), Widget->LinesDrawn().Contains(GameName.Japanese) &&
        !Widget->LinesDrawn().Contains(GameName.English));
    Mode->Settings()->SetEnglishSubtitles(true);
    Widget->Refresh();
    const int32 Focus = FrontEnd->Focus();
    TestTrue(TEXT("The widget moves focus with the arrow keys"), Press(EKeys::Down) && FrontEnd->Focus() == Focus + 1);
    TestEqual(TEXT("A keyboard key switches prompts back"), SoraUI::PromptKey(SoraUI::ECommand::Accept, FrontEnd->Device()), FString(TEXT("Enter")));
    TestTrue(TEXT("The widget swallows keys without menu meaning"), Press(EKeys::M) && Scope.On(EScreen::Main));
    for (const EAction Action : {EAction::ChapterSelect, EAction::Practice, EAction::Wallet, EAction::Settings, EAction::Credits, EAction::Quit})
    {
        Scope.FocusOn(Keyboard, Action);
        Press(EKeys::Enter);
        Screen(*FString::Printf(TEXT("Screen %d"), static_cast<int32>(FrontEnd->Screen())));
        if (Action == EAction::Settings)
            for (const EAction Setting : {EAction::OpenGraphics, EAction::OpenAudio, EAction::OpenSubtitles, EAction::OpenControls, EAction::OpenAccessibility})
            {
                Scope.FocusOn(Keyboard, Setting);
                Press(EKeys::Enter);
                Screen(*FString::Printf(TEXT("Settings screen %d"), static_cast<int32>(FrontEnd->Screen())));
                if (Setting == EAction::OpenControls)
                {
                    Scope.FocusOn(Keyboard, EAction::Binding);
                    TestTrue(TEXT("Enter through the widget opens the rebind dialog"), Press(EKeys::Enter) && FrontEnd->IsCapturing());
                    Screen(TEXT("Rebind dialog"));
                    TestTrue(TEXT("Esc through the widget cancels the rebind"), Press(EKeys::Escape) && Scope.On(EScreen::Controls));
                }
                Press(EKeys::Escape);
            }
        Press(EKeys::Escape);
    }
    TestTrue(TEXT("Every screen closed back to the main menu"), Scope.On(EScreen::Main));
    Mode->BeginRound();
    Mode->OpenPauseMenu();
    Screen(TEXT("Pause menu"));
    Press(EKeys::Escape);
    TestTrue(TEXT("Esc through the widget resumes"), !Mode->bMenu && !FrontEnd->IsOpen());
    Widget->Refresh();
    return TestEqual(TEXT("A closed front end draws no rows"), Widget->RowWidgetCount(), 0);
}

// Runs only in a rendering game client, never in the NullRHI editor suite:
//   scripts/toolchain/run-editor.sh -game -windowed -ResX=1280 -ResY=720 \
//     -ExecCmds="Automation RunTests SoraArena.UIRendered;Quit"
// Keys go through FSlateApplication to the focused SSoraFrontEnd, as a
// player's do, and every screen is saved with its UI to
// Saved/Screenshots/SoraFrontEnd/<width>x<height>/ for review. It opens and
// closes screens only, so the campaign save is read but never written and no
// setting changes. Like any launch, the first one on a machine applies the
// platform's graphics preset and records that in the settings slot.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraFrontEndRenderedTest,
    "SoraArena.UIRendered.FrontEndScreens",
    EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraFrontEndRenderedTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using SoraUI::EAction;
    UWorld* World = nullptr;
    for (const FWorldContext& Context : GEngine->GetWorldContexts())
        if (Context.WorldType == EWorldType::Game && Context.World())
            World = Context.World();
    ASoraGameMode* Mode = World ? Cast<ASoraGameMode>(World->GetAuthGameMode()) : nullptr;
    UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr;
    if (!TestNotNull(TEXT("A game world runs ASoraGameMode"), Mode) || !TestNotNull(TEXT("The game has a viewport"), Viewport) ||
        !TestTrue(TEXT("Slate is running"), FSlateApplication::IsInitialized()))
        return false;
    FVector2D Size;
    Viewport->GetViewportSize(Size);
    const FString Folder = FPaths::ProjectSavedDir() / TEXT("Screenshots/SoraFrontEnd") /
        FString::Printf(TEXT("%dx%d"), FMath::RoundToInt(Size.X), FMath::RoundToInt(Size.Y));
    TWeakObjectPtr<USoraFrontEnd> FrontEnd = Mode->FrontEnd();
    if(!TestNotNull(TEXT("The rendered game has its front end"),FrontEnd.Get())) return false;
    // This navigation tour may run after the entire client suite, with the
    // live viewport receiving input for many minutes. Establish its title
    // precondition explicitly; an untouched launch is checked separately.
    AddInfo(FString::Printf(TEXT("Front-end tour initial screen=%d; returning to title for navigation"),
        static_cast<int32>(FrontEnd->Screen())));
    Mode->SetMenuOpen(true);
    FrontEnd->ShowTitle();
    FrontEnd->NoteDevice(SoraUI::EDevice::KeyboardMouse);
    const auto Press = [](const FKey& Key)
    {
        const FKeyEvent Event(Key, FSlateApplication::Get().GetModifierKeys(), 0, false, 0, 0);
        FSlateApplication::Get().ProcessKeyDownEvent(Event);
        FSlateApplication::Get().ProcessKeyUpEvent(Event);
    };
    const auto Step = [](TFunction<void()> Action)
    {
        ADD_LATENT_AUTOMATION_COMMAND(FFunctionLatentCommand([Action]() { Action(); return true; }));
    };
    const auto Shot = [Folder](const TCHAR* Name)
    {
        ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(.75f));
        const FString File = Folder / (FString(Name) + TEXT(".png"));
        ADD_LATENT_AUTOMATION_COMMAND(FFunctionLatentCommand([File]()
        {
            FScreenshotRequest::RequestScreenshot(File, true, false);
            return true;
        }));
        ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(.75f));
    };
    // Moves down to the row with this action through the widget, then opens it.
    const auto Open = [this, FrontEnd, Press](EAction Action)
    {
        for (int32 Attempt = 0; FrontEnd.IsValid() && Attempt <= FrontEnd->Rows().Num(); ++Attempt)
        {
            const TArray<SoraUI::FRow>& Rows = FrontEnd->Rows();
            if (Rows.IsValidIndex(FrontEnd->Focus()) && Rows[FrontEnd->Focus()].Action == Action)
            {
                Press(EKeys::Enter);
                return;
            }
            Press(EKeys::Down);
        }
        AddError(FString::Printf(TEXT("No row for action %d"), static_cast<int32>(Action)));
    };
    ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(4.f));
    Step([this, FrontEnd]()
    {
        const TSharedPtr<SWidget> Focused = FSlateApplication::Get().GetKeyboardFocusedWidget();
        TestTrue(TEXT("The title screen is open"), FrontEnd.IsValid() && FrontEnd->IsOpen() && FrontEnd->Screen() == SoraUI::EScreen::Title);
        TestTrue(TEXT("The front end widget holds keyboard focus"), Focused.IsValid() && Focused->GetType() == FName(TEXT("SSoraFrontEnd")));
    });
    Shot(TEXT("01_Title"));
    Step([Press]() { Press(EKeys::Enter); });
    Shot(TEXT("02_MainKeyboard"));
    // The mouse, hit-tested by Slate on the drawn rows: moving onto a row
    // focuses it, a left click opens it and a right click goes back.
    TSharedPtr<FVector2D> Pointer = MakeShared<FVector2D>(FVector2D::ZeroVector);
    Step([this, FrontEnd, Pointer]()
    {
        const TSharedPtr<SSoraFrontEnd> Widget = StaticCastSharedPtr<SSoraFrontEnd>(FSlateApplication::Get().GetKeyboardFocusedWidget());
        const int32 Index = FrontEnd.IsValid() ? FrontEnd->Rows().IndexOfByPredicate([](const SoraUI::FRow& Row) { return Row.Action == EAction::ChapterSelect; }) : INDEX_NONE;
        const TSharedPtr<SWidget> Row = Widget ? Widget->RowWidget(Index) : nullptr;
        if (!TestTrue(TEXT("The chapter-select row is drawn"), Row.IsValid()))
            return;
        *Pointer = Row->GetCachedGeometry().GetAbsolutePositionAtCoordinates(FVector2D(.5f, .5f));
        FSlateApplication::Get().ProcessMouseMoveEvent(
            FPointerEvent(0, *Pointer, *Pointer - FVector2D(0.f, 40.f), TSet<FKey>(), EKeys::Invalid, 0.f, FModifierKeysState()));
        TestTrue(TEXT("Moving the mouse onto a row focuses it and switches to mouse prompts"),
            FrontEnd->Focus() == Index && FrontEnd->Device() == SoraUI::EDevice::KeyboardMouse);
    });
    ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(.3f));
    Step([this, FrontEnd, Pointer]()
    {
        FSlateApplication& Slate = FSlateApplication::Get();
        const FPointerEvent Click(0, *Pointer, *Pointer, TSet<FKey>({EKeys::LeftMouseButton}), EKeys::LeftMouseButton, 0.f, FModifierKeysState());
        Slate.ProcessMouseButtonDownEvent(nullptr, Click);
        Slate.ProcessMouseButtonUpEvent(FPointerEvent(0, *Pointer, *Pointer, TSet<FKey>(), EKeys::LeftMouseButton, 0.f, FModifierKeysState()));
        TestTrue(TEXT("A left click on the row opens chapter select"), FrontEnd.IsValid() && FrontEnd->Screen() == SoraUI::EScreen::ChapterSelect);
    });
    ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(.3f));
    Step([this, FrontEnd, Pointer]()
    {
        FSlateApplication& Slate = FSlateApplication::Get();
        const FPointerEvent Click(0, *Pointer, *Pointer, TSet<FKey>({EKeys::RightMouseButton}), EKeys::RightMouseButton, 0.f, FModifierKeysState());
        Slate.ProcessMouseButtonDownEvent(nullptr, Click);
        Slate.ProcessMouseButtonUpEvent(FPointerEvent(0, *Pointer, *Pointer, TSet<FKey>(), EKeys::RightMouseButton, 0.f, FModifierKeysState()));
        TestTrue(TEXT("A right click goes back to the main menu"), FrontEnd.IsValid() && FrontEnd->Screen() == SoraUI::EScreen::Main);
    });
    const TPair<EAction, const TCHAR*> Screens[] = {
        {EAction::ChapterSelect, TEXT("03_ChapterSelect")}, {EAction::Practice, TEXT("04_PracticeLobby")},
        {EAction::Wallet, TEXT("05_Wallet")}, {EAction::Settings, TEXT("06_Settings")},
        {EAction::Credits, TEXT("07_Credits")}, {EAction::Quit, TEXT("09_QuitConfirm")}};
    for (const TPair<EAction, const TCHAR*>& Screen : Screens)
    {
        const EAction Action = Screen.Key;
        Step([Open, Action]() { Open(Action); });
        Shot(Screen.Value);
        if (Action == EAction::Credits)
        {
            Step([Press]() { for (int32 Line = 0; Line < 8; ++Line) Press(EKeys::Down); });
            Shot(TEXT("08_CreditsScrolled"));
        }
        Step([this, FrontEnd, Press]()
        {
            Press(EKeys::Escape);
            TestTrue(TEXT("Esc returns to the main menu"), FrontEnd.IsValid() && FrontEnd->Screen() == SoraUI::EScreen::Main);
        });
    }
    // The settings screens and the rebind dialog. Nothing is changed, so the
    // player's settings stay as they were.
    Step([Open]() { Open(EAction::Settings); });
    const TPair<EAction, const TCHAR*> Settings[] = {
        {EAction::OpenGraphics, TEXT("12_Graphics")}, {EAction::OpenAudio, TEXT("13_Audio")}, {EAction::OpenSubtitles, TEXT("14_Subtitles")},
        {EAction::OpenControls, TEXT("15_Controls")}, {EAction::OpenAccessibility, TEXT("18_Accessibility")}};
    for (const TPair<EAction, const TCHAR*>& Screen : Settings)
    {
        const EAction Action = Screen.Key;
        Step([Open, Action]() { Open(Action); });
        Shot(Screen.Value);
        if (Action == EAction::OpenControls)
        {
            // Down to Fire, so the shot shows both key columns.
            Step([FrontEnd, Press]()
            {
                const int32 Fire = SoraInput::FindRemappable(TEXT("Fire"), 0);
                for (int32 Attempt = 0; FrontEnd.IsValid() && Attempt <= FrontEnd->Rows().Num(); ++Attempt)
                {
                    const TArray<SoraUI::FRow>& Rows = FrontEnd->Rows();
                    if (Rows.IsValidIndex(FrontEnd->Focus()) && Rows[FrontEnd->Focus()].bBinding && Rows[FrontEnd->Focus()].Param == Fire)
                        return;
                    Press(EKeys::Down);
                }
            });
            Shot(TEXT("16_ControlsBindings"));
            Step([this, FrontEnd, Press]()
            {
                Press(EKeys::Enter);
                TestTrue(TEXT("Enter on a binding opens the rebind dialog"), FrontEnd.IsValid() && FrontEnd->IsCapturing());
            });
            Shot(TEXT("17_Rebind"));
            Step([this, FrontEnd, Press]()
            {
                Press(EKeys::Escape);
                TestTrue(TEXT("Esc cancels the rebind"), FrontEnd.IsValid() && FrontEnd->Screen() == SoraUI::EScreen::Controls);
            });
        }
        Step([this, FrontEnd, Press]()
        {
            Press(EKeys::Escape);
            TestTrue(TEXT("Esc returns to the settings hub"), FrontEnd.IsValid() && FrontEnd->Screen() == SoraUI::EScreen::Settings);
        });
    }
    Step([Press]() { Press(EKeys::Escape); });
    Step([this, FrontEnd, Press]()
    {
        Press(EKeys::Gamepad_DPad_Up);
        TestTrue(TEXT("A pad button switches the prompts to the pad"), FrontEnd.IsValid() && FrontEnd->Device() == SoraUI::EDevice::Gamepad);
    });
    Shot(TEXT("10_MainPad"));
    Step([this, FrontEnd, Press]()
    {
        Press(EKeys::Gamepad_FaceButton_Right);
        TestTrue(TEXT("Pad B returns to the title"), FrontEnd.IsValid() && FrontEnd->Screen() == SoraUI::EScreen::Title);
    });
    Shot(TEXT("11_TitlePad"));

    // Into play and back, where the HUD hands input between the viewport and
    // the front end. The round runs on a throwaway save slot, so the player's
    // campaign is never written, and it stops on the title card.
    const TWeakObjectPtr<ASoraGameMode> Game = Mode;
    const FString PlayerSlot = Mode->SaveSlotName;
    const FString Throwaway = FString::Printf(TEXT("SoraArenaRendered_%s"), *FGuid::NewGuid().ToString(EGuidFormats::Digits));
    const auto Hold = [](const FKey& Key, bool bDown)
    {
        const FKeyEvent Event(Key, FSlateApplication::Get().GetModifierKeys(), 0, false, 0, 0);
        if (bDown)
            FSlateApplication::Get().ProcessKeyDownEvent(Event);
        else
            FSlateApplication::Get().ProcessKeyUpEvent(Event);
    };
    const auto PlayInputHolds = [Game](const FKey& Key)
    {
        const APlayerController* Controller = Game.IsValid() ? Game->GetWorld()->GetFirstPlayerController() : nullptr;
        return Controller && Controller->PlayerInput && Controller->PlayerInput->IsPressed(Key);
    };
    const auto FrontEndHasFocus = []()
    {
        const TSharedPtr<SWidget> Focused = FSlateApplication::Get().GetKeyboardFocusedWidget();
        return Focused.IsValid() && Focused->GetType() == FName(TEXT("SSoraFrontEnd"));
    };
    Step([Game, Throwaway]()
    {
        if (Game.IsValid())
        {
            Game->SaveSlotName = Throwaway;
            Game->BeginRound();
        }
    });
    ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(.5f));
    Step([this, Game, FrontEnd, Hold, FrontEndHasFocus]()
    {
        TestTrue(TEXT("Closing the front end starts the round and hands focus to the game"), Game.IsValid() && !Game->bMenu &&
            FrontEnd.IsValid() && !FrontEnd->IsOpen() && !FrontEndHasFocus());
        Hold(EKeys::Gamepad_FaceButton_Left, true);
    });
    ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(.2f));
    Step([this, Hold, PlayInputHolds]()
    {
        TestTrue(TEXT("In play a held X reaches play input"), PlayInputHolds(EKeys::Gamepad_FaceButton_Left));
        Hold(EKeys::Gamepad_FaceButton_Left, false);
        Hold(EKeys::Escape, true);
        Hold(EKeys::Escape, false);
    });
    ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(.5f));
    Step([this, FrontEnd, Hold, FrontEndHasFocus]()
    {
        TestTrue(TEXT("Esc in play opens the pause menu, which takes keyboard focus"), FrontEnd.IsValid() &&
            FrontEnd->Screen() == SoraUI::EScreen::Pause && FrontEndHasFocus());
        Hold(EKeys::Gamepad_FaceButton_Left, true);
    });
    Shot(TEXT("19_Pause"));
    Step([this, FrontEnd, Hold, PlayInputHolds]()
    {
        TestFalse(TEXT("X held under the pause menu never reaches play input"), PlayInputHolds(EKeys::Gamepad_FaceButton_Left));
        TestTrue(TEXT("X means nothing to the pause menu"), FrontEnd.IsValid() && FrontEnd->Screen() == SoraUI::EScreen::Pause);
        Hold(EKeys::Gamepad_FaceButton_Left, false);
        Hold(EKeys::Escape, true);
        Hold(EKeys::Escape, false);
    });
    ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(.5f));
    Step([this, Game, FrontEnd, FrontEndHasFocus]()
    {
        TestTrue(TEXT("Esc resumes and focus returns to the game"), Game.IsValid() && !Game->bMenu && FrontEnd.IsValid() &&
            !FrontEnd->IsOpen() && !FrontEndHasFocus());
        // A director that stops play opens the menu itself.
        if (Game.IsValid())
            Game->SetMenuOpen(true);
    });
    ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(.5f));
    Step([this, FrontEnd, Hold, FrontEndHasFocus]()
    {
        TestTrue(TEXT("A director's menu lands on the main menu with keyboard focus"), FrontEnd.IsValid() &&
            FrontEnd->Screen() == SoraUI::EScreen::Main && FrontEndHasFocus());
        Hold(EKeys::E, true);
    });
    ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(.2f));
    Step([this, Hold, PlayInputHolds, Game, PlayerSlot, Throwaway]()
    {
        TestFalse(TEXT("E held under a director's menu never reaches play input"), PlayInputHolds(EKeys::E));
        Hold(EKeys::E, false);
        if (Game.IsValid())
            Game->SaveSlotName = PlayerSlot;
        if (UGameplayStatics::DoesSaveGameExist(Throwaway, 0))
            UGameplayStatics::DeleteGameInSlot(Throwaway, 0);
    });
    return true;
}
#endif
