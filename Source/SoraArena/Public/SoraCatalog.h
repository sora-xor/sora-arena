#pragma once
#include "CoreMinimal.h"
#include "SoraBeatRules.h"
#include "SoraFieldcraftRules.h"
#include "SoraMountRules.h"
#include "SoraRegistry.h"
#include "SoraSpireRules.h"

struct FSoraWeapon
{
    int32 Id = 0;
    int32 ClassId = 0;
    FString Name;
    FString NameEnglish;
    FString Kind;
    FString Tradeoff;
    float Damage = 25.f;
    float Cooldown = .3f;
    float Range = 6500.f;
    float Reload = 1.5f;
    int32 Magazine = 12;
    float BlastRadius = 0.f;
    float ProjectileSpeed = 2400.f;
    bool Special = false;
};
struct FSoraClass
{
    int32 Id = 0;
    FString Name;
    FString NameEnglish;
    FString Role;
    FString RoleEnglish;
    float Health = 120.f;
    float Speed = 560.f;
    TArray<int32> Weapons;
};
struct FSoraDialogueSpeaker
{
    FString Japanese;
    FString English;
};
struct FSoraHero
{
    FString NameJapanese;
    FString NameEnglish;
    int32 KatanaId = 0;
    int32 YumiId = 18;
    int32 QuiverArrows = 12;
};
// One bilingual line of a chapter file. Lines carry no start time: a trigger
// (FSoraDialogueTrigger) or a dialogue beat decides when each one plays.
struct FSoraDialogueCue
{
    FString Id;
    // The beat the line belongs to, or INDEX_NONE for a chapter-wide bark pool.
    int32 Beat = INDEX_NONE;
    FString SpeakerId;
    FString Japanese;
    FString English;
    float DurationSeconds = 0.f;
    // Empty inherits the event's mode; an explicit ambient/radio line keeps control.
    FString Mode;
    bool bRepeatable = false;
};
// A row of the chapter's event-keyed trigger table: "beat_start",
// "boss_phase:2", "site_restored:0", or "subtitle" (a cinematic line at AtMs).
// A conditional row plays only once its collectible is found or its story
// flag is set.
struct FSoraDialogueTrigger
{
    int32 Beat = INDEX_NONE;
    FString On;
    FString Mode;
    TArray<int32> Lines;
    int32 AtMs = INDEX_NONE;
    bool bRepeatable = false;
    float CooldownSeconds = 0.f;
    unsigned long long RequiresCollectible = 0ull;
    unsigned RequiresFlags = 0u;
};
struct FSoraProductionSite
{
    FString Name;
    FString NameEnglish;
    FString Restored;
    FString RestoredEnglish;
    FString Kind;
    // The beat whose completion restores the site.
    int32 Beat = INDEX_NONE;
    int32 RequiredSitesMask = 0;
};
struct FSoraCollectible
{
    FString Id;
    FString Category;
    // Chapter-local bit 0-5; the save keeps chapter * 6 + MaskBit.
    int32 MaskBit = 0;
    FString Place;
    // The explore beats whose cache holds it; opening one collects it.
    TArray<int32> Beats;
    // Otherwise it lies loose in the world: its FSoraSpace pickup.
    int32 Pickup = INDEX_NONE;
    FString Codex;
    FString CodexEnglish;
};
// A HUD prompt: a UI string, never a voiced line. It names keys only as
// {Action} tokens for input actions, which the HUD replaces with the player's
// own keys (SoraHUDPanels::KeyPrompt).
struct FSoraPrompt
{
    TArray<int32> Beats;
    FString On;
    FString Japanese;
    FString English;
};

// A bilingual label from campaign.json: a mechanic, a manufacturing step or a
// defended target.
struct FSoraLabel
{
    FString Japanese;
    FString English;
};

