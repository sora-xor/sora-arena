#if WITH_DEV_AUTOMATION_TESTS

#include "Engine/SkeletalMesh.h"
#include "Misc/AutomationTest.h"
#include "UObject/UObjectGlobals.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraNyaakotoCookedLODsTest,
    "SoraArena.Character.NyaakotoCookedLODs",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext |
    EAutomationTestFlags::EngineFilter)

bool FSoraNyaakotoCookedLODsTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    const USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr,
        TEXT("/Game/Generated/Meshes/SK_NyaagyuSamurai.SK_NyaagyuSamurai"));
    if (!TestNotNull(TEXT("Cooked Nyaakoto skeletal mesh is loadable"), Mesh))
        return false;

    TestEqual(TEXT("Cooked Nyaakoto retains three authored skeletal LODs"),
        Mesh->GetLODNum(), 3);
    TestEqual(TEXT("Cooked Nyaakoto retains its material identity"),
        Mesh->GetMaterials().Num(), 23);
    UE_LOG(LogTemp, Display, TEXT("SORA_NYAAKOTO_COOKED_LODS: lods=%d materials=%d"),
        Mesh->GetLODNum(), Mesh->GetMaterials().Num());
    return !HasAnyErrors();
}

#endif
