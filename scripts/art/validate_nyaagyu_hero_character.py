"""Independently validate the editable feline-samurai asset and Blender FBX round-trip.

Run: blender -b Content/SourceArt/Characters/Hero/Nyaagyu_HeroCharacter.blend \
  --python scripts/art/validate_nyaagyu_hero_character.py
"""

import atexit
import hashlib
import json
import os
import re
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
out=root/"Content/SourceArt/Characters/Hero"
manifest=json.loads((out/"manifest.json").read_text())
name="SM_Nyaagyu_HeroCharacter"
assert bpy.app.version[:2]==(5,2)
assert Path(bpy.data.filepath).resolve()==(out/manifest["source_blend"]).resolve()
assert manifest["schema_version"]==2 and manifest["name"]==name
assert manifest["character_name_ja"]=="ニャーコト"
assert manifest["character_name_en"]=="Nyaakoto"
assert manifest["user_design_reference_sha256"]=="c9f7a4bbe6ba529b2bbdb629db3ba09858c11b563c334e31593876455a550801"
assert manifest["user_design_reference_embedded"] is False
assert manifest["generator"]=="scripts/art/create_nyaagyu_hero_character.py"
assert manifest["validator"]=="scripts/art/validate_nyaagyu_hero_character.py"
assert manifest["unreal_asset"]==f"/Game/ArtReview/Characters/{name}.{name}"
assert manifest["fbx"]==name+".fbx"
assert manifest["local_forward"]=="+X face-forward; +Z up"
assert manifest["world_origin_m"]==[0,0,0] and manifest["rigged"] is False
assert manifest["external_images"]==[]
assert "Original project-owned character geometry" in manifest["license"]
assert "user-supplied SORA insignia" in manifest["license"]
for filename,field in ((manifest["source_blend"],"blend_sha256"),
                       (manifest["fbx"],"fbx_sha256"),
                       (manifest["preview"],"preview_sha256"),
                       (manifest["detail_preview"],"detail_preview_sha256")):
    path=out/filename
    assert path.stat().st_size>1000,path
    assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest[field],path
logo=(out/manifest["insignia_source"]).resolve()
logo_record=json.loads((logo.parent/"sora_logo_manifest.json").read_text())
assert manifest["insignia_sha256"]==logo_record["source_sha256"]
assert hashlib.sha256(logo.read_bytes()).hexdigest()==manifest["insignia_sha256"]
assert not [image for image in bpy.data.images if image.source=="FILE"]
collection=bpy.data.collections.get("NyaagyuHero_Editable")
assert collection is not None
parts=[o for o in collection.objects if o.type=="MESH"]
assert len(parts)==manifest["source_parts"] and len(parts)>150
triangles=sum(len(p.vertices)-2 for o in parts for p in o.data.polygons)
assert triangles==manifest["source_triangles"] and 10000<triangles<200000
assert len([o for o in parts if re.fullmatch(r"Finger_-?1_[0-3]",o.name)])==8
assert len([o for o in parts if o.name.startswith("Toe_")])==8
assert len([o for o in parts if o.name.startswith("Whisker_")])==8
assert manifest["sora_kamon_placements"]==["chest","waist","sode_-1","sode_1"]
for placement in manifest["sora_kamon_placements"]:
    paths=[o for o in parts if o.name.startswith(f"UserSupplied_SORAKamon_{placement}_Path_")]
    assert len(paths)==2,(placement,[o.name for o in paths])
    assert {o["source_svg_sha256"] for o in paths}=={manifest["insignia_sha256"]}
assert not any(o.name.startswith("Clan_mon_ray_") for o in parts)
assert any(o.name=="Skull" for o in parts)
assert any(o.name=="Tail_arched" for o in parts)
assert any(o.name=="Saya_lacquer" for o in parts)
assert any(o.name=="Katana_tsuka_sheathed" for o in parts)
assert any(o.name=="Yumi_laminated_bamboo" for o in parts)
assert any(o.name=="Yumi_lower_grip_wrap" for o in parts)
assert any(o.name=="Ebira_lacquer_backboard" for o in parts)
assert len([o for o in parts if o.name.startswith("Ya_bamboo_shaft_")])==6
assert len([o for o in parts if o.name.startswith("Ya_red_fletch_")])==12
assert any(o.name=="Karakuri_wrist_cell" for o in parts)
assert not any(o.name==name for o in collection.objects)
assert all(not (o.type=="ARMATURE") for o in bpy.data.objects)

fbx=out/manifest["fbx"]
fbx_data=fbx.read_bytes()
assert fbx_data.startswith(b"Kaydara FBX Binary") and b"/Users/" not in fbx_data
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported=[o for o in set(bpy.data.objects)-before if o.type=="MESH"]
assert len(imported)==1 and imported[0].name==name,[o.name for o in imported]
mesh=imported[0]
corners=[mesh.matrix_world @ Vector(v) for v in mesh.bound_box]
for axis in range(3):
    assert abs(min(v[axis] for v in corners)-manifest["bounds_m"]["min"][axis])<.02
    assert abs(max(v[axis] for v in corners)-manifest["bounds_m"]["max"][axis])<.02
assert manifest["bounds_m"]["min"][2]>-.02
assert 2.15<manifest["bounds_m"]["max"][2]<2.22
slots={slot.material.name.split(".",1)[0] for slot in mesh.material_slots}
for expected in ("M_Hero_GreyTabbyFur","M_Hero_WhiteFur","M_Hero_BlueEye",
                 "M_Hero_OxbloodUrushi","M_Hero_SORAResistanceRed",
                 "M_Hero_YumiLaminatedBamboo","M_Hero_RedArrowFletch"):
    assert expected in slots,(expected,slots)
print("NYAAGYU_HERO_FBX_ROUNDTRIP_PASS",len(parts),triangles,manifest["bounds_m"],sorted(slots))
validated=True
