"""Render fixed-camera look-development captures of the CC0 environment library.

Run in the pinned editor *with* a renderer (not ``-nullrhi``), after
``import-mac.sh``; for example::

    scripts/toolchain/run-editor.sh -RenderOffScreen -unattended -nosplash -nosound \
        -ExecutePythonScript=$PWD/scripts/unreal/render_cc0_environment_lookdev.py

It builds ``/Game/Generated/Environment/CC0/LookDev/L_CC0LookDev`` (generated,
never shipped): one sample per material instance on engine cubes (world-aligned
surfaces: top = floor projection, sides = wall projection), cylinders (bark),
spheres (mesh-UV props, cloth, lantern paper) and the scanned meshes at their
measured size, lit by the lighting-only Kloofendal misty-morning HDRI and a
5200 K sun under fixed manual exposure. Each group is captured dry and again
with ``MPC_EnvironmentWeather`` at Wetness 1 / PuddleAmount 0.7, into
``Saved/CC0LookDev/``. Taking the screenshots compiles every master and
instance permutation for the running platform; the log must then show no
material or shader errors. These are look-development captures on engine
primitives, not in-game photoreal approvals.
"""

from __future__ import annotations

from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402
import cc0_environment_library as library  # noqa: E402

require_running_engine("CC0 environment look development")
require = library.require
ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / "Saved/CC0LookDev"
LEVEL = f"{library.PACKAGE_ROOT}/LookDev/L_CC0LookDev"
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ASSETS = unreal.EditorAssetLibrary
SPACING = 280.0
GROUPS = (
    ("architecture", ("HinokiFloor", "EngawaHinoki", "SugiHameita", "SugiBoardWall", "ItabukiRoof", "Tsuchikabe",
                      "CharcoalHutDaub", "Shikkui", "Tatami", "IbushiKawara", "AjiroTakegaki", "TakegakiPanel")),
    ("ground", ("RojiStonePath", "PackedEarthRoad", "GravelPitch", "ValleyFloor", "MossForestFloor", "StreamBed",
                "MossBank", "MossRockSet01", "MossRockSet02", "Boulder01", "TreeStump01", "MossClump01")),
    ("roofs_bark", ("KayabukiThatchField", "MossyThatch", "WaraStraw", "MakiwaraStraw", "SugiBark", "MatsuBark",
                    "KeyakiBark", "YamazakuraBark", "MomijiBark", "KusunokiBark", "RootCluster01")),
    ("fibre_lantern", ("HempLashing", "HempRope", "TackLeather", "ArmorChestLeather", "TakeKago", "AsaSacking",
                       "AsaHorseBlanket", "JinmakuSilk", "PackWrapCloth", "ShitaguraPad", "ChochinPaper",
                       "AndonPaper")),
)


def load(path):
    asset = unreal.load_asset(path)
    require(asset is not None, f"Missing {path}; run scripts/toolchain/import-mac.sh first")
    return asset


def spawn(cls, location, rotation=(0.0, 0.0, 0.0)):
    return ACTORS.spawn_actor_from_class(cls, unreal.Vector(*location), unreal.Rotator(*rotation))


def mesh_actor(mesh, material, location, scale, rotation=(0.0, 0.0, 0.0)):
    actor = spawn(unreal.StaticMeshActor, location, rotation)
    component = actor.static_mesh_component
    component.set_static_mesh(mesh)
    if material is not None:
        for index in range(component.get_num_materials()):
            component.set_material(index, material)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    return actor


def label(text, location):
    actor = spawn(unreal.TextRenderActor, location, (0.0, 180.0, 0.0))
    component = actor.text_render
    component.set_text(text)
    component.set_world_size(13.0)
    component.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    component.set_text_render_color(unreal.Color(235, 235, 235, 255))


