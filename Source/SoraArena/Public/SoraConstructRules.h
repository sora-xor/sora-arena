#pragma once
#include "SoraCombatRules.h"
#include "SoraHistoricalArms.h"

// Chapter 08 §2.2. These values belong to the collateral construct; ordinary
// loom automatons retain their catalog attacks and defenses.
namespace SoraConstructRules
{
constexpr int Health = 260;
constexpr int WindupMs = 900;
constexpr int RecoveryMs = 1400;
constexpr int RadiusCm = 250;
constexpr int Damage = 25;
constexpr int SealCutMs = 1000;
constexpr int HeavyHits = 2;
constexpr int SettleMs = 1600; // Functional release proxy; final animation is art-owned.

constexpr bool Heavy(SoraCombatRules::EHit Kind, int Weapon, int StaggerMs)
{
    return Kind == SoraCombatRules::EHit::Melee && SoraHistoricalArms::IsMelee(Weapon) &&
        SoraHistoricalArms::Profile(SoraHistoricalArms::FormFor(Weapon)).StaggerMs >= SoraCombatRules::HeavyStaggerMs &&
        StaggerMs >= SoraCombatRules::HeavyStaggerMs;
}
constexpr int CoreDamage(bool Open, bool CoreContact, SoraCombatRules::EHit Kind, int Weapon, int StaggerMs)
{
    return Open && CoreContact && Heavy(Kind, Weapon, StaggerMs) ? Health / HeavyHits : 0;
}
constexpr bool Open(bool Alive, bool SlamReleased, bool Recovering, int RemainingMs)
{
    return Alive && SlamReleased && Recovering && RemainingMs > 0;
}
constexpr float Settle(int ElapsedMs)
{
    const float T = ElapsedMs <= 0 ? 0.f : ElapsedMs >= SettleMs ? 1.f : float(ElapsedMs) / SettleMs;
    return T * T * (3.f - 2.f * T);
}
}
