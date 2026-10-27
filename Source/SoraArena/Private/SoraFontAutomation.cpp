#include "UI/SoraUIFont.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "SoraFrontEnd.h"
#include "Engine/Font.h"
#include "Fonts/FontCache.h"
#include "Framework/Application/SlateApplication.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"
#include "Rendering/SlateRenderer.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FSoraCreditsFontCoverageTest,
    "SoraArena.UI.CreditsFontCoverage",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::EngineFilter)

bool FSoraCreditsFontCoverageTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    if (!TestTrue(TEXT("Slate is running"), FSlateApplication::IsInitialized()))
        return false;
    TStrongObjectPtr<UFont> Font(SoraUI::CreateUIFont(GetTransientPackage()));
    FSlateFontInfo Info(Font.Get(), 24);
    // A last-resort substitution must not make this coverage check pass.
    Info.FontFallback = EFontFallback::FF_NoFallback;
    FSlateFontCache& Cache = *FSlateApplication::Get().GetRenderer()->GetFontCache();
    const FString DefaultPath = FPaths::ProjectContentDir() / TEXT("SourceArt/Fonts/NotoSansCJKjp-Regular.otf");
    for (const TCHAR Character : FString(TEXT("戻る Back 猫柳生")))
    {
        float Scale = 0;
        const FFontData& Selected = Cache.GetFontDataForCodepoint(Info, Character, Scale);
        TestEqual(TEXT("Japanese and English keep the original face"), Selected.GetFontFilename(), DefaultPath);
        TestTrue(TEXT("The original face covers the menu sample"), Cache.CanLoadCodepoint(Selected, Character));
    }

    TArray<SoraUI::FCreditLine> Credits;
    SoraText::FLine Error;
    if (!TestTrue(TEXT("Actual staged credits load"), SoraUI::LoadCredits(Credits, Error)))
        return false;
    int32 ArabicLetters = 0;
    bool bOriginalTitlePreserved = false;
    for (const SoraUI::FCreditLine& Credit : Credits)
    {
        bOriginalTitlePreserved |= Credit.Line.Contains(TEXT("قط شوارع.jpg"));
        bool bHasArabic = false;
        for (const TCHAR Character : Credit.Line)
        {
            if (Character < 0x0600 || Character > 0x06ff)
                continue;
            bHasArabic = true;
            ++ArabicLetters;
            float Scale = 0;
            const FFontData& Selected = Cache.GetFontDataForCodepoint(Info, Character, Scale);
            TestEqual(TEXT("Arabic credit letters select the shipped Arabic face"),
                Selected.GetFontFilename(),
                FPaths::ProjectContentDir() / TEXT("SourceArt/Fonts/NotoNaskhArabicUI-Regular.ttf"));
            TestTrue(*FString::Printf(TEXT("Credit U+%04X loads without fallback"), static_cast<uint32>(Character)),
                Cache.CanLoadCodepoint(Selected, Character));
        }
        if (!bHasArabic)
            continue;
        // Exercise mixed Arabic/Latin attribution shaping, including joined
        // glyph forms, rather than merely checking the source Unicode map.
        const FShapedGlyphSequenceRef Shaped = Cache.ShapeBidirectionalText(Credit.Line, Info, 1.f,
            TextBiDi::ETextDirection::LeftToRight, ETextShapingMethod::FullShaping);
        TestTrue(TEXT("The mixed credit line produces glyphs"), !Shaped->GetGlyphsToRender().IsEmpty());
        for (const FShapedGlyphEntry& Glyph : Shaped->GetGlyphsToRender())
            if (Glyph.bIsVisible)
                TestTrue(*FString::Printf(TEXT("Credit glyph at source index %d is supported"), Glyph.SourceIndex), Glyph.HasValidGlyph());
    }
    TestTrue(TEXT("The original Arabic asset title is retained"), bOriginalTitlePreserved);
    TestTrue(TEXT("Coverage includes the seven Arabic letters that caused the warnings"), ArabicLetters >= 7);
    return !HasAnyErrors();
}
#endif
