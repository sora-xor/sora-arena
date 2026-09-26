// USoraAudioSubsystem: music and ambience.
#include "SoraAudio.h"
#include "Audio/SoraAudioData.h"
#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Quartz/AudioMixerClockHandle.h"
#include "Quartz/QuartzSubsystem.h"
#include "SoraCharacterBase.h"
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "Sound/SoundWave.h"

using namespace SoraAudioData;

namespace
{
const FName StateNames[] = {NAME_None, TEXT("menu"), TEXT("exploration"), TEXT("stealth"), TEXT("combat"), TEXT("boss")};
const FName DefaultMix(TEXT("default"));
const FName Thunder(TEXT("amb.thunder"));
// A bed hands over to the next place's over this long.
constexpr float BedFadeSeconds = 2.f;
// Thunder rolls in from about this far away.
constexpr float ThunderDistanceCm = 150000.f;
// The alert level at which a stealth zone's music turns to combat.
constexpr int32 CombatAlert = 3;

float DbToGain(float Db) { return FMath::Pow(10.f, Db / 20.f); }
}

double USoraAudioSubsystem::MusicClock() const
{
    // Real time: menus pause the world, not the music.
    return GetWorld() ? GetWorld()->GetRealTimeSeconds() : 0.0;
}

ESoraMusicState USoraAudioSubsystem::WantedMusic() const
{
    const ASoraGameMode* Game = Mode();
    if (!Game)
        return ESoraMusicState::Silent;
    const USoraFrontEnd* Front = Game->FrontEnd();
    if (Game->bMenu && Front && Front->IsOpen())
    {
        // The pause menu keeps the round's music under it.
        if (!Front->IsPauseContext())
            return ESoraMusicState::Menu;
        if (MusicNow.State != ESoraMusicState::Silent && MusicNow.State != ESoraMusicState::Menu)
            return MusicNow.State;
    }
    if (Game->bDeterministicPractice || !Game->bCampaign)
        return ESoraMusicState::Combat;
    if (Game->bChapterComplete || bBossDefeated)
        return ESoraMusicState::Exploration;
    if (Boss.IsValid())
        return ESoraMusicState::Boss;
    const FName State = Beat ? Beat->State : StateNames[static_cast<int32>(ESoraMusicState::Exploration)];
    if (State == StateNames[static_cast<int32>(ESoraMusicState::Boss)])
        return ESoraMusicState::Boss;
    if (State == StateNames[static_cast<int32>(ESoraMusicState::Combat)])
        return ESoraMusicState::Combat;
    if (State == StateNames[static_cast<int32>(ESoraMusicState::Stealth)])
    {
        int32 Loudest = 0;
        for (const auto& Pair : Alert)
        {
            const ASoraCharacterBase* Guard = Cast<ASoraCharacterBase>(Pair.Key.Get());
            if (Guard && Guard->IsAlive())
                Loudest = FMath::Max(Loudest, Pair.Value);
        }
        return Loudest >= CombatAlert ? ESoraMusicState::Combat : ESoraMusicState::Stealth;
    }
    return ESoraMusicState::Exploration;
}

FName USoraAudioSubsystem::WantedMix(ESoraMusicState State, TArray<FName>& Stems) const
{
    Stems.Reset();
    const FData* D = FData::Get();
    const FMusicState* Data = D ? D->States.Find(StateNames[static_cast<int32>(State)]) : nullptr;
    if (!Data)
        return NAME_None;
    if (State == ESoraMusicState::Boss && Data->PhaseMixes.Num())
    {
        const int32 Phase = FMath::Clamp(BossPhaseIndex, 0, Data->PhaseMixes.Num() - 1);
        Stems = Data->PhaseMixes[Phase];
        return FName(*FString::Printf(TEXT("phase%d"), Phase + 1));
    }
    FName Mix = DefaultMix;
    if (State == ESoraMusicState::Stealth)
    {
        // The most alarmed guard short of combat picks the stems.
        int32 Loudest = 0;
        for (const auto& Pair : Alert)
        {
            const ASoraCharacterBase* Guard = Cast<ASoraCharacterBase>(Pair.Key.Get());
            if (Guard && Guard->IsAlive())
                Loudest = FMath::Max(Loudest, Pair.Value);
        }
        for (const auto& Level : D->AlertLevels)
            if (Level.Value == FMath::Min(Loudest, CombatAlert - 1) && Data->Mixes.Contains(Level.Key))
                Mix = Level.Key;
    }
    const TArray<FName>* Chosen = Data->Mixes.Find(Mix);
    Stems = Chosen ? *Chosen : Data->Mixes.FindChecked(DefaultMix);
    return Chosen ? Mix : DefaultMix;
}

