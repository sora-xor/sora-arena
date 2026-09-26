#include "SoraFrontEnd.h"
#include "UI/SoraFrontEndRows.h"
#include "ArenaWalletSubsystem.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraGameMode.h"
#include "SoraInputStates.h"
#include "SoraPlayerCharacter.h"
#include "Engine/GameInstance.h"

namespace
{
using SoraUI::FChoice;
using SoraUI::NewBackRow;
using SoraUI::NewChoiceRow;
using SoraUI::NewMenuRow;
using SoraUI::NewOptionRow;

FChoice LobbyMode(int32 Mode)
{
    switch (Mode)
    {
    // The team modes seat two even teams; the Players row sets their size.
    case SoraPracticeLobby::Control:
        return {NSLOCTEXT("SoraArena.Menu", "Lobby.Mode.Control", "拠点制圧"),
            NSLOCTEXT("SoraArena.Menu", "Lobby.Mode.Control.Hint", "二組に分かれて拠点を奪い合う団体戦。")};
    case SoraPracticeLobby::Payload:
        return {NSLOCTEXT("SoraArena.Menu", "Lobby.Mode.Payload", "護送"),
            NSLOCTEXT("SoraArena.Menu", "Lobby.Mode.Payload.Hint", "二組に分かれ、荷車を押し進める側と食い止める側で戦う団体戦。")};
    case SoraPracticeLobby::Melee:
        return {NSLOCTEXT("SoraArena.Menu", "Lobby.Mode.Melee", "近接のみ"),
            NSLOCTEXT("SoraArena.Menu", "Lobby.Mode.Melee.Hint", "刀・鎖鎌・金棒など、近接武器だけで戦う個人戦。")};
    default:
        return {NSLOCTEXT("SoraArena.Menu", "Lobby.Mode.FreeForAll", "乱戦"),
            NSLOCTEXT("SoraArena.Menu", "Lobby.Mode.FreeForAll.Hint", "全員が敵の個人戦。最大八匹。")};
    }
}
FChoice LobbyDifficulty(int32 Difficulty)
{
    switch (Difficulty)
    {
    case SoraPracticeLobby::Novice:
        return {NSLOCTEXT("SoraArena.Menu", "Lobby.Difficulty.Novice", "入門"),
            NSLOCTEXT("SoraArena.Menu", "Lobby.Difficulty.Novice.Hint", "ボットは狙いが甘く、防御も少ない。")};
    case SoraPracticeLobby::Veteran:
        return {NSLOCTEXT("SoraArena.Menu", "Lobby.Difficulty.Veteran", "手練れ"),
            NSLOCTEXT("SoraArena.Menu", "Lobby.Difficulty.Veteran.Hint", "ボットは受け流しと連携を使う。")};
    case SoraPracticeLobby::Master:
        return {NSLOCTEXT("SoraArena.Menu", "Lobby.Difficulty.Master", "達人"),
            NSLOCTEXT("SoraArena.Menu", "Lobby.Difficulty.Master.Hint", "ボットは隙を逃さない。")};
    default:
        return {NSLOCTEXT("SoraArena.Menu", "Lobby.Difficulty.Standard", "標準"),
            NSLOCTEXT("SoraArena.Menu", "Lobby.Difficulty.Standard.Hint", "ボットは狙い、守り、拠点を意識する。")};
    }
}
FText SettingsLabel() { return NSLOCTEXT("SoraArena.Menu", "Main.Settings", "設定"); }
FText SettingsHint()
{
    return NSLOCTEXT("SoraArena.Menu", "Main.Settings.Hint", "画質・音量・字幕・操作・アクセシビリティ。");
}
FText QuitLabel() { return NSLOCTEXT("SoraArena.Menu", "Main.Quit", "ゲームを終了"); }
}

ASoraGameMode& USoraFrontEnd::Mode() const { return *CastChecked<ASoraGameMode>(GetOuter()); }
bool USoraFrontEnd::ShowsEnglish() const { return Mode().bEnglishSubtitles; }

void USoraFrontEnd::ShowTitle()
{
    Stack = {{SoraUI::EScreen::Title, 0}};
    BannerJapanese.Empty(); BannerEnglish.Empty();
    Changed();
}
void USoraFrontEnd::ShowMain(const FString& InBannerJapanese, const FString& InBannerEnglish)
{
    Stack = {{SoraUI::EScreen::Main, 0}};
    BuildRows();
    Stack.Last().Focus = FirstEnabled();
    BannerJapanese = InBannerJapanese; BannerEnglish = InBannerEnglish;
    Changed();
}
void USoraFrontEnd::ShowPause()
{
    Stack = {{SoraUI::EScreen::Pause, 0}};
    BannerJapanese.Empty(); BannerEnglish.Empty();
    Changed();
}
void USoraFrontEnd::Hide()
{
    if (!IsOpen())
        return;
    Stack.Reset();
    BannerJapanese.Empty(); BannerEnglish.Empty();
    Changed();
}
SoraUI::EScreen USoraFrontEnd::Screen() const { return Stack.Num() ? Stack.Last().Screen : SoraUI::EScreen::Title; }
SoraUI::EScreen USoraFrontEnd::BaseScreen() const
{
    for (int32 Index = Stack.Num() - 1; Index >= 0; --Index)
        if (Stack[Index].Screen != SoraUI::EScreen::Confirm && Stack[Index].Screen != SoraUI::EScreen::Capture)
            return Stack[Index].Screen;
    return SoraUI::EScreen::Title;
}

