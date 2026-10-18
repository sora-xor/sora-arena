#pragma once

// The opening distance lesson. Establish the band first, then recover it
// after each of the mentor's authored steps. A checkpoint restarts the beat;
// partial holds and steps are deliberately not campaign unlocks.
namespace SoraMaaiRules
{
constexpr int MaxSteps = 8;
struct FMove { int ForwardCm = 0; int RightCm = 0; };
struct FConfig
{
    int Count = 0;
    int InnerCm = 0;
    int OuterCm = 0;
    int HoldMs = 0;
    int FacingPermille = 0;
    int HintMs = 0;
    FMove Moves[MaxSteps] = {};
};
struct FState
{
    bool Acquired = false;
    int Done = 0;
    int HeldMs = 0;
    int IdleMs = 0;
    bool InBand = false;
};
enum class EResult { None, Acquired, Step, Complete };
constexpr bool Valid(const FConfig& C)
{
    if (C.Count < 0 || C.Count > MaxSteps) return false;
    if (C.Count && (C.InnerCm <= 0 || C.OuterCm <= C.InnerCm || C.OuterCm > 1000 ||
        C.HoldMs <= 0 || C.HoldMs > 10000 || C.FacingPermille < 1 || C.FacingPermille > 1000 ||
        C.HintMs <= 0 || C.HintMs > 60000)) return false;
    if (!C.Count && (C.InnerCm || C.OuterCm || C.HoldMs || C.FacingPermille || C.HintMs)) return false;
    for (int I = 0; I < MaxSteps; ++I)
    {
        const FMove& M = C.Moves[I];
        if (I >= C.Count ? M.ForwardCm || M.RightCm :
            (M.ForwardCm == 0) == (M.RightCm == 0) || M.ForwardCm < -500 || M.ForwardCm > 500 ||
            M.RightCm < -500 || M.RightCm > 500) return false;
    }
    return true;
}
constexpr bool Complete(const FState& S, const FConfig& C) { return S.Done >= C.Count; }
constexpr bool Band(const FConfig& C, double DistanceCm, double FacingDot)
{
    return C.Count > 0 && DistanceCm >= C.InnerCm && DistanceCm <= C.OuterCm &&
        FacingDot * 1000.0 >= C.FacingPermille;
}
constexpr bool Hint(const FState& S, const FConfig& C) { return C.Count > 0 && !Complete(S,C) && S.IdleMs >= C.HintMs; }
constexpr EResult Tick(FState& S, const FConfig& C, int DeltaMs, double DistanceCm, double FacingDot, bool Ready)
{
    if (!Ready || !Valid(C) || Complete(S,C) || DeltaMs <= 0)
    { S.HeldMs = 0; S.InBand = false; return EResult::None; }
    const int Delta = DeltaMs > 60000 ? 60000 : DeltaMs;
    S.IdleMs = S.IdleMs > C.HintMs - Delta ? C.HintMs : S.IdleMs + Delta;
    S.InBand = Band(C,DistanceCm,FacingDot);
    S.HeldMs = !S.InBand ? 0 : S.HeldMs > C.HoldMs - Delta ? C.HoldMs : S.HeldMs + Delta;
    if (S.HeldMs < C.HoldMs) return EResult::None;
    S.HeldMs = 0; S.IdleMs = 0; S.InBand = false;
    if (!S.Acquired) { S.Acquired = true; return EResult::Acquired; }
    ++S.Done;
    return Complete(S,C) ? EResult::Complete : EResult::Step;
}
}
