#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS && !UE_BUILD_SHIPPING && !UE_BUILD_TEST
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "World/SoraPresentationCapabilities.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DataDrivenShaderPlatformInfo.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/HUD.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/PackageName.h"
#include "Misc/SecureHash.h"
#include "UObject/Package.h"
#include "Materials/MaterialInterface.h"
#include "NaniteVisualizationData.h"
#include "RHI.h"
#include "DynamicRHI.h"
#include "RHIGlobals.h"
#include "RenderingThread.h"
#include "SceneInterface.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UObjectIterator.h"
#include "UnrealClient.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "ShaderCompiler.h"
#endif

// Development-only evidence capture. Never changes assets, r.Nanite, the
// environment tier, or materials. Visualization and the camera are temporary;
// a success here means originals were captured, not that Nanite drew anything.
// The archive verifier must find green Mask pixels on the production dojo and
// a corresponding different Triangles frame. Zero coverage is a failed gate.
namespace SoraNaniteDrawCapture
{
constexpr const TCHAR* Scope=TEXT("production dojo renderer diagnostic; unadmitted art; not gameplay or platform release acceptance");
const TCHAR* Cameras[]={TEXT("entry"),TEXT("ceiling")};
const TCHAR* Modes[]={TEXT("Lit"),TEXT("Mask"),TEXT("Triangles")};
const FVector Locations[]={FVector(8420,0,154),FVector(9500,-200,154)};
const FRotator Rotations[]={FRotator(4,0,0),FRotator(52,20,0)};
TArray<TSharedPtr<FJsonValue>> Vec(const FVector& V)
{ return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)}; }
struct FCVar
{
    IConsoleVariable* Var=nullptr; FString Name,Value; EConsoleVariableFlags Flags=ECVF_Default;
    bool Save(const TCHAR* InName)
    {
        Name=InName; Var=IConsoleManager::Get().FindConsoleVariable(InName);
        if (!Var) return false; Value=Var->GetString(); Flags=Var->GetFlags(); return true;
    }
    void Set(const TCHAR* V) const { Var->Set(V,static_cast<EConsoleVariableFlags>(Flags&ECVF_SetByMask)); }
    bool Restore() const
    {
        if (!Var) return true;
        Set(*Value); Var->SetFlags(Flags);
        return Var->GetString()==Value&&Var->GetFlags()==Flags;
    }
};
class FRun final:public IAutomationLatentCommand
{
public:
    FRun(FAutomationTestBase& InTest,bool InSM6):Test(InTest),SM6(InSM6) {}
    ~FRun() { Cleanup(); }
    bool Update() override
    {
        if (!Started) { Started=true; Begin(); }
        if (Failed||Step==Count()) { Cleanup(); return true; }
        if (FPlatformTime::Seconds()-StartTime>150) { Fail(TEXT("Nanite draw capture timed out")); Cleanup(); return true; }
        if (!M.IsValid()||!Camera.IsValid()||!PC()||!M->GetWorld()->IsPaused())
        { Fail(TEXT("Capture lost its paused production world/camera")); return false; }
        if (!Waiting&&FPlatformTime::Seconds()-ChangedAt>=3) Capture();
        return false;
    }
private:
    FAutomationTestBase& Test;
    bool NaniteEligible=false,SM6=false,Started=false,Failed=false,Cleaned=false,BackedUp=false,ChangedWorld=false,Waiting=false;
    bool WasCampaign=false,WasPractice=false,WasPaused=false,ShowHUD=true;
    int32 Step=0,OldViewMode=0; double StartTime=0,ChangedAt=0;
    TWeakObjectPtr<ASoraGameMode> M;
    TWeakObjectPtr<ACameraActor> Camera;
    TWeakObjectPtr<AActor> OldTarget;
    TWeakObjectPtr<AHUD> HUD;
    SoraUI::EScreen OldScreen=SoraUI::EScreen::Title;
    FEngineShowFlags OldFlags{ESFIM_Game}; FName OldNaniteMode;
    FString Slot,Slots[3],Folder,Pending,ShaderPlatform;
    TArray<uint8> Profile[3]; bool Existed[3]={};
    FCVar Visualize,Composite,Edges,Shading;
    FDelegateHandle Screenshot;
    FVector2D ViewportSize=FVector2D::ZeroVector;
    TArray<TSharedPtr<FJsonValue>> Frames,Meshes,AssetFiles;
    TSet<FString> HashedFiles;
    int32 Count() const { return SM6?6:2; }
    APlayerController* PC() const { return M.IsValid()?UGameplayStatics::GetPlayerController(M.Get(),0):nullptr; }
    UGameViewportClient* Viewport() const { return M.IsValid()?M->GetWorld()->GetGameViewport():nullptr; }
    void Fail(const TCHAR* Reason) { if (!Failed) Test.AddError(Reason); Failed=true; }
    FString CVar(const TCHAR* Name) const
    { const auto* V=IConsoleManager::Get().FindConsoleVariable(Name); return V?V->GetString():TEXT("absent"); }
    TSharedRef<FJsonObject> RenderState() const
    {
        auto O=MakeShared<FJsonObject>();
        for (const TCHAR* Name:{TEXT("r.Nanite"),TEXT("r.Nanite.ProxyRenderMode"),TEXT("r.Nanite.Visualize"),
            TEXT("r.Nanite.Visualize.Composite"),TEXT("r.Nanite.Visualize.EdgeDetect"),TEXT("r.Nanite.Visualize.DebugShading"),
            TEXT("r.ScreenPercentage"),TEXT("r.AntiAliasingMethod"),TEXT("sora.HallInstanced")}) O->SetStringField(Name,CVar(Name));
        return O;
    }
    void Begin()
    {
        StartTime=FPlatformTime::Seconds();
        for (const auto& C:GEngine->GetWorldContexts())
            if (C.WorldType==EWorldType::Game&&C.World()) M=Cast<ASoraGameMode>(C.World()->GetAuthGameMode());
        if (!M.IsValid()||!PC()||!PC()->PlayerCameraManager||!Viewport()||!M->GetWorld()->Scene||!M->Campaign()||!M->FrontEnd()||!FSoraCatalog::Get().IsReady()||GUsingNullRHI)
        { Fail(TEXT("Nanite evidence requires a rendered game with its production catalog")); return; }
        // Rebuilding an active game would lose unsaved play. Only a disposable
        // launch at Title/Main is permitted; cleanup rebuilds that checkpoint.
        OldScreen=M->FrontEnd()->Screen();
        if (!M->bMenu||M->bDeterministicPractice||!M->GetWorld()->IsPaused()||
            (OldScreen!=SoraUI::EScreen::Title&&OldScreen!=SoraUI::EScreen::Main))
        { Fail(TEXT("Start this diagnostic in a fresh paused Title/Main session, never active play")); return; }
        const EShaderPlatform Platform=M->GetWorld()->Scene->GetShaderPlatform();
        if (!FDataDrivenShaderPlatformInfo::IsValid(Platform)) { Fail(TEXT("Actual scene shader platform is invalid")); return; }
        ShaderPlatform=FDataDrivenShaderPlatformInfo::GetName(Platform).ToString();
        const bool Eligible=SoraPresentation::UsesNaniteEnvironment(M->GetWorld()); NaniteEligible=Eligible;
        if ((SM6&&(!ShaderPlatform.Contains(TEXT("SM6"))||!Eligible))||
            (!SM6&&(!ShaderPlatform.Contains(TEXT("SM5"))||Eligible)))
        { Fail(TEXT("Actual shader platform/capability does not match the separately requested SM6 or SM5 diagnostic")); return; }
        Viewport()->GetViewportSize(ViewportSize);
        if (ViewportSize!=FVector2D(1280,720)&&ViewportSize!=FVector2D(1920,1080))
        { Fail(TEXT("Nanite capture requires 1280x720 or 1920x1080")); return; }
        Slots[0]=M->SaveSlotName; Slots[1]=M->ControlSlotName; Slots[2]=M->SettingsSlotName;
        for (int32 I=0;I<3;++I)
        {
            Existed[I]=UGameplayStatics::DoesSaveGameExist(Slots[I],0);
            if (Existed[I]&&!UGameplayStatics::LoadDataFromSlot(Profile[I],Slots[I],0))
            { Fail(TEXT("Could not preserve original profile bytes")); return; }
        }
        WasCampaign=M->bCampaign; WasPractice=M->bDeterministicPractice; WasPaused=M->GetWorld()->IsPaused();
        OldTarget=PC()->GetViewTarget(); HUD=PC()->GetHUD(); if (HUD.IsValid()) ShowHUD=HUD->bShowHUD;
        OldViewMode=Viewport()->ViewModeIndex; OldFlags=Viewport()->EngineShowFlags; OldNaniteMode=Viewport()->GetCurrentNaniteVisualizationMode();
        BackedUp=true;
        GetNaniteVisualizationData(); // Initializes the engine-owned cvar registry.
        if (!Visualize.Save(TEXT("r.Nanite.Visualize"))||!Composite.Save(TEXT("r.Nanite.Visualize.Composite"))||
            !Edges.Save(TEXT("r.Nanite.Visualize.EdgeDetect"))||!Shading.Save(TEXT("r.Nanite.Visualize.DebugShading")))
        { Fail(TEXT("Engine Nanite visualization controls are unavailable")); return; }
        Slot=TEXT("SoraNaniteDraw_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
        Folder=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Screenshots/SoraNaniteDraw")/
            FString::Printf(TEXT("%dx%d"),int32(ViewportSize.X),int32(ViewportSize.Y))/FGuid::NewGuid().ToString(EGuidFormats::Digits));
        IFileManager::Get().MakeDirectory(*Folder,true);
        auto* Save=Cast<USoraSaveGame>(UGameplayStatics::CreateSaveGameObject(USoraSaveGame::StaticClass()));
        if (!Save||!USoraCampaignDirector::SeedCheckpoint(*Save,0,1)||!UGameplayStatics::SaveGameToSlot(Save,Slot,0))
        { Fail(TEXT("Could not create the isolated production dojo checkpoint")); return; }
        ChangedWorld=true; M->SaveSlotName=Slot; M->bCampaign=true; M->bDeterministicPractice=false;
        if (!M->Campaign()->LoadSave()) { Fail(TEXT("Dojo checkpoint did not load")); return; }
        M->ResetRound(); M->SetMenuOpen(false); UGameplayStatics::SetGamePaused(M.Get(),true);
        if (HUD.IsValid()) HUD->bShowHUD=false;
        Camera=M->GetWorld()->SpawnActor<ACameraActor>();
        if (!Camera.IsValid()) { Fail(TEXT("Could not create a temporary diagnostic camera")); return; }
        Camera->GetCameraComponent()->SetFieldOfView(94.f);
        PC()->SetViewTarget(Camera.Get());
#if WITH_EDITOR
        FAssetCompilingManager::Get().FinishAllCompilation();
        if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
#endif
        Inventory();
        Screenshot=FScreenshotRequest::OnScreenshotRequestProcessed().AddRaw(this,&FRun::Captured);
        Switch();
    }
    void Inventory()
    {
        // Only actual registered components from the current production world.
        // Bounds/asset validity are identities, never a visible-draw counter.
        for (TObjectIterator<UStaticMeshComponent> It;It;++It)
        {
            auto* C=*It; auto* Mesh=C->GetStaticMesh().Get();
            if (C->GetWorld()!=M->GetWorld()||!C->IsRegistered()||!C->IsVisible()||!Mesh||
                !Mesh->GetPathName().StartsWith(TEXT("/Game/Generated/Environment/DojoKit/"))) continue;
            auto O=MakeShared<FJsonObject>(); O->SetStringField(TEXT("component"),C->GetPathName());
            O->SetStringField(TEXT("mesh"),Mesh->GetPathName()); O->SetStringField(TEXT("class"),C->GetClass()->GetName());
            O->SetBoolField(TEXT("has_nanite_data"),Mesh->HasValidNaniteData());
            if (Mesh->HasValidNaniteData()) O->SetBoolField(TEXT("has_platform_fallback"),Mesh->HasNaniteFallbackMesh(M->GetWorld()->Scene->GetShaderPlatform()));
            O->SetBoolField(TEXT("disallow_nanite"),C->IsDisallowNanite());
            O->SetBoolField(TEXT("force_disable_nanite"),C->IsForceDisableNanite());
            const FString Package=FPaths::ConvertRelativePathToFull(FPackageName::LongPackageNameToFilename(Mesh->GetOutermost()->GetName(),FPackageName::GetAssetPackageExtension()));
            O->SetStringField(TEXT("package_file"),Package);
            if (IFileManager::Get().FileSize(*Package)<=0) { Fail(TEXT("This uncooked diagnostic requires the original loose dojo mesh packages")); return; }
            for (const FString& File:{Package,FPaths::ChangeExtension(Package,TEXT("uexp")),FPaths::ChangeExtension(Package,TEXT("ubulk"))})
            {
                const int64 Size=IFileManager::Get().FileSize(*File);
                if (Size<=0||HashedFiles.Contains(File)) continue;
                auto A=MakeShared<FJsonObject>(); A->SetStringField(TEXT("path"),File); A->SetNumberField(TEXT("bytes"),double(Size));
                A->SetStringField(TEXT("md5"),LexToString(FMD5Hash::HashFile(*File)));
                AssetFiles.Add(MakeShared<FJsonValueObject>(A)); HashedFiles.Add(File);
            }
#if WITH_EDITORONLY_DATA
            O->SetBoolField(TEXT("authoring_nanite_enabled"),Mesh->IsNaniteEnabled());
#endif
            // Instances were just populated; the public cached Bounds can
            // still be zero before the first frame. Query their actual mesh
            // and instance transforms without changing the production scene.
            const FBoxSphereBounds Bounds=C->CalcBounds(C->GetComponentTransform());
            O->SetStringField(TEXT("bounds_source"),TEXT("component CalcBounds at current transform; not render coverage"));
            O->SetArrayField(TEXT("bounds_origin"),Vec(Bounds.Origin)); O->SetArrayField(TEXT("bounds_extent"),Vec(Bounds.BoxExtent));
            O->SetArrayField(TEXT("cached_bounds_origin"),Vec(C->Bounds.Origin)); O->SetArrayField(TEXT("cached_bounds_extent"),Vec(C->Bounds.BoxExtent));
            const auto* Instances=Cast<UInstancedStaticMeshComponent>(C);
            O->SetNumberField(TEXT("instances"),Instances?Instances->GetInstanceCount():1);
            TArray<TSharedPtr<FJsonValue>> Materials;
            for (int32 I=0;I<C->GetNumMaterials();++I)
                Materials.Add(MakeShared<FJsonValueString>(GetPathNameSafe(C->GetMaterial(I))));
            O->SetArrayField(TEXT("materials"),Materials); Meshes.Add(MakeShared<FJsonValueObject>(O));
        }
        if (Meshes.IsEmpty()) Fail(TEXT("Production dojo kit is absent; primitive replacements are not evidence"));
    }
    void Switch()
    {
        const int32 Cam=SM6?Step/3:Step, Mode=SM6?Step%3:0;
        Camera->SetActorLocationAndRotation(Locations[Cam],Rotations[Cam]);
        // Update the ordinary camera cache even though gameplay is paused.
        PC()->PlayerCameraManager->UpdateCamera(0.f);
        Viewport()->SetViewMode(VMI_Lit);
        Viewport()->SetCurrentNaniteVisualizationMode(NAME_None);
        Visualize.Set(Mode?Modes[Mode]:TEXT("off"));
        Composite.Set(TEXT("1")); Edges.Set(TEXT("0")); Shading.Set(TEXT("0"));
        Viewport()->EngineShowFlags.SetVisualizeNanite(Mode!=0);
        ChangedAt=FPlatformTime::Seconds();
    }
    void Capture()
    {
        const int32 Cam=SM6?Step/3:Step, Mode=SM6?Step%3:0;
        // Read the engine renderer's completed mode selection, not a locally
        // forced Update. This synchronization is not a performance sample.
        FlushRenderingCommands();
        const auto& Data=GetNaniteVisualizationData();
        if (Mode&&(Data.GetActiveModeName()!=FName(Modes[Mode])||!Data.IsActive()))
        { Fail(TEXT("Engine did not activate the requested Nanite visualization")); return; }
        if (!Mode&&Data.IsActive()) { Fail(TEXT("Normal comparison still has Nanite visualization active")); return; }
        const FVector At=PC()->PlayerCameraManager->GetCameraLocation();
        const FRotator Rot=PC()->PlayerCameraManager->GetCameraRotation();
        if (!At.Equals(Locations[Cam],.01)||!Rot.Equals(Rotations[Cam],.001)||PC()->GetViewTarget()!=Camera.Get())
        { Fail(TEXT("Actual camera differs from the fixed production-dojo view")); return; }
        const FString Name=FString(Cameras[Cam])+TEXT("-")+Modes[Mode];
        auto O=MakeShared<FJsonObject>(); O->SetStringField(TEXT("name"),Name); O->SetStringField(TEXT("mode"),Modes[Mode]);
        O->SetStringField(TEXT("camera_id"),Cameras[Cam]); O->SetArrayField(TEXT("camera"),Vec(At));
        O->SetArrayField(TEXT("rotation"),Vec(FVector(Rot.Pitch,Rot.Yaw,Rot.Roll)));
        O->SetNumberField(TEXT("fov"),PC()->PlayerCameraManager->GetFOVAngle());
        O->SetNumberField(TEXT("request_frame"),double(GFrameCounter)); O->SetNumberField(TEXT("settle_seconds"),FPlatformTime::Seconds()-ChangedAt);
        O->SetStringField(TEXT("active_visualization"),Data.GetActiveModeName().ToString());
        O->SetNumberField(TEXT("active_mode_id"),Data.GetActiveModeID());
        O->SetBoolField(TEXT("show_visualize_nanite"),Viewport()->EngineShowFlags.VisualizeNanite);
        O->SetObjectField(TEXT("cvars"),RenderState());
        O->SetBoolField(TEXT("paused"),M->GetWorld()->IsPaused()); O->SetBoolField(TEXT("hud_hidden"),!HUD.IsValid()||!HUD->bShowHUD);
        Frames.Add(MakeShared<FJsonValueObject>(O)); Pending=Folder/(Name+TEXT(".png")); Waiting=true;
        FScreenshotRequest::RequestScreenshot(Pending,false,false);
    }
    void Captured()
    {
        if (!Waiting) return;
        if (IFileManager::Get().FileSize(*Pending)<=0) { Fail(TEXT("Original Nanite diagnostic screenshot was not written")); return; }
        Frames.Last()->AsObject()->SetStringField(TEXT("file"),FPaths::GetCleanFilename(Pending));
        Frames.Last()->AsObject()->SetNumberField(TEXT("screenshot_processed_frame"),double(GFrameCounter));
        UE_LOG(LogTemp,Display,TEXT("SORA_NANITE_DRAW_FRAME %s"),*Pending);
        Waiting=false; Pending.Reset(); ++Step;
        if (Step<Count()) Switch();
    }
    void Cleanup()
    {
        if (Cleaned) return; Cleaned=true;
        if (Waiting) FScreenshotRequest::Reset();
        FScreenshotRequest::OnScreenshotRequestProcessed().Remove(Screenshot);
        bool Restored=true;
        for (const FCVar* V:{&Visualize,&Composite,&Edges,&Shading}) Restored=V->Restore()&&Restored;
        if (BackedUp&&!M.IsValid()) Restored=false;
        if (BackedUp&&M.IsValid())
        {
            if (ChangedWorld)
            {
                M->SetMenuOpen(true); M->SaveSlotName=Slots[0]; M->bCampaign=WasCampaign; M->bDeterministicPractice=WasPractice;
                Restored=M->Campaign()->LoadSave()&&Restored; M->ResetRound();
                if (OldScreen==SoraUI::EScreen::Title) M->FrontEnd()->ShowTitle(); else M->FrontEnd()->ShowMain();
            }
            if (PC()) PC()->SetViewTarget(OldTarget.IsValid()?OldTarget.Get():M->Hero());
            if (Camera.IsValid()) Camera->Destroy();
            if (HUD.IsValid()) HUD->bShowHUD=ShowHUD;
            if (Viewport())
            {
                Viewport()->SetViewMode(static_cast<EViewModeIndex>(OldViewMode));
                Viewport()->EngineShowFlags=OldFlags; Viewport()->SetCurrentNaniteVisualizationMode(OldNaniteMode);
            }
            UGameplayStatics::SetGamePaused(M.Get(),WasPaused);
            Restored=(M->SaveSlotName==Slots[0]&&M->bCampaign==WasCampaign&&M->bDeterministicPractice==WasPractice&&
                M->bMenu&&M->FrontEnd()->Screen()==OldScreen&&M->GetWorld()->IsPaused()==WasPaused&&
                (!HUD.IsValid()||HUD->bShowHUD==ShowHUD)&&Viewport()&&Viewport()->ViewModeIndex==OldViewMode&&
                Viewport()->GetCurrentNaniteVisualizationMode()==OldNaniteMode&&
                Viewport()->EngineShowFlags.VisualizeNanite==OldFlags.VisualizeNanite)&&Restored;
        }
        if (BackedUp)
        {
            // LoadSave/ResetRound may create a missing default save. Restore
            // raw bytes/existence AFTER that reconstruction, including failure.
            for (int32 I=0;I<3;++I)
            {
                if (Existed[I]) Restored=UGameplayStatics::SaveDataToSlot(Profile[I],Slots[I],0)&&Restored;
                else if (UGameplayStatics::DoesSaveGameExist(Slots[I],0)) Restored=UGameplayStatics::DeleteGameInSlot(Slots[I],0)&&Restored;
                TArray<uint8> After;
                Restored=(UGameplayStatics::DoesSaveGameExist(Slots[I],0)==Existed[I]&&
                    (!Existed[I]||(UGameplayStatics::LoadDataFromSlot(After,Slots[I],0)&&After==Profile[I])))&&Restored;
            }
        }
        if (!Slot.IsEmpty()&&UGameplayStatics::DoesSaveGameExist(Slot,0)) Restored=UGameplayStatics::DeleteGameInSlot(Slot,0)&&Restored;
        Test.TestTrue(TEXT("Nanite diagnostic restores original menu checkpoint, HUD, profile bytes/existence and temporary cvars"),Restored);
        if (!Folder.IsEmpty())
        {
            auto O=MakeShared<FJsonObject>(); O->SetStringField(TEXT("schema"),TEXT("sora-arena.nanite-draw.v1"));
            O->SetStringField(TEXT("scope"),Scope); O->SetBoolField(TEXT("sm6_requested"),SM6);
            O->SetBoolField(TEXT("nanite_eligible"),NaniteEligible);
            O->SetStringField(TEXT("shader_platform"),ShaderPlatform); O->SetStringField(TEXT("rhi"),GDynamicRHI?GDynamicRHI->GetName():TEXT("none"));
            O->SetStringField(TEXT("adapter"),GRHIAdapterName); O->SetBoolField(TEXT("null_rhi"),GUsingNullRHI);
            O->SetArrayField(TEXT("viewport"),{MakeShared<FJsonValueNumber>(ViewportSize.X),MakeShared<FJsonValueNumber>(ViewportSize.Y)});
            O->SetArrayField(TEXT("asset_files"),AssetFiles); O->SetArrayField(TEXT("meshes"),Meshes); O->SetArrayField(TEXT("frames"),Frames); O->SetNumberField(TEXT("frame_count"),Frames.Num());
            O->SetBoolField(TEXT("restored"),Restored); O->SetBoolField(TEXT("passed"),!Failed&&!Test.HasAnyErrors()&&Step==Count());
            O->SetStringField(TEXT("acceptance"),TEXT("original pixel validation and human geometry attribution required; no GPU counters inferred"));
            FString Json; FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Json));
            Test.TestTrue(TEXT("Writes original Nanite draw observation report"),FFileHelper::SaveStringToFile(Json,*(Folder/TEXT("capture.json"))));
        }
    }
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraNaniteDrawSM6Test,"SoraCapture.NaniteDraw.DojoSM6",EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraNaniteDrawSM6Test::RunTest(const FString& Parameters)
{ (void)Parameters; FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<SoraNaniteDrawCapture::FRun>(*this,true)); return true; }
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraNaniteDrawSM5Test,"SoraCapture.NaniteDraw.DojoSM5",EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraNaniteDrawSM5Test::RunTest(const FString& Parameters)
{ (void)Parameters; FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<SoraNaniteDrawCapture::FRun>(*this,false)); return true; }
#endif
