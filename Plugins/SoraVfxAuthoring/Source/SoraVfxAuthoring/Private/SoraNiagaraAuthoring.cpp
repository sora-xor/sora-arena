#include "SoraNiagaraAuthoring.h"

#include "Dom/JsonObject.h"
#include "NiagaraEmitter.h"
#include "NiagaraEmitterHandle.h"
#include "NiagaraExternalSystemEditorUtilities.h"
#include "NiagaraRendererProperties.h"
#include "NiagaraScript.h"
#include "NiagaraSystem.h"
#include "NiagaraTypes.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
    FString JoinErrors(const FNiagaraExternalEditContext& Context)
    {
        TArray<FString> Lines;
        for (const FText& Error : Context.Errors)
        {
            Lines.Add(Error.ToString());
        }
        return FString::Join(Lines, TEXT("\n"));
    }

    FString MissingSystem()
    {
        return TEXT("No Niagara system was given.");
    }

    FNiagaraExt_StackItemReference InputRef(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input)
    {
        FNiagaraExt_StackItemReference Ref(System, Emitter, Script, Module);
        Ref.InputNameStack = Input;
        return Ref;
    }

    FString ApplyInput(UNiagaraSystem* System, const FNiagaraExt_StackItemReference& Ref, const FNiagaraExt_StackInputValue& Data)
    {
        if (!System)
        {
            return MissingSystem();
        }
        FNiagaraExternalEditContext Context(System);
        UNiagaraExternalEditUtilities::SetStackInputData(Ref, Data, Context);
        return JoinErrors(Context);
    }

    // The script struct Niagara uses for a literal's type; the float vectors have
    // no TBaseStructure, only a variant structure.
    template<typename TValue> const UScriptStruct* LiteralStruct() { return TValue::StaticStruct(); }
    template<> const UScriptStruct* LiteralStruct<FLinearColor>() { return TBaseStructure<FLinearColor>::Get(); }
    template<> const UScriptStruct* LiteralStruct<FVector2f>() { return TVariantStructure<FVector2f>::Get(); }
    template<> const UScriptStruct* LiteralStruct<FVector3f>() { return TVariantStructure<FVector3f>::Get(); }
    template<> const UScriptStruct* LiteralStruct<FVector4f>() { return TVariantStructure<FVector4f>::Get(); }

    template<typename TValue>
    FString ApplyLiteral(UNiagaraSystem* System, const FNiagaraExt_StackItemReference& Ref, const TValue& Value)
    {
        FNiagaraExt_StackInputValue Data;
        Data.InitializeAs(LiteralStruct<TValue>(), reinterpret_cast<const uint8*>(&Value));
        return ApplyInput(System, Ref, Data);
    }

    // Builds an input value from the input's declared type (a Position or a
    // Vector3, an enum, the type of a link) and sets it. The schema lookup and the
    // write share one edit context: a stack reference caches stack entries that
    // belong to its context's view model and must not outlive it.
    FString ApplyTyped(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input,
        TFunctionRef<FString(const FNiagaraTypeDefinition&, FNiagaraExt_StackInputValue&)> Build)
    {
        if (!System)
        {
            return MissingSystem();
        }
        FNiagaraExternalEditContext Context(System);
        const FNiagaraExt_StackItemReference Ref = InputRef(System, Emitter, Script, Module, Input);
        FNiagaraExt_StackInputSchema Schema;
        UNiagaraExternalEditUtilities::GetStackInputSchema(Ref, Schema, Context);
        if (Context.HasErrors())
        {
            return JoinErrors(Context);
        }
        if (!Schema.Type.IsValid())
        {
            return FString::Printf(TEXT("Input %s has no type."), *FString::JoinBy(Input, TEXT("/"), [](FName N) { return N.ToString(); }));
        }
        FNiagaraExt_StackInputValue Data;
        const FString Error = Build(Schema.Type, Data);
        if (!Error.IsEmpty())
        {
            return Error;
        }
        UNiagaraExternalEditUtilities::SetStackInputData(Ref, Data, Context);
        return JoinErrors(Context);
    }

    template<typename TValue>
    FString AddUser(UNiagaraSystem* System, FName Name, const FNiagaraTypeDefinition& Type, const TValue& Default, const FString& Description)
    {
        if (!System)
        {
            return MissingSystem();
        }
        FNiagaraExt_UserVariable Variable;
        const FString Text = Name.ToString();
        Variable.Name = Text.StartsWith(TEXT("User.")) ? Name : FName(TEXT("User.") + Text);
        Variable.Type = Type;
        Variable.DefaultValue.Set(Type, FNiagaraVariant(&Default, sizeof(TValue)));
        Variable.Description = FText::FromString(Description);
        if (!Variable.DefaultValue.IsValid())
        {
            return FString::Printf(TEXT("User parameter %s: the default does not match type %s."), *Text, *Type.GetName());
        }
        FNiagaraExternalEditContext Context(System);
        UNiagaraExternalEditUtilities::AddUserVariable(System, Variable, Context);
        return JoinErrors(Context);
    }

    FString SerializeJson(const TSharedRef<FJsonObject>& Object)
    {
        FString Out;
        const TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
            TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Out);
        FJsonSerializer::Serialize(Object, Writer);
        return Out;
    }

    // A readable input value: enum:<entry>, link:<parameter>, hlsl:<expression>,
    // dynamic:<script> or the literal's exported text.
    FString ValueText(const FNiagaraExt_StackInputValue& Value)
    {
        if (const FNiagaraExt_StackInputData_Enum* Enum = Value.GetPtr<FNiagaraExt_StackInputData_Enum>())
        {
            return TEXT("enum:") + (Enum->DisplayName.IsEmpty() ? Enum->EnumName.ToString() : Enum->DisplayName.ToString());
        }
        if (const FNiagaraExt_StackInputData_Linked* Linked = Value.GetPtr<FNiagaraExt_StackInputData_Linked>())
        {
            return TEXT("link:") + Linked->LinkedVariable.Name.ToString();
        }
        if (const FNiagaraExt_StackInputData_HlslExpression* Hlsl = Value.GetPtr<FNiagaraExt_StackInputData_HlslExpression>())
        {
            return TEXT("hlsl:") + Hlsl->HlslExpression;
        }
        if (const FNiagaraExt_StackInputData_DynamicInput* Dynamic = Value.GetPtr<FNiagaraExt_StackInputData_DynamicInput>())
        {
            return TEXT("dynamic:") + (Dynamic->DynamicInputAsset ? Dynamic->DynamicInputAsset->GetPathName() : FString());
        }
        if (Value.GetPtr<FNiagaraExt_StackInputData_DataInterface>())
        {
            return TEXT("data_interface");
        }
        const UScriptStruct* Struct = Value.GetScriptStruct();
        if (!Struct)
        {
            return FString();
        }
        FString Text;
        Struct->ExportText(Text, Value.GetMemory(), nullptr, nullptr, PPF_None, nullptr);
        return Text;
    }

    TSharedRef<FJsonObject> DescribeStack(const FNiagaraExt_ScriptStackTopology& Stack, const TArray<FNiagaraExt_ModuleInputValues>& Values)
    {
        TSharedRef<FJsonObject> StackJson = MakeShared<FJsonObject>();
        TArray<TSharedPtr<FJsonValue>> Modules;
        for (const FNiagaraExt_ModuleTopology& Module : Stack.Modules)
        {
            const FNiagaraExt_ModuleInputValues* ModuleValues = Values.FindByPredicate(
                [&Module](const FNiagaraExt_ModuleInputValues& Candidate) { return Candidate.ModuleName == Module.ModuleName; });
            TSharedRef<FJsonObject> ModuleJson = MakeShared<FJsonObject>();
            ModuleJson->SetStringField(TEXT("name"), Module.ModuleName.ToString());
            ModuleJson->SetBoolField(TEXT("enabled"), Module.Enabled);
            ModuleJson->SetStringField(TEXT("script"), Module.ModuleScript ? Module.ModuleScript->GetPathName() : FString());
            TArray<TSharedPtr<FJsonValue>> Inputs;
            for (int32 Index = 0; Index < Module.Inputs.Num(); ++Index)
            {
                const FNiagaraExt_StackInputTopology& Input = Module.Inputs[Index];
                TSharedRef<FJsonObject> InputJson = MakeShared<FJsonObject>();
                InputJson->SetStringField(TEXT("name"), Input.Name.ToString());
                InputJson->SetStringField(TEXT("type"), Input.Type.GetName());
                InputJson->SetBoolField(TEXT("visible"), Input.bIsVisible);
                InputJson->SetBoolField(TEXT("editable"), Input.bIsEditable);
                InputJson->SetBoolField(TEXT("dynamic"), Input.bIsDynamic);
                InputJson->SetBoolField(TEXT("static_switch"), Input.bIsStaticSwitch);
                if (ModuleValues && ModuleValues->Inputs.IsValidIndex(Index) && ModuleValues->Inputs[Index].Name == Input.Name)
                {
                    InputJson->SetStringField(TEXT("value"), ValueText(ModuleValues->Inputs[Index].Value));
                }
                Inputs.Add(MakeShared<FJsonValueObject>(InputJson));
            }
            ModuleJson->SetArrayField(TEXT("inputs"), Inputs);
            Modules.Add(MakeShared<FJsonValueObject>(ModuleJson));
        }
        StackJson->SetArrayField(TEXT("modules"), Modules);
        return StackJson;
    }

    FNiagaraFloat NiagaraFloat(float Value)
    {
        FNiagaraFloat Result;
        Result.Value = Value;
        return Result;
    }

    FNiagaraInt32 NiagaraInt(int32 Value)
    {
        FNiagaraInt32 Result;
        Result.Value = Value;
        return Result;
    }

    FNiagaraEmitterHandle* FindEmitter(UNiagaraSystem* System, FName Emitter)
    {
        if (!System)
        {
            return nullptr;
        }
        return System->GetEmitterHandles().FindByPredicate([Emitter](const FNiagaraEmitterHandle& Handle) { return Handle.GetName() == Emitter; });
    }
}

