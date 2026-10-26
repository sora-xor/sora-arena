#pragma once
#include "SoraDojoRules.h"

// Offline campaign combat rules shared by the Unreal damage path
// (Source/SoraArena/Private/Combat) and a host-compiled acceptance driver:
// how a hit meets a raised guard, what staggers and for how long, how long a
// contact holds the world still, the sword school's mutō-dori, 転, 残心 and
// 水月, when a shell arms and whom its blast reaches, how an opponent's
// shield or barrier takes a hit, and how a debt-bound conscript is subdued
// instead of killed. Damage is whole points, time is
// integer milliseconds and angles are cosines in thousandths, so no outcome
// depends on a dice roll or a floating-point frame boundary. These are the
// campaign's rules; the multiplayer kernel's are docs/combat-rules.md.
namespace SoraCombatRules
{
// Melee: a blade, staff, baton or claw. Ranged: a bullet or an arrow. Blast:
// a shell's detonation, from where it went off. Beam: a locked debt beam,
// never guarded. Scripted: damage no weapon dealt (a story event or a test).
// Hazard: the arena turned against the hero (a molten channel, a strike on
// marked cover, a floor tile giving way), never guarded.
enum class EHit { Melee, Ranged, Blast, Beam, Scripted, Hazard };
// MutoDori: sheathed, the hero stepped inside a committed cut and took the blade.
enum class EDefense { Exposed, Guard, Parry, MutoDori };

// A guard covers the front 120 degrees.
constexpr int FrontMilli = 500;
// 合わせ: a guard raised no more than this long before a cut meets it, the
// window chapter one's parry lesson teaches.
constexpr int ParryWindowMs = SoraDojoRules::ParryWindowMs;
constexpr int MinimumGuardStamina = 18;
constexpr int ParryStamina = 18;
constexpr int MeleeGuardStamina = 30;
constexpr int MeleeChipPermille = 250;
// A raised blade takes half of a bullet, an arrow or a blast front.
constexpr int RangedChipPermille = 500;
constexpr int RangedGuardStamina = 12;
constexpr int ParryStaggerMs = 1200;
// A guard broken by a heavy blow cannot be raised again for this long.
constexpr int GuardBreakMs = 1000;

constexpr int Clamp(int Value, int Low, int High)
{
    return Value < Low ? Low : Value > High ? High : Value;
}

// Permille share of Damage, rounded half up.
constexpr int Share(int Damage, int Permille)
{
    return (Damage * Permille + 500) / 1000;
}

// How an attack meets a raised guard. Negative GuardChip and GuardStamina use
// the kind's shares. An unguardable blow (a slam, a final foreclosure) goes
// through a held guard whole; if it is also parryable, a fresh guard still
// meets it.
struct FAttack
{
    EHit Kind;
    int Damage;
    bool Parryable;
    int GuardChip;
    int GuardStamina;
    int ParryStaggerMs;
    bool BreaksGuard;
    bool Unguardable = false;
};

// The defender: whether a guard is held and for how long, its stamina, and the
// cosine between its facing and the direction to where the hit came from.
struct FGuard
{
    bool Held;
    int HeldMs;
    int Stamina;
    int FacingMilli;
};

struct FOutcome
{
    EDefense Defense;
    int Damage;
    int Stamina;
    // A parried attacker is staggered this long.
    int AttackerStaggerMs;
    bool GuardBroken;
};

constexpr bool Guardable(EHit Kind)
{
    return Kind == EHit::Melee || Kind == EHit::Ranged || Kind == EHit::Blast;
}

// Guard and parry against every attacker: a fresh frontal guard parries a
// parryable melee attack outright and staggers its attacker; a held one takes
// the attack's chip. Bullets, arrows and blast fronts are never parried; a
// frontal guard halves them. Beams and scripted damage ignore guards, and
// nothing is defended from behind or on a spent guard.
constexpr FOutcome Defend(FGuard Guard, FAttack Attack)
{
    const FOutcome Exposed{EDefense::Exposed, Attack.Damage, 0, 0, false};
    if (!Guard.Held || Guard.HeldMs < 0 || Guard.FacingMilli < FrontMilli ||
        Guard.Stamina < MinimumGuardStamina || !Guardable(Attack.Kind) || Attack.Damage < 0)
        return Exposed;
    if (Attack.Kind == EHit::Melee)
    {
        if (Attack.Parryable && Guard.HeldMs <= ParryWindowMs)
            return {EDefense::Parry, 0, ParryStamina, Attack.ParryStaggerMs, false};
        if (Attack.Unguardable)
            return Exposed;
        const int Chip = Attack.GuardChip >= 0 ? Clamp(Attack.GuardChip, 0, Attack.Damage)
                                               : Share(Attack.Damage, MeleeChipPermille);
        const int Cost = Attack.GuardStamina >= 0 ? Attack.GuardStamina : MeleeGuardStamina;
        return {EDefense::Guard, Chip, Cost, 0, Attack.BreaksGuard};
    }
    return {EDefense::Guard, Share(Attack.Damage, RangedChipPermille), RangedGuardStamina, 0, false};
}

// Hit-stop: after a blade meets a body or a guard, the whole world runs at
// five percent speed for a few real milliseconds, so the contact reads.
// Ranged hits and blasts never stop the world.
constexpr int HitStopDilationPermille = 50;
constexpr int HeavyStaggerMs = 800;

constexpr int HitStopMs(EHit Kind, EDefense Defense, bool Landed, int StaggerMs)
{
    if (Kind != EHit::Melee)
        return 0;
    return Defense == EDefense::Parry || Defense == EDefense::MutoDori ? 120 : Defense == EDefense::Guard ? 60 :
        !Landed ? 0 : StaggerMs >= HeavyStaggerMs ? 100 : 70;
}

// 無刀取り (mutō-dori). Sheathing the blade takes SheatheMs, and a sheathed
// hand guards nothing. Sheathed and facing a committed cut that allows it,
// the hero who presses guard no more than the window before the cut lands
// steps inside the arc and takes the blade: none of the blow lands and the
// attacker is disarmed. A mistimed attempt takes the whole blow. The window
// is Normal's; bosses.json scales it with the windups on Easy and Hard.
constexpr int SheatheMs = 700;
constexpr int MutoWindowMs = 180;

constexpr bool MutoDori(bool Eligible, bool Sheathed, bool Pressed, int PressedMs, int WindowMs, int FacingMilli)
{
    return Eligible && Sheathed && Pressed && PressedMs >= 0 && PressedMs <= WindowMs && FacingMilli >= FrontMilli;
}

// 転 (marobashi): a sideways step that rolls around an opponent to its flank
// (story bible §3.2). It answers the opponent within MarobashiWindowMs after
// the hero's awase on it, or in the last stretch of a blow whose windup
// allows it (bosses.json marobashi_ms, scaled like the windup). The hero
// travels MarobashiArcDeg around the opponent over MarobashiStepMs (the full
// arc out to a spear's distance; farther out a sidestep of MarobashiStepCm);
// the blow he stepped from misses him, and the opponent cannot turn after
// him for MarobashiTurnLagMs.
constexpr int MarobashiWindowMs = 400;
constexpr int MarobashiArcDeg = 70;
constexpr int MarobashiStepCm = 300;
constexpr int MarobashiStepMs = 200;
constexpr int MarobashiTurnLagMs = 800;

// SinceAwaseMs is negative without an awase on this opponent, UntilLandsMs
// negative without a blow under way.
constexpr bool MarobashiOpen(int SinceAwaseMs, int UntilLandsMs, int WindowMs)
{
    return (SinceAwaseMs >= 0 && SinceAwaseMs <= MarobashiWindowMs) ||
        (WindowMs > 0 && UntilLandsMs >= 0 && UntilLandsMs <= WindowMs);
}

// 残心 (zanshin): the mind stays on the fallen. A guard held ZanshinHoldMs
// after the hero defeats an opponent restores ZanshinStamina to it, once,
// when the hold is complete within ZanshinWindowMs of the defeat; the hold
// itself costs no guard stamina. HeldMs counts the hold from the defeat at
// the earliest, and is negative while the guard is down.
constexpr int ZanshinHoldMs = 500;
constexpr int ZanshinWindowMs = 2500;
constexpr int ZanshinStamina = 15;

constexpr bool Zanshin(int SinceDefeatMs, int HeldMs)
{
    return SinceDefeatMs >= 0 && SinceDefeatMs <= ZanshinWindowMs && HeldMs >= ZanshinHoldMs;
}

// 水月 (suigetsu), the distance read: the reticle's ring shows while the
// opponent before the hero stands in the outer MaaiBandPermille of his melee
// arm's reach, where his committed cut lands and a shorter blade does not
// reach him. (The bible proposes reach ±15%; the ring stops at the reach, so
// it never lights where the cut would fall short.)
constexpr int MaaiBandPermille = 150;

constexpr bool InMaai(int DistanceCm, int ReachCm)
{
    return ReachCm > 0 && DistanceCm <= ReachCm && DistanceCm * 1000 >= ReachCm * (1000 - MaaiBandPermille);
}

// Stagger. A staggered opponent drops its windup and cannot act, and every
// hit on it deals a quarter more. A landed strike staggers when its weight
// meets the target's poise, but not again within the immunity window of the
// last strike stagger, so no chain of cuts can hold an opponent still. A
// parry's stagger ignores the window: it is earned.
constexpr int StaggerDamagePermille = 1250;
constexpr int StaggerImmunityMs = 1500;

constexpr int StrikeStaggerMs(int WeaponStaggerMs, int PoiseMs, bool Immune)
{
    return !Immune && WeaponStaggerMs > 0 && WeaponStaggerMs >= PoiseMs ? WeaponStaggerMs : 0;
}

constexpr int StaggeredDamage(int Damage, bool Staggered)
{
    return Staggered ? Share(Damage, StaggerDamagePermille) : Damage;
}

// Where a hit came from relative to a body's facing: the front and rear 120
// degrees.
constexpr bool FromFront(int FacingMilli, int HalfArcMilli)
{
    return FacingMilli >= HalfArcMilli;
}

constexpr bool FromRear(int FacingMilli)
{
    return FacingMilli <= -FrontMilli;
}

// A tower shield stops everything from the covered arc while it is squared,
// scripted damage excepted. A yari thrust on the rim turns it aside instead.
constexpr bool ShieldStops(EHit Kind, int FacingMilli, int HalfArcMilli, bool Open)
{
    return !Open && Kind != EHit::Scripted && Kind != EHit::Beam && FromFront(FacingMilli, HalfArcMilli);
}

constexpr int RearDamage(int Damage, int FacingMilli, int RearWeakPermille)
{
    return FromRear(FacingMilli) ? Share(Damage, RearWeakPermille) : Damage;
}

// Only the explicitly authored floor-contact rate omits vulnerability bonuses.
// This changes no shield, barrier, invulnerability or defeat admission rules.
enum class EEnvironmentalRate { None, MoltenChannel, WorkshopOil };
constexpr int EnemyVulnerabilityDamage(int Damage,EHit Kind,EEnvironmentalRate Rate,
                                      bool Staggered,int FacingMilli,int RearWeakPermille)
{
    return Kind==EHit::Hazard&&(Rate==EEnvironmentalRate::MoltenChannel||Rate==EEnvironmentalRate::WorkshopOil) ? Damage :
        RearDamage(StaggeredDamage(Damage,Staggered),FacingMilli,RearWeakPermille);
}

// A personal barrier soaks every hit, scaled by the weapon's permille, until
// it breaks; the hit that breaks it does not carry through. After a quiet
// spell it regenerates at a fixed rate. It is kept in thousandths of a point
// and regenerates from the last hit's level, so no frame step rounds it.
struct FBarrier
{
    int HealthMilli;
    int MaxMilli;
};

struct FBarrierHit
{
    FBarrier Barrier;
    // What still reaches the body.
    int Damage;
    bool Broke;
};

constexpr FBarrierHit SoakBarrier(FBarrier Barrier, int Damage, int Permille, bool Bypass)
{
    if (Bypass || Barrier.HealthMilli <= 0)
        return {Barrier, Damage, false};
    Barrier.HealthMilli = Clamp(Barrier.HealthMilli - Share(Damage, Permille) * 1000, 0, Barrier.MaxMilli);
    return {Barrier, 0, Barrier.HealthMilli == 0};
}

// The barrier QuietMs after the last hit left it at AtLastHit.
constexpr FBarrier RegeneratedBarrier(FBarrier AtLastHit, int QuietMs, int DelayMs, int PerSecond)
{
    if (QuietMs <= DelayMs || PerSecond <= 0 || AtLastHit.HealthMilli >= AtLastHit.MaxMilli)
        return AtLastHit;
    // Thousandths per second times milliseconds; full once enough time has passed.
    const int Missing = AtLastHit.MaxMilli - AtLastHit.HealthMilli;
    const int Regenerating = QuietMs - DelayMs;
    AtLastHit.HealthMilli = Regenerating > Missing / PerSecond ? AtLastHit.MaxMilli :
        Clamp(AtLastHit.HealthMilli + PerSecond * Regenerating, 0, AtLastHit.MaxMilli);
    return AtLastHit;
}

// Shells. A shell that stops before travelling its arming distance is a dud:
// no blast at all. An armed detonation hits every body inside its radius with
// a clear line to the detonation point, at full damage: the owner itself,
// without any directional defense, and the owner's opponents, but never the
// owner's allies. These match the kernel's weapon 7 and 15 (catalog.rs).
constexpr int GrenadeLauncherArmingCm = 200;
constexpr int MicroMortarArmingCm = 450;

constexpr int ArmingCm(int WeaponId)
{
    return WeaponId == 7 ? GrenadeLauncherArmingCm : WeaponId == 15 ? MicroMortarArmingCm : 0;
}

constexpr bool Armed(int TraveledCm, int ArmingDistanceCm)
{
    return TraveledCm >= ArmingDistanceCm;
}

constexpr bool BlastReaches(bool Self, bool Opponent, int DistanceCm, int RadiusCm, bool Clear)
{
    return Clear && DistanceCm >= 0 && DistanceCm <= RadiusCm && (Self || Opponent);
}

// A body is defended only from someone else's blast.
constexpr bool BlastDefensible(bool Self)
{
    return !Self;
}

// 活人剣: a debt-bound conscript is never killed. A blow that would kill it
// knocks it down instead (峰打ち); while it is down, holding Interact long
// enough cuts its collar and frees it. Left down too long, the collar drags
// it back up with part of its health.
enum class EConscript { Standing, Down, Freed };

constexpr bool CanCutSeal(EConscript State, int DownMs, int WindowMs)
{
    return State == EConscript::Down && DownMs >= 0 && DownMs < WindowMs;
}

constexpr bool Rises(EConscript State, int DownMs, int WindowMs)
{
    return State == EConscript::Down && DownMs >= WindowMs;
}

constexpr int RisenHealth(int MaxHealth, int Permille)
{
    return Clamp(Share(MaxHealth, Permille), 1, MaxHealth);
}

// Rifle bursts miss on a fixed pattern, never a dice roll: one aimed round in
// three, offset by slot so a squad does not miss in unison.
constexpr bool RoundMisses(int Slot, int Round)
{
    return (Round + Slot) % 3 == 0;
}
} // namespace SoraCombatRules
