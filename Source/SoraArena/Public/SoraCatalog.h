#pragma once
#include "CoreMinimal.h"
#include "SoraBeatRules.h"
#include "SoraMountRules.h"

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
// A HUD prompt: a UI string, never a voiced line.
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
    bool Contains(const FVector& Location) const
    {
        return FMath::Abs(Location.X - Center.X) <= Size.X * .5f && FMath::Abs(Location.Y - Center.Y) <= Size.Y * .5f;
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
    bool Contains(const FVector& Location) const { return Rect.IsInside(FVector2D(Location)); }
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
// Where a beat happens: its zone (INDEX_NONE for the arena hub), where a
// travel cut places the hero, its anchor and task points, trigger volumes,
// opponent spawns and patrols, and what the world builds for its task.
struct FSoraBeatSpace
{
    int32 Zone = INDEX_NONE;
    FVector2D Entry = FVector2D::ZeroVector;
    float EntryYaw = 0.f;
    FVector2D Anchor = FVector2D::ZeroVector;
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
    FString Place;
    FString Title;
    FString TitleEnglish;
    int32 TargetSeconds = 0;
    SoraBeatRules::FTask Task;
    TArray<FSoraWave> Waves;
    // Dialogue: its lines, the event that starts them ("beat_start",
    // "volume_enter:<id>", "interact:<id>") and, for one that ends at an
    // anchor, the event that ends it.
    TArray<int32> Lines;
    FString LinesEvent;
    FString ClosingEvent;
    // A stealth zone's exit or a ride's destination ("volume_enter:<id>"), if named.
    FString ExitEvent;
    // Named points, for the events they raise: objectives, pickups, drop-offs,
    // defended targets and the kinds of the manufacturing steps.
    TArray<FString> Objectives;
    TArray<FString> Pickups;
    TArray<FString> Dropoffs;
    // What a carry moves ("barley_load"): its pickups and deliveries also
    // raise item_picked:<item> and item_delivered:<item>.
    FString CarryItem;
    TArray<FString> Targets;
    TArray<FString> StepKinds;
    // A duel's opponent or the boss; sparring beats use bokuto, shinai or targets.
    FName Opponent;
    bool bSparring = false;
    // A stealth zone's guards, by enemy type.
    TArray<FName> Guards;
    // A duel's scripted events, one per later phase, and the interaction that
    // binds a captured boss ("interact:bulkhead_lever").
    TArray<FString> PhaseEvents;
    FString CaptureEvent;
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
