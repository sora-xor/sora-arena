#pragma once
#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "SoraPracticeLobby.h"
#include "SoraText.h"
#include "SoraFrontEnd.generated.h"
class ASoraGameMode;
struct FKey;

namespace SoraUI
{
// Settings is the hub for the five settings screens. Confirm and Capture are
// dialogs over the screen beneath them.
enum class EScreen : uint8
{
    Title, Main, Pause, ChapterSelect, Practice, Wallet, Settings, Credits, Confirm,
    Graphics, Audio, Subtitles, Controls, Accessibility, Capture,
};
// What a key, click or wheel step asks of the open screen.
enum class ECommand : uint8 { None, Up, Down, Left, Right, Accept, Back, Start, Subtitles };
// The device the player last used; prompts and the mouse cursor follow it.
enum class EDevice : uint8 { KeyboardMouse, Gamepad };
enum class EAction : uint8
{
    Continue, NewCampaign, ChapterSelect, Practice, Wallet, Settings, Credits, Quit,
    Resume, Restart, ReturnToTitle, Chapter,
    LobbyMode, LobbyMap, LobbyClass, LobbySpecial, LobbyDifficulty, LobbyPlayers, LobbyStart,
    WalletPair, WalletOpen, WalletDisconnect,
    ConfirmYes, ConfirmNo, Back,
    // The settings hub's entries.
    OpenGraphics, OpenAudio, OpenSubtitles, OpenControls, OpenAccessibility,
    GraphicsPreset, ResolutionScale, FrameRateLimit, VSync, WindowMode,
    // Param is the ESoraAudioBus.
    Volume,
    Subtitles, SubtitleSize, SpeakerNames, SoundCaptions,
    TelegraphPalette, ToggleGuard, ToggleSprint, CampaignDifficulty, AutoSteer, ReduceFlashing, CameraShake,
    LookSensitivity, MouseSensitivity, InvertLook, MoveDeadZone, LookDeadZone,
    // Param is the SoraInput::Remappable entry.
    Binding, ResetControls, CaptureCancel,
    // A section heading; never focused.
    Heading,
};
enum class EConfirm : uint8 { NewCampaign, Chapter, Restart, ReturnToTitle, Quit, ResetControls };

// One selectable line. Option rows change their value with Left and Right.
struct FRow
{
    EAction Action = EAction::Back;
    int32 Param = 0;
    FString Japanese, English;
    FString ValueJapanese, ValueEnglish;
    // Shown beside the list while the row has focus.
    FString HintJapanese, HintEnglish;
    bool bEnabled = true;
    bool bOption = false;
    // A control's keys on the Controls screen: keyboard or mouse, then pad.
    // On the bindings heading they name the two columns.
    bool bBinding = false;
    bool bHeading = false;
    FString Keys[2];
    FString KeysEnglish[2];
    void SetLabel(const SoraText::FLine& Line) { Japanese = Line.Japanese; English = Line.English; }
    void SetValue(const SoraText::FLine& Line) { ValueJapanese = Line.Japanese; ValueEnglish = Line.English; }
    void SetHint(const SoraText::FLine& Line) { HintJapanese = Line.Japanese; HintEnglish = Line.English; }
};

// One line of the credits: our own, then each file in ThirdPartyNotices.
// Our own lines carry an English subtitle; the notices are shown as written.
struct FCreditLine
{
    enum EKind : uint8 { Heading, Entry, Text };
    EKind Kind = Text;
    FString Line;
    FString English;
};

// The key's menu meaning: arrows, WASD, the d-pad and the left stick move;
// Enter, Space and pad A accept; Esc, Backspace and pad B go back; the
// shoulders change an option like Left and Right; F10 toggles subtitles.
SORAARENA_API ECommand CommandForKey(const FKey& Key);
SORAARENA_API EDevice DeviceForKey(const FKey& Key);
// The label of the key that gives a command on a device ("Enter" or "A").
SORAARENA_API FString PromptKey(ECommand Command, EDevice Device);
// A key's short name for key caps: Japanese for mouse buttons, the d-pad and
// the sided modifiers, the printed name for other key caps and pad buttons,
// Unreal's names elsewhere; "—" for no key.
SORAARENA_API SoraText::FLine KeyLabel(const FKey& Key);
// The name of a rebindable control (SoraInput::Remappable) or of a fixed
// action another key belongs to, for the Controls screen and its refusals.
SORAARENA_API SoraText::FLine ControlName(FName Name, int32 Axis);
// The key the player now uses for an input action, labelled as KeyLabel does:
// the pad button while the player last used the pad, else the keyboard or
// mouse key, and the other device's key when that device has none. It reads
// the hero's live mappings, so prompts follow rebinding; before the hero is
// bound, DefaultInput.ini. Every in-game key prompt names its key through
// this.
SORAARENA_API SoraText::FLine ActionKey(const UObject* WorldContext, FName Action);
// A special weapon's tradeoff: Japanese here, and the catalog's own English
// tradeoff as its subtitle (SoraArena.UI.PracticeLobby checks they match).
// Empty for a weapon without one.
SORAARENA_API FText SpecialTradeoff(int32 WeaponId);
// The name of one of Nyaakoto's six groups of arms (SoraArmsRules::EGroup),
// or empty for another number.
SORAARENA_API FText ArmsGroupName(int32 Group);
// Reads ThirdPartyNotices/*.md and *.txt under the project directory.
SORAARENA_API bool LoadCredits(TArray<FCreditLine>& Out, SoraText::FLine& Error);
// Smallest Slate font sizes (points at the 1080p reference); the game
// viewport scales them to 0.666 at 720p.
constexpr float MinJapaneseFontSize = 24.f;
constexpr float MinEnglishFontSize = 21.f;
}

