#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraMountRules.h"
#include "SoraHorse.generated.h"
class ASoraPlayerCharacter;
class UBoxComponent;
class USceneComponent;
class UStaticMeshComponent;
struct FSoraMount;
struct FSoraZone;

// A native Japanese horse (bible §4.5): about 130 cm at the withers, stocky,
// short-legged and heavy-maned. No horse is imported into Content/Generated
// yet (the Nyaagyu horse remains a source-only anatomy study), so her body is
// a primitive proxy in her coat's colour with period tack: a riding horse's
// kura on front and rear arches, aori flaps, the girth, broad abumi on both
// sides with the SORA mon on their front plates, bit, headstall, cloth tazuna
// and crupper; a pack horse's 荷鞍 with two loads slung either side. The
// legs swing in each gait's footfall order (a lateral walk, a diagonal trot)
// as placeholders for an equine animator's cycles.
// Ridden, she follows SoraMountRules: the rider's legs (MoveForward held),
// urging (Sprint with it) and reins (MoveForward back) set her gait,
// MoveRight steers, and on a road she keeps to it while the rider leaves the
// reins alone (auto-steer). The rider mounts and dismounts on her right. Her
// box sweeps against walls and cover; shots, blades and pawns pass through.
UCLASS()
class SORAARENA_API ASoraHorse : public AActor
{
    GENERATED_BODY()
public:
    enum class ETack : uint8 { Bare, Riding, Pack };
    ASoraHorse();
    virtual void Tick(float DeltaSeconds) override;
    // Builds her body in a coat (chestnut, bay, black_bay) with her tack.
    void Build(FName Coat, ETack Tack);
    // Tack-up: the riding tack's first Pieces pieces (kura, girth, abumi, bit and tazuna).
    void ShowTack(int32 Pieces);
    int32 TackPieces() const { return TackParts.Num(); }
    // A ride's rules, its road (or none) and whether she keeps to it.
    void SetRide(const FSoraMount& Mount, const FSoraZone* InRoad);
    bool Mount(ASoraPlayerCharacter& Rider);
    void Dismount();
    ASoraPlayerCharacter* Rider() const { return RiderPawn.Get(); }
    // A location in her frame: x toward her head, y to her right (cm).
    FVector2D LocalOf(const FVector& Location) const;
    // A pack horse walks a road at a pace (a convoy), or trails a leader on a rope.
    void FollowRoad(const FSoraZone* InRoad, float StartChainage, int32 PaceCmS);
    void Lead(ASoraHorse* InLeader, float SpacingCm);
    void SetWaiting(bool bWait) { bWaiting = bWait; }
    // Places her, halted, on the ground at Location facing Yaw.
    void Place(const FVector& Location, float Yaw);
    // A hazard entered her fear radius, or the road spooks her.
    void Spook() { bSpookPending = true; }
    // The fastest gait the road, a forced stretch or a laden pack mare allows.
    SoraMountRules::EGait Cap = SoraMountRules::EGait::Gallop;
    bool bAutoSteer = false;
    SoraMountRules::EGait Gait() const { return Ride.Gait; }
    int32 StaminaPoints() const { return Ride.Stamina / 1000; }
    bool IsSpooked() const { return SoraMountRules::Spooked(Ride); }
    bool IsWinded() const { return Ride.GallopLocked; }
    int32 SpeedCmS() const { return SoraMountRules::SpeedCmS(Ride, Rules); }
    float RoadChainage() const { return Chainage; }
    const SoraMountRules::FHorse& RideRules() const { return Rules; }
    // Her back, where a rider's eye sits, above the ground.
    static constexpr float RiderEyeCm = 225.f;
private:
    UPROPERTY() TObjectPtr<UBoxComponent> Frame;
    UPROPERTY() TObjectPtr<USceneComponent> Body;
    UPROPERTY() TObjectPtr<USceneComponent> Head;
    UPROPERTY() TArray<TObjectPtr<USceneComponent>> Hips;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Parts;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> TackParts;
    TWeakObjectPtr<ASoraPlayerCharacter> RiderPawn;
    TWeakObjectPtr<ASoraHorse> Leader;
    SoraMountRules::FHorse Rules;
    SoraMountRules::FRide Ride;
    const FSoraZone* Road = nullptr;
    float Chainage = 0.f;
    int32 PaceCmS = 0;
    float LeadSpacing = 0.f;
    bool bWaiting = false;
    bool bSpookPending = false;
    float ClockCarryMs = 0.f;
    float LegPhase = 0.f;
    UStaticMeshComponent* Part(USceneComponent* Parent, const FString& Name, const TCHAR* Shape, FVector Location,
        FVector Scale, FLinearColor Color, FRotator Rotation = FRotator::ZeroRotator);
    USceneComponent* Joint(USceneComponent* Parent, const FString& Name, FVector Location);
    void BuildRidingTack();
    void BuildPackSaddle();
    // Moves her Delta cm along the ground, sliding along whatever blocks her.
    void Move(const FVector& Delta, float Yaw);
    void TickRidden(int32 DeltaMs, float DeltaSeconds);
    void TickLed(int32 DeltaMs, float DeltaSeconds);
    void TickRoad(int32 DeltaMs, float DeltaSeconds);
    void Animate(float DeltaSeconds);
};
