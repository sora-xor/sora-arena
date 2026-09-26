#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "SoraBeatRules.h"
#include "Serialization/JsonSerializer.h"

// Fail-closed JSON readers shared by the catalog loader (SoraCatalog.cpp) and
// its chapter-space reader (SoraCatalogSpace.cpp): every read reports whether
// the field is present with the exact type and range asked for.
namespace SoraCatalogJson
{
using FJsonRows = TArray<TSharedPtr<FJsonValue>>;

inline bool ReadJson(const FString& Relative, TSharedPtr<FJsonObject>& Root)
{
    FString Text;
    return FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Data") / Relative)) &&
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) && Root.IsValid();
}
inline bool Str(const FJsonObject& Object, const TCHAR* Key, FString& Out)
{
    return Object.TryGetStringField(Key, Out) && !Out.IsEmpty();
}
inline bool Whole(double Value, int32& Out)
{
    if (!FMath::IsFinite(Value) || Value != FMath::FloorToDouble(Value) || Value < MIN_int32 || Value > MAX_int32)
        return false;
    Out = static_cast<int32>(Value);
    return true;
}
inline bool Int(const FJsonObject& Object, const TCHAR* Key, int32& Out)
{
    double Value = 0;
    return Object.TryGetNumberField(Key, Value) && Whole(Value, Out);
}
inline bool Num(const FJsonObject& Object, const TCHAR* Key, double& Out)
{
    return Object.TryGetNumberField(Key, Out) && FMath::IsFinite(Out);
}
inline const FJsonRows* Rows(const FJsonObject& Object, const TCHAR* Key)
{
    const FJsonRows* Result = nullptr;
    return Object.TryGetArrayField(Key, Result) ? Result : nullptr;
}
inline TSharedPtr<FJsonObject> Child(const FJsonObject& Object, const TCHAR* Key)
{
    const TSharedPtr<FJsonObject>* Result = nullptr;
    return Object.TryGetObjectField(Key, Result) && Result ? *Result : nullptr;
}
inline bool IsNull(const FJsonObject& Object, const TCHAR* Key)
{
    const TSharedPtr<FJsonValue> Value = Object.TryGetField(Key);
    return Value.IsValid() && Value->IsNull();
}
inline bool Strings(const FJsonRows* Values, TArray<FString>& Out)
{
    if (!Values) return false;
    for (const auto& Value : *Values)
    {
        FString Text;
        if (!Value.IsValid() || !Value->TryGetString(Text) || Text.IsEmpty()) return false;
        Out.Add(MoveTemp(Text));
    }
    return true;
}
inline bool WeaponMask(const FJsonRows* Values, unsigned& Out)
{
    if (!Values) return false;
    for (const auto& Value : *Values)
    {
        double Number = 0; int32 Id = 0;
        if (!Value.IsValid() || !Value->TryGetNumber(Number) || !Whole(Number, Id) ||
            Id < 0 || Id >= SoraBeatRules::WeaponCount || (Out & (1u << Id)) != 0u)
            return false;
        Out |= 1u << Id;
    }
    return true;
}
template <typename TEnum>
inline bool Named(const FJsonObject& Object, const TCHAR* Key, const TMap<FString, TEnum>& Names, TEnum& Out)
{
    FString Name;
    const TEnum* Found = Str(Object, Key, Name) ? Names.Find(Name) : nullptr;
    if (Found) Out = *Found;
    return Found != nullptr;
}
// A non-empty string, or null (left empty).
inline bool Nullable(const FJsonObject& Object, const TCHAR* Key, FString& Out)
{
    Out.Reset();
    return IsNull(Object, Key) || Str(Object, Key, Out);
}
inline bool Points(const FJsonObject& Object, const TCHAR* Key, TArray<FString>& Out)
{
    return Strings(Rows(Object, Key), Out) && Out.Num() <= SoraBeatRules::MaxPoints;
}

} // namespace SoraCatalogJson
