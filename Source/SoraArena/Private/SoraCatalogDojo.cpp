#include "SoraCatalogDojo.h"
#include "SoraCatalog.h"
#include "SoraCatalogJson.h"

bool SoraCatalogDojo::Read(const FJsonObject& Object, FSoraBeat& Beat)
{
    using namespace SoraCatalogJson;
    const auto Ext = Child(Object, TEXT("ext"));
    const auto Pattern = Ext ? Child(*Ext, TEXT("opponent_pattern")) : nullptr;
    const bool Men = Beat.Id == TEXT("ch01.b03"), Kesa = Beat.Id == TEXT("ch01.b04");
    // The maai teacher never attacks, and Toranosuke owns a separate pattern
    // in bosses.json. Do not apply a lesson's timing to either opponent.
    if (!Men && !Kesa) return !Pattern;
    FString Id, Telegraph;
    SoraDojoRules::FPupilTiming Timing;
    Timing.RecoveryMs = 0;
    if (!Pattern || !Beat.bSparring || !Beat.Is(SoraBeatRules::EType::Duel) ||
        !Str(*Pattern, TEXT("id"), Id) || !Str(*Pattern, TEXT("telegraph"), Telegraph) ||
        !Int(*Pattern, TEXT("windup_ms"), Timing.WindupMs)) return false;
    if (Men)
    {
        double Repeat = 0, Stagger = 0;
        if (Id != TEXT("pupil_men") || Telegraph != TEXT("amber_edge") ||
            Pattern->HasField(TEXT("recovery_ms")) ||
            !Pattern->TryGetNumberField(TEXT("repeat_s"), Repeat) || !FMath::IsFinite(Repeat) || Repeat <= 0 || Repeat > 60 ||
            !Pattern->TryGetNumberField(TEXT("stagger_on_awase_s"), Stagger) || Stagger != 1.2) return false;
        Timing.RepeatMs = FMath::RoundToInt32(Repeat * 1000.0);
        if (!FMath::IsNearlyEqual(Repeat * 1000.0, double(Timing.RepeatMs), .0001)) return false;
    }
    else if (Id != TEXT("pupil_kesa") || Telegraph != TEXT("amber_edge_diagonal") ||
        Pattern->HasField(TEXT("repeat_s")) || !Int(*Pattern, TEXT("recovery_ms"), Timing.RecoveryMs)) return false;
    if (!SoraDojoRules::PupilTimingValid(Timing)) return false;
    Beat.PupilTiming = Timing;
    return true;
}
