#pragma once

#if WITH_DEV_AUTOMATION_TESTS
#include "CoreMinimal.h"
class USoraFrontEnd;

// Opt-in diagnostic context only. Scopes retain the synchronous input route;
// they neither consume input nor change the front-end state.
namespace SoraFrontEndInputTrace
{
class FScope
{
public:
    FScope(const USoraFrontEnd* Front, const TCHAR* Route, FName Key = NAME_None, bool bRepeat = false, int32 Command = INDEX_NONE);
    ~FScope();
    FScope(const FScope&) = delete;
    FScope& operator=(const FScope&) = delete;
private:
    friend void TitleToMain(const USoraFrontEnd& Front);
    const FScope* Previous = nullptr;
    const USoraFrontEnd* Model = nullptr;
    const TCHAR* InputRoute = nullptr;
    FName InputKey;
    int32 InputCommand = INDEX_NONE;
    bool bInputRepeat = false;
    bool bActive = false;
};
// Call before ShowMain changes the stack. Logs at most eight actual viewport
// Title-to-Main transitions per process, each with at most sixteen frames.
void TitleToMain(const USoraFrontEnd& Front);
}
#endif
