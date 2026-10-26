#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "SoraAudio.generated.h"
class AActor;
class ASoraGameMode;
class UAudioComponent;
class UQuartzClockHandle;
class USoraSettings;
class USoundAttenuation;
class USoundClass;
class USoundConcurrency;
class USoundSubmix;
class USoundWave;
enum class ESoraUISound : uint8;
struct FSoraBeatEvent;
struct FSoraBossPhaseEvent;
struct FSoraChapterEvent;
struct FSoraDamagedEvent;
struct FSoraDefenseEvent;
struct FSoraDetonatedEvent;
struct FSoraDiedEvent;
struct FSoraEnemyCueEvent;
struct FSoraMarobashiEvent;
struct FSoraMeleeCommittedEvent;
struct FSoraPracticeEvent;
struct FSoraSiteRestoredEvent;
struct FSoraStrikeResolvedEvent;
struct FSoraWeaponFiredEvent;
namespace SoraAudioData
{
struct FBeat;
struct FCue;
struct FFacts;
struct FPlace;
}

// One cue the subsystem started, or would have in a world without an audio
// device (headless automation runs with -nosound): the rule's family, the
// cue, the wave it picked (none for a cue whose sound is still to be made),
// where and how it plays.
struct FSoraAudioPlay
{
    FName Family;
    FName Cue;
    FString Wave;
    FName Bus;
    FName Attenuation;
    FVector Location = FVector::ZeroVector;
    bool bSpatial = false;
    bool bLoop = false;
    bool bStinger = false;
    // A stinger that arrived while another sounded is dropped, never stacked.
    bool bDropped = false;
    bool bCaptioned = false;
    float Volume = 1.f;
    float Pitch = 1.f;
    // Sound travelling to the listener, or a telegraph held back so its
    // strike lands on a longer windup.
    float DelaySeconds = 0.f;
    // Into the wave: a telegraph cut short for a quicker windup.
    float StartSeconds = 0.f;
    // A bed coming in under the one fading out.
    float FadeInSeconds = 0.f;
    // The rule that chose the cue: its family and index in audio.json's
    // bindings, and the Kernel rule that forwarded the event to that family.
    FName RuleFamily;
    int32 Rule = INDEX_NONE;
    int32 ForwardedBy = INDEX_NONE;
    double Time = 0.0;
    TWeakObjectPtr<AActor> Source;
    TWeakObjectPtr<UAudioComponent> Component;
    bool IsVoiced() const { return !Wave.IsEmpty(); }
};

// The music the subsystem plays: the title screen and menus, exploration, a
// stealth zone (its stems follow the most alarmed guard), combat, and a boss
// (its stems follow the boss's phase). Stems of one piece start together on a
// Quartz bar and only change gain, so a stealth zone that turns into a fight
// and back never loses its place in the bar.
enum class ESoraMusicState : uint8 { Silent, Menu, Exploration, Stealth, Combat, Boss };

struct FSoraMusicStatus
{
    ESoraMusicState State = ESoraMusicState::Silent;
    FName Piece;
    FName Mix;
    TArray<FName> Stems;
    // The title's intro is sounding; its loop takes over on bar four.
    bool bIntro = false;
    // The fade of the last change, and how many changes there were.
    float FadeSeconds = 0.f;
    int32 Changes = 0;
    // The stinger sounding, when it ends, and the bed's gain under it.
    FName Stinger;
    double StingerEnds = 0.0;
    float BedGain = 1.f;
    // The gain every stem of the piece is held at: the bed's for the mix,
    // MutedStemGain for the rest, recorded with or without a device.
    TMap<FName, float> StemGains;
};

/**
 * The game's sound (docs/audio.md). It hears every USoraGameEvents
 * announcement, the practice kernel's events and the front end, and polls
 * what has no event: the hero's weapon actions, footsteps, horses and loops
 * that ride on opponents. Content/Data/audio.json (SoraAudioData) picks the
 * cue for each through its family's rules and says how it plays: bus, 3D
 * preset, concurrency and variation, and its bilingual sound caption, which
 * USoraCaptions shows. Music follows the menu, the campaign beat, stealth
 * alerts and boss phases; ambience follows the beat's place and weather or the
 * practice arena. The Music, SFX, Voice, UI and Ambience settings set their
 * submixes' output (Master stays the device volume, USoraSettings), and the
 * telegraph buses never drop below their floor. Everything is presentation:
 * nothing here changes play.
 */
