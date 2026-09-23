using UnrealBuildTool;
using System.IO;
public class SoraArena : ModuleRules
{
    public SoraArena(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "Json", "JsonUtilities" });
        PrivateDependencyModuleNames.AddRange(new string[] { "HTTP", "WebSockets", "SlateCore", "RenderCore", "RHI" });
        PrivateIncludePaths.Add(Path.GetFullPath(Path.Combine(ModuleDirectory, "../../crates/arena-ffi/include")));
        RuntimeDependencies.Add("$(ProjectDir)/Content/Data/catalog.json", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/Content/SourceArt/Fonts/OFL.txt", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/ThirdPartyNotices/QRCodeGen.txt", StagedFileType.NonUFS);
        string NativeBridge = Target.Platform == UnrealTargetPlatform.Mac ? "Mac/libconnect_norito_bridge.dylib"
            : Target.Platform == UnrealTargetPlatform.Win64 ? "Win64/connect_norito_bridge.dll"
            : "Linux/libconnect_norito_bridge.so";
        string NativePath = Path.GetFullPath(Path.Combine(ModuleDirectory, "../../Binaries", NativeBridge));
        if (File.Exists(NativePath)) RuntimeDependencies.Add(NativePath, StagedFileType.NonUFS);
        string KernelFile = Target.Platform == UnrealTargetPlatform.Mac ? "Mac/libarena_ffi.dylib" : "Win64/arena_ffi.dll";
        string KernelPath = Path.GetFullPath(Path.Combine(ModuleDirectory, "../../Binaries", KernelFile));
        if (File.Exists(KernelPath)) RuntimeDependencies.Add(KernelPath, StagedFileType.NonUFS);
    }
}
