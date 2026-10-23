#pragma once
#include "SoraCatalog.h"
#include "Dom/JsonObject.h"

namespace SoraCatalogCollectibles
{
// Normalized chapter data always includes both keys. Null means that no
// title was authored; JSON booleans/numbers must never become visible names.
inline bool ReadTitles(const FJsonObject& Object, FSoraCollectible& Item)
{
    const auto Japanese = Object.TryGetField(TEXT("title_ja"));
    const auto English = Object.TryGetField(TEXT("title_en"));
    Item.Title.Reset(); Item.TitleEnglish.Reset();
    if (!Japanese || !English) return false;
    if (Japanese->Type == EJson::Null && English->Type == EJson::Null) return true;
    if (Japanese->Type != EJson::String || English->Type != EJson::String) return false;
    return Japanese->TryGetString(Item.Title) && English->TryGetString(Item.TitleEnglish) &&
        !Item.Title.IsEmpty() && !Item.TitleEnglish.IsEmpty();
}
}