void USoraFrontEnd::Push(SoraUI::EScreen Screen, int32 Focus)
{
    Stack.Add({Screen, 0});
    BuildRows();
    Stack.Last().Focus = RowList.IsValidIndex(Focus) && RowList[Focus].bEnabled ? Focus : FirstEnabled();
    BannerJapanese.Empty(); BannerEnglish.Empty();
    Changed();
}
void USoraFrontEnd::Pop()
{
    if (Stack.Num() < 2)
        return;
    Stack.Pop();
    BannerJapanese.Empty(); BannerEnglish.Empty();
    Changed();
}
void USoraFrontEnd::Confirm(SoraUI::EConfirm Kind, int32 Param)
{
    PendingConfirm = Kind;
    PendingParam = Param;
    // Rows are Yes then No; a destructive question starts on No.
    Push(SoraUI::EScreen::Confirm, 1);
}
void USoraFrontEnd::Changed()
{
    BuildRows();
    if (Stack.Num())
    {
        int32& Focus = Stack.Last().Focus;
        if (!RowList.IsValidIndex(Focus) || !RowList[Focus].bEnabled)
            Focus = FirstEnabled();
    }
    OnChanged.Broadcast();
}
int32 USoraFrontEnd::FirstEnabled() const
{
    for (int32 Index = 0; Index < RowList.Num(); ++Index)
        if (RowList[Index].bEnabled)
            return Index;
    return INDEX_NONE;
}
void USoraFrontEnd::MoveFocus(int32 Direction)
{
    if (!Stack.Num() || RowList.IsEmpty())
        return;
    int32& Focus = Stack.Last().Focus;
    // Wraps around the list and skips disabled rows.
    for (int32 Step = 1; Step <= RowList.Num(); ++Step)
    {
        const int32 Candidate = (FMath::Max(Focus, 0) + Direction * Step + RowList.Num() * Step) % RowList.Num();
        if (RowList[Candidate].bEnabled)
        {
            Focus = Candidate;
            break;
        }
    }
    Changed();
}
void USoraFrontEnd::NoteDevice(SoraUI::EDevice Device)
{
    if (Device == LastDevice)
        return;
    LastDevice = Device;
    OnChanged.Broadcast();
}

bool USoraFrontEnd::HandleKey(const FKey& Key, bool bRepeat)
{
    if (!IsOpen())
        return false;
    // A rebind takes the key itself, whatever its menu meaning.
    if (IsCapturing())
        return bRepeat || CaptureKey(Key);
    NoteDevice(SoraUI::DeviceForKey(Key));
    const SoraUI::ECommand Pressed = SoraUI::CommandForKey(Key);
    // The title waits for any key; Esc and F10 keep their own meaning there.
    if (Screen() == SoraUI::EScreen::Title && !bRepeat && Pressed != SoraUI::ECommand::Back && Pressed != SoraUI::ECommand::Subtitles)
        return Command(SoraUI::ECommand::Accept);
    const bool bMoves = Pressed == SoraUI::ECommand::Up || Pressed == SoraUI::ECommand::Down || Pressed == SoraUI::ECommand::Left || Pressed == SoraUI::ECommand::Right;
    if (bRepeat && !bMoves)
        return Pressed != SoraUI::ECommand::None;
    return Command(Pressed);
}
bool USoraFrontEnd::Command(SoraUI::ECommand Pressed)
{
    if (!IsOpen())
        return false;
    const SoraUI::EScreen Current = Screen();
    const int32 Focus = this->Focus();
    const SoraUI::FRow* Row = RowList.IsValidIndex(Focus) ? &RowList[Focus] : nullptr;
    switch (Pressed)
    {
    case SoraUI::ECommand::None:
        return false;
    case SoraUI::ECommand::Up:
    case SoraUI::ECommand::Down:
        if (Current == SoraUI::EScreen::Credits)
        {
            CreditsScroll = FMath::Clamp(CreditsScroll + (Pressed == SoraUI::ECommand::Up ? -3 : 3), 0, FMath::Max(CreditLines.Num() - 1, 0));
            Changed();
        }
        else
            MoveFocus(Pressed == SoraUI::ECommand::Up ? -1 : 1);
        return true;
    case SoraUI::ECommand::Left:
    case SoraUI::ECommand::Right:
        if (Row && Row->bOption && Row->bEnabled)
            Adjust(*Row, Pressed == SoraUI::ECommand::Left ? -1 : 1);
        return true;
    case SoraUI::ECommand::Accept:
        if (Current == SoraUI::EScreen::Title)
        {
            ShowMain();
            return true;
        }
        if (Row && Row->bEnabled)
            Activate(*Row);
        return true;
    case SoraUI::ECommand::Back:
        Back();
        return true;
    case SoraUI::ECommand::Start:
        // Start resumes from the pause menu and begins from the title.
        if (Current == SoraUI::EScreen::Pause)
        {
            Mode().ResumePlay();
            return true;
        }
        if (Current == SoraUI::EScreen::Title)
            return Command(SoraUI::ECommand::Accept);
        // The rebind dialog's clickable prompt cancels it.
        if (Current == SoraUI::EScreen::Capture)
        {
            Pop();
            return true;
        }
        return false;
    case SoraUI::ECommand::Subtitles:
        Mode().ToggleSubtitles();
        Changed();
        return true;
    }
    return false;
}
void USoraFrontEnd::Hover(int32 Index)
{
    NoteDevice(SoraUI::EDevice::KeyboardMouse);
    if (!Stack.Num() || !RowList.IsValidIndex(Index) || !RowList[Index].bEnabled || Stack.Last().Focus == Index)
        return;
    Stack.Last().Focus = Index;
    Changed();
}
void USoraFrontEnd::Click(int32 Index, SoraUI::ECommand Pressed)
{
    NoteDevice(SoraUI::EDevice::KeyboardMouse);
    if (!Stack.Num() || !RowList.IsValidIndex(Index) || !RowList[Index].bEnabled)
        return;
    Stack.Last().Focus = Index;
    Command(Pressed);
}

