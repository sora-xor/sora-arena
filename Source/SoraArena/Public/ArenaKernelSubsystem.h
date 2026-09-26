#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ArenaKernelSubsystem.generated.h"
struct FKernelRuntime;

// Practice numbering from arena.h, for code that does not include the kernel
// header. Modes are ArenaConfig.mode; tiers are ARENA_BOT_*.
namespace SoraPractice
{
enum EMode : int32 { FreeForAll = 0, Control = 1, Payload = 2, Melee = 3, ModeCount = 4 };
enum EBot : int32 { BotEasy = 0, BotNormal = 1, BotHard = 2, BotCount = 3 };
enum EEntity : int32 { Decoy = 1, Barricade = 2, FireZone = 3, Ward = 4 };
enum EWinner : int32 { WinnerNone = 0, WinnerTeam = 1, WinnerSlot = 2, WinnerDraw = 3 };
enum EHazard : int32 { HazardFire = 1, HazardSlag = 2, HazardShredder = 3 };
constexpr int32 MapCount = 4;
constexpr int32 ClassCount = 6;
// Ten minutes at 60 Hz (docs/combat-rules.md §2.1).
constexpr uint32 MatchTicks = 36000;
// Objectives change nothing on ticks 0-599 (§8).
constexpr uint32 ObjectiveUnlockTick = 600;
// A death holds a player out for 480 ticks (§10).
constexpr int32 RespawnTicks = 480;
inline bool IsTeamMode(int32 Mode) { return Mode == Control || Mode == Payload; }
// Free-for-all and Melee seat two to eight; the team modes seat two even
// teams, up to six against six. Slot 0 is always the player, on team 0 (the
// Payload attackers).
inline int32 MinPlayers(int32) { return 2; }
inline int32 MaxPlayers(int32 Mode) { return IsTeamMode(Mode) ? 12 : 8; }
inline int32 PlayerStep(int32 Mode) { return IsTeamMode(Mode) ? 2 : 1; }
// The class's special sidegrade (catalog weapons 12-17).
inline int32 SpecialOf(int32 ClassId) { return 12 + ClassId; }
}

/** One offline practice match: mode, seats, arena, the player's class and
 *  admitted special, and the bots' tier. Zero-stake by construction. */
struct FSoraPracticeConfig
{
    int32 Mode = SoraPractice::FreeForAll;
    // Every participant, the player included.
    int32 PlayerCount = 6;
    // 0 Nyaagyu Estate, 1 Lantern Ward, 2 Silk Foundry, 3 Debt Citadel.
    int32 MapId = 0;
    // 0 Samurai, 1 Shinobi, 2 Teppo, 3 Hanabi, 4 Karakuri, 5 Kusushi.
    int32 ClassId = 0;
    // SoraPractice::SpecialOf(ClassId) to enter with the class special, or
    // INDEX_NONE for the standard loadout. Melee admits only a melee special.
    int32 SpecialWeaponId = INDEX_NONE;
    // SoraPractice::BotEasy, BotNormal or BotHard, for every bot.
    int32 Difficulty = SoraPractice::BotNormal;
    bool operator==(const FSoraPracticeConfig& Other) const
    {
        return Mode == Other.Mode && PlayerCount == Other.PlayerCount && MapId == Other.MapId && ClassId == Other.ClassId &&
            SpecialWeaponId == Other.SpecialWeaponId && Difficulty == Other.Difficulty;
    }
};

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
    int32 Slot = 0, Team = 0, ClassId = 0, WeaponId = 0, Health = 0, MaxHealth = 1;
    int32 Stamina = 0, Cooldown = 0, RespawnTicks = 0, Kills = 0, Deaths = 0;
    int32 Ammo = 0, Magazine = 0, ReloadTicks = 0;
    int32 ChargeTicks = 0, ChargeRequired = 0;
    int32 SpawnProtectionTicks = 0, GuardTicks = 0, StanceTicks = 0, MarkedTicks = 0;
    int32 AbilityCooldown = 0, AbilityCooldownTotal = 1;
    // The respawn selection the kernel holds, and the special frozen at
    // admission; INDEX_NONE when there is none.
    int32 PendingClass = INDEX_NONE, PendingWeapon = INDEX_NONE, AdmittedSpecial = INDEX_NONE;
    // Always zero in practice; the results screen shows the kernel's figures.
    uint64 InitialBond = 0, RemainingBond = 0, Earnings = 0;
    bool Alive = false, Guarding = false, Exhausted = false;
};
struct FSoraPracticeWall
{
    FVector Minimum = FVector::ZeroVector, Maximum = FVector::ZeroVector;
    // The arena data's name for the piece ("north dojo hall"); presentation only.
    FString Label;
};
struct FSoraPracticeHazard
{
    int32 Kind = 0, Damage = 0, Period = 0;
    FVector Minimum = FVector::ZeroVector, Maximum = FVector::ZeroVector;
    FString Label;
};
struct FSoraPracticeSpawn
{
    FVector Feet = FVector::ZeroVector;
    float Yaw = 0.f;
};
struct FSoraPracticeLane
{
    FString Name;
    TArray<FVector> Points;
};
/** An arena in Unreal centimetres. Bounds, walls, the Control circle, the
 *  payload route and the hazards come from the kernel's native queries; wall
 *  labels, spawns and bot lanes come from crates/arena-core/data/
 *  arena-map-v1.json, loaded only after every shared value matched the kernel. */