UNiagaraSystem* USoraNiagaraAuthoring::CreateEmptySystem(const FString& PackagePath, const FString& AssetName, FString& Error)
{
    FNiagaraExternalEditContext Context;
    UNiagaraSystem* System = UNiagaraExternalEditUtilities::CreateNiagaraSystem(AssetName, PackagePath, nullptr, Context);
    Error = JoinErrors(Context);
    if (!System && Error.IsEmpty())
    {
        Error = FString::Printf(TEXT("Niagara system %s/%s was not created."), *PackagePath, *AssetName);
    }
    return System;
}

FString USoraNiagaraAuthoring::ResetSystem(UNiagaraSystem* System)
{
    if (!System)
    {
        return MissingSystem();
    }
    TArray<FName> Emitters;
    for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
    {
        Emitters.Add(Handle.GetName());
    }
    for (const FName Emitter : Emitters)
    {
        FNiagaraExternalEditContext Context(System);
        UNiagaraExternalEditUtilities::RemoveEmitter(FNiagaraExt_StackItemReference(System, Emitter), Context);
        if (Context.HasErrors())
        {
            return JoinErrors(Context);
        }
    }
    FNiagaraExternalEditContext Context(System);
    FNiagaraExt_UserVariables Users;
    UNiagaraExternalEditUtilities::GetUserVariables(System, Users, Context);
    for (const FNiagaraExt_UserVariable& User : Users.UserVariables)
    {
        UNiagaraExternalEditUtilities::RemoveUserVariable(System, User, Context);
    }
    return JoinErrors(Context);
}

