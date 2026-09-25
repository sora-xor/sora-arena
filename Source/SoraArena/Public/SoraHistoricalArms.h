#pragma once

// Offline campaign combat design values, in Unreal centimetres and seconds.
// These are readable game approximations of distinct weapon handling, not
// instruction in any living school or an Arena multiplayer rules profile.
// Every melee arm in the campaign, Nyaakoto's and each class's, strikes the
// same way: a committed windup with its direction fixed, one contact inside
// its useful distance, then a recovery. Windup plus recovery is the catalog
// cooldown and the maximum distance its range (SoraArena.Campaign.HistoricalArmsCatalog).
namespace SoraHistoricalArms
{
enum class EForm { Katana, Kusarigama, Wakizashi, Kanabo, ForgeHammer, Tanto, MonofilamentNaginata, Yari, Naginata };
enum class EFootwork { Close, Hold, Withdraw };

struct FProfile
{
    float MinimumDistanceCm;
    float MaximumDistanceCm;
    float WindupSeconds;
    float RecoverySeconds;
    float MinimumFacingDot;
    // A landed strike's weight against an opponent's poise (SoraCombatRules).
    int StaggerMs;
};

constexpr FProfile Profile(EForm Form)
{
    switch (Form)
    {
    case EForm::Katana: return {55.f, 195.f, .20f, .55f, .70f, 350};
    case EForm::Kusarigama: return {70.f, 250.f, .18f, .30f, .80f, 300};
    case EForm::Wakizashi: return {25.f, 160.f, .12f, .36f, .70f, 250};
    case EForm::Kanabo: return {60.f, 210.f, .30f, .70f, .75f, 900};
    case EForm::ForgeHammer: return {45.f, 175.f, .22f, .56f, .72f, 800};
    case EForm::Tanto: return {20.f, 155.f, .10f, .29f, .70f, 200};
    case EForm::MonofilamentNaginata: return {110.f, 300.f, .34f, .56f, .76f, 450};
    case EForm::Yari: return {120.f, 285.f, .29f, .75f, .90f, 500};
    case EForm::Naginata: return {95.f, 260.f, .36f, .88f, .76f, 450};
    }
    return {0.f, 0.f, 0.f, 0.f, 1.f, 0};
}

// The catalog's melee arms: each class's melee weapon 2c, the monofilament
// naginata (12) and the campaign yari (19) and naginata (20).
constexpr bool IsMelee(int WeaponId)
{
    return WeaponId == 0 || WeaponId == 2 || WeaponId == 4 || WeaponId == 6 || WeaponId == 8 ||
        WeaponId == 10 || WeaponId == 12 || WeaponId == 19 || WeaponId == 20;
}

constexpr EForm FormFor(int WeaponId)
{
    switch (WeaponId)
    {
    case 2: return EForm::Kusarigama;
    case 4: return EForm::Wakizashi;
    case 6: return EForm::Kanabo;
    case 8: return EForm::ForgeHammer;
    case 10: return EForm::Tanto;
    case 12: return EForm::MonofilamentNaginata;
    case 19: return EForm::Yari;
    case 20: return EForm::Naginata;
    default: return EForm::Katana;
    }
}

constexpr bool CanStrike(EForm Form, float DistanceCm, float FacingDot)
{
    const FProfile P = Profile(Form);
    return DistanceCm >= P.MinimumDistanceCm && DistanceCm <= P.MaximumDistanceCm &&
        FacingDot >= P.MinimumFacingDot;
}

// A blade retainer's maai: it closes from outside its cut, holds inside it and
// withdraws when crowded.
constexpr EFootwork RetainerFootwork(float DistanceCm)
{
    return DistanceCm < 90.f ? EFootwork::Withdraw :
        DistanceCm > 165.f ? EFootwork::Close : EFootwork::Hold;
}
} // namespace SoraHistoricalArms
