#!/usr/bin/env python3
"""Read-only audit of the installed UE Mesh Partition rendering defaults.

This is source inspection, not a build, cook, Lumen capture, or Nanite test.
It never changes the playable Estate or enables experimental plugins.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path


PLUGINS = ("MeshPartition", "MeshPartitionWater", "PCGMeshPartitionInterop", "MeshTerrainMode")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def read(path: Path) -> str:
    require(path.is_file(), f"Missing installed UE source: {path}")
    return path.read_text(encoding="utf-8")


def assignment(source: str, field: str, expression: str, path: Path) -> str:
    matches = re.findall(rf"\b{re.escape(field)}\s*=\s*({expression})\s*;", source)
    require(len(matches) == 1, f"Expected one {field} assignment in {path}, found {len(matches)}")
    return matches[0]


def audit(engine: Path, project: Path) -> dict:
    build_path = engine / "Engine/Build/Build.version"
    build = json.loads(read(build_path))
    version = ".".join(str(build[key]) for key in ("MajorVersion", "MinorVersion", "PatchVersion"))
    require(version in {"5.8.2", "5.8.3"}, f"Unsupported UE patch for this audit: {version}")

    plugin_root = engine / "Engine/Plugins/Experimental"
    descriptors = {}
    for name in PLUGINS:
        path = plugin_root / name / f"{name}.uplugin"
        descriptor = json.loads(read(path))
        require(descriptor.get("IsExperimentalVersion") is True,
                f"Expected an experimental Epic plugin: {path}")
        descriptors[name] = str(path.relative_to(engine))

    partition = plugin_root / "MeshPartition/Source"
    component_path = partition / "MeshPartition/Private/MeshPartitionStaticMeshComponent.cpp"
    component = read(component_path)
    require(re.search(r"\bbLumenHeightfield\s*=\s*true\s*;", component),
            f"Lumen heightfield component flag changed: {component_path}")

    lumen_scene_path = engine / "Engine/Source/Runtime/Renderer/Private/Lumen/LumenScene.cpp"
    lumen_scene = read(lumen_scene_path)
    require("SceneProxy->SupportsHeightfieldRepresentation() || SceneProxy->IsLumenHeightfield()"
            in lumen_scene, f"Lumen heightfield scene-classification path changed: {lumen_scene_path}")

    distance_field_path = (engine / "Engine/Source/Developer/MeshUtilities/Private/"
                           "MeshDistanceFieldUtilities.cpp")
    distance_field = read(distance_field_path)
    require(re.search(r"void FMeshUtilities::GenerateSignedDistanceFieldVolumeData\([\s\S]*?"
                      r"if \(DistanceFieldResolutionScale > 0\)", distance_field),
            f"Signed mesh distance-field build guard changed: {distance_field_path}")

    header_path = partition / "MeshPartitionEditor/Public/MeshPartitionStaticMeshTransformer.h"
    header = read(header_path)
    nanite_default = assignment(header, "bUseNanite", r"true|false", header_path) == "true"

    render_defaults = {}
    for short_path in ("MeshPartitionEditorUtils.cpp", "MeshPartitionStaticMeshTransformer.cpp"):
        path = partition / "MeshPartitionEditor/Private" / short_path
        source = read(path)
        # The transformer owns a per-LOD setting; the utils file owns the first source model.
        # Other assignments would require re-review rather than silently choosing one.
        render_defaults[short_path] = {
            "distance_field_resolution_scale": float(assignment(
                source, "DistanceFieldResolutionScale", r"[0-9.]+f?", path).rstrip("f")),
            "max_lumen_mesh_cards": int(assignment(
                source, "MaxLumenMeshCards", r"[0-9]+", path)),
            "source_path": str(path.relative_to(engine)),
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    project_descriptor = json.loads(read(project / "SoraArena.uproject"))
    release_research_plugin_enabled = any(
        entry.get("Name") == "SoraMeshTerrainResearch" and entry.get("Enabled") is True
        for entry in project_descriptor.get("Plugins", []))
    require(not release_research_plugin_enabled,
            "Research plugin is enabled in this project descriptor; audit an isolated checkout")

    mac_config = read(project / "Config/Mac/MacEngine.ini")
    require(re.search(r"(?m)^r\.Nanite=0\s*$", mac_config),
            "Expected the M1 conventional-mesh Nanite override")

    return {
        "schema_version": 1,
        "engine": {
            "version": version,
            "changelist": build.get("Changelist"),
            "build_version_sha256": hashlib.sha256(build_path.read_bytes()).hexdigest(),
        },
        "epic_experimental_plugins": descriptors,
        "installed_source_capabilities": {
            "mesh_partition_component_lumen_heightfield_flag": True,
            "lumen_scene_classifies_that_flag_as_heightfield": True,
            "zero_distance_field_scale_skips_signed_mesh_distance_field_build": True,
            "static_mesh_transformer_nanite_default": nanite_default,
            "compiled_static_mesh_build_defaults": render_defaults,
        },
        "project": {
            "research_plugin_enabled_in_release_descriptor": False,
            "m1_nanite_disabled": True,
        },
        "assessment": {
            "release_engine_pin_met": version == "5.8.2",
            "mesh_terrain_rendering_qualified": False,
            "reason": "Source flags and build defaults do not prove cooked compiled sections, Lumen Surface Cache coverage, software distance-field representation, Nanite rendering, or frame rate.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-root", required=True, type=Path)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    try:
        report = audit(args.engine_root.expanduser().resolve(), args.project_root.expanduser().resolve())
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"SORA_MESH_LUMEN_SOURCE_AUDIT_FAILED: {exc}\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