def sample(plan, instance, location):
    """Place one representative object for an instance centred at location (on the ground)."""
    x, y, _ = location
    material = load(library.instance_path(instance))
    family = library.MASTERS[instance.master].family
    meshes = [mesh for mesh in plan.meshes if mesh.instance == instance.name]
    if meshes:
        mesh = meshes[0]
        _, asset = mesh.assets[0]
        static_mesh = load(f"{mesh.folder}/{asset}.{asset}")
        scale = 10.0 if family == "foliage" else 1.0  # 3-4 cm moss sprigs: shown x10
        count = min(len(mesh.assets), 5) if family == "foliage" else 1
        for index in range(count):
            _, asset = mesh.assets[index]
            mesh_actor(load(f"{mesh.folder}/{asset}.{asset}"), None,
                       (x + (index - count // 2) * 25.0, y, 0.0), (scale,) * 3)
        return " (x10)" if scale != 1.0 else ""
    if family in library.WORLD_ALIGNED_FAMILIES and instance.world_aligned:
        mesh_actor(load("/Engine/BasicShapes/Cube.Cube"), material, (x, y, 45.0), (1.6, 1.6, 0.9))
    elif "Bark" in instance.name:
        mesh_actor(load("/Engine/BasicShapes/Cylinder.Cylinder"), material, (x, y, 90.0), (0.7, 0.7, 1.8))
    elif family == "lantern":
        mesh_actor(load("/Engine/BasicShapes/Sphere.Sphere"), material, (x, y, 80.0), (0.5, 0.5, 0.7))
    else:
        mesh_actor(load("/Engine/BasicShapes/Sphere.Sphere"), material, (x, y, 60.0), (1.2, 1.2, 1.2))
    return ""


def build_scene(plan):
    if ASSETS.does_asset_exist(LEVEL):
        require(LEVELS.load_level(LEVEL), f"Could not load {LEVEL}")
        for actor in ACTORS.get_all_level_actors():
            ACTORS.destroy_actor(actor)
    else:
        require(LEVELS.new_level(LEVEL), f"Could not create {LEVEL}")
    by_suffix = {instance.name.split("_", 2)[2]: instance for instance in plan.instances if not instance.evaluation}
    evaluation = [instance for instance in plan.instances if instance.evaluation]
    groups = list(GROUPS) + [(f"evaluation_{index}", tuple(i.name for i in evaluation[index:index + 16]))
                             for index in range(0, len(evaluation), 16)]
    shots = []
    for group_index, (group, names) in enumerate(groups):
        origin_y = group_index * 1600.0
        columns = 4
        for index, name in enumerate(names):
            instance = by_suffix.get(name) or next(item for item in evaluation if item.name == name)
            row, column = divmod(index, columns)
            x, y = row * SPACING * 1.25, origin_y + (column - (columns - 1) / 2) * SPACING
            suffix = sample(plan, instance, (x, y, 0.0))
            label(instance.name.removeprefix("MI_") + suffix, (x - 115.0, y, 4.0))
        rows = (len(names) + columns - 1) // columns
        camera = spawn(unreal.CameraActor, (-560.0, origin_y, 430.0 + rows * 40.0), (-26.0, 0.0, 0.0))
        camera.camera_component.set_editor_property("field_of_view", 62.0)
        shots.append((group, camera))
    ground = mesh_actor(load("/Engine/BasicShapes/Plane.Plane"), None, (1200.0, 4000.0, 0.0), (80.0, 120.0, 1.0))
    ground.static_mesh_component.set_material(0, load("/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial"))
    sun = spawn(unreal.DirectionalLight, (0.0, 0.0, 800.0), (-38.0, 35.0, 0.0))
    light = sun.light_component
    light.set_intensity(3.0)
    light.set_use_temperature(True)
    light.set_temperature(5200.0)
    sky = spawn(unreal.SkyLight, (0.0, 0.0, 600.0))
    sky_component = sky.light_component
    sky_component.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky_component.set_cubemap(load(f"{library.HDRI}/HDRI_KloofendalMistyMorning.HDRI_KloofendalMistyMorning"))
    sky_component.set_intensity(1.0)
    sky_component.recapture_sky()
    volume = spawn(unreal.PostProcessVolume, (0.0, 0.0, 0.0))
    volume.set_editor_property("unbound", True)
    settings = volume.get_editor_property("settings")
    for key, value in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                       ("auto_exposure_apply_physical_camera_exposure", False),
                       ("auto_exposure_bias", 0.0)):
        settings.set_editor_property(f"override_{key}", True)
        settings.set_editor_property(key, value)
    volume.set_editor_property("settings", settings)
    return shots


def main():
    plan = library.build_plan(ROOT, verify=False)
    OUT.mkdir(parents=True, exist_ok=True)
    shots = build_scene(plan)
    mpc = load(library.mpc_path())
    world = unreal.EditorLevelLibrary.get_editor_world()
    queue = [(f"{group}_{state}", camera, state) for state in ("dry", "wet") for group, camera in shots]
    status = {"task": None, "frames": 0, "written": []}

    def weather(state):
        wet = state == "wet"
        unreal.KismetMaterialLibrary.set_scalar_parameter_value(world, mpc, "Wetness", 1.0 if wet else 0.0)
        unreal.KismetMaterialLibrary.set_scalar_parameter_value(world, mpc, "PuddleAmount", 0.7 if wet else 0.0)

    def tick(_delta):
        status["frames"] += 1
        if status["frames"] < 30:  # let the editor viewport settle after level creation
            return
        task = status["task"]
        if task is not None and not task.is_task_done():
            return
        if task is not None:
            status["written"].append(status["current"])
        if not queue:
            unreal.unregister_slate_post_tick_callback(handle)
            unreal.log("SORA_CC0_LOOKDEV_COMPLETE: " + ", ".join(str(path) for path in status["written"]))
            unreal.SystemLibrary.quit_editor()
            return
        name, camera, state = queue.pop(0)
        weather(state)
        status["current"] = OUT / f"{name}.png"
        status["task"] = unreal.AutomationLibrary.take_high_res_screenshot(
            1920, 1080, str(status["current"]), camera, False, False,
            unreal.ComparisonTolerance.LOW, "", 4.0, True)

    handle = unreal.register_slate_post_tick_callback(tick)


main()