FString USoraNiagaraAuthoring::AddEmitter(UNiagaraSystem* System, UNiagaraEmitter* Template, FName Name)
{
    if (!System)
    {
        return MissingSystem();
    }
    FNiagaraExternalEditContext Context(System);
    FNiagaraExt_EmitterTopology Topology;
    UNiagaraExternalEditUtilities::AddEmitter(Template, Name, Topology, Context);
    FString Error = JoinErrors(Context);
    if (Error.IsEmpty() && Topology.EmitterName != Name)
    {
        Error = FString::Printf(TEXT("Emitter was added as %s, not %s; names must be unique in the system."),
            *Topology.EmitterName.ToString(), *Name.ToString());
    }
    return Error;
}

FString USoraNiagaraAuthoring::AddUserFloat(UNiagaraSystem* System, FName Name, float Default, const FString& Description)
{
    return AddUser(System, Name, FNiagaraTypeDefinition::GetFloatDef(), NiagaraFloat(Default), Description);
}

FString USoraNiagaraAuthoring::AddUserInt(UNiagaraSystem* System, FName Name, int32 Default, const FString& Description)
{
    return AddUser(System, Name, FNiagaraTypeDefinition::GetIntDef(), NiagaraInt(Default), Description);
}

FString USoraNiagaraAuthoring::AddUserBool(UNiagaraSystem* System, FName Name, bool Default, const FString& Description)
{
    return AddUser(System, Name, FNiagaraTypeDefinition::GetBoolDef(), FNiagaraBool(Default), Description);
}

