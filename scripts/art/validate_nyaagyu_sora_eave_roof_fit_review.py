"""Independently check the derived source-only cap/roof fit review.

Checks pinned inputs, retained source meshes, transformed cap meshes, fixed
camera/lights, measured socket clearance, the exposed butt-joint failure, and
output hashes. This is not an Unreal render or historical certification.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
ROOF = ROOT / "Content/SourceArt/Environment/NyaagyuKawaraBay"
CAP = ROOT / "Content/SourceArt/Environment/NyaagyuSoraEaveCapStudy"
OUT = CAP / "RoofBayArtReview"
review = json.loads((OUT / "manifest.json").read_text())
roof_manifest = json.loads((ROOF / "manifest.json").read_text())
cap_manifest = json.loads((CAP / "manifest.json").read_text())
for base, expected, name in (
    (ROOF,review["inputs"]["roof_blend_sha256"],"Nyaagyu_KawaraBay.blend"),
    (ROOF,review["inputs"]["roof_fbx_sha256"],"SM_Nyaagyu_KawaraBay.fbx"),
    (CAP,review["inputs"]["cap_blend_sha256"],"Nyaagyu_SORA_EaveCap.blend"),
    (CAP,review["inputs"]["cap_fbx_sha256"],"SM_Nyaagyu_SORA_EaveCap.fbx"),
):
    assert hashlib.sha256((base/name).read_bytes()).hexdigest()==expected, name
    assert expected == (roof_manifest if base==ROOF else cap_manifest)["outputs"][name]
assert review["inputs"]["sora_svg_sha256"]==cap_manifest["source_svg_sha256"]
for name, expected in review["outputs"].items():
    assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==expected, name


def mesh_snapshot(obj):
    return {
        "vertices":[tuple(obj.matrix_world @ v.co) for v in obj.data.vertices],
        "faces":[tuple(p.vertices) for p in obj.data.polygons],
        "slots":[p.material_index for p in obj.data.polygons],
        "materials":[m.name for m in obj.data.materials],
        "uv":[tuple(float(q) for q in loop.uv)
              for loop in obj.data.uv_layers.active.data],
    }


def light_snapshot(name):
    obj=bpy.data.objects[name]
    return (tuple(tuple(row) for row in obj.matrix_world),
            obj.data.energy,obj.data.size,tuple(obj.data.color))


bpy.ops.wm.open_mainfile(filepath=str(ROOF/"Nyaagyu_KawaraBay.blend"))
roof_scene=bpy.context.scene
original={o.name:mesh_snapshot(o) for o in bpy.data.collections["KawaraBay_Editable"].objects
          if o.type=="MESH"}
assert len(original)==64
camera=(tuple(tuple(row) for row in roof_scene.camera.matrix_world),
        roof_scene.camera.data.ortho_scale)
lights={name:light_snapshot(name) for name in ("SkyKey","SoftFill")}
render=(roof_scene.render.engine,roof_scene.render.resolution_x,
        roof_scene.render.resolution_y,roof_scene.render.resolution_percentage,
        roof_scene.cycles.samples)
background=(tuple(roof_scene.world.node_tree.nodes["Background"].inputs["Color"].default_value),
            roof_scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value)

bpy.ops.wm.open_mainfile(filepath=str(CAP/"Nyaagyu_SORA_EaveCap.blend"))
cap_source={o.name:mesh_snapshot(o) for o in bpy.data.collections["SORA_EaveCap_Editable"].objects}
assert len(cap_source)==6
svg_hash=cap_manifest["source_svg_sha256"]
for index in (0,1):
    obj=bpy.data.objects[f"SORA_ExactSVG_ClayRelief_Path_{index}"]
    assert obj["source_svg_sha256"]==svg_hash

bpy.ops.wm.open_mainfile(filepath=str(OUT/"Nyaagyu_KawaraBay_SORA_Cap_FitReview.blend"))
scene=bpy.context.scene
roof_objects={o.name:o for o in bpy.data.collections["KawaraBay_Editable"].objects
              if o.type=="MESH"}
old=set(review["removed_old_review_badge_only"])
assert old=={"SORA_Kamon_EaveCap","Kamon_Brass_Ring","SORA_Kamon_UserSuppliedLogo"}
assert set(roof_objects)==set(original)-old
assert not old.intersection(bpy.data.objects)
cap_objects={o.name:o for o in bpy.data.collections["SORA_EaveCap_Editable"].objects}
assert set(cap_objects)==set(cap_source)
assert (tuple(tuple(row) for row in scene.camera.matrix_world),
        scene.camera.data.ortho_scale)==camera
assert {name:light_snapshot(name) for name in lights}==lights
assert (scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,
        scene.render.resolution_percentage,scene.cycles.samples)==render
assert (tuple(scene.world.node_tree.nodes["Background"].inputs["Color"].default_value),
        scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value)==background

for name,obj in roof_objects.items():
    actual=mesh_snapshot(obj)
    assert actual==original[name], (name,"roof source changed")

matrix=Matrix(review["fit"]["transform_rows"])
max_cap_error=0.0
for name,obj in cap_objects.items():
    source=cap_source[name]
    actual=mesh_snapshot(obj)
    for key in ("faces","slots","materials","uv"):
        assert actual[key]==source[key], (name,key)
    assert len(actual["vertices"])==len(source["vertices"])
    for a,p in zip(actual["vertices"],source["vertices"]):
        d=(Vector(a)-matrix@Vector(p)).length
        max_cap_error=max(max_cap_error,d)
        assert d<2e-6, (name,d)
    assert obj["roof_fit_review_only"] is True

shank=cap_objects["VaultedCover_SolidClay"]
source_front=cap_source[shank.name]["vertices"][:33]
width=max(x for x,_,_ in source_front)-min(x for x,_,_ in source_front)
scale=review["fit"]["uniform_scale"]
assert abs(width-review["fit"]["measured_cap_shank_front_width_m"])<1e-7
assert abs(scale*width-review["fit"]["nominal_cover_width_m"])<1e-7
assert abs(scale-.8869249650710331)<1e-5

cover=roof_objects["MaruGawara_Cover_R0_C1"]
grid=[cover.data.vertices[row*13:(row+1)*13] for row in range(9)]
world_grid=[[cover.matrix_world@v.co for v in row] for row in grid]


def cover_z(x,y):
    if y<world_grid[0][0].y or y>world_grid[-1][0].y:
        return None
    for row in range(8):
        a,b=world_grid[row],world_grid[row+1]
        if a[0].y<=y<=b[0].y:
            def zx(points):
                for i in range(12):
                    p,q=points[i],points[i+1]
                    if p.x<=x<=q.x:
                        t=(x-p.x)/(q.x-p.x)
                        return p.z*(1-t)+q.z*t
                return None
            za,zb=zx(a),zx(b)
            if za is None or zb is None:
                return None
            t=(y-a[0].y)/(b[0].y-a[0].y)
            return za*(1-t)+zb*t
    return None


shank_top=[shank.matrix_world@v.co for v in shank.data.vertices[:33*14]]
clearance=[]
for p in shank_top:
    z=cover_z(p.x,p.y)
    if z is not None:
        clearance.append((p.z-z)*1000)
stats=review["fit"]["roof_clearance_mm"]
assert len(clearance)==stats["sample_count"]==394
assert abs(min(clearance)-stats["min_clearance_mm"])<.01
assert abs(max(clearance)-stats["max_clearance_mm"])<.01
assert abs(sum(clearance)/len(clearance)-stats["mean_clearance_mm"])<.01
rms=(sum((v-1.5)**2 for v in clearance)/len(clearance))**.5
assert abs(rms-stats["rms_from_intended_clearance_mm"])<.01
surface_pass=(min(clearance)>-3 and max(clearance)<6 and rms<2.5)
assert surface_pass==review["fit"]["surface_alignment_gate_pass"]

next_cover=roof_objects["MaruGawara_Cover_R1_C1"]
next_y=min((next_cover.matrix_world@v.co).y for v in next_cover.data.vertices)
shank_back=(shank.matrix_world@shank.data.vertices[13*33+16].co).y
gap=(next_y-shank_back)*1000
assert abs(gap-review["fit"]["exposed_gap_to_next_cover_mm"])<.01
hidden=gap <= -review["fit"]["hidden_joint_requires_overlap_mm"]
assert hidden==review["fit"]["hidden_joint_gate_pass"]
assert (hidden and surface_pass)==review["fit"]["geometry_gate_pass"]
image=bpy.data.images.load(str(OUT/"Nyaagyu_KawaraBay_SORA_Cap_FixedReview.png"))
assert tuple(image.size)==(1360,900)
print(json.dumps({"status":"passed derivative preservation; visual joint still fails",
                  "roof_meshes_unchanged":len(roof_objects),
                  "molded_cap_meshes":len(cap_objects),
                  "cap_max_transform_error_um":round(max_cap_error*1e6,4),
                  "surface_clearance_rms_mm":round(rms,3),
                  "exposed_gap_to_next_cover_mm":round(gap,3),
                  "overall_geometry_gate_pass":hidden and surface_pass},indent=2))
