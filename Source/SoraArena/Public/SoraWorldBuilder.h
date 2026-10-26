#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SoraMarginRules.h"
#include "SoraWorldBuilder.generated.h"
class ASoraFoundryFurnace;
class ADirectionalLight;
class AExponentialHeightFog;
class ASkyLight;
class APointLight;
class ARectLight;
class APostProcessVolume;
class ASoraHorse;
class ASoraCampaignLift;
class ASoraBoss;
class ASoraBridgeProp;
class ASoraEnemy;
class UProceduralMeshComponent;
class ASoraPlayerCharacter;
class UTextureCube;
class ACharacter;
class USkeletalMeshComponent;
class UStaticMeshComponent;
class UTextRenderComponent;
class UWidgetComponent;
class UFont;
class UMaterialInterface;
struct FSoraPracticeMap;
struct FSoraChapter;
struct FSoraBeat;
struct FSoraBeatSpace;
struct FSoraZone;
struct FSoraProp;

// What the active beat's task kit shows (SoraWorldBuilderLayoutTasks.cpp).
struct FSoraKitView
{
    // The task's progress, 0-1000: water risen, a lift or a hold filled.
    int32 ProgressPermille = 0;
    TArray<int32> HoldProgressPermille;
    // A manufacture's current step, and how many strokes are done in all.
    int32 Step = 0;
    int32 Strokes = 0;
    int32 BellowsNotches = 1;
    int32 BellowsFoot = 0;
    int32 RhythmStep = -1;
    int32 RhythmElapsedMs = 0;
    int32 RhythmPeriodMs = 0;
    int32 RhythmHitAgeMs = -1;
    // Each defended target's health, 0-1.
    TArray<float> TargetHealth;
    // Carry: the load in hand, loads taken from each pickup, delivered to each drop-off.
    bool bCarrying = false;
    TArray<bool> PickupTaken;
    TArray<int32> Delivered;
    unsigned LooseMask = 0u;
    TArray<FVector> LooseLoads;
    bool bCarryGateOpen = true;
    // A hold with an opponent in it; a crank gone slack.
    bool bContested = false;
    bool bSlack = false;
    // Where the escorted party stands, and which way they face.
    TArray<FVector> Party;
    float PartyYaw = 0.f;
    bool bPartyWalking = false;
};

