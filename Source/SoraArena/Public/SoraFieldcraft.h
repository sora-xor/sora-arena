#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraCatalog.h"
#include "SoraFieldcraftRules.h"
#include "Subsystems/WorldSubsystem.h"
#include "SoraFieldcraft.generated.h"
class APointLight;
class ASoraCompanion;
class ASoraPlayerCharacter;
class UPointLightComponent;
class USphereComponent;
class UStaticMeshComponent;

// A lamp or fire of the beat's fieldcraft: its body, and the point light
// the guards see by (USoraStealth::LightAt counts every visible APointLight).
// A floodlight's cable junction takes an arrow or a round.
UCLASS()
class SORAARENA_API ASoraLamp : public AActor
{
    GENERATED_BODY()
public:
    ASoraLamp();
    void Build(const FSoraLamp& Data, int32 Index);
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* Instigator, AActor* Causer) override;
    virtual void Destroyed() override;
    void SetLit(bool bLit);
    bool IsLit() const;
    int32 LampIndex() const { return Index; }
    // Where the lamp's flame or lens is, for the eye.
    FVector Glow() const;
private:
    UPROPERTY() TObjectPtr<APointLight> Light;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Pieces;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Flame;
    int32 Index = INDEX_NONE;
    float GlowHeight = 150.f;
    float Intensity = 0.f;
    bool bShootable = false;
};

// A tsubute stone in flight on its arc. Where it lands the guards hear it
// (a lure, SoraStealthRules::ENoise::Lure) and go to look.
UCLASS()
class SORAARENA_API ASoraThrownStone : public AActor
{
    GENERATED_BODY()
public:
    ASoraThrownStone();
    virtual void Tick(float DeltaSeconds) override;
    FVector Velocity = FVector::ZeroVector;
    int32 NoiseCm = 1400;
private:
    UPROPERTY() TObjectPtr<USphereComponent> Collision;
    float Age = 0.f;
    void Land();
};

DECLARE_MULTICAST_DELEGATE_OneParam(FSoraFieldcraftEventSignature, FName);

// What the HUD shows of the beat's fieldcraft for the hero.
struct FSoraFieldcraftReadout
{
    bool bActive = false;
    // In the water: diving, and breath left (0-1).
    bool bSwimming = false;
    bool bDiving = false;
    float Breath = 1.f;
    // On the wall: grip left (0-1), at a ledge.
    bool bClimbing = false;
    float Grip = 1.f;
    bool bLedge = false;
    // Standing at the foot of the face, where Jump starts the climb.
    bool bAtFace = false;
    // Stones carried of the most, and a rubble pile within reach.
    bool bStones = false;
    int32 Stones = 0;
    int32 StonesMax = 0;
    bool bAtPile = false;
    // The candle, and whether Guard cups it.
    bool bCandle = false;
    bool bCupped = false;
    // What Interact held would work now, how far a hold has come (0-1).
    enum class EHold : uint8 { None, Snuff, Revive, Free, Release };
    EHold HoldHere = EHold::None;
    EHold Holding = EHold::None;
    float HoldProgress = 0.f;
    // The escorted party: whether the hero's signal hides or sends them on,
    // and whether they wait for it.
    bool bSignal = false;
    bool bPartyHidden = false;
    int32 PartyDown = 0;
    int32 PartyBound = 0;
    // Allies and escorts who are down, and where.
    TArray<FVector> Downed;
    // Volley ranks: the ring being marked (valid within range), which rank
    // stands in front, and each rank's loading (0-1) and gunners standing.
    bool bVolley = false;
    bool bMarking = false;
    bool bMarkValid = false;
    FVector MarkAt = FVector::ZeroVector;
    float RingRadius = 0.f;
    int32 Ranks = 0;
    int32 FrontRank = 0;
    float RankLoaded[SoraFieldcraftRules::MaxRanks] = {};
    int32 RankStanding[SoraFieldcraftRules::MaxRanks] = {};
};

/**
 * The fieldcraft of the campaign's active beat (FSoraFieldcraft, from
 * scripts/unreal/campaign_fieldcraft.py), played with SoraFieldcraftRules:
 * lamps the hero snuffs or shoots out and that may relight; floors that
 * change his footsteps in the stealth zone; water he swims and dives in,
 * with breath, cover and float lines; a face he climbs hold by hold on his
 * grip; tsubute stones he throws as lures; the candle he cups; the escorted
 * party and the allies as ASoraCompanion characters (downed, raised, freed,
 * hidden on his signal, bleeding out); the volley ranks he commands; and the
 * look_at events the scripts key on what he looks at. The campaign director stages it as a beat starts
 * (after the beat's stealth zone opens) and clears it as the beat ends; what
 * happens reaches the beat through OnEvent. All timing is world time on
 * fixed patterns; nothing is random.
 */
