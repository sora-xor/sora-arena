#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraMaaiAutomation.h"
#include "Combat/SoraBossCatalog.h"
#include "SoraBoss.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraCompanion.h"
#include "SoraEnemy.h"
#include "ArenaKernelSubsystem.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraPlayerCharacter.h"
#include "SoraPracticeLobby.h"
#include "SoraProjectile.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"
#include "Templates/UniquePtr.h"

// Scripted fights in real game worlds, driven through the project's key
// mappings. Every frame records the hero, each opponent and live projectiles;
// the SHA-1 of that trace fingerprints campaign combat behaviour, so a
// refactor that claims no behaviour change must reproduce it exactly.
// SoraArena.Events.ScriptedFight replays the same fights with a listener on
// every USoraGameEvents delegate.
namespace SoraCombatTrace
{
using FHero = ASoraPlayerCharacter;
using FFoe = ASoraEnemy;

// Every gameplay event as one line of text, so a check reads like the event.
struct FEventLog
{
    TArray<FString> Lines;
    TWeakObjectPtr<USoraGameEvents> Events;
    TArray<FDelegateHandle> Handles;
    ~FEventLog() { Detach(); }

    static FString Who(const AActor* Actor)
    {
        if (!Actor)
            return TEXT("None");
        if (Actor->IsA<ASoraPlayerCharacter>())
            return TEXT("Hero");
        if (Actor->IsA<ASoraBoss>())
            return TEXT("Boss");
        if (const ASoraEnemy* Enemy = Cast<ASoraEnemy>(Actor))
            return FString::Printf(TEXT("%s%d"), Enemy->IsDojoPupil() ? TEXT("Pupil") :
                Enemy->IsBladeRetainer() ? TEXT("Retainer") : TEXT("Invader"), Enemy->EnemySlot());
        if (Actor->IsA<ASoraProjectile>())
            return TEXT("Projectile");
        return Actor->GetClass()->GetName();
    }
    static const TCHAR* ShotKind(ESoraShotKind Kind)
    {
        switch (Kind)
        {
        case ESoraShotKind::Hitscan: return TEXT("Hitscan");
        case ESoraShotKind::Shell: return TEXT("Shell");
        case ESoraShotKind::Arrow: return TEXT("Arrow");
        case ESoraShotKind::Beam: return TEXT("Beam");
        }
        return TEXT("Unknown");
    }
    static const TCHAR* Phase(ESoraBossPhase Phase)
    {
        switch (Phase)
        {
        case ESoraBossPhase::Arrived: return TEXT("Arrived");
        case ESoraBossPhase::Windup: return TEXT("Windup");
        case ESoraBossPhase::Strike: return TEXT("Strike");
        case ESoraBossPhase::Recovery: return TEXT("Recovery");
        case ESoraBossPhase::Defeated: return TEXT("Defeated");
        case ESoraBossPhase::PhaseChanged: return TEXT("PhaseChanged");
        case ESoraBossPhase::Staggered: return TEXT("Staggered");
        case ESoraBossPhase::Countered: return TEXT("Countered");
        case ESoraBossPhase::Event: return TEXT("Event");
        }
        return TEXT("Unknown");
    }
    bool Attach(UWorld* World)
    {
        USoraGameEvents* Bus = USoraGameEvents::Get(World);
        if (!Bus)
            return false;
        Events = Bus;
        Handles.Add(Bus->OnWeaponFired.AddLambda([this](const FSoraWeaponFiredEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("Fired shooter=%s weapon=%d kind=%s"), *Who(E.Shooter), E.WeaponId, ShotKind(E.Kind)));
        }));
        Handles.Add(Bus->OnMeleeCommitted.AddLambda([this](const FSoraMeleeCommittedEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("Committed attacker=%s weapon=%d windup=%.2f"), *Who(E.Attacker), E.WeaponId, E.WindupSeconds));
        }));
        Handles.Add(Bus->OnStrikeResolved.AddLambda([this](const FSoraStrikeResolvedEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("Resolved attacker=%s target=%s weapon=%d hit=%d"), *Who(E.Attacker), *Who(E.Target), E.WeaponId, E.bHit));
        }));
        Handles.Add(Bus->OnGuarded.AddLambda([this](const FSoraDefenseEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("Guarded defender=%s attacker=%s dojo=%d"), *Who(E.Defender), *Who(E.Attacker), E.bDojo));
        }));
        Handles.Add(Bus->OnParried.AddLambda([this](const FSoraDefenseEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("Parried defender=%s attacker=%s dojo=%d"), *Who(E.Defender), *Who(E.Attacker), E.bDojo));
        }));
        Handles.Add(Bus->OnDamaged.AddLambda([this](const FSoraDamagedEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("Damaged victim=%s causer=%s"), *Who(E.Victim), *Who(E.Causer)));
        }));
        Handles.Add(Bus->OnDied.AddLambda([this](const FSoraDiedEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("Died victim=%s killer=%s sparring=%d"), *Who(E.Victim), *Who(E.Killer), E.bSparring));
        }));
        Handles.Add(Bus->OnDetonated.AddLambda([this](const FSoraDetonatedEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("Detonated instigator=%s"), *Who(E.Instigator)));
        }));
        Handles.Add(Bus->OnSiteRestored.AddLambda([this](const FSoraSiteRestoredEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("SiteRestored chapter=%d site=%d campaign=%d"), E.ChapterId, E.SiteIndex, E.bCampaign));
        }));
        Handles.Add(Bus->OnChapterStarted.AddLambda([this](const FSoraChapterEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("ChapterStarted chapter=%d resumed=%d liberated=%d"), E.ChapterId, E.bResumed, E.bLiberated));
        }));
        Handles.Add(Bus->OnChapterCompleted.AddLambda([this](const FSoraChapterEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("ChapterCompleted chapter=%d liberated=%d"), E.ChapterId, E.bLiberated));
        }));
        Handles.Add(Bus->OnBossPhase.AddLambda([this](const FSoraBossPhaseEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("Boss phase=%s boss=%s detail=%s"), Phase(E.Phase), *Who(E.Boss), *E.Detail.ToString()));
        }));
        Handles.Add(Bus->OnKernelEvent.AddLambda([this](const FSoraPracticeEvent& E, uint32 Tick)
        {
            Lines.Add(FString::Printf(TEXT("Kernel kind=%u tick=%u"), E.Kind, Tick));
        }));
        Handles.Add(Bus->OnMarobashi.AddLambda([this](const FSoraMarobashiEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("Marobashi hero=%s opponent=%s awase=%d"), *Who(E.Hero), *Who(E.Opponent), E.bAfterAwase));
        }));
        Handles.Add(Bus->OnBeatStarted.AddLambda([this](const FSoraBeatEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("BeatStarted chapter=%d beat=%s resumed=%d phase=%d"), E.ChapterId, *E.BeatId, E.bResumed, E.Phase));
        }));
        Handles.Add(Bus->OnBeatCompleted.AddLambda([this](const FSoraBeatEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("BeatCompleted chapter=%d beat=%s"), E.ChapterId, *E.BeatId));
        }));
        Handles.Add(Bus->OnBeatFailed.AddLambda([this](const FSoraBeatEvent& E)
        {
            Lines.Add(FString::Printf(TEXT("BeatFailed chapter=%d beat=%s"), E.ChapterId, *E.BeatId));
        }));
        return true;
    }
    void Detach()
    {
        USoraGameEvents* Bus = Events.Get();
        if (Bus && Handles.Num() == 17)
        {
            Bus->OnWeaponFired.Remove(Handles[0]); Bus->OnMeleeCommitted.Remove(Handles[1]);
            Bus->OnStrikeResolved.Remove(Handles[2]); Bus->OnGuarded.Remove(Handles[3]);
            Bus->OnParried.Remove(Handles[4]); Bus->OnDamaged.Remove(Handles[5]);
            Bus->OnDied.Remove(Handles[6]); Bus->OnDetonated.Remove(Handles[7]);
            Bus->OnSiteRestored.Remove(Handles[8]); Bus->OnChapterStarted.Remove(Handles[9]);
            Bus->OnChapterCompleted.Remove(Handles[10]); Bus->OnBossPhase.Remove(Handles[11]);
            Bus->OnKernelEvent.Remove(Handles[12]); Bus->OnMarobashi.Remove(Handles[13]);
            Bus->OnBeatStarted.Remove(Handles[14]); Bus->OnBeatCompleted.Remove(Handles[15]);
            Bus->OnBeatFailed.Remove(Handles[16]);
        }
        Handles.Reset();
        Events.Reset();
    }
    int32 Count(const FString& Prefix) const
    {
        int32 Matches = 0;
        for (const FString& Line : Lines)
            Matches += Line.StartsWith(Prefix);
        return Matches;
    }
};

