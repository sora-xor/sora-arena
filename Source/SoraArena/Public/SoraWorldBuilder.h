#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraWorldBuilder.generated.h"
class ASoraHorse;
class ASoraPlayerCharacter;
class USkeletalMeshComponent;
class UStaticMeshComponent;
class UMaterialInterface;
struct FSoraPracticeMap;
struct FSoraChapter;
struct FSoraZone;
struct FSoraProp;

// What the active beat's task kit shows (SoraWorldBuilderLayoutTasks.cpp).
struct FSoraKitView
{
    // The task's progress, 0-1000: water risen, a lift or a hold filled.
    int32 ProgressPermille = 0;
    // A manufacture's current step, and how many strokes are done in all.
    int32 Step = 0;
    int32 Strokes = 0;
    // Each defended target's health, 0-1.
    TArray<float> TargetHealth;
    // Carry: the load in hand, loads taken from each pickup, delivered to each drop-off.
    bool bCarrying = false;
    TArray<bool> PickupTaken;
    TArray<int32> Delivered;
    // A hold with an opponent in it; a crank gone slack.
    bool bContested = false;
    bool bSlack = false;
    // Where the escorted party stands, and which way they face.
    TArray<FVector> Party;
    float PartyYaw = 0.f;
    bool bPartyWalking = false;
};