UCLASS()
class SORAARENA_API USoraFieldcraft : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    static USoraFieldcraft* Get(const UObject* WorldContext);
    void Stage(const FSoraBeat& Beat);
    void Clear();
    bool IsStaged() const { return Staged != nullptr; }
    const FSoraFieldcraft* Active() const { return Staged; }
    // Every event raised for the beat: npc_downed:<id>, npc_revived:any,
    // signal:hide, interact_done:collar_<id>, event:door_1_open,
    // look_at:<id>, lure_triggered, volume_enter:<ledge> ...
    FSoraFieldcraftEventSignature OnEvent;

    // The hero's side. Ability: the signal to an escorted party that answers
    // it; held, the volley ranks' ring marked, ordered as it is let go
    // (volley_command in play); else a stone thrown (tsubute in play). Interact pressed: a held
    // piece of work begins at the nearest point that takes it (a lamp to
    // snuff, the downed to raise, a collar or cell door to open), or stones
    // are taken up at a rubble pile. Jump: starts the climb at the face's
    // foot, or lets go of the wall. Each returns whether it took the press.
    bool Ability(ASoraPlayerCharacter& Hero);
    bool Interact(ASoraPlayerCharacter& Hero);
    bool Jump(ASoraPlayerCharacter& Hero);
    // In the water or on the wall no arm is used and no weapon changes hands.
    bool ArmsStowed() const { return bSwimming || bClimbing; }
    // The hero's own movement input is ignored (the wall moves him).
    bool HoldsHero() const { return bClimbing; }
    // A cap on the hero's pace in cm/s (the water), or 0.
    float HeroPace() const;
    bool IsSwimming() const { return bSwimming; }
    bool IsDiving() const { return bSwimming && bDiving; }
    bool IsClimbing() const { return bClimbing; }
    // How much of the hero an opponent at Distance sees, from what a line
    // reaches (x1000): nothing of him under the water, little in the reeds.
    int32 HeroExposure(int32 ExposurePermille) const;
    // A healing lance round struck Target (a downed companion rises soon).
    void LanceHit(AActor* Target);
    // A defended target's health changed (x1000 of full): the person standing
    // at it is netted as it is worn below half, freed as it is mended past
    // half, and taken when it is lost.
    void TargetChanged(int32 Target, int32 HealthPermille);
    const TArray<TObjectPtr<ASoraCompanion>>& PeopleInPlay() const { return People; }
    // The pace at which the hero's held work fills (a cupped candle halves it).
    int32 WorkRatePermille() const;
    // The events the beat raises, so allies that wait for a wave join it.
    void NoteBeatEvent(const FString& Event);
    // A tsubute landed at At: the beat hears it, and so do the guards in earshot.
    void StoneLanded(const FVector& At, int32 NoiseCm);
    // Every opponent that sees the hero in a stealth beat: the escorted hide.
    void PartyDetected();

    // The escorted party (the director walks it along its road).
    const TArray<TObjectPtr<ASoraCompanion>>& PartyMembers() const { return Party; }
    const TArray<TObjectPtr<ASoraCompanion>>& AlliesInPlay() const { return Allies; }
    // Every member free, standing and in the open: the party walks when the hero keeps up.
    bool PartyReady() const;
    // Places each member at its slot on the road (hidden ones keep their
    // spots; the bound and the downed stay where they are).
    void PlaceParty(const TArray<FVector>& Slots, float Yaw, float PaceCmS);
    // Where the hero's hand is wanted before the party can go on: a member
    // down, a collar to cut or a cell to open, nearest to the party first.
    bool PartyWork(FVector& Location) const;
    // A companion's rules changed state (ASoraCompanion::AdmitDamage).
    void CompanionChanged(ASoraCompanion& Companion, SoraFieldcraftRules::EChange Change);
    // A lamp's cable junction was shot.
    void LampShot(int32 Index);
    // The hero snuffs, or relights, lamp Index (automation and the hold).
    bool SnuffLamp(int32 Index);
    const TArray<TObjectPtr<ASoraLamp>>& Lamps() const { return LampActors; }
    int32 StonesCarried() const { return Stones; }
    FSoraFieldcraftReadout Readout(const ASoraPlayerCharacter& Hero) const;
    // Look targets raised this beat (automation).
    const TSet<FString>& Seen() const { return LookedAt; }
    // Volleys: the ring held, orders given and volleys fired this beat.
    bool IsMarking() const { return bMarking; }
    int32 VolleysOrdered() const { return VolleyState.Orders; }
    int32 VolleysFired() const { return VolleysFiredCount; }

    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    virtual void Deinitialize() override;