struct FSoraPracticeMap
{
    int32 MapId = 0;
    FString Slug;
    FVector Minimum = FVector::ZeroVector, Maximum = FVector::ZeroVector;
    float PlayerRadius = 34.f, PlayerHalfHeight = 88.f, EyeHeight = 140.f;
    TArray<FSoraPracticeWall> Walls;
    FVector ControlCenter = FVector::ZeroVector;
    float ControlRadius = 0.f;
    TArray<FVector> Route;
    float RouteLength = 0.f, PushRadius = 0.f;
    float Checkpoints[3] = {0.f, 0.f, 0.f};
    TArray<FSoraPracticeHazard> Hazards;
    TArray<FSoraPracticeSpawn> TeamSpawns[2];
    TArray<FSoraPracticeSpawn> FreeForAllSpawns;
    TArray<FSoraPracticeLane> Lanes;
    // The floor point at Distance centimetres along the payload route.
    FVector RoutePoint(float Distance) const;
};
/** One kernel ABI 4 event (arena.h ARENA_EVENT_*). Entity events carry the
 *  entity id and kind; Detail is the kind-specific code documented there. */
struct FSoraPracticeEvent
{
    uint32 Kind = 0;
    int32 Actor = INDEX_NONE, Target = INDEX_NONE, WeaponId = 0, Value = 0;
    uint32 WeaponKind = 0;
    uint32 EntityId = 0, EntityKind = 0, Detail = 0;
    FVector From = FVector::ZeroVector, To = FVector::ZeroVector;
};
struct FSoraPracticeProjectile
{
    uint32 Id = 0;
    int32 Owner = 0, WeaponId = 0;
    FVector Position = FVector::ZeroVector;
};
/** A live ability entity (arena.h ArenaEntitySnapshot). Position is the floor
 *  centre; Extent is the barricade half-extents and height, or the radius of a
 *  fire zone, ward or decoy in X and Y. */
struct FSoraPracticeEntity
{
    uint32 Id = 0;
    int32 Kind = 0, Owner = INDEX_NONE, Team = 0;
    FVector Position = FVector::ZeroVector, Extent = FVector::ZeroVector;
    float Yaw = 0.f;
    int32 Health = 0, MaxHealth = 0, Age = 0, Lifetime = 1;
};
/** The objective after the last step (arena.h ArenaObjectiveSnapshot). */
struct FSoraPracticeObjective
{
    int32 Mode = 0;
    uint32 UnlockTick = 0;
    int32 Score[2] = {0, 0};
    int32 ScoreTarget = 0;
    // Control: owner team or INDEX_NONE; progress in -Capture..Capture,
    // negative favouring team 0; living players of each team on the point.
    int32 ControlOwner = INDEX_NONE, ControlProgress = 0, ControlCapture = 1;
    int32 ControlCount[2] = {0, 0};
    bool Contested = false, Overtime = false;
    // Payload, in centimetres along the route.
    float PayloadProgress = 0.f, PayloadLength = 0.f;
    int32 PayloadCheckpoints = 0, PayloadIdle = 0, PayloadRollbackDelay = 0;
    int32 PayloadAttackers = 0, PayloadDefenders = 0;
    FVector PayloadPosition = FVector::ZeroVector;
    int32 WinnerKind = SoraPractice::WinnerNone, WinnerValue = 0;
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
    // Checks a practice choice against the kernel's admission rules and the
    // arena data; Why and WhyEnglish name the first problem.
    bool ValidatePractice(const FSoraPracticeConfig& Config, FString* Why = nullptr, FString* WhyEnglish = nullptr) const;
    // Starts a zero-stake match. Slot 0 is the player; every other slot is a
    // Rust practice bot (crates/arena-bots) of Config.Difficulty.
    bool StartPractice(const FSoraPracticeConfig& Config);
    void StopPractice();
    // One 60 Hz kernel tick with the player's input.
    bool StepPractice(const FSoraPracticeInput& Input);
    bool PracticeActive() const;
    // The bot policy's input for Slot on the next step, at the match's tier.
    bool PracticeBotInput(int32 Slot, FSoraPracticeInput& Out) const;
    // Automation only: slot 0 also plays by the Rust bot policy, so a whole
    // match can run unattended through the same step path.
    bool bPracticeAutopilot = false;
    bool PracticeTerminal = false;
    FSoraPracticeConfig PracticeConfig;
    uint32 PracticeTick = 0;
    FString PracticeError;
    FString PracticeErrorEnglish;
    FString PracticeHash;
    FSoraPracticeMap PracticeMap;
    TArray<FSoraPracticePlayer> PracticePlayers;
    TArray<FSoraPracticeEvent> PracticeEvents;
    TArray<FSoraPracticeProjectile> PracticeProjectiles;
    TArray<FSoraPracticeEntity> PracticeEntities;
    FSoraPracticeObjective PracticeObjective;
    // The match ledger: deposited always equals remaining + earnings, and all
    // three are zero in practice.
    uint64 PracticeDeposited = 0, PracticeRemaining = 0, PracticeEarnings = 0;
private:
    bool RefreshPractice();
    bool LoadPracticeMap(int32 MapId, FSoraPracticeMap& Map, FString& Why, FString& WhyEnglish) const;
    bool Refuse(const TCHAR* Japanese, const TCHAR* English);
    FKernelRuntime* Runtime = nullptr;
    void* Library = nullptr;
};
