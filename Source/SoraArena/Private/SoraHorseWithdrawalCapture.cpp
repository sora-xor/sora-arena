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
#include "SoraHorseWithdrawalRules.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraWorldBuilder.h"
#include "AssetCompilingManager.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
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

// A prepared checkpoint and observer camera, then the actual 150-second
// defense clock and living survivors' ordinary navigation. Combat is frozen
// only until withdrawal; no clock, task, actor position or arrival is written.
// Original live HUD frames require separate pixel review, not art acceptance.
namespace SoraWithdrawalCapture
{
namespace R=SoraHorseWithdrawalRules;
using FJson=TSharedPtr<FJsonObject>;
const TCHAR* Phases[]={TEXT("retreat-bark"),TEXT("walking"),TEXT("gate-clear"),TEXT("arrival-detail")};
constexpr int32 PhaseCount=UE_ARRAY_COUNT(Phases);
const TCHAR* Scope=TEXT("prepared checkpoint/cameras; combat frozen during real defense timer; live survivor navigation, three bilingual HUD frames and one HUD-hidden arrival detail; not ordinary defense or art acceptance");
void Vector(FJson J,const TCHAR* Name,const FVector& V)
{ J->SetArrayField(Name,{MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)}); }
bool AtApproach(const ASoraEnemy& Enemy)
{
    const FVector At=Enemy.GetActorLocation();
    return Enemy.GetCharacterMovement()->IsMovingOnGround()&&
        FMath::Abs(At.Z-Enemy.GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-R::GoalZ)<=R::FloorToleranceCm&&
        FVector::DistSquared2D(At,FVector(R::GoalX,R::GoalY,R::GoalZ))<=FMath::Square(double(R::ArrivalCm));
}
class FRun final:public IAutomationLatentCommand
{
public:
    explicit FRun(FAutomationTestBase& In):Test(In) {}
    ~FRun() { Cleanup(); }
    bool Update() override
    {
        if(!Started) { Started=true; Begin(); }
        if(Failed||Completed) { Cleanup(); return true; }
        const double Now=FPlatformTime::Seconds();
        if(Now-BeganWall>300) { Fail(TEXT("Withdrawal capture exceeded 300 seconds")); return false; }
        if(!M.IsValid()||!Hero()||!PC()||!C()||!OrdinaryClock()||M->bDefeated)
        { Fail(TEXT("Withdrawal capture lost the ordinary live world")); return false; }
        if(C()->ActiveBeat()!=5) { Fail(TEXT("Defense changed before observed completion")); return false; }
        if(!Released)
        {
            if(!C()->HorseWithdrawalActive())
            {
                for(TActorIterator<ASoraEnemy> It(M->GetWorld());It;++It) if(It->IsAlive()) FreezeBody(**It,true);
                return false;
            }
            DefenseMs=C()->TaskProgress().ElapsedMs;
            if(DefenseMs<150000||Now-BeganWall<149||WorldTime()-BeganWorld<149)
            { Fail(TEXT("Withdrawal began without the real defense duration")); return false; }
            for(TActorIterator<ASoraEnemy> It(M->GetWorld());It;++It) if(It->IsAlive()&&!It->IsActorBeingDestroyed())
            {
                if(!It->IsCampaignWithdrawing()) { Fail(TEXT("A survivor has no actual withdrawal assignment")); return false; }
                Survivors.Add(*It); Previous.Add(It->GetActorLocation()); FreezeBody(**It,false);
            }
            if(Survivors.Num()!=6) { Fail(TEXT("Prepared defense did not retain six actual pod arrivals")); return false; }
            DownBefore=Down(); Released=true; RetreatWorld=WorldTime(); RetreatWall=Now;
        }
        for(int32 I=0;I<Survivors.Num();++I)
        {
            const auto* E=Survivors[I].Get();
            if(!E||!E->IsAlive()||!E->IsCampaignWithdrawing()) { Fail(TEXT("A captured survivor disappeared before completion")); return false; }
            Walked+=FVector::Dist2D(Previous[I],E->GetActorLocation()); Previous[I]=E->GetActorLocation();
        }
        if(Down()!=DownBefore||C()->TaskProgress().ElapsedMs!=DefenseMs)
        { Fail(TEXT("Withdrawal changed kill credit or the won defense clock")); return false; }
        const auto* Cue=C()->CurrentDialogueCue();
        if(Cue&&Cue->Id==TEXT("ch02.b06.kohagi.006")&&ClearWorld<0)
        { ClearWorld=WorldTime(); ClearWall=Now; }
        if(Phase==3)
        {
            if(!DetailCameraApplied)
            {
                // The three overview originals retain the ordinary HUD. Only
                // this extra detail hides it; no survivor or clock is changed.
                SetCamera(FVector(-1600,900,500),FVector(-2280,0,90),50.f);
                HUD->bShowHUD=false; DetailCameraApplied=true; DetailCameraFrame=GFrameCounter;
            }
        }
        return false;
    }
private:
    FAutomationTestBase& Test;
    TWeakObjectPtr<ASoraGameMode> M;
    TWeakObjectPtr<ASoraHUD> HUD;
    TWeakObjectPtr<USoraGameEvents> Events;
    TWeakObjectPtr<ACameraActor> Camera;
    TWeakObjectPtr<UGameViewportClient> GameViewport;
    TArray<TWeakObjectPtr<ASoraEnemy>> Survivors;
    TArray<FVector> Previous;
    TArray<TSharedPtr<FJsonValue>> Frames;
    FJson Last;
    FString Slot,OriginalSlot,ControlSlot,SettingsSlot,Folder,PendingFile;
    TArray<uint8> CampaignBytes,ControlBytes,SettingsBytes;
    TArray<FInputActionKeyMapping> Actions;
    TArray<FInputAxisKeyMapping> Axes;
    FDelegateHandle DrawHandle,DetailDrawHandle,ScreenshotHandle,CompleteHandle,ShotHandle;
    FVector2D Viewport;
    bool Started=false,Failed=false,Cleaned=false,Released=false,Completed=false,ShowHUD=true;
    bool DetailCameraApplied=false;
    bool WasCampaign=false,WasPractice=false,WasEnglish=true,HadCampaign=false,HadControls=false,HadSettings=false;
    int32 Phase=0,DefenseMs=0,DownBefore=0,DownAtCompletion=0,Completions=0,Shots=0;
    uint64 RequestFrame=0;
    uint64 DetailCameraFrame=0;
    double BeganWall=0,BeganWorld=0,RetreatWorld=0,RetreatWall=0,ClearWorld=-1,ClearWall=-1,CompleteWorld=-1,CompleteWall=-1,Walked=0;
    ASoraPlayerCharacter* Hero() const { return M.IsValid()?M->Hero():nullptr; }
    APlayerController* PC() const { return Hero()?Cast<APlayerController>(Hero()->GetController()):nullptr; }
    USoraCampaignDirector* C() const { return M.IsValid()?M->Campaign():nullptr; }
    double WorldTime() const { return M->GetWorld()->GetTimeSeconds(); }
    int Down() const { const auto& S=C()->TaskProgress(); return S.Down[0]+S.Down[1]+S.Down[2]; }
    void SetCamera(const FVector& Eye,const FVector& At,float FOV)
    {
        Camera->SetActorLocation(Eye); Camera->SetActorRotation((At-Eye).Rotation());
        Camera->GetCameraComponent()->SetFieldOfView(FOV);
    }
    void Fail(const TCHAR* Why) { Test.AddError(Why); Failed=true; }
    bool OrdinaryClock(bool AllowPause=false) const
    {
        return (AllowPause||!M->GetWorld()->IsPaused())&&!FApp::UseFixedTimeStep()&&!GEngine->bUseFixedFrameRate&&
            FMath::IsNearlyEqual(M->GetWorld()->GetWorldSettings()->GetEffectiveTimeDilation(),1.f)&&
            FMath::IsNearlyEqual(Hero()->CustomTimeDilation,1.f);
    }
    void FreezeBody(ASoraEnemy& E,bool Frozen)
    {
        E.SetActorTickEnabled(!Frozen); E.GetCharacterMovement()->StopMovementImmediately();
        E.GetCharacterMovement()->SetComponentTickEnabled(!Frozen);
        if(auto* Brain=E.GetController()) Brain->SetActorTickEnabled(!Frozen);
    }
    void Begin()
    {
        BeganWall=FPlatformTime::Seconds();
        for(const auto& Context:GEngine->GetWorldContexts())
            if(Context.WorldType==EWorldType::Game&&Context.World()) M=Cast<ASoraGameMode>(Context.World()->GetAuthGameMode());
        if(!M.IsValid()||!PC()||!PC()->PlayerInput||!M->GetWorld()->GetGameViewport()||!OrdinaryClock(true))
        { Fail(TEXT("Withdrawal capture requires an ordinary rendering game")); return; }
        M->GetWorld()->GetGameViewport()->GetViewportSize(Viewport);
        if(Viewport!=FVector2D(1280,720)&&Viewport!=FVector2D(1920,1080))
        { Fail(TEXT("Withdrawal capture requires 1280x720 or 1920x1080")); return; }
        HUD=Cast<ASoraHUD>(PC()->GetHUD()); if(!HUD.IsValid()) { Fail(TEXT("Withdrawal capture needs the real HUD")); return; }
        ShowHUD=HUD->bShowHUD; WasCampaign=M->bCampaign; WasPractice=M->bDeterministicPractice; WasEnglish=M->bEnglishSubtitles;
        OriginalSlot=M->SaveSlotName; ControlSlot=M->ControlSlotName; SettingsSlot=M->SettingsSlotName;
        HadCampaign=UGameplayStatics::DoesSaveGameExist(OriginalSlot,0); HadControls=UGameplayStatics::DoesSaveGameExist(ControlSlot,0);
        HadSettings=UGameplayStatics::DoesSaveGameExist(SettingsSlot,0);
        if((HadCampaign&&!UGameplayStatics::LoadDataFromSlot(CampaignBytes,OriginalSlot,0))||
            (HadControls&&!UGameplayStatics::LoadDataFromSlot(ControlBytes,ControlSlot,0))||
            (HadSettings&&!UGameplayStatics::LoadDataFromSlot(SettingsBytes,SettingsSlot,0)))
        { Fail(TEXT("Could not preserve withdrawal capture profiles")); return; }
        Actions=PC()->PlayerInput->ActionMappings; Axes=PC()->PlayerInput->AxisMappings;
        const FString Id=FGuid::NewGuid().ToString(EGuidFormats::Digits); Slot=TEXT("SoraWithdrawal_")+Id;
        Folder=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Screenshots/SoraWithdrawal")/
            FString::Printf(TEXT("%dx%d"),int32(Viewport.X),int32(Viewport.Y))/Id);
        IFileManager::Get().MakeDirectory(*Folder,true);
        auto* Save=NewObject<USoraSaveGame>();
        if(!USoraCampaignDirector::SeedCheckpoint(*Save,1,5)||!UGameplayStatics::SaveGameToSlot(Save,Slot,0))
        { Fail(TEXT("Could not seed isolated ch02.b06")); return; }
        M->SetMenuOpen(true); M->SaveSlotName=Slot; M->bCampaign=true; M->bDeterministicPractice=false;
        if(!C()->LoadSave()) { Fail(TEXT("Could not load isolated ch02.b06")); return; }
        M->ResetRound(); M->BeginRound(); M->bEnglishSubtitles=true; HUD->bShowHUD=true; BeganWorld=WorldTime();
        Camera=M->GetWorld()->SpawnActor<ACameraActor>();
        if(!Camera.IsValid()) { Fail(TEXT("Could not create withdrawal review camera")); return; }
        SetCamera(FVector(-500,-3400,1900),FVector(-500,0,100),75.f); PC()->SetViewTarget(Camera.Get());
        DrawHandle=HUD->OnReticleDrawn.AddRaw(this,&FRun::Drawn);
        GameViewport=M->GetWorld()->GetGameViewport();
        DetailDrawHandle=GameViewport->OnDrawn().AddRaw(this,&FRun::DetailDrawn);
        ScreenshotHandle=FScreenshotRequest::OnScreenshotRequestProcessed().AddRaw(this,&FRun::Captured);
        Events=USoraGameEvents::Get(M.Get()); if(!Events.IsValid()) { Fail(TEXT("Withdrawal event bus is unavailable")); return; }
        ShotHandle=Events->OnWeaponFired.AddLambda([this](const FSoraWeaponFiredEvent& E) {
            if(Released&&Survivors.ContainsByPredicate([&](const auto& W){return W.Get()==E.Shooter.Get();})) ++Shots;
        });
        CompleteHandle=Events->OnBeatCompleted.AddLambda([this](const FSoraBeatEvent& E) {
            if(E.ChapterId!=1||E.BeatIndex!=5) return;
            ++Completions; DownAtCompletion=Down(); CompleteWorld=WorldTime(); CompleteWall=FPlatformTime::Seconds();
            bool Arrived=Survivors.Num()==6;
            for(const auto& W:Survivors) Arrived&=W.IsValid()&&W->IsAlive()&&AtApproach(*W.Get());
            if(!Released||Phase!=PhaseCount||Completions!=1||Shots!=0||Down()!=DownBefore||!Arrived||ClearWorld<0||
                CompleteWorld-ClearWorld<2.5||CompleteWall-ClearWall<2.4)
                Fail(TEXT("Withdrawal completed without its captured real arrivals and full gate-clear call"));
            Completed=true;
        });
    }
    void Drawn(const FVector2D& Center)
    {
        (void)Center;
        if(Phase<3) CaptureFrame();
    }
    void DetailDrawn()
    {
        // This viewport event runs even with the HUD hidden, inside the same
        // draw that ProcessScreenShots saves. Latent Update runs outside it.
        if(Phase==3&&DetailCameraApplied&&GFrameCounter>DetailCameraFrame+1) CaptureFrame();
    }
    void CaptureFrame()
    {
        if(Failed||!Released||Phase>=PhaseCount||!PendingFile.IsEmpty()) return;
        const auto* Cue=C()->CurrentDialogueCue();
        if(Phase==0&&(!Cue||Cue->Id!=TEXT("ch02.b02.enforcer.009"))) return;
        if(Phase==1&&(WorldTime()-RetreatWorld<1.5||Walked<1000)) return;
        if(Phase>=2&&(!Cue||Cue->Id!=TEXT("ch02.b06.kohagi.006"))) return;
        const bool WithHUD=Phase<3;
        if(!OrdinaryClock()||M->bMenu||HUD->bShowHUD!=WithHUD||!M->bEnglishSubtitles||C()->ActiveBeat()!=5)
        { Fail(TEXT("Withdrawal frame lost its live presentation state")); return; }
        const APlayerCameraManager* View=PC()->PlayerCameraManager;
        if(!View||!View->GetCameraLocation().Equals(Camera->GetActorLocation(),.01)||
            !View->GetCameraRotation().Equals(Camera->GetActorRotation(),.001)||
            !FMath::IsNearlyEqual(View->GetFOVAngle(),Camera->GetCameraComponent()->FieldOfView,.001f))
        { Fail(TEXT("Withdrawal rendered camera has not reached the prepared view")); return; }
        if(WithHUD)
        {
            int32 W=0,H=0; PC()->GetViewportSize(W,H); const FSoraHUDFrame Layout(*HUD.Get(),*M.Get(),W,H); FString Why;
            if(!SoraHUDPanels::BottomHUDLayoutFits(Layout,*Hero(),Why)||!SoraHUDPanels::StoryTrackerLayoutFits(Layout,Why)||
                !SoraHUDPanels::CaptionStoryLayoutFits(Layout,Why)) { Fail(*(TEXT("Withdrawal HUD: ")+Why)); return; }
        }
        Last=MakeShared<FJsonObject>(); Last->SetStringField(TEXT("phase"),Phases[Phase]);
        Last->SetStringField(TEXT("file"),FString(Phases[Phase])+TEXT(".png"));
        Last->SetStringField(TEXT("cue"),Cue?Cue->Id:TEXT(""));
        Last->SetNumberField(TEXT("request_frame"),double(GFrameCounter)); RequestFrame=GFrameCounter;
        Last->SetNumberField(TEXT("world_s"),WorldTime()); Last->SetNumberField(TEXT("wall_s"),FPlatformTime::Seconds()-BeganWall);
        Last->SetNumberField(TEXT("walked_cm"),Walked); Last->SetNumberField(TEXT("defense_ms"),C()->TaskProgress().ElapsedMs);
        Last->SetBoolField(TEXT("paused"),false); Last->SetBoolField(TEXT("hud_drawn"),WithHUD); Last->SetBoolField(TEXT("english"),true);
        Vector(Last,TEXT("camera"),View->GetCameraLocation());
        Vector(Last,TEXT("camera_rotation"),FVector(View->GetCameraRotation().Pitch,View->GetCameraRotation().Yaw,View->GetCameraRotation().Roll));
        Last->SetNumberField(TEXT("camera_fov"),View->GetFOVAngle());
        TArray<TSharedPtr<FJsonValue>> People;
        for(const auto& Weak:Survivors)
        {
            const auto* Enemy=Weak.Get();
            if(!Enemy||!Enemy->IsAlive()||(Phase>=2&&!AtApproach(*Enemy))) { Fail(TEXT("Withdrawal frame has missing/unarrived survivors")); return; }
            FVector2D Screen;
            if(!PC()->ProjectWorldLocationToScreen(Enemy->GetActorLocation(),Screen)||Screen.X<25||Screen.X>Viewport.X-25||Screen.Y<60||Screen.Y>Viewport.Y-100)
            { Fail(TEXT("A real withdrawing survivor is outside the prepared view")); return; }
            auto J=MakeShared<FJsonObject>(); J->SetStringField(TEXT("actor"),Enemy->GetName());
            Vector(J,TEXT("position"),Enemy->GetActorLocation());
            J->SetNumberField(TEXT("feet_z"),Enemy->GetActorLocation().Z-Enemy->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
            J->SetBoolField(TEXT("grounded"),Enemy->GetCharacterMovement()->IsMovingOnGround()); J->SetBoolField(TEXT("at_approach"),AtApproach(*Enemy));
            J->SetArrayField(TEXT("screen"),{MakeShared<FJsonValueNumber>(Screen.X),MakeShared<FJsonValueNumber>(Screen.Y)});
            People.Add(MakeShared<FJsonValueObject>(J));
        }
        Last->SetArrayField(TEXT("survivors"),People);
        PendingFile=Folder/(FString(Phases[Phase])+TEXT(".png")); FScreenshotRequest::RequestScreenshot(PendingFile,true,false);
    }
    void Captured()
    {
        if(Failed||PendingFile.IsEmpty()) return;
        if(RequestFrame!=GFrameCounter)
        { Fail(*FString::Printf(TEXT("Withdrawal %s frame mismatch: request %llu, processed %llu"),Phases[Phase],RequestFrame,GFrameCounter)); return; }
        if(!OrdinaryClock()||IFileManager::Get().FileSize(*PendingFile)<=0)
        { Fail(TEXT("Withdrawal original PNG lost its ordinary clock or saved bytes")); return; }
        Last->SetNumberField(TEXT("processed_frame"),double(GFrameCounter)); Frames.Add(MakeShared<FJsonValueObject>(Last));
        UE_LOG(LogTemp,Display,TEXT("SORA_WITHDRAWAL_FRAME %s"),*PendingFile); PendingFile.Reset(); ++Phase;
        if(Phase==PhaseCount) HUD->bShowHUD=true;
    }
    void Cleanup()
    {
        if(Cleaned) return; Cleaned=true;
        if(!PendingFile.IsEmpty()) FScreenshotRequest::Reset();
        if(HUD.IsValid()) { HUD->OnReticleDrawn.Remove(DrawHandle); HUD->bShowHUD=ShowHUD; }
        if(GameViewport.IsValid()) GameViewport->OnDrawn().Remove(DetailDrawHandle);
        FScreenshotRequest::OnScreenshotRequestProcessed().Remove(ScreenshotHandle);
        if(Events.IsValid()) { Events->OnBeatCompleted.Remove(CompleteHandle); Events->OnWeaponFired.Remove(ShotHandle); }
        bool Profiles=true,Mappings=true;
        if(!Slot.IsEmpty()&&M.IsValid())
        {
            if(PC()&&PC()->PlayerInput)
            { PC()->PlayerInput->FlushPressedKeys(); Mappings=PC()->PlayerInput->ActionMappings==Actions&&PC()->PlayerInput->AxisMappings==Axes; PC()->SetViewTarget(Hero()); }
            else Mappings=false;
            if(Camera.IsValid()) Camera->Destroy();
            M->SetMenuOpen(true); M->SaveSlotName=OriginalSlot; M->bCampaign=WasCampaign; M->bDeterministicPractice=WasPractice;
            C()->LoadSave(); M->ResetRound(); M->FrontEnd()->ShowTitle(); M->bEnglishSubtitles=WasEnglish;
            for(int32 I=0;I<3;++I)
            {
                const FString& Name=I==0?OriginalSlot:I==1?ControlSlot:SettingsSlot;
                const bool Existed=I==0?HadCampaign:I==1?HadControls:HadSettings;
                const auto& Before=I==0?CampaignBytes:I==1?ControlBytes:SettingsBytes; TArray<uint8> After;
                const auto Same=[&]() { return UGameplayStatics::DoesSaveGameExist(Name,0)==Existed&&(!Existed||(UGameplayStatics::LoadDataFromSlot(After,Name,0)&&Before==After)); };
                const bool Unchanged=Same(); if(I>0&&!Unchanged) { Fail(TEXT("Withdrawal capture modified controls/settings bytes")); Profiles=false; }
                if(!Unchanged) { if(Existed) UGameplayStatics::SaveDataToSlot(Before,Name,0); else UGameplayStatics::DeleteGameInSlot(Name,0); }
                Profiles=Same()&&Profiles;
            }
        }
        if(!Slot.IsEmpty()) UGameplayStatics::DeleteGameInSlot(Slot,0);
        const bool Deleted=Slot.IsEmpty()||!UGameplayStatics::DoesSaveGameExist(Slot,0);
        if(!Profiles||!Mappings||!Deleted) Fail(TEXT("Withdrawal capture failed profile/mapping/temporary-slot cleanup"));
        if(Folder.IsEmpty()) return;
        auto J=MakeShared<FJsonObject>(); J->SetStringField(TEXT("schema"),TEXT("sora-arena.withdrawal-capture.v2")); J->SetStringField(TEXT("scope"),Scope);
        J->SetBoolField(TEXT("passed"),!Failed&&Completed&&Phase==PhaseCount); J->SetBoolField(TEXT("ordinary_clock"),true);
        J->SetBoolField(TEXT("profiles_preserved"),Profiles); J->SetBoolField(TEXT("mappings_preserved"),Mappings); J->SetBoolField(TEXT("temporary_slot_deleted"),Deleted);
        J->SetArrayField(TEXT("viewport"),{MakeShared<FJsonValueNumber>(Viewport.X),MakeShared<FJsonValueNumber>(Viewport.Y)});
        J->SetArrayField(TEXT("frames"),Frames); J->SetNumberField(TEXT("completions"),Completions); J->SetNumberField(TEXT("survivor_shots"),Shots);
        J->SetNumberField(TEXT("down_before"),DownBefore); J->SetNumberField(TEXT("down_at_completion"),DownAtCompletion);
        J->SetNumberField(TEXT("defense_ms"),DefenseMs); J->SetNumberField(TEXT("defense_world_s"),RetreatWorld-BeganWorld);
        J->SetNumberField(TEXT("defense_wall_s"),RetreatWall-BeganWall); J->SetNumberField(TEXT("walked_cm"),Walked);
        J->SetNumberField(TEXT("gate_clear_world_s"),CompleteWorld-ClearWorld); J->SetNumberField(TEXT("gate_clear_wall_s"),CompleteWall-ClearWall);
        FString Text; FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&Text));
        if(!FFileHelper::SaveStringToFile(Text,*(Folder/TEXT("capture.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)) Fail(TEXT("Could not save withdrawal frame observations"));
    }
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraWithdrawalCaptureTest,"SoraCapture.HorseWithdrawal.Live",EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraWithdrawalCaptureTest::RunTest(const FString& Parameters)
{
    (void)Parameters; FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<SoraWithdrawalCapture::FRun>(*this)); return true;
}
#endif
