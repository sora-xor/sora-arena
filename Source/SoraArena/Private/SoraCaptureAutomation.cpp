#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "ArenaKernelSubsystem.h"
#include "Combat/SoraBossCatalog.h"
#include "SoraBoss.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraEnemyController.h"
#include "SoraFrontEnd.h"
#include "SoraHorse.h"
#include "SoraPlayerCharacter.h"
#include "SoraPracticeDirector.h"
#include "SoraPracticeLobby.h"
#include "SoraSaveGame.h"
#include "SoraHUD.h"
#include "HUD/SoraHUDPanels.h"
#include "SoraRegistryTesting.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "ContentStreaming.h"
#include "AssetCompilingManager.h"
#include "DynamicRHI.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Input/Events.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/App.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "ProfilingDebugging/CsvProfiler.h"
#include "RenderTimer.h"
#include "RHIGlobals.h"
#include "Tests/AutomationCommon.h"
#include "UnrealClient.h"

// Rendered baseline captures for visual review, and frame time in practice
// combat. They run only in a rendering game client, never in the NullRHI
// editor suite (ClientContext alone), and sit outside the SoraArena test tree
// so the packaged test's default filter does not spend ten minutes on them:
//   scripts/toolchain/capture-packaged-mac.sh ARCHIVE_DIRECTORY [output]
// launches the packaged game with -RenderOffscreen at 1920x1080 and runs
// "Automation RunTests SoraCapture". Like SoraArena.UIRendered, they drive
// the running game's own world through ASoraGameMode, so every frame is the
// game's: its world builder, directors, HUD, Lumen and post process under the
// platform's graphics preset.
//
// SoraCapture.Campaign.ChapterN continues from checkpoints seeded on a
// throwaway save slot (the player's campaign is never read or written) at
// two to four beats of the chapter, turns the hero toward what the beat is
// about (its opponent, a guard, the boss in a telegraph, the task, the horse,
// or the road from the saddle) from where he can see it, and saves the frame
// with its HUD. A cinematic is caught on its letterboxed card through its own
// camera, with a subtitle when one comes; a beat that keeps no checkpoint is
// reached by playing the dialogue beat before it from that beat's checkpoint.
// A shot that misses what it is for (a telegraph, an opponent, its beat) fails.
// SoraCapture.Practice.<Arena> plays zero-stake practice with the hero on the
// kernel's bot policy, measures frame time (capped as the preset ships, then
// uncapped) with the engine's stat-unit timers and a CSV profile, and saves the
// fight, the held scoreboard, stat unit and the results table.
//
// Frames go to Saved/Screenshots/SoraCapture/<width>x<height>/ with index.tsv
// (one row per frame: what it shows and what was seen) and one frame-time
// JSON per arena; CSV profiles to Saved/Profiling/CSV/.
namespace SoraCapture
{
enum class ESubject : uint8 { Cinematic, Opponent, Guard, Boss, Objective, Steed, Ride };

const TCHAR* SubjectName(ESubject Subject)
{
    switch (Subject)
    {
    case ESubject::Cinematic: return TEXT("cinematic");
    case ESubject::Opponent: return TEXT("opponent");
    case ESubject::Guard: return TEXT("guard");
    case ESubject::Boss: return TEXT("boss telegraph");
    case ESubject::Objective: return TEXT("task");
    case ESubject::Steed: return TEXT("horse");
    case ESubject::Ride: return TEXT("ride");
    }
    return TEXT("unknown");
}

struct FShot
{
    // Catalog chapter (0-7) and beat index, as SeedCheckpoint takes them.
    int32 Chapter;
    int32 Beat;
    ESubject Subject;
    const TCHAR* Name;
    // For a beat that keeps no checkpoint, the dialogue beat straight before
    // it, whose checkpoint the shot starts from; INDEX_NONE for the beat's own.
    int32 From = INDEX_NONE;
};

// Two to four beats a chapter: its places, the people in them, a fight, a
// stealth zone, a production task, a ride and every boss's telegraph.
const FShot Shots[] = {
    {0, 1, ESubject::Opponent, TEXT("C1_02_SeiganDuel")},
    {0, 5, ESubject::Steed, TEXT("C1_06_KurimaruTack")},
    {0, 8, ESubject::Objective, TEXT("C1_09_ArrowWork")},
    {0, 12, ESubject::Cinematic, TEXT("C1_13_SkySplits"), 11},
    {1, 1, ESubject::Opponent, TEXT("C2_02_NagayaGate")},
    {1, 7, ESubject::Ride, TEXT("C2_08_PackTrainRide")},
    {1, 14, ESubject::Boss, TEXT("C2_15_DunarkTelegraph")},
    {2, 1, ESubject::Guard, TEXT("C3_02_LandingStealth")},
    {2, 6, ESubject::Objective, TEXT("C3_07_CraftspeopleEscort")},
    {2, 16, ESubject::Boss, TEXT("C3_17_PenaltaTelegraph")},
    {3, 1, ESubject::Ride, TEXT("C4_02_BankRoadRide")},
    {3, 10, ESubject::Objective, TEXT("C4_11_Waterwheel")},
    {3, 15, ESubject::Boss, TEXT("C4_16_AssessorTelegraph")},
    {4, 0, ESubject::Cinematic, TEXT("C5_01_SilkFoundry")},
    {4, 4, ESubject::Opponent, TEXT("C5_05_LoomHall")},
    {4, 5, ESubject::Objective, TEXT("C5_06_Bellows")},
    {4, 15, ESubject::Boss, TEXT("C5_16_TarifaTelegraph")},
    {5, 5, ESubject::Guard, TEXT("C6_06_LedgerAisles")},
    {5, 8, ESubject::Opponent, TEXT("C6_09_ToranosukeDuel")},
    {5, 12, ESubject::Boss, TEXT("C6_13_EskroTelegraph")},
    {6, 3, ESubject::Guard, TEXT("C7_04_CargoHold")},
    {6, 9, ESubject::Opponent, TEXT("C7_10_HullRidge")},
    {6, 12, ESubject::Boss, TEXT("C7_13_CollateraTelegraph")},
    {7, 1, ESubject::Ride, TEXT("C8_02_CausewayRide")},
    {7, 3, ESubject::Objective, TEXT("C8_04_FieldForge")},
    {7, 13, ESubject::Boss, TEXT("C8_14_HighCollectorTelegraph")},
};

struct FArena
{
    int32 MapId;
    const TCHAR* Name;
    int32 Mode;
    int32 Players;
    int32 ClassId;
};

// Each arena in a different mode and class, full seats, Veteran bots.
const FArena Arenas[] = {
    {0, TEXT("NyaagyuEstate"), SoraPracticeLobby::FreeForAll, 8, 2},
    {1, TEXT("LanternWard"), SoraPracticeLobby::Control, 12, 1},
    {2, TEXT("SilkFoundry"), SoraPracticeLobby::Payload, 12, 3},
    {3, TEXT("DebtCitadel"), SoraPracticeLobby::Melee, 8, 0},
};
constexpr int32 ArenaCount = static_cast<int32>(UE_ARRAY_COUNT(Arenas));

// Calls Tick every frame with the seconds since it began until Tick returns
// true or Timeout passes; TimedOut then runs once.
class FUntil : public IAutomationLatentCommand
{
public:
    FUntil(double InTimeout, TFunction<bool(double)> InTick, TFunction<void()> InTimedOut = nullptr)
        : Timeout(InTimeout), Tick(MoveTemp(InTick)), TimedOut(MoveTemp(InTimedOut)) {}
    virtual bool Update() override
    {
        const double Elapsed = GetCurrentRunTime();
        if (Tick(Elapsed))
            return true;
        if (Elapsed < Timeout)
            return false;
        if (TimedOut)
            TimedOut();
        return true;
    }
private:
    double Timeout;
    TFunction<bool(double)> Tick;
    TFunction<void()> TimedOut;
};

// One frame of the engine's stat-unit timers, in milliseconds. Each is the
// last completed frame's, as stat unit draws it.
struct FSample
{
    float Frame = 0.f, Game = 0.f, Render = 0.f, RHI = 0.f, GPU = 0.f;
};

struct FTiming
{
    FString Label;
    TArray<FSample> Samples;
    double Seconds = 0.0;
};

struct FSession
{
    TWeakObjectPtr<ASoraGameMode> Mode;
    FString Folder;
    FString PlayerSlot;
    FString Slot;
    // The shot in progress: whether it began, what it is and what was seen.
    bool bShotLive = false;
    FString Note;
    // What the capture did to the beat beyond facing its subject.
    FString Step;
    // A boss shot: whether the hero stepped in, and the frames he walked for
    // a boss that hunts by ear to hear him.
    bool bSteppedIn = false;
    int32 WalkFrames = 0;
    FString File;
    FDateTime Previous;
    bool bFrameWritten = false;
    TArray<FTiming> Timings;
    ~FSession()
    {
        if (!Slot.IsEmpty() && UGameplayStatics::DoesSaveGameExist(Slot, 0))
            UGameplayStatics::DeleteGameInSlot(Slot, 0);
    }
    ASoraGameMode* M() const { return Mode.Get(); }
    ASoraPlayerCharacter* Hero() const { return M() ? M()->Hero() : nullptr; }
    USoraCampaignDirector* Campaign() const { return M() ? M()->Campaign() : nullptr; }
};
using FSessionRef = TSharedRef<FSession>;

void Queue(TFunction<void()> Action)
{
    ADD_LATENT_AUTOMATION_COMMAND(FFunctionLatentCommand([Action]() { Action(); return true; }));
}

void Wait(double Seconds, TFunction<void()> EachFrame = nullptr)
{
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(Seconds, [EachFrame](double) { if (EachFrame) EachFrame(); return false; }));
}