void USoraFrontEnd::Back()
{
    switch (Screen())
    {
    case SoraUI::EScreen::Title:
        return;
    case SoraUI::EScreen::Main:
        // The main menu under the title goes back to it.
        if (Stack.Num() == 1)
            ShowTitle();
        return;
    case SoraUI::EScreen::Pause:
        Mode().ResumePlay();
        return;
    case SoraUI::EScreen::Confirm:
        Resolve(false);
        return;
    default:
        Pop();
        return;
    }
}
void USoraFrontEnd::ReportFailure()
{
    if (!IsOpen())
        return;
    const ASoraGameMode& Game = Mode();
    const SoraText::FLine Failed = SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Banner.CouldNotStart", "開始できませんでした。"));
    BannerJapanese = Game.Notice.IsEmpty() ? Failed.Japanese : Game.Notice;
    BannerEnglish = Game.NoticeEnglish.IsEmpty() ? Failed.English : Game.NoticeEnglish;
    Changed();
}
void USoraFrontEnd::Resolve(bool bYes)
{
    const SoraUI::EConfirm Kind = PendingConfirm;
    const int32 Param = PendingParam;
    Pop();
    if (!bYes)
        return;
    ASoraGameMode& Game = Mode();
    switch (Kind)
    {
    case SoraUI::EConfirm::NewCampaign:
        Game.StartNewCampaign();
        if (IsOpen())
            ReportFailure();
        return;
    case SoraUI::EConfirm::Chapter:
        if (!Game.StartChapter(Param))
            ReportFailure();
        return;
    case SoraUI::EConfirm::Restart:
        if (!Game.RestartRound())
            ReportFailure();
        return;
    case SoraUI::EConfirm::ReturnToTitle:
        Game.ReturnToTitle();
        return;
    case SoraUI::EConfirm::Quit:
        Game.QuitGame();
        return;
    case SoraUI::EConfirm::ResetControls:
        if (ASoraPlayerCharacter* Hero = Game.Hero())
        {
            Hero->ResetControls();
            SetBanner(SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Banner.ControlsReset", "キー割り当てを既定に戻した。")));
            Changed();
        }
        return;
    }
}

void USoraFrontEnd::Activate(const SoraUI::FRow& Row)
{
    ASoraGameMode& Game = Mode();
    UArenaWalletSubsystem* Wallet = Game.GetGameInstance() ? Game.GetGameInstance()->GetSubsystem<UArenaWalletSubsystem>() : nullptr;
    switch (Row.Action)
    {
    case SoraUI::EAction::Continue:
        if (!Game.ContinueCampaign())
            ReportFailure();
        return;
    case SoraUI::EAction::NewCampaign:
        if (Game.CampaignHasProgress())
            Confirm(SoraUI::EConfirm::NewCampaign);
        else
        {
            Game.StartNewCampaign();
            if (IsOpen())
                ReportFailure();
        }
        return;
    case SoraUI::EAction::ChapterSelect:
        Push(SoraUI::EScreen::ChapterSelect, FMath::Min(Game.Campaign()->ChapterId, Game.HighestChapterReached()));
        return;
    case SoraUI::EAction::Practice:
        if (!bLobbyReady)
        {
            LobbySelection.ClassId = FMath::Clamp(Game.SelectedClass, 0, SoraPracticeLobby::ClassCount - 1);
            LobbySelection.MapId = FMath::Clamp(Game.MapId, 0, SoraPracticeLobby::MapCount - 1);
            bLobbyReady = true;
        }
        Push(SoraUI::EScreen::Practice);
        return;
    case SoraUI::EAction::Wallet:
        if (Wallet && !bWatchingWallet)
        {
            Wallet->OnStateChanged.AddDynamic(this, &USoraFrontEnd::WalletChanged);
            Wallet->OnTransactionStateChanged.AddDynamic(this, &USoraFrontEnd::WalletChanged);
            bWatchingWallet = true;
        }
        Push(SoraUI::EScreen::Wallet);
        return;
    case SoraUI::EAction::Settings:
        Push(SoraUI::EScreen::Settings);
        return;
    case SoraUI::EAction::Credits:
        if (!bCreditsLoaded)
        {
            CreditLines.Reset();
            CreditsLoadError = SoraText::FLine();
            SoraUI::LoadCredits(CreditLines, CreditsLoadError);
            bCreditsLoaded = true;
        }
        CreditsScroll = 0;
        Push(SoraUI::EScreen::Credits);
        return;
    case SoraUI::EAction::Quit:
        Confirm(SoraUI::EConfirm::Quit);
        return;
    case SoraUI::EAction::Resume:
        Game.ResumePlay();
        return;
    case SoraUI::EAction::Restart:
        Confirm(SoraUI::EConfirm::Restart);
        return;
    case SoraUI::EAction::ReturnToTitle:
        Confirm(SoraUI::EConfirm::ReturnToTitle);
        return;
    case SoraUI::EAction::Chapter:
        Confirm(SoraUI::EConfirm::Chapter, Row.Param);
        return;
    case SoraUI::EAction::LobbyStart:
        if (!Game.StartPracticeFromLobby(LobbySelection))
            ReportFailure();
        return;
    case SoraUI::EAction::WalletPair:
        if (Wallet && (Wallet->State == EArenaWalletState::Idle || Wallet->State == EArenaWalletState::Disconnected ||
            Wallet->State == EArenaWalletState::Unavailable || Wallet->State == EArenaWalletState::Error))
            Wallet->BeginPairingFromConfig();
        Changed();
        return;
    case SoraUI::EAction::WalletOpen:
        if (Wallet && Wallet->State == EArenaWalletState::AwaitingApproval)
            Wallet->LaunchWallet();
        Changed();
        return;
    case SoraUI::EAction::WalletDisconnect:
        if (Wallet)
            Wallet->DisconnectWallet();
        Changed();
        return;
    case SoraUI::EAction::ConfirmYes:
        Resolve(true);
        return;
    case SoraUI::EAction::ConfirmNo:
        Resolve(false);
        return;
    case SoraUI::EAction::Back:
        Back();
        return;
    default:
        if (ActivateSetting(Row))
            return;
        // Option rows step forward on Accept or a click.
        if (Row.bOption)
            Adjust(Row, 1);
        return;
    }
}

void USoraFrontEnd::Adjust(const SoraUI::FRow& Row, int32 Direction)
{
    using namespace SoraPracticeLobby;
    FSoraPracticeLobbySelection& L = LobbySelection;
    const auto Wrap = [Direction](int32 Value, int32 Count) { return (Value + Direction + Count) % Count; };
    // A changed mode or class keeps the player count and special weapon legal.
    const auto Settle = [&L]()
    {
        const int32 Min = MinPlayers(L.Mode), Step = PlayerStep(L.Mode);
        L.PlayerCount = FMath::Clamp(L.PlayerCount, Min, MaxPlayers(L.Mode));
        L.PlayerCount = FMath::Min(Min + (L.PlayerCount - Min + Step - 1) / Step * Step, MaxPlayers(L.Mode));
        const TArray<int32> Specials = SpecialOptions(L.Mode, L.ClassId);
        if (!Specials.Contains(L.SpecialWeaponId))
            L.SpecialWeaponId = INDEX_NONE;
    };
    switch (Row.Action)
    {
    case SoraUI::EAction::LobbyMode:
        L.Mode = Wrap(L.Mode, ModeCount);
        Settle();
        break;
    case SoraUI::EAction::LobbyMap:
        L.MapId = Wrap(L.MapId, MapCount);
        break;
    case SoraUI::EAction::LobbyClass:
    {
        // A chosen special follows the class to its own sidegrade.
        const bool bSpecial = L.SpecialWeaponId != INDEX_NONE;
        L.ClassId = Wrap(L.ClassId, ClassCount);
        const TArray<int32> Specials = SpecialOptions(L.Mode, L.ClassId);
        L.SpecialWeaponId = bSpecial && Specials.Num() > 1 ? Specials.Last() : INDEX_NONE;
        break;
    }
    case SoraUI::EAction::LobbySpecial:
    {
        const TArray<int32> Specials = SpecialOptions(L.Mode, L.ClassId);
        L.SpecialWeaponId = Specials[Wrap(FMath::Max(Specials.IndexOfByKey(L.SpecialWeaponId), 0), Specials.Num())];
        break;
    }
    case SoraUI::EAction::LobbyDifficulty:
        L.Difficulty = Wrap(L.Difficulty, DifficultyCount);
        break;
    case SoraUI::EAction::LobbyPlayers:
        L.PlayerCount = FMath::Clamp(L.PlayerCount + Direction * PlayerStep(L.Mode), MinPlayers(L.Mode), MaxPlayers(L.Mode));
        break;
    default:
        // The settings screens change their own values and redraw.
        AdjustSetting(Row, Direction);
        return;
    }
    Changed();
}

void USoraFrontEnd::WalletChanged()
{
    if (IsOpen() && Screen() == SoraUI::EScreen::Wallet)
        Changed();
}

SoraText::FLine USoraFrontEnd::TitleText() const
{
    switch (BaseScreen())
    {
    case SoraUI::EScreen::Title: return SoraText::Line(NSLOCTEXT("SoraArena", "MenuTitle", "猫柳生"));
    case SoraUI::EScreen::Main: return SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Screen.Main", "メインメニュー"));
    case SoraUI::EScreen::Pause: return SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Screen.Pause", "一時停止"));
    case SoraUI::EScreen::ChapterSelect: return SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Screen.ChapterSelect", "章を選ぶ"));
    case SoraUI::EScreen::Practice: return SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Screen.Practice", "武芸稽古"));
    case SoraUI::EScreen::Wallet: return SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Screen.Wallet", "IrohaConnect ウォレット"));
    case SoraUI::EScreen::Settings: return SoraText::Line(SettingsLabel());
    case SoraUI::EScreen::Credits: return SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Screen.Credits", "制作・権利表記"));
    case SoraUI::EScreen::Graphics: return SoraText::Line(NSLOCTEXT("SoraArena.Settings", "Screen.Graphics", "画質"));
    case SoraUI::EScreen::Audio: return SoraText::Line(NSLOCTEXT("SoraArena.Settings", "Screen.Audio", "音量"));
    case SoraUI::EScreen::Subtitles: return SoraText::Line(NSLOCTEXT("SoraArena.Settings", "Screen.Subtitles", "字幕と表示"));
    case SoraUI::EScreen::Controls: return SoraText::Line(NSLOCTEXT("SoraArena.Settings", "Screen.Controls", "操作"));
    case SoraUI::EScreen::Accessibility: return SoraText::Line(NSLOCTEXT("SoraArena.Settings", "Screen.Accessibility", "アクセシビリティ"));
    case SoraUI::EScreen::Confirm:
    case SoraUI::EScreen::Capture: break;
    }
    return SoraText::FLine();
}
SoraText::FLine USoraFrontEnd::ConfirmText() const
{
    const bool bPractice = Mode().bDeterministicPractice;
    if (IsCapturing())
    {
        const bool bPad = CaptureWith == SoraUI::EDevice::Gamepad;
        const SoraText::FLine Cancel = !CaptureRefusal.IsEmpty() ? CaptureRefusal : bPad
            ? SoraText::Line(NSLOCTEXT("SoraArena.Controls", "Capture.CancelPad", "Start でやめる。"))
            : SoraText::Line(NSLOCTEXT("SoraArena.Controls", "Capture.CancelKeyboard", "Esc でやめる。"));
        const SoraInput::FRemappable& Control = SoraInput::Remappable[CaptureIndex];
        return bPad
            ? SoraText::Format(NSLOCTEXT("SoraArena.Controls", "Capture.PromptPad", "「{Control}」の新しいボタンを押す。\n{Cancel}"),
                {{TEXT("Control"), SoraUI::ControlName(Control.Name, Control.Axis)}, {TEXT("Cancel"), Cancel}})
            : SoraText::Format(NSLOCTEXT("SoraArena.Controls", "Capture.PromptKeyboard", "「{Control}」の新しいキーかマウスボタンを押す。\n{Cancel}"),
                {{TEXT("Control"), SoraUI::ControlName(Control.Name, Control.Axis)}, {TEXT("Cancel"), Cancel}});
    }
    switch (PendingConfirm)
    {
    case SoraUI::EConfirm::NewCampaign:
        return SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Confirm.NewCampaign", "はじめからやり直しますか？\n保存した章・途中記録・到達した章をすべて消去します。"));
    case SoraUI::EConfirm::Chapter:
        return SoraText::Format(NSLOCTEXT("SoraArena.Menu", "Confirm.Chapter", "第{Chapter}章から始めますか？\n保存中の章と途中記録は、この章の始まりに置き換わります。到達した章はそのまま選べます。"),
            {{TEXT("Chapter"), PendingParam + 1}});
    case SoraUI::EConfirm::Restart:
        return bPractice
            ? SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Confirm.RestartPractice", "稽古をはじめからやり直しますか？\nこの稽古の記録は失われます。"))
            : SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Confirm.RestartCheckpoint", "チェックポイントからやり直しますか？\n最後のチェックポイント以降の進行は失われます。"));
    case SoraUI::EConfirm::ReturnToTitle:
        return bPractice
            ? SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Confirm.ReturnToTitlePractice", "タイトルへ戻りますか？\n稽古は終了します。"))
            : SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Confirm.ReturnToTitle", "タイトルへ戻りますか？\n最後のチェックポイント以降の進行は失われます。"));
    case SoraUI::EConfirm::Quit:
        return BaseScreen() == SoraUI::EScreen::Pause && !bPractice
            ? SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Confirm.QuitInPlay", "ゲームを終了しますか？\n最後のチェックポイント以降の進行は失われます。"))
            : SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Confirm.Quit", "ゲームを終了しますか？\n物語は最後のチェックポイントまで保存されています。"));
    case SoraUI::EConfirm::ResetControls:
        return SoraText::Line(NSLOCTEXT("SoraArena.Controls", "Confirm.ResetControls", "キー割り当てを既定に戻しますか？\n変えたキーとボタンはすべて元に戻ります。感度・遊び・上下反転はそのまま。"));
    }
    return SoraText::FLine();
}

void USoraFrontEnd::BuildRows()
{
    RowList.Reset();
    if (!IsOpen())
        return;
    ASoraGameMode& Game = Mode();
    const FSoraCatalog& Catalog = FSoraCatalog::Get();
    const bool bReady = Catalog.IsReady() && Game.Arena() != nullptr;
    switch (Screen())
    {
    case SoraUI::EScreen::Title:
        return;
    case SoraUI::EScreen::Main:
    {
        if (Game.CanContinueCampaign())
        {
            const int32 Chapter = Game.Campaign()->ChapterId;
            const FSoraChapter& Data = Catalog.Chapter(Chapter);
            SoraUI::FRow Row = NewMenuRow(SoraUI::EAction::Continue, NSLOCTEXT("SoraArena.Menu", "Main.Continue", "続きから"));
            Row.SetValue(SoraText::Format(NSLOCTEXT("SoraArena.Menu", "Main.Continue.Value", "第{Chapter}章"), {{TEXT("Chapter"), Chapter + 1}}));
            Row.SetHint(SoraText::Format(NSLOCTEXT("SoraArena.Menu", "Main.Continue.Hint", "第{Chapter}章「{Title}」の続きから。"),
                {{TEXT("Chapter"), Chapter + 1}, {TEXT("Title"), SoraText::FLine{Data.Title, Data.TitleEnglish}}}));
            Row.bEnabled = bReady;
            RowList.Add(Row);
        }
        RowList.Add(NewMenuRow(SoraUI::EAction::NewCampaign, NSLOCTEXT("SoraArena.Menu", "Main.NewCampaign", "新しい物語"),
            NSLOCTEXT("SoraArena.Menu", "Main.NewCampaign.Hint", "道場の稽古から、ニャーコトの物語をはじめる。")));
        RowList.Add(NewMenuRow(SoraUI::EAction::ChapterSelect, NSLOCTEXT("SoraArena.Menu", "Main.ChapterSelect", "章を選ぶ"),
            NSLOCTEXT("SoraArena.Menu", "Main.ChapterSelect.Hint", "到達した章から、はじめ直す。")));
        RowList.Add(NewMenuRow(SoraUI::EAction::Practice, NSLOCTEXT("SoraArena.Menu", "Main.Practice", "武芸稽古"),
            NSLOCTEXT("SoraArena.Menu", "Main.Practice.Hint", "形式・舞台・流儀を選び、ボットと稽古する。XOR は使わない。")));
        RowList.Add(NewMenuRow(SoraUI::EAction::Wallet, NSLOCTEXT("SoraArena.Menu", "Screen.Wallet", "IrohaConnect ウォレット"),
            NSLOCTEXT("SoraArena.Menu", "Main.Wallet.Hint", "ウォレットとの接続は、資産の預け入れではない。")));
        RowList.Add(NewMenuRow(SoraUI::EAction::Settings, SettingsLabel(), SettingsHint()));
        RowList.Add(NewMenuRow(SoraUI::EAction::Credits, NSLOCTEXT("SoraArena.Menu", "Main.Credits", "制作・権利表記"),
            NSLOCTEXT("SoraArena.Menu", "Main.Credits.Hint", "制作と、使用している素材の権利表記。")));
        RowList.Add(NewMenuRow(SoraUI::EAction::Quit, QuitLabel(),
            NSLOCTEXT("SoraArena.Menu", "Main.Quit.Hint", "物語は最後のチェックポイントまで保存されている。")));
        for (SoraUI::FRow& Row : RowList)
            if (Row.Action == SoraUI::EAction::NewCampaign || Row.Action == SoraUI::EAction::ChapterSelect || Row.Action == SoraUI::EAction::Practice)
                Row.bEnabled = bReady;
        return;
    }
    case SoraUI::EScreen::Pause:
    {
        const bool bPractice = Game.bDeterministicPractice;
        RowList.Add(NewMenuRow(SoraUI::EAction::Resume, NSLOCTEXT("SoraArena.Menu", "Pause.Resume", "再開")));
        RowList.Add(bPractice
            ? NewMenuRow(SoraUI::EAction::Restart, NSLOCTEXT("SoraArena.Menu", "Pause.RestartPractice", "稽古をやり直す"))
            : NewMenuRow(SoraUI::EAction::Restart, NSLOCTEXT("SoraArena.Menu", "Pause.RestartCheckpoint", "チェックポイントからやり直す")));
        RowList.Add(NewMenuRow(SoraUI::EAction::Settings, SettingsLabel(), SettingsHint()));
        RowList.Add(NewMenuRow(SoraUI::EAction::ReturnToTitle, NSLOCTEXT("SoraArena.Menu", "Pause.ReturnToTitle", "タイトルへ戻る")));
        RowList.Add(NewMenuRow(SoraUI::EAction::Quit, QuitLabel()));
        RowList[1].bEnabled = bReady;
        return;
    }
    case SoraUI::EScreen::ChapterSelect:
    {
        const int32 Highest = Game.HighestChapterReached();
        for (int32 Chapter = 0; Catalog.IsReady() && Chapter < Catalog.Chapters.Num(); ++Chapter)
        {
            SoraUI::FRow Row;
            Row.Action = SoraUI::EAction::Chapter;
            Row.Param = Chapter;
            if (Chapter <= Highest)
            {
                const FSoraChapter& Data = Catalog.Chapter(Chapter);
                Row.SetLabel(SoraText::Format(NSLOCTEXT("SoraArena.Menu", "Chapters.Reached", "第{Chapter}章　{Title}"),
                    {{TEXT("Chapter"), Chapter + 1}, {TEXT("Title"), SoraText::FLine{Data.Title, Data.TitleEnglish}}}));
                Row.SetHint({Data.Narrative, Data.NarrativeEnglish});
                Row.bEnabled = bReady;
            }
            else
            {
                Row.SetLabel(SoraText::Format(NSLOCTEXT("SoraArena.Menu", "Chapters.Locked", "第{Chapter}章　まだ到達していない"),
                    {{TEXT("Chapter"), Chapter + 1}}));
                Row.bEnabled = false;
            }
            RowList.Add(Row);
        }
        RowList.Add(NewBackRow());
        return;
    }
    case SoraUI::EScreen::Practice:
    {
        using namespace SoraPracticeLobby;
        const FSoraPracticeLobbySelection& L = LobbySelection;
        RowList.Add(NewChoiceRow(SoraUI::EAction::LobbyMode, NSLOCTEXT("SoraArena.Menu", "Lobby.Mode", "形式"), LobbyMode(L.Mode)));
        if (Catalog.IsReady())
        {
            const FSoraMap& Map = Catalog.Map(L.MapId);
            SoraUI::FRow MapRow = NewOptionRow(SoraUI::EAction::LobbyMap, NSLOCTEXT("SoraArena.Menu", "Lobby.Arena", "舞台"), {Map.Name, Map.NameEnglish});
            MapRow.SetHint(SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Lobby.Arena.Hint", "四つの闘技場から選ぶ。")));
            RowList.Add(MapRow);
            const FSoraClass& Class = Catalog.Class(L.ClassId);
            SoraUI::FRow ClassRow = NewOptionRow(SoraUI::EAction::LobbyClass, NSLOCTEXT("SoraArena.Menu", "Lobby.Class", "流儀"), {Class.Name, Class.NameEnglish});
            ClassRow.SetHint({Class.Role, Class.RoleEnglish});
            RowList.Add(ClassRow);
            const FText SpecialLabel = NSLOCTEXT("SoraArena.Menu", "Lobby.Special", "特殊武器");
            SoraUI::FRow SpecialRow;
            if (L.SpecialWeaponId == INDEX_NONE)
            {
                SpecialRow = NewOptionRow(SoraUI::EAction::LobbySpecial, SpecialLabel,
                    SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Lobby.Special.None", "なし（標準装備）")));
                SpecialRow.SetHint(SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Lobby.Special.None.Hint", "標準の武器だけで入場する。")));
            }
            else
            {
                const FSoraWeapon& Weapon = Catalog.Weapon(L.SpecialWeaponId);
                SpecialRow = NewOptionRow(SoraUI::EAction::LobbySpecial, SpecialLabel, {Weapon.Name, Weapon.NameEnglish});
                // The tradeoff first: Japanese from the interface, English from the catalog.
                const SoraText::FLine Hint = SoraText::Line(NSLOCTEXT("SoraArena.Menu", "Lobby.Special.Hint", "流儀の特殊武器を手に入場する。稽古では NFT も追加の預け入れもいらない。"));
                const FText Tradeoff = SoraUI::SpecialTradeoff(Weapon.Id);
                SpecialRow.SetHint({Tradeoff.IsEmpty() ? Hint.Japanese : Tradeoff.ToString() + Hint.Japanese,
                    Weapon.Tradeoff.IsEmpty() ? Hint.English : Weapon.Tradeoff + TEXT(" ") + Hint.English});
            }
            SpecialRow.bEnabled = SpecialOptions(L.Mode, L.ClassId).Num() > 1;
            RowList.Add(SpecialRow);
        }
        RowList.Add(NewChoiceRow(SoraUI::EAction::LobbyDifficulty, NSLOCTEXT("SoraArena.Menu", "Lobby.Difficulty", "難易度"), LobbyDifficulty(L.Difficulty)));
        SoraUI::FRow PlayersRow = NewOptionRow(SoraUI::EAction::LobbyPlayers, NSLOCTEXT("SoraArena.Menu", "Lobby.Players", "人数"),
            IsTeamMode(L.Mode)
                ? SoraText::Format(NSLOCTEXT("SoraArena.Menu", "Lobby.Players.Teams", "{Side}対{Side}"), {{TEXT("Side"), L.PlayerCount / 2}})
                : SoraText::Format(NSLOCTEXT("SoraArena.Menu", "Lobby.Players.Count", "{Count}匹"), {{TEXT("Count"), L.PlayerCount}}));
        PlayersRow.SetHint(SoraText::Format(NSLOCTEXT("SoraArena.Menu", "Lobby.Players.Hint", "あなたと {Bots} 匹のボット。"), {{TEXT("Bots"), L.PlayerCount - 1}}));
        RowList.Add(PlayersRow);
        SoraUI::FRow Start = NewMenuRow(SoraUI::EAction::LobbyStart, NSLOCTEXT("SoraArena.Menu", "Lobby.Start", "稽古をはじめる"),
            NSLOCTEXT("SoraArena.Menu", "Lobby.Start.Hint", "資産は預けず、報酬も発生しない。"));
        // Choices practice cannot apply yet are said here, before the player starts.
        if (const FText Limits = Game.PracticeLimits(); !Limits.IsEmpty())
        {
            const SoraText::FLine Note = SoraText::Line(Limits);
            Start.SetHint({Start.HintJapanese + Note.Japanese, Start.HintEnglish + TEXT(" ") + Note.English});
        }
        Start.bEnabled = bReady && SoraPracticeLobby::IsValid(L);
        RowList.Add(Start);
        RowList.Add(NewBackRow());
        return;
    }
    case SoraUI::EScreen::Wallet:
    {
        const UArenaWalletSubsystem* Wallet = Game.GetGameInstance() ? Game.GetGameInstance()->GetSubsystem<UArenaWalletSubsystem>() : nullptr;
        const EArenaWalletState State = Wallet ? Wallet->State : EArenaWalletState::Unavailable;
        SoraUI::FRow Pair = NewMenuRow(SoraUI::EAction::WalletPair, NSLOCTEXT("SoraArena.Wallet", "Pair", "接続を開始"),
            NSLOCTEXT("SoraArena.Wallet", "Pair.Hint", "QR コードかリンクで IrohaConnect ウォレットとつなぐ。"));
        Pair.bEnabled = Wallet && (State == EArenaWalletState::Idle || State == EArenaWalletState::Disconnected ||
            State == EArenaWalletState::Unavailable || State == EArenaWalletState::Error);
        SoraUI::FRow Open = NewMenuRow(SoraUI::EAction::WalletOpen, NSLOCTEXT("SoraArena.Wallet", "Open", "ウォレットを開く"),
            NSLOCTEXT("SoraArena.Wallet", "Open.Hint", "この端末のウォレットで接続を承認する。"));
        Open.bEnabled = Wallet && State == EArenaWalletState::AwaitingApproval;
        SoraUI::FRow Disconnect = NewMenuRow(SoraUI::EAction::WalletDisconnect, NSLOCTEXT("SoraArena.Wallet", "Disconnect", "接続を解除"),
            NSLOCTEXT("SoraArena.Wallet", "Disconnect.Hint", "ウォレットとの接続を終える。"));
        Disconnect.bEnabled = Wallet && State != EArenaWalletState::Idle && State != EArenaWalletState::Disconnected;
        RowList.Add(Pair);
        RowList.Add(Open);
        RowList.Add(Disconnect);
        RowList.Add(NewBackRow());
        return;
    }
    case SoraUI::EScreen::Settings:
    case SoraUI::EScreen::Graphics:
    case SoraUI::EScreen::Audio:
    case SoraUI::EScreen::Subtitles:
    case SoraUI::EScreen::Controls:
    case SoraUI::EScreen::Accessibility:
    case SoraUI::EScreen::Capture:
        BuildSettingsRows();
        return;
    case SoraUI::EScreen::Credits:
        RowList.Add(NewBackRow());
        return;
    case SoraUI::EScreen::Confirm:
    {
        FText Yes;
        switch (PendingConfirm)
        {
        case SoraUI::EConfirm::NewCampaign: Yes = NSLOCTEXT("SoraArena.Menu", "Confirm.NewCampaign.Yes", "消去してはじめる"); break;
        case SoraUI::EConfirm::Chapter: Yes = NSLOCTEXT("SoraArena.Menu", "Confirm.Chapter.Yes", "この章から始める"); break;
        case SoraUI::EConfirm::Restart: Yes = NSLOCTEXT("SoraArena.Menu", "Confirm.Restart.Yes", "やり直す"); break;
        case SoraUI::EConfirm::ReturnToTitle: Yes = NSLOCTEXT("SoraArena.Menu", "Pause.ReturnToTitle", "タイトルへ戻る"); break;
        case SoraUI::EConfirm::Quit: Yes = NSLOCTEXT("SoraArena.Menu", "Confirm.Quit.Yes", "終了する"); break;
        case SoraUI::EConfirm::ResetControls: Yes = NSLOCTEXT("SoraArena.Controls", "Confirm.ResetControls.Yes", "既定に戻す"); break;
        }
        RowList.Add(NewMenuRow(SoraUI::EAction::ConfirmYes, Yes));
        RowList.Add(NewMenuRow(SoraUI::EAction::ConfirmNo, NSLOCTEXT("SoraArena.Menu", "Cancel", "やめる")));
        return;
    }
    }
}
