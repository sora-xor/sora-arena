#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraCatalog.h"
#include "SoraFieldcraftRules.h"
#include "SoraFloodRules.h"
#include "Subsystems/WorldSubsystem.h"
#include "SoraFieldcraft.generated.h"
class APointLight;
class ASoraCompanion;
class ASoraEnemy;
class ASoraHorse;
class ASoraPlayerCharacter;
class UPointLightComponent;
class USphereComponent;
class USpotLightComponent;
class UStaticMeshComponent;
struct FSoraMeleeCommittedEvent;

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

// A seal stake (差押え杭) across the charge's road (ch08.b02): its cyan
// barrier bars the way until a yari thrust from a horse at a canter or
// faster, or two arrows, break it (SoraFieldcraftRules::StakeStruck).
UCLASS()
class SORAARENA_API ASoraSealStake : public AActor
{
    GENERATED_BODY()
public:
    ASoraSealStake();
    void Build(int32 Index, float WidthCm);
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* Instigator, AActor* Causer) override;
    // The barrier falls and the way is open.
    void Break();
    bool IsStanding() const { return bStanding; }
private:
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Stake;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Barrier;
    int32 Index = INDEX_NONE;
    bool bStanding = true;
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
    bool bFloodPassage=false;
    bool bFloodAirShaft=false;
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
    enum class EHold : uint8 { None, Snuff, Revive, Free, Release, NetCut, Relight };
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
    // Easy's auto-order is giving the orders.
    bool bAutoOrder = false;
    // Seizure nets: quarry locked and netted, and the least time any netted
    // one has left before it is hauled off (0-1 of its timer; 1 with no haul).
    int32 NetsLocking = 0;
    int32 NetsHeld = 0;
    float HaulLeft = 1.f;
    // A searchlight's spot on the hero, and how near it is to raising the alarm (0-1).
    bool bInLight = false;
    float LightExposure = 0.f;
    // Cook-fires out (the hold waits for them).
    int32 FiresOut = 0;
    // At a ladder's foot or its top, where Jump climbs; on a ladder.
    bool bAtLadder = false;
    bool bOnLadder = false;
    // The charge: riders with the hero, the rival, and stakes still standing.
    int32 Riders = 0;
    int32 StakesStanding = 0;
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
    bool FloodExitReady() const { return !FloodSpace || SoraFloodRules::Ready(FloodRoute); }
    int32 FloodElapsedMs() const { return FloodClockMs; }
    int32 FloodPassageStage() const { return FloodRoute.Stage; }
    bool FloodCarriesIota() const;
    bool FloodObjective(FVector& At) const;
    bool MoveFloodCompanion(ASoraCompanion& Companion,float Dt);
    int32 FloodFootstepPermille(const FVector& Feet) const;
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
    void CancelHeldInteraction();
    bool Jump(ASoraPlayerCharacter& Hero);
    // In the water or on the wall no arm is used and no weapon changes hands.
    bool ArmsStowed() const { return bSwimming || bClimbing || LadderClimb != INDEX_NONE; }
    // The hero's own movement input is ignored (the wall moves him).
    bool HoldsHero() const { return bClimbing || LadderClimb != INDEX_NONE; }
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
    // Volleys: the ring held, orders given and volleys fired this beat, and
    // the smoke banks standing.
    bool IsMarking() const { return bMarking; }
    int32 VolleysOrdered() const { return VolleyState.Orders; }
    int32 VolleysFired() const { return VolleysFiredCount; }
    int32 SmokeBanks() const { return Smoke.Num(); }
    // A volley's smoke bank stands between From and To: it hides each from
    // the other, for both sides (opponents' sight and aimed rounds), while
    // arrows, rounds and blades pass through it.
    bool SmokeBetween(const FVector& From, const FVector& To) const;
    // Easy's auto-order is on (the difficulty is Easy and the setting allows it).
    bool AutoOrdering() const;

    // Seizure nets (FSoraNets). The director tells it who each wave puts on
    // the field; the drones of a net wave take quarry (as many as the wave
    // nets with; the rest scout), a scout wave's hang off the road. A drone
    // whose net is cut reloads before it locks again. While any of a string
    // or a cart is netted (or the string shies from a searchlight) it halts.
    void OpponentJoined(ASoraEnemy& Enemy, int32 Wave);
    bool IsOnErrand(const ASoraEnemy& Enemy) const;
    bool QuarryHalted() const;
    int32 QuarryCount() const { return QuarryStates.Num(); }
    SoraFieldcraftRules::ENet NetOf(int32 Quarry) const;
    int32 QuarryHealth(int32 Quarry) const;
    FVector QuarryLocation(int32 Quarry) const;
    ASoraEnemy* TetherOf(int32 Quarry) const;
    // A netting drone reloading after its net was cut; the drones that net.
    bool IsRearming(const ASoraEnemy& Drone) const;
    int32 NettingDrones() const;
    // Searchlights: where each one's spot falls now, and whether it shines.
    int32 LightCount() const { return LightStates.Num(); }
    bool IsLightOn(int32 Light) const;
    FVector SpotOf(int32 Light) const;
    // A real detection supplies its evidence. A generic alert bark cannot
    // reveal where an unseen hero has moved since then.
    void LockSearchlights(const FVector& KnownLocation);
    // The one-shot bell: rung this beat.
    bool BellRung() const { return BellUses == 0 && bBellStaged; }
    FVector BellLocation() const;
    // Cook-fires: lit or guttered.
    bool IsFireLit(int32 Fire) const { return FiresLit.IsValidIndex(Fire) && FiresLit[Fire]; }
    int32 FiresOut() const;
    FVector FireLocation(int32 Fire) const;
    // Ladders: on one now, and whether the hero stands on a roof.
    bool IsOnLadder() const { return LadderClimb != INDEX_NONE; }
    bool IsOnRoof(const FVector& Location) const;
    // The League's charge: its riders (the rival first), the stakes, and
    // what the riders have struck.
    const TArray<TObjectPtr<ASoraHorse>>& ChargeRiders() const { return Riders; }
    bool IsStakeStanding(int32 Stake) const;
    FVector StakeLocation(int32 Stake) const;
    void StakeHit(int32 Stake, bool bYari, bool bArrow);
    int32 RiderStrikes() const { return RiderStrikeCount; }
    float PackLead() const { return PackChainage; }

    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    virtual void OnWorldEndPlay(UWorld& InWorld) override;
    virtual void Deinitialize() override;
