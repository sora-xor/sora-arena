#pragma once
#include "SoraMaaiRules.h"

// Offline chapter beat rules for catalog schema 4, shared by the Unreal
// campaign director and a host-compiled acceptance driver. A chapter is an
// ordered list of at most 32 beats. A beat starts once the earlier beats it
// requires are complete; completing it may restore one of the chapter's three
// production sites and unlock weapons (IDs 0-20), mechanic flags and story
// flags. Optional beats never gate a required one, and a later beat grants any
// optional weapon the player skipped, so every route ends with the same arms.
// Inside a beat a task (FTask, bible §12.2) decides what completes it, which
// waves it releases, how a boss or duel changes phase and what a failure does.
// Time is integer milliseconds, distance integer centimetres and fractions
// permille, so no rule depends on a floating-point frame boundary.
// No wallet, network, or Unreal headers belong here.
namespace SoraBeatRules
{
constexpr int MaxBeats = 32;
constexpr int SiteCount = 3;
constexpr int WeaponCount = 21;
constexpr int MechanicCount = 19;
constexpr int MaxStoryFlags = 16;
constexpr unsigned AllSitesMask = (1u << SiteCount) - 1u;
constexpr unsigned AllWeaponsMask = (1u << WeaponCount) - 1u;
constexpr unsigned AllMechanicsMask = (1u << MechanicCount) - 1u;
constexpr unsigned AllFlagsMask = (1u << MaxStoryFlags) - 1u;

struct FBeat
{
    unsigned RequiresMask;   // earlier beats that must be complete first
    int Site;                // production site restored on completion, or -1
    unsigned WeaponsMask;    // weapons unlocked on completion
    unsigned GrantsMask;     // skipped optional weapons granted on completion
    unsigned MechanicsMask;  // mechanic flags unlocked on completion
    unsigned FlagsMask;      // story flags set on completion, read by later chapters
    bool Optional;
    bool Checkpoint;         // saves at the beat's start
    int PhaseCheckpoints;    // further saves inside a boss or duel, one per later phase
};

// Chapter progress as a checkpoint saves it. The weapon, mechanic and story
// flag masks are cumulative across the campaign; Entry* are their values when
// the chapter began.
struct FProgress
{
    unsigned CompletedMask;
    unsigned SitesMask;
    unsigned WeaponsMask;
    unsigned MechanicsMask;
    unsigned FlagsMask;
    bool Complete;
};

constexpr unsigned BeatBit(int Index)
{
    return Index >= 0 && Index < MaxBeats ? 1u << Index : 0u;
}

constexpr unsigned AllBeatsMask(int Count)
{
    return Count <= 0 || Count > MaxBeats ? 0u : Count == MaxBeats ? ~0u : (1u << Count) - 1u;
}

constexpr unsigned SiteBit(int Site)
{
    return Site >= 0 && Site < SiteCount ? 1u << Site : 0u;
}

constexpr unsigned RequiredBeatsMask(const FBeat* Beats, int Count)
{
    unsigned Mask = 0u;
    for (int Index = 0; Beats && Index < Count && Index < MaxBeats; ++Index)
        if (!Beats[Index].Optional)
            Mask |= BeatBit(Index);
    return Mask;
}

// Unlocks a chapter can add: every beat's when IncludeOptional, else only
// those every route completes (required beats' unlocks and grants).
constexpr unsigned ChapterWeapons(const FBeat* Beats, int Count, bool IncludeOptional)
{
    unsigned Mask = 0u;
    for (int Index = 0; Beats && Index < Count && Index < MaxBeats; ++Index)
        if (IncludeOptional || !Beats[Index].Optional)
            Mask |= Beats[Index].WeaponsMask | Beats[Index].GrantsMask;
    return Mask;
}

constexpr unsigned ChapterMechanics(const FBeat* Beats, int Count)
{
    unsigned Mask = 0u;
    for (int Index = 0; Beats && Index < Count && Index < MaxBeats; ++Index)
        Mask |= Beats[Index].MechanicsMask;
    return Mask;
}

// Story flags a chapter can set; an optional beat's flag may never be set.
constexpr unsigned ChapterFlags(const FBeat* Beats, int Count)
{
    unsigned Mask = 0u;
    for (int Index = 0; Beats && Index < Count && Index < MaxBeats; ++Index)
        Mask |= Beats[Index].FlagsMask;
    return Mask;
}

constexpr bool ChapterValid(const FBeat* Beats, int Count)
{
    if (!Beats || Count <= 0 || Count > MaxBeats || Beats[0].RequiresMask != 0u)
        return false;
    const unsigned Required = RequiredBeatsMask(Beats, Count);
    unsigned Sites = 0u, Weapons = 0u, Mechanics = 0u, Flags = 0u;
    for (int Index = 0; Index < Count; ++Index)
    {
        const FBeat& Beat = Beats[Index];
        const unsigned Site = SiteBit(Beat.Site);
        if ((Beat.RequiresMask & ~AllBeatsMask(Index)) != 0u || (Beat.Site != -1 && Site == 0u) ||
            (Sites & Site) != 0u || (Beat.WeaponsMask & ~AllWeaponsMask) != 0u ||
            (Beat.GrantsMask & ~AllWeaponsMask) != 0u || (Beat.MechanicsMask & ~AllMechanicsMask) != 0u ||
            (Beat.FlagsMask & ~AllFlagsMask) != 0u || (Flags & Beat.FlagsMask) != 0u ||
            (Weapons & Beat.WeaponsMask) != 0u || (Mechanics & Beat.MechanicsMask) != 0u ||
            (Beat.WeaponsMask & Beat.GrantsMask) != 0u || Beat.PhaseCheckpoints < 0)
            return false;
        // Optional beats restore no site, unlock no mechanic and gate no required beat.
        if (Beat.Optional && (Site != 0u || Beat.MechanicsMask != 0u))
            return false;
        if (!Beat.Optional && (Beat.RequiresMask & ~Required) != 0u)
            return false;
        Sites |= Site;
        Weapons |= Beat.WeaponsMask;
        Mechanics |= Beat.MechanicsMask;
        Flags |= Beat.FlagsMask;
    }
    return Sites == AllSitesMask;
}

constexpr bool CanStartBeat(FProgress State, const FBeat* Beats, int Count, int Index)
{
    return Beats && !State.Complete && Index >= 0 && Index < Count && Index < MaxBeats &&
        (State.CompletedMask & BeatBit(Index)) == 0u &&
        (State.CompletedMask & Beats[Index].RequiresMask) == Beats[Index].RequiresMask;
}

constexpr bool CompleteBeat(FProgress& State, const FBeat* Beats, int Count, int Index)
{
    if (!CanStartBeat(State, Beats, Count, Index))
        return false;
    State.CompletedMask |= BeatBit(Index);
    State.SitesMask |= SiteBit(Beats[Index].Site);
    State.WeaponsMask |= Beats[Index].WeaponsMask | Beats[Index].GrantsMask;
    State.MechanicsMask |= Beats[Index].MechanicsMask;
    State.FlagsMask |= Beats[Index].FlagsMask;
    return true;
}

// What the hero may use while beat Active is in play: what the route has
// earned, and what a required beat teaches. A beat's unlocks are learned in
// it (ch02.b03 hands over the yari, ch03.b03 teaches the takedown and the seal
// cut), and completing it keeps them. An optional cache gives its weapons
// only once opened, and a grant that makes up for a skipped cache arrives as
// its beat completes.
constexpr unsigned InPlayWeapons(FProgress State, const FBeat* Beats, int Count, int Active)
{
    return State.WeaponsMask | (CanStartBeat(State, Beats, Count, Active) && !Beats[Active].Optional
        ? Beats[Active].WeaponsMask : 0u);
}

constexpr unsigned InPlayMechanics(FProgress State, const FBeat* Beats, int Count, int Active)
{
    return State.MechanicsMask | (CanStartBeat(State, Beats, Count, Active) && !Beats[Active].Optional
        ? Beats[Active].MechanicsMask : 0u);
}

constexpr bool CanFinishChapter(FProgress State, const FBeat* Beats, int Count)
{
    const unsigned Required = RequiredBeatsMask(Beats, Count);
    return Beats && Required != 0u && (State.CompletedMask & Required) == Required &&
        State.SitesMask == AllSitesMask;
}

constexpr bool FinishChapter(FProgress& State, const FBeat* Beats, int Count)
{
    if (State.Complete || !CanFinishChapter(State, Beats, Count))
        return false;
    State.Complete = true;
    return true;
}

// The first required beat still to play, or -1 once every one is complete.
constexpr int NextBeat(FProgress State, const FBeat* Beats, int Count)
{
    for (int Index = 0; Beats && Index < Count && Index < MaxBeats; ++Index)
        if (!Beats[Index].Optional && (State.CompletedMask & BeatBit(Index)) == 0u)
            return CanStartBeat(State, Beats, Count, Index) ? Index : -1;
    return -1;
}

// A saved state is exactly what completing its beats from the entry masks yields.
constexpr bool ProgressValid(FProgress State, const FBeat* Beats, int Count,
    unsigned EntryWeapons, unsigned EntryMechanics, unsigned EntryFlags)
{
    if (!Beats || Count <= 0 || Count > MaxBeats || (State.CompletedMask & ~AllBeatsMask(Count)) != 0u ||
        (EntryWeapons & ~AllWeaponsMask) != 0u || (EntryMechanics & ~AllMechanicsMask) != 0u ||
        (EntryFlags & ~AllFlagsMask) != 0u)
        return false;
    unsigned Sites = 0u, Weapons = EntryWeapons, Mechanics = EntryMechanics, Flags = EntryFlags;
    for (int Index = 0; Index < Count; ++Index)
    {
        if ((State.CompletedMask & BeatBit(Index)) == 0u)
            continue;
        const FBeat& Beat = Beats[Index];
        if ((State.CompletedMask & Beat.RequiresMask) != Beat.RequiresMask)
            return false;
        Sites |= SiteBit(Beat.Site);
        Weapons |= Beat.WeaponsMask | Beat.GrantsMask;
        Mechanics |= Beat.MechanicsMask;
        Flags |= Beat.FlagsMask;
    }
    return State.SitesMask == Sites && State.WeaponsMask == Weapons && State.MechanicsMask == Mechanics &&
        State.FlagsMask == Flags && (!State.Complete || CanFinishChapter(State, Beats, Count));
}

// A checkpoint is taken at the start of a checkpoint beat (phase 0) or at a
// later phase of a boss or duel that saves per phase, before that beat completes.
constexpr bool CheckpointValid(FProgress State, const FBeat* Beats, int Count,
    unsigned EntryWeapons, unsigned EntryMechanics, unsigned EntryFlags, int Beat, int Phase)
{
    return ProgressValid(State, Beats, Count, EntryWeapons, EntryMechanics, EntryFlags) &&
        CanStartBeat(State, Beats, Count, Beat) && Phase >= 0 &&
        (Phase == 0 ? Beats[Beat].Checkpoint : Phase <= Beats[Beat].PhaseCheckpoints);
}

// Entry masks a chapter accepts: at least every route's unlocks from the
// earlier chapters, at most all of them (chapter select grants the latter).
// Story flags have no route minimum: each may come from an optional beat.
constexpr bool EntryValid(unsigned Entry, unsigned RouteMinimum, unsigned AllEarlier)
{
    return (RouteMinimum & ~Entry) == 0u && (Entry & ~AllEarlier) == 0u;
}

// ---------------------------------------------------------------------------
// Beat tasks. The catalog fills an FTask from a beat's type parameters; the
// director keeps an FTaskState from the beat's start (or a restored phase) and
// feeds it the hero's actions and the world's events. The same functions run
// in the host driver against every authored beat.
// ---------------------------------------------------------------------------
constexpr int Permille = 1000;
constexpr int MaxWaves = 8;
constexpr int MaxPhases = 4;
constexpr int MaxSteps = 8;
// Objectives, pickups, drop-offs and defended targets per beat.
constexpr int MaxPoints = 8;
constexpr int MaxGoalCount = 99;
constexpr int MaxClockMs = 1 << 30;

enum class EType : unsigned char
{
    Cinematic, Dialogue, CombatWave, Duel, StealthZone, ProductionTask, HorsebackRide, Boss, ExploreOptional, Collectible
};
enum class ETask : unsigned char { None, Hold, Crank, Escort, Carry, Manufacture, Defend };
// What completes a beat.
enum class EGoal : unsigned char
{
    Elapsed,      // a cinematic's DurationMs on its own clock, or skipped
    Lines,        // the beat's lines played (then its anchor reached, when AnchorAfterLines)
    WavesCleared, // every wave but a reinforcement released, and every lethal opponent down
    Objectives,   // Count distinct objectives worked
    Survive,      // DurationMs survived
    Points,       // a sparring match: Count points before the rival scores Count
    Lessons,      // a lesson duel: LessonMask's dojo forms, then Count scored bouts
    OpponentDown, // a boss, or a duel fought to its end: the opponent's health reaches zero
    Exit,         // a stealth zone's exit or a ride's destination reached
    Hold,         // DurationMs held in the task's volume
    Turns,        // Count crank turns
    Escort,       // the escorted party covers PathCm
    Deliveries,   // Count items delivered
    Steps,        // every manufacturing step, in order
    Cache,        // an explore beat's cache opened
    Found,        // a collectible picked up
};
enum class EWaveTrigger : unsigned char
{
    Start,       // with the beat
    PrevCleared, // once the wave before it is down
    AliveBelow,  // once the wave before it is out and fewer than Value opponents stand
    AfterMs,     // Value ms into the beat
    ProgressAt,  // at Value permille of the beat's progress
    Volume,      // when the hero enters a named volume; a clearing fight waits for it
    Event,       // on an alarm, detection or scripted event: a reinforcement that may never come
};
struct FWave
{
    EWaveTrigger Trigger = EWaveTrigger::Start;
    int Value = 0;
    // Lethal opponents gate the wave; nonlethal ones (bound conscripts) never count.
    int Lethal = 0;
    int Nonlethal = 0;
};
struct FStep
{
    int Count = 0;
    // A rhythm step: every stroke after the first lands BeatMs after the last, within ToleranceMs.
    int BeatMs = 0;
    int ToleranceMs = 0;
};
enum class EContest : unsigned char { None, Pause, Decay };
// How a boss, or a duel fought to its end, ends (bible §3.2, §8): the
// opponent falls; or, disarmed or yielding, is spared at zero health; or
// yields and is bound by the hero's own hand (a capture).
enum class EDefeat : unsigned char { Kill, Spare, Capture };
// A sparring match's loss policy (duel loss_policy).
enum class ELoss : unsigned char { Checkpoint, Retry, ContinueAfter };
enum class EDetected : unsigned char { Combat, Restart, Reinforce };
enum class EFail : unsigned char
{
    PlayerDied, MatchLost, TargetDestroyed, EscortDown, ConvoyLost, Detected, HorseDown, BossEvent
};
constexpr unsigned FailBit(EFail Event)
{
    return 1u << static_cast<unsigned>(Event);
}
// What a failure does: nothing, the beat goes on (combat after detection, a
// rider on foot), the beat restarts in place (a lost sparring match), the
// latest checkpoint is restored, or the beat completes on its loss branch.
enum class ERetry : unsigned char { None, Continue, RetryBeat, Checkpoint, Advance };

struct FTask
{
    EType Type = EType::Cinematic;
    ETask Task = ETask::None;
    EGoal Goal = EGoal::Elapsed;
    // Lines, objectives, points, bouts, turns or deliveries the goal needs.
    int Count = 0;
    // A cinematic, a hold, or a survival.
    int DurationMs = 0;
    bool Skippable = false;
    // Dialogue that ends at an anchor once its lines have played.
    bool AnchorAfterLines = false;
    // Work under guard (production stealth): progress pauses while a guard sees the hero.
    bool PauseWhenSeen = false;
    int MaxAlive = 6;
    int WaveCount = 0;
    FWave Waves[MaxWaves] = {};
    // Boss or duel phases: the opponent's health (permille) as each begins.
    int PhaseCount = 1;
    int PhaseStart[MaxPhases] = {Permille, 0, 0, 0};
    // How the fight ends at zero health.
    EDefeat Defeat = EDefeat::Kill;
    // A lesson duel's dojo forms, in SoraDojoRules order, the clean
    // repetitions each wants (awase ×2), and whether a bout scores only
    // straight after a 転 flank (ch01.b04).
    unsigned LessonMask = 0u;
    SoraMaaiRules::FConfig Maai;
    int FormReps[4] = {1, 1, 1, 1};
    bool FlankBouts = false;
    ELoss Loss = ELoss::Checkpoint;
    int LossLimit = 0;
    // A hold under contest pauses or decays; decay is permille of the hold per
    // second, or for a crank permille of the turns required per second.
    EContest Contest = EContest::None;
    int DecayPermille = 0;
    // A crank's rate band as turn intervals: faster slips, slower lets it decay.
    int MinTurnMs = 0;
    int MaxTurnMs = 0;
    // Each available named worker contributes this physical turn rate,
    // credited at the authored multiplier (the bellows boy: 40%).
    int CoopCount = 0;
    int CoopMilliTurnsS = 0;
    int CoopProgressPermille = Permille;
    bool CoopSuspendsDecay = false;
    int CoopRetreatCm = 0;
    int RatchetCount = 0;
    int Ratchets[3] = {};
    // Escort: the party's pace, how far the hero may range from it, and its
    // route (0 until the world lays the route out).
    int SpeedCmS = 0;
    int WaitCm = 0;
    int PathCm = 0;
    // Carry or cargo points. Explicit capacities follow the named drop-off
    // order; an absent map (count 0) retains the derived equal ceiling share.
    int Pickups = 0;
    int Dropoffs = 0;
    int DropoffCapacityCount = 0;
    int DropoffCapacities[MaxPoints] = {};
    // Easy, Normal, Hard. The effective policy is chosen when a beat starts,
    // including checkpoint retry/reload, like boss and stealth difficulty.
    bool DropOnHitByDifficulty[3] = {};
    bool DropOnHit = false;
    // A carried load slows the hero to this permille of his pace and leaves
    // only these weapons in hand (the katana in one paw, or nothing).
    int CarrySpeedPermille = Permille;
    unsigned CarryWeaponsMask = 0u;
    // Each load is hoisted at its pickup with Interact held this long (0: taken at once).
    int PickupHoldMs = 0;
    // A sealed store must be pried open before any load can leave it.
    int CarryGateMs = 0;
    // Temporary chapter equipment restriction; recovery is earned at the
    // bottom of a real shaft before any goods can be hoisted.
    unsigned EquipmentMask = (1u << WeaponCount) - 1u;
    unsigned RecoveryWeapons = 0u;
    int RecoveryDepthCm = 0;
    int RecoveryStringMs = 0;
    int RecoveryQuiver = 0;
    int StepCount = 0;
    FStep Steps[MaxSteps] = {};
    int TargetCount = 0;
    int TargetHp[MaxPoints] = {};
    // A defence that may lose some of its targets (ch04.b12's planters) fails
    // at its TargetLossLimit-th loss; 0 or 1: at the first.
    int TargetLossLimit = 0;
    EDetected OnDetected = EDetected::Combat;
    int ReinforceWave = -1;
    // A ride whose horse going down returns to the checkpoint (else the rider goes on foot).
    bool HorseDownRetries = false;
    // Failures the beat's `fail` rows return to the checkpoint.
    unsigned FailMask = 0u;
};

constexpr void ApplyCarryDifficulty(FTask& Task, int Difficulty)
{
    Task.DropOnHit = Task.DropOnHitByDifficulty[Difficulty >= 0 && Difficulty < 3 ? Difficulty : 1];
}

struct FTaskState
{
    int ElapsedMs = 0;
    int Phase = 0;
    // Lines, objectives, points or bouts, turns, deliveries or strokes done.
    int Done = 0;
    // Held or survived ms, crank turns in thousandths, escort distance in
    // thousandths of a cm, or the permille of the way to an exit.
    int Progress = 0;
    int RivalPoints = 0;
    int Losses = 0;
    unsigned Forms = 0u;
    SoraMaaiRules::FState Maai;
    int RecoveryHeldMs = 0;
    bool EquipmentRecovered = false;
    // Clean repetitions of each form still being learned.
    int FormReps[4] = {};
    // Decay not yet worn into progress, in millionths of the hold or of the
    // turns required, so no frame boundary loses a fraction.
    int DecayCarry = 0;
    // Signed fractional crank progress, shared by cooperation and decay.
    int CrankCarry = 0;
    int CrankFloor = 0;
    // A hold worked at a reduced rate (a cupped candle): thousandths of a
    // millisecond not yet counted.
    int RateCarry = 0;
    int Step = 0;
    int StepDone = 0;
    // The last counted crank turn or rhythm stroke, or -1.
    int LastActionMs = -1;
    // Objectives worked, or distinct goods picked up.
    unsigned PointsMask = 0u;
    int CarriedFrom = -1;
    int CarryGateHeldMs = 0;
    bool CarryGateOpen = false;
    unsigned LooseLoads = 0u;
    int LooseFrom[MaxPoints] = {};
    int DropoffUses[MaxPoints] = {};
    unsigned Released = 0u;
    int Down[MaxWaves] = {};
    int TargetHp[MaxPoints] = {};
    // Opponent-milliseconds at each defended target not yet worn into damage.
    int SiegeMs[MaxPoints] = {};
    int OpponentPermille = Permille;
    bool Carrying = false;
    bool LinesDone = false;
    bool Reached = false;
    bool Skipped = false;
    bool Conceded = false;
    // A 転 flank waiting for its bout, and a yielded opponent bound.
    bool Flanked = false;
    bool Captured = false;
};

// One step of the beat clock and where the hero stands.
struct FTick
{
    int DeltaMs = 0;
    // In the hold volume, or within WaitCm of the escorted party.
    bool AtTask = false;
    // An opponent stands in the hold volume.
    bool Contested = false;
    // A guard sees the hero.
    bool Seen = false;
    // The pace a hold fills at, x1000 (a cupped candle copies at half speed).
    int RatePermille = Permille;
    int CrankHelpers = 0;
    // Live physical cutter contact on the lift hawser; ordinary cranks use 1.
    int CrankDecayMultiplier = 1;
};

constexpr int Bits(unsigned Mask)
{
    int Count = 0;
    for (; Mask != 0u; Mask &= Mask - 1u)
        ++Count;
    return Count;
}

constexpr int Ratio(long long Part, long long Whole)
{
    return Whole <= 0 ? 0 : Part >= Whole ? Permille : Part <= 0 ? 0 : static_cast<int>(Part * Permille / Whole);
}

constexpr int TotalLethal(const FTask& Task)
{
    int Total = 0;
    for (int Wave = 0; Wave < Task.WaveCount && Wave < MaxWaves; ++Wave)
        Total += Task.Waves[Wave].Lethal;
    return Total;
}

constexpr int TotalStrokes(const FTask& Task)
{
    int Total = 0;
    for (int Step = 0; Step < Task.StepCount && Step < MaxSteps; ++Step)
        Total += Task.Steps[Step].Count;
    return Total;
}

constexpr bool Released(const FTaskState& State, int Wave)
{
    return Wave >= 0 && Wave < MaxWaves && (State.Released & (1u << Wave)) != 0u;
}

constexpr bool WaveCleared(const FTaskState& State, const FTask& Task, int Wave)
{
    return Released(State, Wave) && Wave < Task.WaveCount && State.Down[Wave] >= Task.Waves[Wave].Lethal;
}

// Released lethal opponents still standing, spawned or waiting to spawn.
constexpr int Alive(const FTaskState& State, const FTask& Task)
{
    int Count = 0;
    for (int Wave = 0; Wave < Task.WaveCount && Wave < MaxWaves; ++Wave)
        if (Released(State, Wave))
            Count += Task.Waves[Wave].Lethal - State.Down[Wave];
    return Count;
}

constexpr int Defeated(const FTaskState& State, const FTask& Task)
{
    int Count = 0;
    for (int Wave = 0; Wave < Task.WaveCount && Wave < MaxWaves; ++Wave)
        Count += State.Down[Wave];
    return Count;
}

constexpr bool ReleasedCleared(const FTaskState& State, const FTask& Task)
{
    for (int Wave = 0; Wave < Task.WaveCount && Wave < MaxWaves; ++Wave)
        if (Released(State, Wave) && !WaveCleared(State, Task, Wave))
            return false;
    return true;
}

constexpr bool RequiredWavesReleased(const FTaskState& State, const FTask& Task)
{
    for (int Wave = 0; Wave < Task.WaveCount && Wave < MaxWaves; ++Wave)
        if (Task.Waves[Wave].Trigger != EWaveTrigger::Event && !Released(State, Wave))
            return false;
    return true;
}

constexpr bool DropoffCapacitiesValid(const FTask& Task)
{
    if (Task.DropoffCapacityCount < 0 || Task.DropoffCapacityCount > MaxPoints) return false;
    if (Task.DropoffCapacityCount > 0 && (Task.Type != EType::ProductionTask || Task.Task != ETask::Carry ||
        Task.Goal != EGoal::Deliveries || Task.Dropoffs != Task.DropoffCapacityCount ||
        Task.Count < 1 || Task.Count > MaxGoalCount)) return false;
    int Total = 0;
    for (int Index = 0; Index < MaxPoints; ++Index)
    {
        const int Capacity = Task.DropoffCapacities[Index];
        if (Index < Task.DropoffCapacityCount)
        {
            if (Capacity < 1 || Capacity > MaxGoalCount) return false;
            Total += Capacity;
        }
        else if (Capacity != 0) return false;
    }
    return Task.DropoffCapacityCount == 0 || Total >= Task.Count;
}

constexpr int DropoffCapacity(const FTask& Task, int Index)
{
    if (Index < 0 || Index >= Task.Dropoffs || Task.Dropoffs > MaxPoints || Task.Count < 1 || Task.Count > MaxGoalCount)
        return 0;
    return Task.DropoffCapacityCount == 0 ? (Task.Count + Task.Dropoffs - 1) / Task.Dropoffs :
        Task.DropoffCapacityCount == Task.Dropoffs ? Task.DropoffCapacities[Index] : 0;
}

constexpr bool DropoffHasRoom(const FTaskState& State, const FTask& Task, int Index)
{
    return Index >= 0 && Index < Task.Dropoffs && Index < MaxPoints && State.Done < Task.Count &&
        State.DropoffUses[Index] < DropoffCapacity(Task, Index);
}

constexpr int ProgressPermille(const FTaskState& State, const FTask& Task)
{
    switch (Task.Goal)
    {
    case EGoal::Elapsed: return State.Skipped ? Permille : Ratio(State.ElapsedMs, Task.DurationMs);
    case EGoal::Lines: return Ratio(State.Done, Task.Count);
    case EGoal::WavesCleared: return Ratio(Defeated(State, Task), TotalLethal(Task));
    case EGoal::Objectives:
    case EGoal::Points:
    case EGoal::Deliveries: return Ratio(State.Done, Task.Count);
    case EGoal::Lessons:
        return Ratio(Bits(State.Forms & Task.LessonMask) + (State.Done < Task.Count ? State.Done : Task.Count) + State.Maai.Done,
            Bits(Task.LessonMask) + Task.Count + Task.Maai.Count);
    case EGoal::Survive:
    case EGoal::Hold: return Ratio(State.Progress, Task.DurationMs);
    case EGoal::OpponentDown: return Permille - (State.OpponentPermille < 0 ? 0 : State.OpponentPermille);
    case EGoal::Turns: return Ratio(State.Progress, static_cast<long long>(Task.Count) * Permille);
    case EGoal::Escort: return Ratio(State.Progress, static_cast<long long>(Task.PathCm) * Permille);
    case EGoal::Steps: return Ratio(State.Done, TotalStrokes(Task));
    case EGoal::Exit: return State.Reached ? Permille : State.Progress;
    case EGoal::Cache:
    case EGoal::Found: return State.Reached ? Permille : 0;
    }
    return 0;
}

constexpr bool GoalMet(const FTaskState& State, const FTask& Task)
{
    switch (Task.Goal)
    {
    case EGoal::Elapsed: return State.Skipped || (Task.DurationMs > 0 && State.ElapsedMs >= Task.DurationMs);
    case EGoal::Lines: return State.LinesDone && (!Task.AnchorAfterLines || State.Reached);
    case EGoal::WavesCleared:
        return Task.WaveCount > 0 && RequiredWavesReleased(State, Task) && ReleasedCleared(State, Task);
    case EGoal::Objectives:
    case EGoal::Points:
    case EGoal::Deliveries: return Task.Count > 0 && State.Done >= Task.Count;
    case EGoal::Lessons:
        return (State.Forms & Task.LessonMask) == Task.LessonMask && State.Done >= Task.Count && SoraMaaiRules::Complete(State.Maai,Task.Maai);
    case EGoal::Survive:
    case EGoal::Hold: return Task.DurationMs > 0 && State.Progress >= Task.DurationMs;
    case EGoal::OpponentDown: return State.OpponentPermille <= 0 && (Task.Defeat != EDefeat::Capture || State.Captured);
    case EGoal::Turns: return Task.Count > 0 && State.Progress >= Task.Count * Permille;
    // An escort without a route (PathCm 0) cannot arrive.
    case EGoal::Escort: return Task.PathCm > 0 && State.Progress >= Task.PathCm * Permille;
    case EGoal::Steps: return Task.StepCount > 0 && State.Step >= Task.StepCount;
    case EGoal::Exit:
    case EGoal::Cache:
    case EGoal::Found: return State.Reached;
    }
    return false;
}

// The beat is done: its goal met, or a lost match conceded on the loss
// branch. Waves are what the beat throws at the hero; only a fight to clear
// them (WavesCleared) waits for its opponents to fall, and those still
// standing when any other goal is met withdraw (bible §12.2, chapter-02 b06).
constexpr bool TaskComplete(const FTaskState& State, const FTask& Task)
{
    return (Task.RecoveryWeapons == 0u || State.EquipmentRecovered) &&
        (Task.CarryGateMs == 0 || State.CarryGateOpen) && (GoalMet(State, Task) || State.Conceded);
}

constexpr int PhaseStartPermille(const FTask& Task, int Phase)
{
    return Phase >= 0 && Phase < Task.PhaseCount && Phase < MaxPhases ? Task.PhaseStart[Phase] : Permille;
}

// A beat's progress at its start, or at a restored boss or duel phase with
// the opponent at that phase's health. Waves come from ReleaseWaves.
constexpr FTaskState StartTask(const FTask& Task, int Phase)
{
    FTaskState State{};
    State.Phase = Phase > 0 && Phase < Task.PhaseCount && Phase < MaxPhases ? Phase : 0;
    State.OpponentPermille = PhaseStartPermille(Task, State.Phase);
    for (int Target = 0; Target < Task.TargetCount && Target < MaxPoints; ++Target)
        State.TargetHp[Target] = Task.TargetHp[Target];
    return State;
}

constexpr bool EarlierReleased(const FTaskState& State, int Wave)
{
    const unsigned Earlier = (1u << Wave) - 1u;
    return (State.Released & Earlier) == Earlier;
}

constexpr bool WaveDue(const FTaskState& State, const FTask& Task, int Wave)
{
    const FWave& Row = Task.Waves[Wave];
    switch (Row.Trigger)
    {
    case EWaveTrigger::Start: return true;
    case EWaveTrigger::PrevCleared: return Wave > 0 && WaveCleared(State, Task, Wave - 1);
    case EWaveTrigger::AliveBelow: return Wave > 0 && Released(State, Wave - 1) && Alive(State, Task) < Row.Value;
    case EWaveTrigger::AfterMs: return State.ElapsedMs >= Row.Value;
    case EWaveTrigger::ProgressAt:
        // In a fight to clear the waves progress only comes from defeats, so
        // once the waves before it are out and down the next one comes rather
        // than leaving the field empty.
        return ProgressPermille(State, Task) >= Row.Value ||
            (Task.Goal == EGoal::WavesCleared && EarlierReleased(State, Wave) && ReleasedCleared(State, Task));
    case EWaveTrigger::Volume:
    case EWaveTrigger::Event: return false;
    }
    return false;
}

// Releases every wave whose trigger now holds; returns the waves newly due.
constexpr unsigned ReleaseWaves(FTaskState& State, const FTask& Task)
{
    unsigned Fresh = 0u;
    for (bool Changed = true; Changed;)
    {
        Changed = false;
        for (int Wave = 0; Wave < Task.WaveCount && Wave < MaxWaves; ++Wave)
            if (!Released(State, Wave) && WaveDue(State, Task, Wave))
            {
                State.Released |= 1u << Wave;
                Fresh |= 1u << Wave;
                Changed = true;
            }
    }
    return Fresh;
}

// A volume the hero entered, or an event, releases its wave.
constexpr bool ReleaseWave(FTaskState& State, const FTask& Task, int Wave)
{
    if (Wave < 0 || Wave >= Task.WaveCount || Wave >= MaxWaves || Released(State, Wave) ||
        (Task.Waves[Wave].Trigger != EWaveTrigger::Volume && Task.Waves[Wave].Trigger != EWaveTrigger::Event))
        return false;
    State.Released |= 1u << Wave;
    return true;
}

// Wears Ms of decay off a hold or a crank: DecayPermille of Whole (the
// hold's time, or the turns required in thousandths) a second. The fraction
// of a unit below the loss carries to the next step, so the same slack costs
// the same progress whatever the frame rate.
constexpr long long DecayUnit = 1000LL * Permille;
constexpr void Decay(FTaskState& State, const FTask& Task, long long Whole, int Ms)
{
    const long long Total = State.DecayCarry + static_cast<long long>(Task.DecayPermille) * Whole * Ms;
    const long long Loss = Total / DecayUnit;
    State.DecayCarry = static_cast<int>(Total - Loss * DecayUnit);
    State.Progress = State.Progress > Loss ? State.Progress - static_cast<int>(Loss) : 0;
}

// A reached pawl never releases until the whole task retries.
constexpr void LatchCrank(FTaskState& State, const FTask& Task)
{
    for (int Index = 0; Index < Task.RatchetCount && Index < 3; ++Index)
    {
        const int Floor = Task.Count * Task.Ratchets[Index];
        if (State.Progress >= Floor && Floor > State.CrankFloor) State.CrankFloor = Floor;
    }
}

// Advances the beat clock: holds fill while the hero stands in them, a crank
// slips back once he stops, the escorted party walks while he keeps up, and a
// survival counts down. A completed task no longer moves.
constexpr bool Tick(FTaskState& State, const FTask& Task, FTick Step)
{
    if (Step.DeltaMs <= 0 || TaskComplete(State, Task))
        return false;
    const int Before = State.ElapsedMs;
    const int Clamped = Step.DeltaMs > 60000 ? 60000 : Step.DeltaMs;
    State.ElapsedMs = State.ElapsedMs > MaxClockMs - Clamped ? MaxClockMs : State.ElapsedMs + Clamped;
    const int Delta = State.ElapsedMs - Before;
    const bool Watched = Task.PauseWhenSeen && Step.Seen;
    switch (Task.Goal)
    {
    case EGoal::Survive:
        State.Progress = State.Progress + Delta > Task.DurationMs ? Task.DurationMs : State.Progress + Delta;
        break;
    case EGoal::Hold:
        if (Step.Contested && Task.Contest == EContest::Decay)
            Decay(State, Task, Task.DurationMs, Delta);
        else if (Step.AtTask && !Watched && !(Step.Contested && Task.Contest == EContest::Pause))
        {
            // At a reduced pace the fraction of a millisecond carries to the next step.
            const long long Paced = State.RateCarry + static_cast<long long>(Delta) *
                (Step.RatePermille < 0 ? 0 : Step.RatePermille > Permille ? Permille : Step.RatePermille);
            const int Filled = static_cast<int>(Paced / Permille);
            State.RateCarry = static_cast<int>(Paced - static_cast<long long>(Filled) * Permille);
            State.Progress = State.Progress + Filled > Task.DurationMs ? Task.DurationMs : State.Progress + Filled;
        }
        break;
    case EGoal::Turns:
        if (State.LastActionMs >= 0)
        {
            const int Slack = State.ElapsedMs - State.LastActionMs - Task.MaxTurnMs;
            const int DecayMs = Slack <= 0 || (Step.CrankHelpers > 0 && Task.CoopSuspendsDecay) ? 0 : Slack < Delta ? Slack : Delta;
            const int Helpers = Step.CrankHelpers < 0 ? 0 : Step.CrankHelpers > Task.CoopCount ? Task.CoopCount : Step.CrankHelpers;
            const int DecayMultiplier=Step.CrankDecayMultiplier<1?1:Step.CrankDecayMultiplier>3?3:Step.CrankDecayMultiplier;
            const long long Total = State.CrankCarry + static_cast<long long>(Delta) * Helpers * Task.CoopMilliTurnsS * Task.CoopProgressPermille -
                static_cast<long long>(Task.DecayPermille) * Task.Count * Permille * DecayMs * DecayMultiplier;
            const int Change = static_cast<int>(Total / DecayUnit);
            State.CrankCarry = static_cast<int>(Total - static_cast<long long>(Change) * DecayUnit);
            State.Progress += Change;
            if (State.Progress <= State.CrankFloor && Total < 0) { State.Progress = State.CrankFloor; State.CrankCarry = 0; }
            if (State.Progress >= Task.Count * Permille) { State.Progress = Task.Count * Permille; State.CrankCarry = 0; }
            LatchCrank(State, Task);
            State.Done = State.Progress / Permille;
        }
        break;
    case EGoal::Escort:
        if (Step.AtTask && !Watched && Task.PathCm > 0)
        {
            const long long Walked = State.Progress + static_cast<long long>(Task.SpeedCmS) * Delta;
            const long long Route = static_cast<long long>(Task.PathCm) * Permille;
            State.Progress = static_cast<int>(Walked > Route ? Route : Walked);
        }
        break;
    default:
        break;
    }
    return true;
}

// The crank has gone slack: the hero stopped for longer than its slowest turn.
constexpr bool CrankSlipping(const FTaskState& State, const FTask& Task)
{
    return Task.Goal == EGoal::Turns && State.LastActionMs >= 0 && !GoalMet(State, Task) &&
        State.ElapsedMs - State.LastActionMs > Task.MaxTurnMs;
}

constexpr bool Skip(FTaskState& State, const FTask& Task)
{
    if (Task.Goal != EGoal::Elapsed || !Task.Skippable || GoalMet(State, Task))
        return false;
    State.Skipped = true;
    return true;
}

constexpr bool FinishLines(FTaskState& State, const FTask& Task)
{
    if (Task.Goal != EGoal::Lines || State.LinesDone)
        return false;
    State.LinesDone = true;
    State.Done = Task.Count;
    return true;
}

// How far along the way to an exit or destination the hero has come, in
// permille; it never falls, and only Reach completes the way.
constexpr bool Travel(FTaskState& State, const FTask& Task, int WayPermille)
{
    const int Way = WayPermille < 0 ? 0 : WayPermille >= Permille ? Permille - 1 : WayPermille;
    if (Task.Goal != EGoal::Exit || State.Reached || Way <= State.Progress)
        return false;
    State.Progress = Way;
    return true;
}

// The hero reached the exit or destination, or a dialogue's closing anchor after its lines.
constexpr bool Reach(FTaskState& State, const FTask& Task)
{
    const bool Arrives = Task.Goal == EGoal::Exit || (Task.Goal == EGoal::Lines && Task.AnchorAfterLines && State.LinesDone);
    if (!Arrives || State.Reached)
        return false;
    State.Reached = true;
    return true;
}

// A lethal opponent of Wave went down.
constexpr bool RecordDefeat(FTaskState& State, const FTask& Task, int Wave)
{
    if (!Released(State, Wave) || Wave >= Task.WaveCount || State.Down[Wave] >= Task.Waves[Wave].Lethal)
        return false;
    ++State.Down[Wave];
    return true;
}

enum class EPoint : unsigned char { Refused, Scored, Won, Lost };

// A sparring point to the hero or the rival, or a scored lesson bout (only
// once the lesson's forms are learned, and where the lesson teaches 転 only
// straight after a flank).
constexpr EPoint ScorePoint(FTaskState& State, const FTask& Task, bool Player)
{
    if (GoalMet(State, Task) || State.Conceded)
        return EPoint::Refused;
    if (Task.Goal == EGoal::Lessons)
    {
        if (!Player || (State.Forms & Task.LessonMask) != Task.LessonMask || (Task.FlankBouts && !State.Flanked))
            return EPoint::Refused;
        State.Flanked = false;
        ++State.Done;
        return State.Done >= Task.Count ? EPoint::Won : EPoint::Scored;
    }
    if (Task.Goal != EGoal::Points || State.RivalPoints >= Task.Count)
        return EPoint::Refused;
    if (Player)
    {
        ++State.Done;
        return State.Done >= Task.Count ? EPoint::Won : EPoint::Scored;
    }
    ++State.RivalPoints;
    return State.RivalPoints >= Task.Count ? EPoint::Lost : EPoint::Scored;
}

// Dojo forms (SoraDojoRules) learned so far; only the lesson's own count.
constexpr bool RecordForms(FTaskState& State, const FTask& Task, unsigned Forms)
{
    const unsigned Fresh = Forms & Task.LessonMask & ~State.Forms;
    if (Task.Goal != EGoal::Lessons || Fresh == 0u)
        return false;
    State.Forms |= Fresh;
    return true;
}

// One clean repetition of a form the lesson teaches and has yet to learn;
// true once the form has its repetitions (awase ×2) and may be learned.
constexpr bool RepeatForm(FTaskState& State, const FTask& Task, int Form)
{
    if (Task.Goal != EGoal::Lessons || Form < 0 || Form > 3 || (Task.LessonMask & (1u << Form)) == 0u ||
        (State.Forms & (1u << Form)) != 0u)
        return false;
    if (State.FormReps[Form] < Task.FormReps[Form])
        ++State.FormReps[Form];
    return State.FormReps[Form] >= Task.FormReps[Form];
}

// A 転 step to the opponent's flank straight after an awase, which the next
// scored bout of a lesson that teaches it spends.
constexpr bool RecordFlank(FTaskState& State, const FTask& Task)
{
    if (Task.Goal != EGoal::Lessons || !Task.FlankBouts || State.Flanked || GoalMet(State, Task) ||
        (State.Forms & Task.LessonMask) != Task.LessonMask)
        return false;
    State.Flanked = true;
    return true;
}

// The opponent's health as a permille of its maximum; it only falls. True
// when a later phase begins.
constexpr bool OpponentHealth(FTaskState& State, const FTask& Task, int HealthPermille)
{
    if (Task.Goal != EGoal::OpponentDown)
        return false;
    const int Health = HealthPermille < 0 ? 0 : HealthPermille > Permille ? Permille : HealthPermille;
    if (Health < State.OpponentPermille)
        State.OpponentPermille = Health;
    const int Before = State.Phase;
    while (State.Phase + 1 < Task.PhaseCount && State.Phase + 1 < MaxPhases &&
        State.OpponentPermille <= Task.PhaseStart[State.Phase + 1])
        ++State.Phase;
    return State.Phase != Before;
}

// A capture's opponent has yielded at zero health and waits for the hero.
constexpr bool AwaitsCapture(const FTaskState& State, const FTask& Task)
{
    return Task.Goal == EGoal::OpponentDown && Task.Defeat == EDefeat::Capture && State.OpponentPermille <= 0 &&
        !State.Captured;
}

// The hero binds the yielded opponent (the vault's bulkhead, the engine's spine).
constexpr bool Capture(FTaskState& State, const FTask& Task)
{
    if (!AwaitsCapture(State, Task))
        return false;
    State.Captured = true;
    return true;
}

constexpr bool WorkObjective(FTaskState& State, const FTask& Task, int Index)
{
    if (Task.Goal != EGoal::Objectives || Index < 0 || Index >= Task.Count || Index >= MaxPoints ||
        (State.PointsMask & (1u << Index)) != 0u)
        return false;
    State.PointsMask |= 1u << Index;
    ++State.Done;
    return true;
}

enum class ETurn : unsigned char { Refused, TooFast, InBand, Slow };

// One crank turn. A turn faster than the band slips and restarts the rhythm,
// so hammering the crank never counts.
constexpr ETurn Turn(FTaskState& State, const FTask& Task)
{
    if (Task.Goal != EGoal::Turns || GoalMet(State, Task))
        return ETurn::Refused;
    const int Since = State.LastActionMs < 0 ? -1 : State.ElapsedMs - State.LastActionMs;
    State.LastActionMs = State.ElapsedMs;
    if (Since >= 0 && Since < Task.MinTurnMs)
        return ETurn::TooFast;
    const int Full = Task.Count * Permille;
    State.Progress = State.Progress + Permille > Full ? Full : State.Progress + Permille;
    LatchCrank(State, Task);
    State.Done = State.Progress / Permille;
    return Since > Task.MaxTurnMs ? ETurn::Slow : ETurn::InBand;
}

constexpr bool EquipmentReady(const FTaskState& State, const FTask& Task)
{
    return Task.RecoveryWeapons == 0u || State.EquipmentRecovered;
}
constexpr bool EquipmentAllows(const FTaskState& State, const FTask& Task, int Weapon)
{
    return Weapon >= 0 && Weapon < WeaponCount &&
        (State.EquipmentRecovered || (Task.EquipmentMask & (1u << Weapon)) != 0u);
}
// Stringing must be continuous, at the bundle. Leaving it or releasing
// Interact loses partial work; the completed pickup is raised exactly once.
constexpr bool RecoverEquipment(FTaskState& State, const FTask& Task, int DeltaMs, bool AtBundle, bool Held)
{
    if (EquipmentReady(State, Task)) return false;
    if (!AtBundle || !Held) { State.RecoveryHeldMs = 0; return false; }
    if (DeltaMs <= 0) return false;
    State.RecoveryHeldMs = DeltaMs >= Task.RecoveryStringMs - State.RecoveryHeldMs ? Task.RecoveryStringMs : State.RecoveryHeldMs + DeltaMs;
    if (State.RecoveryHeldMs < Task.RecoveryStringMs) return false;
    State.EquipmentRecovered = true;
    return true;
}

constexpr bool CarryGateReady(const FTaskState& State, const FTask& Task)
{
    return Task.CarryGateMs == 0 || State.CarryGateOpen;
}
// The authored contest is pause: a hit, releasing Interact or leaving the
// seal stops work without erasing it. Only checkpoint retry resets it.
constexpr bool PryCarryGate(FTaskState& State, const FTask& Task, int DeltaMs, bool AtSeal, bool Held, bool Hit)
{
    if (Task.Task != ETask::Carry || CarryGateReady(State,Task) || DeltaMs <= 0 || !AtSeal || !Held || Hit) return false;
    State.CarryGateHeldMs = DeltaMs >= Task.CarryGateMs - State.CarryGateHeldMs ? Task.CarryGateMs : State.CarryGateHeldMs + DeltaMs;
    if (State.CarryGateHeldMs < Task.CarryGateMs) return false;
    State.CarryGateOpen = true;
    return true;
}

// Takes an item at a pickup. Distinct goods (a pickup per item) are each
// taken once; a single store is revisited.
constexpr bool Pickup(FTaskState& State, const FTask& Task, int Index)
{
    if (!EquipmentReady(State, Task) || !CarryGateReady(State, Task) || Task.Task != ETask::Carry || State.Carrying ||
        State.Done + Bits(State.LooseLoads) >= Task.Count || Index < 0 ||
        Index >= Task.Pickups || Index >= MaxPoints)
        return false;
    if (Task.Pickups >= Task.Count)
    {
        if ((State.PointsMask & (1u << Index)) != 0u)
            return false;
        State.PointsMask |= 1u << Index;
    }
    State.Carrying = true;
    State.CarriedFrom = Index;
    return true;
}

// A manual set-down keeps the item out of its store and remembers its
// original source. The world owns the reachable position for each slot.
constexpr int SetDownCarried(FTaskState& State, const FTask& Task)
{
    if (Task.Task != ETask::Carry || !CarryGateReady(State,Task) || !State.Carrying) return -1;
    for (int Slot = 0; Slot < MaxPoints; ++Slot)
        if ((State.LooseLoads & (1u << Slot)) == 0u)
        {
            State.LooseLoads |= 1u << Slot;
            State.LooseFrom[Slot] = State.CarriedFrom;
            State.CarriedFrom = -1; State.Carrying = false;
            return Slot;
        }
    return -1;
}
constexpr bool PickupLoose(FTaskState& State, const FTask& Task, int Slot)
{
    if (Task.Task != ETask::Carry || !EquipmentReady(State,Task) || !CarryGateReady(State,Task) || State.Carrying || State.Done>=Task.Count ||
        Slot < 0 || Slot >= MaxPoints || (State.LooseLoads & (1u << Slot)) == 0u) return false;
    State.CarriedFrom = State.LooseFrom[Slot];
    State.LooseLoads &= ~(1u << Slot);
    State.Carrying = true;
    return true;
}

// Delivers the carried item, or a ride's cargo, at a drop-off with room left.
constexpr bool Deliver(FTaskState& State, const FTask& Task, int Index)
{
    if (!DropoffHasRoom(State, Task, Index))
        return false;
    if (Task.Task == ETask::Carry)
    {
        if (!CarryGateReady(State,Task) || !State.Carrying)
            return false;
        State.Carrying = false;
        State.CarriedFrom = -1;
    }
    else if (Task.Type != EType::HorsebackRide || Task.Goal != EGoal::Deliveries)
        return false;
    ++State.DropoffUses[Index];
    ++State.Done;
    return true;
}

// A hit knocks the carried item loose; it returns to its pickup.
constexpr bool DropCarried(FTaskState& State, const FTask& Task)
{
    if (Task.Task != ETask::Carry || !Task.DropOnHit || !State.Carrying)
        return false;
    if (Task.Pickups >= Task.Count && State.CarriedFrom >= 0)
        State.PointsMask &= ~(1u << State.CarriedFrom);
    State.Carrying = false;
    State.CarriedFrom = -1;
    return true;
}

enum class EStroke : unsigned char { Refused, Counted, Missed, StepDone, Finished };

// One stroke at the current manufacturing step. Off the beat, a rhythm step
// starts again from that stroke (pass or fail, no quality grades).
constexpr EStroke Stroke(FTaskState& State, const FTask& Task)
{
    if (Task.Goal != EGoal::Steps || State.Step >= Task.StepCount || State.Step >= MaxSteps)
        return EStroke::Refused;
    const FStep& Current = Task.Steps[State.Step];
    if (Current.BeatMs > 0 && State.StepDone > 0)
    {
        const int Off = State.ElapsedMs - State.LastActionMs - Current.BeatMs;
        if (Off > Current.ToleranceMs || Off < -Current.ToleranceMs)
        {
            State.Done -= State.StepDone - 1;
            State.StepDone = 1;
            State.LastActionMs = State.ElapsedMs;
            return EStroke::Missed;
        }
    }
    State.LastActionMs = State.ElapsedMs;
    ++State.StepDone;
    ++State.Done;
    if (State.StepDone < Current.Count)
        return EStroke::Counted;
    ++State.Step;
    State.StepDone = 0;
    State.LastActionMs = -1;
    return State.Step >= Task.StepCount ? EStroke::Finished : EStroke::StepDone;
}

// Damage to a defended target; true when it is destroyed by this hit.
constexpr bool DamageTarget(FTaskState& State, const FTask& Task, int Index, int Hp)
{
    if (Index < 0 || Index >= Task.TargetCount || Index >= MaxPoints || Hp <= 0 || State.TargetHp[Index] <= 0)
        return false;
    State.TargetHp[Index] = State.TargetHp[Index] > Hp ? State.TargetHp[Index] - Hp : 0;
    return State.TargetHp[Index] == 0;
}

// Defended targets destroyed so far.
constexpr int TargetsLost(const FTaskState& State, const FTask& Task)
{
    int Lost = 0;
    for (int Target = 0; Target < Task.TargetCount && Target < MaxPoints; ++Target)
        Lost += State.TargetHp[Target] <= 0;
    return Lost;
}

// Opponents standing at a defended target wear it down: SiegeHpPerSecond
// for each of them, carried in whole opponent-milliseconds so no frame
// boundary loses a fraction. Returns the damage to deal now.
constexpr int SiegeRadiusCm = 700;
constexpr int SiegeHpPerSecond = 5;
constexpr int SiegeMsPerHp = 1000 / SiegeHpPerSecond;
constexpr int SiegeDamage(FTaskState& State, const FTask& Task, int Index, int Attackers, int DeltaMs)
{
    if (Index < 0 || Index >= Task.TargetCount || Index >= MaxPoints || Attackers <= 0 || DeltaMs <= 0 ||
        State.TargetHp[Index] <= 0)
        return 0;
    const int Delta = DeltaMs > 60000 ? 60000 : DeltaMs;
    const long long Total = State.SiegeMs[Index] + static_cast<long long>(Attackers > MaxGoalCount ? MaxGoalCount : Attackers) * Delta;
    const long long Damage = Total / SiegeMsPerHp;
    State.SiegeMs[Index] = static_cast<int>(Total - Damage * SiegeMsPerHp);
    return static_cast<int>(Damage > State.TargetHp[Index] ? State.TargetHp[Index] : Damage);
}

// Repairs a damaged, standing target up to its authored health.
constexpr bool RepairTarget(FTaskState& State, const FTask& Task, int Index, int Hp)
{
    if (Index < 0 || Index >= Task.TargetCount || Index >= MaxPoints || Hp <= 0 || State.TargetHp[Index] <= 0 ||
        State.TargetHp[Index] >= Task.TargetHp[Index])
        return false;
    State.TargetHp[Index] = State.TargetHp[Index] + Hp > Task.TargetHp[Index] ? Task.TargetHp[Index] : State.TargetHp[Index] + Hp;
    return true;
}

constexpr bool OpenCache(FTaskState& State, const FTask& Task)
{
    if (Task.Goal != EGoal::Cache || State.Reached)
        return false;
    State.Reached = true;
    return true;
}

constexpr bool Find(FTaskState& State, const FTask& Task)
{
    if (Task.Goal != EGoal::Found || State.Reached)
        return false;
    State.Reached = true;
    return true;
}

// What a failure does to the beat. A sparring bout lost is the rival's
// point, and a lost match follows the duel's loss policy; detection follows
// the zone's on_detected; a horse going down follows on_horse_down; the
// beat's `fail` rows return to the checkpoint. A hero who falls in any other
// beat returns to the latest checkpoint.
constexpr ERetry Fail(FTaskState& State, const FTask& Task, EFail Event)
{
    switch (Event)
    {
    case EFail::PlayerDied:
        if (Task.Goal == EGoal::Points)
            return ScorePoint(State, Task, false) == EPoint::Lost ? Fail(State, Task, EFail::MatchLost) : ERetry::Continue;
        if (Task.Goal == EGoal::Lessons && Task.Loss == ELoss::Retry)
            return ERetry::RetryBeat;
        return ERetry::Checkpoint;
    case EFail::MatchLost:
        if (Task.Goal != EGoal::Points || State.RivalPoints < Task.Count || State.Conceded)
            return ERetry::None;
        ++State.Losses;
        if (Task.Loss == ELoss::ContinueAfter && State.Losses >= Task.LossLimit)
        {
            State.Conceded = true;
            return ERetry::Advance;
        }
        return Task.Loss == ELoss::Checkpoint ? ERetry::Checkpoint : ERetry::RetryBeat;
    case EFail::Detected:
        if (Task.Type != EType::StealthZone && !Task.PauseWhenSeen)
            return ERetry::None;
        if (Task.OnDetected == EDetected::Restart)
            return ERetry::Checkpoint;
        if (Task.OnDetected == EDetected::Reinforce)
            ReleaseWave(State, Task, Task.ReinforceWave);
        return ERetry::Continue;
    case EFail::HorseDown:
        if (Task.Type != EType::HorsebackRide)
            return ERetry::None;
        return Task.HorseDownRetries ? ERetry::Checkpoint : ERetry::Continue;
    case EFail::TargetDestroyed:
        if ((Task.FailMask & FailBit(Event)) == 0u)
            return ERetry::None;
        return Task.TargetLossLimit <= 1 || TargetsLost(State, Task) >= Task.TargetLossLimit ? ERetry::Checkpoint : ERetry::Continue;
    default:
        return (Task.FailMask & FailBit(Event)) != 0u ? ERetry::Checkpoint : ERetry::None;
    }
}

// The beat played again in place after a lost match: fresh progress, with the
// match's losses and the forms already learned kept.
constexpr FTaskState RetryTask(const FTaskState& State, const FTask& Task)
{
    FTaskState Next = StartTask(Task, 0);
    Next.Losses = State.Losses;
    Next.Forms = State.Forms;
    return Next;
}

// Only a boss, or a duel fought to its end, saves at a later phase.
constexpr bool TaskCheckpointValid(const FTask& Task, int Phase)
{
    return DropoffCapacitiesValid(Task) && (Phase == 0 || ((Task.Type == EType::Boss || Task.Type == EType::Duel) &&
        Task.Goal == EGoal::OpponentDown && Phase > 0 && Phase < Task.PhaseCount));
}

constexpr bool WavesValid(const FTask& Task)
{
    if (Task.WaveCount < 0 || Task.WaveCount > MaxWaves || (Task.WaveCount > 0 && Task.MaxAlive < 1))
        return false;
    for (int Wave = 0; Wave < Task.WaveCount; ++Wave)
    {
        const FWave& Row = Task.Waves[Wave];
        if (Row.Lethal < 0 || Row.Nonlethal < 0 || Row.Lethal + Row.Nonlethal < 1 ||
            (Row.Trigger == EWaveTrigger::PrevCleared && Wave == 0) ||
            (Row.Trigger == EWaveTrigger::AliveBelow && (Wave == 0 || Row.Value < 1)) ||
            (Row.Trigger == EWaveTrigger::AfterMs && Row.Value < 0) ||
            (Row.Trigger == EWaveTrigger::ProgressAt && (Row.Value < 0 || Row.Value > Permille)))
            return false;
    }
    return Task.ReinforceWave == -1 || (Task.ReinforceWave >= 0 && Task.ReinforceWave < Task.WaveCount &&
        Task.Waves[Task.ReinforceWave].Trigger == EWaveTrigger::Event);
}

constexpr bool PhasesValid(const FTask& Task)
{
    if (Task.PhaseCount < 1 || Task.PhaseCount > MaxPhases || Task.PhaseStart[0] != Permille ||
        (Task.PhaseCount > 1 && Task.Goal != EGoal::OpponentDown))
        return false;
    for (int Phase = 1; Phase < Task.PhaseCount; ++Phase)
        if (Task.PhaseStart[Phase] <= 0 || Task.PhaseStart[Phase] >= Task.PhaseStart[Phase - 1])
            return false;
    return true;
}

constexpr bool StepsValid(const FTask& Task)
{
    if (Task.StepCount < 1 || Task.StepCount > MaxSteps)
        return false;
    for (int Step = 0; Step < Task.StepCount; ++Step)
    {
        const FStep& Row = Task.Steps[Step];
        if (Row.Count < 1 || Row.Count > MaxGoalCount || Row.BeatMs < 0 || Row.ToleranceMs < 0 ||
            (Row.BeatMs == 0 && Row.ToleranceMs != 0) || (Row.BeatMs > 0 && Row.ToleranceMs >= Row.BeatMs))
            return false;
    }
    return true;
}

constexpr bool TargetsValid(const FTask& Task)
{
    if (Task.TargetCount < 0 || Task.TargetCount > MaxPoints || Task.TargetLossLimit < 0 ||
        Task.TargetLossLimit > Task.TargetCount)
        return false;
    for (int Target = 0; Target < Task.TargetCount; ++Target)
        if (Task.TargetHp[Target] <= 0)
            return false;
    return true;
}

constexpr bool PointsValid(int Count)
{
    return Count > 0 && Count <= MaxPoints;
}

// An authored task: its goal belongs to its type, and every count, clock,
// wave, phase and step can be met.
constexpr bool TaskValid(const FTask& Task)
{
    if (!DropoffCapacitiesValid(Task)) return false;
    if (Task.CarryGateMs < 0 || Task.CarryGateMs > MaxClockMs || (Task.CarryGateMs > 0 && Task.Task != ETask::Carry)) return false;
    if (Task.CoopCount < 0 || Task.CoopCount > 3 || ((Task.CoopCount == 0) != (Task.CoopMilliTurnsS == 0)) ||
        (Task.CoopCount == 0 && (Task.CoopSuspendsDecay || Task.CoopRetreatCm > 0)) ||
        Task.CoopMilliTurnsS < 0 || Task.CoopMilliTurnsS > 10000 || Task.CoopProgressPermille <= 0 || Task.CoopProgressPermille > Permille ||
        Task.CoopRetreatCm < 0 || Task.CoopRetreatCm > 10000 || Task.RatchetCount < 0 || Task.RatchetCount > 3 ||
        ((Task.CoopMilliTurnsS > 0 || Task.RatchetCount > 0 || Task.CoopSuspendsDecay || Task.CoopRetreatCm > 0) && Task.Task != ETask::Crank)) return false;
    for (int Index = 0; Index < Task.RatchetCount; ++Index)
        if (Task.Ratchets[Index] <= 0 || Task.Ratchets[Index] >= Permille || (Index > 0 && Task.Ratchets[Index] <= Task.Ratchets[Index-1])) return false;
    const unsigned AllWeapons = (1u << WeaponCount) - 1u;
    if (Task.EquipmentMask == 0u || (Task.EquipmentMask & ~AllWeapons) != 0u) return false;
    if (Task.RecoveryWeapons != 0u)
    {
        if (Task.Task != ETask::Carry || Task.RecoveryWeapons != ((1u << 0) | (1u << 4) | (1u << 18)) ||
            Task.EquipmentMask != (1u << 4) || Task.RecoveryDepthCm != 700 || Task.RecoveryStringMs != 3000 || Task.RecoveryQuiver != 12) return false;
    }
    else if (Task.RecoveryDepthCm != 0 || Task.RecoveryStringMs != 0 || Task.RecoveryQuiver != 0) return false;
    if (!SoraMaaiRules::Valid(Task.Maai) || (Task.Maai.Count > 0 &&
        (Task.Type != EType::Duel || Task.Goal != EGoal::Lessons || Task.LessonMask != 1u || Task.Count != 0))) return false;
    if (!WavesValid(Task) || !PhasesValid(Task) || Task.Count < 0 || Task.Count > MaxGoalCount ||
        Task.DurationMs < 0 || Task.DurationMs > MaxClockMs || Task.DecayPermille < 0 ||
        Task.DecayPermille > Permille || (Task.Task != ETask::None) != (Task.Type == EType::ProductionTask) ||
        (Task.Defeat != EDefeat::Kill && Task.Goal != EGoal::OpponentDown) ||
        (Task.FlankBouts && (Task.Goal != EGoal::Lessons || Task.Count < 1)))
        return false;
    for (int Form = 0; Form < 4; ++Form)
        if (Task.FormReps[Form] < 1 || Task.FormReps[Form] > MaxGoalCount ||
            (Task.FormReps[Form] > 1 && (Task.Goal != EGoal::Lessons || (Task.LessonMask & (1u << Form)) == 0u)))
            return false;
    const bool NoWaves = Task.WaveCount == 0;
    switch (Task.Type)
    {
    case EType::Cinematic: return Task.Goal == EGoal::Elapsed && Task.DurationMs > 0 && NoWaves;
    case EType::Dialogue: return Task.Goal == EGoal::Lines && Task.Count > 0 && NoWaves;
    case EType::CombatWave:
        return !NoWaves && (Task.Goal == EGoal::WavesCleared ? TotalLethal(Task) > 0 :
            Task.Goal == EGoal::Objectives ? PointsValid(Task.Count) :
            Task.Goal == EGoal::Survive && Task.DurationMs > 0);
    case EType::Duel:
        return NoWaves && (Task.Goal == EGoal::Points ? Task.Count > 0 && (Task.Loss != ELoss::ContinueAfter || Task.LossLimit > 0) :
            Task.Goal == EGoal::Lessons ? (Task.LessonMask & ~0x0fu) == 0u && (Task.LessonMask != 0u || Task.Count > 0) :
            Task.Goal == EGoal::OpponentDown);
    case EType::StealthZone:
        return Task.Goal == EGoal::Exit || (Task.Goal == EGoal::Objectives && PointsValid(Task.Count));
    case EType::ProductionTask:
        switch (Task.Task)
        {
        case ETask::Hold: return Task.Goal == EGoal::Hold && Task.DurationMs > 0;
        case ETask::Crank:
            return Task.Goal == EGoal::Turns && Task.Count > 0 && Task.MinTurnMs > 0 && Task.MinTurnMs <= Task.MaxTurnMs;
        case ETask::Escort: return Task.Goal == EGoal::Escort && Task.SpeedCmS > 0 && Task.WaitCm > 0 && Task.PathCm >= 0;
        case ETask::Carry:
            return Task.Goal == EGoal::Deliveries && Task.Count > 0 && PointsValid(Task.Pickups) && PointsValid(Task.Dropoffs) &&
                Task.CarrySpeedPermille > 0 && Task.CarrySpeedPermille <= Permille && (Task.CarryWeaponsMask & ~1u) == 0u;
        case ETask::Manufacture: return Task.Goal == EGoal::Steps && StepsValid(Task);
        case ETask::Defend:
            return TargetsValid(Task) && (Task.Goal == EGoal::Survive ? Task.DurationMs > 0 :
                Task.Goal == EGoal::WavesCleared && TotalLethal(Task) > 0);
        case ETask::None: return false;
        }
        return false;
    case EType::HorsebackRide:
        return Task.Goal == EGoal::Exit ||
            (Task.Goal == EGoal::Deliveries && PointsValid(Task.Dropoffs) && Task.Count == Task.Dropoffs);
    case EType::Boss: return Task.Goal == EGoal::OpponentDown && NoWaves;
    case EType::ExploreOptional: return Task.Goal == EGoal::Cache && NoWaves;
    case EType::Collectible: return Task.Goal == EGoal::Found && NoWaves;
    }
    return false;
}

// A chapter's gates and tasks together: it opens on a cinematic, every task
// is valid, only explore and collectible beats are optional (and every
// explore beat is), and only a boss or duel with phases saves per phase.
constexpr bool TasksValid(const FBeat* Beats, const FTask* Tasks, int Count)
{
    if (!Tasks || !ChapterValid(Beats, Count) || Tasks[0].Type != EType::Cinematic)
        return false;
    for (int Index = 0; Index < Count; ++Index)
    {
        const FTask& Task = Tasks[Index];
        const bool MayBeOptional = Task.Type == EType::ExploreOptional || Task.Type == EType::Collectible;
        if (!TaskValid(Task) || (Beats[Index].Optional && !MayBeOptional) ||
            (Task.Type == EType::ExploreOptional && !Beats[Index].Optional) ||
            !TaskCheckpointValid(Task, Beats[Index].PhaseCheckpoints))
            return false;
    }
    return true;
}
} // namespace SoraBeatRules
