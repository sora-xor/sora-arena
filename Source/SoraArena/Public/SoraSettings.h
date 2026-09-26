#pragma once
#include "CoreMinimal.h"
#include "GenericPlatform/GenericWindow.h"
#include "Templates/SubclassOf.h"
#include "UObject/Object.h"
#include "SoraSettings.generated.h"
class APlayerController;
class ASoraGameMode;
class UCameraShakeBase;
class UGameUserSettings;
class USoraSettingsSaveGame;

// Graphics presets, applied through UGameUserSettings, which keeps them in
// GameUserSettings.ini. The Mac preset is the macOS path: software Lumen,
// conventional shadows (no MegaLights), TSR from 75% for 1080p at 60 fps on
// the M1 Ultra. Windows Quality is the visual tier (Epic scalability with
// MegaLights, TSR from 67% for 1440p at 60 fps on an RTX 4070-class card);
// Windows Competitive keeps Lumen and view distance but trims shadows,
// effects and post processing for frame rate and readability. These are
// targets to measure, not measured results. Window mode is its own setting.
namespace SoraGraphics
{
enum class EPreset : uint8 { Mac, WindowsQuality, WindowsCompetitive, Custom };
struct FPreset
{
    EPreset Id;
    // Scalability levels, 0 low to 3 epic.
    int32 ViewDistance, AntiAliasing, Shadow, GlobalIllumination, Reflection, PostProcess, Texture, Effects, Foliage, Shading, Landscape;
    // Percent of the output resolution TSR renders from.
    int32 ResolutionScale;
    // Frames per second; 0 is uncapped.
    int32 FrameRateLimit;
    bool bVSync;
};
SORAARENA_API const FPreset& Preset(EPreset Id);
// The presets this platform offers, its first-launch default first: Mac on
// macOS, the two Windows presets elsewhere.
SORAARENA_API TArray<EPreset> PlatformPresets();
// Sets the preset's levels, scale, cap and vsync. Nothing is applied or saved.
SORAARENA_API void Set(UGameUserSettings& Settings, EPreset Id);
// The preset the settings match exactly, or Custom.
SORAARENA_API EPreset Detect(const UGameUserSettings& Settings);
SORAARENA_API int32 ResolutionScale(const UGameUserSettings& Settings);
// The steps the Graphics screen offers.
inline constexpr int32 ResolutionScales[] = {50, 55, 60, 65, 67, 70, 75, 80, 85, 90, 95, 100};
inline constexpr int32 FrameRateLimits[] = {30, 60, 90, 120, 144, 165, 240, 0};
// Exclusive fullscreen is offered only where the platform has it.
SORAARENA_API TArray<EWindowMode::Type> PlatformWindowModes();
}

// Accessibility rules other systems read through USoraSettings.
namespace SoraAccessibility
{
// The two kinds of telegraph the story bible (section 8) sets apart: Cleave
// is a cleave, a blow, a ring or any other area attack, amber in Standard;
// Lock is a locked aim, a laser, a shot or a beam, cyan in Standard.
enum class ETelegraph : uint8 { Cleave, Lock, Count };
// Standard keeps the art direction's amber and cyan. RedGreen suits
// protanopia and deuteranopia, BlueYellow tritanopia, and HighContrast every
// kind; SoraArena.UI.TelegraphPalettes checks them by simulation.
enum class EPalette : uint8 { Standard, RedGreen, BlueYellow, HighContrast, Count };
SORAARENA_API FLinearColor TelegraphColor(EPalette Palette, ETelegraph Kind);
// The colour for the world's chosen palette; Standard without a game mode.
SORAARENA_API FLinearColor TelegraphColor(const UObject* WorldContext, ETelegraph Kind);
enum class ESubtitleSize : uint8 { Standard, Large, ExtraLarge, Count };
SORAARENA_API float SubtitleScale(ESubtitleSize Size);
// Campaign difficulty, the story bible's three tiers: 稽古 (Easy), 真剣
// (Normal) and 免許皆伝 (Hard), in the order of SoraBossRules and
// SoraStealthRules. The systems that own each rule apply it: windups +30%
// on Easy and -15% on Hard, per-difficulty boss health and timing
// tolerances, and on Easy a detected infiltration turns into a fight. It
// never changes the damage the hero takes, practice bots or the kernel.
enum class EDifficulty : uint8 { Easy, Normal, Hard, Count };
// The world's chosen difficulty; Normal without a game mode.
SORAARENA_API EDifficulty CampaignDifficulty(const UObject* WorldContext);
// Starts a camera shake at Scale times the player's camera-shake setting;
// every shake in the game goes through here.
SORAARENA_API void StartCameraShake(APlayerController* Controller, TSubclassOf<UCameraShakeBase> Shake, float Scale = 1.f);
}

