#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/HUD.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"
#include "ContentStreaming.h"
#include "Engine/Texture2D.h"
#include "UObject/UObjectIterator.h"
#include "Tests/AutomationCommon.h"
#include "UnrealClient.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "ShaderCompiler.h"
#endif

// Fixed-camera art-review frames of authored scenes in the running game, HUD
// hidden, for matched before/after comparison of art changes. Like
// SoraCapture.Campaign (SoraCaptureAutomation.cpp) it continues from a
// checkpoint seeded on a throwaway save slot, so the player's campaign is
// never read or written, and every frame is the game's own world builder,
// Lumen and post process under the platform's graphics preset. The hero
// stands and looks from each review point; the world is paused while each
// frame settles (3 s) and is written, so the frames differ only by art.
//   scripts/toolchain/capture-editor-game.sh SoraCapture.ArtReview
// Frames: Saved/Screenshots/SoraArtReview/<width>x<height>/<Shot>.png.
namespace SoraArtReview
{
struct FShot
{
    const TCHAR* Name;
    FVector2D At;
    float Yaw;
    float Pitch;
};

// Chapter 1's Tsumagizaka dojo hall (x 8000-11600, y -1300-1300): the
// entrance view east to the kamiza, the kamiza and its maku, the south shoji
// and engawa, the coffered ceiling, the hall looking back west, and the
// floor under the east windows' light.
const FShot DojoShots[] = {
    {TEXT("Dojo_Entry_East"), FVector2D(8420.f, 0.f), 0.f, 4.f},
    {TEXT("Dojo_Kamiza"), FVector2D(10560.f, 0.f), 0.f, 9.f},
    {TEXT("Dojo_South_Shoji"), FVector2D(9780.f, 520.f), -90.f, 6.f},
    {TEXT("Dojo_Ceiling"), FVector2D(9500.f, -200.f), 20.f, 52.f},
    {TEXT("Dojo_West_Back"), FVector2D(11200.f, 380.f), 180.f, 3.f},
    {TEXT("Dojo_Floor_Light"), FVector2D(10900.f, -700.f), 200.f, -24.f},
};

class FUntil : public IAutomationLatentCommand
{
public:
    FUntil(double InTimeout, TFunction<bool(double)> InTick) : Timeout(InTimeout), Tick(MoveTemp(InTick)) {}
    virtual bool Update() override { const double T = GetCurrentRunTime(); return Tick(T) || T >= Timeout; }
private:
    double Timeout;
    TFunction<bool(double)> Tick;
};

struct FSession
{
    TWeakObjectPtr<ASoraGameMode> Mode;
    FString Folder, Slot, PlayerSlot, File;
    FDateTime Previous;
    bool bLive = false;
    ~FSession()
    {
        if (!Slot.IsEmpty() && UGameplayStatics::DoesSaveGameExist(Slot, 0))
            UGameplayStatics::DeleteGameInSlot(Slot, 0);
    }
    ASoraGameMode* M() const { return Mode.Get(); }
    ASoraPlayerCharacter* Hero() const { return M() ? M()->Hero() : nullptr; }
};
using FSessionRef = TSharedRef<FSession>;

void Queue(TFunction<void()> Action)
{
    ADD_LATENT_AUTOMATION_COMMAND(FFunctionLatentCommand([Action]() { Action(); return true; }));
}

void Wait(double Seconds)
{
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(Seconds, [](double) { return false; }));
}

bool Open(FAutomationTestBase& Test, FSession& Session)
{
    UWorld* World = nullptr;
    for (const FWorldContext& Context : GEngine->GetWorldContexts())
        if (Context.WorldType == EWorldType::Game && Context.World())
            World = Context.World();
    ASoraGameMode* Mode = World ? Cast<ASoraGameMode>(World->GetAuthGameMode()) : nullptr;
    UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr;
    if (!Test.TestNotNull(TEXT("A game world runs ASoraGameMode"), Mode) || !Test.TestNotNull(TEXT("The game has a viewport"), Viewport) ||
        !Test.TestTrue(TEXT("The catalog is loaded and the arena built"), FSoraCatalog::Get().IsReady() && Mode->Arena() != nullptr))
        return false;
    FVector2D Size;
    Viewport->GetViewportSize(Size);
    Session.Mode = Mode;
    Session.Folder = FPaths::ProjectSavedDir() / TEXT("Screenshots/SoraArtReview") /
        FString::Printf(TEXT("%dx%d"), FMath::RoundToInt(Size.X), FMath::RoundToInt(Size.Y));
    Session.PlayerSlot = Mode->SaveSlotName;
    Session.Slot = FString::Printf(TEXT("SoraArtReview_%s"), *FGuid::NewGuid().ToString(EGuidFormats::Digits));
    IFileManager::Get().MakeDirectory(*Session.Folder, true);
    return true;
}

void ShowHUD(ASoraGameMode& Mode, bool bShow)
{
    if (APlayerController* Controller = UGameplayStatics::GetPlayerController(&Mode, 0))
        if (AHUD* HUD = Controller->GetHUD())
            HUD->bShowHUD = bShow;
}

