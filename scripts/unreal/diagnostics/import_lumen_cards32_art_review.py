"""Rebuild paired Estate duplicates for an isolated 12-versus-32-card test.

Run only in the UE 5.8.3 diagnostic worktree's editor. No runtime placement,
source mesh, material, collision, or production asset is changed here. Both
ArtReview variants must undergo the same explicit rebuild before comparison.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import unreal


version = unreal.SystemLibrary.get_engine_version()
if not version.startswith("5.8.3"):
    raise RuntimeError(f"Lumen card ArtReview requires diagnostic UE 5.8.3; got {version}")
root = Path(unreal.Paths.project_dir()).resolve()
if not (root / ".git").is_file():
    raise RuntimeError("Lumen card ArtReview must run in an isolated Git worktree")

assets = unreal.EditorAssetLibrary
subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
destination = "/Game/Generated/Environment/ArtReview/Diagnostics/LumenCards32"
assets.make_directory(destination)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def material_signature(mesh: unreal.StaticMesh) -> list[tuple[str, str]]:
    result = []
    for slot in mesh.get_editor_property("static_materials"):
        bound = slot.get_editor_property("material_interface")
        result.append((str(slot.get_editor_property("material_slot_name")),
                       bound.get_path_name() if bound else ""))
    return result


def bounds_signature(mesh: unreal.StaticMesh) -> tuple[float, ...]:
    bounds = mesh.get_bounds()
    origin = bounds.get_editor_property("origin")
    extent = bounds.get_editor_property("box_extent")
    return (origin.x, origin.y, origin.z,
            extent.x, extent.y, extent.z,
            bounds.get_editor_property("sphere_radius"))


def mesh_signature(mesh: unreal.StaticMesh) -> tuple:
    return (mesh.get_num_triangles(0),
            material_signature(mesh),
            mesh.get_editor_property("nanite_settings").to_tuple(),
            bounds_signature(mesh))


for name in ("SM_Nyaagyu_EstateDojo", "SM_Nyaagyu_ProvisionKura"):
    source_path = f"/Game/Generated/Environment/Props/{name}"
    source_file = root / "Content/Generated/Environment/Props" / (name + ".uasset")
    if not source_file.is_file():
        raise RuntimeError(f"Original imported building package missing: {source_file}")
    before_hash = sha256(source_file)
    source = assets.load_asset(source_path)
    if not isinstance(source, unreal.StaticMesh):
        raise RuntimeError(f"Original building is not a StaticMesh: {source_path}")
    source_build = subsystem.get_lod_build_settings(source, 0)
    source_cards = source_build.get_editor_property("max_lumen_mesh_cards")
    if source_cards != 12:
        raise RuntimeError(f"Expected 12 original Lumen cards for {name}; got {source_cards}")
    source_signature = mesh_signature(source)
    rebuilt: dict[int, unreal.StaticMesh] = {}
    rebuilt_settings: dict[int, dict] = {}

    for cards in (12, 32):
        target_name = name + f"_LumenCards{cards}Rebuilt"
        target_path = f"{destination}/{target_name}"
        # Replace only our namespaced duplicates, leaving the original untouched.
        if assets.does_asset_exist(target_path) and not assets.delete_asset(target_path):
            raise RuntimeError(f"Could not replace old ArtReview duplicate: {target_path}")
        duplicate = assets.duplicate_asset(source_path, target_path)
        if not isinstance(duplicate, unreal.StaticMesh):
            raise RuntimeError(f"Could not duplicate original building: {source_path}")
        build = subsystem.get_lod_build_settings(duplicate, 0)
        if build.get_editor_property("max_lumen_mesh_cards") != 12:
            raise RuntimeError(f"Duplicate did not inherit the 12-card source: {target_path}")
        build.set_editor_property("max_lumen_mesh_cards", cards)
        # UE's subsystem calls PostEditChange even for the 12-card control.
        subsystem.set_lod_build_settings(duplicate, 0, build)
        if not assets.save_loaded_asset(duplicate):
            raise RuntimeError(f"Could not save rebuilt ArtReview mesh: {target_path}")
        readback = subsystem.get_lod_build_settings(duplicate, 0)
        if readback.get_editor_property("max_lumen_mesh_cards") != cards:
            raise RuntimeError(f"ArtReview card setting did not persist: {target_path}")
        rebuilt[cards] = duplicate
        rebuilt_settings[cards] = readback.to_dict()
        unreal.log(f"SORA_LUMEN_CARDS_REBUILT: {target_path} cards={cards} "
                   f"triangles={duplicate.get_num_triangles(0)} "
                   f"materials={material_signature(duplicate)} "
                   f"nanite={duplicate.get_editor_property('nanite_settings').to_dict()} "
                   f"bounds={bounds_signature(duplicate)}")

    control_signature = mesh_signature(rebuilt[12])
    candidate_signature = mesh_signature(rebuilt[32])
    if control_signature != candidate_signature:
        raise RuntimeError(f"Rebuilt ArtReview clones differ in geometry/materials/Nanite/bounds: "
                           f"{name}; control={control_signature}; candidate={candidate_signature}")
    control_settings = dict(rebuilt_settings[12])
    candidate_settings = dict(rebuilt_settings[32])
    control_settings.pop("max_lumen_mesh_cards")
    candidate_settings.pop("max_lumen_mesh_cards")
    if control_settings != candidate_settings:
        raise RuntimeError(f"Rebuilt ArtReview clones differ in another LOD build setting: {name}")
    if (subsystem.get_lod_build_settings(source, 0).get_editor_property("max_lumen_mesh_cards")
            != 12 or sha256(source_file) != before_hash or mesh_signature(source) != source_signature):
        raise RuntimeError(f"Original building package changed during ArtReview: {source_path}")
    unreal.log(f"SORA_LUMEN_CARDS_PAIRED_READY: {source_path}; control=12 candidate=32 "
               f"rebuilt_triangles={control_signature[0]} source_triangles={source_signature[0]} "
               f"source_sha256={before_hash}")
