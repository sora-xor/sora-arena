#pragma once
#include "CoreMinimal.h"
#include "Engine/DamageEvents.h"
#include "SoraCombatRules.h"

class AActor;
class AController;
class ASoraCharacterBase;
class UPrimitiveComponent;
class UWorld;
struct FHitResult;

// One hit as campaign combat sees it: what kind, where it came from, which
// weapon or opponent attack dealt it and how it meets a guard
// (SoraCombatRules::Defend). Victims' defenses write Defense.
struct FSoraHit
{
    SoraCombatRules::EHit Kind = SoraCombatRules::EHit::Scripted;
    // The eye a blade or ray left, or where a shell went off.
    FVector Origin = FVector::ZeroVector;
    bool bHasOrigin = false;
    // True only for traced rounds; arrows, blasts and drowning remain distinct.
    bool bHitscan = false;
    SoraCombatRules::EEnvironmentalRate EnvironmentalRate = SoraCombatRules::EEnvironmentalRate::None;
    // A catalog weapon, or INDEX_NONE for an opponent's attack.
    int32 WeaponId = INDEX_NONE;
    // The opponent's attack (Content/Data/enemies.json), if any.
    FName AttackId;
    bool bParryable = false;
    // Negative uses the kind's share (SoraCombatRules::FAttack).
    int32 GuardChip = -1;
    int32 GuardStamina = -1;
    int32 ParryStaggerMs = SoraCombatRules::ParryStaggerMs;
    bool bBreaksGuard = false;
    // A slam or final foreclosure goes through a held guard (SoraCombatRules::FAttack).
    bool bUnguardable = false;
    // Above zero, a committed cut a sheathed hero may take by mutō-dori
    // within this many milliseconds of its landing.
    int32 MutoWindowMs = 0;
    int32 KnockbackCm = 0;
    // An opponent's blow that lands staggers the hero this long.
    int32 HeroStaggerMs = 0;
    // A hero's strike weighs this much against an opponent's poise.
    int32 StaggerMs = 0;
    // Written by Resolve from the hit's trace: where it struck and which part
    // of the victim (a boss's weak point) it met.
    FVector Impact = FVector::ZeroVector;
    bool bHasImpact = false;
    TWeakObjectPtr<const UPrimitiveComponent> Part;
    // Written by the victim: how its guard, shield or barrier met the hit.
    SoraCombatRules::EDefense Defense = SoraCombatRules::EDefense::Exposed;

    static FSoraHit Melee(const FVector& From, int32 WeaponId);
    static FSoraHit Ranged(const FVector& From, int32 WeaponId);
    static FSoraHit Blast(const FVector& At, int32 WeaponId);
    static FSoraHit Beam(const FVector& From);
    static FSoraHit Hazard(const FVector& At);
    SoraCombatRules::FAttack Attack(int32 Damage) const;
};

// A point hit that carries its FSoraHit through AActor::TakeDamage.
struct FSoraDamageEvent : public FPointDamageEvent
{
    static const int32 ClassID = 0x534F5241;
    FSoraHit Hit;
    FSoraDamageEvent(float InDamage, const FHitResult& InHitInfo, const FVector& InShotDirection, const FSoraHit& InHit);
    virtual int32 GetTypeID() const override { return FSoraDamageEvent::ClassID; }
    virtual bool IsOfType(int32 InID) const override { return FSoraDamageEvent::ClassID == InID || FPointDamageEvent::IsOfType(InID); }
};

// The single damage path for campaign and training combat. Attackers call
// Strike or Blast; every character's TakeDamage calls Resolve, which applies
// the shared rules (no damage between opponents, nor between the hero and
// his companions; SoraCombatRules), asks the
// victim for its own defenses and defeat handling, holds the world still on a
// blade's contact, and announces Damaged, Died or a conscript's knockdown
// through USoraGameEvents. Kernel practice never reaches it: kernel-driven
// characters take no Unreal damage.
namespace SoraDamage
{
// Damage from Causer, credited to Instigator. Returns the damage applied.
float Strike(AActor* Target, float Damage, const FSoraHit& Hit, const FVector& Direction, const FHitResult& Trace,
    AController* Instigator, AActor* Causer);
float Resolve(ASoraCharacterBase& Victim, float Damage, const FDamageEvent& Event, AActor* Causer);
// An armed detonation at Hit.Origin: every character inside Radius with a
// clear line from the detonation point takes Damage, the owner included,
// the owner's allies excepted. Returns how many bodies it reached.
int32 Blast(UWorld& World, float Damage, float Radius, const FSoraHit& Hit, AController* Instigator, AActor* Causer);
// The character an attack comes from: Causer itself, or whoever fired it.
const ASoraCharacterBase* AttackerOf(const AActor* Causer);
// The cosine, x1000, between Body's facing and the direction to From, seen from above.
int32 FacingMilli(const AActor& Body, const FVector& From);
// A short-lived tracer or telegraph line. Presentation only; it never collides.
void Beam(UWorld* World, FVector From, FVector To, FLinearColor Color, float Radius = 1.5f, float Life = .08f);
// A telegraph ring on the ground, drawn as sixteen short lines.
void Ring(UWorld* World, FVector Center, float Radius, FLinearColor Color, float Life);
}
