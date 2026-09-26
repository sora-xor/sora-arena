#include "Combat/SoraBossCatalog.h"
#include "Combat/SoraDataReader.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace SoraBossLoader
{
using FReader = FSoraDataReader;
constexpr const TCHAR* BossesFile = TEXT("bosses.json");
constexpr int32 LongestMs = 600000;
constexpr int32 FarthestCm = 100000;

const TCHAR* const Kinds[] = {TEXT("cut"), TEXT("thrust"), TEXT("feint"), TEXT("charge"), TEXT("area"), TEXT("beam"),
    TEXT("volley"), TEXT("zone"), TEXT("summon"), TEXT("pulse"), TEXT("expose"), TEXT("step")};
const TCHAR* const Telegraphs[] = {TEXT("amber"), TEXT("cyan"), TEXT("none")};
const TCHAR* const Moves[] = {TEXT("close"), TEXT("keep"), TEXT("hunt"), TEXT("hold")};
const TCHAR* const Patterns[] = {TEXT("sequence"), TEXT("priority"), TEXT("weighted")};
const TCHAR* const Defeats[] = {TEXT("kill"), TEXT("disarm"), TEXT("capture"), TEXT("destroy_weakpoints"), TEXT("points")};
const TCHAR* const Finishers[] = {TEXT("none"), TEXT("muto_dori")};
const TCHAR* const Bodies[] = {TEXT("alien"), TEXT("local"), TEXT("machine")};
const TCHAR* const Senses[] = {TEXT("sight"), TEXT("hearing")};
const TCHAR* const ZoneAts[] = {TEXT("target"), TEXT("around_target"), TEXT("anchor"), TEXT("anchor_or_target")};
const TCHAR* const Parries[] = {TEXT("none"), TEXT("measure_reset"), TEXT("mantle_down")};
const TCHAR* const ChargeTargets[] = {TEXT("hero"), TEXT("noise")};
// Every bark answers one of these; the chapter scripts hold the lines.
const TCHAR* const BarkEvents[] = {TEXT("stagger"), TEXT("shield_broken"), TEXT("barrier_broken"), TEXT("mantle_down"),
    TEXT("countered"), TEXT("missed"), TEXT("weakpoint_destroyed"), TEXT("seal"), TEXT("defeated"), TEXT("muto_dori")};

int32 HalfArcMilli(int32 Degrees)
{
    return Degrees >= 360 ? -1000 : FMath::RoundToInt32(FMath::Cos(FMath::DegreesToRadians(Degrees * .5)) * 1000.0);
}

// Attack references are written as ids and resolved once every attack is read.
struct FPendingAttack
{
    FName Then;
    TArray<FName> Opens;
    FName Group;
};

int32 IndexOf(const TArray<FSoraBossWeakPoint>& Points, FName Id)
{
    return Points.IndexOfByPredicate([Id](const FSoraBossWeakPoint& P) { return P.Id == Id; });
}

bool ReadGuard(const FReader& R, const FJsonObject& O, FSoraBossGuard& G, int32 Damage, int32 Hits)
{
    TSharedPtr<FJsonObject> Guard;
    if (!R.Object(O, TEXT("guard"), Guard))
        return false;
    const FReader In{R.Error, R.File, R.Where + TEXT(".guard")};
    if (!In.Only(*Guard, {TEXT("guardable"), TEXT("chip"), TEXT("stamina"), TEXT("breaks"), TEXT("parry"), TEXT("parry_hit"),
            TEXT("parry_stagger_ms")}) ||
        !In.Flag(*Guard, TEXT("guardable"), G.bGuardable) || !In.Int(*Guard, TEXT("chip"), G.Chip, 0, Damage) ||
        !In.Int(*Guard, TEXT("stamina"), G.Stamina, 0, 100) || !In.Flag(*Guard, TEXT("breaks"), G.bBreaks) ||
        !In.Flag(*Guard, TEXT("parry"), G.bParry) || !In.Int(*Guard, TEXT("parry_hit"), G.ParryHit, 0, Hits) ||
        !In.Int(*Guard, TEXT("parry_stagger_ms"), G.ParryStaggerMs, 0, 5000))
        return false;
    if (!G.bParry && (G.ParryHit != 0 || G.ParryStaggerMs != 0))
        return In.Fail(TEXT("parry"), TEXT("an unparryable blow has no parried hit or stagger"));
    if (!G.bGuardable && (G.Stamina != 0 || G.bBreaks || G.Chip != Damage))
        return In.Fail(TEXT("guardable"), TEXT("an unguardable blow lets all of itself through and costs no stamina"));
    return true;
}

bool ReadBlow(const FReader& R, const FJsonObject& O, FSoraBossAttack& A, bool bThrust)
{
    int32 Arc = 0;
    if (bThrust ? !R.Int(O, TEXT("width_cm"), A.WidthCm, 20, 1000) : !R.Int(O, TEXT("arc_deg"), Arc, 10, 360))
        return false;
    if (!R.Int(O, TEXT("hits"), A.Hits, 1, 6) || !R.Int(O, TEXT("gap_ms"), A.GapMs, 0, 2000) ||
        !R.Int(O, TEXT("lunge_cm"), A.LungeCm, 0, 1000) || !R.Int(O, TEXT("pull_cm"), A.PullCm, 0, 1000) ||
        !R.Int(O, TEXT("knockback_cm"), A.KnockbackCm, 0, 1000) || !R.Int(O, TEXT("hero_stagger_ms"), A.HeroStaggerMs, 0, 3000) ||
        !ReadGuard(R, O, A.Guard, A.Damage, A.Hits) || !R.Int(O, TEXT("marobashi_ms"), A.MarobashiMs, 0, 1000) ||
        !R.Flag(O, TEXT("muto"), A.bMuto) || !R.Choice(O, TEXT("on_parry"), Parries, A.OnParry) ||
        !R.Int(O, TEXT("if_guard_held_ms"), A.IfGuardHeldMs, 0, 10000))
        return false;
    A.ArcMilli = bThrust ? 1000 : HalfArcMilli(Arc);
    if ((A.Hits > 1) != (A.GapMs > 0))
        return R.Fail(TEXT("gap_ms"), TEXT("a multi-hit blow spaces its hits, and only it"));
    if (A.MarobashiMs > A.WindupMs)
        return R.Fail(TEXT("marobashi_ms"), TEXT("the 転 stretch is the end of the windup"));
    // A parry that neither staggers nor answers still spares the blow and
    // opens the 転 step after it; such a blow must also allow 転 in its windup.
    if (A.Guard.bParry && A.Guard.ParryStaggerMs == 0 && A.OnParry == ESoraBossParry::None && A.MarobashiMs == 0)
        return R.Fail(TEXT("guard"), TEXT("a parry staggers the attacker or answers with an effect, or 転 answers the blow (marobashi_ms)"));
    if (!A.Guard.bParry && A.OnParry != ESoraBossParry::None)
        return R.Fail(TEXT("on_parry"), TEXT("only a parryable blow answers a parry"));
    if (A.bMuto && (!A.Guard.bParry || bThrust))
        return R.Fail(TEXT("muto"), TEXT("mutō-dori meets a committed cut, which a drawn blade may also parry"));
    return A.Damage > 0 || R.Fail(TEXT("damage"), TEXT("a blow must hurt"));
}

bool ReadAttack(const FReader& R, const FJsonObject& O, FSoraBossAttack& A, FPendingAttack& Pending, bool bBlind)
{
    const TArray<TSharedPtr<FJsonValue>>* Range = nullptr;
    if (!R.Name(O, TEXT("id"), A.Id))
        return false;
    FReader In = R;
    In.Where = R.Where + TEXT(".") + A.Id.ToString();
    if (!In.Choice(O, TEXT("kind"), Kinds, A.Kind))
        return false;
    const TCHAR* Block = Kinds[static_cast<int32>(A.Kind)];
    if (!In.Only(O, {TEXT("id"), TEXT("kind"), TEXT("name_ja"), TEXT("name_en"), TEXT("tell_ja"), TEXT("tell_en"), TEXT("telegraph"),
            TEXT("bark"), TEXT("bark_once"), TEXT("bark_cooldown_ms"), TEXT("windup_ms"), TEXT("active_ms"), TEXT("recovery_ms"),
            TEXT("cooldown_ms"), TEXT("range_cm"), TEXT("damage"), TEXT("repeat"), TEXT("repeat_gap_ms"), Block}) ||
        !In.Text(O, TEXT("name_ja"), A.NameJapanese) || !In.Text(O, TEXT("name_en"), A.NameEnglish) ||
        !In.Text(O, TEXT("tell_ja"), A.TellJapanese) || !In.Text(O, TEXT("tell_en"), A.TellEnglish) ||
        !In.Choice(O, TEXT("telegraph"), Telegraphs, A.Telegraph) || !In.Line(O, TEXT("bark"), A.Bark) ||
        !In.Flag(O, TEXT("bark_once"), A.bBarkOnce) || !In.Int(O, TEXT("bark_cooldown_ms"), A.BarkCooldownMs, 0, 60000) ||
        !In.Int(O, TEXT("windup_ms"), A.WindupMs, 0, 5000) || !In.Int(O, TEXT("active_ms"), A.ActiveMs, 0, LongestMs) ||
        !In.Int(O, TEXT("recovery_ms"), A.RecoveryMs, 0, 10000) || !In.Int(O, TEXT("cooldown_ms"), A.CooldownMs, 0, 120000) ||
        !In.Array(O, TEXT("range_cm"), Range) || !In.Int(O, TEXT("damage"), A.Damage, 0, 200) ||
        !In.Int(O, TEXT("repeat"), A.Repeat, 1, 4) || !In.Int(O, TEXT("repeat_gap_ms"), A.RepeatGapMs, 0, 5000))
        return false;
    double Low = -1.0, High = -1.0;
    if (Range->Num() != 2 || !(*Range)[0]->TryGetNumber(Low) || !(*Range)[1]->TryGetNumber(High) ||
        Low != FMath::FloorToDouble(Low) || High != FMath::FloorToDouble(High) || Low < 0 || High <= Low || High > FarthestCm)
        return In.Fail(TEXT("range_cm"), TEXT("must be [minimum, maximum] centimetres"));
    A.MinRangeCm = static_cast<int32>(Low);
    A.MaxRangeCm = static_cast<int32>(High);
    if (A.Bark.IsNone() && (A.bBarkOnce || A.BarkCooldownMs > 0))
        return In.Fail(TEXT("bark"), TEXT("only a bark repeats once or on a cooldown"));
    if (A.Repeat > 1 && A.Kind != ESoraBossAttackKind::Charge && !A.IsBlow())
        return In.Fail(TEXT("repeat"), TEXT("only blows and charges repeat"));
    if ((A.Repeat > 1) != (A.RepeatGapMs > 0) && A.Kind != ESoraBossAttackKind::Charge)
        return In.Fail(TEXT("repeat_gap_ms"), TEXT("a repeated blow waits before its next windup, and only it"));
    TSharedPtr<FJsonObject> Spec;
    if (!In.Object(O, Block, Spec))
        return false;
    const FReader K{R.Error, R.File, In.Where + TEXT(".") + Block};
    const FJsonObject& S = *Spec;
    switch (A.Kind)
    {
    case ESoraBossAttackKind::Cut:
    case ESoraBossAttackKind::Thrust:
    {
        const bool bThrust = A.Kind == ESoraBossAttackKind::Thrust;
        return K.Only(S, {bThrust ? TEXT("width_cm") : TEXT("arc_deg"), TEXT("hits"), TEXT("gap_ms"), TEXT("lunge_cm"),
                   TEXT("pull_cm"), TEXT("knockback_cm"), TEXT("hero_stagger_ms"), TEXT("guard"), TEXT("marobashi_ms"),
                   TEXT("muto"), TEXT("on_parry"), TEXT("if_guard_held_ms")}) &&
            ReadBlow(K, S, A, bThrust);
    }
    case ESoraBossAttackKind::Feint:
        if (!K.Only(S, {TEXT("hold_ms"), TEXT("then")}) || !K.Int(S, TEXT("hold_ms"), A.HoldMs, 0, 2000) ||
            !K.Name(S, TEXT("then"), Pending.Then))
            return false;
        return A.Damage == 0 || K.Fail(TEXT("damage"), TEXT("a feint does no damage itself"));
    case ESoraBossAttackKind::Charge:
    {
        bool bNoise = false;
        if (!K.Only(S, {TEXT("radius_cm"), TEXT("width_cm"), TEXT("target"), TEXT("miss_recovery_ms"), TEXT("knockback_cm"), TEXT("guard")}) ||
            !K.Int(S, TEXT("radius_cm"), A.RadiusCm, 50, 1000) || !K.Int(S, TEXT("width_cm"), A.WidthCm, 0, 1000) ||
            !K.Choice(S, TEXT("target"), ChargeTargets, bNoise) || !K.Int(S, TEXT("miss_recovery_ms"), A.MissRecoveryMs, 0, 5000) ||
            !K.Int(S, TEXT("knockback_cm"), A.KnockbackCm, 0, 1000) || !ReadGuard(K, S, A.Guard, A.Damage, 1))
            return false;
        A.bToNoise = bNoise;
        if (A.bToNoise != bBlind)
            return K.Fail(TEXT("target"), TEXT("a blind hunter charges at noises, and only it"));
        if (A.Guard.bParry)
            return K.Fail(TEXT("guard"), TEXT("a charge's landing is never parried"));
        return A.Damage > 0 || K.Fail(TEXT("damage"), TEXT("a charge must hurt"));
    }
    case ESoraBossAttackKind::Area:
    {
        int32 Arc = 0;
        if (!K.Only(S, {TEXT("radius_cm"), TEXT("inner_radius_cm"), TEXT("edge_damage"), TEXT("arc_deg"), TEXT("hits"), TEXT("gap_ms"),
                TEXT("knockback_cm"), TEXT("hero_stagger_ms"), TEXT("guard"), TEXT("opens"), TEXT("opens_ms")}) ||
            !K.Int(S, TEXT("radius_cm"), A.RadiusCm, 50, 2000) || !K.Int(S, TEXT("inner_radius_cm"), A.InnerRadiusCm, 0, A.RadiusCm) ||
            !K.Int(S, TEXT("edge_damage"), A.EdgeDamage, 0, A.Damage) || !K.Int(S, TEXT("arc_deg"), Arc, 10, 360) ||
            !K.Int(S, TEXT("hits"), A.Hits, 1, 6) || !K.Int(S, TEXT("gap_ms"), A.GapMs, 0, 2000) ||
            !K.Int(S, TEXT("knockback_cm"), A.KnockbackCm, 0, 1000) || !K.Int(S, TEXT("hero_stagger_ms"), A.HeroStaggerMs, 0, 3000) ||
            !ReadGuard(K, S, A.Guard, A.Damage, A.Hits) || !K.Names(S, TEXT("opens"), Pending.Opens) ||
            !K.Int(S, TEXT("opens_ms"), A.OpensMs, 0, 10000))
            return false;
        A.ArcMilli = HalfArcMilli(Arc);
        if ((A.Hits > 1) != (A.GapMs > 0))
            return K.Fail(TEXT("gap_ms"), TEXT("a multi-hit area spaces its hits, and only it"));
        if (Pending.Opens.IsEmpty() != (A.OpensMs == 0))
            return K.Fail(TEXT("opens_ms"), TEXT("an area opens weak points for a while, or none"));
        if (A.Guard.bParry)
            return K.Fail(TEXT("guard"), TEXT("an area is never parried"));
        return A.Damage > 0 || K.Fail(TEXT("damage"), TEXT("an area must hurt"));
    }
    case ESoraBossAttackKind::Beam:
        if (!K.Only(S, {TEXT("width_cm"), TEXT("track_ms"), TEXT("sweep_deg"), TEXT("height_cm")}) ||
            !K.Int(S, TEXT("width_cm"), A.WidthCm, 20, 1000) || !K.Int(S, TEXT("track_ms"), A.TrackMs, 0, A.WindupMs) ||
            !K.Int(S, TEXT("sweep_deg"), A.SweepDegrees, 0, 360) || !K.Int(S, TEXT("height_cm"), A.HeightCm, 0, 500))
            return false;
        if (A.SweepDegrees > 0 && A.ActiveMs <= 0)
            return K.Fail(TEXT("sweep_deg"), TEXT("a sweeping beam sweeps over its active time"));
        return A.Damage > 0 || K.Fail(TEXT("damage"), TEXT("a beam must hurt"));
    case ESoraBossAttackKind::Volley:
        if (!K.Only(S, {TEXT("rounds"), TEXT("interval_ms"), TEXT("lock_cm"), TEXT("dash_cm")}) ||
            !K.Int(S, TEXT("rounds"), A.Rounds, 1, 12) || !K.Int(S, TEXT("interval_ms"), A.IntervalMs, 0, 2000) ||
            !K.Int(S, TEXT("lock_cm"), A.LockCm, 30, 500) || !K.Int(S, TEXT("dash_cm"), A.DashCm, 0, 1000))
            return false;
        if ((A.Rounds > 1) != (A.IntervalMs > 0) || A.ActiveMs != (A.Rounds - 1) * A.IntervalMs)
            return K.Fail(TEXT("interval_ms"), TEXT("a volley's rounds fill exactly its active time"));
        return A.Damage > 0 || K.Fail(TEXT("damage"), TEXT("a volley must hurt"));
    case ESoraBossAttackKind::Zone:
        if (!K.Only(S, {TEXT("at"), TEXT("anchor"), TEXT("count"), TEXT("spread_cm"), TEXT("radius_cm"), TEXT("arm_ms"), TEXT("life_ms"),
                TEXT("tick_ms"), TEXT("root_ms"), TEXT("stagger_ms"), TEXT("fragile"), TEXT("max_active"), TEXT("void"),
                TEXT("breaks_mantle")}) ||
            !K.Choice(S, TEXT("at"), ZoneAts, A.At) || !K.OptionalName(S, TEXT("anchor"), A.Anchor) ||
            !K.Int(S, TEXT("count"), A.Count, 0, 8) || !K.Int(S, TEXT("spread_cm"), A.SpreadCm, 0, 2000) ||
            !K.Int(S, TEXT("radius_cm"), A.RadiusCm, 50, 1000) || !K.Int(S, TEXT("arm_ms"), A.ArmMs, 0, 5000) ||
            !K.Int(S, TEXT("life_ms"), A.LifeMs, 0, LongestMs) || !K.Int(S, TEXT("tick_ms"), A.TickMs, 0, 5000) ||
            !K.Int(S, TEXT("root_ms"), A.RootMs, 0, 5000) || !K.Int(S, TEXT("stagger_ms"), A.StaggerMs, 0, 3000) ||
            !K.Flag(S, TEXT("fragile"), A.bFragile) || !K.Int(S, TEXT("max_active"), A.MaxActive, 0, 16) ||
            !K.Flag(S, TEXT("void"), A.bVoid) || !K.Flag(S, TEXT("breaks_mantle"), A.bBreaksMantle))
            return false;
        if ((A.At == ESoraZoneAt::Anchor || A.At == ESoraZoneAt::AnchorOrTarget) == A.Anchor.IsNone())
            return K.Fail(TEXT("anchor"), TEXT("a zone placed on arena anchors names their kind, and only it"));
        if (A.Count == 0 && A.At != ESoraZoneAt::Anchor)
            return K.Fail(TEXT("count"), TEXT("only anchor zones may cover every anchor (count 0)"));
        if ((A.At == ESoraZoneAt::AroundTarget) != (A.SpreadCm > 0))
            return K.Fail(TEXT("spread_cm"), TEXT("zones around the target spread, and only they"));
        if ((A.TickMs > 0) && A.LifeMs == 0)
            return K.Fail(TEXT("tick_ms"), TEXT("only a lasting zone strikes again"));
        if (A.Damage == 0 && A.RootMs == 0)
            return K.Fail(TEXT("damage"), TEXT("a zone hurts or holds"));
        return true;
    case ESoraBossAttackKind::Summon:
        if (!K.Only(S, {TEXT("group")}) || !K.Name(S, TEXT("group"), Pending.Group))
            return false;
        return A.Damage == 0 || K.Fail(TEXT("damage"), TEXT("a summon does no damage itself"));
    case ESoraBossAttackKind::Pulse:
        if (!K.Only(S, {TEXT("radius_cm"), TEXT("expand_ms"), TEXT("reveal_cm_s")}) ||
            !K.Int(S, TEXT("radius_cm"), A.RadiusCm, 100, 5000) || !K.Int(S, TEXT("expand_ms"), A.ExpandMs, 0, 5000) ||
            !K.Int(S, TEXT("reveal_cm_s"), A.RevealCmPerSecond, 0, 2000))
            return false;
        if (!bBlind)
            return K.Fail(TEXT("pulse"), TEXT("only a blind hunter pulses"));
        return A.Damage == 0 || K.Fail(TEXT("damage"), TEXT("a pulse reveals and never hurts"));
    case ESoraBossAttackKind::Expose:
        if (!K.Only(S, {TEXT("opens"), TEXT("rotate"), TEXT("barrier_offline"), TEXT("interrupt_damage"), TEXT("interrupt_stagger_ms"),
                TEXT("event"), TEXT("event_limit")}) ||
            !K.Names(S, TEXT("opens"), Pending.Opens) || !K.Flag(S, TEXT("rotate"), A.bRotate) ||
            !K.Flag(S, TEXT("barrier_offline"), A.bBarrierOffline) || !K.Int(S, TEXT("interrupt_damage"), A.InterruptDamage, 0, 5000) ||
            !K.Int(S, TEXT("interrupt_stagger_ms"), A.InterruptStaggerMs, 0, 5000) || !K.OptionalName(S, TEXT("event"), A.Event) ||
            !K.Int(S, TEXT("event_limit"), A.EventLimit, 0, 10))
            return false;
        A.OpensMs = A.ActiveMs;
        if (A.ActiveMs <= 0 || (Pending.Opens.IsEmpty() && !A.bBarrierOffline))
            return K.Fail(TEXT("opens"), TEXT("an exposing act opens a weak point or drops the barrier for a while"));
        if ((A.InterruptDamage > 0) != (A.InterruptStaggerMs > 0) || (A.EventLimit > 0 && A.Event.IsNone()))
            return K.Fail(TEXT("interrupt_damage"), TEXT("an interrupt staggers; a limit counts a named event"));
        return A.Damage == 0 || K.Fail(TEXT("damage"), TEXT("an exposing act does no damage itself"));
    case ESoraBossAttackKind::Step:
        if (!K.Only(S, {TEXT("lunge_cm")}) || !K.Int(S, TEXT("lunge_cm"), A.LungeCm, 10, 1000))
            return false;
        return A.Damage == 0 || K.Fail(TEXT("damage"), TEXT("a pressing step does no damage"));
    }
    return false;
}

bool Resolve(const FReader& R, const FSoraBossData& D, FName Id, int32& Out, const TCHAR* Field)
{
    Out = D.AttackIndex(Id);
    return Out != INDEX_NONE || R.Fail(Field, TEXT("names no attack of this boss"));
}

bool ReadOverrides(const FReader& R, const FJsonObject& O, const TCHAR* Field, const FSoraBossData& D, TArray<FSoraBossOverride>& Out)
{
    TSharedPtr<FJsonObject> Map;
    if (!R.Object(O, Field, Map))
        return false;
    for (const auto& Pair : Map->Values)
    {
        FSoraBossOverride& Row = Out.AddDefaulted_GetRef();
        const FString Key(*Pair.Key);
        const TSharedPtr<FJsonObject> Entry = Pair.Value->AsObject();
        const FReader In{R.Error, R.File, R.Where + TEXT(".") + Field + TEXT(".") + Key};
        if (!Resolve(R, D, FName(*Key), Row.Attack, Field))
            return false;
        if (!Entry.IsValid())
            return In.Fail(TEXT("row"), TEXT("not an object"));
        if (!In.Only(*Entry, {TEXT("windup_ms"), TEXT("active_ms"), TEXT("recovery_ms"), TEXT("cooldown_ms"), TEXT("reach_cm"), TEXT("root_ms")}))
            return false;
        if (Entry->Values.IsEmpty())
            return In.Fail(TEXT("row"), TEXT("changes nothing"));
        const auto Optional = [&](const TCHAR* Name, int32& Value, int32 Low, int32 High)
        {
            return !Entry->HasField(Name) || In.Int(*Entry, Name, Value, Low, High);
        };
        if (!Optional(TEXT("windup_ms"), Row.WindupMs, 0, 5000) || !Optional(TEXT("active_ms"), Row.ActiveMs, 0, LongestMs) ||
            !Optional(TEXT("recovery_ms"), Row.RecoveryMs, 0, 10000) || !Optional(TEXT("cooldown_ms"), Row.CooldownMs, 0, 120000) ||
            !Optional(TEXT("reach_cm"), Row.MaxRangeCm, 1, FarthestCm) || !Optional(TEXT("root_ms"), Row.RootMs, 0, 5000))
            return false;
        const FSoraBossAttack& A = D.Attacks[Row.Attack];
        if (Row.MaxRangeCm >= 0 && Row.MaxRangeCm <= A.MinRangeCm)
            return In.Fail(TEXT("reach_cm"), TEXT("must stay beyond the attack's minimum range"));
    }
    return true;
}

bool ReadAtHealth(const FReader& R, const FJsonObject& O, const TCHAR* Field, const FSoraBossData& D, TArray<FSoraBossAtHealth>& Out)
{
    const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
    if (!R.Array(O, Field, Rows))
        return false;
    for (const TSharedPtr<FJsonValue>& Value : *Rows)
    {
        const TSharedPtr<FJsonObject> Row = Value->AsObject();
        FName Attack;
        FSoraBossAtHealth& Entry = Out.AddDefaulted_GetRef();
        if (!Row.IsValid() || !R.Only(*Row, {TEXT("attack"), TEXT("at_permille")}) || !R.Name(*Row, TEXT("attack"), Attack) ||
            !Resolve(R, D, Attack, Entry.Attack, Field) || !R.Int(*Row, TEXT("at_permille"), Entry.AtPermille, 1, 1000))
            return Row.IsValid() ? false : R.Fail(Field, TEXT("rows must be objects"));
    }
    return true;
}

bool ReadAttacks(const FReader& R, const FJsonObject& O, const TCHAR* Field, const FSoraBossData& D, TArray<int32>& Out)
{
    TArray<FName> Ids;
    if (!R.Names(O, Field, Ids))
        return false;
    for (const FName Id : Ids)
        if (!Resolve(R, D, Id, Out.AddDefaulted_GetRef(), Field))
            return false;
    return true;
}

bool ReadPattern(const FReader& R, const FJsonObject& O, const FSoraBossData& D, FSoraBossPhase& P)
{
    FName Fallback;
    const TArray<TSharedPtr<FJsonValue>>* Habits = nullptr;
    if (!R.Only(O, {TEXT("mode"), TEXT("attacks"), TEXT("beat_ms"), TEXT("measure"), TEXT("pause_ms"), TEXT("cadence_ms"), TEXT("gap_ms"),
            TEXT("fallback"), TEXT("loop_from"), TEXT("habits"), TEXT("easy_halved")}) ||
        !R.Choice(O, TEXT("mode"), Patterns, P.Pattern) || !ReadAttacks(R, O, TEXT("attacks"), D, P.Order) ||
        !R.Int(O, TEXT("beat_ms"), P.BeatMs, 0, 5000) || !R.Int(O, TEXT("measure"), P.Measure, 0, 8) ||
        !R.Int(O, TEXT("pause_ms"), P.PauseMs, 0, 5000) || !R.Ints(O, TEXT("cadence_ms"), P.CadenceMs, 100, 20000) ||
        !R.Ints(O, TEXT("gap_ms"), P.GapMs, 0, 20000) || !R.OptionalName(O, TEXT("fallback"), Fallback) ||
        !R.Int(O, TEXT("loop_from"), P.LoopFrom, 0, 32) || !R.Array(O, TEXT("habits"), Habits) ||
        !ReadAttacks(R, O, TEXT("easy_halved"), D, P.EasyHalved))
        return false;
    if (!Fallback.IsNone() && !Resolve(R, D, Fallback, P.Fallback, TEXT("fallback")))
        return false;
    if ((P.BeatMs > 0) != (P.Measure > 0) || (P.PauseMs > 0 && P.Measure == 0))
        return R.Fail(TEXT("beat_ms"), TEXT("a metronome counts measures, and only it pauses between them"));
    if (P.Pattern == ESoraBossPattern::Weighted)
    {
        if (!P.Order.IsEmpty() || Habits->IsEmpty() || P.BeatMs > 0 || !P.CadenceMs.IsEmpty() || !P.GapMs.IsEmpty() || P.Fallback != INDEX_NONE)
            return R.Fail(TEXT("mode"), TEXT("a weighted pattern lives in its habits"));
        for (int32 Index = 0; Index < Habits->Num(); ++Index)
        {
            const TSharedPtr<FJsonObject> Row = (*Habits)[Index]->AsObject();
            const FReader In{R.Error, R.File, FString::Printf(TEXT("%s.habits[%d]"), *R.Where, Index)};
            FSoraBossHabit& Habit = P.Habits.AddDefaulted_GetRef();
            TSharedPtr<FJsonObject> Weights;
            const TArray<TSharedPtr<FJsonValue>>* Interval = nullptr;
            if (!Row.IsValid() || !In.Only(*Row, {TEXT("lead"), TEXT("interval_ms"), TEXT("recovery_bonus_ms"), TEXT("weights")}) ||
                !In.Int(*Row, TEXT("lead"), Habit.Lead, 0, 2) || !In.Array(*Row, TEXT("interval_ms"), Interval) ||
                !In.Int(*Row, TEXT("recovery_bonus_ms"), Habit.RecoveryBonusMs, 0, 1000) || !In.Object(*Row, TEXT("weights"), Weights))
                return Row.IsValid() ? false : In.Fail(TEXT("row"), TEXT("not an object"));
            double Low = 0.0, High = 0.0;
            if (Interval->Num() != 2 || !(*Interval)[0]->TryGetNumber(Low) || !(*Interval)[1]->TryGetNumber(High) || Low < 200 ||
                High < Low || High > 10000 || Low != FMath::FloorToDouble(Low) || High != FMath::FloorToDouble(High))
                return In.Fail(TEXT("interval_ms"), TEXT("must be [shortest, longest] milliseconds"));
            Habit.MinIntervalMs = static_cast<int32>(Low);
            Habit.MaxIntervalMs = static_cast<int32>(High);
            if (Habit.Lead != Index)
                return In.Fail(TEXT("lead"), TEXT("habits list leads 0, 1 and 2 in order"));
            for (const auto& Pair : Weights->Values)
            {
                int32 Attack = INDEX_NONE, Weight = 0;
                if (!Resolve(In, D, FName(*FString(*Pair.Key)), Attack, TEXT("weights")) ||
                    !In.Int(*Weights, *FString(*Pair.Key), Weight, 1, 100))
                    return false;
                Habit.Attacks.Add(Attack);
                Habit.Weights.Add(Weight);
            }
            if (Habit.Attacks.IsEmpty() || Habit.Attacks.Num() > SoraBossRules::MaxWeighted)
                return In.Fail(TEXT("weights"), TEXT("weighs one to eight attacks"));
        }
        return true;
    }
    if (P.Order.IsEmpty() || !Habits->IsEmpty() || !P.EasyHalved.IsEmpty())
        return R.Fail(TEXT("attacks"), TEXT("a sequence or priority lists its attacks, and has no habits"));
    if (!P.CadenceMs.IsEmpty() && (P.CadenceMs.Num() != P.Order.Num() || P.Pattern != ESoraBossPattern::Sequence))
        return R.Fail(TEXT("cadence_ms"), TEXT("a sequence's cadence gives one start-to-start time per step"));
    if (P.BeatMs > 0 && (P.Pattern != ESoraBossPattern::Sequence || P.Order.Num() % P.Measure != 0 || !P.CadenceMs.IsEmpty()))
        return R.Fail(TEXT("measure"), TEXT("a metronome runs a sequence of whole measures"));
    if (P.LoopFrom >= P.Order.Num() || (P.LoopFrom > 0 && P.Pattern != ESoraBossPattern::Sequence))
        return R.Fail(TEXT("loop_from"), TEXT("a sequence loops back to one of its own steps"));
    return true;
}

bool ReadPhase(const FReader& R, const FJsonObject& O, const FSoraBossData& D, FSoraBossPhase& P)
{
    TSharedPtr<FJsonObject> Move, Pattern, AtFloor, Late;
    FName Ward, ShieldWhile;
    const TArray<TSharedPtr<FJsonValue>>* Concurrent = nullptr;
    if (!R.Only(O, {TEXT("table"), TEXT("from_permille"), TEXT("bark"), TEXT("move"), TEXT("pattern"), TEXT("reactions"), TEXT("concurrent"),
            TEXT("on_enter"), TEXT("summons"), TEXT("once_below"), TEXT("at_floor"), TEXT("ward"), TEXT("shield"), TEXT("barrier"),
            TEXT("mantle"), TEXT("shield_while_adds"), TEXT("floor_permille"), TEXT("hearing_permille"), TEXT("overrides"), TEXT("late")}) ||
        !R.Name(O, TEXT("table"), P.Table) || !R.Int(O, TEXT("from_permille"), P.FromPermille, 1, 1000) ||
        !R.Line(O, TEXT("bark"), P.Bark) || !R.Object(O, TEXT("move"), Move) || !R.Object(O, TEXT("pattern"), Pattern) ||
        !ReadAttacks(R, O, TEXT("reactions"), D, P.Reactions) || !R.Array(O, TEXT("concurrent"), Concurrent) ||
        !ReadAttacks(R, O, TEXT("on_enter"), D, P.OnEnter) || !ReadAtHealth(R, O, TEXT("summons"), D, P.Summons) ||
        !ReadAtHealth(R, O, TEXT("once_below"), D, P.OnceBelow) || !R.OptionalObject(O, TEXT("at_floor"), AtFloor) ||
        !R.OptionalName(O, TEXT("ward"), Ward) || !R.Flag(O, TEXT("shield"), P.bShield) || !R.Flag(O, TEXT("barrier"), P.bBarrier) ||
        !R.Flag(O, TEXT("mantle"), P.bMantle) || !R.OptionalName(O, TEXT("shield_while_adds"), ShieldWhile) ||
        !R.Int(O, TEXT("floor_permille"), P.FloorPermille, 0, 999) || !R.Int(O, TEXT("hearing_permille"), P.HearingPermille, 100, 5000) ||
        !ReadOverrides(R, O, TEXT("overrides"), D, P.Overrides) || !R.OptionalObject(O, TEXT("late"), Late))
        return false;
    const FReader MoveReader{R.Error, R.File, R.Where + TEXT(".move")};
    if (!MoveReader.Only(*Move, {TEXT("mode"), TEXT("speed_cm_s"), TEXT("turn_deg_s"), TEXT("near_cm"), TEXT("far_cm"), TEXT("engage_cm")}) ||
        !MoveReader.Choice(*Move, TEXT("mode"), Moves, P.Move) ||
        !MoveReader.Int(*Move, TEXT("speed_cm_s"), P.SpeedCmPerSecond, 0, 1200) ||
        !MoveReader.Int(*Move, TEXT("turn_deg_s"), P.TurnDegreesPerSecond, 10, 720) ||
        !MoveReader.Int(*Move, TEXT("near_cm"), P.NearCm, 0, 5000) || !MoveReader.Int(*Move, TEXT("far_cm"), P.FarCm, 0, 10000) ||
        !MoveReader.Int(*Move, TEXT("engage_cm"), P.EngageCm, 100, FarthestCm))
        return false;
    if ((P.Move == ESoraBossMove::Keep) != (P.FarCm > P.NearCm) || (P.Move == ESoraBossMove::Hold) != (P.SpeedCmPerSecond == 0))
        return MoveReader.Fail(TEXT("mode"), TEXT("keeping names a band, and only holding stands still"));
    if ((P.Move == ESoraBossMove::Hunt) != D.bBlind)
        return MoveReader.Fail(TEXT("mode"), TEXT("a blind hunter hunts, and only it"));
    if (!ReadPattern(FReader{R.Error, R.File, R.Where + TEXT(".pattern")}, *Pattern, D, P))
        return false;
    for (int32 Index = 0; Index < Concurrent->Num(); ++Index)
    {
        const TSharedPtr<FJsonObject> Row = (*Concurrent)[Index]->AsObject();
        const FReader In{R.Error, R.File, FString::Printf(TEXT("%s.concurrent[%d]"), *R.Where, Index)};
        FSoraBossTimed& Timed = P.Concurrent.AddDefaulted_GetRef();
        FName Attack;
        if (!Row.IsValid() || !In.Only(*Row, {TEXT("attack"), TEXT("every_ms"), TEXT("first_ms")}) || !In.Name(*Row, TEXT("attack"), Attack) ||
            !Resolve(In, D, Attack, Timed.Attack, TEXT("attack")) || !In.Int(*Row, TEXT("every_ms"), Timed.EveryMs, 1000, 120000) ||
            !In.Int(*Row, TEXT("first_ms"), Timed.FirstMs, 0, 120000))
            return Row.IsValid() ? false : In.Fail(TEXT("row"), TEXT("not an object"));
    }
    if (AtFloor.IsValid())
    {
        const FReader In{R.Error, R.File, R.Where + TEXT(".at_floor")};
        FName Attack;
        if (!In.Only(*AtFloor, {TEXT("attack"), TEXT("every_ms")}) || !In.Name(*AtFloor, TEXT("attack"), Attack) ||
            !Resolve(In, D, Attack, P.AtFloorAttack, TEXT("attack")) || !In.Int(*AtFloor, TEXT("every_ms"), P.AtFloorEveryMs, 1000, 60000))
            return false;
        if (P.FloorPermille == 0 && D.FloorPermille == 0)
            return In.Fail(TEXT("attack"), TEXT("only a fight with a floor repeats an attack there"));
    }
    if (Late.IsValid())
    {
        const FReader In{R.Error, R.File, R.Where + TEXT(".late")};
        if (!In.Only(*Late, {TEXT("below_permille"), TEXT("overrides")}) ||
            !In.Int(*Late, TEXT("below_permille"), P.LateBelowPermille, 1, P.FromPermille - 1) ||
            !ReadOverrides(In, *Late, TEXT("overrides"), D, P.Late))
            return false;
    }
    if (!Ward.IsNone())
    {
        P.Ward = D.Wards.IndexOfByPredicate([Ward](const FSoraBossWard& W) { return W.Id == Ward; });
        if (P.Ward == INDEX_NONE)
            return R.Fail(TEXT("ward"), TEXT("names no ward of this boss"));
    }
    if (!ShieldWhile.IsNone())
    {
        P.ShieldWhileAdds = D.Adds.IndexOfByPredicate([ShieldWhile](const FSoraBossAddGroup& G) { return G.Id == ShieldWhile; });
        if (P.ShieldWhileAdds == INDEX_NONE)
            return R.Fail(TEXT("shield_while_adds"), TEXT("names no add group of this boss"));
    }
    if ((P.bShield && !D.bShield) || (P.bBarrier && !D.bBarrier) || (P.bMantle && !D.bMantle))
        return R.Fail(TEXT("shield"), TEXT("a phase raises only the defenses its boss has"));
    for (const FSoraBossAtHealth& Row : P.Summons)
        if (D.Attacks[Row.Attack].Kind != ESoraBossAttackKind::Summon || Row.AtPermille > P.FromPermille)
            return R.Fail(TEXT("summons"), TEXT("summons call adds at or below the phase's start"));
    for (const FSoraBossAtHealth& Row : P.OnceBelow)
        if (Row.AtPermille >= P.FromPermille)
            return R.Fail(TEXT("once_below"), TEXT("must fall inside the phase"));
    return true;
}

bool ReadBoss(FString& Error, const FJsonObject& O, int32 Index, bool bDuel, FSoraBossData& D)
{
    FReader R{Error, BossesFile, FString::Printf(TEXT("%s[%d]"), bDuel ? TEXT("duels") : TEXT("bosses"), Index)};
    if (!R.Name(O, TEXT("id"), D.Id))
        return false;
    R.Where = D.Id.ToString();
    D.bDuel = bDuel;
    TSharedPtr<FJsonObject> Health, Hearing, Shield, Barrier, Mantle;
    const TArray<TSharedPtr<FJsonValue>>* Rows[6] = {};
    bool bFinisher = false, bHearing = false;
    int32 Deflect = 0;
    if (!R.Only(O, {TEXT("id"), TEXT("chapter"), TEXT("beat"), TEXT("opponent"), TEXT("name_ja"), TEXT("reading"), TEXT("name_en"),
            TEXT("style_ja"), TEXT("style_en"), TEXT("body"), TEXT("held_weapon"), TEXT("sparring_weapon"), TEXT("scale_permille"),
            TEXT("health"), TEXT("lethal"), TEXT("defeat"), TEXT("finisher"), TEXT("floor_permille"), TEXT("poise_ms"), TEXT("rear_permille"),
            TEXT("flank_permille"), TEXT("body_permille"), TEXT("arena_radius_cm"), TEXT("transition_ms"), TEXT("telegraph_min_ms"),
            TEXT("deflect_idle_front_deg"), TEXT("front_blocked_hint"), TEXT("senses"), TEXT("hearing"), TEXT("shield"), TEXT("barrier"),
            TEXT("mantle"), TEXT("weak_points"), TEXT("wards"), TEXT("adds"), TEXT("barks"), TEXT("phases"), TEXT("attacks")}) ||
        !R.Int(O, TEXT("chapter"), D.Chapter, 1, 8) || !R.Text(O, TEXT("beat"), D.Beat) || !R.Name(O, TEXT("opponent"), D.Opponent) ||
        !R.Text(O, TEXT("name_ja"), D.NameJapanese) || !R.Text(O, TEXT("reading"), D.Reading) ||
        !R.Text(O, TEXT("name_en"), D.NameEnglish) || !R.Text(O, TEXT("style_ja"), D.StyleJapanese) ||
        !R.Text(O, TEXT("style_en"), D.StyleEnglish) || !R.Choice(O, TEXT("body"), Bodies, D.Body) ||
        !R.Int(O, TEXT("held_weapon"), D.HeldWeapon, 0, 20) || !R.Flag(O, TEXT("sparring_weapon"), D.bSparringWeapon) ||
        !R.Int(O, TEXT("scale_permille"), D.ScalePermille, 500, 6000) || !R.Object(O, TEXT("health"), Health) ||
        !R.Int(*Health, TEXT("easy"), D.Health[0], 100, 20000) || !R.Int(*Health, TEXT("normal"), D.Health[1], 100, 20000) ||
        !R.Int(*Health, TEXT("hard"), D.Health[2], 100, 20000) || !R.Flag(O, TEXT("lethal"), D.bLethal) ||
        !R.Choice(O, TEXT("defeat"), Defeats, D.Defeat) || !R.Choice(O, TEXT("finisher"), Finishers, bFinisher) ||
        !R.Int(O, TEXT("floor_permille"), D.FloorPermille, 0, 999) || !R.Int(O, TEXT("poise_ms"), D.PoiseMs, 0, 10000) ||
        !R.Int(O, TEXT("rear_permille"), D.RearPermille, 1000, 3000) || !R.Int(O, TEXT("flank_permille"), D.FlankPermille, 1000, 3000) ||
        !R.Int(O, TEXT("body_permille"), D.BodyPermille, 0, 1000) || !R.Int(O, TEXT("arena_radius_cm"), D.ArenaRadiusCm, 400, 10000) ||
        !R.Int(O, TEXT("transition_ms"), D.TransitionMs, 0, 5000) || !R.Int(O, TEXT("telegraph_min_ms"), D.TelegraphMinMs, 300, 1500) ||
        !R.Int(O, TEXT("deflect_idle_front_deg"), Deflect, 0, 180) || !R.Int(O, TEXT("front_blocked_hint"), D.FrontBlockedHint, 0, 20) ||
        !R.Choice(O, TEXT("senses"), Senses, bHearing) || !R.OptionalObject(O, TEXT("hearing"), Hearing) ||
        !R.OptionalObject(O, TEXT("shield"), Shield) || !R.OptionalObject(O, TEXT("barrier"), Barrier) ||
        !R.OptionalObject(O, TEXT("mantle"), Mantle) || !R.Array(O, TEXT("weak_points"), Rows[0]) || !R.Array(O, TEXT("wards"), Rows[1]) ||
        !R.Array(O, TEXT("adds"), Rows[2]) || !R.Array(O, TEXT("barks"), Rows[3]) || !R.Array(O, TEXT("phases"), Rows[4]) ||
        !R.Array(O, TEXT("attacks"), Rows[5]))
        return false;
    D.bMutoFinisher = bFinisher;
    D.bBlind = bHearing;
    D.DeflectHalfArcMilli = Deflect > 0 ? HalfArcMilli(Deflect) : 1000;
    if (bDuel == (D.Opponent == D.Id) || (!bDuel && !D.Id.ToString().StartsWith(TEXT("boss_"))) ||
        (bDuel && !D.Id.ToString().StartsWith(TEXT("duel_"))))
        return R.Fail(TEXT("opponent"), TEXT("a boss is its own opponent; a duel_ names the chapter's duellist"));
    if (D.bMutoFinisher && D.Defeat != ESoraBossDefeat::Disarm && D.Defeat != ESoraBossDefeat::Capture)
        return R.Fail(TEXT("finisher"), TEXT("mutō-dori ends only a fight that disarms or captures"));
    if (D.Defeat == ESoraBossDefeat::Points && (!bDuel || D.FloorPermille == 0 || D.bMutoFinisher))
        return R.Fail(TEXT("defeat"), TEXT("a points bout is a duel whose opponent keeps a floor"));
    if (D.FloorPermille > 0 && D.Defeat != ESoraBossDefeat::Points && !D.bMutoFinisher)
        return R.Fail(TEXT("floor_permille"), TEXT("only a points bout or a mutō-dori fight keeps a floor"));
    if ((D.Defeat == ESoraBossDefeat::DestroyWeakPoints) != (D.BodyPermille == 0))
        return R.Fail(TEXT("body_permille"), TEXT("an armoured body falls only by its weak points"));
    if (D.bLethal && D.Defeat != ESoraBossDefeat::Kill)
        return R.Fail(TEXT("lethal"), TEXT("only a kill is lethal"));
    for (const int32 Max : D.Health)
        if (Max * D.FloorPermille % 1000 != 0)
            return R.Fail(TEXT("health"), TEXT("health times the floor must be whole"));
    if (Hearing.IsValid() != D.bBlind)
        return R.Fail(TEXT("hearing"), TEXT("a hearing hunter lists what it hears, and only it"));
    if (Hearing.IsValid())
    {
        const FReader In{Error, BossesFile, R.Where + TEXT(".hearing")};
        FSoraBossHearing& H = D.Hearing;
        if (!In.Only(*Hearing, {TEXT("walk_cm"), TEXT("crouch_cm"), TEXT("sprint_cm"), TEXT("still_cm_s"), TEXT("noise_cm"), TEXT("fresh_ms")}) ||
            !In.Int(*Hearing, TEXT("walk_cm"), H.WalkCm, 100, 10000) || !In.Int(*Hearing, TEXT("crouch_cm"), H.CrouchCm, 0, H.WalkCm) ||
            !In.Int(*Hearing, TEXT("sprint_cm"), H.SprintCm, H.WalkCm, 20000) ||
            !In.Int(*Hearing, TEXT("still_cm_s"), H.StillCmPerSecond, 0, 300) || !In.Int(*Hearing, TEXT("noise_cm"), H.NoiseCm, 100, 20000) ||
            !In.Int(*Hearing, TEXT("fresh_ms"), H.FreshMs, 100, 10000))
            return false;
    }
    if (Shield.IsValid())
    {
        const FReader In{Error, BossesFile, R.Where + TEXT(".shield")};
        int32 Arc = 0;
        if (!In.Only(*Shield, {TEXT("arc_deg"), TEXT("break_weapon"), TEXT("break_hits")}) || !In.Int(*Shield, TEXT("arc_deg"), Arc, 30, 240) ||
            !In.Int(*Shield, TEXT("break_weapon"), D.ShieldBreakWeapon, 0, 20) || !In.Int(*Shield, TEXT("break_hits"), D.ShieldBreakHits, 1, 10))
            return false;
        D.bShield = true;
        D.ShieldHalfArcMilli = HalfArcMilli(Arc);
    }
    if (Barrier.IsValid())
    {
        const FReader In{Error, BossesFile, R.Where + TEXT(".barrier")};
        FSoraBossBarrier& B = D.Barrier;
        TSharedPtr<FJsonObject> Maps[2];
        if (!In.Only(*Barrier, {TEXT("health"), TEXT("regen_delay_ms"), TEXT("regen_per_s"), TEXT("melee_permille"), TEXT("weapon_permille"),
                TEXT("strip_permille")}) ||
            !In.Int(*Barrier, TEXT("health"), B.Health, 1, 5000) || !In.Int(*Barrier, TEXT("regen_delay_ms"), B.RegenDelayMs, 0, 60000) ||
            !In.Int(*Barrier, TEXT("regen_per_s"), B.RegenPerSecond, 0, 5000) || !In.Int(*Barrier, TEXT("melee_permille"), B.MeleePermille, 0, 10000) ||
            !In.Object(*Barrier, TEXT("weapon_permille"), Maps[0]) || !In.Object(*Barrier, TEXT("strip_permille"), Maps[1]))
            return false;
        for (int32 Map = 0; Map < 2; ++Map)
            for (const auto& Pair : Maps[Map]->Values)
            {
                const FString Key(*Pair.Key);
                const int32 WeaponId = Key.IsNumeric() ? FCString::Atoi(*Key) : -1;
                int32 Permille = 0;
                if (WeaponId < 0 || WeaponId > 20 || Key != FString::FromInt(WeaponId))
                    return In.Fail(Map ? TEXT("strip_permille") : TEXT("weapon_permille"), TEXT("keys must be catalog weapon ids"));
                if (!In.Int(*Maps[Map], *Key, Permille, 1, Map ? 1000 : 10000))
                    return false;
                (Map ? B.StripPermille : B.WeaponPermille).Add(WeaponId, Permille);
            }
        D.bBarrier = true;
    }
    if (Mantle.IsValid())
    {
        const FReader In{Error, BossesFile, R.Where + TEXT(".mantle")};
        if (!In.Only(*Mantle, {TEXT("taken_permille"), TEXT("down_ms")}) ||
            !In.Int(*Mantle, TEXT("taken_permille"), D.MantleTakenPermille, 0, 999) || !In.Int(*Mantle, TEXT("down_ms"), D.MantleDownMs, 500, 20000))
            return false;
        D.bMantle = true;
    }
    for (int32 Row = 0; Row < Rows[0]->Num(); ++Row)
    {
        const TSharedPtr<FJsonObject> O2 = (*Rows[0])[Row]->AsObject();
        const FReader In{Error, BossesFile, FString::Printf(TEXT("%s.weak_points[%d]"), *R.Where, Row)};
        FSoraBossWeakPoint& P = D.WeakPoints.AddDefaulted_GetRef();
        TArray<int32> Offset;
        FString Open;
        if (!O2.IsValid() || !In.Only(*O2, {TEXT("id"), TEXT("name_ja"), TEXT("name_en"), TEXT("health"), TEXT("offset_cm"), TEXT("radius_cm"),
                TEXT("melee_permille"), TEXT("ranged_permille"), TEXT("closed_permille"), TEXT("open")}) ||
            !In.Name(*O2, TEXT("id"), P.Id) || !In.Text(*O2, TEXT("name_ja"), P.NameJapanese) || !In.Text(*O2, TEXT("name_en"), P.NameEnglish) ||
            !In.Int(*O2, TEXT("health"), P.Health, 0, 10000) || !In.Ints(*O2, TEXT("offset_cm"), Offset, -2000, 2000) ||
            !In.Int(*O2, TEXT("radius_cm"), P.RadiusCm, 10, 400) || !In.Int(*O2, TEXT("melee_permille"), P.MeleePermille, 0, 5000) ||
            !In.Int(*O2, TEXT("ranged_permille"), P.RangedPermille, 0, 5000) || !In.Int(*O2, TEXT("closed_permille"), P.ClosedPermille, 0, 5000) ||
            !In.Text(*O2, TEXT("open"), Open))
            return O2.IsValid() ? false : In.Fail(TEXT("row"), TEXT("not an object"));
        if (Offset.Num() != 3 || (Open != TEXT("always") && Open != TEXT("exposed")))
            return In.Fail(TEXT("offset_cm"), TEXT("an offset is [forward, right, up]; a point is always or exposed open"));
        P.Offset = FVector(Offset[0], Offset[1], Offset[2]);
        P.bAlwaysOpen = Open == TEXT("always");
        if (IndexOf(D.WeakPoints, P.Id) != Row)
            return In.Fail(TEXT("id"), TEXT("duplicate weak point"));
    }
    for (int32 Row = 0; Row < Rows[1]->Num(); ++Row)
    {
        const TSharedPtr<FJsonObject> O2 = (*Rows[1])[Row]->AsObject();
        const FReader In{Error, BossesFile, FString::Printf(TEXT("%s.wards[%d]"), *R.Where, Row)};
        FSoraBossWard& W = D.Wards.AddDefaulted_GetRef();
        if (!O2.IsValid() || !In.Only(*O2, {TEXT("id"), TEXT("name_ja"), TEXT("name_en"), TEXT("count"), TEXT("health"), TEXT("orbit_cm"),
                TEXT("period_ms"), TEXT("closed_invulnerable"), TEXT("open_every_ms"), TEXT("open_ms"), TEXT("open_after_block"),
                TEXT("respawn_ms"), TEXT("broken_stun_ms"), TEXT("broken_taken_permille"), TEXT("bark")}) ||
            !In.Name(*O2, TEXT("id"), W.Id) || !In.Text(*O2, TEXT("name_ja"), W.NameJapanese) || !In.Text(*O2, TEXT("name_en"), W.NameEnglish) ||
            !In.Int(*O2, TEXT("count"), W.Count, 1, 8) || !In.Int(*O2, TEXT("health"), W.Health, 1, 2000) ||
            !In.Int(*O2, TEXT("orbit_cm"), W.OrbitCm, 50, 2000) || !In.Int(*O2, TEXT("period_ms"), W.PeriodMs, 500, 60000) ||
            !In.Flag(*O2, TEXT("closed_invulnerable"), W.bClosedInvulnerable) || !In.Int(*O2, TEXT("open_every_ms"), W.OpenEveryMs, 0, 60000) ||
            !In.Int(*O2, TEXT("open_ms"), W.OpenMs, 0, 10000) || !In.Flag(*O2, TEXT("open_after_block"), W.bOpenAfterBlock) ||
            !In.Int(*O2, TEXT("respawn_ms"), W.RespawnMs, 0, 120000) || !In.Int(*O2, TEXT("broken_stun_ms"), W.BrokenStunMs, 0, 10000) ||
            !In.Int(*O2, TEXT("broken_taken_permille"), W.BrokenTakenPermille, 1000, 3000) || !In.Line(*O2, TEXT("bark"), W.Bark))
            return O2.IsValid() ? false : In.Fail(TEXT("row"), TEXT("not an object"));
        if (W.bClosedInvulnerable && W.OpenMs == 0)
            return In.Fail(TEXT("open_ms"), TEXT("a ward invulnerable while closed must open"));
    }
    for (int32 Row = 0; Row < Rows[2]->Num(); ++Row)
    {
        const TSharedPtr<FJsonObject> O2 = (*Rows[2])[Row]->AsObject();
        const FReader In{Error, BossesFile, FString::Printf(TEXT("%s.adds[%d]"), *R.Where, Row)};
        FSoraBossAddGroup& G = D.Adds.AddDefaulted_GetRef();
        if (!O2.IsValid() || !In.Only(*O2, {TEXT("id"), TEXT("archetype"), TEXT("variant"), TEXT("count"), TEXT("max_alive"), TEXT("respawn_ms")}) ||
            !In.Name(*O2, TEXT("id"), G.Id) || !In.Name(*O2, TEXT("archetype"), G.Archetype) || !In.OptionalName(*O2, TEXT("variant"), G.Variant) ||
            !In.Int(*O2, TEXT("count"), G.Count, 1, 6) || !In.Int(*O2, TEXT("max_alive"), G.MaxAlive, G.Count, 8) ||
            !In.Int(*O2, TEXT("respawn_ms"), G.RespawnMs, 0, 120000))
            return O2.IsValid() ? false : In.Fail(TEXT("row"), TEXT("not an object"));
    }
    for (int32 Row = 0; Row < Rows[3]->Num(); ++Row)
    {
        const TSharedPtr<FJsonObject> O2 = (*Rows[3])[Row]->AsObject();
        const FReader In{Error, BossesFile, FString::Printf(TEXT("%s.barks[%d]"), *R.Where, Row)};
        FSoraBossBark& B = D.Barks.AddDefaulted_GetRef();
        int32 Event = 0;
        if (!O2.IsValid() || !In.Only(*O2, {TEXT("on"), TEXT("line"), TEXT("cooldown_ms")}) || !In.Choice(*O2, TEXT("on"), BarkEvents, Event) ||
            !In.Line(*O2, TEXT("line"), B.Line) || !In.Int(*O2, TEXT("cooldown_ms"), B.CooldownMs, 0, 120000))
            return O2.IsValid() ? false : In.Fail(TEXT("row"), TEXT("not an object"));
        B.Event = BarkEvents[Event];
        if (B.Line.IsNone())
            return In.Fail(TEXT("line"), TEXT("a bark names its line"));
    }
    // Attacks first, so phases and feints can name them.
    TArray<FPendingAttack> Pending;
    for (int32 Row = 0; Row < Rows[5]->Num(); ++Row)
    {
        const TSharedPtr<FJsonObject> O2 = (*Rows[5])[Row]->AsObject();
        const FReader In{Error, BossesFile, FString::Printf(TEXT("%s.attacks[%d]"), *R.Where, Row)};
        if (!O2.IsValid())
            return In.Fail(TEXT("row"), TEXT("not an object"));
        FSoraBossAttack& A = D.Attacks.AddDefaulted_GetRef();
        if (!ReadAttack(FReader{Error, BossesFile, R.Where + TEXT(".attacks")}, *O2, A, Pending.AddDefaulted_GetRef(), D.bBlind))
            return false;
        if (D.AttackIndex(A.Id) != Row)
            return In.Fail(TEXT("id"), TEXT("duplicate attack"));
    }
    for (int32 Row = 0; Row < D.Attacks.Num(); ++Row)
    {
        FSoraBossAttack& A = D.Attacks[Row];
        const FReader In{Error, BossesFile, R.Where + TEXT(".attacks.") + A.Id.ToString()};
        if (!Pending[Row].Then.IsNone())
        {
            A.Then = D.AttackIndex(Pending[Row].Then);
            if (A.Then == INDEX_NONE || !D.Attacks[A.Then].IsBlow())
                return In.Fail(TEXT("then"), TEXT("a feint turns into one of its boss's blows"));
        }
        for (const FName Point : Pending[Row].Opens)
        {
            const int32 Found = IndexOf(D.WeakPoints, Point);
            if (Found == INDEX_NONE || D.WeakPoints[Found].bAlwaysOpen)
                return In.Fail(TEXT("opens"), TEXT("opens only this boss's closed weak points"));
            A.Opens.Add(Found);
        }
        if (!Pending[Row].Group.IsNone())
        {
            A.Group = D.Adds.IndexOfByPredicate([&](const FSoraBossAddGroup& G) { return G.Id == Pending[Row].Group; });
            if (A.Group == INDEX_NONE)
                return In.Fail(TEXT("group"), TEXT("names no add group of this boss"));
        }
        if (A.Hurts() && A.WindupMs < D.TelegraphMinMs)
            return In.Fail(TEXT("windup_ms"), TEXT("every blow's telegraph meets the fight's floor"));
        if (A.bMuto && !D.bMutoFinisher)
            return In.Fail(TEXT("muto"), TEXT("mutō-dori appears only in fights it may end"));
    }
    int32 Previous = 1001;
    for (int32 Row = 0; Row < Rows[4]->Num(); ++Row)
    {
        const TSharedPtr<FJsonObject> O2 = (*Rows[4])[Row]->AsObject();
        const FReader In{Error, BossesFile, FString::Printf(TEXT("%s.phases[%d]"), *R.Where, Row)};
        if (!O2.IsValid())
            return In.Fail(TEXT("row"), TEXT("not an object"));
        FSoraBossPhase& P = D.Phases.AddDefaulted_GetRef();
        if (!ReadPhase(In, *O2, D, P))
            return false;
        if (P.FromPermille >= Previous || (Row == 0) != (P.FromPermille == 1000) || P.FromPermille <= D.FloorPermille)
            return In.Fail(TEXT("from_permille"), TEXT("phases start at 1000 and descend above the floor"));
        for (const int32 Max : D.Health)
            if (Max * P.FromPermille % 1000 != 0 || Max * P.FloorPermille % 1000 != 0)
                return In.Fail(TEXT("from_permille"), TEXT("health times each phase start and floor must be whole"));
        Previous = P.FromPermille;
    }
    if (D.Phases.IsEmpty() || D.Phases.Num() > SoraBossRules::MaxPhases)
        return R.Fail(TEXT("phases"), TEXT("one to four phases"));
    // Every attack is reachable from some phase.
    TArray<bool> Used;
    Used.Init(false, D.Attacks.Num());
    for (const FSoraBossPhase& P : D.Phases)
    {
        for (const int32 A : P.Order) Used[A] = true;
        for (const int32 A : P.Reactions) Used[A] = true;
        for (const int32 A : P.OnEnter) Used[A] = true;
        for (const FSoraBossTimed& T : P.Concurrent) Used[T.Attack] = true;
        for (const FSoraBossAtHealth& S : P.Summons) Used[S.Attack] = true;
        for (const FSoraBossAtHealth& S : P.OnceBelow) Used[S.Attack] = true;
        for (const FSoraBossHabit& H : P.Habits) for (const int32 A : H.Attacks) Used[A] = true;
        if (P.Fallback != INDEX_NONE) Used[P.Fallback] = true;
        if (P.AtFloorAttack != INDEX_NONE) Used[P.AtFloorAttack] = true;
    }
    for (int32 Pass = 0; Pass < 2; ++Pass)
        for (const FSoraBossAttack& A : D.Attacks)
            if (A.Then != INDEX_NONE && Used[D.AttackIndex(A.Id)])
                Used[A.Then] = true;
    for (int32 Row = 0; Row < D.Attacks.Num(); ++Row)
        if (!Used[Row])
            return R.Fail(TEXT("attacks"), *FString::Printf(TEXT("%s is in no phase"), *D.Attacks[Row].Id.ToString()));
    return true;
}
} // namespace SoraBossLoader

