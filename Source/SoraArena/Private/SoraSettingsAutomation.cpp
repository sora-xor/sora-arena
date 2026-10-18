#include "SoraSettings.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "HUD/SoraHUDPanels.h"
#include "SoraCaptions.h"
#include "SoraCatalog.h"
#include "SoraControlSaveGame.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraHUD.h"
#include "SoraInputStates.h"
#include "SoraPlayerCharacter.h"
#include "SoraSettingsSaveGame.h"
#include "UI/SoraFrontEndTesting.h"
#include "EngineUtils.h"
#include "GameFramework/GameUserSettings.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "Scalability.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"

// Settings, controls and accessibility in standalone game worlds: values set
// through the menus with the pad survive a restart, both local saves write
// their schema, rebinding refuses conflicts and survives a restart, the
// graphics presets read back through Unreal's scalability, the telegraph
// palettes stay apart under simulated colour-vision deficiencies, guard and
// sprint hold or toggle, the campaign difficulty reaches the world without
// touching the damage the hero takes, and sound captions and the dialogue
// layout follow their settings. Worlds use isolated slots and detached settings, so the
// player's saves, the editor's graphics and GameUserSettings.ini are untouched.
namespace SoraSettingsTests
{
using namespace SoraFrontEndTests;
using SoraAccessibility::EDifficulty;
using SoraAccessibility::EPalette;
using SoraAccessibility::ESubtitleSize;
using SoraAccessibility::ETelegraph;

int32 Control(const TCHAR* Name, int32 Axis = 0) { return SoraInput::FindRemappable(Name, Axis); }

// From the title into live play: a fresh save starts the dojo, a seeded one continues.
bool EnterPlay(FScope& Scope)
{
    Scope.Key(EKeys::Enter);
    Scope.Key(EKeys::Enter);
    Scope.Key(EKeys::Enter);
    return Scope.Test.TestTrue(TEXT("The round is in play"), Scope.Mode()->IsPlaying());
}

// CIELAB from linear sRGB, D65.
FVector Lab(const FLinearColor& Color)
{
    const float R = FMath::Clamp(Color.R, 0.f, 1.f), G = FMath::Clamp(Color.G, 0.f, 1.f), B = FMath::Clamp(Color.B, 0.f, 1.f);
    const float X = (.4124f * R + .3576f * G + .1805f * B) / .95047f;
    const float Y = .2126f * R + .7152f * G + .0722f * B;
    const float Z = (.0193f * R + .1192f * G + .9505f * B) / 1.08883f;
    const auto F = [](float T) { return T > .008856f ? FMath::Pow(T, 1.f / 3.f) : 7.787f * T + 16.f / 116.f; };
    return FVector(116.f * F(Y) - 16.f, 500.f * (F(X) - F(Y)), 200.f * (F(Y) - F(Z)));
}

// Machado, Oliveira and Fernandes (2009) at full severity, on linear RGB.
enum class EVision : uint8 { Normal, Protan, Deutan, Tritan };
FLinearColor Simulate(const FLinearColor& Color, EVision Vision)
{
    static const float Matrices[4][3][3] = {
        {{1.f, 0.f, 0.f}, {0.f, 1.f, 0.f}, {0.f, 0.f, 1.f}},
        {{.152286f, 1.052583f, -.204868f}, {.114503f, .786281f, .099216f}, {-.003882f, -.048116f, 1.051998f}},
        {{.367322f, .860646f, -.227968f}, {.280085f, .672501f, .047413f}, {-.011820f, .042940f, .968881f}},
        {{1.255528f, -.076749f, -.178779f}, {-.078411f, .930809f, .147602f}, {.004733f, .691367f, .303900f}},
    };
    const float (&M)[3][3] = Matrices[static_cast<int32>(Vision)];
    const float In[3] = {Color.R, Color.G, Color.B};
    float Out[3];
    for (int32 Row = 0; Row < 3; ++Row)
        Out[Row] = FMath::Clamp(M[Row][0] * In[0] + M[Row][1] * In[1] + M[Row][2] * In[2], 0.f, 1.f);
    return FLinearColor(Out[0], Out[1], Out[2]);
}

// The smallest CIE76 distance between the palette's three telegraphs as seen with Vision.
float Separation(EPalette Palette, EVision Vision)
{
    float Smallest = TNumericLimits<float>::Max();
    for (int32 A = 0; A < static_cast<int32>(ETelegraph::Count); ++A)
        for (int32 B = A + 1; B < static_cast<int32>(ETelegraph::Count); ++B)
            Smallest = FMath::Min(Smallest, FVector::Dist(
                Lab(Simulate(SoraAccessibility::TelegraphColor(Palette, static_cast<ETelegraph>(A)), Vision)),
                Lab(Simulate(SoraAccessibility::TelegraphColor(Palette, static_cast<ETelegraph>(B)), Vision))));
    return Smallest;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraSettingsPersistTest,
    "SoraArena.UI.SettingsPersist",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraSettingsPersistTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraSettingsTests;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FScope Scope(*this, TEXT("SettingsPersist"));
    if (!Scope.Start())
        return false;
    USoraSettings* Settings = Scope.Mode()->Settings();
    TestFalse(TEXT("Automation settings stay detached from the engine"), Settings->IsAttached());
    TestTrue(TEXT("Detached graphics are not the engine's own"), &Settings->Graphics() != UGameUserSettings::GetGameUserSettings());
    TestEqual(TEXT("First launch applies the platform's preset"), Settings->GraphicsPreset(), SoraGraphics::PlatformPresets()[0]);
    const FString Slot = FSoraAutomationWorld::SettingsSlot(Scope.Slot);
    const USoraSettingsSaveGame* First = Cast<USoraSettingsSaveGame>(UGameplayStatics::LoadGameFromSlot(Slot, 0));
    TestTrue(TEXT("The first launch is recorded in the world's own settings slot"), First && First->GraphicsPresetApplied);
    bool bDefaultVolumes = true;
    for (int32 Bus = 0; Bus < static_cast<int32>(ESoraAudioBus::Count); ++Bus)
        bDefaultVolumes &= Settings->BusVolume(static_cast<ESoraAudioBus>(Bus)) == 100;
    TestTrue(TEXT("Defaults: full volume, English subtitles, standard size, speaker names, no captions"), bDefaultVolumes &&
        Settings->EnglishSubtitles() && Scope.Mode()->bEnglishSubtitles && Settings->SubtitleSize() == ESubtitleSize::Standard &&
        Settings->SpeakerNames() && !Settings->SoundCaptions());
    TestTrue(TEXT("Defaults: standard telegraphs, held guard and sprint, normal difficulty, no auto-steer, the volley auto-order, flashes and full shake"),
        Settings->TelegraphPalette() == EPalette::Standard && !Settings->ToggleGuard() && !Settings->ToggleSprint() &&
        Settings->CampaignDifficulty() == EDifficulty::Normal && !Settings->AutoSteer() && !Settings->HoldToCrank() && Settings->VolleyAutoOrder() &&
        !Settings->ReduceFlashing() && Settings->CameraShake() == 100);

    // Everything below with the pad alone.
    if (!TestTrue(TEXT("The pad opens Audio from the title"), Scope.OpenSettings(Pad, EAction::OpenAudio) && Scope.On(EScreen::Audio)))
        return false;
    TestEqual(TEXT("Audio lists the six buses and Back"), Scope.FrontEnd()->Rows().Num(), static_cast<int32>(ESoraAudioBus::Count) + 1);
    Scope.FocusOn(Pad, EAction::Volume, static_cast<int32>(ESoraAudioBus::Master));
    for (int32 Press = 0; Press < 4; ++Press)
        Scope.Key(Pad.Left);
    Scope.FocusOn(Pad, EAction::Volume, static_cast<int32>(ESoraAudioBus::Music));
    Scope.Key(Pad.Left);
    Scope.Key(Pad.Left);
    Scope.FocusOn(Pad, EAction::Volume, static_cast<int32>(ESoraAudioBus::UI));
    for (int32 Press = 0; Press < 22; ++Press)
        Scope.Key(Pad.Left);
    TestEqual(TEXT("The interface volume stops at zero"), Settings->BusVolume(ESoraAudioBus::UI), 0);
    Scope.Key(EKeys::Gamepad_RightShoulder);
    TestTrue(TEXT("Volumes step by five with the d-pad and the shoulders"), Settings->BusVolume(ESoraAudioBus::Master) == 80 &&
        Settings->BusVolume(ESoraAudioBus::Music) == 90 && Settings->BusVolume(ESoraAudioBus::UI) == 5);
    TestTrue(TEXT("Master gain follows a squared curve"), FMath::IsNearlyEqual(Settings->BusGain(ESoraAudioBus::Master), .64f, 1e-5f));
    Scope.Key(Pad.Back);

    Scope.Choose(Pad, EAction::OpenSubtitles);
    Scope.Key(Pad.Right);
    Scope.FocusOn(Pad, EAction::SubtitleSize);
    Scope.Key(Pad.Right);
    Scope.Key(Pad.Right);
    Scope.FocusOn(Pad, EAction::SpeakerNames);
    Scope.Key(Pad.Right);
    Scope.FocusOn(Pad, EAction::SoundCaptions);
    Scope.Key(Pad.Accept);
    TestTrue(TEXT("Subtitles: English off, extra large, no speaker names, sound captions on"), !Scope.Mode()->bEnglishSubtitles &&
        Settings->SubtitleSize() == ESubtitleSize::ExtraLarge && !Settings->SpeakerNames() && Settings->SoundCaptions());
    Scope.Key(Pad.Back);

    Scope.Choose(Pad, EAction::OpenAccessibility);
    Scope.Key(Pad.Right);
    Scope.FocusOn(Pad, EAction::ToggleGuard);
    Scope.Key(Pad.Right);
    Scope.FocusOn(Pad, EAction::ToggleSprint);
    Scope.Key(Pad.Right);
    Scope.FocusOn(Pad, EAction::CampaignDifficulty);
    TestTrue(TEXT("Normal is the bible's 真剣"), Scope.Focused()->ValueJapanese == TEXT("真剣") && Scope.Focused()->ValueEnglish == TEXT("Normal"));
    Scope.Key(Pad.Left);
    TestTrue(TEXT("Left steps to the bible's 稽古, Easy, with its longer telegraphs"), Scope.Focused()->ValueJapanese == TEXT("稽古") &&
        Scope.Focused()->ValueEnglish == TEXT("Easy") && Scope.Focused()->HintJapanese.Contains(TEXT("三割")));
    Scope.Key(Pad.Left);
    TestTrue(TEXT("Left wraps to the bible's 免許皆伝, Hard"), Scope.Focused()->ValueJapanese == TEXT("免許皆伝") && Scope.Focused()->ValueEnglish == TEXT("Hard"));
    Scope.Key(Pad.Right);
    Scope.FocusOn(Pad, EAction::AutoSteer);
    Scope.Key(Pad.Accept);
    Scope.FocusOn(Pad, EAction::HoldToCrank);
    Scope.Key(Pad.Accept);
    Scope.FocusOn(Pad, EAction::VolleyAutoOrder);
    Scope.Key(Pad.Accept);
    Scope.FocusOn(Pad, EAction::ReduceFlashing);
    Scope.Key(Pad.Right);
    Scope.FocusOn(Pad, EAction::CameraShake);
    for (int32 Press = 0; Press < 3; ++Press)
        Scope.Key(Pad.Left);
    TestTrue(TEXT("Accessibility: red-green telegraphs, toggled guard and sprint, easy, auto-steer, no volley auto-order, reduced flashing, 70% shake"),
        Settings->TelegraphPalette() == EPalette::RedGreen && Settings->ToggleGuard() && Settings->ToggleSprint() &&
        Settings->CampaignDifficulty() == EDifficulty::Easy && Settings->AutoSteer() && Settings->HoldToCrank() && !Settings->VolleyAutoOrder() &&
        Settings->ReduceFlashing() && Settings->CameraShake() == 70);
    Scope.Key(Pad.Back);
    Scope.Key(Pad.Back);
    Scope.Key(Pad.Back);
    TestTrue(TEXT("Back leads through the hub to the title"), Scope.On(EScreen::Title));

    if (!TestTrue(TEXT("The game restarts on the same slots"), Scope.Restart()))
        return false;
    Settings = Scope.Mode()->Settings();
    TestTrue(TEXT("Volumes survive the restart"), Settings->BusVolume(ESoraAudioBus::Master) == 80 &&
        Settings->BusVolume(ESoraAudioBus::Music) == 90 && Settings->BusVolume(ESoraAudioBus::UI) == 5 &&
        Settings->BusVolume(ESoraAudioBus::Voice) == 100);
    TestTrue(TEXT("Subtitle settings survive, and English stays off in the game mode"), !Settings->EnglishSubtitles() &&
        !Scope.Mode()->bEnglishSubtitles && Settings->SubtitleSize() == ESubtitleSize::ExtraLarge && !Settings->SpeakerNames() &&
        Settings->SoundCaptions());
    TestTrue(TEXT("Accessibility settings survive"), Settings->TelegraphPalette() == EPalette::RedGreen && Settings->ToggleGuard() &&
        Settings->ToggleSprint() && Settings->CampaignDifficulty() == EDifficulty::Easy && Settings->AutoSteer() && Settings->HoldToCrank() && !Settings->VolleyAutoOrder() &&
        Settings->ReduceFlashing() && Settings->CameraShake() == 70);
    Scope.Key(EKeys::F10);
    TestTrue(TEXT("F10 toggles English subtitles and saves them"), Scope.Mode()->bEnglishSubtitles && Settings->EnglishSubtitles());

    // A save out of range falls back field by field; another schema falls back entirely.
    USoraSettingsSaveGame* Broken = Cast<USoraSettingsSaveGame>(UGameplayStatics::LoadGameFromSlot(Slot, 0));
    if (!TestNotNull(TEXT("The settings save loads"), Broken))
        return false;
    Broken->SubtitleSize = 9;
    Broken->TelegraphPalette = -1;
    Broken->CameraShake = 250;
    Broken->CampaignDifficulty = 3;
    Broken->BusVolumes = {50, 50, 50};
    UGameplayStatics::SaveGameToSlot(Broken, Slot, 0);
    if (!Scope.Restart())
        return false;
    Settings = Scope.Mode()->Settings();
    TestTrue(TEXT("Out-of-range values fall back to their defaults and the rest stay"), Settings->SubtitleSize() == ESubtitleSize::Standard &&
        Settings->TelegraphPalette() == EPalette::Standard && Settings->CameraShake() == 100 && Settings->CampaignDifficulty() == EDifficulty::Normal &&
        Settings->BusVolume(ESoraAudioBus::Master) == 100 && Settings->ToggleGuard() && Settings->ReduceFlashing());
    Broken = Cast<USoraSettingsSaveGame>(UGameplayStatics::LoadGameFromSlot(Slot, 0));
    if (!TestNotNull(TEXT("The settings save loads again"), Broken))
        return false;
    Broken->SaveSchema = USoraSettingsSaveGame::Schema + 1;
    UGameplayStatics::SaveGameToSlot(Broken, Slot, 0);
    if (!Scope.Restart())
        return false;
    Settings = Scope.Mode()->Settings();
    return TestTrue(TEXT("A save of another schema is discarded for the defaults"), !Settings->ToggleGuard() && !Settings->ReduceFlashing() &&
        Settings->EnglishSubtitles() && Settings->CampaignDifficulty() == EDifficulty::Normal && !Settings->AutoSteer() && !Settings->HoldToCrank() &&
        Settings->VolleyAutoOrder());
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraSaveSchemaOnDiskTest,
    "SoraArena.UI.SaveSchemaOnDisk",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

// Unreal writes only the properties that differ from the class default. A
// schema number that defaulted to the current schema never reached disk, so
// every older file passed the schema check. Both local saves must write their
// schema, and a file without one must give way to the defaults.
bool FSoraSaveSchemaOnDiskTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraSettingsTests;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    const auto Names = [](const FString& Slot, const ANSICHAR* Property)
    {
        TArray<uint8> Data;
        if (!UGameplayStatics::LoadDataFromSlot(Data, Slot, 0))
            return false;
        const int32 Length = FCStringAnsi::Strlen(Property);
        for (int32 At = 0; At + Length <= Data.Num(); ++At)
            if (FMemory::Memcmp(Data.GetData() + At, Property, Length) == 0)
                return true;
        return false;
    };
    FScope Scope(*this, TEXT("SaveSchemaOnDisk"));
    if (!Scope.Start())
        return false;
    const FString SettingsSlot = FSoraAutomationWorld::SettingsSlot(Scope.Slot);
    const FString ControlSlot = FSoraAutomationWorld::ControlSlot(Scope.Slot);
    TestTrue(TEXT("The first launch writes the settings with their schema"), Names(SettingsSlot, "SaveSchema"));
    Scope.World->Player()->SetInvertedLook(true);
    TestTrue(TEXT("A changed control preference writes the profile with its schema"), Names(ControlSlot, "SaveSchema"));

    // Files as the earlier default left them: without a schema.
    USoraSettingsSaveGame* OldSettings = NewObject<USoraSettingsSaveGame>(GetTransientPackage());
    OldSettings->GraphicsPresetApplied = true;
    OldSettings->ToggleGuard = true;
    OldSettings->CampaignDifficulty = static_cast<int32>(EDifficulty::Hard);
    TStrongObjectPtr<USoraControlSaveGame> OldProfile(NewObject<USoraControlSaveGame>(GetTransientPackage()));
    FSoraControlBinding Jump;
    Jump.ActionName = TEXT("Jump");
    Jump.Key = EKeys::K;
    OldProfile->Bindings.Add(Jump);
    OldProfile->InvertedLook = true;
    if (!TestTrue(TEXT("Files without a schema are written"), UGameplayStatics::SaveGameToSlot(OldSettings, SettingsSlot, 0) &&
            UGameplayStatics::SaveGameToSlot(OldProfile.Get(), ControlSlot, 0)))
        return false;
    TestFalse(TEXT("An unstamped settings file carries no schema"), Names(SettingsSlot, "SaveSchema"));
    TestFalse(TEXT("An unstamped control file carries no schema"), Names(ControlSlot, "SaveSchema"));
    if (!Scope.Restart())
        return false;
    USoraSettings* Settings = Scope.Mode()->Settings();
    ASoraPlayerCharacter* Hero = Scope.World->Player();
    TestTrue(TEXT("Settings without a schema are discarded for the defaults"),
        !Settings->ToggleGuard() && Settings->CampaignDifficulty() == EDifficulty::Normal);
    return TestTrue(TEXT("A control profile without a schema is discarded for the defaults"),
        Hero->ControlKey(Control(TEXT("Jump")), false) == EKeys::SpaceBar && !Hero->GetInvertedLook());
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraControlsRemapTest,
    "SoraArena.UI.ControlsRemap",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraControlsRemapTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraSettingsTests;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    const int32 Fire = Control(TEXT("Fire")), Melee = Control(TEXT("Melee")), Jump = Control(TEXT("Jump")), Reload = Control(TEXT("Reload"));
    const int32 Crouch = Control(TEXT("Crouch"));
    const int32 Forward = Control(TEXT("MoveForward"), 1);
    FScope Scope(*this, TEXT("ControlsRemap"));
    if (!Scope.Start() || !TestTrue(TEXT("The keyboard opens Controls"), Scope.OpenSettings(Keyboard, EAction::OpenControls) && Scope.On(EScreen::Controls)))
        return false;
    ASoraPlayerCharacter* Hero = Scope.World->Player();
    USoraFrontEnd* FrontEnd = Scope.FrontEnd();
    const auto RowFor = [FrontEnd](int32 Index) { return FrontEnd->Rows().IndexOfByPredicate([Index](const SoraUI::FRow& Row)
        { return Row.bBinding && Row.Param == Index; }); };
    TestEqual(TEXT("Controls lists every rebindable control"), FrontEnd->Rows().FilterByPredicate([](const SoraUI::FRow& Row) { return Row.bBinding; }).Num(),
        SoraInput::RemappableCount);
    const SoraUI::FRow& FireRow = FrontEnd->Rows()[RowFor(Fire)];
    TestTrue(TEXT("Fire shows its mouse button and trigger"), FireRow.Keys[0] == TEXT("左クリック") && FireRow.Keys[1] == TEXT("RT"));

    // Keyboard: conflicts are refused with the reason, Esc cancels, a free key binds.
    Scope.FocusOn(Keyboard, EAction::Binding, Fire);
    Scope.Key(Keyboard.Accept);
    if (!TestTrue(TEXT("Enter on Fire opens a keyboard rebind"), FrontEnd->IsCapturing() && FrontEnd->CaptureDevice() == SoraUI::EDevice::KeyboardMouse))
        return false;
    Scope.Key(EKeys::R);
    TestTrue(TEXT("R is refused: it reloads"), FrontEnd->IsCapturing() && FrontEnd->ConfirmEnglish().Contains(TEXT("Reload")));
    Scope.Key(EKeys::W);
    TestTrue(TEXT("W is refused: it moves forward"), FrontEnd->IsCapturing() && FrontEnd->ConfirmEnglish().Contains(TEXT("Move forward")));
    Scope.Key(EKeys::F10);
    TestTrue(TEXT("F10 is refused: it switches subtitles in play"), FrontEnd->IsCapturing() && FrontEnd->ConfirmEnglish().Contains(TEXT("subtitle switch")));
    Scope.Key(EKeys::Gamepad_FaceButton_Bottom);
    TestTrue(TEXT("A pad button is refused for the keyboard slot"), FrontEnd->IsCapturing() && FrontEnd->ConfirmEnglish().Contains(TEXT("keyboard key or mouse button")));
    Scope.Key(EKeys::Escape);
    TestTrue(TEXT("Esc cancels and Fire keeps the left mouse button"), Scope.On(EScreen::Controls) && Hero->ControlKey(Fire, false) == EKeys::LeftMouseButton);
    Scope.Key(Keyboard.Accept);
    Scope.Key(EKeys::F);
    TestTrue(TEXT("F binds Fire, replacing the mouse button"), Scope.On(EScreen::Controls) && Hero->ControlKey(Fire, false) == EKeys::F &&
        !Hero->GetActionKeys(TEXT("Fire")).Contains(EKeys::LeftMouseButton) && Hero->ControlKey(Fire, true) == EKeys::Gamepad_RightTrigger);
    TestTrue(TEXT("The banner names the new key"), FrontEnd->BannerEnglish.Contains(TEXT("Fire or draw is now on F")));
    // The mouse: a click opens the rebind, the next button binds.
    FrontEnd->Click(RowFor(Melee));
    TestTrue(TEXT("A click on Melee opens a mouse-and-keyboard rebind"), FrontEnd->IsCapturing() && FrontEnd->CaptureDevice() == SoraUI::EDevice::KeyboardMouse);
    FrontEnd->CaptureKey(EKeys::MiddleMouseButton);
    TestEqual(TEXT("The wheel button binds Melee"), Hero->ControlKey(Melee, false), EKeys::MiddleMouseButton);
    // Movement halves take keyboard keys; the freed W is then free.
    Scope.FocusOn(Keyboard, EAction::Binding, Forward);
    Scope.Key(Keyboard.Accept);
    Scope.Key(EKeys::I);
    TestEqual(TEXT("I moves forward"), Hero->ControlKey(Forward, false), EKeys::I);
    Scope.Key(Pad.Accept);
    TestTrue(TEXT("The pad cannot rebind movement"), !FrontEnd->IsCapturing() && FrontEnd->BannerEnglish.Contains(TEXT("keyboard")));

    // Pad: a stick direction is refused. Every pad button has a default job,
    // so a button another control holds trades places with this one's; a
    // button shared across states that never overlap is allowed.
    Scope.FocusOn(Pad, EAction::Binding, Jump);
    Scope.Key(Pad.Accept);
    TestTrue(TEXT("A on Jump opens a pad rebind"), FrontEnd->IsCapturing() && FrontEnd->CaptureDevice() == SoraUI::EDevice::Gamepad);
    Scope.Key(EKeys::Gamepad_LeftStick_Up);
    TestTrue(TEXT("A stick direction is refused"), FrontEnd->IsCapturing() && FrontEnd->ConfirmEnglish().Contains(TEXT("cannot be bound")));
    Scope.Key(EKeys::Gamepad_RightThumbstick);
    TestTrue(TEXT("R3 trades places: Jump takes it and Crouch takes A"), !FrontEnd->IsCapturing() &&
        Hero->ControlKey(Jump, true) == EKeys::Gamepad_RightThumbstick && Hero->ControlKey(Crouch, true) == EKeys::Gamepad_FaceButton_Bottom &&
        FrontEnd->BannerEnglish.Contains(TEXT("Crouch moved to")));
    Scope.FocusOn(Pad, EAction::Binding, Reload);
    Scope.Key(Pad.Accept);
    Scope.Key(EKeys::Gamepad_FaceButton_Bottom);
    TestTrue(TEXT("A binds Reload while Enter keeps it on cards and results, and Crouch takes X"),
        Hero->ControlKey(Reload, true) == EKeys::Gamepad_FaceButton_Bottom && Hero->ControlKey(Crouch, true) == EKeys::Gamepad_FaceButton_Left &&
        Hero->GetActionKeys(TEXT("Enter")).Contains(EKeys::Gamepad_FaceButton_Bottom));
    TestFalse(TEXT("Menu, Enter and Subtitles are not rebindable"), Hero->RemapCombatAction(TEXT("Menu"), EKeys::K) ||
        Hero->RemapCombatAction(TEXT("Enter"), EKeys::K) || Hero->RemapCombatAction(TEXT("Subtitles"), EKeys::K));

    // Sensitivity, dead zones and inversion.
    Scope.FocusOn(Keyboard, EAction::MouseSensitivity);
    Scope.Key(Keyboard.Right);
    Scope.FocusOn(Keyboard, EAction::LookDeadZone);
    Scope.Key(Keyboard.Right);
    Scope.FocusOn(Keyboard, EAction::MoveDeadZone);
    Scope.Key(Keyboard.Left);
    Scope.FocusOn(Keyboard, EAction::InvertLook);
    Scope.Key(Keyboard.Right);
    TestTrue(TEXT("Mouse 1.25, look dead zone 0.14, move dead zone 0.16, inverted"), Hero->GetMouseSensitivity() == 1.25f &&
        FMath::IsNearlyEqual(Hero->GetLookDeadZone(), .14f) && FMath::IsNearlyEqual(Hero->GetMoveDeadZone(), .16f) && Hero->GetInvertedLook());

    if (!TestTrue(TEXT("The game restarts on the same slots"), Scope.Restart()))
        return false;
    Hero = Scope.World->Player();
    TestTrue(TEXT("Rebound keys survive the restart"), Hero->ControlKey(Fire, false) == EKeys::F && Hero->ControlKey(Melee, false) == EKeys::MiddleMouseButton &&
        Hero->ControlKey(Forward, false) == EKeys::I && Hero->ControlKey(Jump, true) == EKeys::Gamepad_RightThumbstick &&
        Hero->ControlKey(Reload, true) == EKeys::Gamepad_FaceButton_Bottom && Hero->ControlKey(Crouch, true) == EKeys::Gamepad_FaceButton_Left);
    const APlayerController* Controller = Cast<APlayerController>(Hero->GetController());
    FInputAxisProperties LeftStick;
    Controller->PlayerInput->GetAxisProperties(EKeys::Gamepad_LeftX, LeftStick);
    TestTrue(TEXT("Sensitivity, inversion and the applied dead zone survive"), Hero->GetMouseSensitivity() == 1.25f && Hero->GetInvertedLook() &&
        FMath::IsNearlyEqual(LeftStick.DeadZone, .16f));

    // In play the new keys act and the old ones do not.
    if (!EnterPlay(Scope))
        return false;
    Scope.World->InjectKey(EKeys::LeftMouseButton, IE_Pressed);
    Scope.World->Tick(1);
    TestFalse(TEXT("The left mouse button no longer fires"), Hero->GetEquipment()->IsTriggerHeld());
    Scope.World->InjectKey(EKeys::LeftMouseButton, IE_Released);
    Scope.World->InjectKey(EKeys::F, IE_Pressed);
    Scope.World->Tick(1);
    TestTrue(TEXT("F fires"), Hero->GetEquipment()->IsTriggerHeld());
    TestFalse(TEXT("Rebinding in play, outside a menu, is refused"), Hero->RemapCombatAction(TEXT("Jump"), EKeys::K));
    Scope.World->InjectKey(EKeys::F, IE_Released);
    Scope.World->Tick(30);
    const FVector Start = Hero->GetActorLocation();
    Scope.World->InjectKey(EKeys::I, IE_Pressed);
    Scope.World->Tick(30);
    Scope.World->InjectKey(EKeys::I, IE_Released);
    TestTrue(TEXT("I walks forward"), FVector::DotProduct(Hero->GetActorLocation() - Start, Hero->GetActorForwardVector()) > 20.f);

    // Reset from the pause menu, after its confirmation.
    Scope.Key(EKeys::Escape);
    Scope.Choose(Keyboard, EAction::Settings);
    Scope.Choose(Keyboard, EAction::OpenControls);
    Scope.Choose(Keyboard, EAction::ResetControls);
    TestTrue(TEXT("Reset asks first, starting on Cancel"), Scope.On(EScreen::Confirm) && Scope.Focused()->Action == EAction::ConfirmNo);
    Scope.Key(Keyboard.Up);
    Scope.Key(Keyboard.Accept);
    const USoraControlSaveGame* Saved = Cast<USoraControlSaveGame>(UGameplayStatics::LoadGameFromSlot(FSoraAutomationWorld::ControlSlot(Scope.Slot), 0));
    TestTrue(TEXT("Reset restores DefaultInput.ini and clears the saved bindings"), Hero->ControlKey(Fire, false) == EKeys::LeftMouseButton &&
        Hero->ControlKey(Forward, false) == EKeys::W && Hero->ControlKey(Jump, true) == EKeys::Gamepad_FaceButton_Bottom &&
        Hero->ControlKey(Reload, true) == EKeys::Gamepad_FaceButton_Left && Hero->ControlKey(Crouch, true) == EKeys::Gamepad_RightThumbstick &&
        Saved && Saved->Bindings.Num() == 0);
    TestTrue(TEXT("Reset keeps sensitivity and the dead zones"), Hero->GetMouseSensitivity() == 1.25f && FMath::IsNearlyEqual(Hero->GetMoveDeadZone(), .16f));

    // A saved swap made through a free button replays as a whole. The profile
    // outlives the restarts, which collect garbage.
    TStrongObjectPtr<USoraControlSaveGame> Profile(USoraControlSaveGame::New());
    FSoraControlBinding Swap;
    Swap.ActionName = TEXT("Interact");
    Swap.Key = EKeys::Gamepad_FaceButton_Left;
    Profile->Bindings.Add(Swap);
    Swap.ActionName = TEXT("Reload");
    Swap.Key = EKeys::Gamepad_FaceButton_Top;
    Profile->Bindings.Add(Swap);
    UGameplayStatics::SaveGameToSlot(Profile.Get(), FSoraAutomationWorld::ControlSlot(Scope.Slot), 0);
    if (!Scope.Restart())
        return false;
    Hero = Scope.World->Player();
    TestTrue(TEXT("Reload and Interact swapped buttons after the restart"), Hero->ControlKey(Reload, true) == EKeys::Gamepad_FaceButton_Top &&
        Hero->ControlKey(Control(TEXT("Interact")), true) == EKeys::Gamepad_FaceButton_Left);
    // A saved layout with a conflict is refused whole.
    Profile->Bindings.Reset();
    Swap.ActionName = TEXT("Fire");
    Swap.Key = EKeys::R;
    Profile->Bindings.Add(Swap);
    UGameplayStatics::SaveGameToSlot(Profile.Get(), FSoraAutomationWorld::ControlSlot(Scope.Slot), 0);
    AddExpectedMessagePlain(TEXT("has an unusable key layout; the default keys apply"), ELogVerbosity::Warning, EAutomationExpectedMessageFlags::Contains, 0);
    if (!Scope.Restart())
        return false;
    Hero = Scope.World->Player();
    return TestTrue(TEXT("A conflicting saved layout falls back to the defaults"), Hero->ControlKey(Fire, false) == EKeys::LeftMouseButton &&
        Hero->ControlKey(Reload, false) == EKeys::R);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraGraphicsPresetsTest,
    "SoraArena.UI.GraphicsPresets",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraGraphicsPresetsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraSettingsTests;
    using SoraGraphics::EPreset;
    // Each preset on a transient UGameUserSettings: its values, detected back,
    // and one changed level makes it Custom.
    for (const EPreset Id : {EPreset::Mac, EPreset::WindowsQuality, EPreset::WindowsCompetitive})
    {
        UGameUserSettings* Graphics = NewObject<UGameUserSettings>(GetTransientPackage());
        Graphics->SetToDefaults();
        SoraGraphics::Set(*Graphics, Id);
        const SoraGraphics::FPreset& P = SoraGraphics::Preset(Id);
        const FString Name = FString::Printf(TEXT("Preset %d"), static_cast<int32>(Id));
        TestTrue(*(Name + TEXT(" sets every level")), Graphics->GetViewDistanceQuality() == P.ViewDistance &&
            Graphics->GetAntiAliasingQuality() == P.AntiAliasing && Graphics->GetShadowQuality() == P.Shadow &&
            Graphics->GetGlobalIlluminationQuality() == P.GlobalIllumination && Graphics->GetReflectionQuality() == P.Reflection &&
            Graphics->GetPostProcessingQuality() == P.PostProcess && Graphics->GetTextureQuality() == P.Texture &&
            Graphics->GetVisualEffectQuality() == P.Effects && Graphics->GetFoliageQuality() == P.Foliage &&
            Graphics->GetShadingQuality() == P.Shading && Graphics->GetLandscapeQuality() == P.Landscape);
        TestTrue(*(Name + TEXT(" sets the TSR scale, frame cap and vsync")), SoraGraphics::ResolutionScale(*Graphics) == P.ResolutionScale &&
            FMath::RoundToInt(Graphics->GetFrameRateLimit()) == P.FrameRateLimit && Graphics->IsVSyncEnabled() == P.bVSync);
        TestEqual(*(Name + TEXT(" is detected")), SoraGraphics::Detect(*Graphics), Id);
        Graphics->SetShadowQuality(P.Shadow == 0 ? 1 : 0);
        TestEqual(*(Name + TEXT(" with one level changed is Custom")), SoraGraphics::Detect(*Graphics), EPreset::Custom);
    }
    // DefaultScalability.ini allows MegaLights only at shadow level 3.
    TestTrue(TEXT("Only Windows Quality reaches the MegaLights shadow tier"), SoraGraphics::Preset(EPreset::WindowsQuality).Shadow == 3 &&
        SoraGraphics::Preset(EPreset::Mac).Shadow < 3 && SoraGraphics::Preset(EPreset::WindowsCompetitive).Shadow < 3);
#if PLATFORM_MAC
    TestTrue(TEXT("macOS offers the Mac preset and no exclusive fullscreen"), SoraGraphics::PlatformPresets() == TArray<EPreset>({EPreset::Mac}) &&
        !SoraGraphics::PlatformWindowModes().Contains(EWindowMode::Fullscreen));
#else
    TestTrue(TEXT("Windows offers its quality and competitive presets"),
        SoraGraphics::PlatformPresets() == TArray<EPreset>({EPreset::WindowsQuality, EPreset::WindowsCompetitive}));
#endif

    // The scalability levels read back through Unreal's own scalability
    // state after a change, then the editor's levels are restored.
    const Scalability::FQualityLevels Before = Scalability::GetQualityLevels();
    for (const EPreset Id : {EPreset::Mac, EPreset::WindowsQuality})
    {
        UGameUserSettings* Probe = NewObject<UGameUserSettings>(GetTransientPackage());
        Probe->SetToDefaults();
        SoraGraphics::Set(*Probe, Id);
        Scalability::SetQualityLevels(Probe->ScalabilityQuality);
        const Scalability::FQualityLevels After = Scalability::GetQualityLevels();
        const SoraGraphics::FPreset& P = SoraGraphics::Preset(Id);
        TestTrue(*FString::Printf(TEXT("Preset %d reads back from the scalability state"), static_cast<int32>(Id)),
            After.ShadowQuality == P.Shadow && After.GlobalIlluminationQuality == P.GlobalIllumination && After.EffectsQuality == P.Effects &&
            After.PostProcessQuality == P.PostProcess && After.ViewDistanceQuality == P.ViewDistance &&
            FMath::RoundToInt(After.ResolutionQuality) == P.ResolutionScale);
    }
    Scalability::SetQualityLevels(Before);
    TestTrue(TEXT("The editor's scalability is restored"), Scalability::GetQualityLevels() == Before);

    // Through the Graphics screen, on the world's detached settings.
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FScope Scope(*this, TEXT("GraphicsScreen"));
    if (!Scope.Start() || !TestTrue(TEXT("The pad opens Graphics"), Scope.OpenSettings(Pad, EAction::OpenGraphics) && Scope.On(EScreen::Graphics)))
        return false;
    USoraSettings* Settings = Scope.Mode()->Settings();
    const EPreset Default = SoraGraphics::PlatformPresets()[0];
    const SoraGraphics::FPreset& P = SoraGraphics::Preset(Default);
    TestEqual(TEXT("The screen opens on the platform preset"), Settings->GraphicsPreset(), Default);
    Scope.FocusOn(Pad, EAction::ResolutionScale);
    Scope.Key(Pad.Right);
    TestTrue(TEXT("Right raises the TSR scale one step and the preset becomes Custom"), Settings->ResolutionScale() > P.ResolutionScale &&
        Settings->GraphicsPreset() == EPreset::Custom);
    Scope.FocusOn(Pad, EAction::GraphicsPreset);
    Scope.Key(Pad.Right);
    TestEqual(TEXT("Right on the preset returns to it"), Settings->GraphicsPreset(), Default);
    Scope.FocusOn(Pad, EAction::FrameRateLimit);
    Scope.Key(Pad.Left);
    const int32 Lower = Settings->FrameRateLimit();
    Scope.FocusOn(Pad, EAction::VSync);
    Scope.Key(Pad.Right);
    TestTrue(TEXT("The frame cap steps down and vsync switches"), Lower != P.FrameRateLimit && Settings->VSync() != P.bVSync);
    Scope.FocusOn(Pad, EAction::WindowMode);
    const EWindowMode::Type Mode = Settings->WindowMode();
    Scope.Key(Pad.Right);
    TestTrue(TEXT("The window mode steps to another offered mode"), Settings->WindowMode() != Mode &&
        SoraGraphics::PlatformWindowModes().Contains(Settings->WindowMode()));
    return TestTrue(TEXT("The engine's own graphics were not touched"), &Settings->Graphics() != UGameUserSettings::GetGameUserSettings());
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraTelegraphPaletteTest,
    "SoraArena.UI.TelegraphPalettes",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraTelegraphPaletteTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraSettingsTests;
    // The story bible's two kinds (section 8): amber for a cleave or an area
    // attack, cyan for a locked aim or a beam, as the collector prototype drew them.
    TestTrue(TEXT("Standard cleaves and areas are the prototype's amber, locked aims and beams its cyan"),
        SoraAccessibility::TelegraphColor(EPalette::Standard, ETelegraph::Cleave) == FLinearColor(1.f, .52f, .08f) &&
        SoraAccessibility::TelegraphColor(EPalette::Standard, ETelegraph::Lock) == FLinearColor(.04f, .85f, .95f));
    // The two kinds stay at least 60 CIELAB units apart for the vision each
    // palette serves (and normal vision); Standard and High contrast for all.
    struct FCase
    {
        EPalette Palette;
        TArray<EVision> Visions;
        const TCHAR* Name;
    };
    const TArray<EVision> Every = {EVision::Normal, EVision::Protan, EVision::Deutan, EVision::Tritan};
    const FCase Cases[] = {
        {EPalette::Standard, Every, TEXT("Standard")},
        {EPalette::RedGreen, {EVision::Normal, EVision::Protan, EVision::Deutan}, TEXT("Red-green safe")},
        {EPalette::BlueYellow, {EVision::Normal, EVision::Tritan}, TEXT("Blue-yellow safe")},
        {EPalette::HighContrast, Every, TEXT("High contrast")},
    };
    const TCHAR* const VisionNames[] = {TEXT("normal vision"), TEXT("protanopia"), TEXT("deuteranopia"), TEXT("tritanopia")};
    for (const FCase& Case : Cases)
        for (const EVision Vision : Case.Visions)
        {
            const float Distance = Separation(Case.Palette, Vision);
            TestTrue(*FString::Printf(TEXT("%s stays apart under %s (%.1f >= 60)"), Case.Name, VisionNames[static_cast<int32>(Vision)], Distance),
                Distance >= 60.f);
        }
    // In a world the colour follows the player's setting.
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FScope Scope(*this, TEXT("TelegraphPalette"));
    if (!Scope.Start())
        return false;
    UWorld* World = Scope.World->GetTestWorld();
    TestEqual(TEXT("A world starts on the standard palette"), SoraAccessibility::TelegraphColor(World, ETelegraph::Lock),
        SoraAccessibility::TelegraphColor(EPalette::Standard, ETelegraph::Lock));
    Scope.Mode()->Settings()->SetTelegraphPalette(EPalette::HighContrast);
    return TestEqual(TEXT("The chosen palette reaches telegraphs in the world"), SoraAccessibility::TelegraphColor(World, ETelegraph::Cleave),
        SoraAccessibility::TelegraphColor(EPalette::HighContrast, ETelegraph::Cleave));
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraKeyPromptsTest,
    "SoraArena.UI.KeyPrompts",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

// In-game prompts name the player's own key on the device in hand: the pad's
// button once the pad is used, the new key after a rebind, and
// DefaultInput.ini's keys before a hero is bound.
bool FSoraKeyPromptsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraSettingsTests;
    const auto Key = [](const UObject* Context, const TCHAR* Action) { return SoraUI::ActionKey(Context, Action).Japanese; };
    TestEqual(TEXT("Without a world, DefaultInput.ini's R reloads"), Key(nullptr, TEXT("Reload")), FString(TEXT("R")));
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FScope Scope(*this, TEXT("KeyPrompts"));
    if (!Scope.Start())
        return false;
    UWorld* World = Scope.World->GetTestWorld();
    TestTrue(TEXT("On the keyboard: R reloads, the left button fires, E examines, Enter continues, Esc pauses"),
        Key(World, TEXT("Reload")) == TEXT("R") && Key(World, TEXT("Fire")) == TEXT("左クリック") && Key(World, TEXT("Interact")) == TEXT("E") &&
        Key(World, TEXT("Enter")) == TEXT("Enter") && Key(World, TEXT("Menu")) == TEXT("Esc"));
    TestEqual(TEXT("A key's English subtitle comes with it"), SoraUI::ActionKey(World, TEXT("Fire")).English, FString(TEXT("Left click")));
    Scope.Key(EKeys::Gamepad_DPad_Down);
    TestTrue(TEXT("Once the pad is used: X reloads, RT fires, Y examines, A continues, Start pauses"),
        Key(World, TEXT("Reload")) == TEXT("X") && Key(World, TEXT("Fire")) == TEXT("RT") && Key(World, TEXT("Interact")) == TEXT("Y") &&
        Key(World, TEXT("Enter")) == TEXT("A") && Key(World, TEXT("Menu")) == TEXT("Start"));
    TestEqual(TEXT("A control without a pad button names its keyboard key"), Key(World, TEXT("WeaponFour")), FString(TEXT("4")));
    ASoraPlayerCharacter* Hero = Scope.World->Player();
    TestTrue(TEXT("Interact rebinds to G in the menu"), Hero->RemapCombatAction(TEXT("Interact"), EKeys::G));
    Scope.Key(EKeys::Down);
    return TestEqual(TEXT("Back on the keyboard, the examine prompt names the rebound G"), Key(World, TEXT("Interact")), FString(TEXT("G")));
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraHoldOrToggleTest,
    "SoraArena.Input.HoldOrToggle",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraHoldOrToggleTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraSettingsTests;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    {
        // The dojo, where the bokken guard is always available.
        FScope Scope(*this, TEXT("HoldOrToggle"));
        if (!Scope.Start() || !EnterPlay(Scope))
            return false;
        FSoraAutomationWorld& World = *Scope.World;
        ASoraPlayerCharacter* Hero = World.Player();
        USoraSettings* Settings = Scope.Mode()->Settings();
        const auto Tap = [&World](const FKey& Key)
        {
            World.InjectKey(Key, IE_Pressed);
            World.Tick(1);
            World.InjectKey(Key, IE_Released);
            World.Tick(1);
        };
        World.InjectKey(EKeys::LeftShift, IE_Pressed);
        World.Tick(1);
        TestTrue(TEXT("Hold: Shift sprints while held"), Hero->IsSprinting());
        World.InjectKey(EKeys::LeftShift, IE_Released);
        World.Tick(1);
        TestFalse(TEXT("Hold: releasing Shift stops"), Hero->IsSprinting());
        World.InjectKey(EKeys::LeftControl, IE_Pressed);
        World.Tick(1);
        TestTrue(TEXT("Hold: Ctrl guards while held"), Hero->IsGuarding());
        World.InjectKey(EKeys::LeftControl, IE_Released);
        World.Tick(1);
        TestFalse(TEXT("Hold: releasing Ctrl lowers the guard"), Hero->IsGuarding());

        Settings->SetToggleSprint(true);
        Settings->SetToggleGuard(true);
        Tap(EKeys::LeftShift);
        TestTrue(TEXT("Toggle: a tap of Shift keeps sprinting"), Hero->IsSprinting());
        Tap(EKeys::LeftShift);
        TestFalse(TEXT("Toggle: a second tap stops"), Hero->IsSprinting());
        Tap(EKeys::LeftControl);
        TestTrue(TEXT("Toggle: a tap of Ctrl keeps the guard up"), Hero->IsGuarding());
        World.Tick(30);
        TestTrue(TEXT("Toggle: the guard stays up untouched"), Hero->IsGuarding());
        Tap(EKeys::LeftControl);
        TestFalse(TEXT("Toggle: a second tap lowers it"), Hero->IsGuarding());
        Tap(EKeys::LeftControl);
        Scope.Key(EKeys::Escape);
        TestTrue(TEXT("The pause menu ends a toggled guard"), Scope.On(EScreen::Pause) && !Hero->IsGuarding());
        Scope.Key(EKeys::Escape);
        Tap(EKeys::LeftShift);
        TestTrue(TEXT("Toggle: sprinting again"), Hero->IsSprinting());
        World.InjectKey(EKeys::LeftMouseButton, IE_Pressed);
        World.Tick(1);
        World.InjectKey(EKeys::LeftMouseButton, IE_Released);
        TestFalse(TEXT("Toggle: firing ends the sprint"), Hero->IsSprinting());
    }
    // Campaign difficulty reaches the world for the systems that apply its
    // rules, and never scales the damage the hero takes: no design document
    // has that rule.
    FScope Scope(*this, TEXT("CampaignDifficulty"));
    if (!Scope.Seed(1, 1) || !Scope.Start() || !EnterPlay(Scope))
        return false;
    ASoraPlayerCharacter* Hero = Scope.World->Player();
    ASoraEnemy* Opponent = nullptr;
    for (TActorIterator<ASoraEnemy> It(Scope.World->GetTestWorld()); It && !Opponent; ++It)
        if (It->IsEnemy())
            Opponent = *It;
    if (!TestNotNull(TEXT("Chapter two has an opponent"), Opponent))
        return false;
    const auto Taken = [&](EDifficulty Difficulty)
    {
        Scope.Mode()->Settings()->SetCampaignDifficulty(Difficulty);
        Hero->Health = Hero->MaxHealth;
        UGameplayStatics::ApplyDamage(Hero, 10.f, nullptr, Opponent, UDamageType::StaticClass());
        return Hero->MaxHealth - Hero->Health;
    };
    const float Normal = Taken(EDifficulty::Normal), Easy = Taken(EDifficulty::Easy), Hard = Taken(EDifficulty::Hard);
    TestEqual(TEXT("The world reads the chosen tier"), SoraAccessibility::CampaignDifficulty(Scope.World->GetTestWorld()), EDifficulty::Hard);
    return TestTrue(*FString::Printf(TEXT("Easy, Normal and Hard deal the hero the same damage (%.1f, %.1f, %.1f)"), Easy, Normal, Hard),
        Normal > 0.f && Easy == Normal && Hard == Normal);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraSoundCaptionsTest,
    "SoraArena.UI.SoundCaptionsAndSubtitleLayout",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraSoundCaptionsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraSettingsTests;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FScope Scope(*this, TEXT("SoundCaptions"));
    if (!Scope.Start() || !EnterPlay(Scope))
        return false;
    UWorld* World = Scope.World->GetTestWorld();
    USoraCaptions* Captions = USoraCaptions::Get(World);
    USoraGameEvents* Events = USoraGameEvents::Get(World);
    ASoraPlayerCharacter* Hero = Scope.World->Player();
    if (!TestNotNull(TEXT("The world has sound captions"), Captions) || !TestNotNull(TEXT("The world has game events"), Events))
        return false;
    AActor* Other = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform(Hero->GetActorLocation() + FVector(0, 0, 0)));
    FSoraWeaponFiredEvent Shot;
    Shot.Shooter = Hero;
    Shot.Kind = ESoraShotKind::Hitscan;
    Events->OnWeaponFired.Broadcast(Shot);
    TestEqual(TEXT("The hero's own shot has no caption"), Captions->Live().Num(), 0);
    Shot.Shooter = Other;
    Shot.Origin = Hero->GetActorLocation() - Hero->GetActorForwardVector() * 800.f;
    Events->OnWeaponFired.Broadcast(Shot);
    Events->OnWeaponFired.Broadcast(Shot);
    TArray<FSoraCaption> Live = Captions->Live();
    TestTrue(TEXT("Another's gunfire is captioned once, counted twice, with its source"), Live.Num() == 1 && Live[0].English == TEXT("Gunfire") &&
        Live[0].Japanese == TEXT("銃声") && Live[0].Count == 2 && Live[0].bHasSource);
    FSoraDetonatedEvent Blast;
    Blast.Location = Hero->GetActorLocation();
    Events->OnDetonated.Broadcast(Blast);
    FSoraBossPhaseEvent Windup;
    Windup.Phase = ESoraBossPhase::Windup;
    Windup.bBeam = true;
    Events->OnBossPhase.Broadcast(Windup);
    FSoraDefenseEvent Parry;
    Parry.Defender = Hero;
    Events->OnParried.Broadcast(Parry);
    Shot.Kind = ESoraShotKind::Arrow;
    Events->OnWeaponFired.Broadcast(Shot);
    Live = Captions->Live();
    TestTrue(TEXT("Explosions, a collector's windup, clashing blades and arrows are captioned, four at most, oldest dropped"),
        Live.Num() == USoraCaptions::MaxLive && Live[0].English == TEXT("Explosion") && Live[1].English == TEXT("Collector charging its beam") &&
        Live[2].English == TEXT("Blades clash") && Live[3].English == TEXT("Arrow loosed"));
    Scope.World->Tick(5 * FramesPerSecond);
    TestEqual(TEXT("Captions fade after a few seconds of play"), Captions->Live().Num(), 0);

