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
    TArray<FString> Targets;
    TArray<FString> StepKinds;
    // A duel's opponent or the boss; sparring beats use bokuto, shinai or targets.
    FName Opponent;
    bool bSparring = false;
    // A stealth zone's guards, by enemy type.
    TArray<FName> Guards;
    // A duel's scripted events, one per later phase.
    TArray<FString> PhaseEvents;
    // The beat's `fail` rows by event.
    TMap<FString, SoraBeatRules::EFail> FailEvents;
    // Collectibles in an explore beat's cache.
    TArray<int32> Rewards;
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
 * labels, mechanic flags and story flags; and campaign/chapter_0N.json,
 * generated by scripts/unreal/build_campaign_data.py, for beats and their
 * tasks, lines, triggers, checkpoints, unlocks, collectibles and prompts.
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
    // Mechanic flags and story flags in bit order.
    TArray<FString> Mechanics;
    TArray<FString> StoryFlags;
    TArray<FSoraCollectibleCategory> CollectibleCategories;
private:
    bool LoadCampaign();
    bool Fail(const FString& Message);
    bool bReady = false;
};
