#include "SoraSettings.h"
#include "SoraGameMode.h"
#include "SoraSettingsSaveGame.h"
#include "AudioDevice.h"
#include "Camera/CameraShakeBase.h"
#include "Engine/Engine.h"
#include "GameFramework/GameUserSettings.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

namespace
{
// Levels: view distance, anti-aliasing (TSR quality), shadow, global
// illumination, reflection, post process, texture, effects, foliage, shading,
// landscape; then the TSR input scale, the frame cap and vsync. DefaultScalability.ini
// turns MegaLights on only at shadow level 3.
constexpr SoraGraphics::FPreset Presets[] = {
    {SoraGraphics::EPreset::Mac, 3, 3, 2, 2, 2, 2, 3, 2, 2, 2, 3, 75, 60, true},
    {SoraGraphics::EPreset::WindowsQuality, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 67, 60, true},
    {SoraGraphics::EPreset::WindowsCompetitive, 3, 2, 2, 2, 1, 1, 3, 1, 2, 2, 2, 75, 0, false},
};

// Linear colours. Standard's amber and cyan are the boss telegraphs' own;
// the others come from sRGB, chosen so each palette's two colours stay apart
// under the simulated deficiency it serves.
FLinearColor FromSRGB(uint8 R, uint8 G, uint8 B) { return FLinearColor::FromSRGBColor(FColor(R, G, B)); }
}

const SoraGraphics::FPreset& SoraGraphics::Preset(EPreset Id)
{
    for (const FPreset& Entry : Presets)
        if (Entry.Id == Id)
            return Entry;
    return Presets[0];
}

TArray<SoraGraphics::EPreset> SoraGraphics::PlatformPresets()
{
#if PLATFORM_MAC
    return {EPreset::Mac};
#else
    return {EPreset::WindowsQuality, EPreset::WindowsCompetitive};
#endif
}

TArray<EWindowMode::Type> SoraGraphics::PlatformWindowModes()
{
#if PLATFORM_MAC
    return {EWindowMode::WindowedFullscreen, EWindowMode::Windowed};
#else
    return {EWindowMode::Fullscreen, EWindowMode::WindowedFullscreen, EWindowMode::Windowed};
#endif
}

void SoraGraphics::Set(UGameUserSettings& Settings, EPreset Id)
{
    if (Id == EPreset::Custom)
        return;
    const FPreset& P = Preset(Id);
    Settings.SetViewDistanceQuality(P.ViewDistance);
    Settings.SetAntiAliasingQuality(P.AntiAliasing);
    Settings.SetShadowQuality(P.Shadow);
    Settings.SetGlobalIlluminationQuality(P.GlobalIllumination);
    Settings.SetReflectionQuality(P.Reflection);
    Settings.SetPostProcessingQuality(P.PostProcess);
    Settings.SetTextureQuality(P.Texture);
    Settings.SetVisualEffectQuality(P.Effects);
    Settings.SetFoliageQuality(P.Foliage);
    Settings.SetShadingQuality(P.Shading);
    Settings.SetLandscapeQuality(P.Landscape);
    Settings.SetResolutionScaleValueEx(P.ResolutionScale);
    Settings.SetFrameRateLimit(P.FrameRateLimit);
    Settings.SetVSyncEnabled(P.bVSync);
}

int32 SoraGraphics::ResolutionScale(const UGameUserSettings& Settings)
{
    float Normalized = 0.f, Value = 100.f, Min = 0.f, Max = 100.f;
    Settings.GetResolutionScaleInformationEx(Normalized, Value, Min, Max);
    return FMath::RoundToInt(Value);
}

