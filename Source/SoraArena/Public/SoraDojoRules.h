#pragma once

// Chapter-one training rules shared by the offline Unreal encounter and a
// host-compiled acceptance driver. Durations are integer milliseconds so a
// saved lesson cannot depend on a floating-point frame boundary.
namespace SoraDojoRules
{
enum class EAction { Stance, Guard, Parry, Recovery };

struct FProgress
{
    unsigned CompletedMask;
};

constexpr unsigned CompleteMask = 0x0fu;
constexpr int StanceHoldMs = 600;
constexpr int GuardHoldMs = 350;
constexpr int ParryWindowMs = 260;

// A pupil_men repeat is measured from windup onset, whereas pupil_kesa
// specifies recovery after contact. Zero selects the other cadence. The
// default retains the unconfigured training-arena pupil's existing drill.
struct FPupilTiming
{
    int WindupMs = 550;
    int RecoveryMs = 1450;
    int RepeatMs = 0;
};
constexpr int PupilWindupMs(const FPupilTiming& Timing, int Difficulty)
{
    const int Permille = Difficulty == 0 ? 1300 : Difficulty == 2 ? 850 : 1000;
    return (Timing.WindupMs * Permille + 500) / 1000;
}
constexpr bool PupilTimingValid(const FPupilTiming& Timing)
{
    return Timing.WindupMs > 0 && Timing.WindupMs <= 10000 &&
        ((Timing.RecoveryMs > 0 && Timing.RecoveryMs <= 60000 && Timing.RepeatMs == 0) ||
         (Timing.RecoveryMs == 0 && Timing.RepeatMs > PupilWindupMs(Timing, 0) && Timing.RepeatMs <= 60000));
}
constexpr int PupilStartIntervalMs(const FPupilTiming& Timing, int Difficulty)
{
    return Timing.RepeatMs > 0 ? Timing.RepeatMs : PupilWindupMs(Timing, Difficulty) + Timing.RecoveryMs;
}

constexpr bool ProgressValid(FProgress Progress)
{
    return Progress.CompletedMask == 0u || Progress.CompletedMask == 1u ||
        Progress.CompletedMask == 3u || Progress.CompletedMask == 7u ||
        Progress.CompletedMask == CompleteMask;
}

constexpr int NextLesson(FProgress Progress)
{
    return !ProgressValid(Progress) ? -1 :
        Progress.CompletedMask == 0u ? 0 :
        Progress.CompletedMask == 1u ? 1 :
        Progress.CompletedMask == 3u ? 2 :
        Progress.CompletedMask == 7u ? 3 : 4;
}

constexpr bool CanScoreBout(FProgress Progress)
{
    return Progress.CompletedMask == CompleteMask;
}

constexpr bool CheckpointValid(FProgress Progress, int Bouts, unsigned SitesMask)
{
    return ProgressValid(Progress) && Bouts >= 0 && (SitesMask & ~7u) == 0u &&
        ((Bouts == 0 && (SitesMask == 0u || SitesMask == 1u)) || CanScoreBout(Progress));
}

constexpr bool Record(FProgress& Progress, EAction Action, int DurationMs,
    bool FacingAttacker = true, int RecoveryMs = 0)
{
    const int Stage = NextLesson(Progress);
    if (Stage < 0 || Stage > 3 || static_cast<int>(Action) != Stage || DurationMs < 0)
        return false;
    const bool Success = Action == EAction::Stance ? DurationMs >= StanceHoldMs :
        Action == EAction::Guard ? FacingAttacker && DurationMs >= GuardHoldMs :
        Action == EAction::Parry ? FacingAttacker && DurationMs <= ParryWindowMs :
        RecoveryMs > 0 && DurationMs >= RecoveryMs;
    if (!Success)
        return false;
    Progress.CompletedMask |= 1u << Stage;
    return true;
}
} // namespace SoraDojoRules