    // The dialogue panel at each subtitle size. At the standard size it is
    // the original panel at every resolution, including those where the
    // subtitle line heights hit their readable floors (S below 1).
    ASoraHUD* HUD = World->SpawnActor<ASoraHUD>();
    USoraSettings* Settings = Scope.Mode()->Settings();
    if (!TestNotNull(TEXT("A HUD spawns"), HUD))
        return false;
    const FVector2D Canvases[] = {{1600.f, 1000.f}, {1920.f, 1080.f}, {1280.f, 720.f}, {1024.f, 768.f}};
    const auto Near = [](float A, float B) { return FMath::IsNearlyEqual(A, B, .01f); };
    TArray<FSoraDialogueLayout> Standard;
    for (const FVector2D& Canvas : Canvases)
    {
        const FSoraHUDFrame Frame(*HUD, *Scope.Mode(), Canvas.X, Canvas.Y);
        const float S = FMath::Clamp(FMath::Min(Canvas.X / 1600.f, Canvas.Y / 1000.f), .45f, 1.5f);
        const FSoraDialogueLayout Layout = Frame.DialogueLayout(true);
        TestTrue(*FString::Printf(TEXT("At %.0fx%.0f the standard size keeps the original panel (top %.1f, height %.1f, lines %.1f/%.1f/%.1f)"),
                Canvas.X, Canvas.Y, Layout.Top, Layout.Height, Layout.SpeakerY, Layout.JapaneseY, Layout.EnglishY),
            Near(Frame.S, S) && Near(Layout.Top, Canvas.Y - 300.f * S) && Near(Layout.Height, 170.f * S) &&
            Near(Layout.SpeakerY, 10.f * S) && Near(Layout.JapaneseY, 40.f * S) && Near(Layout.EnglishY, 105.f * S));
        Standard.Add(Layout);
    }
    TestTrue(TEXT("At 1600x1000 the original panel sits at 700"), Standard[0].Top == 700.f && Standard[0].Height == 170.f);
    Settings->SetSubtitleSize(ESubtitleSize::ExtraLarge);
    for (int32 Index = 0; Index < UE_ARRAY_COUNT(Canvases); ++Index)
    {
        const FSoraHUDFrame Large(*HUD, *Scope.Mode(), Canvases[Index].X, Canvases[Index].Y);
        const FSoraDialogueLayout Big = Large.DialogueLayout(true), Old = Standard[Index];
        const FString Size = FString::Printf(TEXT("At %.0fx%.0f"), Canvases[Index].X, Canvases[Index].Y);
        TestTrue(*(Size + TEXT(" extra large text is half again as big")), FMath::IsNearlyEqual(Large.DialogueJapaneseScale, Large.JapaneseSubtitleScale * 1.5f) &&
            FMath::IsNearlyEqual(Large.DialogueEnglishLineHeight, Large.EnglishSubtitleLineHeight * 1.5f));
        TestTrue(*(Size + TEXT(" the extra large panel grows upwards from the same bottom edge")), Big.Top < Old.Top &&
            Near(Big.Top + Big.Height, Old.Top + Old.Height));
        // Each block gains at least what its lines grew, so the standard spacing holds.
        const float JapaneseGrowth = Large.DialogueJapaneseLineHeight - Large.JapaneseSubtitleLineHeight;
        const float EnglishGrowth = Large.DialogueEnglishLineHeight - Large.EnglishSubtitleLineHeight;
        TestTrue(*(Size + TEXT(" the speaker, Japanese and English blocks grow by their lines' growth")),
            (Big.JapaneseY - Big.SpeakerY) - (Old.JapaneseY - Old.SpeakerY) >= JapaneseGrowth - .01f &&
            (Big.EnglishY - Big.JapaneseY) - (Old.EnglishY - Old.JapaneseY) >= 2.f * JapaneseGrowth - .01f &&
            (Big.Height - Big.EnglishY) - (Old.Height - Old.EnglishY) >= 2.f * EnglishGrowth - .01f);
        if (Index == 0)
            TestTrue(TEXT("At 1600x1000 its two Japanese and two English lines never overlap"), Big.JapaneseY >= Big.SpeakerY + Large.DialogueJapaneseLineHeight &&
                Big.EnglishY >= Big.JapaneseY + 2.f * Large.DialogueJapaneseLineHeight && Big.Height >= Big.EnglishY + 2.f * Large.DialogueEnglishLineHeight);
    }
    Settings->SetSpeakerNames(false);
    Settings->SetReduceFlashing(true);
    Settings->SetSoundCaptions(true);
    const FSoraHUDFrame Plain(*HUD, *Scope.Mode(), 1600.f, 1000.f);
    return TestTrue(TEXT("Without speaker names the text starts at the top, and the frame follows the flashing and caption settings"),
        Plain.DialogueLayout(true).JapaneseY == Plain.DialogueLayout(true).SpeakerY && !Plain.bSpeakerNames && Plain.bReduceFlashing && Plain.bSoundCaptions);
}
#endif
