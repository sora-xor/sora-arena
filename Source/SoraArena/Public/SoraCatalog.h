#pragma once
#include "CoreMinimal.h"

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
    FString Role;
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
struct FSoraDialogueCue
{
    FString SpeakerId;
    FString Japanese;
    FString English;
    float StartSeconds = 0.f;
    float DurationSeconds = 0.f;
};
struct FSoraProductionSite
{
    FString Name;
    FString NameEnglish;
    FString Restored;
    FString RestoredEnglish;
    FString Kind;
    int32 RequiredKills = 0;
    int32 RequiredSitesMask = 0;
};
struct FSoraChapter
{
    FString Title;
    FString Narrative;
    FString NarrativeEnglish;
    FString Objective;
    int32 Map = 0;
    int32 Kills = 6;
    TArray<FSoraDialogueCue> Dialogue;
    TArray<FSoraProductionSite> Sites;
};
struct FSoraMap
{
    FString Name;
    FLinearColor Accent = FLinearColor(.1f,.6f,.6f);
};

/** Offline authored content. Financial rules are deliberately absent. */
class SORAARENA_API FSoraCatalog
{
public:
    static FSoraCatalog& Get();
    bool Load();
    const FSoraWeapon& Weapon(int32 Id) const;
    const FSoraClass& Class(int32 Id) const;
    const FSoraChapter& Chapter(int32 Id) const;
    const FSoraDialogueSpeaker* DialogueSpeaker(const FString& Id) const;
    const FSoraHero& Hero() const { check(bReady); return HeroData; }
    const FSoraMap& Map(int32 Id) const;
    bool IsReady() const { return bReady; }
    FString Error;
    TArray<FSoraWeapon> Weapons;
    TArray<FSoraWeapon> CampaignWeapons;
    TArray<FSoraClass> Classes;
    TArray<FSoraChapter> Chapters;
    TMap<FString, FSoraDialogueSpeaker> DialogueSpeakers;
    FSoraHero HeroData;
    TArray<FSoraMap> Maps;
private:
    bool bReady = false;
};