SoraGraphics::EPreset SoraGraphics::Detect(const UGameUserSettings& Settings)
{
    for (const FPreset& P : Presets)
        if (Settings.GetViewDistanceQuality() == P.ViewDistance && Settings.GetAntiAliasingQuality() == P.AntiAliasing &&
            Settings.GetShadowQuality() == P.Shadow && Settings.GetGlobalIlluminationQuality() == P.GlobalIllumination &&
            Settings.GetReflectionQuality() == P.Reflection && Settings.GetPostProcessingQuality() == P.PostProcess &&
            Settings.GetTextureQuality() == P.Texture && Settings.GetVisualEffectQuality() == P.Effects &&
            Settings.GetFoliageQuality() == P.Foliage && Settings.GetShadingQuality() == P.Shading &&
            Settings.GetLandscapeQuality() == P.Landscape && ResolutionScale(Settings) == P.ResolutionScale &&
            FMath::RoundToInt(Settings.GetFrameRateLimit()) == P.FrameRateLimit && Settings.IsVSyncEnabled() == P.bVSync)
            return P.Id;
    return EPreset::Custom;
}

FLinearColor SoraAccessibility::TelegraphColor(EPalette Palette, ETelegraph Kind)
{
    const int32 K = FMath::Clamp(static_cast<int32>(Kind), 0, static_cast<int32>(ETelegraph::Count) - 1);
    switch (Palette)
    {
    case EPalette::RedGreen:
    {
        // Gold and blue: the yellow-blue axis protanopia and deuteranopia keep.
        const FLinearColor Colors[] = {FromSRGB(0xFF, 0xC0, 0x00), FromSRGB(0x40, 0x60, 0xFF)};
        return Colors[K];
    }
    case EPalette::BlueYellow:
    {
        // Red and teal: the red-cyan axis tritanopia keeps.
        const FLinearColor Colors[] = {FromSRGB(0xFF, 0x30, 0x30), FromSRGB(0x00, 0xE0, 0xA0)};
        return Colors[K];
    }
    case EPalette::HighContrast:
    {
        // Red and pale cyan: apart in hue and lightness under every simulated deficiency.
        const FLinearColor Colors[] = {FromSRGB(0xFF, 0x20, 0x20), FromSRGB(0xB0, 0xFF, 0xFF)};
        return Colors[K];
    }
    case EPalette::Standard:
    case EPalette::Count:
        break;
    }
    // The collector prototype's amber cleave and cyan beam.
    const FLinearColor Colors[] = {FLinearColor(1.f, .52f, .08f), FLinearColor(.04f, .85f, .95f)};
    return Colors[K];
}

FLinearColor SoraAccessibility::TelegraphColor(const UObject* WorldContext, ETelegraph Kind)
{
    const ASoraGameMode* Mode = WorldContext ? Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(WorldContext)) : nullptr;
    return TelegraphColor(Mode && Mode->Settings() ? Mode->Settings()->TelegraphPalette() : EPalette::Standard, Kind);
}

FLinearColor SoraAccessibility::StrikeColor(const UObject* WorldContext, ETelegraph Kind)
{
    return FMath::Lerp(TelegraphColor(WorldContext, Kind), FLinearColor::White, .25f);
}

SoraAccessibility::EDifficulty SoraAccessibility::CampaignDifficulty(const UObject* WorldContext)
{
    const ASoraGameMode* Mode = WorldContext ? Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(WorldContext)) : nullptr;
    return Mode && Mode->Settings() ? Mode->Settings()->CampaignDifficulty() : EDifficulty::Normal;
}

float SoraAccessibility::SubtitleScale(ESubtitleSize Size)
{
    switch (Size)
    {
    case ESubtitleSize::Large: return 1.25f;
    case ESubtitleSize::ExtraLarge: return 1.5f;
    case ESubtitleSize::Standard:
    case ESubtitleSize::Count: break;
    }
    return 1.f;
}

void SoraAccessibility::StartCameraShake(APlayerController* Controller, TSubclassOf<UCameraShakeBase> Shake, float Scale)
{
    if (!Controller || !Shake)
        return;
    const ASoraGameMode* Mode = Cast<ASoraGameMode>(UGameplayStatics::GetGameMode(Controller));
    const float Setting = Mode && Mode->Settings() ? Mode->Settings()->CameraShake() / 100.f : 1.f;
    if (Scale * Setting > 0.f)
        Controller->ClientStartCameraShake(Shake, Scale * Setting);
}

