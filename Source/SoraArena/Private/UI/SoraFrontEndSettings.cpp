#include "SoraFrontEnd.h"
#include "UI/SoraFrontEndRows.h"
#include "SoraGameMode.h"
#include "SoraInputStates.h"
#include "SoraPlayerCharacter.h"
#include "SoraSettings.h"

// The settings hub and its five screens (graphics, audio, subtitles,
// controls, accessibility) and the rebind dialog. Every value lives in
// USoraSettings, UGameUserSettings or the hero's control profile; these
// screens only read and step them.
namespace
{
using SoraUI::EAction;
using SoraUI::EScreen;
using SoraUI::FChoice;
using SoraUI::FRow;
using SoraUI::NewBackRow;
using SoraUI::NewChoiceRow;
using SoraUI::NewMenuRow;
using SoraUI::NewOptionRow;

FChoice PresetChoice(SoraGraphics::EPreset Preset)
{
    switch (Preset)
    {
    case SoraGraphics::EPreset::Mac:
        return {NSLOCTEXT("SoraArena.Settings", "Preset.Mac", "Mac"),
            NSLOCTEXT("SoraArena.Settings", "Preset.Mac.Hint", "ソフトウェア Lumen と通常の影。TSR が 75% から描き、60 fps を目指す。")};
    case SoraGraphics::EPreset::WindowsQuality:
        return {NSLOCTEXT("SoraArena.Settings", "Preset.WindowsQuality", "Windows 高画質"),
            NSLOCTEXT("SoraArena.Settings", "Preset.WindowsQuality.Hint", "すべて最高で MegaLights を使う。TSR が 67% から描き、60 fps を目指す。")};
    case SoraGraphics::EPreset::WindowsCompetitive:
        return {NSLOCTEXT("SoraArena.Settings", "Preset.WindowsCompetitive", "Windows 競技"),
            NSLOCTEXT("SoraArena.Settings", "Preset.WindowsCompetitive.Hint", "Lumen と視界は保ち、影・効果・後処理を抑える。上限なし、垂直同期なし。")};
    case SoraGraphics::EPreset::Custom:
        break;
    }
    return {NSLOCTEXT("SoraArena.Settings", "Preset.Custom", "カスタム"),
        NSLOCTEXT("SoraArena.Settings", "Preset.Custom.Hint", "項目を個別に変えている。左右でプリセットに戻る。")};
}
FChoice BusChoice(ESoraAudioBus Bus)
{
    switch (Bus)
    {
    case ESoraAudioBus::Music:
        return {NSLOCTEXT("SoraArena.Settings", "Bus.Music", "音楽"), NSLOCTEXT("SoraArena.Settings", "Bus.Music.Hint", "楽曲と戦いの音楽。")};
    case ESoraAudioBus::SFX:
        return {NSLOCTEXT("SoraArena.Settings", "Bus.SFX", "効果音"),
            NSLOCTEXT("SoraArena.Settings", "Bus.SFX.Hint", "武器・足音・爆発など。徴収官の予兆音は最小でも聞こえる。")};
    case ESoraAudioBus::Voice:
        return {NSLOCTEXT("SoraArena.Settings", "Bus.Voice", "声"), NSLOCTEXT("SoraArena.Settings", "Bus.Voice.Hint", "会話と掛け声。")};
    case ESoraAudioBus::UI:
        return {NSLOCTEXT("SoraArena.Settings", "Bus.UI", "メニューの音"), NSLOCTEXT("SoraArena.Settings", "Bus.UI.Hint", "メニューとウォレットの音。")};
    case ESoraAudioBus::Ambience:
        return {NSLOCTEXT("SoraArena.Settings", "Bus.Ambience", "環境音"), NSLOCTEXT("SoraArena.Settings", "Bus.Ambience.Hint", "雨・風・街のざわめき。")};
    case ESoraAudioBus::Master:
    case ESoraAudioBus::Count:
        break;
    }
    return {NSLOCTEXT("SoraArena.Settings", "Bus.Master", "全体の音量"), NSLOCTEXT("SoraArena.Settings", "Bus.Master.Hint", "すべての音の大きさ。")};
}
FChoice SubtitleSizeChoice(SoraAccessibility::ESubtitleSize Size)
{
    switch (Size)
    {
    case SoraAccessibility::ESubtitleSize::Large: return {NSLOCTEXT("SoraArena.Settings", "SubtitleSize.Large", "大"), FText::GetEmpty()};
    case SoraAccessibility::ESubtitleSize::ExtraLarge: return {NSLOCTEXT("SoraArena.Settings", "SubtitleSize.ExtraLarge", "特大"), FText::GetEmpty()};
    case SoraAccessibility::ESubtitleSize::Standard:
    case SoraAccessibility::ESubtitleSize::Count:
        break;
    }
    return {NSLOCTEXT("SoraArena.Settings", "SubtitleSize.Standard", "標準"), FText::GetEmpty()};
}
FChoice PaletteChoice(SoraAccessibility::EPalette Palette)
{
    switch (Palette)
    {
    case SoraAccessibility::EPalette::RedGreen:
        return {NSLOCTEXT("SoraArena.Settings", "Palette.RedGreen", "赤緑の色覚に配慮"),
            NSLOCTEXT("SoraArena.Settings", "Palette.RedGreen.Hint", "1型・2型色覚向け。斬撃と範囲は金、照準と光線は青。")};
    case SoraAccessibility::EPalette::BlueYellow:
        return {NSLOCTEXT("SoraArena.Settings", "Palette.BlueYellow", "青黄の色覚に配慮"),
            NSLOCTEXT("SoraArena.Settings", "Palette.BlueYellow.Hint", "3型色覚向け。斬撃と範囲は赤、照準と光線は青緑。")};
    case SoraAccessibility::EPalette::HighContrast:
        return {NSLOCTEXT("SoraArena.Settings", "Palette.HighContrast", "高コントラスト"),
            NSLOCTEXT("SoraArena.Settings", "Palette.HighContrast.Hint", "どの色覚でも見分けやすい。斬撃と範囲は赤、照準と光線は淡い水色。")};
    case SoraAccessibility::EPalette::Standard:
    case SoraAccessibility::EPalette::Count:
        break;
    }
    return {NSLOCTEXT("SoraArena.Settings", "Palette.Standard", "標準"),
        NSLOCTEXT("SoraArena.Settings", "Palette.Standard.Hint", "斬撃と範囲は琥珀、照準と光線は水色。")};
}
// The story bible's tiers; each rule is applied by the system that owns it.
FChoice DifficultyChoice(SoraAccessibility::EDifficulty Difficulty)
{
    switch (Difficulty)
    {
    case SoraAccessibility::EDifficulty::Easy:
        return {NSLOCTEXT("SoraArena.Settings", "Difficulty.Easy", "稽古"),
            NSLOCTEXT("SoraArena.Settings", "Difficulty.Easy.Hint", "予兆が三割長く、首領は打たれ弱い。潜入で見つかっても、やり直しではなく戦いになる。")};
    case SoraAccessibility::EDifficulty::Hard:
        return {NSLOCTEXT("SoraArena.Settings", "Difficulty.Hard", "免許皆伝"),
            NSLOCTEXT("SoraArena.Settings", "Difficulty.Hard.Hint", "予兆が一割五分短く、首領は打たれ強く、合わせの間も狭い。")};
    case SoraAccessibility::EDifficulty::Normal:
    case SoraAccessibility::EDifficulty::Count:
        break;
    }
    return {NSLOCTEXT("SoraArena.Settings", "Difficulty.Normal", "真剣"),
        NSLOCTEXT("SoraArena.Settings", "Difficulty.Normal.Hint", "本来の予兆と手応え。")};
}

FRow SwitchRow(EAction Action, const FText& Label, bool bOn, const FText& On, const FText& Off, const FText& Hint)
{
    FRow Row = NewOptionRow(Action, Label, SoraText::Line(bOn ? On : Off));
    Row.SetHint(SoraText::Line(Hint));
    return Row;
}
FText OnText() { return NSLOCTEXT("SoraArena.Settings", "On", "オン"); }
FText OffText() { return NSLOCTEXT("SoraArena.Settings", "Off", "オフ"); }
FText ShownText() { return NSLOCTEXT("SoraArena.Settings", "Shown", "表示"); }
FText HiddenText() { return NSLOCTEXT("SoraArena.Settings", "Hidden", "非表示"); }
FText ToggleText() { return NSLOCTEXT("SoraArena.Settings", "Toggle", "切り替え"); }
FText HoldText() { return NSLOCTEXT("SoraArena.Settings", "Hold", "長押し"); }
// Percentages and decimals read the same in both languages.
SoraText::FLine Percent(int32 Value) { return SoraText::Same(FString::Printf(TEXT("%d%%"), Value)); }
SoraText::FLine Decimal(float Value) { return SoraText::Same(FString::Printf(TEXT("%.2f"), Value)); }

// The next value from Values after Current in Direction; the nearest first
// when Current is not one of them. Choices wrap, sliders stop at their ends.
int32 StepValue(TArrayView<const int32> Values, int32 Current, int32 Direction, bool bWrap)
{
    int32 Index = Values.IndexOfByKey(Current);
    if (Index == INDEX_NONE)
    {
        Index = 0;
        for (int32 Candidate = 1; Candidate < Values.Num(); ++Candidate)
            if (FMath::Abs(Values[Candidate] - Current) < FMath::Abs(Values[Index] - Current))
                Index = Candidate;
        return Values[Index];
    }
    Index += Direction;
    Index = bWrap ? (Index + Values.Num()) % Values.Num() : FMath::Clamp(Index, 0, Values.Num() - 1);
    return Values[Index];
}
template <typename TEnum>
TEnum StepEnum(TEnum Value, int32 Count, int32 Direction)
{
    return static_cast<TEnum>((static_cast<int32>(Value) + Direction + Count) % Count);
}

FChoice WindowModeChoice(EWindowMode::Type Mode)
{
    switch (Mode)
    {
    case EWindowMode::Fullscreen:
        return {NSLOCTEXT("SoraArena.Settings", "Window.Fullscreen", "フルスクリーン"),
            NSLOCTEXT("SoraArena.Settings", "Window.Fullscreen.Hint", "画面を占有する。変更はすぐに反映される。")};
    case EWindowMode::WindowedFullscreen:
        return {NSLOCTEXT("SoraArena.Settings", "Window.Borderless", "ボーダーレス"),
            NSLOCTEXT("SoraArena.Settings", "Window.Borderless.Hint", "画面いっぱいの枠なしウィンドウ。変更はすぐに反映される。")};
    default:
        return {NSLOCTEXT("SoraArena.Settings", "Window.Windowed", "ウィンドウ"),
            NSLOCTEXT("SoraArena.Settings", "Window.Windowed.Hint", "枠つきのウィンドウ。変更はすぐに反映される。")};
    }
}
}

