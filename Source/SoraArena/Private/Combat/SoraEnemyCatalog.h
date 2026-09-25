#pragma once
#include "CoreMinimal.h"
#include "SoraStealthRules.h"

// How an archetype fights and moves (ASoraEnemyController, ASoraEnemy).
enum class ESoraEnemyBehavior : uint8 { Blade, Rifle, Shield, Grenadier, Marksman, Drone, Conscript, Auditor, Automaton, Walker };
// The body it is built from until each archetype's own kit exists.
enum class ESoraEnemyBody : uint8 { Alien, Local, Drone, Machine, Walker };
// Melee: a committed blow along a locked line or around the body. Burst:
// aimed rounds after a raise. LockShot: a tracked cyan glint, then one shot.
// Lob: an arcing shell whose landing ring shows for its whole flight. Beam: a
// locked ground line, then an unguardable beam. Net: a lock ring on the
// target, then a seizure net that holds it if it has not left the ring.
enum class ESoraEnemyAttackKind : uint8 { Melee, Burst, LockShot, Lob, Beam, Net };

struct FSoraEnemyAttack
{
    FName Id;
    // Raised with USoraGameEvents::OnEnemyCue when the attack commits: the
    // hook for barks and captioned telegraphs.
    FName Cue;
    FString NameJapanese;
    FString NameEnglish;
    ESoraEnemyAttackKind Kind = ESoraEnemyAttackKind::Melee;
    // Cyan marks a locked aim or beam; amber a blow or an area.
    bool bCyanTelegraph = false;
    int32 Damage = 0;
    int32 WindupMs = 0;
    int32 RecoveryMs = 0;
    // After it resolves, this attack is not chosen again for this long.
    int32 CooldownMs = 0;
    int32 MinRangeCm = 0;
    int32 MaxRangeCm = 0;
    // Melee: the cosine of half its arc (x1000; -1000 is all round), how far a
    // landed blow pushes the hero, and how its guard behaves.
    int32 ArcMilli = 1000;
    int32 KnockbackCm = 0;
    int32 HeroStaggerMs = 0;
    bool bParryable = false;
    int32 GuardChip = 0;
    int32 GuardStamina = 0;
    int32 ParryStaggerMs = 0;
    bool bBreaksGuard = false;
    // Burst.
    int32 Rounds = 1;
    int32 IntervalMs = 0;
    // Lob and net rings, a lob's flight and arming, a net's hold, a beam's width.
    int32 RadiusCm = 0;
    int32 FlightMs = 0;
    int32 ArmingCm = 0;
    int32 RootMs = 0;
    int32 WidthCm = 0;
};

// A personal shield that soaks hits until it breaks (SoraCombatRules::SoakBarrier).
struct FSoraEnemyBarrier
{
    int32 Health = 0;
    int32 RegenDelayMs = 0;
    int32 RegenPerSecond = 0;
    int32 BreakStaggerMs = 0;
    int32 MeleePermille = 1000;
    TMap<int32, int32> WeaponPermille;
    TArray<int32> BypassWeapons;
    int32 PermilleFor(int32 WeaponId, bool bMelee) const;
};

struct FSoraEnemyVariant
{
    FName Id;
    FString NameJapanese;
    FString NameEnglish;
    // Zero keeps the archetype's health.
    int32 Health = 0;
    // Negative keeps the archetype's value.
    int32 SightCm = -1;
    int32 DarkSightCm = -1;
    int32 ViewDegrees = -1;
    FSoraEnemyBarrier Barrier;
};

struct FSoraEnemyArchetype
{
    FName Id;
    FString NameJapanese;
    FString Reading;
    FString NameEnglish;
    FString WeaponJapanese;
    FString WeaponEnglish;
    bool bDebtBound = false;
    ESoraEnemyBody Body = ESoraEnemyBody::Alien;
    ESoraEnemyBehavior Behavior = ESoraEnemyBehavior::Rifle;
    int32 FirstChapter = 0;
    int32 Health = 0;
    int32 SpeedCmPerSecond = 0;
    int32 TurnDegreesPerSecond = 0;
    int32 ScalePermille = 1000;
    bool bLethal = true;
    // Nonlethal archetypes only.
    int32 SubdueWindowMs = 0;
    int32 SealCutHoldMs = 0;
    int32 RiseHealthPermille = 0;
    SoraStealthRules::FPerception Perception = SoraStealthRules::Standard();
    // A tower shield's covered front (cosine of half the arc, x1000), and how
    // long a yari thrust on its rim turns it aside.
    bool bShield = false;
    int32 ShieldHalfArcMilli = 1000;
    int32 RimOpeningMs = 0;
    int32 RearWeakPermille = 1000;
    int32 PoiseMs = 0;
    // A rear takedown can start on it (a cat's nape, not a machine's hull).
    bool bRearTakedown = false;
    int32 KeepDistanceCm = 0;
    int32 RelocateAfterShots = 0;
    int32 HoverCm = 0;
    int32 AlarmRadiusCm = 0;
    bool bStatic = false;
    TArray<FSoraEnemyAttack> Attacks;
    TArray<FSoraEnemyVariant> Variants;
    const FSoraEnemyVariant* Variant(FName VariantId) const;
    bool IsMelee() const;
};

// Content/Data/enemies.json, the campaign's opponent archetypes (story bible
// §7). Every documented field is required and range-checked; a file that fails
// leaves the catalog unloaded and no opponent can spawn.
class FSoraEnemyCatalog
{
public:
    static FSoraEnemyCatalog& Get();
    bool Load();
    bool IsReady() const { return bReady; }
    const FSoraEnemyArchetype* Find(FName Id) const;
    const TArray<FSoraEnemyArchetype>& Archetypes() const { return Entries; }
    FString Error;
private:
    bool bReady = false;
    TArray<FSoraEnemyArchetype> Entries;
};
