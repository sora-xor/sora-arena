#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraCampaignDirector.h"
#include "SoraBoss.h"
#include "SoraCatalog.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "Camera/CameraComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/DamageType.h"
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
#include "SceneViewExtension.h"
#include "SceneView.h"
#include "SceneManagement.h"
#include "RenderGraphBuilder.h"
#include "RenderGraphUtils.h"
#include "RHIGPUReadback.h"
#include "HAL/IConsoleManager.h"
#include "Misc/ScopeLock.h"
#include "Misc/FileHelper.h"
#include "Misc/EngineVersion.h"
#include "Dom/JsonObject.h"
#include "RenderingThread.h"
#include "Tasks/Task.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include <atomic>
#include <limits>
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
// Opt-in through SORA_EXEC_PREFIX='sora.ArtExposureDiagnostic 1,'. This never
// changes exposure, show flags, camera cuts or the ordinary capture schedule.
static TAutoConsoleVariable<int32> CVarArtExposureDiagnostic(TEXT("sora.ArtExposureDiagnostic"), 0,
    TEXT("Record ArtReview exposure GPU observations (0 off, 1 on; automation only)."), ECVF_Default);

class FExposureDiagnostic final : public FSceneViewExtensionBase
{
    struct FFrame
    {
        uint64 Counter = 0;
        uint32 Number = 0, ViewKey = 0, Shot = 0;
        FString Name, File, Error;
        bool bScreenshot = false, bPaused = false;
        TMap<FString, double> Values;
        TMap<FString, bool> Flags;
    };
    struct FSlot
    {
        TUniquePtr<FRHIGPUBufferReadback> Buffer;
        TOptional<FFrame> Frame;
    };
    struct FShotResult
    {
        FString Name, File;
        int32 Observations = 0, Requests = 0, Pairs = 0, Failures = 0;
    };
    static constexpr int32 MaxObservations = 2048;
    FViewport* const Viewport;
    FSceneInterface* const Scene;
    FAutomationTestBase* const Test; // Only used on the game thread.
    FString Folder;
    const FString Session;
    const int32 EnabledValue;
    std::atomic<bool> bActive{true}, bRetiring{false}, bRetired{false};
    uint32 ActiveShot = 0, NextShot = 0;
    bool bAborted = false;
    TMap<uint32, FShotResult> Shots; // Game thread only.
    TSet<FString> ReportedErrors;
    FCriticalSection Mutex;
    TMap<uint64, FFrame> TaggedFrames;
    TMap<uint32, int32> Outstanding;
    TArray<FFrame> Completed;
    FSlot Slots[4]; // Render thread only; slot 3 is reserved for the screenshot.

    void Error(const FString& Message)
    {
        if (!ReportedErrors.Contains(Message))
        {
            ReportedErrors.Add(Message);
            Test->AddError(TEXT("Art exposure diagnostic: ") + Message);
        }
    }
    void Publish(FFrame&& Frame)
    {
        FScopeLock Lock(&Mutex);
        --Outstanding.FindChecked(Frame.Shot);
        Completed.Add(MoveTemp(Frame));
    }
    static double CVar(const TCHAR* Name)
    {
        const IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(Name);
        return V ? V->GetFloat() : std::numeric_limits<double>::quiet_NaN();
    }
    void Poll_RenderThread(uint64 CompletedAt)
    {
        for (FSlot& Slot : Slots)
        {
            if (!Slot.Frame.IsSet() || Slot.Frame->Counter >= CompletedAt || !Slot.Buffer->IsReady()) continue;
            FFrame Frame = MoveTemp(Slot.Frame.GetValue());
            Slot.Frame.Reset();
            const void* Data = Slot.Buffer->Lock(sizeof(FVector4f));
            if (Data)
            {
                const FVector4f Value = *static_cast<const FVector4f*>(Data);
                Slot.Buffer->Unlock();
                // Audited UE5.8.3 CL58210709 PostProcessEyeAdaptation.usf,
                // EyeAdaptationCommon: current, target, metered luminance, compensation.
                Frame.Values.Add(TEXT("current_exposure_scale"), Value.X);
                Frame.Values.Add(TEXT("target_exposure_scale"), Value.Y);
                Frame.Values.Add(TEXT("metered_average_scene_luminance"), Value.Z);
                Frame.Values.Add(TEXT("exposure_compensation_multiplier"), Value.W);
                if (!FMath::IsFinite(Value.X) || !FMath::IsFinite(Value.Y) ||
                    !FMath::IsFinite(Value.Z) || !FMath::IsFinite(Value.W) ||
                    Value.X <= 0 || Value.Y <= 0 || Value.Z < 0 || Value.W <= 0)
                    Frame.Error = TEXT("Invalid eye-adaptation GPU payload");
            }
            else Frame.Error = TEXT("Eye-adaptation GPU readback lock failed");
            Frame.Values.Add(TEXT("readback_completed_frame_counter"), static_cast<double>(CompletedAt));
            Publish(MoveTemp(Frame));
        }
    }
    void Retire_RenderThread()
    {
        // Retire() chains this command after RDG's async execution task, so no
        // queued graph pass still owns a raw readback pointer here.
        for (FSlot& Slot : Slots)
        {
            if (Slot.Frame.IsSet())
            {
                FFrame Frame = MoveTemp(Slot.Frame.GetValue());
                Slot.Frame.Reset();
                Frame.Error = TEXT("Readback remained pending at bounded teardown");
                Publish(MoveTemp(Frame));
            }
            Slot.Buffer.Reset(); // RHI references use normal deferred resource release.
        }
        TMap<uint64, FFrame> Missing;
        {
            FScopeLock Lock(&Mutex);
            Missing = MoveTemp(TaggedFrames);
        }
        for (auto& Entry : Missing)
        {
            Entry.Value.Error = TEXT("Tagged view never reached the render callback");
            Publish(MoveTemp(Entry.Value));
        }
        bRetired = true;
    }
protected:
    virtual bool IsActiveThisFrame_Internal(const FSceneViewExtensionContext& Context) const override
    {
        return bActive && Context.Viewport == Viewport;
    }
public:
    FExposureDiagnostic(const FAutoRegister& AutoRegister, FViewport* InViewport, FSceneInterface* InScene,
        FAutomationTestBase* InTest, FString InFolder, int32 InValue)
        : FSceneViewExtensionBase(AutoRegister), Viewport(InViewport), Scene(InScene), Test(InTest),
          Folder(MoveTemp(InFolder)), Session(FGuid::NewGuid().ToString(EGuidFormats::Digits)), EnabledValue(InValue)
    {
        // The runner does not yet archive these sidecars. Keep each diagnostic
        // session distinct so another capture cannot overwrite its evidence.
        Folder = Folder / TEXT("Exposure") / Session;
        if (!IFileManager::Get().MakeDirectory(*Folder, true)) Error(TEXT("Cannot create exposure evidence directory"));
    }