void USoraFrontEnd::BuildSettingsRows()
{
    ASoraGameMode& Game = Mode();
    USoraSettings* Settings = Game.Settings();
    const ASoraPlayerCharacter* Hero = Game.Hero();
    switch (Screen())
    {
    case EScreen::Settings:
        RowList.Add(NewMenuRow(EAction::OpenGraphics, NSLOCTEXT("SoraArena.Settings", "Screen.Graphics", "画質"),
            NSLOCTEXT("SoraArena.Settings", "Screen.Graphics.Hint", "プリセット・解像度スケール・フレームレート・表示モード。")));
        RowList.Add(NewMenuRow(EAction::OpenAudio, NSLOCTEXT("SoraArena.Settings", "Screen.Audio", "音量"),
            NSLOCTEXT("SoraArena.Settings", "Screen.Audio.Hint", "全体・音楽・効果音・声・メニュー・環境音の音量。")));
        RowList.Add(NewMenuRow(EAction::OpenSubtitles, NSLOCTEXT("SoraArena.Settings", "Screen.Subtitles", "字幕と表示"),
            NSLOCTEXT("SoraArena.Settings", "Screen.Subtitles.Hint", "英語字幕・字幕の大きさ・話者名・効果音の字幕。")));
        RowList.Add(NewMenuRow(EAction::OpenControls, NSLOCTEXT("SoraArena.Settings", "Screen.Controls", "操作"),
            NSLOCTEXT("SoraArena.Settings", "Screen.Controls.Hint", "キー割り当て・感度・スティックの遊び・上下反転。")));
        RowList.Add(NewMenuRow(EAction::OpenAccessibility, NSLOCTEXT("SoraArena.Settings", "Screen.Accessibility", "アクセシビリティ"),
            NSLOCTEXT("SoraArena.Settings", "Screen.Accessibility.Hint", "予兆の色・長押しと切り替え・難易度・点滅・画面の揺れ。")));
        RowList.Add(NewBackRow());
        return;
    case EScreen::Graphics:
    {
        RowList.Add(NewChoiceRow(EAction::GraphicsPreset, NSLOCTEXT("SoraArena.Settings", "Preset", "プリセット"), PresetChoice(Settings->GraphicsPreset())));
        FRow Scale = NewOptionRow(EAction::ResolutionScale, NSLOCTEXT("SoraArena.Settings", "ResolutionScale", "解像度スケール（TSR）"),
            Percent(Settings->ResolutionScale()));
        Scale.SetHint(SoraText::Line(NSLOCTEXT("SoraArena.Settings", "ResolutionScale.Hint", "TSR がこの割合で描き、画面の解像度へ高精細に戻す。")));
        RowList.Add(Scale);
        const int32 Limit = Settings->FrameRateLimit();
        FRow Cap = NewOptionRow(EAction::FrameRateLimit, NSLOCTEXT("SoraArena.Settings", "FrameRateLimit", "フレームレート上限"),
            Limit > 0 ? SoraText::Same(FString::Printf(TEXT("%d fps"), Limit)) : SoraText::Line(NSLOCTEXT("SoraArena.Settings", "FrameRateLimit.Uncapped", "無制限")));
        Cap.SetHint(SoraText::Line(NSLOCTEXT("SoraArena.Settings", "FrameRateLimit.Hint", "描く枚数の上限。")));
        RowList.Add(Cap);
        RowList.Add(SwitchRow(EAction::VSync, NSLOCTEXT("SoraArena.Settings", "VSync", "垂直同期"), Settings->VSync(), OnText(), OffText(),
            NSLOCTEXT("SoraArena.Settings", "VSync.Hint", "画面の書き換えに合わせ、画面の裂けを防ぐ。遅延が少し増える。")));
        RowList.Add(NewChoiceRow(EAction::WindowMode, NSLOCTEXT("SoraArena.Settings", "WindowMode", "表示モード"), WindowModeChoice(Settings->WindowMode())));
        RowList.Add(NewBackRow());
        return;
    }
    case EScreen::Audio:
        for (int32 Bus = 0; Bus < static_cast<int32>(ESoraAudioBus::Count); ++Bus)
        {
            const int32 Volume = Settings->BusVolume(static_cast<ESoraAudioBus>(Bus));
            const FChoice Choice = BusChoice(static_cast<ESoraAudioBus>(Bus));
            FRow Row = NewOptionRow(EAction::Volume, Choice.Label, Percent(Volume));
            Row.Param = Bus;
            Row.SetHint(SoraText::Line(Choice.Hint));
            RowList.Add(Row);
        }
        RowList.Add(NewBackRow());
        return;
    case EScreen::Subtitles:
        RowList.Add(SwitchRow(EAction::Subtitles, NSLOCTEXT("SoraArena.Settings", "EnglishSubtitles", "英語字幕"), Game.bEnglishSubtitles, ShownText(), HiddenText(),
            NSLOCTEXT("SoraArena.Settings", "EnglishSubtitles.Hint", "会話・物語・メニューの英語字幕。日本語は常に表示。F10 でも切り替え。")));
        RowList.Add(NewChoiceRow(EAction::SubtitleSize, NSLOCTEXT("SoraArena.Settings", "SubtitleSize", "字幕の大きさ"),
            SubtitleSizeChoice(Settings->SubtitleSize()),
            NSLOCTEXT("SoraArena.Settings", "SubtitleSize.Hint", "会話・物語・効果音の字幕の文字の大きさ。")));
        RowList.Add(SwitchRow(EAction::SpeakerNames, NSLOCTEXT("SoraArena.Settings", "SpeakerNames", "話者名"), Settings->SpeakerNames(), ShownText(), HiddenText(),
            NSLOCTEXT("SoraArena.Settings", "SpeakerNames.Hint", "会話の上に、話している者の名を出す。")));
        RowList.Add(SwitchRow(EAction::SoundCaptions, NSLOCTEXT("SoraArena.Settings", "SoundCaptions", "効果音の字幕"), Settings->SoundCaptions(), ShownText(), HiddenText(),
            NSLOCTEXT("SoraArena.Settings", "SoundCaptions.Hint", "銃声・刃の打ち合い・爆発・徴収官の予兆を、聞こえた方向とともに字幕で知らせる。")));
        RowList.Add(NewBackRow());
        return;
    case EScreen::Accessibility:
    {
        RowList.Add(NewChoiceRow(EAction::TelegraphPalette, NSLOCTEXT("SoraArena.Settings", "TelegraphPalette", "予兆の色"),
            PaletteChoice(Settings->TelegraphPalette())));
        RowList.Add(SwitchRow(EAction::ToggleGuard, NSLOCTEXT("SoraArena.Settings", "ToggleGuard", "構え"), Settings->ToggleGuard(), ToggleText(), HoldText(),
            NSLOCTEXT("SoraArena.Settings", "ToggleGuard.Hint", "切り替えでは、一度押すと構え、もう一度押すと解く。")));
        RowList.Add(SwitchRow(EAction::ToggleSprint, NSLOCTEXT("SoraArena.Settings", "ToggleSprint", "走る"), Settings->ToggleSprint(), ToggleText(), HoldText(),
            NSLOCTEXT("SoraArena.Settings", "ToggleSprint.Hint", "切り替えでは、もう一度押すか撃つと止まる。")));
        FRow Difficulty = NewChoiceRow(EAction::CampaignDifficulty, NSLOCTEXT("SoraArena.Settings", "CampaignDifficulty", "物語の難易度"),
            DifficultyChoice(Settings->CampaignDifficulty()));
        // The tier's rules, then that it leaves practice and matches alone.
        const SoraText::FLine Scope = SoraText::Line(NSLOCTEXT("SoraArena.Settings", "Difficulty.Scope", "武芸稽古と対戦には影響しない。"));
        Difficulty.SetHint({Difficulty.HintJapanese + Scope.Japanese, Difficulty.HintEnglish + TEXT(" ") + Scope.English});
        RowList.Add(Difficulty);
        RowList.Add(SwitchRow(EAction::AutoSteer, NSLOCTEXT("SoraArena.Settings", "AutoSteer", "騎乗の自動誘導"), Settings->AutoSteer(), OnText(), OffText(),
            NSLOCTEXT("SoraArena.Settings", "AutoSteer.Hint", "騎乗の場面で、馬が道筋をたどる。歩様と狙いは自分で操る。")));
        RowList.Add(SwitchRow(EAction::VolleyAutoOrder, NSLOCTEXT("SoraArena.Settings", "VolleyAutoOrder", "斉射の自動号令"), Settings->VolleyAutoOrder(),
            OnText(), OffText(),
            NSLOCTEXT("SoraArena.Settings", "VolleyAutoOrder.Hint", "稽古の難易度でのみ、込め終えた鉄砲組が一番近い敵へ自ら斉射する。")));
        RowList.Add(SwitchRow(EAction::ReduceFlashing, NSLOCTEXT("SoraArena.Settings", "ReduceFlashing", "点滅を抑える"), Settings->ReduceFlashing(), OnText(), OffText(),
            NSLOCTEXT("SoraArena.Settings", "ReduceFlashing.Hint", "被弾したときの赤い縁取りなど、画面の点滅を弱く穏やかにする。")));
        FRow Shake = NewOptionRow(EAction::CameraShake, NSLOCTEXT("SoraArena.Settings", "CameraShake", "画面の揺れ"), Percent(Settings->CameraShake()));
        Shake.SetHint(SoraText::Line(NSLOCTEXT("SoraArena.Settings", "CameraShake.Hint", "爆発や衝撃によるカメラの揺れの強さ。0% で揺れない。")));
        RowList.Add(Shake);
        RowList.Add(NewBackRow());
        return;
    }
    case EScreen::Controls:
    {
        const auto Stick = [&](EAction Action, const FText& Label, float Value, const FText& Hint)
        {
            FRow Row = NewOptionRow(Action, Label, Decimal(Value));
            Row.SetHint(SoraText::Line(Hint));
            Row.bEnabled = Hero != nullptr;
            RowList.Add(Row);
        };
        Stick(EAction::LookSensitivity, NSLOCTEXT("SoraArena.Controls", "LookSensitivity", "パッドの視点感度"), Hero ? Hero->GetGamepadLookSensitivity() : 1.f,
            NSLOCTEXT("SoraArena.Controls", "LookSensitivity.Hint", "右スティックで視点を回す速さ。"));
        Stick(EAction::MouseSensitivity, NSLOCTEXT("SoraArena.Controls", "MouseSensitivity", "マウス感度"), Hero ? Hero->GetMouseSensitivity() : 1.f,
            NSLOCTEXT("SoraArena.Controls", "MouseSensitivity.Hint", "マウスで視点を回す速さ。"));
        FRow Invert = SwitchRow(EAction::InvertLook, NSLOCTEXT("SoraArena.Controls", "InvertLook", "視点の上下反転"), Hero && Hero->GetInvertedLook(),
            NSLOCTEXT("SoraArena.Controls", "InvertLook.Inverted", "反転"), NSLOCTEXT("SoraArena.Controls", "InvertLook.Standard", "標準"),
            NSLOCTEXT("SoraArena.Controls", "InvertLook.Hint", "マウスと右スティックの上下を入れ替える。"));
        Invert.bEnabled = Hero != nullptr;
        RowList.Add(Invert);
        Stick(EAction::MoveDeadZone, NSLOCTEXT("SoraArena.Controls", "MoveDeadZone", "移動スティックの遊び"), Hero ? Hero->GetMoveDeadZone() : .18f,
            NSLOCTEXT("SoraArena.Controls", "MoveDeadZone.Hint", "左スティックが反応し始めるまでの遊び。スティックが勝手に動くなら大きくする。"));
        Stick(EAction::LookDeadZone, NSLOCTEXT("SoraArena.Controls", "LookDeadZone", "視点スティックの遊び"), Hero ? Hero->GetLookDeadZone() : .12f,
            NSLOCTEXT("SoraArena.Controls", "LookDeadZone.Hint", "右スティックが反応し始めるまでの遊び。"));
        FRow Heading = NewMenuRow(EAction::Heading, NSLOCTEXT("SoraArena.Controls", "Bindings", "キー割り当て"));
        Heading.bHeading = true;
        Heading.bEnabled = false;
        const SoraText::FLine KeyColumn = SoraText::Line(NSLOCTEXT("SoraArena.Controls", "Bindings.Keyboard", "キー・マウス"));
        const SoraText::FLine PadColumn = SoraText::Line(NSLOCTEXT("SoraArena.Controls", "Bindings.Pad", "パッド"));
        Heading.Keys[0] = KeyColumn.Japanese;
        Heading.Keys[1] = PadColumn.Japanese;
        Heading.KeysEnglish[0] = KeyColumn.English;
        Heading.KeysEnglish[1] = PadColumn.English;
        RowList.Add(Heading);
        const SoraText::FLine LeftStick = SoraText::Line(NSLOCTEXT("SoraArena.Controls", "LeftStick", "Lスティック"));
        for (int32 Index = 0; Index < SoraInput::RemappableCount; ++Index)
        {
            const SoraInput::FRemappable& Control = SoraInput::Remappable[Index];
            FRow Row;
            Row.Action = EAction::Binding;
            Row.Param = Index;
            Row.bBinding = true;
            Row.SetLabel(SoraUI::ControlName(Control.Name, Control.Axis));
            const SoraText::FLine Keyboard = SoraUI::KeyLabel(Hero ? Hero->ControlKey(Index, false) : EKeys::Invalid);
            const SoraText::FLine Pad = Control.Axis != 0 ? LeftStick : SoraUI::KeyLabel(Hero ? Hero->ControlKey(Index, true) : EKeys::Invalid);
            Row.Keys[0] = Keyboard.Japanese;
            Row.Keys[1] = Pad.Japanese;
            // The hint names the current keys in each language.
            Row.SetHint(Control.Axis != 0
                ? SoraText::Format(NSLOCTEXT("SoraArena.Controls", "Binding.Movement.Hint", "現在は {Keyboard}、パッドは {Pad}。キーボードのキーを割り当てる。パッドでは左スティックで動く。"),
                    {{TEXT("Keyboard"), Keyboard}, {TEXT("Pad"), Pad}})
                : SoraText::Format(NSLOCTEXT("SoraArena.Controls", "Binding.Hint", "現在は {Keyboard}、パッドは {Pad}。決定を押した機器（キーボード・マウスかパッド）で、次に押したキーやボタンを割り当てる。"),
                    {{TEXT("Keyboard"), Keyboard}, {TEXT("Pad"), Pad}}));
            Row.bEnabled = Hero != nullptr;
            RowList.Add(Row);
        }
        FRow Reset = NewMenuRow(EAction::ResetControls, NSLOCTEXT("SoraArena.Controls", "ResetControls", "既定のキーに戻す"),
            NSLOCTEXT("SoraArena.Controls", "ResetControls.Hint", "変えたキーとボタンをすべて元に戻す。"));
        Reset.bEnabled = Hero != nullptr;
        RowList.Add(Reset);
        RowList.Add(NewBackRow());
        return;
    }
    case EScreen::Capture:
        RowList.Add(NewMenuRow(EAction::CaptureCancel, NSLOCTEXT("SoraArena.Menu", "Cancel", "やめる")));
        return;
    default:
        return;
    }
}