struct FRun
{
    FAutomationTestBase& Test;
    FString Name;
    FString Slot;
    TUniquePtr<FSoraAutomationWorld> World;
    FString Trace;
    int32 Frame = 0;
    FEventLog* Log = nullptr;

    FRun(FAutomationTestBase& InTest, const TCHAR* InName, FEventLog* InLog = nullptr)
        : Test(InTest), Name(InName), Slot(FSoraAutomationWorld::UniqueSaveSlot(InName)), Log(InLog)
    {
        FSoraAutomationWorld::IgnoreMissingGeneratedArt(Test);
        FSoraAutomationWorld::IgnoreAbsentSaveSlot(Test, Slot);
    }
    ~FRun()
    {
        if (Log)
            Log->Detach();
        if (World)
        {
            World->DestroyTestWorld(true);
            World->ForwardErrorMessages(&Test);
            World.Reset();
        }
        FSoraAutomationWorld::DeleteSaveSlot(Slot);
    }
    ASoraGameMode* Mode() const { return World ? World->Mode() : nullptr; }
    FHero* Hero() const { return World ? World->Player() : nullptr; }
    UWorld* Get() const { return World ? World->GetTestWorld() : nullptr; }
    APlayerController* Controller() const { return Hero() ? Cast<APlayerController>(Hero()->GetController()) : nullptr; }

    bool Fail(const FString& Message)
    {
        Test.AddError(FString::Printf(TEXT("%s frame %d: %s"), *Name, Frame, *Message));
        return false;
    }
    // A schema-6 checkpoint at the start of Beat, reached through every
    // earlier required beat with the unlocks chapter select grants.
    bool Seed(int32 Chapter, int32 Beat)
    {
        USoraSaveGame* Save = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!Save)
            return Fail(TEXT("Save object was not created"));
        if (!USoraCampaignDirector::SeedCheckpoint(*Save, Chapter, Beat))
            return Fail(TEXT("Seed checkpoint is not valid"));
        return UGameplayStatics::SaveGameToSlot(Save, Slot, 0) || Fail(TEXT("Seed save was not written"));
    }
    // Defeats the active beat's remaining opponents, one per frame, untraced.
    bool ClearBeat(int32 Beat)
    {
        for (int32 Attempt = 0; Attempt < 40 && Mode()->Campaign()->ActiveBeat() == Beat; ++Attempt)
        {
            for (TActorIterator<FFoe> It(Get()); It; ++It)
                if (It->IsEnemy() && It->IsAlive() && !It->IsActorBeingDestroyed())
                {
                    UGameplayStatics::ApplyDamage(*It, It->Health, Controller(), Hero(), UDamageType::StaticClass());
                    break;
                }
            if (!World->Tick(1))
                return Fail(TEXT("World failed to tick"));
        }
        return Mode()->Campaign()->ActiveBeat() != Beat || Fail(TEXT("Beat did not complete"));
    }
    bool Start()
    {
        World = MakeUnique<FSoraAutomationWorld>();
        // A listener attaches before the first frame, which builds the round.
        // Any key leaves the title screen for the main menu, whose first row
        // continues a saved campaign or begins a fresh one.
        if (!World->Start(Slot) || (Log && !Log->Attach(World->GetTestWorld())) || !World->Tick(1) || !World->EnableKeyInput() ||
            !World->PressKey(EKeys::Enter))
        {
            World->ForwardErrorMessages(&Test);
            return Fail(TEXT("World did not start with key input"));
        }
        return (Mode() && Hero() && Mode()->Arena()) || Fail(TEXT("World lacks its mode, hero or arena"));
    }
    // The beat's allies leave the field: a trace is the hero's own fight
    // (SoraArena.Fieldcraft.Allies plays the allies).
    bool StandAlliesAside()
    {
        for (TActorIterator<ASoraCompanion> It(Get()); It; ++It)
            It->Destroy();
        return true;
    }
    bool Key(const FKey& Key) { return World->PressKey(Key) || Fail(TEXT("Key press failed")); }
    bool Down(const FKey& Key) { return World->InjectKey(Key, IE_Pressed) || Fail(TEXT("Key down failed")); }
    bool Up(const FKey& Key) { return World->InjectKey(Key, IE_Released) || Fail(TEXT("Key up failed")); }
    bool Tap(const FKey& Key) { return Down(Key) && Up(Key); }

    FFoe* Foe(int32 EnemySlot) const
    {
        for (TActorIterator<FFoe> It(Get()); It; ++It)
            if (It->IsEnemy() && It->EnemySlot() == EnemySlot && !It->IsActorBeingDestroyed())
                return *It;
        return nullptr;
    }
    // Moves an actor beside the hero on the flat gameplay ground, keeping its height.
    bool Place(AActor* Actor, const FVector& Offset)
    {
        if (!Actor)
            return Fail(TEXT("No actor to place"));
        const FVector Base = Hero()->GetActorLocation();
        Actor->SetActorLocation(FVector(Base.X + Offset.X, Base.Y + Offset.Y, Actor->GetActorLocation().Z),
            false, nullptr, ETeleportType::TeleportPhysics);
        return true;
    }
    // A test world has no viewport, so the controller does not turn the pawn;
    // face the target as APlayerController::UpdateRotation would.
    bool Aim(const AActor* Target)
    {
        if (!Target || !Controller())
            return Fail(TEXT("No aim target"));
        const FRotator Rotation(0.f, (Target->GetActorLocation() - Hero()->GetActorLocation()).Rotation().Yaw, 0.f);
        Controller()->SetControlRotation(Rotation);
        Hero()->FaceRotation(Rotation, 0.f);
        return true;
    }
    bool Step()
    {
        if (!World->Tick(1))
        {
            World->ForwardErrorMessages(&Test);
            return Fail(TEXT("World failed to tick"));
        }
        Record();
        ++Frame;
        return true;
    }
    void Record()
    {
        const ASoraGameMode* G = Mode();
        const FHero* H = Hero();
        const FVector L = H->GetActorLocation();
        Trace += FString::Printf(TEXT("%d|%d %d %d %d %d|%.3f %.3f %.3f %.3f %.3f %d %d %d %.3f %d %d|"),
            Frame, G->Campaign()->Kills, G->bDefeated, G->bChapterComplete, static_cast<int32>(G->InputState()), G->Campaign()->DojoLessonStage(),
            L.X, L.Y, L.Z, H->GetActorRotation().Yaw, H->Health, H->WeaponId, H->GetEquipment()->Ammo, H->GetEquipment()->bReloading,
            H->GetEquipment()->GuardReserve(), H->GetEquipment()->IsCommittedStrike(), H->GetEquipment()->IsBowDrawing());
        TArray<FFoe*> Foes;
        for (TActorIterator<FFoe> It(Get()); It; ++It)
            if (It->IsEnemy())
                Foes.Add(*It);
        Foes.Sort([](const FFoe& A, const FFoe& B) { return A.EnemySlot() < B.EnemySlot(); });
        for (const FFoe* F : Foes)
        {
            const FVector P = F->GetActorLocation();
            const ASoraBoss* Boss = Cast<ASoraBoss>(F);
            Trace += FString::Printf(TEXT("%d %.3f %.3f %.3f %.3f %.3f %d;"), F->EnemySlot(), P.X, P.Y, P.Z,
                F->GetActorRotation().Yaw, F->Health, Boss && Boss->IsBossTelegraphing());
        }
        for (TActorIterator<ASoraProjectile> It(Get()); It; ++It)
        {
            const FVector P = It->GetActorLocation();
            Trace += FString::Printf(TEXT("|%.3f %.3f %.3f"), P.X, P.Y, P.Z);
        }
        Trace += TEXT("\n");
    }
    // Runs the script, then logs the trace hash and writes the trace for diffing.
    bool Play(int32 Frames, TFunctionRef<bool(FRun&, int32)> Script)
    {
        for (int32 Index = 0; Index < Frames; ++Index)
            if (!Script(*this, Index) || !Step())
                return false;
        return true;
    }
    // The scripted outcome, checked after the traced frames.
    bool Expect(const TCHAR* What, bool bHolds) { return Test.TestTrue(*FString::Printf(TEXT("%s: %s"), *Name, What), bHolds); }
    FString Finish()
    {
        const FTCHARToUTF8 Bytes(*Trace);
        FSHA1 Sha;
        Sha.Update(reinterpret_cast<const uint8*>(Bytes.Get()), Bytes.Length());
        Sha.Final();
        uint8 Digest[FSHA1::DigestSize];
        Sha.GetHash(Digest);
        const FString Hex = BytesToHex(Digest, FSHA1::DigestSize);
        FFileHelper::SaveStringToFile(Trace, *(FPaths::ProjectSavedDir() / TEXT("Diagnostics") / (TEXT("combat_trace_") + Name + TEXT(".txt"))));
        UE_LOG(LogTemp, Display, TEXT("SORA_COMBAT_TRACE: scenario=%s frames=%d kills=%d hero_health=%.3f hash=%s"),
            *Name, Frame, Mode()->Campaign()->Kills, Hero()->Health, *Hex);
        return Hex;
    }
};

