#include "SoraAudio.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "ArenaKernelSubsystem.h"
#include "Audio/SoraAudioData.h"
#include "AudioDevice.h"
#include "Components/AudioComponent.h"
#include "HUD/SoraHUDPanels.h"
#include "SoraCaptions.h"
#include "SoraEnemy.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraHorse.h"
#include "SoraHUD.h"
#include "SoraPlayerCharacter.h"
#include "SoraSettings.h"
#include "Sound/SoundClass.h"
#include "Sound/SoundWave.h"
#include "UI/SoraFrontEndTesting.h"

// The game's sound in standalone game worlds: every rule of Content/Data/
// audio.json plays its cue from the event it names, with an imported wave in
// its bus's class; the volume settings set the submix gains and the telegraph
// floor; the music moves between menu, exploration, stealth, combat and boss
// with its stems and stingers; the ambience follows place and weather; sound
// captions reach the caption panel in Japanese and English while the setting
// is on; and the front end sounds its keys. Headless automation has no audio
// device, so what played is the subsystem's record; with a device each voiced
// cue must also be playing.
namespace SoraAudioTests
{
using namespace SoraFrontEndTests;
using SoraAudioData::FData;
using SoraAudioData::FFacts;

bool EnterPlay(FScope& Scope)
{
    Scope.Key(EKeys::Enter);
    Scope.Key(EKeys::Enter);
    Scope.Key(EKeys::Enter);
    return Scope.Test.TestTrue(TEXT("The round is in play"), Scope.Mode()->IsPlaying());
}

FString Join(const TArray<FName>& Names)
{
    TArray<FString> Out;
    for (const FName& Name : Names)
        Out.Add(Name.ToString());
    return FString::Join(Out, TEXT(", "));
}

// The first beat of a music state, from the data.
FString BeatIn(const TCHAR* State)
{
    const FData* D = FData::Get();
    TArray<FString> Ids;
    for (const auto& Pair : D->Beats)
        if (Pair.Value.State == State)
            Ids.Add(Pair.Key);
    Ids.Sort();
    return Ids.IsEmpty() ? FString() : Ids[0];
}

// Raises an event and checks exactly which cues it played; every voiced
// cue's wave must be imported in its bus's class, and playing where there is
// a device. Remembers each family's cues for the coverage check.
struct FProbe
{
    FAutomationTestBase& Test;
    USoraAudioSubsystem& Audio;
    TSet<FString> Covered;

