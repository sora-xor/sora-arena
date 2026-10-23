#pragma once

#include "CoreMinimal.h"

class UWorld;

namespace SoraPresentation
{
    // Select at world construction using the world's actual shader platform
    // and renderer eligibility, including atomics and runtime settings.
    // MAC is the existing conventional asset suffix, also usable on other RHIs.
    bool UsesNaniteEnvironment(const UWorld* World);
    const TCHAR* EnvironmentAssetTier(const UWorld* World);
    void LogEnvironmentAssetTier(const UWorld* World);
}
