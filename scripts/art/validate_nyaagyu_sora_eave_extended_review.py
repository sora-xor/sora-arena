"""Check the extended source-only joint and fired-clay material derivative."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
import bmesh


ROOT=Path(__file__).resolve().parents[2]
CAP=ROOT/"Content/SourceArt/Environment/NyaagyuSoraEaveCapStudy"
BASE=CAP/"RoofBayArtReview"
OUT=CAP/"RoofBayExtendedArtReview"
base=json.loads((BASE/"manifest.json").read_text())
record=json.loads((OUT/"manifest.json").read_text())
source=BASE/"Nyaagyu_KawaraBay_SORA_Cap_FitReview.blend"
assert hashlib.sha256(source.read_bytes()).hexdigest()==record["baseline_blend_sha256"]
assert record["baseline_blend_sha256"]==base["outputs"][source.name]
for name, expected in record["outputs"].items():
    assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==expected,name


def snapshot(obj):
    return ([tuple(v.co) for v in obj.data.vertices],
            [tuple(p.vertices) for p in obj.data.polygons],
            [p.material_index for p in obj.data.polygons],
            tuple(tuple(row) for row in obj.matrix_world))


def lighting():
    scene=bpy.context.scene
    return (tuple(tuple(row) for row in scene.camera.matrix_world),
            scene.camera.data.ortho_scale,
            tuple((name,tuple(tuple(row) for row in bpy.data.objects[name].matrix_world),
                   bpy.data.objects[name].data.energy,bpy.data.objects[name].data.size)
                  for name in ("SkyKey","SoftFill")),
            scene.render.engine,scene.render.resolution_x,scene.render.resolution_y,
            scene.cycles.samples)


bpy.ops.wm.open_mainfile(filepath=str(source))
roof_before={o.name:snapshot(o) for o in bpy.data.collections["KawaraBay_Editable"].objects
             if o.type=="MESH"}
cap_before={o.name:snapshot(o) for o in bpy.data.collections["SORA_EaveCap_Editable"].objects}
assert len(roof_before)==61 and len(cap_before)==6
light_before=lighting()
svg_hash=json.loads((CAP/"manifest.json").read_text())["source_svg_sha256"]

bpy.ops.wm.open_mainfile(filepath=str(OUT/"Nyaagyu_SORA_Extended_FitReview.blend"))
roof_after={o.name:o for o in bpy.data.collections["KawaraBay_Editable"].objects
            if o.type=="MESH"}
cap_after={o.name:o for o in bpy.data.collections["SORA_EaveCap_Editable"].objects}
assert set(roof_after)==set(roof_before)
assert set(cap_after)==set(cap_before)
assert all(snapshot(o)==roof_before[name] for name,o in roof_after.items())
assert lighting()==light_before
assert not set(base["removed_old_review_badge_only"]).intersection(bpy.data.objects)

extension=record["extension"]["rear_only_m"]
assert extension==.080
stride=33*14
for name,obj in cap_after.items():
    vertices,faces,slots,world=snapshot(obj)
    prev_vertices,prev_faces,prev_slots,prev_world=cap_before[name]
    assert faces==prev_faces and slots==prev_slots and world==prev_world,name
    if name=="VaultedCover_SolidClay":
        assert len(vertices)==2*stride
        for skin in (0,1):
            for row in range(14):
                t=max(0,(row-4)/9)
                offset=extension*t*t*(3-2*t)
                for col in range(33):
                    i=skin*stride+row*33+col
                    x,y,z=vertices[i]
                    px,py,pz=prev_vertices[i]
                    assert abs(x-px)<1e-7 and abs(z-pz)<1e-7
                    assert abs((y-py)-offset)<1e-7,(row,col,y-py,offset)
        assert obj.data.materials[0].name.startswith("M_ReviewOnly_SmokedIbushiCap")
    else:
        assert vertices==prev_vertices,name
        expected=("M_ReviewOnly_FictionalIronOxide_SORAClay"
                  if name.startswith("SORA_ExactSVG_ClayRelief")
                  else "M_ReviewOnly_SmokedIbushiCap")
        assert obj.data.materials[0].name.startswith(expected),name
        if name.startswith("SORA_ExactSVG_ClayRelief"):
            assert obj["source_svg_sha256"]==svg_hash
    bm=bmesh.new(); bm.from_mesh(obj.data)
    assert all(e.is_manifold for e in bm.edges),name
    assert bm.calc_volume(signed=True)>0,name
    bm.free()

cover=roof_after["MaruGawara_Cover_R0_C1"]
next_cover=roof_after["MaruGawara_Cover_R1_C1"]
shank=cap_after["VaultedCover_SolidClay"]
grid=[[cover.matrix_world@v.co for v in cover.data.vertices[row*13:(row+1)*13]]
      for row in range(9)]


def cover_z(x,y):
    if y<grid[0][0].y or y>grid[-1][0].y:
        return None
    for row in range(8):
        a,b=grid[row],grid[row+1]
        if a[0].y<=y<=b[0].y:
            def across(points):
                for col in range(12):
                    p,q=points[col],points[col+1]
                    if p.x<=x<=q.x:
                        t=(x-p.x)/(q.x-p.x)
                        return p.z*(1-t)+q.z*t
                return None
            za,zb=across(a),across(b)
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
stats=record["joint"]["surface_clearance"]
assert len(clearance)==stats["count"]==392
rms=(sum((v-1.5)**2 for v in clearance)/len(clearance))**.5
for key,value in (("min_mm",min(clearance)),("max_mm",max(clearance)),
                  ("mean_mm",sum(clearance)/len(clearance)),
                  ("rms_from_1p5mm_mm",rms)):
    assert abs(stats[key]-value)<.01,(key,stats[key],value)
next_y=min((next_cover.matrix_world@v.co).y for v in next_cover.data.vertices)
back_y=(shank.matrix_world@shank.data.vertices[13*33+16].co).y
gap=(next_y-back_y)*1000
assert abs(gap-record["joint"]["gap_to_next_cover_mm"])<.01
assert (gap<=-5)==record["joint"]["hidden_joint_gate_pass"]
assert (min(clearance)>-3 and max(clearance)<6 and rms<2.5)==record["joint"]["surface_alignment_gate_pass"]
assert record["joint"]["geometry_gate_pass"]
image=bpy.data.images.load(str(OUT/"Nyaagyu_SORA_Extended_FixedReview.png"))
assert tuple(image.size)==(1360,900)
print(json.dumps({"status":"passed source-only extended derivative geometry; no AAA or historical approval",
                  "roof_meshes_unchanged":len(roof_after),"cap_front_rows_preserved":4,
                  "svg_relief_meshes_preserved":2,
                  "socket_overlap_under_next_course_mm":round(-gap,3),
                  "clearance_rms_mm":round(rms,3)},indent=2))