UCLASS()
class SORAARENA_API USoraAudioSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    static USoraAudioSubsystem* Get(const UObject* WorldContext);
    // audio.json loaded; without it the world stays silent.
    bool IsReady() const;
    // A device to play on: false in headless automation, where every cue is
    // still chosen and recorded.
    bool HasDevice() const;

    // Runs Family's rules on an event's fields as the pollers do, for a
    // sound at Location (from Source when it is set). The families without a
    // broadcast (Hero, Footstep, Horse, Workshop) come through here.
    void Hear(FName Family, const SoraAudioData::FFacts& Facts, AActor* Source, const FVector& Location);

    // A stationary ambience loop at an authored world position. Owner scopes
    // its lifetime; Name selects audio.json's emitter. Repeating the same
    // request never stacks voices. Only spatial Ambience loops are accepted.
    bool StartAmbientEmitter(AActor* Owner, FName Name, const FVector& Location);
    void StopAmbientEmitters(const AActor* Owner);

    // What played, oldest first (the last 512).
    const TArray<FSoraAudioPlay>& Plays() const { return Played; }
    void ForgetPlays() { Played.Reset(); }
    const FSoraMusicStatus& Music() const { return MusicNow; }
    // The ambience bed and weather bed looping now (none for silence), and the
    // place's weather.
    FName Bed() const { return BedCue; }
    FName WeatherBed() const { return WeatherCue; }
    FName Weather() const { return WeatherName; }
    // The stems of the piece now sounding whose voice is playing on the
    // device, neither fading out nor virtualised (none without a device);
    // muted stems keep theirs, sample-locked.
    TArray<FName> StemVoices() const;
    // A muted stem's gain (-80 dB). UAudioComponent::AdjustVolume to a level
    // within UE_SMALL_NUMBER of zero is a fade-out that stops the sound when
    // it ends, so a stem that left the mix would never come back; this stays
    // clear of that and far below hearing under the mix.
    static constexpr float MutedStemGain = .0001f;
    // The output gain the settings gave a bus's submix (1 before any).
    float SubmixGain(FName Bus) const;
    // The gain last sent to each bus's submix on the device: empty unless
    // settings attached to the engine (or DriveSubmixesForTesting) drive it.
    const TMap<FName, float>& DeviceSubmixGains() const { return DeviceGains; }
    // Slider and floored buses whose SMX_ submix did not load from the path
    // the runtime uses (an import missing or renamed).
    TArray<FName> MissingSubmixes() const;
    // Automation only: drive this world's submixes from detached settings as
    // attached ones would, so a device run checks the real path; false puts
    // every driven submix back to unity.
    void DriveSubmixesForTesting(bool bDrive);
    // Loops running now, by cue: beds, sustains, holds and loops on
    // opponents (a cue still without its sound runs silent).
    TArray<FName> LiveLoops() const;

    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    // Menus pause the world; their music and sounds keep going.
    virtual bool IsTickableWhenPaused() const override { return true; }
protected:
    virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