FString USoraNiagaraAuthoring::AddUserVector(UNiagaraSystem* System, FName Name, FVector Default, const FString& Description)
{
    return AddUser(System, Name, FNiagaraTypeDefinition::GetVec3Def(), FVector3f(Default), Description);
}

FString USoraNiagaraAuthoring::AddUserColor(UNiagaraSystem* System, FName Name, FLinearColor Default, const FString& Description)
{
    return AddUser(System, Name, FNiagaraTypeDefinition::GetColorDef(), Default, Description);
}

FString USoraNiagaraAuthoring::AddModule(UNiagaraSystem* System, FName Emitter, FName Script, UNiagaraScript* Module, FName AfterModule, FName& OutName)
{
    OutName = NAME_None;
    if (!System)
    {
        return MissingSystem();
    }
    FNiagaraExternalEditContext Context(System);
    FNiagaraExt_ModuleTopology Topology;
    UNiagaraExternalEditUtilities::AddModule(FNiagaraExt_StackItemReference(System, Emitter, Script, AfterModule), Module, Topology, Context);
    OutName = Topology.ModuleName;
    FString Error = JoinErrors(Context);
    if (Error.IsEmpty() && OutName.IsNone())
    {
        Error = FString::Printf(TEXT("Module %s was not added to %s/%s."), Module ? *Module->GetPathName() : TEXT("(null)"),
            *Emitter.ToString(), *Script.ToString());
    }
    return Error;
}

FString USoraNiagaraAuthoring::AddSetParameter(UNiagaraSystem* System, FName Emitter, FName Script, FName AfterModule, FName Parameter, const FString& Type, FName& OutName)
{
    OutName = NAME_None;
    if (!System)
    {
        return MissingSystem();
    }
    const TMap<FString, FNiagaraTypeDefinition> Types = {
        {TEXT("float"), FNiagaraTypeDefinition::GetFloatDef()}, {TEXT("int"), FNiagaraTypeDefinition::GetIntDef()},
        {TEXT("bool"), FNiagaraTypeDefinition::GetBoolDef()}, {TEXT("vec2"), FNiagaraTypeDefinition::GetVec2Def()},
        {TEXT("vec3"), FNiagaraTypeDefinition::GetVec3Def()}, {TEXT("vec4"), FNiagaraTypeDefinition::GetVec4Def()},
        {TEXT("color"), FNiagaraTypeDefinition::GetColorDef()}, {TEXT("position"), FNiagaraTypeDefinition::GetPositionDef()}};
    const FNiagaraTypeDefinition* TypeDef = Types.Find(Type);
    if (!TypeDef)
    {
        return FString::Printf(TEXT("Unknown parameter type %s."), *Type);
    }
    FNiagaraExt_SetParameterEntry Entry;
    Entry.Variable.Name = Parameter;
    Entry.Variable.Type = *TypeDef;
    TArray<uint8> Zero;
    Zero.SetNumZeroed(TypeDef->GetSize());
    Entry.DefaultValue.Set(*TypeDef, FNiagaraVariant(Zero));
    FNiagaraExternalEditContext Context(System);
    FNiagaraExt_ModuleTopology Topology;
    UNiagaraExternalEditUtilities::AddSetParametersModule(FNiagaraExt_StackItemReference(System, Emitter, Script, AfterModule), {Entry}, Topology, Context);
    OutName = Topology.ModuleName;
    FString Error = JoinErrors(Context);
    if (Error.IsEmpty() && OutName.IsNone())
    {
        Error = FString::Printf(TEXT("No Set Parameters module for %s was added to %s/%s."), *Parameter.ToString(), *Emitter.ToString(), *Script.ToString());
    }
    return Error;
}

FString USoraNiagaraAuthoring::RemoveModule(UNiagaraSystem* System, FName Emitter, FName Script, FName Module)
{
    if (!System)
    {
        return MissingSystem();
    }
    FNiagaraExternalEditContext Context(System);
    UNiagaraExternalEditUtilities::RemoveModule(FNiagaraExt_StackItemReference(System, Emitter, Script, Module), Context);
    return JoinErrors(Context);
}

