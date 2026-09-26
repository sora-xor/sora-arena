#include "Audio/SoraAudioData.h"

// The sound captions audio.json names (its cues' "caption" keys). Each is an
// NSLOCTEXT with its English subtitle in Content/Localization/Game/en/Game.po;
// USoraCaptions shows both, in brackets, with the sound's direction.
// scripts/audio/validate_audio_data.py fails on a key missing here or a text
// no cue uses.
FText SoraAudioData::CaptionText(FName Key)
{
    static const FName CellEjects(TEXT("CellEjects")), BarrierShatters(TEXT("BarrierShatters")),
        BarrierRecharging(TEXT("BarrierRecharging")), NightingaleFloor(TEXT("NightingaleFloor")),
        TargetingLock(TEXT("TargetingLock")), SkySplits(TEXT("SkySplits")), DebtSealsClamp(TEXT("DebtSealsClamp")),
        CreditHouseChime(TEXT("CreditHouseChime"));
    if (Key == CellEjects)
        return NSLOCTEXT("SoraArena.SoundCaptions", "CellEjects", "セル排出音");
    if (Key == BarrierShatters)
        return NSLOCTEXT("SoraArena.SoundCaptions", "BarrierShatters", "障壁が砕ける");
    if (Key == BarrierRecharging)
        return NSLOCTEXT("SoraArena.SoundCaptions", "BarrierRecharging", "障壁の再生音");
    if (Key == NightingaleFloor)
        return NSLOCTEXT("SoraArena.SoundCaptions", "NightingaleFloor", "鶯張りが鳴る");
    if (Key == TargetingLock)
        return NSLOCTEXT("SoraArena.SoundCaptions", "TargetingLock", "照準固定音");
    if (Key == SkySplits)
        return NSLOCTEXT("SoraArena.SoundCaptions", "SkySplits", "空が裂ける音");
    if (Key == DebtSealsClamp)
        return NSLOCTEXT("SoraArena.SoundCaptions", "DebtSealsClamp", "債務の封印が締まる音");
    if (Key == CreditHouseChime)
        return NSLOCTEXT("SoraArena.SoundCaptions", "CreditHouseChime", "信用院の警報音");
    return FText::GetEmpty();
}
