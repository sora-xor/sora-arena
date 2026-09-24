"""Derived-only longer socket and smoked-clay crest material comparison.

Starts from the failed exact-source roof fit. Extends only the rear rows of a
copied vaulted shank mesh; the molded SVG crest, disc, collars and first four
shank rows stay geometrically identical. The parent assets are never saved.
Set SORA_EXTENDED_ANALYSIS_ONLY=1 to report geometry without output files.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"Content/SourceArt/Environment/NyaagyuSoraEaveCapStudy/RoofBayArtReview"
OUT=ROOT/"Content/SourceArt/Environment/NyaagyuSoraEaveCapStudy/RoofBayExtendedArtReview"
OUT.mkdir(parents=True,exist_ok=True)
baseline=json.loads((BASE/"manifest.json").read_text())
source=BASE/"Nyaagyu_KawaraBay_SORA_Cap_FitReview.blend"
assert hashlib.sha256(source.read_bytes()).hexdigest()==baseline["outputs"][source.name]
bpy.ops.wm.open_mainfile(filepath=str(source))
scene=bpy.context.scene
camera_matrix=tuple(tuple(row) for row in scene.camera.matrix_world)
light_state={name:(tuple(tuple(row) for row in bpy.data.objects[name].matrix_world),
                   bpy.data.objects[name].data.energy,bpy.data.objects[name].data.size)
             for name in ("SkyKey","SoftFill")}
asset=bpy.data.collections["SORA_EaveCap_Editable"]
objects={obj.name:obj for obj in asset.objects}
assert len(objects)==6
shank=objects["VaultedCover_SolidClay"]
shank.data=shank.data.copy()
front_before=[tuple(v.co) for v in shank.data.vertices[:4*33]]
extension=.080
start_row=4
rows=13
stride=33*(rows+1)
assert len(shank.data.vertices)==stride*2
for skin in (0,1):
    for row in range(start_row,rows+1):
        t=(row-start_row)/(rows-start_row)
        ease=t*t*(3-2*t)
        for col in range(33):
            vertex=shank.data.vertices[skin*stride+row*33+col]
            vertex.co.y+=extension*ease
shank.data.update()
assert [tuple(v.co) for v in shank.data.vertices[:4*33]]==front_before
for index,uv_loop in enumerate(shank.data.uv_layers.active.data):
    vertex=shank.data.vertices[shank.data.loops[index].vertex_index]
    uv_loop.uv.y=max(.01,min(.99,float(vertex.co.y)/(.226+extension)))
bm=bmesh.new(); bm.from_mesh(shank.data)
assert all(edge.is_manifold for edge in bm.edges)
assert bm.calc_volume(signed=True)>0
bm.free()


def tinted_copy(material, name, rgb):
    candidate=material.copy()
    candidate.name=name
    nodes,links=candidate.node_tree.nodes,candidate.node_tree.links
    bsdf=nodes.get("Principled BSDF")
    old=bsdf.inputs["Base Color"].links[0]
    source_socket=old.from_socket
    links.remove(old)
    tint=nodes.new("ShaderNodeMixRGB")
    tint.name="Fictional fired-clay color treatment (art estimate)"
    tint.blend_type="MULTIPLY"
    tint.inputs[0].default_value=1
    tint.inputs[2].default_value=(*rgb,1)
    links.new(source_socket,tint.inputs[1])
    links.new(tint.outputs["Color"],bsdf.inputs["Base Color"])
    return candidate


base_mat=objects["EaveCap_SculptedClay"].data.materials[0]
high_mat=objects["SORA_ExactSVG_ClayRelief_Path_0"].data.materials[0]
body=tinted_copy(base_mat,"M_ReviewOnly_SmokedIbushiCap",(.63,.66,.69))
oxide=tinted_copy(high_mat,"M_ReviewOnly_FictionalIronOxide_SORAClay",(.60,.20,.15))
for name,obj in objects.items():
    obj.data.materials.clear()
    obj.data.materials.append(oxide if name.startswith("SORA_ExactSVG_ClayRelief") else body)
    obj["review_material_only"]="fictional smoked-clay / iron-oxide treatment"
shank["review_geometry_only"]="rear rows extended 80 mm; front four rows and crest unchanged"

cover=bpy.data.objects["MaruGawara_Cover_R0_C1"]
next_cover=bpy.data.objects["MaruGawara_Cover_R1_C1"]
grid=[[cover.matrix_world@v.co for v in cover.data.vertices[row*13:(row+1)*13]]
      for row in range(9)]


def cover_z(x,y):
    if y<grid[0][0].y or y>grid[-1][0].y:
        return None
    for row in range(8):
        a,b=grid[row],grid[row+1]
        if a[0].y<=y<=b[0].y:
            def side(points):
                for col in range(12):
                    p,q=points[col],points[col+1]
                    if p.x<=x<=q.x:
                        t=(x-p.x)/(q.x-p.x)
                        return p.z*(1-t)+q.z*t
                return None
            za,zb=side(a),side(b)
            if za is None or zb is None:
                return None
            t=(y-a[0].y)/(b[0].y-a[0].y)
            return za*(1-t)+zb*t
    return None


clearance=[]
for vertex in shank.data.vertices[:stride]:
    p=shank.matrix_world@vertex.co
    z=cover_z(p.x,p.y)
    if z is not None:
        clearance.append((p.z-z)*1000)
assert clearance
stats={"count":len(clearance),
       "min_mm":min(clearance),"max_mm":max(clearance),
       "mean_mm":sum(clearance)/len(clearance),
       "rms_from_1p5mm_mm":(sum((v-1.5)**2 for v in clearance)/len(clearance))**.5}
next_y=min((next_cover.matrix_world@v.co).y for v in next_cover.data.vertices)
back_y=(shank.matrix_world@shank.data.vertices[rows*33+16].co).y
gap_mm=(next_y-back_y)*1000
hidden_joint=gap_mm <= -5.0
surface_match=(stats["min_mm"]>-3 and stats["max_mm"]<6
               and stats["rms_from_1p5mm_mm"]<2.5)
print("SORA_EXTENDED_FIT",json.dumps({"gap_mm":gap_mm,"hidden_joint":hidden_joint,
                                         "surface_match":surface_match,"stats":stats},sort_keys=True))
if os.environ.get("SORA_EXTENDED_ANALYSIS_ONLY")=="1":
    raise SystemExit(0)

assert tuple(tuple(row) for row in scene.camera.matrix_world)==camera_matrix
for name,expected in light_state.items():
    light=bpy.data.objects[name]
    assert (tuple(tuple(row) for row in light.matrix_world),
            light.data.energy,light.data.size)==expected
scene.render.filepath=str(OUT/"Nyaagyu_SORA_Extended_FixedReview.png")
bpy.context.preferences.filepaths.save_version=0
for image in bpy.data.images:
    if image.source=="FILE" and image.filepath: image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"Nyaagyu_SORA_Extended_FitReview.blend"))
bpy.ops.render.render(write_still=True)
manifest={
    "status":"derived source-only 80 mm rear-shank extension and fictional clay-color review",
    "generator":"scripts/art/create_nyaagyu_sora_eave_extended_review.py",
    "baseline_blend_sha256":baseline["outputs"][source.name],
    "extension":{"rear_only_m":extension,"start_row":start_row,
                 "source_row_count":rows+1,"front_rows_preserved":start_row,
                 "first_four_rows_exact":True,"crest_geometry_unchanged":True,
                 "manifold_positive_volume":True},
    "joint":{"gap_to_next_cover_mm":gap_mm,"hidden_joint_gate_pass":hidden_joint,
             "surface_clearance":stats,"surface_alignment_gate_pass":surface_match,
             "geometry_gate_pass":hidden_joint and surface_match},
    "fictional_ornament_material":{"body":"smoked ibushi color estimate",
                                   "relief":"iron-oxide tinted molded clay, not a decal",
                                   "historical_claim":False},
    "review_camera_lights_unchanged":True,
    "outputs":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        OUT/"Nyaagyu_SORA_Extended_FitReview.blend",
        OUT/"Nyaagyu_SORA_Extended_FixedReview.png")},
}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print("SORA_EXTENDED_REVIEW",json.dumps(manifest,sort_keys=True))