USTRUCT()
struct FSoraSummitTile
{
    GENERATED_BODY()
    int32 X=0,Y=0,State=0;
    bool bSelected=false;
    FVector2D Stand=FVector2D::ZeroVector;
    TArray<FVector2D> Outline;
    UPROPERTY() TObjectPtr<UProceduralMeshComponent> Mesh;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Edges;
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
    virtual void Tick(float DeltaSeconds) override;
    void Build(int32 MapId, const FSoraChapter* Chapter = nullptr);
    void BuildPractice(int32 MapId, const FSoraPracticeMap& Map);
    // The practice arena's dressing kit (Private/World/SoraPracticeArena.h).
    friend struct FSoraPracticeArenaKit;
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
    bool HasBridgeDeck() const { return bBridgeActive&&BridgeRoot!=nullptr&&BridgeProps.Num()==10; }
    bool BeginBridgeMargin(ASoraBoss& Boss,int32 Attack,int32 Serial);
    bool BridgeMarginPoints(const ASoraPlayerCharacter& Hero,TArray<FVector>& Points) const;
    const TArray<TObjectPtr<UStaticMeshComponent>>& BridgeConsoles() const { return MarginConsoles; }
    const TArray<int32>& MarginTargetIds() const { return MarginIds; }
    int32 MarginDestroyedCount() const { return MarginState.Destroyed; }
    int32 MarginConsoleHits(int32 Id) const { return Id>=0&&Id<SoraMarginRules::Consoles?MarginState.Hits[Id]:-1; }
    int32 MarginLingerMs() const { return MarginState.HeldMs; }
    int32 MarginPinnedConsole() const { return MarginState.Pinned; }
    bool MarginIsPending() const { return MarginElapsedMs>=0; }
    bool BeginBridgeSlide(ASoraBoss& Boss,int32 Attack,int32 Serial);
    float BridgeMoveScale(const ACharacter& Body,const FVector& Intent) const;
    float BridgeListDegrees() const { return BridgeDegrees; }
    USceneComponent* BridgeDeckRoot() const { return BridgeRoot; }
    const TArray<TObjectPtr<ASoraBridgeProp>>& BridgeLooseProps() const { return BridgeProps; }
    void StageHelm(const FSoraBeat& Beat);
    void ShowHelm(bool NeedsTrim,float HeldFraction);
    bool CanReachHelm(const ASoraPlayerCharacter& Hero) const;
    void BuildFlood(const FSoraBeat& Beat);
    void BuildMoat(const FSoraBeat& Beat);
    void BuildLanding(const FSoraZone& Zone);
    void BuildWardGate(const FSoraZone& Zone);
    void BuildClimb(const FSoraBeat& Beat);
    void BuildRelayRoom(const FSoraBeat& Beat);
    void BuildPalace(const FSoraZone& Zone);
    void BuildLedger(const FSoraZone& Zone);
    void BuildArchive(const FSoraZone& Zone,const FSoraZone& Press);
    void ShowArchivePage(const FSoraBeat& Beat,int32 Phase);
    void StageArchiveReveal(float Seconds);
    void StageKit(const FSoraChapter& Chapter, int32 Beat);
    void ShowKit(const FSoraKitView& View);
    void ClearKit();
    ASoraHorse* DefendedHorse(int32 Index) const { return DefendedHorses.IsValidIndex(Index)?DefendedHorses[Index].Get():nullptr; }
    ASoraFoundryFurnace* FoundryTarget() const;
    void ShowFoundrySupplies(unsigned Used,unsigned Netted);
    ASoraCampaignLift* CampaignLift() const;
    FVector RidgeAnchorFloor(int Index) const;
    int32 ReachRidgeCable(const ASoraPlayerCharacter& Hero) const;
    bool WindLee(const ASoraPlayerCharacter& Hero) const;
    bool WindShelteredPoint(const FVector& Point) const;
    bool SupplyFloor(const FString& Id,FVector& Out) const;
    bool CanReachSupply(const FString& Id,const ASoraPlayerCharacter& Hero) const;
    bool CanReachWoodPoi(int32 Index,const ASoraPlayerCharacter& Hero) const;
    bool IsWoodClapperHit(const FHitResult& Hit) const;
    bool GalleryPoiFloor(FName Id,FVector& Out) const;
    bool CanReachGalleryPoi(FName Id,const ASoraPlayerCharacter& Hero) const;
    void ShowGalleryPois(int32 FoundMask);
    bool GalleryLabelVisible() const;
    bool GalleryMonVisible() const;
    // Only an active spire's hunting auditors use these physical L3 panels.
    // A shout never closes the shortcut; arrival checks the actual floor.
    bool SpireAlarmGoal(const ASoraEnemy& Auditor,FVector& Out) const;
    bool TrySpireAlarm(const ASoraEnemy& Auditor);
    bool SpireShortcutClosed() const { return bSpireClosed; }
    bool SpireAlarmPending() const { return bSpireAlarmPending; }
    FVector SpireShutterFloor() const { return SpireShutterAt-FVector(0,0,150); }
    // The campaign summit owns the real seizure floor. Other arenas retain
    // the generic boss zone implementation.
    bool BeginSeizure(ASoraBoss& Boss,int32 Attack,int32 Serial,int32 WarningMs);
    int32 SeizurePattern() const { return SummitPattern; }
    bool SummitSafePoint(const FVector& From,const ACharacter& Body,FVector& Out) const;
    FVector SummitSpineApproach() const { return SummitCenter+FVector(0,-320,120); }
    FVector SummitSpinePoint() const { return SummitCenter+FVector(0,-201,220); }
    bool CanReachSummitSpine(const ASoraPlayerCharacter& Hero) const;
    void ShowSummitSpine(bool Ready,float CutProgress=0.f);
    void StageBulkhead(const FSoraBeat& Beat);
    FVector BulkheadPoint() const { return BulkheadAt+FVector(11,0,100); }
    FVector BulkheadApproach() const { return BulkheadAt+FVector(140,0,0); }
    bool CanReachBulkhead(const ASoraPlayerCharacter& Hero) const;
    void ShowBulkhead(bool Ready,float Progress);
    void ShowRecoveryBundle(bool Visible);
    void ShowEpilogue(bool SwordFound, bool SwordReturned, int32 Plaques);
    int32 RehungPlaques() const { return EpiloguePlaques; }
    bool WashioSwordReturned() const { return bEpilogueSwordReturned; }
    // The chapter's collectibles still lying loose (indices into its pickups).
    void ShowPickups(const FSoraChapter& Chapter, const TArray<int32>& Loose);
    // A carried load in the hero's arms (NAME_None: nothing).
    void ShowCarried(ASoraPlayerCharacter* Hero, FName Item);
    // The staged kit's kind, how high its gauge (water, lift) stands, and
    // whether a load is in the hero's arms.
    FName ActiveKit() const { return KitWork; }
    float KitGaugeHeight() const;
    bool IsCarryingLoad() const { return CarriedLoad != nullptr; }
    int32 LooseLoadVisualCount() const;
    int32 CargoStandCount() const { return CargoStandLoads.Num()/2; }
    int32 CargoQuantityShownAt(int32 Destination) const;
    static FVector Floor(const FVector2D& Point, float Height = 0.f) { return FVector(Point.X, Point.Y, Height); }
    static UStaticMeshComponent* Shape(AActor* Owner, USceneComponent* Parent, const FString& Name, const TCHAR* Asset, FVector Location, FVector Scale, FLinearColor Color, bool Collision = false);
    static void Tint(UStaticMeshComponent* Mesh, FLinearColor Color);
    static void Surface(UStaticMeshComponent* Mesh, const FString& Role, FLinearColor Color = FLinearColor::White);
    TArray<FVector> NodePositions;
private:
    // Campaign spaces (SoraWorldBuilderLayout.cpp, SoraWorldBuilderLayoutZones.cpp).
    void BuildArena(int32 MapId, bool bSites);
    void BuildCampaign(const FSoraChapter& Chapter);
    void BuildChapterWood(const FSoraChapter& Chapter);
    TArray<FVector> WoodFloors;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> WoodTargets;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> WoodClapper;
    void BuildWindSpace(const FSoraBeat& Beat);
    FVector2D RidgeOrigin=FVector2D::ZeroVector;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> RidgeAnchors;
    void BuildSpire(const FSoraBeat& Beat);
    void StageSupply(const FSoraBeat& Beat);
    void StageGalleryPois(const FSoraChapter& Chapter,const FSoraBeat& Beat);
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> GalleryTargets;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> GalleryLabel;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> GalleryMon;
    TArray<FName> GalleryIds;
    TArray<FVector> GalleryFloors;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> SupplyCrate;
    FString SupplyId;
    FVector SupplyAt=FVector::ZeroVector;
    void ResetSpireAlarm(bool Active);
    void TickSpireAlarm();
    UPROPERTY() TObjectPtr<UStaticMeshComponent> SpireShutter;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> SpirePanels;
    TArray<FVector> SpirePanelGoals;
    FVector SpireShutterAt=FVector::ZeroVector;
    FRotator SpireShutterRotation=FRotator::ZeroRotator;
    bool bSpireActive=false,bSpireClosed=false,bSpireAlarmPending=false;
    void BuildSummit(const FSoraBeat& Beat);
    FVector SummitCenter=FVector::ZeroVector;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> SummitSpine;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> SummitSeam;
    FVector BulkheadAt=FVector::ZeroVector;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> BulkheadLever;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> BulkheadHandle;
    void BuildSummitTiles();
    void ClearSummitTiles();
    void ResetSeizure();
    void TickSeizure();
    UPROPERTY() TArray<FSoraSummitTile> SummitTiles;
    TWeakObjectPtr<ASoraBoss> SummitBoss;
    int32 SummitPattern=-1,SummitFieldStarted=-1,SummitWarningMs=1500,SummitFieldSerial=0;
    int32 SummitAttackIndex=INDEX_NONE;
    bool bSummitActive=false,bSummitStrikeAnnounced=false;
    void BuildBridge(const FSoraZone& Zone,int32 Index,const FSoraBeat& Beat);
    void StageBridge(bool Active);
    void TickBridge(float DeltaSeconds);
    void ClearBridge();
    void StageMargin(bool Restore);
    void CancelMargin();
    void TickMargin(float DeltaSeconds,const ASoraBoss* Boss);
    void SelectMarginTargets(const ASoraPlayerCharacter& Hero,TArray<int32>& Ids,TArray<FVector>& LocalPoints) const;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> MarginConsoles;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> MarginMarks;
    SoraMarginRules::FState MarginState;
    TWeakObjectPtr<ASoraBoss> MarginBoss;
    TArray<int32> MarginIds;
    TArray<FVector> MarginPoints;
    int32 MarginAttack=INDEX_NONE,MarginSerial=0,MarginWarningMs=1500;
    double MarginElapsedMs=-1,MarginClockCarry=0;
    bool bMarginReleased=false;
    float BridgeCeilingCm=700;

