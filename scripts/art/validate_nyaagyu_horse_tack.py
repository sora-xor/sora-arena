"""Independently inspect the editable horse/tack source and FBX round-trip.

Run: blender -b Content/SourceArt/Horses/Nyaagyu/Nyaagyu_HorseAndTack.blend \
  --python scripts/art/validate_nyaagyu_horse_tack.py
"""

import atexit
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


validated=False
def fail_exit():
    if not validated:
        sys.stdout.flush();sys.stderr.flush();os._exit(1)
atexit.register(fail_exit)

root=Path(__file__).resolve().parents[2]
out=root/"Content/SourceArt/Horses/Nyaagyu"
manifest=json.loads((out/"manifest.json").read_text())
assert bpy.app.version[:2]==(5,2)
assert manifest["schema_version"]==1
assert manifest["name"]=="SM_Nyaagyu_HorseAndTack"
assert manifest["generator"]=="scripts/art/create_nyaagyu_horse_tack.py"
assert manifest["validator"]=="scripts/art/validate_nyaagyu_horse_tack.py"
assert manifest["unreal_asset"]=="/Game/ArtReview/Horses/SM_Nyaagyu_HorseAndTack.SM_Nyaagyu_HorseAndTack"
assert manifest["units"]=="meters" and manifest["world_origin_m"]==[0,0,0]
assert manifest["local_forward"]=="+X horse-forward; +Z up"
assert manifest["rigged"] is False and manifest["external_images"]==[]
assert "not a photoreal shipping horse" in manifest["limitations"]
assert "Original project-owned" in manifest["license"]
assert Path(bpy.data.filepath).resolve()==(out/manifest["source_blend"]).resolve()
for filename,field in ((manifest["source_blend"],"blend_sha256"),
                       (manifest["fbx"],"fbx_sha256"),
                       (manifest["preview"],"preview_sha256")):
    path=out/filename
    assert path.stat().st_size>1000,path
    assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest[field],path
logo=(out/manifest["insignia_source"]).resolve()
assert hashlib.sha256(logo.read_bytes()).hexdigest()==manifest["insignia_sha256"]
assert not [im for im in bpy.data.images if im.source=="FILE"]

collection=bpy.data.collections.get("NyaagyuHorse_Editable")
assert collection is not None
parts=[obj for obj in collection.objects if obj.type=="MESH"]
assert len(parts)==manifest["source_parts"] and len(parts)>110
assert len([obj for obj in parts if obj.name.startswith("SORA_kamon_exact_svg_")])==8
assert all(obj["source_svg_sha256"]==manifest["insignia_sha256"]
           for obj in parts if obj.name.startswith("SORA_kamon_exact_svg_"))
for name in ("Horse_anatomical_core",
             "Horse_tail_root","Kura_wooden_tree","Kura_lacquered_seat",
             "Kura_maewa_high_lacquer_panel","Kura_shizuwa_high_lacquer_panel",
             "Kura_girth_under_belly","Tack_breaststrap","Tack_crupper",
             "Abumi_-1_broad_iron_footplate","Abumi_1_broad_iron_footplate",
             "Abumi_-1_hato_mune_iron_toe_shell","Abumi_1_hato_mune_iron_toe_shell",
             "Abumi_-1_strap","Abumi_1_strap","Kutsuwa_hami_bar",
             "Tazuna_rein_-1","Tazuna_rein_1"):
    assert any(obj.name==name for obj in parts),name
assert len([obj for obj in parts if "_hoof" in obj.name])==4
assert not [obj for obj in parts if obj.name.endswith("_continuous_limb")]
core=collection.objects["Horse_anatomical_core"]
assert len(core.data.vertices)>20000
assert {mat.name for mat in core.data.materials}=={
    "M_Horse_SealBrownCoat","M_Horse_DarkPoints"}
assert {core.data.materials[p.material_index].name for p in core.data.polygons}=={
    "M_Horse_SealBrownCoat","M_Horse_DarkPoints"}
assert len([obj for obj in parts if obj.name.startswith("Horse_mane_strand_")])==104
assert len([obj for obj in parts if obj.name.startswith("Horse_forelock_strand_")])==18
assert len([obj for obj in parts if obj.name.startswith("Horse_tail_strand_")])==54
for side in (-1,1):
    for label in ("fore","hind"):
        hoof=collection.objects[f"Horse_{label}_{side}_hoof"]
        assert len(hoof.data.vertices)==3*20
assert all(any(obj.name==f"Horse_eye_{side}" for obj in parts) for side in (-1,1))
triangles=sum(len(poly.vertices)-2 for obj in parts for poly in obj.data.polygons)
assert triangles==manifest["source_triangles"] and 8000<triangles<250000
assert all(obj.type!="ARMATURE" for obj in bpy.data.objects)
for name,position in manifest["anchors_m"].items():
    anchor=collection.objects.get(name)
    assert anchor and anchor.type=="EMPTY",name
    assert all(abs(anchor.location[i]-position[i])<1e-5 for i in range(3)),name
assert set(manifest["anchors_m"])=={
    "Horse_Root","Saddle_RiderSeat","Tazuna_LeftGrip","Tazuna_RightGrip",
    "Abumi_LeftFoot","Abumi_RightFoot"}

fbx=out/manifest["fbx"]
assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
assert b"/Users/" not in fbx.read_bytes()
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported=[obj for obj in set(bpy.data.objects)-before if obj.type=="MESH"]
assert len(imported)==1,[obj.name for obj in imported]
model=imported[0]
assert model.name.startswith(manifest["name"]),model.name
corners=[model.matrix_world @ Vector(c) for c in model.bound_box]
for axis in range(3):
    assert abs(min(v[axis] for v in corners)-manifest["bounds_m"]["min"][axis])<.025
    assert abs(max(v[axis] for v in corners)-manifest["bounds_m"]["max"][axis])<.025
assert -.02<manifest["bounds_m"]["min"][2]<.02
assert 1.80<manifest["bounds_m"]["max"][2]<1.90
slots={slot.material.name.split(".",1)[0] for slot in model.material_slots}
for material in ("M_Horse_SealBrownCoat","M_Horse_BlackMane",
                 "M_Tack_BlackUrushi","M_Tack_IndigoSilk",
                 "M_Tack_BlackenedIron","M_Tack_SORA_Red"):
    assert material in slots,(material,slots)
print("NYAAGYU_HORSE_TACK_FBX_ROUNDTRIP_PASS",len(parts),triangles,
      manifest["bounds_m"],sorted(slots))
validated=True