    void Expect(const FString& What, TFunctionRef<void()> Raise, std::initializer_list<const TCHAR*> Cues)
    {
        Audio.ForgetPlays();
        Raise();
        TArray<FName> Got, Wanted;
        for (const TCHAR* Cue : Cues)
            Wanted.Add(Cue);
        for (const FSoraAudioPlay& Play : Audio.Plays())
        {
            Got.Add(Play.Cue);
            Covered.Add(Play.Family.ToString() + TEXT("|") + Play.Cue.ToString());
            const SoraAudioData::FCue* Cue = FData::Get()->Cue(Play.Cue);
            if (!Play.IsVoiced())
            {
                Test.TestTrue(*FString::Printf(TEXT("%s: %s plays nothing only while its sound is still needed"), *What, *Play.Cue.ToString()),
                    Cue && !Cue->IsVoiced() && !Cue->Needs.IsEmpty());
                continue;
            }
            const USoundWave* Wave = LoadObject<USoundWave>(nullptr, *SoraAudioData::WaveObjectPath(Play.Wave), nullptr, LOAD_NoWarn | LOAD_Quiet);
            const FString Class = FString::Printf(TEXT("SC_%s"), *Play.Bus.ToString());
            Test.TestTrue(*FString::Printf(TEXT("%s: %s is an imported wave of %s on %s"), *What, *Play.Wave, *Play.Cue.ToString(), *Class),
                Wave && Wave->SoundClassObject && Cue && Cue->Waves.Contains(Play.Wave) && Cue->Bus == Play.Bus);
            // A short 3D one-shot out of earshot of the device's listener is
            // culled at creation; everything else must be sounding.
            const SoraAudioData::FAttenuation* Preset = Play.bSpatial ? FData::Get()->Attenuation.Find(Play.Attenuation) : nullptr;
            const FAudioDevice* Device = Audio.GetWorld() ? Audio.GetWorld()->GetAudioDeviceRaw() : nullptr;
            float SquaredDistance = 0.f;
            const bool bInEarshot = !Preset || (Device && Device->GetDistanceSquaredToNearestListener(Play.Location, SquaredDistance) &&
                SquaredDistance < FMath::Square(Preset->InnerCm + Preset->FalloffCm));
            if (Audio.HasDevice() && !Play.bDropped && Play.DelaySeconds <= 0.f && bInEarshot)
            {
                const UAudioComponent* Component = Play.Component.Get();
                const USoundClass* Routed = Component ? (Component->SoundClassOverride ? Component->SoundClassOverride.Get() : Wave->SoundClassObject.Get()) : nullptr;
                Test.TestTrue(*FString::Printf(TEXT("%s: %s is playing on the device in %s"), *What, *Play.Cue.ToString(), *Class),
                    Component && Component->IsPlaying() && Routed && Routed->GetName() == Class);
            }
        }
        Test.TestTrue(*FString::Printf(TEXT("%s plays [%s] (played [%s])"), *What, *Join(Wanted), *Join(Got)), Got == Wanted);
    }
};

FSoraPracticeEvent Kernel(uint32 Kind, int32 Actor, int32 Target, int32 WeaponId = 0, uint32 Detail = 0, int32 Value = 0)
{
    FSoraPracticeEvent Event;
    Event.Kind = Kind;
    Event.Actor = Actor;
    Event.Target = Target;
    Event.WeaponId = WeaponId;
    Event.Detail = Detail;
    Event.Value = Value;
    Event.From = FVector(100.f, 0.f, 150.f);
    Event.To = FVector(900.f, 0.f, 150.f);
    return Event;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraAudioDataTest,
    "SoraArena.Audio.Data",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraAudioDataTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using SoraAudioData::FData;
    const FData* D = FData::Get();
    if (!TestNotNull(*FString::Printf(TEXT("Content/Data/audio.json loads (%s)"), *FData::Error()), D))
        return false;
    int32 Voiced = 0, Waves = 0, Overridden = 0;
    for (const auto& Pair : D->Cues)
    {
        const SoraAudioData::FCue& Cue = Pair.Value;
        Voiced += Cue.IsVoiced();
        for (const FString& Path : Cue.Waves)
        {
            ++Waves;
            const USoundWave* Wave = LoadObject<USoundWave>(nullptr, *SoraAudioData::WaveObjectPath(Path), nullptr, LOAD_NoWarn | LOAD_Quiet);
            if (!TestNotNull(*FString::Printf(TEXT("%s: %s is imported (scripts/toolchain/import-mac.sh)"), *Pair.Key.ToString(), *Path), Wave))
                continue;
            // A wave sits in the class of the ready cues that share it; a cue
            // on another bus reaches its own class through an override.
            TestTrue(*FString::Printf(TEXT("%s: %s has a bus class and loops only as its cue does"), *Pair.Key.ToString(), *Path),
                Wave->SoundClassObject && Wave->SoundClassObject->GetName().StartsWith(TEXT("SC_")) && Wave->bLooping == Cue.bLoop);
            Overridden += Wave->SoundClassObject && Wave->SoundClassObject->GetName() != TEXT("SC_") + Cue.Bus.ToString();
        }
        TestTrue(*FString::Printf(TEXT("%s: a telegraph's strike mark falls inside its waves"), *Pair.Key.ToString()), Cue.StrikeMs == 0 ||
            Cue.Bus == TEXT("SFX_Telegraph"));
    }
    for (const auto& Pair : D->Pieces)
        for (const TPair<FName, FString>& Stem : Pair.Value.Stems)
        {
            const USoundWave* Wave = LoadObject<USoundWave>(nullptr, *SoraAudioData::WaveObjectPath(Stem.Value), nullptr, LOAD_NoWarn | LOAD_Quiet);
            TestTrue(*FString::Printf(TEXT("Music %s stem %s is an imported loop of whole bars"), *Pair.Key.ToString(), *Stem.Key.ToString()), Wave &&
                Wave->bLooping && FMath::IsNearlyZero(FMath::Fmod(Wave->Duration / Pair.Value.BarSeconds() + .0005f, 1.f), .002f));
        }
    for (const TCHAR* Family : {TEXT("WeaponFired"), TEXT("MeleeCommitted"), TEXT("StrikeResolved"), TEXT("Guarded"), TEXT("Parried"),
             TEXT("Marobashi"), TEXT("Damaged"), TEXT("Died"), TEXT("Detonated"), TEXT("EnemyCue"), TEXT("SiteRestored"),
             TEXT("ChapterStarted"), TEXT("ChapterCompleted"), TEXT("BossPhase"), TEXT("BeatStarted"), TEXT("BeatCompleted"),
             TEXT("BeatFailed"), TEXT("Kernel"), TEXT("UI"), TEXT("Hero"), TEXT("Footstep"), TEXT("Horse")})
        TestTrue(*FString::Printf(TEXT("The %s family has its rules"), Family), D->Bindings.Contains(Family));
    UE_LOG(LogTemp, Display, TEXT("SORA_AUDIO_DATA_OK: cues=%d voiced=%d waves=%d class_overrides=%d beats=%d"), D->Cues.Num(), Voiced, Waves,
        Overridden, D->Beats.Num());
    TestEqual(TEXT("Only the hero's hurt borrows waves from another bus (the parry body layers)"), Overridden, 2);
    return TestTrue(TEXT("Every campaign beat has its music and ambience"), D->Beats.Num() == 133 && D->Maps.Num() == 4);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraAudioEventsTest,
    "SoraArena.Audio.EventsPlayCues",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraAudioEventsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraAudioTests;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FScope Scope(*this, TEXT("AudioEvents"));
    if (!Scope.Start() || !EnterPlay(Scope))
        return false;
    UWorld* World = Scope.World->GetTestWorld();
    USoraAudioSubsystem* Audio = USoraAudioSubsystem::Get(World);
    USoraGameEvents* Events = USoraGameEvents::Get(World);
    ASoraPlayerCharacter* Hero = Scope.World->Player();
    if (!TestNotNull(TEXT("The world has its audio"), Audio) || !TestTrue(TEXT("The audio data is loaded"), Audio->IsReady()) ||
        !TestNotNull(TEXT("The world has game events"), Events))
        return false;
    AActor* Other = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform(Hero->GetActorLocation() + FVector(600.f, 0.f, 0.f)));
    AActor* Boss = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform(Hero->GetActorLocation() + FVector(900.f, 0.f, 0.f)));
    FProbe Probe{*this, *Audio};
    const auto Beat = [&](const TCHAR* Id, bool bResumed = false)
    {
        return [&, Id, bResumed]()
        {
            FSoraBeatEvent Started;
            Started.BeatId = Id; Started.bResumed = bResumed;
            Events->OnBeatStarted.Broadcast(Started);
        };
    };
    // Outside any sparring beat, whatever the dojo is doing.
    Beat(TEXT("ch02.b02"))();

    // Weapons: each catalog weapon's shot, a boss's round and its beam.
    const auto Shot = [&](int32 WeaponId, ESoraShotKind Kind, AActor* Shooter)
    {
        return [&, WeaponId, Kind, Shooter]()
        {
            FSoraWeaponFiredEvent Fired;
            Fired.Shooter = Shooter; Fired.WeaponId = WeaponId; Fired.Kind = Kind; Fired.Origin = Shooter->GetActorLocation();
            Events->OnWeaponFired.Broadcast(Fired);
        };
    };
    const TPair<int32, const TCHAR*> Guns[] = {{1, TEXT("weapon.fired.arc_carbine")}, {3, TEXT("weapon.fired.needle_smg")},
        {5, TEXT("weapon.fired.coil_matchlock")}, {9, TEXT("weapon.fired.repeater")}, {11, TEXT("weapon.fired.pulse_carbine")},
        {13, TEXT("weapon.fired.phantom_smg")}, {14, TEXT("weapon.fired.plasma_matchlock")}, {17, TEXT("weapon.fired.healing_lance")}};
    for (const auto& Gun : Guns)
        Probe.Expect(FString::Printf(TEXT("Weapon %d"), Gun.Key), Shot(Gun.Key, ESoraShotKind::Hitscan, Hero), {Gun.Value});
    Probe.Expect(TEXT("The grenade launcher"), Shot(7, ESoraShotKind::Shell, Hero), {TEXT("weapon.fired.grenade_launcher")});
    Probe.Expect(TEXT("The micro-mortar"), Shot(15, ESoraShotKind::Shell, Hero), {TEXT("weapon.fired.micro_mortar")});
    Probe.Expect(TEXT("The yumi"), Shot(18, ESoraShotKind::Arrow, Hero), {TEXT("weapon.fired.yumi")});
    Probe.Expect(TEXT("A boss's round"), Shot(INDEX_NONE, ESoraShotKind::Hitscan, Boss), {TEXT("weapon.fired.boss_round")});
    Probe.Expect(TEXT("A collector's beam"), Shot(INDEX_NONE, ESoraShotKind::Beam, Boss), {TEXT("projectile.beam")});
    // The Shock Emitter sustains: a second shot inside the gap starts its
    // loop, and the release plays when the firing stops.
    Probe.Expect(TEXT("The Shock Emitter's first shot"), Shot(16, ESoraShotKind::Hitscan, Other), {TEXT("weapon.fired.shock_emitter")});
    Probe.Expect(TEXT("The Shock Emitter held"), Shot(16, ESoraShotKind::Hitscan, Other), {TEXT("weapon.loop.shock_emitter")});
    TestTrue(TEXT("The Shock Emitter's loop runs"), Audio->LiveLoops().Contains(TEXT("weapon.loop.shock_emitter")));
    // Letting go takes play time, in which the dojo may make its own sounds.
    Audio->ForgetPlays();
    Scope.World->Tick(FramesPerSecond);
    bool bReleased = false;
    for (const FSoraAudioPlay& Play : Audio->Plays())
        bReleased |= Play.Cue == TEXT("weapon.release.shock_emitter") && Play.Source == Other;
    TestTrue(TEXT("The Shock Emitter let go plays its release"), bReleased);
    TestFalse(TEXT("The Shock Emitter's loop stops"), Audio->LiveLoops().Contains(TEXT("weapon.loop.shock_emitter")));
    Beat(TEXT("ch02.b02"))();

    // Blades: committed swings by weapon and weight, strikes, guards and parries.
    const auto Swing = [&](int32 WeaponId, float Windup)
    {
        return [&, WeaponId, Windup]()
        {
            FSoraMeleeCommittedEvent Committed;
            Committed.Attacker = Other; Committed.WeaponId = WeaponId; Committed.WindupSeconds = Windup;
            Events->OnMeleeCommitted.Broadcast(Committed);
        };
    };
    const TPair<int32, const TCHAR*> Blades[] = {{0, TEXT("katana")}, {4, TEXT("wakizashi")}, {10, TEXT("tanto")}};
    for (const auto& Blade : Blades)
    {
        Probe.Expect(FString::Printf(TEXT("A quick %s cut"), Blade.Value), Swing(Blade.Key, .3f), {*FString::Printf(TEXT("melee.committed.%s"), Blade.Value)});
        Probe.Expect(FString::Printf(TEXT("A heavy %s cut"), Blade.Value), Swing(Blade.Key, .6f),
            {*FString::Printf(TEXT("melee.committed.%s.heavy"), Blade.Value)});
    }
    Probe.Expect(TEXT("The naginata"), Swing(20, .5f), {TEXT("melee.committed.naginata")});
    Probe.Expect(TEXT("The monofilament naginata"), Swing(12, .5f), {TEXT("melee.committed.naginata")});
    Probe.Expect(TEXT("The yari"), Swing(19, .5f), {TEXT("melee.committed.yari")});
    Probe.Expect(TEXT("The kusarigama"), Swing(2, .5f), {TEXT("melee.committed.kusarigama")});
    Probe.Expect(TEXT("The kanabō"), Swing(6, .5f), {TEXT("melee.committed.kanabo")});
    Probe.Expect(TEXT("The forge hammer"), Swing(8, .5f), {TEXT("melee.committed.kanabo")});
    const auto Strike = [&](bool bHit)
    {
        return [&, bHit]()
        {
            FSoraStrikeResolvedEvent Resolved;
            Resolved.Attacker = Hero; Resolved.Target = Other; Resolved.WeaponId = 0; Resolved.bHit = bHit; Resolved.Damage = 20.f;
            Events->OnStrikeResolved.Broadcast(Resolved);
        };
    };
    const auto Defend = [&](bool bParry, bool bDojo)
    {
        return [&, bParry, bDojo]()
        {
            FSoraDefenseEvent Defense;
            Defense.Defender = Other; Defense.Attacker = Hero; Defense.bDojo = bDojo;
            (bParry ? Events->OnParried : Events->OnGuarded).Broadcast(Defense);
        };
    };
    Probe.Expect(TEXT("A struck body"), Strike(true), {TEXT("melee.strike.hit_body")});
    Probe.Expect(TEXT("A miss"), Strike(false), {});
    Probe.Expect(TEXT("A guard"), Defend(false, false), {TEXT("melee.guard")});
    Probe.Expect(TEXT("A parry"), Defend(true, false), {TEXT("melee.parry")});
    Probe.Expect(TEXT("A dojo guard"), Defend(false, true), {TEXT("melee.dojo.clack")});
    Probe.Expect(TEXT("A dojo parry"), Defend(true, true), {TEXT("melee.dojo.clack")});
    Probe.Expect(TEXT("転"), [&]()
    {
        FSoraMarobashiEvent Step;
        Step.Hero = Hero; Step.Opponent = Other;
        Events->OnMarobashi.Broadcast(Step);
    }, {TEXT("melee.marobashi")});

    // Sparring: in a sparring beat the blades are bokutō or fukuro-shinai.
    Beat(TEXT("ch01.b02"))();
    Probe.Expect(TEXT("A bokutō in keiko"), Swing(0, .3f), {TEXT("melee.committed.bokuto")});
    Probe.Expect(TEXT("A bokutō strike in keiko"), Strike(true), {TEXT("melee.dojo.clack")});
    Beat(TEXT("ch01.b11"))();
    Probe.Expect(TEXT("A fukuro-shinai bout"), Swing(0, .3f), {TEXT("melee.committed.fukuro_shinai")});
    Probe.Expect(TEXT("The sky splits"), Beat(TEXT("ch01.b13")), {TEXT("sfx.alien.sky_seam")});
    Probe.Expect(TEXT("The sky splits again from a checkpoint"), Beat(TEXT("ch01.b13"), true), {});
    Probe.Expect(TEXT("The debt seals clamp"), Beat(TEXT("ch02.b01")), {TEXT("sfx.alien.debt_seal_clamp")});
    Probe.Expect(TEXT("A beat completed"), [&]()
    {
        FSoraBeatEvent Done;
        Done.BeatId = TEXT("ch02.b01");
        Events->OnBeatCompleted.Broadcast(Done);
    }, {TEXT("ui.objective")});
    Probe.Expect(TEXT("A beat failed"), [&]()
    {
        FSoraBeatEvent Failed;
        Failed.BeatId = TEXT("ch02.b02");
        Events->OnBeatFailed.Broadcast(Failed);
    }, {});

    // Hurt and fallen.
    Probe.Expect(TEXT("The hero hurt"), [&]()
    {
        FSoraDamagedEvent Damaged;
        Damaged.Victim = Hero; Damaged.Causer = Other; Damaged.Amount = 1.f; Damaged.HealthAfter = Hero->Health;
        Events->OnDamaged.Broadcast(Damaged);
    }, {TEXT("player.damaged")});
    Probe.Expect(TEXT("An opponent hurt"), [&]()
    {
        FSoraDamagedEvent Damaged;
        Damaged.Victim = Other; Damaged.Causer = Hero; Damaged.Amount = 1.f;
        Events->OnDamaged.Broadcast(Damaged);
    }, {});
    const auto Fall = [&](AActor* Victim, bool bSparring)
    {
        return [&, Victim, bSparring]()
        {
            FSoraDiedEvent Died;
            Died.Victim = Victim; Died.Killer = Victim == Hero ? Other : Hero; Died.bSparring = bSparring;
            Events->OnDied.Broadcast(Died);
        };
    };
    Probe.Expect(TEXT("A sparring point"), Fall(Other, true), {TEXT("sparring.point")});
    Probe.Expect(TEXT("The hero falls"), Fall(Hero, false), {TEXT("player.died")});
    Probe.Expect(TEXT("An opponent falls"), Fall(Other, false), {TEXT("enemy.died")});
    Probe.Expect(TEXT("An explosion"), [&]()
    {
        FSoraDetonatedEvent Blast;
        Blast.Location = Other->GetActorLocation(); Blast.Radius = 300.f; Blast.Damage = 60.f;
        Events->OnDetonated.Broadcast(Blast);
    }, {TEXT("explosion.detonated")});

    // Opponents.
    const auto Cue = [&](ESoraEnemyCue Kind, const TCHAR* Detail)
    {
        return [&, Kind, Detail]()
        {
            FSoraEnemyCueEvent Event;
            Event.Enemy = Other; Event.Archetype = TEXT("marksman"); Event.Cue = Kind; Event.Detail = Detail;
            Events->OnEnemyCue.Broadcast(Event);
        };
    };
    Probe.Expect(TEXT("A marksman's lock"), Cue(ESoraEnemyCue::AttackWindup, TEXT("marksman_lock")), {TEXT("enemy.windup.lock")});
    Probe.Expect(TEXT("A retainer's cut, heard only as its blade"), Cue(ESoraEnemyCue::AttackWindup, TEXT("retainer_warning")), {});
    Probe.Expect(TEXT("A barrier broken"), Cue(ESoraEnemyCue::BarrierBroken, TEXT("")), {TEXT("boss.shield.break")});
    Probe.Expect(TEXT("A shield turning a shot"), Cue(ESoraEnemyCue::ShieldTurned, TEXT("")), {TEXT("boss.shield.hit")});
    Probe.Expect(TEXT("An alarm"), Cue(ESoraEnemyCue::Alarm, TEXT("")), {TEXT("ui.alien.chime")});

    // Bosses: telegraphs by attack class, strikes, shields, counters, defeat.
    const auto Phase = [&](ESoraBossPhase Kind, const TCHAR* BossId, const TCHAR* Detail, bool bBeam = false, int32 WindupMs = 0)
    {
        return [&, Kind, BossId, Detail, bBeam, WindupMs]()
        {
            FSoraBossPhaseEvent Event;
            Event.Boss = Boss; Event.Phase = Kind; Event.BossId = BossId; Event.Detail = Detail; Event.bBeam = bBeam; Event.WindupMs = WindupMs;
            Events->OnBossPhase.Broadcast(Event);
        };
    };
    Probe.Expect(TEXT("A boss arrives"), Phase(ESoraBossPhase::Arrived, TEXT("boss_dunark"), TEXT("")), {TEXT("boss.arrived")});
    Probe.Expect(TEXT("Dunark's quick cut"), Phase(ESoraBossPhase::Windup, TEXT("boss_dunark"), TEXT("quick_cut"), false, 500),
        {TEXT("boss.windup.cleave")});
    const FSoraAudioPlay Quick = Audio->Plays().Last();
    TestTrue(*FString::Printf(TEXT("A 500 ms windup starts the 900 ms telegraph 0.4 s in (%.3f, %.3f)"), Quick.StartSeconds, Quick.DelaySeconds),
        FMath::IsNearlyEqual(Quick.StartSeconds, .4f, .001f) && Quick.DelaySeconds == 0.f);
    Probe.Expect(TEXT("Dunark's burning beam"), Phase(ESoraBossPhase::Windup, TEXT("boss_dunark"), TEXT("burning_beam"), false, 1950),
        {TEXT("boss.windup.area_1500")});
    const FSoraAudioPlay Area = Audio->Plays().Last();
    TestTrue(*FString::Printf(TEXT("An Easy 1950 ms windup holds the 1500 ms telegraph back 0.45 s (%.3f)"), Area.DelaySeconds),
        FMath::IsNearlyEqual(Area.DelaySeconds, .45f, .001f) && Area.StartSeconds == 0.f);
    Probe.Expect(TEXT("A locked beam"), Phase(ESoraBossPhase::Windup, TEXT("boss_hakari"), TEXT("sweep_beam"), true, 1100),
        {TEXT("boss.windup.beam")});
    Probe.Expect(TEXT("Collatera's margin call"), Phase(ESoraBossPhase::Windup, TEXT("boss_collatera"), TEXT("margin_call"), false, 1500),
        {TEXT("boss.windup.margin_call")});
    Probe.Expect(TEXT("Collatera's reload window"), Phase(ESoraBossPhase::Windup, TEXT("boss_collatera"), TEXT("reload")),
        {TEXT("weapon.reload.cell_eject")});
    Probe.Expect(TEXT("A summons, which has no telegraph tone"), Phase(ESoraBossPhase::Windup, TEXT("boss_collatera"), TEXT("drone_call")), {});
    Probe.Expect(TEXT("A rival's cut, which has no telegraph tone"),
        Phase(ESoraBossPhase::Windup, TEXT("duel_toranosuke_steel"), TEXT("kesa_combo"), false, 450), {});
    Probe.Expect(TEXT("A cleave landing"), Phase(ESoraBossPhase::Strike, TEXT("boss_dunark"), TEXT("heavy_overhead")), {TEXT("boss.strike.cleave")});
    Probe.Expect(TEXT("A shield broken"), Phase(ESoraBossPhase::Event, TEXT("boss_penalta"), TEXT("shield_broken")), {TEXT("boss.shield.break")});
    Probe.Expect(TEXT("A blow deflected"), Phase(ESoraBossPhase::Event, TEXT("boss_penalta"), TEXT("deflected")), {TEXT("boss.shield.hit")});
    Probe.Expect(TEXT("A boss countered"), Phase(ESoraBossPhase::Countered, TEXT("boss_dunark"), TEXT("quick_cut")), {TEXT("melee.parry")});
    Probe.Expect(TEXT("A boss defeated"), Phase(ESoraBossPhase::Defeated, TEXT("boss_dunark"), TEXT("kill")), {TEXT("boss.defeated")});

    // Campaign progress.
    Probe.Expect(TEXT("A chapter starts"), [&]()
    {
        FSoraChapterEvent Started;
        Started.ChapterId = 1;
        Events->OnChapterStarted.Broadcast(Started);
    }, {TEXT("chapter.started")});
    Probe.Expect(TEXT("A chapter resumed from a checkpoint"), [&]()
    {
        FSoraChapterEvent Started;
        Started.ChapterId = 1; Started.bResumed = true;
        Events->OnChapterStarted.Broadcast(Started);
    }, {});
    Probe.Expect(TEXT("A chapter complete"), [&]()
    {
        FSoraChapterEvent Done;
        Done.ChapterId = 1;
        Events->OnChapterCompleted.Broadcast(Done);
    }, {TEXT("chapter.completed")});
    Probe.Expect(TEXT("A site restored"), [&]()
    {
        FSoraSiteRestoredEvent Restored;
        Restored.ChapterId = 1; Restored.SiteIndex = 0; Restored.Kind = TEXT("irrigation");
        Events->OnSiteRestored.Broadcast(Restored);
    }, {TEXT("site.restored"), TEXT("ui.xor.credited")});

    // Practice kernel events, forwarded to the families they sound as.
    const auto Tick = [&](const FSoraPracticeEvent& Event) { return [&, Event]() { Events->OnKernelEvent.Broadcast(Event, 1u); }; };
    Probe.Expect(TEXT("A kernel katana swing"), Tick(Kernel(1u, 1, INDEX_NONE, 0)), {TEXT("melee.committed.katana")});
    Probe.Expect(TEXT("A kernel carbine shot"), Tick(Kernel(1u, 1, INDEX_NONE, 1)), {TEXT("weapon.fired.arc_carbine")});
    Probe.Expect(TEXT("A kernel grenade"), Tick(Kernel(1u, 1, INDEX_NONE, 7)), {TEXT("weapon.fired.grenade_launcher")});
    Probe.Expect(TEXT("The player hurt in practice"), Tick(Kernel(2u, 1, 0, 1, 0, 10)), {TEXT("player.damaged")});
    Probe.Expect(TEXT("The player scorched in practice"), Tick(Kernel(15u, INDEX_NONE, 0, 0, 0, 5)), {TEXT("player.damaged")});
    Probe.Expect(TEXT("The player falls in practice"), Tick(Kernel(3u, 1, 0)), {TEXT("player.died")});
    Probe.Expect(TEXT("A bot falls in practice"), Tick(Kernel(3u, 0, 1)), {TEXT("enemy.died")});
    Probe.Expect(TEXT("A kernel parry"), Tick(Kernel(6u, 1, 0, 0, 1)), {TEXT("melee.parry")});
    Probe.Expect(TEXT("A kernel guard"), Tick(Kernel(6u, 1, 0, 0, 0)), {TEXT("melee.guard")});
    Probe.Expect(TEXT("A riposte"), Tick(Kernel(10u, 0, 1)), {TEXT("melee.parry")});
    Probe.Expect(TEXT("The player respawns"), Tick(Kernel(4u, INDEX_NONE, 0)), {TEXT("ui.notify")});
    Probe.Expect(TEXT("A bot respawns"), Tick(Kernel(4u, INDEX_NONE, 1)), {});
    Probe.Expect(TEXT("A barricade destroyed"), Tick(Kernel(14u, 1, 0, 0, 1)), {TEXT("boss.shield.break")});
    Probe.Expect(TEXT("The point captured"), Tick(Kernel(16u, INDEX_NONE, INDEX_NONE, 0, 1)), {TEXT("ui.objective")});
    Probe.Expect(TEXT("A payload checkpoint"), Tick(Kernel(18u, INDEX_NONE, INDEX_NONE, 0, 1)), {TEXT("ui.objective")});
    Probe.Expect(TEXT("Overtime"), Tick(Kernel(17u, INDEX_NONE, INDEX_NONE)), {TEXT("ui.notify")});
    Probe.Expect(TEXT("The player wins free-for-all"), Tick(Kernel(19u, INDEX_NONE, INDEX_NONE, 0, 2, 0)), {TEXT("chapter.completed")});
    Probe.Expect(TEXT("A bot wins free-for-all"), Tick(Kernel(19u, INDEX_NONE, INDEX_NONE, 0, 2, 3)), {});

    // The front end's sounds.
    const TPair<ESoraUISound, const TCHAR*> Interface[] = {{ESoraUISound::Hover, TEXT("ui.hover")}, {ESoraUISound::Click, TEXT("ui.click")},
        {ESoraUISound::Confirm, TEXT("ui.confirm")}, {ESoraUISound::Back, TEXT("ui.back")}, {ESoraUISound::Error, TEXT("ui.error")},
        {ESoraUISound::Option, TEXT("ui.tab")}, {ESoraUISound::Slider, TEXT("ui.slider")}, {ESoraUISound::MenuOpen, TEXT("ui.menu.open")},
        {ESoraUISound::MenuClose, TEXT("ui.menu.close")}};
    for (const auto& Sound : Interface)
        Probe.Expect(FString::Printf(TEXT("The %s interface sound"), Sound.Value), [&]() { Events->OnUISound.Broadcast(Sound.Key); }, {Sound.Value});

    // What the subsystem polls: weapon actions, footsteps and horses.
    const auto Hear = [&](const TCHAR* Family, FFacts Facts, AActor* Source)
    {
        return [&, Family, Facts, Source]() { Audio->Hear(Family, Facts, Source, FVector::ZeroVector); };
    };
    const TPair<const TCHAR*, const TCHAR*> Actions[] = {{TEXT("ReloadStarted"), TEXT("weapon.reload.cell_eject")},
        {TEXT("ChargeStarted"), TEXT("weapon.charge.plasma_matchlock")}, {TEXT("ChargeHeld"), TEXT("weapon.hold.plasma_matchlock")},
        {TEXT("BowDrawn"), TEXT("weapon.yumi.draw")}, {TEXT("Sheathed"), TEXT("melee.katana.sheathe")}, {TEXT("Drawn"), TEXT("melee.katana.draw")}};
    for (const auto& Action : Actions)
        Probe.Expect(FString::Printf(TEXT("%s"), Action.Key),
            Hear(TEXT("Hero"), FFacts().Text(TEXT("Action"), Action.Key).Int(TEXT("WeaponId"), FCString::Strcmp(Action.Key, TEXT("ReloadStarted")) ? 14 : 1)
                .Flag(TEXT("IsHero"), true), Hero), {Action.Value});
    Probe.Expect(TEXT("A katana reload, which needs none"), Hear(TEXT("Hero"), FFacts().Text(TEXT("Action"), TEXT("ReloadStarted")).Int(TEXT("WeaponId"), 0), Hero), {});
    for (const auto& Surface : FData::Get()->Surfaces)
        Probe.Expect(FString::Printf(TEXT("A step on %s"), *Surface.Key.ToString()),
            Hear(TEXT("Footstep"), FFacts().Text(TEXT("Surface"), Surface.Key.ToString()).Text(TEXT("Pace"), TEXT("walk")).Flag(TEXT("IsHero"), false), Other),
            {*Surface.Value.ToString()});
    for (const TCHAR* Gait : {TEXT("Walk"), TEXT("Trot"), TEXT("Canter"), TEXT("Gallop")})
        Probe.Expect(FString::Printf(TEXT("A hoofbeat at the %s"), Gait),
            Hear(TEXT("Horse"), FFacts().Text(TEXT("Action"), TEXT("Hoof")).Text(TEXT("Gait"), Gait), Other),
            {*FString::Printf(TEXT("horse.%s"), *FString(Gait).ToLower())});
    Probe.Expect(TEXT("A spooked horse"), Hear(TEXT("Horse"), FFacts().Text(TEXT("Action"), TEXT("Spooked")).Text(TEXT("Gait"), TEXT("Walk")), Other),
        {TEXT("horse.whinny")});
    Probe.Expect(TEXT("Mounting"), Hear(TEXT("Horse"), FFacts().Text(TEXT("Action"), TEXT("Mounted")).Text(TEXT("Gait"), TEXT("Halt")), Other),
        {TEXT("horse.tack")});

    // Every rule of every family was heard; a kernel forward counts through
    // the cue it played for that family.
    const FData* D = FData::Get();
    for (const auto& Pair : D->Bindings)
        for (const SoraAudioData::FRule& Rule : Pair.Value)
        {
            if (!Rule.Cue.IsNone())
                TestTrue(*FString::Printf(TEXT("%s's rule for %s was exercised"), *Pair.Key.ToString(), *Rule.Cue.ToString()),
                    Probe.Covered.Contains(Pair.Key.ToString() + TEXT("|") + Rule.Cue.ToString()));
            else
            {
                bool bForwarded = false;
                for (const SoraAudioData::FRule& Target : D->Bindings.FindRef(Rule.As))
                    bForwarded |= !Target.Cue.IsNone() && Probe.Covered.Contains(TEXT("Kernel|") + Target.Cue.ToString());
                TestTrue(*FString::Printf(TEXT("Kernel events forwarded to %s were exercised"), *Rule.As.ToString()), bForwarded);
            }
        }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraAudioPollingTest,
    "SoraArena.Audio.PolledSounds",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraAudioPollingTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraAudioTests;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FScope Scope(*this, TEXT("AudioPolling"));
    if (!Scope.Start() || !EnterPlay(Scope))
        return false;
    UWorld* World = Scope.World->GetTestWorld();
    USoraAudioSubsystem* Audio = USoraAudioSubsystem::Get(World);
    ASoraPlayerCharacter* Hero = Scope.World->Player();
    USoraEquipmentComponent* Gear = Hero ? Hero->FindComponentByClass<USoraEquipmentComponent>() : nullptr;
    if (!TestNotNull(TEXT("The world has its audio"), Audio) || !TestNotNull(TEXT("The hero carries his weapons"), Gear))
        return false;
    const auto Played = [Audio](const TCHAR* Cue, FName Family = NAME_None)
    {
        for (const FSoraAudioPlay& Play : Audio->Plays())
            if (Play.Cue == Cue && (Family.IsNone() || Play.Family == Family))
                return &Play;
        return static_cast<const FSoraAudioPlay*>(nullptr);
    };

    // The hero walks: footsteps on the surface under him, at his feet.
    Audio->ForgetPlays();
    Scope.World->InjectKey(EKeys::W, IE_Pressed);
    Scope.World->Tick(FramesPerSecond);
    Scope.World->InjectKey(EKeys::W, IE_Released);
    Scope.World->Tick(2);
    int32 Steps = 0;
    for (const FSoraAudioPlay& Play : Audio->Plays())
        if (Play.Family == TEXT("Footstep") && Play.Source == Hero)
        {
            ++Steps;
            TestTrue(*FString::Printf(TEXT("A step plays a surface's footstep cue (%s)"), *Play.Cue.ToString()),
                Play.Cue.ToString().StartsWith(TEXT("foot.")) && FData::Get()->Cue(Play.Cue) != nullptr);
            TestTrue(TEXT("A step sounds at the hero's feet"), FMath::Abs(Play.Location.Z - (Hero->GetActorLocation().Z - Hero->GetSimpleCollisionHalfHeight())) < 20.f);
        }
    TestTrue(*FString::Printf(TEXT("A second's walk takes two to six steps (%d)"), Steps), Steps >= 2 && Steps <= 6);

    // A reload of an energy arm ejects its cell, uncaptioned for the hero himself.
    Hero->WeaponId = 1;
    Gear->Ammo = 0;
    Audio->ForgetPlays();
    Scope.World->Tick(1);
    Gear->Reload();
    Scope.World->Tick(1);
    const FSoraAudioPlay* Eject = Played(TEXT("weapon.reload.cell_eject"), TEXT("Hero"));
    TestTrue(TEXT("The hero's energy reload ejects its cell, without a caption for his own sound"), Eject && !Eject->bCaptioned);

    // A horse moving past at a trot: two-beat hoofbeats from her pace.
    ASoraHorse* Horse = World->SpawnActor<ASoraHorse>(ASoraHorse::StaticClass(), FTransform(Hero->GetActorLocation() + FVector(800.f, 400.f, 0.f)));
    if (!TestNotNull(TEXT("A horse spawns"), Horse))
        return false;
    Horse->Build(TEXT("bay"), ASoraHorse::ETack::Pack);
    Scope.World->Tick(1);
    Audio->ForgetPlays();
    for (int32 Frame = 0; Frame < FramesPerSecond; ++Frame)
    {
        Horse->SetActorLocation(Horse->GetActorLocation() + FVector(350.f / FramesPerSecond, 0.f, 0.f));
        Scope.World->Tick(1);
    }
    int32 Hoofbeats = 0;
    for (const FSoraAudioPlay& Play : Audio->Plays())
        Hoofbeats += Play.Cue == TEXT("horse.trot");
    TestTrue(*FString::Printf(TEXT("A second's trot sounds 2-4 hoofbeats (%d)"), Hoofbeats), Hoofbeats >= 2 && Hoofbeats <= 4);

    // A drone carries its hover loop while it lives near the listener.
    ASoraEnemy* Drone = ASoraEnemy::SpawnArchetype(*World, TEXT("drone"), 0, Hero->GetActorLocation() + FVector(600.f, -300.f, 200.f), FRotator::ZeroRotator);
    if (!TestNotNull(TEXT("A drone spawns"), Drone))
        return false;
    Scope.World->Tick(FramesPerSecond / 2 + 2);
    TestTrue(TEXT("The drone's hover loop rides on it"), Audio->LiveLoops().Contains(TEXT("amb.alien.drone")));
    Drone->Destroy();
    Scope.World->Tick(FramesPerSecond / 2 + 2);
    return TestFalse(TEXT("The loop stops with the drone"), Audio->LiveLoops().Contains(TEXT("amb.alien.drone")));
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraAudioVolumesTest,
    "SoraArena.Audio.VolumesSetSubmixGains",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraAudioVolumesTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraAudioTests;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FScope Scope(*this, TEXT("AudioVolumes"));
    if (!Scope.Start())
        return false;
    USoraAudioSubsystem* Audio = USoraAudioSubsystem::Get(Scope.World->GetTestWorld());
    USoraSettings* Settings = Scope.Mode()->Settings();
    if (!TestNotNull(TEXT("The world has its audio"), Audio) || !TestNotNull(TEXT("The world has settings"), Settings))
        return false;
    const auto Gains = [Audio](std::initializer_list<const TCHAR*> Buses)
    {
        TArray<FString> Out;
        for (const TCHAR* Bus : Buses)
            Out.Add(FString::Printf(TEXT("%s %.3f"), Bus, Audio->SubmixGain(Bus)));
        return FString::Join(Out, TEXT(", "));
    };
    const auto Near = [](float A, float B) { return FMath::IsNearlyEqual(A, B, .001f); };
    TestTrue(TEXT("Full volumes leave every submix at unity"), Near(Audio->SubmixGain(TEXT("Music")), 1.f) && Near(Audio->SubmixGain(TEXT("SFX")), 1.f));
    Settings->SetBusVolume(ESoraAudioBus::Music, 50);
    Settings->SetBusVolume(ESoraAudioBus::Voice, 70);
    Settings->SetBusVolume(ESoraAudioBus::UI, 30);
    Settings->SetBusVolume(ESoraAudioBus::Ambience, 90);
    Settings->SetBusVolume(ESoraAudioBus::SFX, 80);
    TestTrue(*FString::Printf(TEXT("Each slider sets its submix on the squared curve (%s)"),
                 *Gains({TEXT("Music"), TEXT("SFX"), TEXT("Voice"), TEXT("UI"), TEXT("Ambience")})),
        Near(Audio->SubmixGain(TEXT("Music")), .25f) && Near(Audio->SubmixGain(TEXT("SFX")), .64f) && Near(Audio->SubmixGain(TEXT("Voice")), .49f) &&
        Near(Audio->SubmixGain(TEXT("UI")), .09f) && Near(Audio->SubmixGain(TEXT("Ambience")), .81f));
    TestTrue(*FString::Printf(TEXT("Telegraphs follow SFX and barks follow Voice above their floor (%s)"), *Gains({TEXT("SFX_Telegraph"), TEXT("Voice_Barks")})),
        Near(Audio->SubmixGain(TEXT("SFX_Telegraph")), .64f) && Near(Audio->SubmixGain(TEXT("Voice_Barks")), .49f));
    Settings->SetBusVolume(ESoraAudioBus::SFX, 0);
    Settings->SetBusVolume(ESoraAudioBus::Voice, 0);
    const float Floor = FMath::Pow(10.f, -12.f / 20.f);
    TestTrue(*FString::Printf(TEXT("With SFX and Voice at 0, telegraphs and barks keep their -12 dB floor (%s)"),
                 *Gains({TEXT("SFX"), TEXT("SFX_Telegraph"), TEXT("Voice"), TEXT("Voice_Barks")})),
        Near(Audio->SubmixGain(TEXT("SFX")), 0.f) && Near(Audio->SubmixGain(TEXT("SFX_Telegraph")), Floor) &&
        Near(Audio->SubmixGain(TEXT("Voice")), 0.f) && Near(Audio->SubmixGain(TEXT("Voice_Barks")), Floor));
    TestTrue(TEXT("Master stays the device volume, never a submix gain"), Near(Audio->SubmixGain(TEXT("Master")), 1.f) &&
        Near(Audio->SubmixGain(TEXT("SFX_Weapons")), 1.f));
    return TestFalse(TEXT("Automation's settings stay detached, so the editor's mix is untouched"), Settings->IsAttached());
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraAudioMusicTest,
    "SoraArena.Audio.MusicStates",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraAudioMusicTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraAudioTests;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FScope Scope(*this, TEXT("AudioMusic"));
    if (!Scope.Start())
        return false;
    UWorld* World = Scope.World->GetTestWorld();
    USoraAudioSubsystem* Audio = USoraAudioSubsystem::Get(World);
    USoraGameEvents* Events = USoraGameEvents::Get(World);
    if (!TestNotNull(TEXT("The world has its audio"), Audio) || !TestNotNull(TEXT("The world has game events"), Events))
        return false;
    const FSoraMusicStatus& Music = Audio->Music();
    const auto Is = [&](ESoraMusicState State, const TCHAR* Piece, std::initializer_list<const TCHAR*> Stems)
    {
        TArray<FName> Wanted;
        for (const TCHAR* Stem : Stems)
            Wanted.Add(Stem);
        return Music.State == State && Music.Piece == Piece && Music.Stems == Wanted;
    };
    const auto Status = [&]() { return FString::Printf(TEXT("state %d, %s [%s] %s, fade %.2f"), static_cast<int32>(Music.State),
        *Music.Piece.ToString(), *Join(Music.Stems), *Music.Mix.ToString(), Music.FadeSeconds); };
    TestTrue(*FString::Printf(TEXT("The title plays Wind over Nyaagyū from its intro (%s)"), *Status()),
        Is(ESoraMusicState::Menu, TEXT("title"), {TEXT("main")}) && Music.bIntro);
    const int32 TitleChanges = Music.Changes;
    if (!EnterPlay(Scope))
        return false;
    Scope.World->Tick(2);
    TestTrue(*FString::Printf(TEXT("The dojo explores to the same piece without restarting it (%s)"), *Status()),
        Is(ESoraMusicState::Exploration, TEXT("title"), {TEXT("main")}) && Music.Changes == TitleChanges + 1);

    // A stealth zone: its stems follow the most alarmed guard, and a fight
    // is the same piece with the alert stems, so it never loses the bar.
    const FString Stealth = BeatIn(TEXT("stealth")), Combat = BeatIn(TEXT("combat")), Boss = BeatIn(TEXT("boss"));
    ASoraPlayerCharacter* Hero = Scope.World->Player();
    ASoraEnemy* Guard = ASoraEnemy::SpawnArchetype(*World, TEXT("blade_retainer"), 0, Hero->GetActorLocation() + FVector(2000.f, 0.f, 0.f), FRotator::ZeroRotator);
    if (!TestNotNull(TEXT("A guard spawns"), Guard) || !TestFalse(TEXT("The data has stealth, combat and boss beats"), Stealth.IsEmpty() || Combat.IsEmpty() || Boss.IsEmpty()))
        return false;
    const auto Start = [&](const FString& Id)
    {
        FSoraBeatEvent Started;
        Started.BeatId = Id;
        Events->OnBeatStarted.Broadcast(Started);
        Scope.World->Tick(1);
    };
    const auto Alert = [&](const TCHAR* Detail)
    {
        FSoraEnemyCueEvent Event;
        Event.Enemy = Guard; Event.Archetype = TEXT("blade_retainer"); Event.Cue = ESoraEnemyCue::AlertState; Event.Detail = Detail;
        Events->OnEnemyCue.Broadcast(Event);
        Scope.World->Tick(1);
    };
    const FData* D = FData::Get();
    Start(Stealth);
    TestTrue(*FString::Printf(TEXT("%s plays Occupied Streets' base stem (%s)"), *Stealth, *Status()),
        Is(ESoraMusicState::Stealth, TEXT("occupation"), {TEXT("base")}) && FMath::IsNearlyEqual(Music.FadeSeconds, D->PieceSeconds));
    if (Audio->HasDevice())
        TestEqual(TEXT("On a device every stem of the piece has its voice, the silent ones too"), Audio->StemVoices().Num(), 4);
    Alert(TEXT("suspicious"));
    TestTrue(*FString::Printf(TEXT("A suspicious guard adds the pulse (%s)"), *Status()),
        Is(ESoraMusicState::Stealth, TEXT("occupation"), {TEXT("base"), TEXT("pulse")}) && FMath::IsNearlyEqual(Music.FadeSeconds, D->StemSeconds));
    Alert(TEXT("alert"));
    TestTrue(*FString::Printf(TEXT("Detection turns to combat in 250 ms on the same piece (%s)"), *Status()),
        Is(ESoraMusicState::Combat, TEXT("occupation"), {TEXT("base"), TEXT("pulse"), TEXT("perc")}) && FMath::IsNearlyEqual(Music.FadeSeconds, .25f));
    Alert(TEXT("search"));
    TestTrue(*FString::Printf(TEXT("A search eases back over 2.5 s (%s)"), *Status()),
        Is(ESoraMusicState::Stealth, TEXT("occupation"), {TEXT("base"), TEXT("pulse"), TEXT("search")}) && FMath::IsNearlyEqual(Music.FadeSeconds, 2.5f));
    Alert(TEXT("unaware"));
    TestTrue(*FString::Printf(TEXT("An unaware guard leaves the base alone (%s)"), *Status()), Is(ESoraMusicState::Stealth, TEXT("occupation"), {TEXT("base")}));

    // A combat beat, then a boss by his phases, then his defeat.
    Start(Combat);
    TestTrue(*FString::Printf(TEXT("%s plays the alert stems (%s)"), *Combat, *Status()),
        Is(ESoraMusicState::Combat, TEXT("occupation"), {TEXT("base"), TEXT("pulse"), TEXT("perc")}));
    Start(Boss);
    TestTrue(*FString::Printf(TEXT("%s plays the Compound-Interest Flagship's synth (%s)"), *Boss, *Status()),
        Is(ESoraMusicState::Boss, TEXT("flagship"), {TEXT("synth")}));
    const auto Phase = [&](ESoraBossPhase Kind, int32 Index)
    {
        FSoraBossPhaseEvent Event;
        Event.Boss = Guard; Event.Phase = Kind; Event.PhaseIndex = Index; Event.BossId = TEXT("boss_dunark");
        Events->OnBossPhase.Broadcast(Event);
        Scope.World->Tick(1);
    };
    Phase(ESoraBossPhase::Arrived, 0);
    Phase(ESoraBossPhase::PhaseChanged, 1);
    TestTrue(*FString::Printf(TEXT("His second phase brings in the taiko (%s)"), *Status()), Is(ESoraMusicState::Boss, TEXT("flagship"), {TEXT("synth"), TEXT("taiko")}));
    Phase(ESoraBossPhase::PhaseChanged, 2);
    TestTrue(*FString::Printf(TEXT("His last phase is the taiko alone (%s)"), *Status()), Is(ESoraMusicState::Boss, TEXT("flagship"), {TEXT("taiko")}));
    Phase(ESoraBossPhase::Defeated, 2);
    TestTrue(*FString::Printf(TEXT("His defeat returns to exploration (%s)"), *Status()), Is(ESoraMusicState::Exploration, TEXT("title"), {TEXT("main")}));

    // The pause menu keeps the round's music; the title brings its own back.
    Start(Combat);
    Scope.Mode()->OpenPauseMenu();
    Scope.World->Tick(1);
    TestTrue(*FString::Printf(TEXT("The pause menu keeps the fight's music (%s)"), *Status()), Is(ESoraMusicState::Combat, TEXT("occupation"),
        {TEXT("base"), TEXT("pulse"), TEXT("perc")}));
    Scope.Mode()->ResumePlay();
    Scope.World->Tick(1);

    // Stingers duck the bed and never stack. The dojo scores its own points,
    // so wait for a moment without one.
    for (int32 Frame = 0; Frame < 12 * FramesPerSecond && !Music.Stinger.IsNone(); ++Frame)
        Scope.World->Tick(1);
    Audio->ForgetPlays();
    FSoraChapterEvent Done;
    Done.ChapterId = 1;
    Events->OnChapterCompleted.Broadcast(Done);
    FSoraSiteRestoredEvent Restored;
    Events->OnSiteRestored.Broadcast(Restored);
    const TArray<FSoraAudioPlay>& Plays = Audio->Plays();
    TestTrue(*FString::Printf(TEXT("A stinger ducks the bed by 6 dB (%s, gain %.3f)"), *Music.Stinger.ToString(), Music.BedGain),
        Music.Stinger == TEXT("chapter.completed") && FMath::IsNearlyEqual(Music.BedGain, FMath::Pow(10.f, -6.f / 20.f), .001f));
    TestTrue(TEXT("A second stinger while the first sounds is dropped, never stacked"), Plays.Num() >= 2 && !Plays[0].bDropped &&
        Plays[1].Cue == TEXT("site.restored") && Plays[1].bDropped);
    Scope.World->Tick(8 * FramesPerSecond);
    return TestTrue(*FString::Printf(TEXT("After the stinger the bed comes back (%s, %.3f)"), *Music.Stinger.ToString(), Music.BedGain),
        Music.Stinger != TEXT("chapter.completed") && (!Music.Stinger.IsNone() || FMath::IsNearlyEqual(Music.BedGain, 1.f)));
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraAudioAmbienceTest,
    "SoraArena.Audio.AmbienceByPlaceAndWeather",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraAudioAmbienceTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraAudioTests;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FScope Scope(*this, TEXT("AudioAmbience"));
    if (!Scope.Start())
        return false;
    UWorld* World = Scope.World->GetTestWorld();
    USoraAudioSubsystem* Audio = USoraAudioSubsystem::Get(World);
    USoraGameEvents* Events = USoraGameEvents::Get(World);
    Scope.World->Tick(1);
    TestTrue(TEXT("The title has no ambience"), Audio->Bed().IsNone() && Audio->WeatherBed().IsNone());
    if (!EnterPlay(Scope))
        return false;
    const auto Start = [&](const TCHAR* Id)
    {
        FSoraBeatEvent Started;
        Started.BeatId = Id;
        Events->OnBeatStarted.Broadcast(Started);
        Scope.World->Tick(1);
        return FString::Printf(TEXT("%s: bed %s, weather %s (%s)"), Id, *Audio->Bed().ToString(), *Audio->Weather().ToString(), *Audio->WeatherBed().ToString());
    };
    FString Seen = Start(TEXT("ch01.b10"));
    TestTrue(*(TEXT("The estate by day: ") + Seen), Audio->Bed() == TEXT("amb.estate.day") && Audio->Weather() == TEXT("clear") && Audio->WeatherBed().IsNone());
    Seen = Start(TEXT("ch03.b02"));
    TestTrue(*(TEXT("The canal approach in the rain: ") + Seen), Audio->Weather() == TEXT("rain") && Audio->WeatherBed() == TEXT("amb.rain"));
    Seen = Start(TEXT("ch07.b02"));
    TestTrue(*(TEXT("The anchor bastion in the typhoon: ") + Seen), Audio->Weather() == TEXT("typhoon") && Audio->WeatherBed() == TEXT("amb.typhoon"));
    Seen = Start(TEXT("ch07.b05"));
    const FSoraAudioPlay* Engine = nullptr;
    for (const FSoraAudioPlay& Play : Audio->Plays())
        if (Play.Cue == TEXT("amb.alien.flagship_engine"))
            Engine = &Play;
    TestTrue(*(TEXT("The flagship's interior hums with its engine, heard everywhere: ") + Seen),
        Audio->Bed() == TEXT("amb.alien.flagship_engine") && Audio->LiveLoops().Contains(TEXT("amb.alien.flagship_engine")) && Engine &&
        Engine->IsVoiced() && !Engine->bSpatial && Engine->bLoop);
    Seen = Start(TEXT("ch02.b02"));
    return TestTrue(*(TEXT("The burning estate at night: ") + Seen), Audio->Bed() == TEXT("amb.night_insects") && Audio->Weather() == TEXT("fire") &&
        Audio->WeatherBed() == TEXT("amb.fire") && !Audio->LiveLoops().Contains(TEXT("amb.alien.flagship_engine")));
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraAudioCaptionsTest,
    "SoraArena.Audio.SoundCaptions",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraAudioCaptionsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraAudioTests;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FScope Scope(*this, TEXT("AudioCaptions"));
    if (!Scope.Start() || !EnterPlay(Scope))
        return false;
    UWorld* World = Scope.World->GetTestWorld();
    USoraCaptions* Captions = USoraCaptions::Get(World);
    USoraGameEvents* Events = USoraGameEvents::Get(World);
    USoraSettings* Settings = Scope.Mode()->Settings();
    ASoraHUD* HUD = World->SpawnActor<ASoraHUD>();
    ASoraPlayerCharacter* Hero = Scope.World->Player();
    if (!TestNotNull(TEXT("The world has captions"), Captions) || !TestNotNull(TEXT("A HUD spawns"), HUD))
        return false;
    AActor* Boss = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform(Hero->GetActorLocation() + FVector(0.f, 900.f, 0.f)));
    Scope.World->Tick(6 * FramesPerSecond);
    const auto Find = [Captions](const TCHAR* Japanese)
    {
        for (const FSoraCaption& Caption : Captions->Live())
            if (Caption.Japanese == Japanese)
                return Caption;
        return FSoraCaption();
    };

    Settings->SetSoundCaptions(true);
    FSoraBossPhaseEvent Broken;
    Broken.Boss = Boss; Broken.Phase = ESoraBossPhase::Event; Broken.BossId = TEXT("boss_penalta"); Broken.Detail = TEXT("shield_broken");
    Events->OnBossPhase.Broadcast(Broken);
    const FSoraCaption Shatter = Find(TEXT("障壁が砕ける"));
    TestTrue(*FString::Printf(TEXT("A shattering barrier is captioned in Japanese with its English subtitle and its source (%s / %s)"),
                 *Shatter.Japanese, *Shatter.English),
        Shatter.English == TEXT("Barrier shatters") && Shatter.bHasSource && Shatter.Source.Equals(Boss->GetActorLocation(), 1.f));
    TestTrue(TEXT("The caption panel draws while the setting is on"), FSoraHUDFrame(*HUD, *Scope.Mode(), 1600.f, 1000.f).bSoundCaptions);

    FSoraEnemyCueEvent Lock;
    Lock.Enemy = Boss; Lock.Archetype = TEXT("marksman"); Lock.Cue = ESoraEnemyCue::AttackWindup; Lock.Detail = TEXT("marksman_lock");
    Events->OnEnemyCue.Broadcast(Lock);
    TestEqual(TEXT("A marksman's lock is captioned"), Find(TEXT("照準固定音")).English, FString(TEXT("Targeting lock")));

    // The hero's own reload needs no caption; his own step on a
    // nightingale floor is exactly what he must be told about.
    USoraAudioSubsystem* Audio = USoraAudioSubsystem::Get(World);
    Audio->Hear(TEXT("Hero"), FFacts().Text(TEXT("Action"), TEXT("ReloadStarted")).Int(TEXT("WeaponId"), 1).Flag(TEXT("IsHero"), true), Hero, FVector::ZeroVector);
    TestTrue(TEXT("The hero's own reload is not captioned"), Find(TEXT("セル排出音")).Japanese.IsEmpty());
    Audio->Hear(TEXT("Footstep"), FFacts().Text(TEXT("Surface"), TEXT("nightingale_floor")).Text(TEXT("Pace"), TEXT("walk")).Flag(TEXT("IsHero"), true),
        Hero, FVector::ZeroVector);
    TestEqual(TEXT("The hero's step on a nightingale floor is captioned"), Find(TEXT("鶯張りが鳴る")).English, FString(TEXT("Nightingale floor chirps")));

    Settings->SetSoundCaptions(false);
    return TestFalse(TEXT("With the setting off the caption panel draws nothing"), FSoraHUDFrame(*HUD, *Scope.Mode(), 1600.f, 1000.f).bSoundCaptions);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraAudioFrontEndTest,
    "SoraArena.Audio.FrontEndSounds",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraAudioFrontEndTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraAudioTests;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    FScope Scope(*this, TEXT("AudioFrontEnd"));
    if (!Scope.Start())
        return false;
    USoraAudioSubsystem* Audio = USoraAudioSubsystem::Get(Scope.World->GetTestWorld());
    const auto Press = [&](const FKey& Key)
    {
        Audio->ForgetPlays();
        Scope.Key(Key);
        TArray<FName> Cues;
        for (const FSoraAudioPlay& Play : Audio->Plays())
            if (Play.Family == TEXT("UI"))
                Cues.Add(Play.Cue);
        return Cues;
    };
    const auto Only = [](const TArray<FName>& Cues, const TCHAR* Cue) { return Cues.Num() == 1 && Cues[0] == Cue; };
    TArray<FName> Cues = Press(Keyboard.Accept);
    TestTrue(*FString::Printf(TEXT("Leaving the title confirms with the rin (%s)"), *Join(Cues)), Only(Cues, TEXT("ui.confirm")));
    Cues = Press(Keyboard.Down);
    TestTrue(*FString::Printf(TEXT("Moving the focus ticks (%s)"), *Join(Cues)), Only(Cues, TEXT("ui.hover")));
    if (!Scope.FocusOn(Keyboard, EAction::Settings))
        return false;
    Cues = Press(Keyboard.Accept);
    TestTrue(*FString::Printf(TEXT("Opening a screen clicks (%s)"), *Join(Cues)), Only(Cues, TEXT("ui.click")));
    if (!Scope.Choose(Keyboard, EAction::OpenAudio) || !Scope.FocusOn(Keyboard, EAction::Volume, static_cast<int32>(ESoraAudioBus::Music)))
        return false;
    Cues = Press(Keyboard.Left);
    TestTrue(*FString::Printf(TEXT("A volume step ticks the slider (%s)"), *Join(Cues)), Only(Cues, TEXT("ui.slider")));
    Cues = Press(Keyboard.Back);
    TestTrue(*FString::Printf(TEXT("Back sounds back (%s)"), *Join(Cues)), Only(Cues, TEXT("ui.back")));
    Cues = Press(Keyboard.Back);
    if (!TestTrue(TEXT("Back at the main menu"), Scope.On(EScreen::Main)) || !Scope.FocusOn(Keyboard, EAction::NewCampaign))
        return false;
    Scope.Key(Keyboard.Accept);
    // Enter skips the chapter's title card.
    Scope.Key(Keyboard.Accept);
    Scope.World->Tick(2);
    if (!TestTrue(TEXT("The round is in play"), Scope.Mode()->IsPlaying()))
        return false;
    Cues = Press(Keyboard.Pause);
    TestTrue(*FString::Printf(TEXT("The pause menu slides open (%s)"), *Join(Cues)), Only(Cues, TEXT("ui.menu.open")));
    Cues = Press(Keyboard.Back);
    return TestTrue(*FString::Printf(TEXT("Leaving it steps back and slides it shut (%s)"), *Join(Cues)),
        Cues.Num() == 2 && Cues[0] == TEXT("ui.back") && Cues[1] == TEXT("ui.menu.close"));
}
#endif
