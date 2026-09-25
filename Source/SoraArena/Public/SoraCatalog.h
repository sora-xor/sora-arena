#pragma once
#include "CoreMinimal.h"
#include "SoraBeatRules.h"

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
struct FSoraDialogueTrigger
{
    int32 Beat = INDEX_NONE;
    FString On;
    TArray<int32> Lines;
    int32 AtMs = INDEX_NONE;
    bool bRepeatable = false;
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
    // Completing any of these beats collects it.
    TArray<int32> Beats;
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

enum class ESoraBeatType : uint8
{
    Cinematic, Dialogue, CombatWave, Duel, StealthZone, ProductionTask, HorsebackRide, Boss, ExploreOptional
};
// What completes a beat in the offline runtime. Each type's parameters reduce
// to one of these until the stealth AI, mounts and Sequencer cinematics that
// specialise them arrive.
enum class ESoraBeatGoal : uint8
{
    Cinematic, // the letterboxed card for GoalSeconds; Enter skips it
    Lines,     // the beat's lines, in order
    Defeat,    // GoalCount defeated opponents
    Lessons,   // LessonMask's dojo forms, then GoalCount scored bouts
    Interact,  // GoalCount interactions at the beat's anchor
    Hold,      // GoalSeconds spent at the anchor
    Reach,     // the anchor reached
    Explore,   // an optional beat, completed at its unmarked cache
};
enum class ESoraOpponent : uint8 { None, Invader, Pupil, Boss };

struct FSoraBeat
{
    FString Id;
    ESoraBeatType Type = ESoraBeatType::Cinematic;
    FString Place;
    FString Title;
    FString TitleEnglish;
    int32 TargetSeconds = 0;
    ESoraBeatGoal Goal = ESoraBeatGoal::Cinematic;
    int32 GoalCount = 0;
    float GoalSeconds = 0.f;
    bool bSkippable = false;
    // Dialogue beats: whether the lines wait for the anchor (a volume, or an
    // interaction there), and whether the beat then ends at the anchor.
    bool bLinesAtAnchor = false;
    bool bLinesOnInteract = false;
    bool bReachAfterLines = false;
    TArray<int32> Lines;
    // The trigger event raised when the hero reaches or works the anchor
    // ("volume_enter:vol_back_gate", "interact:crate_iota"), if any.
    FString AnchorEvent;
    // Opponents: their kind, the lethal count over every wave (nonlethal
    // types excluded) and how many stand at once. A points duel respawns its
    // single opponent until GoalCount bouts are won.
    ESoraOpponent Opponent = ESoraOpponent::None;
    int32 Opponents = 0;
    int32 MaxAlive = 0;
    // Dojo forms (SoraDojoRules order) named by a lesson duel's gates.
    unsigned LessonMask = 0u;
    // Health percent at which each boss or duel phase begins, phase 0 first.
    TArray<int32> PhaseHealthPercent;
    // Collectibles in an explore beat's cache.
    TArray<int32> Rewards;
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
    // Beats[I]'s gates, contiguous for SoraBeatRules.
    TArray<SoraBeatRules::FBeat> Rules;
    TArray<FSoraDialogueCue> Dialogue;
    TArray<FSoraDialogueTrigger> Triggers;
    TArray<FSoraCollectible> Collectibles;
    TArray<FSoraPrompt> Prompts;
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
 * labels and mechanic flags; and campaign/chapter_0N.json, generated by
 * scripts/unreal/build_campaign_data.py, for beats, lines, triggers,
 * checkpoints, unlocks, collectibles and prompts. Financial rules are
 * deliberately absent.
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
    FString Error;
    TArray<FSoraWeapon> Weapons;
    TArray<FSoraWeapon> CampaignWeapons;
    TArray<FSoraClass> Classes;
    TArray<FSoraChapter> Chapters;
    TMap<FString, FSoraDialogueSpeaker> DialogueSpeakers;
    FSoraHero HeroData;
    TArray<FSoraMap> Maps;
    // Mechanic flags in bit order.
    TArray<FString> Mechanics;
    TArray<FSoraCollectibleCategory> CollectibleCategories;
private:
    bool LoadCampaign();
    bool Fail(const FString& Message);
    bool bReady = false;
};
