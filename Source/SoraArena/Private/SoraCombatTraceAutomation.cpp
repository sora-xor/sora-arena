#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraAutomationWorld.h"
#include "SoraBoss.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "ArenaKernelSubsystem.h"
#include "SoraEquipmentComponent.h"
#include "SoraGameEvents.h"
#include "SoraPlayerCharacter.h"
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
            Lines.Add(FString::Printf(TEXT("Boss phase=%s boss=%s"), Phase(E.Phase), *Who(E.Boss)));
        }));
        Handles.Add(Bus->OnKernelEvent.AddLambda([this](const FSoraPracticeEvent& E, uint32 Tick)
        {
            Lines.Add(FString::Printf(TEXT("Kernel kind=%u tick=%u"), E.Kind, Tick));
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
        if (Bus && Handles.Num() == 16)
        {
            Bus->OnWeaponFired.Remove(Handles[0]); Bus->OnMeleeCommitted.Remove(Handles[1]);
            Bus->OnStrikeResolved.Remove(Handles[2]); Bus->OnGuarded.Remove(Handles[3]);
            Bus->OnParried.Remove(Handles[4]); Bus->OnDamaged.Remove(Handles[5]);
            Bus->OnDied.Remove(Handles[6]); Bus->OnDetonated.Remove(Handles[7]);
            Bus->OnSiteRestored.Remove(Handles[8]); Bus->OnChapterStarted.Remove(Handles[9]);
            Bus->OnChapterCompleted.Remove(Handles[10]); Bus->OnBossPhase.Remove(Handles[11]);
            Bus->OnKernelEvent.Remove(Handles[12]); Bus->OnBeatStarted.Remove(Handles[13]);
            Bus->OnBeatCompleted.Remove(Handles[14]); Bus->OnBeatFailed.Remove(Handles[15]);
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
        if (!World->Start(Slot) || (Log && !Log->Attach(World->GetTestWorld())) || !World->Tick(1) || !World->EnableKeyInput())
        {
            World->ForwardErrorMessages(&Test);
            return Fail(TEXT("World did not start with key input"));
        }
        return (Mode() && Hero() && Mode()->Arena()) || Fail(TEXT("World lacks its mode, hero or arena"));
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

// The flagship's first deck fight (ch07.b08), four opponents at once (more
// arrive once fewer than two stand): guard and parry a blade retainer, cut it
// down with the katana, then carbine, reload, yumi, yari, sprint and jump,
// with every arm the earlier chapters unlocked.
constexpr int32 RetainerChapter = 6, RetainerBeat = 7;
FString Retainer(FAutomationTestBase& Test, FEventLog* Log = nullptr)
{
    FRun Run(Test, TEXT("Retainer"), Log);
    if (!Run.Seed(RetainerChapter, RetainerBeat) || !Run.Start() || !Run.Key(EKeys::Enter) || !Run.Key(EKeys::Enter))
        return FString();
    if (!Test.TestTrue(TEXT("Retainer scenario is in play"), Run.Mode()->IsPlaying()) || !Run.Place(Run.Foe(0), FVector(160, 0, 0)))
        return FString();
    const bool bOk = Run.Play(640, [](FRun& R, int32 F)
    {
        switch (F)
        {
        case 5: return R.Down(EKeys::LeftControl);
        case 40: return R.Up(EKeys::LeftControl);
        case 60: case 150: case 200: return R.Aim(R.Foe(0)) && R.Tap(EKeys::LeftMouseButton);
        case 116: return R.Down(EKeys::LeftControl);
        case 135: return R.Up(EKeys::LeftControl);
        case 250: return R.Tap(EKeys::One);
        case 270: return R.Aim(R.Foe(1)) && R.Down(EKeys::LeftMouseButton);
        case 330: return R.Up(EKeys::LeftMouseButton);
        case 340: return R.Tap(EKeys::R);
        case 440: return R.Tap(EKeys::Four);
        case 460: return R.Aim(R.Foe(2)) && R.Down(EKeys::LeftMouseButton);
        case 510: return R.Up(EKeys::LeftMouseButton);
        case 530: return R.Tap(EKeys::Five);
        case 545: return R.Place(R.Foe(3), FVector(200, 0, 0)) && R.Aim(R.Foe(3));
        case 550: return R.Tap(EKeys::RightMouseButton);
        case 570: return R.Down(EKeys::LeftShift) && R.Down(EKeys::W);
        case 595: return R.Tap(EKeys::SpaceBar);
        case 620: return R.Up(EKeys::LeftShift) && R.Up(EKeys::W);
        default: return true;
        }
    });
    const FString Hash = Run.Finish();
    Run.Expect(TEXT("the retainer and a carbine target fall and Nyaakoto stands"),
        bOk && Run.Mode()->Campaign()->Kills == 2 && Run.Hero()->IsAlive());
    // After the traced fight, the rest of the deck falls and the next beat begins.
    if (bOk && Log && !Run.ClearBeat(RetainerBeat))
        return FString();
    return bOk ? Hash : FString();
}

// The dojo's lesson duels (ch01.b02-b04): stance, guard, parry and recovery
// through real Block and Fire presses against one sparring pupil, then a
// scored bout with the bokken.
FString Dojo(FAutomationTestBase& Test, FEventLog* Log = nullptr)
{
    FRun Run(Test, TEXT("Dojo"), Log);
    if (!Run.Seed(0, 1) || !Run.Start() || !Run.Key(EKeys::Enter) || !Run.Key(EKeys::Enter))
        return FString();
    if (!Test.TestTrue(TEXT("Dojo scenario is in play"), Run.Mode()->IsPlaying()) || !Run.Place(Run.Foe(0), FVector(150, 0, 0)))
        return FString();
    const bool bOk = Run.Play(420, [](FRun& R, int32 F)
    {
        switch (F)
        {
        case 0: return R.Down(EKeys::LeftControl);
        case 120: return R.Up(EKeys::LeftControl);
        case 190: return R.Down(EKeys::LeftControl);
        case 205: return R.Up(EKeys::LeftControl);
        case 215: case 270: case 320: case 370: return R.Aim(R.Foe(0)) && R.Tap(EKeys::LeftMouseButton);
        default: return true;
        }
    });
    const FString Hash = Run.Finish();
    Run.Expect(TEXT("all four forms are learned and one pupil yields in the flanking duel"),
        bOk && Run.Mode()->Campaign()->DojoLessonStage() == 4 && Run.Mode()->Campaign()->ActiveBeat() == 3 &&
        Run.Mode()->Campaign()->Kills == 1);
    return bOk ? Hash : FString();
}

// The final chapter restored at its boss (ch08.b14): the collector's beam and
// cleave, carbine fire and its defeat; Enter skips the aftermath cinematic
// and the registry is carried to the last site. With a listener attached the
// chapter then plays out to liberation.
constexpr int32 CollectorChapter = 7, CollectorBeat = 13, BossSlot = 0;
FString Collector(FAutomationTestBase& Test, FEventLog* Log = nullptr)
{
    FRun Run(Test, TEXT("Collector"), Log);
    if (!Run.Seed(CollectorChapter, CollectorBeat) || !Run.Start() || !Run.Key(EKeys::Enter))
        return FString();
    if (!Test.TestTrue(TEXT("Collector scenario is in play"), Run.Mode()->IsPlaying()) ||
        !Test.TestNotNull(TEXT("The collector waits at its checkpoint"), Run.Mode()->Campaign()->CampaignBoss()) ||
        !Run.Place(Run.Foe(BossSlot), FVector(600, 0, 0)))
        return FString();
    const bool bOk = Run.Play(420, [](FRun& R, int32 F)
    {
        switch (F)
        {
        case 5: return R.Tap(EKeys::One);
        case 20: return R.Down(EKeys::D);
        case 60: return R.Up(EKeys::D);
        case 150: return R.Place(R.Foe(BossSlot), FVector(250, 0, 0)) && R.Aim(R.Foe(BossSlot));
        case 160: return R.Down(EKeys::LeftMouseButton);
        case 300: return R.Up(EKeys::LeftMouseButton);
        case 330:
        {
            FFoe* Boss = R.Foe(BossSlot);
            if (!Boss || !Boss->IsA<ASoraBoss>())
                return R.Fail(TEXT("The collector is gone before its defeat"));
            UGameplayStatics::ApplyDamage(Boss, Boss->Health, R.Controller(), R.Hero(), UDamageType::StaticClass());
            return true;
        }
        // Enter skips the aftermath cinematic; the registry box is carried from
        // the canal steps to the notice board at the last site.
        case 340: return R.Tap(EKeys::Enter);
        case 360: case 370:
        {
            FVector Point;
            if (!R.Mode()->Campaign()->ObjectiveAnchor(Point))
                return R.Fail(TEXT("The registry has no pickup or drop-off"));
            R.Hero()->SetActorLocation(FVector(Point.X, Point.Y, R.Hero()->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
            return R.Tap(EKeys::E);
        }
        default: return true;
        }
    });
    const FString Hash = Run.Finish();
    const USoraCampaignDirector* Campaign = Run.Mode()->Campaign();
    Run.Expect(TEXT("the collector falls and the registry restores the last site"),
        bOk && !Campaign->CampaignBoss() && Run.Mode()->Arena()->ActivatedMask() == 7 && Campaign->ActiveBeat() == 16);
    if (bOk && Log)
    {
        // The festival's closing lines play on, then Nyaakoto rehangs the plaque
        // and Enter skips the final cinematic into liberation.
        for (int32 Frame = 0; Frame < 400 && Campaign->ActiveBeat() == 16 && Campaign->LinesQueued() > 0; ++Frame)
            if (!Run.World->Tick(1, .5f))
                return FString();
        FVector Plaque;
        if (!Campaign->ObjectiveAnchor(Plaque))
        {
            Run.Fail(TEXT("The plaque has no anchor"));
            return FString();
        }
        Run.Hero()->SetActorLocation(FVector(Plaque.X, Plaque.Y, Run.Hero()->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
        if (!Run.World->Tick(2) || !Run.Key(EKeys::Enter))
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
    if (!Run.Start() || !Run.Key(EKeys::M) || !Run.Key(EKeys::F4) || !Run.Key(EKeys::Enter))
        return FString();
    if (!Test.TestTrue(TEXT("Training arena is in play"), Run.Mode()->IsPlaying() && !Run.Mode()->bCampaign))
        return FString();
    const bool bOk = Run.Play(440, [](FRun& R, int32 F)
    {
        switch (F)
        {
        case 0: return R.Place(R.Foe(1), FVector(700, 0, 0));
        case 5: return R.Aim(R.Foe(1)) && R.Tap(EKeys::LeftMouseButton);
        case 65: return R.Place(R.Foe(2), FVector(700, 250, 0));
        case 70: return R.Aim(R.Foe(2)) && R.Tap(EKeys::LeftMouseButton);
        case 140: return R.Tap(EKeys::R);
        case 290: return R.Tap(EKeys::Three) && R.Place(R.Foe(3), FVector(900, -250, 0));
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
    if (!Run.Start() || !Run.Key(EKeys::P) || !Run.Key(EKeys::Enter))
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
    TestFalse(TEXT("Dojo lessons and bouts complete"), Dojo(*this).IsEmpty());
    TestFalse(TEXT("Collector fight completes"), Collector(*this).IsEmpty());
    TestFalse(TEXT("Training arena fight completes"), Training(*this).IsEmpty());
    return true;
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
    FEventLog RetainerLog, DojoLog, CollectorLog, TrainingLog, KernelLog;
    TestEqual(TEXT("Retainer fight is unchanged by listeners"), Retainer(*this, &RetainerLog), Retainer(*this));
    TestEqual(TEXT("Dojo is unchanged by listeners"), Dojo(*this, &DojoLog), Dojo(*this));
    TestEqual(TEXT("Collector fight is unchanged by listeners"), Collector(*this, &CollectorLog), Collector(*this));
    TestEqual(TEXT("Training fight is unchanged by listeners"), Training(*this, &TrainingLog), Training(*this));

    const TCHAR* Scenario = TEXT("Flagship deck");
    TestEqual(TEXT("The chapter starts once, at its checkpoint"), RetainerLog.Count(TEXT("ChapterStarted ")), 1);
    Expect(*this, RetainerLog, Scenario, TEXT("ChapterStarted chapter=6 resumed=1 liberated=0"));
    Expect(*this, RetainerLog, Scenario, TEXT("BeatStarted chapter=6 beat=ch07.b08 resumed=1 phase=0"));
    Expect(*this, RetainerLog, Scenario, TEXT("Guarded defender=Hero attacker=Retainer0 dojo=0"));
    Expect(*this, RetainerLog, Scenario, TEXT("Parried defender=Hero attacker=Retainer0 dojo=0"));
    Expect(*this, RetainerLog, Scenario, TEXT("Committed attacker=Retainer0 weapon=0 windup=0.42"));
    Expect(*this, RetainerLog, Scenario, TEXT("Committed attacker=Hero weapon=0 windup=0.20"), 3);
    Expect(*this, RetainerLog, Scenario, TEXT("Committed attacker=Hero weapon=19 windup=0.29"));
    Expect(*this, RetainerLog, Scenario, TEXT("Resolved attacker=Hero target=Retainer0 weapon=0 hit=1"), 3);
    Expect(*this, RetainerLog, Scenario, TEXT("Resolved attacker=Retainer0 target=Hero weapon=0 hit=1"));
    Expect(*this, RetainerLog, Scenario, TEXT("Damaged victim=Retainer0 causer=Hero"), 3);
    Expect(*this, RetainerLog, Scenario, TEXT("Died victim=Retainer0 killer=Hero sparring=0"));
    Expect(*this, RetainerLog, Scenario, TEXT("Fired shooter=Hero weapon=1 kind=Hitscan"), 4);
    Expect(*this, RetainerLog, Scenario, TEXT("Died victim=Invader1 killer=Hero sparring=0"));
    Expect(*this, RetainerLog, Scenario, TEXT("Fired shooter=Hero weapon=18 kind=Arrow"));
    Expect(*this, RetainerLog, Scenario, TEXT("Fired shooter=Invader"));
    Expect(*this, RetainerLog, Scenario, TEXT("Damaged victim=Hero causer=Invader"));
    Expect(*this, RetainerLog, Scenario, TEXT("BeatCompleted chapter=6 beat=ch07.b08"));
    Expect(*this, RetainerLog, Scenario, TEXT("BeatStarted chapter=6 beat=ch07.b09 resumed=0 phase=0"));

    Scenario = TEXT("Dojo");
    Expect(*this, DojoLog, Scenario, TEXT("ChapterStarted chapter=0 resumed=1 liberated=0"));
    Expect(*this, DojoLog, Scenario, TEXT("BeatCompleted chapter=0 beat=ch01.b02"));
    Expect(*this, DojoLog, Scenario, TEXT("BeatCompleted chapter=0 beat=ch01.b03"));
    Expect(*this, DojoLog, Scenario, TEXT("SiteRestored chapter=0 site=1 campaign=1"));
    Expect(*this, DojoLog, Scenario, TEXT("Guarded defender=Hero attacker=Pupil0 dojo=1"), 2);
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
    Expect(*this, CollectorLog, Scenario, TEXT("Damaged victim=Boss causer=Hero"), 5);
    TestEqual(TEXT("The collector falls once"), CollectorLog.Count(TEXT("Boss phase=Defeated boss=Boss")), 1);
    Expect(*this, CollectorLog, Scenario, TEXT("Died victim=Boss killer=Hero sparring=0"));
    Expect(*this, CollectorLog, Scenario, TEXT("BeatCompleted chapter=7 beat=ch08.b14"));
    Expect(*this, CollectorLog, Scenario, TEXT("BeatCompleted chapter=7 beat=ch08.b15"));
    Expect(*this, CollectorLog, Scenario, TEXT("SiteRestored chapter=7 site=2 campaign=1"));
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
    Expect(*this, TrainingLog, Scenario, TEXT("Committed attacker=Hero weapon=6 windup=0.00"));
    Expect(*this, TrainingLog, Scenario, TEXT("Resolved attacker=Hero target=Retainer0 weapon=6 hit=1"));

    KernelEvents(*this, KernelLog);
    UE_LOG(LogTemp, Display, TEXT("SORA_SCRIPTED_FIGHT_EVENTS_OK: invasion=%d dojo=%d collector=%d training=%d kernel=%d"),
        RetainerLog.Lines.Num(), DojoLog.Lines.Num(), CollectorLog.Lines.Num(), TrainingLog.Lines.Num(), KernelLog.Lines.Num());
    return true;
}
#endif
