"""Editor phases for the opt-in UE 5.8 Mesh Partition research map.

Only run via run_mesh_partition_research.py in an isolated project worktree.
The normal campaign world and its collision are never changed by this script.
"""

import hashlib
import json
import os
from pathlib import Path
import sys

import unreal


SOURCE_MAP = "/Game/Research/NyaagyuMeshTerrain_Source"
WP_MAP = SOURCE_MAP + "_WP"
TERRAIN_PACKAGE = "/Game/Generated/Environment/Terrain"
MATERIALS = (
    "/Game/Generated/Environment/MI_Nyaagyu_Soil",
    "/Game/Generated/Environment/MI_Nyaagyu_Stone",
)


def require(value, message):
    if not value:
        raise RuntimeError("SORA_MESH_RESEARCH_REJECTED: " + message)


project = Path(unreal.Paths.project_dir()).resolve()
phase = os.environ.get("SORA_MESH_RESEARCH_PHASE", "")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import ENGINE_VERSION  # noqa: E402

engine_version = unreal.SystemLibrary.get_engine_version()
require(engine_version == ENGINE_VERSION,
        f"Expected pinned UE {ENGINE_VERSION}, found {engine_version}")
require(phase in ("stage", "author", "verify"), "Unknown research phase")


def load_hi_tiles():
    source = project / "Content/SourceArt/Environment/NyaagyuTerrain"
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    require(manifest.get("schema_version") == 1 and manifest.get("tile_layout") == [4, 4]
            and manifest.get("tile_size_cm") == [1600, 1300]
            and manifest.get("world_xy_cm") == [-3200, -2600, 3200, 2600],
            "Estate source manifest has changed")
    hi = [tile for tile in manifest["tiles"] if tile["tier"] == "hi"]
    require(len(hi) == 16 and len({tuple(tile["index"]) for tile in hi}) == 16,
            "Expected exactly 16 unique HI source tiles")
    for tile in hi:
        x, y = tile["index"]
        name = f"SM_NyaagyuTerrain_HI_X{x}_Y{y}"
        fbx = source / tile["fbx"]
        require(tile["name"] == name and tile["triangles"] == 26624
                and tile["placement_center_cm"] == [-2400 + 1600*x, -1950 + 1300*y, 0]
                and fbx.is_file()
                and hashlib.sha256(fbx.read_bytes()).hexdigest() == tile["fbx_sha256"],
                f"HI source tile identity, placement, or hash changed: {name}")
        asset = unreal.EditorAssetLibrary.load_asset(f"{TERRAIN_PACKAGE}/{name}")
        require(isinstance(asset, unreal.StaticMesh), f"Imported UE static mesh missing: {name}")
        tile["asset"] = asset
    return sorted(hi, key=lambda tile: (tile["index"][1], tile["index"][0]))


if phase == "stage":
    require(not unreal.EditorAssetLibrary.does_asset_exist(SOURCE_MAP)
            and not unreal.EditorAssetLibrary.does_asset_exist(WP_MAP),
            "Research map already exists; refusing to replace it")
    hi_tiles = load_hi_tiles()
    material_assets = [unreal.EditorAssetLibrary.load_asset(path) for path in MATERIALS]
    require(all(isinstance(material, unreal.MaterialInterface) for material in material_assets),
            "Project PBR soil/stone material instances are missing")
    unreal.EditorAssetLibrary.make_directory("/Game/Research")
    require(unreal.EditorLevelLibrary.new_level(SOURCE_MAP), "Could not create separate source map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for tile in hi_tiles:
        name = tile["name"]
        center = tile["placement_center_cm"]
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor,
                                              unreal.Vector(*center), unreal.Rotator(0, 0, 0))
        require(actor is not None, f"Could not spawn source actor: {name}")
        actor.set_actor_label(f"ResearchTerrain_{name}")
        component = actor.get_editor_property("static_mesh_component")
        require(component.set_static_mesh(tile["asset"]), f"Could not assign imported mesh: {name}")
        for index, material in enumerate(material_assets):
            component.set_material(index, material)
    require(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, False),
            "Could not save research source map")
    require(unreal.EditorAssetLibrary.does_asset_exist(SOURCE_MAP), "Source map did not persist")
    unreal.log("SORA_MESH_RESEARCH_STAGE_COMPLETE: 16 source HI actors")

elif phase == "author":
    require(unreal.EditorAssetLibrary.does_asset_exist(WP_MAP),
            "World Partition conversion map is missing")
    world = unreal.EditorLoadingAndSavingUtils.load_map(WP_MAP)
    require(world is not None, "Could not load World Partition research map")
    require(unreal.SoraMeshTerrainResearchLibrary.convert_placed_hi_tiles(),
            "Native Mesh Partition base conversion rejected the level")
    require(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True),
            "Could not save Mesh Partition actor and 16 base modifiers")
    unreal.log("SORA_MESH_RESEARCH_AUTHOR_COMPLETE: saved native Mesh Partition and base modifiers")

elif phase == "verify":
    require(unreal.EditorAssetLibrary.does_asset_exist(WP_MAP),
            "World Partition research map is missing")
    world = unreal.EditorLoadingAndSavingUtils.load_map(WP_MAP)
    require(world is not None, "Could not load compiled World Partition research map")
    require(unreal.SoraMeshTerrainResearchLibrary.verify_compiled_sections(),
            "Compiled runtime section provenance or static meshes are incomplete")
    unreal.log("SORA_MESH_RESEARCH_VERIFY_COMPLETE: compiled runtime sections validated")
