#include "SoraCatalog.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace
{
using FJsonRows = TArray<TSharedPtr<FJsonValue>>;

bool ReadJson(const FString& Relative, TSharedPtr<FJsonObject>& Root)
{
    FString Text;
    return FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Data") / Relative)) &&
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) && Root.IsValid();
}
bool Str(const FJsonObject& Object, const TCHAR* Key, FString& Out)
{
    return Object.TryGetStringField(Key, Out) && !Out.IsEmpty();
}
bool Whole(double Value, int32& Out)
{
    if (!FMath::IsFinite(Value) || Value != FMath::FloorToDouble(Value) || Value < MIN_int32 || Value > MAX_int32)
        return false;
    Out = static_cast<int32>(Value);
    return true;
}
bool Int(const FJsonObject& Object, const TCHAR* Key, int32& Out)
{
    double Value = 0;
    return Object.TryGetNumberField(Key, Value) && Whole(Value, Out);
}
bool Num(const FJsonObject& Object, const TCHAR* Key, double& Out)
{
    return Object.TryGetNumberField(Key, Out) && FMath::IsFinite(Out);
}
const FJsonRows* Rows(const FJsonObject& Object, const TCHAR* Key)
{
    const FJsonRows* Result = nullptr;
    return Object.TryGetArrayField(Key, Result) ? Result : nullptr;
}
TSharedPtr<FJsonObject> Child(const FJsonObject& Object, const TCHAR* Key)
{
    const TSharedPtr<FJsonObject>* Result = nullptr;
    return Object.TryGetObjectField(Key, Result) && Result ? *Result : nullptr;
}
bool IsNull(const FJsonObject& Object, const TCHAR* Key)
{
    const TSharedPtr<FJsonValue> Value = Object.TryGetField(Key);
    return Value.IsValid() && Value->IsNull();
}
bool Strings(const FJsonRows* Values, TArray<FString>& Out)
{
    if (!Values) return false;
    for (const auto& Value : *Values)
    {
        FString Text;
        if (!Value.IsValid() || !Value->TryGetString(Text) || Text.IsEmpty()) return false;
        Out.Add(MoveTemp(Text));
    }
    return true;
}
bool WeaponMask(const FJsonRows* Values, unsigned& Out)
{
    if (!Values) return false;
    for (const auto& Value : *Values)
    {
        double Number = 0; int32 Id = 0;
        if (!Value.IsValid() || !Value->TryGetNumber(Number) || !Whole(Number, Id) ||
            Id < 0 || Id >= SoraBeatRules::WeaponCount || (Out & (1u << Id)) != 0u)
            return false;
        Out |= 1u << Id;
    }
    return true;
}
// Lethal opponents over every wave; nonlethal types (bound conscripts) are freed, never defeated.
bool WaveOpponents(const FJsonObject& Params, int32& Count, int32& MaxAlive)
{
    Count = 0; MaxAlive = 6;
    TArray<FString> Nonlethal = {TEXT("bound_conscript")};
    if (const FJsonRows* Types = Rows(Params, TEXT("nonlethal_types")))
    {
        Nonlethal.Reset();
        if (!Strings(Types, Nonlethal)) return false;
    }
    if (Params.HasField(TEXT("max_alive")) && (!Int(Params, TEXT("max_alive"), MaxAlive) || MaxAlive < 1)) return false;
    const FJsonRows* Waves = Rows(Params, TEXT("waves"));
    if (!Waves) return !Params.HasField(TEXT("waves"));
    for (const auto& Wave : *Waves)
    {
        const TSharedPtr<FJsonObject> WaveObject = Wave.IsValid() ? Wave->AsObject() : nullptr;
        const FJsonRows* Enemies = WaveObject ? Rows(*WaveObject, TEXT("enemies")) : nullptr;
        if (!Enemies) return false;
        for (const auto& Enemy : *Enemies)
        {
            const TSharedPtr<FJsonObject> EnemyObject = Enemy.IsValid() ? Enemy->AsObject() : nullptr;
            FString Type; int32 Number = 0;
            if (!EnemyObject || !Str(*EnemyObject, TEXT("type"), Type) || !Int(*EnemyObject, TEXT("count"), Number) || Number < 1)
                return false;
            if (!Nonlethal.Contains(Type)) Count += Number;
        }
    }
    return true;
}
}

int32 FSoraChapter::BeatIndex(const FString& BeatId) const
{
    return Beats.IndexOfByPredicate([&](const FSoraBeat& Beat) { return Beat.Id == BeatId; });
}
int32 FSoraChapter::LineIndex(const FString& LineId) const
{
    return Dialogue.IndexOfByPredicate([&](const FSoraDialogueCue& Line) { return Line.Id == LineId; });
}

