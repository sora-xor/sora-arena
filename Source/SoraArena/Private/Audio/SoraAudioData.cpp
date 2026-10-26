#include "Audio/SoraAudioData.h"
#include "SoraSettings.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace SoraAudioData
{
namespace
{
using FObject = TSharedPtr<FJsonObject>;
using FValues = TArray<TSharedPtr<FJsonValue>>;

// Required fields with their types; the first failure names its place.
struct FReader
{
    FString& Error;
    FString Where;
    bool Fail(const TCHAR* Field, const TCHAR* Problem) const
    {
        if (Error.IsEmpty())
            Error = FString::Printf(TEXT("audio.json %s.%s: %s"), *Where, Field, Problem);
        return false;
    }
    bool Object(const FJsonObject& O, const TCHAR* Field, FObject& Out) const
    {
        const FObject* Found = nullptr;
        if (!O.TryGetObjectField(Field, Found) || !Found || !Found->IsValid())
            return Fail(Field, TEXT("missing object"));
        Out = *Found;
        return true;
    }
    bool Array(const FJsonObject& O, const TCHAR* Field, const FValues*& Out) const
    {
        if (!O.TryGetArrayField(Field, Out) || !Out)
            return Fail(Field, TEXT("missing array"));
        return true;
    }
    bool Text(const FJsonObject& O, const TCHAR* Field, FString& Out) const
    {
        if (!O.TryGetStringField(Field, Out))
            return Fail(Field, TEXT("missing text"));
        return true;
    }
    bool Name(const FJsonObject& O, const TCHAR* Field, FName& Out) const
    {
        FString Value;
        if (!Text(O, Field, Value))
            return false;
        Out = Value.IsEmpty() ? NAME_None : FName(*Value);
        return true;
    }
    bool Number(const FJsonObject& O, const TCHAR* Field, float& Out) const
    {
        double Value = 0.0;
        if (!O.TryGetNumberField(Field, Value) || !FMath::IsFinite(Value))
            return Fail(Field, TEXT("missing number"));
        Out = static_cast<float>(Value);
        return true;
    }
    bool Int(const FJsonObject& O, const TCHAR* Field, int32& Out) const
    {
        double Value = 0.0;
        if (!O.TryGetNumberField(Field, Value) || Value != FMath::FloorToDouble(Value))
            return Fail(Field, TEXT("missing whole number"));
        Out = static_cast<int32>(Value);
        return true;
    }
    bool Flag(const FJsonObject& O, const TCHAR* Field, bool& Out) const
    {
        if (!O.TryGetBoolField(Field, Out))
            return Fail(Field, TEXT("missing true or false"));
        return true;
    }
    bool Pair(const FJsonObject& O, const TCHAR* Field, float (&Out)[2]) const
    {
        const FValues* Values = nullptr;
        if (!Array(O, Field, Values) || Values->Num() != 2)
            return Fail(Field, TEXT("needs two numbers"));
        for (int32 Index = 0; Index < 2; ++Index)
        {
            double Value = 0.0;
            if (!(*Values)[Index]->TryGetNumber(Value))
                return Fail(Field, TEXT("needs two numbers"));
            Out[Index] = static_cast<float>(Value);
        }
        return Out[0] <= Out[1] || Fail(Field, TEXT("range out of order"));
    }
    bool Strings(const FJsonObject& O, const TCHAR* Field, TArray<FString>& Out) const
    {
        const FValues* Values = nullptr;
        if (!Array(O, Field, Values))
            return false;
        for (const TSharedPtr<FJsonValue>& Value : *Values)
        {
            FString Text;
            if (!Value->TryGetString(Text) || Text.IsEmpty())
                return Fail(Field, TEXT("must list text"));
            Out.Add(Text);
        }
        return true;
    }
    bool Names(const FJsonObject& O, const TCHAR* Field, TArray<FName>& Out) const
    {
        TArray<FString> Texts;
        if (!Strings(O, Field, Texts))
            return false;
        for (const FString& Text : Texts)
            Out.Add(FName(*Text));
        return true;
    }
};

// A rule value as the facts spell it.
bool ValueText(const TSharedPtr<FJsonValue>& Value, FString& Out)
{
    switch (Value->Type)
    {
    case EJson::Boolean:
        Out = Value->AsBool() ? TEXT("true") : TEXT("false");
        return true;
    case EJson::Number:
    {
        const double Number = Value->AsNumber();
        Out = Number == FMath::FloorToDouble(Number) ? FString::Printf(TEXT("%lld"), static_cast<long long>(Number))
                                                    : FString::SanitizeFloat(Number);
        return true;
    }
    case EJson::String:
        Out = Value->AsString();
        return !Out.IsEmpty();
    default:
        return false;
    }
}

bool ReadCondition(const FReader& R, const FString& Field, const TSharedPtr<FJsonValue>& Value, FCondition& Out)
{
    Out.Field = FName(*Field);
    FValues Single{Value};
    const FValues& Items = Value->Type == EJson::Array ? Value->AsArray() : Single;
    if (Items.IsEmpty())
        return R.Fail(*Field, TEXT("empty condition"));
    for (const TSharedPtr<FJsonValue>& Item : Items)
    {
        FString Text;
        if (!ValueText(Item, Text))
            return R.Fail(*Field, TEXT("unreadable condition"));
        static const TPair<const TCHAR*, FCondition::EOp> Operators[] = {{TEXT("<="), FCondition::EOp::LessEqual},
            {TEXT(">="), FCondition::EOp::GreaterEqual}, {TEXT("<"), FCondition::EOp::Less}, {TEXT(">"), FCondition::EOp::Greater}};
        bool bCompared = false;
        for (const auto& Operator : Operators)
            if (Item->Type == EJson::String && Text.StartsWith(Operator.Key))
            {
                if (Items.Num() != 1)
                    return R.Fail(*Field, TEXT("a comparison stands alone"));
                Out.Op = Operator.Value;
                Out.Bound = FCString::Atod(*Text.RightChop(FCString::Strlen(Operator.Key)));
                bCompared = true;
                break;
            }
        if (bCompared)
            continue;
        if (Item->Type == EJson::String && Text.StartsWith(TEXT("!")))
        {
            if (Items.Num() != 1)
                return R.Fail(*Field, TEXT("a negation stands alone"));
            Out.Op = FCondition::EOp::NotEqual;
            Text.RightChopInline(1);
        }
        Out.Values.Add(Text);
    }
    return true;
}

bool ReadRules(const FReader& R, const FValues& Items, TArray<FRule>& Out)
{
    for (const TSharedPtr<FJsonValue>& Item : Items)
    {
        const FObject* Object = nullptr;
        if (!Item->TryGetObject(Object) || !Object || !Object->IsValid())
            return R.Fail(TEXT("rule"), TEXT("not an object"));
        FRule& Rule = Out.AddDefaulted_GetRef();
        FObject When;
        int32 DelayMs = 0;
        if (!R.Object(**Object, TEXT("when"), When) || !R.Flag(**Object, TEXT("continue"), Rule.bContinue) ||
            !R.Int(**Object, TEXT("delay_ms"), DelayMs))
            return false;
        Rule.DelaySeconds = DelayMs / 1000.f;
        FString Cue, As;
        const bool bCue = (*Object)->TryGetStringField(TEXT("cue"), Cue), bAs = (*Object)->TryGetStringField(TEXT("as"), As);
        if (bCue == bAs)
            return R.Fail(TEXT("rule"), TEXT("needs a cue or an as, not both"));
        Rule.Cue = bCue ? FName(*Cue) : NAME_None;
        Rule.As = bAs ? FName(*As) : NAME_None;
        for (const auto& Pair : When->Values)
            if (!ReadCondition(R, FString(*Pair.Key), Pair.Value, Rule.When.AddDefaulted_GetRef()))
                return false;
    }
    return true;
}

bool ReadCue(const FReader& R, const FJsonObject& O, FCue& Cue)
{
    FObject Sustain;
    if (!R.Name(O, TEXT("id"), Cue.Id) || !R.Name(O, TEXT("bus"), Cue.Bus) || !R.Text(O, TEXT("status"), Cue.Status) ||
        !R.Strings(O, TEXT("waves"), Cue.Waves) || !R.Flag(O, TEXT("spatial"), Cue.bSpatial) ||
        !R.Name(O, TEXT("attenuation"), Cue.Attenuation) || !R.Flag(O, TEXT("loop"), Cue.bLoop) ||
        !R.Int(O, TEXT("max_instances"), Cue.MaxInstances) || !R.Flag(O, TEXT("shuffle"), Cue.bShuffle) ||
        !R.Pair(O, TEXT("pitch_cents"), Cue.PitchCents) || !R.Pair(O, TEXT("volume_db"), Cue.VolumeDb) ||
        !R.Name(O, TEXT("caption"), Cue.Caption) || !R.Flag(O, TEXT("caption_hero"), Cue.bCaptionHero) ||
        !R.Flag(O, TEXT("stinger"), Cue.bStinger) || !R.Int(O, TEXT("strike_ms"), Cue.StrikeMs) ||
        !R.Text(O, TEXT("needs"), Cue.Needs) || !R.Text(O, TEXT("unbound"), Cue.Unbound))
        return false;
    if (Cue.MaxInstances < 1 || Cue.bSpatial != !Cue.Attenuation.IsNone())
        return R.Fail(TEXT("spatial"), TEXT("a 3D cue needs a preset and one instance at least"));
    if (O.HasTypedField<EJson::Object>(TEXT("sustain")))
    {
        int32 GapMs = 0;
        if (!R.Object(O, TEXT("sustain"), Sustain) || !R.Name(*Sustain, TEXT("loop"), Cue.Sustain.Loop) ||
            !R.Name(*Sustain, TEXT("release"), Cue.Sustain.Release) || !R.Int(*Sustain, TEXT("gap_ms"), GapMs) || GapMs <= 0)
            return R.Fail(TEXT("sustain"), TEXT("needs a loop, a release and a positive gap"));
        Cue.bSustain = true;
        Cue.Sustain.GapSeconds = GapMs / 1000.f;
    }
    else if (!O.HasTypedField<EJson::Null>(TEXT("sustain")))
        return R.Fail(TEXT("sustain"), TEXT("missing object (null for none)"));
    return true;
}

bool ReadPlace(const FReader& R, const FJsonObject& O, FPlace& Place)
{
    return R.Name(O, TEXT("bed"), Place.Bed) && R.Name(O, TEXT("weather"), Place.Weather) && R.Name(O, TEXT("surface"), Place.Surface);
}

bool ReadMusic(const FReader& R, const FJsonObject& Music, FData& D)
{
    FObject Pieces, States, Levels, Fades;
    if (!R.Object(Music, TEXT("pieces"), Pieces) || !R.Object(Music, TEXT("states"), States) ||
        !R.Object(Music, TEXT("alert_levels"), Levels) || !R.Object(Music, TEXT("crossfade_ms"), Fades) ||
        !R.Number(Music, TEXT("stinger_duck_db"), D.StingerDuckDb))
        return false;
    for (const auto& Pair : Pieces->Values)
    {
        const FJsonObject& O = *Pair.Value->AsObject();
        FPiece& Piece = D.Pieces.Add(FName(*Pair.Key));
        Piece.Id = FName(*Pair.Key);
        FObject Stems;
        int32 HandoffSample = 0;
        if (!R.Number(O, TEXT("bpm"), Piece.Bpm) || !R.Int(O, TEXT("beats_per_bar"), Piece.BeatsPerBar) ||
            !R.Text(O, TEXT("intro"), Piece.Intro) || !R.Int(O, TEXT("handoff_bars"), Piece.HandoffBars) ||
            !R.Int(O, TEXT("handoff_sample"), HandoffSample) || !R.Object(O, TEXT("stems"), Stems))
            return false;
        if (Piece.Bpm <= 0.f || Piece.BeatsPerBar <= 0 || Stems->Values.IsEmpty() || (!Piece.Intro.IsEmpty() && Piece.HandoffBars <= 0))
            return R.Fail(*Pair.Key, TEXT("a piece needs a tempo, a metre, stems and a handoff after its intro"));
        for (const auto& Stem : Stems->Values)
            Piece.Stems.Emplace(FName(*Stem.Key), Stem.Value->AsString());
    }
    for (const auto& Pair : States->Values)
    {
        const FJsonObject& O = *Pair.Value->AsObject();
        FMusicState& State = D.States.Add(FName(*Pair.Key));
        FObject Mixes;
        const FValues* Phases = nullptr;
        if (!R.Name(O, TEXT("piece"), State.Piece) || !R.Flag(O, TEXT("intro"), State.bIntro) ||
            !R.Object(O, TEXT("mixes"), Mixes) || !R.Array(O, TEXT("phase_mixes"), Phases) || !D.Pieces.Contains(State.Piece))
            return R.Fail(*Pair.Key, TEXT("a state needs a known piece, its mixes and phase mixes"));
        for (const auto& Mix : Mixes->Values)
        {
            TArray<FName>& Stems = State.Mixes.Add(FName(*Mix.Key));
            for (const TSharedPtr<FJsonValue>& Stem : Mix.Value->AsArray())
                Stems.Add(FName(*Stem->AsString()));
        }
        for (const TSharedPtr<FJsonValue>& Phase : *Phases)
        {
            TArray<FName>& Stems = State.PhaseMixes.AddDefaulted_GetRef();
            for (const TSharedPtr<FJsonValue>& Stem : Phase->AsArray())
                Stems.Add(FName(*Stem->AsString()));
        }
        if (!State.Mixes.Contains(TEXT("default")))
            return R.Fail(*Pair.Key, TEXT("a state needs a default mix"));
    }
    for (const TCHAR* Needed : {TEXT("menu"), TEXT("exploration"), TEXT("stealth"), TEXT("combat"), TEXT("boss")})
        if (!D.States.Contains(Needed))
            return R.Fail(Needed, TEXT("missing music state"));
    for (const auto& Pair : Levels->Values)
        D.AlertLevels.Add(FName(*Pair.Key), static_cast<int32>(Pair.Value->AsNumber()));
    int32 Into = 0, Out = 0, Stems = 0, Piece = 0;
    if (!R.Int(*Fades, TEXT("into_alert"), Into) || !R.Int(*Fades, TEXT("out_of_alert"), Out) ||
        !R.Int(*Fades, TEXT("stems"), Stems) || !R.Int(*Fades, TEXT("piece"), Piece))
        return false;
    D.IntoAlertSeconds = Into / 1000.f;
    D.OutOfAlertSeconds = Out / 1000.f;
    D.StemSeconds = Stems / 1000.f;
    D.PieceSeconds = Piece / 1000.f;
    return true;
}

bool ReadAll(const FJsonObject& Root, FData& D, FString& Error)
{
    FReader R{Error, TEXT("root")};
    int32 Schema = 0;
    const FValues* Buses = nullptr;
    const FValues* Cues = nullptr;
    FObject Attenuation, Bindings, Music, Beats, Maps, Weather, Footsteps, Horses, Attached, Emitters, Telegraphs;
    if (!R.Int(Root, TEXT("schema_version"), Schema) || Schema != 1 || !R.Int(Root, TEXT("sample_rate_hz"), D.SampleRate) ||
        !R.Array(Root, TEXT("buses"), Buses) || !R.Array(Root, TEXT("cues"), Cues) ||
        !R.Object(Root, TEXT("attenuation"), Attenuation) || !R.Object(Root, TEXT("bindings"), Bindings) ||
        !R.Object(Root, TEXT("music"), Music) || !R.Object(Root, TEXT("beats"), Beats) || !R.Object(Root, TEXT("maps"), Maps) ||
        !R.Object(Root, TEXT("weather"), Weather) || !R.Object(Root, TEXT("footsteps"), Footsteps) ||
        !R.Object(Root, TEXT("horses"), Horses) || !R.Object(Root, TEXT("attached"), Attached) ||
        !R.Object(Root, TEXT("emitters"), Emitters) || !R.Object(Root, TEXT("telegraphs"), Telegraphs))
        return R.Fail(TEXT("schema_version"), TEXT("needs schema 1 and every section"));

    static const TCHAR* const Sliders[] = {TEXT("Master"), TEXT("Music"), TEXT("SFX"), TEXT("Voice"), TEXT("UI"), TEXT("Ambience")};
    static_assert(UE_ARRAY_COUNT(Sliders) == static_cast<int32>(ESoraAudioBus::Count), "one slider per ESoraAudioBus");
    for (const TSharedPtr<FJsonValue>& Item : *Buses)
    {
        const FJsonObject& O = *Item->AsObject();
        FBus& Bus = D.Buses.AddDefaulted_GetRef();
        FString Slider;
        R.Where = TEXT("buses");
        if (!R.Name(O, TEXT("id"), Bus.Id) || !R.Name(O, TEXT("parent"), Bus.Parent) || !R.Name(O, TEXT("submix_parent"), Bus.SubmixParent) ||
            !R.Number(O, TEXT("default_db"), Bus.DefaultDb) || !R.Text(O, TEXT("slider"), Slider) ||
            !R.Name(O, TEXT("floor_of"), Bus.FloorOf) || !R.Number(O, TEXT("floor_db"), Bus.FloorDb))
            return false;
        for (int32 Index = 0; Index < UE_ARRAY_COUNT(Sliders); ++Index)
            if (Slider == Sliders[Index])
                Bus.Slider = Index;
        if (!Slider.IsEmpty() && Bus.Slider == INDEX_NONE)
            return R.Fail(*Bus.Id.ToString(), TEXT("unknown slider"));
    }
    for (const auto& Pair : Attenuation->Values)
    {
        const FJsonObject& O = *Pair.Value->AsObject();
        FAttenuation& A = D.Attenuation.Add(FName(*Pair.Key));
        float InnerM = 0.f, FalloffM = 0.f;
        R.Where = FString(TEXT("attenuation.")) + FString(*Pair.Key);
        if (!R.Number(O, TEXT("inner_m"), InnerM) || !R.Number(O, TEXT("falloff_m"), FalloffM) ||
            !R.Number(O, TEXT("lpf_far_hz"), A.LowPassFarHz) || !R.Flag(O, TEXT("reverb_send"), A.bReverbSend) ||
            !R.Flag(O, TEXT("doppler"), A.bDoppler) || !R.Flag(O, TEXT("distance_delay"), A.bDistanceDelay))
            return false;
        A.InnerCm = InnerM * 100.f;
        A.FalloffCm = FalloffM * 100.f;
    }
    for (const TSharedPtr<FJsonValue>& Item : *Cues)
    {
        FCue Cue;
        R.Where = TEXT("cues");
        if (!ReadCue(R, *Item->AsObject(), Cue))
            return false;
        if (!D.Bus(Cue.Bus) || (!Cue.Attenuation.IsNone() && !D.Attenuation.Contains(Cue.Attenuation)))
            return R.Fail(*Cue.Id.ToString(), TEXT("unknown bus or attenuation"));
        D.Cues.Add(Cue.Id, MoveTemp(Cue));
    }
    for (const auto& Pair : Bindings->Values)
    {
        R.Where = FString(TEXT("bindings.")) + FString(*Pair.Key);
        TArray<FRule>& Rules = D.Bindings.Add(FName(*Pair.Key));
        if (!ReadRules(R, Pair.Value->AsArray(), Rules))
            return false;
        for (const FRule& Rule : Rules)
            if (!Rule.Cue.IsNone() && !D.Cues.Contains(Rule.Cue))
                return R.Fail(*Rule.Cue.ToString(), TEXT("unknown cue"));
    }
    R.Where = TEXT("music");
    if (!ReadMusic(R, *Music, D))
        return false;
    for (const auto& Pair : Beats->Values)
    {
        const FJsonObject& O = *Pair.Value->AsObject();
        FBeat& Beat = D.Beats.Add(FString(*Pair.Key));
        const FValues* Thunder = nullptr;
        R.Where = FString(TEXT("beats.")) + FString(*Pair.Key);
        if (!R.Int(O, TEXT("chapter"), Beat.Chapter) || !R.Name(O, TEXT("place"), Beat.Place) ||
            !R.Name(O, TEXT("music_id"), Beat.MusicId) || !R.Name(O, TEXT("state"), Beat.State) ||
            !R.Name(O, TEXT("sparring"), Beat.Sparring) || !ReadPlace(R, O, Beat) || !R.Array(O, TEXT("thunder_s"), Thunder))
            return false;
        for (const TSharedPtr<FJsonValue>& Seconds : *Thunder)
            Beat.ThunderSeconds.Add(static_cast<float>(Seconds->AsNumber()));
        if (!D.States.Contains(Beat.State))
            return R.Fail(TEXT("state"), TEXT("unknown music state"));
    }
    for (const auto& Pair : Maps->Values)
    {
        R.Where = FString(TEXT("maps.")) + FString(*Pair.Key);
        if (!ReadPlace(R, *Pair.Value->AsObject(), D.Maps.Add(FCString::Atoi(*Pair.Key))))
            return false;
    }
    for (const auto& Pair : Weather->Values)
        D.Weather.Add(FName(*Pair.Key), Pair.Value->AsString().IsEmpty() ? NAME_None : FName(*Pair.Value->AsString()));

    R.Where = TEXT("footsteps");
    FObject Materials, Surfaces, Stride, Pace;
    int32 RangeM = 0;
    if (!R.Object(*Footsteps, TEXT("materials"), Materials) || !R.Object(*Footsteps, TEXT("surfaces"), Surfaces) ||
        !R.Object(*Footsteps, TEXT("stride_cm"), Stride) || !R.Object(*Footsteps, TEXT("pace_db"), Pace) ||
        !R.Int(*Footsteps, TEXT("nightingale_permille"), D.NightingalePermille) ||
        !R.Number(*Footsteps, TEXT("run_speed_cm_s"), D.RunSpeedCmS) || !R.Number(*Footsteps, TEXT("min_speed_cm_s"), D.MinSpeedCmS) ||
        !R.Int(*Footsteps, TEXT("range_m"), RangeM))
        return false;
    D.FootstepRangeCm = RangeM * 100.f;
    for (const auto& Pair : Materials->Values)
        D.Materials.Add(FString(*Pair.Key), FName(*Pair.Value->AsString()));
    for (const auto& Pair : Surfaces->Values)
        D.Surfaces.Add(FName(*Pair.Key), FName(*Pair.Value->AsString()));
    static const TCHAR* const Paces[] = {TEXT("crouch"), TEXT("walk"), TEXT("run")};
    for (int32 Index = 0; Index < 3; ++Index)
        if (!R.Number(*Stride, Paces[Index], D.StrideCm[Index]) || !R.Number(*Pace, Paces[Index], D.PaceDb[Index]) || D.StrideCm[Index] <= 0.f)
            return R.Fail(Paces[Index], TEXT("needs a positive stride and a level"));

    R.Where = TEXT("horses");
    FObject Hoofbeats;
    if (!R.Object(*Horses, TEXT("hoofbeats_per_s"), Hoofbeats) || !R.Int(*Horses, TEXT("range_m"), RangeM))
        return false;
    D.HorseRangeCm = RangeM * 100.f;
    for (const auto& Pair : Hoofbeats->Values)
        D.HoofbeatsPerSecond.Add(FName(*Pair.Key), static_cast<float>(Pair.Value->AsNumber()));
    for (const auto& Pair : Attached->Values)
        D.Attached.Add(FName(*Pair.Key), FName(*Pair.Value->AsString()));
    R.Where = TEXT("emitters");
    for (const auto& Pair : Emitters->Values)
    {
        FString CueId;
        if (Pair.Key.IsEmpty() || Pair.Key.Equals(TEXT("None"), ESearchCase::IgnoreCase) ||
            !R.Text(*Emitters, *Pair.Key, CueId))
            return R.Fail(*Pair.Key, TEXT("needs an emitter name and cue"));
        const FCue* Cue = D.Cue(FName(*CueId));
        if (!Cue || !Cue->bLoop || !Cue->bSpatial || Cue->Bus != TEXT("Ambience"))
            return R.Fail(*Pair.Key, TEXT("needs a spatial Ambience loop"));
        D.Emitters.Add(FName(*Pair.Key), Cue->Id);
    }

    R.Where = TEXT("telegraphs");
    FObject Boss, Enemy;
    const FValues* Permille = nullptr;
    if (!R.Object(*Telegraphs, TEXT("boss"), Boss) || !R.Object(*Telegraphs, TEXT("enemy"), Enemy) ||
        !R.Array(*Telegraphs, TEXT("windup_permille"), Permille) || Permille->Num() != 3)
        return R.Fail(TEXT("windup_permille"), TEXT("needs boss and enemy tables and three windup scales"));
    for (int32 Index = 0; Index < 3; ++Index)
        D.WindupPermille[Index] = static_cast<int32>((*Permille)[Index]->AsNumber());
    const auto ReadTelegraph = [&R](const FJsonObject& O, FTelegraph& T) { return R.Name(O, TEXT("class"), T.Class) && R.Int(O, TEXT("windup_ms"), T.WindupMs); };
    for (const auto& Pair : Boss->Values)
        if (!ReadTelegraph(*Pair.Value->AsObject(), D.BossTelegraphs.Add(FString(*Pair.Key))))
            return false;
    for (const auto& Pair : Enemy->Values)
        if (!ReadTelegraph(*Pair.Value->AsObject(), D.EnemyTelegraphs.Add(FName(*Pair.Key))))
            return false;
    return true;
}

struct FLoaded
{
    bool bTried = false;
    bool bReady = false;
    FString Error;
    FData Data;
};

FLoaded& Loaded()
{
    static FLoaded Instance;
    return Instance;
}
}

FFacts& FFacts::Text(FName Field, const FString& Value)
{
    Values.Emplace(Field, Value);
    return *this;
}
FFacts& FFacts::Int(FName Field, int32 Value) { return Text(Field, FString::FromInt(Value)); }
FFacts& FFacts::Flag(FName Field, bool bValue) { return Text(Field, bValue ? TEXT("true") : TEXT("false")); }
FFacts& FFacts::Number(FName Field, double Value) { return Text(Field, FString::SanitizeFloat(Value)); }
const FString* FFacts::Find(FName Field) const
{
    for (const TPair<FName, FString>& Pair : Values)
        if (Pair.Key == Field)
            return &Pair.Value;
    return nullptr;
}

bool FCondition::Matches(const FFacts& Facts) const
{
    const FString* Value = Facts.Find(Field);
    if (!Value)
        return false;
    switch (Op)
    {
    case EOp::Equal: return Values.Contains(*Value);
    case EOp::NotEqual: return !Values.Contains(*Value);
    case EOp::Less: return FCString::Atod(**Value) < Bound;
    case EOp::LessEqual: return FCString::Atod(**Value) <= Bound;
    case EOp::Greater: return FCString::Atod(**Value) > Bound;
    case EOp::GreaterEqual: return FCString::Atod(**Value) >= Bound;
    }
    return false;
}

bool FRule::Matches(const FFacts& Facts) const
{
    for (const FCondition& Condition : When)
        if (!Condition.Matches(Facts))
            return false;
    return true;
}

const FBus* FData::Bus(FName Id) const
{
    return Buses.FindByPredicate([Id](const FBus& Bus) { return Bus.Id == Id; });
}

const FData* FData::Get()
{
    FLoaded& L = Loaded();
    if (!L.bTried)
    {
        L.bTried = true;
        FString Text;
        const FString Path = FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Data/audio.json"));
        TSharedPtr<FJsonObject> Root;
        if (!FFileHelper::LoadFileToString(Text, *Path))
            L.Error = FString::Printf(TEXT("cannot read %s"), *Path);
        else if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid())
            L.Error = TEXT("audio.json is not JSON");
        else
            L.bReady = ReadAll(*Root, L.Data, L.Error);
        if (!L.bReady)
            L.Data = FData();
    }
    return L.bReady ? &L.Data : nullptr;
}

const FString& FData::Error() { return Loaded().Error; }

FString WaveObjectPath(const FString& Wave)
{
    return FString::Printf(TEXT("/Game/Generated/Audio/%s.%s"), *Wave, *FPaths::GetCleanFilename(Wave));
}

FString SubmixObjectPath(FName Bus)
{
    return FString::Printf(TEXT("/Game/Generated/Audio/Buses/SMX_%s.SMX_%s"), *Bus.ToString(), *Bus.ToString());
}
}
