#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraBossHazard.generated.h"
class ASoraBoss;
class UStaticMeshComponent;
struct FSoraBossAttack;
struct FSoraBossWard;

/**
 * What a boss leaves in its arena. A zone is a mark on the floor: its ring
 * fills for the attack's windup and arming delay, then it strikes once or
 * keeps striking for its life (a molten channel, a void tile, a late-fee
 * seal that roots whoever steps in). A fragile zone breaks to one arrow or
 * cut. A ward orbits its boss (a fencer's drone, a collector's ledger
 * shards) and intercepts ranged hits aimed at it while closed; it can be
 * shot down, some only while it re-indexes. The boss owns the rules; the
 * hazard keeps time and reports back. Every strike is announced by the boss
 * (ESoraBossPhase::Strike, with the attack's serial) before it lands.
 */
UCLASS()
class ASoraBossHazard : public AActor
{
    GENERATED_BODY()
public:
    ASoraBossHazard();
    void BeginZone(ASoraBoss& From, int32 Attack, int32 AttackSerial, int32 Windup, int32 Root);
    void BeginWard(ASoraBoss& From, int32 Ward, int32 Place);
    virtual void Tick(float DeltaSeconds) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer) override;
    bool IsWard() const { return WardIndex != INDEX_NONE; }
    int32 AttackOf() const { return AttackIndex; }
    int32 WardOf() const { return WardIndex; }
    bool IsArmed() const;
    bool IsSpent() const { return bSpent; }
    float Radius() const { return RadiusCm; }
    // A ward: its health, and whether it is re-indexing (open: it blocks
    // nothing and can be hurt even when its boss says it is otherwise immune).
    int32 WardHealth() const { return Health; }
    bool IsOpen() const;
    // Steps into the line of a ranged hit at Point. False when it cannot
    // (open, or already broken); any damage it may take is applied here.
    bool Intercept(const FVector& Point, int32 Damage);
    // Arms at once and strikes now if the hero is inside (tests, scripted beats).
    void Expire();
private:
    int32 NowMs() const;
    void BuildZone(bool bCyan);
    void BuildWard();
    void Paint(float Progress);
    void StrikeHero();
    void Break();
    TWeakObjectPtr<ASoraBoss> Keeper;
    int32 AttackIndex = INDEX_NONE;
    int32 WardIndex = INDEX_NONE;
    int32 Serial = 0;
    int32 Slot = 0;
    int32 StartedMs = 0;
    int32 WindupMs = 0;
    int32 RootMs = 0;
    float RadiusCm = 0.f;
    int32 PreviousArmedMs = -1;
    bool bSpent = false;
    // The hero was inside at the last tick (a root or a void catches him once per entry).
    bool bHeroInside = false;
    int32 Health = 0;
    int32 LastBlockMs = MIN_int32 / 2;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Fill;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Rim;
};