// The running game's world and mode, as a player's copy has them.
bool OpenSession(FAutomationTestBase& Test, FSession& Session, const TCHAR* Purpose)
{
    UWorld* World = nullptr;
    for (const FWorldContext& Context : GEngine->GetWorldContexts())
        if (Context.WorldType == EWorldType::Game && Context.World())
            World = Context.World();
    ASoraGameMode* Mode = World ? Cast<ASoraGameMode>(World->GetAuthGameMode()) : nullptr;
    UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr;
    if (!Test.TestNotNull(TEXT("A game world runs ASoraGameMode"), Mode) || !Test.TestNotNull(TEXT("The game has a viewport"), Viewport) ||
        !Test.TestTrue(TEXT("Slate is running"), FSlateApplication::IsInitialized()) ||
        !Test.TestTrue(TEXT("The catalog is loaded and the arena built"), FSoraCatalog::Get().IsReady() && Mode->Arena() != nullptr))
        return false;
    FVector2D Size;
    Viewport->GetViewportSize(Size);
    Session.Mode = Mode;
    Session.Folder = FPaths::ProjectSavedDir() / TEXT("Screenshots/SoraCapture") /
        FString::Printf(TEXT("%dx%d"), FMath::RoundToInt(Size.X), FMath::RoundToInt(Size.Y));
    Session.PlayerSlot = Mode->SaveSlotName;
    Session.Slot = FString::Printf(TEXT("SoraCapture_%s_%s"), Purpose, *FGuid::NewGuid().ToString(EGuidFormats::Digits));
    IFileManager::Get().MakeDirectory(*Session.Folder, true);
    return true;
}

// The player's slot again, read afresh, with the title in front of it.
void CloseSession(FSessionRef Session)
{
    Queue([Session]()
    {
        ASoraGameMode* M = Session->M();
        if (!M)
            return;
        if (UArenaKernelSubsystem* K = M->Kernel())
            K->bPracticeAutopilot = false;
        if (!M->bMenu)
            M->SetMenuOpen(true);
        M->SaveSlotName = Session->PlayerSlot;
        M->bDeterministicPractice = false;
        M->bCampaign = true;
        M->Campaign()->LoadSave();
        M->ResetRound();
        M->FrontEnd()->ShowTitle();
    });
}

FVector Center(const AActor& Actor)
{
    return Actor.GetComponentsBoundingBox(true).GetCenter();
}

// A character's face and shoulders, most of the way up its capsule, where a
// player looks at an opponent (the centre of its bounds is its belly).
FVector Upper(const ACharacter& Body)
{
    return Body.GetActorLocation() + FVector(0.f, 0.f, Body.GetCapsuleComponent()->GetScaledCapsuleHalfHeight() * .7f);
}

void Aim(ASoraPlayerCharacter& Hero, const FVector& Target)
{
    APlayerController* Controller = Cast<APlayerController>(Hero.GetController());
    if (!Controller)
        return;
    const FVector Eye = Hero.GetCamera() ? Hero.GetCamera()->GetComponentLocation() : Hero.GetPawnViewLocation();
    FRotator Look = (Target - Eye).Rotation();
    Look.Pitch = FMath::Clamp(Look.Pitch, -40.f, 30.f);
    Look.Roll = 0.f;
    Controller->SetControlRotation(Look);
}

// Stands the hero on the ground at a point, as a travel cut does.
void Place(ASoraPlayerCharacter& Hero, const FVector2D& At)
{
    const float Half = Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    FVector Spot(At.X, At.Y, Hero.GetActorLocation().Z);
    FHitResult Hit;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraCapturePlace), false, &Hero);
    const float Top = Hero.GetActorLocation().Z + 600.f;
    if (Hero.GetWorld()->LineTraceSingleByObjectType(Hit, FVector(At.X, At.Y, Top), FVector(At.X, At.Y, Top - 8000.f),
            FCollisionObjectQueryParams(ECC_WorldStatic), Query))
        Spot.Z = Hit.ImpactPoint.Z + Half + 2.f;
    Hero.GetCharacterMovement()->StopMovementImmediately();
    Hero.SetActorLocation(Spot, false, nullptr, ETeleportType::TeleportPhysics);
}

// What the shot looks at: the point, a second point low on it (a
// character's legs, which a table or a ledge can hide) and the floor under
// it, and the character there, if it is one.
struct FSight
{
    FVector Target = FVector::ZeroVector;
    FVector Low = FVector::ZeroVector;
    float FloorZ = 0.f;
    const AActor* Body = nullptr;
};

// Whether the hero's eye sees the sight, high and low: nothing blocks either
// line short of Slack before its end (an objective's kit stands at its
// anchor). The character looked at never blocks its own view, nor does the
// horse he rides (Ridden).
bool Sees(const ASoraPlayerCharacter& Hero, const FSight& Sight, float Slack, const AActor* Ridden)
{
    const FVector Eye = Hero.GetCamera() ? Hero.GetCamera()->GetComponentLocation() : Hero.GetPawnViewLocation();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraCaptureSees), false, &Hero);
    if (Sight.Body)
        Query.AddIgnoredActor(Sight.Body);
    if (Ridden)
        Query.AddIgnoredActor(Ridden);
    for (const FVector& Point : {Sight.Target, Sight.Low})
    {
        FHitResult Hit;
        if (Hero.GetWorld()->LineTraceSingleByChannel(Hit, Eye, Point, ECC_Visibility, Query) && FVector::Dist(Hit.ImpactPoint, Point) > Slack)
            return false;
    }
    return true;
}

// A working distance from the sight with a clear view of it: where the hero
// stands when he is between Near and Far from it and sees it; else Reach from
// it, on the floor it stands on (not on a table or a ledge beside it), on his
// side of it or the nearest turn round it (30 degrees at a time) from which
// he sees it. Says what it did; empty when he stayed.
FString Frame(ASoraPlayerCharacter& Hero, const FSight& Sight, float Near, float Far, float Reach, float Slack, const AActor* Ridden)
{
    const FVector Start = Hero.GetActorLocation();
    const FVector2D To(Sight.Target), From(Start);
    const float Distance = FVector2D::Distance(From, To);
    if (Distance >= Near && Distance <= Far && Sees(Hero, Sight, Slack, Ridden))
        return FString();
    const FVector2D Away = Distance > 1.f ? (From - To) / Distance : FVector2D(1.f, 0.f);
    const float Half = Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    for (int32 Turn = 0; Turn < 12; ++Turn)
    {
        const int32 Degrees = 30 * ((Turn + 1) / 2) * (Turn % 2 ? 1 : -1);
        Hero.SetActorLocation(Start, false, nullptr, ETeleportType::TeleportPhysics);
        Place(Hero, To + Away.GetRotated(static_cast<float>(Degrees)) * Reach);
        if (FMath::Abs(Hero.GetActorLocation().Z - Half - Sight.FloorZ) <= 60.f && Sees(Hero, Sight, Slack, Ridden))
            return FString::Printf(TEXT("the hero moved from %.0f m off to %.0f m, %d degrees round from his side, where he sees it"),
                Distance / 100.f, Reach / 100.f, Degrees);
    }
    Hero.SetActorLocation(Start, false, nullptr, ETeleportType::TeleportPhysics);
    if (Distance >= Near && Distance <= Far)
        return FString::Printf(TEXT("no clear view from %.0f m on any side; the hero stayed %.0f m off"), Reach / 100.f, Distance / 100.f);
    Place(Hero, To + Away * Reach);
    return FString::Printf(TEXT("no clear view from %.0f m on any side; the hero moved from %.0f m off to %.0f m on his side"),
        Reach / 100.f, Distance / 100.f, Reach / 100.f);
}

// Adds what the capture did to the beat.
void Did(FSession& Session, const FString& What)
{
    if (!What.IsEmpty())
        Session.Step += (Session.Step.IsEmpty() ? TEXT("") : TEXT("; ")) + What;
}

// The nearest living opponent (a duellist may be a boss), guards first when
// asked for one, and one on the ground before a drone overhead.
const ASoraEnemy* Nearest(const FSession& Session, bool bGuard)
{
    const ASoraPlayerCharacter* Hero = Session.Hero();
    if (!Hero)
        return nullptr;
    const ASoraEnemy* Best = nullptr;
    int32 BestRank = 0;
    float BestDistance = TNumericLimits<float>::Max();
    for (TActorIterator<ASoraEnemy> It(Hero->GetWorld()); It; ++It)
    {
        if (It->IsActorBeingDestroyed() || !It->IsAlive())
            continue;
        const ASoraEnemyController* Brain = Cast<ASoraEnemyController>(It->GetController());
        const int32 Rank = (bGuard && !(Brain && Brain->IsGuard()) ? 2 : 0) + (It->IsFlying() ? 1 : 0);
        const float Distance = FVector::Dist(It->GetActorLocation(), Hero->GetActorLocation());
        if (!Best || Rank < BestRank || (Rank == BestRank && Distance < BestDistance))
        {
            Best = *It;
            BestRank = Rank;
            BestDistance = Distance;
        }
    }
    return Best;
}

