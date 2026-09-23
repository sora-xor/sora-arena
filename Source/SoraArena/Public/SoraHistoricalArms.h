#pragma once

// Offline campaign combat design values, in Unreal centimetres and seconds.
// These are readable game approximations of distinct weapon handling, not
// instruction in any living school or an Arena multiplayer rules profile.
namespace SoraHistoricalArms
{
enum class EForm { Katana, Yari, Naginata };

struct FProfile
{
    float MinimumDistanceCm;
    float MaximumDistanceCm;
    float WindupSeconds;
    float RecoverySeconds;
    float MinimumFacingDot;
};

constexpr FProfile Profile(EForm Form)
{
    switch (Form)
    {
    case EForm::Katana: return {55.f, 195.f, .20f, .55f, .70f};
    case EForm::Yari: return {120.f, 285.f, .29f, .75f, .90f};
    case EForm::Naginata: return {95.f, 260.f, .36f, .88f, .76f};
    }
    return {0.f, 0.f, 0.f, 0.f, 1.f};
}

constexpr bool CanStrike(EForm Form, float DistanceCm, float FacingDot)
{
    const FProfile P = Profile(Form);
    return DistanceCm >= P.MinimumDistanceCm && DistanceCm <= P.MaximumDistanceCm &&
        FacingDot >= P.MinimumFacingDot;
}
} // namespace SoraHistoricalArms
