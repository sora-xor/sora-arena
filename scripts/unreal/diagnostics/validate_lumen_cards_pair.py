"""Fresh-editor readback gate for the isolated Estate Lumen-card ArtReview pair.

Run after import and before applying the diagnostic runtime selector. A failed
pair must never be packaged as a controlled 12-versus-32 card comparison.
"""

from pathlib import Path
import hashlib
import sys

import unreal


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Lumen-card paired readback")
root = Path(unreal.Paths.project_dir()).resolve()
if not (root / ".git").is_file():
    raise RuntimeError("Lumen-card paired readback requires an isolated Git worktree")

assets = unreal.EditorAssetLibrary
subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
destination = "/Game/Generated/Environment/ArtReview/Diagnostics/LumenCards32"


def signature(mesh):
    bounds = mesh.get_bounds()
    origin = bounds.get_editor_property("origin")
    extent = bounds.get_editor_property("box_extent")
    materials = []
    for slot in mesh.get_editor_property("static_materials"):
        bound = slot.get_editor_property("material_interface")
        materials.append((str(slot.get_editor_property("material_slot_name")),
                          bound.get_path_name() if bound else ""))
    return {
        "triangles": mesh.get_num_triangles(0),
        "materials": materials,
        "nanite": mesh.get_editor_property("nanite_settings").to_tuple(),
        "bounds": (origin.x, origin.y, origin.z, extent.x, extent.y, extent.z,
                   bounds.get_editor_property("sphere_radius")),
    }


for name in ("SM_Nyaagyu_EstateDojo", "SM_Nyaagyu_ProvisionKura"):
    source = assets.load_asset(f"/Game/Generated/Environment/Props/{name}")
    if not isinstance(source, unreal.StaticMesh):
        raise RuntimeError(f"Original building missing: {name}")
    if subsystem.get_lod_build_settings(source, 0).get_editor_property("max_lumen_mesh_cards") != 12:
        raise RuntimeError(f"Original building no longer has 12 cards: {name}")
    pair = {}
    settings = {}
    for cards in (12, 32):
        path = f"{destination}/{name}_LumenCards{cards}Rebuilt"
        mesh = assets.load_asset(path)
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError(f"Rebuilt ArtReview mesh missing: {path}")
        build = subsystem.get_lod_build_settings(mesh, 0)
        if build.get_editor_property("max_lumen_mesh_cards") != cards:
            raise RuntimeError(f"Card setting did not persist for {path}")
        pair[cards] = signature(mesh)
        settings[cards] = build.to_dict()
        unreal.log(f"SORA_LUMEN_CARDS_PAIRED_READBACK: {path} cards={cards} {pair[cards]}")
    if pair[12] != pair[32]:
        raise RuntimeError(f"Rebuilt ArtReview pair differs beyond card budget: {name}; "
                           f"control={pair[12]}; candidate={pair[32]}")
    for build in settings.values():
        build.pop("max_lumen_mesh_cards")
    if settings[12] != settings[32]:
        raise RuntimeError(f"Rebuilt ArtReview pair differs in other build settings: {name}")
    source_file = root / "Content/Generated/Environment/Props" / (name + ".uasset")
    if not source_file.is_file():
        raise RuntimeError(f"Original package missing: {source_file}")
    original_sha = hashlib.sha256(source_file.read_bytes()).hexdigest()
    unreal.log(f"SORA_LUMEN_CARDS_PAIRED_READBACK_READY: {name} "
               f"triangles={pair[12]['triangles']} source_sha256={original_sha}")