FString USoraNiagaraAuthoring::SetModuleEnabled(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, bool bEnabled)
{
    if (!System)
    {
        return MissingSystem();
    }
    FNiagaraExternalEditContext Context(System);
    UNiagaraExternalEditUtilities::SetModuleEnabled(FNiagaraExt_StackItemReference(System, Emitter, Script, Module), bEnabled, Context);
    return JoinErrors(Context);
}

FString USoraNiagaraAuthoring::SetInputFloat(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, float Value)
{
    return ApplyLiteral(System, InputRef(System, Emitter, Script, Module, Input), NiagaraFloat(Value));
}

FString USoraNiagaraAuthoring::SetInputInt(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, int32 Value)
{
    return ApplyLiteral(System, InputRef(System, Emitter, Script, Module, Input), NiagaraInt(Value));
}

FString USoraNiagaraAuthoring::SetInputBool(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, bool Value)
{
    return ApplyLiteral(System, InputRef(System, Emitter, Script, Module, Input), FNiagaraBool(Value));
}

FString USoraNiagaraAuthoring::SetInputVector2(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, FVector2D Value)
{
    return ApplyLiteral(System, InputRef(System, Emitter, Script, Module, Input), FVector2f(Value));
}

FString USoraNiagaraAuthoring::SetInputVector(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, FVector Value)
{
    return ApplyTyped(System, Emitter, Script, Module, Input, [&Value](const FNiagaraTypeDefinition& Type, FNiagaraExt_StackInputValue& Data)
    {
        const FVector3f Vector(Value);
        if (Type == FNiagaraTypeDefinition::GetPositionDef())
        {
            const FNiagaraPosition Position(Vector);
            Data.InitializeAs(FNiagaraPosition::StaticStruct(), reinterpret_cast<const uint8*>(&Position));
        }
        else
        {
            Data.InitializeAs(TVariantStructure<FVector3f>::Get(), reinterpret_cast<const uint8*>(&Vector));
        }
        return FString();
    });
}

FString USoraNiagaraAuthoring::SetInputVector4(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, FVector4 Value)
{
    return ApplyLiteral(System, InputRef(System, Emitter, Script, Module, Input), FVector4f(Value));
}

FString USoraNiagaraAuthoring::SetInputColor(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, FLinearColor Value)
{
    return ApplyLiteral(System, InputRef(System, Emitter, Script, Module, Input), Value);
}

FString USoraNiagaraAuthoring::SetInputEnum(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, const FString& Value)
{
    return ApplyTyped(System, Emitter, Script, Module, Input, [&Value, &Input](const FNiagaraTypeDefinition& Type, FNiagaraExt_StackInputValue& Data)
    {
        UEnum* Enum = Type.GetEnum();
        if (!Enum)
        {
            return FString::Printf(TEXT("Input %s is %s, not an enum."), *FString::JoinBy(Input, TEXT("/"), [](FName N) { return N.ToString(); }), *Type.GetName());
        }
        TArray<FString> Known;
        for (int32 Index = 0; Index < Enum->NumEnums() - 1; ++Index)
        {
            const FString Display = Enum->GetDisplayNameTextByIndex(Index).ToString();
            const FString Internal = Enum->GetNameStringByIndex(Index);
            if (Display.Equals(Value, ESearchCase::IgnoreCase) || Internal.Equals(Value, ESearchCase::IgnoreCase))
            {
                FNiagaraExt_StackInputData_Enum& EnumData = Data.InitializeAs<FNiagaraExt_StackInputData_Enum>();
                EnumData.Enum = Enum;
                EnumData.EnumName = Enum->GetNameByIndex(Index);
                EnumData.DisplayName = FText::FromString(Display);
                return FString();
            }
            Known.Add(Display);
        }
        return FString::Printf(TEXT("%s has no entry %s; entries: %s"), *Enum->GetName(), *Value, *FString::Join(Known, TEXT(", ")));
    });
}

FString USoraNiagaraAuthoring::SetInputLinked(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, FName Parameter)
{
    return ApplyTyped(System, Emitter, Script, Module, Input, [Parameter](const FNiagaraTypeDefinition& Type, FNiagaraExt_StackInputValue& Data)
    {
        FNiagaraExt_StackInputData_Linked& Linked = Data.InitializeAs<FNiagaraExt_StackInputData_Linked>();
        Linked.LinkedVariable.Name = Parameter;
        Linked.LinkedVariable.Type = Type;
        return FString();
    });
}

