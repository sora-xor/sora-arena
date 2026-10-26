#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraProjectile.generated.h"
class USphereComponent;
class USoraCampaignDirector;

// A yumi arrow or an explosive shell in flight. An arrow strikes what it hits.
// A shell detonates where it stops, but only once it has travelled its arming
// distance; a shell stopped short is a dud (SoraCombatRules). Its blast goes
// through SoraDamage::Blast, which reaches its owner and the owner's opponents.
UCLASS()
class SORAARENA_API ASoraProjectile : public AActor
{
    GENERATED_BODY()
public:
    ASoraProjectile();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    FVector Velocity = FVector::ZeroVector;
    float Damage = 55.f;
    float Radius = 320.f;
    bool bArrow = false;
    // A shell's fall; arrows fall at full gravity.
    float Gravity = 420.f;
    int32 ArmingCm = 0;
    // The catalog weapon that fired it, or INDEX_NONE for an opponent's shell.
    int32 WeaponId = INDEX_NONE;
    // Assigned only by the active chapter-one range after a real release.
    unsigned long long ArcheryShotId=0;
    unsigned long long WoodShotId=0;
    float TraveledCm() const { return Traveled; }
    void BindHorseShell(USoraCampaignDirector& Director,uint64 Generation,AActor* Warning);
    bool HorseShellCurrent() const;
    void ShowArcWarning(const FVector& Landing,float FlightSeconds);
    AActor* ArcWarningActor() const { return ArcWarning.Get(); }
private:
    UPROPERTY() TObjectPtr<USphereComponent> Collision;
    float Age = 0.f;
    float Traveled = 0.f;
    bool bDetonated=false;
    bool bHorseShell=false;
    uint64 HorseShellGeneration=0;
    TWeakObjectPtr<USoraCampaignDirector> HorseShellDirector;
    TWeakObjectPtr<AActor> HorseShellWarning;
    TWeakObjectPtr<AActor> ArcWarning;
    void Detonate();
};
