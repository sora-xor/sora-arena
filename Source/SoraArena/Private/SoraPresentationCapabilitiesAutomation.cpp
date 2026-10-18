#include "World/SoraPresentationCapabilities.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/AutomationTest.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/ScopedCVar.h"
#include "RHI.h"
#include "SceneInterface.h"
#include "Tests/AutomationCommon.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraEnvironmentCapabilityTest,
    "SoraArena.Rendering.EnvironmentCapability",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraEnvironmentCapabilityTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    TestEqual(TEXT("No world selects conventional assets"),
        FString(SoraPresentation::EnvironmentAssetTier(nullptr)), FString(TEXT("MAC")));
    FTestWorldWrapper TestWorld;
    if (!TestTrue(TEXT("Disposable game world exists"), TestWorld.CreateTestWorld(EWorldType::Game)))
        return false;
    UWorld* World = TestWorld.GetTestWorld();
    if (!TestNotNull(TEXT("Game world is available"), World)) return false;
    IConsoleVariable* Nanite = IConsoleManager::Get().FindConsoleVariable(TEXT("r.Nanite"));
    if (!TestNotNull(TEXT("Renderer Nanite control exists"), Nanite)) return false;
    const int32 OriginalValue = Nanite->GetInt();
    const FString OriginalTier = SoraPresentation::EnvironmentAssetTier(World);
    SoraPresentation::LogEnvironmentAssetTier(World);
    if (GUsingNullRHI || !World->Scene || World->Scene->GetFeatureLevel() < ERHIFeatureLevel::SM6)
        TestEqual(TEXT("NullRHI and SM5 never select the dense Nanite assets"),
            OriginalTier, FString(TEXT("MAC")));
    {
        const FScopedCVar<int32> DisableNanite(TEXT("r.Nanite"), 0);
        TestEqual(TEXT("Explicitly disabling Nanite uses the conventional tier on this RHI"),
            FString(SoraPresentation::EnvironmentAssetTier(World)), FString(TEXT("MAC")));
        TestFalse(TEXT("Disabled Nanite cannot be reported eligible"),
            SoraPresentation::UsesNaniteEnvironment(World));
    }
    TestEqual(TEXT("Test restores the user's Nanite setting"), Nanite->GetInt(), OriginalValue);
    TestEqual(TEXT("Tier selection responds after the setting is restored"),
        FString(SoraPresentation::EnvironmentAssetTier(World)), OriginalTier);
    TestWorld.ForwardErrorMessages(this);
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraMacShaderTargetsTest,
    "SoraArena.Rendering.MacShaderTargets",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraMacShaderTargetsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    TArray<FString> Targets;
    GConfig->GetArray(TEXT("/Script/MacTargetPlatform.MacTargetSettings"),
        TEXT("TargetedRHIs"), Targets, GEngineIni);
    TestEqual(TEXT("Mac cook has exactly two shader targets"), Targets.Num(), 2);
    TestTrue(TEXT("Mac cook retains M1 and forced-SM5 fallback shaders"), Targets.Contains(TEXT("SF_METAL_SM5")));
    TestTrue(TEXT("Mac cook includes M2+ Nanite shaders"), Targets.Contains(TEXT("SF_METAL_SM6")));
    return !HasAnyErrors();
}
#endif