// Builds the world at runtime. The training arena's shared layout (ground,
// walls, building rows, cover, torii, production sites and lanterns) lives in
// Private/World/SoraWorldBuilder.cpp; each map's dressing lives in its own
// Private/World/SoraMap*.cpp file, lighting in SoraWorldBuilderLighting.cpp
// and the kernel-defined practice map in SoraWorldBuilderPractice.cpp. A
// campaign chapter is built from its space (FSoraSpace): the hub arena when a
// place is the arena itself, plus walled zones and route corridors
// (SoraWorldBuilderLayout.cpp, SoraWorldBuilderLayoutZones.cpp) and each
// beat's task kit, loose collectibles and caches
// (SoraWorldBuilderLayoutTasks.cpp). Campaign geometry never touches the
// kernel's practice collision. Authored props are visual only; the primitive
// boxes remain the gameplay collision.
UCLASS()
class SORAARENA_API ASoraWorldBuilder : public AActor
{
    GENERATED_BODY()
public:
    ASoraWorldBuilder();
    void Build(int32 MapId, const FSoraChapter* Chapter = nullptr);
    void BuildPractice(int32 MapId, const FSoraPracticeMap& Map);
    bool ActivateNearest(const FVector& Location);
    int32 NearestInactiveNode(const FVector& Location) const;
    int32 ActiveNodes() const { return Activated.Num(); }
    int32 ActivatedMask() const;
    void RestoreActivatedMask(int32 Mask);
    // The training arena's invader spawns.
    FVector SpawnPoint(int32 Index) const;
    // Shows the marker over the active objective; nullptr hides it.
    void ShowObjective(const FVector* Location);
    // Explore caches: an unmarked chest with a lantern glow (bible §12.2).
    // Caches already standing where asked are left as they are.
    void ShowCaches(const TArray<FVector>& Locations);
    const TArray<TObjectPtr<AActor>>& CacheGlows() const { return CacheLights; }
    // A site restored by its beat, wherever the hero stands.
    void ActivateSite(int32 Index);
    FVector ExitPoint() const { return FVector(2250,0,110); }
    // A campaign chapter starts at its first beat's entry. The arena begins
    // far enough west of the entrance torii to frame the gate and estate in
    // first person instead of spawning with the camera under a beam.
    FVector PlayerStart() const;
    float PlayerStartYaw() const { return bCampaignSpace ? CampaignStartYaw : 0.f; }
    // The active beat's task kit (SoraWorldBuilderLayoutTasks.cpp): built as
    // the beat starts, shown as its task goes on, cleared with the beat.
    void StageKit(const FSoraChapter& Chapter, int32 Beat);
    void ShowKit(const FSoraKitView& View);
    void ClearKit();
    // The chapter's collectibles still lying loose (indices into its pickups).
    void ShowPickups(const FSoraChapter& Chapter, const TArray<int32>& Loose);
    // A carried load in the hero's arms (NAME_None: nothing).
    void ShowCarried(ASoraPlayerCharacter* Hero, FName Item);
    // The staged kit's kind, how high its gauge (water, lift) stands, and
    // whether a load is in the hero's arms.
    FName ActiveKit() const { return KitWork; }
    float KitGaugeHeight() const;
    bool IsCarryingLoad() const { return CarriedLoad != nullptr; }
    static FVector Floor(const FVector2D& Point, float Height = 0.f) { return FVector(Point.X, Point.Y, Height); }
    static UStaticMeshComponent* Shape(AActor* Owner, USceneComponent* Parent, const FString& Name, const TCHAR* Asset, FVector Location, FVector Scale, FLinearColor Color, bool Collision = false);
    static void Tint(UStaticMeshComponent* Mesh, FLinearColor Color);
    static void Surface(UStaticMeshComponent* Mesh, const FString& Role, FLinearColor Color = FLinearColor::White);
    TArray<FVector> NodePositions;
private:
    // Campaign spaces (SoraWorldBuilderLayout.cpp, SoraWorldBuilderLayoutZones.cpp).
    void BuildArena(int32 MapId, bool bSites);
    void BuildCampaign(const FSoraChapter& Chapter);
    void BuildZone(const FSoraZone& Zone, int32 Index);
    void ZoneProp(const FSoraZone& Zone, const FSoraProp& Prop, int32 Index);
    void ZoneLantern(FVector Location, bool bLit);
    bool bCampaignSpace = false;
    FVector CampaignStart = FVector::ZeroVector;
    float CampaignStartYaw = 0.f;
    // Task kit, pickups and the carried load (SoraWorldBuilderLayoutTasks.cpp).
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> KitPieces;
    UPROPERTY() TArray<TObjectPtr<AActor>> KitActors;
    // The escorted party: one root per member, a villager or a cart under it.
    UPROPERTY() TArray<TObjectPtr<USceneComponent>> KitParty;
    UPROPERTY() TArray<TObjectPtr<USkeletalMeshComponent>> KitWalkers;
    // Pieces the kit moves or tints as the task goes on.
    UPROPERTY() TObjectPtr<UStaticMeshComponent> KitGauge;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> KitWheel;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> KitFill;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> KitStations;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> KitTargets;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> KitStacks;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> KitLoads;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> PickupPieces;
    UPROPERTY() TArray<TObjectPtr<AActor>> PickupLights;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> CarriedLoad;
    UPROPERTY() TObjectPtr<AActor> KitLight;
    FName KitWork;
    FVector KitAnchor = FVector::ZeroVector;
    float KitHoldRadius = 0.f;
    // Carry: the item's kind, each drop-off, and the loads shown delivered there.
    FName KitItemKind;
    TArray<FVector> KitDropoffs;
    TArray<int32> KitDeliveredShown;
    UStaticMeshComponent* KitShape(const FString& Name, const TCHAR* Asset, FVector Location, FVector Scale, FLinearColor Color,
        const FString& SurfaceRole = TEXT(""), bool Collision = false);
    ASoraHorse* KitHorse(FVector Location, float Yaw, FName Coat, bool bPack);
    USceneComponent* KitMember(FName Kind, FVector Location, float Yaw);
    void KitItem(FName Item, FVector Location, int32 Index, TArray<TObjectPtr<UStaticMeshComponent>>& Into);
    // One production site: its base and core, and the kind's own structure.
    void SiteStructure(int32 Index, FVector P, const FString& Kind, int32 StyleMap, FLinearColor Accent);
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Pieces;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Nodes;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> SiteEffects;
    TArray<FLinearColor> SiteRestoredColors;
    UPROPERTY() TArray<TObjectPtr<AActor>> DecorActors;
    TSet<int32> Activated;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> ObjectiveMarker;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> CacheMarkers;
    UPROPERTY() TArray<TObjectPtr<AActor>> CacheLights;
    TArray<FVector> CacheLocations;
    // Shared layout (SoraWorldBuilder.cpp).
    UStaticMeshComponent* Box(const FString& Name, FVector Location, FVector Size, FLinearColor Color, bool Collision = true, FRotator Rotation = FRotator::ZeroRotator, const FString& SurfaceRole = TEXT(""));
    void Building(FVector Location, FVector Size, FLinearColor Wall, bool HighTech);
    bool ImportedProp(const FString& Name, FVector Location, FRotator Rotation, float Scale = 1.f);
    void Torii(FVector Location, float Yaw);
    void ProductionSites(int32 MapId, FLinearColor Accent);
    void Lanterns();
    void ClearArena();
    // Sun, sky, fog and grade per map (SoraWorldBuilderLighting.cpp).
    void Lighting(int32 MapId);
    // Nyaagyu Estate, map 0 (SoraMapNyaagyuEstate.cpp).
    void NyaagyuTerrain();
    void NyaagyuTree(FVector Location, FRotator Rotation, float Scale);
    void NyaagyuPine(FVector Location, FRotator Rotation, float Scale, int32 Variant);
    void EstatePerimeter(int32 S, UStaticMeshComponent* WallX, UStaticMeshComponent* WallY);
    void EstateHall(int32 I, int32 S, FVector P, int32 BuildingStart);
    void EstateGrounds();
    void EstateCargo(int32 I, FVector Location, UStaticMeshComponent* Cover);
    void EstateSluice(FVector P);
    // Lantern Ward, map 1 (SoraMapLanternWard.cpp).
    void LanternWardTerminal();
    // Silk Foundry, map 2 (SoraMapSilkFoundry.cpp).
    void SilkFoundryLoom(FVector P);
    // Debt Citadel, map 3 (SoraMapDebtCitadel.cpp).
    void DebtCitadelKiosk();
};