bool USoraFrontEnd::ActivateSetting(const SoraUI::FRow& Row)
{
    switch (Row.Action)
    {
    case EAction::OpenGraphics: Push(EScreen::Graphics); return true;
    case EAction::OpenAudio: Push(EScreen::Audio); return true;
    case EAction::OpenSubtitles: Push(EScreen::Subtitles); return true;
    case EAction::OpenControls: Push(EScreen::Controls); return true;
    case EAction::OpenAccessibility: Push(EScreen::Accessibility); return true;
    case EAction::Binding: StartCapture(Row.Param); return true;
    case EAction::ResetControls: Confirm(SoraUI::EConfirm::ResetControls); return true;
    case EAction::CaptureCancel: Pop(); return true;
    default: return false;
    }
}

bool USoraFrontEnd::AdjustSetting(const SoraUI::FRow& Row, int32 Direction)
{
    ASoraGameMode& Game = Mode();
    USoraSettings& Settings = *Game.Settings();
    ASoraPlayerCharacter* Hero = Game.Hero();
    using namespace SoraAccessibility;
    switch (Row.Action)
    {
    case EAction::GraphicsPreset:
    {
        const TArray<SoraGraphics::EPreset> Presets = SoraGraphics::PlatformPresets();
        const int32 Index = Presets.IndexOfByKey(Settings.GraphicsPreset());
        const int32 Next = Index == INDEX_NONE ? (Direction > 0 ? 0 : Presets.Num() - 1) : (Index + Direction + Presets.Num()) % Presets.Num();
        Settings.SetGraphicsPreset(Presets[Next]);
        break;
    }
    case EAction::ResolutionScale:
        Settings.SetResolutionScale(StepValue(MakeArrayView(SoraGraphics::ResolutionScales), Settings.ResolutionScale(), Direction, false));
        break;
    case EAction::FrameRateLimit:
        Settings.SetFrameRateLimit(StepValue(MakeArrayView(SoraGraphics::FrameRateLimits), Settings.FrameRateLimit(), Direction, true));
        break;
    case EAction::VSync:
        Settings.SetVSync(!Settings.VSync());
        break;
    case EAction::WindowMode:
    {
        const TArray<EWindowMode::Type> Modes = SoraGraphics::PlatformWindowModes();
        const int32 Index = FMath::Max(Modes.IndexOfByKey(Settings.WindowMode()), 0);
        Settings.SetWindowMode(Modes[(Index + Direction + Modes.Num()) % Modes.Num()]);
        break;
    }
    case EAction::Volume:
    {
        const ESoraAudioBus Bus = static_cast<ESoraAudioBus>(Row.Param);
        Settings.SetBusVolume(Bus, Settings.BusVolume(Bus) + 5 * Direction);
        break;
    }
    case EAction::Subtitles:
        Game.ToggleSubtitles();
        break;
    case EAction::SubtitleSize:
        Settings.SetSubtitleSize(StepEnum(Settings.SubtitleSize(), static_cast<int32>(ESubtitleSize::Count), Direction));
        break;
    case EAction::SpeakerNames:
        Settings.SetSpeakerNames(!Settings.SpeakerNames());
        break;
    case EAction::SoundCaptions:
        Settings.SetSoundCaptions(!Settings.SoundCaptions());
        break;
    case EAction::TelegraphPalette:
        Settings.SetTelegraphPalette(StepEnum(Settings.TelegraphPalette(), static_cast<int32>(EPalette::Count), Direction));
        break;
    case EAction::ToggleGuard:
        Settings.SetToggleGuard(!Settings.ToggleGuard());
        break;
    case EAction::ToggleSprint:
        Settings.SetToggleSprint(!Settings.ToggleSprint());
        break;
    case EAction::CampaignDifficulty:
        Settings.SetCampaignDifficulty(StepEnum(Settings.CampaignDifficulty(), static_cast<int32>(EDifficulty::Count), Direction));
        break;
    case EAction::AutoSteer:
        Settings.SetAutoSteer(!Settings.AutoSteer());
        break;
    case EAction::VolleyAutoOrder:
        Settings.SetVolleyAutoOrder(!Settings.VolleyAutoOrder());
        break;
    case EAction::ReduceFlashing:
        Settings.SetReduceFlashing(!Settings.ReduceFlashing());
        break;
    case EAction::CameraShake:
        Settings.SetCameraShake(Settings.CameraShake() + 10 * Direction);
        break;
    case EAction::LookSensitivity:
        if (Hero)
            Hero->SetGamepadLookSensitivity(Hero->GetGamepadLookSensitivity() + .25f * Direction);
        break;
    case EAction::MouseSensitivity:
        if (Hero)
            Hero->SetMouseSensitivity(Hero->GetMouseSensitivity() + .25f * Direction);
        break;
    case EAction::InvertLook:
        if (Hero)
            Hero->SetInvertedLook(!Hero->GetInvertedLook());
        break;
    case EAction::MoveDeadZone:
    case EAction::LookDeadZone:
        if (Hero)
        {
            // Two-hundredths steps, kept exact.
            const auto Step = [Direction](float Value) { return FMath::RoundToFloat(Value * 50.f + Direction) / 50.f; };
            const bool bMove = Row.Action == EAction::MoveDeadZone;
            Hero->SetGamepadDeadZones(bMove ? Step(Hero->GetMoveDeadZone()) : Hero->GetMoveDeadZone(),
                bMove ? Hero->GetLookDeadZone() : Step(Hero->GetLookDeadZone()));
        }
        break;
    default:
        return false;
    }
    Changed();
    return true;
}

