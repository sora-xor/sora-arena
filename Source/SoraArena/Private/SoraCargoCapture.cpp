#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraEnemy.h"
#include "SoraFrontEnd.h"
#include "SoraGameEvents.h"
#include "SoraHorse.h"
#include "SoraHUD.h"
#include "HUD/SoraHUDPanels.h"
#include "SoraLeadRopeComponent.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "AssetCompilingManager.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "ContentStreaming.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "GameFramework/WorldSettings.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "InputKeyEventArgs.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/App.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"
#include <initializer_list>

// Assisted scene review: checkpoint, placements, camera and frozen AI are
// preparation. Only mapped Interact and ordinary running-world time deliver
// cargo. Static screenshots pause the world; the entire b15 cinematic runs.
// Getters validate identity, never appearance. Review the original PNGs.
namespace SoraCargoCapture
{
const TCHAR* Scope=TEXT("prepared cargo checkpoint/positions/camera and frozen AI; mapped active-time unloads; paused original frames; not playthrough or art acceptance");
const TCHAR* Phases[]={TEXT("remaining-30"),TEXT("remaining-20"),TEXT("remaining-10"),TEXT("remaining-0")};
using FJson=TSharedPtr<FJsonObject>;
void Vector(FJson J,const TCHAR* Name,const FVector& V)
{
    J->SetArrayField(Name,{MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)});
}
class FRun final : public IAutomationLatentCommand
{
public:
    explicit FRun(FAutomationTestBase& In):Test(In) {}
    ~FRun() { Cleanup(); }
    bool Update() override
    {
        if(!Started) { Started=true; Begin(); }
        if(Failed||Phase==4) { Cleanup(); return true; }
        const double Now=FPlatformTime::Seconds();
        if(Now-BeganWall>240) { Fail(TEXT("Cargo capture exceeded 240 seconds")); return false; }
        if(!M.IsValid()||!Hero()||!PC()||!C()||!OrdinaryClock()) { Fail(TEXT("Cargo capture lost its ordinary live world")); return false; }
        HoldThreats();
        if(Stage==EStage::Ready)
        {
            FAssetCompilingManager::Get().ProcessAsyncTasks(true);
            if(FAssetCompilingManager::Get().GetNumRemainingAssets()||!M->IsPlaying()||C()->CurrentDialogueCue())
            { QuietAt=Now; return false; }
            if(Now-QuietAt<2) return false;
            if(C()->ActiveBeat()!=13||!C()->IsMounted()) { Fail(TEXT("Cargo seed did not enter mounted b14")); return false; }
            Interact=Mapped(TEXT("Interact"));
            if(!Key(IE_Pressed)||!Key(IE_Released)) return false;
            if(C()->IsMounted()) { Fail(TEXT("Mapped Interact did not dismount at the original start")); return false; }
            Dismounted=true; Prepare(0); Stage=EStage::Settle; FirstFrame=true;
        }
        else if(Stage==EStage::Settle&&Now-QuietAt>=1)
        {
            if(FirstFrame) { PauseFrame(); FirstFrame=false; }
            else StartHold();
        }
        else if(Stage==EStage::Holding)
        {
            const bool Accepted=Point==2?Terminal.IsValid():(C()->ActiveBeat()==13&&C()->TaskProgress().Done==Point+1);
            if(Accepted)
            {
                if(!Key(IE_Released)) return false;
                auto Hold=MakeShared<FJsonObject>();
                Hold->SetNumberField(TEXT("destination"),Point);
                Hold->SetNumberField(TEXT("before"),Point); Hold->SetNumberField(TEXT("after"),Point+1);
                Hold->SetNumberField(TEXT("start_world_s"),HoldWorld); Hold->SetNumberField(TEXT("end_world_s"),WorldTime());
                Hold->SetNumberField(TEXT("start_wall_s"),HoldWall-BeganWall); Hold->SetNumberField(TEXT("end_wall_s"),Now-BeganWall);
                Hold->SetNumberField(TEXT("world_elapsed_s"),WorldTime()-HoldWorld);
                Hold->SetNumberField(TEXT("wall_elapsed_s"),Now-HoldWall);
                Hold->SetBoolField(TEXT("mapped_interact"),true); Hold->SetBoolField(TEXT("paused_during_hold"),false);
                Holds.Add(MakeShared<FJsonValueObject>(Hold));
                if(WorldTime()-HoldWorld<2.999||Now-HoldWall<2.9) { Fail(TEXT("Cargo was accepted without the ordinary three-second hold")); return false; }
                if(Point==2) Stage=EStage::Cinema;
                else { QuietAt=Now; Stage=EStage::Accepted; }
            }
            else if(C()->ActiveBeat()!=13||C()->TaskProgress().Done!=Point||!C()->IsUnloadingCargo()||Now-HoldWall>8)
                Fail(TEXT("The mapped hold stopped or changed its unique delivery unexpectedly"));
        }
        else if(Stage==EStage::Accepted&&Now-QuietAt>=.3) PauseFrame();
        else if(Stage==EStage::Cinema&&CinemaEnded)
        {
            if(C()->ActiveBeat()!=15||!Terminal.IsValid()||CinemaElapsedMs!=90000||CinemaWorldEnd-CinemaWorldStart<89.9||
                CinemaWallEnd-CinemaWallStart<89.5) { Fail(TEXT("Cargo capture did not observe the full ordinary 90-second b15 cinematic")); return false; }
            // b14's props have naturally gone. Keep its zero Registry feedback
            // on the real returning HUD, without recreating old cargo visuals.
            const FVector H=Hero()->GetActorLocation();
            SetCamera(H+FVector(-700,-900,350),H+FVector(0,0,80));
            PauseFrame();
        }
        return false;
    }
private:
    enum class EStage { Ready,Settle,Paused,Holding,Accepted,Cinema };
    EStage Stage=EStage::Ready;
    FAutomationTestBase& Test;
    TWeakObjectPtr<ASoraGameMode> M;
    TWeakObjectPtr<ASoraHUD> HUD;
    TWeakObjectPtr<USoraGameEvents> Events;
    TWeakObjectPtr<ACameraActor> Camera;
    FString Slot,OriginalSlot,ControlSlot,SettingsSlot,Folder,PendingFile;
    TArray<uint8> CampaignBytes,ControlBytes,SettingsBytes;
    TArray<FInputActionKeyMapping> Actions;
    TArray<FInputAxisKeyMapping> Axes;
    TArray<TSharedPtr<FJsonValue>> Frames,Holds,Preparations;
    FJson Last,Terminal;
    FDelegateHandle DrawHandle,ScreenshotHandle,StartedHandle,CompletedHandle;
    FKey Interact;
    FVector2D Viewport;
    FVector Dropoff;
    bool Started=false,Failed=false,Cleaned=false,ShowHUD=true,WasCampaign=false,WasPractice=false,WasEnglish=true;
    bool HadCampaign=false,HadControls=false,HadSettings=false,Dismounted=false,FirstFrame=false,CinemaEnded=false;
    int32 Phase=0,Point=0,CinemaElapsedMs=0,Completions=0;
    uint64 RequestFrame=0;
    double BeganWall=0,QuietAt=0,HoldWorld=0,HoldWall=0,PauseWorld=0;
    double CinemaWorldStart=-1,CinemaWallStart=-1,CinemaWorldEnd=-1,CinemaWallEnd=-1;
    ASoraPlayerCharacter* Hero() const { return M.IsValid()?M->Hero():nullptr; }
    APlayerController* PC() const { return Hero()?Cast<APlayerController>(Hero()->GetController()):nullptr; }
    USoraCampaignDirector* C() const { return M.IsValid()?M->Campaign():nullptr; }
    double WorldTime() const { return M->GetWorld()->GetTimeSeconds(); }
    void Fail(const TCHAR* Why) { Test.AddError(Why); Failed=true; }
    bool OrdinaryClock() const
    {
        return !FApp::UseFixedTimeStep()&&!GEngine->bUseFixedFrameRate&&
            FMath::IsNearlyEqual(M->GetWorld()->GetWorldSettings()->GetEffectiveTimeDilation(),1.f)&&
            FMath::IsNearlyEqual(Hero()->CustomTimeDilation,1.f);
    }
    FKey Mapped(const TCHAR* Action)
    {
        for(const FKey& K:Hero()->GetActionKeys(Action)) if(!K.IsGamepadKey()) return K;
        Fail(TEXT("Cargo capture has no mapped Interact key")); return EKeys::Invalid;
    }
    bool Key(EInputEvent E)
    {
        if(!Interact.IsValid()||!PC()||!PC()->PlayerInput||!Hero()->InputComponent) { Fail(TEXT("Cargo mapped input stack is unavailable")); return false; }
        PC()->InputKey(FInputKeyEventArgs::CreateSimulated(Interact,E,E==IE_Pressed?1.f:0.f));
        PC()->PlayerInput->ProcessInputStack({Hero()->InputComponent},M->GetWorld()->GetDeltaSeconds(),M->GetWorld()->IsPaused());
        return true;
    }
    void HoldThreats()
    {
        for(TActorIterator<ASoraEnemy> It(M->GetWorld());It;++It)
        {
            It->SetActorTickEnabled(false); It->GetCharacterMovement()->StopMovementImmediately();
            It->GetCharacterMovement()->SetComponentTickEnabled(false);
            if(auto* Brain=It->GetController()) Brain->SetActorTickEnabled(false);
        }
    }
    void SetCamera(const FVector& Eye,const FVector& At)
    {
        Camera->SetActorLocation(Eye); Camera->SetActorRotation((At-Eye).Rotation());
        Camera->GetCameraComponent()->SetFieldOfView(65); PC()->SetViewTarget(Camera.Get());
    }
    void Prepare(int32 Destination)
    {
        Point=Destination;
        if(!C()->ActiveSpace()||!C()->ActiveSpace()->Dropoffs.IsValidIndex(Point)||!C()->Steed()||C()->PackHorses().Num()!=1)
        { Fail(TEXT("Cargo preparation lost its authored destination or horses")); return; }
        Dropoff=FVector(C()->ActiveSpace()->Dropoffs[Point],0);
        Hero()->GetCharacterMovement()->StopMovementImmediately();
        Hero()->SetActorLocation(Dropoff+FVector(0,-180,Hero()->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2));
        C()->Steed()->Place(Dropoff+FVector(-80,450,0),0);
        C()->PackHorses()[0]->Place(Dropoff+FVector(-380,450,0),0);
        SetCamera(Dropoff+FVector(-450,-1150,480),Dropoff+FVector(-130,170,105));
        auto J=MakeShared<FJsonObject>(); J->SetNumberField(TEXT("destination"),Point);
        Vector(J,TEXT("dropoff"),Dropoff); Vector(J,TEXT("hero"),Hero()->GetActorLocation());
        Vector(J,TEXT("steed"),C()->Steed()->GetActorLocation()); Vector(J,TEXT("pack"),C()->PackHorses()[0]->GetActorLocation());
        Vector(J,TEXT("camera"),Camera->GetActorLocation()); Preparations.Add(MakeShared<FJsonValueObject>(J));
        QuietAt=FPlatformTime::Seconds();
    }
    void StartHold()
    {
        if(M->GetWorld()->IsPaused()||C()->ActiveBeat()!=13||C()->IsMounted()||C()->TaskProgress().Done!=Point||
            !Hero()->GetCharacterMovement()->IsMovingOnGround()||FVector::Dist2D(Hero()->GetActorLocation(),Dropoff)>260||
            !C()->Steed()||FVector::Dist2D(Hero()->GetActorLocation(),C()->Steed()->GetActorLocation())<=420)
        { Fail(TEXT("Cargo hold did not start from its on-foot accepted state")); return; }
        HoldWorld=WorldTime(); HoldWall=FPlatformTime::Seconds();
        if(!Key(IE_Pressed)||!C()->IsUnloadingCargo()) { Fail(TEXT("Mapped Interact did not begin cargo unloading")); return; }
        Stage=EStage::Holding;
    }
    FJson Stock(int32 Done,bool ObserveRope=true)
    {
        const auto Packs=C()->PackHorses(); auto* Kit=M->Arena();
        if(!C()->Steed()||Packs.Num()!=1||!IsValid(Packs[0])||!Kit||Kit->CargoStandCount()!=3||C()->TaskProgress().Done!=Done||C()->IsMounted())
        { Fail(TEXT("Cargo observation lost its real horses, stands or accepted on-foot count")); return {}; }
        const int32 Remaining=Packs[0]->CargoQuantityShown();
        auto J=MakeShared<FJsonObject>(); J->SetNumberField(TEXT("deliveries"),C()->TaskProgress().Done);
        J->SetNumberField(TEXT("pack_quantity"),Remaining); J->SetNumberField(TEXT("stand_count"),Kit->CargoStandCount());
        TArray<TSharedPtr<FJsonValue>> Stands;
        for(int32 I=0;I<3;++I)
        {
            const int32 Quantity=Kit->CargoQuantityShownAt(I); Stands.Add(MakeShared<FJsonValueNumber>(Quantity));
            if(Quantity!=(I<Done?10:0)) { Fail(TEXT("Visible stand shares differ from accepted unique transfers")); return {}; }
        }
        J->SetArrayField(TEXT("stand_quantities"),Stands);
        J->SetStringField(TEXT("objective_ja"),C()->ObjectiveText()); J->SetStringField(TEXT("objective_en"),C()->ObjectiveTextEnglish());
        if(Remaining!=30-10*Done||!C()->ObjectiveText().Contains(FString::Printf(TEXT("麦 残り %d束"),Remaining))||
            !C()->ObjectiveTextEnglish().Contains(FString::Printf(TEXT("Barley: %d sheaves left"),Remaining)))
        { Fail(TEXT("Actual cargo objective and component load disagree")); return {}; }
        if(!ObserveRope) return J;
        const auto* Rope=Packs[0]->LeadRope(); FVector Halter,Tie,RenderedHalter,RenderedTie;
        if(!Rope||!Rope->Anchors(Halter,Tie)||!Rope->RenderedEndpoints(RenderedHalter,RenderedTie)||
            Rope->VisibleSegments()!=12||Rope->HasCollision()||!Halter.Equals(RenderedHalter,.01)||!Tie.Equals(RenderedTie,.01))
        { Fail(TEXT("Cargo rope endpoints, segments or collision differ from the real animated anchors")); return {}; }
        J->SetNumberField(TEXT("rope_segments"),Rope->VisibleSegments()); J->SetBoolField(TEXT("rope_collision"),Rope->HasCollision());
        Vector(J,TEXT("halter"),Halter); Vector(J,TEXT("tie"),Tie);
        Vector(J,TEXT("rendered_halter"),RenderedHalter); Vector(J,TEXT("rendered_tie"),RenderedTie);
        return J;
    }
    void PauseFrame()
    {
        if(C()->IsUnloadingCargo()||PC()->PlayerInput->IsPressed(Interact)) { Fail(TEXT("Cargo screenshot cannot pause a held unload")); return; }
        if(!UGameplayStatics::SetGamePaused(M.Get(),true)) { Fail(TEXT("Could not pause the cargo observation")); return; }
        PauseWorld=WorldTime(); QuietAt=FPlatformTime::Seconds(); Stage=EStage::Paused;
        IStreamingManager::Get().StreamAllResources(4.f);
    }
    void Begin()
    {
        BeganWall=QuietAt=FPlatformTime::Seconds();
        for(const auto& Context:GEngine->GetWorldContexts())
            if(Context.WorldType==EWorldType::Game&&Context.World()) M=Cast<ASoraGameMode>(Context.World()->GetAuthGameMode());
        if(!M.IsValid()||!PC()||!PC()->PlayerInput||!M->GetWorld()->GetGameViewport()||!OrdinaryClock()) { Fail(TEXT("Cargo capture requires an ordinary running rendered game")); return; }
        M->GetWorld()->GetGameViewport()->GetViewportSize(Viewport);
        if(Viewport!=FVector2D(1280,720)&&Viewport!=FVector2D(1920,1080)) { Fail(TEXT("Cargo capture requires 1280x720 or 1920x1080")); return; }
        HUD=Cast<ASoraHUD>(PC()->GetHUD()); if(!HUD.IsValid()) { Fail(TEXT("Cargo capture requires the actual game HUD")); return; }
        ShowHUD=HUD->bShowHUD; WasCampaign=M->bCampaign; WasPractice=M->bDeterministicPractice; WasEnglish=M->bEnglishSubtitles;
        OriginalSlot=M->SaveSlotName; ControlSlot=M->ControlSlotName; SettingsSlot=M->SettingsSlotName;
        HadCampaign=UGameplayStatics::DoesSaveGameExist(OriginalSlot,0); HadControls=UGameplayStatics::DoesSaveGameExist(ControlSlot,0);
        HadSettings=UGameplayStatics::DoesSaveGameExist(SettingsSlot,0);
        if((HadCampaign&&!UGameplayStatics::LoadDataFromSlot(CampaignBytes,OriginalSlot,0))||
            (HadControls&&!UGameplayStatics::LoadDataFromSlot(ControlBytes,ControlSlot,0))||
            (HadSettings&&!UGameplayStatics::LoadDataFromSlot(SettingsBytes,SettingsSlot,0))) { Fail(TEXT("Could not preserve cargo capture profiles")); return; }
        Actions=PC()->PlayerInput->ActionMappings; Axes=PC()->PlayerInput->AxisMappings;
        const FString Id=FGuid::NewGuid().ToString(EGuidFormats::Digits); Slot=TEXT("SoraCargo_")+Id;
        Folder=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Screenshots/SoraCargo")/
            FString::Printf(TEXT("%dx%d"),int32(Viewport.X),int32(Viewport.Y))/Id);
        IFileManager::Get().MakeDirectory(*Folder,true);
        auto* Save=NewObject<USoraSaveGame>();
        if(!USoraCampaignDirector::SeedCheckpoint(*Save,3,13)||!UGameplayStatics::SaveGameToSlot(Save,Slot,0)) { Fail(TEXT("Could not seed isolated ch04.b14")); return; }
        M->SetMenuOpen(true); M->SaveSlotName=Slot; M->bCampaign=true; M->bDeterministicPractice=false;
        if(!C()->LoadSave()) { Fail(TEXT("Could not load isolated ch04.b14")); return; }
        M->ResetRound(); M->BeginRound(); M->bEnglishSubtitles=true; HUD->bShowHUD=true;
        Camera=M->GetWorld()->SpawnActor<ACameraActor>();
        if(!Camera.IsValid()) { Fail(TEXT("Could not create cargo review camera")); return; }
        DrawHandle=HUD->OnReticleDrawn.AddRaw(this,&FRun::Drawn);
        ScreenshotHandle=FScreenshotRequest::OnScreenshotRequestProcessed().AddRaw(this,&FRun::Captured);
        Events=USoraGameEvents::Get(M.Get()); if(!Events.IsValid()) { Fail(TEXT("Cargo event bus is unavailable")); return; }
        StartedHandle=Events->OnBeatStarted.AddLambda([this](const FSoraBeatEvent& E) {
            if(E.ChapterId==3&&E.BeatIndex==14) { CinemaWorldStart=WorldTime(); CinemaWallStart=FPlatformTime::Seconds(); }
        });
        CompletedHandle=Events->OnBeatCompleted.AddLambda([this](const FSoraBeatEvent& E) {
            if(E.ChapterId!=3) return;
            if(E.BeatIndex==13) { ++Completions; Terminal=Stock(3,false); }
            if(E.BeatIndex==14)
            {
                CinemaWorldEnd=WorldTime(); CinemaWallEnd=FPlatformTime::Seconds();
                CinemaElapsedMs=C()->TaskProgress().ElapsedMs; CinemaEnded=true;
            }
        });
    }
    void Drawn(const FVector2D& Center)
    {
        (void)Center;
        if(Failed||Stage!=EStage::Paused||Phase>=4||!PendingFile.IsEmpty()||FPlatformTime::Seconds()-QuietAt<3) return;
        if(!M->GetWorld()->IsPaused()||WorldTime()!=PauseWorld||M->bMenu||!HUD->bShowHUD||!M->bEnglishSubtitles||!OrdinaryClock())
        { Fail(TEXT("Cargo observed HUD lost its paused bilingual state")); return; }
        Last=MakeShared<FJsonObject>();
        Last->SetStringField(TEXT("name"),Phases[Phase]); Last->SetStringField(TEXT("file"),FString(Phases[Phase])+TEXT(".png"));
        Last->SetNumberField(TEXT("request_frame"),double(GFrameCounter)); RequestFrame=GFrameCounter;
        Last->SetNumberField(TEXT("world_s"),WorldTime()); Last->SetNumberField(TEXT("wall_s"),FPlatformTime::Seconds()-BeganWall);
        Last->SetBoolField(TEXT("paused"),true); Last->SetBoolField(TEXT("english"),M->bEnglishSubtitles);
        Last->SetBoolField(TEXT("hud_drawn"),true); Last->SetBoolField(TEXT("interact_held"),PC()->PlayerInput->IsPressed(Interact));
        Last->SetNumberField(TEXT("beat"),C()->ActiveBeat()); Last->SetNumberField(TEXT("destination"),Point);
        Vector(Last,TEXT("camera"),Camera->GetActorLocation());
        if(Phase<3)
        {
            const auto Observation=Stock(Phase); if(!Observation.IsValid()) return;
            Last->SetObjectField(TEXT("stock"),Observation);
            // Project real horse/stand/rope centers into the screenshot. This
            // is only a framing gate; occlusion and appearance need PNG review.
            TArray<TSharedPtr<FJsonValue>> Points;
            const auto* Rope=C()->PackHorses()[0]->LeadRope(); FVector A,B; Rope->Anchors(A,B);
            for(const FVector& V:{C()->Steed()->GetActorLocation()+FVector(0,0,130),C()->PackHorses()[0]->GetActorLocation()+FVector(0,0,130),Dropoff+FVector(0,0,100),A,B})
            {
                FVector2D Screen;
                if(!PC()->ProjectWorldLocationToScreen(V,Screen)||Screen.X<40||Screen.X>Viewport.X-40||Screen.Y<80||Screen.Y>Viewport.Y-100)
                { Fail(TEXT("A cargo horse, stand or rope endpoint falls outside the prepared view")); return; }
                Points.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(Screen.X),MakeShared<FJsonValueNumber>(Screen.Y)}));
            }
            Last->SetArrayField(TEXT("projected_subjects"),Points);
        }
        else
        {
            const FSoraStoryNotice* Zero=nullptr;
            for(const auto& N:C()->StoryNotices()) if(N.Kind==FSoraStoryNotice::EKind::Registry&&N.Japanese.Contains(TEXT("麦 残り 0束"))&&N.English.Contains(TEXT("Barley: 0 sheaves left"))) Zero=&N;
            if(!Zero||Zero->Remaining<=0||C()->StoryNotices().Num()!=1||Completions!=1||C()->PackHorses().Num()!=0||M->Arena()->CargoStandCount()!=0)
            { Fail(TEXT("The returning real HUD lacks final zero feedback or cargo teardown")); return; }
            Last->SetStringField(TEXT("notice_ja"),Zero->Japanese); Last->SetStringField(TEXT("notice_en"),Zero->English);
            Last->SetNumberField(TEXT("notice_remaining_s"),Zero->Remaining); Last->SetNumberField(TEXT("notice_count"),C()->StoryNotices().Num());
            Last->SetNumberField(TEXT("pack_count"),C()->PackHorses().Num()); Last->SetNumberField(TEXT("stand_count"),M->Arena()->CargoStandCount());
        }
        int32 W=0,H=0; PC()->GetViewportSize(W,H); const FSoraHUDFrame Layout(*HUD.Get(),*M.Get(),W,H); FString Why;
        if(!SoraHUDPanels::BottomHUDLayoutFits(Layout,*Hero(),Why)||!SoraHUDPanels::StoryTrackerLayoutFits(Layout,Why)||
            !SoraHUDPanels::CaptionStoryLayoutFits(Layout,Why)||!SoraHUDPanels::InteractionPromptLayoutFits(Layout,Why))
        { Fail(*(TEXT("Cargo HUD layout: ")+Why)); return; }
        PendingFile=Folder/(FString(Phases[Phase])+TEXT(".png")); FScreenshotRequest::RequestScreenshot(PendingFile,true,false);
    }
    void Captured()
    {
        if(Failed||PendingFile.IsEmpty()) return;
        if(RequestFrame!=GFrameCounter||WorldTime()!=PauseWorld||IFileManager::Get().FileSize(*PendingFile)<=0)
        { Fail(TEXT("Cargo original PNG does not match its observed paused HUD frame")); return; }
        Last->SetNumberField(TEXT("screenshot_processed_frame"),double(GFrameCounter)); Frames.Add(MakeShared<FJsonValueObject>(Last));
        UE_LOG(LogTemp,Display,TEXT("SORA_CARGO_FRAME %s"),*PendingFile); PendingFile.Reset(); ++Phase;
        UGameplayStatics::SetGamePaused(M.Get(),false);
        if(Phase==1) StartHold();
        else if(Phase<4) { Prepare(Phase-1); Stage=EStage::Settle; }
    }
    void Cleanup()
    {
        if(Cleaned) return; Cleaned=true;
        if(!PendingFile.IsEmpty()) FScreenshotRequest::Reset();
        if(HUD.IsValid()) { HUD->OnReticleDrawn.Remove(DrawHandle); HUD->bShowHUD=ShowHUD; }
        FScreenshotRequest::OnScreenshotRequestProcessed().Remove(ScreenshotHandle);
        if(Events.IsValid()) { Events->OnBeatStarted.Remove(StartedHandle); Events->OnBeatCompleted.Remove(CompletedHandle); }
        bool Profiles=true,Mappings=true,Released=true;
        if(!Slot.IsEmpty()&&M.IsValid())
        {
            if(PC()&&PC()->PlayerInput)
            {
                if(Interact.IsValid()) Key(IE_Released);
                PC()->PlayerInput->FlushPressedKeys(); Released=!Interact.IsValid()||!PC()->PlayerInput->IsPressed(Interact);
                Mappings=PC()->PlayerInput->ActionMappings==Actions&&PC()->PlayerInput->AxisMappings==Axes;
                PC()->SetViewTarget(Hero());
            }
            else { Released=false; Mappings=false; }
            if(Camera.IsValid()) Camera->Destroy();
            M->SetMenuOpen(true); M->SaveSlotName=OriginalSlot; M->bCampaign=WasCampaign; M->bDeterministicPractice=WasPractice;
            C()->LoadSave(); M->ResetRound(); M->FrontEnd()->ShowTitle(); M->bEnglishSubtitles=WasEnglish;
            for(int32 I=0;I<3;++I)
            {
                const FString& Name=I==0?OriginalSlot:I==1?ControlSlot:SettingsSlot;
                const bool Existed=I==0?HadCampaign:I==1?HadControls:HadSettings;
                const auto& Before=I==0?CampaignBytes:I==1?ControlBytes:SettingsBytes; TArray<uint8> After;
                const auto Same=[&]() { return UGameplayStatics::DoesSaveGameExist(Name,0)==Existed&&(!Existed||(UGameplayStatics::LoadDataFromSlot(After,Name,0)&&Before==After)); };
                const bool Unchanged=Same(); if(I>0&&!Unchanged) { Fail(TEXT("Cargo capture modified controls/settings bytes")); Profiles=false; }
                if(!Unchanged) { if(Existed) UGameplayStatics::SaveDataToSlot(Before,Name,0); else UGameplayStatics::DeleteGameInSlot(Name,0); }
                Profiles=Same()&&Profiles;
            }
        }
        if(!Slot.IsEmpty()) UGameplayStatics::DeleteGameInSlot(Slot,0);
        const bool Deleted=Slot.IsEmpty()||!UGameplayStatics::DoesSaveGameExist(Slot,0);
        if(!Profiles||!Mappings||!Released||!Deleted) Fail(TEXT("Cargo capture failed profile/mapping/input/temporary-slot cleanup"));
        if(Folder.IsEmpty()) return;
        auto J=MakeShared<FJsonObject>(); J->SetStringField(TEXT("schema"),TEXT("sora-arena.cargo-capture.v1")); J->SetStringField(TEXT("scope"),Scope);
        J->SetBoolField(TEXT("passed"),!Failed&&Phase==4); J->SetBoolField(TEXT("prepared_checkpoint"),true); J->SetBoolField(TEXT("frozen_ai"),true);
        J->SetBoolField(TEXT("mapped_start_dismount"),Dismounted); J->SetBoolField(TEXT("ordinary_clock"),true);
        J->SetBoolField(TEXT("profiles_preserved"),Profiles); J->SetBoolField(TEXT("mappings_preserved"),Mappings);
        J->SetBoolField(TEXT("inputs_released"),Released); J->SetBoolField(TEXT("temporary_slot_deleted"),Deleted);
        J->SetArrayField(TEXT("viewport"),{MakeShared<FJsonValueNumber>(Viewport.X),MakeShared<FJsonValueNumber>(Viewport.Y)});
        J->SetArrayField(TEXT("frames"),Frames); J->SetArrayField(TEXT("holds"),Holds); J->SetArrayField(TEXT("preparations"),Preparations);
        if(Terminal.IsValid()) J->SetObjectField(TEXT("terminal_before_teardown"),Terminal);
        J->SetNumberField(TEXT("cargo_completions"),Completions); J->SetNumberField(TEXT("cinematic_elapsed_ms"),CinemaElapsedMs);
        J->SetNumberField(TEXT("cinematic_world_s"),CinemaWorldEnd-CinemaWorldStart); J->SetNumberField(TEXT("cinematic_wall_s"),CinemaWallEnd-CinemaWallStart);
        J->SetNumberField(TEXT("cinematic_start_world_s"),CinemaWorldStart); J->SetNumberField(TEXT("cinematic_start_wall_s"),CinemaWallStart-BeganWall);
        J->SetNumberField(TEXT("cinematic_end_world_s"),CinemaWorldEnd); J->SetNumberField(TEXT("cinematic_end_wall_s"),CinemaWallEnd-BeganWall);
        FString Text; FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&Text));
        if(!FFileHelper::SaveStringToFile(Text,*(Folder/TEXT("capture.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)) Fail(TEXT("Could not write cargo original-frame observations"));
    }
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCargoCaptureTest,"SoraCapture.Cargo.Transfer",EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCargoCaptureTest::RunTest(const FString& Parameters)
{
    (void)Parameters; FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<SoraCargoCapture::FRun>(*this)); return true;
}
#endif