// A chapter's space (scripts/unreal/campaign_space.py), in the world frame:
// integer centimetres about the arena centre, every floor at z 0.
struct FSoraBox
{
    FVector2D Center = FVector2D::ZeroVector;
    FVector2D Size = FVector2D::ZeroVector;
    float Height = 0.f;
};
// A visual-only prop: an imported mesh, or "pine", "tree", "building" and
// "building_hightech" for the world builder's own dressing.
struct FSoraProp
{
    FName Mesh;
    FVector2D At = FVector2D::ZeroVector;
    float Yaw = 0.f;
};
// A trigger volume: the hero standing inside it raises Event.
struct FSoraVolume
{
    FString Event;
    FVector2D Center = FVector2D::ZeroVector;
    FVector2D Size = FVector2D::ZeroVector;
    bool bHeight = false;
    int32 FloorCm = 0;
    bool Contains(const FVector& Location) const
    {
        return (!bHeight || (Location.Z >= FloorCm - 20 && Location.Z <= FloorCm + 200)) &&
            FMath::Abs(Location.X - Center.X) <= Size.X * .5f && FMath::Abs(Location.Y - Center.Y) <= Size.Y * .5f;
    }
};
// A walled zone for a place, or a route corridor with its road.
struct FSoraZone
{
    FString Id;
    FString Place;
    // estate, ward, foundry or citadel; hall, yard, field or route.
    FName Style;
    FName Form;
    FBox2D Rect = FBox2D(ForceInit);
    float WallHeight = 0.f;
    FVector2D Entry = FVector2D::ZeroVector;
    float EntryYaw = 0.f;
    TArray<FSoraBox> Walls;
    TArray<FSoraBox> Cover;
    TArray<FSoraProp> Props;
    TArray<FVector2D> Route;
    float RouteLength = 0.f;
    bool IsRoute() const { return Route.Num() >= 2; }
    bool bHeightBounds = false;
    int32 MinZ = 0, MaxZ = 0;
    bool Contains(const FVector& Location) const
    { return Rect.IsInside(FVector2D(Location))&&(!bHeightBounds||(Location.Z>=MinZ&&Location.Z<MaxZ)); }
    // The road's point Chainage cm from its start, and how far along the road
    // a point stands (projected onto its nearest stretch).
    FVector2D PointAlong(float Chainage) const;
    float ChainageOf(const FVector2D& Point) const;
    // The road's heading at a chainage, in degrees.
    float HeadingAt(float Chainage) const;
};
struct FSoraTackStep
{
    FString Id;
    FName Part;
    // Presses refused before she accepts it, and what a refusal waits for.
    int32 Refusals = 0;
    FString Gift;
};
struct FSoraGaitCap
{
    int32 FromCm = 0;
    int32 ToCm = 0;
    SoraMountRules::EGait Gait = SoraMountRules::EGait::Walk;
};
struct FSoraForcedGait
{
    FString Volume;
    SoraMountRules::EGait Gait = SoraMountRules::EGait::Walk;
};
// A pack horse beside the ride: a convoy walking the road ahead, or a laden
// mare led on a rope behind.
struct FSoraPackHorse
{
    FString Id;
    FName Follow;
    int32 SpeedCmS = 0;
    int32 SpacingCm = 0;
    // A convoy horse's health (ch02.b08 convoy.hp); 0 for a led mare.
    int32 Hp = 0;
};
// The horse a ride, or a mounted fight's opening phases, puts under the hero.
struct FSoraMount
{
    FName Horse;
    FName Coat;
    // Starts in the saddle; otherwise tacked up (Tack) and mounted from the right.
    bool bMounted = true;
    TArray<FSoraTackStep> Tack;
    SoraMountRules::FHorse Rules;
    // A live opponent this close spooks her (0: nothing does); so does
    // entering one of the Spooks volumes.
    int32 FearRadiusCm = 0;
    TArray<FString> Spooks;
    TArray<FSoraGaitCap> Caps;
    TArray<FSoraForcedGait> Forced;
    bool bDismount = true;
    // The horse follows the road unless the rider steers.
    bool bAutoSteer = false;
    // A mounted fight: the rider dismounts as this phase begins (0: never).
    int32 UntilPhase = 0;
    TArray<FSoraPackHorse> Pack;
    FVector2D At = FVector2D::ZeroVector;
};
// A beat's fieldcraft (scripts/unreal/campaign_fieldcraft.py), played by
// USoraFieldcraft with SoraFieldcraftRules.h.
// A lamp or fire the guards see by: how far it lights and how it goes dark
// (Interact held HoldMs beside it, an arrow or round on its cable junction,
// or never), and after how long it comes back (0: it stays dark).
struct FSoraLamp
{
    enum class ESnuff : uint8 { Hold, Shot, None };
    FString Id;
    FName Kind;
    FVector2D At = FVector2D::ZeroVector;
    float RadiusCm = 0.f;
    ESnuff Snuff = ESnuff::None;
    int32 HoldMs = 0;
    int32 RelightMs = 0;
};
// A floor that changes footsteps (SoraStealthRules::FSurface), on the
// ground or on a roof HeightCm up.
struct FSoraFloorPatch
{
    FName Kind;
    FSoraVolume Area;
    int32 HeightCm = 0;
    int32 StepPermille = 1000;
    int32 CrouchPermille = 1000;
};
// Water to swim and dive in, the reeds and lotus that hide a swimmer's head,
// and the float lines that ring when touched at the surface.
struct FSoraWater
{
    FSoraVolume Area;
    SoraFieldcraftRules::FWaterRules Rules{};
    int32 SurfaceStepPermille = 1000;
    TArray<FSoraVolume> Cover;
    TArray<FSoraVolume> Lines;
    TArray<int32> LineNoiseCm;
};
// A face to climb: its foot's centre, the way it faces, its width, depth and
// height, its holds' rules, and the events its ledges and top raise.
struct FSoraClimbFace
{
    FVector2D At = FVector2D::ZeroVector;
    float Yaw = 0.f;
    float WidthCm = 0.f;
    float DepthCm = 0.f;
    SoraFieldcraftRules::FClimbRules Rules{};
    TArray<FString> LedgeEvents;
    FString TopEvent;
};
struct FSoraStones
{
    int32 Carried = 0;
    int32 Max = 0;
    int32 NoiseCm = 0;
    int32 InvestigateMs = 0;
    TArray<FVector2D> Piles;
};
// Someone who walks or fights beside the hero. An escorted party member
// (Role escort) walks the road; Release is the cell door that holds it.
struct FSoraCompanionSpec
{
    FString Id;
    FName Role;
    int32 WeaponId = INDEX_NONE;
    SoraFieldcraftRules::FCompanionRules Rules{};
    FVector2D At = FVector2D::ZeroVector;
    bool bDetectable = true;
    int32 Release = INDEX_NONE;
    // The event it joins the fight on ("wave_start:3"), or empty: from the start.
    FString Joins;
    // A volley rank's gunner: its rank (0 is the first), or INDEX_NONE.
    int32 Rank = INDEX_NONE;
};
// A defended person at a target, or a crank helper (Target INDEX_NONE)
// at its work and an existing cover slot.
struct FSoraDefendedPerson
{
    FString Id;
    int32 Target = INDEX_NONE;
    FVector2D At = FVector2D::ZeroVector;
    FVector2D Cover = FVector2D::ZeroVector;
};
// Rotating volley ranks the hero commands (ch08 volley_command): the ranks
// are the beat's allies with a Rank, PerRank to a rank, all with WeaponId.
struct FSoraVolley
{
    SoraFieldcraftRules::FVolleyRules Rules{};
    int32 PerRank = 0;
    int32 WeaponId = INDEX_NONE;
    // The white smoke bank each volley leaves, and whether Easy may order for the hero.
    int32 SmokeMs = 0;
    bool bAutoOrder = false;
};
// An alarm lectern an auditor runs to.
struct FSoraAlarmPoint
{
    FString Id;
    FVector2D At = FVector2D::ZeroVector;
};
// Seizure nets: what the drones of NetWaves net (a convoy's pack horses by
// id, an escort's cart, a defence's people by target), how a net is cut, and
// which waves only scout. A pack horse or the cart has health opponents can
// wear down.
struct FSoraNetQuarry
{
    FString Id;
    int32 Index = INDEX_NONE;
    int32 Hp = 0;
};
struct FSoraNets
{
    enum class EKind : uint8 { PackHorse, Cart, Person };
    EKind Kind = EKind::Person;
    TArray<FSoraNetQuarry> Quarry;
    SoraFieldcraftRules::FNetRules Rules{};
    // A blade from the saddle on this side (1 right, -1 left) cuts a net; INDEX_NONE: none.
    int32 SaddleWeapon = INDEX_NONE;
    int32 SaddleSide = 0;
    bool bHalts = false;
    // The waves whose drones net, and how many of each wave's drones net (the
    // rest hang off the road as scouts); the waves whose drones only scout.
    TArray<int32> NetWaves;
    TArray<int32> NetsPerWave;
    TArray<int32> ScoutWaves;
    // One netting drone of CrossWave crosses the road to the hero's right
    // once he passes CrossAtCm along it (ch02.b08 G4); INDEX_NONE: none.
    int32 CrossWave = INDEX_NONE;
    int32 CrossAtCm = 0;
    // Raised when a quarry is hauled off (convoy_member_seized), or empty.
    FString LostEvent;
};
// A searchlight: on a wall (At, HeightCm up, facing Yaw, its spot ReachCm
// out) sweeping its arc, or over a road sweeping from RoadFromCm to RoadToCm
// once ActiveOn is raised, spooking the horses its spot comes near.
struct FSoraSearchlight
{
    FString Id;
    FVector2D At = FVector2D::ZeroVector;
    float HeightCm = 0.f;
    float Yaw = 0.f;
    float ReachCm = 0.f;
    int32 RoadFromCm = 0;
    int32 RoadToCm = 0;
    SoraFieldcraftRules::FSearchlightRules Rules{};
    FString ActiveOn;
    bool bSpooks = false;
    bool IsRoad() const { return RoadToCm > 0; }
};
// A one-shot lure object hanging HeightCm up (ch07.b04's temple bell).
struct FSoraBell
{
    FString Id;
    FVector2D At = FVector2D::ZeroVector;
    float HeightCm = 0.f;
    SoraFieldcraftRules::FBellRules Rules{};
};
// A hold's cook-fires: where each stands, the progress marks (permille) at
// which the next gutters, and how long a relight is held.
struct FSoraFires
{
    TArray<FString> Ids;
    TArray<FVector2D> Points;
    TArray<int32> OutAt;
    int32 RelightMs = 0;
};
// A ladder onto a roof: its foot and the way it faces, the roof it reaches
// and how high, how far the thud of a drop from it is heard (drop_noise_cm),
// the straw that softens one, and the zone's guards posted up there (by
// their index).
struct FSoraLadder
{
    FString Id;
    FVector2D Foot = FVector2D::ZeroVector;
    float Yaw = 0.f;
    FSoraVolume Roof;
    float HeightCm = 0.f;
    int32 DropNoiseCm = 0;
    bool bStraw = false;
    FSoraVolume Straw;
    TArray<int32> Guards;
};
// The League's charge (ch08.b02): Riders in a column of twos with the rival
// at the hero's right, their pace and how far they ease for a hero left
// behind, and the seal stakes across the road.
struct FSoraCharge
{
    int32 Riders = 0;
    FString Rival;
    int32 PaceCmS = 0;
    int32 CatchUpCmS = 0;
    int32 StakeBreakMs = 0;
    TArray<FString> StakeIds;
    TArray<FVector2D> Stakes;
};
struct FSoraRelease
{
    FString Id;
    FVector2D At = FVector2D::ZeroVector;
    int32 HoldMs = 0;
};
struct FSoraFieldcraft
{
    TArray<FSoraLamp> Lamps;
    TArray<FSoraFloorPatch> Floors;
    bool bWater = false;
    FSoraWater Water;
    bool bClimb = false;
    FSoraClimbFace Climb;
    bool bStones = false;
    FSoraStones Stones;
    bool bCandle = false;
    SoraFieldcraftRules::FCandle Candle{};
    float CandleRadiusCm = 0.f;
    TArray<FSoraCompanionSpec> Party;
    bool bSignal = false;
    TArray<FVector2D> HideSpots;
    TArray<FSoraRelease> Releases;
    TArray<FSoraCompanionSpec> Allies;
    TArray<FSoraDefendedPerson> People;
    bool bVolley = false;
    FSoraVolley Volley;
    TArray<FSoraAlarmPoint> Alarms;
    bool bNets = false;
    FSoraNets Nets;
    TArray<FSoraSearchlight> Searchlights;
    bool bBell = false;
    FSoraBell Bell;
    bool bFires = false;
    FSoraFires Fires;
    TArray<FSoraLadder> Ladders;
    bool bCharge = false;
    FSoraCharge Charge;
    bool IsEmpty() const
    {
        return Lamps.IsEmpty() && Floors.IsEmpty() && !bWater && !bClimb && !bStones && !bCandle && Party.IsEmpty() &&
            Allies.IsEmpty() && People.IsEmpty() && Alarms.IsEmpty() && !bNets && Searchlights.IsEmpty() && !bBell &&
            !bFires && Ladders.IsEmpty() && !bCharge;
    }
};

