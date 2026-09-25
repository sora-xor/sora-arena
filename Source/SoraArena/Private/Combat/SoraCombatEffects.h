#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "SoraCombatEffects.generated.h"
class ACharacter;

/**
 * Timed combat effects that outlive the call that caused them: the hit-stop
 * that runs the whole world at SoraCombatRules::HitStopDilationPermille for a
 * few milliseconds after a blade's contact, and a seizure net's hold on a
 * character's movement. Both are measured in the world's real, undilated time,
 * so a hit-stop cannot stretch itself, and both end with the world. Kernel
 * practice never stops: its steps are fixed to the frame.
 */
UCLASS()
class USoraCombatEffects : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    static USoraCombatEffects* Get(const UObject* WorldContext);
    // Holds the world for at least Milliseconds more; zero does nothing.
    void HitStop(int32 Milliseconds);
    bool IsHitStopped() const { return bHitStop; }
    // Target cannot walk for Milliseconds.
    void Root(ACharacter& Target, int32 Milliseconds);
    bool IsRooted(const AActor* Target) const;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    virtual void Deinitialize() override;
protected:
    virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
private:
    struct FRoot
    {
        TWeakObjectPtr<ACharacter> Target;
        double EndsAt = 0.0;
    };
    void EndHitStop();
    double Now() const;
    bool bHitStop = false;
    double HitStopEndsAt = 0.0;
    float DilationBefore = 1.f;
    TArray<FRoot> Roots;
};