// The mix buses the Audio screen sets (docs/audio.md section 2). Master is
// applied here, as the main audio device's volume; the audio lane applies the
// others' gains to its sound classes.
enum class ESoraAudioBus : uint8 { Master, Music, SFX, Voice, UI, Ambience, Count };

// The player's settings: graphics through UGameUserSettings, and everything
// else in USoraSettingsSaveGame. ASoraGameMode owns it and loads it at
// BeginPlay after the campaign save. Every setter saves at once and
// broadcasts OnChanged. Automation runs it detached from the engine: it then
// works on a transient UGameUserSettings and never applies or writes graphics
// or the audio device, so tests leave the editor and GameUserSettings.ini
// alone.
UCLASS()
class SORAARENA_API USoraSettings : public UObject
{
    GENERATED_BODY()
public:
    // Reads Slot. A missing save starts from the defaults and, attached to the
    // engine, applies the platform's first preset once.
    void Load(const FString& Slot, bool bAttachToEngine);
    bool IsAttached() const { return bAttached; }
    // The graphics the screen edits: the engine's own, or a transient copy.
    UGameUserSettings& Graphics() const;
    SoraGraphics::EPreset GraphicsPreset() const;
    void SetGraphicsPreset(SoraGraphics::EPreset Preset);
    int32 ResolutionScale() const;
    void SetResolutionScale(int32 Percent);
    int32 FrameRateLimit() const;
    void SetFrameRateLimit(int32 FramesPerSecond);
    bool VSync() const;
    void SetVSync(bool bEnabled);
    EWindowMode::Type WindowMode() const;
    void SetWindowMode(EWindowMode::Type Mode);

    // Percent, 0 to 100.
    int32 BusVolume(ESoraAudioBus Bus) const;
    void SetBusVolume(ESoraAudioBus Bus, int32 Percent);
    // The bus's own amplitude multiplier, on a squared curve so equal slider
    // steps sound roughly even. Master is not folded into the others.
    float BusGain(ESoraAudioBus Bus) const;

    bool EnglishSubtitles() const;
    void SetEnglishSubtitles(bool bEnabled);
    SoraAccessibility::ESubtitleSize SubtitleSize() const;
    void SetSubtitleSize(SoraAccessibility::ESubtitleSize Size);
    bool SpeakerNames() const;
    void SetSpeakerNames(bool bEnabled);
    bool SoundCaptions() const;
    void SetSoundCaptions(bool bEnabled);
    SoraAccessibility::EPalette TelegraphPalette() const;
    void SetTelegraphPalette(SoraAccessibility::EPalette Palette);
    bool ToggleGuard() const;
    void SetToggleGuard(bool bToggle);
    bool ToggleSprint() const;
    void SetToggleSprint(bool bToggle);
    SoraAccessibility::EDifficulty CampaignDifficulty() const;
    void SetCampaignDifficulty(SoraAccessibility::EDifficulty Difficulty);
    bool ReduceFlashing() const;
    void SetReduceFlashing(bool bEnabled);
    // On a horseback ride whose beat allows it (auto_steer: setting), the
    // horse follows the route while the player keeps gait and aim.
    bool AutoSteer() const;
    void SetAutoSteer(bool bEnabled);
    // Percent, 0 to 100.
    int32 CameraShake() const;
    void SetCameraShake(int32 Percent);

    // After every change; the audio lane re-reads its bus gains here.
    FSimpleMulticastDelegate OnChanged;
private:
    UPROPERTY() TObjectPtr<USoraSettingsSaveGame> Save;
    UPROPERTY() TObjectPtr<UGameUserSettings> DetachedGraphics;
    FString SlotName;
    bool bAttached = false;
    ASoraGameMode* Mode() const;
    // The loaded values; the defaults before Load.
    const USoraSettingsSaveGame& Read() const;
    USoraSettingsSaveGame& Write();
    void Changed();
    // Graphics() made ready for a change.
    UGameUserSettings& EditGraphics();
    // Applies graphics to the engine and writes GameUserSettings.ini when attached.
    void ApplyGraphics(bool bResolution);
    void ApplyAudio();
};