// A guard a stealth zone posts: its enemies.json archetype and the senses
// the chapter authors for it. 0 (sight, view cone, suspicion) or -1 (dark
// sight, hearing) keeps the archetype's own.
struct FSoraGuard
{
    FName Type;
    int32 SightCm = 0;
    int32 DarkSightCm = -1;
    int32 ViewDegrees = 0;
    int32 HearingCm = -1;
    int32 SuspicionPermille = 0;
    // A post it keeps rather than a round it walks; the arc it sweeps there
    // and the ms a sweep takes (0: the brain's own look about), or how often
    // it turns about (0: never).
    bool bPost = false;
    int32 ScanDegrees = 0;
    int32 ScanMs = 0;
    int32 TurnMs = 0;
};
// A stealth zone's authored rules (bible §12.2 detection, takedowns,
// x_bodies, x_on_detected_carryover) before the difficulty's scaling.
struct FSoraStealthRulesData
{
    int32 RatePermille = 1000;
    int32 SuspiciousAtPermille = 250;
    int32 SearchMs = 12000;
    int32 WaryPermille = 1200;
    bool bRearTakedowns = true;
    bool bLethalDefault = false;
    bool bBodies = true;
    bool bDrag = true;
    // A detection here starts that later zone's guards suspicious and wary.
    FString CarryoverTo;
};

