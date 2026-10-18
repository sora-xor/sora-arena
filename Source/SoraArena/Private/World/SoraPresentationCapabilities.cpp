#include "World/SoraPresentationCapabilities.h"

#include "DataDrivenShaderPlatformInfo.h"
#include "Engine/World.h"
#include "RenderUtils.h"
#include "RHI.h"
#include "SceneInterface.h"

bool SoraPresentation::UsesNaniteEnvironment(const UWorld* World)
{
    if (!World || !World->Scene || GUsingNullRHI)
        return false;
    const EShaderPlatform Platform = World->Scene->GetShaderPlatform();
    return FDataDrivenShaderPlatformInfo::IsValid(Platform) && UseNanite(Platform);
}

const TCHAR* SoraPresentation::EnvironmentAssetTier(const UWorld* World)
{
    return UsesNaniteEnvironment(World) ? TEXT("HI") : TEXT("MAC");
}

void SoraPresentation::LogEnvironmentAssetTier(const UWorld* World)
{
    FString ShaderPlatform = TEXT("none");
    if (World && World->Scene)
    {
        const EShaderPlatform Platform = World->Scene->GetShaderPlatform();
        if (FDataDrivenShaderPlatformInfo::IsValid(Platform))
            ShaderPlatform = FDataDrivenShaderPlatformInfo::GetName(Platform).ToString();
    }
    UE_LOG(LogTemp, Display,
        TEXT("SORA_ENVIRONMENT_TIER: shader_platform=%s null_rhi=%d nanite_eligible=%d tier=%s"),
        *ShaderPlatform, GUsingNullRHI ? 1 : 0, UsesNaniteEnvironment(World) ? 1 : 0,
        EnvironmentAssetTier(World));
}