    void BeginShot(const FString& Name)
    {
        if (bAborted) return;
        Pump();
        ActiveShot = ++NextShot;
        FShotResult& Shot = Shots.Add(ActiveShot);
        Shot.Name = Name;
        const FString Sidecar = Folder / (Name + TEXT(".exposure.jsonl"));
        const FString Header = FString::Printf(TEXT("{\"type\":\"session\",\"session\":\"%s\",\"diagnostic_cvar\":%d,\"engine\":\"5.8.3-58210709\",\"layout\":\"EyeAdaptationCommon.float4.v1\",\"cached_values\":\"asynchronous; source GPU frame unavailable\"}\n"), *Session, EnabledValue);
        if (!FFileHelper::SaveStringToFile(Header, *Sidecar, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
            Error(TEXT("Cannot initialize exposure sidecar ") + Sidecar);
        else UE_LOG(LogTemp, Display, TEXT("SORA_ART_EXPOSURE_SIDECAR %s"), *Sidecar);
    }
    void StopShot() { ActiveShot = 0; }
    void ArmScreenshot(const FString& File)
    {
        if (ActiveShot) Shots.FindChecked(ActiveShot).File = FPaths::ConvertRelativePathToFull(File);
    }
    void Pump()
    {
        TArray<FFrame> Ready;
        {
            FScopeLock Lock(&Mutex);
            Ready = MoveTemp(Completed);
        }
        for (FFrame& Frame : Ready)
        {
            FShotResult& Shot = Shots.FindChecked(Frame.Shot);
            if (!Frame.Error.IsEmpty()) { ++Shot.Failures; Error(Frame.Name + TEXT(": ") + Frame.Error); }
            else if (Frame.bScreenshot) ++Shot.Pairs;
            auto Json = MakeShared<FJsonObject>();
            Json->SetStringField(TEXT("type"), TEXT("frame"));
            Json->SetStringField(TEXT("session"), Session);
            Json->SetStringField(TEXT("shot"), Frame.Name);
            Json->SetStringField(TEXT("screenshot_file"), Frame.File);
            Json->SetNumberField(TEXT("shot_id"), Frame.Shot);
            Json->SetNumberField(TEXT("family_frame_counter"), static_cast<double>(Frame.Counter));
            Json->SetNumberField(TEXT("family_frame_number"), Frame.Number);
            Json->SetNumberField(TEXT("view_key"), Frame.ViewKey);
            Json->SetBoolField(TEXT("screenshot_frame"), Frame.bScreenshot);
            Json->SetBoolField(TEXT("world_paused_game_thread"), Frame.bPaused);
            Json->SetStringField(TEXT("error"), Frame.Error);
            for (const auto& Value : Frame.Values)
                if (FMath::IsFinite(Value.Value)) Json->SetNumberField(Value.Key, Value.Value);
                else Json->SetField(Value.Key, MakeShared<FJsonValueNull>());
            for (const auto& Flag : Frame.Flags) Json->SetBoolField(Flag.Key, Flag.Value);
            // FViewInfo::bPrevTransformsReset is private. Absence of a public
            // forcing condition does not establish ForceTarget=false.
            if (Frame.Flags.FindRef(TEXT("force_target_proven_true"))) Json->SetBoolField(TEXT("force_target"), true);
            else Json->SetField(TEXT("force_target"), MakeShared<FJsonValueNull>());
            Json->SetStringField(TEXT("previous_transforms_reset"), TEXT("unavailable_public_api"));
            FString Text;
            if (!FJsonSerializer::Serialize(Json, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text)))
            { ++Shot.Failures; Error(TEXT("Cannot serialize exposure observation")); continue; }
            if (!FFileHelper::SaveStringToFile(Text + TEXT("\n"), *(Folder / (Frame.Name + TEXT(".exposure.jsonl"))),
                FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append))
                Error(TEXT("Cannot append exposure sidecar for ") + Frame.Name);
        }
    }
    bool Drained()
    {
        Pump();
        FScopeLock Lock(&Mutex);
        for (const auto& Entry : Outstanding) if (Entry.Value != 0) return false;
        return true;
    }
    void ValidateShot(const FString& Name)
    {
        if (bAborted) return;
        if (!Shots.Contains(NextShot) || Shots.FindChecked(NextShot).Name != Name)
        { Error(Name + TEXT(": no diagnostic shot was armed")); return; }
        if (!Drained())
        {
            Error(TEXT("Five-second GPU observation drain timed out"));
            bAborted = true;
            Retire();
        }
        const FShotResult& Shot = Shots.FindChecked(NextShot);
        if (Shot.Requests != 1 || Shot.Pairs != 1 || Shot.Failures != 0 || Shot.Observations == 0)
            Error(FString::Printf(TEXT("%s: expected one valid screenshot pair; requests=%d pairs=%d failed_frames=%d observations=%d"),
                *Shot.Name, Shot.Requests, Shot.Pairs, Shot.Failures, Shot.Observations));
        const FString Summary = FString::Printf(TEXT("{\"type\":\"summary\",\"requests\":%d,\"valid_screenshot_pairs\":%d,\"failed_frames\":%d,\"observations\":%d,\"drained\":%s}\n"),
            Shot.Requests, Shot.Pairs, Shot.Failures, Shot.Observations, Drained() ? TEXT("true") : TEXT("false"));
        if (!FFileHelper::SaveStringToFile(Summary, *(Folder / (Shot.Name + TEXT(".exposure.jsonl"))),
            FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append))
            Error(TEXT("Cannot write exposure summary for ") + Shot.Name);
    }
    void Retire()
    {
        if (bRetiring.exchange(true)) return;
        StopShot(); bActive = false;
        auto Self = StaticCastSharedRef<FExposureDiagnostic>(AsShared());
        ENQUEUE_RENDER_COMMAND(SoraArtExposureRetireAfterGraphs)([Self](FRHICommandListImmediate&)
        {
            // RDG passes may execute asynchronously after their render command.
            // Keep the owner alive through that task; never wait on the GPU.
            auto GraphExecution = FRDGBuilder::GetAsyncExecuteTask();
            UE::Tasks::Launch(UE_SOURCE_LOCATION, [Self]()
            {
                ENQUEUE_RENDER_COMMAND(SoraArtExposureRetire)([Self](FRHICommandListImmediate&) { Self->Retire_RenderThread(); });
            }, UE::Tasks::Prerequisites(GraphExecution));
        });
    }
    bool Retired() { Pump(); return bRetired; }

    virtual void BeginRenderViewFamily(FSceneViewFamily& Family) override
    {
        Pump();
        if (!ActiveShot || Family.Scene != Scene || Family.RenderTarget != Viewport) return;
        const FSceneView* PlayerView = nullptr;
        int32 Count = 0;
        for (const FSceneView* View : Family.Views)
            if (View && View->bIsGameView && !View->bIsSceneCapture && !View->bIsReflectionCapture && View->IsPrimarySceneView())
            { PlayerView = View; ++Count; }
        if (Count != 1 || !PlayerView->State)
        { Error(TEXT("Expected exactly one persistent player view")); return; }
        FShotResult& Shot = Shots.FindChecked(ActiveShot);
        const bool bScreenshot = !Shot.File.IsEmpty() && FScreenshotRequest::IsScreenshotRequested() &&
            FPaths::ConvertRelativePathToFull(FScreenshotRequest::GetFilename()) == Shot.File;
        if (!bScreenshot && Shot.Observations >= MaxObservations)
        { Error(Shot.Name + TEXT(": observation cap reached")); return; }
        if (bScreenshot && ++Shot.Requests != 1)
        { Error(Shot.Name + TEXT(": ambiguous screenshot frame")); return; }
        ++Shot.Observations;
        FFrame Frame;
        Frame.Shot = ActiveShot; Frame.Name = Shot.Name; Frame.File = bScreenshot ? Shot.File : FString();
        Frame.Counter = Family.FrameCounter; Frame.Number = Family.FrameNumber; Frame.ViewKey = PlayerView->GetViewKey();
        Frame.bScreenshot = bScreenshot;
        UWorld* World = Viewport->GetClient() ? Viewport->GetClient()->GetWorld() : nullptr;
        if (!World) { Error(Shot.Name + TEXT(": game viewport lost its world")); return; }
        Frame.bPaused = World->IsPaused();
        FScopeLock Lock(&Mutex);
        if (TaggedFrames.Num() >= 64 || TaggedFrames.Contains(Frame.Counter))
        { Error(Shot.Name + TEXT(": missing or ambiguous frame metadata capacity")); return; }
        ++Outstanding.FindOrAdd(ActiveShot);
        TaggedFrames.Add(Frame.Counter, MoveTemp(Frame));
    }
    virtual void PostRenderView_RenderThread(FRDGBuilder& GraphBuilder, FSceneView& View) override
    {
        if (bRetiring) return;
        if (View.Family->Scene != Scene || View.Family->RenderTarget != Viewport || View.bIsSceneCapture || View.bIsReflectionCapture) return;
        Poll_RenderThread(View.Family->FrameCounter);
        FFrame Frame;
        {
            FScopeLock Lock(&Mutex);
            FFrame* Found = TaggedFrames.Find(View.Family->FrameCounter);
            if (!Found || Found->ViewKey != View.GetViewKey() || Found->Number != View.Family->FrameNumber) return;
            Frame = MoveTemp(*Found);
            TaggedFrames.Remove(View.Family->FrameCounter);
        }
        const auto& Time = View.Family->Time;
        Frame.Values.Add(TEXT("delta_world_seconds"), Time.GetDeltaWorldTimeSeconds());
        Frame.Values.Add(TEXT("delta_real_seconds"), Time.GetDeltaRealTimeSeconds());
        Frame.Values.Add(TEXT("world_seconds"), Time.GetWorldTimeSeconds());
        Frame.Values.Add(TEXT("real_seconds"), Time.GetRealTimeSeconds());
        Frame.Values.Add(TEXT("camera_x"), View.ViewLocation.X); Frame.Values.Add(TEXT("camera_y"), View.ViewLocation.Y); Frame.Values.Add(TEXT("camera_z"), View.ViewLocation.Z);
        Frame.Values.Add(TEXT("camera_pitch"), View.ViewRotation.Pitch); Frame.Values.Add(TEXT("camera_yaw"), View.ViewRotation.Yaw); Frame.Values.Add(TEXT("camera_roll"), View.ViewRotation.Roll);
        Frame.Values.Add(TEXT("view_width"), View.UnscaledViewRect.Width()); Frame.Values.Add(TEXT("view_height"), View.UnscaledViewRect.Height());
        Frame.Flags.Add(TEXT("camera_cut"), View.bCameraCut);
        Frame.Flags.Add(TEXT("force_camera_visibility_reset"), View.bForceCameraVisibilityReset);
        Frame.Flags.Add(TEXT("eye_adaptation_showflag"), View.Family->EngineShowFlags.EyeAdaptation);
        Frame.Flags.Add(TEXT("fixed_exposure"), View.Family->ExposureSettings.bFixed);
        Frame.Values.Add(TEXT("fixed_exposure_ev100"), View.Family->ExposureSettings.FixedEV100);
        const auto& P = View.FinalPostProcessSettings;
#define ART_EXPOSURE_SETTING(Name) Frame.Values.Add(TEXT(#Name), P.Name)
        ART_EXPOSURE_SETTING(AutoExposureMethod); ART_EXPOSURE_SETTING(AutoExposureMinBrightness); ART_EXPOSURE_SETTING(AutoExposureMaxBrightness);
        ART_EXPOSURE_SETTING(HistogramLogMin); ART_EXPOSURE_SETTING(HistogramLogMax);
        ART_EXPOSURE_SETTING(AutoExposureLowPercent); ART_EXPOSURE_SETTING(AutoExposureHighPercent);
        ART_EXPOSURE_SETTING(AutoExposureSpeedUp); ART_EXPOSURE_SETTING(AutoExposureSpeedDown); ART_EXPOSURE_SETTING(AutoExposureBias);
#undef ART_EXPOSURE_SETTING
        Frame.Flags.Add(TEXT("force_target_proven_true"), View.bCameraCut ||
            !(P.AutoExposureMinBrightness < P.AutoExposureMaxBrightness) || P.AutoExposureSpeedUp < 0 || P.AutoExposureSpeedDown < 0);
        for (const TCHAR* Name : {TEXT("r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange"), TEXT("r.EyeAdaptation.MethodOverride"),
            TEXT("r.EyeAdaptationQuality"), TEXT("r.EyeAdaptation.LensAttenuation"), TEXT("r.EyeAdaptation.PreExposureOverride")})
            Frame.Values.Add(Name, CVar(Name));
        Frame.Values.Add(TEXT("cached_async_last_exposure_scale"), View.GetLastEyeAdaptationExposure());
        Frame.Values.Add(TEXT("cached_async_last_average_scene_luminance"), View.GetLastAverageSceneLuminance());
        if (View.State) Frame.Values.Add(TEXT("cached_async_state_pre_exposure"), View.State->GetPreExposure());
        for (const auto& Value : Frame.Values)
            if (!FMath::IsFinite(Value.Value))
            { Frame.Error = TEXT("Nonfinite or unavailable view exposure metadata: ") + Value.Key; Publish(MoveTemp(Frame)); return; }
        FRDGPooledBuffer* Buffer = View.GetEyeAdaptationBuffer();
        if (!View.HasValidEyeAdaptationBuffer() || !Buffer || Buffer->Desc.BytesPerElement != sizeof(FVector4f) || Buffer->Desc.NumElements != 2)
        { Frame.Error = TEXT("Missing or unexpected UE5.8.3 exposure buffer"); Publish(MoveTemp(Frame)); return; }
        FSlot* Available = nullptr;
        const int32 Start = Frame.bScreenshot ? 3 : 0, End = Frame.bScreenshot ? 4 : 3;
        for (int32 Index = Start; Index < End; ++Index)
            if (!Slots[Index].Frame.IsSet()) { Available = &Slots[Index]; break; }
        if (!Available)
        { Frame.Error = TEXT("GPU readback ring full; frame missing"); Publish(MoveTemp(Frame)); return; }
        if (!Available->Buffer) Available->Buffer = MakeUnique<FRHIGPUBufferReadback>(FName(TEXT("SoraArtExposure")));
        Available->Buffer->ResetReady();
        Available->Frame = MoveTemp(Frame);
        TRefCountPtr<FRDGPooledBuffer> OwnedBuffer(Buffer);
        AddEnqueueCopyPass(GraphBuilder, Available->Buffer.Get(), GraphBuilder.RegisterExternalBuffer(OwnedBuffer, ERDGBufferFlags::MultiFrame), sizeof(FVector4f));
    }
};

struct FShot
{
    const TCHAR* Name;
    FVector2D At;
    float Yaw;
    float Pitch;
    // Optional authored surface height: fail instead of silently photographing
    // the street beneath an elevated review point.
    float SurfaceHeight=-1.f;
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
    TSharedPtr<FExposureDiagnostic, ESPMode::ThreadSafe> Exposure;
    ~FSession()
    {
        if (Exposure) Exposure->Retire();
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
    const int32 ExposureDiagnostic = CVarArtExposureDiagnostic.GetValueOnGameThread();
    if (ExposureDiagnostic != 0)
    {
        const FEngineVersion& Version = FEngineVersion::Current();
        if (!Test.TestTrue(TEXT("Exposure diagnostic requires value 1 and audited UE5.8.3 CL58210709"),
            ExposureDiagnostic == 1 && Version.GetMajor() == 5 && Version.GetMinor() == 8 &&
            Version.GetPatch() == 3 && Version.GetChangelist() == 58210709)) return false;
        if (!Test.TestNotNull(TEXT("Exposure diagnostic has a game viewport"), Viewport->Viewport)) return false;
        Session.Exposure = FSceneViewExtensions::NewExtension<FExposureDiagnostic>(Viewport->Viewport,
            World->Scene, &Test, Session.Folder, ExposureDiagnostic);
    }
    return true;
}

void ShowHUD(ASoraGameMode& Mode, bool bShow)
{
    if (APlayerController* Controller = UGameplayStatics::GetPlayerController(&Mode, 0))
        if (AHUD* HUD = Controller->GetHUD())
            HUD->bShowHUD = bShow;
}

bool Stand(ASoraPlayerCharacter& Hero, const FShot& Shot)
{
    const float Half = Hero.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    FVector Spot(Shot.At.X, Shot.At.Y, Hero.GetActorLocation().Z);
    FHitResult Hit;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(SoraArtReviewStand), false, &Hero);
    const float Top = Hero.GetActorLocation().Z + 600.f;
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    if (Hero.GetWorld()->LineTraceSingleByObjectType(Hit, FVector(Shot.At.X, Shot.At.Y, Top), FVector(Shot.At.X, Shot.At.Y, Top - 8000.f),Objects,Query))
    {
        if(Shot.SurfaceHeight>=0&&FMath::Abs(Hit.ImpactPoint.Z-Shot.SurfaceHeight)>1.f)return false;
        const float NormalZ=Hit.ImpactNormal.Z;
        if(NormalZ<Hero.GetCharacterMovement()->GetWalkableFloorZ())return false;
        const float RoundedContact=Hero.GetCapsuleComponent()->GetScaledCapsuleRadius()*(1.f/NormalZ-1.f);
        Spot.Z=Hit.ImpactPoint.Z+Half+RoundedContact+2.15f;
    }
    else if(Shot.SurfaceHeight>=0)return false;
    Hero.GetCharacterMovement()->StopMovementImmediately();
    Hero.SetActorLocation(Spot, false, nullptr, ETeleportType::TeleportPhysics);
    if (APlayerController* Controller = Cast<APlayerController>(Hero.GetController()))
        Controller->SetControlRotation(FRotator(Shot.Pitch, Shot.Yaw, 0.f));
    UE_LOG(LogTemp,Display,TEXT("SORA_ART_REVIEW_SUPPORT shot=%s surface_z=%.3f expected_z=%.3f component=%s hero_z=%.3f"),
        Shot.Name,Hit.ImpactPoint.Z,Shot.SurfaceHeight,*GetNameSafe(Hit.GetComponent()),Hero.GetActorLocation().Z);
    return true;
}

void Frame(FAutomationTestBase* Test, FSessionRef Session, const FShot& Shot)
{
    Queue([Test,Session, Shot]()
    {
        ASoraGameMode* M = Session->M();
        ASoraPlayerCharacter* Hero = Session->Hero();
        if (!Session->bLive || !M || !Hero)
            return;
        if (Session->Exposure) Session->Exposure->BeginShot(Shot.Name);
        UGameplayStatics::SetGamePaused(M, false);
        if(!Test->TestTrue(TEXT("The review camera stands on its authored support surface"),Stand(*Hero,Shot)))Session->bLive=false;
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
        if (Session->Exposure) Session->Exposure->ArmScreenshot(Session->File);
        FScreenshotRequest::RequestScreenshot(Session->File, false, false);
    });
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(15.0, [Session](double)
    {
        return IFileManager::Get().FileSize(*Session->File) > 0 && IFileManager::Get().GetTimeStamp(*Session->File) != Session->Previous;
    }));
    if (Session->Exposure)
    {
        Queue([Session]() { Session->Exposure->StopShot(); });
        ADD_LATENT_AUTOMATION_COMMAND(FUntil(5.0, [Session](double) { return Session->Exposure->Drained(); }));
        Queue([Session, Name]() { Session->Exposure->ValidateShot(Name); });
    }
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
    if (Session->Exposure)
    {
        Queue([Session]() { Session->Exposure->Retire(); });
        ADD_LATENT_AUTOMATION_COMMAND(FUntil(5.0, [Session](double) { return Session->Exposure->Retired(); }));
        Queue([Test, Session]()
        {
            Test->TestTrue(TEXT("Art exposure diagnostic render-thread teardown completed"), Session->Exposure->Retired());
        });
    }
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

// A directed phase setup followed by the production reveal clock and camera.
// Unlike the fixed dojo views, this fixture never positions either character
// or a camera. Each still pauses a naturally reached mark, retaining the HUD
// and authored subtitle, and records the actual player-camera cache.
struct FArchiveSession : FSession
{
    TWeakObjectPtr<ASoraBoss> Rival;
    double Seconds = 0;
    FTransform Camera, HeroPose, RivalPose;
    FMinimalViewInfo View;
    FString Cue;
    bool bAtMark = false;
};

void RunArchiveReveal(FAutomationTestBase* Test)
{
    const TSharedRef<FArchiveSession> Session = MakeShared<FArchiveSession>();
    if (!Open(*Test, *Session)) return;
    if (!Test->TestFalse(TEXT("Archive review does not use the dojo exposure diagnostic"), Session->Exposure.IsValid())) return;
    Session->Folder /= TEXT("ArchiveReveal_") + FGuid::NewGuid().ToString(EGuidFormats::Digits);
    IFileManager::Get().MakeDirectory(*Session->Folder, true);
    Queue([Test, Session]()
    {
        ASoraGameMode* M = Session->M();
        USoraSaveGame* Save = Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!M || !Save || !USoraCampaignDirector::SeedCheckpoint(*Save, 5, 8) ||
            !UGameplayStatics::SaveGameToSlot(Save, Session->Slot, 0))
        { Test->AddError(TEXT("Archive review checkpoint could not be seeded")); return; }
        if (!M->bMenu) M->SetMenuOpen(true);
        M->SaveSlotName = Session->Slot;
        M->bDeterministicPractice = false;
        M->bCampaign = true;
        if (!M->Campaign()->LoadSave())
        { Test->AddError(TEXT("Archive review checkpoint could not be loaded")); return; }
        M->ResetRound(); M->BeginRound();
        M->Notice.Reset(); M->NoticeEnglish.Reset(); M->NoticeTime = 0.f;
        for (TActorIterator<ASoraBoss> It(M->GetWorld()); It; ++It)
            if (It->IsAlive()) Session->Rival = *It;
        if (!Test->TestNotNull(TEXT("Archive review has its real duel opponent"), Session->Rival.Get()) ||
            !Test->TestNotNull(TEXT("Archive review has its real hero"), Session->Hero())) return;
        // The fixture isolates staging; damage and AI holds are explicitly
        // directed, so these images are not ordinary duel-play evidence.
        Session->Rival->Hold(600000);
        ShowHUD(*M, true);
        Session->bLive = true;
#if WITH_EDITOR
        FAssetCompilingManager::Get().FinishAllCompilation();
        if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
#endif
        for (TObjectIterator<UTexture2D> It; It; ++It) It->SetForceMipLevelsToBeResident(600.f);
        IStreamingManager::Get().StreamAllResources(8.f);
    });
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(45.0, [Session](double)
    { return !Session->bLive || !Session->M() || Session->M()->Campaign()->LinesQueued() == 0; }));
    Queue([Test, Session]()
    {
        if (!Session->bLive || !Session->M() || !Session->Rival.IsValid()) return;
        if (!Test->TestEqual(TEXT("Opening speech finishes before directed phase damage"), Session->M()->Campaign()->LinesQueued(), 0))
        { Session->bLive = false; return; }
        UGameplayStatics::ApplyDamage(Session->Rival.Get(), Session->Rival->MaxHealth * .5f,
            nullptr, Session->Hero(), UDamageType::StaticClass());
    });
    struct FMark { const TCHAR* Name; double Seconds; };
    const FMark Marks[] = {
        {TEXT("01_Wide"), .20}, {TEXT("02_RackImpact"), 1.45},
        {TEXT("03_FirstLine"), 4.80}, {TEXT("04_FamilyPage"), 10.0},
        {TEXT("05_Reaction"), 18.20}, {TEXT("06_Return"), 19.70}
    };
    for (const FMark& Mark : Marks)
    {
        Queue([Session]() { Session->bAtMark = false; });
        ADD_LATENT_AUTOMATION_COMMAND(FUntil(30.0, [Test, Session, Mark](double)
        {
            if (!Session->bLive || !Session->M()) return true;
            auto* C = Session->M()->Campaign();
            if (!C->IsArchiveRevealActive() || C->ArchiveRevealTime() < Mark.Seconds) return false;
            Session->Seconds = C->ArchiveRevealTime();
            if (!Test->TestTrue(TEXT("The natural reveal reaches the requested mark without skipping it"), Session->Seconds < Mark.Seconds + .15))
            { Session->bLive = false; return true; }
            UGameplayStatics::SetGamePaused(Session->M(), true);
            auto* Shot = C->CinematicCamera();
            auto* PC = UGameplayStatics::GetPlayerController(Session->M(), 0);
            if (!Test->TestTrue(TEXT("The production reveal camera owns the actual local view"),
                Shot && PC && PC->PlayerCameraManager && PC->GetViewTarget() == Shot))
            { Session->bLive = false; return true; }
            Session->Camera = Shot->GetActorTransform();
            Session->HeroPose = Session->Hero()->GetActorTransform();
            Session->RivalPose = Session->Rival->GetActorTransform();
            Session->View = PC->PlayerCameraManager->GetCameraCacheView();
            const auto* Cue = C->CurrentDialogueCue();
            Session->Cue = Cue ? Cue->Id : FString();
            Session->bAtMark = true;
            return true;
        }));
        // Settle rendering without advancing the production scene clock.
        Wait(3.0);
        Queue([Test, Session, Mark]()
        {
            if (!Session->bLive || !Session->M()) return;
            if (!Test->TestTrue(TEXT("The reveal reached its capture mark"), Session->bAtMark))
            { Session->bLive = false; return; }
            Session->File = Session->Folder / (FString(Mark.Name) + TEXT(".png"));
            Session->Previous = IFileManager::Get().GetTimeStamp(*Session->File);
            FScreenshotRequest::RequestScreenshot(Session->File, false, false);
        });
        ADD_LATENT_AUTOMATION_COMMAND(FUntil(15.0, [Session](double)
        { return !Session->bLive || (IFileManager::Get().FileSize(*Session->File) > 0 && IFileManager::Get().GetTimeStamp(*Session->File) != Session->Previous); }));
        Queue([Test, Session, Mark]()
        {
            if (!Session->bLive || !Session->M()) return;
            auto* C = Session->M()->Campaign();
            auto* PC = UGameplayStatics::GetPlayerController(Session->M(), 0);
            auto* Shot = C->CinematicCamera();
            const bool Written = IFileManager::Get().FileSize(*Session->File) > 0 &&
                IFileManager::Get().GetTimeStamp(*Session->File) != Session->Previous;
            const auto* Cue = C->CurrentDialogueCue();
            const bool Frozen = C->IsArchiveRevealActive() && C->ArchiveRevealTime() == Session->Seconds &&
                UGameplayStatics::IsGamePaused(Session->M()) && Shot && PC && PC->PlayerCameraManager && PC->GetViewTarget() == Shot &&
                Session->Camera.Equals(Shot->GetActorTransform(), .001f) &&
                Session->HeroPose.Equals(Session->Hero()->GetActorTransform(), .001f) &&
                Session->RivalPose.Equals(Session->Rival->GetActorTransform(), .001f) &&
                Session->Cue == (Cue ? Cue->Id : FString());
            if (!Test->TestTrue(TEXT("A new original archive frame was written"), Written) ||
                !Test->TestTrue(TEXT("The scene and dialogue remained frozen through the screenshot"), Frozen))
            { Session->bLive = false; return; }
            const FMinimalViewInfo& View = PC->PlayerCameraManager->GetCameraCacheView();
            if (!Test->TestTrue(TEXT("The actual camera cache remains stable during capture"),
                View.Location.Equals(Session->View.Location, .001) && View.Rotation.Equals(Session->View.Rotation, .001) &&
                FMath::IsNearlyEqual(View.FOV, Session->View.FOV, .001f)))
            { Session->bLive = false; return; }
            // This observation is archived in the raw capture log alongside
            // the PNG acknowledgement; it describes the view actually drawn,
            // without substituting a separately posed review camera.
            UE_LOG(LogTemp, Display, TEXT("SORA_ARCHIVE_REVEAL_VIEW name=%s seconds=%.9f cue=%s target=%s camera=(%s) view=(%s) rotation=(%s) fov=%.6f hero=(%s) rival=(%s) hud=1 directed_damage=1 held_ai=1"),
                Mark.Name, Session->Seconds, *Session->Cue, *Shot->GetName(), *Session->Camera.GetLocation().ToString(),
                *View.Location.ToString(), *View.Rotation.ToString(), View.FOV,
                *Session->HeroPose.GetLocation().ToString(), *Session->RivalPose.GetLocation().ToString());
            UE_LOG(LogTemp, Display, TEXT("SORA_ART_REVIEW_FRAME %s"), *Session->File);
            UGameplayStatics::SetGamePaused(Session->M(), false);
        });
    }
    ADD_LATENT_AUTOMATION_COMMAND(FUntil(10.0, [Session](double)
    { return !Session->bLive || !Session->M() || !Session->M()->Campaign()->IsArchiveRevealActive(); }));
    Wait(.5);
    Queue([Test, Session]()
    {
        ASoraGameMode* M = Session->M();
        if (!M) return;
        if (Session->bLive)
        {
            auto* PC = UGameplayStatics::GetPlayerController(M, 0);
            Test->TestTrue(TEXT("The captured reveal naturally releases to the player"),
                !M->Campaign()->IsArchiveRevealActive() && PC && PC->GetViewTarget() == Session->Hero());
        }
        UGameplayStatics::SetGamePaused(M, false);
        ShowHUD(*M, true);
        if (!M->bMenu) M->SetMenuOpen(true);
        M->SaveSlotName = Session->PlayerSlot;
        M->bCampaign = true;
        M->Campaign()->LoadSave(); M->ResetRound();
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

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraArtReviewArchiveRevealTest, "SoraCapture.ArtReview.ArchiveReveal",
    EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter)
bool FSoraArtReviewArchiveRevealTest::RunTest(const FString& Parameters)
{
    SoraArtReview::RunArchiveReveal(this);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraArtReviewNoticeRoofTest, "SoraCapture.ArtReview.NoticeRoof",
    EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter)
bool FSoraArtReviewNoticeRoofTest::RunTest(const FString& Parameters)
{
    // Directed architectural review, independent of the mapped traversal
    // tests. These views confer neither gameplay nor final-art acceptance.
    SoraArtReview::Run(this,2,9,{
        {TEXT("NoticeRoof_StreetFacade"),FVector2D(1600,100),140,12,0},
        {TEXT("NoticeRoof_LowerFlight"),FVector2D(380,1810),-70,24,0},
        {TEXT("NoticeRoof_CanopyFlight"),FVector2D(500,1420),-38,22,320},
        {TEXT("NoticeRoof_RidgeReturn"),FVector2D(1200,850),153,-20,726.25}});
    return true;
}
#endif
