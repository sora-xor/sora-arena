#include "SoraText.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Internationalization/Text.h"
#include "Internationalization/TextLocalizationResource.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"

// The Game localization's English subtitles, read with Unreal's own loaders:
// every Japanese native key has a current English translation, the runtime
// lookup gives it, and a missing or outdated translation shows no English
// rather than the wrong words. scripts/unreal/native_japanese_localization.py
// builds the resources and checks the sources; this checks what the engine
// loads.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraEnglishSubtitlesTest,
    "SoraArena.Localization.EnglishSubtitles",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraEnglishSubtitlesTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    const FString TargetDir = FPaths::ProjectContentDir() / TEXT("Localization/Game");
    FTextLocalizationMetaDataResource Meta;
    if (!TestTrue(TEXT("Unreal loads Game.locmeta"), Meta.LoadFromFile(TargetDir / TEXT("Game.locmeta"))))
        return false;
    TestEqual(TEXT("Japanese stays the native culture"), Meta.NativeCulture, FString(TEXT("ja")));
    TestTrue(TEXT("Japanese and English are compiled"), Meta.CompiledCultures.Contains(TEXT("ja")) && Meta.CompiledCultures.Contains(TEXT("en")));

    FTextLocalizationResource Japanese, English;
    if (!TestTrue(TEXT("Unreal loads ja/Game.locres"), Japanese.LoadFromFile(TargetDir / TEXT("ja/Game.locres"), 0)) ||
        !TestTrue(TEXT("Unreal loads en/Game.locres"), English.LoadFromFile(SoraText::EnglishResourcePath(), 0)))
        return false;
    TestTrue(TEXT("The interface has its strings in the resource"), Japanese.Entries.Num() > 300);
    TestEqual(TEXT("English covers exactly the Japanese keys"), English.Entries.Num(), Japanese.Entries.Num());
    const auto HasJapanese = [](const FString& Text)
    {
        for (const TCHAR Char : Text)
            if ((Char >= 0x3000 && Char <= 0x9FFF) || (Char >= 0xFF00 && Char <= 0xFFEF))
                return true;
        return false;
    };
    int32 Current = 0;
    for (const auto& Native : Japanese.Entries)
    {
        const FString Name = Native.Key.GetNamespace().ToString() + TEXT(",") + Native.Key.GetKey().ToString();
        const FTextLocalizationResource::FEntry* Translation = English.Entries.Find(Native.Key);
        if (!TestNotNull(*FString::Printf(TEXT("%s has English"), *Name), Translation))
            continue;
        const FString Source = Native.Value.LocalizedString.IsValid() ? *Native.Value.LocalizedString : FString();
        const FString Subtitle = Translation->LocalizedString.IsValid() ? *Translation->LocalizedString : FString();
        // The native resource holds each source as its own display string.
        const bool bNative = !Source.IsEmpty() && FTextLocalizationResource::HashString(Source) == Native.Value.SourceStringHash;
        const bool bTranslated = Translation->SourceStringHash == Native.Value.SourceStringHash && !Subtitle.IsEmpty() && !HasJapanese(Subtitle);
        FString Lookup;
        const bool bFound = SoraText::FindEnglish(Native.Key, Source, Lookup) && Lookup == Subtitle;
        TestTrue(*FString::Printf(TEXT("%s is current: native, translated from it, found by the runtime lookup"), *Name), bNative && bTranslated && bFound);
        Current += bNative && bTranslated && bFound;
    }

    const FText Title = NSLOCTEXT("SoraArena", "MenuTitle", "猫柳生");
    TestEqual(TEXT("The title's English subtitle"), SoraText::English(Title), FString(TEXT("Nyaagyu Rebellion")));
    const SoraText::FLine Chapter = SoraText::Format(NSLOCTEXT("SoraArena.Menu", "Chapters.Locked", "第{Chapter}章　まだ到達していない"), {{TEXT("Chapter"), 3}});
    TestEqual(TEXT("A pattern fills its Japanese"), Chapter.Japanese, FString(TEXT("第3章　まだ到達していない")));
    TestEqual(TEXT("A pattern fills its English"), Chapter.English, FString(TEXT("Chapter 3: not reached yet")));
    const SoraText::FLine Rebound = SoraText::Format(NSLOCTEXT("SoraArena.Controls", "Banner.Rebound", "「{Control}」を {Key} にした。"),
        {{TEXT("Control"), SoraText::FLine{TEXT("斬撃"), TEXT("Melee strike")}}, {TEXT("Key"), FString(TEXT("F"))}});
    TestTrue(TEXT("Each language takes its own argument"), Rebound.Japanese == TEXT("「斬撃」を F にした。") && Rebound.English == TEXT("Melee strike is now on F."));

    // Translations made from other Japanese, and keys with none, are refused.
    FString Unused;
    TestFalse(TEXT("A translation of older Japanese is refused"), SoraText::FindEnglish(FTextInspector::GetTextId(Title), TEXT("猫柳生の古い題"), Unused));
    TestFalse(TEXT("An unknown key has no English"), SoraText::FindEnglish(FTextId(TEXT("SoraArena.Test"), TEXT("Untranslated")), TEXT("未翻訳"), Unused));
    AddExpectedMessagePlain(TEXT("No current English subtitle for SoraArena.Test,Untranslated"), ELogVerbosity::Error, EAutomationExpectedMessageFlags::Contains, 1);
    const FText Untranslated = FText::AsLocalizable_Advanced(TEXT("SoraArena.Test"), TEXT("Untranslated"), TEXT("未翻訳"));
    TestTrue(TEXT("An untranslated key shows no English and reports itself once"),
        SoraText::English(Untranslated).IsEmpty() && SoraText::English(Untranslated).IsEmpty());
    UE_LOG(LogTemp, Display, TEXT("SORA_ENGLISH_SUBTITLES_OK: keys=%d current=%d title=%s"), Japanese.Entries.Num(), Current, *SoraText::English(Title));
    return !HasAnyErrors();
}
#endif
