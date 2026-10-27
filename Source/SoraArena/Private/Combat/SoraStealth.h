#pragma once
#include "CoreMinimal.h"
#include "SoraStealthRules.h"
#include "Subsystems/WorldSubsystem.h"
#include "SoraStealth.generated.h"
class ASoraEnemy;
class ASoraEnemyController;
class ASoraPlayerCharacter;

// One stealth beat's rules (story bible §12.2 stealth_zone; also a production
// task with stealth: true). The campaign director fills it from the beat's
// data and the campaign difficulty.
struct FSoraStealthZone
{
    // detection {suspicion_rate, suspicious_at, search_s, wary_after_search}
    // before the difficulty's scaling.
    SoraStealthRules::FVigilance Vigilance = SoraStealthRules::Watchful();
    SoraStealthRules::EDifficulty Difficulty = SoraStealthRules::EDifficulty::Normal;
    SoraStealthRules::EOnDetected OnDetected = SoraStealthRules::EOnDetected::Combat;
    // takedowns {rear, lethal_default}
    bool bRearTakedowns = true;
    bool bLethalDefault = false;
    // bodies {discoverable, drag}
    bool bBodiesDiscoverable = true;
    bool bDragBodies = true;
    // The hero was detected in the zone before (x_on_detected_carryover):
    // its guards start suspicious and wary.
    bool bCarriedOver = false;
};

// What the HUD shows for one guard: where its head is, how alarmed it is and
// how full its meter.
struct FSoraStealthMark
{
    TWeakObjectPtr<ASoraEnemy> Enemy;
    FVector Head = FVector::ZeroVector;
    SoraStealthRules::EState State = SoraStealthRules::EState::Unaware;
    int32 MeterPermille = 0;
};

struct FSoraStealthReadout
{
    bool bZone = false;
    // The most alarmed guard's state and meter.
    SoraStealthRules::EState Worst = SoraStealthRules::EState::Unaware;
    int32 MeterPermille = 0;
    // Guards whose meter is filling or who are alarmed.
    TArray<FSoraStealthMark> Marks;
    // Light where the hero stands and his carried light, both x1000.
    int32 LightPermille = 0;
    int32 VisibilityPermille = 1000;
    bool bCrouched = false;
    bool bSeen = false;
    bool bDetected = false;
    bool bAlarm = false;
    // A rear takedown or a body to move is within reach; the hero drags one.
    bool bTakedown = false;
    // The guard in reach is debt-bound: the takedown is always 峰打ち.
    bool bTakedownSubdues = false;
    bool bLethalDefault = false;
    bool bDrag = false;
    bool bDragging = false;
};

// Detection and the alarm are announced once per zone; Response is the zone's
// on_detected on the difficulty.
struct FSoraStealthDetection
{
    TWeakObjectPtr<ASoraEnemy> By;
    SoraStealthRules::EOnDetected Response = SoraStealthRules::EOnDetected::Combat;
    // Evidence held by the detector/alarm sender, never sampled later from
    // the hero's current position. Synthetic detections may have no point.
    TOptional<FVector> KnownLocation;
};

DECLARE_MULTICAST_DELEGATE_OneParam(FSoraStealthDetectedSignature, const FSoraStealthDetection&);
DECLARE_MULTICAST_DELEGATE_OneParam(FSoraStealthAlarmSignature, ASoraEnemy*);
DECLARE_MULTICAST_DELEGATE_TwoParams(FSoraStealthBodySignature, ASoraEnemy* /*Body*/, ASoraEnemy* /*Finder*/);

/**
 * The stealth zone of the current beat, shared by the guards' brains, the
 * hero's takedowns and the HUD. It holds the zone's rules, its noise surfaces
 * and alarm lecterns, the bodies left on the floor, and whether the hero has
 * been detected or the alarm raised; it runs the hero's rear takedowns and
 * body dragging. Guards are the opponents that start on a patrol or post; a
 * combat wave's hunters never obey a zone. Outside a zone the guards keep
 * SoraStealthRules::Watchful(), bodies are not searched for and takedowns are
 * off. All timing is world time on fixed patterns; nothing is random.
 */
