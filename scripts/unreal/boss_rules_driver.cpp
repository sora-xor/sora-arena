// Host acceptance driver for Source/SoraArena/Public/SoraBossRules.h and the
// mutō-dori and unguardable-blow rules in SoraCombatRules.h. Built and run by
// scripts/unreal/test_boss_rules.py, which generates SORA_BOSS_TABLE from
// Content/Data/bosses.json.
#include "SoraBossRules.h"
#include "SoraCombatRules.h"

#include <cassert>
#include <cstdio>
#include <initializer_list>

using namespace SoraBossRules;
namespace Combat = SoraCombatRules;

struct FDataFight
{
    const char* Id;
    int Health[3];
    int FloorPermille;
    int PhaseCount;
    int Starts[MaxPhases];
    int PhaseFloors[MaxPhases];
};

#include SORA_BOSS_TABLE

static void Difficulty()
{
    // bosses.json: Easy (稽古) +30%, Hard (免許皆伝) -15% (bible §8).
    assert(ForDifficulty(900, EDifficulty::Normal, 1300, 850) == 900);
    assert(ForDifficulty(900, EDifficulty::Easy, 1300, 850) == 1170);
    assert(ForDifficulty(900, EDifficulty::Hard, 1300, 850) == 765);
    assert(ForDifficulty(500, EDifficulty::Hard, 1300, 850) == 425);
    // The chapter-six mutō-dori window: 180 ms, 234 on Easy, 153 on Hard.
    assert(ForDifficulty(Combat::MutoWindowMs, EDifficulty::Easy, 1300, 850) == 234);
    assert(ForDifficulty(Combat::MutoWindowMs, EDifficulty::Hard, 1300, 850) == 153);
}

static void Phases()
{
    const int Starts[] = {1000, 600, 250};
    assert(HealthPermille(1400, 1400) == 1000 && HealthPermille(840, 1400) == 600 && HealthPermille(0, 1400) == 0);
    assert(HealthPermille(841, 1400) == 601 && HealthPermille(839, 1400) == 599);
    assert(PhaseFor(Starts, 3, 1000) == 0 && PhaseFor(Starts, 3, 601) == 0);
    assert(PhaseFor(Starts, 3, 600) == 1 && PhaseFor(Starts, 3, 251) == 1);
    assert(PhaseFor(Starts, 3, 250) == 2 && PhaseFor(Starts, 3, 0) == 2);
    assert(PhaseHealth(1400, 600) == 840 && PhaseHealth(1400, 250) == 350);
    // A blow stops at the next phase's start, so every phase is seen...
    assert(Admitted(1400, 1000, 1400, Starts, 3, 0, 0) == 560);
    assert(Admitted(840, 100, 1400, Starts, 3, 0, 0) == 0);
    assert(Admitted(900, 50, 1400, Starts, 3, 0, 0) == 50);
    assert(Admitted(840, 600, 1400, Starts, 3, 1, 0) == 490);
    // ...and the last phase falls to zero, unless the fight keeps a floor.
    assert(Admitted(350, 1000, 1400, Starts, 3, 2, 0) == 350);
    const int Duel[] = {1000, 500};
    assert(Admitted(70, 50, 600, Duel, 2, 1, 100) == 10 && Admitted(60, 50, 600, Duel, 2, 1, 100) == 0);
    assert(Admitted(0, 50, 600, Duel, 2, 1, 0) == 0 && Admitted(100, 0, 600, Duel, 2, 1, 0) == 0);
}

static void WeakPoints()
{
    assert(WeakPointDamage(52, 2000, -1) == 104);
    assert(WeakPointDamage(52, 2000, 50) == 50);
    assert(WeakPointDamage(40, 2500, 2200) == 100 && WeakPointDamage(40, 1250, -1) == 50);
    assert(WeakPointDamage(40, 0, -1) == 0);
    assert(Interrupted(250, 250) && !Interrupted(249, 250) && !Interrupted(10000, 0));
    assert(!SealsFail(2, 3) && SealsFail(3, 3) && !SealsFail(9, 0));
}