FString USoraNiagaraAuthoring::SetInputExpression(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, const FString& Hlsl)
{
    FNiagaraExt_StackInputValue Data;
    Data.InitializeAs<FNiagaraExt_StackInputData_HlslExpression>().HlslExpression = Hlsl;
    return ApplyInput(System, InputRef(System, Emitter, Script, Module, Input), Data);
}

FString USoraNiagaraAuthoring::SetInputDynamic(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, UNiagaraScript* DynamicInput)
{
    if (!DynamicInput)
    {
        return TEXT("No dynamic input script was given.");
    }
    FNiagaraExt_StackInputValue Data;
    Data.InitializeAs<FNiagaraExt_StackInputData_DynamicInput>().DynamicInputAsset = DynamicInput;
    return ApplyInput(System, InputRef(System, Emitter, Script, Module, Input), Data);
}

FString USoraNiagaraAuthoring::SetInputDataInterface(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, const FString& PropertiesJson)
{
    FNiagaraExt_StackInputValue Data;
    Data.InitializeAs<FNiagaraExt_StackInputData_DataInterface>().PropertyValues = PropertiesJson;
    return ApplyInput(System, InputRef(System, Emitter, Script, Module, Input), Data);
}

FString USoraNiagaraAuthoring::SetEmitterProperties(UNiagaraSystem* System, FName Emitter, const FString& PropertiesJson)
{
    if (!System)
    {
        return MissingSystem();
    }
    FNiagaraExternalEditContext Context(System);
    FNiagaraExt_EmitterData Data;
    Data.PropertyValues = PropertiesJson;
    UNiagaraExternalEditUtilities::SetEmitterData(FNiagaraExt_StackItemReference(System, Emitter), Data, Context);
    return JoinErrors(Context);
}

FString USoraNiagaraAuthoring::GetEmitterProperties(UNiagaraSystem* System, FName Emitter, FString& OutJson)
{
    OutJson.Reset();
    if (!System)
    {
        return MissingSystem();
    }
    FNiagaraExternalEditContext Context(System);
    FNiagaraExt_EmitterData Data;
    UNiagaraExternalEditUtilities::GetEmitterData(FNiagaraExt_StackItemReference(System, Emitter), Data, Context);
    OutJson = Data.PropertyValues;
    return JoinErrors(Context);
}

FString USoraNiagaraAuthoring::AddRenderer(UNiagaraSystem* System, FName Emitter, TSubclassOf<UNiagaraRendererProperties> RendererClass, int32& OutIndex)
{
    OutIndex = INDEX_NONE;
    if (!System)
    {
        return MissingSystem();
    }
    FNiagaraExternalEditContext Context(System);
    FNiagaraExt_RendererRef Renderer;
    UNiagaraExternalEditUtilities::AddRenderer(FNiagaraExt_StackItemReference(System, Emitter), RendererClass, Renderer, Context);
    OutIndex = Renderer.RendererIndex;
    return JoinErrors(Context);
}

FString USoraNiagaraAuthoring::RemoveRenderer(UNiagaraSystem* System, FName Emitter, int32 Index)
{
    if (!System)
    {
        return MissingSystem();
    }
    FNiagaraExternalEditContext Context(System);
    FNiagaraExt_StackItemReference Ref(System, Emitter);
    Ref.RendererIndex = Index;
    UNiagaraExternalEditUtilities::RemoveRenderer(Ref, Context);
    return JoinErrors(Context);
}

FString USoraNiagaraAuthoring::SetRendererProperties(UNiagaraSystem* System, FName Emitter, int32 Index, const FString& PropertiesJson)
{
    if (!System)
    {
        return MissingSystem();
    }
    FNiagaraExternalEditContext Context(System);
    FNiagaraExt_StackItemReference Ref(System, Emitter);
    Ref.RendererIndex = Index;
    FNiagaraExt_RendererData Data;
    Data.PropertyValues = PropertiesJson;
    UNiagaraExternalEditUtilities::SetRendererData(Ref, Data, Context);
    return JoinErrors(Context);
}

FString USoraNiagaraAuthoring::GetRendererProperties(UNiagaraSystem* System, FName Emitter, int32 Index, FString& OutJson)
{
    OutJson.Reset();
    if (!System)
    {
        return MissingSystem();
    }
    FNiagaraExternalEditContext Context(System);
    FNiagaraExt_StackItemReference Ref(System, Emitter);
    Ref.RendererIndex = Index;
    FNiagaraExt_RendererData Data;
    UNiagaraExternalEditUtilities::GetRendererData(Ref, Data, Context);
    OutJson = Data.PropertyValues;
    return JoinErrors(Context);
}

