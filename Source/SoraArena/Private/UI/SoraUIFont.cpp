#include "UI/SoraUIFont.h"
#include "Engine/Font.h"
#include "Fonts/CompositeFont.h"
#include "Fonts/UnicodeBlockRange.h"
#include "Misc/Paths.h"

UFont* SoraUI::CreateUIFont(UObject* Outer)
{
    UFont* Font = NewObject<UFont>(Outer);
    Font->FontCacheType = EFontCacheType::Runtime;
    Font->LegacyFontSize = 28;
    Font->LegacyFontName = FName(TEXT("Regular"));
    FCompositeFont& Composite = Font->GetMutableInternalCompositeFont();
    Composite = FCompositeFont(FName(TEXT("Regular")),
        FPaths::ProjectContentDir() / TEXT("SourceArt/Fonts/NotoSansCJKjp-Regular.otf"),
        EFontHinting::Default, EFontLoadingPolicy::LazyLoad);

    // Credits preserve upstream titles, including Arabic. The custom Japanese
    // composite does not inherit the engine default's Arabic subfont. Use the
    // same shipped Noto face/ranges, without replacing Japanese or Latin text.
    FCompositeSubFont& Arabic = Composite.SubTypefaces.AddDefaulted_GetRef();
    for (const EUnicodeBlockRange Block : {
        EUnicodeBlockRange::Arabic, EUnicodeBlockRange::ArabicExtendedA,
        EUnicodeBlockRange::ArabicMathematicalAlphabeticSymbols,
        EUnicodeBlockRange::ArabicPresentationFormsA, EUnicodeBlockRange::ArabicPresentationFormsB,
        EUnicodeBlockRange::ArabicSupplement})
    {
        Arabic.CharacterRanges.Add(FUnicodeBlockRange::GetUnicodeBlockRange(Block).GetRange());
    }
    // No culture filter: an Arabic attribution must also render in the
    // Japanese and bilingual credits screens.
    Arabic.Typeface.AppendFont(FName(TEXT("Regular")),
        FPaths::ProjectContentDir() / TEXT("SourceArt/Fonts/NotoNaskhArabicUI-Regular.ttf"),
        EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
    return Font;
}