// Where the shot looks, if its subject is on the field now.
bool Subject(const FSession& Session, ESubject Kind, FSight& Sight)
{
    USoraCampaignDirector* Campaign = Session.Campaign();
    if (!Campaign)
        return false;
    const auto Character = [&Sight](const ACharacter& Body)
    {
        const float Half = Body.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        Sight.Target = Upper(Body);
        Sight.Low = Body.GetActorLocation() - FVector(0.f, 0.f, Half * .4f);
        Sight.FloorZ = Body.GetActorLocation().Z - Half;
        Sight.Body = &Body;
        return true;
    };
    // The objective's anchor is a point on the floor.
    const auto Anchor = [&Sight, Campaign](float Above)
    {
        if (!Campaign->ObjectiveAnchor(Sight.Target))
            return false;
        Sight.FloorZ = Sight.Target.Z;
        Sight.Target.Z += Above;
        Sight.Low = Sight.Target;
        Sight.Body = nullptr;
        return true;
    };
    switch (Kind)
    {
    case ESubject::Opponent:
    case ESubject::Guard:
        if (const ASoraEnemy* Enemy = Nearest(Session, Kind == ESubject::Guard))
            return Character(*Enemy);
        return Anchor(0.f);
    case ESubject::Boss:
        if (const ASoraBoss* Boss = Campaign->CampaignBoss())
            return Character(*Boss);
        return false;
    case ESubject::Objective:
        return Anchor(60.f);
    case ESubject::Steed:
        if (const ASoraHorse* Horse = Campaign->Steed())
        {
            Sight.Target = Center(*Horse);
            Sight.Low = Sight.Target;
            Sight.FloorZ = Horse->GetActorLocation().Z;
            Sight.Body = Horse;
            return true;
        }
        return false;
    default:
        return false;
    }
}

// Each frame the shot waits: the hero keeps facing its subject, or, in the
// saddle, down the road, and keeps his health.
void FaceSubject(const FSession& Session, ESubject Kind)
{
    ASoraPlayerCharacter* Hero = Session.Hero();
    USoraCampaignDirector* Campaign = Session.Campaign();
    if (!Session.bShotLive || !Hero || !Campaign)
        return;
    // The hero outlasts whatever the capture waits through; his health stays
    // full, so the HUD reads as at the beat's start.
    if (Hero->IsAlive())
        Hero->Health = Hero->MaxHealth;
    if (Kind == ESubject::Cinematic)
        return;
    if (Kind == ESubject::Ride)
    {
        const ASoraHorse* Horse = Campaign->Steed();
        APlayerController* Controller = Cast<APlayerController>(Hero->GetController());
        if (Horse && Controller && Campaign->IsMounted())
            Controller->SetControlRotation(FRotator(-6.f, Horse->GetActorRotation().Yaw, 0.f));
        return;
    }
    FSight Sight;
    if (Subject(Session, Kind, Sight))
        Aim(*Hero, Sight.Target);
}

// E at the horse's right side until her tack is on (the bit is refused until
// she has had her barley), one press a frame as a player's would be.
void TackUp(FSessionRef Session)
{
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(4.0, [Session](double)
    {
        USoraCampaignDirector* Campaign = Session->Campaign();
        ASoraPlayerCharacter* Hero = Session->Hero();
        ASoraHorse* Horse = Campaign ? Campaign->Steed() : nullptr;
        const FSoraBeat* Beat = Campaign ? Campaign->ActiveBeatData() : nullptr;
        if (!Session->bShotLive || !Hero || !Horse || !Beat || Campaign->IsMounted() || Campaign->TackDone() >= Beat->Space.Mount.Tack.Num())
            return true;
        Place(*Hero, FVector2D(Horse->GetActorLocation() + Horse->GetActorRightVector() * 120.f));
        Session->M()->Interact(Hero);
        return false;
    }));
}

void Mount(FSessionRef Session)
{
    Queue([Session]()
    {
        USoraCampaignDirector* Campaign = Session->Campaign();
        ASoraPlayerCharacter* Hero = Session->Hero();
        ASoraHorse* Horse = Campaign ? Campaign->Steed() : nullptr;
        if (!Session->bShotLive || !Hero || !Horse || Campaign->IsMounted())
            return;
        Place(*Hero, FVector2D(Horse->GetActorLocation() + Horse->GetActorRightVector() * 120.f));
        Session->M()->Interact(Hero);
    });
}

void AppendIndex(const FSession& Session, const FString& Row)
{
    const FString Index = Session.Folder / TEXT("index.tsv");
    if (!IFileManager::Get().FileExists(*Index))
        FFileHelper::SaveStringToFile(FString(TEXT("file\tchapter\tbeat\ttitle_ja\ttitle_en\tsubject\tseen\n")), *Index,
            FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    FFileHelper::SaveStringToFile(Row + TEXT("\n"), *Index, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,
        &IFileManager::Get(), FILEWRITE_Append);
}

// Streams every texture and mesh in, blocking up to a few seconds, so a frame
// never shows a mip still on its way.
void StreamIn()
{
    Queue([]() { IStreamingManager::Get().StreamAllResources(4.f); });
}

// Stops the world from the frame a shot has what it is for until its frame is
// written, so the telegraph or the fight the harness saw is the one drawn
// however long a frame takes; the HUD and the renderer go on.
void Freeze(FSessionRef Session, bool bFrozen)
{
    Queue([Session, bFrozen]()
    {
        if (ASoraGameMode* M = Session->M())
            UGameplayStatics::SetGamePaused(M, bFrozen);
    });
}

// Requests the viewport with its HUD and Slate, then waits for the file to
// be written (or rewritten, when an earlier run left one there).
void SaveFrame(FAutomationTestBase* Test, FSessionRef Session, const FString& Name, bool bRequireLive = false)
{
    Queue([Session, Name, bRequireLive]()
    {
        Session->bFrameWritten = false;
        if (bRequireLive && !Session->bShotLive) return;
        Session->File = Session->Folder / (Name + TEXT(".png"));
        Session->Previous = IFileManager::Get().GetTimeStamp(*Session->File);
        FScreenshotRequest::RequestScreenshot(Session->File, true, false);
    });
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(15.0, [Session, bRequireLive](double)
    {
        if (bRequireLive && !Session->bShotLive) return true;
        Session->bFrameWritten = IFileManager::Get().FileSize(*Session->File) > 0 &&
            IFileManager::Get().GetTimeStamp(*Session->File) != Session->Previous;
        return Session->bFrameWritten;
    }, [Test, Session]()
    {
        Test->AddError(FString::Printf(TEXT("No screenshot was written to %s"), *Session->File));
    }));
}

FString BossSeen(const ASoraBoss& Boss)
{
    const FSoraBossAttack* Attack = Boss.BossAttack();
    return FString::Printf(TEXT("%s telegraphs %s at %d%% of its warning; health %d permille, phase %d"), *Boss.GetName(),
        Attack ? *Attack->Id.ToString() : TEXT("nothing"), FMath::RoundToInt(Boss.BossWarningProgress() * 100.f),
        Boss.HealthPermille(), Boss.PhaseIndex() + 1);
}

// What a boss that has not attacked is doing, for the AI lane: where it
// stands against the hero and its phase's engage and near distances, whether
// it faces him, moves and ticks, who drives it, and its defensive states.
FString BossState(const FSession& Session, const ASoraBoss& Boss)
{
    const ASoraPlayerCharacter* Hero = Session.Hero();
    const FSoraBossPhase* Phase = Boss.CurrentPhase();
    const FVector Toward = Hero ? (Hero->GetActorLocation() - Boss.GetActorLocation()).GetSafeNormal2D() : FVector::ZeroVector;
    const AController* Brain = Boss.GetController();
    FString Reach;
    if (Phase)
        for (const int32 Index : Phase->Order)
            Reach += FString::Printf(TEXT("%s%d"), Reach.IsEmpty() ? TEXT("") : TEXT("/"), Boss.ReachFor(Index));
    return FString::Printf(TEXT("distance %.0f cm (engage %d, near %d, reach %s), facing %.2f, speed %.0f cm/s, tick %d, ")
        TEXT("controller %s, stunned %d, invulnerable %d, recovering %d, staggered %d, turn-locked %d, serial %d, playing %d"),
        Hero ? FVector::Dist2D(Hero->GetActorLocation(), Boss.GetActorLocation()) : -1.0, Phase ? Phase->EngageCm : -1,
        Phase ? Phase->NearCm : -1, *Reach, FVector::DotProduct(Boss.GetActorForwardVector().GetSafeNormal2D(), Toward),
        Boss.GetVelocity().Size2D(), Boss.IsActorTickEnabled() ? 1 : 0, Brain ? *Brain->GetClass()->GetName() : TEXT("none"),
        Boss.IsStunned() ? 1 : 0, Boss.IsInvulnerable() ? 1 : 0, Boss.IsRecovering() ? 1 : 0, Boss.IsStaggered() ? 1 : 0,
        Boss.IsTurnLocked() ? 1 : 0, Boss.AttackSerial(), Session.M() && Session.M()->IsPlaying() ? 1 : 0);
}