// The foundry yard's first wave (ch05.b05): two blade retainers and two rifle
// enforcers from enemies.json at once (more arrive once fewer than two
// stand). Guard a retainer's cut, meet the next with a fresh guard (a parry,
// timed from the retainer's own windup), cut it down with the katana, then
// the naginata on the second retainer, the yumi, the yari, sprint and jump,
// with every arm the earlier chapters unlocked (the carbine comes later, at
// ch05.b09).
constexpr int32 RetainerChapter = 4, RetainerBeat = 4;
FString Retainer(FAutomationTestBase& Test, FEventLog* Log = nullptr)
{
    FRun Run(Test, TEXT("Retainer"), Log);
    if (!Run.Seed(RetainerChapter, RetainerBeat) || !Run.Start() || !Run.Key(EKeys::Enter) || !Run.Key(EKeys::Enter) ||
        !Run.StandAlliesAside())
        return FString();
    if (!Test.TestTrue(TEXT("Retainer scenario is in play"), Run.Mode()->IsPlaying()) || !Run.Place(Run.Foe(0), FVector(160, 0, 0)))
        return FString();
    // A blade's contact holds world time for a moment (hit-stop), so each arm
    // after the katana is taken up once the last one has recovered, and the
    // script follows the hero's own state from there rather than fixed frames.
    int32 ParryAt = INDEX_NONE, ReadyAt = INDEX_NONE, DrawAt = INDEX_NONE, ThrustAt = INDEX_NONE, RunAt = INDEX_NONE;
    const bool bOk = Run.Play(800, [&](FRun& R, int32 F)
    {
        // The guard goes up once the retainer's second cut is past half its
        // windup, inside the parry window, and comes down after the cut.
        const FFoe* Blade = R.Foe(0);
        if (ParryAt == INDEX_NONE && F > 105 && F < 240 && Blade && Blade->IsWindingUp() && Blade->WindupProgress() >= .55f)
        {
            ParryAt = F;
            return R.Down(EKeys::LeftControl);
        }
        if (ParryAt != INDEX_NONE && F == ParryAt + 14)
            return R.Up(EKeys::LeftControl);
        // The naginata: the polearms key (2) twice, past the yari.
        if (F >= 250 && F < 262)
            return R.Hero()->WeaponId == 20 || F % 4 != 2 || R.Tap(EKeys::Two);
        switch (F)
        {
        case 5: return R.Down(EKeys::LeftControl);
        case 40: return R.Up(EKeys::LeftControl);
        case 60: case 150: case 200: return R.Aim(R.Foe(0)) && R.Tap(EKeys::LeftMouseButton);
        case 265: return R.Place(R.Foe(1), FVector(220, 0, 0)) && R.Aim(R.Foe(1));
        case 270: case 330: case 390: return R.Aim(R.Foe(1)) && R.Tap(EKeys::LeftMouseButton);
        default: break;
        }
        // The hero keeps facing the second retainer through the naginata's cuts;
        // it walks the navigation mesh rather than standing on the aim line.
        if (F < 440)
            return F > 265 && R.Foe(1) && R.Foe(1)->IsAlive() ? R.Aim(R.Foe(1)) : true;
        const int32 Held = R.Hero()->WeaponId;
        // The yumi: drawn at the first rifle enforcer, a moment after it comes
        // to hand, and loosed.
        if (DrawAt == INDEX_NONE)
        {
            if (Held != 18)
                return F % 4 != 0 || R.Tap(EKeys::Three);
            if (ReadyAt == INDEX_NONE)
                ReadyAt = F;
            if (F < ReadyAt + 20)
                return true;
            DrawAt = F;
            ReadyAt = INDEX_NONE;
            return R.Aim(R.Foe(2)) && R.Down(EKeys::LeftMouseButton);
        }
        if (F == DrawAt + 50)
            return R.Up(EKeys::LeftMouseButton);
        // The yari: a thrust at the second enforcer, set two metres off.
        if (F > DrawAt + 60 && ThrustAt == INDEX_NONE)
        {
            if (Held != 19)
                return F % 4 != 0 || R.Tap(EKeys::Two);
            if (ReadyAt == INDEX_NONE)
                ReadyAt = F;
            if (F < ReadyAt + 20)
                return true;
            ThrustAt = F;
            return R.Place(R.Foe(3), FVector(200, 0, 0)) && R.Aim(R.Foe(3)) && R.Tap(EKeys::RightMouseButton);
        }
        // Sprint, and a jump in stride.
        if (ThrustAt != INDEX_NONE && RunAt == INDEX_NONE && F >= ThrustAt + 20)
        {
            RunAt = F;
            return R.Down(EKeys::LeftShift) && R.Down(EKeys::W);
        }
        if (RunAt != INDEX_NONE && F == RunAt + 25)
            return R.Tap(EKeys::SpaceBar);
        if (RunAt != INDEX_NONE && F == RunAt + 50)
            return R.Up(EKeys::LeftShift) && R.Up(EKeys::W);
        return true;
    });
    const FString Hash = Run.Finish();
    Run.Expect(TEXT("the second cut is met with a fresh guard"), ParryAt != INDEX_NONE);
    Run.Expect(TEXT("the yumi is drawn, the yari thrust and the hero sprints"), DrawAt != INDEX_NONE && ThrustAt != INDEX_NONE && RunAt != INDEX_NONE);
    Run.Expect(TEXT("the first retainer falls to the katana, both retainers fall and Nyaakoto stands"),
        bOk && Run.Mode()->Campaign()->Kills == 2 && Run.Foe(0) == nullptr && Run.Hero()->IsAlive());
    // After the traced fight, the rest of the deck falls and the next beat begins.
    if (bOk && Log && !Run.ClearBeat(RetainerBeat))
        return FString();
    return bOk ? Hash : FString();
}

