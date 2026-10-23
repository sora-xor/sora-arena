#include "SoraGameMode.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "SoraCampaignDirector.h"
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraPlayerCharacter.h"
#include "SoraSaveGame.h"
#include "SoraSettings.h"
#include "SoraWoodRules.h"
#include "UI/SSoraFrontEnd.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Input/Events.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

// Prepared discovery ledgers, normal Slate navigation, real viewport pixels.
// This is UI evidence, not evidence that a player earned all 48 collectibles.
namespace SoraCodexCapture
{
using SoraUI::EAction;
using SoraUI::EScreen;
const TCHAR* Names[]={TEXT("empty"),TEXT("index-first"),TEXT("index-last"),TEXT("reader-standard"),
    TEXT("reader-xl-top"),TEXT("reader-xl-end"),TEXT("reader-ja-only"),TEXT("toshiya")};
class FRun final : public IAutomationLatentCommand
{
public:
    explicit FRun(FAutomationTestBase& In):Test(In) {}
    ~FRun() { Cleanup(); }
    bool Update() override
    {
        if (!Started) { Started=true; Begin(); }
        if (Failed||Step==UE_ARRAY_COUNT(Names)) { Cleanup(); return true; }
        if (FPlatformTime::Seconds()-StartedAt>90) { Fail(TEXT("Codex capture timed out")); Cleanup(); return true; }
        if (Waiting||FPlatformTime::Seconds()-ChangedAt<.8) return false;
        if (!M.IsValid()||!M->FrontEnd()||!M->GetWorld()->IsPaused()) { Fail(TEXT("Codex lost its paused live menu")); return false; }
        Capture();
        return false;
    }
private:
    FAutomationTestBase& Test;
    TWeakObjectPtr<ASoraGameMode> M;
    FString Slot,OriginalSlot,Controls,Settings,Folder,Pending;
    TArray<uint8> Bytes[3]; bool Existed[3]{};
    TArray<FInputActionKeyMapping> Actions;
    TArray<FInputAxisKeyMapping> Axes;
    TArray<TSharedPtr<FJsonValue>> Frames;
    bool Started=false,Failed=false,Cleaned=false,Waiting=false,BackedUp=false;
    bool OriginalEnglish=true,WasCampaign=false,WasPractice=false;
    SoraAccessibility::ESubtitleSize OriginalSize=SoraAccessibility::ESubtitleSize::Standard;
    int32 Step=0,LongestKey=0;
    FVector2D CaptureViewport;
    double StartedAt=0,ChangedAt=0;
    FDelegateHandle Screenshot;
    APlayerController* PC() const { return M.IsValid()&&M->Hero()?Cast<APlayerController>(M->Hero()->GetController()):nullptr; }
    USoraFrontEnd* Menu() const { return M.IsValid()?M->FrontEnd():nullptr; }
    void Fail(const TCHAR* Message) { Test.AddError(Message); Failed=true; }
    void Press(const FKey& Key)
    {
        const FKeyEvent Event(Key,FModifierKeysState(),0,false,0,0);
        FSlateApplication::Get().ProcessKeyDownEvent(Event);
        FSlateApplication::Get().ProcessKeyUpEvent(Event);
    }
    bool Choose(EAction Action,int32 Param=INDEX_NONE)
    {
        for (int32 I=0;I<=Menu()->Rows().Num();++I)
        {
            const int32 At=Menu()->Focus();
            if (Menu()->Rows().IsValidIndex(At)&&Menu()->Rows()[At].Action==Action&&
                (Param==INDEX_NONE||Menu()->Rows()[At].Param==Param)) { Press(EKeys::Enter); return true; }
            Press(EKeys::Down);
        }
        Fail(TEXT("Normal Slate navigation could not reach the requested Codex row")); return false;
    }
    bool Seed(bool Full)
    {
        auto* Save=NewObject<USoraSaveGame>();
        Save->SaveSchema=USoraSaveGame::Schema;
        Save->HighestChapter=Full?7:0;
        Save->Collectibles=Full?(int64(1)<<48)-1:0;
        Save->WoodPoiMask=Full?SoraWoodRules::All:0;
        if (!UGameplayStatics::SaveGameToSlot(Save,Slot,0)||!M->Campaign()->LoadSave())
        { Fail(TEXT("Prepared Codex ledger could not load")); return false; }
        M->FrontEnd()->ShowTitle(); Press(EKeys::Enter);
        return Choose(EAction::Codex);
    }
    void Begin()
    {
        StartedAt=ChangedAt=FPlatformTime::Seconds();
        for (const auto& Context:GEngine->GetWorldContexts())
            if (Context.WorldType==EWorldType::Game&&Context.World()) M=Cast<ASoraGameMode>(Context.World()->GetAuthGameMode());
        if (!M.IsValid()||!PC()||!PC()->PlayerInput||!M->Settings()||!M->GetWorld()->GetGameViewport()||!FSlateApplication::IsInitialized())
        { Fail(TEXT("Codex capture requires a rendering game with its live Slate front end")); return; }
        FVector2D Size; M->GetWorld()->GetGameViewport()->GetViewportSize(Size);
        if (Size!=FVector2D(1280,720)&&Size!=FVector2D(1920,1080)) { Fail(TEXT("Capture requires 1280x720 or 1920x1080")); return; }
        CaptureViewport=Size;
        OriginalSlot=M->SaveSlotName; Controls=M->ControlSlotName; Settings=M->SettingsSlotName;
        for (int32 I=0;I<3;++I)
        {
            const FString& Name=I==0?OriginalSlot:I==1?Controls:Settings;
            Existed[I]=UGameplayStatics::DoesSaveGameExist(Name,0);
            if (Existed[I]&&!UGameplayStatics::LoadDataFromSlot(Bytes[I],Name,0)) { Fail(TEXT("Could not preserve profile bytes")); return; }
        }
        BackedUp=true;
        Actions=PC()->PlayerInput->ActionMappings; Axes=PC()->PlayerInput->AxisMappings;
        OriginalEnglish=M->bEnglishSubtitles; OriginalSize=M->Settings()->SubtitleSize();
        WasCampaign=M->bCampaign; WasPractice=M->bDeterministicPractice;
        Slot=TEXT("SoraCodexCapture_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
        Folder=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Screenshots/SoraCodex")/
            FString::Printf(TEXT("%dx%d"),int32(Size.X),int32(Size.Y))/FGuid::NewGuid().ToString(EGuidFormats::Digits));
        IFileManager::Get().MakeDirectory(*Folder,true);
        M->SetMenuOpen(true); M->SaveSlotName=Slot;
        M->Settings()->SetEnglishSubtitles(true);
        M->Settings()->SetSubtitleSize(SoraAccessibility::ESubtitleSize::Standard);
        Screenshot=FScreenshotRequest::OnScreenshotRequestProcessed().AddRaw(this,&FRun::Captured);
        Seed(false);
    }
    TSharedPtr<SSoraFrontEnd> Widget()
    {
        const auto Focus=FSlateApplication::Get().GetKeyboardFocusedWidget();
        if (!Focus.IsValid()||Focus->GetTypeAsString()!=TEXT("SSoraFrontEnd"))
        { Fail(TEXT("Keyboard focus is not on the actual SSoraFrontEnd")); return nullptr; }
        return StaticCastSharedPtr<SSoraFrontEnd>(Focus);
    }
    void Capture()
    {
        auto View=Widget(); if (!View) return;
        const bool Reader=Step>=3;
        const auto ExpectedSize=Step<4?SoraAccessibility::ESubtitleSize::Standard:SoraAccessibility::ESubtitleSize::ExtraLarge;
        const auto* Selected=Menu()->SelectedCodexEntry();
        const bool RightScreen=Menu()->Screen()==(Reader?EScreen::CodexEntry:EScreen::Codex);
        const bool RightEntry=!Reader||(Selected&&Selected->Key==(Step==7?48:LongestKey));
        const bool RightLanguage=Menu()->ShowsEnglish()==(Step!=6);
        const bool RightSize=M->Settings()->SubtitleSize()==ExpectedSize;
        const bool RightCount=Menu()->CodexEntries().Num()==(Step==0?0:49);
        const bool Top=!Reader||Step==5||(Menu()->CodexScrollFraction()==0.f&&FMath::Abs(View->CodexScrollOffset())<1.f);
        const bool RightIndex=(Step!=1&&Step!=2)||(Menu()->Rows().IsValidIndex(Menu()->Focus())&&
            Menu()->Rows()[Menu()->Focus()].Action==EAction::CodexEntry&&Menu()->Rows()[Menu()->Focus()].Param==(Step==1?0:48));
        if (!RightScreen||!RightEntry||!RightLanguage||!RightSize||!RightCount||!Top||!RightIndex)
        {
            Test.AddError(FString::Printf(TEXT("Codex phase %s did not establish its actual screen/input state: screen=%d key=%d english=%d size=%d entries=%d focus=%d fraction=%.3f offset=%.3f"),
                Names[Step],int32(Menu()->Screen()),Selected?Selected->Key:-1,Menu()->ShowsEnglish(),int32(M->Settings()->SubtitleSize()),
                Menu()->CodexEntries().Num(),Menu()->Focus(),Menu()->CodexScrollFraction(),View->CodexScrollOffset()));
            Failed=true; return;
        }
        auto Record=MakeShared<FJsonObject>();
        Record->SetStringField(TEXT("name"),Names[Step]);
        Record->SetBoolField(TEXT("prepared_discoveries"),true);
        Record->SetNumberField(TEXT("request_frame"),double(GFrameCounter));
        Record->SetNumberField(TEXT("screen"),int32(Menu()->Screen()));
        Record->SetStringField(TEXT("screen_name"),Menu()->Screen()==EScreen::CodexEntry?TEXT("reader"):TEXT("index"));
        Record->SetNumberField(TEXT("focus"),Menu()->Focus());
        Record->SetNumberField(TEXT("entries"),Menu()->CodexEntries().Num());
        Record->SetBoolField(TEXT("english"),Menu()->ShowsEnglish());
        Record->SetNumberField(TEXT("text_scale"),SoraAccessibility::SubtitleScale(M->Settings()->SubtitleSize()));
        if (Menu()->Screen()==EScreen::CodexEntry)
        {
            const auto* Entry=Menu()->SelectedCodexEntry();
            if (!Entry) { Fail(TEXT("Reader lost its selected entry")); return; }
            Test.TestTrue(TEXT("Rendered reader submits the full Japanese body"),View->LinesDrawn().Contains(Entry->Body.Japanese));
            Test.TestEqual(TEXT("Rendered English body follows the selected setting"),View->LinesDrawn().Contains(Entry->Body.English),Menu()->ShowsEnglish());
            const FGeometry Clip=View->CodexViewportGeometry(), Content=View->CodexContentGeometry();
            const FVector2D Min=Clip.AbsoluteToLocal(Content.LocalToAbsolute(FVector2D::ZeroVector));
            const FVector2D Max=Clip.AbsoluteToLocal(Content.LocalToAbsolute(Content.GetLocalSize()));
            Test.TestTrue(TEXT("Reader content stays within the horizontal clip"),Min.X>=-1&&Max.X<=Clip.GetLocalSize().X+1);
            Test.TestTrue(TEXT("Reader viewport has actual positive arranged size"),Clip.GetLocalSize().X>0&&Clip.GetLocalSize().Y>0);
            if (Step==5)
            {
                Test.TestTrue(TEXT("Extra-large actual content exercises scrolling"),View->CodexScrollEnd()>1);
                Test.TestTrue(TEXT("Normal Down input reaches the actual end"),FMath::IsNearlyEqual(View->CodexScrollOffset(),View->CodexScrollEnd(),1.f));
                Test.TestTrue(TEXT("Last body line is inside the viewport at the end"),Max.Y<=Clip.GetLocalSize().Y+1&&Max.Y>=0);
            }
            const auto Back=View->RowWidget(0);
            if (!Back) { Fail(TEXT("Reader has no Back widget")); return; }
            const FGeometry Parent=View->GetCachedGeometry(), BackGeometry=Back->GetCachedGeometry();
            const FVector2D BackMin=Parent.AbsoluteToLocal(BackGeometry.LocalToAbsolute(FVector2D::ZeroVector));
            const FVector2D BackMax=Parent.AbsoluteToLocal(BackGeometry.LocalToAbsolute(BackGeometry.GetLocalSize()));
            const double ReaderBottom=Parent.AbsoluteToLocal(Clip.LocalToAbsolute(Clip.GetLocalSize())).Y;
            Test.TestTrue(TEXT("Back remains visible below the reader and within the viewport"),
                BackMin.Y>=ReaderBottom-1&&BackMax.Y<=Parent.GetLocalSize().Y+1&&BackMax.X<=Parent.GetLocalSize().X+1&&BackGeometry.GetLocalSize().Y>0);
            Record->SetStringField(TEXT("entry_id"),Entry->Id);
            Record->SetNumberField(TEXT("entry_key"),Entry->Key);
            Record->SetNumberField(TEXT("scroll_offset"),View->CodexScrollOffset());
            Record->SetNumberField(TEXT("scroll_end"),View->CodexScrollEnd());
            Record->SetNumberField(TEXT("content_bottom"),Max.Y);
            Record->SetNumberField(TEXT("viewport_height"),Clip.GetLocalSize().Y);
        }
        Frames.Add(MakeShared<FJsonValueObject>(Record));
        Pending=Folder/(FString(Names[Step])+TEXT(".png")); Waiting=true;
        FScreenshotRequest::RequestScreenshot(Pending,true,false);
    }
    void Captured()
    {
        if (!Waiting) return;
        if (IFileManager::Get().FileSize(*Pending)<=0) { Fail(TEXT("Original Codex screenshot was not written")); return; }
        Frames.Last()->AsObject()->SetNumberField(TEXT("screenshot_processed_frame"),double(GFrameCounter));
        Frames.Last()->AsObject()->SetStringField(TEXT("file"),FPaths::GetCleanFilename(Pending));
        UE_LOG(LogTemp,Display,TEXT("SORA_CODEX_FRAME %s"),*Pending);
        Pending.Reset(); Waiting=false; ++Step;
        if (Step==UE_ARRAY_COUNT(Names)) return;
        if (Step==1)
        {
            if (!Seed(true)) return;
            int32 Length=-1;
            for (const auto& Entry:Menu()->CodexEntries())
            {
                const int32 Candidate=Entry.Body.Japanese.Len()*2+Entry.Body.English.Len();
                if (Entry.Key<48&&Candidate>Length) { Length=Candidate; LongestKey=Entry.Key; }
            }
        }
        if (Step==2)
        {
            // Up from the first entry wraps to Back; Up again reaches Toshiya.
            Press(EKeys::Gamepad_DPad_Up); Press(EKeys::Gamepad_DPad_Up);
            Test.TestEqual(TEXT("Pad reaches the final index entry"),Menu()->Rows()[Menu()->Focus()].Param,48);
        }
        if (Step==3) Choose(EAction::CodexEntry,LongestKey);
        if (Step==4)
        {
            Press(EKeys::Escape); Press(EKeys::Escape);
            if (!Choose(EAction::Settings)||!Choose(EAction::OpenSubtitles)||!Choose(EAction::SubtitleSize)) return;
            Press(EKeys::Right); // Standard -> Large on Accept, then Extra large.
            Press(EKeys::Escape); Press(EKeys::Escape);
            if (!Choose(EAction::Codex)||!Choose(EAction::CodexEntry,LongestKey)) return;
            Test.TestEqual(TEXT("Normal settings input selects extra-large text"),M->Settings()->SubtitleSize(),SoraAccessibility::ESubtitleSize::ExtraLarge);
        }
        if (Step==5)
        {
            // The actual hit-tested wheel must bubble from the reader to its
            // menu handler, before pad input continues to the actual end.
            auto View=Widget(); if (!View) return;
            const FVector2D At=View->CodexViewportGeometry().GetAbsolutePositionAtCoordinates(FVector2D(.5,.5));
            const FPointerEvent Wheel(0,At,At,TSet<FKey>(),EKeys::Invalid,-1.f,FModifierKeysState());
            FSlateApplication::Get().ProcessMouseWheelOrGestureEvent(Wheel,nullptr);
            if (!Test.TestTrue(TEXT("A real wheel event advances the reader"),Menu()->CodexScrollFraction()>0.f)) { Failed=true; return; }
            for (int32 I=0;I<6;++I) Press(EKeys::Gamepad_DPad_Down);
        }
        if (Step==6) { Press(EKeys::F10); for (int32 I=0;I<6;++I) Press(EKeys::Up); }
        if (Step==7) { Press(EKeys::F10); Press(EKeys::Escape); Choose(EAction::CodexEntry,48); }
        ChangedAt=FPlatformTime::Seconds();
    }
    void Cleanup()
    {
        if (Cleaned) return; Cleaned=true;
        if (!Pending.IsEmpty()) FScreenshotRequest::Reset();
        FScreenshotRequest::OnScreenshotRequestProcessed().Remove(Screenshot);
        if (BackedUp&&M.IsValid())
        {
            if (PC()&&PC()->PlayerInput)
            {
                PC()->PlayerInput->FlushPressedKeys();
                Test.TestTrue(TEXT("Capture preserves all action and axis mappings"),PC()->PlayerInput->ActionMappings==Actions&&PC()->PlayerInput->AxisMappings==Axes);
                for (const FKey& Key:{EKeys::Enter,EKeys::Up,EKeys::Down,EKeys::Escape,EKeys::Gamepad_DPad_Up,EKeys::Gamepad_DPad_Down})
                    Test.TestFalse(TEXT("Capture leaves no held menu inputs"),PC()->PlayerInput->IsPressed(Key));
            }
            M->SaveSlotName=OriginalSlot; M->bCampaign=WasCampaign; M->bDeterministicPractice=WasPractice;
            M->Campaign()->LoadSave(); M->ResetRound();
            M->Settings()->SetEnglishSubtitles(OriginalEnglish); M->Settings()->SetSubtitleSize(OriginalSize);
            M->FrontEnd()->ShowTitle();
            for (int32 I=0;I<3;++I)
            {
                const FString& Name=I==0?OriginalSlot:I==1?Controls:Settings;
                if (Existed[I]) UGameplayStatics::SaveDataToSlot(Bytes[I],Name,0);
                else if (UGameplayStatics::DoesSaveGameExist(Name,0)) UGameplayStatics::DeleteGameInSlot(Name,0);
                TArray<uint8> After;
                Test.TestTrue(TEXT("Capture restores original profile bytes and existence"),UGameplayStatics::DoesSaveGameExist(Name,0)==Existed[I]&&
                    (!Existed[I]||(UGameplayStatics::LoadDataFromSlot(After,Name,0)&&After==Bytes[I])));
            }
        }
        if (!Slot.IsEmpty()) UGameplayStatics::DeleteGameInSlot(Slot,0);
        if (!Folder.IsEmpty())
        {
            auto Report=MakeShared<FJsonObject>(); Report->SetArrayField(TEXT("frames"),Frames);
            Report->SetStringField(TEXT("schema"),TEXT("sora-arena.codex-capture.v1"));
            Report->SetStringField(TEXT("scope"),TEXT("prepared Codex discovery ledger; not playthrough or art acceptance"));
            Report->SetBoolField(TEXT("prepared_discoveries"),true);
            Report->SetNumberField(TEXT("frame_count"),Frames.Num());
            Report->SetArrayField(TEXT("viewport"),{MakeShared<FJsonValueNumber>(CaptureViewport.X),MakeShared<FJsonValueNumber>(CaptureViewport.Y)});
            Report->SetBoolField(TEXT("passed"),!Failed&&!Test.HasAnyErrors()&&Step==UE_ARRAY_COUNT(Names));
            FString Json; FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
            Test.TestTrue(TEXT("Capture writes its source-observation report"),FFileHelper::SaveStringToFile(Json,*(Folder/TEXT("capture.json"))));
            Test.AddInfo(FString::Printf(TEXT("Codex originals and report: %s"),*Folder));
        }
    }
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraCodexCaptureTest,"SoraCapture.Codex.Live",
    EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraCodexCaptureTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    FAutomationTestFramework::Get().EnqueueLatentCommand(MakeShared<SoraCodexCapture::FRun>(*this));
    return true;
}
#endif