TArray<FName> USoraAudioSubsystem::StemVoices() const
{
    TArray<FName> Out;
    for (const FPieceVoice& Voice : Voices)
        if (Voice.StopAt <= 0.0 && Voice.Piece == MusicNow.Piece)
            for (const auto& Stem : Voice.Stems)
            {
                // A stem fading out is on its way to stopping; a virtualised
                // one would restart out of step with the others.
                const UAudioComponent* Component = Stem.Value.Get();
                if (Component && Component->IsPlaying() && Component->GetPlayState() != EAudioComponentPlayState::FadingOut &&
                    !Component->IsVirtualized())
                    Out.Add(Stem.Key);
            }
    return Out;
}

void USoraAudioSubsystem::HoldStemGains()
{
    MusicNow.StemGains.Reset();
    const FData* D = FData::Get();
    if (const FPiece* Piece = D ? D->Pieces.Find(MusicNow.Piece) : nullptr)
        for (const TPair<FName, FString>& Stem : Piece->Stems)
            MusicNow.StemGains.Add(Stem.Key, MusicNow.Stems.Contains(Stem.Key) ? MusicNow.BedGain : MutedStemGain);
}

void USoraAudioSubsystem::TickMusic()
{
    const double Now = MusicClock();
    TArray<FName> Stems;
    const ESoraMusicState State = WantedMusic();
    const FName Mix = WantedMix(State, Stems);
    if (State != MusicNow.State || Mix != MusicNow.Mix || Stems != MusicNow.Stems)
        ChangeMusic(State, Mix, Stems);
    if (MusicNow.bIntro && Now >= IntroEnds)
        MusicNow.bIntro = false;
    if (!MusicNow.Stinger.IsNone() && Now >= MusicNow.StingerEnds)
    {
        MusicNow.Stinger = NAME_None;
        MusicNow.BedGain = 1.f;
        SetStemGains(.6f);
    }
    for (int32 Index = Voices.Num() - 1; Index >= 0; --Index)
    {
        FPieceVoice& Voice = Voices[Index];
        if (Voice.StopAt <= 0.0 || Now < Voice.StopAt)
            continue;
        if (UQuartzClockHandle* Clock = Voice.Clock.Get())
        {
            Clock->StopClock(GetWorld(), true, Clock);
            Clocks.Remove(Clock);
        }
        Voices.RemoveAt(Index);
    }
}

void USoraAudioSubsystem::ChangeMusic(ESoraMusicState State, FName Mix, const TArray<FName>& Stems)
{
    const FData* D = FData::Get();
    const FMusicState* Data = D->States.Find(StateNames[static_cast<int32>(State)]);
    const FName Piece = Data ? Data->Piece : NAME_None;
    float Fade = D->StemSeconds;
    if (State == ESoraMusicState::Combat && MusicNow.State == ESoraMusicState::Stealth)
        Fade = D->IntoAlertSeconds;
    else if (MusicNow.State == ESoraMusicState::Combat && State == ESoraMusicState::Stealth)
        Fade = D->OutOfAlertSeconds;
    const bool bNewPiece = Piece != MusicNow.Piece;
    if (bNewPiece)
        Fade = D->PieceSeconds;
    MusicNow.State = State;
    MusicNow.Piece = Piece;
    MusicNow.Mix = Mix;
    MusicNow.Stems = Stems;
    MusicNow.FadeSeconds = Fade;
    ++MusicNow.Changes;
    if (!bNewPiece)
    {
        SetStemGains(Fade);
        return;
    }
    for (FPieceVoice& Voice : Voices)
        if (Voice.StopAt <= 0.0)
            FadeOutPiece(Voice, Fade);
    const FPiece* PieceData = D->Pieces.Find(Piece);
    MusicNow.bIntro = Data && Data->bIntro && PieceData && !PieceData->Intro.IsEmpty();
    HoldStemGains();
    if (PieceData)
        StartPiece(Piece, Stems, MusicNow.bIntro, Fade);
}