// A boss that has stopped out of reach of every attack its phase opens
// with, while the hero waits inside its engage distance, never strikes; a
// player would step in, and so does the hero, once, to just inside the
// shortest reach in front of it.
void StepIn(FSession& Session, const ASoraBoss& Boss)
{
    ASoraPlayerCharacter* Hero = Session.Hero();
    const FSoraBossPhase* Phase = Boss.CurrentPhase();
    if (!Hero || !Phase || Phase->Order.IsEmpty())
        return;
    int32 Reach = TNumericLimits<int32>::Max();
    for (const int32 Index : Phase->Order)
        Reach = FMath::Min(Reach, Boss.ReachFor(Index));
    const float Distance = FVector::Dist2D(Hero->GetActorLocation(), Boss.GetActorLocation());
    if (Distance <= Reach || Distance > Phase->EngageCm)
        return;
    const float Bodies = Boss.GetCapsuleComponent()->GetScaledCapsuleRadius() + Hero->GetCapsuleComponent()->GetScaledCapsuleRadius() + 15.f;
    const float Stand = FMath::Max(Bodies, Reach - 50.f);
    Place(*Hero, FVector2D(Boss.GetActorLocation() + Boss.GetActorForwardVector().GetSafeNormal2D() * Stand));
    const FString What = FString::Printf(TEXT("the boss stood %.0f cm off, outside its %d cm reach, and did not close; the hero stepped in to %.0f cm"),
        Distance, Reach, Stand);
    Did(Session, What);
    UE_LOG(LogTemp, Display, TEXT("SORA_CAPTURE_BOSS %s: %s"), *Boss.GetName(), *What);
}

// A boss that hunts by ear never finds a hero who stands still; a player
// would move, and so does the hero, sideways round it, while it has not
// heard him.
void Walk(FSession& Session, const ASoraBoss& Boss)
{
    ASoraPlayerCharacter* Hero = Session.Hero();
    const FSoraBossData* Data = Boss.Data();
    if (!Hero || !Data || !Data->bBlind || Boss.KnowsHero())
        return;
    Hero->AddMovementInput(Hero->GetActorRightVector(), 1.f);
    ++Session.WalkFrames;
}

// Whether the chapter's beat is in play as it should be, a cinematic on its
// letterboxed card and any other beat live; if not, the error says what is.
bool InBeat(FAutomationTestBase* Test, const FSession& Session, int32 Chapter, int32 Beat, const FString& Where)
{
    const ASoraGameMode* M = Session.M();
    const USoraCampaignDirector* Campaign = Session.Campaign();
    const bool bCinematic = FSoraCatalog::Get().Chapter(Chapter).Beats[Beat].Is(SoraBeatRules::EType::Cinematic);
    const SoraInput::EState Expected = bCinematic ? SoraInput::Card : SoraInput::Play;
    if (M && Campaign && Session.Hero() && Campaign->ChapterId == Chapter && Campaign->ActiveBeat() == Beat && M->InputState() == Expected)
        return true;
    Test->AddError(FString::Printf(TEXT("%s: beat %d is not in play %s (chapter %d, beat %d, input state %d, hero %s)"), *Where,
        Beat + 1, bCinematic ? TEXT("on its card") : TEXT("live"), Campaign ? Campaign->ChapterId + 1 : 0,
        Campaign ? Campaign->ActiveBeat() + 1 : 0, M ? static_cast<int32>(M->InputState()) : -1,
        Session.Hero() ? TEXT("present") : TEXT("missing")));
    return false;
}

// A beat that keeps no checkpoint is reached from the dialogue beat straight
// before it: the hero goes to its trigger and presses E, as a player does,
// and when its lines have run the shot's beat begins.
void LeadIn(FAutomationTestBase* Test, FSessionRef Session, const FShot& Shot, const FString& Where)
{
    Queue([Test, Session, Shot, Where]()
    {
        USoraCampaignDirector* Campaign = Session->Campaign();
        ASoraPlayerCharacter* Hero = Session->Hero();
        if (!Session->bShotLive || !Campaign || !Hero)
            return;
        if (Shot.From + 1 != Shot.Beat || Campaign->ActiveTask().Goal != SoraBeatRules::EGoal::Lines)
        {
            Test->AddError(Where + TEXT(": a shot starts only from the dialogue beat straight before it"));
            Session->bShotLive = false;
            return;
        }
        FVector Anchor;
        if (!Campaign->LinesStarted() && Campaign->ObjectiveAnchor(Anchor))
        {
            const FVector2D To(Anchor), From(Hero->GetActorLocation());
            Place(*Hero, To + (From - To).GetSafeNormal() * 150.f);
            Aim(*Hero, Anchor);
            Session->M()->Interact(Hero);
        }
        Session->bShotLive = Test->TestTrue(*(Where + TEXT(": the dialogue before the beat begins")), Campaign->LinesStarted());
    });
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(90.0, [Session, Shot](double)
    {
        const USoraCampaignDirector* Campaign = Session->Campaign();
        return !Session->bShotLive || !Campaign || Campaign->ActiveBeat() != Shot.From;
    }, [Test, Session, Where]()
    {
        Test->AddError(Where + TEXT(": the dialogue before the beat did not end within 90 s"));
        Session->bShotLive = false;
    }));
    Queue([Test, Session, Shot, Where]()
    {
        if (!Session->bShotLive)
            return;
        Session->bShotLive = InBeat(Test, *Session, Shot.Chapter, Shot.Beat, Where);
        if (Session->bShotLive)
            Did(*Session, FString::Printf(TEXT("played on from the checkpoint at beat %d through its dialogue"), Shot.From + 1));
    });
}

