#include "Combat/SoraEnemyCatalog.h"
#include "Combat/SoraDataReader.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace
{
using FReader = FSoraDataReader;
constexpr const TCHAR* EnemiesFile = TEXT("enemies.json");

int32 HalfArcMilli(int32 Degrees)
{
    return FMath::RoundToInt32(FMath::Cos(FMath::DegreesToRadians(Degrees * .5)) * 1000.0);
}

const TCHAR* const Behaviors[] = {TEXT("blade"), TEXT("rifle"), TEXT("shield"), TEXT("grenadier"), TEXT("marksman"),
    TEXT("drone"), TEXT("conscript"), TEXT("auditor"), TEXT("automaton"), TEXT("walker")};
const TCHAR* const Bodies[] = {TEXT("alien"), TEXT("local"), TEXT("drone"), TEXT("machine"), TEXT("walker")};
const TCHAR* const AttackKinds[] = {TEXT("melee"), TEXT("burst"), TEXT("lock_shot"), TEXT("lob"), TEXT("beam"), TEXT("net")};
const TCHAR* const Telegraphs[] = {TEXT("amber"), TEXT("cyan")};
const TCHAR* const Factions[] = {TEXT("credit_house"), TEXT("debt_bound")};

bool ReadPerception(const FReader& R, const FJsonObject& O, SoraStealthRules::FPerception& P)
{
    int32 Sight = 0, Dark = 0, View = 0;
    if (!R.Int(O, TEXT("sight_cm"), Sight, 100, 10000) || !R.Int(O, TEXT("dark_sight_cm"), Dark, 0, Sight) ||
        !R.Int(O, TEXT("view_deg"), View, 10, 360) || !R.Int(O, TEXT("hearing_cm"), P.HearingCm, 0, 10000) ||
        !R.Int(O, TEXT("suspicion_permille"), P.SuspicionPermille, 100, 2000) || !R.Flag(O, TEXT("alarmist"), P.Alarmist))
        return false;
    P.SightRangeCm = Sight;
    P.DarkSightRangeCm = Dark;
    P.ViewConeMilli = HalfArcMilli(View);
    P.FocusConeMilli = FMath::Max(P.ViewConeMilli, SoraStealthRules::FocusConeMilli);
    return true;
}

bool ReadBarrier(const FReader& R, const FJsonObject& O, FSoraEnemyBarrier& B)
{
    if (!R.Int(O, TEXT("health"), B.Health, 1, 10000) || !R.Int(O, TEXT("regen_delay_ms"), B.RegenDelayMs, 0, 60000) ||
        !R.Int(O, TEXT("regen_per_s"), B.RegenPerSecond, 0, 10000) || !R.Int(O, TEXT("break_stagger_ms"), B.BreakStaggerMs, 0, 10000) ||
        !R.Int(O, TEXT("melee_permille"), B.MeleePermille, 0, 10000))
        return false;
    TSharedPtr<FJsonObject> Weapons;
    const TArray<TSharedPtr<FJsonValue>>* Bypass = nullptr;
    if (!R.Object(O, TEXT("weapon_permille"), Weapons) || !R.Array(O, TEXT("bypass_weapons"), Bypass))
        return false;
    for (const auto& Pair : Weapons->Values)
    {
        const FString Key(*Pair.Key);
        bool bDigits = !Key.IsEmpty() && Key.Len() <= 2;
        for (const TCHAR Character : Key)
            bDigits &= FChar::IsDigit(Character);
        const int32 WeaponId = bDigits ? FCString::Atoi(*Key) : -1;
        int32 Permille = 0;
        if (WeaponId < 0 || WeaponId > 20)
            return R.Fail(TEXT("weapon_permille"), TEXT("keys must be catalog weapon ids"));
        if (!R.Int(*Weapons, *Key, Permille, 0, 10000))
            return false;
        B.WeaponPermille.Add(WeaponId, Permille);
    }
    for (const auto& Value : *Bypass)
    {
        double WeaponId = -1.0;
        if (!Value->TryGetNumber(WeaponId) || WeaponId != FMath::FloorToDouble(WeaponId) || WeaponId < 0 || WeaponId > 20)
            return R.Fail(TEXT("bypass_weapons"), TEXT("must list catalog weapon ids"));
        B.BypassWeapons.Add(static_cast<int32>(WeaponId));
    }
    return true;
}

bool ReadAttack(const FReader& R, const FJsonObject& O, FSoraEnemyAttack& A)
{
    ESoraEnemyAttackKind Kind = ESoraEnemyAttackKind::Melee;
    int32 Telegraph = 0;
    const TArray<TSharedPtr<FJsonValue>>* Range = nullptr;
    if (!R.Name(O, TEXT("id"), A.Id) || !R.Name(O, TEXT("cue"), A.Cue) || !R.Text(O, TEXT("name_ja"), A.NameJapanese) ||
        !R.Text(O, TEXT("name_en"), A.NameEnglish) || !R.Choice(O, TEXT("kind"), AttackKinds, Kind) ||
        !R.Choice(O, TEXT("telegraph"), Telegraphs, Telegraph) || !R.Int(O, TEXT("damage"), A.Damage, 0, 1000) ||
        !R.Int(O, TEXT("windup_ms"), A.WindupMs, 300, 5000) || !R.Int(O, TEXT("recovery_ms"), A.RecoveryMs, 0, 20000) ||
        !R.Int(O, TEXT("cooldown_ms"), A.CooldownMs, 0, 60000) || !R.Array(O, TEXT("range_cm"), Range))
        return false;
    A.Kind = Kind;
    A.bCyanTelegraph = Telegraph == 1;
    double Low = -1.0, High = -1.0;
    if (Range->Num() != 2 || !(*Range)[0]->TryGetNumber(Low) || !(*Range)[1]->TryGetNumber(High) ||
        Low != FMath::FloorToDouble(Low) || High != FMath::FloorToDouble(High) || Low < 0 || High <= Low || High > 10000)
        return R.Fail(TEXT("range_cm"), TEXT("must be [minimum, maximum] centimetres"));
    A.MinRangeCm = static_cast<int32>(Low);
    A.MaxRangeCm = static_cast<int32>(High);
    switch (Kind)
    {
    case ESoraEnemyAttackKind::Melee:
    {
        int32 Arc = 0;
        TSharedPtr<FJsonObject> Guard;
        if (!R.Int(O, TEXT("arc_deg"), Arc, 10, 360) || !R.Int(O, TEXT("knockback_cm"), A.KnockbackCm, 0, 1000) ||
            !R.Int(O, TEXT("hero_stagger_ms"), A.HeroStaggerMs, 0, 5000) || !R.Object(O, TEXT("guard"), Guard) ||
            !R.Flag(*Guard, TEXT("parry"), A.bParryable) || !R.Int(*Guard, TEXT("chip"), A.GuardChip, 0, A.Damage) ||
            !R.Int(*Guard, TEXT("stamina"), A.GuardStamina, 0, 100) ||
            !R.Int(*Guard, TEXT("parry_stagger_ms"), A.ParryStaggerMs, 0, 5000) || !R.Flag(*Guard, TEXT("breaks"), A.bBreaksGuard))
            return false;
        if (A.bParryable != (A.ParryStaggerMs > 0))
            return R.Fail(TEXT("guard"), TEXT("a parryable blow staggers its attacker; an unparryable one cannot"));
        A.ArcMilli = Arc >= 360 ? -1000 : HalfArcMilli(Arc);
        return true;
    }
    case ESoraEnemyAttackKind::Burst:
        if (!R.Int(O, TEXT("rounds"), A.Rounds, 1, 10) || !R.Int(O, TEXT("interval_ms"), A.IntervalMs, 50, 2000))
            return false;
        return A.Damage > 0 || R.Fail(TEXT("damage"), TEXT("a burst must hurt"));
    case ESoraEnemyAttackKind::LockShot:
        return A.Damage > 0 || R.Fail(TEXT("damage"), TEXT("a shot must hurt"));
    case ESoraEnemyAttackKind::Lob:
        if (!R.Int(O, TEXT("radius_cm"), A.RadiusCm, 50, 2000) || !R.Int(O, TEXT("flight_ms"), A.FlightMs, 300, 5000) ||
            !R.Int(O, TEXT("arming_cm"), A.ArmingCm, 0, 5000))
            return false;
        if (A.MinRangeCm <= A.RadiusCm)
            return R.Fail(TEXT("range_cm"), TEXT("a lob's minimum range must clear its own blast"));
        return A.Damage > 0 || R.Fail(TEXT("damage"), TEXT("a shell must hurt"));
    case ESoraEnemyAttackKind::Beam:
        if (!R.Int(O, TEXT("width_cm"), A.WidthCm, 10, 2000))
            return false;
        return A.Damage > 0 || R.Fail(TEXT("damage"), TEXT("a beam must hurt"));
    case ESoraEnemyAttackKind::Net:
        return R.Int(O, TEXT("radius_cm"), A.RadiusCm, 50, 1000) && R.Int(O, TEXT("root_ms"), A.RootMs, 100, 10000);
    }
    return false;
}

bool ReadVariant(const FReader& R, const FJsonObject& O, FSoraEnemyVariant& V)
{
    if (!R.Name(O, TEXT("id"), V.Id) || !R.Text(O, TEXT("name_ja"), V.NameJapanese) ||
        !R.Text(O, TEXT("name_en"), V.NameEnglish) || !R.Int(O, TEXT("health"), V.Health, 0, 100000))
        return false;
    const TSharedPtr<FJsonObject>* Perception = nullptr;
    if (O.TryGetObjectField(TEXT("perception"), Perception) && Perception && Perception->IsValid())
    {
        if (!R.Int(**Perception, TEXT("sight_cm"), V.SightCm, 100, 10000) ||
            !R.Int(**Perception, TEXT("dark_sight_cm"), V.DarkSightCm, 0, V.SightCm) ||
            !R.Int(**Perception, TEXT("view_deg"), V.ViewDegrees, 10, 360))
            return false;
    }
    const TSharedPtr<FJsonObject>* Barrier = nullptr;
    if (O.TryGetObjectField(TEXT("barrier"), Barrier) && Barrier && Barrier->IsValid() && !ReadBarrier(R, **Barrier, V.Barrier))
        return false;
    if (V.Health == 0 && V.SightCm < 0 && V.Barrier.Health == 0)
        return R.Fail(TEXT("id"), TEXT("a variant must change health, perception or barrier"));
    return true;
}

bool ReadArchetype(FString& Error, const FJsonObject& O, int32 Index, FSoraEnemyArchetype& E)
{
    FReader R{Error, EnemiesFile, FString::Printf(TEXT("archetypes[%d]"), Index)};
    int32 Faction = 0;
    if (!R.Name(O, TEXT("id"), E.Id))
        return false;
    R.Where = E.Id.ToString();
    TSharedPtr<FJsonObject> Perception, Defense, Tactics;
    const TArray<TSharedPtr<FJsonValue>>* Attacks = nullptr;
    const TArray<TSharedPtr<FJsonValue>>* Variants = nullptr;
    int32 FrontBlock = 0;
    if (!R.Text(O, TEXT("name_ja"), E.NameJapanese) || !R.Text(O, TEXT("reading"), E.Reading) ||
        !R.Text(O, TEXT("name_en"), E.NameEnglish) || !R.Text(O, TEXT("weapon_ja"), E.WeaponJapanese) ||
        !R.Text(O, TEXT("weapon_en"), E.WeaponEnglish) || !R.Choice(O, TEXT("faction"), Factions, Faction) ||
        !R.Choice(O, TEXT("body"), Bodies, E.Body) || !R.Choice(O, TEXT("behavior"), Behaviors, E.Behavior) ||
        !R.Int(O, TEXT("first_chapter"), E.FirstChapter, 1, 8) || !R.Int(O, TEXT("health"), E.Health, 1, 100000) ||
        !R.Int(O, TEXT("speed_cm_s"), E.SpeedCmPerSecond, 0, 2000) || !R.Int(O, TEXT("turn_deg_s"), E.TurnDegreesPerSecond, 10, 720) ||
        !R.Int(O, TEXT("scale_permille"), E.ScalePermille, 300, 4000) || !R.Flag(O, TEXT("lethal"), E.bLethal) ||
        !R.Object(O, TEXT("perception"), Perception) || !ReadPerception(R, *Perception, E.Perception) ||
        !R.Object(O, TEXT("defense"), Defense) || !R.Int(*Defense, TEXT("front_block_deg"), FrontBlock, 0, 360) ||
        !R.Int(*Defense, TEXT("rim_opening_ms"), E.RimOpeningMs, 0, 5000) ||
        !R.Int(*Defense, TEXT("rear_weak_permille"), E.RearWeakPermille, 1000, 5000) ||
        !R.Int(*Defense, TEXT("poise_ms"), E.PoiseMs, 0, 10000) || !R.Flag(*Defense, TEXT("rear_takedown"), E.bRearTakedown) ||
        !R.Object(O, TEXT("tactics"), Tactics) ||
        !R.Int(*Tactics, TEXT("keep_distance_cm"), E.KeepDistanceCm, 0, 5000) ||
        !R.Int(*Tactics, TEXT("relocate_after_shots"), E.RelocateAfterShots, 0, 20) ||
        !R.Int(*Tactics, TEXT("hover_cm"), E.HoverCm, 0, 3000) || !R.Int(*Tactics, TEXT("alarm_radius_cm"), E.AlarmRadiusCm, 0, 10000) ||
        !R.Flag(*Tactics, TEXT("static"), E.bStatic) || !R.Array(O, TEXT("attacks"), Attacks) ||
        !R.Array(O, TEXT("variants"), Variants))
        return false;
    E.bDebtBound = Faction == 1;
    E.bShield = FrontBlock > 0;
    E.ShieldHalfArcMilli = E.bShield ? HalfArcMilli(FrontBlock) : 1000;
    if (E.bShield != (E.RimOpeningMs > 0))
        return R.Fail(TEXT("defense"), TEXT("a shield turns on its rim, and only a shield does"));
    if (E.bRearTakedown != (E.Body == ESoraEnemyBody::Alien || E.Body == ESoraEnemyBody::Local))
        return R.Fail(TEXT("defense.rear_takedown"), TEXT("cats, and only cats, can be taken down from behind"));
    if (!E.bLethal)
    {
        TSharedPtr<FJsonObject> Subdue;
        if (!R.Object(O, TEXT("subdue"), Subdue) || !R.Int(*Subdue, TEXT("window_ms"), E.SubdueWindowMs, 1000, 60000) ||
            !R.Int(*Subdue, TEXT("seal_cut_hold_ms"), E.SealCutHoldMs, 100, E.SubdueWindowMs) ||
            !R.Int(*Subdue, TEXT("rise_health_permille"), E.RiseHealthPermille, 1, 1000))
            return false;
    }
    else if (O.HasField(TEXT("subdue")))
        return R.Fail(TEXT("subdue"), TEXT("only a nonlethal archetype is subdued"));
    if (E.bDebtBound == E.bLethal)
        return R.Fail(TEXT("lethal"), TEXT("the debt-bound, and only they, are nonlethal"));
    if (E.Behavior == ESoraEnemyBehavior::Drone ? E.HoverCm <= 0 : E.HoverCm != 0)
        return R.Fail(TEXT("tactics.hover_cm"), TEXT("drones, and only drones, hover"));
    if (E.bStatic != (E.SpeedCmPerSecond == 0))
        return R.Fail(TEXT("tactics.static"), TEXT("a static archetype has no speed, and only it"));
    for (int32 AttackIndex = 0; AttackIndex < Attacks->Num(); ++AttackIndex)
    {
        const TSharedPtr<FJsonObject> Row = (*Attacks)[AttackIndex]->AsObject();
        FReader AttackReader{Error, EnemiesFile, FString::Printf(TEXT("%s.attacks[%d]"), *R.Where, AttackIndex)};
        if (!Row.IsValid())
            return AttackReader.Fail(TEXT("row"), TEXT("not an object"));
        FSoraEnemyAttack& Attack = E.Attacks.AddDefaulted_GetRef();
        if (!ReadAttack(AttackReader, *Row, Attack))
            return false;
        for (int32 Earlier = 0; Earlier < AttackIndex; ++Earlier)
            if (E.Attacks[Earlier].Id == Attack.Id)
                return AttackReader.Fail(TEXT("id"), TEXT("duplicate attack"));
    }
    if (E.Attacks.IsEmpty() != (E.Behavior == ESoraEnemyBehavior::Auditor))
        return R.Fail(TEXT("attacks"), TEXT("every archetype but the auditor attacks"));
    for (int32 VariantIndex = 0; VariantIndex < Variants->Num(); ++VariantIndex)
    {
        const TSharedPtr<FJsonObject> Row = (*Variants)[VariantIndex]->AsObject();
        FReader VariantReader{Error, EnemiesFile, FString::Printf(TEXT("%s.variants[%d]"), *R.Where, VariantIndex)};
        if (!Row.IsValid())
            return VariantReader.Fail(TEXT("row"), TEXT("not an object"));
        FSoraEnemyVariant& Variant = E.Variants.AddDefaulted_GetRef();
        if (!ReadVariant(VariantReader, *Row, Variant))
            return false;
        for (int32 Earlier = 0; Earlier < VariantIndex; ++Earlier)
            if (E.Variants[Earlier].Id == Variant.Id)
                return VariantReader.Fail(TEXT("id"), TEXT("duplicate variant"));
    }
    return true;
}
} // namespace

