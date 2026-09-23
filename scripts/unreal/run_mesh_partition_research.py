#!/usr/bin/env python3
"""One-shot UE 5.8 Mesh Partition experiment in a separate Git worktree.

The release project descriptor and campaign map are untouched. This program
enables its opt-in editor plugin only in the supplied diagnostic worktree.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


SOURCE_MAP = "/Game/Research/NyaagyuMeshTerrain_Source"
WP_MAP = SOURCE_MAP + "_WP"
PHASE_MARKERS = {
    "stage": "SORA_MESH_RESEARCH_STAGE_COMPLETE: 16 source HI actors",
    "author": "SORA_MESH_RESEARCH_AUTHOR_COMPLETE: saved native Mesh Partition and base modifiers",
    "verify": "SORA_MESH_RESEARCH_VERIFY_COMPLETE: compiled runtime sections validated",
}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def source_check(project):
    manifest_path = project / "Content/SourceArt/Environment/NyaagyuTerrain/manifest.json"
    require(manifest_path.is_file(), f"Terrain manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest.get("schema_version") == 1
            and manifest.get("tile_layout") == [4, 4]
            and manifest.get("tile_size_cm") == [1600, 1300]
            and manifest.get("world_xy_cm") == [-3200, -2600, 3200, 2600],
            "Original terrain manifest identity has changed")
    hi = [tile for tile in manifest["tiles"] if tile["tier"] == "hi"]
    require(len(hi) == 16 and len({tuple(tile["index"]) for tile in hi}) == 16,
            "Research requires all 16 unique HI source tiles")
    import hashlib
    for tile in hi:
        x, y = tile["index"]
        name = f"SM_NyaagyuTerrain_HI_X{x}_Y{y}"
        path = manifest_path.parent / tile["fbx"]
        package = project / f"Content/Generated/Environment/Terrain/{name}.uasset"
        require(tile["name"] == name and tile["triangles"] == 26624
                and tile["placement_center_cm"] == [-2400 + 1600*x, -1950 + 1300*y, 0]
                and path.is_file()
                and hashlib.sha256(path.read_bytes()).hexdigest() == tile["fbx_sha256"],
                f"HI source identity or hash changed: {name}")
        require(package.is_file(), f"UE import missing; run import_original_assets.py first: {package}")
    for name in ("MI_Nyaagyu_Soil", "MI_Nyaagyu_Stone"):
        require((project / f"Content/Generated/Environment/{name}.uasset").is_file(),
                f"PBR material import missing: {name}")
    require((project / "Plugins/SoraMeshTerrainResearch/SoraMeshTerrainResearch.uplugin").is_file(),
            "Opt-in research editor plugin is absent")


def enable_plugin_only_in_worktree(project):
    path = project / "SoraArena.uproject"
    descriptor = json.loads(path.read_text(encoding="utf-8"))
    plugins = descriptor.setdefault("Plugins", [])
    entry = next((item for item in plugins if item["Name"] == "SoraMeshTerrainResearch"), None)
    if entry is None:
        plugins.append({"Name": "SoraMeshTerrainResearch", "Enabled": True})
    else:
        entry["Enabled"] = True
    path.write_text(json.dumps(descriptor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_phase(args, phase, command, marker=None):
    log = args.project_root / f"Saved/Logs/mesh_research_{phase}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    env = dict(__import__("os").environ,
               SORA_MESH_RESEARCH_PHASE=phase,
               SORA_MESH_RESEARCH_ENGINE_VERSION=args.engine_version)
    with log.open("w", encoding="utf-8") as output:
        result = subprocess.run(command, cwd=args.project_root, env=env, stdout=output,
                                stderr=subprocess.STDOUT, timeout=3600, check=False)
    content = log.read_text(encoding="utf-8", errors="replace")
    require(result.returncode == 0, f"{phase} failed with exit {result.returncode}; inspect {log}")
    if marker is not None:
        require(marker in content, f"{phase} did not emit its success marker; inspect {log}")
    require("SORA_MESH_RESEARCH_REJECTED:" not in content,
            f"{phase} rejected the research map; inspect {log}")
    print(f"{phase}: verified log {log}")
    return content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path,
                        help="Separate diagnostic Git worktree containing imported UE assets")
    parser.add_argument("--engine-root", required=True, type=Path,
                        help="Installed UE 5.8 engine root")
    parser.add_argument("--allow-interim-5.8.3", action="store_true",
                        help="Research diagnostic only; release remains pinned to 5.8.2")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without editing or running UE")
    parser.add_argument("--prepare-plugin-only", action="store_true",
                        help="Enable the Editor plugin in the diagnostic worktree, then stop for its build")
    args = parser.parse_args()
    args.project_root = args.project_root.expanduser().resolve()
    args.engine_root = args.engine_root.expanduser().resolve()
    source_root = Path(__file__).resolve().parents[2]
    require(args.project_root != source_root and (args.project_root / ".git").is_file(),
            "Use a separate linked Git worktree; never run on the release checkout")
    require((args.project_root / "SoraArena.uproject").is_file(), "Project descriptor missing")
    source_check(args.project_root)
    build = json.loads((args.engine_root / "Engine/Build/Build.version").read_text())
    args.engine_version = f'{build["MajorVersion"]}.{build["MinorVersion"]}.{build["PatchVersion"]}'
    require(args.engine_version == "5.8.2" or
            (args.allow_interim_5_8_3 and args.engine_version == "5.8.3"),
            f"UE {args.engine_version} is not the pinned 5.8.2 release engine")
    system = sys.platform
    if system == "darwin":
        editor = args.engine_root / "Engine/Binaries/Mac/UnrealEditor-Cmd"
    elif system == "win32":
        editor = args.engine_root / "Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
    else:
        editor = args.engine_root / "Engine/Binaries/Linux/UnrealEditor-Cmd"
    require(editor.is_file(), f"UnrealEditor-Cmd executable missing: {editor}")
    for name in ("NyaagyuMeshTerrain_Source.umap", "NyaagyuMeshTerrain_Source_WP.umap"):
        require(not (args.project_root / "Content/Research" / name).exists(),
                f"Research map already exists; refusing to overwrite {name}")
    if args.dry_run:
        print(f"Source, imports, worktree, and UE {args.engine_version} preflight passed")
        return

    enable_plugin_only_in_worktree(args.project_root)
    if args.prepare_plugin_only:
        print("Enabled SoraMeshTerrainResearch only in the diagnostic worktree; build SoraArenaEditor there")
        return
    project_file = args.project_root / "SoraArena.uproject"
    editor_script = args.project_root / "scripts/unreal/mesh_partition_research_editor.py"
    require(editor_script.is_file(), f"UE Python research script missing: {editor_script}")
    common = [str(editor), str(project_file), "-unattended", "-nop4", "-NoSplash"]

    run_phase(args, "stage", common + [f"-ExecutePythonScript={editor_script}"], PHASE_MARKERS["stage"])
    require((args.project_root / "Content/Research/NyaagyuMeshTerrain_Source.umap").is_file(),
            "Stage marker appeared without a persisted source map")
    run_phase(args, "partition", common + ["-run=WorldPartitionConvertCommandlet",
                                         SOURCE_MAP, "-AllowCommandletRendering", "-ConversionSuffix"])
    require((args.project_root / "Content/Research/NyaagyuMeshTerrain_Source_WP.umap").is_file(),
            "WorldPartitionConvertCommandlet did not create the separate _WP map")
    run_phase(args, "author", common + [f"-ExecutePythonScript={editor_script}"], PHASE_MARKERS["author"])
    build_log = run_phase(args, "build", common + [WP_MAP, "-run=WorldPartitionBuilderCommandlet",
                                                  "-Builder=WorldPartitionMeshPartitionBuilder",
                                                  "-ReuseMode=ForceRebuild", "-AllowCommandletRendering"])
    summary = re.search(r"Finished Build for World .*?\(Built (\d+), Reused (\d+), Failed (\d+), "
                        r"Removed (\d+), Could Not Remove (\d+) Compiled Sections, "
                        r"(\d+) Failed Mesh Partitions\)", build_log)
    require(summary is not None, "Mesh Partition builder did not emit the expected summary")
    built, reused, failed, _, could_not_remove, failed_partitions = map(int, summary.groups())
    require(built > 0 and reused == 0 and failed == 0 and could_not_remove == 0
            and failed_partitions == 0,
            f"Mesh Partition build gate failed: {summary.group(0)}")
    run_phase(args, "verify", common + [f"-ExecutePythonScript={editor_script}"], PHASE_MARKERS["verify"])
    print("SORA_MESH_RESEARCH_COMPLETE: separate WP map has proven compiled Mesh Partition sections")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        print(f"SORA_MESH_RESEARCH_FAILED: {error}", file=sys.stderr)
        sys.exit(1)
