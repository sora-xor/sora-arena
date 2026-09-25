#pragma once
#include "CoreMinimal.h"
#include "SoraBossRules.h"

// Content/Data/bosses.json: the seven campaign bosses and the two rival duels
// (story bible §8, chapter scripts ch01-ch08), read by ASoraBoss. Every
// documented field is required and checked; a file that fails leaves the
// catalog unloaded and no boss can spawn.

// Cut: a committed blow in a frontal arc, one or more hits. Thrust: a blow
// along a narrow lane, often with a lunge. Feint: a false windup that holds,
// then turns into another attack. Charge: a leap or rush to a locked point
// (the hero, or a blind hunter's last noise). Area: a slam, spin or sweep
// around the body. Beam: a locked, unguardable line, optionally sweeping.
// Volley: aimed rounds at a locked mark. Zone: marks on the floor that strike
// when they arm (area denial). Summon: adds. Pulse: a sonar ring that
// reveals a moving hero. Expose: an act that opens weak points or drops a
// barrier for a while. Step: pressure without a blow.
enum class ESoraBossAttackKind : uint8 { Cut, Thrust, Feint, Charge, Area, Beam, Volley, Zone, Summon, Pulse, Expose, Step };
// Cyan marks a locked aim or beam; amber a blow or an area.
enum class ESoraBossTelegraph : uint8 { Amber, Cyan, None };
// Close: walk to Near and attack within Engage. Keep: hold between Near and
// Far. Hunt: follow the last thing heard. Hold: turn but never walk.
enum class ESoraBossMove : uint8 { Close, Keep, Hunt, Hold };
// Sequence: a fixed order (on a metronome, a cadence or gaps). Priority: the
// first ready attack in reach. Weighted: a duellist's habits by score state.
enum class ESoraBossPattern : uint8 { Sequence, Priority, Weighted };
// Points: a sparring bout the campaign scores; the opponent never falls.
enum class ESoraBossDefeat : uint8 { Kill, Disarm, Capture, DestroyWeakPoints, Points };
enum class ESoraBossBody : uint8 { Alien, Local, Machine };
enum class ESoraZoneAt : uint8 { Target, AroundTarget, Anchor, AnchorOrTarget };
// What a parry does beyond its stagger: a fencer restarts his measure; a
// tether snaps and the overseer's mantle drops.
enum class ESoraBossParry : uint8 { None, MeasureReset, MantleDown };

struct FSoraBossGuard
{
    bool bGuardable = true;
    int32 Chip = 0;
    int32 Stamina = 0;
    bool bBreaks = false;
    bool bParry = false;
    // Which hit of a multi-hit blow can be parried; zero for any.
    int32 ParryHit = 0;
    int32 ParryStaggerMs = 0;
};

struct FSoraBossAttack
{
    FName Id;
    ESoraBossAttackKind Kind = ESoraBossAttackKind::Cut;
    FString NameJapanese;
    FString NameEnglish;
    // The HUD's captioned telegraph: what is coming and how to answer it.
    FString TellJapanese;
    FString TellEnglish;
    ESoraBossTelegraph Telegraph = ESoraBossTelegraph::Amber;
    // The captioned voice telegraph (a chapter script line id), or none.
    FName Bark;
    bool bBarkOnce = false;
    int32 BarkCooldownMs = 0;
    int32 WindupMs = 0;
    int32 ActiveMs = 0;
    int32 RecoveryMs = 0;
    int32 CooldownMs = 0;
    int32 MinRangeCm = 0;
    int32 MaxRangeCm = 0;
    // Per hit, per round or per zone strike.
    int32 Damage = 0;
    // The attack runs Repeat times back to back, each with its own windup.
    int32 Repeat = 1;
    int32 RepeatGapMs = 0;
    // Cut and thrust.
    int32 ArcMilli = 1000;
    int32 WidthCm = 0;
    int32 Hits = 1;
    int32 GapMs = 0;
    int32 LungeCm = 0;
    int32 PullCm = 0;
    int32 KnockbackCm = 0;
    int32 HeroStaggerMs = 0;
    FSoraBossGuard Guard;
    // A 転 (marobashi) step in this last stretch of the windup reaches the
    // flank, and the blow misses (SoraDefense::Marobashi).
    int32 MarobashiMs = 0;
    bool bMuto = false;
    ESoraBossParry OnParry = ESoraBossParry::None;
    // Chosen before anything else once the hero has held his guard this long.
    int32 IfGuardHeldMs = 0;
    // Feint.
    int32 HoldMs = 0;
    int32 Then = INDEX_NONE;
    // Charge, area, zone and pulse.
    int32 RadiusCm = 0;
    bool bToNoise = false;
    int32 MissRecoveryMs = 0;
    int32 InnerRadiusCm = 0;
    int32 EdgeDamage = 0;
    // Area and expose: weak points it opens, and for how long.
    TArray<int32> Opens;
    int32 OpensMs = 0;
    bool bRotate = false;
    // Beam.
    int32 TrackMs = 0;
    int32 SweepDegrees = 0;
    int32 HeightCm = 0;
    // Volley.
    int32 Rounds = 1;
    int32 IntervalMs = 0;
    int32 LockCm = 0;
    int32 DashCm = 0;
    // Zone.
    ESoraZoneAt At = ESoraZoneAt::Target;
    FName Anchor;
    int32 Count = 1;
    int32 SpreadCm = 0;
    int32 ArmMs = 0;
    int32 LifeMs = 0;
    int32 TickMs = 0;
    int32 RootMs = 0;
    int32 StaggerMs = 0;
    int32 MaxActive = 0;
    bool bFragile = false;
    bool bVoid = false;
    bool bBreaksMantle = false;
    // Summon.
    int32 Group = INDEX_NONE;
    // Pulse.
    int32 ExpandMs = 0;
    int32 RevealCmPerSecond = 0;
    // Expose.
    bool bBarrierOffline = false;
    int32 InterruptDamage = 0;
    int32 InterruptStaggerMs = 0;
    FName Event;
    int32 EventLimit = 0;