static void Metronome()
{
    assert(NextBeat(0, 0, 1300) == 0 && NextBeat(1, 0, 1300) == 1300 && NextBeat(1300, 0, 1300) == 1300);
    assert(NextBeat(2601, 0, 1300) == 3900 && NextBeat(5000, 1000, 1000) == 5000 && NextBeat(5001, 1000, 1000) == 6000);
    assert(NextBeat(700, 1000, 1000) == 1000 && NextBeat(2500, 1000, 0) == 2500);
}

static void Weighted()
{
    // Over one cycle of the summed weight every attack comes up exactly its
    // weight's number of times, and the same weights give the same sequence.
    const int Weights[] = {35, 25, 25, 15};
    FWeighted A = Fresh(), B = Fresh();
    int Counts[4] = {};
    int Run = 0, LongestRun = 0, Last = -1;
    for (int Pick = 0; Pick < 100; ++Pick)
    {
        const int First = PickWeighted(A, Weights, 4);
        assert(First == PickWeighted(B, Weights, 4) && First >= 0 && First < 4);
        ++Counts[First];
        Run = First == Last ? Run + 1 : 1;
        LongestRun = Run > LongestRun ? Run : LongestRun;
        Last = First;
    }
    assert(Counts[0] == 35 && Counts[1] == 25 && Counts[2] == 25 && Counts[3] == 15);
    // One whole cycle leaves nothing owed: the rotation repeats exactly.
    for (const int Owed : A.Current)
        assert(Owed == 0);
    // The rotation itself, pinned: chapter one's even-score habits.
    const int Rotation[] = {0, 1, 2, 3, 0, 1, 2, 0, 3, 0, 1, 2, 0, 1, 2, 0, 3, 1, 2, 0};
    FWeighted Pinned = Fresh();
    for (const int Expected : Rotation)
        assert(PickWeighted(Pinned, Weights, 4) == Expected);
    // A tie goes to the earlier habit.
    const int Even[] = {1, 1};
    FWeighted Tie = Fresh();
    assert(PickWeighted(Tie, Even, 2) == 0 && PickWeighted(Tie, Even, 2) == 1 && PickWeighted(Tie, Even, 2) == 0);
    // Interleaved, not bunched: the heaviest habit never runs three in a row.
    assert(LongestRun <= 2);
    const int Zeroes[] = {0, 5, 0};
    FWeighted C = Fresh();
    for (int Pick = 0; Pick < 10; ++Pick)
        assert(PickWeighted(C, Zeroes, 3) == 1);
    const int None[] = {0, 0};
    FWeighted D = Fresh();
    assert(PickWeighted(D, None, 2) == -1);
    // Intervals visit eight fixed steps spanning the whole range.
    bool Seen[8] = {};
    for (int Step = 0; Step < 8; ++Step)
    {
        const int Ms = IntervalMs(1600, 2400, Step);
        assert(Ms >= 1600 && Ms <= 2400);
        Seen[Step * 5 % 8] = true;
        assert(IntervalMs(1600, 2400, Step + 8) == Ms);
    }
    for (const bool Visited : Seen)
        assert(Visited);
    assert(IntervalMs(1000, 1600, 0) == 1000);
    const int Spread[] = {1600, 2171, 1828, 2400, 2057, 1714, 2285, 1942};
    for (int Step = 0; Step < 8; ++Step)
        assert(IntervalMs(1600, 2400, Step) == Spread[Step]);
}

