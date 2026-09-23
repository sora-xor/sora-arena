"""Independent source/FBX checks for the source-only Nyaakoto paw study.

Run:
  blender -b Content/SourceArt/Characters/NyaakotoFirstPersonPaws/Nyaakoto_FirstPersonPaws_GripStudy.blend \
    --python scripts/art/validate_nyaakoto_first_person_paws.py
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"Content/SourceArt/Characters/NyaakotoFirstPersonPaws"
record=json.loads((OUT/"manifest.json").read_text())
assert record["schema_version"]==1 and record["status"].startswith("source-only")
assert Path(bpy.data.filepath).resolve()==(OUT/"Nyaakoto_FirstPersonPaws_GripStudy.blend").resolve()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for relative,digest in record["source_sha256"].items():
    assert sha(ROOT/relative)==digest,relative
for name,digest in record["reused_project_pbr_sha256"].items():
    assert sha(ROOT/record["reused_project_pbr"]/name)==digest,name
pad_record=json.loads((ROOT/record["original_paw_pad_maps"]).read_text())
for entry in pad_record["maps"].values():
    path=OUT/"Textures"/entry["file"]
    assert sha(path)==entry["sha256"],path
    header=path.read_bytes()[:26]
    assert header[:8]==b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II",header[16:24])==(1024,1024) and header[25]==2
for name,info in record["outputs"].items():
    path=OUT/name
    assert path.stat().st_size==info["bytes"] and sha(path)==info["sha256"],name

for collection in ("Construction_Editable_Hidden","Katana_Paws_Editable",
                   "Yumi_Paw_Editable","Review_Only_ExistingKatana","Review_Only_ExistingYumi"):
    assert collection in bpy.data.collections,collection
assert bpy.data.collections["Construction_Editable_Hidden"].hide_render
assert all(o.get("review_only") for c in ("Review_Only_ExistingKatana","Review_Only_ExistingYumi")
           for o in bpy.data.collections[c].objects if o.type=="MESH")

mesh_objs={o.name:o for o in bpy.data.objects if o.type=="MESH"}
bodies=[]
for prefix in ("", "LeftSupport_", "BowLeft_"):
    name=prefix+"Paw_SculptedContinuousBody"
    body=mesh_objs[name]
    assert 15000<len(body.data.polygons)<50000,(name,len(body.data.polygons))
    assert body.data.uv_layers.active is not None
    assert body.get("runtime_status"," ").startswith("source-only")
    assert .17<max(body.dimensions)<.25,(name,tuple(body.dimensions))
    bodies.append(body)
    for i in range(1,5):
        for component in (f"DigitalPad_{i}",f"RetractileClaw_{i}"):
            obj=mesh_objs[prefix+component]
            assert obj.data.uv_layers.active is not None,(prefix,component)
    for i in range(1,4):
        obj=mesh_objs[prefix+f"Kote_LacqueredIronLamella_{i}"]
        assert obj.data.uv_layers.active is not None

# Contact pads must lie on, or slightly compress against, the two imported
# handle radii. This checks world-space pose and catches a transform mismatch.
contact=[]
for prefix in ("", "LeftSupport_", "BowLeft_"):
    for i in range(1,5):
        p=mesh_objs[prefix+f"DigitalPad_{i}"].matrix_world.translation
        if prefix=="BowLeft_":
            radial=math.hypot(p.x-2.012,p.y)
            assert abs(p.z)<.07
        else:
            radial=math.hypot(p.y,p.z)
            expected_x=-.095 if prefix=="" else -.215
            assert abs(p.x-expected_x)<.075
        assert .018<radial<.032,(prefix,i,radial)
        contact.append(round(radial,4))

for image in bpy.data.images:
    if image.source=="FILE" and image.filepath:
        assert Path(bpy.path.abspath(image.filepath)).is_file(),image.filepath

sculpt_body_faces=len(bodies[0].data.polygons)

for asset,expected_bodies in (("SM_Nyaakoto_KatanaPaws_GripStudy.fbx",2),
                              ("SM_Nyaakoto_YumiPaw_GripStudy.fbx",1)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(OUT/asset))
    imported=[o for o in bpy.data.objects if o.type=="MESH"]
    assert len(imported)>expected_bodies*25,(asset,len(imported))
    assert sum("Paw_SculptedContinuousBody" in o.name for o in imported)==expected_bodies,asset
    assert not any("ReviewOnly" in o.name for o in imported),asset
    assert all(o.data.uv_layers.active is not None for o in imported),asset
    assert sum(len(o.data.polygons) for o in imported)<120000,asset

print(json.dumps({"verified":"source-only paw study","contact_radii_m":contact,
                  "sculpt_body_faces":sculpt_body_faces,
                  "fbx_roundtrip":["katana","yumi"]}))