UNiagaraRendererProperties* USoraNiagaraAuthoring::GetRenderer(UNiagaraSystem* System, FName Emitter, int32 Index)
{
    const FNiagaraEmitterHandle* Handle = FindEmitter(System, Emitter);
    const FVersionedNiagaraEmitterData* Data = Handle ? Handle->GetEmitterData() : nullptr;
    if (!Data || !Data->GetRenderers().IsValidIndex(Index))
    {
        return nullptr;
    }
    return Data->GetRenderers()[Index];
}

FString USoraNiagaraAuthoring::DescribeSystem(UNiagaraSystem* System)
{
    TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
    if (!System)
    {
        Root->SetStringField(TEXT("error"), MissingSystem());
        return SerializeJson(Root);
    }
    FNiagaraExternalEditContext Context(System);
    FNiagaraExt_SystemSummary Summary;
    UNiagaraExternalEditUtilities::GetSystemSummary(System, Summary, Context);
    Root->SetStringField(TEXT("system"), System->GetPathName());

    TArray<TSharedPtr<FJsonValue>> Users;
    for (const FNiagaraExt_UserVariable& User : Summary.UserVariables)
    {
        TSharedRef<FJsonObject> UserJson = MakeShared<FJsonObject>();
        UserJson->SetStringField(TEXT("name"), User.Name.ToString());
        UserJson->SetStringField(TEXT("type"), User.Type.GetName());
        UserJson->SetStringField(TEXT("description"), User.Description.ToString());
        Users.Add(MakeShared<FJsonValueObject>(UserJson));
    }
    Root->SetArrayField(TEXT("user"), Users);

    TSharedRef<FJsonObject> SystemStacks = MakeShared<FJsonObject>();
    for (const TCHAR* ScriptName : {TEXT("SystemSpawnScript"), TEXT("SystemUpdateScript")})
    {
        FNiagaraExt_ScriptStackTopology Stack;
        const FNiagaraExt_StackItemReference Ref(System, NAME_None, ScriptName);
        UNiagaraExternalEditUtilities::GetScriptStackTopology(Ref, Stack, Context);
        TArray<FNiagaraExt_ModuleInputValues> Values;
        UNiagaraExternalEditUtilities::GetScriptStackInputValues(Ref, Values, Context);
        SystemStacks->SetObjectField(ScriptName, DescribeStack(Stack, Values));
    }
    Root->SetObjectField(TEXT("system_stacks"), SystemStacks);

    TArray<TSharedPtr<FJsonValue>> Emitters;
    for (const FNiagaraExt_EmitterSummary& Emitter : Summary.Emitters)
    {
        const FNiagaraExt_StackItemReference EmitterRef(System, Emitter.EmitterName);
        FNiagaraExt_EmitterTopology Topology;
        UNiagaraExternalEditUtilities::GetEmitterTopology(EmitterRef, Topology, Context);
        TArray<FNiagaraExt_ModuleInputValues> Values;
        UNiagaraExternalEditUtilities::GetEmitterInputValues(EmitterRef, Values, Context);

        TSharedRef<FJsonObject> EmitterJson = MakeShared<FJsonObject>();
        EmitterJson->SetStringField(TEXT("name"), Emitter.EmitterName.ToString());
        EmitterJson->SetBoolField(TEXT("enabled"), Emitter.bEnabled);
        EmitterJson->SetStringField(TEXT("sim_target"), StaticEnum<ENiagaraSimTarget>()->GetNameStringByValue(int64(Emitter.SimTarget)));
        TArray<TSharedPtr<FJsonValue>> Renderers;
        for (const FNiagaraExt_RendererRef& Renderer : Topology.Renderers)
        {
            TSharedRef<FJsonObject> RendererJson = MakeShared<FJsonObject>();
            RendererJson->SetNumberField(TEXT("index"), Renderer.RendererIndex);
            RendererJson->SetStringField(TEXT("class"), Renderer.RendererClass ? Renderer.RendererClass->GetName() : FString());
            Renderers.Add(MakeShared<FJsonValueObject>(RendererJson));
        }
        EmitterJson->SetArrayField(TEXT("renderers"), Renderers);
        TSharedRef<FJsonObject> Stacks = MakeShared<FJsonObject>();
        Stacks->SetObjectField(TEXT("EmitterSpawnScript"), DescribeStack(Topology.EmitterSpawnScript, Values));
        Stacks->SetObjectField(TEXT("EmitterUpdateScript"), DescribeStack(Topology.EmitterUpdateScript, Values));
        Stacks->SetObjectField(TEXT("ParticleSpawnScript"), DescribeStack(Topology.ParticleSpawnScript, Values));
        Stacks->SetObjectField(TEXT("ParticleUpdateScript"), DescribeStack(Topology.ParticleUpdateScript, Values));
        EmitterJson->SetObjectField(TEXT("stacks"), Stacks);
        Emitters.Add(MakeShared<FJsonValueObject>(EmitterJson));
    }
    Root->SetArrayField(TEXT("emitters"), Emitters);
    Root->SetStringField(TEXT("error"), JoinErrors(Context));
    return SerializeJson(Root);
}

