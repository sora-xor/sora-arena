#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "UObject/Package.h"
#include "SoraSettingsSaveGame.generated.h"

// The player's local settings: volumes, subtitles and accessibility. Graphics
// live in UGameUserSettings (GameUserSettings.ini) and controls in
// USoraControlSaveGame. Nothing here reaches combat rules, the kernel or a
// wallet. USoraSettings reads and writes it; a save of another schema is
// discarded and the defaults apply, and values out of range fall back to
// their defaults.
UCLASS()
class SORAARENA_API USoraSettingsSaveGame : public USaveGame
{
    GENERATED_BODY()
public:
    static constexpr int32 Schema = 1;
    // New settings stamped with Schema. Unreal writes only the properties
    // that differ from the class default, so SaveSchema defaults to 0: a
    // stamped schema is always on disk, and a file without one reads as 0.
    static USoraSettingsSaveGame* New()
    {
        USoraSettingsSaveGame* Settings = NewObject<USoraSettingsSaveGame>(GetTransientPackage());
        Settings->SaveSchema = Schema;
        return Settings;
    }
    UPROPERTY(SaveGame) int32 SaveSchema = 0;
    // Set once the platform's graphics preset has been applied on first launch.
    UPROPERTY(SaveGame) bool GraphicsPresetApplied = false;
    // Percent, 0 to 100, in ESoraAudioBus order: master, music, effects,
    // voice, interface, ambience.
    UPROPERTY(SaveGame) TArray<int32> BusVolumes = {100, 100, 100, 100, 100, 100};
    UPROPERTY(SaveGame) bool EnglishSubtitles = true;
    // SoraAccessibility::ESubtitleSize.
    UPROPERTY(SaveGame) int32 SubtitleSize = 0;
    UPROPERTY(SaveGame) bool SpeakerNames = true;
    UPROPERTY(SaveGame) bool SoundCaptions = false;
    // SoraAccessibility::EPalette.
    UPROPERTY(SaveGame) int32 TelegraphPalette = 0;
    UPROPERTY(SaveGame) bool ToggleGuard = false;
    UPROPERTY(SaveGame) bool ToggleSprint = false;
    // SoraAccessibility::EDifficulty; Normal.
    UPROPERTY(SaveGame) int32 CampaignDifficulty = 1;
    UPROPERTY(SaveGame) bool ReduceFlashing = false;
    UPROPERTY(SaveGame) bool AutoSteer = false;
    UPROPERTY(SaveGame) bool HoldToCrank = false;
    UPROPERTY(SaveGame) bool VolleyAutoOrder = true;
    // Percent, 0 to 100.
    UPROPERTY(SaveGame) int32 CameraShake = 100;
};
