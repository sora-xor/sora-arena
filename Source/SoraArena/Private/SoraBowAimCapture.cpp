#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraArcheryTarget.h"
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEquipmentComponent.h"
#include "SoraFrontEnd.h"
#include "SoraGameEvents.h"
#include "SoraHUD.h"
#include "HUD/SoraHUDPanels.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraViewmodelComponent.h"
#include "AssetCompilingManager.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "ContentStreaming.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "GameFramework/WorldSettings.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "InputKeyEventArgs.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"
#include <initializer_list>

// Prepared checkpoint/view, then live mapped inputs and ordinary wall-clock
// frames. No world freeze, manual tick, draw-age write or cosmetic override.
// Run SoraCapture.BowAim.Live at each requested 1280x720 / 1920x1080 viewport.
namespace SoraBowAimCapture
{
const TCHAR* Phases[]={TEXT("steady"),TEXT("positive"),TEXT("negative"),TEXT("released")};
struct FFrame
{
    FVector2D Reticle,Projected,Target;
    FVector Camera,Ray,PresentationRay;
    FRotator Rotation,Offset;
    FQuat Bow;
    FString PresentationPose;
    float WorldFOV=0,FirstPersonFOV=0;
    bool FallbackBow=false;
    TArray<TSharedPtr<FJsonValue>> Bounds;
    float NearClip=0,AimClearancePixels=0;
    uint64 Number=0;
    double Age=0,Wall=0,World=0;
    bool Drawing=false,Held=false;
    int32 Ammo=0;
};
class FRun final : public IAutomationLatentCommand
{
public:
    explicit FRun(FAutomationTestBase& InTest):Test(InTest) {}
    ~FRun() { Cleanup(); }
    bool Update() override
    {
        if(!Started) { Started=true; Begin(); }
        if(Failed||Phase==4) { Cleanup(); return true; }
        const double Now=FPlatformTime::Seconds();
        if(Now-BeganWall>150) { Fail(TEXT("Live bow capture exceeded its wall-clock timeout")); Cleanup(); return true; }
        if(!M.IsValid()||!Hero()||!PC()) { Fail(TEXT("Live capture lost its game world or hero")); return false; }
        if(Stage==0)
        {
            FAssetCompilingManager::Get().ProcessAsyncTasks(true);
            if(FAssetCompilingManager::Get().GetNumRemainingAssets()||!M->IsPlaying()||C()->CurrentDialogueCue())
            { QuietAt=Now; return false; }
            if(Now-QuietAt<2) return false;
            IStreamingManager::Get().StreamAllResources(4.f);
            const FVector Line=C()->ArcheryLine();
            Hero()->GetCharacterMovement()->StopMovementImmediately();
            Hero()->SetActorLocation(Line+FVector(0,0,Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2));
            Stage=1; QuietAt=Now; return false;
        }
        if(Stage==1&&Now-QuietAt>.5)
        {
            if(!C()->AtArcheryLine()||!C()->ArcheryTarget(0)) { Fail(TEXT("Prepared range view is not grounded on the actual line")); return false; }
            const FRotator Look=(C()->ArcheryTarget(0)->GetActorLocation()-Hero()->GetCamera()->GetComponentLocation()).Rotation();
            PC()->SetControlRotation(Look);
            BowKey=Mapped(TEXT("WeaponThree")); FireKey=Mapped(TEXT("Fire"));
            if(!Key(BowKey,IE_Pressed)||!Key(BowKey,IE_Released)) return false;
            Stage=2; QuietAt=Now; return false;
        }
        if(Stage==2&&Now-QuietAt>.5)
        {
            if(Hero()->WeaponId!=18||!C()->IsArcheryLesson()) { Fail(TEXT("Mapped bow equip did not preserve the real range lesson")); return false; }
            TArray<USceneComponent*> Parts; Hero()->GetViewmodel()->GetChildrenComponents(true,Parts);
            if(!Hero()->GetViewmodel()->IsVisible()||!Parts.ContainsByPredicate([](const USceneComponent* Part) {
                return Part->IsVisible()&&Part->GetName().StartsWith(TEXT("YumiUpper")); }))
            { Fail(TEXT("The held yumi proxy is absent or hidden")); return false; }
            FHitResult Hit;
            if(!M->GetWorld()->LineTraceSingleByChannel(Hit,Hero()->GetCamera()->GetComponentLocation(),
                C()->ArcheryTarget(0)->GetActorLocation(),ECC_Visibility,FCollisionQueryParams(SCENE_QUERY_STAT(BowCaptureTarget),false,Hero()))||
                Hit.GetActor()!=C()->ArcheryTarget(0)) { Fail(TEXT("The actual range target is occluded in the fixed view")); return false; }
            FixedCamera=Hero()->GetCamera()->GetComponentLocation(); FixedRotation=PC()->GetControlRotation();
            DrawWorld=M->GetWorld()->GetTimeSeconds(); DrawWall=Now;
            if(!Key(FireKey,IE_Pressed)||!Hero()->GetEquipment()->IsBowDrawing()) { Fail(TEXT("Mapped Attack did not begin the real draw")); return false; }
            Stage=3;
        }
        return false;
    }
private:
    FAutomationTestBase& Test;
    TWeakObjectPtr<ASoraGameMode> M;
    TWeakObjectPtr<ASoraHUD> HUD;
    TWeakObjectPtr<USoraGameEvents> Events;
    FString Slot,OriginalSlot,ControlSlot,SettingsSlot,Folder,PendingFile;
    TArray<FInputActionKeyMapping> Actions;
    TArray<FInputAxisKeyMapping> Axes;
    TArray<uint8> CampaignBytes,ControlBytes,SettingsBytes;
    bool HadCampaign=false,HadControls=false,HadSettings=false,ShowHUD=true,Started=false,Failed=false,Cleaned=false;
    bool WasCampaign=false,WasPractice=false;
    int32 Stage=0,Phase=0,Shots=0;
    uint64 ShotFrame=0;
    FVector2D Viewport;
    FKey BowKey,FireKey;
    FDelegateHandle ReticleHandle,ScreenshotHandle,ShotHandle;
    double BeganWall=0,QuietAt=0,DrawWorld=0,DrawWall=0,ShotWorld=0;
    FVector FixedCamera,ShotRay;
    FRotator FixedRotation;
    FFrame Last;
    ASoraPlayerCharacter* Hero() const { return M.IsValid()?M->Hero():nullptr; }
    APlayerController* PC() const { return Hero()?Cast<APlayerController>(Hero()->GetController()):nullptr; }
    USoraCampaignDirector* C() const { return M.IsValid()?M->Campaign():nullptr; }
    void Fail(const TCHAR* Why) { Test.AddError(Why); Failed=true; }
    FKey Mapped(const TCHAR* Action)
    {
        for(const FKey& K:Hero()->GetActionKeys(Action)) if(!K.IsGamepadKey()) return K;
        Fail(TEXT("The capture action has no mapped keyboard/mouse key")); return EKeys::Invalid;
    }
    bool Key(const FKey& K,EInputEvent Event)
    {
        if(!K.IsValid()||!PC()||!PC()->PlayerInput||!Hero()->InputComponent)
        { Fail(TEXT("Mapped input lost its live controller stack")); return false; }
        PC()->InputKey(FInputKeyEventArgs::CreateSimulated(K,Event,Event==IE_Pressed?1.f:0.f));
        PC()->PlayerInput->ProcessInputStack({Hero()->InputComponent},M->GetWorld()->GetDeltaSeconds(),M->GetWorld()->IsPaused());
        return true;
    }
    void Begin()
    {
        BeganWall=QuietAt=FPlatformTime::Seconds();
        if(FApp::UseFixedTimeStep()||GEngine->bUseFixedFrameRate) { Fail(TEXT("Bow capture requires ordinary wall-clock frames, not a fixed simulation clock")); return; }
        for(const auto& Context:GEngine->GetWorldContexts())
            if(Context.WorldType==EWorldType::Game&&Context.World()) M=Cast<ASoraGameMode>(Context.World()->GetAuthGameMode());
        if(!M.IsValid()||!PC()||!PC()->PlayerInput||!M->GetWorld()->GetGameViewport()) { Fail(TEXT("Bow capture requires the running rendering game")); return; }
        M->GetWorld()->GetGameViewport()->GetViewportSize(Viewport);
        if(Viewport!=FVector2D(1280,720)&&Viewport!=FVector2D(1920,1080)) { Fail(TEXT("Bow aim capture requires 1280x720 or 1920x1080")); return; }
        HUD=Cast<ASoraHUD>(PC()->GetHUD());
        if(!HUD.IsValid()) { Fail(TEXT("Bow aim capture requires the actual game HUD")); return; }
        ShowHUD=HUD->bShowHUD;
        WasCampaign=M->bCampaign; WasPractice=M->bDeterministicPractice;
        OriginalSlot=M->SaveSlotName; ControlSlot=M->ControlSlotName; SettingsSlot=M->SettingsSlotName;
        HadCampaign=UGameplayStatics::DoesSaveGameExist(OriginalSlot,0);
        HadControls=UGameplayStatics::DoesSaveGameExist(ControlSlot,0);
        HadSettings=UGameplayStatics::DoesSaveGameExist(SettingsSlot,0);
        if((HadCampaign&&!UGameplayStatics::LoadDataFromSlot(CampaignBytes,OriginalSlot,0))||
            (HadControls&&!UGameplayStatics::LoadDataFromSlot(ControlBytes,ControlSlot,0))||
            (HadSettings&&!UGameplayStatics::LoadDataFromSlot(SettingsBytes,SettingsSlot,0))) { Fail(TEXT("Could not preserve profile bytes")); return; }
        Actions=PC()->PlayerInput->ActionMappings; Axes=PC()->PlayerInput->AxisMappings;
        const FString Id=FGuid::NewGuid().ToString(EGuidFormats::Digits);
        Slot=TEXT("SoraBowAim_")+Id;
        Folder=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Screenshots/SoraBowAim")/
            FString::Printf(TEXT("%dx%d"),int32(Viewport.X),int32(Viewport.Y))/Id);
        IFileManager::Get().MakeDirectory(*Folder,true);
        auto* Save=NewObject<USoraSaveGame>();
        if(!USoraCampaignDirector::SeedCheckpoint(*Save,0,6)||!UGameplayStatics::SaveGameToSlot(Save,Slot,0)) { Fail(TEXT("Could not seed the isolated b07 checkpoint")); return; }
        HUD->bShowHUD=true;
        M->SetMenuOpen(true); M->SaveSlotName=Slot; M->bCampaign=true; M->bDeterministicPractice=false;
        if(!C()->LoadSave()) { Fail(TEXT("The isolated b07 checkpoint did not load")); return; }
        M->ResetRound(); M->BeginRound();
        ReticleHandle=HUD->OnReticleDrawn.AddRaw(this,&FRun::Drawn);
        ScreenshotHandle=FScreenshotRequest::OnScreenshotRequestProcessed().AddRaw(this,&FRun::Captured);
        Events=USoraGameEvents::Get(M.Get());
        if(!Events.IsValid()) { Fail(TEXT("The live shot event bus is missing")); return; }
        ShotHandle=Events->OnWeaponFired.AddLambda([this](const FSoraWeaponFiredEvent& E) {
            if(E.Shooter==Hero()&&E.WeaponId==18)
            { ++Shots; ShotRay=E.Direction; ShotWorld=M->GetWorld()->GetTimeSeconds(); ShotFrame=GFrameCounter; }
        });
    }
    void Drawn(const FVector2D& Center)
    {
        if(Failed||Stage!=3||Phase>=4) return;
        auto* Kit=Hero()->GetEquipment(); auto* Camera=Hero()->GetCamera();
        Last.Reticle=Center; Last.Camera=Camera->GetComponentLocation(); Last.Rotation=PC()->GetControlRotation();
        Last.Ray=Kit->BowAimDirection(); Last.Offset=Kit->BowAimOffset(); Last.Bow=Hero()->GetViewmodel()->GetRelativeRotation().Quaternion();
        const FMinimalViewInfo View=SoraViewmodelPresentation::CameraView(*Camera);
        Last.PresentationRay=(View.TransformWorldToFirstPerson(View.Location+Hero()->GetViewmodel()->GetForwardVector()*10000.f,true)-View.Location).GetSafeNormal();
        Last.PresentationPose=Hero()->GetViewmodel()->PresentationPose(); Last.FallbackBow=Hero()->GetViewmodel()->UsesFallbackBowPresentation();
        Last.WorldFOV=View.FOV; Last.FirstPersonFOV=View.FirstPersonFOV;
        Last.Number=GFrameCounter; Last.World=M->GetWorld()->GetTimeSeconds(); Last.Age=Last.World-DrawWorld; Last.Wall=FPlatformTime::Seconds()-DrawWall;
        Last.Drawing=Kit->IsBowDrawing(); Last.Held=PC()->PlayerInput->IsPressed(FireKey); Last.Ammo=Kit->Ammo;
        if(!PC()->ProjectWorldLocationToScreen(Last.Camera+Last.Ray*10000.f,Last.Projected)||
            !PC()->ProjectWorldLocationToScreen(C()->ArcheryTarget(0)->GetActorLocation(),Last.Target)||
            !Last.Camera.Equals(FixedCamera,.1)||!Last.Rotation.Equals(FixedRotation,.001)||
            !Camera->GetComponentRotation().Equals(FixedRotation,.001)||
            !Last.FallbackBow||Last.Bow.ContainsNaN()||
            Last.PresentationPose!=(Last.Drawing?TEXT("fallback.bow.drawn"):TEXT("fallback.bow"))||
            (Last.Drawing&&!Last.PresentationRay.Equals(Last.Ray,1e-5))||
            FVector2D::Distance(Center,Last.Projected)>.25||M->GetWorld()->IsPaused()||
            !FMath::IsNearlyEqual(M->GetWorld()->GetWorldSettings()->GetEffectiveTimeDilation(),1.f)||
            !FMath::IsNearlyEqual(Hero()->CustomTimeDilation,1.f))
        { Fail(TEXT("Live reticle/presentation direction, fixed camera or ordinary world-clock invariant failed")); return; }
        // Actual component volumes after native FP projection, independently
        // projected through this viewport. Socket points alone miss the bulky
        // fallback grip/paw. Narrow arrow pieces have their own size checks;
        // these observations do not admit the authored 20 m arrow package.
        TArray<SoraViewmodelPresentation::FPartBounds> Parts;
        if(!Hero()->GetViewmodel()->FallbackBowBounds(Parts)) { Fail(TEXT("Missing actual fallback bow bounds")); return; }
        Last.Bounds.Reset(); Last.NearClip=View.GetFinalPerspectiveNearClipPlane();
        Last.AimClearancePixels=Viewport.X*.07f;
        bool GripVisible=false,StaveVisible=false;
        for(const auto& Part:Parts)
        {
            FBox2D Screen(ForceInit); double Depth=TNumericLimits<double>::Max();
            for(const FVector& Corner:Part.WorldCorners)
            {
                const FVector Native=View.TransformWorldToFirstPerson(Corner,false);
                FVector2D Pixel;
                if(!PC()->ProjectWorldLocationToScreen(Native,Pixel)) { Fail(TEXT("Fallback geometry is behind the projection plane")); return; }
                Screen+=Pixel;
                Depth=FMath::Min(Depth,View.Rotation.UnrotateVector(Native-View.Location).X);
            }
            if(Depth<Last.NearClip+2.f-.01f||(!Part.bArrow&&Screen.Max.X>Center.X-Last.AimClearancePixels+.25f)||
                (Part.bArrow&&Screen.GetSize().Y>Viewport.Y*.04f))
            { Fail(TEXT("Fallback bow volume obstructs aim, clips the near plane or enlarges its narrow arrow")); return; }
            if(Part.Name==TEXT("YumiGrip"))
                GripVisible=Screen.Min.X>=Viewport.X*.05f&&Screen.Max.X<=Viewport.X*.95f&&
                    Screen.Min.Y>=Viewport.Y*.05f&&Screen.Max.Y<=Viewport.Y*.95f&&
                    Screen.GetSize().X>=Viewport.X*.035f&&Screen.GetSize().Y>=Viewport.Y*.15f;
            if(Part.Name==TEXT("YumiLower")||Part.Name==TEXT("YumiUpper"))
                StaveVisible|=FMath::Min(Screen.Max.Y,Viewport.Y)-FMath::Max(Screen.Min.Y,0.)>=Viewport.Y*.25f&&
                    FMath::Min(Screen.Max.X,Viewport.X)-FMath::Max(Screen.Min.X,0.)>=2.;
            auto Row=MakeShared<FJsonObject>(); Row->SetStringField(TEXT("part"),Part.Name);
            Row->SetBoolField(TEXT("narrow_arrow"),Part.bArrow); Row->SetNumberField(TEXT("corner_count"),Part.WorldCorners.Num());
            Row->SetNumberField(TEXT("min_fp_depth_cm"),Depth);
            Row->SetArrayField(TEXT("projected_rect"),{MakeShared<FJsonValueNumber>(Screen.Min.X),MakeShared<FJsonValueNumber>(Screen.Min.Y),
                MakeShared<FJsonValueNumber>(Screen.Max.X),MakeShared<FJsonValueNumber>(Screen.Max.Y)});
            Last.Bounds.Add(MakeShared<FJsonValueObject>(Row));
        }
        if(!GripVisible||!StaveVisible) { Fail(TEXT("Fallback framing hides the readable grip/stave")); return; }
        if(!PendingFile.IsEmpty()) return;
        const bool Ready=Phase==0?(Last.Age>=1&&Last.Age<4.65&&Last.Drawing&&Last.Held&&Last.Offset.IsZero()):
            Phase==1?(Last.Drawing&&Last.Held&&Last.Offset.Pitch>.10&&Last.Offset.Yaw>.20):
            Phase==2?(Last.Drawing&&Last.Held&&Last.Offset.Pitch<-.12&&Last.Offset.Yaw<-.18):
            (!Last.Drawing&&!Last.Held&&Last.Offset.IsZero()&&Last.Ammo==11&&Shots==1);
        if(!Ready) return;
        int32 ViewW=0,ViewH=0; PC()->GetViewportSize(ViewW,ViewH);
        const FSoraHUDFrame Layout(*HUD.Get(),*M.Get(),ViewW,ViewH);
        FString LayoutWhy;
        if(!SoraHUDPanels::BottomHUDLayoutFits(Layout,*Hero(),LayoutWhy)||
            !SoraHUDPanels::StoryTrackerLayoutFits(Layout,LayoutWhy)||
            !SoraHUDPanels::CaptionStoryLayoutFits(Layout,LayoutWhy)||
            !SoraHUDPanels::InteractionPromptLayoutFits(Layout,LayoutWhy))
        { Fail(*(TEXT("Live bow HUD layout: ")+LayoutWhy)); return; }
        PendingFile=Folder/(FString(Phases[Phase])+TEXT(".png"));
        FScreenshotRequest::RequestScreenshot(PendingFile,true,false);
    }
    void Captured()
    {
        if(Failed||PendingFile.IsEmpty()) return;
        if(Last.Number!=GFrameCounter||IFileManager::Get().FileSize(*PendingFile)<=0)
        { Fail(TEXT("Bow PNG was not written from the observed HUD frame")); return; }
        const FFrame Sample=Last;
        auto Json=MakeShared<FJsonObject>();
        Json->SetStringField(TEXT("phase"),Phases[Phase]);
        Json->SetStringField(TEXT("scope"),TEXT("live mapped bow draw from prepared checkpoint/view; not playthrough or art acceptance"));
        Json->SetNumberField(TEXT("frame"),double(Sample.Number)); Json->SetNumberField(TEXT("draw_age_s"),Sample.Age);
        Json->SetNumberField(TEXT("sample_world_s"),Sample.World);
        Json->SetNumberField(TEXT("wall_elapsed_s"),Sample.Wall); Json->SetBoolField(TEXT("drawing"),Sample.Drawing);
        Json->SetBoolField(TEXT("attack_held"),Sample.Held); Json->SetNumberField(TEXT("ammo"),Sample.Ammo);
        const auto Array=[&](const TCHAR* Name,std::initializer_list<double> Values) {
            TArray<TSharedPtr<FJsonValue>> Out; for(double V:Values) Out.Add(MakeShared<FJsonValueNumber>(V)); Json->SetArrayField(Name,Out);
        };
        Array(TEXT("viewport"),{Viewport.X,Viewport.Y}); Array(TEXT("reticle"),{Sample.Reticle.X,Sample.Reticle.Y});
        Array(TEXT("projected"),{Sample.Projected.X,Sample.Projected.Y}); Array(TEXT("target"),{Sample.Target.X,Sample.Target.Y});
        Array(TEXT("camera"),{Sample.Camera.X,Sample.Camera.Y,Sample.Camera.Z});
        Array(TEXT("rotation"),{Sample.Rotation.Pitch,Sample.Rotation.Yaw,Sample.Rotation.Roll});
        Array(TEXT("offset_degrees"),{Sample.Offset.Pitch,Sample.Offset.Yaw}); Array(TEXT("ray"),{Sample.Ray.X,Sample.Ray.Y,Sample.Ray.Z});
        Array(TEXT("bow_quat"),{Sample.Bow.X,Sample.Bow.Y,Sample.Bow.Z,Sample.Bow.W});
        Json->SetStringField(TEXT("presentation_pose"),Sample.PresentationPose);
        Json->SetNumberField(TEXT("presentation_schema_version"),2);
        Json->SetStringField(TEXT("presentation_admission"),TEXT("explicit fixed primitive fallback framing; actual projected bounds checked; authored 20m arrow/paw package and visual quality unqualified"));
        Json->SetArrayField(TEXT("fallback_component_bounds"),Sample.Bounds);
        Json->SetNumberField(TEXT("fallback_near_clip_cm"),Sample.NearClip);
        Json->SetNumberField(TEXT("fallback_aim_clearance_pixels"),Sample.AimClearancePixels);
        Json->SetBoolField(TEXT("fallback_bow"),Sample.FallbackBow);
        Array(TEXT("presentation_projected_direction"),{Sample.PresentationRay.X,Sample.PresentationRay.Y,Sample.PresentationRay.Z});
        Json->SetNumberField(TEXT("world_fov"),Sample.WorldFOV); Json->SetNumberField(TEXT("first_person_fov"),Sample.FirstPersonFOV);
        if(Phase==2)
        {
            // Keep the observed render sample and actual release separate.
            // A callback's scheduling alone is not proof of equal aim/time.
            const double ReleaseWorld=M->GetWorld()->GetTimeSeconds();
            const FVector ReleaseRay=Hero()->GetEquipment()->BowAimDirection();
            FVector2D ReleaseProjected;
            if(!PC()->ProjectWorldLocationToScreen(Hero()->GetCamera()->GetComponentLocation()+ReleaseRay*10000.f,ReleaseProjected))
            { Fail(TEXT("The actual release aim cannot be projected")); return; }
            Json->SetNumberField(TEXT("release_frame"),double(GFrameCounter));
            Json->SetNumberField(TEXT("release_world_s"),ReleaseWorld);
            Json->SetNumberField(TEXT("release_delay_s"),ReleaseWorld-Sample.World);
            Json->SetNumberField(TEXT("release_wall_elapsed_s"),FPlatformTime::Seconds()-DrawWall);
            Array(TEXT("release_ray"),{ReleaseRay.X,ReleaseRay.Y,ReleaseRay.Z});
            Array(TEXT("release_projected"),{ReleaseProjected.X,ReleaseProjected.Y});
            if(!Key(FireKey,IE_Released)||!Test.TestEqual(TEXT("The rendered draw releases one actual shot"),Shots,1)||
                !Test.TestTrue(TEXT("The shot matches the independently sampled actual release aim"),ShotRay.Equals(ReleaseRay,1e-8)))
            { Failed=true; return; }
            Json->SetBoolField(TEXT("shot_matches_render_sample"),ShotRay.Equals(Sample.Ray,1e-8));
            Json->SetNumberField(TEXT("shot_frame"),double(ShotFrame)); Json->SetNumberField(TEXT("shot_world_s"),ShotWorld);
            Array(TEXT("shot_ray"),{ShotRay.X,ShotRay.Y,ShotRay.Z});
        }
        FString Text; FJsonSerializer::Serialize(Json,TJsonWriterFactory<>::Create(&Text));
        const FString Metadata=FPaths::ChangeExtension(PendingFile,TEXT("json"));
        if(!FFileHelper::SaveStringToFile(Text,*Metadata,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
        { Fail(TEXT("Bow capture could not write its frame observations")); return; }
        UE_LOG(LogTemp,Display,TEXT("SORA_BOW_AIM_FRAME %s"),*PendingFile);
        UE_LOG(LogTemp,Display,TEXT("SORA_BOW_AIM_SAMPLE %s"),*Text);
        PendingFile.Reset(); ++Phase;
    }
    void Cleanup()
    {
        if(Cleaned) return; Cleaned=true;
        if(!PendingFile.IsEmpty()) FScreenshotRequest::Reset();
        if(HUD.IsValid()) { HUD->OnReticleDrawn.Remove(ReticleHandle); HUD->bShowHUD=ShowHUD; }
        FScreenshotRequest::OnScreenshotRequestProcessed().Remove(ScreenshotHandle);
        if(Events.IsValid()) Events->OnWeaponFired.Remove(ShotHandle);
        if(!Slot.IsEmpty()&&M.IsValid())
        {
            if(Hero()) Hero()->GetEquipment()->Halt();
            if(PC()&&PC()->PlayerInput)
            {
                PC()->PlayerInput->FlushPressedKeys();
                Test.TestTrue(TEXT("Bow capture leaves no held capture inputs"),
                    (!FireKey.IsValid()||!PC()->PlayerInput->IsPressed(FireKey))&&(!BowKey.IsValid()||!PC()->PlayerInput->IsPressed(BowKey)));
                Test.TestTrue(TEXT("Bow capture preserves action and axis mappings"),PC()->PlayerInput->ActionMappings==Actions&&PC()->PlayerInput->AxisMappings==Axes);
            }
            M->SetMenuOpen(true); M->SaveSlotName=OriginalSlot;
            M->bCampaign=WasCampaign; M->bDeterministicPractice=WasPractice;
            C()->LoadSave(); M->ResetRound(); M->FrontEnd()->ShowTitle();
            for(int32 I=0;I<3;++I)
            {
                const FString& Name=I==0?OriginalSlot:I==1?ControlSlot:SettingsSlot;
                const bool Existed=I==0?HadCampaign:I==1?HadControls:HadSettings;
                const auto& Before=I==0?CampaignBytes:I==1?ControlBytes:SettingsBytes; TArray<uint8> After;
                const auto Identical=[&]() {
                    return UGameplayStatics::DoesSaveGameExist(Name,0)==Existed&&
                        (!Existed||(UGameplayStatics::LoadDataFromSlot(After,Name,0)&&Before==After));
                };
                const bool Same=Identical();
                // Loading/resetting the player's original slot may persist a
                // default or normalized save. Restore its original bytes (or
                // absence) after that work; never leave the capture's reset.
                if(I>0) Test.TestTrue(TEXT("Bow capture does not modify saved controls/settings"),Same);
                if(!Same)
                {
                    if(Existed) UGameplayStatics::SaveDataToSlot(Before,Name,0);
                    else UGameplayStatics::DeleteGameInSlot(Name,0);
                }
                Test.TestTrue(FString::Printf(TEXT("Bow capture preserves original profile bytes/existence: %s"),*Name),Identical());
            }
        }
        if(!Slot.IsEmpty()) UGameplayStatics::DeleteGameInSlot(Slot,0);
    }
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraBowAimCaptureTest,"SoraCapture.BowAim.Live",
    EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraBowAimCaptureTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<SoraBowAimCapture::FRun>(*this));
    return true;
}
#endif