// Where a beat happens: its zone (INDEX_NONE for the arena hub), where a
// travel cut places the hero, its anchor and task points, trigger volumes,
// opponent spawns and patrols, and what the world builds for its task.
struct FSoraLiftSpace
{
    bool bEnabled=false;
    FVector2D Size=FVector2D::ZeroVector;
    int32 BottomCm=0,TopCm=0;
    TArray<int32> GantryCm;
    FBox2D Gallery;
    FVector2D GalleryExit=FVector2D::ZeroVector;
};
struct FSoraSpireSpace
{
    FVector2D Center = FVector2D::ZeroVector;
    TArray<FVector> Ramp;
    TArray<FVector> Spawns;
    bool Enabled() const { return Ramp.Num()==SoraSpireRules::NodeCount; }
};
struct FSoraSummitSpace
{
    FVector2D Center = FVector2D::ZeroVector;
    TArray<FVector> Stairs;
    bool Enabled() const { return Stairs.Num()==6; }
};
struct FSoraBeatSpace
{
    FSoraSummitSpace Summit;
    FSoraSpireSpace Spire;
    int32 HeightCm=0;
    FSoraLiftSpace Lift;
    int32 Zone = INDEX_NONE;
    FVector2D Entry = FVector2D::ZeroVector;
    float EntryYaw = 0.f;
    FVector2D Anchor = FVector2D::ZeroVector;
    FVector2D Recovery = FVector2D::ZeroVector;
    FVector2D CarryGate = FVector2D::ZeroVector;
    TArray<FVector2D> Objectives;
    TArray<FVector2D> Pickups;
    TArray<FVector2D> Dropoffs;
    TArray<FVector2D> Targets;
    TArray<FVector2D> Stations;
    TArray<int32> StepStations;
    TArray<FVector2D> Spawns;
    TArray<TArray<FVector2D>> Patrols;
    TArray<FSoraVolume> Volumes;
    FSoraVolume Exit;
    bool bClosing = false;
    FVector2D Closing = FVector2D::ZeroVector;
    bool bCache = false;
    FVector2D Cache = FVector2D::ZeroVector;
    // A cinematic's camera: it dollies from From to To looking at Look.
    bool bCamera = false;
    FVector CameraFrom = FVector::ZeroVector;
    FVector CameraTo = FVector::ZeroVector;
    FVector CameraLook = FVector::ZeroVector;
    // A ride or escort runs on its zone's road; an escorted party walks from
    // RouteMarginCm to RouteMarginCm short of the end.
    bool bRoute = false;
    int32 RouteMarginCm = 0;
    // The task's kit: sluice, bellows, lift, hold, stations, carry, defend or
    // escort; the carried item; and the kind of each pickup, drop-off, target
    // and escorted party member.
    FName Work;
    FName Item;
    TArray<FName> PickupKinds;
    TArray<FName> DropoffKinds;
    TArray<FName> TargetKinds;
    TArray<FName> Party;
    bool bMount = false;
    FSoraMount Mount;
    FSoraFieldcraft Fieldcraft;
};
// A collectible lying loose in a zone.
struct FSoraPickup
{
    int32 Collectible = INDEX_NONE;
    int32 Zone = INDEX_NONE;
    FVector2D At = FVector2D::ZeroVector;
};
struct FSoraSpace
{
    // The arena built at the origin as the hub, or INDEX_NONE.
    int32 Hub = INDEX_NONE;
    FVector2D Start = FVector2D::ZeroVector;
    float StartYaw = 0.f;
    TArray<FSoraZone> Zones;
    TArray<FVector2D> Sites;
    TArray<FSoraPickup> Pickups;
    // The zone a location stands in, INDEX_NONE for the hub, or -2 for neither.
    int32 ZoneAt(const FVector& Location) const;
};