static void Hearing()
{
    // Walk 12 m, crouch-walk 6 m, sprint 24 m; standing still is silent; a
    // flooded floor doubles it.
    assert(HearsSteps(1200, 150, false, false, 1200, 600, 2400, 40, 1000));
    assert(!HearsSteps(1201, 150, false, false, 1200, 600, 2400, 40, 1000));
    assert(HearsSteps(600, 150, true, false, 1200, 600, 2400, 40, 1000) && !HearsSteps(601, 150, true, false, 1200, 600, 2400, 40, 1000));
    assert(HearsSteps(2400, 400, false, true, 1200, 600, 2400, 40, 1000));
    assert(!HearsSteps(10, 40, false, true, 1200, 600, 2400, 40, 1000));
    assert(HearsSteps(1200, 150, true, false, 1200, 600, 2400, 40, 2000) && !HearsSteps(1201, 150, true, false, 1200, 600, 2400, 40, 2000));
    // The sonar ring: its front crosses 18 m in 720 ms and finds a mover.
    assert(PulseFrontCm(0, 720, 1800) == 0 && PulseFrontCm(360, 720, 1800) == 900 && PulseFrontCm(9999, 720, 1800) == 1800);
    assert(PulseReveals(121, 120, false) && !PulseReveals(120, 120, false) && PulseReveals(0, 120, true));
}

static void Strikes()
{
    assert(Lands(250, 250) && !Lands(251, 250) && !Lands(-1, 250));
    assert(ChargeRecoveryMs(true, 800, 1500) == 800 && ChargeRecoveryMs(false, 800, 1500) == 1500);
    // A locked volley: stepping 1.5 m off the mark breaks the lock.
    assert(LockHolds(150, 150) && !LockHolds(151, 150));
    // The mantle takes 70% off; a stunned boss takes half again.
    assert(Taken(100, 300) == 30 && Taken(40, 1500) == 60 && Taken(45, 1000) == 45);
    // Rear 120 degrees, other off-front, front.
    assert(DirectionalPermille(-500, 1500, 1200) == 1500 && DirectionalPermille(-499, 1500, 1200) == 1200);
    assert(DirectionalPermille(499, 1500, 1200) == 1200 && DirectionalPermille(500, 1500, 1200) == 1000);
    // Deflection: only ranged hits, only idle, only within the arc (cos 45° = 707).
    assert(Deflects(707, 707, true, true) && !Deflects(706, 707, true, true));
    assert(!Deflects(1000, 707, false, true) && !Deflects(1000, 707, true, false) && !Deflects(1000, 1000, true, true));
}

static void Zones()
{
    // Marked through windup and arming, armed for its life, then spent; a
    // zero life strikes once.
    assert(ZoneAt(0, 700, 800, 12000) == EZone::Marked && ZoneAt(1499, 700, 800, 12000) == EZone::Marked);
    assert(ZoneAt(1500, 700, 800, 12000) == EZone::Armed && ZoneAt(13499, 700, 800, 12000) == EZone::Armed);
    assert(ZoneAt(13500, 700, 800, 12000) == EZone::Spent);
    assert(ZoneAt(1500, 1500, 0, 0) == EZone::Armed && ZoneAt(1501, 1500, 0, 0) == EZone::Spent);
    assert(ZoneTick(0, -1, 1000) && !ZoneTick(999, 0, 1000) && ZoneTick(1000, 999, 1000) && !ZoneTick(1500, 1200, 0));
    assert(!ZoneTick(-1, -1, 1000));
    // A drone re-indexes every 8 s for 1.2 s, and right after it blocks.
    assert(!WardOpen(7999, 8000, 1200, 99999, true) && WardOpen(8000, 8000, 1200, 99999, true));
    assert(WardOpen(9199, 8000, 1200, 99999, true) && !WardOpen(9200, 8000, 1200, 99999, true));
    assert(WardOpen(100, 8000, 1200, 0, true) && WardOpen(100, 8000, 1200, 1199, true) && !WardOpen(100, 8000, 1200, 1200, true));
    assert(!WardOpen(100, 8000, 1200, 0, false) && !WardOpen(8000, 0, 0, 0, true));
}