    UPROPERTY() TObjectPtr<USceneComponent> BridgeRoot;
    UPROPERTY() TArray<TObjectPtr<ASoraBridgeProp>> BridgeProps;
    TArray<TWeakObjectPtr<ACharacter>> BridgeRiders;
    bool bBridgeActive=false;
    float BridgeDegrees=0.f;
    void BuildZone(const FSoraZone& Zone, int32 Index, const FSoraBeat* Recovery = nullptr);
    void ZoneProp(const FSoraZone& Zone, const FSoraProp& Prop, int32 Index);
    void ZoneLantern(FVector Location, bool bLit);
    // An estate hall's authored interior (SoraWorldBuilderDojoHall.cpp): false
    // when any kit module is missing, so the primitive visuals stay.
    bool HallInterior(const FSoraZone& Zone, int32 Index);
    bool bCampaignSpace = false;
    FVector CampaignStart = FVector::ZeroVector;
    float CampaignStartYaw = 0.f;
    // Task kit, pickups and the carried load (SoraWorldBuilderLayoutTasks.cpp).
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> KitPieces;
    void StageEpilogue(const FSoraBeat& Beat);
    UPROPERTY() TObjectPtr<UStaticMeshComponent> ArchivePage;
    UPROPERTY() TObjectPtr<UWidgetComponent> ArchivePageText;
    UPROPERTY() TObjectPtr<UFont> ArchivePageFont;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> ArchiveEastRack;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> ArchiveNorthGate;
    UPROPERTY() TObjectPtr<ARectLight> ArchivePageLight;
    UPROPERTY() TObjectPtr<APostProcessVolume> ArchiveExposure;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> ToranosukePlaque;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> NyaakotoPlaque;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> WashioSword;
    UPROPERTY() TArray<TObjectPtr<UTextRenderComponent>> EpilogueLabels;
    FVector EpilogueBoard = FVector::ZeroVector;
    FVector EpilogueSwordStand = FVector::ZeroVector;
    int32 EpiloguePlaques = 0;
    bool bEpilogueSwordReturned = false;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> RecoveryBundle;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> RecoveryHatch;
    UPROPERTY() TArray<TObjectPtr<AActor>> KitActors;
    UPROPERTY() TArray<TObjectPtr<ASoraHorse>> DefendedHorses;
    TWeakObjectPtr<ASoraFoundryFurnace> FoundryActor;
    TArray<TWeakObjectPtr<UStaticMeshComponent>> FoundryTubs,FoundryBellows;
    unsigned FoundryUsedShown=~0u;
    void BuildFoundryDefense(const FSoraBeatSpace& Space);
    UPROPERTY() TObjectPtr<ASoraCampaignLift> Lift;
    // The escorted party: one root per member, a villager or a cart under it.
    UPROPERTY() TArray<TObjectPtr<USceneComponent>> KitParty;
    UPROPERTY() TArray<TObjectPtr<USkeletalMeshComponent>> KitWalkers;
    // Pieces the kit moves or tints as the task goes on.
    FVector HelmAt=FVector::ZeroVector;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> HelmWheel;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> HelmNeedle;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> KitGauge;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> BellowsNotches;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> BellowsSparks;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> BellowsFeet;
    int32 BellowsShownBand = 0;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> KitWheel;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> KitFill;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> KitStations;
    // Functional workshop motions; authored character clips remain separate.
    void StageWorkshop(const FSoraBeat& Beat);
    void ShowWorkshop(const FSoraKitView& View);
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> WorkshopParts;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> WorkshopRing;
    FVector WorkshopAnchor = FVector::ZeroVector;
    int32 WorkshopStep = -1;
    bool bWorkshopHammer = false;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> KitTargets;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> KitStacks;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> KitLoads;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> KitLooseLoads;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> CargoStandLoads;
    int32 CargoUnitsPerShare = 0;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> CarrySeal;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> PickupPieces;
    UPROPERTY() TArray<TObjectPtr<AActor>> PickupLights;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> CarriedLoad;
    UPROPERTY() TObjectPtr<AActor> KitLight;
    FName KitWork;
    FVector KitAnchor = FVector::ZeroVector;
    float KitHoldRadius = 0.f;
    FVector2D KitHoldSize = FVector2D::ZeroVector;
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
    // The map's rig, re-aimed for an authored campaign beat: sun bearing and
    // colour temperature, overcast dome or atmospheric sky. Intensities, sky
    // light, exposure and fog never change; one rig serves every beat and retry.
    void BeatLight(const FSoraBeat& Beat);
    UPROPERTY() TObjectPtr<ADirectionalLight> RigSun;
    UPROPERTY() TObjectPtr<ASkyLight> RigSky;
    UPROPERTY() TObjectPtr<AExponentialHeightFog> RigFog;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> RigDome;
    UPROPERTY() TObjectPtr<UTextureCube> RigOvercast;
    FRotator RigDefaultRotation=FRotator::ZeroRotator;
    FLinearColor RigDefaultColor=FLinearColor::White;
    bool bRigDefaultRealTimeCapture=true;
    bool bRigAuthored=false;
    FString RigBeat;
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
