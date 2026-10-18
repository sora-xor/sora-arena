#include "SoraAudio.h"
#include "ArenaKernelSubsystem.h"
#include "Audio/SoraAudioData.h"
#include "Audio/SoraAudioMath.h"
#include "AudioDevice.h"
#include "Components/AudioComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "SoraCaptions.h"
#include "SoraCatalog.h"
#include "SoraCharacterBase.h"
#include "SoraGameEvents.h"
#include "SoraGameMode.h"
#include "SoraPracticeDirector.h"
#include "SoraSettings.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundClass.h"
#include "Sound/SoundConcurrency.h"
#include "Sound/SoundSubmix.h"
#include "Sound/SoundWave.h"

DEFINE_LOG_CATEGORY_STATIC(LogSoraAudio, Log, All);

using namespace SoraAudioData;

namespace
{
// ARENA_EVENT_* 1-19 (crates/arena-ffi/include/arena.h).
const TCHAR* const KernelKinds[] = {TEXT("Shot"), TEXT("Damage"), TEXT("Death"), TEXT("Respawn"), TEXT("Terminal"),
    TEXT("Guarded"), TEXT("Healed"), TEXT("Ability"), TEXT("Marked"), TEXT("Riposte"), TEXT("EntitySpawned"),
    TEXT("EntityDamaged"), TEXT("EntityRepaired"), TEXT("EntityDestroyed"), TEXT("HazardDamage"),
    TEXT("ObjectiveCaptured"), TEXT("Overtime"), TEXT("Checkpoint"), TEXT("MatchWinner")};
constexpr uint32 KernelWinnerTeam = 1u, KernelWinnerSlot = 2u;
constexpr int32 MaxPlays = 512;

template <typename TEnum>
FString EnumName(TEnum Value)
{
    return StaticEnum<TEnum>()->GetNameStringByValue(static_cast<int64>(Value));
}

FString KernelWeaponKind(int32 WeaponId)
{
    const FSoraCatalog& Catalog = FSoraCatalog::Get();
    return Catalog.IsReady() && WeaponId >= 0 && WeaponId <= 20 ? Catalog.Weapon(WeaponId).Kind : FString();
}

FVector Where(const AActor* Actor, const FVector& Otherwise = FVector::ZeroVector)
{
    return Actor ? Actor->GetActorLocation() : Otherwise;
}
}

USoraAudioSubsystem* USoraAudioSubsystem::Get(const UObject* WorldContext)
{
    const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
    return World ? World->GetSubsystem<USoraAudioSubsystem>() : nullptr;
}

bool USoraAudioSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
    return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId USoraAudioSubsystem::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(USoraAudioSubsystem, STATGROUP_Tickables);
}

bool USoraAudioSubsystem::IsReady() const { return bSubscribed && FData::Get() != nullptr; }

bool USoraAudioSubsystem::HasDevice() const
{
    const UWorld* World = GetWorld();
    return GEngine && GEngine->UseSound() && World && World->GetAudioDeviceRaw() != nullptr;
}

void USoraAudioSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);
    if (!FData::Get())
    {
        static bool bReported = false;
        if (!bReported)
            UE_LOG(LogSoraAudio, Error, TEXT("SORA audio is silent: %s"), *FData::Error());
        bReported = true;
        return;
    }
    USoraGameEvents* Events = USoraGameEvents::Get(&InWorld);
    if (!Events)
        return;
    Handles = {
        Events->OnWeaponFired.AddUObject(this, &USoraAudioSubsystem::WeaponFired),
        Events->OnMeleeCommitted.AddUObject(this, &USoraAudioSubsystem::MeleeCommitted),
        Events->OnStrikeResolved.AddUObject(this, &USoraAudioSubsystem::StrikeResolved),
        Events->OnGuarded.AddUObject(this, &USoraAudioSubsystem::Guarded),
        Events->OnParried.AddUObject(this, &USoraAudioSubsystem::Parried),
        Events->OnMarobashi.AddUObject(this, &USoraAudioSubsystem::Marobashi),
        Events->OnDamaged.AddUObject(this, &USoraAudioSubsystem::Damaged),
        Events->OnDied.AddUObject(this, &USoraAudioSubsystem::Died),
        Events->OnDetonated.AddUObject(this, &USoraAudioSubsystem::Detonated),
        Events->OnEnemyCue.AddUObject(this, &USoraAudioSubsystem::EnemyCue),
        Events->OnSiteRestored.AddUObject(this, &USoraAudioSubsystem::SiteRestored),
        Events->OnChapterStarted.AddUObject(this, &USoraAudioSubsystem::ChapterStarted),
        Events->OnChapterCompleted.AddUObject(this, &USoraAudioSubsystem::ChapterCompleted),
        Events->OnBossPhase.AddUObject(this, &USoraAudioSubsystem::BossPhase),
        Events->OnBeatStarted.AddUObject(this, &USoraAudioSubsystem::BeatStarted),
        Events->OnBeatCompleted.AddUObject(this, &USoraAudioSubsystem::BeatCompleted),
        Events->OnBeatFailed.AddUObject(this, &USoraAudioSubsystem::BeatFailed),
        Events->OnKernelEvent.AddUObject(this, &USoraAudioSubsystem::KernelEvent),
        Events->OnUISound.AddUObject(this, &USoraAudioSubsystem::UISound),
    };
    bSubscribed = true;
}