void Stand(ASoraPlayerCharacter& Hero, const FShot& Shot)
{
    const float Half = Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    FVector Spot(Shot.At.X, Shot.At.Y, Hero.GetActorLocation().Z);
    FHitResult Hit;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraArtReviewStand), false, &Hero);
    const float Top = Hero.GetActorLocation().Z + 600.f;
    if (Hero.GetWorld()->LineTraceSingleByObjectType(Hit, FVector(Shot.At.X, Shot.At.Y, Top), FVector(Shot.At.X, Shot.At.Y, Top - 8000.f),
            FCollisionObjectQueryParams(ECC_WorldStatic), Query))
        Spot.Z = Hit.ImpactPoint.Z + Half + 2.f;
    Hero.GetCharacterMovement()->StopMovementImmediately();
    Hero.SetActorLocation(Spot, false, nullptr, ETeleportType::TeleportPhysics);
    if (APlayerController* Controller = Cast<APlayerController>(Hero.GetController()))
        Controller->SetControlRotation(FRotator(Shot.Pitch, Shot.Yaw, 0.f));
}

void Frame(FAutomationTestBase* Test, FSessionRef Session, const FShot& Shot)
{
    Queue([Session, Shot]()
    {
        ASoraGameMode* M = Session->M();
        ASoraPlayerCharacter* Hero = Session->Hero();
        if (!Session->bLive || !M || !Hero)
            return;
        UGameplayStatics::SetGamePaused(M, false);
        Stand(*Hero, Shot);
    });
    Wait(0.4);
    Queue([Session]()
    {
        if (ASoraGameMode* M = Session->M()) UGameplayStatics::SetGamePaused(M, true);
        IStreamingManager::Get().StreamAllResources(4.f);
    });
    // Lumen's surface cache, screen probes and TSR converge on the still view.
    Wait(3.0);
    const FString Name = Shot.Name;
    Queue([Session, Name]()
    {
        Session->File = Session->Folder / (Name + TEXT(".png"));
        Session->Previous = IFileManager::Get().GetTimeStamp(*Session->File);
        FScreenshotRequest::RequestScreenshot(Session->File, false, false);
    });
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(15.0, [Session](double)
    {
        return IFileManager::Get().FileSize(*Session->File) > 0 && IFileManager::Get().GetTimeStamp(*Session->File) != Session->Previous;
    }));
    Queue([Test, Session, Name]()
    {
        if (IFileManager::Get().FileSize(*Session->File) <= 0 || IFileManager::Get().GetTimeStamp(*Session->File) == Session->Previous)
            Test->AddError(FString::Printf(TEXT("No art-review frame was written for %s"), *Name));
        else
            UE_LOG(LogTemp, Display, TEXT("SORA_ART_REVIEW_FRAME %s"), *Session->File);
    });
}

void Run(FAutomationTestBase* Test, int32 Chapter, int32 Beat, const TArray<FShot>& Shots)
{
    const FSessionRef Session = MakeShared<FSession>();
    if (!Open(*Test, *Session))
        return;
    Queue([Test, Session, Chapter, Beat]()
    {
        ASoraGameMode* M = Session->M();
        USoraSaveGame* Save = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!M || !Save || !USoraCampaignDirector::SeedCheckpoint(*Save, Chapter, Beat) ||
            !UGameplayStatics::SaveGameToSlot(Save, Session->Slot, 0))
        {
            Test->AddError(TEXT("The art-review checkpoint could not be seeded"));
            return;
        }
        if (!M->bMenu)
            M->SetMenuOpen(true);
        M->SaveSlotName = Session->Slot;
        M->bDeterministicPractice = false;
        M->bCampaign = true;
        if (!M->Campaign()->LoadSave())
        {
            Test->AddError(TEXT("The seeded art-review save did not load"));
            return;
        }
        M->ResetRound();
        M->BeginRound();
        M->Notice.Reset();
        M->NoticeEnglish.Reset();
        M->NoticeTime = 0.f;
        ShowHUD(*M, false);
        Session->bLive = true;
    });
    // The editor binary compiles textures, meshes and shaders on demand: finish
    // them all (a packaged game has them cooked), then stream every mip.
    Queue([]()
    {
#if WITH_EDITOR
        FAssetCompilingManager::Get().FinishAllCompilation();
        if (GShaderCompilingManager)
            GShaderCompilingManager->FinishAllCompilation();
#endif
        // Every loaded texture fully resident, as a still review frame needs.
        for (TObjectIterator<UTexture2D> It; It; ++It)
            It->SetForceMipLevelsToBeResident(600.f);
        IStreamingManager::Get().StreamAllResources(8.f);
    });
    Wait(6.0);
    for (const FShot& Shot : Shots)
        Frame(Test, Session, Shot);
    Queue([Session]()
    {
        ASoraGameMode* M = Session->M();
        if (!M)
            return;
        UGameplayStatics::SetGamePaused(M, false);
        ShowHUD(*M, true);
        if (!M->bMenu)
            M->SetMenuOpen(true);
        M->SaveSlotName = Session->PlayerSlot;
        M->bCampaign = true;
        M->Campaign()->LoadSave();
        M->ResetRound();
    });
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraArtReviewDojoTest, "SoraCapture.ArtReview.Dojo",
    EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter)
bool FSoraArtReviewDojoTest::RunTest(const FString& Parameters)
{
    // Chapter 1, beat 2 (the first lesson in the hall), from its checkpoint.
    SoraArtReview::Run(this, 0, 1, TArray<SoraArtReview::FShot>(SoraArtReview::DojoShots, UE_ARRAY_COUNT(SoraArtReview::DojoShots)));
    return true;
}
#endif