int32 FSoraEnemyBarrier::PermilleFor(int32 WeaponId, bool bMelee) const
{
    if (const int32* Permille = WeaponPermille.Find(WeaponId))
        return *Permille;
    return bMelee ? MeleePermille : 1000;
}

const FSoraEnemyVariant* FSoraEnemyArchetype::Variant(FName VariantId) const
{
    return Variants.FindByPredicate([VariantId](const FSoraEnemyVariant& V) { return V.Id == VariantId; });
}

bool FSoraEnemyArchetype::IsMelee() const
{
    return Behavior == ESoraEnemyBehavior::Blade || Behavior == ESoraEnemyBehavior::Shield ||
        Behavior == ESoraEnemyBehavior::Conscript || Behavior == ESoraEnemyBehavior::Automaton;
}

FSoraEnemyCatalog& FSoraEnemyCatalog::Get()
{
    static FSoraEnemyCatalog Catalog;
    return Catalog;
}

const FSoraEnemyArchetype* FSoraEnemyCatalog::Find(FName Id) const
{
    return bReady ? Entries.FindByPredicate([Id](const FSoraEnemyArchetype& E) { return E.Id == Id; }) : nullptr;
}

bool FSoraEnemyCatalog::Load()
{
    if (bReady)
        return true;
    Entries.Reset();
    FString Text;
    TSharedPtr<FJsonObject> Root;
    const FString Path = FPaths::ProjectContentDir() / TEXT("Data/enemies.json");
    double Schema = 0.0;
    const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
    if (!FFileHelper::LoadFileToString(Text, *Path) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid())
        Error = TEXT("Cannot load Content/Data/enemies.json");
    else if (!Root->TryGetNumberField(TEXT("schema_version"), Schema) || Schema != 1)
        Error = TEXT("Unsupported enemies.json schema");
    else if (!Root->TryGetArrayField(TEXT("archetypes"), Rows) || !Rows || Rows->IsEmpty())
        Error = TEXT("enemies.json lists no archetypes");
    else
    {
        // Pointers to archetypes stay valid for the program's life: the array
        // never grows after a successful load.
        Entries.Reserve(Rows->Num());
        bool bValid = true;
        for (int32 Index = 0; bValid && Index < Rows->Num(); ++Index)
        {
            const TSharedPtr<FJsonObject> Row = (*Rows)[Index]->AsObject();
            FSoraEnemyArchetype& Entry = Entries.AddDefaulted_GetRef();
            bValid = Row.IsValid() && ReadArchetype(Error, *Row, Index, Entry);
            if (!Row.IsValid())
                Error = FString::Printf(TEXT("enemies.json archetypes[%d] is not an object"), Index);
            for (int32 Earlier = 0; bValid && Earlier < Index; ++Earlier)
                if (Entries[Earlier].Id == Entry.Id)
                {
                    Error = FString::Printf(TEXT("enemies.json repeats archetype %s"), *Entry.Id.ToString());
                    bValid = false;
                }
        }
        if (bValid)
        {
            Error.Reset();
            bReady = true;
            return true;
        }
        Entries.Reset();
    }
    UE_LOG(LogTemp, Error, TEXT("%s"), *Error);
    return false;
}