void USoraAudioSubsystem::Deinitialize()
{
    if (USoraGameEvents* Events = bSubscribed ? USoraGameEvents::Get(GetWorld()) : nullptr)
    {
        FDelegateHandle* H = Handles.GetData();
        Events->OnWeaponFired.Remove(H[0]); Events->OnMeleeCommitted.Remove(H[1]); Events->OnStrikeResolved.Remove(H[2]);
        Events->OnGuarded.Remove(H[3]); Events->OnParried.Remove(H[4]); Events->OnMarobashi.Remove(H[5]);
        Events->OnDamaged.Remove(H[6]); Events->OnDied.Remove(H[7]); Events->OnDetonated.Remove(H[8]);
        Events->OnEnemyCue.Remove(H[9]); Events->OnSiteRestored.Remove(H[10]); Events->OnChapterStarted.Remove(H[11]);
        Events->OnChapterCompleted.Remove(H[12]); Events->OnBossPhase.Remove(H[13]); Events->OnBeatStarted.Remove(H[14]);
        Events->OnBeatCompleted.Remove(H[15]); Events->OnBeatFailed.Remove(H[16]); Events->OnKernelEvent.Remove(H[17]);
        Events->OnUISound.Remove(H[18]);
    }
    Handles.Reset();
    bSubscribed = false;
    if (bDriveSubmixesForTesting)
        DriveSubmixesForTesting(false);
    if (USoraSettings* Settings = BoundSettings.Get())
        Settings->OnChanged.Remove(SettingsHandle);
    BoundSettings.Reset();
    for (const TObjectPtr<UAudioComponent>& Component : Held)
        if (Component)
            Component->Stop();
    Held.Reset();
    Loops.Reset();
    Super::Deinitialize();
}

void USoraAudioSubsystem::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);
    UWorld* World = GetWorld();
    if (!IsReady() || !World)
        return;
    const double Now = World->GetTimeSeconds();
    BindSettings();
    TickPending(Now);
    TickSustains(Now);
    TickMusic();
    TickAmbience(Now);
    if (!World->IsPaused())
    {
        TickHero();
        TickKernel();
        TickFootsteps(DeltaTime);
        TickHorses(DeltaTime);
        TickAttached(Now);
        TickDoppler(DeltaTime);
    }
    // Finished one-shots and faded loops let go of their components.
    Held.RemoveAll([](const TObjectPtr<UAudioComponent>& Component) { return !Component || !Component->IsPlaying(); });
}

ASoraGameMode* USoraAudioSubsystem::Mode() const
{
    return GetWorld() ? Cast<ASoraGameMode>(GetWorld()->GetAuthGameMode()) : nullptr;
}

bool USoraAudioSubsystem::IsHero(const AActor* Actor) const
{
    return Actor && Actor == UGameplayStatics::GetPlayerPawn(this, 0);
}

FVector USoraAudioSubsystem::Listener() const
{
    if (APlayerController* Controller = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr)
    {
        FVector Location, Front, Right;
        Controller->GetAudioListenerPosition(Location, Front, Right);
        return Location;
    }
    return FVector::ZeroVector;
}

FName USoraAudioSubsystem::SparringWeapon() const
{
    const ASoraGameMode* Game = Mode();
    return Beat && Game && Game->bCampaign && !Game->bDeterministicPractice ? Beat->Sparring : NAME_None;
}

int32 USoraAudioSubsystem::DifficultyIndex() const
{
    return FMath::Clamp(static_cast<int32>(SoraAccessibility::CampaignDifficulty(this)), 0, 2);
}

AActor* USoraAudioSubsystem::KernelPawn(int32 Slot) const
{
    const ASoraGameMode* Game = Mode();
    return Game && Game->Practice() && Slot >= 0 && Slot < Game->Practice()->ParticipantCount() ? Game->Practice()->Participant(Slot) : nullptr;
}

float USoraAudioSubsystem::SubmixGain(FName Bus) const
{
    const float* Gain = SubmixGains.Find(Bus);
    return Gain ? *Gain : 1.f;
}

TArray<FName> USoraAudioSubsystem::MissingSubmixes() const
{
    TArray<FName> Out;
    for (const auto& Pair : SubmixGains)
        if (!SubmixObjects.Contains(Pair.Key))
            Out.Add(Pair.Key);
    return Out;
}

TArray<FName> USoraAudioSubsystem::LiveLoops() const
{
    TArray<FName> Out;
    for (const auto& Pair : Loops)
        Out.Add(Pair.Value.Cue);
    return Out;
}

// Settings ------------------------------------------------------------------

void USoraAudioSubsystem::BindSettings()
{
    ASoraGameMode* Game = Mode();
    USoraSettings* Settings = Game ? Game->Settings() : nullptr;
    if (Settings == BoundSettings.Get())
        return;
    if (USoraSettings* Old = BoundSettings.Get())
        Old->OnChanged.Remove(SettingsHandle);
    BoundSettings = Settings;
    if (Settings)
        SettingsHandle = Settings->OnChanged.AddUObject(this, &USoraAudioSubsystem::ApplyBusGains);
    ApplyBusGains();
}

void USoraAudioSubsystem::ApplyBusGains()
{
    const FData* D = FData::Get();
    USoraSettings* Settings = BoundSettings.Get();
    if (!D)
        return;
    const auto Slider = [Settings](int32 Index) { return Settings ? Settings->BusGain(static_cast<ESoraAudioBus>(Index)) : 1.f; };
    // Settings attached to the engine drive the device; automation's detached
    // settings only compute, so no test changes the editor's mix unless it
    // drives the submixes itself and puts them back.
    const bool bDevice = ((Settings && Settings->IsAttached()) || bDriveSubmixesForTesting) && HasDevice();
    for (const FBus& Bus : D->Buses)
    {
        float Gain = 1.f;
        if (Bus.Slider > static_cast<int32>(ESoraAudioBus::Master))
            Gain = Slider(Bus.Slider);
        else if (const FBus* Of = Bus.FloorOf.IsNone() ? nullptr : D->Bus(Bus.FloorOf))
            Gain = FMath::Max(Slider(Of->Slider), SoraAudioMath::DbToGain(Bus.FloorDb));
        else
            continue;
        SubmixGains.Add(Bus.Id, Gain);
        USoundSubmix* Submix = SubmixFor(Bus.Id);
        if (bDevice && Submix)
        {
            Submix->SetSubmixOutputVolume(GetWorld(), Gain);
            DeviceGains.Add(Bus.Id, Gain);
        }
    }
}

