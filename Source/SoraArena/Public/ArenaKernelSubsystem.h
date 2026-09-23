#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ArenaKernelSubsystem.generated.h"
struct FKernelRuntime;

struct FSoraPracticeInput
{
    int16 Forward = 0, Right = 0, Pitch = 0;
    uint16 Yaw = 0;
    uint32 Buttons = 0;
};
struct FSoraPracticePlayer
{
    FVector Feet = FVector::ZeroVector;
    FRotator Aim = FRotator::ZeroRotator;
    int32 Slot = 0, ClassId = 0, WeaponId = 0, Health = 0, MaxHealth = 1;
    int32 Stamina = 0, Cooldown = 0, RespawnTicks = 0, Kills = 0, Deaths = 0;
    int32 Ammo = 0, Magazine = 0, ReloadTicks = 0;
    int32 ChargeTicks = 0, ChargeRequired = 0;
    bool Alive = false;
};
struct FSoraPracticeWall
{
    FVector Minimum = FVector::ZeroVector, Maximum = FVector::ZeroVector;
};
struct FSoraPracticeMap
{
    FVector Minimum = FVector::ZeroVector, Maximum = FVector::ZeroVector;
    float PlayerRadius = 34.f, PlayerHalfHeight = 88.f, EyeHeight = 140.f;
    TArray<FSoraPracticeWall> Walls;
};
struct FSoraPracticeEvent
{
    uint32 Kind = 0;
    int32 Actor = INDEX_NONE, Target = INDEX_NONE, WeaponId = 0, Value = 0;
    uint32 WeaponKind = 0;
    FVector From = FVector::ZeroVector, To = FVector::ZeroVector;
};
struct FSoraPracticeProjectile
{
    uint32 Id = 0;
    int32 Owner = 0, WeaponId = 0;
    FVector Position = FVector::ZeroVector;
};

/** Actual Rust diagnostics and zero-stake practice. Neither authorizes settlement. */
UCLASS()
class SORAARENA_API UArenaKernelSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    UPROPERTY(BlueprintReadOnly) bool Available = false;
    UPROPERTY(BlueprintReadOnly) bool ProofQualified = false;
    UPROPERTY(BlueprintReadOnly) int32 AbiVersion = 0;
    UPROPERTY(BlueprintReadOnly) int32 VerifiedOfflineTicks = 0;
    UPROPERTY(BlueprintReadOnly) FString OfflineStateHash;
    UPROPERTY(BlueprintReadOnly) FString StatusText;
    bool StartPractice(int32 ClassId, int32 WeaponSlot, int32 MapId);
    void StopPractice();
    bool StepPractice(const FSoraPracticeInput& Input);
    bool PracticeActive() const;
    bool PracticeTerminal = false;
    uint32 PracticeTick = 0;
    FString PracticeError;
    FString PracticeHash;
    FSoraPracticeMap PracticeMap;
    TArray<FSoraPracticePlayer> PracticePlayers;
    TArray<FSoraPracticeEvent> PracticeEvents;
    TArray<FSoraPracticeProjectile> PracticeProjectiles;
private:
    bool RefreshPractice();
    FKernelRuntime* Runtime = nullptr;
    void* Library = nullptr;
};
