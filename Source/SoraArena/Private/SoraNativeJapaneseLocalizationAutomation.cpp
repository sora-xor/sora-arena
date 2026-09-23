#include "SoraCatalog.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Internationalization/Internationalization.h"
#include "Internationalization/Text.h"
#include "Internationalization/TextLocalizationManager.h"
#include "Internationalization/TextLocalizationResource.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraNativeJapaneseLocalizationTest,
    "SoraArena.Localization.NativeJapanese",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraNativeJapaneseLocalizationTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    const FString TargetDir = FPaths::ProjectContentDir() / TEXT("Localization/Game");
    FTextLocalizationMetaDataResource Meta;
    if (!TestTrue(TEXT("Unreal loads Game.locmeta"), Meta.LoadFromFile(TargetDir / TEXT("Game.locmeta"))))
        return false;
    TestEqual(TEXT("Native game culture"), Meta.NativeCulture, FString(TEXT("ja")));
    TestEqual(TEXT("Native resource path"), Meta.NativeLocRes, FString(TEXT("ja/Game.locres")));
    TestTrue(TEXT("Compiled Japanese culture"), Meta.CompiledCultures.Contains(TEXT("ja")));

    FTextLocalizationResource Resource;
    if (!TestTrue(TEXT("Unreal loads Japanese Game.locres"),
        Resource.LoadFromFile(TargetDir / TEXT("ja/Game.locres"), 0)))
        return false;
    const FText Title = NSLOCTEXT("SoraArena", "MenuTitle", "猫柳生");
    const FTextId TitleId = FTextInspector::GetTextId(Title);
    TestEqual(TEXT("Title namespace"), TitleId.GetNamespace().ToString(), FString(TEXT("SoraArena")));
    TestEqual(TEXT("Title key"), TitleId.GetKey().ToString(), FString(TEXT("MenuTitle")));
    const FString* Source = FTextInspector::GetSourceString(Title);
    if (!TestNotNull(TEXT("Japanese source text"), Source)) return false;
    TestEqual(TEXT("Japanese title source"), *Source, FString(TEXT("猫柳生")));
    const FTextLocalizationResource::FEntry* Entry = Resource.Entries.Find(TitleId);
    if (!TestNotNull(TEXT("Japanese title in native resource"), Entry)) return false;
    TestEqual(TEXT("Unreal source CRC"), Entry->SourceStringHash,
        FTextLocalizationResource::HashString(*Source));
    if (!TestTrue(TEXT("Localized display string exists"), Entry->LocalizedString.IsValid())) return false;
    TestEqual(TEXT("Japanese title from Unreal resource"), *Entry->LocalizedString, *Source);

    FTextLocalizationManager& Manager = FTextLocalizationManager::Get();
    TestEqual(TEXT("Registered native game culture"),
        Manager.GetNativeCultureName(ELocalizedTextSourceCategory::Game), FString(TEXT("ja")));
    TestTrue(TEXT("Japanese game localization is discoverable"),
        Manager.GetLocalizedCultureNames(ELocalizationLoadFlags::Game).Contains(TEXT("ja")));
    // In editor the editor language can be different; -game must not fall back.
    if (!GIsEditor)
    {
        TestEqual(TEXT("Runtime localized language"), Manager.GetLocalizedLanguageName(), FString(TEXT("ja")));
        TestEqual(TEXT("Runtime title"), Title.ToString(), *Source);
    }

    FSoraCatalog& Catalog = FSoraCatalog::Get();
    if (!TestTrue(TEXT("Bilingual story catalog loads"), Catalog.Load())) return false;
    if (!TestTrue(TEXT("First chapter has dialogue"), !Catalog.Chapter(0).Dialogue.IsEmpty())) return false;
    const FSoraDialogueCue& Cue = Catalog.Chapter(0).Dialogue[0];
    TestTrue(TEXT("English subtitle remains authored separately"),
        !Cue.English.IsEmpty() && Cue.English != Cue.Japanese);
    UE_LOG(LogTemp, Display, TEXT("SORA_NATIVE_JA_LOCRES_OK: native=ja active=%s title=%s english_subtitle=%s"),
        *Manager.GetLocalizedLanguageName(), *Title.ToString(), !Cue.English.IsEmpty() ? TEXT("present") : TEXT("missing"));
    return !HasAnyErrors();
}
#endif