UCLASS()
class USoraStealth : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    static USoraStealth* Get(const UObject* WorldContext);

    // Opens a zone: bodies, detection and the alarm start clear, and guards
    // already posted take the zone's start (carryover). A checkpoint that
    // restores the beat opens it again. A takedown still being decided lets
    // its guard go unalarmed.
    void BeginZone(const FSoraStealthZone& Zone);
    // Closes the zone and forgets its surfaces, lecterns and bodies. A
    // takedown still being decided lets its guard go: the beat is over, so
    // nobody is detected and nobody is called.
    void EndZone();
    bool IsZoneActive() const { return bZoneActive; }
    const FSoraStealthZone& Zone() const { return ZoneRules; }
    // The zone's vigilance on its difficulty, or Watchful() outside a zone.
    SoraStealthRules::FVigilance Vigilance() const;

    // Layout: floors that change footsteps, and the alarm lecterns an auditor
    // runs to (ch06 alarm_points).
    void AddSurface(const FBox& Volume, SoraStealthRules::FSurface Surface);
    SoraStealthRules::FSurface SurfaceAt(const FVector& Feet) const;
    void AddAlarmPoint(const FVector& Location);
    const TArray<FVector>& AlarmPoints() const { return Lecterns; }
    // What the hero carries (a lit candle 2000, cupped 1200, nothing 1000).
    void SetHeroVisibility(int32 Permille) { CarriedLight = FMath::Clamp(Permille, 0, 4000); }
    int32 HeroVisibility() const { return CarriedLight; }
    // The light proxy (SoraStealthRules::LightPermille) at a place: the key
    // light and every lamp that reaches it.
    int32 LightAt(const FVector& Location) const;

    // Reports from the guards' brains.
    void NoteState(ASoraEnemy& Guard, SoraStealthRules::EState Previous, SoraStealthRules::EState Next);
    void RaiseAlarm(ASoraEnemy& By, const FVector& Where);
    // Fixed sensors can detect the hero even when every guard is down.
    void RaiseSensorAlarm(const FVector& Where);
    void AddBody(ASoraEnemy& Body);
    // Undiscovered bodies a guard may still find.
    TArray<ASoraEnemy*> UnfoundBodies() const;
    void FindBody(ASoraEnemy& Body, ASoraEnemy& Finder);
    bool IsDetected() const { return bDetected; }
    bool IsAlarmRaised() const { return bAlarm; }
    // A noise every brain hears at once (a takedown's scuffle), at Loudness
    // (x1000 of the kind's own; a roof's authored drop reaches as its script says).
    void MakeNoise(SoraStealthRules::ENoise Kind, const FVector& Origin, const FVector& Evidence, const AActor* Source,
        int32 LoudnessPermille = 1000) const;
    // Work under guard: any guard sees the hero or is alarmed.
    bool IsWorkPaused() const;

    // The hero's side. Melee pressed behind an unsuspecting guard starts a
    // takedown (true: the press is spent), released decides a tap; Interact
    // pressed at a body starts dragging it, released drops it.
    bool BeginTakedown(ASoraPlayerCharacter& Hero);
    void ReleaseTakedown();
    bool IsHeroBusy() const { return bTakedownActive; }
    ASoraEnemy* TakedownTarget(const ASoraPlayerCharacter& Hero) const;
    bool BeginDrag(ASoraPlayerCharacter& Hero);
    void EndDrag();
    bool IsDragging() const { return Dragged.IsValid(); }
    ASoraEnemy* DragTarget(const ASoraPlayerCharacter& Hero) const;
    // The hero's walking pace while he drags a body, x1.
    float HeroMoveScale() const;

    FSoraStealthReadout Readout(const ASoraPlayerCharacter& Hero) const;

    FSoraStealthDetectedSignature OnDetected;
    FSoraStealthAlarmSignature OnAlarm;
    FSoraStealthBodySignature OnBodyFound;

    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    virtual void Deinitialize() override;
protected:
    virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
private:
    void RaiseAlarmFrom(ASoraEnemy* By,const FVector& Where);
    struct FBody
    {
        TWeakObjectPtr<ASoraEnemy> Enemy;
        bool bFound = false;
    };
    struct FFloor
    {
        FBox Volume;
        SoraStealthRules::FSurface Surface;
    };
    void TickTakedown();
    void TickDrag();
    // Lets go of the takedown under way. An undecided victim is roused (it
    // felt the grab) unless the zone itself is closing or restarting.
    void AbortTakedown(bool bRouse);
    void FinishTakedown(ASoraEnemy& Target, ASoraPlayerCharacter& Hero);
    void UnlockHero();
    double Now() const;
    bool bZoneActive = false;
    FSoraStealthZone ZoneRules;
    TArray<FFloor> Floors;
    TArray<FVector> Lecterns;
    TArray<FBody> Bodies;
    int32 CarriedLight = 1000;
    bool bDetected = false;
    bool bAlarm = false;
    // The takedown under way; the hero's movement input is held meanwhile.
    bool bTakedownActive = false;
    bool bMoveLocked = false;
    TWeakObjectPtr<ASoraEnemy> Victim;
    TWeakObjectPtr<ASoraPlayerCharacter> Taker;
    double TakedownStartedAt = 0.0;
    bool bTakedownHeld = false;
    bool bTakedownDecided = false;
    SoraStealthRules::ETakedown TakedownKind = SoraStealthRules::ETakedown::Knockout;
    // The body being dragged.
    TWeakObjectPtr<ASoraEnemy> Dragged;
    TWeakObjectPtr<ASoraPlayerCharacter> Dragger;
};