void USoraAudioSubsystem::StartPiece(FName PieceId, const TArray<FName>& Stems, bool bIntro, float FadeSeconds)
{
    const FPiece& Piece = FData::Get()->Pieces.FindChecked(PieceId);
    FPieceVoice& Voice = Voices.AddDefaulted_GetRef();
    Voice.Piece = PieceId;
    if (bIntro)
        IntroEnds = MusicClock() + Piece.HandoffBars * Piece.BarSeconds();
    UWorld* World = GetWorld();
    if (!HasDevice() || !World)
        return;
    // One Quartz clock per piece at its tempo and metre: every stem starts on
    // its first bar, so they stay sample-locked while only their gains move;
    // after the title's intro the loop starts exactly HandoffBars bars later
    // (sample 698,182 of the intro at 66 BPM), while the intro's tail rings on.
    UQuartzSubsystem* Quartz = UQuartzSubsystem::Get(World);
    FQuartzClockSettings Settings;
    Settings.TimeSignature.NumBeats = Piece.BeatsPerBar;
    Settings.TimeSignature.BeatType = EQuartzTimeSignatureQuantization::QuarterNote;
    Voice.ClockName = FName(*FString::Printf(TEXT("SoraMusic_%s_%d"), *PieceId.ToString(), ++ClockSerial));
    UQuartzClockHandle* Clock = Quartz ? Quartz->CreateNewClock(World, Voice.ClockName, Settings, true) : nullptr;
    if (Clock)
    {
        Clock->SetBeatsPerMinute(World, FQuartzQuantizationBoundary(), FOnQuartzCommandEventBP(), Clock, Piece.Bpm);
        Clocks.Add(Clock);
        Voice.Clock = Clock;
    }
    FQuartzQuantizationBoundary OnStart(EQuartzCommandQuantization::Bar, 1.f, EQuarztQuantizationReference::BarRelative, true);
    FQuartzQuantizationBoundary Handoff(EQuartzCommandQuantization::Bar, static_cast<float>(FMath::Max(Piece.HandoffBars, 1)),
        EQuarztQuantizationReference::CurrentTimeRelative, false);
    const auto Start = [&](UAudioComponent* Component, FQuartzQuantizationBoundary& Boundary, float Fade, float Gain)
    {
        Component->bIsUISound = true;
        if (Clock)
            Component->PlayQuantized(World, Clock, Boundary, FOnQuartzCommandEventBP(), 0.f, Fade, Gain);
        else
            Component->FadeIn(Fade, Gain);
        Held.Add(Component);
    };
    // Each component goes when its voice stops (after FadeOutPiece), rather
    // than staying on the world settings for the rest of the world.
    const bool bAutoDestroy = true;
    if (bIntro)
        if (USoundWave* Intro = LoadWave(Piece.Intro))
            if (UAudioComponent* Component = UGameplayStatics::CreateSound2D(World, Intro, 1.f, 1.f, 0.f, nullptr, false, bAutoDestroy))
            {
                Start(Component, OnStart, 0.f, MusicNow.BedGain);
                Voice.Intro = Component;
            }
    for (const TPair<FName, FString>& Stem : Piece.Stems)
        if (USoundWave* Wave = LoadWave(Stem.Value))
            if (UAudioComponent* Component = UGameplayStatics::CreateSound2D(World, Wave, 1.f, 1.f, 0.f, nullptr, false, bAutoDestroy))
            {
                Start(Component, bIntro ? Handoff : OnStart, bIntro ? 0.f : FadeSeconds, MusicNow.StemGains.FindRef(Stem.Key));
                Voice.Stems.Add(Stem.Key, Component);
            }
    if (Clock)
        Clock->StartClock(World, Clock);
}

void USoraAudioSubsystem::FadeOutPiece(FPieceVoice& Voice, float FadeSeconds)
{
    for (const auto& Stem : Voice.Stems)
        if (UAudioComponent* Component = Stem.Value.Get())
            Component->FadeOut(FMath::Max(FadeSeconds, .02f), 0.f);
    if (UAudioComponent* Intro = Voice.Intro.Get())
        Intro->FadeOut(FMath::Max(FadeSeconds, .02f), 0.f);
    Voice.StopAt = MusicClock() + FadeSeconds + .1;
}

