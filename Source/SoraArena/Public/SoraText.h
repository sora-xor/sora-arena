#pragma once
#include "CoreMinimal.h"
#include <initializer_list>

// Player-facing text shows in two languages at once. Every interface string
// is an NSLOCTEXT whose native text is Japanese. Its English subtitle is the
// same key's translation in Content/Localization/Game/en/Game.locres, which
// scripts/unreal/native_japanese_localization.py compiles from
// Content/Localization/Game/en/Game.po. The Japanese line follows the game
// culture, which is ja. The English line is read from the English resource
// directly, so both show together. Pass English() only NSLOCTEXT values;
// formatted text goes through Format.
namespace SoraText
{
// A line resolved for drawing.
struct FLine
{
    FString Japanese;
    FString English;
    bool IsEmpty() const { return Japanese.IsEmpty() && English.IsEmpty(); }
};

// A named Format argument with its value in each language.
struct FArg
{
    FString Name;
    FLine Value;
    FArg(const TCHAR* InName, const FLine& InValue) : Name(InName), Value(InValue) {}
    // Numbers, key caps and proper names read the same in both languages.
    FArg(const TCHAR* InName, const FString& Same) : Name(InName), Value{Same, Same} {}
    FArg(const TCHAR* InName, int32 Number) : Name(InName), Value{FString::FromInt(Number), FString::FromInt(Number)} {}
};

// The English translation of a native Japanese FText. A key that has no
// English translation, or whose translation was made from other Japanese,
// logs an error once and returns an empty string. The subtitle is then
// missing rather than wrong.
SORAARENA_API FString English(const FText& Native);
// The translation for the id and the Japanese source it must have been
// made from, without logging. The localization test uses it too.
SORAARENA_API bool FindEnglish(const FTextId& Id, const FString& Source, FString& OutEnglish);
SORAARENA_API FLine Line(const FText& Native);
// Fills the Japanese pattern in the game culture and its English translation
// with each argument's value in that language.
SORAARENA_API FLine Format(const FText& Pattern, std::initializer_list<FArg> Arguments);
inline FLine Same(const FString& Text) { return {Text, Text}; }
// Content/Localization/Game/en/Game.locres under the project content directory.
SORAARENA_API FString EnglishResourcePath();
}