// One spawn group of a wave: its enemy type (bible §7, Content/Data/enemies.json
// once the AI lane lands it), how many, and whether they count toward the wave.
struct FSoraWaveGroup
{
    FName Type;
    int32 Count = 0;
    bool bLethal = true;
    // A scripted opponent that takes no damage (ch08.b02's sweep-only walkers).
    bool bInvulnerable = false;
};
struct FSoraWave
{
    FString Id;
    // The event that releases a volume or event wave ("volume_enter:vol_x",
    // "alert_state:alert"); empty for the waves the beat's own rules release.
    FString Event;
    TArray<FSoraWaveGroup> Groups;
};

// A beat of a chapter. Its task (SoraBeatRules.h) decides what completes it,
// which waves it releases, its phases and what a failure does; the rest names
// the lines, points and opponents the director puts in the world.
struct FSoraBeat
{
    FString Id;
    TArray<FString> CrankNpcs;
    FString Place;
    FString Title;
    FString TitleEnglish;
    int32 TargetSeconds = 0;
    SoraBeatRules::FTask Task;
    TOptional<FSoraRegistryEntry> Registry;
    TArray<FSoraWave> Waves;
    // Dialogue: its lines, the event that starts them ("beat_start",
    // "volume_enter:<id>", "interact:<id>") and, for one that ends at an
    // anchor, the event that ends it.
    TArray<int32> Lines;
    // A dialogue's blocking lines (ext blocking_lines): when the last of them
    // ends the beat raises blocking_end and play is the player's again.
    TArray<int32> BlockingLines;
    FString LinesEvent;
    FString ClosingEvent;
    // A stealth zone's exit or a ride's destination ("volume_enter:<id>"), if named.
    FString ExitEvent;
    // Named points, for the events they raise: objectives, pickups, drop-offs,
    // defended targets and the kinds of the manufacturing steps.
    TArray<FString> Objectives;
    TArray<FString> Pickups;
    TArray<FString> Dropoffs;
    // Exact authored map; Task capacities use this array of drop-off names.
    TMap<FString, int32> DropoffCapacities;
    // What a carry moves ("barley_load"): its pickups and deliveries also
    // raise item_picked:<item> and item_delivered:<item>.
    FString CarryItem;
    FString CarryGatePoint;
    FString RecoveryItem;
    FString RecoveryInteract;
    // Authored supply station identity; it grants ammunition, never unlocks.
    FString SupplyPoint;
    TArray<FString> Targets;
    TArray<FString> StepKinds;
    // A duel's opponent or the boss; sparring beats use bokuto, shinai or targets.
    FName Opponent;
    bool bSparring = false;
    // Each objective's hold (ms of Interact held to work it; 0: a press).
    TArray<int32> ObjectiveHoldMs;
    // The guards a stealth zone, or a production task under guard, posts on
    // its patrols, with the senses the script authors for each, and the
    // zone's own rules.
    TArray<FSoraGuard> Guards;
    bool bStealth = false;
    FSoraStealthRulesData Stealth;
    // A duel's scripted events, one per later phase, and the interaction that
    // binds a captured boss ("interact:bulkhead_lever").
    TArray<FString> PhaseEvents;
    FString CaptureEvent;
    int32 CaptureHoldMs=0;
    // The beat's `fail` rows by event.
    TMap<FString, SoraBeatRules::EFail> FailEvents;
    // Collectibles in an explore beat's cache.
    TArray<int32> Rewards;
    FSoraBeatSpace Space;
    bool Is(SoraBeatRules::EType Type) const { return Task.Type == Type; }
    bool Has(SoraBeatRules::EGoal Goal) const { return Task.Goal == Goal; }
};
struct FSoraChapter
{
    FString Id;
    FString Title;
    FString TitleEnglish;
    FString Narrative;
    FString NarrativeEnglish;
    FString Objective;
    FString ObjectiveEnglish;
    int32 Map = 0;
    int32 TargetSeconds = 0;
    TArray<FSoraProductionSite> Sites;
    TArray<FSoraBeat> Beats;
    // Beats[I]'s gates and tasks, contiguous for SoraBeatRules.
    TArray<SoraBeatRules::FBeat> Rules;
    TArray<SoraBeatRules::FTask> Tasks;
    TArray<FSoraDialogueCue> Dialogue;
    TArray<FSoraDialogueTrigger> Triggers;
    TArray<FSoraCollectible> Collectibles;
    TArray<FSoraPrompt> Prompts;
    FSoraSpace Space;
    int32 BeatIndex(const FString& BeatId) const;
    int32 LineIndex(const FString& LineId) const;
};
struct FSoraMap
{
    FString Name;
    FString NameEnglish;
    FLinearColor Accent = FLinearColor(.1f,.6f,.6f);
};
struct FSoraCollectibleCategory
{
    FString Id;
    FString Japanese;
    FString English;
    int32 Count = 0;
};

