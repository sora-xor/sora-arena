#pragma once

// The campaign bosses' and rival duels' rules (Content/Data/bosses.json, story
// bible §8), shared by ASoraBoss and a host-compiled acceptance driver: how
// difficulty scales a telegraph, which phase a health belongs to and how a
// blow stops at a phase's start or a fight's floor, the metronome of a
// fencer's measures, the fixed rotation that stands in for a duellist's
// weighted choice, what a blind hunter hears and what its sonar reveals,
// where a pounce lands, when a locked volley still holds its mark, and when
// a mantle, a stun, a weak point or an interrupted kneel changes a blow.
// Health and damage are whole points, time is integer milliseconds and
// distances whole centimetres; nothing is rolled.
namespace SoraBossRules
{
enum class EDifficulty { Easy, Normal, Hard };

constexpr int Permille = 1000;
constexpr int MaxPhases = 4;
constexpr int MaxWeighted = 8;

constexpr int Clamp(int Value, int Low, int High)
{
    return Value < Low ? Low : Value > High ? High : Value;
}

// Permille share, rounded half up.
constexpr int Share(int Value, int SharePermille)
{
    return (Value * SharePermille + 500) / 1000;
}

// Windups, recoveries of telegraphed attacks and the mutō-dori window are
// written for Normal. Easy (稽古) and Hard (免許皆伝) scale them by the
// permilles in bosses.json, rounded half up.
constexpr int ForDifficulty(int NormalMs, EDifficulty Difficulty, int EasyPermille, int HardPermille)
{
    return Difficulty == EDifficulty::Easy ? Share(NormalMs, EasyPermille) :
        Difficulty == EDifficulty::Hard ? Share(NormalMs, HardPermille) : NormalMs;
}

// Health as the campaign director reads it: permille of the maximum, rounded
// half up.
constexpr int HealthPermille(int Health, int MaxHealth)
{
    return MaxHealth <= 0 ? 0 : Clamp((Health * 1000 + MaxHealth / 2) / MaxHealth, 0, Permille);
}

// The health at which a phase starting at StartPermille begins. bosses.json
// keeps every maximum times every start divisible by 1000, so it is exact.
constexpr int PhaseHealth(int MaxHealth, int StartPermille)
{
    return MaxHealth * StartPermille / 1000;
}

// The phase a health permille belongs to: the last whose start it has
// reached. Starts descend from 1000.
constexpr int PhaseFor(const int* Starts, int Count, int HealthPermilleNow)
{
    int Phase = 0;
    for (int Index = 1; Index < Count && Index < MaxPhases; ++Index)
        if (HealthPermilleNow <= Starts[Index])
            Phase = Index;
    return Phase;
}

// How much of a weapon's blow lands on a boss in Phase: it stops at the next
// phase's start, so every phase change is seen, and at the fight's floor
// (a duel's opponent who can only be disarmed, a collector who can only be
// taken). Scripted damage (a story event) is not subject to either.
constexpr int Admitted(int Health, int Damage, int MaxHealth, const int* Starts, int Count, int Phase, int FloorPermille)
{
    if (Damage <= 0 || Health <= 0)
        return 0;
    int Lowest = PhaseHealth(MaxHealth, FloorPermille);
    if (Phase + 1 < Count && Phase + 1 < MaxPhases)
    {
        const int Next = PhaseHealth(MaxHealth, Starts[Phase + 1]);
        Lowest = Next > Lowest ? Next : Lowest;
    }
    return Clamp(Health - Lowest, 0, Damage);
}

// A blow on a weak point is scaled by its permille and cannot take more than
// the point has left (a negative Remaining has no pool of its own).
constexpr int WeakPointDamage(int Damage, int PointPermille, int Remaining)
{
    const int Scaled = Share(Damage, PointPermille);
    return Remaining < 0 ? Scaled : Clamp(Scaled, 0, Remaining);
}

// A fencer's metronome: an attack starts on the first beat, counted from the
// phase's start, at or after it is free to act.
constexpr int NextBeat(int FreeAtMs, int OriginMs, int BeatMs)
{
    if (BeatMs <= 0 || FreeAtMs <= OriginMs)
        return FreeAtMs > OriginMs ? FreeAtMs : OriginMs;
    const int Elapsed = FreeAtMs - OriginMs;
    return OriginMs + (Elapsed + BeatMs - 1) / BeatMs * BeatMs;
}

// A duellist's weighted habits without dice: smooth weighted round-robin.
// Every pick adds each weight to its running total, takes the largest
// (earliest on a tie) and charges it the sum, so over one cycle of the
// summed weight every attack comes up exactly its weight's number of times,
// interleaved rather than bunched.
struct FWeighted
{
    int Current[MaxWeighted];
};

constexpr FWeighted Fresh()
{
    return FWeighted{};
}

constexpr int PickWeighted(FWeighted& State, const int* Weights, int Count)
{
    int Total = 0, Best = -1;
    for (int Index = 0; Index < Count && Index < MaxWeighted; ++Index)
    {
        if (Weights[Index] <= 0)
            continue;
        State.Current[Index] += Weights[Index];
        Total += Weights[Index];
        if (Best < 0 || State.Current[Index] > State.Current[Best])
            Best = Index;
    }
    if (Best >= 0)
        State.Current[Best] -= Total;
    return Best;
}

// The pause before a duellist's next attack walks its range in eight fixed
// steps, visiting every step once per cycle in a spread-out order.
constexpr int IntervalMs(int MinMs, int MaxMs, int Step)
{
    const int Position = (Step < 0 ? -Step : Step) * 5 % 8;
    return MinMs + (MaxMs - MinMs) * Position / 7;
}

// A blind hunter hears the hero's feet within a stance's radius, scaled by
// the floor (a flooded vault doubles it). Standing still is silent.
constexpr bool HearsSteps(int DistanceCm, int SpeedCmS, bool Crouched, bool Sprinting, int WalkCm, int CrouchCm,
    int SprintCm, int StillCmS, int HearingPermille)
{
    if (SpeedCmS <= StillCmS || DistanceCm < 0)
        return false;
    const int Radius = Sprinting ? SprintCm : Crouched ? CrouchCm : WalkCm;
    return DistanceCm <= Share(Radius, HearingPermille);
}

// A sonar pulse's front expands to its radius over ExpandMs; when it passes
// the hero it reveals him if he is moving faster than RevealCmS or has just
// made a noise.
constexpr int PulseFrontCm(int ElapsedMs, int ExpandMs, int RadiusCm)
{
    return ExpandMs <= 0 ? RadiusCm : Clamp(RadiusCm * Clamp(ElapsedMs, 0, ExpandMs) / ExpandMs, 0, RadiusCm);
}

constexpr bool PulseReveals(int SpeedCmS, int RevealCmS, bool Noise)
{
    return Noise || SpeedCmS > RevealCmS;
}

// A pounce or a charge's landing hits what stands within its radius.
constexpr bool Lands(int DistanceCm, int RadiusCm)
{
    return DistanceCm >= 0 && DistanceCm <= RadiusCm;
}

// A missed pounce leaves its claws stuck: the longer recovery.
constexpr int ChargeRecoveryMs(bool Hit, int RecoveryMs, int MissRecoveryMs)
{
    return Hit ? RecoveryMs : MissRecoveryMs;
}

// A volley fires at the mark it locked when its windup began; a target that
// has moved more than LockCm from it has broken the lock.
constexpr bool LockHolds(int DeviationCm, int LockCm)
{
    return DeviationCm >= 0 && DeviationCm <= LockCm;
}

// A kneel (or any exposing act) is interrupted once the damage dealt to the
// point it exposes reaches the threshold; a zero threshold never interrupts.
constexpr bool Interrupted(int DamageInWindow, int Threshold)
{
    return Threshold > 0 && DamageInWindow >= Threshold;
}

// A completed assessment stamps a seal; the limit's seal fails the phase.
constexpr bool SealsFail(int Seals, int Limit)
{
    return Limit > 0 && Seals >= Limit;
}

// A mantle, a stun or a flank scales what lands.
constexpr int Taken(int Damage, int TakenPermille)
{
    return Share(Damage, TakenPermille);
}

// Where a blow came from. A rear strike (the rear 120 degrees) takes the
// rear permille; any other off-front strike (outside the front 120 degrees)
// takes the flank permille. FacingMilli is the cosine, x1000, between the
// boss's facing and the direction to the striker.
constexpr int DirectionalPermille(int FacingMilli, int RearPermille, int FlankPermille)
{
    return FacingMilli <= -500 ? RearPermille : FacingMilli < 500 ? FlankPermille : Permille;
}

// A fencer between measures turns frontal arrows and bullets aside: a
// ranged hit within the deflecting arc of his facing while no attack is under way.
constexpr bool Deflects(int FacingMilli, int HalfArcMilli, bool Idle, bool Ranged)
{
    return Idle && Ranged && HalfArcMilli < 1000 && FacingMilli >= HalfArcMilli;
}

// A zone on the floor: marked while its windup and arming delay run, then
// armed for its life (a zero life strikes once and is spent).
enum class EZone { Marked, Armed, Spent };

constexpr EZone ZoneAt(int ElapsedMs, int WindupMs, int ArmMs, int LifeMs)
{
    const int Armed = WindupMs + ArmMs;
    return ElapsedMs < Armed ? EZone::Marked : ElapsedMs < Armed + (LifeMs > 0 ? LifeMs : 1) ? EZone::Armed : EZone::Spent;
}

// A one-shot zone must release on the first observed frame at or after its
// deadline, even if no frame sampled its nominal one-millisecond armed window.
// PreviousArmedMs is the actor's release receipt, not a second clock.
constexpr EZone ObservedZoneAt(int ElapsedMs, int WindupMs, int ArmMs, int LifeMs, int PreviousArmedMs)
{
    if(LifeMs==0&&ElapsedMs>=WindupMs+ArmMs)
        return PreviousArmedMs<0?EZone::Armed:EZone::Spent;
    return ZoneAt(ElapsedMs,WindupMs,ArmMs,LifeMs);
}

// An armed zone's periodic strike: the first when it arms, then every TickMs.
constexpr bool ZoneTick(int ArmedMs, int PreviousArmedMs, int TickMs)
{
    if (ArmedMs < 0)
        return false;
    if (PreviousArmedMs < 0)
        return true;
    return TickMs > 0 && ArmedMs / TickMs > PreviousArmedMs / TickMs;
}

// A ward (an orbiting drone or shard) blocks while closed. One that
// re-indexes opens for OpenMs every EveryMs since it arrived, and again
// right after it blocks a hit.
constexpr bool WardOpen(int SinceSpawnMs, int EveryMs, int OpenMs, int SinceBlockMs, bool OpenAfterBlock)
{
    if (OpenMs <= 0)
        return false;
    if (OpenAfterBlock && SinceBlockMs >= 0 && SinceBlockMs < OpenMs)
        return true;
    return EveryMs > 0 && SinceSpawnMs >= EveryMs && SinceSpawnMs % EveryMs < OpenMs;
}
} // namespace SoraBossRules