int32 FSoraBossData::AttackIndex(FName AttackId) const
{
    return Attacks.IndexOfByPredicate([AttackId](const FSoraBossAttack& A) { return A.Id == AttackId; });
}

const FSoraBossBark* FSoraBossData::BarkFor(FName Event) const
{
    return Barks.FindByPredicate([Event](const FSoraBossBark& B) { return B.Event == Event; });
}

FSoraBossCatalog& FSoraBossCatalog::Get()
{
    static FSoraBossCatalog Catalog;
    return Catalog;
}

const FSoraBossData* FSoraBossCatalog::Find(FName Id) const
{
    if (!bReady)
        return nullptr;
    if (const FSoraBossData* Boss = BossEntries.FindByPredicate([Id](const FSoraBossData& D) { return D.Id == Id; }))
        return Boss;
    return DuelEntries.FindByPredicate([Id](const FSoraBossData& D) { return D.Id == Id; });
}

const FSoraBossData* FSoraBossCatalog::ForBeat(const FString& Beat) const
{
    if (!bReady)
        return nullptr;
    if (const FSoraBossData* Boss = BossEntries.FindByPredicate([&Beat](const FSoraBossData& D) { return D.Beat == Beat; }))
        return Boss;
    return DuelEntries.FindByPredicate([&Beat](const FSoraBossData& D) { return D.Beat == Beat; });
}

