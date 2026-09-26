#pragma once
#include "CoreMinimal.h"

// Content/Data/audio.json, built by scripts/audio/build_audio_data.py and
// checked by scripts/audio/validate_audio_data.py: the buses, 3D presets,
// cues, the rules that pick a cue from each event family, the music pieces
// and states, and every campaign beat's and practice arena's ambience. It is
// read once, fail-closed: a missing or malformed field fails the load and
// USoraAudioSubsystem stays silent with the reason logged.
namespace SoraAudioData
{
// An event's fields as the rules read them: whole numbers, flags as true or
// false, enum and id names, and measures as decimal text.
struct FFacts
{
    TArray<TPair<FName, FString>, TInlineAllocator<8>> Values;
    FFacts& Text(FName Field, const FString& Value);
    FFacts& Int(FName Field, int32 Value);
    FFacts& Flag(FName Field, bool bValue);
    FFacts& Number(FName Field, double Value);
    const FString* Find(FName Field) const;
};

// One field test of a rule: equal to any listed value, not equal to one, or
// a numeric comparison ("<0.5", ">=1200"). A missing field never matches.
struct FCondition
{
    enum class EOp : uint8 { Equal, NotEqual, Less, LessEqual, Greater, GreaterEqual };
    FName Field;
    EOp Op = EOp::Equal;
    TArray<FString> Values;
    double Bound = 0.0;
    bool Matches(const FFacts& Facts) const;
};

// The first matching rule of a family plays its cue, or hands the event to
// another family's rules (As, practice kernel events only); Continue keeps
// looking after it.
struct FRule
{
    TArray<FCondition> When;
    FName Cue;
    FName As;
    bool bContinue = false;
    float DelaySeconds = 0.f;
    bool Matches(const FFacts& Facts) const;
};

// A shot repeated within Gap keeps Loop running; Release plays when it stops.
struct FSustain
{
    FName Loop;
    FName Release;
    float GapSeconds = 0.f;
};

struct FCue
{
    FName Id;
    FName Bus;
    FString Status;
    // Paths under both Content/SourceArt/Audio and /Game/Generated/Audio
    // ("Original/Weapons/wpn_arc_carbine_fire_01"); none for a cue whose
    // sound is still to be made (Needs says what).
    TArray<FString> Waves;
    bool bSpatial = false;
    FName Attenuation;
    bool bLoop = false;
    int32 MaxInstances = 1;
    bool bShuffle = true;
    float PitchCents[2] = {0.f, 0.f};
    float VolumeDb[2] = {0.f, 0.f};
    // A SoraArena.SoundCaptions key, and whether the hero's own sound is captioned too.
    FName Caption;
    bool bCaptionHero = false;
    // Music-bus one-shots: never two at once, and the bed ducks under them.
    bool bStinger = false;
    // A telegraph's strike, in milliseconds from its start; the scaled windup
    // lines it up with the blow.
    int32 StrikeMs = 0;
    bool bSustain = false;
    FSustain Sustain;
    FString Needs;
    // Imported but never played by a rule (layers for a MetaSound and the like).
    FString Unbound;
    bool IsVoiced() const { return Waves.Num() > 0; }
};

struct FBus
{
    FName Id;
    FName Parent;
    FName SubmixParent;
    float DefaultDb = 0.f;
    // The ESoraAudioBus slider it carries, or INDEX_NONE.
    int32 Slider = INDEX_NONE;
    // A telegraph bus: never below FloorDb whatever FloorOf's slider says.
    FName FloorOf;
    float FloorDb = 0.f;
};

struct FAttenuation
{
    float InnerCm = 0.f;
    float FalloffCm = 0.f;
    // Zero: no distance low-pass.
    float LowPassFarHz = 0.f;
    bool bReverbSend = false;
    bool bDoppler = false;
    // Sound travels at 343 m/s: far thunder arrives late.
    bool bDistanceDelay = false;
};

struct FPiece
{
    FName Id;
    float Bpm = 60.f;
    int32 BeatsPerBar = 4;
    // An intro plays once; the stems start HandoffBars bars after it.
    FString Intro;
    int32 HandoffBars = 0;
    TArray<TPair<FName, FString>> Stems;
    float BarSeconds() const { return BeatsPerBar * 60.f / Bpm; }
};

struct FMusicState
{
    FName Piece;
    bool bIntro = false;
    TMap<FName, TArray<FName>> Mixes;
    // A boss fight's stems by its pattern phase; the last covers later phases.
    TArray<TArray<FName>> PhaseMixes;
};

struct FPlace
{
    FName Bed;
    FName Weather;
    FName Surface;
};

struct FBeat : FPlace
{
    int32 Chapter = 0;
    FName Place;
    FName MusicId;
    FName State;
    FName Sparring;
    // Seconds between thunderclaps, cycled (the chapter's lightning schedule).
    TArray<float> ThunderSeconds;
};

struct FTelegraph
{
    FName Class;
    int32 WindupMs = 0;
};

struct FData
{
    int32 SampleRate = 48000;
    TArray<FBus> Buses;
    TMap<FName, FAttenuation> Attenuation;
    TMap<FName, FCue> Cues;
    TMap<FName, TArray<FRule>> Bindings;
    TMap<FName, FPiece> Pieces;
    TMap<FName, FMusicState> States;
    TMap<FName, int32> AlertLevels;
    float IntoAlertSeconds = 0.f, OutOfAlertSeconds = 0.f, StemSeconds = 0.f, PieceSeconds = 0.f;
    float StingerDuckDb = 0.f;
    TMap<FString, FBeat> Beats;
    TMap<int32, FPlace> Maps;
    TMap<FName, FName> Weather;
    // Footsteps: material role to surface, surface to cue, and pace.
    TMap<FString, FName> Materials;
    TMap<FName, FName> Surfaces;
    int32 NightingalePermille = 0;
    // Crouch, walk, run.
    float StrideCm[3] = {0.f, 0.f, 0.f};
    float PaceDb[3] = {0.f, 0.f, 0.f};
    float RunSpeedCmS = 0.f, MinSpeedCmS = 0.f, FootstepRangeCm = 0.f;
    TMap<FName, float> HoofbeatsPerSecond;
    float HorseRangeCm = 0.f;
    TMap<FName, FName> Attached;
    // "boss_id/attack_id", and an enemy attack's cue.
    TMap<FString, FTelegraph> BossTelegraphs;
    TMap<FName, FTelegraph> EnemyTelegraphs;
    // Easy, Normal, Hard.
    int32 WindupPermille[3] = {1000, 1000, 1000};

    // Reads Content/Data/audio.json once; later calls return the first result.
    static const FData* Get();
    // Why the load failed, or empty.
    static const FString& Error();
    const FCue* Cue(FName Id) const { return Cues.Find(Id); }
    const FBus* Bus(FName Id) const;
};

// The caption text of a SoraArena.SoundCaptions key (SoraSoundCaptions.cpp).
FText CaptionText(FName Key);
// A wave's object path under /Game/Generated/Audio.
FString WaveObjectPath(const FString& Wave);
// A bus's submix under /Game/Generated/Audio/Buses.
FString SubmixObjectPath(FName Bus);
}