void QueueShot(FAutomationTestBase* Test, FSessionRef Session, const FShot& Shot)
{
    const FString Where = FString::Printf(TEXT("%s (chapter %d beat %d)"), Shot.Name, Shot.Chapter + 1, Shot.Beat + 1);
    const int32 Start = Shot.From == INDEX_NONE ? Shot.Beat : Shot.From;
    // The checkpoint on the throwaway slot, continued as Continue would: the
    // round rebuilt from the save, then play (a cinematic's on its card).
    Queue([Test, Session, Shot, Where, Start]()
    {
        Session->bShotLive = false;
        Session->Note.Reset();
        Session->Step.Reset();
        Session->bSteppedIn = false;
        Session->WalkFrames = 0;
        ASoraGameMode* M = Session->M();
        USaveGame* Created = UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass());
        USoraSaveGame* Save = Cast<USoraSaveGame>(Created);
        if (!M || !Save || !USoraCampaignDirector::SeedCheckpoint(*Save, Shot.Chapter, Start) ||
            !UGameplayStatics::SaveGameToSlot(Save, Session->Slot, 0))
        {
            Test->AddError(FString::Printf(TEXT("%s: the checkpoint at beat %d could not be seeded"), *Where, Start + 1));
            return;
        }
        if (!M->bMenu)
            M->SetMenuOpen(true);
        M->SaveSlotName = Session->Slot;
        M->bDeterministicPractice = false;
        M->bCampaign = true;
        if (!M->Campaign()->LoadSave())
        {
            Test->AddError(Where + TEXT(": the seeded save did not load"));
            return;
        }
        M->ResetRound();
        M->BeginRound();
        if (!InBeat(Test, *Session, Shot.Chapter, Start, Where))
            return;
        // The restore notice is the seeding's, not the beat's.
        M->Notice.Reset();
        M->NoticeEnglish.Reset();
        M->NoticeTime = 0.f;
        Session->bShotLive = true;
    });
    if (Shot.From != INDEX_NONE)
        LeadIn(Test, Session, Shot, Where);
    // Face the subject from a working distance where nothing blocks the view:
    // close enough to read, a stealth guard neither in the hero's face nor
    // lost in the distance, and crouched in a stealth zone, as a player
    // sneaks there.
    Queue([Session, Shot]()
    {
        ASoraPlayerCharacter* Hero = Session->Hero();
        USoraCampaignDirector* Campaign = Session->Campaign();
        if (!Session->bShotLive || !Hero || !Campaign)
            return;
        if (Hero->IsCrouched())
            Hero->UnCrouch();
        const AActor* Ridden = Campaign->IsMounted() ? Campaign->Steed() : nullptr;
        FSight Sight;
        if (Subject(*Session, Shot.Subject, Sight))
            switch (Shot.Subject)
            {
            case ESubject::Objective: Did(*Session, Frame(*Hero, Sight, 0.f, 700.f, 380.f, 150.f, Ridden)); break;
            case ESubject::Opponent: Did(*Session, Frame(*Hero, Sight, 0.f, 2500.f, 800.f, 50.f, Ridden)); break;
            case ESubject::Guard: Did(*Session, Frame(*Hero, Sight, 1000.f, 4500.f, 1500.f, 50.f, Ridden)); break;
            case ESubject::Boss: Did(*Session, Frame(*Hero, Sight, 0.f, 3000.f, 1200.f, 50.f, Ridden)); break;
            default: break;
            }
        if (Shot.Subject == ESubject::Guard)
            Hero->Crouch();
    });
    if (Shot.Subject == ESubject::Steed || Shot.Subject == ESubject::Ride)
        TackUp(Session);
    if (Shot.Subject == ESubject::Ride)
        Mount(Session);
    if (Shot.Subject == ESubject::Steed)
        Queue([Session]()
        {
            // Off her right shoulder, where the tack reads in profile.
            ASoraHorse* Horse = Session->Campaign() ? Session->Campaign()->Steed() : nullptr;
            if (Session->bShotLive && Horse && Session->Hero())
                Place(*Session->Hero(), FVector2D(Horse->GetActorLocation() + Horse->GetActorForwardVector() * 90.f +
                    Horse->GetActorRightVector() * 340.f));
        });
    const ESubject Kind = Shot.Subject;
    Wait(2.5, [Session, Kind]() { FaceSubject(*Session, Kind); });
    StreamIn();
    // Lumen and TSR settle after the stream-in hitch; a boss is caught in a
    // telegraph, a fight once an opponent stands, a cinematic with a line.
    const double Timeout = Kind == ESubject::Boss ? 40.0 : Kind == ESubject::Cinematic ? 45.0 : Kind == ESubject::Opponent ? 15.0 : 1.5;
    const TSharedRef<int32> Reported = MakeShared<int32>(0);
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(Timeout, [Session, Kind, Reported](double Elapsed)
    {
        FaceSubject(*Session, Kind);
        USoraCampaignDirector* Campaign = Session->Campaign();
        if (!Session->bShotLive || !Campaign)
            return true;
        if (Elapsed < 1.5)
            return false;
        switch (Kind)
        {
        case ESubject::Boss:
        {
            const ASoraBoss* Boss = Campaign->CampaignBoss();
            if (Boss && Elapsed >= 5.0 * (*Reported + 1))
            {
                ++*Reported;
                UE_LOG(LogTemp, Display, TEXT("SORA_CAPTURE_BOSS %.0f s: %s; %s"), Elapsed, *BossSeen(*Boss), *BossState(*Session, *Boss));
            }
            if (Boss && Elapsed >= 7.0 && !Boss->IsBossTelegraphing())
            {
                if (!Session->bSteppedIn)
                {
                    Session->bSteppedIn = true;
                    StepIn(*Session, *Boss);
                }
                Walk(*Session, *Boss);
            }
            if (!Boss || !Boss->IsBossTelegraphing() || Boss->BossWarningProgress() < .3f)
                return false;
            if (Session->WalkFrames > 0)
                Did(*Session, FString::Printf(TEXT("the boss hunts by ear and had not heard the hero standing still; he walked round it for %d frames until it did"),
                    Session->WalkFrames));
            Session->Note = BossSeen(*Boss);
            return true;
        }
        case ESubject::Opponent:
        {
            // Opponents walk up as the shot waits; it is taken once the
            // nearest stands in clear view, not behind a table or a ledge.
            FSight Sight;
            if (!Session->Hero() || !Subject(*Session, Kind, Sight) || !Sight.Body || !Sees(*Session->Hero(), Sight, 50.f, nullptr))
                return false;
            Session->Note = FString::Printf(TEXT("%s %.0f m away in clear view"), *Sight.Body->GetName(),
                FVector::Dist(Sight.Body->GetActorLocation(), Session->Hero()->GetActorLocation()) / 100.f);
            return true;
        }
        case ESubject::Cinematic:
        {
            const FSoraDialogueCue* Line = Campaign->CurrentDialogueCue();
            if (!Line)
                return false;
            Session->Note = FString::Printf(TEXT("%.0f s into the cinematic, with the line %s"), Campaign->CinematicElapsed(), *Line->Id);
            return true;
        }
        default:
            return true;
        }
    }, [Test, Session, Kind, Where]()
    {
        const USoraCampaignDirector* Campaign = Session->Campaign();
        const ASoraBoss* Boss = Campaign ? Campaign->CampaignBoss() : nullptr;
        switch (Kind)
        {
        case ESubject::Boss:
            Session->Note = Boss ? TEXT("no telegraph within 40 s; ") + BossSeen(*Boss) + TEXT("; ") + BossState(*Session, *Boss)
                                 : FString(TEXT("no boss on the field"));
            Test->AddError(Where + TEXT(": ") + Session->Note);
            break;
        case ESubject::Opponent:
            Session->Note = TEXT("no opponent in clear view within 15 s");
            Test->AddError(Where + TEXT(": ") + Session->Note);
            break;
        case ESubject::Cinematic:
            // Not every stretch of a cinematic carries a line; the frame is still its card.
            Session->Note = FString::Printf(TEXT("%.0f s into the cinematic, with no line on its card"), Campaign ? Campaign->CinematicElapsed() : 0.f);
            break;
        default:
            break;
        }
    }));
    if (Kind == ESubject::Cinematic)
        Queue([Test, Session, Where]()
        {
            const USoraCampaignDirector* Campaign = Session->Campaign();
            const ASoraPlayerCharacter* Hero = Session->Hero();
            const APlayerController* Controller = Hero ? Cast<APlayerController>(Hero->GetController()) : nullptr;
            if (Session->bShotLive)
                Test->TestTrue(*(Where + TEXT(": the cinematic plays through its camera")), Campaign && Controller &&
                    Campaign->CinematicCamera() && Controller->GetViewTarget() == Campaign->CinematicCamera());
        });
    Freeze(Session, true);
    SaveFrame(Test, Session, Shot.Name);
    Queue([Test, Session, Shot, Where]()
    {
        USoraCampaignDirector* Campaign = Session->Campaign();
        const FSoraChapter& Chapter = FSoraCatalog::Get().Chapter(Shot.Chapter);
        const FSoraBeat& Beat = Chapter.Beats[Shot.Beat];
        TArray<FString> Seen;
        if (!Session->Step.IsEmpty())
            Seen.Add(Session->Step);
        if (!Session->Note.IsEmpty())
            Seen.Add(Session->Note);
        if (Session->bShotLive && Campaign)
        {
            if (Session->Note.IsEmpty() && Shot.Subject == ESubject::Guard)
                if (const ASoraEnemy* Guard = Nearest(*Session, true))
                    Seen.Add(FString::Printf(TEXT("%s %.0f m away, the hero crouched"), *Guard->GetName(),
                        FVector::Dist(Guard->GetActorLocation(), Session->Hero()->GetActorLocation()) / 100.f));
            if (Shot.Subject == ESubject::Steed || Shot.Subject == ESubject::Ride)
                Seen.Add(FString::Printf(TEXT("tack %d, %s"), Campaign->TackDone(), Campaign->IsMounted() ? TEXT("mounted") : TEXT("on foot")));
            if (Campaign->ActiveBeat() != Shot.Beat)
            {
                const FString Moved = FString::Printf(TEXT("the frame shows beat %d, not %d"), Campaign->ActiveBeat() + 1, Shot.Beat + 1);
                Test->AddError(Where + TEXT(": ") + Moved);
                Seen.Insert(Moved, 0);
            }
        }
        if (Shot.Subject == ESubject::Ride)
            Test->TestTrue(*(Where + TEXT(": the hero rides")), Campaign && Campaign->IsMounted());
        const FString Line = FString::Join(Seen, TEXT("; "));
        UE_LOG(LogTemp, Display, TEXT("SORA_CAPTURE %s chapter %d %s (%s): %s"), Shot.Name, Shot.Chapter + 1, *Beat.Id,
            SubjectName(Shot.Subject), *Line);
        AppendIndex(*Session, FString::Printf(TEXT("%s.png\t%d\t%s\t%s\t%s\t%s\t%s"), Shot.Name, Shot.Chapter + 1, *Beat.Id,
            *Beat.Title, *Beat.TitleEnglish, SubjectName(Shot.Subject), *Line.Replace(TEXT("\t"), TEXT(" "))));
    });
    Freeze(Session, false);
}

// ---- Practice ----

// The hero plays by the kernel's bot policy; the camera follows its aim.
void FollowAutopilot(const FSession& Session)
{
    ASoraGameMode* M = Session.M();
    const UArenaKernelSubsystem* K = M ? M->Kernel() : nullptr;
    ASoraPlayerCharacter* Hero = M ? M->Hero() : nullptr;
    APlayerController* Controller = Hero ? Cast<APlayerController>(Hero->GetController()) : nullptr;
    if (K && Controller && K->PracticePlayers.IsValidIndex(0) && K->PracticePlayers[0].Alive)
        Controller->SetControlRotation(K->PracticePlayers[0].Aim);
}

// A living opponent the hero looks at, within 35 m and in clear sight of
// his eye; INDEX_NONE if none.
int32 InSights(const FSession& Session)
{
    ASoraGameMode* M = Session.M();
    const UArenaKernelSubsystem* K = M ? M->Kernel() : nullptr;
    const ASoraPlayerCharacter* Hero = M ? M->Hero() : nullptr;
    const APlayerController* Controller = Hero ? Cast<APlayerController>(Hero->GetController()) : nullptr;
    if (!K || !Controller || !Hero->GetCamera())
        return INDEX_NONE;
    const FVector Eye = Hero->GetCamera()->GetComponentLocation();
    const FVector Forward = Controller->GetControlRotation().Vector();
    for (int32 Slot = 1; Slot < K->PracticePlayers.Num(); ++Slot)
    {
        const FSoraPracticePlayer& Other = K->PracticePlayers[Slot];
        const ASoraCharacterBase* Body = M->Practice()->Participant(Slot);
        if (!Other.Alive || !Body || (SoraPractice::IsTeamMode(K->PracticeConfig.Mode) && Other.Team == K->PracticePlayers[0].Team))
            continue;
        const FVector Chest = Other.Feet + FVector(0.f, 0.f, 90.f);
        const FVector Toward = Chest - Eye;
        if (Toward.Size() > 3500.f || FVector::DotProduct(Toward.GetSafeNormal(), Forward) < .94f)
            continue;
        FHitResult Hit;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraCaptureSights), false, Hero);
        Query.AddIgnoredActor(Body);
        if (!Hero->GetWorld()->LineTraceSingleByChannel(Hit, Eye, Chest, ECC_Visibility, Query))
            return Slot;
    }
    return INDEX_NONE;
}

