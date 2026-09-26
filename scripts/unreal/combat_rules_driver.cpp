#include "SoraCombatRules.h"
#include <cassert>
#include <initializer_list>

using namespace SoraCombatRules;

// test_combat_rules.py generates these from Content/Data/enemies.json and
// crates/arena-core/src/catalog.rs.
struct FDataAttack
{
    const char* Id;
    FAttack Attack;
};
#include SORA_ENEMY_ATTACKS

namespace
{
constexpr FGuard Fresh{true, 120, 100, 1000};
constexpr FGuard Held{true, 900, 100, 1000};
constexpr FGuard Behind{true, 120, 100, -1000};
constexpr FGuard Lowered{false, 120, 100, 1000};
constexpr FGuard Spent{true, 120, MinimumGuardStamina - 1, 1000};
}

int main()
{
    // Guard and parry meet every melee attacker the same way: a fresh frontal
    // guard parries a parryable blow outright and staggers its attacker; a
    // held one takes the blow's chip; from behind, lowered or spent, nothing.
    int Parryable = 0;
    for (const FDataAttack& Data : EnemyMeleeAttacks)
    {
        const FAttack A = Data.Attack;
        assert(A.Kind == EHit::Melee && A.Damage > 0);
        const FOutcome Parry = Defend(Fresh, A);
        const FOutcome Guard = Defend(Held, A);
        if (A.Parryable)
        {
            ++Parryable;
            assert(Parry.Defense == EDefense::Parry && Parry.Damage == 0 && Parry.Stamina == ParryStamina);
            assert(Parry.AttackerStaggerMs == A.ParryStaggerMs && Parry.AttackerStaggerMs > 0);
        }
        else
            assert(Parry.Defense == EDefense::Guard && Parry.Damage == A.GuardChip && Parry.AttackerStaggerMs == 0);
        assert(Guard.Defense == EDefense::Guard && Guard.Damage == A.GuardChip && Guard.Damage < A.Damage);
        assert(Guard.Stamina == A.GuardStamina && Guard.GuardBroken == A.BreaksGuard);
        assert(Defend(Behind, A).Defense == EDefense::Exposed && Defend(Behind, A).Damage == A.Damage);
        assert(Defend(Lowered, A).Damage == A.Damage && Defend(Spent, A).Damage == A.Damage);
    }
    assert(Parryable > 0);
    // The collector's cleave and a dojo pupil's cut are melee blows too.
    const FAttack Cleave{EHit::Melee, 30, true, 8, -1, ParryStaggerMs, false};
    assert(Defend(Fresh, Cleave).Defense == EDefense::Parry && Defend(Held, Cleave).Damage == 8);
    assert(Defend(Held, Cleave).Stamina == MeleeGuardStamina);
    const FAttack Spar{EHit::Melee, 4, true, -1, -1, ParryStaggerMs, false};
    assert(Defend(Fresh, Spar).AttackerStaggerMs == 1200 && Defend(Held, Spar).Damage == Share(4, MeleeChipPermille));
    // The parry window is the dojo lesson's 260 ms, inclusive; the front is 120 degrees.
    assert(ParryWindowMs == 260 && ParryWindowMs == SoraDojoRules::ParryWindowMs);
    assert(Defend({true, 260, 100, 1000}, Cleave).Defense == EDefense::Parry);
    assert(Defend({true, 261, 100, 1000}, Cleave).Defense == EDefense::Guard);
    assert(Defend({true, 100, 100, FrontMilli}, Cleave).Defense == EDefense::Parry);
    assert(Defend({true, 100, 100, FrontMilli - 1}, Cleave).Defense == EDefense::Exposed);
    // An unparryable thrust that breaks the guard: a fresh guard only chips it.
    const FAttack Thrust{EHit::Melee, 40, false, 20, 40, 0, true};
    assert(Defend(Fresh, Thrust).Defense == EDefense::Guard && Defend(Fresh, Thrust).Damage == 20);
    assert(Defend(Fresh, Thrust).GuardBroken);

    // Ranged hits and blast fronts: a frontal guard halves them (rounded up),
    // never parries them, and costs less stamina than a blow.
    for (const EHit Kind : {EHit::Ranged, EHit::Blast})
    {
        const FAttack Round{Kind, 9, false, -1, -1, 0, false};
        assert(Defend(Fresh, Round).Defense == EDefense::Guard && Defend(Fresh, Round).Damage == 5);
        assert(Defend(Held, Round).Damage == 5 && Defend(Held, Round).Stamina == RangedGuardStamina);
        assert(Defend(Behind, Round).Damage == 9);
        const FAttack Shot{Kind, 40, true, -1, -1, 1200, false};
        assert(Defend(Fresh, Shot).Defense == EDefense::Guard && Defend(Fresh, Shot).AttackerStaggerMs == 0);
    }
    assert(RangedGuardStamina < MeleeGuardStamina);
    // Beams and scripted damage ignore any guard.
    assert(Defend(Fresh, {EHit::Beam, 22, false, -1, -1, 0, false}).Damage == 22);
    assert(Defend(Fresh, {EHit::Scripted, 50, false, -1, -1, 0, false}).Defense == EDefense::Exposed);

    // Hit-stop: only a blade's contact holds the world, a parry longest.
    assert(HitStopMs(EHit::Melee, EDefense::Parry, false, 0) > HitStopMs(EHit::Melee, EDefense::Exposed, true, 0));
    assert(HitStopMs(EHit::Melee, EDefense::Exposed, true, 0) > HitStopMs(EHit::Melee, EDefense::Guard, false, 0));
    assert(HitStopMs(EHit::Melee, EDefense::Exposed, true, HeavyStaggerMs) > HitStopMs(EHit::Melee, EDefense::Exposed, true, 350));
    assert(HitStopMs(EHit::Melee, EDefense::Exposed, false, 0) == 0);
    assert(HitStopMs(EHit::Ranged, EDefense::Guard, true, 0) == 0 && HitStopMs(EHit::Blast, EDefense::Exposed, true, 0) == 0);
    assert(HitStopDilationPermille > 0 && HitStopDilationPermille < 1000);

    // Stagger: a strike's weight against poise, once per immunity window.
    assert(StrikeStaggerMs(350, 300, false) == 350);
    assert(StrikeStaggerMs(350, 450, false) == 0 && StrikeStaggerMs(900, 450, false) == 900);
    assert(StrikeStaggerMs(900, 300, true) == 0 && StrikeStaggerMs(0, 0, false) == 0);
    assert(StrikeStaggerMs(900, 10000, false) == 0);
    assert(StaggeredDamage(52, true) == 65 && StaggeredDamage(52, false) == 52);
    // A katana cut every 750 ms cannot keep a retainer staggered through its 420 ms windup.
    assert(StaggerImmunityMs > 750 && 350 < 750);

    // Shields, weak rears and barriers.
    const int Front = 500;
    assert(ShieldStops(EHit::Melee, 900, Front, false) && ShieldStops(EHit::Ranged, 600, Front, false));
    assert(ShieldStops(EHit::Blast, 900, Front, false));
    assert(!ShieldStops(EHit::Melee, 900, Front, true) && !ShieldStops(EHit::Melee, 200, Front, false));
    assert(!ShieldStops(EHit::Scripted, 900, Front, false) && !ShieldStops(EHit::Beam, 900, Front, false));
    assert(RearDamage(45, -900, 2000) == 90 && RearDamage(45, 900, 2000) == 45 && RearDamage(45, 0, 2000) == 45);
    FBarrierHit Soaked = SoakBarrier({60000, 60000}, 24, 1500, false);
    assert(Soaked.Damage == 0 && Soaked.Barrier.HealthMilli == 24000 && !Soaked.Broke);
    Soaked = SoakBarrier(Soaked.Barrier, 52, 1000, false);
    assert(Soaked.Damage == 0 && Soaked.Broke && Soaked.Barrier.HealthMilli == 0);
    assert(SoakBarrier(Soaked.Barrier, 52, 1000, false).Damage == 52);
    assert(SoakBarrier({60000, 60000}, 85, 1000, true).Damage == 85);
    assert(RegeneratedBarrier({0, 60000}, 4000, 4000, 30).HealthMilli == 0);
    assert(RegeneratedBarrier({0, 60000}, 5000, 4000, 30).HealthMilli == 30000);
    assert(RegeneratedBarrier({0, 60000}, 6000, 4000, 30).HealthMilli == 60000);
    assert(RegeneratedBarrier({0, 60000}, 2000000000, 4000, 30).HealthMilli == 60000);
    assert(RegeneratedBarrier({10000, 60000}, 4017, 4000, 30).HealthMilli == 10510);

    // Shells: dud short of the arming distance, full damage inside the radius
    // with a clear line, the owner included, allies never.
    assert(ArmingCm(7) * 10 == KERNEL_ARMING_7_MM && ArmingCm(15) * 10 == KERNEL_ARMING_15_MM);
    assert(ArmingCm(1) == 0 && ArmingCm(18) == 0);
    assert(!Armed(199, 200) && Armed(200, 200) && Armed(0, 0));
    assert(BlastReaches(true, false, 100, 360, true));
    assert(BlastReaches(false, true, 360, 360, true));
    assert(!BlastReaches(false, false, 100, 360, true));
    assert(!BlastReaches(false, true, 361, 360, true) && !BlastReaches(true, false, 100, 360, false));
    assert(!BlastDefensible(true) && BlastDefensible(false));

    // 活人剣: knocked down, never killed; the collar can be cut within the
    // window; left too long, the conscript rises hurt.
    assert(CanCutSeal(EConscript::Down, 0, 8000) && CanCutSeal(EConscript::Down, 7999, 8000));
    assert(!CanCutSeal(EConscript::Down, 8000, 8000) && !CanCutSeal(EConscript::Standing, 10, 8000));
    assert(!CanCutSeal(EConscript::Freed, 10, 8000));
    assert(Rises(EConscript::Down, 8000, 8000) && !Rises(EConscript::Down, 7999, 8000) && !Rises(EConscript::Freed, 9000, 8000));
    assert(RisenHealth(60, 500) == 30 && RisenHealth(1, 1) == 1);

    // Bursts miss one aimed round in three, never twice in a row, offset by slot.
    for (int Slot = 0; Slot < 6; ++Slot)
    {
        int Misses = 0;
        for (int Round = 0; Round < 30; ++Round)
        {
            Misses += RoundMisses(Slot, Round);
            assert(!(Round > 0 && RoundMisses(Slot, Round) && RoundMisses(Slot, Round - 1)));
        }
        assert(Misses == 10);
    }
    assert(RoundMisses(1, 2) && RoundMisses(2, 1) && RoundMisses(3, 0));

    // 無刀取り: sheathed, facing, a guard pressed no more than the window
    // before an eligible cut lands.
    assert(MutoDori(true, true, true, 0, MutoWindowMs, 1000) && MutoDori(true, true, true, MutoWindowMs, MutoWindowMs, FrontMilli));
    assert(!MutoDori(true, true, true, MutoWindowMs + 1, MutoWindowMs, 1000) && !MutoDori(true, false, true, 100, MutoWindowMs, 1000));
    assert(!MutoDori(false, true, true, 100, MutoWindowMs, 1000) && !MutoDori(true, true, true, 100, MutoWindowMs, FrontMilli - 1));
    assert(!MutoDori(true, true, false, 100, MutoWindowMs, 1000) && !MutoDori(true, true, true, -1, MutoWindowMs, 1000));
    // 転: within 400 ms of an awase, or in the last marobashi_ms of a windup that allows it.
    assert(MarobashiOpen(0, -1, 0) && MarobashiOpen(MarobashiWindowMs, -1, 0) && !MarobashiOpen(MarobashiWindowMs + 1, -1, 0));
    assert(MarobashiOpen(-1, 0, 400) && MarobashiOpen(-1, 400, 400) && !MarobashiOpen(-1, 401, 400));
    assert(!MarobashiOpen(-1, 100, 0) && !MarobashiOpen(-1, -1, 400));
    // The arc ends outside the front 120 degrees, where a flank cut lands and a
    // shield's rim does not reach; the lag outlasts the step.
    assert(MarobashiArcDeg > 60 && MarobashiArcDeg < 90 && MarobashiTurnLagMs > MarobashiStepMs);
    // 残心: half a second of guard within the window after a defeat, once.
    assert(Zanshin(500, 500) && Zanshin(ZanshinWindowMs, ZanshinHoldMs) && !Zanshin(ZanshinWindowMs + 1, 2000));
    assert(!Zanshin(400, ZanshinHoldMs - 1) && !Zanshin(900, -1) && !Zanshin(-1, 600));
    assert(ZanshinStamina == 15 && ZanshinHoldMs == 500 && ZanshinHoldMs < ZanshinWindowMs);
    // 水月: the outer fifteen percent of the reach, never beyond it.
    assert(InMaai(195, 195) && InMaai(166, 195) && !InMaai(165, 195) && !InMaai(196, 195));
    assert(!InMaai(100, 0) && InMaai(285, 285) && !InMaai(120, 285) && !InMaai(-1, 195));
}
