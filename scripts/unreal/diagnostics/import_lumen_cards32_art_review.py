"""Duplicate the Estate buildings for an isolated 12-versus-32 Lumen-card test.

Run only in the UE 5.8.3 diagnostic worktree's editor. No runtime placement,
source mesh, material, collision, or production asset is changed here.
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


for name in ("SM_Nyaagyu_EstateDojo", "SM_Nyaagyu_ProvisionKura"):
    source_path = f"/Game/Generated/Environment/Props/{name}"
    target_name = name + "_LumenCards32"
    target_path = f"{destination}/{target_name}"
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
    source_materials = material_signature(source)
    source_triangles = source.get_num_triangles(0)
    source_nanite = bool(source.get_editor_property("nanite_settings").get_editor_property("enabled"))

    # Replacing only our namespaced duplicate makes the experiment rerunnable.
    if assets.does_asset_exist(target_path) and not assets.delete_asset(target_path):
        raise RuntimeError(f"Could not replace old ArtReview duplicate: {target_path}")
    candidate = assets.duplicate_asset(source_path, target_path)
    if not isinstance(candidate, unreal.StaticMesh):
        raise RuntimeError(f"Could not duplicate original building: {source_path}")
    candidate_build = subsystem.get_lod_build_settings(candidate, 0)
    if candidate_build.get_editor_property("max_lumen_mesh_cards") != 12:
        raise RuntimeError(f"Duplicate did not inherit the 12-card baseline: {target_path}")
    candidate_build.set_editor_property("max_lumen_mesh_cards", 32)
    # UE's subsystem calls PostEditChange here, requesting a mesh/card rebuild.
    subsystem.set_lod_build_settings(candidate, 0, candidate_build)
    if not assets.save_loaded_asset(candidate):
        raise RuntimeError(f"Could not save rebuilt ArtReview mesh: {target_path}")

    readback = subsystem.get_lod_build_settings(candidate, 0)
    if readback.get_editor_property("max_lumen_mesh_cards") != 32:
        raise RuntimeError(f"ArtReview card setting did not persist: {target_path}")
    if (candidate.get_num_triangles(0) != source_triangles
            or material_signature(candidate) != source_materials
            or bool(candidate.get_editor_property("nanite_settings").get_editor_property("enabled"))
            != source_nanite):
        raise RuntimeError(f"ArtReview duplicated mesh changed beyond card budget: {target_path}")
    if (subsystem.get_lod_build_settings(source, 0).get_editor_property("max_lumen_mesh_cards")
            != 12 or sha256(source_file) != before_hash):
        raise RuntimeError(f"Original building package changed during ArtReview: {source_path}")
    unreal.log(f"SORA_LUMEN_CARDS32_ART_REVIEW_READY: {source_path} -> {target_path}; "
               f"cards=12->32 triangles={source_triangles} source_sha256={before_hash}")