FSample Sample()
{
    FSample Out;
    Out.Frame = static_cast<float>(FApp::GetDeltaTime() * 1000.0);
    Out.Game = FPlatformTime::ToMilliseconds(GGameThreadTime);
    Out.Render = FPlatformTime::ToMilliseconds(GRenderThreadTime);
    Out.RHI = FPlatformTime::ToMilliseconds(GRHIThreadTime);
    Out.GPU = FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(0));
    return Out;
}

float Percentile(TArray<float> Values, float Fraction)
{
    if (Values.IsEmpty())
        return 0.f;
    Values.Sort();
    return Values[FMath::Clamp(FMath::CeilToInt(Fraction * Values.Num()) - 1, 0, Values.Num() - 1)];
}

float Mean(const TArray<float>& Values)
{
    double Sum = 0.0;
    for (const float Value : Values)
        Sum += Value;
    return Values.IsEmpty() ? 0.f : static_cast<float>(Sum / Values.Num());
}

FString Summary(const FTiming& Timing)
{
    TArray<float> Frame, Game, Render, RHI, GPU;
    int32 Over17 = 0, Over33 = 0;
    for (const FSample& S : Timing.Samples)
    {
        Frame.Add(S.Frame); Game.Add(S.Game); Render.Add(S.Render); RHI.Add(S.RHI); GPU.Add(S.GPU);
        Over17 += S.Frame > 1000.f / 60.f + .5f ? 1 : 0;
        Over33 += S.Frame > 1000.f / 30.f ? 1 : 0;
    }
    const float Average = Mean(Frame);
    return FString::Printf(TEXT("{\"window\":\"%s\",\"frames\":%d,\"seconds\":%.2f,\"fps\":%.1f,")
        TEXT("\"frame_ms\":{\"mean\":%.2f,\"p50\":%.2f,\"p95\":%.2f,\"p99\":%.2f,\"max\":%.2f},")
        TEXT("\"game_ms\":{\"mean\":%.2f,\"p95\":%.2f},\"render_ms\":{\"mean\":%.2f,\"p95\":%.2f},")
        TEXT("\"rhi_ms\":{\"mean\":%.2f,\"p95\":%.2f},\"gpu_ms\":{\"mean\":%.2f,\"p50\":%.2f,\"p95\":%.2f,\"max\":%.2f},")
        TEXT("\"frames_over_16_7ms\":%d,\"frames_over_33_3ms\":%d}"),
        *Timing.Label, Timing.Samples.Num(), Timing.Seconds, Timing.Seconds > 0.0 ? Timing.Samples.Num() / Timing.Seconds : 0.0,
        Average, Percentile(Frame, .5f), Percentile(Frame, .95f), Percentile(Frame, .99f), Percentile(Frame, 1.f),
        Mean(Game), Percentile(Game, .95f), Mean(Render), Percentile(Render, .95f), Mean(RHI), Percentile(RHI, .95f),
        Mean(GPU), Percentile(GPU, .5f), Percentile(GPU, .95f), Percentile(GPU, 1.f), Over17, Over33);
}

// How long a 5 ms sleep really takes in this process: the frame cap waits by
// sleeping, and macOS may coalesce the timers of an app with no visible window.
FString SleepProbe()
{
    TArray<float> Taken;
    for (int32 Try = 0; Try < 20; ++Try)
    {
        const double Before = FPlatformTime::Seconds();
        FPlatformProcess::SleepNoStats(.005f);
        Taken.Add(static_cast<float>((FPlatformTime::Seconds() - Before) * 1000.0));
    }
    return FString::Printf(TEXT("{\"requested_ms\":5,\"mean_ms\":%.2f,\"p50_ms\":%.2f,\"max_ms\":%.2f}"), Mean(Taken),
        Percentile(Taken, .5f), Percentile(Taken, 1.f));
}

FString ConsoleValue(const TCHAR* Name)
{
    const IConsoleVariable* Variable = IConsoleManager::Get().FindConsoleVariable(Name);
    return Variable ? Variable->GetString() : FString(TEXT("absent"));
}

// The renderer the frames were measured under: the preset's levels, the
// resolution scale and cap, and the GI, shadow and geometry paths.
FString RenderSettings()
{
    FString Out;
    for (const TCHAR* Name : {TEXT("r.ScreenPercentage"), TEXT("t.MaxFPS"), TEXT("r.VSync"), TEXT("r.AntiAliasingMethod"),
             TEXT("r.DynamicGlobalIlluminationMethod"), TEXT("r.ReflectionMethod"), TEXT("r.Lumen.HardwareRayTracing"),
             TEXT("r.Shadow.Virtual.Enable"), TEXT("r.Nanite"), TEXT("r.MegaLights.Enable"), TEXT("sg.ViewDistanceQuality"),
             TEXT("sg.AntiAliasingQuality"), TEXT("sg.ShadowQuality"), TEXT("sg.GlobalIlluminationQuality"),
             TEXT("sg.ReflectionQuality"), TEXT("sg.PostProcessQuality"), TEXT("sg.TextureQuality"), TEXT("sg.EffectsQuality"),
             TEXT("sg.FoliageQuality"), TEXT("sg.ShadingQuality"), TEXT("sg.LandscapeQuality")})
        Out += FString::Printf(TEXT("%s\"%s\":\"%s\""), Out.IsEmpty() ? TEXT("") : TEXT(","), Name,
            *ConsoleValue(Name).ReplaceCharWithEscapedChar());
    return TEXT("{") + Out + TEXT("}");
}

// Frame time over Seconds of live practice, with a CSV profile of the same window.
void Measure(FAutomationTestBase* Test, FSessionRef Session, const FString& Label, double Seconds, bool bUncapped)
{
    TSharedRef<float> Cap = MakeShared<float>(0.f);
    Queue([Session, Label, Cap, bUncapped]()
    {
        IConsoleVariable* MaxFps = IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS"));
        *Cap = MaxFps ? MaxFps->GetFloat() : 0.f;
        if (bUncapped && MaxFps)
            MaxFps->Set(0.f, ECVF_SetByConsole);
        FTiming& Timing = Session->Timings.AddDefaulted_GetRef();
        Timing.Label = Label;
        if (ASoraGameMode* M = Session->M())
            GEngine->Exec(M->GetWorld(), TEXT("csvprofile start"));
        CSV_METADATA(TEXT("SoraCaptureWindow"), *Label);
    });
    // The first frames after a change of cap are the old cap's.
    Wait(.5, [Session]() { FollowAutopilot(*Session); });
    const TSharedRef<double> Began = MakeShared<double>(0.0);
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(Seconds, [Session, Began](double)
    {
        FollowAutopilot(*Session);
        if (*Began == 0.0)
            *Began = FPlatformTime::Seconds();
        else
            Session->Timings.Last().Samples.Add(Sample());
        return false;
    }));
    Queue([Session, Began, Cap, bUncapped]()
    {
        Session->Timings.Last().Seconds = FPlatformTime::Seconds() - *Began;
        if (ASoraGameMode* M = Session->M())
            GEngine->Exec(M->GetWorld(), TEXT("csvprofile stop"));
        IConsoleVariable* MaxFps = IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS"));
        if (bUncapped && MaxFps)
            MaxFps->Set(*Cap, ECVF_SetByConsole);
    });
#if CSV_PROFILER
    // The profile stops at the next frame and is written after it; until
    // then the engine draws its frame counter over the view, and no frame is
    // saved or window begun.
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(30.0, [](double)
    {
        return !FCsvProfiler::Get()->IsCapturing() && !FCsvProfiler::Get()->IsWritingFile();
    }, [Test, Label]()
    {
        Test->AddError(FString::Printf(TEXT("The %s window's CSV profile was still being captured or written 30 s after it stopped"), *Label));
    }));
#endif
}

void HoldKey(const FKey& Key, bool bDown)
{
    const FKeyEvent Event(Key, FSlateApplication::Get().GetModifierKeys(), 0, false, 0, 0);
    if (bDown)
        FSlateApplication::Get().ProcessKeyDownEvent(Event);
    else
        FSlateApplication::Get().ProcessKeyUpEvent(Event);
}