    bool IsBlow() const { return Kind == ESoraBossAttackKind::Cut || Kind == ESoraBossAttackKind::Thrust; }
    // It can hurt, so its windup must meet the fight's telegraph floor.
    bool Hurts() const { return Damage > 0 || RootMs > 0; }
};

// A phase's change to one attack's timing, reach or hold (-1 keeps it).
struct FSoraBossOverride
{
    int32 Attack = INDEX_NONE;
    int32 WindupMs = -1;
    int32 ActiveMs = -1;
    int32 RecoveryMs = -1;
    int32 CooldownMs = -1;
    int32 MaxRangeCm = -1;
    int32 RootMs = -1;
};

// An attack on its own clock, alongside the pattern (a sonar pulse, a
// channel gate, a leg planting).
struct FSoraBossTimed
{
    int32 Attack = INDEX_NONE;
    int32 EveryMs = 0;
    int32 FirstMs = 0;
};

// An attack due once, at a health permille (adds at a threshold, a final gate).
struct FSoraBossAtHealth
{
    int32 Attack = INDEX_NONE;
    int32 AtPermille = 0;
};

// A points duel's habits while the hero leads by Lead (2 means two or more).
struct FSoraBossHabit
{
    int32 Lead = 0;
    int32 MinIntervalMs = 0;
    int32 MaxIntervalMs = 0;
    int32 RecoveryBonusMs = 0;
    TArray<int32> Attacks;
    TArray<int32> Weights;
};

struct FSoraBossPhase
{
    // The chapter beat's pattern table id.
    FName Table;
    int32 FromPermille = 1000;
    FName Bark;
    ESoraBossMove Move = ESoraBossMove::Close;
    int32 SpeedCmPerSecond = 0;
    int32 TurnDegreesPerSecond = 0;
    int32 NearCm = 0;
    int32 FarCm = 0;
    int32 EngageCm = 0;
    ESoraBossPattern Pattern = ESoraBossPattern::Sequence;
    TArray<int32> Order;
    int32 BeatMs = 0;
    int32 Measure = 0;
    int32 PauseMs = 0;
    TArray<int32> CadenceMs;
    TArray<int32> GapMs;
    int32 Fallback = INDEX_NONE;
    int32 LoopFrom = 0;
    TArray<FSoraBossHabit> Habits;
    TArray<int32> EasyHalved;
    TArray<int32> Reactions;
    TArray<FSoraBossTimed> Concurrent;
    TArray<int32> OnEnter;
    TArray<FSoraBossAtHealth> Summons;
    TArray<FSoraBossAtHealth> OnceBelow;
    int32 AtFloorAttack = INDEX_NONE;
    int32 AtFloorEveryMs = 0;
    int32 Ward = INDEX_NONE;
    bool bShield = false;
    bool bBarrier = false;
    bool bMantle = false;
    // Invulnerable while any add of this group lives.
    int32 ShieldWhileAdds = INDEX_NONE;
    int32 FloorPermille = 0;
    int32 HearingPermille = 1000;
    TArray<FSoraBossOverride> Overrides;
    int32 LateBelowPermille = 0;
    TArray<FSoraBossOverride> Late;
};

struct FSoraBossWeakPoint
{
    FName Id;
    FString NameJapanese;
    FString NameEnglish;
    // Its own share of the boss's health; zero for a point that only scales.
    int32 Health = 0;
    // From the boss's centre, in its facing frame, in world centimetres.
    FVector Offset = FVector::ZeroVector;
    int32 RadiusCm = 0;
    int32 MeleePermille = 1000;
    int32 RangedPermille = 1000;
    int32 ClosedPermille = 0;
    bool bAlwaysOpen = false;
};