USoundSubmix* USoraAudioSubsystem::SubmixFor(FName Bus)
{
    if (const TObjectPtr<USoundSubmix>* Found = SubmixObjects.Find(Bus))
        return *Found;
    USoundSubmix* Submix = LoadObject<USoundSubmix>(nullptr, *SubmixObjectPath(Bus), nullptr, LOAD_NoWarn | LOAD_Quiet);
    if (Submix)
        SubmixObjects.Add(Bus, Submix);
    return Submix;
}

void USoraAudioSubsystem::DriveSubmixesForTesting(bool bDrive)
{
    bDriveSubmixesForTesting = bDrive;
    if (!bDrive)
    {
        for (const auto& Pair : DeviceGains)
            if (USoundSubmix* Submix = HasDevice() ? SubmixFor(Pair.Key) : nullptr)
                Submix->SetSubmixOutputVolume(GetWorld(), 1.f);
        DeviceGains.Reset();
    }
    ApplyBusGains();
}

// Rules and playback --------------------------------------------------------

void USoraAudioSubsystem::Dispatch(FName Family, const FFacts& Facts, const FRequest& Request)
{
    const FData* D = FData::Get();
    const TArray<FRule>* Rules = D ? D->Bindings.Find(Family) : nullptr;
    if (!Rules)
        return;
    for (int32 Index = 0; Index < Rules->Num(); ++Index)
    {
        const FRule& Rule = (*Rules)[Index];
        if (!Rule.Matches(Facts))
            continue;
        if (!Rule.Cue.IsNone())
        {
            FRequest Chosen = Request;
            Chosen.RuleFamily = Family;
            Chosen.Rule = Index;
            Play(Rule.Cue, Chosen, Rule.DelaySeconds);
        }
        if (!Rule.bContinue)
            return;
    }
}

void USoraAudioSubsystem::Hear(FName Family, const FFacts& Facts, AActor* Source, const FVector& Location)
{
    FRequest Request;
    Request.Family = Family;
    Request.Source = Source;
    Request.Location = Source ? Source->GetActorLocation() : Location;
    Request.bHero = IsHero(Source);
    Dispatch(Family, Facts, Request);
}

int32 USoraAudioSubsystem::PickWave(const FCue& Cue)
{
    const int32 Count = Cue.Waves.Num();
    int32& Last = LastPick.FindOrAdd(Cue.Id, INDEX_NONE);
    if (Count <= 1)
        return Last = 0;
    if (!Cue.bShuffle)
        return Last = (Last + 1) % Count;
    // Shuffle without repeats, and never the same wave twice across decks.
    TArray<int32>& Deck = Decks.FindOrAdd(Cue.Id);
    if (Deck.IsEmpty())
    {
        for (int32 Index = 0; Index < Count; ++Index)
            Deck.Add(Index);
        for (int32 Index = Count - 1; Index > 0; --Index)
            Deck.Swap(Index, Random.RandRange(0, Index));
        if (Deck.Last() == Last)
            Deck.Swap(0, Count - 1);
    }
    return Last = Deck.Pop();
}