void QueueArena(FAutomationTestBase* Test, FSessionRef Session, const FArena& Arena)
{
    const FString Prefix = FString::Printf(TEXT("A%d_%s"), Arena.MapId + 1, Arena.Name);
    Queue([Test, Session, Arena]()
    {
        ASoraGameMode* M = Session->M();
        if (!M)
            return;
        if (!M->bMenu)
            M->SetMenuOpen(true);
        // Starting practice saves the campaign beside it; that goes to the throwaway slot.
        M->SaveSlotName = Session->Slot;
        FSoraPracticeLobbySelection Selection;
        Selection.Mode = Arena.Mode;
        Selection.PlayerCount = Arena.Players;
        Selection.MapId = Arena.MapId;
        Selection.ClassId = Arena.ClassId;
        Selection.SpecialWeaponId = INDEX_NONE;
        Selection.Difficulty = SoraPracticeLobby::Veteran;
        const bool bStarted = M->StartPracticeFromLobby(Selection);
        UArenaKernelSubsystem* K = M->Kernel();
        Session->bShotLive = Test->TestTrue(*FString::Printf(TEXT("%s practice starts (%s / %s)"), Arena.Name, *M->Notice, *M->NoticeEnglish),
            bStarted && K && K->PracticeActive() && M->bDeterministicPractice && M->IsPlaying());
        if (K)
            K->bPracticeAutopilot = true;
    });
    // Warm-up: the arena streams in and the bots close.
    Wait(4.0, [Session]() { FollowAutopilot(*Session); });
    StreamIn();
    Wait(3.0, [Session]() { FollowAutopilot(*Session); });
    Measure(Test, Session, TEXT("capped"), 20.0, false);
    Measure(Test, Session, TEXT("uncapped"), 15.0, true);
    // A fight with a fresh line in the kill feed, seen by the living hero.
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(45.0, [Session](double)
    {
        FollowAutopilot(*Session);
        ASoraGameMode* M = Session->M();
        const UArenaKernelSubsystem* K = M ? M->Kernel() : nullptr;
        if (!Session->bShotLive || !K || K->PracticeTerminal)
            return true;
        if (!K->PracticePlayers.IsValidIndex(0) || !K->PracticePlayers[0].Alive)
            return false;
        int32 Age = INDEX_NONE;
        for (const FSoraPracticeFeedEntry& Entry : M->Practice()->Feed())
            if (Entry.Kind == FSoraPracticeFeedEntry::Kill && K->PracticeTick - Entry.Tick < 240)
                Age = static_cast<int32>(K->PracticeTick - Entry.Tick);
        const int32 Seen = InSights(*Session);
        if (Age == INDEX_NONE || Seen == INDEX_NONE)
            return false;
        Session->Note = FString::Printf(TEXT("tick %u; slot %d in the hero's sights %.0f m away; kill feed line %d ticks old"), K->PracticeTick,
            Seen, FVector::Dist(K->PracticePlayers[Seen].Feet, K->PracticePlayers[0].Feet) / 100.f, Age);
        return true;
    }, [Test, Session, Arena]()
    {
        Session->Note = TEXT("no opponent in the hero's sights with a fresh kill line within 45 s");
        Test->AddError(FString::Printf(TEXT("%s combat frame: %s"), Arena.Name, *Session->Note));
    }));
    Freeze(Session, true);
    SaveFrame(Test, Session, Prefix + TEXT("_Combat"));
    Freeze(Session, false);
    Queue([Session]() { UE_LOG(LogTemp, Display, TEXT("SORA_CAPTURE practice combat: %s"), *Session->Note); });
    Queue([]() { HoldKey(EKeys::Tab, true); });
    Wait(.6, [Session]() { FollowAutopilot(*Session); });
    Queue([Test, Session]()
    {
        const ASoraGameMode* M = Session->M();
        Test->TestTrue(TEXT("Tab held shows the scoreboard"), M && M->Practice()->ShowsScoreboard());
    });
    SaveFrame(Test, Session, Prefix + TEXT("_Scoreboard"));
    Queue([]() { HoldKey(EKeys::Tab, false); });
    Queue([Session]() { if (ASoraGameMode* M = Session->M()) GEngine->Exec(M->GetWorld(), TEXT("stat unit")); });
    Wait(1.5, [Session]() { FollowAutopilot(*Session); });
    SaveFrame(Test, Session, Prefix + TEXT("_StatUnit"));
    Queue([Session]() { if (ASoraGameMode* M = Session->M()) GEngine->Exec(M->GetWorld(), TEXT("stat unit")); });
    // The rest of the match at up to 320 kernel ticks a frame, through the
    // director's own step, until the kernel decides it.
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(180.0, [Session](double)
    {
        ASoraGameMode* M = Session->M();
        const UArenaKernelSubsystem* K = M ? M->Kernel() : nullptr;
        if (!Session->bShotLive || !K || !K->PracticeActive() || K->PracticeTerminal)
            return true;
        for (int32 Call = 0; Call < 40 && !K->PracticeTerminal && K->PracticeActive(); ++Call)
            M->Practice()->Step(8.f / 60.f);
        return K->PracticeTerminal;
    }, [Test]() { Test->AddError(TEXT("The practice match was not decided within 180 s of fast play")); }));
    Wait(3.0);
    Queue([Test, Session]()
    {
        const ASoraGameMode* M = Session->M();
        const UArenaKernelSubsystem* K = M ? M->Kernel() : nullptr;
        Test->TestTrue(TEXT("The match is decided and its results are drawn"), K && K->PracticeTerminal && M->Practice()->Results().bValid);
    });
    SaveFrame(Test, Session, Prefix + TEXT("_Results"));
    Queue([Test, Session, Arena, Prefix]()
    {
        const ASoraGameMode* M = Session->M();
        const UArenaKernelSubsystem* K = M ? M->Kernel() : nullptr;
        FString Windows;
        for (const FTiming& Timing : Session->Timings)
            Windows += (Windows.IsEmpty() ? TEXT("") : TEXT(",")) + Summary(Timing);
        FVector2D Size = FVector2D::ZeroVector;
        if (M && M->GetWorld()->GetGameViewport())
            M->GetWorld()->GetGameViewport()->GetViewportSize(Size);
        const FSoraPracticeResults* Results = M ? &M->Practice()->Results() : nullptr;
        const FString Json = FString::Printf(TEXT("{\"arena\":\"%s\",\"map_id\":%d,\"mode\":%d,\"players\":%d,\"class\":%d,")
            TEXT("\"bots\":\"veteran\",\"hero\":\"kernel bot policy\",\"viewport\":\"%dx%d\",\"rhi\":\"%s\",\"adapter\":\"%s\",")
            TEXT("\"build\":\"%s\",\"final_tick\":%u,\"winner_kind\":%d,\"windows\":[%s],\"sleep_probe\":%s,\"settings\":%s}"),
            Arena.Name, Arena.MapId, Arena.Mode, Arena.Players, Arena.ClassId, FMath::RoundToInt(Size.X), FMath::RoundToInt(Size.Y),
            GDynamicRHI ? GDynamicRHI->GetName() : TEXT("none"), *GRHIAdapterName.ReplaceCharWithEscapedChar(),
            LexToString(FApp::GetBuildConfiguration()), K ? K->PracticeTick : 0u, Results ? Results->WinnerKind : 0, *Windows,
            *SleepProbe(), *RenderSettings());
        UE_LOG(LogTemp, Display, TEXT("SORA_FRAMETIME %s"), *Json);
        FFileHelper::SaveStringToFile(Json + TEXT("\n"), *(Session->Folder / (Prefix + TEXT("_frametime.json"))),
            FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        for (const FTiming& Timing : Session->Timings)
            Test->TestTrue(*FString::Printf(TEXT("%s %s window sampled frames"), Arena.Name, *Timing.Label), Timing.Samples.Num() > 30);
        const FString Note = Session->Note;
        for (const TCHAR* Kind : {TEXT("Combat"), TEXT("Scoreboard"), TEXT("StatUnit"), TEXT("Results")})
            AppendIndex(*Session, FString::Printf(TEXT("%s_%s.png\tpractice\t%s\t\t\t%s\t%s"), *Prefix, Kind, Arena.Name, Kind,
                FCString::Strcmp(Kind, TEXT("Combat")) == 0 ? *Note : TEXT("")));
        if (UArenaKernelSubsystem* Kernel = M ? M->Kernel() : nullptr)
            Kernel->bPracticeAutopilot = false;
    });
}
// Let actual asynchronous asset work finish and its preparation messages
// disappear naturally. Keep editor diagnostics enabled and fail on a timeout.
void WaitForRegistryAssets(FAutomationTestBase* Test,FSessionRef Session)
{
    const TSharedRef<double> QuietSince=MakeShared<double>(-1.0);
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(120.0,[Test,Session,QuietSince](double Elapsed)
    {
        if(!Session->bShotLive) return true;
        FAssetCompilingManager& Assets=FAssetCompilingManager::Get();
        Assets.ProcessAsyncTasks(true);
        if(Assets.GetNumRemainingAssets()!=0)
        {
            *QuietSince=-1.0;
            return false;
        }
        if(*QuietSince<0.0) *QuietSince=Elapsed;
        if(Elapsed-*QuietSince<2.0) return false;
        Test->AddInfo(TEXT("Registry capture: asset compilation idle for two seconds; diagnostics remain enabled"));
        return true;
    },[Test,Session]()
    {
        Test->AddError(FString::Printf(TEXT("Registry capture asset compilation did not settle; %d assets remain"),
            FAssetCompilingManager::Get().GetNumRemainingAssets()));
        Session->bShotLive=false;
    }));
}
// Completed-save fixtures use the real catalog, progress validator, disk load,
// Continue action and HUD. They are UI evidence, never played-campaign proof.
void QueueRegistryFixture(FAutomationTestBase* Test,FSessionRef Session,int32 Chapter,bool English)
{
    const FString Name=FString::Printf(TEXT("RegistryFixture_Chapter%d_%s"),Chapter+1,English?TEXT("JA_EN"):TEXT("JA"));
    Queue([Test,Session,Chapter,English]()
    {
        Session->bShotLive=false;
        ASoraGameMode* M=Session->M();
        auto* Save=NewObject<USoraSaveGame>();
        if(!M||!SoraRegistryTesting::CompletedFixture(*Save,Chapter))
        {
            Test->AddError(TEXT("Registry fixture could not construct valid completed progress")); return;
        }
        Save->EnglishSubtitles=English;
        if(!UGameplayStatics::SaveGameToSlot(Save,Session->Slot,0))
        {
            Test->AddError(TEXT("Registry fixture could not save its throwaway checkpoint")); return;
        }
        if(!M->bMenu) M->SetMenuOpen(true);
        M->SaveSlotName=Session->Slot; M->bDeterministicPractice=false; M->bCampaign=true;
        if(!M->Campaign()->LoadSave()) { Test->AddError(TEXT("Registry fixture did not load")); return; }
        M->ResetRound();
        if(!Test->TestTrue(TEXT("Continue opens the completed registry"),M->ContinueCampaign()&&SoraHUDPanels::ShowsRegistry(*M))||
            !Test->TestEqual(TEXT("Continue preserves the fixture chapter"),M->Campaign()->ChapterId,Chapter)||
            !Test->TestEqual(TEXT("The fixture keeps its language choice"),M->bEnglishSubtitles,English)) return;
        const TArray<FSoraRegistryRow> Rows=M->Campaign()->RegistryRows();
        const TArray<int32> Counts=Chapter==3?TArray<int32>{12,1,30,120}:Chapter==4?TArray<int32>{24,3,1}:TArray<int32>{430};
        if(!Test->TestEqual(TEXT("All authored entries are present once"),Rows.Num(),Counts.Num())) return;
        const ESoraRegistryState State=Chapter==3?ESoraRegistryState::Recorded:Chapter==4?ESoraRegistryState::Inspected:ESoraRegistryState::Returned;
        for(int32 Index=0;Index<Rows.Num();++Index)
        {
            if(!Test->TestEqual(TEXT("The authored count is intact"),Rows[Index].Entry.Quantity,Counts[Index])||
                !Test->TestTrue(TEXT("The chapter has its correct inspection state"),Rows[Index].State==State)||
                !Test->TestEqual(TEXT("Only inspected goods have tally marks"),Rows[Index].HasSplitTally(),Chapter==4)) return;
        }
        if(Chapter==6)
        {
            const SoraText::FLine Note=SoraRegistry::Status(State);
            if(!Test->TestEqual(TEXT("The return note remains exact in Japanese"),Note.Japanese,FString(TEXT("返還のみ記帳・札は切らず")))||
                !Test->TestEqual(TEXT("The return note remains exact in English"),Note.English,FString(TEXT("Recorded as returned. No tally cut.")))) return;
        }
        M->Notice.Reset(); M->NoticeEnglish.Reset(); M->NoticeTime=0.f;
        Session->bShotLive=true;
    });
    StreamIn();
    WaitForRegistryAssets(Test,Session);
    Queue([Test,Session]()
    {
        if(!Session->bShotLive) return;
        ASoraGameMode* M=Session->M();
        APlayerController* PC=M?M->GetWorld()->GetFirstPlayerController():nullptr;
        ASoraHUD* HUD=PC?Cast<ASoraHUD>(PC->GetHUD()):nullptr;
        UGameViewportClient* Viewport=M?M->GetWorld()->GetGameViewport():nullptr;
        if(!Test->TestNotNull(TEXT("The fixture uses the actual game HUD"),HUD)||!Viewport)
        {
            Session->bShotLive=false; return;
        }
        FVector2D Size; Viewport->GetViewportSize(Size);
        FString Why;
        Session->bShotLive=Test->TestTrue(TEXT("All registry text fits without dropped counters or footer text"),
            SoraHUDPanels::RegistryLayoutFits(FSoraHUDFrame(*HUD,*M,Size.X,Size.Y),Why));
        if(!Why.IsEmpty()) Test->AddError(Why);
    });
    SaveFrame(Test,Session,Name,true);
    Queue([Session,Chapter,English,Name]()
    {
        if(!Session->bShotLive||!Session->bFrameWritten) return;
        const FSoraChapter& Data=FSoraCatalog::Get().Chapter(Chapter);
        const FString Note=FString::Printf(TEXT("validated completed-save UI fixture; not playthrough evidence; language=%s; rows=%d; measured text and role bounds passed; assets idle"),
            English?TEXT("JA+EN"):TEXT("JA"),Session->Campaign()->RegistryRows().Num());
        AppendIndex(*Session,FString::Printf(TEXT("%s.png\t%d\tcompleted-save-fixture\t%s\t%s\tregistry UI fixture\t%s"),
            *Name,Chapter+1,*Data.Title,*Data.TitleEnglish,*Note));
        UE_LOG(LogTemp,Display,TEXT("SORA_REGISTRY_FIXTURE %s"),*Note);
        UE_LOG(LogTemp,Display,TEXT("SORA_REGISTRY_FIXTURE_FRAME %s"),*FPaths::ConvertRelativePathToFull(Session->File));
    });
}

} // namespace SoraCapture

