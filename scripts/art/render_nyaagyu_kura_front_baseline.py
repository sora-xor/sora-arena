"""Matched eye-height source render of the unchanged Kura for frontage A/B.

Run before create_nyaagyu_kura_front.py with Blender 5.2.2 LTS. This is a
Blender source comparison, not evidence of in-engine game quality.
"""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "Content/SourceArt/Environment/NyaagyuKura/Nyaagyu_ProvisionKura.blend"
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuKuraFront"
bpy.ops.wm.open_mainfile(filepath=str(BASE))
stage = bpy.data.collections.get("ArtReview_NotForFBX")
if stage:
    for obj in list(stage.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(stage)
for obj in list(bpy.data.objects):
    if obj.type in {"CAMERA", "LIGHT"}:
        bpy.data.objects.remove(obj, do_unlink=True)


def area(name, loc, energy, color, size, target):
    bpy.ops.object.light_add(type="AREA", location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.data.energy = energy
    ob.data.color = color
    ob.data.shape = "DISK"
    ob.data.size = size
    ob.rotation_euler = (Vector(target)-ob.location).to_track_quat("-Z","Y").to_euler()


area("EyeHeight_WarmSky",(-4.6,-7,7.5),1600,(1,.79,.61),6,(0,-3,2))
area("EyeHeight_CoolBounce",(4,-5,5.5),950,(.69,.82,1),5,(0,-3,2))
bpy.ops.object.camera_add(location=(4.8,-10,1.58))
camera = bpy.context.object
camera.name = "KuraFront_Close_EyeHeight_Baseline"
camera.rotation_euler = (Vector((0,-3.1,2.25))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.type = "PERSP"
camera.data.lens = 32
scene = bpy.context.scene
scene.camera = camera
scene.world.color = (.16,.17,.19)
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 1400
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -.4
OUT.mkdir(parents=True,exist_ok=True)
scene.render.filepath = str(OUT/"KuraFront_Baseline_EyeHeight_Source.png")
scene.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)
print("NYAAGYU_KURA_FRONT_BASELINE_SOURCE_READY",scene.render.filepath,flush=True)