private:
    // A cue about to play, before the cue's own variation.
    struct FRequest
    {
        FName Family;
        FVector Location = FVector::ZeroVector;
        TWeakObjectPtr<AActor> Source;
        // Rides on Source instead of staying where it started.
        bool bAttach = false;
        // The hero made it: no caption unless the cue asks for one.
        bool bHero = false;
        float ExtraDb = 0.f;
        // The telegraph's windup after difficulty, to line its strike up.
        int32 WindupMs = 0;
        // An ambience bed: heard everywhere, whatever the cue's 3D preset.
        bool bBed = false;
        // Comes in over this long instead of starting at full level.
        float FadeInSeconds = 0.f;
        // Loops are kept under this key until stopped.
        FString LoopKey;
        // The rule that chose the cue (FSoraAudioPlay).
        FName RuleFamily;
        int32 Rule = INDEX_NONE;
        int32 ForwardedBy = INDEX_NONE;
    };
    struct FLoop
    {
        FName Cue;
        TWeakObjectPtr<UAudioComponent> Component;
        TWeakObjectPtr<AActor> Attach;
        FVector LastLocation = FVector::ZeroVector;
        bool bDoppler = false;
    };
    struct FSustainState
    {
        FName Cue;
        TWeakObjectPtr<AActor> Source;
        FVector Location = FVector::ZeroVector;
        double LastShot = 0.0;
        bool bLooping = false;
    };
    struct FPending
    {
        int32 Serial = 0;
        double Due = 0.0;
        FSoraAudioPlay Play;
        FString LoopKey;
        bool bAttach = false;
    };
    struct FPieceVoice
    {
        FName Piece;
        TMap<FName, TWeakObjectPtr<UAudioComponent>> Stems;
        TWeakObjectPtr<UAudioComponent> Intro;
        TWeakObjectPtr<UQuartzClockHandle> Clock;
        FName ClockName;
        double StopAt = 0.0;
    };
    struct FStride
    {
        FVector Last = FVector::ZeroVector;
        float Distance = 0.f;
    };
    struct FHoof
    {
        FVector Last = FVector::ZeroVector;
        float Beats = 0.f;
        bool bSpooked = false;
        TWeakObjectPtr<AActor> Rider;
    };
    struct FWeaponState
    {
        int32 WeaponId = INDEX_NONE;
        bool bReloading = false;
        bool bDrawing = false;
        bool bSheathed = false;
        bool bCharging = false;
        bool bHeld = false;
    };

    // Events.
    void WeaponFired(const FSoraWeaponFiredEvent& Event);
    void MeleeCommitted(const FSoraMeleeCommittedEvent& Event);
    void StrikeResolved(const FSoraStrikeResolvedEvent& Event);
    void Guarded(const FSoraDefenseEvent& Event);
    void Parried(const FSoraDefenseEvent& Event);
    void Marobashi(const FSoraMarobashiEvent& Event);
    void Damaged(const FSoraDamagedEvent& Event);
    void Died(const FSoraDiedEvent& Event);
    void Detonated(const FSoraDetonatedEvent& Event);
    void EnemyCue(const FSoraEnemyCueEvent& Event);
    void SiteRestored(const FSoraSiteRestoredEvent& Event);
    void ChapterStarted(const FSoraChapterEvent& Event);
    void ChapterCompleted(const FSoraChapterEvent& Event);
    void BossPhase(const FSoraBossPhaseEvent& Event);
    void BeatStarted(const FSoraBeatEvent& Event);
    void BeatCompleted(const FSoraBeatEvent& Event);
    void BeatFailed(const FSoraBeatEvent& Event);
    void KernelEvent(const FSoraPracticeEvent& Event, uint32 Tick);
    void UISound(ESoraUISound Sound);

    // Runs Family's rules on Facts; a matching rule plays its cue.
    void Dispatch(FName Family, const SoraAudioData::FFacts& Facts, const FRequest& Request);
    // Plays Cue now or after its delay; returns the record's index.
    int32 Play(FName Cue, const FRequest& Request, float RuleDelaySeconds = 0.f);
    UAudioComponent* Spawn(const FSoraAudioPlay& Play, bool bAttach);
    void StopLoop(const FString& Key, float FadeSeconds);
    bool IsLooping(const FString& Key) const;
    // A burst of sustained shots ended: its loop stops and its release plays.
    void EndSustain(const FString& Key, const FSustainState& State);
    USoundSubmix* SubmixFor(FName Bus);
    USoundWave* LoadWave(const FString& Wave);
    USoundAttenuation* AttenuationFor(FName Preset);
    USoundConcurrency* ConcurrencyFor(const SoraAudioData::FCue& Cue);
    USoundClass* ClassFor(FName Bus);
    int32 PickWave(const SoraAudioData::FCue& Cue);

    // Who and where.
    ASoraGameMode* Mode() const;
    bool IsHero(const AActor* Actor) const;
    FVector Listener() const;
    FName SparringWeapon() const;
    int32 DifficultyIndex() const;
    AActor* KernelPawn(int32 Slot) const;

    // Per frame.
    void BindSettings();
    void ApplyBusGains();
    void TickSustains(double Now);
    void TickPending(double Now);
    void TickMusic();
    void TickAmbience(double Now);
    void TickHero();
    void TickKernel();
    void TickFootsteps(float DeltaTime);
    void TickHorses(float DeltaTime);
    void TickAttached(double Now);
    void TickAmbientEmitters();
    void TickDoppler(float DeltaTime);
    FName SurfaceUnder(const AActor& Walker, const FVector& Feet) const;

    // Music.
    ESoraMusicState WantedMusic() const;
    FName WantedMix(ESoraMusicState State, TArray<FName>& Stems) const;
    void ChangeMusic(ESoraMusicState State, FName Mix, const TArray<FName>& Stems);
    void StartPiece(FName Piece, const TArray<FName>& Stems, bool bIntro, float FadeSeconds);
    void SetStemGains(float FadeSeconds);
    // MusicNow.StemGains for the piece, mix and bed gain now.
    void HoldStemGains();
    void FadeOutPiece(FPieceVoice& Voice, float FadeSeconds);
    bool StartStinger(FSoraAudioPlay& Record, const SoraAudioData::FCue& Cue);
    double MusicClock() const;

    // Ambience.
    const SoraAudioData::FPlace* WantedPlace() const;
    void SetBed(const FString& Key, FName Cue, FName& Current);

    TArray<FSoraAudioPlay> Played;
    TArray<FPending> Pending;
    int32 PendingSerial = 0;
    TMap<FString, FLoop> Loops;
    TMap<FString, TWeakObjectPtr<AActor>> AmbientOwners;
    TMap<FString, FSustainState> Sustains;
    TMap<FName, TArray<int32>> Decks;
    TMap<FName, int32> LastPick;
    FRandomStream Random{0x50A0D10};
    UPROPERTY() TMap<FName, TObjectPtr<USoundAttenuation>> AttenuationObjects;
    UPROPERTY() TMap<FName, TObjectPtr<USoundConcurrency>> ConcurrencyObjects;
    UPROPERTY() TMap<FString, TObjectPtr<USoundWave>> WaveObjects;
    UPROPERTY() TMap<FName, TObjectPtr<USoundClass>> ClassObjects;
    TSet<FString> MissingWaves;
    // Components this subsystem keeps alive: loops, stems and intros.
    UPROPERTY() TArray<TObjectPtr<UAudioComponent>> Held;
    UPROPERTY() TArray<TObjectPtr<UQuartzClockHandle>> Clocks;
    TArray<FDelegateHandle> Handles;
    bool bSubscribed = false;

    // Settings.
    TWeakObjectPtr<USoraSettings> BoundSettings;
    FDelegateHandle SettingsHandle;
    TMap<FName, float> SubmixGains;
    TMap<FName, float> DeviceGains;
    UPROPERTY() TMap<FName, TObjectPtr<USoundSubmix>> SubmixObjects;
    bool bDriveSubmixesForTesting = false;

    // Campaign context.
    FString BeatId;
    const SoraAudioData::FBeat* Beat = nullptr;
    TMap<TWeakObjectPtr<AActor>, int32> Alert;
    TWeakObjectPtr<AActor> Boss;
    int32 BossPhaseIndex = 0;
    bool bBossDefeated = false;

    // Music.
    FSoraMusicStatus MusicNow;
    TArray<FPieceVoice> Voices;
    double IntroEnds = 0.0;
    int32 ClockSerial = 0;

    // Ambience.
    FName BedCue;
    FName WeatherCue;
    FName WeatherName;
    int32 ThunderIndex = 0;
    double NextThunder = 0.0;

    // Polling.
    FWeaponState HeroWeapon;
    TArray<FWeaponState> KernelWeapons;
    TMap<TWeakObjectPtr<AActor>, FStride> Strides;
    TMap<TWeakObjectPtr<AActor>, FHoof> Hooves;
    TMap<TWeakObjectPtr<AActor>, FString> AttachedLoops;
    double NextAttachedScan = 0.0;
};
