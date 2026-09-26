using EpicGames.Core;
using Microsoft.Extensions.Logging;
using UnrealBuildTool;
using System.IO;
public class SoraArena : ModuleRules
{
    public SoraArena(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        // AIModule and GameplayTasks are public because ASoraEnemyController's
        // header derives from AAIController. Later feature lanes (navigation,
        // UMG, Niagara, MetaSounds, sequences and cinematic cameras) depend on
        // modules declared here so they need not edit this file.
        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "Json", "JsonUtilities",
            "AIModule", "GameplayTasks", "NavigationSystem" });
        PrivateDependencyModuleNames.AddRange(new string[] { "HTTP", "WebSockets", "Slate", "SlateCore", "UMG", "RenderCore", "RHI",
            "Niagara", "AudioMixer", "MetasoundEngine", "LevelSequence", "MovieScene", "CinematicCamera" });
        PrivateIncludePaths.Add(Path.GetFullPath(Path.Combine(ModuleDirectory, "../../crates/arena-ffi/include")));
        // Content/Data is read from disk at runtime, never cooked: stage all of it.
        RuntimeDependencies.Add("$(ProjectDir)/Content/Data/...", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf", StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(ProjectDir)/Content/SourceArt/Fonts/OFL.txt", StagedFileType.NonUFS);
        // The credits screen reads every third-party notice at runtime.
        RuntimeDependencies.Add("$(ProjectDir)/ThirdPartyNotices/...", StagedFileType.NonUFS);
        // A packaged game without the IrohaConnect bridge or the Rust combat
        // kernel cannot sign or run deterministic practice, so the build fails.
        // The editor may still build without them and says so.
        string Platform = Target.Platform == UnrealTargetPlatform.Mac ? "Mac"
            : Target.Platform == UnrealTargetPlatform.Win64 ? "Win64" : null;
        if (Platform == null)
        {
            if (Target.Type != TargetType.Editor)
                throw new BuildException("SoraArena ships the Connect bridge and arena kernel only for Mac and Win64, not {0}.", Target.Platform);
            Logger.LogWarning("SoraArena has no Connect bridge or arena kernel for {Platform}; wallet and practice are unavailable.", Target.Platform);
            return;
        }
        StageNativeLibrary(Target, Platform == "Mac" ? "Mac/libconnect_norito_bridge.dylib" : "Win64/connect_norito_bridge.dll",
            "IrohaConnect bridge", "scripts/connect/build-bridge.sh");
        StageNativeLibrary(Target, Platform == "Mac" ? "Mac/libarena_ffi.dylib" : "Win64/arena_ffi.dll",
            "arena kernel", "cargo build --release -p arena-ffi, then scripts/unreal/stage_kernel.py");
    }

    private void StageNativeLibrary(ReadOnlyTargetRules Target, string BinaryPath, string Label, string Remedy)
    {
        string NativePath = Path.GetFullPath(Path.Combine(ModuleDirectory, "../../Binaries", BinaryPath));
        if (File.Exists(NativePath))
        {
            RuntimeDependencies.Add(NativePath, StagedFileType.NonUFS);
            return;
        }
        if (Target.Type != TargetType.Editor)
            throw new BuildException("The {0} is missing at {1}; stage it before building a game target ({2}).", Label, NativePath, Remedy);
        Logger.LogWarning("The {Label} is missing at {Path}; the editor builds without it ({Remedy}).", Label, NativePath, Remedy);
    }
}