/**
 * Offline authored content, loaded fail-closed: Content/Data/catalog.json
 * (schema 4) for weapons, classes, maps, the hero and the dialogue speakers;
 * Content/Data/campaign/campaign.json for the chapter index, title cards, site
 * labels, mechanic flags and story flags with the labels of mechanics,
 * manufacturing steps and defended targets; and campaign/chapter_0N.json,
 * generated by scripts/unreal/build_campaign_data.py, for beats and their
 * tasks, lines, triggers, checkpoints, unlocks, collectibles, prompts and
 * the chapter's space (read by SoraCatalogSpace.cpp).
 * Financial rules are deliberately absent.
 */
class SORAARENA_API FSoraCatalog
{
public:
    static constexpr int32 ChapterCount = 8;
    static constexpr int32 CollectiblesPerChapter = 6;
    static FSoraCatalog& Get();
    bool Load();
    const FSoraWeapon& Weapon(int32 Id) const;
    const FSoraClass& Class(int32 Id) const;
    const FSoraChapter& Chapter(int32 Id) const;
    const FSoraDialogueSpeaker* DialogueSpeaker(const FString& Id) const;
    const FSoraHero& Hero() const { check(bReady); return HeroData; }
    const FSoraMap& Map(int32 Id) const;
    bool IsReady() const { return bReady; }
    // Unlock masks a chapter may be entered with: the weapons every route
    // through the earlier chapters holds (optional pickups skipped), every
    // weapon they offer (what chapter select grants), and their mechanics.
    unsigned RouteMinimumWeapons(int32 Chapter) const;
    unsigned EarlierWeapons(int32 Chapter) const;
    unsigned EarlierMechanics(int32 Chapter) const;
    // Story flags the earlier chapters can set (optional beats included).
    unsigned EarlierFlags(int32 Chapter) const;
    FString Error;
    TArray<FSoraWeapon> Weapons;
    TArray<FSoraWeapon> CampaignWeapons;
    TArray<FSoraClass> Classes;
    TArray<FSoraChapter> Chapters;
    TMap<FString, FSoraDialogueSpeaker> DialogueSpeakers;
    FSoraHero HeroData;
    TArray<FSoraMap> Maps;
    // Mechanic flags and story flags in bit order, with the mechanics' labels.
    TArray<FString> Mechanics;
    TArray<FSoraLabel> MechanicLabels;
    TArray<FString> StoryFlags;
    TArray<FSoraCollectibleCategory> CollectibleCategories;
    // Manufacturing steps and defended targets by id.
    TMap<FString, FSoraLabel> StepLabels;
    TMap<FString, FSoraLabel> TargetLabels;
private:
    bool LoadCampaign();
    // A chapter file's space block (SoraCatalogSpace.cpp).
    bool LoadSpace(const class FJsonObject& Data, FSoraChapter& Chapter);
    bool Fail(const FString& Message);
    bool bReady = false;
};