int32 USoraAudioSubsystem::Play(FName CueId, const FRequest& Request, float RuleDelaySeconds)
{
    const FData* D = FData::Get();
    const FCue* Cue = D ? D->Cue(CueId) : nullptr;
    UWorld* World = GetWorld();
    if (!Cue || !World)
        return INDEX_NONE;
    const double Now = World->GetTimeSeconds();
    // A loop is always kept under a key, so a repeated rule never stacks it
    // and the world's end stops it.
    FRequest Keyed = Request;
    if (Cue->bLoop && Keyed.LoopKey.IsEmpty())
        Keyed.LoopKey = FString::Printf(TEXT("%s|%s"), *CueId.ToString(),
            Request.Source.IsValid() ? *Request.Source->GetPathName() : *Request.Family.ToString());
    if (!Keyed.LoopKey.IsEmpty() && IsLooping(Keyed.LoopKey))
        return INDEX_NONE;

    // A shot repeated within the sustain gap keeps its loop running instead.
    if (Cue->bSustain)
    {
        const FString Key = FString::Printf(TEXT("%s|%s"), *CueId.ToString(),
            Request.Source.IsValid() ? *Request.Source->GetPathName() : *Request.Location.ToString());
        FSustainState* State = Sustains.Find(Key);
        if (State && Now - State->LastShot <= Cue->Sustain.GapSeconds)
        {
            State->LastShot = Now;
            State->Location = Request.Location;
            if (!State->bLooping)
            {
                State->bLooping = true;
                FRequest Loop = Request;
                Loop.LoopKey = TEXT("sustain:") + Key;
                Loop.bAttach = Request.Source.IsValid();
                Play(Cue->Sustain.Loop, Loop);
            }
            return INDEX_NONE;
        }
        // A shot after the gap starts a new burst. Shooters tick before this
        // subsystem, so the last burst may not have been let go yet: let go
        // of it first, or its loop would run on with nothing to stop it.
        if (State)
        {
            const FSustainState Ended = *State;
            Sustains.Remove(Key);
            EndSustain(Key, Ended);
        }
        FSustainState& Fresh = Sustains.Add(Key);
        Fresh.Cue = CueId;
        Fresh.Source = Request.Source;
        Fresh.Location = Request.Location;
        Fresh.LastShot = Now;
    }

    FSoraAudioPlay Record;
    Record.Family = Request.Family;
    Record.Cue = CueId;
    Record.Bus = Cue->Bus;
    Record.Attenuation = Cue->Attenuation;
    Record.bSpatial = Cue->bSpatial && !Request.bBed;
    Record.bLoop = Cue->bLoop;
    Record.bStinger = Cue->bStinger;
    Record.Location = Request.Location;
    Record.Source = Request.Source;
    Record.FadeInSeconds = Request.FadeInSeconds;
    Record.RuleFamily = Request.RuleFamily;
    Record.Rule = Request.Rule;
    Record.ForwardedBy = Request.ForwardedBy;
    Record.Time = Now;
    if (Cue->IsVoiced())
        Record.Wave = Cue->Waves[PickWave(*Cue)];
    Record.Volume = SoraAudioMath::DbToGain(Random.FRandRange(Cue->VolumeDb[0], Cue->VolumeDb[1]) + Request.ExtraDb);
    Record.Pitch = FMath::Pow(2.f, Random.FRandRange(Cue->PitchCents[0], Cue->PitchCents[1]) / 1200.f);
    Record.DelaySeconds = RuleDelaySeconds;
    if (const FAttenuation* Preset = Record.bSpatial ? D->Attenuation.Find(Cue->Attenuation) : nullptr)
        if (Preset->bDistanceDelay)
            Record.DelaySeconds += FVector::Dist(Listener(), Request.Location) / SoraAudioMath::SpeedOfSoundCmS;
    // A telegraph's strike lands with the blow whatever the windup: held back
    // for a longer one, started part-way for a shorter one, never pitched.
    if (Cue->StrikeMs > 0 && Request.WindupMs > 0)
    {
        if (Request.WindupMs >= Cue->StrikeMs)
            Record.DelaySeconds += (Request.WindupMs - Cue->StrikeMs) / 1000.f;
        else
            Record.StartSeconds = (Cue->StrikeMs - Request.WindupMs) / 1000.f;
    }
    if (Cue->bStinger && !StartStinger(Record, *Cue))
        Record.bDropped = true;
    if (!Record.bDropped && Cue->IsVoiced() && !Cue->Caption.IsNone() && (!Request.bHero || Cue->bCaptionHero))
        if (USoraCaptions* Captions = USoraCaptions::Get(this))
        {
            Captions->Show(CaptionText(Cue->Caption), Record.bSpatial ? &Request.Location : nullptr, 3.f);
            Record.bCaptioned = true;
        }
    if (Played.Num() >= MaxPlays)
        Played.RemoveAt(0, Played.Num() - MaxPlays + 1);
    const int32 Index = Played.Add(Record);
    if (Record.bDropped)
        return Index;
    if (Cue->bLoop && !Keyed.LoopKey.IsEmpty())
    {
        FLoop& Loop = Loops.Add(Keyed.LoopKey);
        Loop.Cue = CueId;
        if (Request.bAttach)
            Loop.Attach = Request.Source;
        Loop.LastLocation = Request.Location;
        const FAttenuation* Preset = Record.bSpatial ? D->Attenuation.Find(Cue->Attenuation) : nullptr;
        Loop.bDoppler = Preset && Preset->bDoppler;
    }
    if (!Record.IsVoiced() || !HasDevice())
        return Index;
    if (Record.DelaySeconds > 0.f)
    {
        FPending& Wait = Pending.AddDefaulted_GetRef();
        Wait.Serial = ++PendingSerial;
        Wait.Due = Now + Record.DelaySeconds;
        Wait.Play = Record;
        Wait.LoopKey = Keyed.LoopKey;
        Wait.bAttach = Request.bAttach;
        return Index;
    }
    UAudioComponent* Component = Spawn(Record, Request.bAttach);
    Played[Index].Component = Component;
    if (FLoop* Loop = Keyed.LoopKey.IsEmpty() ? nullptr : Loops.Find(Keyed.LoopKey))
        Loop->Component = Component;
    return Index;
}

UAudioComponent* USoraAudioSubsystem::Spawn(const FSoraAudioPlay& Record, bool bAttach)
{
    UWorld* World = GetWorld();
    USoundWave* Wave = LoadWave(Record.Wave);
    const FCue* Cue = FData::Get() ? FData::Get()->Cue(Record.Cue) : nullptr;
    if (!World || !Wave || !Cue || !World->bAllowAudioPlayback)
        return nullptr;
    AActor* Carrier = Record.bSpatial && bAttach && Record.Source.IsValid() && Record.Source->GetRootComponent() ? Record.Source.Get() : nullptr;
    FAudioDevice::FCreateComponentParams Params(World, Carrier);
    if (Record.bSpatial && !Carrier)
        Params.SetLocation(Record.Location);
    Params.AttenuationSettings = Record.bSpatial ? AttenuationFor(Record.Attenuation) : nullptr;
    if (USoundConcurrency* Concurrency = ConcurrencyFor(*Cue))
        Params.ConcurrencySet.Add(Concurrency);
    UAudioComponent* Component = FAudioDevice::CreateComponent(Wave, Params);
    if (!Component)
        return nullptr;
    if (Carrier)
        Component->AttachToComponent(Carrier->GetRootComponent(), FAttachmentTransformRules::KeepRelativeTransform);
    else if (Record.bSpatial)
        Component->SetWorldLocation(Record.Location);
    Component->SetVolumeMultiplier(Record.Volume);
    Component->SetPitchMultiplier(Record.Pitch);
    Component->bAllowSpatialization = Record.bSpatial;
    // Menus pause the world; the interface and the music play on, the rest
    // pauses with it.
    Component->bIsUISound = !Record.bSpatial && (Cue->Bus == TEXT("UI") || Cue->Bus == TEXT("Music") || Cue->bStinger);
    // Every component goes when its sound ends, a loop once StopLoop's fade
    // is done, so none lingers on the world settings or its carrier.
    Component->bAutoDestroy = true;
    Component->bStopWhenOwnerDestroyed = Carrier != nullptr;
    // A wave imported for another bus's cue (the parry body layers under the
    // hero's hurt) still sounds on this cue's bus.
    USoundClass* Class = ClassFor(Cue->Bus);
    if (Class && Wave->SoundClassObject != Class)
        Component->SoundClassOverride = Class;
    if (Record.FadeInSeconds > 0.f)
        Component->FadeIn(Record.FadeInSeconds, 1.f, Record.StartSeconds);
    else
        Component->Play(Record.StartSeconds);
    if (Record.bLoop)
        Held.Add(Component);
    return Component;
}

