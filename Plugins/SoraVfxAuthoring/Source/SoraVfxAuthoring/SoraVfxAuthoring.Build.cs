using UnrealBuildTool;

// Editor-only: wraps NiagaraEditor's external-edit utilities (plain C++ in UE 5.8)
// as Blueprint-callable functions so the VFX build script can drive them from Python.
public class SoraVfxAuthoring : ModuleRules
{
    public SoraVfxAuthoring(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "Niagara" });
        PrivateDependencyModuleNames.AddRange(new string[] {
            "NiagaraCore", "NiagaraEditor", "UnrealEd", "Json", "JsonUtilities"
        });
    }
}