FSoraCatalog& FSoraCatalog::Get() { static FSoraCatalog Catalog; return Catalog; }
bool FSoraCatalog::Fail(const FString& Message)
{
    Error = Message;
    UE_LOG(LogTemp, Error, TEXT("SORA catalog: %s"), *Error);
    return false;
}
bool FSoraCatalog::Load()
{
    if (bReady) return true;
    TSharedPtr<FJsonObject> Root;
    if (!ReadJson(TEXT("catalog.json"), Root)) return Fail(TEXT("Cannot load Content/Data/catalog.json"));
    int32 SchemaVersion = 0;
    if (!Int(*Root, TEXT("schema_version"), SchemaVersion) || SchemaVersion != 4 || Root->HasField(TEXT("chapters")))
        return Fail(TEXT("Unsupported offline catalog schema"));
    Weapons.Reset(); CampaignWeapons.Reset(); Classes.Reset(); Chapters.Reset(); Maps.Reset(); DialogueSpeakers.Reset();
    Mechanics.Reset(); CollectibleCategories.Reset();
    const FJsonRows* Rows = nullptr;
    if (!Root->TryGetArrayField(TEXT("dialogue_speakers"), Rows)) return Fail(TEXT("Catalog lacks dialogue speakers"));
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return Fail(TEXT("Invalid dialogue speaker"));
        FString Id; FSoraDialogueSpeaker Speaker;
        if (!O->TryGetStringField(TEXT("id"), Id) || !O->TryGetStringField(TEXT("ja"), Speaker.Japanese) ||
            !O->TryGetStringField(TEXT("en"), Speaker.English) || Id.IsEmpty() || Speaker.Japanese.IsEmpty() ||
            Speaker.English.IsEmpty() || DialogueSpeakers.Contains(Id))
            return Fail(TEXT("Invalid dialogue speaker"));
        DialogueSpeakers.Add(Id, MoveTemp(Speaker));
    }
    if (DialogueSpeakers.IsEmpty()) return Fail(TEXT("Catalog lacks dialogue speakers"));
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
        return Fail(TEXT("Invalid Nyaakoto hero identity or initial arms"));
    if (!Root->TryGetArrayField(TEXT("weapons"), Rows)) return Fail(TEXT("Catalog lacks weapons"));
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return Fail(TEXT("Invalid weapon catalog"));
        FSoraWeapon W;
        W.Id = O->GetIntegerField(TEXT("id")); W.ClassId = O->GetIntegerField(TEXT("class"));
        W.Name = O->GetStringField(TEXT("name")); W.Kind = O->GetStringField(TEXT("kind")); W.Tradeoff = O->GetStringField(TEXT("tradeoff"));
        W.Damage = O->GetNumberField(TEXT("damage")); W.Cooldown = O->GetNumberField(TEXT("cooldown"));
        W.Range = O->GetNumberField(TEXT("range")); W.Reload = O->GetNumberField(TEXT("reload"));
        W.Magazine = O->GetIntegerField(TEXT("magazine")); W.BlastRadius = O->GetNumberField(TEXT("blast_radius"));
        W.ProjectileSpeed = O->GetNumberField(TEXT("projectile_speed")); W.Special = O->GetBoolField(TEXT("special"));
        if (W.Id != Weapons.Num() || W.ClassId < 0 || W.ClassId >= 6 || W.Cooldown <= 0 || W.Magazine < 1 || W.Damage <= 0) return Fail(TEXT("Invalid weapon catalog"));
        if (!O->TryGetStringField(TEXT("name_en"), W.NameEnglish) || W.NameEnglish.IsEmpty()) return Fail(TEXT("Weapon lacks its English name"));
        Weapons.Add(W);
    }
    // These three arms exist only in the offline campaign. Arena admission and
    // its compiled 18-weapon rules profile cannot select their IDs.
    if (!Root->TryGetArrayField(TEXT("campaign_weapons"), Rows) || Rows->Num() != 3)
        return Fail(TEXT("Catalog needs three campaign-only historical arms"));
    static const TCHAR* HistoricalKinds[] = { TEXT("bow"), TEXT("melee"), TEXT("melee") };
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return Fail(TEXT("Invalid campaign-only arm"));
        FSoraWeapon W;
        if (!O->TryGetStringField(TEXT("name"), W.Name) || !O->TryGetStringField(TEXT("name_en"), W.NameEnglish) ||
            !O->TryGetStringField(TEXT("kind"), W.Kind) || !O->TryGetStringField(TEXT("tradeoff"), W.Tradeoff))
            return Fail(TEXT("Invalid campaign-only arm"));
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
            return Fail(TEXT("Invalid campaign-only arm"));
        CampaignWeapons.Add(MoveTemp(W));
    }
    if (!Root->TryGetArrayField(TEXT("classes"), Rows)) return Fail(TEXT("Catalog lacks classes"));
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return Fail(TEXT("Invalid class"));
        FSoraClass C; C.Id = O->GetIntegerField(TEXT("id")); C.Name = O->GetStringField(TEXT("name")); C.Role = O->GetStringField(TEXT("role"));
        C.Health = O->GetNumberField(TEXT("health")); C.Speed = O->GetNumberField(TEXT("speed"));
        if (!O->TryGetStringField(TEXT("name_en"), C.NameEnglish) || !O->TryGetStringField(TEXT("role_en"), C.RoleEnglish) ||
            C.NameEnglish.IsEmpty() || C.RoleEnglish.IsEmpty())
            return Fail(TEXT("Class lacks its English name or role"));
        for (const auto& V : O->GetArrayField(TEXT("weapons")))
        {
            const int32 Id = V->AsNumber();
            if (!Weapons.IsValidIndex(Id) || Weapons[Id].ClassId != C.Id) return Fail(TEXT("Invalid class weapon"));
            C.Weapons.Add(Id);
        }
        if (C.Id != Classes.Num() || C.Weapons.Num() != 3 || C.Health <= 0 || C.Speed <= 0) return Fail(TEXT("Invalid class"));
        Classes.Add(C);
    }
    if (!Root->TryGetArrayField(TEXT("maps"), Rows)) return Fail(TEXT("Catalog lacks maps"));
    for (const auto& Row : *Rows)
    {
        const auto O = Row->AsObject(); if (!O.IsValid()) return Fail(TEXT("Invalid map"));
        FSoraMap M; M.Name = O->GetStringField(TEXT("name")); const auto& A = O->GetArrayField(TEXT("accent"));
        if (A.Num() != 3) return Fail(TEXT("Map accent needs three channels"));
        if (!O->TryGetStringField(TEXT("name_en"), M.NameEnglish) || M.Name.IsEmpty() || M.NameEnglish.IsEmpty())
            return Fail(TEXT("Map lacks its English name"));
        M.Accent = FLinearColor(A[0]->AsNumber(), A[1]->AsNumber(), A[2]->AsNumber()); Maps.Add(M);
    }
    if (Weapons.Num() != 18 || CampaignWeapons.Num() != 3 || Classes.Num() != 6 || Maps.Num() != 4)
        return Fail(TEXT("Catalog must contain 6 classes, 18 weapons, 3 campaign arms and 4 maps"));
    if (!LoadCampaign()) return false;
    bReady = true;
    return true;
}

