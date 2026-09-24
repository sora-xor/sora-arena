"""Render an unedited, source-only WeaponRoot translation A/B.

Run with Blender 5.2.2 LTS from the repository root. No Unreal or gameplay
asset is touched. Only translation changes between Current and Proposed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Content/SourceArt/Characters/NyaakotoBokutoViewmodel"
OUT = SOURCE / "PoseProbe"
OUT.mkdir(parents=True, exist_ok=True)
source_record = json.loads((SOURCE / "manifest.json").read_text())
blend = SOURCE / "Nyaakoto_BokutoPaws.blend"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


assert sha(blend) == source_record["outputs"][blend.name]["sha256"]
assert source_record["idle_review_transform"] == {
    "weapon_root_location_cm":[40,18,-18], "mesh_scale":.75,
    "camera_horizontal_fov_degrees":70}

bpy.ops.wm.open_mainfile(filepath=str(blend))
scene = bpy.context.scene
camera = bpy.data.objects["Camera_NormalIdlePose_FOV70"]
assert tuple(camera.location) == (0.0,0.0,0.0)
scene.camera = camera
model = bpy.data.collections["Nyaakoto_BokutoPaws_Editable"]
prop = bpy.data.collections["ReviewOnly_RealBokuto"]
model_objects = [o for o in model.objects if o.type in {"MESH","ARMATURE"}]
prop_objects = [o for o in prop.objects if o.type == "MESH"]
assert len(prop_objects) == 4
assert len([o for o in prop_objects if o.name.startswith("ReviewOnly_Tsuka_")]) == 1
original = {obj:obj.matrix_world.copy() for obj in [*model_objects,*prop_objects]}
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_x = 1600
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
assert scene.render.engine == "CYCLES"


def subject(which):
    model.hide_render = which not in {"Full","PawsOnly"}
    prop.hide_render = which not in {"Full","BokutoOnly","GripOnly"}
    for obj in prop_objects:
        obj.hide_render = which == "GripOnly" and not obj.name.startswith("ReviewOnly_Tsuka_")


outputs = {}


def render(name, which):
    subject(which)
    path = OUT / f"{name}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    outputs[path.name] = {"sha256":sha(path),"bytes":path.stat().st_size}


# The empty frame is a raw renderer output and supplies the exact background
# for objective occupied-pixel and reticle-clearance measurements.
render("Empty_SameCameraAndLight","Empty")
for name,cm in (("Current",(40,18,-18)),("Proposed",(40,8,-7))):
    transform = Matrix.Translation(Vector(v/100 for v in cm)) @ Matrix.Scale(.75,4)
    for obj,base in original.items():
        obj.matrix_world = transform @ base
    for which in ("Full","BokutoOnly","GripOnly","PawsOnly"):
        render(f"{name}_{which}",which)

record = {
    "schema_version":1,
    "status":"source-only pose probe; Blender camera does not implement Unreal FirstPersonScale",
    "source_blend_sha256":sha(blend),
    "source_manifest_sha256":sha(SOURCE / "manifest.json"),
    "camera":"Camera_NormalIdlePose_FOV70",
    "horizontal_fov_degrees":70,
    "resolution":[1600,900],
    "mesh_scale":.75,
    "current_root_cm":[40,18,-18],
    "proposed_root_cm":[40,8,-7],
    "rotation_degrees":[0,0,0],
    "geometry_materials_camera_lights":"identical in both poses",
    "outputs":outputs,
}
(OUT / "manifest.json").write_text(json.dumps(record,indent=2)+"\n")
print("NYAAKOTO_POSE_PROBE_RENDERED",len(outputs),flush=True)