bool FSoraBossCatalog::Load()
{
    if (bReady)
        return true;
    BossEntries.Reset();
    DuelEntries.Reset();
    FString Text;
    TSharedPtr<FJsonObject> Root;
    const FString Path = FPaths::ProjectContentDir() / TEXT("Data/bosses.json");
    double Schema = 0.0;
    const TArray<TSharedPtr<FJsonValue>>* Lists[2] = {};
    TSharedPtr<FJsonObject> Difficulty;
    SoraBossLoader::FReader R{Error, SoraBossLoader::BossesFile, TEXT("root")};
    if (!FFileHelper::LoadFileToString(Text, *Path) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid())
        Error = TEXT("Cannot load Content/Data/bosses.json");
    else if (!Root->TryGetNumberField(TEXT("schema_version"), Schema) || Schema != 1)
        Error = TEXT("Unsupported bosses.json schema");
    else if (R.Only(*Root, {TEXT("schema_version"), TEXT("difficulty"), TEXT("bosses"), TEXT("duels")}) &&
        R.Object(*Root, TEXT("difficulty"), Difficulty) &&
        R.Only(*Difficulty, {TEXT("easy_windup_permille"), TEXT("hard_windup_permille")}) &&
        R.Int(*Difficulty, TEXT("easy_windup_permille"), EasyWindupPermille, 1000, 2000) &&
        R.Int(*Difficulty, TEXT("hard_windup_permille"), HardWindupPermille, 500, 1000) &&
        R.Array(*Root, TEXT("bosses"), Lists[0]) && R.Array(*Root, TEXT("duels"), Lists[1]))
    {
        // Pointers to entries stay valid for the program's life: the arrays
        // never grow after a successful load.
        bool bValid = true;
        for (int32 List = 0; bValid && List < 2; ++List)
        {
            TArray<FSoraBossData>& Entries = List ? DuelEntries : BossEntries;
            Entries.Reserve(Lists[List]->Num());
            for (int32 Index = 0; bValid && Index < Lists[List]->Num(); ++Index)
            {
                const TSharedPtr<FJsonObject> Row = (*Lists[List])[Index]->AsObject();
                FSoraBossData& Entry = Entries.AddDefaulted_GetRef();
                bValid = Row.IsValid() && SoraBossLoader::ReadBoss(Error, *Row, Index, List == 1, Entry);
                if (!Row.IsValid())
                    Error = FString::Printf(TEXT("bosses.json %s[%d] is not an object"), List ? TEXT("duels") : TEXT("bosses"), Index);
                int32 Seen = 0;
                for (const TArray<FSoraBossData>* Listed : {&BossEntries, &DuelEntries})
                    for (const FSoraBossData& Other : *Listed)
                        Seen += Other.Id == Entry.Id ? 1 : 0;
                if (bValid && Seen != 1)
                    bValid = R.Fail(Entry.Id.ToString(), TEXT("repeats an id"));
            }
        }
        if (bValid && (BossEntries.IsEmpty() || DuelEntries.IsEmpty()))
            bValid = R.Fail(TEXT("bosses"), TEXT("lists no bosses or no duels"));
        if (bValid)
        {
            Error.Reset();
            bReady = true;
            return true;
        }
        BossEntries.Reset();
        DuelEntries.Reset();
    }
    UE_LOG(LogTemp, Error, TEXT("%s"), *Error);
    return false;
}
