#include "SoraCatalog.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

FSoraCatalog& FSoraCatalog::Get() { static FSoraCatalog Catalog; return Catalog; }
bool FSoraCatalog::Load()
{
    if (bReady) return true;
    FString Text;
    const FString Path = FPaths::ProjectContentDir() / TEXT("Data/catalog.json");
    TSharedPtr<FJsonObject> Root;
    if (!FFileHelper::LoadFileToString(Text, *Path) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid())
    { Error = TEXT("Cannot load Content/Data/catalog.json"); UE_LOG(LogTemp, Error, TEXT("%s"), *Error); return false; }
    double SchemaVersion = 0;
    if (!Root->TryGetNumberField(TEXT("schema_version"), SchemaVersion) || SchemaVersion != 3)
    { Error = TEXT("Unsupported offline catalog schema"); return false; }
    Weapons.Reset(); CampaignWeapons.Reset(); Classes.Reset(); Chapters.Reset(); Maps.Reset(); DialogueSpeakers.Reset();
    const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
    if (!Root->TryGetArrayField(TEXT("dialogue_speakers"), Rows)) { Error = TEXT("Catalog lacks dialogue speakers"); return false; }
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return false;
        FString Id; FSoraDialogueSpeaker Speaker;
        if (!O->TryGetStringField(TEXT("id"), Id) || !O->TryGetStringField(TEXT("ja"), Speaker.Japanese) ||
            !O->TryGetStringField(TEXT("en"), Speaker.English) || Id.IsEmpty() || Speaker.Japanese.IsEmpty() ||
            Speaker.English.IsEmpty() || DialogueSpeakers.Contains(Id))
        { Error = TEXT("Invalid dialogue speaker"); return false; }
        DialogueSpeakers.Add(Id, MoveTemp(Speaker));
    }
    if (DialogueSpeakers.IsEmpty()) { Error = TEXT("Catalog lacks dialogue speakers"); return false; }
    const FSoraDialogueSpeaker* HeroSpeaker = DialogueSpeakers.Find(TEXT("samurai"));
    const TSharedPtr<FJsonObject>* HeroObject = nullptr;
    if (!HeroSpeaker || !Root->TryGetObjectField(TEXT("hero"), HeroObject) || !HeroObject || !HeroObject->IsValid() ||
        !(*HeroObject)->TryGetStringField(TEXT("name_ja"), HeroData.NameJapanese) ||
        !(*HeroObject)->TryGetStringField(TEXT("name_en"), HeroData.NameEnglish) ||
        !(*HeroObject)->TryGetNumberField(TEXT("katana_id"), HeroData.KatanaId) ||
        !(*HeroObject)->TryGetNumberField(TEXT("yumi_id"), HeroData.YumiId) ||
        !(*HeroObject)->TryGetNumberField(TEXT("quiver_arrows"), HeroData.QuiverArrows) ||
        HeroData.NameJapanese.IsEmpty() || HeroData.NameEnglish.IsEmpty() ||
        HeroData.KatanaId != 0 || HeroData.YumiId != 18 || HeroData.QuiverArrows != 12 ||
        HeroSpeaker->Japanese != HeroData.NameJapanese ||
        HeroSpeaker->English != HeroData.NameEnglish)
    { Error = TEXT("Invalid Nyaakoto hero identity or initial arms"); return false; }
    if (!Root->TryGetArrayField(TEXT("weapons"), Rows)) { Error = TEXT("Catalog lacks weapons"); return false; }
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return false;
        FSoraWeapon W;
        W.Id = O->GetIntegerField(TEXT("id")); W.ClassId = O->GetIntegerField(TEXT("class"));
        W.Name = O->GetStringField(TEXT("name")); W.Kind = O->GetStringField(TEXT("kind")); W.Tradeoff = O->GetStringField(TEXT("tradeoff"));
        W.Damage = O->GetNumberField(TEXT("damage")); W.Cooldown = O->GetNumberField(TEXT("cooldown"));
        W.Range = O->GetNumberField(TEXT("range")); W.Reload = O->GetNumberField(TEXT("reload"));
        W.Magazine = O->GetIntegerField(TEXT("magazine")); W.BlastRadius = O->GetNumberField(TEXT("blast_radius"));
        W.ProjectileSpeed = O->GetNumberField(TEXT("projectile_speed")); W.Special = O->GetBoolField(TEXT("special"));
        if (W.Id != Weapons.Num() || W.ClassId < 0 || W.ClassId >= 6 || W.Cooldown <= 0 || W.Magazine < 1 || W.Damage <= 0) { Error = TEXT("Invalid weapon catalog"); return false; }
        Weapons.Add(W);
    }
    // These three arms exist only in the offline campaign. Arena admission and
    // its compiled 18-weapon rules profile cannot select their IDs.
    if (!Root->TryGetArrayField(TEXT("campaign_weapons"), Rows) || Rows->Num() != 3)
    { Error = TEXT("Catalog needs three campaign-only historical arms"); return false; }
    static const TCHAR* HistoricalKinds[] = { TEXT("bow"), TEXT("melee"), TEXT("melee") };
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return false;
        FSoraWeapon W;
        if (!O->TryGetStringField(TEXT("name"), W.Name) || !O->TryGetStringField(TEXT("name_en"), W.NameEnglish) ||
            !O->TryGetStringField(TEXT("kind"), W.Kind) || !O->TryGetStringField(TEXT("tradeoff"), W.Tradeoff)) return false;
        W.Id = O->GetIntegerField(TEXT("id")); W.ClassId = O->GetIntegerField(TEXT("class"));
        W.Damage = O->GetNumberField(TEXT("damage")); W.Cooldown = O->GetNumberField(TEXT("cooldown"));
        W.Range = O->GetNumberField(TEXT("range")); W.Reload = O->GetNumberField(TEXT("reload"));
        W.Magazine = O->GetIntegerField(TEXT("magazine")); W.BlastRadius = O->GetNumberField(TEXT("blast_radius"));
        W.ProjectileSpeed = O->GetNumberField(TEXT("projectile_speed")); W.Special = O->GetBoolField(TEXT("special"));
        const int32 Index = CampaignWeapons.Num();
        if (W.Id != 18 + Index || W.ClassId != 0 || W.Kind != HistoricalKinds[Index] ||
            W.Name.IsEmpty() || W.NameEnglish.IsEmpty() || W.Tradeoff.IsEmpty() || W.Special ||
            W.Damage <= 0 || W.Cooldown <= 0 || W.Range <= 0 || W.Reload <= 0 || W.Magazine < 1 ||
            W.BlastRadius != 0 || (Index == 0 && W.ProjectileSpeed <= 0) ||
            (Index > 0 && W.ProjectileSpeed != 0))
        { Error = TEXT("Invalid campaign-only arm"); return false; }
        CampaignWeapons.Add(MoveTemp(W));
    }
    if (!Root->TryGetArrayField(TEXT("classes"), Rows)) return false;
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return false;
        FSoraClass C; C.Id = O->GetIntegerField(TEXT("id")); C.Name = O->GetStringField(TEXT("name")); C.Role = O->GetStringField(TEXT("role"));
        C.Health = O->GetNumberField(TEXT("health")); C.Speed = O->GetNumberField(TEXT("speed"));
        for (const auto& V : O->GetArrayField(TEXT("weapons"))) { const int32 Id = V->AsNumber(); if (!Weapons.IsValidIndex(Id) || Weapons[Id].ClassId != C.Id) return false; C.Weapons.Add(Id); }
        if (C.Id != Classes.Num() || C.Weapons.Num() != 3 || C.Health <= 0 || C.Speed <= 0) return false;
        Classes.Add(C);
    }
    if (!Root->TryGetArrayField(TEXT("chapters"), Rows)) return false;
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return false;
        FSoraChapter C; C.Title = O->GetStringField(TEXT("title")); C.Narrative = O->GetStringField(TEXT("narrative")); C.Objective = O->GetStringField(TEXT("objective"));
        C.NarrativeEnglish = O->GetStringField(TEXT("narrative_en"));
        C.Map = O->GetIntegerField(TEXT("map")); C.Kills = O->GetIntegerField(TEXT("kills"));
        const TArray<TSharedPtr<FJsonValue>>* SiteRows = nullptr;
        if (!O->TryGetArrayField(TEXT("sites"), SiteRows) || SiteRows->Num() != 3)
        { Error = TEXT("Each chapter needs three authored production sites"); return false; }
        static const TSet<FString> SiteKinds = {
            TEXT("training"), TEXT("debt_seal"), TEXT("irrigation"), TEXT("workshop"),
            TEXT("foundry"), TEXT("ledger"), TEXT("power"), TEXT("supplies")
        };
        for (const auto& SiteRow : *SiteRows)
        {
            const auto SiteObject = SiteRow->AsObject();
            FSoraProductionSite Site; const int32 SiteIndex = C.Sites.Num();
            const TArray<TSharedPtr<FJsonValue>>* Prerequisites = nullptr;
            if (!SiteObject.IsValid() ||
                !SiteObject->TryGetStringField(TEXT("name"), Site.Name) ||
                !SiteObject->TryGetStringField(TEXT("name_en"), Site.NameEnglish) ||
                !SiteObject->TryGetStringField(TEXT("restored"), Site.Restored) ||
                !SiteObject->TryGetStringField(TEXT("restored_en"), Site.RestoredEnglish) ||
                !SiteObject->TryGetStringField(TEXT("kind"), Site.Kind) ||
                !SiteObject->TryGetNumberField(TEXT("requires_kills"), Site.RequiredKills) ||
                !SiteObject->TryGetArrayField(TEXT("requires_sites"), Prerequisites) ||
                Site.Name.IsEmpty() || Site.NameEnglish.IsEmpty() || Site.Restored.IsEmpty() ||
                Site.RestoredEnglish.IsEmpty() || !SiteKinds.Contains(Site.Kind) ||
                Site.RequiredKills < 0 || Site.RequiredKills > C.Kills)
            { Error = TEXT("Invalid chapter production site"); return false; }
            for (const auto& Prerequisite : *Prerequisites)
            {
                double Id = -1;
                if (!Prerequisite.IsValid() || !Prerequisite->TryGetNumber(Id) ||
                    !FMath::IsFinite(Id) || Id < 0 || Id >= SiteIndex ||
                    Id != static_cast<double>(FMath::FloorToInt(Id)) ||
                    (Site.RequiredSitesMask & (1 << static_cast<int32>(Id))) != 0)
                { Error = TEXT("Invalid production site prerequisite"); return false; }
                Site.RequiredSitesMask |= 1 << static_cast<int32>(Id);
            }
            C.Sites.Add(MoveTemp(Site));
        }
        const TArray<TSharedPtr<FJsonValue>>* CueRows = nullptr;
        if (!O->TryGetArrayField(TEXT("dialogue"), CueRows)) { Error = TEXT("Chapter lacks dialogue"); return false; }
        float PreviousEnd = 0.f;
        for (const auto& CueRow : *CueRows)
        {
            const auto CueObject = CueRow->AsObject(); if (!CueObject.IsValid()) return false;
            FSoraDialogueCue Cue; double Start = 0, Duration = 0;
            if (!CueObject->TryGetStringField(TEXT("speaker"), Cue.SpeakerId) ||
                !CueObject->TryGetStringField(TEXT("ja"), Cue.Japanese) ||
                !CueObject->TryGetStringField(TEXT("en"), Cue.English) ||
                !CueObject->TryGetNumberField(TEXT("start_s"), Start) ||
                !CueObject->TryGetNumberField(TEXT("duration_s"), Duration) ||
                !DialogueSpeakers.Contains(Cue.SpeakerId) || Cue.Japanese.IsEmpty() || Cue.English.IsEmpty() ||
                !FMath::IsFinite(Start) || !FMath::IsFinite(Duration) || Start < PreviousEnd ||
                Duration < 1.5 || Duration > 8.0 || Start + Duration > 45.0)
            { Error = TEXT("Invalid or overlapping chapter dialogue"); return false; }
            Cue.StartSeconds = static_cast<float>(Start);
            Cue.DurationSeconds = static_cast<float>(Duration);
            PreviousEnd = Cue.StartSeconds + Cue.DurationSeconds;
            C.Dialogue.Add(MoveTemp(Cue));
        }
        if (C.Dialogue.Num() < 2) { Error = TEXT("Each chapter needs at least two dialogue cues"); return false; }
        Chapters.Add(MoveTemp(C));
    }
    if (!Root->TryGetArrayField(TEXT("maps"), Rows)) return false;
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return false;
        FSoraMap M; M.Name = O->GetStringField(TEXT("name")); const auto& A = O->GetArrayField(TEXT("accent"));
        if (A.Num() != 3) return false;
        M.Accent = FLinearColor(A[0]->AsNumber(), A[1]->AsNumber(), A[2]->AsNumber()); Maps.Add(M);
    }
    bReady = Weapons.Num() == 18 && CampaignWeapons.Num() == 3 && Classes.Num() == 6 && Chapters.Num() == 8 && Maps.Num() == 4;
    for (const auto& C : Chapters) bReady &= Maps.IsValidIndex(C.Map) && C.Kills > 0;
    if (!bReady) Error = TEXT("Catalog must contain 6 classes, 18 weapons, 8 chapters, and 4 maps");
    return bReady;
}
const FSoraWeapon& FSoraCatalog::Weapon(int32 Id) const
{
    check(bReady);
    if (Id >= 18 && Id < 18 + CampaignWeapons.Num()) return CampaignWeapons[Id - 18];
    check(Weapons.IsValidIndex(Id));
    return Weapons[Id];
}
const FSoraClass& FSoraCatalog::Class(int32 Id) const { check(bReady); return Classes[FMath::Clamp(Id,0,Classes.Num()-1)]; }
const FSoraChapter& FSoraCatalog::Chapter(int32 Id) const { check(bReady); return Chapters[FMath::Clamp(Id,0,Chapters.Num()-1)]; }
const FSoraDialogueSpeaker* FSoraCatalog::DialogueSpeaker(const FString& Id) const { return DialogueSpeakers.Find(Id); }
const FSoraMap& FSoraCatalog::Map(int32 Id) const { check(bReady); return Maps[FMath::Clamp(Id,0,Maps.Num()-1)]; }