protected:
    virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
private:
    enum class EHoldKind : uint8 { None, Snuff, Companion, Release };
    struct FHold
    {
        EHoldKind Kind = EHoldKind::None;
        int32 Index = INDEX_NONE;
        TWeakObjectPtr<ASoraCompanion> Companion;
        int32 HeldMs = 0;
        int32 NeedMs = 0;
    };
    void Raise(const FString& Event);
    void RaiseDowned(const ASoraCompanion& Companion);
    ASoraPlayerCharacter* Hero() const;
    int32 StepMs(float DeltaTime);
    void StageWorld(const FSoraBeat& Beat);
    void StageCompanions(const FSoraBeat& Beat);
    void TickHolds(int32 DtMs);
    void TickCompanions(int32 DtMs);
    void TickLamps(int32 DtMs);
    void TickWater(int32 DtMs);
    void TickClimb(float DeltaTime, int32 DtMs);
    void TickCandle();
    void TickLooks();
    void TickVolley(int32 DtMs);
    // Where the hero's eye meets the ground within the volley's reach.
    bool AimMark(const ASoraPlayerCharacter& Hero, FVector& At) const;
    void OrderVolley();
    void FireVolley(int32 Rank, const FVector& At);
    void ThrowStone(ASoraPlayerCharacter& Hero);
    void LetGo(ASoraPlayerCharacter& Hero, bool bFell);
    bool AtFace(const ASoraPlayerCharacter& Hero) const;
    // The nearest work within reach of Where: its kind, index or companion, and the ms it takes.
    FHold WorkAt(const FVector& Where) const;
    UStaticMeshComponent* Piece(const FString& Name, const TCHAR* Mesh, const FVector& At, const FVector& Scale,
        const FLinearColor& Color, bool bCollision = false);

    const FSoraFieldcraft* Staged = nullptr;
    FString BeatId;
    UPROPERTY() TObjectPtr<AActor> Props;
    UPROPERTY() TArray<TObjectPtr<ASoraLamp>> LampActors;
    UPROPERTY() TArray<TObjectPtr<ASoraCompanion>> Party;
    UPROPERTY() TArray<TObjectPtr<ASoraCompanion>> Allies;
    UPROPERTY() TArray<TObjectPtr<ASoraCompanion>> People;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Doors;
    UPROPERTY() TObjectPtr<UPointLightComponent> CandleLight;
    TArray<SoraFieldcraftRules::FLamp> LampStates;
    TArray<int32> LampHeldMs;
    TArray<bool> DoorsOpen;
    TArray<int32> HideSpotOf;
    FHold Holding;
    float ClockCarryMs = 0.f;
    // Water.
    bool bSwimming = false;
    bool bDiving = false;
    SoraFieldcraftRules::FBreath Breath{0, 0, 0};
    TSet<int32> LinesTouched;
    // Climbing: the grip, where on the wall, and a fall's start.
    bool bClimbing = false;
    SoraFieldcraftRules::FClimb Grip{0, 0};
    float ClimbHeight = 0.f;
    bool bFalling = false;
    float FallFromZ = 0.f;
    TSet<int32> LedgesReached;
    // Stones and the candle.
    int32 Stones = 0;
    bool bCupped = false;
    // Look targets already raised in the beat, and when looks were last checked.
    TSet<FString> LookedAt;
    float NextLookAt = 0.f;
    bool bPartyHidden = false;
    bool bFirstSignal = true;
    // Volley ranks: their clock, the ring held, orders on their way.
    struct FPendingVolley
    {
        int32 Rank = INDEX_NONE;
        FVector At = FVector::ZeroVector;
        int32 FireAtMs = 0;
    };
    SoraFieldcraftRules::FVolley VolleyState = SoraFieldcraftRules::StartVolley();
    int32 VolleyClockMs = 0;
    bool bMarking = false;
    bool bMarkValid = false;
    FVector MarkAt = FVector::ZeroVector;
    bool bFrontReady = false;
    bool bVolleyTaught = false;
    TArray<FPendingVolley> PendingVolleys;
    int32 VolleysFiredCount = 0;
};