USoundClass* USoraAudioSubsystem::ClassFor(FName Bus)
{
    if (const TObjectPtr<USoundClass>* Found = ClassObjects.Find(Bus))
        return *Found;
    USoundClass* Class = LoadObject<USoundClass>(nullptr, *FString::Printf(TEXT("/Game/Generated/Audio/Buses/SC_%s.SC_%s"), *Bus.ToString(),
        *Bus.ToString()), nullptr, LOAD_NoWarn | LOAD_Quiet);
    if (Class)
        ClassObjects.Add(Bus, Class);
    return Class;
}

void USoraAudioSubsystem::TickPending(double Now)
{
    for (int32 Index = 0; Index < Pending.Num();)
    {
        if (Pending[Index].Due > Now)
        {
            ++Index;
            continue;
        }
        const FPending Wait = Pending[Index];
        Pending.RemoveAt(Index);
        UAudioComponent* Component = Spawn(Wait.Play, Wait.bAttach);
        if (FLoop* Loop = Wait.LoopKey.IsEmpty() ? nullptr : Loops.Find(Wait.LoopKey))
            Loop->Component = Component;
        for (FSoraAudioPlay& Record : Played)
            if (Record.Cue == Wait.Play.Cue && Record.Time == Wait.Play.Time && !Record.Component.IsValid())
                Record.Component = Component;
    }
}

bool USoraAudioSubsystem::IsLooping(const FString& Key) const { return Loops.Contains(Key); }

void USoraAudioSubsystem::StopLoop(const FString& Key, float FadeSeconds)
{
    FLoop Loop;
    if (!Loops.RemoveAndCopyValue(Key, Loop))
        return;
    if (UAudioComponent* Component = Loop.Component.Get())
        Component->FadeOut(FMath::Max(FadeSeconds, .02f), 0.f);
}

void USoraAudioSubsystem::EndSustain(const FString& Key, const FSustainState& State)
{
    const FData* D = FData::Get();
    const FCue* Cue = D ? D->Cue(State.Cue) : nullptr;
    if (!Cue || !State.bLooping)
        return;
    StopLoop(TEXT("sustain:") + Key, .08f);
    FRequest Release;
    Release.Family = TEXT("Sustain");
    Release.Source = State.Source;
    Release.Location = State.Source.IsValid() ? State.Source->GetActorLocation() : State.Location;
    Release.bHero = IsHero(State.Source.Get());
    Play(Cue->Sustain.Release, Release);
}

void USoraAudioSubsystem::TickSustains(double Now)
{
    const FData* D = FData::Get();
    TArray<TPair<FString, FSustainState>> Ended;
    for (auto It = Sustains.CreateIterator(); It; ++It)
    {
        const FCue* Cue = D->Cue(It.Value().Cue);
        if (Cue && Now - It.Value().LastShot <= Cue->Sustain.GapSeconds)
            continue;
        Ended.Emplace(It.Key(), It.Value());
        It.RemoveCurrent();
    }
    for (const TPair<FString, FSustainState>& Burst : Ended)
        EndSustain(Burst.Key, Burst.Value);
}

USoundWave* USoraAudioSubsystem::LoadWave(const FString& Wave)
{
    if (Wave.IsEmpty() || MissingWaves.Contains(Wave))
        return nullptr;
    if (const TObjectPtr<USoundWave>* Found = WaveObjects.Find(Wave))
        return *Found;
    USoundWave* Loaded = LoadObject<USoundWave>(nullptr, *WaveObjectPath(Wave), nullptr, LOAD_NoWarn | LOAD_Quiet);
    if (!Loaded)
    {
        MissingWaves.Add(Wave);
        UE_LOG(LogSoraAudio, Display, TEXT("SORA audio: %s is not imported (scripts/toolchain/import-mac.sh)"), *Wave);
        return nullptr;
    }
    WaveObjects.Add(Wave, Loaded);
    return Loaded;
}

USoundAttenuation* USoraAudioSubsystem::AttenuationFor(FName Preset)
{
    if (const TObjectPtr<USoundAttenuation>* Found = AttenuationObjects.Find(Preset))
        return *Found;
    const FAttenuation* Data = FData::Get() ? FData::Get()->Attenuation.Find(Preset) : nullptr;
    if (!Data)
        return nullptr;
    // Outside the world: sounds still fading on a shared device when the world
    // ends keep their settings alive, never the world.
    USoundAttenuation* Object = NewObject<USoundAttenuation>(GetTransientPackage(), NAME_None, RF_Transient);
    FSoundAttenuationSettings& S = Object->Attenuation;
    S.bAttenuate = true;
    S.bSpatialize = true;
    S.AttenuationShape = EAttenuationShape::Sphere;
    S.AttenuationShapeExtents = FVector(Data->InnerCm, 0.f, 0.f);
    S.FalloffDistance = Data->FalloffCm;
    S.DistanceAlgorithm = EAttenuationDistanceModel::NaturalSound;
    S.bAttenuateWithLPF = Data->LowPassFarHz > 0.f;
    S.LPFRadiusMin = Data->InnerCm;
    S.LPFRadiusMax = Data->InnerCm + Data->FalloffCm;
    S.LPFFrequencyAtMin = 20000.f;
    S.LPFFrequencyAtMax = Data->LowPassFarHz > 0.f ? Data->LowPassFarHz : 20000.f;
    S.bEnableReverbSend = Data->bReverbSend;
    AttenuationObjects.Add(Preset, Object);
    return Object;
}