ASoraGameMode* USoraSettings::Mode() const { return Cast<ASoraGameMode>(GetOuter()); }

const USoraSettingsSaveGame& USoraSettings::Read() const
{
    return Save ? *Save : *GetDefault<USoraSettingsSaveGame>();
}

USoraSettingsSaveGame& USoraSettings::Write()
{
    if (!Save)
        Save = USoraSettingsSaveGame::New();
    return *Save;
}

void USoraSettings::Load(const FString& Slot, bool bAttachToEngine)
{
    SlotName = Slot;
    bAttached = bAttachToEngine && UGameUserSettings::GetGameUserSettings() != nullptr;
    Save = Slot.IsEmpty() ? nullptr : Cast<USoraSettingsSaveGame>(UGameplayStatics::LoadGameFromSlot(Slot, 0));
    if (Save && Save->SaveSchema != USoraSettingsSaveGame::Schema)
        Save = nullptr;
    // Values out of range fall back to their defaults, one by one.
    const USoraSettingsSaveGame* Defaults = GetDefault<USoraSettingsSaveGame>();
    USoraSettingsSaveGame& D = Write();
    if (D.BusVolumes.Num() != static_cast<int32>(ESoraAudioBus::Count))
        D.BusVolumes = Defaults->BusVolumes;
    for (int32& Volume : D.BusVolumes)
        if (Volume < 0 || Volume > 100)
            Volume = 100;
    const auto Within = [](int32& Value, int32 Count, int32 Default)
    {
        if (Value < 0 || Value >= Count)
            Value = Default;
    };
    Within(D.SubtitleSize, static_cast<int32>(SoraAccessibility::ESubtitleSize::Count), Defaults->SubtitleSize);
    Within(D.TelegraphPalette, static_cast<int32>(SoraAccessibility::EPalette::Count), Defaults->TelegraphPalette);
    Within(D.CampaignDifficulty, static_cast<int32>(SoraAccessibility::EDifficulty::Count), Defaults->CampaignDifficulty);
    Within(D.CameraShake, 101, Defaults->CameraShake);
    if (ASoraGameMode* Game = Mode())
        Game->bEnglishSubtitles = D.EnglishSubtitles;
    // First launch on this machine: the platform's preset, once. A player's
    // own graphics after that stay in GameUserSettings.ini.
    if (!D.GraphicsPresetApplied)
    {
        SoraGraphics::Set(EditGraphics(), SoraGraphics::PlatformPresets()[0]);
        ApplyGraphics(false);
        D.GraphicsPresetApplied = true;
        if (!SlotName.IsEmpty() && !UGameplayStatics::SaveGameToSlot(Save, SlotName, 0))
            UE_LOG(LogTemp, Warning, TEXT("SORA settings could not be saved"));
    }
    ApplyAudio();
}

UGameUserSettings& USoraSettings::Graphics() const
{
    if (bAttached)
        if (UGameUserSettings* Engine = UGameUserSettings::GetGameUserSettings())
            return *Engine;
    if (!DetachedGraphics)
    {
        // Created on first use, from the engine defaults rather than any ini.
        USoraSettings* Self = const_cast<USoraSettings*>(this);
        Self->DetachedGraphics = NewObject<UGameUserSettings>(Self, TEXT("DetachedGraphics"));
        Self->DetachedGraphics->SetToDefaults();
    }
    return *DetachedGraphics;
}

UGameUserSettings& USoraSettings::EditGraphics()
{
    // The engine's settings reset themselves to the defaults the first time
    // they are applied with no GameUserSettings.ini behind them, which would
    // drop any change made here first. Validating first settles them.
    UGameUserSettings& Settings = Graphics();
    if (bAttached)
        Settings.ValidateSettings();
    return Settings;
}

void USoraSettings::Changed()
{
    if (!SlotName.IsEmpty() && !UGameplayStatics::SaveGameToSlot(Save, SlotName, 0))
        UE_LOG(LogTemp, Warning, TEXT("SORA settings could not be saved"));
    OnChanged.Broadcast();
}

