#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ArenaKernelSubsystem.h"
#include "SoraPracticeActors.generated.h"
class ASoraPracticePawn;
class UPointLightComponent;
class USceneComponent;
class UStaticMeshComponent;

// The presentation kit shared by practice actors and the practice arena.
// Everything it makes is visual only: parts never collide, so the Rust
// kernel stays the only collision and the only judge of every hit.
namespace SoraPracticeArt
{
// Engine shape paths for Part.
extern const TCHAR* const Cube;
extern const TCHAR* const Cylinder;
extern const TCHAR* const Cone;
extern const TCHAR* const Sphere;
// A registered static mesh part with no collision.
SORAARENA_API UStaticMeshComponent* Part(AActor* Owner, USceneComponent* Parent, const FString& Name, const TCHAR* Shape,
    FVector Location, FVector Scale, FRotator Rotation = FRotator::ZeroRotator);
// A flat colour on the arena surface material.
SORAARENA_API void Paint(UStaticMeshComponent* Mesh, FLinearColor Color, float Roughness = .6f, float Metallic = 0.f);
// A world-aligned photographed PBR surface: Timber, Stone, Metal, Plaster,
// Kawara, Soil, TerrainSoil or TerrainStone, tinted.
SORAARENA_API void Surface(UStaticMeshComponent* Mesh, const TCHAR* Role, FLinearColor Tint = FLinearColor::White);
// Additive light: lanterns, embers, wards and capture rings.
SORAARENA_API void Glow(UStaticMeshComponent* Mesh, FLinearColor Color, float Strength = 1.f);
// A point light in lumens. Shadows are costly on the Mac preset; most
// practice lights go without.
SORAARENA_API UPointLightComponent* Light(AActor* Owner, USceneComponent* Parent, const FString& Name, FVector Location,
    FLinearColor Color, float Lumens, float Radius, bool bShadows = false);
// A kamon disc facing local +X. bSora draws the SORA mark (the resistance,
// Content/SourceArt/UI/SORA_Resistance_Logo.png); otherwise the invaders'
// square-holed debt coin. Parts go into Out when given.
SORAARENA_API void Kamon(AActor* Owner, USceneComponent* Parent, const FString& Name, FVector Location, FRotator Rotation,
    float Diameter, float Thickness, bool bSora, FLinearColor Field, FLinearColor Mark, TArray<UStaticMeshComponent*>* Out = nullptr);
// A sashimono, the back banner Edo retainers wore to show their side: a
// pole and a flag in the team colour carrying the kamon, fixed behind the
// shoulders of a body whose capsule is Parent.
SORAARENA_API void Sashimono(AActor* Owner, USceneComponent* Parent, float HalfHeight, FLinearColor Color, bool bSora, bool bOwnerNoSee,
    TArray<UStaticMeshComponent*>* Out = nullptr);
// Team 0 (the SORA resistance) is lacquer red, team 1 (the invaders) cold
// cyan; free-for-all gives every slot its own colour.
SORAARENA_API FLinearColor TeamColor(int32 Team);
SORAARENA_API FLinearColor SlotColor(int32 Slot);
}

// One live ability entity from the kernel: a Shinobi decoy (a still body of
// its owner), a Karakuri barricade (exactly the kernel's box), a Hanabi fire
// zone or a Kusushi ward. The director presents it every tick and destroys it
// when the kernel removes it.
UCLASS()
class SORAARENA_API ASoraPracticeEntityActor : public AActor
{
    GENERATED_BODY()
public:
    ASoraPracticeEntityActor();
    // Color and bSora are the owner's side; Owner is the owner's state, which
    // a decoy copies. Map gives the decoy the kernel's body size.
    void Present(const FSoraPracticeEntity& Entity, FLinearColor Color, bool bSora, const FSoraPracticePlayer* Owner, bool bAlienBody, const FSoraPracticeMap& Map);
    const FSoraPracticeEntity& State() const { return Current; }
    ASoraPracticePawn* DecoyBody() const { return Decoy; }
    // The barricade's hidden trace box; null for other kinds.
    UStaticMeshComponent* Blocker() const { return Box; }
    virtual void Tick(float DeltaSeconds) override;
    virtual void Destroyed() override;
private:
    void Build(const FSoraPracticeEntity& Entity, FLinearColor Color, bool bSora, const FSoraPracticePlayer* Owner, bool bAlienBody, const FSoraPracticeMap& Map);
    FSoraPracticeEntity Current;
    bool bBuilt = false;
    float Time = 0.f;
    UPROPERTY() TObjectPtr<ASoraPracticePawn> Decoy;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Box;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Flames;
    UPROPERTY() TObjectPtr<USceneComponent> Talisman;
    UPROPERTY() TObjectPtr<UPointLightComponent> Lamp;
};

// The Control point: a stone plaza of the kernel's radius, a ring of lamps
// that fills with the capturing side's colour as progress moves, and the
// owner's kamon at the centre. Flat on the floor; nothing here is cover.
UCLASS()
class SORAARENA_API ASoraPracticeControlPoint : public AActor
{
    GENERATED_BODY()
public:
    static constexpr int32 Segments = 48;
    ASoraPracticeControlPoint();
    void Build(const FSoraPracticeMap& Map);
    void Present(const FSoraPracticeObjective& Objective, uint32 Tick);
    virtual void Tick(float DeltaSeconds) override;
    // Lamps lit for the side that leads the capture, and that side's team.
    int32 LitSegments() const { return Lit; }
    int32 LeadingTeam() const { return Leading; }
    int32 OwnerTeam() const { return Owner; }
private:
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Ring;
    // The owner's kamon for team 0 (SORA) and team 1 (the debt coin).
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> SoraEmblem;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> CoinEmblem;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Unclaimed;
    UPROPERTY() TObjectPtr<UPointLightComponent> Beacon;
    float Radius = 0.f, Time = 0.f;
    int32 Lit = -1, Leading = INDEX_NONE, Owner = -2;
    bool bContested = false, bLocked = true;
};

// The payload: a wooden cart of Nyaagyu goods on the kernel's route, with
// flat rails and sleepers along the route, a banded gate at each checkpoint
// and a floor ring at the push radius. The kernel gives the cart no
// collision, so it is no cover and shots pass through it here too.
UCLASS()
class SORAARENA_API ASoraPracticePayload : public AActor
{
    GENERATED_BODY()
public:
    ASoraPracticePayload();
    void Build(const FSoraPracticeMap& Map);
    // Place the cart this frame; the objective updates the ring and gates.
    void Present(const FSoraPracticeObjective& Objective, FVector Position);
    USceneComponent* Cart() const { return CartRoot; }
    int32 ReachedCheckpoints() const { return Reached; }
private:
    UPROPERTY() TObjectPtr<USceneComponent> CartRoot;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Wheels;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> PushRing;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Gates;
    UPROPERTY() TObjectPtr<UPointLightComponent> CartLamp;
    TArray<FVector> Route;
    float Travelled = 0.f;
    FVector LastPosition = FVector::ZeroVector;
    int32 Reached = -1, RingState = -1;
};