// The first fight after the arc carbine is assembled (ch05.b10): four rifle
// enforcers from enemies.json at once. The carbine comes to hand on its key,
// held fire cuts down the first enforcer (kept six metres off, in front of
// the muzzle), a reload refills the magazine, and a second enforcer, kept in
// the open seven metres off, finds Nyaakoto with its bursts.
constexpr int32 CarbineChapter = 4, CarbineBeat = 9, CarbineMagazine = 24;
FString Carbine(FAutomationTestBase& Test, FEventLog* Log = nullptr)
{
    FRun Run(Test, TEXT("Carbine"), Log);
    if (!Run.Seed(CarbineChapter, CarbineBeat) || !Run.Start() || !Run.Key(EKeys::Enter) || !Run.Key(EKeys::Enter) ||
        !Run.StandAlliesAside())
        return FString();
    if (!Test.TestTrue(TEXT("Carbine scenario is in play"), Run.Mode()->IsPlaying()) ||
        !Test.TestNotNull(TEXT("The first enforcer stands"), Run.Foe(0)))
        return FString();
    int32 FellAt = INDEX_NONE, ReloadAt = INDEX_NONE, HitAt = INDEX_NONE;
    const bool bOk = Run.Play(480, [&](FRun& R, int32 F)
    {
        // The carbine: the firearms key (4) until it is in hand.
        if (F < 20)
            return F < 5 || R.Hero()->WeaponId == 1 || F % 4 != 1 || R.Tap(EKeys::Four);
        FFoe* Target = R.Foe(0);
        if (FellAt == INDEX_NONE)
        {
            if (!Target || !Target->IsAlive())
            {
                FellAt = F;
                return R.Up(EKeys::LeftMouseButton);
            }
            // The enforcer is kept in front of the muzzle while the trigger is held.
            if (F == 20)
                return R.Place(Target, FVector(600, 0, 0)) && R.Aim(Target) && R.Down(EKeys::LeftMouseButton);
            if (F % 10 == 0 && !R.Place(Target, FVector(600, 0, 0)))
                return false;
            return R.Aim(Target);
        }
        if (ReloadAt == INDEX_NONE && F >= FellAt + 5)
        {
            ReloadAt = F;
            return R.Tap(EKeys::R);
        }
        // The next enforcer stands in the open until its rounds land.
        if (HitAt == INDEX_NONE && ReloadAt != INDEX_NONE && R.Hero()->Health < R.Hero()->MaxHealth)
            HitAt = F;
        if (HitAt == INDEX_NONE && ReloadAt != INDEX_NONE && (F - ReloadAt) % 20 == 10)
            return R.Place(R.Foe(1), FVector(700, 150, 0));
        return true;
    });
    const FString Hash = Run.Finish();
    const USoraEquipmentComponent* Kit = Run.Hero()->GetEquipment();
    Run.Expect(TEXT("the first enforcer falls to the carbine"), bOk && FellAt != INDEX_NONE && Run.Mode()->Campaign()->Kills == 1);
    Run.Expect(TEXT("the reload refills the carbine's magazine"), ReloadAt != INDEX_NONE && Run.Hero()->WeaponId == 1 &&
        !Kit->bReloading && Kit->Ammo == CarbineMagazine);
    Run.Expect(TEXT("an enforcer's rounds find Nyaakoto, who stands"), HitAt != INDEX_NONE && Run.Hero()->IsAlive());
    return bOk ? Hash : FString();
}

