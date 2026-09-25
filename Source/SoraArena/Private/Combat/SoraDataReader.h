#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

// Reads required, typed and range-checked fields from Content/Data's JSON
// (enemies.json, bosses.json), naming the first failure as file, place and
// field. Nothing is defaulted: a missing or malformed field fails the load.
struct FSoraDataReader
{
    FString& Error;
    const TCHAR* File;
    FString Where;

    bool Fail(const FString& Field, const TCHAR* Problem) const
    {
        Error = FString::Printf(TEXT("%s %s.%s: %s"), File, *Where, *Field, Problem);
        return false;
    }
    bool Int(const FJsonObject& Object, const TCHAR* Field, int32& Out, int32 Minimum, int32 Maximum) const
    {
        double Value = 0.0;
        if (!Object.TryGetNumberField(Field, Value))
            return Fail(Field, TEXT("missing whole number"));
        if (Value != FMath::FloorToDouble(Value) || Value < Minimum || Value > Maximum)
            return Fail(Field, TEXT("out of range or not whole"));
        Out = static_cast<int32>(Value);
        return true;
    }
    bool Text(const FJsonObject& Object, const TCHAR* Field, FString& Out) const
    {
        if (!Object.TryGetStringField(Field, Out) || Out.TrimStartAndEnd().IsEmpty())
            return Fail(Field, TEXT("missing text"));
        return true;
    }
    static bool IsId(const FString& Value)
    {
        if (Value.IsEmpty())
            return false;
        for (const TCHAR Character : Value)
            if (!FChar::IsLower(Character) && !FChar::IsDigit(Character) && Character != TEXT('_'))
                return false;
        return true;
    }
    bool Name(const FJsonObject& Object, const TCHAR* Field, FName& Out) const
    {
        FString Value;
        if (!Text(Object, Field, Value))
            return false;
        if (!IsId(Value))
            return Fail(Field, TEXT("not a lower_snake_case id"));
        Out = FName(*Value);
        return true;
    }
    // A lower_snake_case id, or the empty string for none.
    bool OptionalName(const FJsonObject& Object, const TCHAR* Field, FName& Out) const
    {
        FString Value;
        if (!Object.TryGetStringField(Field, Value))
            return Fail(Field, TEXT("missing text (empty for none)"));
        if (!Value.IsEmpty() && !IsId(Value))
            return Fail(Field, TEXT("not a lower_snake_case id"));
        Out = Value.IsEmpty() ? NAME_None : FName(*Value);
        return true;
    }
    // A chapter script's line id (ch02.b15.dunark.005), or the empty string for none.
    bool Line(const FJsonObject& Object, const TCHAR* Field, FName& Out) const
    {
        FString Value;
        if (!Object.TryGetStringField(Field, Value))
            return Fail(Field, TEXT("missing line id (empty for none)"));
        if (!Value.IsEmpty())
        {
            TArray<FString> Parts;
            Value.ParseIntoArray(Parts, TEXT("."), false);
            bool bValid = Parts.Num() == 4 && Parts[0].StartsWith(TEXT("ch")) && Parts[1].StartsWith(TEXT("b"));
            for (const FString& Part : Parts)
                bValid &= IsId(Part);
            if (!bValid)
                return Fail(Field, TEXT("not a chapter script line id"));
        }
        Out = Value.IsEmpty() ? NAME_None : FName(*Value);
        return true;
    }
    bool Flag(const FJsonObject& Object, const TCHAR* Field, bool& Out) const
    {
        if (!Object.TryGetBoolField(Field, Out))
            return Fail(Field, TEXT("missing true or false"));
        return true;
    }
    bool Object(const FJsonObject& Parent, const TCHAR* Field, TSharedPtr<FJsonObject>& Out) const
    {
        const TSharedPtr<FJsonObject>* Found = nullptr;
        if (!Parent.TryGetObjectField(Field, Found) || !Found || !Found->IsValid())
            return Fail(Field, TEXT("missing object"));
        Out = *Found;
        return true;
    }
    // An object, or null for none.
    bool OptionalObject(const FJsonObject& Parent, const TCHAR* Field, TSharedPtr<FJsonObject>& Out) const
    {
        if (!Parent.HasField(Field))
            return Fail(Field, TEXT("missing object (null for none)"));
        if (Parent.HasTypedField<EJson::Null>(Field))
        {
            Out.Reset();
            return true;
        }
        return Object(Parent, Field, Out);
    }
    bool Array(const FJsonObject& Parent, const TCHAR* Field, const TArray<TSharedPtr<FJsonValue>>*& Out) const
    {
        if (!Parent.TryGetArrayField(Field, Out) || !Out)
            return Fail(Field, TEXT("missing array"));
        return true;
    }
    bool Ints(const FJsonObject& Parent, const TCHAR* Field, TArray<int32>& Out, int32 Minimum, int32 Maximum) const
    {
        const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
        if (!Array(Parent, Field, Values))
            return false;
        for (const TSharedPtr<FJsonValue>& Value : *Values)
        {
            double Number = 0.0;
            if (!Value->TryGetNumber(Number) || Number != FMath::FloorToDouble(Number) || Number < Minimum || Number > Maximum)
                return Fail(Field, TEXT("must list whole numbers in range"));
            Out.Add(static_cast<int32>(Number));
        }
        return true;
    }
    bool Names(const FJsonObject& Parent, const TCHAR* Field, TArray<FName>& Out) const
    {
        const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
        if (!Array(Parent, Field, Values))
            return false;
        for (const TSharedPtr<FJsonValue>& Value : *Values)
        {
            FString Text;
            if (!Value->TryGetString(Text) || !IsId(Text))
                return Fail(Field, TEXT("must list lower_snake_case ids"));
            Out.Add(FName(*Text));
        }
        return true;
    }
    template <typename TEnum, int32 N>
    bool Choice(const FJsonObject& Object, const TCHAR* Field, const TCHAR* const (&Choices)[N], TEnum& Out) const
    {
        FString Value;
        if (!Text(Object, Field, Value))
            return false;
        for (int32 Index = 0; Index < N; ++Index)
            if (Value == Choices[Index])
            {
                Out = static_cast<TEnum>(Index);
                return true;
            }
        return Fail(Field, TEXT("unknown value"));
    }
    // Every key of Object is one of Allowed: a misspelt or stray field fails
    // instead of being ignored.
    bool Only(const FJsonObject& Object, std::initializer_list<const TCHAR*> Allowed) const
    {
        for (const auto& Pair : Object.Values)
        {
            const FString Key(*Pair.Key);
            bool bKnown = false;
            for (const TCHAR* Field : Allowed)
                bKnown |= Key == Field;
            if (!bKnown)
                return Fail(Key, TEXT("unknown field"));
        }
        return true;
    }
};