USoundConcurrency* USoraAudioSubsystem::ConcurrencyFor(const FCue& Cue)
{
    if (const TObjectPtr<USoundConcurrency>* Found = ConcurrencyObjects.Find(Cue.Id))
        return *Found;
    USoundConcurrency* Object = NewObject<USoundConcurrency>(GetTransientPackage(), NAME_None, RF_Transient);
    Object->Concurrency.MaxCount = Cue.MaxInstances;
    Object->Concurrency.bLimitToOwner = false;
    Object->Concurrency.ResolutionRule = Cue.bSpatial ? EMaxConcurrentResolutionRule::StopFarthestThenOldest : EMaxConcurrentResolutionRule::StopOldest;
    ConcurrencyObjects.Add(Cue.Id, Object);
    return Object;
}

// Events --------------------------------------------------------------------

void USoraAudioSubsystem::WeaponFired(const FSoraWeaponFiredEvent& Event)
{
    FFacts Facts;
    Facts.Int(TEXT("WeaponId"), Event.WeaponId).Text(TEXT("Kind"), EnumName(Event.Kind)).Flag(TEXT("ShooterIsHero"), IsHero(Event.Shooter));
    FRequest Request;
    Request.Family = TEXT("WeaponFired");
    Request.Location = Event.Origin;
    Request.Source = Event.Shooter.Get();
    Request.bHero = IsHero(Event.Shooter);
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::MeleeCommitted(const FSoraMeleeCommittedEvent& Event)
{
    FFacts Facts;
    Facts.Int(TEXT("WeaponId"), Event.WeaponId).Number(TEXT("WindupSeconds"), Event.WindupSeconds)
        .Flag(TEXT("AttackerIsHero"), IsHero(Event.Attacker)).Text(TEXT("Sparring"), SparringWeapon().IsNone() ? FString() : SparringWeapon().ToString());
    FRequest Request;
    Request.Family = TEXT("MeleeCommitted");
    Request.Location = Where(Event.Attacker);
    Request.Source = Event.Attacker.Get();
    Request.bHero = IsHero(Event.Attacker);
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::StrikeResolved(const FSoraStrikeResolvedEvent& Event)
{
    FFacts Facts;
    Facts.Int(TEXT("WeaponId"), Event.WeaponId).Flag(TEXT("bHit"), Event.bHit).Number(TEXT("Damage"), Event.Damage)
        .Flag(TEXT("AttackerIsHero"), IsHero(Event.Attacker)).Flag(TEXT("TargetIsHero"), IsHero(Event.Target))
        .Text(TEXT("Sparring"), SparringWeapon().IsNone() ? FString() : SparringWeapon().ToString());
    FRequest Request;
    Request.Family = TEXT("StrikeResolved");
    Request.Location = Where(Event.Target, Where(Event.Attacker));
    Request.Source = Event.Target ? Event.Target.Get() : Event.Attacker.Get();
    Request.bHero = IsHero(Event.Attacker);
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::Guarded(const FSoraDefenseEvent& Event)
{
    FFacts Facts;
    Facts.Flag(TEXT("bDojo"), Event.bDojo).Int(TEXT("HeldMs"), Event.HeldMs).Number(TEXT("Damage"), Event.Damage)
        .Flag(TEXT("DefenderIsHero"), IsHero(Event.Defender)).Flag(TEXT("AttackerIsHero"), IsHero(Event.Attacker));
    FRequest Request;
    Request.Family = TEXT("Guarded");
    Request.Location = Where(Event.Defender);
    Request.Source = Event.Defender.Get();
    Request.bHero = IsHero(Event.Defender);
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::Parried(const FSoraDefenseEvent& Event)
{
    FFacts Facts;
    Facts.Flag(TEXT("bDojo"), Event.bDojo).Int(TEXT("HeldMs"), Event.HeldMs).Number(TEXT("Damage"), Event.Damage)
        .Flag(TEXT("DefenderIsHero"), IsHero(Event.Defender)).Flag(TEXT("AttackerIsHero"), IsHero(Event.Attacker));
    FRequest Request;
    Request.Family = TEXT("Parried");
    Request.Location = Where(Event.Defender);
    Request.Source = Event.Defender.Get();
    Request.bHero = IsHero(Event.Defender);
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::Marobashi(const FSoraMarobashiEvent& Event)
{
    FFacts Facts;
    Facts.Flag(TEXT("bAfterAwase"), Event.bAfterAwase);
    FRequest Request;
    Request.Family = TEXT("Marobashi");
    Request.Location = Where(Event.Hero);
    Request.Source = Event.Hero.Get();
    Request.bHero = true;
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::Damaged(const FSoraDamagedEvent& Event)
{
    FFacts Facts;
    Facts.Flag(TEXT("VictimIsHero"), IsHero(Event.Victim)).Flag(TEXT("CauserIsHero"), IsHero(Event.Causer))
        .Number(TEXT("Amount"), Event.Amount).Number(TEXT("HealthAfter"), Event.HealthAfter);
    FRequest Request;
    Request.Family = TEXT("Damaged");
    Request.Location = Where(Event.Victim);
    Request.Source = Event.Victim.Get();
    Request.bHero = IsHero(Event.Victim);
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::Died(const FSoraDiedEvent& Event)
{
    Alert.Remove(Event.Victim.Get());
    FFacts Facts;
    Facts.Flag(TEXT("VictimIsHero"), IsHero(Event.Victim)).Flag(TEXT("KillerIsHero"), IsHero(Event.Killer)).Flag(TEXT("bSparring"), Event.bSparring);
    FRequest Request;
    Request.Family = TEXT("Died");
    Request.Location = Where(Event.Victim);
    Request.Source = Event.Victim.Get();
    Request.bHero = IsHero(Event.Victim);
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::Detonated(const FSoraDetonatedEvent& Event)
{
    FFacts Facts;
    Facts.Number(TEXT("Radius"), Event.Radius).Number(TEXT("Damage"), Event.Damage);
    FRequest Request;
    Request.Family = TEXT("Detonated");
    Request.Location = Event.Location;
    Request.bHero = IsHero(Event.Instigator);
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::EnemyCue(const FSoraEnemyCueEvent& Event)
{
    const FData* D = FData::Get();
    const FString Detail = Event.Detail.IsNone() ? FString() : Event.Detail.ToString();
    if (Event.Cue == ESoraEnemyCue::AlertState && Event.Enemy)
        Alert.Add(Event.Enemy.Get(), D->AlertLevels.FindRef(Event.Detail));
    const FTelegraph* Telegraph = Event.Cue == ESoraEnemyCue::AttackWindup ? D->EnemyTelegraphs.Find(Event.Detail) : nullptr;
    FFacts Facts;
    Facts.Text(TEXT("Cue"), EnumName(Event.Cue)).Text(TEXT("Archetype"), Event.Archetype.ToString()).Text(TEXT("Detail"), Detail)
        .Text(TEXT("Telegraph"), Telegraph ? Telegraph->Class.ToString() : TEXT("none"));
    FRequest Request;
    Request.Family = TEXT("EnemyCue");
    Request.Location = Where(Event.Enemy);
    Request.Source = Event.Enemy.Get();
    Request.WindupMs = Telegraph ? Telegraph->WindupMs * D->WindupPermille[DifficultyIndex()] / 1000 : 0;
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::SiteRestored(const FSoraSiteRestoredEvent& Event)
{
    FFacts Facts;
    Facts.Int(TEXT("ChapterId"), Event.ChapterId).Int(TEXT("SiteIndex"), Event.SiteIndex).Text(TEXT("Kind"), Event.Kind)
        .Flag(TEXT("bCampaign"), Event.bCampaign);
    FRequest Request;
    Request.Family = TEXT("SiteRestored");
    Request.Location = Listener();
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::ChapterStarted(const FSoraChapterEvent& Event)
{
    Alert.Reset();
    Boss.Reset();
    bBossDefeated = false;
    FFacts Facts;
    Facts.Int(TEXT("ChapterId"), Event.ChapterId).Flag(TEXT("bResumed"), Event.bResumed).Flag(TEXT("bLiberated"), Event.bLiberated);
    FRequest Request;
    Request.Family = TEXT("ChapterStarted");
    Request.Location = Listener();
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::ChapterCompleted(const FSoraChapterEvent& Event)
{
    FFacts Facts;
    Facts.Int(TEXT("ChapterId"), Event.ChapterId).Flag(TEXT("bResumed"), Event.bResumed).Flag(TEXT("bLiberated"), Event.bLiberated);
    FRequest Request;
    Request.Family = TEXT("ChapterCompleted");
    Request.Location = Listener();
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::BossPhase(const FSoraBossPhaseEvent& Event)
{
    const FData* D = FData::Get();
    switch (Event.Phase)
    {
    case ESoraBossPhase::Arrived:
        Boss = Event.Boss.Get();
        BossPhaseIndex = Event.PhaseIndex;
        bBossDefeated = false;
        break;
    case ESoraBossPhase::PhaseChanged:
        BossPhaseIndex = Event.PhaseIndex;
        break;
    case ESoraBossPhase::Defeated:
        bBossDefeated = true;
        break;
    default:
        break;
    }
    FName Class = TEXT("none");
    if (Event.Phase == ESoraBossPhase::Windup || Event.Phase == ESoraBossPhase::Strike)
    {
        const FTelegraph* Telegraph = D->BossTelegraphs.Find(Event.BossId.ToString() + TEXT("/") + Event.Detail.ToString());
        Class = Event.bBeam ? FName(TEXT("lock")) : Telegraph ? Telegraph->Class : Class;
    }
    FFacts Facts;
    Facts.Text(TEXT("Phase"), EnumName(Event.Phase)).Flag(TEXT("bBeam"), Event.bBeam).Text(TEXT("BossId"), Event.BossId.ToString())
        .Int(TEXT("PhaseIndex"), Event.PhaseIndex).Text(TEXT("Detail"), Event.Detail.IsNone() ? FString() : Event.Detail.ToString())
        .Text(TEXT("Telegraph"), Class.ToString()).Int(TEXT("WindupMs"), Event.WindupMs);
    FRequest Request;
    Request.Family = TEXT("BossPhase");
    Request.Location = Where(Event.Boss, Listener());
    Request.Source = Event.Boss.Get();
    Request.WindupMs = Event.Phase == ESoraBossPhase::Windup ? Event.WindupMs : 0;
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::BeatStarted(const FSoraBeatEvent& Event)
{
    const FData* D = FData::Get();
    if (Event.BeatId != BeatId)
    {
        Alert.Reset();
        if (!Boss.IsValid() || bBossDefeated)
        {
            Boss.Reset();
            bBossDefeated = false;
        }
    }
    BeatId = Event.BeatId;
    Beat = D->Beats.Find(Event.BeatId);
    FFacts Facts;
    Facts.Int(TEXT("ChapterId"), Event.ChapterId).Text(TEXT("BeatId"), Event.BeatId).Flag(TEXT("bResumed"), Event.bResumed)
        .Int(TEXT("Phase"), Event.Phase).Flag(TEXT("bOptional"), Event.bOptional);
    FRequest Request;
    Request.Family = TEXT("BeatStarted");
    Request.Location = Listener();
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::BeatCompleted(const FSoraBeatEvent& Event)
{
    FFacts Facts;
    Facts.Int(TEXT("ChapterId"), Event.ChapterId).Text(TEXT("BeatId"), Event.BeatId).Flag(TEXT("bResumed"), Event.bResumed)
        .Int(TEXT("Phase"), Event.Phase).Flag(TEXT("bOptional"), Event.bOptional);
    FRequest Request;
    Request.Family = TEXT("BeatCompleted");
    Request.Location = Listener();
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::BeatFailed(const FSoraBeatEvent& Event)
{
    FFacts Facts;
    Facts.Int(TEXT("ChapterId"), Event.ChapterId).Text(TEXT("BeatId"), Event.BeatId).Flag(TEXT("bResumed"), Event.bResumed)
        .Int(TEXT("Phase"), Event.Phase).Flag(TEXT("bOptional"), Event.bOptional);
    FRequest Request;
    Request.Family = TEXT("BeatFailed");
    Request.Location = Listener();
    Dispatch(Request.Family, Facts, Request);
}

void USoraAudioSubsystem::KernelEvent(const FSoraPracticeEvent& Event, uint32 Tick)
{
    (void)Tick;
    const FData* D = FData::Get();
    if (Event.Kind < 1 || Event.Kind > UE_ARRAY_COUNT(KernelKinds))
        return;
    const ASoraGameMode* Game = Mode();
    const UArenaKernelSubsystem* Kernel = Game ? Game->Kernel() : nullptr;
    const FString WeaponKind = KernelWeaponKind(Event.WeaponId);
    // The player is slot 0: a match won by that slot or by its team.
    const bool bHeroWon = Event.Kind == 19u && ((Event.Detail == KernelWinnerSlot && Event.Value == 0) ||
        (Event.Detail == KernelWinnerTeam && Kernel && Kernel->PracticePlayers.Num() > 0 && Event.Value == Kernel->PracticePlayers[0].Team));
    FFacts Facts;
    Facts.Text(TEXT("Kind"), KernelKinds[Event.Kind - 1]).Int(TEXT("WeaponId"), Event.WeaponId).Text(TEXT("WeaponKind"), WeaponKind)
        .Flag(TEXT("ActorIsHero"), Event.Actor == 0).Flag(TEXT("TargetIsHero"), Event.Target == 0)
        .Int(TEXT("Detail"), static_cast<int32>(Event.Detail)).Flag(TEXT("HeroWon"), bHeroWon);
    FRequest Request;
    Request.Family = TEXT("Kernel");
    const bool bAtTarget = Event.Kind == 2u || Event.Kind == 3u || Event.Kind == 6u || Event.Kind == 10u || Event.Kind == 15u;
    AActor* Pawn = KernelPawn(bAtTarget ? Event.Target : Event.Actor);
    Request.Source = Pawn;
    Request.Location = !Event.From.IsNearlyZero() && !bAtTarget ? Event.From : Pawn ? Pawn->GetActorLocation() : Event.To;
    Request.bHero = (bAtTarget ? Event.Target : Event.Actor) == 0;
    const TArray<FRule>* Rules = D->Bindings.Find(Request.Family);
    for (int32 Index = 0; Rules && Index < Rules->Num(); ++Index)
    {
        const FRule& Rule = (*Rules)[Index];
        if (!Rule.Matches(Facts))
            continue;
        if (!Rule.Cue.IsNone())
        {
            FRequest Chosen = Request;
            Chosen.RuleFamily = Request.Family;
            Chosen.Rule = Index;
            Play(Rule.Cue, Chosen, Rule.DelaySeconds);
        }
        else if (!Rule.As.IsNone())
        {
            // The event as the family it forwards to would carry it.
            FFacts As;
            const FString As_ = Rule.As.ToString();
            if (As_ == TEXT("WeaponFired"))
                As.Int(TEXT("WeaponId"), Event.WeaponId)
                    .Text(TEXT("Kind"), WeaponKind == TEXT("explosive") ? TEXT("Shell") : WeaponKind == TEXT("bow") ? TEXT("Arrow") : TEXT("Hitscan"))
                    .Flag(TEXT("ShooterIsHero"), Event.Actor == 0);
            else if (As_ == TEXT("MeleeCommitted"))
                As.Int(TEXT("WeaponId"), Event.WeaponId).Number(TEXT("WindupSeconds"), 0.0).Flag(TEXT("AttackerIsHero"), Event.Actor == 0)
                    .Text(TEXT("Sparring"), FString());
            else if (As_ == TEXT("Damaged"))
                As.Flag(TEXT("VictimIsHero"), Event.Target == 0).Flag(TEXT("CauserIsHero"), Event.Actor == 0).Number(TEXT("Amount"), Event.Value)
                    .Number(TEXT("HealthAfter"), Kernel && Kernel->PracticePlayers.IsValidIndex(Event.Target) ? Kernel->PracticePlayers[Event.Target].Health : 0);
            else if (As_ == TEXT("Died"))
                As.Flag(TEXT("VictimIsHero"), Event.Target == 0).Flag(TEXT("KillerIsHero"), Event.Actor == 0).Flag(TEXT("bSparring"), false);
            else
                As.Flag(TEXT("bDojo"), false).Int(TEXT("HeldMs"), 0).Number(TEXT("Damage"), 0.0)
                    .Flag(TEXT("DefenderIsHero"), Event.Target == 0).Flag(TEXT("AttackerIsHero"), Event.Actor == 0);
            FRequest Forwarded = Request;
            Forwarded.ForwardedBy = Index;
            Dispatch(Rule.As, As, Forwarded);
        }
        if (!Rule.bContinue)
            return;
    }
}

void USoraAudioSubsystem::UISound(ESoraUISound Sound)
{
    FFacts Facts;
    Facts.Text(TEXT("Sound"), EnumName(Sound));
    FRequest Request;
    Request.Family = TEXT("UI");
    Request.Location = Listener();
    Dispatch(Request.Family, Facts, Request);
}