// The dojo's lesson duels (ch01.b02-b03): stance, guard, two parries (awase
// ×2) and recovery through real Block and Fire presses against one sparring
// pupil, then the lesson's two scored bouts with the bokken, the second pupil
// stepping in for the first, which opens the 転 lesson (ch01.b04). The pupil
// walks its own footwork and a blade's contact holds the world for a moment
// (hit-stop), so the script answers the pupil rather than the frame count: a
// pupil that strays is set back in front, each awase is a fresh guard in the
// last stretch of the pupil's windup (its cut lands 0.55 s of world time after
// the windup begins, and a guard younger than 260 ms meets it), and the bouts'
// swings come every twelve frames while a pupil stands.
FString Dojo(FAutomationTestBase& Test, FEventLog* Log = nullptr)
{
    FRun Run(Test, TEXT("Dojo"), Log);
    if (!Run.Seed(0, 1) || !Run.Start() || !Run.Key(EKeys::Enter) || !Run.Key(EKeys::Enter))
        return FString();
    // The opening lesson is now a measured distance drill before any pupil
    // attacks. Keep the trace's guard/parry section at its original start.
    if(!Run.Down(EKeys::LeftControl)||!Run.World->Tick(45)||!Run.Up(EKeys::LeftControl)||
        !SoraMaaiAutomation::Walk(*Run.World)) return FString();
    if (!Test.TestTrue(TEXT("Dojo scenario is in play"), Run.Mode()->IsPlaying()) || !Run.Place(Run.Foe(0), FVector(150, 0, 0)) || !Run.Aim(Run.Foe(0)))
        return FString();
    double WindupAt = -1.0;
    bool bGuardUp = false, bSecondStepsIn = false;
    const bool bOk = Run.Play(900, [&](FRun& R, int32 F)
    {
        const USoraCampaignDirector* Campaign = R.Mode()->Campaign();
        const double Now = R.Get()->GetTimeSeconds();
        FFoe* Pupil = R.Foe(0) && R.Foe(0)->IsAlive() ? R.Foe(0) : R.Foe(1) && R.Foe(1)->IsAlive() ? R.Foe(1) : nullptr;
        // Stance, then the guard held through a cut.
        if (F == 0)
            return R.Down(EKeys::LeftControl);
        if (F == 120)
            return R.Up(EKeys::LeftControl);
        if (F < 130 || !Pupil)
            return true;
        // The second pupil steps in once the first has yielded.
        if (Pupil == R.Foe(1) && !bSecondStepsIn)
        {
            bSecondStepsIn = true;
            return R.Place(Pupil, FVector(150, 0, 0)) && R.Aim(Pupil);
        }
        if (!Pupil->IsPupilWindup() && FVector::Dist2D(Pupil->GetActorLocation(), R.Hero()->GetActorLocation()) > 170.f && F % 30 == 0)
            return R.Place(Pupil, FVector(150, 0, 0)) && R.Aim(Pupil);
        if (Campaign->DojoLessonStage() == 2)
        {
            // Awase: the guard goes up 0.38 s into the windup and down after the cut.
            if (WindupAt < 0.0 && Pupil->IsPupilWindup())
                WindupAt = Now;
            if (WindupAt >= 0.0 && !bGuardUp && Now >= WindupAt + .38)
            {
                bGuardUp = true;
                return R.Aim(Pupil) && R.Down(EKeys::LeftControl);
            }
            if (bGuardUp && Now >= WindupAt + .8)
            {
                bGuardUp = false; WindupAt = -1.0;
                return R.Up(EKeys::LeftControl);
            }
            return R.Aim(Pupil);
        }
        if (bGuardUp)
        {
            bGuardUp = false; WindupAt = -1.0;
            return R.Up(EKeys::LeftControl);
        }
        // Recovery, then the bouts: a cut every twelve frames.
        return F % 12 == 0 ? R.Aim(Pupil) && R.Tap(EKeys::LeftMouseButton) : true;
    });
    const FString Hash = Run.Finish();
    const USoraCampaignDirector* Campaign = Run.Mode()->Campaign();
    Run.Expect(TEXT("all four forms are learned, awase twice, and two pupils yield in the lesson's bouts"),
        bOk && Campaign->DojoLessonStage() == 4 && (Campaign->Progress().CompletedMask & SoraBeatRules::BeatBit(2)) != 0u &&
        Campaign->ActiveBeat() == 3);
    return bOk ? Hash : FString();
}

