#if WITH_DEV_AUTOMATION_TESTS
#include "SoraCatalog.h"
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "Misc/AutomationTest.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "RHI.h"
#include "Tests/AutomationCommon.h"
#include "UnrealClient.h"

// Deliberately outside SoraArena: this is a single-test fresh process, before
// any navigation tour or input injection. Both packaged runners supply an
// empty UserDir. Never normalize the screen, focus, menu or input here.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSoraFreshStartupRenderedTest,
    "SoraStartup.RenderedFreshLaunch",EAutomationTestFlags::ClientContext|EAutomationTestFlags::EngineFilter)
bool FSoraFreshStartupRenderedTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    FString Commands;
    FParse::Value(FCommandLine::Get(),TEXT("ExecCmds="),Commands);
    if(!TestEqual(TEXT("Startup qualification runs alone in a fresh process"),Commands,
        FString(TEXT("Automation RunTests SoraStartup.RenderedFreshLaunch;Quit")))||
        !TestFalse(TEXT("Startup qualification requires actual rendering"),GUsingNullRHI)) return false;
    UWorld* World=nullptr;
    for(const FWorldContext& Context:GEngine->GetWorldContexts())
        if(Context.WorldType==EWorldType::Game&&Context.World()) World=Context.World();
    auto* Mode=World?Cast<ASoraGameMode>(World->GetAuthGameMode()):nullptr;
    if(!TestNotNull(TEXT("The untouched launch has the production game mode"),Mode)||
        !TestNotNull(TEXT("The untouched launch has a front end"),Mode->FrontEnd())||
        !TestTrue(TEXT("The untouched launch starts on Title"),Mode->FrontEnd()->Screen()==SoraUI::EScreen::Title)||
        !TestTrue(TEXT("Slate is initialized"),FSlateApplication::IsInitialized())) return false;
    const TWeakObjectPtr<ASoraGameMode> WeakMode=Mode;
    // Allow the production next-tick world preparation and Slate layout to
    // settle. A failure remains a failure; there is no retry/reset to Title.
    ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(4.f));
    const TSharedRef<FString> Shot=MakeShared<FString>();
    ADD_LATENT_AUTOMATION_COMMAND(FFunctionLatentCommand([this,WeakMode,Shot]()
    {
        auto* Live=WeakMode.Get();
        auto* Front=Live?Live->FrontEnd():nullptr;
        auto* Viewport=Live?Live->GetWorld()->GetGameViewport():nullptr;
        const auto Focused=FSlateApplication::Get().GetKeyboardFocusedWidget();
        const bool Title=Front&&Front->IsOpen()&&Front->Screen()==SoraUI::EScreen::Title;
        const bool Focus=Focused.IsValid()&&Focused->GetType()==FName(TEXT("SSoraFrontEnd"));
        TestTrue(TEXT("Title remains open without navigation normalization"),Title);
        TestTrue(TEXT("The production front end holds keyboard focus"),Focus);
        TestTrue(TEXT("Production menu state is open"),Live&&Live->bMenu);
        TestTrue(TEXT("The catalog loaded successfully"),FSoraCatalog::Get().IsReady());
        TestTrue(TEXT("The production arena was prepared"),Live&&Live->Arena());
        TestTrue(TEXT("The prepared world is paused behind Title"),Live&&Live->GetWorld()->IsPaused());
        TestTrue(TEXT("The untouched title has no error banner"),Front&&Front->BannerJapanese.IsEmpty()&&Front->BannerEnglish.IsEmpty());
        TestTrue(TEXT("The title widget has rendered geometry"),Focus&&Focused->GetVisibility().IsVisible()&&
            Focused->GetCachedGeometry().GetLocalSize().X>0.f&&Focused->GetCachedGeometry().GetLocalSize().Y>0.f);
        FVector2D Size=FVector2D::ZeroVector;
        if(Viewport) Viewport->GetViewportSize(Size);
        TestTrue(TEXT("The production viewport has a nonzero rendered extent"),Viewport&&Size.X>0&&Size.Y>0);
        if(HasAnyErrors()) return true;
        const int32 Width=FMath::RoundToInt(Size.X),Height=FMath::RoundToInt(Size.Y);
        *Shot=FPaths::ProjectSavedDir()/TEXT("Screenshots/SoraStartup")/
            FString::Printf(TEXT("%dx%d/01_Title.png"),Width,Height);
        FScreenshotRequest::RequestScreenshot(*Shot,true,false);
        AddInfo(FString::Printf(TEXT("SORA_FRESH_STARTUP title=1 menu=1 focus=SSoraFrontEnd catalog=1 arena=1 paused=1 rendered=1 width=%d height=%d"),Width,Height));
        return true;
    }));
    const TSharedRef<double> Deadline=MakeShared<double>(0.0);
    ADD_LATENT_AUTOMATION_COMMAND(FFunctionLatentCommand([this,Shot,Deadline]()
    {
        if(Shot->IsEmpty()) return true;
        if(IFileManager::Get().FileSize(**Shot)>0) return true;
        const double Now=FPlatformTime::Seconds();
        if(*Deadline==0.0) *Deadline=Now+30.0;
        if(Now<*Deadline) return false;
        AddError(TEXT("The untouched rendered title screenshot was not written within 30 seconds"));
        return true;
    }));
    return true;
}
#endif
