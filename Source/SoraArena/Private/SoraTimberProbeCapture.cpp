#include "SoraGameMode.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR && !UE_BUILD_SHIPPING && !UE_BUILD_TEST
#include "SoraFrontEnd.h"
#include "World/SoraPresentationCapabilities.h"
#include "World/SoraCaptureReadiness.h"
#include "AssetCompilingManager.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DataDrivenShaderPlatformInfo.h"
#include "Dom/JsonObject.h"
#include "DynamicRHI.h"
#include "DynamicResolutionState.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/PointLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/Texture.h"
#include "Engine/World.h"
#include "GameFramework/HUD.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstance.h"
#include "Materials/MaterialRenderProxy.h"
#include "MaterialShared.h"
#include "MeshDescription.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"
#include "NaniteVisualizationData.h"
#include "Rendering/NaniteResources.h"
#include "RenderingThread.h"
#include "RHIGlobals.h"
#include "SceneInterface.h"
#include "SceneView.h"
#include "SceneViewExtension.h"
#include "Serialization/JsonSerializer.h"
#include "ShaderCompiler.h"
#include "StaticMeshAttributes.h"
#include "StaticMeshResources.h"
#include "UnrealClient.h"

// A separate fixture and schema: this does not relax the production dojo gate.
// No asset saves, world rebuilds, material substitutions or r.Nanite overrides.
// CPU source/resource observations are NEVER evidence of a visible Nanite draw.
namespace SoraTimberProbeCapture
{
constexpr const TCHAR* Root=TEXT("/Game/Generated/Qualification/DojoTimberProbe/");
constexpr const TCHAR* Scope=TEXT("nine saved timber probe assets in an isolated fixture; not production placement, art or platform acceptance");
const TCHAR* Names[]={
    TEXT("SM_DojoTimberColumn_8000_m1300_11600_1300_S0_B18"),
    TEXT("SM_DojoTimberRail_Cornice_8000_m1300_11600_1300_S1_B01"),
    TEXT("SM_DojoTimberRail_Koshi_8000_m1300_11600_1300_S2_B15"),
    TEXT("SM_DojoTimberRail_Nageshi_8000_m1300_11600_1300_S1_B00"),
    TEXT("SM_DojoTimberRail_Nuki_8000_m1300_11600_1300_S3_B13"),
    TEXT("SM_DojoTimberColumn_MAC_Wall_09"),TEXT("SM_DojoTimberColumn_MAC_Open_02"),
    TEXT("SM_DojoTimberRail_MAC_Nageshi_01"),TEXT("SM_DojoTimberRail_MAC_Nuki_01")};
const TCHAR* Modes[]={TEXT("Lit"),TEXT("Mask"),TEXT("Triangles"),TEXT("Lit")};
const FVector Origin(1000000,1000000,1000000);
TArray<TSharedPtr<FJsonValue>> Vec(const FVector& V)
{ return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)}; }
TArray<TSharedPtr<FJsonValue>> UV(const FVector2f& V)
{ return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y)}; }
TArray<TSharedPtr<FJsonValue>> Color(const FVector4& V)
{ return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z),MakeShared<FJsonValueNumber>(V.W)}; }
struct FResolutionControls
{
    // Cache absence as well as presence once per fixture. Repeated queries of
    // the unregistered test CVar cause UE5.8's frequent-lookup warning.
    IConsoleVariable* Screen=IConsoleManager::Get().FindConsoleVariable(TEXT("r.ScreenPercentage"));
    IConsoleVariable* Override=IConsoleManager::Get().FindConsoleVariable(TEXT("r.Test.OverrideScreenPercentageInterface"));
    TSharedRef<FJsonObject> Read() const
    {
        auto O=MakeShared<FJsonObject>(); const auto* V=Screen;
        O->SetNumberField(TEXT("screen_percentage"),V?V->GetFloat():-1);
        O->SetNumberField(TEXT("flags"),V?uint32(V->GetFlags()):0);
        O->SetStringField(TEXT("set_by"),V?GetConsoleVariableSetByName(V->GetFlags()):TEXT("absent"));
        FDynamicResolutionStateInfos Dynamic; GEngine->GetDynamicResolutionCurrentStateInfos(Dynamic);
        const TCHAR* Status=TEXT("unknown");
        switch (Dynamic.Status)
        {
            case EDynamicResolutionStatus::Unsupported: Status=TEXT("Unsupported"); break;
            case EDynamicResolutionStatus::Disabled: Status=TEXT("Disabled"); break;
            case EDynamicResolutionStatus::Paused: Status=TEXT("Paused"); break;
            case EDynamicResolutionStatus::Enabled: Status=TEXT("Enabled"); break;
            case EDynamicResolutionStatus::DebugForceEnabled: Status=TEXT("DebugForceEnabled"); break;
        }
        O->SetStringField(TEXT("dynamic_resolution_status"),Status);
        // This test CVar is mentioned by SceneView.h but is not registered in
        // this UE5.8 build. Absence is a separate observation, not a value of -1.
        O->SetBoolField(TEXT("test_interface_override_registered"),Override!=nullptr);
        if (Override) O->SetNumberField(TEXT("test_interface_override"),Override->GetInt());
        else O->SetField(TEXT("test_interface_override"),MakeShared<FJsonValueNull>());
        return O;
    }
};
// This callback runs on the game thread after the actual viewport view has
// blended its unbound volumes and owned camera. It only observes the one view
// whose screenshot request matches the original file; no synthetic CalcSceneView.
class FViewObservation final:public FSceneViewExtensionBase
{
    FViewport* Viewport; FSceneInterface* Scene; FResolutionControls Resolution;
    TSharedPtr<FJsonObject> Frame; FString File; int32 Observations=0;
protected:
    bool IsActiveThisFrame_Internal(const FSceneViewExtensionContext& Context) const override
    { return Frame.IsValid()&&Context.Viewport==Viewport; }
public:
    FViewObservation(const FAutoRegister& Register,FViewport* V,FSceneInterface* S,const FResolutionControls& R):FSceneViewExtensionBase(Register),Viewport(V),Scene(S),Resolution(R) {}
    void Arm(const TSharedRef<FJsonObject>& F,const FString& Path) { Frame=F; File=Path; Observations=0; Frame->SetNumberField(TEXT("final_view_observations"),0); }
    void Disarm() { Frame.Reset(); File.Reset(); }
    void BeginRenderViewFamily(FSceneViewFamily& Family) override
    {
        if (!Frame.IsValid()||Family.Scene!=Scene||Family.RenderTarget!=Viewport||!FScreenshotRequest::IsScreenshotRequested()||
            FPaths::ConvertRelativePathToFull(FScreenshotRequest::GetFilename())!=File) return;
        for (const FSceneView* View:Family.Views)
        {
            if (!View||!View->bIsGameView||View->bIsSceneCapture||View->bIsReflectionCapture||!View->IsPrimarySceneView()) continue;
            Frame->SetNumberField(TEXT("final_view_observations"),++Observations);
            Frame->SetNumberField(TEXT("final_view_frame"),double(Family.FrameCounter));
            auto ResolutionState=Resolution.Read(); const auto* Driver=Family.GetScreenPercentageInterface();
            // Public upper bound, not a GPU measurement. With dynamic resolution
            // disabled UE's legacy driver uses this same static primary fraction.
            ResolutionState->SetNumberField(TEXT("primary_fraction_upper_bound"),Driver?Driver->GetResolutionFractionsUpperBound()[GDynamicPrimaryResolutionFraction]:-1);
            ResolutionState->SetNumberField(TEXT("secondary_fraction"),Family.SecondaryViewFraction);
            ResolutionState->SetNumberField(TEXT("view_primary_fraction_override"),View->SceneViewInitOptions.OverridePrimaryResolutionFraction);
            ResolutionState->SetBoolField(TEXT("screen_percentage_show_flag"),Family.EngineShowFlags.ScreenPercentage);
            const auto& Rect=View->UnscaledViewRect;
            ResolutionState->SetArrayField(TEXT("unscaled_view_rect"),{MakeShared<FJsonValueNumber>(Rect.Min.X),MakeShared<FJsonValueNumber>(Rect.Min.Y),
                MakeShared<FJsonValueNumber>(Rect.Width()),MakeShared<FJsonValueNumber>(Rect.Height())});
            Frame->SetObjectField(TEXT("final_resolution"),ResolutionState);
            auto O=MakeShared<FJsonObject>(); const auto& P=View->FinalPostProcessSettings;
#define PROBE_SETTING(Name) O->SetNumberField(TEXT(#Name),P.Name)
            PROBE_SETTING(AutoExposureMethod); PROBE_SETTING(AutoExposureApplyPhysicalCameraExposure); PROBE_SETTING(AutoExposureBias);
            PROBE_SETTING(CameraISO); PROBE_SETTING(CameraShutterSpeed); PROBE_SETTING(DepthOfFieldFstop);
            PROBE_SETTING(DynamicGlobalIlluminationMethod); PROBE_SETTING(ReflectionMethod); PROBE_SETTING(ScreenSpaceReflectionIntensity);
            PROBE_SETTING(BloomIntensity); PROBE_SETTING(LensFlareIntensity); PROBE_SETTING(VignetteIntensity); PROBE_SETTING(AmbientOcclusionIntensity);
            PROBE_SETTING(WhiteTemp); PROBE_SETTING(WhiteTint);
#undef PROBE_SETTING
            O->SetArrayField(TEXT("ColorSaturation"),Color(P.ColorSaturation)); O->SetArrayField(TEXT("ColorContrast"),Color(P.ColorContrast));
            O->SetArrayField(TEXT("ColorGamma"),Color(P.ColorGamma)); O->SetArrayField(TEXT("ColorGain"),Color(P.ColorGain)); O->SetArrayField(TEXT("ColorOffset"),Color(P.ColorOffset));
            Frame->SetObjectField(TEXT("final_post_process"),O); auto Flags=MakeShared<FJsonObject>();
#define PROBE_FLAG(Name) Flags->SetBoolField(TEXT(#Name),Family.EngineShowFlags.Name)
            PROBE_FLAG(DirectionalLights); PROBE_FLAG(Fog); PROBE_FLAG(Atmosphere); PROBE_FLAG(SkyLighting); PROBE_FLAG(GlobalIllumination);
            PROBE_FLAG(LumenGlobalIllumination); PROBE_FLAG(ReflectionEnvironment); PROBE_FLAG(ScreenSpaceReflections); PROBE_FLAG(LumenReflections);
#undef PROBE_FLAG
            Frame->SetObjectField(TEXT("final_show_flags"),Flags);
        }
    }
};
struct FCVar
{
    IConsoleVariable* Var=nullptr; FString Value; EConsoleVariableFlags Flags=ECVF_Default;
    bool Save(const TCHAR* Name) { Var=IConsoleManager::Get().FindConsoleVariable(Name); if (!Var) return false; Value=Var->GetString(); Flags=Var->GetFlags(); return true; }
    void Set(const TCHAR* V) const { Var->Set(V,static_cast<EConsoleVariableFlags>(Flags&ECVF_SetByMask)); }
    bool Restore() const { if (!Var) return true; Set(*Value); Var->SetFlags(Flags); return Var->GetString()==Value&&Var->GetFlags()==Flags; }
};
class FRun final:public IAutomationLatentCommand
{
public:
    FRun(FAutomationTestBase& T,bool S):Test(T),SM6(S) {}
    ~FRun() { Cleanup(); }
    bool Update() override
    {
        if (!Started) { Started=true; Begin(); }
        if (Failed||Step==Count()) { Cleanup(); return true; }
        if (FPlatformTime::Seconds()-Start>360) { Fail(TEXT("Timber probe capture exceeded 360 seconds")); Cleanup(); return true; }
        if (!M.IsValid()||!Camera.IsValid()||!PC()||!M->GetWorld()->IsPaused()) { Fail(TEXT("Lost paused fixture/camera")); return false; }
        if (!Waiting&&FPlatformTime::Seconds()-Changed>=3) Capture();
        return false;
    }
private:
    FAutomationTestBase& Test; bool SM6=false,Started=false,Failed=false,Cleaned=false,BackedUp=false,Waiting=false,Eligible=false;
    int32 Step=0,OldViewMode=0; double Start=0,Changed=0;
    TWeakObjectPtr<ASoraGameMode> M; TWeakObjectPtr<ACameraActor> Camera;
    TWeakObjectPtr<AActor> OldTarget; TWeakObjectPtr<AHUD> HUD;
    TArray<TWeakObjectPtr<AActor>> Owned; TArray<TWeakObjectPtr<AStaticMeshActor>> Fixtures;
    bool ShowHUD=true,WasPaused=false; SoraUI::EScreen OldScreen=SoraUI::EScreen::Title;
    FEngineShowFlags OldFlags{ESFIM_Game}; FName OldNaniteMode;
    FString Folder,Pending,Platform,Slots[3]; TArray<uint8> Profiles[3]; bool Existed[3]={};
    FCVar Visualize,Composite,Edges,Shading,ScreenPercentage; FDelegateHandle Screenshot;
    FResolutionControls Resolution;
    SoraCaptureReadiness::FGate Readiness;
    TSharedPtr<FJsonObject> FirstReadiness,LastReadiness,FirstReadyReadiness,LastRejectedReadiness;
    TSharedPtr<FJsonObject> OriginalResolution;
    TSharedPtr<FViewObservation,ESPMode::ThreadSafe> ViewObservation;
    FVector2D Size=FVector2D::ZeroVector; FVector CameraAt; FRotator CameraRotation;
    TArray<TSharedPtr<FJsonValue>> Meshes,Frames,Packages,Inputs;
    TMap<FString,FString> PackageHashes;
    int32 PerMesh() const { return SM6?4:2; }
    int32 Count() const { return 9*PerMesh(); }
    int32 Index() const { return Step/PerMesh(); }
    int32 Mode() const { return SM6?Step%4:0; }
    bool Detail() const { return Step%PerMesh()==PerMesh()-1; }
    APlayerController* PC() const { return M.IsValid()?UGameplayStatics::GetPlayerController(M.Get(),0):nullptr; }
    UGameViewportClient* Viewport() const { return M.IsValid()?M->GetWorld()->GetGameViewport():nullptr; }
    void Fail(const TCHAR* Text) { if (!Failed) Test.AddError(Text); Failed=true; }
    FString CVar(const TCHAR* N) const { const auto* V=IConsoleManager::Get().FindConsoleVariable(N); return V?V->GetString():TEXT("absent"); }
    TSharedRef<FJsonObject> State() const
    {
        auto O=MakeShared<FJsonObject>();
        for (const TCHAR* N:{TEXT("r.Nanite"),TEXT("r.Nanite.ProxyRenderMode"),TEXT("r.Nanite.Visualize"),TEXT("r.Nanite.Visualize.Composite"),
            TEXT("r.Nanite.Visualize.EdgeDetect"),TEXT("r.Nanite.Visualize.DebugShading"),TEXT("r.ScreenPercentage"),TEXT("r.AntiAliasingMethod")}) O->SetStringField(N,CVar(N));
        return O;
    }
    void Begin()
    {
        Start=FPlatformTime::Seconds();
        for (const auto& C:GEngine->GetWorldContexts()) if (C.WorldType==EWorldType::Game&&C.World()) M=Cast<ASoraGameMode>(C.World()->GetAuthGameMode());
        if (!M.IsValid()||!PC()||!PC()->PlayerCameraManager||!Viewport()||!M->GetWorld()->Scene||!M->FrontEnd()||GUsingNullRHI||
            !GDynamicRHI||FString(GDynamicRHI->GetName())!=TEXT("Metal")) { Fail(TEXT("Timber probe requires a real Metal editor-game scene")); return; }
        OldScreen=M->FrontEnd()->Screen();
        if (!M->bMenu||!M->GetWorld()->IsPaused()||OldScreen!=SoraUI::EScreen::Title)
        { Fail(TEXT("Start probe in a disposable paused Title session")); return; }
        const EShaderPlatform P=M->GetWorld()->Scene->GetShaderPlatform();
        if (!FDataDrivenShaderPlatformInfo::IsValid(P)) { Fail(TEXT("Invalid actual shader platform")); return; }
        Platform=FDataDrivenShaderPlatformInfo::GetName(P).ToString(); Eligible=SoraPresentation::UsesNaniteEnvironment(M->GetWorld());
        if ((SM6&&(Platform!=TEXT("METAL_SM6")||!Eligible))||(!SM6&&(Platform!=TEXT("METAL_SM5")||Eligible)))
        { Fail(TEXT("Actual Metal scene does not match separately requested SM6/SM5 test")); return; }
        Viewport()->GetViewportSize(Size);
        if (Size!=FVector2D(1280,720)&&Size!=FVector2D(1920,1080)) { Fail(TEXT("Probe requires 1280x720 or 1920x1080")); return; }
        Slots[0]=M->SaveSlotName; Slots[1]=M->ControlSlotName; Slots[2]=M->SettingsSlotName;
        for (int I=0;I<3;++I)
        {
            Existed[I]=UGameplayStatics::DoesSaveGameExist(Slots[I],0);
            if (Existed[I]&&!UGameplayStatics::LoadDataFromSlot(Profiles[I],Slots[I],0)) { Fail(TEXT("Could not preserve profile bytes")); return; }
        }
        WasPaused=M->GetWorld()->IsPaused(); OldTarget=PC()->GetViewTarget(); HUD=PC()->GetHUD(); if (HUD.IsValid()) ShowHUD=HUD->bShowHUD;
        OldViewMode=Viewport()->ViewModeIndex; OldFlags=Viewport()->EngineShowFlags; OldNaniteMode=Viewport()->GetCurrentNaniteVisualizationMode(); BackedUp=true;
        GetNaniteVisualizationData();
        if (!Visualize.Save(TEXT("r.Nanite.Visualize"))||!Composite.Save(TEXT("r.Nanite.Visualize.Composite"))||!Edges.Save(TEXT("r.Nanite.Visualize.EdgeDetect"))||!Shading.Save(TEXT("r.Nanite.Visualize.DebugShading"))||!ScreenPercentage.Save(TEXT("r.ScreenPercentage")))
        { Fail(TEXT("Missing visualization or resolution controls")); return; }
        OriginalResolution=Resolution.Read(); ScreenPercentage.Set(TEXT("100"));
        if (ScreenPercentage.Var->GetFloat()!=100.f) { Fail(TEXT("Could not establish 100 percent probe screen percentage")); return; }
        Folder=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Screenshots/SoraTimberProbe")/FGuid::NewGuid().ToString(EGuidFormats::Digits));
        IFileManager::Get().MakeDirectory(*Folder,true);
        InventoryFiles(); if (Failed) return;
        // Hide only the front end. bMenu and pause stay set throughout: no
        // campaign checkpoint, game clock, input mode or production actor changes.
        M->FrontEnd()->Hide(); if (HUD.IsValid()) HUD->bShowHUD=false;
        Camera=M->GetWorld()->SpawnActor<ACameraActor>(); if (!Camera.IsValid()) { Fail(TEXT("Could not spawn fixture camera")); return; }
        Owned.Add(Camera.Get()); auto* Cam=Camera->GetCameraComponent(); Cam->SetFieldOfView(35.f); Cam->PostProcessBlendWeight=1.f;
        auto& PP=Cam->PostProcessSettings;
        PP.bOverride_AutoExposureMethod=true; PP.AutoExposureMethod=AEM_Manual;
        PP.bOverride_AutoExposureApplyPhysicalCameraExposure=true; PP.AutoExposureApplyPhysicalCameraExposure=true;
        PP.bOverride_CameraISO=true; PP.CameraISO=100;
        PP.bOverride_CameraShutterSpeed=true; PP.CameraShutterSpeed=60;
        PP.bOverride_DepthOfFieldFstop=true; PP.DepthOfFieldFstop=2.8f;
        PP.bOverride_AutoExposureBias=true; PP.AutoExposureBias=0;
        PP.bOverride_DepthOfFieldScale=true; PP.DepthOfFieldScale=0;
        // A remote location alone does not exclude the production directional
        // sun, unbound grade, GI or reflection environment. Override the owned
        // camera and viewport, then verify their final screenshot-view values.
        PP.bOverride_DynamicGlobalIlluminationMethod=true; PP.DynamicGlobalIlluminationMethod=EDynamicGlobalIlluminationMethod::None;
        PP.bOverride_ReflectionMethod=true; PP.ReflectionMethod=EReflectionMethod::None;
        PP.bOverride_ScreenSpaceReflectionIntensity=true; PP.ScreenSpaceReflectionIntensity=0;
        PP.bOverride_BloomIntensity=true; PP.BloomIntensity=0;
        PP.bOverride_LensFlareIntensity=true; PP.LensFlareIntensity=0;
        PP.bOverride_VignetteIntensity=true; PP.VignetteIntensity=0;
        PP.bOverride_AmbientOcclusionIntensity=true; PP.AmbientOcclusionIntensity=0;
        PP.bOverride_ColorSaturation=true; PP.ColorSaturation=FVector4(1,1,1,1);
        PP.bOverride_ColorContrast=true; PP.ColorContrast=FVector4(1,1,1,1);
        PP.bOverride_ColorGamma=true; PP.ColorGamma=FVector4(1,1,1,1);
        PP.bOverride_ColorGain=true; PP.ColorGain=FVector4(1,1,1,1);
        PP.bOverride_ColorOffset=true; PP.ColorOffset=FVector4(0,0,0,0);
        PP.bOverride_WhiteTemp=true; PP.WhiteTemp=6500;
        PP.bOverride_WhiteTint=true; PP.WhiteTint=0;
        PC()->SetViewTarget(Camera.Get());
        ViewObservation=FSceneViewExtensions::NewExtension<FViewObservation>(Viewport()->Viewport,M->GetWorld()->Scene,Resolution);
        for (int I=0;I<2;++I)
        {
            auto* L=M->GetWorld()->SpawnActor<APointLight>(); if (!L) { Fail(TEXT("Could not spawn fixture light")); return; } Owned.Add(L);
            L->GetLightComponent()->SetMobility(EComponentMobility::Movable);
            L->SetActorLocation(Origin+(I?FVector(-400,-200,100):FVector(350,-350,550)));
            auto* Light=CastChecked<UPointLightComponent>(L->GetLightComponent());
            Light->SetIntensityUnits(ELightUnits::Lumens); Light->SetIntensity(I?5000000.f:20000000.f); Light->SetAttenuationRadius(5000.f);
            Light->SetSourceRadius(100.f); Light->SetLightColor(I?FLinearColor(.72f,.82f,1.f):FLinearColor(1.f,.86f,.68f));
        }
        for (int I=0;I<9;++I)
        {
            const FString Path=FString(Root)+Names[I]+TEXT(".")+Names[I]; auto* Mesh=LoadObject<UStaticMesh>(nullptr,*Path);
            if (!Mesh) { Fail(TEXT("Reviewed saved probe mesh is absent")); return; }
            auto* A=M->GetWorld()->SpawnActor<AStaticMeshActor>(); if (!A) { Fail(TEXT("Could not spawn probe mesh")); return; }
            Owned.Add(A); Fixtures.Add(A); auto* C=A->GetStaticMeshComponent(); C->SetMobility(EComponentMobility::Movable);
            C->SetCollisionEnabled(ECollisionEnabled::NoCollision); C->SetStaticMesh(Mesh); A->SetActorHiddenInGame(true);
            const auto B=Mesh->GetBounds(); const FVector E=B.BoxExtent;
            const FVector Axis=E.X>=E.Y&&E.X>=E.Z?FVector::ForwardVector:E.Y>=E.Z?FVector::RightVector:FVector::UpVector;
            const FQuat Rotation=FQuat::FindBetweenNormals(Axis,FVector::UpVector); const double Scale=250./E.GetMax();
            if (!FMath::IsFinite(Scale)||Scale<=0) { Fail(TEXT("Invalid mesh bounds")); return; }
            A->SetActorTransform(FTransform(Rotation,Origin-Rotation.RotateVector(B.Origin*Scale),FVector(Scale)));
        }
        FAssetCompilingManager::Get().FinishAllCompilation(); if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
        for (int I=0;I<9;++I) Observe(I);
        if (Failed) return;
        Screenshot=FScreenshotRequest::OnScreenshotRequestProcessed().AddRaw(this,&FRun::Captured); Switch();
    }
    void InventoryFiles()
    {
        const FString Directory=FPaths::ConvertRelativePathToFull(FPaths::ProjectContentDir()/TEXT("Generated/Qualification/DojoTimberProbe"));
        TArray<FString> Files; IFileManager::Get().FindFilesRecursive(Files,*Directory,TEXT("*"),true,false); Files.Sort(); int Assets=0;
        for (const FString& File:Files)
        {
            const FString Ext=FPaths::GetExtension(File); if (Ext!=TEXT("uasset")&&Ext!=TEXT("uexp")&&Ext!=TEXT("ubulk")) continue;
            Assets+=Ext==TEXT("uasset"); const FString Hash=LexToString(FMD5Hash::HashFile(*File)); PackageHashes.Add(File,Hash);
            auto O=MakeShared<FJsonObject>(); O->SetStringField(TEXT("path"),File); O->SetNumberField(TEXT("bytes"),double(IFileManager::Get().FileSize(*File))); O->SetStringField(TEXT("md5"),Hash); Packages.Add(MakeShared<FJsonValueObject>(O));
        }
        if (Assets!=31) { Fail(TEXT("Probe must contain exactly the reviewed 31 saved packages")); return; }
        for (const TCHAR* Relative:{TEXT("Source/SoraArena/Private/SoraTimberProbeCapture.cpp"),TEXT("Source/SoraArena/Private/World/SoraCaptureReadiness.h"),TEXT("scripts/unreal/import_nyaagyu_dojo_timbers.py"),TEXT("scripts/unreal/dojo_timber_admission.py"),TEXT("scripts/unreal/dojo_nanite.py")})
        {
            const FString File=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/Relative); auto O=MakeShared<FJsonObject>();
            if (IFileManager::Get().FileSize(*File)<=0) { Fail(TEXT("Missing capture/importer provenance input")); return; }
            O->SetStringField(TEXT("path"),Relative); O->SetNumberField(TEXT("bytes"),double(IFileManager::Get().FileSize(*File)));
            O->SetStringField(TEXT("md5"),LexToString(FMD5Hash::HashFile(*File))); Inputs.Add(MakeShared<FJsonValueObject>(O));
        }
    }
    void Observe(int I)
    {
        auto* C=Fixtures[I]->GetStaticMeshComponent(); auto* Mesh=C->GetStaticMesh().Get(); auto O=MakeShared<FJsonObject>();
        O->SetStringField(TEXT("name"),Names[I]); O->SetStringField(TEXT("mesh"),Mesh->GetPathName());
        O->SetStringField(TEXT("kind"),I<5?TEXT("dense_nanite_source"):TEXT("authored_conventional_pool"));
        O->SetStringField(TEXT("sm5_interpretation"),I<5?TEXT("generated_dense_asset_fallback; not authored M1 pool"):TEXT("authored conventional pool; not M1 hardware qualification"));
        O->SetStringField(TEXT("component"),C->GetPathName()); O->SetBoolField(TEXT("has_nanite_data"),Mesh->HasValidNaniteData());
        if (Mesh->HasValidNaniteData()) O->SetBoolField(TEXT("has_platform_fallback"),Mesh->HasNaniteFallbackMesh(M->GetWorld()->Scene->GetShaderPlatform()));
        O->SetBoolField(TEXT("authoring_nanite_enabled"),Mesh->IsNaniteEnabled());
        O->SetBoolField(TEXT("disallow_nanite"),C->IsDisallowNanite()); O->SetBoolField(TEXT("force_disable_nanite"),C->IsForceDisableNanite());
        const auto* R=Mesh->GetRenderData();
        O->SetNumberField(TEXT("nanite_input_triangles"),R&&R->NaniteResourcesPtr.IsValid()?R->NaniteResourcesPtr->NumInputTriangles:0);
        O->SetNumberField(TEXT("nanite_input_vertices"),R&&R->NaniteResourcesPtr.IsValid()?R->NaniteResourcesPtr->NumInputVertices:0);
        O->SetNumberField(TEXT("lod0_render_triangles"),R&&R->LODResources.Num()?R->LODResources[0].GetNumTriangles():0);
        O->SetStringField(TEXT("resource_scope"),TEXT("CPU source/resource counts; not visible draw or GPU triangle counts"));
        const auto Bounds=C->CalcBounds(C->GetComponentTransform()); O->SetArrayField(TEXT("bounds_origin"),Vec(Bounds.Origin)); O->SetArrayField(TEXT("bounds_extent"),Vec(Bounds.BoxExtent));
        O->SetArrayField(TEXT("fixture_scale"),Vec(C->GetComponentScale()));
        TArray<TSharedPtr<FJsonValue>> Materials;
        for (int J=0;J<C->GetNumMaterials();++J)
        {
            auto P=MakeShared<FJsonObject>(); auto* Mat=C->GetMaterial(J); const auto* MI=Cast<UMaterialInstance>(Mat);
            P->SetStringField(TEXT("material"),GetPathNameSafe(Mat)); P->SetStringField(TEXT("parent"),MI?GetPathNameSafe(MI->Parent):TEXT("none"));
            if (!Mat||!MI) { Fail(TEXT("Saved probe material instance missing")); return; }
            auto Textures=MakeShared<FJsonObject>(); auto Scalars=MakeShared<FJsonObject>(); TArray<FMaterialParameterInfo> Infos; TArray<FGuid> Ids;
            Mat->GetAllTextureParameterInfo(Infos,Ids);
            for (const auto& Info:Infos) { UTexture* T=nullptr; if (Mat->GetTextureParameterValue(Info,T)) Textures->SetStringField(Info.Name.ToString(),GetPathNameSafe(T)); }
            Infos.Reset(); Ids.Reset(); Mat->GetAllScalarParameterInfo(Infos,Ids);
            for (const auto& Info:Infos) { float V=0; if (Mat->GetScalarParameterValue(Info,V)) Scalars->SetNumberField(Info.Name.ToString(),V); }
            TArray<UTexture*> Used; Mat->GetUsedTextures(Used);
            TArray<TSharedPtr<FJsonValue>> UsedPaths; for (const auto* T:Used) UsedPaths.Add(MakeShared<FJsonValueString>(GetPathNameSafe(T)));
            P->SetArrayField(TEXT("used_textures"),UsedPaths);
            P->SetObjectField(TEXT("textures"),Textures); P->SetObjectField(TEXT("scalars"),Scalars); Materials.Add(MakeShared<FJsonValueObject>(P));
        }
        O->SetArrayField(TEXT("materials"),Materials);
        const FMeshDescription* D=Mesh->GetNumSourceModels()>0&&Mesh->IsMeshDescriptionValid(0)?Mesh->GetMeshDescription(0):nullptr;
        if (!D||D->VertexInstances().Num()>3000000) { Fail(TEXT("Source mesh UV observations absent or exceed bounded 3M vertex instances")); return; }
        const auto UVs=FStaticMeshConstAttributes(*D).GetVertexInstanceUVs();
        if (!UVs.IsValid()||UVs.GetNumChannels()<4) { Fail(TEXT("Saved source mesh lacks UV2/UV3")); return; }
        O->SetNumberField(TEXT("source_triangles"),D->Triangles().Num()); O->SetNumberField(TEXT("uv_channels"),UVs.GetNumChannels());
        TArray<TSharedPtr<FJsonValue>> Channels;
        for (int Channel=2;Channel<=3;++Channel)
        {
            FVector2f Min(FLT_MAX,FLT_MAX),Max(-FLT_MAX,-FLT_MAX); int32 N=0; TArray<TSharedPtr<FJsonValue>> Samples;
            const int32 Stride=FMath::Max(1,D->VertexInstances().Num()/8);
            for (const FVertexInstanceID Id:D->VertexInstances().GetElementIDs())
            {
                const FVector2f V=UVs.Get(Id,Channel); if (!FMath::IsFinite(V.X)||!FMath::IsFinite(V.Y)) { Fail(TEXT("Nonfinite saved UV")); return; }
                Min.X=FMath::Min(Min.X,V.X); Min.Y=FMath::Min(Min.Y,V.Y); Max.X=FMath::Max(Max.X,V.X); Max.Y=FMath::Max(Max.Y,V.Y);
                if (N%Stride==0&&Samples.Num()<8) { auto S=MakeShared<FJsonObject>(); S->SetNumberField(TEXT("vertex_instance"),Id.GetValue()); S->SetArrayField(TEXT("uv"),UV(V)); Samples.Add(MakeShared<FJsonValueObject>(S)); } ++N;
            }
            auto U=MakeShared<FJsonObject>(); U->SetNumberField(TEXT("channel"),Channel); U->SetNumberField(TEXT("scanned_vertex_instances"),N);
            U->SetArrayField(TEXT("min"),UV(Min)); U->SetArrayField(TEXT("max"),UV(Max)); U->SetArrayField(TEXT("samples"),Samples); Channels.Add(MakeShared<FJsonValueObject>(U));
        }
        O->SetStringField(TEXT("uv_scope"),TEXT("saved LOD0 MeshDescription UV2/UV3, no unflip or shader correction; complete min/max and at most eight samples/channel"));
        O->SetArrayField(TEXT("uv_observations"),Channels); Meshes.Add(MakeShared<FJsonValueObject>(O));
    }
    void Switch()
    {
        for (int I=0;I<Fixtures.Num();++I) Fixtures[I]->SetActorHiddenInGame(I!=Index());
        const auto B=Fixtures[Index()]->GetStaticMeshComponent()->CalcBounds(Fixtures[Index()]->GetActorTransform());
        const double HalfVertical=FMath::Atan(FMath::Tan(FMath::DegreesToRadians(17.5))*Size.Y/Size.X);
        const FVector Aim=Detail()?Origin+FVector(0,0,225):Origin;
        const double Radius=Detail()?FMath::Max(35.,FMath::Max(B.BoxExtent.X,B.BoxExtent.Y)*1.5):B.SphereRadius;
        const double Distance=1.15*Radius/FMath::Sin(HalfVertical);
        CameraAt=Aim+FVector(1,-2,.7).GetSafeNormal()*Distance; CameraRotation=(Aim-CameraAt).Rotation();
        Camera->SetActorLocationAndRotation(CameraAt,CameraRotation); PC()->PlayerCameraManager->UpdateCamera(0.f);
        Viewport()->SetViewMode(VMI_Lit); Viewport()->SetCurrentNaniteVisualizationMode(NAME_None);
        // Fixture-only viewport state; production components/lights remain untouched.
        Viewport()->EngineShowFlags.SetFog(false); Viewport()->EngineShowFlags.SetAtmosphere(false); Viewport()->EngineShowFlags.SetSkyLighting(false);
        Viewport()->EngineShowFlags.SetDirectionalLights(false); Viewport()->EngineShowFlags.SetGlobalIllumination(false);
        Viewport()->EngineShowFlags.SetLumenGlobalIllumination(false); Viewport()->EngineShowFlags.SetReflectionEnvironment(false);
        Viewport()->EngineShowFlags.SetScreenSpaceReflections(false); Viewport()->EngineShowFlags.SetLumenReflections(false);
        const bool Diagnostic=SM6&&(Mode()==1||Mode()==2);
        Visualize.Set(Diagnostic?Modes[Mode()]:TEXT("off")); Composite.Set(TEXT("1")); Edges.Set(TEXT("0")); Shading.Set(TEXT("0"));
        Viewport()->EngineShowFlags.SetVisualizeNanite(Diagnostic); Changed=FPlatformTime::Seconds();
        Readiness={}; Readiness.Started=Changed; FirstReadiness.Reset(); LastReadiness.Reset(); FirstReadyReadiness.Reset(); LastRejectedReadiness.Reset();
    }
    struct FShader
    {
        bool Proxy=false,Fallback=false,Default=false,Valid=false,Complete=false; FString Asset;
        bool Ready() const { return Proxy&&!Fallback&&!Default&&Valid&&Complete&&!Asset.IsEmpty(); }
    };
    FShader ObserveShader() const
    {
        FShader Shader;
        const auto* Material=Fixtures[Index()]->GetStaticMeshComponent()->GetMaterial(0);
        const FMaterialRenderProxy* Proxy=Material?Material->GetRenderProxy():nullptr;
        const ERHIFeatureLevel::Type Feature=M->GetWorld()->GetFeatureLevel();
        ENQUEUE_RENDER_COMMAND(SoraProbeMaterialObservation)([Proxy,Feature,&Shader](FRHICommandListImmediate&)
        {
            Shader.Proxy=Proxy!=nullptr; if (!Proxy) return;
            // UE5.8 assigns the out pointer only on fallback; successful
            // resolution leaves it unchanged (MaterialRenderProxy.cpp).
            const FMaterialRenderProxy* ResolvedProxy=Proxy; const FMaterial& Resolved=Proxy->GetMaterialWithFallback(Feature,ResolvedProxy);
            Shader.Fallback=ResolvedProxy!=Proxy; Shader.Default=Resolved.IsDefaultMaterial(); Shader.Asset=Resolved.GetAssetName();
            const auto* Map=Resolved.GetRenderingThreadShaderMap(); Shader.Valid=Map&&Map->IsValidForRendering(); Shader.Complete=Resolved.IsRenderingThreadShaderMapComplete();
        });
        FlushRenderingCommands(); return Shader;
    }
    TSharedRef<FJsonObject> ShaderJson(const FShader& Shader,const TCHAR* Stage) const
    {
        auto ShaderJson=MakeShared<FJsonObject>();
        ShaderJson->SetBoolField(TEXT("proxy_present"),Shader.Proxy); ShaderJson->SetBoolField(TEXT("used_fallback_proxy"),Shader.Fallback);
        ShaderJson->SetBoolField(TEXT("default_material"),Shader.Default); ShaderJson->SetBoolField(TEXT("shader_map_valid"),Shader.Valid);
        ShaderJson->SetBoolField(TEXT("shader_map_complete"),Shader.Complete); ShaderJson->SetStringField(TEXT("resource_asset"),Shader.Asset);
        ShaderJson->SetStringField(TEXT("scope"),TEXT("CPU render-thread base proxy observation bracketing the screenshot view; not GPU shader identity, a draw count or visualization override identity"));
        ShaderJson->SetStringField(TEXT("observation_stage"),Stage);
        ShaderJson->SetNumberField(TEXT("observation_frame"),double(GFrameCounter));
        return ShaderJson;
    }
    TSharedRef<FJsonObject> ReadinessJson() const
    {
        auto O=MakeShared<FJsonObject>(); O->SetNumberField(TEXT("polls"),Readiness.Polls); O->SetNumberField(TEXT("rejected"),Readiness.Rejected);
        O->SetNumberField(TEXT("first_ready_frame"),double(Readiness.FirstReadyFrame)); O->SetNumberField(TEXT("deadline_seconds"),SoraCaptureReadiness::FGate::DeadlineSeconds);
        O->SetNumberField(TEXT("elapsed_seconds"),FPlatformTime::Seconds()-Changed);
        if (FirstReadiness.IsValid()) O->SetObjectField(TEXT("first_observation"),FirstReadiness);
        if (LastReadiness.IsValid()) O->SetObjectField(TEXT("last_observation"),LastReadiness);
        if (FirstReadyReadiness.IsValid()) O->SetObjectField(TEXT("first_ready_observation"),FirstReadyReadiness);
        if (LastRejectedReadiness.IsValid()) O->SetObjectField(TEXT("last_rejected_observation"),LastRejectedReadiness);
        O->SetStringField(TEXT("scope"),TEXT("two consecutive distinct-frame ready proxy observations after visibility; time-sliced completion processing; not rendered-pixel proof"));
        return O;
    }
    void Capture()
    {
        // Visibility can schedule shader work after Begin's initial compile.
        // Do not block on FinishAllCompilation in this polling path.
        if (FPlatformTime::Seconds()-Changed>=SoraCaptureReadiness::FGate::DeadlineSeconds)
        { Fail(TEXT("Visible timber material was not ready within 30 seconds; pending readiness observations retained")); return; }
        if (Readiness.HasFrame&&GFrameCounter<=Readiness.LastFrame) return;
        // UE5.8's registered shader manager forwards this to
        // ProcessAsyncResults(true,false): time sliced, no global-shader wait.
        FAssetCompilingManager::Get().ProcessAsyncTasks(true);
        const FShader Shader=ObserveShader();
        const auto Observation=ShaderJson(Shader,TEXT("visible_readiness_poll"));
        LastReadiness=Observation; if (!FirstReadiness.IsValid()) FirstReadiness=Observation;
        const bool Ready=Shader.Ready()&&Shader.Asset==(Index()<5?TEXT("M_SoraTimberNanite"):TEXT("M_SoraTimber"));
        if (!Ready) { LastRejectedReadiness=Observation; FirstReadyReadiness.Reset(); }
        else if (!Readiness.HasReady) FirstReadyReadiness=Observation;
        const auto Admission=Readiness.Observe(FPlatformTime::Seconds(),GFrameCounter,Ready);
        if (Admission==SoraCaptureReadiness::EResult::TimedOut)
        { Fail(TEXT("Visible timber material readiness deadline expired; observations retained")); return; }
        if (Admission!=SoraCaptureReadiness::EResult::Capture) return;
        const auto ResolutionState=Resolution.Read(); const FString Dynamic=ResolutionState->GetStringField(TEXT("dynamic_resolution_status"));
        if (ResolutionState->GetNumberField(TEXT("screen_percentage"))!=100||
            (ScreenPercentage.Var->GetFlags()&ECVF_SetByMask)!=(ScreenPercentage.Flags&ECVF_SetByMask)||
            (Dynamic!=TEXT("Disabled")&&Dynamic!=TEXT("Unsupported"))||
            (ResolutionState->GetBoolField(TEXT("test_interface_override_registered"))&&ResolutionState->GetNumberField(TEXT("test_interface_override"))!=0))
        {
            FString Observed; FJsonSerializer::Serialize(ResolutionState,TJsonWriterFactory<>::Create(&Observed));
            Fail(*(TEXT("Probe requires unchanged 100 percent control and inactive dynamic/test resolution overrides: ")+Observed)); return;
        }
        FlushRenderingCommands(); const auto& Data=GetNaniteVisualizationData(); const bool Diagnostic=SM6&&(Mode()==1||Mode()==2);
        if ((Diagnostic&&(!Data.IsActive()||Data.GetActiveModeName()!=FName(Modes[Mode()])))||(!Diagnostic&&Data.IsActive())) { Fail(TEXT("Renderer has not selected requested visualization")); return; }
        if (!PC()->PlayerCameraManager->GetCameraLocation().Equals(CameraAt,.01)||!PC()->PlayerCameraManager->GetCameraRotation().Equals(CameraRotation,.001)||PC()->GetViewTarget()!=Camera.Get()) { Fail(TEXT("Actual probe camera mismatch")); return; }
        int Visible=0; for (const auto& A:Fixtures) Visible+=A.IsValid()&&!A->IsHidden();
        if (Visible!=1||Fixtures[Index()]->IsHidden()) { Fail(TEXT("Probe requires exactly one visible owned mesh")); return; }
        auto F=MakeShared<FJsonObject>(); const FString View=Detail()?TEXT("detail"):TEXT("full"); const FString Name=FString(Names[Index()])+TEXT("-")+View+TEXT("-")+Modes[Mode()];
        F->SetStringField(TEXT("name"),Name); F->SetStringField(TEXT("mesh_name"),Names[Index()]); F->SetStringField(TEXT("view"),View); F->SetStringField(TEXT("mode"),Modes[Mode()]);
        F->SetArrayField(TEXT("camera"),Vec(CameraAt)); F->SetArrayField(TEXT("rotation"),Vec(FVector(CameraRotation.Pitch,CameraRotation.Yaw,CameraRotation.Roll)));
        F->SetNumberField(TEXT("fov"),PC()->PlayerCameraManager->GetFOVAngle()); F->SetNumberField(TEXT("visible_fixture_meshes"),Visible);
        F->SetNumberField(TEXT("request_frame"),double(GFrameCounter)); F->SetNumberField(TEXT("settle_seconds"),FPlatformTime::Seconds()-Changed);
        F->SetBoolField(TEXT("paused"),M->GetWorld()->IsPaused()); F->SetBoolField(TEXT("hud_hidden"),!HUD.IsValid()||!HUD->bShowHUD);
        F->SetStringField(TEXT("active_visualization"),Data.GetActiveModeName().ToString()); F->SetNumberField(TEXT("active_mode_id"),Data.GetActiveModeID());
        F->SetBoolField(TEXT("show_visualize_nanite"),Viewport()->EngineShowFlags.VisualizeNanite); F->SetObjectField(TEXT("cvars"),State());
        F->SetObjectField(TEXT("material_pre_request_readback"),ShaderJson(Shader,TEXT("before_screenshot_request")));
        F->SetObjectField(TEXT("material_readiness"),ReadinessJson());
        Frames.Add(MakeShared<FJsonValueObject>(F)); Pending=Folder/(Name+TEXT(".png")); Waiting=true;
        ViewObservation->Arm(F,Pending); FScreenshotRequest::RequestScreenshot(Pending,false,false);
    }
    void Captured()
    {
        if (!Waiting) return;
        if (IFileManager::Get().FileSize(*Pending)<=0) { Fail(TEXT("Original probe screenshot missing")); return; }
        const auto Frame=Frames.Last()->AsObject();
        Frame->SetStringField(TEXT("file"),FPaths::GetCleanFilename(Pending)); Frame->SetNumberField(TEXT("screenshot_processed_frame"),double(GFrameCounter));
        // The pixels have been saved. Observe the same base proxy again after
        // that view, retaining both endpoints rather than assigning the old
        // pre-request observation to the next screenshot frame.
        const FShader FinalShader=ObserveShader();
        Frame->SetObjectField(TEXT("material_render_readback"),ShaderJson(FinalShader,TEXT("after_screenshot_processed")));
        if (ViewObservation.IsValid()) ViewObservation->Disarm();
        double ViewFrame=-1,ViewCount=0;
        const bool SameView=Frame->TryGetNumberField(TEXT("final_view_frame"),ViewFrame)&&Frame->TryGetNumberField(TEXT("final_view_observations"),ViewCount)&&
            ViewCount==1&&ViewFrame==double(GFrameCounter);
        // Acknowledgement means the original exists, not that it passed. Emit
        // before admission so failure archives retain this last saved image.
        UE_LOG(LogTemp,Display,TEXT("SORA_TIMBER_PROBE_FRAME %s"),*Pending);
        if (!SameView||!FinalShader.Ready()||FinalShader.Asset!=Frame->GetObjectField(TEXT("material_pre_request_readback"))->GetStringField(TEXT("resource_asset")))
        {
            Waiting=false; Fail(TEXT("Saved timber original has no matching final view or its final base proxy is unready/changed; original and both observations retained")); return;
        }
        Waiting=false; Pending.Reset(); ++Step; if (Step<Count()) Switch();
    }
    void Cleanup()
    {
        if (Cleaned) return; Cleaned=true; if (Waiting) FScreenshotRequest::Reset(); FScreenshotRequest::OnScreenshotRequestProcessed().Remove(Screenshot);
        if (ViewObservation.IsValid()) { ViewObservation->Disarm(); ViewObservation.Reset(); }
        bool Restored=true; for (const FCVar* C:{&Visualize,&Composite,&Edges,&Shading,&ScreenPercentage}) Restored=C->Restore()&&Restored;
        if (BackedUp&&!M.IsValid()) Restored=false;
        if (BackedUp&&M.IsValid())
        {
            if (PC()&&OldTarget.IsValid()) PC()->SetViewTarget(OldTarget.Get()); else Restored=false;
            if (HUD.IsValid()) HUD->bShowHUD=ShowHUD;
            if (OldScreen==SoraUI::EScreen::Title) M->FrontEnd()->ShowTitle(); else M->FrontEnd()->ShowMain();
            if (Viewport())
            {
                Viewport()->SetViewMode(static_cast<EViewModeIndex>(OldViewMode)); Viewport()->EngineShowFlags=OldFlags; Viewport()->SetCurrentNaniteVisualizationMode(OldNaniteMode);
#define PROBE_RESTORED(Name) Restored=(Viewport()->EngineShowFlags.Name==OldFlags.Name)&&Restored
                PROBE_RESTORED(DirectionalLights); PROBE_RESTORED(Fog); PROBE_RESTORED(Atmosphere); PROBE_RESTORED(SkyLighting); PROBE_RESTORED(GlobalIllumination);
                PROBE_RESTORED(LumenGlobalIllumination); PROBE_RESTORED(ReflectionEnvironment); PROBE_RESTORED(ScreenSpaceReflections); PROBE_RESTORED(LumenReflections);
#undef PROBE_RESTORED
            }
            else Restored=false;
            UGameplayStatics::SetGamePaused(M.Get(),WasPaused);
            Restored=Restored&&M->bMenu&&M->FrontEnd()->Screen()==OldScreen&&M->GetWorld()->IsPaused()==WasPaused&&PC()&&PC()->GetViewTarget()==OldTarget.Get()&&
                (!HUD.IsValid()||HUD->bShowHUD==ShowHUD)&&Viewport()&&Viewport()->ViewModeIndex==OldViewMode&&Viewport()->GetCurrentNaniteVisualizationMode()==OldNaniteMode&&
                Viewport()->EngineShowFlags.VisualizeNanite==OldFlags.VisualizeNanite&&M->SaveSlotName==Slots[0]&&M->ControlSlotName==Slots[1]&&M->SettingsSlotName==Slots[2];
            for (int I=0;I<3;++I)
            {
                TArray<uint8> Bytes; const bool Exists=UGameplayStatics::DoesSaveGameExist(Slots[I],0);
                // No gameplay/profile calls occur in this fixture. Detect any
                // unexpected mutation before restoring the exact original bytes.
                const bool Same=Exists==Existed[I]&&(!Exists||(UGameplayStatics::LoadDataFromSlot(Bytes,Slots[I],0)&&Bytes==Profiles[I]));
                Restored=Same&&Restored;
                if (!Same) { if (Existed[I]) UGameplayStatics::SaveDataToSlot(Profiles[I],Slots[I],0); else if (Exists) UGameplayStatics::DeleteGameInSlot(Slots[I],0); }
            }
        }
        for (auto& A:Owned) if (A.IsValid()) Restored=A->Destroy()&&Restored;
        bool Unchanged=true;
        for (const auto& P:PackageHashes) Unchanged=IFileManager::Get().FileSize(*P.Key)>0&&LexToString(FMD5Hash::HashFile(*P.Key))==P.Value&&Unchanged;
        Test.TestTrue(TEXT("Probe restores view/menu/HUD/profile/CVars and removes owned actors"),Restored); Test.TestTrue(TEXT("Saved probe package bytes remain unchanged"),Unchanged);
        if (Folder.IsEmpty()) return;
        auto O=MakeShared<FJsonObject>(); O->SetStringField(TEXT("schema"),TEXT("sora-arena.timber-probe.v3")); O->SetStringField(TEXT("scope"),Scope);
        O->SetBoolField(TEXT("sm6_requested"),SM6); O->SetBoolField(TEXT("nanite_eligible"),Eligible); O->SetStringField(TEXT("shader_platform"),Platform);
        O->SetStringField(TEXT("rhi"),GDynamicRHI?GDynamicRHI->GetName():TEXT("none")); O->SetBoolField(TEXT("null_rhi"),GUsingNullRHI); O->SetStringField(TEXT("adapter"),GRHIAdapterName);
        O->SetArrayField(TEXT("viewport"),{MakeShared<FJsonValueNumber>(Size.X),MakeShared<FJsonValueNumber>(Size.Y)}); O->SetArrayField(TEXT("fixture_origin"),Vec(Origin));
        O->SetArrayField(TEXT("meshes"),Meshes); O->SetArrayField(TEXT("frames"),Frames); O->SetNumberField(TEXT("frame_count"),Frames.Num()); O->SetArrayField(TEXT("asset_files"),Packages); O->SetArrayField(TEXT("source_inputs"),Inputs);
        if (OriginalResolution.IsValid()) O->SetObjectField(TEXT("original_resolution_control"),OriginalResolution);
        O->SetObjectField(TEXT("restored_resolution_control"),Resolution.Read());
        if (Failed&&Step<Count()) { O->SetNumberField(TEXT("pending_step"),Step); O->SetObjectField(TEXT("pending_readiness"),ReadinessJson()); }
        O->SetStringField(TEXT("lighting"),TEXT("two temporary point lights, key 20M lm warm/fill 5M lm cool; manual ISO100 1/60 f2.8, bias0; directional/fog/atmosphere/sky/GI/reflection excluded; neutral global grade and no bloom/AO; final screenshot-view settings recorded, no photometric calibration"));
        O->SetBoolField(TEXT("restored"),Restored); O->SetBoolField(TEXT("packages_unchanged"),Unchanged); O->SetBoolField(TEXT("passed"),!Failed&&!Test.HasAnyErrors()&&Step==Count());
        O->SetStringField(TEXT("acceptance"),TEXT("original paired pixels and human geometry/material review required; no GPU counters inferred; SM5 generated fallback differs from authored pool"));
        FString Json; FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Json));
        const FString ReportPath=Folder/TEXT("capture.json"); const bool Saved=FFileHelper::SaveStringToFile(Json,*ReportPath);
        Test.TestTrue(TEXT("Writes original probe observation report"),Saved);
        // Also locates a deadline failure that produced no PNG at all.
        if (Saved) UE_LOG(LogTemp,Display,TEXT("SORA_TIMBER_PROBE_REPORT %s"),*ReportPath);
    }
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraTimberProbeSM6Test,"SoraCapture.TimberProbe.SM6",EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraTimberProbeSM6Test::RunTest(const FString& Parameters)
{ (void)Parameters; FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<SoraTimberProbeCapture::FRun>(*this,true)); return true; }
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraTimberProbeSM5Test,"SoraCapture.TimberProbe.SM5",EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraTimberProbeSM5Test::RunTest(const FString& Parameters)
{ (void)Parameters; FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<SoraTimberProbeCapture::FRun>(*this,false)); return true; }
#endif