// The final chapter restored at its boss (ch08.b14): High Collector Val Amort
// with his beam and cleave, and carbine fire his ledger shards intercept. The
// story's blow then brings him to his cane phase (the phases between are
// SoraArena.Boss.ValAmort's), where no weapon finishes him: the katana goes
// into its scabbard on the Sheathe key, and a guard pressed just before his
// final foreclosure lands takes his cane (mutō-dori). He yields and E binds
// him (captured, not killed), Enter skips the aftermath cinematic and the
// registry is carried to the last site. With a listener attached the chapter
// then plays out to liberation.
constexpr int32 CollectorChapter = 7, CollectorBeat = 13, BossSlot = 0;
FString Collector(FAutomationTestBase& Test, FEventLog* Log = nullptr)
{
    FRun Run(Test, TEXT("Collector"), Log);
    if (!Run.Seed(CollectorChapter, CollectorBeat) || !Run.Start() || !Run.Key(EKeys::Enter))
        return FString();
    if (!Test.TestTrue(TEXT("Collector scenario is in play"), Run.Mode()->IsPlaying()) ||
        !Test.TestNotNull(TEXT("The collector waits at its checkpoint"), Run.Mode()->Campaign()->CampaignBoss()))
        return FString();
    // Keep this isolated combat setup on clear summit floor, outside the
    // central dais/spine and inside the open edge. Traversal is tested separately.
    const FVector ArenaCenter=Run.Mode()->Campaign()->CampaignBoss()->ArenaCenter();
    Run.Hero()->SetActorLocation(FVector(ArenaCenter.X-800,ArenaCenter.Y-900,Run.Hero()->GetActorLocation().Z),
        false,nullptr,ETeleportType::TeleportPhysics);
    if(!Run.Place(Run.Foe(BossSlot),FVector(600,0,0))) return FString();
    // Let the collector finish his 1.2-second cleave before the injected
    // phase change. Cancelling its windup would leave no resolved melee hit
    // for the listener contract to observe.
    constexpr int32 CaneAt = 450;
    int32 TakenAt = INDEX_NONE, GuardAt = INDEX_NONE, Attempts = 0;
    const bool bOk = Run.Play(900, [&](FRun& R, int32 F)
    {
        const auto MoveTo = [&R](const FVector& Point)
        {
            R.Hero()->SetActorLocation(FVector(Point.X, Point.Y, R.Hero()->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
        };
        if (TakenAt != INDEX_NONE)
        {
            FVector Point;
            // The yielded collector waits where he knelt; E beside him binds him.
            if (F == TakenAt + 5)
            {
                if (!R.Mode()->Campaign()->AwaitingCapture() || !R.Mode()->Campaign()->ObjectiveAnchor(Point))
                    return R.Fail(TEXT("The collector did not yield to be captured"));
                MoveTo(Point);
                return R.Tap(EKeys::E);
            }
            // Enter skips the aftermath cinematic; the registry box is carried
            // from the canal steps to the notice board at the last site.
            if (F == TakenAt + 15)
                return R.Tap(EKeys::Enter);
            if (F == TakenAt + 30 || F == TakenAt + 40)
            {
                if (!R.Mode()->Campaign()->ObjectiveAnchor(Point))
                    return R.Fail(TEXT("The registry has no pickup or drop-off"));
                MoveTo(Point);
                return R.Tap(EKeys::E);
            }
            return true;
        }
        FFoe* Foe = R.Foe(BossSlot);
        const ASoraBoss* Boss = Cast<ASoraBoss>(Foe);
        if (F > CaneAt && (!Boss || Boss->IsDefeated()))
        {
            if (!Boss)
                return R.Fail(TEXT("The collector is gone before his capture"));
            TakenAt = F;
            return R.Up(EKeys::LeftControl);
        }
        // The carbine: the firearms key (4) until it is in hand.
        if (F >= 5 && F < 20)
            return R.Hero()->WeaponId == 1 || F % 4 != 1 || R.Tap(EKeys::Four);
        switch (F)
        {
        case 20: return R.Down(EKeys::D);
        case 60: return R.Up(EKeys::D);
        case 150: return R.Place(Foe, FVector(250, 0, 0)) && R.Aim(Foe);
        case 160: return R.Down(EKeys::LeftMouseButton);
        case 300: return R.Up(EKeys::LeftMouseButton);
        case CaneAt:
            if (!Foe)
                return R.Fail(TEXT("The collector is gone before his cane phase"));
            UGameplayStatics::ApplyDamage(Foe, Foe->Health - Foe->MaxHealth * .4f, R.Controller(), R.Hero(), UDamageType::StaticClass());
            return true;
        case CaneAt + 2: return R.Tap(EKeys::One);
        case CaneAt + 4:
        {
            // The cane phase stays clear of the physical spine and dais;
            // the hero stands two metres off, facing him.
            if (!Boss)
                return R.Fail(TEXT("The collector is gone before his cane phase"));
            const FVector Stand(Boss->ArenaCenter().X, Boss->ArenaCenter().Y-1000, Foe->GetActorLocation().Z);
            Foe->SetActorLocation(Stand, false, nullptr, ETeleportType::TeleportPhysics);
            MoveTo(Stand - FVector(220.f, 0.f, 0.f));
            return R.Aim(Foe);
        }
        case CaneAt + 10: return R.Tap(EKeys::V);
        default: break;
        }
        if (F <= CaneAt + 10 || !Boss)
            return true;
        // Sheathed and facing him, a guard pressed in the foreclosure's last
        // 100 ms; released after it, ready for the next if one is needed.
        const FSoraBossAttack* Attack = Boss->BossAttack();
        if (GuardAt == INDEX_NONE && Attack && Attack->bMuto && Boss->IsBossTelegraphing() && Boss->BossWarningSeconds() <= .1f &&
            R.Hero()->GetEquipment()->IsSheathed())
        {
            GuardAt = F;
            ++Attempts;
            return R.Aim(Foe) && R.Down(EKeys::LeftControl);
        }
        if (GuardAt != INDEX_NONE && F >= GuardAt + 20)
        {
            GuardAt = INDEX_NONE;
            return R.Up(EKeys::LeftControl);
        }
        return R.Aim(Foe);
    });
    const FString Hash = Run.Finish();
    const USoraCampaignDirector* Campaign = Run.Mode()->Campaign();
    Run.Expect(TEXT("the collector is taken by mutō-dori on the first foreclosure"), TakenAt != INDEX_NONE && Attempts == 1);
    Run.Expect(TEXT("the collector yields, is captured, and the registry restores the last site"),
        bOk && !Campaign->CampaignBoss() && Run.Mode()->Arena()->ActivatedMask() == 7 && Campaign->ActiveBeat() == 16);
    if (bOk && Log)
    {
        // Arrival at the torii starts walk-and-talk. Interact at the name
        // board then starts the plaque exchange; only its final line unlocks
        // the closing cinematic. Enter cannot replace either world event.
        const auto WaitForLines=[&]()
        {
            for(int32 Frame=0;Frame<600&&Campaign->LinesQueued()>0;++Frame)
                if(!Run.World->Tick(1,.1f)) return false;
            return Run.Expect(TEXT("the epilogue dialogue finishes without skipping"),Campaign->LinesQueued()==0);
        };
        if(!WaitForLines()) return FString();
        FVector At;
        if(!Run.Expect(TEXT("the epilogue first requires torii arrival"),
            Campaign->ObjectiveAnchor(At)&&!Campaign->AnchorTakesInteract())) return FString();
        Run.Hero()->SetActorLocation(FVector(At.X,At.Y,Run.Hero()->GetActorLocation().Z),false,nullptr,ETeleportType::TeleportPhysics);
        if(!Run.World->Tick(2)||!WaitForLines()) return FString();
        if(!Run.Expect(TEXT("the name board requires ordinary Interact"),
            Campaign->ObjectiveAnchor(At)&&Campaign->AnchorTakesInteract())) return FString();
        Run.Hero()->SetActorLocation(FVector(At.X,At.Y,Run.Hero()->GetActorLocation().Z),false,nullptr,ETeleportType::TeleportPhysics);
        if(!Run.Key(EKeys::E)||!WaitForLines()||!Run.World->Tick(1)) return FString();
        if(!Run.Expect(TEXT("the plaque exchange unlocks the closing cinematic"),
            Campaign->ActiveBeat()==17&&Run.Mode()->Arena()->RehungPlaques()==2)) return FString();
        if (!Run.Key(EKeys::Enter)||!Run.World->Tick(1))
            return FString();
        Run.Expect(TEXT("Nyaagyu is liberated"), Run.Mode()->bChapterComplete && Campaign->bCampaignComplete);
    }
    return bOk ? Hash : FString();
}

// The training arena with the Hanabi class: grenade and mortar shells, a
// reload, and the kanabo's swept melee.
FString Training(FAutomationTestBase& Test, FEventLog* Log = nullptr)
{
    FRun Run(Test, TEXT("Training"), Log);
    if (!Run.Start())
        return FString();
    // The training arena has no front-end entry. Enter it as the retired M and
    // F4 menu keys did: Lantern Ward, then the Hanabi class, then play.
    ASoraGameMode* Mode = Run.Mode();
    Mode->bCampaign = false;
    Mode->MapId = 1;
    Mode->ResetRound();
    Mode->SelectedClass = 3;
    Mode->ResetRound();
    Mode->BeginRound();
    if (!Run.World->Tick(2))
        return FString();
    if (!Test.TestTrue(TEXT("Training arena is in play"), Run.Mode()->IsPlaying() && !Run.Mode()->bCampaign))
        return FString();
    const bool bOk = Run.Play(440, [](FRun& R, int32 F)
    {
        switch (F)
        {
        case 0: return R.Place(R.Foe(1), FVector(700, 0, 0));
        case 5: return R.Aim(R.Foe(1)) && R.Tap(EKeys::LeftMouseButton);
        // The wounded Invader1 stands 250 cm from the next shell's target,
        // inside its 360 cm blast.
        case 65: return R.Place(R.Foe(1), FVector(700, 0, 0)) && R.Place(R.Foe(2), FVector(700, 250, 0));
        case 70: return R.Aim(R.Foe(2)) && R.Tap(EKeys::LeftMouseButton);
        case 140: return R.Tap(EKeys::R);
        // Far enough from the wounded Invader2 that the mortar's blast reaches
        // only the invader it targets, on a line between the torii's pillars.
        case 290: return R.Tap(EKeys::Three) && R.Place(R.Foe(3), FVector(1200, -400, 0));
        case 310: return R.Aim(R.Foe(3)) && R.Tap(EKeys::LeftMouseButton);
        case 360: return R.Tap(EKeys::Two);
        case 370: return R.Place(R.Foe(0), FVector(120, 0, 0)) && R.Aim(R.Foe(0));
        case 380: return R.Tap(EKeys::LeftMouseButton);
        default: return true;
        }
    });
    const FString Hash = Run.Finish();
    Run.Expect(TEXT("a shell defeats an invader"), bOk && Run.Mode()->Campaign()->Kills == 1);
    return bOk ? Hash : FString();
}
// Deterministic practice announces every kernel event of every step, with the
// tick that step ended on.
bool KernelEvents(FAutomationTestBase& Test, FEventLog& Log)
{
    FRun Run(Test, TEXT("KernelEvents"), &Log);
    if (!Run.Start())
        return false;
    // The practice lobby's start with the saved class and map, six players.
    FSoraPracticeLobbySelection Selection;
    Selection.ClassId = Run.Mode()->SelectedClass;
    Selection.MapId = Run.Mode()->MapId;
    Selection.PlayerCount = 6;
    if (!Run.Mode()->StartPracticeFromLobby(Selection) || !Run.World->Tick(2))
        return false;
    const UArenaKernelSubsystem* Kernel = Run.Mode()->Kernel();
    if (!Test.TestTrue(TEXT("Practice runs on the staged kernel"), Kernel && Kernel->PracticeActive() && Run.Mode()->IsPlaying()))
        return false;
    // The world opened on the dojo chapter before practice replaced it.
    const int32 BeforePractice = Log.Lines.Num();
    int32 Total = 0;
    for (int32 Frame = 0; Frame < 300; ++Frame)
    {
        const int32 Before = Log.Count(TEXT("Kernel "));
        if (!Run.Step())
            return false;
        const int32 Announced = Log.Count(TEXT("Kernel ")) - Before;
        // One 1/60 s frame is one kernel step, so the frame announces that step's events.
        if (!Test.TestEqual(*FString::Printf(TEXT("Frame %d announces each kernel event"), Frame), Announced, Kernel->PracticeEvents.Num()))
            return false;
        if (Announced > 0 && !Test.TestTrue(TEXT("Kernel events carry their tick"),
            Log.Lines.Last().EndsWith(FString::Printf(TEXT(" tick=%u"), Kernel->PracticeTick))))
            return false;
        Total += Announced;
    }
    Test.TestTrue(TEXT("Practice combat produced kernel events"), Total > 0);
    Test.TestEqual(TEXT("Practice raises only kernel events"), Log.Lines.Num() - BeforePractice, Total);
    UE_LOG(LogTemp, Display, TEXT("SORA_KERNEL_EVENTS_OK: frames=300 events=%d"), Total);
    return true;
}

void Expect(FAutomationTestBase& Test, const FEventLog& Log, const TCHAR* Scenario, const FString& Prefix, int32 Minimum = 1)
{
    Test.TestTrue(*FString::Printf(TEXT("%s announces at least %d '%s'"), Scenario, Minimum, *Prefix), Log.Count(Prefix) >= Minimum);
}
} // namespace SoraCombatTrace

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraCombatTraceTest,
    "SoraArena.Campaign.CombatTrace",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraCombatTraceTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCombatTrace;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    TestFalse(TEXT("Retainer fight completes"), Retainer(*this).IsEmpty());
    TestFalse(TEXT("Carbine fight completes"), Carbine(*this).IsEmpty());
    TestFalse(TEXT("Dojo lessons and bouts complete"), Dojo(*this).IsEmpty());
    TestFalse(TEXT("Collector fight completes"), Collector(*this).IsEmpty());
    TestFalse(TEXT("Training arena fight completes"), Training(*this).IsEmpty());
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraScriptedFightEventsTest,
    "SoraArena.Events.ScriptedFight",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraScriptedFightEventsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    using namespace SoraCombatTrace;
    if (!TestTrue(TEXT("Offline catalog loads"), FSoraCatalog::Get().Load()))
        return false;
    // Listeners observe only: each fight must trace identically with and without them.
    FEventLog RetainerLog, CarbineLog, DojoLog, CollectorLog, TrainingLog, KernelLog;
    TestEqual(TEXT("Retainer fight is unchanged by listeners"), Retainer(*this, &RetainerLog), Retainer(*this));
    TestEqual(TEXT("Carbine fight is unchanged by listeners"), Carbine(*this, &CarbineLog), Carbine(*this));
    TestEqual(TEXT("Dojo is unchanged by listeners"), Dojo(*this, &DojoLog), Dojo(*this));
    TestEqual(TEXT("Collector fight is unchanged by listeners"), Collector(*this, &CollectorLog), Collector(*this));
    TestEqual(TEXT("Training fight is unchanged by listeners"), Training(*this, &TrainingLog), Training(*this));
    // Each fight's announced events, for reading a failed expectation.
    for (const TPair<const TCHAR*, const FEventLog*>& Fight : {TPair<const TCHAR*, const FEventLog*>(TEXT("Retainer"), &RetainerLog),
        TPair<const TCHAR*, const FEventLog*>(TEXT("Carbine"), &CarbineLog), TPair<const TCHAR*, const FEventLog*>(TEXT("Dojo"), &DojoLog), TPair<const TCHAR*, const FEventLog*>(TEXT("Collector"), &CollectorLog),
        TPair<const TCHAR*, const FEventLog*>(TEXT("Training"), &TrainingLog)})
        FFileHelper::SaveStringToFile(FString::Join(Fight.Value->Lines, TEXT("\n")),
            *(FPaths::ProjectSavedDir() / TEXT("Diagnostics") / (FString(TEXT("scripted_fight_")) + Fight.Key + TEXT(".txt"))));

    const TCHAR* Scenario = TEXT("Foundry yard");
    TestEqual(TEXT("The chapter starts once, at its checkpoint"), RetainerLog.Count(TEXT("ChapterStarted ")), 1);
    Expect(*this, RetainerLog, Scenario, TEXT("ChapterStarted chapter=4 resumed=1 liberated=0"));
    Expect(*this, RetainerLog, Scenario, TEXT("BeatStarted chapter=4 beat=ch05.b05 resumed=1 phase=0"));
    Expect(*this, RetainerLog, Scenario, TEXT("Guarded defender=Hero attacker=Retainer0 dojo=0"));
    Expect(*this, RetainerLog, Scenario, TEXT("Parried defender=Hero attacker=Retainer0 dojo=0"));
    Expect(*this, RetainerLog, Scenario, TEXT("Committed attacker=Retainer0 weapon=0 windup=0.42"));
    Expect(*this, RetainerLog, Scenario, TEXT("Committed attacker=Hero weapon=0 windup=0.20"), 3);
    Expect(*this, RetainerLog, Scenario, TEXT("Committed attacker=Hero weapon=20"));
    Expect(*this, RetainerLog, Scenario, TEXT("Committed attacker=Hero weapon=19 windup=0.29"));
    Expect(*this, RetainerLog, Scenario, TEXT("Resolved attacker=Hero target=Retainer0 weapon=0 hit=1"), 3);
    Expect(*this, RetainerLog, Scenario, TEXT("Resolved attacker=Retainer0 target=Hero weapon=0 hit=1"));
    Expect(*this, RetainerLog, Scenario, TEXT("Damaged victim=Retainer0 causer=Hero"), 3);
    Expect(*this, RetainerLog, Scenario, TEXT("Died victim=Retainer0 killer=Hero sparring=0"));
    Expect(*this, RetainerLog, Scenario, TEXT("Resolved attacker=Hero target=Retainer1 weapon=20 hit=1"));
    Expect(*this, RetainerLog, Scenario, TEXT("Fired shooter=Hero weapon=18 kind=Arrow"));
    Expect(*this, RetainerLog, Scenario, TEXT("Fired shooter=Invader"));
    Expect(*this, RetainerLog, Scenario, TEXT("BeatCompleted chapter=4 beat=ch05.b05"));
    Expect(*this, RetainerLog, Scenario, TEXT("BeatStarted chapter=4 beat=ch05.b06 resumed=0 phase=0"));

    // The hero's carbine: hitscan rounds that land and kill, and the
    // enforcers' fire that lands on him.
    Scenario = TEXT("Carbine");
    Expect(*this, CarbineLog, Scenario, TEXT("BeatStarted chapter=4 beat=ch05.b10 resumed=1 phase=0"));
    Expect(*this, CarbineLog, Scenario, TEXT("Fired shooter=Hero weapon=1 kind=Hitscan"), 4);
    Expect(*this, CarbineLog, Scenario, TEXT("Damaged victim=Invader0 causer=Hero"), 4);
    Expect(*this, CarbineLog, Scenario, TEXT("Died victim=Invader0 killer=Hero sparring=0"));
    Expect(*this, CarbineLog, Scenario, TEXT("Fired shooter=Invader"));
    Expect(*this, CarbineLog, Scenario, TEXT("Damaged victim=Hero causer=Invader"));

    Scenario = TEXT("Dojo");
    Expect(*this, DojoLog, Scenario, TEXT("ChapterStarted chapter=0 resumed=1 liberated=0"));
    Expect(*this, DojoLog, Scenario, TEXT("BeatCompleted chapter=0 beat=ch01.b02"));
    Expect(*this, DojoLog, Scenario, TEXT("BeatCompleted chapter=0 beat=ch01.b03"));
    Expect(*this, DojoLog, Scenario, TEXT("SiteRestored chapter=0 site=1 campaign=1"));
    Expect(*this, DojoLog, Scenario, TEXT("Guarded defender=Hero attacker=Pupil0 dojo=1"));
    Expect(*this, DojoLog, Scenario, TEXT("Parried defender=Hero attacker=Pupil0 dojo=1"), 2);
    Expect(*this, DojoLog, Scenario, TEXT("Committed attacker=Pupil0 weapon=0 windup=0.55"), 2);
    Expect(*this, DojoLog, Scenario, TEXT("Committed attacker=Hero weapon=0 windup=0.00"), 4);
    Expect(*this, DojoLog, Scenario, TEXT("Resolved attacker=Hero target=Pupil0 weapon=0 hit=0"));
    Expect(*this, DojoLog, Scenario, TEXT("Resolved attacker=Hero target=Pupil0 weapon=0 hit=1"), 3);
    Expect(*this, DojoLog, Scenario, TEXT("Died victim=Pupil0 killer=Hero sparring=1"));
    TestEqual(TEXT("Dojo raises no ranged fire"), DojoLog.Count(TEXT("Fired ")), 0);

    Scenario = TEXT("Final chapter");
    Expect(*this, CollectorLog, Scenario, TEXT("ChapterStarted chapter=7 resumed=1 liberated=0"));
    Expect(*this, CollectorLog, Scenario, TEXT("Boss phase=Arrived boss=Boss"));
    Expect(*this, CollectorLog, Scenario, TEXT("Boss phase=Windup boss=Boss"), 2);
    Expect(*this, CollectorLog, Scenario, TEXT("Boss phase=Strike boss=Boss"), 2);
    Expect(*this, CollectorLog, Scenario, TEXT("Boss phase=Recovery boss=Boss"), 2);
    Expect(*this, CollectorLog, Scenario, TEXT("Fired shooter=Boss weapon=-1 kind=Beam"));
    Expect(*this, CollectorLog, Scenario, TEXT("Resolved attacker=Boss target=Hero weapon=-1 hit=1"));
    Expect(*this, CollectorLog, Scenario, TEXT("Damaged victim=Hero causer=Boss"));
    // His ledger shards take the carbine's rounds; the story's blow takes him
    // to his cane phase, and mutō-dori, not a blow, takes him.
    Expect(*this, CollectorLog, Scenario, TEXT("Boss phase=Event boss=Boss detail=ward_blocked"));
    Expect(*this, CollectorLog, Scenario, TEXT("Damaged victim=Boss causer=Hero"));
    Expect(*this, CollectorLog, Scenario, TEXT("Boss phase=PhaseChanged boss=Boss detail=amort_p3_cane"));
    Expect(*this, CollectorLog, Scenario, TEXT("Boss phase=Windup boss=Boss detail=amort_final_foreclosure"));
    TestEqual(TEXT("The collector falls once"), CollectorLog.Count(TEXT("Boss phase=Defeated boss=Boss")), 1);
    Expect(*this, CollectorLog, Scenario, TEXT("Boss phase=Defeated boss=Boss detail=muto_dori"));
    TestEqual(TEXT("The foreclosure is taken, not guarded or parried"),
        CollectorLog.Count(TEXT("Guarded defender=Hero attacker=Boss")) + CollectorLog.Count(TEXT("Parried defender=Hero attacker=Boss")), 0);
    // High Collector Val Amort is taken, never killed (katsujinken).
    Expect(*this, CollectorLog, Scenario, TEXT("Died victim=Boss killer=Hero sparring=1"));
    Expect(*this, CollectorLog, Scenario, TEXT("BeatCompleted chapter=7 beat=ch08.b14"));
    Expect(*this, CollectorLog, Scenario, TEXT("BeatCompleted chapter=7 beat=ch08.b15"));
    Expect(*this, CollectorLog, Scenario, TEXT("SiteRestored chapter=7 site=2 campaign=1"));
    Expect(*this, CollectorLog, Scenario, TEXT("BeatCompleted chapter=7 beat=ch08.b17"));
    Expect(*this, CollectorLog, Scenario, TEXT("BeatStarted chapter=7 beat=ch08.b18 resumed=0 phase=0"));
    Expect(*this, CollectorLog, Scenario, TEXT("ChapterCompleted chapter=7 liberated=1"));

    Scenario = TEXT("Training arena");
    // The world opens on the dojo; the arena rounds that replace it are not chapters.
    TestEqual(TEXT("Only the opening dojo round starts a chapter"), TrainingLog.Count(TEXT("ChapterStarted ")), 1);
    Expect(*this, TrainingLog, Scenario, TEXT("ChapterStarted chapter=0 resumed=0 liberated=0"));
    Expect(*this, TrainingLog, Scenario, TEXT("Fired shooter=Hero weapon=7 kind=Shell"), 2);
    Expect(*this, TrainingLog, Scenario, TEXT("Fired shooter=Hero weapon=15 kind=Shell"));
    Expect(*this, TrainingLog, Scenario, TEXT("Detonated instigator=Hero"), 3);
    Expect(*this, TrainingLog, Scenario, TEXT("Damaged victim=Invader1 causer=Projectile"));
    Expect(*this, TrainingLog, Scenario, TEXT("Died victim=Invader1 killer=Projectile sparring=0"));
    Expect(*this, TrainingLog, Scenario, TEXT("Committed attacker=Hero weapon=6 windup=0.30"));
    Expect(*this, TrainingLog, Scenario, TEXT("Resolved attacker=Hero target=Retainer0 weapon=6 hit=1"));

    KernelEvents(*this, KernelLog);
    if(HasAnyErrors()) return false;
    UE_LOG(LogTemp, Display, TEXT("SORA_SCRIPTED_FIGHT_EVENTS_OK: invasion=%d carbine=%d dojo=%d collector=%d training=%d kernel=%d"),
        RetainerLog.Lines.Num(), CarbineLog.Lines.Num(), DojoLog.Lines.Num(), CollectorLog.Lines.Num(), TrainingLog.Lines.Num(), KernelLog.Lines.Num());
    return true;
}
#endif