IMPLEMENT_COMPLEX_AUTOMATION_TEST(
    FSoraCaptureCampaignTest,
    "SoraCapture.Campaign",
    EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

void FSoraCaptureCampaignTest::GetTests(TArray<FString>& OutBeautifiedNames, TArray<FString>& OutTestCommands) const
{
    for (int32 Chapter = 0; Chapter < 8; ++Chapter)
    {
        OutBeautifiedNames.Add(FString::Printf(TEXT("Chapter%d"), Chapter + 1));
        OutTestCommands.Add(FString::FromInt(Chapter));
    }
}

bool FSoraCaptureCampaignTest::RunTest(const FString& Parameters)
{
    using namespace SoraCapture;
    const int32 Chapter = FCString::Atoi(*Parameters);
    const FSessionRef Session = MakeShared<FSession>();
    if (!OpenSession(*this, *Session, *FString::Printf(TEXT("Chapter%d"), Chapter + 1)))
        return false;
    int32 Queued = 0;
    for (const FShot& Shot : Shots)
        if (Shot.Chapter == Chapter)
        {
            QueueShot(this, Session, Shot);
            ++Queued;
        }
    CloseSession(Session);
    return TestTrue(TEXT("The chapter has shots"), Queued >= 2);
}

IMPLEMENT_COMPLEX_AUTOMATION_TEST(
    FSoraCapturePracticeTest,
    "SoraCapture.Practice",
    EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

void FSoraCapturePracticeTest::GetTests(TArray<FString>& OutBeautifiedNames, TArray<FString>& OutTestCommands) const
{
    for (int32 Index = 0; Index < SoraCapture::ArenaCount; ++Index)
    {
        OutBeautifiedNames.Add(SoraCapture::Arenas[Index].Name);
        OutTestCommands.Add(FString::FromInt(Index));
    }
}

bool FSoraCapturePracticeTest::RunTest(const FString& Parameters)
{
    using namespace SoraCapture;
    const int32 Index = FCString::Atoi(*Parameters);
    const FSessionRef Session = MakeShared<FSession>();
    if (!TestTrue(TEXT("A known arena"), Index >= 0 && Index < ArenaCount) ||
        !OpenSession(*this, *Session, Arenas[Index].Name))
        return false;
    QueueArena(this, Session, Arenas[Index]);
    CloseSession(Session);
    return true;
}
IMPLEMENT_COMPLEX_AUTOMATION_TEST(
    FSoraCaptureRegistryFixtureTest,
    "SoraCapture.RegistryFixture",
    EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

void FSoraCaptureRegistryFixtureTest::GetTests(TArray<FString>& OutBeautifiedNames,TArray<FString>& OutTestCommands) const
{
    for(const int32 Chapter:{3,4,6})
    {
        OutBeautifiedNames.Add(FString::Printf(TEXT("Chapter%d"),Chapter+1));
        OutTestCommands.Add(FString::FromInt(Chapter));
    }
}
bool FSoraCaptureRegistryFixtureTest::RunTest(const FString& Parameters)
{
    using namespace SoraCapture;
    const int32 Chapter=FCString::Atoi(*Parameters);
    const FSessionRef Session=MakeShared<FSession>();
    if(!TestTrue(TEXT("A supported registry fixture chapter"),Chapter==3||Chapter==4||Chapter==6)||
        !OpenSession(*this,*Session,TEXT("RegistryFixture"))) return false;
    APlayerController* PC=Session->M()->GetWorld()->GetFirstPlayerController();
    ASoraHUD* HUD=PC?Cast<ASoraHUD>(PC->GetHUD()):nullptr;
    if(!TestNotNull(TEXT("The fixture has the game HUD"),HUD)) return false;
    const TWeakObjectPtr<ASoraHUD> WeakHUD=HUD;
    const bool PreviousVisibility=HUD->bShowHUD;
    HUD->bShowHUD=true;
    QueueRegistryFixture(this,Session,Chapter,false);
    QueueRegistryFixture(this,Session,Chapter,true);
    Queue([WeakHUD,PreviousVisibility]() { if(ASoraHUD* Live=WeakHUD.Get()) Live->bShowHUD=PreviousVisibility; });
    CloseSession(Session);
    return true;
}

#endif