void USoraSettings::ApplyGraphics(bool bResolution)
{
    if (!bAttached)
        return;
    UGameUserSettings& Settings = Graphics();
    if (bResolution)
    {
        Settings.ApplyResolutionSettings(false);
        Settings.ConfirmVideoMode();
    }
    Settings.ApplyNonResolutionSettings();
    Settings.SaveSettings();
}

void USoraSettings::ApplyAudio()
{
    if (!bAttached || !GEngine)
        return;
    if (FAudioDeviceHandle Device = GEngine->GetMainAudioDevice())
        Device->SetTransientPrimaryVolume(BusGain(ESoraAudioBus::Master));
}

SoraGraphics::EPreset USoraSettings::GraphicsPreset() const { return SoraGraphics::Detect(Graphics()); }

void USoraSettings::SetGraphicsPreset(SoraGraphics::EPreset Preset)
{
    if (Preset == SoraGraphics::EPreset::Custom || !SoraGraphics::PlatformPresets().Contains(Preset))
        return;
    SoraGraphics::Set(EditGraphics(), Preset);
    ApplyGraphics(false);
    Changed();
}

int32 USoraSettings::ResolutionScale() const { return SoraGraphics::ResolutionScale(Graphics()); }

void USoraSettings::SetResolutionScale(int32 Percent)
{
    EditGraphics().SetResolutionScaleValueEx(FMath::Clamp(Percent, 50, 100));
    ApplyGraphics(false);
    Changed();
}

int32 USoraSettings::FrameRateLimit() const { return FMath::RoundToInt(Graphics().GetFrameRateLimit()); }

void USoraSettings::SetFrameRateLimit(int32 FramesPerSecond)
{
    EditGraphics().SetFrameRateLimit(FMath::Max(FramesPerSecond, 0));
    ApplyGraphics(false);
    Changed();
}

bool USoraSettings::VSync() const { return Graphics().IsVSyncEnabled(); }

void USoraSettings::SetVSync(bool bEnabled)
{
    EditGraphics().SetVSyncEnabled(bEnabled);
    ApplyGraphics(false);
    Changed();
}

EWindowMode::Type USoraSettings::WindowMode() const { return Graphics().GetFullscreenMode(); }

void USoraSettings::SetWindowMode(EWindowMode::Type WindowMode)
{
    if (!SoraGraphics::PlatformWindowModes().Contains(WindowMode))
        return;
    UGameUserSettings& Settings = EditGraphics();
    const FIntPoint Desktop = Settings.GetDesktopResolution();
    // Fullscreen fills the display; a window opens at two thirds of it.
    if (WindowMode != EWindowMode::Windowed)
        Settings.SetScreenResolution(Desktop);
    else if (Desktop.X > 0 && Settings.GetScreenResolution().X >= Desktop.X)
        Settings.SetScreenResolution(FIntPoint(Desktop.X * 2 / 3 / 2 * 2, Desktop.Y * 2 / 3 / 2 * 2));
    Settings.SetFullscreenMode(WindowMode);
    ApplyGraphics(true);
    Changed();
}

int32 USoraSettings::BusVolume(ESoraAudioBus Bus) const
{
    return Read().BusVolumes.IsValidIndex(static_cast<int32>(Bus)) ? Read().BusVolumes[static_cast<int32>(Bus)] : 100;
}

void USoraSettings::SetBusVolume(ESoraAudioBus Bus, int32 Percent)
{
    if (!Write().BusVolumes.IsValidIndex(static_cast<int32>(Bus)))
        return;
    Write().BusVolumes[static_cast<int32>(Bus)] = FMath::Clamp(Percent, 0, 100);
    ApplyAudio();
    Changed();
}

float USoraSettings::BusGain(ESoraAudioBus Bus) const { return FMath::Square(BusVolume(Bus) / 100.f); }

bool USoraSettings::EnglishSubtitles() const { return Read().EnglishSubtitles; }

