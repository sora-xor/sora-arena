#include "UI/SoraFrontEndInputTrace.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFrontEnd.h"
#include "SoraGameMode.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "HAL/PlatformStackWalk.h"
#include "Misc/AutomationTest.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Templates/UnrealTemplate.h"

namespace SoraFrontEndInputTrace
{
namespace
{
// All scopes and model changes are game-thread only. No context survives its
// synchronous call, including early returns and nested model commands.
const FScope* Current = nullptr;
constexpr uint32 MaxTransitions = 8;
constexpr uint32 MaxFrames = 16;
uint32 Transitions = 0;
bool bLogging = false;
bool Enabled()
{
    static const bool bRequested = FParse::Param(FCommandLine::Get(), TEXT("SoraTraceFrontEndInput"));
    return bRequested && IsInGameThread();
}
bool IsViewportModel(const USoraFrontEnd& Front)
{
    const UWorld* World = Front.Mode().GetWorld();
    const UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr;
    return Front.Mode().FrontEnd() == &Front && World && World->WorldType == EWorldType::Game &&
        Viewport && Viewport->GetWorld() == World;
}
}

FScope::FScope(const USoraFrontEnd* Front, const TCHAR* Route, FName Key, bool bRepeat, int32 Command)
{
    if (!Enabled() || !Front || !IsViewportModel(*Front)) return;
    Previous = Current;
    Model = Front;
    InputRoute = Route;
    InputKey = Key;
    bInputRepeat = bRepeat;
    InputCommand = Command;
    bActive = true;
    Current = this;
}
FScope::~FScope()
{
    if (bActive) Current = Previous;
}
void TitleToMain(const USoraFrontEnd& Front)
{
    if (!Enabled() || bLogging || Transitions >= MaxTransitions || !Front.IsOpen() ||
        Front.Screen() != SoraUI::EScreen::Title || !IsViewportModel(Front)) return;
    // Set both bounds before any logging or symbol lookup; even a reentrant
    // output device cannot recursively trace this transition.
    TGuardValue<bool> LoggingGuard(bLogging, true);
    const uint32 Sequence = ++Transitions;
    const TCHAR* Route = TEXT("direct-show-main");
    FName Key = NAME_None;
    int32 Command = INDEX_NONE;
    bool bRepeat = false;
    for (const FScope* Scope = Current; Scope; Scope = Scope->Previous)
    {
        if (Scope->Model != &Front) continue;
        Route = Scope->InputRoute; // the outermost matching route is the origin
        if (!Scope->InputKey.IsNone()) { Key = Scope->InputKey; bRepeat = Scope->bInputRepeat; }
        if (Scope->InputCommand != INDEX_NONE) Command = Scope->InputCommand;
    }
    const FAutomationTestFramework& Framework = FAutomationTestFramework::Get();
    const FString Test = Framework.GetCurrentTest() ? Framework.GetCurrentTestFullPath() : FString();
    UE_LOG(LogTemp, Display, TEXT("SORA_FRONTEND_INPUT transition=%u/%u route=%s key=%s repeat=%d command=%d incoming=Title open=1 menu=%d paused=%d focus=%d device=%d world=%s model=%s test=%s"),
        Sequence, MaxTransitions, Route, *Key.ToString(), bRepeat ? 1 : 0, Command,
        Front.Mode().bMenu ? 1 : 0, Front.Mode().GetWorld()->IsPaused() ? 1 : 0, Front.Focus(), static_cast<int32>(Front.Device()),
        *Front.Mode().GetWorld()->GetPathName(), *Front.GetPathName(), Test.IsEmpty() ? TEXT("<none>") : *Test);
    const bool bSymbols = FPlatformStackWalk::InitStackWalking();
    uint64 Frames[MaxFrames] = {};
    const uint32 Count = FMath::Min(FPlatformStackWalk::CaptureStackBackTrace(Frames, MaxFrames), MaxFrames);
    for (uint32 Index = 0; Index < Count; ++Index)
    {
        FProgramCounterSymbolInfo Symbol;
        if (bSymbols) FPlatformStackWalk::ProgramCounterToSymbolInfo(Frames[Index], Symbol);
        const FString Function = FString(ANSI_TO_TCHAR(Symbol.FunctionName)).Left(240);
        const FString Module = FString(ANSI_TO_TCHAR(Symbol.ModuleName)).Left(100);
        UE_LOG(LogTemp, Display, TEXT("SORA_FRONTEND_INPUT_STACK transition=%u frame=%u pc=0x%llx module=%s function=%s"),
            Sequence, Index, static_cast<unsigned long long>(Frames[Index]), *Module, *Function);
    }
}
}
#endif
