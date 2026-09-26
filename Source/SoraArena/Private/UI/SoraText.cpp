#include "SoraText.h"
#include "Internationalization/TextLocalizationResource.h"
#include "Misc/Paths.h"

DEFINE_LOG_CATEGORY_STATIC(LogSoraText, Log, All);

namespace
{
// The English resource is read once and kept until the process exits, so no
// lookup can outlive it during shutdown.
struct FEnglishTable
{
    FTextLocalizationResource Resource;
    TSet<FTextId> Reported;
};
FEnglishTable& EnglishTable()
{
    static FEnglishTable* Table = []()
    {
        FEnglishTable* Loaded = new FEnglishTable();
        const FString Path = SoraText::EnglishResourcePath();
        if (!Loaded->Resource.LoadFromFile(Path, 0))
            UE_LOG(LogSoraText, Error, TEXT("English subtitles are unavailable: %s did not load"), *Path);
        return Loaded;
    }();
    return *Table;
}
}

FString SoraText::EnglishResourcePath()
{
    return FPaths::ProjectContentDir() / TEXT("Localization/Game/en/Game.locres");
}

bool SoraText::FindEnglish(const FTextId& Id, const FString& Source, FString& OutEnglish)
{
    const FTextLocalizationResource::FEntry* Entry = Id.IsEmpty() ? nullptr : EnglishTable().Resource.Entries.Find(Id);
    // Unreal's own lookup drops a translation made from other source text; so does this.
    if (!Entry || !Entry->LocalizedString.IsValid() || Entry->SourceStringHash != FTextLocalizationResource::HashString(Source))
        return false;
    OutEnglish = *Entry->LocalizedString;
    return true;
}

FString SoraText::English(const FText& Native)
{
    const FTextId Id = FTextInspector::GetTextId(Native);
    const FString* Source = FTextInspector::GetSourceString(Native);
    FString Translation;
    if (Source && FindEnglish(Id, *Source, Translation))
        return Translation;
    FEnglishTable& Table = EnglishTable();
    if (!Table.Reported.Contains(Id))
    {
        Table.Reported.Add(Id);
        UE_LOG(LogSoraText, Error, TEXT("No current English subtitle for %s,%s (\"%s\"); run scripts/unreal/native_japanese_localization.py"),
            *Id.GetNamespace().ToString(), *Id.GetKey().ToString(), Source ? **Source : TEXT(""));
    }
    return FString();
}

SoraText::FLine SoraText::Line(const FText& Native)
{
    return {Native.ToString(), English(Native)};
}

SoraText::FLine SoraText::Format(const FText& Pattern, std::initializer_list<FArg> Arguments)
{
    FFormatNamedArguments Japanese, EnglishArguments;
    for (const FArg& Argument : Arguments)
    {
        Japanese.Add(Argument.Name, FText::AsCultureInvariant(Argument.Value.Japanese));
        EnglishArguments.Add(Argument.Name, FText::AsCultureInvariant(Argument.Value.English));
    }
    const FString EnglishPattern = English(Pattern);
    return {FText::Format(FTextFormat(Pattern), Japanese).ToString(),
        EnglishPattern.IsEmpty() ? FString() : FText::Format(FTextFormat(FText::AsCultureInvariant(EnglishPattern)), EnglishArguments).ToString()};
}