FString USoraNiagaraAuthoring::CompileSystem(UNiagaraSystem* System, FString& OutReport)
{
    OutReport.Reset();
    if (!System)
    {
        return MissingSystem();
    }
    // Forced: a cached result from an earlier build of the same script (the key ignores the
    // system's user parameters) must not stand in for this one.
    System->RequestCompile(true);
    System->WaitForCompilationComplete(false, false);

    FNiagaraExternalEditContext Context(System);
    FNiagaraExt_SystemCompileState State;
    UNiagaraExternalEditUtilities::GetSystemCompileState(System, State, Context);
    FNiagaraExt_StackIssues Issues;
    UNiagaraExternalEditUtilities::GetStackIssues(System, Issues, Context);

    TArray<FString> Errors;
    for (const FText& Error : Context.Errors)
    {
        Errors.Add(Error.ToString());
    }
    TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
    Report->SetStringField(TEXT("status"), StaticEnum<ENiagaraExt_ScriptCompileStatus>()->GetNameStringByValue(int64(State.AggregateStatus)));
    TArray<TSharedPtr<FJsonValue>> Events;
    for (const FNiagaraExt_ScriptCompileInfo& Script : State.Scripts)
    {
        for (const FNiagaraExt_CompileEvent& Event : Script.CompileEvents)
        {
            if (Event.Severity != ENiagaraExt_CompileEventSeverity::Warning && Event.Severity != ENiagaraExt_CompileEventSeverity::Error)
            {
                continue;
            }
            const FString Line = FString::Printf(TEXT("%s/%s: %s"), *Script.EmitterName.ToString(), *Script.ScriptName.ToString(), *Event.Message);
            Events.Add(MakeShared<FJsonValueString>((Event.Severity == ENiagaraExt_CompileEventSeverity::Error ? TEXT("error ") : TEXT("warning ")) + Line));
            if (Event.Severity == ENiagaraExt_CompileEventSeverity::Error)
            {
                Errors.Add(Line);
            }
        }
        if (Script.LastCompileStatus == ENiagaraExt_ScriptCompileStatus::Error && Script.CompileEvents.IsEmpty())
        {
            Errors.Add(FString::Printf(TEXT("%s/%s: %s"), *Script.EmitterName.ToString(), *Script.ScriptName.ToString(), *Script.ErrorSummary));
        }
    }
    Report->SetArrayField(TEXT("compile_events"), Events);
    TArray<TSharedPtr<FJsonValue>> StackIssues;
    for (const FNiagaraExt_StackIssue& Issue : Issues.Issues)
    {
        if (Issue.Severity == ENiagaraExt_StackIssueSeverity::None || Issue.bIsDismissed)
        {
            continue;
        }
        const FString Line = FString::Printf(TEXT("%s %s%s: %s %s"), *StaticEnum<ENiagaraExt_StackIssueSeverity>()->GetNameStringByValue(int64(Issue.Severity)),
            *Issue.Location.EmitterName.ToString(), *Issue.StackDisplayPath, *Issue.ShortDescription, *Issue.LongDescription);
        StackIssues.Add(MakeShared<FJsonValueString>(Line));
        if (Issue.Severity == ENiagaraExt_StackIssueSeverity::Error)
        {
            Errors.Add(Line);
        }
    }
    Report->SetArrayField(TEXT("stack_issues"), StackIssues);
    OutReport = SerializeJson(Report);
    return FString::Join(Errors, TEXT("\n"));
}