void USoraSettings::SetEnglishSubtitles(bool bEnabled)
{
    Write().EnglishSubtitles = bEnabled;
    if (ASoraGameMode* Game = Mode())
        Game->bEnglishSubtitles = bEnabled;
    Changed();
}

SoraAccessibility::ESubtitleSize USoraSettings::SubtitleSize() const { return static_cast<SoraAccessibility::ESubtitleSize>(Read().SubtitleSize); }

void USoraSettings::SetSubtitleSize(SoraAccessibility::ESubtitleSize Size)
{
    Write().SubtitleSize = FMath::Clamp(static_cast<int32>(Size), 0, static_cast<int32>(SoraAccessibility::ESubtitleSize::Count) - 1);
    Changed();
}

bool USoraSettings::SpeakerNames() const { return Read().SpeakerNames; }

void USoraSettings::SetSpeakerNames(bool bEnabled)
{
    Write().SpeakerNames = bEnabled;
    Changed();
}

bool USoraSettings::SoundCaptions() const { return Read().SoundCaptions; }

void USoraSettings::SetSoundCaptions(bool bEnabled)
{
    Write().SoundCaptions = bEnabled;
    Changed();
}

SoraAccessibility::EPalette USoraSettings::TelegraphPalette() const { return static_cast<SoraAccessibility::EPalette>(Read().TelegraphPalette); }

void USoraSettings::SetTelegraphPalette(SoraAccessibility::EPalette Palette)
{
    Write().TelegraphPalette = FMath::Clamp(static_cast<int32>(Palette), 0, static_cast<int32>(SoraAccessibility::EPalette::Count) - 1);
    Changed();
}

bool USoraSettings::ToggleGuard() const { return Read().ToggleGuard; }

void USoraSettings::SetToggleGuard(bool bToggle)
{
    Write().ToggleGuard = bToggle;
    Changed();
}

bool USoraSettings::ToggleSprint() const { return Read().ToggleSprint; }

void USoraSettings::SetToggleSprint(bool bToggle)
{
    Write().ToggleSprint = bToggle;
    Changed();
}

SoraAccessibility::EDifficulty USoraSettings::CampaignDifficulty() const { return static_cast<SoraAccessibility::EDifficulty>(Read().CampaignDifficulty); }

void USoraSettings::SetCampaignDifficulty(SoraAccessibility::EDifficulty Difficulty)
{
    Write().CampaignDifficulty = FMath::Clamp(static_cast<int32>(Difficulty), 0, static_cast<int32>(SoraAccessibility::EDifficulty::Count) - 1);
    Changed();
}

bool USoraSettings::ReduceFlashing() const { return Read().ReduceFlashing; }

void USoraSettings::SetReduceFlashing(bool bEnabled)
{
    Write().ReduceFlashing = bEnabled;
    Changed();
}

bool USoraSettings::AutoSteer() const { return Read().AutoSteer; }

void USoraSettings::SetAutoSteer(bool bEnabled)
{
    Write().AutoSteer = bEnabled;
    Changed();
}

bool USoraSettings::RhythmAssist() const { return Read().RhythmAssist; }
void USoraSettings::SetRhythmAssist(bool bEnabled)
{
    Write().RhythmAssist = bEnabled;
    Changed();
}

bool USoraSettings::HoldToCrank() const { return Read().HoldToCrank; }
void USoraSettings::SetHoldToCrank(bool bEnabled)
{
    Write().HoldToCrank = bEnabled;
    Changed();
}

bool USoraSettings::VolleyAutoOrder() const { return Read().VolleyAutoOrder; }

void USoraSettings::SetVolleyAutoOrder(bool bEnabled)
{
    Write().VolleyAutoOrder = bEnabled;
    Changed();
}

int32 USoraSettings::CameraShake() const { return Read().CameraShake; }

void USoraSettings::SetCameraShake(int32 Percent)
{
    Write().CameraShake = FMath::Clamp(Percent, 0, 100);
    Changed();
}
