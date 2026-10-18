#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "SoraNiagaraAuthoring.generated.h"

class UNiagaraEmitter;
class UNiagaraRendererProperties;
class UNiagaraScript;
class UNiagaraSystem;

/**
 * Python-facing Niagara stack authoring for scripts/unreal/create_sora_vfx.py.
 *
 * UE 5.8 ships the stack editing it needs (add emitters and modules, set module
 * inputs to literals, links, HLSL expressions or dynamic inputs, user
 * parameters, compile diagnostics) only as plain C++ in
 * UNiagaraExternalEditUtilities, which Python cannot call. Each function here
 * forwards to it and returns the engine's errors joined into one string, empty
 * on success, so the script can stop at the first refusal.
 *
 * A stack location is (Emitter, Script, Module, Input): Script is an
 * ENiagaraScriptUsage name such as ParticleSpawnScript or EmitterUpdateScript,
 * Module the function name the stack shows (InitializeParticle, ScaleColor), and
 * Input the path to the input, one name per nested dynamic input.
 */
UCLASS()
class SORAVFXAUTHORING_API USoraNiagaraAuthoring : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    /** Creates a system asset with no emitters at PackagePath/AssetName. */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static UNiagaraSystem* CreateEmptySystem(const FString& PackagePath, const FString& AssetName, FString& Error);

    /** Removes every emitter and user parameter so an existing asset is rebuilt in place. */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString ResetSystem(UNiagaraSystem* System);

    /** Copies Template (an engine template emitter) into System under Name. */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString AddEmitter(UNiagaraSystem* System, UNiagaraEmitter* Template, FName Name);

    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString AddUserFloat(UNiagaraSystem* System, FName Name, float Default, const FString& Description);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString AddUserInt(UNiagaraSystem* System, FName Name, int32 Default, const FString& Description);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString AddUserBool(UNiagaraSystem* System, FName Name, bool Default, const FString& Description);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString AddUserVector(UNiagaraSystem* System, FName Name, FVector Default, const FString& Description);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString AddUserColor(UNiagaraSystem* System, FName Name, FLinearColor Default, const FString& Description);

    /** Appends Module to the stack, after AfterModule when that is set; OutName is the name the stack gave it. */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString AddModule(UNiagaraSystem* System, FName Emitter, FName Script, UNiagaraScript* Module, FName AfterModule, FName& OutName);
    /**
     * Adds a Set Parameters module writing Parameter (e.g. Particles.Position), after AfterModule when set.
     * Type is float, int, bool, vec2, vec3, vec4, color or position. OutName is the module's stack name;
     * set the value with SetInput* on input [Parameter].
     */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString AddSetParameter(UNiagaraSystem* System, FName Emitter, FName Script, FName AfterModule, FName Parameter, const FString& Type, FName& OutName);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString RemoveModule(UNiagaraSystem* System, FName Emitter, FName Script, FName Module);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetModuleEnabled(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, bool bEnabled);

    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetInputFloat(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, float Value);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetInputInt(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, int32 Value);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetInputBool(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, bool Value);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetInputVector2(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, FVector2D Value);
    /** Sets a Vector3 input, or a Position input when the module declares one. */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetInputVector(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, FVector Value);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetInputVector4(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, FVector4 Value);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetInputColor(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, FLinearColor Value);
    /** Value is the enum entry's display name (as the stack shows it) or internal name. */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetInputEnum(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, const FString& Value);
    /** Reads the input from a parameter such as User.Intensity or Particles.NormalizedAge. */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetInputLinked(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, FName Parameter);
    /** A single HLSL rvalue, which may read namespaced parameters (User.X, Particles.NormalizedAge). */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetInputExpression(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, const FString& Hlsl);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetInputDynamic(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, UNiagaraScript* DynamicInput);
    /** Replaces a data interface input with one whose properties come from PropertiesJson. */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetInputDataInterface(UNiagaraSystem* System, FName Emitter, FName Script, FName Module, const TArray<FName>& Input, const FString& PropertiesJson);

    /** Emitter properties (SimTarget, bLocalSpace, CalculateBoundsMode, FixedBounds ...) as a JSON object. */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetEmitterProperties(UNiagaraSystem* System, FName Emitter, const FString& PropertiesJson);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString GetEmitterProperties(UNiagaraSystem* System, FName Emitter, FString& OutJson);

    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString AddRenderer(UNiagaraSystem* System, FName Emitter, TSubclassOf<UNiagaraRendererProperties> RendererClass, int32& OutIndex);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString RemoveRenderer(UNiagaraSystem* System, FName Emitter, int32 Index);
    /** Renderer properties as a JSON object; covers renderer classes Python does not expose (ribbons). */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString SetRendererProperties(UNiagaraSystem* System, FName Emitter, int32 Index, const FString& PropertiesJson);
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString GetRendererProperties(UNiagaraSystem* System, FName Emitter, int32 Index, FString& OutJson);
    /** The renderer object itself, for set_editor_property; null when absent. */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static UNiagaraRendererProperties* GetRenderer(UNiagaraSystem* System, FName Emitter, int32 Index);

    /** JSON: user parameters, and per emitter its renderers and every stack's modules and inputs. */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString DescribeSystem(UNiagaraSystem* System);

    /** Compiles and waits. OutReport is JSON with the compile status, errors and warnings. Returns the errors. */
    UFUNCTION(BlueprintCallable, Category = "Sora|VFX")
    static FString CompileSystem(UNiagaraSystem* System, FString& OutReport);
};