protected:
    virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
private:
    enum class EHoldKind : uint8 { None, Snuff, Companion, Release, NetCut, Relight };
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
    void StageFlood(const FSoraBeat& Beat);
    void ClearFlood();
    void TickFloodWater(int32 DtMs);
    void TickFloodCompanions(int32 DtMs);
    float FloodSurfaceAt(const FVector& At) const;
    bool InFloodWater(const FVector& At) const;
    void TickClimb(float DeltaTime, int32 DtMs);
    void TickCandle();
    void TickLooks();
    void TickVolley(int32 DtMs);
    void TickSmoke(int32 DtMs);
    void AutoOrder();
    // Nets, searchlights, the bell, cook-fires, ladders and the charge
    // (SoraFieldcraftNets.cpp, SoraFieldcraftWatch.cpp, SoraFieldcraftCharge.cpp).
    void StageNets();
    void TickNets(int32 DtMs);
    void NetChanged(int32 Quarry, SoraFieldcraftRules::ENetChange Change);
    void QuarryDamaged(int32 Quarry, int32 Hp);
    void SaddleCut(const FSoraMeleeCommittedEvent& Event);
    void TickScouts();
    void StageWatch();
    void TickSearchlights(int32 DtMs);
    void BellStruck();
    void TickFires();
    void TickLadders(float DeltaTime);
    bool LadderJump(ASoraPlayerCharacter& Hero);
    void StageCharge();
    void TickCharge(float DeltaTime, int32 DtMs);
    void RiderStrikes(int32 DtMs);
    // Where the hero's eye meets the ground within the volley's reach.
    bool AimMark(const ASoraPlayerCharacter& Hero, FVector& At) const;
    void OrderVolley();
    void FireVolley(int32 Rank, const FVector& At);
    void ThrowStone(ASoraPlayerCharacter& Hero);
    void LetGo(ASoraPlayerCharacter& Hero, bool bFell);
    bool AtFace(const ASoraPlayerCharacter& Hero) const;
    // The nearest work within reach of Where: its kind, index or companion, and the ms it takes.
    FHold WorkAt(const FVector& Where) const;
    // A piece of the set; with a Surface role (SoraFieldcraftLayout) it wears
    // that CC0 PBR surface of the environment palette, tinted Color.
    UStaticMeshComponent* Piece(const FString& Name, const TCHAR* Mesh, const FVector& At, const FVector& Scale,
        const FLinearColor& Color, bool bCollision = false, const TCHAR* Surface = nullptr);
    // At the water's surface among reeds or lotus: only a head shows, under the leaves.
    bool UnderCover(const FVector& Location) const;
    // The ladder whose roof Location stands on, or INDEX_NONE.
    int32 RoofAt(const FVector& Location) const;

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
    const FSoraFloodSpace* FloodSpace=nullptr;
    int32 FloodClockMs=0;
    SoraFloodRules::FRoute FloodRoute;
    FVector FloodLast=FVector::ZeroVector;
    bool bFloodFloating=false;
    float FloodOldGravity=1.f, FloodOldAirControl=.05f, FloodOldFriction=0.f;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> FloodSurfaces;
    UPROPERTY() TArray<TObjectPtr<APointLight>> FloodLights;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> FloodBoat;
    bool bFloodCarrying=false;
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
    // Smoke banks: the drum of smoke each hangs in over its ring (its foot,
    // radius and top), what shows it, and the ms it has left.
    struct FSmoke
    {
        TWeakObjectPtr<UStaticMeshComponent> Bank;
        int32 LeftMs = 0;
        FVector Foot = FVector::ZeroVector;
        float RadiusCm = 0.f;
        float TopCm = 0.f;
    };
    TArray<FSmoke> Smoke;
    // Seizure nets: each quarry's net, its drone, health and siege carry;
    // the drones that net (and how many of each net wave have joined), the
    // scouts, the reload of each drone whose net was cut, and the one drone
    // sent across the road to the hero's right.
    struct FQuarryState
    {
        SoraFieldcraftRules::FNet Net = SoraFieldcraftRules::FreeNet();
        TWeakObjectPtr<ASoraEnemy> Drone;
        int32 Hp = 0;
        int32 SiegeMs = 0;
        bool bLost = false;
        // Freed, it is let be this long (the cut net's drone reloads).
        int32 GraceMs = 0;
        TWeakObjectPtr<UStaticMeshComponent> NetMesh;
    };
    TArray<FQuarryState> QuarryStates;
    TArray<TWeakObjectPtr<ASoraEnemy>> Netters;
    TArray<int32> NettersJoined;
    TArray<TWeakObjectPtr<ASoraEnemy>> Scouts;
    TMap<TWeakObjectPtr<ASoraEnemy>, int32> NetRearm;
    TArray<TWeakObjectPtr<ASoraEnemy>> Crossers;
    TWeakObjectPtr<ASoraEnemy> Crosser;
    bool bDroneCrossed = false;
    int32 StringShyMs = 0;
    FDelegateHandle MeleeHandle;
    // Searchlights: time the hero's head has spent in each spot, whether it
    // shines, and where it is locked after a detection.
    struct FLightState
    {
        int32 InSpotMs = 0;
        bool bOn = false;
        // Current visibility is separate from exposure, which decays after
        // the hero leaves the beam or takes cover.
        bool bSeesHero = false;
        int32 LockedMs = 0;
        FVector LockedAt = FVector::ZeroVector;
        bool bSpookedHorses = false;
        TWeakObjectPtr<USpotLightComponent> Lamp;
        TWeakObjectPtr<UStaticMeshComponent> Spot;
    };
    TArray<FLightState> LightStates;
    int32 LightClockMs = 0;
    // The bell.
    bool bBellStaged = false;
    int32 BellUses = 0;
    // Cook-fires: lit, and the marks passed.
    TArray<bool> FiresLit;
    UPROPERTY() TArray<TObjectPtr<ASoraLamp>> FireActors;
    int32 FireMarks = 0;
    int32 LastProgress = 0;
    // Ladders: the one being climbed, up or down, and how far; the roof he
    // last stood on, and the roof a fall started from (INDEX_NONE: none).
    int32 LadderClimb = INDEX_NONE;
    bool bLadderUp = true;
    float LadderAlong = 0.f;
    int32 RoofFall = INDEX_NONE;
    float RoofFallZ = 0.f;
    int32 RoofStood = INDEX_NONE;
    float RoofStandZ = 0.f;
    // The charge: the riders (the rival first), the pack's lead chainage, the
    // stakes and when the pack reached each still standing.
    UPROPERTY() TArray<TObjectPtr<ASoraHorse>> Riders;
    UPROPERTY() TArray<TObjectPtr<ASoraSealStake>> Stakes;
    TArray<int32> StakeArrows;
    TArray<int32> StakeHeldMs;
    TArray<float> StakeChainage;
    float PackChainage = 0.f;
    int32 RiderClockMs = 0;
    int32 RiderStrikeCount = 0;
};