// The C++ Slate front end's state: the title screen, main and pause menus,
// chapter select, the practice lobby, the IrohaConnect wallet, settings,
// credits and confirmation dialogs, with the focused row, the practice
// lobby's choice and the last input device. ASoraGameMode owns it and keeps
// the world paused while any screen is open. ASoraHUD's SSoraFrontEnd draws
// it and forwards keys, clicks and the wheel here; automation drives the same
// entry points without a viewport.
UCLASS()
class SORAARENA_API USoraFrontEnd : public UObject
{
    GENERATED_BODY()
public:
    // Screen changes made by ASoraGameMode. They never call back into it.
    void ShowTitle();
    // The menu reached from the title, or opened by a director from play
    // with its notice as a banner (a finished campaign or a stopped practice).
    void ShowMain(const FString& BannerJapanese = FString(), const FString& BannerEnglish = FString());
    void ShowPause();
    void Hide();
    bool IsOpen() const { return Stack.Num() > 0; }
    SoraUI::EScreen Screen() const;
    // The screen under a confirmation dialog, or the screen itself.
    SoraUI::EScreen BaseScreen() const;
    // Opened from play over the paused round, rather than from the title.
    bool IsPauseContext() const { return Stack.Num() && Stack[0].Screen == SoraUI::EScreen::Pause; }
    // Menus follow the English subtitle setting; Japanese always shows.
    bool ShowsEnglish() const;
    ASoraGameMode& Mode() const;
    // A key press from the focused widget, or from automation. Repeats move
    // focus and change options but never accept or go back. Returns false for
    // a key without meaning on the open screen.
    bool HandleKey(const FKey& Key, bool bRepeat = false);
    bool Command(SoraUI::ECommand Command);
    // The mouse: moving over a row focuses it; a click on it acts like Accept,
    // or like Left or Right on an option row's arrows.
    void Hover(int32 Row);
    void Click(int32 Row, SoraUI::ECommand Command = SoraUI::ECommand::Accept);
    void NoteDevice(SoraUI::EDevice Device);
    SoraUI::EDevice Device() const { return LastDevice; }
    const TArray<SoraUI::FRow>& Rows() const { return RowList; }
    // A rebind in progress: the next key or button of CaptureDevice() goes to
    // the control; Esc or Start cancels. A key the control cannot take keeps
    // the dialog open with the reason.
    bool IsCapturing() const { return Screen() == SoraUI::EScreen::Capture; }
    bool CaptureKey(const FKey& Key);
    SoraUI::EDevice CaptureDevice() const { return CaptureWith; }
    int32 Focus() const { return Stack.Num() ? Stack.Last().Focus : INDEX_NONE; }
    // The open screen's heading, and the confirmation's question and warning.
    FString TitleJapanese() const { return TitleText().Japanese; }
    FString TitleEnglish() const { return TitleText().English; }
    FString ConfirmJapanese() const { return ConfirmText().Japanese; }
    FString ConfirmEnglish() const { return ConfirmText().English; }
    FString BannerJapanese, BannerEnglish;
    const FSoraPracticeLobbySelection& Lobby() const { return LobbySelection; }
    const TArray<SoraUI::FCreditLine>& Credits() const { return CreditLines; }
    const SoraText::FLine& CreditsError() const { return CreditsLoadError; }
    // Lines the credits list has scrolled past.
    int32 CreditsScroll = 0;
    // Broadcast after every change the view must redraw.
    FSimpleMulticastDelegate OnChanged;
private:
    struct FEntry
    {
        SoraUI::EScreen Screen;
        int32 Focus = 0;
    };
    TArray<FEntry> Stack;
    TArray<SoraUI::FRow> RowList;
    SoraUI::EDevice LastDevice = SoraUI::EDevice::KeyboardMouse;
    SoraUI::EConfirm PendingConfirm = SoraUI::EConfirm::Quit;
    int32 PendingParam = 0;
    FSoraPracticeLobbySelection LobbySelection;
    bool bLobbyReady = false;
    TArray<SoraUI::FCreditLine> CreditLines;
    SoraText::FLine CreditsLoadError;
    bool bCreditsLoaded = false;
    bool bWatchingWallet = false;
    int32 CaptureIndex = INDEX_NONE;
    SoraUI::EDevice CaptureWith = SoraUI::EDevice::KeyboardMouse;
    // Why the last key was refused, shown in the capture dialog.
    SoraText::FLine CaptureRefusal;

    SoraText::FLine TitleText() const;
    SoraText::FLine ConfirmText() const;
    void SetBanner(const SoraText::FLine& Line) { BannerJapanese = Line.Japanese; BannerEnglish = Line.English; }
    void Push(SoraUI::EScreen Screen, int32 Focus = INDEX_NONE);
    void Pop();
    void Confirm(SoraUI::EConfirm Kind, int32 Param = 0);
    void Changed();
    void BuildRows();
    int32 FirstEnabled() const;
    void MoveFocus(int32 Direction);
    void Activate(const SoraUI::FRow& Row);
    void Adjust(const SoraUI::FRow& Row, int32 Direction);
    void Back();
    void Resolve(bool bYes);
    // The settings screens, in SoraFrontEndSettings.cpp.
    void BuildSettingsRows();
    bool ActivateSetting(const SoraUI::FRow& Row);
    bool AdjustSetting(const SoraUI::FRow& Row, int32 Direction);
    void StartCapture(int32 Index);
    void ReportFailure();
    UFUNCTION() void WalletChanged();
};