void USoraFrontEnd::StartCapture(int32 Index)
{
    if (Index < 0 || Index >= SoraInput::RemappableCount || !Mode().Hero())
        return;
    if (SoraInput::Remappable[Index].Axis != 0 && LastDevice == SoraUI::EDevice::Gamepad)
    {
        SetBanner(SoraText::Line(NSLOCTEXT("SoraArena.Controls", "Banner.MovementByKeyboard", "移動はキーボードで割り当てる。パッドでは左スティックで動く。")));
        Changed();
        return;
    }
    CaptureIndex = Index;
    CaptureWith = LastDevice;
    CaptureRefusal = SoraText::FLine();
    Push(EScreen::Capture);
}

bool USoraFrontEnd::CaptureKey(const FKey& Key)
{
    if (!IsCapturing() || CaptureIndex == INDEX_NONE)
        return false;
    // Esc and Start stay the menu's own keys, so they cancel.
    if (Key == EKeys::Escape || Key == EKeys::Gamepad_Special_Right)
    {
        Pop();
        return true;
    }
    const SoraInput::FRemappable& Control = SoraInput::Remappable[CaptureIndex];
    if (Key.IsGamepadKey() != (CaptureWith == SoraUI::EDevice::Gamepad))
    {
        CaptureRefusal = CaptureWith == SoraUI::EDevice::Gamepad
            ? SoraText::Line(NSLOCTEXT("SoraArena.Controls", "Capture.WantPad", "パッドのボタンを押してほしい。Start でやめる。"))
            : SoraText::Line(NSLOCTEXT("SoraArena.Controls", "Capture.WantKeyboard", "キーボードのキーかマウスのボタンを押してほしい。Esc でやめる。"));
        Changed();
        return true;
    }
    ASoraPlayerCharacter* Hero = Mode().Hero();
    FName TakenBy;
    int32 TakenAxis = 0;
    const SoraText::FLine KeyName = SoraUI::KeyLabel(Key);
    const FKey OldKey = Hero ? Hero->ControlKey(CaptureIndex, Key.IsGamepadKey()) : EKeys::Invalid;
    switch (Hero ? Hero->RemapControl(CaptureIndex, Key, &TakenBy, &TakenAxis) : ESoraRemapResult::NoControl)
    {
    case ESoraRemapResult::Done:
        Pop();
        SetBanner(SoraText::Format(NSLOCTEXT("SoraArena.Controls", "Banner.Rebound", "「{Control}」を {Key} にした。"),
            {{TEXT("Control"), SoraUI::ControlName(Control.Name, Control.Axis)}, {TEXT("Key"), KeyName}}));
        Changed();
        return true;
    case ESoraRemapResult::Swapped:
        Pop();
        SetBanner(SoraText::Format(NSLOCTEXT("SoraArena.Controls", "Banner.Swapped", "「{Control}」を {Key} にした。「{Other}」は {OldKey} に移った。"),
            {{TEXT("Control"), SoraUI::ControlName(Control.Name, Control.Axis)}, {TEXT("Key"), KeyName},
                {TEXT("Other"), SoraUI::ControlName(TakenBy, TakenAxis)}, {TEXT("OldKey"), SoraUI::KeyLabel(OldKey)}}));
        Changed();
        return true;
    case ESoraRemapResult::Taken:
        CaptureRefusal = SoraText::Format(NSLOCTEXT("SoraArena.Controls", "Capture.Taken", "{Key} は「{Control}」に使われている。先にそちらを変えるか、別のキーを押してほしい。"),
            {{TEXT("Key"), KeyName}, {TEXT("Control"), SoraUI::ControlName(TakenBy, TakenAxis)}});
        break;
    case ESoraRemapResult::WrongDevice:
        CaptureRefusal = SoraText::Line(NSLOCTEXT("SoraArena.Controls", "Capture.MovementKeyboardOnly", "移動にはキーボードのキーだけを割り当てられる。"));
        break;
    case ESoraRemapResult::Unbindable:
        CaptureRefusal = SoraText::Format(NSLOCTEXT("SoraArena.Controls", "Capture.Unbindable", "{Key} は割り当てられない。別のキーを押してほしい。"),
            {{TEXT("Key"), KeyName}});
        break;
    case ESoraRemapResult::NotInMenu:
    case ESoraRemapResult::NoControl:
        CaptureRefusal = SoraText::Line(NSLOCTEXT("SoraArena.Controls", "Capture.NotNow", "今は割り当てられない。"));
        break;
    }
    Changed();
    return true;
}