// Orbiting guards that intercept ranged hits: a fencer's drone, a
// collector's ledger shards.
struct FSoraBossWard
{
    FName Id;
    FString NameJapanese;
    FString NameEnglish;
    int32 Count = 0;
    int32 Health = 0;
    int32 OrbitCm = 0;
    int32 PeriodMs = 0;
    bool bClosedInvulnerable = false;
    int32 OpenEveryMs = 0;
    int32 OpenMs = 0;
    bool bOpenAfterBlock = false;
    int32 RespawnMs = 0;
    int32 BrokenStunMs = 0;
    int32 BrokenTakenPermille = 1000;
    FName Bark;
};

struct FSoraBossAddGroup
{
    FName Id;
    FName Archetype;
    FName Variant;
    int32 Count = 0;
    int32 MaxAlive = 0;
    // Called again this long after the group is cleared; zero never.
    int32 RespawnMs = 0;
};

struct FSoraBossBark
{
    FName Event;
    FName Line;
    int32 CooldownMs = 0;
};

struct FSoraBossBarrier
{
    int32 Health = 0;
    int32 RegenDelayMs = 0;
    int32 RegenPerSecond = 0;
    int32 MeleePermille = 1000;
    TMap<int32, int32> WeaponPermille;
    // A hit from these weapons strips this share of the whole barrier.
    TMap<int32, int32> StripPermille;
};

struct FSoraBossHearing
{
    int32 WalkCm = 0;
    int32 CrouchCm = 0;
    int32 SprintCm = 0;
    int32 StillCmPerSecond = 0;
    // Shots, swings, blasts, shouts and thrown stones.
    int32 NoiseCm = 0;
    // What it heard is worth pouncing on for this long.
    int32 FreshMs = 0;
};

struct FSoraBossData
{
    FName Id;
    bool bDuel = false;
    // The chapter's name for the opponent: the boss id, or a duel's npc.
    FName Opponent;
    int32 Chapter = 0;
    FString Beat;
    FString NameJapanese;
    FString Reading;
    FString NameEnglish;
    FString StyleJapanese;
    FString StyleEnglish;
    ESoraBossBody Body = ESoraBossBody::Alien;
    int32 HeldWeapon = 0;
    bool bSparringWeapon = false;
    int32 ScalePermille = 1000;
    int32 Health[3] = {0, 0, 0};
    // Whether the defeat kills; the disarmed, captured and machine-bound live.
    bool bLethal = true;
    ESoraBossDefeat Defeat = ESoraBossDefeat::Kill;
    bool bMutoFinisher = false;
    int32 FloorPermille = 0;
    int32 PoiseMs = 0;
    int32 RearPermille = 1000;
    int32 FlankPermille = 1000;
    // Hits that meet no weak point; zero for an armoured machine.
    int32 BodyPermille = 1000;
    int32 ArenaRadiusCm = 0;
    int32 TransitionMs = 0;
    int32 TelegraphMinMs = 0;
    // Idle between measures, ranged hits in this frontal arc are turned aside (1000 for none).
    int32 DeflectHalfArcMilli = 1000;
    // Blocked frontal hits before the fight's hint (zero for none).
    int32 FrontBlockedHint = 0;
    bool bBlind = false;
    FSoraBossHearing Hearing;
    bool bShield = false;
    int32 ShieldHalfArcMilli = 1000;
    int32 ShieldBreakWeapon = INDEX_NONE;
    int32 ShieldBreakHits = 0;
    bool bBarrier = false;
    FSoraBossBarrier Barrier;
    bool bMantle = false;
    int32 MantleTakenPermille = 1000;
    int32 MantleDownMs = 0;
    TArray<FSoraBossWeakPoint> WeakPoints;
    TArray<FSoraBossWard> Wards;
    TArray<FSoraBossAddGroup> Adds;
    TArray<FSoraBossBark> Barks;
    TArray<FSoraBossPhase> Phases;
    TArray<FSoraBossAttack> Attacks;

    int32 AttackIndex(FName AttackId) const;
    const FSoraBossBark* BarkFor(FName Event) const;
    int32 HealthFor(SoraBossRules::EDifficulty Difficulty) const { return Health[static_cast<int32>(Difficulty)]; }
};

class FSoraBossCatalog
{
public:
    static FSoraBossCatalog& Get();
    bool Load();
    bool IsReady() const { return bReady; }
    // A boss (boss_dunark) or a rival duel (duel_toranosuke_steel).
    const FSoraBossData* Find(FName Id) const;
    // The fight a chapter beat stages (ch06.b09 is the steel duel), or null.
    const FSoraBossData* ForBeat(const FString& Beat) const;
    const TArray<FSoraBossData>& Bosses() const { return BossEntries; }
    const TArray<FSoraBossData>& Duels() const { return DuelEntries; }
    int32 EasyWindupPermille = 1000;
    int32 HardWindupPermille = 1000;
    FString Error;
private:
    bool bReady = false;
    TArray<FSoraBossData> BossEntries;
    TArray<FSoraBossData> DuelEntries;
};
