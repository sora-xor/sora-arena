using UnrealBuildTool;

public class SoraMeshTerrainResearch : ModuleRules
{
    public SoraMeshTerrainResearch(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        bAllowUETypesInNamespaces = true;
        PrivateDependencyModuleNames.AddRange(new string[] {
            "Core", "CoreUObject", "Engine", "UnrealEd", "MeshPartition", "MeshPartitionEditor",
            "MeshConversion", "MeshDescription", "DynamicMesh", "GeometryCore"
        });
    }
}