void USoraAudioSubsystem::SetStemGains(float FadeSeconds)
{
    // Never to zero: the engine would stop the stem at the end of the fade.
    HoldStemGains();
    for (FPieceVoice& Voice : Voices)
    {
        if (Voice.StopAt > 0.0 || Voice.Piece != MusicNow.Piece)
            continue;
        for (const auto& Stem : Voice.Stems)
            if (UAudioComponent* Component = Stem.Value.Get())
                Component->AdjustVolume(FMath::Max(FadeSeconds, .02f), MusicNow.StemGains.FindRef(Stem.Key));
        if (UAudioComponent* Intro = Voice.Intro.Get())
            Intro->AdjustVolume(FMath::Max(FadeSeconds, .02f), MusicNow.BedGain);
    }
}

bool USoraAudioSubsystem::StartStinger(FSoraAudioPlay& Record, const FCue& Cue)
{
    (void)Cue;
    const double Now = MusicClock();
    // Never two stingers at once: the later one is dropped.
    if (!MusicNow.Stinger.IsNone() && Now < MusicNow.StingerEnds)
        return false;
    const USoundWave* Wave = LoadWave(Record.Wave);
    if (!Wave || Wave->Duration <= 0.f)
        return true;
    MusicNow.Stinger = Record.Cue;
    MusicNow.StingerEnds = Now + Wave->Duration;
    MusicNow.BedGain = DbToGain(FData::Get()->StingerDuckDb);
    SetStemGains(.08f);
    return true;
}

// Ambience ------------------------------------------------------------------

const FPlace* USoraAudioSubsystem::WantedPlace() const
{
    const ASoraGameMode* Game = Mode();
    const FData* D = FData::Get();
    if (!Game || !D)
        return nullptr;
    const USoraFrontEnd* Front = Game->FrontEnd();
    if (Game->bMenu && Front && Front->IsOpen() && !Front->IsPauseContext())
        return nullptr;
    if (Game->bDeterministicPractice || !Game->bCampaign)
        return D->Maps.Find(Game->MapId);
    return Beat;
}

void USoraAudioSubsystem::SetBed(const FString& Key, FName Cue, FName& Current)
{
    if (Cue == Current)
        return;
    if (!Current.IsNone())
        StopLoop(Key, BedFadeSeconds);
    Current = Cue;
    if (Cue.IsNone())
        return;
    // The new bed comes in over the same 2 s the old one takes to go.
    FRequest Request;
    Request.Family = TEXT("Ambience");
    Request.Location = Listener();
    Request.LoopKey = Key;
    Request.bBed = true;
    Request.FadeInSeconds = BedFadeSeconds;
    Play(Cue, Request);
}

void USoraAudioSubsystem::TickAmbience(double Now)
{
    const FData* D = FData::Get();
    const FPlace* Place = WantedPlace();
    WeatherName = Place ? Place->Weather : NAME_None;
    SetBed(TEXT("bed"), Place ? Place->Bed : NAME_None, BedCue);
    SetBed(TEXT("weather"), Place ? D->Weather.FindRef(Place->Weather) : NAME_None, WeatherCue);
    // A storm's thunder on the chapter's lightning schedule, rolling in from
    // far off (the far preset delays it by its distance).
    const FBeat* Storm = Place && Place == Beat && Beat->ThunderSeconds.Num() ? Beat : nullptr;
    if (!Storm)
    {
        NextThunder = 0.0;
        ThunderIndex = 0;
        return;
    }
    if (NextThunder <= 0.0)
    {
        NextThunder = Now + Storm->ThunderSeconds[0];
        return;
    }
    if (Now < NextThunder)
        return;
    const float Bearing = Random.FRandRange(0.f, 2.f * PI);
    FRequest Request;
    Request.Family = TEXT("Ambience");
    Request.Location = Listener() + FVector(FMath::Cos(Bearing), FMath::Sin(Bearing), .2f) * ThunderDistanceCm;
    Play(Thunder, Request);
    ThunderIndex = (ThunderIndex + 1) % Storm->ThunderSeconds.Num();
    NextThunder = Now + Storm->ThunderSeconds[ThunderIndex];
}