bool FSoraCatalog::LoadCampaign()
{
    TSharedPtr<FJsonObject> Campaign;
    int32 SchemaVersion = 0;
    if (!ReadJson(TEXT("campaign/campaign.json"), Campaign) || !Int(*Campaign, TEXT("schema_version"), SchemaVersion) || SchemaVersion != 4)
        return Fail(TEXT("Cannot load Content/Data/campaign/campaign.json (schema 4)"));
    if (!Strings(Rows(*Campaign, TEXT("mechanics")), Mechanics) || Mechanics.Num() != SoraBeatRules::MechanicCount)
        return Fail(TEXT("Campaign needs its nineteen mechanic flags"));
    for (int32 Index = 0; Index < Mechanics.Num(); ++Index)
        if (Mechanics.Find(Mechanics[Index]) != Index) return Fail(TEXT("Duplicate campaign mechanic flag"));
    const FJsonRows* CategoryRows = Rows(*Campaign, TEXT("collectible_categories"));
    if (!CategoryRows) return Fail(TEXT("Campaign lacks collectible categories"));
    for (const auto& Row : *CategoryRows)
    {
        const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
        FSoraCollectibleCategory Category;
        if (!O || !Str(*O, TEXT("id"), Category.Id) || !Str(*O, TEXT("ja"), Category.Japanese) ||
            !Str(*O, TEXT("en"), Category.English) || !Int(*O, TEXT("count"), Category.Count) || Category.Count < 1)
            return Fail(TEXT("Invalid collectible category"));
        CollectibleCategories.Add(MoveTemp(Category));
    }
    const FJsonRows* ChapterRows = Rows(*Campaign, TEXT("chapters"));
    if (!ChapterRows || ChapterRows->Num() != ChapterCount) return Fail(TEXT("Campaign needs eight chapters"));
    static const TMap<FString, ESoraBeatType> BeatTypes = {
        {TEXT("cinematic"), ESoraBeatType::Cinematic}, {TEXT("dialogue"), ESoraBeatType::Dialogue},
        {TEXT("combat_wave"), ESoraBeatType::CombatWave}, {TEXT("duel"), ESoraBeatType::Duel},
        {TEXT("stealth_zone"), ESoraBeatType::StealthZone}, {TEXT("production_task"), ESoraBeatType::ProductionTask},
        {TEXT("horseback_ride"), ESoraBeatType::HorsebackRide}, {TEXT("boss"), ESoraBeatType::Boss},
        {TEXT("explore_optional"), ESoraBeatType::ExploreOptional}};
    static const TSet<FString> SiteKinds = {
        TEXT("training"), TEXT("debt_seal"), TEXT("irrigation"), TEXT("workshop"),
        TEXT("foundry"), TEXT("ledger"), TEXT("power"), TEXT("supplies")};
    // Lesson gates that name one of the four dojo forms, in SoraDojoRules order.
    static const TMap<FString, int32> LessonGates = {
        {TEXT("stance_hold"), 0}, {TEXT("front_guard_survive"), 1}, {TEXT("awase"), 2}, {TEXT("recovery_complete"), 3}};
    for (int32 ChapterIndex = 0; ChapterIndex < ChapterCount; ++ChapterIndex)
    {
        const auto Entry = (*ChapterRows)[ChapterIndex].IsValid() ? (*ChapterRows)[ChapterIndex]->AsObject() : nullptr;
        FSoraChapter C; FString File;
        if (!Entry || !Str(*Entry, TEXT("id"), C.Id) || !Str(*Entry, TEXT("file"), File) ||
            !Str(*Entry, TEXT("narrative_ja"), C.Narrative) || !Str(*Entry, TEXT("narrative_en"), C.NarrativeEnglish) ||
            !Str(*Entry, TEXT("objective_ja"), C.Objective) || !Str(*Entry, TEXT("objective_en"), C.ObjectiveEnglish))
            return Fail(FString::Printf(TEXT("Chapter %d lacks its bilingual narrative or objective"), ChapterIndex + 1));
        const FJsonRows* SiteLabels = Rows(*Entry, TEXT("sites"));
        if (!SiteLabels || SiteLabels->Num() != SoraBeatRules::SiteCount)
            return Fail(FString::Printf(TEXT("%s needs three production sites"), *C.Id));
        for (const auto& Label : *SiteLabels)
        {
            const auto O = Label.IsValid() ? Label->AsObject() : nullptr;
            FSoraProductionSite Site;
            if (!O || !Str(*O, TEXT("kind"), Site.Kind) || !Str(*O, TEXT("name_ja"), Site.Name) ||
                !Str(*O, TEXT("name_en"), Site.NameEnglish) || !Str(*O, TEXT("restored_ja"), Site.Restored) ||
                !Str(*O, TEXT("restored_en"), Site.RestoredEnglish) || !SiteKinds.Contains(Site.Kind))
                return Fail(FString::Printf(TEXT("%s has an invalid production site label"), *C.Id));
            C.Sites.Add(MoveTemp(Site));
        }
        TSharedPtr<FJsonObject> Data;
        int32 FileSchema = 0, FileIndex = -1;
        FString FileId;
        if (!ReadJson(File, Data) || !Int(*Data, TEXT("schema_version"), FileSchema) || FileSchema != 4 ||
            !Str(*Data, TEXT("id"), FileId) || FileId != C.Id || !Int(*Data, TEXT("index"), FileIndex) || FileIndex != ChapterIndex ||
            !Str(*Data, TEXT("title_ja"), C.Title) || !Str(*Data, TEXT("title_en"), C.TitleEnglish) ||
            !Int(*Data, TEXT("map"), C.Map) || !Maps.IsValidIndex(C.Map) || !Int(*Data, TEXT("target_s"), C.TargetSeconds))
            return Fail(FString::Printf(TEXT("Cannot load %s for %s"), *File, *C.Id));
        const FString Where = C.Id;
        auto Bad = [&](const FString& What) { return Fail(FString::Printf(TEXT("%s: %s"), *Where, *What)); };

        // Beat ids first: lines, collectibles and prompts refer to beats by id.
        const FJsonRows* BeatRows = Rows(*Data, TEXT("beats"));
        if (!BeatRows || BeatRows->IsEmpty() || BeatRows->Num() > SoraBeatRules::MaxBeats) return Bad(TEXT("needs 1-32 beats"));
        TMap<FString, int32> BeatIds;
        for (const auto& Row : *BeatRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            FString Id;
            if (!O || !Str(*O, TEXT("id"), Id) || BeatIds.Contains(Id)) return Bad(TEXT("invalid or duplicate beat id"));
            BeatIds.Add(Id, BeatIds.Num());
        }
        const auto BeatRef = [&](const FJsonObject& O, int32& Out)
        {
            FString Id;
            if (IsNull(O, TEXT("beat"))) { Out = INDEX_NONE; return true; }
            if (!Str(O, TEXT("beat"), Id) || !BeatIds.Contains(Id)) return false;
            Out = BeatIds[Id];
            return true;
        };
        const FJsonRows* LineRows = Rows(*Data, TEXT("lines"));
        if (!LineRows || LineRows->IsEmpty()) return Bad(TEXT("has no lines"));
        TMap<FString, int32> LineIds;
        for (const auto& Row : *LineRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            FSoraDialogueCue Line; double Duration = 0;
            if (!O || !Str(*O, TEXT("id"), Line.Id) || LineIds.Contains(Line.Id) || !BeatRef(*O, Line.Beat) ||
                !Str(*O, TEXT("speaker"), Line.SpeakerId) || !DialogueSpeakers.Contains(Line.SpeakerId) ||
                !Str(*O, TEXT("ja"), Line.Japanese) || !Str(*O, TEXT("en"), Line.English) ||
                !Num(*O, TEXT("duration_s"), Duration) || Duration < 1.0 || Duration > 20.0 ||
                !O->TryGetBoolField(TEXT("repeatable"), Line.bRepeatable))
                return Bad(FString::Printf(TEXT("invalid line %s"), *Line.Id));
            Line.DurationSeconds = static_cast<float>(Duration);
            LineIds.Add(Line.Id, C.Dialogue.Num());
            C.Dialogue.Add(MoveTemp(Line));
        }
        const auto LineRefs = [&](const FJsonRows* Values, TArray<int32>& Out)
        {
            TArray<FString> Ids;
            if (!Strings(Values, Ids) || Ids.IsEmpty()) return false;
            for (const FString& Id : Ids)
            {
                if (!LineIds.Contains(Id)) return false;
                Out.Add(LineIds[Id]);
            }
            return true;
        };
        const FJsonRows* CollectibleRows = Rows(*Data, TEXT("collectibles"));
        if (!CollectibleRows || CollectibleRows->Num() != CollectiblesPerChapter) return Bad(TEXT("needs six collectibles"));
        unsigned CollectibleBits = 0u;
        for (const auto& Row : *CollectibleRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            const TSharedPtr<FJsonObject> Codex = O ? Child(*O, TEXT("codex")) : nullptr;
            FSoraCollectible Item; TArray<FString> Beats;
            if (!O || !Codex || !Str(*O, TEXT("id"), Item.Id) || !Str(*O, TEXT("category"), Item.Category) ||
                !CollectibleCategories.ContainsByPredicate([&](const FSoraCollectibleCategory& Category) { return Category.Id == Item.Category; }) ||
                !Int(*O, TEXT("mask_bit"), Item.MaskBit) || Item.MaskBit < 0 || Item.MaskBit >= CollectiblesPerChapter ||
                (CollectibleBits & (1u << Item.MaskBit)) != 0u || !Strings(Rows(*O, TEXT("beats")), Beats) ||
                !Str(*O, TEXT("place"), Item.Place) || !Str(*Codex, TEXT("ja"), Item.Codex) || !Str(*Codex, TEXT("en"), Item.CodexEnglish))
                return Bad(FString::Printf(TEXT("invalid collectible %s"), *Item.Id));
            for (const FString& Beat : Beats)
            {
                if (!BeatIds.Contains(Beat)) return Bad(FString::Printf(TEXT("collectible %s names an unknown beat"), *Item.Id));
                Item.Beats.Add(BeatIds[Beat]);
            }
            CollectibleBits |= 1u << Item.MaskBit;
            C.Collectibles.Add(MoveTemp(Item));
        }

        // Phase checkpoints per beat; phase 0 rows must match the beats' own flag.
        TArray<int32> PhaseCheckpoints; PhaseCheckpoints.Init(0, BeatIds.Num());
        TArray<bool> StartCheckpoints; StartCheckpoints.Init(false, BeatIds.Num());
        const FJsonRows* CheckpointRows = Rows(*Data, TEXT("checkpoints"));
        if (!CheckpointRows) return Bad(TEXT("lacks checkpoints"));
        for (const auto& Row : *CheckpointRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            int32 Beat = INDEX_NONE, Phase = -1;
            if (!O || !BeatRef(*O, Beat) || Beat == INDEX_NONE || !Int(*O, TEXT("phase"), Phase) || Phase < 0)
                return Bad(TEXT("invalid checkpoint row"));
            if (Phase == 0)
            {
                if (StartCheckpoints[Beat]) return Bad(TEXT("duplicate checkpoint"));
                StartCheckpoints[Beat] = true;
            }
            else if (Phase != PhaseCheckpoints[Beat] + 1) return Bad(TEXT("phase checkpoints out of order"));
            else PhaseCheckpoints[Beat] = Phase;
        }

        for (int32 BeatIndex = 0; BeatIndex < BeatRows->Num(); ++BeatIndex)
        {
            const auto O = (*BeatRows)[BeatIndex]->AsObject();
            FSoraBeat Beat; FString TypeName;
            SoraBeatRules::FBeat Rule{0u, -1, 0u, 0u, 0u, false, false, 0};
            const TSharedPtr<FJsonObject> Unlocks = Child(*O, TEXT("unlocks"));
            const TSharedPtr<FJsonObject> Params = Child(*O, TEXT("params"));
            TArray<FString> Requires, MechanicNames;
            if (!Str(*O, TEXT("id"), Beat.Id) || !Str(*O, TEXT("type"), TypeName) || !BeatTypes.Contains(TypeName) || !Str(*O, TEXT("place"), Beat.Place) ||
                !Str(*O, TEXT("title_ja"), Beat.Title) || !Str(*O, TEXT("title_en"), Beat.TitleEnglish) ||
                !Int(*O, TEXT("target_s"), Beat.TargetSeconds) || Beat.TargetSeconds <= 0 ||
                !O->TryGetBoolField(TEXT("checkpoint"), Rule.Checkpoint) || !O->TryGetBoolField(TEXT("optional"), Rule.Optional) ||
                !Strings(Rows(*O, TEXT("requires")), Requires) || !Unlocks || !Params ||
                !WeaponMask(Rows(*Unlocks, TEXT("weapons")), Rule.WeaponsMask) ||
                !WeaponMask(Rows(*Unlocks, TEXT("grants")), Rule.GrantsMask) ||
                !Strings(Rows(*Unlocks, TEXT("mechanics")), MechanicNames))
                return Bad(FString::Printf(TEXT("beat %s lacks a required field"), *Beat.Id));
            Beat.Type = BeatTypes[TypeName];
            for (const FString& Prior : Requires)
            {
                if (!BeatIds.Contains(Prior) || BeatIds[Prior] >= BeatIndex) return Bad(FString::Printf(TEXT("beat %s requires a later beat"), *Beat.Id));
                Rule.RequiresMask |= SoraBeatRules::BeatBit(BeatIds[Prior]);
            }
            for (const FString& Name : MechanicNames)
            {
                const int32 Bit = Mechanics.Find(Name);
                if (Bit == INDEX_NONE) return Bad(FString::Printf(TEXT("beat %s unlocks unknown mechanic %s"), *Beat.Id, *Name));
                Rule.MechanicsMask |= 1u << Bit;
            }
            if (!IsNull(*O, TEXT("site")) && (!Int(*O, TEXT("site"), Rule.Site) || Rule.Site < 0 || Rule.Site >= SoraBeatRules::SiteCount))
                return Bad(FString::Printf(TEXT("beat %s has an invalid site"), *Beat.Id));
            if (StartCheckpoints[BeatIndex] != Rule.Checkpoint) return Bad(FString::Printf(TEXT("beat %s disagrees with its checkpoint rows"), *Beat.Id));
            Rule.PhaseCheckpoints = PhaseCheckpoints[BeatIndex];

            const FJsonObject& P = *Params;
            const TSharedPtr<FJsonObject> Complete = Child(P, TEXT("complete"));
            FString CompleteKind;
            if (Complete) Str(*Complete, TEXT("kind"), CompleteKind);
            bool bValid = true;
            switch (Beat.Type)
            {
            case ESoraBeatType::Cinematic:
            {
                double Duration = 0;
                bValid = Num(P, TEXT("duration_s"), Duration) && Duration > 0 && P.TryGetBoolField(TEXT("skippable"), Beat.bSkippable);
                Beat.Goal = ESoraBeatGoal::Cinematic; Beat.GoalSeconds = static_cast<float>(Duration);
                break;
            }
            case ESoraBeatType::Dialogue:
            {
                FString Trigger;
                bValid = LineRefs(Rows(P, TEXT("lines")), Beat.Lines) && Str(P, TEXT("trigger"), Trigger) &&
                    (Trigger == TEXT("beat_start") || Trigger.StartsWith(TEXT("volume_enter:")) || Trigger.StartsWith(TEXT("interact:"))) &&
                    (CompleteKind.IsEmpty() || CompleteKind == TEXT("volume_enter") || CompleteKind == TEXT("event"));
                Beat.Goal = ESoraBeatGoal::Lines;
                Beat.bLinesAtAnchor = Trigger != TEXT("beat_start");
                Beat.bLinesOnInteract = Trigger.StartsWith(TEXT("interact:"));
                Beat.bReachAfterLines = !CompleteKind.IsEmpty();
                if (Beat.bLinesAtAnchor) Beat.AnchorEvent = Trigger;
                break;
            }
            case ESoraBeatType::CombatWave:
            {
                FString Target = TEXT("enemy");
                P.TryGetStringField(TEXT("target_kind"), Target);
                bValid = WaveOpponents(P, Beat.Opponents, Beat.MaxAlive) && Beat.Opponents > 0 &&
                    (Target == TEXT("enemy") || Target == TEXT("mato") || Target == TEXT("pupil"));
                // Training targets stand in as sparring pupils until the AI lane's target actors land.
                Beat.Opponent = Target == TEXT("enemy") ? ESoraOpponent::Invader : ESoraOpponent::Pupil;
                if (CompleteKind == TEXT("all_waves_cleared")) { Beat.Goal = ESoraBeatGoal::Defeat; Beat.GoalCount = Beat.Opponents; }
                else if (CompleteKind == TEXT("objectives"))
                {
                    const FJsonRows* Objectives = Rows(*Complete, TEXT("objectives"));
                    Beat.Goal = ESoraBeatGoal::Interact; Beat.GoalCount = Objectives ? Objectives->Num() : 0;
                }
                else bValid = false;
                break;
            }
            case ESoraBeatType::Duel:
            {
                const TSharedPtr<FJsonObject> Scoring = Child(P, TEXT("scoring"));
                const TSharedPtr<FJsonObject> Arms = Child(P, TEXT("weapons"));
                FString Mode, PlayerArms;
                bValid = Scoring && Arms && Str(*Scoring, TEXT("mode"), Mode);
                // Bokuto and fukuro shinai bouts are sparring; live blades duel a retainer.
                Beat.Opponent = Arms && Arms->TryGetStringField(TEXT("player"), PlayerArms) &&
                    (PlayerArms == TEXT("bokuto") || PlayerArms == TEXT("fukuro_shinai")) ? ESoraOpponent::Pupil : ESoraOpponent::Invader;
                Beat.MaxAlive = 1;
                if (Mode == TEXT("lesson_gates"))
                {
                    Beat.Goal = ESoraBeatGoal::Lessons;
                    const FJsonRows* Gates = Rows(P, TEXT("lesson_gates"));
                    bValid &= Gates && !Gates->IsEmpty();
                    for (int32 Gate = 0; bValid && Gate < Gates->Num(); ++Gate)
                    {
                        const auto G = (*Gates)[Gate].IsValid() ? (*Gates)[Gate]->AsObject() : nullptr;
                        FString Name; int32 Count = 0;
                        if (!G || !Str(*G, TEXT("gate"), Name)) { bValid = false; break; }
                        if (const int32* Lesson = LessonGates.Find(Name)) Beat.LessonMask |= 1u << *Lesson;
                        // Flanking with marobashi is scored as bouts against the pupil.
                        else if (Name == TEXT("marobashi_flank"))
                        {
                            bValid = Int(*G, TEXT("count"), Count) && Count > 0;
                            Beat.GoalCount += Count;
                        }
                        // Stepping the maai ring has no measured rule yet; the stance gate carries its beat.
                        else bValid = Name == TEXT("maai_step");
                    }
                    bValid &= Beat.LessonMask != 0u || Beat.GoalCount > 0;
                    Beat.Opponents = FMath::Max(1, Beat.GoalCount);
                }
                else if (Mode == TEXT("points")) { Beat.Goal = ESoraBeatGoal::Defeat; bValid &= Int(*Scoring, TEXT("first_to"), Beat.GoalCount) && Beat.GoalCount > 0; Beat.Opponents = Beat.GoalCount; }
                else if (Mode == TEXT("hp")) { Beat.Goal = ESoraBeatGoal::Defeat; Beat.GoalCount = 1; Beat.Opponents = 1; }
                else bValid = false;
                Beat.PhaseHealthPercent.Add(100);
                if (const FJsonRows* Events = Rows(P, TEXT("events")))
                    for (const auto& Event : *Events)
                    {
                        const auto E = Event.IsValid() ? Event->AsObject() : nullptr;
                        int32 Percent = 0;
                        bValid &= E && Int(*E, TEXT("at_hp_pct"), Percent) && Percent > 0 && Percent < Beat.PhaseHealthPercent.Last();
                        Beat.PhaseHealthPercent.Add(Percent);
                    }
                break;
            }
            case ESoraBeatType::StealthZone:
            {
                // Guards and detection belong to the stealth AI; until it lands
                // the zone is crossed to its exit or its objectives are worked.
                if (CompleteKind == TEXT("exit_reached"))
                {
                    FString Volume;
                    Beat.Goal = ESoraBeatGoal::Reach;
                    if (Str(*Complete, TEXT("volume"), Volume)) Beat.AnchorEvent = TEXT("volume_enter:") + Volume;
                }
                else if (CompleteKind == TEXT("objectives"))
                {
                    const FJsonRows* Objectives = Rows(P, TEXT("objectives"));
                    if (!Objectives) Objectives = Rows(*Complete, TEXT("objectives"));
                    Beat.Goal = ESoraBeatGoal::Interact; Beat.GoalCount = Objectives ? Objectives->Num() : 0;
                }
                else bValid = false;
                break;
            }
            case ESoraBeatType::ProductionTask:
            {
                FString Task;
                bValid = Str(P, TEXT("task"), Task) && WaveOpponents(P, Beat.Opponents, Beat.MaxAlive);
                const TSharedPtr<FJsonObject> Block = bValid ? Child(P, *Task) : nullptr;
                bValid &= Block.IsValid();
                Beat.Opponent = Beat.Opponents > 0 ? ESoraOpponent::Invader : ESoraOpponent::None;
                if (!bValid) break;
                double Seconds = 0;
                if (Task == TEXT("hold"))
                {
                    const FJsonRows* Points = Rows(*Block, TEXT("interact_points"));
                    if (!Num(*Block, TEXT("hold_s"), Seconds) && Points && Num(*Block, TEXT("per_point_s"), Seconds))
                        Seconds *= Points->Num();
                    Beat.Goal = ESoraBeatGoal::Hold; Beat.GoalSeconds = static_cast<float>(Seconds);
                    bValid = Seconds > 0;
                }
                else if (Task == TEXT("escort")) Beat.Goal = ESoraBeatGoal::Reach;
                else if (Task == TEXT("carry")) { Beat.Goal = ESoraBeatGoal::Interact; bValid = Int(*Block, TEXT("count"), Beat.GoalCount); }
                else if (Task == TEXT("crank")) { Beat.Goal = ESoraBeatGoal::Interact; bValid = Int(*Block, TEXT("turns_required"), Beat.GoalCount); }
                else if (Task == TEXT("manufacture"))
                {
                    Beat.Goal = ESoraBeatGoal::Interact;
                    const FJsonRows* Steps = Rows(*Block, TEXT("steps"));
                    bValid = Steps && !Steps->IsEmpty();
                    for (int32 Step = 0; bValid && Step < Steps->Num(); ++Step)
                    {
                        const auto S = (*Steps)[Step].IsValid() ? (*Steps)[Step]->AsObject() : nullptr;
                        int32 Count = 0;
                        bValid = S && Int(*S, TEXT("count"), Count) && Count > 0;
                        Beat.GoalCount += Count;
                    }
                }
                else if (Task == TEXT("defend"))
                {
                    if (Num(*Block, TEXT("duration_s"), Seconds) && Seconds > 0) { Beat.Goal = ESoraBeatGoal::Hold; Beat.GoalSeconds = static_cast<float>(Seconds); }
                    else { Beat.Goal = ESoraBeatGoal::Defeat; Beat.GoalCount = Beat.Opponents; bValid = Beat.Opponents > 0; }
                }
                else bValid = false;
                if (Beat.Goal == ESoraBeatGoal::Interact) bValid &= Beat.GoalCount > 0;
                break;
            }
            case ESoraBeatType::HorsebackRide:
            {
                bValid = WaveOpponents(P, Beat.Opponents, Beat.MaxAlive);
                Beat.Opponent = Beat.Opponents > 0 ? ESoraOpponent::Invader : ESoraOpponent::None;
                FString Volume;
                if (CompleteKind == TEXT("reach") || CompleteKind == TEXT("volume_enter"))
                {
                    Beat.Goal = ESoraBeatGoal::Reach;
                    bValid &= Str(*Complete, TEXT("volume"), Volume);
                    Beat.AnchorEvent = TEXT("volume_enter:") + Volume;
                }
                else if (CompleteKind == TEXT("cargo_delivered"))
                {
                    const TSharedPtr<FJsonObject> Cargo = Child(P, TEXT("cargo"));
                    const FJsonRows* Dropoffs = Cargo ? Rows(*Cargo, TEXT("dropoffs")) : nullptr;
                    Beat.Goal = ESoraBeatGoal::Interact; Beat.GoalCount = Dropoffs ? Dropoffs->Num() : 0;
                    bValid &= Beat.GoalCount > 0;
                }
                else bValid = false;
                break;
            }
            case ESoraBeatType::Boss:
            {
                const FJsonRows* Phases = Rows(P, TEXT("phases"));
                FString Boss, Defeat;
                bValid = Phases && !Phases->IsEmpty() && Str(P, TEXT("boss"), Boss) && Str(P, TEXT("defeat"), Defeat);
                for (int32 Phase = 0; bValid && Phase < Phases->Num(); ++Phase)
                {
                    const auto Row = (*Phases)[Phase].IsValid() ? (*Phases)[Phase]->AsObject() : nullptr;
                    int32 Percent = 0;
                    bValid = Row && Int(*Row, TEXT("hp_pct_start"), Percent) &&
                        (Phase == 0 ? Percent == 100 : Percent > 0 && Percent < Beat.PhaseHealthPercent.Last());
                    Beat.PhaseHealthPercent.Add(Percent);
                }
                Beat.Goal = ESoraBeatGoal::Defeat; Beat.GoalCount = 1;
                Beat.Opponent = ESoraOpponent::Boss; Beat.Opponents = 1; Beat.MaxAlive = 1;
                break;
            }
            case ESoraBeatType::ExploreOptional:
            {
                TArray<FString> Rewards;
                bValid = Strings(Rows(P, TEXT("rewards")), Rewards);
                Beat.Goal = ESoraBeatGoal::Explore;
                // Arrows and other pickups refill at the cache; collectibles enter the codex.
                for (const FString& Reward : Rewards)
                {
                    const int32 Item = C.Collectibles.IndexOfByPredicate([&](const FSoraCollectible& Candidate) { return Candidate.Id == Reward; });
                    if (Item != INDEX_NONE) Beat.Rewards.Add(Item);
                }
                bValid &= Rule.Optional;
                break;
            }
            }
            // Only boss and duel phases save inside a beat, one per later phase.
            if (Rule.PhaseCheckpoints > 0 && Rule.PhaseCheckpoints >= Beat.PhaseHealthPercent.Num()) bValid = false;
            if (!bValid) return Bad(FString::Printf(TEXT("beat %s has invalid %s parameters"), *Beat.Id, *TypeName));
            C.Beats.Add(MoveTemp(Beat));
            C.Rules.Add(Rule);
        }
        if (!SoraBeatRules::ChapterValid(C.Rules.GetData(), C.Rules.Num())) return Bad(TEXT("beats violate SoraBeatRules"));
        // The opening cinematic carries the chapter's title card.
        if (C.Beats[0].Goal != ESoraBeatGoal::Cinematic) return Bad(TEXT("does not open on a cinematic"));
        // A collectible without beats lies in its explore beat's cache or, when
        // no cache holds it, along the beats played at its place.
        for (int32 Item = 0; Item < C.Collectibles.Num(); ++Item)
        {
            FSoraCollectible& Collectible = C.Collectibles[Item];
            if (!Collectible.Beats.IsEmpty()) continue;
            for (int32 Beat = 0; Beat < C.Beats.Num(); ++Beat)
                if (C.Beats[Beat].Rewards.Contains(Item)) Collectible.Beats.Add(Beat);
            for (int32 Beat = 0; Collectible.Beats.IsEmpty() && Beat < C.Beats.Num(); ++Beat)
                if (C.Beats[Beat].Place == Collectible.Place && !C.Rules[Beat].Optional) Collectible.Beats.Add(Beat);
            if (Collectible.Beats.IsEmpty()) return Bad(FString::Printf(TEXT("collectible %s is never reachable"), *Collectible.Id));
        }

        const FJsonRows* SiteRows = Rows(*Data, TEXT("sites"));
        if (!SiteRows || SiteRows->Num() != SoraBeatRules::SiteCount) return Bad(TEXT("needs three site rows"));
        for (const auto& Row : *SiteRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            int32 Index = -1, Beat = INDEX_NONE;
            const FJsonRows* Prerequisites = O ? Rows(*O, TEXT("requires_sites")) : nullptr;
            if (!O || !Int(*O, TEXT("index"), Index) || !C.Sites.IsValidIndex(Index) || C.Sites[Index].Beat != INDEX_NONE ||
                !BeatRef(*O, Beat) || Beat == INDEX_NONE || C.Rules[Beat].Site != Index || !Prerequisites)
                return Bad(TEXT("site row disagrees with its beat"));
            for (const auto& Prerequisite : *Prerequisites)
            {
                double Number = 0; int32 Prior = -1;
                if (!Prerequisite.IsValid() || !Prerequisite->TryGetNumber(Number) || !Whole(Number, Prior) ||
                    Prior < 0 || Prior >= SoraBeatRules::SiteCount || Prior == Index)
                    return Bad(TEXT("invalid site prerequisite"));
                C.Sites[Index].RequiredSitesMask |= 1 << Prior;
            }
            C.Sites[Index].Beat = Beat;
        }

        const FJsonRows* TriggerRows = Rows(*Data, TEXT("triggers"));
        if (!TriggerRows) return Bad(TEXT("lacks its trigger table"));
        for (const auto& Row : *TriggerRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            FSoraDialogueTrigger Trigger;
            if (!O || !BeatRef(*O, Trigger.Beat) || !Str(*O, TEXT("on"), Trigger.On) || !LineRefs(Rows(*O, TEXT("lines")), Trigger.Lines) ||
                !O->TryGetBoolField(TEXT("repeatable"), Trigger.bRepeatable) ||
                (!IsNull(*O, TEXT("at_ms")) && (!Int(*O, TEXT("at_ms"), Trigger.AtMs) || Trigger.AtMs < 0)))
                return Bad(TEXT("invalid trigger row"));
            // A cinematic subtitle is placed on the cinematic's own clock.
            if (Trigger.On == TEXT("subtitle") &&
                (Trigger.AtMs < 0 || Trigger.Beat == INDEX_NONE || C.Beats[Trigger.Beat].Goal != ESoraBeatGoal::Cinematic))
                return Bad(TEXT("subtitle outside a cinematic"));
            C.Triggers.Add(MoveTemp(Trigger));
        }
        const FJsonRows* PromptRows = Rows(*Data, TEXT("ui_prompts"));
        if (!PromptRows) return Bad(TEXT("lacks its HUD prompts"));
        for (const auto& Row : *PromptRows)
        {
            const auto O = Row.IsValid() ? Row->AsObject() : nullptr;
            FSoraPrompt Prompt; TArray<FString> Beats;
            if (!O || !Str(*O, TEXT("ja"), Prompt.Japanese) || !Str(*O, TEXT("en"), Prompt.English) ||
                !Strings(Rows(*O, TEXT("beats")), Beats) || (!IsNull(*O, TEXT("on")) && !Str(*O, TEXT("on"), Prompt.On)))
                return Bad(TEXT("invalid HUD prompt"));
            for (const FString& Beat : Beats)
            {
                if (!BeatIds.Contains(Beat)) return Bad(TEXT("HUD prompt names an unknown beat"));
                Prompt.Beats.Add(BeatIds[Beat]);
            }
            C.Prompts.Add(MoveTemp(Prompt));
        }
        Chapters.Add(MoveTemp(C));
    }
    // Every route through the campaign ends holding all 21 weapons and every mechanic.
    if (RouteMinimumWeapons(ChapterCount) != SoraBeatRules::AllWeaponsMask ||
        EarlierWeapons(ChapterCount) != SoraBeatRules::AllWeaponsMask ||
        EarlierMechanics(ChapterCount) != SoraBeatRules::AllMechanicsMask)
        return Fail(TEXT("The campaign does not unlock every weapon and mechanic on every route"));
    return true;
}

unsigned FSoraCatalog::RouteMinimumWeapons(int32 Chapter) const
{
    unsigned Mask = 0u;
    for (int32 Index = 0; Index < Chapter && Chapters.IsValidIndex(Index); ++Index)
        Mask |= SoraBeatRules::ChapterWeapons(Chapters[Index].Rules.GetData(), Chapters[Index].Rules.Num(), false);
    return Mask;
}
unsigned FSoraCatalog::EarlierWeapons(int32 Chapter) const
{
    unsigned Mask = 0u;
    for (int32 Index = 0; Index < Chapter && Chapters.IsValidIndex(Index); ++Index)
        Mask |= SoraBeatRules::ChapterWeapons(Chapters[Index].Rules.GetData(), Chapters[Index].Rules.Num(), true);
    return Mask;
}
unsigned FSoraCatalog::EarlierMechanics(int32 Chapter) const
{
    unsigned Mask = 0u;
    for (int32 Index = 0; Index < Chapter && Chapters.IsValidIndex(Index); ++Index)
        Mask |= SoraBeatRules::ChapterMechanics(Chapters[Index].Rules.GetData(), Chapters[Index].Rules.Num());
    return Mask;
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
