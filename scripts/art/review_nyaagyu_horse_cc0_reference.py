"""Render fixed clay comparison of the isolated horse and an external CC0 OBJ.

Usage: blender -b --factory-startup --python this_file -- --zip /tmp/horse.zip
       --out /tmp/sora-horse-reference-review

The external archive is unpacked only into a temporary directory. It is never
copied into the game or saved in the new Blender source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
import zipfile
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def args():
    parser=argparse.ArgumentParser()
    parser.add_argument("--zip",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--")+1:])


A=args()
A.out.mkdir(parents=True,exist_ok=True)
ROOT=Path(__file__).resolve().parents[2]
STUDY=ROOT/"Content/SourceArt/Horses/Nyaagyu/AnatomyStudy/Nyaagyu_Horse_AnatomyStudy.blend"
zip_sha=hashlib.sha256(A.zip.read_bytes()).hexdigest()
bpy.context.preferences.filepaths.save_version=0


def camera_and_render(label,objects):
    scene=bpy.context.scene
    scene.render.engine="BLENDER_WORKBENCH"
    scene.render.resolution_x=1400
    scene.render.resolution_y=900
    scene.render.resolution_percentage=100
    scene.render.film_transparent=False
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="SINGLE"
    scene.display.shading.single_color=(.64,.62,.59)
    scene.display.shading.show_shadows=True
    scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type="BOTH"
    scene.display.shading.background_type="WORLD"
    if scene.world is None:
        scene.world=bpy.data.worlds.new("ReferenceReviewWorld")
    scene.world.color=(.045,.047,.051)
    camera_data=bpy.data.cameras.new("Fixed_Review_Camera")
    camera=bpy.data.objects.new("Fixed_Review_Camera",camera_data)
    scene.collection.objects.link(camera)
    scene.camera=camera
    camera_data.type="ORTHO"
    for view,location,target,scale in (
        ("profile",(0,-4.0,.95),(0,0,.95),3.30),
        ("front",(4.0,0,.95),(0,0,.95),3.30),
    ):
        camera.location=location
        camera.rotation_euler=(Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler()
        camera_data.ortho_scale=scale
        scene.render.filepath=str(A.out/f"{label}_{view}.png")
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera,do_unlink=True)
    return {view:hashlib.sha256((A.out/f"{label}_{view}.png").read_bytes()).hexdigest()
            for view in ("profile","front")}


def turntable_render():
    scene=bpy.context.scene
    camera_data=bpy.data.cameras.new("Eight_View_Review_Camera")
    camera=bpy.data.objects.new("Eight_View_Review_Camera",camera_data)
    scene.collection.objects.link(camera)
    scene.camera=camera
    camera_data.type="ORTHO"
    camera_data.ortho_scale=3.30
    paths={}
    for degrees in (0,45,90,135,180,225,270,315):
        angle=math.radians(degrees)
        camera.location=(4.0*math.cos(angle),4.0*math.sin(angle),.95)
        camera.rotation_euler=(Vector((0,0,.95))-camera.location).to_track_quat("-Z","Y").to_euler()
        path=A.out/f"nyaagyu_study_turntable_{degrees:03}.png"
        scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        paths[str(degrees)]=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.data.objects.remove(camera,do_unlink=True)
    return paths


def bounds(objects):
    points=[obj.matrix_world@Vector(corner) for obj in objects for corner in obj.bound_box]
    low=[min(p[i] for p in points) for i in range(3)]
    high=[max(p[i] for p in points) for i in range(3)]
    return {"min_m":[round(x,4) for x in low],"max_m":[round(x,4) for x in high],
            "extent_m":[round(hi-lo,4) for hi,lo in zip(high,low)]}


with tempfile.TemporaryDirectory(prefix="sora-rancher-cc0-") as tmp:
    with zipfile.ZipFile(A.zip) as source:
        allowed={"horse/LD_HorseRtime02.obj","horse/LD_HorseRtime02.mtl",
                 "horse/HorseMain2k00.png","horse/eye_texture.png",
                 "horse/Hair12Main2k.png","horse/HorseMain2k00Norm00.png",
                 "horse/HorseMain2k00AO00.png","horse/Hair12Main2kNorm.png"}
        assert set(source.namelist())==allowed|{"horse/"}
        assert all(not Path(n).is_absolute() and ".." not in Path(n).parts for n in source.namelist())
        source.extractall(tmp)
    mtl=Path(tmp)/"horse/LD_HorseRtime02.mtl"
    mtl.write_text(mtl.read_text().replace("LD_HorseRtime02.blend/",""))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=str(Path(tmp)/"horse/LD_HorseRtime02.obj"))
    rancher=[o for o in bpy.data.objects if o.type=="MESH" and o.name!="Cube"]
    assert len(rancher)==5
    # OBJ: longitudinal -Y is forward. Place hooves at Z=0 and normalize
    # whole-model height to the Nyaagyu source's 1.83 m ear height for a
    # silhouette comparison; this is NOT a historical body-size claim.
    main=next(o for o in rancher if o.name=="Plane")
    raw=[main.matrix_world@v.co for v in main.data.vertices]
    raw_min_z=min(v.z for v in raw)
    raw_max_z=max(v.z for v in raw)
    scale=1.83/(raw_max_z-raw_min_z)
    rotate=Matrix.Rotation(math.pi/2,4,"Z")
    transform=Matrix.Translation((0,0,-raw_min_z*scale))@rotate@Matrix.Scale(scale,4)
    for obj in rancher:obj.matrix_world=transform@obj.matrix_world
    main_bounds=[main.matrix_world@v.co for v in main.data.vertices]
    x_center=(min(v.x for v in main_bounds)+max(v.x for v in main_bounds))*.5
    for obj in rancher:obj.location.x-=x_center
    rancher_tris=sum(len(p.vertices)-2 for o in rancher for p in o.data.polygons)
    rancher_images=camera_and_render("rancher_cc0",rancher)

bpy.ops.wm.open_mainfile(filepath=str(STUDY))
anatomy=bpy.data.collections["AnatomyStudy_Editable"]
tack=bpy.data.collections["NyaagyuHorse_Editable"]
model=[o for o in (*anatomy.objects,*tack.objects) if o.type=="MESH"]
assert model
for coll_name in ("Blender_Review_Only","AnatomyStudy_Export_Only"):
    coll=bpy.data.collections.get(coll_name)
    if coll:coll.hide_render=True
tack.hide_render=True
for obj in anatomy.objects:
    if "_kura_" in obj.name:obj.hide_render=True
bare_images=camera_and_render("nyaagyu_anatomy_bare",model)
tack.hide_render=False
for obj in anatomy.objects:
    if "_kura_" in obj.name:obj.hide_render=False
study_images=camera_and_render("nyaagyu_study_saddled",model)
turntable=turntable_render()
structural=[o for o in anatomy.objects if any(fragment in o.name for fragment in (
    "arched_crosspiece","side_tree","shaped_seat"))]
abumi=[o for o in tack.objects if o.type=="MESH" and o.name.startswith("Abumi_-1_")
       and any(fragment in o.name for fragment in (
           "broad_iron_footplate","wooden_tread","hato_mune_iron_toe_shell","iron_side_"))]
assert len(structural)==5 and len(abumi)>=4
record={
    "archive_url":"https://opengameart.org/sites/default/files/horse.zip",
    "archive_sha256":zip_sha,
    "source_page":"https://opengameart.org/content/realtime-ranchers-3d-model-pack",
    "page_license":"CC0 1.0 (OpenGameArt author lyndon; archive has no separate license file)",
    "archive_entries":sorted(allowed),
    "rancher_source_triangles":rancher_tris,
    "normalization":"Both renders share ground Z=0 and approximately 1.83 m full ear height; reference size is an arbitrary comparison scale, not historical evidence.",
    "views":{"rancher_cc0":rancher_images,"nyaagyu_anatomy_bare":bare_images,
             "nyaagyu_study_saddled":study_images},
    "turntable_sha256":turntable,
    "kura_structural_bounds":bounds(structural),
    "abumi_left_toe_bounds":bounds(abumi),
    "reference_mesh_in_game":False,
}
(A.out/"comparison_manifest.json").write_text(json.dumps(record,indent=2)+"\n")
print("NYAAGYU_RANCHER_REFERENCE_RENDER_COMPLETE",rancher_tris,zip_sha)