static void MutoAndUnguardable()
{
    using namespace SoraCombatRules;
    // 無刀取り: sheathed, facing, a guard pressed within the window of the landing.
    assert(MutoDori(true, true, true, 180, MutoWindowMs, 1000) && MutoDori(true, true, true, 0, MutoWindowMs, FrontMilli));
    assert(!MutoDori(true, true, true, 181, MutoWindowMs, 1000) && !MutoDori(true, true, true, -1, MutoWindowMs, 1000));
    assert(!MutoDori(false, true, true, 100, MutoWindowMs, 1000) && !MutoDori(true, false, true, 100, MutoWindowMs, 1000));
    assert(!MutoDori(true, true, false, 100, MutoWindowMs, 1000) && !MutoDori(true, true, true, 100, MutoWindowMs, FrontMilli - 1));
    assert(HitStopMs(EHit::Melee, EDefense::MutoDori, false, 0) == HitStopMs(EHit::Melee, EDefense::Parry, false, 0));
    // A final foreclosure: a fresh guard parries it; a held guard lets it all through.
    const FAttack Foreclosure{EHit::Melee, 45, true, 45, 0, ParryStaggerMs, false, true};
    assert(Defend({true, 200, 100, 1000}, Foreclosure).Defense == EDefense::Parry);
    const FOutcome Held = Defend({true, 400, 100, 1000}, Foreclosure);
    assert(Held.Defense == EDefense::Exposed && Held.Damage == 45 && Held.Stamina == 0);
    // An unguardable slam that cannot be parried goes through any guard.
    const FAttack Slam{EHit::Melee, 45, false, 45, 0, 0, false, true};
    assert(Defend({true, 100, 100, 1000}, Slam).Defense == EDefense::Exposed);
    // The arena's hazards are never guarded.
    assert(!Guardable(EHit::Hazard) && Defend({true, 100, 100, 1000}, {EHit::Hazard, 35, false, -1, -1, 0, false}).Damage == 35);
}

// Every fight in bosses.json: phase starts land on whole health, and hits of
// any size walk it through every phase in order, never skipping one, down to
// zero or its floor.
static int Fights()
{
    int Checked = 0;
    for (const FDataFight& Fight : Fights_)
    {
        assert(Fight.PhaseCount >= 1 && Fight.PhaseCount <= MaxPhases && Fight.Starts[0] == 1000);
        for (int Difficulty = 0; Difficulty < 3; ++Difficulty)
        {
            const int Max = Fight.Health[Difficulty];
            for (int Phase = 0; Phase < Fight.PhaseCount; ++Phase)
            {
                assert(Max * Fight.Starts[Phase] % 1000 == 0);
                assert(HealthPermille(PhaseHealth(Max, Fight.Starts[Phase]), Max) == Fight.Starts[Phase]);
                assert(PhaseFor(Fight.Starts, Fight.PhaseCount, Fight.Starts[Phase]) == Phase);
            }
            for (const int Hit : {1, 7, 52, 130, 499, 5000})
            {
                int Health = Max, Phase = 0, Seen = 1;
                for (int Blow = 0; Blow < 100000; ++Blow)
                {
                    const int Floor = Fight.FloorPermille > Fight.PhaseFloors[Phase] ? Fight.FloorPermille : Fight.PhaseFloors[Phase];
                    const int Landed = Admitted(Health, Hit, Max, Fight.Starts, Fight.PhaseCount, Phase, Floor);
                    if (Landed == 0)
                    {
                        const int Next = PhaseFor(Fight.Starts, Fight.PhaseCount, HealthPermille(Health, Max));
                        if (Next == Phase)
                            break;
                        assert(Next == Phase + 1);
                        Phase = Next;
                        ++Seen;
                        continue;
                    }
                    Health -= Landed;
                }
                assert(Seen == Fight.PhaseCount);
                const int Floor = Fight.FloorPermille > Fight.PhaseFloors[Phase] ? Fight.FloorPermille : Fight.PhaseFloors[Phase];
                assert(Health == PhaseHealth(Max, Floor));
            }
        }
        ++Checked;
    }
    return Checked;
}

int main()
{
    Difficulty();
    Phases();
    WeakPoints();
    Metronome();
    Weighted();
    Hearing();
    Strikes();
    Zones();
    MutoAndUnguardable();
    const int Checked = Fights();
    std::printf("boss rules driver: %d fights walked through every phase\n", Checked);
    return 0;
}
